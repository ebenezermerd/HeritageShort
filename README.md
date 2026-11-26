# Forty Springs

A 63 second painted short about three brothers swimming at a spring in Arba Minch, narrated in
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
make film VOICE=say  # placeholder voice (macOS) if Gemini's free quota is spent; output is named
                     # final_9x16.say-placeholder.mp4 so it cannot pass for the real film
make test            # the test suite
```

`make film` writes `outputs/final_9x16.mp4` (the phone version) and `outputs/final_16x9.mp4`, made with the real Gemini voice. `make film VOICE=say` names its files `*.say-placeholder.mp4`.
The chosen pictures, the Gemini narration and the score are committed under `assets/`, so a fresh
clone rebuilds the submitted film in under a minute with no keys and no model calls (the narration,
reference and keyframe stages find everything cached). `scripts/clean_clone_check.sh` proves that: it
clones, runs `make setup film`, checks both files are 60 to 90 seconds, and fails if the build made any
model call (`docs/evidence/clean_clone_2026-11-26.log`). Keys are only needed to make new pictures or
lines after changing the storyboard.

## What it does

| Stage | Script | Makes |
|---|---|---|
| contract | `pipeline/validate.py` | checks `storyboard.json` against `schema/storyboard.schema.json` |
| narration | `pipeline/narrate.py` | one voice file per line (Gemini TTS) |
| references | `pipeline/references.py` | one picture of the spring and one of the three brothers, passed to every shot so they stay the same |
| keyframes | `pipeline/keyframes.py` | one painted still per shot per ratio (FLUX.2 klein 4B, Cloudflare or Kaggle) |
| Kaggle images | `pipeline/kaggle_images.py` | writes the image job list for notebook 15 and imports what it made |
| candidates | `pipeline/candidates.py` | several options per shot; `pick` in `storyboard.json` names the chosen one, which is kept as the keyframe |
| ambience | `pipeline/ambience.py` | water and splash effects from FFmpeg, used only if there is no score (E18) |
| moving shots | `pipeline/shots.py` | Ken Burns by default, Wan 2.2 clips where you downloaded them |
| music | `pipeline/music.py` | imports ACE-Step candidates, records which one you chose and why |
| assembly | `pipeline/assemble.py` | cut, captions, ducking, loudness, end card, both ratios |

`ARCHITECTURE.md` explains the contract, the caching and what happens when something fails.

## The two jobs that need a GPU

ACE-Step (the score) and, when Cloudflare's quota ran out, the keyframes ran by hand in Kaggle
notebooks (`15_keyframes`). Wan 2.2 (moving shots) has a notebook too but was not run for the
submitted film (E20). See `notebooks/README.md`. Without them the film still builds: moving shots fall back to a slow pan over
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
