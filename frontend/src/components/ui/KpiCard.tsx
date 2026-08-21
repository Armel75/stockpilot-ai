import type { ReactNode } from "react";
import clsx from "clsx";
import Card from "./Card";

export default function KpiCard({
  label,
  value,
  hint,
  icon,
  accent = "text-white",
  sub,
  title,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: ReactNode;
  accent?: string;
  sub?: ReactNode;
  title?: string;
}) {
  return (
    <Card className="p-5" title={title}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
        {icon && <div className="text-slate-500">{icon}</div>}
      </div>
      <p className={clsx("mt-2 text-2xl font-bold tabular-nums", accent)}>{value}</p>
      {sub ? <div className="mt-1">{sub}</div> : hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </Card>
  );
}
