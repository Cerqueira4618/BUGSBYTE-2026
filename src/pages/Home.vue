<template>
  <section class="home-page">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-icon">⚡</span>
          <span>Simulador de Arbitragem Cripto</span>
        </div>
        <h1 class="hero-title">
          Descubra Oportunidades de
          <span class="gradient-text">Arbitragem</span>
          em Tempo Real
        </h1>
        <p class="hero-description">
          Plataforma avançada para simulação de arbitragem multi-exchange.
          Monitore spreads, analise oportunidades e simule estratégias com dados
          sintéticos de mercado antes de operar com capital real.
        </p>
        <div class="hero-cta">
          <router-link to="/simulador" class="btn-primary">
            <span>Iniciar Simulação</span>
            <span class="arrow">→</span>
          </router-link>
          <a href="#features" class="btn-secondary">Saiba Mais</a>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">4</div>
          <div class="stat-label">Exchanges</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">12+</div>
          <div class="stat-label">Pares Cripto</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">&lt;50s</div>
          <div class="stat-label">Latência Média</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">24/7</div>
          <div class="stat-label">Monitorização</div>
        </div>
      </div>
    </div>

    <!-- Features Section -->
    <div id="features" class="features-section">
      <h2 class="section-title">Recursos Principais</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Análise em Tempo Real</h3>
          <p>
            Monitorização contínua de orderbooks de múltiplas exchanges com
            cálculo automático de spreads brutos e líquidos.
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">⚙️</div>
          <h3>Motor de Simulação</h3>
          <p>
            Execução simulada de trades considerando taxas de exchange, slippage
            e custos de transferência entre carteiras.
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">💰</div>
          <h3>Gestão de Inventário</h3>
          <p>
            Sistema inteligente de rebalanceamento automático entre exchanges
            para maximizar oportunidades de arbitragem.
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">📈</div>
          <h3>Performance Tracking</h3>
          <p>
            Dashboard completo com P&L acumulado, histórico de trades e métricas
            de performance em tempo real.
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">🎯</div>
          <h3>Demo de Crash</h3>
          <p>
            Simule cenários extremos de mercado com injeção de spreads
            artificiais para testar estratégias.
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">🔒</div>
          <h3>Ambiente Seguro</h3>
          <p>
            Simulação 100% isolada sem risco financeiro real. Teste estratégias
            antes de aplicar capital.
          </p>
        </div>
      </div>
    </div>

    <!-- How It Works -->
    <div class="how-it-works">
      <h2 class="section-title">Como Funciona</h2>
      <div class="steps-grid">
        <div class="step-card">
          <div class="step-number">1</div>
          <h3>Monitorização</h3>
          <p>
            O sistema monitora orderbooks de Binance, Kraken, Uphold e Bybit em
            busca de diferenças de preço entre exchanges.
          </p>
        </div>

        <div class="step-card">
          <div class="step-number">2</div>
          <h3>Cálculo de Spread</h3>
          <p>
            Para cada par de exchanges, calcula spread bruto, desconta taxas de
            trading e custos de transferência para obter spread líquido.
          </p>
        </div>

        <div class="step-card">
          <div class="step-number">3</div>
          <h3>Validação</h3>
          <p>
            Verifica disponibilidade de fundos, liquidez suficiente no orderbook
            e viabilidade da operação considerando todos os custos.
          </p>
        </div>

        <div class="step-card">
          <div class="step-number">4</div>
          <h3>Execução Simulada</h3>
          <p>
            Executa trade virtual com timing realista, atualiza inventário e
            regista P&L. Tudo sem risco financeiro real.
          </p>
        </div>
      </div>
    </div>

    <!-- Info Cards -->
    <div class="info-section">
      <div class="info-grid">
        <div class="info-card">
          <h3>🎓 Aprenda Arbitragem</h3>
          <p>
            Arbitragem é a prática de comprar um ativo numa exchange e vendê-lo
            simultaneamente noutra exchange a um preço superior, capturando a
            diferença como lucro. No mundo cripto, as ineficiências de mercado
            criam estas oportunidades frequentemente.
          </p>
        </div>

        <div class="info-card">
          <h3>⚠️ Fatores Críticos</h3>
          <ul>
            <li><strong>Taxas de Trading:</strong> 0.1-0.2% por operação</li>
            <li>
              <strong>Custos de Rede:</strong> Gas fees para transferências
            </li>
            <li><strong>Slippage:</strong> Impacto do volume no preço final</li>
            <li><strong>Latência:</strong> Velocidade de execução é crucial</li>
          </ul>
        </div>

        <div class="info-card">
          <h3>🚀 Próximos Passos</h3>
          <p>
            Acesse o <strong>Simulador</strong> para configurar volume de
            operação, selecionar pares de trading e visualizar oportunidades em
            tempo real. Use o botão "Simular Crash" para testar o sistema em
            condições extremas de mercado.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 80px);
  padding: 0;
  overflow-x: hidden;
}

/* Hero Section */
.hero-section {
  padding: 80px 24px 60px;
  background: linear-gradient(
    180deg,
    rgba(10, 25, 47, 0.95) 0%,
    rgba(15, 28, 45, 0.98) 50%,
    rgba(9, 20, 34, 1) 100%
  );
  position: relative;
}

.hero-section::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
    ellipse at top,
    rgba(34, 197, 94, 0.15) 0%,
    transparent 60%
  );
  pointer-events: none;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
  text-align: center;
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(
    135deg,
    rgba(34, 197, 94, 0.15),
    rgba(102, 239, 139, 0.12)
  );
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: #86efac;
  margin-bottom: 24px;
  animation: fadeInDown 0.6s ease;
}

.badge-icon {
  font-size: 16px;
}

.hero-title {
  margin: 0 0 24px;
  font-size: 56px;
  font-weight: 800;
  line-height: 1.2;
  color: #ecf3ff;
  animation: fadeInUp 0.8s ease;
}

.gradient-text {
  background: linear-gradient(135deg, #22c55e 0%, #66ef8b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-description {
  margin: 0 0 40px;
  font-size: 18px;
  line-height: 1.7;
  color: #b8c9e3;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
  animation: fadeInUp 1s ease;
}

.hero-cta {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  animation: fadeInUp 1.2s ease;
}

.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
  cursor: pointer;
}

.btn-primary {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  border: 1px solid rgba(34, 197, 94, 0.5);
  box-shadow: 0 8px 24px rgba(34, 197, 94, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(34, 197, 94, 0.4);
}

.btn-primary .arrow {
  transition: transform 0.3s ease;
}

.btn-primary:hover .arrow {
  transform: translateX(4px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: #d4e2f4;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  max-width: 900px;
  margin: 60px auto 0;
  position: relative;
  z-index: 1;
}

.stat-card {
  padding: 24px;
  background: linear-gradient(
    135deg,
    rgba(15, 25, 44, 0.9),
    rgba(10, 18, 31, 0.95)
  );
  border: 1px solid rgba(74, 222, 128, 0.25);
  border-radius: 16px;
  text-align: center;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(34, 197, 94, 0.5);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #66ef8b, #22c55e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #8fa9cc;
  font-weight: 500;
}

/* Features Section */
.features-section {
  padding: 80px 24px;
  background: linear-gradient(
    180deg,
    rgba(9, 20, 34, 1) 0%,
    rgba(12, 23, 38, 1) 100%
  );
}

.section-title {
  text-align: center;
  font-size: 40px;
  font-weight: 800;
  margin: 0 0 48px;
  color: #ecf3ff;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  padding: 32px;
  background: linear-gradient(
    135deg,
    rgba(15, 25, 44, 0.8),
    rgba(10, 18, 31, 0.9)
  );
  border: 1px solid rgba(74, 222, 128, 0.2);
  border-radius: 16px;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-6px);
  border-color: rgba(34, 197, 94, 0.4);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-card h3 {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 700;
  color: #d4e2f4;
}

.feature-card p {
  margin: 0;
  line-height: 1.6;
  color: #a8bad2;
  font-size: 15px;
}

/* How It Works */
.how-it-works {
  padding: 80px 24px;
  background: linear-gradient(
    180deg,
    rgba(12, 23, 38, 1) 0%,
    rgba(9, 20, 34, 1) 100%
  );
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.step-card {
  padding: 28px;
  background: linear-gradient(
    135deg,
    rgba(15, 25, 44, 0.7),
    rgba(10, 18, 31, 0.85)
  );
  border: 1px solid rgba(74, 222, 128, 0.2);
  border-radius: 16px;
  position: relative;
  transition: all 0.3s ease;
}

.step-card:hover {
  border-color: rgba(102, 239, 139, 0.4);
  transform: translateY(-4px);
}

.step-number {
  position: absolute;
  top: -16px;
  left: 28px;
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  color: white;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4);
}

.step-card h3 {
  margin: 16px 0 12px;
  font-size: 18px;
  font-weight: 700;
  color: #d4e2f4;
}

.step-card p {
  margin: 0;
  line-height: 1.6;
  color: #8fa9cc;
  font-size: 14px;
}

/* Info Section */
.info-section {
  padding: 80px 24px;
  background: linear-gradient(
    180deg,
    rgba(9, 20, 34, 1) 0%,
    rgba(7, 15, 26, 1) 100%
  );
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.info-card {
  padding: 32px;
  background: linear-gradient(
    135deg,
    rgba(15, 25, 44, 0.6),
    rgba(10, 18, 31, 0.8)
  );
  border: 1px solid rgba(74, 222, 128, 0.25);
  border-radius: 16px;
  transition: all 0.3s ease;
}

.info-card:hover {
  border-color: rgba(255, 206, 112, 0.4);
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.info-card h3 {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 700;
  color: #ecf3ff;
}

.info-card p {
  margin: 0;
  line-height: 1.7;
  color: #b8c9e3;
  font-size: 15px;
}

.info-card ul {
  margin: 0;
  padding-left: 20px;
  color: #b8c9e3;
  line-height: 1.8;
}

.info-card li {
  margin-bottom: 8px;
}

.info-card strong {
  color: #d4e2f4;
}

/* Animations */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .steps-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 40px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .features-grid,
  .steps-grid {
    grid-template-columns: 1fr;
  }

  .hero-cta {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>
