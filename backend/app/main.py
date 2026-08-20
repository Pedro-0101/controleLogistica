"""API FastAPI do controle de logística (portaria + balança)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .routers import auth, pesagem, plantas, pontos, portaria, usuarios, veiculos

DESCRICAO = """
API de operação de logística para os frontends da **Portaria** e da **Balança**.

## Fluxo

1. A **portaria** envia a foto frontal do caminhão com a operação de
   `entrada` ou `saida` e a **unidade** (`POST /portaria/eventos`).
2. A **balança** envia a foto frontal com o peso em **toneladas** e a
   **unidade** (`POST /pesagens`).
3. A placa é reconhecida via ANPR (PaddleOCR) ou pode ser enviada
   explicitamente no campo `placa`, ignorando o OCR.

## Visita

O `visita_id` (UUID) agrupa **1 entrada → N pesagens → 1 saída**. Ao fechar a
visita, calcula-se o peso líquido e o tipo de carregamento.

## Autenticação

OAuth2 password flow (`POST /auth/login`). Use o botão **Authorize** do Swagger
com um usuário cadastrado. Perfis: `admin`, `portaria` e `balanca`.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Login, renovação de token e dados do usuário."},
    {
        "name": "portaria",
        "description": "Registro de passagens (entrada/saída) e visitas abertas.",
    },
    {
        "name": "pesagens",
        "description": "Registro de pesagens (toneladas) e carregamentos concluídos.",
    },
    {"name": "plantas", "description": "CRUD de unidades (plantas)."},
    {"name": "veiculos", "description": "CRUD de caminhões (veículos)."},
    {
        "name": "pontos",
        "description": "CRUD de pontos de coleta (portarias e balança).",
    },
    {"name": "usuarios", "description": "CRUD de usuários e perfis."},
    {"name": "infra", "description": "Health check."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings.imagens_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Controle Logística — API de Operação",
    description=DESCRICAO,
    version="0.2.0",
    openapi_tags=TAGS_METADATA,
    contact={"name": "Equipe de Operação", "email": "operacao@example.com"},
    license_info={
        "name": "Proprietário",
        "url": "https://example.com/licenca",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.get("/health", summary="Health check", tags=["infra"])
def health() -> dict[str, str]:
    """Verifica se a API está no ar."""
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(portaria.router)
app.include_router(pesagem.router)
app.include_router(plantas.router)
app.include_router(veiculos.router)
app.include_router(pontos.router)
app.include_router(usuarios.router)
