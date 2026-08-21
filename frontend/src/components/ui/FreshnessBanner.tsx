import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { getPilotage } from "@/api/client";

/**
 * Bandeau de fraîcheur des données — réutilisable sur toutes les pages.
 * N'affiche rien quand les données sont à jour (donc invisible en nominal).
 */
export default function FreshnessBanner() {
  const { data } = useQuery({ queryKey: ["pilotage"], queryFn: getPilotage });
  if (!data || data.freshness.is_fresh) return null;

  return (
    <div className="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
      <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
      <div>
        <p className="text-sm font-semibold text-amber-300">Données potentiellement obsolètes</p>
        <p className="text-xs text-amber-200/80">{data.freshness.message}</p>
      </div>
    </div>
  );
}
