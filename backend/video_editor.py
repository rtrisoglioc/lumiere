"""Unified FFmpeg transform pipeline for the pro editor.

Applies, in ONE encode pass: speed change, reframe to a target aspect
(16:9 / 9:16 / 1:1, center-crop cover), a color look, whole-clip transitions,
optional PNG logo overlay, optional music bed, and optional burned-in
CapCut-style captions (via a pre-generated ASS file).
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
    "film": "curves=preset=increase_contrast,colorbalance=rs=-0.06:gs=-0.02:bs=0.08:rm=0.04:bm=-0.04,eq=saturation=1.05",
    "noir": "hue=s=0,eq=contrast=1.28:brightness=-0.02,curves=preset=increase_contrast",
    "vintage": "curves=preset=vintage,eq=saturation=0.88:gamma=1.03",
    "teal_orange": "colorbalance=rs=0.05:bs=0.05:gm=-0.03:bm=-0.05,eq=saturation=1.15:contrast=1.08",
}

TRANSITIONS = {"fade": 0.5, "dissolve": 1.0, "smooth": 0.8, "fadeblack": 0.7, "fadewhite": 0.7}


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    except FileNotFoundError as e:
        class _F:
            returncode = 127; stderr = f"binary_not_found: {e}"; stdout = ""
        return _F()


def _duration(src):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", src],
                           capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def transform_video(src: str, out: str, opts: dict, logo_path: str = None,
                    music_path: str = None, subtitle_path: str = None):
    aspect = opts.get("aspect", "16:9")
    W, H = ASPECT_DIMS.get(aspect, ASPECT_DIMS["16:9"])
    speed = float(opts.get("speed", 1.0) or 1.0)
    speed = min(4.0, max(0.25, speed))
    color = COLOR.get(opts.get("filter", "none"))
    transition = opts.get("transition", "none")
    tdur = float(opts.get("transition_dur") or 0) or None
    music_vol = float(opts.get("music_volume", 0.85) or 0.85)
    text_ov = opts.get("text_overlay") or {}
    logo = opts.get("logo") or {}
    use_logo = bool(logo.get("enabled")) and logo_path and Path(logo_path).exists()
    use_music = bool(music_path) and Path(music_path).exists()
    use_subs = bool(subtitle_path) and Path(subtitle_path).exists()

    vchain = []
    if speed != 1.0:
        vchain.append(f"setpts={1.0 / speed:.6f}*PTS")
    vchain.append(f"scale={W}:{H}:force_original_aspect_ratio=increase")
    vchain.append(f"crop={W}:{H}")
    if color:
        vchain.append(color)
    if transition in TRANSITIONS:
        fd = tdur or TRANSITIONS[transition]
        col = ":color=white" if transition == "fadewhite" else ""
        dur = (_duration(src) or 0) / (speed or 1.0)
        vchain.append(f"fade=t=in:st=0:d={fd}{col}")
        if dur > 2 * fd:
            vchain.append(f"fade=t=out:st={dur - fd:.2f}:d={fd}{col}")
    if text_ov.get("enabled") and (text_ov.get("content") or "").strip():
        content = text_ov["content"].strip()
        tf = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
        tf.write(content)
        tf.close()
        req_fs = int(H * min(0.14, max(0.03, float(text_ov.get("size", 0.06)))))
        fit_fs = int(W * 0.92 / max(1, len(content) * 0.55))
        fs = max(18, min(req_fs, fit_fs))
        bw = max(2, fs // 12)
        pos = text_ov.get("position", "top")
        yexpr = "(h*0.07)" if pos == "top" else ("(h-text_h)/2" if pos == "center" else "(h-text_h-h*0.09)")
        vchain.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf:"
            f"textfile={tf.name}:fontcolor=white:fontsize={fs}:borderw={bw}:bordercolor=black@0.9:"
            f"x=(w-text_w)/2:y={yexpr}"
        )
    if use_subs:
        vchain.append(f"ass={subtitle_path}")

    inputs = ["-i", src]
    logo_idx = music_idx = None
    if use_logo:
        inputs += ["-i", logo_path]
        logo_idx = 1
    if use_music:
        inputs += ["-i", music_path]
        music_idx = (logo_idx or 0) + 1

    if use_logo:
        lw = min(0.9, max(0.03, float(logo.get("scale", 0.18))))
        op = min(1.0, max(0.05, float(logo.get("opacity", 0.85))))
        xf = min(1.0, max(0.0, float(logo.get("x", 0.95))))
        yf = min(1.0, max(0.0, float(logo.get("y", 0.95))))
        filter_complex = (
            f"[0:v]{','.join(vchain)}[base];"
            f"[{logo_idx}:v]scale=iw*{lw:.4f}:-1,format=rgba,colorchannelmixer=aa={op:.3f}[lg];"
            f"[base][lg]overlay=x=(W-w)*{xf:.4f}:y=(H-h)*{yf:.4f}[v]"
        )
    else:
        filter_complex = f"[0:v]{','.join(vchain)}[v]"

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[v]"]
    if use_music:
        cmd += ["-map", f"{music_idx}:a", "-af", f"afade=t=in:d=1,volume={music_vol:.2f}", "-shortest", "-c:a", "aac"]
    elif speed != 1.0:
        cmd += ["-filter:a", _atempo_chain(speed), "-map", "0:a?", "-c:a", "aac"]
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
        factors.append(2.0)
        s /= 2.0
    while s < 0.5:
        factors.append(0.5)
        s /= 0.5
    factors.append(round(s, 4))
    return ",".join(f"atempo={f}" for f in factors)
