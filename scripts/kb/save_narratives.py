#!/usr/bin/env python3
"""Persist per-venue narrative-workflow output into per-topic sidecar files.

Each run is for ONE venue. Results are merged into scripts/kb/build/topics/<slug>.json
under byVenue[<venue>] = {narrative, milestones}, so a topic file accumulates a
separate venue-scoped story for each conference. Milestone paperIds are resolved
to URLs within that venue's assembled data. assemble.py copies these into
assets/kb/topics/, and js/kb.js loads byVenue[currentVenue].

Usage: python scripts/kb/save_narratives.py --results <file.json> --venue ndss
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"
TOPICS_OUT = ROOT / "scripts" / "kb" / "build" / "topics"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--venue", required=True,
                    help="venue key (uss/ndss/sp/ccs), or 'top4' for the cross-venue combined story")
    args = ap.parse_args()

    # 'top4' resolves milestone paperIds across all venues; a single venue resolves within it.
    venue_files = ["uss", "ndss", "sp", "ccs"] if args.venue == "top4" else [args.venue]
    by_id: dict[str, dict] = {}
    tax: dict[str, dict] = {}
    default_venue = "the Big Four"
    for vk in venue_files:
        d = json.loads((ASSETS / f"{vk}.json").read_text(encoding="utf-8"))
        for p in d["papers"]:
            by_id[p["id"]] = p
        for t in d["topics"]:
            tax.setdefault(t["slug"], t)

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    if isinstance(results, dict):
        results = results.get("results", [])

    TOPICS_OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in results:
        slug = r["slug"]
        milestones = []
        for m in r.get("milestones", []):
            p = by_id.get(m.get("paperId", ""))
            milestones.append({
                "year": m.get("year"),
                "title": m.get("title") or (p["title"] if p else ""),
                "note": m.get("note", ""),
                "venue": (p or {}).get("venue", default_venue),
                "url": (p or {}).get("url"),
                "paperId": m.get("paperId"),
            })
        milestones.sort(key=lambda x: x.get("year") or 0)

        path = TOPICS_OUT / f"{slug}.json"
        topic = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        topic.setdefault("slug", slug)
        topic["name"] = topic.get("name") or r.get("name") or tax.get(slug, {}).get("name", slug)
        topic["description"] = topic.get("description") or tax.get(slug, {}).get("description", "")
        topic.setdefault("byVenue", {})
        topic["byVenue"][args.venue] = {
            "narrative": r.get("narrative", ""),
            "milestones": milestones,
        }
        path.write_text(json.dumps(topic, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    print(f"[{args.venue}] merged {n} topics into {TOPICS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
