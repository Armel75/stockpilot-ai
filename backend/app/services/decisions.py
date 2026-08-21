"""Décisions du jour — synthèse exécutive DÉTERMINISTE à partir des signaux.

Pas de LLM ici : on extrait les actions à prendre, en langage métier,
avec produit, référence, quantité et rôle concerné. Fiabilité garantie.
"""
from app.models.entities import Product, Signal
from app.schemas.api import DecisionOut

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

_ACTION_TYPES = {
    "rupture": "commander",
    "reappro": "commander",
    "surstock": "ecouler",
    "dormant": "traiter",
    "opportunite": "pousser",
    "acceleration": "securiser",
}

_ROLES = {
    "rupture": "Approvisionnement",
    "reappro": "Approvisionnement",
    "surstock": "Commercial",
    "dormant": "Commercial",
    "opportunite": "Commercial",
    "acceleration": "Approvisionnement",
}


def _message(sig: Signal, p: Product) -> str:
    m = sig.metrics or {}
    t = sig.signal_type
    coverage = m.get("coverage_days")
    qty = m.get("suggested_qty")
    if t == "rupture":
        if qty:
            return (
                f"Risque de rupture dans ~{coverage:g} jours — commander environ {qty:g} unités "
                f"pour couvrir le délai fournisseur ({p.lead_time_days} j) + stock de sécurité."
            )
        return f"Risque de rupture dans ~{coverage:g} jours — réapprovisionnement urgent."
    if t == "reappro":
        if qty:
            return f"Commander {qty:g} unités pour maintenir le stock de sécurité."
        return "Réapprovisionnement à planifier pour maintenir le stock de sécurité."
    if t == "surstock":
        return f"Stock suffisant pour {coverage:g} jours — à écouler (promotion, transfert)."
    if t == "dormant":
        return f"Aucune vente depuis {m.get('dormant_days', 0):g} jours — décision à prendre."
    if t == "opportunite":
        return "Demande forte et marge élevée — prioriser ce produit."
    if t == "acceleration":
        return "Ventes en forte hausse — sécuriser l'approvisionnement."
    return "Surveiller la situation."


def build_decisions(
    signals: list[tuple[Signal, Product]], limit: int = 5
) -> list[DecisionOut]:
    """Convertit les signaux ouverts en décisions prioritaires (top N)."""
    ranked = sorted(signals, key=lambda sp: _PRIORITY_ORDER.get(sp[0].priority, 3))
    out: list[DecisionOut] = []
    for sig, p in ranked[:limit]:
        qty = (sig.metrics or {}).get("suggested_qty")
        out.append(
            DecisionOut(
                priority=sig.priority,
                action_type=_ACTION_TYPES.get(sig.signal_type, "surveiller"),
                product_ref=p.ref,
                product_name=p.name,
                quantity=round(qty) if qty else None,
                message=_message(sig, p),
                role=_ROLES.get(sig.signal_type, "Commercial"),
            )
        )
    return out
