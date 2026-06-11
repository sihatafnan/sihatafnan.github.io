#!/usr/bin/env python3
"""Fallback: reconstruct narrative-workflow results from agent transcripts.

Scans a workflow transcript dir's agent-*.jsonl files. For each, reads the
research-area name from the prompt and the {narrative, milestones} object from
the agent's StructuredOutput tool call, maps the name to a taxonomy slug, and
emits {"results": [...]} compatible with save_narratives.py.

Usage:
  python scripts/kb/extract_wf_results.py --dir <workflow transcript dir> --out scripts/kb/build/narratives.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"


def name_to_slug() -> dict[str, str]:
    tax = json.loads((ASSETS / "taxonomy.json").read_text(encoding="utf-8"))
    return {t["name"].lower(): t["slug"] for t in tax["topics"]}


def find_struct(obj):
    """Return the first tool_use input dict that has a 'narrative' key."""
    msg = obj.get("message", {})
    content = msg.get("content")
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                inp = c.get("input") or {}
                if "narrative" in inp:
                    return inp
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default=str(ROOT / "scripts" / "kb" / "build" / "narratives.json"))
    args = ap.parse_args()

    n2s = name_to_slug()
    results = []
    for jf in sorted(Path(args.dir).glob("agent-*.jsonl")):
        lines = jf.read_text(encoding="utf-8", errors="ignore").splitlines()
        area, struct = None, None
        for ln in lines:
            try:
                o = json.loads(ln)
            except ValueError:
                continue
            if area is None:
                txt = json.dumps(o)
                m = re.search(r'Research area:\s*\\?"([^"\\]+)', txt)
                if m:
                    area = m.group(1).strip()
            s = find_struct(o)
            if s:
                struct = s
        if not struct:
            continue
        slug = n2s.get((area or "").lower())
        if not slug:
            print(f"  [warn] {jf.name}: unmapped area {area!r}")
            continue
        results.append({"slug": slug, "name": area,
                        "narrative": struct.get("narrative", ""),
                        "milestones": struct.get("milestones", [])})
    Path(args.out).write_text(json.dumps({"results": results}, ensure_ascii=False), encoding="utf-8")
    print(f"extracted {len(results)} topic narratives -> {args.out}")


if __name__ == "__main__":
    main()
