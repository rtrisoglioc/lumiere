import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Clapperboard, Camera, Gauge, Scissors, Terminal, Upload, Sparkles,
  Play, AlertTriangle, Wand2, Loader2, Film,
} from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import { useI18n } from "@/i18n";
import { bl } from "@/lib/bilingual";
import { Header } from "@/components/Header";
import { StatusBadge, ProcessTimeline } from "@/components/StatusBadge";
import { CircularScore, ScoreBar } from "@/components/CircularScore";
import { AgentTrace } from "@/components/AgentTrace";

const TABS = [
  { id: "story", icon: Clapperboard },
  { id: "capture", icon: Camera },
  { id: "evaluate", icon: Gauge },
  { id: "edit", icon: Scissors },
  { id: "trace", icon: Terminal },
];

function UploadButton({ expId, missionId, label, onStart, testid, variant = "ghost" }) {
  const ref = useRef();
  const [busy, setBusy] = useState(false);
  const handle = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    if (missionId) form.append("mission_id", missionId);
    try {
      await api.post(`/experiences/${expId}/upload`, form, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Uploaded — analyzing");
      onStart?.();
    } catch {
      toast.error("Upload failed");
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  };
  const cls = variant === "primary"
    ? "bg-lumiere-orange hover:bg-lumiere-orangeHover text-white"
    : "border border-white/20 text-white hover:border-lumiere-orange";
  return (
    <>
      <input ref={ref} type="file" accept="video/*,image/*" className="hidden" onChange={handle} data-testid={`${testid}-input`} />
      <button data-testid={testid} disabled={busy} onClick={() => ref.current?.click()}
        className={`inline-flex items-center gap-2 px-4 py-2.5 font-mono text-xs uppercase tracking-widest transition-colors duration-300 disabled:opacity-50 ${cls}`}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {label}
      </button>
    </>
  );
}

function VideoMonitor({ storagePath, testid }) {
  return (
    <div className="viewfinder border border-white/15 bg-black p-2" data-testid={testid}>
      <span className="vf-bl" /><span className="vf-br" />
      <video src={fileUrl(storagePath)} controls playsInline className="w-full aspect-video bg-black" />
    </div>
  );
}

export default function Experience() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const [exp, setExp] = useState(null);
  const [tab, setTab] = useState("story");
  const [runs, setRuns] = useState([]);
  const [agentHealth, setAgentHealth] = useState(null);
  const [partnerHealth, setPartnerHealth] = useState(null);
  const [intent, setIntent] = useState("");
  const [planning, setPlanning] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [cutting, setCutting] = useState(false);
  const [revising, setRevising] = useState(false);
  const [instruction, setInstruction] = useState("");
  const pollRef = useRef(null);

  const fetchExp = useCallback(async () => {
    try {
      const res = await api.get(`/experiences/${id}`);
      setExp(res.data);
      return res.data;
    } catch { toast.error("Load failed"); }
  }, [id]);

  const fetchRuns = useCallback(async () => {
    try { const res = await api.get(`/experiences/${id}/agent-runs`); setRuns(res.data); } catch { /* */ }
  }, [id]);

  useEffect(() => {
    fetchExp();
    fetchRuns();
    api.get("/agent/health").then((r) => setAgentHealth(r.data)).catch(() => {});
    api.get("/partner/health").then((r) => setPartnerHealth(r.data)).catch(() => {});
  }, [fetchExp, fetchRuns]);

  // polling while work is pending
  const pending = exp && (
    (exp.media || []).some((m) => ["processing", "analyzing"].includes(m.status)) ||
    (exp.cuts || []).some((c) => c.status === "rendering")
  );
  useEffect(() => {
    if (pending && !pollRef.current) {
      pollRef.current = setInterval(() => { fetchExp(); fetchRuns(); }, 3500);
    } else if (!pending && pollRef.current) {
      clearInterval(pollRef.current); pollRef.current = null;
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [pending, fetchExp, fetchRuns]);

  const doPlan = async () => {
    if (!intent.trim()) return;
    setPlanning(true);
    try {
      await api.post(`/experiences/${id}/plan`, { intent: intent.trim() });
      await fetchExp(); await fetchRuns();
      toast.success("Story directed");
    } catch { toast.error("Planning failed"); }
    finally { setPlanning(false); }
  };

  const doEvaluate = async () => {
    setEvaluating(true);
    try {
      await api.post(`/experiences/${id}/evaluate`);
      await fetchExp(); await fetchRuns();
      toast.success("Coverage evaluated");
    } catch (e) { toast.error(e?.response?.data?.detail || "Evaluation failed"); }
    finally { setEvaluating(false); }
  };

  const doCut = async () => {
    setCutting(true);
    try {
      await api.post(`/experiences/${id}/cut`);
      await fetchExp(); await fetchRuns();
      toast.success("Rendering cut");
    } catch (e) { toast.error(e?.response?.data?.detail || "Cut failed"); }
    finally { setCutting(false); }
  };

  const doRevise = async (cutId, confirm = false) => {
    if (!instruction.trim()) return;
    setRevising(true);
    try {
      await api.post(`/cuts/${cutId}/revise`, { instruction: instruction.trim() });
      setInstruction("");
      await fetchExp(); await fetchRuns();
      toast.success("Re-editing");
    } catch { toast.error("Revise failed"); }
    finally { setRevising(false); }
  };

  if (!exp) {
    return (
      <div className="min-h-screen bg-lumiere-base">
        <Header back />
        <div className="flex items-center justify-center py-32"><span className="font-mono text-sm text-lumiere-orange cursor-blink">LOADING</span></div>
      </div>
    );
  }

  const plan = exp.plan;
  const missions = (exp.missions || {}).missions || [];
  const media = exp.media || [];
  const analyzedCount = media.filter((m) => m.status === "analyzed").length;
  const usableCount = media.filter((m) => (m.analysis?.technical?.usable)).length;
  const completeness = exp.completeness;
  const cuts = exp.cuts || [];
  const latestReadyCut = [...cuts].reverse().find((c) => c.status === "ready");

  return (
    <div className="min-h-screen bg-lumiere-base pb-24 sm:pb-8">
      <Header back />

      {/* title band */}
      <div className="px-4 sm:px-8 pt-6 pb-4 max-w-6xl mx-auto">
        <p className="label-mono mb-1 text-lumiere-orange">{exp.type} · {t("private")}</p>
        <h1 className="font-display text-3xl sm:text-4xl font-black tracking-tight text-white">{exp.title}</h1>
      </div>

      {/* tabs (top on desktop) */}
      <div className="hidden sm:flex sticky top-[65px] z-30 px-8 max-w-6xl mx-auto gap-1 border-b border-white/10 bg-lumiere-base/80 backdrop-blur-xl">
        {TABS.map((tb) => (
          <button key={tb.id} data-testid={`tab-${tb.id}`} onClick={() => setTab(tb.id)}
            className={`flex items-center gap-2 px-4 py-3 font-mono text-xs uppercase tracking-widest border-b-2 -mb-px transition-colors duration-300 ${tab === tb.id ? "border-lumiere-orange text-white" : "border-transparent text-zinc-500 hover:text-white"}`}>
            <tb.icon size={14} /> {t(tb.id)}
          </button>
        ))}
      </div>

      <main className="px-4 sm:px-8 py-6 max-w-6xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>

            {/* STORY */}
            {tab === "story" && (
              <div className="space-y-8">
                {!plan ? (
                  <div className="max-w-2xl">
                    <p className="label-mono mb-2">{t("storyIntent")}</p>
                    <h2 className="font-display text-2xl sm:text-3xl text-white mb-6">{t("intentPrompt")}</h2>
                    <textarea data-testid="intent-textarea" value={intent} onChange={(e) => setIntent(e.target.value)}
                      rows={5} placeholder={t("intentPlaceholder")}
                      className="w-full bg-lumiere-surface border border-white/15 focus:border-lumiere-orange outline-none p-4 text-white resize-none transition-colors duration-300" />
                    <button data-testid="direct-story-button" onClick={doPlan} disabled={planning || !intent.trim()}
                      className="mt-4 inline-flex items-center gap-2 bg-lumiere-orange hover:bg-lumiere-orangeHover disabled:opacity-50 text-white px-6 py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300">
                      {planning ? <><Loader2 size={14} className="animate-spin" /> {t("directing")}</> : <><Sparkles size={14} /> {t("directMyStory")}</>}
                    </button>
                    {planning && <p className="mt-3 font-mono text-xs text-zinc-500 cursor-blink">DIRECTOR + CINEMATOGRAPHER</p>}
                  </div>
                ) : (
                  <>
                    <div className="viewfinder border border-white/10 bg-lumiere-surface p-6 sm:p-8">
                      <span className="vf-bl" /><span className="vf-br" />
                      <p className="label-mono mb-3">{t("story")}</p>
                      <h2 data-testid="plan-title" className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">{bl(plan.title, lang)}</h2>
                      <p className="text-zinc-300 leading-relaxed max-w-2xl">{bl(plan.premise, lang)}</p>
                      <div className="grid sm:grid-cols-2 gap-6 mt-6">
                        <div><p className="label-mono mb-1">{t("arc")}</p><p className="text-sm text-zinc-400">{bl(plan.arc, lang)}</p></div>
                        <div><p className="label-mono mb-1">{t("tone")}</p><p className="text-sm text-zinc-400">{bl(plan.tone, lang)}</p></div>
                      </div>
                    </div>

                    <div>
                      <p className="label-mono mb-3">{t("beats")}</p>
                      <div className="space-y-2">
                        {(plan.beats || []).map((b) => (
                          <div key={b.id} data-testid={`beat-${b.id}`} className="border-l-2 border-lumiere-orange bg-lumiere-surface p-4">
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-xs text-lumiere-orange">{String(b.order).padStart(2, "0")}</span>
                              <span className="font-display text-lg text-white">{bl(b.name, lang)}</span>
                            </div>
                            <p className="text-sm text-zinc-400 mt-1 ml-8">{bl(b.purpose, lang)}</p>
                            <p className="text-xs text-lumiere-cyan mt-1 ml-8 font-mono">{bl(b.emotion, lang)}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <p className="label-mono">{t("shotMissions")}</p>
                        <button data-testid="goto-capture" onClick={() => setTab("capture")} className="font-mono text-xs text-lumiere-orange hover:underline">{t("capture")} →</button>
                      </div>
                      <div className="grid sm:grid-cols-2 gap-3">
                        {[...missions].sort((a, b) => (a.priority || 5) - (b.priority || 5)).map((m) => (
                          <div key={m.id} data-testid={`mission-${m.id}`} className="border border-white/10 bg-lumiere-surface p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-cyan">{m.shot_type}</span>
                              <span className="font-mono text-[0.6rem] text-zinc-500">{t("priority")} {m.priority}</span>
                            </div>
                            <p className="font-display text-lg text-white">{bl(m.title, lang)}</p>
                            <p className="text-sm text-zinc-400 mt-1">{bl(m.direction, lang)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* CAPTURE */}
            {tab === "capture" && (
              <div className="space-y-8">
                {!plan ? (
                  <p className="text-zinc-500">{t("noFootage")}</p>
                ) : (
                  <>
                    <div>
                      <p className="label-mono mb-3">{t("liveDirection")}</p>
                      <div className="space-y-3">
                        {[...missions].sort((a, b) => (a.priority || 5) - (b.priority || 5)).map((m, idx) => {
                          const shot = media.filter((x) => x.mission_id === m.id);
                          const isNext = idx === 0 && shot.length === 0;
                          return (
                            <div key={m.id} data-testid={`capture-mission-${m.id}`}
                              className={`border p-4 ${isNext ? "border-lumiere-orange bg-lumiere-orange/5" : "border-white/10 bg-lumiere-surface"}`}>
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <div>
                                  <div className="flex items-center gap-2">
                                    {isNext && <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-orange">{t("nextMission")}</span>}
                                    <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-cyan">{m.shot_type}</span>
                                  </div>
                                  <p className="font-display text-lg text-white mt-1">{bl(m.title, lang)}</p>
                                  <p className="text-sm text-zinc-400">{bl(m.direction, lang)}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                  {shot.map((s) => <StatusBadge key={s.id} status={s.status} />)}
                                  <UploadButton expId={id} missionId={m.id} label={t("uploadFootage")} testid={`upload-${m.id}`}
                                    variant={isNext ? "primary" : "ghost"} onStart={fetchExp} />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <p className="label-mono mb-3">{t("capturedFootage")} · {media.length}</p>
                      {media.length === 0 ? (
                        <p className="text-zinc-500">{t("noFootage")}</p>
                      ) : (
                        <div className="grid sm:grid-cols-2 gap-3">
                          {media.map((a) => (
                            <div key={a.id} data-testid={`asset-${a.id}`} className="border border-white/10 bg-lumiere-surface p-4">
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-xs text-zinc-400 truncate max-w-[60%]">{a.original_filename}</span>
                                <StatusBadge status={a.status} />
                              </div>
                              <ProcessTimeline status={a.status} />
                              {a.status === "analyzed" && a.analysis && (
                                <div className="mt-3 space-y-2">
                                  <p className="text-sm text-zinc-300">{bl(a.analysis.scene, lang)}</p>
                                  <div className="flex flex-wrap gap-2">
                                    <span className={`font-mono text-[0.6rem] px-2 py-0.5 border ${a.analysis.technical?.usable ? "border-emerald-500/40 text-emerald-400" : "border-red-500/40 text-red-400"}`}>
                                      {a.analysis.technical?.usable ? t("usable") : t("notUsable")}
                                    </span>
                                    <span className="font-mono text-[0.6rem] px-2 py-0.5 border border-lumiere-cyan/40 text-lumiere-cyan">
                                      {t("relevance")} {Math.round((a.analysis.narrative_relevance?.score || 0) * 100)}%
                                    </span>
                                  </div>
                                </div>
                              )}
                              {a.status === "failed" && <p className="text-xs text-red-400 mt-2">{t("failed")}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    {analyzedCount > 0 && (
                      <button data-testid="goto-evaluate" onClick={() => setTab("evaluate")}
                        className="font-mono text-xs text-lumiere-orange hover:underline">{t("evaluate")} →</button>
                    )}
                  </>
                )}
              </div>
            )}

            {/* EVALUATE */}
            {tab === "evaluate" && (
              <div className="space-y-8">
                {analyzedCount === 0 ? (
                  <p className="text-zinc-500">{t("noEval")}</p>
                ) : (
                  <>
                    <button data-testid="evaluate-button" onClick={doEvaluate} disabled={evaluating}
                      className="inline-flex items-center gap-2 border border-lumiere-cyan/50 text-lumiere-cyan hover:bg-lumiere-cyan/10 px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300 disabled:opacity-50">
                      {evaluating ? <><Loader2 size={14} className="animate-spin" /> {t("evaluating")}</> : <><Gauge size={14} /> {t("runEvaluation")}</>}
                    </button>

                    {completeness?.completeness && (
                      <div className="grid lg:grid-cols-3 gap-6 items-center">
                        <div className="viewfinder border border-white/10 bg-lumiere-surface p-8 flex justify-center">
                          <span className="vf-bl" /><span className="vf-br" />
                          <CircularScore value={completeness.completeness.overall} label={t("overall")} testid="overall-score" />
                        </div>
                        <div className="lg:col-span-2 border border-white/10 bg-lumiere-surface p-6 space-y-4">
                          <ScoreBar label={t("narrative")} value={completeness.completeness.narrative} />
                          <ScoreBar label={t("visual")} value={completeness.completeness.visual} />
                          <ScoreBar label={t("emotional")} value={completeness.completeness.emotional} />
                          {completeness.recommendation && (
                            <div className="pt-3 border-t border-white/10">
                              <p className="label-mono mb-1">{t("recommendation")}</p>
                              <p className="text-sm text-zinc-300">{bl(completeness.recommendation, lang)}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {completeness?.gaps?.length > 0 && (
                      <div>
                        <p className="label-mono mb-3">{t("gaps")}</p>
                        <div className="space-y-2">
                          {completeness.gaps.map((g, i) => (
                            <div key={i} className="flex items-start gap-3 border border-white/10 bg-lumiere-surface p-3">
                              <AlertTriangle size={15} className={g.severity === "critical" ? "text-red-400 mt-0.5" : "text-amber-400 mt-0.5"} />
                              <div>
                                <span className={`font-mono text-[0.6rem] uppercase tracking-widest ${g.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>{t(g.severity)}</span>
                                <p className="text-sm text-zinc-300">{bl(g.reason, lang)}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {completeness?.get_the_shot?.length > 0 && (
                      <div>
                        <p className="label-mono mb-3 text-lumiere-orange">{t("getTheShot")}</p>
                        <div className="grid sm:grid-cols-2 gap-3">
                          {completeness.get_the_shot.map((s) => (
                            <div key={s.id} data-testid={`gts-${s.id}`}
                              className="relative overflow-hidden border border-lumiere-orange/40 p-5">
                              <div className="absolute inset-0 opacity-20 bg-cover bg-center blur-sm"
                                style={{ backgroundImage: "url('https://images.unsplash.com/photo-1601042879364-f3947d3f9c16?crop=entropy&cs=srgb&fm=jpg&q=85&w=800')" }} />
                              <div className="relative">
                                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-cyan">{s.shot_type}</span>
                                <p className="font-display text-xl text-white mt-1">{bl(s.title, lang)}</p>
                                <p className="text-sm text-zinc-300 mt-1">{bl(s.direction, lang)}</p>
                                <p className="text-xs text-zinc-400 mt-2 italic">{bl(s.why, lang)}</p>
                                <div className="mt-4">
                                  <UploadButton expId={id} missionId={s.id} label={t("captureThis")} testid={`gts-upload-${s.id}`} variant="primary" onStart={fetchExp} />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {completeness && (
                      <button data-testid="goto-edit" onClick={() => setTab("edit")} className="font-mono text-xs text-lumiere-orange hover:underline">{t("edit")} →</button>
                    )}
                  </>
                )}
              </div>
            )}

            {/* EDIT */}
            {tab === "edit" && (
              <div className="space-y-8">
                <div className="flex flex-wrap items-center gap-4">
                  <button data-testid="render-cut-button" onClick={doCut} disabled={cutting || usableCount === 0}
                    className="inline-flex items-center gap-2 bg-lumiere-orange hover:bg-lumiere-orangeHover disabled:opacity-40 text-white px-6 py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300">
                    {cutting ? <><Loader2 size={14} className="animate-spin" /> {t("rendering")}</> : <><Film size={14} /> {cuts.length === 0 ? t("firstCut") : t("firstCut")}</>}
                  </button>
                  {usableCount === 0 && <span className="font-mono text-xs text-zinc-500">{t("noCut")}</span>}
                </div>

                {latestReadyCut && (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <p className="label-mono text-lumiere-orange">{t("finalFilm")} · {t("version")} {latestReadyCut.version}</p>
                      <span className="font-mono text-xs text-zinc-500">{t("duration")}: {Math.round(latestReadyCut.duration_sec || 0)}{t("seconds")} · {latestReadyCut.clip_count} {t("clips")}</span>
                    </div>
                    <VideoMonitor storagePath={latestReadyCut.storage_path} testid="cut-player" />
                  </div>
                )}

                {/* re-edit */}
                {latestReadyCut && (
                  <div className="border border-white/10 bg-lumiere-surface p-5">
                    <p className="label-mono mb-3 flex items-center gap-2"><Wand2 size={13} /> {t("reEdit")}</p>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <input data-testid="revise-input" value={instruction} onChange={(e) => setInstruction(e.target.value)}
                        placeholder={t("reEditPlaceholder")}
                        className="flex-1 bg-black/40 border border-white/15 focus:border-lumiere-orange outline-none px-4 py-3 text-white transition-colors duration-300" />
                      <button data-testid="apply-edit-button" onClick={() => doRevise(latestReadyCut.id)} disabled={revising || !instruction.trim()}
                        className="inline-flex items-center gap-2 bg-lumiere-orange hover:bg-lumiere-orangeHover disabled:opacity-50 text-white px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300">
                        {revising ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {t("applyEdit")}
                      </button>
                    </div>
                  </div>
                )}

                {/* version history */}
                {cuts.length > 0 && (
                  <div>
                    <p className="label-mono mb-3">{t("version")} · {cuts.length}</p>
                    <div className="space-y-2">
                      {[...cuts].reverse().map((c) => (
                        <div key={c.id} data-testid={`cut-${c.version}`} className="border border-white/10 bg-lumiere-surface p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-lumiere-orange">V{c.version}</span>
                              <span className="font-mono text-xs text-zinc-400 uppercase">{c.kind === "revision" ? t("revision") : t("initial")}</span>
                            </div>
                            <StatusBadge status={c.status} />
                          </div>
                          {c.instruction && <p className="text-sm text-zinc-300 mt-2 screenplay"><span className="name text-lumiere-orange">YOU</span> — “{c.instruction}”</p>}
                          {c.reviser_summary && <p className="text-sm text-zinc-400 mt-1 screenplay"><span className="name text-lumiere-cyan">REVISER</span> — {bl(c.reviser_summary, lang)}</p>}
                          {c.requires_confirmation && <p className="text-xs text-amber-400 mt-1 flex items-center gap-1"><AlertTriangle size={12} /> {t("needsConfirm")}</p>}
                          {c.edit_decisions?.length > 0 && (
                            <p className="text-xs text-zinc-500 mt-2 font-mono">{t("editDecisions")}: {c.edit_decisions.map((d) => d.type).join(", ")}</p>
                          )}
                          {c.status === "ready" && (
                            <button data-testid={`play-cut-${c.version}`} onClick={() => { setTab("edit"); }}
                              className="mt-3 inline-flex items-center gap-1.5 font-mono text-xs text-lumiere-orange hover:underline"><Play size={12} /> {t("finalFilm")}</button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TRACE */}
            {tab === "trace" && (
              <AgentTrace runs={runs} agentHealth={agentHealth} partnerHealth={partnerHealth} />
            )}

          </motion.div>
        </AnimatePresence>
      </main>

      {/* mobile bottom nav */}
      <nav className="sm:hidden fixed bottom-0 inset-x-0 z-40 grid grid-cols-5 bg-lumiere-surface/95 backdrop-blur-xl border-t border-white/10">
        {TABS.map((tb) => (
          <button key={tb.id} data-testid={`mtab-${tb.id}`} onClick={() => setTab(tb.id)}
            className={`flex flex-col items-center gap-1 py-3 transition-colors duration-300 ${tab === tb.id ? "text-lumiere-orange" : "text-zinc-500"}`}>
            <tb.icon size={18} />
            <span className="font-mono text-[0.55rem] uppercase tracking-wider">{t(tb.id)}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
