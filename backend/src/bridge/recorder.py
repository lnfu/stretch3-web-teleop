import asyncio
import logging
import platform
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2
import h5py
import numpy as np

from .config import settings

logger = logging.getLogger(__name__)

CAMERA_ID_ARDUCAM = 0x00
CAMERA_ID_D435I_RGB = 0x01
CAMERA_ID_D435I_DEPTH = 0x02
CAMERA_ID_D405_RGB = 0x03
CAMERA_ID_D405_DEPTH = 0x04

CAMERA_FILES = {
    CAMERA_ID_ARDUCAM: "arducam_rgb.h5",
    CAMERA_ID_D435I_RGB: "d435i_rgb.h5",
    CAMERA_ID_D435I_DEPTH: "d435i_depth.h5",
    CAMERA_ID_D405_RGB: "d405_rgb.h5",
    CAMERA_ID_D405_DEPTH: "d405_depth.h5",
}

CAMERA_NAMES = {
    CAMERA_ID_ARDUCAM: "arducam_rgb",
    CAMERA_ID_D435I_RGB: "d435i_rgb",
    CAMERA_ID_D435I_DEPTH: "d435i_depth",
    CAMERA_ID_D405_RGB: "d405_rgb",
    CAMERA_ID_D405_DEPTH: "d405_depth",
}


class Recorder:
    def __init__(self):
        self._recording = False
        self._session_name: str | None = None
        self._session_dir: Path | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._drain_task: asyncio.Task | None = None
        self._h5_files: dict = {}
        # Single-worker executor: h5py is not thread-safe; one dedicated thread
        # keeps all file I/O off the asyncio event loop without concurrency issues.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="recorder")

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def session_name(self) -> str | None:
        return self._session_name

    async def start(self) -> str:
        if self._recording:
            return self._session_name  # type: ignore[return-value]
        self._session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        recordings_dir = Path(settings.recordings_dir)
        self._session_dir = recordings_dir / self._session_name
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._h5_files = {}
        self._recording = True
        self._drain_task = asyncio.create_task(self._drain_loop())
        logger.info(f"Recording started: {self._session_name}")
        return self._session_name

    async def stop(self) -> "Path | None":
        if not self._recording:
            return
        self._recording = False
        if self._drain_task:
            # Wait for all queued writes to finish before tearing down.
            await self._queue.join()
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        loop = asyncio.get_running_loop()
        # Close HDF5 files on the same executor thread that wrote them.
        await loop.run_in_executor(self._executor, self._close_h5_files)
        logger.info(f"Recording stopped: {self._session_name}")
        return self._session_dir

    async def generate_previews(self, session_dir: Path) -> None:
        """Run preview generation in a thread pool (CPU-bound). Awaitable."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._generate_previews, session_dir)

    def record_camera(self, camera_id: int, timestamp_ns: int, frame: np.ndarray) -> None:
        if not self._recording:
            return
        self._queue.put_nowait(("camera", camera_id, timestamp_ns, frame.copy()))

    def record_status(self, timestamp_ns: int, status: dict) -> None:
        if not self._recording:
            return
        self._queue.put_nowait(("status", timestamp_ns, status))

    async def _drain_loop(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await self._queue.get()
                try:
                    if item[0] == "camera":
                        _, camera_id, timestamp_ns, frame = item
                        await loop.run_in_executor(
                            self._executor,
                            self._write_camera,
                            camera_id,
                            timestamp_ns,
                            frame,
                        )
                    elif item[0] == "status":
                        _, timestamp_ns, status = item
                        await loop.run_in_executor(
                            self._executor,
                            self._write_status,
                            timestamp_ns,
                            status,
                        )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                # stop() drains the queue via queue.join() before cancelling,
                # so the queue is empty here; just exit cleanly.
                raise

    def _close_h5_files(self) -> None:
        for f in self._h5_files.values():
            try:
                f.close()
            except Exception:
                pass
        self._h5_files.clear()

    def _get_h5_file(self, key: str) -> h5py.File:
        if key not in self._h5_files:
            assert self._session_dir is not None
            path = self._session_dir / key
            self._h5_files[key] = h5py.File(path, "a")
        return self._h5_files[key]

    def _write_camera(self, camera_id: int, timestamp_ns: int, frame: np.ndarray) -> None:
        filename = CAMERA_FILES.get(camera_id)
        if not filename:
            return
        f = self._get_h5_file(filename)
        is_depth = camera_id in (CAMERA_ID_D435I_DEPTH, CAMERA_ID_D405_DEPTH)
        dtype = np.uint16 if is_depth else np.uint8
        frame = frame.astype(dtype)

        if "timestamps" not in f:
            f.create_dataset(
                "timestamps", shape=(0,), maxshape=(None,), dtype=np.uint64, chunks=(1,)
            )
        if "frames" not in f:
            shape = (0,) + frame.shape
            maxshape = (None,) + frame.shape
            f.create_dataset(
                "frames",
                shape=shape,
                maxshape=maxshape,
                dtype=dtype,
                chunks=(1,) + frame.shape,
                compression="lzf",
            )

        ts_ds = f["timestamps"]
        fr_ds = f["frames"]
        n = ts_ds.shape[0]
        ts_ds.resize((n + 1,))
        ts_ds[n] = timestamp_ns
        fr_ds.resize((n + 1,) + frame.shape)
        fr_ds[n] = frame
        f.flush()

    def _write_status(self, timestamp_ns: int, status: dict) -> None:
        # Odometry
        f = self._get_h5_file("odometry.h5")
        odom = status.get("odometry", {})
        pose = odom.get("pose", {})
        twist = odom.get("twist", {})
        x = float(pose.get("x", 0.0))
        y = float(pose.get("y", 0.0))
        theta = float(pose.get("theta", 0.0))
        linear = float(twist.get("linear", 0.0))
        angular = float(twist.get("angular", 0.0))

        if "timestamps" not in f:
            for name in ("timestamps", "x", "y", "theta", "linear", "angular"):
                dtype = np.uint64 if name == "timestamps" else np.float64
                f.create_dataset(
                    name, shape=(0,), maxshape=(None,), dtype=dtype, chunks=(1,)
                )

        n = f["timestamps"].shape[0]
        for name, val in [
            ("timestamps", timestamp_ns),
            ("x", x),
            ("y", y),
            ("theta", theta),
            ("linear", linear),
            ("angular", angular),
        ]:
            ds = f[name]
            ds.resize((n + 1,))
            ds[n] = val
        f.flush()

        # Joint states
        fj = self._get_h5_file("joint_states.h5")
        positions_raw = list(status.get("joint_positions", [0.0] * 10))
        positions = np.array(positions_raw[:10], dtype=np.float64)
        # Pad to 10 if fewer values
        if len(positions) < 10:
            positions = np.pad(positions, (0, 10 - len(positions)))

        if "timestamps" not in fj:
            fj.create_dataset(
                "timestamps", shape=(0,), maxshape=(None,), dtype=np.uint64, chunks=(1,)
            )
            fj.create_dataset(
                "positions",
                shape=(0, 10),
                maxshape=(None, 10),
                dtype=np.float64,
                chunks=(1, 10),
            )

        nj = fj["timestamps"].shape[0]
        fj["timestamps"].resize((nj + 1,))
        fj["timestamps"][nj] = timestamp_ns
        fj["positions"].resize((nj + 1, 10))
        fj["positions"][nj] = positions
        fj.flush()

    def _generate_previews(self, session_dir: Path | None = None) -> None:
        if session_dir is None:
            session_dir = self._session_dir
        if not session_dir:
            return
        preview_dir = session_dir / "preview"
        preview_dir.mkdir(exist_ok=True)

        for camera_id, name in CAMERA_NAMES.items():
            h5_path = session_dir / CAMERA_FILES[camera_id]
            if not h5_path.exists():
                continue
            is_depth = camera_id in (CAMERA_ID_D435I_DEPTH, CAMERA_ID_D405_DEPTH)
            try:
                with h5py.File(h5_path, "r") as f:
                    if "frames" not in f or "timestamps" not in f:
                        continue
                    frames = f["frames"][:]
                    timestamps = f["timestamps"][:]

                n = len(frames)
                if n == 0:
                    continue

                # Compute FPS from recorded timestamps
                if n >= 2:
                    duration_s = (int(timestamps[-1]) - int(timestamps[0])) / 1e9
                    fps = (n - 1) / duration_s if duration_s > 0 else 10.0
                else:
                    fps = 10.0
                fps = float(max(1.0, min(fps, 120.0)))

                h, w = frames[0].shape[:2]
                out_path = str(preview_dir / f"{name}.mp4")

                # On Linux, avc1 triggers the h264_v4l2m2m hardware encoder which
                # may not be available; use mp4v (MPEG-4) directly to avoid errors.
                # On macOS, avc1 uses the native software encoder and is preferred.
                if platform.system() == "Darwin":
                    fourcc = cv2.VideoWriter_fourcc(*"avc1")
                    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
                    if not writer.isOpened():
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
                else:
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

                for frame in frames:
                    if is_depth:
                        bgr = cv2.applyColorMap(
                            cv2.convertScaleAbs(frame, alpha=0.03), cv2.COLORMAP_JET
                        )
                    else:
                        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    writer.write(bgr)

                writer.release()
                logger.info(f"Preview saved: {out_path} ({n} frames @ {fps:.1f} fps)")
            except Exception as e:
                logger.error(f"Failed to save preview for {name}: {e}")
