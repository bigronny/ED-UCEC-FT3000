// ED Target Board page - 2 Nav › 1 Syst's CURRENT SYSTEM / REMOTE: a system picked to look at and plan in - its bodies
// and stations in 1 Syst (and its map); its waypoints, flight plans and attacks on the Nav pages, which follow 1 Syst -
// instead of the one you're in. REMOTE opens a list: MANUAL first (a name typed - on the keypad as a waypoint's NAME: 2
// and 8 step the letter under the cursor, 4 and 6 move the cursor - with the matches, from the systems you know of and
// Spansh's search, listed under it), then your plotted route's destination, your active missions' systems, OCOR's
// objectives, the systems you've been in lately and those picked lately. 1 Syst stays on the remote system through any
// number of jumps until CURRENT SYSTEM - or until you arrive there (then it simply is the current system).
// The UFC (page menu): COMM1's first stop on the System list is the switch - a pull opens the list (REMOTE on: back to the
// current system). While the list is open, COMM1 moves through it and a pull (or ENT) picks; MANUAL's pull starts the
// name; CLR clears the name (again: stops typing; again: closes the list).
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$;
  var CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -+.'", NAME_MAX = 40;   // what the keypad can put in a name
  var GROUPS = [["route", "Route destination"], ["missions", "Active missions"], ["ocor", "OCOR objectives"],
                ["hist", "Been lately"], ["recent", "Viewed lately"]];
  var SEARCH_WAIT = 600;   // ms after the last change to a name before asking for its matches
  var R = { open: false, items: [], sel: 0, typing: null, matches: [], msel: -1, asked: "", note: "", told: "", timer: 0, busy: false };

  function rv() { return (S.data || {}).remote || {}; }
  function showing() { return ED.showing("nav", 1); }
  function say(t) { R.note = t; draw(); }
  function ly(v) { return v == null ? "" : (v < 100 ? v.toFixed(1) : Math.round(v).toLocaleString("en-GB")) + " ly"; }

  // ---- the list: MANUAL, then each source's systems ----
  function rows() {
    var out = [{ kind: "manual" }];
    GROUPS.forEach(function (g) {
      R.items.forEach(function (i) { if (i.g === g[0]) out.push({ kind: "sys", g: g[0], name: i.name, why: i.why, ly: i.ly }); });
    });
    return out;
  }
  function open() {
    R.open = true; R.sel = 0; R.typing = null; R.matches = []; R.msel = -1; R.note = ""; R.asked = ""; R.items = [];
    clearTimeout(R.timer);
    if ($("sy-rq")) $("sy-rq").value = "";   // (a new name: not the last one's)
    draw();
    fetch("/api/remote").then(function (r) { return r.json(); }).then(function (j) {
      if (!R.open) return;
      R.items = (j && j.items) || [];
      draw();
    }, function () { say("Couldn't fetch the list"); });
  }
  function close() {
    R.open = false; R.typing = null; R.matches = []; R.msel = -1; R.asked = "";
    clearTimeout(R.timer);
    draw();
    if ($("sy-rpop")) $("sy-rpop").innerHTML = "";
  }
  function current() {   // CURRENT SYSTEM: 1 Syst back on where you are
    post({ off: true }, function () { close(); });
  }
  function post(body, done) {
    fetch("/api/remote", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (done) done(j || {}); ED.refresh(); }, function () { if (done) done({}); });
  }
  function pick(name) {
    name = String(name || "").trim();
    if (!name) { say("Type a system's name"); return; }
    R.busy = true; say("Looking for " + name.toUpperCase() + "...");
    post({ system: name }, function (j) {
      R.busy = false;
      if (j.ok) { close(); S.sySel = null; S.syMode = "auto"; }
      else say(j.why === "unknown" ? "No system called " + name.toUpperCase() + " (Spansh)" : "Couldn't pick it");
    });
  }

  // ---- MANUAL: the name, typed on the keypad (as a waypoint's NAME) or the keyboard; its matches under it ----
  function startTyping() {
    var v = String(($("sy-rq") || {}).value || "").toUpperCase().split("").slice(0, NAME_MAX);
    R.typing = { chars: v, pos: v.length };
    R.sel = 0; R.msel = -1;
    draw();
  }
  function typed() { return R.typing ? R.typing.chars.join("").replace(/\s+/g, " ").trim() : String(($("sy-rq") || {}).value || "").trim(); }
  function changed() {   // the name changed: its matches, once it's been left a moment
    clearTimeout(R.timer);
    var q = typed();
    if (q.length < 2) { R.matches = []; R.msel = -1; R.asked = ""; draw(); return; }
    R.timer = setTimeout(function () {
      if (q === R.asked) return;
      R.asked = q;
      fetch("/api/sysfind?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (j) {
        if (!R.open || typed() !== q) return;
        R.matches = (j && j.items) || []; R.msel = -1;
        draw();
      }, function () {});
    }, SEARCH_WAIT);
  }
  function nameKey(k) {
    var en = R.typing, ch = en.chars, i;
    if (k === "2" || k === "8") {   // the letter under the cursor, up or down (a new one past the end)
      if (en.pos >= ch.length) {
        if (ch.length >= NAME_MAX) return;
        ch.push(k === "2" ? CHARS[0] : CHARS[CHARS.length - 1]);
      } else {
        i = CHARS.indexOf(ch[en.pos]);
        ch[en.pos] = i < 0 ? CHARS[0] : CHARS[(i + (k === "2" ? 1 : CHARS.length - 1)) % CHARS.length];
      }
      changed();
    } else if (k === "6") {
      en.pos = Math.min(Math.min(ch.length, NAME_MAX - 1), en.pos + 1);
    } else if (k === "4") {
      en.pos = Math.max(0, en.pos - 1);
    }
  }
  function enter() {   // ENT, or a COMM1 pull: typing - the highlighted match, or the name as typed; else COMM1's row
    if (R.typing) {
      if (R.msel >= 0 && R.matches[R.msel]) pick(R.matches[R.msel].name);
      else pick(typed());
      return;
    }
    var r = rows()[R.sel];
    if (!r) return;
    if (r.kind === "manual") startTyping();   // (what's in the box, if anything, carried on with the keypad)
    else pick(r.name);
  }
  function enterBox() {   // the keyboard's Enter in MANUAL's box: the highlighted match, or the name as typed
    if (R.msel >= 0 && R.matches[R.msel]) pick(R.matches[R.msel].name);
    else pick(typed());
  }

  // ---- the UFC (while the list is open: COMM1, its pull, the keypad) ----
  function knob1(clicks) {
    if (!R.open) return;
    if (R.typing) {   // through the matches (above the first: the name itself)
      R.msel = Math.max(-1, Math.min(R.matches.length - 1, R.msel + clicks));
    } else {
      R.sel = Math.max(0, Math.min(rows().length - 1, R.sel + clicks));
      if (document.activeElement === $("sy-rq")) $("sy-rq").blur();   // (COMM1's row, not the box)
    }
    draw();
  }
  function pull1() { if (R.open && !R.busy) enter(); }
  function key(k) {
    if (!R.open) return;
    if (k === "Ent") { if (!R.busy) enter(); return; }
    if (k === "Clr") {
      if (R.typing && R.typing.chars.length) { R.typing.chars = []; R.typing.pos = 0; R.matches = []; R.msel = -1; R.asked = ""; }
      else if (R.typing) R.typing = null;
      else close();
      draw();
      return;
    }
    if (R.typing) { nameKey(k); draw(); }
  }

  // ---- drawing ----
  function nameHtml() {   // the name with its cursor (keypad typing)
    var en = R.typing;
    if (!en) return "";
    var ch = en.chars.slice();
    if (en.pos >= ch.length) ch.push("_");
    return ch.map(function (c, i) { return '<span class="' + (i === en.pos ? "rcur" : "") + '">' + ED.esc(c === " " ? " " : c) + "</span>"; }).join("");
  }
  function draw() {
    var box = $("sy-rpop");
    if (!box) return;
    box.hidden = !R.open;
    tell();
    if (!R.open) return;
    var rs = rows(), html = '<div class="rphead"><span class="lab rpt">Remote system</span>' +
      '<button type="button" class="sybtn" id="sy-rclose">Close</button></div>';
    rs.forEach(function (r, i) {
      if (r.kind === "manual") {
        html += '<div class="rpman' + (R.typing ? " typing" : "") + '"><button type="button" class="srow' + (i === R.sel && !R.typing ? " cur" : "") +
          '" data-i="0"><span class="nm">Manual</span><span class="rt">Type a name</span></button>' +
          '<div class="rpbox"><input class="tgin rpin" id="sy-rq" type="text" autocomplete="off" spellcheck="false" placeholder="System name">' +
          '<span class="rpkeys" id="sy-rkeys">' + nameHtml() + "</span></div>" +
          '<div class="lab rphint">Keypad: 2 / 8 the letter, 4 / 6 the cursor · ENT picks · CLR clears</div>' +
          (R.matches.length ? '<div class="rpmatch">' + R.matches.map(function (m, j) {
            return '<button type="button" class="srow' + (j === R.msel ? " cur" : "") + '" data-m="' + j + '"><span class="nm">' + ED.esc(m.name) +
              '</span><span class="rt">' + ED.esc(ly(m.ly)) + "</span></button>";
          }).join("") + "</div>" : (typed().length >= 2 && R.asked === typed() ? '<div class="tgnil">No matches</div>' : "")) + "</div>";
        return;
      }
      if (i === 1 || rs[i - 1].g !== r.g) html += '<div class="lab rpg">' + ED.esc((GROUPS.filter(function (g) { return g[0] === r.g; })[0] || ["", ""])[1]) + "</div>";
      html += '<button type="button" class="srow' + (i === R.sel && !R.typing ? " cur" : "") + '" data-i="' + i + '"><span class="nm">' + ED.esc(r.name) +
        (r.why ? ' <span class="rpwhy">· ' + ED.esc(r.why) + "</span>" : "") + '</span><span class="rt">' + ED.esc(ly(r.ly)) + "</span></button>";
    });
    if (rs.length === 1) html += '<div class="tgnil">Nothing else to list - no route plotted, no missions, no OCOR briefing, no history yet</div>';
    html += '<div class="aknote" id="sy-rnote">' + ED.esc(R.note) + "</div>";
    var keep = document.activeElement && document.activeElement.id === "sy-rq", val = keep ? $("sy-rq").value : (R.typing ? typed() : ($("sy-rq") || {}).value || "");
    box.innerHTML = html;
    var inp = $("sy-rq");
    inp.value = R.typing ? R.typing.chars.join("") : val;
    if (keep) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    var cur = box.querySelector(".srow.cur");
    if (cur) cur.scrollIntoView({ block: "nearest" });
  }
  function tell() {   // the board: the keypad (and COMM1) are the list's while it's open; what the scratchpad shows
    var o = R.open && showing(), show = { page: ED.pageId, on: o, knob1: o };
    if (o && R.typing) {
      var en = R.typing, from = Math.max(0, en.pos - 7), win = en.chars.slice(from, from + 8);
      if (en.pos === en.chars.length && win.length < 8) win.push("_");
      show.s1 = "SY"; show.num = win.join("");
    } else if (o) {
      var r = rows()[R.sel] || {};
      show.s1 = "RM"; show.num = (r.kind === "manual" ? "MANUAL" : String(r.name || "")).toUpperCase().slice(0, 8);
    }
    var sig = JSON.stringify(show);
    if (sig === R.told) return;
    R.told = sig;
    try { fetch("/api/keypad", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {}); } catch (e) { /* nothing to tell */ }
  }

  // ---- the mouse and keyboard ----
  document.addEventListener("click", function (e) {
    var box = $("sy-rpop");
    if (!box || !R.open || !box.contains(e.target)) return;
    if (e.target.closest("#sy-rclose")) { close(); return; }
    var m = e.target.closest(".srow[data-m]");
    if (m) { pick((R.matches[+m.dataset.m] || {}).name); return; }
    var b = e.target.closest(".srow[data-i]");
    if (b) {
      R.sel = +b.dataset.i;
      if (R.sel === 0) { R.typing = null; draw(); $("sy-rq").focus(); }
      else pick((rows()[R.sel] || {}).name);
    }
  });
  document.addEventListener("input", function (e) {
    if (e.target && e.target.id === "sy-rq") { R.typing = null; R.sel = 0; changed(); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.target && e.target.id === "sy-rq" && e.key === "Enter") { e.preventDefault(); enterBox(); }
    else if (R.open && e.key === "Escape") close();
  });

  ED.remote = {
    open: open, close: close, current: current, pick: pick, knob1: knob1, pull1: pull1, key: key, draw: draw, sync: tell,
    isOpen: function () { return R.open; }, state: R, on: function () { return !!rv().on; }
  };
})();
