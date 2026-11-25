# Report: Forty Springs

> Draft for Abenezer to read, correct and make his own. It is written from the repo's real logs and
> notes. Anything in [square brackets] has not happened yet and must be filled in or cut, not left as
> it is. The AI interview afterwards is about this work, so read every line and check it is true.

## 1. What I set out to make, and for whom

A 65 second painted short, "Forty Springs", about me and my two brothers, Tesfa and Beki, swimming at
a spring in Arba Minch when we were 16, 17 and 19. Arba Minch means "forty springs". It is for my two
brothers, on their phones, and I wanted them to laugh first and miss it second. The film is painted
and AI-made, narrated in English by a stock voice, with English subtitles, a score and a card at the
end that says it was made with AI. Behind it is a small pipeline in which `storyboard.json` drives
every stage and one command, `make film`, rebuilds both the vertical and horizontal versions.

## 2. What I learned from my audience

[Fill in after the two listener tests with Tesfa, Beki and Amani. Use their own words from
`DESIGN.md`: where they smiled, what confused them, what you changed because of it. Until then this
section has nothing true to say, and the brief grades exactly this.]

## 3. The hardest problem

Gemini's free text-to-speech allows 10 requests a day per model. I did not know that, and I spent
the whole allowance by early afternoon on two smoke tests, one nine-line narration pass, a prompt
experiment and my own retries. After that every call returned `429 RESOURCE_EXHAUSTED`. `runs.jsonl`
shows it plainly: 10 successful speech calls and 38 failed ones.

I checked the error body, then tried the four other Gemini speech models on my key. They are in the
model list but all returned 404, so there was no second voice to fall back on. What I did: kept the
pipeline moving with a clearly labelled local placeholder voice (macOS Daniel, logged as provider
`macos`), used it for the first listener test and the first full build, and planned the real Gemini
narration for after the daily reset. [Fill in: when the reset came, whether the Gemini narration ran,
and how it compares by ear with the placeholder.] The lesson is in `FAILURES.md` #4.

## 4. A suggested practice that helped, and one that did not

**Helped: log every call.** My instinct was to log errors only. Logging every call, with model,
parameters, seed and latency, is what let me count 10 successes against 38 failures, see that image
generation averaged 8.9 s, and fill in `COSTS.md` from data instead of guesses.

**Did not help (here): one narration file per line.** It makes a retake cheap in time, and it let me
change one line in the walkthrough. But with a limit of 10 requests a day, nine lines cost nine
requests, where one request for the whole script would have cost one. A per-line file was the right
idea for compute and the wrong one for this quota. I kept it because it makes the one-shot
regeneration demo possible, but it nearly cost me the film's voice.

**One I skipped:** the reference sheet before keyframes. I used text descriptions of each brother
instead and judged consistency by eye (E02). [If you did the likeness test, say whether a reference
image did better.]

## 5. Work beyond the floor

- **A measured look at loudness (E06 to E08).** The film came out at -15.5 LUFS instead of the -14
  I had set, with no error. I read loudnorm's own report, found it had fallen into a fallback mode
  because the loudness range was 17.2 LU, and fixed it with a limiter chosen from three measured
  settings. I could not reproduce it with a test, and I said so in the docs.
- **Two image models, compared (E05).** schnell could not make a 9:16 image at all.
- [Ken Burns against Wan 2.2 on the same shot, and the likeness test, if they get done.]

## 6. What I would build next

Reference sheets for the brothers, and a real likeness test with their written yes to the photos. One
narration request for the whole script, split by silence, so a daily limit of 10 is not a problem.
Wan clips in 16:9 too. And a script stage with Gemini text, once its 503s stop (FAILURES #3).
