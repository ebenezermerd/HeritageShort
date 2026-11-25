.PHONY: setup test validate film clean

setup:
	uv sync

test:
	uv run pytest -q

validate:
	uv run python -m pipeline.validate

film: validate
	uv run python -m pipeline.run_all

clean:
	rm -rf outputs/*
