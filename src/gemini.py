import json, re, requests
from semantico import TablaSimbolos

GEMINI_API_KEY = "AIzaSyD47SnsV5e-j84WIiAS6fND8UEkvUHzF0U"
MODELOS = ["gemini-2.5-flash-preview-04-17","gemini-2.0-flash","gemini-2.0-flash-lite","gemini-1.5-flash-latest"]

def construir_prompt(tabla):
    p=tabla.paciente
    rutinas=[b for b in tabla.bloques if b.tipo=="RUTINA"]
    dietas=[b for b in tabla.bloques if b.tipo=="DIETA"]
    rest=", ".join(p.restricciones) if p.restricciones else "ninguna"
    rut="".join(f"\n  - {r.nombre}: {', '.join(r.acciones)}" for r in rutinas) or "ninguna"
    die="".join(f"\n  - {d.nombre}: {', '.join(d.acciones)}" for d in dietas) or "ninguna"
    return f"""Eres especialista en nutricion y entrenamiento. Genera un plan clinico personalizado.

PACIENTE: {p.nombre}
EDAD: {p.edad or 'no especificada'} anios
PESO: {p.peso or 'no especificado'} kg
OBJETIVO: {p.objetivo or 'no especificado'}
NIVEL: {getattr(p,'nivel','no especificado')}
RESTRICCIONES MEDICAS: {rest}
RUTINAS SOLICITADAS: {rut}
DIETAS SOLICITADAS: {die}

IMPORTANTE: Respeta ESTRICTAMENTE las restricciones medicas. Restriccion lumbar: sin impacto en espalda. Restriccion rodilla: sin saltos ni sentadillas profundas.

Responde SOLO con JSON valido sin markdown:

{{"plan_clinico":{{"paciente":"{p.nombre}","objetivo_principal":"...","rutinas":[{{"nombre":"...","duracion_semanas":4,"dias_por_semana":3,"ejercicios":[{{"nombre":"...","series":3,"repeticiones":"12","descanso":"60s","observacion":"..."}}],"advertencias":["..."]}}],"dietas":[{{"nombre":"...","calorias_diarias":1800,"comidas":[{{"momento":"Desayuno","descripcion":"...","calorias_aprox":400}}],"alimentos_evitar":["..."]}}],"observaciones_clinicas":"...","proxima_revision":"4 semanas"}}}}"""

def _limpiar_json(texto):
    texto=texto.strip()
    m=re.search(r"```(?:json)?\s*([\s\S]*?)```",texto)
    if m: texto=m.group(1).strip()
    ini=texto.find("{"); fin=texto.rfind("}")
    if ini!=-1 and fin!=-1: texto=texto[ini:fin+1]
    texto=re.sub(r"//[^\n]*","",texto)
    texto=re.sub(r",\s*([}\]])",r"\1",texto)
    return texto

def llamar_gemini(prompt):
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.3,"maxOutputTokens":2048}}
    ultimo_error=""
    for modelo in MODELOS:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp=requests.post(url,json=payload,timeout=30)
            if resp.status_code in (429,404,403): ultimo_error=f"HTTP {resp.status_code} en {modelo}"; continue
            resp.raise_for_status()
            texto=resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"ok":True,"plan":json.loads(_limpiar_json(texto)),"prompt":prompt,"modelo_usado":modelo}
        except json.JSONDecodeError as e: ultimo_error=f"JSON invalido: {e}"; continue
        except Exception as e: ultimo_error=str(e); continue
    return _plan_demo(prompt,ultimo_error)

def _plan_demo(prompt,razon):
    nombre="Paciente"
    m=re.search(r"PACIENTE:\s*(\w+)",prompt)
    if m: nombre=m.group(1)
    rest=[]
    m=re.search(r"RESTRICCIONES MEDICAS:\s*(.+)",prompt)
    if m and "ninguna" not in m.group(1): rest=[r.strip() for r in m.group(1).split(",")]
    adv=[]
    if any("lumbar" in r for r in rest): adv.append("Evitar carga en espalda baja")
    if any("rodilla" in r for r in rest): adv.append("Evitar saltos y sentadillas profundas")
    if not adv: adv=["Calentar 10 minutos antes de cada sesion"]
    plan={"plan_clinico":{"paciente":nombre,"objetivo_principal":"Plan personalizado - Compilador de Nutrias",
        "nota":f"[MODO DEMO — {razon}]",
        "rutinas":[{"nombre":"rutina_personalizada","duracion_semanas":4,"dias_por_semana":3,
            "ejercicios":[
                {"nombre":"Caminata en banda","series":1,"repeticiones":"30 min","descanso":"N/A","observacion":"Cardio bajo impacto"},
                {"nombre":"Plancha abdominal","series":3,"repeticiones":"20-30 seg","descanso":"45s","observacion":"Core sin carga lumbar"},
                {"nombre":"Curl de biceps","series":3,"repeticiones":"12-15","descanso":"60s","observacion":"Fuerza tren superior"},
            ],"advertencias":adv}],
        "dietas":[{"nombre":"plan_nutricional","calorias_diarias":1800,
            "comidas":[
                {"momento":"Desayuno 7am","descripcion":"Avena, 2 huevos, fruta","calorias_aprox":450},
                {"momento":"Almuerzo 12pm","descripcion":"Pollo a la plancha, arroz integral","calorias_aprox":550},
                {"momento":"Merienda 3pm","descripcion":"Yogur griego con almendras","calorias_aprox":200},
                {"momento":"Cena 7pm","descripcion":"Salmon, vegetales al vapor","calorias_aprox":500},
            ],"alimentos_evitar":["Azucar refinada","Frituras","Gaseosas"]}],
        "observaciones_clinicas":f"Plan para {nombre}. Restricciones: {', '.join(rest) if rest else 'ninguna'}. Hidratacion 2L diarios.",
        "proxima_revision":"En 4 semanas"}}
    return {"ok":True,"plan":plan,"prompt":prompt,"modelo_usado":"DEMO","advertencia":razon}

def generar_plan(tabla): return llamar_gemini(construir_prompt(tabla))
