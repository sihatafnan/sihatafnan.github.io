#!/usr/bin/env python3
"""Persist narrative-workflow output into per-topic sidecar files.

Input: a JSON file containing the Workflow return value, i.e. {"results": [
  {"slug", "name", "narrative", "milestones": [{"year","paperId","title","note"}]}
]}. Resolves each milestone's paperId to a paper URL/venue from the assembled
venue data and writes scripts/kb/build/topics/<slug>.json, which assemble.py then
copies into assets/kb/topics/.

Usage: python scripts/kb/save_narratives.py --results <file.json> --venue uss
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
    ap.add_argument("--venues", default="uss,ndss,sp,ccs")
    args = ap.parse_args()

    by_id: dict[str, dict] = {}
    tax: dict[str, dict] = {}
    venues_present: list[str] = []
    for vk in [v.strip() for v in args.venues.split(",") if v.strip()]:
        path = ASSETS / f"{vk}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        venues_present.append(vk)
        for p in d["papers"]:
            by_id[p["id"]] = p
        for t in d["topics"]:
            tax.setdefault(t["slug"], t)
    venue_data = {"venue": "the Big Four"}

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
                "venue": (p or {}).get("venue", venue_data["venue"]),
                "url": (p or {}).get("url"),
                "paperId": m.get("paperId"),
            })
        milestones.sort(key=lambda x: x.get("year") or 0)
        topic = {
            "slug": slug,
            "name": r.get("name") or tax.get(slug, {}).get("name", slug),
            "description": tax.get(slug, {}).get("description", ""),
            "narrative": r.get("narrative", ""),
            "milestones": milestones,
            "venues": venues_present,
        }
        (TOPICS_OUT / f"{slug}.json").write_text(
            json.dumps(topic, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    print(f"wrote {n} topic narrative files to {TOPICS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
