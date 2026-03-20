<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NButtonGroup, NButton } from 'naive-ui'
import { cameraFrames } from '../composables/useWebSocket'
import type { CameraId } from '../types/protocol'

const props = defineProps<{
  cameraId: 'arducam' | 'd435i' | 'd405'
  label: string
  rotation?: number // degrees: 0, 90, -90
}>()

type DisplayMode = 'rgb' | 'depth' | 'overlay'
const mode = ref<DisplayMode>('rgb')

const hasDepth = computed(() => props.cameraId !== 'arducam')
const isRotated = computed(() => !!props.rotation && props.rotation !== 0)

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

const rotationLabel = computed(() => {
  if (!props.rotation) return ''
  return props.rotation < 0 ? ' ↺90°' : ' ↻90°'
})

// Canvas used when rotation is applied (handles all modes)
const rotatedCanvasRef = ref<HTMLCanvasElement | null>(null)
// Canvas used for overlay mode without rotation
const overlayCanvasRef = ref<HTMLCanvasElement | null>(null)

const noSignal = computed(() => {
  if (!isRotated.value) return false
  if (mode.value === 'rgb') return !rgbUrl.value
  if (mode.value === 'depth') return !depthUrl.value
  return !rgbUrl.value
})

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function drawRotatedImage(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  deg: number,
  cw: number,
  ch: number,
) {
  ctx.save()
  ctx.translate(cw / 2, ch / 2)
  ctx.rotate((deg * Math.PI) / 180)
  ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2)
  ctx.restore()
}

async function drawRotatedFrame() {
  const canvas = rotatedCanvasRef.value
  if (!canvas) return
  const deg = props.rotation ?? 0
  const is90 = Math.abs(deg) === 90

  const ctx = canvas.getContext('2d')!

  if (mode.value === 'rgb' && rgbUrl.value) {
    const img = await loadImage(rgbUrl.value)
    canvas.width = is90 ? img.naturalHeight : img.naturalWidth
    canvas.height = is90 ? img.naturalWidth : img.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    drawRotatedImage(ctx, img, deg, canvas.width, canvas.height)
  } else if (mode.value === 'depth' && depthUrl.value) {
    const img = await loadImage(depthUrl.value)
    canvas.width = is90 ? img.naturalHeight : img.naturalWidth
    canvas.height = is90 ? img.naturalWidth : img.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    drawRotatedImage(ctx, img, deg, canvas.width, canvas.height)
  } else if (mode.value === 'overlay' && rgbUrl.value) {
    const rgbImg = await loadImage(rgbUrl.value)
    canvas.width = is90 ? rgbImg.naturalHeight : rgbImg.naturalWidth
    canvas.height = is90 ? rgbImg.naturalWidth : rgbImg.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    drawRotatedImage(ctx, rgbImg, deg, canvas.width, canvas.height)
    if (depthUrl.value) {
      const depthImg = await loadImage(depthUrl.value)
      ctx.globalAlpha = 0.2
      drawRotatedImage(ctx, depthImg, deg, canvas.width, canvas.height)
      ctx.globalAlpha = 1.0
    }
  }
}

async function drawOverlay() {
  if (mode.value !== 'overlay' || !overlayCanvasRef.value) return
  const canvas = overlayCanvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx || !rgbUrl.value) return

  const rgbImg = await loadImage(rgbUrl.value)
  canvas.width = rgbImg.naturalWidth
  canvas.height = rgbImg.naturalHeight
  ctx.drawImage(rgbImg, 0, 0)

  if (depthUrl.value) {
    const depthImg = await loadImage(depthUrl.value)
    ctx.globalAlpha = 0.2
    ctx.drawImage(depthImg, 0, 0, canvas.width, canvas.height)
    ctx.globalAlpha = 1.0
  }
}

watch([rgbUrl, depthUrl, mode], () => {
  if (isRotated.value) {
    drawRotatedFrame()
  } else if (mode.value === 'overlay') {
    drawOverlay()
  }
})
</script>

<template>
  <div class="relative flex flex-col bg-black rounded overflow-hidden h-full">
    <!-- Label overlay -->
    <div class="absolute top-2 left-2 z-10 text-white text-sm bg-black/50 px-2.5 py-1 rounded">
      {{ label }}{{ rotationLabel }}
    </div>

    <!-- Rotated display: canvas with correct intrinsic dimensions -->
    <template v-if="isRotated">
      <canvas v-show="!noSignal" ref="rotatedCanvasRef" class="w-full h-full object-contain" />
      <div v-if="noSignal" class="flex-1 flex items-center justify-center text-gray-500 text-sm">
        No signal
      </div>
    </template>

    <!-- Non-rotated display: original img / canvas approach -->
    <template v-else>
      <img v-if="mode !== 'overlay' && (mode === 'rgb' ? rgbUrl : depthUrl)" :src="mode === 'rgb' ? rgbUrl! : depthUrl!"
        class="w-full h-full object-contain" alt="camera feed" />
      <div v-else-if="mode !== 'overlay'" class="flex-1 flex items-center justify-center text-gray-500 text-sm">
        No signal
      </div>
      <canvas v-if="mode === 'overlay'" ref="overlayCanvasRef" class="w-full h-full object-contain" />
      <div v-if="mode === 'overlay' && !rgbUrl"
        class="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
        No signal
      </div>
    </template>

    <!-- Mode toggle (depth cameras only) -->
    <div v-if="hasDepth" class="absolute bottom-3 left-1/2 -translate-x-1/2 z-10">
      <NButtonGroup size="small">
        <NButton :type="mode === 'rgb' ? 'primary' : 'default'" @click="mode = 'rgb'">RGB</NButton>
        <NButton :type="mode === 'depth' ? 'primary' : 'default'" @click="mode = 'depth'">Depth</NButton>
        <NButton :type="mode === 'overlay' ? 'primary' : 'default'" @click="mode = 'overlay'">Overlay</NButton>
      </NButtonGroup>
    </div>
  </div>
</template>
