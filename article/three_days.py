#!/usr/bin/env python3
"""Figure: "Three days in the life of an SD-Power hybrid" (the NEA testbed's playout principle, Craig 7 Nov).

Reads docs/article/data/trace_<year>.json (scripts/spark/gb_trace.py) and writes
docs/article/sd_power_hybrid/figures/three_days.html: an animated, interactive playout for the web (three controller
lanes, the price and weather above, Britain's demand against the SD-Power cap below, captions at the moments that
explain it, a verdict at the end of each day) plus a static small-multiple version shown in print.
    .venv/bin/python scripts/article/three_days.py [2010]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YEAR = sys.argv[1] if len(sys.argv) > 1 else "2010"
TRACE = json.load(open(ROOT / "docs" / "article" / "data" / f"trace_{YEAR}.json"))
FIG = ROOT / "docs" / "article" / "sd_power_hybrid" / "figures" / "three_days.html"
ORDER = sorted(TRACE["days"], key=lambda k: TRACE["days"][k]["date"])
LANES = [("biv0", "Fixed 0 °C switch", "ships today"), ("ccop", "C-COP", "price only"),
         ("sdp", "SD-Power", "price + the grid")]


def compact():
    out = {"lanes": LANES, "order": ORDER, "days": {}}
    for k in ORDER:
        d = TRACE["days"][k]
        out["days"][k] = {kk: d[kk] for kk in ("date", "price_date", "out_c", "heat_kwh", "cop", "carb_g", "price_p", "phi",
                                               "elec_kwh", "day_cost_p", "day_kg", "gb")}
    out["gas_p"], out["gas_kg"] = TRACE["gas_p"], TRACE["gas_kg"]
    return out


JS = r"""
(function () {
  const D = JSON.parse(document.getElementById("td-data").textContent);
  const $ = id => document.getElementById(id), NS = "http://www.w3.org/2000/svg";
  const el = (t, a, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const fmtT = s => `${String(Math.floor(s / 2)).padStart(2, "0")}:${s % 2 ? "30" : "00"}`;
  const nice = d => new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  const TAR = [["agile", "Agile"], ["cosy", "Cosy"], ["iog", "IOG"], ["svr", "SVR"]];
  let day = D.order[0], tar = "agile", slot = 0, playing = !matchMedia("(prefers-reduced-motion: reduce)").matches, acc = 0, last = 0, hold = 0;
  const W = 760, X = s => 150 + s * (W - 160) / 48;
  function seg(id, items, cur, on) { const box = $(id); box.innerHTML = ""; items.forEach(([k, l]) => { const b = document.createElement("button"); b.type = "button"; b.textContent = l; b.setAttribute("aria-pressed", String(k === cur)); b.onclick = () => on(k); box.appendChild(b); }); }
  function hpShare(d, c, s) { const h = d.heat_kwh[s]; return h > 1e-6 ? Math.min(1, d.elec_kwh[tar][c][s] * d.cop[s] / h) : 1; }
  function draw() {
    const d = D.days[day], svg = $("td-svg"); svg.innerHTML = "";
    // price strip
    const pr = d.price_p[tar], pmin = Math.min(0, ...pr), pmax = Math.max(40, ...pr), PY = v => 44 - (v - pmin) / (pmax - pmin) * 34;
    el("text", { x: 4, y: 20, class: "lab" }, svg).textContent = "Price p/kWh";
    el("line", { x1: X(0), x2: X(48), y1: PY(0), y2: PY(0), class: "grid" }, svg);
    const gasEq = D.gas_p / 0.9;
    el("line", { x1: X(0), x2: X(48), y1: PY(gasEq), y2: PY(gasEq), class: "ref" }, svg);
    el("text", { x: X(48) - 2, y: PY(gasEq) - 3, class: "tick", "text-anchor": "end" }, svg).textContent = `gas heat ${gasEq.toFixed(1)}p`;
    el("path", { d: pr.map((v, s) => `${s ? "L" : "M"}${X(s)},${PY(v)} L${X(s + 1)},${PY(v)}`).join(" "), class: "ln c4" }, svg);
    // outside temperature strip
    const oc = d.out_c, TY = v => 92 - (v + 6) / 22 * 34;
    el("text", { x: 4, y: 68, class: "lab" }, svg).textContent = "Outside °C";
    el("line", { x1: X(0), x2: X(48), y1: TY(0), y2: TY(0), class: "grid" }, svg);
    el("text", { x: X(0) - 6, y: TY(0) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = "0°";
    el("path", { d: oc.map((v, s) => `${s ? "L" : "M"}${X(s + .5)},${TY(v)}`).join(" "), class: "ln hp", "stroke-dasharray": "0" }, svg);
    // controller lanes
    D.lanes.forEach(([c, name, sub], i) => {
      const y = 110 + i * 34;
      el("text", { x: 4, y: y + 12, class: "lab" }, svg).textContent = name;
      el("text", { x: 4, y: y + 25, class: "tick" }, svg).textContent = sub;
      for (let s = 0; s < 48; s++) {
        const f = hpShare(d, c, s), shed = c === "sdp" && d.phi[tar][s] > 0;
        const r = el("rect", { x: X(s) + 1, y: y, width: (W - 160) / 48 - 2, height: 24, rx: 2,
          class: `cell ${f >= 0.5 ? "hp" : "gas"}${shed ? " shed" : ""}`, opacity: s <= slot ? 1 : 0.18 }, svg);
        el("title", {}, r).textContent = `${name} ${fmtT(s)}: ${f >= 0.5 ? "heat pump" : "boiler"}${f > 0.02 && f < 0.98 ? ` (${Math.round(f * 100)}% heat pump)` : ""}; price ${pr[s].toFixed(1)}p, COP ${d.cop[s].toFixed(2)}${shed ? `; GB shed share ${Math.round(d.phi[tar][s] * 100)}%` : ""}`;
      }
    });
    // GB system demand
    if (d.gb) {
      const g = d.gb[tar], base = g.base_gw, cc = base.map((b, s) => b + g.ccop_gw[s]), sd = base.map((b, s) => b + g.sdp_gw[s]);
      const top = Math.max(...cc, ...sd, 60) * 1.05, GY = v => 330 - v / top * 112;
      el("text", { x: 4, y: 226, class: "lab" }, svg).textContent = "Britain, GW";
      [0, 50, 100].filter(v => v < top).forEach(v => { el("line", { x1: X(0), x2: X(48), y1: GY(v), y2: GY(v), class: "grid" }, svg);
        el("text", { x: X(0) - 6, y: GY(v) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = v; });
      el("path", { d: base.map((v, s) => `${s ? "L" : "M"}${X(s + .5)},${GY(v)}`).join(" ") + ` L${X(47.5)},${GY(0)} L${X(.5)},${GY(0)} Z`, class: "band base" }, svg);
      const capv = Math.max(...sd);
      el("line", { x1: X(0), x2: X(48), y1: GY(capv), y2: GY(capv), class: "ref" }, svg);
      el("text", { x: X(48) - 2, y: GY(capv) - 4, class: "tick", "text-anchor": "end" }, svg).textContent = `SD-Power cap ${capv.toFixed(0)} GW`;
      const upto = a => a.slice(0, slot + 1).map((v, s) => `${s ? "L" : "M"}${X(s + .5)},${GY(v)}`).join(" ");
      el("path", { d: upto(cc), class: "ln hyb" }, svg);
      el("path", { d: upto(sd), class: "ln c4" }, svg);
      const lc = el("text", { x: X(Math.min(slot, 40)) + 6, y: GY(cc[slot]) - 6, class: "dl" }, svg); lc.textContent = "every home on C-COP";
      const ls = el("text", { x: X(Math.min(slot, 40)) + 6, y: GY(sd[slot]) + 14, class: "dl" }, svg); ls.textContent = "SD-Power";
      el("text", { x: 4, y: 245, class: "tick" }, svg).textContent = "national demand";
      el("text", { x: 4, y: 258, class: "tick" }, svg).textContent = "+ every gas home";
    }
    el("line", { x1: X(slot + 1), x2: X(slot + 1), y1: 8, y2: 334, class: "head" }, svg);
    [0, 12, 24, 36, 48].forEach(s => el("text", { x: X(s), y: 348, class: "tick", "text-anchor": "middle" }, svg).textContent = s === 48 ? "24:00" : fmtT(s));
    readout(d);
  }
  function sums(d, c, upto) { let p = 0, kg = 0; for (let s = 0; s <= upto; s++) { const e = d.elec_kwh[tar][c][s], h = d.heat_kwh[s], gh = Math.max(0, h - e * d.cop[s]);
      p += e * d.price_p[tar][s] + gh / 0.9 * D.gas_p; kg += e * d.carb_g[s] / 1000 + gh / 0.9 * D.gas_kg; } return [p, kg]; }
  function readout(d) {
    $("td-when").textContent = `${nice(d.date)}, ${fmtT(slot)}, weather of ${d.date.slice(0, 4)}, priced on ${nice(d.price_date).replace(/^\w+ /, "")}`;
    $("td-totals").innerHTML = D.lanes.map(([c, name]) => { const [p, kg] = sums(d, c, slot);
      return `<div><b>${name}</b><span>£${(p / 100).toFixed(2)}</span><span>${kg.toFixed(1)} kg CO₂</span></div>`; }).join("");
    $("td-say").textContent = caption(d);
  }
  function caption(d) {
    const s = slot, pr = d.price_p[tar][s], f = c => hpShare(d, c, s), was = c => s ? hpShare(d, c, s - 1) : f(c), phi = d.phi[tar][s];
    if (d.gb && phi > 0 && (!s || d.phi[tar][s - 1] === 0)) { const g = d.gb[tar]; return `Britain would reach ${(g.base_gw[s] + g.ccop_gw[s]).toFixed(0)} GW if every gas home ran C-COP. SD-Power asks ${Math.round(phi * 100)}% of homes to use their boiler for this half-hour${f("sdp") < 0.5 && f("ccop") >= 0.5 ? "; this house is one of them" : ""}.`; }
    if (pr < 0 && (!s || d.price_p[tar][s - 1] >= 0)) return `The price goes negative (${pr.toFixed(1)}p). Every price-aware controller runs the heat pump; the fixed switch ${f("biv0") >= 0.5 ? "does too" : "keeps burning gas because it is below 0 °C"}.`;
    if (was("ccop") >= 0.5 && f("ccop") < 0.5) return `At ${pr.toFixed(1)}p and a COP of ${d.cop[s].toFixed(2)}, the boiler's heat is cheaper. C-COP hands over.`;
    if (was("ccop") < 0.5 && f("ccop") >= 0.5) return `The heat pump is cheaper again (${pr.toFixed(1)}p ÷ COP ${d.cop[s].toFixed(2)} < gas ${(D.gas_p / 0.9).toFixed(1)}p). C-COP switches back.`;
    if (f("biv0") < 0.5 && f("ccop") >= 0.5 && was("biv0") >= 0.5) return `${d.out_c[s].toFixed(1)} °C outside. The fixed switch goes to gas, although the heat pump is cheaper right now.`;
    return $("td-say").textContent || "Press play, or drag through the day. Blue: heat pump. Green: boiler. Hatched: SD-Power has asked homes to switch.";
  }
  function controls() {
    seg("td-days", D.order.map(k => [k, new Date(D.days[k].date + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })]), day, k => { day = k; slot = 0; controls(); draw(); });
    seg("td-tar", TAR, tar, k => { tar = k; controls(); draw(); });
    $("td-play").textContent = playing ? "Pause" : "Play";
  }
  $("td-play").onclick = () => { playing = !playing; controls(); };
  $("td-scrub").oninput = e => { slot = +e.target.value; playing = false; controls(); draw(); };
  function frame(ts) { requestAnimationFrame(frame); const dt = Math.min(0.1, (ts - (last || ts)) / 1000); last = ts; if (!playing) return;
    if (hold > 0) { hold -= dt; if (hold <= 0) { const i = D.order.indexOf(day); day = D.order[(i + 1) % D.order.length]; slot = 0; controls(); draw(); } return; }
    acc += dt * 4; while (acc >= 1) { acc -= 1; if (slot < 47) { slot++; $("td-scrub").value = slot; draw(); } else { hold = 4; break; } } }
  controls(); draw(); requestAnimationFrame(frame);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
})();
"""

CSS = """
.td { background: var(--panel); border: 1px solid var(--rule); border-radius: 12px; padding: 14px; font-family: var(--f-sans) }
.td .bar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; margin-bottom: 8px }
.td .seg button, .td #td-play { font: 500 13px var(--f-sans); padding: 5px 10px; border: 1px solid var(--rule); background: var(--bg); color: var(--ink-2); border-radius: 6px; cursor: pointer; margin-right: 4px }
.td .seg button[aria-pressed="true"], .td #td-play { border-color: var(--forest); color: var(--forest); font-weight: 600 }
.td #td-scrub { flex: 1; min-width: 160px; accent-color: var(--forest) }
.td #td-when { font-size: 13px; color: var(--ink-3) }
.td #td-say { min-height: 44px; font-size: 15px; color: var(--ink); background: var(--bg); border-left: 3px solid var(--gold); padding: 8px 12px; margin: 8px 0 }
.td svg { width: 100%; height: auto; display: block }
.td .cell.hp { fill: var(--hp) } .td .cell.gas { fill: var(--gas) } .td .cell.shed { stroke: var(--gold); stroke-width: 2 }
.td .ref { stroke: var(--ink-3); stroke-dasharray: 4 4 } .td .head { stroke: var(--ink); stroke-width: 1 } .td .band.base { fill: var(--sage); opacity: .5; stroke: none }
.td #td-totals { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; font-size: 13px }
.td #td-totals div { border: 1px solid var(--rule); border-radius: 8px; padding: 6px 10px; display: flex; flex-direction: column }
.td #td-totals span { font-family: var(--f-mono); color: var(--ink-2) }
.printonly { display: none }
@media print { .td.noprint { display: none } .printonly { display: block } }
"""


def static_svg(data):
    """Print version: for each day, the three lanes on Agile as coloured strips, and the day's totals."""
    rows = []
    y = 10
    for k in ORDER:
        d = data["days"][k]
        rows.append(f'<text x="4" y="{y + 12}" class="lab">{d["date"]} (weather) · Agile</text>')
        y += 20
        for c, name, _ in LANES:
            rows.append(f'<text x="4" y="{y + 12}" class="tick">{name}</text>')
            for s in range(48):
                h = d["heat_kwh"][s]
                f = min(1, d["elec_kwh"]["agile"][c][s] * d["cop"][s] / h) if h > 1e-6 else 1
                cls = "hp" if f >= 0.5 else "gas"
                rows.append(f'<rect x="{130 + s * 10}" y="{y}" width="9" height="14" class="bar {cls}"/>')
            rows.append(f'<text x="{620}" y="{y + 11}" class="tick">£{d["day_cost_p"]["agile"][c] / 100:.2f} · {d["day_kg"]["agile"][c]:.1f} kg</text>')
            y += 18
        y += 10
    return f'<svg viewBox="0 0 740 {y}" role="img" aria-label="Heat source by half-hour on three days">' + "".join(rows) + "</svg>"


if __name__ == "__main__":
    data = compact()
    blob = json.dumps(data, separators=(",", ":"))
    html = f"""<figure id="fig-three_days" class="fig">
<style>{CSS}</style>
<div class="td noprint" aria-label="Interactive: three days in the life of an SD-Power hybrid">
  <div class="bar"><span class="seg" id="td-days"></span><span class="seg" id="td-tar"></span><button type="button" id="td-play">Pause</button>
    <input type="range" id="td-scrub" min="0" max="47" value="0" aria-label="Time of day"></div>
  <div id="td-when"></div><div id="td-say" aria-live="polite"></div>
  <svg id="td-svg" viewBox="0 0 760 354" role="img" aria-label="Price, outside temperature, heat source per controller, and Britain's demand, by half-hour"></svg>
  <div id="td-totals"></div>
</div>
<div class="printonly">{static_svg(data)}</div>
<script type="application/json" id="td-data">{blob}</script>
<script>{JS}</script>
<figcaption><b>Figure 3.</b> Three days in the life of an SD-Power hybrid. The monitored house, run as a hybrid with its old boiler, through
three real days of the winter of 2010–11, priced on the same calendar days of 2025–26. The days were chosen by rule: the
day SD-Power sheds most of Britain's heat-pump demand, the coldest day in Poole, and the heating-season day with the most
negative Agile prices. Blue: heat pump; green: boiler; gold outline: SD-Power is asking a share of homes to switch, and
this house switches when its own random draw falls in that share. Bottom: Britain's demand if every gas home ran C-COP
alone, and under SD-Power. Change the tariff to compare.</figcaption>
</figure>
"""
    FIG.write_text(html)
    print(f"wrote {FIG.relative_to(ROOT)} ({len(html) // 1024} KB)")
