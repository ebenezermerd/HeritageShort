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
