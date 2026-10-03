PY ?= python3

.PHONY: setup data data2 run demo test verify api frontend reset

setup:            ## create venv and install deps
	$(PY) -m venv .venv && .venv/bin/pip install -r requirements.txt

data:             ## generate batch 1 (full history, dirty on purpose)
	$(PY) -m src.generate_sample_data --batch 1

data2:            ## generate batch 2 (new listings + price changes + duplicates)
	$(PY) -m src.generate_sample_data --batch 2

run:              ## ingest -> clean -> load -> quality checks
	$(PY) -m src.pipeline

demo:             ## full incremental demo: full load, then a delta load
	$(MAKE) reset data run
	$(MAKE) data2 run

test:
	$(PY) -m pytest -q

verify:          ## cross-check warehouse (and API if running) against the source CSV
	$(PY) scripts/verify.py

api:             ## FastAPI backend on http://localhost:8000
	$(PY) -m uvicorn api.server:app --port 8000 --reload

frontend:        ## React dashboard on http://localhost:5173 (needs `make api` running)
	cd frontend && npm install && npm run dev

reset:
	rm -f data/warehouse.duckdb* data/inbox/*.csv
