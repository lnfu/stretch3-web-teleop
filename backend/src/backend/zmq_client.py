import asyncio
import logging
import struct
import time
from typing import Callable, Awaitable

import cv2
import msgpack
import numpy as np
import zmq
import zmq.asyncio

from .config import settings
from .messages import (
    CAMERA_ID_ARDUCAM,
    CAMERA_ID_D435I_RGB,
    CAMERA_ID_D435I_DEPTH,
    CAMERA_ID_D405_RGB,
    CAMERA_ID_D405_DEPTH,
    encode_camera_frame,
)

logger = logging.getLogger(__name__)

BroadcastCallback = Callable[[bytes | str], Awaitable[None]]


class ZMQClient:
    def __init__(self):
        self._ctx = zmq.asyncio.Context()
        self._broadcast_cb: BroadcastCallback | None = None
        self._record_camera_cb: Callable | None = None
        self._record_status_cb: Callable | None = None
        self._tasks: list[asyncio.Task] = []
        # Persistent PUB socket for sending commands
        self._pub_sock: zmq.asyncio.Socket | None = None

    def set_broadcast_callback(self, cb: BroadcastCallback):
        self._broadcast_cb = cb

    def set_record_callbacks(self, camera_cb: Callable, status_cb: Callable):
        self._record_camera_cb = camera_cb
        self._record_status_cb = status_cb

    async def start(self):
        # Create a persistent PUB socket for command publishing
        self._pub_sock = self._ctx.socket(zmq.PUB)
        self._pub_sock.connect(settings.zmq_command_addr)
        # Give the socket a moment to establish connection
        await asyncio.sleep(0.1)

        self._tasks = [
            asyncio.create_task(self._status_loop(), name="zmq_status"),
            asyncio.create_task(self._arducam_loop(), name="zmq_arducam"),
            asyncio.create_task(self._d435i_loop(), name="zmq_d435i"),
            asyncio.create_task(self._d405_loop(), name="zmq_d405"),
        ]
        logger.info("ZMQ client started, all subscriber tasks launched")

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._pub_sock:
            self._pub_sock.close()
        self._ctx.term()
        logger.info("ZMQ client stopped")

    async def send_command(self, topic: str, payload: dict):
        """Send a command on the PUB socket."""
        if self._pub_sock is None:
            logger.error("PUB socket not initialised")
            return
        ts = struct.pack("!Q", time.time_ns())
        data = msgpack.packb(payload, use_bin_type=True)
        await self._pub_sock.send_multipart([topic.encode(), ts, data])

    # ------------------------------------------------------------------ #
    # Subscriber loops                                                     #
    # ------------------------------------------------------------------ #

    async def _status_loop(self):
        sock = self._ctx.socket(zmq.SUB)
        sock.connect(settings.zmq_status_addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        warned = False
        logger.info("Status subscriber connected to %s", settings.zmq_status_addr)
        try:
            while True:
                try:
                    parts = await asyncio.wait_for(sock.recv_multipart(), timeout=5.0)
                    warned = False
                    if len(parts) < 2:
                        continue
                    ts_bytes, payload = parts[0], parts[1]
                    timestamp_ns = struct.unpack("!Q", ts_bytes)[0]
                    data = msgpack.unpackb(payload, raw=False)

                    # Normalise odometry which may arrive as nested dicts or lists
                    odom_raw = data.get("odometry", {})
                    if isinstance(odom_raw, dict):
                        pose_raw = odom_raw.get("pose", {})
                        twist_raw = odom_raw.get("twist", {})
                    else:
                        pose_raw = {}
                        twist_raw = {}

                    odometry = {
                        "pose": {
                            "x": float(pose_raw.get("x", 0)),
                            "y": float(pose_raw.get("y", 0)),
                            "theta": float(pose_raw.get("theta", 0)),
                        },
                        "twist": {
                            "linear": float(twist_raw.get("linear", 0)),
                            "angular": float(twist_raw.get("angular", 0)),
                        },
                    }

                    status_msg = {
                        "type": "status",
                        "timestamp_ns": timestamp_ns,
                        "is_charging": bool(data.get("is_charging", False)),
                        "is_low_voltage": bool(data.get("is_low_voltage", False)),
                        "runstop": bool(data.get("runstop", False)),
                        "odometry": odometry,
                        "joint_positions": list(data.get("joint_positions", [0.0] * 10)),
                    }

                    import json
                    if self._broadcast_cb:
                        await self._broadcast_cb(json.dumps(status_msg))
                    if self._record_status_cb:
                        self._record_status_cb(timestamp_ns, status_msg)

                except asyncio.TimeoutError:
                    if not warned:
                        logger.warning(
                            "No status messages received in 5 seconds. "
                            "Is the ZMQ driver running?"
                        )
                        warned = True
                except Exception as e:
                    logger.error("Status loop error: %s", e)

        except asyncio.CancelledError:
            pass
        finally:
            sock.close()

    async def _arducam_loop(self):
        sock = self._ctx.socket(zmq.SUB)
        sock.connect(settings.zmq_arducam_addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info("Arducam subscriber connected to %s", settings.zmq_arducam_addr)
        try:
            while True:
                try:
                    parts = await asyncio.wait_for(sock.recv_multipart(), timeout=5.0)
                    if len(parts) < 2:
                        continue
                    ts_bytes, payload = parts[0], parts[1]
                    timestamp_ns = struct.unpack("!Q", ts_bytes)[0]

                    if settings.arducam_compressed:
                        import blosc2
                        raw = blosc2.decompress(payload)
                    else:
                        raw = payload

                    frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                        settings.arducam_height, settings.arducam_width, 3
                    )
                    jpeg = self._encode_jpeg_rgb(frame)
                    msg = encode_camera_frame(CAMERA_ID_ARDUCAM, timestamp_ns, jpeg)

                    if self._broadcast_cb:
                        await self._broadcast_cb(msg)
                    if self._record_camera_cb:
                        self._record_camera_cb(CAMERA_ID_ARDUCAM, timestamp_ns, frame)

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.error("Arducam loop error: %s", e)

        except asyncio.CancelledError:
            pass
        finally:
            sock.close()

    async def _d435i_loop(self):
        sock = self._ctx.socket(zmq.SUB)
        sock.connect(settings.zmq_d435if_addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"rgb")
        sock.setsockopt(zmq.SUBSCRIBE, b"depth")
        logger.info("D435i subscriber connected to %s", settings.zmq_d435if_addr)
        try:
            while True:
                try:
                    parts = await asyncio.wait_for(sock.recv_multipart(), timeout=5.0)
                    if len(parts) < 3:
                        continue
                    topic, ts_bytes, payload = parts[0], parts[1], parts[2]
                    timestamp_ns = struct.unpack("!Q", ts_bytes)[0]

                    if settings.d435if_compressed:
                        import blosc2
                        raw = blosc2.decompress(payload)
                    else:
                        raw = payload

                    if topic == b"rgb":
                        frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                            settings.realsense_height, settings.realsense_width, 3
                        )
                        jpeg = self._encode_jpeg_rgb(frame)
                        msg = encode_camera_frame(CAMERA_ID_D435I_RGB, timestamp_ns, jpeg)
                        if self._broadcast_cb:
                            await self._broadcast_cb(msg)
                        if self._record_camera_cb:
                            self._record_camera_cb(CAMERA_ID_D435I_RGB, timestamp_ns, frame)

                    elif topic == b"depth":
                        frame = np.frombuffer(raw, dtype=np.uint16).reshape(
                            settings.realsense_height, settings.realsense_width
                        )
                        heatmap = cv2.applyColorMap(
                            cv2.convertScaleAbs(frame, alpha=0.03), cv2.COLORMAP_JET
                        )
                        _, jpeg_buf = cv2.imencode(
                            ".jpg", heatmap, [cv2.IMWRITE_JPEG_QUALITY, 85]
                        )
                        jpeg = jpeg_buf.tobytes()
                        msg = encode_camera_frame(CAMERA_ID_D435I_DEPTH, timestamp_ns, jpeg)
                        if self._broadcast_cb:
                            await self._broadcast_cb(msg)
                        if self._record_camera_cb:
                            self._record_camera_cb(CAMERA_ID_D435I_DEPTH, timestamp_ns, frame)

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.error("D435i loop error: %s", e)

        except asyncio.CancelledError:
            pass
        finally:
            sock.close()

    async def _d405_loop(self):
        sock = self._ctx.socket(zmq.SUB)
        sock.connect(settings.zmq_d405_addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"rgb")
        sock.setsockopt(zmq.SUBSCRIBE, b"depth")
        logger.info("D405 subscriber connected to %s", settings.zmq_d405_addr)
        try:
            while True:
                try:
                    parts = await asyncio.wait_for(sock.recv_multipart(), timeout=5.0)
                    if len(parts) < 3:
                        continue
                    topic, ts_bytes, payload = parts[0], parts[1], parts[2]
                    timestamp_ns = struct.unpack("!Q", ts_bytes)[0]

                    if settings.d405_compressed:
                        import blosc2
                        raw = blosc2.decompress(payload)
                    else:
                        raw = payload

                    if topic == b"rgb":
                        frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                            settings.realsense_height, settings.realsense_width, 3
                        )
                        jpeg = self._encode_jpeg_rgb(frame)
                        msg = encode_camera_frame(CAMERA_ID_D405_RGB, timestamp_ns, jpeg)
                        if self._broadcast_cb:
                            await self._broadcast_cb(msg)
                        if self._record_camera_cb:
                            self._record_camera_cb(CAMERA_ID_D405_RGB, timestamp_ns, frame)

                    elif topic == b"depth":
                        frame = np.frombuffer(raw, dtype=np.uint16).reshape(
                            settings.realsense_height, settings.realsense_width
                        )
                        heatmap = cv2.applyColorMap(
                            cv2.convertScaleAbs(frame, alpha=0.03), cv2.COLORMAP_JET
                        )
                        _, jpeg_buf = cv2.imencode(
                            ".jpg", heatmap, [cv2.IMWRITE_JPEG_QUALITY, 85]
                        )
                        jpeg = jpeg_buf.tobytes()
                        msg = encode_camera_frame(CAMERA_ID_D405_DEPTH, timestamp_ns, jpeg)
                        if self._broadcast_cb:
                            await self._broadcast_cb(msg)
                        if self._record_camera_cb:
                            self._record_camera_cb(CAMERA_ID_D405_DEPTH, timestamp_ns, frame)

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.error("D405 loop error: %s", e)

        except asyncio.CancelledError:
            pass
        finally:
            sock.close()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _encode_jpeg_rgb(self, frame: np.ndarray) -> bytes:
        """Convert RGB numpy array to JPEG bytes."""
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, jpeg_buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return jpeg_buf.tobytes()
