// ED Target Board page - the stopwatch and countdown timer, after the T-6A's clock and its two buttons: SEL (the stopwatch,
// ET, or the countdown, CD) and CTL (start it - and again, reset it). The board keeps it (the UFC record's "timer", pushed
// with the board's clock, t), so every open page shows the same and a reload keeps it running. 2 Nav > HSI shows it at the
// bottom left of its map and works it (hsi.js: COMM1 to ET / CD or the time, a pull presses it; the countdown's time
// typed on the UFC's keypad - or, clicked, the keyboard). On the other pages, while it runs or has a countdown set: a
// copy in the sub-tab row (main.js puts its place there, #tmr-mini).
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$;
  var MAX = 99 * 3600 + 59 * 60 + 59;   // (99:59:59: the board's TIMER_MAX)
  var T = { skews: [], skew: 0, mini: "" };

  // ---- the board's clock: how far ahead of this one it is (the most of the last few pushes - the least delayed) ----
  function heard(t) {
    if (typeof t !== "number" || !isFinite(t)) return;
    T.skews.push(t - Date.now() / 1000);
    if (T.skews.length > 20) T.skews.shift();
    T.skew = Math.max.apply(null, T.skews);
  }
  function now() { return Date.now() / 1000 + T.skew; }

  // ---- what it shows ----
  function rec() { return (S.ufc || {}).timer || { mode: "et", run: false, t0: null, cd: null, ack: false }; }
  // {mode: "et" | "cd", run, set: a countdown time set, secs: what the display shows (null: no countdown time), up: a
  // countdown past zero - counting up again, as the T-6A's does - alarm: ... and not yet seen (SEL, or CTL: reset)}
  function read() {
    var r = rec(), o = { mode: r.mode === "cd" ? "cd" : "et", run: !!r.run, set: r.cd != null, secs: 0, up: false, alarm: false };
    if (o.mode === "et") o.secs = o.run && r.t0 != null ? Math.max(0, now() - r.t0) : 0;
    else if (r.cd == null) o.secs = null;
    else if (!o.run || r.t0 == null) o.secs = r.cd;
    else {
      var left = r.cd - (now() - r.t0);
      if (left > 0) o.secs = Math.ceil(left);   // (00:00:01 until it's there: then zero, and up)
      else { o.up = true; o.secs = -left; o.alarm = !r.ack; }
    }
    return o;
  }
  function fmt(secs) {   // hh:mm:ss
    if (secs == null) return "--:--:--";
    var v = Math.min(MAX, Math.max(0, Math.floor(secs + 1e-6)));
    return [Math.floor(v / 3600), Math.floor(v / 60) % 60, v % 60].map(function (x) { return String(x).padStart(2, "0"); }).join(":");
  }
  function active() { var o = read(); return o.run || (o.mode === "cd" && o.set); }

  // ---- a countdown's time, as typed: the digits fill HH, MM, SS from the left ----
  function typed(d) {   // "013" -> "01:3_:__"
    var s = (String(d || "") + "______").slice(0, 6);
    return s.slice(0, 2) + ":" + s.slice(2, 4) + ":" + s.slice(4, 6);
  }
  function parse(text) {   // HHMMSS (or less: the rest zero), or H:M:S - > seconds (1 s - 99:59:59), or null
    var t = String(text || "").trim(), h, m, sec;
    if (/:/.test(t)) {
      var p = t.split(":").map(function (x) { return x.trim(); });
      if (p.length > 3 || p.some(function (x) { return !/^\d{0,2}$/.test(x); })) return null;
      h = +(p[0] || 0); m = +(p[1] || 0); sec = +(p[2] || 0);
    } else {
      var d = t.replace(/\D/g, "");
      if (!d || d.length > 6 || d.length !== t.length) return null;
      d = (d + "000000").slice(0, 6);
      h = +d.slice(0, 2); m = +d.slice(2, 4); sec = +d.slice(4, 6);
    }
    var v = h * 3600 + m * 60 + sec;
    return m < 60 && sec < 60 && v >= 1 && v <= MAX ? v : null;
  }

  // ---- working it: the board acts on each UFC press once (its token), whichever pages answer ----
  function post(body, done) {
    var u = ED.ufcU ? ED.ufcU() : undefined;
    if (u && body.u == null) body.u = u;
    fetch("/api/timer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (done) done(j || {}); }, function () { if (done) done({}); });
  }

  // ---- the copy in the sub-tab row (not on the HSI: it's there in full) ----
  function mini() {
    var el = $("tmr-mini");
    if (!el) return;
    var o = read(), show = active() && !ED.showing("nav", 5);
    var sig = show ? [o.mode, fmt(o.secs), o.run, o.up, o.alarm].join("|") : "";
    if (sig === T.mini && el.hidden === !show) return;
    T.mini = sig;
    el.hidden = !show;
    if (!show) return;
    el.textContent = (o.mode === "cd" ? "CD " : "ET ") + (o.up ? "+" : "") + fmt(o.secs);
    el.className = "tmrmini" + (o.run ? " run" : " set") + (o.up ? " up" : "") + (o.alarm ? " alarm" : "");
  }
  setInterval(mini, 250);

  ED.timer = { heard: heard, now: now, read: read, fmt: fmt, typed: typed, parse: parse, post: post, active: active, mini: mini };
})();
