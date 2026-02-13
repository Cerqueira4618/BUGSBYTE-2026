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

Se precisares ajustar CORS para o frontend, define `CORS_ORIGINS` em `.env` (ver `backend/.env.example`).
