import { defineStore } from 'pinia'
import { ref } from 'vue'
import { connectArbitrageSocket, type ArbitrageStatus, type SpreadPoint } from '../services/arbitrage'

export const useWebSocketStore = defineStore('websocket', () => {
  const socketState = ref<'connected' | 'disconnected'>('disconnected')
  const socket = ref<WebSocket | null>(null)
  const status = ref<ArbitrageStatus | null>(null)
  const spreadSeries = ref<SpreadPoint[]>([])

  function setSocketState(state: 'connected' | 'disconnected') {
    socketState.value = state
  }

  function startArbitrageSocket() {
    if (socket.value?.readyState === WebSocket.OPEN) {
      return
    }

    socket.value = connectArbitrageSocket(({ snapshot, spread_series }) => {
      status.value = snapshot
      spreadSeries.value = spread_series
      socketState.value = 'connected'
    })

    socket.value.addEventListener('open', () => {
      socketState.value = 'connected'
    })

    socket.value.addEventListener('close', () => {
      socketState.value = 'disconnected'
    })

    socket.value.addEventListener('error', () => {
      socketState.value = 'disconnected'
    })
  }

  function disconnectSocket() {
    if (socket.value) {
      socket.value.close()
      socket.value = null
      socketState.value = 'disconnected'
    }
  }

  return {
    socketState,
    socket,
    status,
    spreadSeries,
    setSocketState,
    startArbitrageSocket,
    disconnectSocket,
  }
})
