test:
	.venv/bin/pytest -v

live:
	.venv/bin/python3 tests/test_live.py

.PHONY: test live

