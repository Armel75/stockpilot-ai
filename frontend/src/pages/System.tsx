import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Database, Play, Sparkles, Server } from "lucide-react";
import clsx from "clsx";
import { getHealth, getIngestionLogs } from "@/api/client";
import { useAgentRun } from "@/hooks/useAgentRun";
import Card, { CardHeader } from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import FreshnessBanner from "@/components/ui/FreshnessBanner";

export default function System() {
  const [mode, setMode] = useState("auto");

  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 15_000 });
  const { data: logs } = useQuery({ queryKey: ["ingestion-logs"], queryFn: getIngestionLogs, refetchInterval: 15_000 });
  const { start, isRunning, result, error } = useAgentRun();

  return (
    <div className="space-y-6 max-w-6xl">
      <FreshnessBanner />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="API" value={health?.status ?? "—"} accent="text-emerald-400" icon={<Activity className="h-4 w-4" />} />
        <KpiCard label="Produits" value={String(health?.nb_products ?? 0)} icon={<Database className="h-4 w-4" />} />
        <KpiCard label="Lignes de ventes" value={String(health?.nb_sales ?? 0)} icon={<Database className="h-4 w-4" />} />
        <KpiCard
          label="DeepSeek"
          value={health?.deepseek_configured ? "Configuré" : "Non configuré"}
          accent={health?.deepseek_configured ? "text-emerald-400" : "text-amber-400"}
          icon={<Sparkles className="h-4 w-4" />}
        />
      </div>

      <Card>
        <CardHeader
          title="Exécuter l'agent"
          subtitle="Relance manuelle de la boucle complète : ingestion → prévisions → signaux → narration"
        />
        <div className="px-5 pb-5 flex flex-wrap items-center gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="rounded-xl border border-ink-700 bg-ink-850 px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500/60"
          >
            <option value="auto">Auto (X3 puis démo)</option>
            <option value="sagex3">SAGE X3 uniquement</option>
            <option value="seed">Données de démonstration</option>
          </select>
          <button className="btn-primary" onClick={() => start(mode)} disabled={isRunning}>
            {isRunning ? (
              <>
                <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Exécution…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Lancer l'agent
              </>
            )}
          </button>
          <span className="text-xs text-slate-500">
            Mode ingestion courant : {health?.ingestion_mode ?? "—"} · Données du{" "}
            {health?.data_date ? new Date(health.data_date).toLocaleDateString("fr-FR") : "—"}
          </span>
        </div>
        {error && (
          <div className="mx-5 mb-5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-300">
            ✗ {error}
          </div>
        )}
        {result && !error && (
          <div className="mx-5 mb-5 rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 text-xs text-slate-300">
            <p className="font-semibold text-white">
              {result.status === "success" ? "✓" : "✗"} {result.message}
            </p>
            <p className="mt-1 text-slate-500">
              Source : {result.data_source} · {result.nb_products} produits · {result.nb_forecast} prévisions ·{" "}
              {result.nb_signals} signaux · {result.nb_assertions} affirmations ·{" "}
              {result.llm_used ? "narration LLM" : "narration règles"} · {result.duration_seconds}s
            </p>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Journal d'ingestion" subtitle="Historique des chargements de données (SAGE X3 / démo)" right={<Server className="h-4 w-4 text-slate-500" />} />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-700 text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3">Source</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3 text-right">Lignes</th>
                <th className="px-4 py-3">Message</th>
                <th className="px-5 py-3 text-right">Début</th>
              </tr>
            </thead>
            <tbody>
              {logs?.map((l) => (
                <tr key={l.id} className="border-b border-ink-700/50 last:border-0">
                  <td className="px-5 py-3 text-slate-300">{l.source}</td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        "inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold",
                        l.status === "success"
                          ? "bg-emerald-500/15 text-emerald-300"
                          : l.status === "error"
                            ? "bg-rose-500/15 text-rose-300"
                            : "bg-sky-500/15 text-sky-300"
                      )}
                    >
                      {l.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-400">{l.rows_loaded}</td>
                  <td className="px-4 py-3 text-slate-400 max-w-md truncate">{l.message}</td>
                  <td className="px-5 py-3 text-right text-slate-500 tabular-nums">
                    {new Date(l.started_at).toLocaleTimeString("fr-FR")}
                  </td>
                </tr>
              ))}
              {(!logs || logs.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-500">
                    Aucune ingestion enregistrée.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
