#!/usr/bin/env python3
"""A4 PDF of LDS Public Class No. 1, rendered on the DGX Spark (review, 9 Nov 2026: "fix A4
pagination, text rendering, page numbers, figures, captions and links before circulating"; version 1.0, 11 Nov 2026).

1. Print source from the STRICT build (docs/article/sd_power_hybrid/build/index.html: every number filled, or the
   build fails), with: static TrueType fonts in place of Google's variable web fonts (Chrome embeds variable fonts as
   Type 3 glyph drawings; static ones embed as real TrueType subsets); the abstract kept on the title page; a version
   notice on page 1 and a running version header on every later page.
2. Rendered by headless Chromium in a throwaway node:22-alpine container on the Spark (the Azure box is too small,
   and has no browser), A4 from the template's print stylesheet, page numbers in the footer.
3. Metadata to the LDS file rules: Author "LDS Consulting Limited", no generator, producer, title, subject or
   keywords, real creation and modification dates.
Writes docs/article/sd_power_hybrid/build/paper_draft.pdf.
    .venv/bin/python scripts/article/make_pdf.py
"""
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "docs" / "article" / "sd_power_hybrid" / "build"
SPARK = "<your-gpu-host>:<path>
WORK = "pdfwork"                                                    # ~/pdfwork on the Spark (fonts/ cached there)
FONTS = ("https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400"
         "&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500")

PRINT_CSS = """<link rel="stylesheet" href="fonts/fonts.css">
<style>
@media print {
  @page { @top-center { content: "LDS Public Class No. 1 \\00B7  version 1.0, 11 November 2026 \\00B7  built %(when)s"; font-family: "IBM Plex Sans", sans-serif;
          font-size: 8.5pt; color: #8a6d24 } }
  @page :first { @top-center { content: none } }
  .abstract h2, .abstract + * h2 { break-before: auto }
  .draft-cover { display: block !important; border: 1.5pt solid #C4993A; color: #1c211e; padding: 6pt 9pt; margin: 0 0 10pt;
                 font: 600 8.5pt/1.35 "IBM Plex Sans", sans-serif }
  svg, img { max-width: 100%% !important; height: auto }
  /* title page: title, abstract, declaration on one page */
  h1 { font-size: 24pt; margin: 4pt 0 2pt } .sub { font-size: 11pt; margin: 0 0 6pt } .byline { margin-bottom: 4pt }
  .abstract { font-size: 9.3pt; line-height: 1.38; padding: 8pt 12pt; margin: 8pt 0 0 } .abstract p { margin: 0 0 5pt }
  .abstract .keywords { font-size: 8pt; line-height: 1.3 }
  /* keep headings and captions with what follows */
  h2, h3, h4, .tcap { break-after: avoid-page; break-inside: avoid }
  h3::after, h4::after, .tcap::after { content: ""; display: block; height: 7em; margin-bottom: -7em }
  h2 + *, h3 + *, h4 + *, .tcap + * { break-before: avoid-page }
  p, li { orphans: 3; widows: 3 }
  p:has(+ .tablebox), p:has(+ figure), p:has(+ .eq) { break-after: avoid-page }
  .tablebox { break-inside: avoid; page-break-inside: avoid; display: block }
  figure, .tablebox, table, tr, .eq, blockquote { break-inside: avoid }
  .tablebox { overflow: visible } details.tview { display: none }
  /* print contents, figures and tables */
  .ptoc { break-before: page; break-after: page; font-family: "IBM Plex Sans", sans-serif; font-size: 9.2pt; line-height: 1.3 }
  .ptoc h2 { break-before: auto; font-size: 16pt; margin: 0 0 8pt } .ptoc h3 { font-size: 11pt; margin: 14pt 0 5pt }
  .ptoc h3::after { content: none }
  .ptoc a { display: flex; align-items: baseline; gap: 5pt; color: inherit; text-decoration: none; padding: 1.3pt 0 }
  .ptoc a .d { flex: 1; border-bottom: .7pt dotted #9aa39d; position: relative; top: -2.5pt; min-width: 12pt }
  .ptoc a .pg { font-variant-numeric: tabular-nums; min-width: 14pt; text-align: right }
  .ptoc .l2 { font-weight: 600; margin-top: 4pt } .ptoc .l3 { padding-left: 16pt; color: #333 }
  .ptoc .x { padding-left: 0 }
}
.draft-cover, .ptoc { display: none }
@media print { .ptoc { display: block } }
</style>"""
COVER = ('<div class="draft-cover">LDS Public Class No. 1, version 1.0 (11 November 2026), DOI 10.5281/zenodo.24133414, '
         'built %(when)s from model v4. '
         'Web version: energy.ldsconsultancy.net/class/. Model, data and results: '
         'github.com/CFLLDS/gb-hybrid-heat-model, release v1.0.0.</div>')

CONTAINER = r"""
set -e
apk add -q --no-progress chromium font-noto py3-pypdf qpdf >/dev/null 2>&1
python3 /w/pdf_paginate.py /w/paper.html /w/raw.pdf
python3 - <<'PY'
from datetime import datetime, timezone
from pypdf import PdfReader, PdfWriter
r = PdfReader("/w/raw.pdf"); w = PdfWriter(clone_from=r)
now = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
w._info = None
w.add_metadata({"/Author": "LDS Consulting Limited", "/CreationDate": now, "/ModDate": now})
for k in ("/Creator", "/Producer", "/Title", "/Subject", "/Keywords"):
    if k in w._info.get_object():
        del w._info.get_object()[k]
w._root_object.pop("/Metadata", None)
w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
w.write("/w/meta.pdf")
print("pages", len(r.pages))
PY
qpdf --object-streams=generate --compress-streams=y --recompress-flate --compression-level=9 /w/meta.pdf /w/paper.pdf
chown %(uid)s /w/paper.pdf
"""


def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h)).strip()


def contents(p):
    """Print-only contents page: sections (h2, h3), figures and tables, each with a page-number slot."""
    def row(i, title, cls):
        return (f'<a class="{cls}" href="#{i}"><span class="t">{html.escape(title)}</span><span class="d"></span>'
                f'<span class="pg" data-id="{i}">00</span></a>')
    rows, outline, h2id = [], [], None
    for lvl, i, t in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>', p, re.S):
        t = strip(t)
        if lvl == "2":
            h2id = i
        rows.append(row(i, t, f"l{lvl}"))
        outline.append({"id": i, "title": t, "parent": h2id if lvl == "3" else None})
    figs = [row(i, strip(c).split(". ", 1)[0] + ". " + strip(c).split(". ", 2)[1] + ".", "x")
            for i, c in re.findall(r'<figure id="([^"]+)"[^>]*>.*?<figcaption>(.*?)</figcaption>', p, re.S)]
    tabs = [row(i, strip(c), "x") for i, c in re.findall(r'<p class="tcap" id="([^"]+)">(.*?)</p>', p, re.S)]
    return ('<section class="ptoc"><h2 class="nobreak">Contents</h2>' + "".join(rows)
            + "<h3>Figures</h3>" + "".join(figs) + "<h3>Tables</h3>" + "".join(tabs) + "</section>"
            + "<!--OUTLINE " + json.dumps(outline) + "-->")


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(f"FAILED: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "article" / "build.py")], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("strict build failed (a number is missing?):\n" + r.stdout + r.stderr)
    when = datetime.now(ZoneInfo("Europe/London")).strftime("%d %B %Y, %H:%M")
    p = (BUILD / "index.html").read_text()
    head_links = [ln for ln in p.split("\n") if "fonts.googleapis.com" in ln or "fonts.gstatic.com" in ln]
    for ln in head_links:                                           # static local fonts instead of the variable web fonts
        p = p.replace(ln + "\n", "")
    p = p.replace("</head>", PRINT_CSS % {"when": when} + "\n</head>", 1)
    i = p.index(">", p.index("<body")) + 1
    p = p[:i] + "\n" + COVER % {"when": when} + p[i:]
    j = p.index('<nav class="toc')
    p = p[:j] + contents(p) + "\n" + p[j:]
    src = BUILD / "paper_print.html"
    src.write_text(p)
    sh(f"ssh {SPARK} 'mkdir -p ~/{WORK}/fonts'")
    sh(f"ssh {SPARK} 'cd ~/{WORK}/fonts && [ -s fonts.css ] || {{ curl -s -A curl/8 \"{FONTS}\" -o fonts.css && i=0; "
       f"for u in $(grep -o \"https://fonts.gstatic.com[^)]*\" fonts.css); do i=$((i+1)); curl -s \"$u\" -o f$i.ttf; "
       f"sed -i \"s#$u#f$i.ttf#\" fonts.css; done; }}'")
    sh(f"rsync -a {src} {ROOT / 'scripts' / 'article' / 'pdf_paginate.py'} {SPARK}:{WORK}/")
    sh(f"ssh {SPARK} 'mv ~/{WORK}/paper_print.html ~/{WORK}/paper.html'")
    uid = sh(f"ssh {SPARK} 'id -u'").strip()
    script = CONTAINER.replace("%(uid)s", uid)
    out = sh(f"ssh {SPARK} 'docker run --rm -i -v ~/{WORK}:/w node:22-alpine sh -s'", input=script)
    dest = BUILD / "paper_draft.pdf"
    sh(f"rsync -a {SPARK}:{WORK}/paper.pdf {dest}")
    print(out.strip(), f"-> {dest} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
