"""Real (non-AI) media processing with FFmpeg.

Validates media, extracts segments and renders a real cut from a structured EDL.
Originals are never modified; every render is a new derivative file.
"""
import json
import subprocess
from pathlib import Path


class _Failed:
    def __init__(self, err):
        self.returncode = 127
        self.stderr = err
        self.stdout = ""


def _run(cmd: list):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as e:
        return _Failed(f"binary_not_found: {e}")
    except subprocess.TimeoutExpired:
        return _Failed("ffmpeg_timeout")


def probe(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height",
        "-of", "json", str(path),
    ]
    r = _run(cmd)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr[-400:]}
    data = json.loads(r.stdout or "{}")
    streams = data.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    return {"ok": True, "duration": duration, "has_audio": has_audio, "has_video": has_video}


def faststart_bytes(data: bytes, suffix: str = ".mp4") -> bytes:
    """Remux mp4 bytes so the moov atom is at the FRONT (-movflags +faststart).
    Browsers can't render mp4s with moov-at-end without full download (black video).
    Stream-copies (no re-encode). Returns original bytes on any failure."""
    import tempfile, os
    if not suffix.lower().lstrip(".") in ("mp4", "mov", "m4v"):
        return data
    src = dst = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(data)
            src = tf.name
        dst = src + ".fs.mp4"
        r = _run(["ffmpeg", "-y", "-i", src, "-c", "copy", "-movflags", "+faststart", dst])
        if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
            with open(dst, "rb") as f:
                return f.read()
    except Exception:
        pass
    finally:
        for p in (src, dst):
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass
    return data




def _is_image(src: str) -> bool:
    """A still image has a video stream but no meaningful timeline duration."""
    info = probe(src)
    return bool(info.get("has_video")) and (info.get("duration", 0) or 0) < 0.05


def _drawtext(title: str) -> str:
    import re as _re
    safe = _re.sub(r"[^A-Za-z0-9 ,.!?'-]", "", str(title))[:48].replace("'", "")
    if not safe:
        return ""
    font = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    fontpart = f"fontfile={font}:" if Path(font).exists() else ""
    return (f",drawtext={fontpart}text='{safe}':fontsize=34:fontcolor=white:"
            f"box=1:boxcolor=black@0.45:boxborderw=12:x=(w-text_w)/2:y=h-140:"
            f"alpha='min(1,max(0,(t-0.3)*2))'")


def normalize_segment(src: str, start: float, end: float, out: Path, has_audio: bool, title: str = None) -> bool:
    """Trim [start,end] and normalize to 1280x720/30fps + stereo audio.
    Still images are looped to fill the requested duration (so they render and
    can be crossfaded like video clips). Optional title card burned via drawtext."""
    dur = max(0.5, float(end) - float(start))
    vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30")
    if title:
        vf += _drawtext(title)
    common_out = ["-vf", vf, "-r", "30",
                  "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-ar", "48000", "-ac", "2"]
    if _is_image(src):
        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", str(src),
               "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
               *common_out, "-map", "0:v:0", "-map", "1:a:0", "-shortest", str(out)]
    else:
        cmd = ["ffmpeg", "-y", "-ss", str(max(0, float(start))), "-t", str(dur), "-i", str(src)]
        if not has_audio:
            cmd += ["-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        cmd += [*common_out, "-map", "0:v:0",
                "-map", ("1:a:0" if not has_audio else "0:a:0"), "-shortest", str(out)]
    r = _run(cmd)
    return r.returncode == 0 and out.exists()


def render_cut(edl_clips: list, resolver, tmp_dir: Path, out_path: Path) -> dict:
    """edl_clips: [{asset_id, segment_start_sec, segment_end_sec, order}].
    resolver(asset_id) -> (local_path, has_audio). Returns render result dict.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(edl_clips, key=lambda c: c.get("order", 0))
    seg_files = []
    for i, clip in enumerate(ordered):
        resolved = resolver(clip["asset_id"])
        if not resolved:
            continue
        src, has_audio = resolved
        seg_out = tmp_dir / f"seg_{i:03d}.mp4"
        ok = normalize_segment(src, clip.get("segment_start_sec", 0), clip.get("segment_end_sec", 3), seg_out, has_audio)
        if ok:
            seg_files.append(seg_out)

    if not seg_files:
        return {"ok": False, "error": "no_usable_segments"}

    list_file = tmp_dir / "concat.txt"
    list_file.write_text("".join(f"file '{f.as_posix()}'\n" for f in seg_files))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)])
    if r.returncode != 0 or not out_path.exists():
        return {"ok": False, "error": r.stderr[-400:]}

    info = probe(str(out_path))
    return {"ok": True, "clips": len(seg_files), "duration": info.get("duration", 0), "path": str(out_path)}


XFADE_MAP = {"fade": "fade", "dissolve": "dissolve", "smooth": "smoothleft",
             "fadeblack": "fadeblack", "fadewhite": "fadewhite"}


def xfade_concat(seg_files: list, out_path: Path, transition: str = "fade", tdur: float = 0.4) -> dict:
    """Crossfade a list of already-normalized (1280x720/30fps/stereo) clips together."""
    seg_files = [f for f in seg_files if (probe(str(f)).get("duration") or 0) >= 0.2]
    if not seg_files:
        return {"ok": False, "error": "no_usable_segments"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if len(seg_files) == 1:
        r = _run(["ffmpeg", "-y", "-i", str(seg_files[0]), "-c", "copy", str(out_path)])
        return {"ok": r.returncode == 0 and out_path.exists(), "clips": 1, "path": str(out_path)}
    xf = XFADE_MAP.get(transition, "fade")
    durs = [probe(str(f)).get("duration", 0) or 0 for f in seg_files]
    T = min(tdur, max(0.2, min(durs) / 2.0))
    inputs = []
    for f in seg_files:
        inputs += ["-i", str(f)]
    parts, prev_v, prev_a = [], "[0:v]", "[0:a]"
    running = durs[0]
    for m in range(1, len(seg_files)):
        offset = max(0.0, running - T)
        parts.append(f"{prev_v}[{m}:v]xfade=transition={xf}:duration={T:.3f}:offset={offset:.3f}[v{m}]")
        parts.append(f"{prev_a}[{m}:a]acrossfade=d={T:.3f}[a{m}]")
        prev_v, prev_a = f"[v{m}]", f"[a{m}]"
        running += durs[m] - T
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts),
           "-map", prev_v, "-map", prev_a, "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(out_path)]
    r = _run(cmd)
    if r.returncode != 0 or not out_path.exists():
        return {"ok": False, "error": r.stderr[-400:]}
    return {"ok": True, "clips": len(seg_files), "path": str(out_path)}


def render_cut_with_transitions(edl_clips: list, resolver, tmp_dir: Path, out_path: Path,
                                transition: str = "fade", tdur: float = 0.5) -> dict:
    """Like render_cut but crossfades BETWEEN scenes (real CapCut-style transitions)."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(edl_clips, key=lambda c: c.get("order", 0))
    seg_files = []
    for i, clip in enumerate(ordered):
        resolved = resolver(clip["asset_id"])
        if not resolved:
            continue
        src, has_audio = resolved
        seg_out = tmp_dir / f"seg_{i:03d}.mp4"
        if normalize_segment(src, clip.get("segment_start_sec", 0), clip.get("segment_end_sec", 3), seg_out, has_audio, clip.get("title")):
            seg_files.append(seg_out)
    return xfade_concat(seg_files, out_path, transition, tdur)


def add_music(video_path, music_path, out_path) -> bool:
    """Mux a music bed under the existing audio, trimmed to the video length."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path), "-i", str(music_path),
        "-filter_complex",
        "[1:a]volume=0.35[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(out_path), "-loglevel", "error",
    ]
    r = _run(cmd)
    return r.returncode == 0 and Path(out_path).exists()
