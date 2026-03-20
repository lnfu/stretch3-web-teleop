<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { NButton } from 'naive-ui'
import { useRecordingStore } from '../stores/recordingStore'
import { sendMessage } from '../composables/useWebSocket'

const recordingStore = useRecordingStore()

const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

function startTimer() {
  stopTimer()
  elapsed.value = 0
  timer = setInterval(() => {
    elapsed.value++
  }, 1000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  elapsed.value = 0
}

watch(
  () => recordingStore.isRecording,
  (val) => {
    if (val) startTimer()
    else stopTimer()
  },
)

onUnmounted(stopTimer)

const elapsedStr = computed(() => {
  const m = Math.floor(elapsed.value / 60)
    .toString()
    .padStart(2, '0')
  const s = (elapsed.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

function toggle() {
  if (recordingStore.isRecording) {
    sendMessage({ type: 'recording_stop' })
  } else {
    sendMessage({ type: 'recording_start' })
  }
}
</script>

<template>
  <div class="flex items-center gap-2">
    <span
      v-if="recordingStore.isRecording"
      class="flex items-center gap-1 text-red-400 text-sm"
    >
      <span class="animate-pulse w-2 h-2 bg-red-500 rounded-full inline-block"></span>
      {{ elapsedStr }}
    </span>
    <NButton
      :type="recordingStore.isRecording ? 'error' : 'primary'"
      size="small"
      @click="toggle"
    >
      {{ recordingStore.isRecording ? 'Stop Recording' : 'Record' }}
    </NButton>
  </div>
</template>
