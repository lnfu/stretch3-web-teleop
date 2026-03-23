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

_DEPTH_CAMERA_IDS = {CAMERA_ID_D435I_DEPTH, CAMERA_ID_D405_DEPTH}


class _CameraWriter:
    """One queue + one dedicated thread + one HDF5 file per camera stream."""

    def __init__(self, name: str, file_path: Path, is_depth: bool):
        self._name = name
        self._file_path = file_path
        self._is_depth = is_depth
        self._queue: asyncio.Queue = asyncio.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"rec_{name}"
        )
        self._h5: h5py.File | None = None
        self._drain_task: asyncio.Task | None = None

    def start(self) -> None:
        self._drain_task = asyncio.create_task(
            self._drain_loop(), name=f"drain_{self._name}"
        )

    def enqueue(self, timestamp_ns: int, frame: np.ndarray) -> None:
        self._queue.put_nowait((timestamp_ns, frame.copy()))

    async def stop(self) -> None:
        await self._queue.join()
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._close_h5)
        self._executor.shutdown(wait=False)

    async def _drain_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await self._queue.get()
                try:
                    timestamp_ns, frame = item
                    await loop.run_in_executor(
                        self._executor, self._write, timestamp_ns, frame
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                raise

    def _get_h5(self) -> h5py.File:
        if self._h5 is None:
            self._h5 = h5py.File(self._file_path, "a")
        return self._h5

    def _close_h5(self) -> None:
        if self._h5 is not None:
            try:
                self._h5.close()
            except Exception:
                pass
            self._h5 = None

    def _write(self, timestamp_ns: int, frame: np.ndarray) -> None:
        dtype = np.uint16 if self._is_depth else np.uint8
        frame = frame.astype(dtype)
        f = self._get_h5()
        if "timestamps" not in f:
            f.create_dataset(
                "timestamps", shape=(0,), maxshape=(None,), dtype=np.uint64, chunks=(1,)
            )
            f.create_dataset(
                "frames",
                shape=(0,) + frame.shape,
                maxshape=(None,) + frame.shape,
                dtype=dtype,
                chunks=(1,) + frame.shape,
                compression="lzf",
            )
        n = f["timestamps"].shape[0]
        f["timestamps"].resize((n + 1,))
        f["timestamps"][n] = timestamp_ns
        f["frames"].resize((n + 1,) + frame.shape)
        f["frames"][n] = frame


class _StatusWriter:
    """One queue + one dedicated thread + one HDF5 file for odometry and joint states."""

    def __init__(self, file_path: Path):
        self._file_path = file_path
        self._queue: asyncio.Queue = asyncio.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="rec_status"
        )
        self._h5: h5py.File | None = None
        self._drain_task: asyncio.Task | None = None

    def start(self) -> None:
        self._drain_task = asyncio.create_task(
            self._drain_loop(), name="drain_status"
        )

    def enqueue(self, timestamp_ns: int, status: dict) -> None:
        self._queue.put_nowait((timestamp_ns, status))

    async def stop(self) -> None:
        await self._queue.join()
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._close_h5)
        self._executor.shutdown(wait=False)

    async def _drain_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await self._queue.get()
                try:
                    timestamp_ns, status = item
                    await loop.run_in_executor(
                        self._executor, self._write, timestamp_ns, status
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                raise

    def _get_h5(self) -> h5py.File:
        if self._h5 is None:
            self._h5 = h5py.File(self._file_path, "a")
        return self._h5

    def _close_h5(self) -> None:
        if self._h5 is not None:
            try:
                self._h5.close()
            except Exception:
                pass
            self._h5 = None

    def _write(self, timestamp_ns: int, status: dict) -> None:
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


class Recorder:
    def __init__(self):
        self._recording = False
        self._session_name: str | None = None
        self._session_dir: Path | None = None
        self._camera_writers: dict[int, _CameraWriter] = {}
        self._status_writer: _StatusWriter | None = None

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
        self._session_dir = Path(settings.recordings_dir) / self._session_name
        self._session_dir.mkdir(parents=True, exist_ok=True)

        self._camera_writers = {
            camera_id: _CameraWriter(
                name=name,
                file_path=self._session_dir / f"{name}.h5",
                is_depth=camera_id in _DEPTH_CAMERA_IDS,
            )
            for camera_id, name in CAMERA_NAMES.items()
        }
        self._status_writer = _StatusWriter(self._session_dir / "status.h5")

        for writer in self._camera_writers.values():
            writer.start()
        self._status_writer.start()

        self._recording = True
        logger.info("Recording started: %s", self._session_name)
        return self._session_name

    async def stop(self) -> "Path | None":
        if not self._recording:
            return None
        self._recording = False

        # Stop all writers in parallel, then stop status writer
        await asyncio.gather(*[w.stop() for w in self._camera_writers.values()])
        if self._status_writer:
            await self._status_writer.stop()

        logger.info("Recording stopped: %s", self._session_name)
        return self._session_dir

    def record_camera(self, camera_id: int, timestamp_ns: int, frame: np.ndarray) -> None:
        if not self._recording:
            return
        writer = self._camera_writers.get(camera_id)
        if writer:
            writer.enqueue(timestamp_ns, frame)

    def record_status(self, timestamp_ns: int, status: dict) -> None:
        if not self._recording:
            return
        if self._status_writer:
            self._status_writer.enqueue(timestamp_ns, status)
