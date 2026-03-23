#!/usr/bin/env python3
"""Align all streams in a recording to the joint_states timeline.

Supports two input formats:
  - Directory (new): recordings/<session>/   — one .h5 file per camera + status.h5
  - Single file (old): recordings/<session>.h5 — all streams in one file

Uses merge_asof (nearest match) to find the closest sample in each stream
for every joint_states timestamp.

Usage:
    uv run python scripts/align_recording.py <recording_dir_or_h5>

Output:
    recordings/<session>_aligned.h5
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

CAMERAS = ["arducam_rgb", "d435i_rgb", "d435i_depth", "d405_rgb", "d405_depth"]
ODOMETRY_FIELDS = ["x", "y", "theta", "linear", "angular"]


def _open_camera(src_root: h5py.File | Path, cam: str):
    """Return (timestamps, frames_dataset) for a camera, handling both formats."""
    if isinstance(src_root, h5py.File):
        # Old single-file format: camera group lives inside the file
        if cam not in src_root:
            return None, None
        grp = src_root[cam]
        return grp["timestamps"][:], grp["frames"]
    else:
        # New directory format: each camera has its own .h5 file
        cam_path = src_root / f"{cam}.h5"
        if not cam_path.exists():
            return None, None
        # Caller is responsible for closing; we return an open file handle
        f = h5py.File(cam_path, "r")
        return f["timestamps"][:], f["frames"], f  # extra: file handle to close


def align_recording(input_path: Path) -> Path:
    is_dir = input_path.is_dir()

    if is_dir:
        session_name = input_path.name
        out_path = input_path.parent / f"{session_name}_aligned.h5"
        status_path = input_path / "status.h5"
        if not status_path.exists():
            print(f"Error: status.h5 not found in {input_path}", file=sys.stderr)
            sys.exit(1)
        src_status = h5py.File(status_path, "r")
    else:
        out_path = input_path.parent / f"{input_path.stem}_aligned.h5"
        src_status = h5py.File(input_path, "r")

    open_handles: list[h5py.File] = [src_status]

    try:
        js_ts = src_status["joint_states/timestamps"][:]
        js_pos = src_status["joint_states/positions"][:]
        n = len(js_ts)
        ref = pd.DataFrame({"ts": js_ts})

        print(f"Reference: {n} joint_states timestamps")

        with h5py.File(out_path, "w") as dst:
            dst.create_dataset("timestamps", data=js_ts, dtype=np.uint64)

            # Align cameras
            for cam in CAMERAS:
                if is_dir:
                    result = _open_camera(input_path, cam)
                    if result[0] is None:
                        print(f"  skip {cam} (not found)")
                        continue
                    cam_ts, cam_frames, cam_h5 = result
                    open_handles.append(cam_h5)
                else:
                    result = _open_camera(src_status, cam)
                    if result[0] is None:
                        print(f"  skip {cam} (not in file)")
                        continue
                    cam_ts, cam_frames = result

                frame_shape = cam_frames.shape[1:]
                dtype = cam_frames.dtype

                right = pd.DataFrame({"ts": cam_ts, "idx": np.arange(len(cam_ts))})
                merged = pd.merge_asof(ref, right, on="ts", direction="nearest")
                indices = merged["idx"].to_numpy()

                print(f"  aligning {cam}: {len(cam_ts)} → {n} frames")

                cam_grp = dst.require_group(cam)
                ds = cam_grp.create_dataset(
                    "frames",
                    shape=(n,) + frame_shape,
                    dtype=dtype,
                    chunks=(1,) + frame_shape,
                    compression="lzf",
                )
                for i, src_idx in enumerate(indices):
                    ds[i] = cam_frames[int(src_idx)]

            # Align odometry
            odom_src = src_status if is_dir else src_status
            if "odometry" in odom_src:
                odom_ts = odom_src["odometry/timestamps"][:]
                right = pd.DataFrame({"ts": odom_ts})
                for field in ODOMETRY_FIELDS:
                    right[field] = odom_src[f"odometry/{field}"][:]
                merged = pd.merge_asof(ref, right, on="ts", direction="nearest")

                odom_grp = dst.create_group("odometry")
                for field in ODOMETRY_FIELDS:
                    odom_grp.create_dataset(
                        field, data=merged[field].to_numpy(dtype=np.float64)
                    )
                print(f"  aligned odometry: {len(odom_ts)} → {n} samples")

            # Joint states (already on reference timeline)
            js_grp = dst.create_group("joint_states")
            js_grp.create_dataset("positions", data=js_pos, dtype=np.float64)

    finally:
        for h in open_handles:
            try:
                h.close()
            except Exception:
                pass

    print(f"Written: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Align all streams to the joint_states timeline using merge_asof."
    )
    parser.add_argument(
        "recording",
        type=Path,
        help="Path to the recording directory (new format) or .h5 file (old format)",
    )
    args = parser.parse_args()

    if not args.recording.exists():
        print(f"Error: {args.recording} not found", file=sys.stderr)
        sys.exit(1)

    align_recording(args.recording)


if __name__ == "__main__":
    main()
