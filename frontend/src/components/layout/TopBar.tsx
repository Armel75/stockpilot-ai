import { useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Play, Sparkles } from "lucide-react";
import clsx from "clsx";
import { getHealth } from "@/api/client";
import { useAgentRun } from "@/hooks/useAgentRun";

const TITLES: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Pilotage", subtitle: "Le point de situation de l'agent — affirmations priorisées" },
  "/previsions": { title: "Prévisions", subtitle: "Demande attendue sur les 30 prochains jours" },
  "/produits": { title: "Produits", subtitle: "Catalogue, stocks et signaux ouverts" },
  "/precision": { title: "Précision", subtitle: "Prévision vs réalité — la confiance de l'agent" },
  "/systeme": { title: "Système", subtitle: "Santé, ingestion SAGE X3 et exécution" },
};

export default function TopBar() {
  const { pathname } = useLocation();
  const meta = TITLES[pathname] ?? TITLES["/"];

  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealth, staleTime: 60_000 });
  const { start, isRunning, result, error } = useAgentRun();

  return (
    <header className="sticky top-0 z-20 border-b border-ink-700/60 bg-ink-950/80 backdrop-blur px-6 lg:px-8 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-white">{meta.title}</h1>
          <p className="text-xs text-slate-400">{meta.subtitle}</p>
        </div>

        <div className="flex items-center gap-3">
          {health?.data_date && (
            <span
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium",
                health.last_ingestion === "success"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-300"
              )}
            >
              {health.last_ingestion === "success" ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5" />
              )}
              Données du {new Date(health.data_date).toLocaleDateString("fr-FR")}
            </span>
          )}

          {health?.deepseek_configured && (
            <span className="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-2.5 py-1 text-[11px] font-medium text-indigo-300">
              <Sparkles className="h-3.5 w-3.5" />
              DeepSeek actif
            </span>
          )}

          <button className="btn-primary" onClick={() => start()} disabled={isRunning}>
            {isRunning ? (
              <>
                <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Analyse en cours…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Générer le point
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs text-rose-300">
          ✗ Échec de l'analyse : {error}
        </div>
      )}

      {result && !error && (
        <div className="mt-3 rounded-xl border border-ink-700 bg-ink-850 px-4 py-2.5 text-xs text-slate-300 flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-semibold text-white">
            {result.status === "success" ? "✓ Point généré" : "✗ Échec"}
          </span>
          <span>{result.message}</span>
          {result.data_source && <span className="text-slate-500">Source : {result.data_source}</span>}
          <span className="text-slate-500">
            {result.nb_products} produits · {result.nb_forecast} prévisions · {result.nb_signals} signaux ·{" "}
            {result.nb_assertions} affirmations
            {result.llm_used ? " · LLM" : " · règles"}
          </span>
        </div>
      )}
    </header>
  );
}
