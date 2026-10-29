# Propuesta de framework de automatización (Python / pytest)

Prioridad: **claridad + mantenibilidad + trazabilidad + facilidad para agregar casos**. Nada sobre-diseñado.

## Estructura

```
qa-api-tests/
├── pytest.ini                  # markers, addopts, html report
├── requirements.txt            # pytest, requests, pytest-html, jsonschema, python-dotenv, pytest-xdist(opt)
├── .env.example                # QA_USER, QA_PASS, BASE_* (real .env gitignored)
├── conftest.py                 # fixtures globales
├── config/
│   └── environments.py         # dict QA/DEV: base_recepcion, base_nc, base_consultas, auth_url
├── data/
│   ├── receptor_canonico.json  # receptor válido con giro/comuna verificados en vivo
│   ├── factura33/*.json        # plantillas + tablas de casos
│   ├── factura34/*.json
│   └── notacredito61/*.json
├── utils/
│   ├── api_client.py           # wrapper requests -> ApiResult(status, json, text, headers, elapsed_ms, request_repr)
│   ├── auth.py                 # login(), token_variants(): expired/malformed/empty/foreign_env/bad_sig/...
│   ├── rut.py                  # dv_modulo11(), rut_valido_distinto(), formatos()
│   ├── payloads.py             # builders: build_factura33(**overrides), mutate(path, value), drop(path)
│   ├── evidence.py             # grabа reports/evidence/<test_id>.json + registra DTE emitidos
│   ├── dte_budget.py           # contador de folios consumidos; aborta si supera el tope
│   └── assertions.py           # assert_codigo_respuesta, assert_schema, assert_no_stacktrace, ...
├── tests/
│   ├── test_auth.py
│   ├── test_catalogos_regiones.py / _comunas.py / _rubros.py / _acteco.py / _consistencia.py
│   ├── test_app_catalogos.py
│   ├── test_factura33_happy.py / _obligatorios.py / _montos.py / _tipos_datos.py /
│   │   _strings.py / _campos_desconocidos.py / _seguridad.py
│   ├── test_factura34.py
│   ├── test_notacredito61.py
│   ├── test_rut.py
│   ├── test_app_factura.py
│   ├── test_duplicidad.py       # marker: emision + duplicidad
│   ├── test_performance.py      # marker: perf (opt-in)
│   └── test_contract.py
├── reports/
│   ├── evidence/                # 1 JSON por caso: request, response, http, ts, duración, resultado
│   ├── evidence/emitidos.csv    # folio,tipoDte,test_id,timestamp  (trazabilidad de DTE reales)
│   ├── report.html              # pytest-html
│   └── matriz_resultados.csv    # ID,API,método,escenario,esperado,real,http,estado,prioridad
└── scripts/
    ├── gen_postman.py           # genera la Postman Collection + environments desde data/ + matriz
    └── build_matriz.py          # fusiona docs/02_matriz + reports/evidence -> matriz_resultados.csv
```

## Decisiones clave

1. **Markers** (`pytest.ini`):
   - `emision` — cualquier test que puede generar un DTE real. `pytest -m "not emision"` = pasada segura completa.
   - `emision_happy` — subconjunto que se **espera** que emita (consume folio).
   - `duplicidad`, `perf`, `seguridad`, `app`, `bloqueante`.
   - `posible_defecto` — se marca cuando el comportamiento observado contradice el contrato; el test falla (visible) pero se triangula en el reporte.

2. **Guard de presupuesto** (`utils/dte_budget.py` + fixture `dte_budget` autouse en tests `emision`): lee `--dte-budget=N` (default configurable), cuenta respuestas 200 de endpoints de emisión; al llegar al tope, los tests restantes de emisión se marcan `skip` con motivo → nunca se pasa del límite pactado.

3. **Evidencia automática**: fixture autouse captura el último intercambio del `api_client` y escribe `reports/evidence/<nodeid>.json` con `test_id, request(method,url,headers_sanitized,body), response(status,headers,body), timestamp, duration_ms, expected, actual, estado`. Tokens y `pass` se enmascaran.

4. **Datos fuera del código**: plantillas base y tablas de casos en `data/*.json`. Los tests hacen `parametrize` leyendo esas tablas → agregar un caso = agregar una fila, sin tocar lógica.

5. **Aserciones alineadas al contrato documentado**, no al "debería pasar". Negativos afirman `status in (400,422)` etc. según manual. Cuando el real difiere → `FAIL` = candidato a defecto (Regla 3).

6. **Idempotencia de la suite**: el happy path 33/34 emite 1 vez por sesión y **cachea folio+payload** en un fixture de sesión; las suites de verificación (`POST /v1/app/dte/...`), performance baseline y duplicidad reusan ese folio en vez de emitir de nuevo.

7. **Sin dependencia dura entre tests**: cada archivo puede correr solo. El orden natural (`auth → catálogos → emisión → consulta → NC → duplicidad`) se logra con `pytest` ordenando por archivo + un `-p no:randomly`.

8. **Postman**: `scripts/gen_postman.py` produce `DTE API Testing.postman_collection.json` con la jerarquía Ambiente → API → Escenario → Caso, variables `{{baseUrl}}` etc., y tests JS de aserción basados en el `esperado` de cada caso. Se regenera desde la misma fuente que pytest para no divergir.

## Ejecución prevista

```bash
pip install -r requirements.txt
cp .env.example .env      # completar QA_USER / QA_PASS

# 1) Pasada segura (sin emitir): ~370 casos
pytest -m "not emision" --html=reports/report_safe.html

# 2) Emisión controlada (respeta tope):
pytest -m "emision" --dte-budget=50 --html=reports/report_emision.html

# 3) Performance (opt-in):
pytest -m "perf"

# 4) Consolidar matriz + generar Postman:
python scripts/build_matriz.py
python scripts/gen_postman.py
```

### Ambiente DUMMYS (APIs mock)

Mientras QA/DEV están lentos hay un mock en `https://5nnpwr8b-3000.brs.devtunnels.ms` (override con `DUMMYS_BASE`).
Solo expone el canal App (`/v1/app/*`) + `actuator/health`; no hay login ni rutas con JWT y no emite DTE reales.

```bash
ENV=DUMMYS pytest                       # corre solo -m app + suite test_dummys.py; el resto queda SKIPPED
ENV=DUMMYS python scripts/build_matriz.py
```

- Reporte, evidencia, matriz y `emitidos.csv` van a `reports/dummys/` (no pisan los de QA).
- `test_dummys.py` (marker `dummys`, casos DUM-00x) valida el contrato propio del mock: health UP, consulta
  `POST` con body `{rutEmisor}` (en el backend real es `GET`), NC `/v1/app/nota-credito` → 201. Con `ENV=QA` se omite.
- Los FAIL del canal App contra el mock (método ≠ POST → 404 en vez de 405, `regiones/abc` → 404 en vez de 400,
  emite con cualquier `rutEmisor`) son brechas del mock, **no** defectos del backend real.
- Postman: environment `DTE API Testing - DUMMYS` (solo sirven las requests `app/*`).
