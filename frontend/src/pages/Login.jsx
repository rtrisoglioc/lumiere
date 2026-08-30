import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { LanguageToggle } from "@/components/LanguageToggle";
import { LoopStrip } from "@/components/LoopStrip";

export default function Login() {
  const { user, loading, login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) navigate("/studio", { replace: true });
  }, [user, loading, navigate]);

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink flex flex-col">
      <div className="flex items-center justify-between px-6 sm:px-12 py-6">
        <span className="font-display text-xl font-black tracking-tight">LUMIÈRE</span>
        <LanguageToggle />
      </div>

      <div className="flex-1 grid lg:grid-cols-2 gap-8 items-center px-6 sm:px-12 lg:px-16 max-w-7xl mx-auto w-full">
        <div>
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="label-mono text-lumiere-ink/50 mb-5">Agentic Experience Studio</motion.p>
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.1 }}
            className="font-display text-5xl sm:text-6xl lg:text-7xl font-black leading-[0.92] tracking-tight">
            {t("tagline")}
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.3 }}
            className="mt-6 text-lg text-lumiere-ink/60 max-w-lg">{t("subtitle")}</motion.p>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.4 }}
            className="mt-3 text-base text-lumiere-ink/50 max-w-lg italic">{t("positioning")}</motion.p>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.5 }} className="mt-10">
            <button data-testid="enter-studio-button" onClick={login}
              className="group inline-flex items-center gap-3 bg-lumiere-ink hover:bg-lumiere-ink/85 text-lumiere-ivory px-7 py-3.5 rounded-full font-mono text-sm uppercase tracking-widest transition-colors">
              {t("signInGoogle")}
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform duration-300" />
            </button>
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }}
          className="relative rounded-3xl overflow-hidden border border-black/10 aspect-[4/5] hidden lg:block">
          <img src="https://images.pexels.com/photos/34033016/pexels-photo-34033016.jpeg?auto=compress&cs=tinysrgb&w=1200"
            alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-lumiere-ink/40 to-transparent" />
        </motion.div>
      </div>

      <div className="mt-8">
        <LoopStrip />
      </div>
    </div>
  );
}
