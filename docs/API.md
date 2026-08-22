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
| `400` | Imagem inválida, operação/tipo inválido ou peso <= 0 |
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

- As credenciais das câmeras são globais, via variáveis de ambiente (`DVR_USER`,
  `DVR_PASSWORD`, `DVR_AUTH=digest|basic`, `DVR_TIMEOUT`).
- Para descobrir/validar a URL do seu equipamento, use
  `python -m scripts.dvr_probe --host <IP> --password <senha>`.

## Unidade de peso

Toda a API usa **toneladas**. O legado do sistema de teste armazenava **kg**;
qualquer importação de pesos legados deve dividir o valor por 1000.
