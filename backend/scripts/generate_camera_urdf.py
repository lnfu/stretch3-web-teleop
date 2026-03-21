from typing import NamedTuple

import urchin


class CameraChain(NamedTuple):
    links: list[str]
    joints: list[str]


D405 = CameraChain(
    links=[
        "base_link",
        "link_mast",
        "link_lift",
        "link_arm_l4",
        "link_arm_l3",
        "link_arm_l2",
        "link_arm_l1",
        "link_arm_l0",
        "link_wrist_yaw",
        "link_wrist_yaw_bottom",
        "link_wrist_pitch",
        "link_wrist_roll",
        "link_gripper_s3_body",
        "gripper_camera_bottom_screw_frame",
        "gripper_camera_link",
        "gripper_camera_color_frame",
        "gripper_camera_color_optical_frame",
    ],
    joints=[
        "joint_mast",
        "joint_lift",
        "joint_arm_l4",
        "joint_arm_l3",
        "joint_arm_l2",
        "joint_arm_l1",
        "joint_arm_l0",
        "joint_wrist_yaw",
        "joint_wrist_yaw_bottom",
        "joint_wrist_pitch",
        "joint_wrist_roll",
        "joint_gripper_s3_body",
        "gripper_camera_joint",
        "gripper_camera_link_joint",
        "gripper_camera_color_joint",
        "gripper_camera_color_optical_joint",
    ],
)

D435IF = CameraChain(
    links=[
        "base_link",
        "link_mast",
        "link_head",
        "link_head_pan",
        "link_head_tilt",
        "camera_bottom_screw_frame",
        "camera_link",
        "camera_color_frame",
        "camera_color_optical_frame",
    ],
    joints=[
        "joint_mast",
        "joint_head",
        "joint_head_pan",
        "joint_head_tilt",
        "camera_joint",
        "camera_link_joint",
        "camera_color_joint",
        "camera_color_optical_joint",
    ],
)

ARDUCAM = CameraChain(
    links=[
        "base_link",
        "link_mast",
        "link_head",
        "link_head_pan",
        "link_head_tilt",
        "link_head_nav_cam",
    ],
    joints=[
        "joint_mast",
        "joint_head",
        "joint_head_pan",
        "joint_head_tilt",
        "joint_head_nav_cam",
    ],
)

ALL_CHAINS = [D405, D435IF, ARDUCAM]


def generate_combined_camera_urdf(
    original_urdf_path: str,
    output_urdf_path: str,
    all_chain_links: set[str],
    all_chain_joints: set[str],
):
    original_urdf = urchin.URDF.load(original_urdf_path)
    print(f"Original URDF - links: {len(original_urdf.links)}, joints: {len(original_urdf.joints)}")

    modified_urdf = original_urdf.copy()

    removed_links = [link for link in modified_urdf._links if link.name not in all_chain_links]
    removed_joints = [joint for joint in modified_urdf._joints if joint.name not in all_chain_joints]

    for link in removed_links:
        modified_urdf._links.remove(link)
    for joint in removed_joints:
        modified_urdf._joints.remove(joint)

    print(f"Combined URDF - links: {len(modified_urdf.links)}, joints: {len(modified_urdf.joints)}")
    print(f"Removed {len(removed_links)} links, {len(removed_joints)} joints")

    modified_urdf.save(output_urdf_path)
    print(f"Saved to: {output_urdf_path}")


def main():
    original_urdf_path = "./data/exported_urdf/stretch.urdf"
    output_urdf_path = "./data/camera_chain.urdf"

    all_links: set[str] = set()
    all_joints: set[str] = set()
    for chain in ALL_CHAINS:
        all_links.update(chain.links)
        all_joints.update(chain.joints)

    print(f"Union - {len(all_links)} links, {len(all_joints)} joints")

    generate_combined_camera_urdf(original_urdf_path, output_urdf_path, all_links, all_joints)
    print("\nDone!")


if __name__ == "__main__":
    main()
