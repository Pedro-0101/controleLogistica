# controleLogistica

API de operação de logística (portaria + balança) — FastAPI + PostgreSQL.

A API recebe da **portaria** a `operacao` (entrada/saída) e da **balança** o
`peso` (toneladas) com `tipo` (`tara`/`bruto`). O front envia a **URL de snapshot
da câmera**, que o backend captura e usa para reconhecer a placa via ANPR
(PaddleOCR), ou usa a placa enviada explicitamente no corpo.

## Pré-requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (ou pip)
- Docker (para o PostgreSQL)

## Como subir

```bash
# 1. Banco
docker compose up -d db

# 2. Ambiente + dependências
uv venv
uv pip install -r backend/requirements.txt
uv pip install -r backend/requirements-dev.txt   # desenvolvimento

# 3. Configuração
cp .env.example .env    # ajuste SECRET_KEY e ADMIN_PASSWORD

# 4. Migrações
cd backend
uv run alembic upgrade head

# 5. Dados iniciais (planta, pontos e usuário admin)
uv run python -m scripts.seed

# 6. API
uv run uvicorn app.main:app --reload
```

Documentação interativa: http://localhost:8000/docs

## Variáveis de ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL do PostgreSQL | `postgresql+psycopg2://logistica:logistica@localhost:5432/controle_logistica` |
| `ANPR_LANG` | Idioma do OCR de placas | `en` |
| `SECRET_KEY` | Chave de assinatura dos JWT | `dev-secret-change-me` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do access token | `30` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Validade do refresh token | `10080` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NOME` | Usuário admin criado pelo seed | — |
| `DVR_USER` / `DVR_PASSWORD` | Credenciais das câmeras IP Intelbras (Digest) | `admin` / vazio |
| `DVR_AUTH` | Tipo de autenticação das câmeras (`digest` ou `basic`) | `digest` |
| `DVR_TIMEOUT` | Timeout (segundos) para capturar o snapshot | `5.0` |

## Câmeras (IP Intelbras)

O front envia a **URL completa do snapshot** da câmera (o usuário gerencia as
câmeras, então o sistema funciona com qualquer quantidade). Exemplos:

```
# Hikvision/ISAPI
http://IP/ISAPI/Streaming/channels/101/picture

# Dahua
http://IP/cgi-bin/snapshot.cgi
```

As câmeras usam autenticação **Digest** (credenciais globais em `DVR_USER`/
`DVR_PASSWORD`). Para descobrir/validar a URL do seu equipamento:

```bash
cd backend
uv run python -m scripts.dvr_probe --host 192.168.11.241 --password Cameraip1
```

## Autenticação

OAuth2 password flow. Obtenha o token em `POST /auth/login` (form-urlencoded
`username`/`password`) e envie `Authorization: Bearer <token>`. Perfis: `admin`,
`portaria`, `balanca`.

## Principais endpoints

- `POST /portaria/eventos` — `operacao` (`entrada`|`saida`) + `camera` (URL) + `unidade` + `placa` (opcional).
- `POST /pesagens` — `peso` (toneladas) + `tipo` (`tara`|`bruto`) + `camera` (URL) + `unidade` + `placa` (opcional).
- CRUD: `/plantas`, `/veiculos`, `/pontos`, `/usuarios`.

Veja [docs/API.md](docs/API.md) para o contrato completo.

## Qualidade de código

```bash
cd backend
uv run ruff check app scripts tests alembic
uv run ruff format --check app scripts tests alembic
uv run mypy app scripts tests alembic
uv run pytest
```

## Notas

- Migrações via **Alembic** (`backend/alembic`).
- A unidade de peso é **toneladas**; o legado (kg) deve ser convertido (`/ 1000`)
  em qualquer importação manual.
- O reconhecimento de placas (PaddleOCR) é carregado sob demanda; enviar `placa`
  no corpo dispensa o OCR.
