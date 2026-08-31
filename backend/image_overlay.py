"""PIL-based logo / text overlay for Social Studio post images.

Recomposites from the ORIGINAL image every time (non-destructive) so overlays
can be re-edited or removed."""
import io

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(size: int, bold: bool = True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def apply_overlay(base_bytes: bytes, logo_bytes: bytes = None,
                  logo_opts: dict = None, text_opts: dict = None) -> bytes:
    base = Image.open(io.BytesIO(base_bytes)).convert("RGBA")
    W, H = base.size
    lo = logo_opts or {}
    to = text_opts or {}

    if logo_bytes and lo.get("enabled"):
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        scale = _clamp(float(lo.get("scale", 0.18)), 0.03, 0.9)
        lw = max(1, int(W * scale))
        lh = max(1, int(logo.height * (lw / logo.width)))
        logo = logo.resize((lw, lh), Image.LANCZOS)
        opacity = _clamp(float(lo.get("opacity", 0.9)), 0.05, 1.0)
        if opacity < 1.0:
            alpha = logo.split()[3].point(lambda p: int(p * opacity))
            logo.putalpha(alpha)
        x = int((W - lw) * _clamp(float(lo.get("x", 0.95)), 0, 1))
        y = int((H - lh) * _clamp(float(lo.get("y", 0.95)), 0, 1))
        base.alpha_composite(logo, (x, y))

    if to.get("enabled") and (to.get("content") or "").strip():
        draw = ImageDraw.Draw(base)
        size = max(12, int(H * _clamp(float(to.get("size", 0.07)), 0.02, 0.2)))
        font = _font(size, bold=True)
        max_w = int(W * 0.9)
        lines = _wrap(draw, to["content"].strip(), font, max_w)
        line_h = int(size * 1.2)
        block_h = line_h * len(lines)
        pos = to.get("position", "bottom")
        if pos == "top":
            y0 = int(H * 0.06)
        elif pos == "center":
            y0 = (H - block_h) // 2
        else:
            y0 = H - block_h - int(H * 0.06)
        color = to.get("color", "#FFFFFF")
        stroke = max(2, size // 12)
        for i, ln in enumerate(lines):
            tw = draw.textlength(ln, font=font)
            x = (W - tw) // 2
            y = y0 + i * line_h
            draw.text((x, y), ln, font=font, fill=color,
                      stroke_width=stroke, stroke_fill="#000000")

    out = io.BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()
