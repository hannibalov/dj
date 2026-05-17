import { onMounted, onUnmounted } from 'vue'

export function usePolling(callback: () => void | Promise<void>, intervalMs: number): void {
  let timer: ReturnType<typeof setInterval> | undefined

  onMounted(() => {
    void callback()
    timer = setInterval(() => {
      void callback()
    }, intervalMs)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })
}
