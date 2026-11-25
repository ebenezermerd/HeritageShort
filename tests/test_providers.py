import base64
import io
import shutil
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


@pytest.mark.skipif(shutil.which("say") is None, reason="needs macOS say")
def test_say_tts_returns_a_playable_wav():
    wav = providers.say_tts("Arba Minch means forty springs.", "ignored")
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getnframes() / w.getframerate() > 1.0


def test_voices_table_names_gemini_and_the_local_placeholder():
    assert providers.VOICES["gemini"] == ("gemini", providers.GEMINI_TTS_MODEL, providers.DEFAULT_VOICE)
    assert providers.VOICES["say"][0] == "macos"


def test_schnell_payload_never_sends_a_seed():
    # Cloudflare rejects "seed" for flux-1-schnell (found in the first smoke run).
    payload = providers.schnell_payload("a spring", seed=7)
    assert "seed" not in payload
    assert payload["prompt"] == "a spring"


def test_tts_prompt_is_the_plain_line_with_no_spoken_instruction():
    # Experiment 1: any instruction text added to the prompt was spoken or slowed the read
    # (2.5 s plain vs 9.2 s with a style sentence for the same line).
    p = providers.tts_prompt("Arba Minch means forty springs.", "calm, warm, unhurried")
    assert p == "Arba Minch means forty springs."


def _gemini_style_wav(frames: bytes) -> bytes:
    """What Gemini TTS returns now: a full WAV, with a provenance chunk after the audio."""
    wav = providers.pcm_to_wav(frames)
    meta = b"C2PA provenance: Google Media Processing Services trainedAlgorithmicMedia" * 20
    chunk = b"c2pa" + len(meta).to_bytes(4, "little") + meta
    body = wav[12:] + chunk
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WAVE" + body


def test_tts_bytes_that_are_already_a_wav_are_kept_as_they_are():
    # FAILURES #11: wrapping Gemini's own WAV in a second header made its provenance block play
    # as a burst of noise ("ksh") at the end of every line.
    frames = b"\x01\x00" * 2400
    data = _gemini_style_wav(frames)
    out = providers.as_wav(data)
    assert out == data
    import io as _io
    import wave as _wave
    with _wave.open(_io.BytesIO(out)) as w:
        assert w.readframes(w.getnframes()) == frames


def test_raw_pcm_is_still_wrapped():
    out = providers.as_wav(b"\x00\x00" * 100)
    assert out[:4] == b"RIFF" and len(out) == 44 + 200


def test_double_wrapped_clip_is_repaired_to_the_inner_wav():
    inner = _gemini_style_wav(b"\x02\x00" * 2400)
    assert providers.unwrap_double_wav(providers.pcm_to_wav(inner)) == inner
    assert providers.unwrap_double_wav(inner) is None
