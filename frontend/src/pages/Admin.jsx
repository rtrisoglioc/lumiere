import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Save, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Header } from "@/components/Header";

const TABS = ["overview", "plans", "users", "video", "social"];
const TAB_LABEL = {
  overview: { en: "Overview", es: "Resumen" }, plans: { en: "Plans & Pricing", es: "Planes y Precios" },
  users: { en: "Users", es: "Usuarios" }, video: { en: "Video Jobs", es: "Jobs de Video" }, social: { en: "Social Posts", es: "Posts Sociales" },
};

export default function Admin() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [plans, setPlans] = useState([]);
  const [users, setUsers] = useState([]);
  const [videoJobs, setVideoJobs] = useState([]);
  const [socialPosts, setSocialPosts] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!loading && (!user || !user.is_admin)) navigate("/studio", { replace: true });
  }, [user, loading, navigate]);

  const loadAll = async () => {
    try {
      const [o, p, u, v, s] = await Promise.all([
        api.get("/admin/overview"), api.get("/admin/plans"), api.get("/admin/users"),
        api.get("/admin/video-jobs"), api.get("/admin/social-posts"),
      ]);
      setOverview(o.data); setPlans(p.data.plans); setUsers(u.data);
      setVideoJobs(v.data); setSocialPosts(s.data);
    } catch { toast.error("Load failed"); }
  };
  useEffect(() => { if (user?.is_admin) loadAll(); }, [user]);

  const updPlan = (i, path, val) => {
    setPlans((ps) => ps.map((p, idx) => {
      if (idx !== i) return p;
      const np = JSON.parse(JSON.stringify(p));
      const keys = path.split(".");
      let o = np; for (let k = 0; k < keys.length - 1; k++) o = o[keys[k]];
      o[keys[keys.length - 1]] = val;
      return np;
    }));
  };

  const savePlans = async () => {
    setSaving(true);
    try { await api.put("/admin/plans", { plans }); toast.success("Plans saved"); }
    catch { toast.error("Save failed"); } finally { setSaving(false); }
  };

  const changeUserPlan = async (uid, plan) => {
    try { await api.post(`/admin/users/${uid}/plan`, { plan }); toast.success("Updated"); loadAll(); }
    catch { toast.error("Failed"); }
  };

  if (loading || !user?.is_admin) return <div className="min-h-screen bg-lumiere-ink" />;

  return (
    <div className="min-h-screen bg-lumiere-ink text-lumiere-ivory">
      <Header dark />
      <main className="px-4 sm:px-8 lg:px-16 py-10 max-w-7xl mx-auto" data-testid="admin-page">
        <div className="flex items-center gap-3">
          <ShieldCheck size={22} className="text-lumiere-gold" />
          <h1 className="font-display text-3xl sm:text-4xl font-black tracking-tight">Admin</h1>
        </div>
        <p className="font-mono text-xs text-lumiere-ivory/40 mt-1">{user.email}</p>

        <div className="flex flex-wrap gap-2 mt-8 border-b border-lumiere-ivory/10 pb-4">
          {TABS.map((tb) => (
            <button key={tb} data-testid={`admin-tab-${tb}`} onClick={() => setTab(tb)}
              className={`px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors ${tab === tb ? "bg-lumiere-gold text-lumiere-ink" : "text-lumiere-ivory/50 hover:text-lumiere-ivory"}`}>
              {TAB_LABEL[tb].en}
            </button>
          ))}
        </div>

        {!overview ? (
          <div className="mt-10"><Loader2 className="animate-spin text-lumiere-gold" /></div>
        ) : (
          <div className="mt-8">
            {tab === "overview" && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="admin-overview">
                {[["Users", overview.users], ["Experiences", overview.experiences], ["Cuts", overview.cuts],
                  ["Video jobs", overview.video_jobs], ["Videos done", overview.video_done], ["Videos failed", overview.video_failed],
                  ["Social posts", overview.social_posts]].map(([label, val]) => (
                  <div key={label} className="rounded-2xl border border-lumiere-ivory/10 bg-lumiere-surface p-6">
                    <p className="font-mono text-3xl text-lumiere-gold">{val}</p>
                    <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ivory/40 mt-1">{label}</p>
                  </div>
                ))}
              </div>
            )}

            {tab === "plans" && (
              <div>
                <div className="flex justify-end mb-4">
                  <button data-testid="admin-save-plans" onClick={savePlans} disabled={saving}
                    className="inline-flex items-center gap-2 bg-lumiere-gold text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest">
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
                  </button>
                </div>
                <div className="grid md:grid-cols-3 gap-4">
                  {plans.map((p, i) => (
                    <div key={p.id} data-testid={`admin-plan-${p.id}`} className="rounded-2xl border border-lumiere-ivory/10 bg-lumiere-surface p-6 space-y-3">
                      <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-gold">{p.id}</p>
                      <Field label="Name" value={p.name} onChange={(v) => updPlan(i, "name", v)} />
                      <div className="grid grid-cols-2 gap-2">
                        <Field label="$/mo" type="number" value={p.price.monthly} onChange={(v) => updPlan(i, "price.monthly", Number(v))} />
                        <Field label="$/yr" type="number" value={p.price.yearly} onChange={(v) => updPlan(i, "price.yearly", Number(v))} />
                      </div>
                      <Field label="Experiences" type="number" value={p.limits.experiences} onChange={(v) => updPlan(i, "limits.experiences", Number(v))} />
                      <Field label="Cuts" type="number" value={p.limits.cuts} onChange={(v) => updPlan(i, "limits.cuts", Number(v))} />
                      <Field label="Video quota / mo" type="number" value={p.limits.ai_generations} onChange={(v) => updPlan(i, "limits.ai_generations", Number(v))} />
                      <Toggle label="Video enabled" checked={p.entitlements?.video} onChange={(v) => updPlan(i, "entitlements.video", v)} testid={`admin-plan-${p.id}-video`} />
                      <Toggle label="Social Studio" checked={p.entitlements?.social} onChange={(v) => updPlan(i, "entitlements.social", v)} testid={`admin-plan-${p.id}-social`} />
                      <Toggle label="Recommended" checked={p.recommended} onChange={(v) => updPlan(i, "recommended", v)} testid={`admin-plan-${p.id}-rec`} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === "users" && (
              <div className="overflow-x-auto rounded-2xl border border-lumiere-ivory/10" data-testid="admin-users">
                <table className="w-full text-sm">
                  <thead><tr className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ivory/40 border-b border-lumiere-ivory/10">
                    <th className="text-left p-3">Email</th><th className="text-left p-3">Plan</th><th className="text-left p-3">Exp</th><th className="text-left p-3">Videos</th><th className="text-left p-3">Admin</th></tr></thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.user_id} className="border-b border-lumiere-ivory/5">
                        <td className="p-3">{u.email}</td>
                        <td className="p-3">
                          <select data-testid={`admin-user-plan-${u.user_id}`} value={u.plan} onChange={(e) => changeUserPlan(u.user_id, e.target.value)}
                            className="bg-lumiere-ink border border-lumiere-ivory/15 rounded-lg px-2 py-1 text-xs">
                            {plans.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
                          </select>
                        </td>
                        <td className="p-3 font-mono">{u.experiences}</td>
                        <td className="p-3 font-mono">{u.video_jobs}</td>
                        <td className="p-3">{u.is_admin ? <span className="text-lumiere-gold font-mono text-xs">✓</span> : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {tab === "video" && (
              <div className="overflow-x-auto rounded-2xl border border-lumiere-ivory/10" data-testid="admin-video-jobs">
                <table className="w-full text-sm">
                  <thead><tr className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ivory/40 border-b border-lumiere-ivory/10">
                    <th className="text-left p-3">Prompt</th><th className="text-left p-3">Status</th><th className="text-left p-3">Created</th></tr></thead>
                  <tbody>
                    {videoJobs.map((j) => (
                      <tr key={j.id} className="border-b border-lumiere-ivory/5">
                        <td className="p-3 max-w-md truncate">{j.prompt}</td>
                        <td className="p-3 font-mono text-xs">{j.status}</td>
                        <td className="p-3 font-mono text-xs text-lumiere-ivory/40">{(j.created_at || "").slice(0, 16)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {tab === "social" && (
              <div className="overflow-x-auto rounded-2xl border border-lumiere-ivory/10" data-testid="admin-social-posts">
                <table className="w-full text-sm">
                  <thead><tr className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ivory/40 border-b border-lumiere-ivory/10">
                    <th className="text-left p-3">Network</th><th className="text-left p-3">Status</th><th className="text-left p-3">Scheduled</th></tr></thead>
                  <tbody>
                    {socialPosts.map((s) => (
                      <tr key={s.id} className="border-b border-lumiere-ivory/5">
                        <td className="p-3 capitalize">{s.network}</td>
                        <td className="p-3 font-mono text-xs">{s.status}</td>
                        <td className="p-3 font-mono text-xs text-lumiere-ivory/40">{(s.scheduled_at || "").slice(0, 16)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }) {
  return (
    <div>
      <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ivory/40 block mb-1">{label}</label>
      <input type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)}
        className="w-full bg-lumiere-ink border border-lumiere-ivory/15 rounded-lg px-2 py-1.5 text-sm" />
    </div>
  );
}

function Toggle({ label, checked, onChange, testid }) {
  return (
    <button data-testid={testid} onClick={() => onChange(!checked)}
      className="flex items-center justify-between w-full text-sm">
      <span className="text-lumiere-ivory/70">{label}</span>
      <span className={`w-10 h-5 rounded-full transition-colors relative ${checked ? "bg-lumiere-gold" : "bg-lumiere-ivory/15"}`}>
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-lumiere-ink transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
      </span>
    </button>
  );
}
