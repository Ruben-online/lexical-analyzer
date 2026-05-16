from dataclasses import dataclass, field
from parser import Nodo

@dataclass
class SimboloPaciente:
    nombre: str; edad: int=None; peso: float=None
    objetivo: str=None; restricciones: list=field(default_factory=list); linea: int=0
    def to_dict(self):
        return {"identificador":self.nombre,"tipo":"PACIENTE","edad":self.edad,
                "peso":self.peso,"objetivo":self.objetivo,"restricciones":self.restricciones,"linea":self.linea}

@dataclass
class SimboloBloque:
    nombre: str; tipo: str; acciones: list=field(default_factory=list); linea: int=0
    def to_dict(self):
        return {"identificador":self.nombre,"tipo":self.tipo,"acciones":self.acciones,"linea":self.linea}

@dataclass
class TablaSimbolos:
    paciente: SimboloPaciente=None; bloques: list=field(default_factory=list)
    def paciente_declarado(self): return self.paciente is not None
    def nombre_bloque_existe(self,nombre): return any(b.nombre==nombre for b in self.bloques)
    def to_dict(self):
        return {"paciente":self.paciente.to_dict() if self.paciente else None,
                "bloques":[b.to_dict() for b in self.bloques]}

class ErrorSemantico(Exception):
    def __init__(self,codigo,mensaje,linea=0):
        self.codigo=codigo; self.mensaje=mensaje; self.linea=linea
        super().__init__(mensaje)
    def to_dict(self): return {"codigo":self.codigo,"mensaje":self.mensaje,"linea":self.linea}

class AnalizadorSemantico:
    def __init__(self): self.tabla=TablaSimbolos(); self._props=set()
    def analizar(self,arbol):
        self._visitar(arbol); return self.tabla
    def _visitar(self,nodo):
        if nodo.tipo in ("PROGRAMA","SENTENCIAS"):
            for h in nodo.hijos: self._visitar(h)
        elif nodo.tipo=="BLOQUE_PACIENTE": self._paciente(nodo)
        elif nodo.tipo=="BLOQUE_RUTINA":  self._bloque(nodo,"RUTINA")
        elif nodo.tipo=="BLOQUE_DIETA":   self._bloque(nodo,"DIETA")
        elif nodo.tipo=="SENTENCIA_SI":
            if not self.tabla.paciente_declarado():
                raise ErrorSemantico("SEM-01","Bloque SI declarado antes que PACIENTE")
            for h in nodo.hijos:
                if h.tipo=="SENTENCIAS": self._visitar(h)
        elif nodo.tipo=="SENTENCIA_IMPRIMIR":
            if not self.tabla.paciente_declarado():
                raise ErrorSemantico("SEM-01","IMPRIMIR usado antes que PACIENTE")
            nombre=nodo.hijos[1].valor
            if not self.tabla.nombre_bloque_existe(nombre):
                raise ErrorSemantico("SEM-06",f"IMPRIMIR '{nombre}': bloque no declarado")
    def _paciente(self,nodo):
        if self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-02","Paciente declarado más de una vez")
        nombre=nodo.hijos[2].valor
        self.tabla.paciente=SimboloPaciente(nombre=nombre); self._props=set()
        for h in nodo.hijos:
            if h.tipo=="INSTRUCCION": self._instruccion_paciente(h)
    def _instruccion_paciente(self,nodo):
        etiqueta=nodo.hijos[0].valor.upper()
        if etiqueta in self._props:
            raise ErrorSemantico("SEM-10",f"Propiedad '{etiqueta}' declarada dos veces")
        self._props.add(etiqueta)
        valor=nodo.hijos[2].valor
        if etiqueta=="EDAD":
            try:
                edad=int(valor)
                if not (1<=edad<=120): raise ErrorSemantico("SEM-04",f"EDAD fuera de rango (1-120): {edad}")
                self.tabla.paciente.edad=edad
            except ValueError: raise ErrorSemantico("SEM-04",f"EDAD requiere entero, se encontró '{valor}'")
        elif etiqueta=="PESO":
            try:
                peso=float(valor)
                if not (1.0<=peso<=700.0): raise ErrorSemantico("SEM-05",f"PESO fuera de rango (1-700): {peso}")
                self.tabla.paciente.peso=peso
            except ValueError: raise ErrorSemantico("SEM-05",f"PESO requiere número, se encontró '{valor}'")
        elif etiqueta=="OBJETIVO": self.tabla.paciente.objetivo=valor
        elif etiqueta=="RESTRICCION": self.tabla.paciente.restricciones.append(nodo.hijos[3].valor)
    def _bloque(self,nodo,tipo):
        if not self.tabla.paciente_declarado():
            raise ErrorSemantico("SEM-01",f"Bloque {tipo} declarado antes que PACIENTE")
        nombre=nodo.hijos[2].valor
        if self.tabla.nombre_bloque_existe(nombre):
            raise ErrorSemantico("SEM-03",f"Bloque '{nombre}' declarado más de una vez")
        bloque=SimboloBloque(nombre=nombre,tipo=tipo)
        self.tabla.bloques.append(bloque)
        acciones_nodo=next((h for h in nodo.hijos if h.tipo=="ACCIONES"),None)
        if not acciones_nodo or not acciones_nodo.hijos:
            raise ErrorSemantico("SEM-11",f"Bloque '{nombre}' sin ninguna ACCION")
        for a in acciones_nodo.hijos:
            if a.tipo=="ACCION":
                hojas=[h.valor for h in a.hijos if h.es_hoja() and h.valor not in ("ACCION",":",";")] 
                bloque.acciones.append(" ".join(hojas))
