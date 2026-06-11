#!/usr/bin/env python3
"""Download + extract text from paper PDFs for the deep-read step.

Agents cannot fetch USENIX/ACM/IEEE PDFs directly (403 to the fetch tool), so we
pull them here with a browser User-Agent and extract text with pypdf, caching the
result. The extracted text is then fed to deep-read agents via their prompt.

Usage (as a library):
  from pdftext import get_text
  txt = get_text(pdf_url)        # returns extracted text (cached) or None

CLI: python scripts/kb/pdftext.py <pdf_url>
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
PDFCACHE = ROOT / "scripts" / "kb" / "build" / "pdf"
BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90]


def get_text(url: str, max_chars: int = 45000) -> str | None:
    if not url:
        return None
    PDFCACHE.mkdir(parents=True, exist_ok=True)
    txt_cache = PDFCACHE / f"{_slug(url)}.txt"
    if txt_cache.exists():
        return txt_cache.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    pdf_cache = PDFCACHE / f"{_slug(url)}.pdf"
    if not pdf_cache.exists():
        try:
            r = requests.get(url, headers=BROWSER_UA, timeout=120)
            if r.status_code != 200 or not r.content[:4] == b"%PDF":
                return None
            pdf_cache.write_bytes(r.content)
            time.sleep(0.8)
        except requests.RequestException:
            return None

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_cache))
        parts = []
        for page in reader.pages[:14]:  # intro/design usually within first ~14 pages
            parts.append(page.extract_text() or "")
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(parts)).strip()
        txt_cache.write_text(text, encoding="utf-8")
        return text[:max_chars]
    except Exception as e:  # noqa: BLE001
        print(f"pdf extract failed for {url}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    t = get_text(sys.argv[1])
    print((t or "<none>")[:1500])
