import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from .config import settings

logger = logging.getLogger(__name__)

CAMERA_ID_ARDUCAM = 0x00
CAMERA_ID_D435I_RGB = 0x01
CAMERA_ID_D435I_DEPTH = 0x02
CAMERA_ID_D405_RGB = 0x03
CAMERA_ID_D405_DEPTH = 0x04

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
        self._session_file: Path | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._drain_task: asyncio.Task | None = None
        self._h5_file: h5py.File | None = None
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
        recordings_dir.mkdir(parents=True, exist_ok=True)
        self._session_file = recordings_dir / f"{self._session_name}.h5"
        self._h5_file = None
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
        # Close HDF5 file on the same executor thread that wrote it.
        await loop.run_in_executor(self._executor, self._close_h5_file)
        logger.info(f"Recording stopped: {self._session_name}")
        return self._session_file

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

    def _close_h5_file(self) -> None:
        if self._h5_file is not None:
            try:
                self._h5_file.close()
            except Exception:
                pass
            self._h5_file = None

    def _get_h5(self) -> h5py.File:
        if self._h5_file is None:
            assert self._session_file is not None
            self._h5_file = h5py.File(self._session_file, "a")
        return self._h5_file

    def _write_camera(self, camera_id: int, timestamp_ns: int, frame: np.ndarray) -> None:
        name = CAMERA_NAMES.get(camera_id)
        if not name:
            return
        f = self._get_h5()
        is_depth = camera_id in (CAMERA_ID_D435I_DEPTH, CAMERA_ID_D405_DEPTH)
        dtype = np.uint16 if is_depth else np.uint8
        frame = frame.astype(dtype)

        if name not in f:
            grp = f.create_group(name)
            grp.create_dataset(
                "timestamps", shape=(0,), maxshape=(None,), dtype=np.uint64, chunks=(1,)
            )
            grp.create_dataset(
                "frames",
                shape=(0,) + frame.shape,
                maxshape=(None,) + frame.shape,
                dtype=dtype,
                chunks=(1,) + frame.shape,
                compression="lzf",
            )

        grp = f[name]
        ts_ds = grp["timestamps"]
        fr_ds = grp["frames"]
        n = ts_ds.shape[0]
        ts_ds.resize((n + 1,))
        ts_ds[n] = timestamp_ns
        fr_ds.resize((n + 1,) + frame.shape)
        fr_ds[n] = frame

    def _write_status(self, timestamp_ns: int, status: dict) -> None:
        f = self._get_h5()

        # Odometry
        odom = status.get("odometry", {})
        pose = odom.get("pose", {})
        twist = odom.get("twist", {})
        x = float(pose.get("x", 0.0))
        y = float(pose.get("y", 0.0))
        theta = float(pose.get("theta", 0.0))
        linear = float(twist.get("linear", 0.0))
        angular = float(twist.get("angular", 0.0))

        if "odometry" not in f:
            grp = f.create_group("odometry")
            for name in ("timestamps", "x", "y", "theta", "linear", "angular"):
                dtype = np.uint64 if name == "timestamps" else np.float64
                grp.create_dataset(
                    name, shape=(0,), maxshape=(None,), dtype=dtype, chunks=(1,)
                )

        grp = f["odometry"]
        n = grp["timestamps"].shape[0]
        for name, val in [
            ("timestamps", timestamp_ns),
            ("x", x),
            ("y", y),
            ("theta", theta),
            ("linear", linear),
            ("angular", angular),
        ]:
            ds = grp[name]
            ds.resize((n + 1,))
            ds[n] = val

        # Joint states
        positions_raw = list(status.get("joint_positions", [0.0] * 10))
        positions = np.array(positions_raw[:10], dtype=np.float64)
        if len(positions) < 10:
            positions = np.pad(positions, (0, 10 - len(positions)))

        if "joint_states" not in f:
            grp = f.create_group("joint_states")
            grp.create_dataset(
                "timestamps", shape=(0,), maxshape=(None,), dtype=np.uint64, chunks=(1,)
            )
            grp.create_dataset(
                "positions",
                shape=(0, 10),
                maxshape=(None, 10),
                dtype=np.float64,
                chunks=(1, 10),
            )

        grp = f["joint_states"]
        nj = grp["timestamps"].shape[0]
        grp["timestamps"].resize((nj + 1,))
        grp["timestamps"][nj] = timestamp_ns
        grp["positions"].resize((nj + 1, 10))
        grp["positions"][nj] = positions
