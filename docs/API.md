# API de Operação — controleLogistica

API pura (FastAPI) para a fase de operação, consumida pelos frontends da
**Portaria** e da **Balança**.

- **Portaria** envia foto da frente do caminhão + `operacao` (`entrada` | `saida`) + `unidade`.
- **Balança** envia foto da frente do caminhão + `peso` (em toneladas) + `unidade`.

`unidade` é o **código** da planta (ex.: `PLT001`).

## Visão geral

| Recurso | Rotas | Perfis |
|---------|-------|--------|
| Autenticação | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` | pública / autenticada |
| Portaria | `POST /portaria/eventos`, `GET /portaria/eventos`, `GET /portaria/abertas` | `portaria`, `admin` |
| Balança | `POST /pesagens`, `GET /pesagens`, `GET /pesagens/carregamentos` | `balanca`, `admin` |
| Unidades | `/plantas` (CRUD) | GET: autenticado; escrita: `admin` |
| Caminhões | `/veiculos` (CRUD) | GET: autenticado; escrita: `admin` |
| Pontos de coleta | `/pontos` (CRUD) | `admin` |
| Usuários | `/usuarios` (CRUD) | `admin` |

Documentação interativa (OpenAPI) em `GET /docs`.

## Autenticação

OAuth2 password flow. Faça login para obter os tokens:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

Resposta:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Use o token nas demais rotas:

```bash
curl http://localhost:8000/auth/me -H "Authorization: Bearer <access_token>"
```

Para renovar sem novo login, use `POST /auth/refresh` com `{"refresh_token": "..."}`.

Perfis: `admin`, `portaria`, `balanca`.

## Portaria

`POST /portaria/eventos` — multipart:

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `foto` | file | sim | Foto da frente do caminhão |
| `operacao` | str | sim | `entrada` ou `saida` |
| `unidade` | str | sim | Código da unidade/planta (ex.: `PLT001`) |
| `placa` | str | não | Placa explícita (ignora o OCR) |

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
  "foto_frontal_path": "data/imagens/2026....jpg",
  "capturado_em": "2026-08-20T14:00:00Z"
}
```

## Balança

`POST /pesagens` — multipart:

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `foto` | file | sim | Foto da frente do caminhão |
| `peso` | float | sim | Peso em **toneladas** (ex.: `99.99`) |
| `unidade` | str | sim | Código da unidade/planta (ex.: `PLT001`) |
| `placa` | str | não | Placa explícita (ignora o OCR) |

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

> A pesagem exige uma **visita aberta** na portaria (entrada registrada e ainda
> não saída). Sem entrada prévia, retorna `409`.

## Ciclo da visita

`visita_id` (UUID) agrupa: **1 entrada → N pesagens → 1 saída**.

- A **entrada** abre (ou reutiliza) uma visita.
- Cada **pesagem** é anexada à visita aberta (`ordem` = 1, 2, 3, ...).
- A **saída** fecha a visita e calcula, na última pesagem:
  - `peso_entrada` (1ª pesagem) e `peso_saida` (última pesagem);
  - `peso_liquido = |peso_saida - peso_entrada|`;
  - `tipo_carregamento`:
    - 0 pesagens → `sem_pesagem` (visita fechada sem registro de peso);
    - 1 pesagem → `pesagem_parcial`;
    - 2+ pesagens → `carregamento` (peso aumentou) ou `descarregamento` (diminuiu).

## Códigos de erro

| Código | Situação |
|--------|----------|
| `400` | Imagem inválida, operação inválida ou peso <= 0 |
| `401` | Token ausente/inválido/expirado |
| `403` | Perfil sem permissão |
| `404` | Recurso, unidade ou ponto de coleta não encontrado |
| `409` | Conflito (registro duplicado, dependência, sem visita aberta) |
| `422` | Placa inválida ou não reconhecida (e não enviada no corpo) |

## Unidade de peso

Toda a API usa **toneladas**. O legado do sistema de teste armazenava **kg**;
qualquer importação de pesos legados deve dividir o valor por 1000.
