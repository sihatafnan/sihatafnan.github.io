---
name: add-research
description: Add a new research entry to `_includes/research.html`. Use when the user says "add research", "new paper", "log my <project name> work", or mentions a submission to a venue (NeurIPS, MobiCom, S&P, USENIX, etc.). Captures venue + status (e.g. "Under review", "Accepted", "ArXiv") consistently with the resume's research section.
---

# Add a Research entry

The site's Research section lives in `_includes/research.html`. Follow the existing structure — do **not** invent new wrappers. The resume's "Research Experience" section in `Resume.pdf` is the canonical content style.

## Steps

1. Read `_includes/research.html` end-to-end to learn the current entry markup.
2. Collect from the user (or `Resume.pdf`):
   - **Project title** (e.g. `Security/Privacy of Robotics`, `Security of AR/VR Systems`)
   - **Description**: 3-5 sentences. Match the resume's voice — past tense for completed work, present continuous for in-progress (`Investigated…`, `Developing…`).
   - **Venue + status**: one of `Under review at <VENUE> <YEAR>`, `Accepted to <VENUE> <YEAR>`, `Published at <VENUE> <YEAR>`, `ArXiv`. If under review, name the venue exactly as the user wrote it.
   - **Optional project page / code / paper links**.
3. Insert the new entry at the **top** of the list inside the research section's main content column — research is reverse-chronological by status (in-progress / under review first, then published).
4. Keep the surrounding `<div class="row">` / `<div class="card">` / `card-simple` structure that the file already uses. If the file uses a different wrapper than experience.html, mirror **that** file's pattern, not experience's.
5. Link formatting:
   - External links: `target="_blank" rel="noopener"`.
   - Code / Paper / Project page: render as `[Code]`, `[Paper]`, `[Project Page]` link chips (match how `projects.html` renders `[Code]` links).
6. Status line: render in bold, e.g. `<strong>Status:</strong> Under review at NeurIPS 2026`.

## Source-of-truth check

The resume currently lists these in-progress / under-review items:

- **UNVEIL** — Security/Privacy of Robotics → Under review at NeurIPS 2026 (page: `https://project-unveil.github.io/`)
- **AR/VR acoustic attack** — Security of AR/VR Systems → Under review at MobiCom 2026
- **AV-VR CARLA framework** — Autonomous Vehicle Security → Under review at IEEE S&P 2027
- **LogShield** — LLM-Based Threat Detection → ArXiv

If the site is missing any of the above, surface the gap.

## After inserting

- 1-line summary: `Added <title> (<status>) to research.html`.
- Don't run jekyll automatically — offer it.
