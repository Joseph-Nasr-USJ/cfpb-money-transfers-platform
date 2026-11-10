# Banking Complaints Data Platform - common commands.
# Run every target from the repository root, e.g. "make up". Settings and secrets come from .env.
# Install make once:  Windows: winget install ezwinports.make    macOS: xcode-select --install

COMPOSE = docker compose
RUN     = $(COMPOSE) run --rm pipeline

# Arguments for "make process" and "make load"
SOURCE ?= full_load
RUN_ID ?=

.PHONY: help up down reset test ingest-full ingest-incremental process load \
        pipeline-full pipeline-incremental sample benchmark analytics logs

help:
	@echo Stack:     make up / make down / make reset - deletes all data / make logs
	@echo Pipeline:  make pipeline-full / make pipeline-incremental
	@echo Steps:     make ingest-full / make ingest-incremental / make sample
	@echo            make process SOURCE=full_load RUN_ID=id   or   SOURCE=api RUN_ID=id
	@echo            make load RUN_ID=id
	@echo Serving:   make benchmark / make analytics
	@echo Tests:     make test

# ---------- Stack ----------
up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail 100

# ---------- Tests ----------
test:
	$(RUN) python -m pytest -q

# ---------- Individual pipeline steps ----------
ingest-full:
	$(RUN) python -m ingestion.historical

ingest-incremental:
	$(RUN) python -m ingestion.incremental

process:
	$(if $(RUN_ID),,$(error RUN_ID is required, e.g. make process SOURCE=api RUN_ID=20261110T020000Z_api))
	$(RUN) spark-submit processing/spark_job.py --source $(SOURCE) --run-id $(RUN_ID)

load:
	$(if $(RUN_ID),,$(error RUN_ID is required, e.g. make load RUN_ID=20261110T020000Z_api))
	$(RUN) python -m database.load --run-id $(RUN_ID)

sample:
	$(RUN) python -m ingestion.sample

# ---------- Full chains (same code as the 24-hour scheduler) ----------
pipeline-full:
	$(RUN) python -m ingestion.pipeline --mode full

pipeline-incremental:
	$(RUN) python -m ingestion.pipeline --mode incremental

# ---------- Serving layer and analysis ----------
benchmark:
	$(RUN) python -m database.benchmark

analytics:
	$(RUN) python -m analytics.run_all
