"""Tests de la réconciliation serveur des affirmations LLM (P0)."""
from app.models.entities import Product, Signal
from app.schemas.api import LLMAssertion
from app.services.narrator import _reconcile_assertions


def _product(ref: str, name: str) -> Product:
    return Product(ref=ref, name=name, lead_time_days=15, min_order_qty=1)


def test_reconcile_replaces_llm_evidence_with_deterministic_values():
    p = _product("CIM-001", "Ciment CPJ 42.5 50kg")
    sig = Signal(
        product_id=1, signal_type="rupture", priority="P0", status="open",
        metrics={"stock": 557, "daily_avg_30": 111.37, "coverage_days": 5},
    )
    llm = LLMAssertion(
        priority="P0", type="rupture", title="T", message="M",
        product_ref="CIM-001", product_name="Ciment CPJ 42.5 50kg",
        confidence=0.9, action="A",
        evidence=[{"label": "Stock", "value": 55}],  # le LLM a écrit un mauvais chiffre
    )
    reconciled = _reconcile_assertions([llm], [(sig, p)])
    evidence = {e["label"]: e["value"] for e in reconciled[0].evidence}
    assert evidence["Stock actuel"] == 557  # corrigé par le serveur
    assert evidence["Ventes moyennes / jour"] == 111.37
    assert evidence["Stock restant (jours)"] == 5
    assert reconciled[0].product_name == "Ciment CPJ 42.5 50kg"


def test_reconcile_fixes_wrong_reference_by_name():
    # Le LLM a écrit une mauvaise référence (PLM-003) mais le bon nom (Ballon = PLM-004)
    p = _product("PLM-004", "Ballon d'eau 1000L")
    sig = Signal(
        product_id=1, signal_type="reappro", priority="P1", status="open",
        metrics={"suggested_qty": 52, "safety_stock": 48},
    )
    llm = LLMAssertion(
        priority="P1", type="reappro", title="T", message="M",
        product_ref="PLM-003", product_name="Ballon d'eau 1000L",
        confidence=0.8, action="A",
    )
    reconciled = _reconcile_assertions([llm], [(sig, p)])
    assert reconciled[0].product_ref == "PLM-004"
    evidence = {e["label"]: e["value"] for e in reconciled[0].evidence}
    assert evidence["Quantité à commander"] == 52


def test_reconcile_keeps_unmatched_assertion():
    p = _product("CIM-001", "Ciment CPJ 42.5")
    sig = Signal(product_id=1, signal_type="rupture", priority="P0", metrics={"stock": 100})
    llm = LLMAssertion(
        priority="P2", type="info", title="T", message="M",
        product_ref="CIM-001", product_name="Ciment CPJ 42.5",
        confidence=0.5, action="",
    )
    reconciled = _reconcile_assertions([llm], [(sig, p)])
    assert len(reconciled) == 1
    assert reconciled[0].product_ref == "CIM-001"
