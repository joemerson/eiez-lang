# src/eiez/optimizer_interface.py
"""
Interface de Otimização da linguagem EIEZ.

─────────────────────────────────────────────────────────────────────────────
CAMADA DE ABSTRAÇÃO — O compilador EIEZ nunca chama motores internos
diretamente. Ele sempre passa pela interface OptimizerBackend definida aqui.

Isso garante:
  1. A linguagem funciona 100% independente de qualquer motor externo.
  2. O motor real (ZIE ou outro) pode ser trocado sem tocar no compilador.
  3. O código-fonte da linguagem não expõe detalhes do motor.
─────────────────────────────────────────────────────────────────────────────

Hierarquia de backends disponíveis:
  OptimizerBackend      ← ABC (interface pura)
  ├── NullBackend       ← padrão, retorna zero; nunca falha
  └── ZIEBackend        ← motor interno; importado *somente* se disponível
"""

from __future__ import annotations

import abc
from typing import Dict, List, Tuple

from .ir import ProgramIR, OptimizeStmt, GateDecl, ForLoop

QArg = Tuple[str, int]


# ---------------------------------------------------------------------------
# Interface pública (ABC)
# ---------------------------------------------------------------------------

class OptimizerBackend(abc.ABC):
    """
    Contrato que qualquer backend de otimização deve implementar.

    O compilador só conhece este ABC — nunca o backend concreto.
    """

    @abc.abstractmethod
    def compute(self, qargs: List[QArg], metric: str) -> float:
        """
        Recebe a lista de qubits afetados e o nome da métrica.
        Deve retornar um float que será injetado como parâmetro de gate.

        Nunca deve lançar exceção para o compilador — trate internamente.
        """
        ...

    def apply_all(self, program: ProgramIR) -> Dict[str, float]:
        """
        Percorre o IR completo e resolve todos os OptimizeStmt.

        Retorna dicionário  { varname: float_value }.
        Chamado pelo QASMGenerator antes da geração de código.
        """
        result: Dict[str, float] = {}
        self._walk(program.body, result)
        return result

    # ------------------------------------------------------------------
    # Implementação interna de travessia — não precisa ser sobrescrita
    # ------------------------------------------------------------------

    def _walk(self, stmts: list, result: Dict[str, float]) -> None:
        for stmt in stmts:
            name = stmt.__class__.__name__

            if name == "OptimizeStmt":
                val = self._safe_compute(stmt)
                result[stmt.varname] = val

            elif name == "GateDecl":
                self._walk(stmt.body, result)

            elif name == "ForLoop":
                self._walk(stmt.body, result)

    def _safe_compute(self, stmt: OptimizeStmt) -> float:
        try:
            return float(self.compute(stmt.qargs, stmt.metric))
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Backend padrão — sem dependências externas, sempre seguro
# ---------------------------------------------------------------------------

class NullBackend(OptimizerBackend):
    """
    Backend neutro. Retorna 0.0 para qualquer métrica.

    Usado quando nenhum motor externo está configurado.
    Permite compilar e gerar QASM válido mesmo sem backend real.
    """

    def compute(self, qargs: List[QArg], metric: str) -> float:
        return 0.0


# ---------------------------------------------------------------------------
# Backend ZIE — carregado de forma lazy e isolada
# ---------------------------------------------------------------------------

class ZIEBackend(OptimizerBackend):
    """
    Backend que delega ao motor ZIE interno.

    O motor ZIE é importado dentro deste método — o restante do compilador
    nunca importa zie_core diretamente. Se o módulo não estiver disponível,
    o backend cai silenciosamente para NullBackend.

    Não há referência a 'zie_core' fora desta classe.
    """

    # Mapeamento: nome de métrica EIEZ → identificador interno do motor
    _METRIC_MAP = {
        "coherence":   "coherence",
        "stability":   "stability",
        "balance":     "balance",
        "uniformity":  "uniformity",
        # Aliases do sistema de origem (transparentes para o usuário)
        "eie_ratio":   "coherence",
        "tau_max":     "stability",
    }

    def __init__(self) -> None:
        self._engine = self._load_engine()

    @staticmethod
    def _load_engine():
        """Importa o motor interno de forma isolada."""
        try:
            # Importação completamente encapsulada aqui
            from . import _zie_engine as engine  # módulo interno renomeado
            return engine
        except ImportError:
            return None

    def compute(self, qargs: List[QArg], metric: str) -> float:
        if self._engine is None:
            return 0.0

        mapped_metric = self._METRIC_MAP.get(metric.lower(), metric.lower())

        try:
            value = self._engine.run(qargs, mapped_metric)
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Fábrica pública — ponto de entrada único para o compilador
# ---------------------------------------------------------------------------

def create_optimizer(backend: str = "auto") -> OptimizerBackend:
    """
    Cria e retorna o backend de otimização apropriado.

    backend:
        "auto"  — tenta ZIEBackend; se indisponível, usa NullBackend
        "null"  — sempre NullBackend (sem motor externo)
        "zie"   — força ZIEBackend (falha se motor ausente)

    O compilador chama apenas esta função — nunca instancia backends diretamente.
    """
    if backend == "null":
        return NullBackend()

    if backend == "zie":
        b = ZIEBackend()
        if b._engine is None:
            raise RuntimeError("Backend ZIE solicitado mas motor não encontrado.")
        return b

    # "auto"
    b = ZIEBackend()
    return b if b._engine is not None else NullBackend()
