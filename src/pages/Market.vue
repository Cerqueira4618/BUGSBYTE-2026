<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

type CryptoAsset = {
  symbol: string
  name: string
  popular: boolean
}

type AssetMeta = {
  id: string
  description: string
}

type PricePoint = {
  time: number
  price: number
}

type ChartDaysOption = {
  value: number
  label: string
}

const assets: CryptoAsset[] = [
  { symbol: 'BTC', name: 'Bitcoin', popular: true },
  { symbol: 'ETH', name: 'Ethereum', popular: true },
  { symbol: 'SOL', name: 'Solana', popular: true },
  { symbol: 'BNB', name: 'BNB', popular: true },
  { symbol: 'XRP', name: 'XRP', popular: true },
  { symbol: 'ADA', name: 'Cardano', popular: false },
  { symbol: 'AVAX', name: 'Avalanche', popular: false },
  { symbol: 'DOT', name: 'Polkadot', popular: false },
  { symbol: 'LINK', name: 'Chainlink', popular: false },
]

const assetMeta: Record<string, AssetMeta> = {
  BTC: {
    id: 'bitcoin',
    description: 'A primeira e maior criptomoeda, criada como dinheiro digital descentralizado.',
  },
  ETH: {
    id: 'ethereum',
    description: 'Plataforma de contratos inteligentes usada para apps descentralizados e DeFi.',
  },
  SOL: {
    id: 'solana',
    description: 'Blockchain focada em throughput alto e taxas baixas, popular para DeFi e jogos.',
  },
  BNB: {
    id: 'binancecoin',
    description: 'Token do ecossistema Binance, usado para taxas, pagamentos e utilidades na rede.',
  },
  XRP: {
    id: 'ripple',
    description: 'Token usado na rede Ripple para liquidação rápida e barata entre instituições.',
  },
  ADA: {
    id: 'cardano',
    description: 'Blockchain em camadas com ênfase em pesquisa acadêmica e segurança formal.',
  },
  AVAX: {
    id: 'avalanche-2',
    description: 'Plataforma de sub-redes para apps escaláveis, com foco em velocidade e customização.',
  },
  DOT: {
    id: 'polkadot',
    description: 'Rede que interliga múltiplas parachains, trazendo interoperabilidade entre blockchains.',
  },
  LINK: {
    id: 'chainlink',
    description: 'Rede de oráculos que conecta contratos inteligentes a dados e eventos do mundo real.',
  },
}

const coingeckoApiKey = import.meta.env.VITE_COINGECKO_KEY ?? 'CG-DemoAPIKey'
const ENV_API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')
const API_BASE_CANDIDATES = ENV_API_BASE
  ? [ENV_API_BASE]
  : ['http://127.0.0.1:8000', 'http://localhost:8000', 'http://127.0.0.1:8001', 'http://localhost:8001']
let resolvedApiBase: string | null = ENV_API_BASE ?? null

const chartDaysOptions: ChartDaysOption[] = [
  { value: 7, label: '7 dias' },
  { value: 31, label: '31 dias' },
  { value: 60, label: '2 meses' },
  { value: 90, label: '3 meses' },
]

const selectedSymbol = ref(assets[0]?.symbol ?? '')
const showPopularOnly = ref(false)
const selectedDays = ref(31)
const priceSeries = ref<PricePoint[]>([])
const loadingChart = ref(false)
const chartError = ref('')
const fallbackUsed = ref(false)
const fallbackReason = ref('')

const visibleAssets = computed(() =>
  showPopularOnly.value ? assets.filter((asset) => asset.popular) : assets,
)

const selectedAsset = computed(
  () => visibleAssets.value.find((asset) => asset.symbol === selectedSymbol.value) ?? null,
)

const selectedDaysLabel = computed(
  () => chartDaysOptions.find((option) => option.value === selectedDays.value)?.label ?? '31 dias',
)

const formatEur = (value: number) =>
  new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(value)

const lastPrice = computed(() => {
  const last = priceSeries.value[priceSeries.value.length - 1]
  return last?.price ?? null
})

const priceChangePct = computed(() => {
  if (priceSeries.value.length < 2) return 0
  const first = priceSeries.value[0]?.price ?? 0
  const last = priceSeries.value[priceSeries.value.length - 1]?.price ?? 0
  if (!first) return 0
  return ((last - first) / first) * 100
})

const chartWidth = 540
const chartHeight = 140

const chartPoints = computed(() => {
  if (priceSeries.value.length === 0) return [] as Array<PricePoint & { x: number; y: number }>
  const maxPrice = Math.max(...priceSeries.value.map((p) => p.price))
  const minPrice = Math.min(...priceSeries.value.map((p) => p.price))
  const range = maxPrice - minPrice || 1
  return priceSeries.value
    .map((point, idx) => {
      const x = (idx / Math.max(priceSeries.value.length - 1, 1)) * chartWidth
      const y = chartHeight - ((point.price - minPrice) / range) * chartHeight
      return { ...point, x, y }
    })
})

const sparklinePoints = computed(() =>
  chartPoints.value
    .map((point) => {
      return `${point.x},${point.y}`
    })
    .join(' ')
)

const minPrice = computed(() => {
  if (!priceSeries.value.length) return null
  return Math.min(...priceSeries.value.map((point) => point.price))
})

const maxPrice = computed(() => {
  if (!priceSeries.value.length) return null
  return Math.max(...priceSeries.value.map((point) => point.price))
})

const avgPrice = computed(() => {
  if (!priceSeries.value.length) return null
  const sum = priceSeries.value.reduce((acc, point) => acc + point.price, 0)
  return sum / priceSeries.value.length
})

const startDateLabel = computed(() => {
  const first = priceSeries.value[0]
  if (!first) return '—'
  return new Intl.DateTimeFormat('pt-PT', { day: '2-digit', month: '2-digit' }).format(
    new Date(first.time),
  )
})

const endDateLabel = computed(() => {
  const last = priceSeries.value[priceSeries.value.length - 1]
  if (!last) return '—'
  return new Intl.DateTimeFormat('pt-PT', { day: '2-digit', month: '2-digit' }).format(
    new Date(last.time),
  )
})

const hoveredIndex = ref<number | null>(null)

const hoveredPoint = computed(() => {
  if (hoveredIndex.value === null) return null
  return chartPoints.value[hoveredIndex.value] ?? null
})

const hoveredDateLabel = computed(() => {
  if (!hoveredPoint.value) return ''
  return new Intl.DateTimeFormat('pt-PT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(hoveredPoint.value.time))
})

const updateHoveredPoint = (event: MouseEvent) => {
  const target = event.currentTarget as SVGSVGElement | null
  if (!target || chartPoints.value.length === 0) {
    hoveredIndex.value = null
    return
  }
  const rect = target.getBoundingClientRect()
  if (!rect.width) {
    hoveredIndex.value = null
    return
  }

  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  const index = Math.round(ratio * Math.max(chartPoints.value.length - 1, 0))
  hoveredIndex.value = index
}

const clearHoveredPoint = () => {
  hoveredIndex.value = null
}

const orderedBases = (): string[] => {
  if (!resolvedApiBase) return API_BASE_CANDIDATES
  return [resolvedApiBase, ...API_BASE_CANDIDATES.filter((base) => base !== resolvedApiBase)]
}

const requestBackendHistory = async (symbol: string, days: number): Promise<PricePoint[]> => {
  let lastError = 'Backend indisponível'
  for (const base of orderedBases()) {
    try {
      const response = await fetch(
        `${base}/api/market/history?symbol=${encodeURIComponent(symbol)}&days=${days}`,
      )
      if (!response.ok) {
        lastError = `API ${response.status} em ${base}`
        continue
      }
      const data: { items: { time: number; price: number }[] } = await response.json()
      resolvedApiBase = base
      return (data.items ?? []).map((item) => ({ time: item.time, price: item.price }))
    } catch {
      lastError = `Sem ligação a ${base}`
    }
  }
  throw new Error(lastError)
}

const generateFallbackSeries = (symbol: string, days: number): PricePoint[] => {
  const baseLookup: Record<string, number> = {
    BTC: 42000,
    ETH: 2300,
    SOL: 95,
    BNB: 300,
    XRP: 0.55,
    ADA: 0.45,
    AVAX: 38,
    DOT: 7,
    LINK: 14,
  }

  const base = baseLookup[symbol] ?? 50
  const out: PricePoint[] = []
  let price = base
  for (let i = days - 1; i >= 0; i -= 1) {
    const noise = (Math.sin(i / 2) + Math.cos(i / 3)) * 0.01 * base
    price = Math.max(0.1, price + noise)
    out.unshift({ time: Date.now() - i * 24 * 3600 * 1000, price: parseFloat(price.toFixed(2)) })
  }
  return out
}

const loadAssetDetails = async (symbol: string) => {
  const meta = assetMeta[symbol]
  priceSeries.value = []
  hoveredIndex.value = null
  chartError.value = ''
  fallbackUsed.value = false
  fallbackReason.value = ''

  if (!meta) {
    chartError.value = 'Sem dados para este ativo.'
    return
  }

  loadingChart.value = true
  try {
    const normalized = await requestBackendHistory(symbol, selectedDays.value)

    if (!normalized.length) {
      fallbackUsed.value = true
      fallbackReason.value = 'Sem dados da API'
      priceSeries.value = generateFallbackSeries(symbol, selectedDays.value)
      return
    }

    priceSeries.value = normalized
  } catch (err) {
    try {
      const directUrl =
        `https://api.coingecko.com/api/v3/coins/${meta.id}/market_chart` +
        `?vs_currency=eur&days=${selectedDays.value}&interval=daily&precision=2&x_cg_demo_api_key=${encodeURIComponent(coingeckoApiKey)}`
      const directResponse = await fetch(directUrl)
      if (directResponse.ok) {
        const directData: { prices: [number, number][] } = await directResponse.json()
        const directSeries = (directData?.prices ?? []).map(([time, price]) => ({ time, price }))
        if (directSeries.length) {
          priceSeries.value = directSeries
          return
        }
      }
    } catch {
      // fallback below
    }
    console.error(err)
    fallbackUsed.value = true
    fallbackReason.value = 'Erro ao chamar API/backend'
    priceSeries.value = generateFallbackSeries(symbol, selectedDays.value)
  } finally {
    loadingChart.value = false
  }
}

const selectAsset = (symbol: string) => {
  selectedSymbol.value = symbol
  void loadAssetDetails(symbol)
}

const selectChartDays = (days: number) => {
  if (selectedDays.value === days) return
  selectedDays.value = days
  if (!selectedSymbol.value) return
  void loadAssetDetails(selectedSymbol.value)
}

watch(
  () => visibleAssets.value,
  (list) => {
    if (!list.length) return
    const exists = list.some((asset) => asset.symbol === selectedSymbol.value)
    if (!exists) {
      const first = list[0]
      if (!first) return
      selectedSymbol.value = first.symbol
      void loadAssetDetails(first.symbol)
    }
  },
  { deep: true },
)

onMounted(() => {
  if (selectedSymbol.value) {
    void loadAssetDetails(selectedSymbol.value)
  }
})
</script>

<template>
  <section class="market-page">
    <div class="market-card">
      <h1>Mercado de Criptomoedas</h1>
      <p class="subtitle">Escolha uma criptomoeda e use o filtro para ver as mais populares.</p>

      <div class="controls">
        <label class="checkbox-label">
          <input v-model="showPopularOnly" type="checkbox" />
          <span>Ver apenas as mais populares</span>
        </label>
      </div>

      <div class="asset-grid">
        <button
          v-for="asset in visibleAssets"
          :key="asset.symbol"
          class="asset-item"
          :class="{ 'asset-item-active': selectedSymbol === asset.symbol }"
          @click="selectAsset(asset.symbol)"
        >
          <strong>{{ asset.symbol }}</strong>
          <span>{{ asset.name }}</span>
          <small v-if="asset.popular">Popular</small>
        </button>
      </div>
      <div v-if="selectedAsset" class="asset-detail">
        <div class="detail-header">
          <div>
            <p class="eyebrow">Selecionada</p>
            <h2>{{ selectedAsset.name }} ({{ selectedAsset.symbol }})</h2>
            <p class="description">{{ assetMeta[selectedAsset.symbol]?.description }}</p>
          </div>
          <div class="price-block">
            <p class="label">Preço</p>
            <strong class="price">{{ lastPrice ? formatEur(lastPrice) : '—' }}</strong>
            <span
              class="change"
              :class="{ positive: priceChangePct >= 0, negative: priceChangePct < 0 }"
            >
              {{ priceChangePct >= 0 ? '+' : '' }}{{ priceChangePct.toFixed(2) }}%
              ({{ selectedDaysLabel }})
            </span>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <p class="label">Histórico (EUR, {{ selectedDaysLabel }})</p>
            <span v-if="fallbackUsed" class="badge-fallback">Dados demo · {{ fallbackReason }}</span>
          </div>
          <div class="chart-days">
            <button
              v-for="option in chartDaysOptions"
              :key="option.value"
              type="button"
              class="chart-days-btn"
              :class="{ 'chart-days-btn-active': selectedDays === option.value }"
              @click="selectChartDays(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <div v-if="priceSeries.length" class="chart-stats">
            <span>Mín: {{ minPrice ? formatEur(minPrice) : '—' }}</span>
            <span>Média: {{ avgPrice ? formatEur(avgPrice) : '—' }}</span>
            <span>Máx: {{ maxPrice ? formatEur(maxPrice) : '—' }}</span>
          </div>
          <div class="chart-area" role="img" aria-label="Gráfico de preço em euros">
            <p v-if="loadingChart" class="placeholder">A carregar gráfico...</p>
            <p v-else-if="chartError" class="placeholder">{{ chartError }}</p>
            <p v-else-if="!priceSeries.length" class="placeholder">Sem dados disponíveis.</p>
            <p v-else-if="!chartPoints.length" class="placeholder">Sem dados disponíveis.</p>
            <svg
              v-else
              :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
              preserveAspectRatio="none"
              class="sparkline"
              @mousemove="updateHoveredPoint"
              @mouseleave="clearHoveredPoint"
            >
              <defs>
                <linearGradient id="sparkline-fill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#66ef8b" stop-opacity="0.25" />
                  <stop offset="100%" stop-color="#66ef8b" stop-opacity="0" />
                </linearGradient>
              </defs>
              <line x1="0" y1="0" :x2="chartWidth" y2="0" class="sparkline-grid" />
              <line
                x1="0"
                :y1="chartHeight / 2"
                :x2="chartWidth"
                :y2="chartHeight / 2"
                class="sparkline-grid"
              />
              <line
                x1="0"
                :y1="chartHeight"
                :x2="chartWidth"
                :y2="chartHeight"
                class="sparkline-grid"
              />
              <polyline :points="sparklinePoints" class="sparkline-stroke" />
              <polyline
                :points="sparklinePoints + ` ${chartWidth},${chartHeight} 0,${chartHeight}`"
                class="sparkline-fill"
              />
              <line
                v-if="hoveredPoint"
                :x1="hoveredPoint.x"
                y1="0"
                :x2="hoveredPoint.x"
                :y2="chartHeight"
                class="sparkline-cursor"
              />
              <circle
                v-if="hoveredPoint"
                :cx="hoveredPoint.x"
                :cy="hoveredPoint.y"
                r="4"
                class="sparkline-dot"
              />
            </svg>
            <div v-if="chartPoints.length" class="chart-x-labels">
              <span>{{ startDateLabel }}</span>
              <span>{{ endDateLabel }}</span>
            </div>
            <div
              v-if="hoveredPoint"
              class="chart-tooltip"
              :style="{ left: `${(hoveredPoint.x / chartWidth) * 100}%` }"
            >
              <strong>{{ formatEur(hoveredPoint.price) }}</strong>
              <small>{{ hoveredDateLabel }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.market-page {
  min-height: calc(100vh - 190px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.market-card {
  width: 100%;
  max-width: 980px;
  padding: 28px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(14, 28, 45, 0.92) 0%, rgba(9, 20, 34, 0.92) 100%);
  border: 1px solid rgba(95, 126, 166, 0.2);
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.35);
}

h1 {
  margin: 0;
  font-size: 30px;
}

.subtitle {
  margin: 10px 0 20px;
  color: rgba(232, 240, 252, 0.86);
}

.controls {
  margin-bottom: 18px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: rgba(232, 240, 252, 0.92);
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.asset-item {
  text-align: left;
  display: grid;
  gap: 4px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(95, 126, 166, 0.3);
  background: rgba(7, 18, 31, 0.8);
  color: #fff;
  cursor: pointer;
}

.asset-item-active {
  border-color: rgba(102, 239, 139, 0.8);
  box-shadow: 0 0 0 1px rgba(102, 239, 139, 0.4) inset;
}

.asset-item small {
  color: #66ef8b;
}

.selected-info {
  margin: 20px 0 0;
  color: rgba(232, 240, 252, 0.9);
}

.asset-detail {
  margin-top: 24px;
  padding: 18px;
  border-radius: 14px;
  border: 1px solid rgba(95, 126, 166, 0.28);
  background: linear-gradient(180deg, rgba(11, 24, 40, 0.92) 0%, rgba(6, 14, 23, 0.9) 100%);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.32);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.eyebrow {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  font-size: 12px;
  color: rgba(232, 240, 252, 0.6);
}

.detail-header h2 {
  margin: 0 0 8px;
}

.description {
  margin: 0;
  color: rgba(232, 240, 252, 0.85);
  max-width: 720px;
  line-height: 1.5;
}

.price-block {
  min-width: 180px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(102, 239, 139, 0.35);
  background: rgba(8, 30, 19, 0.55);
  text-align: right;
}

.price-block .label {
  margin: 0;
  font-size: 12px;
  color: rgba(232, 240, 252, 0.65);
}

.price-block .price {
  display: block;
  font-size: 22px;
  margin: 4px 0;
}

.change {
  font-size: 13px;
}

.change.positive {
  color: #66ef8b;
}

.change.negative {
  color: #ff9d9d;
}

.chart-card {
  margin-top: 16px;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chart-card .label {
  margin: 0 0 8px;
  color: rgba(232, 240, 252, 0.7);
}

.chart-days {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-days-btn {
  border: 1px solid rgba(95, 126, 166, 0.35);
  background: rgba(7, 18, 31, 0.78);
  color: rgba(232, 240, 252, 0.85);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}

.chart-days-btn-active {
  border-color: rgba(102, 239, 139, 0.8);
  box-shadow: 0 0 0 1px rgba(102, 239, 139, 0.35) inset;
  color: #ffffff;
}

.chart-stats {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: rgba(232, 240, 252, 0.78);
  font-size: 13px;
}

.chart-area {
  position: relative;
  border-radius: 12px;
  background: radial-gradient(circle at 20% 20%, rgba(102, 239, 139, 0.06), transparent 35%),
    linear-gradient(180deg, rgba(5, 13, 22, 0.95) 0%, rgba(10, 21, 34, 0.95) 100%);
  border: 1px solid rgba(95, 126, 166, 0.25);
  min-height: 200px;
  display: grid;
  place-items: center;
  padding: 12px;
}

.placeholder {
  color: rgba(232, 240, 252, 0.7);
  margin: 0;
}

.sparkline {
  width: 100%;
  height: 180px;
  overflow: visible;
}

.sparkline-grid {
  stroke: rgba(95, 126, 166, 0.26);
  stroke-width: 1;
}

.sparkline-stroke {
  fill: none;
  stroke: #66ef8b;
  stroke-width: 3;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.sparkline-fill {
  fill: url(#sparkline-fill);
  stroke: none;
}

.sparkline-cursor {
  stroke: rgba(232, 240, 252, 0.6);
  stroke-width: 1;
  stroke-dasharray: 4;
}

.sparkline-dot {
  fill: #66ef8b;
  stroke: rgba(9, 20, 34, 0.95);
  stroke-width: 2;
}

.chart-x-labels {
  width: 100%;
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  color: rgba(232, 240, 252, 0.65);
  font-size: 12px;
}

.chart-tooltip {
  position: absolute;
  bottom: 16px;
  transform: translateX(-50%);
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(95, 126, 166, 0.6);
  background: rgba(9, 20, 34, 0.96);
  color: rgba(232, 240, 252, 0.95);
  pointer-events: none;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35);
}

.chart-tooltip strong {
  font-size: 13px;
  line-height: 1.1;
}

.chart-tooltip small {
  font-size: 11px;
  color: rgba(232, 240, 252, 0.72);
}

.badge-fallback {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 206, 112, 0.16);
  color: #ffd27a;
  border: 1px solid rgba(255, 206, 112, 0.5);
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .asset-grid {
    grid-template-columns: 1fr;
  }

  .detail-header {
    flex-direction: column;
  }
}
</style>
