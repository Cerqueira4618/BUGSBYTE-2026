<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";
import {
  connectArbitrageSocket,
  getArbitrageOpportunities,
  getArbitrageStatus,
  getArbitrageTrades,
  getSpreadSeries,
  setExchangeEnabled,
  setArbitrageSymbol,
  setSimulationVolumeUsd,
  type ArbitrageOpportunity,
  type ArbitrageStatus,
  type SimulatedTrade,
  type SpreadPoint,
} from "../services/arbitrage";

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
  Filler,
);

const loading = ref(true);
const error = ref("");
const socketState = ref<"connected" | "disconnected">("disconnected");
const status = ref<ArbitrageStatus | null>(null);
const opportunities = ref<ArbitrageOpportunity[]>([]);
const trades = ref<SimulatedTrade[]>([]);
const spreadSeries = ref<SpreadPoint[]>([]);
const isSwitchingPair = ref(false);
const isUpdatingVolume = ref(false);
const exchangeToggleLoading = ref<Record<string, boolean>>({});

<<<<<<< HEAD
const availablePairs = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "BNBUSDT", "SOLUSDT"];
const selectedPair = ref<string>("");
const performanceCanvas = ref<HTMLCanvasElement | null>(null);
let performanceChart: Chart | null = null;
=======
const availablePairs = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "BNBUSDT", "SOLUSDT", "BTCETH", "ETHBTC"];
const selectedPair = ref<string>("BTCUSDT");
const simulationVolumeInput = ref<number>(2500);
const inventoryExchangeOrder = ["uphold", "binance", "kraken", "bybit"];
>>>>>>> 3aecddf (Ponto 3 e 2)

const activeSymbols = computed(() =>
  selectedPair.value ? [selectedPair.value] : [],
);

let socket: WebSocket | null = null;
let refreshTimer: number | null = null;

const acceptedOpportunities = computed(() =>
  opportunities.value.filter((item) => item.status === "accepted"),
);

const inventoryCards = computed(() => {
  const fromStatus = status.value?.exchange_inventory ?? [];
  const byExchange = new Map(fromStatus.map((item) => [item.exchange.toLowerCase(), item]));
  const states = new Map(
    (status.value?.exchange_states ?? []).map((state) => [state.exchange.toLowerCase(), state.enabled]),
  );

  return inventoryExchangeOrder.map((exchange) => {
    const entry = byExchange.get(exchange);
    return {
      exchange,
      baseBalance: entry?.base_balance ?? 0,
      quoteBalance: entry?.quote_balance ?? 0,
      enabled: states.get(exchange) ?? entry?.enabled ?? true,
    };
  });
});

const uniqueOpportunities = computed(() => {
  const map = new Map<string, ArbitrageOpportunity>();
  for (const item of opportunities.value) {
    const key = `${item.buy_exchange}-${item.sell_exchange}`;
    const existing = map.get(key);
    if (!existing || item.timestamp > existing.timestamp) {
      map.set(key, item);
    }
  }
  return Array.from(map.values());
});

const cumulativePnlSeries = computed(() => {
  const sortedTrades = trades.value
    .slice()
    .sort(
      (left, right) =>
        new Date(left.timestamp).getTime() -
        new Date(right.timestamp).getTime(),
    );

  if (!sortedTrades.length) {
    return [
      {
        time: "Agora",
        pnl: status.value?.total_pnl_usd ?? 0,
      },
    ];
  }

  let runningPnl = 0;
  return sortedTrades.map((trade) => {
    runningPnl += trade.pnl_usd;
    return {
      time: new Date(trade.timestamp).toLocaleTimeString("pt-PT", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      pnl: Number(runningPnl.toFixed(2)),
    };
  });
});

function formatUsd(value: number): string {
  return new Intl.NumberFormat("pt-PT", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPct(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(3)}%`;
}

function formatAsset(value: number, symbol: string): string {
  const maxFractionDigits = symbol === "USDT" || symbol === "USD" ? 2 : 6;
  return `${new Intl.NumberFormat("pt-PT", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxFractionDigits,
  }).format(value)} ${symbol}`;
}

function pairLabel(symbol: string): string {
  const upper = symbol.toUpperCase();
  const knownQuotes = ["USDT", "USDC", "USD", "ETH", "BTC", "EUR"];
  for (const quote of knownQuotes) {
    if (upper.endsWith(quote) && upper.length > quote.length) {
      const base = upper.slice(0, upper.length - quote.length);
      return `${base} / ${quote}`;
    }
  }
  if (upper.length > 3) {
    return `${upper.slice(0, upper.length - 3)} / ${upper.slice(-3)}`;
  }
  return upper;
}

function exchangeLabel(exchange: string): string {
  return exchange.charAt(0).toUpperCase() + exchange.slice(1);
}

async function onToggleExchange(exchange: string, enabled: boolean): Promise<void> {
  try {
    exchangeToggleLoading.value = {
      ...exchangeToggleLoading.value,
      [exchange]: true,
    };
    const snapshot = await setExchangeEnabled(exchange, !enabled);
    status.value = snapshot;

    const [opportunitiesData, tradesData] = await Promise.all([
      getArbitrageOpportunities(60, activeSymbols.value),
      getArbitrageTrades(20, activeSymbols.value),
    ]);
    opportunities.value = opportunitiesData;
    trades.value = tradesData;
  } catch (cause) {
    const details = cause instanceof Error ? cause.message : "erro desconhecido";
    error.value = `Não foi possível ${enabled ? "parar" : "iniciar"} a exchange ${exchangeLabel(exchange)} (${details}).`;
  } finally {
    exchangeToggleLoading.value = {
      ...exchangeToggleLoading.value,
      [exchange]: false,
    };
  }
}

function volatilityText(latencyMs: number): string {
  if (latencyMs > 900) return "Alta";
  if (latencyMs > 450) return "Média";
  return "Baixa";
}

function volatilityClass(latencyMs: number): string {
  if (latencyMs > 900) return "alta";
  if (latencyMs > 450) return "media";
  return "baixa";
}

async function onSymbolChange(): Promise<void> {
  try {
    isSwitchingPair.value = true;
    await setArbitrageSymbol(selectedPair.value);
    await loadData();
  } catch (cause) {
    const details = cause instanceof Error ? cause.message : "erro desconhecido";
    if (details.includes("404") && details.includes("/api/arbitrage/symbol")) {
      error.value = "O backend ativo não suporta troca de par ainda. Reinicia o FastAPI para carregar a rota /api/arbitrage/symbol.";
    } else {
      error.value = `Não foi possível alterar o par de simulação no backend (${details}).`;
    }
  } finally {
    isSwitchingPair.value = false;
  }
}

async function onSimulationVolumeChange(): Promise<void> {
  const nextVolume = Number.isFinite(simulationVolumeInput.value)
    ? Math.max(1, simulationVolumeInput.value)
    : 1;
  simulationVolumeInput.value = nextVolume;

  try {
    isUpdatingVolume.value = true;
    const snapshot = await setSimulationVolumeUsd(nextVolume);
    status.value = snapshot;

    const [opportunitiesData, tradesData, spreadData] = await Promise.all([
      getArbitrageOpportunities(60, activeSymbols.value),
      getArbitrageTrades(20, activeSymbols.value),
      getSpreadSeries(40),
    ]);
    opportunities.value = opportunitiesData;
    trades.value = tradesData;
    spreadSeries.value = spreadData;
  } catch (cause) {
    const details = cause instanceof Error ? cause.message : "erro desconhecido";
    error.value = `Não foi possível atualizar o volume de simulação (${details}).`;
  } finally {
    isUpdatingVolume.value = false;
  }
}

function renderPerformanceChart(): void {
  const canvas = performanceCanvas.value;
  if (!canvas) return;

  const labels = cumulativePnlSeries.value.map((point) => point.time);
  const values = cumulativePnlSeries.value.map((point) => point.pnl);

  if (!performanceChart) {
    performanceChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "P&L Acumulado (USD)",
            data: values,
            borderColor: "#66ef8b",
            backgroundColor: "rgba(102, 239, 139, 0.12)",
            borderWidth: 2,
            fill: true,
            tension: 0.24,
            pointRadius: 2,
            pointHoverRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#dbe9ff",
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Tempo",
              color: "#a8bad2",
            },
            ticks: {
              color: "#b9cae3",
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 8,
            },
            grid: {
              color: "rgba(123, 154, 192, 0.15)",
            },
          },
          y: {
            title: {
              display: true,
              text: "P&L Acumulado (USD)",
              color: "#a8bad2",
            },
            ticks: {
              color: "#b9cae3",
            },
            grid: {
              color: "rgba(123, 154, 192, 0.15)",
            },
          },
        },
      },
    });
    return;
  }

  performanceChart.data.labels = labels;
  const [dataset] = performanceChart.data.datasets;
  if (dataset) {
    dataset.data = values;
  }
  performanceChart.update();
}

async function loadData() {
  try {
    error.value = "";
    const statusData = await getArbitrageStatus();
    status.value = statusData;
    if (statusData.symbol && statusData.symbol !== selectedPair.value) {
      selectedPair.value = statusData.symbol;
    }
    if (statusData.simulation_volume_usd) {
      simulationVolumeInput.value = statusData.simulation_volume_usd;
    }

    const [opportunitiesData, tradesData, spreadData] = await Promise.all([
      getArbitrageOpportunities(60, activeSymbols.value),
      getArbitrageTrades(20, activeSymbols.value),
      getSpreadSeries(40),
    ]);

    opportunities.value = opportunitiesData;
    trades.value = tradesData;
    spreadSeries.value = spreadData;
  } catch {
    error.value =
      "Não foi possível carregar dados do backend. Inicia o FastAPI (uvicorn app.main:app --reload --port 8000). O frontend tenta automaticamente as portas 8000 e 8001.";
  } finally {
    loading.value = false;
  }
}

function startSocket() {
  socket = connectArbitrageSocket(({ snapshot, spread_series }) => {
    status.value = snapshot;
    if (snapshot.symbol && snapshot.symbol !== selectedPair.value) {
      selectedPair.value = snapshot.symbol;
    }
    if (snapshot.simulation_volume_usd) {
      simulationVolumeInput.value = snapshot.simulation_volume_usd;
    }
    spreadSeries.value = spread_series;
    socketState.value = "connected";
  });

  socket.addEventListener("open", () => {
    socketState.value = "connected";
  });

  socket.addEventListener("close", () => {
    socketState.value = "disconnected";
  });

  socket.addEventListener("error", () => {
    socketState.value = "disconnected";
  });
}

onMounted(async () => {
  await loadData();
  startSocket();
  renderPerformanceChart();

  refreshTimer = window.setInterval(() => {
    void Promise.all([
      getArbitrageOpportunities(60, activeSymbols.value),
      getArbitrageTrades(20, activeSymbols.value),
    ]).then(([opportunitiesData, tradesData]) => {
      opportunities.value = opportunitiesData;
      trades.value = tradesData;
    });
  }, 3000);
});

onBeforeUnmount(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer);
  }
  socket?.close();
  performanceChart?.destroy();
  performanceChart = null;
});

watch(cumulativePnlSeries, () => {
  renderPerformanceChart();
});
</script>

<template>
  <section class="main-page">
    <div class="panel">
      <div class="panel-header">
        <h2>Simulador de Captura de Arbitragem</h2>
        <p>Painel de validação do backend em tempo real (REST + WebSocket).</p>
        <p class="connection" :class="socketState">WS: {{ socketState }}</p>
      </div>

      <p v-if="error" class="error-box">{{ error }}</p>

      <div class="filter-bar">
        <div class="filter-group">
          <label for="pair">Par de Simulação</label>
          <select id="pair" v-model="selectedPair" @change="onSymbolChange">
<<<<<<< HEAD
            <option value="">Todos</option>
            <option
              v-for="symbol in availablePairs"
              :key="symbol"
              :value="symbol"
            >
              {{ symbol.slice(0, -4) }} / {{ symbol.slice(-4) }}
=======
            <option v-for="symbol in availablePairs" :key="symbol" :value="symbol">
              {{ pairLabel(symbol) }}
>>>>>>> 3aecddf (Ponto 3 e 2)
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label for="simulation-volume">Volume de Simulação (US$)</label>
          <input
            id="simulation-volume"
            v-model.number="simulationVolumeInput"
            type="number"
            min="1"
            step="100"
            @change="onSimulationVolumeChange"
          />
        </div>

        <span v-if="isSwitchingPair">A trocar par no backend...</span>
        <span v-if="isUpdatingVolume">A atualizar volume...</span>
      </div>

      <div class="inventory-grid">
        <div
          v-for="item in inventoryCards"
          :key="item.exchange"
          class="inventory-card"
          :class="{ disabled: !item.enabled }"
        >
          <h3>{{ exchangeLabel(item.exchange) }}</h3>
          <p>{{ formatAsset(item.quoteBalance, status?.quote_asset ?? "USDT") }}</p>
          <p>{{ formatAsset(item.baseBalance, status?.base_asset ?? "BTC") }}</p>
          <button
            class="exchange-toggle-btn"
            :disabled="exchangeToggleLoading[item.exchange]"
            @click="onToggleExchange(item.exchange, item.enabled)"
          >
            {{ exchangeToggleLoading[item.exchange] ? "A atualizar..." : item.enabled ? "Parar" : "Iniciar" }}
          </button>
        </div>
      </div>

      <div class="metrics">
        <div class="metric">
          <span>Oportunidades aceites</span>
          <strong>{{ acceptedOpportunities.length }}</strong>
        </div>
        <div class="metric">
          <span>Volume de simulação</span>
          <strong>{{ formatUsd(status?.simulation_volume_usd ?? 0) }}</strong>
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
          <span>Última latência</span>
          <strong
            >{{
              (status?.latest_opportunity?.latency_ms ?? 0).toFixed(1)
            }}
            ms</strong
          >
        </div>
        <div class="metric">
          <span>Exchanges ativas</span>
          <strong>{{ status?.active_exchanges?.join(", ") || "-" }}</strong>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Moeda</th>
              <th>Compra (A)</th>
              <th>Venda (B)</th>
              <th>Spread Bruto</th>
              <th>Spread Líquido</th>
              <th>P&L Esperado</th>
              <th>Latência (ms)</th>
              <th>Volatilidade</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9">A carregar dados...</td>
            </tr>
            <tr v-else-if="!uniqueOpportunities.length">
              <td colspan="9">Sem oportunidades recebidas.</td>
            </tr>
            <tr
              v-for="item in uniqueOpportunities"
              :key="`${item.buy_exchange}-${item.sell_exchange}`"
            >
              <td>
                <div class="symbol-cell">
                  <strong>{{ item.symbol_name || item.symbol }}</strong>
                  <small>{{ item.symbol }}</small>
                </div>
              </td>
              <td>{{ item.buy_exchange }}</td>
              <td>{{ item.sell_exchange }}</td>
              <td :class="item.gross_spread_pct >= 0 ? 'positive' : 'negative'">
                {{ formatPct(item.gross_spread_pct) }}
              </td>
              <td :class="item.net_spread_pct >= 0 ? 'positive' : 'negative'">
                {{ formatPct(item.net_spread_pct) }}
              </td>
              <td
                :class="item.expected_profit_usd >= 0 ? 'positive' : 'negative'"
              >
                {{ formatUsd(item.expected_profit_usd) }}
              </td>
              <td>{{ item.latency_ms.toFixed(1) }}</td>
              <td>
                <span class="badge" :class="volatilityClass(item.latency_ms)">
                  {{ volatilityText(item.latency_ms) }}
                </span>
              </td>
              <td>
<<<<<<< HEAD
                <span class="status-pill" :class="item.status">{{
                  item.status
                }}</span>
=======
                <span class="status-pill" :class="item.status">
                  {{ item.status === "no_funds" ? "No Funds" : item.status }}
                </span>
>>>>>>> 3aecddf (Ponto 3 e 2)
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="split-grid">
        <div class="chart-section">
          <h3>Gráfico de Performance Acumulada</h3>
          <p class="chart-caption">Eixo X: Tempo | Eixo Y: P&amp;L Acumulado</p>
          <div class="chart-wrap">
            <canvas
              ref="performanceCanvas"
              aria-label="Curva de P&L acumulado"
            ></canvas>
          </div>
        </div>

        <div class="trades-section">
          <h3>Execuções Simuladas</h3>
          <ul>
            <li
              v-for="trade in trades.slice().reverse().slice(0, 5)"
              :key="trade.timestamp + trade.buy_exchange + trade.sell_exchange"
            >
              {{ trade.symbol_name || trade.symbol }} |
              {{ trade.buy_exchange }} → {{ trade.sell_exchange }} |
              {{ formatUsd(trade.pnl_usd) }}
            </li>
            <li v-if="!trades.length">Ainda não há execuções simuladas.</li>
          </ul>
        </div>

        <div class="trades-section">
          <h3>Série de Spread (últimos 6)</h3>
          <ul>
            <li
              v-for="item in spreadSeries.slice(-6)"
              :key="item.timestamp + item.pair"
            >
              {{ item.pair }} | {{ formatPct(item.spread_net_pct) }} |
              {{ item.latency_ms.toFixed(1) }} ms
            </li>
            <li v-if="!spreadSeries.length">
              Ainda não há dados de série temporal.
            </li>
          </ul>
        </div>
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
  background: linear-gradient(
    180deg,
    rgba(15, 25, 44, 0.94) 0%,
    rgba(10, 18, 31, 0.96) 100%
  );
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

.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  margin: 12px 0 6px;
  color: #c9d6ea;
}

.inventory-grid {
  margin: 12px 0 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.inventory-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(120, 151, 189, 0.16);
  border-radius: 10px;
  padding: 10px 12px;
}

.inventory-card h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #f4f8ff;
}

.inventory-card p {
  margin: 0;
  color: #b8cae3;
  font-size: 13px;
}

.inventory-card p + p {
  margin-top: 4px;
}

.inventory-card.disabled {
  opacity: 0.75;
}

.exchange-toggle-btn {
  margin-top: 10px;
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(102, 239, 139, 0.35);
  background: rgba(102, 239, 139, 0.12);
  color: #dfffe9;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
  cursor: pointer;
}

.exchange-toggle-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 140px;
}

.filter-group label {
  font-size: 13px;
  color: #e5edff;
  font-weight: 600;
}

.filter-group select {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(102, 239, 139, 0.35);
  color: #e6f7ff;
  border-radius: 8px;
  padding: 8px 10px;
  outline: none;
}

.filter-group input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(102, 239, 139, 0.35);
  color: #e6f7ff;
  border-radius: 8px;
  padding: 8px 10px;
  outline: none;
}

.filter-group input:focus {
  border-color: #66ef8b;
  box-shadow: 0 0 0 2px rgba(102, 239, 139, 0.25);
}

.filter-group select:focus {
  border-color: #66ef8b;
  box-shadow: 0 0 0 2px rgba(102, 239, 139, 0.25);
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

.symbol-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.symbol-cell small {
  color: #90a3c2;
  font-size: 12px;
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

.badge.media {
  background: rgba(255, 206, 112, 0.14);
  color: #ffd27a;
}

.badge.alta {
  background: rgba(255, 124, 124, 0.16);
  color: #ff8f8f;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 5px 12px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.1px;
  text-transform: capitalize;
  background: linear-gradient(135deg, #2d1b22, #23141c);
  color: #ffd8d8;
  border: 1.2px solid rgba(255, 95, 95, 0.6);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
}

.status-pill.accepted {
  background: linear-gradient(135deg, #103428, #0b2620);
  color: #bfffe0;
  border-color: rgba(102, 239, 139, 0.6);
  box-shadow: 0 6px 12px rgba(102, 239, 139, 0.2);
}

.status-pill.discarded {
  background: linear-gradient(135deg, #3a1f28, #2c161d);
  color: #ffd8d8;
  border-color: rgba(255, 120, 120, 0.65);
  box-shadow: 0 6px 12px rgba(255, 120, 120, 0.18);
}

.status-pill.no_funds {
  background: linear-gradient(135deg, #382f12, #2a230f);
  color: #ffe5a9;
  border-color: rgba(255, 201, 106, 0.7);
  box-shadow: 0 6px 12px rgba(255, 201, 106, 0.2);
}

.status-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
  background: rgba(255, 95, 95, 0.25);
  border: 1px solid rgba(255, 95, 95, 0.6);
}

.status-dot.accepted {
  background: rgba(102, 239, 139, 0.5);
  border-color: rgba(102, 239, 139, 0.9);
}

.status-dot.discarded {
  background: rgba(255, 95, 95, 0.5);
  border-color: rgba(255, 95, 95, 0.9);
}

.status-text {
  vertical-align: middle;
}

.split-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.chart-section,
.trades-section {
  margin-top: 16px;
}

.chart-section h3,
.trades-section h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #dbe9ff;
}

.chart-caption {
  margin: 0 0 10px;
  color: #a8bad2;
  font-size: 13px;
}

.chart-wrap {
  height: 240px;
  border-radius: 10px;
  border: 1px solid rgba(120, 151, 189, 0.12);
  background: rgba(255, 255, 255, 0.03);
  padding: 8px;
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

<<<<<<< HEAD
@media (max-width: 980px) {
  .split-grid {
    grid-template-columns: 1fr;
=======
@media (max-width: 1000px) {
  .inventory-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
>>>>>>> 3aecddf (Ponto 3 e 2)
  }
}
</style>
