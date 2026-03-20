<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton } from 'naive-ui'
import { useRobotStore } from '../stores/robotStore'
import { sendMessage } from '../composables/useWebSocket'

const robotStore = useRobotStore()

// Gripper uses a different unit between status and command, so cache the last sent command value
const lastGripperCmd = ref(0)

interface JointDef {
  index: number
  name: string
  unit: string
  step: number
}

// 9 joints (gripper handled separately below), 5 cols × 2 rows with 1 empty cell at end
const JOINTS: JointDef[] = [
  { index: 0, name: 'base_trans',  unit: 'm',   step: 0.05 },
  { index: 2, name: 'lift',        unit: 'm',   step: 0.05 },
  { index: 3, name: 'arm',         unit: 'm',   step: 0.02 },
  { index: 6, name: 'wrist_yaw',   unit: 'rad', step: 0.1  },
  { index: 4, name: 'head_pan',    unit: 'rad', step: 0.1  },
  { index: 1, name: 'base_rot',    unit: 'rad', step: 0.1  },
  { index: 7, name: 'wrist_pitch', unit: 'rad', step: 0.1  },
  { index: 8, name: 'wrist_roll',  unit: 'rad', step: 0.1  },
  { index: 5, name: 'head_tilt',   unit: 'rad', step: 0.1  },
]

const GRIPPER_PRESETS = [-10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

const gripperStatus = computed(() =>
  (robotStore.status?.joint_positions[9] ?? 0).toFixed(3),
)

function adjust(jointIndex: number, delta: number) {
  const positions = [...robotStore.jointPositions] as number[]
  positions[jointIndex] = (positions[jointIndex] ?? 0) + delta
  positions[9] = lastGripperCmd.value
  sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
}

function setGripper(val: number) {
  lastGripperCmd.value = val
  const positions = [...robotStore.jointPositions] as number[]
  positions[9] = val
  sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
}

function value(index: number): string {
  return (robotStore.jointPositions[index] ?? 0).toFixed(3)
}
</script>

<template>
  <div class="px-4 py-3 flex flex-col gap-3">
    <!-- 9 regular joints: 5-column grid -->
    <div class="grid grid-cols-5 gap-x-4 gap-y-3">
      <div v-for="j in JOINTS" :key="j.index" class="flex flex-col gap-1">
        <span class="text-[0.65rem] text-gray-400 leading-none tracking-wide">{{ j.name }}</span>
        <div class="flex items-center gap-1.5">
          <NButton size="small" class="shrink-0" @click="adjust(j.index, -j.step)">−</NButton>
          <span class="flex-1 text-center text-xs font-mono">
            {{ value(j.index) }}<span class="text-gray-500 ml-0.5">{{ j.unit }}</span>
          </span>
          <NButton size="small" class="shrink-0" @click="adjust(j.index, j.step)">+</NButton>
        </div>
      </div>
    </div>

    <!-- Gripper: preset buttons + status value -->
    <div class="flex items-center gap-3 pt-1 border-t border-gray-800">
      <div class="flex flex-col shrink-0 w-16">
        <span class="text-[0.65rem] text-gray-400 leading-none tracking-wide">gripper</span>
        <span class="font-mono text-xs text-gray-300 mt-0.5">{{ gripperStatus }}</span>
      </div>
      <div class="flex gap-1 flex-wrap">
        <NButton
          v-for="val in GRIPPER_PRESETS"
          :key="val"
          size="small"
          @click="setGripper(val)"
        >
          {{ val }}
        </NButton>
      </div>
    </div>
  </div>
</template>
