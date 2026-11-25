SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
LOAD_ENV := set -a; [ -f team.env ] && . ./team.env; set +a

.PHONY: dev wait

$(PY): platform/requirements.txt platform/requirements-dev.txt
	python3.12 -m venv $(VENV)
	$(PY) -m pip install -q -r platform/requirements-dev.txt
	touch $(PY)

## Run the app on this machine with live reload against the model endpoints in team.env
dev: $(PY)
	@$(LOAD_ENV); PYTHONPATH=platform APP_DIR=app $(PY) -m uvicorn baseapp.main:app \
		--port $${APP_PORT:-8742} --reload --reload-dir app --reload-include '*.yaml' --reload-include '*.md'

## Wait until the team's Route serves the commit you just pushed
wait: $(PY)
	@$(LOAD_ENV); PYTHONPATH=platform $(PY) -m baseapp.wait
