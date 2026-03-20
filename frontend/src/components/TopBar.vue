<script setup lang="ts">
import { NText } from 'naive-ui'
import { isConnected } from '../composables/useWebSocket'
import RecordButton from './RecordButton.vue'
</script>

<template>
  <div class="flex items-center justify-between px-5 py-3 bg-gray-900 border border-gray-700 rounded-xl shrink-0">
    <div class="flex items-center gap-4">
      <NText strong style="font-size: 1.3rem; color: white">Stretch 3</NText>
      <span
        :class="[
          'text-sm font-medium px-3 py-1 rounded-full',
          isConnected ? 'bg-green-600 text-white' : 'bg-red-600 text-white',
        ]"
      >
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </span>
    </div>
    <RecordButton />
  </div>
</template>
