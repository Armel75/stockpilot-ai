import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgePercent,
  Check,
  Lightbulb,
  PackageX,
  RotateCcw,
  ShoppingCart,
  TrendingUp,
  X,
} from "lucide-react";
import clsx from "clsx";
import type { Assertion } from "@/types";
import { postFeedback } from "@/api/client";
import PriorityChip from "@/components/ui/PriorityChip";
import ConfidenceBar from "@/components/ui/ConfidenceBar";

const TYPE_META: Record<string, { icon: typeof AlertTriangle; label: string; color: string }> = {
  rupture: { icon: AlertTriangle, label: "Rupture de stock", color: "text-rose-400" },
  surstock: { icon: PackageX, label: "Surstock", color: "text-amber-400" },
  dormant: { icon: RotateCcw, label: "Stock dormant", color: "text-slate-400" },
  acceleration: { icon: TrendingUp, label: "Accélération des ventes", color: "text-emerald-400" },
  opportunite: { icon: BadgePercent, label: "Opportunité commerciale", color: "text-violet-400" },
  reappro: { icon: ShoppingCart, label: "Réapprovisionnement", color: "text-sky-400" },
  info: { icon: Lightbulb, label: "Info", color: "text-slate-400" },
};

export default function AssertionCard({ assertion }: { assertion: Assertion }) {
  const qc = useQueryClient();
  const [state, setState] = useState<"none" | "accurate" | "inaccurate">(assertion.feedback);

  const meta = TYPE_META[assertion.type] ?? TYPE_META.info;
  const Icon = meta.icon;

  const feedback = useMutation({
    mutationFn: (value: "accurate" | "inaccurate") => postFeedback(assertion.id, value),
    onSuccess: (updated) => {
      setState(updated.feedback);
      qc.invalidateQueries({ queryKey: ["pilotage"] });
    },
  });

  return (
    <article
      className={clsx(
        "rounded-2xl border bg-ink-850 p-5 transition-colors",
        assertion.priority === "P0" && "border-rose-500/30",
        assertion.priority === "P1" && "border-amber-500/25",
        assertion.priority === "P2" && "border-ink-700/60"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="shrink-0 h-8 w-8 rounded-lg bg-ink-800 flex items-center justify-center">
            <Icon className={clsx("h-4 w-4", meta.color)} />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
              {meta.label}
              {assertion.product_ref && (
                <span className="ml-1.5 text-indigo-400 normal-case tracking-normal">· {assertion.product_ref}</span>
              )}
            </p>
            <h4 className="text-sm font-semibold text-white truncate">{assertion.title}</h4>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceBar value={assertion.confidence} />
          <PriorityChip priority={assertion.priority} />
        </div>
      </div>

      <p className="mt-3 text-sm text-slate-300 leading-relaxed">{assertion.message}</p>

      {assertion.evidence && assertion.evidence.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {assertion.evidence.slice(0, 6).map((e, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 rounded-md bg-ink-800 border border-ink-700 px-2 py-1 text-[11px] text-slate-400"
            >
              <span className="text-slate-500">{e.label}:</span>
              <span className="font-semibold text-slate-200 tabular-nums">{e.value}</span>
            </span>
          ))}
        </div>
      )}

      {assertion.action && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-2">
          <ShoppingCart className="h-4 w-4 text-indigo-300 mt-0.5 shrink-0" />
          <p className="text-xs text-indigo-200 leading-relaxed">
            <span className="font-semibold">Action : </span>
            {assertion.action}
          </p>
        </div>
      )}

      <div className="mt-4 flex items-center gap-2">
        <span className="text-[11px] text-slate-500 mr-1">Cette affirmation est-elle exacte ?</span>
        <button
          onClick={() => feedback.mutate("accurate")}
          disabled={feedback.isPending || state === "accurate"}
          className={clsx(
            "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors",
            state === "accurate"
              ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
              : "border-ink-700 text-slate-400 hover:border-emerald-500/40 hover:text-emerald-300"
          )}
        >
          <Check className="h-3.5 w-3.5" /> Exact
        </button>
        <button
          onClick={() => feedback.mutate("inaccurate")}
          disabled={feedback.isPending || state === "inaccurate"}
          className={clsx(
            "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors",
            state === "inaccurate"
              ? "border-rose-500/50 bg-rose-500/15 text-rose-300"
              : "border-ink-700 text-slate-400 hover:border-rose-500/40 hover:text-rose-300"
          )}
        >
          <X className="h-3.5 w-3.5" /> Faux
        </button>
        {state !== "none" && (
          <span className="text-[11px] text-slate-500">
            {state === "accurate" ? "Merci, confirmation enregistrée." : "Merci, ce retour alimente l'apprentissage."}
          </span>
        )}
      </div>
    </article>
  );
}
