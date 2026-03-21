#!/usr/bin/env python3
"""Align all streams in a recording HDF5 file to the joint_states timeline.

Uses merge_asof (nearest match) to find the closest sample in each stream
for every joint_states timestamp.

Usage:
    uv run python scripts/align_recording.py <recording.h5>

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


def align_recording(h5_path: Path) -> Path:
    out_path = h5_path.parent / f"{h5_path.stem}_aligned.h5"

    with h5py.File(h5_path, "r") as src, h5py.File(out_path, "w") as dst:
        js_ts = src["joint_states/timestamps"][:]
        js_pos = src["joint_states/positions"][:]
        n = len(js_ts)
        ref = pd.DataFrame({"ts": js_ts})

        print(f"Reference: {n} joint_states timestamps")

        dst.create_dataset("timestamps", data=js_ts, dtype=np.uint64)

        # Align cameras
        for cam in CAMERAS:
            if cam not in src:
                print(f"  skip {cam} (not in file)")
                continue

            cam_ts = src[f"{cam}/timestamps"][:]
            cam_frames = src[f"{cam}/frames"]
            frame_shape = cam_frames.shape[1:]
            dtype = cam_frames.dtype

            right = pd.DataFrame({"ts": cam_ts, "idx": np.arange(len(cam_ts))})
            merged = pd.merge_asof(ref, right, on="ts", direction="nearest")
            indices = merged["idx"].to_numpy()

            print(f"  aligning {cam}: {len(cam_ts)} → {n} frames")

            ds = dst.create_dataset(
                cam,
                shape=(n,) + frame_shape,
                dtype=dtype,
                chunks=(1,) + frame_shape,
                compression="lzf",
            )
            for i, src_idx in enumerate(indices):
                ds[i] = cam_frames[int(src_idx)]

        # Align odometry
        if "odometry" in src:
            odom_ts = src["odometry/timestamps"][:]
            right = pd.DataFrame({"ts": odom_ts})
            for field in ODOMETRY_FIELDS:
                right[field] = src[f"odometry/{field}"][:]
            merged = pd.merge_asof(ref, right, on="ts", direction="nearest")

            odom_grp = dst.create_group("odometry")
            for field in ODOMETRY_FIELDS:
                odom_grp.create_dataset(field, data=merged[field].to_numpy(dtype=np.float64))
            print(f"  aligned odometry: {len(odom_ts)} → {n} samples")

        # Joint states (already on reference timeline)
        js_grp = dst.create_group("joint_states")
        js_grp.create_dataset("positions", data=js_pos, dtype=np.float64)

    print(f"Written: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Align all streams to the joint_states timeline using merge_asof."
    )
    parser.add_argument("recording", type=Path, help="Path to the recording .h5 file")
    args = parser.parse_args()

    if not args.recording.exists():
        print(f"Error: {args.recording} not found", file=sys.stderr)
        sys.exit(1)

    align_recording(args.recording)


if __name__ == "__main__":
    main()
