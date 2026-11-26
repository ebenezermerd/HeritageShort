# Costs

Everything was run on free tiers with no card. "Measured" numbers come from `runs.jsonl`; "list
price" is what the same work would cost at published rates, looked up on 25 Nov 2026.

## Measured latency per stage

| Stage | Provider / model | Calls | Mean | Total |
|---|---|---|---|---|
| Keyframes | Cloudflare, FLUX.2 klein 4B, 768x1344 or 1344x768 | 38 | 8.9 s | 339 s |
| Candidates | Cloudflare, FLUX.2 klein 4B, 768x1344 | 30 | 9.1 s | 273 s |
| Narration (Gemini) | Gemini 3.8 Flash TTS | 10 successful (plus 2 in smoke tests) | 4.2 s | 42 s |
| Narration (placeholder) | macOS `say`, voice Daniel | 9 | 0.85 s | 8 s |
| Moving shots | FFmpeg `zoompan` | 20 | 0.8 s | 16 s |
| Assembly | FFmpeg | 4 | 24 s | 96 s |
| Keyframes and references (second route) | Kaggle T4, FLUX.2 klein 4B via `diffusers`, 4 steps | 61 images (2 references, 59 candidates) | 99 s | 6,056 s, about 101 GPU minutes (`outputs/kaggle_logs/notebook_log_keyframes_rerun.jsonl`); the four out-of-memory attempts before it are not timed |
| Wan 2.2 clips | Kaggle T4 | not run (E20) | | 0 |
| ACE-Step score | Kaggle T4, ACE-Step 1.5 turbo | 1 batch of 3 x 65 s | 18.5 s generation | 0.3 GPU min generating; the first run also spent several minutes installing and downloading weights (not timed) |

A fresh clone with the placeholder voice built both films in about 4.8 minutes (the log is saved in `docs/evidence/clean_clone_2026-11-25.log`; it ran in a temporary clone with its own `runs.jsonl`, so its roughly 20 image calls are not in the table above): narration 9.3 s,
keyframes 192.5 s, shots 21.2 s, assembly 31.5 s and 33.8 s. Failures are in the log too: 38 failed
Gemini speech calls (the daily quota, FAILURES #4) and 3 failed smoke calls.

## Free-tier limits I actually hit or read

- **Gemini TTS:** 10 requests per day per model on the free tier (read from the 429 error body).
  This is the tightest limit in the whole project.
- **Cloudflare Workers AI:** 10,000 neurons a day free. klein costs 26.05 neurons per 512x512 output
  tile, and a 768x1344 image is about 3.9 tiles (my calculation), so about 100 neurons an image and
  roughly 97 images a day.
- **Kaggle:** 30 GPU hours a week, read from the notebook sidebar on 25 Nov ("Quota: 00:05 / 30 hrs"
  after the smoke test). The smoke test saw two Tesla T4s with 15.6 GB each and 20.9 GB of free disk.

## List-price equivalent

| Item | Rate | This project |
|---|---|---|
| FLUX.2 klein 4B on Workers AI | $0.000287 per 512x512 output tile | about $0.0011 an image, so the 20 final keyframes cost about $0.023 and all 38 calls about $0.043 |
| Gemini 3.8 Flash TTS | $9 per 1M audio tokens, about $0.00225 per 10 s of audio, until 31 Dec 2026 ($0.0045 from 1 Jan) | the narration is about 25 s, so about $0.006 |
| klein on Kaggle, ACE-Step | open weights, run on free Kaggle GPUs | no list price looked up; about 1.7 GPU hours of the 30 a week went on klein, a few minutes on ACE-Step |
| FFmpeg, Pillow | free | $0 |

Whole project at list price: a few cents. The real cost was my time and one daily quota.

## Frontier comparison

None. I had no access to a frontier image, video or music model, so there is no like-for-like
comparison. I checked: the Gemini key lists Nano Banana and other image models, but the free tier allows
0 image requests (FAILURES #10). The only model comparison I made is klein against schnell (E05).

## Trade-offs I chose

- **10 times slower images, for consistency.** klein on Cloudflare took about 9 s an image; the same
  model on a Kaggle T4 took about 99 s, because it had to run with CPU offload and small reference
  images to fit in memory. I paid that because Cloudflare's quota had stopped resetting, and because
  only the local run could take the spring and the brothers as reference pictures reliably.
- **No Wan.** It was planned for four 9:16 shots only (16:9 would double the GPU time). In the end it
  was not run at all (E20), so its cost is zero and the four shots are camera moves.
