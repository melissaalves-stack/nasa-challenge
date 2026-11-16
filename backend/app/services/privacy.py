"""Privacy-preserving inference: o backend só aceita FEATURES do diário.

O texto é processado e destruído no dispositivo. Aqui garantimos, por
whitelist estrita, que nenhum texto (nem "escondido" em campo livre) entra.
"""
from __future__ import annotations

import re

ALLOWED_KEYS = {
    "neg_emotion_score",
    "pos_emotion_score",
    "stress_score",
    "loneliness_score",
    "anhedonia_score",
    "suicidal_ideation_flag",
    "suicidal_ideation_confidence",
    "text_length",
    "complexity",
    "topic_tags",
}
SCORE_KEYS = (
    "neg_emotion_score",
    "pos_emotion_score",
    "stress_score",
    "loneliness_score",
    "anhedonia_score",
    "suicidal_ideation_flag",
    "complexity",
)
CONFIDENCE_LEVELS = {"low", "medium", "high"}

# Vocabulário FECHADO: tags livres seriam um canal para vazar texto.
TOPIC_VOCAB = {
    "sono", "trabalho", "família", "saúde", "isolamento", "tédio", "tarefa",
    "equipe", "alimentação", "exercício", "saudade", "outro",
}
MAX_TOPICS = 5
MAX_TEXT_LENGTH = 20000
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class PrivacyViolation(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_text_hash(text_hash: str) -> str:
    h = (text_hash or "").lower()
    if not _HASH_RE.match(h):
        raise PrivacyViolation("text_hash must be 64 hex chars (SHA-256/HMAC-SHA-256)")
    return h


def validate_diary_features(features: dict, *, consent: bool) -> dict:
    """Valida e devolve uma cópia LIMPA das features. Nunca ecoa valores."""
    if not consent:
        raise PrivacyViolation("Diary consent required", status=403)
    if not isinstance(features, dict):
        raise PrivacyViolation("features must be an object")

    extras = set(features) - ALLOWED_KEYS
    if extras:
        # só os NOMES dos campos, nunca os valores
        raise PrivacyViolation(f"Unexpected fields: {sorted(extras)}")

    clean: dict = {}
    for k in SCORE_KEYS:
        v = features.get(k)
        if not _is_number(v):
            raise PrivacyViolation(f"{k} is required and must be a number")
        if not (0 <= v <= 1):
            raise PrivacyViolation(f"{k} out of range [0,1]")
        clean[k] = round(float(v), 4)

    conf = features.get("suicidal_ideation_confidence")
    if conf not in CONFIDENCE_LEVELS:
        raise PrivacyViolation("suicidal_ideation_confidence must be low|medium|high")
    clean["suicidal_ideation_confidence"] = conf

    tl = features.get("text_length")
    if not isinstance(tl, int) or isinstance(tl, bool) or not (0 <= tl <= MAX_TEXT_LENGTH):
        raise PrivacyViolation("text_length must be an int in [0, 20000]")
    clean["text_length"] = tl

    tags = features.get("topic_tags", [])
    if not isinstance(tags, list) or len(tags) > MAX_TOPICS:
        raise PrivacyViolation(f"topic_tags must be a list with at most {MAX_TOPICS} items")
    bad = [t for t in tags if t not in TOPIC_VOCAB]
    if bad:
        raise PrivacyViolation("topic_tags outside the allowed vocabulary")
    clean["topic_tags"] = list(dict.fromkeys(tags))
    return clean


def safe_log_ref(text_hash: str, model_version: str) -> dict:
    """Única informação do diário que pode aparecer em logs."""
    return {"text_hash": text_hash, "local_model_version": model_version}
