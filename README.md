# 🦦 Compilador de Nutrias — Prototipo Web
**Vitally | Universidad Rafael Landívar | Compiladores**

## Requisitos
- Python 3.10+

## Instalación y arranque

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Correr el servidor
python servidor.py

# 3. Abrir en el navegador
http://localhost:5000
```

## Estructura
```
nutrias_proto/
├── servidor.py          ← Flask (Persona 2)
├── requirements.txt
├── src/
│   ├── tokens.py        ← Definición de tokens (Persona 1)
│   └── lexer.py         ← Analizador léxico   (Persona 1)
├── templates/
│   └── index.html       ← Interfaz web         (Persona 3)
├── static/css/
│   ├── estilos.css      ← Estilos Vitally      (Persona 3)
│   └── app.js           ← Lógica frontend      (Persona 3)
└── ejemplos/
    └── valido.nut
```

## Endpoint API
```
POST /analizar
Body: { "codigo": "PACIENTE: Sofia;\nEDAD: 25;" }

Response:
{
  "tokens":  [ { tipo, lexema, linea, columna, categoria } ],
  "errores": [ { lexema, linea, columna, mensaje } ],
  "resumen": { total_tokens, total_errores, exitoso }
}
```

## Tokens del lenguaje
| Token | Patrón |
|---|---|
| Palabras reservadas | PACIENTE EDAD PESO OBJETIVO RESTRICCION ACCION RECETA RUTINA DIETA |
| TK_ID | `[a-zA-Z...][...0-9_]*` |
| TK_ENTERO | `[0-9]+` |
| TK_DECIMAL | `[0-9]+\.[0-9]+` |
| TK_IGUAL | `==` |
| TK_ASIGNACION | `:` |
| TK_SUMA | `+` |
| TK_MULT | `*` |
| TK_FIN_INSTRUC | `;` |
| TK_LT / TK_GT | `< >` |

## Atajo de teclado
`Ctrl + Enter` → Analizar
