/* app.js - Compilador de Nutrias - Modo Caso de Uso */

const $ = id => document.getElementById(id);
let _modoActual = 'formulario';
let _tabActual = 'codigo-gen';
let _codigoActual = '';
let _debounce = null;
let _semOk = false;
let _phaseTimers = [];
let _phaseRunId = 0;
let _lastTokenCount = 0;

const PHASES = ['lexica', 'sintactica', 'semantica', 'generacion'];
const PHASE_LABELS = {
  lexica: 'léxica',
  sintactica: 'sintáctica',
  semantica: 'semántica',
  generacion: 'generación',
  completa: 'completa',
  ninguna: '-'
};

const EJEMPLOS_EDITOR = {
  valido: `INICIO
    PACIENTE: Sofia_Garcia;
    EDAD: 25;
    PESO: 65.5;
    RESTRICCION: <lumbar>;
    OBJETIVO: bajar_grasa;

    RUTINA: rutina_sofia;
        ACCION: cardio * 5;
        ACCION: fuerza;
    FIN

    DIETA: dieta_proteica;
        ACCION: desayuno_avena;
        ACCION: almuerzo_pollo;
    FIN

    IMPRIMIR rutina_sofia;
FIN`,
  error: `INICIO
    RUTINA: sin_paciente;
        ACCION: flexiones;
    FIN
    PACIENTE: Carlos;
FIN`
};

function sanitizeIdentifier(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, '_')
    .replace(/[^\w]/g, '');
}

function setModo(modo) {
  _modoActual = modo;
  const esForm = modo === 'formulario';

  $('modo-formulario').style.display = esForm ? 'block' : 'none';
  $('modo-codigo').style.display = esForm ? 'none' : 'flex';
  $('modo-codigo').style.flexDirection = 'column';
  $('modo-codigo').style.height = '100%';

  $('nav-formulario').classList.toggle('active', esForm);
  $('nav-codigo').classList.toggle('active', !esForm);

  $('page-title').textContent = esForm
    ? 'Modo Fácil - Formulario de Paciente'
    : 'Modo Experto - Editor de Código .nut';

  const tabCodigo = $('tab-codigo-gen');
  tabCodigo.disabled = !esForm;
  tabCodigo.classList.toggle('disabled', !esForm);
  tabCodigo.title = esForm
    ? 'Ver código generado por el formulario'
    : 'En modo experto el código se edita en el panel izquierdo';

  if (esForm) {
    mostrarResultado('codigo-gen');
    actualizarCodigoGen(_codigoActual);
  } else {
    if (_tabActual === 'codigo-gen') mostrarResultado('tokens');
    onEditorInput();
  }
}

function mostrarResultado(tab) {
  if (_modoActual === 'codigo' && tab === 'codigo-gen') return;

  _tabActual = tab;
  const tabs = ['codigo-gen', 'tokens', 'arbol', 'tabla', 'plan'];
  tabs.forEach(t => {
    const p = $('panel-' + t);
    const b = $('tab-' + t);
    if (p) p.style.display = t === tab ? 'block' : 'none';
    if (b) b.classList.toggle('active', t === tab);
  });
}

function setStatus(tipo, texto) {
  $('status-dot').className = 'status-dot ' + (tipo === 'idle' ? '' : tipo);
  $('status-text').textContent = texto;
}

function phaseLabel(phase) {
  return PHASE_LABELS[phase] || phase || '-';
}

function clearPhaseTimers() {
  _phaseTimers.forEach(timer => clearTimeout(timer));
  _phaseTimers = [];
}

function getPhaseCard() {
  return $('stat-fase')?.closest('.stat-card');
}

function setPhaseDisplay(phase, state = 'active', detail = 'Fase activa') {
  const currentIndex = PHASES.indexOf(phase);
  const phaseValue = $('stat-fase');
  const phaseDetail = $('phase-detail');
  const phaseCard = getPhaseCard();

  if (phaseValue) {
    phaseValue.textContent = phaseLabel(phase);
    phaseValue.classList.remove('bump');
    void phaseValue.offsetWidth;
    phaseValue.classList.add('bump');
  }

  if (phaseDetail) {
    phaseDetail.textContent = detail;
    phaseDetail.classList.toggle('phase-detail-error', state === 'failed');
    phaseDetail.classList.toggle('phase-detail-ok', state === 'done');
  }

  if (phaseCard) {
    phaseCard.classList.toggle('phase-running', state === 'active');
    phaseCard.classList.toggle('phase-failed', state === 'failed');
  }

  document.querySelectorAll('.phase-dot').forEach(dot => {
    const dotPhase = dot.dataset.phase;
    const dotIndex = PHASES.indexOf(dotPhase);
    dot.className = 'phase-dot';

    if (currentIndex === -1) {
      dot.classList.add('pending');
    } else if (state === 'failed' && dotPhase === phase) {
      dot.classList.add('failed');
    } else if (dotIndex < currentIndex || (state === 'done' && dotIndex <= currentIndex)) {
      dot.classList.add('done');
    } else if (dotPhase === phase && state === 'active') {
      dot.classList.add('active');
    } else if (dotIndex <= currentIndex && state !== 'failed') {
      dot.classList.add('done');
    } else {
      dot.classList.add('pending');
    }
  });
}

function resetPhaseDisplay() {
  clearPhaseTimers();
  if ($('stat-fase')) $('stat-fase').textContent = '-';
  if ($('phase-detail')) {
    $('phase-detail').textContent = 'Fase activa';
    $('phase-detail').classList.remove('phase-detail-error', 'phase-detail-ok');
  }
  const phaseCard = getPhaseCard();
  if (phaseCard) phaseCard.classList.remove('phase-running', 'phase-failed');
  document.querySelectorAll('.phase-dot').forEach(dot => {
    dot.className = 'phase-dot pending';
  });
}

function startPhaseAnimation(includeGeneration = false) {
  clearPhaseTimers();
  const runId = ++_phaseRunId;
  const phases = includeGeneration ? PHASES : PHASES.slice(0, 3);
  phases.forEach((phase, index) => {
    const timer = setTimeout(() => {
      if (runId !== _phaseRunId) return;
      setPhaseDisplay(phase, 'active', index === 0 ? 'Analizando...' : 'Fase activa');
    }, index * 180);
    _phaseTimers.push(timer);
  });
}

function finishPhaseFromData(data, includeGeneration = false) {
  clearPhaseTimers();
  _phaseRunId++;

  const erroresLexicos = data.errores_lexicos || [];
  if (erroresLexicos.length) {
    setPhaseDisplay('lexica', 'failed', 'Falló en');
    return;
  }
  if (data.error_sintactico) {
    setPhaseDisplay('sintactica', 'failed', 'Falló en');
    return;
  }
  if (data.error_semantico) {
    setPhaseDisplay('semantica', 'failed', 'Falló en');
    return;
  }

  const fase = includeGeneration && data.plan_clinico ? 'generacion' : (data.resumen?.fase_exitosa || 'semantica');
  setPhaseDisplay(fase === 'completa' ? 'generacion' : fase, 'done', 'Completado');
}

function setStatValue(id, value) {
  const el = $(id);
  if (!el) return;
  const next = String(value);
  if (el.textContent !== next) {
    el.textContent = next;
    el.classList.remove('bump');
    void el.offsetWidth;
    el.classList.add('bump');
  }
}

function generarCodigo() {
  const nombre = sanitizeIdentifier($('f-nombre').value);
  const edad = $('f-edad').value;
  const peso = $('f-peso').value;
  const objetivo = $('f-objetivo').value;
  const nivel = document.querySelector('input[name="nivel"]:checked')?.value || 'intermedio';
  const dieta = $('f-dieta').value;
  const custom = sanitizeIdentifier($('f-restriccion-custom').value);

  const checked = [...document.querySelectorAll('.restricciones-grid input[type=checkbox]:checked')];
  const restricciones = checked
    .map(el => el.value)
    .filter(v => ['lumbar', 'rodilla', 'hombro', 'presion_alta', 'diabetes', 'cervical'].includes(v));
  if (custom) restricciones.push(custom);

  const ejercicios = checked
    .map(el => el.value)
    .filter(v => ['cardio', 'fuerza', 'flexibilidad', 'funcional', 'yoga', 'natacion'].includes(v));

  if (!nombre) {
    _codigoActual = '';
    actualizarCodigoGen('');
    limpiarResultados();
    setStatus('idle', 'Esperando...');
    return;
  }

  let codigo = 'INICIO\n';
  codigo += `    PACIENTE: ${nombre};\n`;
  if (edad) codigo += `    EDAD: ${edad};\n`;
  if (peso) codigo += `    PESO: ${peso};\n`;
  restricciones.forEach(r => { codigo += `    RESTRICCION: <${r}>;\n`; });
  if (objetivo) codigo += `    OBJETIVO: ${objetivo};\n`;
  codigo += '\n';

  if (ejercicios.length > 0) {
    const nombreRutina = `rutina_${nivel}`;
    codigo += `    RUTINA: ${nombreRutina};\n`;
    ejercicios.forEach(e => { codigo += `        ACCION: ${e};\n`; });
    codigo += `    FIN\n\n`;
    codigo += `    IMPRIMIR ${nombreRutina};\n`;
  }

  if (dieta) {
    codigo += `\n    DIETA: ${dieta};\n`;
    codigo += `        ACCION: desayuno_saludable;\n`;
    codigo += `        ACCION: almuerzo_equilibrado;\n`;
    codigo += `        ACCION: cena_ligera;\n`;
    codigo += `    FIN\n`;
  }

  codigo += 'FIN\n';
  _codigoActual = codigo;
  actualizarCodigoGen(codigo);

  setStatus('loading', 'Compilando...');
  clearTimeout(_debounce);
  _debounce = setTimeout(() => compilar(codigo), 350);
}

function actualizarCodigoGen(codigo) {
  if (!codigo) {
    $('codigo-gen-contenido').style.display = 'none';
    $('empty-codigo-gen').style.display = 'flex';
    return;
  }
  $('codigo-gen-pre').textContent = codigo;
  $('codigo-gen-contenido').style.display = 'block';
  $('empty-codigo-gen').style.display = 'none';
}

function copiarCodigo() {
  navigator.clipboard.writeText(_codigoActual).then(() => {
    const btn = document.querySelector('[onclick="copiarCodigo()"]');
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado';
    setTimeout(() => {
      btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copiar';
    }, 1500);
  });
}

function cargarEjemplo() {
  $('f-nombre').value = 'Sofia_Garcia';
  $('f-edad').value = '25';
  $('f-peso').value = '65.5';
  $('f-objetivo').value = 'bajar_grasa';
  document.querySelector('input[name="nivel"][value="intermedio"]').checked = true;
  $('f-dieta').value = 'dieta_proteica';
  $('f-restriccion-custom').value = '';

  document.querySelectorAll('.restricciones-grid input[type=checkbox]').forEach(el => {
    el.checked = ['lumbar', 'cardio', 'fuerza'].includes(el.value);
  });
  generarCodigo();
}

function limpiarFormulario() {
  ['f-nombre', 'f-edad', 'f-peso', 'f-restriccion-custom'].forEach(id => { if ($(id)) $(id).value = ''; });
  $('f-objetivo').value = '';
  $('f-dieta').value = '';
  document.querySelectorAll('input[type=checkbox]').forEach(el => { el.checked = false; });
  document.querySelector('input[name="nivel"][value="intermedio"]').checked = true;
  _codigoActual = '';
  actualizarCodigoGen('');
  limpiarResultados();
  setStatus('idle', 'Esperando...');
}

function onEditorInput() {
  sincronizarLineas();
  const codigo = $('editor').value.trim();
  _codigoActual = codigo;
  if (!codigo) {
    limpiarResultados();
    setStatus('idle', 'Esperando...');
    return;
  }
  setStatus('loading', 'Compilando...');
  clearTimeout(_debounce);
  _debounce = setTimeout(() => compilar(codigo), 450);
}

function sincronizarLineas() {
  const n = ($('editor').value.match(/\n/g) || []).length + 1;
  $('line-numbers').textContent = Array.from({ length: n }, (_, i) => i + 1).join('\n');
}

function sincronizarScroll() {
  $('line-numbers').scrollTop = $('editor').scrollTop;
}

function cargarEjemploEditor(tipo) {
  $('editor').value = EJEMPLOS_EDITOR[tipo] || '';
  sincronizarLineas();
  onEditorInput();
}

function limpiarEditor() {
  $('editor').value = '';
  _codigoActual = '';
  sincronizarLineas();
  limpiarResultados();
  setStatus('idle', 'Esperando...');
}

async function compilar(codigo) {
  if (!codigo.trim()) {
    limpiarResultados();
    setStatus('idle', 'Esperando...');
    return;
  }

  startPhaseAnimation(false);
  try {
    const r = await fetch('/compilar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo, generar: false })
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    renderTodo(await r.json());
  } catch (e) {
    clearPhaseTimers();
    setPhaseDisplay('lexica', 'failed', 'Sin conexión');
    setStatus('error', 'Sin conexión al servidor');
  }
}

async function generarPlan() {
  const codigo = _modoActual === 'formulario' ? _codigoActual : $('editor').value.trim();
  if (!codigo) {
    alert('Completa el formulario o escribe código primero.');
    return;
  }
  if (!_semOk) {
    alert('El análisis semántico debe ser exitoso antes de generar el plan.');
    return;
  }

  const btn = _modoActual === 'formulario' ? $('btn-generar') : document.querySelector('.btn-generar-small');
  const btnHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generando...';
  }

  mostrarResultado('plan');
  $('empty-plan').style.display = 'none';
  $('plan-listo').style.display = 'block';
  $('plan-resultado').innerHTML = `
    <div class="loading-plan">
      <span class="spinner"><i class="fa-solid fa-circle-notch"></i></span>
      <p>Gemini está generando el plan clínico...</p>
      <p style="font-size:11px;margin-top:6px;color:#9CA3AF">Puede tomar 10-20 segundos</p>
    </div>`;

  startPhaseAnimation(true);
  try {
    const r = await fetch('/compilar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo, generar: true })
    });
    const data = await r.json();
    if (data.plan_clinico) {
      renderTodo(data, true);
      renderPlan(data.plan_clinico, data.prompt_generado, data.modelo_usado, data.advertencia);
      const esDemo = data.modelo_usado === 'DEMO';
      setStatus(esDemo ? 'warning' : 'ok', esDemo ? 'Modo Demo' : 'Plan generado con ' + data.modelo_usado);
    } else {
      finishPhaseFromData(data, true);
      $('plan-resultado').innerHTML = `<div class="error-sint-msg">${esc(data.resumen?.mensaje || 'No se pudo generar el plan')}</div>`;
    }
  } catch (e) {
    clearPhaseTimers();
    setPhaseDisplay('generacion', 'failed', 'Falló en');
    $('plan-resultado').innerHTML = `<div class="error-sint-msg">Error de conexión: ${esc(e.message)}</div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = btnHtml;
    }
  }
}

function renderTodo(data, includeGeneration = false) {
  const { tokens, errores_lexicos, arbol_texto, tabla_simbolos, error_sintactico, error_semantico, resumen } = data;
  const totalErr = (errores_lexicos || []).length + (error_sintactico ? 1 : 0) + (error_semantico ? 1 : 0);
  const fase = resumen?.fase_exitosa || '-';
  const exitoso = Boolean(resumen?.exitoso || fase === 'semantica');

  setStatValue('stat-tokens', (tokens || []).length);
  setStatValue('stat-errores', totalErr);
  $('stat-estado').textContent = exitoso ? 'Válido' : 'Error';
  $('stat-err-icon').className = totalErr > 0 ? 'stat-icon red' : 'stat-icon green';
  $('stat-estado-icon').className = exitoso ? 'stat-icon green' : 'stat-icon red';

  _semOk = exitoso;

  const tbody = $('token-body');
  tbody.innerHTML = '';
  (tokens || []).forEach((t, i) => {
    const tr = document.createElement('tr');
    tr.style.animationDelay = Math.min(i * 5, 150) + 'ms';
    tr.innerHTML = `<td style="color:var(--muted);font-size:11px">${i + 1}</td>
      <td><code class="lexema-code">${esc(t.lexema)}</code></td>
      <td><span class="badge ${esc(t.categoria || '')}">${esc(t.tipo)}</span></td>
      <td>${esc(t.linea)}</td><td>${esc(t.columna)}</td>`;
    tbody.appendChild(tr);
  });
  $('token-table').style.display = tokens && tokens.length ? 'table' : 'none';
  $('empty-tokens').style.display = tokens && tokens.length ? 'none' : 'flex';

  if (arbol_texto) {
    $('arbol-pre').textContent = 'Cadena aceptada\n\nÁrbol sintáctico:\n\n' + arbol_texto;
    $('arbol-pre').style.display = 'block';
    $('empty-arbol').style.display = 'none';
  } else {
    $('arbol-pre').style.display = 'none';
    $('empty-arbol').style.display = 'flex';
  }

  if (tabla_simbolos) {
    renderTabla(tabla_simbolos);
    $('tabla-contenido').style.display = 'block';
    $('empty-tabla').style.display = 'none';
    if (!$('plan-resultado').innerHTML.trim()) {
      $('empty-plan').style.display = 'flex';
      $('plan-listo').style.display = 'none';
    }
  } else {
    $('tabla-contenido').style.display = 'none';
    $('empty-tabla').style.display = 'flex';
    $('empty-plan').style.display = 'flex';
    $('plan-listo').style.display = 'none';
    $('plan-resultado').innerHTML = '';
  }

  renderErrLex(errores_lexicos || []);
  renderErrSint(error_sintactico);
  renderErrSem(error_semantico);

  if (exitoso) setStatus('ok', 'Listo para generar plan');
  else if ((errores_lexicos || []).length) setStatus('error', 'Error léxico');
  else if (error_sintactico) setStatus('warning', 'Error sintáctico');
  else if (error_semantico) setStatus('warning', 'Error semántico');

  finishPhaseFromData(data, includeGeneration);
}

function renderTabla(tabla) {
  const div = $('tabla-contenido');
  div.innerHTML = '';
  if (tabla.paciente) {
    const p = tabla.paciente;
    div.innerHTML += `<div class="ts-seccion"><div class="ts-titulo">Entidad Paciente</div>
      <div class="ts-card">
        <div class="ts-nombre"><i class="fa-solid fa-user"></i>${esc(p.identificador)}</div>
        ${p.edad ? `<div class="ts-prop">Edad: <span>${esc(p.edad)} años</span></div>` : ''}
        ${p.peso ? `<div class="ts-prop">Peso: <span>${esc(p.peso)} kg</span></div>` : ''}
        ${p.objetivo ? `<div class="ts-prop">Objetivo: <span>${esc(p.objetivo)}</span></div>` : ''}
        ${p.restricciones && p.restricciones.length ? `<div class="ts-prop">Restricciones: <span>${esc(p.restricciones.join(', '))}</span></div>` : ''}
      </div></div>`;
  }

  if (tabla.bloques && tabla.bloques.length) {
    let html = '<div class="ts-seccion"><div class="ts-titulo">Bloques declarados</div>';
    tabla.bloques.forEach(b => {
      html += `<div class="ts-bloque"><span class="ts-bloque-tipo ${b.tipo === 'DIETA' ? 'dieta' : ''}">${esc(b.tipo)}</span>
        <div class="ts-nombre">${esc(b.nombre)}</div>
        ${(b.acciones || []).map(a => `<div class="ts-accion"><i class="fa-solid fa-angle-right"></i> ${esc(a)}</div>`).join('')}
      </div>`;
    });
    div.innerHTML += html + '</div>';
  }
}

function renderPlan(plan, prompt, modelo, advertencia) {
  const pc = plan.plan_clinico || plan;
  const esDemo = modelo === 'DEMO';
  let html = `<div class="banner-demo ${esDemo ? 'warning' : 'ok'}">
    <span><i class="fa-solid ${esDemo ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i></span>
    <span>${esDemo ? `Modo Demo - Gemini no disponible (${esc(advertencia || 'cuota agotada')}). Plan generado localmente con datos reales.` : `Plan generado con ${esc(modelo)}`}</span>
  </div>
  <div class="plan-header"><h2><i class="fa-solid fa-notes-medical"></i> Plan Clínico - ${esc(pc.paciente || '')}</h2>
    <p>${esc(pc.objetivo_principal || '')} · ${esc(pc.proxima_revision || '')}</p></div>`;

  if (pc.rutinas && pc.rutinas.length) {
    html += '<div class="plan-seccion"><div class="plan-seccion-titulo"><i class="fa-solid fa-dumbbell"></i> Rutinas</div>';
    pc.rutinas.forEach(r => {
      html += `<div class="plan-bloque"><div class="plan-bloque-header">${esc(r.nombre)}<span>${esc(r.dias_por_semana || '?')} días/sem · ${esc(r.duracion_semanas || '?')} sem</span></div>`;
      (r.ejercicios || []).forEach(e => {
        html += `<div class="ejercicio-row"><span>${esc(e.nombre)}</span>
          <span class="chip">${esc(e.series || '?')} series</span>
          <span class="chip">${esc(e.repeticiones || '?')}</span>
          <span class="chip"><i class="fa-regular fa-clock"></i> ${esc(e.descanso || '?')}</span></div>`;
      });
      if (r.advertencias && r.advertencias.length) {
        html += `<div style="padding:8px 14px;font-size:12px;color:var(--amber);background:var(--amber-bg)"><i class="fa-solid fa-triangle-exclamation"></i> ${esc(r.advertencias.join(' · '))}</div>`;
      }
      html += '</div>';
    });
    html += '</div>';
  }

  if (pc.dietas && pc.dietas.length) {
    html += '<div class="plan-seccion"><div class="plan-seccion-titulo"><i class="fa-solid fa-bowl-food"></i> Plan Nutricional</div>';
    pc.dietas.forEach(d => {
      html += `<div class="plan-bloque"><div class="plan-bloque-header">${esc(d.nombre)}<span>~${esc(d.calorias_diarias || '?')} kcal/día</span></div>`;
      (d.comidas || []).forEach(c => {
        html += `<div class="comida-row"><span><strong>${esc(c.momento)}</strong> - ${esc(c.descripcion)}</span>
          <span class="chip">${esc(c.calorias_aprox || '?')} kcal</span></div>`;
      });
      html += '</div>';
    });
    html += '</div>';
  }

  if (pc.observaciones_clinicas) {
    html += `<div class="plan-seccion"><div class="plan-seccion-titulo"><i class="fa-regular fa-clipboard"></i> Observaciones</div><div class="obs-box">${esc(pc.observaciones_clinicas)}</div></div>`;
  }

  if (prompt) {
    html += `<div class="plan-seccion"><div class="plan-seccion-titulo"><i class="fa-solid fa-magnifying-glass"></i> Prompt generado (Fase 4)</div><div class="prompt-box">${esc(prompt)}</div></div>`;
  }

  $('plan-resultado').innerHTML = html;
}

function renderErrLex(errores) {
  if (errores.length) {
    const eb = $('body-lex');
    eb.innerHTML = '';
    errores.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><code class="lexema-code" style="color:var(--red)">${esc(e.lexema)}</code></td>
        <td>${esc(e.linea)}</td><td>${esc(e.columna)}</td><td>${esc(e.mensaje)}</td>`;
      eb.appendChild(tr);
    });
    $('cnt-lex').textContent = errores.length + ' error' + (errores.length !== 1 ? 'es' : '');
    $('error-lex').style.display = 'block';
  } else {
    $('error-lex').style.display = 'none';
  }
}

function renderErrSint(e) {
  if (e) {
    $('body-sint').innerHTML = `<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Esperaba: <strong>${esc(e.esperado)}</strong> · Encontró: <code>${esc(e.encontrado)}</code> · L${esc(e.linea)}:C${esc(e.columna)}</div>`;
    $('error-sint').style.display = 'block';
  } else {
    $('error-sint').style.display = 'none';
  }
}

function renderErrSem(e) {
  if (e) {
    $('cnt-sem').textContent = e.codigo || 'SEM';
    $('body-sem').innerHTML = `<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Código: <strong>${esc(e.codigo)}</strong>${e.linea ? ' · Línea ' + esc(e.linea) : ''}</div>`;
    $('error-sem').style.display = 'block';
  } else {
    $('error-sem').style.display = 'none';
  }
}

function limpiarResultados() {
  $('token-body').innerHTML = '';
  $('token-table').style.display = 'none';
  $('empty-tokens').style.display = 'flex';
  $('arbol-pre').style.display = 'none';
  $('empty-arbol').style.display = 'flex';
  $('tabla-contenido').style.display = 'none';
  $('empty-tabla').style.display = 'flex';
  $('empty-plan').style.display = 'flex';
  $('plan-listo').style.display = 'none';
  $('plan-resultado').innerHTML = '';
  $('error-lex').style.display = $('error-sint').style.display = $('error-sem').style.display = 'none';
  $('stat-tokens').textContent = $('stat-errores').textContent = '0';
  $('stat-estado').textContent = '-';
  $('stat-err-icon').className = 'stat-icon';
  $('stat-estado-icon').className = 'stat-icon';
  resetPhaseDisplay();
  _lastTokenCount = 0;
  _semOk = false;
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    const codigo = _modoActual === 'formulario' ? _codigoActual : $('editor').value.trim();
    clearTimeout(_debounce);
    compilar(codigo);
  }
});

mostrarResultado('codigo-gen');
