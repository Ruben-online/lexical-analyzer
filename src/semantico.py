"""
semantico.py — Analizador Semántico — Compilador de Nutrias
Construye la tabla de símbolos y valida reglas semánticas.

Reglas implementadas:
  SEM-01  RUTINA/DIETA/SI/IMPRIMIR antes que PACIENTE
  SEM-02  Paciente declarado más de una vez
  SEM-03  Nombre de RUTINA o DIETA duplicado
  SEM-04  EDAD fuera de rango (1-120) o no entero
  SEM-05  PESO fuera de rango (1.0-700.0)
  SEM-06  IMPRIMIR referencia bloque no declarado
  SEM-07  ALTURA fuera de rango (0.50-2.50 m)
  SEM-10  Propiedad del paciente declarada dos veces
  SEM-11  Bloque RUTINA/DIETA sin ninguna ACCION
  SEM-12  IMC usado sin PESO o ALTURA declarados previamente
"""

from dataclasses import dataclass, field
from parser import Nodo


# ─── Tabla de símbolos ────────────────────────────────────────

@dataclass
class SimboloPaciente:
    nombre:        str
    edad:          int   = None
    peso:          float = None
    objetivo:      str   = None
    restricciones: list  = field(default_factory=list)
    imc:           float = None    # calculado por la instrucción IMC
    linea:         int   = 0
    altura:        float = None

    def to_dict(self):
        return {
            "identificador": self.nombre,
            "tipo":          "PACIENTE",
            "edad":          self.edad,
            "peso":          self.peso,
            "objetivo":      self.objetivo,
            "restricciones": self.restricciones,
            # Agrega esta línea en to_dict() de SimboloPaciente:
            "altura": self.altura,
            "imc":    round(self.imc, 2) if self.imc is not None else None,
            "linea":         self.linea,
        }


@dataclass
class SimboloBloque:
    nombre:  str
    tipo:    str   # RUTINA | DIETA
    acciones: list = field(default_factory=list)
    linea:   int   = 0

    def to_dict(self):
        return {
            "identificador": self.nombre,
            "tipo":          self.tipo,
            "acciones":      self.acciones,
            "linea":         self.linea,
        }


@dataclass
class TablaSimbolos:
    paciente: SimboloPaciente = None
    bloques:  list = field(default_factory=list)   # [SimboloBloque]

    def paciente_declarado(self) -> bool:
        return self.paciente is not None

    def nombre_bloque_existe(self, nombre: str) -> bool:
        return any(b.nombre == nombre for b in self.bloques)

    def buscar_bloque(self, nombre: str):
        return next((b for b in self.bloques if b.nombre == nombre), None)

    def to_dict(self) -> dict:
        return {
            "paciente": self.paciente.to_dict() if self.paciente else None,
            "bloques":  [b.to_dict() for b in self.bloques],
        }


# ─── Error semántico ──────────────────────────────────────────

class ErrorSemantico(Exception):
    def __init__(self, codigo: str, mensaje: str, linea: int = 0):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.linea   = linea
        super().__init__(mensaje)

    def to_dict(self):
        return {"codigo": self.codigo, "mensaje": self.mensaje, "linea": self.linea}


# ─── Analizador semántico ─────────────────────────────────────

class AnalizadorSemantico:
    """
    Recorre el AST producido por el Parser y aplica las
    reglas semánticas del lenguaje .nut, construyendo la
    tabla de símbolos automáticamente.
    """

    def __init__(self):
        self.tabla = TablaSimbolos()
        self._props_declaradas: set = set()   # EDAD, PESO, OBJETIVO ya declaradas

    def analizar(self, arbol: Nodo) -> TablaSimbolos:
        """
        Punto de entrada. Lanza ErrorSemantico si detecta un problema.
        Retorna la tabla de símbolos si el análisis es exitoso.
        """
        self._visitar(arbol)
        return self.tabla

    # ─── Visitantes ──────────────────────────────────────────

    def _visitar(self, nodo: Nodo):
        if nodo.tipo == "PROGRAMA":
            for hijo in nodo.hijos:
                self._visitar(hijo)

        elif nodo.tipo == "SENTENCIAS":
            for hijo in nodo.hijos:
                self._visitar(hijo)

        elif nodo.tipo == "BLOQUE_PACIENTE":
            self._visitar_paciente(nodo)

        elif nodo.tipo == "BLOQUE_RUTINA":
            self._visitar_bloque(nodo, "RUTINA")

        elif nodo.tipo == "BLOQUE_DIETA":
            self._visitar_bloque(nodo, "DIETA")

        elif nodo.tipo == "SENTENCIA_SI":
            self._visitar_si(nodo)

        elif nodo.tipo == "SENTENCIA_IMPRIMIR":
            self._visitar_imprimir(nodo)

    def _visitar_paciente(self, nodo: Nodo):
        # SEM-02: solo un paciente por programa
        if self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-02",
                "El paciente ya fue declarado — solo puede existir un PACIENTE por programa")

        # El segundo hijo (índice 2) es el TK_ID con el nombre
        nombre = self._buscar_terminal(nodo, 2)
        self.tabla.paciente = SimboloPaciente(nombre=nombre)
        self._props_declaradas = set()

        # Procesar instrucciones del paciente
        for hijo in nodo.hijos:
            if hijo.tipo == "INSTRUCCION":
                self._visitar_instruccion_paciente(hijo)

    def _visitar_instruccion_paciente(self, nodo: Nodo):
        etiqueta = nodo.hijos[0].valor.upper()

        # SEM-10: propiedad duplicada (no aplica a RESTRICCION porque son acumulables)
        if etiqueta != "RESTRICCION" and etiqueta in self._props_declaradas:
            raise ErrorSemantico("SEM-10",
                f"La propiedad '{etiqueta}' ya fue declarada para este paciente")
        if etiqueta != "RESTRICCION":
            self._props_declaradas.add(etiqueta)

        valor_nodo = nodo.hijos[2]  # KW : VALOR ...

        if etiqueta == "EDAD":
            # SEM-04: EDAD debe ser entero positivo 1-120
            try:
                edad = int(valor_nodo.valor)
                if not (1 <= edad <= 120):
                    raise ErrorSemantico("SEM-04",
                        f"EDAD fuera de rango válido (1-120): {edad}")
                self.tabla.paciente.edad = edad
            except ValueError:
                raise ErrorSemantico("SEM-04",
                    f"EDAD requiere un número entero, se encontró: '{valor_nodo.valor}'")

        elif etiqueta == "PESO":
            # SEM-05: PESO debe ser numérico 1.0-700.0
            try:
                peso = float(valor_nodo.valor)
                if not (1.0 <= peso <= 700.0):
                    raise ErrorSemantico("SEM-05",
                        f"PESO fuera de rango válido (1.0-700.0 kg): {peso}")
                self.tabla.paciente.peso = peso
            except ValueError:
                raise ErrorSemantico("SEM-05",
                    f"PESO requiere un número, se encontró: '{valor_nodo.valor}'")

        elif etiqueta == "OBJETIVO":
            self.tabla.paciente.objetivo = valor_nodo.valor

        elif etiqueta == "RESTRICCION":
            # Recoger todos los IDs entre < > en los hijos del nodo
            # Formato: RESTRICCION : <ID> (, <ID>)* ;
            # hijos: [RESTRICCION, :, <, ID, >, (, <, ID, >)*, ;]
            i = 3  # primer ID (después de RESTRICCION : <)
            while i < len(nodo.hijos):
                h = nodo.hijos[i]
                if h.es_hoja() and h.valor not in ("RESTRICCION", ":", "<", ">", ",", ";"):
                    self.tabla.paciente.restricciones.append(h.valor)
                i += 1
        elif etiqueta == "ALTURA":
            try:
                altura = float(valor_nodo.valor)
                if not (0.5 <= altura <= 2.5):
                    raise ErrorSemantico("SEM-07",
                        f"ALTURA fuera de rango válido (0.50–2.50 m): {altura}")
                self.tabla.paciente.altura = altura
            except ValueError:
                raise ErrorSemantico("SEM-07",
                    f"ALTURA requiere un número, se encontró: '{valor_nodo.valor}'")

    def _visitar_bloque(self, nodo: Nodo, tipo: str):
        # SEM-01: paciente debe estar declarado primero
        if not self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-01",
                f"El bloque {tipo} fue declarado antes que PACIENTE — "
                f"el paciente debe declararse primero, es la entidad raíz del plan clínico")

        # El índice 2 tiene el nombre del bloque (RUTINA/DIETA : ID ;)
        nombre = self._buscar_terminal(nodo, 2)

        # SEM-03: nombre de bloque duplicado
        if self.tabla.nombre_bloque_existe(nombre):
            raise ErrorSemantico("SEM-03",
                f"El bloque '{nombre}' ya fue declarado — cada RUTINA/DIETA debe tener un nombre único")

        bloque = SimboloBloque(nombre=nombre, tipo=tipo)
        self.tabla.bloques.append(bloque)

        # Procesar acciones
        acciones_nodo = next((h for h in nodo.hijos if h.tipo == "ACCIONES"), None)
        if acciones_nodo is None or not acciones_nodo.hijos:
            raise ErrorSemantico("SEM-11",
                f"El bloque '{nombre}' no tiene ninguna ACCION — debe tener al menos una")

        for accion in acciones_nodo.hijos:
            if accion.tipo == "ACCION":
                desc = self._describir_accion(accion)
                bloque.acciones.append(desc)

    def _visitar_si(self, nodo: Nodo):
        if not self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-01", "El bloque SI fue declarado antes que PACIENTE")

        # SEM-12: si la condición usa IMC, verificar que hay PESO declarado
        condicion = next((h for h in nodo.hijos if h.tipo == "CONDICION"), None)

        if condicion and condicion.hijos and condicion.hijos[0].valor.upper() == "IMC":
            pac = self.tabla.paciente
            if pac.peso is None:
                raise ErrorSemantico("SEM-12",
                    "IMC requiere que el paciente tenga PESO declarado")
            if pac.altura is None:
                raise ErrorSemantico("SEM-12",
                    "IMC requiere que el paciente tenga ALTURA declarada")
            # Fórmula real: kg / m²
            pac.imc = pac.peso / (pac.altura ** 2)
        for hijo in nodo.hijos:
            if hijo.tipo == "SENTENCIAS":
                self._visitar(hijo)

    def _visitar_imprimir(self, nodo: Nodo):
        # SEM-01
        if not self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-01",
                "IMPRIMIR fue usado antes que PACIENTE")

        # SEM-06: el identificador debe existir en tabla de bloques
        nombre = nodo.hijos[1].valor
        if not self.tabla.nombre_bloque_existe(nombre):
            raise ErrorSemantico("SEM-06",
                f"IMPRIMIR '{nombre}': bloque no declarado — "
                f"solo se pueden imprimir RUTINA o DIETA previamente definidas")

    # ─── Helpers ─────────────────────────────────────────────

    def _buscar_terminal(self, nodo: Nodo, indice: int) -> str:
        """Retorna el lexema del hijo en la posición dada."""
        if indice < len(nodo.hijos):
            return nodo.hijos[indice].valor
        return ""

    def _describir_accion(self, nodo: Nodo) -> str:
        """Genera descripción legible de una acción para la tabla."""
        hojas = [h.valor for h in nodo.hijos if h.es_hoja()]
        # hojas: [ACCION, :, nombre, (*, N)?, ;]
        partes = [v for v in hojas if v not in ("ACCION", ":", ";")]
        return " ".join(partes)
