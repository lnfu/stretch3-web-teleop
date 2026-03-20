import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RobotStatus } from '../types/protocol'

export const useRobotStore = defineStore('robot', () => {
  const status = ref<RobotStatus | null>(null)

  function updateStatus(s: RobotStatus) {
    status.value = s
  }

  const jointPositions = computed(
    () => status.value?.joint_positions ?? (Array(10).fill(0) as number[]),
  )

  return { status, updateStatus, jointPositions }
})
