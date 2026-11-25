# Experiments

One entry per thing I changed on purpose: hypothesis, change, result. Numbers
come from `runs.jsonl` or from files in `outputs/`. Where I only looked and did
not measure, it says so.

## E01. Does a style instruction in the TTS prompt shape the voice? (25 Nov)

**Hypothesis.** Telling Gemini TTS to speak "calm, warm, unhurried" changes how
the line sounds but not what is said or how long it takes.

**Change.** Same sentence, "Arba Minch means forty springs.", same voice
(Charon), three prompts: the plain line; "Say calmly: ..."; and my first
version, "Say this calm, warm, unhurried, like a quiet storyteller: ...".

**Result.** 2.48 s, 4.40 s and 9.22 s. The instruction made the audio longer,
not just different. On the 9.22 s clip `silencedetect` found speech until
4.65 s, a 1.78 s gap, then more speech to the end, which fits the instruction
being read out loud before the line. I have not listened to confirm that, so
treat it as likely, not proven. These three calls came from a throwaway script that did not write to `runs.jsonl`, so they are not in the log.

**Decision.** Send the plain line only (`providers.tts_prompt`). The narration
cache key now covers the exact prompt, so the old long audio could not be
reused by mistake. A test pins this.

## E02. Can text alone give teenage, brown-skinned brothers? (25 Nov)

**Hypothesis.** Describing the boys as "teenage" with short hair and swim shorts
is enough for FLUX.2 klein 4B to paint three teenage brothers.

**Change.** First contact sheet of all ten 9:16 keyframes, then a second
version of the character looks: a number for each age (19, 17, 16), "lanky"
for the oldest, and "warm brown skin" for all three.

**Result.** Version 1 painted boys of about eight to twelve with noticeably
light skin. Version 2 fixed the proportions and the skin tone in all six shots
that name a character. 14 of 20 images regenerated; the 6 images of shots
that had not changed (6, 7 and 9, both ratios) came from the cache with no
call. Side-by-side sheets are in `outputs/keyframes/` (git-ignored).

## E03. The submerged log (25 Nov)

**Hypothesis.** "A large fallen log lying under the water" will put the log
below the surface like in Abeni's photos of the spring.

**Change.** Reworded shot 1 to "submerged beneath the clear water and visible
through the surface".

**Result.** Partly. The log now sits in the water and is clearly the landmark,
but it is large, in the foreground, and still breaks the surface. Good enough
for the film; not what the photos show. Left as is.

## E04. Pale skin in the shots that name no character (25 Nov)

**Hypothesis.** The skin-tone fix in E02 only reaches shots that list characters,
so the flip (shot 6) and the hands (shot 7) will still come out pale.

**Change.** Added "warm brown skin" to those two prompts.

**Result.** Confirmed first, then fixed: both shots had come out pale after
E02, and regenerating them cost exactly 4 calls (2 shots x 2 ratios).
`runs.jsonl` shows 4 successful keyframe calls each for shots 6 and 7 and
only 2 for shot 9, which never changed.

## E05. FLUX.1 schnell against FLUX.2 klein 4B on the same shot (25 Nov)

**Hypothesis.** The older, faster schnell will be good enough for the keyframes, so klein is not needed.

**Change.** One prompt (shot 8, the three brothers shouting in the water), both models on Cloudflare,
asked for 768x1344.

**Result.** schnell ignored the size and returned 1024x1024 (it takes no width or height there), takes
no seed (FAILURES #2), and took 34.2 s against klein's 8.6 s (the two ran while another job was also
using the account, so treat the times as rough). Its faces were bigger and more cartoonish. klein gave
the watercolour look the rest of the film has, the right 9:16 frame, and a seed. klein stays the
keyframe model. Image: `outputs/experiments/e05_compare.png`.

## E06. One-pass against two-pass loudness normalisation (25 Nov)

**Hypothesis.** Two-pass `loudnorm` will land closer to the -14 LUFS target than one pass.

**Change.** Same mix (narration over the score), measured raw, then one-pass, then two-pass.

**Result.** Raw -21.8 LUFS. One-pass -16.3 LUFS. Two-pass -15.5 LUFS. Two-pass was 0.8 LU closer, but
both missed the target by 1.5 LU or more, so the hypothesis held only in direction.

## E07. How much does the ducking actually lower the score? (25 Nov)

**Hypothesis.** `sidechaincompress` at threshold 0.02, ratio 6, attack 300 ms, release 1500 ms (the
brief's starting values) will pull the score down clearly while the narrator speaks.

**Change.** Measured the mean level of the score alone during the first narration line, with the
sidechain off and on.

**Result.** -31.5 dB without ducking, -46.7 dB with it: a 15.2 dB drop. The starting values work as
they are, so I did not tune them. I judged the level by measurement, not by ear.

## E08. A limiter in front of loudnorm (25 Nov)

**Hypothesis.** `loudnorm` stalls below target because speech over a quiet bed has high peaks. A peak
limiter ahead of it should let it reach -14 LUFS.

**Change.** Before changing the code, I read loudnorm's own measurement of the real mix: input
loudness range 17.2 LU against a target of 11, and `normalization_type: dynamic`, so it had silently
dropped out of linear mode. I then tried `alimiter` at limit 0.5, 0.3 and 0.2 before the two-pass.

**Result.** 0.5 gave -15.5 LUFS, 0.3 gave -14.7, 0.2 gave -14.0, all with true peak -1.5 dBFS. I chose
0.3: the 0.2 setting reaches the target but flattens the speech more, and being 0.7 LU under is
harmless because platforms only turn loud files down. The final film measures -14.7 LUFS, true peak
-1.4 dBFS, in both ratios. I could not reproduce the stall with synthetic test audio (FAILURES #7),
so this one is backed by the measurements above, not by a failing test.

## E09. How stable are the three brothers across seeds? (25 Nov)

**Hypothesis.** Because each brother's look is written into the prompt, changing only the seed will
change the composition but keep the three of them recognisably the same people.

**Change.** Shot 8 (the three in the water), same prompt, four seeds: 108 (the one in the film), 208,
308, 408. About 9 to 10 s each.

**Result.** Half true. The composition changes completely every time. The oldest brother (tall, curly
hair) is recognisable in all four. The two younger ones are not: their faces, their shorts (grey, blue,
navy, green) and their apparent age change from seed to seed, and they still read as about 10 to 13
even though the prompt says 16 and 17. So text alone holds one character well and two badly. That is
the reason to test reference images (the likeness test, which needs both brothers' written photo
consent first). Image: `outputs/experiments/e09_seeds.png`.

## E10. How low should the ducking threshold be? (25 Nov)

**Hypothesis.** The brief's starting threshold of 0.02 is about right, and a lower or higher value
will make the music either vanish or barely move.

**Change.** Same score pad and same narration line, `sidechaincompress` ratio 6, attack 300 ms,
release 1500 ms, threshold swept over 0.01, 0.02, 0.05 and 0.1. Measured the mean level of the music
alone during the first spoken line (E07's method).

**Result.** The score dropped 20.2 dB at 0.01, 15.2 dB at 0.02, 8.6 dB at 0.05 and only 3.6 dB at 0.1
(against -31.5 dB with no ducking). 0.02 keeps the music clearly audible between lines and clearly out
of the way during them, so I kept it. 0.01 would make the score almost disappear under the voice.
I judged by measured level, not by ear, and this narration is the placeholder voice.

## E11. Does the placeholder voice's speaking rate change the film? (25 Nov)

**Hypothesis.** The three speaking rates 140, 165 and 190 words per minute will change total
narration time by only a few seconds, so the 65 s timeline does not depend on the rate.

**Change.** Rendered all nine real lines (64 words) with macOS `say` at each rate and summed the
durations.

**Result.** 27.1 s at 140, 24.7 s at 165 (what the pipeline uses) and 22.9 s at 190, which is 2.4,
2.6 and 2.8 words a second. Total narration moves by about 4 s across the whole range, so the
timeline holds either way, because most of the 65 s is picture. It also matches the brief's guide of
2 to 2.5 words a second. It does mean the film has long stretches without speech, which is the thing
to ask the listeners about.

## E12. Does a lower resolution make keyframes faster on Cloudflare? (25 Nov)

**Hypothesis.** The brief advises drafting at low resolution to save time, so a 512x896 image should
come back clearly faster than a 1024x1792 one.

**Change.** Same prompt and seed (shot 3) at 512x896, 768x1344 and 1024x1792.

**Result.** 8.9 s, 8.4 s and 9.7 s, and every size came back exactly as asked. Resolution made almost no
difference, so the advice does not apply to this hosted API: its time is mostly fixed overhead. It
is advice for GPU video time. For keyframes I use the larger size. Single run each, so differences of
about a second are noise.

## E13. What does the style block actually do? (25 Nov)

**Hypothesis.** The shared style block ("warm hand-painted look, soft paper grain...") is what makes
the film painted, and without it klein would draw something less consistent but still illustrated.

**Change.** Shot 3 with the full prompt, and the same prompt with the style block removed, same seed.

**Result.** Wrong guess about what "less consistent" would look like. Without the style block the
model produced a near-photographic image of a young man jumping into a turquoise pool, with a very
different look from every other shot. The style block is what makes the film painted and consistent,
and it also keeps the brothers from being rendered as photoreal people, which fits what I decided in
`ETHICS.md`. Image: `outputs/experiments/e13_compare.png`.
