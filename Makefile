test:
	pytest -v

live:
	python3 tests/test_live.py

.PHONY: test live

