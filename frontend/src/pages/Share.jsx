import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, Film } from "lucide-react";
import { API } from "@/lib/api";

export default function Share() {
  const { shareId } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    fetch(`${API}/public/cuts/${shareId}`).then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setData).catch(() => setErr(true));
  }, [shareId]);

  if (err) return (
    <div className="min-h-screen bg-lumiere-base text-lumiere-ivory flex flex-col items-center justify-center gap-3">
      <Film className="text-lumiere-gold" /><p className="text-lumiere-ivory/60">This film is no longer available.</p>
    </div>
  );
  if (!data) return <div className="min-h-screen bg-lumiere-base flex items-center justify-center"><Loader2 className="animate-spin text-lumiere-gold" /></div>;

  return (
    <div className="min-h-screen bg-lumiere-base text-lumiere-ivory" data-testid="share-page">
      <header className="px-6 py-5 flex items-center justify-between border-b border-white/10">
        <span className="font-display text-2xl font-black tracking-tight">LUMIÈRE</span>
        <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ivory/40">{data.style} · {data.duration}s</span>
      </header>
      <main className="max-w-4xl mx-auto px-4 sm:px-8 py-10">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-gold mb-2">A film made with LUMIÈRE</p>
        <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight mb-5">{data.title}</h1>
        <div className="rounded-2xl overflow-hidden border border-white/10 bg-black shadow-2xl">
          <video src={`${API}${data.video_url}`} poster={data.poster_url ? `${API}${data.poster_url}` : undefined}
            controls playsInline className="w-full max-h-[70vh] bg-black" data-testid="share-video" />
        </div>
        {data.premise && <p className="text-lumiere-ivory/60 mt-5 max-w-2xl">{data.premise}</p>}
        <a href="/" className="inline-block mt-8 font-mono text-[0.65rem] uppercase tracking-widest text-lumiere-gold hover:underline">Make your own → </a>
      </main>
    </div>
  );
}
