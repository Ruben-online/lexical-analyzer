"""
gemini.py — Cliente Gemini + Generador de Prompt
Compilador de Nutrias — Fase 4: Generación de código
"""

import json
import re
import requests
from semantico import TablaSimbolos

GEMINI_API_KEY = "AIzaSyD47SnsV5e-j84WIiAS6fND8UEkvUHzF0U"

MODELOS = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
]


def construir_prompt(tabla: TablaSimbolos) -> str:
    p       = tabla.paciente
    rutinas = [b for b in tabla.bloques if b.tipo == "RUTINA"]
    dietas  = [b for b in tabla.bloques if b.tipo == "DIETA"]

    restricciones_txt = ", ".join(p.restricciones) if p.restricciones else "ninguna"
    rutinas_txt = "".join(f"\n  - {r.nombre}: {', '.join(r.acciones)}" for r in rutinas) or "ninguna"
    dietas_txt  = "".join(f"\n  - {d.nombre}: {', '.join(d.acciones)}" for d in dietas)  or "ninguna"

    return f"""Eres especialista en nutricion y entrenamiento. Genera un plan clinico.

PACIENTE: {p.nombre}
EDAD: {p.edad or 'no especificada'} anios
PESO: {p.peso or 'no especificado'} kg
OBJETIVO: {p.objetivo or 'no especificado'}
RESTRICCIONES: {restricciones_txt}
RUTINAS: {rutinas_txt}
DIETAS: {dietas_txt}

IMPORTANTE: Respeta restricciones medicas. Restriccion lumbar: sin impacto en espalda.

Responde SOLO con JSON valido sin markdown ni comentarios:

{{"plan_clinico":{{"paciente":"{p.nombre}","objetivo_principal":"...","rutinas":[{{"nombre":"rutina_1","duracion_semanas":4,"dias_por_semana":3,"ejercicios":[{{"nombre":"...","series":3,"repeticiones":"12","descanso":"60s","observacion":"..."}}],"advertencias":["..."]}}],"dietas":[{{"nombre":"dieta_1","calorias_diarias":1800,"comidas":[{{"momento":"Desayuno","descripcion":"...","calorias_aprox":450}}],"alimentos_evitar":["azucar"]}}],"observaciones_clinicas":"...","proxima_revision":"4 semanas"}}}}"""


def _limpiar_json(texto: str) -> str:
    texto = texto.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto)
    if m:
        texto = m.group(1).strip()
    ini = texto.find("{")
    fin = texto.rfind("}")
    if ini != -1 and fin != -1:
        texto = texto[ini:fin+1]
    texto = re.sub(r"//[^\n]*", "", texto)
    texto = re.sub(r",\s*([}\]])", r"\1", texto)
    return texto


def llamar_gemini(prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
    }
    ultimo_error = ""
    for modelo in MODELOS:
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{modelo}:generateContent?key={GEMINI_API_KEY}")
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code in (429, 404, 403):
                ultimo_error = f"HTTP {resp.status_code} en {modelo}"
                continue
            resp.raise_for_status()
            data  = resp.json()
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            texto = _limpiar_json(texto)
            plan  = json.loads(texto)
            return {"ok": True, "plan": plan, "prompt": prompt, "modelo_usado": modelo}
        except json.JSONDecodeError as e:
            ultimo_error = f"JSON invalido en {modelo}: {e}"
            continue
        except Exception as e:
            ultimo_error = str(e)
            continue
    return _plan_demo(prompt, ultimo_error)


def _plan_demo(prompt: str, razon: str) -> dict:
    nombre = "Paciente"
    m = re.search(r"PACIENTE:\s*(\w+)", prompt)
    if m: nombre = m.group(1)

    restricciones = []
    m = re.search(r"RESTRICCIONES:\s*(.+)", prompt)
    if m and "ninguna" not in m.group(1):
        restricciones = [r.strip() for r in m.group(1).split(",")]

    advertencias = []
    if any("lumbar" in r for r in restricciones):
        advertencias.append("Evitar carga en espalda baja e hiperextensiones")
    if any("rodilla" in r for r in restricciones):
        advertencias.append("Evitar sentadillas profundas y saltos")
    if not advertencias:
        advertencias = ["Calentar 10 minutos antes de cada sesion"]

    plan = {"plan_clinico": {
        "paciente": nombre,
        "objetivo_principal": "Plan generado por Compilador de Nutrias",
        "nota": f"[MODO DEMO — {razon}]",
        "rutinas": [{"nombre": "rutina_personalizada", "duracion_semanas": 4,
            "dias_por_semana": 3,
            "ejercicios": [
                {"nombre": "Caminata en banda", "series": 1, "repeticiones": "30 min",
                 "descanso": "N/A", "observacion": "Cardio de bajo impacto"},
                {"nombre": "Plancha abdominal", "series": 3, "repeticiones": "20-30 seg",
                 "descanso": "45s", "observacion": "Fortalece core sin carga lumbar"},
                {"nombre": "Curl de biceps", "series": 3, "repeticiones": "12-15",
                 "descanso": "60s", "observacion": "Fuerza de tren superior"},
                {"nombre": "Remo con mancuerna", "series": 3, "repeticiones": "12",
                 "descanso": "60s", "observacion": "Espalda alta sin impacto lumbar"},
            ], "advertencias": advertencias}],
        "dietas": [{"nombre": "plan_nutricional", "calorias_diarias": 1800,
            "comidas": [
                {"momento": "Desayuno 7am", "descripcion": "Avena, 2 huevos, fruta", "calorias_aprox": 450},
                {"momento": "Almuerzo 12pm", "descripcion": "Pollo a la plancha, arroz integral, ensalada", "calorias_aprox": 550},
                {"momento": "Merienda 3pm", "descripcion": "Yogur griego con almendras", "calorias_aprox": 200},
                {"momento": "Cena 7pm", "descripcion": "Salmon, vegetales al vapor, quinoa", "calorias_aprox": 500},
            ], "alimentos_evitar": ["Azucar refinada", "Frituras", "Gaseosas", "Embutidos"]}],
        "observaciones_clinicas": (
            f"Plan adaptado para {nombre}. "
            f"Restricciones: {', '.join(restricciones) if restricciones else 'ninguna'}. "
            "Hidratacion minima 2 litros diarios. Consultar medico antes de iniciar."
        ),
        "proxima_revision": "En 4 semanas"
    }}
    return {"ok": True, "plan": plan, "prompt": prompt,
            "modelo_usado": "DEMO", "advertencia": razon}


def generar_plan(tabla: TablaSimbolos) -> dict:
    prompt = construir_prompt(tabla)
    return llamar_gemini(prompt)
