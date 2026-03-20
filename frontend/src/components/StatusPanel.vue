<script setup lang="ts">
import { computed } from 'vue'
import { useRobotStore } from '../stores/robotStore'

const robotStore = useRobotStore()
const status = computed(() => robotStore.status)

const toDeg = (r: number) => ((r * 180) / Math.PI).toFixed(1)
</script>

<template>
  <div class="flex items-center gap-2 px-3 py-3 border border-gray-200 rounded-xl bg-white">
    <div v-if="!status" class="text-gray-400 text-xs">Waiting for robot status...</div>
    <template v-else>

      <!-- Charging -->
      <div :class="[
        'w-14 h-14 rounded-full flex items-center justify-center text-center shrink-0',
        status.is_charging ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-500',
      ]">
        <span class="text-[10px] font-bold leading-tight">{{ status.is_charging ? 'CHARGING' : 'BATTERY' }}</span>
      </div>

      <!-- Runstop -->
      <div :class="[
        'w-14 h-14 rounded-full flex items-center justify-center text-center shrink-0',
        status.runstop ? 'bg-red-500 text-white' : 'bg-green-100 text-green-700',
      ]">
        <span class="text-[10px] font-bold leading-tight">{{ status.runstop ? 'RUNSTOP' : 'OK' }}</span>
      </div>

      <div class="w-px self-stretch bg-gray-200 shrink-0 mx-1" />

      <!-- Odometry: fixed-width columns, key on top, value below -->
      <div class="flex gap-2 flex-1">
        <div class="flex flex-col gap-0.5 w-14 shrink-0">
          <span class="text-[10px] text-gray-400 leading-none">X</span>
          <span class="text-xs font-mono text-gray-800 leading-none">{{ status.odometry.pose.x.toFixed(2) }} m</span>
        </div>
        <div class="flex flex-col gap-0.5 w-14 shrink-0">
          <span class="text-[10px] text-gray-400 leading-none">Y</span>
          <span class="text-xs font-mono text-gray-800 leading-none">{{ status.odometry.pose.y.toFixed(2) }} m</span>
        </div>
        <div class="flex flex-col gap-0.5 w-16 shrink-0">
          <span class="text-[10px] text-gray-400 leading-none">θ</span>
          <span class="text-xs font-mono text-gray-800 leading-none">{{ toDeg(status.odometry.pose.theta) }}°</span>
        </div>
        <div class="flex flex-col gap-0.5 w-20 shrink-0">
          <span class="text-[10px] text-gray-400 leading-none">Linear</span>
          <span class="text-xs font-mono text-gray-800 leading-none">{{ status.odometry.twist.linear.toFixed(3) }}
            m/s</span>
        </div>
        <div class="flex flex-col gap-0.5 w-20 shrink-0">
          <span class="text-[10px] text-gray-400 leading-none">Angular</span>
          <span class="text-xs font-mono text-gray-800 leading-none">{{ status.odometry.twist.angular.toFixed(3) }}
            r/s</span>
        </div>
      </div>

    </template>
  </div>
</template>
