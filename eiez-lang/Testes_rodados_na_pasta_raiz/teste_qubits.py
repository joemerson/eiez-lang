#!/usr/bin/env python3
"""
EIEZ — Teste da Verdade
Joemerson da Silva Lima | Cuiabá, MT | 2026
Roda os 4 testes direto, sem pausas.
"""

import math, cmath, random, time

I = complex(0, 1)

class SimuladorReal:
    def __init__(self, n):
        self.n = n
        self.dim = 2 ** n
        self.state = [complex(0)] * self.dim
        self.state[0] = complex(1)

    def H(self, qubit):
        s = 1 / math.sqrt(2)
        new = [complex(0)] * self.dim
        for idx in range(self.dim):
            bit  = (idx >> (self.n - 1 - qubit)) & 1
            idx0 = idx & ~(1 << (self.n - 1 - qubit))
            idx1 = idx |  (1 << (self.n - 1 - qubit))
            if bit == 0:
                new[idx0] += s * self.state[idx]
                new[idx1] += s * self.state[idx]
            else:
                new[idx0] +=  s * self.state[idx]
                new[idx1] += -s * self.state[idx]
        self.state = new

    def CX(self, ctrl, tgt):
        new = [complex(0)] * self.dim
        for idx in range(self.dim):
            c = (idx >> (self.n - 1 - ctrl)) & 1
            if c == 1:
                new[idx ^ (1 << (self.n - 1 - tgt))] += self.state[idx]
            else:
                new[idx] += self.state[idx]
        self.state = new

    def medir(self, qubit):
        prob1 = sum(abs(self.state[i]) ** 2
                    for i in range(self.dim)
                    if (i >> (self.n - 1 - qubit)) & 1 == 1)
        r = 1 if random.random() < prob1 else 0
        for i in range(self.dim):
            if (i >> (self.n - 1 - qubit)) & 1 != r:
                self.state[i] = complex(0)
        norm = math.sqrt(sum(abs(a) ** 2 for a in self.state))
        if norm > 1e-12:
            self.state = [a / norm for a in self.state]
        return r


class QubitVirtual:
    def __init__(self):
        self.alpha = complex(1)
        self.beta  = complex(0)

    def H(self):
        s = 1 / math.sqrt(2)
        a, b = self.alpha, self.beta
        self.alpha = s * (a + b)
        self.beta  = s * (a - b)

    def RX(self, theta):
        c = math.cos(theta / 2)
        s = math.sin(theta / 2)
        a, b = self.alpha, self.beta
        self.alpha = c * a - I * s * b
        self.beta  = -I * s * a + c * b

    def medir(self):
        return 1 if random.random() < abs(self.beta) ** 2 else 0


# ── TESTE 1 ──────────────────────────────────────────────
print()
print("██████████████████████████████████████████████████████")
print("  EIEZ Lang — Teste da Verdade")
print("  Joemerson da Silva Lima | Cuiabá, MT | 2026")
print("██████████████████████████████████████████████████████")
print()
print("╔══════════════════════════════════════════════════════╗")
print("║  TESTE 1 — Bell State (emaranhamento real)          ║")
print("║  Esperado: APENAS |00⟩ ou |11⟩, nunca |01⟩ |10⟩    ║")
print("╚══════════════════════════════════════════════════════╝")

c = {"00":0,"01":0,"10":0,"11":0}
for _ in range(500):
    sim = SimuladorReal(2)
    sim.H(0); sim.CX(0, 1)
    r0 = sim.medir(0); r1 = sim.medir(1)
    c[f"{r0}{r1}"] += 1

print(f"\n  500 medicoes:\n")
for k, v in sorted(c.items()):
    pct = v / 500 * 100
    bar = "█" * int(pct / 2)
    ok  = "✓ OK" if k in ("00","11") else ("❌ ERRO" if v > 0 else "")
    print(f"  |{k}⟩  {bar:<26} {pct:5.1f}%  {ok}")
print(f"\n  {'✅ Emaranhamento CORRETO' if (c['01']+c['10'])==0 else '❌ QUEBRADO'}")

# ── TESTE 2 ──────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════╗")
print("║  TESTE 2 — Limite do Simulador REAL (statevector)   ║")
print("║  Cada qubit DOBRA a memoria — onde sua RAM explode?  ║")
print("╚══════════════════════════════════════════════════════╝")
print()
print(f"  {'Qubits':<8} {'Amplitudes':<15} {'Memoria':<12} {'Tempo':<10} Status")
print(f"  {'-'*62}")

for n in [5, 10, 15, 18, 20, 22, 24, 25, 26, 28, 30]:
    amp    = 2 ** n
    mem_mb = amp * 16 / (1024 ** 2)
    if mem_mb > 14000:
        print(f"  {n:<8} {amp:<15,} {mem_mb:>8.0f} MB   {'--':<10} ❌ Precisaria de {mem_mb/1024:.0f} GB RAM")
        continue
    try:
        t0  = time.perf_counter()
        sim = SimuladorReal(n)
        for q in range(min(n, 3)):
            sim.H(q)
        ms = (time.perf_counter() - t0) * 1000
        print(f"  {n:<8} {amp:<15,} {mem_mb:>8.1f} MB   {ms:>7.1f} ms   ✓")
        if ms > 25000:
            print("  → Passou de 25s. Parando.")
            break
    except MemoryError:
        print(f"  {n:<8} {amp:<15,} {mem_mb:>8.0f} MB   {'--':<10} 💥 MemoryError — RAM esgotada aqui")
        break

# ── TESTE 3 ──────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════╗")
print("║  TESTE 3 — 3000 qubits VIRTUAIS (sem emaranhamento) ║")
print("╚══════════════════════════════════════════════════════╝")
print()

N = 3000
tempos = []
for shot in range(1, 6):
    t0 = time.perf_counter()
    qubits = [QubitVirtual() for _ in range(N)]
    for q in qubits: q.H()
    for q in qubits[:10]: q.RX(math.pi / 4)
    med = [q.medir() for q in qubits]
    ms  = (time.perf_counter() - t0) * 1000
    tempos.append(ms)
    uns = sum(med)
    print(f"  Shot {shot}: {ms:7.2f} ms  |  |1⟩={uns} ({uns/N*100:.1f}%)  |0⟩={N-uns}")

print(f"\n  Media: {sum(tempos)/len(tempos):.2f} ms")
print(f"  Estados possiveis (teorico): 10^{int(3000*math.log10(2))}")
print()
print("  ⚠  Esses 3000 qubits sao INDEPENDENTES (sem emaranhamento)")
print("  ⚠  Simulador real travaria antes de 30 qubits")

# ── TESTE 4 ──────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════╗")
print("║  TESTE 4 — Real vs Virtual: a diferenca concreta    ║")
print("╚══════════════════════════════════════════════════════╝")

print("\n  REAL (H+CX, 200 shots) — com emaranhamento:")
c = {"00":0,"01":0,"10":0,"11":0}
for _ in range(200):
    sim = SimuladorReal(2)
    sim.H(0); sim.CX(0, 1)
    r0 = sim.medir(0); r1 = sim.medir(1)
    c[f"{r0}{r1}"] += 1
for k, v in sorted(c.items()):
    print(f"    |{k}⟩ {'█'*(v//4):<50} {v}")
print("    → So |00⟩ e |11⟩  ✓")

print("\n  VIRTUAL (H independente, 200 shots) — sem emaranhamento:")
c2 = {"00":0,"01":0,"10":0,"11":0}
for _ in range(200):
    q0 = QubitVirtual(); q0.H()
    q1 = QubitVirtual(); q1.H()
    r0 = q0.medir(); r1 = q1.medir()
    c2[f"{r0}{r1}"] += 1
for k, v in sorted(c2.items()):
    print(f"    |{k}⟩ {'█'*(v//4):<50} {v}")
print("    → Todos os 4 estados  ✗")

# ── VEREDICTO ─────────────────────────────────────────────
print()
print("══════════════════════════════════════════════════════")
print("  VEREDICTO FINAL")
print("══════════════════════════════════════════════════════")
print()
print("  Simulador REAL:")
print("    ✅ Emaranhamento correto")
print("    ✅ Matematica quantica exata")
print("    ❌ Limite: ~25 qubits em hardware comum")
print()
print("  Simulador VIRTUAL:")
print("    ✅ Escala para milhares de qubits")
print("    ✅ Rapido e eficiente")
print("    ❌ Sem emaranhamento")
print()
print("  Nenhum PC no mundo simula 1000+ qubits com")
print("  emaranhamento real. Isso e um limite fisico,")
print("  nao uma limitacao do seu codigo.")
print("══════════════════════════════════════════════════════")
print()
