#!/usr/bin/env python3
"""
EIEZ Lang — Mega Benchmark
Teste de estabilidade: 1000 a 30000 qubits
Uso: python benchmark_mega.py
"""
import sys, os, time, math, random, statistics, json

_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, "src"))

# Tenta usar motor ZIE se disponivel
try:
    from eiez._zie_engine import run as zie_run
    THETA = zie_run([("q", i) for i in range(10)], "coherence") or 0.7345
    BACKEND = "ZIE"
except Exception:
    THETA = 0.7345
    BACKEND = "fallback"

class QubitState:
    def __init__(self):
        self.alpha = complex(1)
        self.beta  = complex(0)
    def apply_h(self):
        s = 1/math.sqrt(2)
        a, b = self.alpha, self.beta
        self.alpha = s*(a+b); self.beta = s*(a-b)
    def apply_rx(self, theta):
        c = math.cos(theta/2); s = math.sin(theta/2); I = complex(0,1)
        a, b = self.alpha, self.beta
        self.alpha = c*a - I*s*b; self.beta = -I*s*a + c*b
    def measure(self):
        return 1 if random.random() < abs(self.beta)**2 else 0

def run_circuit(n, shots, theta):
    times, ones_list = [], []
    for _ in range(shots):
        t0 = time.perf_counter()
        qubits = [QubitState() for _ in range(n)]
        for q in qubits: q.apply_h()
        for i in range(min(10, n)): qubits[i].apply_rx(theta)
        measurements = [q.measure() for q in qubits]
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)
        ones_list.append(sum(measurements))
    return {
        "n": n, "shots": shots,
        "avg_ms":   round(statistics.mean(times), 4),
        "min_ms":   round(min(times), 4),
        "max_ms":   round(max(times), 4),
        "stdev_ms": round(statistics.stdev(times) if shots > 1 else 0, 4),
        "ones_avg": round(statistics.mean(ones_list), 1),
        "ratio":    round(statistics.mean(o/n for o in ones_list), 4),
        "states":   f"10^{int(n*math.log10(2))}",
        "gates":    n + min(10, n),
    }

SIZES = [1000, 5000, 10000, 15000, 20000, 30000]
SHOTS = 5

print()
print("=" * 65)
print("  EIEZ Lang — Mega Benchmark (Teste de Estabilidade)")
print(f"  Tamanhos : {SIZES}")
print(f"  Shots    : {SHOTS}")
print(f"  Backend  : {BACKEND}  |  Theta: {THETA:.4f}")
print("=" * 65)

results = []
for n in SIZES:
    print(f"  ▸ {n:>6,} qubits × {SHOTS} shots ...", end=" ", flush=True)
    r = run_circuit(n, SHOTS, THETA)
    results.append(r)
    estavel = "✓" if abs(r["ratio"] - 0.5) < 0.02 else "⚠"
    print(f"✅  avg={r['avg_ms']:.3f}ms  "
          f"stdev={r['stdev_ms']:.3f}ms  "
          f"|1>={r['ratio']*100:.1f}% {estavel}  "
          f"estados={r['states']}")

total_ms    = sum(r["avg_ms"] * r["shots"] for r in results)
total_gates = sum(r["gates"] for r in results) * SHOTS
ratios      = [r["ratio"]*100 for r in results]

print()
print("=" * 65)
print(f"  Tempo total    : {total_ms:.1f} ms")
print(f"  Gates totais   : {total_gates:,}")
print(f"  Media |1>      : {statistics.mean(ratios):.2f}%")
print(f"  Desvio |1>     : {statistics.stdev(ratios):.3f}%")
print(f"  Max estados    : {results[-1]['states']}")
print("=" * 65)

# Salva JSON para o relatorio
out_json = os.path.join(_base, "mega_results.json")
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n  Dados salvos em: mega_results.json")
print("  Agora rode: python gerar_relatorio_mega.py")
print()
