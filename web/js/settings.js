// ED Target Board page - 4 Setup > 2 Settings: what the FT3000 starts with - the journal folder, the AI that writes
// subject files (and its model), viewing the page from other devices on your network, the game controllers, opening the
// page at start. The board keeps them (settings.json - see the board's Settings) as they're changed here (POST
// /api/settings {key, value}); each takes effect at the next start, and RESTART NOW (POST /api/restart) closes the board
// and starts it again - this page stays open and finds the new start (its run, in GET /api/settings, changes). A setting
// waiting for a restart says so; one the command line set at start says which option did (it wins over the setting).
(function () {
  "use strict";
  var ED = window.ED, $ = ED.$, esc = ED.esc;
  var T = { v: null, busy: false, note: "", noteAt: 0, restart: null, typed: {} };
  var ENGINE = { auto: "Auto", claude: "Claude", codex: "ChatGPT", none: "None" };
  var TOOL = { claude: "Claude Code", codex: "Codex (ChatGPT)", none: "none" };

  function say(t) { T.note = t; T.noteAt = Date.now(); draw(); }
  function rows() { return ((T.v || {}).settings) || {}; }

  function poll() {
    if (T.busy || document.hidden || (!ED.showing("setup", 2) && !T.restart)) return;
    T.busy = true;
    fetch("/api/settings").then(function (r) { return r.json(); }).then(function (v) {
      T.busy = false;
      if (T.restart && v.run !== T.restart.run) {   // started again
        T.restart = null;
        say("Started again: these settings are in use");
      }
      T.v = v;
      draw();
    }, function () { T.busy = false; draw(); });
  }

  function post(key, value, done) {
    fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: key, value: value }) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.view) T.v = j.view;
        if (done) done(j || {});
        draw();
      }, function () { if (done) done({}); });
  }

  function seg(id, value) {
    Array.prototype.forEach.call($(id).querySelectorAll("button[data-v]"), function (b) {
      b.classList.toggle("on", b.dataset.v === String(value));
    });
  }
  function flag(key, r, extra) {
    var el = $("st-f-" + key);
    if (!el) return;
    var t = r.flag ? "Set by " + r.flag + " at start" : r.pending ? "Restart to apply" : "";
    el.textContent = t || extra || "";
    el.className = "stflag" + (r.flag ? " cmd" : r.pending ? " pend" : "");
  }
  function input(id, value) {   // (not while it's being typed in)
    var el = $(id);
    if (document.activeElement !== el && !T.typed[id]) el.value = value;
  }
  function day(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toDateString() === new Date().toDateString() ? "today" : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  function draw() {
    var v = T.v;
    if (T.note && Date.now() - T.noteAt > 10000 && !T.restart) T.note = "";
    $("st-note").textContent = T.restart ? (Date.now() - T.restart.t > 40000 ? "It hasn't come back: start it again from its shortcut" : "Restarting...") : T.note;
    $("st-restart").disabled = !!T.restart;
    $("st-restart").textContent = T.restart ? "Restarting" : "Restart now";
    if (!v) return;
    var R = rows();
    $("st-restart").classList.toggle("arm", !!v.pending && !T.restart);
    // the journal folder
    var J = R.journal_dir || {};
    input("st-jdir", J.value || "");
    $("st-jdir").placeholder = J.default || "";
    $("st-jdef").disabled = !J.value;
    $("st-jinfo").textContent = (J.value ? "" : "The default folder · ") +
      (J.found ? J.found + " journal" + (J.found === 1 ? "" : "s") + " there, the newest written " + day(J.newest) : "No journals there yet") +
      (J.running && J.running !== J.folder ? " · now reading " + J.running : "");
    flag("journal_dir", J);
    // the AI
    var E = R.engine || {}, tools = E.tools || {};
    seg("st-engine", E.value);
    input("st-model", (R.model || {}).value || "");
    $("st-einfo").innerHTML = esc("On this PC: Claude Code " + (tools.claude ? "found" : "not found") + " · Codex " + (tools.codex ? "found" : "not found") +
      " · Auto picks " + TOOL[E.auto || "none"]) + "<br>" + esc("Now: " + (E.running && E.running !== "none" ? TOOL[E.running] + (E.model ? " (" + E.model + ")" : "") +
      (E.msg ? " · " + E.msg : "") : "none (no subject files)"));
    flag("engine", E);
    flag("model", R.model || {});
    // other devices
    var L = R.lan || {}, addr = (L.addresses || []).map(function (a) { return "http://" + a + ":" + L.port + "/"; });
    seg("st-lan", L.value);
    $("st-linfo").textContent = L.running ? "Now: on - open " + (addr.length ? addr.join(" or ") : "http://<this PC's address>:" + L.port + "/") + " on the other device"
      : "Now: off, this PC only" + (L.value && addr.length ? " · after a restart, " + addr.join(" or ") : "");
    $("st-lwarn").hidden = !(L.value || L.running);
    flag("lan", L);
    // controllers, opening the page
    var C = R.controllers || {};
    seg("st-controllers", C.value);
    $("st-cinfo").textContent = C.running ? "Now: on" : "Now: off, the page alone";
    flag("controllers", C);
    var O = R.open_page || {};
    seg("st-open_page", O.value);
    flag("open_page", O);
    // about
    var A = v.about || {};
    $("st-about").innerHTML = [["Version", A.version], ["Program", A.program], ["Your data", A.data],
      ["Key bindings", (A.bindings || []).length ? A.bindings.join(", ") : "None found in " + (A.bindings_dir || "?")],
      ["Project", A.project || "-"]].map(function (r) {
        var val = r[0] === "Project" && A.project ? '<a href="' + esc(A.project) + '" target="_blank" rel="noopener">' + esc(A.project) + "</a>" : esc(r[1] || "");
        return '<div class="stabr"><span class="lab">' + esc(r[0]) + '</span><span class="stav">' + val + "</span></div>";
      }).join("");
  }

  // the switches: each kept as it's pressed
  ["engine", "lan", "controllers", "open_page"].forEach(function (key) {
    $("st-" + key).addEventListener("click", function (e) {
      var b = e.target.closest("button[data-v]");
      if (!b) return;
      var val = b.dataset.v === "true" ? true : b.dataset.v === "false" ? false : b.dataset.v;
      post(key, val, function (j) { if (!j.ok) say(j.why || "Couldn't save it"); });
    });
  });
  // the typed ones: SAVE (or Enter)
  function saveTyped(id, key) {
    var el = $(id), val = el.value;
    post(key, val, function (j) {
      if (j.ok) { T.typed[id] = false; el.blur(); say(key === "model" ? "Model kept" : "Journal folder kept"); }
      else say(j.why || "Couldn't save it");
    });
  }
  [["st-jdir", "journal_dir", "st-jsave"], ["st-model", "model", "st-msave"]].forEach(function (q) {
    $(q[0]).addEventListener("input", function () { T.typed[q[0]] = true; });
    $(q[0]).addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); saveTyped(q[0], q[1]); }
      else if (e.key === "Escape") { T.typed[q[0]] = false; $(q[0]).blur(); draw(); }
      e.stopPropagation();
    });
    $(q[2]).addEventListener("click", function () { saveTyped(q[0], q[1]); });
  });
  $("st-jdef").addEventListener("click", function () {
    T.typed["st-jdir"] = false;
    post("journal_dir", "", function (j) { say(j.ok ? "Journal folder: the default" : j.why || "Couldn't save it"); });
  });
  // RESTART NOW
  $("st-restart").addEventListener("click", function () {
    if (T.restart || !T.v) return;
    T.restart = { run: T.v.run, t: Date.now() };
    draw();
    fetch("/api/restart", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(function () {});
  });
  setInterval(function () { if (T.restart || ED.showing("setup", 2)) { poll(); draw(); } }, 1000);

  ED.page({
    tab: "setup", sub: 2, key: 2, label: "Settings", el: "pg-settings", back: "4 Setup · Settings", subrow: true,
    enter: function () { T.typed = {}; poll(); },
    leave: function () { T.typed = {}; }
  });
  ED.settings = T;
})();
