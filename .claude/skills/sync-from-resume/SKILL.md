---
name: sync-from-resume
description: Compare every site section against `Resume.pdf` and report a punch list of mismatches — outdated titles, missing experiences/research/projects/awards, stale courses, typos. Use when the user says "sync the site with my CV", "check the site against my resume", or after they drop a new `Resume.pdf`. Read-only by default — produces a report, then asks before editing.
---

# Sync the site against `Resume.pdf`

`Resume.pdf` is the canonical source of owner facts. Site partials in `_includes/` drift between resume updates. This skill produces a diff-style report.

## Steps

1. Read `Resume.pdf` (use the `Read` tool — it handles PDFs natively).
2. For each section below, read the matching partial and compare. Don't edit anything yet.

| Resume section            | Site partial                  | What to check                                                              |
|---------------------------|-------------------------------|----------------------------------------------------------------------------|
| Header (name/email/role)  | `_includes/about.html`        | Name, current title ("PhD student" — not "Graduate Fellow"), email, links  |
| Education                 | `_includes/about.html`        | Both UCI + BUET entries, correct dates, correct degree names               |
| Graduate Courses at UCI   | `_includes/coursework.html`   | Every course on the resume appears; no stale undergrad-only courses        |
| Experience                | `_includes/experience.html`   | TA role at UCI (Sept 2024 – Present), BRAC Lecturer, Spectrum ML Engineer  |
| Research Experience       | `_includes/research.html`     | UNVEIL, AR/VR acoustic, AV-VR CARLA, LogShield — with correct status lines |
| Projects                  | `_includes/projects.html`     | LiDAR Scanner, P4 Flow Classification, Peak-Hopper, Smart Stick            |
| Academic Recognition      | `_includes/awards.html`       | UCI CS Research Fellowship, BUET Dean's List, BUET Merit List, Talentpool  |
| Contact                   | `_includes/contact.html`      | Email + location (Irvine, CA)                                              |

3. Produce a report in this format:

```
## Mismatches found

### about.html
- [outdated] Title says "Graduate Fellow at UC Irvine"; resume says "PhD in Computer Science"
- [missing] Resume lists email `sihata@uci.edu`; site links `sihatafnan24@gmail.com`

### research.html
- [missing] UNVEIL (NeurIPS 2026 under review) — not on site
- [missing] AR/VR acoustic attack (MobiCom 2026 under review) — not on site
...

### projects.html
- [ok] All four resume projects present
```

4. After delivering the report, ask: **"Want me to apply all of these, a subset, or just specific ones?"** Do not edit until the user picks.
5. When applying fixes, delegate per-section edits to the `site-editor` agent or the matching `add-*` skill so the markup conventions are preserved.

## What not to do

- Don't rewrite the whole partial when one line needs fixing — surgical edits only.
- Don't modify `Resume.pdf`.
- Don't change wording the user has explicitly customized (e.g. the hobbies sentence in `about.html`) unless asked.
