"""PIL-based logo + crisp text overlay for Social post images.

Text is rendered by us (not the AI) so typography is always sharp — a headline
and/or subline in any position, auto-wrapped to fit width, with a strong outline.
Recomposites from the ORIGINAL image every time (non-destructive)."""
import io

from PIL import Image, ImageDraw, ImageFont, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(size, bold=True):
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


def _draw_text_block(base, W, H, opts):
    content = (opts.get("content") or "").strip()
    if not content:
        return
    if opts.get("uppercase"):
        content = content.upper()
    draw = ImageDraw.Draw(base)
    # auto-fit: shrink font until the widest word fits, wrapping to lines
    size = max(14, int(H * _clamp(float(opts.get("size", 0.08)), 0.02, 0.22)))
    max_w = int(W * 0.9)
    for _ in range(24):
        font = _font(size, bold=True)
        widest = max((draw.textlength(w, font=font) for w in content.split()), default=0)
        if widest <= max_w or size <= 16:
            break
        size -= 3
    font = _font(size, bold=True)
    lines = _wrap(draw, content, font, max_w)
    line_h = int(size * 1.12)
    block_h = line_h * len(lines)
    pos = opts.get("position", "top")
    if pos == "top":
        y0 = int(H * 0.05)
    elif pos == "center":
        y0 = (H - block_h) // 2
    else:
        y0 = H - block_h - int(H * 0.05)
    color = opts.get("color", "#FFFFFF")
    stroke = max(2, size // 10)
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=font)
        x = (W - tw) // 2
        y = y0 + i * line_h
        draw.text((x, y), ln, font=font, fill=color, stroke_width=stroke, stroke_fill="#000000")


def apply_overlay(base_bytes, logo_bytes=None, logo_opts=None, text_opts=None, texts=None):
    base = Image.open(io.BytesIO(base_bytes)).convert("RGBA")
    W, H = base.size
    lo = logo_opts or {}

    if logo_bytes and lo.get("enabled"):
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        scale = _clamp(float(lo.get("scale", 0.18)), 0.03, 0.9)
        lw = max(1, int(W * scale))
        lh = max(1, int(logo.height * (lw / logo.width)))
        logo = logo.resize((lw, lh), Image.LANCZOS)
        opacity = _clamp(float(lo.get("opacity", 0.95)), 0.05, 1.0)
        if opacity < 1.0:
            alpha = logo.split()[3].point(lambda p: int(p * opacity))
            logo.putalpha(alpha)
        x = int((W - lw) * _clamp(float(lo.get("x", 0.95)), 0, 1))
        y = int((H - lh) * _clamp(float(lo.get("y", 0.95)), 0, 1))
        base.alpha_composite(logo, (x, y))

    layers = list(texts) if texts else ([text_opts] if text_opts else [])
    for layer in layers:
        if layer and layer.get("enabled", True):
            _draw_text_block(base, W, H, layer)

    out = io.BytesIO()
    base.convert("RGB").save(out, format="PNG")
    return out.getvalue()
