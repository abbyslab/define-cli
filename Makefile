setup:
	python3 -m venv .venv
	.venv/bin/pip install -e .
	.venv/bin/pip install pytest
	chmod +x define

test:
	.venv/bin/pytest -v --ignore=tests/test_live.py

live:
	.venv/bin/python3 tests/test_live.py

.PHONY: setup test live
