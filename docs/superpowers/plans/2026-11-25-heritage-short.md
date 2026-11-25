# Heritage Short Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command pipeline that turns `storyboard.json` into the "Forty Springs" film in 9:16 and 16:9, plus the evidence files the 10 Academy grader reads.

**Architecture:** One validated `storyboard.json` feeds six stage scripts. Each stage caches per shot by an input hash, retries three times, logs every attempt to `runs.jsonl`, and falls back (Ken Burns for motion). Wan 2.2, ACE-Step and the likeness test run in hand-run Kaggle notebooks with a file handoff. Assembly is deterministic FFmpeg plus Pillow-rendered captions.

**Tech Stack:** Python 3.12 via `uv`, `jsonschema`, `pytest`, `requests`, `Pillow`, FFmpeg 8.1 (has `zoompan`, `sidechaincompress`, `loudnorm`, `overlay`; has no `libass` or `drawtext`), Gemini API (text + TTS), Cloudflare Workers AI (FLUX), Kaggle notebooks (Wan 2.2 TI2V-5B, ACE-Step 1.5, FLUX.2 klein 4B for likeness).

**Spec:** `docs/superpowers/specs/2026-11-25-heritage-short-design.md`

## Global Constraints

- Deadline: Thu 26 Nov 2026, 23:59 EAT. Abeni wants everything finished today.
- Free tiers only, no card. Wan runs 9:16 only, 480p draft, on shots 1, 3, 6, 8.
- Keyframes generated per ratio (9:16 primary, 16:9 second). Wan never runs in 16:9.
- Three attempts per shot per stage, then fallback; every attempt logged.
- `runs.jsonl` line fields: `ts, stage, shot_id, provider, model, params, seed, input_hash, latency_s, status, cost_usd, error`.
- English narration, stock TTS voice, no voice cloning, calm unhurried style instruction.
- Subtitles: max two lines, about 40 characters a line, inside the vertical safe area; drawn with Pillow and overlaid (no libass).
- Audio: `sidechaincompress` threshold 0.02, ratio 6, attack 300, release 1500; two-pass `loudnorm` to -14 LUFS, true peak -1 dB; H.264 + AAC, constant frame rate.
- End card text: "Made with AI. Painted from memory." for 3 s.
- Secrets only in git-ignored `.env`; `.env.example` has names only. `refs/` (photos) is git-ignored and never uploaded without both brothers' yes.
- No living artist's name in prompts. Narration lines marked (added) in the spec need Abeni's confirm before the radio cut.
- Docs are written from real events: each entry cites a log line, a listener's words, or a real error. No filler.

## Review Focus

- Empty or whitespace narration line: schema rejects it, no TTS call is made.
- Storyboard edited to change one shot: only that shot's hash changes, so only that shot regenerates (the walkthrough demo depends on it).
- Missing API key or token: stage stops with a message naming the env var, writes no partial output, and logs nothing misleading.
- Provider rate limit or timeout: retries back off, third failure is logged `status="failed"` and the fallback runs.
- Narration longer than the shot: assembly extends the shot to the narration duration, never cuts the voice.
- Wan clip missing for a `wan` shot: assembly uses Ken Burns on the keyframe and says so in the log.
- Partial Kaggle download (zero-byte or truncated clip): manifest import rejects it via `ffprobe`, shot stays on fallback.

---

### Task 1: Foundation (repo, helpers, logging)

**Files:**
- Create: `pyproject.toml`, `Makefile`, `.env.example`, `pipeline/__init__.py`, `pipeline/common.py`, `tests/test_common.py`

**Interfaces:**
- Produces in `pipeline/common.py`:
  - `ROOT: Path`
  - `log_run(stage: str, shot_id: str | None, provider: str, model: str, params: dict, seed: int | None, input_hash: str, latency_s: float, status: str, cost_usd: float = 0.0, error: str | None = None) -> None` appends one JSON line to `ROOT/runs.jsonl`
  - `input_hash(*parts: Any) -> str` SHA-256 of canonical JSON; a `Path` part contributes its file bytes
  - `class Manifest(stage: str)` with `is_fresh(shot_id: str, h: str) -> bool`, `put(shot_id: str, h: str, path: str) -> None`, `get(shot_id: str) -> dict | None`, persisted at `outputs/<stage>/manifest.json`
  - `with_retries(fn: Callable[[], T], attempts: int = 3, base_delay: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> T` re-raises the last error
  - `require_env(name: str) -> str` raises `SystemExit` naming the variable

- [ ] **Step 1: Write failing tests** `test_log_run_appends_valid_json_line`, `test_input_hash_changes_when_any_part_changes`, `test_input_hash_uses_file_bytes`, `test_manifest_is_fresh_only_for_same_hash_and_existing_file`, `test_with_retries_succeeds_on_third_try` (assert two sleeps, delays 2 then 4), `test_with_retries_raises_after_three` , `test_require_env_exits_with_name`.
- [ ] **Step 2: Run** `uv run pytest tests/test_common.py -q`. Expected: FAIL, module missing.
- [ ] **Step 3: Implement** the signatures above. Makefile targets: `setup` (uv sync), `test`, `validate`, `film` (later tasks add stages), `clean`.
- [ ] **Step 4: Run** the same command. Expected: 7 passed.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Add pipeline helpers: logging, hashing, manifest, retries"`

### Task 2: Storyboard schema, validation, first storyboard

**Files:**
- Create: `schema/storyboard.schema.json`, `pipeline/validate.py`, `storyboard.json`, `tests/test_schema.py`

**Interfaces:**
- Consumes: `ROOT`.
- Produces: `load_storyboard(path: Path = ROOT/"storyboard.json") -> dict` (validates, raises `SystemExit` with the failing JSON path); `shot_ids(sb: dict) -> list[str]`.
- Schema fields: `title`, `ratios` (enum `"9:16"`,`"16:9"`), `style_block`, `characters[{id,name,age,look}]`, `shots[{id, reason, narration, image_prompt, seed, motion:{mode: "kenburns"|"wan", camera: "push_in"|"pull_out"|"pan_left"|"pan_right", prompt}}]`, `music{caption, bpm, key, duration_s}`, `end_card{text, duration_s}`. `reason` and `narration` are non-empty after trim.

- [ ] **Step 1: Write failing tests** `test_example_storyboard_is_valid`, `test_shot_without_reason_is_rejected`, `test_unknown_motion_mode_is_rejected`, `test_blank_narration_is_rejected`, `test_ten_shots_with_unique_ids`.
- [ ] **Step 2: Run** `uv run pytest tests/test_schema.py -q`. Expected: FAIL.
- [ ] **Step 3: Write** the schema and `load_storyboard`. Fill `storyboard.json` from the spec's shot table: 10 shots, each with its stated reason, narration lines 1-9 as drafted (shots 1-9 get lines 1-9 in order; shot 10 is silent with `narration: null`, which the schema allows, while any non-null narration must be non-blank), style block "warm hand-painted look, soft grain, dappled green and turquoise light, clear spring water, tall trees, red-brown earth bank", character looks from the spec's draft notes, motion modes exactly as in the spec table.
- [ ] **Step 4: Run** tests. Expected: 5 passed. Also `make validate` prints `storyboard ok`.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Add storyboard schema and first storyboard"`

### Task 3: Smoke test of every provider

**Files:**
- Create: `pipeline/smoke.py`, `.env` (git-ignored, written locally from keys Abeni provided)

**Interfaces:**
- Consumes: `require_env`, `log_run`, `with_retries`.
- Produces: `python -m pipeline.smoke` prints one line per provider (`ok`/`FAIL`, latency) and logs each to `runs.jsonl`. It also writes `outputs/smoke/models.json` with the confirmed Gemini TTS model id, the Gemini text model id, and the Cloudflare FLUX model id that returned an image.

- [ ] **Step 1: Write** `.env` with `GEMINI_API_KEY` from Abeni's message and empty `CF_ACCOUNT_ID`, `CF_API_TOKEN`. Never echo the key.
- [ ] **Step 2: Implement** `smoke()`: one tiny Gemini text call, one Gemini TTS call ("Arba Minch means forty springs." as WAV), and, if Cloudflare vars are set, one FLUX.1 schnell image and one FLUX.2 klein try. Missing Cloudflare vars print `SKIP (set CF_ACCOUNT_ID and CF_API_TOKEN)`.
- [ ] **Step 3: Run** `uv run python -m pipeline.smoke`. Expected: Gemini text and TTS `ok`; Cloudflare `ok` once Abeni supplies the token and account id. Any `FAIL` goes into `FAILURES.md` immediately with the real error.
- [ ] **Step 4: Commit** `git add pipeline/smoke.py && git commit -m "Add provider smoke test"` (not `.env`).

### Task 4: Narration stage

**Files:**
- Create: `pipeline/narrate.py`, `tests/test_narrate.py`

**Interfaces:**
- Consumes: `load_storyboard`, `Manifest`, `input_hash`, `with_retries`, `log_run`, TTS model id from `outputs/smoke/models.json`.
- Produces: `run(storyboard: dict, tts: Callable[[str, str], bytes] = gemini_tts) -> dict[str, float]` writes `outputs/narration/<shot_id>.wav`, returns `{shot_id: duration_seconds}` (via `ffprobe`); skips shots whose hash is fresh; skips `null` narration.

- [ ] **Step 1: Write failing tests** with a fake `tts`: `test_one_file_per_narrated_shot`, `test_second_run_makes_zero_tts_calls`, `test_changing_one_line_regenerates_only_that_shot` (assert exactly one call and one new `runs.jsonl` line), `test_silent_shot_gets_no_file`.
- [ ] **Step 2: Run** `uv run pytest tests/test_narrate.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `run` and `gemini_tts(text: str, style: str) -> bytes` (style "calm, warm, unhurried"; hash includes text, style, voice, model).
- [ ] **Step 4: Run** tests. Expected: 4 passed. Then `uv run python -m pipeline.narrate` with the real key; log shows 9 calls; listen to two files.
- [ ] **Step 5: Commit** `git commit -am "Add narration stage with per-shot caching"`

### Task 5: Radio cut (first user test)

**Files:**
- Create: `pipeline/radio_cut.py`, `tests/test_radio_cut.py`

**Interfaces:**
- Consumes: `run` from narrate, `load_storyboard`.
- Produces: `build(durations: dict[str, float], out: Path = ROOT/"outputs/radio_cut.mp4") -> Path`: narration lines in order, 0.8 s between lines, over a quiet synthesised pad (FFmpeg `sine` mix, ducked), black 1280x720 video; total duration returned by `ffprobe` equals sum of lines plus gaps within 0.3 s.

- [ ] **Step 1: Write failing test** `test_radio_cut_duration_matches_lines_plus_gaps` using generated sine WAVs as fake narration.
- [ ] **Step 2: Run** and see FAIL. **Step 3: Implement** `build`. **Step 4: Run** test, expect pass.
- [ ] **Step 5: Run for real**, send `outputs/radio_cut.mp4` to Tesfa, Beki and Amani. Abeni records what each said in `DESIGN.md` (test 1). The agent then changes the storyboard from what they said, and the diff goes in the commit message.
- [ ] **Step 6: Commit** `git commit -am "Add radio cut and first user test notes"`

### Task 6: Keyframe stage

**Files:**
- Create: `pipeline/keyframes.py`, `tests/test_keyframes.py`

**Interfaces:**
- Consumes: common helpers, Cloudflare FLUX id from `outputs/smoke/models.json`.
- Produces: `run(storyboard: dict, gen: Callable[[str, int, tuple[int,int]], bytes] = cloudflare_flux) -> dict[str, dict[str, Path]]` writes `outputs/keyframes/<ratio>/<shot_id>.png` for each ratio, sizes 768x1344 and 1344x768; prompt is `style_block + character looks present + image_prompt`; hash includes prompt, seed, ratio, model.

- [ ] **Step 1: Write failing tests** with fake `gen`: `test_two_ratios_per_shot`, `test_prompt_contains_style_block_and_character_look`, `test_cache_hit_makes_no_calls`, `test_third_failure_is_logged_failed_and_other_shots_continue`.
- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement.** **Step 4: Run**, expect 4 passed.
- [ ] **Step 5: Run for real**; inspect shot 1 (spring should match `refs/1-3`), logging each prompt change as an experiment in `EXPERIMENTS.md` (hypothesis, change, result).
- [ ] **Step 6: Commit** `git commit -am "Add keyframe stage"`

### Task 7: Motion stage with Ken Burns, Wan handoff and fallback

**Files:**
- Create: `pipeline/shots.py`, `tests/test_shots.py`

**Interfaces:**
- Consumes: keyframes output, `Manifest`.
- Produces:
  - `kenburns(frame: Path, camera: str, seconds: float, out: Path, size: tuple[int,int]) -> Path` (FFmpeg `zoompan`, 24 fps)
  - `export_wan_jobs(storyboard: dict) -> Path` writes `outputs/jobs/wan_jobs.json` (9:16 keyframe path, motion prompt, seed, per-shot hash) for shots with mode `wan`
  - `import_wan(raw_dir: Path = ROOT/"outputs/shots/raw") -> list[str]` validates each clip with `ffprobe` (readable, at least 3 s), records it in the manifest, rejects zero-byte or truncated files
  - `run(storyboard: dict, durations: dict[str, float]) -> dict[str, dict[str, Path]]` per shot per ratio: Wan clip if valid for 9:16, else Ken Burns; 16:9 always Ken Burns; logs which was used

- [ ] **Step 1: Write failing tests** with a generated test PNG: `test_kenburns_output_has_requested_duration_and_size`, `test_wan_job_file_lists_only_wan_shots`, `test_truncated_wan_clip_is_rejected`, `test_missing_wan_clip_falls_back_to_kenburns_and_logs_it`, `test_16x9_never_uses_wan`.
- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement.** **Step 4: Run**, expect 5 passed.
- [ ] **Step 5: Commit** `git commit -am "Add shots stage with Ken Burns fallback and Wan import"`

### Task 8: Kaggle notebooks

**Files:**
- Create: `notebooks/00_smoke.ipynb`, `notebooks/10_acestep.ipynb`, `notebooks/20_wan.ipynb`, `notebooks/30_likeness.ipynb`, `notebooks/README.md`

**Interfaces:**
- `00_smoke`: prints GPU model, free disk, remaining quota, and loads nothing big.
- `10_acestep`: reads `music` from the uploaded `storyboard.json`, writes three instrumental candidates `music_{1,2,3}.wav`, logs seconds per track to `notebook_log.jsonl`.
- `20_wan`: reads `wan_jobs.json` and keyframes, renders 480p 9:16 TI2V-5B clips with CPU offload, saves each clip the moment it finishes, logs seconds per clip, resumes by skipping clips already present.
- `30_likeness`: only runs if the notebook README records both brothers' yes; reads portraits from a private Kaggle dataset; generates shots 8 (and 3) with FLUX.2 klein 4B reference images, same seed with and without references.

- [ ] **Step 1: Write notebooks** as plain `.ipynb` JSON with short markdown cells saying what to press and what to download.
- [ ] **Step 2: Verify** each loads as JSON and contains the log-writing cell: `python -c "import json;[json.load(open(f)) for f in ...]"`. Expected: no error.
- [ ] **Step 3: Abeni runs** `00_smoke` now; the agent records quota and GPU in `COSTS.md`.
- [ ] **Step 4: Commit** `git add notebooks && git commit -m "Add Kaggle notebooks"`

### Task 9: Music stage

**Files:**
- Create: `pipeline/music.py`, `tests/test_music.py`

**Interfaces:**
- Produces: `import_candidates(raw_dir: Path = ROOT/"outputs/music/raw") -> list[Path]` (validates with `ffprobe`); `choose(index: int, reason: str) -> Path` copies the pick to `outputs/music/score.wav` and appends the reason to `EXPERIMENTS.md`; `fallback_score(seconds: float, out: Path) -> Path` synthesises the same quiet pad as the radio cut when no candidate exists.

- [ ] **Step 1: Write failing tests** `test_choose_records_reason_in_experiments`, `test_zero_length_candidate_rejected`, `test_fallback_score_has_requested_duration`.
- [ ] **Step 2-4:** run FAIL, implement, run pass.
- [ ] **Step 5: Commit** `git commit -am "Add music stage"`

### Task 10: Assembly

**Files:**
- Create: `pipeline/assemble.py`, `pipeline/captions.py`, `tests/test_assemble.py`

**Interfaces:**
- `captions.render(text: str, size: tuple[int,int], out: Path) -> Path` wraps to max two lines of about 40 characters inside the safe area (vertical: bottom margin 18% of height) using a bundled open-licence font.
- `captions.end_card(text: str, size: tuple[int,int], out: Path) -> Path`
- `assemble.run(storyboard: dict, durations: dict[str, float], ratio: str) -> Path` writes `outputs/final_9x16.mp4` or `outputs/final_16x9.mp4`: shots cut to `max(narration, 3.0)` seconds with 0.4 s crossfades, captions overlaid with `enable='between(t,a,b)'`, score ducked, two-pass `loudnorm`, 3 s end card, 60 to 90 s total.

- [ ] **Step 1: Write failing tests** with generated fixtures: `test_total_duration_between_60_and_90_seconds`, `test_shot_extended_when_narration_longer`, `test_audio_loudness_near_minus_14_lufs` (measure with `ffmpeg -af ebur128`, tolerance 1.5), `test_true_peak_below_minus_1_dbtp`, `test_caption_never_exceeds_two_lines_or_42_chars`, `test_output_codecs_are_h264_aac_constant_fps`.
- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement.** **Step 4: Run**, expect 6 passed. If total is under 60 s, adjust shot minimums or add a silent beat in the storyboard, logged as an experiment.
- [ ] **Step 5: Commit** `git commit -am "Add assembly with captions, ducking, loudness and both ratios"`

### Task 11: One command, caching proof, clean clone

**Files:**
- Modify: `Makefile`
- Create: `pipeline/run_all.py`, `tests/test_end_to_end.py`, `scripts/clean_clone_check.sh`

**Interfaces:**
- `run_all.main() -> None` runs validate, narrate, keyframes, shots, music (with fallback score if none), assemble for both ratios; prints per-stage seconds. `make film` calls it.
- `scripts/clean_clone_check.sh` clones the repo into a temp directory, copies `.env`, runs `make setup film`, and fails unless both MP4s exist with 60 to 90 s duration.

- [ ] **Step 1: Write failing test** `test_second_run_makes_no_model_calls` and `test_one_narration_edit_regenerates_only_that_shot_and_reassembles` with fakes for every provider.
- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement.** **Step 4: Run**, expect pass.
- [ ] **Step 5: Run** `bash scripts/clean_clone_check.sh`; paste the result into `FAILURES.md` if it breaks and fix.
- [ ] **Step 6: Commit** `git commit -am "Add make film, caching tests and clean-clone check"`

### Task 12: Second user test, docs, report, release kit

**Files:**
- Create: `README.md`, `ARCHITECTURE.md`, `DESIGN.md`, `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, `ETHICS.md`, `REPORT.md`, `POST.md`, `WALKTHROUGH.md`, `scripts/check_docs.py`, `tests/test_docs.py`

**Interfaces:**
- `check_docs.main() -> int` returns non-zero when: any required file is missing; `EXPERIMENTS.md` has fewer than 10 entries each containing Hypothesis, Change and Result; `ETHICS.md` lacks both brothers' consent text; `runs.jsonl` is missing or any line lacks a required field.

- [ ] **Step 1: Write failing tests** `test_missing_file_fails`, `test_nine_experiments_fails_ten_passes`, `test_runs_line_missing_field_fails`, `test_ethics_without_consent_fails`.
- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement** `check_docs.py`. **Step 4: Run**, expect pass.
- [ ] **Step 5: Second user test:** send the near-final cut to the same three listeners (a fourth if possible); Abeni records their words in `DESIGN.md` and the agent applies one change they asked for.
- [ ] **Step 6: Write the docs** from real material only: `ETHICS.md` holds Tesfa's and Beki's replies verbatim, the photo-upload yes (relayed by Abeni; paste their exact messages), licences (Wan 2.2 Apache 2.0, ACE-Step 1.5 MIT, FLUX.2 klein 4B Apache 2.0, FLUX.1 schnell Apache 2.0, Gemini terms), the labelling plan; `COSTS.md` uses measured seconds from `runs.jsonl` and notebook logs with list-price equivalents; `REPORT.md` covers the sections the brief names, including one practice that beat Abeni's instinct and one that did not, only if they truly happened; `POST.md` is a draft Abeni rewrites in his own words; `WALKTHROUGH.md` is a five-minute outline ending with the one-line edit and a single-shot regeneration.
- [ ] **Step 7: Run** `uv run python scripts/check_docs.py`. Expected exit 0.
- [ ] **Step 8: Commit** `git commit -am "Add docs, report and release kit"`; Abeni creates the public GitHub repo, and the push needs his explicit yes.
