import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { LanguageToggle } from "@/components/LanguageToggle";

export default function Login() {
  const { user, loading, login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) navigate("/studio", { replace: true });
  }, [user, loading, navigate]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-lumiere-base">
      <div
        className="absolute inset-0 opacity-30 bg-cover bg-center"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1478720568477-152d9b164e26?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-lumiere-base via-lumiere-base/80 to-lumiere-base/40" />

      <div className="relative z-10 flex flex-col min-h-screen">
        <div className="flex items-center justify-between px-6 sm:px-10 py-6">
          <span className="font-mono text-xs tracking-[0.3em] text-zinc-400">LUMIÈRE / v1</span>
          <LanguageToggle />
        </div>

        <div className="flex-1 flex flex-col justify-center px-6 sm:px-16 max-w-4xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="label-mono mb-6 text-lumiere-orange"
          >
            Agentic Experience Studio
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.1 }}
            className="font-display text-4xl sm:text-6xl lg:text-7xl font-black leading-[0.95] tracking-tight text-white"
          >
            {t("tagline")}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.35 }}
            className="mt-6 text-base sm:text-lg text-zinc-400 max-w-xl leading-relaxed"
          >
            {t("subtitle")}
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.5 }}
            className="mt-10"
          >
            <button
              data-testid="enter-studio-button"
              onClick={login}
              className="group inline-flex items-center gap-3 bg-lumiere-orange hover:bg-lumiere-orangeHover text-white px-7 py-3.5 font-mono text-sm uppercase tracking-widest transition-colors duration-300 pulse-orange"
            >
              {t("signInGoogle")}
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform duration-300" />
            </button>
          </motion.div>
        </div>

        <div className="px-6 sm:px-16 py-8 font-mono text-[0.65rem] text-zinc-600 tracking-wider">
          INTENT → PLAN → DIRECT → CAPTURE → UNDERSTAND → EVALUATE → GET THE SHOT → EDIT → FINAL FILM
        </div>
      </div>
    </div>
  );
}
