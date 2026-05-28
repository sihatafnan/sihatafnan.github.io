# sihatafnan.github.io

Personal academic website for **Sihat Afnan**, PhD student in Computer Science at UC Irvine. Built with Jekyll, served by GitHub Pages at the `main` branch.

## Owner snapshot (source: `Resume.pdf`)

- PhD in CS, **University of California, Irvine** (Sep 2024 – Present, GPA 3.97/4.00)
- B.Sc. CSE, **BUET** (Apr 2018 – Jun 2023, GPA 3.81/4.00)
- Email `sihata@uci.edu` · Irvine, CA · `github.com/sihatafnan`
- Research interests: **Systems Security, Network Security**, Robotics privacy, AR/VR security, AV security, LLM-based threat detection
- Current roles: TA at UCI (CS 130, ICS 33, ICS H32); previously Lecturer at BRAC University (CSE341/340/321/230) and ML Engineer at Spectrum Software & Consulting Ltd
- Active submissions: NeurIPS 2026 (UNVEIL), MobiCom 2026 (AR/VR acoustic attack), IEEE S&P 2027 (AV-VR sim); LogShield on ArXiv

When editing site content, prefer facts from `Resume.pdf` as the source of truth. Some existing HTML (e.g. `_includes/about.html`) is out of date relative to the resume — flag mismatches when you spot them.

## Repo layout

- `index.html` — Jekyll entry; only stitches `_includes/*.html` partials together. Edit the partials, not this file.
- `_includes/` — one partial per page section: `about`, `experience`, `research`, `coursework`, `projects`, `awards`, `usefullinks`, `contact`, plus `head`, `navigation`, `search`, `tail-scripts`, `footer`. **This is where ~all content edits happen.**
- `css/academic.css`, `js/` — theme assets (Academic / Bootstrap based). Avoid editing unless explicitly asked.
- `img/`, `admin/` — images (`admin/sihat.jpg` is the avatar; CV photo).
- `note/`, `notes.html` — notes section.
- `Gemfile` — just `gem "jekyll"`.
- `push.sh` — convenience wrapper around `git add . && git commit -m "$1" && git push` (relies on env vars `$remote`/`$branch`, which look unset — don't rely on it).
- `Resume.pdf` — current CV, source of truth for owner facts.

## Conventions

- All section partials follow the same Bootstrap card / `home-section` skeleton — when adding a new entry, **copy an existing entry in the same partial verbatim and swap the content** rather than hand-writing markup. Section-heading classes (`wg-about`, `wg-experience`, `wg-pages`) are theme hooks; preserve them.
- Dates: spell month and use comma + year, e.g. `Sept 2024 - Present`, `June, 2023 - August, 2024`. Match the surrounding entries.
- External links: include `target="_blank" rel="noopener"`.
- Don't add or remove sections from `index.html` without being asked; commented-out includes (e.g. `papers.html`) are intentional.

## Local development

```sh
bundle install            # first time
bundle exec jekyll serve  # http://127.0.0.1:4000
```

If `bundle` is missing: `gem install bundler jekyll`.

## Deploying

GitHub Pages auto-builds from `main`. Push to `main` and the live site updates within a minute or two — there is no separate build/deploy step.

## Editing checklist

When you make a content change:
1. Edit the relevant `_includes/*.html` partial.
2. Keep the wrapping `div`/`section` structure intact — the CSS depends on it.
3. If the resume has newer info that contradicts the page, mention it so the owner can decide.
4. Don't touch `Resume.pdf` from code — it's a binary asset the owner updates manually.
