import { useEffect, useRef, useState } from "react";
import { Play, Pause, Music } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import { useI18n } from "@/i18n";
import { bl } from "@/lib/bilingual";

export function MusicPicker({ selected, onSelect }) {
  const { t, lang } = useI18n();
  const [tracks, setTracks] = useState([]);
  const [playing, setPlaying] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    api.get("/music").then((r) => setTracks(r.data)).catch(() => {});
    return () => { if (audioRef.current) audioRef.current.pause(); };
  }, []);

  const toggle = (track) => {
    if (playing === track.id) {
      audioRef.current?.pause();
      setPlaying(null);
      return;
    }
    if (audioRef.current) audioRef.current.pause();
    const a = new Audio(fileUrl(track.storage_path));
    audioRef.current = a;
    a.play().catch(() => {});
    a.onended = () => setPlaying(null);
    setPlaying(track.id);
  };

  return (
    <div className="space-y-2" data-testid="music-picker">
      <div className="flex items-center gap-2">
        <Music size={13} className="text-lumiere-iris" />
        <span className="label-mono text-lumiere-iris">{t("stockMusic")}</span>
        <span className="font-mono text-[0.6rem] text-lumiere-ivory/40">{t("royaltyFree")}</span>
      </div>
      {tracks.map((tr) => {
        const isSel = selected === tr.id;
        return (
          <div key={tr.id} data-testid={`track-${tr.id}`}
            className={`flex items-center gap-3 p-3 border transition-colors ${isSel ? "border-lumiere-gold bg-lumiere-gold/10" : "border-white/10 hover:border-white/25"}`}>
            <button data-testid={`play-${tr.id}`} onClick={() => toggle(tr)}
              className="w-8 h-8 flex items-center justify-center border border-white/20 text-lumiere-ivory hover:border-lumiere-gold transition-colors">
              {playing === tr.id ? <Pause size={13} /> : <Play size={13} />}
            </button>
            <div className="flex-1">
              <p className="font-display text-base text-lumiere-ivory">{bl(tr.title, lang)}</p>
              <p className="font-mono text-[0.6rem] text-lumiere-ivory/40 uppercase">{tr.mood} · {tr.duration_sec}s · CC0</p>
            </div>
            <button data-testid={`apply-${tr.id}`} onClick={() => onSelect(isSel ? null : tr.id)}
              className={`px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest transition-colors ${isSel ? "bg-lumiere-gold text-lumiere-ink" : "border border-white/20 text-lumiere-ivory hover:border-lumiere-gold"}`}>
              {isSel ? t("applied") : t("apply")}
            </button>
          </div>
        );
      })}
    </div>
  );
}
