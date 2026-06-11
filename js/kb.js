/* Knowledge-base front-end for the Big-Four security conference pages.
   Loads /assets/kb/<venue>.json, indexes it with Fuse.js, and renders a
   searchable, topic-filterable list with per-topic evolution timelines.
   Topic narratives (when available) load on demand from
   /assets/kb/topics/<slug>.json; otherwise a timeline is derived locally. */
(function () {
  "use strict";
  var KB = window.KB || {};
  var $ = function (id) { return document.getElementById(id); };
  var els = {
    stats: $("kb-stats"), search: $("kb-search"), clear: $("kb-clear"),
    sort: $("kb-sort"), topics: $("kb-topics"), results: $("kb-results"),
    count: $("kb-count"), empty: $("kb-empty"),
    panel: $("kb-topic-panel"), tName: $("kb-topic-name"), tDesc: $("kb-topic-desc"),
    tNarr: $("kb-topic-narrative"), timeline: $("kb-timeline"), tClose: $("kb-topic-close")
  };

  var papers = [], topics = [], topicMap = {}, fuse = null;
  var state = { q: "", topic: null, sort: "relevance" };
  var narrativeCache = {};

  fetch("/assets/kb/" + KB.venueKey + ".json")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function (e) {
      els.stats.innerHTML = '<span class="kb-muted">Knowledge base for ' +
        esc(KB.venueTitle) + ' is being generated &mdash; check back soon.</span>';
      console.error("KB load failed", e);
    });

  function init(data) {
    papers = (data.papers || []).map(function (p) { p._cites = p.citationCount || 0; return p; });
    topics = data.topics || [];
    topics.forEach(function (t) { topicMap[t.slug] = t; });
    renderStats(data);
    renderChips();
    buildFuse();
    wire();
    applyHash();
    render();
  }

  function renderStats(data) {
    var withDeep = papers.filter(function (p) { return p.depth === "deep"; }).length;
    var yrs = papers.map(function (p) { return p.year; }).filter(Boolean);
    var lo = Math.min.apply(null, yrs), hi = Math.max.apply(null, yrs);
    els.stats.innerHTML = "<b>" + papers.length + "</b> papers &middot; " +
      (isFinite(lo) ? lo + "&ndash;" + hi : "") + " &middot; <b>" + topics.length +
      "</b> research areas" + (withDeep ? " &middot; <b>" + withDeep + "</b> deep-read" : "");
  }

  function buildFuse() {
    fuse = new Fuse(papers, {
      includeScore: true, ignoreLocation: true, threshold: 0.34, minMatchCharLength: 2,
      keys: [
        { name: "title", weight: 0.42 },
        { name: "authors", weight: 0.12 },
        { name: "topicNames", weight: 0.16 },
        { name: "keyContribution", weight: 0.12 },
        { name: "abstract", weight: 0.1 },
        { name: "tldr", weight: 0.08 }
      ]
    });
  }

  function renderChips() {
    els.topics.innerHTML = "";
    topics.slice().sort(function (a, b) { return b.count - a.count; }).forEach(function (t) {
      var b = document.createElement("button");
      b.className = "kb-chip"; b.dataset.slug = t.slug;
      b.innerHTML = esc(t.name) + '<span class="kb-chip-n">' + t.count + "</span>";
      b.onclick = function () { toggleTopic(t.slug); };
      els.topics.appendChild(b);
    });
  }

  function current() {
    var list;
    if (state.q.trim()) {
      list = fuse.search(state.q).map(function (r) { return r.item; });
    } else {
      list = papers.slice();
    }
    if (state.topic) {
      list = list.filter(function (p) { return (p.topics || []).indexOf(state.topic) >= 0; });
    }
    var rel = state.sort === "relevance" && state.q.trim();
    if (!rel) {
      list.sort(function (a, b) {
        if (state.sort === "oldest") return a.year - b.year || b._cites - a._cites;
        if (state.sort === "newest") return b.year - a.year || b._cites - a._cites;
        return b._cites - a._cites || b.year - a.year; // citations default
      });
    }
    return list;
  }

  function render() {
    document.querySelectorAll(".kb-chip").forEach(function (c) {
      c.classList.toggle("active", c.dataset.slug === state.topic);
    });
    renderTopicPanel();
    var list = current();
    els.count.textContent = list.length + (list.length === 1 ? " paper" : " papers") +
      (state.topic ? " in " + (topicMap[state.topic] ? topicMap[state.topic].name : state.topic) : "") +
      (state.q.trim() ? ' matching "' + state.q.trim() + '"' : "");
    els.empty.hidden = list.length !== 0;
    els.results.innerHTML = "";
    var frag = document.createDocumentFragment();
    list.slice(0, 300).forEach(function (p) { frag.appendChild(card(p)); });
    els.results.appendChild(frag);
    if (list.length > 300) {
      var more = document.createElement("p");
      more.className = "kb-muted"; more.style.textAlign = "center"; more.style.marginTop = "16px";
      more.textContent = "Showing top 300 of " + list.length + " — refine your search to narrow.";
      els.results.appendChild(more);
    }
  }

  function card(p) {
    var el = document.createElement("article");
    el.className = "kb-card";
    var titleHtml = p.url
      ? '<a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a>"
      : esc(p.title);
    var deep = p.depth === "deep" ? '<span class="kb-deep-badge">deep read</span>' : "";
    var cites = (p.citationCount != null)
      ? '<span class="kb-cites"><i class="fas fa-quote-right"></i> ' + p.citationCount + " cites</span>" : "";
    var authors = (p.authors || []).slice(0, 4).join(", ") + ((p.authors || []).length > 4 ? " et al." : "");

    var contrib = p.keyContribution
      ? '<div class="kb-contrib"><b>Contribution:</b> ' + esc(p.keyContribution) +
        (p.threatModel ? '<br><b>Threat model:</b> ' + esc(p.threatModel) : "") +
        (p.depth === "deep" && p.lineage ? '<br><b>Builds on / improves:</b> ' + esc(p.lineage) : "") +
        "</div>"
      : "";
    var abs = p.abstract || p.tldr || "";
    var absHtml = abs ? '<div class="kb-abstract clamp">' + esc(abs) + "</div>" +
      '<button class="kb-more">Read more</button>' : "";

    var tags = (p.topics || []).map(function (s) {
      var name = topicMap[s] ? topicMap[s].name : s;
      return '<span class="kb-tag" data-slug="' + esc(s) + '">' + esc(name) + "</span>";
    }).join("");

    var links = [];
    if (p.pdf) links.push('<a href="' + esc(p.pdf) + '" target="_blank" rel="noopener"><i class="fas fa-file-pdf"></i> PDF</a>');
    if (p.url) links.push('<a href="' + esc(p.url) + '" target="_blank" rel="noopener"><i class="fas fa-external-link-alt"></i> Page</a>');
    if (p.doi) links.push('<a href="https://doi.org/' + esc(p.doi) + '" target="_blank" rel="noopener">DOI</a>');
    if (p.s2) links.push('<a href="https://www.semanticscholar.org/paper/' + esc(p.s2) + '" target="_blank" rel="noopener">Semantic Scholar</a>');

    el.innerHTML =
      '<div class="kb-card-top"><h3 class="kb-card-title">' + titleHtml + deep + "</h3>" +
      '<span class="kb-year">' + (p.year || "") + "</span></div>" +
      '<div class="kb-card-meta">' + esc(authors) + " &middot; " + esc(p.venue || KB.venueTitle) +
      (cites ? " &middot; " + cites : "") + "</div>" +
      contrib + absHtml +
      '<div class="kb-tags">' + tags + "</div>" +
      (links.length ? '<div class="kb-links">' + links.join("") + "</div>" : "");

    var moreBtn = el.querySelector(".kb-more");
    if (moreBtn) moreBtn.onclick = function () {
      var a = el.querySelector(".kb-abstract");
      a.classList.toggle("clamp");
      moreBtn.textContent = a.classList.contains("clamp") ? "Read more" : "Show less";
    };
    el.querySelectorAll(".kb-tag").forEach(function (t) {
      t.onclick = function () { toggleTopic(t.dataset.slug); window.scrollTo({ top: 0, behavior: "smooth" }); };
    });
    return el;
  }

  // ---- Topic panel: narrative + timeline -------------------------------
  function renderTopicPanel() {
    if (!state.topic) { els.panel.hidden = true; return; }
    var t = topicMap[state.topic] || { name: state.topic, description: "" };
    els.panel.hidden = false;
    els.tName.textContent = t.name;
    els.tDesc.textContent = t.description || "";
    els.tNarr.innerHTML = '<span class="kb-muted">Loading evolution&hellip;</span>';
    els.timeline.innerHTML = "";
    loadNarrative(state.topic).then(function (n) {
      if (state.topic !== t.slug) return; // topic changed during async load
      if (n && n.narrative) {
        els.tNarr.innerHTML = n.narrative.split(/\n\n+/).map(function (para) {
          return "<p>" + esc(para) + "</p>";
        }).join("");
      } else {
        els.tNarr.innerHTML = '<p class="kb-muted">A written evolution summary for this area is coming soon. ' +
          'The timeline below is derived from the most-cited and earliest papers.</p>';
      }
      renderTimeline(n);
    });
  }

  function loadNarrative(slug) {
    if (narrativeCache[slug] !== undefined) return Promise.resolve(narrativeCache[slug]);
    return fetch("/assets/kb/topics/" + slug + ".json")
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (n) { narrativeCache[slug] = n; return n; });
  }

  function renderTimeline(n) {
    var items;
    if (n && n.milestones && n.milestones.length) {
      items = n.milestones;
    } else {
      // Fallback: earliest paper + top-cited papers in this topic, ordered by year.
      var inTopic = papers.filter(function (p) { return (p.topics || []).indexOf(state.topic) >= 0; });
      var byCite = inTopic.slice().sort(function (a, b) { return b._cites - a._cites; }).slice(0, 7);
      var earliest = inTopic.slice().sort(function (a, b) { return a.year - b.year; })[0];
      if (earliest && byCite.indexOf(earliest) < 0) byCite.push(earliest);
      items = byCite.sort(function (a, b) { return a.year - b.year; }).map(function (p) {
        return { year: p.year, title: p.title, venue: p.venue, url: p.url,
                 note: p.tldr || (p.keyContribution || "") };
      });
    }
    els.timeline.innerHTML = "";
    items.forEach(function (m) {
      var li = document.createElement("li");
      var title = m.url ? '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.title) + "</a>" : esc(m.title);
      li.innerHTML = '<span class="kb-tl-year">' + (m.year || "") + "</span>" +
        (m.venue ? '<span class="kb-tl-venue">' + esc(m.venue) + "</span>" : "") +
        '<span class="kb-tl-title">' + title + "</span>" +
        (m.note ? '<span class="kb-tl-note">' + esc(m.note) + "</span>" : "");
      els.timeline.appendChild(li);
    });
  }

  // ---- State / events --------------------------------------------------
  function toggleTopic(slug) {
    state.topic = state.topic === slug ? null : slug;
    syncHash();
    render();
  }

  function wire() {
    var deb;
    els.search.addEventListener("input", function () {
      clearTimeout(deb);
      els.clear.hidden = !els.search.value;
      deb = setTimeout(function () { state.q = els.search.value; render(); }, 120);
    });
    els.clear.onclick = function () { els.search.value = ""; els.clear.hidden = true; state.q = ""; render(); els.search.focus(); };
    els.sort.onchange = function () { state.sort = els.sort.value; render(); };
    els.tClose.onclick = function () { state.topic = null; syncHash(); render(); };
    window.addEventListener("hashchange", function () { applyHash(); render(); });
  }

  function applyHash() {
    var m = (location.hash || "").match(/topic=([\w-]+)/);
    state.topic = m ? m[1] : null;
    var q = (location.hash || "").match(/q=([^&]+)/);
    if (q) { state.q = decodeURIComponent(q[1]); els.search.value = state.q; els.clear.hidden = !state.q; }
  }

  function syncHash() {
    location.hash = state.topic ? "topic=" + state.topic : "";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
})();
