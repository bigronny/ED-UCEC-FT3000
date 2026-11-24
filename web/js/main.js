// ED Target Board page - starts the page and routes everything: which page shows, the board's
// state to every page, the UFC's input to the overlay or page in front, the strip along the top, Exit.
//
// Each tab is made of pages, grouped in sub-tabs (the second row of tabs; the UFC's keypad picks them). A page
// registers itself with ED.page({...}) (see core.js), with any of these:
//   tab, sub          where it lives: tab "nav", sub 2 = the Nav tab's second page (the Syst map)
//   key, label        its sub-tab: the keypad digit and name ("1", "Syst": the Syst list and map share one)
//   el                the id of its section of the screen (index.html, <section class="page">)
//   mode              classes #app carries while it shows (for the CSS)
//   back              what the hyperspace overlay says it returns to ("2 Nav · Syst map")
//   update(s)         every refresh, showing or not: keep lists, selections and reports current
//   draw(s)           every refresh while it shows, after every page's update
//   enter(viaTab)     it starts showing (viaTab: from another tab, rather than another page of this one)
//   leave()           it stops showing
//   resume()          an overlay that covered it has closed
//   cursor(u, scroll) show the UFC knob's highlight from the UFC record u (every page, showing or not)
//   list, pick(key)   the UFC list it picks from ("targets", "ocor", "syst", "hist", "chist") and a COMM1 pull on it
//   scroll(clicks, turns), knob(dyaw, dtilt), pull(), longPull()
//                     the UFC's COMM2 knob, the BRT / COMM2 VOLUME dials, COMM2 pulls - while it shows. turns: the turns
//                     of COMM2 in those clicks, each with its count ([[n, clicks]...]; null if some went by unseen)
//   knob1(clicks), pull1()
//                     the COMM1 knob and its pull, on a page that works it itself (the board's PAGE_KNOB1: Traj, Tgt...)
// What a page sends the board while answering a UFC press carries the press's token (ED.ufcU()): every open page answers
// each press, and the board acts on it once.
//   keypad(k)         a keypad key ("0".."9", "Clr", "Ent"; "Opt1".."Opt5" while one of its UFC sub-levels is open) while the
//                     page has said it's typing (POST /api/keypad: Wpt, Atk, HSI) - and ENT and CLR always, on those pages
//   dsg(n)            the page menu's DSG: designate what COMM1 has highlighted (n: the press, so the board acts on it once)
//   tick()            every second
// Overlays (hyperspace, changing vehicle) sit above the pages; while the hyperspace overlay is up
// the UFC's knobs and pulls go nowhere.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$;
  var LAST_SUB = {}, LAST_KEY = {};   // the page last shown on each tab, and in each of its sub-tabs ("nav|1": the Syst list or map)
  function keyOf(tab, sub) { var p = (ED.tabs[tab] || [])[sub - 1]; return p ? p.key || sub : sub; }
  function subPage(tab, key) {   // the page a sub-tab shows: the one last shown in it, else its first
    if (LAST_KEY[tab + "|" + key]) return LAST_KEY[tab + "|" + key];
    var pages = ED.tabs[tab] || [];
    for (var i = 0; i < pages.length; i++) if (pages[i] && (pages[i].key || i + 1) === key) return i + 1;
    return null;
  }

  // ---- which page shows ----
  // The view (tab + sub) is one record shared with the board (POST /api/select), so the UFC's ':'
  // marker and knob follow the page, and the UFC moving the view moves every open page.
  function setView(tab, sub) {
    var pages = ED.tabs[tab];
    if (!pages || !pages.length) return false;
    sub = Math.max(1, Math.min(pages.length, sub || LAST_SUB[tab] || 1));
    var v = ED.view;
    if (v.tab === tab && v.sub === sub) return false;
    var had = v.tab !== null, viaTab = had && v.tab !== tab, old = ED.here();
    if (old && old.leave) old.leave();
    v.tab = tab; v.sub = sub; LAST_SUB[tab] = sub; LAST_KEY[tab + "|" + keyOf(tab, sub)] = sub;
    var cur = ED.here();
    renderSubtabs();
    Array.prototype.forEach.call(document.querySelectorAll(".tab[data-tab]"), function (b) {
      var on = b.dataset.tab === tab;
      b.classList.toggle("on", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-subtabs]"), function (g) {   // a tab's own page buttons:
      Array.prototype.forEach.call(g.querySelectorAll("button[data-sub]"), function (b) {      // the page it shows, or will on return
        var on = +b.dataset.sub === (LAST_SUB[g.dataset.subtabs] || 1);
        b.classList.toggle("on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
    var app = $("app");
    ED.pages().forEach(function (p) {
      $(p.el).classList.toggle("on", p === cur);
      (p.mode || "").split(" ").forEach(function (c) { if (c) app.classList.remove(c); });
    });
    (cur.mode || "").split(" ").forEach(function (c) { if (c) app.classList.add(c); });
    // the screen settling on what it shows now: the full lens pull for another tab (a new source), a lighter one on
    // the page alone for another page of the same tab (a redraw) - Syst's list and map included
    if (viaTab) ED.replay(app, "pullbig");
    else if (had) ED.replay($(cur.el), "pull");
    ED.reportView({ tab: tab, sub: sub });
    if (cur.enter) cur.enter(viaTab);
    return true;
  }
  // the second row: the tab's sub-tabs (shown on a tab with more than one), the one showing lit
  function renderSubtabs() {
    var tab = ED.view.tab, seen = {}, groups = [], box = $("subtabs");
    (ED.tabs[tab] || []).forEach(function (p, i) {
      var k = p.key || i + 1;
      if (!seen[k]) { seen[k] = 1; groups.push({ key: k, label: p.label || "" }); }
    });
    var cur = keyOf(tab, ED.view.sub), sig = tab + "|" + cur;
    if (box._sig === sig) return;
    box._sig = sig;
    var row = groups.length > 1 || (ED.tabs[tab] || []).some(function (p) { return p.subrow; });   // (Setup: its row, though it has one so far)
    box.hidden = !row;
    box.innerHTML = !row ? "" : '<span class="ar" aria-hidden="true">&#9656;</span>' + groups.map(function (g) {
      return '<button type="button" class="stab' + (g.key === cur ? " on" : "") + '" data-key="' + g.key + '" aria-pressed="' + (g.key === cur) + '">' +
        g.key + " " + ED.esc(g.label) + "</button>";
    }).join("") + '<span class="tmrmini" id="tmr-mini" hidden></span><span class="hint">Keypad ' + (groups.length > 1 ? "1-" + groups.length : "1") + "</span>";
    if (ED.timer) ED.timer.mini();   // (the timer's copy, while it runs or has a countdown set)
  }
  function go(tab, sub) {   // move to a page and show it now
    if (setView(tab, sub)) { ED.dialsDisarm(); if (S.data) render(S.data); }
  }
  function resume() {   // an overlay closed: the page underneath picks up again
    var p = ED.here();
    if (p && p.resume) p.resume();
  }

  // ---- the board's state, to every page ----
  function render(s) {
    if (s.timing && !ED.timing.on()) ED.timing.start();   // the board's noting timings (--timing-log): so does the page
    var tm = ED.timing.on(), slow = {}, a = 0;
    function lap() { var b = performance.now(), d = b - a; a = b; return Math.round(d * 10) / 10; }
    if (tm) lap();
    S.data = s;
    if (ED.view.tab === null) setView(s.contracts.length ? "contracts" : "home", 1);   // start on Contracts if there are any
    ED.pages().forEach(function (p) {
      if (!p.update) return;
      p.update(s);
      if (tm) { var d = lap(); if (d >= 1) slow[p.el] = d; }   // (timing log: the pages that took a while)
    });
    ED.boot.update(s);   // changing vehicle: the disconnect / start-up effect
    if (ED.contracts.lock()) setView("contracts", 1);   // a fresh lock on a target's ship jumps to it
    renderStrip(s);
    var cur = ED.here(), rest = tm ? lap() : 0;
    if (cur && cur.draw) cur.draw(s);
    var draw = tm ? lap() : 0;
    ED.hyper.update(s);
    S.first = false;
    tick();
    if (tm) S.rt = { upd: slow, rest: rest, draw: draw, page: cur ? cur.el : "", tail: lap() };
  }
  function renderStrip(s) {
    $("cmdr").textContent = s.commander ? "CMDR " + s.commander : "";
    var rm = s.remote || {};   // (1 Syst on a remote system - and the Nav pages with it: said in amber)
    $("loc").textContent = s.system ? "Loc " + s.system : "";
    $("rmt").textContent = rm.on ? "Remote " + rm.system : "";
    $("rmt").hidden = !rm.on;
    $("count").textContent = s.contracts.length + " active";
    // (the backstories' AI and its login check: on 4 Setup > Settings, not up here)
    if ($("link").className === "bad") {
      $("link").className = "";
      $("link").innerHTML = 'Live<span class="blink">_</span>';
    }
    var last = s.last_event ? "Last event " + ED.clock(s.last_event) : "";
    Array.prototype.forEach.call(document.querySelectorAll(".lastev"), function (el) { el.textContent = last; });
  }
  function tick() {
    var a = performance.now();
    ED.pages().forEach(function (p) { if (p.tick) p.tick(); });
    ED.clipShow();
    var d = performance.now() - a;
    if (d >= 2 && ED.timing.on()) ED.timing.rec("p.tick", { w: ED.timing.wall(a), ms: Math.round(d * 10) / 10 });
  }
  // the board's state: fetched the moment the board says something's new (state_n, jump_n on the event stream),
  // and every 2 s anyway. One fetch at a time: asked again while one is on its way, it fetches again as soon as
  // that one lands (however many asks came in between)
  async function refresh(why) {
    if (S.halted) return;
    if (S.fetching) { S.again = true; S.againWhy = why; return; }
    S.fetching = true;
    try {
      do {
        S.again = false;
        var t0 = performance.now();
        var r = await fetch("/api/state", { cache: "no-store" });
        var t1 = performance.now(), txt = await r.text(), t2 = performance.now(), s = JSON.parse(txt), t3 = performance.now();
        render(s);
        if (ED.timing.on()) {   // the fetch (to the answer starting, then the rest of it), reading it, the pages' refresh
          var me = (s.syst || {}).me || {}, rt = S.rt || {}, q = function (x) { return Math.round(x * 10) / 10; };
          ED.timing.rec("p.ref", { w: ED.timing.wall(t0), why: why || "", f: q(t1 - t0), b: q(t2 - t1), j: q(t3 - t2), r: q(performance.now() - t3),
                                   kb: q(txt.length / 1024), mt: me.t, age: me.age, upd: rt.upd, rest: rt.rest, draw: rt.draw, page: rt.page, tail: rt.tail });
        }
        why = "again:" + (S.againWhy || "");
      } while (S.again && !S.halted);
    } catch (e) {
      $("link").className = "bad";
      $("link").textContent = "Link lost";
    } finally {
      S.fetching = false;
    }
  }

  // ---- the UFC's input, from the board's event stream ----
  var seen = null;   // the UFC record's counters, as last acted on
  function applyCursor(scroll) {   // every page shows the knob's highlight in its own list
    var u = S.ufc || {};
    ED.pages().forEach(function (p) { if (p.cursor) p.cursor(u, scroll); });
  }
  // a UFC press, to the page showing (unless an overlay takes it). tok names the press ("c2.<n>": the n-th COMM2 pull...):
  // every open page answers each press, so what a page sends the board for it carries the token (ED.ufcU()) and the
  // board acts on it once - the page answering after another is given the same answer
  var TOK = { t: null, n: 0 };
  function route(what, a, b, tok) {
    if (ED.hyper.on()) return;   // in hyperspace: nothing to act on
    var p = ED.here();
    if (!p || !p[what]) return;
    TOK.t = tok || null; TOK.n = 0;
    try { p[what](a, b); } finally { TOK.t = null; }
  }
  // the token for the next thing sent the board while answering a UFC press (each its own: "c2.5.0", "c2.5.1"...), or
  // undefined (not answering one - a click, a timer)
  ED.ufcU = function () { return TOK.t ? TOK.t + "." + (TOK.n++) : undefined; };
  function onUfc(u) {
    // what happened before this page opened doesn't count - nor, when the script has been started again
    // (a new run, counting from zero), what the old run counted; the new run is told where this page is
    var restarted = !!S.ufc && u.run !== S.ufc.run, first = !S.ufc || restarted;
    if (first) {
      seen = { view: u.view_n, scroll: u.scroll_pos, pick: u.pick_n, c2: u.c2pull_n, c2long: u.c2long_n,
               jump: u.jump_n, state: u.state_n, k1: u.knob1_pos, c1: u.c1pull_n, key: u.key_n, dsg: u.dsg_n, mk: u.mk_n, sn: u.scroll_n };
      if (restarted) reportAll();
    } else {
      if (u.view_n > seen.view) {   // an option button picked a tab (or the next page of one)
        seen.view = u.view_n;
        if (u.view && u.view.tab) go(u.view.tab, u.view.sub);
      }
      if (u.scroll_pos !== seen.scroll) {   // COMM2 knob (+1 a click clockwise)
        var clicks = u.scroll_pos - seen.scroll;
        seen.scroll = u.scroll_pos;
        // (and the turns themselves, each with its count - those not seen yet; null if some went by unseen)
        var turns = (u.scroll_turns || []).filter(function (q) { return q[0] > (seen.sn || 0); });
        if (!turns.length || turns[0][0] !== (seen.sn || 0) + 1) turns = null;
        seen.sn = u.scroll_n;
        route("scroll", clicks, turns, "c2t." + u.scroll_n);
      }
      if (u.knob1_pos !== undefined && u.knob1_pos !== seen.k1) {   // COMM1, on a page that works it itself (Traj)
        var k1 = u.knob1_pos - (seen.k1 || 0);
        seen.k1 = u.knob1_pos;
        route("knob1", k1);   // (no token: nothing a page does for a COMM1 turn goes to the board at once)
      }
    }
    if ((u.clip || {}).n !== ((S.ufc || {}).clip || {}).n) S.clipAt = first ? 0 : Date.now();   // a press of the copy button
    S.ufc = u;
    ED.clipShow();
    if (!first) {
      if (u.pick_n > seen.pick) {   // a COMM1 pull picks the highlighted item, on whichever page owns that list
        seen.pick = u.pick_n;
        var owner = u.pick && ED.pages().filter(function (p) { return p.list === u.pick.list && p.pick; })[0];
        if (owner) owner.pick(u.pick.key);
      }
      if (u.c2long_n > seen.c2long) { seen.c2long = u.c2long_n; route("longPull", null, null, "c2l." + u.c2long_n); }   // 2-second COMM2 pull
      if (u.c2pull_n > seen.c2) { seen.c2 = u.c2pull_n; route("pull", null, null, "c2." + u.c2pull_n); }   // short COMM2 pull
      if (u.c1pull_n > (seen.c1 || 0)) { seen.c1 = u.c1pull_n; route("pull1", null, null, "c1." + u.c1pull_n); }   // a COMM1 pull, on a page that works it itself
      if (u.key_n > (seen.key || 0)) {   // keypad keys, to a page typing with them (each once, in order)
        var from = seen.key || 0;
        seen.key = u.key_n;
        (u.keys || []).forEach(function (q) { if (q[0] > from) route("keypad", q[1], null, "k." + q[0]); });
      }
      if (u.dsg_n > (seen.dsg || 0)) { seen.dsg = u.dsg_n; route("dsg", u.dsg_n); }   // DSG: the page showing designates
      if (u.mk_n > (seen.mk || 0)) { seen.mk = u.mk_n; if (ED.nav) ED.nav.markNow(u.mk_n); }   // MK: a mark where you are, whatever shows
      if (u.jump_n !== seen.jump) { seen.jump = u.jump_n; refresh("jump"); }      // a jump or start-up: fetch the state now
      if (u.state_n !== seen.state) { seen.state = u.state_n; refresh("sse"); }   // anything new (Status.json, the journal...): the same
    }
    applyCursor(true);
    dialKick();   // the dials, where they sit now
  }

  // ---- the UFC's three dials as speed controls (page menu only): the middle fifth of each holds; turned further
  // either way, it moves that way - gently just outside the middle, at full speed at the end stop. A dial waits
  // until it's been back in the middle once (after the page opens, or a new selection), so one left turned
  // doesn't set things moving on its own. The page showing gets the speeds each frame (its dial()), and says
  // what moved, for the UFC's scratchpad (Z+ / Z-, << >> UP DN) ----
  var DIAL_HOLD = 0.2, DIALS = { zoom: "comm1_volume", yaw: "comm2_volume", pitch: "brightness" };
  var DL = { armed: {}, raf: 0, t: 0, cue: "|" };
  function dialRate(name) {   // -1 .. 1 (0 in the middle, or while it's waiting)
    var u = S.ufc || {}, pos = (u.dials || {})[name];
    if (pos == null) return 0;
    var d = (pos - 0.5) * 2, a = Math.abs(d);
    if (a < DIAL_HOLD) { DL.armed[name] = true; return 0; }
    if (!DL.armed[name] || u.menu !== "PAGE" || S.halted || ED.hyper.on()) return 0;
    var x = Math.min(1, (a - DIAL_HOLD) / (1 - DIAL_HOLD));
    return (d < 0 ? -1 : 1) * (0.05 + 0.95 * x * x);
  }
  function dialFrame(t) {
    DL.raf = 0;
    var r = { zoom: dialRate(DIALS.zoom), yaw: dialRate(DIALS.yaw), pitch: dialRate(DIALS.pitch) };
    var dt = DL.t ? Math.min(0.1, (t - DL.t) / 1000) : 0, moving = !!(r.zoom || r.yaw || r.pitch);
    DL.t = moving ? t : 0;
    var p = ED.here(), cue = { z: "", t: "" };
    if (moving && p && p.dial) cue = p.dial(r, dt) || cue;
    dialCue(cue);
    if (moving && !document.hidden) DL.raf = requestAnimationFrame(dialFrame);
  }
  function dialKick() { if (!DL.raf) DL.raf = requestAnimationFrame(dialFrame); }
  function dialCue(cue) {
    var sig = (cue.z || "") + "|" + (cue.t || "");
    if (sig === DL.cue) return;
    DL.cue = sig;
    try {
      fetch("/api/dialcue", { method: "POST", headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ page: ED.pageId, z: cue.z || "", t: cue.t || "" }) }).catch(function () {});
    } catch (err) { /* nothing to tell */ }
  }
  ED.dialsDisarm = function () {   // a new selection: a dial that's turned waits for the middle again (one in it carries on)
    var dials = (S.ufc || {}).dials || {};
    DL.armed = {};
    Object.keys(DIALS).forEach(function (k) {
      var pos = dials[DIALS[k]];
      if (pos != null && Math.abs((pos - 0.5) * 2) < DIAL_HOLD) DL.armed[DIALS[k]] = true;
    });
  };
  function reportAll() {   // where this page is and what it has picked, for a script that has just started again
    var v = { tab: ED.view.tab, sub: ED.view.sub, pick: {} };
    [["targets", S.sel], ["ocor", S.obSel], ["syst", S.sySel], ["hist", S.hiSel], ["chist", S.chSel]].forEach(function (p) {
      if (typeof p[1] === "string") v.pick[p[0]] = p[1];
    });
    if (v.tab) ED.reportView(v);
  }
  function listenUfc() {
    if (!window.EventSource) return;
    S.es = new EventSource("/api/events?page=" + ED.pageId);
    S.es.onopen = function () { if (ED.boot) ED.boot.ufcAgain(); };   // (re)connected: tell the board what the UFC should show
    S.es.onmessage = function (e) {
      var a = performance.now(), u = null;
      try { u = JSON.parse(e.data); if (ED.timer) ED.timer.heard(u.t); onUfc(u); } catch (err) { if (window.console) console.warn(err); }
      if (ED.timing.on() && u) ED.timing.rec("p.ev", { w: ED.timing.wall(a), sn: u.state_n, ms: Math.round((performance.now() - a) * 10) / 10 });
    };
  }

  // ---- clicks on the tabs, their sub-tabs, and a page's own page buttons (Syst: list / map) ----
  $("subtabs").addEventListener("click", function (e) {
    var b = e.target.closest("button.stab");
    if (b && S.data && ED.view.tab) { var sub = subPage(ED.view.tab, +b.dataset.key); if (sub) go(ED.view.tab, sub); }
  });
  document.querySelector(".tabs").addEventListener("click", function (e) {
    var b = e.target.closest(".tab[data-tab]");
    if (!b || b.disabled || !S.data) return;
    go(b.dataset.tab);
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-subtabs]"), function (g) {
    g.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-sub]");
      if (b && S.data) go(g.dataset.subtabs, +b.dataset.sub);
    });
  });

  // Exit: first press arms it (turns red), a second press within 4 s stops the script
  var quitTimer = null;
  $("quit").addEventListener("click", async function () {
    var b = $("quit");
    if (!quitTimer) {
      b.classList.add("arm");
      b.textContent = "[ Confirm exit ]";
      quitTimer = setTimeout(function () {
        quitTimer = null;
        b.classList.remove("arm");
        b.textContent = "[ Exit ]";
      }, 4000);
      return;
    }
    clearTimeout(quitTimer);
    b.disabled = true;
    b.textContent = "[ Stopping ]";
    try { await fetch("/api/quit", { method: "POST" }); } catch (e) {}
    S.halted = true;
    clearInterval(S.pollTimer);
    clearInterval(S.tickTimer);
    if (S.es) S.es.close();
    $("paste").hidden = true;
    ED.boot.end();
    $("halt").hidden = false;
  });

  ED.setView = setView;
  ED.go = go;
  ED.resume = resume;
  ED.render = render;
  ED.refresh = refresh;
  ED.applyCursor = applyCursor;
  ED.tick = tick;

  refresh("start");
  listenUfc();
  S.pollTimer = setInterval(function () { refresh("poll"); }, 2000);
  S.tickTimer = setInterval(tick, 1000);
})();
