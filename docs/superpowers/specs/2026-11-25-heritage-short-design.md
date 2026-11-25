# Heritage Short: design

Working title: **Forty Springs** (Arba Minch literally means "forty springs").
Author: Abenezer (Abeni). Written 25 Nov 2026. Status: draft for approval.

## Intent and the why

A 60-90 second film about the days Abeni, Tesfa (Tesfa) and Bereket (Beki)
swam together at a spring in their hometown, Arba Minch. It exists because
the three of them no longer get to do that, and a short film is a way to
hand the afternoon back to them.

It is also the 10 Academy "AI-Content Generation" challenge (B2W0). Two
submissions are due **Thu 26 Nov 2026, 23:59 EAT**. We have about one
working day, not three, so scope is cut to what can be finished and proven.

## Audience

Tesfa and Beki first, plus Abeni. Anyone else who watches is a bonus.
They watch on a phone, so vertical 9:16 is the primary export and 16:9 is
the second. After it ends they should feel: *we really were that happy,
and I want to go back.* Laughing, not sad nostalgia.

## Goals

- A finished film in both ratios: English narration, English subtitles,
  an original score ducked under the voice, an end card saying it was made
  with AI.
- A pipeline where `storyboard.json` is the only contract, `make film`
  rebuilds everything from a clean clone, and changing one shot
  regenerates only that shot.
- Evidence in text: `runs.jsonl` (one line per model call), `DESIGN.md`,
  `EXPERIMENTS.md` (aim for ten), `FAILURES.md`, `COSTS.md`, `ETHICS.md`.
- Two real user tests (radio cut, near-final cut), at least three listeners
  each, written up honestly, with the storyboard visibly changed by them.

## Non-goals

- Photoreal likenesses of the brothers.
- More than one language. English only (Abeni's call; it removes the
  Amharic text-to-speech risk).
- A web app, an MCP server or a LoRA. Only if the floor is finished early.

## Anti-goals (a failure even if it technically works)

- Docs that read like generic filler. Every doc entry cites something that
  actually happened: a log line, a listener's words, a real error.
- A real person's face or voice generated before written consent is in
  `ETHICS.md`. Without it the film scores zero.
- Inventing memories. The narration is Abeni's. Specifics the model made
  up and Abeni did not confirm do not ship.
- Committing the Gemini key or any token.

## Constraints

- Deadline above. No payment card; free tiers only (Gemini API,
  Cloudflare Workers AI, Kaggle ~30 GPU hours/week, Colab as backup).
- Local machine: macOS, Python 3.14, FFmpeg 8.1 with **libx264, loudnorm,
  sidechaincompress, zoompan, but no libass and no drawtext**. FFmpeg
  cannot burn in subtitles or draw text on this machine.
- Kaggle and Cloudflare logins are Abeni's. The agent cannot sign in.
- Free endpoints may train on what they receive, so no real photo of a
  person is uploaded unless a separate decision allows it (see Likeness).

## Approaches considered

All three share the same shape: storyboard.json, then keyframes, shots,
music, narration, assembly.

**A. Full GPU path.** Flux keyframes, Wan 2.2 for every shot on Kaggle,
ACE-Step on Kaggle, FFmpeg. Highest ceiling, but one Kaggle problem
(timeouts, quota, setup) blocks the whole film. Too risky for one day.

**B. Hybrid with a guaranteed fallback. (Chosen by Abeni, as recommended.)**
Flux keyframes for every shot. Each shot has a `motion` field. Default is a
Ken Burns pan over the still (FFmpeg `zoompan`). Wan 2.2 is used only for
the 3-5 shots that matter most. ACE-Step makes three score candidates.
After three failed attempts a shot falls back to Ken Burns on its own, so a
finished film always exists. Ken Burns versus Wan on the same shot is a
ready-made experiment.

**C. Stills only.** Safest, but drops the moving-shots stage, ACE-Step and
GPU measurement, so it gives up marks in several criteria.

## Design decisions

Decided by Abeni: approach B; English narration; audience is the brothers;
painted look is fine; written consent obtained (see ETHICS below).

My calls, to be checked:

- **Pipeline language:** Python, run through `uv` with a pinned Python 3.12
  environment. The machine has 3.14 and some media libraries lag behind.
- **Entry point:** `make film`. Stages are `pipeline/01_script.py` through
  `06_assemble.py`, each callable alone. Each reads `storyboard.json`
  and writes under `outputs/<stage>/`.
- **Validation:** `schema/storyboard.schema.json`, checked with
  `jsonschema` before any stage runs. A bad storyboard stops the run.
- **Caching:** each shot's output is keyed by a SHA-256 of exactly the
  inputs that affect it (prompt, style block, seed, model id, reference
  files, motion settings). Same hash and file present means skip. The key
  is stored in `outputs/<stage>/manifest.json`.
- **Retries:** exponential backoff, three attempts per shot per stage, then
  the stage's declared fallback (Ken Burns for motion; skip and flag for
  everything else). Every attempt writes a `runs.jsonl` line, including
  failures.
- **`runs.jsonl` fields:** timestamp, stage, shot id, provider, model,
  parameters, seed, input hash, latency seconds, status, cost
  (list-price equivalent, 0 actual), error text if any.
- **Secrets:** `.env` is git-ignored; `.env.example` lists names only. The
  Gemini key Abeni pasted into chat should be regenerated after submission.
- **Keyframes:** Cloudflare Workers AI, FLUX.2 klein if it is available on
  the free tier, otherwise FLUX.1 schnell. The exact model id is confirmed
  in the smoke test, not assumed.
- **Narration:** Gemini TTS, one audio file per shot, so one line can be
  re-recorded without touching the others. English, calm and unhurried style
  instruction. Voice is a stock voice, not a clone of any person.
- **Wan 2.2 and ACE-Step:** run in Kaggle notebooks by Abeni. File handoff:
  the pipeline writes `outputs/jobs/` (keyframes and prompts), the notebook
  writes clips and tracks back, and Abeni downloads them into
  `outputs/shots/raw/` and `outputs/music/raw/`. Checksums go in the
  manifest so caching still works.
- **Music:** three ACE-Step candidates from a short spotting note, instrumental,
  chosen by ear under the narration, with the reason in `EXPERIMENTS.md`.
  Tempo and key go in the metadata fields, not the caption.
- **Assembly (all FFmpeg, deterministic):** cut to the narration timing,
  duck music with `sidechaincompress` (start at threshold 0.02, ratio 6,
  attack 300 ms, release 1500 ms), two-pass `loudnorm` to about -14 LUFS
  and true peak -1 dB, H.264 + AAC, constant frame rate.
- **Subtitles and end card without libass:** render caption images and the
  end card with Pillow and overlay them with FFmpeg's `overlay` filter,
  `enable='between(t,a,b)'`. Max two lines, about 40 characters a line,
  inside the vertical safe area. This is a good `FAILURES.md` entry
  (what broke, what replaced it).
- **Framing (my call, revised after review):** a centred square crop
  cannot hold three people side by side in both ratios. So keyframes are
  generated **per ratio**: a 9:16 set (primary) and a 16:9 set. Images
  are cheap on the free tier (about 20 plus retries fits the daily
  allowance). Wan runs in **9:16 only**, on the 3-4 hero shots. The 16:9
  export uses a Ken Burns pass over its own 16:9 keyframe for those shots.
  The two exports therefore differ slightly in motion; this is stated in
  `ARCHITECTURE.md` and `COSTS.md` as a GPU-quota trade-off.
- **Faces (my call, revised after review):** Flux without reference images
  will not hold three faces perfectly across shots. So the shot list keeps
  faces **small, turned away, or partly hidden** (backs, distance,
  silhouettes, hands, splash) in most shots, with at most two shots where
  faces are readable. How well identity holds is logged as an experiment,
  not hidden.
- **Placeholder narration:** the pipeline is built against placeholder
  text first. Because caching is keyed on the exact line, filling in
  Abeni's real words re-runs only the narration and the shots whose timing
  changed.
- **Clean clone (my call):** the chosen Wan clips and music track, at draft
  resolution, are committed under `assets/` (no LFS, a few tens of MB).
  `make film` uses them if present. Everything else rebuilds from the
  storyboard. The README says plainly that the Kaggle steps are manual and
  shows how to re-run them.

## Deliverables and what they are scored on

(From the 10 Academy brief; the grader reads text, not media, for
assignment 1.)

- **Assignment 1, codebase and report (100):** public GitHub repo with one
  documented command; report (PDF/Word/link). Engineering and
  reproducibility 20, documentation 10, design thinking and audience 10,
  experiments (ten with hypotheses) 10, troubleshooting 10, measurement 5,
  consent/labelling/licences 5, report sections 30. Followed by an AI
  interview about the work.
- **Assignment 2, film, walkthrough, post (100, graded by hand):** film 50
  (both ratios, 60-90 s), walkthrough of at most five minutes with one shot
  regenerated on screen 30, public post with the AI label on 20. Links
  must open without a login.
- **Hard gate:** a real person shown or voiced without consent in
  `ETHICS.md` scores zero for the film.
- **Radio cut** means narration over placeholder music on a black screen,
  no pictures. It is the first thing tested with listeners.

## Settled with Abeni (25 Nov)

- **Who and when:** the memory is from when Beki was 19, Tesfa 17 and
  Abeni 16. Beki is the oldest, Tesfa the middle brother, Abeni the
  youngest. So the characters are painted as teenagers, not as the grown
  men in the portraits.
- **What happened (his words):** the oldest brother jumped first, then
  Tesfa, then Abeni last. They splashed each other, did flips and tricks
  from the tree beside the water, and shouted "Whoa, whoa, whoa" a lot.
  They were just having fun.
- **How much I may fill in:** Abeni said not to make the memory overly
  specific and to recreate the rest. So the narration and shots stay close
  to what he told us. Anything beyond it is marked **(added)** in the
  drafts and he confirms or cuts it before the radio cut.
- **Listeners:** Tesfa, Beki and Abeni's friend Amani. That is three people
  for each test. The same three can hear both cuts; fresh ears would be
  better, so a fourth is welcome.
- **Kaggle:** Abeni runs the notebooks, the agent writes them (schedule
  below).

## Likeness

Abeni wants the painted brothers to look like them as much as possible, and
accepts a looser resemblance if that is not possible.

Both brothers agreed in writing to the film. Their replies were to a
message that said photos might be used "as private reference". Uploading a
face to a hosted service is not private, so before any photo leaves this
machine each brother must say yes to that specifically.

Plan (option 3, tilted toward likeness):

1. **Default, no consent needed beyond what exists:** every keyframe from a
   text description (Cloudflare FLUX). Faces small or turned away.
2. **Likeness test, after the extra yes:** run a reference-image model
   (FLUX.2 klein 4B, Apache 2.0, open weights) inside Abeni's own Kaggle
   notebook with the portraits uploaded as a *private* Kaggle dataset, not
   to a public inference endpoint. Generate the two readable-face shots
   (shot 8, and shot 3 if it works) both ways.
3. **Decision rule:** the brothers pick, blind, which version looks more
   like them. If the reference version wins, the film uses it for those
   shots; the result goes in `EXPERIMENTS.md` either way.
4. The portraits show grown men, the memory is of teenagers. Expect the
   model to age them up; the prompt asks for teenage boys with their hair
   and build, and the drift is logged.

Photo ownership, as told by Abeni: Tesfa is #4-left, #5, #6, #7. Beki is
#8, #9, #10. Abeni is #4-right and #11-#14. Photos #1-#3 show strangers at
the spring and are used for the place only, never faces.

Draft look notes for the prompts (from the portraits; Abeni to correct):
Beki, tallest and oldest, short curly hair. Tesfa, slimmer, short hair.
Abeni, youngest, short hair. As teenagers all three swim in plain shorts;
shots stay wholesome and wide.

## Story draft (shot list)

About 60-75 seconds plus a 3 s end card. Shouts are an audio layer, not
narration: first try a lively TTS read of the shout, and test a real sound
effect against it as an experiment. No one's voice is cloned.

| # | Shot | Why it exists | Motion |
|---|------|---------------|--------|
| 1 | Wide: the spring in morning light, turquoise water, trees | Say where we are | wan |
| 2 | Three teenage brothers walking to the water, from behind | Meet the three without faces | kenburns |
| 3 | Beki, the oldest, mid-air jumping off the bank, back to camera | He goes first | wan |
| 4 | Tesfa mid-jump toward the water | He goes second | kenburns |
| 5 | Abeni last at the edge, then leaping | The youngest goes last | kenburns |
| 6 | One of them flipping off the tree branch over the water | The tricks from the tree | wan |
| 7 | Insert: hands throwing water, drops in the air | Joy in detail | kenburns |
| 8 | Medium: all three in the water, mouths open, shouting and laughing | The core feeling | wan |
| 9 | Wide: the empty spring, ripples settling, golden light | Time has passed | kenburns |
| 10 | The three sitting on the bank, feet in the water, from behind | Closing image | kenburns |
| 11 | End card: "Made with AI. Painted from memory." | Required label | still |

Draft narration, in Abeni's voice. Lines built only from what he told us
are plain; invented lines are marked **(added)**.

1. "Arba Minch means forty springs."
2. "We only ever needed one." **(added)**
3. "I was sixteen. Tesfa was seventeen. Beki was nineteen."
4. "Beki, the oldest, always jumped first."
5. "Then Tesfa. And me, last."
6. "Then it was splashing, and flips off the tree, and whatever tricks we could think of."
7. "And all of us shouting. Whoa, whoa, whoa."
8. "Nobody wanted to get out." **(added)**
9. "I would give a lot to hear that noise again." **(added)**

## Kaggle schedule (the agent writes the notebooks, Abeni presses run)

These are planning estimates to replace with measured numbers in
`COSTS.md`. Brief figure: about 30 GPU hours a week. This plan uses 3-5.

1. **Tonight, about 20 minutes:** a smoke-test notebook with GPU (T4) and
   internet on. It prints the GPU, checks free-disk and shows the remaining
   quota. Tells us early whether Wan 2.2 will fit.
2. **Tomorrow morning, session A (about 30 min):** ACE-Step, three
   instrumental candidates from the spotting note.
3. **Tomorrow morning, session B (about 1-2 hours, runs unattended):** Wan
   2.2 image-to-video, 480p, 9:16, for shots 1, 3, 6 and 8, saving each clip
   as it finishes so a timeout loses nothing.
4. **Session C, only if both brothers say yes to photo upload:** the
   likeness test above.
5. Any shot that fails three times falls back to Ken Burns, and the
   failure goes in `FAILURES.md`.

## Plan for the day

Tonight: schema, storyboard, narration, radio cut, send to the brothers.
Tomorrow morning: keyframes, Kaggle runs, music candidates. Afternoon:
assembly, second user test, docs. By early evening: report, public post,
walkthrough, submit with a margin before 23:59.

## What is left to the builder

Exact Cloudflare and Gemini model ids (confirmed by smoke test), the
JSON Schema field names, shot timing numbers, Kaggle notebook code, the
caption layout, and the make targets.

## ETHICS (record, filled in as it happens)

Consent, received in writing from each brother by chat, replying to a
message that said the film is AI-made, paints them, may use their photos as
private reference, and will be posted publicly with an AI label:

- Tesfa: "ofcourse you can use it we're brothers."
- Beki: "Okay you may use mine no problems I'm okay with it"

Neither reply names uploading photos to a third-party service, so the
option-2 experiment needs one more explicit yes from each.
