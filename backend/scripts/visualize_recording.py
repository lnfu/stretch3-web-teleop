#!/usr/bin/env python3
"""Visualize an aligned HDF5 recording with rerun.io.

Logs 3D camera-frame axes (X/Y/Z arrows), RGB images, and depth images
on a real nanosecond timestamp timeline.

Usage:
    uv run python scripts/visualize_recording.py <path_to_h5_with_poses>
"""

import argparse
from pathlib import Path

import h5py
import numpy as np
import rerun as rr

CAMERAS_RGB = ["arducam_rgb", "d405_rgb", "d435i_rgb"]
CAMERAS_DEPTH = ["d405_depth", "d435i_depth"]

# RGB cameras that also have a matching depth camera group.
DEPTH_PAIR = {"d405_rgb": "d405_depth", "d435i_rgb": "d435i_depth"}

ARROW_LENGTH = 0.08  # metres – length of each axis arrow

# X=red, Y=green, Z=blue (ROS / standard convention)
AXIS_COLORS = np.array([[220, 50, 50], [50, 200, 50], [50, 100, 220]], dtype=np.uint8)
AXIS_LABELS = ["X", "Y", "Z"]


def log_world_origin() -> None:
    """Log a static world-origin coordinate frame."""
    origins = np.zeros((3, 3), dtype=np.float32)
    vectors = np.eye(3, dtype=np.float32) * ARROW_LENGTH * 1.5
    rr.log(
        "world/origin",
        rr.Arrows3D(
            origins=origins,
            vectors=vectors,
            colors=AXIS_COLORS,
            radii=0.006,
            labels=AXIS_LABELS,
        ),
        static=True,
    )


def log_frame(
    ts_ns: int,
    frame_idx: int,
    data: dict,
    present_rgb: list[str],
    present_depth: list[str],
) -> None:
    """Log all data for one timestep."""
    rr.set_time("timestamp", timestamp=np.datetime64(int(ts_ns), "ns"))
    rr.set_time("frame", sequence=frame_idx)

    for cam in present_rgb:
        T: np.ndarray = data[cam]["poses"][frame_idx]  # (4, 4)
        origin = T[:3, 3].astype(np.float32)
        R = T[:3, :3].astype(np.float32)

        # --- 3D transform: position + orientation as three axis arrows ---
        origins = np.vstack([origin, origin, origin])
        vectors = np.column_stack([R[:, 0], R[:, 1], R[:, 2]]).T * ARROW_LENGTH

        rr.log(
            f"world/{cam}/axes",
            rr.Arrows3D(
                origins=origins,
                vectors=vectors,
                colors=AXIS_COLORS,
                radii=0.004,
                labels=AXIS_LABELS,
            ),
        )

        # Also log Transform3D so the entity tree reflects the pose.
        rr.log(
            f"world/{cam}",
            rr.Transform3D(translation=origin, mat3x3=R),
        )

        # --- RGB image ---
        rgb = data[cam]["frames"][frame_idx]
        rr.log(f"world/{cam}/rgb", rr.Image(rgb, color_model="RGB"))

    for cam in present_depth:
        depth = data[cam]["frames"][frame_idx]  # H x W uint16, millimetres
        rr.log(
            f"world/{cam}/depth",
            rr.DepthImage(depth, meter=1000.0),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize aligned HDF5 recording with 3D poses via rerun.io."
    )
    parser.add_argument("h5_path", type=Path, help="Path to *_with_poses.h5 file")
    parser.add_argument(
        "--save",
        metavar="FILE.rrd",
        help="Save to .rrd file instead of opening the viewer",
    )
    args = parser.parse_args()

    if not args.h5_path.exists():
        raise SystemExit(f"File not found: {args.h5_path}")

    print(f"Loading {args.h5_path} …")
    with h5py.File(args.h5_path, "r") as f:
        timestamps: np.ndarray = f["timestamps"][:]  # uint64 nanoseconds

        data: dict = {}
        present_rgb: list[str] = []
        present_depth: list[str] = []

        for cam in CAMERAS_RGB:
            if cam not in f:
                print(f"  skip {cam} (not in file)")
                continue
            grp = f[cam]
            if "camera_pose" not in grp:
                print(f"  skip {cam} (no camera_pose – run compute_camera_poses.py first)")
                continue
            data[cam] = {
                "frames": grp["frames"][:],
                "poses": grp["camera_pose"][:],
            }
            present_rgb.append(cam)

        for cam in CAMERAS_DEPTH:
            if cam not in f:
                continue
            data[cam] = {"frames": f[cam]["frames"][:]}
            present_depth.append(cam)

    n_frames = len(timestamps)
    print(f"  {n_frames} frames, {len(present_rgb)} RGB cameras, {len(present_depth)} depth cameras")

    # --- Initialise rerun ---
    rr_kwargs: dict = {}
    if args.save:
        rr_kwargs["default_blueprint"] = None  # will be saved as-is
        rr.init("stretch3_recording", **rr_kwargs)
        rr.save(args.save)
        print(f"Saving to {args.save}")
    else:
        rr.init("stretch3_recording", spawn=True)

    log_world_origin()

    print("Logging frames …")
    for i, ts in enumerate(timestamps):
        log_frame(int(ts), i, data, present_rgb, present_depth)
        if (i + 1) % 50 == 0 or i + 1 == n_frames:
            print(f"  {i + 1}/{n_frames}")

    print("Done. Rerun viewer should be open.")


if __name__ == "__main__":
    main()
