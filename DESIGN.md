# Design

## Who it is for and what it should do

**Audience.** Tesfa and Beki, Abeni's two brothers, watching on a phone. Anyone
else who sees it is a bonus.

**Intent.** The three of them swam at a spring in Arba Minch when they were
16, 17 and 19. The film hands that afternoon back to them. At the end they
should feel "we really were that happy, and I want to go back". Laughing first,
longing second, never sad.

**Where they watch.** On a phone, so vertical 9:16 is the main version and
16:9 is the second.

## What Abeni remembered (his words, my notes)

Beki, the oldest, jumped first, then Tesfa, then Abeni last. They splashed each
other, did flips and tricks from the tree beside the water, and shouted "Whoa,
whoa, whoa" a lot. They were just having fun. Abeni said not to over-specify
the memory, so the film stays close to that and nothing more.

## Every shot and why it is there

The reason for each shot is in `storyboard.json` next to its prompt, so the
planner, the grader and the interview all read the same sentence.

## User test 1: the radio cut

**Run on 25-26 Nov, over WhatsApp.** The cut was `outputs/radio_cut.mp4`, 62 s: the real Gemini
narration on the film's real timing over the chosen ACE-Step score (E17), on a black screen. Each
listener got the clip and four questions (where did you smile, was any line confusing, what did you feel
at the end, was it too slow or too fast anywhere) and wrote back. Their answers are quoted as they wrote
them, including the spelling.

**Beki (19, the oldest brother)**
> Come on lol i smilled when i hear I used to jump first evertime that was cool back then, knowing that the water is cold and even i am shaking i will always take the first jump to cross over my fear and enjoy the moment, my name is funny in english too
>
> hearing my name in english specially nickname was that funny and no line i found confusing
>
> it remind me what a childhood memory we had and how aged we have now that we couldn't get to gether to loss our minds into madness that we have done back then
>
> well it was cool the background music the storytelling i is kind of fun and refreshing and the narrtion sounds itself funny and refreshing with good flow

**Tesfa (17, the middle brother)**
> I smiled the way you generated our laughing it was too harsh that it sounds serious guy laughing , like what the heck did we laugh like that, it was that funny hearing the narrator laughing trying to immitate us
>
> well i am not always the second to jump you yourself sometimes do the staff but it is cool that everline hits the momory we had
>
> I felt what a funny way way to hear a story through english instead of our native lanaguage but kind of wondered me what a cool thing back then we did , i flashed a huge memory for me that i was in love of the stunts i used to do jumptng from fallen tree to the water and many of the best things back then
>
> well i speak faster and hit the memory flash fast but the story telling while it is good but it seems slow to me

**Amani (Abeni's friend, never went to the spring)**
> the story telling made it look like funny to call amharic names through english so it made me funny and the way the narror laughs sounds so much refreshing wow wow wooooh
>
> i don't hear any confusion being made
>
> it made me realize this might be the memory i would like to have cause it is so interesting that made me visit arbaminch some time
>
> it got me thinking i woule like to see the video if this sound has one cause everythign made it ask one thing what the memory look like what the spring look like so i like hwo it is narrated and the speed it followed.

**What I take from it.** All three smiled, nobody found a line confusing, and the ending landed as
intended: Beki thought about how they have grown apart, Tesfa got "a huge memory" back. Hearing Amharic
nicknames in an English voice was funny to all three, which suits a laughing film, so the names stay.
Two notes disagree with each other: the shouted "whoa" was "too harsh… serious guy laughing" for Tesfa
and "so much refreshing" for Amani, and the pace was "slow" for Tesfa but liked by Beki ("good flow")
and Amani. Two notes are corrections of fact, and those I take without argument: Tesfa was not always
second, and his favourite stunt was off the fallen tree.

| Listener | What they said, in short | What changed in `storyboard.json` |
|---|---|---|
| Beki | Smiled at "jumped first"; did it every time, cold and shaking, to beat his fear | s03 line now carries his detail: "Beki, the oldest, always jumped first, even when the water was cold." |
| Tesfa | "I am not always the second to jump" | s04 line: "Then Tesfa. Most days." |
| Tesfa | Loved "jumping from fallen tree to the water" | s06 line: "flips off the fallen tree"; s06 picture: a flip off the fallen trunk |
| Tesfa, Amani | The "whoa" is harsh (Tesfa) / refreshing (Amani) | s08 retaken once with a lighter, exclaimed "Whoa! Whoa! Whoa!"; Abeni chooses between the takes |
| Tesfa | "seems slow" (Beki and Amani disagreed) | The two silent holds trimmed by 1 s each (s01 7 to 6 s, s10 6 to 5 s); the film stays above 60 s |
| Amani | Wants to see what the spring looks like | No change to the story; it confirms the work on one consistent spring picture (E19 onward) |

## User test 2: the near-final cut

Not run yet. Same listeners, near-final film, notes go here.
