"""Subtitles and the end card, drawn with Pillow. This FFmpeg has no libass or drawtext (FAILURES #1)."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MAX_LINES = 2
LINE_CHARS = 40


def wrap(text: str) -> list[str]:
    """At most two lines of about 40 characters. Longer text is an error, not a third line."""
    lines = textwrap.wrap(text, width=LINE_CHARS)
    if len(lines) > MAX_LINES:
        raise ValueError(f"caption needs more than two lines: {text!r}")
    return lines


def _font_fitting(lines: list[str], max_width: float, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 12:
        font = ImageFont.load_default(size=size)  # Pillow's bundled scalable font, no file to ship
        if max(font.getlength(line) for line in lines) <= max_width:
            return font
        size -= 2
    return ImageFont.load_default(size=12)


def render(text: str, size: tuple[int, int], out: Path) -> Path:
    """A full-frame transparent PNG with the caption inside the safe area."""
    w, h = size
    lines = wrap(text)
    font = _font_fitting(lines, w * 0.88, max(24, w // 15))
    margin = 0.18 if h > w else 0.08  # keep clear of the app buttons at the bottom of a phone screen
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    line_h = font.size * 1.25
    y = h * (1 - margin) - line_h * len(lines)
    for line in lines:
        x = (w - font.getlength(line)) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
        y += line_h
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def end_card(text: str, size: tuple[int, int], out: Path) -> Path:
    """Opaque full-frame card, one sentence per line."""
    w, h = size
    lines = [s.strip() + ("." if not s.strip().endswith(".") else "") for s in text.split(". ") if s.strip()]
    font = _font_fitting(lines, w * 0.8, max(28, w // 12))
    img = Image.new("RGB", size, (24, 32, 28))
    draw = ImageDraw.Draw(img)
    line_h = font.size * 1.4
    y = (h - line_h * len(lines)) / 2
    for line in lines:
        draw.text(((w - font.getlength(line)) / 2, y), line, font=font, fill=(240, 232, 214))
        y += line_h
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
