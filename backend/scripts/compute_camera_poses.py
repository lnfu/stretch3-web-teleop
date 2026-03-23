#!/usr/bin/env python3
"""Compute per-frame camera poses for an aligned recording.

For each timestep in the aligned HDF5, computes the 4x4 transformation matrix
(camera pose relative to base_link) for every camera using pinocchio FK on the
camera_chain.urdf.  The result is written as a new dataset `camera_pose` of
shape (N, 4, 4) float64 inside each camera's group.

Usage:
    uv run python scripts/compute_camera_poses.py <session_aligned.h5>

Output:
    <same_dir>/<stem>_with_poses.h5
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import pinocchio as pin

URDF_PATH = Path(__file__).parent.parent / "data" / "camera_chain.urdf"

# Mapping from HDF5 camera group name → EE frame in camera_chain.urdf.
# RGB and depth share the same optical frame (driver already aligned them).
CAMERA_EE_FRAME: dict[str, str] = {
    "d405_rgb": "gripper_camera_color_optical_frame",
    "d405_depth": "gripper_camera_color_optical_frame",
    "d435i_rgb": "camera_color_optical_frame",
    "d435i_depth": "camera_color_optical_frame",
    "arducam_rgb": "link_head_nav_cam",
}

# joint_states/positions column layout (10 values):
#   [0] base_translate   [1] base_rotate
#   [2] lift             [3] arm_total_extension
#   [4] head_pan         [5] head_tilt
#   [6] wrist_yaw        [7] wrist_pitch
#   [8] wrist_roll       [9] stretch_gripper
_POS_LIFT = 2
_POS_ARM = 3
_POS_HEAD_PAN = 4
_POS_HEAD_TILT = 5
_POS_WRIST_YAW = 6
_POS_WRIST_PITCH = 7
_POS_WRIST_ROLL = 8


def _positions_to_joint_dict(pos: np.ndarray) -> dict[str, float]:
    arm_per_seg = float(pos[_POS_ARM]) / 4.0
    return {
        "joint_lift": float(pos[_POS_LIFT]),
        "joint_arm_l3": arm_per_seg,
        "joint_arm_l2": arm_per_seg,
        "joint_arm_l1": arm_per_seg,
        "joint_arm_l0": arm_per_seg,
        "joint_head_pan": float(pos[_POS_HEAD_PAN]),
        "joint_head_tilt": float(pos[_POS_HEAD_TILT]),
        "joint_wrist_yaw": float(pos[_POS_WRIST_YAW]),
        "joint_wrist_pitch": float(pos[_POS_WRIST_PITCH]),
        "joint_wrist_roll": float(pos[_POS_WRIST_ROLL]),
    }


class _PinModel:
    def __init__(self, urdf_path: str) -> None:
        self.model = pin.buildModelFromUrdf(urdf_path)
        self.data = self.model.createData()
        self.q = pin.neutral(self.model)
        self._base_frame_id = self.model.getFrameId("base_link")

    def update(self, joint_positions: dict[str, float]) -> None:
        for name, value in joint_positions.items():
            if not self.model.existJointName(name):
                continue
            jid = self.model.getJointId(name)
            self.q[self.model.joints[jid].idx_q] = value
        pin.forwardKinematics(self.model, self.data, self.q)
        pin.updateFramePlacements(self.model, self.data)

    def pose_in_base(self, frame_name: str) -> np.ndarray:
        """4x4 homogeneous transform: camera pose expressed in base_link frame."""
        cam_id = self.model.getFrameId(frame_name)
        T_world_base = self.data.oMf[self._base_frame_id]
        T_world_cam = self.data.oMf[cam_id]
        return (T_world_base.inverse() * T_world_cam).homogeneous


def compute_camera_poses(h5_path: Path) -> Path:
    out_path = h5_path.parent / f"{h5_path.stem}_with_poses.h5"

    model = _PinModel(str(URDF_PATH))

    with h5py.File(h5_path, "r") as src, h5py.File(out_path, "w") as dst:
        # Copy every existing group/dataset verbatim.
        for key in src:
            src.copy(key, dst)

        joint_pos_all = src["joint_states/positions"][:]
        n = joint_pos_all.shape[0]

        present_cameras = [cam for cam in CAMERA_EE_FRAME if cam in src]
        if not present_cameras:
            print("No known camera groups found in the input file.", file=sys.stderr)
            sys.exit(1)

        # Compute FK for unique EE frames; cameras sharing a frame reuse the result.
        unique_ee_frames = {CAMERA_EE_FRAME[cam] for cam in present_cameras}
        poses: dict[str, np.ndarray] = {
            frame: np.empty((n, 4, 4), dtype=np.float64) for frame in unique_ee_frames
        }

        print(f"Computing FK for {n} frames, {len(unique_ee_frames)} unique EE frame(s)...")
        for i, pos in enumerate(joint_pos_all):
            model.update(_positions_to_joint_dict(pos))
            for frame in unique_ee_frames:
                poses[frame][i] = model.pose_in_base(frame)
            if (i + 1) % 200 == 0 or i + 1 == n:
                print(f"  {i + 1}/{n}")

        for cam in present_cameras:
            ee_frame = CAMERA_EE_FRAME[cam]
            dst[cam].create_dataset("camera_pose", data=poses[ee_frame])
            print(f"  {cam}/camera_pose  ← {ee_frame}")

    print(f"Written: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute per-frame camera poses (T_base_to_camera) for an aligned recording."
    )
    parser.add_argument("recording", type=Path, help="Path to the *_aligned.h5 file")
    args = parser.parse_args()

    if not args.recording.exists():
        print(f"Error: {args.recording} not found", file=sys.stderr)
        sys.exit(1)

    compute_camera_poses(args.recording)


if __name__ == "__main__":
    main()
