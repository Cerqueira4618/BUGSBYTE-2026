<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  connectArbitrageSocket,
  getArbitrageOpportunities,
  getArbitrageStatus,
  getArbitrageTrades,
  type ArbitrageOpportunity,
  type ArbitrageStatus,
  type SimulatedTrade,
} from '../services/arbitrage'

const loading = ref(true)
const error = ref('')
const status = ref<ArbitrageStatus | null>(null)
const opportunities = ref<ArbitrageOpportunity[]>([])
const trades = ref<SimulatedTrade[]>([])
const socketState = ref<'connected' | 'disconnected'>('disconnected')

let socket: WebSocket | null = null

const acceptedOpportunities = computed(() => opportunities.value.filter((item) => item.status === 'accepted'))

const averageNetSpread = computed(() => {
  if (!acceptedOpportunities.value.length) return 0
  const total = acceptedOpportunities.value.reduce((acc, item) => acc + item.net_spread_pct, 0)
  return total / acceptedOpportunities.value.length
})

const volatilityLabel = computed(() => {
  const latestLatency = status.value?.latest_opportunity?.latency_ms ?? 0
  if (latestLatency > 900) return 'Alta'
  if (latestLatency > 450) return 'Média'
  return 'Baixa'
})

function formatPct(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatUsd(value: number): string {
  return `${value >= 0 ? '+' : ''}$${value.toFixed(2)}`
}

function volatilityClass(latencyMs: number): 'baixa' | 'media' | 'alta' {
  if (latencyMs > 900) return 'alta'
  if (latencyMs > 450) return 'media'
  return 'baixa'
}

function volatilityText(latencyMs: number): 'Baixa' | 'Média' | 'Alta' {
  if (latencyMs > 900) return 'Alta'
  if (latencyMs > 450) return 'Média'
  return 'Baixa'
}

async function loadData() {
  try {
    error.value = ''
    const [statusData, opportunitiesData, tradesData] = await Promise.all([
      getArbitrageStatus(),
      getArbitrageOpportunities(50),
      getArbitrageTrades(20),
    ])
    status.value = statusData
    opportunities.value = opportunitiesData
    trades.value = tradesData
  } catch {
    error.value = 'Não foi possível carregar os dados do backend. Verifica se o FastAPI está ativo na porta 8000.'
  } finally {
    loading.value = false
  }
}

function startSocket() {
  socket = connectArbitrageSocket(({ snapshot }) => {
    status.value = snapshot
    socketState.value = 'connected'
  })
  socket.addEventListener('close', () => {
    socketState.value = 'disconnected'
  })
  socket.addEventListener('error', () => {
    socketState.value = 'disconnected'
  })
}

onMounted(async () => {
  await loadData()
  startSocket()
})

onBeforeUnmount(() => {
  socket?.close()
})
</script>

<template>
  <section class="main-page">
    <div class="panel">
      <div class="panel-header">
        <h2>Simulador de Captura de Arbitragem</h2>
        <p>
          Objetivo: detectar ineficiências entre order books e simular captura de lucro
          líquido automatizada, considerando volatilidade em tempo real.
        </p>
        <p class="connection" :class="socketState">WS: {{ socketState }}</p>
      </div>

      <p v-if="error" class="error-box">{{ error }}</p>

      <div class="metrics">
        <div class="metric">
          <span>Oportunidades ativas</span>
          <strong>{{ acceptedOpportunities.length }}</strong>
        </div>
        <div class="metric">
          <span>Lucro líquido médio</span>
          <strong>{{ formatPct(averageNetSpread) }}</strong>
        </div>
        <div class="metric">
          <span>Risco de volatilidade</span>
          <strong>{{ volatilityLabel }}</strong>
        </div>
        <div class="metric">
          <span>P&L acumulado</span>
          <strong>{{ formatUsd(status?.total_pnl_usd ?? 0) }}</strong>
        </div>
        <div class="metric">
          <span>Saldo simulado</span>
          <strong>{{ formatUsd(status?.balance_usd ?? 0) }}</strong>
        </div>
        <div class="metric">
          <span>Exchanges ativas</span>
          <strong>{{ status?.active_exchanges?.join(', ') || '-' }}</strong>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Par</th>
              <th>Compra (A)</th>
              <th>Venda (B)</th>
              <th>Spread Bruto</th>
              <th>Lucro Líquido</th>
              <th>Lucro Esperado (USD)</th>
              <th>Latência (ms)</th>
              <th>Volatilidade</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9">A carregar dados...</td>
            </tr>
            <tr v-else-if="!opportunities.length">
              <td colspan="9">Sem oportunidades recebidas.</td>
            </tr>
            <tr v-for="item in opportunities" :key="`${item.timestamp}-${item.buy_exchange}-${item.sell_exchange}`">
              <td>{{ item.symbol }}</td>
              <td>{{ item.buy_exchange }}</td>
              <td>{{ item.sell_exchange }}</td>
              <td :class="item.gross_spread_pct >= 0 ? 'positive' : 'negative'">{{ formatPct(item.gross_spread_pct) }}</td>
              <td :class="item.net_spread_pct >= 0 ? 'positive' : 'negative'">{{ formatPct(item.net_spread_pct) }}</td>
              <td :class="item.expected_profit_usd >= 0 ? 'positive' : 'negative'">{{ formatUsd(item.expected_profit_usd) }}</td>
              <td>{{ item.latency_ms.toFixed(1) }}</td>
              <td>
                <span class="badge" :class="volatilityClass(item.latency_ms)">{{ volatilityText(item.latency_ms) }}</span>
              </td>
              <td>{{ item.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="trades-section">
        <h3>Execuções Simuladas</h3>
        <ul>
          <li v-for="trade in trades.slice().reverse().slice(0, 5)" :key="trade.timestamp + trade.buy_exchange + trade.sell_exchange">
            {{ trade.symbol }} | {{ trade.buy_exchange }} → {{ trade.sell_exchange }} | {{ formatUsd(trade.pnl_usd) }}
          </li>
          <li v-if="!trades.length">Ainda não há execuções simuladas.</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.main-page {
  padding: 16px;
}

.panel {
  max-width: 1200px;
  margin: 0 auto;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(15, 25, 44, 0.94) 0%, rgba(10, 18, 31, 0.96) 100%);
  border: 1px solid rgba(109, 141, 180, 0.15);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
  padding: 18px;
}

.panel-header h2 {
  margin: 0 0 8px;
  color: #ecf3ff;
}

.panel-header p {
  margin: 0;
  color: #aebcd3;
  line-height: 1.45;
}

.connection {
  margin-top: 8px;
  font-size: 13px;
}

.connection.connected {
  color: #66ef8b;
}

.connection.disconnected {
  color: #ff9d9d;
}

.error-box {
  margin: 12px 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 116, 116, 0.12);
  border: 1px solid rgba(255, 116, 116, 0.25);
  color: #ffd4d4;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0;
}

.metric {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(120, 151, 189, 0.12);
  border-radius: 10px;
  padding: 12px;
}

.metric span {
  display: block;
  color: #9aa9c0;
  font-size: 13px;
  margin-bottom: 6px;
}

.metric strong {
  color: #f6fbff;
}

.table-wrap {
  overflow-x: auto;
  border-radius: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
}

thead {
  background: rgba(255, 255, 255, 0.04);
}

th,
td {
  padding: 12px 10px;
  border-bottom: 1px solid rgba(123, 154, 192, 0.13);
  text-align: left;
  color: #d9e6f7;
  font-size: 14px;
}

th {
  color: #a8bad2;
  font-weight: 600;
}

.positive {
  color: #66ef8b;
  font-weight: 600;
}

.negative {
  color: #ff8f8f;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.badge.baixa {
  background: rgba(102, 239, 139, 0.14);
  color: #66ef8b;
}

.badge.média {
  background: rgba(255, 206, 112, 0.14);
  color: #ffd27a;
}

.badge.media {
  background: rgba(255, 206, 112, 0.14);
  color: #ffd27a;
}

.badge.alta {
  background: rgba(255, 124, 124, 0.16);
  color: #ff8f8f;
}

.row-btn {
  border: 1px solid rgba(102, 239, 139, 0.45);
  background: rgba(102, 239, 139, 0.08);
  color: #66ef8b;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}

.trades-section {
  margin-top: 16px;
}

.trades-section h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #dbe9ff;
}

.trades-section ul {
  margin: 0;
  padding-left: 18px;
  color: #b9cae3;
}

.trades-section li {
  margin-bottom: 6px;
}
</style>
