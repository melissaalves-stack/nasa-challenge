import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./astrokatu.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

DISCLAIMER = (
    "Sistema de apoio à decisão. Não emite diagnóstico e não substitui "
    "avaliação de um profissional de saúde."
)

# Pagina /demo (simulacao visual). Desligue em producao: ENABLE_DEMO_UI=0
ENABLE_DEMO_UI = os.getenv("ENABLE_DEMO_UI", "1") == "1"
