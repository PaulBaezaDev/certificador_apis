# Matriz de pruebas — Emisión DTE (Fase 1)

Estado inicial de todos los casos: `NOT_EXECUTED`.
Estados: `PASS` · `FAIL` · `BLOCKED` · `NOT_EXECUTED`. Prioridad: `CRITICAL` · `HIGH` · `MEDIUM` · `LOW`.

**Convención de ID:** `<SUITE>-<NNN>`. Familias parametrizadas se anotan `(×N)` y expanden en código con un `case_id` por variante.

> "Resultado esperado" = comportamiento **según contrato documentado** (manual + verificación en vivo). Un `FAIL` puede ser el resultado buscado (Regla 3). "Resultado real / HTTP / Estado" se completan en la ejecución.

---

## 0. Convenciones de payload base

- **Emisor QA:** `rutEmisor = 10471336-K` (= `sub` del JWT). Los tests de "otro RUT" usan RUTs válidos por módulo 11 distintos.
- **`receptor` canónico** (se congela con valores verificados en vivo antes de ejecutar):
  ```json
  { "rut":"26461274-8", "razonSocial":"Empresa Receptora SpA", "giro":<acteco.id vivo>,
    "direccion":"Av. Providencia 1234", "comuna":<comuna.id vivo>, "email":"factura@empresa.cl", "telefono":"92323420" }
  ```
- **`factura33_min`**: 1 ítem, `cantidad 1`, `precioUnitarioNeto 100000`, `monto 100000`, `montoNeto 100000`, `montoIVA 19000`, `montoTotal 119000`.
- **`factura34_min`**: 1 ítem `monto 45000`, `montoTotal 45000`.

---

## 1. Suite AUTH — `test_auth.py` (CRITICAL/HIGH)

Se ejecuta contra un **endpoint GET de bajo impacto** (`GET /v1/regiones`) y, marcado aparte, contra `POST /v1/factura` con payload que fallaría de todos modos (para no consumir folio).

| ID | API | Método | Escenario | Datos | Resultado esperado | Prioridad |
|---|---|---|---|---|---|---|
| AUTH-001 | /v1/regiones | GET | Token válido y vigente | Bearer fresco | 200, `data[]` | CRITICAL |
| AUTH-002 | /v1/regiones | GET | Sin header `Authorization` | — | 401 | CRITICAL |
| AUTH-003 | /v1/regiones | GET | Header vacío `Authorization:` | `""` | 401 | HIGH |
| AUTH-004 | /v1/regiones | GET | Esquema no-Bearer | `Basic dXNlcjpw` | 401 | HIGH |
| AUTH-005 | /v1/regiones | GET | Esquema `Token <jwt>` | `Token eyJ...` | 401 | MEDIUM |
| AUTH-006 | /v1/regiones | GET | `Bearer` sin token | `Bearer ` | 401 | HIGH |
| AUTH-007 | /v1/regiones | GET | `bearer` minúsculas | `bearer eyJ...` | 200 ó 401 (documentar) | MEDIUM |
| AUTH-008 | /v1/regiones | GET | Token malformado (2 segmentos) | `eyJ.eyJ` | 401 | HIGH |
| AUTH-009 | /v1/regiones | GET | Token con firma alterada | último char cambiado | **documentar** (app no valida firma; ¿gateway sí?) | CRITICAL |
| AUTH-010 | /v1/regiones | GET | Token expirado (exp pasado) | JWT viejo real de la colección | **documentar** (app no valida exp; ¿gateway sí?) | CRITICAL |
| AUTH-011 | /v1/regiones | GET | Token con `sub` vacío | JWT recompuesto | 401 ó 403 ó 500 (documentar) | HIGH |
| AUTH-012 | /v1/regiones | GET | Token de otro ambiente (DEV) | login DEV | documentar | HIGH |
| AUTH-013 | /v1/regiones | GET | Doble header Bearer | 2× `Authorization` | documentar | MEDIUM |
| AUTH-014 | /v1/regiones | GET | Token con espacios internos | `Bearer ey J...` | 401 | LOW |
| AUTH-015 | /v1/regiones | GET | Token extremadamente largo | 100 KB base64 | 401 / 431 (documentar) | MEDIUM |
| AUTH-016 | /v1/regiones | GET | Token reutilizado tras nuevo login | token N-1 | 200 (múltiples sesiones) — documentar | MEDIUM |
| AUTH-017 | /v1/regiones | GET | Token cercano a expiración (obsv.) | pedir token, esperar, reintentar | 200 hasta exp | LOW |
| AUTH-018 | /v1/factura | POST | Token expira durante operación | best-effort | `BLOCKED` si no reproducible | LOW |
| AUTH-019 | /v1/factura | POST | `sub` ≠ `rutEmisor` (RUT válido distinto) | rutEmisor `77151256-9` | **403 / codigoRespuesta 403** | CRITICAL |
| AUTH-020 | /v1/factura | POST | `sub` == `rutEmisor` pero payload inválido | control | 400 (no 403) | HIGH |
| AUTH-021 | /v1/nota-credito | POST | `sub` ≠ `rutEmisor` | idem | 403 | CRITICAL |
| AUTH-022 | actuator/health | GET | Bearer sobre health | token válido | **403 SigV4** (H-04) — confirmar y evaluar fuga de info | MEDIUM |

---

## 2. Suite Catálogos GET — `test_catalogos_*.py`

### 2.1 `test_catalogos_regiones.py` — `GET /v1/regiones` (HIGH)

| ID | Escenario | Resultado esperado | Prio |
|---|---|---|---|
| REG-001 | Happy path | 200; `data[]`, `total:int` | HIGH |
| REG-002 | Schema: cada item `{id:int, nombre:str}` | cumple | HIGH |
| REG-003 | `total` == `len(data)` | igual — **verificar** (manual dice `total:16`, QA `total=16`) | HIGH |
| REG-004 | `id` únicos, sin duplicados | sin duplicados | HIGH |
| REG-005 | `nombre` no vacío / sin espacios extremos | cumple | MEDIUM |
| REG-006 | Contiene las 16 regiones de Chile | 16 | MEDIUM |
| REG-007 | Método `POST` | 405 (o documentar) | MEDIUM |
| REG-008 | Método `PUT` / `DELETE` / `PATCH` (×3) | 405 | MEDIUM |
| REG-009 | `HEAD` / `OPTIONS` (×2) | 200/204 ó 405 (documentar CORS) | LOW |
| REG-010 | `Content-Type: text/plain` en GET | ignorado, 200 | LOW |
| REG-011 | Query params basura `?x=1&drop=table` | ignorados, 200 | LOW |
| REG-012..016 | Batería auth (sin token, inválido, expirado, malformado, bearer malo) (×5) | 401 / documentar | HIGH |

### 2.2 `test_catalogos_comunas.py` — `GET /v1/regiones/{regionId}/comunas` (HIGH)

| ID | Escenario | Datos | Resultado esperado | Prio |
|---|---|---|---|---|
| COM-001 | Happy RM | `13` | 200; `region.id==13`; `comunas[]` | HIGH |
| COM-002 | Happy otra región | `4` | 200 | HIGH |
| COM-003 | Schema completo | `13` | `data.region{id,nombre}`, `comunas[{id,nombre}]`, `total` | HIGH |
| COM-004 | `region.id` == path | `13` | igual | HIGH |
| COM-005 | Todas las comunas con prefijo de región | `13` → ids `131xx` | **verificar integridad** región→comuna | HIGH |
| COM-006 | `total` == `len(comunas)` | `13` | igual | HIGH |
| COM-007 | `id` de comuna únicos | `13` | sin duplicados | HIGH |
| COM-008 | Región inexistente | `99` | 404 `"Region no encontrada"` | HIGH |
| COM-009 | Región `0` | `0` | 404 / 400 (documentar) | HIGH |
| COM-010 | Región negativa | `-1` | 400 / 404 | HIGH |
| COM-011 | Decimal | `1.5` | 400 | MEDIUM |
| COM-012 | String | `abc` | 400 | MEDIUM |
| COM-013 | Vacío (`/regiones//comunas`) | `` | 404 / 400 | MEDIUM |
| COM-014 | `null` literal | `null` | 400 / 404 | MEDIUM |
| COM-015 | Muy grande (> int64) | `99999999999999999999` | 400 / 500 (documentar) | MEDIUM |
| COM-016 | Overflow de `short` | `32768`, `2147483648` (×2) | 400 / 404 / 500 (documentar; manual tipa `short`) | HIGH |
| COM-017 | Caracteres especiales | `13%20`, `13!@#`, `13 ` (×3) | 400 / 404 | MEDIUM |
| COM-018 | SQLi básica | `13 OR 1=1`, `13;SELECT 1`, `13'--` (×3) | 400 / 404, **sin** filtrado ni error SQL | CRITICAL |
| COM-019 | Path traversal | `../rubros`, `%2e%2e%2f` (×2) | 400 / 404 | HIGH |
| COM-020 | URL-encoded válido | `%31%33` (=13) | 200 ó 400 (documentar) | LOW |
| COM-021 | Batería auth (×5) | | 401 | HIGH |
| COM-022 | Métodos incorrectos POST/PUT/DELETE (×3) | | 405 | MEDIUM |

### 2.3 `test_catalogos_rubros.py` — `GET /v1/rubros` (HIGH)

Mismo set que REG-001..016 adaptado (`RUB-001..016`). `total` esperado 21 `[verificado QA]`.

### 2.4 `test_catalogos_acteco.py` — `GET /v1/rubros/{rubroId}/acteco` (HIGH)

Mismo set que COM-001..022 adaptado (`ACT-001..022`):
- ACT-001 happy `rubroId=7`; schema `{id, codActeco, nombre}`.
- ACT-005 integridad rubro→acteco.
- ACT-008 rubro inexistente `99` → 404 `"Rubro no encontrado"`.
- ACT-016 `rubroId` como `integer` (no `short`) → probar `2147483648`, `99999999999`.
- ACT-018 SQLi.

### 2.5 `test_catalogos_consistencia.py` — cross-endpoint (HIGH)

| ID | Escenario | Resultado esperado | Prio |
|---|---|---|---|
| CONS-001 | Recorrer las 16 regiones → unir comunas → `id` de comuna globalmente únicos | sin colisiones entre regiones | HIGH |
| CONS-002 | Suma de `total` de comunas por región == nº total de comunas del país (~346) | coherente | MEDIUM |
| CONS-003 | Recorrer los 21 rubros → unir acteco → `id` globalmente únicos | sin colisiones | HIGH |
| CONS-004 | `codActeco` con formato SII (6 dígitos) | todos cumplen | MEDIUM |
| CONS-005 | Un `acteco.id` de un rubro sirve como `giro` válido en `POST /v1/factura` | 200 (consumo controlado) | HIGH |
| CONS-006 | Una `comuna.id` de una región sirve como `comuna` válida en `POST /v1/factura` | 200 (mismo DTE que CONS-005) | HIGH |
| CONS-007 | `giro` = `codActeco` (string) en vez de `id` | 400 (manual advierte explícitamente) | HIGH |
| CONS-008 | `comuna` de región A + dirección de región B | 200 (no valida coherencia geográfica) — documentar | MEDIUM |

---

## 3. Suite Catálogos App/POS — `test_app_catalogos.py` (MEDIUM)

| ID | API | Escenario | Resultado esperado | Prio |
|---|---|---|---|---|
| APPC-001 | `GET /v1/app/regiones` | Sin token (como documenta el manual) | **Esperado doc: 200. Real verificado: 401** → `FAIL` / defecto H-03 | HIGH |
| APPC-002 | `GET /v1/app/regiones` | Con token Bearer válido | 200 ó 401 (documentar) | MEDIUM |
| APPC-003 | `GET /v1/app/regiones/{id}/comunas` | sin token / con token (×2) | documentar | MEDIUM |
| APPC-004 | `GET /v1/app/rubros` | sin token / con token (×2) | documentar | MEDIUM |
| APPC-005 | `GET /v1/app/rubros/{id}/acteco` | sin token / con token (×2) | documentar | MEDIUM |
| APPC-006 | `/v1/app/regiones/{id}/comunas` | id inexistente / 0 / negativo / string (×4) | 404 / 400 | MEDIUM |
| APPC-007 | `/v1/app/rubros/{id}/acteco` | id inexistente / string (×2) | 404 / 400 | MEDIUM |
| APPC-008 | app catálogos | métodos incorrectos (×3) | 405 | LOW |
| APPC-009 | app vs jwt | comparar payload `data` de `/v1/app/regiones` vs `/v1/regiones` | idénticos | MEDIUM |

---

## 4. Suite Factura 33 — CRITICAL

### 4.1 `test_factura33_happy.py` — genera DTE real

| ID | Escenario | Resultado esperado | DTE | Prio |
|---|---|---|---|---|
| F33H-001 | Request mínimo válido | 200 `codigoRespuesta:"01"`, `datosDTE.folio`, `timbrePDF417` | ✅ 1 | CRITICAL |
| F33H-002 | Request completo (2 ítems, `movimientoItem` %, `movimientoGlobal` $) | 200 | ✅ 1 | CRITICAL |
| F33H-003 | 1 sola línea | 200 | ✅ 1 | HIGH |
| F33H-004 | 10 líneas (límite máximo) | 200 | ✅ 1 | HIGH |
| F33H-005 | 11 líneas (sobre el límite) | 400 | ❌ | HIGH |
| F33H-006 | `cantidad` con 4 decimales (`1.2345`) | 200 (o 400 si exige ≤4) | ✅ 1 | MEDIUM |
| F33H-007 | Verificación post-emisión: `POST /v1/app/dte/33/{folio}` de cada DTE | 200, datos coinciden, `estado` registrado | — | CRITICAL |

### 4.2 `test_factura33_obligatorios.py` — matriz campos obligatorios (esperado 400, sin DTE)

Familia parametrizada. Para cada campo obligatorio × cada mutación:

| ID | Campo | Mutaciones (×) | Resultado esperado |
|---|---|---|---|
| F33O-001 (×4) | `rutEmisor` | omitido · `null` · `""` · number `123` | 400 (ó 403 si rompe `sub==rutEmisor`) |
| F33O-002 (×4) | `tipoDte` | omitido · `null` · `"33"` · `0` | 400 |
| F33O-003 (×3) | `receptor` | omitido · `null` · `[]` | 400 |
| F33O-004 (×3) | `items` | omitido · `null` · `[]` (vacío) | 400 |
| F33O-005 (×3) | `montoNeto` | omitido · `null` · `0` | 400 (tipo 33 exige > 0) |
| F33O-006 (×3) | `montoIVA` | omitido · `null` · `0` | 400 |
| F33O-007 (×3) | `montoTotal` | omitido · `null` · `0` | 400 |
| F33O-008 (×4) | `receptor.rut` | omitido · `null` · `""` · number | 400 |
| F33O-009 (×3) | `receptor.razonSocial` | omitido · `null` · `""` | 400 |
| F33O-010 (×4) | `receptor.giro` | omitido · `null` · `0` · `"301"` (string) | 400 |
| F33O-011 (×3) | `receptor.direccion` | omitido · `null` · `""` | 400 |
| F33O-012 (×4) | `receptor.comuna` | omitido · `null` · `0` · `"13101"` (string) | 400 |
| F33O-013 (×3) | `receptor.email` | omitido · `null` · `""` | 400 (¿ó acepta?) — documentar |
| F33O-014 (×3) | `items[0].numeroLinea` | omitido · `null` · `"1"` | 400 |
| F33O-015 (×3) | `items[0].nombreItem` | omitido · `null` · `""` | 400 |
| F33O-016 (×3) | `items[0].cantidad` | omitido · `null` · `0` | 400 |
| F33O-017 (×3) | `items[0].precioUnitarioNeto` | omitido · `null` · `-1` | 400 |
| F33O-018 (×3) | `items[0].monto` | omitido · `null` · `0` | 400 |
| F33O-019 | `receptor.telefono` omitido (opcional) | 200 (control) | ✅ 1 |
| F33O-020 | `receptor.ciudad` omitido (opcional) | 200 (mismo DTE F33O-019) | — |

> Cada caso registra `codigoRespuesta` y `mensajeRespuesta` reales. El manual usa mensajes genéricos → se verifica si **algún** campo produce mensaje específico (útil para el reporte).

### 4.3 `test_factura33_montos.py` — reglas tributarias / consistencia (O-01)

| ID | Escenario | Resultado esperado (a confirmar) | DTE | Prio |
|---|---|---|---|---|
| F33M-001 | `montoNeto` negativo | 400 | ❌ | CRITICAL |
| F33M-002 | `montoIVA` negativo | 400 | ❌ | CRITICAL |
| F33M-003 | `montoTotal` negativo | 400 | ❌ | CRITICAL |
| F33M-004 | `precioUnitarioNeto` negativo | 400 | ❌ | HIGH |
| F33M-005 | `cantidad` negativa | 400 | ❌ | HIGH |
| F33M-006 | `cantidad` = 0 | 400 | ❌ | HIGH |
| F33M-007 | `item.monto` negativo | 400 | ❌ | HIGH |
| F33M-008 | `montoNeto` ≠ Σ`items.monto` (neto inflado) | **¿400 o 200?** — determina si valida | ⚠️ posible | CRITICAL |
| F33M-009 | `montoIVA` ≠ 19% de `montoNeto` (ej. IVA=1) | **¿400 o 200?** | ⚠️ posible | CRITICAL |
| F33M-010 | `montoTotal` ≠ `montoNeto + montoIVA` | **¿400 o 200?** | ⚠️ posible | CRITICAL |
| F33M-011 | `montoTotal` = 1, neto/iva coherentes entre sí pero enormes | ¿? | ⚠️ posible | HIGH |
| F33M-012 | Todos los montos coherentes, valores correctos | 200 (baseline de O-01: comparar respuesta vs enviado) | ✅ 1 | CRITICAL |
| F33M-013 | `montoNeto` con decimales (`100000.5`) | 400 (manual: sin decimales) | ❌ | MEDIUM |
| F33M-014 | Número gigante `9_999_999_999_999` | 400 / 500 (documentar) | ⚠️ | MEDIUM |
| F33M-015 | Notación científica `1e6` en `montoTotal` | 400 | ❌ | LOW |
| F33M-016 | `movimientoItem` descuento > monto de línea | 400 | ❌ | HIGH |
| F33M-017 | `movimientoItem.porcentaje` > 100 | 400 | ❌ | HIGH |
| F33M-018 | `movimientoGlobal` descuento > total documento | 400 | ❌ | HIGH |
| F33M-019 | `movimientoItem.tipo` inválido (`"X"`) | 400 | ❌ | MEDIUM |
| F33M-020 | `movimientoItem.tipoValor` `"%"` sin `porcentaje` | 400 | ❌ | MEDIUM |
| F33M-021 | IVA informado = 0 en afecta | 400 (tipo 33 exige IVA > 0) | ❌ | HIGH |

> **Los casos ⚠️ (F33M-008/009/010/011/014) son el corazón de O-01.** Se ejecutan **de a uno**, y de cada 200 se guarda folio + se consulta el DTE para ver qué montos persistió. Presupuesto: ≤ 4 DTE aquí.

### 4.4 `test_factura33_tipos_datos.py` (esperado 400)

| ID | Escenario | Esperado |
|---|---|---|
| F33T-001 (×4) | `tipoDte`: `"33"` · `33.0` · `true` · `[33]` | 400 (ó 200 si castea `"33"`/`33.0` — documentar) |
| F33T-002 (×3) | `items`: `{}` · `"x"` · `123` | 400 |
| F33T-003 (×3) | `receptor`: `[]` · `"x"` · `123` | 400 |
| F33T-004 (×3) | `montoTotal`: `"119000"` · `true` · `[119000]` | 400 (ó 200 si castea string) |
| F33T-005 (×2) | `rutEmisor`: `["10471336-K"]` · `{"v":"..."}` | 400 |
| F33T-006 (×2) | `items[0].cantidad`: `"1"` · `true` | 400 |
| F33T-007 | `movimientoGlobal`: `"D"` (string en vez de objeto) | 400 |

### 4.5 `test_factura33_strings.py` — campos string (aplicado a `razonSocial`, `nombreItem`, `direccion`, `descripcion`)

| ID | Escenario | Esperado |
|---|---|---|
| F33S-001 | String válido normal | 200 (baseline) ✅ 1 |
| F33S-002 (×4) | `""` · solo espacios · espacios al inicio · espacios al final | 400 obligatorios / trim (documentar) |
| F33S-003 | String 10.000 chars en `nombreItem` | 400 / 200 (documentar límite) |
| F33S-004 (×3) | Unicode / emojis / acentos raros `𝕏 ✅ 中文` | 200 (documentar si persiste ok) |
| F33S-005 (×2) | Saltos de línea `\n\r`, tab | 200 / 400 |
| F33S-006 | HTML `<b>x</b>` en `razonSocial` | 200 sin ejecutar / sanitizado (documentar) |
| F33S-007 | XSS `<script>alert(1)</script>` en `nombreItem` | almacenado como texto plano; verificar en consulta |
| F33S-008 | SQLi `x'; DROP TABLE dte;--` en `razonSocial` | 200 tratado como texto / 400 — **sin** error SQL |
| F33S-009 | Caracteres de escape / control ` ` | 400 |
| F33S-010 | `email` con formato inválido `"abc"` | 400 (documentar si valida formato) |

> F33S-001, y como mucho 1–2 casos que resulten en 200, generan DTE. Presupuesto ≤ 3.

### 4.6 `test_factura33_campos_desconocidos.py`

| ID | Escenario | Esperado |
|---|---|---|
| F33U-001 | `"campoNoExiste":"test"` en raíz | 200 ignorado / 400 (documentar) — verificar que **no** aparezca en la respuesta ni en la consulta |
| F33U-002 | campo extra dentro de `receptor` | idem |
| F33U-003 | campo extra dentro de `items[0]` | idem |
| F33U-004 | `tipoDte:61` en `/v1/factura` | **400** (endpoint no soporta 61) — registrar respuesta exacta |
| F33U-005 | `tipoDte:39` (boleta) / `56` (ND) (×2) | 400 |
| F33U-006 | duplicar clave JSON `"montoTotal"` dos veces | documentar (last-wins / 400) |

> F33U-001..003: si devuelven 200 generan DTE. Presupuesto ≤ 2.

### 4.7 `test_factura33_seguridad.py` / HTTP

| ID | Escenario | Esperado |
|---|---|---|
| F33X-001 (×3) | `Content-Type`: `text/plain` · `application/xml` · ausente | 415 / 400 |
| F33X-002 | `Content-Type: multipart/form-data` con body JSON | 415 / 400 |
| F33X-003 | Body vacío | 400 |
| F33X-004 | Body `null` / `[]` / `"string"` (×3) | 400 |
| F33X-005 | JSON malformado (coma final, sin cerrar) | 400 |
| F33X-006 (×5) | Métodos `GET` · `PUT` · `PATCH` · `DELETE` · `OPTIONS` sobre `/v1/factura` | 405 (verificado: `GET` → **500**, H-07) |
| F33X-007 | Payload grande controlado: 10 ítems con `nombreItem` de 5 KB c/u (~60 KB) | 400 / 413 / 200 (documentar) |
| F33X-008 | Header `X-Forwarded-For`, `X-Original-URL` manipulados | sin cambio de comportamiento |
| F33X-009 | `rutEmisor` con SQLi `10471336-K' OR '1'='1` | 400 (módulo 11) — sin error SQL |
| F33X-010 | Doble slash / case en path `/v1//factura`, `/V1/FACTURA` | 404 / 405 |

---

## 5. Suite Factura 34 — `test_factura34.py` (CRITICAL)

| ID | Escenario | Resultado esperado | DTE | Prio |
|---|---|---|---|---|
| F34-001 | Exenta mínima válida (`montoTotal` solo) | 200; `datosDTE.montoExento==montoTotal` | ✅ 1 | CRITICAL |
| F34-002 | Exenta varias líneas | 200 | ✅ 1 | HIGH |
| F34-003 | **`montoIVA` > 0 enviado en exenta** | **manual: se ignora → 200 con `montoExento=total`, sin IVA.** Confirmar exacto: ¿rechaza / ignora / recalcula? | ✅ 1 | CRITICAL |
| F34-004 | `montoNeto` > 0 enviado en exenta | manual: se ignora → 200 | ✅ 1 | HIGH |
| F34-005 | `montoNeto` + `montoIVA` + `montoTotal` todos, incoherentes entre sí | 200 (ignora neto/iva) — verificar persistencia | ✅ 1 | HIGH |
| F34-006 | `montoIVA` negativo en exenta | ¿ignora (200) o valida (400)? | ⚠️ | HIGH |
| F34-007 | `montoIVA: null` explícito | 200 | — | MEDIUM |
| F34-008 | `montoTotal` = 0 | 400 | ❌ | HIGH |
| F34-009 | `montoTotal` negativo | 400 | ❌ | HIGH |
| F34-010 | `montoTotal` omitido | 400 | ❌ | HIGH |
| F34-011 | `montoTotal` gigante | 400 / 200 (documentar) | ⚠️ | MEDIUM |
| F34-012 | Ítem sin `descripcion` (opcional) | 200 | ✅ 1 | LOW |
| F34-013 | Ítems duplicados (misma línea 2 veces, `numeroLinea` repetido) | ¿400 o 200? | ⚠️ | HIGH |
| F34-014 | `numeroLinea` no secuencial (1,3,7) | ¿400 o 200? | ⚠️ | MEDIUM |
| F34-015 | `cantidad` inválida (0 / negativa) (×2) | 400 | ❌ | HIGH |
| F34-016 | Campos obligatorios (`rutEmisor`, `receptor.*`, `items`, `montoTotal`) omitidos (×~8) | 400 | ❌ | HIGH |
| F34-017 | `movimientoGlobal` descuento en exenta | 200 / 400 (documentar) | ⚠️ | MEDIUM |
| F34-018 | Verificación post-emisión `POST /v1/app/dte/34/{folio}` | montos: `montoExento`+`montoTotal`, sin `montoNeto`/`montoIva` | — | CRITICAL |
| F34-019 | `tipoDte:34` con `montoNeto` string | 400 / ignora | ⚠️ | LOW |
| F34-020 | Duplicidad: reenviar F34-001 idéntico ×2 | documentar (ver suite Duplicidad) | ✅ ≤2 | HIGH |

> Presupuesto DTE Factura 34: **≤ 8**.

---

## 6. Suite Nota de Crédito 61 — `test_notacredito61.py` (CRITICAL)

**Pre-requisito:** intentar obtener una factura del emisor en estado `ACEPTADO` (emitir 33 → consultar `estado` en loop corto). Si no se logra → NC-happy = `BLOCKED`, se documenta con la respuesta real.

| ID | API | Escenario | Resultado esperado | Prio |
|---|---|---|---|---|
| NC-001 | `/v1/factura` | Enviar `tipoDte:61` al endpoint de factura | **400** — "tipo 61 no soportado por este endpoint"; registrar respuesta real | CRITICAL |
| NC-002 | `/v1/nota-credito` | Happy: anulación (`codigoReferencia:1`) de factura ACEPTADA mismo período | 200 `codigoRespuesta:"01"`, `datosDTE.tipoDte:61`, `folio` | CRITICAL |
| NC-003 | `/v1/nota-credito` | Happy con `razonReferencia` (factura período anterior) | 200 | HIGH |
| NC-004 | `/v1/nota-credito` | Factura de período anterior **sin** `razonReferencia` | 422 `codigoRespuesta:96` (o 400) | HIGH |
| NC-005 | `/v1/nota-credito` | `datosFactura.folio` inexistente (`999999999`) | 422 / 404 `"no elegible"` / `FACTURA_NO_ENCONTRADA` | CRITICAL |
| NC-006 | `/v1/nota-credito` | `datosFactura.tipoDte` inválido (`99`, `61`, `39`) (×3) | 400 | HIGH |
| NC-007 | `/v1/nota-credito` | `folio` inválido (`0`, `-1`, `"abc"`, decimal) (×4) | 400 | HIGH |
| NC-008 | `/v1/nota-credito` | Factura de **otro emisor** | 403 / 422 (no revela datos) | CRITICAL |
| NC-009 | `/v1/nota-credito` | `receptor` no coincide con la factura original | 422 / 400 | CRITICAL |
| NC-010 | `/v1/nota-credito` | `montoTotal` NC > factura original | 400 / 422 | CRITICAL |
| NC-011 | `/v1/nota-credito` | `montoTotal` NC = factura original (anulación total válida) | 200 (si elegible) | HIGH |
| NC-012 | `/v1/nota-credito` | `montoTotal` NC = 0 | 400 | HIGH |
| NC-013 | `/v1/nota-credito` | `montoTotal` NC negativo | 400 | HIGH |
| NC-014 | `/v1/nota-credito` | `codigoReferencia` inválido (`0`, `2`, `99`, `"1"`) (×4) | 400 (solo `1` soportado) | HIGH |
| NC-015 | `/v1/nota-credito` | `razonReferencia` vacía cuando se requiere | 422 / 400 | MEDIUM |
| NC-016 | `/v1/nota-credito` | `razonReferencia` de 91 chars (> 90) | 400 | MEDIUM |
| NC-017 | `/v1/nota-credito` | `razonReferencia` de 5.000 chars | 400 | MEDIUM |
| NC-018 | `/v1/nota-credito` | NC duplicada: 2ª NC sobre la misma factura | 409 `codigoRespuesta:97` / 422 | CRITICAL |
| NC-019 | `/v1/nota-credito` | Campos obligatorios omitidos (`codigoReferencia`, `rutEmisor`, `receptor`, `datosFactura`) (×4) | 400 | HIGH |
| NC-020 | `/v1/nota-credito` | `sub` ≠ `rutEmisor` | 403 | CRITICAL |
| NC-021 | `/v1/nota-credito` | Sin token / token inválido (×2) | 401 | HIGH |
| NC-022 | `/v1/app/nota-credito` | Sin JWT (canal App) | doc: procesa; real: probablemente 401 (H-03) — documentar | HIGH |
| NC-023 | `/v1/nota-credito` | Factura referenciada en estado ≠ ACEPTADO (recién emitida) | 422 `FACTURA_NO_ACEPTADA_SII` | HIGH |
| NC-024 | `/v1/nota-credito` | Métodos incorrectos (GET/PUT/DELETE) (×3) | 405 | LOW |
| NC-025 | `/v1/nota-credito` | `Content-Type` incorrecto (×2) | 415 / 400 | LOW |

> Presupuesto NC reales: **≤ 4** (idealmente 1–2 + 1 duplicada). Muchos casos son 400/403/422 sin consumo.

---

## 7. Suite RUT — `test_rut.py` (CRITICAL)

Aplica sobre `rutEmisor` de `/v1/factura` (nota: si el RUT es válido y ≠ `sub` → 403; si es inválido de formato → 400, gana la validación de formato). También sobre `receptor.rut` y sobre el canal App (`/v1/app/factura` donde `rutEmisor` es la identidad).

| ID | Campo | Valor | Resultado esperado | Prio |
|---|---|---|---|---|
| RUT-001 | rutEmisor | `10471336-K` (sin puntos, con guión) — canónico | pasa validación de formato | CRITICAL |
| RUT-002 | rutEmisor | `10.471.336-K` (con puntos y guión) | 200/403 si acepta ese formato; 400 si no — **documentar** | HIGH |
| RUT-003 | rutEmisor | `10471336K` (sin guión) | documentar | HIGH |
| RUT-004 | rutEmisor | `10471336-k` (k minúscula) | documentar (¿case-insensitive?) | HIGH |
| RUT-005 | rutEmisor | `10.471.336-k` | documentar | MEDIUM |
| RUT-006 | rutEmisor | `10471336-0` (DV incorrecto) | **400** (módulo 11) | CRITICAL |
| RUT-007 | rutEmisor | `99999999-9` (DV ok, no existe / no habilitado) | 403 (sub≠rutEmisor) — vía app: 403 "no habilitado" | HIGH |
| RUT-008 | rutEmisor | `1-9` (demasiado corto) | 400 | HIGH |
| RUT-009 | rutEmisor | `123456789012-3` (demasiado largo) | 400 | HIGH |
| RUT-010 | rutEmisor | `""` (vacío) | 400 | CRITICAL |
| RUT-011 | rutEmisor | `null` | 400 | CRITICAL |
| RUT-012 | rutEmisor | `10471336` (solo números, sin DV) | 400 | HIGH |
| RUT-013 | rutEmisor | `ABCDEFGH-I` (letras) | 400 | HIGH |
| RUT-014 | rutEmisor | ` 10471336-K ` (espacios) | 400 / trim (documentar) | MEDIUM |
| RUT-015 | rutEmisor | `10-471-336-K` (múltiples guiones) | 400 | MEDIUM |
| RUT-016 | rutEmisor | `1.0471.336-K` (puntos mal ubicados) | 400 | MEDIUM |
| RUT-017 | rutEmisor | `10471336-K;--` / `<script>` (especiales) | 400 | HIGH |
| RUT-018 | rutEmisor | `10471336-±` (unicode en DV) | 400 | LOW |
| RUT-019 | rutEmisor | `12345678-5` con DV calculado correcto pero comercio inexistente | 403 | HIGH |
| RUT-020 | receptor.rut | mismas mutaciones clave (DV malo, vacío, null, formato) (×5) | 400 | HIGH |
| RUT-021 | **Caso crítico** | `sub=10471336-K`, `rutEmisor=77151256-9` (válido, otro) en `/v1/factura` | **403 / codigoRespuesta 403** — no emite | CRITICAL |
| RUT-022 | **Caso crítico** | `/v1/app/factura` con `rutEmisor=77151256-9` (otro comercio, sin verificar habilitación) | 403 "Error de autenticacion" (o 200 si está habilitado → **hallazgo grave**) | CRITICAL |
| RUT-023 | **Caso crítico** | `/v1/app/factura` con `rutEmisor=10471336-K` (emisor real) sin token | doc: 200; real: 401 (H-03) — documentar | CRITICAL |
| RUT-024 | receptor.rut == rutEmisor (auto-factura) | 200 / 400 (documentar) | MEDIUM |

> Presupuesto DTE en esta suite: **≤ 2** (RUT-001 baseline, RUT-024).

---

## 8. Suite App/POS emisión — `test_app_factura.py` (MEDIUM)

| ID | Escenario | Resultado esperado | Prio |
|---|---|---|---|
| APPF-001 | `POST /v1/app/factura` 33 válido, **sin** token | doc: 200 emite. real: probablemente **401** (H-03) — documentar como defecto si aplica | HIGH |
| APPF-002 | `POST /v1/app/factura` 33 válido, **con** token Bearer | 200 / 401 (documentar) | MEDIUM |
| APPF-003 | `POST /v1/app/factura` `rutEmisor` no habilitado | 403 "Error de autenticacion" | HIGH |
| APPF-004 | `POST /v1/app/factura` `rutEmisor` con DV inválido | 400 | HIGH |
| APPF-005 | `POST /v1/app/factura` sin `rutEmisor` en body | 400 | HIGH |
| APPF-006 | `POST /v1/app/factura` 34 válido | 200 / 401 | MEDIUM |
| APPF-007 | Comparar: mismo body en `/v1/factura` (jwt) vs `/v1/app/factura` | misma estructura de respuesta | MEDIUM |
| APPF-008 | Métodos incorrectos (×3) | 405 | LOW |
| APPF-009 | `/v1/app/factura` sin validación `sub` → ¿puedo emitir a nombre de cualquier comercio habilitado? | **prueba de autorización clave** — documentar | CRITICAL |

> Si el canal está tras 401 (H-03), la mayoría quedan `BLOCKED` y se reporta el bloqueo. Presupuesto DTE: **≤ 2**.

---

## 9. Suite Duplicidad / Idempotencia — `test_duplicidad.py` (CRITICAL)

**Límite seguro pactado:** ver §Presupuesto. Ninguna prueba concurrente supera **5 hilos**. Se ejecuta al final, con presupuesto propio.

| ID | Escenario | Resultado esperado (a determinar) | DTE máx | Prio |
|---|---|---|---|---|
| DUP-001 | Reenviar el **mismo** payload 33 exacto 2 veces (secuencial) | ¿2 folios distintos? ¿mismo folio? ¿409? ¿error? — **documentar** | 2 | CRITICAL |
| DUP-002 | Reenviar el mismo payload 3 veces (secuencial) | idem | 3 | CRITICAL |
| DUP-003 | 5 requests **concurrentes** con payload idéntico | ¿5 DTE? ¿control de idempotencia? ¿lock? | 5 | CRITICAL |
| DUP-004 | ¿Existe header/campo de idempotencia? (`Idempotency-Key`, `X-Request-Id`) | probar con y sin — documentar si tiene efecto | 0–2 | HIGH |
| DUP-005 | Mismo payload con `numeroLinea`/monto idénticos pero distinto `codigoItem` | documentar | 1 | MEDIUM |
| DUP-006 | NC duplicada sobre misma factura (mueve a NC-018) | 409 `97` esperado | 0 | CRITICAL |
| DUP-007 | Análisis: ¿los folios son correlativos y sin saltos? (consultar folios emitidos) | correlativos | 0 | HIGH |

> **Total DTE de esta suite: ≤ 10.** Es el mayor consumidor de folios. Se puede reducir a DUP-001 + DUP-003 (≤ 7) si se prefiere.

---

## 10. Suite Performance — `test_performance.py` (LOW, opt-in `-m perf`)

Solo GET de catálogos. **Sin** carga agresiva. POST de emisión: NO se load-testea.

| ID | Escenario | Métrica | Prio |
|---|---|---|---|
| PERF-001 | `GET /v1/regiones` ×10 secuencial | p50, p95, max, media | LOW |
| PERF-002 | `GET /v1/regiones` ×50 secuencial | p50, p95, p99, throughput, errores | LOW |
| PERF-003 | `GET /v1/regiones/{id}/comunas` ×50 | idem | LOW |
| PERF-004 | `GET /v1/rubros/{id}/acteco` ×50 | idem | LOW |
| PERF-005 | `GET /v1/regiones` 5 hilos ×10 (50 total) | latencia bajo concurrencia leve | LOW |
| PERF-006 | Baseline latencia `POST /v1/factura` — 3 emisiones cronometradas (reusa DTE de F33H) | p50/max solo informativo | LOW |
| PERF-007 | ¿Existe rate limiting? 30 GET en ráfaga | detectar 429 / `Retry-After` | MEDIUM |

---

## 11. Suite Respuesta / contrato — transversal (`utils/assertions.py` + `test_contract.py`)

Por cada respuesta registrada en TODAS las suites se captura y valida:
`HTTP status` · `headers` (Content-Type, Server, X-*, correlación) · `body` · `schema` · `codigoRespuesta` · `mensajeRespuesta` · `tiempo de respuesta`.

| ID | Escenario | Esperado |
|---|---|---|
| CTR-001 | Todas las respuestas de error traen `codigoRespuesta` + `mensajeRespuesta` | consistente |
| CTR-002 | Códigos HTTP usados por la API — inventario real vs {400,401,403,404,405,409,415,422,429,500,502,503} | tabla en el reporte |
| CTR-003 | Errores 5xx no exponen stacktrace / SQL / rutas internas | sin fugas (revisar H-04, H-06, H-07) |
| CTR-004 | `Content-Type` de respuesta siempre `application/json` | consistente |
| CTR-005 | Header de correlación (`X-Request-Id` / `trace-id`) presente para soporte | documentar |
| CTR-006 | Tiempos: ningún GET de catálogo > 2 s p95; emisión > umbral se anota | informativo |

---

## 12. Resumen de conteo y presupuesto de DTE

| Suite | Casos aprox. | DTE reales (200 esperado) |
|---|---:|---:|
| AUTH | 22 | 0 |
| Catálogos GET (regiones/comunas/rubros/acteco) | ~95 | 0 |
| Catálogos consistencia | 8 | 1 (CONS-005/006 comparten 1) |
| Catálogos App | 9 | 0 |
| Factura 33 — happy | 7 | 5 |
| Factura 33 — obligatorios | ~60 | 1 |
| Factura 33 — montos (O-01) | 21 | 4 |
| Factura 33 — tipos de dato | 20 | 0 |
| Factura 33 — strings | 12 | 3 |
| Factura 33 — campos desconocidos | 8 | 2 |
| Factura 33 — seguridad/HTTP | 20 | 0 |
| Factura 34 | 20 | 8 |
| Nota de Crédito 61 | 25 | ≤ 4 |
| RUT | 24 | 2 |
| App/POS emisión | 9 | ≤ 2 |
| Duplicidad / idempotencia | 7 | ≤ 10 |
| Performance | 7 | 0 (reusa F33H) |
| Contrato transversal | 6 | 0 |
| **TOTAL** | **≈ 420–460 casos** | **≈ 40–48 DTE** |

### Tope propuesto (a confirmar contigo)

- **Máximo 50 DTE tipo 33/34 emitidos en QA** en toda la fase.
- **Máximo 4 NC tipo 61** en QA.
- **Duplicidad ≤ 10 DTE**, concurrencia ≤ 5 hilos.
- Todo DTE emitido se registra en `reports/evidence/emitidos.csv` (folio, tipo, test_id, timestamp) para trazabilidad y eventual limpieza.
- Si el equipo de la API prefiere un número menor, se recorta primero: Duplicidad (DUP-002) → Montos (dejar 2) → Strings (dejar 1) → F34 IVA (dejar F34-003 solo).
