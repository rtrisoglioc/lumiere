"""Unified FFmpeg transform pipeline for the pro editor (Phase a).

Applies, in ONE encode pass: speed change, reframe to a target aspect
(16:9 / 9:16 / 1:1, center-crop cover), a color look, and an optional PNG logo
overlay (position as fractions of the frame so it auto-recomputes on reframe).
Outputs a faststart mp4 (moov at front) so browsers play without needing Range."""
import subprocess
import tempfile
from pathlib import Path

ASPECT_DIMS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}

COLOR = {
    "none": None,
    "cinematic": "eq=contrast=1.10:saturation=1.20:gamma=0.96,curves=preset=increase_contrast",
    "warm": "eq=saturation=1.12:gamma_r=1.06:gamma_b=0.94",
    "cool": "eq=saturation=1.08:gamma_b=1.06:gamma_r=0.95",
    "bw": "hue=s=0,eq=contrast=1.08",
    "vivid": "eq=saturation=1.4:contrast=1.08",
}


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def transform_video(src: str, out: str, opts: dict, logo_path: str = None):
    aspect = opts.get("aspect", "16:9")
    W, H = ASPECT_DIMS.get(aspect, ASPECT_DIMS["16:9"])
    speed = float(opts.get("speed", 1.0) or 1.0)
    speed = min(4.0, max(0.25, speed))
    color = COLOR.get(opts.get("filter", "none"))
    logo = opts.get("logo") or {}
    use_logo = bool(logo.get("enabled")) and logo_path and Path(logo_path).exists()

    vchain = []
    if speed != 1.0:
        vchain.append(f"setpts={1.0/speed:.6f}*PTS")
    vchain.append(f"scale={W}:{H}:force_original_aspect_ratio=increase")
    vchain.append(f"crop={W}:{H}")
    if color:
        vchain.append(color)

    inputs = ["-i", src]
    if use_logo:
        inputs += ["-i", logo_path]

    if use_logo:
        lw = min(0.9, max(0.03, float(logo.get("scale", 0.18))))
        op = min(1.0, max(0.05, float(logo.get("opacity", 0.85))))
        xf = min(1.0, max(0.0, float(logo.get("x", 0.95))))
        yf = min(1.0, max(0.0, float(logo.get("y", 0.95))))
        filter_complex = (
            f"[0:v]{','.join(vchain)}[base];"
            f"[1:v]scale=iw*{lw:.4f}:-1,format=rgba,colorchannelmixer=aa={op:.3f}[lg];"
            f"[base][lg]overlay=x=(W-w)*{xf:.4f}:y=(H-h)*{yf:.4f}[v]"
        )
    else:
        filter_complex = f"[0:v]{','.join(vchain)}[v]"

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[v]"]
    # Audio: keep it, applying tempo when speed changed (optional stream).
    if speed != 1.0:
        atempo = _atempo_chain(speed)
        cmd += ["-filter:a", atempo, "-map", "0:a?", "-c:a", "aac"]
    else:
        cmd += ["-map", "0:a?", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out]
    r = _run(cmd)
    if r.returncode != 0 or not Path(out).exists():
        raise RuntimeError(f"ffmpeg_edit_failed: {r.stderr[-400:]}")
    return out


def _atempo_chain(speed):
    """atempo supports 0.5..2.0; chain for out-of-range speeds."""
    factors, s = [], speed
    while s > 2.0:
        factors.append(2.0); s /= 2.0
    while s < 0.5:
        factors.append(0.5); s /= 0.5
    factors.append(round(s, 4))
    return ",".join(f"atempo={f}" for f in factors)
