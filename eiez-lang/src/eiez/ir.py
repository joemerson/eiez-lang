# src/eiez/ir.py
"""
IR — Intermediate Representation da linguagem EIEZ.

Fonte da verdade para todos os nós da AST.
Nenhum outro módulo redefine estruturas de dados — todos importam daqui.
"""

from __future__ import annotations
from typing import List, Optional, Union, Tuple


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class IRNode:
    """Nó base. Todos os nós herdam daqui."""

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, IRNode):
                out[k] = v.to_dict()
            elif isinstance(v, list):
                out[k] = [i.to_dict() if isinstance(i, IRNode) else i for i in v]
            else:
                out[k] = v
        return out


# ---------------------------------------------------------------------------
# Declarações de registradores
# ---------------------------------------------------------------------------

class QRegDecl(IRNode):
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


class CRegDecl(IRNode):
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

class ProgramIR(IRNode):
    """
    Raiz do programa compilado.

    Atributos públicos:
        version    — versão declarada no header EIEZ (float)
        qreg       — declaração do registrador quântico (QRegDecl)
        creg       — declaração do registrador clássico (CRegDecl)
        body       — lista de statements do programa
    """

    def __init__(
        self,
        version: float,
        qreg: Optional[QRegDecl] = None,
        creg: Optional[CRegDecl] = None,
        body: Optional[List[IRNode]] = None,
    ):
        self.version = version
        self.qreg = qreg
        self.creg = creg
        self.body: List[IRNode] = body if body is not None else []


# ---------------------------------------------------------------------------
# Tipos de argumento
# ---------------------------------------------------------------------------

# QArg é uma tupla simples (reg_name, index) para manter compatibilidade com PLY
QArg = Tuple[str, int]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

class GateCall(IRNode):
    def __init__(self, name: str, params: List, qargs: List[QArg]):
        self.name   = name
        self.params = params or []
        self.qargs  = qargs  or []


class GateDecl(IRNode):
    def __init__(self, name: str, params: List[str], qargs: List[str], body: List[IRNode]):
        self.name   = name
        self.params = params or []
        self.qargs  = qargs  or []
        self.body   = body   or []


class Measure(IRNode):
    def __init__(self, qarg: QArg, carg: QArg):
        self.qarg = qarg
        self.carg = carg


class IfStmt(IRNode):
    def __init__(self, creg: str, index: int, value: int, body: IRNode):
        self.creg  = creg
        self.index = index
        self.value = value
        self.body  = body   # statement único (ex: GateCall)


class ForLoop(IRNode):
    def __init__(self, var: str, start: int, end: int, body: List[IRNode]):
        self.var   = var
        self.start = start
        self.end   = end
        self.body  = body or []


class OptimizeStmt(IRNode):
    """
    Representa:  optimize q[0], q[1] using <metric> as <varname>;

    Atributos:
        qargs   — lista de QArg afetados
        metric  — nome da métrica ('coherence', 'stability', ...)
        varname — variável de saída onde o valor otimizado será armazenado
    """
    def __init__(self, qargs: List[QArg], metric: str, varname: str):
        self.qargs   = qargs or []
        self.metric  = metric
        self.varname = varname
