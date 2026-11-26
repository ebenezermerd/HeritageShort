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

## E14. Does the same seed give the same image on Cloudflare klein? (25 Nov)

**Hypothesis.** The brief says a fixed seed makes two runs comparable, and my cache key includes the
seed, so the same prompt and seed should give the same picture.

**Change.** The same prompt and seed 7, twice, at 512x512, plus seed 8 once.

**Result.** The two seed-7 files differed (different MD5), so klein through this API does not
reproduce an image from a seed. That is a correction to my own earlier work: the "same seed"
comparisons in E05 and E13 compared prompts under a different random start each time, so their
conclusions are looser than I wrote. The cache is still correct (it skips a call whose inputs have
not changed, and the saved file is the picture), but a seed cannot recreate a picture. The keyframe I
keep is the file in `outputs/`, not a seed.

## E15. Pick the cleanest of three candidates per shot (25 Nov)

**Hypothesis.** One image per shot hides klein's weak spots (extra limbs, pale skin, merged hands).
Three candidates per shot, judged by eye, should leave a clean one for every shot, which a single
generation did not.

**Change.** New stage `pipeline/candidates.py`: 3 candidates per shot at 9:16 (30 calls, mean 9.1 s).
Before generating I also tightened four prompts: "exactly two arms and two hands each" in the style
block; shot 6 now names Tesfa and "warm brown skin, bare chest"; shot 7 asks for "one single pair" of
cupped hands; shot 8 asks for the same warm brown skin on all three and arms down in the water.
I looked at all 30 and kept one per shot.

**Result.** The first-pass pictures had real faults: shot 7 showed two pairs of hands (four hands),
shot 6 showed a pale boy in a white shirt, and shot 8 gave the three boys different skin tones. In
the candidates, shot 7's first option still showed an extra hand, and several others had odd arms or hands
(I did not count them). I judged them on contact sheets at about 230x400 pixels and called each pick clean. That was
wrong: the author watched the rebuilt film and still saw four fingers, extra legs and bodies that did not
read as real. At that size extra fingers and a merged leg are invisible, so my review could not catch
them. Re-seeding removed the worst fault (shot 7's four hands) but did not fix anatomy, and it did
nothing for consistency: the brothers in shot 8 still look like three different people, and the spring
is a different place in every shot. The
catch from E14: because a seed cannot recreate an image, `candidates.pick` copies the chosen file
into place and records it in the manifest, and the storyboard seed names which candidate it was.
The 16:9 images were generated once each and I checked them by eye; I saw no extra limbs.

## E16. Remove the hum and add ambience and splashes (25 Nov)

**Hypothesis.** The author found the sound "irritating" and said they could hear nothing of the
place. The only music in the build was my synthesised 110 Hz pad, so removing it and adding water,
birds and splash effects from FFmpeg should fix both complaints.

**Change.** `pipeline/ambience.py` builds a pink-noise water bed, two bird chirp patterns and a
splash for each `sfx` cue in `storyboard.json` (shots 3 to 8, 8 cues). Without an ACE-Step score the
music bed is left out. The ambience is ducked under the narration like the score.

**Result.** Measured, not heard (I cannot listen): a splash cue lifts the level at its moment by more
than 3 dB over the bed (a test pins it), and the films stay 65.0 s. Loudness first landed at a
true peak of +0.1 dBFS after AAC encoding even though the WAV was at -1.5: the white-noise splashes
make the encoder overshoot by 1.6 dB. Setting loudnorm's ceiling to -3 dB gives -14.6 LUFS and
-1.5 dBFS in the final MP4 for both ratios. Whether it sounds better is for the author's ears; the
music will only be right once an ACE-Step track replaces the empty music bed.

## E17. Which score candidate? 

**Hypothesis.** One of the ACE-Step candidates sits under the narration without competing with it.

**Change.** Listened to 3 candidates (de99c94f-0606-6eed-34cc-0f7e23eb814d.flac, ea6fa79b-20f1-0be7-20f3-8163b7ca8330.flac, fa37f557-f519-478d-9755-c01daf18b8b0.flac) quietly under the narration.

**Result.** Chose de99c94f-0606-6eed-34cc-0f7e23eb814d.flac. Track 1 is steady and its instrumental feel and tempo match the pace of the pictures; it suits the narrative, sounds joyful and has a few surprising touches. (Abeni's choice after listening to all three; measured -15.2 LUFS, loudness range 3.2 LU, the steadiest of the three.)

## E18. Take the synthesised ambience back out (25 Nov)

**Hypothesis.** E16's pink-noise "water" and white-noise "splashes" would make the place feel real.

**Change.** None at first: the author listened to the preview with the chosen score (E17).

**Result.** Wrong. The author heard a "shh" between narration lines. That is the noise bed: the
ducking lowers it while the voice speaks and lets it rise again in every pause, so it comes and goes
like a hiss, and noise from FFmpeg does not sound like water. With a real ACE-Step score there is no
gap left to fill, so the score is now the only bed under the voice and the noise ambience is used only
when no score exists (a test pins this). The Gemini narration clips themselves are clean: their noise
floor measures -62 to -90 dB. Final mix: -14.0 LUFS, true peak -1.5 dBFS. Lesson: a sound I cannot hear
should not go into the film without the author hearing it first.

## E19. Reference images on Kaggle, and the stacked-panel problem (26 Nov)

**Hypothesis.** Giving klein the spring picture and the brothers sheet as references keeps the place
and the three brothers the same from shot to shot, which plain prompts did not (E15).

**Change.** Generated 2 references and 50 candidates with FLUX.2 klein 4B on a Kaggle T4 (3 per shot
at 9:16, 2 at 16:9), 98 s an image on average, 5,105 s of GPU time in all
(`outputs/kaggle_logs/notebook_log_keyframes.jsonl`). Looked at every candidate, then at the figures
cropped at full size: hands, feet, how many legs.

**Result.** The spring is now the same place in every shot: the same pool, log, red bank and leaning
trunk. No extra limbs in any candidate I picked. But every 9:16 candidate for s05, s08 and s10, and
two of three for s02, came back as two pictures stacked in one frame, one showing the place and one
the brothers lined up like the sheet. The same shots at 16:9 were single pictures, and no shot with
the spring as its only reference was ever split. So a tall frame plus a character sheet reads to the
model as "make a page with two panels". Fix: `refs_by_ratio` lets a shot use only the spring at 9:16
and keep both references at 16:9; the brothers' looks stay in the text prompt. Picked 17 of 20 frames,
then remade s05, s08 and s10 at 9:16 with the spring alone (9 images, 102 to 126 s each; a test pins
that the override changes only the one ratio, so the picked 16:9 frames were not regenerated). No
panels this time. s05 and s10 came out right. Every s08 candidate drew a fourth boy standing behind
the three heads, though, so the 9:16 s08 is a full-height slice of the picked 16:9 frame (which has
exactly three), scaled up 1.75 times (`crop_from_wide` in the storyboard, logged as a pick with its
source). It is softer than the others, but it shows the right number of brothers.

## E20. Ship without Wan (26 Nov)

**Question.** Is it worth running Wan 2.2 on the four planned moving shots (s01, s04, s07, s09) this
close to the deadline?

**What I knew.** The Wan notebook had never run. The same T4 needed four rounds of out-of-memory fixes
for a 4B image model (FAILURES #12), and Wan is a 5B video model that would have to run in float16, a
numeric path none of my runs had tried. Every Wan shot already had a working fallback: a slow camera
move over its painting, logged as `fallback`. The one Wan shot with a person in it (s04) is exactly
where moving a body tends to bring back the extra-limb problem the listeners and Abeni kept pointing at.

**Decision.** Built the complete film first with camera moves on every shot (63 s, -14.0 LUFS, no new
model calls, 54 s to build), then Abeni decided not to run Wan. The four shots stay as camera moves, and
`runs.jsonl` says so on each of them. The Wan bundle (`make kaggle-bundle`) and notebook `20_wan` are in
the repo, untested. What I lose: real motion in four shots. What I keep: a finished film that does not
depend on an untried GPU job, and pictures whose figures were all checked at full size.
