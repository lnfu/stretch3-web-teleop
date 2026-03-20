<script setup lang="ts">
import { NTabs, NTabPane, NButton } from 'naive-ui'
import { useRobotStore } from '../stores/robotStore'
import { sendMessage } from '../composables/useWebSocket'

const robotStore = useRobotStore()

interface JointDef {
  index: number
  name: string
  unit: string
  step: number
}

const ALL_JOINTS: JointDef[] = [
  { index: 0, name: 'base_translate', unit: 'm', step: 0.05 },
  { index: 1, name: 'base_rotate', unit: 'rad', step: 0.1 },
  { index: 2, name: 'lift', unit: 'm', step: 0.05 },
  { index: 3, name: 'arm', unit: 'm', step: 0.02 },
  { index: 4, name: 'head_pan', unit: 'rad', step: 0.1 },
  { index: 5, name: 'head_tilt', unit: 'rad', step: 0.1 },
  { index: 6, name: 'wrist_yaw', unit: 'rad', step: 0.1 },
  { index: 7, name: 'wrist_pitch', unit: 'rad', step: 0.1 },
  { index: 8, name: 'wrist_roll', unit: 'rad', step: 0.1 },
  { index: 9, name: 'gripper', unit: '', step: 0.05 },
]

const BASE_JOINTS = ALL_JOINTS.filter((j) => [0, 1].includes(j.index))
const ARM_JOINTS = ALL_JOINTS.filter((j) => [2, 3, 6, 7, 8, 9].includes(j.index))
const HEAD_JOINTS = ALL_JOINTS.filter((j) => [4, 5].includes(j.index))

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
  <div class="p-2 overflow-auto h-full">
    <NTabs type="line" size="small" animated>
      <NTabPane name="base" tab="Base">
        <div class="space-y-2 pt-2">
          <div
            v-for="j in BASE_JOINTS"
            :key="j.index"
            class="flex items-center gap-2 text-sm"
          >
            <span class="flex-1 text-gray-300 text-xs">{{ j.name }}</span>
            <NButton size="tiny" @click="adjust(j.index, -j.step)">−</NButton>
            <span class="w-20 text-center text-xs font-mono">{{ value(j.index) }} {{ j.unit }}</span>
            <NButton size="tiny" @click="adjust(j.index, j.step)">+</NButton>
          </div>
        </div>
      </NTabPane>
      <NTabPane name="arm" tab="Arm">
        <div class="space-y-2 pt-2">
          <div
            v-for="j in ARM_JOINTS"
            :key="j.index"
            class="flex items-center gap-2 text-sm"
          >
            <span class="flex-1 text-gray-300 text-xs">{{ j.name }}</span>
            <NButton size="tiny" @click="adjust(j.index, -j.step)">−</NButton>
            <span class="w-20 text-center text-xs font-mono">{{ value(j.index) }} {{ j.unit }}</span>
            <NButton size="tiny" @click="adjust(j.index, j.step)">+</NButton>
          </div>
        </div>
      </NTabPane>
      <NTabPane name="head" tab="Head">
        <div class="space-y-2 pt-2">
          <div
            v-for="j in HEAD_JOINTS"
            :key="j.index"
            class="flex items-center gap-2 text-sm"
          >
            <span class="flex-1 text-gray-300 text-xs">{{ j.name }}</span>
            <NButton size="tiny" @click="adjust(j.index, -j.step)">−</NButton>
            <span class="w-20 text-center text-xs font-mono">{{ value(j.index) }} {{ j.unit }}</span>
            <NButton size="tiny" @click="adjust(j.index, j.step)">+</NButton>
          </div>
        </div>
      </NTabPane>
    </NTabs>
  </div>
</template>
