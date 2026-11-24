// ED Target Board page - 4 Setup > 1 Controls: which button or dial, on which game controller, does each of the UFC's
// jobs. The left: the controllers the board can see (lit while they send; in use, or not; any with a job that's not
// plugged in), how assigning works, RESTORE DEFAULTS (twice: every job back to the UFC's own layout). The panel: the
// jobs, in groups - each with its button (or dial), "default" while it's the UFC's own, what Elite also does with it,
// ASSIGN (then press the button on any controller - or turn the dial end to end and back - in the time it shows)
// and CLEAR; a row lights while its button's pressed, so a setup can be tried out here. The board keeps them
// (controls.json - see the board's Controls); this page asks GET /api/controls four times a second while it shows
// (which keeps every controller open) and sends POST /api/controls {op: learn | cancel | clear | restore}.
(function () {
  "use strict";
  var ED = window.ED, $ = ED.$, esc = ED.esc;
  var C = { v: null, sig: "", busy: false, confirm: false, note: "", noteAt: 0, seen: 0 };

  function post(body, done) {
    fetch("/api/controls", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (done) done(j || {}); poll(); }, function () { if (done) done({}); });
  }
  function say(t) { C.note = t; C.noteAt = Date.now(); draw(); }
  function nameOf(job) { var j = ((C.v || {}).jobs || []).filter(function (x) { return x.job === job; })[0]; return j ? j.name : job; }

  function poll() {
    if (C.busy || !ED.showing("setup", 1) || document.hidden) return;
    C.busy = true;
    fetch("/api/controls").then(function (r) { return r.json(); }).then(function (v) {
      C.busy = false;
      var res = v.result, prev = (C.v || {}).result;
      C.v = v;
      if (res && (!prev || res.n !== prev.n) && C.seen) {   // ASSIGN finished (or ran out): say how it went
        if (res.ok) say(nameOf(res.job) + ": " + res.name + " · " + res.label + (res.moved.length ? " - taken from " + res.moved.map(nameOf).join(", ") + ", which now has none" : ""));
        else say(nameOf(res.job) + ": " + res.why);
      }
      C.seen = 1;
      draw();
    }, function () { C.busy = false; });
  }

  function draw() {
    var v = C.v;
    if (!v) return;
    if (C.note && Date.now() - C.noteAt > 10000) C.note = "";
    var sig = JSON.stringify([v.jobs, v.devices, v.learning && [v.learning.job, v.learning.kind, v.learning.ready], v.on, v.why, v.custom, C.confirm, C.note]);
    if (sig !== C.sig) {
      C.sig = sig;
      // the controllers: those it can see, and any with a job that isn't plugged in
      var have = {}, rows = (v.devices || []).map(function (d) {
        have[d.key] = have[d.name] = 1;
        return '<div class="srow ctdev" data-dev="' + esc(d.key) + '"><span class="nm"><i class="ctdot" aria-hidden="true"></i>' + esc(d.name) +
          '</span><span class="rt">' + (d.bound ? "In use" : d.open ? "Seen" : "") + "</span></div>";
      });
      var gone = {};
      (v.jobs || []).forEach(function (j) { if (j.bind && !have[j.bind.dev] && !have[j.bind.name]) gone[j.bind.name] = 1; });
      Object.keys(gone).forEach(function (n) { rows.push('<div class="srow ctdev gone"><span class="nm"><i class="ctdot" aria-hidden="true"></i>' + esc(n) + '</span><span class="rt">Not connected</span></div>'); });
      $("ct-devs").innerHTML = rows.join("") || '<div class="tgnil">None found</div>';
      $("ct-off").textContent = v.on ? "" : v.why || "Off";
      $("ct-off").hidden = !!v.on;
      $("ct-restore").textContent = C.confirm ? "Confirm restore" : "Restore defaults";
      $("ct-restore").classList.toggle("tgdanger", C.confirm);
      $("ct-restore").disabled = !v.custom && !C.confirm;
      $("ct-note").textContent = C.note;
      // the jobs, by group
      var L = v.learning;
      $("ct-jobs").innerHTML = (v.groups || []).map(function (g) {
        var jobs = (v.jobs || []).filter(function (j) { return j.group === g.id; });
        return '<div class="lab ctgrp">' + esc(g.name) + (g.what ? ' <span class="ctgw">· ' + esc(g.what) + "</span>" : "") + "</div>" + jobs.map(function (j) {
          var now = L && L.job === j.job, b = j.bind;
          var bind = now ? '<span class="ctwait">' + (j.kind === "dial" ? "Turn it end to end, and back" : "Press it") + "</span>" :
            b ? esc(b.label) + (b.name && b.label.indexOf("UFC ") !== 0 ? ' <span class="ctdv">· ' + esc(b.name) + "</span>" : "") + (j.default ? ' <span class="ctdf">default</span>' : "") :
            '<span class="ctnone">None</span>';
          return '<div class="ctrow' + (now ? " learning" : "") + '" data-job="' + esc(j.job) + '">' +
            '<div class="ctname"><span class="ctn">' + esc(j.name) + "</span>" + (j.what ? '<span class="ctwhat">' + esc(j.what) + "</span>" : "") + "</div>" +
            '<div class="ctbind">' + bind + (j.elite && j.elite.length ? '<span class="ctelite">Elite also: ' + esc(j.elite.join(", ")) + "</span>" : "") + "</div>" +
            '<div class="ctbtns"><button type="button" class="sybtn sm" data-a="assign"' + (v.on ? "" : " disabled") + ">" + (now ? "Waiting" : "Assign") + "</button>" +
            '<button type="button" class="sybtn sm" data-a="clear"' + (b ? "" : " disabled") + ">Clear</button></div></div>";
        }).join("");
      }).join("");
    }
    // ASSIGN waiting: what for, and how long it's got
    var L2 = v.learning;
    $("ct-learn").hidden = !L2;
    if (L2) $("ct-learn-t").textContent = "Assign · " + nameOf(L2.job) + " · " + (L2.ready ? (L2.kind === "dial" ? "turn the dial end to end, and back" : "press the button") + " on any controller" : "get ready") + " · " + Math.ceil(L2.left) + " s";
    // lit: a controller sending, a job's button pressed (or its dial turning)
    var lit = v.lit || {};
    Array.prototype.forEach.call(document.querySelectorAll("#ct-jobs .ctrow"), function (r) {
      var j = r.dataset.job, t = lit[j] != null ? lit[j] : lit[j + "_LONG"];
      r.classList.toggle("lit", t != null && t < 0.5);
    });
    var act = {};
    (v.devices || []).forEach(function (d) { act[d.key] = d.active; });
    Array.prototype.forEach.call(document.querySelectorAll("#ct-devs .ctdev[data-dev]"), function (r) { r.classList.toggle("act", !!act[r.dataset.dev]); });
  }

  $("ct-jobs").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-a]"), row = e.target.closest(".ctrow");
    if (!btn || !row || btn.disabled) return;
    var job = row.dataset.job;
    C.confirm = false;
    if (btn.dataset.a === "assign") {
      if (C.v && C.v.learning && C.v.learning.job === job) { post({ op: "cancel" }); return; }
      post({ op: "learn", job: job }, function (j) { if (!j.ok) say(j.why || "Couldn't"); });
    } else post({ op: "clear", job: job }, function (j) { say(j.ok ? nameOf(job) + ": none" : "Couldn't"); });
  });
  $("ct-cancel").addEventListener("click", function () { post({ op: "cancel" }); });
  $("ct-restore").addEventListener("click", function () {
    if (!C.confirm) { C.confirm = true; draw(); return; }
    C.confirm = false;
    post({ op: "restore" }, function (j) { say(j.ok ? "Every job back to the UFC's own button or dial" : "Couldn't"); });
  });
  setInterval(poll, 250);

  ED.page({
    tab: "setup", sub: 1, key: 1, label: "Controls", el: "pg-controls", back: "4 Setup · Controls", subrow: true,
    enter: function () { C.confirm = false; C.seen = 0; C.sig = ""; poll(); },
    leave: function () { C.confirm = false; if (C.v && C.v.learning) post({ op: "cancel" }); }
  });
  ED.controls = C;
})();
