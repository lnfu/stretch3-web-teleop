<script setup lang="ts">
import { NConfigProvider, NNotificationProvider } from 'naive-ui'
import TopBar from './components/TopBar.vue'
import CameraGrid from './components/CameraGrid.vue'
import JointControls from './components/JointControls.vue'
import { useWebSocketSingleton } from './composables/useWebSocket'

useWebSocketSingleton()
</script>

<template>
  <NConfigProvider>
    <NNotificationProvider placement="bottom-right">
    <div class="flex flex-col h-screen bg-slate-100 text-gray-900 overflow-hidden p-2 gap-2">
      <TopBar />
      <div class="flex-1 flex flex-col overflow-hidden min-h-0 gap-2">
        <!-- Top: all cameras + status (inside CameraGrid) -->
        <div class="flex-1 min-h-0 overflow-hidden">
          <CameraGrid />
        </div>
        <!-- Bottom: joint controls -->
        <div class="shrink-0">
          <JointControls />
        </div>
      </div>
    </div>
    </NNotificationProvider>
  </NConfigProvider>
</template>
