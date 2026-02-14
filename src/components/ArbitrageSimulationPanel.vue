<script setup lang="ts">
const opportunities = [
  {
    pair: 'BTC/USDT',
    buy: 'Binance',
    sell: 'Kraken',
    spread: '+0.92%',
    fees: '-0.18%',
    slippage: '-0.21%',
    transfer: '-0.07%',
    net: '+0.46%',
    volatility: 'Média',
    action: 'Simular'
  },
  {
    pair: 'ETH/USDT',
    buy: 'Coinbase',
    sell: 'Bybit',
    spread: '+0.74%',
    fees: '-0.16%',
    slippage: '-0.14%',
    transfer: '-0.05%',
    net: '+0.39%',
    volatility: 'Baixa',
    action: 'Simular'
  },
  {
    pair: 'SOL/USDT',
    buy: 'OKX',
    sell: 'Gate',
    spread: '+1.18%',
    fees: '-0.22%',
    slippage: '-0.44%',
    transfer: '-0.09%',
    net: '+0.43%',
    volatility: 'Alta',
    action: 'Aguardar'
  }
]
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
      </div>

      <div class="metrics">
        <div class="metric">
          <span>Oportunidades ativas</span>
          <strong>3</strong>
        </div>
        <div class="metric">
          <span>Lucro líquido médio</span>
          <strong>+0.43%</strong>
        </div>
        <div class="metric">
          <span>Risco de volatilidade</span>
          <strong>Médio</strong>
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
              <th>Fees</th>
              <th>Slippage</th>
              <th>Transferência</th>
              <th>Lucro Líquido</th>
              <th>Volatilidade</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in opportunities" :key="`${item.pair}-${item.buy}-${item.sell}`">
              <td>{{ item.pair }}</td>
              <td>{{ item.buy }}</td>
              <td>{{ item.sell }}</td>
              <td class="positive">{{ item.spread }}</td>
              <td class="negative">{{ item.fees }}</td>
              <td class="negative">{{ item.slippage }}</td>
              <td class="negative">{{ item.transfer }}</td>
              <td class="positive">{{ item.net }}</td>
              <td>
                <span class="badge" :class="item.volatility.toLowerCase()">{{ item.volatility }}</span>
              </td>
              <td>
                <button class="row-btn">{{ item.action }}</button>
              </td>
            </tr>
          </tbody>
        </table>
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
  min-width: 960px;
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
</style>
