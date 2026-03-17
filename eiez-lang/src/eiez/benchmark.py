#!/usr/bin/env python3
# eiez-lang/benchmark.py
"""
EIEZ Benchmark — simula circuitos de N qubits em serie e gera relatorio HTML.

Uso:
    python benchmark.py
    python benchmark.py --shots 5
    python benchmark.py --sizes 100 500 1000 2000 3000 5000
"""

import sys, os, time, math, random, argparse, statistics

_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, "src"))

from eiez.optimizer_interface import create_optimizer


# ---------------------------------------------------------------------------
# Simulador inline (nao depende de arquivo .eiez)
# ---------------------------------------------------------------------------

class QubitState:
    def __init__(self):
        self.alpha = complex(1)
        self.beta  = complex(0)

    def apply_h(self):
        s = 1/math.sqrt(2)
        a, b = self.alpha, self.beta
        self.alpha = s*(a+b)
        self.beta  = s*(a-b)

    def apply_rx(self, theta):
        c = math.cos(theta/2)
        s = math.sin(theta/2)
        I = complex(0,1)
        a, b = self.alpha, self.beta
        self.alpha = c*a - I*s*b
        self.beta  = -I*s*a + c*b

    def prob1(self):
        return abs(self.beta)**2

    def measure(self):
        return 1 if random.random() < self.prob1() else 0


def run_circuit(n_qubits: int, shots: int, params: dict) -> dict:
    """
    Circuito padrao para benchmark:
      - H em todos os qubits (via loop)
      - RX(theta) nos primeiros 10 qubits (usa parametro ZIE se disponivel)
      - Mede todos
    """
    theta = params.get("theta", 0.7854)  # pi/4 como fallback

    results = []
    times   = []

    for _ in range(shots):
        t0 = time.perf_counter()

        qubits = [QubitState() for _ in range(n_qubits)]

        # H em todos
        for q in qubits:
            q.apply_h()

        # RX nos primeiros min(10, n) qubits
        for i in range(min(10, n_qubits)):
            qubits[i].apply_rx(theta)

        # Mede todos
        measurements = [q.measure() for q in qubits]
        ones  = sum(measurements)
        zeros = n_qubits - ones

        elapsed = time.perf_counter() - t0
        times.append(elapsed * 1000)  # ms
        results.append({"ones": ones, "zeros": zeros, "ratio": ones/n_qubits})

    return {
        "n_qubits":    n_qubits,
        "shots":       shots,
        "time_ms_avg": round(statistics.mean(times), 3),
        "time_ms_min": round(min(times), 3),
        "time_ms_max": round(max(times), 3),
        "ones_avg":    round(statistics.mean(r["ones"]  for r in results), 1),
        "zeros_avg":   round(statistics.mean(r["zeros"] for r in results), 1),
        "ratio_avg":   round(statistics.mean(r["ratio"] for r in results), 4),
        "states_possible": f"10^{int(n_qubits * math.log10(2))}",
        "gates_total": n_qubits + min(10, n_qubits),
    }


# ---------------------------------------------------------------------------
# Gerador de relatorio HTML
# ---------------------------------------------------------------------------

def generate_html(results: list, shots: int) -> str:
    rows = ""
    chart_labels = []
    chart_times  = []
    chart_qubits = []

    for r in results:
        bar_w = min(int(r["ratio_avg"] * 100), 100)
        ratio_pct = round(r["ratio_avg"] * 100, 1)
        time_str = f"{r['time_ms_avg']:.3f} ms"
        if r["time_ms_avg"] > 1000:
            time_str = f"{r['time_ms_avg']/1000:.2f} s"

        rows += f"""
        <tr>
          <td><strong>{r['n_qubits']:,}</strong></td>
          <td>{r['states_possible']}</td>
          <td>{r['gates_total']:,}</td>
          <td>{time_str}</td>
          <td>{r['time_ms_min']:.3f} / {r['time_ms_max']:.3f} ms</td>
          <td>
            <div class="bar-wrap">
              <div class="bar" style="width:{bar_w}%"></div>
              <span>{ratio_pct}% |1⟩</span>
            </div>
          </td>
        </tr>"""

        chart_labels.append(str(r['n_qubits']))
        chart_times.append(r['time_ms_avg'])
        chart_qubits.append(r['n_qubits'])

    total_gates = sum(r['gates_total'] for r in results)
    total_time  = sum(r['time_ms_avg'] * r['shots'] for r in results)
    max_q = max(r['n_qubits'] for r in results)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>EIEZ Benchmark Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');
  :root {{
    --bg:#07070e; --s1:#0f0f1a; --s2:#161624;
    --border:#252538; --accent:#7c6af7; --green:#5ee7b0;
    --yellow:#f7c26a; --red:#ff5f7e; --text:#e0e0f0; --muted:#6868a0;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Syne',sans-serif; padding:2rem; }}
  h1 {{ font-size:1.8rem; font-weight:800; letter-spacing:-0.03em; margin-bottom:0.3rem; }}
  .sub {{ color:var(--muted); font-family:'IBM Plex Mono',monospace; font-size:0.8rem; margin-bottom:2rem; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:2rem; }}
  .card {{ background:var(--s1); border:1px solid var(--border); border-radius:12px; padding:1.2rem; text-align:center; }}
  .card .val {{ font-size:1.8rem; font-weight:800; font-family:'IBM Plex Mono',monospace; }}
  .card .lbl {{ font-size:0.65rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.1em; margin-top:0.3rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.82rem; margin-bottom:2rem;
           background:var(--s1); border:1px solid var(--border); border-radius:12px; overflow:hidden; }}
  th {{ text-align:left; padding:0.9rem 1rem; font-size:0.65rem; font-weight:700;
        letter-spacing:0.12em; text-transform:uppercase; color:var(--muted);
        border-bottom:1px solid var(--border); }}
  td {{ padding:0.85rem 1rem; border-bottom:1px solid rgba(37,37,56,0.6); vertical-align:middle; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:rgba(124,106,247,0.05); }}
  .bar-wrap {{ display:flex; align-items:center; gap:0.6rem; }}
  .bar {{ height:8px; background:linear-gradient(90deg,var(--accent),var(--green));
          border-radius:4px; min-width:2px; transition:width 0.3s; }}
  .bar-wrap span {{ font-size:0.75rem; color:var(--muted); white-space:nowrap; }}
  .chart-wrap {{ background:var(--s1); border:1px solid var(--border); border-radius:12px;
                 padding:1.5rem; margin-bottom:2rem; }}
  .chart-title {{ font-size:0.7rem; font-weight:700; letter-spacing:0.15em;
                  text-transform:uppercase; color:var(--muted); margin-bottom:1rem; }}
  canvas {{ width:100% !important; }}
  .footer {{ text-align:center; font-size:0.72rem; color:var(--muted);
             font-family:'IBM Plex Mono',monospace; margin-top:1rem; }}
</style>
</head>
<body>

<h1>⚛ EIEZ Benchmark Report</h1>
<p class="sub">Simulacao em serie · {len(results)} tamanhos · {shots} shots cada · gerado pelo EIEZ Compiler</p>

<div class="cards">
  <div class="card">
    <div class="val" style="color:var(--accent)">{max_q:,}</div>
    <div class="lbl">Max Qubits</div>
  </div>
  <div class="card">
    <div class="val" style="color:var(--green)">{total_gates:,}</div>
    <div class="lbl">Gates Totais</div>
  </div>
  <div class="card">
    <div class="val" style="color:var(--yellow)">{total_time:.1f} ms</div>
    <div class="lbl">Tempo Total</div>
  </div>
  <div class="card">
    <div class="val" style="color:var(--red)">10^{int(max_q*math.log10(2))}</div>
    <div class="lbl">Estados Possiveis (max)</div>
  </div>
</div>

<div class="chart-wrap">
  <div class="chart-title">Tempo de simulacao (ms) por numero de qubits</div>
  <canvas id="chart" height="80"></canvas>
</div>

<table>
  <thead>
    <tr>
      <th>Qubits</th>
      <th>Estados possíveis</th>
      <th>Gates</th>
      <th>Tempo médio</th>
      <th>Min / Max</th>
      <th>Distribuição |1⟩</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>

<div class="footer">
  EIEZ Compiler v2.0 · Simulador por qubit independente · nao usa statevector completo
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<script>
const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: 'Tempo medio (ms)',
      data: {chart_times},
      borderColor: '#7c6af7',
      backgroundColor: 'rgba(124,106,247,0.1)',
      borderWidth: 2,
      pointBackgroundColor: '#5ee7b0',
      pointRadius: 5,
      tension: 0.3,
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ labels: {{ color: '#e0e0f0', font: {{ family: 'IBM Plex Mono' }} }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: '#6868a0' }}, grid: {{ color: '#252538' }} }},
      y: {{ ticks: {{ color: '#6868a0' }}, grid: {{ color: '#252538' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli = argparse.ArgumentParser(description="EIEZ Benchmark")
    cli.add_argument("--sizes",  nargs="+", type=int,
                     default=[100, 500, 1000, 2000, 3000, 5000])
    cli.add_argument("--shots",  type=int, default=3)
    cli.add_argument("--backend", choices=["auto","null","zie"], default="auto")
    cli.add_argument("-o", "--output", default="benchmark_report.html")
    args = cli.parse_args()

    # Parametros ZIE
    optimizer = create_optimizer(args.backend)
    # Simula qargs fake para obter theta
    fake_qargs = [("q", i) for i in range(10)]
    try:
        from eiez._zie_engine import run as zie_run
        theta = zie_run(fake_qargs, "coherence") or 0.7854
        backend_label = "ZIE"
    except Exception:
        theta = 0.7854
        backend_label = "null (ZIE ausente)"
    params = {"theta": theta}

    print()
    print("=" * 60)
    print("  EIEZ Benchmark — Simulacao em Serie")
    print(f"  Tamanhos : {args.sizes}")
    print(f"  Shots    : {args.shots}")
    print(f"  Backend  : {backend_label}")
    print(f"  Theta ZIE: {theta:.4f}")
    print("=" * 60)

    all_results = []
    for n in args.sizes:
        print(f"\n  ▸ Simulando {n:>5} qubits × {args.shots} shots ...", end=" ", flush=True)
        r = run_circuit(n, args.shots, params)
        all_results.append(r)
        states = f"10^{int(n*math.log10(2))}"
        print(f"✅  {r['time_ms_avg']:.3f} ms avg  |  {states} estados")

    print()
    print("=" * 60)
    print(f"  Gerando relatorio: {args.output}")

    html = generate_html(all_results, args.shots)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✅ Salvo em: {args.output}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
