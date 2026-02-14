<template>
  <section class="home-page">
    <div class="home-card">
      <h1>CryptoByte</h1>
      <p class="lead">
        Plataforma para simulação de arbitragem em cripto, focada em comparar preços entre mercados e analisar oportunidades de forma rápida e visual para tentar encontrar uma boa opurtunidade de negócio.
      </p>

      <div class="summary-grid">
        <article class="summary-item">
          <h2>O que faz</h2>
          <p>
            Executa simulações com dados de mercado para identificar diferença de preço e potencial de
            retorno em operações de compra e venda.
          </p>
        </article>

        <article class="summary-item">
          <h2>Para quem</h2>
          <p>
            Usuários que querem estudar arbitragem de cripto com uma interface simples antes de tomar
            decisões reais.
          </p>
        </article>

        <article class="summary-item">
          <h2>Próximo passo</h2>
          <p>
            Entre na área de login e acesse o Simulador para configurar parâmetros e testar cenários.
          </p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 190px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.home-card {
  width: 100%;
  max-width: 980px;
  padding: 30px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(14, 28, 45, 0.92) 0%, rgba(9, 20, 34, 0.92) 100%);
  border: 1px solid rgba(95, 126, 166, 0.2);
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.35);
}

h1 {
  margin: 0;
  font-size: 32px;
}

.lead {
  margin: 12px 0 24px;
  color: rgba(232, 240, 252, 0.88);
  line-height: 1.6;
}

.summary-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-item {
  padding: 16px;
  border-radius: 12px;
  background: rgba(7, 18, 31, 0.8);
  border: 1px solid rgba(95, 126, 166, 0.2);
}

.summary-item h2 {
  margin: 0 0 8px;
  font-size: 17px;
}

.summary-item p {
  margin: 0;
  color: rgba(232, 240, 252, 0.82);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
