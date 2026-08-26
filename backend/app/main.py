"""API FastAPI do controle de logística (portaria + balança)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .routers import (
    auth,
    camera,
    pesagem,
    plantas,
    pontos,
    portaria,
    usuarios,
    veiculos,
)

DESCRICAO = """
API de operação de logística para os frontends da **Portaria** e da **Balança**.

## Fluxo

1. A **portaria** envia a `operacao` (`entrada` ou `saida`), a **URL de
   snapshot da câmera** e a **unidade** (`POST /portaria/eventos`).
2. A **balança** envia o peso em **toneladas**, o `tipo` (`tara` = vazio ou
   `bruto` = cheio), a **URL de snapshot** e a **unidade** (`POST /pesagens`).
3. O backend captura o snapshot na URL informada e reconhece a placa via ANPR
   (PaddleOCR), ou usa a placa enviada explicitamente no campo `placa`.

## Visita

O `visita_id` (UUID) agrupa **1 entrada → pesagens → 1 saída**. Ao fechar a
visita, calcula-se `peso_liquido = bruto - tara` e o tipo de carregamento.

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
    {
        "name": "camera",
        "description": "Reconhecimento de placa via câmera IP com credenciais customizadas.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
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
app.include_router(camera.router)
app.include_router(portaria.router)
app.include_router(pesagem.router)
app.include_router(plantas.router)
app.include_router(veiculos.router)
app.include_router(pontos.router)
app.include_router(usuarios.router)
