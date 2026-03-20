<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useRobotStore } from '../stores/robotStore'
import { sendMessage } from '../composables/useWebSocket'

const robotStore = useRobotStore()

interface JointDef {
  index: number
  name: string
  unit: string
  step: number
}

// 5 cols × 2 rows — grouped by function column-wise:
// col1: base | col2: arm vertical | col3: arm extend+wrist | col4: wrist rotation | col5: head
const JOINTS: JointDef[] = [
  { index: 0, name: 'base_trans',  unit: 'm',   step: 0.05 },
  { index: 2, name: 'lift',        unit: 'm',   step: 0.05 },
  { index: 3, name: 'arm',         unit: 'm',   step: 0.02 },
  { index: 6, name: 'wrist_yaw',   unit: 'rad', step: 0.1  },
  { index: 4, name: 'head_pan',    unit: 'rad', step: 0.1  },
  { index: 1, name: 'base_rot',    unit: 'rad', step: 0.1  },
  { index: 9, name: 'gripper',     unit: '',    step: 0.05 },
  { index: 7, name: 'wrist_pitch', unit: 'rad', step: 0.1  },
  { index: 8, name: 'wrist_roll',  unit: 'rad', step: 0.1  },
  { index: 5, name: 'head_tilt',   unit: 'rad', step: 0.1  },
]

function adjust(jointIndex: number, delta: number) {
  const positions = [...robotStore.jointPositions] as number[]
  positions[jointIndex] = (positions[jointIndex] ?? 0) + delta
  sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
}

function value(index: number): string {
  return (robotStore.jointPositions[index] ?? 0).toFixed(3)
}
</script>

<template>
  <div class="px-4 py-3">
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
  </div>
</template>
