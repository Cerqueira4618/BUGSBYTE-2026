<script setup lang="ts">
import { computed, ref } from 'vue'

type CryptoAsset = {
  symbol: string
  name: string
  popular: boolean
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

const selectedSymbol = ref(assets[0]?.symbol ?? '')
const showPopularOnly = ref(false)

const visibleAssets = computed(() =>
  showPopularOnly.value ? assets.filter((asset) => asset.popular) : assets,
)

const selectedAsset = computed(
  () => visibleAssets.value.find((asset) => asset.symbol === selectedSymbol.value) ?? null,
)

const selectAsset = (symbol: string) => {
  selectedSymbol.value = symbol
}
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

      <p v-if="selectedAsset" class="selected-info">
        Selecionada: <strong>{{ selectedAsset.name }} ({{ selectedAsset.symbol }})</strong>
      </p>
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

@media (max-width: 900px) {
  .asset-grid {
    grid-template-columns: 1fr;
  }
}
</style>
