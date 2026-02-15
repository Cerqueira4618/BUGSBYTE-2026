<template>
  <section class="help-page">
    <div class="help-container">
      <header class="help-header">
        <h1>❓ Ajuda e Perguntas Frequentes</h1>
        <p>Tire suas dúvidas sobre a plataforma CryptoByte</p>
      </header>

      <div class="help-sections">
        <article class="help-section">
          <h2>🔐 Login e Autenticação</h2>
          <div class="faq-item">
            <h3>Como faço login no simulador?</h3>
            <p>
              Use a conta de teste: <strong>admin@cryptobyte.com</strong> com senha <strong>123456</strong>. 
              Esta é a única conta válida para acesso ao Simulador de Arbitragem.
            </p>
          </div>
          <div class="faq-item">
            <h3>Posso acessar o Mercado sem login?</h3>
            <p>
              Sim! A página de Mercado está disponível para todos os utilizadores sem necessidade de autenticação. 
              Apenas o Simulador requer login.
            </p>
          </div>
          <div class="faq-item">
            <h3>O que acontece se eu usar credenciais erradas?</h3>
            <p>
              Você verá uma mensagem de erro indicando que as credenciais são inválidas. 
              Certifique-se de usar a conta de teste fornecida.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>📊 Simulador de Arbitragem</h2>
          <div class="faq-item">
            <h3>O que é arbitragem de criptomoedas?</h3>
            <p>
              Arbitragem é a prática de comprar uma criptomoeda em uma exchange onde o preço está mais baixo 
              e vendê-la simultaneamente em outra exchange onde o preço está mais alto, lucrando com a diferença.
            </p>
          </div>
          <div class="faq-item">
            <h3>Como funciona o Volume de Simulação?</h3>
            <p>
              O Volume de Simulação (em US$) determina quanto capital seria usado em cada operação simulada. 
              Valores maiores resultam em lucros potenciais maiores, mas também requerem mais capital disponível.
            </p>
          </div>
          <div class="faq-item">
            <h3>O que significa "Spread Bruto" e "Spread Líquido"?</h3>
            <p>
              <strong>Spread Bruto:</strong> É a diferença percentual pura entre o preço de compra e venda.<br>
              <strong>Spread Líquido:</strong> É o spread bruto menos as taxas de transação (trading fees e network fees), 
              representando o lucro real esperado.
            </p>
          </div>
          <div class="faq-item">
            <h3>O que são os status das oportunidades?</h3>
            <p>
              <strong>Accepted:</strong> Oportunidade aceite e executada na simulação<br>
              <strong>Discarded:</strong> Oportunidade descartada por não ser lucrativa<br>
              <strong>No Funds:</strong> Fundos insuficientes para executar<br>
              <strong>Low Liquidity:</strong> Liquidez insuficiente no mercado
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>💰 Carteiras e Saldos</h2>
          <div class="faq-item">
            <h3>Como funciona o Rebalance?</h3>
            <p>
              O Rebalance redistribui os fundos entre as exchanges para otimizar as oportunidades de arbitragem. 
              Ele equilibra as carteiras para que haja capital disponível em ambas as exchanges necessárias para cada operação.
            </p>
          </div>
          <div class="faq-item">
            <h3>Os valores são reais?</h3>
            <p>
              Sim, os dados de mercado e cotações são atualizados em tempo real. No entanto, o capital e as operações são simulados. Nenhuma transação financeira real é executada, permitindo que você estude e valide estratégias em um ambiente seguro e sem risco financeiro.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>📈 Gráficos e Métricas</h2>
          <div class="faq-item">
            <h3>O que é o P&L Acumulado?</h3>
            <p>
              P&L (Profit and Loss) Acumulado mostra o lucro ou prejuízo total desde o início da simulação. 
              O gráfico exibe a evolução desse valor ao longo do tempo.
            </p>
          </div>
          <div class="faq-item">
            <h3>Como interpretar a latência?</h3>
            <p>
              <strong>Baixa (verde):</strong> &lt; 450ms - Excelente para arbitragem<br>
              <strong>Média (amarela):</strong> 450-900ms - Aceitável, mas pode perder oportunidades<br>
              <strong>Alta (vermelha):</strong> &gt; 900ms - Pode ser tarde demais para capturar o spread
            </p>
          </div>
          <div class="faq-item">
            <h3>O que é a "Série de Spread"?</h3>
            <p>
              Mostra o histórico dos últimos spreads detectados em tempo real, 
              incluindo o par de moedas, spread líquido e latência da detecção.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>🔧 Filtros e Configurações</h2>
          <div class="faq-item">
            <h3>Como filtrar por moeda específica?</h3>
            <p>
              Use os dropdowns "Moeda base" e "Moeda cotada" na barra de filtros. 
              Por exemplo, selecione "BTC" como base para ver apenas oportunidades com Bitcoin.
            </p>
          </div>
          <div class="faq-item">
            <h3>Posso combinar filtros?</h3>
            <p>
              Sim! Você pode selecionar tanto a moeda base quanto a moeda cotada para filtrar resultados específicos, 
              como apenas pares BTC/USDT.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>⚡ WebSocket e Atualizações</h2>
          <div class="faq-item">
            <h3>O que significa "WS: connected/disconnected"?</h3>
            <p>
              Indica o status da conexão WebSocket em tempo real com o backend:<br>
              <strong style="color: #66ef8b;">connected:</strong> Recebendo atualizações em tempo real<br>
              <strong style="color: #ff9d9d;">disconnected:</strong> Sem conexão ao vivo (requer refresh manual)
            </p>
          </div>
          <div class="faq-item">
            <h3>Com que frequência os dados são atualizados?</h3>
            <p>
              O WebSocket fornece atualizações em tempo real instantâneas. 
              Além disso, há um refresh automático a cada 3 segundos para garantir que os dados estejam sempre atualizados.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>🚨 Solução de Problemas</h2>
          <div class="faq-item">
            <h3>Vejo a mensagem "Não foi possível carregar dados do backend"</h3>
            <p>
              Certifique-se de que o servidor FastAPI está em execução. 
              Execute no terminal: <code>uvicorn app.main:app --reload --port 8000</code>
            </p>
          </div>
          <div class="faq-item">
            <h3>As oportunidades não aparecem</h3>
            <p>
              Verifique se você selecionou filtros muito restritivos. 
              Tente limpar os filtros selecionando "Todas" nas opções de moeda.
            </p>
          </div>
          <div class="faq-item">
            <h3>O gráfico não carrega</h3>
            <p>
              Aguarde algumas operações serem executadas. O gráfico mostra o histórico de P&L, 
              que só aparecerá após haver trades aceitos na simulação.
            </p>
          </div>
        </article>

        <article class="help-section">
          <h2>💡 Dicas de Uso</h2>
          <div class="faq-item">
            <h3>Como encontrar as melhores oportunidades?</h3>
            <p>
              Procure por oportunidades com:<br>
              • Spread líquido positivo e significativo (&gt; 0.5%)<br>
              • Latência baixa (verde)<br>
              • Status "Accepted"<br>
              • Atualização recente (há poucos segundos)
            </p>
          </div>
          <div class="faq-item">
            <h3>Qual o melhor volume de simulação?</h3>
            <p>
              Depende do seu objetivo de estudo. Volumes maiores amplificam os resultados, 
              mas também exigem mais capital. Comece com $1,000 para entender o funcionamento, 
              e experimente valores maiores ($10,000 - $50,000) para cenários mais realistas.
            </p>
          </div>
        </article>
      </div>

      
    </div>
  </section>
</template>

<style scoped>
.help-page {
  min-height: calc(100vh - 190px);
  padding: 24px;
}

.help-container {
  max-width: 900px;
  margin: 0 auto;
}

.help-header {
  text-align: center;
  margin-bottom: 40px;
  padding: 30px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(14, 28, 45, 0.92) 0%, rgba(9, 20, 34, 0.92) 100%);
  border: 1px solid rgba(95, 126, 166, 0.2);
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.35);
}

.help-header h1 {
  margin: 0 0 12px;
  font-size: 32px;
  color: #ecf3ff;
}

.help-header p {
  margin: 0;
  font-size: 16px;
  color: rgba(232, 240, 252, 0.85);
}

.help-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.help-section {
  padding: 24px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(14, 28, 45, 0.92) 0%, rgba(9, 20, 34, 0.92) 100%);
  border: 1px solid rgba(95, 126, 166, 0.2);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
}

.help-section h2 {
  margin: 0 0 20px;
  font-size: 22px;
  color: #66ef8b;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(102, 239, 139, 0.2);
}

.faq-item {
  margin-bottom: 20px;
}

.faq-item:last-child {
  margin-bottom: 0;
}

.faq-item h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #dbe9ff;
  font-weight: 600;
}

.faq-item p {
  margin: 0;
  color: rgba(232, 240, 252, 0.85);
  line-height: 1.6;
  font-size: 14px;
}

.faq-item strong {
  color: #66ef8b;
  font-weight: 600;
}

.faq-item code {
  background: rgba(102, 239, 139, 0.1);
  color: #66ef8b;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.help-footer {
  margin-top: 40px;
  padding: 24px;
  text-align: center;
  border-radius: 16px;
  background: rgba(102, 239, 139, 0.08);
  border: 1px solid rgba(102, 239, 139, 0.25);
}

.help-footer p {
  margin: 0;
  color: #dbe9ff;
  line-height: 1.6;
  font-size: 15px;
}

@media (max-width: 768px) {
  .help-header h1 {
    font-size: 26px;
  }

  .help-section {
    padding: 18px;
  }

  .help-section h2 {
    font-size: 20px;
  }
}
</style>
