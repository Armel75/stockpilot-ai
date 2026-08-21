export default function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-400">
      <div className="h-6 w-6 rounded-full border-2 border-ink-600 border-t-indigo-400 animate-spin" />
      <span className="text-sm">{label ?? "Chargement…"}</span>
    </div>
  );
}
