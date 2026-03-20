import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useRecordingStore = defineStore('recording', () => {
  const isRecording = ref(false)
  const session = ref<string | null>(null)
  const startTime = ref<number | null>(null)

  function setRecording(recording: boolean, sessionName: string | null) {
    isRecording.value = recording
    session.value = sessionName
    if (recording && !startTime.value) {
      startTime.value = Date.now()
    } else if (!recording) {
      startTime.value = null
    }
  }

  return { isRecording, session, startTime, setRecording }
})
