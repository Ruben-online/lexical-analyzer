/* app.js — Lógica del frontend del Analizador Léxico */

// ── Ejemplos de código .nut ──────────────────────────────────
const EJEMPLOS = {
  valido: `// Receta válida — paciente Sofia García
PACIENTE: Sofia;
EDAD: 25;
PESO: 65.5;
RESTRICCION: <lumbar>;
OBJETIVO: bajar_grasa;

RUTINA: rutina_basica;
ACCION: flexiones * 3;
ACCION: sentadillas * 10;
OBJETIVO: tonificar;

DIETA: dieta_proteica;
ACCION: proteina + carbohidrato;
ACCION: almuerzo_pollo;`,

  errores: `// Ejemplo con errores léxicos
; PACIENTE
3edad = 10;
PACIENTE: @Sofia;
EDAD: veinticinco;
PESO: 3.14.5;
OBJETIVO: "meta sin cerrar`
};

//Helpers ──────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function cargarEjemplo(tipo) {
  $('editor').value = EJEMPLOS[tipo] || '';
  sincronizarLineas();
  // limpiar resultados anteriores
  $('token-table').style.display  = 'none';
  $('empty-state').style.display  = 'flex';
  $('error-panel').style.display  = 'none';
  $('stats-row').style.display    = 'none';
}

function limpiar() {
  $('editor').value = '';
  $('token-body').innerHTML  = '';
  $('error-body').innerHTML  = '';
  $('token-table').style.display  = 'none';
  $('empty-state').style.display  = 'flex';
  $('error-panel').style.display  = 'none';
  $('stats-row').style.display    = 'none';
  sincronizarLineas();
}

//Numeros de línea ─────────────────────────────────────────
function sincronizarLineas() {
  const lineas = ($('editor').value.match(/\n/g) || []).length + 1;
  $('line-numbers').textContent = Array.from({length: lineas}, (_, i) => i + 1).join('\n');
}

function sincronizarScroll() {
  $('line-numbers').scrollTop = $('editor').scrollTop;
}

//Analizar ─────────────────────────────────────────────────
async function analizar() {
  const codigo = $('editor').value.trim();
  if (!codigo) {
    alert('Escribe código .nut antes de analizar.');
    return;
  }

  // Estado de carga
  const btn = document.querySelector('.btn-primary');
  btn.textContent = 'Analizando…';
  btn.disabled = true;

  try {
    const resp = await fetch('/analizar', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ codigo })
    });

    if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`);
    const data = await resp.json();
    renderResultados(data);

  } catch (err) {
    alert('No se pudo conectar con el servidor.\n' + err.message);
  } finally {
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg> Analizar`;
    btn.disabled = false;
  }
}

//Render de resultados ─────────────────────────────────────
function renderResultados({ tokens, errores, resumen }) {

  //Stats ─────────────────────────────────────
  const reservadas = tokens.filter(t => t.categoria === 'reservada').length;
  $('stat-tokens').textContent    = resumen.total_tokens;
  $('stat-reservadas').textContent = reservadas;
  $('stat-errores').textContent   = resumen.total_errores;
  $('stat-estado').textContent    = resumen.exitoso ? 'Sin errores' : 'Con errores';

  const iconoEstado = $('stat-estado-icon');
  if (resumen.exitoso) {
    iconoEstado.className = 'stat-icon green';
    iconoEstado.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
  } else {
    iconoEstado.className = 'stat-icon red';
    iconoEstado.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  }
  $('stats-row').style.display = 'grid';

  // ── Tabla de tokens ───────────────────────────
  const tbody = $('token-body');
  tbody.innerHTML = '';

  tokens.forEach((t, i) => {
    const tr = document.createElement('tr');
    tr.style.animationDelay = `${i * 12}ms`;
    tr.innerHTML = `
      <td style="color:var(--text-muted);font-size:11px">${i + 1}</td>
      <td><code class="lexema-code">${escHtml(t.lexema)}</code></td>
      <td><span class="badge ${t.categoria}">${t.tipo}</span></td>
      <td>${t.linea}</td>
      <td>${t.columna}</td>
    `;
    tbody.appendChild(tr);
  });

  $('empty-state').style.display = 'none';
  $('token-table').style.display = tokens.length ? 'table' : 'none';
  if (!tokens.length) $('empty-state').style.display = 'flex';

  //Panel de errores ──────────────────────────
  if (errores.length > 0) {
    const ebdy = $('error-body');
    ebdy.innerHTML = '';
    errores.forEach((e, i) => {
      const tr = document.createElement('tr');
      tr.style.animationDelay = `${i * 20}ms`;
      tr.innerHTML = `
        <td><code class="lexema-code" style="color:var(--red)">${escHtml(e.lexema)}</code></td>
        <td>${e.linea}</td>
        <td>${e.columna}</td>
        <td>${escHtml(e.mensaje)}</td>
      `;
      ebdy.appendChild(tr);
    });
    $('error-count').textContent   = `${errores.length} error${errores.length !== 1 ? 'es' : ''}`;
    $('error-panel').style.display = 'block';
  } else {
    $('error-panel').style.display = 'none';
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

//Atajo de teclado: Ctrl+Enter ─────────────────────────────
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    analizar();
  }
});

//Init ─────────────────────────────────────────────────────
sincronizarLineas();