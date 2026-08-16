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


VENUE_SHORT = {"USENIX Security": "USENIX", "NDSS": "NDSS", "IEEE S&P": "S&P", "ACM CCS": "CCS"}


def build_topic_inputs(venue_keys: list[str], min_papers: int, cap: int, snippet: int = 220) -> list[dict]:
    # Merge papers across all given venues, grouped by topic (cross-venue narratives).
    tax: dict[str, dict] = {}
    by_topic: dict[str, list] = {}
    venue_label = []
    for vk in venue_keys:
        path = ASSETS / f"{vk}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        venue_label.append(data["venue"])
        for t in data["topics"]:
            tax.setdefault(t["slug"], t)
        for p in data["papers"]:
            p["_venue_short"] = VENUE_SHORT.get(p.get("venue"), p.get("venue"))
            for s in p.get("topics", []):
                by_topic.setdefault(s, []).append(p)

    venues_str = ", ".join(venue_label)
    topics = []
    for slug, papers in by_topic.items():
        if slug == "uncategorized" or len(papers) < min_papers:
            continue
        # Keep the most-cited (capped) + the earliest papers, for timeline anchoring.
        papers_sorted = sorted(papers, key=lambda x: (-(x.get("citationCount") or 0), x.get("year") or 0))
        keep = list(papers_sorted[:cap])
        kept_ids = {id(p) for p in keep}
        for e in sorted(papers, key=lambda x: x.get("year") or 9999)[:3]:
            if id(e) not in kept_ids:
                keep.append(e)
                kept_ids.add(id(e))
        # Also always include the most RECENT papers (current state of the art, e.g.
        # 2026): citation-ranking drops them because new papers have few citations,
        # which would make narratives blind to the latest year.
        for e in sorted(papers, key=lambda x: -(x.get("year") or 0))[:10]:
            if id(e) not in kept_ids:
                keep.append(e)
                kept_ids.add(id(e))
        compact = [
            {
                "id": p["id"],
                "title": p["title"],
                "venue": p.get("_venue_short"),
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
            "venue": venues_str,
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
  const list = t.papers.map(p => `- [${p.id}] ${p.venue} ${p.year}, ${p.cites} cites: ${p.title} :: ${p.snippet}`).join('\\n');
  return [
    `You are a security-research librarian writing for a knowledge base aimed at grad students.`,
    `Research area: "${t.name}" — ${t.description}`,
    `Below are ${t.papers.length} representative papers (of ${t.total} total in this area) drawn from the top security venues (${t.venue}), sorted by year.`,
    `Each line: [id] VENUE year, citations: title :: snippet.`,
    ``,
    list,
    ``,
    `TASKS:`,
    `1) narrative: Write 2-4 SHORT paragraphs (blank-line separated), in plain, readable language, telling how this area evolved across these top venues: what the earliest listed work tackled, the key shifts/breakthroughs, and where it stands now. Make sure the final paragraph reflects the most recent work shown (including the latest year in the list). Cite specific papers inline by title and year (you may note the venue). Draw connections across venues where relevant. Do NOT invent papers — use only the list above. No markdown headers.`,
    `2) milestones: Choose 5-8 pivotal papers FROM THE LIST that best mark the area's evolution (they may span different venues). For each, return its exact paperId and title (copied verbatim), its year, and a one-clause note on why it mattered. Order chronologically.`,
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
    ap.add_argument("--venues", default="uss,ndss,sp,ccs",
                    help="comma-separated venue keys to merge into cross-venue narratives")
    ap.add_argument("--min", type=int, default=5)
    ap.add_argument("--cap", type=int, default=40)
    ap.add_argument("--snippet", type=int, default=150)
    args = ap.parse_args()
    venue_keys = [v.strip() for v in args.venues.split(",") if v.strip()]
    topics = build_topic_inputs(venue_keys, args.min, args.cap, args.snippet)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    js = WF_TEMPLATE % {
        "key": "-".join(venue_keys),
        "venue": "the Big Four security conferences",
        "data": json.dumps(topics, ensure_ascii=False),
    }
    OUT.write_text(js, encoding="utf-8")
    size = len(js.encode("utf-8"))
    print(f"wrote {OUT} with {len(topics)} topics "
          f"({sum(len(t['papers']) for t in topics)} paper refs, {size} bytes)"
          + ("  <-- WARNING >512KB, lower --cap/--snippet" if size > 524288 else ""))


if __name__ == "__main__":
    main()
