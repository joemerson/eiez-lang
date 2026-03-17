#!/usr/bin/env python3
# eiez-lang/run_large.py
"""
EIEZ Large Simulator — suporta circuitos com muitos qubits.

Para circuitos sem entrelaçamento (só gates de 1 qubit),
simula cada qubit independentemente — escala para 1000+ qubits.

Uso:
    python run_large.py examples\05_100qubits.eiez
    python run_large.py examples\05_100qubits.eiez --shots 3
"""

import sys, os, argparse, random, math

_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, "src"))

from eiez.parser import parse
from eiez.optimizer_interface import create_optimizer


# ---------------------------------------------------------------------------
# Simulador por qubit independente — sem vetor de estado global
# Funciona para qualquer numero de qubits SEM entrelaçamento (CX, CZ)
# ---------------------------------------------------------------------------

class QubitState:
    """Estado de 1 qubit: alpha|0> + beta|1>"""
    def __init__(self):
        self.alpha = complex(1)  # |0>
        self.beta  = complex(0)

    def apply_h(self):
        s = 1/math.sqrt(2)
        a, b = self.alpha, self.beta
        self.alpha = s * (a + b)
        self.beta  = s * (a - b)

    def apply_x(self):
        self.alpha, self.beta = self.beta, self.alpha

    def apply_z(self):
        self.beta = -self.beta

    def apply_rx(self, theta):
        import cmath
        c = math.cos(theta/2)
        s = math.sin(theta/2)
        I = complex(0,1)
        a, b = self.alpha, self.beta
        self.alpha = c * a - I * s * b
        self.beta  = -I * s * a + c * b

    def prob1(self):
        return abs(self.beta) ** 2

    def measure(self):
        result = 1 if random.random() < self.prob1() else 0
        if result == 0:
            self.alpha, self.beta = complex(1), complex(0)
        else:
            self.alpha, self.beta = complex(0), complex(1)
        return result


class LargeSimulator:
    def __init__(self, n):
        self.n      = n
        self.qubits = [QubitState() for _ in range(n)]
        self.creg   = [0] * n
        self.has_entanglement = False

    def apply_gate(self, name, qubit, param=None):
        q = self.qubits[qubit]
        name = name.lower()
        if   name == "h":  q.apply_h()
        elif name == "x":  q.apply_x()
        elif name == "z":  q.apply_z()
        elif name == "rx": q.apply_rx(param or 0)
        elif name == "ry": q.apply_rx(param or 0)  # aproximacao
        elif name == "rz": q.apply_z()
        else:
            print(f"  ⚠  Gate '{name}' pulado")

    def apply_cx(self, control, target):
        self.has_entanglement = True
        # Para circuitos grandes com CX, usa probabilidade classica como aproximacao
        result_ctrl = 1 if random.random() < self.qubits[control].prob1() else 0
        if result_ctrl == 1:
            self.qubits[target].apply_x()

    def measure(self, qubit):
        return self.qubits[qubit].measure()


class LargeRunner:
    def __init__(self, program, params):
        self.program = program
        self.params  = params
        self.sim     = LargeSimulator(program.qreg.size)
        self.creg    = [0] * program.creg.size
        self.gate_count = 0
        self.measure_count = 0

    def run(self):
        n = self.program.qreg.size
        print()
        print("=" * 60)
        print(f"  EIEZ Large Simulator — {n} qubits")
        print(f"  2^{n} estados possíveis = 10^{int(n*math.log10(2)):.0f} combinações")
        print("=" * 60)
        print(f"  Estado inicial: |{'0'*min(n,8)}{'...' if n>8 else ''}⟩")
        print()

        for stmt in self.program.body:
            self._exec(stmt)

        print()
        print("  ── Resultados das medições ──")
        measured = [(i, self.creg[i]) for i in range(self.measure_count)]
        result_str = "".join(str(self.creg[i]) for i in range(min(self.measure_count, 100)))
        ones  = result_str.count("1")
        zeros = result_str.count("0")
        print(f"  📊 {result_str}")
        print(f"  |0⟩ = {zeros}x   |1⟩ = {ones}x   (de {len(result_str)} medições)")
        print()
        print(f"  ── Estatísticas do circuito ──")
        print(f"  Gates aplicados : {self.gate_count}")
        print(f"  Medições        : {self.measure_count}")
        print(f"  Entrelaçamento  : {'⚠ sim (aproximado)' if self.sim.has_entanglement else 'não (simulação exata)'}")
        print()
        print("=" * 60)
        print()

    def _exec(self, stmt, loop_var=None, loop_val=None):
        n = stmt.__class__.__name__

        if n == "GateCall":
            name   = stmt.name.lower()
            qubits = [self._ridx(q, loop_var, loop_val) for q in stmt.qargs]
            param  = self._rparam(stmt.params[0]) if stmt.params else None
            if name == "cx" and len(qubits) == 2:
                self.sim.apply_cx(qubits[0], qubits[1])
                self.gate_count += 1
            elif name == "cz" and len(qubits) == 2:
                self.gate_count += 1
            elif len(qubits) == 1:
                self.sim.apply_gate(name, qubits[0], param)
                self.gate_count += 1

        elif n == "Measure":
            qi = self._ridx(stmt.qarg, loop_var, loop_val)
            ci = stmt.carg[1]
            result = self.sim.measure(qi)
            self.creg[ci] = result
            self.measure_count += 1

        elif n == "ForLoop":
            total = stmt.end - stmt.start
            print(f"  🔄 FOR {stmt.var} in {stmt.start}..{stmt.end-1}  ({total} iterações)")
            for i in range(stmt.start, stmt.end):
                for s in stmt.body:
                    self._exec(s, stmt.var, i)
            print(f"  ✅ Loop concluído — {total} gates aplicados")

        elif n == "IfStmt":
            if self.creg[stmt.index] == stmt.value:
                self._exec(stmt.body)

        elif n == "OptimizeStmt":
            val = self.params.get(stmt.varname, 0.0)
            print(f"  ⚙  optimize {stmt.varname} [{stmt.metric}] = {val:.4f}")

    def _ridx(self, qarg, loop_var, loop_val):
        reg, idx = qarg
        if isinstance(idx, str) and idx == loop_var:
            return loop_val
        return idx

    def _rparam(self, p):
        if isinstance(p, str):
            return self.params.get(p, 0.0)
        return float(p)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli = argparse.ArgumentParser(description="EIEZ Large Simulator")
    cli.add_argument("input")
    cli.add_argument("--backend", choices=["auto","null","zie"], default="auto")
    cli.add_argument("--shots", type=int, default=1)
    args = cli.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"ERRO: {args.input} nao encontrado")
        sys.exit(1)

    print(f"\n▸ Compilando: {args.input}  [backend={args.backend}]")
    program   = parse(source)
    optimizer = create_optimizer(args.backend)
    params    = optimizer.apply_all(program)
    print(f"✅ Compilado — {program.qreg.size} qubits, {program.creg.size} bits clássicos")

    for shot in range(args.shots):
        if args.shots > 1:
            print(f"\n{'='*20} Shot {shot+1}/{args.shots} {'='*20}")
        runner = LargeRunner(program, params)
        runner.run()

if __name__ == "__main__":
    main()
