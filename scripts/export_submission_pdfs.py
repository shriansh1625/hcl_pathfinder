#!/usr/bin/env python3
"""Export submission markdown docs to well-formatted PDFs."""

from __future__ import annotations

import re
import sys
from io import BytesIO
from pathlib import Path

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "pdf"

CSS = """
@page {
  size: A4;
  margin: 20mm 16mm 22mm 16mm;
}

* {
  box-sizing: border-box;
}

html {
  font-size: 11pt;
}

body {
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  color: #0f172a;
  line-height: 1.55;
  margin: 0;
  padding: 0;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

h1 {
  font-size: 22pt;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 10pt 0;
  line-height: 1.2;
}

h2 {
  font-size: 15pt;
  font-weight: 700;
  color: #1e3a5f;
  margin: 22pt 0 8pt 0;
  padding-bottom: 4pt;
  border-bottom: 1.5pt solid #cbd5e1;
}

h3 {
  font-size: 12.5pt;
  font-weight: 600;
  color: #1e40af;
  margin: 16pt 0 6pt 0;
}

h4 {
  font-size: 11pt;
  font-weight: 600;
  color: #334155;
  margin: 12pt 0 4pt 0;
}

p {
  margin: 0 0 8pt 0;
}

strong {
  font-weight: 600;
}

a {
  color: #1d4ed8;
  word-break: break-all;
}

hr {
  border: none;
  border-top: 1pt solid #e2e8f0;
  margin: 14pt 0;
}

ul, ol {
  margin: 0 0 10pt 0;
  padding-left: 20pt;
}

li {
  margin: 0 0 4pt 0;
}

blockquote {
  margin: 10pt 0;
  padding: 10pt 14pt;
  border-left: 4pt solid #3b82f6;
  background: #f1f5f9;
  color: #1e293b;
  border-radius: 0 4pt 4pt 0;
}

blockquote p {
  margin: 0;
}

pre {
  font-family: Consolas, "Courier New", monospace;
  font-size: 8.5pt;
  line-height: 1.35;
  background: #f8fafc;
  border: 1pt solid #e2e8f0;
  border-radius: 4pt;
  padding: 10pt 12pt;
  margin: 10pt 0 12pt 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9pt;
  background: #f1f5f9;
  padding: 1pt 4pt;
  border-radius: 3pt;
}

pre code {
  background: transparent;
  padding: 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 10pt 0 14pt 0;
  table-layout: fixed;
}

th {
  background: #1e3a5f;
  color: #ffffff;
  font-weight: 600;
  text-align: left;
  padding: 7pt 8pt;
  font-size: 9.5pt;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

td {
  border: 1pt solid #cbd5e1;
  padding: 6pt 8pt;
  font-size: 9.5pt;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
}

tr:nth-child(even) td {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  background: #1e3a5f;
  color: #fff;
  font-size: 9pt;
  font-weight: 600;
  padding: 4pt 10pt;
  border-radius: 4pt;
  margin-bottom: 12pt;
}

.subtitle {
  font-size: 10pt;
  color: #475569;
  margin-bottom: 16pt;
  line-height: 1.5;
}

.subtitle p {
  margin: 0 0 3pt 0;
}
"""


def preprocess_md(md_text: str) -> str:
    md_text = re.sub(
        r"\n---\n\n\*Export this document to PDF.*\*$",
        "",
        md_text.strip(),
        flags=re.DOTALL,
    )
    return re.sub(r"^- \[ \] ", "- ☐ ", md_text, flags=re.MULTILINE)


def md_to_html(md_text: str, *, title: str, badge: str) -> str:
    body = markdown.markdown(
        preprocess_md(md_text),
        extensions=[TableExtension(), FencedCodeExtension(), "sane_lists"],
    )
    body = re.sub(
        r"(<h1>.*?</h1>)\s*(<p><strong>.*?</strong>.*?</p>\s*(?:<p>.*?</p>\s*)*)",
        r"\1<div class='subtitle'>\2</div>",
        body,
        count=1,
        flags=re.DOTALL,
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="badge">{badge}</div>
  {body}
</body>
</html>"""


def export_pdf_playwright(html: str, out_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=str(out_path),
            format="A4",
            margin={"top": "20mm", "right": "16mm", "bottom": "22mm", "left": "16mm"},
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                '<div style="width:100%;font-size:9px;color:#64748b;text-align:center;'
                'font-family:Segoe UI,Arial,sans-serif;">'
                '<span class="pageNumber"></span></div>'
            ),
        )
        browser.close()


def export_pdf_xhtml2pdf(html: str, out_path: Path) -> None:
    from xhtml2pdf import pisa

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as pdf_file:
        result = pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=pdf_file, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed with {result.err} error(s)")


def export_pdf(html: str, out_path: Path) -> None:
    try:
        export_pdf_playwright(html, out_path)
    except Exception as exc:
        print(f"  Playwright unavailable ({exc}); using xhtml2pdf fallback.")
        export_pdf_xhtml2pdf(html, out_path)


def main() -> int:
    docs = [
        (
            ROOT / "docs" / "SOLUTION_DOCUMENTATION.md",
            OUT_DIR / "PathFinder_Solution_Documentation.pdf",
            "PathFinder — Solution Documentation",
            "HCLTech AMPlified Season 1 · Round 2",
        ),
        (
            ROOT / "docs" / "DEMO_VIDEO_SCRIPT.md",
            OUT_DIR / "PathFinder_Demo_Video_Script.pdf",
            "PathFinder — 5-Minute Demo Video Script",
            "Recording guide · 4:45 to 5:00 minutes",
        ),
    ]

    for src, dst, title, badge in docs:
        if not src.exists():
            print(f"ERROR: missing {src}", file=sys.stderr)
            return 1
        html = md_to_html(src.read_text(encoding="utf-8"), title=title, badge=badge)
        print(f"Generating {dst.name} ...")
        export_pdf(html, dst)
        print(f"  OK  {dst} ({dst.stat().st_size // 1024} KB)")

    print(f"\nDone. PDFs saved to: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
