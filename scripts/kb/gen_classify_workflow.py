#!/usr/bin/env python3
"""Generate sharded Workflow scripts that LLM-classify papers into taxonomy
topics and extract a one-line contribution + threat model from each abstract.

Workflow scripts are capped at 512KB and cannot read files, so papers are
embedded directly and split across as many scripts as needed. Each script runs
a pipeline of batches; each agent classifies ~batch papers.

Outputs scripts to scripts/kb/build/classify-<venue>-<n>.js and prints them.
Capture each run's output['result']['items'] and feed save_classify.py.

Usage: python scripts/kb/gen_classify_workflow.py --venue uss --batch 40 --per-script 1100 --snippet 240
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"
BUILD = ROOT / "scripts" / "kb" / "build"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="uss")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--per-script", type=int, default=1100)
    ap.add_argument("--snippet", type=int, default=240)
    args = ap.parse_args()

    tax = json.loads((ASSETS / "taxonomy.json").read_text(encoding="utf-8"))["topics"]
    tax_lines = "\\n".join(f"{t['slug']}: {t['name']}" for t in tax)
    valid = {t["slug"] for t in tax}

    papers = json.loads((BUILD / args.venue / "papers.json").read_text(encoding="utf-8"))
    compact = [
        {"id": p["id"], "title": p["title"],
         "snippet": (p.get("abstract") or p.get("tldr") or "")[:args.snippet]}
        for p in papers
    ]

    scripts = []
    for si, start in enumerate(range(0, len(compact), args.per_script)):
        chunk = compact[start:start + args.per_script]
        batches = [chunk[i:i + args.batch] for i in range(0, len(chunk), args.batch)]
        js = TEMPLATE % {
            "venue": args.venue, "n": si,
            "tax": tax_lines,
            "batches": json.dumps(batches, ensure_ascii=False),
        }
        out = BUILD / f"classify-{args.venue}-{si}.js"
        out.write_text(js, encoding="utf-8")
        scripts.append(out)
        print(f"wrote {out.name}: {len(chunk)} papers in {len(batches)} batches, {len(js)} bytes"
              + ("  <-- WARNING >512KB" if len(js) > 524288 else ""))
    print("RUN:", " ".join(s.name for s in scripts))


TEMPLATE = """export const meta = {
  name: 'kb-classify-%(venue)s-%(n)s',
  description: 'LLM-classify %(venue)s papers into security research areas + extract contribution/threat model',
  phases: [{ title: 'Classify' }],
};

const TAXONOMY = `%(tax)s`;
const BATCHES = %(batches)s;

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    items: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          id: { type: 'string' },
          topics: { type: 'array', items: { type: 'string' }, minItems: 1, maxItems: 3 },
          keyContribution: { type: 'string', description: 'one sentence, <= 25 words' },
          threatModel: { type: 'string', description: 'short phrase or empty string' },
        },
        required: ['id', 'topics', 'keyContribution', 'threatModel'],
      },
    },
  },
  required: ['items'],
};

function prompt(batch) {
  const papers = batch.map(p => `### ${p.id}\\nTITLE: ${p.title}\\nABSTRACT: ${p.snippet}`).join('\\n\\n');
  return [
    `Classify each security paper into 1-3 research areas from this taxonomy (use the slug on the left):`,
    TAXONOMY,
    ``,
    `For EACH paper return: id (copy exactly), topics (1-3 slugs from the list above, most specific first),`,
    `keyContribution (one plain-language sentence, <=25 words, what the paper does/shows),`,
    `threatModel (a short phrase naming the attacker/setting, or "" if not an attack paper).`,
    `Only use slugs from the taxonomy. Do not invent slugs.`,
    ``,
    `PAPERS:`,
    papers,
  ].join('\\n');
}

phase('Classify');
const results = await pipeline(
  BATCHES,
  (batch, _orig, i) => agent(prompt(batch), { label: `classify-%(venue)s-%(n)s:${i}`, phase: 'Classify', schema: SCHEMA })
        .then(r => (r && r.items) ? r.items : [])
);
return { items: results.flat() };
"""


if __name__ == "__main__":
    main()
