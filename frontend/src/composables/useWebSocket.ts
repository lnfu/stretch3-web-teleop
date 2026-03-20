import { ref, type Ref } from 'vue'
import { useWebSocket as vueUseWebSocket } from '@vueuse/core'
import { createDiscreteApi } from 'naive-ui'
import { useRobotStore } from '../stores/robotStore'
import { useRecordingStore } from '../stores/recordingStore'
import { CAMERA_ID_MAP, type CameraId, type RobotStatus, type RecordingState, type PreviewReady } from '../types/protocol'
import { INITIAL_POSITIONS, cachedPositions } from './useJointCache'

const { notification } = createDiscreteApi(['notification'])

export const cameraFrames: Record<CameraId, Ref<string | null>> = {
  arducam: ref(null),
  d435i_rgb: ref(null),
  d435i_depth: ref(null),
  d405_rgb: ref(null),
  d405_depth: ref(null),
}

export const isConnected = ref(false)

let ws: ReturnType<typeof vueUseWebSocket> | null = null

function initWebSocket() {
  ws = vueUseWebSocket('/ws', {
    autoReconnect: {
      retries: Infinity,
      delay: 3000,
    },
    onConnected() {
      isConnected.value = true
      cachedPositions.value = [...INITIAL_POSITIONS]
      sendMessage({ type: 'command', topic: 'manipulator', joint_positions: [...INITIAL_POSITIONS] })
    },
    onDisconnected() {
      isConnected.value = false
    },
    onMessage(_ws: WebSocket, event: MessageEvent) {
      if (event.data instanceof Blob) {
        handleBinaryMessage(event.data)
      } else if (event.data instanceof ArrayBuffer) {
        handleBinaryMessage(new Blob([event.data]))
      } else if (typeof event.data === 'string') {
        handleTextMessage(event.data)
      }
    },
  })
}

async function handleBinaryMessage(blob: Blob) {
  const buf = await blob.arrayBuffer()
  const view = new DataView(buf)
  if (buf.byteLength < 10) return
  const messageType = view.getUint8(0)
  if (messageType !== 0x01) return

  const cameraIdByte = view.getUint8(1)
  const cameraId = CAMERA_ID_MAP[cameraIdByte]
  if (!cameraId) return

  // Bytes 2-9: uint64 big-endian timestamp (10 bytes total header)
  const jpegData = buf.slice(10)
  const jpegBlob = new Blob([jpegData], { type: 'image/jpeg' })

  const old = cameraFrames[cameraId].value
  if (old) URL.revokeObjectURL(old)
  cameraFrames[cameraId].value = URL.createObjectURL(jpegBlob)
}

function handleTextMessage(text: string) {
  // Stores are called here (not at module scope) so Pinia is guaranteed to be
  // installed before any message arrives.
  const robotStore = useRobotStore()
  const recordingStore = useRecordingStore()

  try {
    const msg = JSON.parse(text)
    if (msg.type === 'status') {
      robotStore.updateStatus(msg as RobotStatus)
    } else if (msg.type === 'recording_state') {
      const rs = msg as RecordingState
      recordingStore.setRecording(rs.recording, rs.session)
    } else if (msg.type === 'preview_ready') {
      const pr = msg as PreviewReady
      notification.success({
        title: 'Preview ready',
        content: `recordings/${pr.session}/preview/`,
        duration: 8000,
        keepAliveOnHover: true,
      })
    }
  } catch (e) {
    console.error('Failed to parse WS message', e)
  }
}

export function sendMessage(msg: object) {
  if (ws) {
    ws.send(JSON.stringify(msg))
  }
}

/**
 * Returns the singleton WebSocket connection.
 * Must be called after Pinia is installed (i.e., from inside a component or App.vue setup).
 */
export function useWebSocketSingleton() {
  if (!ws) {
    initWebSocket()
  }
  return { isConnected, cameraFrames, sendMessage }
}
