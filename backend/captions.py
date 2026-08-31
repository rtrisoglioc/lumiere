"""CapCut-style auto-captions.

Transcribes a video's speech with OpenAI Whisper (Emergent Universal Key) and
renders styled, burned-in subtitles via a generated ASS file that FFmpeg's
`ass` filter draws onto the final frame. Timings are scaled by playback speed so
captions stay in sync after a speed change."""
import os
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
FONT = "Liberation Sans"

# ASS colours are &HAABBGGRR (AA=alpha, 00=opaque). BorderStyle 1=outline+shadow, 3=opaque box.
STYLES = {
    "bold":    {"primary": "&H00FFFFFF", "outline": "&H00000000", "back": "&H64000000", "size": 0.072, "bd": 1, "ol": 3, "sh": 1, "bold": -1, "upper": False},
    "pop":     {"primary": "&H0000E5FF", "outline": "&H00000000", "back": "&H78000000", "size": 0.085, "bd": 1, "ol": 4, "sh": 1, "bold": -1, "upper": True},
    "boxed":   {"primary": "&H00FFFFFF", "outline": "&H00000000", "back": "&HAA000000", "size": 0.066, "bd": 3, "ol": 6, "sh": 0, "bold": -1, "upper": False},
    "minimal": {"primary": "&H00FFFFFF", "outline": "&H00000000", "back": "&H00000000", "size": 0.058, "bd": 1, "ol": 2, "sh": 0, "bold": 0,  "upper": False},
}


def _fmt_time(t: float) -> str:
    if t < 0:
        t = 0
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, c = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _wrap(text: str, max_chars: int = 30) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\\N".join(lines[:2])


def build_ass(segments: list, W: int, H: int, speed: float = 1.0, style: str = "bold") -> str:
    st = STYLES.get(style, STYLES["bold"])
    fontsize = max(16, int(H * st["size"]))
    marginv = int(H * 0.09)
    marginlr = int(W * 0.05)
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{FONT},{fontsize},{st['primary']},&H000000FF,{st['outline']},{st['back']},"
        f"{st['bold']},0,0,0,100,100,0,0,{st['bd']},{st['ol']},{st['sh']},2,{marginlr},{marginlr},{marginv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    rows = []
    for seg in segments:
        txt = (seg.get("text") or "").strip()
        if not txt:
            continue
        if st["upper"]:
            txt = txt.upper()
        rows.append(
            f"Dialogue: 0,{_fmt_time(seg['start'] / speed)},{_fmt_time(seg['end'] / speed)},"
            f"Default,,0,0,0,,{_wrap(txt)}"
        )
    return header + "\n".join(rows) + "\n"


def _extract_audio(video_path: str):
    audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", audio],
        capture_output=True, timeout=120,
    )
    if r.returncode != 0 or not Path(audio).exists() or Path(audio).stat().st_size < 256:
        Path(audio).unlink(missing_ok=True)
        return None
    return audio


async def transcribe(video_path: str, language: str = None) -> list:
    from emergentintegrations.llm.openai import OpenAISpeechToText
    audio = _extract_audio(video_path)
    if not audio:
        return []
    try:
        stt = OpenAISpeechToText(api_key=EMERGENT_KEY)
        with open(audio, "rb") as f:
            kwargs = dict(file=f, model="whisper-1", response_format="verbose_json",
                          timestamp_granularities=["segment"])
            if language:
                kwargs["language"] = language
            resp = await stt.transcribe(**kwargs)
    finally:
        Path(audio).unlink(missing_ok=True)

    raw = getattr(resp, "segments", None)
    if raw is None and isinstance(resp, dict):
        raw = resp.get("segments")
    segs = []
    for s in raw or []:
        get = (lambda k: s.get(k)) if isinstance(s, dict) else (lambda k: getattr(s, k, None))
        text = (get("text") or "").strip()
        if not text:
            continue
        segs.append({"start": float(get("start") or 0), "end": float(get("end") or 0), "text": text})
    return segs


async def generate_ass(video_path: str, W: int, H: int, speed: float = 1.0,
                       style: str = "bold", language: str = None):
    """Return a temp .ass file path with burned-in captions, or None if no speech."""
    segs = await transcribe(video_path, language)
    if not segs:
        return None
    p = tempfile.NamedTemporaryFile(suffix=".ass", delete=False).name
    Path(p).write_text(build_ass(segs, W, H, speed or 1.0, style), encoding="utf-8")
    return p
