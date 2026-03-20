import struct
import time

import msgpack

CAMERA_FRAME_TYPE = 0x01

CAMERA_ID_ARDUCAM = 0x00
CAMERA_ID_D435I_RGB = 0x01
CAMERA_ID_D435I_DEPTH = 0x02
CAMERA_ID_D405_RGB = 0x03
CAMERA_ID_D405_DEPTH = 0x04


def encode_camera_frame(camera_id: int, timestamp_ns: int, jpeg_data: bytes) -> bytes:
    """Pack binary WebSocket frame: [type:1][cam_id:1][ts:8][jpeg:N]"""
    header = struct.pack("!BBQ", CAMERA_FRAME_TYPE, camera_id, timestamp_ns)
    return header + jpeg_data


def decode_timestamp(data: bytes) -> int:
    return struct.unpack("!Q", data)[0]


def encode_msgpack(data: dict) -> bytes:
    return msgpack.packb(data, use_bin_type=True)


def decode_msgpack(data: bytes) -> dict:
    return msgpack.unpackb(data, raw=False)


def make_timestamp() -> bytes:
    return struct.pack("!Q", time.time_ns())
