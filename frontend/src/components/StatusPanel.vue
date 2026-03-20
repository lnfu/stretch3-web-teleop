<script setup lang="ts">
import { computed } from 'vue'
import { useRobotStore } from '../stores/robotStore'

const robotStore = useRobotStore()
const status = computed(() => robotStore.status)

const toDeg = (r: number) => ((r * 180) / Math.PI).toFixed(1)
</script>

<template>
  <div class="flex items-center gap-2 px-3 py-3 border border-gray-700/60 rounded-xl bg-gray-900/50">
    <div v-if="!status" class="text-gray-400 text-xs">Waiting for robot status...</div>
    <template v-else>

      <!-- Charging: fixed square → nearly circular -->
      <div
        :class="[
          'w-14 h-14 rounded-2xl flex items-center justify-center text-center shrink-0',
          status.is_charging ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300',
        ]"
      >
        <span class="text-[10px] font-bold leading-tight">{{ status.is_charging ? 'Charg-\ning' : 'Bat-\ntery' }}</span>
      </div>

      <!-- Runstop: fixed square → nearly circular -->
      <div
        :class="[
          'w-14 h-14 rounded-2xl flex items-center justify-center text-center shrink-0',
          status.runstop ? 'bg-red-600 text-white' : 'bg-green-800 text-green-200',
        ]"
      >
        <span class="text-[10px] font-bold leading-tight">{{ status.runstop ? 'RUN-\nSTOP' : 'OK' }}</span>
      </div>

      <div class="w-px self-stretch bg-gray-700 shrink-0 mx-1" />

      <!-- Odometry: fixed-width columns, key on top, value below -->
      <div class="flex gap-2 flex-1">
        <div class="flex flex-col gap-0.5 w-14 shrink-0">
          <span class="text-[10px] text-gray-500 leading-none">X</span>
          <span class="text-xs font-mono text-gray-200 leading-none">{{ status.odometry.pose.x.toFixed(2) }} m</span>
        </div>
        <div class="flex flex-col gap-0.5 w-14 shrink-0">
          <span class="text-[10px] text-gray-500 leading-none">Y</span>
          <span class="text-xs font-mono text-gray-200 leading-none">{{ status.odometry.pose.y.toFixed(2) }} m</span>
        </div>
        <div class="flex flex-col gap-0.5 w-16 shrink-0">
          <span class="text-[10px] text-gray-500 leading-none">θ</span>
          <span class="text-xs font-mono text-gray-200 leading-none">{{ toDeg(status.odometry.pose.theta) }}°</span>
        </div>
        <div class="flex flex-col gap-0.5 w-20 shrink-0">
          <span class="text-[10px] text-gray-500 leading-none">Linear</span>
          <span class="text-xs font-mono text-gray-200 leading-none">{{ status.odometry.twist.linear.toFixed(3) }} m/s</span>
        </div>
        <div class="flex flex-col gap-0.5 w-20 shrink-0">
          <span class="text-[10px] text-gray-500 leading-none">Angular</span>
          <span class="text-xs font-mono text-gray-200 leading-none">{{ status.odometry.twist.angular.toFixed(3) }} r/s</span>
        </div>
      </div>

    </template>
  </div>
</template>
