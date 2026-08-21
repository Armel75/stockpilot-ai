import { useQuery } from "@tanstack/react-query";
import { Crosshair, Info } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAccuracyHistory, getAccuracyLatest } from "@/api/client";
import Card, { CardHeader } from "@/components/ui/Card";
import KpiCard from "@/components/ui/KpiCard";
import Spinner from "@/components/ui/Spinner";
import FreshnessBanner from "@/components/ui/FreshnessBanner";

function interpret(mape: number | null | undefined) {
  if (mape === null || mape === undefined) return { label: "En attente", cls: "text-slate-400" };
  if (mape < 10) return { label: "Excellente", cls: "text-emerald-400" };
  if (mape < 20) return { label: "Bonne", cls: "text-emerald-300" };
  if (mape < 30) return { label: "Acceptable", cls: "text-amber-300" };
  return { label: "À surveiller", cls: "text-rose-400" };
}

export default function Accuracy() {
  const { data: latest } = useQuery({ queryKey: ["accuracy", "latest"], queryFn: getAccuracyLatest });
  const { data: history, isLoading } = useQuery({ queryKey: ["accuracy", "history"], queryFn: getAccuracyHistory });

  const verdict = interpret(latest?.mape);

  return (
    <div className="space-y-6 max-w-6xl">
      <FreshnessBanner />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          label="Erreur moyenne (MAPE)"
          value={latest?.mape !== null && latest?.mape !== undefined ? `${latest.mape.toFixed(1)} %` : "—"}
          accent={verdict.cls}
          hint={latest?.score_date ? `Évalué le ${new Date(latest.score_date).toLocaleDateString("fr-FR")}` : undefined}
        />
        <KpiCard
          label="Biais"
          value={latest?.bias !== null && latest?.bias !== undefined ? `${latest.bias.toFixed(1)} %` : "—"}
          hint={
            latest?.bias !== null && latest?.bias !== undefined
              ? latest.bias > 0
                ? "Tendance à sur-prévoir"
                : "Tendance à sous-prévoir"
              : undefined
          }
          accent={latest && latest.bias !== null && latest.bias !== undefined && Math.abs(latest.bias) > 20 ? "text-amber-400" : "text-white"}
        />
        <KpiCard
          label="Fiabilité"
          value={verdict.label}
          accent={verdict.cls}
          hint={`${latest?.sample_size ?? 0} produits évalués`}
        />
      </div>

      {latest && !latest.has_score && (
        <div className="flex items-start gap-3 rounded-2xl border border-ink-700 bg-ink-850 px-4 py-3">
          <Info className="h-5 w-5 text-slate-400 mt-0.5 shrink-0" />
          <p className="text-sm text-slate-300">
            {latest.message ?? "Aucun score disponible pour le moment."} Le score apparaît automatiquement une fois
            les prévisions arrivées à échéance (30 jours).
          </p>
        </div>
      )}

      <Card>
        <CardHeader
          title="Historique de la précision"
          subtitle="Évolution de l'erreur moyenne (MAPE) semaine après semaine — la confiance de l'agent"
          right={<Crosshair className="h-4 w-4 text-slate-500" />}
        />
        <div className="px-5 pb-5">
          {isLoading ? (
            <Spinner />
          ) : history && history.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#1a2745" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="score_date"
                    tick={{ fill: "#64748b", fontSize: 10 }}
                    axisLine={{ stroke: "#1a2745" }}
                    tickLine={false}
                    tickFormatter={(v: string) => new Date(v).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })}
                  />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={40} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1a2745", borderRadius: 12, fontSize: 12 }}
                    labelStyle={{ color: "#94a3b8" }}
                  />
                  <Line type="monotone" dataKey="mape" stroke="#818cf8" strokeWidth={2} dot={{ r: 3, fill: "#818cf8" }} name="MAPE (%)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="py-10 text-center text-sm text-slate-500">Pas encore d'historique — revenez après la première évaluation.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
