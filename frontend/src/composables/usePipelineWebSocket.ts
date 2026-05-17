import { onMounted, onUnmounted } from 'vue'

import type { PipelineSnapshot, PipelineWsMessage } from '@/types/pipeline'

function wsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

export function usePipelineWebSocket(
  onSnapshot: (snapshot: PipelineSnapshot) => void,
  onConnected?: (connected: boolean) => void,
) {
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined

  function connect(): void {
    socket = new WebSocket(wsUrl())
    socket.onopen = () => {
      onConnected?.(true)
    }
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data as string) as PipelineWsMessage
      if (payload.type === 'snapshot') {
        onSnapshot(payload.data)
        onConnected?.(true)
      }
    }
    socket.onclose = () => {
      onConnected?.(false)
      reconnectTimer = setTimeout(connect, 3000)
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    socket?.close()
  })
}
