#!/usr/bin/env python3
"""
EIEZ/ZIE — Experimento Real v2.0
Calibrado para dados financeiros reais (PETR4.SA)
Correções v2:
  - Limiares Ψ mais conservadores (0.85 / 1.2)
  - alpha reduzido (0.08) — freio mais suave
  - Janela τ maior (30) — menos sensível a ruído
  - lr_floor maior (1e-5) — não trava o aprendizado
  - Aceleração desativada — dados financeiros não precisam
Joemerson da Silva Lima | Cuiabá, MT | 2026
Patente BR 10 2025 024459 4
"""

import os, time, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler

try:
    from codecarbon import EmissionsTracker
    CODECARBON = True
except ImportError:
    CODECARBON = False

try:
    import yfinance as yf
    YFINANCE = True
except ImportError:
    YFINANCE = False

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO v2 — calibrada para dados financeiros
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "ticker":      "PETR4.SA",
    "periodo":     "5y",
    "seq_len":     30,
    "hidden":      64,
    "dropout":     0.20,
    "epochs":      80,
    "batch_size":  32,
    "lr_inicial":  1e-3,
    "split":       0.80,
    "seed":        42,
    "p_cpu_watts": 25.0,
    # EIE/ZIE v2 — parâmetros calibrados
    "janela_tau":  30,      # v1=20 → maior janela, menos ruído
    "beta":        0.15,    # v1=0.10 → suavização maior
    "alpha":       0.08,    # v1=0.15 → freio mais suave
    "truncamento": 0.05,
    "psi_prev":    0.85,    # v1=0.80 → limiar preventivo mais alto
    "psi_alarme":  1.20,    # v1=1.00 → alarme só em crítico real
    "lr_floor":    1e-5,    # v1=1e-6 → não trava o aprendizado
    "lr_ceil":     1e-3,    # sem aceleração — mantém lr_inicial
}

torch.manual_seed(CONFIG["seed"])
np.random.seed(CONFIG["seed"])

# ═══════════════════════════════════════════════════════════════
# DADOS
# ═══════════════════════════════════════════════════════════════

def carregar_dados():
    print(f"\n📥 Baixando dados reais: {CONFIG['ticker']} ({CONFIG['periodo']})")
    if YFINANCE:
        try:
            df = yf.download(CONFIG["ticker"], period=CONFIG["periodo"],
                             auto_adjust=True, progress=False)
            if df.empty:
                raise ValueError("vazio")
            serie = df["Close"].dropna().values.astype(float)
            fonte = f"Yahoo Finance — {CONFIG['ticker']}"
            print(f"  ✓ {len(serie)} dias de dados reais")
            return serie, fonte
        except Exception as e:
            print(f"  ⚠ Erro: {e} — usando fallback")
    n = 1200
    t = np.arange(n)
    serie = 20 + 0.03*t + 3*np.sin(2*np.pi*t/252) + np.random.normal(0, 1, n)
    return serie, "Sintético (fallback)"

def preparar_dataset(serie):
    scaler = MinMaxScaler()
    s = scaler.fit_transform(serie.reshape(-1,1)).flatten()
    X, y = [], []
    for i in range(len(s) - CONFIG["seq_len"]):
        X.append(s[i:i+CONFIG["seq_len"]])
        y.append(s[i+CONFIG["seq_len"]])
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    split = int(len(X)*CONFIG["split"])
    ds_tr  = TensorDataset(torch.tensor(X[:split]).unsqueeze(-1),
                           torch.tensor(y[:split]).unsqueeze(-1))
    ds_val = TensorDataset(torch.tensor(X[split:]).unsqueeze(-1),
                           torch.tensor(y[split:]).unsqueeze(-1))
    return (DataLoader(ds_tr,  batch_size=CONFIG["batch_size"], shuffle=True),
            DataLoader(ds_val, batch_size=CONFIG["batch_size"], shuffle=False),
            scaler)

# ═══════════════════════════════════════════════════════════════
# MODELO
# ═══════════════════════════════════════════════════════════════

class LSTMModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1, CONFIG["hidden"], num_layers=2,
                            dropout=CONFIG["dropout"], batch_first=True)
        self.fc = nn.Linear(CONFIG["hidden"], 1)
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# ═══════════════════════════════════════════════════════════════
# MOTOR EIE/ZIE v2
# ═══════════════════════════════════════════════════════════════

class MotorEIEZIE:
    def __init__(self):
        self.hist_loss   = []
        self.tau_smooth  = 1.0
        self.tau_hist    = []
        self.lr_atual    = CONFIG["lr_inicial"]
        self.intervencoes = 0
        self.hist_tau    = []
        self.hist_psi    = []
        self.hist_modo   = []
        self.hist_lr     = []

    def calcular_tau(self):
        W = CONFIG["janela_tau"]
        if len(self.hist_loss) < W + 2:
            return 1.0
        janela = np.array(self.hist_loss[-W:])
        media  = janela.mean()
        var    = janela.var()
        if var < 1e-12:
            return 1.0
        C = []
        for d in range(1, len(janela)):
            r = np.mean((janela[:-d]-media)*(janela[d:]-media)) / var
            C.append(r)
            if abs(r) < CONFIG["truncamento"]:
                break
        return max(0.5 + sum(C), 0.5)

    def atualizar(self, loss_val):
        self.hist_loss.append(loss_val)
        tau = self.calcular_tau()
        b = CONFIG["beta"]
        self.tau_smooth = b*tau + (1-b)*self.tau_smooth
        self.tau_hist.append(self.tau_smooth)

        tau_crit = (np.percentile(self.tau_hist, 95)
                    if len(self.tau_hist) >= 5
                    else max(self.tau_smooth*1.5, 1.5))

        psi = self.tau_smooth / tau_crit

        # Limiares v2 — mais conservadores
        if psi < 0.6:
            modo    = "Otimização"
            novo_lr = self.lr_atual          # mantém — sem aceleração
        elif psi < CONFIG["psi_prev"]:
            modo    = "Monitoramento"
            novo_lr = self.lr_atual          # ainda não intervém
        elif psi < CONFIG["psi_alarme"]:
            modo    = "Preventivo"
            novo_lr = self.lr_atual * (1 - CONFIG["alpha"] * (psi - 0.6))
            self.intervencoes += 1
        else:
            modo    = "Alarme"
            fator   = CONFIG["alpha"] * min(psi - 0.8, 1.5)
            novo_lr = self.lr_atual * (1 - fator)
            self.intervencoes += 1

        novo_lr = max(min(novo_lr, CONFIG["lr_ceil"]), CONFIG["lr_floor"])
        self.lr_atual = novo_lr

        self.hist_tau.append(self.tau_smooth)
        self.hist_psi.append(psi)
        self.hist_modo.append(modo)
        self.hist_lr.append(novo_lr)

        return novo_lr, psi, modo

# ═══════════════════════════════════════════════════════════════
# TREINAMENTO
# ═══════════════════════════════════════════════════════════════

def treinar(dl_tr, dl_val, usar_eiezie, fonte):
    rotulo = "B — LSTM + EIE/ZIE v2" if usar_eiezie else "A — LSTM Convencional"
    print(f"\n{'='*55}")
    print(f"  Treinando Grupo {rotulo}")
    print(f"  Dataset: {fonte}")
    print(f"{'='*55}")

    modelo     = LSTMModel()
    criterio   = nn.MSELoss()
    otimizador = torch.optim.Adam(modelo.parameters(), lr=CONFIG["lr_inicial"])
    motor      = MotorEIEZIE() if usar_eiezie else None

    hist_tr, hist_val, hist_e, hist_lr = [], [], [], []
    tempo_total = 0.0

    for ep in range(CONFIG["epochs"]):
        t0 = time.perf_counter()

        modelo.train()
        lt = sum(criterio(modelo(xb), yb).item()
                 for xb, yb in dl_tr
                 if not (modelo.zero_grad() or False)
                 and not (otimizador.zero_grad() or False)) / len(dl_tr)

        # treino correto
        modelo.train()
        lt = 0.0
        for xb, yb in dl_tr:
            otimizador.zero_grad()
            loss = criterio(modelo(xb), yb)
            loss.backward()
            otimizador.step()
            lt += loss.item()
        lt /= len(dl_tr)

        modelo.eval()
        lv = 0.0
        with torch.no_grad():
            for xb, yb in dl_val:
                lv += criterio(modelo(xb), yb).item()
        lv /= len(dl_val)

        elapsed = time.perf_counter() - t0
        tempo_total += elapsed
        hist_e.append(elapsed * CONFIG["p_cpu_watts"])
        hist_tr.append(lt)
        hist_val.append(lv)

        if usar_eiezie and motor:
            novo_lr, psi, modo = motor.atualizar(lv)
            hist_lr.append(novo_lr)
            for g in otimizador.param_groups:
                g["lr"] = novo_lr
            status = f"Ψ={psi:.3f} [{modo[:4]}] lr={novo_lr:.2e}"
        else:
            hist_lr.append(CONFIG["lr_inicial"])
            status = f"lr={CONFIG['lr_inicial']:.2e}"

        if (ep+1) % 10 == 0 or ep == 0:
            print(f"  Época {ep+1:3d}/{CONFIG['epochs']} | "
                  f"tr={lt:.5f} | val={lv:.5f} | {status} | {elapsed*1000:.0f}ms")

    return {
        "loss_tr":      hist_tr,
        "loss_val":     hist_val,
        "energia":      hist_e,
        "energia_total": sum(hist_e),
        "tempo_total":  tempo_total,
        "hist_lr":      hist_lr,
        "motor":        motor,
    }

# ═══════════════════════════════════════════════════════════════
# RELATÓRIO
# ═══════════════════════════════════════════════════════════════

def relatorio(ra, rb, fonte):
    ea, eb   = ra["energia_total"], rb["energia_total"]
    lva, lvb = ra["loss_val"][-1],  rb["loss_val"][-1]
    de = (ea-eb)/ea*100
    dl = (lva-lvb)/lva*100

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  RESULTADO — EIE/ZIE v2 | Dados Reais              ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Dataset: {fonte:<43}║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Métrica':<30} {'Grupo A':>10} {'Grupo B':>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Loss validação final':<30} {lva:>10.6f} {lvb:>10.6f} ║")
    print(f"║  {'Energia total (J)':<30} {ea:>10.1f} {eb:>10.1f} ║")
    print(f"║  {'Tempo total (s)':<30} {ra['tempo_total']:>10.1f} {rb['tempo_total']:>10.1f} ║")
    if rb["motor"]:
        print(f"║  {'Intervenções EIE/ZIE':<30} {'—':>10} {rb['motor'].intervencoes:>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    vd = "✓ melhor" if de > 0 else "✗ pior"
    vl = "✓ melhor" if dl > 0 else "✗ pior"
    print(f"║  Energia:  {de:+.1f}%  {vd:<40}║")
    print(f"║  Loss:     {dl:+.1f}%  {vl:<40}║")
    print("╚══════════════════════════════════════════════════════╝")

    res = {
        "versao": "v2",
        "dataset": fonte,
        "parametros_v2": {
            "janela_tau": CONFIG["janela_tau"],
            "alpha": CONFIG["alpha"],
            "psi_preventivo": CONFIG["psi_prev"],
            "psi_alarme": CONFIG["psi_alarme"],
            "lr_floor": CONFIG["lr_floor"],
        },
        "grupo_a": {"energia_j": round(ea,2), "loss_final": round(lva,6),
                    "tempo_s": round(ra["tempo_total"],2)},
        "grupo_b": {"energia_j": round(eb,2), "loss_final": round(lvb,6),
                    "tempo_s": round(rb["tempo_total"],2),
                    "intervencoes": rb["motor"].intervencoes if rb["motor"] else 0},
        "reducao_energia_pct": round(de,2),
        "reducao_loss_pct":    round(dl,2),
    }
    with open("resultado_v2.json","w",encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print("  📄 Salvo: resultado_v2.json")
    return res

def graficos(ra, rb, fonte):
    C = {"conv":"#ff5f7e","eie":"#7c6af7","verde":"#5ee7b0",
         "am":"#f7c26a","muted":"#6868a0","bg":"#07070e",
         "s1":"#0f0f1a","border":"#252538","text":"#e0e0f0"}
    ep = list(range(1, CONFIG["epochs"]+1))
    motor = rb["motor"]

    fig = plt.figure(figsize=(16,12), facecolor=C["bg"])
    fig.suptitle(f"EIE/ZIE v2 — Experimento Real | {fonte} | Patente BR 10 2025 024459 4",
                 color=C["text"], fontsize=12, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    def ax_style(ax, t):
        ax.set_facecolor(C["s1"])
        ax.tick_params(colors=C["muted"])
        ax.set_title(t, color=C["text"], fontsize=9, pad=6)
        for s in ax.spines.values(): s.set_edgecolor(C["border"])

    # Loss treino
    ax = fig.add_subplot(gs[0,0])
    ax.semilogy(ep, ra["loss_tr"], color=C["conv"], lw=1.5, label="Convencional")
    ax.semilogy(ep, rb["loss_tr"], color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v2")
    ax_style(ax, "Loss Treino (log)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Loss validação
    ax = fig.add_subplot(gs[0,1])
    ax.semilogy(ep, ra["loss_val"], color=C["conv"], lw=1.5, label="Convencional")
    ax.semilogy(ep, rb["loss_val"], color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v2")
    ax_style(ax, "Loss Validação (log)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # τ_corr
    if motor:
        ax = fig.add_subplot(gs[1,0])
        ax.plot(ep, motor.hist_tau, color=C["verde"], lw=1.5, label="τ_corr")
        tc = np.percentile(motor.hist_tau, 95)
        ax.axhline(tc, color=C["am"], ls="--", lw=1, label=f"τ_crit p95={tc:.2f}")
        ax_style(ax, "Tempo de Correlação τ_corr")
        ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

        # Ψ(t)
        ax = fig.add_subplot(gs[1,1])
        ax.plot(ep, motor.hist_psi, color=C["eie"], lw=1.5)
        ax.axhline(CONFIG["psi_prev"],   color=C["am"],   ls="--", lw=1, alpha=0.8,
                   label=f"Preventivo ({CONFIG['psi_prev']})")
        ax.axhline(CONFIG["psi_alarme"], color=C["conv"], ls="--", lw=1, alpha=0.8,
                   label=f"Alarme ({CONFIG['psi_alarme']})")
        cores_m = {"Otimização":C["verde"],"Monitoramento":C["eie"],
                   "Preventivo":C["am"],"Alarme":C["conv"]}
        for i, m in enumerate(motor.hist_modo):
            ax.axvspan(i+0.5, i+1.5, alpha=0.10, color=cores_m.get(m,"gray"))
        ax_style(ax, "Índice Ψ(t) — limiares v2")
        ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Energia acumulada
    ax = fig.add_subplot(gs[2,0])
    ax.plot(ep, np.cumsum(ra["energia"]), color=C["conv"], lw=1.5, label="Convencional")
    ax.plot(ep, np.cumsum(rb["energia"]), color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v2")
    ax_style(ax, "Energia Acumulada (J)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Learning rate
    ax = fig.add_subplot(gs[2,1])
    ax.semilogy(ep, ra["hist_lr"], color=C["conv"], lw=1.5, ls="--", label="Convencional (fixo)")
    ax.semilogy(ep, rb["hist_lr"], color=C["eie"],  lw=1.5,          label="EIE/ZIE v2 (adaptativo)")
    ax_style(ax, "Learning Rate (log)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    plt.savefig("resultado_graficos_v2.png", dpi=150,
                bbox_inches="tight", facecolor=C["bg"])
    print("  📊 Salvo: resultado_graficos_v2.png")
    plt.show()

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("██████████████████████████████████████████████████████")
    print("  EIE/ZIE — Experimento Real v2.0")
    print("  Calibrado para dados financeiros reais")
    print("  Joemerson da Silva Lima | Cuiabá, MT | 2026")
    print("  Patente BR 10 2025 024459 4")
    print("██████████████████████████████████████████████████████")
    print()
    print("  Mudanças v2 vs v1:")
    print(f"    janela_tau:  20 → {CONFIG['janela_tau']}  (menos sensível a ruído)")
    print(f"    alpha:       0.15 → {CONFIG['alpha']}  (freio mais suave)")
    print(f"    psi_prev:    0.80 → {CONFIG['psi_prev']}  (dispara mais tarde)")
    print(f"    psi_alarme:  1.00 → {CONFIG['psi_alarme']}  (alarme só em crítico real)")
    print(f"    lr_floor:    1e-6 → {CONFIG['lr_floor']}  (não trava aprendizado)")
    print(f"    aceleração:  removida (desnecessária em dados financeiros)")

    serie, fonte  = carregar_dados()
    dl_tr, dl_val, scaler = preparar_dataset(serie)

    ra = treinar(dl_tr, dl_val, usar_eiezie=False, fonte=fonte)
    rb = treinar(dl_tr, dl_val, usar_eiezie=True,  fonte=fonte)

    res = relatorio(ra, rb, fonte)
    graficos(ra, rb, fonte)

    print()
    print("  Arquivos gerados:")
    print("    resultado_v2.json          — métricas")
    print("    resultado_graficos_v2.png  — gráficos")
    print()
