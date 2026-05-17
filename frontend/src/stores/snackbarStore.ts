import { defineStore } from 'pinia'
import { ref } from 'vue'

export const SNACKBAR_TIMEOUT_MS = 10_000

export type SnackbarColor = 'success' | 'info' | 'error' | 'warning'

export const useSnackbarStore = defineStore('snackbar', () => {
  const visible = ref(false)
  const message = ref('')
  const color = ref<SnackbarColor>('info')
  const timeout = ref(SNACKBAR_TIMEOUT_MS)

  function show(
    text: string,
    options?: { color?: SnackbarColor; timeoutMs?: number },
  ): void {
    message.value = text
    color.value = options?.color ?? 'info'
    timeout.value = options?.timeoutMs ?? SNACKBAR_TIMEOUT_MS
    visible.value = true
  }

  function close(): void {
    visible.value = false
  }

  return {
    visible,
    message,
    color,
    timeout,
    show,
    close,
  }
})
