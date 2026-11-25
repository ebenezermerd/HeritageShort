# Ethics, consent and licences

## Consent

The film shows three real people: Abenezer (Abeni, the author), Tesahun (Tesfa)
and Bereket (Beki), his brothers. They are shown as painted, AI-made teenage
versions of themselves. Nobody's voice is cloned: the narration is a stock
voice.

Abeni asked both brothers by chat, in a message saying the film is AI-made,
paints them, might use their photos as a reference, and will be posted publicly
with an AI label. Their replies, copied word for word:

- **Tesfa:** "ofcourse you can use it we're brothers."
- **Beki:** "Okay you may use mine no problems I'm okay with it"

Abeni then asked each of them again about uploading their photos to a private
Kaggle dataset to help the model match their faces, and told me both said yes.
**I only have Abeni's word for that second yes.** Their exact messages still need
to be pasted here. Until they are, no photo of a person is uploaded anywhere and
every keyframe comes from a text description only.

Abeni is the author and consents for himself.

## What leaves this computer

- Text prompts go to Google (Gemini speech) and Cloudflare (FLUX). Free tiers may
  use inputs to improve their models, so no private family detail is in a prompt.
  Prompts contain only the first names, ages, a general look and the scene.
- The three spring photos and eleven portraits in `refs/` are git-ignored and have
  not been uploaded anywhere.

## Licences (checked when each model was chosen)

| Model | Used for | Licence |
|---|---|---|
| FLUX.2 klein 4B (Cloudflare Workers AI) | keyframes | Apache 2.0 (open weights); Cloudflare's service terms apply |
| FLUX.1 schnell (Cloudflare Workers AI) | comparison only | Apache 2.0 |
| Gemini 3.8 Flash TTS | final narration | Google Gemini API terms (free tier) |
| macOS `say` (voice Daniel) | placeholder narration only; it must not be used in the submitted film, and any build with it is named `*.say-placeholder.mp4` | Apple system voice, local |
| Wan 2.2 TI2V-5B | moving shots | Apache 2.0 |
| ACE-Step 1.5 | score | MIT; outputs usable commercially |
| FFmpeg | assembly | LGPL/GPL build as installed |

## Labelling

- The film ends with a 3 second card: "Made with AI. Painted from memory."
- When posted, the platform's AI-content label is switched on.
- Provenance marks such as SynthID are left in place.
