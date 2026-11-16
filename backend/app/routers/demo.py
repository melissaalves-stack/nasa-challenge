"""Frontend de demonstração (página estática). Só consome a API existente."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(include_in_schema=False)
_PAGE = Path(__file__).resolve().parent.parent / "static" / "demo.html"


@router.get("/demo")
def demo_page():
    return FileResponse(_PAGE, media_type="text/html")
