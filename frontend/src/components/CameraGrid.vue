<script setup lang="ts">
import CameraFeed from './CameraFeed.vue'
import StatusPanel from './StatusPanel.vue'
</script>

<template>
  <div class="flex h-full gap-2 p-2">
    <!-- Portrait cameras -->
    <div class="flex-[9] min-w-0">
      <CameraFeed camera-id="arducam" label="Arducam" :rotation="-90" />
    </div>
    <div class="flex-[12] min-w-0">
      <CameraFeed camera-id="d435i" label="D435i" :rotation="90" />
    </div>
    <!-- D405 (landscape, larger) + status below -->
    <div class="flex-[20] flex flex-col min-w-0 gap-2">
      <div class="flex-1 min-h-0">
        <CameraFeed camera-id="d405" label="D405" />
      </div>
      <div class="shrink-0">
        <StatusPanel />
      </div>
    </div>
  </div>
</template>
