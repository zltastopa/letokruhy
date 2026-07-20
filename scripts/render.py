#!/usr/bin/env python3
"""Render a self-contained HTML report of NRSR age distribution over time.

Reads data/distribution.json (produced by build.py) and writes index.html with
inline SVG charts and embedded data; no external dependencies, opens offline.
"""
from __future__ import annotations

import html
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "distribution.json").read_text(encoding="utf-8"))
TERMS = DATA["terms"]

# ---- palette -------------------------------------------------------------
INK = "#1b2130"
MUTED = "#6b7280"
GRID = "#e8eaf0"
ACCENT = "#2f6fed"
ACCENT2 = "#e4572e"
BOX = "#9db8f2"
BOXEDGE = "#3a5fb0"
BANDS = [
    ("<30", "#4a7bd4"),
    ("30–39", "#69b3a2"),
    ("40–49", "#e6c34a"),
    ("50–59", "#e08b3b"),
    ("60+", "#c0504d"),
]


def band_index(age: int) -> int:
    if age < 30:
        return 0
    if age < 40:
        return 1
    if age < 50:
        return 2
    if age < 60:
        return 3
    return 4


def esc(s) -> str:
    return html.escape(str(s))


# ---- chart 1: box plots by term -----------------------------------------
def chart_boxplots() -> str:
    W, H = 900, 440
    ml, mr, mt, mb = 46, 16, 20, 46
    pw, ph = W - ml - mr, H - mt - mb
    amin, amax = 20, 82
    n = len(TERMS)
    step = pw / n

    def y(age):
        return mt + ph - (age - amin) / (amax - amin) * ph

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Age distribution by term">']
    # y grid + labels
    for age in range(20, 81, 10):
        yy = y(age)
        parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{W-mr}" y2="{yy:.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{ml-8}" y="{yy+4:.1f}" text-anchor="end" class="ax">{age}</text>')
    parts.append(f'<text x="14" y="{mt+ph/2:.0f}" class="axttl" transform="rotate(-90 14 {mt+ph/2:.0f})">vek pri voľbách</text>')

    for i, t in enumerate(TERMS):
        cx = ml + step * (i + 0.5)
        bw = min(46, step * 0.5)
        ages = t["ages"]
        q1, med, q3 = t["q1"], t["median"], t["q3"]
        lo, hi = t["min"], t["max"]
        # jittered dots
        import hashlib
        for j, a in enumerate(ages):
            seed = int(hashlib.md5(f"{i}-{j}".encode()).hexdigest(), 16)
            jx = ((seed % 1000) / 1000 - 0.5) * bw * 1.5
            parts.append(f'<circle cx="{cx+jx:.1f}" cy="{y(a):.1f}" r="1.6" fill="{ACCENT}" opacity="0.16"/>')
        # whisker
        parts.append(f'<line x1="{cx:.1f}" y1="{y(hi):.1f}" x2="{cx:.1f}" y2="{y(lo):.1f}" stroke="{BOXEDGE}" stroke-width="1"/>')
        for v in (lo, hi):
            parts.append(f'<line x1="{cx-bw*0.28:.1f}" y1="{y(v):.1f}" x2="{cx+bw*0.28:.1f}" y2="{y(v):.1f}" stroke="{BOXEDGE}" stroke-width="1"/>')
        # box
        parts.append(f'<rect x="{cx-bw/2:.1f}" y="{y(q3):.1f}" width="{bw:.1f}" height="{y(q1)-y(q3):.1f}" fill="{BOX}" stroke="{BOXEDGE}" opacity="0.9"/>')
        # median
        parts.append(f'<line x1="{cx-bw/2:.1f}" y1="{y(med):.1f}" x2="{cx+bw/2:.1f}" y2="{y(med):.1f}" stroke="{INK}" stroke-width="2"/>')
        # mean diamond
        my = y(t["mean"])
        parts.append(f'<path d="M{cx:.1f},{my-4:.1f} L{cx+4:.1f},{my:.1f} L{cx:.1f},{my+4:.1f} L{cx-4:.1f},{my:.1f} Z" fill="{ACCENT2}"/>')
        # x label
        parts.append(f'<text x="{cx:.1f}" y="{H-mb+18:.0f}" text-anchor="middle" class="ax b">{esc(t["label"])}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{H-mb+32:.0f}" text-anchor="middle" class="axs">{t["n"]} posl.</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---- chart 2: trend line -------------------------------------------------
def chart_trend() -> str:
    W, H = 900, 300
    ml, mr, mt, mb = 46, 60, 20, 40
    pw, ph = W - ml - mr, H - mt - mb
    amin, amax = 40, 52
    n = len(TERMS)
    xs = [ml + pw * (i / (n - 1)) for i in range(n)]

    def y(v):
        return mt + ph - (v - amin) / (amax - amin) * ph

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Mean and median age over time">']
    for age in range(40, 53, 2):
        yy = y(age)
        parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{W-mr}" y2="{yy:.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{ml-8}" y="{yy+4:.1f}" text-anchor="end" class="ax">{age}</text>')

    def line(key, color, dash=""):
        pts = " ".join(f"{xs[i]:.1f},{y(t[key]):.1f}" for i, t in enumerate(TERMS))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"{d}/>'

    parts.append(line("mean", ACCENT2))
    parts.append(line("median", ACCENT, "5 4"))
    for i, t in enumerate(TERMS):
        parts.append(f'<circle cx="{xs[i]:.1f}" cy="{y(t["mean"]):.1f}" r="3.5" fill="{ACCENT2}"/>')
        parts.append(f'<circle cx="{xs[i]:.1f}" cy="{y(t["median"]):.1f}" r="3.5" fill="{ACCENT}"/>')
        parts.append(f'<text x="{xs[i]:.1f}" y="{y(t["mean"])-9:.1f}" text-anchor="middle" class="axs" fill="{ACCENT2}">{t["mean"]}</text>')
        parts.append(f'<text x="{xs[i]:.1f}" y="{H-mb+18:.0f}" text-anchor="middle" class="ax b">{esc(t["label"])}</text>')
    # legend
    lx = W - mr + 6
    parts.append(f'<circle cx="{lx+4}" cy="{mt+6}" r="4" fill="{ACCENT2}"/><text x="{lx+12}" y="{mt+10}" class="axs">priemer</text>')
    parts.append(f'<circle cx="{lx+4}" cy="{mt+24}" r="4" fill="{ACCENT}"/><text x="{lx+12}" y="{mt+28}" class="axs">medián</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---- chart 3: age-band composition (100% stacked) ------------------------
def chart_bands() -> str:
    W, H = 900, 340
    ml, mr, mt, mb = 30, 130, 12, 40
    pw, ph = W - ml - mr, H - mt - mb
    n = len(TERMS)
    step = pw / n
    bw = min(52, step * 0.72)
    parts = [f'<svg id="bandsvg" viewBox="0 0 {W} {H}" role="img" aria-label="Age band composition by term">']
    for i, t in enumerate(TERMS):
        cx = ml + step * (i + 0.5)
        counts = [0] * 5
        for a in t["ages"]:
            counts[band_index(a)] += 1
        tot = sum(counts)
        yb = mt + ph
        for bi, (label, color) in enumerate(BANDS):
            cnt = counts[bi]
            frac = cnt / tot
            hh = frac * ph
            yb -= hh
            parts.append(
                f'<rect class="seg" x="{cx-bw/2:.1f}" y="{yb:.1f}" width="{bw:.1f}" height="{hh:.1f}" '
                f'fill="{color}" data-term="{esc(t["label"])}" data-band="{esc(label)}" '
                f'data-pct="{frac*100:.1f}" data-n="{cnt}" data-tot="{tot}" data-color="{color}"/>'
            )
            if frac > 0.06:
                parts.append(f'<text x="{cx:.1f}" y="{yb+hh/2+4:.1f}" text-anchor="middle" class="pct">{frac*100:.0f}%</text>')
        parts.append(f'<text x="{cx:.1f}" y="{H-mb+18:.0f}" text-anchor="middle" class="ax b">{esc(t["label"])}</text>')
    # legend
    lx = W - mr + 12
    for bi, (label, color) in enumerate(BANDS):
        yy = mt + 14 + bi * 22
        parts.append(f'<rect x="{lx}" y="{yy-10}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text x="{lx+20}" y="{yy+1}" class="axs">{esc(label)} rokov</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---- chart 4 data: client-side interactive grouped histogram -------------
def compare_payload() -> str:
    """Term spans (election year + birth dates) so the comparison chart can
    build the age distribution for any year the user picks: the parliament in
    office that year, aged to that year, computed live in the browser."""
    spans = [
        {"year": int(t["election_date"][:4]), "births": t["births"]}
        for t in TERMS
    ]
    spans.sort(key=lambda s: s["year"])
    return json.dumps({"minYear": spans[0]["year"], "spans": spans}, ensure_ascii=False)


def stat_table() -> str:
    head = ("<tr><th>Voľby</th><th>Poslanci*</th><th>Priemer</th><th>Medián</th>"
            '<th>Najmladší</th><th>Najstarší</th><th>Q1–Q3</th><th><span class="nocase">σ</span></th></tr>')
    rows = []
    for t in TERMS:
        rows.append(
            f'<tr><td class="b">{esc(t["label"])}</td><td>{t["n"]}</td>'
            f'<td>{t["mean"]}</td><td>{t["median"]:g}</td>'
            f'<td>{t["min"]}</td><td>{t["max"]}</td>'
            f'<td>{t["q1"]:g}–{t["q3"]:g}</td><td>{t["stdev"]}</td></tr>'
        )
    return f"<table>{head}{''.join(rows)}</table>"


def main() -> None:
    all_mean = round(statistics.mean(t["mean"] for t in TERMS), 1)
    first, last = TERMS[0], TERMS[-1]
    youngest = DATA["records"]["youngest"]
    oldest = DATA["records"]["oldest"]
    delta = round(last["mean"] - first["mean"], 1)

    js = r"""<script>
(function(){
  const DATA = window.CMP_DATA;
  const ACCENT="#2f6fed", GRAY="#b9bdc6", GRID="#e8eaf0", INK="#1b2130", MUTED="#6b7280";
  function counts(ages, edges){
    const lo=edges[0], c=edges.map(()=>0);
    ages.forEach(a=>{ let k=Math.floor((a-lo)/5); k=Math.max(0,Math.min(k,edges.length-1)); c[k]++; });
    return c;
  }
  const SPANS=DATA.spans.slice().sort((a,b)=>a.year-b.year);
  const MINY=DATA.minYear, MAXY=new Date().getFullYear(), NOW=new Date();
  // parliament in office in year Y = latest term whose election year <= Y
  function termForYear(Y){ let sp=SPANS[0]; for(const s of SPANS){ if(s.year<=Y) sp=s; } return sp; }
  function ageAsOf(iso, ref){ const d=new Date(iso); let a=ref.getFullYear()-d.getFullYear();
    const m=ref.getMonth()-d.getMonth(); if(m<0||(m===0&&ref.getDate()<d.getDate())) a--; return a; }
  function entryForYear(Y){ const sp=termForYear(Y);
    const ref = Y>=MAXY ? NOW : new Date(Y,5,30);    // mid-year; current year = today
    return { label:String(Y), ages: sp.births.map(b=>ageAsOf(b,ref)) }; }
  function svgEl(A,B){
    const aAges=A.ages, bAges=B.ages;
    // adaptive x-range: cover both years' min..max, snapped to 5-year bins
    const all=aAges.concat(bAges);
    const lo=Math.floor(Math.min(...all)/5)*5;
    const hi=Math.floor(Math.max(...all)/5)*5;
    const edges=[]; for(let e=lo;e<=hi;e+=5) edges.push(e);
    const ca=counts(aAges,edges), cb=counts(bAges,edges);
    const totA=aAges.length, totB=bAges.length;
    const ha=ca.map(x=>x/totA), hb=cb.map(x=>x/totB);
    const peak=Math.max(...ha,...hb);
    const ymax=(Math.floor(peak*100/5)+1)*0.05;
    const W=940,H=500, ml=52,mr=16,mt=44,mb=46, pw=W-ml-mr, ph=H-mt-mb;
    const n=edges.length, step=pw/n, bw=step*0.38;
    const y=v=>mt+ph-Math.min(v,ymax)/ymax*ph;
    let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Vek ${A.label} vs ${B.label}">`;
    s+=`<text x="${ml+pw/2}" y="26" text-anchor="middle" class="ctitle">Vekové rozdelenie poslancov NR SR</text>`;
    for(let p=0;p<=Math.round(ymax*100);p+=5){ const yy=y(p/100);
      s+=`<line x1="${ml}" y1="${yy}" x2="${W-mr}" y2="${yy}" stroke="${GRID}"/>`;
      s+=`<text x="${ml-8}" y="${yy+4}" text-anchor="end" class="ax">${p}%</text>`; }
    for(let i=0;i<n;i++){ const x0=ml+step*i+(step-2*bw)/2, gx=ml+step*i, bin=`${edges[i]}\u2013${edges[i]+4}`;
      [[ha[i],ACCENT,0],[hb[i],GRAY,bw]].forEach(([fr,col,off])=>{ const h=ph-(y(fr)-mt);
        s+=`<rect x="${x0+off}" y="${y(fr)}" width="${bw}" height="${h}" fill="${col}" stroke="#5a5f6a" stroke-width="0.4"/>`; });
      s+=`<rect class="hit" x="${gx}" y="${mt}" width="${step}" height="${ph}" fill="transparent"`
        +` data-bin="${bin}" data-la="${A.label}" data-pa="${(ha[i]*100).toFixed(1)}" data-na="${ca[i]}" data-ta="${totA}"`
        +` data-lb="${B.label}" data-pb="${(hb[i]*100).toFixed(1)}" data-nb="${cb[i]}" data-tb="${totB}"/>`;
      s+=`<text x="${ml+step*i+step/2}" y="${H-mb+18}" text-anchor="middle" class="ax">${edges[i]}</text>`; }
    s+=`<text x="${ml+pw/2}" y="${H-6}" text-anchor="middle" class="axttl">veková kategória (roky)</text>`;
    s+=`<text x="${ml+step*0.9}" y="${mt+34}" class="era" fill="${ACCENT}">${A.label}</text>`;
    s+=`<text x="${ml+step*(n-2.4)}" y="${mt+40}" class="era" fill="#9aa0ab">${B.label}</text>`;
    return s+"</svg>";
  }
  const selA=document.getElementById("selA"), selB=document.getElementById("selB"),
        outA=document.getElementById("outA"), outB=document.getElementById("outB"),
        cmp=document.getElementById("cmp"), swap=document.getElementById("swap");
  const tip=document.createElement("div"); tip.className="tip"; tip.style.display="none";
  document.body.appendChild(tip);
  [selA,selB].forEach(sl=>{ sl.min=MINY; sl.max=MAXY; sl.step=1; });
  selA.value=MINY; selB.value=MAXY;
  function draw(){ const ya=+selA.value, yb=+selB.value;
    outA.textContent=ya; outB.textContent=yb;
    cmp.innerHTML=svgEl(entryForYear(ya), entryForYear(yb)); }
  selA.addEventListener("input",draw); selB.addEventListener("input",draw);
  swap.addEventListener("click",()=>{ const a=selA.value; selA.value=selB.value; selB.value=a; draw(); });
  function showTip(html,e){ tip.innerHTML=html; tip.style.display="block";
    tip.style.left=Math.max(8, Math.min(e.clientX+14, innerWidth-tip.offsetWidth-8))+"px";
    tip.style.top=Math.max(8, Math.min(e.clientY+14, innerHeight-tip.offsetHeight-8))+"px"; }
  function hideTip(){ tip.style.display="none"; }
  cmp.addEventListener("mousemove",e=>{ const b=e.target.closest(".hit"); if(!b){ hideTip(); return; }
    const d=b.dataset;
    showTip(`<div class="tb">${d.bin} rokov</div>`
      +`<div class="tr"><span class="sw" style="background:${ACCENT}"></span>${d.la}: <b>${d.pa}%</b> <span class="tn">(${d.na} z ${d.ta})</span></div>`
      +`<div class="tr"><span class="sw" style="background:${GRAY}"></span>${d.lb}: <b>${d.pb}%</b> <span class="tn">(${d.nb} z ${d.tb})</span></div>`, e); });
  cmp.addEventListener("mouseleave",hideTip);
  const bandsvg=document.getElementById("bandsvg");
  if(bandsvg){
    bandsvg.addEventListener("mousemove",e=>{ const s=e.target.closest(".seg"); if(!s){ hideTip(); return; }
      const d=s.dataset;
      showTip(`<div class="tb">${d.band} rokov</div>`
        +`<div class="tr"><span class="sw" style="background:${d.color}"></span>${d.term}: <b>${d.pct}%</b> <span class="tn">(${d.n} z ${d.tot})</span></div>`, e); });
    bandsvg.addEventListener("mouseleave",hideTip);
  }
  draw();
})();
</script>"""

    tpl = f"""<!doctype html>
<html lang="sk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vekové zloženie NR SR (1994–2023)</title>
<style>
  :root {{ --ink:{INK}; --muted:{MUTED}; --accent:{ACCENT}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:#f7f8fb; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 20px 80px; }}
  header h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-.02em; }}
  header p.sub {{ color:var(--muted); margin:0 0 24px; font-size:17px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:22px 0 34px; }}
  .kpi {{ background:#fff; border:1px solid {GRID}; border-radius:12px; padding:16px 16px 14px; }}
  .kpi .n {{ font-size:26px; font-weight:700; letter-spacing:-.01em; }}
  .kpi .l {{ color:var(--muted); font-size:13px; margin-top:2px; }}
  section {{ background:#fff; border:1px solid {GRID}; border-radius:14px; padding:22px 22px 12px; margin:20px 0; }}
  section h2 {{ font-size:19px; margin:0 0 2px; }}
  section p.desc {{ color:var(--muted); margin:0 0 14px; font-size:14px; }}
  svg {{ width:100%; height:auto; display:block; }}
  .ax {{ fill:{MUTED}; font-size:12px; }}
  .ax.b {{ fill:var(--ink); font-weight:600; }}
  .axs {{ fill:{MUTED}; font-size:11px; }}
  .axttl {{ fill:{MUTED}; font-size:12px; text-anchor:middle; }}
  .pct {{ fill:#fff; font-size:11px; font-weight:600; }}
  .ctitle {{ fill:var(--ink); font-size:20px; font-weight:700; }}
  .era {{ font-size:26px; font-weight:700; letter-spacing:-.01em; }}
  .picker {{ display:flex; gap:20px; align-items:center; margin:0 0 10px; flex-wrap:wrap; }}
  .picker .yr {{ display:flex; align-items:center; gap:8px; font-size:14px; color:var(--muted);
                flex:1 1 260px; min-width:240px; }}
  .picker .yr .tag {{ font-weight:700; font-size:15px; }}
  .picker .yr input[type=range] {{ flex:1; accent-color:var(--accent); cursor:pointer; }}
  .picker .yr output {{ font-weight:700; font-size:16px; color:var(--ink); min-width:3ch;
                       font-variant-numeric:tabular-nums; text-align:right; }}
  .picker #swap {{ font-size:16px; padding:6px 12px; border:1px solid #cdd2dc; border-radius:8px;
                  background:#fff; cursor:pointer; color:var(--ink); }}
  .picker #swap:hover {{ background:#eef1f7; }}
  svg text {{ pointer-events:none; }}
  #cmp .hit, #bandsvg .seg {{ cursor:crosshair; }}
  #bandsvg .seg:hover {{ opacity:.82; }}
  .tip {{ position:fixed; z-index:20; pointer-events:none; background:{INK}; color:#fff;
          padding:8px 11px; border-radius:8px; font-size:13px; line-height:1.5;
          box-shadow:0 4px 14px rgba(0,0,0,.22); max-width:260px; }}
  .tip .tb {{ font-weight:700; margin-bottom:4px; }}
  .tip .tr {{ white-space:nowrap; }}
  .tip .tn {{ color:#c3c9d4; }}
  .tip .sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; margin-top:6px; }}
  th,td {{ padding:8px 10px; text-align:right; border-bottom:1px solid {GRID}; }}
  th:first-child, td:first-child {{ text-align:left; }}
  th {{ color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.03em; }}
  th .nocase {{ text-transform:none; font-size:14px; }}
  td.b {{ font-weight:700; }}
  .legend-inline span {{ display:inline-block; margin-right:14px; font-size:13px; color:var(--muted); }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }}
  footer {{ color:var(--muted); font-size:13px; line-height:1.7; margin-top:26px; }}
  footer code {{ background:#eef1f7; padding:1px 5px; border-radius:4px; font-size:12px; }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Vekové zloženie Národnej rady SR</h1>
  <p class="sub">Ako starí boli slovenskí poslanci pri každých parlamentných voľbách, 1994–2023.
     Vek počítaný ku dňu volieb, zo všetkých {sum(t['n'] for t in TERMS)} mandátov (vrátane náhradníkov).</p>
</header>

<div class="kpis">
  <div class="kpi"><div class="n">{all_mean}</div><div class="l">priemerný vek naprieč 9 voľbami</div></div>
  <div class="kpi"><div class="n">{last['mean']}</div><div class="l">priemer 2023 ({'+' if delta>=0 else ''}{delta} r. oproti 1994)</div></div>
  <div class="kpi"><div class="n">{youngest['age']}</div><div class="l">najmladší poslanec:<br><a href="{esc(youngest['url'])}" target="_blank" rel="noopener">{esc(youngest['name'])}</a> ({youngest['label']})</div></div>
  <div class="kpi"><div class="n">{oldest['age']}</div><div class="l">najstarší poslanec:<br><a href="{esc(oldest['url'])}" target="_blank" rel="noopener">{esc(oldest['name'])}</a> ({oldest['label']})</div></div>
</div>

<section>
  <h2>Porovnanie</h2>
  <p class="desc">Posuň jazdce a porovnaj ľubovoľné dva roky, od {TERMS[0]['label']} po dnešok.
     Pre každý rok sa vezme parlament, ktorý v tom roku úradoval, a vek poslancov sa
     prepočíta k danému roku (aktuálny rok k dnešnému dňu). Podiel = z poslancov daného obdobia.</p>
  <div class="picker">
    <label class="yr"><span class="tag" style="color:{ACCENT}">A</span>
      <input type="range" id="selA"><output id="outA"></output></label>
    <label class="yr"><span class="tag" style="color:#9aa0ab">B</span>
      <input type="range" id="selB"><output id="outB"></output></label>
    <button id="swap" type="button" title="Vymeniť">⇄</button>
  </div>
  <div id="cmp"></div>
</section>

<section>
  <h2>Rozdelenie veku podľa volebného obdobia</h2>
  <p class="desc">Každý stĺpec = jedny voľby. Box = medzikvartilové rozpätie (Q1–Q3), čiara = medián,
     kosoštvorec = priemer, fúzy = najmladší a najstarší. Body v pozadí sú jednotliví poslanci.</p>
  {chart_boxplots()}
  <p class="legend-inline"><span><span class="dot" style="background:{BOX}"></span>Q1–Q3</span>
    <span><span class="dot" style="background:{INK}"></span>medián</span>
    <span><span class="dot" style="background:{ACCENT2}"></span>priemer</span></p>
</section>

<section>
  <h2>Priemerný a mediánový vek v čase</h2>
  <p class="desc">Vek parlamentu je pozoruhodne stabilný, okolo 47 rokov počas troch dekád, s miernym nárastom v roku 2023.</p>
  {chart_trend()}
</section>

<section>
  <h2>Zastúpenie vekových skupín</h2>
  <p class="desc">Podiel poslancov v jednotlivých vekových pásmach (100 % = všetci poslanci daného obdobia).</p>
  {chart_bands()}
</section>

<section>
  <h2>Súhrnná tabuľka</h2>
  {stat_table()}
  <p class="desc" style="margin-top:10px">
    <b>σ</b> (malé sigma) = smerodajná odchýlka veku, teda ako veľmi sa vek poslancov typicky líši od priemeru
    (vyššie σ = pestrejšie vekové zloženie). <b>Q1–Q3</b> = pásmo, v ktorom sa nachádza stredná polovica poslancov.<br>
    * Počet zahŕňa všetkých, ktorí v danom období zastávali mandát, vrátane náhradníkov, preto je vyšší ako 150.
  </p>
</section>

<footer>
  <strong>Metodika a zdroje.</strong> Zostavené „from first principles“ z verejných stránok
  Národnej rady SR (<code>nrsr.sk</code>): pre každé volebné obdobie sa načítal abecedný zoznam
  poslancov a detailná stránka každého poslanca s dátumom narodenia
  (<code>Narodený(á)</code>). Vek = celé roky ku dňu volieb daného obdobia
  (1994-10-01, 1998-09-26, 2002-09-21, 2006-06-17, 2010-06-12, 2012-03-10,
  2016-03-05, 2020-02-29, 2023-09-30). Zoznam pre aktuálne obdobie (2023) uvádza
  len sediacich poslancov, preto bol doplnený o všetkých, ktorí v ňom hlasovali
  (mandát počas obdobia opustili napr. ministri), spolu 189. Traja poslanci mali
  na nrsr.sk chybný/prázdny dátum narodenia (Sólymos, Jurinová, Borguľa), opravené
  podľa Wikipédie/TASR.
  Dáta: <code>data/mps.csv</code>, <code>data/distribution.json</code>. Generované {esc(DATA['generated'])}.
</footer>
</div>
<script>window.CMP_DATA = {compare_payload()};</script>
{js}
</body>
</html>"""
    (ROOT / "index.html").write_text(tpl, encoding="utf-8")
    print(f"wrote index.html ({len(tpl)} bytes)")


if __name__ == "__main__":
    main()
