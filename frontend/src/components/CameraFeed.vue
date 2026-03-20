<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NButtonGroup, NButton } from 'naive-ui'
import { cameraFrames } from '../composables/useWebSocket'
import type { CameraId } from '../types/protocol'

const props = defineProps<{
  cameraId: 'arducam' | 'd435i' | 'd405'
  label: string
}>()

type DisplayMode = 'rgb' | 'depth' | 'overlay'
const mode = ref<DisplayMode>('rgb')

const hasDepth = computed(() => props.cameraId !== 'arducam')

const rgbId = computed((): CameraId => {
  if (props.cameraId === 'arducam') return 'arducam'
  return `${props.cameraId}_rgb` as CameraId
})

const depthId = computed((): CameraId | null => {
  if (!hasDepth.value) return null
  return `${props.cameraId}_depth` as CameraId
})

const rgbUrl = computed(() => cameraFrames[rgbId.value].value)
const depthUrl = computed(() => (depthId.value ? cameraFrames[depthId.value].value : null))

const canvasRef = ref<HTMLCanvasElement | null>(null)

async function drawOverlay() {
  if (mode.value !== 'overlay' || !canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  if (!rgbUrl.value) return

  const rgbImg = new Image()
  rgbImg.src = rgbUrl.value
  await new Promise((r) => {
    rgbImg.onload = r
    rgbImg.onerror = r
  })
  canvas.width = rgbImg.naturalWidth
  canvas.height = rgbImg.naturalHeight
  ctx.drawImage(rgbImg, 0, 0)

  if (depthUrl.value) {
    const depthImg = new Image()
    depthImg.src = depthUrl.value
    await new Promise((r) => {
      depthImg.onload = r
      depthImg.onerror = r
    })
    ctx.globalAlpha = 0.5
    ctx.drawImage(depthImg, 0, 0, canvas.width, canvas.height)
    ctx.globalAlpha = 1.0
  }
}

watch([rgbUrl, depthUrl, mode], () => {
  if (mode.value === 'overlay') drawOverlay()
})
</script>

<template>
  <div class="relative flex flex-col bg-black rounded overflow-hidden h-full">
    <!-- Label overlay -->
    <div class="absolute top-2 left-2 z-10 text-white text-xs bg-black/50 px-1 rounded">
      {{ label }}
    </div>

    <!-- RGB or Depth image -->
    <img
      v-if="mode !== 'overlay' && (mode === 'rgb' ? rgbUrl : depthUrl)"
      :src="mode === 'rgb' ? rgbUrl! : depthUrl!"
      class="w-full h-full object-contain"
      alt="camera feed"
    />

    <!-- No signal placeholder -->
    <div
      v-else-if="mode !== 'overlay'"
      class="flex-1 flex items-center justify-center text-gray-500 text-sm"
    >
      No signal
    </div>

    <!-- Overlay canvas -->
    <canvas v-if="mode === 'overlay'" ref="canvasRef" class="w-full h-full object-contain" />
    <div
      v-if="mode === 'overlay' && !rgbUrl"
      class="absolute inset-0 flex items-center justify-center text-gray-500 text-sm"
    >
      No signal
    </div>

    <!-- Mode toggle (depth cameras only) -->
    <div v-if="hasDepth" class="absolute bottom-2 left-1/2 -translate-x-1/2 z-10">
      <NButtonGroup size="tiny">
        <NButton :type="mode === 'rgb' ? 'primary' : 'default'" @click="mode = 'rgb'">
          RGB
        </NButton>
        <NButton :type="mode === 'depth' ? 'primary' : 'default'" @click="mode = 'depth'">
          Depth
        </NButton>
        <NButton :type="mode === 'overlay' ? 'primary' : 'default'" @click="mode = 'overlay'">
          Overlay
        </NButton>
      </NButtonGroup>
    </div>
  </div>
</template>
