from .config import DISCLAIMER


def with_disclaimer(data) -> dict:
    """Toda resposta clínica carrega o aviso de que isto não é diagnóstico."""
    return {"disclaimer": DISCLAIMER, "data": data}
