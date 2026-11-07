#!/usr/bin/env python3
"""Build LDS Public Class No. 1 from its chapters.

    .venv/bin/python scripts/article/build.py [--draft]

Chapters: docs/article/sd_power_hybrid/chapters/NN_*.md, in file-name order. Markdown, plus:
  __NAME__            a number from docs/article/numbers.json (written by scripts/article/article_numbers.py); a missing
                      or unused-but-referenced name FAILS the build -- no number is typed into the prose
  [@Key]              citation, Harvard (Author Year); [@Key, p. 5] with a locator; [@A; @B] several.
                      Key must exist in docs/article/sources.json (fetched + quoted sources only) -- else FAIL
  {{fig:name}}        a figure from docs/article/sd_power_hybrid/figures/name.html (inline SVG + caption)
Writes docs/article/sd_power_hybrid/build/index.html (web) and, with the print CSS, the PDF source.
"""
import json
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "article" / "sd_power_hybrid"
SRC = json.load(open(ROOT / "docs" / "article" / "sources.json"))
NUMS_P = ROOT / "docs" / "article" / "numbers.json"
NUMS = json.load(open(NUMS_P)) if NUMS_P.exists() else {}
DRAFT = "--draft" in sys.argv          # draft: unfilled numbers render as [[NAME]] instead of failing
# --omit A,B: treat these numbers as not yet computed (e.g. run totals while the 86-year run is still going)
for _k in (sys.argv[sys.argv.index("--omit") + 1].split(",") if "--omit" in sys.argv else []):
    NUMS.pop(_k, None)
OUTNAME = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "index.html"
SHORT = {  # organisation authors whose Harvard string is too long for an in-text citation
    "FREEDOM2018": "WPD and WWU",
}
errors = []


def short(key):
    s = SRC["sources"][key]
    h = s["harvard"]
    m = re.match(r"^(.*?)\s*\((\d{4}[a-z]?|n\.d\.)\)", h)
    if not m:
        errors.append(f"cannot parse Harvard string for {key}")
        return key, ""
    authors, year = m.group(1).strip().rstrip(","), m.group(2)
    if key in SHORT:
        return SHORT[key], year
    names = re.findall(r"([A-Z][A-Za-z'\-]+(?: [a-z]+ [A-Z][A-Za-z'\-]+)?), (?:[A-Z]\.\s?-?)+", authors)
    if names:
        if len(names) == 1:
            return names[0], year
        if len(names) == 2:
            return f"{names[0]} and {names[1]}", year
        return f"{names[0]} et al.", year
    if " et al" in authors:
        return authors.split(",")[0].split(" et al")[0] + " et al.", year
    return authors, year


def cite(m):
    parts, out = [p.strip() for p in m.group(1).split(";")], []
    for p in parts:
        mm = re.match(r"@([A-Za-z0-9_\-]+)(?:,\s*(.+))?$", p)
        if not mm:
            errors.append(f"bad citation [{m.group(1)}]")
            continue
        k = SRC["aliases"].get(mm.group(1), mm.group(1))
        if k not in SRC["sources"]:
            errors.append(f"unknown citation key @{mm.group(1)} (not in sources.json)")
            continue
        CITED.add(k)
        a, y = short(k)
        out.append(f'<a href="#ref-{k}">{a} {y}</a>' + (f", {mm.group(2)}" if mm.group(2) else ""))
    return "(" + "; ".join(out) + ")"


def number(m):
    k = m.group(1)
    if k in NUMS:
        USED.add(k)
        return str(NUMS[k])
    if DRAFT:
        return f'<mark class="slot">[[{k}]]</mark>'
    errors.append(f"number __{k}__ not in numbers.json")
    return m.group(0)


def figure(m):
    p = ART / "figures" / f"{m.group(1)}.html"
    if p.exists():
        return p.read_text()
    if DRAFT:
        return f'<figure class="pending"><figcaption>[Figure pending: {m.group(1)}]</figcaption></figure>'
    errors.append(f"figure {m.group(1)} missing")
    return ""


CITED, USED = set(), set()
body = []
for ch in sorted((ART / "chapters").glob("*.md")):
    t = ch.read_text()
    t = re.sub(r"__([A-Z][A-Z0-9_]+)__", number, t)
    t = re.sub(r"\[(@[^\]]+)\]", cite, t)
    t = re.sub(r"\{\{fig:([a-z0-9_]+)\}\}", figure, t)
    body.append(markdown.markdown(t, extensions=["tables", "footnotes", "attr_list", "md_in_html", "toc"]))
refs = sorted(CITED, key=lambda k: SRC["sources"][k]["harvard"].lower())
ref_html = "\n".join(f'<li id="ref-{k}">{SRC["sources"][k]["harvard"]}</li>' for k in refs)
if errors:
    sys.exit("BUILD FAILED:\n  " + "\n  ".join(sorted(set(errors))))
tpl = (ART / "template.html").read_text()
html = tpl.replace("<!--BODY-->", "\n".join(body)).replace("<!--REFERENCES-->", ref_html)
out = ART / "build"
out.mkdir(exist_ok=True)
(out / OUTNAME).write_text(html)
prose = re.sub(r"<(script|style)[^>]*>.*?</\1>|<figure.*?</figure>", " ", "\n".join(body), flags=re.S)
words = len(re.sub(r"<[^>]+>", " ", prose).split())
print(f"built {out / OUTNAME}: {words:,} words, {len(refs)} references, {len(USED)} numbers"
      + (" (DRAFT)" if DRAFT else ""))
