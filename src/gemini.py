"""
gemini.py — Cliente Gemini + Generador de Prompt
Compilador de Nutrias — Fase 4: Generación de código
"""

import json
import requests
from semantico import TablaSimbolos

GEMINI_API_KEY = "AIzaSyD47SnsV5e-j84WIiAS6fND8UEkvUHzF0U"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
    f"?key={GEMINI_API_KEY}"
)


# ─── Generador de prompt ──────────────────────────────────────

def construir_prompt(tabla: TablaSimbolos) -> str:
    """
    Transforma la tabla de símbolos en un prompt estructurado
    para Gemini. Esta es la Fase 4 del compilador: generación
    de código (el 'código' es el prompt).
    """
    p = tabla.paciente
    bloques = tabla.bloques

    rutinas = [b for b in bloques if b.tipo == "RUTINA"]
    dietas  = [b for b in bloques if b.tipo == "DIETA"]

    restricciones_txt = (
        ", ".join(p.restricciones) if p.restricciones
        else "ninguna restricción médica reportada"
    )

    rutinas_txt = ""
    for r in rutinas:
        rutinas_txt += f"\n  - Rutina '{r.nombre}': {', '.join(r.acciones)}"

    dietas_txt = ""
    for d in dietas:
        dietas_txt += f"\n  - Dieta '{d.nombre}': {', '.join(d.acciones)}"

    prompt = f"""Eres un especialista certificado en nutrición clínica y entrenamiento físico.
Tu tarea es generar un plan clínico personalizado y profesional basado en los siguientes datos del paciente.

=== DATOS DEL PACIENTE (validados por compilador) ===
Nombre:              {p.nombre}
Edad:                {p.edad if p.edad else 'no especificada'} años
Peso:                {p.peso if p.peso else 'no especificado'} kg
Objetivo:            {p.objetivo if p.objetivo else 'no especificado'}
Restricciones médicas: {restricciones_txt}

=== BLOQUES SOLICITADOS ===
Rutinas de ejercicio: {rutinas_txt if rutinas_txt else 'ninguna'}
Planes de dieta:      {dietas_txt  if dietas_txt  else 'ninguna'}

=== INSTRUCCIONES ===
- Genera un plan clínico completo, detallado y profesional
- Respeta ESTRICTAMENTE las restricciones médicas al elegir ejercicios
- Adapta la intensidad a la edad y peso del paciente
- Para cada ejercicio incluye: series, repeticiones, tiempo de descanso
- Para la dieta incluye: horario, porciones aproximadas, calorías estimadas
- Agrega observaciones clínicas relevantes
- Si hay restricción lumbar: evita ejercicios de impacto en espalda baja
- Si hay restricción de rodilla: evita sentadillas profundas y saltos

Responde ÚNICAMENTE con un objeto JSON válido con este esquema exacto
(sin markdown, sin texto adicional, solo el JSON):

{{
  "plan_clinico": {{
    "paciente": "{p.nombre}",
    "fecha_generacion": "hoy",
    "objetivo_principal": "...",
    "rutinas": [
      {{
        "nombre": "...",
        "duracion_semanas": 4,
        "dias_por_semana": 3,
        "ejercicios": [
          {{
            "nombre": "...",
            "series": 3,
            "repeticiones": "...",
            "descanso": "60 segundos",
            "observacion": "..."
          }}
        ],
        "advertencias": ["..."]
      }}
    ],
    "dietas": [
      {{
        "nombre": "...",
        "calorias_diarias": 2000,
        "comidas": [
          {{
            "momento": "Desayuno",
            "descripcion": "...",
            "calorias_aprox": 400
          }}
        ],
        "alimentos_evitar": ["..."]
      }}
    ],
    "observaciones_clinicas": "...",
    "proxima_revision": "En 4 semanas"
  }}
}}"""

    return prompt


# ─── Cliente Gemini ───────────────────────────────────────────

def llamar_gemini(prompt: str) -> dict:
    """
    Envía el prompt a la API de Gemini y retorna el plan clínico
    parseado como diccionario Python.
    """
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        }
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Extraer texto de la respuesta
        texto = data["candidates"][0]["content"]["parts"][0]["text"]

        # Limpiar markdown y extraer JSON robusto
        texto = texto.strip()

        # Eliminar bloques ```json ... ``` o ``` ... ```
        if "```" in texto:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto)
            if match:
                texto = match.group(1).strip()

        # Si aún no empieza con { buscar el primer {
        if not texto.startswith("{"):
            idx = texto.find("{")
            if idx != -1:
                texto = texto[idx:]

        # Recortar al último } para eliminar texto sobrante
        idx_fin = texto.rfind("}")
        if idx_fin != -1:
            texto = texto[:idx_fin+1]

        return {"ok": True, "plan": json.loads(texto), "prompt": prompt}
    
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Timeout — Gemini tardó más de 30 segundos"}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Error de conexión: {str(e)}"}
    except (KeyError, IndexError):
        return {"ok": False, "error": "Respuesta inesperada de Gemini"}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Gemini no devolvió JSON válido: {str(e)}",
                "texto_crudo": texto if 'texto' in dir() else ""}


def generar_plan(tabla: TablaSimbolos) -> dict:
    """Función principal: tabla → prompt → Gemini → plan clínico."""
    prompt = construir_prompt(tabla)
    return llamar_gemini(prompt)
