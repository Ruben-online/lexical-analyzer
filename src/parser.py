"""
parser.py — Analizador Sintáctico — Compilador de Nutrias
Gramática BNF implementada (descendente recursivo LL1)
"""

from dataclasses import dataclass, field
from typing import Optional
from tokens import TipoToken
from lexer import Token


# ─── Nodos del AST ───────────────────────────────────────────

@dataclass
class Nodo:
    tipo:  str
    hijos: list = field(default_factory=list)
    valor: str  = ""

    def es_hoja(self): return len(self.hijos) == 0
    def agregar(self, h): self.hijos.append(h); return self

    @staticmethod
    def hoja(lexema: str) -> "Nodo":
        return Nodo(tipo="TERMINAL", valor=lexema)


# ─── Error sintáctico ─────────────────────────────────────────

class ErrorSintactico(Exception):
    def __init__(self, esperado: str, token: Token):
        self.esperado   = esperado
        self.token      = token
        self.linea      = token.linea
        self.columna    = token.columna
        super().__init__(str(self))

    def __str__(self):
        return (f"Error sintáctico en L{self.linea}:C{self.columna} — "
                f"se esperaba {self.esperado}, "
                f"se encontró '{self.token.lexema}' ({self.token.tipo})")

    def to_dict(self):
        return {"mensaje": str(self), "esperado": self.esperado,
                "encontrado": self.token.lexema,
                "tipo_encontrado": self.token.tipo,
                "linea": self.linea, "columna": self.columna}


# ─── Parser ───────────────────────────────────────────────────

_INICIO_SENT = {
    TipoToken.PACIENTE.value, TipoToken.RUTINA.value,
    TipoToken.DIETA.value,    TipoToken.TK_SI.value,
    TipoToken.TK_IMPRIMIR.value, TipoToken.EDAD.value,
    TipoToken.PESO.value,     TipoToken.OBJETIVO.value,
    TipoToken.RESTRICCION.value, TipoToken.ACCION.value,
}

_OPS_COMP = {
    TipoToken.TK_IGUAL.value, TipoToken.TK_GT.value,
    TipoToken.TK_LT.value,    "TK_MAYOR_IGUAL", "TK_MENOR_IGUAL",
}


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = [t for t in tokens if t.tipo != "TK_EOF"]
        self._eof    = next((t for t in tokens if t.tipo == "TK_EOF"),
                            Token("TK_EOF","EOF",0,-1,"otro"))
        self._pos = 0

    def _actual(self) -> Token:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else self._eof

    def _avanzar(self) -> Token:
        t = self._actual()
        if self._pos < len(self._tokens): self._pos += 1
        return t

    def _verificar(self, *tipos) -> bool:
        return self._actual().tipo in tipos

    def _consumir(self, tipo: str, desc: str = "") -> Token:
        t = self._actual()
        if t.tipo == tipo: return self._avanzar()
        raise ErrorSintactico(desc or tipo, t)

    def _hoja(self, t: Token) -> Nodo:
        return Nodo(tipo="TERMINAL", valor=t.lexema)

    def parsear(self) -> tuple[Optional[Nodo], Optional[ErrorSintactico]]:
        try:
            return self._programa(), None
        except ErrorSintactico as e:
            return None, e

    def _programa(self) -> Nodo:
        nodo = Nodo(tipo="PROGRAMA")
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_INICIO.value, "INICIO")))
        nodo.agregar(self._sentencias())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        if self._actual().tipo != "TK_EOF":
            raise ErrorSintactico("fin de programa", self._actual())
        return nodo

    def _sentencias(self) -> Nodo:
        nodo = Nodo(tipo="SENTENCIAS")
        while self._actual().tipo in _INICIO_SENT:
            nodo.agregar(self._sentencia())
        return nodo

    def _sentencia(self) -> Nodo:
        t = self._actual().tipo
        if t == TipoToken.PACIENTE.value:    return self._bloque_paciente()
        if t == TipoToken.RUTINA.value:      return self._bloque_rutina()
        if t == TipoToken.DIETA.value:       return self._bloque_dieta()
        if t == TipoToken.TK_SI.value:       return self._sentencia_si()
        if t == TipoToken.TK_IMPRIMIR.value: return self._sentencia_imprimir()
        return self._instruccion()

    def _bloque_paciente(self) -> Nodo:
        nodo = Nodo(tipo="BLOQUE_PACIENTE")
        nodo.agregar(self._hoja(self._consumir(TipoToken.PACIENTE.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre del paciente")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        _datos = {TipoToken.EDAD.value, TipoToken.PESO.value,
                TipoToken.OBJETIVO.value, TipoToken.RESTRICCION.value}
        while self._actual().tipo in _datos:
            nodo.agregar(self._instruccion())
        return nodo

    def _instruccion(self) -> Nodo:
        t = self._actual().tipo
        if t == TipoToken.RESTRICCION.value: return self._restriccion()
        if t in (TipoToken.EDAD.value, TipoToken.OBJETIVO.value):
            return self._instruccion_simple(t, TipoToken.TK_ID.value if t == TipoToken.OBJETIVO.value else TipoToken.TK_ENTERO.value, "valor")
        if t == TipoToken.PESO.value: return self._instruccion_numero(t)
        raise ErrorSintactico("EDAD, PESO, OBJETIVO o RESTRICCION", self._actual())
    
    def _instruccion_simple(self, kw, tipo_val, desc) -> Nodo:
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(kw)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(tipo_val, desc)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _instruccion_numero(self, kw) -> Nodo:
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(kw)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        t = self._actual()
        if t.tipo in (TipoToken.TK_ENTERO.value, TipoToken.TK_DECIMAL.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintactico("número (entero o decimal)", t)
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _restriccion(self) -> Nodo:
        """RESTRICCION : <id> (, <id>)* ;"""
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(TipoToken.RESTRICCION.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        # primera restricción obligatoria
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_LT.value, "'<'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "tipo restricción")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_GT.value, "'>'")))
        # restricciones adicionales opcionales separadas por coma
        while self._verificar(TipoToken.TK_COMA.value):
            nodo.agregar(self._hoja(self._avanzar()))  # ,
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_LT.value, "'<'")))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "tipo restricción")))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_GT.value, "'>'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _bloque_rutina(self) -> Nodo:
        nodo = Nodo(tipo="BLOQUE_RUTINA")
        nodo.agregar(self._hoja(self._consumir(TipoToken.RUTINA.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre rutina")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        nodo.agregar(self._acciones())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        return nodo

    def _bloque_dieta(self) -> Nodo:
        nodo = Nodo(tipo="BLOQUE_DIETA")
        nodo.agregar(self._hoja(self._consumir(TipoToken.DIETA.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre dieta")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        nodo.agregar(self._acciones())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        return nodo

    def _acciones(self) -> Nodo:
        nodo = Nodo(tipo="ACCIONES")
        if not self._verificar(TipoToken.ACCION.value):
            raise ErrorSintactico("al menos una ACCION", self._actual())
        while self._verificar(TipoToken.ACCION.value):
            nodo.agregar(self._accion())
        return nodo

    def _accion(self) -> Nodo:
        nodo = Nodo(tipo="ACCION")
        nodo.agregar(self._hoja(self._consumir(TipoToken.ACCION.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre ejercicio/alimento")))
        if self._verificar(TipoToken.TK_MULT.value):
            nodo.agregar(self._hoja(self._avanzar()))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ENTERO.value, "número de repeticiones")))
        elif self._verificar(TipoToken.TK_SUMA.value):
            nodo.agregar(self._hoja(self._avanzar()))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "identificador")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _sentencia_si(self) -> Nodo:
        nodo = Nodo(tipo="SENTENCIA_SI")
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_SI.value)))
        nodo.agregar(self._condicion())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ENTONCES.value, "ENTONCES")))
        nodo.agregar(self._sentencias())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        return nodo

    def _condicion(self) -> Nodo:
        nodo = Nodo(tipo="CONDICION")
        t = self._actual()
        if t.tipo in (TipoToken.PESO.value, TipoToken.EDAD.value, TipoToken.TK_ID.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintactico("PESO, EDAD o identificador", t)
        t = self._actual()
        if t.tipo in (TipoToken.TK_IGUAL.value, TipoToken.TK_GT.value, TipoToken.TK_LT.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintactico("operador de comparación (==, >, <)", t)
        t = self._actual()
        if t.tipo in (TipoToken.TK_ID.value, TipoToken.TK_ENTERO.value, TipoToken.TK_DECIMAL.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintactico("valor numérico o identificador", t)
        return nodo

    def _sentencia_imprimir(self) -> Nodo:
        nodo = Nodo(tipo="SENTENCIA_IMPRIMIR")
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_IMPRIMIR.value)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre del bloque a imprimir")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo


# ─── Utilidades de serialización ─────────────────────────────

def arbol_a_texto(nodo: Nodo, prefijo="", es_ultimo=True) -> str:
    conector  = "└── " if es_ultimo else "├── "
    label     = nodo.valor if nodo.es_hoja() else nodo.tipo
    linea     = prefijo + conector + label + "\n"
    extension = "    " if es_ultimo else "│   "
    for i, hijo in enumerate(nodo.hijos):
        linea += arbol_a_texto(hijo, prefijo + extension, i == len(nodo.hijos) - 1)
    return linea

def arbol_a_dict(nodo: Nodo) -> dict:
    if nodo.es_hoja():
        return {"nombre": nodo.valor, "hijos": [], "es_hoja": True}
    return {"nombre": nodo.tipo, "hijos": [arbol_a_dict(h) for h in nodo.hijos], "es_hoja": False}
