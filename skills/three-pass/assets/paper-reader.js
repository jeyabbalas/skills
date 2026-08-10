/* paper-reader.js — shared behavior for three-pass reading workspaces.
   Classic script (no ES modules: file:// pages block module CORS). Load with
   defer, AFTER the KaTeX scripts, so math bootstrapping can detect them. */
(function () {
  'use strict';

  /* ---------- live filter (glossary, notes, library) ---------- */

  function initFilters() {
    document.querySelectorAll('input[data-filter]').forEach(function (input) {
      var container = document.querySelector(input.getAttribute('data-filter'));
      if (!container) return;
      var countEl = document.querySelector('.filter-count');
      var entries = Array.prototype.slice.call(container.querySelectorAll('.entry, .card'));
      function apply() {
        var words = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
        var shown = 0;
        entries.forEach(function (el) {
          var hay = (el.textContent + ' ' + (el.getAttribute('data-tags') || '')).toLowerCase();
          var match = words.every(function (w) { return hay.indexOf(w) !== -1; });
          el.hidden = !match;
          if (match) shown += 1;
        });
        if (countEl) {
          countEl.textContent = words.length
            ? shown + ' of ' + entries.length + ' shown'
            : entries.length + ' entries';
        }
      }
      input.addEventListener('input', apply);
      apply();
    });
  }

  /* ---------- expand / collapse all (detailed summary) ---------- */

  function initDetailsTools() {
    document.querySelectorAll('[data-details]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var open = btn.getAttribute('data-details') === 'open';
        document.querySelectorAll('details.sec').forEach(function (d) { d.open = open; });
      });
    });
  }

  /* ---------- print: open every <details>, then restore ---------- */

  function openForPrint() {
    document.querySelectorAll('details:not([open])').forEach(function (d) {
      d.setAttribute('data-print-opened', '');
      d.open = true;
    });
  }
  function restoreAfterPrint() {
    document.querySelectorAll('details[data-print-opened]').forEach(function (d) {
      d.open = false;
      d.removeAttribute('data-print-opened');
    });
  }

  /* ---------- math: render if KaTeX loaded, banner if not ---------- */

  function initMath() {
    if (!document.body.hasAttribute('data-math')) return;
    if (typeof window.renderMathInElement === 'function') {
      window.renderMathInElement(document.body, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false }
        ],
        trust: function (ctx) { return ctx.command === '\\htmlClass'; },
        strict: 'ignore',
        throwOnError: false
      });
      initTermSync();
    } else {
      var banner = document.createElement('div');
      banner.className = 'banner chrome';
      banner.textContent = 'Math rendering unavailable (offline) — formulas are shown as LaTeX source.';
      var page = document.querySelector('.page') || document.body;
      page.prepend(banner);
    }
  }

  /* ---------- equation term ↔ legend sync ----------
     Terms are rendered by KaTeX \htmlClass{term tN term-<id>}{...}; legend rows
     carry data-term="<id>". Hover highlights transiently; click pins. */

  function termId(el) {
    for (var i = 0; i < el.classList.length; i++) {
      if (el.classList[i].indexOf('term-') === 0) return el.classList[i].slice(5);
    }
    return null;
  }

  function initTermSync() {
    document.querySelectorAll('.eq').forEach(function (eq) {
      var rows = eq.querySelectorAll('.legend-row[data-term]');
      var spans = eq.querySelectorAll('.term');
      function setActive(id) {
        if (!id) {
          eq.classList.remove('has-active');
          eq.querySelectorAll('.is-active').forEach(function (el) { el.classList.remove('is-active'); });
          return;
        }
        eq.classList.add('has-active');
        spans.forEach(function (s) { s.classList.toggle('is-active', termId(s) === id); });
        rows.forEach(function (r) { r.classList.toggle('is-active', r.getAttribute('data-term') === id); });
      }
      function settle() { setActive(eq.getAttribute('data-pinned') || null); }
      function bind(el, id) {
        el.addEventListener('mouseenter', function () { setActive(id); });
        el.addEventListener('mouseleave', settle);
        el.addEventListener('click', function () {
          if (eq.getAttribute('data-pinned') === id) eq.removeAttribute('data-pinned');
          else eq.setAttribute('data-pinned', id);
          settle();
        });
      }
      rows.forEach(function (r) { bind(r, r.getAttribute('data-term')); });
      spans.forEach(function (s) { var id = termId(s); if (id) bind(s, id); });
    });
  }

  /* ---------- relationship / reference maps ----------
     A .map element contains <script type="application/json" class="map-data">
     with {nodes: [{id, label, sub, col, row, href}], edges: [{from, to, label,
     kind}]}. Nodes lay out on a fixed grid (deterministic — the agent iterates
     by editing the data, and the same data always draws the same picture).
     Clicking a node toggles the matching #panel-<id> if present, else follows
     href. Edge kinds: builds-on | contrasts | shares-method | same-problem. */

  var CELL_W = 230, CELL_H = 120, NODE_W = 195, NODE_H = 64, PAD = 12;

  function clipToRect(cx, cy, tx, ty, halfW, halfH, gap) {
    var dx = tx - cx, dy = ty - cy;
    var t = 1;
    if (dx !== 0) t = Math.min(t, (halfW + gap) / Math.abs(dx));
    if (dy !== 0) t = Math.min(t, (halfH + gap) / Math.abs(dy));
    return { x: cx + dx * t, y: cy + dy * t };
  }

  function svgEl(name, attrs) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', name);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  }

  function renderMap(map) {
    var dataEl = map.querySelector('script.map-data');
    if (!dataEl) return;
    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var nodes = data.nodes || [], edges = data.edges || [];
    if (!nodes.length) return;

    var byId = {};
    var maxCol = 0, maxRow = 0;
    nodes.forEach(function (n) {
      n.x = PAD + n.col * CELL_W;
      n.y = PAD + n.row * CELL_H;
      byId[n.id] = n;
      maxCol = Math.max(maxCol, n.col);
      maxRow = Math.max(maxRow, n.row);
    });
    var w = PAD * 2 + maxCol * CELL_W + NODE_W;
    var h = PAD * 2 + maxRow * CELL_H + NODE_H;

    var svg = svgEl('svg', { viewBox: '0 0 ' + w + ' ' + h, role: 'img' });
    var defs = svgEl('defs', {});
    var marker = svgEl('marker', {
      id: 'map-arrow-head', class: 'map-arrow', viewBox: '0 0 10 10',
      refX: '9', refY: '5', markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse'
    });
    marker.appendChild(svgEl('path', { d: 'M 0 0 L 10 5 L 0 10 z' }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    var labels = [];
    edges.forEach(function (e) {
      var a = byId[e.from], b = byId[e.to];
      if (!a || !b) return;
      var acx = a.x + NODE_W / 2, acy = a.y + NODE_H / 2;
      var bcx = b.x + NODE_W / 2, bcy = b.y + NODE_H / 2;
      var p1 = clipToRect(acx, acy, bcx, bcy, NODE_W / 2, NODE_H / 2, 4);
      var p2 = clipToRect(bcx, bcy, acx, acy, NODE_W / 2, NODE_H / 2, 8);
      var g = svgEl('g', { class: 'map-edge ' + (e.kind || '') });
      g.appendChild(svgEl('line', {
        x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, 'marker-end': 'url(#map-arrow-head)'
      }));
      svg.appendChild(g);
      if (e.label) {
        /* near-horizontal neighbors leave no gap for a label — set it below the nodes */
        var nearHorizontal = Math.abs(acy - bcy) < NODE_H;
        var ly = nearHorizontal
          ? Math.max(a.y, b.y) + NODE_H + 14
          : (p1.y + p2.y) / 2 - 5;
        labels.push({ x: (p1.x + p2.x) / 2, y: ly, text: e.label, kind: e.kind || '' });
      }
    });

    nodes.forEach(function (n) {
      var g = svgEl('g', {
        class: 'map-node', transform: 'translate(' + n.x + ',' + n.y + ')',
        tabindex: '0', role: 'button', 'aria-expanded': 'false', 'data-node': n.id
      });
      var title = svgEl('title', {});
      title.textContent = n.title || n.label;
      g.appendChild(title);
      g.appendChild(svgEl('rect', { width: NODE_W, height: NODE_H, rx: 10 }));
      var t1 = svgEl('text', { class: 't', x: 14, y: 27 });
      t1.textContent = n.label;
      g.appendChild(t1);
      if (n.sub) {
        var t2 = svgEl('text', { class: 's', x: 14, y: 47 });
        t2.textContent = n.sub;
        g.appendChild(t2);
      }
      function activate() {
        var panel = document.getElementById('panel-' + n.id);
        if (panel) {
          var opening = panel.hidden;
          map.parentNode.querySelectorAll('.map-profile').forEach(function (p) { p.hidden = true; });
          svg.querySelectorAll('.map-node').forEach(function (m) {
            m.classList.remove('is-open');
            m.setAttribute('aria-expanded', 'false');
          });
          if (opening) {
            panel.hidden = false;
            g.classList.add('is-open');
            g.setAttribute('aria-expanded', 'true');
            panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          }
        } else if (n.href) {
          window.location.href = n.href;
        }
      }
      g.addEventListener('click', activate);
      g.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); activate(); }
      });
      svg.appendChild(g);
    });

    /* labels last, above everything, halo keeping them readable over any overlap */
    labels.forEach(function (l) {
      var g = svgEl('g', { class: 'map-edge ' + l.kind });
      var t = svgEl('text', { x: l.x, y: l.y, 'text-anchor': 'middle' });
      t.textContent = l.text;
      g.appendChild(t);
      svg.appendChild(g);
      h = Math.max(h, l.y + 8);
    });
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);

    map.insertBefore(svg, dataEl);
  }

  /* ---------- figure image zoom ---------- */

  function initZoom() {
    document.addEventListener('click', function (ev) {
      var img = ev.target.closest && ev.target.closest('.figure img');
      if (img) img.classList.toggle('zoomed');
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') {
        document.querySelectorAll('.figure img.zoomed').forEach(function (img) {
          img.classList.remove('zoomed');
        });
      }
    });
  }

  /* ---------- boot ---------- */

  function init() {
    initFilters();
    initDetailsTools();
    initMath(); /* also wires term sync after KaTeX renders */
    document.querySelectorAll('.map').forEach(renderMap);
    initZoom();
    window.addEventListener('beforeprint', openForPrint);
    window.addEventListener('afterprint', restoreAfterPrint);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
