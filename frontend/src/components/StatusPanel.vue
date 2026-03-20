<script setup lang="ts">
import { computed } from 'vue'
import { useRobotStore } from '../stores/robotStore'

const robotStore = useRobotStore()
const status = computed(() => robotStore.status)

const toDeg = (r: number) => ((r * 180) / Math.PI).toFixed(1)
</script>

<template>
  <div class="px-4 py-2.5 border-t border-gray-700 text-sm">
    <div v-if="!status" class="text-gray-400">Waiting for robot status...</div>
    <div v-else class="flex items-center gap-5 flex-wrap">
      <!-- Badges -->
      <div class="flex gap-2 shrink-0">
        <span
          :class="[
            'font-medium px-3 py-1 rounded-full',
            status.is_charging ? 'bg-green-600 text-white' : 'bg-gray-600 text-gray-200',
          ]"
        >
          {{ status.is_charging ? 'Charging' : 'Battery' }}
        </span>
        <span
          :class="[
            'font-medium px-3 py-1 rounded-full',
            status.runstop ? 'bg-red-600 text-white' : 'bg-green-700 text-white',
          ]"
        >
          {{ status.runstop ? 'RUNSTOP' : 'OK' }}
        </span>
      </div>

      <div class="h-4 w-px bg-gray-600 shrink-0" />

      <!-- Odometry: all in one row -->
      <div class="flex gap-4 font-mono flex-wrap">
        <span><span class="text-gray-400 font-sans">X</span> {{ status.odometry.pose.x.toFixed(2) }}m</span>
        <span><span class="text-gray-400 font-sans">Y</span> {{ status.odometry.pose.y.toFixed(2) }}m</span>
        <span><span class="text-gray-400 font-sans">θ</span> {{ toDeg(status.odometry.pose.theta) }}°</span>
        <span><span class="text-gray-400 font-sans">Lin</span> {{ status.odometry.twist.linear.toFixed(3) }}m/s</span>
        <span><span class="text-gray-400 font-sans">Ang</span> {{ status.odometry.twist.angular.toFixed(3) }}r/s</span>
      </div>
    </div>
  </div>
</template>
