import { useEffect, useState } from "react";
import { Check, Star } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/i18n";
import { bl } from "@/lib/bilingual";
import { Header } from "@/components/Header";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";

export default function Pricing() {
  const { t, lang } = useI18n();
  const [data, setData] = useState(null);
  const [cycle, setCycle] = useState("monthly");
  const [current, setCurrent] = useState("free");
  const [busy, setBusy] = useState(null);

  const load = async () => {
    try { const r = await api.get("/pricing/plans"); setData(r.data); setCurrent(r.data.current_plan); } catch { /* */ }
  };
  useEffect(() => { load(); }, []);

  const choose = async (planId) => {
    setBusy(planId);
    try {
      await api.post("/account/plan", { plan: planId });
      setCurrent(planId);
      toast.success(t("currentPlanBadge"));
    } catch { toast.error("Failed"); }
    finally { setBusy(null); }
  };

  const plans = data?.plans || [];

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <main className="px-4 sm:px-8 lg:px-16 py-12 max-w-6xl mx-auto" data-testid="pricing-page">
        <div className="text-center max-w-2xl mx-auto">
          <p className="label-mono text-lumiere-ink/50 mb-2">{t("pricing")}</p>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight">{t("choosePlan")}</h1>
          <p className="mt-4 text-lumiere-ink/60 italic">{t("positioning")}</p>

          {/* cycle toggle */}
          <div className="inline-flex items-center mt-8 border border-black/15 rounded-full p-1" data-testid="cycle-toggle">
            {["monthly", "yearly"].map((c) => (
              <button key={c} data-testid={`cycle-${c}`} onClick={() => setCycle(c)}
                className={`px-5 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors ${cycle === c ? "bg-lumiere-ink text-lumiere-ivory" : "text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
                {t(c)}
              </button>
            ))}
            {cycle === "yearly" && <span className="ml-2 mr-2 font-mono text-[0.6rem] text-lumiere-sage uppercase">{t("save2Months")}</span>}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-12 items-start">
          {plans.map((p) => {
            const price = cycle === "monthly" ? p.price.monthly : p.price.yearly;
            const isCurrent = current === p.id;
            const rec = p.recommended;
            return (
              <div key={p.id} data-testid={`plan-${p.id}`}
                className={`relative rounded-2xl p-8 bg-lumiere-warm border transition-transform hover:-translate-y-1 ${rec ? "border-lumiere-gold shadow-[0_10px_40px_rgba(214,168,95,0.2)] md:-mt-4 md:mb-4" : "border-black/10"}`}>
                {rec && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 bg-lumiere-gold text-lumiere-ink px-3 py-1 rounded-full font-mono text-[0.6rem] uppercase tracking-widest">
                    <Star size={11} /> {t("recommended")}
                  </span>
                )}
                <h3 className="font-display text-2xl font-bold">{p.name}</h3>
                <p className="text-sm text-lumiere-ink/60 mt-2 min-h-[3rem]">{bl(p.tagline, lang)}</p>
                <div className="mt-5 flex items-end gap-1">
                  <span className="font-display text-4xl font-black">{price === 0 ? t("freeLabel") : `$${price}`}</span>
                  {price !== 0 && <span className="font-mono text-sm text-lumiere-ink/50 mb-1">{cycle === "monthly" ? t("perMonth") : t("perYear")}</span>}
                </div>
                <ul className="mt-6 space-y-3">
                  {p.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Check size={16} className="text-lumiere-sage mt-0.5 shrink-0" /> <span>{bl(f, lang)}</span>
                    </li>
                  ))}
                </ul>
                {isCurrent ? (
                  <div data-testid={`current-${p.id}`} className="mt-8 w-full text-center border border-lumiere-gold text-lumiere-ink py-3 rounded-full font-mono text-xs uppercase tracking-widest">
                    {t("currentPlanBadge")}
                  </div>
                ) : (
                  <button data-testid={`select-${p.id}`} onClick={() => choose(p.id)} disabled={busy === p.id}
                    className={`mt-8 w-full py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors ${rec ? "bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink" : "bg-lumiere-ink hover:bg-lumiere-ink/85 text-lumiere-ivory"}`}>
                    {busy === p.id ? "…" : (p.id === "free" ? t("selectPlan") : t("upgrade"))}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* FAQ */}
        {data?.faq && (
          <div className="max-w-2xl mx-auto mt-20">
            <h2 className="font-display text-3xl font-bold text-center mb-6">{t("faqTitle")}</h2>
            <Accordion type="single" collapsible className="w-full">
              {data.faq.map((f, i) => (
                <AccordionItem key={i} value={`faq-${i}`} className="border-black/10">
                  <AccordionTrigger data-testid={`faq-${i}`} className="font-display text-lg text-left hover:no-underline">{bl(f.q, lang)}</AccordionTrigger>
                  <AccordionContent className="text-lumiere-ink/60">{bl(f.a, lang)}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        )}
      </main>
    </div>
  );
}
