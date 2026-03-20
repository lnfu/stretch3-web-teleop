#!/usr/bin/env python3
"""Generate a preview MP4 from a recorded HDF5 camera file.

Usage:
    uv run python scripts/make_preview.py <recording_dir> <camera> [options]

Camera choices:
    arducam_rgb, d435i_rgb, d435i_depth, d405_rgb, d405_depth

Examples:
    uv run python scripts/make_preview.py recordings/20260320_170326 d405_rgb
    uv run python scripts/make_preview.py recordings/20260320_170326 d435i_depth --colormap TURBO
    uv run python scripts/make_preview.py recordings/20260320_170326 d405_rgb -o /tmp/out.mp4
"""

import argparse
import sys
from pathlib import Path

import cv2
import h5py
import numpy as np

CAMERA_FILES = {
    "arducam_rgb": "arducam_rgb.h5",
    "d435i_rgb": "d435i_rgb.h5",
    "d435i_depth": "d435i_depth.h5",
    "d405_rgb": "d405_rgb.h5",
    "d405_depth": "d405_depth.h5",
}

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
    recording_dir: Path,
    camera: str,
    output: Path | None,
    colormap_name: str,
    fps: float | None,
) -> Path:
    h5_path = recording_dir / CAMERA_FILES[camera]
    if not h5_path.exists():
        print(f"Error: {h5_path} not found", file=sys.stderr)
        sys.exit(1)

    is_depth = camera in DEPTH_CAMERAS
    colormap = COLORMAPS[colormap_name]

    with h5py.File(h5_path, "r") as f:
        timestamps = f["timestamps"][:]
        n_frames = len(timestamps)
        if n_frames == 0:
            print("Error: no frames in file", file=sys.stderr)
            sys.exit(1)

        if fps is None:
            duration_s = (timestamps[-1] - timestamps[0]) / 1e9
            fps = n_frames / duration_s if duration_s > 0 else 30.0

        first_frame = f["frames"][0]

    # Determine output size (h5 frames are H×W or H×W×3)
    h, w = first_frame.shape[:2]

    if output is None:
        preview_dir = recording_dir / "preview"
        preview_dir.mkdir(exist_ok=True)
        output = preview_dir / f"{camera}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (w, h))

    print(f"Writing {n_frames} frames at {fps:.1f} fps → {output}")

    with h5py.File(h5_path, "r") as f:
        frames_ds = f["frames"]
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
        description="Generate a preview MP4 from a recorded HDF5 camera file."
    )
    parser.add_argument("recording_dir", type=Path, help="Path to the recording directory")
    parser.add_argument(
        "camera",
        choices=list(CAMERA_FILES.keys()),
        help="Camera stream to render",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: <recording_dir>/preview/<camera>.mp4)",
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
        recording_dir=args.recording_dir,
        camera=args.camera,
        output=args.output,
        colormap_name=args.colormap,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
