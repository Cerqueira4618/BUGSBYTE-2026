export type ArbitrageStatus = {
  symbol: string
  trade_size: number
  balance_usd: number
  total_pnl_usd: number
  active_exchanges: string[]
  latest_opportunity: ArbitrageOpportunity | null
}

export type ArbitrageOpportunity = {
  timestamp: string
  status: 'accepted' | 'discarded'
  reason: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  trade_size: number
  gross_spread_pct: number
  net_spread_pct: number
  expected_profit_usd: number
  latency_ms: number
  buy_vwap: number
  sell_vwap: number
}

export type SimulatedTrade = {
  timestamp: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  size: number
  pnl_usd: number
  latency_ms: number
}

export type SpreadPoint = {
  timestamp: string
  spread_gross_pct: number
  spread_net_pct: number
  expected_profit_usd: number
  status: 'accepted' | 'discarded'
  reason: string
  pair: string
  trigger_exchange: string
  latency_ms: number
}

const API_BASE = ((import.meta.env as any).VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000'

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return (await response.json()) as T
}

export async function getArbitrageStatus(): Promise<ArbitrageStatus> {
  return requestJson<ArbitrageStatus>('/api/arbitrage/status')
}

export async function getArbitrageOpportunities(limit = 100): Promise<ArbitrageOpportunity[]> {
  const data = await requestJson<{ items: ArbitrageOpportunity[] }>(`/api/arbitrage/opportunities?limit=${limit}`)
  return data.items
}

export async function getArbitrageTrades(limit = 50): Promise<SimulatedTrade[]> {
  const data = await requestJson<{ items: SimulatedTrade[] }>(`/api/arbitrage/trades?limit=${limit}`)
  return data.items
}

export async function getSpreadSeries(limit = 50): Promise<SpreadPoint[]> {
  const data = await requestJson<{ items: SpreadPoint[] }>(`/api/arbitrage/spread-series?limit=${limit}`)
  return data.items
}

export function connectArbitrageSocket(onSnapshot: (payload: { snapshot: ArbitrageStatus; spread_series: SpreadPoint[] }) => void): WebSocket {
  const wsBase = API_BASE.replace(/^http/, 'ws')
  const socket = new WebSocket(`${wsBase}/ws/arbitrage`)

  socket.addEventListener('message', (event) => {
    try {
      const message = JSON.parse(event.data)
      if (message.type === 'arbitrage_snapshot') {
        onSnapshot({
          snapshot: message.snapshot as ArbitrageStatus,
          spread_series: (message.spread_series ?? []) as SpreadPoint[],
        })
      }
    } catch {
      // ignore malformed ws payload
    }
  })

  return socket
}
