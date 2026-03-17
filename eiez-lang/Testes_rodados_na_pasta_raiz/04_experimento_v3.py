#!/usr/bin/env python3
"""
EIEZ/ZIE — Experimento Real v3.0
Novidade principal: RECUPERAÇÃO ADAPTATIVA
  - Após Ψ cair abaixo de 0.5, lr sobe gradualmente de volta
  - Taxa de recuperação proporcional à queda de Ψ
  - Teto de recuperação = lr que estava antes da crise
Joemerson da Silva Lima | Cuiabá, MT | 2026
Patente BR 10 2025 024459 4
"""

import time, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler

try:
    import yfinance as yf
    YFINANCE = True
except ImportError:
    YFINANCE = False

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO v3
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "ticker":        "PETR4.SA",
    "periodo":       "5y",
    "seq_len":       30,
    "hidden":        64,
    "dropout":       0.20,
    "epochs":        80,
    "batch_size":    32,
    "lr_inicial":    1e-3,
    "split":         0.80,
    "seed":          42,
    "p_cpu_watts":   25.0,
    # EIE/ZIE v3
    "janela_tau":    30,
    "beta":          0.15,
    "alpha":         0.08,    # freio
    "gamma":         0.03,    # NOVO: taxa de recuperação
    "truncamento":   0.05,
    "psi_prev":      0.85,
    "psi_alarme":    1.20,
    "psi_recupera":  0.50,    # NOVO: abaixo disso, recupera lr
    "lr_floor":      1e-5,
    "lr_ceil":       1e-3,
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
            print(f"  ⚠ Erro: {e} — fallback sintético")
    n = 1200
    t = np.arange(n)
    serie = 20 + 0.03*t + 3*np.sin(2*np.pi*t/252) + np.random.normal(0,1,n)
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
    split = int(len(X) * CONFIG["split"])
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
# MOTOR EIE/ZIE v3 — com recuperação adaptativa
# ═══════════════════════════════════════════════════════════════

class MotorEIEZIE:
    def __init__(self):
        self.hist_loss    = []
        self.tau_smooth   = 1.0
        self.tau_hist     = []
        self.lr_atual     = CONFIG["lr_inicial"]
        self.lr_pre_crise = CONFIG["lr_inicial"]  # NOVO: guarda lr antes da crise
        self.em_crise     = False                  # NOVO: flag de estado
        self.intervencoes = 0
        self.recuperacoes = 0                      # NOVO: contador
        self.hist_tau     = []
        self.hist_psi     = []
        self.hist_modo    = []
        self.hist_lr      = []

    def calcular_tau(self):
        W = CONFIG["janela_tau"]
        if len(self.hist_loss) < W + 2:
            return 1.0
        janela = np.array(self.hist_loss[-W:])
        media, var = janela.mean(), janela.var()
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
                    else max(self.tau_smooth * 1.5, 1.5))

        psi = self.tau_smooth / tau_crit

        # ── Máquina de estados: Normal → Crise → Recuperação ──

        if psi >= CONFIG["psi_alarme"]:
            # ALARME — reduz lr agressivamente
            if not self.em_crise:
                self.lr_pre_crise = self.lr_atual  # salva lr antes da crise
                self.em_crise = True
            fator   = CONFIG["alpha"] * min(psi - 0.8, 1.5)
            novo_lr = self.lr_atual * (1 - fator)
            modo    = "Alarme"
            self.intervencoes += 1

        elif psi >= CONFIG["psi_prev"]:
            # PREVENTIVO — reduz lr suavemente
            novo_lr = self.lr_atual * (1 - CONFIG["alpha"] * (psi - 0.6))
            modo    = "Preventivo"
            self.intervencoes += 1

        elif psi <= CONFIG["psi_recupera"] and self.em_crise:
            # RECUPERAÇÃO — Ψ caiu, sistema estável, sobe lr gradualmente
            novo_lr = self.lr_atual * (1 + CONFIG["gamma"])
            novo_lr = min(novo_lr, self.lr_pre_crise)  # teto = lr antes da crise
            modo    = "Recuperação"
            self.recuperacoes += 1
            if novo_lr >= self.lr_pre_crise * 0.95:
                self.em_crise = False  # saiu da crise completamente

        elif psi < 0.6:
            # OTIMIZAÇÃO — sistema saudável
            novo_lr = self.lr_atual
            modo    = "Otimização"

        else:
            # MONITORAMENTO — zona intermediária
            novo_lr = self.lr_atual
            modo    = "Monitoramento"

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
    rotulo = "B — LSTM + EIE/ZIE v3" if usar_eiezie else "A — LSTM Convencional"
    print(f"\n{'='*55}")
    print(f"  Treinando Grupo {rotulo}")
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
            status = f"Ψ={psi:.3f} [{modo[:5]}] lr={novo_lr:.2e}"
        else:
            hist_lr.append(CONFIG["lr_inicial"])
            status = f"lr={CONFIG['lr_inicial']:.2e}"

        if (ep+1) % 10 == 0 or ep == 0:
            print(f"  Época {ep+1:3d}/{CONFIG['epochs']} | "
                  f"tr={lt:.5f} | val={lv:.5f} | {status} | {elapsed*1000:.0f}ms")

    return {
        "loss_tr":       hist_tr,
        "loss_val":      hist_val,
        "energia":       hist_e,
        "energia_total": sum(hist_e),
        "tempo_total":   tempo_total,
        "hist_lr":       hist_lr,
        "motor":         motor,
    }

# ═══════════════════════════════════════════════════════════════
# RELATÓRIO
# ═══════════════════════════════════════════════════════════════

def relatorio(ra, rb, fonte):
    ea, eb   = ra["energia_total"], rb["energia_total"]
    lva, lvb = ra["loss_val"][-1],  rb["loss_val"][-1]
    de = (ea - eb) / ea * 100
    dl = (lva - lvb) / lva * 100
    motor = rb["motor"]

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  RESULTADO — EIE/ZIE v3 | Recuperação Adaptativa   ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Dataset: {fonte:<43}║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Métrica':<30} {'Grupo A':>10} {'Grupo B':>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Loss validação final':<30} {lva:>10.6f} {lvb:>10.6f} ║")
    print(f"║  {'Energia total (J)':<30} {ea:>10.1f} {eb:>10.1f} ║")
    print(f"║  {'Tempo total (s)':<30} {ra['tempo_total']:>10.1f} {rb['tempo_total']:>10.1f} ║")
    if motor:
        print(f"║  {'Intervenções (freio)':<30} {'—':>10} {motor.intervencoes:>10} ║")
        print(f"║  {'Recuperações (subida lr)':<30} {'—':>10} {motor.recuperacoes:>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Energia:  {de:+.1f}%  {'✓ melhor' if de>0 else '✗ pior':<42}║")
    print(f"║  Loss:     {dl:+.1f}%  {'✓ melhor' if dl>0 else '✗ pior':<42}║")
    print("╚══════════════════════════════════════════════════════╝")

    # Distribuição de modos
    if motor:
        from collections import Counter
        dist = Counter(motor.hist_modo)
        print()
        print("  Distribuição de modos operacionais:")
        for modo, n in sorted(dist.items(), key=lambda x: -x[1]):
            barra = "█" * (n // 2)
            print(f"    {modo:<15} {barra:<40} {n} épocas")

    res = {
        "versao": "v3",
        "dataset": fonte,
        "novidade": "recuperacao_adaptativa",
        "parametros": {
            "janela_tau":   CONFIG["janela_tau"],
            "alpha_freio":  CONFIG["alpha"],
            "gamma_recup":  CONFIG["gamma"],
            "psi_prev":     CONFIG["psi_prev"],
            "psi_alarme":   CONFIG["psi_alarme"],
            "psi_recupera": CONFIG["psi_recupera"],
            "lr_floor":     CONFIG["lr_floor"],
        },
        "grupo_a": {
            "energia_j":  round(ea, 2),
            "loss_final": round(lva, 6),
            "tempo_s":    round(ra["tempo_total"], 2),
        },
        "grupo_b": {
            "energia_j":    round(eb, 2),
            "loss_final":   round(lvb, 6),
            "tempo_s":      round(rb["tempo_total"], 2),
            "intervencoes": motor.intervencoes if motor else 0,
            "recuperacoes": motor.recuperacoes if motor else 0,
        },
        "reducao_energia_pct": round(de, 2),
        "reducao_loss_pct":    round(dl, 2),
    }
    with open("resultado_v3.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print("\n  📄 Salvo: resultado_v3.json")
    return res

def graficos(ra, rb, fonte):
    C = {"conv":"#ff5f7e","eie":"#7c6af7","verde":"#5ee7b0",
         "am":"#f7c26a","recup":"#00e5ff","muted":"#6868a0",
         "bg":"#07070e","s1":"#0f0f1a","border":"#252538","text":"#e0e0f0"}
    ep    = list(range(1, CONFIG["epochs"]+1))
    motor = rb["motor"]

    fig = plt.figure(figsize=(16, 12), facecolor=C["bg"])
    fig.suptitle(
        f"EIE/ZIE v3 — Recuperação Adaptativa | {fonte} | Patente BR 10 2025 024459 4",
        color=C["text"], fontsize=12, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    def ax_style(ax, t):
        ax.set_facecolor(C["s1"])
        ax.tick_params(colors=C["muted"])
        ax.set_title(t, color=C["text"], fontsize=9, pad=6)
        for s in ax.spines.values(): s.set_edgecolor(C["border"])

    cores_modo = {
        "Otimização":   C["verde"],
        "Monitoramento":C["eie"],
        "Preventivo":   C["am"],
        "Alarme":       C["conv"],
        "Recuperação":  C["recup"],
    }

    # Loss treino
    ax = fig.add_subplot(gs[0, 0])
    ax.semilogy(ep, ra["loss_tr"], color=C["conv"], lw=1.5, label="Convencional")
    ax.semilogy(ep, rb["loss_tr"], color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v3")
    ax_style(ax, "Loss Treino (log)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Loss validação + zonas de modo
    ax = fig.add_subplot(gs[0, 1])
    ax.semilogy(ep, ra["loss_val"], color=C["conv"], lw=1.5, label="Convencional")
    ax.semilogy(ep, rb["loss_val"], color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v3")
    if motor:
        for i, m in enumerate(motor.hist_modo):
            ax.axvspan(i+0.5, i+1.5, alpha=0.08, color=cores_modo.get(m, "gray"))
    ax_style(ax, "Loss Validação (log) + modos")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # τ_corr
    if motor:
        ax = fig.add_subplot(gs[1, 0])
        ax.plot(ep, motor.hist_tau, color=C["verde"], lw=1.5, label="τ_corr")
        tc = np.percentile(motor.hist_tau, 95)
        ax.axhline(tc, color=C["am"], ls="--", lw=1, label=f"τ_crit={tc:.2f}")
        ax_style(ax, "τ_corr — Tempo de Correlação")
        ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

        # Ψ(t) com 5 modos coloridos
        ax = fig.add_subplot(gs[1, 1])
        ax.plot(ep, motor.hist_psi, color=C["eie"], lw=1.5, zorder=5)
        ax.axhline(CONFIG["psi_prev"],    color=C["am"],   ls="--", lw=1,
                   label=f"Preventivo ({CONFIG['psi_prev']})")
        ax.axhline(CONFIG["psi_alarme"],  color=C["conv"], ls="--", lw=1,
                   label=f"Alarme ({CONFIG['psi_alarme']})")
        ax.axhline(CONFIG["psi_recupera"],color=C["recup"],ls=":",  lw=1,
                   label=f"Recuperação ({CONFIG['psi_recupera']})")
        for i, m in enumerate(motor.hist_modo):
            ax.axvspan(i+0.5, i+1.5, alpha=0.12, color=cores_modo.get(m, "gray"))
        ax_style(ax, "Ψ(t) — 5 modos operacionais v3")
        ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Energia acumulada
    ax = fig.add_subplot(gs[2, 0])
    ax.plot(ep, np.cumsum(ra["energia"]), color=C["conv"], lw=1.5, label="Convencional")
    ax.plot(ep, np.cumsum(rb["energia"]), color=C["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE v3")
    ax_style(ax, "Energia Acumulada (J)")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    # Learning rate com zonas de recuperação destacadas
    ax = fig.add_subplot(gs[2, 1])
    ax.semilogy(ep, ra["hist_lr"], color=C["conv"], lw=1.5, ls="--", label="Convencional (fixo)")
    ax.semilogy(ep, rb["hist_lr"], color=C["eie"],  lw=1.5, label="EIE/ZIE v3 (adaptativo)")
    if motor:
        for i, m in enumerate(motor.hist_modo):
            if m == "Recuperação":
                ax.axvspan(i+0.5, i+1.5, alpha=0.25, color=C["recup"])
    ax_style(ax, "Learning Rate — zonas de recuperação em ciano")
    ax.legend(fontsize=7, facecolor=C["s1"], labelcolor=C["text"])

    plt.savefig("resultado_graficos_v3.png", dpi=150,
                bbox_inches="tight", facecolor=C["bg"])
    print("  📊 Salvo: resultado_graficos_v3.png")
    plt.show()

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("██████████████████████████████████████████████████████")
    print("  EIE/ZIE — Experimento Real v3.0")
    print("  Novidade: Recuperação Adaptativa do Learning Rate")
    print("  Joemerson da Silva Lima | Cuiabá, MT | 2026")
    print("  Patente BR 10 2025 024459 4")
    print("██████████████████████████████████████████████████████")
    print()
    print("  Ciclo completo v3:")
    print("    Otimização → Monitoramento → Preventivo")
    print("    → Alarme → [Ψ cai] → Recuperação → Otimização")
    print()
    print(f"  gamma (recuperação): {CONFIG['gamma']}")
    print(f"  psi_recupera:        {CONFIG['psi_recupera']}")

    serie, fonte = carregar_dados()
    dl_tr, dl_val, scaler = preparar_dataset(serie)

    ra = treinar(dl_tr, dl_val, usar_eiezie=False, fonte=fonte)
    rb = treinar(dl_tr, dl_val, usar_eiezie=True,  fonte=fonte)

    res = relatorio(ra, rb, fonte)
    graficos(ra, rb, fonte)

    print()
    print("  Arquivos gerados:")
    print("    resultado_v3.json          — métricas")
    print("    resultado_graficos_v3.png  — gráficos")
    print()
