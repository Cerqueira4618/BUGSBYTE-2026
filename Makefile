SHELL := /bin/bash
.ONESHELL:

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PARENT_DIR := $(abspath $(ROOT_DIR)/..)
BACKEND_DIR := $(ROOT_DIR)/backend
BACKEND_PID_FILE := $(BACKEND_DIR)/.uvicorn.pid
BACKEND_LOG_FILE := $(BACKEND_DIR)/.uvicorn.log
BACKEND_DB_FILE := $(BACKEND_DIR)/data/bugsbyte.db
BACKEND_DB_WAL := $(BACKEND_DIR)/data/bugsbyte.db-wal
BACKEND_DB_SHM := $(BACKEND_DIR)/data/bugsbyte.db-shm

ifneq (,$(wildcard $(ROOT_DIR)/.venv/bin/python))
PYTHON := $(ROOT_DIR)/.venv/bin/python
else ifneq (,$(wildcard $(PARENT_DIR)/.venv/bin/python))
PYTHON := $(PARENT_DIR)/.venv/bin/python
else ifneq (,$(wildcard $(BACKEND_DIR)/.venv/bin/python))
PYTHON := $(BACKEND_DIR)/.venv/bin/python
else
PYTHON := python3
endif

.PHONY: help site backend-on backend-off backend-status

help:
	@echo "Targets disponíveis:"
	@echo "  make site           # sobe o frontend (vite)"
	@echo "  make backend-on     # liga o backend em background"
	@echo "  make backend-off    # desliga o backend e limpa a BD SQLite"
	@echo "  make backend-status # mostra status do backend"

site:
	cd "$(ROOT_DIR)"
	npm run dev

backend-on:
	cd "$(BACKEND_DIR)"
	if [[ -f "$(BACKEND_PID_FILE)" ]] && kill -0 "$$(cat "$(BACKEND_PID_FILE)")" 2>/dev/null; then
		echo "Backend já está ligado (PID $$(cat "$(BACKEND_PID_FILE)"))."
		exit 0
	fi
	if [[ "$(PYTHON)" == "python3" ]] && [[ ! -d ".venv" ]]; then
		python3 -m venv .venv
		PYTHON="$(BACKEND_DIR)/.venv/bin/python"
	else
		PYTHON="$(PYTHON)"
	fi
	if ! "$$PYTHON" -m pip --version >/dev/null 2>&1; then
		"$$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
	fi
	"$$PYTHON" -m pip install -r requirements.txt >/dev/null
	nohup "$$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$(BACKEND_LOG_FILE)" 2>&1 &
	echo $$! > "$(BACKEND_PID_FILE)"
	sleep 1
	if kill -0 "$$(cat "$(BACKEND_PID_FILE)")" 2>/dev/null; then
		echo "Backend ligado em http://127.0.0.1:8000 (PID $$(cat "$(BACKEND_PID_FILE)"))."
		echo "Log: $(BACKEND_LOG_FILE)"
	else
		echo "Falha ao ligar backend. Verifique $(BACKEND_LOG_FILE)."
		rm -f "$(BACKEND_PID_FILE)"
		exit 1
	fi

backend-off:
	cd "$(BACKEND_DIR)"
	if [[ ! -f "$(BACKEND_PID_FILE)" ]]; then
		echo "Backend não está ligado (sem arquivo PID)."
	else
		PID="$$(cat "$(BACKEND_PID_FILE)")"
		if kill -0 "$$PID" 2>/dev/null; then
			kill "$$PID"
			sleep 1
			if kill -0 "$$PID" 2>/dev/null; then
				kill -9 "$$PID" 2>/dev/null || true
			fi
			echo "Backend desligado (PID $$PID)."
		else
			echo "Processo $$PID não estava em execução."
		fi
	fi
	if fuser 8000/tcp >/dev/null 2>&1; then
		fuser -k 8000/tcp >/dev/null 2>&1 || true
		echo "Processos na porta 8000 terminados."
	fi
	rm -f "$(BACKEND_PID_FILE)"
	rm -f "$(BACKEND_DB_FILE)"
	rm -f "$(BACKEND_DB_WAL)" "$(BACKEND_DB_SHM)"
	echo "Base de dados resetada: $(BACKEND_DB_FILE)"

backend-status:
	cd "$(BACKEND_DIR)"
	if [[ -f "$(BACKEND_PID_FILE)" ]] && kill -0 "$$(cat "$(BACKEND_PID_FILE)")" 2>/dev/null; then
		echo "Backend ligado (PID $$(cat "$(BACKEND_PID_FILE)"))."
		exit 0
	fi
	echo "Backend desligado."
	exit 1
