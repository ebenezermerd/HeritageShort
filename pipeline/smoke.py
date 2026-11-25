"""Call each provider once, log the latency, and record which model ids worked."""
from __future__ import annotations

import json
import time
from typing import Callable

from pipeline import common, providers

OUT = common.ROOT / "outputs" / "smoke"


def _timed(name: str, provider: str, model: str, fn: Callable[[], bytes | str], params: dict, models: dict, key: str, ext: str | None):
    start = time.time()
    try:
        result = fn()
        latency = time.time() - start
        if ext:
            (OUT / f"{name}.{ext}").write_bytes(result)  # type: ignore[arg-type]
        common.log_run("smoke", None, provider, model, params, None, common.input_hash(name, params), latency, "ok")
        models[key] = model
        print(f"ok    {name:<22} {latency:5.1f}s  {model}")
    except Exception as e:  # noqa: BLE001 - the point is to report any failure honestly
        latency = time.time() - start
        common.log_run("smoke", None, provider, model, params, None, common.input_hash(name, params), latency, "failed", error=str(e)[:300])
        print(f"FAIL  {name:<22} {latency:5.1f}s  {model}  {str(e)[:160]}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    models: dict[str, str] = {}
    _timed("gemini_text", "gemini", providers.GEMINI_TEXT_MODEL,
           lambda: common.with_retries(lambda: providers.gemini_text("Reply with the single word: ready").strip()), {}, models, "gemini_text", None)
    _timed("gemini_tts", "gemini", providers.GEMINI_TTS_MODEL,
           lambda: providers.gemini_tts("Arba Minch means forty springs."),
           {"voice": providers.DEFAULT_VOICE, "style": providers.DEFAULT_STYLE}, models, "gemini_tts", "wav")
    prompt = "a clear turquoise forest spring with a fallen log under the water, hand-painted look"
    _timed("flux_schnell", "cloudflare", providers.FLUX_SCHNELL,
           lambda: providers.cloudflare_flux(prompt, 1, (768, 1344), providers.FLUX_SCHNELL),
           {"steps": 4, "seed": 1}, models, "flux_schnell", "jpg")
    _timed("flux_klein_4b", "cloudflare", providers.FLUX_KLEIN_4B,
           lambda: providers.cloudflare_flux(prompt, 1, (768, 1344), providers.FLUX_KLEIN_4B),
           {"width": 768, "height": 1344, "seed": 1}, models, "flux_klein_4b", "png")
    (OUT / "models.json").write_text(json.dumps(models, indent=2))
    print("confirmed:", json.dumps(models))


if __name__ == "__main__":
    main()
