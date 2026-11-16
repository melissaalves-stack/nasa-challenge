from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (registra as tabelas)
from .config import CORS_ORIGINS, DISCLAIMER, ENABLE_DEMO_UI
from .db import Base, engine
from .routers import clinician, entries, simulate, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="AstroKatu API",
    version="0.1.0",
    description=("Monitoramento longitudinal de saúde comportamental para missões longas. "
                 + DISCLAIMER),
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # O handler padrão ecoa o "input" recebido. Aqui só devolvemos local + mensagem,
    # para que nenhum conteúdo enviado (ex.: texto de diário) volte ou vá parar em logs.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health():
    return {"status": "ok"}


for r in (users.router, entries.router, clinician.router, simulate.router):
    app.include_router(r)

if ENABLE_DEMO_UI:
    from .routers import demo
    app.include_router(demo.router)
