# Planejamento — API de Operação (controleLogistica)

> Documento de planejamento. **Não executar ainda** — serve como guia para a fase de
> implementação. Itens marcados com **"PENDENTE"** devem ser confirmados antes/na execução.

---

## 1. Objetivo

Transformar o sistema de teste atual (monólito FastAPI + tela única `index.html`) em uma
**API pura** para a fase de operação, consumida por **dois frontends separados**:

- **Front Portaria** — envia fotos da frente do caminhão com a operação de entrada/saída.
- **Front Balança** — envia foto da frente do caminhão com o peso (toneladas).

A API passa a receber requisições nos formatos:

- **Portaria (entrada/saída):** `{ foto da frente do caminhão, operacao: "entrada" | "saida" }`
- **Balança:** `{ foto da frente do caminhão, peso: 99.99 }` (toneladas)

Escopo deste plano: **somente a API**. Os dois frontends ficam para outro planejamento.

---

## 2. Decisões confirmadas

| # | Tema | Decisão |
|---|------|---------|
| 1 | Autenticação | **JWT com perfis/roles** (OAuth2 password flow). Roles: `admin`, `portaria`, `balanca`. |
| 2 | Fonte de peso | **Somente HTTP**. Remover leitura serial/simulador (`app/balanca/*`). |
| 3 | Nomes de entidades | **Manter nomes atuais** (`Planta` = "unidade", `Veiculo` = "caminhão"). |
| 4 | Separação de tabelas | **2 tabelas**: uma p/ movimentação de portaria + uma p/ pesagens e carregamentos. |
| 5 | Escopo | **Só a API** (sem detalhar os fronts). |
| 6 | Placa na foto | **ANPR continua**, mas o body pode trazer `placa` explícita (ignora/valida o OCR). |

---

## 3. Mapeamento de nomes

| Termo do usuário | Entidade atual (mantida) | Rota CRUD |
|------------------|--------------------------|-----------|
| "unidades" | `Planta` | `/plantas` |
| "caminhões" | `Veiculo` | `/veiculos` |
| "pontos de coleta" (portarias/balança) | `Ponto` | `/pontos` |
| — (novo) | `Usuario` | `/usuarios` |

---

## 4. Arquitetura de rotas

Todas as rotas (exceto `POST /auth/login`, `GET /health`, `GET /docs`) exigem
`Authorization: Bearer <token>`.

### 4.1 Autenticação

| Método | Rota | Role | Descrição |
|--------|------|------|-----------|
| POST | `/auth/login` | pública | Login/senha → `access_token` (JWT) + `token_type` + `expires_in`. |
| POST | `/auth/refresh` | autenticada | Renova token (refresh token ou re-login). *(opcional, v1 pode re-logar)* |
| GET | `/auth/me` | autenticada | Dados do usuário logado (id, nome, email, role). |

- Formato OAuth2: `application/x-www-form-urlencoded` com `username` e `password`
  (compatível com o botão "Authorize" do Swagger em `/docs`).
- Token carrega: `sub` (user id), `role`, `exp`. Assinado com `SECRET_KEY` (env).

### 4.2 Operacional — Portaria

| Método | Rota | Role | Descrição |
|--------|------|------|-----------|
| POST | `/portaria/eventos` | `portaria`, `admin` | Registra passagem. Multipart: `foto` + `operacao` + `placa` (opcional). |
| GET | `/portaria/eventos` | `portaria`, `admin` | Lista passagens (filtros: `placa`, `operacao`, `visita_id`, `de`/`ate`). |
| GET | `/portaria/abertas` | `portaria`, `admin` | Lista visitas abertas (entrou, ainda não saiu). |

### 4.3 Operacional — Balança

| Método | Rota | Role | Descrição |
|--------|------|------|-----------|
| POST | `/pesagens` | `balanca`, `admin` | Registra pesagem. Multipart: `foto` + `peso` + `placa` (opcional). |
| GET | `/pesagens` | `balanca`, `admin` | Lista pesagens (filtros: `placa`, `visita_id`, `de`/`ate`). |
| GET | `/pesagens/carregamentos` | `balanca`, `admin` | Lista carregamentos concluídos (peso líquido + tipo). |

### 4.4 CRUD de entidades

| Entidade | Métodos | Role | Observações |
|----------|---------|------|-------------|
| `/plantas` (unidades) | GET list, GET one, POST, PUT, DELETE | `admin` (GET: autenticado) | `codigo`, `nome`, `cidade`, `uf`. |
| `/veiculos` (caminhões) | GET list, GET one, POST, PUT, DELETE | `admin` (GET: autenticado) | `placa` (única). |
| `/pontos` | GET list, GET one, POST, PUT, DELETE | `admin` | `codigo`, `tipo` (`portaria_entrada`\|`portaria_saida`\|`balanca`), `planta_id`. |
| `/usuarios` | GET list, GET one, POST, PUT, DELETE | `admin` | `nome`, `email`, `senha`, `role`, `ativo`. |

Regras de CRUD:
- DELETE: retorna `204`. Se houver dependência (ex.: unidade com pontos), retorna `409`.
- POST/PUT validam unicidade (`planta.codigo`, `veiculo.placa`, `ponto.codigo`, `usuario.email`).
- Senha nunca é retornada nas respostas (schemas `Out` sem campo de senha).

### 4.5 Infra / docs

| Método | Rota | Role | Descrição |
|--------|------|------|-----------|
| GET | `/health` | pública | Health check (`{"status":"ok"}`). |
| GET | `/docs`, `/redoc`, `/openapi.json` | pública | Documentação OpenAPI gerada automaticamente. |

---

## 5. Modelo de dados

Banco: PostgreSQL (mantém o `docker-compose.yml` atual). Recomenda-se **Alembic** para
migrações (hoje usa `Base.metadata.create_all`).

### 5.1 Tabelas de referência / cadastro

- `plantas` — **mantém** (id, codigo, nome, cidade, uf, criado_em).
- `pontos` — **mantém** (id, planta_id, codigo, tipo, descricao, camera_url, criado_em).
- `veiculos` — **mantém** (id, placa, criado_em, atualizado_em).
- `usuarios` — **nova** (id, nome, email único, senha_hash, role, ativo, criado_em).

### 5.2 Tabelas operacionais (2 tabelas)

O `visita_id` (UUID) é o agrupador de uma visita completa: **1 entrada → N pesagens → 1 saída**.
Não há terceira tabela.

**Tabela 1 — `portaria_movimentacoes`** (somente movimentação da portaria; 1 linha por passagem)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | int PK | |
| `visita_id` | uuid | Agrupa entrada + saída de uma visita. |
| `planta_id` | FK | Unidade. |
| `ponto_id` | FK | Portaria entrada/saída. |
| `veiculo_id` | FK (nullable) | Caminhão (criado/vinculado na hora). |
| `placa` | str(8) | Rastreio (normalizada). |
| `placa_raw` / `formato` / `confianca` | str/str/float | Resultado do ANPR. |
| `operacao` | str(10) | `entrada` \| `saida`. |
| `foto_frontal_path` | str(300) | Foto da frente do caminhão salva em disco. |
| `status_visita` | str(10) | `aberta` \| `fechada` (preenchido na linha de entrada). |
| `capturado_em` / `criado_em` | timestamptz | |

**Tabela 2 — `pesagens`** (pesagens **e** carregamentos)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | int PK | |
| `visita_id` | uuid | Liga à portaria. |
| `planta_id` / `ponto_id` | FK | Unidade / balança. |
| `veiculo_id` | FK (nullable) | Caminhão. |
| `placa` | str(8) | Rastreio. |
| `foto_frontal_path` | str(300) | Foto da frente. |
| `peso` | float | Peso em **toneladas** (ex.: `99.99`). |
| `desvio` / `amostras` | float/int (nullable) | Dispersão (opcional; sem serial, vira `null`). |
| `ordem` | int | `1` = pesagem de entrada, `2` = pesagem de saída (dentro da visita). |
| `peso_entrada` / `peso_saida` | float (nullable) | Preenchidos na pesagem de saída. |
| `peso_liquido` | float (nullable) | `abs(peso_saida - peso_entrada)`. |
| `tipo_carregamento` | str(20) (nullable) | `carregamento` \| `descarregamento` \| `sem_pesagem`. |
| `capturado_em` / `criado_em` | timestamptz | |

> **Carregamento** vive na mesma tabela de pesagens: a linha de saída (`ordem=2`) recebe
> `peso_entrada`, `peso_saida`, `peso_liquido` e `tipo_carregamento` ao fechar a visita.
> Se a visita fechar sem pesagem, gera-se um registro com `tipo_carregamento='sem_pesagem'`.

### 5.3 Tabelas removidas

- `movimentacoes` → substituída por `portaria_movimentacoes` + `pesagens`.
- `eventos_placa` → absorvida por `portaria_movimentacoes`.

---

## 6. Regras de negócio (máquina de estados da visita)

Estado atual em `app/services/movimentacao_service.py` — será adaptado.

1. **Entrada** (`operacao=entrada`):
   - ANPR extrai placa (ou usa `placa` do body se enviada).
   - `obter_ou_criar_veiculo(placa)`.
   - Se já existe visita aberta para `(planta, veiculo)`, reutiliza; senão cria `visita_id` novo.
   - Insere linha em `portaria_movimentacoes` com `status_visita='aberta'`.
2. **Pesagem** (`peso`):
   - ANPR extrai placa (ou usa `placa` do body).
   - Vincula à visita aberta. Se não houver visita aberta, abre uma (PENDENTE: exigir entrada
     prévia na portaria? Comportamento atual permite balança abrir visita).
   - Define `ordem`: 1ª pesagem = entrada, 2ª = saída. Pesagens adicionais (PENDENTE: permitir
     ou bloquear?) — comportamento atual considera apenas as duas primeiras.
3. **Saída** (`operacao=saida`):
   - ANPR extrai placa (ou usa `placa`).
   - Insere linha em `portaria_movimentacoes` com `operacao='saida'`.
   - Fecha a visita: atualiza `status_visita='fechada'`.
   - Se há 2 pesagens → calcula `peso_liquido` + `tipo_carregamento` e grava na pesagem de saída.
   - Se 1 pesagem → `tipo_carregamento='pesagem_parcial'` (PENDENTE: manter esse tipo?).
   - Se 0 pesagens → `tipo_carregamento='sem_pesagem'`.

---

## 7. Contratos dos endpoints operacionais (exemplos)

### 7.1 `POST /portaria/eventos`

```
Content-Type: multipart/form-data
  foto     (file)   — imagem frontal do caminhão
  operacao (str)    — "entrada" | "saida"
  placa    (str)    — opcional
```

Resposta `201`:
```json
{
  "id": 12,
  "visita_id": "7f3c...",
  "placa": "ABC1D23",
  "formato": "mercosul",
  "confianca": 0.98,
  "operacao": "entrada",
  "status_visita": "aberta",
  "foto_frontal_path": "data/imagens/2026...jpg",
  "capturado_em": "2026-08-20T14:00:00Z"
}
```

Erros: `400` imagem inválida / operacao inválida; `404` ponto não encontrado;
`422` placa não reconhecida e não enviada no body.

### 7.2 `POST /pesagens`

```
Content-Type: multipart/form-data
  foto  (file)   — imagem frontal do caminhão
  peso  (float)  — 99.99 (toneladas)
  placa (str)    — opcional
```

Resposta `201`:
```json
{
  "id": 8,
  "visita_id": "7f3c...",
  "placa": "ABC1D23",
  "peso": 99.99,
  "ordem": 1,
  "peso_liquido": null,
  "tipo_carregamento": null,
  "capturado_em": "2026-08-20T14:10:00Z"
}
```

Erros: `400` imagem inválida / peso <= 0; `404` ponto balança não encontrado;
`422` placa não reconhecida e não enviada no body.

---

## 8. Autenticação (detalhes)

- Libs: `pyjwt` (JWT), `bcrypt` (hash de senha). `SECRET_KEY` e `ACCESS_TOKEN_EXPIRE_MINUTES` em `.env`.
- Middleware/dependência `get_current_user` decodifica o bearer token, valida `exp` e carrega o
  usuário do banco.
- Dependência `require_role("admin")` etc. para proteger rotas por perfil.
- Seed cria um usuário `admin` inicial (senha via env, ex.: `ADMIN_PASSWORD`).
- Atualizar `.env.example` com `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ADMIN_EMAIL`,
  `ADMIN_PASSWORD`.

---

## 9. Estrutura de arquivos proposta (backend)

```
backend/
  alembic/                     # (recomendado) migrações
  app/
    auth/
      security.py              # hash senha, criar/validar JWT
      deps.py                  # get_current_user, require_role
    routers/
      auth.py                  # /auth/login, /auth/refresh, /auth/me
      portaria.py              # /portaria/*
      pesagem.py               # /pesagens*
      plantas.py               # CRUD /plantas
      veiculos.py              # CRUD /veiculos
      pontos.py                # CRUD /pontos
      usuarios.py              # CRUD /usuarios
    services/
      visita_service.py        # máquina de estados da visita
      pesagem_service.py       # registro de pesagem + carregamento
      plate_service.py         # obter_ou_criar_veiculo (mantém/adapta)
    anpr/                      # mantém (plate.py, recognizer.py)
    config.py                  # + SECRET_KEY, token expire, dirs
    db.py                      # mantém
    models.py                  # novos modelos (2 tabelas + usuarios)
    schemas.py                 # novos schemas
    main.py                    # refatorado: só rotas/mount, sem static/balanca
  scripts/seed.py              # atualizado (planta, pontos, usuário admin)
  tests/                       # (novo) testes de rotas/serviços
```

**Remover:** `app/balanca/*` (serial/simulador/websocket), `app/static/*` (front sai do backend),
rotas antigas (`/placas/reconhecer`, `/eventos`, `/movimentacoes`, `/ws/peso`, `/balanca/*`).

---

## 10. Documentação atualizada

- **OpenAPI/Swagger** automático em `GET /docs` (FastAPI já gera a partir dos schemas).
- **`docs/API.md`** (novo): visão geral, autenticação (com exemplo de login + bearer), exemplos
  de request/response para `/portaria/eventos`, `/pesagens`, CRUD e códigos de erro.
- **`README.md`**: atualizar para descrever a API (não mais a tela de teste), como subir
  (`docker compose up db`, `uvicorn`), variáveis de ambiente e como consumir.
- `.env.example` atualizado com as novas variáveis.

---

## 11. Ordem de implementação (checklist)

1. Atualizar `config.py`/`.env.example` (SECRET_KEY, expiração, dirs).
2. Criar `models.py` novo (usuarios + 2 tabelas operacionais) e `Usuarios`; remover modelos antigos.
3. Adicionar Alembic (ou manter `create_all` + script de reset para v1).
4. Implementar `auth/security.py` + `deps.py`.
5. Implementar `routers/auth.py`.
6. Adaptar `services/` (visita + pesagem + plate) à nova máquina de estados.
7. Implementar `routers/portaria.py` e `routers/pesagem.py`.
8. Implementar CRUD `plantas`, `veiculos`, `pontos`, `usuarios`.
9. Refatorar `main.py` (remover static/balanca/ws, registrar routers).
10. Atualizar `scripts/seed.py`.
11. Escrever `docs/API.md`, atualizar `README.md` e `.env.example`.
12. Testes (`pytest`) + `mypy` + `ruff`.

---

## 12. Pendências a confirmar na execução

1. Balança pode abrir visita sem entrada prévia na portaria? Bloquear pesagem
2. Mais de 2 pesagens por visita: permitir ou bloquear? Permitir
3. Manter o tipo `pesagem_parcial` (1 pesagem) ou simplificar para `sem_pesagem`? Manter tipo, o veiculo pode pesar uma vez e pesar novamente depois de horas, a placa faz a ligacao
4. Unidade de peso armazenada: **toneladas** (conforme request) — confirmar se o legado em kg
   (ex.: `15480.0`) será convertido/migrado. faca a conversao
5. Renovar JWT via refresh token ou apenas re-login na v1? refresh token
6. Alembic agora ou manter `create_all` temporariamente? alembic
