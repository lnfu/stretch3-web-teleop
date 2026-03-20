<script setup lang="ts">
import { computed } from 'vue'
import { NText } from 'naive-ui'
import { useRobotStore } from '../stores/robotStore'

const robotStore = useRobotStore()
const status = computed(() => robotStore.status)

const toDeg = (r: number) => ((r * 180) / Math.PI).toFixed(1)

const JOINT_NAMES = [
  'base_translate',
  'base_rotate',
  'lift',
  'arm',
  'head_pan',
  'head_tilt',
  'wrist_yaw',
  'wrist_pitch',
  'wrist_roll',
  'gripper',
]
const JOINT_UNITS = ['m', 'rad', 'm', 'm', 'rad', 'rad', 'rad', 'rad', 'rad', '']
</script>

<template>
  <div class="p-3 overflow-auto h-full text-sm">
    <div v-if="!status" class="text-gray-400">Waiting for robot status...</div>
    <div v-else>
      <!-- Status badges -->
      <div class="flex gap-2 flex-wrap mb-3">
        <span
          :class="[
            'text-xs font-medium px-2 py-0.5 rounded-full',
            status.is_charging ? 'bg-green-600 text-white' : 'bg-gray-600 text-gray-200',
          ]"
        >
          {{ status.is_charging ? 'Charging' : 'On battery' }}
        </span>
        <span
          :class="[
            'text-xs font-medium px-2 py-0.5 rounded-full',
            status.runstop ? 'bg-red-600 text-white' : 'bg-green-700 text-white',
          ]"
        >
          {{ status.runstop ? 'RUNSTOP ACTIVE' : 'OK' }}
        </span>
      </div>

      <!-- Odometry -->
      <div class="mb-3">
        <NText
          strong
          style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af"
        >
          Odometry
        </NText>
        <div class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
          <span class="text-gray-400">X</span>
          <span>{{ status.odometry.pose.x.toFixed(2) }} m</span>
          <span class="text-gray-400">Y</span>
          <span>{{ status.odometry.pose.y.toFixed(2) }} m</span>
          <span class="text-gray-400">θ</span>
          <span>{{ toDeg(status.odometry.pose.theta) }}°</span>
          <span class="text-gray-400">Linear</span>
          <span>{{ status.odometry.twist.linear.toFixed(3) }} m/s</span>
          <span class="text-gray-400">Angular</span>
          <span>{{ status.odometry.twist.angular.toFixed(3) }} rad/s</span>
        </div>
      </div>

      <!-- Joint positions -->
      <div>
        <NText
          strong
          style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af"
        >
          Joints
        </NText>
        <div class="mt-1">
          <div
            v-for="(name, i) in JOINT_NAMES"
            :key="i"
            class="flex justify-between text-xs py-0.5"
          >
            <span class="text-gray-400">{{ name }}</span>
            <span class="font-mono">
              {{ (status.joint_positions[i] ?? 0).toFixed(3) }}
              {{ JOINT_UNITS[i] }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
