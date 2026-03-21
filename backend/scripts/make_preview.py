#!/usr/bin/env python3
"""Generate a preview MP4 from a recorded HDF5 camera stream.

Usage:
    uv run python scripts/make_preview.py <recording.h5> <camera> [options]

Camera choices:
    arducam_rgb, d435i_rgb, d435i_depth, d405_rgb, d405_depth

Examples:
    uv run python scripts/make_preview.py recordings/20260320_170326.h5 d405_rgb
    uv run python scripts/make_preview.py recordings/20260320_170326.h5 d435i_depth --colormap TURBO
    uv run python scripts/make_preview.py recordings/20260320_170326.h5 d405_rgb -o /tmp/out.mp4
"""

import argparse
import sys
from pathlib import Path

import cv2
import h5py
import numpy as np

CAMERA_NAMES = [
    "arducam_rgb",
    "d435i_rgb",
    "d435i_depth",
    "d405_rgb",
    "d405_depth",
]

DEPTH_CAMERAS = {"d435i_depth", "d405_depth"}

COLORMAPS = {
    "TURBO": cv2.COLORMAP_TURBO,
    "JET": cv2.COLORMAP_JET,
    "INFERNO": cv2.COLORMAP_INFERNO,
    "PLASMA": cv2.COLORMAP_PLASMA,
    "MAGMA": cv2.COLORMAP_MAGMA,
    "HOT": cv2.COLORMAP_HOT,
}


def depth_to_heatmap(frame: np.ndarray, colormap: int) -> np.ndarray:
    """Convert a uint16 depth frame to a BGR heatmap."""
    valid = frame[frame > 0]
    if valid.size == 0:
        normalized = np.zeros(frame.shape, dtype=np.uint8)
    else:
        lo, hi = np.percentile(valid, 2), np.percentile(valid, 98)
        if hi == lo:
            normalized = np.zeros(frame.shape, dtype=np.uint8)
        else:
            clipped = np.clip(frame.astype(np.float32), lo, hi)
            normalized = ((clipped - lo) / (hi - lo) * 255).astype(np.uint8)
    return cv2.applyColorMap(normalized, colormap)


def make_preview(
    h5_path: Path,
    camera: str,
    output: Path | None,
    colormap_name: str,
    fps: float | None,
) -> Path:
    if not h5_path.exists():
        print(f"Error: {h5_path} not found", file=sys.stderr)
        sys.exit(1)

    is_depth = camera in DEPTH_CAMERAS
    colormap = COLORMAPS[colormap_name]

    with h5py.File(h5_path, "r") as f:
        if camera not in f:
            print(f"Error: group '{camera}' not found in {h5_path}", file=sys.stderr)
            sys.exit(1)

        grp = f[camera]
        timestamps = grp["timestamps"][:]
        n_frames = len(timestamps)
        if n_frames == 0:
            print("Error: no frames in file", file=sys.stderr)
            sys.exit(1)

        if fps is None:
            duration_s = (timestamps[-1] - timestamps[0]) / 1e9
            fps = n_frames / duration_s if duration_s > 0 else 30.0

        first_frame = grp["frames"][0]

    # Determine output size (h5 frames are H×W or H×W×3)
    h, w = first_frame.shape[:2]

    if output is None:
        output = h5_path.parent / f"{h5_path.stem}_preview_{camera}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (w, h))

    print(f"Writing {n_frames} frames at {fps:.1f} fps → {output}")

    with h5py.File(h5_path, "r") as f:
        frames_ds = f[camera]["frames"]
        for i in range(n_frames):
            frame = frames_ds[i]
            if is_depth:
                bgr = depth_to_heatmap(frame, colormap)
            else:
                # HDF5 stores RGB; OpenCV needs BGR
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(bgr)

            if (i + 1) % 100 == 0 or i + 1 == n_frames:
                print(f"  {i + 1}/{n_frames}", end="\r")

    writer.release()
    print(f"\nDone: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate a preview MP4 from a recorded HDF5 camera stream."
    )
    parser.add_argument("recording", type=Path, help="Path to the recording .h5 file")
    parser.add_argument(
        "camera",
        choices=CAMERA_NAMES,
        help="Camera stream to render",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: <recording_dir>/preview/<session>_<camera>.mp4)",
    )
    parser.add_argument(
        "--colormap",
        choices=list(COLORMAPS.keys()),
        default="TURBO",
        help="Colormap for depth streams (default: TURBO)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Output FPS (default: inferred from timestamps)",
    )
    args = parser.parse_args()

    make_preview(
        h5_path=args.recording,
        camera=args.camera,
        output=args.output,
        colormap_name=args.colormap,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
