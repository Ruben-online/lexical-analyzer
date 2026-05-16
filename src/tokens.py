from enum import Enum

class TipoToken(Enum):
    PACIENTE    = "PACIENTE"
    EDAD        = "EDAD"
    PESO        = "PESO"
    OBJETIVO    = "OBJETIVO"
    RESTRICCION = "RESTRICCION"
    ACCION      = "ACCION"
    RECETA      = "RECETA"
    RUTINA      = "RUTINA"
    DIETA       = "DIETA"
    TK_INICIO   = "TK_INICIO"
    TK_FIN      = "TK_FIN"
    TK_SI       = "TK_SI"
    TK_ENTONCES = "TK_ENTONCES"
    TK_IMPRIMIR = "TK_IMPRIMIR"
    TK_ID       = "TK_ID"
    TK_ENTERO   = "TK_ENTERO"
    TK_DECIMAL  = "TK_DECIMAL"
    TK_CADENA   = "TK_CADENA"
    TK_ASIGNACION  = "TK_ASIGNACION"
    TK_IGUAL       = "TK_IGUAL"
    TK_SUMA        = "TK_SUMA"
    TK_MULT        = "TK_MULT"
    TK_MAYOR       = "TK_MAYOR"
    TK_MENOR       = "TK_MENOR"
    TK_MAYOR_IGUAL = "TK_MAYOR_IGUAL"
    TK_MENOR_IGUAL = "TK_MENOR_IGUAL"
    TK_FIN_INSTRUC = "TK_FIN_INSTRUC"
    TK_LT          = "TK_LT"
    TK_GT          = "TK_GT"
    TK_EOF         = "TK_EOF"
    TK_ERROR       = "TK_ERROR"

PALABRAS_RESERVADAS = {
    "PACIENTE":    TipoToken.PACIENTE,
    "EDAD":        TipoToken.EDAD,
    "PESO":        TipoToken.PESO,
    "OBJETIVO":    TipoToken.OBJETIVO,
    "RESTRICCION": TipoToken.RESTRICCION,
    "ACCION":      TipoToken.ACCION,
    "RECETA":      TipoToken.RECETA,
    "RUTINA":      TipoToken.RUTINA,
    "DIETA":       TipoToken.DIETA,
    "INICIO":      TipoToken.TK_INICIO,
    "FIN":         TipoToken.TK_FIN,
    "SI":          TipoToken.TK_SI,
    "ENTONCES":    TipoToken.TK_ENTONCES,
    "IMPRIMIR":    TipoToken.TK_IMPRIMIR,
}

CATEGORIAS = {
    "reservada":    [TipoToken.PACIENTE, TipoToken.EDAD, TipoToken.PESO,
                     TipoToken.OBJETIVO, TipoToken.RESTRICCION, TipoToken.ACCION,
                     TipoToken.RECETA, TipoToken.RUTINA, TipoToken.DIETA,
                     TipoToken.TK_INICIO, TipoToken.TK_FIN, TipoToken.TK_SI,
                     TipoToken.TK_ENTONCES, TipoToken.TK_IMPRIMIR],
    "identificador":[TipoToken.TK_ID],
    "numero":       [TipoToken.TK_ENTERO, TipoToken.TK_DECIMAL],
    "cadena":       [TipoToken.TK_CADENA],
    "operador":     [TipoToken.TK_ASIGNACION, TipoToken.TK_IGUAL,
                     TipoToken.TK_SUMA, TipoToken.TK_MULT,
                     TipoToken.TK_MAYOR, TipoToken.TK_MENOR,
                     TipoToken.TK_MAYOR_IGUAL, TipoToken.TK_MENOR_IGUAL],
    "simbolo":      [TipoToken.TK_FIN_INSTRUC, TipoToken.TK_LT, TipoToken.TK_GT],
    "error":        [TipoToken.TK_ERROR],
}

def categoria_de(tipo):
    for cat, tipos in CATEGORIAS.items():
        if tipo in tipos:
            return cat
    return "otro"
