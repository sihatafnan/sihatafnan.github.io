#!/usr/bin/env python3
"""Generate a self-contained Workflow script that writes a plain-language
evolution narrative + timeline milestones for each research topic, using the
assembled per-venue KB data.

The paper data is embedded directly into the generated .js (Workflow scripts
cannot read files or take large inline args). Run the result with:
  Workflow({ scriptPath: "scripts/kb/build/narrative_wf.js" })
then feed the returned {results:[...]} back through save_narratives.py.

Usage: python scripts/kb/gen_narrative_workflow.py --venue uss --min 5 --cap 55
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"
OUT = ROOT / "scripts" / "kb" / "build" / "narrative_wf.js"


def build_topic_inputs(venue_key: str, min_papers: int, cap: int, snippet: int = 220) -> list[dict]:
    data = json.loads((ASSETS / f"{venue_key}.json").read_text(encoding="utf-8"))
    tax = {t["slug"]: t for t in data["topics"]}
    by_topic: dict[str, list] = {}
    for p in data["papers"]:
        for s in p.get("topics", []):
            by_topic.setdefault(s, []).append(p)

    topics = []
    for slug, papers in by_topic.items():
        if slug == "uncategorized" or len(papers) < min_papers:
            continue
        # Keep all earliest-year papers + the most cited, capped, for context.
        papers_sorted = sorted(papers, key=lambda x: (-(x.get("citationCount") or 0), x.get("year") or 0))
        keep = papers_sorted[:cap]
        # ensure earliest paper(s) included for timeline anchoring
        earliest = sorted(papers, key=lambda x: x.get("year") or 9999)[:3]
        for e in earliest:
            if e not in keep:
                keep.append(e)
        compact = [
            {
                "id": p["id"],
                "title": p["title"],
                "year": p.get("year"),
                "cites": p.get("citationCount") or 0,
                "snippet": (p.get("tldr") or (p.get("abstract") or ""))[:snippet],
            }
            for p in sorted(keep, key=lambda x: x.get("year") or 0)
        ]
        topics.append({
            "slug": slug,
            "name": tax.get(slug, {}).get("name", slug),
            "description": tax.get(slug, {}).get("description", ""),
            "venue": data["venue"],
            "total": len(papers),
            "papers": compact,
        })
    topics.sort(key=lambda t: -t["total"])
    return topics


WF_TEMPLATE = """export const meta = {
  name: 'kb-narratives-%(key)s',
  description: 'Write a plain-language evolution narrative + timeline for each %(venue)s research topic',
  phases: [{ title: 'Narratives', detail: 'one agent per research area' }],
};

const TOPICS = %(data)s;

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    narrative: { type: 'string', description: '2-4 short paragraphs, plain language, separated by blank lines' },
    milestones: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          year: { type: 'number' },
          paperId: { type: 'string' },
          title: { type: 'string' },
          note: { type: 'string', description: 'one concise clause on why this paper mattered' },
        },
        required: ['year', 'title', 'note'],
      },
    },
  },
  required: ['narrative', 'milestones'],
};

function prompt(t) {
  const list = t.papers.map(p => `- [${p.id}] (${p.year}, ${p.cites} cites) ${p.title} :: ${p.snippet}`).join('\\n');
  return [
    `You are a security-research librarian writing for a knowledge base aimed at grad students.`,
    `Research area: "${t.name}" — ${t.description}`,
    `Below are ${t.papers.length} representative ${t.venue} papers (of ${t.total} total in this area), sorted by year.`,
    `Each line: [id] (year, citations) title :: snippet.`,
    ``,
    list,
    ``,
    `TASKS:`,
    `1) narrative: Write 2-4 SHORT paragraphs (blank-line separated), in plain, readable language, telling how this area evolved at ${t.venue}: what the earliest listed work tackled, the key shifts/breakthroughs, and where it stands now. Cite specific papers inline by title and year. Do NOT invent papers — use only the list above. No markdown headers.`,
    `2) milestones: Choose 5-8 pivotal papers FROM THE LIST that best mark the area's evolution. For each, return its exact paperId and title (copied verbatim), its year, and a one-clause note on why it mattered. Order chronologically.`,
  ].join('\\n');
}

phase('Narratives');
const results = await pipeline(
  TOPICS,
  t => agent(prompt(t), { label: `narr:${t.slug}`, phase: 'Narratives', schema: SCHEMA })
        .then(r => r ? { slug: t.slug, name: t.name, ...r } : null)
);
return { results: results.filter(Boolean) };
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="uss")
    ap.add_argument("--min", type=int, default=5)
    ap.add_argument("--cap", type=int, default=55)
    ap.add_argument("--snippet", type=int, default=220)
    args = ap.parse_args()
    topics = build_topic_inputs(args.venue, args.min, args.cap, args.snippet)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    js = WF_TEMPLATE % {
        "key": args.venue,
        "venue": json.loads((ASSETS / f"{args.venue}.json").read_text(encoding="utf-8"))["venue"],
        "data": json.dumps(topics, ensure_ascii=False),
    }
    OUT.write_text(js, encoding="utf-8")
    print(f"wrote {OUT} with {len(topics)} topics "
          f"({sum(len(t['papers']) for t in topics)} paper refs embedded)")


if __name__ == "__main__":
    main()
