# eiez-lang/src/eiez/simulator.py
"""
Simulador de circuitos EIEZ — statevector correto.
Suporta: H, X, Y, Z, RX, RY, RZ, CX, CZ, Measure, If, For
"""

from __future__ import annotations
import cmath, math, random
from typing import Dict, List, Tuple

I = complex(0, 1)

def _h():
    s = 1/math.sqrt(2)
    return [[s, s], [s, -s]]

def _rx(t): c,s=math.cos(t/2),math.sin(t/2); return [[c,-I*s],[-I*s,c]]
def _ry(t): c,s=math.cos(t/2),math.sin(t/2); return [[c,-s],[s,c]]
def _rz(t): return [[cmath.exp(-I*t/2),0],[0,cmath.exp(I*t/2)]]

GATES_1Q = {
    "h": _h,
    "x": lambda: [[0,1],[1,0]],
    "y": lambda: [[0,-I],[I,0]],
    "z": lambda: [[1,0],[0,-1]],
    "rx": _rx, "ry": _ry, "rz": _rz,
}


class Simulator:
    def __init__(self, n_qubits: int):
        self.n   = n_qubits
        self.dim = 2 ** n_qubits
        self.state = [complex(0)] * self.dim
        self.state[0] = complex(1)
        self.measurements: Dict[int, int] = {}

    def apply_gate(self, name: str, qubit: int, param: float = None):
        name = name.lower()
        if name not in GATES_1Q:
            print(f"  ⚠ Gate '{name}' nao suportado — pulando.")
            return
        fn = GATES_1Q[name]
        matrix = fn(param) if param is not None and name in ("rx","ry","rz") else fn()
        self._apply_1q(matrix, qubit)

    def apply_cx(self, control: int, target: int):
        new_state = [complex(0)] * self.dim
        for idx in range(self.dim):
            ctrl = (idx >> (self.n - 1 - control)) & 1
            if ctrl == 1:
                # flip target bit
                flipped = idx ^ (1 << (self.n - 1 - target))
                new_state[flipped] += self.state[idx]
            else:
                new_state[idx] += self.state[idx]
        self.state = new_state

    def apply_cz(self, control: int, target: int):
        new_state = list(self.state)
        for idx in range(self.dim):
            ctrl = (idx >> (self.n - 1 - control)) & 1
            tgt  = (idx >> (self.n - 1 - target))  & 1
            if ctrl == 1 and tgt == 1:
                new_state[idx] = -self.state[idx]
        self.state = new_state

    def measure(self, qubit: int) -> int:
        # Probabilidade de |1>
        prob1 = sum(
            abs(self.state[idx]) ** 2
            for idx in range(self.dim)
            if (idx >> (self.n - 1 - qubit)) & 1 == 1
        )
        result = 1 if random.random() < prob1 else 0
        self.measurements[qubit] = result
        # Colapso
        for idx in range(self.dim):
            if (idx >> (self.n - 1 - qubit)) & 1 != result:
                self.state[idx] = complex(0)
        # Renormaliza
        norm = math.sqrt(sum(abs(a)**2 for a in self.state))
        if norm > 1e-12:
            self.state = [a / norm for a in self.state]
        return result

    def probabilities(self) -> Dict[str, float]:
        return {
            format(i, f"0{self.n}b"): round(abs(self.state[i]) ** 2, 4)
            for i in range(self.dim)
            if abs(self.state[i]) ** 2 > 1e-6
        }

    def _apply_1q(self, matrix, qubit):
        """Aplica gate de 1 qubit pelo produto tensorial correto."""
        new_state = [complex(0)] * self.dim
        for idx in range(self.dim):
            bit  = (idx >> (self.n - 1 - qubit)) & 1
            idx0 = idx & ~(1 << (self.n - 1 - qubit))   # qubit = 0
            idx1 = idx |  (1 << (self.n - 1 - qubit))   # qubit = 1
            # Contribuicao de idx0 (bit=0) para idx0 e idx1
            if bit == 0:
                new_state[idx0] += matrix[0][0] * self.state[idx]
                new_state[idx1] += matrix[1][0] * self.state[idx]
            # Contribuicao de idx1 (bit=1) para idx0 e idx1
            else:
                new_state[idx0] += matrix[0][1] * self.state[idx]
                new_state[idx1] += matrix[1][1] * self.state[idx]
        self.state = new_state


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class SimRunner:
    def __init__(self, program, params: Dict[str, float]):
        self.program = program
        self.params  = params
        self.sim     = Simulator(program.qreg.size)
        self.creg    = [0] * program.creg.size

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
                self._log(f"  🔧 CX             q[{qubits[0]}], q[{qubits[1]}]")
                self.sim.apply_cx(qubits[0], qubits[1])
            elif name == "cz" and len(qubits) == 2:
                self._log(f"  🔧 CZ             q[{qubits[0]}], q[{qubits[1]}]")
                self.sim.apply_cz(qubits[0], qubits[1])
            elif len(qubits) == 1:
                label = f"{name.upper()}({param:.4f})" if param is not None else name.upper()
                self._log(f"  🔧 {label:<14} q[{qubits[0]}]")
                self.sim.apply_gate(name, qubits[0], param)
            else:
                self._log(f"  ⚠ Gate customizado '{name}' pulado na simulacao direta.")

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
            pass

    def _resolve_idx(self, qarg, loop_var, loop_val):
        reg, idx = qarg
        if isinstance(idx, str) and idx == loop_var:
            return loop_val
        return idx

    def _resolve_param(self, p):
        if isinstance(p, str):
            return self.params.get(p, 0.0)
        return float(p)

    def _log(self, msg):
        print(msg)

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
        creg_str = "".join(str(self.creg[i]) for i in range(len(self.creg)))
        print(f"  📊 creg = {creg_str}  ({int(creg_str, 2)} decimal)")
        probs = self.sim.probabilities()
        print()
        print("  ── Probabilidades do estado final ──")
        for state, prob in sorted(probs.items(), key=lambda x: -x[1]):
            bar = "█" * int(prob * 30) + "░" * (30 - int(prob * 30))
            print(f"  |{state}⟩  {bar}  {prob*100:5.1f}%")
        print()
        print("=" * 56)
        print()
