#!/usr/bin/env python3
"""Unify a split recording directory into a single .h5 file.

Handles two directory layouts produced by the recorder:

  New layout (status.h5):
    <session>/
      arducam_rgb.h5, d435i_rgb.h5, d435i_depth.h5, d405_rgb.h5, d405_depth.h5
      status.h5  — contains joint_states/ and odometry/ groups

  Old layout (separate files):
    <session>/
      arducam_rgb.h5, d435i_rgb.h5, ...
      joint_states.h5  — timestamps + positions at root
      odometry.h5      — timestamps + x/y/theta/linear/angular at root

Output: <session>.h5 (sibling of the directory) with the layout expected by
align_recording.py (old single-file format):
    {cam}/timestamps, {cam}/frames
    joint_states/timestamps, joint_states/positions
    odometry/timestamps, odometry/x, odometry/y, odometry/theta,
             odometry/linear, odometry/angular

Usage:
    uv run python scripts/unify_recording.py <recording_dir> [--output <path>]
"""

import argparse
import sys
from pathlib import Path

import h5py

CAMERAS = ["arducam_rgb", "d435i_rgb", "d435i_depth", "d405_rgb", "d405_depth"]
ODOMETRY_FIELDS = ["timestamps", "x", "y", "theta", "linear", "angular"]


def _copy_camera(src_path: Path, cam: str, dst: h5py.File) -> bool:
    """Copy timestamps and frames from a camera .h5 file into dst[cam/]."""
    cam_path = src_path / f"{cam}.h5"
    if not cam_path.exists():
        return False
    with h5py.File(cam_path, "r") as src:
        grp = dst.require_group(cam)
        src.copy("timestamps", grp)
        src.copy("frames", grp)
    return True


def _copy_status_new(status_path: Path, dst: h5py.File) -> None:
    """Copy joint_states and odometry from new-layout status.h5."""
    with h5py.File(status_path, "r") as src:
        src.copy("joint_states", dst)
        if "odometry" in src:
            src.copy("odometry", dst)


def _copy_status_old(src_path: Path, dst: h5py.File) -> None:
    """Reconstruct joint_states/ and odometry/ groups from old separate files."""
    js_path = src_path / "joint_states.h5"
    if js_path.exists():
        with h5py.File(js_path, "r") as src:
            js_grp = dst.require_group("joint_states")
            src.copy("timestamps", js_grp)
            src.copy("positions", js_grp)

    odom_path = src_path / "odometry.h5"
    if odom_path.exists():
        with h5py.File(odom_path, "r") as src:
            odom_grp = dst.require_group("odometry")
            for field in ODOMETRY_FIELDS:
                if field in src:
                    src.copy(field, odom_grp)


def unify_recording(input_dir: Path, output_path: Path | None = None) -> Path:
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        output_path = input_dir.parent / f"{input_dir.name}.h5"

    if output_path.exists():
        print(f"Error: output already exists: {output_path}", file=sys.stderr)
        sys.exit(1)

    has_status = (input_dir / "status.h5").exists()
    has_joint_states = (input_dir / "joint_states.h5").exists()

    if not has_status and not has_joint_states:
        print(
            f"Error: neither status.h5 nor joint_states.h5 found in {input_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    layout = "new" if has_status else "old"
    print(f"Input:  {input_dir}  (layout: {layout})")
    print(f"Output: {output_path}")

    with h5py.File(output_path, "w") as dst:
        # Copy cameras
        for cam in CAMERAS:
            ok = _copy_camera(input_dir, cam, dst)
            if ok:
                n = dst[cam]["timestamps"].shape[0]
                print(f"  copied {cam}: {n} frames")
            else:
                print(f"  skip {cam} (not found)")

        # Copy status / joint_states + odometry
        if layout == "new":
            _copy_status_new(input_dir / "status.h5", dst)
        else:
            _copy_status_old(input_dir, dst)

        if "joint_states" in dst:
            n = dst["joint_states"]["timestamps"].shape[0]
            print(f"  copied joint_states: {n} samples")
        if "odometry" in dst:
            n = dst["odometry"]["timestamps"].shape[0]
            print(f"  copied odometry: {n} samples")

    print(f"Written: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Merge a split recording directory into a single .h5 file."
    )
    parser.add_argument(
        "recording_dir",
        type=Path,
        help="Path to the recording directory (e.g. recordings/20260323_200731)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .h5 path (default: <parent>/<session>.h5)",
    )
    args = parser.parse_args()

    if not args.recording_dir.exists():
        print(f"Error: {args.recording_dir} not found", file=sys.stderr)
        sys.exit(1)

    unify_recording(args.recording_dir, args.output)


if __name__ == "__main__":
    main()
