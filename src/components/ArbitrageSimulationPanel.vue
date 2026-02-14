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
  rebalanceArbitrageWallets,
  getSpreadSeries,
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
const opportunitiesLimit = 500;
const rebalancing = ref(false);

const fallbackPairs = [
  "BTCEUR",
  "BTCUSD",
  "BTCUSDT",
  "ETHEUR",
  "ETHUSD",
  "ETHUSDT",
  "SOLEUR",
  "SOLUSD",
  "SOLUSDT",
  "BNBEUR",
  "BNBUSD",
  "BNBUSDT",
  "ADAEUR",
  "ADAUSD",
  "ADAUSDT",
  "ETHBTC",
  "SOLBTC",
  "SOLETH",
  "BNBBTC",
  "BNBETH",
  "ADABTC",
  "ADAETH",
  "ADABNB",
];
const selectedBaseCurrency = ref<string>("");
const selectedQuoteCurrency = ref<string>("");
const simulationVolumeUsd = ref<number>(1000);
const performanceCanvas = ref<HTMLCanvasElement | null>(null);
let performanceChart: Chart | null = null;

const availablePairs = computed(() => {
  const fromBackend = status.value?.symbols ?? [];
  const allPairs = fromBackend.length ? fromBackend : fallbackPairs;
  return Array.from(new Set(allPairs.map((pair) => pair.toUpperCase())));
});

const quoteSuffixes = [
  "USDT",
  "USDC",
  "EUR",
  "USD",
  "AVAX",
  "LINK",
  "DOT",
  "XRP",
  "BNB",
  "SOL",
  "ADA",
  "BTC",
  "ETH",
];

function splitTradingPair(
  symbol: string,
): { base: string; quote: string } | null {
  const normalized = symbol.toUpperCase();
  for (const suffix of quoteSuffixes) {
    if (normalized.endsWith(suffix) && normalized.length > suffix.length) {
      const base = normalized.slice(0, -suffix.length);
      return { base, quote: suffix };
    }
  }
  return null;
}

const parsedPairs = computed(() =>
  availablePairs.value
    .map((symbol) => {
      const parsed = splitTradingPair(symbol);
      if (!parsed) return null;
      return { symbol, ...parsed };
    })
    .filter(
      (item): item is { symbol: string; base: string; quote: string } =>
        item !== null,
    ),
);

const baseCurrencies = computed(() =>
  Array.from(new Set(parsedPairs.value.map((pair) => pair.base))).sort(),
);

const quoteCurrencies = computed(() => {
  const candidates = selectedBaseCurrency.value
    ? parsedPairs.value.filter(
        (pair) => pair.base === selectedBaseCurrency.value,
      )
    : parsedPairs.value;
  return Array.from(new Set(candidates.map((pair) => pair.quote)))
    .filter((quote) => quote !== "BNB")
    .sort();
});

const matchingPairs = computed(() =>
  parsedPairs.value
    .filter((pair) => {
      if (
        selectedBaseCurrency.value &&
        pair.base !== selectedBaseCurrency.value
      )
        return false;
      if (
        selectedQuoteCurrency.value &&
        pair.quote !== selectedQuoteCurrency.value
      )
        return false;
      return true;
    })
    .map((pair) => pair.symbol),
);

const activeSymbols = computed(() => {
  if (!selectedBaseCurrency.value && !selectedQuoteCurrency.value) return [];
  return matchingPairs.value;
});

const PAGE_SIZE = 26;
const currentPage = ref(1);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(opportunities.value.length / PAGE_SIZE)),
);

const visiblePages = computed(() => {
  const total = totalPages.value;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const current = currentPage.value;
  const pages: number[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  if (start > 2) pages.push(-1);
  for (let i = start; i <= end; i++) pages.push(i);
  if (end < total - 1) pages.push(-2);
  pages.push(total);
  return pages;
});

const paginatedOpportunities = computed(() => {
  const page = Math.min(currentPage.value, totalPages.value);
  const start = (page - 1) * PAGE_SIZE;
  return opportunities.value.slice(start, start + PAGE_SIZE);
});

function goToPage(page: number): void {
  currentPage.value = Math.max(1, Math.min(page, totalPages.value));
}

let socket: WebSocket | null = null;
let refreshTimer: number | null = null;
let tickTimer: number | null = null;
const now = ref(Date.now());

function timeAgo(iso: string): string {
  const diff = Math.max(
    0,
    Math.floor((now.value - new Date(iso).getTime()) / 1000),
  );
  if (diff < 60) return `há ${diff}s`;
  if (diff < 3600) return `há ${Math.floor(diff / 60)}m`;
  return `há ${Math.floor(diff / 3600)}h`;
}

const acceptedOpportunities = computed(() =>
  opportunities.value.filter((item) => item.status === "accepted"),
);

const acceptedTradesTotal = computed(() => trades.value.length);

const acceptedTradesHistory = computed(() =>
  trades.value
    .slice()
    .sort(
      (left, right) =>
        new Date(right.timestamp).getTime() -
        new Date(left.timestamp).getTime(),
    ),
);

const exchangeInventory = computed(() => {
  const inventory = status.value?.inventory_by_exchange ?? {};
  return Object.entries(inventory).map(([exchange, wallet]) => ({
    exchange,
    quoteAsset: wallet.quote_asset,
    quoteBalance: wallet.quote_balance,
    baseAsset: wallet.base_asset,
    baseBalance: wallet.base_balance,
    totalValueUsd: wallet.total_value_usd ?? wallet.quote_balance,
    assetBalances: Object.entries(wallet.asset_balances ?? {}).map(
      ([asset, balance]) => ({
        asset,
        balance,
      }),
    ),
  }));
});

const walletCryptoColumns = computed(() => {
  const allAssets = new Set<string>();
  for (const wallet of exchangeInventory.value) {
    for (const asset of wallet.assetBalances) {
      allAssets.add(asset.asset.toUpperCase());
    }
  }
  return Array.from(allAssets).sort();
});

function walletBalanceForAsset(
  wallet: {
    baseAsset: string;
    baseBalance: number;
    assetBalances: Array<{ asset: string; balance: number }>;
  },
  asset: string,
): number {
  const match = wallet.assetBalances.find(
    (entry) => entry.asset.toUpperCase() === asset.toUpperCase(),
  );
  if (match) {
    return match.balance;
  }
  if (wallet.baseAsset.toUpperCase() === asset.toUpperCase()) {
    return wallet.baseBalance;
  }
  return 0;
}

const averageNetSpread = computed(() => {
  if (!acceptedOpportunities.value.length) return 0;
  const total = acceptedOpportunities.value.reduce(
    (acc, item) => acc + item.net_spread_pct,
    0,
  );
  return total / acceptedOpportunities.value.length;
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

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("pt-PT", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function statusLabel(statusValue: ArbitrageOpportunity["status"]): string {
  if (statusValue === "accepted") return "Accepted";
  if (statusValue === "no_funds") return "No Funds";
  if (statusValue === "insufficient_liquidity") return "Insufficient Liquidity";
  return "Discarded";
}

function networkFeeLabel(item: ArbitrageOpportunity): string {
  const feeCost = item.network_cost_usd ?? 0;
  const feeUnits = item.network_fee_units ?? 0;
  const feeAsset = item.network_fee_asset ?? "";
  if (!feeCost || !feeUnits || !feeAsset) {
    return formatUsd(feeCost);
  }
  return `⛽ ${feeUnits.toFixed(4)} ${feeAsset} (${formatUsd(feeCost)})`;
}

function latencyText(latencyMs: number): string {
  if (latencyMs > 900) return "Alta";
  if (latencyMs > 450) return "Média";
  return "Baixa";
}

function latencyClass(latencyMs: number): string {
  if (latencyMs > 900) return "alta";
  if (latencyMs > 450) return "media";
  return "baixa";
}

function onCurrencyChange(): void {
  currentPage.value = 1;
  void loadData();
}

function onSimulationVolumeChange(): void {
  if (
    !Number.isFinite(simulationVolumeUsd.value) ||
    simulationVolumeUsd.value <= 0
  ) {
    simulationVolumeUsd.value = 1000;
  }
  void loadData();
}

async function onRebalance(): Promise<void> {
  if (rebalancing.value) return;
  rebalancing.value = true;
  try {
    const result = await rebalanceArbitrageWallets();
    status.value = result.snapshot;
    await loadData();
  } catch {
    error.value = "Não foi possível executar o rebalance.";
  } finally {
    rebalancing.value = false;
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
    await setSimulationVolumeUsd(simulationVolumeUsd.value);
    const [statusData, opportunitiesData, tradesData, spreadData] =
      await Promise.all([
        getArbitrageStatus(),
        getArbitrageOpportunities(
          opportunitiesLimit,
          activeSymbols.value,
          simulationVolumeUsd.value,
        ),
        getArbitrageTrades(5000, activeSymbols.value),
        getSpreadSeries(40),
      ]);

    status.value = statusData;
    if (
      selectedBaseCurrency.value &&
      !baseCurrencies.value.includes(selectedBaseCurrency.value)
    ) {
      selectedBaseCurrency.value = "";
    }
    if (
      selectedQuoteCurrency.value &&
      !quoteCurrencies.value.includes(selectedQuoteCurrency.value)
    ) {
      selectedQuoteCurrency.value = "";
    }
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

  tickTimer = window.setInterval(() => {
    now.value = Date.now();
  }, 1000);

  refreshTimer = window.setInterval(() => {
    void Promise.all([
      getArbitrageOpportunities(
        opportunitiesLimit,
        activeSymbols.value,
        simulationVolumeUsd.value,
      ),
      getArbitrageTrades(5000, activeSymbols.value),
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
  if (tickTimer) {
    window.clearInterval(tickTimer);
  }
  socket?.close();
  performanceChart?.destroy();
  performanceChart = null;
});

watch(cumulativePnlSeries, () => {
  renderPerformanceChart();
});

watch(simulationVolumeUsd, (value) => {
  if (!Number.isFinite(value) || value <= 0) return;
  void setSimulationVolumeUsd(value);
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
          <label for="base-currency">Moeda base</label>
          <select
            id="base-currency"
            v-model="selectedBaseCurrency"
            @change="onCurrencyChange"
          >
            <option value="">Todas</option>
            <option v-for="base in baseCurrencies" :key="base" :value="base">
              {{ base }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label for="quote-currency">Moeda cotada</label>
          <select
            id="quote-currency"
            v-model="selectedQuoteCurrency"
            @change="onCurrencyChange"
          >
            <option value="">Todas</option>
            <option
              v-for="quote in quoteCurrencies"
              :key="quote"
              :value="quote"
            >
              {{ quote }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label for="simulation-volume">Volume de Simulação (US$)</label>
          <input
            id="simulation-volume"
            v-model.number="simulationVolumeUsd"
            type="number"
            min="1"
            step="100"
            @change="onSimulationVolumeChange"
          />
        </div>
      </div>

      <div class="metrics">
        <div class="metric">
          <span>Total aceite</span>
          <strong>{{ acceptedTradesTotal }}</strong>
        </div>
        <div class="metric">
          <span>P&L acumulado</span>
          <strong>{{ formatUsd(status?.total_pnl_usd ?? 0) }}</strong>
        </div>
        <div class="metric">
          <span>Portfólio total</span>
          <strong>{{ formatUsd(status?.portfolio_total_usd ?? 0) }}</strong>
        </div>
        <div class="metric">
          <span>Volume de Simulação atual</span>
          <strong>{{ formatUsd(simulationVolumeUsd) }}</strong>
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

      <div class="inventory-section">
        <div class="inventory-header">
          <h3>Carteiras por Exchange</h3>
          <button
            class="rebalance-btn"
            :disabled="rebalancing"
            @click="onRebalance"
          >
            {{ rebalancing ? "A reequilibrar..." : "Rebalance" }}
          </button>
        </div>
        <div class="inventory-table-wrap">
          <table class="inventory-table">
            <thead>
              <tr>
                <th>Exchange</th>
                <th>Saldo USDT</th>
                <th
                  v-for="asset in walletCryptoColumns"
                  :key="`head-${asset}`"
                  class="crypto-col-head"
                >
                  {{ asset }}
                </th>
                <th>Valor Total (USD)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!exchangeInventory.length">
                <td
                  :colspan="3 + walletCryptoColumns.length"
                  class="inventory-empty"
                >
                  Saldos indisponíveis.
                </td>
              </tr>
              <tr v-for="wallet in exchangeInventory" :key="wallet.exchange">
                <td>{{ wallet.exchange }}</td>
                <td>{{ formatUsd(wallet.quoteBalance) }}</td>
                <td
                  v-for="asset in walletCryptoColumns"
                  :key="`${wallet.exchange}-${asset}`"
                  class="crypto-balances-cell"
                >
                  {{ walletBalanceForAsset(wallet, asset).toFixed(3) }}
                </td>
                <td>{{ formatUsd(wallet.totalValueUsd) }}</td>
              </tr>
            </tbody>
          </table>
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
              <th class="network-fee-head">Gas</th>
              <th>P&L Esperado</th>
              <th>Latência</th>
              <th>Atualização</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="10">A carregar dados...</td>
            </tr>
            <tr v-else-if="!opportunities.length">
              <td colspan="10">Sem oportunidades recebidas.</td>
            </tr>
            <tr
              v-for="item in paginatedOpportunities"
              :key="`${item.symbol}-${item.buy_exchange}-${item.sell_exchange}`"
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
              <td class="network-fee-cell">
                {{ networkFeeLabel(item) }}
              </td>
              <td
                :class="item.expected_profit_usd >= 0 ? 'positive' : 'negative'"
              >
                {{ formatUsd(item.expected_profit_usd) }}
              </td>
              <td>
                <span class="badge" :class="latencyClass(item.latency_ms)">
                  {{ latencyText(item.latency_ms) }}
                </span>
              </td>
              <td>
                <span
                  v-if="item.buy_book_updated_at || item.sell_book_updated_at"
                  class="update-ts"
                >
                  {{
                    timeAgo(
                      [item.buy_book_updated_at, item.sell_book_updated_at]
                        .filter(Boolean)
                        .sort()[0]!,
                    )
                  }}
                </span>
                <span v-else>—</span>
              </td>
              <td>
                <span class="status-pill" :class="item.status">{{
                  statusLabel(item.status)
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="totalPages > 1" class="pagination">
          <button :disabled="currentPage <= 1" @click="goToPage(1)">«</button>
          <button
            :disabled="currentPage <= 1"
            @click="goToPage(currentPage - 1)"
          >
            ‹
          </button>
          <template v-for="page in visiblePages" :key="page">
            <span v-if="page < 0" class="ellipsis">…</span>
            <button
              v-else
              :class="{ active: page === currentPage }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
          </template>
          <button
            :disabled="currentPage >= totalPages"
            @click="goToPage(currentPage + 1)"
          >
            ›
          </button>
          <button
            :disabled="currentPage >= totalPages"
            @click="goToPage(totalPages)"
          >
            »
          </button>
          <span class="page-info">{{ opportunities.length }} resultados</span>
        </div>
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
          <h3>Histórico de Trocas Aceites</h3>
          <div class="trades-history-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data/Hora</th>
                  <th>Moeda</th>
                  <th>Compra</th>
                  <th>Venda</th>
                  <th>Tamanho</th>
                  <th>P&L</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!acceptedTradesHistory.length">
                  <td colspan="6">Ainda não há trocas aceites.</td>
                </tr>
                <tr
                  v-for="trade in acceptedTradesHistory"
                  :key="
                    trade.timestamp + trade.buy_exchange + trade.sell_exchange
                  "
                >
                  <td>{{ formatDateTime(trade.timestamp) }}</td>
                  <td>{{ trade.symbol_name || trade.symbol }}</td>
                  <td>{{ trade.buy_exchange }}</td>
                  <td>{{ trade.sell_exchange }}</td>
                  <td>{{ trade.size.toFixed(4) }}</td>
                  <td :class="trade.pnl_usd >= 0 ? 'positive' : 'negative'">
                    {{ formatUsd(trade.pnl_usd) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
  font-size: 40px;
  text-align: center;
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

.update-ts {
  font-size: 13px;
  color: #a8bad2;
  white-space: nowrap;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.pagination button {
  background: rgba(255, 255, 255, 0.05);
  color: #c9d6ea;
  border: 1px solid rgba(109, 141, 180, 0.2);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 13px;
  cursor: pointer;
  min-width: 32px;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.pagination button:hover:not(:disabled):not(.active) {
  background: rgba(102, 239, 139, 0.1);
  border-color: rgba(102, 239, 139, 0.3);
}

.pagination button.active {
  background: rgba(102, 239, 139, 0.2);
  color: #66ef8b;
  border-color: rgba(102, 239, 139, 0.5);
  font-weight: 700;
}

.pagination button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-info {
  margin-left: 8px;
  font-size: 12px;
  color: #8899b0;
}

.ellipsis {
  color: #8899b0;
  padding: 0 4px;
  font-size: 14px;
  user-select: none;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  max-width: 72px;
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
  background: linear-gradient(135deg, #4b3d1f, #312510);
  color: #ffe7ad;
  border-color: rgba(255, 196, 88, 0.65);
  box-shadow: 0 6px 12px rgba(255, 196, 88, 0.18);
}

.status-pill.insufficient_liquidity {
  background: linear-gradient(135deg, #2b2347, #1d1733);
  color: #d7d2ff;
  border-color: rgba(152, 136, 255, 0.6);
  box-shadow: 0 6px 12px rgba(152, 136, 255, 0.2);
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

.inventory-section {
  margin-top: 16px;
  margin-bottom: 18px;
}

.inventory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.inventory-section h3 {
  margin: 0;
  font-size: 16px;
  color: #dbe9ff;
}

.rebalance-btn {
  border: 1px solid rgba(102, 239, 139, 0.5);
  color: #bfffe0;
  background: rgba(102, 239, 139, 0.12);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.rebalance-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.network-fee-cell {
  color: #c4d3ea;
  font-size: 12px;
  white-space: nowrap;
  text-align: center;
}

.network-fee-head {
  text-align: center;
}

.inventory-table-wrap {
  border-radius: 10px;
  border: 1px solid rgba(120, 151, 189, 0.12);
  background: rgba(255, 255, 255, 0.03);
  overflow: auto;
}

.inventory-table {
  width: 100%;
  border-collapse: collapse;
}

.inventory-table th,
.inventory-table td {
  padding: 8px 6px;
  border-bottom: 1px solid rgba(120, 151, 189, 0.12);
}

.inventory-table th {
  color: #a8bad2;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 11px;
  text-align: left;
}

.crypto-balances-cell {
  min-width: 74px;
  text-align: center;
  font-size: 12px;
}

.crypto-col-head {
  text-align: center !important;
}

.inventory-empty {
  color: #a8bad2;
  text-align: center;
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

.trades-history-wrap {
  max-height: 260px;
  overflow: auto;
  border-radius: 10px;
  border: 1px solid rgba(120, 151, 189, 0.12);
  background: rgba(255, 255, 255, 0.03);
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

@media (max-width: 980px) {
  .split-grid {
    grid-template-columns: 1fr;
  }
}
</style>
