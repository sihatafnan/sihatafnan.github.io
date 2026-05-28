---
name: add-experience
description: Add a new entry to the Professional Experience section (`_includes/experience.html`). Use when the user says "add experience", "I started a new job/TA position", "log my time as <role>", etc. Copies an existing `card-simple` entry as the template and inserts above the older ones (newest first).
---

# Add an Experience entry

`_includes/experience.html` lists professional roles as `<div class="card-simple">` blocks under `<div class="col-12 col-lg-8">`. Newest role is first.

## Steps

1. Read the whole file so the most recent existing entry can serve as the template.
2. Ask the user (or infer from context / `Resume.pdf`) for:
   - Role title (e.g. `Teaching Assistant`)
   - Org name + URL (e.g. `University of California, Irvine`, `https://uci.edu`)
   - Optional sub-line (e.g. department / school) — match how nearby entries split this.
   - Date range, formatted like the surrounding entries: `"Sept 2024 - Present"` or `"June, 2023 - August, 2024."` (match the file's existing style).
   - One short description paragraph. If multiple sub-items (e.g. courses taught), use a `<ul>` only if a nearby entry already does — otherwise keep prose.
3. Insert the new `<div class="card-simple">…</div>` immediately after the opening `<div class="col-12 col-lg-8">` so it renders first.
4. Preserve every existing class (`card-simple`, `article-title`, `article-header`, `article-metadata`, `article-date`, `middot-divider`, `pub-publication`, `article-style`).
5. External org links: `<a href="…" target="_blank" rel="noopener">…</a>`.

## Template (copy verbatim, swap content)

```html
<div class="card-simple">
    <h3 class="article-title mb-1 mt-3">
        ROLE_TITLE
    </h3>
    <div>
        <span class="article-header"><a href="ORG_URL" target="_blank" rel="noopener">ORG_NAME</a></span>
    </div>
    <div class="article-metadata">
        <span class="article-date">
            DATE_RANGE.
        </span>
        <span class="middot-divider"></span>
    </div>
    <div class="article-style">
        <p>ONE_SENTENCE_DESCRIPTION</p>
    </div>
</div>
```

## After inserting

- Show a 1-line summary: `Added <role> @ <org> to experience.html`.
- If the resume lists this role differently (e.g. it's already on `Resume.pdf` with different dates), flag the mismatch.
- Don't commit unless asked.
