export const bl = (f, lang = "en") => {
  if (!f) return "";
  if (typeof f === "string") return f;
  return f[lang] || f.en || f.es || "";
};
