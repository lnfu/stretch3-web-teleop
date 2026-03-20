<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRobotStore } from '../stores/robotStore'
import { sendMessage } from '../composables/useWebSocket'

const robotStore = useRobotStore()
const lastGripperCmd = ref(0)

interface JointDef {
  index: number
  label: string
  unit: string
  step: number
}

interface Group {
  name: string
  accent: string
  joints: JointDef[]
}

// Top row: Base | Arm | Wrist
const TOP_GROUPS: Group[] = [
  {
    name: 'Base',
    accent: '#60a5fa',
    joints: [
      { index: 0, label: 'Translate', unit: 'm', step: 0.05 },
      { index: 1, label: 'Rotate', unit: 'rad', step: 0.1 },
    ],
  },
  {
    name: 'Arm',
    accent: '#34d399',
    joints: [
      { index: 2, label: 'Lift', unit: 'm', step: 0.05 },
      { index: 3, label: 'Arm', unit: 'm', step: 0.02 },
    ],
  },
  {
    name: 'Wrist',
    accent: '#fb923c',
    joints: [
      { index: 6, label: 'Yaw', unit: 'rad', step: 0.1 },
      { index: 7, label: 'Pitch', unit: 'rad', step: 0.1 },
      { index: 8, label: 'Roll', unit: 'rad', step: 0.1 },
    ],
  },
]

// Bottom row: Head (alongside Gripper)
const HEAD_JOINTS: JointDef[] = [
  { index: 4, label: 'Pan', unit: 'rad', step: 0.1 },
  { index: 5, label: 'Tilt', unit: 'rad', step: 0.1 },
]

const GRIPPER_PRESETS = [-10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

function gripperColor(i: number): string {
  const t = i / (GRIPPER_PRESETS.length - 1)
  const h = Math.round(t * 120)
  const s = 75
  const l = Math.round(28 + t * 12)
  return `hsl(${h}, ${s}%, ${l}%)`
}

const gripperStatus = computed(() =>
  (robotStore.status?.joint_positions[9] ?? 0).toFixed(1),
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
  return (robotStore.jointPositions[index] ?? 0).toFixed(2)
}
</script>

<template>
  <div class="grid gap-2 px-1 py-1">

    <!-- Top row: Base | Arm | Wrist -->
    <div class="grid grid-cols-[2fr_2fr_3fr] gap-2">
      <div v-for="g in TOP_GROUPS" :key="g.name"
        class="grid gap-2 border border-gray-700/60 rounded-xl p-3 bg-gray-900/50" style="grid-template-rows: auto 1fr">
        <span class="text-[11px] font-bold uppercase tracking-widest text-center leading-none pb-0.5"
          :style="{ color: g.accent }">{{ g.name }}</span>

        <div class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${g.joints.length}, 1fr)` }">
          <div v-for="j in g.joints" :key="j.index" class="grid gap-1.5" style="grid-template-rows: auto 1fr">
            <div class="grid grid-cols-[1fr_auto] items-baseline px-1">
              <span class="text-xs text-gray-400 leading-none">{{ j.label }}</span>
              <span class="text-xs font-mono text-gray-300 leading-none">
                {{ value(j.index) }}<span class="text-gray-600 ml-0.5 text-[10px]">{{ j.unit }}</span>
              </span>
            </div>
            <div class="grid grid-cols-2 rounded-lg overflow-hidden">
              <button
                class="py-5 bg-gray-800 hover:bg-red-900 active:bg-red-700 text-white text-2xl font-black select-none transition-colors border-r border-gray-700 leading-none"
                @click="adjust(j.index, -j.step)">−</button>
              <button
                class="py-5 bg-gray-800 hover:bg-blue-900 active:bg-blue-700 text-white text-2xl font-black select-none transition-colors leading-none"
                @click="adjust(j.index, j.step)">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Head group -->
      <div class="grid gap-2 border border-gray-700/60 rounded-xl p-3 bg-gray-900/50"
        style="grid-template-rows: auto 1fr">
        <span class="text-[11px] font-bold uppercase tracking-widest text-center leading-none pb-0.5"
          style="color: #c084fc">Head</span>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="j in HEAD_JOINTS" :key="j.index" class="grid gap-1.5" style="grid-template-rows: auto 1fr">
            <div class="grid grid-cols-[1fr_auto] items-baseline px-1">
              <span class="text-xs text-gray-400 leading-none">{{ j.label }}</span>
              <span class="text-xs font-mono text-gray-300 leading-none">
                {{ value(j.index) }}<span class="text-gray-600 ml-0.5 text-[10px]">{{ j.unit }}</span>
              </span>
            </div>
            <div class="grid grid-cols-2 rounded-lg overflow-hidden">
              <button
                class="py-5 bg-gray-800 hover:bg-red-900 active:bg-red-700 text-white text-2xl font-black select-none transition-colors border-r border-gray-700 leading-none"
                @click="adjust(j.index, -j.step)">−</button>
              <button
                class="py-5 bg-gray-800 hover:bg-blue-900 active:bg-blue-700 text-white text-2xl font-black select-none transition-colors leading-none"
                @click="adjust(j.index, j.step)">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Gripper -->
      <div class="col-span-2 grid gap-2 border border-gray-700/60 rounded-xl px-4 py-3 bg-gray-900/50"
        style="grid-template-rows: auto 1fr auto">
        <div class="grid grid-cols-[auto_1fr] items-center gap-2">
          <span class="text-[11px] font-bold uppercase tracking-widest" style="color: #f472b6">Gripper</span>
          <span class="text-xs font-mono text-gray-400">{{ gripperStatus }}</span>
        </div>
        <div class="grid grid-cols-12 gap-1.5">
          <button v-for="(val, i) in GRIPPER_PRESETS" :key="val" :style="{ backgroundColor: gripperColor(i) }"
            :title="`${val}`" :class="[
              'rounded-lg select-none transition-all duration-150 min-h-[52px]',
              val === lastGripperCmd
                ? 'ring-2 ring-white/80 ring-offset-1 ring-offset-gray-900 scale-y-110 brightness-125'
                : 'hover:brightness-150 hover:scale-y-105',
            ]" @click="setGripper(val)" />
        </div>
        <div class="grid grid-cols-2 text-[10px] text-gray-600 px-0.5">
          <span>close</span>
          <span class="text-right">open</span>
        </div>
      </div>

    </div>
  </div>
</template>
