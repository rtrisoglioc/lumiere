"""Stock/AI B-roll inserts: turn a still image into a short animated clip
(Ken Burns / zoom-out / slide / fade / pulse) and splice it into a base video
at an arbitrary timestamp, crossfaded in and out."""
import subprocess
from pathlib import Path

import ffmpeg_worker as ff

EFFECTS = ("kenburns", "zoomout", "slide", "fade", "pulse")
W, H, FPS = 1280, 720, 30


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def build_insert_clip(image_path: str, out: Path, duration: float = 2.0, effect: str = "kenburns") -> bool:
    duration = max(0.8, min(8.0, float(duration)))
    n = max(1, int(round(duration * FPS)))
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    zp = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if effect == "kenburns":
        vf = f"{cover},zoompan=z='min(zoom+0.0012,1.4)':d={n}:{zp}:s={W}x{H}:fps={FPS}"
    elif effect == "zoomout":
        vf = f"{cover},zoompan=z='if(eq(on,0),1.4,max(zoom-0.0012,1.001))':d={n}:{zp}:s={W}x{H}:fps={FPS}"
    elif effect == "pulse":
        vf = f"{cover},zoompan=z='min(zoom+0.0006,1.15)':d={n}:{zp}:s={W}x{H}:fps={FPS}"
    elif effect == "slide":
        vf = (f"scale={int(W*1.25)}:{int(H*1.25)}:force_original_aspect_ratio=increase,crop={int(W*1.2)}:{H},setsar=1,"
              f"zoompan=z=1.0:d={n}:x='(iw-{W})*on/{n}':y=0:s={W}x{H}:fps={FPS}")
    else:  # fade / static
        vf = f"{cover},fps={FPS}"
    fd = min(0.4, duration / 4.0)
    vf += f",fade=t=in:st=0:d={fd:.2f},fade=t=out:st={max(0, duration - fd):.2f}:d={fd:.2f}"
    cmd = ["ffmpeg", "-y", "-loop", "1", "-t", f"{duration:.2f}", "-i", str(image_path),
           "-f", "lavfi", "-t", f"{duration:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
           "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-ar", "48000", "-ac", "2", "-map", "0:v", "-map", "1:a", "-shortest", str(out)]
    r = _run(cmd)
    return r.returncode == 0 and out.exists()


def splice_inserts(base_path: str, inserts: list, out_path: Path, tmp_dir: Path,
                   join: str = "fade") -> dict:
    """inserts: [{image_path, at_sec, duration, effect}] placed by time into base."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dur = ff.probe(str(base_path)).get("duration", 0) or 0
    if dur <= 0:
        return {"ok": False, "error": "bad_base"}
    items = sorted(inserts, key=lambda i: max(0.0, min(float(i.get("at_sec", 0)), dur)))
    segments, prev, idx = [], 0.0, 0
    for i in items:
        at = max(0.0, min(float(i.get("at_sec", 0)), dur))
        if at - prev > 0.2:
            bp = tmp_dir / f"base_{idx:03d}.mp4"
            if ff.normalize_segment(str(base_path), prev, at, bp, True):
                segments.append(bp)
        ic = tmp_dir / f"ins_{idx:03d}.mp4"
        eff = i.get("effect") if i.get("effect") in EFFECTS else "kenburns"
        if build_insert_clip(i["image_path"], ic, i.get("duration", 2.0), eff):
            segments.append(ic)
        prev, idx = at, idx + 1
    if dur - prev > 0.2:
        bp = tmp_dir / f"base_{idx:03d}.mp4"
        if ff.normalize_segment(str(base_path), prev, dur, bp, True):
            segments.append(bp)
    if not segments:
        return {"ok": False, "error": "no_segments"}
    return ff.xfade_concat(segments, out_path, join if join in ff.XFADE_MAP else "fade", tdur=0.35)
