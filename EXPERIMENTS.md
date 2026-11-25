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
treat it as likely, not proven.

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
