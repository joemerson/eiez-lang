# src/eiez/generator_qasm.py
"""
Gerador de OpenQASM 2.0 para a linguagem EIEZ.

Recebe um ProgramIR e um OptimizerBackend (pela interface).
Nunca importa zie_core nem qualquer motor interno diretamente.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .ir import (
    ProgramIR, GateCall, GateDecl, Measure,
    IfStmt, ForLoop, OptimizeStmt
)
from .optimizer_interface import OptimizerBackend, NullBackend

QArg = Tuple[str, int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_qarg(qarg: QArg) -> str:
    reg, idx = qarg
    return f"{reg}[{idx}]"


def _fmt_param(param, table: Dict[str, float]) -> str:
    if isinstance(param, str) and param in table:
        return f"{table[param]:.4f}"
    if isinstance(param, float):
        return f"{param:.4f}"
    if isinstance(param, int):
        return str(param)
    return str(param)


# ---------------------------------------------------------------------------
# Gerador principal
# ---------------------------------------------------------------------------

class QASMGenerator:
    """
    Converte ProgramIR → string OpenQASM 2.0.

    Dependências:
        program   — ProgramIR (saída do parser)
        optimizer — OptimizerBackend (qualquer implementação da interface)
                    Padrão: NullBackend (nunca falha, não precisa de motor externo)
    """

    def __init__(
        self,
        program: ProgramIR,
        optimizer: OptimizerBackend | None = None,
    ):
        self.program   = program
        self.optimizer = optimizer if optimizer is not None else NullBackend()
        self.lines:  List[str] = []
        self._gates: List[GateDecl] = []

        # Tabela de parâmetros resolvidos: { varname -> float }
        self._params: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    def generate(self) -> str:
        # 1. Resolver todos os optimize antes de emitir qualquer linha
        self._params = self.optimizer.apply_all(self.program)

        # 2. Cabeçalho
        out: List[str] = [
            f"OPENQASM {self.program.version:.1f};",
            'include "qelib1.inc";',
            f"qreg {self.program.qreg.name}[{self.program.qreg.size}];",
            f"creg {self.program.creg.name}[{self.program.creg.size}];",
            "",
        ]

        # 3. Definições de gates customizados (GateDecl)
        for stmt in self.program.body:
            if isinstance(stmt, GateDecl):
                self._emit_gate_decl(stmt)

        if self._gates:
            out.append("")

        # 4. Corpo principal
        for stmt in self.program.body:
            if not isinstance(stmt, GateDecl):
                self._visit(stmt)

        out.extend(self.lines)
        return "\n".join(line for line in out if line.strip() or line == "")

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _visit(self, stmt) -> None:
        dispatch = {
            "GateCall":     self._emit_gate_call,
            "Measure":      self._emit_measure,
            "IfStmt":       self._emit_if,
            "ForLoop":      self._emit_for_loop,
            "OptimizeStmt": self._emit_optimize_comment,
        }
        handler = dispatch.get(stmt.__class__.__name__)
        if handler:
            handler(stmt)
        else:
            self.lines.append(f"// <unhandled {stmt.__class__.__name__}>")

    # ------------------------------------------------------------------
    # Emissores
    # ------------------------------------------------------------------

    def _emit_gate_decl(self, stmt: GateDecl) -> None:
        params_str = ", ".join(stmt.params)
        qargs_str  = ", ".join(stmt.qargs)
        self.lines.append(f"gate {stmt.name.lower()}({params_str}) {qargs_str} {{")

        inner = QASMGenerator(self.program, self.optimizer)
        inner._params = self._params
        for s in stmt.body:
            inner._visit(s)
        for line in inner.lines:
            self.lines.append("    " + line.strip())

        self.lines.append("}")
        self._gates.append(stmt)

    def _emit_gate_call(self, stmt: GateCall) -> None:
        name       = stmt.name.lower()
        params_str = (
            f"({', '.join(_fmt_param(p, self._params) for p in stmt.params)})"
            if stmt.params else ""
        )
        qargs_str = ", ".join(_fmt_qarg(q) for q in stmt.qargs)
        self.lines.append(f"{name}{params_str} {qargs_str};")

    def _emit_measure(self, stmt: Measure) -> None:
        self.lines.append(
            f"measure {_fmt_qarg(stmt.qarg)} -> {_fmt_qarg(stmt.carg)};"
        )

    def _emit_optimize_comment(self, stmt: OptimizeStmt) -> None:
        val = self._params.get(stmt.varname, 0.0)
        qargs_str = ", ".join(_fmt_qarg(q) for q in stmt.qargs)
        self.lines.append(
            f"// optimize {stmt.varname} [{stmt.metric}] on {qargs_str} -> {val:.4f}"
        )

    def _emit_for_loop(self, stmt: ForLoop) -> None:
        self.lines.append(f"// FOR {stmt.var} in {stmt.start}..{stmt.end - 1}")
        for i in range(stmt.start, stmt.end):
            self.lines.append(f"// ITER {stmt.var}={i}")
            for inner in stmt.body:
                self._visit(self._substitute_var(inner, stmt.var, i))

    def _emit_if(self, stmt: IfStmt) -> None:
        inner = stmt.body
        if isinstance(inner, GateCall):
            args = ", ".join(_fmt_qarg(q) for q in inner.qargs)
            if inner.params:
                p = _fmt_param(inner.params[0], self._params)
                self.lines.append(
                    f"if({stmt.creg}[{stmt.index}]=={stmt.value})"
                    f" {inner.name.lower()}({p}) {args};"
                )
            else:
                self.lines.append(
                    f"if({stmt.creg}[{stmt.index}]=={stmt.value})"
                    f" {inner.name.lower()} {args};"
                )
        else:
            self.lines.append(
                f"// if(...) <unsupported inner: {inner.__class__.__name__}>"
            )

    # ------------------------------------------------------------------
    # Substituição de variável de loop
    # ------------------------------------------------------------------

    def _substitute_var(self, stmt, var: str, value: int):
        if isinstance(stmt, GateCall):
            new_qargs = [
                (reg, value if isinstance(idx, str) and idx == var else idx)
                for reg, idx in stmt.qargs
            ]
            return GateCall(stmt.name, stmt.params, new_qargs)
        return stmt


# ---------------------------------------------------------------------------
# Função de conveniência
# ---------------------------------------------------------------------------

def generate_qasm(
    program: ProgramIR,
    optimizer: OptimizerBackend | None = None,
) -> str:
    """
    Gera OpenQASM 2.0 a partir de um ProgramIR.

    optimizer é opcional — se omitido, usa NullBackend (sem motor externo).
    """
    return QASMGenerator(program, optimizer).generate()
