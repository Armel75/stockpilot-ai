import clsx from "clsx";
import { PackageX, RotateCcw, ShieldCheck, ShoppingCart, TrendingUp } from "lucide-react";
import type { Decision } from "@/types";
import PriorityChip from "@/components/ui/PriorityChip";
import Card from "@/components/ui/Card";

const ACTION_META: Record<string, { icon: typeof ShoppingCart; color: string; label: string }> = {
  commander: { icon: ShoppingCart, color: "text-sky-400", label: "Commander" },
  ecouler: { icon: PackageX, color: "text-amber-400", label: "Écouler" },
  traiter: { icon: RotateCcw, color: "text-slate-400", label: "Traiter" },
  pousser: { icon: TrendingUp, color: "text-violet-400", label: "Pousser" },
  securiser: { icon: ShieldCheck, color: "text-emerald-400", label: "Sécuriser" },
  surveiller: { icon: RotateCcw, color: "text-slate-400", label: "Surveiller" },
};

const nf = new Intl.NumberFormat("fr-FR");

export default function DecisionCard({ decision }: { decision: Decision }) {
  const meta = ACTION_META[decision.action_type] ?? ACTION_META.surveiller;
  const Icon = meta.icon;
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-8 w-8 rounded-lg bg-ink-800 flex items-center justify-center">
            <Icon className={clsx("h-4 w-4", meta.color)} />
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {meta.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500 hidden sm:inline">{decision.role}</span>
          <PriorityChip priority={decision.priority} />
        </div>
      </div>
      <p className="mt-3 text-sm font-semibold text-white">
        {decision.product_name} <span className="text-xs text-slate-500">· {decision.product_ref}</span>
      </p>
      {decision.quantity != null && (
        <p className="mt-1 text-lg font-bold text-indigo-300 tabular-nums">
          {nf.format(decision.quantity)} unités
        </p>
      )}
      <p className="mt-1 text-xs text-slate-400 leading-relaxed">{decision.message}</p>
    </Card>
  );
}
