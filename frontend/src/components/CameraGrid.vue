<script setup lang="ts">
import CameraFeed from './CameraFeed.vue'
</script>

<template>
  <div class="flex h-full gap-2 p-2">
    <div class="flex-[9] min-w-0">
      <CameraFeed camera-id="arducam" label="Arducam" :rotation="-90" />
    </div>
    <div class="flex-[12] min-w-0">
      <CameraFeed camera-id="d435i" label="D435i" :rotation="90" />
    </div>
    <div class="flex-[22] min-w-0">
      <CameraFeed camera-id="d405" label="D405" />
    </div>
  </div>
</template>
