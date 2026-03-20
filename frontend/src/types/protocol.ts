export type CameraId = 'arducam' | 'd435i_rgb' | 'd435i_depth' | 'd405_rgb' | 'd405_depth'

export const CAMERA_ID_MAP: Record<number, CameraId> = {
  0x00: 'arducam',
  0x01: 'd435i_rgb',
  0x02: 'd435i_depth',
  0x03: 'd405_rgb',
  0x04: 'd405_depth',
}

export interface Pose2D {
  x: number
  y: number
  theta: number
}

export interface Twist2D {
  linear: number
  angular: number
}

export interface Odometry {
  pose: Pose2D
  twist: Twist2D
}

export interface RobotStatus {
  type: 'status'
  timestamp_ns: number
  is_charging: boolean
  is_low_voltage: boolean
  runstop: boolean
  odometry: Odometry
  joint_positions: number[]
}

export interface RecordingState {
  type: 'recording_state'
  recording: boolean
  session: string | null
}
