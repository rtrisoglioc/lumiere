import { useState } from "react";
import { Trash2, RotateCcw, AlertTriangle, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { bl } from "@/lib/bilingual";

export function MediaActions({ asset, onDone, lang }) {
  const [dialog, setDialog] = useState(null); // {mode:'trash'|'permanent', impact}
  const [busy, setBusy] = useState(false);
  const [force, setForce] = useState(false);
  const trashed = asset.status === "trashed";

  const openTrash = async () => {
    setBusy(true);
    try {
      const r = await api.get(`/media/${asset.id}/impact`);
      setDialog({ mode: "trash", impact: r.data });
    } catch { setDialog({ mode: "trash", impact: null }); } finally { setBusy(false); }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      if (dialog.mode === "permanent") {
        await api.delete(`/media/${asset.id}?permanent=true&confirm=true${force ? "&force=true" : ""}`);
        toast.success(lang === "es" ? "Eliminado permanentemente" : "Permanently deleted");
      } else {
        await api.delete(`/media/${asset.id}`);
        toast.success(lang === "es" ? "Movido a la papelera" : "Moved to Trash");
      }
      setDialog(null); setForce(false); onDone?.();
    } catch (e) {
      if (e?.response?.data?.detail === "in_use_requires_force") {
        setForce(true);
        toast.warning(lang === "es"
          ? "Este clip se usa en un corte. Se romperá ese corte — confirma para forzar."
          : "This clip is used in a cut. That cut will break — confirm to force.");
      } else { toast.error("Failed"); }
    } finally { setBusy(false); }
  };

  const restore = async () => {
    setBusy(true);
    try { await api.post(`/media/${asset.id}/restore`); toast.success(lang === "es" ? "Restaurado" : "Restored"); onDone?.(); }
    catch { toast.error("Failed"); } finally { setBusy(false); }
  };

  return (
    <div className="flex items-center gap-2" data-testid={`media-actions-${asset.id}`}>
      {trashed ? (
        <>
          <button data-testid={`media-restore-${asset.id}`} onClick={restore} disabled={busy}
            className="inline-flex items-center gap-1 font-mono text-[0.6rem] uppercase tracking-widest text-emerald-400 border border-emerald-400/30 px-2 py-1 hover:bg-emerald-400/10 transition-colors">
            <RotateCcw size={11} /> {lang === "es" ? "Restaurar" : "Restore"}
          </button>
          <button data-testid={`media-delete-perm-${asset.id}`} onClick={() => setDialog({ mode: "permanent" })} disabled={busy}
            className="inline-flex items-center gap-1 font-mono text-[0.6rem] uppercase tracking-widest text-red-400 border border-red-400/30 px-2 py-1 hover:bg-red-400/10 transition-colors">
            <Trash2 size={11} /> {lang === "es" ? "Eliminar" : "Delete"}
          </button>
        </>
      ) : (
        <button data-testid={`media-trash-${asset.id}`} onClick={openTrash} disabled={busy}
          className="inline-flex items-center gap-1 font-mono text-[0.6rem] uppercase tracking-widest text-zinc-400 border border-white/15 px-2 py-1 hover:border-red-400/40 hover:text-red-400 transition-colors">
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />} {lang === "es" ? "Papelera" : "Trash"}
        </button>
      )}

      {dialog && (
        <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={() => !busy && setDialog(null)}>
          <div className="bg-lumiere-surface border border-white/15 max-w-md w-full p-6" onClick={(e) => e.stopPropagation()} data-testid="media-delete-dialog">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-amber-400">
                <AlertTriangle size={18} />
                <span className="font-mono text-xs uppercase tracking-widest">
                  {dialog.mode === "permanent"
                    ? (lang === "es" ? "Eliminar permanentemente" : "Delete permanently")
                    : (lang === "es" ? "Mover a la papelera" : "Move to Trash")}
                </span>
              </div>
              <button onClick={() => setDialog(null)} className="text-zinc-500 hover:text-white"><X size={16} /></button>
            </div>
            <p className="text-sm text-zinc-300 mt-4">
              {dialog.mode === "permanent"
                ? (lang === "es"
                  ? "Esta acción es irreversible. El archivo original se borrará para siempre."
                  : "This is irreversible. The original file will be permanently removed.")
                : (dialog.impact ? bl(dialog.impact.message, lang)
                  : (lang === "es" ? "Se moverá a la papelera y se excluirá del análisis." : "It will move to Trash and be excluded from analysis."))}
            </p>
            {dialog.mode === "trash" && dialog.impact?.beats_at_risk?.length > 0 && (
              <p className="text-xs text-amber-400 mt-2 font-mono">
                {lang === "es" ? "Creará una toma faltante en la historia." : "This will create a missing shot in the story."}
              </p>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setDialog(null)} disabled={busy}
                className="px-4 py-2 font-mono text-xs uppercase tracking-widest text-zinc-400 border border-white/15 hover:text-white">
                {lang === "es" ? "Cancelar" : "Cancel"}
              </button>
              <button data-testid="media-confirm-delete" onClick={confirm} disabled={busy}
                className={`inline-flex items-center gap-2 px-4 py-2 font-mono text-xs uppercase tracking-widest text-white transition-colors ${dialog.mode === "permanent" ? "bg-red-600 hover:bg-red-700" : "bg-amber-600 hover:bg-amber-700"}`}>
                {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                {force ? (lang === "es" ? "Forzar borrado" : "Force delete")
                  : dialog.mode === "permanent" ? (lang === "es" ? "Eliminar" : "Delete") : (lang === "es" ? "A papelera" : "To Trash")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
