from enum import Enum


class TipoToken(Enum):
    # ── Palabras reservadas ──────────────────
    PACIENTE    = "PACIENTE"
    EDAD        = "EDAD"
    PESO        = "PESO"
    OBJETIVO    = "OBJETIVO"
    RESTRICCION = "RESTRICCION"
    ACCION      = "ACCION"
    RECETA      = "RECETA"
    RUTINA      = "RUTINA"
    DIETA       = "DIETA"
    

    # ── Identificadores y literales ──────────
    TK_ID       = "TK_ID"
    TK_ENTERO   = "TK_ENTERO"
    TK_DECIMAL  = "TK_DECIMAL"
    TK_CADENA   = "TK_CADENA"

    # ── Operadores ───────────────────────────
    TK_ASIGNACION  = "TK_ASIGNACION"   # :
    TK_IGUAL       = "TK_IGUAL"        # ==
    TK_SUMA        = "TK_SUMA"         # +
    TK_MULT        = "TK_MULT"         # *

    # ── Símbolos estructurales ───────────────
    TK_FIN_INSTRUC = "TK_FIN_INSTRUC"  # ;
    TK_LT          = "TK_LT"           # <
    TK_GT          = "TK_GT"           # >

    # ── Especiales ───────────────────────────
    TK_EOF         = "TK_EOF"
    TK_ERROR       = "TK_ERROR"


# Tabla de palabras reservadas (lookup O(1))
PALABRAS_RESERVADAS: dict[str, TipoToken] = {
    "PACIENTE":    TipoToken.PACIENTE,
    "EDAD":        TipoToken.EDAD,
    "PESO":        TipoToken.PESO,
    "OBJETIVO":    TipoToken.OBJETIVO,
    "RESTRICCION": TipoToken.RESTRICCION,
    "ACCION":      TipoToken.ACCION,
    "RECETA":      TipoToken.RECETA,
    "RUTINA":      TipoToken.RUTINA,
    "DIETA":       TipoToken.DIETA,
}

# Categorías para colorear en el frontend
CATEGORIAS: dict[str, list[TipoToken]] = {
    "reservada": [
        TipoToken.PACIENTE, TipoToken.EDAD, TipoToken.PESO,
        TipoToken.OBJETIVO, TipoToken.RESTRICCION, TipoToken.ACCION,
        TipoToken.RECETA, TipoToken.RUTINA, TipoToken.DIETA,
    ],
    "identificador": [TipoToken.TK_ID],
    "numero":        [TipoToken.TK_ENTERO, TipoToken.TK_DECIMAL],
    "cadena":        [TipoToken.TK_CADENA],
    "operador":      [TipoToken.TK_ASIGNACION, TipoToken.TK_IGUAL,
                      TipoToken.TK_SUMA, TipoToken.TK_MULT],
    "simbolo":       [TipoToken.TK_FIN_INSTRUC, TipoToken.TK_LT, TipoToken.TK_GT],
    "error":         [TipoToken.TK_ERROR],
}

def categoria_de(tipo: TipoToken) -> str:
    for cat, tipos in CATEGORIAS.items():
        if tipo in tipos:
            return cat
    return "otro"
