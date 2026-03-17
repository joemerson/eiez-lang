# eiez-lang/src/eiez/simulator.py
"""
Simulador de circuitos EIEZ/QASM — visualização no terminal.

Simula qubits usando vetores de estado (statevector).
Não é física real, mas é matematicamente correto para circuitos pequenos.

Suporta: H, X, Y, Z, RX, RY, RZ, CX, CZ, Measure, If
"""

from __future__ import annotations
import cmath, math, random
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
I = complex(0, 1)

# Gates de 1 qubit — matrizes 2x2
GATES_1Q: Dict[str, List[List[complex]]] = {
    "h":  [[1/math.sqrt(2),  1/math.sqrt(2)],
           [1/math.sqrt(2), -1/math.sqrt(2)]],
    "x":  [[0, 1], [1, 0]],
    "y":  [[0, -I], [I, 0]],
    "z":  [[1, 0], [0, -1]],
}


def rx_matrix(theta: float):
    c, s = math.cos(theta/2), math.sin(theta/2)
    return [[c, -I*s], [-I*s, c]]

def ry_matrix(theta: float):
    c, s = math.cos(theta/2), math.sin(theta/2)
    return [[c, -s], [s, c]]

def rz_matrix(theta: float):
    return [[cmath.exp(-I*theta/2), 0], [0, cmath.exp(I*theta/2)]]


# ---------------------------------------------------------------------------
# Simulador
# ---------------------------------------------------------------------------

class Simulator:
    def __init__(self, n_qubits: int):
        self.n   = n_qubits
        self.dim = 2 ** n_qubits
        # Estado inicial: |000...0>
        self.state = [complex(0)] * self.dim
        self.state[0] = complex(1)
        self.measurements: Dict[int, int] = {}   # qubit -> resultado medido

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def apply_gate(self, name: str, qubit: int, param: float = None):
        """Aplica gate de 1 qubit."""
        name = name.lower()
        if   name == "rx": matrix = rx_matrix(param or 0)
        elif name == "ry": matrix = ry_matrix(param or 0)
        elif name == "rz": matrix = rz_matrix(param or 0)
        elif name in GATES_1Q: matrix = GATES_1Q[name]
        else:
            print(f"  ⚠ Gate '{name}' não suportado na simulação — pulando.")
            return
        self._apply_1q(matrix, qubit)

    def apply_cx(self, control: int, target: int):
        """CNOT — entrelaçamento."""
        self._apply_2q_controlled("x", control, target)

    def apply_cz(self, control: int, target: int):
        """CZ gate."""
        self._apply_2q_controlled("z", control, target)

    def measure(self, qubit: int) -> int:
        """Mede um qubit, colapsa o estado."""
        # Probabilidade de medir |1>
        prob1 = sum(
            abs(self.state[idx]) ** 2
            for idx in range(self.dim)
            if (idx >> (self.n - 1 - qubit)) & 1 == 1
        )
        result = 1 if random.random() < prob1 else 0
        self.measurements[qubit] = result
        # Colapso
        norm = 0.0
        for idx in range(self.dim):
            bit = (idx >> (self.n - 1 - qubit)) & 1
            if bit != result:
                self.state[idx] = complex(0)
            else:
                norm += abs(self.state[idx]) ** 2
        if norm > 1e-12:
            sqrt_norm = math.sqrt(norm)
            self.state = [a / sqrt_norm for a in self.state]
        return result

    def probabilities(self) -> Dict[str, float]:
        """Retorna probabilidade de cada estado base."""
        return {
            format(i, f"0{self.n}b"): round(abs(self.state[i]) ** 2, 6)
            for i in range(self.dim)
            if abs(self.state[i]) ** 2 > 1e-8
        }

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _apply_1q(self, matrix, qubit):
        new_state = [complex(0)] * self.dim
        for idx in range(self.dim):
            bit = (idx >> (self.n - 1 - qubit)) & 1
            idx0 = idx & ~(1 << (self.n - 1 - qubit))
            idx1 = idx |  (1 << (self.n - 1 - qubit))
            if bit == 0:
                new_state[idx0] += matrix[0][0] * self.state[idx0]
                new_state[idx1] += matrix[1][0] * self.state[idx0]
            else:
                new_state[idx0] += matrix[0][1] * self.state[idx1]
                new_state[idx1] += matrix[1][1] * self.state[idx1]
        self.state = new_state

    def _apply_2q_controlled(self, gate_name, control, target):
        new_state = list(self.state)
        for idx in range(self.dim):
            ctrl_bit = (idx >> (self.n - 1 - control)) & 1
            if ctrl_bit == 1:
                tgt_bit  = (idx >> (self.n - 1 - target)) & 1
                idx_flip = idx ^ (1 << (self.n - 1 - target))
                if gate_name == "x":
                    new_state[idx_flip] = self.state[idx]
                    new_state[idx]      = self.state[idx_flip] if tgt_bit == 0 else self.state[idx]
                elif gate_name == "z":
                    if tgt_bit == 1:
                        new_state[idx] = -self.state[idx]
        self.state = new_state


# ---------------------------------------------------------------------------
# Runner — executa IR no simulador
# ---------------------------------------------------------------------------

class SimRunner:
    def __init__(self, program, params: Dict[str, float]):
        self.program = program
        self.params  = params
        self.sim     = Simulator(program.qreg.size)
        self.creg    = [0] * program.creg.size
        self.log: List[str] = []

    def run(self):
        self._banner()
        for stmt in self.program.body:
            self._exec(stmt)
        self._show_results()

    def _exec(self, stmt, loop_var=None, loop_val=None):
        n = stmt.__class__.__name__

        if n == "GateCall":
            name   = stmt.name.lower()
            qubits = [self._resolve_idx(q, loop_var, loop_val) for q in stmt.qargs]
            param  = self._resolve_param(stmt.params[0]) if stmt.params else None

            if name == "cx" and len(qubits) == 2:
                self._log_gate("CX", qubits)
                self.sim.apply_cx(qubits[0], qubits[1])
            elif name == "cz" and len(qubits) == 2:
                self._log_gate("CZ", qubits)
                self.sim.apply_cz(qubits[0], qubits[1])
            elif len(qubits) == 1:
                label = f"{name.upper()}({param:.4f})" if param is not None else name.upper()
                self._log_gate(label, qubits)
                self.sim.apply_gate(name, qubits[0], param)
            else:
                print(f"  ⚠ Gate customizado '{name}' — pulado na simulação.")

        elif n == "Measure":
            qi = self._resolve_idx(stmt.qarg, loop_var, loop_val)
            ci = stmt.carg[1]
            result = self.sim.measure(qi)
            self.creg[ci] = result
            self._log(f"  📏 measure q[{qi}] -> c[{ci}] = {result}")

        elif n == "ForLoop":
            self._log(f"\n  🔄 FOR {stmt.var} in {stmt.start}..{stmt.end - 1}")
            for i in range(stmt.start, stmt.end):
                for s in stmt.body:
                    self._exec(s, stmt.var, i)

        elif n == "IfStmt":
            cond_val = self.creg[stmt.index]
            if cond_val == stmt.value:
                self._log(f"  ✓ if c[{stmt.index}]=={stmt.value} → TRUE")
                self._exec(stmt.body)
            else:
                self._log(f"  ✗ if c[{stmt.index}]=={stmt.value} → FALSE (c={cond_val})")

        elif n == "OptimizeStmt":
            val = self.params.get(stmt.varname, 0.0)
            self._log(f"  ⚙ optimize {stmt.varname} [{stmt.metric}] = {val:.4f}")

        elif n == "GateDecl":
            pass  # definições são ignoradas na execução direta

    def _resolve_idx(self, qarg, loop_var, loop_val):
        reg, idx = qarg
        if isinstance(idx, str) and idx == loop_var:
            return loop_val
        return idx

    def _resolve_param(self, p):
        if isinstance(p, str):
            return self.params.get(p, 0.0)
        return float(p)

    def _log_gate(self, name, qubits):
        q_str = ", ".join(f"q[{q}]" for q in qubits)
        self._log(f"  🔧 {name:<14} {q_str}")

    def _log(self, msg):
        print(msg)
        self.log.append(msg)

    def _banner(self):
        n = self.program.qreg.size
        print()
        print("=" * 56)
        print(f"  EIEZ Simulator — {n} qubit{'s' if n > 1 else ''}")
        print(f"  qreg {self.program.qreg.name}[{n}]  |  creg {self.program.creg.name}[{self.program.creg.size}]")
        print("=" * 56)
        print(f"  Estado inicial: |{'0' * n}⟩")
        print()
        print("  ── Executando circuito ──")

    def _show_results(self):
        print()
        print("  ── Resultados ──")

        # Medições clássicas
        creg_str = "".join(str(self.creg[i]) for i in range(len(self.creg)))
        print(f"  📊 creg = {creg_str}  ({int(creg_str, 2)} decimal)")

        # Probabilidades do estado quântico
        probs = self.sim.probabilities()
        print()
        print("  ── Probabilidades do estado final ──")
        n = self.program.qreg.size
        for state, prob in sorted(probs.items(), key=lambda x: -x[1]):
            bar_len = int(prob * 30)
            bar     = "█" * bar_len + "░" * (30 - bar_len)
            print(f"  |{state}⟩  {bar}  {prob*100:5.1f}%")

        print()
        print("=" * 56)
        print()
