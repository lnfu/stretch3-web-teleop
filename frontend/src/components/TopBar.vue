<script setup lang="ts">
import { NText } from 'naive-ui'
import { isConnected } from '../composables/useWebSocket'
import RecordButton from './RecordButton.vue'
</script>

<template>
  <div class="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
    <div class="flex items-center gap-3">
      <NText strong style="font-size: 1.1rem; color: white">Stretch 3</NText>
      <span
        :class="[
          'text-xs font-medium px-2 py-0.5 rounded-full',
          isConnected ? 'bg-green-600 text-white' : 'bg-red-600 text-white',
        ]"
      >
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </span>
    </div>
    <RecordButton />
  </div>
</template>
