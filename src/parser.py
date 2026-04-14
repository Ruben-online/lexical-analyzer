"""
parser.py — Analizador Sintactico

Gramatica implementada (BNF):

  <programa>          ::= INICIO <sentencias> FIN
  <sentencias>        ::= <sentencia> <sentencias> | <sentencia>
  <sentencia>         ::= <bloque_paciente>
                        | <bloque_rutina>
                        | <bloque_dieta>
                        | <sentencia_si>
                        | <sentencia_imprimir>
                        | <instruccion>

  <bloque_paciente>   ::= PACIENTE : TK_ID ; <datos_paciente>
  <datos_paciente>    ::= <instruccion> <datos_paciente> | <instruccion>
  <instruccion>       ::= EDAD        : TK_ENTERO  ;
                        | PESO        : <numero>   ;
                        | OBJETIVO    : TK_ID      ;
                        | RESTRICCION : < TK_ID >  ;

  <bloque_rutina>     ::= RUTINA : TK_ID ; <acciones> FIN
  <bloque_dieta>      ::= DIETA  : TK_ID ; <acciones> FIN
  <acciones>          ::= <accion> <acciones> | <accion>
  <accion>            ::= ACCION : TK_ID * TK_ENTERO ;
                        | ACCION : TK_ID + TK_ID     ;
                        | ACCION : TK_ID              ;

  <sentencia_si>      ::= SI <condicion> ENTONCES <sentencias> FIN
  <condicion>         ::= <lado_izq> <operador_comp> <valor>
  <lado_izq>          ::= TK_ID | PESO | EDAD
  <operador_comp>     ::= == | > | < | >= | <=
  <valor>             ::= TK_ID | TK_ENTERO | TK_DECIMAL

  <sentencia_imprimir>::= IMPRIMIR TK_ID ;

 Analizador: Descendente recursivo (LL(1))
  - cada regla gramatical = un metodo _parsear_X()
  - _consumir() avanza y verifica el token esperado
  - al primer error sintactico se lanza ErrorSintacticoException
"""

from dataclasses import dataclass, field
from typing import Optional
from tokens import TipoToken
from lexer import Token

### Nodos del AST
@dataclass
class Nodo:
    """Nodo base del árbol sintáctico."""
    tipo:  str
    hijos: list = field(default_factory=list)
    valor: str  = ""          # para nodos hoja (lexema)

    def es_hoja(self) -> bool:
        return len(self.hijos) == 0

    def agregar(self, hijo: "Nodo"):
        self.hijos.append(hijo)
        return self

    def hoja(label: str) -> "Nodo":
        """Crea un nodo terminal (hoja del árbol)."""
        return Nodo(tipo="TERMINAL", valor=label)


#  Errores sintactico
class ErrorSintacticoException(Exception):
    def __init__(self, esperado: str, token: Token):
        self.esperado = esperado
        self.token    = token
        self.linea    = token.linea
        self.columna  = token.columna
        super().__init__(str(self))

    def __str__(self):
        return (
            f"Error sintáctico en L{self.linea}:C{self.columna} — "
            f"se esperaba {self.esperado}, "
            f"se encontró '{self.token.lexema}' ({self.token.tipo})"
        )

    def to_dict(self) -> dict:
        return {
            "mensaje":  str(self),
            "esperado": self.esperado,
            "encontrado": self.token.lexema,
            "tipo_encontrado": self.token.tipo,
            "linea":    self.linea,
            "columna":  self.columna,
        }

### Parser
# Tokens que pueden iniciar una sentencia (para el lookahead)
_INICIO_SENTENCIA = {
    TipoToken.PACIENTE.value,
    TipoToken.RUTINA.value,
    TipoToken.DIETA.value,
    TipoToken.TK_SI.value,
    TipoToken.TK_IMPRIMIR.value,
    TipoToken.EDAD.value,
    TipoToken.PESO.value,
    TipoToken.OBJETIVO.value,
    TipoToken.RESTRICCION.value,
    TipoToken.ACCION.value,
}

# Operadores de comparación válidos en condiciones
_OPS_COMP = {
    TipoToken.TK_IGUAL.value,
    TipoToken.TK_MAYOR.value,
    TipoToken.TK_MENOR.value,
    TipoToken.TK_MAYOR_IGUAL.value,
    TipoToken.TK_MENOR_IGUAL.value,
}


class Parser:
    """
    Analizador sintáctico descendente recursivo.
    Recibe la lista de tokens del Lexer y produce un árbol sintáctico (Nodo).
    """

    def __init__(self, tokens: list[Token]):
        # Filtrar EOF para manejarlo aparte
        self._tokens  = [t for t in tokens if t.tipo != "TK_EOF"]
        self._eof     = next((t for t in tokens if t.tipo == "TK_EOF"),
                             Token("TK_EOF", "EOF", 0, -1, "otro"))
        self._pos     = 0

    # ── Helpers internos ─────────────────────────────────────

    def _actual(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._eof

    def _avanzar(self) -> Token:
        t = self._actual()
        if self._pos < len(self._tokens):
            self._pos += 1
        return t

    def _verificar(self, *tipos: str) -> bool:
        return self._actual().tipo in tipos

    def _consumir(self, tipo: str, descripcion: str = "") -> Token:
        """Consume el token actual si coincide con `tipo`, si no lanza error."""
        t = self._actual()
        if t.tipo == tipo:
            return self._avanzar()
        raise ErrorSintacticoException(
            descripcion or tipo, t
        )

    def _hoja(self, token: Token) -> Nodo:
        return Nodo(tipo="TERMINAL", valor=token.lexema)

    # ── Punto de entrada ─────────────────────────────────────

    def parsear(self) -> tuple[Optional[Nodo], Optional[ErrorSintacticoException]]:
        """
        Parsea el programa completo.
        Retorna (arbol, None) si es válido, o (None, error) si hay error sintáctico.
        """
        try:
            arbol = self._parsear_programa()
            return arbol, None
        except ErrorSintacticoException as e:
            return None, e

    # ── Reglas gramaticales ───────────────────────────────────

    def _parsear_programa(self) -> Nodo:
        """<programa> ::= INICIO <sentencias> FIN"""
        nodo = Nodo(tipo="PROGRAMA")

        tk_inicio = self._consumir(TipoToken.TK_INICIO.value, "INICIO")
        nodo.agregar(self._hoja(tk_inicio))

        nodo.agregar(self._parsear_sentencias())

        tk_fin = self._consumir(TipoToken.TK_FIN.value, "FIN")
        nodo.agregar(self._hoja(tk_fin))

        # Verificar que no haya tokens después del FIN
        if self._actual().tipo != "TK_EOF":
            t = self._actual()
            raise ErrorSintacticoException("fin de programa", t)

        return nodo

    def _parsear_sentencias(self) -> Nodo:
        """<sentencias> ::= <sentencia> <sentencias> | <sentencia>"""
        nodo = Nodo(tipo="SENTENCIAS")

        while self._actual().tipo in _INICIO_SENTENCIA:
            nodo.agregar(self._parsear_sentencia())

        if not nodo.hijos:
            # Un bloque vacío es válido (ej: INICIO FIN)
            pass

        return nodo

    def _parsear_sentencia(self) -> Nodo:
        """<sentencia> ::= <bloque_paciente> | <bloque_rutina> | ..."""
        t = self._actual()

        if t.tipo == TipoToken.PACIENTE.value:
            return self._parsear_bloque_paciente()
        elif t.tipo == TipoToken.RUTINA.value:
            return self._parsear_bloque_rutina()
        elif t.tipo == TipoToken.DIETA.value:
            return self._parsear_bloque_dieta()
        elif t.tipo == TipoToken.TK_SI.value:
            return self._parsear_sentencia_si()
        elif t.tipo == TipoToken.TK_IMPRIMIR.value:
            return self._parsear_sentencia_imprimir()
        else:
            return self._parsear_instruccion()

    # ── Bloque PACIENTE ───────────────────────────────────────

    def _parsear_bloque_paciente(self) -> Nodo:
        """<bloque_paciente> ::= PACIENTE : TK_ID ; <datos_paciente>"""
        nodo = Nodo(tipo="BLOQUE_PACIENTE")

        nodo.agregar(self._hoja(self._consumir(TipoToken.PACIENTE.value, "PACIENTE")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre del paciente (identificador)")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))

        # Datos opcionales del paciente
        _DATOS = {TipoToken.EDAD.value, TipoToken.PESO.value,
                  TipoToken.OBJETIVO.value, TipoToken.RESTRICCION.value}
        while self._actual().tipo in _DATOS:
            nodo.agregar(self._parsear_instruccion())

        return nodo

    def _parsear_instruccion(self) -> Nodo:
        """
        <instruccion> ::= EDAD        : TK_ENTERO ;
                        | PESO        : <numero>   ;
                        | OBJETIVO    : TK_ID      ;
                        | RESTRICCION : < TK_ID >  ;
        """
        t = self._actual()

        if t.tipo == TipoToken.EDAD.value:
            return self._parsear_instruccion_simple(
                TipoToken.EDAD.value, TipoToken.TK_ENTERO.value, "número entero"
            )
        elif t.tipo == TipoToken.PESO.value:
            return self._parsear_instruccion_numero(TipoToken.PESO.value)
        elif t.tipo == TipoToken.OBJETIVO.value:
            return self._parsear_instruccion_simple(
                TipoToken.OBJETIVO.value, TipoToken.TK_ID.value, "identificador"
            )
        elif t.tipo == TipoToken.RESTRICCION.value:
            return self._parsear_restriccion()
        else:
            raise ErrorSintacticoException(
                "EDAD, PESO, OBJETIVO o RESTRICCION", t
            )

    def _parsear_instruccion_simple(self, kw: str, tipo_valor: str, desc_valor: str) -> Nodo:
        """Parsea: KW : VALOR ;"""
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(kw, kw)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(tipo_valor, desc_valor)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _parsear_instruccion_numero(self, kw: str) -> Nodo:
        """Parsea: KW : (ENTERO | DECIMAL) ;"""
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(kw, kw)))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))

        t = self._actual()
        if t.tipo in (TipoToken.TK_ENTERO.value, TipoToken.TK_DECIMAL.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintacticoException("número (entero o decimal)", t)

        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    def _parsear_restriccion(self) -> Nodo:
        """<instruccion> ::= RESTRICCION : < TK_ID > ;"""
        nodo = Nodo(tipo="INSTRUCCION")
        nodo.agregar(self._hoja(self._consumir(TipoToken.RESTRICCION.value, "RESTRICCION")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_MENOR.value, "'<'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "tipo de restricción (identificador)")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_MAYOR.value, "'>'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    # ── Bloques RUTINA / DIETA ────────────────────────────────

    def _parsear_bloque_rutina(self) -> Nodo:
        """<bloque_rutina> ::= RUTINA : TK_ID ; <acciones> FIN"""
        nodo = Nodo(tipo="BLOQUE_RUTINA")
        nodo.agregar(self._hoja(self._consumir(TipoToken.RUTINA.value, "RUTINA")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre de rutina (identificador)")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        nodo.agregar(self._parsear_acciones())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        return nodo

    def _parsear_bloque_dieta(self) -> Nodo:
        """<bloque_dieta> ::= DIETA : TK_ID ; <acciones> FIN"""
        nodo = Nodo(tipo="BLOQUE_DIETA")
        nodo.agregar(self._hoja(self._consumir(TipoToken.DIETA.value, "DIETA")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre de dieta (identificador)")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        nodo.agregar(self._parsear_acciones())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))
        return nodo

    def _parsear_acciones(self) -> Nodo:
        """<acciones> ::= <accion> <acciones> | <accion>"""
        nodo = Nodo(tipo="ACCIONES")

        if not self._verificar(TipoToken.ACCION.value):
            raise ErrorSintacticoException(
                "al menos una ACCION", self._actual()
            )

        while self._verificar(TipoToken.ACCION.value):
            nodo.agregar(self._parsear_accion())

        return nodo

    def _parsear_accion(self) -> Nodo:
        """
        <accion> ::= ACCION : TK_ID * TK_ENTERO ;
                   | ACCION : TK_ID + TK_ID     ;
                   | ACCION : TK_ID              ;
        """
        nodo = Nodo(tipo="ACCION")
        nodo.agregar(self._hoja(self._consumir(TipoToken.ACCION.value, "ACCION")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ASIGNACION.value, "':'")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre del ejercicio/alimento")))

        # Opcional: operador + operando
        if self._verificar(TipoToken.TK_MULT.value):
            nodo.agregar(self._hoja(self._avanzar()))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ENTERO.value, "número de repeticiones")))
        elif self._verificar(TipoToken.TK_SUMA.value):
            nodo.agregar(self._hoja(self._avanzar()))
            nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "identificador")))

        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo

    # ── SI (condicional) ──────────────────────────────────────

    def _parsear_sentencia_si(self) -> Nodo:
        """<sentencia_si> ::= SI <condicion> ENTONCES <sentencias> FIN"""
        nodo = Nodo(tipo="SENTENCIA_SI")

        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_SI.value, "SI")))
        nodo.agregar(self._parsear_condicion())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ENTONCES.value, "ENTONCES")))
        nodo.agregar(self._parsear_sentencias())
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN.value, "FIN")))

        return nodo

    def _parsear_condicion(self) -> Nodo:
        """<condicion> ::= <lado_izq> <operador_comp> <valor>"""
        nodo = Nodo(tipo="CONDICION")

        # Lado izquierdo: PESO, EDAD, o cualquier identificador
        t = self._actual()
        if t.tipo in (TipoToken.PESO.value, TipoToken.EDAD.value, TipoToken.TK_ID.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintacticoException(
                "PESO, EDAD o identificador en condición", t
            )

        # Operador de comparación
        t = self._actual()
        if t.tipo in _OPS_COMP:
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintacticoException(
                "operador de comparación (==, >, <, >=, <=)", t
            )

        # Valor derecho
        t = self._actual()
        if t.tipo in (TipoToken.TK_ID.value, TipoToken.TK_ENTERO.value, TipoToken.TK_DECIMAL.value):
            nodo.agregar(self._hoja(self._avanzar()))
        else:
            raise ErrorSintacticoException(
                "valor (identificador o número)", t
            )

        return nodo

    # ── IMPRIMIR ──────────────────────────────────────────────

    def _parsear_sentencia_imprimir(self) -> Nodo:
        """<sentencia_imprimir> ::= IMPRIMIR TK_ID ;"""
        nodo = Nodo(tipo="SENTENCIA_IMPRIMIR")
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_IMPRIMIR.value, "IMPRIMIR")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_ID.value, "nombre del bloque a imprimir")))
        nodo.agregar(self._hoja(self._consumir(TipoToken.TK_FIN_INSTRUC.value, "';'")))
        return nodo


#  Serializacion del arbol a texto y a dict
#dict de mensajes en pantalla

def arbol_a_texto(nodo: Nodo, prefijo: str = "", es_ultimo: bool = True) -> str:
    """
    Convierte el árbol a texto estilo consola:
    PROGRAMA
    ├── INICIO
    ├── SENTENCIAS
    │   └── BLOQUE_PACIENTE
    │       ├── PACIENTE
    │       └── Sofia
    └── FIN
    """
    conector = "└── " if es_ultimo else "├── "
    label    = nodo.valor if nodo.es_hoja() else nodo.tipo
    linea    = prefijo + conector + label + "\n"

    extension = "    " if es_ultimo else "│   "
    nuevo_pref = prefijo + extension

    for i, hijo in enumerate(nodo.hijos):
        ultimo = (i == len(nodo.hijos) - 1)
        linea += arbol_a_texto(hijo, nuevo_pref, ultimo)

    return linea


def arbol_a_dict(nodo: Nodo) -> dict:
    """Convierte el árbol a diccionario para JSON (usado por el frontend)."""
    if nodo.es_hoja():
        return {"nombre": nodo.valor, "hijos": [], "es_hoja": True}
    return {
        "nombre":   nodo.tipo,
        "hijos":    [arbol_a_dict(h) for h in nodo.hijos],
        "es_hoja":  False
    }
