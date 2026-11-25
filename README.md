# Forty Springs

A 65 second painted short about three brothers swimming at a spring in Arba Minch, narrated in
English, with English subtitles, a score, and an end card saying it was made with AI. It is also a
small pipeline: one file, `storyboard.json`, drives every stage, and changing one shot regenerates
only that shot.

Made for the 10 Academy AI-Content Generation challenge. The film is for the author's two brothers.

## Run it

You need: [uv](https://docs.astral.sh/uv/), FFmpeg with the `zoompan`, `sidechaincompress`, `loudnorm`
and `overlay` filters (any normal build; it does not need `libass`), and keys in a `.env` file
(copy `.env.example`):

```
GEMINI_API_KEY=...     # Google AI Studio, for the narration voice
CF_ACCOUNT_ID=...      # Cloudflare account id
CF_API_TOKEN=...       # a Cloudflare API token with Workers AI access
```

```bash
make setup           # install Python 3.12 dependencies
make film            # the whole film, both ratios, into outputs/
make film VOICE=say  # same, with a local placeholder voice (macOS) if Gemini's free quota is spent
make test            # the test suite
```

`make film` writes `outputs/final_9x16.mp4` (the phone version) and `outputs/final_16x9.mp4`.
On a fresh clone with a placeholder voice it took about 4.8 minutes, almost all of it the 20 image
calls (see `COSTS.md`). `scripts/clean_clone_check.sh` proves that: it clones, runs, and checks both
files are 60 to 90 seconds.

## What it does

| Stage | Script | Makes |
|---|---|---|
| contract | `pipeline/validate.py` | checks `storyboard.json` against `schema/storyboard.schema.json` |
| narration | `pipeline/narrate.py` | one voice file per line (Gemini TTS) |
| keyframes | `pipeline/keyframes.py` | one painted still per shot per ratio (FLUX.2 klein 4B on Cloudflare) |
| moving shots | `pipeline/shots.py` | Ken Burns by default, Wan 2.2 clips where you downloaded them |
| music | `pipeline/music.py` | imports ACE-Step candidates, records which one you chose and why |
| assembly | `pipeline/assemble.py` | cut, captions, ducking, loudness, end card, both ratios |

`ARCHITECTURE.md` explains the contract, the caching and what happens when something fails.

## The two jobs that need a GPU

Wan 2.2 (moving shots) and ACE-Step (the score) run by hand in Kaggle notebooks. See
`notebooks/README.md`. Without them the film still builds: moving shots fall back to a slow pan over
the painted still, and the score falls back to a quiet synthesised pad. Both fallbacks are logged.

## Change one shot

Edit a prompt or a narration line in `storyboard.json`, run `make film`, and only the affected
files are rebuilt. `runs.jsonl` gets a line for every model call, so you can see exactly what ran.

## The files that explain the work

`DESIGN.md` (who it is for, what listeners said), `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`,
`ETHICS.md` (consent and licences), `REPORT.md`.

## Cost

Everything ran on free tiers. The list-price equivalent of the whole run is a few cents; the numbers
are in `COSTS.md`.
