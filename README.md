# Certificador Facturador · Departamento Desarrollo Android · KLAP

App web (HTML/CSS/JS puro, sin build) para probar las APIs de emisión de DTE de Klap:
- Probar **cada API** por separado, con **datos precargados** editables.
- Menú lateral anidado en 2 niveles: **Con Auth** (requieren JWT) y **Sin Auth** (`/v1/app/...`, sin token),
  y dentro de cada uno los mismos grupos (Catálogos, Emisión, Consulta).
- Botones **“Probar Ambiente (Con Auth)”** y **“Probar Ambiente (Sin Auth)”**: cada uno dispara una petición
  a las APIs de su grupo y prende una **luz verde / ámbar / roja** al costado de cada una según la respuesta.

## Cómo abrir

Doble clic en `index.html` (o servirlo con cualquier server estático).

> El navegador bloquea las llamadas directas a `*.mcdesaqa.cl` por **CORS**. Si ves “Error de red”
> en todas las APIs, levanta el proxy incluido:
>
> ```
> python proxy.py
> ```
>
> y en el Certificador, campo **“Proxy CORS”**, pon `http://localhost:8787`.

## Uso

1. **Ambiente**: selector arriba a la derecha (QA / DEV / **DUMMYS**).
   - **DUMMYS** = APIs mock de un colega (`https://5nnpwr8b-3000.brs.devtunnels.ms`, colección
     `Api Documento Tributario (Factura y NC) App-POS.postman_collection.json` en la raíz), para cuando QA/DEV están lentos.
     Tiene las rutas **Sin Auth** (`/v1/app/...`) y `actuator/health`: en ese ambiente se ocultan Login y Con Auth, y
     `Probar Ambiente (Con Auth)` queda deshabilitado. Permite CORS, así que funciona **sin proxy**.
     El botón **“Probar Ambiente (Dummys)”** cambia a DUMMYS y prueba las 8 APIs Sin Auth + Health.
     Diferencia con el backend real: la consulta de DTE es `POST` con body `{"rutEmisor": "..."}`
     (en QA/DEV es `GET` sin body). Como es mock,
     "Emisión real" no genera documentos reales.
2. **Token**: se reutiliza mientras siga vigente (se guarda en `localStorage` y muestra los minutos restantes).
   - `Login rápido` obtiene uno nuevo con las credenciales precargadas.
   - También puedes pegar un JWT a mano.
   - El servicio de auth **limita la cantidad de tokens** (`code 88`), por eso se reutiliza y **no** se re-loguea salvo que venza.
3. **Probar cada API**: elige una en la barra izquierda → ajusta los campos → **Ejecutar** (o `Ctrl+Enter`).
   El panel derecho muestra el request JSON (editable con `✎ Editar`) y la respuesta.
4. **Probar Ambiente (Con Auth / Sin Auth)**: botones arriba a la izquierda. Cada uno recorre solo las APIs
   de su grupo (Con Auth = Login + APIs con JWT + Health; Sin Auth = solo las `/v1/app/...`, sin login previo):
   - 🟢 **verde** = respondió lo esperado (ver detalle al pasar el mouse por la luz).
   - 🟠 **ámbar** = respondió pero con algo a revisar (401/403, 500 de app, comportamiento inesperado).
   - 🔴 **rojo** = caída / error de red / 502-503-504.
   - Para las APIs de emisión, “Probar Ambiente” envía **body vacío** (espera `400`) — **no genera DTE**.
   - Al terminar, se **descarga automáticamente un informe HTML**
     (`informe_<AMBIENTE>_<alcance>_<AAAA-MM-DD_HH-MM-SS>.html`) con fecha y hora de inicio y término,
     el resumen (OK / revisar / caídas), una tabla con todas las pruebas y el detalle de cada una
     (URL, request, response). Las contraseñas y los tokens aparecen ocultos. Se puede imprimir a PDF
     desde el navegador. El botón **“⭳ Descargar último informe”** lo vuelve a descargar.

## APIs incluidas

| Grupo | API | Genera DTE |
|---|---|---|
| Autenticación | `POST /login` | — |
| **Con Auth** · Catálogos | `GET /v1/regiones`, `/v1/regiones/{id}/comunas`, `/v1/rubros`, `/v1/rubros/{id}/acteco` | — |
| **Con Auth** · Emisión | `POST /v1/factura` (33), `POST /v1/factura` (34), `POST /v1/nota-credito` (61) | **sí** (al Ejecutar manual) |
| **Con Auth** · Consulta | `POST /v1/app/dte/{tipoDte}/{folio}` | — |
| **Sin Auth** · Catálogos | `GET /v1/app/regiones`, `/v1/app/regiones/{id}/comunas`, `/v1/app/rubros`, `/v1/app/rubros/{id}/acteco` | — |
| **Sin Auth** · Emisión | `POST /v1/app/factura` (33), `POST /v1/app/factura` (34), `POST /v1/app/nota-credito` (61) | **sí** (al Ejecutar manual) |
| **Sin Auth** · Consulta | `GET /v1/app/dte/{tipoDte}/{folio}` | — |
| Estado | `GET /actuator/health` | — |

Cada API "Con Auth" tiene su par bajo `/v1/app/...` que no requiere JWT — mismos campos y payload,
solo cambia la ruta y el header `Authorization`.

## Ambientes y URLs (botón ⚙ arriba a la derecha)

Abre un cuadro con **todas las URLs**, editables y persistidas en el navegador:

- **Bases por ambiente** (Login, Recepción FE, Recepción NC, Consultas, Health) para QA y DEV.
  Cambiar una base actualiza al instante todas las pruebas que la usan.
- **URL por prueba**: la URL resuelta de cada API en QA y en DEV. Editar una celda **sobrescribe**
  solo esa prueba en ese ambiente (queda marcada en ámbar).
- **Restablecer todo** vuelve a los valores de `config.js`.

## Editar / agregar APIs y datos

Todo está en **`js/config.js`**:
- `ENVS` — URLs por ambiente.
- `DEFAULTS` — datos precargados (RUTs, giro, comuna, folios, etc.).
- `APIS` — cada entrada define método, servicio, campos del formulario, `buildPayload`, y el `smoke`
  test que usa el botón “Probar Ambiente”. El campo `parent` (`'Con Auth'` / `'Sin Auth'` / ausente)
  controla bajo qué menú padre aparece y qué botón de “Probar Ambiente” la incluye.

`js/app.js` es el motor y normalmente no hay que tocarlo.
