#!/usr/bin/env python3
"""Assemble served KB JSON from the ingest workspace.

Reads:
  scripts/kb/build/<venue>/papers.json     (from ingest.py)
  assets/kb/taxonomy.json                   (topic list + keywords)
  scripts/kb/build/<venue>/llm.json         (optional sidecar from the classify/
                                             deep-read Workflow, keyed by paper id)
  scripts/kb/build/topics/<slug>.json       (optional narrative/milestones sidecars)

Writes (served statically, fetched by /js/kb.js):
  assets/kb/<venue>.json
  assets/kb/topics/<slug>.json              (cross-venue, when narratives exist)

Topic assignment: uses LLM topics from the sidecar when present, otherwise a
keyword matcher over title+abstract. The site is fully functional either way.

Usage:
  python scripts/kb/assemble.py --venue uss
  python scripts/kb/assemble.py --venue all
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "kb" / "build"
ASSETS = ROOT / "assets" / "kb"
VENUE_KEYS = ["uss", "ndss", "sp", "ccs"]

# Short keywords that need word-boundary matching to avoid false positives.
SHORT = {"dp", "5g", "4g", "lte", "tee", "sgx", "mfa", "rf", "cfi", "rop", "puf",
         "ics", "can bus", "nft", "mev", "sim", "cve", "ai", "llm", "gpt", "zkp",
         "mpc", "fhe", "iot", "apk", "dns", "bgp", "tcp", "tls", "ssl", "vpn", "sbom"}


def load_taxonomy() -> list[dict]:
    tax = json.loads((ASSETS / "taxonomy.json").read_text(encoding="utf-8"))
    for t in tax["topics"]:
        pats = []
        for kw in t["keywords"]:
            kw = kw.lower()
            if kw in SHORT or len(kw) <= 3:
                pats.append((re.compile(r"\b" + re.escape(kw) + r"\b"), 1))
            else:
                pats.append((re.compile(re.escape(kw)), 1))
        t["_pats"] = pats
    return tax["topics"]


def classify(paper: dict, topics: list[dict]) -> list[str]:
    title = (paper.get("title") or "").lower()
    body = " ".join([title, title, (paper.get("abstract") or "").lower(),
                     (paper.get("tldr") or "").lower()])  # title double-weighted
    scored = []
    for t in topics:
        score = sum(w for pat, w in t["_pats"] if pat.search(body))
        # bonus if a keyword appears in the title
        if any(pat.search(title) for pat, _ in t["_pats"]):
            score += 2
        if score:
            scored.append((score, t["slug"]))
    scored.sort(reverse=True)
    return [slug for _, slug in scored[:3]] or ["uncategorized"]


def assemble_venue(key: str, topics: list[dict]) -> None:
    papers_path = BUILD / key / "papers.json"
    if not papers_path.exists():
        print(f"[skip] {key}: no papers.json")
        return
    papers = json.loads(papers_path.read_text(encoding="utf-8"))

    llm_path = BUILD / key / "llm.json"
    llm = json.loads(llm_path.read_text(encoding="utf-8")) if llm_path.exists() else {}

    tname = {t["slug"]: t["name"] for t in topics}
    out_papers = []
    counts: dict[str, int] = {}
    for p in papers:
        side = llm.get(p["id"], {})
        tlist = side.get("topics") or classify(p, topics)
        tlist = [s for s in tlist if s in tname or s == "uncategorized"]
        rec = {
            "id": p["id"],
            "title": p["title"],
            "authors": p.get("authors", []),
            "year": p.get("year"),
            "venue": p.get("venue"),
            "url": p.get("url"),
            "pdf": p.get("pdf"),
            "doi": p.get("doi"),
            "arxiv": p.get("arxiv"),
            "s2": p.get("s2"),
            "citationCount": p.get("citationCount"),
            "abstract": p.get("abstract"),
            "tldr": p.get("tldr"),
            "topics": tlist,
            "topicNames": [tname.get(s, s) for s in tlist],
        }
        for f in ("keyContribution", "threatModel", "lineage", "findings", "depth"):
            if side.get(f):
                rec[f] = side[f]
        out_papers.append(rec)
        for s in tlist:
            counts[s] = counts.get(s, 0) + 1

    venue_topics = [
        {"slug": t["slug"], "name": t["name"], "description": t["description"],
         "count": counts.get(t["slug"], 0)}
        for t in topics if counts.get(t["slug"], 0) > 0
    ]
    venue_topics.sort(key=lambda x: -x["count"])

    display = papers[0]["venue"] if papers else key
    data = {
        "venue": display,
        "venue_key": key,
        "generated": datetime.date.today().isoformat(),
        "topics": venue_topics,
        "papers": out_papers,
    }
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"{key}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[{key}] wrote {out.relative_to(ROOT)}: {len(out_papers)} papers, "
          f"{len(venue_topics)} topics, {sum(1 for p in out_papers if p.get('depth') == 'deep')} deep")


def assemble_topics() -> None:
    """Copy any cross-venue topic narrative sidecars into served assets."""
    src = BUILD / "topics"
    if not src.exists():
        return
    dst = ASSETS / "topics"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        (dst / f.name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        n += 1
    if n:
        print(f"[topics] wrote {n} narrative files")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="uss")
    args = ap.parse_args()
    topics = load_taxonomy()
    keys = VENUE_KEYS if args.venue == "all" else [args.venue]
    for key in keys:
        assemble_venue(key, topics)
    assemble_topics()


if __name__ == "__main__":
    main()
