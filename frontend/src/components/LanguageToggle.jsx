import { useI18n } from "@/i18n";

export function LanguageToggle() {
  const { lang, setLang } = useI18n();
  return (
    <div className="inline-flex items-center border border-white/15 font-mono text-xs" data-testid="language-toggle">
      {["EN", "ES"].map((l) => {
        const code = l.toLowerCase();
        const active = lang === code;
        return (
          <button
            key={l}
            data-testid={`lang-${code}`}
            onClick={() => { setLang(code); localStorage.setItem("lumiere_lang", code); }}
            className={`px-2.5 py-1 transition-colors duration-300 ${active ? "bg-lumiere-orange text-white" : "text-zinc-500 hover:text-white"}`}
          >
            {l}
          </button>
        );
      })}
    </div>
  );
}
