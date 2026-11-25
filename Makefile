.PHONY: candidates setup test validate film clean kaggle-bundle choose-music save-assets

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

VOICE ?= gemini

candidates: validate
	uv run python -m pipeline.candidates -n 3

film: validate
	uv run python -m pipeline.run_all --voice $(VOICE)

# Removes what the pipeline generates. Keeps outputs/shots/raw and outputs/music/raw (hand-downloaded
# from Kaggle) and outputs/music/score.wav, which cost GPU time to make.
clean:
	rm -rf outputs/keyframes outputs/narration outputs/assemble outputs/jobs outputs/kaggle outputs/experiments
	rm -rf outputs/shots/9x16 outputs/shots/16x9 outputs/shots/manifest.json
	rm -f outputs/final_* outputs/radio_cut.mp4 outputs/kaggle_bundle.zip

# make choose-music N=2 WHY="softest texture under the voice"
choose-music:
	uv run python -m pipeline.music $(N) "$(WHY)"

# Copy the chosen Wan clips (and their job-hash files) and the chosen score into assets/, which is
# committed, so a clean clone can rebuild the finished film.
save-assets:
	mkdir -p assets/shots assets/music
	if ls outputs/shots/raw/*.mp4 >/dev/null 2>&1; then cp outputs/shots/raw/*.mp4 outputs/shots/raw/*.json assets/shots/; else echo "no Wan clips yet, saving the score only"; fi
	cp outputs/music/score.wav assets/music/score.wav
