"""Thin wrappers over the hosted models: Gemini (text, speech) and Cloudflare FLUX."""
from __future__ import annotations

import base64
import io
import subprocess
import tempfile
import wave
from pathlib import Path

import requests

from pipeline.common import require_env

GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_TEXT_MODEL = "gemini-3.8-flash"
GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"
DEFAULT_VOICE = "Charon"
DEFAULT_STYLE = "calm, warm, unhurried"
FLUX_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
FLUX_KLEIN_4B = "@cf/black-forest-labs/flux-2-klein-4b"


LOCAL_VOICE = "Daniel"

# name -> (provider label for runs.jsonl, model, voice). "say" is a local placeholder that works
# when Gemini's 10-requests-a-day free quota is spent; builds made with it are named *.say-placeholder.mp4 and must not be submitted.
VOICES = {
    "gemini": ("gemini", GEMINI_TTS_MODEL, DEFAULT_VOICE),
    "say": ("macos", "say", LOCAL_VOICE),
}


def say_tts(text: str, style: str = "") -> bytes:
    """Placeholder narration from the macOS `say` command, as a 24 kHz mono WAV."""
    with tempfile.TemporaryDirectory() as d:
        aiff, wav = Path(d) / "line.aiff", Path(d) / "line.wav"
        subprocess.run(["say", "-v", LOCAL_VOICE, "-r", "165", "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "24000", "-ac", "1",
                        str(wav)], check=True)
        return wav.read_bytes()


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    """Wrap raw 16-bit mono PCM (what Gemini TTS returns) in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def tts_prompt(text: str, style: str) -> str:
    """The prompt sent to TTS. It is just the line: Gemini speaks or stretches any added
    instruction (experiment 1), so `style` is kept in the signature but not used."""
    return text


def decode_image_response(payload: dict) -> bytes:
    if not payload.get("success", True) or "result" not in payload:
        errors = payload.get("errors") or [{"message": str(payload)[:200]}]
        raise RuntimeError("; ".join(e.get("message", str(e)) for e in errors))
    return base64.b64decode(payload["result"]["image"])


def gemini_text(prompt: str, model: str = GEMINI_TEXT_MODEL) -> str:
    r = requests.post(
        f"{GEMINI}/{model}:generateContent",
        headers={"x-goog-api-key": require_env("GEMINI_API_KEY")},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def gemini_tts(
    text: str,
    style: str = DEFAULT_STYLE,
    voice: str = DEFAULT_VOICE,
    model: str = GEMINI_TTS_MODEL,
) -> bytes:
    """Return a WAV for `text`. A stock voice, never a clone."""
    r = requests.post(
        f"{GEMINI}/{model}:generateContent",
        headers={"x-goog-api-key": require_env("GEMINI_API_KEY")},
        json={
            "contents": [{"parts": [{"text": tts_prompt(text, style)}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            },
        },
        timeout=180,
    )
    r.raise_for_status()
    part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
    return pcm_to_wav(base64.b64decode(part["data"]))


def schnell_payload(prompt: str, seed: int) -> dict:
    """flux-1-schnell takes no seed on Cloudflare, so runs with it are not reproducible."""
    return {"prompt": prompt, "steps": 4}


def cloudflare_flux(prompt: str, seed: int, size: tuple[int, int], model: str = FLUX_SCHNELL) -> bytes:
    """Return image bytes from Cloudflare Workers AI. size is (width, height)."""
    account = require_env("CF_ACCOUNT_ID")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {require_env('CF_API_TOKEN')}"}
    if "klein" in model:
        fields = {"prompt": prompt, "width": str(size[0]), "height": str(size[1]), "seed": str(seed)}
        r = requests.post(url, headers=headers, files={k: (None, v) for k, v in fields.items()}, timeout=180)
    else:
        r = requests.post(url, headers=headers, json=schnell_payload(prompt, seed), timeout=180)
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    return decode_image_response(r.json())
