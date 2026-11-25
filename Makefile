.PHONY: setup test validate film clean kaggle-bundle

kaggle-bundle: validate
	uv run python -m pipeline.shots
	rm -rf outputs/kaggle outputs/kaggle_bundle.zip
	mkdir -p outputs/kaggle
	cp storyboard.json outputs/kaggle/
	cp -r outputs/jobs/wan_jobs.json outputs/jobs/keyframes outputs/kaggle/
	cd outputs/kaggle && zip -qr ../kaggle_bundle.zip .
	@echo "outputs/kaggle_bundle.zip ready"

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
