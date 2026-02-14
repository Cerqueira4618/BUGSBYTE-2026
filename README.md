BUGSBYTE 2026

Equipa de Trabalho:

Guilherme Gomes - a110449

João Cerqueira - a111753

Nuno Pereira - a110067

Rafael Esteves - a112032

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

### Como testar rápido

1. Arranca o backend:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

2. Verifica:
   - `http://localhost:8000/api/arbitrage/status`
   - `http://localhost:8000/api/arbitrage/opportunities`

Se precisares ajustar CORS para o frontend, define `CORS_ORIGINS` em `.env` (ver `backend/.env.example`).
