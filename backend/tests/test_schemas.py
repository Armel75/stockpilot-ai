"""Tests des schémas Pydantic (contrat de sortie du narrateur LLM)."""
import pytest
from pydantic import ValidationError

from app.schemas.api import LLMAssertion, LLMNarration


def _valid_assertion() -> dict:
    return {
        "priority": "P0",
        "type": "rupture",
        "title": "Rupture imminente — Ciment X",
        "message": "Le stock couvre 5 jours.",
        "product_ref": "CIM-001",
        "product_name": "Ciment X",
        "confidence": 0.9,
        "action": "Commander 500 unités.",
        "evidence": [{"label": "Stock", "value": 250}],
    }


def test_llm_assertion_valid():
    a = LLMAssertion.model_validate(_valid_assertion())
    assert a.priority == "P0"
    assert a.confidence == 0.9


def test_llm_assertion_rejects_invalid_priority():
    payload = _valid_assertion()
    payload["priority"] = "P9"
    with pytest.raises(ValidationError):
        LLMAssertion.model_validate(payload)


def test_llm_assertion_rejects_invalid_type():
    payload = _valid_assertion()
    payload["type"] = "inconnu"
    with pytest.raises(ValidationError):
        LLMAssertion.model_validate(payload)


def test_llm_assertion_rejects_confidence_out_of_range():
    payload = _valid_assertion()
    payload["confidence"] = 1.5
    with pytest.raises(ValidationError):
        LLMAssertion.model_validate(payload)


def test_llm_narration_valid():
    narration = LLMNarration.model_validate(
        {"summary": "Point du jour.", "assertions": [_valid_assertion()]}
    )
    assert len(narration.assertions) == 1
    assert narration.summary == "Point du jour."
