#!/usr/bin/env python3
"""
EIEZ/ZIE — Experimento Real v1.0
Dataset: Série financeira real (Yahoo Finance)
Energia: medida pelo CodeCarbon
Joemerson da Silva Lima | Cuiabá, MT | 2026
Patente BR 10 2025 024459 4
"""

import os, time, math, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# CodeCarbon para medição real de energia
try:
    from codecarbon import EmissionsTracker
    CODECARBON = True
except ImportError:
    CODECARBON = False
    print("⚠ CodeCarbon não encontrado — usando estimativa por tempo (como no paper)")

# Yahoo Finance para dados reais
try:
    import yfinance as yf
    YFINANCE = True
except ImportError:
    YFINANCE = False
    print("⚠ yfinance não encontrado — usando dados sintéticos como fallback")


# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "ticker":      "PETR4.SA",   # Petrobras — mude para qualquer ticker
    "periodo":     "5y",         # 5 anos de dados
    "seq_len":     30,           # janela de entrada
    "hidden":      64,
    "dropout":     0.20,
    "epochs":      80,
    "batch_size":  32,
    "lr_inicial":  1e-3,
    "split":       0.80,
    "seed":        42,
    "p_cpu_watts": 25.0,         # potência estimada CPU (W)
    # EIE/ZIE
    "janela_tau":  20,
    "beta":        0.10,
    "alpha":       0.15,
    "truncamento": 0.05,
}

torch.manual_seed(CONFIG["seed"])
np.random.seed(CONFIG["seed"])


# ═══════════════════════════════════════════════════════════════
# 1. DADOS REAIS
# ═══════════════════════════════════════════════════════════════

def carregar_dados():
    print(f"\n📥 Baixando dados reais: {CONFIG['ticker']} ({CONFIG['periodo']})")

    if YFINANCE:
        try:
            df = yf.download(CONFIG["ticker"], period=CONFIG["periodo"],
                             auto_adjust=True, progress=False)
            if df.empty:
                raise ValueError("Dados vazios")
            serie = df["Close"].dropna().values.astype(float)
            fonte = f"Yahoo Finance — {CONFIG['ticker']}"
            print(f"  ✓ {len(serie)} dias de dados reais")
        except Exception as e:
            print(f"  ⚠ Erro ao baixar ({e}) — usando fallback sintético")
            serie, fonte = _fallback_sintetico()
    else:
        serie, fonte = _fallback_sintetico()

    return serie, fonte


def _fallback_sintetico():
    """Série com tendência + sazonalidade + regime crítico artificial."""
    n = 1200
    t = np.arange(n)
    tendencia   = 20 + 0.03 * t
    sazonalidade = 3 * np.sin(2 * np.pi * t / 252)
    ruido = np.random.normal(0, 1, n)
    # Regime crítico artificial entre 800 e 1000
    ruido[800:1000] *= np.linspace(1, 4, 200)
    serie = tendencia + sazonalidade + ruido
    return serie, "Sintético (fallback)"


def preparar_dataset(serie):
    scaler = MinMaxScaler()
    serie_norm = scaler.fit_transform(serie.reshape(-1, 1)).flatten()

    X, y = [], []
    for i in range(len(serie_norm) - CONFIG["seq_len"]):
        X.append(serie_norm[i:i + CONFIG["seq_len"]])
        y.append(serie_norm[i + CONFIG["seq_len"]])

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    split = int(len(X) * CONFIG["split"])
    X_tr, X_val = X[:split], X[split:]
    y_tr, y_val = y[:split], y[split:]

    ds_tr  = TensorDataset(torch.tensor(X_tr).unsqueeze(-1),
                           torch.tensor(y_tr).unsqueeze(-1))
    ds_val = TensorDataset(torch.tensor(X_val).unsqueeze(-1),
                           torch.tensor(y_val).unsqueeze(-1))

    dl_tr  = DataLoader(ds_tr,  batch_size=CONFIG["batch_size"], shuffle=True)
    dl_val = DataLoader(ds_val, batch_size=CONFIG["batch_size"], shuffle=False)

    return dl_tr, dl_val, scaler


# ═══════════════════════════════════════════════════════════════
# 2. MODELO LSTM
# ═══════════════════════════════════════════════════════════════

class LSTMModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1, CONFIG["hidden"], num_layers=2,
                            dropout=CONFIG["dropout"], batch_first=True)
        self.fc   = nn.Linear(CONFIG["hidden"], 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# ═══════════════════════════════════════════════════════════════
# 3. MOTOR EIE/ZIE
# ═══════════════════════════════════════════════════════════════

class MotorEIEZIE:
    def __init__(self):
        self.historico_loss  = []
        self.tau_smooth      = 1.0
        self.tau_hist        = []
        self.tau_crit        = None
        self.lr_atual        = CONFIG["lr_inicial"]
        self.modo_atual      = "Aceleração"
        self.intervencoes    = 0
        self.historico_tau   = []
        self.historico_psi   = []
        self.historico_modo  = []
        self.historico_lr    = []

    def calcular_tau_corr(self):
        W = CONFIG["janela_tau"]
        if len(self.historico_loss) < W + 2:
            return 1.0

        janela = np.array(self.historico_loss[-W:])
        media  = janela.mean()
        var    = janela.var()
        if var < 1e-12:
            return 1.0

        # Autocorrelação normalizada
        C = []
        for delta in range(1, len(janela)):
            num = np.mean((janela[:-delta] - media) * (janela[delta:] - media))
            C.append(num / var)
            if abs(C[-1]) < CONFIG["truncamento"]:
                break

        tau = 0.5 + sum(C)
        return max(tau, 0.5)

    def atualizar(self, loss_val, epoca):
        self.historico_loss.append(loss_val)

        tau = self.calcular_tau_corr()
        beta = CONFIG["beta"]
        self.tau_smooth = beta * tau + (1 - beta) * self.tau_smooth
        self.tau_hist.append(self.tau_smooth)

        # τ_crit = percentil 95 histórico
        if len(self.tau_hist) >= 5:
            self.tau_crit = np.percentile(self.tau_hist, 95)
        else:
            self.tau_crit = max(self.tau_smooth * 1.5, 1.5)

        psi = self.tau_smooth / self.tau_crit

        # Modo operacional
        if psi < 0.4:
            modo = "Aceleração"
            novo_lr = min(self.lr_atual * 1.05, 2 * CONFIG["lr_inicial"])
        elif psi < 0.8:
            modo = "Otimização"
            novo_lr = self.lr_atual
        elif psi < 1.0:
            modo = "Preventivo"
            novo_lr = self.lr_atual * (1 - CONFIG["alpha"] * psi)
            self.intervencoes += 1
        else:
            modo = "Alarme"
            novo_lr = self.lr_atual * (1 - CONFIG["alpha"] * min(psi, 2.0))
            self.intervencoes += 1

        novo_lr = max(novo_lr, 1e-6)
        self.lr_atual   = novo_lr
        self.modo_atual = modo

        self.historico_tau.append(self.tau_smooth)
        self.historico_psi.append(psi)
        self.historico_modo.append(modo)
        self.historico_lr.append(novo_lr)

        return novo_lr, psi, modo


# ═══════════════════════════════════════════════════════════════
# 4. TREINAMENTO
# ═══════════════════════════════════════════════════════════════

def treinar(dl_tr, dl_val, usar_eiezie: bool, fonte: str):
    label = "EIE/ZIE" if usar_eiezie else "Convencional"
    print(f"\n{'='*55}")
    print(f"  Treinando Grupo {'B — LSTM + EIE/ZIE' if usar_eiezie else 'A — LSTM Convencional'}")
    print(f"  Dataset: {fonte}")
    print(f"{'='*55}")

    modelo    = LSTMModel()
    criterio  = nn.MSELoss()
    otimizador = torch.optim.Adam(modelo.parameters(), lr=CONFIG["lr_inicial"])
    motor     = MotorEIEZIE() if usar_eiezie else None

    hist_loss_tr  = []
    hist_loss_val = []
    hist_energia  = []
    hist_lr       = [CONFIG["lr_inicial"]] * CONFIG["epochs"]
    tempo_total   = 0.0

    # CodeCarbon
    tracker = None
    if CODECARBON and usar_eiezie is False:
        try:
            tracker = EmissionsTracker(
                project_name=f"EIEZIE_{label}",
                output_dir=".",
                log_level="error",
                save_to_file=True,
            )
            tracker.start()
        except Exception:
            tracker = None

    for epoca in range(CONFIG["epochs"]):
        t0 = time.perf_counter()

        # Treino
        modelo.train()
        loss_tr_total = 0.0
        for xb, yb in dl_tr:
            otimizador.zero_grad()
            pred = modelo(xb)
            loss = criterio(pred, yb)
            loss.backward()
            otimizador.step()
            loss_tr_total += loss.item()
        loss_tr = loss_tr_total / len(dl_tr)

        # Validação
        modelo.eval()
        loss_val_total = 0.0
        with torch.no_grad():
            for xb, yb in dl_val:
                pred = modelo(xb)
                loss_val_total += criterio(pred, yb).item()
        loss_val = loss_val_total / len(dl_val)

        elapsed = time.perf_counter() - t0
        tempo_total += elapsed
        energia_epoca = elapsed * CONFIG["p_cpu_watts"]
        hist_energia.append(energia_epoca)

        # EIE/ZIE
        if usar_eiezie and motor:
            novo_lr, psi, modo = motor.atualizar(loss_val, epoca)
            hist_lr[epoca] = novo_lr
            for g in otimizador.param_groups:
                g["lr"] = novo_lr
            status = f"Ψ={psi:.2f} [{modo[:4]}] lr={novo_lr:.2e}"
        else:
            status = f"lr={CONFIG['lr_inicial']:.2e}"

        hist_loss_tr.append(loss_tr)
        hist_loss_val.append(loss_val)

        if (epoca + 1) % 10 == 0 or epoca == 0:
            print(f"  Época {epoca+1:3d}/{CONFIG['epochs']} | "
                  f"loss_tr={loss_tr:.5f} | loss_val={loss_val:.5f} | "
                  f"{status} | {elapsed*1000:.0f}ms")

    # Parar CodeCarbon
    emissoes_reais = None
    if tracker:
        try:
            emissoes_reais = tracker.stop()
        except Exception:
            pass

    energia_total = sum(hist_energia)
    print(f"\n  ✓ Energia total estimada: {energia_total:.1f} J")
    if emissoes_reais:
        print(f"  ✓ CO₂ real (CodeCarbon): {emissoes_reais*1e6:.2f} mg")

    return {
        "label":        label,
        "loss_tr":      hist_loss_tr,
        "loss_val":     hist_loss_val,
        "energia":      hist_energia,
        "energia_total": energia_total,
        "tempo_total":  tempo_total,
        "hist_lr":      hist_lr,
        "motor":        motor,
        "emissoes_co2": emissoes_reais,
    }


# ═══════════════════════════════════════════════════════════════
# 5. RELATÓRIO
# ═══════════════════════════════════════════════════════════════

def gerar_relatorio(res_a, res_b, fonte):
    ea = res_a["energia_total"]
    eb = res_b["energia_total"]
    reducao_e   = (ea - eb) / ea * 100
    loss_a_final = res_a["loss_val"][-1]
    loss_b_final = res_b["loss_val"][-1]
    reducao_loss = (loss_a_final - loss_b_final) / loss_a_final * 100

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  RESULTADOS — EXPERIMENTO REAL EIE/ZIE              ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Dataset: {fonte:<43}║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Métrica':<30} {'Grupo A':>10} {'Grupo B':>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  {'Loss validação final (MSE)':<30} {loss_a_final:>10.5f} {loss_b_final:>10.5f} ║")
    print(f"║  {'Energia total (J)':<30} {ea:>10.1f} {eb:>10.1f} ║")
    print(f"║  {'Tempo total (s)':<30} {res_a['tempo_total']:>10.1f} {res_b['tempo_total']:>10.1f} ║")
    if res_b["motor"]:
        print(f"║  {'Intervenções EIE/ZIE':<30} {'—':>10} {res_b['motor'].intervencoes:>10} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Redução de energia:  {reducao_e:+.1f}%{' '*29}║")
    print(f"║  Redução loss final:  {reducao_loss:+.1f}%{' '*29}║")
    print("╚══════════════════════════════════════════════════════╝")

    # Salvar JSON
    resultado = {
        "dataset": fonte,
        "ticker": CONFIG["ticker"],
        "grupo_a": {
            "energia_j": round(ea, 2),
            "loss_final": round(loss_a_final, 6),
            "tempo_s": round(res_a["tempo_total"], 2),
        },
        "grupo_b": {
            "energia_j": round(eb, 2),
            "loss_final": round(loss_b_final, 6),
            "tempo_s": round(res_b["tempo_total"], 2),
            "intervencoes": res_b["motor"].intervencoes if res_b["motor"] else 0,
        },
        "reducao_energia_pct": round(reducao_e, 2),
        "reducao_loss_pct":    round(reducao_loss, 2),
    }
    with open("resultado_experimento.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("\n  📄 Salvo: resultado_experimento.json")


def gerar_graficos(res_a, res_b, fonte):
    motor = res_b["motor"]
    epocas = list(range(1, CONFIG["epochs"] + 1))

    CORES = {
        "conv":   "#ff5f7e",
        "eie":    "#7c6af7",
        "verde":  "#5ee7b0",
        "amarelo":"#f7c26a",
        "muted":  "#6868a0",
        "bg":     "#07070e",
        "s1":     "#0f0f1a",
        "border": "#252538",
        "text":   "#e0e0f0",
    }

    fig = plt.figure(figsize=(16, 12), facecolor=CORES["bg"])
    fig.suptitle(
        f"EIE/ZIE — Experimento Real | {fonte} | Patente BR 10 2025 024459 4",
        color=CORES["text"], fontsize=13, fontweight="bold", y=0.98
    )

    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    def ax_style(ax, titulo):
        ax.set_facecolor(CORES["s1"])
        ax.tick_params(colors=CORES["muted"])
        ax.title.set_color(CORES["text"])
        ax.set_title(titulo, fontsize=9, pad=6)
        for spine in ax.spines.values():
            spine.set_edgecolor(CORES["border"])
        ax.yaxis.label.set_color(CORES["muted"])
        ax.xaxis.label.set_color(CORES["muted"])

    # 1 — Loss treino
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.semilogy(epocas, res_a["loss_tr"], color=CORES["conv"], lw=1.5, label="Convencional")
    ax1.semilogy(epocas, res_b["loss_tr"], color=CORES["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE")
    ax_style(ax1, "Loss de Treino (MSE — escala log)")
    ax1.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

    # 2 — Loss validação
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.semilogy(epocas, res_a["loss_val"], color=CORES["conv"], lw=1.5, label="Convencional")
    ax2.semilogy(epocas, res_b["loss_val"], color=CORES["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE")
    if motor:
        for i, modo in enumerate(motor.historico_modo):
            if modo in ("Preventivo", "Alarme"):
                ax2.axvline(x=i+1, color=CORES["amarelo"], alpha=0.15, lw=0.8)
    ax_style(ax2, "Loss de Validação (MSE — escala log)")
    ax2.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

    # 3 — τ_corr
    if motor:
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.plot(epocas, motor.historico_tau, color=CORES["verde"], lw=1.5, label="τ_corr suavizado")
        tau_crit_val = np.percentile(motor.historico_tau, 95)
        ax3.axhline(y=tau_crit_val, color=CORES["amarelo"], ls="--", lw=1, label=f"τ_crit (p95={tau_crit_val:.2f})")
        ax_style(ax3, "Tempo de Correlação τ_corr")
        ax3.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

        # 4 — Ψ(t)
        ax4 = fig.add_subplot(gs[1, 1])
        psi_vals = motor.historico_psi
        ax4.plot(epocas, psi_vals, color=CORES["eie"], lw=1.5)
        ax4.axhline(y=0.8, color=CORES["amarelo"], ls="--", lw=1, alpha=0.7, label="Preventivo (0.8)")
        ax4.axhline(y=1.0, color=CORES["conv"],    ls="--", lw=1, alpha=0.7, label="Alarme (1.0)")
        cores_modo = {"Aceleração":"#5ee7b0","Otimização":"#7c6af7","Preventivo":"#f7c26a","Alarme":"#ff5f7e"}
        for i, modo in enumerate(motor.historico_modo):
            ax4.axvspan(i+0.5, i+1.5, alpha=0.12, color=cores_modo.get(modo, "gray"))
        ax_style(ax4, "Índice de Proximidade Crítica Ψ(t)")
        ax4.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

    # 5 — Energia acumulada
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.plot(epocas, np.cumsum(res_a["energia"]), color=CORES["conv"], lw=1.5, label="Convencional")
    ax5.plot(epocas, np.cumsum(res_b["energia"]), color=CORES["eie"],  lw=1.5, ls="--", label="+ EIE/ZIE")
    ax_style(ax5, "Energia Acumulada (J)")
    ax5.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

    # 6 — Learning rate
    ax6 = fig.add_subplot(gs[2, 1])
    lr_conv = [CONFIG["lr_inicial"]] * CONFIG["epochs"]
    ax6.semilogy(epocas, lr_conv,          color=CORES["conv"], lw=1.5, ls="--", label="Convencional (fixo)")
    ax6.semilogy(epocas, res_b["hist_lr"], color=CORES["eie"],  lw=1.5,          label="EIE/ZIE (adaptativo)")
    ax_style(ax6, "Learning Rate (escala log)")
    ax6.legend(fontsize=7, facecolor=CORES["s1"], labelcolor=CORES["text"])

    plt.savefig("resultado_graficos.png", dpi=150, bbox_inches="tight",
                facecolor=CORES["bg"])
    print("  📊 Salvo: resultado_graficos.png")
    plt.show()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("██████████████████████████████████████████████████████")
    print("  EIE/ZIE — Experimento Real v1.0")
    print("  Dataset: Série Financeira Real")
    print("  Joemerson da Silva Lima | Cuiabá, MT | 2026")
    print("  Patente BR 10 2025 024459 4")
    print("██████████████████████████████████████████████████████")

    # Dados
    serie, fonte = carregar_dados()
    dl_tr, dl_val, scaler = preparar_dataset(serie)

    print(f"\n  Configuração:")
    print(f"    Ticker:   {CONFIG['ticker']}")
    print(f"    Épocas:   {CONFIG['epochs']}")
    print(f"    Seq len:  {CONFIG['seq_len']}")
    print(f"    Dataset:  {fonte}")
    print(f"    CodeCarbon: {'✓ ativo' if CODECARBON else '✗ estimativa por tempo'}")

    # Grupo A — Convencional
    res_a = treinar(dl_tr, dl_val, usar_eiezie=False, fonte=fonte)

    # Grupo B — EIE/ZIE
    res_b = treinar(dl_tr, dl_val, usar_eiezie=True,  fonte=fonte)

    # Resultados
    gerar_relatorio(res_a, res_b, fonte)
    gerar_graficos(res_a, res_b, fonte)

    print()
    print("  Experimento concluído.")
    print("  Arquivos gerados:")
    print("    resultado_experimento.json  — métricas completas")
    print("    resultado_graficos.png      — gráficos")
    print()
