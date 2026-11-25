# Walkthrough plan (5 minutes at most)

Record your screen and talk in your own words. This is an outline, not a script. The one thing
the grader needs to see on screen is a single change in `storyboard.json` followed by a rerun in
which only that shot's work happens.

**0:00 to 0:30. The film.** Play 15 seconds of the vertical film. Say who it is for and one sentence
on why you made it.

**0:30 to 1:45. The architecture.** Show the folder. Open `storyboard.json` and point at one shot: its
reason, its prompt, its seed. Say "this one file is the contract". Show `schema/` and run
`make validate`. Then walk the six stages in `README.md`. Mention that the hash cache is why a rerun
only does what changed.

**1:45 to 2:45. One hard decision.** Pick one and say what you chose and what it cost you:
- the Gemini 10-requests-a-day quota and the local placeholder voice (`FAILURES.md` #4), or
- no `libass` in FFmpeg, so captions are drawn with Pillow (`FAILURES.md` #1), or
- the loudness limiter chosen from measurements (`EXPERIMENTS.md` E08).

**2:45 to 4:15. Change one shot, live.**
1. Open `runs.jsonl` and note how many lines it has: `wc -l runs.jsonl`.
2. In `storyboard.json` change one narration line, for example shot `s04` from "Then Tesfa." to
   "Then Tesfa, right after him."
3. Run `make film` (use `VOICE=say` if the Gemini quota is spent).
4. Show the output: only narration for that shot ran, no keyframes, and both ratios were
   reassembled. Run `tail -4 runs.jsonl` to show the new lines. It is fine to pause the recording
   while it builds (about a minute).

**4:15 to 5:00. Close.** One thing that broke, one thing you learned, and what is next.

## Before recording

- Run `make film` once so everything is cached and the live change is the only new work.
- Check the Gemini quota. If it is spent, use `VOICE=say` and say why on camera.
- Do not show `.env`.
