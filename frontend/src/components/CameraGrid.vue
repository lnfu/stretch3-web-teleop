<script setup lang="ts">
import CameraFeed from './CameraFeed.vue'
</script>

<template>
  <div class="flex flex-col gap-2 h-full p-2">
    <!-- Arducam: ~60% height -->
    <div class="flex-[3]">
      <CameraFeed camera-id="arducam" label="Arducam (RGB)" />
    </div>
    <!-- Bottom row: d435i and d405 ~40% height -->
    <div class="flex-[2] flex gap-2">
      <div class="flex-1">
        <CameraFeed camera-id="d435i" label="D435i" />
      </div>
      <div class="flex-1">
        <CameraFeed camera-id="d405" label="D405" />
      </div>
    </div>
  </div>
</template>
