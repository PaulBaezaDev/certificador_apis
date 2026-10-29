/* ═══════════════════════════════════════════════════════════
   CERTIFICADOR API FACTURADOR — config.js
   Aquí se define TODO lo editable: ambientes, datos precargados y APIs.
   ═══════════════════════════════════════════════════════════ */
'use strict';

/* ─────────────────────────────────────────────────────────────
   AMBIENTES
   ───────────────────────────────────────────────────────────── */
const ENVS = {
  QA: {
    label: 'QA',
    color: '#8b5cf6',
    auth:      'https://verticalqa.mcdesaqa.cl/public/auth/web/v2/login',
    recepcion: 'https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion',
    nc:        'https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc',
    consultas: 'https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/consultas',
    healthFe:  'https://apiqa-cloud.mcdesaqa.cl/mcs-central-be-recepcion-fe/actuator/health',
  },
  DEV: {
    label: 'DEV',
    color: '#f59e0b',
    auth:      'https://apidev.mcdesaqa.cl/public/auth/web/v2/login',
    recepcion: 'https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion',
    nc:        'https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc',
    consultas: 'https://apidev-cloud.mcdesaqa.cl/central/dte/fe/consultas',
    healthFe:  'https://apidev-cloud.mcdesaqa.cl/mcs-central-be-recepcion-fe/actuator/health',
  },
  /* APIs dummy (mock) mientras el backend real está lento.
     Expone las rutas "Sin Auth" (/v1/app/...) + actuator/health. No hay login ni rutas con JWT.
     Colección: "Api Documento Tributario (Factura y NC) App-POS.postman_collection.json" (raíz del repo). */
  DUMMYS: {
    label: 'DUMMYS',
    color: '#38bdf8',
    soloSinAuth: true,   // oculta Login / Con Auth (health se muestra si healthFe tiene URL) y deshabilita "Probar Ambiente (Con Auth)"
    directo: true,       // el devtunnel permite CORS (Access-Control-Allow-Origin: *) -> no usa el proxy
    auth:      '',
    recepcion: 'https://5nnpwr8b-3000.brs.devtunnels.ms/central/dte/fe/recepcion',
    nc:        'https://5nnpwr8b-3000.brs.devtunnels.ms/central/dte/fe/recepcion-nc',
    consultas: 'https://5nnpwr8b-3000.brs.devtunnels.ms/central/dte/fe/consultas',
    healthFe:  'https://5nnpwr8b-3000.brs.devtunnels.ms/mcs-central-be-recepcion-fe/actuator/health',
  },
};

/* ─────────────────────────────────────────────────────────────
   DATOS PRECARGADOS (mock data)
   ───────────────────────────────────────────────────────────── */
const DEFAULTS = {
  loginUser:  '10471336-K',
  loginPass:  '1555',
  rutEmisor:  '10471336-K',
  rutReceptor:'26461274-8',
  razonReceptor: 'Empresa Receptora SpA',
  giro:       458,        // acteco.id "Edición de programas informáticos" (rubro 10)
  comuna:     13101,      // comuna.id "Santiago" (RM)
  direccion:  'Av. Providencia 1234',
  email:      'factura@empresa.cl',
  telefono:   '92323420',
  regionId:   13,
  rubroId:    7,
  tipoDteConsulta: 33,
  folioConsulta:   107,
};

/* receptor reutilizable para facturas (giro/comuna como ID entero) */
function receptorFactura(v) {
  return {
    rut:         v.rutReceptor || DEFAULTS.rutReceptor,
    razonSocial: v.razonReceptor || DEFAULTS.razonReceptor,
    giro:        Number(v.giro ?? DEFAULTS.giro),
    direccion:   v.direccion || DEFAULTS.direccion,
    comuna:      Number(v.comuna ?? DEFAULTS.comuna),
    email:       v.email || DEFAULTS.email,
    telefono:    v.telefono || DEFAULTS.telefono,
  };
}

/* receptor para NC (giro/comuna como TEXTO — contrato distinto, ver DEF-07) */
function receptorNc(v) {
  return {
    rut:         v.rutReceptor || DEFAULTS.rutReceptor,
    razonSocial: v.razonReceptor || DEFAULTS.razonReceptor,
    giro:        'Edicion de programas informaticos',
    direccion:   v.direccion || DEFAULTS.direccion,
    comuna:      'Santiago',
    email:       v.email || DEFAULTS.email,
    telefono:    v.telefono || DEFAULTS.telefono,
  };
}

/* ─────────────────────────────────────────────────────────────
   CAMPOS COMUNES
   ───────────────────────────────────────────────────────────── */
const F_RECEPTOR = [
  'separator',
  { key: 'rutReceptor',   label: 'RUT Receptor',   default: DEFAULTS.rutReceptor },
  { key: 'razonReceptor', label: 'Razón Social',   default: DEFAULTS.razonReceptor },
  { key: 'giro',          label: 'Giro (acteco id)', type: 'number', default: DEFAULTS.giro,
    hint: 'ID de la tabla acteco (ver Catálogo Actecos), NO el codActeco' },
  { key: 'comuna',        label: 'Comuna (id)',    type: 'number', default: DEFAULTS.comuna,
    hint: 'ID de la tabla comuna (ver Catálogo Comunas)' },
  { key: 'direccion',     label: 'Dirección',      default: DEFAULTS.direccion },
  { key: 'email',         label: 'Email',          type: 'email', default: DEFAULTS.email },
  { key: 'telefono',      label: 'Teléfono',       default: DEFAULTS.telefono, required: false },
];

/* ─────────────────────────────────────────────────────────────
   DEFINICIÓN DE APIS
   Cada entrada:
     id, group, label, method, service ('auth'|'recepcion'|'nc'|'consultas'|'raw'),
     methodByEnv ({DUMMYS:'POST'}) -> método distinto en un ambiente puntual,
     payloadByEnv ({DUMMYS: (v) => ({...})}) -> body distinto en un ambiente puntual,
     path, auth ('bearer'|'none'),
     fields[], buildPayload(vals), buildUrl(vals, env),
     emits (bool) -> muestra aviso "genera DTE",
     onSuccess(data) -> hook,
     smoke: { payload, expect:[codes], label } -> para el botón "Probar Ambiente"
   ───────────────────────────────────────────────────────────── */
const APIS = [
  /* ===== AUTENTICACIÓN ===== */
  {
    id: 'login',
    group: 'Autenticación',
    label: 'Login (obtener token)',
    method: 'POST',
    service: 'auth',
    auth: 'none',
    fields: [
      { key: 'loginUser', label: 'Usuario (RUT)', default: DEFAULTS.loginUser },
      { key: 'loginPass', label: 'Contraseña',    default: DEFAULTS.loginPass, type: 'password' },
    ],
    buildUrl: (v, env) => env.auth,
    buildPayload: (v) => ({ user: v.loginUser || DEFAULTS.loginUser, pass: v.loginPass || DEFAULTS.loginPass }),
    onSuccess: (data) => {
      const tok = data?.data?.token;
      if (tok) { setToken(tok); toast('success', '🔑 Token guardado y reutilizable'); }
      else toast('warning', 'Respuesta OK pero sin token (¿code 88 tope excedido?)');
    },
    smoke: {
      payload: () => ({ user: DEFAULTS.loginUser, pass: DEFAULTS.loginPass }),
      ok: (st, b) => b && (b.code === 1 || b.code === 88),
      label: 'code 1 (o 88 = auth arriba pero tope de tokens)',
    },
  },

  /* ===== CATÁLOGOS (JWT) ===== */
  {
    id: 'regiones',
    group: 'Catálogos',
    parent: 'Con Auth',
    label: 'GET Regiones',
    method: 'GET', service: 'recepcion', path: '/v1/regiones', auth: 'bearer',
    fields: [],
    smoke: { ok: (st) => st === 200, label: 'HTTP 200 con data[] y total' },
  },
  {
    id: 'comunas',
    group: 'Catálogos',
    parent: 'Con Auth',
    label: 'GET Comunas por región',
    method: 'GET', service: 'recepcion', auth: 'bearer',
    path: '/v1/regiones/{regionId}/comunas',
    fields: [{ key: 'regionId', label: 'Region ID', type: 'number', default: DEFAULTS.regionId }],
    buildUrl: (v, env) => `${env.recepcion}/v1/regiones/${encodeURIComponent(v.regionId ?? DEFAULTS.regionId)}/comunas`,
    smoke: { vals: { regionId: 13 }, ok: (st) => st === 200, label: 'HTTP 200, comunas de la RM' },
  },
  {
    id: 'rubros',
    group: 'Catálogos',
    parent: 'Con Auth',
    label: 'GET Rubros',
    method: 'GET', service: 'recepcion', path: '/v1/rubros', auth: 'bearer',
    fields: [],
    smoke: { ok: (st) => st === 200, label: 'HTTP 200 con data[] y total' },
  },
  {
    id: 'acteco',
    group: 'Catálogos',
    parent: 'Con Auth',
    label: 'GET Actividades económicas',
    method: 'GET', service: 'recepcion', auth: 'bearer',
    path: '/v1/rubros/{rubroId}/acteco',
    fields: [{ key: 'rubroId', label: 'Rubro ID', type: 'number', default: DEFAULTS.rubroId }],
    buildUrl: (v, env) => `${env.recepcion}/v1/rubros/${encodeURIComponent(v.rubroId ?? DEFAULTS.rubroId)}/acteco`,
    smoke: { vals: { rubroId: 7 }, ok: (st) => st === 200, label: 'HTTP 200 con acteco[]' },
  },

  /* ===== CATÁLOGOS — sin JWT (/v1/app/...) ===== */
  {
    id: 'app_regiones',
    group: 'Catálogos',
    parent: 'Sin Auth',
    label: 'GET Regiones (sin JWT)',
    method: 'GET', service: 'recepcion', path: '/v1/app/regiones', auth: 'none',
    fields: [],
    smoke: { ok: (st) => st === 200, label: 'doc: 200 sin token · real QA: 401 (DEF-01)' },
  },
  {
    id: 'app_comunas',
    group: 'Catálogos',
    parent: 'Sin Auth',
    label: 'GET Comunas por región (sin JWT)',
    method: 'GET', service: 'recepcion', auth: 'none',
    path: '/v1/app/regiones/{regionId}/comunas',
    fields: [{ key: 'regionId', label: 'Region ID', type: 'number', default: DEFAULTS.regionId }],
    buildUrl: (v, env) => `${env.recepcion}/v1/app/regiones/${encodeURIComponent(v.regionId ?? DEFAULTS.regionId)}/comunas`,
    smoke: { vals: { regionId: 13 }, ok: (st) => st === 200, label: 'HTTP 200, comunas de la RM' },
  },
  {
    id: 'app_rubros',
    group: 'Catálogos',
    parent: 'Sin Auth',
    label: 'GET Rubros (sin JWT)',
    method: 'GET', service: 'recepcion', path: '/v1/app/rubros', auth: 'none',
    fields: [],
    smoke: { ok: (st) => st === 200, label: 'HTTP 200 con data[] y total' },
  },
  {
    id: 'app_acteco',
    group: 'Catálogos',
    parent: 'Sin Auth',
    label: 'GET Actividades económicas (sin JWT)',
    method: 'GET', service: 'recepcion', auth: 'none',
    path: '/v1/app/rubros/{rubroId}/acteco',
    fields: [{ key: 'rubroId', label: 'Rubro ID', type: 'number', default: DEFAULTS.rubroId }],
    buildUrl: (v, env) => `${env.recepcion}/v1/app/rubros/${encodeURIComponent(v.rubroId ?? DEFAULTS.rubroId)}/acteco`,
    smoke: { vals: { rubroId: 7 }, ok: (st) => st === 200, label: 'HTTP 200 con acteco[]' },
  },

  /* ===== EMISIÓN (JWT) ===== */
  {
    id: 'factura33',
    group: 'Emisión',
    parent: 'Con Auth',
    label: 'POST Factura Afecta (33)',
    method: 'POST', service: 'recepcion', path: '/v1/factura', auth: 'bearer',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor,
        hint: 'Debe coincidir con el sub del JWT' },
      { key: 'nombreItem', label: 'Nombre ítem', default: 'Servicio de consultoría' },
      { key: 'cantidad',   label: 'Cantidad',    type: 'number', default: 1 },
      { key: 'precio',     label: 'Precio unitario neto', type: 'number', default: 100000 },
      { key: 'montoNeto',  label: 'Monto Neto',  type: 'number', default: 100000 },
      { key: 'montoIVA',   label: 'Monto IVA',   type: 'number', default: 19000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 119000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      tipoDte: 33,
      receptor: receptorFactura(v),
      items: [{
        numeroLinea: 1,
        nombreItem: v.nombreItem || 'Servicio',
        cantidad: Number(v.cantidad || 1),
        precioUnitarioNeto: Number(v.precio || 100000),
        monto: Number(v.cantidad || 1) * Number(v.precio || 100000),
      }],
      montoNeto: Number(v.montoNeto || 100000),
      montoIVA: Number(v.montoIVA || 19000),
      montoTotal: Number(v.montoTotal || 119000),
    }),
    smoke: {
      payload: {},   // body vacío: NO emite, solo verifica que la API valida
      ok: (st) => st === 400,
      label: 'body vacío → 400 (API operativa, NO se emite DTE)',
    },
  },
  {
    id: 'factura34',
    group: 'Emisión',
    parent: 'Con Auth',
    label: 'POST Factura Exenta (34)',
    method: 'POST', service: 'recepcion', path: '/v1/factura', auth: 'bearer',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor },
      { key: 'nombreItem', label: 'Nombre ítem', default: 'Consulta médica general' },
      { key: 'cantidad',   label: 'Cantidad',    type: 'number', default: 1 },
      { key: 'precio',     label: 'Precio unitario', type: 'number', default: 45000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 45000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      tipoDte: 34,
      receptor: receptorFactura(v),
      items: [{
        numeroLinea: 1,
        nombreItem: v.nombreItem || 'Servicio exento',
        cantidad: Number(v.cantidad || 1),
        precioUnitarioNeto: Number(v.precio || 45000),
        monto: Number(v.cantidad || 1) * Number(v.precio || 45000),
      }],
      montoTotal: Number(v.montoTotal || 45000),
    }),
    smoke: { payload: {}, ok: (st) => st === 400, label: 'body vacío → 400 (NO se emite DTE)' },
  },
  {
    id: 'notacredito',
    group: 'Emisión',
    parent: 'Con Auth',
    label: 'POST Nota de Crédito (61)',
    method: 'POST', service: 'nc', path: '/v1/nota-credito', auth: 'bearer',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor },
      { key: 'folioRef',  label: 'Folio factura referenciada', type: 'number', default: DEFAULTS.folioConsulta,
        hint: 'La factura debe estar ACEPTADA por el SII' },
      { key: 'tipoRef',   label: 'Tipo DTE referencia', type: 'number', default: 33 },
      { key: 'razonReferencia', label: 'Razón / motivo', default: 'Anula documento por error en datos del receptor' },
      { key: 'montoNeto',  label: 'Monto Neto',  type: 'number', default: 100000 },
      { key: 'montoIVA',   label: 'Monto IVA',   type: 'number', default: 19000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 119000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      codigoReferencia: 1,
      razonReferencia: v.razonReferencia || 'Anula documento',
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      receptor: receptorNc(v),
      datosFactura: {
        tipoDte: Number(v.tipoRef || 33),
        folio: Number(v.folioRef || DEFAULTS.folioConsulta),
        items: [{ numeroLinea: 1, nombreItem: 'Servicio', cantidad: 1,
                  precioUnitarioNeto: Number(v.montoNeto || 100000), monto: Number(v.montoNeto || 100000) }],
        montoNeto: Number(v.montoNeto || 100000),
        montoIVA: Number(v.montoIVA || 19000),
        montoTotal: Number(v.montoTotal || 119000),
      },
    }),
    smoke: { payload: {}, ok: (st) => st === 400, label: 'body vacío → 400 (NO se emite NC)' },
  },

  /* ===== EMISIÓN — sin JWT (/v1/app/...) ===== */
  {
    id: 'app_factura33',
    group: 'Emisión',
    parent: 'Sin Auth',
    label: 'POST Factura Afecta (33) (sin JWT)',
    method: 'POST', service: 'recepcion', path: '/v1/app/factura', auth: 'none',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor,
        hint: 'Debe coincidir con el sub del JWT' },
      { key: 'nombreItem', label: 'Nombre ítem', default: 'Servicio de consultoría' },
      { key: 'cantidad',   label: 'Cantidad',    type: 'number', default: 1 },
      { key: 'precio',     label: 'Precio unitario neto', type: 'number', default: 100000 },
      { key: 'montoNeto',  label: 'Monto Neto',  type: 'number', default: 100000 },
      { key: 'montoIVA',   label: 'Monto IVA',   type: 'number', default: 19000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 119000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      tipoDte: 33,
      receptor: receptorFactura(v),
      items: [{
        numeroLinea: 1,
        nombreItem: v.nombreItem || 'Servicio',
        cantidad: Number(v.cantidad || 1),
        precioUnitarioNeto: Number(v.precio || 100000),
        monto: Number(v.cantidad || 1) * Number(v.precio || 100000),
      }],
      montoNeto: Number(v.montoNeto || 100000),
      montoIVA: Number(v.montoIVA || 19000),
      montoTotal: Number(v.montoTotal || 119000),
    }),
    smoke: { payload: {}, ok: (st) => st === 400, label: 'body vacío → 400 (API operativa, NO se emite DTE)' },
  },
  {
    id: 'app_factura34',
    group: 'Emisión',
    parent: 'Sin Auth',
    label: 'POST Factura Exenta (34) (sin JWT)',
    method: 'POST', service: 'recepcion', path: '/v1/app/factura', auth: 'none',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor },
      { key: 'nombreItem', label: 'Nombre ítem', default: 'Consulta médica general' },
      { key: 'cantidad',   label: 'Cantidad',    type: 'number', default: 1 },
      { key: 'precio',     label: 'Precio unitario', type: 'number', default: 45000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 45000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      tipoDte: 34,
      receptor: receptorFactura(v),
      items: [{
        numeroLinea: 1,
        nombreItem: v.nombreItem || 'Servicio exento',
        cantidad: Number(v.cantidad || 1),
        precioUnitarioNeto: Number(v.precio || 45000),
        monto: Number(v.cantidad || 1) * Number(v.precio || 45000),
      }],
      montoTotal: Number(v.montoTotal || 45000),
    }),
    smoke: { payload: {}, ok: (st) => st === 400, label: 'body vacío → 400 (NO se emite DTE)' },
  },
  {
    id: 'app_notacredito',
    group: 'Emisión',
    parent: 'Sin Auth',
    label: 'POST Nota de Crédito (61) (sin JWT)',
    method: 'POST', service: 'nc', path: '/v1/app/nota-credito', auth: 'none',
    emits: true,
    fields: [
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor },
      { key: 'folioRef',  label: 'Folio factura referenciada', type: 'number', default: DEFAULTS.folioConsulta,
        hint: 'La factura debe estar ACEPTADA por el SII' },
      { key: 'tipoRef',   label: 'Tipo DTE referencia', type: 'number', default: 33 },
      { key: 'razonReferencia', label: 'Razón / motivo', default: 'Anula documento por error en datos del receptor' },
      { key: 'montoNeto',  label: 'Monto Neto',  type: 'number', default: 100000 },
      { key: 'montoIVA',   label: 'Monto IVA',   type: 'number', default: 19000 },
      { key: 'montoTotal', label: 'Monto Total', type: 'number', default: 119000 },
      ...F_RECEPTOR,
    ],
    buildPayload: (v) => ({
      codigoReferencia: 1,
      razonReferencia: v.razonReferencia || 'Anula documento',
      rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor,
      receptor: receptorNc(v),
      datosFactura: {
        tipoDte: Number(v.tipoRef || 33),
        folio: Number(v.folioRef || DEFAULTS.folioConsulta),
        items: [{ numeroLinea: 1, nombreItem: 'Servicio', cantidad: 1,
                  precioUnitarioNeto: Number(v.montoNeto || 100000), monto: Number(v.montoNeto || 100000) }],
        montoNeto: Number(v.montoNeto || 100000),
        montoIVA: Number(v.montoIVA || 19000),
        montoTotal: Number(v.montoTotal || 119000),
      },
    }),
    smoke: { payload: {}, ok: (st) => st === 400, label: 'body vacío → 400 (NO se emite NC)' },
  },

  /* ===== CONSULTA ===== */
  {
    id: 'consulta',
    group: 'Consulta',
    parent: 'Con Auth',
    label: 'POST Consultar DTE por folio',
    method: 'POST', service: 'consultas', auth: 'bearer',
    buildPayload: (v) => ({ rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor }),
    path: '/v1/app/dte/{tipoDte}/{folio}',
    fields: [
      { key: 'tipoDte', label: 'Tipo DTE', type: 'number', default: DEFAULTS.tipoDteConsulta },
      { key: 'folio',   label: 'Folio',    type: 'number', default: DEFAULTS.folioConsulta },
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor, hint: 'Va en el body del POST' },
    ],
    buildUrl: (v, env) =>
      `${env.consultas}/v1/app/dte/${encodeURIComponent(v.tipoDte ?? 33)}/${encodeURIComponent(v.folio ?? 1)}`,
    smoke: {
      vals: { tipoDte: 33, folio: 999999 },
      ok: (st) => st === 200 || st === 404,
      label: '200 (existe) o 404 (no existe). 500 = DEF-03',
    },
  },
  {
    id: 'app_consulta',
    group: 'Consulta',
    parent: 'Sin Auth',
    label: 'Consultar DTE por folio (sin JWT)',
    method: 'POST', service: 'consultas', auth: 'none',
    // la consulta es POST con { rutEmisor } en el body (sin él -> 400 "Error de validacion de datos")
    buildPayload: (v) => ({ rutEmisor: v.rutEmisor || DEFAULTS.rutEmisor }),
    path: '/v1/app/dte/{tipoDte}/{folio}',
    fields: [
      { key: 'tipoDte', label: 'Tipo DTE', type: 'number', default: DEFAULTS.tipoDteConsulta },
      { key: 'folio',   label: 'Folio',    type: 'number', default: DEFAULTS.folioConsulta },
      { key: 'rutEmisor', label: 'RUT Emisor', default: DEFAULTS.rutEmisor,
        hint: 'Va en el body del POST' },
    ],
    buildUrl: (v, env) =>
      `${env.consultas}/v1/app/dte/${encodeURIComponent(v.tipoDte ?? 33)}/${encodeURIComponent(v.folio ?? 1)}`,
    smoke: {
      vals: { tipoDte: 33, folio: 999999 },
      ok: (st) => st === 200 || st === 404,
      label: '200 (existe) o 404 (no existe). 500 = DEF-03',
    },
  },

  /* ===== ESTADO ===== */
  {
    id: 'health',
    group: 'Estado',
    label: 'GET Health (actuator)',
    method: 'GET', service: 'raw', auth: 'none',
    buildUrl: (v, env) => env.healthFe,
    fields: [],
    smoke: {
      ok: (st) => st > 0 && st !== 502 && st !== 503 && st !== 504,
      label: 'responde algo (incluido 403 SigV4 = DEF-04)',
    },
  },
];
