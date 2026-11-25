import pytest
from PIL import Image

from pipeline import captions


def test_caption_wraps_to_at_most_two_lines_of_42_characters():
    lines = captions.wrap("We only ever needed one. I was sixteen, Tesfa was seventeen, Beki was nineteen.")
    assert len(lines) == 2
    assert all(len(line) <= 42 for line in lines)


def test_too_long_a_caption_is_an_error_not_a_third_line():
    with pytest.raises(ValueError, match="two lines"):
        captions.wrap("word " * 40)


def test_vertical_caption_sits_inside_the_safe_area(tmp_path):
    out = captions.render("Beki, the oldest, always jumped first.", (720, 1280), tmp_path / "c.png")
    img = Image.open(out)
    assert img.size == (720, 1280) and img.mode == "RGBA"
    box = img.getchannel("A").getbbox()
    assert box is not None
    assert box[3] <= 1280 * (1 - 0.15)  # text ends well above the bottom 15% where app buttons sit
    assert box[0] >= 720 * 0.05 and box[2] <= 720 * 0.95


def test_end_card_is_opaque_and_full_frame(tmp_path):
    out = captions.end_card("Made with AI. Painted from memory.", (1280, 720), tmp_path / "e.png")
    img = Image.open(out)
    assert img.size == (1280, 720)
    assert img.convert("RGBA").getchannel("A").getextrema() == (255, 255)
