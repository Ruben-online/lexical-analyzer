import json
import os
import re

import requests
from semantico import TablaSimbolos


def _cargar_env_local():
    raiz = os.path.dirname(os.path.dirname(__file__))
    ruta = os.path.join(raiz, ".env")
    if not os.path.exists(ruta):
        return

    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ[clave.strip()] = valor.strip().strip('"').strip("'")


_cargar_env_local()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MODELOS_PREFERIDOS = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]
MODELOS_PREFERIDOS = [m for m in MODELOS_PREFERIDOS if m]


def _log(mensaje):
    print(f"[Gemini] {mensaje}", flush=True)


def _key_resumen():
    if not GEMINI_API_KEY:
        return "sin key"
    return f"{GEMINI_API_KEY[:6]}...{GEMINI_API_KEY[-4:]}"


def construir_prompt(tabla: TablaSimbolos):
    p = tabla.paciente
    rutinas = [b for b in tabla.bloques if b.tipo == "RUTINA"]
    dietas = [b for b in tabla.bloques if b.tipo == "DIETA"]
    rest = ", ".join(p.restricciones) if p.restricciones else "ninguna"
    rut = "".join(f"\n  - {r.nombre}: {', '.join(r.acciones)}" for r in rutinas) or "ninguna"
    die = "".join(f"\n  - {d.nombre}: {', '.join(d.acciones)}" for d in dietas) or "ninguna"

    return f"""Eres especialista en nutricion y entrenamiento. Genera un plan clinico personalizado.

PACIENTE: {p.nombre}
EDAD: {p.edad or 'no especificada'} anios
PESO: {p.peso or 'no especificado'} kg
OBJETIVO: {p.objetivo or 'no especificado'}
NIVEL: {getattr(p, 'nivel', 'no especificado')}
RESTRICCIONES MEDICAS: {rest}
RUTINAS SOLICITADAS: {rut}
DIETAS SOLICITADAS: {die}

IMPORTANTE: Respeta ESTRICTAMENTE las restricciones medicas. Restriccion lumbar: sin impacto en espalda. Restriccion rodilla: sin saltos ni sentadillas profundas.

Responde SOLO con JSON valido sin markdown. Mantén cada descripcion breve para que el JSON cierre correctamente.

{{"plan_clinico":{{"paciente":"{p.nombre}","objetivo_principal":"...","rutinas":[{{"nombre":"...","duracion_semanas":4,"dias_por_semana":3,"ejercicios":[{{"nombre":"...","series":3,"repeticiones":"12","descanso":"60s","observacion":"..."}}],"advertencias":["..."]}}],"dietas":[{{"nombre":"...","calorias_diarias":1800,"comidas":[{{"momento":"Desayuno","descripcion":"...","calorias_aprox":400}}],"alimentos_evitar":["..."]}}],"observaciones_clinicas":"...","proxima_revision":"4 semanas"}}}}"""


def _limpiar_json(texto):
    texto = texto.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto)
    if m:
        texto = m.group(1).strip()
    ini = texto.find("{")
    fin = texto.rfind("}")
    if ini != -1 and fin != -1:
        texto = texto[ini : fin + 1]
    texto = re.sub(r"//[^\n]*", "", texto)
    texto = re.sub(r",\s*([}\]])", r"\1", texto)
    return texto


def _error_google(resp):
    try:
        data = resp.json()
        mensaje = data.get("error", {}).get("message")
        if mensaje:
            return mensaje
    except ValueError:
        pass
    return f"HTTP {resp.status_code}"


def _sanear_error(error):
    texto = str(error)
    texto = re.sub(r"key=[^&\s)]+", "key=***", texto)
    texto = re.sub(r"https://generativelanguage\.googleapis\.com/[^\s)]+", "Gemini API", texto)
    return texto


def _modelos_disponibles():
    if not GEMINI_API_KEY:
        _log("No hay GEMINI_API_KEY configurada; se usara modo demo.")
        return []

    try:
        _log(f"Consultando modelos disponibles con key {_key_resumen()}")
        resp = requests.get(
            f"{GEMINI_API_BASE}/models",
            params={"key": GEMINI_API_KEY},
            timeout=12,
        )
        if not resp.ok:
            _log(f"No se pudieron listar modelos: {_error_google(resp)}")
            return []
        modelos = []
        for modelo in resp.json().get("models", []):
            nombre = modelo.get("name", "").replace("models/", "")
            metodos = modelo.get("supportedGenerationMethods", [])
            es_texto = "tts" not in nombre.lower() and "image" not in nombre.lower()
            if nombre and es_texto and "generateContent" in metodos:
                modelos.append(nombre)
        preferidos = [m for m in MODELOS_PREFERIDOS if m in modelos]
        restantes = [m for m in modelos if m not in preferidos and "flash" in m]
        _log(f"Modelos disponibles para generateContent: {', '.join((preferidos + restantes)[:8])}")
        return preferidos + restantes
    except requests.RequestException:
        _log("No se pudo conectar para listar modelos; se probaran modelos preferidos.")
        return []


def _extraer_texto(resp_json):
    candidatos = resp_json.get("candidates") or []
    if not candidatos:
        raise ValueError("Gemini no devolvio candidatos")
    partes = candidatos[0].get("content", {}).get("parts") or []
    textos = [p.get("text", "") for p in partes if p.get("text")]
    if not textos:
        raise ValueError("Gemini no devolvio texto")
    return "\n".join(textos)


def llamar_gemini(prompt):
    if not GEMINI_API_KEY:
        return _plan_demo(prompt, "Falta configurar GEMINI_API_KEY")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    modelos = (_modelos_disponibles() or MODELOS_PREFERIDOS)[:4]
    errores = []

    _log("Enviando prompt a Gemini")
    _log(f"Prompt: {len(prompt)} caracteres")
    _log(f"Modelos a probar: {', '.join(modelos[:8])}")

    for modelo in modelos:
        url = f"{GEMINI_API_BASE}/models/{modelo}:generateContent"
        try:
            _log(f"Probando modelo: {modelo}")
            resp = requests.post(
                url,
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=35,
            )
            if not resp.ok:
                ultimo_error = f"{modelo}: {_error_google(resp)}"
                errores.append(ultimo_error)
                _log(f"Fallo {modelo}: {ultimo_error}")
                continue

            texto = _extraer_texto(resp.json())
            _log(f"Respuesta recibida de {modelo}: {len(texto)} caracteres")
            try:
                plan = json.loads(_limpiar_json(texto))
            except json.JSONDecodeError as e:
                ultimo_error = f"{modelo}: JSON invalido ({e})"
                errores.append(ultimo_error)
                _log(f"Fallo parseando JSON de {modelo}: {e}")
                _log(f"Respuesta cruda de {modelo}: {texto[:500]}")
                continue
            return {"ok": True, "plan": plan, "prompt": prompt, "modelo_usado": modelo}
        except json.JSONDecodeError as e:
            ultimo_error = f"{modelo}: JSON invalido ({e})"
            errores.append(ultimo_error)
            _log(f"Fallo parseando JSON de {modelo}: {e}")
        except Exception as e:
            ultimo_error = f"{modelo}: {_sanear_error(e)}"
            errores.append(ultimo_error)
            _log(f"Error con {modelo}: {ultimo_error}")

    resumen_error = " | ".join(errores[-4:]) or "Gemini no disponible"
    _log(f"Gemini no genero plan real. Activando demo: {resumen_error}")
    return _plan_demo(prompt, resumen_error)


def _plan_demo(prompt, razon):
    razon = _sanear_error(razon)
    nombre = "Paciente"
    m = re.search(r"PACIENTE:\s*(\w+)", prompt)
    if m:
        nombre = m.group(1)

    rest = []
    m = re.search(r"RESTRICCIONES MEDICAS:\s*(.+)", prompt)
    if m and "ninguna" not in m.group(1):
        rest = [r.strip() for r in m.group(1).split(",")]

    adv = []
    if any("lumbar" in r for r in rest):
        adv.append("Evitar carga en espalda baja")
    if any("rodilla" in r for r in rest):
        adv.append("Evitar saltos y sentadillas profundas")
    if not adv:
        adv = ["Calentar 10 minutos antes de cada sesion"]

    plan = {
        "plan_clinico": {
            "paciente": nombre,
            "objetivo_principal": "Plan personalizado - Compilador de Nutrias",
            "nota": f"[MODO DEMO - {razon}]",
            "rutinas": [
                {
                    "nombre": "rutina_personalizada",
                    "duracion_semanas": 4,
                    "dias_por_semana": 3,
                    "ejercicios": [
                        {
                            "nombre": "Caminata en banda",
                            "series": 1,
                            "repeticiones": "30 min",
                            "descanso": "N/A",
                            "observacion": "Cardio bajo impacto",
                        },
                        {
                            "nombre": "Plancha abdominal",
                            "series": 3,
                            "repeticiones": "20-30 seg",
                            "descanso": "45s",
                            "observacion": "Core sin carga lumbar",
                        },
                        {
                            "nombre": "Curl de biceps",
                            "series": 3,
                            "repeticiones": "12-15",
                            "descanso": "60s",
                            "observacion": "Fuerza tren superior",
                        },
                    ],
                    "advertencias": adv,
                }
            ],
            "dietas": [
                {
                    "nombre": "plan_nutricional",
                    "calorias_diarias": 1800,
                    "comidas": [
                        {
                            "momento": "Desayuno 7am",
                            "descripcion": "Avena, 2 huevos, fruta",
                            "calorias_aprox": 450,
                        },
                        {
                            "momento": "Almuerzo 12pm",
                            "descripcion": "Pollo a la plancha, arroz integral",
                            "calorias_aprox": 550,
                        },
                        {
                            "momento": "Merienda 3pm",
                            "descripcion": "Yogur griego con almendras",
                            "calorias_aprox": 200,
                        },
                        {
                            "momento": "Cena 7pm",
                            "descripcion": "Salmon, vegetales al vapor",
                            "calorias_aprox": 500,
                        },
                    ],
                    "alimentos_evitar": ["Azucar refinada", "Frituras", "Gaseosas"],
                }
            ],
            "observaciones_clinicas": f"Plan para {nombre}. Restricciones: {', '.join(rest) if rest else 'ninguna'}. Hidratacion 2L diarios.",
            "proxima_revision": "En 4 semanas",
        }
    }
    return {
        "ok": True,
        "plan": plan,
        "prompt": prompt,
        "modelo_usado": "DEMO",
        "advertencia": razon,
    }


def generar_plan(tabla):
    return llamar_gemini(construir_prompt(tabla))
