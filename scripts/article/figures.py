#!/usr/bin/env python3
"""Figures for LDS Public Class No. 1 -> docs/article/sd_power_hybrid/figures/<name>.html (one <figure> each).

Inline SVG drawn against the article's CSS roles (--fig-hp, --fig-hyb, --fig-gas, --fig-4, --ink-*, --rule) so
light/dark and print follow the page. Every mark carries a <title> (native hover tooltip); every figure with data
has a visually hidden table view; series <= 4 are direct-labelled. Palette validated with the dataviz skill's
validate_palette.js (light + dark PASS; gas contrast WARN -> direct labels + table view).
    .venv/bin/python scripts/article/figures.py [name ...]
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "docs" / "article" / "sd_power_hybrid" / "figures"
NUMS_P = ROOT / "docs" / "article" / "numbers.json"


class Plot:
    """Minimal x/y SVG plot: linear axes, recessive grid, thin marks."""

    def __init__(self, w=680, h=360, x=(0, 1), y=(0, 1), m=(16, 20, 44, 56)):
        self.w, self.h, (self.x0, self.x1), (self.y0, self.y1) = w, h, x, y
        self.mt, self.mr, self.mb, self.ml = m
        self.parts = []

    def X(self, v):
        return self.ml + (v - self.x0) / (self.x1 - self.x0) * (self.w - self.ml - self.mr)

    def Y(self, v):
        return self.h - self.mb - (v - self.y0) / (self.y1 - self.y0) * (self.h - self.mt - self.mb)

    def axes(self, xt, yt, xl, yl, xfmt="{:g}", yfmt="{:g}"):
        p = self.parts
        for v in yt:
            p.append(f'<line x1="{self.ml}" x2="{self.w - self.mr}" y1="{self.Y(v):.1f}" y2="{self.Y(v):.1f}" class="grid"/>')
            p.append(f'<text x="{self.ml - 8}" y="{self.Y(v) + 4:.1f}" class="tick" text-anchor="end">{yfmt.format(v)}</text>')
        for v in xt:
            p.append(f'<text x="{self.X(v):.1f}" y="{self.h - self.mb + 18}" class="tick" text-anchor="middle">{xfmt.format(v)}</text>')
        p.append(f'<line x1="{self.ml}" x2="{self.w - self.mr}" y1="{self.h - self.mb}" y2="{self.h - self.mb}" class="axis"/>')
        p.append(f'<text x="{(self.ml + self.w - self.mr) / 2:.1f}" y="{self.h - 6}" class="lab" text-anchor="middle">{xl}</text>')
        p.append(f'<text x="14" y="{self.mt + (self.h - self.mt - self.mb) / 2:.1f}" class="lab" text-anchor="middle" '
                 f'transform="rotate(-90 14 {self.mt + (self.h - self.mt - self.mb) / 2:.1f})">{yl}</text>')

    def line(self, pts, cls, title=""):
        d = " ".join(f"{'M' if i == 0 else 'L'}{self.X(a):.1f},{self.Y(b):.1f}" for i, (a, b) in enumerate(pts))
        self.parts.append(f'<path d="{d}" class="ln {cls}"><title>{escape(title)}</title></path>')

    def band(self, lo, hi, cls, title=""):
        d = " ".join(f"{'M' if i == 0 else 'L'}{self.X(a):.1f},{self.Y(b):.1f}" for i, (a, b) in enumerate(lo))
        d += " " + " ".join(f"L{self.X(a):.1f},{self.Y(b):.1f}" for a, b in reversed(hi)) + " Z"
        self.parts.append(f'<path d="{d}" class="band {cls}"><title>{escape(title)}</title></path>')

    def dot(self, a, b, cls, r=5, title=""):
        self.parts.append(f'<circle cx="{self.X(a):.1f}" cy="{self.Y(b):.1f}" r="{r}" class="dot {cls}"><title>{escape(title)}</title></circle>')

    def label(self, a, b, text, cls="dl", anchor="start", dx=6, dy=4):
        self.parts.append(f'<text x="{self.X(a) + dx:.1f}" y="{self.Y(b) + dy:.1f}" class="{cls}" text-anchor="{anchor}">{escape(text)}</text>')

    def svg(self, aria):
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(aria)}">'
                + "".join(self.parts) + "</svg>")


def table(head, rows):
    h = "".join(f"<th>{escape(str(x))}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in r) + "</tr>" for r in rows)
    return f'<details class="tview"><summary>Data table</summary><div class="tablebox"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div></details>'


def figure(name, n, caption, body):
    (FIG / f"{name}.html").write_text(f'<figure id="fig-{name}" class="fig">{body}<figcaption><b>Figure {n}.</b> {caption}</figcaption></figure>\n')
    print(f"wrote figures/{name}.html")


def pipeline():
    steps = [("Weather", "ERA5 hourly temperature, 79 towns, every heating year 1940–41 to 2025–26"),
             ("Prices &amp; carbon", "2025–26 actual half-hourly Agile, Cosy and regional grid carbon, by calendar day"),
             ("Homes", "32,000 sampled homes per town, MCS-sized; one monitored house"),
             ("Physics", "Half-hourly heat demand, COP from measured systems, unit capacity"),
             ("Controllers", "Fixed bivalent · C-COP · carbon-aware · SD-Power dispatch"),
             ("Outcomes", "Yearly bill per home · CO₂ (average &amp; marginal) · GB evening peak")]
    cells = "".join(f'<div class="step"><span class="n">{i + 1}</span><b>{t}</b><span>{d}</span></div>' for i, (t, d) in enumerate(steps))
    figure("pipeline", 1, "The model. Each heating year runs every town, home, tariff and controller on a single DGX Spark; "
           "every number in this paper is generated from its outputs.", f'<div class="pipe">{cells}</div>')


def share_fit():
    j = json.load(open(ROOT / "logs" / "hpm_shares_20261106.json"))
    mids = {"-10..0": -3.0, "0..3": 1.5, "3..6": 4.5, "6..9": 7.5, "9..12": 10.5, "12..16": 14.0}
    fleet = [(mids[k], v["share"], v["days"]) for k, v in j["bands"].items()]
    house = [(1.5, 0.353), (4.5, 0.335), (7.5, 0.313), (11.0, 0.250), (14.0, 0.205)]
    lo = 0.816                                  # physics.STOCK_LEVEL[0], recalibrated 9 Nov 2026 (Section 4.4)
    P = Plot(x=(-4, 16), y=(0.15, 0.40))
    P.axes(range(-4, 17, 4), [0.15, 0.20, 0.25, 0.30, 0.35, 0.40], "Outdoor temperature (°C)", "Share of Carnot COP",
           yfmt="{:.2f}")
    P.band([(t, s * lo) for t, s, _ in fleet], [(t, s) for t, s, _ in fleet], "hyb",
           "Housing stock: each home drawn between the field-trial level (x0.816) and the tuned fleet (x1.0)")
    P.line([(t, s) for t, s, _ in fleet], "hyb", "Fitted share, 55 GB systems")
    for t, s, d in fleet:
        P.dot(t, s, "hyb", r=4 + min(d, 3600) ** 0.5 / 12, title=f"{t:g} °C band: share {s:.3f} from {d:,} system-days")
    P.line(house, "hp", "Monitored house, measured")
    for t, s in house:
        P.dot(t, s, "hp", r=4, title=f"Monitored house {t:g} °C: {s:.3f}")
    P.label(14, 0.3124, "55 tuned systems (heatpumpmonitor.org)", anchor="end", dx=-10, dy=-12)
    P.label(14, 0.205, "monitored house", anchor="end", dx=-10, dy=-6)
    P.label(-3, 0.3415 * lo, "stock range, down to the field-trial level", dy=-8)
    rows = [(f"{t:g}", f"{s:.3f}", f"{s * lo:.3f}", f"{d:,}") for t, s, d in fleet]
    figure("share_fit", 2, "Heat-pump efficiency as a share of the ideal (Carnot) COP. Dots: 55 British air-source systems "
           "on heatpumpmonitor.org that report space heating separately, sized by system-days in each temperature band. "
           "The shaded band is the range the sampled homes are drawn from, between the tuned fleet and the national "
           "field-trial median. Line with small dots: the monitored house, which cycles in mild weather.",
           P.svg("Carnot share against outdoor temperature") + table(
               ["Band midpoint °C", "Fleet share", "Field-trial level", "System-days"], rows))


def eoh_profiles():
    """Figure 3: the trial's measured cold-day profile against the model's, same nine days (validation_eoh.py)."""
    v = json.load(open(ROOT / "docs" / "article" / "results" / "diversity" / "eoh_validation.json"))
    meas, base, eoh = v["measured"]["profile_kw_mean"], v["model"]["base"]["profile_kw_mean"], v["model"]["eoh"]["profile_kw_mean"]
    xs = [i / 2 + 0.25 for i in range(48)]
    P = Plot(x=(0, 24), y=(0, 3))
    P.axes(range(0, 25, 6), [0, 0.5, 1, 1.5, 2, 2.5, 3], "Hour of day", "Electricity per home (kW)", xfmt="{:02d}:00", yfmt="{:.1f}")
    P.line(list(zip(xs, base)), "hp", "Model, main runs: all-electric homes, set point held all day")
    P.line(list(zip(xs, eoh)), "hyb", "Model with the trial's measured heating habits")
    P.line(list(zip(xs, meas)), "gas", f"Measured: {v['measured']['homes']} trial homes, whole-system electricity")
    for i in (0, 12, 24, 36, 47):
        P.dot(xs[i], meas[i], "gas", r=3, title=f"Measured {i // 2:02d}:{30 * (i % 2):02d}: {meas[i]:.2f} kW")
    P.label(xs[base.index(max(base))], max(base), "model, main runs", dy=-8)
    P.label(23.5, eoh[46], "model, measured habits", anchor="end", dy=-8)
    P.label(23.5, meas[46], "measured", anchor="end", dy=14)
    n = v["numbers"]
    rows = [(f"{i // 2:02d}:{30 * (i % 2):02d}", f"{meas[i]:.2f}", f"{base[i]:.2f}", f"{eoh[i]:.2f}") for i in range(0, 48, 2)]
    figure("eoh_profiles", 3, f"Coincident electricity per home on the trial's nine coldest days of winter 2022–23 "
           f"(mean outdoor temperature {n['REV_V_MEAS_TEMP_C']} °C), averaged over the days. Measured: the {n['REV_V_MEAS_HOMES']} "
           f"non-hybrid homes of the Electrification of Heat trial with complete data on every day. Model: 4,000 all-electric "
           f"homes in each of {n['REV_V_TOWNS']} on the same dates, without and with the trial's heating habits. Shape "
           f"correlation {n['REV_V_BASE_SHAPE_R']} and {n['REV_V_EOH_SHAPE_R']}; peaks at {n['REV_V_MEAS_PEAK_HH']} measured, "
           f"{n['REV_V_BASE_PEAK_HH']} and {n['REV_V_EOH_PEAK_HH']} modelled.",
           P.svg("Measured and modelled cold-day electricity per home by hour") + table(
               ["Hour", "Measured kW", "Model kW", "Model with habits kW"], rows))


ALL = {"pipeline": pipeline, "share_fit": share_fit, "eoh_profiles": eoh_profiles}
if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    for n in (sys.argv[1:] or ALL):
        ALL[n]()
