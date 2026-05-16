/* app.js — Compilador de Nutrias — Modo Caso de Uso */

// ── Estado ────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
let _modoActual   = 'formulario';
let _tabActual    = 'codigo-gen';
let _codigoActual = '';
let _debounce     = null;
let _semOk        = false;

// ── Ejemplos predefinidos ─────────────────────────────────────
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

// ── Modo: Formulario / Editor ─────────────────────────────────
function setModo(modo) {
  _modoActual = modo;
  const esForm = modo === 'formulario';

  $('modo-formulario').style.display = esForm ? 'block' : 'none';
  $('modo-codigo').style.display     = esForm ? 'none'  : 'flex';
  $('modo-codigo').style.flexDirection = 'column';
  $('modo-codigo').style.height = '100%';

  $('nav-formulario').classList.toggle('active', esForm);
  $('nav-codigo').classList.toggle('active', !esForm);

  $('page-title').textContent = esForm
    ? 'Modo Fácil — Formulario de Paciente'
    : 'Modo Experto — Editor de Código .nut';

  // Mostrar código generado cuando cambia a formulario
  if (esForm) mostrarResultado('codigo-gen');
}

// ── Tabs resultados ───────────────────────────────────────────
function mostrarResultado(tab) {
  _tabActual = tab;
  const tabs = ['codigo-gen','tokens','arbol','tabla','plan'];
  tabs.forEach(t => {
    const p = $('panel-'+t);
    const b = $('tab-'+t);
    if (p) p.style.display = t===tab ? 'block' : 'none';
    if (b) b.classList.toggle('active', t===tab);
  });
}

// ── Status ────────────────────────────────────────────────────
function setStatus(tipo, texto) {
  $('status-dot').className = 'status-dot ' + (tipo==='idle'?'':tipo);
  $('status-text').textContent = texto;
}

// ── GENERADOR DE CÓDIGO desde el formulario ───────────────────
function generarCodigo() {
  const nombre   = ($('f-nombre').value||'').trim().replace(/\s+/g,'_');
  const edad     = $('f-edad').value;
  const peso     = $('f-peso').value;
  const objetivo = $('f-objetivo').value;
  const nivel    = document.querySelector('input[name="nivel"]:checked')?.value || 'intermedio';
  const dieta    = $('f-dieta').value;
  const custom   = ($('f-restriccion-custom').value||'').trim().replace(/\s+/g,'_');

  // Restricciones seleccionadas
  const restricciones = [...document.querySelectorAll('.restricciones-grid input[type=checkbox]:checked')]
    .filter(el => el.closest('.form-section:nth-of-type(3)') || true)
    .map(el => el.value)
    .filter(v => ['lumbar','rodilla','hombro','presion_alta','diabetes','cervical'].includes(v));
  if (custom) restricciones.push(custom);

  // Tipos de ejercicio seleccionados
  const ejercicios = [...document.querySelectorAll('.restricciones-grid input[type=checkbox]:checked')]
    .map(el => el.value)
    .filter(v => ['cardio','fuerza','flexibilidad','funcional','yoga','natacion'].includes(v));

  if (!nombre) { _codigoActual=''; actualizarCodigoGen(''); return; }

  let codigo = 'INICIO\n';

  // Bloque paciente
  codigo += `    PACIENTE: ${nombre};\n`;
  if (edad)     codigo += `    EDAD: ${edad};\n`;
  if (peso)     codigo += `    PESO: ${peso};\n`;
  restricciones.forEach(r => { codigo += `    RESTRICCION: <${r}>;\n`; });
  if (objetivo) codigo += `    OBJETIVO: ${objetivo};\n`;
  codigo += '\n';

  // Bloque rutina
  if (ejercicios.length > 0) {
    const nombreRutina = `rutina_${nivel}`;
    codigo += `    RUTINA: ${nombreRutina};\n`;
    ejercicios.forEach(e => { codigo += `        ACCION: ${e};\n`; });
    codigo += `    FIN\n\n`;
    codigo += `    IMPRIMIR ${nombreRutina};\n`;
  }

  // Bloque dieta
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

  // Compilar automáticamente
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
    btn.textContent = '✓ Copiado';
    setTimeout(() => btn.textContent = '📋 Copiar', 1500);
  });
}

// ── Formulario helpers ────────────────────────────────────────
function cargarEjemplo() {
  $('f-nombre').value  = 'Sofia_Garcia';
  $('f-edad').value   = '25';
  $('f-peso').value   = '65.5';
  $('f-objetivo').value = 'bajar_grasa';
  document.querySelector('input[name="nivel"][value="intermedio"]').checked = true;
  $('f-dieta').value  = 'dieta_proteica';
  // Restricciones
  document.querySelectorAll('.restricciones-grid input[type=checkbox]').forEach(el => {
    el.checked = el.value === 'lumbar';
  });
  // Ejercicios
  document.querySelectorAll('.restricciones-grid input[type=checkbox]').forEach(el => {
    if (['cardio','fuerza'].includes(el.value)) el.checked = true;
  });
  generarCodigo();
}

function limpiarFormulario() {
  ['f-nombre','f-edad','f-peso','f-restriccion-custom'].forEach(id => { if ($(id)) $(id).value=''; });
  $('f-objetivo').value = '';
  $('f-dieta').value = '';
  document.querySelectorAll('input[type=checkbox]').forEach(el => el.checked=false);
  document.querySelector('input[name="nivel"][value="intermedio"]').checked = true;
  _codigoActual = '';
  actualizarCodigoGen('');
  limpiarResultados();
  setStatus('idle','Esperando...');
}

// ── Editor (Modo Experto) ─────────────────────────────────────
function onEditorInput() {
  sincronizarLineas();
  const codigo = $('editor').value.trim();
  _codigoActual = codigo;
  setStatus('loading','Compilando...');
  clearTimeout(_debounce);
  _debounce = setTimeout(() => compilar(codigo), 450);
}

function sincronizarLineas() {
  const n = ($('editor').value.match(/\n/g)||[]).length+1;
  $('line-numbers').textContent = Array.from({length:n},(_,i)=>i+1).join('\n');
}
function sincronizarScroll() { $('line-numbers').scrollTop = $('editor').scrollTop; }

function cargarEjemploEditor(tipo) {
  $('editor').value = EJEMPLOS_EDITOR[tipo]||'';
  sincronizarLineas();
  onEditorInput();
}
function limpiarEditor() {
  $('editor').value=''; sincronizarLineas(); limpiarResultados(); setStatus('idle','Esperando...');
}

// ── Compilador ────────────────────────────────────────────────
async function compilar(codigo) {
  if (!codigo.trim()) { limpiarResultados(); setStatus('idle','Esperando...'); return; }
  try {
    const r = await fetch('/compilar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo, generar:false})
    });
    if (!r.ok) throw new Error('HTTP '+r.status);
    renderTodo(await r.json());
  } catch(e) { setStatus('error','Sin conexión al servidor'); }
}

async function generarPlan() {
  const codigo = _modoActual==='formulario' ? _codigoActual : $('editor').value.trim();
  if (!codigo) { alert('Completa el formulario o escribe código primero.'); return; }
  if (!_semOk) { alert('El análisis semántico debe ser exitoso antes de generar el plan.'); return; }

  const btn = $('btn-generar');
  if (btn) { btn.disabled=true; btn.textContent='⏳ Generando...'; }

  mostrarResultado('plan');
  $('empty-plan').style.display   = 'none';
  $('plan-listo').style.display   = 'block';
  $('plan-resultado').innerHTML   = `<div class="loading-plan"><span class="spinner">🤖</span><p>Gemini está generando el plan clínico...</p><p style="font-size:11px;margin-top:6px;color:#9CA3AF">Puede tomar 10-20 segundos</p></div>`;

  try {
    const r = await fetch('/compilar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo, generar:true})
    });
    const data = await r.json();
    if (data.plan_clinico) {
      renderPlan(data.plan_clinico, data.prompt_generado, data.modelo_usado, data.advertencia);
      const esDemo = data.modelo_usado==='DEMO';
      setStatus(esDemo?'warning':'ok', esDemo?'⚠ Modo Demo':'✓ Plan generado con '+data.modelo_usado);
    } else {
      $('plan-resultado').innerHTML = `<div class="error-sint-msg">${esc(data.resumen.mensaje)}</div>`;
    }
  } catch(e) {
    $('plan-resultado').innerHTML = `<div class="error-sint-msg">Error de conexión: ${e.message}</div>`;
  } finally {
    if (btn) { btn.disabled=false; btn.textContent='🤖 Generar Plan Clínico con IA'; }
  }
}

// ── Render ────────────────────────────────────────────────────
function renderTodo(data) {
  const {tokens,errores_lexicos,arbol_texto,tabla_simbolos,error_sintactico,error_semantico,resumen} = data;
  const totalErr = (errores_lexicos||[]).length + (error_sintactico?1:0) + (error_semantico?1:0);

  $('stat-tokens').textContent  = (tokens||[]).length;
  $('stat-fase').textContent    = resumen.fase_exitosa||'—';
  $('stat-errores').textContent = totalErr;
  $('stat-estado').textContent  = resumen.exitoso ? 'Válido' : 'Error';
  $('stat-err-icon').className  = totalErr>0 ? 'stat-icon red' : 'stat-icon green';
  $('stat-estado-icon').className = resumen.exitoso ? 'stat-icon green' : 'stat-icon red';

  _semOk = resumen.exitoso || resumen.fase_exitosa==='semantica';

  // Tokens
  const tbody=$('token-body'); tbody.innerHTML='';
  (tokens||[]).forEach((t,i)=>{
    const tr=document.createElement('tr');
    tr.style.animationDelay=Math.min(i*5,150)+'ms';
    tr.innerHTML=`<td style="color:var(--muted);font-size:11px">${i+1}</td>
      <td><code class="lexema-code">${esc(t.lexema)}</code></td>
      <td><span class="badge ${t.categoria}">${t.tipo}</span></td>
      <td>${t.linea}</td><td>${t.columna}</td>`;
    tbody.appendChild(tr);
  });
  $('token-table').style.display = tokens&&tokens.length?'table':'none';
  $('empty-tokens').style.display = tokens&&tokens.length?'none':'flex';

  // Árbol
  if (arbol_texto) {
    $('arbol-pre').textContent='Cadena aceptada\n\nÁrbol sintáctico:\n\n'+arbol_texto;
    $('arbol-pre').style.display='block'; $('empty-arbol').style.display='none';
  } else {
    $('arbol-pre').style.display='none'; $('empty-arbol').style.display='flex';
  }

  // Tabla símbolos
  if (tabla_simbolos) {
    renderTabla(tabla_simbolos);
    $('tabla-contenido').style.display='block'; $('empty-tabla').style.display='none';
    $('empty-plan').style.display='none'; $('plan-listo').style.display='block';
  } else {
    $('tabla-contenido').style.display='none'; $('empty-tabla').style.display='flex';
    $('empty-plan').style.display='flex'; $('plan-listo').style.display='none';
  }

  // Errores
  renderErrLex(errores_lexicos||[]);
  renderErrSint(error_sintactico);
  renderErrSem(error_semantico);

  // Status
  if (resumen.exitoso || resumen.fase_exitosa==='semantica')
    setStatus('ok','✓ Listo para generar plan');
  else if ((errores_lexicos||[]).length) setStatus('error','Error léxico');
  else if (error_sintactico) setStatus('warning','Error sintáctico');
  else if (error_semantico)  setStatus('warning','Error semántico');
}

function renderTabla(tabla) {
  const div=$('tabla-contenido'); div.innerHTML='';
  if (tabla.paciente) {
    const p=tabla.paciente;
    div.innerHTML+=`<div class="ts-seccion"><div class="ts-titulo">Entidad Paciente</div>
      <div class="ts-card">
        <div class="ts-nombre">👤 ${esc(p.identificador)}</div>
        ${p.edad?`<div class="ts-prop">Edad: <span>${p.edad} años</span></div>`:''}
        ${p.peso?`<div class="ts-prop">Peso: <span>${p.peso} kg</span></div>`:''}
        ${p.objetivo?`<div class="ts-prop">Objetivo: <span>${esc(p.objetivo)}</span></div>`:''}
        ${p.restricciones&&p.restricciones.length?`<div class="ts-prop">Restricciones: <span>${p.restricciones.join(', ')}</span></div>`:''}
      </div></div>`;
  }
  if (tabla.bloques&&tabla.bloques.length) {
    let html='<div class="ts-seccion"><div class="ts-titulo">Bloques declarados</div>';
    tabla.bloques.forEach(b=>{
      html+=`<div class="ts-bloque"><span class="ts-bloque-tipo ${b.tipo==='DIETA'?'dieta':''}">${b.tipo}</span>
        <div class="ts-nombre">${esc(b.nombre)}</div>
        ${b.acciones.map(a=>`<div class="ts-accion">• ${esc(a)}</div>`).join('')}
      </div>`;
    });
    div.innerHTML+=html+'</div>';
  }
}

function renderPlan(plan, prompt, modelo, advertencia) {
  const pc=plan.plan_clinico||plan;
  const esDemo=modelo==='DEMO';
  let html=`<div class="banner-demo ${esDemo?'warning':'ok'}">
    <span>${esDemo?'⚠':'✅'}</span>
    <span>${esDemo?`Modo Demo — Gemini no disponible (${esc(advertencia||'cuota agotada')}). Plan generado localmente con datos reales.`:`Plan generado con ${esc(modelo)}`}</span>
  </div>
  <div class="plan-header"><h2>🏥 Plan Clínico — ${esc(pc.paciente||'')}</h2>
    <p>${esc(pc.objetivo_principal||'')} · ${esc(pc.proxima_revision||'')}</p></div>`;

  if (pc.rutinas&&pc.rutinas.length) {
    html+='<div class="plan-seccion"><div class="plan-seccion-titulo">💪 Rutinas</div>';
    pc.rutinas.forEach(r=>{
      html+=`<div class="plan-bloque"><div class="plan-bloque-header">${esc(r.nombre)}<span>${r.dias_por_semana||'?'} días/sem · ${r.duracion_semanas||'?'} sem</span></div>`;
      (r.ejercicios||[]).forEach(e=>{
        html+=`<div class="ejercicio-row"><span>${esc(e.nombre)}</span>
          <span class="chip">${e.series||'?'} series</span>
          <span class="chip">${esc(e.repeticiones||'?')}</span>
          <span class="chip">⏱ ${esc(e.descanso||'?')}</span></div>`;
      });
      if (r.advertencias&&r.advertencias.length)
        html+=`<div style="padding:7px 14px;font-size:11px;color:var(--orange);background:var(--orange-bg)">⚠ ${r.advertencias.join(' · ')}</div>`;
      html+='</div>';
    });
    html+='</div>';
  }

  if (pc.dietas&&pc.dietas.length) {
    html+='<div class="plan-seccion"><div class="plan-seccion-titulo">🥗 Plan Nutricional</div>';
    pc.dietas.forEach(d=>{
      html+=`<div class="plan-bloque"><div class="plan-bloque-header">${esc(d.nombre)}<span>~${d.calorias_diarias||'?'} kcal/día</span></div>`;
      (d.comidas||[]).forEach(c=>{
        html+=`<div class="comida-row"><span><strong>${esc(c.momento)}</strong> — ${esc(c.descripcion)}</span>
          <span class="chip">${c.calorias_aprox||'?'} kcal</span></div>`;
      });
      html+='</div>';
    });
    html+='</div>';
  }

  if (pc.observaciones_clinicas)
    html+=`<div class="plan-seccion"><div class="plan-seccion-titulo">📋 Observaciones</div><div class="obs-box">${esc(pc.observaciones_clinicas)}</div></div>`;

  if (prompt)
    html+=`<div class="plan-seccion"><div class="plan-seccion-titulo">🔍 Prompt generado (Fase 4)</div><div class="prompt-box">${esc(prompt)}</div></div>`;

  $('plan-resultado').innerHTML=html;
}

function renderErrLex(errores) {
  if (errores.length) {
    const eb=$('body-lex'); eb.innerHTML='';
    errores.forEach(e=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td><code class="lexema-code" style="color:var(--red)">${esc(e.lexema)}</code></td>
        <td>${e.linea}</td><td>${e.columna}</td><td>${esc(e.mensaje)}</td>`;
      eb.appendChild(tr);
    });
    $('cnt-lex').textContent=errores.length+' error'+(errores.length!==1?'es':'');
    $('error-lex').style.display='block';
  } else { $('error-lex').style.display='none'; }
}
function renderErrSint(e) {
  if (e) {
    $('body-sint').innerHTML=`<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Esperaba: <strong>${esc(e.esperado)}</strong> · Encontró: <code>${esc(e.encontrado)}</code> · L${e.linea}:C${e.columna}</div>`;
    $('error-sint').style.display='block';
  } else { $('error-sint').style.display='none'; }
}
function renderErrSem(e) {
  if (e) {
    $('cnt-sem').textContent=e.codigo||'SEM';
    $('body-sem').innerHTML=`<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Código: <strong>${esc(e.codigo)}</strong>${e.linea?' · Línea '+e.linea:''}</div>`;
    $('error-sem').style.display='block';
  } else { $('error-sem').style.display='none'; }
}

function limpiarResultados() {
  $('token-body').innerHTML='';
  $('token-table').style.display='none'; $('empty-tokens').style.display='flex';
  $('arbol-pre').style.display='none';  $('empty-arbol').style.display='flex';
  $('tabla-contenido').style.display='none'; $('empty-tabla').style.display='flex';
  $('empty-plan').style.display='flex'; $('plan-listo').style.display='none';
  $('error-lex').style.display=$('error-sint').style.display=$('error-sem').style.display='none';
  $('stat-tokens').textContent=$('stat-errores').textContent='0';
  $('stat-fase').textContent=$('stat-estado').textContent='—';
  _semOk=false;
}

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

document.addEventListener('keydown',e=>{
  if ((e.ctrlKey||e.metaKey)&&e.key==='Enter'){
    e.preventDefault();
    const codigo=_modoActual==='formulario'?_codigoActual:$('editor').value.trim();
    clearTimeout(_debounce); compilar(codigo);
  }
});

// Init
mostrarResultado('codigo-gen');
