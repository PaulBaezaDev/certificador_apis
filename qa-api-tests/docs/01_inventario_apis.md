# Inventario de APIs — Emisión DTE (Fase 1)

> Fuente: `manual_api_recepcion_fe_v1.5.pdf`, `manual_api_recepcion_nc_v1.1.pdf`,
> `manual_api_consultas_fenc_v1.1.pdf`, `Pruebas Api Facturacion. mcs klap.postman_collection.json`
> y **reconocimiento read-only ejecutado contra QA el 2026-08-28**.
> Regla 1 del encargo: no se inventan contratos. Todo lo marcado `[verificado QA]` fue observado en vivo.

---

## 1. Servicios y ambientes

Son **3 microservicios** distintos, con **base paths distintos**:

| Servicio | Prefijo base QA | DEV (no ejecutar) | Prod |
|---|---|---|---|
| Recepción FE (33/34) | `https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion` | `https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion` | `https://api-cloud.klap.cl/central/dte/fe/recepcion` |
| Recepción NC (61) | `https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc` | `https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc` | `https://api-cloud.klap.cl/central/dte/fe/recepcion-nc` |
| Consultas FENC (33/34/61) | `https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/consultas` | `https://apidev-cloud.mcdesaqa.cl/central/dte/fe/consultas` | `https://api-cloud.klap.cl/central/dte/fe/consultas` |

> **Hallazgo temprano H-01 (doc):** El encargo indica `baseUrl = .../recepcion/` para todo. La **Nota de Crédito NO vive en ese base** — está en `.../recepcion-nc/v1/nota-credito`. El endpoint `/v1/factura` **solo acepta tipo 33 y 34** (ver §5).

### Autenticación (login)

| Ambiente | Endpoint login (manual) | Endpoint login (colección) |
|---|---|---|
| QA | `POST https://apiqa.mcdesaqa.cl/public/auth/web/v1/login` `[verificado QA → 200]` | `POST https://verticalqa.mcdesaqa.cl/public/auth/web/v2/login` `[verificado QA → 200]` |
| DEV | `POST https://apidev.mcdesaqa.cl/public/auth/web/v1/login` | `POST https://apidev.mcdesaqa.cl/public/auth/web/v2/login` |

- Body: `{ "user": "<rut>", "pass": "<clave>" }`
- Respuesta: `{ code:1, message:"Token generado", data:{ token, permissions[], core_token(dentro del JWT) }, date, time }`
- Credenciales QA disponibles (colección): `user=10471336-K`, `pass=1555` → `sub = 10471336-K`, `user_id=131`.
- **TTL del token: 8 h** (`exp = iat + 28800`) `[verificado QA]`.
- `core_token` (Keycloak) para apps móviles va embebido en el JWT; se usa como `Bearer` alternativo.

> **Hallazgo H-02 (doc):** discrepancia `v1` (manual) vs `v2` (colección) y host `apiqa` vs `verticalqa`. Ambos responden 200 en QA. A confirmar cuál es el oficial.

---

## 2. Modelo de autenticación / autorización (CRÍTICO para diseño de pruebas)

Del manual §12 + verificación:

1. **La aplicación NO valida firma ni expiración del JWT.** Eso se delega al API Gateway / ALB upstream (manual §12.2, §10.2, §11.2 de los 3 manuales).
2. La app **solo compara `sub` (del JWT) contra `rutEmisor` (del body)**. Si no coinciden → `403 / codigoRespuesta 403`.
3. En endpoints GET de catálogos/consulta, `sub` identifica al comercio y se valida propiedad del recurso.
4. `[verificado QA]` El **gateway QA responde `401 {"message":"Unauthorized"}`** ante peticiones sin `Bearer` — **incluidas las rutas `/v1/app/*`** que la documentación describe como "sin JWT". → ver Hallazgo H-03.
5. `[verificado QA]` Los endpoints `actuator/health` e `actuator/info` **NO aceptan Bearer**: responden `403` con error de **AWS SigV4** (`Invalid key=value pair ... (hashed with SHA-256 ...)`). → Hallazgo H-04 (contradice manual §13, que dice que requieren `Bearer`). Además **filtra información de infraestructura** (mecanismo de firma, hash del header).

> **Hallazgo H-03 (bloqueante para prioridad 🟡):** en QA, `GET /v1/app/regiones` **sin** token → `401 Unauthorized` (gateway). El canal "App/POS sin JWT" **no es alcanzable sin credenciales** en QA. Debe probarse igual y documentar (el encargo lo pide explícitamente).

---

## 3. Endpoints — Recepción FE

### 3.1 `POST /v1/factura` 🔴 (con JWT)

| | |
|---|---|
| Método | `POST` |
| Auth | `Authorization: Bearer <JWT>` — obligatorio |
| Headers | `Content-Type: application/json` — obligatorio |
| Regla clave | `JWT.sub == body.rutEmisor`, si no → 403 |
| Efecto | **Consume folio CAF real, genera TED firmado y persiste el DTE** en cada 200 |

**Body:**

| Campo | Tipo | Oblig. | Notas |
|---|---|---|---|
| `rutEmisor` | string | SÍ | RUT del emisor; debe == `sub` del JWT. En QA fijo `10471336-K`. |
| `tipoDte` | integer | SÍ | `33` (Afecta) o `34` (Exenta). |
| `receptor` | object | SÍ | ver abajo |
| `items` | array | SÍ | 1 a 10 líneas |
| `movimientoGlobal` | object | NO | descuento/recargo global |
| `montoNeto` | integer | Condicional | tipo 33: obligatorio y > 0. tipo 34: **se ignora**. Sin decimales. |
| `montoIVA` | integer | Condicional | tipo 33: obligatorio y > 0. tipo 34: **se ignora**. Sin decimales. |
| `montoTotal` | integer | SÍ | Sin decimales. |

**`receptor`:**

| Campo | Tipo | Oblig. | Notas |
|---|---|---|---|
| `rut` | string | SÍ | |
| `razonSocial` | string | SÍ | |
| `giro` | integer | SÍ | **`id` (PK) de la tabla acteco** (NO el `codActeco`). Ej: `301`. |
| `direccion` | string | SÍ | |
| `comuna` | integer | SÍ | **`id` de la tabla comuna**. Ej: `13101`. |
| `email` | string | SÍ | |
| `telefono` | string | NO | |
| `ciudad` | string | NO | se resuelve desde la comuna si se omite |

**`items[]`:**

| Campo | Tipo | Oblig. | Notas |
|---|---|---|---|
| `numeroLinea` | integer | SÍ | secuencial |
| `nombreItem` | string | SÍ | |
| `cantidad` | decimal | SÍ | hasta 4 decimales |
| `precioUnitarioNeto` | integer | SÍ | sin decimales |
| `monto` | integer | SÍ | total de línea = cantidad × precio ± movimiento, sin decimales |
| `descripcion` | string | NO | |
| `codigoItem` | string | NO | SKU |
| `unidadMedida` | string | NO | |
| `movimientoItem` | object | NO | |

**`movimientoItem`:** `tipo` (`D`/`R`, SÍ), `tipoValor` (`$`/`%`, SÍ), `monto` (int, SÍ), `porcentaje` (decimal, cond. si `%`).
**`movimientoGlobal`:** `tipoMovimiento` (`D`/`R`, SÍ), `tipoValor` (`$`/`%`, SÍ), `monto` (int, SÍ), `porcentaje` (cond.), `descripcion` (NO).

**Reglas por `tipoDte`:**
- `33`: `montoNeto`, `montoIVA`, `montoTotal` obligatorios y > 0. Persiste `tasa_iva` de config (19%).
- `34`: solo `montoTotal` obligatorio. `montoNeto` y `montoIVA` **se ignoran**. Persiste `monto_neto=0`, `monto_exento=montoTotal`, `tasa_iva=0`.

> **Observación abierta O-01:** el ejemplo de respuesta 33 del manual (§6) es internamente **inconsistente** (`montoNeto` 585000, `montoIVA` 111150, pero `montoTotal` 725900, y aparece un `movimientoGlobal` que no venía en el request). No queda claro si la API **recalcula** montos o **confía** en los enviados. → a determinar empíricamente (suite Montos).

**Respuesta 200 (tipo 33):**
```
{ codigoRespuesta:"01", mensajeRespuesta:"Documento procesado exitosamente",
  datosEmisor:{rut,razonSocial,direccion,comuna,ciudad},
  datosReceptor:{rut,razonSocial,giro(texto),direccion,comuna(texto),ciudad},
  datosDTE:{ tipoDte, descripcionDte, folio, fechaEmision, items[], movimientoGlobal?,
             montoNeto, montoIVA, montoTotal, timbrePDF417 } }
```
**Respuesta 200 (tipo 34):** `datosDTE:{ tipoDte, descripcionDte, folio, fechaEmision, montoExento, montoTotal, timbrePDF417 }`

**Códigos:**

| codigoRespuesta | HTTP | Significado |
|---|---|---|
| `01` | 200 | Documento procesado exitosamente |
| `99` | 400 | Error en la validación de datos (`"error en la validacion de datos"`) |
| `98` | 503 | No hay folios disponibles |
| `97` | 409 | Transición de estado inválida |
| `404` | 404 | Recurso no encontrado (región, rubro) |
| `401` | 401 | Token faltante o inválido |
| `403` | 403 | `sub` del token no coincide con `rutEmisor` |
| — | 500 | Error interno |

**Sin campo de fecha en el request** — `fechaEmision` la asigna el servidor. (Relevante para la suite "Fechas" del encargo: no hay input de fecha del cliente en emisión.)

---

### 3.2 `POST /v1/app/factura` 🟡 (sin JWT — según doc)

- Body y respuesta **idénticos** a `/v1/factura`.
- Sin header `Authorization`; **sin** validación `sub == rutEmisor`.
- Validaciones (manual §7): JSON válido → 400; `@Valid` campos obligatorios → 400; `rutEmisor` módulo 11 → 400; comercio existe y habilitado → **403 "Error de autenticacion"**; validaciones de caso de uso → 400/503.
- `[verificado QA]` **rutas `/v1/app/*` responden `401` en el gateway sin token** (H-03).

---

### 3.3 Catálogos con JWT 🟠

| Endpoint | Método | Respuesta OK | Error |
|---|---|---|---|
| `GET /v1/regiones` | GET | `{ data:[{id:int,nombre:str}], total:int }` — `[verificado QA: 16 regiones, total=16]` | — |
| `GET /v1/regiones/{regionId}/comunas` | GET | `{ data:{ region:{id,nombre}, comunas:[{id,nombre}] }, total:int }` — `[verificado QA región 13]` | `404 {codigoRespuesta:"404", mensajeRespuesta:"Region no encontrada"}` |
| `GET /v1/rubros` | GET | `{ data:[{id,nombre}], total:int }` — `[verificado QA: total=21]` | — |
| `GET /v1/rubros/{rubroId}/acteco` | GET | `{ data:{ rubro:{id,nombre}, acteco:[{id,codActeco,nombre}] }, total:int }` — `[verificado QA rubro 7]` | `404 {codigoRespuesta:"404", mensajeRespuesta:"Rubro no encontrado"}` |

- `regionId` tipado como `short` en el manual (→ probar overflow > 32767).
- `rubroId` tipado como `integer`.
- `[verificado QA]` los `id` de acteco reales difieren de los ejemplos del manual (manual dice `155` para "Venta al por mayor de vehículos"; QA devuelve `301`). **Usar siempre valores en vivo, no los del manual.**

### 3.4 Catálogos sin JWT 🟡

`GET /v1/app/regiones`, `/v1/app/regiones/{regionId}/comunas`, `/v1/app/rubros`, `/v1/app/rubros/{rubroId}/acteco`.
`[verificado QA]` `GET /v1/app/regiones` sin token → **401** (H-03).

### 3.5 Estado

`GET /mcs-central-be-recepcion-fe/actuator/health` y `/actuator/info`.
`[verificado QA]` → **403 AWS SigV4** con Bearer (H-04). No usables desde el cliente API.

---

## 4. Endpoints — Recepción NC (`/v1/nota-credito`) 🔴

| | |
|---|---|
| Endpoint | `POST {baseNC}/v1/nota-credito` (con JWT) / `POST {baseNC}/v1/app/nota-credito` (sin JWT) |
| `tipoDte` | **61 implícito** — NO se envía en el body |
| Regla | `JWT.sub == body.rutEmisor` → si no, 403 |
| Efecto | Consulta la factura referenciada vía Consultas FENC, valida elegibilidad, **consume folio CAF tipo 61 y persiste la NC** en estado `APROBADA`. La factura **no se modifica** aquí. |

**Body:**

| Campo | Tipo | Oblig. | Notas |
|---|---|---|---|
| `codigoReferencia` | integer | SÍ | `1` = Anula documento completo (único soportado en v1.1) |
| `razonReferencia` | string | Condicional | máx **90** chars. Obligatorio si la factura es de período anterior (ver tabla elegibilidad) |
| `rutEmisor` | string | SÍ | == `sub` |
| `receptor` | object | SÍ | **debe coincidir exactamente con la factura original** |
| `datosFactura` | object | SÍ | datos de la factura referenciada |

**`receptor` (NC):** `rut`, `razonSocial`, `giro` **(string / texto, NO id)**, `direccion`, `comuna` **(string / texto)**, `email` (todos SÍ), `telefono` (NO).

> **Hallazgo H-05 (inconsistencia de contrato):** en `/v1/factura` el receptor usa `giro` y `comuna` como **integer (id)**; en `/v1/nota-credito` los usa como **string (texto)**. Diseño incoherente entre servicios.

**`datosFactura`:** `tipoDte` (33|34, SÍ), `folio` (int, SÍ), `items[]` (SÍ), `movimientoGlobal` (NO), `montoNeto`/`montoIVA` (cond. tipo 33), `montoTotal` (SÍ). `items[]` misma forma que en factura.

**Tabla de elegibilidad (validada server-side):**

| Condición factura | Permite NC | Requiere `razonReferencia` | Código |
|---|---|---|---|
| Estado ≠ ACEPTADO | No | — | `FACTURA_NO_ACEPTADA_SII` |
| Estado = ANULADO | No | — | `FACTURA_ANULADA` |
| ACEPTADO, mismo mes (0) | Sí | No | `PERIODO_VIGENTE` |
| ACEPTADO, 1–3 meses | Sí | Sí | `REQUIERE_DESCRIPCION` |
| ACEPTADO, 4–12 meses | Sí | Sí | `FUERA_PLAZO_REQUIERE_DESCRIPCION` |
| ACEPTADO, > 12 meses | No | — | `NO_PERMITIDO` |

**Códigos NC:**

| codigoRespuesta | HTTP | Significado |
|---|---|---|
| `01` | 200 | NC procesada exitosamente |
| `96` | 422 | Factura no elegible para NC |
| `97` | 409 | Bloqueo concurrente — NC en proceso |
| `98` | 503 | No hay folios disponibles |
| `99` | 400 | Error en la validación de datos |
| `401` | 401 | Token faltante o inválido |
| `403` | 403 | `sub` ≠ `rutEmisor` |
| — | 500 | Error interno |

> **Riesgo R-01 para el happy path NC:** requiere una factura **ACEPTADA por el SII** del mismo emisor. La aceptación SII es asíncrona y la hace otro servicio (`mcs-central-be-envia-dte-sii`), fuera de alcance. Si ninguna factura emitida en QA llega a `ACEPTADO` durante la ventana de pruebas → **happy path NC = BLOCKED**, solo se cubren los caminos de rechazo (400/403/422).

---

## 5. Endpoints — Consultas FENC (soporte / evidencia)

| Endpoint | Método | Auth | Uso en esta fase |
|---|---|---|---|
| `POST /v1/app/dte/{tipoDte}/{folio}` (body `{rutEmisor}`) | POST | Bearer JWT | Verificar cada DTE emitido (evidencia), leer `estado` y `evaluacionNc` |
| `POST /v1/app/dte/{tipoDte}/{folio}` | POST | sin JWT (`{rutEmisor}` en body) | idem canal App |

- `tipoDte` ∈ {33, 34, 61}; `folio` entero > 0.
- Respuesta factura: `datosEmisor`, `datosReceptor`, `datosFactura{...estado, items[], montos, timbrePDF417}`, `notaCredito?`, `evaluacionNc{permiteEmisionNc, requiereDescripcionNc, codigoRestriccion, ...}`.
- Respuesta NC: `datosNotaCredito`, `datosFacturaAnulada?`.
- Errores: `TIPO_DOCUMENTO_NO_VALIDO`, `FOLIO_NO_VALIDO`, `FACTURA_NO_ENCONTRADA`, `ACCESO_NO_AUTORIZADO` (400/403/404); genéricos con `codigoRespuesta:"99"`.

> **Hallazgo H-06 `[verificado QA]`:** `POST /central/dte/fe/consultas/v1/app/dte/33/106` (body `{rutEmisor}`) (folio de ejemplo de la colección) → **HTTP 500** `"Error interno del servidor. Intente nuevamente."`. Debería ser `404 FACTURA_NO_ENCONTRADA` o `403 ACCESO_NO_AUTORIZADO`, no 500.

> **Hallazgo H-07 `[verificado QA]`:** `GET /central/dte/fe/recepcion/v1/factura` (método incorrecto sobre endpoint de emisión) → **HTTP 500** `"Error interno del servidor"`. Debería ser `405 Method Not Allowed`.

---

## 6. La colección `mundo feliz` — análisis

Archivo: `Pruebas Api Facturacion. mcs klap.postman_collection.json` (Postman v2.1).

**Estructura:** `DEV / QA` → subcarpetas `00-.Auth`, `01-.Con Auth (JWT)`, `02-.Sin Auth (JWT)`.

| Request | Método | URL | Auth | Observaciones |
|---|---|---|---|---|
| Login dev | POST | `apidev.mcdesaqa.cl/public/auth/web/v2/login` | — | body `{user:10471336-K, pass:1555}` |
| Login QA | POST | `verticalqa.mcdesaqa.cl/public/auth/web/v2/login` | — | idem |
| Consulta folio (colección original, GET `.../consultas/v1/dte/33/106`; ahora POST `.../consultas/v1/app/dte/33/106` con `{rutEmisor}`) | POST | `.../consultas/v1/app/dte/33/106` | Bearer (hardcoded, **expirado**) | |
| Consulta folio sin jwt | POST | `.../consultas/v1/app/dte/33/106` | noauth | body vacío (falta `{rutEmisor}`) |
| Get regiones | GET | `.../recepcion/v1/regiones` | Bearer hardcoded | OK |
| Get rubros | GET | `.../recepcion/v1/app/rubros` | Bearer hardcoded | nombre dice "rubros" pero pega a `/v1/app/rubros` |
| Camino bonito Emision 33 | POST | `.../recepcion/v1/factura` | Bearer hardcoded | body 2 líneas, `movimientoItem` %, `montoNeto 610000 / IVA 115900 / total 725900` |
| Camino bonito Emision 61 Nota credito | POST | `.../recepcion/v1/nota`**``**`-credito` | Bearer hardcoded | **URL corrupta** (carácter de control ``); además base path equivocado (`recepcion` en vez de `recepcion-nc`) y forma de body distinta al manual |
| Camino bonito Emision 34 | POST | `.../recepcion/v1/factura` | Bearer hardcoded | body `tipoDte 34`, solo `montoTotal 45000` |
| Info_Region | GET | `{{facturaUrl}}v1/regiones/4/comunas` | Bearer hardcoded | **variable `{{facturaUrl}}` no definida** en la colección |
| info_Rubro | GET | `{{facturaUrl}}v1/rubros/19/acteco` | Bearer hardcoded | idem |
| 02 Sin Auth: Get regiones / Get rubros / Emision 33 / Emision 34 / Info_Region / info_Rubro | GET/POST | `.../recepcion/v1/app/...` | noauth | canal App |

**Hallazgos de la colección:**
- H-08: **No define variables ni environments.** `{{facturaUrl}}` queda sin resolver. Tokens hardcodeados y **ya expirados** (iat ≈ 2026-04).
- H-09: request de NC con **URL con carácter de control** `` y base path incorrecto.
- H-10: `Camino bonito 34` incluye `giro:659` y `comuna:4102` como ids — hay que verificar que existan en QA (los ejemplos del manual usan otros valores).
- H-11: `Consulta folio sin jwt` usa método `POST` sin body `{rutEmisor}` requerido.
- Emisión 61 en `mundo feliz` con `datosFactura.folio: 106` — mismo folio que da 500 en consultas (H-06).

**Dependencias entre APIs:**
```
login ──► token (sub=rutEmisor)
                │
   ┌────────────┼───────────────────────────┐
   ▼            ▼                           ▼
GET /v1/rubros  GET /v1/regiones      POST /v1/factura
   │               │                        │  (folio N)
   ▼               ▼                        ▼
GET .../{id}/acteco  GET .../{id}/comunas   POST /v1/app/dte/33/N  (evidencia, estado)
   │               │                        │
   └── giro (acteco.id) ──┐   ┌── comuna.id ┘   estado == ACEPTADO ?
                          ▼   ▼                       │
                   receptor del POST /v1/factura      ▼
                                             POST /v1/nota-credito (ref folio N)
```

---

## 7. Datos maestros QA (recolectados en vivo 2026-08-28)

| Dato | Valor |
|---|---|
| Emisor (JWT `sub`) | `10471336-K` |
| Regiones | 16 (ids: 1–16; RM = 13) |
| Rubros | 21 (ids 1–21) |
| Comuna ejemplo válida | `13101` Santiago (RM) |
| Acteco ejemplo válido | `301` (rubro 7) — *pendiente elegir uno estable para receptor* |
| RUT receptor de ejemplo (colección) | `26461274-8` |

> Antes de la suite de emisión se fijará un **`receptor` canónico válido** con `giro` y `comuna` verificados en vivo, y se guardará en `data/`.

---

## 8. Resumen de hallazgos del inventario (pre-ejecución)

| ID | Tipo | Severidad prelim. | Descripción |
|---|---|---|---|
| H-01 | Doc/alcance | Media | NC no está en base `/recepcion`; `/v1/factura` no soporta tipo 61 |
| H-02 | Doc | Baja | login `v1`/`apiqa` vs `v2`/`verticalqa` |
| H-03 | Comportamiento | **Alta** | `/v1/app/*` responde 401 en gateway QA — canal "sin JWT" no alcanzable |
| H-04 | Seguridad/Doc | Media | `actuator/*` exige AWS SigV4, no Bearer; filtra info de infraestructura |
| H-05 | Contrato | Media | `giro`/`comuna` = integer en factura, string en NC |
| H-06 | Defecto | **Alta** | Consulta de folio inexistente → 500 en vez de 404/403 |
| H-07 | Defecto | Media | Método HTTP incorrecto en `/v1/factura` → 500 en vez de 405 |
| H-08 | Colección | Baja | sin variables/environments; tokens expirados |
| H-09 | Colección | Baja | URL de NC con carácter de control y base path incorrecto |
| H-10 | Datos | Baja | ids `giro`/`comuna` de la colección sin verificar en QA |
| H-11 | Colección | Baja | consulta app sin body `{rutEmisor}` |
| O-01 | Abierto | — | ¿la API recalcula montos o confía en los enviados? (a determinar) |
| R-01 | Riesgo | — | happy path NC depende de factura ACEPTADA por SII (asíncrono, fuera de alcance) |

> Ninguno se corrige (Regla 8). Todos entran a la matriz / reporte de defectos.
