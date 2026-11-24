// ED Target Board page - the page's side of the timing log (the board started with --timing-log; /api/state then
// says "timing"). Records go to the board every 2 seconds (POST /api/timing), which writes them in timing_log.jsonl
// beside its own: each fetch of the state and what the pages did with it (main.js), each position reading the filter
// took in and how far that moved where it had you (traj.js), each animation frame while Atk shows (atk.js), and the
// browser's own long tasks and long frames (with the scripts in them, where the browser says). Off, it does nothing.
// "w" is the wall clock in milliseconds (the board's records are in seconds: one PC, one clock).
(function () {
  "use strict";
  var ED = window.ED;
  var FLUSH_MS = 2000;     // how often the records go to the board
  var MAX_BUF = 20000;     // records held before they go early (a long gap between flushes)
  var T = { on: false, buf: [], timer: 0,
            t0: (performance.timeOrigin || (Date.now() - performance.now())) };
  function r1(x) { return Math.round(x * 10) / 10; }
  function wall(pn) { return r1(T.t0 + (pn == null ? performance.now() : pn)); }   // ms since 1970, to a tenth
  function rec(k, o) {
    if (!T.on) return;
    o = o || {};
    o.k = k;
    if (o.w == null) o.w = wall();
    T.buf.push(o);
    if (T.buf.length >= MAX_BUF) flush();
  }
  function flush() {
    if (!T.buf.length) return;
    var recs = T.buf;
    T.buf = [];
    try {
      fetch("/api/timing", { method: "POST", headers: { "Content-Type": "application/json" },
                             body: JSON.stringify({ pn: r1(performance.now()), dn: Date.now(), recs: recs }) }).catch(function () {});
    } catch (e) { /* nothing to do */ }
  }
  function watch(type, each) {   // the browser's own timings, where it has them
    try {
      new PerformanceObserver(function (list) { list.getEntries().forEach(each); }).observe({ type: type, buffered: false });
      return true;
    } catch (e) { return false; }
  }
  function start() {
    if (T.on) return;
    T.on = true;
    var lt = watch("longtask", function (e) {   // the page's thread busy for 50 ms or more: nothing else runs, frames included
      rec("p.long", { w: wall(e.startTime), ms: r1(e.duration), n: e.name });
    });
    var lf = watch("long-animation-frame", function (e) {   // a frame that took 50 ms or more, and the scripts that ran in it
      var sc = (e.scripts || []).slice().sort(function (a, b) { return b.duration - a.duration; }).slice(0, 4).map(function (s) {
        var src = String(s.sourceURL || "").replace(/^.*\/js\//, "");
        return { ms: r1(s.duration), fn: s.sourceFunctionName || "", src: src, at: s.sourceCharPosition, inv: String(s.invoker || "").slice(0, 60),
                 lay: r1(s.forcedStyleAndLayoutDuration || 0) };
      });
      rec("p.lframe", { w: wall(e.startTime), ms: r1(e.duration), block: r1(e.blockingDuration || 0),
                        render: e.renderStart ? r1(e.renderStart - e.startTime) : null,
                        style: e.styleAndLayoutStart ? r1(e.styleAndLayoutStart - e.startTime) : null, sc: sc });
    });
    rec("p.info", { page: ED.pageId, ua: navigator.userAgent, dpr: window.devicePixelRatio || 1, sw: screen.width, sh: screen.height,
                    iw: window.innerWidth, ih: window.innerHeight, dn: Date.now(), to: r1(T.t0), reduce: !!(ED.reduce && ED.reduce.matches),
                    longtask: lt, lframe: lf });
    document.addEventListener("visibilitychange", function () { rec("p.vis", { hidden: document.hidden }); });
    window.addEventListener("resize", function () { rec("p.size", { iw: window.innerWidth, ih: window.innerHeight }); });
    T.timer = setInterval(flush, FLUSH_MS);
    window.addEventListener("pagehide", flush);
  }
  ED.timing = { rec: rec, start: start, flush: flush, wall: wall, on: function () { return T.on; } };
})();
