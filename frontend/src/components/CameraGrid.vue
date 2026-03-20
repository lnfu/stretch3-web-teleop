<script setup lang="ts">
import CameraFeed from './CameraFeed.vue'
</script>

<template>
  <div class="flex h-full gap-2 p-2">
    <div class="flex-[27] min-w-0 h-full">
      <CameraFeed camera-id="arducam" label="Arducam" :rotation="-90" />
    </div>
    <div class="flex-[36] min-w-0 h-full">
      <CameraFeed camera-id="d435i" label="D435i" :rotation="90" />
    </div>
    <div class="flex-[64] min-w-0 h-full">
      <CameraFeed camera-id="d405" label="D405" />
    </div>
  </div>
</template>
