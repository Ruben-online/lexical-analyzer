import re
from dataclasses import dataclass, asdict
from tokens import TipoToken, PALABRAS_RESERVADAS, categoria_de

#  Estructuras de datos
@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int
    categoria: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ErrorLexico:
    lexema: str
    linea: int
    columna: int
    mensaje: str

    def to_dict(self) -> dict:
        return asdict(self)


#  Especificacion de tokens (orden = prioridad)

_SPEC = [

    # ── 1. Ignorados ─────────────────────────
    ("_COMENTARIO_ML", r"/\*[\s\S]*?\*/"),
    ("_COMENTARIO_SL", r"//[^\n]*"),
    ("_ESPACIO",       r"[ \t\r\n]+"),

    # ── 2. Operadores compuestos (ANTES que simples) ─────
    ("TK_IGUAL",        r"=="),
    ("TK_MAYOR_IGUAL",  r">="),
    ("TK_MENOR_IGUAL",  r"<="),

    # ── 3. ERRORES (alta prioridad) ──────────

    # identificador que empieza con número
    ("_NUM_ID_INVALIDO", r"\d+[a-zA-ZáéíóúÁÉÍÓÚñÑ_]+[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]*"),

    # decimal mal formado (ej: 12.34.56)
    ("_DECIMAL_INVALIDO", r"\d+\.\d+\.\d+"),

    # cadena con salto de línea
    ("_CADENA_SALTO", r'"[^"]*\n[^"]*"'),

    # cadena no cerrada
    ("_CADENA_ABIERTA", r'"[^"\n]*$'),

    # ── 4. Literales válidos ─────────────────
    ("TK_DECIMAL",     r"\d+\.\d+"),
    ("TK_ENTERO",      r"\d+"),
    ("TK_CADENA",      r'"[^"\n]*"'),

    # ── 5. Identificadores ──────────────────
    ("TK_ID", r"[a-zA-ZáéíóúÁÉÍÓÚñÑ][a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]*"),

    # ── 6. Operadores simples ───────────────
    ("TK_ASIGNACION",  r":"),
    ("TK_SUMA",        r"\+"),
    ("TK_MULT",        r"\*"),

    # ── 7. Símbolos ─────────────────────────
    ("TK_FIN_INSTRUC", r";"),
    ("TK_MAYOR",        r">"),
    ("TK_MENOR",        r"<"),
    # LT y GT se reconocen igual que MAYOR/MENOR — el parser decide el contexto

    # ── 8. Error específico ─────────────────
    ("_IGUAL_SIMPLE",  r"="),

    # ── 9. Catch-all ────────────────────────
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
        tokens: list[Token] = []
        errores: list[ErrorLexico] = []

        linea = 1
        col_ini = 0

        for m in _PATRON.finditer(codigo):
            nombre = m.lastgroup
            lexema = m.group()
            col = m.start() - col_ini + 1

            # ── Ignorados ─────────────────────
            if nombre in ("_ESPACIO", "_COMENTARIO_SL", "_COMENTARIO_ML"):
                saltos = lexema.count("\n")
                if saltos:
                    linea += saltos
                    ultimo = lexema.rfind("\n")
                    col_ini = m.start() + ultimo + 1
                continue

            # ── Errores ───────────────────────

            if nombre == "_CADENA_ABIERTA":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    "Cadena de texto no cerrada"
                ))
                continue

            if nombre == "_CADENA_SALTO":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    "Cadena no puede contener saltos de línea"
                ))
                continue

            if nombre == "_NUM_ID_INVALIDO":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    "Identificador inválido: no puede iniciar con número"
                ))
                continue

            if nombre == "_DECIMAL_INVALIDO":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    "Número decimal inválido (múltiples puntos)"
                ))
                continue

            if nombre == "_IGUAL_SIMPLE":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    "'=' no válido — usa ':' o '=='"
                ))
                continue

            if nombre == "TK_ERROR":
                errores.append(ErrorLexico(
                    lexema, linea, col,
                    f"Caracter no reconocido: '{lexema}'"
                ))
                continue

            # ── Tokens válidos ────────────────
            if nombre == "TK_ID":
                tipo = PALABRAS_RESERVADAS.get(
                    lexema.upper(), TipoToken.TK_ID
                )
            else:
                tipo = TipoToken[nombre]

            tokens.append(Token(
                tipo=tipo.value,
                lexema=lexema,
                linea=linea,
                columna=col,
                categoria=categoria_de(tipo)
            ))

        tokens.append(Token(
            tipo="TK_EOF",
            lexema="EOF",
            linea=linea,
            columna=-1,
            categoria="otro"
        ))

        return tokens, errores