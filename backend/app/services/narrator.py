"""Narrateur — transforme les signaux calculés en affirmations priorisées.

DeepSeek produit le « point de situation » (résumé + affirmations structurées).
En cas d'échec LLM, repli déterministe : l'agent reste toujours fonctionnel.
"""
import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Product, Signal
from app.schemas.api import LLMAssertion, LLMNarration
from app.services import llm

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------
# Messages de repli déterministe
# ---------------------------------------------------------------

def _fallback_message(sig: Signal, p: Product) -> str:
    m = sig.metrics or {}
    name = p.name
    stock = m.get("stock", 0)
    coverage = m.get("coverage_days")
    daily = m.get("daily_avg_30", 0)
    t = sig.signal_type
    if t == "rupture":
        return (
            f"Le stock de {name} ({stock:g} unités) couvre {coverage:g} jours au rythme "
            f"actuel ({daily:g}/jour). Risque de rupture dans {coverage:g} jours."
        )
    if t == "surstock":
        return (
            f"Le stock de {name} ({stock:g} unités) représente {coverage:g} jours de couverture, "
            f"au-delà du seuil de {settings.OVERSTOCK_COVERAGE_DAYS} jours. Capital immobilisé inutilement."
        )
    if t == "dormant":
        return (
            f"{name} n'a enregistré aucune vente depuis {m.get('dormant_days', 0):g} jours, "
            f"alors que {stock:g} unités sont en stock."
        )
    if t == "acceleration":
        growth = m.get("growth_pct", 0)
        return (
            f"Les ventes de {name} ont augmenté de {growth * 100:.0f} % sur les 30 derniers jours "
            f"({daily:g} unités/jour). Anticiper le réapprovisionnement."
        )
    if t == "opportunite":
        if m.get("opportunity") == "stock_excedent_marge_elevee":
            return (
                f"{name} combine un stock excédentaire et une marge élevée ({p.margin_rate * 100:.0f} %). "
                f"Une campagne commerciale ciblée accélérerait sa rotation."
            )
        return (
            f"{name} affiche une forte demande, un stock limité et une marge élevée "
            f"({p.margin_rate * 100:.0f} %). Prioriser son réapprovisionnement."
        )
    if t == "reappro":
        return (
            f"Besoin de réapprovisionnement pour {name} : commander environ "
            f"{m.get('suggested_qty', 0):g} unités (prévision sur {p.lead_time_days} j + stock de "
            f"sécurité − stock disponible − en transit)."
        )
    return f"Signal {t} détecté sur {name}."


def _fallback_confidence(sig: Signal) -> float:
    if sig.priority == "P0":
        return 0.9
    if sig.priority == "P1":
        return 0.8
    return 0.7


def _fallback_action(sig: Signal, p: Product) -> str:
    m = sig.metrics or {}
    if sig.signal_type == "rupture":
        return (
            f"Valider un réapprovisionnement de {name_prio(p)} pour couvrir "
            f"{p.lead_time_days} jours + stock de sécurité."
        )
    if sig.signal_type == "surstock":
        return "Lancer une action commerciale (promotion, transfert) pour réduire le stock."
    if sig.signal_type == "dormant":
        return "Décider : promotion agressive, transfert vers une autre agence ou écriture de perte."
    if sig.signal_type == "acceleration":
        return "Sécuriser l'approvisionnement et vérifier la capacité de stock."
    if sig.signal_type == "opportunite":
        return "Prioriser la mise en avant commerciale de ce produit."
    if sig.signal_type == "reappro":
        return f"Préparer un bon de commande fournisseur d'environ {m.get('suggested_qty', 0):g} unités."
    return "Surveiller la situation."


def name_prio(p: Product) -> str:
    return p.name


def _evidence_from_metrics(m: dict) -> list[dict]:
    labels = {
        "stock": "Stock actuel",
        "reserved": "Stock réservé",
        "in_transit": "En transit",
        "daily_avg_30": "Ventes moyennes / jour",
        "coverage_days": "Stock restant (jours)",
        "growth_pct": "Croissance 30 j",
        "last_sale_days_ago": "Dernière vente (jours)",
        "dormant_days": "Sans vente depuis (jours)",
        "suggested_qty": "Quantité à commander",
        "safety_stock": "Stock de sécurité (objectif)",
    }
    out = []
    for k, v in m.items():
        if k in labels and v is not None:
            if isinstance(v, float):
                if k in ("growth_pct",):
                    out.append({"label": labels[k], "value": f"{v * 100:.0f} %"})
                else:
                    out.append({"label": labels[k], "value": round(v, 2)})
            else:
                out.append({"label": labels[k], "value": v})
    return out[:8]


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _reconcile_assertions(
    assertions: list[LLMAssertion],
    signals: list[tuple[Signal, Product]],
) -> list[LLMAssertion]:
    """Rattache chaque affirmation à SON signal déterministe.

    Les chiffres (evidence) et les références produit sont revalidés côté
    serveur : jamais laissés à la discrétion du LLM (qui peut déformer un
    nombre ou mélanger une référence). Correspondance d'abord par référence,
    puis par nom (secours si la référence écrite par le LLM est erronée).
    """
    by_ref_type: dict[tuple[str, str], tuple[Signal, Product]] = {}
    by_name_type: dict[tuple[str, str], tuple[Signal, Product]] = {}
    products_by_ref: dict[str, Product] = {}
    for sig, p in signals:
        by_ref_type.setdefault((p.ref, sig.signal_type), (sig, p))
        by_name_type.setdefault((_norm(p.name), sig.signal_type), (sig, p))
        products_by_ref.setdefault(p.ref, p)

    reconciled: list[LLMAssertion] = []
    for a in assertions:
        source = by_ref_type.get((a.product_ref, a.type))
        if source is None:
            source = by_name_type.get((_norm(a.product_name), a.type))
        if source is not None:
            sig, p = source
            a.product_ref = p.ref
            a.product_name = p.name
            a.evidence = _evidence_from_metrics(sig.metrics or {})
        elif a.product_ref in products_by_ref:
            p = products_by_ref[a.product_ref]
            a.product_ref = p.ref
            a.product_name = p.name
            a.evidence = []
        reconciled.append(a)
    return reconciled


def _fallback_assertions(signals: list[tuple[Signal, Product]]) -> list[LLMAssertion]:
    out: list[LLMAssertion] = []
    for sig, p in signals:
        m = sig.metrics or {}
        out.append(
            LLMAssertion(
                priority=sig.priority,
                type=sig.signal_type,
                title=f"{sig.signal_type.capitalize()} — {p.name}",
                message=_fallback_message(sig, p),
                product_ref=p.ref,
                product_name=p.name,
                confidence=_fallback_confidence(sig),
                action=_fallback_action(sig, p),
                evidence=_evidence_from_metrics(m),
            )
        )
    return out


# ---------------------------------------------------------------
# Narration LLM (DeepSeek) avec repli
# ---------------------------------------------------------------

def _llm_payload(signals: list[tuple[Signal, Product]]) -> str:
    facts = []
    for sig, p in signals:
        facts.append(
            {
                "product_ref": p.ref,
                "product_name": p.name,
                "signal_type": sig.signal_type,
                "priority": sig.priority,
                "metrics": {k: v for k, v in (sig.metrics or {}).items() if v is not None},
            }
        )
    return json.dumps(
        {
            "regles_de_redaction": [
                "Réponds en français, affirmations directes et actionnables.",
                "N'invente JAMAIS de chiffres : utilise uniquement les metrics fournies.",
                "N'ajoute PAS de champ evidence : les preuves chiffrées sont ajoutées par le système.",
                "Dans le message, reste qualitatif (ex: 'stock critique', 'couverture très faible') "
                "sans répéter de valeurs numériques précises.",
                "Chaque affirmation doit contenir un titre court, un message, une action.",
                "confidence = confiance dans l'affirmation (0-1).",
                "Hiérarchise : P0 = urgence, P1 = important, P2 = à surveiller.",
                "Limite le nombre d'affirmations à ~15 (les plus importantes).",
            ],
            "signaux_calcules": facts[: settings.NARRATOR_MAX_SIGNALS],
        },
        ensure_ascii=False,
    )


def narrate(
    db: Session,  # noqa: ARG001 (non utilisé directement, interface homogène)
    as_of: date,
    signals: list[tuple[Signal, Product]],
) -> tuple[str, list[LLMAssertion], bool]:
    """Produit le point de situation. Retourne (summary, assertions, llm_used)."""
    llm_used = False
    if not signals:
        return "Aucun signal détecté aujourd'hui. La situation est sous contrôle.", [], False

    n_p0 = sum(1 for s, _ in signals if s.priority == "P0")
    fallback_summary = (
        f"Point de situation du {as_of.isoformat()} : {len(signals)} signaux détectés, "
        f"dont {n_p0} prioritaires (P0)."
    )

    if llm.is_available():
        payload = _llm_payload(signals)
        try:
            raw = llm.chat_json(
                payload,
                system_prompt=(
                    "Tu es le rédacteur en chef d'un agent de pilotage stocks/ventes d'une "
                    "entreprise de distribution au Cameroun. Tu reçois des faits calculés et tu "
                    "produis le point de situation du jour. Tu rédiges du TEXTE, pas des chiffres : "
                    "n'ajoute jamais de champ evidence et ne répète pas de valeurs numériques précises "
                    "dans le message (les preuves chiffrées sont ajoutées automatiquement par le "
                    "système). Le chiffre d'affaires et les montants de ventes sont CONFIDENTIELS : "
                    "ne les mentionne jamais. Réponds uniquement en JSON au format : "
                    '{"summary": "...", "assertions": [{"priority": "P0|P1|P2", "type": '
                    '"rupture|surstock|dormant|acceleration|opportunite|reappro|info", "title": "...", '
                    '"message": "...", "product_ref": "...", "product_name": "...", "confidence": 0.8, '
                    '"action": "..."}]}'
                ),
            )
            if raw:
                narration = LLMNarration.model_validate(raw)
                if narration.assertions:
                    llm_used = True
                    # Les chiffres et références sont revalidés côté serveur
                    assertions = _reconcile_assertions(narration.assertions, signals)
                    return narration.summary, assertions, True
                logger.warning("DeepSeek a renvoyé 0 affirmation — repli déterministe")
        except Exception as exc:  # noqa: BLE001
            logger.error("Narration LLM échouée, repli déterministe: %s", exc)

    return fallback_summary, _fallback_assertions(signals), llm_used
