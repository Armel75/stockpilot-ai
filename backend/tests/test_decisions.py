"""Tests des Décisions du jour (synthèse exécutive déterministe)."""
from app.models.entities import Product, Signal
from app.services.decisions import build_decisions


def _signal(stype: str, priority: str, metrics: dict | None = None) -> Signal:
    return Signal(product_id=1, signal_type=stype, priority=priority, status="open", metrics=metrics or {})


def _product(ref: str, name: str) -> Product:
    return Product(ref=ref, name=name, lead_time_days=15, min_order_qty=1)


def test_build_decisions_orders_by_priority():
    signals = [
        (_signal("reappro", "P2", {"suggested_qty": 100}), _product("B", "Produit B")),
        (_signal("rupture", "P0", {"coverage_days": 5, "suggested_qty": 500}), _product("A", "Produit A")),
    ]
    decisions = build_decisions(signals)
    assert len(decisions) == 2
    assert decisions[0].priority == "P0"
    assert decisions[0].action_type == "commander"
    assert decisions[0].product_ref == "A"
    assert decisions[0].quantity == 500


def test_build_decisions_caps_limit():
    signals = [(_signal("reappro", "P2", {}), _product(f"R{i}", f"P{i}")) for i in range(8)]
    assert len(build_decisions(signals, limit=3)) == 3


def test_build_decisions_surstock_action():
    signals = [(_signal("surstock", "P1", {"coverage_days": 162.9}), _product("A", "Tôle bac acier"))]
    decision = build_decisions(signals)[0]
    assert decision.action_type == "ecouler"
    assert decision.role == "Commercial"
    assert "écouler" in decision.message


def test_build_decisions_reappro_quantity():
    signals = [(_signal("reappro", "P1", {"suggested_qty": 2865}), _product("CIM-002", "Ciment 32.5"))]
    decision = build_decisions(signals)[0]
    assert decision.quantity == 2865
    assert decision.role == "Approvisionnement"
