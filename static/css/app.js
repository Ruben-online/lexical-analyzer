/* app.js — Compilador de Nutrias v4 — Léxico+Sintáctico+Semántico+Gemini */

const EJEMPLOS = {
  valido: `INICIO
    PACIENTE: Sofia;
    EDAD: 25;
    PESO: 65.5;
    RESTRICCION: <lumbar>;
    OBJETIVO: bajar_grasa;

    SI PESO > 60 ENTONCES
        RUTINA: rutina_intensa;
            ACCION: flexiones * 10;
            ACCION: sentadillas * 15;
            ACCION: proteina + carbohidrato;
        FIN
    FIN

    DIETA: dieta_proteica;
        ACCION: desayuno_avena;
        ACCION: almuerzo_pollo;
    FIN

    IMPRIMIR rutina_intensa;
FIN`,
  errores: `INICIO
    RUTINA: rutina_sin_paciente;
        ACCION: flexiones;
    FIN
    PACIENTE: Carlos;
FIN`
};

const $ = id => document.getElementById(id);
let _debounce = null;
let _tabActual = 'tokens';
let _ultimaTabla = null;

sincronizarLineas();

function onEditorInput() {
  sincronizarLineas();
  setStatus('loading','Analizando...');
  clearTimeout(_debounce);
  _debounce = setTimeout(correrAnalisis, 450);
}

function sincronizarLineas() {
  const n = ($('editor').value.match(/\n/g)||[]).length + 1;
  $('line-numbers').textContent = Array.from({length:n},(_,i)=>i+1).join('\n');
}
function sincronizarScroll() { $('line-numbers').scrollTop = $('editor').scrollTop; }

function cargarEjemplo(tipo) {
  $('editor').value = EJEMPLOS[tipo]||'';
  sincronizarLineas();
  onEditorInput();
}
function limpiar() {
  $('editor').value = '';
  sincronizarLineas();
  limpiarTodo();
  setStatus('idle','Esperando...');
}

// ── Tabs ──────────────────────────────────────────────────────
function mostrarPanel(tab) {
  _tabActual = tab;
  ['tokens','arbol-txt','tabla','plan'].forEach(t => {
    $('panel-'+t).style.display = t===tab ? 'block':'none';
    $('tab-'+t).classList.toggle('active', t===tab);
  });
  $('leyenda-tokens').style.display = tab==='tokens' ? 'flex':'none';
}

function cambiarTab(s) {
  const titulos = {lexico:'Analizador Léxico',sintactico:'Analizador Sintáctico',
                   semantico:'Tabla de Símbolos',plan:'Generación de Plan — Gemini'};
  const subs    = {lexico:'Fase 1',sintactico:'Fase 2',semantico:'Fase 3',plan:'Fase 4 — IA'};
  $('page-title').textContent = titulos[s]||'Compilador de Nutrias';
  $('page-sub').textContent   = subs[s]||'';
  document.querySelectorAll('.nav-item').forEach((el,i)=>
    el.classList.toggle('active', i===['lexico','sintactico','semantico','plan'].indexOf(s)));
  const tabMap = {lexico:'tokens',sintactico:'arbol-txt',semantico:'tabla',plan:'plan'};
  mostrarPanel(tabMap[s]||'tokens');
}

function setStatus(tipo, texto) {
  $('status-dot').className = 'status-dot '+(tipo==='idle'?'':tipo);
  $('status-text').textContent = texto;
}

// ── Análisis principal ─────────────────────────────────────────
async function correrAnalisis() {
  const codigo = $('editor').value.trim();
  if (!codigo) { limpiarTodo(); setStatus('idle','Esperando...'); return; }
  try {
    const r = await fetch('/compilar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo, generar: false})
    });
    if (!r.ok) throw new Error('HTTP '+r.status);
    renderTodo(await r.json());
  } catch(e) { setStatus('error','Sin conexión al servidor'); }
}

// ── Generar plan con Gemini ───────────────────────────────────
async function generarPlan() {
  const codigo = $('editor').value.trim();
  const btn    = $('btn-generar');
  btn.disabled = true;
  btn.textContent = '⏳ Generando con Gemini...';
  $('plan-resultado').innerHTML = `<div class="loading-gemini">
    <div class="spinner"></div>
    <p>Gemini está generando el plan clínico personalizado...</p>
    <p style="font-size:11px;margin-top:8px">Esto puede tomar 5-15 segundos</p>
  </div>`;

  try {
    const r = await fetch('/compilar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo, generar: true})
    });
    const data = await r.json();
    if (data.plan_clinico) {
      renderPlan(data.plan_clinico, data.prompt_generado);
      setStatus('ok','Plan generado ✓');
    } else {
      $('plan-resultado').innerHTML = `<div class="error-sint-msg">${esc(data.resumen.mensaje)}</div>`;
    }
  } catch(e) {
    $('plan-resultado').innerHTML = `<div class="error-sint-msg">Error de conexión: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Generar Plan Clínico con Gemini';
  }
}

// ── Render principal ───────────────────────────────────────────
function renderTodo(data) {
  const {tokens, errores_lexicos, arbol_texto, tabla_simbolos,
         error_sintactico, error_semantico, resumen} = data;

  // stats
  $('stat-tokens').textContent = (tokens||[]).length;
  $('stat-fase').textContent   = resumen.fase_exitosa || '—';
  const totalErr = (errores_lexicos||[]).length + (error_sintactico?1:0) + (error_semantico?1:0);
  $('stat-errores').textContent = totalErr;
  $('stat-estado').textContent  = resumen.exitoso ? 'Válido' : 'Errores';
  $('stat-err-icon').className  = totalErr > 0 ? 'stat-icon red' : 'stat-icon green';
  $('stat-estado-icon').className = resumen.exitoso ? 'stat-icon green' : 'stat-icon red';

  // tokens
  const tbody = $('token-body'); tbody.innerHTML='';
  (tokens||[]).forEach((t,i)=>{
    const tr=document.createElement('tr');
    tr.style.animationDelay=Math.min(i*6,150)+'ms';
    tr.innerHTML=`<td style="color:var(--text-muted);font-size:11px">${i+1}</td>
      <td><code class="lexema-code">${esc(t.lexema)}</code></td>
      <td><span class="badge ${t.categoria}">${t.tipo}</span></td>
      <td>${t.linea}</td><td>${t.columna}</td>`;
    tbody.appendChild(tr);
  });
  $('token-table').style.display = tokens&&tokens.length?'table':'none';
  $('empty-tokens').style.display = tokens&&tokens.length?'none':'flex';

  // árbol
  if (arbol_texto) {
    $('arbol-pre').textContent = 'Cadena aceptada\n\nÁrbol sintáctico:\n\n'+arbol_texto;
    $('arbol-pre').style.display='block'; $('empty-arbol').style.display='none';
  } else {
    $('arbol-pre').style.display='none'; $('empty-arbol').style.display='flex';
  }

  // tabla de símbolos
  _ultimaTabla = tabla_simbolos;
  if (tabla_simbolos) {
    renderTablaSimbolos(tabla_simbolos);
    $('tabla-simbolos-contenido').style.display='block'; $('empty-tabla').style.display='none';
    // habilitar botón de generar
    $('empty-plan').style.display='none'; $('plan-listo').style.display='block';
    $('plan-resultado').innerHTML='';
  } else {
    $('tabla-simbolos-contenido').style.display='none'; $('empty-tabla').style.display='flex';
    $('empty-plan').style.display='flex'; $('plan-listo').style.display='none';
  }

  // errores
  renderErroresLexicos(errores_lexicos||[]);
  renderErrorSintactico(error_sintactico);
  renderErrorSemantico(error_semantico);

  // status
  if (resumen.exitoso)               setStatus('ok',    'Análisis completo ✓');
  else if ((errores_lexicos||[]).length) setStatus('error', 'Error léxico');
  else if (error_sintactico)          setStatus('warning','Error sintáctico');
  else if (error_semantico)           setStatus('warning','Error semántico');
  else                                setStatus('idle',  '...');
}

function renderTablaSimbolos(tabla) {
  const div = $('tabla-simbolos-contenido');
  div.innerHTML = '';
  if (tabla.paciente) {
    const p = tabla.paciente;
    div.innerHTML += `<div class="ts-seccion">
      <div class="ts-titulo">Entidad Paciente</div>
      <div class="ts-card">
        <div class="ts-nombre">👤 ${esc(p.identificador)}</div>
        <div class="ts-prop">Tipo: <span>${p.tipo}</span></div>
        ${p.edad  ? `<div class="ts-prop">Edad: <span>${p.edad} años</span></div>` : ''}
        ${p.peso  ? `<div class="ts-prop">Peso: <span>${p.peso} kg</span></div>` : ''}
        ${p.objetivo ? `<div class="ts-prop">Objetivo: <span>${esc(p.objetivo)}</span></div>` : ''}
        ${p.restricciones&&p.restricciones.length ? `<div class="ts-prop">Restricciones: <span>${p.restricciones.join(', ')}</span></div>` : ''}
        <div class="ts-prop">Declarado en: <span>línea ${p.linea}</span></div>
      </div>
    </div>`;
  }
  if (tabla.bloques && tabla.bloques.length) {
    let html='<div class="ts-seccion"><div class="ts-titulo">Bloques declarados</div>';
    tabla.bloques.forEach(b=>{
      html+=`<div class="ts-bloque">
        <span class="ts-bloque-tipo ${b.tipo==='DIETA'?'dieta':''}">${b.tipo}</span>
        <div class="ts-nombre">${esc(b.nombre)}</div>
        ${b.acciones.map(a=>`<div class="ts-accion">• ${esc(a)}</div>`).join('')}
        <div class="ts-prop" style="margin-top:4px">Línea: <span>${b.linea}</span></div>
      </div>`;
    });
    html+='</div>';
    div.innerHTML+=html;
  }
}

function renderPlan(plan, prompt) {
  const pc = plan.plan_clinico || plan;
  let html = `<div class="plan-header">
    <h2>Plan Clínico — ${esc(pc.paciente||'Paciente')}</h2>
    <p>${esc(pc.objetivo_principal||'')} · Próxima revisión: ${esc(pc.proxima_revision||'')}</p>
  </div>`;

  if (pc.rutinas && pc.rutinas.length) {
    html+='<div class="plan-seccion"><div class="plan-seccion-titulo">💪 Rutinas de Ejercicio</div>';
    pc.rutinas.forEach(r=>{
      html+=`<div class="plan-rutina">
        <div class="plan-bloque-header">${esc(r.nombre)}
          <span class="plan-bloque-meta">${r.dias_por_semana||'?'} días/sem · ${r.duracion_semanas||'?'} semanas</span>
        </div>`;
      (r.ejercicios||[]).forEach(e=>{
        html+=`<div class="ejercicio-row">
          <span class="ejercicio-nombre">${esc(e.nombre)}</span>
          <span class="ejercicio-chip">${e.series||'?'} series</span>
          <span class="ejercicio-chip">${esc(e.repeticiones||'?')}</span>
          <span class="ejercicio-chip">⏱ ${esc(e.descanso||'?')}</span>
        </div>`;
      });
      if (r.advertencias && r.advertencias.length) {
        html+=`<div style="padding:8px 14px;font-size:11px;color:#E65100;background:#FFF3E0">
          ⚠ ${r.advertencias.join(' · ')}</div>`;
      }
      html+='</div>';
    });
    html+='</div>';
  }

  if (pc.dietas && pc.dietas.length) {
    html+='<div class="plan-seccion"><div class="plan-seccion-titulo">🥗 Plan Nutricional</div>';
    pc.dietas.forEach(d=>{
      html+=`<div class="plan-dieta">
        <div class="plan-bloque-header">${esc(d.nombre)}
          <span class="plan-bloque-meta">~${d.calorias_diarias||'?'} kcal/día</span>
        </div>`;
      (d.comidas||[]).forEach(c=>{
        html+=`<div class="comida-row">
          <span><strong>${esc(c.momento)}</strong> — ${esc(c.descripcion)}</span>
          <span class="ejercicio-chip">${c.calorias_aprox||'?'} kcal</span>
        </div>`;
      });
      html+='</div>';
    });
    html+='</div>';
  }

  if (pc.observaciones_clinicas) {
    html+=`<div class="plan-seccion">
      <div class="plan-seccion-titulo">📋 Observaciones Clínicas</div>
      <div class="obs-box">${esc(pc.observaciones_clinicas)}</div>
    </div>`;
  }

  if (prompt) {
    html+=`<div class="plan-seccion">
      <div class="plan-seccion-titulo">Prompt generado</div>
      <div class="prompt-box">${esc(prompt)}</div>
    </div>`;
  }

  $('plan-resultado').innerHTML = html;
}

function renderErroresLexicos(errores) {
  if (errores.length) {
    const eb=$('error-body-lex'); eb.innerHTML='';
    errores.forEach(e=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td><code class="lexema-code" style="color:var(--red)">${esc(e.lexema)}</code></td>
        <td>${e.linea}</td><td>${e.columna}</td><td>${esc(e.mensaje)}</td>`;
      eb.appendChild(tr);
    });
    $('error-count-lex').textContent=errores.length+' error'+(errores.length!==1?'es':'');
    $('error-panel-lex').style.display='block';
  } else { $('error-panel-lex').style.display='none'; }
}

function renderErrorSintactico(e) {
  if (e) {
    $('error-sint-body').innerHTML=`<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Esperaba: <strong>${esc(e.esperado)}</strong> &nbsp;·&nbsp;
      Encontró: <code>${esc(e.encontrado)}</code> &nbsp;·&nbsp; L${e.linea}:C${e.columna}</div>`;
    $('error-panel-sint').style.display='block';
  } else { $('error-panel-sint').style.display='none'; }
}

function renderErrorSemantico(e) {
  if (e) {
    $('error-sem-code').textContent = e.codigo||'Fase 3';
    $('error-sem-body').innerHTML=`<div class="error-sint-msg">${esc(e.mensaje)}</div>
      <div class="error-sint-hint">Código: <strong>${esc(e.codigo)}</strong>
      ${e.linea ? ` &nbsp;·&nbsp; Línea ${e.linea}` : ''}</div>`;
    $('error-panel-sem').style.display='block';
  } else { $('error-panel-sem').style.display='none'; }
}

function limpiarTodo() {
  $('token-body').innerHTML='';
  $('token-table').style.display='none'; $('empty-tokens').style.display='flex';
  $('arbol-pre').style.display='none';  $('empty-arbol').style.display='flex';
  $('tabla-simbolos-contenido').style.display='none'; $('empty-tabla').style.display='flex';
  $('empty-plan').style.display='flex'; $('plan-listo').style.display='none';
  $('plan-resultado').innerHTML='';
  $('error-panel-lex').style.display='none';
  $('error-panel-sint').style.display='none';
  $('error-panel-sem').style.display='none';
  $('stat-tokens').textContent=$('stat-errores').textContent='0';
  $('stat-fase').textContent=$('stat-estado').textContent='—';
  _ultimaTabla=null;
}

function esc(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.addEventListener('keydown',e=>{
  if ((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();clearTimeout(_debounce);correrAnalisis();}
});
