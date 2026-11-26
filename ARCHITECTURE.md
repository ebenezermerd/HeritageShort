# Architecture

## The contract

`storyboard.json` is the only thing the stages share. `schema/storyboard.schema.json` is checked
before every run (`pipeline/validate.py`), and a bad storyboard stops the run with the exact JSON
path that failed. Each shot carries everything that decides its output: `reason`, `narration`
(or `null` for a silent shot), `image_prompt`, which `characters` appear, `seed`, `duration_s`, and
`motion` (`kenburns` or `wan`, a camera move, and a motion prompt). Prompts and seeds live in the file,
not in code, so a run can be reproduced and explained.

Each stage reads the storyboard and writes under `outputs/<stage>/`. Stages do not call each other
except through those files, and each can be run alone (`python -m pipeline.narrate`).

## One timing rule

`pipeline/timeline.py` decides how long each shot lasts: its `duration_s`, or its narration plus half
a second if the narration is longer. The radio cut and the final film both use it, so a listener test
of the radio cut is a test of the real pacing. Narration is only about 25 seconds, so the shots carry
the rest of the 65 seconds on purpose.

## Caching

Every stage hashes exactly the inputs that decide an output (`common.input_hash`: the prompt as it is
sent, seed, model, ratio, and the bytes of any input file) and stores it in
`outputs/<stage>/manifest.json`. A file is rebuilt only if the hash changed or the file is missing.
Examples from real runs: changing the character looks and two prompts regenerated 14 of 20 images, then
4; a second `make film` makes no model calls and logs nothing new (a test pins that).

The narration key covers the *prompt sent*, not only the text, so when I changed the prompt format the
old audio could not be reused by mistake. The assembly key includes the ducking, limiter and loudness
settings for the same reason.

## Failure handling

- **Retries.** Three attempts per call with backoff (`common.with_retries`). Every attempt is logged
  to `runs.jsonl`, failures included, with the error text.
- **Keep going.** A failed shot does not stop the other shots. The stage finishes the rest and then
  reports which shots failed.
- **Fallbacks, never silent.** A `wan` shot with no valid clip becomes a Ken Burns shot and is logged
  `fallback`. A missing score becomes a synthesised pad, logged `fallback`. 16:9 never uses Wan clips
  (a deliberate GPU-quota trade-off, see `COSTS.md`).
- **Validated imports.** A downloaded Wan clip or music file is fully decoded with FFmpeg, not just read
  from its header, because a file cut short after an intact header still reports its full length. A
  truncated or empty file is ignored, not used. A Wan clip must also carry a job hash (a small `.json`
  beside it) matching the current keyframe, prompt and seed, or it is treated as stale and replaced by
  a Ken Burns pass.
- **Quota.** Free tiers run out. The narration stage can switch to a clearly labelled local voice
  (`--voice say`, logged as provider `macos`) so work continues; it must not be the submitted voice, so any build with it is named `final_*.say-placeholder.mp4` and `runs.jsonl` records the voice.
- **Secrets.** Keys are read from a git-ignored `.env`. A missing key stops the stage with the name of
  the variable and writes nothing.

## Assembly (all FFmpeg, deterministic)

1. Shots are cut hard to the timeline (no crossfades, which would move picture away from the voice).
2. Captions and the end card are drawn with Pillow and overlaid with `overlay=enable='between(t,a,b)'`
   because this FFmpeg has no `libass` or `drawtext`. Captions are at most two lines of about 40
   characters, inside the safe area.
3. The score is ducked under the voice with `sidechaincompress` (threshold 0.02, ratio 6, attack
   300 ms, release 1500 ms), which lowered it by 15.2 dB in a measurement (E07).
4. A peak limiter, then two-pass `loudnorm` to -14 LUFS with a true-peak ceiling of -3 dB before AAC encoding (the encoded file stays under -1 dB, see E15). The final
   film measures -14.7 LUFS (E06 to E08).
5. H.264 video at a constant 24 fps and AAC audio, in both 9:16 and 16:9.

## Where the GPU work happens

Wan 2.2 and ACE-Step run in Kaggle notebooks (`notebooks/`). The handoff is files. `make
kaggle-bundle` writes the keyframes and job file to upload; the notebooks write clips and tracks that
are downloaded into `outputs/shots/raw/` and `outputs/music/raw/`. Chosen files are committed under
`assets/` (`make save-assets`): the score, the 20 picked keyframes, the two reference pictures and the
Gemini narration, each with its stage's manifest. `make film` copies them back into `outputs/` when they
are missing, so every stage sees them as cached and a clean clone rebuilds the finished film without a
single model call. They have to be kept as files: klein on Cloudflare does not repeat an image from its
seed (E14), and Gemini allows 10 speech requests a day.
