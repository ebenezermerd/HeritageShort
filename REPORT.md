# Report: Forty Springs

> Draft for Abenezer to read, correct and make his own. It is written from the repo's real logs and
> notes. Anything in [square brackets] has not happened yet and must be filled in or cut, not left as
> it is. The AI interview afterwards is about this work, so read every line and check it is true.

## 1. What I set out to make, and for whom

A 63 second painted short, "Forty Springs", about me and my two brothers, Tesfa and Beki, swimming at
a spring in Arba Minch when we were 16, 17 and 19. Arba Minch means "forty springs". It is for my two
brothers, on their phones, and I wanted them to laugh first and miss it second. The film is painted
and AI-made, narrated in English by a stock voice, with English subtitles, a score and a card at the
end that says it was made with AI. Behind it is a small pipeline in which `storyboard.json` drives
every stage and one command, `make film`, rebuilds both the vertical and horizontal versions.

## 2. What I learned from my audience

I played a radio cut (the real narration and score on a black screen, 62 s) to Beki, Tesfa and my friend
Amani, who has never been to the spring, and asked four questions over WhatsApp. Their answers are
copied word for word in `DESIGN.md`. All three smiled and nobody found a line confusing. Hearing our
Amharic nicknames in an English voice made all three laugh, so the names stayed. Beki smiled at
jumping first and told me why: he did it every time, "even i am shaking", to beat his fear. That is
now in his line. Tesfa corrected me twice: he was "not always the second to jump", so his line became
"Then Tesfa. Most days.", and his favourite stunt was jumping off the fallen tree, which is now both the
s06 line and the s06 picture. He also found the shouted "whoa" "too harsh" and the pace "slow"; Amani
found the same "whoa" "so much refreshing", and Beki and Amani liked the pace. I took a lighter second
take of the "whoa" and trimmed the two silent shots by a second each, and left the rest. Amani's last
answer was that they wanted to see what the spring looks like, which is what the picture work was for.
[Add test 2 here if the brothers watch the finished film before you submit.]

## 3. The hardest problem

Making the people look right. The first full set of pictures had a boy with four hands, legs that did
not match, bodies that looked lifeless, and a spring that changed from shot to shot. The first check was
at thumbnail size and missed it; I saw it when I looked at full size (FAILURES #8). Three things fixed it, and each
one broke something new. First, I stopped asking the model to draw hands and legs it could not hold
together: most shots now show the brothers from behind, far away, or with only heads above the water.
Second, I gave the model two reference pictures, one of the spring and one of the three brothers, so
every shot is the same place and the same three people (E19). Cloudflare's daily image quota then
stopped resetting, so I moved generation to a free Kaggle T4, where it ran out of memory four times
before it worked: at the decoder, in attention, in how the model was split across two GPUs, and in the
end because this GPU has no fast attention kernel for bfloat16, fixed by shrinking the reference
pictures to 320 px (FAILURES #12). Third, the tall phone frames given both references came back as two
pictures stacked in one frame, so those shots now use only the spring at 9:16, and the one shot that
still drew a fourth boy uses a slice of its correct 16:9 picture instead. Every figure in the final 20
frames was checked cropped at full size.

The voice was the other hard part. Gemini's free speech allows 10 requests a day, and I spent them by
early afternoon on 25 Nov (FAILURES #4). The full Gemini narration ran that evening with a second key
of my own, and the rewritten lines the next morning. Then every line ended in a "ksh" noise: Gemini had
started returning a complete WAV file, and the pipeline wrapped it in a second WAV header, so the file's
provenance data played as sound (FAILURES #11). The fix unwraps the old files without new requests.

## 4. A suggested practice that helped, and one that did not

**Helped: log every call.** My instinct was to log errors only. Logging every call, with model,
parameters, seed and latency, is what let me count successes against failures, see that a Kaggle image
took 99 s against 9 s on Cloudflare, and fill in `COSTS.md` from data instead of guesses.

**Did not help (here): one narration file per line.** It makes a retake cheap in time, and it let me
change four lines after the listener test without touching the rest. But with a limit of 10 requests a
day, nine lines cost nine requests, where one request for the whole script would have cost one. I kept
it because it makes the one shot regeneration demo possible, but it nearly cost me the film's voice.

**Helped in the end: the reference sheet.** I skipped it at first and used text descriptions of each
brother (E02). That is what gave me inconsistent people. Adding reference pictures of the spring and the
brothers is what made the shots look like one place and one family (E19).

## 5. Work beyond the floor

- **A measured look at loudness (E06 to E08).** The film came out at -15.5 LUFS instead of the -14
  I had set, with no error. I read loudnorm's own report, found it had fallen into a fallback mode
  because the loudness range was 17.2 LU, and fixed it with a limiter chosen from three measured
  settings. The final film measures -14.0 LUFS in both ratios.
- **Two image models, compared (E05).** schnell could not make a 9:16 image at all.
- **A second image route.** When Cloudflare's quota stopped resetting, the same model ran on Kaggle
  from the same job list, and its pictures came back into the same cache, so `make film` still makes
  no new image calls.
- **A recorded listener test that changed the film (DESIGN.md).** Four storyboard changes came straight
  from what my brothers and Amani wrote.

## 6. What I would build next

Wan 2.2 on the three scenery shots, which I planned but did not run (E20): the notebook is written but
untested, and I chose a finished film over an untried GPU job on the last day. One narration request for
the whole script, split by silence, so a daily limit of 10 is not a problem. A likeness test with my
brothers' written yes to their photos. And a script stage with Gemini text, once its 503s stop
(FAILURES #3).
