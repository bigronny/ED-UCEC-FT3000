// ED Target Board page - shared by every file: the page registry and the view (which tab and page
// shows), the board's data, text effects, formatting, the ID mark, reporting to the board.
// Files load in the order index.html lists them; each adds what it offers to window.ED.
(function () {
  "use strict";
  var ED = window.ED = {};
  var $ = function (id) { return document.getElementById(id); };
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var LOCK_MS = 90000;
  // S: the board's latest data (S.data), the UFC's record (S.ufc), and each page's own working state
  var S = { data: null, sel: null, railSig: "", railKeys: null, panelKey: null, chipSig: "",
            scanSeen: {}, pct: {}, story: {}, storyStatus: {}, first: true };

  // ---- pages: each tab is made of pages, in sub-tabs; main.js says what a page can have ----
  var TABS = {};                        // tab -> [its page 1, page 2, ...]
  var ORDER = [];                       // every page, in the order registered (updates run in this order)
  var view = { tab: null, sub: 1 };     // where you are: a tab and its page (shared with the board)
  function page(def) {
    (TABS[def.tab] = TABS[def.tab] || [])[def.sub - 1] = def;
    ORDER.push(def);
    return def;
  }
  function pages() { return ORDER.slice(); }
  function here() { var t = TABS[view.tab]; return t ? t[view.sub - 1] || null : null; }
  function showing(tab, sub) { return view.tab === tab && (!sub || view.sub === sub); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function cr(n) { return n ? Number(n).toLocaleString("en-GB") + " CR" : "-"; }
  function msLeft(iso) { return iso ? Date.parse(iso) - Date.now() : NaN; }
  function left(iso, short) {
    var ms = msLeft(iso);
    if (isNaN(ms)) return "-";
    if (ms <= 0) return "Expired";
    var d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5) % 24, m = Math.floor(ms / 6e4) % 60;
    if (short) return d ? d + "d " + h + "h" : h + "h " + m + "m";
    return (d ? d + "d " : "") + (d || h ? h + "h " : "") + m + "m";
  }
  function ago(iso) {
    var s = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
    if (s < 90) return s + "s ago";
    if (s < 5400) return Math.round(s / 60) + "m ago";
    return Math.round(s / 3600) + "h ago";
  }
  function clock(iso) {
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleTimeString("en-GB", { hour12: false });
  }
  function blocks(p) {
    var n = Math.max(0, Math.min(12, Math.round((Number(p) || 0) / 100 * 12)));
    return new Array(n + 1).join("\u2588") + new Array(12 - n + 1).join("\u2591");
  }
  function replay(el, cls) {
    if (reduce.matches) return;
    el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls);
  }
  function stop(el) {
    if (el._rs) { clearInterval(el._rs); el._rs = null; }
    if (el._tw) { clearInterval(el._tw); el._tw = null; }
  }

  // ---- motion: text resolve, typewriter, phosphor ghost ----
  var GLYPHS = "\u2591\u2592\u2593\u25880123456789ABCDEF#/";
  function resolve(el, text, html) {
    stop(el); el._final = text;
    if (reduce.matches) { if (html) el.innerHTML = html; else el.textContent = text; return; }
    var f = 0, N = 16;
    el._rs = setInterval(function () {
      f++;
      var fixed = Math.floor(text.length * f / N), out = text.slice(0, fixed);
      for (var i = fixed; i < text.length; i++) out += text[i] === " " ? " " : GLYPHS[(Math.random() * GLYPHS.length) | 0];
      el.textContent = out;
      if (f >= N) { stop(el); if (html) el.innerHTML = html; else el.textContent = text; }
    }, 35);
  }
  function setText(el, text, animate) {
    var cur = el._final != null ? el._final : el.textContent;
    if (cur === text) return;
    if (animate) { resolve(el, text); } else { stop(el); el._final = text; el.textContent = text; }
  }
  function typeOut(el, text) {
    stop(el); el._final = text;
    if (reduce.matches) { el.textContent = text; return; }
    el.textContent = "";
    var node = document.createTextNode(""), cursor = document.createElement("span");
    cursor.className = "blink"; cursor.textContent = "_";
    el.appendChild(node); el.appendChild(cursor);
    var i = 0;
    el._tw = setInterval(function () {
      i = Math.min(text.length, i + 3); node.data = text.slice(0, i);
      if (i >= text.length) { stop(el); cursor.remove(); }
    }, 18);
  }
  function ghost(el, oldText) {
    if (reduce.matches || !oldText) return;
    var g = document.createElement("span");
    g.className = "ghost"; g.textContent = oldText;
    el.appendChild(g);
    setTimeout(function () { g.remove(); }, 1100);
  }

  // ---- ID mark generated from the target's name ----
  function hash(s) {
    var h = 2166136261 >>> 0;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h;
  }
  function sigil(name) {
    var h = hash(String(name).toLowerCase());
    function r(shift, mod) { return (h >>> shift) % mod; }
    function pt(a, rad) {
      var t = (a - 90) * Math.PI / 180;
      return (28 + rad * Math.cos(t)).toFixed(2) + " " + (28 + rad * Math.sin(t)).toFixed(2);
    }
    var a0 = r(0, 360), span = 50 + r(9, 140), d1 = 1 + r(3, 3), d2 = 2 + r(5, 4);
    var ticks = "";
    for (var k = 0; k < 3; k++) {
      var a = (a0 + 70 + k * (40 + r(11 + k * 3, 60))) % 360;
      ticks += '<path d="M' + pt(a, 14) + " L" + pt(a, 19) + '" stroke="#45f08a" stroke-width="1"></path>';
    }
    return '<svg viewBox="0 0 56 56" width="56" height="56" aria-hidden="true">' +
      '<circle cx="28" cy="28" r="26.5" fill="none" stroke="#1d4a2a"></circle>' +
      '<circle cx="28" cy="28" r="20" fill="none" stroke="#25b85c" stroke-dasharray="' + d1 + " " + d2 + '"></circle>' +
      '<circle cx="28" cy="28" r="12" fill="none" stroke="#45f08a" stroke-width="1.2"></circle>' +
      '<path d="M' + pt(a0, 26.5) + " A26.5 26.5 0 " + (span > 180 ? 1 : 0) + " 1 " + pt(a0 + span, 26.5) +
      '" fill="none" stroke="#e3a24a" stroke-width="2"></path>' + ticks +
      '<circle cx="' + pt(r(13, 360), 3 + r(17, 6)).replace(" ", '" cy="') + '" r="2.4" fill="#8affc1"></circle></svg>';
  }
  // ---- telling the board what this page shows ----
  // {tab, sub}: where you are (the UFC's ':' marks that tab); {pick: {list: key}}: what's picked in a list
  // ("targets", "ocor", "syst", "hist" or "chist"), where the UFC knob starts
  function reportView(v) {
    fetch("/api/select", { method: "POST", headers: { "Content-Type": "application/json" },
                           body: JSON.stringify(v) }).catch(function () {});
  }
  // COMM2 knob: scroll a panel two lines per click (a phone held upright scrolls the whole page)
  function scrollBox(box, clicks) {
    var step = Math.round(parseFloat(getComputedStyle(document.body).fontSize) * 1.25 * 2);
    if (box && box.offsetParent && box.scrollHeight - box.clientHeight > 1) box.scrollTop += clicks * step;
    else window.scrollBy(0, clicks * step);
  }
  // a start-up / journal message (Home and Contracts show it in place of their panel)
  function showNote(s) {
    Array.prototype.forEach.call(document.querySelectorAll(".emsg"), function (el) {
      el.textContent = s.note || "";
      el.className = "emsg" + (s.note ? " bad" : "");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".emsg2"), function (el) { el.hidden = true; });
  }
  function num(n) { return n === null || n === undefined ? "-" : Number(n).toLocaleString("en-GB"); }
  function cr0(n) { return Number(n || 0).toLocaleString("en-GB") + " CR"; }
  var STALE_MS = 12 * 36e5;   // a briefing pasted longer ago than this shows its age in red
  function sinceTxt(iso, bare) {
    var ms = Date.now() - Date.parse(iso);
    if (isNaN(ms)) return "";
    ms = Math.max(0, ms);
    if (ms < 6e4) return bare ? "0m" : "just now";
    var d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5) % 24, m = Math.floor(ms / 6e4) % 60;
    var t = d ? d + "d " + h + "h" : h ? h + "h " + m + "m" : m + "m";
    return bare ? t : t + " ago";
  }
  function pastedAt(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return "";
    var t = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
    return d.toDateString() === new Date().toDateString() ? t
      : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" }) + " " + t;
  }
  ED.S = S; ED.$ = $; ED.reduce = reduce;
  ED.ZOOM_TRAVEL = 8;   // the UFC's COMM1 VOLUME dial turned end to end zooms by this much

  // ---- the copy / paste button beside a system's name (OCOR, Contracts): the board puts the name on the PC's
  // clipboard; pressing again pastes it into Elite (Ctrl+V - into the galaxy map's search box, say) ----
  var CLIP_PASTE_MS = 120000;
  ED.clipPress = function (text, pull) {   // pull: the UFC pull it answers (only the first page to say counts)
    if (!text) return;
    try {
      fetch("/api/clip", { method: "POST", headers: { "Content-Type": "application/json" },
                           body: JSON.stringify({ text: text, pull: typeof pull === "number" ? pull : null }) }).catch(function () {});
    } catch (err) { /* nothing to tell */ }
  };
  ED.clipShow = function () {   // each button's label, from the last press (and how long ago it was heard of)
    var c = (S.ufc || {}).clip || {}, age = S.clipAt ? Date.now() - S.clipAt : Infinity;
    Array.prototype.forEach.call(document.querySelectorAll("button.clipb"), function (b) {
      var mine = !!c.text && b.dataset.clip === c.text;
      var st = !mine ? "" : c.state === "copied" && age < CLIP_PASTE_MS ? "paste" :
        c.did === "paste" && age < 3000 ? (c.ok ? "pasted" : "notpasted") : "";
      var txt = { paste: "Paste", pasted: "Pasted", notpasted: "Not pasted" }[st] || "Copy";
      if (b.textContent !== txt) b.textContent = txt;
      ["paste", "pasted", "notpasted"].forEach(function (c) { b.classList.toggle(c, c === st); });   // (keeps its UFC focus)
      b.title = st === "notpasted" ? (c.why || "") : st === "paste" ? "Press again to paste it into Elite (Ctrl+V)" : "Copy this system's name";
    });
  };
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button.clipb");
    if (b && b.dataset.clip) ED.clipPress(b.dataset.clip, null);
  });
  // who this page is, to the board (the UFC's displays follow the first page opened); kept through a
  // reload, so reloading doesn't lose its place
  ED.pageId = (function () {
    var id = "";
    try { id = sessionStorage.getItem("ft3000-page") || ""; } catch (e) { /* storage blocked */ }
    if (!/^[a-z0-9]{6,32}$/.test(id)) {
      id = (Date.now().toString(36) + Math.random().toString(36).slice(2, 10)).slice(0, 24);
      try { sessionStorage.setItem("ft3000-page", id); } catch (e) { /* storage blocked */ }
    }
    return id;
  })();
  ED.tabs = TABS; ED.view = view; ED.page = page; ED.pages = pages; ED.here = here; ED.showing = showing;
  ED.scrollBox = scrollBox; ED.showNote = showNote;
  ED.LOCK_MS = LOCK_MS;
  ED.STALE_MS = STALE_MS;
  ED.ago = ago;
  ED.blocks = blocks;
  ED.clock = clock;
  ED.cr = cr;
  ED.cr0 = cr0;
  ED.esc = esc;
  ED.ghost = ghost;
  ED.left = left;
  ED.msLeft = msLeft;
  ED.num = num;
  ED.pastedAt = pastedAt;
  ED.replay = replay;
  ED.reportView = reportView;
  ED.resolve = resolve;
  ED.setText = setText;
  ED.sigil = sigil;
  ED.sinceTxt = sinceTxt;
  ED.stop = stop;
  ED.typeOut = typeOut;
})();
