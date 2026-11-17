"""Build the one-page project website from saved data and the editable text file.

Input : data/us_macro_annual.csv, outputs/lp_gini_response.csv  (numbers)
        site/content.md                                         (words)
        outputs/inequality_macro_summary.pdf                    (copied for download)
Output: docs/index.html (+ the PDF), ready for GitHub Pages ("main" branch, /docs folder)

Same rule as 03_build_report.py: numbers are computed from the saved artifacts,
never typed. The text in site/content.md refers to them with {placeholders};
an unknown placeholder stops the build rather than leaving a gap on the page.

Usage:
    python code/04_build_site.py               # build docs/index.html
    python code/04_build_site.py --list-facts  # show every available placeholder
"""
import html
import json
import pathlib
import re
import shutil
import sys

import markdown
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "us_macro_annual.csv"
LP = ROOT / "outputs" / "lp_gini_response.csv"
PDF = ROOT / "outputs" / "inequality_macro_summary.pdf"
CONTENT = ROOT / "site" / "content.md"
DOCS = ROOT / "docs"
REPO_URL = "https://github.com/jvelaise/us-inequality-macro"

SHOCKS = {"gdp": "gdp_growth", "inf": "inflation_cpi_avg", "fis": "fiscal_balance_pct_gdp"}
LP_TITLES = {
    "gdp": "Growth +1 pp",
    "inf": "Inflation +1 pp",
    "fis": "Budget balance +1 pp",
}
REQUIRED_SECTIONS = ["intro", "rise", "cycle", "size", "drivers", "caveats", "method"]


# ---------------------------------------------------------------- facts ----
def _slope_per_decade(s):
    return float(np.polyfit(s.index, s.values, 1)[0] * 10)


def _ranges(hs):
    """[0,1,2,3,4,7] -> '0-4 and 7' (en dash)."""
    if not hs:
        return "none"
    groups, start, prev = [], hs[0], hs[0]
    for h in hs[1:] + [None]:
        if h is not None and h == prev + 1:
            prev = h
            continue
        groups.append(f"{start}–{prev}" if prev > start else f"{start}")
        if h is not None:
            start = prev = h
    return groups[0] if len(groups) == 1 else ", ".join(groups[:-1]) + " and " + groups[-1]


def compute_facts():
    panel = pd.read_csv(PANEL, index_col="year")
    lp = pd.read_csv(LP)
    g = (panel["gini_families"].dropna() * 100)
    low_year = int(g.idxmin())
    jumps = g.diff().dropna()
    decade_means = g.groupby((g.index // 10) * 10).mean()

    facts = {"g": {
        "first_year": int(g.index[0]), "first_value": f"{g.iloc[0]:.1f}",
        "last_year": int(g.index[-1]), "last_value": f"{g.iloc[-1]:.1f}",
        "low_year": low_year, "low_value": f"{g.min():.1f}",
        "max_year": int(g.idxmax()), "max_value": f"{g.max():.1f}",
        "rise_since_low": f"{g.iloc[-1] - g.min():.1f}",
        "trend_before": f"{abs(_slope_per_decade(g.loc[:low_year])):.1f}",
        "trend_after": f"{_slope_per_decade(g.loc[low_year:]):.1f}",
        "jump_year": int(jumps.idxmax()), "jump_size": f"{jumps.max():.1f}",
    }}

    cc = panel.dropna()
    rise_cc = (cc["gini_families"].iloc[-1] - cc["gini_families"].iloc[0]) * 100
    facts["s"] = {"start": int(cc.index.min()), "end": int(cc.index.max()), "n": len(cc),
                  "rise": f"{rise_cc:.1f}", "n_min": int(lp.n.min()), "n_max": int(lp.n.max())}

    for key, shock in SHOCKS.items():
        sub = lp[lp.shock == shock].sort_values("horizon").reset_index(drop=True)
        sig = [int(r.horizon) for r in sub.itertuples() if r.lo90 * r.hi90 > 0]
        pk = sub.loc[sub.beta.abs().idxmax()]
        pos_sig = [int(r.horizon) for r in sub.itertuples() if r.beta > 0 and r.lo90 > 0]
        facts[key] = {
            "h0": f"{abs(sub.beta.iloc[0]):.2f}",
            "peak": f"{abs(pk.beta):.2f}", "peak_h": int(pk.horizon),
            "sig": _ranges(sig),
            "flip_h": pos_sig[0] if pos_sig else "none",
        }
    facts["gdp"]["share_pct"] = f"{facts_share(lp, rise_cc):.0f}"

    charts = {
        "gini": {"x": [int(i) for i in g.index], "y": [round(float(v), 1) for v in g.values],
                 "marks": [int(g.index[0]), low_year, int(g.index[-1])],
                 "note_year": int(jumps.idxmax())},
        "lp": {k: lp[lp.shock == s].sort_values("horizon")[["horizon", "beta", "lo90", "hi90"]]
               .round(3).to_dict("list") for k, s in SHOCKS.items()},
        "size": [{"label": f"Rise in the Gini, {facts['s']['start']}–{facts['s']['end']}",
                  "value": round(rise_cc, 2)},
                 {"label": "Largest effect of the business cycle (faster growth)",
                  "value": round(float(facts["gdp"]["peak"]), 2)}],
    }
    checks = {"decades_rising_since_1970s": bool(decade_means.loc[1970:].is_monotonic_increasing)}
    return facts, charts, checks, g, lp


def facts_share(lp, rise_cc):
    sub = lp[lp.shock == SHOCKS["gdp"]]
    return abs(sub.beta.loc[sub.beta.abs().idxmax()]) / rise_cc * 100


# -------------------------------------------------------------- content ----
PLACEHOLDER = re.compile(r"\{([a-z]+)\.([a-z0-9_]+)\}")


def fill(text, facts):
    def sub(m):
        ns, key = m.groups()
        try:
            return str(facts[ns][key])
        except KeyError:
            raise KeyError(f"unknown placeholder {{{ns}.{key}}} in site/content.md; "
                           f"run with --list-facts to see valid names") from None
    return PLACEHOLDER.sub(sub, text)


def parse_content(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "site/content.md must start with a --- front-matter block"
    meta = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    body = re.sub(r"<!--.*?-->", "", text[m.end():], flags=re.S)
    sections = {}
    for chunk in re.split(r"^## ", body, flags=re.M)[1:]:
        head, _, md = chunk.partition("\n")
        sid, _, heading = head.partition("|")
        sections[sid.strip()] = {"heading": heading.strip(), "md": md.strip()}
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    assert not missing, f"site/content.md is missing sections: {missing}"
    return meta, sections


def md_to_html(md):
    return markdown.markdown(md, extensions=["sane_lists"])


# ----------------------------------------------------------------- html ----
def table(headers, rows):
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>"
                  for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def data_tables(g, lp):
    gini_tbl = table(["Year", "Gini (0–100)"], [(y, f"{v:.1f}") for y, v in g.items()])
    lp_rows = []
    for k, s in SHOCKS.items():
        for r in lp[lp.shock == s].sort_values("horizon").itertuples():
            lp_rows.append((LP_TITLES[k], r.horizon, f"{r.beta:+.3f}",
                            f"[{r.lo90:+.3f}, {r.hi90:+.3f}]", r.n))
    lp_tbl = table(["Variable", "Years after", "Gini change", "90% range", "n"], lp_rows)
    wrap = lambda t: f'<div class="scroll">{t}</div>'
    return wrap(gini_tbl), wrap(lp_tbl)


def build_html(meta, sections, facts, charts, g, lp):
    S = {k: {"heading": html.escape(fill(v["heading"], facts)),
             "body": md_to_html(fill(v["md"], facts))} for k, v in sections.items()}
    title = html.escape(fill(meta.get("title", "Income inequality"), facts))
    subtitle = html.escape(fill(meta.get("subtitle", ""), facts))
    draft = meta.get("status", "draft").lower() != "approved"
    gini_tbl, lp_tbl = data_tables(g, lp)
    f = facts

    def section(sid, extra=""):
        return (f'<section id="{sid}"><h2>{S[sid]["heading"]}</h2>'
                f'{S[sid]["body"]}{extra}</section>')

    tiles = f"""<div class="tiles">
  <div class="tile"><div class="tile-v">{f['g']['last_value']}</div><div class="tile-l">Gini index for US families, {f['g']['last_year']}</div></div>
  <div class="tile"><div class="tile-v">+{f['g']['rise_since_low']}</div><div class="tile-l">points since the {f['g']['low_year']} low</div></div>
  <div class="tile"><div class="tile-v">~{f['gdp']['share_pct']}%</div><div class="tile-l">of the rise matched by the largest business-cycle effect</div></div>
</div>"""
    gini_fig = f"""<figure><div class="chart" id="chart-gini" role="img"
  aria-label="Line chart of the US family Gini index, {f['g']['first_year']} to {f['g']['last_year']}"></div>
  <figcaption>Gini index for US families (0&ndash;100; higher = more unequal). Source: US Census Bureau via FRED (GINIALLRF).</figcaption>
  <details><summary>Show data table</summary>{gini_tbl}</details></figure>"""
    lp_fig = "<figure><div class=\"multiples\">" + "".join(
        f'<div><h3>{html.escape(LP_TITLES[k])}</h3><div class="chart small" id="chart-lp-{k}" '
        f'role="img" aria-label="Change in Gini over 8 years after: {html.escape(LP_TITLES[k])}"></div></div>'
        for k in SHOCKS) + f"""</div>
  <figcaption>Cumulative change in the Gini index (points) in the years after a 1 percentage point higher value of each variable. Line: estimate. Band: 90% confidence range. Responses are predictive, not proven causal effects.</figcaption>
  <details><summary>Show data table</summary>{lp_tbl}</details></figure>"""
    size_fig = "<figure><div class=\"bars\" id=\"chart-size\">" + "".join(
        f'<div class="bar-row"><div class="bar-label">{html.escape(b["label"])}</div>'
        f'<div class="bar-track"><div class="bar" style="width:{b["value"] / charts["size"][0]["value"] * 100:.2f}%"></div>'
        f'<span class="bar-v">{b["value"]:.2f} points</span></div></div>'
        for b in charts["size"]) + "</div></figure>"

    downloads = (f'<p class="links"><a href="inequality_macro_summary.pdf">Two-page technical summary (PDF)</a> &middot; '
                 f'<a href="{REPO_URL}">Code and data on GitHub</a> &middot; '
                 f'<a href="{REPO_URL}/blob/main/notebooks/gini_coefficient.ipynb">Gini notebook</a></p>')

    banner = ('<div class="draft" role="note"><strong>DRAFT</strong> &mdash; text not yet reviewed. '
              'Set <code>status: approved</code> in site/content.md once every claim is checked.</div>'
              if draft else "")

    return TEMPLATE.format(
        title=title, subtitle=subtitle, banner=banner, tiles=tiles,
        intro=section("intro"), rise=section("rise", gini_fig), cycle=section("cycle", lp_fig),
        size=section("size", size_fig), drivers=section("drivers"),
        caveats=section("caveats"), method=section("method", downloads),
        data=json.dumps(charts, separators=(",", ":")), script=SCRIPT, css=CSS)


CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--series:#2a78d6;--ring:rgba(11,11,11,.10);--warn-bg:#fff4d6;--warn-ink:#5c4300}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--series:#3987e5;--ring:rgba(255,255,255,.10);
--warn-bg:#3a2e0c;--warn-ink:#f7dd9a}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--series:#3987e5;--ring:rgba(255,255,255,.10);--warn-bg:#3a2e0c;--warn-ink:#f7dd9a}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:780px;margin:0 auto;padding:32px 16px 64px}
header h1{font-size:2rem;line-height:1.2;margin:0 0 6px}
header p{color:var(--ink2);margin:0 0 24px;font-size:1.1rem}
h2{font-size:1.35rem;line-height:1.3;margin:48px 0 8px}
h3{font-size:.85rem;font-weight:600;color:var(--ink2);margin:0 0 4px}
p,li{color:var(--ink)} ul,ol{padding-left:1.3em} li{margin:6px 0}
a{color:var(--series)}
.draft{background:var(--warn-bg);color:var(--warn-ink);padding:10px 14px;border-radius:8px;margin-bottom:24px;font-size:.9rem}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:8px 0 8px}
.tile{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:14px}
.tile-v{font-size:2rem;font-weight:650;line-height:1.1}
.tile-l{color:var(--ink2);font-size:.85rem;margin-top:4px}
figure{margin:20px 0 8px;background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:16px}
figcaption{color:var(--ink2);font-size:.8rem;margin-top:8px}
.chart{position:relative;height:300px;touch-action:pan-y}
.chart.small{height:200px}
.multiples{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
svg text{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
svg .lbl{fill:var(--ink);font-size:12px}
.gridline{stroke:var(--grid);stroke-width:1}
.axis{stroke:var(--axis);stroke-width:1}
.zero{stroke:var(--ink2);stroke-width:1}
.line{fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.band{fill:var(--series);opacity:.18}
.dot{fill:var(--series);stroke:var(--surface);stroke-width:2}
.cross{stroke:var(--ink2);stroke-width:1;stroke-dasharray:3 3}
.tip{position:absolute;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);
box-shadow:0 2px 8px rgba(0,0,0,.12);border-radius:6px;padding:6px 8px;font-size:.8rem;line-height:1.35;white-space:nowrap;display:none;z-index:2}
.tip b{font-variant-numeric:tabular-nums}
.bars{display:grid;gap:14px}
.bar-label{font-size:.9rem;color:var(--ink2);margin-bottom:4px}
.bar-track{display:flex;align-items:center;gap:8px}
.bar{height:22px;min-width:4px;background:var(--series);border-radius:0 4px 4px 0}
.bar-v{font-size:.9rem;font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums}
details{margin-top:10px;font-size:.85rem} summary{cursor:pointer;color:var(--ink2)}
details table{border-collapse:collapse;margin-top:8px;width:100%;font-variant-numeric:tabular-nums}
details div.scroll{max-height:320px;overflow:auto}
th,td{text-align:left;padding:3px 8px;border-bottom:1px solid var(--grid)}
.links{font-size:.95rem}
footer{color:var(--muted);font-size:.8rem;margin-top:48px}
@media (max-width:640px){.tiles{grid-template-columns:1fr}.multiples{grid-template-columns:1fr}
header h1{font-size:1.6rem}.chart{height:240px}}
"""

SCRIPT = r"""
(function(){
const D = JSON.parse(document.getElementById('chart-data').textContent);
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e;}
function lin(d0,d1,r0,r1){return v=>r0+(v-d0)/(d1-d0)*(r1-r0);}
function niceTicks(lo,hi,n){const raw=(hi-lo)/n,p=Math.pow(10,Math.floor(Math.log10(raw)));
  const step=[1,2,2.5,5,10].map(m=>m*p).find(s=>s>=raw);const t=[];for(let v=Math.ceil(lo/step)*step;v<=hi+1e-9;v+=step)t.push(+v.toFixed(6));return t;}

function lineChart(host, o){
  host.innerHTML='';
  const W=host.clientWidth, H=host.clientHeight, m={t:14,r:o.padR||14,b:26,l:38};
  const svg=el('svg',{width:W,height:H,viewBox:`0 0 ${W} ${H}`},host);
  const x=lin(o.xDomain[0],o.xDomain[1],m.l,W-m.r), y=lin(o.yDomain[0],o.yDomain[1],H-m.b,m.t);
  niceTicks(o.yDomain[0],o.yDomain[1],o.yTicks||4).forEach(v=>{
    if(v<o.yDomain[0]||v>o.yDomain[1])return;
    el('line',{x1:m.l,x2:W-m.r,y1:y(v),y2:y(v),class:'gridline'},svg);
    el('text',{x:m.l-6,y:y(v)+4,'text-anchor':'end'},svg).textContent=o.yFmt(v);});
  el('line',{x1:m.l,x2:W-m.r,y1:H-m.b,y2:H-m.b,class:'axis'},svg);
  o.xTicks.forEach(v=>{el('text',{x:x(v),y:H-m.b+16,'text-anchor':'middle'},svg).textContent=v;});
  if(o.zero) el('line',{x1:m.l,x2:W-m.r,y1:y(0),y2:y(0),class:'zero'},svg);
  const X=o.x;
  if(o.lo){let d='M'+X.map((v,i)=>x(v)+','+y(o.hi[i])).join('L')+'L'+X.slice().reverse().map((v,j)=>x(v)+','+y(o.lo[X.length-1-j])).join('L')+'Z';el('path',{d,class:'band'},svg);}
  el('path',{d:'M'+X.map((v,i)=>x(v)+','+y(o.y[i])).join('L'),class:'line'},svg);
  (o.marks||[]).forEach(mk=>{const i=X.indexOf(mk.x);el('circle',{cx:x(mk.x),cy:y(o.y[i]),r:4.5,class:'dot'},svg);
    const t=el('text',{x:x(mk.x)+(mk.dx||0),y:y(o.y[i])+(mk.dy||-10),'text-anchor':mk.anchor||'middle',class:'lbl'},svg);t.textContent=mk.text;});
  if(o.dots) X.forEach((v,i)=>el('circle',{cx:x(v),cy:y(o.y[i]),r:3,class:'dot'},svg));
  // hover layer
  const tip=document.createElement('div');tip.className='tip';host.appendChild(tip);
  const cross=el('line',{y1:m.t,y2:H-m.b,class:'cross',visibility:'hidden'},svg);
  const hd=el('circle',{r:5,class:'dot',visibility:'hidden'},svg);
  const hit=el('rect',{x:m.l,y:0,width:W-m.l-m.r,height:H,fill:'transparent'},svg);
  function move(ev){const r=svg.getBoundingClientRect(),px=ev.clientX-r.left;
    let i=0,best=1e9;X.forEach((v,j)=>{const d=Math.abs(x(v)-px);if(d<best){best=d;i=j;}});
    cross.setAttribute('x1',x(X[i]));cross.setAttribute('x2',x(X[i]));cross.setAttribute('visibility','visible');
    hd.setAttribute('cx',x(X[i]));hd.setAttribute('cy',y(o.y[i]));hd.setAttribute('visibility','visible');
    tip.innerHTML=o.tip(i);tip.style.display='block';
    const tw=tip.offsetWidth;let left=x(X[i])+10;if(left+tw>W)left=x(X[i])-tw-10;
    tip.style.left=Math.max(0,left)+'px';tip.style.top=m.t+'px';}
  function leave(){tip.style.display='none';cross.setAttribute('visibility','hidden');hd.setAttribute('visibility','hidden');}
  hit.addEventListener('pointermove',move);hit.addEventListener('pointerdown',move);hit.addEventListener('pointerleave',leave);
}

function drawAll(){
  const g=D.gini, gx=g.x, gy=g.y, val=yr=>gy[gx.indexOf(yr)];
  const lo=Math.floor(Math.min(...gy))-1, hi=Math.ceil(Math.max(...gy))+1;
  const [m0,m1,m2]=g.marks, narrow=document.getElementById('chart-gini').clientWidth<480;
  lineChart(document.getElementById('chart-gini'),{x:gx,y:gy,xDomain:[gx[0],gx[gx.length-1]],yDomain:[lo,hi],padR:18,
    xTicks:gx.filter(v=>v%(narrow?20:10)===0),yFmt:v=>v,
    marks:[{x:m0,text:`${m0}: ${val(m0).toFixed(1)}`,anchor:'start',dx:4,dy:-10},
           {x:m1,text:`Low, ${m1}: ${val(m1).toFixed(1)}`,dy:20},
           {x:m2,text:`${m2}: ${val(m2).toFixed(1)}`,anchor:'end',dy:-12}],
    tip:i=>`${gx[i]}<br>Gini <b>${gy[i].toFixed(1)}</b>`+(gx[i]===g.note_year?'<br>Census survey change this year':'')});
  const all=[];Object.values(D.lp).forEach(s=>all.push(...s.lo90,...s.hi90));
  const pad=0.03,ylo=Math.min(...all)-pad,yhi=Math.max(...all)+pad;
  for(const k in D.lp){const s=D.lp[k];
    lineChart(document.getElementById('chart-lp-'+k),{x:s.horizon,y:s.beta,lo:s.lo90,hi:s.hi90,zero:true,dots:true,
      xDomain:[0,8],yDomain:[ylo,yhi],xTicks:[0,2,4,6,8],yFmt:v=>(v>0?'+':'')+v.toFixed(1),yTicks:4,
      tip:i=>`${s.horizon[i]} yr after<br>Gini <b>${s.beta[i]>0?'+':''}${s.beta[i].toFixed(2)}</b> pts<br>range ${s.lo90[i].toFixed(2)} to ${s.hi90[i].toFixed(2)}`});}
}
drawAll();
let t;new ResizeObserver(()=>{clearTimeout(t);t=setTimeout(drawAll,80);}).observe(document.querySelector('main'));
})();
"""

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{subtitle}">
<style>{css}</style></head>
<body><main>
{banner}
<header><h1>{title}</h1><p>{subtitle}</p></header>
{tiles}
{intro}
{rise}
{cycle}
{size}
{drivers}
{caveats}
{method}
<footer>Built by code/04_build_site.py from the data in this project's repository.</footer>
</main>
<script type="application/json" id="chart-data">{data}</script>
<script>{script}</script>
</body></html>
"""


def main(argv):
    facts, charts, checks, g, lp = compute_facts()
    if "--list-facts" in argv:
        for ns, d in facts.items():
            for k, v in d.items():
                print(f"{{{ns}.{k}}}".ljust(24), v)
        return
    meta, sections = parse_content(CONTENT.read_text())
    page = build_html(meta, sections, facts, charts, g, lp)
    leftover = re.findall(r"\{[a-z]+\.[a-z0-9_]+\}", page)
    assert not leftover, f"unfilled placeholders: {leftover}"
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page)
    (DOCS / ".nojekyll").write_text("")
    if PDF.exists():
        shutil.copy(PDF, DOCS / PDF.name)
    status = meta.get("status", "draft")
    print(f"wrote docs/index.html ({len(page) // 1024} KB), status: {status}; checks: {checks}")


if __name__ == "__main__":
    main(sys.argv[1:])
