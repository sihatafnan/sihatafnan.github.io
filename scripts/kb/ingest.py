#!/usr/bin/env python3
"""Ingest pipeline for the Big-Four security-conference knowledge base.

Per venue/year:
  1. DBLP table-of-contents (paginated) -> canonical paper list.
  2. Semantic Scholar *bulk-by-venue* -> citationCount / fields / openAccessPdf
     / abstract-where-available, matched back to DBLP papers by normalized title.
  3. Venue-specific abstract scrape to fill any still-missing abstracts
     (USENIX & NDSS are fully open access and publish abstracts on their site).

Outputs merged `_data/kb/<venue>/papers.json`. Raw DBLP dumps and scraped pages
are cached so reruns are cheap.

Usage:
  python scripts/kb/ingest.py --venue uss --years 2018-2025
  python scripts/kb/ingest.py --venue all
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
# Build workspace: raw DBLP/S2 dumps + intermediate per-venue papers.json.
# Lives under scripts/ (excluded from the Jekyll build); final served JSON is
# emitted to assets/kb/ by the assemble step.
DATA = ROOT / "scripts" / "kb" / "build"
CACHE = DATA / "cache"

# DBLP key -> (display venue, Semantic Scholar venue string)
VENUES = {
    "uss": ("USENIX Security", "USENIX Security Symposium"),
    "ndss": ("NDSS", "Network and Distributed System Security Symposium"),
    "sp": ("IEEE S&P", "IEEE Symposium on Security and Privacy"),
    "ccs": ("ACM CCS", "Conference on Computer and Communications Security"),
}

DBLP_API = "https://dblp.org/search/publ/api"
S2_BULK = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIELDS = "title,abstract,citationCount,influentialCitationCount,year,venue,externalIds,openAccessPdf,fieldsOfStudy"

BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
API_UA = {"User-Agent": "sihatafnan.github.io KB builder (academic, polite)"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def norm_title(t: str) -> str:
    """Aggressive title key for cross-source matching."""
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()


# ---------------------------------------------------------------------------
# DBLP
# ---------------------------------------------------------------------------
def fetch_dblp_year(key: str, year: int, refresh: bool = False) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"dblp-{key}{year}.json"
    if cache.exists() and not refresh:
        hits = json.loads(cache.read_text(encoding="utf-8"))
    else:
        log(f"[dblp] {key} {year}")
        hits, first = [], 0
        while True:
            data = None
            # DBLP throttles aggressively (connection resets); back off patiently.
            for attempt, wait in enumerate((0, 20, 45, 90, 150, 240)):
                if wait:
                    log(f"  dblp retry {attempt} in {wait}s")
                    time.sleep(wait)
                try:
                    r = requests.get(
                        DBLP_API,
                        params={
                            "q": f"toc:db/conf/{key}/{key}{year}.bht:",
                            "h": 100,
                            "f": first,
                            "format": "json",
                        },
                        headers=API_UA,
                        timeout=60,
                    )
                    r.raise_for_status()
                    data = r.json()
                    break
                except (requests.RequestException, ValueError):
                    continue
            if data is None:
                raise RuntimeError(f"DBLP failed for {key}{year} at f={first}")
            block = data["result"]["hits"]
            total = int(block.get("@total", 0))
            page = block.get("hit", []) or []
            hits.extend(h["info"] for h in page)
            first += len(page)
            if len(page) < 100 or first >= total:
                break
            time.sleep(1.5)
        cache.write_text(json.dumps(hits, indent=1), encoding="utf-8")
        time.sleep(1.0)

    papers, seen = [], set()
    for info in hits:
        if info.get("type") not in ("Conference and Workshop Papers", None):
            continue
        title = (info.get("title") or "").strip().rstrip(".")
        if not title or norm_title(title) in seen:
            continue
        seen.add(norm_title(title))
        authors = info.get("authors", {}).get("author", []) if info.get("authors") else []
        if isinstance(authors, dict):
            authors = [authors]
        names = [re.sub(r"\s+\d{4}$", "", a.get("text", "")) if isinstance(a, dict) else str(a) for a in authors]
        papers.append(
            {
                "id": f"{key}{year}-{slugify(title)[:48]}",
                "title": title,
                "authors": names,
                "venue": VENUES[key][0],
                "venue_key": key,
                "year": int(info.get("year", year)),
                "doi": (info.get("doi") or "").strip() or None,
                "url": info.get("ee"),
                "dblp": info.get("url"),
            }
        )
    log(f"  -> {len(papers)} papers (dblp @total reported above)")
    return papers


# ---------------------------------------------------------------------------
# Semantic Scholar bulk-by-venue
# ---------------------------------------------------------------------------
def s2_bulk_year(venue_str: str, year: int, refresh: bool = False) -> dict[str, dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"s2-{slugify(venue_str)}-{year}.json"
    if cache.exists() and not refresh:
        records = json.loads(cache.read_text(encoding="utf-8"))
    else:
        log(f"[s2] {venue_str} {year}")
        records, token = [], None
        while True:
            params = {"venue": venue_str, "year": str(year), "fields": S2_FIELDS}
            if token:
                params["token"] = token
            data = None
            for attempt in range(5):
                try:
                    r = requests.get(S2_BULK, params=params, headers=API_UA, timeout=90)
                    if r.status_code == 429:
                        time.sleep(8)
                        continue
                    r.raise_for_status()
                    data = r.json()
                    break
                except (requests.RequestException, ValueError):
                    time.sleep(5 * (attempt + 1))
            if data is None:
                break
            records.extend(data.get("data") or [])
            token = data.get("token")
            if not token:
                break
            time.sleep(2)
        cache.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(1.0)
    return {norm_title(rec.get("title", "")): rec for rec in records if rec.get("title")}


def apply_s2(p: dict, rec: dict) -> None:
    if rec.get("abstract") and not p.get("abstract"):
        p["abstract"] = rec["abstract"]
    p["citationCount"] = rec.get("citationCount")
    p["influentialCitationCount"] = rec.get("influentialCitationCount")
    p["fieldsOfStudy"] = rec.get("fieldsOfStudy")
    oa = rec.get("openAccessPdf") or {}
    if oa.get("url"):
        p["pdf"] = oa["url"]
    ext = rec.get("externalIds") or {}
    p["arxiv"] = ext.get("ArXiv")
    p["s2"] = ext.get("CorpusId")


# ---------------------------------------------------------------------------
# Venue-specific abstract scraping (fills missing abstracts)
# ---------------------------------------------------------------------------
ABSTRACT_PATTERNS = {
    "uss": [r"field-name-field-paper-description.*?<p>(.*?)</p>"],
    "ndss": [
        r'class="paper-data".*?<p>(.*?)</p>',
        r"<h2[^>]*>Abstract</h2>\s*<p>(.*?)</p>",
    ],
}


def scrape_page(key: str, url: str | None) -> str | None:
    """Return cached page HTML for a venue landing page (or None)."""
    if not url:
        return None
    host_ok = (key == "uss" and "usenix.org" in url) or (key == "ndss" and "ndss-symposium.org" in url)
    if not host_ok:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"page-{slugify(url)}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="ignore")
    try:
        r = requests.get(url, headers=BROWSER_UA, timeout=60)
        if r.status_code != 200:
            return None
        cache.write_text(r.text, encoding="utf-8", errors="ignore")
        time.sleep(0.8)
        return r.text
    except requests.RequestException:
        return None


def extract_abstract(key: str, text: str) -> str | None:
    for pat in ABSTRACT_PATTERNS.get(key, []):
        m = re.search(pat, text, re.S)
        if m:
            abs_txt = strip_html(m.group(1))
            if len(abs_txt) > 40:
                return abs_txt
    return None


def extract_pdf(key: str, text: str) -> str | None:
    # Prefer the paper PDF over slides/extended/appendix variants.
    pdfs = re.findall(r'href="([^"]+\.pdf)"', text)
    if not pdfs:
        return None
    for href in pdfs:
        low = href.lower()
        if "slides" in low or "appendix" in low or "poster" in low:
            continue
        return href if href.startswith("http") else "https://www.usenix.org" + href
    return pdfs[0]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def parse_years(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(spec)]


def ingest_venue(key: str, years: list[int], refresh: bool = False) -> None:
    display, venue_str = VENUES[key]
    all_papers: list[dict] = []
    for y in years:
        papers = fetch_dblp_year(key, y, refresh=refresh)
        s2 = s2_bulk_year(venue_str, y, refresh=refresh)
        matched = 0
        for p in papers:
            rec = s2.get(norm_title(p["title"]))
            if rec:
                apply_s2(p, rec)
                matched += 1
        # Scrape venue landing pages to fill missing abstracts and PDF links.
        scraped = 0
        for p in papers:
            if p.get("abstract") and p.get("pdf"):
                continue
            text = scrape_page(key, p.get("url"))
            if not text:
                continue
            if not p.get("abstract"):
                ab = extract_abstract(key, text)
                if ab:
                    p["abstract"] = ab
                    scraped += 1
            if not p.get("pdf"):
                pdf = extract_pdf(key, text)
                if pdf:
                    p["pdf"] = pdf
        have_abs = sum(1 for p in papers if p.get("abstract"))
        log(f"  {key} {y}: {len(papers)} papers | s2-matched {matched} | scraped {scraped} | abstracts {have_abs}/{len(papers)}")
        all_papers.extend(papers)

    out_dir = DATA / key
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "papers.json"
    out.write_text(json.dumps(all_papers, indent=1, ensure_ascii=False), encoding="utf-8")
    have_abs = sum(1 for p in all_papers if p.get("abstract"))
    log(f"[{key}] wrote {out}: {len(all_papers)} papers, {have_abs} with abstracts")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="uss", help="uss|ndss|sp|ccs|all")
    ap.add_argument("--years", default="2018-2025")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    keys = list(VENUES) if args.venue == "all" else [args.venue]
    for key in keys:
        ingest_venue(key, parse_years(args.years), refresh=args.refresh)


if __name__ == "__main__":
    main()
