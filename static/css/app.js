/* app.js — Compilador de Nutrias v2 — Analisis en tiempo real */

// ── Ejemplos ──────────────────────────────────────────────────
const EJEMPLOS = {
  valido: `INICIO
    PACIENTE: Sofia;
    EDAD: 25;
    PESO: 65.5;
    RESTRICCION: <lumbar>;
    OBJETIVO: bajar_grasa;

    SI PESO > 60 ENTONCES
        RUTINA: rutina_basica;
            ACCION: flexiones * 10;
            ACCION: proteina + carbohidrato;
        FIN
    FIN

    DIETA: dieta_proteica;
        ACCION: desayuno_avena;
        ACCION: almuerzo_pollo;
    FIN

    IMPRIMIR rutina_basica;
FIN`,

  errores: `INICIO
    PACIENTE: @Sofia;
    EDAD: veinticinco;
    SI PESO > 60
        RUTINA: rutina_basica;
            ACCION: flexiones;
        FIN
    FIN
FIN`
};

// ── State ──────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
let _debounce = null;
let _tabActual = 'tokens';

// ── Init ───────────────────────────────────────────────────────
sincronizarLineas();

// ── Editor ─────────────────────────────────────────────────────
function onEditorInput() {
  sincronizarLineas();
  setStatus('loading', 'Analizando...');
  clearTimeout(_debounce);
  _debounce = setTimeout(correrAnalisis, 400); // 400ms debounce
}

function sincronizarLineas() {
  const n = ($('editor').value.match(/\n/g) || []).length + 1;
  $('line-numbers').textContent = Array.from({length:n}, (_,i) => i+1).join('\n');
}

function sincronizarScroll() {
  $('line-numbers').scrollTop = $('editor').scrollTop;
}

function cargarEjemplo(tipo) {
  $('editor').value = EJEMPLOS[tipo] || '';
  sincronizarLineas();
  onEditorInput();
}

function limpiar() {
  $('editor').value = '';
  sincronizarLineas();
  limpiarResultados();
  setStatus('idle', 'Esperando...');
}

// ── Tabs ───────────────────────────────────────────────────────
function mostrarPanel(tab) {
  _tabActual = tab;
  ['tokens','arbol-txt','arbol-vis'].forEach(t => {
    $('panel-' + t).style.display   = t === tab ? 'block' : 'none';
    $('tab-'   + t).classList.toggle('active', t === tab);
  });
  $('leyenda-tokens').style.display = tab === 'tokens' ? 'flex' : 'none';
}

function cambiarTab(seccion) {
  $('page-title').textContent = seccion === 'lexico'
    ? 'Analizador Léxico' : 'Analizador Sintactico';
  $('page-sub').textContent = seccion === 'lexico'
    ? 'Fase 1 — Analisis en tiempo real'
    : 'Fase 2 — Arbol sintactico';
  document.querySelectorAll('.nav-item').forEach((el,i) =>
    el.classList.toggle('active', i === (seccion==='lexico'?0:1)));
  if (seccion === 'sintactico') mostrarPanel('arbol-txt');
  else mostrarPanel('tokens');
}

// ── Status pill ────────────────────────────────────────────────
function setStatus(tipo, texto) {
  const dot  = $('status-dot');
  const span = $('status-text');
  dot.className = 'status-dot ' + tipo;
  span.textContent = texto;
}

// ── Analisis principal ─────────────────────────────────────────
async function correrAnalisis() {
  const codigo = $('editor').value.trim();
  if (!codigo) { limpiarResultados(); setStatus('idle','Esperando...'); return; }

  try {
    const resp = await fetch('/parsear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo })
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    renderTodo(data);
  } catch(e) {
    setStatus('error', 'Sin conexion al servidor');
  }
}

// ── Limpiar ─────────────────────────────────────────────────────
function limpiarResultados() {
  $('token-body').innerHTML = '';
  $('token-table').style.display = 'none';
  $('empty-state').style.display = 'flex';
  $('arbol-pre').style.display = 'none';
  $('empty-arbol-txt').style.display = 'flex';
  $('arbol-vis-container').innerHTML = '';
  $('empty-arbol-vis').style.display = 'flex';
  $('error-panel-lex').style.display  = 'none';
  $('error-panel-sint').style.display = 'none';
  $('stat-tokens').textContent = '0';
  $('stat-reservadas').textContent = '0';
  $('stat-errores').textContent = '0';
  $('stat-estado').textContent = '—';
}

// ── Render completo ─────────────────────────────────────────────
function renderTodo(data) {
  const { tokens, errores_lexicos, arbol_texto, arbol_dict, error_sintactico, resumen } = data;

  // ── Stats ──────────────────────────────────
  const reservadas = (tokens||[]).filter(t => t.categoria === 'reservada').length;
  $('stat-tokens').textContent     = (tokens||[]).length;
  $('stat-reservadas').textContent = reservadas;
  $('stat-errores').textContent    = (errores_lexicos||[]).length;
  $('stat-estado').textContent     = resumen.exitoso ? 'Aceptada' : 'Con errores';

  const iconEstado = $('stat-estado-icon');
  iconEstado.className = resumen.exitoso ? 'stat-icon green' : 'stat-icon red';
  iconEstado.innerHTML = resumen.exitoso
    ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
    : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

  const iconErrLex = $('stat-errlex-icon');
  iconErrLex.className = (errores_lexicos||[]).length > 0 ? 'stat-icon red' : 'stat-icon green';

  // ── Tabla tokens ────────────────────────────
  const tbody = $('token-body');
  tbody.innerHTML = '';
  if (tokens && tokens.length) {
    tokens.forEach((t, i) => {
      const tr = document.createElement('tr');
      tr.style.animationDelay = Math.min(i * 8, 200) + 'ms';
      tr.innerHTML = `
        <td style="color:var(--text-muted);font-size:11px">${i+1}</td>
        <td><code class="lexema-code">${esc(t.lexema)}</code></td>
        <td><span class="badge ${t.categoria}">${t.tipo}</span></td>
        <td>${t.linea}</td>
        <td>${t.columna}</td>`;
      tbody.appendChild(tr);
    });
    $('token-table').style.display = 'table';
    $('empty-state').style.display = 'none';
  } else {
    $('token-table').style.display = 'none';
    $('empty-state').style.display = 'flex';
  }

  // ── Arbol texto ─────────────────────────────
  if (arbol_texto) {
    $('arbol-pre').textContent    = 'Cadena aceptada\n\nArbol sintactico:\n\n' + arbol_texto;
    $('arbol-pre').style.display  = 'block';
    $('empty-arbol-txt').style.display = 'none';
  } else {
    $('arbol-pre').style.display  = 'none';
    $('empty-arbol-txt').style.display = 'flex';
  }

  // ── Arbol visual ────────────────────────────
  const visContainer = $('arbol-vis-container');
  if (arbol_dict) {
    visContainer.innerHTML = '';
    visContainer.appendChild(construirArbolVisual(arbol_dict));
    $('empty-arbol-vis').style.display = 'none';
  } else {
    visContainer.innerHTML = '';
    $('empty-arbol-vis').style.display = 'flex';
  }

  // ── Errores lexicos ─────────────────────────
  if (errores_lexicos && errores_lexicos.length > 0) {
    const eb = $('error-body-lex');
    eb.innerHTML = '';
    errores_lexicos.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code class="lexema-code" style="color:var(--red)">${esc(e.lexema)}</code></td>
        <td>${e.linea}</td>
        <td>${e.columna}</td>
        <td>${esc(e.mensaje)}</td>`;
      eb.appendChild(tr);
    });
    $('error-count-lex').textContent = errores_lexicos.length + ' error' + (errores_lexicos.length!==1?'es':'');
    $('error-panel-lex').style.display = 'block';
  } else {
    $('error-panel-lex').style.display = 'none';
  }

  // ── Error sintactico ─────────────────────────
  if (error_sintactico) {
    $('error-sint-body').innerHTML = `
      <div class="error-sint-msg">${esc(error_sintactico.mensaje)}</div>
      <div class="error-sint-hint">
        Se esperaba: <strong>${esc(error_sintactico.esperado)}</strong> &nbsp;·&nbsp;
        Se encontro: <code>${esc(error_sintactico.encontrado)}</code> (${esc(error_sintactico.tipo_encontrado)})
        &nbsp;·&nbsp; Linea ${error_sintactico.linea}, columna ${error_sintactico.columna}
      </div>`;
    $('error-panel-sint').style.display = 'block';
  } else {
    $('error-panel-sint').style.display = 'none';
  }

  // ── Status ──────────────────────────────────
  if (resumen.exitoso) {
    setStatus('ok', 'Cadena aceptada');
  } else if ((errores_lexicos||[]).length > 0) {
    setStatus('error', 'Error lexico');
  } else if (error_sintactico) {
    setStatus('warning', 'Error sintactico');
  } else {
    setStatus('idle', 'Analizando...');
  }
}

// ── Arbol visual recursivo ──────────────────────────────────────
function construirArbolVisual(nodo) {
  const wrap = document.createElement('div');
  wrap.className = 'tree-node-wrap';

  const box = document.createElement('div');
  const esTerminal = nodo.es_hoja;
  const esProg     = nodo.nombre === 'PROGRAMA';
  box.className = 'tree-box ' + (esProg ? 'programa' : esTerminal ? 'terminal' : 'nodo');
  box.textContent = nodo.nombre;
  wrap.appendChild(box);

  if (nodo.hijos && nodo.hijos.length > 0) {
    const childrenWrap = document.createElement('div');
    childrenWrap.className = 'tree-children';
    nodo.hijos.forEach(hijo => {
      childrenWrap.appendChild(construirArbolVisual(hijo));
    });
    wrap.appendChild(childrenWrap);
  }
  return wrap;
}

// ── Helpers ─────────────────────────────────────────────────────
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Ctrl+Enter sigue funcionando para forzar un analisis
document.addEventListener('keydown', e => {
  if ((e.ctrlKey||e.metaKey) && e.key==='Enter') {
    e.preventDefault(); clearTimeout(_debounce); correrAnalisis();
  }
});
