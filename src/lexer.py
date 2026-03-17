"""
lexer.py — Analizador Léxico del Compilador de Nutrias
Vitally — Fase 1

Tokens reconocidos:
  Palabras reservadas : PACIENTE EDAD PESO OBJETIVO RESTRICCION ACCION RECETA RUTINA DIETA
  Identificadores     : [a-zA-ZáéíóúñÁÉÍÓÚÑ][...0-9_]*
  Números             : enteros [0-9]+  |  decimales [0-9]+\.[0-9]+
  Cadenas             : "texto libre"
  Operadores          : :  ==  +  *
  Simbolos            : ;  <  >
  Ignorados           : espacios, comentarios // y /* .. */
  Errores             : cualquier otro caracter o = suelto
"""

import re
from dataclasses import dataclass, asdict
from tokens import TipoToken, PALABRAS_RESERVADAS, categoria_de


# ─────────────────────────────────────────────────
#  Estructuras de datos
# ─────────────────────────────────────────────────

@dataclass
class Token:
    tipo:      str   # nombre del TipoToken
    lexema:    str
    linea:     int
    columna:   int
    categoria: str   # para colorear en frontend

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ErrorLexico:
    lexema:   str
    linea:    int
    columna:  int
    mensaje:  str

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────
#  Especificación de tokens (orden = prioridad)
# ─────────────────────────────────────────────────

_SPEC = [
    # Ignorados primero
    ("_COMENTARIO_ML", r"/\*[\s\S]*?\*/"),
    ("_COMENTARIO_SL", r"//[^\n]*"),
    ("_ESPACIO",       r"[ \t\r\n]+"),

    # Operadores compuestos ANTES que simples
    ("TK_IGUAL",       r"=="),

    # Literales
    ("TK_DECIMAL",     r"\d+\.\d+"),
    ("TK_ENTERO",      r"\d+"),
    ("TK_CADENA",      r'"[^"\n]*"'),           # cadena cerrada
    ("_CADENA_ABIERTA",r'"[^"\n]*$'),            # error: sin cerrar

    # Identificadores / palabras reservadas
    ("TK_ID",          r"[a-zA-ZáéíóúÁÉÍÓÚñÑ][a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]*"),

    # Operadores simples
    ("TK_ASIGNACION",  r":"),
    ("TK_SUMA",        r"\+"),
    ("TK_MULT",        r"\*"),

    # Símbolos
    ("TK_FIN_INSTRUC", r";"),
    ("TK_LT",          r"<"),
    ("TK_GT",          r">"),

    # = suelto → error (no existe en el lenguaje)
    ("_IGUAL_SIMPLE",  r"="),

    # Catch-all → error
    ("TK_ERROR",       r"."),
]

_PATRON = re.compile(
    "|".join(f"(?P<{nombre}>{regex})" for nombre, regex in _SPEC),
    re.UNICODE | re.MULTILINE
)


# ─────────────────────────────────────────────────
#  Lexer
# ─────────────────────────────────────────────────

class Lexer:

    def tokenizar(self, codigo: str) -> tuple[list[Token], list[ErrorLexico]]:
        tokens:  list[Token]      = []
        errores: list[ErrorLexico] = []

        linea   = 1
        col_ini = 0   # índice en `codigo` donde empieza la línea actual

        for m in _PATRON.finditer(codigo):
            nombre = m.lastgroup
            lexema = m.group()
            col    = m.start() - col_ini + 1

            # ── Ignorados ────────────────────────────
            if nombre in ("_ESPACIO", "_COMENTARIO_SL", "_COMENTARIO_ML"):
                saltos = lexema.count("\n")
                if saltos:
                    linea   += saltos
                    ultimo   = lexema.rfind("\n")
                    col_ini  = m.start() + ultimo + 1
                continue

            # ── Errores detectados explícitamente ────
            if nombre == "_CADENA_ABIERTA":
                errores.append(ErrorLexico(
                    lexema  = lexema,
                    linea   = linea,
                    columna = col,
                    mensaje = "Cadena de texto no cerrada (falta '\"')"
                ))
                continue

            if nombre == "_IGUAL_SIMPLE":
                errores.append(ErrorLexico(
                    lexema  = "=",
                    linea   = linea,
                    columna = col,
                    mensaje = "'=' no existe en el lenguaje — ¿quisiste usar ':' para asignar o '==' para comparar?"
                ))
                continue

            if nombre == "TK_ERROR":
                errores.append(ErrorLexico(
                    lexema  = lexema,
                    linea   = linea,
                    columna = col,
                    mensaje = f"Carácter no reconocido: '{lexema}'"
                ))
                continue

            # ── Resolver palabra reservada vs ID ─────
            if nombre == "TK_ID":
                tipo = PALABRAS_RESERVADAS.get(lexema.upper(), TipoToken.TK_ID)
            else:
                tipo = TipoToken[nombre]

            tokens.append(Token(
                tipo      = tipo.value,
                lexema    = lexema,
                linea     = linea,
                columna   = col,
                categoria = categoria_de(tipo)
            ))

        tokens.append(Token(
            tipo="TK_EOF", lexema="EOF",
            linea=linea, columna=-1, categoria="otro"
        ))

        return tokens, errores
