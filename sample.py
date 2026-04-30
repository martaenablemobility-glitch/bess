import math
import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px

# ── Colours ──────────────────────────────────────────────────────────────────
ACCENT  = "#00e5c8"
ACCENT2 = "#f5a623"
ACCENT3 = "#e94f4f"
ACCENT4 = "#a78bfa"
GRID_C  = "#1e2d3d"
BG_MAIN = "#060e18"
BG_CARD = "#0a1520"
BG_DARK = "#050d16"

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
               sessions2026, sessions2036, availability,
               op_hours, omie, premium, charge_price, bess_power):
    grid_max   = 100
    total_avail = grid_max + bess_power
    rows = []
    for i in range(11):
        year   = 2026 + i
        t      = i / 10
        sess   = lerp(sessions2026, sessions2036, t)
        op_days = 365 * (availability / 100)
        avg_min = ((energy120 / power120) + (energy150 / power150)) / 2 * 60
        p_conc  = concurrency_prob(sess, avg_min, op_hours)

        dur1_cp1 = session_duration(energy120, power120, total_avail, 1)
        dur1_cp2 = session_duration(energy150, power150, total_avail, 1)
        dur2_cp1 = session_duration(energy120, power120, total_avail, 2)
        dur2_cp2 = session_duration(energy150, power150, total_avail, 2)

        daily_e   = sess * energy120 + sess * energy150
        annual_e  = daily_e * op_days
        buy_cost  = (omie + premium) / 1000
        annual_cost = annual_e * buy_cost
        annual_rev  = annual_e * charge_price
        margin      = annual_rev - annual_cost

        rows.append(dict(
            year=year, sess=round(sess),
            pConc=round(p_conc * 100, 1),
            dur1_cp1=round(dur1_cp1, 1), dur1_cp2=round(dur1_cp2, 1),
            dur2_cp1=round(dur2_cp1, 1), dur2_cp2=round(dur2_cp2, 1),
            daily_e=round(daily_e, 1),
            annual_e=round(annual_e),
            annual_cost=round(annual_cost),
            annual_rev=round(annual_rev),
            margin=round(margin),
            op_days=round(op_days),
        ))
    return rows

def investment_cost(power, capacity):
    if power == 0:
        return dict(low=0, high=0)
    low  = round((capacity * 400 + power * 140 + 15000) / 5000) * 5000
    high = round((capacity * 570 + power * 200 + 15000) / 5000) * 5000
    return dict(low=low, high=high)

# ── Style helpers ─────────────────────────────────────────────────────────────
FONT_MONO = "'Space Mono', monospace"
FONT_BODY = "'DM Sans', 'Segoe UI', sans-serif"

def card(children, **style):
    base = dict(background=BG_CARD, border=f"1px solid #1a2d42",
                borderRadius=12, padding="18px 20px")
    base.update(style)
    return html.Div(children, style=base)

def section_title(title, icon):
    return html.Div([
        html.Span(icon, style=dict(fontSize=16)),
        html.Span(title, style=dict(fontSize=13, fontWeight=700, color="#c0d8f0",
                                    letterSpacing=".4px", textTransform="uppercase",
                                    marginLeft=8)),
    ], style=dict(display="flex", alignItems="center", marginBottom=14,
                  borderBottom=f"1px solid {GRID_C}", paddingBottom=9))

def kpi_card(label, value, sub="", accent=ACCENT, hi=False):
    return html.Div([
        html.Div(label, style=dict(fontSize=10, color="#5a7a9a",
                                   textTransform="uppercase", letterSpacing=1, marginBottom=4)),
        html.Div(value, style=dict(fontSize=20, fontWeight=800,
                                   color=accent if hi else "#e0ecf8",
                                   fontFamily=FONT_MONO)),
        html.Div(sub, style=dict(fontSize=10, color="#6a8aaa", marginTop=3)) if sub else None,
    ], style=dict(
        background=f"{accent}18" if hi else BG_DARK,
        border=f"1px solid {accent if hi else '#1a2d42'}",
        borderRadius=10, padding="14px 18px"
    ))

def param_row(label, input_id, value, min_v, max_v, step=1, unit=""):
    return html.Div([
        html.Span(label, style=dict(fontSize=11, color="#8aaccc")),
        html.Div([
            dcc.Input(id=input_id, type="number", value=value,
                      min=min_v, max=max_v, step=step,
                      style=dict(width=70, background="#0a1520",
                                 border="1px solid #1e3050", borderRadius=6,
                                 color=ACCENT, fontFamily=FONT_MONO, fontSize=12,
                                 padding="3px 7px", textAlign="right")),
            html.Span(unit, style=dict(fontSize=10, color="#5a7a9a", minWidth=36)) if unit else None,
        ], style=dict(display="flex", alignItems="center", gap=6)),
    ], style=dict(display="flex", justifyContent="space-between", alignItems="center",
                  padding="5px 0", borderBottom="1px solid #0d1e2d"))

BESS_OPTIONS = [0, 50, 75, 100, 125, 150]

def bess_buttons(current):
    btns = []
    for v in BESS_OPTIONS:
        selected = (v == current)
        btns.append(html.Button(
            "Sem BESS" if v == 0 else f"{v} kW",
            id={"type": "bess-btn", "index": v},
            n_clicks=0,
            style=dict(
                padding="6px 12px", borderRadius=20,
                border=f"1.5px solid {ACCENT if selected else '#1a2d42'}",
                background=f"{ACCENT}22" if selected else "#0a1520",
                color=ACCENT if selected else "#6a8aaa",
                fontFamily=FONT_MONO, fontSize=11,
                cursor="pointer", fontWeight=700 if selected else 400,
            )
        ))
    return html.Div(btns, style=dict(display="flex", gap=7, flexWrap="wrap"))

# ── App layout ────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="BESS Dashboard 2026–2036")
app.layout = html.Div([
    # Hidden store for BESS power
    dcc.Store(id="bess-power-store", data=75),

    # Header
    html.Div([
        html.Div("BESS · Load Balancing · Dimensionamento",
                 style=dict(fontSize=10, fontWeight=700, letterSpacing=3, color=ACCENT,
                            textTransform="uppercase", fontFamily=FONT_MONO, marginBottom=4)),
        html.H1("Gestão de Cargas + BESS — Análise 2026–2036",
                style=dict(fontSize=25, fontWeight=900, color="#e8f4ff", margin=0)),
        html.P("Potência gerida dinamicamente entre sessões ativas · BTE 100 kVA",
               style=dict(fontSize=12, color="#5a7a9a", margin="4px 0 0")),
    ], style=dict(marginBottom=22)),

    # Grid: sidebar + main
    html.Div([

        # ── Sidebar ──────────────────────────────────────────────────────────
        html.Div([
            card([
                section_title("Parâmetros", "⚙️"),

                html.Div("CARREGADORES", style=dict(fontSize=10, color=ACCENT,
                                                     marginBottom=5, fontWeight=700)),
                param_row("Potência CP1",        "p-power120",    120,  50,  300, 1,    "kW"),
                param_row("Energia/sessão CP1",  "p-energy120",    30,  10,  100, 0.5,  "kWh"),
                param_row("Potência CP2",        "p-power150",    150,  50,  300, 1,    "kW"),
                param_row("Energia/sessão CP2",  "p-energy150",   32.5, 10,  100, 0.5,  "kWh"),

                html.Div("UTILIZAÇÃO", style=dict(fontSize=10, color=ACCENT,
                                                   marginTop=12, marginBottom=5, fontWeight=700)),
                param_row("Sessões/dia 2026",  "p-sess2026",   7,   1,  30, 1, "/charger"),
                param_row("Sessões/dia 2036",  "p-sess2036",  14,   1,  60, 1, "/charger"),
                param_row("Horas oper./dia",   "p-ophours",   14,   6,  24, 1, "h"),
                param_row("Disponibilidade",   "p-avail",     95,  50, 100, 1, "%"),

                html.Div("ENERGIA", style=dict(fontSize=10, color=ACCENT,
                                                marginTop=12, marginBottom=5, fontWeight=700)),
                param_row("OMIE base",          "p-omie",   60,   20, 200, 1,    "€/MWh"),
                param_row("Prémio indexado",    "p-premium", 25,   0, 100, 1,    "€/MWh"),
                param_row("Preço carregamento", "p-price",  0.32, .15, .80, 0.01, "€/kWh"),

                # BESS selector
                html.Div([
                    html.Div("POTÊNCIA BESS A SIMULAR",
                             style=dict(fontSize=10, color=ACCENT2, fontWeight=700, marginBottom=10)),
                    html.Div(id="bess-buttons-container",
                             children=bess_buttons(75)),
                    html.Div(id="bess-info",
                             style=dict(marginTop=10, fontSize=10, color="#5a7a9a")),
                ], style=dict(marginTop=14, padding="12px 10px",
                              background="#050d16", borderRadius=8,
                              border="1px solid #0e2035")),
            ])
        ], style=dict(width=238, flexShrink=0)),

        # ── Main content ─────────────────────────────────────────────────────
        html.Div([

            # Insight banner
            html.Div([
                html.Span("⚖️", style=dict(fontSize=22, marginTop=1)),
                html.Div([
                    html.Div("Com Load Balancing, a BESS deixa de ser estruturalmente obrigatória",
                             style=dict(fontWeight=800, color=ACCENT4, fontSize=14, marginBottom=4)),
                    html.P([
                        "O sistema de gestão de cargas distribui os ",
                        html.Strong("100 kW da rede BTE", style=dict(color="#e0ecf8")),
                        " dinamicamente entre as sessões ativas — nunca há sobrecarga da ligação. "
                        "A BESS torna-se um ",
                        html.Strong("investimento de qualidade de serviço", style=dict(color=ACCENT4)),
                        ": reduz os tempos de sessão quando há concorrência, e aumenta a competitividade do serviço.",
                    ], style=dict(fontSize=12, color="#a0b8cc", lineHeight=1.7, margin=0)),
                ]),
            ], style=dict(background=f"{ACCENT4}18", border=f"1px solid {ACCENT4}55",
                          borderRadius=10, padding="14px 18px",
                          display="flex", gap=14, alignItems="flex-start")),

            # KPI row
            html.Div(id="kpi-row",
                     style=dict(display="grid",
                                gridTemplateColumns="repeat(4,1fr)", gap=10)),

            # Session duration card
            card([
                section_title("Tempo de Sessão com Load Balancing + BESS", "⏱️"),
                html.Div(id="dur-grid"),
            ]),

            # Charts row
            html.Div([
                card([
                    section_title("Prob. Concorrência 2026–2036", "📊"),
                    dcc.Graph(id="chart-concurrency", config=dict(displayModeBar=False),
                              style=dict(height=200)),
                ]),
                card([
                    section_title("Margem Bruta Energia (k€)", "💶"),
                    dcc.Graph(id="chart-margin", config=dict(displayModeBar=False),
                              style=dict(height=200)),
                ]),
            ], style=dict(display="grid", gridTemplateColumns="1fr 1fr", gap=14)),

            # Recommendation matrix
            card([
                section_title("Recomendação de Dimensionamento", "🎯"),
                html.Div(id="rec-matrix"),
            ]),

            # Footer
            html.Div([
                html.Strong("Modelo: ", style=dict(color="#8aaccc")),
                "Aproximação M/M/1 (Poisson arrivals, exponential service). "
                "P(concorrência) = ρ² onde ρ = (sessões/h) / (completions/h). "
                "Energia por sessão é fixa — o load balancing aumenta a duração, não reduz a energia entregue ao veículo. ",
                html.Strong("A BESS não é estruturalmente obrigatória com load balancing",
                            style=dict(color="#8aaccc")),
                " — é um investimento de qualidade de serviço e diferenciação competitiva.",
            ], style=dict(background=BG_DARK, border="1px solid #0e2035",
                          borderRadius=10, padding="11px 16px",
                          fontSize=11, color="#5a7a9a", lineHeight=1.8)),

        ], style=dict(display="flex", flexDirection="column", gap=16, flex=1)),

    ], style=dict(display="flex", gap=16, alignItems="flex-start")),

], style=dict(background=BG_MAIN, minHeight="100vh",
              fontFamily=FONT_BODY, color="#c0d8f0",
              padding=24))


# ── Callbacks ─────────────────────────────────────────────────────────────────

# Update BESS store when any button is clicked
@app.callback(
    Output("bess-power-store", "data"),
    [Input({"type": "bess-btn", "index": v}, "n_clicks") for v in BESS_OPTIONS],
    State("bess-power-store", "data"),
    prevent_initial_call=True,
)
def update_bess_store(*args):
    ctx = callback_context
    if not ctx.triggered:
        return args[-1]
    prop_id = ctx.triggered[0]["prop_id"]
    # extract index from pattern match id
    import json
    id_part = prop_id.split(".")[0]
    try:
        idx = json.loads(id_part)["index"]
        return idx
    except Exception:
        return args[-1]


@app.callback(
    Output("bess-buttons-container", "children"),
    Output("bess-info", "children"),
    Input("bess-power-store", "data"),
)
def refresh_bess_ui(bess_power):
    capacity = 0 if bess_power == 0 else max(100, bess_power * 2)
    cost = investment_cost(bess_power, capacity)
    cost_str = "—" if cost["low"] == 0 else f"{cost['low']//1000}–{cost['high']//1000} k€"
    info = [
        f"Capacidade auto: ", html.Span(f"{capacity} kWh",
                                        style=dict(color=ACCENT2, fontWeight=700)),
        html.Br(),
        "Investimento: ", html.Span(cost_str, style=dict(color=ACCENT2, fontWeight=700)),
    ]
    return bess_buttons(bess_power), info


@app.callback(
    Output("kpi-row", "children"),
    Output("dur-grid", "children"),
    Output("chart-concurrency", "figure"),
    Output("chart-margin", "figure"),
    Output("rec-matrix", "children"),
    Input("p-power120", "value"),  Input("p-power150", "value"),
    Input("p-energy120", "value"), Input("p-energy150", "value"),
    Input("p-sess2026", "value"),  Input("p-sess2036", "value"),
    Input("p-avail", "value"),     Input("p-ophours", "value"),
    Input("p-omie", "value"),      Input("p-premium", "value"),
    Input("p-price", "value"),     Input("bess-power-store", "data"),
)
def update_dashboard(power120, power150, energy120, energy150,
                     sess2026, sess2036, avail, ophours,
                     omie, premium, price, bess_power):

    # Defaults / guards
    def g(v, default): return v if v is not None else default
    power120  = g(power120,  120); power150  = g(power150,  150)
    energy120 = g(energy120,  30); energy150 = g(energy150, 32.5)
    sess2026  = g(sess2026,    7); sess2036  = g(sess2036,   14)
    avail     = g(avail,      95); ophours   = g(ophours,    14)
    omie      = g(omie,       60); premium   = g(premium,    25)
    price     = g(price,    0.32); bess_power= g(bess_power, 75)

    capacity = 0 if bess_power == 0 else max(100, bess_power * 2)
    cost = investment_cost(bess_power, capacity)

    data   = build_data(power120, power150, energy120, energy150,
                        sess2026, sess2036, avail, ophours, omie, premium, price, bess_power)
    data_no = build_data(power120, power150, energy120, energy150,
                         sess2026, sess2036, avail, ophours, omie, premium, price, 0)

    d0, d10   = data[0],    data[10]
    d0n, d10n = data_no[0], data_no[10]

    cost_str = "Sem custo" if cost["low"] == 0 else f"{cost['low']//1000}–{cost['high']//1000} k€"
    bess_label = "Sem BESS" if bess_power == 0 else f"{bess_power} kW"

    # ── KPIs ─────────────────────────────────────────────────────────────────
    kpis = html.Div([
        kpi_card("Prob. concorrência 2026", f"{d0['pConc']}%", "Sessões simultâneas", ACCENT2),
        kpi_card("Prob. concorrência 2036", f"{d10['pConc']}%", "Cresce com utilização", ACCENT2, hi=True),
        kpi_card("BESS selecionada", bess_label, f"{capacity} kWh", ACCENT, hi=(bess_power > 0)),
        kpi_card("Investimento estimado", cost_str, "Instalado", ACCENT2),
    ], style=dict(display="grid", gridTemplateColumns="repeat(4,1fr)", gap=10))

    # ── Duration bars ─────────────────────────────────────────────────────────
    max_dur = max(d10n["dur2_cp1"], d10n["dur2_cp2"], 60)

    def dur_bar(label, no_bess, with_bess):
        improved = with_bess < no_bess - 0.5
        bar_color = ACCENT if improved else "#6a8aaa"
        return html.Div([
            html.Div(label, style=dict(fontSize=11, color="#8aaccc", marginBottom=5)),
            html.Div([
                # No BESS
                html.Div([
                    html.Div("Sem BESS (rede 100 kW)", style=dict(fontSize=10, color="#5a7a9a", marginBottom=3)),
                    html.Div(style=dict(height=7, borderRadius=4, background="#1a2d42", overflow="hidden"),
                             children=html.Div(style=dict(
                                 height="100%",
                                 width=f"{min(100, (no_bess / max_dur) * 100):.1f}%",
                                 background=ACCENT3, borderRadius=4))),
                    html.Div(f"{no_bess:.1f} min",
                             style=dict(fontFamily=FONT_MONO, fontSize=12, color=ACCENT3, marginTop=3)),
                ]),
                # With BESS
                html.Div([
                    html.Div("Com BESS selecionada", style=dict(fontSize=10, color="#5a7a9a", marginBottom=3)),
                    html.Div(style=dict(height=7, borderRadius=4, background="#1a2d42", overflow="hidden"),
                             children=html.Div(style=dict(
                                 height="100%",
                                 width=f"{min(100, (with_bess / max_dur) * 100):.1f}%",
                                 background=bar_color, borderRadius=4))),
                    html.Div(f"{with_bess:.1f} min",
                             style=dict(fontFamily=FONT_MONO, fontSize=12, color=bar_color, marginTop=3)),
                ]),
            ], style=dict(display="grid", gridTemplateColumns="1fr 1fr", gap=10)),
        ], style=dict(marginBottom=12))

    dur_grid = html.Div([
        html.Div([
            html.Div(f"2026 — {d0['sess']} sessões/charger/dia",
                     style=dict(fontSize=11, color=ACCENT, fontWeight=700, marginBottom=12)),
            dur_bar("CP1 (120 kW) — sessão única",     d0n["dur1_cp1"], d0["dur1_cp1"]),
            dur_bar("CP2 (150 kW) — sessão única",     d0n["dur1_cp2"], d0["dur1_cp2"]),
            dur_bar("CP1 — 2 sessões em simultâneo",   d0n["dur2_cp1"], d0["dur2_cp1"]),
            dur_bar("CP2 — 2 sessões em simultâneo",   d0n["dur2_cp2"], d0["dur2_cp2"]),
        ]),
        html.Div([
            html.Div(f"2036 — {d10['sess']} sessões/charger/dia",
                     style=dict(fontSize=11, color=ACCENT2, fontWeight=700, marginBottom=12)),
            dur_bar("CP1 (120 kW) — sessão única",     d10n["dur1_cp1"], d10["dur1_cp1"]),
            dur_bar("CP2 (150 kW) — sessão única",     d10n["dur1_cp2"], d10["dur1_cp2"]),
            dur_bar("CP1 — 2 sessões em simultâneo",   d10n["dur2_cp1"], d10["dur2_cp1"]),
            dur_bar("CP2 — 2 sessões em simultâneo",   d10n["dur2_cp2"], d10["dur2_cp2"]),
        ]),
    ], style=dict(display="grid", gridTemplateColumns="1fr 1fr", gap=24))

    # ── Concurrency chart ────────────────────────────────────────────────────
    years  = [d["year"]  for d in data]
    p_conc = [d["pConc"] for d in data]

    fig_conc = go.Figure()
    fig_conc.add_trace(go.Scatter(
        x=years, y=p_conc, name="Prob. concorrência (%)",
        mode="lines", line=dict(color=ACCENT2, width=2),
        fill="tozeroy",
        fillcolor=f"rgba(245,166,35,0.15)",
    ))
    fig_conc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5a7a9a", size=10),
        margin=dict(l=40, r=10, t=10, b=30),
        xaxis=dict(gridcolor=GRID_C, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID_C, ticksuffix="%", range=[0, 100], tickfont=dict(size=10)),
        showlegend=False,
    )

    # ── Revenue/margin chart ─────────────────────────────────────────────────
    data_even = [d for i, d in enumerate(data) if i % 2 == 0]
    ye   = [d["year"]        for d in data_even]
    rev  = [d["annual_rev"]  for d in data_even]
    cost_e = [d["annual_cost"] for d in data_even]
    marg = [d["margin"]      for d in data_even]

    fig_margin = go.Figure()
    fig_margin.add_trace(go.Bar(x=ye, y=rev,  name="Receita (€)",  marker_color=ACCENT,  opacity=.85))
    fig_margin.add_trace(go.Bar(x=ye, y=cost_e, name="Custo E. (€)", marker_color=ACCENT3, opacity=.80))
    fig_margin.add_trace(go.Bar(x=ye, y=marg, name="Margem (€)",   marker_color=ACCENT2, opacity=.90))
    fig_margin.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#5a7a9a", size=10),
        margin=dict(l=50, r=10, t=10, b=30),
        barmode="group",
        xaxis=dict(gridcolor=GRID_C, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID_C, tickfont=dict(size=10),
                   tickformat="~s"),
        legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
    )

    # ── Recommendation matrix ────────────────────────────────────────────────
    RECS = [
        dict(scenario="Sem BESS",                  power=0,   cap=0,   tag="Load balancing 100% via rede",     col="#4a6a8a", best=False,
             pros="Sem investimento. Grid 100 kW cobre a maioria das sessões.",
             cons="CP1/CP2 limitados a 100 kW em sessão única. Concorrência: cada charger com ~50 kW."),
        dict(scenario="BESS 50 kW / 100 kWh",       power=50,  cap=100, tag="Melhoria marginal QoS",            col="#4a8a6a", best=False,
             pros="Reduz limitação CP2 em sessão única.",
             cons="Pouco impacto em concorrência elevada."),
        dict(scenario="BESS 75 kW / 150 kWh ✅",    power=75,  cap=150, tag="Equilíbrio recomendado",           col=ACCENT,   best=True,
             pros="Cobre CP1 e CP2 individualmente. Concorrência com ~87 kW/charger. Payback ~5–7 anos.",
             cons="Investimento moderado necessário."),
        dict(scenario="BESS 100–150 kW / 200–300 kWh", power=125, cap=250, tag="Orientado a 2036+",            col=ACCENT2,  best=False,
             pros="Máxima experiência. Preparado para crescimento acelerado.",
             cons="Investimento significativo, subutilizado até ~2030."),
    ]

    rows = []
    for r in RECS:
        c = investment_cost(r["power"], r["cap"])
        c_str = "—" if c["low"] == 0 else f"{c['low']//1000}–{c['high']//1000} k€"
        rows.append(html.Div([
            html.Div([
                html.Div(r["scenario"], style=dict(fontWeight=800, color=r["col"], fontSize=13)),
                html.Div(r["tag"], style=dict(fontSize=10, color="#5a7a9a", marginTop=2)),
            ]),
            html.Div(c_str, style=dict(fontFamily=FONT_MONO, color=ACCENT2, fontSize=12, fontWeight=700)),
            html.Div(f"✅ {r['pros']}", style=dict(fontSize=11, color="#4ade80")),
            html.Div(f"⚠️ {r['cons']}", style=dict(fontSize=11, color="#f87171")),
        ], style=dict(
            background=f"{ACCENT}12" if r["best"] else BG_DARK,
            border=f"1px solid {ACCENT if r['best'] else '#1a2d42'}",
            borderRadius=9, padding="11px 16px",
            display="grid", gridTemplateColumns="1.6fr 0.7fr 2fr 2fr", gap=12, alignItems="center",
        )))

    rec_matrix = html.Div(rows, style=dict(display="flex", flexDirection="column", gap=9))

    return kpis, dur_grid, fig_conc, fig_margin, rec_matrix


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
