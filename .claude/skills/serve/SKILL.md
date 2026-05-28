---
name: serve
description: Start the local Jekyll dev server at http://127.0.0.1:4000 so the user can preview changes. Use when the user says "serve", "run jekyll", "preview the site", "open it locally". Runs in the background and returns the URL.
---

# Start the local Jekyll server

## Steps

1. Check `Gemfile.lock` exists. If not, run `bundle install` first (foreground, since the serve step depends on it).
2. Start `bundle exec jekyll serve` as a **background** Bash command (`run_in_background: true`). The server keeps running until killed.
3. Verify it's up with `curl -sI http://127.0.0.1:4000` (expect `HTTP/1.1 200 OK`). If port 4000 is busy, retry with `--port 4001` and report the new URL.
4. Reply with: `Serving at http://127.0.0.1:4000 — open in browser to preview.`

## Don't

- Don't try to `open` the URL automatically (the user may be on a different desktop or remote).
- Don't kill an existing background server without being asked — if port 4000 is busy, use 4001.
- Don't build (`jekyll build`) when the user just wanted a preview; `serve` does an incremental build automatically.

## If the build errors

Surface the `Liquid Exception` or `Error: ...` line verbatim with the file + line number, then suggest the most likely partial to inspect. Common causes: a renamed include in `index.html`, an unbalanced `{% if %}`, or a typo in front matter.
