/* ═══════════════════════════════════════════════════════════
   CERTIFICADOR API FACTURADOR — app.js (motor)
   ═══════════════════════════════════════════════════════════ */
'use strict';

const LS = {
  token: 'facturador.token',
  env:   'facturador.env',
  theme: 'facturador.theme',
  proxy: 'facturador.proxy',
  baseOv: 'facturador.baseOverrides',   // {QA:{recepcion:'...'}, DEV:{...}}
  apiOv:  'facturador.apiUrlOverrides',  // {QA:{factura33:'https://...'}, DEV:{...}}
};

const BASE_KEYS = ['auth', 'recepcion', 'nc', 'consultas', 'healthFe'];
const BASE_LABEL = { auth: 'Login (auth)', recepcion: 'Recepción FE', nc: 'Recepción NC', consultas: 'Consultas', healthFe: 'Health / actuator' };

function loadOv(k) { try { return JSON.parse(localStorage.getItem(k) || '{}'); } catch { return {}; } }
function saveOv(k, v) { localStorage.setItem(k, JSON.stringify(v)); }
let baseOv = loadOv(LS.baseOv);
let apiOv  = loadOv(LS.apiOv);

/* env con overrides de base aplicados */
function envFor(name) { return { ...ENVS[name], ...(baseOv[name] || {}) }; }
/* URL resuelta de una prueba en un ambiente dado (usa defaults de los campos) */
function resolvedUrl(a, name) {
  const ov = (apiOv[name] || {})[a.id];
  if (ov) return ov;
  const e = envFor(name);
  const defs = fieldDefaults(a);
  if (a.buildUrl) { try { return a.buildUrl(defs, e); } catch { return '(url dinámica)'; } }
  const base = ({ auth: e.auth, recepcion: e.recepcion, nc: e.nc, consultas: e.consultas, raw: '' })[a.service] ?? e.recepcion;
  return base + (a.path || '');
}

const DEFAULT_PROXY = 'http://localhost:8787';
const state = {
  env:   localStorage.getItem(LS.env) || 'QA',
  theme: localStorage.getItem(LS.theme) || 'dark',
  // el gateway de apiqa-cloud NO permite CORS (preflight solo OPTIONS) -> el proxy es casi obligatorio.
  proxy: localStorage.getItem(LS.proxy) ?? DEFAULT_PROXY,   // '' = directo
  current: 0,
  history: [],
  results: {},   // id -> {state:'ok'|'fail'|'warn'|'run', status, ms, note}
  editingJson: false,
  collapsed: (() => { try { return JSON.parse(localStorage.getItem('facturador.collapsed') || '{}'); } catch { return {}; } })(),
};

/* ── token ── */
function getToken()  { return localStorage.getItem(LS.token) || ''; }
function setToken(t)  { localStorage.setItem(LS.token, t || ''); const el = $('tokenInput'); if (el) el.value = t || ''; refreshTokenMeta(); }

function tokenExp(t) {
  try { return JSON.parse(atob(t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).exp || 0; }
  catch { return 0; }
}
function tokenVigente(t) { const e = tokenExp(t); return e === 0 || e * 1000 > Date.now() + 60000; }

/* ── dom ── */
const $ = (id) => document.getElementById(id);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };

function env() { return envFor(state.env); }
function api()  { return APIS[state.current]; }
const ENV_NAMES = Object.keys(ENVS);
/* método efectivo en el ambiente actual (ej. consulta = POST en DUMMYS) */
function mth(a) { return (a.methodByEnv || {})[state.env] || a.method; }
/* ¿la API existe en ese ambiente? (DUMMYS solo tiene las rutas Sin Auth) */
function apiDisponible(a, name = state.env) {
  const e = ENVS[name];
  if (!e?.soloSinAuth) return true;
  return a.parent === 'Sin Auth' || (a.group === 'Estado' && !!envFor(name).healthFe);
}

/* ── url / payload ── */
function serviceBase(a) {
  const e = env();
  return { auth: e.auth, recepcion: e.recepcion, nc: e.nc, consultas: e.consultas, raw: '' }[a.service] ?? e.recepcion;
}
function fieldValues(a) {
  const v = {};
  (a.fields || []).forEach((f) => {
    if (f === 'separator') return;
    const node = $(`f_${f.key}`);
    if (node) v[f.key] = f.type === 'checkbox' ? node.checked : node.value;
  });
  return v;
}
function buildUrl(a, vals) {
  const ov = (apiOv[state.env] || {})[a.id];
  if (ov) return ov;
  if (a.buildUrl) return a.buildUrl(vals || fieldValues(a), env());
  return serviceBase(a) + (a.path || '');
}
function buildBody(a, vals) {
  const fn = (a.payloadByEnv || {})[state.env] || a.buildPayload;
  if (!fn) return null;
  try { return fn(vals || fieldValues(a)); } catch { return {}; }
}
/* hosts de login: sí permiten CORS del navegador -> se llaman directo aunque haya proxy,
   así siempre se puede obtener token aunque el proxy esté apagado. */
const DIRECT_HOSTS = ['verticalqa.mcdesaqa.cl', 'apiqa.mcdesaqa.cl', 'apidev.mcdesaqa.cl'];
function withProxy(url) {
  if (!state.proxy) return url;
  try {
    const host = new URL(url).host;
    if (DIRECT_HOSTS.includes(host)) return url;
    const hostsDirectos = ENV_NAMES.filter((n) => ENVS[n].directo)
      .flatMap((n) => BASE_KEYS.map((k) => envFor(n)[k]).filter(Boolean).map((u) => { try { return new URL(u).host; } catch { return ''; } }));
    if (hostsDirectos.includes(host)) return url;
  } catch {}
  return `${state.proxy.replace(/\/$/, '')}/proxy?url=${encodeURIComponent(url)}`;
}

/* ── HTTP ── */
const TIMEOUT_MS = 25000;        // GET / catálogos
const TIMEOUT_EMIT_MS = 70000;   // emisión (más lento: firma TED, folio CAF, persistencia)

async function doRequest(a, { url, body, bearer } = {}) {
  url  = url  ?? buildUrl(a);
  body = body ?? buildBody(a);
  const headers = {};
  const wantsAuth = a.auth === 'bearer';
  if (wantsAuth) headers['Authorization'] = `Bearer ${bearer ?? getToken()}`;
  let payload;
  if (mth(a) !== 'GET' && mth(a) !== 'DELETE') {
    headers['Content-Type'] = 'application/json';
    payload = typeof body === 'string' ? body : JSON.stringify(body ?? {});
  }
  const ctrl = new AbortController();
  const limit = a.emits ? TIMEOUT_EMIT_MS : TIMEOUT_MS;
  const timer = setTimeout(() => ctrl.abort(), limit);
  const t0 = performance.now();
  try {
    const res = await fetch(withProxy(url), { method: mth(a), headers, body: payload, signal: ctrl.signal });
    clearTimeout(timer);
    const ms = Math.round(performance.now() - t0);
    const ct = res.headers.get('content-type') || '';
    let data;
    if (ct.includes('json')) { try { data = await res.json(); } catch { data = { raw: await res.text() }; } }
    else data = { raw: await res.text() };
    return { ok: true, status: res.status, ms, data, headers: Object.fromEntries(res.headers.entries()) };
  } catch (err) {
    clearTimeout(timer);
    const aborted = err && err.name === 'AbortError';
    const hint = aborted
      ? `Timeout tras ${Math.round(limit / 1000)}s. Si el ambiente está lento, reintenta.`
      : state.proxy
        ? `¿El proxy está corriendo?  python proxy.py  (esperado en ${state.proxy})`
        : 'CORS: el gateway apiqa-cloud no permite llamadas del navegador. Levanta el proxy (python proxy.py) y pon http://localhost:8787 en "Proxy CORS".';
    return { ok: false, status: 0, ms: Math.round(performance.now() - t0),
             data: { error: aborted ? 'timeout' : String(err), sugerencia: hint },
             netError: true, aborted, hint };
  }
}

/* ── ejecutar API actual (manual) ── */
async function executeCurrent() {
  const a = api();
  setStatus('loading', 'Ejecutando…');
  $('btnExec').disabled = true;
  $('btnExec').innerHTML = '<div class="spinner"></div> Ejecutando…';

  const raw = $('jsonArea').value.trim();
  const body = (state.editingJson && raw) ? raw : buildBody(a);
  const r = await doRequest(a, { body });

  renderResponse(r);
  addHistory(a, r);
  markResult(a.id, classifyManual(a, r), r);

  if (r.ok && r.status >= 200 && r.status < 300 && a.onSuccess) {
    try { a.onSuccess(r.data); } catch {}
  }
  setStatus(r.netError ? 'error' : 'ready', r.netError ? 'Error de red' : `HTTP ${r.status}`);
  if (r.netError && r.hint) toast('warning', r.hint, 6000);
  $('btnExec').disabled = false;
  $('btnExec').innerHTML = '<span class="ico">▶</span> Ejecutar';
  renderSidebar();
}

function classifyManual(a, r) {
  if (r.netError) return 'fail';
  if (r.status >= 500) return 'warn';
  if (r.status >= 200 && r.status < 300) return 'ok';
  if (r.status === 401 || r.status === 403) return 'warn';
  return 'ok'; // 400/404/422 = la API respondió y validó
}

/* ── PROBAR AMBIENTE ──
   scope: 'con-auth' -> Login + APIs con JWT + Estado
          'sin-auth'  -> solo APIs /v1/app/* (sin JWT), sin login previo */
function apisConAuth() { return APIS.filter((a) => (a.parent === 'Con Auth' || a.group === 'Autenticación' || a.group === 'Estado') && apiDisponible(a)); }
function apisSinAuth()  { return APIS.filter((a) => a.parent === 'Sin Auth' && apiDisponible(a)); }

const PROBAR_BTN = {
  'con-auth': { id: 'btnProbarAuth', label: 'Probar Ambiente (Con Auth)' },
  'sin-auth': { id: 'btnProbarSinAuth', label: 'Probar Ambiente (Sin Auth)' },
  'dummys':   { id: 'btnProbarDummys', label: 'Probar Ambiente (Dummys)' },
};

async function probarAmbiente(scope) {
  // "Dummys" = cambia al ambiente DUMMYS y corre sus APIs (solo existen las Sin Auth)
  if (scope === 'dummys' && state.env !== 'DUMMYS') cambiarAmbiente('DUMMYS');
  const list = scope === 'con-auth' ? apisConAuth()
    : scope === 'dummys' ? [...apisSinAuth(), ...APIS.filter((a) => a.group === 'Estado' && apiDisponible(a))]
    : apisSinAuth();
  if (!list.length) { toast('warning', `El ambiente ${state.env} no tiene APIs ${scope === 'sin-auth' ? 'Sin Auth' : 'Con Auth'}`); return; }
  const { id: btnId, label: btnLabel } = PROBAR_BTN[scope] || PROBAR_BTN['con-auth'];
  const scopeLabel = scope === 'con-auth' ? 'Con Auth' : scope === 'dummys' ? 'Sin Auth + Health' : 'Sin Auth';

  const emisionReal = $('chkEmisionReal').checked;
  if (emisionReal) {
    const n = list.filter((a) => a.emits).length;
    if (n && !confirm(`"Emisión real" está activo: se van a GENERAR ${n} documentos en ${state.env} (${scopeLabel}). ¿Continuar?`)) return;
  }
  const btn = $(btnId);
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Probando…';
  toast('info', `Probando ambiente ${state.env} — ${scopeLabel}${emisionReal ? ' (emisión real)' : ''}…`);
  state.collapsed = {}; saveCollapsed();   // ver todas las luces mientras corre

  const run = { env: state.env, scope, scopeLabel, emisionReal, proxy: state.proxy,
                inicio: new Date(), fin: null, items: [] };

  let ok = 0, fail = 0, warn = 0;
  for (const a of list) {
    markResult(a.id, 'run');
    renderSidebar();
    const sm = a.smoke || {};
    const realRun = emisionReal && a.emits;
    const vals = { ...fieldDefaults(a), ...(realRun ? {} : (sm.vals || {})) };
    const url  = buildUrl(a, vals);
    let body = null;
    if (mth(a) !== 'GET' && mth(a) !== 'DELETE') {
      body = realRun
        ? buildBody(a, vals)
        : ('payload' in sm ? (typeof sm.payload === 'function' ? sm.payload() : sm.payload) : buildBody(a, vals));
    }
    const r = await doRequest(a, { url, body });
    const okFn = realRun ? ((st) => st >= 200 && st < 300) : sm.ok;
    const passed = okFn ? safeOk(okFn, r) : (!r.netError && r.status > 0 && r.status < 500);
    const st = r.netError ? 'fail' : (passed ? 'ok' : (r.status >= 500 || r.status === 0 ? 'fail' : 'warn'));
    const nota = realRun
      ? `Probar Ambiente (${scopeLabel}) — emisión real (2xx esperado)`
      : `Probar Ambiente (${scopeLabel}) — ${sm.label || 'reachability'}`;
    markResult(a.id, st, r, nota);
    addHistory(a, r, { url, body, tag: `Probar Ambiente · ${scopeLabel}`, outcome: st });
    run.items.push({
      label: a.label, group: a.group, method: mth(a), auth: a.auth === 'bearer' ? 'Bearer JWT' : 'Sin token',
      emits: !!a.emits, realRun, esperado: realRun ? 'HTTP 2xx (emisión real)' : (sm.label || 'reachability'),
      url, body, outcome: st, status: r.netError ? (r.aborted ? 'TIMEOUT' : 'NET') : r.status,
      ms: r.ms, data: r.data, ts: new Date(),
    });
    renderSidebar();
    if (a.id === 'login' && r.ok) { try { a.onSuccess?.(r.data); } catch {} }
    st === 'ok' ? ok++ : st === 'warn' ? warn++ : fail++;
  }
  btn.disabled = false;
  btn.innerHTML = `<span class="ico">◈</span> ${btnLabel}`;
  applyEnvUi();
  toast(fail ? 'error' : warn ? 'warning' : 'success',
        `Ambiente ${state.env} (${scopeLabel}): ${ok} OK · ${warn} revisar · ${fail} caídas`);
  run.fin = new Date();
  run.totales = { ok, warn, fail };
  state.lastRun = run;
  descargarInforme(run);
  renderSidebar();
  renderResumen();
}

/* ── INFORME DESCARGABLE ──
   Al terminar cada "Probar Ambiente" se descarga un HTML autocontenido
   (se puede abrir en cualquier navegador o imprimir a PDF). */
const SECRET_KEYS = /^(pass|password|clave|token|accessToken|refreshToken|authorization)$/i;
function redact(v) {
  if (Array.isArray(v)) return v.map(redact);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, x] of Object.entries(v)) o[k] = SECRET_KEYS.test(k) && x ? '••••••' : redact(x);
    return o;
  }
  return v;
}
function parseMaybeJson(b) { if (typeof b !== 'string') return b; try { return JSON.parse(b); } catch { return b; } }
function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
const pad2 = (n) => String(n).padStart(2, '0');
function fechaHora(d) { return d.toLocaleString('es-CL', { dateStyle: 'full', timeStyle: 'medium' }); }
function stampArchivo(d) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}_${pad2(d.getHours())}-${pad2(d.getMinutes())}-${pad2(d.getSeconds())}`; }

function descargarInforme(run) {
  run = run || state.lastRun;
  if (!run) { toast('warning', 'Aún no hay una prueba de ambiente para informar'); return; }
  const blob = new Blob([buildInformeHtml(run)], { type: 'text/html;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `informe_${run.env}_${run.scope}_${stampArchivo(run.inicio)}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  toast('success', `Informe descargado: ${a.download}`, 4500);
}

function buildInformeHtml(run) {
  const { ok, warn, fail } = run.totales;
  const total = run.items.length;
  const durS = ((run.fin - run.inicio) / 1000).toFixed(1);
  const OUT = { ok: ['OK', 'ok'], warn: ['Revisar', 'warn'], fail: ['Caída', 'fail'] };
  const veredicto = fail ? ['CON CAÍDAS', 'fail'] : warn ? ['CON OBSERVACIONES', 'warn'] : ['OPERATIVO', 'ok'];
  const pretty = (x) => esc(JSON.stringify(redact(parseMaybeJson(x)), null, 2));

  const filas = run.items.map((it, i) => `
      <tr>
        <td class="num">${i + 1}</td>
        <td><span class="pill ${OUT[it.outcome][1]}">${OUT[it.outcome][0]}</span></td>
        <td><b>${esc(it.label)}</b><div class="sub">${esc(it.group)} · ${it.auth}${it.emits ? ' · <span class="dte">DTE</span>' : ''}</div></td>
        <td><span class="m">${it.method}</span></td>
        <td class="num"><b>${esc(it.status)}</b></td>
        <td class="num">${it.ms} ms</td>
        <td class="sub">${esc(it.esperado)}</td>
        <td class="num sub">${it.ts.toLocaleTimeString('es-CL')}</td>
      </tr>`).join('');

  const detalle = run.items.map((it, i) => `
    <section class="det ${OUT[it.outcome][1]}">
      <h3><span class="pill ${OUT[it.outcome][1]}">${OUT[it.outcome][0]}</span> ${i + 1}. ${esc(it.method)} ${esc(it.label)}</h3>
      <dl>
        <dt>Hora</dt><dd>${it.ts.toLocaleTimeString('es-CL')}</dd>
        <dt>HTTP</dt><dd><b>${esc(it.status)}</b> · ${it.ms} ms</dd>
        <dt>Esperado</dt><dd>${esc(it.esperado)}</dd>
        <dt>Autenticación</dt><dd>${it.auth}</dd>
        <dt>URL</dt><dd><code>${esc(it.url)}</code></dd>
      </dl>
      ${it.body != null ? `<p class="lbl">Request</p><pre>${pretty(it.body)}</pre>` : ''}
      <p class="lbl">Response</p><pre>${pretty(it.data)}</pre>
    </section>`).join('');

  return `<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe ${esc(run.env)} · ${esc(run.scopeLabel)} · ${stampArchivo(run.inicio)}</title>
<style>
  :root { --navy:#0B2A4A; --green:#25D07B; --ok:#16a34a; --warn:#d97706; --fail:#dc2626; --bd:#DBE5EF; --t2:#4A657F; }
  * { box-sizing:border-box; }
  body { font:13px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; color:var(--navy); background:#EEF3F8; margin:0; padding:24px; }
  .wrap { max-width:1100px; margin:0 auto; }
  header { background:var(--navy); color:#fff; border-radius:12px; padding:20px 24px; border-bottom:4px solid var(--green); }
  header h1 { margin:0 0 4px; font-size:20px; }
  header .s { color:#BCCDDD; font-size:12px; }
  .card { background:#fff; border:1px solid var(--bd); border-radius:12px; padding:18px 20px; margin-top:16px; }
  .meta { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px 24px; }
  .meta div span { display:block; font-size:10.5px; text-transform:uppercase; letter-spacing:.6px; color:var(--t2); font-weight:700; }
  .kpis { display:flex; flex-wrap:wrap; gap:12px; align-items:stretch; }
  .kpi { flex:1; min-width:120px; border:1px solid var(--bd); border-radius:10px; padding:12px 14px; }
  .kpi b { display:block; font-size:26px; }
  .kpi.ok b { color:var(--ok); } .kpi.warn b { color:var(--warn); } .kpi.fail b { color:var(--fail); }
  .verd { font-weight:800; font-size:15px; padding:6px 12px; border-radius:8px; display:inline-block; }
  .verd.ok { background:#dcfce7; color:var(--ok); } .verd.warn { background:#fef3c7; color:var(--warn); } .verd.fail { background:#fee2e2; color:var(--fail); }
  h2 { font-size:15px; margin:0 0 12px; }
  .tbl { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--bd); vertical-align:top; }
  th { font-size:10.5px; text-transform:uppercase; letter-spacing:.5px; color:var(--t2); background:#F5F9FC; }
  td.num { white-space:nowrap; font-variant-numeric:tabular-nums; }
  .sub { color:var(--t2); font-size:11.5px; }
  .pill { display:inline-block; font-size:10.5px; font-weight:800; padding:2px 8px; border-radius:99px; white-space:nowrap; }
  .pill.ok { background:#dcfce7; color:var(--ok); } .pill.warn { background:#fef3c7; color:var(--warn); } .pill.fail { background:#fee2e2; color:var(--fail); }
  .m { font:700 11px Consolas,monospace; }
  .dte { color:var(--warn); font-weight:700; }
  .det { border:1px solid var(--bd); border-left:4px solid var(--bd); border-radius:10px; padding:14px 16px; margin-top:12px; break-inside:avoid; }
  .det.ok { border-left-color:var(--ok); } .det.warn { border-left-color:var(--warn); } .det.fail { border-left-color:var(--fail); }
  .det h3 { margin:0 0 10px; font-size:14px; }
  dl { display:grid; grid-template-columns:120px 1fr; gap:4px 12px; margin:0; }
  dt { color:var(--t2); font-weight:600; } dd { margin:0; word-break:break-all; }
  .lbl { font-size:10.5px; text-transform:uppercase; letter-spacing:.6px; color:var(--t2); font-weight:700; margin:12px 0 4px; }
  pre { background:#F5F9FC; border:1px solid var(--bd); border-radius:8px; padding:10px 12px; margin:0; font:11.5px/1.45 Consolas,"Cascadia Code",monospace; white-space:pre-wrap; word-break:break-word; max-height:420px; overflow:auto; }
  footer { text-align:center; color:var(--t2); font-size:11px; margin:20px 0 4px; }
  @media print { body { background:#fff; padding:0; } pre { max-height:none; } .card, header { break-inside:avoid; } }
</style></head>
<body><div class="wrap">
  <header>
    <h1>Informe · Probar Ambiente ${esc(run.env)} — ${esc(run.scopeLabel)}</h1>
    <div class="s">Certificador Facturador · Departamento Desarrollo Android · KLAP</div>
  </header>

  <div class="card meta">
    <div><span>Fecha y hora de inicio</span>${esc(fechaHora(run.inicio))}</div>
    <div><span>Fecha y hora de término</span>${esc(fechaHora(run.fin))}</div>
    <div><span>Duración total</span>${durS} s</div>
    <div><span>Ambiente</span>${esc(run.env)}</div>
    <div><span>Alcance</span>${esc(run.scopeLabel)}</div>
    <div><span>Emisión real</span>${run.emisionReal ? 'Sí (genera DTE)' : 'No (body vacío → 400 esperado)'}</div>
    <div><span>Conexión</span>${run.proxy ? `Proxy ${esc(run.proxy)}` : 'Directa'}</div>
  </div>

  <div class="card">
    <h2>Resumen &nbsp;<span class="verd ${veredicto[1]}">${veredicto[0]}</span></h2>
    <div class="kpis">
      <div class="kpi"><b>${total}</b>Pruebas ejecutadas</div>
      <div class="kpi ok"><b>${ok}</b>OK</div>
      <div class="kpi warn"><b>${warn}</b>A revisar</div>
      <div class="kpi fail"><b>${fail}</b>Caídas</div>
    </div>
  </div>

  <div class="card">
    <h2>Pruebas realizadas</h2>
    <div class="tbl"><table>
      <thead><tr><th>#</th><th>Resultado</th><th>API</th><th>Método</th><th>HTTP</th><th>Tiempo</th><th>Criterio esperado</th><th>Hora</th></tr></thead>
      <tbody>${filas}</tbody>
    </table></div>
  </div>

  <div class="card">
    <h2>Detalle de cada prueba</h2>
    ${detalle}
  </div>

  <footer>Generado automáticamente el ${esc(fechaHora(run.fin))} · Contraseñas y tokens ocultos (••••••)</footer>
</div></body></html>`;
}

function safeOk(fn, r) { try { return !!fn(r.status, r.data, r.ms); } catch { return false; } }

function fieldDefaults(a) {
  const v = {};
  (a.fields || []).forEach((f) => {
    if (f === 'separator') return;
    v[f.key] = typeof f.default === 'function' ? f.default() : (f.default ?? '');
  });
  return v;
}

function markResult(id, st, r, note) {
  state.results[id] = { state: st, status: r?.status, ms: r?.ms, note: note || state.results[id]?.note };
}

/* ── colapsar grupos / padres del menú ── */
function saveCollapsed() { localStorage.setItem('facturador.collapsed', JSON.stringify(state.collapsed)); }
function toggleCollapse(key) { state.collapsed[key] = !state.collapsed[key]; saveCollapsed(); renderSidebar(); }

/* ── render: sidebar con luces, anidado en 2 niveles (Con Auth / Sin Auth) ── */
const NAV_SECTIONS = [
  { type: 'group',  group: 'Autenticación' },
  { type: 'parent', parent: 'Con Auth' },
  { type: 'parent', parent: 'Sin Auth' },
  { type: 'group',  group: 'Estado' },
];

function renderSidebar() {
  const nav = $('navList');
  nav.innerHTML = '';
  NAV_SECTIONS.forEach((sec) => {
    if (sec.type === 'group') {
      const items = APIS.filter((a) => a.group === sec.group && apiDisponible(a));
      if (items.length) renderGroup(nav, sec.group, sec.group, items, false);
    } else {
      renderParent(nav, sec.parent);
    }
  });
}

function renderParent(nav, parentName) {
  const items = APIS.filter((a) => a.parent === parentName && apiDisponible(a));
  if (!items.length) return;
  const key = `__parent_${parentName}`;
  const collapsed = !!state.collapsed[key];
  const res = items.map((a) => state.results[a.id]).filter(Boolean);
  const cnt = (s) => res.filter((r) => r.state === s).length;
  const cls = parentName === 'Con Auth' ? 'auth' : 'noauth';

  const head = el('div', `nav-parent-head ${cls}${collapsed ? ' collapsed' : ''}`);
  head.innerHTML = `
    <span class="ngh-chev">▾</span>
    <span class="nph-label">${parentName}</span>
    ${res.length
      ? `<span class="ngh-dots">${cnt('fail') ? `<i class="gd gd-fail"></i>` : ''}${cnt('warn') ? `<i class="gd gd-warn"></i>` : ''}${cnt('ok') ? `<i class="gd gd-ok"></i>` : ''}</span>`
      : ''}
    <span class="ngh-count">${items.length}</span>`;
  head.addEventListener('click', () => toggleCollapse(key));
  nav.appendChild(head);
  if (collapsed) return;

  const box = el('div', 'nav-parent-items');
  const groups = [...new Set(items.map((a) => a.group))];
  groups.forEach((g) => renderGroup(box, `${key}::${g}`, g, items.filter((a) => a.group === g), true));
  nav.appendChild(box);
}

function renderGroup(container, collapseKey, label, itemsList, nested) {
  const items = itemsList.map((a) => ({ a, i: APIS.indexOf(a) }));
  const collapsed = !!state.collapsed[collapseKey];
  const res = items.map((x) => state.results[x.a.id]).filter(Boolean);
  const cnt = (s) => res.filter((r) => r.state === s).length;

  const head = el('div', `nav-group-head${nested ? ' nested' : ''}${collapsed ? ' collapsed' : ''}`);
  head.innerHTML = `
    <span class="ngh-chev">▾</span>
    <span class="ngh-label">${label}</span>
    ${res.length
      ? `<span class="ngh-dots">${cnt('fail') ? `<i class="gd gd-fail"></i>` : ''}${cnt('warn') ? `<i class="gd gd-warn"></i>` : ''}${cnt('ok') ? `<i class="gd gd-ok"></i>` : ''}</span>`
      : ''}
    <span class="ngh-count">${items.length}</span>`;
  head.addEventListener('click', () => toggleCollapse(collapseKey));
  container.appendChild(head);
  if (collapsed) return;

  const box = el('div', `nav-group-items${nested ? ' nested' : ''}`);
  items.forEach(({ a, i }) => {
    const r = state.results[a.id];
    const dotCls = r ? `dot-${r.state}` : 'dot-idle';
    const li = el('li', `nav-item${i === state.current ? ' active' : ''}`);
    li.innerHTML = `
      <span class="light ${dotCls}" title="${r?.note || 'sin probar'}"></span>
      <span class="nav-method m-${mth(a).toLowerCase()}">${mth(a)}</span>
      <span class="nav-item-label">${a.label}</span>
      ${a.emits ? '<span class="emits-badge" title="Genera un DTE real">DTE</span>' : ''}
      ${r?.status ? `<span class="nav-status">${r.status}</span>` : ''}
    `;
    li.addEventListener('click', () => selectApi(i));
    box.appendChild(li);
  });
  container.appendChild(box);
}

function renderResumen() {
  const box = $('resumen');
  if (!box) return;
  const vals = Object.values(state.results);
  if (!vals.length) { box.style.display = 'none'; return; }
  const c = (s) => vals.filter((v) => v.state === s).length;
  box.style.display = 'flex';
  box.innerHTML = `
    <span class="chip chip-ok">${c('ok')} OK</span>
    <span class="chip chip-warn">${c('warn')} revisar</span>
    <span class="chip chip-fail">${c('fail')} caídas</span>`;
  $('btnInforme').style.display = state.lastRun ? 'block' : 'none';
}

/* ── render: form + preview ── */
function selectApi(i) {
  state.current = i;
  state.editingJson = false;
  const a = APIS[i];
  const keys = a.parent ? [a.group, `__parent_${a.parent}`, `__parent_${a.parent}::${a.group}`] : [a.group];
  let changed = false;
  keys.forEach((k) => { if (state.collapsed[k]) { state.collapsed[k] = false; changed = true; } });
  if (changed) saveCollapsed();
  renderSidebar();
  renderForm();
}

function renderForm() {
  const a = api();
  $('apiTitle').textContent = a.label;
  $('apiGroup').textContent = a.group;
  const m = $('apiMethod');
  m.textContent = mth(a); m.className = `http-method method-${mth(a)}`;
  $('apiPath').textContent = a.path || (a.buildUrl ? '(url dinámica)' : '');
  $('emitWarn').style.display = a.emits ? 'flex' : 'none';
  $('authTag').textContent = a.auth === 'bearer' ? 'Bearer JWT' : 'Sin token';
  $('authTag').className = `auth-tag ${a.auth === 'bearer' ? 'auth-jwt' : 'auth-none'}`;

  const grid = $('fields');
  grid.innerHTML = '';
  (a.fields || []).forEach((f) => {
    if (f === 'separator') { grid.appendChild(el('hr', 'sep')); return; }
    const g = el('div', 'field');
    g.appendChild(el('label', 'flabel', `${f.label}${f.required === false ? '' : ' '}`));
    let input;
    if (f.type === 'select') {
      input = el('select', 'finput');
      (f.options || []).forEach((o) => { const op = el('option'); op.value = o; op.textContent = o; input.appendChild(op); });
    } else {
      input = el('input', 'finput');
      input.type = f.type === 'password' ? 'text' : (f.type || 'text');
    }
    input.id = `f_${f.key}`;
    input.value = typeof f.default === 'function' ? f.default() : (f.default ?? '');
    input.addEventListener('input', refreshPreview);
    g.appendChild(input);
    if (f.hint) g.appendChild(el('span', 'fhint', f.hint));
    grid.appendChild(g);
  });
  if (!(a.fields || []).length) grid.appendChild(el('p', 'no-fields', 'Esta API no requiere parámetros.'));

  refreshPreview();
  renderResponse(null);
}

function refreshPreview() {
  const a = api();
  const url = buildUrl(a) || '—';
  $('urlPreview').textContent = url;
  $('rbMethod').textContent = mth(a);
  $('rbMethod').className = `rb-method method-${mth(a)}`;
  $('rbUrl').textContent = url;
  $('rbUrl').title = url;
  $('rbAuth').textContent = a.auth === 'bearer' ? 'Bearer JWT' : 'Sin token';
  $('rbAuth').className = `rb-tag ${a.auth === 'bearer' ? 'auth-jwt' : 'auth-none'}`;
  const body = buildBody(a);
  if (body == null) {
    $('jsonArea').value = '';
    $('jsonView').innerHTML = '<span class="dim">— sin body —</span>';
  } else if (!state.editingJson) {
    const s = JSON.stringify(body, null, 2);
    $('jsonArea').value = s;
    $('jsonView').innerHTML = hl(s);
  }
}

function renderResponse(r) {
  const meta = $('respMeta'), box = $('respBody');
  if (!r) {
    meta.style.display = 'none';
    box.innerHTML = '<div class="resp-empty">▶ Ejecuta una solicitud para ver la respuesta</div>';
    return;
  }
  meta.style.display = 'flex';
  const sc = $('respCode');
  sc.textContent = r.netError ? 'NET' : r.status;
  sc.className = 'status-code ' + (r.netError || r.status >= 400 ? 'st-bad' : 'st-ok');
  $('respTime').textContent = `${r.ms}ms`;
  const good = !r.netError && r.status >= 200 && r.status < 300;
  box.innerHTML = '';
  box.appendChild(el('div', `resp-alert ${good ? 'ok' : 'bad'}`,
    `<span>${good ? '✓' : '✗'}</span><span><b>${r.netError ? 'Error de red' : r.status}</b> — ${good ? 'OK' : (r.data?.mensajeRespuesta || r.data?.message || 'Error')}</span>`));
  box.appendChild(el('pre', 'resp-json', hl(JSON.stringify(r.data, null, 2))));
}

/* ── syntax highlight ── */
function hl(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (m) => {
        let c = 'j-num';
        if (/^"/.test(m)) c = /:$/.test(m) ? 'j-key' : 'j-str';
        else if (/true|false/.test(m)) c = 'j-bool';
        else if (/null/.test(m)) c = 'j-null';
        return `<span class="${c}">${m}</span>`;
      });
}

/* ── history ── */
function addHistory(a, r, opts = {}) {
  state.history.unshift({
    id: Date.now() + Math.random(), label: a.label, method: mth(a),
    status: r.netError ? (r.aborted ? 'TIMEOUT' : 'NET') : r.status, ms: r.ms,
    url: opts.url ?? buildUrl(a), body: opts.body ?? buildBody(a), data: r.data,
    tag: opts.tag || null, outcome: opts.outcome || null,
    ts: new Date().toLocaleTimeString('es-CL'),
  });
  state.history = state.history.slice(0, 60);
  renderHistory();
}
function renderHistory() {
  const list = $('histList');
  if (!state.history.length) { list.innerHTML = '<li class="hist-empty">Sin solicitudes aún</li>'; return; }
  list.innerHTML = '';
  state.history.forEach((h) => {
    const ok = h.outcome ? h.outcome === 'ok' : (h.status >= 200 && h.status < 300);
    const cls = h.outcome === 'warn' ? 'warn' : (ok ? 'ok' : 'bad');
    const li = el('li', `hist-item ${cls}`);
    li.innerHTML = `<div class="hist-label">${h.tag ? '<span class="hist-tag">◈</span> ' : ''}${h.method} ${h.label}</div>
      <div class="hist-meta"><b>${h.status}</b> · ${h.ms}ms · ${h.ts}</div>`;
    li.addEventListener('click', () => openModal(h));
    list.appendChild(li);
  });
}
function openModal(h) {
  $('modalTitle').textContent = `${h.method} ${h.label}`;
  $('modalBody').innerHTML = `
    <p class="m-sub">${h.ts} · ${h.status} · ${h.ms}ms${h.tag ? ` · ${h.tag}` : ''}</p>
    <p class="m-h">URL</p><pre class="m-pre">${h.url}</pre>
    ${h.body ? `<p class="m-h">Request</p><pre class="m-pre">${hl(JSON.stringify(h.body, null, 2))}</pre>` : ''}
    <p class="m-h">Response</p><pre class="m-pre">${hl(JSON.stringify(h.data, null, 2))}</pre>`;
  $('modal').style.display = 'flex';
}

/* ── modal AMBIENTES / URLS ── */
function openEnvModal() {
  renderEnvBases();
  renderEnvApis();
  $('envModal').style.display = 'flex';
}

function renderEnvBases() {
  const box = $('envBases');
  box.innerHTML = '';
  box.appendChild(etHead('Servicio'));
  BASE_KEYS.forEach((k) => {
    const row = etRow();
    row.appendChild(el('span', 'et-name', BASE_LABEL[k]));
    ENV_NAMES.forEach((name) => {
      const cur = (baseOv[name] || {})[k] ?? ENVS[name][k] ?? '';
      const isOv = (baseOv[name] || {})[k] != null;
      const inp = el('input', 'et-input' + (isOv ? ' et-ov' : ''));
      inp.value = cur;
      inp.spellcheck = false;
      inp.placeholder = 'no aplica';
      inp.title = isOv ? 'valor personalizado' : 'valor por defecto';
      inp.addEventListener('input', () => {
        const v = inp.value.trim();
        baseOv[name] = baseOv[name] || {};
        if (!v || v === ENVS[name][k]) delete baseOv[name][k];
        else baseOv[name][k] = v;
        if (!Object.keys(baseOv[name]).length) delete baseOv[name];
        saveOv(LS.baseOv, baseOv);
        inp.classList.toggle('et-ov', (baseOv[name] || {})[k] != null);
        renderEnvApis();
        refreshPreview();
      });
      row.appendChild(inp);
    });
    box.appendChild(row);
  });
}

function renderEnvApis() {
  const box = $('envApis');
  box.innerHTML = '';
  box.appendChild(etHead('Prueba'));
  APIS.forEach((a) => {
    const row = etRow();
    row.appendChild(el('span', 'et-name', `<span class="et-m m-${a.method.toLowerCase()}">${a.method}</span> ${a.label}`));
    ENV_NAMES.forEach((name) => {
      if (!apiDisponible(a, name)) {
        const na = el('input', 'et-input et-na'); na.disabled = true; na.placeholder = 'no disponible en este ambiente';
        row.appendChild(na); return;
      }
      const ov = (apiOv[name] || {})[a.id];
      const inp = el('input', 'et-input' + (ov ? ' et-ov' : ''));
      inp.value = ov ?? resolvedUrl(a, name);
      inp.spellcheck = false;
      inp.title = ov ? 'URL personalizada para esta prueba' : 'URL calculada (editar = sobrescribir)';
      inp.addEventListener('input', () => {
        const v = inp.value.trim();
        apiOv[name] = apiOv[name] || {};
        if (!v || v === resolvedUrlNoApiOv(a, name)) delete apiOv[name][a.id];
        else apiOv[name][a.id] = v;
        if (!Object.keys(apiOv[name]).length) delete apiOv[name];
        saveOv(LS.apiOv, apiOv);
        inp.classList.toggle('et-ov', (apiOv[name] || {})[a.id] != null);
        refreshPreview();
      });
      row.appendChild(inp);
    });
    box.appendChild(row);
  });
}
function etRow() { const r = el('div', 'et-row'); r.style.gridTemplateColumns = `190px repeat(${ENV_NAMES.length}, minmax(0, 1fr))`; return r; }
function etHead(first) {
  const r = etRow(); r.classList.add('et-head');
  r.innerHTML = `<span>${first}</span>` + ENV_NAMES.map((n) => `<span>${n}</span>`).join('');
  return r;
}

/* URL resuelta ignorando el override por-prueba (para comparar y limpiar) */
function resolvedUrlNoApiOv(a, name) {
  const e = envFor(name);
  const defs = fieldDefaults(a);
  if (a.buildUrl) { try { return a.buildUrl(defs, e); } catch { return ''; } }
  const base = ({ auth: e.auth, recepcion: e.recepcion, nc: e.nc, consultas: e.consultas, raw: '' })[a.service] ?? e.recepcion;
  return base + (a.path || '');
}

function resetEnvOverrides() {
  baseOv = {}; apiOv = {};
  localStorage.removeItem(LS.baseOv);
  localStorage.removeItem(LS.apiOv);
  renderEnvBases(); renderEnvApis(); refreshPreview();
  toast('info', 'URLs restablecidas a los valores por defecto');
}

/* ── toasts ── */
function toast(type, msg, ms = 3200) {
  const ic = { success: '✓', error: '✗', info: 'ℹ', warning: '⚠' }[type] || 'ℹ';
  const t = el('div', `toast ${type}`, `<span>${ic}</span><span>${msg}</span>`);
  $('toasts').appendChild(t);
  setTimeout(() => t.remove(), ms);
}
function setStatus(type, text) {
  $('statusBar').className = `status-ind ${type === 'loading' ? 'loading' : type === 'error' ? 'error' : ''}`;
  $('statusTxt').textContent = text;
}

function refreshTokenMeta() {
  const t = getToken();
  const m = $('tokenMeta');
  if (!t) { m.textContent = 'sin token'; m.className = 'token-meta bad'; return; }
  if (tokenVigente(t)) {
    const mins = Math.round((tokenExp(t) * 1000 - Date.now()) / 60000);
    m.textContent = tokenExp(t) ? `vigente ~${mins} min` : 'token cargado';
    m.className = 'token-meta ok';
  } else { m.textContent = 'token vencido — re-login'; m.className = 'token-meta bad'; }
}

/* ── events ── */
function bind() {
  $('btnExec').addEventListener('click', executeCurrent);
  $('btnProbarAuth').addEventListener('click', () => probarAmbiente('con-auth'));
  $('btnProbarSinAuth').addEventListener('click', () => probarAmbiente('sin-auth'));
  $('btnProbarDummys').addEventListener('click', () => probarAmbiente('dummys'));
  $('btnInforme').addEventListener('click', () => descargarInforme());
  $('btnReset').addEventListener('click', () => { state.editingJson = false; $('jsonWrap').classList.remove('editing'); renderForm(); toast('info', 'Campos reseteados'); });
  $('btnCopyReq').addEventListener('click', () => navigator.clipboard.writeText($('jsonArea').value).then(() => toast('success', 'JSON copiado')));
  $('btnCopyResp').addEventListener('click', () => {
    const p = $('respBody').querySelector('.resp-json');
    navigator.clipboard.writeText(p ? p.textContent : '').then(() => toast('success', 'Respuesta copiada'));
  });
  $('btnEditJson').addEventListener('click', () => {
    state.editingJson = !state.editingJson;
    $('jsonWrap').classList.toggle('editing', state.editingJson);
    $('btnEditJson').textContent = state.editingJson ? '👁 Ver' : '✎ Editar';
  });
  $('jsonArea').addEventListener('input', () => { if (state.editingJson) $('jsonView').innerHTML = hl($('jsonArea').value); });

  $('envSel').addEventListener('change', (e) => {
    cambiarAmbiente(e.target.value);
  });
  $('proxyInput').addEventListener('change', (e) => {
    state.proxy = e.target.value.trim(); localStorage.setItem(LS.proxy, state.proxy);
    toast('info', state.proxy ? `Proxy: ${state.proxy}` : 'Modo directo');
  });
  $('tokenInput').addEventListener('change', (e) => setToken(e.target.value.trim()));
  $('tokenToggle').addEventListener('click', () => {
    const i = $('tokenInput'); i.type = i.type === 'password' ? 'text' : 'password';
  });
  $('btnLoginQuick').addEventListener('click', async () => {
    const loginApi = APIS.find((a) => a.id === 'login');
    const r = await doRequest(loginApi, { body: { user: DEFAULTS.loginUser, pass: DEFAULTS.loginPass } });
    if (r.ok && r.data?.data?.token) { setToken(r.data.data.token); toast('success', '🔑 Token obtenido'); }
    else toast('error', r.data?.message || 'No se pudo obtener token');
    markResult('login', r.ok && r.data?.code === 1 ? 'ok' : 'warn', r);
    renderSidebar();
  });

  $('themeToggle').addEventListener('click', () => {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem(LS.theme, state.theme);
  });
  $('clearHist').addEventListener('click', () => { state.history = []; renderHistory(); });
  $('modalClose').addEventListener('click', () => $('modal').style.display = 'none');
  $('modal').addEventListener('click', (e) => { if (e.target === $('modal')) $('modal').style.display = 'none'; });

  $('rbCopy').addEventListener('click', () => navigator.clipboard.writeText($('rbUrl').textContent).then(() => toast('success', 'URL copiada')));
  $('btnEnvs').addEventListener('click', openEnvModal);
  $('envModalClose').addEventListener('click', () => $('envModal').style.display = 'none');
  $('envModal').addEventListener('click', (e) => { if (e.target === $('envModal')) $('envModal').style.display = 'none'; });
  $('envReset').addEventListener('click', resetEnvOverrides);
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !$('btnExec').disabled) { e.preventDefault(); executeCurrent(); }
  });
}

function cambiarAmbiente(name) {
  state.env = name; localStorage.setItem(LS.env, state.env);
  $('envSel').value = name;
  state.results = {};
  applyEnvUi();
  if (apiDisponible(api())) { renderSidebar(); renderForm(); } else selectApi(firstDisponible());
  renderResumen();
  toast('info', `Ambiente: ${state.env}`);
}

/* ajustes de UI que dependen del ambiente (color, botón Con Auth en DUMMYS) */
function applyEnvUi() {
  $('envDot').style.background = env().color;
  const b = $('btnProbarAuth');
  const soloSin = !!ENVS[state.env].soloSinAuth;
  b.disabled = soloSin;
  b.title = soloSin ? `${state.env} solo expone APIs Sin Auth (/v1/app/...)` : '';
}
function firstDisponible() { const i = APIS.findIndex((a) => apiDisponible(a)); return i < 0 ? 0 : i; }

/* ── init ── */
function init() {
  document.documentElement.setAttribute('data-theme', state.theme);
  if (!ENVS[state.env]) state.env = 'QA';
  $('envSel').innerHTML = ENV_NAMES.map((n) => `<option value="${n}">${ENVS[n].label || n}</option>`).join('');
  $('envSel').value = state.env;
  applyEnvUi();
  $('proxyInput').value = state.proxy;
  $('tokenInput').value = getToken();
  refreshTokenMeta();
  selectApi(apiDisponible(APIS[0]) ? 0 : firstDisponible());
  renderHistory();
  bind();
  toast('info', 'Certificador Facturador listo. Ctrl+Enter para ejecutar.', 3500);
}
document.addEventListener('DOMContentLoaded', init);
