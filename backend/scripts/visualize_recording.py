#!/usr/bin/env python3
"""Visualize an aligned HDF5 recording file.

Usage:
    uv run python scripts/visualize_recording.py <path_to_h5>

Navigation:
    n / Right arrow  - next frame
    p / Left arrow   - previous frame
    q / Esc          - quit
"""

import sys
import argparse
import numpy as np
import cv2
import h5py


DEPTH_COLORMAP = cv2.COLORMAP_PLASMA
WINDOW_NAME = "Recording Viewer"
PANEL_WIDTH = 640
PANEL_HEIGHT = 480
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.45
FONT_COLOR = (255, 255, 255)
FONT_THICKNESS = 1
TEXT_BG_COLOR = (30, 30, 30)


def colorize_depth(depth_frame: np.ndarray) -> np.ndarray:
    """Convert uint16 depth to a BGR colormap image."""
    valid = depth_frame[depth_frame > 0]
    if valid.size == 0:
        return np.zeros((*depth_frame.shape, 3), dtype=np.uint8)
    d_min, d_max = valid.min(), valid.max()
    norm = np.zeros_like(depth_frame, dtype=np.float32)
    if d_max > d_min:
        mask = depth_frame > 0
        norm[mask] = (depth_frame[mask] - d_min) / (d_max - d_min) * 255.0
    norm_u8 = norm.astype(np.uint8)
    colored = cv2.applyColorMap(norm_u8, DEPTH_COLORMAP)
    return colored


def resize_to(img: np.ndarray, w: int, h: int) -> np.ndarray:
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def draw_text_box(img: np.ndarray, lines: list[str], origin: tuple[int, int]) -> None:
    """Draw multi-line text with a semi-transparent background."""
    x, y = origin
    line_h = 18
    pad = 4
    max_w = max(cv2.getTextSize(l, FONT, FONT_SCALE, FONT_THICKNESS)[0][0] for l in lines)
    box_h = line_h * len(lines) + pad * 2
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y - pad), (x + max_w + pad * 2, y + box_h), TEXT_BG_COLOR, -1)
    cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (x + pad, y + i * line_h + line_h - 2),
                    FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, cv2.LINE_AA)


def pose_to_lines(label: str, pose: np.ndarray) -> list[str]:
    lines = [f"--- {label} pose ---"]
    for row in pose:
        lines.append(f"  {row[0]:+7.3f}  {row[1]:+7.3f}  {row[2]:+7.3f}  {row[3]:+7.3f}")
    pos = pose[:3, 3]
    lines.append(f"  xyz: ({pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:+.3f}) m")
    return lines


def build_frame(data: dict, frame_idx: int, n_frames: int) -> np.ndarray:
    panels = []

    # --- RGB panels ---
    for cam, label in [("arducam_rgb", "Arducam RGB"),
                        ("d405_rgb", "D405 RGB"),
                        ("d435i_rgb", "D435i RGB")]:
        rgb = data[cam]["frames"][frame_idx]   # H x W x 3 uint8
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        bgr = resize_to(bgr, PANEL_WIDTH, PANEL_HEIGHT)
        draw_text_box(bgr, [label, f"frame {frame_idx + 1}/{n_frames}"], (4, 4))
        panels.append(bgr)

    # --- Depth panels ---
    for cam, label in [("d405_depth", "D405 Depth"),
                        ("d435i_depth", "D435i Depth")]:
        depth = data[cam]["frames"][frame_idx]   # H x W uint16
        colored = colorize_depth(depth)
        colored = resize_to(colored, PANEL_WIDTH, PANEL_HEIGHT)
        draw_text_box(colored, [label, f"frame {frame_idx + 1}/{n_frames}"], (4, 4))
        panels.append(colored)

    # --- Camera pose text panel ---
    pose_panel = np.full((PANEL_HEIGHT, PANEL_WIDTH, 3), 20, dtype=np.uint8)
    y_cursor = 6
    for cam, label in [("arducam_rgb", "arducam_rgb"),
                        ("d405_rgb", "d405"),
                        ("d435i_rgb", "d435i")]:
        pose = data[cam]["poses"][frame_idx]
        lines = pose_to_lines(label, pose)
        for line in lines:
            cv2.putText(pose_panel, line, (6, y_cursor + 14),
                        FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
            y_cursor += 16
        y_cursor += 4
    draw_text_box(pose_panel, ["Camera Poses (world→cam, meters)"], (4, 4))
    panels.append(pose_panel)

    # Arrange into a 2-row grid: top row [arducam, d405_rgb, d435i_rgb]
    #                            bot row [d405_depth, d435i_depth, pose]
    row0 = np.hstack(panels[0:3])
    row1 = np.hstack(panels[3:6])
    return np.vstack([row0, row1])


def main():
    parser = argparse.ArgumentParser(description="Visualize aligned HDF5 recording.")
    parser.add_argument("h5_path", help="Path to aligned HDF5 file")
    args = parser.parse_args()

    with h5py.File(args.h5_path, "r") as f:
        cameras = ["arducam_rgb", "d405_rgb", "d435i_rgb", "d405_depth", "d435i_depth"]
        data = {}
        for cam in cameras:
            group = f[cam]
            key = "frames" if "frames" in group else list(group.keys())[0]
            data[cam] = {
                "frames": group["frames"][:],
                "poses": group["camera_pose"][:],
            }
        n_frames = data["arducam_rgb"]["frames"].shape[0]

    print(f"Loaded {n_frames} frames from {args.h5_path}")
    print("Keys: n/Right = next  |  p/Left = prev  |  q/Esc = quit")

    frame_idx = 0
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, PANEL_WIDTH * 3, PANEL_HEIGHT * 2)

    while True:
        canvas = build_frame(data, frame_idx, n_frames)
        cv2.imshow(WINDOW_NAME, canvas)
        key = cv2.waitKey(0) & 0xFF

        if key in (ord('q'), 27):          # q or Esc
            break
        elif key in (ord('n'), 83):        # n or Right arrow
            frame_idx = min(frame_idx + 1, n_frames - 1)
        elif key in (ord('p'), 81):        # p or Left arrow
            frame_idx = max(frame_idx - 1, 0)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
