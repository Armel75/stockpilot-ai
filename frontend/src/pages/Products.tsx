import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Package, Search } from "lucide-react";
import clsx from "clsx";
import { getProducts } from "@/api/client";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import FreshnessBanner from "@/components/ui/FreshnessBanner";

const SIGNAL_LABELS: Record<string, { label: string; cls: string }> = {
  rupture: { label: "Rupture", cls: "bg-rose-500/15 text-rose-300 border-rose-500/40" },
  surstock: { label: "Surstock", cls: "bg-amber-500/15 text-amber-300 border-amber-500/40" },
  dormant: { label: "Dormant", cls: "bg-slate-500/15 text-slate-300 border-slate-500/40" },
  acceleration: { label: "Accél.", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40" },
  opportunite: { label: "Opportunité", cls: "bg-violet-500/15 text-violet-300 border-violet-500/40" },
  reappro: { label: "Réappro", cls: "bg-sky-500/15 text-sky-300 border-sky-500/40" },
};

export default function Products() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["products", q, category],
    queryFn: () => getProducts({ q: q || undefined, limit: 500 }),
    placeholderData: (prev) => prev,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    return category ? data.filter((p) => p.product.category === category) : data;
  }, [data, category]);

  const categories = useMemo(
    () => Array.from(new Set((data ?? []).map((p) => p.product.category).filter(Boolean) as string[])),
    [data]
  );

  if (isLoading) return <Spinner label="Chargement du catalogue…" />;

  return (
    <div className="space-y-4 max-w-7xl">
      <FreshnessBanner />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Rechercher un produit…"
            className="w-full rounded-xl border border-ink-700 bg-ink-850 pl-9 pr-3 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/60"
          />
        </div>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-xl border border-ink-700 bg-ink-850 px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/60"
        >
          <option value="">Toutes les catégories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="Aucun produit trouvé" icon={<Package className="h-8 w-8" />} />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-700 text-left text-[11px] uppercase tracking-wider text-slate-500">
                  <th className="px-5 py-3">Produit</th>
                  <th className="px-4 py-3">Catégorie</th>
                  <th className="px-4 py-3 text-right">Stock</th>
                  <th className="px-4 py-3 text-right">Ventes/j</th>
                  <th className="px-4 py-3 text-right">Couverture</th>
                  <th className="px-4 py-3 text-right">Marge</th>
                  <th className="px-5 py-3">Signaux</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => {
                  const cov = p.coverage_days;
                  const covCls =
                    cov === null
                      ? "text-slate-500"
                      : cov < 15
                        ? "text-rose-400 font-semibold"
                        : cov > 90
                          ? "text-amber-400 font-semibold"
                          : "text-emerald-400";
                  return (
                    <tr key={p.product.ref} className="border-b border-ink-700/50 last:border-0 hover:bg-ink-800/40">
                      <td className="px-5 py-3">
                        <p className="font-semibold text-slate-200">{p.product.name}</p>
                        <p className="text-[11px] text-slate-500">{p.product.ref}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{p.product.category ?? "—"}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {new Intl.NumberFormat("fr-FR").format(Math.round(p.stock))}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {p.daily_avg_30.toFixed(1)}
                      </td>
                      <td className={clsx("px-4 py-3 text-right tabular-nums", covCls)}>
                        {cov === null ? "—" : `${Math.round(cov)} j`}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {(p.product.margin_rate * 100).toFixed(0)} %
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1">
                          {p.open_signals.length === 0 && <span className="text-[11px] text-slate-600">—</span>}
                          {p.open_signals.map((s) => {
                            const meta = SIGNAL_LABELS[s];
                            return meta ? (
                              <span
                                key={s}
                                className={clsx(
                                  "inline-flex rounded-md border px-1.5 py-0.5 text-[10px] font-semibold",
                                  meta.cls
                                )}
                              >
                                {meta.label}
                              </span>
                            ) : null;
                          })}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
