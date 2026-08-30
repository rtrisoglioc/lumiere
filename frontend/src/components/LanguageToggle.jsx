import { useI18n } from "@/i18n";

export function LanguageToggle({ dark = false }) {
  const { lang, setLang } = useI18n();
  const border = dark ? "border-white/15" : "border-black/15";
  const idle = dark ? "text-lumiere-ivory/50 hover:text-lumiere-ivory" : "text-lumiere-ink/50 hover:text-lumiere-ink";
  return (
    <div className={`inline-flex items-center border ${border} font-mono text-xs rounded-full overflow-hidden`} data-testid="language-toggle">
      {["EN", "ES"].map((l) => {
        const code = l.toLowerCase();
        const active = lang === code;
        return (
          <button
            key={l}
            data-testid={`lang-${code}`}
            onClick={() => { setLang(code); localStorage.setItem("lumiere_lang", code); }}
            className={`px-2.5 py-1 transition-colors duration-300 ${active ? "bg-lumiere-gold text-lumiere-ink" : idle}`}
          >
            {l}
          </button>
        );
      })}
    </div>
  );
}
