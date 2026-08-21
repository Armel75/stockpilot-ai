import { useQuery } from "@tanstack/react-query";
import { TrendingUp } from "lucide-react";
import { getForecasts } from "@/api/client";
import Card, { CardHeader } from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import ForecastChart from "@/components/pilotage/ForecastChart";
import FreshnessBanner from "@/components/ui/FreshnessBanner";

const nf = new Intl.NumberFormat("fr-FR");

export default function Forecasts() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["forecasts", "all"],
    queryFn: () => getForecasts(undefined, 20),
  });

  if (isLoading) return <Spinner label="Chargement des prévisions…" />;
  if (isError || !data || data.length === 0) {
    return (
      <EmptyState
        title="Aucune prévision disponible"
        description="Lancez une analyse via « Générer le point » pour calculer la demande des 30 prochains jours."
        icon={<TrendingUp className="h-8 w-8" />}
      />
    );
  }

  return (
    <div className="space-y-4 max-w-6xl">
      <FreshnessBanner />

      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Demande prévue — 30 jours
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Top {data.length} par volume prévu · fourchette à 80 % de confiance · détail complet dans
            « Produits »
          </p>
        </div>
        <span className="text-xs text-slate-500">{data.length} produits affichés</span>
      </div>

      {data.map((f) => {
        const total = f.points.reduce((s, p) => s + p.mid, 0);
        const low = f.points.reduce((s, p) => s + p.low, 0);
        const high = f.points.reduce((s, p) => s + p.high, 0);
        return (
          <Card key={f.product_ref}>
            <CardHeader
              title={`${f.product_name} — ${f.product_ref}`}
              subtitle={`Fourchette à 80 % de confiance : ${nf.format(Math.round(low))} – ${nf.format(Math.round(high))} unités sur ${f.horizon_days} jours`}
              right={
                <span className="text-sm font-bold text-indigo-300 tabular-nums">
                  {nf.format(Math.round(total))} unités
                </span>
              }
            />
            <div className="px-5 pb-5">
              <ForecastChart series={f} />
            </div>
          </Card>
        );
      })}
    </div>
  );
}
