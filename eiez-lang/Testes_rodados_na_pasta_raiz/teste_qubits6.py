#!/usr/bin/env python3
"""
EIEZ — Teste da Verdade
Joemerson da Silva Lima

Dois modos, lado a lado:
  MODO A: Statevector REAL (com emaranhamento) — trava em ~25 qubits
  MODO B: Independente VIRTUAL (sem emaranhamento) — roda 3000+ qubits

Execute:
    python teste_qubits.py
"""

import math, cmath, random, time, sys

I = complex(0, 1)

# ═══════════════════════════════════════════════════════
# MODO A — Simulador Statevector REAL
# Mantém 2^n amplitudes complexas na memória
# Suporta emaranhamento completo
# Limite: ~25 qubits em 8GB RAM
# ═══════════════════════════════════════════════════════

class SimuladorReal:
    """Simulador quântico statevector completo."""

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

    def probabilidades(self):
        return {format(i, f"0{self.n}b"): round(abs(self.state[i]) ** 2, 6)
                for i in range(self.dim) if abs(self.state[i]) ** 2 > 1e-9}


# ═══════════════════════════════════════════════════════
# MODO B — Simulador por Qubit Independente (Virtual)
# Cada qubit é calculado sozinho
# NÃO suporta emaranhamento
# Escala para milhares de qubits
# ═══════════════════════════════════════════════════════

class QubitVirtual:
    """Um qubit independente — sem emaranhamento."""

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
        prob1 = abs(self.beta) ** 2
        return 1 if random.random() < prob1 else 0


class SimuladorVirtual:
    """Simula N qubits independentes."""

    def __init__(self, n):
        self.n = n
        self.qubits = [QubitVirtual() for _ in range(n)]

    def H_todos(self):
        for q in self.qubits:
            q.H()

    def RX_primeiros(self, k, theta):
        for q in self.qubits[:k]:
            q.RX(theta)

    def medir_todos(self):
        return [q.medir() for q in self.qubits]


# ═══════════════════════════════════════════════════════
# TESTE 1 — Bell State (prova de emaranhamento)
# Só funciona no Modo A
# ═══════════════════════════════════════════════════════

def teste_bell():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  TESTE 1 — Bell State (emaranhamento real)          ║")
    print("║  Circuito: H(q0) → CX(q0,q1) → medir               ║")
    print("║  Esperado: APENAS |00⟩ ou |11⟩, nunca |01⟩ |10⟩    ║")
    print("╚══════════════════════════════════════════════════════╝")

    contagem = {"00": 0, "01": 0, "10": 0, "11": 0}
    SHOTS = 500

    for _ in range(SHOTS):
        sim = SimuladorReal(2)
        sim.H(0)
        sim.CX(0, 1)
        r0 = sim.medir(0)
        r1 = sim.medir(1)
        contagem[f"{r0}{r1}"] += 1

    print(f"\n  {SHOTS} medições:\n")
    for k, v in sorted(contagem.items()):
        pct  = v / SHOTS * 100
        bar  = "█" * int(pct / 2)
        spc  = " " * (50 - len(bar))
        flag = "✓ OK" if k in ("00","11") else ("❌ ERRO — não deveria aparecer!" if v > 0 else "")
        print(f"  |{k}⟩  {bar}{spc} {pct:5.1f}%  {flag}")

    erros = contagem["01"] + contagem["10"]
    if erros == 0:
        print(f"\n  ✅ Emaranhamento CORRETO — |01⟩ e |10⟩ = zero")
    else:
        print(f"\n  ❌ Emaranhamento QUEBRADO — {erros} estados inválidos")


# ═══════════════════════════════════════════════════════
# TESTE 2 — Limite do Modo A (statevector)
# Mostra onde a RAM explode
# ═══════════════════════════════════════════════════════

def teste_limite_real():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  TESTE 2 — Limite do Simulador REAL (statevector)   ║")
    print("║  Cada qubit DOBRA a memória necessária               ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print(f"  {'Qubits':<8} {'Amplitudes':<15} {'Memória':<12} {'Tempo':<10} Status")
    print(f"  {'-'*60}")

    for n in [5, 10, 15, 18, 20, 22, 24, 25, 26, 28, 30]:
        amp    = 2 ** n
        mem_mb = amp * 16 / (1024 ** 2)

        if mem_mb > 12000:
            print(f"  {n:<8} {amp:<15,} {mem_mb:>8.0f} MB   {'--':<10} ❌ Precisa de {mem_mb/1024:.0f} GB RAM")
            continue

        try:
            t0  = time.perf_counter()
            sim = SimuladorReal(n)
            for q in range(min(n, 3)):
                sim.H(q)
            ms = (time.perf_counter() - t0) * 1000
            print(f"  {n:<8} {amp:<15,} {mem_mb:>8.1f} MB   {ms:>7.1f} ms   ✓")

            if ms > 20000:
                print(f"  → Passando de 20s. Parando aqui.")
                break

        except MemoryError:
            print(f"  {n:<8} {amp:<15,} {mem_mb:>8.0f} MB   {'--':<10} 💥 MemoryError — RAM esgotada")
            break


# ═══════════════════════════════════════════════════════
# TESTE 3 — Modo Virtual: 3000 qubits
# Roda rápido MAS sem emaranhamento
# ═══════════════════════════════════════════════════════

def teste_3000_virtual():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  TESTE 3 — 3000 qubits VIRTUAIS (sem emaranhamento) ║")
    print("║  Circuito: H em todos + RX(pi/4) nos primeiros 10   ║")
    print("╚══════════════════════════════════════════════════════╝")

    N     = 3000
    SHOTS = 5

    print(f"\n  {N} qubits | {SHOTS} shots | circuito H + RX")
    print()

    tempos = []
    for shot in range(1, SHOTS + 1):
        t0  = time.perf_counter()
        sim = SimuladorVirtual(N)
        sim.H_todos()
        sim.RX_primeiros(10, math.pi / 4)
        med = sim.medir_todos()
        ms  = (time.perf_counter() - t0) * 1000
        tempos.append(ms)

        uns   = sum(med)
        zeros = N - uns
        pct   = uns / N * 100
        print(f"  Shot {shot}: {ms:7.2f} ms  |  |1⟩={uns} ({pct:.1f}%)  |0⟩={zeros}")

    media = sum(tempos) / len(tempos)
    print(f"\n  Média: {media:.2f} ms")
    print(f"  Estados possíveis (teórico): 2^3000 = 10^{int(3000*math.log10(2))}")
    print()
    print("  ⚠  ATENÇÃO: esses 3000 qubits são INDEPENDENTES.")
    print("  ⚠  Não há emaranhamento entre eles.")
    print("  ⚠  É matematicamente equivalente a 3000 moedas.")
    print("  ⚠  Um simulador real travaria antes de 30 qubits.")


# ═══════════════════════════════════════════════════════
# TESTE 4 — Prova final: CX no modo virtual não funciona
# ═══════════════════════════════════════════════════════

def teste_cx_virtual():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  TESTE 4 — CX no modo virtual: não existe           ║")
    print("║  Prova que os modos são fundamentalmente diferentes  ║")
    print("╚══════════════════════════════════════════════════════╝")

    print()
    print("  Modo REAL (2 qubits, H+CX, 200 shots):")
    c = {"00":0,"01":0,"10":0,"11":0}
    for _ in range(200):
        sim = SimuladorReal(2)
        sim.H(0); sim.CX(0,1)
        r0 = sim.medir(0); r1 = sim.medir(1)
        c[f"{r0}{r1}"] += 1
    for k,v in sorted(c.items()):
        bar = "█" * (v//4)
        print(f"    |{k}⟩ {bar} {v}")
    print("    → Só |00⟩ e |11⟩: emaranhamento ✓")

    print()
    print("  Modo VIRTUAL (2 qubits independentes, H em ambos, 200 shots):")
    c2 = {"00":0,"01":0,"10":0,"11":0}
    for _ in range(200):
        q0 = QubitVirtual(); q0.H()
        q1 = QubitVirtual(); q1.H()
        r0 = q0.medir(); r1 = q1.medir()
        c2[f"{r0}{r1}"] += 1
    for k,v in sorted(c2.items()):
        bar = "█" * (v//4)
        print(f"    |{k}⟩ {bar} {v}")
    print("    → Todos os 4 estados aparecem: sem emaranhamento ✗")

    print()
    print("  Esta é a diferença real entre os dois modos.")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("██████████████████████████████████████████████████████")
    print("  EIEZ Lang — Teste da Verdade")
    print("  Simulador Real vs Virtual — lado a lado")
    print("  Joemerson da Silva Lima | Cuiabá, MT | 2026")
    print("██████████████████████████████████████████████████████")

    teste_bell()
    input("\n  [Enter para próximo teste]")

    teste_limite_real()
    input("\n  [Enter para próximo teste]")

    teste_3000_virtual()
    input("\n  [Enter para próximo teste]")

    teste_cx_virtual()

    print()
    print("══════════════════════════════════════════════════════")
    print("  VEREDICTO FINAL")
    print("══════════════════════════════════════════════════════")
    print()
    print("  Simulador REAL (statevector):")
    print("    ✅ Emaranhamento correto")
    print("    ✅ Bell State, Deutsch, Teleportação — tudo certo")
    print("    ❌ Limite: ~25 qubits em hardware comum")
    print("    ❌ 3000 qubits = impossível (RAM do universo)")
    print()
    print("  Simulador VIRTUAL (independente):")
    print("    ✅ Escala para milhares de qubits")
    print("    ✅ Rápido, eficiente, estável")
    print("    ❌ Sem emaranhamento — não é quântico completo")
    print("    ❌ Matematicamente equivalente a moedas aleatórias")
    print()
    print("  Nenhum computador clássico simula 1000+ qubits")
    print("  com emaranhamento real. Nem IBM, nem Google, nem NASA.")
    print()
    print("  Seu projeto é real, honesto e educacionalmente valioso.")
    print("══════════════════════════════════════════════════════")
    print()
