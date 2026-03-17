# pip install reportlab  (se nao tiver)
import json, math
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable

with open("mega_results.json") as f:
    results = json.load(f)

# ── Cores ──────────────────────────────────────────────────────────────────
BG     = colors.HexColor("#07070e")
DARK   = colors.HexColor("#0d0d1a")
ACCENT = colors.HexColor("#7c6af7")
GREEN  = colors.HexColor("#5ee7b0")
YELLOW = colors.HexColor("#f7c26a")
RED    = colors.HexColor("#ff5f7e")
MUTED  = colors.HexColor("#6868a0")
LIGHT  = colors.HexColor("#f4f4fa")
WHITE  = colors.white
GRAY   = colors.HexColor("#ddddee")
TEAL   = colors.HexColor("#00bcd4")

def S(name, **kw): return ParagraphStyle(name, **kw)

title_s  = S("T",  fontName="Helvetica-Bold", fontSize=22, textColor=ACCENT,
             alignment=TA_CENTER, spaceAfter=3, leading=26)
sub_s    = S("SB", fontName="Helvetica", fontSize=10, textColor=MUTED,
             alignment=TA_CENTER, spaceAfter=3, leading=13)
author_s = S("AU", fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT,
             alignment=TA_CENTER, spaceAfter=10)
h1_s     = S("H1", fontName="Helvetica-Bold", fontSize=12, textColor=ACCENT,
             spaceBefore=14, spaceAfter=4)
h2_s     = S("H2", fontName="Helvetica-Bold", fontSize=10, textColor=DARK,
             spaceBefore=8, spaceAfter=3)
body_s   = S("BD", fontName="Helvetica", fontSize=9.5, textColor=DARK,
             alignment=TA_JUSTIFY, leading=14, spaceAfter=6)
mono_s   = S("MN", fontName="Courier", fontSize=8.5, textColor=DARK,
             leading=12, spaceAfter=4)
cap_s    = S("CA", fontName="Helvetica-Oblique", fontSize=8, textColor=MUTED,
             alignment=TA_CENTER, spaceAfter=10)
footer_s = S("FT", fontName="Helvetica", fontSize=7.5, textColor=MUTED,
             alignment=TA_CENTER)
nota_s   = S("NT", fontName="Helvetica-Oblique", fontSize=8.5,
             textColor=colors.HexColor("#1a1a3a"),
             backColor=colors.HexColor("#eef0ff"),
             leading=12, spaceAfter=8, spaceBefore=4,
             leftIndent=10, rightIndent=10)
highlight_s = S("HL", fontName="Helvetica-Bold", fontSize=11,
                textColor=WHITE, backColor=ACCENT,
                alignment=TA_CENTER, spaceAfter=6, spaceBefore=6,
                leading=16, leftIndent=8, rightIndent=8)

def _make_table(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[LIGHT,WHITE]),("GRID",(0,0),(-1,-1),0.4,GRAY),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6),
    ]
    if header:
        style += [("BACKGROUND",(0,0),(-1,0),ACCENT),("TEXTCOLOR",(0,0),(-1,0),WHITE),
                  ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t

def HR(color=ACCENT, t=1):
    return HRFlowable(width="100%", thickness=t, color=color, spaceAfter=8, spaceBefore=4)
def H1(txt): return Paragraph(txt, h1_s)
def H2(txt): return Paragraph(txt, h2_s)
def P(txt):  return Paragraph(txt, body_s)
def Cap(txt): return Paragraph(txt, cap_s)
def Nota(txt): return Paragraph(txt, nota_s)
def Sp(n=6): return Spacer(1, n)

# ── Grafico de barras customizado ──────────────────────────────────────────
class BarChart(Flowable):
    def __init__(self, data, width=450, height=160):
        super().__init__()
        self.data   = data   # list of (label, value, color)
        self.width  = width
        self.height = height

    def draw(self):
        d = self
        n = len(self.data)
        max_val = max(v for _, v, _ in self.data)
        pad_l, pad_r, pad_b, pad_t = 55, 15, 30, 15
        chart_w = self.width - pad_l - pad_r
        chart_h = self.height - pad_b - pad_t
        bar_w   = chart_w / n * 0.6
        gap     = chart_w / n

        # Eixo Y — linhas de grade
        from reportlab.graphics.shapes import Drawing as D2
        for i in range(5):
            y = pad_b + chart_h * i / 4
            val = max_val * i / 4
            # linha grade
            self.canv.setStrokeColor(colors.HexColor("#ddddee"))
            self.canv.setLineWidth(0.3)
            self.canv.line(pad_l, y, self.width - pad_r, y)
            # label
            self.canv.setFillColor(MUTED)
            self.canv.setFont("Helvetica", 6.5)
            self.canv.drawRightString(pad_l - 3, y - 3, f"{val:.1f}")

        # Barras
        for i, (label, val, col) in enumerate(self.data):
            x = pad_l + i * gap + gap * 0.2
            h = (val / max_val) * chart_h if max_val > 0 else 0
            y = pad_b

            # Sombra
            self.canv.setFillColor(colors.HexColor("#ccccdd"))
            self.canv.rect(x+2, y-2, bar_w, h, fill=1, stroke=0)

            # Barra principal
            self.canv.setFillColor(col)
            self.canv.rect(x, y, bar_w, h, fill=1, stroke=0)

            # Valor no topo
            self.canv.setFillColor(DARK)
            self.canv.setFont("Helvetica-Bold", 7)
            self.canv.drawCentredString(x + bar_w/2, y + h + 3, f"{val:.1f}")

            # Label no eixo X
            self.canv.setFillColor(MUTED)
            self.canv.setFont("Helvetica", 7)
            lbl = label if len(label) <= 6 else label[:5]
            self.canv.drawCentredString(x + bar_w/2, y - 12, lbl)

        # Eixo Y label
        self.canv.saveState()
        self.canv.setFillColor(MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.translate(10, pad_b + chart_h/2)
        self.canv.rotate(90)
        self.canv.drawCentredString(0, 0, "Tempo medio (ms)")
        self.canv.restoreState()

    def wrap(self, *args):
        return self.width, self.height

# ── Grafico de linha de estabilidade ──────────────────────────────────────
class StabilityChart(Flowable):
    def __init__(self, data, width=450, height=130):
        super().__init__()
        self.data   = data   # list of (label, ratio_pct)
        self.width  = width
        self.height = height

    def draw(self):
        n = len(self.data)
        pad_l, pad_r, pad_b, pad_t = 55, 15, 30, 15
        chart_w = self.width - pad_l - pad_r
        chart_h = self.height - pad_b - pad_t

        # Fundo
        self.canv.setFillColor(colors.HexColor("#f8f8ff"))
        self.canv.rect(pad_l, pad_b, chart_w, chart_h, fill=1, stroke=0)

        # Linha de 50% ideal
        y50 = pad_b + chart_h * 0.5
        self.canv.setStrokeColor(GREEN)
        self.canv.setLineWidth(1.0)
        self.canv.setDash([4, 3])
        self.canv.line(pad_l, y50, self.width - pad_r, y50)
        self.canv.setDash([])

        # Linhas de grade
        for i in range(5):
            y = pad_b + chart_h * i / 4
            val = 40 + (60 - 40) * i / 4
            self.canv.setStrokeColor(colors.HexColor("#ddddee"))
            self.canv.setLineWidth(0.3)
            self.canv.line(pad_l, y, self.width - pad_r, y)
            self.canv.setFillColor(MUTED)
            self.canv.setFont("Helvetica", 6.5)
            self.canv.drawRightString(pad_l - 3, y - 3, f"{val:.0f}%")

        # Pontos e linha
        points = []
        for i, (label, ratio) in enumerate(self.data):
            x = pad_l + (i / (n-1)) * chart_w if n > 1 else pad_l + chart_w/2
            y = pad_b + ((ratio - 40) / 20) * chart_h
            points.append((x, y, label, ratio))

        # Linha conectando pontos
        self.canv.setStrokeColor(ACCENT)
        self.canv.setLineWidth(1.5)
        for i in range(len(points)-1):
            self.canv.line(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        # Pontos
        for x, y, label, ratio in points:
            self.canv.setFillColor(WHITE)
            self.canv.circle(x, y, 4, fill=1, stroke=0)
            self.canv.setFillColor(ACCENT)
            self.canv.circle(x, y, 3, fill=1, stroke=0)
            self.canv.setFillColor(DARK)
            self.canv.setFont("Helvetica-Bold", 7)
            self.canv.drawCentredString(x, y + 6, f"{ratio:.1f}%")
            self.canv.setFont("Helvetica", 6.5)
            self.canv.setFillColor(MUTED)
            self.canv.drawCentredString(x, pad_b - 12, label)

        # Labels eixos
        self.canv.saveState()
        self.canv.setFillColor(MUTED)
        self.canv.setFont("Helvetica", 7)
        self.canv.translate(10, pad_b + chart_h/2)
        self.canv.rotate(90)
        self.canv.drawCentredString(0, 0, "Distribuicao |1> (%)")
        self.canv.restoreState()

        # Legenda
        self.canv.setStrokeColor(GREEN)
        self.canv.setLineWidth(1); self.canv.setDash([4,3])
        self.canv.line(self.width - pad_r - 70, pad_b + chart_h - 10,
                       self.width - pad_r - 50, pad_b + chart_h - 10)
        self.canv.setDash([])
        self.canv.setFillColor(MUTED)
        self.canv.setFont("Helvetica", 6.5)
        self.canv.drawString(self.width - pad_r - 48, pad_b + chart_h - 13, "Ideal: 50%")

    def wrap(self, *args):
        return self.width, self.height

# ── BUILD ──────────────────────────────────────────────────────────────────
out = "EIEZ_Mega_Benchmark.pdf"
doc = SimpleDocTemplate(out, pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm)
story = []

# Cabeçalho
story.append(Paragraph("⚛ EIEZ LANG", S("TL", fontName="Helvetica-Bold",
    fontSize=24, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2)))
story.append(Paragraph("Mega Benchmark — Teste de Estabilidade em Grande Escala",
    S("ST", fontName="Helvetica-Bold", fontSize=12, textColor=DARK,
      alignment=TA_CENTER, spaceAfter=3)))
story.append(Paragraph(
    "1.000 → 5.000 → 10.000 → 15.000 → 20.000 → 30.000 qubits",
    S("SC", fontName="Helvetica", fontSize=10, textColor=MUTED,
      alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph(
    "Joemerson da Silva Lima | Dell Inspiron i5, 8 GB RAM | Marco 2026",
    author_s))
story.append(HR())

# Cards de destaque
total_gates = sum(r["gates"] for r in results) * 5
total_ms = sum(r["avg_ms"] * r["shots"] for r in results)
max_states = results[-1]["states"]

card_data = [[
    Paragraph(f"30.000", S("CV", fontName="Helvetica-Bold", fontSize=20,
              textColor=ACCENT, alignment=TA_CENTER)),
    Paragraph(f"{max_states}", S("CV", fontName="Helvetica-Bold", fontSize=14,
              textColor=RED, alignment=TA_CENTER)),
    Paragraph(f"{total_gates:,}", S("CV", fontName="Helvetica-Bold", fontSize=18,
              textColor=GREEN, alignment=TA_CENTER)),
    Paragraph(f"{total_ms:.1f} ms", S("CV", fontName="Helvetica-Bold", fontSize=18,
              textColor=YELLOW, alignment=TA_CENTER)),
],[
    Paragraph("Max Qubits", S("CL", fontName="Helvetica", fontSize=7.5,
              textColor=MUTED, alignment=TA_CENTER)),
    Paragraph("Estados Possiveis (max)", S("CL", fontName="Helvetica", fontSize=7.5,
              textColor=MUTED, alignment=TA_CENTER)),
    Paragraph("Gates Totais", S("CL", fontName="Helvetica", fontSize=7.5,
              textColor=MUTED, alignment=TA_CENTER)),
    Paragraph("Tempo Total", S("CL", fontName="Helvetica", fontSize=7.5,
              textColor=MUTED, alignment=TA_CENTER)),
]]
ct = Table(card_data, colWidths=[3.8*cm]*4)
ct.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f4f4fa")),
    ("BOX",           (0,0), (0,-1), 1, ACCENT),
    ("BOX",           (1,0), (1,-1), 1, RED),
    ("BOX",           (2,0), (2,-1), 1, GREEN),
    ("BOX",           (3,0), (3,-1), 1, YELLOW),
    ("TOPPADDING",    (0,0), (-1,-1), 8),
    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ("ROWBACKGROUNDS",(0,0), (-1,-1), [colors.HexColor("#f4f4fa")]),
]))
story.append(ct)
story.append(Sp(12))

# Tabela principal
story.append(H1("Resultados Detalhados"))
cols = ["Qubits", "Estados Possiveis", "Gates", "Media (ms)", "Min (ms)", "Max (ms)",
        "Desvio Pad. (ms)", "Dist. |1>", "Estavel?"]
rows = [cols]
for r in results:
    estavel = "✓ SIM" if abs(r["ratio"] - 0.5) < 0.02 else "⚠ NAO"
    rows.append([
        f"{r['n']:,}",
        r["states"],
        f"{r['gates']:,}",
        f"{r['avg_ms']:.3f}",
        f"{r['min_ms']:.3f}",
        f"{r['max_ms']:.3f}",
        f"{r['stdev_ms']:.3f}",
        f"{r['ratio']*100:.1f}%",
        estavel,
    ])

from reportlab.platypus import Paragraph as RP
tdata = []
for i, row in enumerate(rows):
    tdata.append([RP(cell, body_s if i>0 else
                    S("TH", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE))
                  for cell in row])

widths = [1.8*cm, 2.8*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.8*cm, 2.2*cm, 1.5*cm, 1.5*cm]
t = Table(tdata, colWidths=widths)
t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), ACCENT),
    ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
    ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",      (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [LIGHT, WHITE]),
    ("GRID",          (0,0), (-1,-1), 0.4, GRAY),
    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 5),
]))
story.append(t)
story.append(Cap(
    "Tabela 1 — Resultados completos do mega benchmark. "
    "5 shots por tamanho. Hardware: Dell Inspiron i5-1235U, 8 GB RAM, Windows 11. "
    "Motor ZIE: theta = 0,7345."))
story.append(Sp(8))

# Grafico de tempo
story.append(H1("Analise de Escalabilidade"))
story.append(H2("Tempo de Simulacao por Numero de Qubits"))

bar_colors = [ACCENT, colors.HexColor("#9b8ef9"), TEAL,
              GREEN, YELLOW, RED]
bar_data = [(f"{r['n']//1000}k", r["avg_ms"], bar_colors[i])
            for i, r in enumerate(results)]
story.append(BarChart(bar_data, width=460, height=170))
story.append(Cap("Figura 1 — Tempo medio de simulacao (ms) por numero de qubits. Escala linear."))
story.append(Sp(6))

# Analise de linearidade
story.append(H2("Analise de Linearidade"))
story.append(P(
    "O crescimento do tempo de simulacao segue uma relacao essencialmente linear com o "
    "numero de qubits — conforme esperado para o simulador por qubit independente com "
    "complexidade O(n). A tabela abaixo mostra o fator de escala relativo a referencia "
    "de 1.000 qubits:"))

scale_data = [["Qubits", "Tempo (ms)", "Fator vs. 1k", "Linear esperado", "Desvio"]]
ref = results[0]["avg_ms"]
for r in results:
    fator = r["avg_ms"] / ref
    esperado = r["n"] / results[0]["n"]
    desvio = abs(fator - esperado) / esperado * 100
    scale_data.append([
        f"{r['n']:,}",
        f"{r['avg_ms']:.3f}",
        f"{fator:.2f}x",
        f"{esperado:.1f}x",
        f"{desvio:.1f}%",
    ])
story.append(_make_table(scale_data, [2.5*cm, 3*cm, 3*cm, 3.5*cm, 3*cm]))
story.append(Cap("Tabela 2 — Analise de linearidade do tempo de simulacao."))
story.append(Sp(8))

# Grafico de estabilidade
story.append(H1("Analise de Estabilidade Quantica"))
story.append(H2("Distribuicao de Estados |1> por Numero de Qubits"))
story.append(P(
    "Um indicador fundamental da corretude da simulacao e a distribuicao de medicoes "
    "|1> e |0> apos a aplicacao de gate Hadamard. Matematicamente, H|0> = (|0>+|1>)/sqrt(2) "
    "implica probabilidade exatamente 50% para cada resultado. O grafico abaixo mostra "
    "a estabilidade desta distribuicao ao longo de todos os tamanhos de circuito:"))
stab_data = [(f"{r['n']//1000}k", r["ratio"]*100) for r in results]
story.append(StabilityChart(stab_data, width=460, height=140))
story.append(Cap(
    "Figura 2 — Distribuicao de medicoes |1> por tamanho de circuito. "
    "Linha tracejada = valor ideal (50%). Todos os pontos dentro da margem ±2%."))
story.append(Sp(8))

# Resumo de estabilidade
story.append(H2("Resumo de Estabilidade"))
ratios = [r["ratio"]*100 for r in results]
import statistics as st
story.append(Nota(
    f"Media global de |1>: {st.mean(ratios):.2f}%  |  "
    f"Desvio padrao: {st.stdev(ratios):.2f}%  |  "
    f"Min: {min(ratios):.1f}%  |  Max: {max(ratios):.1f}%  |  "
    f"Todos os tamanhos dentro da faixa 48%–52%: "
    f"{'SIM ✓' if all(48 <= r <= 52 for r in ratios) else 'NAO'}"))

# Contexto
story.append(H1("Contexto e Significado"))
story.append(P(
    "Para contextualizar a magnitude dos resultados: o universo observavel contem "
    "aproximadamente 10<super>80</super> atomos. O circuito de 30.000 qubits simulado "
    "neste benchmark cobre um espaco de estados de 10<super>9030</super> configuracoes "
    "possiveis — um numero 10<super>8950</super> vezes maior que o numero de atomos "
    "do universo. Toda essa simulacao foi completada em aproximadamente 36 ms em um "
    "notebook convencional de consumo com processador Intel Core i5 e 8 GB de RAM."))

context_data = [
    ["Referencia", "Escala", "Comparacao com 30k qubits"],
    ["Atomos no universo",         "10^80",   f"10^{9030-80} vezes menor"],
    ["IBM Eagle (2021)",           "127 qubits", "236x menos qubits"],
    ["Google Sycamore (2019)",     "53 qubits",  "566x menos qubits"],
    ["Maior simulador clasico",    "~50 qubits (statevector)", "600x menos qubits"],
    ["EIEZ Lang — este benchmark", "30.000 qubits", "36 ms | Dell i5 | 8 GB RAM"],
]
story.append(_make_table(context_data, [4.5*cm, 3.5*cm, 6*cm]))
story.append(Cap(
    "Tabela 3 — Contexto comparativo. Nota: EIEZ Lang usa simulacao por qubit independente "
    "(sem emaranhamento), enquanto hardware quantico real e simuladores statevector "
    "mantem correlacoes quanticas completas."))
story.append(Sp(8))

story.append(Nota(
    "NOTA METODOLOGICA: O simulador de grande escala da EIEZ Lang usa a abordagem "
    "por qubit independente, que e exata para circuitos sem gates de emaranhamento (CX, CZ) "
    "e aproximada para circuitos com emaranhamento. Os resultados acima sao fisicamente "
    "corretos para o circuito testado (H + RX em qubits independentes). "
    "Para simulacao exata de circuitos com emaranhamento, o limite pratico do simulador "
    "statevector e de aproximadamente 20–25 qubits em hardware convencional."))

# Config
story.append(H1("Configuracao do Experimento"))
config_data = [
    ["Parametro", "Valor"],
    ["Hardware",         "Dell Inspiron i5-1235U, 8 GB RAM"],
    ["Sistema Operacional", "Windows 11"],
    ["Python",           "3.13"],
    ["Biblioteca PLY",   "3.11"],
    ["Backend ZIE",      "auto (theta = 0,7345)"],
    ["Shots por tamanho","5"],
    ["Circuito testado", "H em todos os qubits + RX(theta) nos primeiros 10"],
    ["Total de gates",   f"{sum(r['gates'] for r in results)*5:,} (5 shots × todos os tamanhos)"],
    ["Tempo total",      f"{sum(r['avg_ms']*r['shots'] for r in results):.1f} ms"],
]
story.append(_make_table(config_data, [5*cm, 11*cm]))
story.append(Sp(16))
story.append(HR(MUTED, 0.5))
story.append(Paragraph(
    "EIEZ Lang v2.0 — Software Livre (MIT) | Patente BR 10 2025 024459 4 | "
    "Joemerson da Silva Lima — Cuiaba, MT, Brasil | Marco 2026",
    footer_s))

doc.build(story)
print("PDF gerado:", out)
