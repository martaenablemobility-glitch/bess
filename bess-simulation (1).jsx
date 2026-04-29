import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area,
} from "recharts";

const ACCENT  = "#00e5c8";
const ACCENT2 = "#f5a623";
const ACCENT3 = "#e94f4f";
const ACCENT4 = "#a78bfa";
const GRID_C  = "#1e2d3d";

function lerp(a, b, t) { return a + (b - a) * t; }

function concurrencyProb(sessions, sessionMinutes, opHours) {
  const lambda = sessions / opHours;
  const mu = 60 / sessionMinutes;
  const rho = Math.min(lambda / mu, 0.95);
  return rho * rho;
}

function sessionDuration(energyKwh, ratedKw, availTotal, nSessions) {
  const share = Math.min(ratedKw, availTotal / nSessions);
  return (energyKwh / share) * 60;
}

function buildData(p) {
  const { power120, power150, energy120, energy150,
    sessions2026, sessions2036, availability, opHoursPerDay,
    omie, premium, chargePrice, bessPower } = p;
  const gridMax    = 100;
  const totalAvail = gridMax + bessPower;

  return Array.from({ length: 11 }, (_, i) => {
    const year   = 2026 + i;
    const t      = i / 10;
    const sess   = lerp(sessions2026, sessions2036, t);
    const opDays = 365 * (availability / 100);
    const avgMin = ((energy120 / power120) + (energy150 / power150)) / 2 * 60;
    const pConc  = concurrencyProb(sess, avgMin, opHoursPerDay);

    const dur1_cp1 = sessionDuration(energy120, power120, totalAvail, 1);
    const dur1_cp2 = sessionDuration(energy150, power150, totalAvail, 1);
    const dur2_cp1 = sessionDuration(energy120, power120, totalAvail, 2);
    const dur2_cp2 = sessionDuration(energy150, power150, totalAvail, 2);

    const dailyE  = sess * energy120 + sess * energy150;
    const annualE = dailyE * opDays;
    const buyCost = (omie + premium) / 1000;
    const annualCost = annualE * buyCost;
    const annualRev  = annualE * chargePrice;
    const margin     = annualRev - annualCost;

    return {
      year, sess: Math.round(sess),
      pConc: +(pConc * 100).toFixed(1),
      dur1_cp1: +dur1_cp1.toFixed(1), dur1_cp2: +dur1_cp2.toFixed(1),
      dur2_cp1: +dur2_cp1.toFixed(1), dur2_cp2: +dur2_cp2.toFixed(1),
      dailyE: +dailyE.toFixed(1),
      annualE: +annualE.toFixed(0),
      annualCost: +annualCost.toFixed(0),
      annualRev:  +annualRev.toFixed(0),
      margin:     +margin.toFixed(0),
      opDays:     +opDays.toFixed(0),
    };
  });
}

function investmentCost(power, capacity) {
  if (power === 0) return { low: 0, high: 0 };
  return {
    low:  Math.round((capacity * 400 + power * 140 + 15000) / 5000) * 5000,
    high: Math.round((capacity * 570 + power * 200 + 15000) / 5000) * 5000,
  };
}

function Tt({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:"#0d1b2a", border:`1px solid ${ACCENT}33`, borderRadius:8, padding:"10px 14px", fontSize:12 }}>
      <p style={{ color:"#aac", marginBottom:6, fontWeight:700 }}>{label}</p>
      {payload.map((p,i) => (
        <p key={i} style={{ color:p.color, margin:"2px 0" }}>
          {p.name}: <strong>{Number(p.value).toLocaleString("pt-PT")}</strong>
        </p>
      ))}
    </div>
  );
}

function KPI({ label, value, sub, accent=ACCENT, hi }) {
  return (
    <div style={{ background: hi ? `${accent}18` : "#0a1520", border:`1px solid ${hi ? accent : "#1a2d42"}`, borderRadius:10, padding:"14px 18px" }}>
      <div style={{ fontSize:10, color:"#5a7a9a", textTransform:"uppercase", letterSpacing:1, marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:20, fontWeight:800, color: hi ? accent : "#e0ecf8", fontFamily:"'Space Mono',monospace" }}>{value}</div>
      {sub && <div style={{ fontSize:10, color:"#6a8aaa", marginTop:3 }}>{sub}</div>}
    </div>
  );
}

function Sec({ title, icon }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14, borderBottom:`1px solid ${GRID_C}`, paddingBottom:9 }}>
      <span>{icon}</span>
      <span style={{ fontSize:13, fontWeight:700, color:"#c0d8f0", letterSpacing:.4, textTransform:"uppercase" }}>{title}</span>
    </div>
  );
}

function PRow({ label, value, onChange, min, max, step=1, unit }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"5px 0", borderBottom:"1px solid #0d1e2d" }}>
      <span style={{ fontSize:11, color:"#8aaccc" }}>{label}</span>
      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
        <input type="number" value={value} min={min} max={max} step={step}
          onChange={e => onChange(+e.target.value)}
          style={{ width:70, background:"#0a1520", border:"1px solid #1e3050", borderRadius:6, color:ACCENT,
            fontFamily:"'Space Mono',monospace", fontSize:12, padding:"3px 7px", textAlign:"right" }} />
        {unit && <span style={{ fontSize:10, color:"#5a7a9a", minWidth:36 }}>{unit}</span>}
      </div>
    </div>
  );
}

function BessSlider({ value, onChange }) {
  const options = [0, 50, 75, 100, 125, 150];
  return (
    <div style={{ display:"flex", gap:7, flexWrap:"wrap" }}>
      {options.map(v => (
        <button key={v} onClick={() => onChange(v)}
          style={{
            padding:"6px 12px", borderRadius:20,
            border:`1.5px solid ${v===value ? ACCENT : "#1a2d42"}`,
            background: v===value ? `${ACCENT}22` : "#0a1520",
            color: v===value ? ACCENT : "#6a8aaa",
            fontFamily:"'Space Mono',monospace", fontSize:11,
            cursor:"pointer", fontWeight: v===value ? 700 : 400,
          }}>
          {v === 0 ? "Sem BESS" : `${v} kW`}
        </button>
      ))}
    </div>
  );
}

function DurBar({ label, noBess, withBess, max }) {
  const improved = withBess < noBess - 0.5;
  return (
    <div style={{ marginBottom:12 }}>
      <div style={{ fontSize:11, color:"#8aaccc", marginBottom:5 }}>{label}</div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
        {[["Sem BESS (rede 100 kW)", noBess, ACCENT3], ["Com BESS selecionada", withBess, improved ? ACCENT : "#6a8aaa"]].map(([lbl, val, col]) => (
          <div key={lbl}>
            <div style={{ fontSize:10, color:"#5a7a9a", marginBottom:3 }}>{lbl}</div>
            <div style={{ height:7, borderRadius:4, background:"#1a2d42", overflow:"hidden" }}>
              <div style={{ height:"100%", width:`${Math.min(100,(val/max)*100)}%`, background:col, borderRadius:4, transition:"width .4s" }} />
            </div>
            <div style={{ fontFamily:"'Space Mono',monospace", fontSize:12, color:col, marginTop:3 }}>{val.toFixed(1)} min</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [power120,     setPower120]     = useState(120);
  const [power150,     setPower150]     = useState(150);
  const [energy120,    setEnergy120]    = useState(30);
  const [energy150,    setEnergy150]    = useState(32.5);
  const [sessions2026, setSessions2026] = useState(7);
  const [sessions2036, setSessions2036] = useState(14);
  const [availability, setAvailability] = useState(95);
  const [opHours,      setOpHours]      = useState(14);
  const [omie,         setOmie]         = useState(60);
  const [premium,      setPremium]      = useState(25);
  const [chargePrice,  setChargePrice]  = useState(0.32);
  const [bessPower,    setBessPower]    = useState(75);

  const bessCapacity = bessPower === 0 ? 0 : Math.max(100, bessPower * 2);
  const p = { power120, power150, energy120, energy150, sessions2026, sessions2036,
               availability, opHoursPerDay: opHours, omie, premium, chargePrice, bessPower };
  const pNo = { ...p, bessPower: 0 };

  const data   = useMemo(() => buildData(p),   [power120, power150, energy120, energy150, sessions2026, sessions2036, availability, opHours, omie, premium, chargePrice, bessPower]);
  const dataNo = useMemo(() => buildData(pNo), [power120, power150, energy120, energy150, sessions2026, sessions2036, availability, opHours, omie, premium, chargePrice]);

  const cost  = investmentCost(bessPower, bessCapacity);
  const d0    = data[0];   const d10 = data[10];
  const d0n   = dataNo[0]; const d10n= dataNo[10];
  const maxDur= Math.max(d10n.dur2_cp1, d10n.dur2_cp2, 60);

  const RECS = [
    { scenario:"Sem BESS", power:0, cap:0, tag:"Load balancing 100% via rede", col:"#4a6a8a",
      pros:`Sem investimento. Grid 100 kW cobre a maioria das sessões.`,
      cons:`CP1/CP2 limitados a 100 kW em sessão única. Concorrência: cada charger com ~50 kW.` },
    { scenario:"BESS 50 kW / 100 kWh", power:50, cap:100, tag:"Melhoria marginal QoS", col:"#4a8a6a",
      pros:"Reduz limitação CP2 em sessão única.",
      cons:"Pouco impacto em concorrência elevada." },
    { scenario:"BESS 75 kW / 150 kWh ✅", power:75, cap:150, tag:"Equilíbrio recomendado", col:ACCENT, best:true,
      pros:`Cobre CP1 e CP2 individualmente. Concorrência com ~87 kW/charger. Payback ~5–7 anos.`,
      cons:"Investimento moderado necessário." },
    { scenario:"BESS 100–150 kW / 200–300 kWh", power:125, cap:250, tag:"Orientado a 2036+", col:ACCENT2,
      pros:"Máxima experiência. Preparado para crescimento acelerado.",
      cons:"Investimento significativo, subutilizado até ~2030." },
  ];

  return (
    <div style={{ background:"#060e18", minHeight:"100vh", fontFamily:"'DM Sans','Segoe UI',sans-serif", color:"#c0d8f0", padding:24 }}>
      <div style={{ marginBottom:22 }}>
        <div style={{ fontSize:10, fontWeight:700, letterSpacing:3, color:ACCENT, textTransform:"uppercase", fontFamily:"'Space Mono',monospace", marginBottom:4 }}>
          BESS · Load Balancing · Dimensionamento
        </div>
        <h1 style={{ fontSize:25, fontWeight:900, color:"#e8f4ff", margin:0 }}>
          Gestão de Cargas + BESS — Análise 2026–2036
        </h1>
        <p style={{ fontSize:12, color:"#5a7a9a", margin:"4px 0 0" }}>
          Potência gerida dinamicamente entre sessões ativas · BTE 100 kVA
        </p>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"238px 1fr", gap:16, alignItems:"start" }}>
        {/* Params */}
        <div style={{ background:"#0a1520", border:"1px solid #1a2d42", borderRadius:12, padding:"16px 14px" }}>
          <Sec title="Parâmetros" icon="⚙️" />
          <div style={{ fontSize:10, color:ACCENT, marginBottom:5, fontWeight:700 }}>CARREGADORES</div>
          <PRow label="Potência CP1"       value={power120}     onChange={setPower120}     min={50}  max={300}        unit="kW" />
          <PRow label="Energia/sessão CP1" value={energy120}    onChange={setEnergy120}    min={10}  max={100} step={.5} unit="kWh" />
          <PRow label="Potência CP2"       value={power150}     onChange={setPower150}     min={50}  max={300}        unit="kW" />
          <PRow label="Energia/sessão CP2" value={energy150}    onChange={setEnergy150}    min={10}  max={100} step={.5} unit="kWh" />
          <div style={{ fontSize:10, color:ACCENT, marginTop:12, marginBottom:5, fontWeight:700 }}>UTILIZAÇÃO</div>
          <PRow label="Sessões/dia 2026"   value={sessions2026} onChange={setSessions2026} min={1}  max={30}          unit="/charger" />
          <PRow label="Sessões/dia 2036"   value={sessions2036} onChange={setSessions2036} min={1}  max={60}          unit="/charger" />
          <PRow label="Horas oper./dia"    value={opHours}      onChange={setOpHours}      min={6}  max={24}          unit="h" />
          <PRow label="Disponibilidade"    value={availability} onChange={setAvailability} min={50} max={100}         unit="%" />
          <div style={{ fontSize:10, color:ACCENT, marginTop:12, marginBottom:5, fontWeight:700 }}>ENERGIA</div>
          <PRow label="OMIE base"          value={omie}         onChange={setOmie}         min={20} max={200}         unit="€/MWh" />
          <PRow label="Prémio indexado"    value={premium}      onChange={setPremium}      min={0}  max={100}         unit="€/MWh" />
          <PRow label="Preço carregamento" value={chargePrice}  onChange={setChargePrice}  min={.15} max={.80} step={.01} unit="€/kWh" />
          <div style={{ marginTop:14, padding:"12px 10px", background:"#050d16", borderRadius:8, border:"1px solid #0e2035" }}>
            <div style={{ fontSize:10, color:ACCENT2, fontWeight:700, marginBottom:10 }}>POTÊNCIA BESS A SIMULAR</div>
            <BessSlider value={bessPower} onChange={setBessPower} />
            <div style={{ marginTop:10, fontSize:10, color:"#5a7a9a" }}>
              Capacidade auto: <span style={{ color:ACCENT2, fontWeight:700 }}>{bessCapacity} kWh</span><br />
              Investimento: <span style={{ color:ACCENT2, fontWeight:700 }}>
                {cost.low === 0 ? "—" : `${(cost.low/1000).toFixed(0)}–${(cost.high/1000).toFixed(0)} k€`}
              </span>
            </div>
          </div>
        </div>

        {/* Main */}
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* Key insight */}
          <div style={{ background:`${ACCENT4}18`, border:`1px solid ${ACCENT4}55`, borderRadius:10, padding:"14px 18px", display:"flex", gap:14, alignItems:"flex-start" }}>
            <span style={{ fontSize:22, marginTop:1 }}>⚖️</span>
            <div>
              <div style={{ fontWeight:800, color:ACCENT4, fontSize:14, marginBottom:4 }}>
                Com Load Balancing, a BESS deixa de ser estruturalmente obrigatória
              </div>
              <div style={{ fontSize:12, color:"#a0b8cc", lineHeight:1.7 }}>
                O sistema de gestão de cargas distribui os <strong style={{color:"#e0ecf8"}}>100 kW da rede BTE</strong> dinamicamente entre as sessões ativas —
                nunca há sobrecarga da ligação. A BESS torna-se um <strong style={{color:ACCENT4}}>investimento de qualidade de serviço</strong>:
                reduz os tempos de sessão quando há concorrência, e aumenta a competitividade do serviço.
                A decisão de instalar (e com que dimensão) depende do nível de serviço pretendido e do retorno esperado.
              </div>
            </div>
          </div>

          {/* KPIs */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10 }}>
            <KPI label="Prob. concorrência 2026" value={`${d0.pConc}%`}  sub="Sessões simultâneas" accent={ACCENT2} />
            <KPI label="Prob. concorrência 2036" value={`${d10.pConc}%`} sub="Cresce com utilização" accent={ACCENT2} hi />
            <KPI label="BESS selecionada" value={bessPower === 0 ? "Sem BESS" : `${bessPower} kW`} sub={`${bessCapacity} kWh`} accent={ACCENT} hi={bessPower > 0} />
            <KPI label="Investimento estimado" value={cost.low === 0 ? "Sem custo" : `${(cost.low/1000).toFixed(0)}–${(cost.high/1000).toFixed(0)} k€`} sub="Instalado" accent={ACCENT2} />
          </div>

          {/* Session durations */}
          <div style={{ background:"#0a1520", border:"1px solid #1a2d42", borderRadius:12, padding:"18px 20px" }}>
            <Sec title="Tempo de Sessão com Load Balancing + BESS" icon="⏱️" />
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:24 }}>
              <div>
                <div style={{ fontSize:11, color:ACCENT, fontWeight:700, marginBottom:12 }}>2026 — {d0.sess} sessões/charger/dia</div>
                <DurBar label="CP1 (120 kW) — sessão única"      noBess={d0n.dur1_cp1} withBess={d0.dur1_cp1} max={maxDur} />
                <DurBar label="CP2 (150 kW) — sessão única"      noBess={d0n.dur1_cp2} withBess={d0.dur1_cp2} max={maxDur} />
                <DurBar label="CP1 — 2 sessões em simultâneo"    noBess={d0n.dur2_cp1} withBess={d0.dur2_cp1} max={maxDur} />
                <DurBar label="CP2 — 2 sessões em simultâneo"    noBess={d0n.dur2_cp2} withBess={d0.dur2_cp2} max={maxDur} />
              </div>
              <div>
                <div style={{ fontSize:11, color:ACCENT2, fontWeight:700, marginBottom:12 }}>2036 — {d10.sess} sessões/charger/dia</div>
                <DurBar label="CP1 (120 kW) — sessão única"      noBess={d10n.dur1_cp1} withBess={d10.dur1_cp1} max={maxDur} />
                <DurBar label="CP2 (150 kW) — sessão única"      noBess={d10n.dur1_cp2} withBess={d10.dur1_cp2} max={maxDur} />
                <DurBar label="CP1 — 2 sessões em simultâneo"    noBess={d10n.dur2_cp1} withBess={d10.dur2_cp1} max={maxDur} />
                <DurBar label="CP2 — 2 sessões em simultâneo"    noBess={d10n.dur2_cp2} withBess={d10.dur2_cp2} max={maxDur} />
              </div>
            </div>
            <div style={{ marginTop:12, padding:"10px 12px", background:"#050d16", borderRadius:8, border:"1px solid #0e2035", fontSize:11, color:"#6a8aaa", lineHeight:1.7 }}>
              💡 <strong style={{color:"#8aaccc"}}>Sessão única:</strong> A BESS só melhora o tempo se o charger exceder 100 kW (grid).
              CP1={power120} kW → {power120>100 ? "limitado pela rede, BESS ajuda":"dentro do limite de rede, sem diferença"}.
              CP2={power150} kW → {power150>100 ? "limitado pela rede, BESS ajuda":"dentro do limite de rede, sem diferença"}.
              {" "}<strong style={{color:"#8aaccc"}}>Concorrência:</strong> com 2 sessões simultâneas, a BESS aumenta o bolo de potência disponível,
              reduzindo o tempo para ambos.
            </div>
          </div>

          {/* Concurrency + energy charts side by side */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            <div style={{ background:"#0a1520", border:"1px solid #1a2d42", borderRadius:12, padding:"18px 20px" }}>
              <Sec title="Prob. Concorrência 2026–2036" icon="📊" />
              <ResponsiveContainer width="100%" height={170}>
                <AreaChart data={data} margin={{ top:5, right:5, left:0, bottom:0 }}>
                  <defs>
                    <linearGradient id="gc" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={ACCENT2} stopOpacity={.35} />
                      <stop offset="95%" stopColor={ACCENT2} stopOpacity={0}   />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_C} />
                  <XAxis dataKey="year" tick={{ fill:"#5a7a9a", fontSize:10 }} />
                  <YAxis tickFormatter={v=>`${v}%`} tick={{ fill:"#5a7a9a", fontSize:10 }} width={36} domain={[0,100]} />
                  <Tooltip content={<Tt />} />
                  <Area type="monotone" dataKey="pConc" name="Prob. concorrência (%)" stroke={ACCENT2} fill="url(#gc)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div style={{ background:"#0a1520", border:"1px solid #1a2d42", borderRadius:12, padding:"18px 20px" }}>
              <Sec title="Margem Bruta Energia (k€)" icon="💶" />
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={data.filter((_,i)=>i%2===0)} margin={{ top:5, right:5, left:0, bottom:0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_C} />
                  <XAxis dataKey="year" tick={{ fill:"#5a7a9a", fontSize:10 }} />
                  <YAxis tickFormatter={v=>`${(v/1000).toFixed(0)}k`} tick={{ fill:"#5a7a9a", fontSize:10 }} width={42} />
                  <Tooltip content={<Tt />} />
                  <Bar dataKey="annualRev"  name="Receita (€)"  fill={ACCENT}  opacity={.85} radius={[3,3,0,0]} />
                  <Bar dataKey="annualCost" name="Custo E. (€)" fill={ACCENT3} opacity={.80} radius={[3,3,0,0]} />
                  <Bar dataKey="margin"     name="Margem (€)"   fill={ACCENT2} opacity={.90} radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recommendation matrix */}
          <div style={{ background:"#0a1520", border:"1px solid #1a2d42", borderRadius:12, padding:"18px 20px" }}>
            <Sec title="Recomendação de Dimensionamento" icon="🎯" />
            <div style={{ display:"flex", flexDirection:"column", gap:9 }}>
              {RECS.map(o => {
                const c = investmentCost(o.power, o.cap);
                return (
                  <div key={o.scenario} style={{
                    background: o.best ? `${ACCENT}12` : "#050d16",
                    border:`1px solid ${o.best ? ACCENT : "#1a2d42"}`,
                    borderRadius:9, padding:"11px 16px",
                    display:"grid", gridTemplateColumns:"1.6fr 0.7fr 2fr 2fr", gap:12, alignItems:"center",
                  }}>
                    <div>
                      <div style={{ fontWeight:800, color:o.col, fontSize:13 }}>{o.scenario}</div>
                      <div style={{ fontSize:10, color:"#5a7a9a", marginTop:2 }}>{o.tag}</div>
                    </div>
                    <div style={{ fontFamily:"'Space Mono',monospace", color:ACCENT2, fontSize:12, fontWeight:700 }}>
                      {o.power === 0 ? "—" : `${(c.low/1000).toFixed(0)}–${(c.high/1000).toFixed(0)} k€`}
                    </div>
                    <div style={{ fontSize:11, color:"#4ade80" }}>✅ {o.pros}</div>
                    <div style={{ fontSize:11, color:"#f87171" }}>⚠️ {o.cons}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div style={{ background:"#050d16", border:"1px solid #0e2035", borderRadius:10, padding:"11px 16px", fontSize:11, color:"#5a7a9a", lineHeight:1.8 }}>
            <strong style={{ color:"#8aaccc" }}>Modelo:</strong> Aproximação M/M/1 (Poisson arrivals, exponential service).
            P(concorrência) = ρ² onde ρ = (sessões/h) / (completions/h). Energia por sessão é fixa — o load balancing aumenta a duração, não reduz a energia entregue ao veículo.
            {" "}<strong style={{ color:"#8aaccc" }}>A BESS não é estruturalmente obrigatória com load balancing</strong> — é um investimento de qualidade de serviço e diferenciação competitiva.
          </div>
        </div>
      </div>
    </div>
  );
}
