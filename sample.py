import math
import streamlit as st
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BESS Dashboard 2026–2036",
    page_icon="⚡",
    layout="wide",
)

# ── Colours ───────────────────────────────────────────────────────────────────
ACCENT  = "#00e5c8"
ACCENT2 = "#f5a623"
ACCENT3 = "#e94f4f"
ACCENT4 = "#a78bfa"
GRID_C  = "#1e2d3d"
BG_DARK = "#050d16"

# ── Dark theme CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
      background: #060e18 !important;
      color: #c0d8f0;
  }
  section[data-testid="stSidebar"] { background: #0a1520 !important; }
  section[data-testid="stSidebar"] * { color: #c0d8f0 !important; }
  .stSlider > div { color: #c0d8f0; }
  h1, h2, h3, h4 { color: #e8f4ff !important; }
  .kpi-box {
      background: #0a1520; border: 1px solid #1a2d42;
      border-radius: 10px; padding: 14px 18px; text-align: center;
  }
  .kpi-box.hi { background: rgba(0,229,200,.09); border-color: #00e5c8; }
  .kpi-label { font-size: 10px; color: #5a7a9a; text-transform: uppercase;
               letter-spacing: 1px; margin-bottom: 4px; }
  .kpi-value { font-size: 20px; font-weight: 800; font-family: 'Space Mono', monospace; }
  .kpi-sub   { font-size: 10px; color: #6a8aaa; margin-top: 3px; }
  .sec-title { font-size: 12px; font-weight: 700; color: #c0d8f0;
               text-transform: uppercase; letter-spacing: .4px;
               border-bottom: 1px solid #1e2d3d; padding-bottom: 8px;
               margin-bottom: 14px; }
  .insight-box {
      background: rgba(167,139,250,.1); border: 1px solid rgba(167,139,250,.35);
      border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;
  }
  .dur-label { font-size: 11px; color: #8aaccc; margin-bottom: 4px; }
  .dur-sub   { font-size: 10px; color: #5a7a9a; margin-bottom: 3px; }
  .dur-val   { font-size: 12px; font-family: 'Space Mono', monospace; margin-top: 3px; }
  .rec-row {
      background: #050d16; border: 1px solid #1a2d42;
      border-radius: 9px; padding: 11px 16px; margin-bottom: 8px;
  }
  .rec-row.best { background: rgba(0,229,200,.07); border-color: #00e5c8; }
  .stNumberInput input { background: #0a1520 !important; color: #00e5c8 !important;
                         border-color: #1e3050 !important; }
</style>
""", unsafe_allow_html=True)

# ── Physics helpers ───────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def concurrency_prob(sessions, session_minutes, op_hours):
    lam = sessions / op_hours
    mu  = 60 / session_minutes
    rho = min(lam / mu, 0.95)
    return rho * rho

def session_duration(energy_kwh, rated_kw, avail_total, n_sessions):
    share = min(rated_kw, avail_total / n_sessions)
    return (energy_kwh / share) * 60

def build_data(power120, power150, energy120, energy150,
               sess2026, sess2036, avail, op_hours, omie, premium, price, bess_power):
    total_avail = 100 + bess_power
    rows = []
    for i in range(11):
        year    = 2026 + i
        t       = i / 10
        sess    = lerp(sess2026, sess2036, t)
        op_days = 365 * (avail / 100)
        avg_min = ((energy120 / power120) + (energy150 / power150)) / 2 * 60
        p_conc  = concurrency_prob(sess, avg_min, op_hours)

        dur1_cp1 = session_duration(energy120, power120, total_avail, 1)
        dur1_cp2 = session_duration(energy150, power150, total_avail, 1)
        dur2_cp1 = session_duration(energy120, power120, total_avail, 2)
        dur2_cp2 = session_duration(energy150, power150, total_avail, 2)

        daily_e     = sess * energy120 + sess * energy150
        annual_e    = daily_e * op_days
        annual_cost = annual_e * (omie + premium) / 1000
        annual_rev  = annual_e * price
        margin      = annual_rev - annual_cost

        rows.append(dict(
            year=year, sess=round(sess),
            pConc=round(p_conc * 100, 1),
            dur1_cp1=round(dur1_cp1, 1), dur1_cp2=round(dur1_cp2, 1),
            dur2_cp1=round(dur2_cp1, 1), dur2_cp2=round(dur2_cp2, 1),
            annual_e=round(annual_e),
            annual_cost=round(annual_cost),
            annual_rev=round(annual_rev),
            margin=round(margin),
        ))
    return rows

def investment_cost(power, capacity):
    if power == 0:
        return 0, 0
    low  = round((capacity * 400 + power * 140 + 15000) / 5000) * 5000
    high = round((capacity * 570 + power * 200 + 15000) / 5000) * 5000
    return low, high

# ── Sidebar parameters ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Parâmetros")

    st.markdown("**CARREGADORES**")
    power120  = st.number_input("Potência CP1 (kW)",        50,  300, 120, 1)
    energy120 = st.number_input("Energia/sessão CP1 (kWh)", 10,  100,  30, 1)
    power150  = st.number_input("Potência CP2 (kW)",        50,  300, 150, 1)
    energy150 = st.number_input("Energia/sessão CP2 (kWh)", 10,  100,  33, 1)

    st.markdown("**UTILIZAÇÃO**")
    sess2026 = st.number_input("Sessões/dia 2026 (/charger)",  1,  30,  7, 1)
    sess2036 = st.number_input("Sessões/dia 2036 (/charger)",  1,  60, 14, 1)
    op_hours = st.number_input("Horas operação/dia (h)",       6,  24, 14, 1)
    avail    = st.number_input("Disponibilidade (%)",         50, 100, 95, 1)

    st.markdown("**ENERGIA**")
    omie    = st.number_input("OMIE base (€/MWh)",       20,  200,  60, 1)
    premium = st.number_input("Prémio indexado (€/MWh)",  0,  100,  25, 1)
    price   = st.number_input("Preço carregamento (€/kWh)", 0.15, 0.80, 0.32, 0.01, format="%.2f")

    st.markdown("**POTÊNCIA BESS A SIMULAR**")
    bess_options = {
        "Sem BESS": 0, "50 kW": 50, "75 kW ✅": 75,
        "100 kW": 100, "125 kW": 125, "150 kW": 150,
    }
    bess_label  = st.radio("", list(bess_options.keys()), index=2, label_visibility="collapsed")
    bess_power  = bess_options[bess_label]
    bess_cap    = 0 if bess_power == 0 else max(100, bess_power * 2)
    cost_low, cost_high = investment_cost(bess_power, bess_cap)
    cost_str = "—" if cost_low == 0 else f"{cost_low//1000}–{cost_high//1000} k€"
    st.caption(f"Capacidade auto: **{bess_cap} kWh** | Investimento: **{cost_str}**")

# ── Compute data ──────────────────────────────────────────────────────────────
data    = build_data(power120, power150, energy120, energy150,
                     sess2026, sess2036, avail, op_hours, omie, premium, price, bess_power)
data_no = build_data(power120, power150, energy120, energy150,
                     sess2026, sess2036, avail, op_hours, omie, premium, price, 0)
d0, d10   = data[0],    data[10]
d0n, d10n = data_no[0], data_no[10]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="font-size:10px;font-weight:700;letter-spacing:3px;color:{ACCENT};'
    f'text-transform:uppercase;font-family:monospace;margin-bottom:4px">'
    f'BESS · Load Balancing · Dimensionamento</div>',
    unsafe_allow_html=True,
)
st.markdown("# Gestão de Cargas + BESS — Análise 2026–2036")
st.caption("Potência gerida dinamicamente entre sessões ativas · BTE 100 kVA")

# ── Insight banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="insight-box">
  <span style="font-size:22px">⚖️</span>
  <span style="font-weight:800;color:#a78bfa;font-size:14px;margin-left:10px">
    Com Load Balancing, a BESS deixa de ser estruturalmente obrigatória
  </span>
  <p style="font-size:12px;color:#a0b8cc;line-height:1.7;margin-top:8px;margin-bottom:0">
    O sistema de gestão de cargas distribui os <strong style="color:#e0ecf8">100 kW da rede BTE</strong>
    dinamicamente entre as sessões ativas — nunca há sobrecarga da ligação. A BESS torna-se um
    <strong style="color:#a78bfa">investimento de qualidade de serviço</strong>: reduz os tempos de sessão
    quando há concorrência, e aumenta a competitividade do serviço.
  </p>
</div>
""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
bess_disp = "Sem BESS" if bess_power == 0 else f"{bess_power} kW"

for col, label, value, sub, hi in [
    (k1, "Prob. concorrência 2026", f"{d0['pConc']}%",  "Sessões simultâneas",    False),
    (k2, "Prob. concorrência 2036", f"{d10['pConc']}%", "Cresce com utilização",  True),
    (k3, "BESS selecionada",        bess_disp,           f"{bess_cap} kWh",        bess_power > 0),
    (k4, "Investimento estimado",   cost_str,            "Instalado",              False),
]:
    with col:
        cls = "kpi-box hi" if hi else "kpi-box"
        val_color = ACCENT if hi else "#e0ecf8"
        st.markdown(f"""
        <div class="{cls}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="color:{val_color}">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Duration bars helper ──────────────────────────────────────────────────────
def dur_bar_html(label, no_bess, with_bess, max_dur):
    improved  = with_bess < no_bess - 0.5
    bar_color = ACCENT if improved else "#6a8aaa"
    pct_no    = min(100, (no_bess   / max_dur) * 100)
    pct_wi    = min(100, (with_bess / max_dur) * 100)
    return f"""
    <div style="margin-bottom:12px">
      <div class="dur-label">{label}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div>
          <div class="dur-sub">Sem BESS (rede 100 kW)</div>
          <div style="height:7px;border-radius:4px;background:#1a2d42;overflow:hidden">
            <div style="height:100%;width:{pct_no:.1f}%;background:{ACCENT3};border-radius:4px"></div>
          </div>
          <div class="dur-val" style="color:{ACCENT3}">{no_bess:.1f} min</div>
        </div>
        <div>
          <div class="dur-sub">Com BESS selecionada</div>
          <div style="height:7px;border-radius:4px;background:#1a2d42;overflow:hidden">
            <div style="height:100%;width:{pct_wi:.1f}%;background:{bar_color};border-radius:4px"></div>
          </div>
          <div class="dur-val" style="color:{bar_color}">{with_bess:.1f} min</div>
        </div>
      </div>
    </div>"""

# ── Session durations ─────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">⏱️ Tempo de Sessão com Load Balancing + BESS</div>',
            unsafe_allow_html=True)
max_dur = max(d10n["dur2_cp1"], d10n["dur2_cp2"], 60)

col_26, col_36 = st.columns(2)
with col_26:
    st.markdown(f'<div style="font-size:11px;color:{ACCENT};font-weight:700;margin-bottom:12px">'
                f'2026 — {d0["sess"]} sessões/charger/dia</div>', unsafe_allow_html=True)
    for lbl, nob, wib in [
        ("CP1 (120 kW) — sessão única",    d0n["dur1_cp1"], d0["dur1_cp1"]),
        ("CP2 (150 kW) — sessão única",    d0n["dur1_cp2"], d0["dur1_cp2"]),
        ("CP1 — 2 sessões em simultâneo",  d0n["dur2_cp1"], d0["dur2_cp1"]),
        ("CP2 — 2 sessões em simultâneo",  d0n["dur2_cp2"], d0["dur2_cp2"]),
    ]:
        st.markdown(dur_bar_html(lbl, nob, wib, max_dur), unsafe_allow_html=True)

with col_36:
    st.markdown(f'<div style="font-size:11px;color:{ACCENT2};font-weight:700;margin-bottom:12px">'
                f'2036 — {d10["sess"]} sessões/charger/dia</div>', unsafe_allow_html=True)
    for lbl, nob, wib in [
        ("CP1 (120 kW) — sessão única",    d10n["dur1_cp1"], d10["dur1_cp1"]),
        ("CP2 (150 kW) — sessão única",    d10n["dur1_cp2"], d10["dur1_cp2"]),
        ("CP1 — 2 sessões em simultâneo",  d10n["dur2_cp1"], d10["dur2_cp1"]),
        ("CP2 — 2 sessões em simultâneo",  d10n["dur2_cp2"], d10["dur2_cp2"]),
    ]:
        st.markdown(dur_bar_html(lbl, nob, wib, max_dur), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────────────────
ch1, ch2 = st.columns(2)

with ch1:
    st.markdown('<div class="sec-title">📊 Prob. Concorrência 2026–2036</div>',
                unsafe_allow_html=True)
    years  = [d["year"]  for d in data]
    p_conc = [d["pConc"] for d in data]
    fig1 = go.Figure(go.Scatter(
        x=years, y=p_conc, mode="lines",
        line=dict(color=ACCENT2, width=2),
        fill="tozeroy", fillcolor="rgba(245,166,35,0.15)",
        name="Prob. concorrência (%)",
    ))
    fig1.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5a7a9a", size=10),
        margin=dict(l=40, r=10, t=10, b=30),
        xaxis=dict(gridcolor=GRID_C),
        yaxis=dict(gridcolor=GRID_C, ticksuffix="%", range=[0, 100]),
        showlegend=False, height=220,
    )
    st.plotly_chart(fig1, use_container_width=True)

with ch2:
    st.markdown('<div class="sec-title">💶 Margem Bruta Energia (k€)</div>',
                unsafe_allow_html=True)
    data_e = [d for i, d in enumerate(data) if i % 2 == 0]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=[d["year"] for d in data_e],
                          y=[d["annual_rev"]  for d in data_e],
                          name="Receita (€)",  marker_color=ACCENT,  opacity=.85))
    fig2.add_trace(go.Bar(x=[d["year"] for d in data_e],
                          y=[d["annual_cost"] for d in data_e],
                          name="Custo E. (€)", marker_color=ACCENT3, opacity=.80))
    fig2.add_trace(go.Bar(x=[d["year"] for d in data_e],
                          y=[d["margin"]      for d in data_e],
                          name="Margem (€)",   marker_color=ACCENT2, opacity=.90))
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5a7a9a", size=10),
        margin=dict(l=50, r=10, t=10, b=30),
        barmode="group",
        xaxis=dict(gridcolor=GRID_C),
        yaxis=dict(gridcolor=GRID_C, tickformat="~s"),
        legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        height=220,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Recommendation matrix ─────────────────────────────────────────────────────
st.markdown('<div class="sec-title">🎯 Recomendação de Dimensionamento</div>',
            unsafe_allow_html=True)

RECS = [
    dict(scenario="Sem BESS",                      power=0,   cap=0,   best=False, col="#4a6a8a",
         tag="Load balancing 100% via rede",
         pros="Sem investimento. Grid 100 kW cobre a maioria das sessões.",
         cons="CP1/CP2 limitados a 100 kW em sessão única. Concorrência: cada charger com ~50 kW."),
    dict(scenario="BESS 50 kW / 100 kWh",           power=50,  cap=100, best=False, col="#4a8a6a",
         tag="Melhoria marginal QoS",
         pros="Reduz limitação CP2 em sessão única.",
         cons="Pouco impacto em concorrência elevada."),
    dict(scenario="BESS 75 kW / 150 kWh ✅",        power=75,  cap=150, best=True,  col=ACCENT,
         tag="Equilíbrio recomendado",
         pros="Cobre CP1 e CP2 individualmente. Concorrência com ~87 kW/charger. Payback ~5–7 anos.",
         cons="Investimento moderado necessário."),
    dict(scenario="BESS 100–150 kW / 200–300 kWh",  power=125, cap=250, best=False, col=ACCENT2,
         tag="Orientado a 2036+",
         pros="Máxima experiência. Preparado para crescimento acelerado.",
         cons="Investimento significativo, subutilizado até ~2030."),
]

for r in RECS:
    cl, ch = investment_cost(r["power"], r["cap"])
    c_str = "—" if cl == 0 else f"{cl//1000}–{ch//1000} k€"
    cls   = "rec-row best" if r["best"] else "rec-row"
    st.markdown(f"""
    <div class="{cls}">
      <div style="display:grid;grid-template-columns:1.6fr 0.6fr 2fr 2fr;gap:12px;align-items:center">
        <div>
          <div style="font-weight:800;color:{r['col']};font-size:13px">{r['scenario']}</div>
          <div style="font-size:10px;color:#5a7a9a;margin-top:2px">{r['tag']}</div>
        </div>
        <div style="font-family:monospace;color:{ACCENT2};font-size:12px;font-weight:700">{c_str}</div>
        <div style="font-size:11px;color:#4ade80">✅ {r['pros']}</div>
        <div style="font-size:11px;color:#f87171">⚠️ {r['cons']}</div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:{BG_DARK};border:1px solid #0e2035;border-radius:10px;
            padding:11px 16px;font-size:11px;color:#5a7a9a;line-height:1.8">
  <strong style="color:#8aaccc">Modelo:</strong>
  Aproximação M/M/1 (Poisson arrivals, exponential service).
  P(concorrência) = ρ² onde ρ = (sessões/h) / (completions/h).
  Energia por sessão é fixa — o load balancing aumenta a duração, não reduz a energia entregue ao veículo.
  <strong style="color:#8aaccc">A BESS não é estruturalmente obrigatória com load balancing</strong>
  — é um investimento de qualidade de serviço e diferenciação competitiva.
</div>
""", unsafe_allow_html=True)
