import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgePercent,
  Clock,
  PackageX,
  RotateCcw,
  ShoppingCart,
  Sparkles,
} from "lucide-react";
import { getForecasts, getPilotage } from "@/api/client";
import KpiCard from "@/components/ui/KpiCard";
import Card, { CardHeader } from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import AssertionCard from "@/components/pilotage/AssertionCard";
import DecisionCard from "@/components/pilotage/DecisionCard";
import ForecastChart from "@/components/pilotage/ForecastChart";
import FreshnessBanner from "@/components/ui/FreshnessBanner";

const nf = new Intl.NumberFormat("fr-FR");

export default function Pilotage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["pilotage"],
    queryFn: getPilotage,
  });

  const { data: forecasts } = useQuery({
    queryKey: ["forecasts", "top"],
    queryFn: () => getForecasts(undefined, 4),
    enabled: !!data,
  });

  const [showAll, setShowAll] = useState(false);

  if (isLoading) return <Spinner label="Analyse de la situation…" />;
  if (isError || !data) {
    return (
      <EmptyState
        title="Impossible de charger le point de situation"
        description="Vérifiez que le backend est démarré, puis cliquez sur « Générer le point »."
        icon={<AlertTriangle className="h-8 w-8" />}
      />
    );
  }

  const k = data.kpis;
  const visibleAssertions = showAll ? data.assertions : data.assertions.slice(0, 6);

  return (
    <div className="space-y-6 max-w-7xl">
      <FreshnessBanner />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          label="Réappro. suggérés"
          value={String(k.nb_reappro)}
          icon={<ShoppingCart className="h-4 w-4" />}
          accent={k.nb_reappro > 0 ? "text-sky-400" : "text-emerald-400"}
          hint={`${nf.format(k.nb_products)} produits suivis`}
          title="Produits à réapprovisionner"
        />
        <KpiCard
          label="Opportunités"
          value={String(k.nb_opportunities)}
          icon={<BadgePercent className="h-4 w-4" />}
          accent={k.nb_opportunities > 0 ? "text-violet-400" : "text-emerald-400"}
          hint="Produits à pousser commercialement"
          title="Produits à pousser commercialement (marge élevée)"
        />
        <KpiCard
          label="Ruptures"
          value={String(k.nb_ruptures)}
          icon={<AlertTriangle className="h-4 w-4" />}
          accent={k.nb_ruptures > 0 ? "text-rose-400" : "text-emerald-400"}
        />
        <KpiCard
          label="Surstocks"
          value={String(k.nb_overstock)}
          icon={<PackageX className="h-4 w-4" />}
          accent={k.nb_overstock > 0 ? "text-amber-400" : "text-emerald-400"}
        />
        <KpiCard
          label="Stocks dormants"
          value={String(k.nb_dormant)}
          icon={<RotateCcw className="h-4 w-4" />}
          title="Produits sans vente depuis 60 jours"
        />
        <KpiCard
          label="Autonomie du stock"
          value={k.avg_coverage_days > 0 ? `${nf.format(Math.round(k.avg_coverage_days))} j` : "—"}
          icon={<Clock className="h-4 w-4" />}
          title="Jours de vente couverts par le stock actuel"
          sub={
            <span className="text-xs text-slate-500">
              {data.freshness.data_date
                ? `Stock au ${new Date(data.freshness.data_date).toLocaleDateString("fr-FR")}`
                : "Données non disponibles"}
            </span>
          }
        />
      </div>

      {/* Résumé de l'agent */}
      <Card className="p-5">
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0">
            <Sparkles className="h-4.5 w-4.5 h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              Point de situation · {new Date(data.report_date).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
            </p>
            <p className="mt-1 text-sm text-slate-200 leading-relaxed">{data.summary}</p>
          </div>
        </div>
      </Card>

      {/* Décisions du jour — synthèse exécutive déterministe */}
      {data.decisions.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Décisions du jour
            </h2>
            <span className="text-xs text-slate-500">Priorités automatiques · {data.decisions.length}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.decisions.map((d, i) => (
              <DecisionCard key={`${d.product_ref}-${d.action_type}-${i}`} decision={d} />
            ))}
          </div>
        </section>
      )}

      {/* Affirmations */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Affirmations de l'agent
          </h2>
          <span className="text-xs text-slate-500">
            {data.assertions.length} affirmation{data.assertions.length > 1 ? "s" : ""}
          </span>
        </div>
        {data.assertions.length === 0 ? (
          <EmptyState
            title="Aucune affirmation pour le moment"
            description="Lancez une analyse via « Générer le point » pour obtenir les priorités du jour."
          />
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {visibleAssertions.map((a) => (
                <AssertionCard key={a.id} assertion={a} />
              ))}
            </div>
            {!showAll && data.assertions.length > 6 && (
              <div className="mt-4 text-center">
                <button onClick={() => setShowAll(true)} className="btn-ghost">
                  Voir les {data.assertions.length - 6} autres affirmations
                </button>
              </div>
            )}
          </>
        )}
      </section>

      {/* Prévisions top produits */}
      {forecasts && forecasts.length > 0 && (
        <section>
          <CardHeader
            title="Demande prévue — 30 jours"
            subtitle="Top produits par volume prévu (fourchette 80 % de confiance)"
            right={<ShoppingCart className="h-4 w-4 text-slate-500" />}
          />
          <Card className="mx-5 mb-5 space-y-4">
            {forecasts.map((f) => (
              <div key={f.product_ref}>
                <div className="mb-1 flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-200">
                    {f.product_name} <span className="text-slate-500">· {f.product_ref}</span>
                  </p>
                  <p className="text-xs text-slate-400 tabular-nums">
                    ≈ {nf.format(Math.round(f.points.reduce((s, p) => s + p.mid, 0)))} unités
                  </p>
                </div>
                <ForecastChart series={f} />
              </div>
            ))}
          </Card>
        </section>
      )}
    </div>
  );
}
