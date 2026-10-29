# QA_API_TESTING — Fase 1: Pruebas de APIs de Emisión DTE

**Ambiente:** QA · **Fecha:** 2026-08-28 · **Autor:** QA Automation
**Estado:** Framework + matriz + colección completos. **Ejecución masiva bloqueada** por límite de tokens del servicio de autenticación QA (ver §6 y DEF-08).

---

## 1. Objetivo

Probar de forma exhaustiva las APIs REST de emisión de Documentos Tributarios Electrónicos (DTE) de Klap —
Factura Afecta (33), Factura Exenta (34) y Nota de Crédito (61)— contra el ambiente **QA**, identificando
errores, inconsistencias de contrato, problemas de validación tributaria, de autenticación/autorización y de
seguridad, y dejando como entregables una **matriz de pruebas trazable**, un **framework Python/pytest**,
una **Postman Collection** y este reporte.

## 2. Alcance

| Servicio | Base QA | Endpoints cubiertos |
|---|---|---|
| Recepción FE | `…/central/dte/fe/recepcion` | `POST /v1/factura`, `POST /v1/app/factura`, `GET /v1/regiones`, `GET /v1/regiones/{id}/comunas`, `GET /v1/rubros`, `GET /v1/rubros/{id}/acteco`, y variantes `/v1/app/*` |
| Recepción NC | `…/central/dte/fe/recepcion-nc` | `POST /v1/nota-credito`, `POST /v1/app/nota-credito` |
| Consultas FENC | `…/central/dte/fe/consultas` | `POST /v1/app/dte/{tipo}/{folio}` con body `{rutEmisor}` (evidencia / verificación de DTE emitidos) |
| Auth | `https://apiqa.mcdesaqa.cl/public/auth/web/v1/login` | login de comercio (obtención de JWT) |

Fuera de alcance: DEV (estructura preparada, sin ejecutar), aceptación SII de los DTE (proceso asíncrono de
otro servicio), `actuator/*` (protegidos por AWS SigV4, no consumibles con Bearer).

## 3. Ambiente

- **QA** exclusivamente. Emisor de pruebas: `10471336-K` (= `sub` del JWT).
- El manual v1.5 indica bases `apiqa-cloud…/recepcion`; verificado en vivo.
- **DEV no se ejecutó** por indicación del encargo; la colección y el framework quedan parametrizados para DEV.

## 4. Herramientas

- **Python 3.12 + pytest 8.3** — framework de pruebas automatizadas (`qa-api-tests/`).
- **requests** — cliente HTTP; wrapper propio (`utils/api_client.py`) que estructura y enmascara cada intercambio.
- **pytest-html** — reporte navegable (`reports/report.html`).
- **jsonschema** — validación de estructura de respuestas.
- **Postman Collection v2.1** — `DTE API Testing` + environments `QA` / `DEV` (generada por `scripts/gen_postman.py`).
- Guard de presupuesto de DTE (`utils/dte_budget.py`) + evidencia por caso (`reports/evidence/*.json`, `emitidos.csv`).

## 5. Estrategia

1. **Inspección** de los 3 manuales de integración + colección `Pruebas Api Facturacion. mcs klap` +
   **reconocimiento read-only en vivo** contra QA (login, catálogos, health, métodos incorrectos).
   → `docs/01_inventario_apis.md`.
2. **Diseño de matriz** (~440 casos) organizada por *suite → escenario → caso*, cubriendo: camino feliz,
   datos inválidos/incompletos/nulos, tipos incorrectos, límites y valores extremos, campos desconocidos,
   duplicidad/idempotencia/concurrencia, autenticación/autorización, seguridad (SQLi/XSS/path traversal/
   Content-Type/métodos HTTP), reglas tributarias (neto/IVA/total, IVA en exenta), batería de RUT,
   consistencia entre catálogos, y performance controlada. → `docs/02_matriz_pruebas.md`.
3. **Aserciones alineadas al contrato documentado**, no a "debería pasar": un `FAIL` es un candidato a
   defecto (Regla 3 del encargo). Ningún comportamiento inesperado se corrige (Regla 8): se registra.
4. **Control de impacto en QA:** todo test que puede emitir un DTE lleva el marker `emision`; un guard con
   `--dte-budget` hace `skip` al alcanzar el tope pactado (**≤ 50 DTE 33/34 + ≤ 4 NC**, duplicidad ≤ 10,
   concurrencia ≤ 5 hilos). Cada folio emitido queda en `reports/evidence/emitidos.csv`.
5. **Ejecución contra QA** en 2 pasadas: (a) `-m "not emision"` (negativos, sin consumo), (b) `-m emision`
   con presupuesto. Performance opt-in (`-m perf`).
6. **Análisis** → `reports/resumen_ejecucion.md` + este reporte + defectos.

## 6. Matriz de pruebas — cifras

| | |
|---|---|
| Casos diseñados (matriz) | ~440 |
| Casos automatizados (pytest) | **353** |
| Requests en Postman Collection | 70 (jerarquía Ambiente → API → Escenario → Caso) |
| PASS | *pendiente ejecución completa* |
| FAIL | *pendiente* (hallazgos ya confirmados en §8) |
| BLOCKED | Auth QA (ver abajo), happy-path NC (depende de aceptación SII) |
| NOT_EXECUTED | resto, hasta completar pasada |

### Estado de ejecución

El **servicio de login de QA devolvió `code 88 "Máximo de tokens excedido" (HTTP 403)`** tras generar ~15
tokens durante el reconocimiento y la puesta a punto del framework, y **no se recuperó dentro de la ventana
de trabajo** (>40 min). Esto **bloquea la pasada masiva** (todos los endpoints salvo `login` exigen `Bearer`
válido en el gateway). Es en sí mismo un hallazgo (**DEF-08**): un límite de tokens no documentado que puede
dejar fuera de servicio a un integrador legítimo, sin endpoint de `logout`/revocación (`/logout` → 500 con
fuga de IP interna).

**Para completar la ejecución** (cuando el auth se libere, o con un JWT vigente en `QA_TOKEN` del `.env`):

```bash
cd qa-api-tests
pytest -m "not emision"                 # ~250 negativos, sin consumo de folios
pytest -m "emision" --dte-budget=54     # emisión controlada
pytest -m "perf"                        # performance (opt-in)
python scripts/build_matriz.py          # consolida reports/resumen_ejecucion.md + matriz_resultados.csv
```

Los resultados parciales ya capturados (canal App/POS sin token) están en `reports/evidence/`.

## 7. Resultados por API

*(se completará con `scripts/build_matriz.py` tras la pasada completa; a la fecha:)*

| Endpoint | Total tests | PASS | FAIL | BLOCKED | Observaciones |
|---|---|---|---|---|---|
| `GET /v1/regiones` (+comunas/rubros/acteco) | ~110 | ✔ verificado read-only OK | — | auth battery pendiente | catálogos responden 200, `total==len`, ids únicos |
| `GET /v1/app/*` (catálogos) | 9 | 0 | **4** | 2 | **todos 401 sin token** (contradice manual) → DEF-01 |
| `POST /v1/factura` (33) | 148 | pend. | pend. | — | reconocimiento: método incorrecto → 500 (DEF-02) |
| `POST /v1/factura` (34) | 21 | pend. | pend. | — | foco: IVA en exenta |
| `POST /v1/nota-credito` (61) | 31 | pend. | pend. | happy | requiere factura ACEPTADA por SII |
| `POST /v1/app/factura` | 9 | pend. | pend. | probable | canal tras 401 (DEF-01) |
| `POST /v1/app/dte/{t}/{f}` (consultas) | — | — | **1** | — | folio inexistente → **500** en vez de 404/403 (DEF-03) |
| `login` | — | — | **1** | — | cap de tokens no documentado (DEF-08) |

## 8. Defectos encontrados

> Confirmados mediante reconocimiento read-only en vivo (2026-08-28) y/o revisión de contrato. Severidad preliminar.

### DEF-01 — Canal "App/POS sin JWT" no accesible en QA · **Severidad: ALTA**
- **API:** `GET /v1/app/regiones`, `/v1/app/regiones/{id}/comunas`, `/v1/app/rubros`, `/v1/app/rubros/{id}/acteco`, `POST /v1/app/factura`, `POST /v1/app/nota-credito`.
- **Descripción:** el manual v1.5 §7 describe estos endpoints como accesibles **sin token JWT**. En QA, el API Gateway responde `401 {"message":"Unauthorized"}` a toda petición sin `Authorization: Bearer`.
- **Pasos:** `curl https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion/v1/app/regiones`
- **Esperado:** `200` con catálogo (contrato manual §7). **Actual:** `401 {"message":"Unauthorized"}`.
- **Impacto:** el canal presencial/POS descrito en la documentación no es utilizable en QA; toda la funcionalidad "sin JWT" (incl. emisión App) queda inverificable como está documentada.

### DEF-02 — Método HTTP no permitido devuelve 500 en vez de 405 · **Severidad: MEDIA**
- **API:** `POST/PUT/DELETE/PATCH` sobre `GET /v1/regiones`; `GET` sobre `POST /v1/factura`.
- **Pasos:** `curl -X POST …/recepcion/v1/regiones -H "Authorization: Bearer <jwt>" -d '{}'` → `500`; `curl …/recepcion/v1/factura -H "Authorization: Bearer <jwt>"` (GET) → `500`.
- **Esperado:** `405 Method Not Allowed`. **Actual:** `500 {"codigoRespuesta":"99","mensajeRespuesta":"Error interno del servidor"}`.
- **Impacto:** un cliente que use el verbo equivocado recibe un 5xx (parece caída del servicio) en vez de un error de cliente claro; enmascara problemas y puede disparar alertas/reintentos.

### DEF-03 — Consulta de folio inexistente/ajeno devuelve 500 · **Severidad: ALTA**
- **API:** `POST /central/dte/fe/consultas/v1/app/dte/33/106` (body `{rutEmisor}`).
- **Esperado:** `404 FACTURA_NO_ENCONTRADA` o `403 ACCESO_NO_AUTORIZADO` (manual consultas §10). **Actual:** `500 {"codigoRespuesta":"99","mensajeRespuesta":"Error interno del servidor. Intente nuevamente."}`.
- **Impacto:** los integradores no pueden distinguir "no existe" de "error del servicio"; rompe flujos de verificación post-emisión y de elegibilidad de NC.

### DEF-04 — `actuator/health|info` inaccesibles con Bearer + fuga de infraestructura · **Severidad: MEDIA**
- **API:** `GET /mcs-central-be-recepcion-fe/actuator/health`.
- **Descripción:** el manual §13 dice que requieren `Authorization: Bearer <token>`. En QA responden `403` con un error de **AWS SigV4**: `Invalid key=value pair (missing equal-sign) in Authorization header (hashed with SHA-256 and encoded with Base64): '…='`.
- **Impacto:** (a) contrato incorrecto — el monitoreo documentado no funciona; (b) **information disclosure**: el mensaje revela el mecanismo de autenticación interno y devuelve un hash del header enviado.

### DEF-05 — Endpoint `/logout` inexistente filtra IP y ruta internas · **Severidad: MEDIA**
- **API:** `POST https://apiqa.mcdesaqa.cl/public/auth/web/v1/logout`.
- **Actual:** `500 {"code":99,"message":"RESTEASY003210: Could not find resource for full path: https://10.179.20.11:8443/mc_auth_v2/logout"}`.
- **Impacto:** **information disclosure** (IP privada `10.179.20.11`, puerto `8443`, nombre de artefacto `mc_auth_v2`, framework RESTEasy). Además no existe forma de revocar tokens (ver DEF-08).

### DEF-06 — Mensaje de error 404 de catálogos no coincide con el manual · **Severidad: BAJA**
- **API:** `GET /v1/regiones/99/comunas`, `GET /v1/rubros/99/acteco`.
- **Esperado (manual):** `"Region no encontrada"` / `"Rubro no encontrado"`. **Actual:** `404 {"codigoRespuesta":"404","mensajeRespuesta":"No fue posible obtener la información solicitada"}` (genérico para ambos).
- **Impacto:** menor; documentación desalineada.

### DEF-07 — Inconsistencia de contrato `giro`/`comuna` entre servicios · **Severidad: MEDIA**
- **Descripción:** en `POST /v1/factura` el `receptor.giro` y `receptor.comuna` son **integer (id de catálogo)**; en `POST /v1/nota-credito` los mismos campos son **string (texto libre)**. Un integrador que reutiliza el objeto `receptor` entre factura y NC fallará.
- **Impacto:** fricción de integración y riesgo de datos inconsistentes entre la factura y su NC.

### DEF-08 — Límite de tokens de login no documentado, sin revocación · **Severidad: ALTA**
- **API:** `POST /public/auth/web/v1/login` (y `v2`/`verticalqa`).
- **Descripción:** tras ~15 logins del mismo comercio en ~45 min, el servicio responde `403 {"code":88,"message":"Máximo de tokens excedido"}` y **deja de emitir tokens**; además tokens previamente válidos empezaron a ser rechazados por el gateway (`403 "explicit deny in an identity-based policy"`). No hay endpoint de `logout`/revocación (DEF-05). El límite y su ventana de reset no están documentados.
- **Pasos:** repetir `POST /login` con credenciales válidas hasta obtener `code 88`.
- **Impacto:** **un integrador legítimo puede quedar fuera de servicio** (no puede emitir DTE) por reintentos, despliegues o múltiples instancias, sin mecanismo de recuperación ni documentación. Bloqueó la ejecución masiva de esta fase.

### DEF-09 (menor, colección) — La colección `mundo feliz` tiene la URL de NC corrupta
- El request "Camino bonito Emision 61" apunta a `…/recepcion/v1/nota-credito` (carácter de control `` y base path incorrecto — debe ser `…/recepcion-nc/v1/nota-credito`). Sin variables ni environments; tokens hardcodeados y expirados.

### Pendientes de confirmar en la pasada de emisión (hipótesis de la matriz)
- **O-01:** ¿`/v1/factura` recalcula montos o confía en `montoNeto`/`montoIVA`/`montoTotal` enviados? (F33M-008/009/010/012)
- **IVA en exenta (34):** ¿rechaza, ignora, o emite el DTE con IVA? (F34-003)
- **Duplicidad:** ¿reenvío idéntico genera N DTE, o hay control de idempotencia? (DUP-001/002/003)
- **Autorización App:** ¿`/v1/app/factura` permite emitir a nombre de cualquier comercio habilitado sin prueba de identidad? (APPF-009)
- **`sub` ≠ `rutEmisor`:** confirmar 403 y **no emisión** (RUT-021).

## 9. Riesgos

| Riesgo | Estado | Nota |
|---|---|---|
| Emisión duplicada / falta de idempotencia | **A verificar** (DUP-001/003) | crítico por impacto tributario |
| Autenticación: cap de tokens sin recuperación | **Confirmado** (DEF-08) | puede bloquear producción |
| Autenticación: firma/expiración no validadas por la app | Por diseño (manual §12.2) — delegado al gateway; **verificar que el gateway QA efectivamente las valida** (AUTH-009/010) |
| Autorización: `/v1/app/*` sin validación `sub` | **A verificar** (APPF-009) — potencial suplantación de emisor |
| RUT: `JWT.sub` ≠ `rutEmisor` | **A verificar** (RUT-021/022) |
| Reglas tributarias: neto/IVA/total inconsistentes aceptados | **A verificar** (O-01) |
| IVA en factura exenta | **A verificar** (F34-003) |
| Integridad catálogos (región→comuna, rubro→acteco) | test automatizado listo (CONS-001..004) |
| Manejo de errores: 5xx en vez de 4xx | **Confirmado** (DEF-02, DEF-03) |
| Information disclosure en errores | **Confirmado** (DEF-04, DEF-05) |

## 10. Cobertura

**Cubierto (automatizado):** camino feliz 33/34, matriz de campos obligatorios (55 casos), montos/reglas
tributarias (20), tipos de dato (19), strings/inyecciones (17), campos desconocidos (8), seguridad/HTTP (18),
factura 34 / IVA (21), NC 61 (31), RUT (24), auth (22), catálogos GET + consistencia (95), catálogos App (9),
App emisión (9), duplicidad/concurrencia (5), performance (6), contrato (4).

**No ejecutable / BLOCKED:**
- Pasada masiva contra QA — **bloqueada por DEF-08** (cap de tokens). Framework listo para correr en 1 comando.
- Happy path NC (NC-002/003/011/018) — requiere factura en estado `ACEPTADO` por el SII; el framework intenta
  emitir y esperar la aceptación, y si no llega marca `BLOCKED` con la respuesta real.
- Canal App/POS sin JWT — **DEF-01**; se documenta el 401 y se prueba también con token.
- "Token expira durante la operación" (AUTH-018) — best-effort; probable `BLOCKED`.
- "Token de otro ambiente" (AUTH-012) — requeriría login DEV (fuera de alcance); se omite o se usa token fabricado.

## 11. Postman Collection

- **Nombre:** `DTE API Testing` — `DTE API Testing.postman_collection.json` (raíz del proyecto).
- **Environments:** `DTE API Testing - QA.postman_environment.json`, `DTE API Testing - DEV.postman_environment.json`.
- **Ambientes:** `QA` (ejecutable) y `DEV` (estructura preparada, sin credenciales). Cambio de ambiente vía
  `{{baseUrl}}`, `{{baseUrlNc}}`, `{{baseUrlConsultas}}`.
- **Carpetas:** `QA → {00 Login, 01 Factura 33 (001 Happy … 008 Auth), 02 Factura 34, 03 Nota de Crédito 61,
  04 Regiones, 05 Comunas, 06 Rubros, 07 Actecos, 08 App POS, 09 Consultas}`, `DEV → (preparada)`.
- **Requests:** 70. **Variables:** `baseUrl`, `baseUrlNc`, `baseUrlConsultas`, `jwt`, `loginUser`, `loginPass`
  (secret), `rutEmisor`, `rutReceptor`, `folioFactura` (se auto-setea desde la respuesta de emisión).
- **Scripts:** `000 - Login` guarda `jwt` en variable de colección; los happy paths validan `codigoRespuesta:"01"`
  + `folio` y propagan `folioFactura`; los negativos validan el rango de HTTP esperado. Sin tokens sensibles
  hardcodeados (se obtienen del login).
- **Cómo ejecutar:** importar colección + environment `QA`, seleccionar el environment, ejecutar `000 - Login`,
  luego la carpeta deseada o el runner completo. Cuidar el consumo de folios en `001 Happy Path`, `007 Duplicidad`.
- **Regenerar:** `python qa-api-tests/scripts/gen_postman.py`.

## 12. Automatización Python

```bash
cd qa-api-tests
python -m venv .venv && . .venv/Scripts/activate      # opcional
pip install -r requirements.txt
cp .env.example .env                                   # completar QA_USER / QA_PASS (y QA_TOKEN si el login está capado)

pytest -m "not emision"                                # negativos, sin emitir DTE
pytest -m "emision" --dte-budget=54                    # emisión controlada en QA
pytest -m "perf"                                       # performance (opt-in)
python scripts/build_matriz.py                         # consolida resultados -> reports/
```

- **Estructura:** `config/` (ambientes), `utils/` (api_client, auth, rut, payloads, dte_budget, evidence,
  assertions), `data/`, `tests/` (20 archivos), `reports/` (evidence/, report.html, matriz_resultados.csv),
  `scripts/` (gen_postman, build_matriz), `docs/`.
- **Markers:** `emision`, `emision_happy`, `duplicidad`, `perf`, `seguridad`, `app`, `nc`, `bloqueante`,
  `posible_defecto`, `case_id`.
- **Guard de presupuesto:** `--dte-budget=N` (default `DTE_BUDGET` del `.env`); al alcanzarlo, los tests de
  emisión restantes se `skip`. Cada DTE emitido → `reports/evidence/emitidos.csv` (folio, tipo, test_id, ts).
- **Evidencia:** un JSON por caso en `reports/evidence/` con request (headers enmascarados), response, HTTP,
  duración, esperado/real, estado. `reports/matriz_resultados.csv` es la matriz con estado por caso.
- **Configuración necesaria:** solo `.env`. Si el login de QA está capado (DEF-08), definir `QA_TOKEN` con un
  JWT vigente del emisor `10471336-K` y el framework lo usa como fallback.

---

### Anexos

- `docs/01_inventario_apis.md` — inventario detallado + 13 hallazgos de contrato.
- `docs/02_matriz_pruebas.md` — matriz completa (~440 casos, IDs, esperado, prioridad).
- `docs/03_framework_propuesta.md` — decisiones de diseño del framework.
- `reports/evidence/` — evidencia por caso · `reports/evidence/emitidos.csv` — DTE emitidos en QA.
