<script setup lang="ts">
import { computed } from 'vue'
import { sendMessage } from '../composables/useWebSocket'
import { cachedPositions } from '../composables/useJointCache'
import StatusPanel from './StatusPanel.vue'

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
    accent: '#2563eb',
    joints: [
      { index: 0, label: 'Translate', unit: 'm', step: 0.05 },
      { index: 1, label: 'Rotate', unit: 'rad', step: 0.1 },
    ],
  },
  {
    name: 'Arm',
    accent: '#059669',
    joints: [
      { index: 2, label: 'Lift', unit: 'm', step: 0.05 },
      { index: 3, label: 'Arm', unit: 'm', step: 0.02 },
    ],
  },
  {
    name: 'Wrist',
    accent: '#ea580c',
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

const gripperCached = computed(() => cachedPositions.value[9] ?? 0)

// Indices 0 (base translate) and 1 (base rotate) are delta-controlled and must
// never be cached — they always send the raw delta and are 0 in all other commands.
const BASE_DELTA_INDICES = new Set([0, 1])

function adjust(jointIndex: number, delta: number) {
  const positions = [...cachedPositions.value]
  if (BASE_DELTA_INDICES.has(jointIndex)) {
    positions[jointIndex] = delta
    sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
    // Do not update cachedPositions so base slots stay at 0.
  } else {
    positions[jointIndex] = (positions[jointIndex] ?? 0) + delta
    cachedPositions.value = positions
    sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
  }
}

function setGripper(val: number) {
  const positions = [...cachedPositions.value]
  positions[9] = val
  cachedPositions.value = positions
  sendMessage({ type: 'command', topic: 'manipulator', joint_positions: positions })
}

function value(index: number): string {
  return (cachedPositions.value[index] ?? 0).toFixed(2)
}
</script>

<template>
  <div class="grid gap-2 px-1 py-1">

    <!-- Top row: Base | Arm | Wrist -->
    <div class="grid grid-cols-[2fr_2fr_3fr] gap-2">
      <div v-for="g in TOP_GROUPS" :key="g.name"
        class="grid gap-2 border border-gray-200 rounded-xl p-3 bg-white" style="grid-template-rows: auto 1fr">
        <span class="text-[11px] font-bold uppercase tracking-widest text-center leading-none pb-0.5"
          :style="{ color: g.accent }">{{ g.name }}</span>

        <div class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${g.joints.length}, 1fr)` }">
          <div v-for="j in g.joints" :key="j.index" class="grid gap-1.5" style="grid-template-rows: auto 1fr">
            <div class="grid grid-cols-[1fr_auto] items-baseline px-1">
              <span class="text-xs text-gray-500 leading-none">{{ j.label }}</span>
              <span class="text-xs font-mono text-gray-700 leading-none">
                {{ value(j.index) }}<span class="text-gray-400 ml-0.5 text-[10px]">{{ j.unit }}</span>
              </span>
            </div>
            <div class="grid grid-cols-2 rounded-lg overflow-hidden border border-gray-200">
              <button
                class="py-5 bg-gray-50 hover:bg-red-100 active:bg-red-200 text-gray-800 hover:text-red-700 text-2xl font-black select-none transition-colors border-r border-gray-200 leading-none"
                @click="adjust(j.index, -j.step)">−</button>
              <button
                class="py-5 bg-gray-50 hover:bg-blue-100 active:bg-blue-200 text-gray-800 hover:text-blue-700 text-2xl font-black select-none transition-colors leading-none"
                @click="adjust(j.index, j.step)">+</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom row: Head | Gripper | Status -->
    <div class="grid grid-cols-[2fr_2fr_3fr] gap-2">

      <!-- Head -->
      <div class="grid gap-2 border border-gray-200 rounded-xl p-3 bg-white" style="grid-template-rows: auto 1fr">
        <span class="text-[11px] font-bold uppercase tracking-widest text-center leading-none pb-0.5"
          style="color: #9333ea">Head</span>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="j in HEAD_JOINTS" :key="j.index" class="grid gap-1.5" style="grid-template-rows: auto 1fr">
            <div class="grid grid-cols-[1fr_auto] items-baseline px-1">
              <span class="text-xs text-gray-500 leading-none">{{ j.label }}</span>
              <span class="text-xs font-mono text-gray-700 leading-none">
                {{ value(j.index) }}<span class="text-gray-400 ml-0.5 text-[10px]">{{ j.unit }}</span>
              </span>
            </div>
            <div class="grid grid-cols-2 rounded-lg overflow-hidden border border-gray-200">
              <button
                class="py-5 bg-gray-50 hover:bg-red-100 active:bg-red-200 text-gray-800 hover:text-red-700 text-2xl font-black select-none transition-colors border-r border-gray-200 leading-none"
                @click="adjust(j.index, -j.step)">−</button>
              <button
                class="py-5 bg-gray-50 hover:bg-blue-100 active:bg-blue-200 text-gray-800 hover:text-blue-700 text-2xl font-black select-none transition-colors leading-none"
                @click="adjust(j.index, j.step)">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Gripper -->
      <div class="grid gap-2 border border-gray-200 rounded-xl px-3 py-3 bg-white" style="grid-template-rows: auto 1fr auto">
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-bold uppercase tracking-widest" style="color: #db2777">Gripper</span>
          <span class="text-xs font-mono text-gray-500">{{ gripperCached.toFixed(1) }}</span>
        </div>
        <div class="grid grid-cols-12 gap-1">
          <button v-for="(val, i) in GRIPPER_PRESETS" :key="val" :style="{ backgroundColor: gripperColor(i) }"
            :title="`${val}`" :class="[
              'rounded-md select-none transition-all duration-150',
              val === gripperCached
                ? 'ring-2 ring-gray-800/60 ring-offset-1 ring-offset-white scale-y-110 brightness-110'
                : 'hover:brightness-110 hover:scale-y-105',
            ]" @click="setGripper(val)" />
        </div>
        <div class="grid grid-cols-2 text-[10px] text-gray-400 px-0.5">
          <span>close</span>
          <span class="text-right">open</span>
        </div>
      </div>

      <!-- Status -->
      <StatusPanel />

    </div>
  </div>
</template>
