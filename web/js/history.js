// ED Target Board page - 2 Nav, sub-tab 2 (Hist): everywhere you've been; and 3 Contracts, sub-tab 2 (History):
// every mission you've finished. Both lists come from the board, which reads all your journals; the toggles above
// each are the board's too, so the UFC's COMM1 knob steps through just what shows (a pull picks the highlighted
// row). The COMM2 knob steps across the toggles, the copy button and the details (and then scrolls them); a short
// pull flips the toggle or presses the button.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  var CHUNK = 160, PART = 400;   // rows drawn at a time, and fetched at a time: more as the list is scrolled down, or the knob goes past them
  var WORDS = { jump: "Jump", cjump: "Carrier", dock: "Dock", orbit: "Orbit", land: "Land", near: "Near", here: "" };
  var MARKS = { dock: "docked", orbit: "orbit", land: "landed" };   // how you were there: the icon beside the word
  var OUTS = { completed: "Completed", failed: "Failed", abandoned: "Abandoned" };

  function dayOf(iso) { var d = new Date(iso); return isNaN(d) ? "" : d.toDateString(); }
  function dayText(iso) {
    var d = new Date(iso), now = new Date();
    if (isNaN(d)) return "";
    var full = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    if (d.toDateString() === now.toDateString()) return "Today \u00b7 " + full;
    if (d.toDateString() === new Date(now - 864e5).toDateString()) return "Yesterday \u00b7 " + full;
    return full;
  }
  function hhmm(iso) {
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  function post(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }

  // ---- what both pages share: the list (fetched from the board when it changes), the toggles and totals,
  // the selection and its details, the UFC's knobs ----
  function HistPage(o) {
    var P = { v: null, rows: [], at: {}, total: 0, shown: 0, lastDay: "", sel: null, item: null, itemFor: null, filters: {},
              totals: {}, focus: null, busy: false, again: false, cache: {} };   // rows: the list as far as it's been fetched
    var list = $(o.ids.list), box = $(o.ids.pc);

    function showing() { return ED.showing(o.tab, o.sub); }
    function url(start, count, want) {
      return "/api/hist?page=" + o.page + "&start=" + start + "&count=" + count + (want ? "&want=" + encodeURIComponent(want) : "");
    }
    function get(u, then) {
      P.busy = true;
      fetch(u, { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (j) {
        P.busy = false;
        then(j);
        if (P.again) { P.again = false; load(); }
      }, function () { P.busy = false; });
    }
    function load() {   // the list from the top, as the board has it now (as far as it had been fetched, and the selection)
      if (P.busy) { P.again = true; return; }
      get(url(0, Math.max(PART, P.rows.length), P.sel), took);
    }
    function fetchMore(want) {   // the next part of the list (at least as far as the row want)
      if (P.busy || P.rows.length >= P.total) return;
      get(url(P.rows.length, PART, want), function (j) {
        if (j.v !== P.v || j.start !== P.rows.length) { P.again = true; return; }   // changed meanwhile: from the top again
        (j.rows || []).forEach(function (r) { P.at[r.k] = P.rows.length; P.rows.push(r); });
        more(want in P.at ? P.at[want] + 20 : 0);
        if (want) ED.applyCursor(true);
      });
    }
    function took(j) {
      P.v = j.v; P.rows = j.rows || []; P.total = j.total || 0; P.filters = j.filters || {}; P.totals = j.totals || {};
      P.ready = j.ready; P.progress = j.progress;
      P.itemFor = null;   // (its details may have changed too)
      P.at = {};
      P.rows.forEach(function (r, i) { P.at[r.k] = i; });
      if (P.sel === null || !(P.sel in P.at)) P.sel = P.rows.length ? P.rows[0].k : null;   // (a toggle hid it: the newest)
      S[o.selKey] = P.sel;
      if (P.sel) ED.reportView({ pick: (function (p) { p[o.list] = P.sel; return p; })({}) });
      draw(true);
      ED.applyCursor(false);
    }
    // the rows (with a line for each new day): the first CHUNK, and more as needed
    function more(upTo) {
      var end = Math.min(P.rows.length, Math.max(P.shown + CHUNK, upTo || 0)), html = "";
      for (var i = P.shown; i < end; i++) {
        var r = P.rows[i];
        if (!r.d) {
          var day = dayOf(r.ts);
          if (day !== P.lastDay) { P.lastDay = day; html += '<div class="hday">' + ED.esc(dayText(r.ts)) + "</div>"; }
        }
        html += o.row(r, r.k === P.sel);
      }
      P.shown = end;
      list.insertAdjacentHTML("beforeend", html);
    }
    function draw(reset) {
      var page = $(o.ids.page);
      var top = list.scrollTop, had = P.shown;
      if (reset) { list.innerHTML = ""; P.shown = 0; P.lastDay = ""; }
      var none = !P.rows.length;
      page.classList.toggle("hnone", none);
      $(o.ids.railmsg).textContent = !none ? "" : P.ready === false ? "Reading journals" : o.empty(P.filters);
      if (!none && P.shown === 0) { more(Math.max(had, P.sel in P.at ? P.at[P.sel] + 20 : 0)); list.scrollTop = top; }   // (where it was)
      Array.prototype.forEach.call($(o.ids.page).querySelectorAll(".htg"), function (b) {
        var on = !!P.filters[b.dataset.tg];
        b.classList.toggle("on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      $(o.ids.tot).textContent = o.totals(P.totals, P.filters);
      var pr = P.progress || [0, 0];
      $(o.ids.foot).textContent = P.ready === false ? "Reading journals" + (pr[1] ? " " + pr[0] + " / " + pr[1] : "") : "Journals read";
      if (P.sel) open(P.sel); else details(null);
      if (reset && P.sel && !top) { var row = list.querySelector('[data-key="' + cssKey(P.sel) + '"]'); if (row) row.scrollIntoView({ block: "nearest" }); }
    }
    function cssKey(k) { return String(k).replace(/["\\]/g, "\\$&"); }
    function itemKey(k) { var r = P.rows[P.at[k]]; return r ? (o.place ? r.p : r.k) : null; }
    function open(k) {   // the selected row's details (a place on Hist, a mission on History)
      var key = itemKey(k);
      if (!key) { details(null); return; }
      if (P.itemFor === key && P.item) return;
      if (P.cache[key] && P.cache[key].v === P.v) { P.itemFor = key; details(P.cache[key].item, true); return; }
      P.itemFor = key;
      fetch("/api/hist/item?page=" + o.page + "&key=" + encodeURIComponent(key), { cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (item) {
          if (P.itemFor !== key) return;
          P.cache[key] = { v: P.v, item: item };
          details(item, true);
        }, function () { if (P.itemFor === key) details(null); });
    }
    function details(item, fresh) {
      var page = $(o.ids.page), had = P.item && P.item.key;
      P.item = item;
      page.classList.toggle("hnoitem", !item);
      if (!item) return;
      if (fresh && had !== item.key) { ED.replay(box, "pull"); box.scrollTop = 0; }
      o.detail(item);
      focusClasses();
    }
    function pick(k) {   // a click on a row, or a COMM1 pull on the UFC
      if (!(k in P.at)) return;
      var old = list.querySelector(".sel");
      if (old) { old.classList.remove("sel"); old.setAttribute("aria-pressed", "false"); }
      P.sel = k;
      S[o.selKey] = k;
      var row = list.querySelector('[data-key="' + cssKey(k) + '"]');
      if (row) { row.classList.add("sel"); row.setAttribute("aria-pressed", "true"); }
      ED.reportView({ pick: (function (p) { p[o.list] = k; return p; })({}) });
      open(k);
    }
    function cursor(u, scroll) {   // the UFC knob's highlight (page menu)
      var on = u.menu === "PAGE", cur = on ? (u.cursors || {})[o.list] : null;
      if (cur && !(cur in P.at) && P.v !== null) fetchMore(cur);   // further down than fetched yet
      if (cur && cur in P.at && P.at[cur] >= P.shown && P.shown) more(P.at[cur] + 20);
      Array.prototype.forEach.call(list.querySelectorAll(".cur"), function (b) { if (b.dataset.key !== cur) b.classList.remove("cur"); });
      if (cur) {
        var row = list.querySelector('[data-key="' + cssKey(cur) + '"]');
        if (row) { row.classList.add("cur"); if (scroll && showing()) row.scrollIntoView({ block: "nearest" }); }
      }
      focusClasses();
    }
    // ---- the COMM2 knob: the toggles, the copy button, then the details (which it scrolls) ----
    function stops() {
      var out = o.toggles.map(function (t) { return "tg-" + t; });
      if (!$(o.ids.clip).hidden) out.push("copy");
      out.push("data");
      return out;
    }
    function focusClasses() {
      var ufc = (S.ufc || {}).menu === "PAGE";
      Array.prototype.forEach.call($(o.ids.page).querySelectorAll("[data-f]"), function (b) {
        b.classList.toggle("focus", ufc && b.dataset.f === P.focus);
      });
      box.classList.toggle("focus", ufc && P.focus === "data");
    }
    function scroll(clicks) {   // a click at a time (several can arrive together)
      var order = stops(), step = Math.round(parseFloat(getComputedStyle(document.body).fontSize) * 1.25 * 2);
      for (var n = 0; n < Math.abs(clicks); n++) {
        var i = order.indexOf(P.focus);
        if (i < 0) P.focus = order[0];
        else if (clicks > 0) {
          if (P.focus === "data") box.scrollTop += step;
          else P.focus = order[i + 1];
        } else if (P.focus === "data" && box.scrollTop > 0) box.scrollTop -= step;
        else P.focus = order[Math.max(0, i - 1)];
      }
      focusClasses();
    }
    function pull() {   // a short COMM2 pull: flip the toggle, or press the copy button
      if (P.focus && P.focus.indexOf("tg-") === 0) toggle(P.focus.slice(3));
      else if (P.focus === "copy" && P.item && P.item.copy) ED.clipPress(P.item.copy, (S.ufc || {}).c2pull_n);
    }
    function toggle(name) {
      P.filters[name] = !P.filters[name];
      draw(false);
      post("/api/histfilter", { page: o.page, name: name, on: P.filters[name] }).then(load, load);
    }

    list.addEventListener("click", function (e) {
      var b = e.target.closest("[data-key]");
      if (b) pick(b.dataset.key);
    });
    list.addEventListener("scroll", function () {
      if (list.scrollTop + list.clientHeight < list.scrollHeight - 400) return;
      if (P.shown < P.rows.length) more();
      else fetchMore();
    });
    Array.prototype.forEach.call($(o.ids.page).querySelectorAll(".htg"), function (b) {
      b.addEventListener("click", function () { toggle(b.dataset.tg); });
    });

    ED.page({
      tab: o.tab, sub: o.sub, key: o.key, label: o.label, el: o.ids.page, mode: o.mode || "", back: o.back, list: o.list,
      update: function (s) {   // the board says when its lists change: fetched again while this page shows
        var h = s.hist || {};
        if (showing() && h.v !== undefined && h.v !== P.v) load();
        else if (P.v !== null && h.ready !== P.ready) { P.ready = h.ready; P.progress = h.progress; }
      },
      enter: function () { P.focus = null; P.item = null; P.itemFor = null; load(); if (o.enter) o.enter(); },
      leave: function () { if (o.leave) o.leave(); },
      cursor: cursor, pick: pick, scroll: scroll, pull: pull
    });
    return P;
  }

  // ---- 2 Nav › Hist: everywhere you've been ----
  var hiPic = { pic: null, schem: null, plan: null, rot: 0, tilt: -12, raf: 0, t: 0 };
  function navRow(r, sel) {
    var mark = MARKS[r.t] ? ED.icon(MARKS[r.t]) : "";
    return '<button type="button" class="srow hrow' + (r.d ? " k1" : "") + (r.t === "jump" || r.t === "cjump" || r.t === "here" ? "" : " st") +
      (sel ? " sel" : "") + '" data-key="' + ED.esc(r.k) + '" aria-pressed="' + sel + '"><span class="nm">' + ED.icon(r.i) + ED.esc(r.n) +
      (r.s ? '<span class="hs"> \u00b7 ' + ED.esc(r.s) + "</span>" : "") + '</span><span class="rt"><span class="hw">' + mark +
      ED.esc(WORDS[r.t] || "") + "</span> " + ED.esc(hhmm(r.ts)) + "</span></button>";
  }
  function navDetail(it) {
    ED.setText($("hi-case"), it.lab || "", false);
    ED.setText($("hi-name"), it.name || "", false);
    $("hi-chips").innerHTML = (it.chips || []).map(function (c, i) { return '<span class="chip' + (i ? " dim" : "") + '">' + ED.esc(c) + "</span>"; }).join("");
    $("hi-sys").textContent = it.system || "";   // (the copy button beside it: for the galaxy map's search box)
    $("hi-clip").hidden = !it.copy;
    if ($("hi-clip").dataset.clip !== it.copy) { $("hi-clip").dataset.clip = it.copy || ""; ED.clipShow(); }
    $("hi-grid").innerHTML = (it.rows || []).map(function (r) {
      return '<div class="cell' + (r[2] ? " wide" : "") + '"><span class="lab">' + ED.esc(r[0]) + '</span><span class="v">' + ED.esc(r[1]) + "</span></div>";
    }).join("");
    $("hi-vis").innerHTML = (it.log || []).map(function (l) {
      return '<div class="hv"><span class="d">' + ED.esc(l[0]) + '</span><span>' + ED.esc(l[1]) + "</span></div>";
    }).join("");
    // the picture: the planet (its settlements, where you landed), the station, or the settlement's confirmed layout
    var p = it.pic || { kind: "star" };
    hiPic.pic = p;
    hiPic.schem = it.schem || null;
    hiPic.plan = null;
    hiPic.rot = p.lon != null ? p.lon : 0;
    hiPic.tilt = p.lat != null ? Math.max(-60, Math.min(60, p.lat)) : -12;
    if (hiPic.schem) {
      var want = hiPic.schem;
      ED.schem.get(want.category, want.count).then(function (plans) {
        if (hiPic.schem !== want) return;
        hiPic.plan = plans.filter(function (x) { return x.id === want.id; })[0] || null;
        hiPic.rot = 0;
        picDraw();
      }, function () { /* the planet, then */ });
    }
    picDraw();
    picAnimate();
  }
  function picDraw() {
    var svg = $("hi-svg"), cw = svg.clientWidth;
    if (!hiPic.pic || !cw) return;
    var px = 140 / cw, html;
    if (hiPic.plan) html = ED.schem.draw(hiPic.plan, { rot: hiPic.rot, tilt: 35, zoom: 1, pan: [0, 0], hw: 70, hh: 70, px: px, max: false,
                                                       icons: {} });
    else html = ED.sysPic(hiPic.pic, hiPic.rot, hiPic.tilt, px);
    svg.innerHTML = html;
    ED.pixel.draw(svg, $("hi-px"), { x: 0, y: 0, w: 140, h: 140 });
  }
  function picLoop(t) {   // the picture turns slowly while the page shows
    hiPic.raf = 0;
    if (!ED.showing("nav", 7) || S.halted || ED.hyper.on() || !hiPic.pic) return;
    var dt = hiPic.t ? Math.min(100, t - hiPic.t) : 0;
    hiPic.t = t;
    var globe = hiPic.pic.kind === "globe" || hiPic.pic.kind === "star";
    hiPic.rot = (hiPic.rot + dt * (hiPic.plan ? 0.01 : globe ? 0.008 : 0.014)) % 360;
    picDraw();
    hiPic.raf = requestAnimationFrame(picLoop);
  }
  function picAnimate() {
    if (reduce.matches || hiPic.raf || !ED.showing("nav", 7)) return;
    hiPic.t = 0;
    hiPic.raf = requestAnimationFrame(picLoop);
  }
  var NAV_NAMES = { systems: "system", stations: "station", planetary: "planetary" };
  ED.hist = {};   // (each page's working state: for the tests)
  ED.hist.nav = HistPage({
    page: "nav", tab: "nav", sub: 7, key: 6, label: "Hist", back: "2 Nav \u00b7 Hist", list: "hist", selKey: "hiSel", place: true,
    toggles: ["systems", "stations", "planetary"],
    ids: { page: "pg-hist", list: "hi-list", tot: "hi-tot", railmsg: "hi-railmsg", foot: "hi-foot", pc: "hi-pc", clip: "hi-clip" },
    row: navRow, detail: navDetail,
    totals: function (t, f) {
      var out = ["systems", "stations", "planetary"].filter(function (k) { return f[k]; }).map(function (k) {
        var n = t[k] || 0;
        return ED.num(n) + " " + (k === "planetary" ? "planetary" : NAV_NAMES[k] + (n === 1 ? "" : "s"));
      });
      return out.length ? out.join(" \u00b7 ") : "Nothing chosen to show";
    },
    empty: function (f) { return f.systems || f.stations || f.planetary ? "No history yet" : "Nothing chosen"; },
    enter: function () { picAnimate(); },
  });
  window.addEventListener("resize", function () { if (ED.showing("nav", 7)) picDraw(); });

  // ---- 3 Contracts › History: every mission you've finished ----
  function chRow(r, sel) {
    var o = r.o === "completed" ? "" : '<span class="ho ' + r.o + '">' + OUTS[r.o] + "</span> ";
    return '<button type="button" class="item' + (sel ? " sel" : "") + '" data-key="' + ED.esc(r.k) + '" aria-pressed="' + sel + '">' +
      '<span class="meta"><span>' + ED.esc(r.c) + "</span><span>" + o + ED.esc(hhmm(r.ts)) + '</span></span><span class="nm">' +
      ED.esc(r.n) + "</span></button>";
  }
  function chDetail(it) {
    ED.setText($("ch-case"), it.label || "", false);
    ED.setText($("ch-name"), it.name || "", false);
    $("ch-sigil").innerHTML = ED.sigil(it.name || "");
    $("ch-chips").innerHTML = it.partial ? '<span class="chip dim">Accepted before your journals</span>' : "";
    var f = it.file, w = f && f.fields && f.fields.background ? f.fields : null;   // (a target: its subject file)
    $("ch-pc").classList.toggle("contract", !f);
    $("ch-l1").textContent = f ? "Status" : "Outcome";
    $("ch-l2").textContent = f ? "Contract" : "Issued by";
    $("ch-out").innerHTML = '<span class="ho big ' + ED.esc(it.outcome.toLowerCase()) + '">' + ED.esc(f ? f.status : it.outcome) + "</span>";
    $("ch-iss").textContent = f ? f.contract : it.issuer;
    if (f) {
      $("ch-aff").textContent = f.affiliation || "-";
      $("ch-ser").textContent = f.serial || "-";
      $("ch-inc").textContent = f.incept || "-";
      $("ch-mak").textContent = w && w.maker || "-";
      $("ch-fun").textContent = w && w.original_function || "-";
      $("ch-thr").textContent = f.threat || "-";
    }
    $("ch-paid").textContent = it.paid;
    $("ch-acc").textContent = it.accepted;
    $("ch-end").textContent = it.ended;
    $("ch-dest").textContent = it.dest;
    $("ch-clip").hidden = !it.copy;
    if ($("ch-clip").dataset.clip !== it.copy) { $("ch-clip").dataset.clip = it.copy || ""; ED.clipShow(); }
    $("ch-brief").innerHTML = (it.rows || []).map(function (r) {
      return '<span class="lab">' + ED.esc(r[0]) + '</span><span class="v">' + ED.esc(r[1]) + "</span>";
    }).join("") || '<span class="note">The journal says nothing more about it.</span>';
    $("ch-slab").hidden = $("ch-story").hidden = !it.story;   // (a dossier written before the subject files: as it was)
    $("ch-story").textContent = it.story || "";
    $("ch-dsecs").hidden = !w;
    if (w) {
      $("ch-bg").textContent = w.background || "";
      $("ch-mem").textContent = w.implanted_memory || "";
      $("ch-beh").textContent = w.behavioural_notes || "";
      $("ch-ass").textContent = w.assessment || "";
    }
  }
  ED.hist.contracts = HistPage({
    page: "contracts", tab: "contracts", sub: 2, key: 2, label: "History", back: "3 Contracts \u00b7 History", list: "chist", selKey: "chSel",
    toggles: ["completed", "failed", "abandoned"],
    ids: { page: "pg-chist", list: "ch-list", tot: "ch-tot", railmsg: "ch-railmsg", foot: "ch-foot", pc: "ch-pc", clip: "ch-clip" },
    row: chRow, detail: chDetail,
    totals: function (t, f) {
      var out = ["completed", "failed", "abandoned"].filter(function (k) { return f[k]; }).map(function (k) { return ED.num(t[k] || 0) + " " + k; });
      return out.length ? out.join(" \u00b7 ") : "Nothing chosen to show";
    },
    empty: function (f) { return f.completed || f.failed || f.abandoned ? "No missions" : "Nothing chosen"; },
  });
})();
