"""Royalty-free (CC0) stock music library.

Tracks are synthesized with FFmpeg at startup — fully license-free and owned by
the app. Seeded once into object storage + `music_tracks` collection (idempotent
via MUSIC_VERSION). Used to score rendered cuts.
"""
import subprocess
import tempfile
from pathlib import Path

from db import db, now_iso
import storage

MUSIC_VERSION = 1

TRACKS = [
    {"id": "golden-hour", "title": {"en": "Golden Hour", "es": "Hora Dorada"}, "mood": "warm",
     "freqs": [220.00, 277.18, 329.63], "dur": 28},
    {"id": "sage-drift", "title": {"en": "Sage Drift", "es": "Deriva Salvia"}, "mood": "calm",
     "freqs": [196.00, 246.94, 293.66], "dur": 28},
    {"id": "iris-night", "title": {"en": "Iris Night", "es": "Noche Iris"}, "mood": "cinematic",
     "freqs": [174.61, 207.65, 261.63], "dur": 30},
    {"id": "coastal-light", "title": {"en": "Coastal Light", "es": "Luz Costera"}, "mood": "bright",
     "freqs": [261.63, 329.63, 392.00], "dur": 26},
]


def _synth(freqs, dur, out: Path) -> bool:
    inputs = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={dur}"]
    n = len(freqs)
    fc = (f"[{']['.join(str(i) for i in range(n))}]amix=inputs={n},"
          f"vibrato=f=5:d=0.4,aecho=0.8:0.9:120:0.25,"
          f"afade=t=in:d=2,afade=t=out:st={dur-3}:d=3,volume=3")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-ac", "2", "-ar", "44100",
           "-c:a", "libmp3lame", "-q:a", "5", str(out), "-loglevel", "error"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 0


async def seed_music():
    existing = await db.music_tracks.find_one({"version": MUSIC_VERSION}, {"_id": 0})
    if existing:
        return
    tmp = Path(tempfile.gettempdir())
    for spec in TRACKS:
        out = tmp / f"{spec['id']}.mp3"
        if not _synth(spec["freqs"], spec["dur"], out):
            continue
        data = out.read_bytes()
        path = f"{storage.APP_NAME}/music/{spec['id']}.mp3"
        put = storage.put_object(path, data, "audio/mpeg")
        await db.music_tracks.update_one(
            {"id": spec["id"]},
            {"$set": {
                "id": spec["id"], "title": spec["title"], "mood": spec["mood"],
                "duration_sec": spec["dur"], "storage_path": put["path"],
                "content_type": "audio/mpeg", "license": "CC0", "is_bundled": True,
                "version": MUSIC_VERSION, "created_at": now_iso(),
            }},
            upsert=True,
        )


async def list_tracks():
    return await db.music_tracks.find({}, {"_id": 0}).sort("id", 1).to_list(100)


async def get_track(track_id: str):
    return await db.music_tracks.find_one({"id": track_id}, {"_id": 0})
