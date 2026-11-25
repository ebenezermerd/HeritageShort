import base64
import io
import wave

import pytest

from pipeline import providers


def test_pcm_to_wav_has_correct_duration():
    pcm = b"\x00\x00" * 24000  # one second of 24 kHz mono 16-bit silence
    wav = providers.pcm_to_wav(pcm, rate=24000)
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 24000
        assert w.getnframes() / w.getframerate() == pytest.approx(1.0)


def test_decode_image_response_reads_base64_result():
    payload = {"result": {"image": base64.b64encode(b"PNGBYTES").decode()}, "success": True}
    assert providers.decode_image_response(payload) == b"PNGBYTES"


def test_decode_image_response_raises_with_api_error_text():
    payload = {"success": False, "errors": [{"message": "quota exceeded"}]}
    with pytest.raises(RuntimeError, match="quota exceeded"):
        providers.decode_image_response(payload)


def test_schnell_payload_never_sends_a_seed():
    # Cloudflare rejects "seed" for flux-1-schnell (found in the first smoke run).
    payload = providers.schnell_payload("a spring", seed=7)
    assert "seed" not in payload
    assert payload["prompt"] == "a spring"


def test_tts_prompt_carries_style_and_text():
    p = providers.tts_prompt("Arba Minch means forty springs.", "calm, warm, unhurried")
    assert "calm, warm, unhurried" in p
    assert "Arba Minch means forty springs." in p
