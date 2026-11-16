"""Plano de ações: biblioteca CURADA + regras determinísticas.

Nenhum LLM gera conteúdo clínico aqui. (Se um LLM for usado no futuro, só
para redigir a mensagem a partir destes templates, com guardrails.)
"""
from __future__ import annotations

import copy

from ..config import DISCLAIMER

ACTION_LIBRARY = {
    "info": [
        {"type": "content", "audience": "astronaut", "title": "Podcast sobre tédio", "ref": "podcast_boredom_01"},
        {"type": "routine", "audience": "astronaut", "title": "Ajustar horário de sono em 30 min"},
    ],
    "watch": [
        {"type": "content", "audience": "astronaut", "title": "Exercício de respiração 4-7-8"},
        {"type": "routine", "audience": "astronaut", "title": "Pausa programada + registro de humor 2x/dia"},
        {"type": "social", "audience": "astronaut", "title": "Sugerir contato com colega de tripulação"},
    ],
    "review_required": [
        {"type": "escalation", "audience": "clinician", "title": "Notificar centro de controle", "requires_human": True},
        {"type": "clinical", "audience": "clinician", "title": "Agendar avaliação com profissional de saúde", "requires_human": True},
        {"type": "monitoring", "audience": "astronaut", "title": "Aumentar frequência de registros"},
    ],
}

# Prioridade crítica (marcador de ideação): TUDO passa por humano.
CRITICAL_ACTIONS = [
    {"type": "escalation", "audience": "clinician", "title": "Notificar clínico responsável imediatamente", "requires_human": True},
    {"type": "clinical", "audience": "clinician", "title": "Contato humano com o astronauta conforme protocolo de escalonamento", "requires_human": True},
    {"type": "support", "audience": "astronaut", "title": "Conversar agora com alguém de confiança (tripulante ou canal de apoio)"},
]

TOPIC_ACTIONS = {
    "sono": {"type": "content", "audience": "astronaut", "title": "Higiene do sono — guia rápido"},
    "tédio": {"type": "content", "audience": "astronaut", "title": "Podcast sobre tédio", "ref": "podcast_boredom_01"},
    "isolamento": {"type": "social", "audience": "astronaut", "title": "Videochamada com a família (janela de comunicação)"},
    "trabalho": {"type": "routine", "audience": "astronaut", "title": "Revisar carga de tarefas com a tripulação"},
}


def generate_action_plan(severity: str, priority: str = "normal", topics=()) -> dict:
    if priority == "critical":
        actions = copy.deepcopy(CRITICAL_ACTIONS)
        status = "pending_human_review"
    else:
        actions = copy.deepcopy(ACTION_LIBRARY[severity])
        # personalização leve (não clínica) a partir dos tópicos do diário
        existing = {a["title"] for a in actions}
        for t in topics:
            extra = TOPIC_ACTIONS.get(t)
            if extra and extra["title"] not in existing and severity != "review_required":
                actions.append(copy.deepcopy(extra))
                existing.add(extra["title"])
        status = "pending_human_review" if severity == "review_required" else "suggested"
    for a in actions:
        a["auto_execute"] = False
    return {"severity": severity, "priority": priority, "actions": actions,
            "status": status, "disclaimer": DISCLAIMER, "generated_by": "curated_library_v1"}
