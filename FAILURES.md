# Failures

What broke while building this, what I tried, and what I did about it.
Entries are in the order they happened. Raw evidence is in `runs.jsonl`.

## 1. FFmpeg here cannot burn in subtitles (25 Nov, before any code)

**What happened.** I planned to burn subtitles with FFmpeg's `subtitles` or
`drawtext` filter. Before writing anything I checked the build on this Mac
(FFmpeg 8.1.2) and neither filter exists: it was built without `libass` and
without `libfreetype`.

**What I tried.** Looked at installing a fuller FFmpeg build. That would make
"clone the repo and run one command" depend on a Homebrew rebuild, which a
stranger may not have.

**What fixed it.** Caption text and the end card are rendered to PNGs with
Pillow and laid over the video with FFmpeg's `overlay` filter, switched on by
`enable='between(t,a,b)'`. It works on any FFmpeg that has `overlay`.

## 2. Cloudflare rejected a seed for flux-1-schnell (25 Nov, first smoke run)

**What happened.** The smoke test sent `seed` to
`@cf/black-forest-labs/flux-1-schnell` and Cloudflare answered
`Bad input: Additional or unevaluated properties '/seed' at '/' not allowed`
(0.46 s, logged `failed` in `runs.jsonl`).

**What I tried.** Removed the field. The call then worked (3.0 s).

**What it means.** schnell on Cloudflare cannot be pinned to a seed, so it is
not reproducible. FLUX.2 klein 4B accepts a seed and worked first time
(6.0 s), so klein is the keyframe model and schnell is only a comparison
and a fallback. A test (`test_schnell_payload_never_sends_a_seed`) keeps it
that way.

## 3. Gemini 3.8 Flash text returns 503 (25 Nov, smoke run)

**What happened.** `gemini-3.8-flash` (text) answered
`503 Service Unavailable` on both smoke runs, including after three retries
spread over 16 s. The speech model `gemini-3.8-flash-tts` on the same key
worked every time (about 4.3 s).

**What I tried.** Probed `gemini-3.8-flash-lite`, `gemini-3.7-flash` and
`gemini-3.5-flash` on the same key. All three returned 404 for
`generateContent` even though the model list names them.

**What I did.** Nothing in the pipeline's critical path needs Gemini text (the
storyboard is written by hand against the schema), so I did not block on it.
Speech is the Gemini feature the film depends on and it is healthy. I will
retry text later and say here if it recovers.

## 4. Gemini's free speech quota is 10 requests a day, and I spent it (25 Nov)

**What happened.** About a dozen narration calls into the afternoon every call
began returning `429 RESOURCE_EXHAUSTED`. I read the error body and it says it
plainly: `generate_content_free_tier_requests, limit: 10, model:
gemini-3.8-flash-tts`, "per day limit exceeded on Free Tier", retry in about 20
hours. `runs.jsonl` shows 12 successful speech calls (10 narration and 2 smoke) and 38 failed narration calls. The three E01 experiment calls came from a throwaway script that did not log, so they are not in the file.

**How I used it up.** Two smoke runs, the first nine-line narration pass, a prompt
experiment (E01), and my own retries. A 2 s and 4 s backoff was far too short
for a limit that resets daily, and I raised it to 15 s and 30 s, but that only
helps with per-minute limits.

**What I tried.** Other speech models on the same key: `gemini-3.8-flash-lite-tts`,
`gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-preview-tts` and
`gemini-2.5-pro-preview-tts` all appear in the model list and all return 404 for
`generateContent`. So there is no second Gemini voice to fall back to.

**What I did.** Added a local placeholder voice (macOS `say`, "Daniel") behind the
same interface (`narrate.py --voice say`), logged as provider `macos` so it can
never pass for Gemini. The radio cut for the first user test uses it. The
final film's narration is generated with Gemini after the quota resets, which
needs 9 of the 10 daily requests, so retakes are limited to one per day. That
makes "change one narration line" a cheap, safe demo for the walkthrough.

Shot 1's line, "Arba Minch means forty springs.", had already been made with Gemini during experiment E01
(same voice, model and plain prompt), so I registered that clip with `narrate.import_audio`. It is
logged as `imported` in `runs.jsonl`, not as a new request. The real run after the reset therefore needs
8 requests, which leaves 2 retakes.

## 5. klein returned JPEG bytes and I saved them as .png (25 Nov)

**What happened.** FFmpeg refused every keyframe: `Invalid PNG signature
0xFFD8FFE000104A46`. `FF D8` is the JPEG signature. Cloudflare's FLUX.2 klein
answers with JPEG data while I had named the files `.png`.

**What fixed it.** A test that checks the saved file really starts with the PNG
signature (it failed first), then `to_png()` in `keyframes.py` re-saves through
Pillow. The 20 images already on disk were converted in place so no free image
quota was spent again.

## 6. My own scripts cost me time twice (25 Nov)

- The first TTS experiment script patched the very function one of its variants
  called, and died with a `RecursionError` after a long rate-limit wait.
- `radio_cut`'s `main` asked for the Gemini voice while the quota was gone. It
  sat in 15 s and 30 s retry waits for eight shots until I stopped it. It now
  takes `--voice`, and I now check the quota before long runs.

## 7. loudnorm quietly stopped doing its job (25 Nov)

**What happened.** My loudness tests passed, but measuring the real film showed -15.5 LUFS, not the
-14 I had set. Nothing errored.

**What I tried.** First I guessed high peaks and built a synthetic test signal to reproduce it. Two
versions of that signal passed without the bug, so they proved nothing. I stopped guessing and read
loudnorm's own measurement of the real mix: loudness range 17.2 LU against a target of 11, and
`normalization_type: dynamic`. It had switched to its fallback mode.

**What fixed it.** A peak limiter before loudnorm (`alimiter limit=0.3`), chosen from a measured
comparison (E08). The assembly cache key now includes the audio settings, so changing them cannot
be skipped by a stale cache. The honest gap: I have no failing test that reproduces this; the evidence
is the measurements in `EXPERIMENTS.md` E06 to E08.

## 8. The first keyframes were not checked, and the seed did not do what I assumed (25 Nov)

**What broke.** The author reviewed the film and found the images "awful", with people who "have like
four hands sometimes". I had generated one image per shot and never looked closely at hands or faces,
although the brief says to check them before spending GPU time. Shot 7 showed four hands, shot 6 a
pale boy in a white shirt, shot 8 three different skin tones.

**What I tried.** Regenerate with new seeds. When the picked 9:16 image came back different on the
rebuild, I tested the seed directly and found klein does not reproduce an image from the same seed
(E14).

**What fixed it.** Three candidates per shot, judged by eye (E15), and a `pick` step that keeps the
chosen file instead of trusting the seed.

**What I would do differently.** Look at every image the moment it is made, and treat "same seed" as a
claim to test rather than a fact. It also means the Wan clips will animate clean pictures.
