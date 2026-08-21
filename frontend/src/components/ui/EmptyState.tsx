import type { ReactNode } from "react";

export default function EmptyState({
  title,
  description,
  icon,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      {icon && <div className="text-slate-600 mb-1">{icon}</div>}
      <p className="text-sm font-semibold text-slate-300">{title}</p>
      {description && <p className="text-xs text-slate-500 max-w-sm">{description}</p>}
    </div>
  );
}
