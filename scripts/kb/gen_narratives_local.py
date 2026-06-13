#!/usr/bin/env python3
"""Generate per-venue evolution narratives locally (no external API calls).

For each topic with >=5 papers at a given venue, writes a data-driven
narrative paragraph + milestone list to scripts/kb/build/narr-<venue>.json.

Usage:
  python scripts/kb/gen_narratives_local.py --venue ccs
  python scripts/kb/gen_narratives_local.py --venue ndss
"""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "kb"
BUILD = ROOT / "scripts" / "kb" / "build"

VENUE_SHORT = {
    "USENIX Security": "USENIX Security",
    "NDSS": "NDSS",
    "IEEE S&P": "S&P",
    "ACM CCS": "CCS",
}

VENUE_LONG = {
    "uss": "USENIX Security",
    "ndss": "NDSS",
    "sp": "S&P",
    "ccs": "CCS",
}

# Topic-specific framing hints to make narratives feel more tailored
TOPIC_CONTEXT = {
    "fuzzing": ("fuzz testing methods, coverage-guided fuzzing, hybrid fuzzing, and domain-specific harnesses", "bug-finding and test generation"),
    "ml-security": ("adversarial attacks, model robustness, and security of ML systems", "machine learning and security"),
    "ml-privacy": ("membership inference, model inversion, and privacy leakage from ML models", "ML privacy"),
    "applied-crypto": ("cryptographic constructions, protocols, and their practical deployment", "applied cryptography"),
    "crypto-protocols": ("protocol design, verification, and attacks on cryptographic protocols", "cryptographic protocols"),
    "mpc-fhe": ("secure multi-party computation, homomorphic encryption, and private computation", "MPC and FHE"),
    "privacy-pets": ("privacy-enhancing technologies, anonymity tools, and data privacy mechanisms", "privacy"),
    "network-security": ("network attacks, defenses, traffic analysis, and protocol security", "network security"),
    "web-security": ("web vulnerabilities, browser security, XSS, CSRF, and web privacy", "web security"),
    "mobile-security": ("mobile OS security, app analysis, and smartphone privacy", "mobile security"),
    "iot-embedded": ("IoT security, embedded firmware, and connected device vulnerabilities", "IoT and embedded security"),
    "hardware-security": ("hardware attacks, CPU vulnerabilities, and microarchitectural security", "hardware security"),
    "side-channels": ("side-channel attacks, timing leaks, and covert channels", "side channels"),
    "trusted-execution": ("trusted execution environments, SGX, enclaves, and TEE attacks", "trusted execution"),
    "memory-safety": ("memory safety bugs, exploit mitigations, and memory error detection", "memory safety"),
    "program-analysis": ("static analysis, symbolic execution, taint analysis, and program verification", "program analysis"),
    "binary-analysis": ("binary analysis, decompilation, reverse engineering, and binary hardening", "binary analysis"),
    "vuln-discovery": ("vulnerability discovery, patch analysis, and CVE research", "vulnerability discovery"),
    "malware": ("malware detection, analysis, and reverse engineering", "malware"),
    "systems-security": ("OS security, kernel hardening, and systems-level defenses", "systems security"),
    "blockchain": ("blockchain security, smart contract vulnerabilities, and DeFi attacks", "blockchain and cryptocurrency security"),
    "authentication": ("authentication schemes, passwords, biometrics, and access control", "authentication"),
    "usable-security": ("user-facing security, security UX, and human factors", "usable security"),
    "cybercrime-measurement": ("measurement studies of cybercrime, abuse, and underground ecosystems", "cybercrime measurement"),
    "wireless-cellular": ("wireless protocol security, cellular attacks, and RF-based threats", "wireless and cellular security"),
    "cps-av-security": ("CPS security, autonomous vehicles, and industrial control systems", "CPS and AV security"),
    "forensics": ("digital forensics, incident response, and artifact analysis", "digital forensics"),
    "anonymity-censorship": ("anonymity networks, censorship circumvention, and traffic fingerprinting", "anonymity and censorship"),
    "formal-methods": ("formal verification, model checking, and security proofs", "formal methods"),
    "phishing-social": ("phishing detection, social engineering, and online scams", "phishing and social engineering"),
    "supply-chain": ("software supply chain security, dependency attacks, and third-party risk", "supply chain security"),
    "differential-privacy": ("differential privacy mechanisms, DP algorithms, and private data release", "differential privacy"),
    "llm-security": ("LLM safety, jailbreaks, prompt injection, and AI model security", "LLM and AI security"),
}


def get_era_label(year: int) -> str:
    if year <= 2018:
        return "early"
    elif year <= 2020:
        return "mid"
    elif year <= 2022:
        return "recent"
    else:
        return "latest"


def shorten(text: str, n: int = 120) -> str:
    if not text:
        return ""
    text = text.strip().rstrip(".")
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "..."


def build_narrative(slug: str, name: str, papers: list[dict], venue_short: str) -> str:
    if not papers:
        return ""

    ctx, domain = TOPIC_CONTEXT.get(slug, (name.lower(), name.lower()))

    # Sort by year, then citation count desc
    sorted_yr = sorted(papers, key=lambda p: (p.get("year") or 0, -(p.get("citationCount") or 0)))
    sorted_cites = sorted(papers, key=lambda p: -(p.get("citationCount") or 0))

    years = sorted([p.get("year") or 0 for p in papers if p.get("year")])
    if not years:
        return ""

    min_yr, max_yr = years[0], years[-1]
    span = max_yr - min_yr

    # Split into early / mid / recent
    if span <= 2:
        early_papers = sorted_yr
        mid_papers = []
        late_papers = []
    elif span <= 5:
        cut = min_yr + span // 2
        early_papers = [p for p in sorted_yr if (p.get("year") or 0) <= cut]
        mid_papers = []
        late_papers = [p for p in sorted_yr if (p.get("year") or 0) > cut]
    else:
        early_cut = min(min_yr + 3, 2019)
        mid_cut = min(early_cut + 3, 2022)
        early_papers = [p for p in sorted_yr if (p.get("year") or 0) <= early_cut]
        mid_papers = [p for p in sorted_yr if early_cut < (p.get("year") or 0) <= mid_cut]
        late_papers = [p for p in sorted_yr if (p.get("year") or 0) > mid_cut]

    def top(plist: list[dict], n: int = 3) -> list[dict]:
        return sorted(plist, key=lambda p: -(p.get("citationCount") or 0))[:n]

    def cite(p: dict) -> str:
        yr = p.get("year", "")
        return f"{p['title']} ({venue_short} {yr})"

    def kc(p: dict, n: int = 110) -> str:
        return shorten(p.get("keyContribution") or p.get("tldr") or "", n)

    paragraphs: list[str] = []

    # ── Paragraph 1: early work ───────────────────────────────────────
    if early_papers:
        ep = top(early_papers, 3)
        p1_parts = [
            f"Research on {domain} at {venue_short} began taking shape around {min_yr}, "
            f"with early work concentrating on {ctx}."
        ]
        if ep:
            main = ep[0]
            p1_parts.append(
                f" {cite(main)} set an influential baseline by showing how to {kc(main, 120)}."
            )
        if len(ep) > 1:
            extras = ep[1:3]
            conj = " Alongside this, " if len(extras) == 1 else " Parallel contributions—"
            names = " and ".join(f"{e['title']} ({e.get('year', '')})" for e in extras)
            addendum = "—reinforced" if len(extras) > 1 else "reinforced"
            p1_parts.append(f"{conj}{names} {addendum} the foundational challenges in this space.")
        paragraphs.append("".join(p1_parts))

    # ── Paragraph 2: mid-period (if exists) ──────────────────────────
    if mid_papers:
        mp = top(mid_papers, 4)
        era_range = f"{early_papers[-1].get('year', min_yr) + 1 if early_papers else min_yr + 1}–{mid_papers[-1].get('year', '') if mid_papers else ''}"
        p2_parts = [f"A productive wave of {venue_short} work from {era_range} deepened the area."]
        if mp:
            p2_parts.append(f" {cite(mp[0])} advanced the field by demonstrating {kc(mp[0], 120)}.")
        if len(mp) > 1:
            others = ", ".join(f"{e['title']} ({e.get('year', '')})" for e in mp[1:3])
            p2_parts.append(f" Other strong contributions included {others}, broadening the space of techniques and targets.")
        paragraphs.append("".join(p2_parts))

    # ── Paragraph 3: late / recent work ──────────────────────────────
    if late_papers:
        lp = top(late_papers, 3)
        era_start = (late_papers[0].get("year") or max_yr - 2) if late_papers else max_yr - 2
        p3_parts = [f"The most recent {venue_short} contributions (from {era_start} onward) reflect a maturing field that pushes into harder targets and broader threat models."]
        if lp:
            p3_parts.append(f" {cite(lp[0])} exemplified this trend by tackling {kc(lp[0], 120)}.")
        if len(lp) > 1:
            others = " and ".join(f"{e['title']} ({e.get('year', '')})" for e in lp[1:3])
            p3_parts.append(f" Similarly, {others} show how the community continues to scale and adapt its methods.")
        paragraphs.append("".join(p3_parts))
    elif not mid_papers and len(early_papers) > 3:
        # No split but enough papers for a follow-up paragraph
        remaining = top([p for p in early_papers if p not in top(early_papers, 2)], 3)
        if remaining:
            p2_parts = [f"Additional {venue_short} work in this period extended these foundations."]
            names = ", ".join(f"{e['title']} ({e.get('year', '')})" for e in remaining[:3])
            p2_parts.append(f" {names} each contributed new techniques or targets to the evolving body of {domain} research at {venue_short}.")
            paragraphs.append("".join(p2_parts))

    return "\n\n".join(paragraphs)


def select_milestones(papers: list[dict], n: int = 7) -> list[dict]:
    if not papers:
        return []

    # Sort by year
    by_year: dict[int, list[dict]] = {}
    for p in papers:
        yr = p.get("year") or 0
        by_year.setdefault(yr, []).append(p)

    years = sorted(by_year.keys())
    if not years:
        return []

    chosen: list[dict] = []
    chosen_ids: set[str] = set()

    def add(p: dict) -> bool:
        pid = p.get("id", "")
        if pid and pid not in chosen_ids:
            chosen.append(p)
            chosen_ids.add(pid)
            return True
        return False

    # Always include the earliest paper (timeline anchor)
    first_yr_papers = sorted(by_year[years[0]], key=lambda p: -(p.get("citationCount") or 0))
    if first_yr_papers:
        add(first_yr_papers[0])

    # Always include the most recent paper (current state anchor)
    last_yr_papers = sorted(by_year[years[-1]], key=lambda p: -(p.get("citationCount") or 0))
    if last_yr_papers:
        add(last_yr_papers[0])

    # Fill with most-cited papers from different years
    by_cites = sorted(papers, key=lambda p: -(p.get("citationCount") or 0))
    for p in by_cites:
        if len(chosen) >= n:
            break
        add(p)

    # Sort chronologically
    chosen.sort(key=lambda p: p.get("year") or 0)
    return chosen[:n]


def kc_note(p: dict, n: int = 90) -> str:
    raw = p.get("keyContribution") or p.get("tldr") or ""
    raw = raw.strip().rstrip(".")
    # lowercase first letter for use as a clause
    if raw:
        raw = raw[0].lower() + raw[1:]
    return shorten(raw, n) or "established an important contribution in this area"


def process_venue(venue_key: str, min_papers: int = 5) -> list[dict]:
    path = ASSETS / f"{venue_key}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    venue_short = VENUE_LONG.get(venue_key, venue_key.upper())

    # Index papers by topic
    by_topic: dict[str, list[dict]] = {}
    for p in data["papers"]:
        for s in p.get("topics", []):
            by_topic.setdefault(s, []).append(p)

    results: list[dict] = []
    qualifying_topics = [t for t in data["topics"] if t["count"] >= min_papers and t["slug"] != "uncategorized"]
    qualifying_topics.sort(key=lambda t: -t["count"])

    for t in qualifying_topics:
        slug = t["slug"]
        name = t["name"]
        papers = by_topic.get(slug, [])
        if len(papers) < min_papers:
            continue

        narrative = build_narrative(slug, name, papers, venue_short)
        milestones_raw = select_milestones(papers, n=7)
        milestones = [
            {
                "year": p.get("year"),
                "paperId": p.get("id", ""),
                "title": p.get("title", ""),
                "note": kc_note(p),
            }
            for p in milestones_raw
        ]

        results.append({
            "slug": slug,
            "name": name,
            "narrative": narrative,
            "milestones": milestones,
        })
        print(f"  [{venue_short}] {slug}: {len(papers)} papers, {len(milestones)} milestones")

    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", required=True, help="venue key: uss/ndss/sp/ccs")
    ap.add_argument("--min", type=int, default=5)
    ap.add_argument("--topics", default=None, help="comma-separated slug list to limit (optional)")
    args = ap.parse_args()

    BUILD.mkdir(parents=True, exist_ok=True)
    print(f"Processing {args.venue}...")
    results = process_venue(args.venue, args.min)

    if args.topics:
        wanted = set(args.topics.split(","))
        results = [r for r in results if r["slug"] in wanted]

    out = BUILD / f"narr-{args.venue}.json"
    out.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {len(results)} topics to {out}")


if __name__ == "__main__":
    main()
