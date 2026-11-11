#!/usr/bin/env python3
"""Two-pass pagination for the A4 PDF (run inside the render container by make_pdf.py).

The print contents page links every heading, figure and table (<a href="#id">); Chromium writes each internal link
as a named destination, so the page every entry lands on can be read back from the PDF. Pass 1 renders with "00"
placeholders, the numbers are filled in and the page re-rendered until they stop moving (page numbers are the same
width, so one more pass normally suffices). The PDF also gets a bookmark outline from the same entries.
    python3 pdf_paginate.py /w/paper.html /w/raw.pdf
"""
import json
import re
import subprocess
import sys

from pypdf import PdfReader, PdfWriter

SRC, OUT = sys.argv[1], sys.argv[2]
CHROME = ["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--run-all-compositor-stages-before-draw",
          "--virtual-time-budget=20000", "--no-pdf-header-footer"]


def render(html_path, pdf_path):
    subprocess.run(CHROME + [f"--print-to-pdf={pdf_path}", f"file://{html_path}"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pages(pdf_path):
    r = PdfReader(pdf_path)
    out = {}
    for name, dest in r.named_destinations.items():
        try:
            out[name.lstrip("/")] = r.get_destination_page_number(dest) + 1
        except Exception:
            pass
    return out, len(r.pages)


def main():
    html = open(SRC).read()
    ids = re.findall(r'class="pg" data-id="([^"]+)"', html)
    prev = None
    for n in range(4):
        tmp = SRC.replace(".html", f".p{n}.html")
        open(tmp, "w").write(html)
        render(tmp, OUT)
        got, npages = pages(OUT)
        missing = [i for i in ids if i not in got]
        cur = {i: got.get(i, 0) for i in ids}
        print(f"pass {n + 1}: {npages} pages, {len(ids) - len(missing)}/{len(ids)} entries placed", flush=True)
        if cur == prev:
            break
        prev = cur
        html = re.sub(r'(class="pg" data-id="([^"]+)">)[^<]*(<)', lambda m: f"{m.group(1)}{cur.get(m.group(2), '')}{m.group(3)}",
                      html)
    if missing:
        print("not found:", missing[:10])
    # bookmarks
    entries = json.loads(re.search(r"<!--OUTLINE (.*?)-->", html, re.S).group(1))
    w = PdfWriter(clone_from=OUT)
    parents = {}
    for e in entries:
        p = prev.get(e["id"])
        if not p:
            continue
        parent = parents.get(e["parent"]) if e.get("parent") else None
        parents[e["id"]] = w.add_outline_item(e["title"], p - 1, parent=parent)
    w.page_mode = "/UseOutlines"
    w.write(OUT)


if __name__ == "__main__":
    main()
