<script setup lang="ts">
import { NConfigProvider, darkTheme } from 'naive-ui'
import TopBar from './components/TopBar.vue'
import CameraGrid from './components/CameraGrid.vue'
import StatusPanel from './components/StatusPanel.vue'
import JointControls from './components/JointControls.vue'
import { useWebSocketSingleton } from './composables/useWebSocket'

useWebSocketSingleton()
</script>

<template>
  <NConfigProvider :theme="darkTheme">
    <div class="flex flex-col h-screen bg-gray-950 text-white overflow-hidden">
      <!-- Top bar -->
      <TopBar />
      <!-- Main content -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Left: Camera grid (~65%) -->
        <div class="flex-[65] overflow-hidden">
          <CameraGrid />
        </div>
        <!-- Right: Status + Controls (~35%) -->
        <div class="flex-[35] flex flex-col overflow-hidden border-l border-gray-700">
          <div class="flex-1 overflow-auto border-b border-gray-700">
            <StatusPanel />
          </div>
          <div class="flex-1 overflow-auto">
            <JointControls />
          </div>
        </div>
      </div>
    </div>
  </NConfigProvider>
</template>
