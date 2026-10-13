/* app.js — the schemify workspace website.

   Shipped by scripts/schemify.py into <workspace>/site/; never edit that copy.
   Reads window.SCHEMIFY_STATE (site/data/state.js, written by `schemify.py build`)
   and window.SCHEMIFY_ACTIVITY (site/data/activity.js), renders six tabs, and
   collects the person's feedback in an outbox that is either POSTed to the
   local server (serve.py → schemify/inbox/pending/) or downloaded as a file.

   Works opened from disk (file://) and served over http: only classic scripts,
   no fetch() of local files, data re-read by <script> injection. Every piece of
   text from the state is inserted as a text node — sources can contain anything. */
(function () {
  "use strict";

  var lib = window.JsonSchemaDataDictionary;
  var S = window.SCHEMIFY_STATE;
  var ACT = window.SCHEMIFY_ACTIVITY || {};
  var X = {};                 // indexes over S
  var UI = { tab: "overview", qFilter: "waiting", evTab: "sources", dFilter: "review", dSearch: "", dictTable: null,
             openDrawer: null, findingsDraft: null };
  var CONN = { mode: location.protocol === "file:" ? "disk" : "checking", token: null };
  var POLL_MS = 4000;
  var TABS = [
    ["overview", "Overview"], ["questions", "Questions"], ["dictionary", "Dictionary"],
    ["skip-logic", "Skip logic"], ["evidence", "Sources & decisions"], ["data-check", "Data check"]
  ];

  // ------------------------------------------------------------------ DOM helpers
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v === null || v === undefined || v === false) return;
        if (k === "class") el.className = v;
        else if (k === "text") el.textContent = v;
        else if (k === "dataset") Object.keys(v).forEach(function (d) { el.dataset[d] = v[d]; });
        else if (k.slice(0, 2) === "on" && typeof v === "function") el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : String(v));
      });
    }
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function append(el, kid) {
    if (kid === null || kid === undefined || kid === false) return;
    if (Array.isArray(kid)) { kid.forEach(function (k) { append(el, k); }); return; }
    el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function chip(text, kind, title) { return h("span", { class: "sf-chip" + (kind ? " sf-chip-" + kind : ""), title: title || null }, text); }
  function btn(text, onclick, cls, attrs) {
    var a = Object.assign({ type: "button", class: "sf-btn" + (cls ? " " + cls : ""), onclick: onclick }, attrs || {});
    return h("button", a, text);
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  function timeAgo(iso) {
    if (!iso) return "";
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (isNaN(s)) return "";
    if (s < 60) return "just now";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    return Math.round(s / 86400) + " days ago";
  }
  function toast(msg, warn) {
    var box = $("#sf-toast");
    var t = h("div", { class: warn ? "sf-toast-warn" : null }, msg);
    box.appendChild(t);
    setTimeout(function () { t.remove(); }, 7000);
  }

  // ------------------------------------------------------------------ storage (per workspace, never required)
  function skey(k) { return "schemify:" + ((S && S.workspace && S.workspace.id) || "ws") + ":" + k; }
  function lsGet(k, d) { try { var v = localStorage.getItem(skey(k)); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(skey(k), JSON.stringify(v)); return true; } catch (e) { return false; } }

  // ------------------------------------------------------------------ indexes
  function reindex() {
    X.dec = new Map(); (S.decisions || []).forEach(function (d) { X.dec.set(d.id, d); });
    X.src = new Map(); (S.sources || []).forEach(function (s) { X.src.set(s.id, s); });
    X.rule = new Map(); (S.rules || []).forEach(function (r) { X.rule.set(r.id, r); });
    X.topic = new Map(); (S.topics || []).forEach(function (t) { X.topic.set(t.id, t); });
    X.table = new Map(); (S.tables || []).forEach(function (t) { X.table.set(t.name, t); });
    X.doc = new Map(); (S.schemas || []).forEach(function (d) { X.doc.set(d.path, d); });
    X.props = new Map(); X.byName = new Map();
    (S.topics || []).forEach(function (tp) {
      var doc = X.doc.get(tp.file);
      var props = doc && doc.schema && doc.schema.properties;
      if (!props || typeof props !== "object") return;
      Object.keys(props).forEach(function (name) {
        var key = tp.table + "." + name;
        X.props.set(key, { key: key, table: tp.table, topic: tp.id, name: name, schema: props[name] || {}, file: tp.file });
        if (!X.byName.has(name)) X.byName.set(name, []);
        X.byName.get(name).push(key);
      });
    });
    X.encoded = new Map();
    (S.encodedRules || []).forEach(function (r) { if (r.id) { if (!X.encoded.has(r.id)) X.encoded.set(r.id, []); X.encoded.get(r.id).push(r); } });
    X.stamp = S.quacSetId || String((S.schemas || []).length) + ":" + (S.generatedAt || "");
  }
  function unsureEffect(d) {            // the steward is the last person to ask: their "not sure" stays an open question
    var who = role() === "steward" ? "listed as an open question in the package README" : "marked for the data steward";
    return d.kind === "consent" ? "Treated as “not now”: nothing is enforced, and the rules stay " + who + "." :
      d.kind === "bulk" ? "The guesses stay as they are, " + who + "." :
      "Your agent uses its recommendation for now, " + who + ".";
  }
  function role() {
    var r = lsGet("role", null);
    if (r === "author" || r === "steward") return r;
    return (S.workspace.mode === "review") ? "steward" : "author";
  }
  function harnessDone() {
    var inv = S.workspace.invoke || "/schemify";
    return S.workspace.harness === "codex" ? inv + " done" : "done";
  }
  function continuePhrase() {
    var inv = S.workspace.invoke || "/schemify";
    return S.workspace.harness === "codex" ? "start your message with " + inv : "type " + inv;
  }

  // ------------------------------------------------------------------ the outbox
  var OB = null;
  function obLoad() {
    OB = lsGet("outbox", null) || {};
    ["answers", "confirms", "topics", "sources"].forEach(function (k) { if (!OB[k] || typeof OB[k] !== "object") OB[k] = {}; });
    ["comments", "notes", "datasets"].forEach(function (k) { if (!Array.isArray(OB[k])) OB[k] = []; });
    if (UI.alignmentDraft === undefined) UI.alignmentDraft = null;     // too big for storage; memory only
  }
  function obSave() { lsSet("outbox", OB); renderOutboxBar(); renderBadges(); }
  function emptyOutbox() { return { answers: {}, confirms: {}, comments: [], topics: {}, sources: {}, notes: [], datasets: [] }; }
  function draftReady(a) {            // "Something else" counts once it says what
    return !!a && (!!(a.choices && a.choices.length) || (a.choice && a.choice !== "other") || !!String(a.text || "").trim());
  }
  function readyAnswers() { return Object.keys(OB.answers).filter(function (id) { return draftReady(OB.answers[id]); }); }
  function obCount() {
    return readyAnswers().length + Object.keys(OB.confirms).length + OB.comments.length +
      Object.keys(OB.topics).length + Object.keys(OB.sources).length + OB.notes.length + OB.datasets.length + (UI.alignmentDraft ? 1 : 0);
  }
  function obItems() {
    var items = [];
    readyAnswers().forEach(function (id) { items.push(Object.assign({ kind: "answer", decision: id }, OB.answers[id])); });
    Object.keys(OB.confirms).forEach(function (id) {
      var nt = (OB.answers[id] || {}).note;
      items.push(Object.assign({ kind: "confirm", decision: id }, nt ? { note: nt } : {}));
    });
    OB.comments.forEach(function (c) { items.push({ kind: "comment", target: c.target, tags: c.tags || [], text: c.text || "" }); });
    Object.keys(OB.topics).forEach(function (id) { items.push(Object.assign({ kind: "topic", topic: id }, OB.topics[id])); });
    Object.keys(OB.sources).forEach(function (id) { items.push(Object.assign({ kind: "source", source: id }, OB.sources[id])); });
    OB.notes.forEach(function (n) { items.push({ kind: "note", text: n.text }); });
    OB.datasets.forEach(function (d) { items.push(Object.assign({ kind: "dataset" }, d)); });
    if (UI.alignmentDraft) items.push({ kind: "alignment", label: UI.alignmentDraft.label, note: UI.alignmentDraft.note, findings: UI.alignmentDraft.findings });
    return items;
  }
  function sentMarks() { return lsGet("sent", {}) || {}; }
  function markSent(items, subId) {
    var sent = sentMarks();
    items.forEach(function (it) {
      var k = it.kind === "answer" || it.kind === "confirm" ? "D:" + it.decision :
        it.kind === "topic" ? "T:" + it.topic : it.kind === "source" ? "S:" + it.source : null;
      if (k) sent[k] = { at: new Date().toISOString(), sub: subId };
    });
    lsSet("sent", sent);
  }
  function sentAfter(m, since) { return !!m && (!since || Date.parse(m.at) > Date.parse(since)); }
  function topicSent(t) {                 // a verdict counts for the presentation it answered, not a later one
    return sentAfter(sentMarks()["T:" + t.id], t.presentedAt);
  }
  function decisionSent(d) {              // likewise an answer, for the posting it answered: a re-posted question asks again
    return sentAfter(sentMarks()["D:" + d.id], d.askedAt);
  }
  function describeItem(it) {
    var d;
    if (it.kind === "answer") {
      d = X.dec.get(it.decision) || {};
      return "Answer to " + it.decision + ": " + (it.choice === "unsure" ? "not sure — use the recommendation, " + (role() === "steward" ? "listed as an open question" : "flag for the steward") :
        it.choice === "other" ? (it.text || "(something else)") : it.choices ? it.choices.map(function (c) { return optionLabel(d, c); }).join("; ") :
          optionLabel(d, it.choice) || it.text || it.choice) + (it.note ? " — note: " + it.note : "");
    }
    if (it.kind === "confirm") return "Looks right: " + it.decision + " — " + ((X.dec.get(it.decision) || {}).question || "") + (it.note ? " — note: " + it.note : "");
    if (it.kind === "comment") return "Comment on " + targetText(it.target) + ": " + ((it.tags || []).join(", ") + (it.text ? " " + it.text : ""));
    if (it.kind === "topic") return (it.verdict === "approve" ? "Topic looks right: " : "Changes requested on topic: ") + ((X.topic.get(it.topic) || {}).title || it.topic) + (it.text ? " — " + it.text : "");
    if (it.kind === "source") return (it.verdict === "approve" ? "Use web source " : "Do not use web source ") + it.source + " — " + ((X.src.get(it.source) || {}).title || "");
    if (it.kind === "note") return "Note: " + it.text;
    if (it.kind === "alignment") return "Data-check findings (no data): " + it.label;
    if (it.kind === "dataset") return it.withdraw ? "Stop your agent checking " + (datasetById(it.withdraw).label || it.withdraw) + " itself" :
      "Let your agent check “" + it.label + "” itself (" + BASIS[it.basis] + "): " + it.path;
    return it.kind;
  }
  function targetText(t) {
    if (!t) return "the work";
    if (t.type === "variable") return "variable " + t.name;
    if (t.type === "code") return "code " + t.code + " of " + t.name;
    return t.type + " " + (t.id || "");
  }
  function optionLabel(d, id) {
    var o = (d.options || []).filter(function (x) { return x.id === id; })[0];
    return o ? o.label : null;
  }

  // ------------------------------------------------------------------ connection and live updates
  function connect() {
    if (location.protocol === "file:") { CONN.mode = "disk"; renderStatus(); return; }
    fetch("api/session", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (j) {
      var was = CONN.mode;
      if (j && j.ok && j.workspace === S.workspace.id) { CONN.mode = "live"; CONN.token = j.token; }
      else CONN.mode = "offline";
      renderStatus();
      if (was !== CONN.mode) renderQuacCardAgain();
    }).catch(function () { var was = CONN.mode; CONN.mode = "offline"; renderStatus(); if (was !== "offline") renderQuacCardAgain(); });
  }
  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src + "?t=" + Date.now();
      s.onload = function () { s.remove(); resolve(); };
      s.onerror = function () { s.remove(); reject(new Error(src)); };
      document.head.appendChild(s);
    });
  }
  function poll() {
    loadScript("site/data/activity.js").then(function () {
      ACT = window.SCHEMIFY_ACTIVITY || {};
      renderActivity();
      quacTick();
      if (ACT.stateAt && S && ACT.stateAt !== S.generatedAt && ACT.stateAt > S.generatedAt) {
        return loadScript("site/data/state.js").then(function () {
          var fresh = window.SCHEMIFY_STATE;
          if (fresh && fresh.generatedAt !== S.generatedAt) {
            S = fresh; reindex(); renderAll(true);
            toast("Updated — your agent changed something.");
          }
        });
      }
    }).catch(function () { /* the next tick tries again */ }).then(function () { setTimeout(poll, POLL_MS); });
  }

  // ------------------------------------------------------------------ routing
  function go(hash) { if (location.hash !== "#" + hash) location.hash = hash; else route(); }
  function route() {
    var raw = decodeURIComponent((location.hash || "#overview").slice(1));
    var parts = raw.split("/");
    var tab = TABS.some(function (t) { return t[0] === parts[0]; }) ? parts[0] : "overview";
    UI.tab = tab;
    document.body.classList.toggle("sf-on-dictionary", tab === "dictionary");
    TABS.forEach(function (t) {
      var on = t[0] === tab;
      var b = $("#tab-" + t[0]);
      if (b) { b.setAttribute("aria-selected", on ? "true" : "false"); b.tabIndex = on ? 0 : -1; }
      var p = $("#panel-" + t[0]);
      if (p) p.hidden = !on;
    });
    if (tab === "dictionary") {
      renderDictionary();
      if (parts[1] === "topic" && parts[2]) setTimeout(function () { gotoTopic(parts[2]); }, 60);
      if (parts[1] === "var" && parts[2] && parts[3]) setTimeout(function () { gotoVariable(parts[2], parts[3], true); }, 60);
    }
    if (tab === "evidence" && (parts[1] === "sources" || parts[1] === "decisions" || parts[1] === "people")) { UI.evTab = parts[1]; renderEvidence(); }
    if (tab === "evidence" && parts[1] === "decision" && parts[2]) { UI.evTab = "decisions"; UI.dFilter = "all"; UI.dSearch = parts[2]; renderEvidence(); }
    if (tab === "data-check" && DT.pending) syncToyGrid(DT.pending[0], DT.pending[1]);
    if (tab === "skip-logic" && parts[1]) setTimeout(function () { var el = document.getElementById("rule-" + parts[1]); if (el) el.scrollIntoView({ block: "center" }); }, 60);
    window.scrollTo(0, 0);
  }
  function renderTabs() {
    var nav = clear($("#sf-tabs"));
    TABS.forEach(function (t) {
      nav.appendChild(h("button", {
        class: "sf-tab", id: "tab-" + t[0], role: "tab", "aria-controls": "panel-" + t[0],
        onclick: function () { go(t[0]); },
        onkeydown: function (e) {
          var i = TABS.findIndex(function (x) { return x[0] === t[0]; });
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            var j = (i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length;
            go(TABS[j][0]); $("#tab-" + TABS[j][0]).focus(); e.preventDefault();
          }
        }
      }, t[1], h("span", { class: "sf-badge", id: "badge-" + t[0], hidden: true })));
    });
  }
  function setBadge(tab, n, warn) {
    var b = $("#badge-" + tab);
    if (!b) return;
    b.hidden = !n;
    b.textContent = n || "";
    b.className = "sf-badge" + (warn ? " sf-badge-warn" : "");
  }
  function renderBadges() {
    setBadge("questions", waitingQuestions().length);
    setBadge("evidence", (S.sources || []).filter(function (s) { return s.status === "suggested" && !OB.sources[s.id]; }).length);
    setBadge("skip-logic", (S.rules || []).filter(function (r) { return r.evidence === "inferred" && r.status === "encoded" && needsReviewDecision(r.decision); }).length, true);
  }
  function needsReviewDecision(id) { var d = X.dec.get(id); return !!(d && d.needsReview); }

  // ------------------------------------------------------------------ header status
  function renderStatus() {
    renderOutboxBar();                       // its button says send or save by the connection
    var box = clear($("#sf-status"));
    var label = { live: "Connected to your agent", offline: "Not connected — answers are kept in this browser",
                  disk: "Opened from disk — answers are kept in this browser", checking: "Connecting…" }[CONN.mode];
    var dot = { live: "sf-dot-ok", offline: "sf-dot-warn", disk: "sf-dot-accent", checking: "" }[CONN.mode];
    box.appendChild(h("span", { class: "sf-conn", title: CONN.mode === "live" ? "Your answers go straight to the agent's inbox."
      : "When your agent runs, it serves this page at a local address; there, answers go straight to it. Here, you can download them as a file." },
      h("span", { class: "sf-dot " + dot }), label));
    var sel = h("select", { class: "sf-select", "aria-label": "Answering as", onchange: function (e) { lsSet("role", e.target.value); renderAll(); } },
      h("option", { value: "author", selected: role() === "author" }, "Answering as: author"),
      h("option", { value: "steward", selected: role() === "steward" }, "Answering as: data steward"));
    box.appendChild(sel);
    box.appendChild(btn("✎ Note to your agent", openNote, "sf-btn-sm"));
  }
  function renderActivity() {
    var el = $("#sf-activity");
    if (!el) return;
    clear(el);
    var fresh = ACT.at && (Date.now() - new Date(ACT.at).getTime()) < 20 * 60 * 1000;
    el.appendChild(h("span", { class: "sf-pulse" + (fresh ? "" : " sf-idle"), "aria-hidden": "true" }));
    if (fresh && ACT.text) el.appendChild(h("div", null, h("strong", null, "Your agent is working: "), ACT.text, " ", h("span", { class: "sf-muted sf-small" }, "· " + timeAgo(ACT.at))));
    else {
      var last = (S.log || []).filter(function (l) { return l.summary; }).slice(-1)[0];
      el.appendChild(h("div", null, h("strong", null, "Your agent is not working right now."), " ",
        last && last.next && last.next !== "done" ? h("span", { class: "sf-muted" }, "Next time it will: " + last.next) : null));
    }
    var gen = $("#sf-generated");
    if (gen) gen.textContent = " · page data from " + fmtDate(S.generatedAt);
  }

  // ------------------------------------------------------------------ shared vocabularies
  var TOPIC_STATUS = {
    "planned": ["Not started", "outline"], "drafted": ["Drafted", null], "tested": ["Tested on toy data", "accent"],
    "in-review": ["Ready for your review", "warn"], "changes-requested": ["Changes requested", "bad"], "confirmed": ["Confirmed ✓", "ok"]
  };
  var KIND_LABEL = {
    conflict: ["Sources disagree", "bad"], gap: ["Not in the sources", "warn"], ambiguity: ["Unclear in the source", "warn"],
    guess: ["Agent's guess", "warn"], rule: ["Skip logic", "accent"], consent: ["Skip logic", "accent"],
    structure: ["How the data is organised", "accent"], convention: ["Package-wide choice", "accent"],
    interview: ["About you", null], knowledge: ["What you told the agent", "ok"], alignment: ["Real-data finding", "bad"],
    bulk: ["Several guesses at once", "warn"], feedback: ["Your feedback", "ok"]
  };
  function topicChip(status) { var s = TOPIC_STATUS[status] || [status, null]; return chip(s[0], s[1]); }
  function kindChip(kind) { var k = KIND_LABEL[kind] || [kind || "question", null]; return chip(k[0], k[1]); }
  function byLabel(by) { return { author: "the author", steward: "the data steward", agent: "your agent" }[by] || by || ""; }

  function waitingQuestions() {
    var r = role(), out = [];
    (S.batches || []).forEach(function (b) {
      if (b.withdrawn) return;
      if (b.to && b.to !== "any" && b.to !== r) return;       // the other person's batches stay folded on the Questions tab
      (b.items || []).forEach(function (id) {
        var d = X.dec.get(id);
        if (!d || d.batch !== b.id) return;
        if ((d.status === "asked" || d.status === "provisional" && d.needsReview) && !decisionSent(d)) out.push(d);
      });
    });
    return out;
  }

  // ------------------------------------------------------------------ overview
  function statusSentence() {
    if (S.workspace.mode === "review") return "The data steward's review: the first pass is done; only the questions that need specialist knowledge remain.";
    var cur = (S.phase || []).filter(function (p) { return p.state === "current"; })[0];
    var conf = (S.topics || []).filter(function (t) { return t.status === "confirmed"; }).length;
    if (!cur) return "Finished — every topic is confirmed.";
    if (cur.id === "build") return "Building the schemas topic by topic — " + conf + " of " + plural((S.topics || []).length, "topic") + " confirmed.";
    return { sources: "Reading your documents and looking for more about the study.", interview: "Getting to know you and the study.",
             plan: "Planning how to organise the variables.", skiplogic: "Checking the skip logic across all topics.",
             done: "Wrapping up — every topic is confirmed; the last questions and checks remain." }[cur.id] || cur.label;
  }
  function renderOverview() {
    var p = clear($("#panel-overview"));
    var topics = S.topics || [];
    var conf = topics.filter(function (t) { return t.status === "confirmed"; }).length;
    var v = (S.progress || {}).variables || {};
    var pct = topics.length ? Math.round(100 * conf / topics.length) : 0;
    p.appendChild(h("div", { class: "sf-card sf-hero" },
      h("h1", null, S.workspace.study || "Your study"),
      h("p", { class: "sf-status-line" }, statusSentence()),
      h("div", { class: "sf-progress", role: "progressbar", "aria-valuenow": pct, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": "Topics confirmed" },
        h("span", { style: "width:" + pct + "%" })),
      h("p", { class: "sf-muted sf-small" },
        topics.length ? conf + " of " + plural(topics.length, "topic") + " confirmed" : "No topics planned yet",
        v.total ? " · " + (v.inSchemas || 0) + " of " + plural(v.total, "variable") + " in the schemas" : "",
        " · " + plural((S.progress || {}).sessions || 0, "session") + " so far"),
      h("div", { class: "sf-activity", id: "sf-activity" })));
    var grid = h("div", { class: "sf-grid" });
    var left = h("div"), right = h("div");
    grid.appendChild(left); grid.appendChild(right); p.appendChild(grid);
    left.appendChild(yourTurnCard());
    left.appendChild(topicsCard());
    left.appendChild(logCard());
    right.appendChild(journeyCard());
    right.appendChild(checksCard());
    right.appendChild(continueCard());
    renderActivity();
  }
  function yourTurnCard() {
    var card = h("div", { class: "sf-card sf-turn" }, h("div", { class: "sf-card-head" }, h("h2", null, "Your turn")));
    var items = [];
    var q = waitingQuestions();
    if (q.length) items.push(["❓", plural(q.length, "question") + " need your answers",
      "About " + Math.max(1, Math.round(q.length * 0.8)) + " min. Each comes with what the documents say and a recommended answer.",
      "Answer questions", "questions"]);
    (S.topics || []).filter(function (t) { return t.status === "in-review" && !topicSent(t); }).forEach(function (t) {
      items.push(["🔎", "“" + t.title + "” is ready for your review",
        "Read its rows in the dictionary: names, labels, codes, ranges. Then say it looks right, or what is wrong.",
        "Review it", "dictionary/topic/" + t.id]);
    });
    var sug = (S.sources || []).filter(function (s) { return s.status === "suggested" && !OB.sources[s.id]; });
    if (sug.length) items.push(["🌐", (sug.length === 1 ? "A web page your agent found needs" : sug.length + " web pages your agent found need") + " your OK",
      "The agent uses information from the web only after you approve the source.", "Review sources", "evidence/sources"]);
    var n = obCount();
    if (n) items.push(["📤", plural(n, "answer or comment", "answers and comments") + " not sent yet",
      CONN.mode === "live" ? "Send them so your agent can use them." : "Download them as a file for your agent, or open this page from the agent's local address.",
      "Review & send", null]);
    if (!items.length) {
      card.appendChild(h("p", { class: "sf-muted" }, "Nothing needs you right now."));
      var guesses = (S.decisions || []).filter(function (d) { return d.needsReview; }).length;
      if (guesses) card.appendChild(h("p", { class: "sf-small" }, "Optional: your agent made " + plural(guesses, "guess", "guesses") +
        " where the documents were silent. ", h("a", { href: "#evidence/decisions" }, "Look them over"), " — each says why."));
      return card;
    }
    items.forEach(function (it) {
      card.appendChild(h("div", { class: "sf-turn-item" },
        h("span", { "aria-hidden": "true" }, it[0]),
        h("div", { class: "sf-turn-text" }, h("strong", null, it[1]), h("span", { class: "sf-muted sf-small" }, it[2])),
        btn(it[3], it[4] ? function () { go(it[4]); } : openSend, "sf-btn-primary sf-btn-sm")));
    });
    return card;
  }
  function topicsCard() {
    var card = h("div", { class: "sf-card" }, h("div", { class: "sf-card-head" }, h("h2", null, "Topics"),
      h("span", { class: "sf-muted sf-small" }, "Each topic is one group of variables, reviewed as a unit.")));
    var topics = S.topics || [];
    if (!topics.length) { card.appendChild(h("p", { class: "sf-empty" }, "Your agent proposes topics after reading the documents and talking with you.")); return card; }
    var tbody = h("tbody");
    topics.forEach(function (t) {
      tbody.appendChild(h("tr", { class: "sf-click", tabindex: 0, onclick: function () { go("dictionary/topic/" + t.id); },
        onkeydown: function (e) { if (e.key === "Enter") go("dictionary/topic/" + t.id); } },
        h("td", null, h("strong", null, t.title), (S.tables || []).length > 1 ? h("div", { class: "sf-muted sf-small" }, t.table) : null),
        h("td", null, t.variables || "—"),
        h("td", null, topicChip(t.status)),
        h("td", null, t.open ? chip(String(t.open), "accent", "open questions") : h("span", { class: "sf-muted" }, "—")),
        h("td", null, t.guesses ? chip(String(t.guesses), "warn", "agent guesses awaiting review") : h("span", { class: "sf-muted" }, "—"))));
    });
    card.appendChild(h("div", { class: "sf-table-wrap" }, h("table", { class: "sf-table" },
      h("thead", null, h("tr", null, h("th", null, "Topic"), h("th", null, "Variables"), h("th", null, "Status"), h("th", null, "Questions"), h("th", null, "Guesses"))),
      tbody)));
    return card;
  }
  function journeyCard() {
    var ol = h("ol", { class: "sf-steps" });
    (S.phase || []).forEach(function (s, i) {
      ol.appendChild(h("li", { class: "sf-step", dataset: { state: s.state } },
        h("span", { class: "sf-step-mark" }, s.state === "done" ? "✓" : String(i + 1)),
        h("span", null, s.label, s.state === "optional" ? h("span", { class: "sf-muted sf-small" }, " — optional") : null)));
    });
    return h("div", { class: "sf-card" }, h("h2", null, "The journey"), ol);
  }
  function checksCard() {
    var card = h("div", { class: "sf-card" }, h("h2", null, "Checks"));
    var c = S.checks;
    if (!c) { card.appendChild(h("p", { class: "sf-empty" }, "Checks start once the first topic is drafted: every schema file, every rule, and the toy data are tested automatically.")); return card; }
    var ul = h("ul", { class: "sf-health" });
    ul.appendChild(h("li", null, h("span", { class: "sf-dot " + (c.ok ? "sf-dot-ok" : "sf-dot-bad") }),
      h("span", null, c.ok ? "Everything your agent built passes its checks." : "Some checks fail — your agent fixes these before asking you anything.")));
    if (c.headline) ul.appendChild(h("li", null, h("span", { class: "sf-dot" }), h("span", { class: "sf-small" }, c.headline)));
    var guesses = (S.decisions || []).filter(function (d) { return d.needsReview; }).length;
    ul.appendChild(h("li", null, h("span", { class: "sf-dot " + (guesses ? "sf-dot-warn" : "sf-dot-ok") }),
      h("span", null, guesses ? plural(guesses, "agent guess", "agent guesses") + " await a person's review — every one is listed with its reason." :
        "Every fact traces to a document or to a person.")));
    card.appendChild(ul);
    card.appendChild(h("p", { class: "sf-muted sf-small" }, "Toy data is made up from your documents — never sampled from real data — and includes planted mistakes, so the checks prove each rule both accepts good rows and catches bad ones."));
    return card;
  }
  function continueCard() {
    var w = S.workspace;
    var card = h("div", { class: "sf-card" }, h("h2", null, "How to continue"));
    card.appendChild(h("p", { class: "sf-small" }, "Everything is saved in the folder ", h("code", null, w.folder || "schemify"),
      ". Large dictionaries take several sessions; nothing is lost between them."));
    card.appendChild(h("ol", { class: "sf-steps-numbered sf-small" },
      h("li", null, "Open your coding agent in ", h("code", null, w.parent || "the folder that contains it"), "."),
      h("li", null, "Then " + continuePhrase() + "."),
      h("li", null, "Your agent reads its notes, tells you where things stand, and carries on.")));
    card.appendChild(h("p", { class: "sf-small" }, CONN.mode === "live" ? "Keep this page open — it updates as your agent works." :
      "To see live updates and send answers in one click, open the address your agent gives you (it starts a small local server)."));
    card.appendChild(h("details", { class: "sf-small" }, h("summary", null, "Have the data steward review it"),
      h("p", null, "When the first pass is done, ask your agent to “prepare this for review by our data steward”. It packs this folder into a zip and writes the steward's instructions. The steward then answers only the questions that need their knowledge.")));
    return card;
  }
  function logCard() {
    var card = h("div", { class: "sf-card" }, h("h2", null, "Recent sessions"));
    var log = (S.log || []).filter(function (l) { return l.summary; }).slice(-5).reverse();
    if (!log.length) { card.appendChild(h("p", { class: "sf-empty" }, "The first session is under way.")); return card; }
    var ul = h("ul", { class: "sf-log" });
    log.forEach(function (l) {
      ul.appendChild(h("li", null, h("div", { class: "sf-muted sf-small" }, fmtDate(l.at || l.startedAt)),
        h("div", null, l.summary), l.next && l.next !== "done" ? h("div", { class: "sf-small" }, h("strong", null, "Next: "), l.next) : null));
    });
    card.appendChild(ul);
    return card;
  }

  // ------------------------------------------------------------------ questions
  function evidenceList(d) {
    var ev = d.evidence || [];
    if (!ev.length) return null;
    return h("div", { class: "sf-evidence" }, ev.map(function (e) {
      return h("div", { class: "sf-quote" }, h("cite", null, refText(e.ref)), e.quote ? h("q", null, e.quote) : null);
    }));
  }
  function refText(ref) {
    if (!ref) return "";
    var m = /^(S\d{2,})(?::(.+))?$/.exec(ref);
    if (m) {
      var s = X.src.get(m[1]);
      return (s ? s.title : m[1]) + (m[2] ? " — " + m[2] : "") + (s && s.kind === "web" ? " (web)" : "");
    }
    if (/^A\d{2,}$/.test(ref)) {
      var run = (S.alignment || []).filter(function (a) { return a.id === ref; })[0];
      return "Your data check " + ref + (run ? " (" + (run.label || "dataset") + ", " + fmtDate(run.at) + ")" : "");
    }
    var d = X.dec.get(ref);
    return d ? ref + " — " + (d.question || "") : ref;
  }
  function renderQuestions() {
    var p = clear($("#panel-questions"));
    p.appendChild(h("h1", null, "Questions"));
    p.appendChild(h("p", { class: "sf-lede" }, "Your agent asks only what the documents cannot settle. Each question shows what the sources say and a recommended answer — pick it, pick another, or say you are not sure: the agent then uses its recommendation for now and " + (role() === "steward" ? "lists it as an open question." : "marks it for the data steward.")));
    var filters = h("div", { class: "sf-filters", role: "group", "aria-label": "Show" });
    [["waiting", "Waiting for you"], ["answered", "Answered"], ["all", "All"]].forEach(function (f) {
      filters.appendChild(h("button", { type: "button", class: "sf-filter", "aria-pressed": UI.qFilter === f[0] ? "true" : "false",
        onclick: function () { UI.qFilter = f[0]; renderQuestions(); } }, f[1]));
    });
    p.appendChild(filters);
    var shown = 0, r = role();
    var batches = (S.batches || []).filter(function (b) { return !b.withdrawn; }).slice().sort(function (a, b) { return (a.postedAt || "").localeCompare(b.postedAt || ""); });
    var mine = batches.filter(function (b) { return !b.to || b.to === "any" || b.to === r; });
    var others = batches.filter(function (b) { return mine.indexOf(b) < 0; });
    var othersBox = h("div");
    function renderBatch(b, into) {
      var items = (b.items || []).map(function (id) { return X.dec.get(id); }).filter(function (d) { return d && d.batch === b.id; });
      var waiting = items.filter(function (d) { return (d.status === "asked" || d.status === "provisional" && d.needsReview) && !decisionSent(d); });
      var list = UI.qFilter === "waiting" ? waiting : UI.qFilter === "answered" ? items.filter(function (d) { return waiting.indexOf(d) < 0; }) : items;
      if (!list.length) return 0;
      var head = h("div", { class: "sf-batch-head" }, h("h2", null, b.title || b.id),
        chip(b.to === "steward" ? "for the data steward" : b.to === "author" ? "for the author" : "for anyone", "outline"),
        h("span", { class: "sf-muted sf-small" }, "asked " + fmtDate(b.postedAt)));
      if (waiting.length && UI.qFilter !== "answered") {
        head.appendChild(h("span", { class: "sf-muted sf-small" }, answeredDraftCount(waiting) + " of " + waiting.length + " answered"));
        head.appendChild(btn("Accept all recommendations", function () { acceptAll(waiting); }, "sf-btn-sm"));
      }
      var sec = h("section", { class: "sf-batch" }, head);
      list.forEach(function (d, i) { sec.appendChild(questionCard(d, i + 1)); });
      into.appendChild(sec);
      return list.length;
    }
    mine.forEach(function (b) { shown += renderBatch(b, p) || 0; });
    var otherCount = 0;
    others.forEach(function (b) { otherCount += renderBatch(b, othersBox) || 0; });
    if (!shown) p.appendChild(h("div", { class: "sf-card" }, h("p", { class: "sf-empty" },
      UI.qFilter === "waiting" ? "No questions are waiting for you. Your agent posts new ones here — this page updates by itself." : "Nothing here yet.")));
    if (otherCount) p.appendChild(h("details", { class: "sf-card" }, h("summary", null,
      plural(otherCount, "question") + " addressed to " + (r === "steward" ? "the author" : "the data steward") +
      " — answer them only if you know (your answers are recorded as " + (r === "steward" ? "the data steward's" : "the author's") + ")"), othersBox));
  }
  function answeredDraftCount(list) {
    return list.filter(function (d) { return draftReady(OB.answers[d.id]) || OB.confirms[d.id]; }).length;
  }
  function acceptAll(list) {
    list.forEach(function (d) {
      if (draftReady(OB.answers[d.id]) || OB.confirms[d.id]) return;     // an answer the person chose stays
      if (d.status === "provisional") { OB.confirms[d.id] = true; keepNoteOnly(d.id); }
      else if (d.recommended) setAnswer(d, { choice: d.recommended, text: "" });
    });
    obSave(); renderQuestions();
    toast("Recommendations accepted — review them, then send.");
  }
  function setAnswer(d, patch) {         // a note alone is kept, and goes out with the answer or the "Looks right"
    var cur = Object.assign({}, OB.answers[d.id] || {}, patch);
    Object.keys(cur).forEach(function (k) { if (cur[k] === "" || cur[k] === null || (Array.isArray(cur[k]) && !cur[k].length)) delete cur[k]; });
    if (Object.keys(cur).length) OB.answers[d.id] = cur; else delete OB.answers[d.id];
    if (Object.keys(patch).some(function (k) { return k !== "note"; })) delete OB.confirms[d.id];
    obSave();
    var st = document.querySelector("#q-" + d.id + " .sf-state");      // typing does not redraw the card
    if (st) { var ds = draftState(d); st.textContent = ds[0]; st.className = "sf-state" + (ds[1] ? "" : " sf-muted"); }
  }
  function keepNoteOnly(id) {
    var nt = (OB.answers[id] || {}).note;
    if (nt) OB.answers[id] = { note: nt }; else delete OB.answers[id];
  }
  function draftState(d) {
    var a = OB.answers[d.id];
    if (OB.confirms[d.id]) return ["✓ Looks right — ready to send", true];
    if (draftReady(a)) return ["✓ Answered — ready to send", true];
    if (a && (a.choice || a.choices)) return ["Describe your answer to send it", false];
    if (a && a.note) return ["Choose an answer to send your note", false];
    return ["Not answered yet", false];
  }
  function questionCard(d, n) {
    var answered = !(d.status === "asked" || d.status === "provisional" && d.needsReview);
    var draft = OB.answers[d.id] || {};
    var card = h("article", { class: "sf-card sf-q" + (answered ? " sf-answered" : ""), id: "q-" + d.id });
    var top = h("div", { class: "sf-q-top" }, h("strong", null, "Q" + n), kindChip(d.kind), h("span", { class: "sf-mono" }, d.id));
    if (d.topic && X.topic.get(d.topic)) top.appendChild(h("a", { href: "#dictionary/topic/" + d.topic }, X.topic.get(d.topic).title));
    (d.targets || []).slice(0, 4).forEach(function (t) {
      var keys = X.byName.get(t) || [];
      top.appendChild(keys.length ? h("a", { href: "#dictionary/var/" + X.props.get(keys[0]).table + "/" + t }, h("code", null, t)) : h("code", null, t));
    });
    if (d.importance === "high") top.appendChild(chip("important", "bad"));
    card.appendChild(top);
    card.appendChild(h("div", { class: "sf-q-title" }, d.question || ""));
    if (d.context) card.appendChild(h("p", { class: "sf-q-context" }, d.context));
    var ev = evidenceList(d);
    if (ev) card.appendChild(ev);
    if (d.kind === "bulk" && (d.covers || []).length) {
      var ul = h("ul", { class: "sf-small" });
      d.covers.forEach(function (id) {
        var c = X.dec.get(id); if (!c) return;
        ul.appendChild(h("li", null, h("span", { class: "sf-mono" }, id + " "), (c.question || "") + " → ",
          h("strong", null, optionLabel(c, (c.agentDecision || {}).choice) || (c.agentDecision || {}).choice || ""),
          (c.agentDecision || {}).why ? h("span", { class: "sf-muted" }, " — " + c.agentDecision.why) : null));
      });
      card.appendChild(h("details", null, h("summary", null, "The " + plural(d.covers.length, "guess", "guesses")), ul));
    }
    if (d.kind === "consent" && (d.covers || []).length) {
      var rl = h("ul", { class: "sf-small" });
      d.covers.forEach(function (id) {
        var ru = X.rule.get(id); if (!ru) return;
        rl.appendChild(h("li", null, h("a", { href: "#skip-logic/" + id, class: "sf-mono" }, id), " " + (ru.reading || "")));
      });
      card.appendChild(h("details", { open: true }, h("summary", null, "The " + plural(d.covers.length, "rule") + " this asks about"), rl));
    }
    if (answered) {
      card.appendChild(answeredBlock(d));
      return card;
    }
    if (d.status === "provisional") {
      var ad = d.agentDecision || {};
      card.appendChild(h("p", null, h("strong", null, "Your agent chose: "), optionLabel(d, ad.choice) || ad.choice || "",
        ad.why ? h("span", { class: "sf-muted" }, " — " + ad.why) : null));
      var confirmed = !!OB.confirms[d.id];
      card.appendChild(h("div", { class: "sf-q-foot" },
        btn(confirmed ? "✓ Looks right (ready to send)" : "Looks right", function () {
          if (OB.confirms[d.id]) delete OB.confirms[d.id]; else { OB.confirms[d.id] = true; keepNoteOnly(d.id); }
          obSave(); renderQuestions();
        }, confirmed ? "sf-btn-primary sf-btn-sm" : "sf-btn-sm"),
        h("span", { class: "sf-muted sf-small" }, "or choose differently:")));
    }
    card.appendChild(optionsBlock(d, draft));
    var noteOpen = !!draft.note;
    var noteBox = h("textarea", { class: "sf-textarea", rows: 2, placeholder: "Optional: anything your agent should know about this answer",
      oninput: function (e) { setAnswer(d, { note: e.target.value }); } });
    noteBox.value = draft.note || "";
    var noteWrap = h("div", { hidden: !noteOpen }, noteBox);
    card.appendChild(h("div", { class: "sf-q-foot" },
      btn("Add a note", function () { noteWrap.hidden = false; noteBox.focus(); }, "sf-btn-quiet sf-btn-sm"),
      h("span", { class: "sf-state" + (draftState(d)[1] ? "" : " sf-muted") }, draftState(d)[0])));
    card.appendChild(noteWrap);
    return card;
  }
  function optionsBlock(d, draft) {
    var wrap = h("div", { class: "sf-options", role: d.input === "multi" ? "group" : "radiogroup", "aria-label": d.question || "Options" });
    var name = "opt-" + d.id;
    if (d.input === "text") {
      var ta = h("textarea", { class: "sf-textarea", placeholder: "Your answer", oninput: function (e) { setAnswer(d, { text: e.target.value, choice: e.target.value ? "other" : "" }); } });
      ta.value = draft.text || "";
      wrap.appendChild(ta);
      return wrap;
    }
    var multi = d.input === "multi";
    (d.options || []).forEach(function (o) {
      var picked = multi ? (draft.choices || []).indexOf(o.id) >= 0 : draft.choice === o.id;
      var input = h("input", { type: multi ? "checkbox" : "radio", name: name, value: o.id, checked: picked,
        onchange: function (e) {
          if (multi) {
            var set = (OB.answers[d.id] && OB.answers[d.id].choices || []).filter(function (x) { return x !== o.id; });
            if (e.target.checked) set.push(o.id);
            setAnswer(d, { choices: set, choice: "" });
          } else setAnswer(d, { choice: o.id, text: "" });
          renderQuestions(); var c = document.getElementById("q-" + d.id); if (c) c.scrollIntoView({ block: "nearest" });
        } });
      wrap.appendChild(h("label", { class: "sf-option" + (picked ? " sf-picked" : "") }, input,
        h("div", { class: "sf-option-body" },
          h("span", { class: "sf-option-label" }, o.label), d.recommended === o.id ? h("span", { class: "sf-rec" }, "★ Recommended") : null,
          o.effect ? h("div", { class: "sf-option-effect" }, o.effect) : null,
          d.recommended === o.id && d.why ? h("div", { class: "sf-why" }, "Why: " + d.why) : null)));
    });
    var otherPicked = draft.choice === "other";
    var otherText = h("input", { class: "sf-input", placeholder: "Describe the answer", value: draft.text || "",
      oninput: function (e) { setAnswer(d, { choice: "other", text: e.target.value }); } });
    wrap.appendChild(h("label", { class: "sf-option" + (otherPicked ? " sf-picked" : "") },
      h("input", { type: "radio", name: name, value: "other", checked: otherPicked,
        onchange: function () { setAnswer(d, { choice: "other", choices: [] }); renderQuestions(); var c = document.getElementById("q-" + d.id); if (c) { var i = c.querySelector(".sf-option .sf-input"); if (i) i.focus(); } } }),
      h("div", { class: "sf-option-body" }, h("span", { class: "sf-option-label" }, "Something else"), otherPicked ? otherText : null)));
    if (d.kind !== "interview") {
      var unsure = draft.choice === "unsure";
      wrap.appendChild(h("label", { class: "sf-option sf-option-unsure" + (unsure ? " sf-picked" : "") },
        h("input", { type: "radio", name: name, value: "unsure", checked: unsure, onchange: function () { setAnswer(d, { choice: "unsure", choices: [], text: "" }); renderQuestions(); } }),
        h("div", { class: "sf-option-body" }, h("span", { class: "sf-option-label" }, "I'm not sure"),
          h("div", { class: "sf-option-effect" }, unsureEffect(d)))));
    }
    return wrap;
  }
  function answeredBlock(d) {
    var a = d.answer || {}, ad = d.agentDecision || {};
    var dl = h("dl", { class: "sf-qa" });
    if (decisionSent(d) && (d.status === "asked" || d.status === "provisional")) {
      dl.appendChild(h("dt", null, "Status")); dl.appendChild(h("dd", null, chip("Sent — your agent will pick it up", "accent")));
      return dl;
    }
    if (d.status === "answered") {
      dl.appendChild(h("dt", null, "Answer"));
      dl.appendChild(h("dd", null, a.choices ? a.choices.map(function (c) { return optionLabel(d, c) || c; }).join("; ") : (optionLabel(d, a.choice) || a.text || a.choice),
        h("span", { class: "sf-muted sf-small" }, " — " + byLabel(a.by) + ", " + fmtDate(a.at))));
      if (a.note) { dl.appendChild(h("dt", null, "Note")); dl.appendChild(h("dd", null, a.note)); }
    } else if (ad.choice !== undefined) {
      dl.appendChild(h("dt", null, "Decision"));
      dl.appendChild(h("dd", null, optionLabel(d, ad.choice) || ad.choice, h("span", { class: "sf-muted sf-small" }, " — your agent" +
        (d.status === "confirmed" ? ", confirmed by " + byLabel((d.confirmations || []).slice(-1)[0].by) : d.reviewer === "steward" ? ", flagged for the data steward" : ""))));
    }
    dl.appendChild(h("dt", null, "In the files"));
    dl.appendChild(h("dd", null, d.unapplied ? chip("Waiting for your agent to apply it", "accent") : chip("Applied ✓", "ok")));
    return dl;
  }

  // ------------------------------------------------------------------ dictionary
  var DICT = { tables: {}, el: null, mount: null, table: null, stamp: null, observer: null, semantic: false };
  var TRANSFORMERS_URL = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1";
  var ROW_CSS = ".sf-row-btn{display:inline-flex;align-items:center;gap:5px;margin-top:6px;font:600 11.5px/1.5 system-ui,sans-serif;" +
    "color:var(--dd-accent);background:transparent;border:1px solid var(--dd-border);border-radius:999px;padding:1px 9px;cursor:pointer}" +
    ".sf-row-btn:hover{background:var(--dd-accent-weak)}.sf-row-dot{width:7px;height:7px;border-radius:50%;background:#1a7f37;flex:none}" +
    ".sf-row-dot.sf-warn{background:#c58a00}.sf-row-dot.sf-open{background:#1f4fd8}.sf-row-dot.sf-fb{background:#7a43c2}" +
    "@media print{.sf-row-btn{display:none}}";

  function tableDocs() {
    return (S.schemas || []).filter(function (d) { return d.schema && typeof d.schema === "object"; })
      .map(function (d) { return { uri: d.uri, name: d.path, schema: d.schema }; });
  }
  function getTable(name) {
    if (!lib) return null;
    var cached = DICT.tables[name];
    if (cached && cached.stamp === X.stamp) return cached.table;
    var tb = X.table.get(name);
    var mother = tb && X.doc.get(tb.mother);
    if (!mother) return null;
    var t = lib.schemaDocumentsToTable(tableDocs(), { rootUri: mother.uri });
    hideProvenance(t);
    DICT.tables[name] = { stamp: X.stamp, table: t };
    return t;
  }
  function hideProvenance(node, seen) {     // each row's Details panel shows it in plain words instead
    seen = seen || new WeakSet();
    if (!node || typeof node !== "object" || seen.has(node)) return;
    seen.add(node);
    ["Additional information", "additionalInformation"].forEach(function (key) {
      var info = node[key];
      if (!info || typeof info !== "object" || Array.isArray(info)) return;
      delete info["x-provenance"];
      Object.keys(info).forEach(function (k) {           // x-unit → Unit: plain words, not keyword names
        if (k.indexOf("x-") !== 0) return;
        var plain = k.slice(2).replace(/-/g, " ");
        info[plain.charAt(0).toUpperCase() + plain.slice(1)] = info[k];
        delete info[k];
      });
      if (!Object.keys(info).length) node[key] = null;
    });
    Object.keys(node).forEach(function (k) { hideProvenance(node[k], seen); });
  }
  function varFlags(key) {
    var p = X.props.get(key);
    if (!p) return {};
    var prov = (p.schema && p.schema["x-provenance"]) || {};
    var guess = false;
    Object.keys(prov).forEach(function (f) {
      [].concat(prov[f]).forEach(function (r) { var d = X.dec.get(String(r).split(":")[0]); if (d && d.needsReview) guess = true; });
    });
    var open = (S.decisions || []).some(function (d) { return (d.targets || []).indexOf(p.name) >= 0 && (d.status === "open" || d.status === "asked"); });
    var fb = OB.comments.some(function (c) { return c.target && c.target.name === p.name; });
    return { guess: guess, open: open, fb: fb };
  }
  function decorate(root, table) {
    var rows = root.querySelectorAll("tr[data-dd-row]:not([data-sf])");
    rows.forEach(function (tr) {
      tr.setAttribute("data-sf", "1");
      var i = Number(tr.getAttribute("data-dd-row-index"));
      var row = table.rows[i];
      var cell = tr.querySelector(".dd-col-name") || tr.firstElementChild;
      if (!row || !cell) return;
      var name = row["Variable name"];
      if (row.__depth) return;                                  // nested fields share their parent's details
      var flags = varFlags(DICT.table + "." + name);
      var dot = document.createElement("span");
      dot.className = "sf-row-dot" + (flags.fb ? " sf-fb" : flags.open ? " sf-open" : flags.guess ? " sf-warn" : "");
      var b = document.createElement("button");
      b.type = "button"; b.className = "sf-row-btn"; b.dataset.sfVar = name;
      b.title = flags.guess ? "Includes an agent's guess awaiting review — see where each part comes from" :
        flags.open ? "A question about this variable is open" : "See where this comes from; comment";
      b.appendChild(dot); b.appendChild(document.createTextNode("Details"));
      var wrap = document.createElement("div"); wrap.appendChild(b);
      cell.appendChild(wrap);
    });
  }
  function mountDictionary(name, parent) {
    var table = getTable(name);
    if (!table) return null;
    if (DICT.el && DICT.table === name && DICT.stamp === X.stamp && DICT.semanticOn === DICT.semantic) { parent.appendChild(DICT.mount); return DICT.mount; }
    if (DICT.observer) DICT.observer.disconnect();
    DICT.mount = h("div", { class: "sf-dict-mount" });
    parent.appendChild(DICT.mount);           // the element builds its shadow root only once it is in the document
    DICT.table = name; DICT.stamp = X.stamp; DICT.semanticOn = DICT.semantic;
    var opts = { shadow: true, theme: "auto", expandCategories: true, pageSize: 100, includeExport: true };
    DICT.el = lib.renderDataDictionary(DICT.mount, table, opts);
    if (DICT.semantic) semanticOptions(name).then(function (sem) {
      if (!sem || DICT.table !== name) return;
      DICT.el.options = Object.assign({}, opts, { semanticSearch: sem });
    });
    var root = DICT.el.shadowRoot || DICT.el;
    try {
      var sheet = new CSSStyleSheet(); sheet.replaceSync(ROW_CSS);
      root.adoptedStyleSheets = (root.adoptedStyleSheets || []).concat([sheet]);
    } catch (e) { var st = document.createElement("style"); st.textContent = ROW_CSS; root.appendChild(st); }
    var run = function () { decorate(root, table); };
    DICT.observer = new MutationObserver(run);
    DICT.observer.observe(root, { childList: true, subtree: true });
    setTimeout(run, 0);
    root.addEventListener("click", function (e) {
      var t = e.composedPath ? e.composedPath()[0] : e.target;
      var b = t && t.closest ? t.closest(".sf-row-btn") : null;
      if (b) { e.preventDefault(); openVariable(name, b.dataset.sfVar); }
    });
    return DICT.mount;
  }
  function semanticOptions(table) {
    var cache = lib.createIndexedDbVectorCache({ dbName: "schemify:" + S.workspace.id + ":" + table });
    var status = function (st) { var el = $("#sf-sem-status"); if (el) el.textContent = st && st.state ? ({ loading: "loading the model…", indexing: "indexing…", ready: "ready", error: "unavailable" }[st.state] || st.state) : ""; };
    var mainThread = function () {
      return { embedder: lib.createTransformersEmbedder(function () { return import(TRANSFORMERS_URL); }, { device: "auto" }), cache: cache, onStatus: status };
    };
    if (location.protocol === "file:") return Promise.resolve(mainThread());   // browsers refuse workers to file:// pages
    return new Promise(function (resolve) {
      var done = false;
      var timer = setTimeout(function () { if (!done) { done = true; resolve(mainThread()); } }, 8000);
      try {
        var w = new Worker("site/embed-worker.js?transformers=" + encodeURIComponent(TRANSFORMERS_URL) + "&device=auto");
        Promise.resolve(lib.createWorkerEmbedder(w)).then(function (emb) {
          if (done) return; done = true; clearTimeout(timer);
          resolve({ embedder: emb, cache: cache, onStatus: status });
        }, function () { if (!done) { done = true; clearTimeout(timer); resolve(mainThread()); } });
      } catch (e) { done = true; clearTimeout(timer); resolve(mainThread()); }
    });
  }
  function shadowRootOf() { return DICT.el ? (DICT.el.shadowRoot || DICT.el) : null; }
  function gotoVariable(table, name, open) {
    if (UI.tab !== "dictionary") { go("dictionary/var/" + table + "/" + name); return; }
    if (DICT.table !== table) { UI.dictTable = table; renderDictionary(); }
    setTimeout(function () {
      var root = shadowRootOf(); if (!root) return;
      var host = root.querySelector("[data-dd-root]");
      if (host) {
        var b = document.createElement("button"); b.hidden = true; b.setAttribute("data-dd-goto", name);
        host.appendChild(b); b.click(); b.remove();
      }
      if (open) openVariable(table, name);
    }, 80);
  }
  function gotoTopic(tid) {
    var tp = X.topic.get(tid); if (!tp) return;
    if (DICT.table !== tp.table) { UI.dictTable = tp.table; renderDictionary(); }
    setTimeout(function () {
      var table = getTable(tp.table); var root = shadowRootOf(); if (!table || !root) return;
      var doc = X.doc.get(tp.file);
      var idx = table.categories.findIndex(function (c) { return c.source && doc && (c.source.uri === doc.uri || (c.source.name || "") === tp.file); });
      if (idx < 0) idx = table.categories.findIndex(function (c) { return c.title === ((doc && doc.schema && doc.schema.title) || tp.title); });
      var sec = idx >= 0 ? root.querySelector('[data-dd-category][data-dd-cat="' + idx + '"]') : null;
      if (!sec) return;
      if (sec.getAttribute("data-collapsed") === "true") { var tg = sec.querySelector("[data-dd-category-toggle]"); if (tg) tg.click(); }
      sec.scrollIntoView({ block: "start", behavior: "smooth" });
    }, 120);
  }
  function renderDictionary() {
    var p = $("#panel-dictionary");
    var keepMount = DICT.mount;
    clear(p);
    p.appendChild(h("h1", null, "Data dictionary"));
    p.appendChild(h("p", { class: "sf-lede" }, "The schemas as a data dictionary: every variable, its codes, ranges, and the skip patterns that set them. Use ",
      h("strong", null, "Details"), " on any row to see where each part comes from and to tell your agent what is wrong."));
    if (!lib) { p.appendChild(h("div", { class: "sf-card" }, "The dictionary library did not load (site/json-schema-data-dictionary.global.js). Ask your agent to run refresh-assets.")); return; }
    var tables = (S.tables || []).filter(function (t) { return X.doc.get(t.mother); });
    if (!tables.length) { p.appendChild(h("div", { class: "sf-card" }, h("p", { class: "sf-empty" }, "No schema yet — the dictionary appears as soon as the first topic is drafted."))); return; }
    if (!UI.dictTable || !tables.some(function (t) { return t.name === UI.dictTable; })) UI.dictTable = tables[0].name;
    var bar = h("div", { class: "sf-dict-toolbar" });
    if (tables.length > 1) {
      var seg = h("div", { class: "sf-seg", role: "group", "aria-label": "Table" });
      tables.forEach(function (t) { seg.appendChild(h("button", { type: "button", "aria-pressed": UI.dictTable === t.name ? "true" : "false",
        onclick: function () { UI.dictTable = t.name; renderDictionary(); } }, t.title || t.name)); });
      bar.appendChild(seg);
    }
    var tb = X.table.get(UI.dictTable);
    if (tb && tb.grain) bar.appendChild(h("span", { class: "sf-muted sf-small" }, tb.grain));
    var sem = h("label", { class: "sf-switch", title: "Also find variables by meaning. Downloads a small model once (about 50 MB from huggingface.co and cdn.jsdelivr.net); your schemas never leave this browser." },
      h("input", { type: "checkbox", checked: DICT.semantic, onchange: function (e) { DICT.semantic = e.target.checked; lsSet("semantic", DICT.semantic); renderDictionary(); } }),
      "Semantic search", h("span", { class: "sf-muted sf-small", id: "sf-sem-status" }));
    bar.appendChild(h("span", { style: "flex:1" }));
    bar.appendChild(sem);
    p.appendChild(bar);
    var strip = h("div", { class: "sf-topic-strip", role: "list" });
    (S.topics || []).filter(function (t) { return t.table === UI.dictTable; }).forEach(function (t) {
      var st = TOPIC_STATUS[t.status] || [t.status];
      strip.appendChild(h("button", { type: "button", class: "sf-topic-pill", role: "listitem", title: st[0], onclick: function () { gotoTopic(t.id); } },
        h("span", { class: "sf-dot " + ({ confirmed: "sf-dot-ok", "in-review": "sf-dot-warn", "changes-requested": "sf-dot-bad", tested: "sf-dot-accent" }[t.status] || "") }),
        t.title));
    });
    p.appendChild(strip);
    (S.topics || []).filter(function (t) { return t.table === UI.dictTable && t.status === "in-review" && !topicSent(t); }).forEach(function (t) {
      p.appendChild(reviewBanner(t));
    });
    if (keepMount && DICT.table === UI.dictTable && DICT.stamp === X.stamp && DICT.semanticOn === DICT.semantic) p.appendChild(keepMount);
    else mountDictionary(UI.dictTable, p);
  }
  function reviewBanner(t) {
    var v = OB.topics[t.id];
    var box = h("div", { class: "sf-card sf-review-banner" },
      h("div", { class: "sf-turn-text" }, h("strong", null, "“" + t.title + "” is ready for your review."),
        t.presentNote ? h("div", { class: "sf-small" }, "Your agent's note: " + t.presentNote) : null,
        h("div", { class: "sf-small sf-muted" }, "Read its rows: are the names, labels, codes, and ranges how you would describe the study? " +
          (t.guesses ? plural(t.guesses, "part is an agent's guess", "parts are agent's guesses") + " (amber dots)." : ""))));
    if (v) {
      box.appendChild(chip(v.verdict === "approve" ? "✓ Looks right — ready to send" : "Changes requested — ready to send", v.verdict === "approve" ? "ok" : "warn"));
      box.appendChild(btn("Undo", function () { delete OB.topics[t.id]; obSave(); renderDictionary(); }, "sf-btn-quiet sf-btn-sm"));
      return box;
    }
    var form = h("div", { hidden: true, style: "flex-basis:100%" });
    var ta = h("textarea", { class: "sf-textarea", placeholder: "What is wrong? (You can also comment on single variables with their Details button.)" });
    form.appendChild(ta);
    form.appendChild(h("div", { class: "sf-row", style: "margin-top:8px" }, btn("Add to outbox", function () {
      if (!ta.value.trim()) { ta.focus(); return; }
      OB.topics[t.id] = { verdict: "changes", text: ta.value.trim() }; obSave(); renderDictionary();
    }, "sf-btn-primary sf-btn-sm")));
    box.appendChild(btn("✓ Looks right", function () { OB.topics[t.id] = { verdict: "approve", hash: t.hash }; obSave(); renderDictionary(); toast("Noted — send it when you are ready."); }, "sf-btn-ok sf-btn-sm"));
    box.appendChild(btn("Something's wrong", function () { form.hidden = false; ta.focus(); }, "sf-btn-sm"));
    box.appendChild(form);
    return box;
  }

  // ------------------------------------------------------------------ drawer
  var FACETS = { "default": "Everything else", title: "Name and label", description: "Description", type: "Type",
    values: "Codes", sentinels: "Missing-value codes", minimum: "Lowest plausible value", maximum: "Highest plausible value",
    pattern: "Format", unit: "Unit", universe: "Who it applies to", derivation: "How it is derived" };
  function facetLabel(f) { return FACETS[f] || (f.indexOf("value:") === 0 ? "Code " + f.slice(6) : f); }
  function originChip(ref) {
    var id = String(ref).split(":")[0];
    if (id[0] === "S") {
      var s = X.src.get(id);
      return s && s.kind === "web" ? chip("Web source", "web") : chip("Your document", "accent");
    }
    var d = X.dec.get(id);
    if (!d) return chip("Unknown", "bad");
    if (d.status === "answered") return chip(d.answer && d.answer.by === "steward" ? "Data steward" : "Author", "ok");
    if (d.status === "confirmed") return chip("Agent, confirmed", "ok");
    if (d.status === "provisional") return chip("Agent's guess ⚑", "warn");
    if (d.status === "decided") return chip("Agent (mechanical)", "outline");
    return chip("Open question", "accent");
  }
  function citeNode(ref) {
    var id = String(ref).split(":")[0];
    if (id[0] === "S") return h("span", { class: "sf-cite" }, refText(ref));
    var d = X.dec.get(id);
    if (!d) return h("span", { class: "sf-cite" }, ref);
    var ans = d.status === "answered" ? (optionLabel(d, (d.answer || {}).choice) || (d.answer || {}).text || "") :
      d.agentDecision ? (optionLabel(d, d.agentDecision.choice) || d.agentDecision.choice) : "";
    return h("span", { class: "sf-cite" }, h("a", { href: "#evidence/decision/" + id }, id), " ", d.question || "",
      ans ? h("span", null, " → ", h("strong", null, String(ans))) : null,
      d.agentDecision && d.agentDecision.why && d.status !== "answered" ? h("div", { class: "sf-muted sf-small" }, "Why: " + d.agentDecision.why) : null);
  }
  function closeDrawer() {
    var s = $("#sf-scrim"), d = $("#sf-drawer");
    if (s) s.remove(); if (d) d.remove();
    UI.openDrawer = null;
  }
  function drawerShell(title, sub) {
    closeDrawer();
    var scrim = h("div", { class: "sf-scrim", id: "sf-scrim", onclick: closeDrawer });
    var body = h("div", { class: "sf-drawer-body" });
    var dr = h("aside", { class: "sf-drawer", id: "sf-drawer", role: "dialog", "aria-modal": "true", "aria-label": title },
      h("div", { class: "sf-drawer-head" }, h("div", null, h("h2", null, title), sub ? h("div", { class: "sf-muted sf-small" }, sub) : null),
        btn("Close ✕", closeDrawer, "sf-btn-quiet sf-close")), body);
    document.body.appendChild(scrim); document.body.appendChild(dr);
    dr.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });
    setTimeout(function () { var c = dr.querySelector(".sf-close"); if (c) c.focus(); }, 0);
    return body;
  }
  function openVariable(table, name) {
    var key = table + "." + name, p = X.props.get(key);
    var sch = (p && p.schema) || {};
    UI.openDrawer = { type: "variable", table: table, name: name };
    var body = drawerShell(name, (sch.title || "") + (p ? " · " + ((X.topic.get(p.topic) || {}).title || p.topic) : ""));
    var t = getTable(table);
    var row = t && t.rows.filter(function (r) { return r["Variable name"] === name; })[0];
    if (row) {
      var vv = (row["Valid values"] || []).map(function (v) {
        return h("li", null, v.kind === "measurement" ? (v.label || "") + " (measured)" : h("span", null, h("code", null, JSON.stringify(v.value)), " ", v.label || ""),
          v.kind === "sentinel" ? h("span", { class: "sf-muted" }, " — special code") : null,
          v.condition ? h("div", { class: "sf-muted sf-small" }, "set when " + v.condition) : null);
      });
      body.appendChild(h("section", null, h("h3", null, "In plain words"),
        h("p", null, splitDesc(row)), h("p", { class: "sf-small" }, h("strong", null, "Type: "), row["Data type"] || ""),
        vv.length ? h("ul", { class: "sf-small" }, vv) : null));
    }
    var prov = sch["x-provenance"] || {};
    var facets = Object.keys(prov).sort(function (a, b) { return a === "default" ? 1 : b === "default" ? -1 : 0; });
    var groups = [];                                   // facets citing the same thing share one line
    facets.forEach(function (f) {
      var refs = [].concat(prov[f]).map(String), key = refs.join("|");
      var g = groups.filter(function (x) { return x.key === key; })[0];
      if (g) g.facets.push(f); else groups.push({ key: key, refs: refs, facets: [f] });
    });
    var ul = h("ul", { class: "sf-prov" });
    groups.forEach(function (g) {
      var label = g.facets.map(facetLabel).join(" and ");
      ul.appendChild(h("li", null, h("span", { class: "sf-facet" }, label),
        h("div", null, g.refs.map(function (r, i) { return h("div", { style: i ? "margin-top:6px" : null }, originChip(r), " ", citeNode(r)); }))));
    });
    body.appendChild(h("section", null, h("h3", null, "Where this comes from"),
      facets.length ? ul : h("p", { class: "sf-muted" }, "No provenance recorded yet — your agent adds it as it drafts.")));
    var decs = (S.decisions || []).filter(function (d) { return (d.targets || []).indexOf(name) >= 0 && d.kind !== "feedback"; });
    if (decs.length) {
      var dl = h("ul", { class: "sf-small" });
      decs.forEach(function (d) {
        dl.appendChild(h("li", null, h("a", { href: "#evidence/decision/" + d.id }, d.id), " ", d.question || "", " ", chip(decisionStatusText(d), decisionStatusKind(d)),
          d.needsReview && !OB.confirms[d.id] ? btn("Looks right", function () { OB.confirms[d.id] = true; keepNoteOnly(d.id); obSave(); openVariable(table, name); }, "sf-btn-quiet sf-btn-sm") : null,
          OB.confirms[d.id] ? chip("✓ ready to send", "ok") : null));
      });
      body.appendChild(h("section", null, h("h3", null, "Questions and decisions"), dl));
    }
    var rules = (S.rules || []).filter(function (r) { return (r.gates || []).concat(r.targets || []).indexOf(name) >= 0; });
    if (rules.length) {
      var rl = h("ul", { class: "sf-small" });
      rules.forEach(function (r) { rl.appendChild(h("li", null, h("a", { href: "#skip-logic/" + r.id }, r.id), " ", r.reading || "", " ", chip(r.status, r.status === "encoded" ? "ok" : null))); });
      body.appendChild(h("section", null, h("h3", null, "Skip logic"), rl));
    }
    body.appendChild(feedbackForm({ type: "variable", table: table, name: name },
      ["Wrong label", "Wrong codes", "Missing code", "Wrong range", "Wrong skip logic", "Not in our data", "Looks right"]));
  }
  function splitDesc(row) {
    try { return lib.splitDescription(row).text; } catch (e) { return row.Description || ""; }
  }
  function decisionStatusText(d) {
    return { open: "not asked yet", asked: "waiting for an answer", answered: "answered", provisional: "awaiting review", confirmed: "confirmed",
             decided: "decided by your agent (mechanical — nothing to review)", unsure: "not sure — agent to decide", superseded: "replaced",
             cancelled: "withdrawn" }[d.status] || d.status;
  }
  function decisionStatusKind(d) {
    return { answered: "ok", confirmed: "ok", decided: "ok", provisional: "warn", asked: "accent", open: "accent", unsure: "warn" }[d.status] || null;
  }
  function feedbackForm(target, tags) {
    var picked = [];
    var ta = h("textarea", { class: "sf-textarea", placeholder: "Tell your agent what is wrong or missing — in your own words." });
    var tagBox = h("div", { class: "sf-tags" });
    tags.forEach(function (t) {
      var b = h("button", { type: "button", class: "sf-tag", "aria-pressed": "false", onclick: function () {
        var i = picked.indexOf(t); if (i >= 0) picked.splice(i, 1); else picked.push(t);
        b.setAttribute("aria-pressed", picked.indexOf(t) >= 0 ? "true" : "false");
      } }, t);
      tagBox.appendChild(b);
    });
    var existing = OB.comments.filter(function (c) { return JSON.stringify(c.target) === JSON.stringify(target); });
    var sec = h("section", null, h("h3", null, "Tell your agent"), tagBox, ta,
      h("div", { class: "sf-row", style: "margin-top:8px" }, btn("Add to outbox", function () {
        if (!ta.value.trim() && !picked.length) { ta.focus(); return; }
        OB.comments.push({ target: target, tags: picked.slice(), text: ta.value.trim() }); obSave();
        toast("Added to your outbox — send it when you are ready.");
        ta.value = ""; picked.length = 0; tagBox.querySelectorAll(".sf-tag").forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
        if (UI.openDrawer && UI.openDrawer.type === "variable") openVariable(UI.openDrawer.table, UI.openDrawer.name);
      }, "sf-btn-primary sf-btn-sm")));
    if (existing.length) sec.appendChild(h("p", { class: "sf-small sf-muted" }, plural(existing.length, "comment") + " on this already in your outbox."));
    return sec;
  }

  // ------------------------------------------------------------------ skip logic
  var EVIDENCE = { documented: ["Stated in a source", "accent"], implied: ["Implied by a source", "accent"],
    told: ["Told by a person", "ok"], inferred: ["Inferred by your agent ⚑", "warn"] };
  var RULE_STATUS = { encoded: ["In the schema", "ok"], waiting: ["Waiting for variables", null], suspected: ["Suspected — needs your choice", "warn"],
    deferred: ["Not now", "outline"], declined: ["Not included", "outline"], "not-expressible": ["Cannot be checked by JSON Schema", "outline"] };
  function ruleIdOf(text) { var m = /\bR\d{3,}\b/.exec(text || ""); return m ? m[0] : null; }
  function renderSkipLogic() {
    var p = clear($("#panel-skip-logic"));
    p.appendChild(h("h1", null, "Skip logic"));
    p.appendChild(h("p", { class: "sf-lede" }, "Skip patterns decide who was asked what. Each rule below is written into the schema so that a skipped question carrying a real answer — or an asked question marked “not applicable” — shows up as a mismatch. Rules your agent inferred without a source are marked ⚑ until a person confirms them."));
    var rules = S.rules || [];
    var counts = {};
    rules.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });
    var sus = rules.filter(function (r) { return r.status === "suspected"; });
    var consentWaiting = waitingQuestions().some(function (d) { return d.kind === "consent"; });
    if (sus.length && consentWaiting) p.appendChild(h("div", { class: "sf-card sf-turn" }, h("strong", null, "Your agent believes " + (sus.length === 1 ? "a skip pattern exists" : sus.length + " skip patterns exist") + " that your documents do not state."),
      h("p", { class: "sf-small" }, "It asks whether to include them (each marked for the data steward to confirm) in the Questions tab."),
      btn("Go to questions", function () { go("questions"); }, "sf-btn-sm")));
    var vmRules = [];
    (S.tables || []).forEach(function (tb) {
      var t = getTable(tb.name); if (!t) return;
      var vm; try { vm = lib.buildViewModel(t); } catch (e) { vm = null; }
      ((vm && vm.rules) || []).forEach(function (r) { vmRules.push({ table: tb.name, vm: r, id: ruleIdOf(r.description) }); });
    });
    var byId = new Map();
    vmRules.forEach(function (r) { var k = r.id || ("?" + byId.size); if (!byId.has(k)) byId.set(k, []); byId.get(k).push(r); });
    var encodedCard = h("div", { class: "sf-card" }, h("div", { class: "sf-card-head" }, h("h2", null, "In the schema"), chip(String(byId.size), "ok")));
    if (!byId.size) encodedCard.appendChild(h("p", { class: "sf-empty" }, "No rules are encoded yet."));
    var groups = new Map();
    byId.forEach(function (halves, id) {
      var gate = (halves[0].vm.triggers || [])[0] || "(other)";
      if (!groups.has(gate)) groups.set(gate, []);
      groups.get(gate).push([id, halves]);
    });
    groups.forEach(function (list, gate) {
      var keys = X.byName.get(gate) || [];
      var title = keys.length ? (X.props.get(keys[0]).schema.title || "") : "";
      var g = h("div", { class: "sf-gate" }, h("div", { class: "sf-gate-head" }, h("code", null, gate), h("span", { class: "sf-muted" }, title),
        keys.length ? h("a", { class: "sf-small", href: "#dictionary/var/" + X.props.get(keys[0]).table + "/" + gate }, "in the dictionary") : null));
      list.forEach(function (pair) { g.appendChild(ruleRow(pair[0], pair[1])); });
      encodedCard.appendChild(g);
    });
    p.appendChild(encodedCard);
    var others = rules.filter(function (r) { return r.status !== "encoded"; });
    if (others.length) {
      var oc = h("div", { class: "sf-card" }, h("div", { class: "sf-card-head" }, h("h2", null, "Not in the schema"), chip(String(others.length), "outline")));
      others.forEach(function (r) {
        var st = RULE_STATUS[r.status] || [r.status];
        var ev = EVIDENCE[r.evidence] || [r.evidence];
        oc.appendChild(h("div", { class: "sf-rule", id: "rule-" + r.id },
          h("div", null, h("div", { class: "sf-rule-reading" }, r.reading || ""),
            r.note ? h("div", { class: "sf-small sf-muted" }, r.note) : null,
            (r.waits_for || []).length ? h("div", { class: "sf-small sf-muted" }, "Waits for: " + r.waits_for.join(", ")) : null),
          h("div", { class: "sf-rule-actions" }, feedbackButton({ type: "rule", id: r.id }, "Comment")),
          h("div", { class: "sf-rule-meta" }, h("span", { class: "sf-mono" }, r.id), chip(st[0], st[1]), chip(ev[0], ev[1]),
            (r.refs || []).map(function (ref) { return h("span", null, refText(ref)); }))));
      });
      p.appendChild(oc);
    }
  }
  function ruleRow(id, halves) {
    var rec = X.rule.get(id) || {};
    var enc = (X.encoded.get(id) || [])[0] || {};
    var ev = EVIDENCE[rec.evidence] || ["Not in the ledger", "bad"];
    var reading = h("div", null);
    halves.forEach(function (hf) {
      reading.appendChild(h("div", { class: "sf-rule-reading" }, "If " + hf.vm.condition, h("span", { class: "sf-arrow" }, "→"),
        (hf.vm.effects || []).join("; ")));
    });
    var comment = halves.map(function (hf) { return hf.vm.description; }).filter(Boolean)[0];
    if (comment) reading.appendChild(h("div", { class: "sf-small sf-muted" }, comment));
    var actions = h("div", { class: "sf-rule-actions" });
    var dec = X.dec.get(rec.decision);
    if (rec.evidence === "inferred" && dec && dec.needsReview) {
      actions.appendChild(OB.confirms[dec.id] ? chip("✓ ready to send", "ok") :
        btn("Looks right", function () { OB.confirms[dec.id] = true; keepNoteOnly(dec.id); obSave(); renderSkipLogic(); }, "sf-btn-ok sf-btn-sm"));
    }
    actions.appendChild(feedbackButton({ type: "rule", id: id }, "Something's wrong"));
    var prov = enc.provenance || {};
    var cites = Object.keys(prov).map(function (f) { return [].concat(prov[f]).map(function (r) { return h("span", null, originChip(r), " ", refText(r)); }); });
    return h("div", { class: "sf-rule", id: "rule-" + id }, reading, actions,
      h("div", { class: "sf-rule-meta" }, h("span", { class: "sf-mono" }, id), chip(ev[0], ev[1]), cites,
        dec && dec.agentDecision && dec.agentDecision.why && rec.evidence === "inferred" ? h("span", null, "Why your agent thinks so: " + dec.agentDecision.why) : null));
  }
  function feedbackButton(target, label) {
    return btn(label, function () {
      var body = drawerShell(target.type === "rule" ? "Rule " + target.id : targetText(target), "Tell your agent");
      UI.openDrawer = { type: "feedback" };
      var r = target.type === "rule" ? X.rule.get(target.id) : null;
      if (r) body.appendChild(h("section", null, h("h3", null, "The rule"), h("p", null, r.reading || "")));
      body.appendChild(feedbackForm(target, ["Wrong condition", "Wrong variables", "Wrong code", "Not a real skip", "Looks right"]));
    }, "sf-btn-sm");
  }

  // ------------------------------------------------------------------ sources & decisions
  function renderEvidence() {
    var p = clear($("#panel-evidence"));
    p.appendChild(h("h1", null, "Sources & decisions"));
    p.appendChild(h("p", { class: "sf-lede" }, "Every name, code, range, and rule in the schemas comes from a source document, a web page you approved, an answer from you or the data steward — or a guess your agent made and marked for review. This is the full record."));
    var seg = h("div", { class: "sf-seg", role: "group", "aria-label": "Show" });
    [["sources", "Sources"], ["decisions", "Decisions"], ["people", "People"]].forEach(function (t) {
      seg.appendChild(h("button", { type: "button", "aria-pressed": UI.evTab === t[0] ? "true" : "false", onclick: function () { UI.evTab = t[0]; renderEvidence(); } }, t[1]));
    });
    p.appendChild(h("div", { class: "sf-row", style: "margin-bottom:14px" }, seg));
    if (UI.evTab === "sources") p.appendChild(sourcesView());
    else if (UI.evTab === "people") p.appendChild(peopleView());
    else p.appendChild(decisionsView());
  }
  function sourcesView() {
    var wrap = h("div");
    var src = S.sources || [];
    if (!src.length) return h("div", { class: "sf-card" }, h("p", { class: "sf-empty" }, "No sources registered yet."));
    src.forEach(function (s) {
      var st = { active: ["In use", "ok"], suggested: ["Found by your agent — needs your OK", "warn"], approved: ["Approved", "ok"],
                 rejected: ["Not used", "outline"], retired: ["Retired", "outline"] }[s.status] || [s.status];
      var where = s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, s.url) : s.path ? h("code", null, s.path) : null;
      var card = h("div", { class: "sf-card sf-source" }, h("span", { class: "sf-id" }, s.id),
        h("div", null, h("strong", null, s.title || ""), " ", chip(s.kind === "web" ? "Web" : "Document", s.kind === "web" ? "web" : "accent"),
          h("div", null, s.what || ""), where ? h("div", { class: "sf-small" }, where) : null,
          s.digest ? h("div", { class: "sf-small sf-muted" }, "Read and summarised" + (s.digest.variables ? " — " + plural(s.digest.variables, "variable") : "") +
            ((s.digest.verified || []).length ? "; spot-checked at " + s.digest.verified.join(", ") : "")) : null,
          (s.notes || []).length ? h("details", { class: "sf-small" }, h("summary", null, "Notes"), h("ul", null, s.notes.map(function (n) { return h("li", null, n); }))) : null),
        h("div", null, chip(st[0], st[1])));
      if (s.status === "suggested") {
        var v = OB.sources[s.id];
        card.appendChild(h("div", { style: "grid-column: 1 / -1", class: "sf-row" }, v ? chip(v.verdict === "approve" ? "✓ Use it — ready to send" : "✕ Don't use — ready to send", v.verdict === "approve" ? "ok" : "outline") : null,
          v ? btn("Undo", function () { delete OB.sources[s.id]; obSave(); renderEvidence(); }, "sf-btn-quiet sf-btn-sm") :
            [btn("Use it", function () { OB.sources[s.id] = { verdict: "approve" }; obSave(); renderEvidence(); }, "sf-btn-ok sf-btn-sm"),
             btn("Don't use it", function () { OB.sources[s.id] = { verdict: "reject" }; obSave(); renderEvidence(); }, "sf-btn-sm")]));
      }
      wrap.appendChild(card);
    });
    return wrap;
  }
  function peopleView() {
    var ppl = S.people || [];
    if (!ppl.length) return h("div", { class: "sf-card" }, h("p", { class: "sf-empty" }, "Recorded after the first interview."));
    return h("div", null, ppl.map(function (pp) {
      return h("div", { class: "sf-card" }, h("strong", null, pp.name || (pp.role === "steward" ? "The data steward" : "The author")), " ",
        chip(pp.role === "steward" ? "Data steward" : pp.role === "author" ? "Author" : (pp.role || ""), "outline"),
        pp.profile ? h("div", { class: "sf-small sf-muted" }, { steward: "Knows the study's data pipeline first-hand.", informed: "Knows the study well; defers to the steward on processing details.", limited: "Newer to the study; the agent fills gaps provisionally and flags them for the steward." }[pp.profile] || pp.profile) : null,
        (pp.knows || []).length ? h("div", { class: "sf-small" }, "Knows about: " + pp.knows.join(", ")) : null);
    }));
  }
  function decisionsView() {
    var wrap = h("div");
    var filters = h("div", { class: "sf-filters" });
    var all = (S.decisions || []).filter(function (d) { return d.kind !== "interview" || UI.dFilter === "all"; });
    var defs = [["review", "Agent guesses to review", function (d) { return d.needsReview; }],
                ["people", "Answered by people", function (d) { return d.status === "answered" && d.kind !== "feedback"; }],
                ["open", "Open", function (d) { return ["open", "asked", "unsure"].indexOf(d.status) >= 0; }],
                ["all", "All", function () { return true; }]];
    defs.forEach(function (f) {
      var n = all.filter(f[2]).length;
      filters.appendChild(h("button", { type: "button", class: "sf-filter", "aria-pressed": UI.dFilter === f[0] ? "true" : "false",
        onclick: function () { UI.dFilter = f[0]; renderEvidence(); } }, f[1] + " (" + n + ")"));
    });
    var search = h("input", { class: "sf-input", type: "search", placeholder: "Search decisions (a variable name, D014, a word)…", value: UI.dSearch || "",
      oninput: function (e) { UI.dSearch = e.target.value; clearTimeout(UI.dTimer); UI.dTimer = setTimeout(function () { renderEvidence(); var s = $("#panel-evidence input[type=search]"); if (s) { s.focus(); s.setSelectionRange(s.value.length, s.value.length); } }, 250); } });
    wrap.appendChild(filters);
    wrap.appendChild(h("div", { style: "margin-bottom:12px" }, search));
    var pred = defs.filter(function (f) { return f[0] === UI.dFilter; })[0][2];
    var q = (UI.dSearch || "").toLowerCase().trim();
    var list = all.filter(pred).filter(function (d) {
      if (!q) return true;
      return [d.id, d.question, d.context, (d.targets || []).join(" "), d.topic].join(" ").toLowerCase().indexOf(q) >= 0;
    });
    if (UI.dFilter === "review" && list.length) {
      var notYet = list.filter(function (d) { return !OB.confirms[d.id]; });
      if (notYet.length > 1) wrap.appendChild(h("div", { class: "sf-row", style: "margin-bottom:10px" },
        btn("Accept all " + notYet.length + " shown", function () { notYet.forEach(function (d) { OB.confirms[d.id] = true; keepNoteOnly(d.id); }); obSave(); renderEvidence(); }, "sf-btn-sm"),
        h("span", { class: "sf-muted sf-small" }, "Only if each looks right to you — anything you are unsure about is better left for the data steward.")));
    }
    if (!list.length) wrap.appendChild(h("div", { class: "sf-card" }, h("p", { class: "sf-empty" }, "Nothing here.")));
    list.slice(0, 300).forEach(function (d) { wrap.appendChild(decisionCard(d)); });
    if (list.length > 300) wrap.appendChild(h("p", { class: "sf-muted" }, "Showing 300 of " + list.length + " — search to narrow it down."));
    return wrap;
  }
  function decisionCard(d) {
    var card = h("article", { class: "sf-card sf-decision", id: "dec-" + d.id });
    var top = h("div", { class: "sf-q-top" }, h("span", { class: "sf-mono" }, d.id), kindChip(d.kind), chip(decisionStatusText(d), decisionStatusKind(d)));
    if (d.topic && X.topic.get(d.topic)) top.appendChild(h("a", { href: "#dictionary/topic/" + d.topic }, X.topic.get(d.topic).title));
    (d.targets || []).slice(0, 5).forEach(function (t) { top.appendChild(h("code", null, t)); });
    card.appendChild(top);
    card.appendChild(h("div", { class: "sf-q-title" }, d.question || ""));
    if (d.context) card.appendChild(h("p", { class: "sf-q-context sf-small" }, d.context));
    var dl = h("dl", { class: "sf-qa" });
    if (d.answer && d.status === "answered") {
      dl.appendChild(h("dt", null, "Answer")); dl.appendChild(h("dd", null, (d.answer.choices ? d.answer.choices.map(function (c) { return optionLabel(d, c) || c; }).join("; ") : optionLabel(d, d.answer.choice) || d.answer.text || d.answer.choice),
        h("span", { class: "sf-muted sf-small" }, " — " + byLabel(d.answer.by) + ", " + fmtDate(d.answer.at))));
      if (d.answer.note) { dl.appendChild(h("dt", null, "Note")); dl.appendChild(h("dd", null, d.answer.note)); }
    }
    if (d.agentDecision && d.status !== "answered") {
      dl.appendChild(h("dt", null, "Decision")); dl.appendChild(h("dd", null, optionLabel(d, d.agentDecision.choice) || String(d.agentDecision.choice),
        h("span", { class: "sf-muted sf-small" }, " — your agent" + (d.reviewer === "steward" ? ", on the author's behalf (they were not sure)" : ""))));
      if (d.agentDecision.why) { dl.appendChild(h("dt", null, "Why")); dl.appendChild(h("dd", null, d.agentDecision.why)); }
    }
    if (d.recommended && ["open", "asked"].indexOf(d.status) >= 0) {
      dl.appendChild(h("dt", null, "Recommended")); dl.appendChild(h("dd", null, optionLabel(d, d.recommended) || d.recommended, d.why ? h("span", { class: "sf-muted sf-small" }, " — " + d.why) : null));
    }
    if (dl.childNodes.length) card.appendChild(dl);
    var ev = evidenceList(d);
    if (ev) card.appendChild(h("details", null, h("summary", { class: "sf-small" }, "Evidence (" + (d.evidence || []).length + ")"), ev));
    var foot = h("div", { class: "sf-q-foot" });
    if (d.needsReview) {
      foot.appendChild(OB.confirms[d.id] ? chip("✓ Looks right — ready to send", "ok") :
        btn("Looks right", function () { OB.confirms[d.id] = true; keepNoteOnly(d.id); obSave(); renderEvidence(); }, "sf-btn-ok sf-btn-sm"));
      if (OB.confirms[d.id]) foot.appendChild(btn("Undo", function () { delete OB.confirms[d.id]; obSave(); renderEvidence(); }, "sf-btn-quiet sf-btn-sm"));
    }
    if (["cancelled", "superseded"].indexOf(d.status) < 0) foot.appendChild(feedbackButton({ type: "decision", id: d.id }, d.needsReview ? "I disagree" : "Comment"));
    if (d.status === "asked") foot.appendChild(btn("Answer it", function () { UI.qFilter = "waiting"; go("questions"); setTimeout(function () { var c = document.getElementById("q-" + d.id); if (c) c.scrollIntoView({ block: "center" }); }, 80); }, "sf-btn-sm"));
    if (d.replacement) foot.appendChild(h("a", { href: "#evidence/decision/" + d.replacement }, "Replaced by " + d.replacement));
    card.appendChild(foot);
    return card;
  }

  // ------------------------------------------------------------------ data check
  function checkKey(c) {
    var loc = c.location || {};
    return [c.ruleId, c.keyword, loc.file, loc.pointer, c.path || ""].join("|");
  }
  function parseFindings(doc, ruleMap) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc)) return { error: "This file is not QuaC findings." };
    if (doc.containsData !== false || !Array.isArray(doc.schemaChecks))
      return { error: "This is not QuaC's “findings without data”. In QuaC, after Run QC, use Findings without data → JSON." };
    var sch = (doc.inputs || {}).schema || {};
    var root = sch.root || "";
    var table = (S.tables || []).filter(function (t) { return t.mother === root || root.slice(-t.mother.length) === t.mother; })[0] ||
      (S.tables || []).filter(function (t) { return (sch.id || "") && X.doc.get(t.mother) && X.doc.get(t.mother).uri === sch.id; })[0] || null;
    var checks = doc.schemaChecks.filter(function (c) { return c.severity === "error" || c.severity === "warning"; }).map(function (c) {
      var m = /^schema:cond:(\d+):/.exec(c.ruleId || "");
      var rule = ruleMap && c.ruleId && ruleMap[c.ruleId] ? ruleMap[c.ruleId] : null;   // stored when the run was imported
      if (!rule && m && table) {
        var enc = (S.encodedRules || []).filter(function (r) { return r.table === table.name && r.index === Number(m[1]); })[0];
        rule = enc ? enc.id : null;
      }
      var key = table && c.variable ? table.name + "." + c.variable : null;
      var prop = key ? X.props.get(key) : null;
      return { c: c, key: checkKey(c), rule: rule, topic: prop ? prop.topic : null };
    });
    return { doc: doc, table: table, checks: checks, setId: sch.setId, matches: !!(S.quacSetId && sch.setId === S.quacSetId),
             version: doc.findingsSchemaVersion };
  }
  function findingsStats(doc) {
    var ov = doc.overview || {};
    return [[ov.records, "records checked"],
            [ov.recordsWithErrors, "records with a mismatch" + (ov.records ? " (" + Math.round(100 * (ov.recordsWithErrors || 0) / ov.records) + "%)" : "")],
            [ov.schemaChecksFailed, "schema checks failed"],
            [((ov.missingVariables || {}).required || 0), "required variables missing"],
            [ov.columnsNotInSchema, "columns the schema does not describe"]];
  }
  function checksTable(parsed, triage, planned, later) {
    var tbody = h("tbody");
    parsed.checks.slice().sort(function (a, b) { return (b.c.records || 0) - (a.c.records || 0); }).forEach(function (x) {
      var c = x.c, tri = triage ? triage[x.key] : null;
      tbody.appendChild(h("tr", null,
        h("td", null, c.variable ? h("code", null, c.variable) : h("span", { class: "sf-muted" }, "the whole dataset"),
          x.topic && X.topic.get(x.topic) ? h("div", { class: "sf-muted sf-small" }, X.topic.get(x.topic).title) : null),
        h("td", null, c.requirement || "", x.rule ? h("div", null, h("a", { href: "#skip-logic/" + x.rule, class: "sf-small" }, "rule " + x.rule)) : null),
        h("td", { class: "sf-nowrap" }, c.records !== null && c.records !== undefined ? [c.records + (c.percentOfRecords !== null && c.percentOfRecords !== undefined ? " (" + c.percentOfRecords + "%)" : ""),
          typeof c.percentOfRecords === "number" ? h("span", { class: "sf-pbar", title: c.percentOfRecords + "% of records" }, h("i", { style: "width:" + Math.min(100, Math.max(1, c.percentOfRecords)) + "%" })) : null]
          : h("span", { class: "sf-muted" }, "—")),
        triage ? h("td", null, tri ? chip({ "schema-fix": "Schema fixed", "data-issue": "Data issue", expected: "Expected", question: "Asked you" }[tri.verdict] || tri.verdict,
          { "schema-fix": "ok", "data-issue": "bad", expected: "outline", question: "accent" }[tri.verdict]) :
          (planned || []).indexOf(x.key) >= 0 ? chip("Its topic is not built yet", "outline") : later ? chip("Checked again in " + later, "outline") : chip("Agent to review", "warn")) : null));
    });
    return h("div", { class: "sf-table-wrap" }, h("table", { class: "sf-table" }, h("thead", null, h("tr", null, h("th", null, "Variable"), h("th", null, "What the schema requires"), h("th", null, "Records"),
      triage ? h("th", null, "Outcome") : null)), tbody));
  }
  // ------------------------------------------------------------------ toy data, annotated
  // The made-up toy rows (never real data) in an interactive grid, every JSON Schema validation
  // error pinned to its cell: data-table (DuckDB-WASM in a worker), loaded from jsDelivr at this
  // pinned version the first time the Data check tab opens. Without it (offline, a blocked CDN,
  // an old browser) the same rows show in a plain table.
  var DT = { version: "0.10.0", worker: "assets/worker-BpxbYHX2.js",   // the worker's file name is fixed per version (VENDORED.md)
             loading: null, failed: null, table: null, box: null, loaded: null, gen: 0, ids: null, pending: null };
  DT.base = "https://cdn.jsdelivr.net/npm/@jeyabbalas/data-table@" + DT.version + "/dist/";
  var KW = { anyOf: "not an allowed value", oneOf: "not an allowed value", "enum": "not an allowed value", "const": "breaks a rule",
             not: "breaks a rule", type: "wrong type", minimum: "too small", maximum: "too large", exclusiveMinimum: "too small",
             exclusiveMaximum: "too large", pattern: "wrong format", format: "wrong format", minLength: "too short", maxLength: "too long",
             required: "missing", unevaluatedProperties: "not a variable", additionalProperties: "not a variable", uniqueItems: "duplicate row" };
  var KIND = { "wrong-type": "wrong type", "unknown-level": "a code the dictionary does not define", "range-break": "out of range",
               "invented-sentinel": "a made-up special code", "pattern-break": "wrong format", "skip-break": "breaks a skip rule",
               "applicability-break": "breaks an applicability rule", "routing-break": "breaks a routing rule", "missing-key": "a missing value",
               "undeclared-column": "a column the dictionary does not have", "duplicate-row": "a duplicate row" };

  function toyColumns(entry) {
    var seen = new Set(), out = [];
    (entry.rows || []).forEach(function (r) { Object.keys(r || {}).forEach(function (k) { if (!seen.has(k)) { seen.add(k); out.push(k); } }); });
    return out;
  }
  function toyVarTitle(entry, name) {
    var c = (entry.columns || {})[name];
    if (c && c.title) return c.title;
    var prop = X.props.get(entry.table + "." + name);
    return (prop && prop.schema && prop.schema.title) || name;
  }
  function toyCases(entry) {
    var byRow = new Map();
    (entry.errors || []).forEach(function (f) { if (!byRow.has(f.row)) byRow.set(f.row, []); byRow.get(f.row).push(f); });
    var cases = (entry.planted || []).map(function (c) {
      var errs = byRow.get(c.row) || [];
      var hit = errs.filter(function (f) { return f.column === c.column || (c.kind === "duplicate-row" && !f.column); });
      var verdict = !errs.length ? "missed" : !hit.length ? "wrong-column" : hit.length === errs.length ? "caught" : "caught-extra";
      return { row: c.row, column: c.column, kind: c.kind, reason: c.reason, errors: errs, verdict: verdict };
    });
    var planted = new Set(cases.map(function (c) { return c.row; }));
    var unplanned = [];
    byRow.forEach(function (errs, row) { if (!planted.has(row)) unplanned.push({ row: row, errors: errs }); });
    unplanned.sort(function (a, b) { return a.row - b.row; });
    return { cases: cases, unplanned: unplanned };
  }
  function toySummary(entry) {
    var rows = entry.rowCount || (entry.rows || []).length;
    if (entry.checkError) return h("p", null, chip("Not checked", "warn"), " — the validator could not check these rows: " + entry.checkError);
    if (entry.unchecked) return h("p", null, chip("Not checked yet", "outline"), " — your agent's next build checks these rows against the current schemas.");
    if (entry.file !== "invalid") {
      var bad = new Set((entry.errors || []).map(function (f) { return f.row; })).size;
      return bad ? h("p", null, chip(bad + " of " + plural(rows, "row") + " fail", "bad"),
                     " — these rows should all pass. Your agent fixes the schemas or the rows before calling a topic tested.")
                 : h("p", null, chip("✓ All " + plural(rows, "row") + " pass", "ok"), " — everything your documents allow is accepted, including every special code.");
    }
    var tc = toyCases(entry), n = tc.cases.length;
    var caught = tc.cases.filter(function (c) { return c.verdict === "caught"; }).length;
    var missed = tc.cases.filter(function (c) { return c.verdict === "missed"; }).length;
    var parts = [chip(caught === n && !tc.unplanned.length ? "✓ All " + n + " planted mistakes caught" : caught + " of " + n + " planted mistakes caught exactly",
                      caught === n && !tc.unplanned.length ? "ok" : "warn")];
    if (missed) parts.push(" ", chip(missed + " slipped through", "bad"));
    parts.push(" — each row breaks one thing on purpose; a red cell is the check that caught it. Hover a cell for the explanation.");
    return h("p", null, parts);
  }
  function toyIssueList(entry) {
    var ol = h("ol", { class: "sf-toy-issues", "aria-label": "Mismatches" });
    var verdictChip = { caught: chip("caught", "ok"), "caught-extra": chip("caught, and other cells fail too", "warn"),
                        "wrong-column": chip("caught on another column", "warn"), missed: chip("slipped through", "bad") };
    function item(row, column, title, lines, verdict) {
      ol.appendChild(h("li", { class: "sf-toy-issue" },
        h("button", { type: "button", class: "sf-toy-go", onclick: function () { revealToy(entry, row, column); } },
          h("span", { class: "sf-muted" }, "Row " + (row + 1) + " · "), title),
        lines.map(function (l) { return h("div", { class: "sf-small" + (l[1] ? " sf-muted" : "") }, l[0]); }),
        verdict ? h("div", null, verdictChip[verdict]) : null));
    }
    if (entry.file === "invalid") {
      var tc = toyCases(entry);
      tc.cases.forEach(function (c) {
        var lines = [["Planted: " + (KIND[c.kind] || c.kind) + (c.reason ? " — " + c.reason : ""), false]];
        if (c.errors[0]) lines.push([c.errors[0].message, true]);
        item(c.row, c.column, c.column ? toyVarTitle(entry, c.column) : "the whole row", lines, c.verdict);
      });
      tc.unplanned.forEach(function (u) {
        item(u.row, u.errors[0].column, u.errors[0].column ? toyVarTitle(entry, u.errors[0].column) : "the whole row",
             [["Fails, but no mistake was planted here: " + u.errors[0].message, false]], "missed");
      });
    } else {
      (entry.errors || []).slice(0, 200).forEach(function (f) {
        item(f.row, f.column, f.column ? toyVarTitle(entry, f.column) : "the whole row", [[f.message, false], [f.hint || "", true]], null);
      });
    }
    if (!ol.firstChild) return h("p", { class: "sf-muted sf-small" }, "Nothing to list: every row passes.");
    return ol;
  }
  function toyAnnotations(entry, ids, has) {
    var planted = new Map((entry.planted || []).map(function (c) { return [c.row, c]; }));
    var out = [];
    (entry.errors || []).forEach(function (f) {
      if (ids[f.row] === undefined) return;
      var c = planted.get(f.row);
      var msg = f.message + (f.hint ? "\n" + f.hint : "") + (c && c.reason ? "\nPlanted on purpose: " + c.reason : "");
      var a = { severity: "error", message: msg, code: f.rule || KW[f.keyword] || f.keyword || "mismatch",
                source: entry.file === "invalid" ? (c ? "planted mistake" : "not planted") : "this row should pass", rowId: Number(ids[f.row]) };
      if (f.column && has.has(f.column)) { a.scope = "cell"; a.column = f.column; } else a.scope = "row";
      out.push(a);
    });
    if (entry.file === "invalid") toyCases(entry).cases.forEach(function (c) {
      if (c.verdict === "missed" && ids[c.row] !== undefined)
        out.push({ scope: "row", rowId: Number(ids[c.row]), severity: "warning", code: "slipped through", source: "planted mistake",
                   message: "This row breaks one thing on purpose (" + (KIND[c.kind] || c.kind) + (c.reason ? ": " + c.reason : "") +
                            "), yet it passes — the schemas do not catch it yet." });
    });
    return out;
  }
  function toyTooltip(entry, name) {
    var c = (entry.columns || {})[name];
    var prop = X.props.get(entry.table + "." + name);
    if (!c && !prop) return { title: name, description: "Not a variable of this table: the data dictionary does not describe it." };
    var tp = prop && X.topic.get(prop.topic);
    var items = [{ label: "Variable", value: name }];
    if (tp) items.push({ label: "Topic", value: tp.title || tp.id });
    return { title: toyVarTitle(entry, name), description: c && c.allowed ? "Allowed: " + c.allowed : "", items: items };
  }
  function toyKey(entry) { return entry.table + "/" + entry.file + "@" + (entry.hash || S.generatedAt || ""); }
  function loadDT() {
    if (DT.loading) return DT.loading;
    if (!document.querySelector("link[data-sf-dt]"))
      document.head.appendChild(h("link", { rel: "stylesheet", href: DT.base + "data-table.css", "data-sf-dt": "" }));
    DT.loading = import(DT.base + "data-table.js");
    return DT.loading;
  }
  function startWorker() {
    // A browser starts no worker from another origin's script; a blob: URL belongs to this page.
    var code = "import " + JSON.stringify(DT.base + DT.worker) + ";";
    return new Worker(URL.createObjectURL(new Blob([code], { type: "text/javascript" })), { type: "module" });
  }
  function toyFile(entry) { return new File([JSON.stringify(entry.rows || [])], entry.file + ".json", { type: "application/json" }); }
  function toyTableName(entry) { return "toy_" + String(entry.table).replace(/[^A-Za-z0-9_]/g, "_") + "_" + entry.file; }
  function syncToyGrid(entry, slot) {
    if (!entry || !entry.rows) return;
    if (UI.tab !== "data-check") { DT.pending = [entry, slot]; return; }      // a hidden container has no height
    DT.pending = null;
    if (DT.failed) { clear(slot).appendChild(staticToyTable(entry, DT.failed)); return; }
    if (!DT.box) DT.box = h("div", { class: "sf-toy-grid" });
    if (DT.box.parentNode !== slot) slot.appendChild(DT.box);
    var key = toyKey(entry);
    if (DT.loaded === key) return;
    var gen = ++DT.gen;
    var wait = h("div", { class: "sf-toy-loading", role: "status" }, DT.table ? "Loading…" : "Loading the interactive table — the first time takes a few seconds…");
    slot.appendChild(wait);
    var ready = DT.table
      ? DT.table.loadData(toyFile(entry), { tableName: toyTableName(entry) }).then(function () { return DT.table; })
      : loadDT().then(function (mod) {
          return mod.createDataTable({ container: DT.box, source: toyFile(entry), tableName: toyTableName(entry),
            persistence: false, presets: false, expressionFilter: false, derivedColumns: false,
            bridgeOptions: { workerFactory: startWorker } });
        }).then(function (t) { DT.table = t; return t; });
    ready.then(function (t) {
      if (gen !== DT.gen) return null;
      return t.actions.getColumnValues("__rowid__").then(function (ids) {
        if (gen !== DT.gen) return;
        DT.ids = ids;
        var names = toyColumns(entry), has = new Set(names);
        t.annotations.clear();
        var anns = toyAnnotations(entry, ids, has);
        if (anns.length) t.annotations.addMany(anns);
        names.forEach(function (n) { t.actions.setColumnHeaderTooltip(n, toyTooltip(entry, n)); });
        if (UI.toyOnlyBad && anns.length) t.actions.showAnnotatedRows();
        DT.loaded = key;
      });
    }).catch(function (e) {
      if (gen !== DT.gen) return;
      DT.failed = (e && (e.message || e.code)) || String(e);
      if (window.console) console.warn("schemify: the interactive table could not load; showing a plain table.", e);
      clear(slot).appendChild(staticToyTable(entry, DT.failed));
    }).then(function () { if (wait.parentNode) wait.remove(); });
  }
  function revealToy(entry, row, column) {
    if (DT.table && DT.ids && !DT.failed && DT.loaded === toyKey(entry)) {
      var rid = DT.ids[row];
      if (rid === undefined) return;
      if (DT.box) DT.box.scrollIntoView({ block: "nearest" });
      var col = column && toyColumns(entry).indexOf(column) >= 0 ? column : undefined;
      DT.table.actions.revealRow(Number(rid), col).then(function (shown) {
        if (shown === null) toast("That row is hidden by a filter in the table — clear the filters to see it.");
      }, function () { /* a newer move took over */ });
      return;
    }
    var cell = document.getElementById("toy-" + row + "-" + (column || "")) || document.getElementById("toy-" + row + "-");
    if (cell) {
      cell.scrollIntoView({ block: "center", inline: "center" });
      cell.classList.add("sf-cell-flash"); setTimeout(function () { cell.classList.remove("sf-cell-flash"); }, 1600);
    }
  }
  function staticToyTable(entry, reason) {
    var cols = toyColumns(entry).slice(0, 300), rows = (entry.rows || []).slice(0, 500);
    var bad = new Map();
    (entry.errors || []).forEach(function (f) {
      var k = f.row + "|" + (f.column && cols.indexOf(f.column) >= 0 ? f.column : "");
      bad.set(k, (bad.get(k) ? bad.get(k) + "\n\n" : "") + f.message + (f.hint ? "\n" + f.hint : ""));
    });
    var head = h("tr", null, h("th", { scope: "col" }, "Row"), cols.map(function (c) { return h("th", { scope: "col", title: toyVarTitle(entry, c) }, c); }));
    var body = h("tbody");
    rows.forEach(function (r, i) {
      var rowMsg = bad.get(i + "|");
      body.appendChild(h("tr", null,
        h("th", { scope: "row", id: "toy-" + i + "-", class: rowMsg ? "sf-cell-bad" : null, title: rowMsg || null }, String(i + 1)),
        cols.map(function (c) {
          var msg = bad.get(i + "|" + c), has = Object.prototype.hasOwnProperty.call(r || {}, c);
          var v = has ? (r[c] === null ? "null" : typeof r[c] === "object" ? JSON.stringify(r[c]) : String(r[c])) : "";
          return h("td", { id: "toy-" + i + "-" + c, class: msg ? "sf-cell-bad" : null, title: msg || null }, has ? v : h("span", { class: "sf-muted" }, "—"));
        })));
    });
    return h("div", null,
      reason ? h("p", { class: "sf-small sf-muted" }, "The interactive table could not load here (it needs an internet connection the first time), so this is a plain view. Hover a red cell for the explanation.") : null,
      h("div", { class: "sf-table-wrap sf-toy-static" }, h("table", { class: "sf-table" }, h("thead", null, head), body)));
  }
  function renderToy(card) {
    clear(card);
    card.appendChild(h("h2", null, "1. What a mismatch looks like — on toy data"));
    card.appendChild(h("p", { class: "sf-small" }, "Your agent made these rows up from your documents — never from real data. One set should all pass; in the other, each row breaks one thing on purpose. Every red cell is a JSON Schema validation error, explained in plain words: the same checks QuaC runs on your real data."));
    var all = (S.toyData || []).filter(function (t) { return t && t.table; });
    if (!all.length) { card.appendChild(h("p", { class: "sf-empty" }, "Toy data appears once the first topic is drafted.")); return; }
    var tables = [];
    all.forEach(function (t) { if (tables.indexOf(t.table) < 0) tables.push(t.table); });
    if (tables.indexOf(UI.toyTable) < 0) UI.toyTable = tables[0];
    var files = all.filter(function (t) { return t.table === UI.toyTable; });
    if (!files.some(function (f) { return f.file === UI.toyFile; })) UI.toyFile = files.some(function (f) { return f.file === "invalid"; }) ? "invalid" : files[0].file;
    var entry = files.filter(function (f) { return f.file === UI.toyFile; })[0];
    var bar = h("div", { class: "sf-row sf-toy-bar" });
    if (tables.length > 1) {
      var sel = h("select", { class: "sf-select", "aria-label": "Table", onchange: function (e) { UI.toyTable = e.target.value; renderDataCheck(); } },
        tables.map(function (t) { var o = h("option", { value: t }, t); if (t === UI.toyTable) o.selected = true; return o; }));
      bar.appendChild(sel);
    }
    var seg = h("div", { class: "sf-seg", role: "group", "aria-label": "Which rows" });
    files.forEach(function (f) {
      var n = f.rowCount || (f.rows || []).length;
      seg.appendChild(h("button", { type: "button", "aria-pressed": f.file === UI.toyFile ? "true" : "false",
        onclick: function () { UI.toyFile = f.file; renderDataCheck(); } },
        (f.file === "invalid" ? "Planted mistakes" : "Rows that should pass") + " (" + n + ")"));
    });
    bar.appendChild(seg);
    var only = h("label", { class: "sf-small" }, h("input", { type: "checkbox", checked: UI.toyOnlyBad ? true : null, onchange: function (e) {
      UI.toyOnlyBad = e.target.checked;
      if (DT.table && !DT.failed) { if (UI.toyOnlyBad) DT.table.actions.showAnnotatedRows(); else DT.table.actions.hideAnnotatedRows(); }
    } }), " Only rows with a mismatch");
    if (!DT.failed) bar.appendChild(only);
    if (!DT.failed) bar.appendChild(btn("Next mismatch ↓", function () { if (DT.table) DT.table.actions.nextAnnotation().catch(function () {}); }, "sf-btn-sm", { title: "Or press F8 in the table" }));
    card.appendChild(bar);
    card.appendChild(toySummary(entry));
    var slot = h("div", { class: "sf-toy-slot" });
    var layout = h("div", { class: "sf-toy-layout" }, slot, h("div", { class: "sf-toy-side" }, h("h3", { class: "sf-small" }, "Mismatches"), toyIssueList(entry)));
    card.appendChild(layout);
    if (!entry.rows) slot.appendChild(h("p", { class: "sf-muted sf-small" }, "These rows are too many to show here; download them below."));
    card.appendChild(h("p", { class: "sf-small sf-muted" }, "Download: ",
      entry.path ? h("a", { href: entry.path, download: "" }, "JSON") : null, entry.csv ? " · " : null,
      entry.csv ? h("a", { href: entry.csv, download: "" }, "CSV") : null,
      DT.failed ? null : " · In the table: hover a red cell, press F8 for the next mismatch, click a bar in a column's chart to filter."));
    syncToyGrid(entry, slot);
  }

  function renderDataCheck() {
    var p = $("#panel-data-check");
    if (!$("#dc-toy", p)) {
      clear(p);
      p.appendChild(h("h1", null, "Data check"));
      p.appendChild(h("p", { class: "sf-lede" }, "A schema is right when real data fits it. Every place the data and the schema disagree shows up as a validation failure — the measure of how far apart they are. Your real data never leaves your computer, and your agent never sees it: you check it in QuaC, which runs inside your browser, and send back only a summary of what failed (counts and the schema's own wording — no values). Only for public data, or an agent on a model you control, can you let your agent run that check itself."));
      p.appendChild(h("div", { class: "sf-card", id: "dc-toy" }));
      p.appendChild(h("div", { class: "sf-card", id: "dc-real" }));
      p.appendChild(h("div", { class: "sf-card", id: "dc-agent" }));
      p.appendChild(h("div", { class: "sf-card", id: "dc-runs" }));
    }
    var toyCard = $("#dc-toy", p);
    var tk = (S.toyData || []).map(toyKey).join(",") + "|" + UI.toyTable + "|" + UI.toyFile + "|" + (DT.failed ? 1 : 0);
    if (toyCard.dataset.key !== tk || !toyCard.firstChild) { toyCard.dataset.key = tk; renderToy(toyCard); }
    else if (DT.pending && UI.tab === "data-check") syncToyGrid(DT.pending[0], DT.pending[1]);
    renderRealCheck(clear($("#dc-real", p)));
    renderAgentCheck(clear($("#dc-agent", p)));
    renderRuns(clear($("#dc-runs", p)));
  }
  var BASIS = { "public": "the data is public", "local-model": "your agent runs on a model you control" };
  var BROWSER_TEXT = "Keep checking this dataset in QuaC, in my browser, and send my agent only the findings without data.";
  function datasetById(id) { return (S.datasets || []).filter(function (d) { return d.id === id; })[0] || {}; }
  function renderAgentCheck(card) {
    card.appendChild(h("h2", null, "3. Or let your agent run the check itself"));
    card.appendChild(h("p", null, "Only if the data is public, or if your agent runs on a model you control and your data agreement allows that model to process this data. ",
      "Your agent then runs QuaC on the file each time the schemas change and reads only the findings without data — never the rows. You can stop it here at any time."));
    var model = (S.workspace || {}).model;
    card.appendChild(h("p", { class: "sf-small sf-muted" }, model ? "Your agent last said it runs on: " + model + (S.workspace.harness ? " (" + S.workspace.harness + ")" : "") +
      ". A permission for “a model you control” covers that model only." : "Your agent has not said which model it runs on."));
    var live = (S.datasets || []).filter(function (d) { return !d.withdrawn && d.basis !== "browser"; });
    var stopping = OB.datasets.filter(function (d) { return d.withdraw; }).map(function (d) { return d.withdraw; });
    live.forEach(function (d) {
      var runs = (S.alignment || []).filter(function (a) { return a.dataset === d.id; }).length;
      card.appendChild(h("div", { class: "sf-row", style: "align-items:baseline;gap:10px;margin:6px 0" },
        chip(d.id, "outline"), h("strong", null, d.label), h("code", { class: "sf-small" }, d.path),
        h("span", { class: "sf-small sf-muted" }, BASIS[d.basis] + " — allowed by " + byLabel(d.by) + ", " + fmtDate(d.at) +
          (d.model ? " for " + d.model : "") + " · " + plural(runs, "run")),
        stopping.indexOf(d.id) >= 0 ? chip("Stop is in your outbox", "warn") :
          btn("Stop", function () { OB.datasets.push({ withdraw: d.id }); obSave(); renderDataCheck(); toast("Added — send it to your agent."); }, "sf-btn-quiet sf-btn-sm")));
    });
    OB.datasets.filter(function (d) { return !d.withdraw; }).forEach(function (d) {
      card.appendChild(h("p", null, chip("In your outbox", "ok"), " " + d.label + " — " + d.path));
    });
    var f = { path: "", label: "", table: (S.tables || []).length === 1 ? S.tables[0].name : "", sheet: "", basis: "", text: "" };
    var form = h("div", null);
    function field(label, el, hint) { form.appendChild(h("label", { class: "sf-label" }, label)); form.appendChild(el); if (hint) form.appendChild(h("div", { class: "sf-small sf-muted" }, hint)); }
    field("Where the file is", h("input", { class: "sf-input", placeholder: "data/public_extract.csv", oninput: function (e) { f.path = e.target.value.trim(); } }),
      "A full path, or one relative to " + ((S.workspace || {}).parent || "the folder you opened your agent in") + ". Keep it outside the schemify folder.");
    field("A name for it", h("input", { class: "sf-input", placeholder: "2024 public-use extract", oninput: function (e) { f.label = e.target.value.trim(); } }));
    if ((S.tables || []).length > 1) {
      var sel = h("select", { class: "sf-input", onchange: function (e) { f.table = e.target.value; } }, h("option", { value: "" }, "Which table is it?"));
      S.tables.forEach(function (t) { sel.appendChild(h("option", { value: t.name }, (t.title || t.name) + " (" + t.name + ")")); });
      field("Table", sel);
    }
    field("Excel sheet (only for a workbook with several sheets)", h("input", { class: "sf-input", oninput: function (e) { f.sheet = e.target.value.trim(); } }));
    var basisBox = h("div", { role: "radiogroup", "aria-label": "Why your agent may process it" });
    Object.keys(BASIS).forEach(function (k) {
      basisBox.appendChild(h("label", { class: "sf-option" }, h("input", { type: "radio", name: "dc-basis", value: k, onchange: function () { f.basis = k; } }),
        h("div", { class: "sf-option-body" }, h("span", { class: "sf-option-label" }, k === "public" ? "The data is public" :
          "My agent runs on a model I control, and my data agreement allows it to process this data"))));
    });
    field("Why your agent may process it", basisBox);
    field("In your own words — this is recorded as your permission", h("textarea", { class: "sf-textarea", rows: 2,
      placeholder: "e.g. “It is the public-use file from the study website.”", oninput: function (e) { f.text = e.target.value.trim(); } }));
    form.appendChild(h("div", { class: "sf-row", style: "margin-top:10px" }, btn("Add to outbox", function () {
      var miss = [!f.path && "where the file is", !f.label && "a name", (S.tables || []).length > 1 && !f.table && "the table", !f.basis && "why", !f.text && "your own words"].filter(Boolean);
      if (miss.length) { toast("Still needed: " + miss.join(", ") + ".", true); return; }
      OB.datasets.push({ path: f.path, label: f.label, table: f.table || undefined, sheet: f.sheet || undefined, basis: f.basis, text: f.text });
      obSave(); renderDataCheck(); toast("Added — send it to your agent.");
    }, "sf-btn-primary")));
    card.appendChild(h("details", { open: false }, h("summary", null, live.length ? "Allow another dataset" : "Allow a dataset"), form));
  }
  function renderRealCheck(s2) {
    s2.appendChild(h("h2", null, "2. Check your real data, privately"));
    renderQuacCard(s2);
    var manual = h("details", { open: !!UI.findingsDraft || !!UI.alignmentDraft }, h("summary", null, "Or check it by hand, one run at a time"));
    s2.appendChild(manual);
    s2 = manual;
    var folder = (S.workspace.path || "schemify") + "/" + ((S.quac || {}).schemasFolder || "package/schemas");
    var cli = ((S.quac || {}).cli || "npx --yes @jeyabbalas/quac@1.2.0") + " YOUR_DATA.csv --schema \"" + folder + "\" --no-report --findings quac-findings.json";
    s2.appendChild(h("ol", { class: "sf-steps-numbered" },
      h("li", null, btn("Open QuaC ↗", function () { window.open((S.quac || {}).app || "https://jeyabbalas.github.io/quac/", "_blank", "noopener"); }, "sf-btn-primary sf-btn-sm"),
        h("span", { class: "sf-small sf-muted" }, " — it opens in a new tab and runs entirely in your browser.")),
      h("li", null, "Drop your data file (CSV, Excel, JSON, or Parquet) into ", h("strong", null, "Dataset"), "."),
      h("li", null, "Drop this folder into ", h("strong", null, "JSON Schema"), ":",
        h("div", { class: "sf-copy" }, h("code", null, folder), btn("Copy path", function () { copyText(folder); }, "sf-btn-sm")),
        (S.tables || []).length > 1 ? h("span", { class: "sf-small sf-muted" }, "QuaC asks which table the data is; pick its schema file.") : null),
      h("li", null, "Press ", h("strong", null, "Run QC"), ". QuaC shows every mismatch on your data — values included — on your screen only."),
      h("li", null, "Under ", h("strong", null, "Findings without data"), ", press ", h("strong", null, "JSON"), ". The file is saved to your downloads."),
      h("li", null, "Press ", h("strong", null, "Reset"), " at the top of QuaC — it keeps your data in this browser until you do."),
      h("li", null, "Drop the downloaded file below.")));
    s2.appendChild(h("details", { class: "sf-small" }, h("summary", null, "Prefer the command line? (Node 24 or newer)"),
      h("div", { class: "sf-copy" }, h("code", null, cli), btn("Copy", function () { copyText(cli); }, "sf-btn-sm")),
      h("p", null, "Run it yourself in a terminal — not through your agent. It writes no report with data, only the findings file.")));
    var drop = h("div", { class: "sf-drop", tabindex: 0, role: "button", "aria-label": "Choose the QuaC findings file" },
      h("strong", null, "Drop the findings file here"), h("div", { class: "sf-small sf-muted" }, "or click to choose it — quac-findings_….json"));
    var input = h("input", { type: "file", accept: ".json,application/json", hidden: true, onchange: function (e) { if (e.target.files[0]) readFindings(e.target.files[0]); } });
    drop.addEventListener("click", function () { input.click(); });
    drop.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
    drop.addEventListener("dragover", function (e) { e.preventDefault(); drop.classList.add("sf-over"); });
    drop.addEventListener("dragleave", function () { drop.classList.remove("sf-over"); });
    drop.addEventListener("drop", function (e) { e.preventDefault(); drop.classList.remove("sf-over"); if (e.dataTransfer.files[0]) readFindings(e.dataTransfer.files[0]); });
    s2.appendChild(drop); s2.appendChild(input);
    if (UI.findingsDraft) s2.appendChild(findingsPreview(UI.findingsDraft));
    if (UI.alignmentDraft) s2.appendChild(h("p", null, chip("✓ Findings are in your outbox — send them to your agent", "ok")));
  }
  // ------------------------------------------------------------------ QuaC, kept connected
  // The person's file stays in QuaC's own tab (QuaC keeps it between visits). This page hands QuaC the schema files
  // whenever the agent asks for a re-check (activity.js → recheck) or the person presses Check again, and forwards
  // the findings without data QuaC sends back. Messages go only to the tab this page opened, at QuaC's origin.
  var QC = { win: null, origin: null, label: "", table: "", state: "off", status: "", detail: "", datasetLoaded: false,
    request: null, handled: null, sentAt: null, timer: null };
  var QUAC_PROTOCOL = { protocol: "quac-companion", version: 1 };
  function quacApp() { return (S.quac || {}).app || "https://jeyabbalas.github.io/quac/"; }
  function quacOrigin() { try { return new URL(quacApp(), location.href).origin; } catch (e) { return null; } }
  function quacDataset() {
    return (S.datasets || []).filter(function (d) {
      return d.basis === "browser" && !d.withdrawn && d.label === QC.label && (d.table || "") === (QC.table || "");
    }).slice(-1)[0] || null;
  }
  function quacUpToDate() {
    var ds = quacDataset();
    var last = ds ? (S.alignment || []).filter(function (a) { return a.dataset === ds.id; }).slice(-1)[0] : null;
    return !!last && last.fingerprint === S.quacSetId;
  }
  function quacConnected() { return !!QC.win && !QC.win.closed && (QC.state === "on" || QC.state === "busy"); }
  function postQuiet(path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Schemify-Token": CONN.token || "" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); });
  }
  function quacPresence() {
    if (CONN.mode !== "live" || QC.state === "off") return;
    var ds = quacDataset();
    postQuiet("api/presence", { quac: { connected: quacConnected(), datasetLoaded: QC.datasetLoaded, dataset: ds ? ds.id : "",
      status: QC.status || "", request: QC.request || "", detail: QC.detail || "" } }).catch(function () { /* next tick */ });
  }
  function quacTick() {
    if (QC.state === "off") return;
    if (QC.win && QC.win.closed) { QC.win = null; QC.state = "closed"; renderQuacCardAgain(); }
    // A QuaC tab that is still connected from before (this page reloaded) answers a ping; a new one asks Allow first.
    if (QC.state === "opening" && QC.win) QC.win.postMessage(Object.assign({ kind: "ping" }, QUAC_PROTOCOL), QC.origin);
    var rq = ACT.recheck, ds = quacDataset();
    if (rq && rq.id !== QC.handled && ds && rq.dataset === ds.id && quacConnected()) { QC.handled = rq.id; quacSendSchemas(rq.id); }
    quacPresence();
  }
  function quacSendSchemas(rid) {
    var files = (S.schemas || []).map(function (x) { return x.path; });
    var t = (S.tables || []).filter(function (x) { return x.name === QC.table; })[0] || ((S.tables || []).length === 1 ? S.tables[0] : null);
    QC.request = rid; QC.status = "loading"; QC.detail = ""; renderQuacCardAgain();
    Promise.all(files.map(function (path) {
      return fetch("package/schemas/" + path.split("/").map(encodeURIComponent).join("/"), { cache: "no-store" })
        .then(function (r) { if (!r.ok) throw new Error(path); return r.text(); })
        .then(function (text) { return { path: path, text: text }; });
    })).then(function (sent) {
      if (!quacConnected()) return;
      QC.win.postMessage(Object.assign({ kind: "schemas", id: rid, files: sent }, QUAC_PROTOCOL, t && t.mother ? { index: t.mother } : {}), QC.origin);
    }).catch(function (e) { QC.status = "failed"; QC.detail = "could not read " + e.message; renderQuacCardAgain(); quacPresence(); });
  }
  function onQuacMessage(ev) {
    if (!QC.win || ev.source !== QC.win || ev.origin !== QC.origin) return;
    var m = ev.data;
    if (!m || m.protocol !== QUAC_PROTOCOL.protocol || m.version !== QUAC_PROTOCOL.version) return;
    if (m.kind === "hello") {
      clearTimeout(QC.timer);
      var first = QC.state !== "on";
      QC.state = "on"; QC.datasetLoaded = !!m.datasetLoaded;
      if (first && !quacUpToDate()) quacSendSchemas("P" + Date.now().toString(16));   // the first check, unless done
      else if (first) QC.status = "current";
    } else if (m.kind === "status") {
      QC.status = m.status; QC.detail = m.detail || "";
      if (m.status === "needs-dataset") QC.datasetLoaded = false;
    } else if (m.kind === "findings") {
      var fd = m.findings;
      if (!fd || fd.containsData !== false || !Array.isArray(fd.schemaChecks)) return;
      fd.dataset = Object.assign({}, fd.dataset || {}, { name: QC.label });   // never the file's own name
      var ds = quacDataset();
      QC.datasetLoaded = true; QC.status = "sent"; QC.detail = ""; QC.sentAt = Date.now();
      postQuiet("api/inbox", submission([{ kind: "alignment", label: QC.label, findings: fd, request: m.id || undefined,
        dataset: ds ? ds.id : undefined }])).then(function (j) {
        if (!j || !j.ok) { QC.status = "failed"; QC.detail = "your agent's server refused the findings"; renderQuacCardAgain(); }
      }).catch(function () { QC.status = "failed"; QC.detail = "your agent's server is not reachable"; renderQuacCardAgain(); });
    } else if (m.kind === "closed") {
      QC.state = "closed"; QC.win = null;
    }
    renderQuacCardAgain(); quacPresence();
  }
  window.addEventListener("message", onQuacMessage);
  function connectQuac(label, table) {
    QC.label = label; QC.table = table; QC.origin = quacOrigin(); QC.status = ""; QC.detail = ""; QC.handled = (ACT.recheck || {}).id || null;
    if (!quacDataset()) {
      postQuiet("api/inbox", submission([{ kind: "dataset", basis: "browser", label: label, table: table || undefined, text: BROWSER_TEXT }]))
        .catch(function () { /* the next connect sends it again */ });
    }
    QC.state = "opening";
    QC.win = window.open(quacApp() + "#/load?companion=" + encodeURIComponent(location.origin), "schemify-quac");
    clearTimeout(QC.timer);
    QC.timer = setTimeout(function () { if (QC.state === "opening") { QC.state = "silent"; renderQuacCardAgain(); } }, 60000);
    renderQuacCardAgain();
  }
  function disconnectQuac(stop) {
    if (QC.win && !QC.win.closed) QC.win.postMessage(Object.assign({ kind: "close" }, QUAC_PROTOCOL), QC.origin);
    var ds = quacDataset();
    QC.state = "closed"; QC.win = null; quacPresence(); QC.state = "off";
    if (stop && ds) postQuiet("api/inbox", submission([{ kind: "dataset", withdraw: ds.id, text: "Stopped on the website." }])).catch(function () {});
    renderQuacCardAgain();
  }
  function renderQuacCardAgain() { var c = $("#dc-quac"); if (c) renderQuacCard(c.parentNode, c); }
  var QC_SAYS = {
    loading: "Handing QuaC the current schemas…", running: "QuaC is checking your data…", busy: "QuaC is finishing another check; this one follows it.",
    "needs-dataset": "Load your data file in the QuaC tab — the check runs as soon as it is in.",
    "schemas-unusable": "QuaC could not use the schemas", failed: "The check did not finish", sent: "Findings without data sent to your agent",
    current: "Your agent already has a check of this data against the current schemas. Changed your file? Press Check again."
  };
  function renderQuacCard(parent, old) {
    var box = h("div", { id: "dc-quac", class: "sf-card", style: "margin:10px 0" });
    if (old) parent.replaceChild(box, old); else parent.appendChild(box);
    box.appendChild(h("h3", null, "Keep it checked, automatically"));
    box.appendChild(h("p", null, "QuaC opens in its own tab and keeps your data file there, in your browser. Each time your agent changes the schemas, this page hands them to QuaC, QuaC checks your data, and only the findings without data come back to your agent. Your data never leaves the QuaC tab."));
    var ds = QC.label ? quacDataset() : null;
    var known = (S.datasets || []).filter(function (d) { return d.basis === "browser" && !d.withdrawn; });
    if (CONN.mode !== "live") {
      box.appendChild(h("p", { class: "sf-small sf-muted" }, "This needs the website served by your agent (ask it for the address); opened from disk, use the steps below."));
      return;
    }
    if (QC.state === "off" || QC.state === "closed" || QC.state === "silent") {
      if (QC.state === "closed") box.appendChild(h("p", null, chip("Not connected", "outline"), " The QuaC tab was closed or disconnected. Connect again — QuaC still has your file."));
      if (QC.state === "silent") box.appendChild(h("p", null, chip("QuaC did not answer", "warn"), " Press Allow in the QuaC tab. If it shows no such question, that QuaC is too old to connect: use the steps below."));
      var f = { label: QC.label || (known[0] || {}).label || "", table: QC.table || (known[0] || {}).table || ((S.tables || []).length === 1 ? S.tables[0].name : "") };
      var row = h("div", { class: "sf-row", style: "gap:8px;align-items:flex-end;flex-wrap:wrap" });
      row.appendChild(h("label", { class: "sf-label" }, "A name for the data", h("input", { class: "sf-input", value: f.label, placeholder: "2024 baseline export",
        oninput: function (e) { f.label = e.target.value.trim(); } })));
      if ((S.tables || []).length > 1) {
        var sel = h("select", { class: "sf-input", onchange: function (e) { f.table = e.target.value; } }, h("option", { value: "" }, "Which table is it?"));
        S.tables.forEach(function (t) { sel.appendChild(h("option", { value: t.name, selected: t.name === f.table }, (t.title || t.name) + " (" + t.name + ")")); });
        row.appendChild(h("label", { class: "sf-label" }, "Table", sel));
      }
      row.appendChild(btn("Connect QuaC ↗", function () {
        if (!f.label) { toast("Give the data a name first — your agent sees only that, never the file's name.", true); return; }
        if ((S.tables || []).length > 1 && !f.table) { toast("Say which table it is.", true); return; }
        connectQuac(f.label, f.table);
      }, "sf-btn-primary"));
      box.appendChild(row);
      known.forEach(function (d) {
        box.appendChild(h("p", { class: "sf-small sf-muted" }, chip(d.id, "outline"), " " + d.label + " — kept checked since " + fmtDate(d.at) + ". ",
          btn("Stop", function () { QC.label = d.label; QC.table = d.table || ""; disconnectQuac(true); toast("Stopped — your agent is told."); }, "sf-btn-quiet sf-btn-sm")));
      });
      return;
    }
    var line = QC.state === "opening" ? "Opening QuaC… press Allow in its tab." : (QC_SAYS[QC.status] || (QC.datasetLoaded ? "Connected — QuaC has your data." : "Connected — load your data file in the QuaC tab."));
    box.appendChild(h("p", null, chip(QC.state === "opening" ? "Connecting" : "Connected", QC.state === "opening" ? "outline" : "ok"), " ",
      h("strong", null, QC.label), ds ? h("span", { class: "sf-small sf-muted" }, " (" + ds.id + ")") : null));
    box.appendChild(h("p", { role: "status" }, line + (QC.detail ? ": " + QC.detail : "") +
      (QC.status === "sent" && QC.sentAt ? " · " + new Date(QC.sentAt).toLocaleTimeString() : "")));
    box.appendChild(h("div", { class: "sf-row", style: "gap:8px" },
      btn("Check again", function () { if (quacConnected()) quacSendSchemas("P" + Date.now().toString(16)); }, "sf-btn-sm"),
      btn("Show the QuaC tab", function () { if (QC.win) QC.win.focus(); }, "sf-btn-quiet sf-btn-sm"),
      btn("Disconnect", function () { disconnectQuac(false); }, "sf-btn-quiet sf-btn-sm"),
      ds ? btn("Stop for good", function () { disconnectQuac(true); toast("Stopped — your agent is told."); }, "sf-btn-quiet sf-btn-sm") : null));
  }
  function renderRuns(s3) {
    var runs = S.alignment || [];
    s3.appendChild(h("h2", null, "4. How the gap is closing"));
    if (!runs.length) { s3.appendChild(h("p", { class: "sf-empty" }, "Each findings file you send is kept here, so you can watch the mismatches shrink as the schemas improve.")); return; }
    var bars = h("div", { class: "sf-bars", "aria-label": "Share of records with a mismatch, per check" });
    runs.forEach(function (a) {
      var pct = a.records ? Math.round(100 * (a.failing || 0) / a.records) : 0;
      bars.appendChild(h("div", { style: "height:" + Math.max(3, pct) + "%", title: a.id + ": " + pct + "% of records with a mismatch" }, h("span", null, a.id)));
    });
    s3.appendChild(bars);
    s3.appendChild(h("div", { style: "height:18px" }));
    runs.slice().reverse().forEach(function (a) {
      var parsed = a.findings ? parseFindings(a.findings, a.ruleMap) : null;
      s3.appendChild(h("details", null, h("summary", null, a.id + " · " + (a.label || "dataset") + " · " + fmtDate(a.at) + " · " +
        (a.records ? Math.round(100 * (a.failing || 0) / a.records) + "% of " + a.records + " records" : "") + (a.current ? "" : " · made with older schemas") +
        (a.by === "agent" ? " · run by your agent" : "")),
        parsed && !parsed.error ? checksTable(parsed, a.triage || {}, a.planned || [], a.supersededBy) : h("p", { class: "sf-muted" }, "Findings file unavailable.")));
    });
  }
  function readFindings(file) {
    var r = new FileReader();
    r.onload = function () {
      var doc;
      try { doc = JSON.parse(String(r.result)); } catch (e) { toast("That file is not JSON. In QuaC choose Findings without data → JSON.", true); return; }
      var parsed = parseFindings(doc);
      if (parsed.error) { toast(parsed.error, true); return; }
      UI.findingsDraft = { parsed: parsed, label: "real data", note: "" };
      renderDataCheck();
    };
    r.readAsText(file);
  }
  function findingsPreview(fd) {
    var parsed = fd.parsed, doc = parsed.doc;
    var box = h("div", { style: "margin-top:16px" });
    box.appendChild(parsed.matches ? h("p", null, chip("✓ Made with the current schemas", "ok")) :
      h("p", null, chip("Made with a different version of the schema files", "warn"), h("span", { class: "sf-small" },
        " — mismatches may not line up with today's schemas. Re-run QuaC with the folder above for the clearest picture (you can still send these).")));
    var stats = h("div", { class: "sf-stats" });
    findingsStats(doc).forEach(function (s) { stats.appendChild(h("div", { class: "sf-stat" }, h("b", null, s[0] === undefined || s[0] === null ? "—" : String(s[0])), h("span", null, s[1]))); });
    box.appendChild(stats);
    if (parsed.checks.length) box.appendChild(checksTable(parsed, null));
    else box.appendChild(h("p", null, chip("No mismatches — the data fits the schemas", "ok")));
    var label = h("input", { class: "sf-input", value: fd.label, oninput: function (e) { fd.label = e.target.value; } });
    var note = h("textarea", { class: "sf-textarea", placeholder: "Anything your agent should know — e.g. “999 means missing in the 2015 wave”, or “the extra column is a site code we add”.",
      oninput: function (e) { fd.note = e.target.value; } });
    note.value = fd.note;
    box.appendChild(h("label", { class: "sf-label" }, "A name for this dataset (instead of its file name)"));
    box.appendChild(label);
    box.appendChild(h("label", { class: "sf-label" }, "Notes for your agent (optional)"));
    box.appendChild(note);
    var preview = h("pre", { class: "sf-pre" });
    box.appendChild(h("details", { class: "sf-small", ontoggle: function (e) { if (e.target.open) preview.textContent = JSON.stringify(sanitizedFindings(fd), null, 2).slice(0, 40000); } },
      h("summary", null, "Exactly what will be sent"), h("p", null, "The findings as QuaC wrote them, with the dataset's file name replaced by the name above. QuaC builds them from the schema, the column names, and counts — never from values."), preview));
    box.appendChild(h("div", { class: "sf-row", style: "margin-top:10px" },
      btn("Add to outbox", function () { UI.alignmentDraft = { label: fd.label || "real data", note: fd.note || "", findings: sanitizedFindings(fd) }; UI.findingsDraft = null; renderOutboxBar(); renderDataCheck(); toast("Added — send it to your agent when ready."); }, "sf-btn-primary"),
      btn("Discard", function () { UI.findingsDraft = null; renderDataCheck(); }, "sf-btn-quiet")));
    return box;
  }
  function sanitizedFindings(fd) {
    var copy = JSON.parse(JSON.stringify(fd.parsed.doc));
    if (copy.dataset) copy.dataset.name = fd.label || "real data";
    return copy;
  }
  function copyText(text) {
    var ok = function () { toast("Copied."); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok, function () { fallbackCopy(text); });
    else fallbackCopy(text);
  }
  function fallbackCopy(text) {
    var ta = h("textarea", { style: "position:fixed;left:-9999px" }); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast("Copied."); } catch (e) { toast("Copy failed — select the text and copy it.", true); }
    ta.remove();
  }

  // ------------------------------------------------------------------ outbox bar, send, note
  function renderOutboxBar() {
    if (!OB) return;
    var bar = $("#sf-outbox");
    var n = obCount();
    if (!n) { if (bar) bar.remove(); return; }
    if (!bar) { bar = h("div", { class: "sf-outbox", id: "sf-outbox", role: "region", "aria-label": "Outbox" }); document.body.appendChild(bar); }
    clear(bar);
    bar.appendChild(h("span", null, h("strong", null, plural(n, "item")), " ready to send"));
    bar.appendChild(btn(CONN.mode === "live" ? "Review & send" : "Review & save", openSend, "sf-btn-primary sf-btn-sm"));
  }
  function closeModal() { var m = $("#sf-modal"), s = $("#sf-mscrim"); if (m) m.remove(); if (s) s.remove(); }
  function modal(title) {
    closeModal();
    var s = h("div", { class: "sf-scrim", id: "sf-mscrim", onclick: closeModal });
    var m = h("div", { class: "sf-modal", id: "sf-modal", role: "dialog", "aria-modal": "true", "aria-label": title }, h("h2", null, title));
    m.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });
    document.body.appendChild(s); document.body.appendChild(m);
    return m;
  }
  function submission(items) {
    return { schemifyInbox: 1, workspace: S.workspace.id, study: S.workspace.study, from: role(), submittedAt: new Date().toISOString(), items: items };
  }
  function openSend() {
    var items = obItems();
    if (!items.length) { toast("Nothing to send yet."); return; }
    var m = modal("Send to your agent");
    m.appendChild(h("p", { class: "sf-small sf-muted" }, "Answering as " + (role() === "steward" ? "the data steward" : "the author") + ". Check the list, then send."));
    var ul = h("ul", { class: "sf-small" });
    items.forEach(function (it) { ul.appendChild(h("li", null, describeItem(it))); });
    m.appendChild(ul);
    var row = h("div", { class: "sf-row", style: "margin-top:14px" });
    if (CONN.mode === "live") row.appendChild(btn("Send to your agent", function () { sendNow(items); }, "sf-btn-primary"));
    row.appendChild(btn("Download as a file", function () { downloadFeedback(items); }, CONN.mode === "live" ? "" : "sf-btn-primary"));
    row.appendChild(btn("Copy", function () { copyText(JSON.stringify(submission(items))); toast("Copied — paste it into your agent's chat."); }, ""));
    row.appendChild(btn("Keep editing", closeModal, "sf-btn-quiet"));
    m.appendChild(row);
    if (CONN.mode !== "live") m.appendChild(h("p", { class: "sf-small sf-muted", style: "margin-top:10px" },
      "This page is not connected to your agent, so save your answers as a file and tell your agent where it is (for example: “I saved my answers in Downloads”). Or open this page at the address your agent gives you — there, one click sends them."));
    var clearRow = h("p", { class: "sf-small", style: "margin-top:12px" }, btn("Clear the outbox", function () {
      OB = emptyOutbox(); UI.alignmentDraft = null; obSave(); closeModal(); renderAll();
    }, "sf-btn-quiet sf-btn-sm"));
    m.appendChild(clearRow);
  }
  function afterSent(items, id, how) {
    markSent(items, id);
    OB = emptyOutbox();
    UI.alignmentDraft = null;
    obSave(); closeModal(); renderAll();
    toast(how === "sent" ? "Sent ✓. Now tell your agent you are done — type: " + harnessDone() :
      "Saved to your downloads. Tell your agent: “I saved my answers in Downloads” — it will pick them up.");
  }
  function sendNow(items, retried) {
    fetch("api/inbox", { method: "POST", headers: { "Content-Type": "application/json", "X-Schemify-Token": CONN.token || "" }, body: JSON.stringify(submission(items)) })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, j: j }; }); })
      .then(function (res) {
        if (res.j && res.j.ok) { afterSent(items, res.j.id, "sent"); return; }
        if (res.status === 403 && !retried) {
          return fetch("api/session", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (j) { CONN.token = j.token; sendNow(items, true); });
        }
        toast("Not sent: " + ((res.j && res.j.error) || "the agent's server refused it") + ". You can download the answers instead.", true);
      })
      .catch(function () { CONN.mode = "offline"; renderStatus(); renderOutboxBar(); toast("Your agent's server is not reachable. Download the answers as a file instead.", true); openSend(); });
  }
  function downloadFeedback(items) {
    var stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    var blob = new Blob([JSON.stringify(submission(items), null, 2)], { type: "application/json" });
    var a = h("a", { href: URL.createObjectURL(blob), download: "schemify-feedback-" + (S.workspace.slug || "study") + "-" + stamp + ".json" });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    afterSent(items, "download", "download");
  }
  function openNote() {
    var m = modal("A note to your agent");
    m.appendChild(h("p", { class: "sf-small sf-muted" }, "Anything it should know — about the study, how the data was processed, a mistake you spotted. It is recorded as information from you, and used in the schemas where it applies."));
    var ta = h("textarea", { class: "sf-textarea", rows: 6 });
    m.appendChild(ta);
    m.appendChild(h("div", { class: "sf-row", style: "margin-top:10px" }, btn("Add to outbox", function () {
      if (!ta.value.trim()) { ta.focus(); return; }
      OB.notes.push({ text: ta.value.trim() }); obSave(); closeModal(); toast("Added to your outbox.");
    }, "sf-btn-primary"), btn("Cancel", closeModal, "sf-btn-quiet")));
    setTimeout(function () { ta.focus(); }, 0);
  }

  // ------------------------------------------------------------------ boot
  function renderAll() {
    var y = window.scrollY;
    renderStatus(); renderBadges(); renderOverview(); renderQuestions(); renderSkipLogic(); renderEvidence(); renderDataCheck(); renderOutboxBar();
    if (UI.tab === "dictionary") renderDictionary();
    if (UI.openDrawer && UI.openDrawer.type === "variable") openVariable(UI.openDrawer.table, UI.openDrawer.name);
    window.scrollTo(0, y);
  }
  function boot() {
    if (!S || !S.workspace) { var e = $("#sf-boot-error"); if (e) e.hidden = false; return; }
    reindex(); obLoad();
    DICT.semantic = !!lsGet("semantic", false);
    renderTabs(); renderAll(); route(); connect();
    window.addEventListener("hashchange", route);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeDrawer(); closeModal(); } });
    setTimeout(poll, POLL_MS);
    setInterval(function () { if (CONN.mode !== "disk") connect(); }, 30000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
