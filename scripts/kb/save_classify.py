#!/usr/bin/env python3
"""Merge classification-workflow output(s) into a per-venue llm.json sidecar.

Each input is a Workflow output file (JSON with ['result']['items'] = list of
{id, topics, keyContribution, threatModel}). Invalid slugs are dropped; papers
with no valid topic are skipped (assemble.py keyword-classifies those). Writes
scripts/kb/build/<venue>/llm.json keyed by paper id.

Usage:
  python scripts/kb/save_classify.py --venue uss --outputs f1.output f2.output
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"
BUILD = ROOT / "scripts" / "kb" / "build"


def load_items(path: str) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(d, dict) and "result" in d:
        d = d["result"]
    if isinstance(d, dict):
        return d.get("items", [])
    return d if isinstance(d, list) else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="uss")
    ap.add_argument("--outputs", nargs="+", required=True)
    args = ap.parse_args()

    valid = {t["slug"] for t in json.loads((ASSETS / "taxonomy.json").read_text(encoding="utf-8"))["topics"]}

    merged: dict[str, dict] = {}
    raw = 0
    for path in args.outputs:
        for it in load_items(path):
            raw += 1
            pid = it.get("id")
            topics = [s for s in (it.get("topics") or []) if s in valid][:3]
            if not pid or not topics:
                continue
            entry = {"topics": topics}
            if it.get("keyContribution"):
                entry["keyContribution"] = it["keyContribution"].strip()
            if it.get("threatModel"):
                entry["threatModel"] = it["threatModel"].strip()
            merged[pid] = entry

    out = BUILD / args.venue / "llm.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[{args.venue}] {raw} items in -> {len(merged)} classified papers written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
