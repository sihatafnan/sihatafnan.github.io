---
name: add-project
description: Add a new project to `_includes/projects.html`. Use when the user says "add project", "log <project> on the site", or mentions a project from `Resume.pdf` that isn't on the page yet. Uses the existing vertically-connected timeline card layout (the one with the badge dots and `border-right` connectors).
---

# Add a Project entry

`_includes/projects.html` renders projects as a vertical timeline. Each entry is a `<div class="row experience">` with two columns:

- `col-auto` — the badge dot + connector lines (`row h-50` above and below the badge)
- `col py-2` — the project card itself

Connector lines (`border-right` on the inner `col`) decide whether a vertical line is drawn above/below the badge. The **first** entry has no top connector; the **last** has no bottom connector. Middle entries have both.

## Steps

1. Read `_includes/projects.html` fully. Identify the first and last entries so you know which connectors to set.
2. Gather:
   - Project title (e.g. `LiDAR Scanner`)
   - 1-3 sentence description (resume-style)
   - Optional code/paper/project-page links
3. Decide insertion position:
   - **Newest project** → insert at the top. Drop the top connectors on the new entry and **add** top connectors to what was previously the first entry.
   - **Specific position** → adjust connectors on the neighbors so the timeline is unbroken.
4. Copy an existing middle entry as the template and edit only the title, description, and links.

## Template (middle position — has both top and bottom connector)

```html
<div class="row experience">
    <div class="col-auto text-center flex-column d-none d-sm-flex">
        <div class="row h-50">
            <div class="col border-right">&nbsp;</div>
            <div class="col">&nbsp;</div>
        </div>
        <div class="m-2">
            <span class="badge badge-pill border ">&nbsp;</span>
        </div>
        <div class="row h-50">
            <div class="col border-right">&nbsp;</div>
            <div class="col">&nbsp;</div>
        </div>
    </div>
    <div class="col py-2">
        <div class="card">
            <div class="card-body">
                <h4 class="card-title exp-title text-muted mt-0 mb-1">PROJECT_TITLE</h4>
                <div class="text-muted exp-meta">
                    <span class="middot-divider"></span>
                    <p>
                        ONE_TO_THREE_SENTENCE_DESCRIPTION<br>
                        <a href="LINK_URL" target="_blank" rel="noopener">[Code]</a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
```

For the **first** entry, change the top `row h-50` block to:
```html
<div class="row h-50">
    <div class="col ">&nbsp;</div>
    <div class="col">&nbsp;</div>
</div>
```
(no `border-right`).

For the **last** entry, the bottom `row h-50` mirrors that (drop `border-right`).

## Source-of-truth check

Projects on `Resume.pdf`: LiDAR Scanner, Flow Classification on Data Plane Using P4 Switch, Improving RTT & RTO (Peak-Hopper), Smart Stick for the Visually Impaired. If the site is missing any, mention it.

## After inserting

- Re-Read the file briefly to confirm the timeline connectors are continuous (no orphan dot, no double line). Mention if the connectors look off.
- 1-line summary: `Added <title> to projects.html at position <N>`.
