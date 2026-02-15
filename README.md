BUGSBYTE 2026

Sistema de Simulação e Monitoramento de Arbitragem de Criptomoedas em Tempo Real

Equipa de Trabalho:

Guilherme Gomes - a110449

João Cerqueira - a111753

Nuno Pereira - a110067

Rafael Esteves - a112032

## Arquitetura do Projeto

O projeto está dividido em duas partes principais:

### Backend (Python + FastAPI)
- API REST para dados de arbitragem
- WebSocket para atualizações em tempo real
- Motor de cálculo de spread e oportunidades
- Persistência em SQLite/PostgreSQL

### Frontend (Vue 3 + TypeScript + Vite)
- Interface interativa para monitoramento
- Dashboard em tempo real via WebSocket
- Sistema de autenticação
- Múltiplas páginas (Home, Login, Simulador, Mercado, Ajuda)

## 📸 Interface do Simulador

![Simulador de Arbitragem](docs/simulator-screenshot.png)

O painel principal mostra em tempo real:
- **Navbar Superior**: Estado da conexão WebSocket (verde=conectado), utilizador autenticado e logout
- **Filtros**: Seleção de moeda base/cotada, volume de simulação e controlo do bot automático
- **Métricas**: Total de trades, P&L acumulado, portfólio total, latência e exchanges ativas
- **Carteiras**: Saldos USDT e criptomoedas distribuídos pelas 4 exchanges (Binance, Bybit, Kraken, Uphold)
- **Tabela de Oportunidades**: Lista paginada com spreads, custos de gas, P&L esperado e status (Discarded/Accepted)

## Frontend (Vue 3)

### Requisitos

```bash
sudo apt install nodejs npm
```

### Instalação e Execução

Para correr o frontend (a partir da raiz do repo):

```bash
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:5173`

### Estrutura do Frontend

```
src/
├── components/
│   └── ArbitrageSimulationPanel.vue  # Painel principal de simulação
├── pages/
│   ├── Home.vue                      # Página inicial
│   ├── Login.vue                     # Página de autenticação
│   ├── Main.vue                      # Dashboard principal
│   ├── Market.vue                    # Página de mercado
│   └── Help.vue                      # Página de ajuda
├── router/
│   └── index.ts                      # Configuração de rotas
├── services/
│   └── arbitrage.ts                  # Serviço de API
├── stores/
│   ├── counter.ts                    # Store exemplo
│   └── websocket.ts                  # Store global do WebSocket
├── App.vue                           # Componente raiz
└── main.ts                           # Entry point
```

### Funcionalidades do Frontend

#### Sistema de Autenticação
- Login com email/senha
- Sessão persistente no localStorage
- Proteção de rotas
- Display do utilizador na navbar

#### Painel de Simulação (Simulador)
- **Conexão WebSocket em Tempo Real**: Estado de conexão (connected/disconnected) visível na navbar
- **Filtros Dinâmicos**: Filtrar por moeda base, moeda cotada e volume de simulação
- **Métricas em Tempo Real**:
  - Total de trades aceites
  - P&L acumulado
  - Portfólio total
  - Latência da última oportunidade
  - Exchanges ativas
- **Carteiras por Exchange**: Visualização de saldos USDT e criptomoedas por exchange
- **Tabela de Oportunidades**: Paginação, status (accepted/discarded/no_funds/low_liquidity)
- **Gráfico de Performance**: Chart.js mostrando P&L acumulado ao longo do tempo
- **Histórico de Trades**: Lista de todas as trades executadas com detalhes

#### Gestão de Estado Global
- **Pinia Store**: Store WebSocket global que mantém a conexão entre páginas
- **Reatividade**: Atualizações automáticas via WebSocket
- **Persistência**: Conexão mantida ao navegar entre páginas

#### Páginas Adicionais
- **Mercado**: Visualização de dados de mercado
- **Ajuda**: Documentação e FAQs sobre o sistema

## Backend em Python (FastAPI)

Requisitos no Linux Mint/Ubuntu:

```bash
sudo apt update
sudo apt install python3-venv
```

Para correr o backend (a partir da raiz do repo):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Endpoints disponíveis:

- http://localhost:8000/ (root, status)
- http://localhost:8000/health
- http://localhost:8000/api/echo?message=ola

## MVP de Arbitragem (tempo real)

O backend agora inclui um MVP com 3 camadas:

1. Data Layer (`WebSocket push`)
   - `binance` via WebSocket de profundidade (`depth20@100ms`)

- `uphold` via API pública de ticker (bid/ask)
- `sim_exchange` para simulação controlada e testes de estratégia (opcional)
- Normalização para formato único de order book

2. Motor de Cálculo
   - Spread bruto e spread líquido
   - Taxas por exchange
   - Custo fixo de transferência
   - Slippage com VWAP usando profundidade do livro (não só topo)

3. Execução Simultânea (simulada)
   - Simulação automática de execução quando há oportunidade líquida
   - Reserva de volume no order book para evitar reutilização imediata do mesmo volume

### Configuração das taxas e parâmetros

Edita `backend/config.json` para:

- definir símbolo e tamanho de trade
- alterar taxas por exchange
- ajustar custo de transferência
- ativar/desativar feeds

### Endpoints de arbitragem

- `GET /api/arbitrage/status`
  - estado geral, saldo e P&L acumulado
- `GET /api/arbitrage/opportunities?limit=100`
  - oportunidades aceites e descartadas
- `GET /api/arbitrage/trades?limit=100`
  - execuções simuladas
- Ambos aceitam filtro opcional por símbolo: `?symbols=BTCUSDT&symbols=ETHUSDT`
- Cada item devolve também `symbol_name` (ex.: "Bitcoin / Tether")
- `GET /api/arbitrage/spread-series?limit=200`
  - série temporal de spread bruto/líquido e latência
- `WS /ws/arbitrage`
  - stream de snapshot em tempo real para dashboard

### Persistência de dados (trades/oportunidades)

O motor guarda oportunidades e trades em memória para o dashboard em tempo real, mas agora também persiste em BD.

- Por defeito usa **SQLite** em `backend/data/bugsbyte.db`
- Para usar **PostgreSQL**, define `DATABASE_URL`

Exemplos:

- SQLite (default, não precisas definir nada)
- PostgreSQL:

```bash
export DATABASE_URL='postgresql+asyncpg://user:pass@localhost:5432/bugsbyte'
```

### Como testar o sistema completo

#### 1. Arranca o Backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verifica que o backend está a funcionar:
- `http://localhost:8000/api/arbitrage/status`
- `http://localhost:8000/api/arbitrage/opportunities`

#### 2. Arranca o Frontend

Em outro terminal, a partir da raiz do projeto:

```bash
npm install
npm run dev
```

Acede ao frontend em: `http://localhost:5173`

#### 3. Utilização

1. **Login**: Faz login na página inicial (email/senha)
2. **Simulador**: Acede ao painel de simulação para visualizar oportunidades em tempo real
3. **Filtros**: Usa os filtros de moeda base, moeda cotada e volume para ajustar a simulação
4. **Monitoramento**: Observa o estado da conexão WebSocket na navbar (connected/disconnected)
5. **Navegação**: Navega entre as páginas sem perder a conexão WebSocket

### Configuração de CORS

Se precisares ajustar CORS para o frontend, define `CORS_ORIGINS` em `.env` (ver `backend/.env.example`).

### Tecnologias Utilizadas

#### Backend
- Python 3.x
- FastAPI
- WebSockets
- SQLAlchemy (async)
- SQLite/PostgreSQL
- CCXT (para integração com exchanges)

#### Frontend
- Vue 3 (Composition API)
- TypeScript
- Vite
- Vue Router
- Pinia (State Management)
- Chart.js (Gráficos)
- CSS Scoped (Estilização)
