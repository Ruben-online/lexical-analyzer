"""
gemini.py — Cliente Gemini + Generador de Prompt
Compilador de Nutrias — Fase 4: Generación de código
"""
import time
import json
import re
import requests
import os
from semantico import TablaSimbolos

# ⚠️ Mejor usar variable de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDKwjber_pugTBkQcusdqtBAj8hf5HS2OE")

# ✅ Modelo estable
MODELOS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",   # si aparece en tu lista
    "gemini-2.0-flash"         # fallback (aunque tenga cuota limitada)
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

    # quitar ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto)
    if m:
        texto = m.group(1).strip()

    # recortar desde primer { hasta último }
    ini = texto.find("{")
    fin = texto.rfind("}")
    if ini != -1 and fin != -1:
        texto = texto[ini:fin+1]

    # limpiar comentarios y comas colgantes
    texto = re.sub(r"//[^\n]*", "", texto)
    texto = re.sub(r",\s*([}\]])", r"\1", texto)

    return texto


def llamar_gemini(prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }

    ultimo_error = ""

    for modelo in MODELOS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_API_KEY}"

        for intento in range(3):  # 🔁 reintentos por modelo
            try:
                resp = requests.post(url, json=payload, timeout=30)

                print("=== GEMINI DEBUG ===")
                print("Modelo:", modelo)
                print("Intento:", intento + 1)
                print("Status:", resp.status_code)
                print("Respuesta:", resp.text[:300])
                print("====================")

                # 🔴 errores recuperables
                if resp.status_code in (503, 429):
                    ultimo_error = f"{modelo} ocupado (intento {intento+1})"
                    time.sleep(2 * (intento + 1))  # backoff
                    continue

                if resp.status_code != 200:
                    ultimo_error = f"HTTP {resp.status_code}: {resp.text}"
                    break

                data = resp.json()

                if "candidates" not in data:
                    ultimo_error = f"Respuesta rara: {data}"
                    break

                parts = data["candidates"][0]["content"]["parts"]

                if not parts or "text" not in parts[0]:
                    ultimo_error = f"Sin texto: {data}"
                    break

                texto = parts[0]["text"]

                # 🔥 doble parseo
                if texto.startswith('"') and texto.endswith('"'):
                    try:
                        texto = json.loads(texto)
                    except:
                        pass

                texto = _limpiar_json(texto)
                plan = json.loads(texto)

                return {
                    "ok": True,
                    "plan": plan,
                    "prompt": prompt,
                    "modelo_usado": modelo
                }

            except Exception as e:
                ultimo_error = str(e)

        # pasa al siguiente modelo si este falla

    return _plan_demo(prompt, ultimo_error)

def _plan_demo(prompt: str, razon: str) -> dict:
    nombre = "Paciente"

    m = re.search(r"PACIENTE:\s*(\w+)", prompt)
    if m:
        nombre = m.group(1)

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

    plan = {
        "plan_clinico": {
            "paciente": nombre,
            "objetivo_principal": "Plan generado por Compilador de Nutrias",
            "nota": f"[MODO DEMO — {razon}]",
            "rutinas": [{
                "nombre": "rutina_personalizada",
                "duracion_semanas": 4,
                "dias_por_semana": 3,
                "ejercicios": [
                    {"nombre": "Caminata en banda", "series": 1, "repeticiones": "30 min", "descanso": "N/A", "observacion": "Cardio de bajo impacto"},
                    {"nombre": "Plancha abdominal", "series": 3, "repeticiones": "20-30 seg", "descanso": "45s", "observacion": "Fortalece core"},
                ],
                "advertencias": advertencias
            }],
            "dietas": [{
                "nombre": "plan_nutricional",
                "calorias_diarias": 1800,
                "comidas": [
                    {"momento": "Desayuno", "descripcion": "Avena y huevos", "calorias_aprox": 450},
                ],
                "alimentos_evitar": ["Azucar", "Frituras"]
            }],
            "observaciones_clinicas": f"Restricciones: {', '.join(restricciones) if restricciones else 'ninguna'}",
            "proxima_revision": "4 semanas"
        }
    }

    return {
        "ok": True,
        "plan": plan,
        "prompt": prompt,
        "modelo_usado": "DEMO",
        "advertencia": razon
    }


def generar_plan(tabla: TablaSimbolos) -> dict:
    prompt = construir_prompt(tabla)
    return llamar_gemini(prompt)