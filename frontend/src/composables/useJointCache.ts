import { ref } from 'vue'

export const INITIAL_POSITIONS: number[] = [0, 0, 0.5, 0, 0, 0, 0, 0, 0, 50]

// Last-sent joint positions — used as the base for all +/- adjustments.
// Never read from robot status; always reflects what was actually commanded.
export const cachedPositions = ref<number[]>([...INITIAL_POSITIONS])

export function resetToInitial(send: (msg: object) => void) {
  cachedPositions.value = [...INITIAL_POSITIONS]
  send({ type: 'command', topic: 'manipulator', joint_positions: [...INITIAL_POSITIONS] })
}
