<script setup lang="ts">
import { NConfigProvider, darkTheme } from 'naive-ui'
import TopBar from './components/TopBar.vue'
import CameraGrid from './components/CameraGrid.vue'
import JointControls from './components/JointControls.vue'
import { useWebSocketSingleton } from './composables/useWebSocket'

useWebSocketSingleton()
</script>

<template>
  <NConfigProvider :theme="darkTheme">
    <div class="flex flex-col h-screen bg-gray-950 text-white overflow-hidden">
      <TopBar />
      <div class="flex-1 flex flex-col overflow-hidden min-h-0">
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
  </NConfigProvider>
</template>
