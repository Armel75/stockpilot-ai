import clsx from "clsx";
import type { Priority } from "@/types";

const STYLES: Record<Priority, string> = {
  P0: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  P1: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  P2: "bg-sky-500/15 text-sky-300 border-sky-500/40",
};

export default function PriorityChip({ priority }: { priority: Priority | string }) {
  const p = (priority as Priority) in STYLES ? (priority as Priority) : "P2";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-bold tracking-wide",
        STYLES[p]
      )}
    >
      {priority}
    </span>
  );
}
