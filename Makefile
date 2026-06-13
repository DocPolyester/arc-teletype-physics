#!/bin/bash
# Makefile für schnelle Befehle
.PHONY: help deploy install start stop status logs clean test

help:
	@echo "Arc Middleware - Makefile Commands"
	@echo ""
	@echo "  make deploy   - Deploy code to Pi (rsync)"
	@echo "  make install  - Install dependencies"
	@echo "  make start    - Start service"
	@echo "  make stop     - Stop service"
	@echo "  make status   - Show service status"
	@echo "  make logs     - View live logs"
	@echo "  make clean    - Remove local cache files"
	@echo ""

deploy:
	bash scripts/deploy.sh deploy

install:
	bash scripts/deploy.sh install

start:
	bash scripts/deploy.sh start

stop:
	bash scripts/deploy.sh stop

status:
	bash scripts/deploy.sh status

logs:
	bash scripts/deploy.sh logs

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v

.DEFAULT_GOAL := help
