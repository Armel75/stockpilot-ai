"""Client LLM CENTRALISÉ — DeepSeek (API compatible OpenAI).

Règle d'or de l'agent : le LLM ne calcule JAMAIS les chiffres.
Il reçoit des faits calculés (JSON) et ne fait que prioriser, expliquer, rédiger.
"""
import json
import logging
import time
from typing import Any

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_SYSTEM_PROMPT = (
    "Tu es le rédacteur en chef d'un agent de pilotage des stocks et des ventes "
    "d'une entreprise de distribution. Tu reçois des faits calculés par un moteur "
    "déterministe (jamais inventés). Tu produis des affirmations courtes, directes "
    "et actionnables en français, avec les preuves fournies. "
    "Tu ne calcules jamais : tu t'appuies exclusivement sur les valeurs reçues. "
    "Tu hiérarchises en P0 (urgence), P1 (important), P2 (à surveiller)."
)


def _client() -> OpenAI:
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY manquante dans .env")
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )


def chat_json(
    user_payload: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    max_tokens: int = 4000,
) -> dict[str, Any] | None:
    """Appelle DeepSeek et retourne un objet JSON (None si échec)."""
    payload = (
        "Réponds uniquement avec un objet JSON valide. "
        "Contrat attendu :\n" + user_payload
    )
    last_error: Exception | None = None
    for attempt in range(1 + settings.LLM_MAX_RETRIES):
        try:
            resp = _client().chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": payload},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("DeepSeek appel %s échoué: %s", attempt + 1, exc)
            time.sleep(1.0)
    logger.error("DeepSeek indisponible après retries: %s", last_error)
    return None


def is_available() -> bool:
    return bool(settings.DEEPSEEK_API_KEY)
