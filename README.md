# 🦦 Compilador de Nutrias — Vitally v4
Universidad Rafael Landívar | Compiladores

## Instalación
```bash
pip install flask flask-cors requests
python servidor.py
# → http://localhost:5000
```

## Fases
1. **Léxico** — Tokeniza el código .nut
2. **Sintáctico** — Valida la gramática, construye el árbol
3. **Semántico** — Tabla de símbolos, reglas clínicas
4. **Gemini** — Genera el plan clínico con IA

## Estructura
```
nutrias_final/
├── servidor.py
├── src/
│   ├── tokens.py      ← Definición de tokens
│   ├── lexer.py       ← Fase 1
│   ├── parser.py      ← Fase 2
│   ├── semantico.py   ← Fase 3
│   └── gemini.py      ← Fase 4 (API Key incluida)
├── templates/index.html
└── static/css/
    ├── estilos.css
    └── app.js
```

## Ejemplo válido
```
INICIO
    PACIENTE: Sofia;
    EDAD: 25;
    PESO: 65.5;
    RESTRICCION: <lumbar>;
    OBJETIVO: bajar_grasa;

    RUTINA: rutina_basica;
        ACCION: flexiones * 10;
        ACCION: cardio;
    FIN

    IMPRIMIR rutina_basica;
FIN
```
