#!/usr/bin/env python3
"""Claims ledger for LDS Public Class No. 1: every sentence that states a number or cites a source, with its backing.

    .venv/bin/python scripts/article/ledger.py

For each sentence of docs/article/sd_power_hybrid/chapters/*.md:
  numbers    each __NAME__ slot, its value (docs/article/numbers.json) and where it comes from (numbers_meta.json)
  citations  each [@Key]: the Harvard reference and the quotes the review agent recorded from the source
             (docs/article/sources.json -- every source was fetched and read)
  FLAG       a digit typed into the prose that is neither a number slot nor inside a citation: a reviewer should
             check it first (literature figures are usually fine if the sentence also cites their source)
Writes docs/article/sd_power_hybrid/build/claims.csv and claims.html.
"""
import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "article"
CH = ART / "sd_power_hybrid" / "chapters"
OUT = ART / "sd_power_hybrid" / "build"
NUMS = json.load(open(ART / "numbers.json"))
META = json.load(open(ART / "numbers_meta.json"))
SRC = json.load(open(ART / "sources.json"))
REF_WORDS = (r"(Section|Sections|Figure|Figures|Table|RQ|H)\s*\d+(\.\d+)?|\b\d+\.\d+\b(?=\s+[A-Z])|^#+.*"
             r"|\b(19|20)\d\d(–\d\d)?\b|\b\d{1,2}:\d\d\b"                                          # years, clock times
             r"|\b\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December)\b"
             r"|^\d+\.$|\[[^\]]*\]\(#[^)]*\)|\b\d+-metre\b")                                     # list numerals, toc links
MODEL_INPUT = re.compile(r"^\|.*\|$|q_space|COP\(t\)|clipped to|uniform|log-normal|weather compensation|reheats|"
                         r"Hot water is made|capacity|COP 1|gains profile|Fixed bivalent|peak off|Intelligent Octopus Go")


def short(key):
    h = SRC["sources"][key]["harvard"]
    m = re.match(r"^(.*?)\s*\((\d{4}[a-z]?|n\.d\.)\)", h)
    if not m:
        return key
    names = re.findall(r"([A-Z][A-Za-z'\-]+), (?:[A-Z]\.\s?-?)+", m.group(1))
    a = names[0] + (" et al." if len(names) > 2 else f" and {names[1]}" if len(names) == 2 else "") if names else m.group(1)
    return f"{a} {m.group(2)}"


def sentences(text):
    text = re.sub(r"\{\{fig:[a-z0-9_]+\}\}", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\n(?=[-*>|#]|\d+\.\s)", "\n\n", text)
    out = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para or set(para) <= set("|-: "):
            continue
        out += [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(\[*])", para) if s.strip()]
    return out


def main():
    rows = []
    for ch in sorted(CH.glob("*.md")):
        for s in sentences(ch.read_text()):
            slots = re.findall(r"__([A-Z][A-Z0-9_]+)__", s)
            cites = []
            for grp in re.findall(r"\[(@[^\]]+)\]", s):
                for p in grp.split(";"):
                    m = re.match(r"\s*@([A-Za-z0-9_\-]+)(?:,\s*(.+))?", p)
                    if m:
                        cites.append((SRC["aliases"].get(m.group(1), m.group(1)), (m.group(2) or "").strip()))
            bare = re.sub(r"__[A-Z0-9_]+__|\[@[^\]]+\]", " ", s)
            bare = re.sub(REF_WORDS, " ", bare)
            typed = re.findall(r"(?<![A-Za-z_])\d[\d,.]*", bare)
            if not slots and not cites and not typed:
                continue
            filled = re.sub(r"__([A-Z][A-Z0-9_]+)__", lambda m: str(NUMS.get(m.group(1), f"[[{m.group(1)}]]")), s)
            filled = re.sub(r"\[(@[^\]]+)\]", lambda m: "(" + "; ".join(short(SRC["aliases"].get(k, k)) for k in
                            re.findall(r"@([A-Za-z0-9_\-]+)", m.group(1)) if SRC["aliases"].get(k, k) in SRC["sources"]) + ")", filled)
            numbers = [{"name": n, "value": NUMS.get(n, "NOT YET COMPUTED"), "source": META.get(n, "?")} for n in slots]
            refs = []
            for k, loc in cites:
                src = SRC["sources"].get(k)
                if not src:
                    refs.append({"key": k, "ref": "MISSING FROM REGISTER", "quotes": []})
                    continue
                refs.append({"key": k, "ref": src["harvard"], "locator": loc,
                             "quotes": [f"\"{c['quote']}\" ({c.get('locator', '')})" for c in src.get("claims", [])[:3]]})
            if typed and not cites and ch.stem.startswith("04") and MODEL_INPUT.search(s):
                flag = "model input (stated design choice; see the published code)"
            else:
                flag = "typed number, no slot or citation" if typed and not cites else ("typed number, cited sentence" if typed else "")
            rows.append({"chapter": ch.stem, "sentence": filled, "numbers": numbers, "citations": refs, "typed": typed,
                         "flag": flag})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "claims.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "chapter", "sentence", "numbers (name=value; source)", "citations (key; locator)", "typed digits", "flag"])
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["chapter"], r["sentence"], " | ".join(f"{n['name']}={n['value']}; {n['source']}" for n in r["numbers"]),
                        " | ".join(f"{c['key']}; {c.get('locator', '')}" for c in r["citations"]), " ".join(r["typed"]), r["flag"]])
    page(rows)
    nf = sum(1 for r in rows if r["flag"].startswith("typed number, no"))
    print(f"{len(rows)} claims ({sum(bool(r['numbers']) for r in rows)} with model numbers, "
          f"{sum(bool(r['citations']) for r in rows)} cited); {nf} flagged for review -> build/claims.csv, claims.html")


def page(rows):
    e = html.escape
    tr = []
    for i, r in enumerate(rows, 1):
        nums = "".join(f"<li><code>{e(n['name'])}</code> = <b>{e(str(n['value']))}</b><br><small>{e(n['source'])}</small></li>" for n in r["numbers"])
        cits = "".join(f"<li><b>{e(c['key'])}</b>{(' · ' + e(c.get('locator', ''))) if c.get('locator') else ''}<br><small>{e(c['ref'])}</small>"
                       + "".join(f"<blockquote>{e(q)}</blockquote>" for q in c["quotes"]) + "</li>" for c in r["citations"])
        cls = "flag" if r["flag"].startswith("typed number, no") else ""
        tr.append(f'<tr class="{cls}"><td>{i}</td><td><small>{e(r["chapter"])}</small><br>{e(r["sentence"])}'
                  f'{f"<div class=f>⚑ {e(r[chr(102) + chr(108) + chr(97) + chr(103)])}: {e(" ".join(r["typed"]))}</div>" if r["flag"] else ""}</td>'
                  f'<td><ul>{nums}</ul></td><td><ul>{cits}</ul></td></tr>')
    (OUT / "claims.html").write_text(f"""<title>Claims Ledger</title>
<style>
:root {{ --bg:#fbfaf6; --ink:#1c211e; --ink2:#55605A; --rule:#dfe3dc; --flag:#fff1c7; --acc:#1F4D3C }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#121614; --ink:#edf0eb; --ink2:#a9b3ab; --rule:#2e3530; --flag:#4a3d12; --acc:#8fc4a9; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#121614; --ink:#edf0eb; --ink2:#a9b3ab; --rule:#2e3530; --flag:#4a3d12; --acc:#8fc4a9; color-scheme:dark }}
body {{ background:var(--bg); color:var(--ink); font:14px/1.5 "IBM Plex Sans",system-ui,sans-serif; padding-block:24px; padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)) }}
h1 {{ color:var(--acc); margin:0 0 6px }} p {{ max-width:70ch; color:var(--ink2) }}
.box {{ overflow-x:auto }} table {{ border-collapse:collapse; width:100%; min-width:900px }}
td,th {{ border-bottom:1px solid var(--rule); padding:8px; vertical-align:top; text-align:left }} th {{ font-size:12px; color:var(--ink2) }}
tr.flag td {{ background:var(--flag) }} ul {{ margin:0; padding-left:16px }} li {{ margin-bottom:6px }} small {{ color:var(--ink2) }}
blockquote {{ margin:4px 0 0; padding-left:8px; border-left:2px solid var(--rule); font-style:italic; color:var(--ink2) }}
.f {{ margin-top:4px; font-weight:600 }} label {{ display:inline-flex; gap:6px; align-items:center; margin:8px 0 }}
</style>
<h1>Claims ledger</h1>
<p>Every sentence of the draft that states a number or cites a source, with what backs it: model numbers with the
file they come from, and citations with the quotes recorded from the source when it was read. Highlighted rows hold a
number typed into the prose with no slot and no citation; check those first.</p>
<label><input type="checkbox" id="only"> Show flagged rows only</label>
<div class="box"><table><thead><tr><th>#</th><th>Claim</th><th>Model numbers</th><th>Sources</th></tr></thead><tbody>
{"".join(tr)}</tbody></table></div>
<script>document.getElementById("only").onchange = e => document.querySelectorAll("tbody tr").forEach(r => r.hidden = e.target.checked && !r.classList.contains("flag"));</script>
""")


if __name__ == "__main__":
    main()
