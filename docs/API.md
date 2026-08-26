# API de Operação — controleLogistica

API pura (FastAPI) para a fase de operação, consumida pelos frontends da
**Portaria** e da **Balança**.

- **Portaria** envia `operacao` (`entrada` | `saida`) + `camera` (URL de snapshot) +
  `unidade`. O backend captura o snapshot e reconhece a placa via ANPR.
- **Balança** envia `peso` (em toneladas) + `tipo` (`tara` | `bruto`) + `camera` +
  `unidade`. O backend também captura o snapshot.

`camera` é a **URL completa do snapshot** da câmera (o front decide qual câmera
usar, então o sistema se adapta a qualquer quantidade de câmeras) e `unidade` é
o **código** da planta (ex.: `SAO_JOAO`).

## Visão geral

| Recurso | Rotas | Perfis |
|---------|-------|--------|
| Autenticação | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` | pública / autenticada |
| Câmera (ANPR) | `POST /camera/reconhecer-placa` | pública |
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

## Câmera — Reconhecimento de Placa (ANPR)

`POST /camera/reconhecer-placa` — JSON (`application/json`):

Este endpoint recebe as credenciais da câmera IP diretamente no request,
captura um snapshot, roda o ANPR (PaddleOCR) e retorna a placa do veículo.
**Não requer autenticação.**

### Request body

| Campo | Tipo | Obrigatório | Default | Descrição |
|-------|------|-------------|---------|-----------|
| `host` | str | sim | — | IP da câmera (ex.: `192.168.11.241`) |
| `port` | int | não | `80` | Porta HTTP da câmera |
| `user` | str | sim | — | Usuário da câmera (ex.: `admin`) |
| `password` | str | sim | — | Senha da câmera |
| `auth` | str | não | `"digest"` | Tipo de autenticação: `"digest"` ou `"basic"` |
| `camera_url` | str | não | `null` | URL completa do snapshot. Se omitida, o sistema tenta descobrir automaticamente entre 13 padrões comuns (Intelbras/Dahua/Hikvision) |

**Exemplo com URL explícita:**

```json
{
  "host": "192.168.11.241",
  "port": 80,
  "user": "admin",
  "password": "minha_senha",
  "auth": "digest",
  "camera_url": "http://192.168.11.241/ISAPI/Streaming/channels/101/picture"
}
```

**Exemplo com probe automático** (sem `camera_url`):

```json
{
  "host": "192.168.11.241",
  "port": 80,
  "user": "admin",
  "password": "minha_senha",
  "auth": "digest"
}
```

O sistema testa os seguintes endpoints automaticamente:

```
/cgi-bin/snapshot.cgi
/cgi-bin/snapshot.cgi?channel=1
/cgi-bin/snapshot.cgi?channel=0
/webcapture.jpg?command=snap&channel=1
/tmpfs/auto.jpg
/snapshot.jpg
/jpg/image.jpg
/onvif/snapshot
/cgi-bin/images_cgi?channel=0&subtype=0
/cgi-bin/currentpic.cgi
/Streaming/channels/1/picture
/ISAPI/Streaming/channels/101/picture
/cap.jpg
```

Cada endpoint é testado com Digest e Basic auth. O primeiro que retornar
HTTP 200 com conteúdo é utilizado.

### Response `200`

```json
{
  "placa": "ABC1D23",
  "formato": "mercosul",
  "confianca": 0.9876,
  "raw": "ABCI1D23",
  "camera_url_encontrada": "http://192.168.11.241/ISAPI/Streaming/channels/101/picture",
  "foto_path": "C:\\projetos\\controleLogistica\\data\\imagens\\20260826T153000123456.jpg"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `placa` | str | Placa normalizada (Mercosul: `ABC1D23`, Antiga: `ABC1234`) |
| `formato` | str | `"mercosul"` ou `"antiga"` |
| `confianca` | float | Score de confiança do OCR (0 a 1) |
| `raw` | str | Texto bruto capturado pelo OCR antes da normalização |
| `camera_url_encontrada` | str \| null | URL que retornou imagem válida (preenchido quando probe automático foi usado) |
| `foto_path` | str \| null | Caminho absoluto da imagem salva em disco |

### Responses de erro

| Código | Situação |
|--------|----------|
| `400` | Credenciais inválidas ou `camera_url` malformada |
| `422` | Placa não reconhecida na imagem capturada |
| `502` | Falha ao conectar ou capturar imagem da câmera (IP inacessível, timeout, autenticação recusada, ou nenhum endpoint de snapshot respondeu) |

### Exemplo com curl

```bash
# Com URL explícita
curl -X POST http://localhost:8000/camera/reconhecer-placa \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.11.241",
    "user": "admin",
    "password": "minha_senha",
    "auth": "digest",
    "camera_url": "http://192.168.11.241/ISAPI/Streaming/channels/101/picture"
  }'

# Com probe automático
curl -X POST http://localhost:8000/camera/reconhecer-placa \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.11.241",
    "user": "admin",
    "password": "minha_senha"
  }'
```

### Notas para o front

- O endpoint é **público** (não requer token de autenticação).
- Se `camera_url` for omitido, o probe automático pode levar alguns segundos
  (testa 13 endpoints × 2 modos de auth).
- O campo `confianca` indica a qualidade do reconheceimento. Valores acima de
  `0.9` são considerados confiáveis.
- A imagem capturada é salva em disco e o caminho é retornado em `foto_path`.
- O front pode usar `camera_url_encontrada` para cache futuro (evitar probe
  repetido para a mesma câmera).

## Portaria

`POST /portaria/eventos` — formulário (`application/x-www-form-urlencoded`):

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `operacao` | str | sim | `entrada` ou `saida` |
| `camera` | str | sim | URL completa do snapshot (ex.: `http://IP/ISAPI/Streaming/channels/101/picture`) |
| `unidade` | str | sim | Código da unidade/planta (ex.: `SAO_JOAO`) |
| `placa` | str | não | Placa explícita (ignora o OCR) |

A `operacao` define se a passagem abre (`entrada`) ou fecha (`saida`) a visita. O
backend captura o snapshot da URL `camera` e roda o ANPR nela. Falha de captura →
`502`.

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

`POST /pesagens` — formulário (`application/x-www-form-urlencoded`):

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `peso` | float | sim | Peso em **toneladas** (ex.: `99.99`) |
| `tipo` | str | sim | `tara` (vazio) ou `bruto` (cheio) |
| `camera` | str | sim | URL completa do snapshot |
| `unidade` | str | sim | Código da unidade/planta (ex.: `SAO_JOAO`) |
| `placa` | str | não | Placa explícita (ignora o OCR) |

Resposta `201`:

```json
{
  "id": 8,
  "visita_id": "7f3c...",
  "placa": "ABC1D23",
  "peso": 99.99,
  "ordem": 1,
  "tipo": "tara",
  "peso_liquido": null,
  "tipo_carregamento": null,
  "capturado_em": "2026-08-20T14:10:00Z"
}
```

> A pesagem exige uma **visita aberta** na portaria (entrada registrada e ainda
> não saída). Sem entrada prévia, retorna `409`.

## Ciclo da visita

`visita_id` (UUID) agrupa: **1 entrada → pesagens → 1 saída**.

- A **entrada** abre (ou reutiliza) uma visita.
- Cada **pesagem** é anexada à visita aberta, com um `tipo` (`tara` ou `bruto`).
- A **saída** fecha a visita e calcula, na última pesagem:
  - `peso_entrada` = último peso de `tara` (caminhão vazio);
  - `peso_saida` = último peso de `bruto` (caminhão cheio);
  - `peso_liquido = bruto - tara`;
  - `tipo_carregamento`:
    - sem pesagens → `sem_pesagem`;
    - só tara ou só bruto → `pesagem_parcial`;
    - `carregamento` (bruto > tara) ou `descarregamento` (bruto < tara).

## Códigos de erro

| Código | Situação |
|--------|----------|
| `400` | Imagem inválida, operação/tipo inválido, peso <= 0 ou credenciais inválidas |
| `401` | Token ausente/inválido/expirado |
| `403` | Perfil sem permissão |
| `404` | Unidade ou ponto de coleta não encontrado |
| `409` | Conflito (registro duplicado, dependência, sem visita aberta) |
| `422` | Placa inválida ou não reconhecida (e não enviada), ou campo obrigatório ausente |
| `502` | Falha ao capturar o snapshot da câmera (rede/autenticação) |

## Câmeras (IP Intelbras)

A imagem não é enviada pelo frontend — ele envia apenas a **URL de snapshot** da
câmera e o backend faz a captura. Como cada câmera pode ter firmware de OEM
diferente, a URL completa é flexível:

```
# Hikvision/ISAPI (linha atual)
http://IP/ISAPI/Streaming/channels/101/picture

# Dahua
http://IP/cgi-bin/snapshot.cgi
```

**Duas formas de usar:**

1. **Endpoint portaria/balança** (`POST /portaria/eventos`, `POST /pesagens`):
   o front envia a `camera` (URL de snapshot) no body. As credenciais são
   globais (`.env`).

2. **Endpoint de reconhecimento** (`POST /camera/reconhecer-placa`): o front
   envia IP + credenciais no body. Útil para telas de configuração ou quando
   o front não conhece a URL de snapshot da câmera. Ver seção
   [Câmera — Reconhecimento de Placa (ANPR)](#câmera--reconhecimento-de-placa-anpr).

- As credenciais das câmeras são globais, via variáveis de ambiente (`DVR_USER`,
  `DVR_PASSWORD`, `DVR_AUTH=digest|basic`, `DVR_TIMEOUT`).
- Para descobrir/validar a URL do seu equipamento, use
  `python -m scripts.dvr_probe --host <IP> --password <senha>`.

## Unidade de peso

Toda a API usa **toneladas**. O legado do sistema de teste armazenava **kg**;
qualquer importação de pesos legados deve dividir o valor por 1000.
