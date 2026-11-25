// ED Target Board page - 2 Nav › Traj: guidance down to a planetary facility. Three panels, 40 / 20 / 40: the
// top-down view of the course in (left), the ILS and the highway in the sky (middle), the side profile and the
// vertical velocity (right). Profile buttons across the top - ENTRY 1, or CIRCLE (a Heading Alignment Cone, after the
// Shuttle's: see HAC below; the pop-up is Atk's attack plan) - and the destination: 1 SYST SEL (what Nav › Syst has
// selected) or DEST (what you've targeted in the game).
//
// CIRCLE: from where you are when it's armed (picked, a new destination or course, OVHD / STRT-IN flipped, and all the
// while in orbital cruise) it puts the HAC on the side giving the bigger turn (OVHD) or the smaller (STRT-IN), and keeps
// it there. ACQ: fly the line to WP1, where it meets the HAC tangent; HAC: round the tightening turn, R_IN down to R_OUT,
// to WP2 on the course; OGS: down the outer glide slope to the destination (inside FINAL_IN, the final approach - to your
// pad, as ENTRY 1's). The top-down view draws the HAC, WP1, WP2 and the OGS; the side profile is the path unrolled - the
// reference altitude (the OGS up to WP2, then DESC on round the HAC and out) with its band, and you. The readouts: WP1's
// bearing and range and the turn (ACQ); the turn to go, the HAC's radius there and how far in or out you are (HAC); the
// course (OGS); the reference altitude, HIGH / LOW, the descent rate it needs at your ground speed, the path to go.
//
// The page follows the flight's phases, from the game's own flags: orbital cruise (setting up: the ILS, highway
// and vertical-velocity check wait for the glide), the glide and the flying after it (ENTRY 1), and the final
// approach inside FINAL_IN of the settlement (to your pad, once docking's granted, where the board knows where it
// is). Each phase has a fixed scale, so the pictures change scale only when the phase does.
//
// Where you are comes from Status.json, which the game writes near a planet while you move - every second while
// your height's changing quickly, otherwise when your latitude or longitude has moved about WRITE_DEG (0.02
// degrees: 4 s at 393 m/s on a 4,360 km world, 8 s at 205 m/s), and not at all while you're still. Each reading,
// timed by when the game wrote the file, goes through a Kalman filter (position and velocity, east / north / up),
// which gives the speeds and carries you on between readings - as long as the game should take to write again at
// your speed, from that rule (a moment only below SLOW: a hover or a drift, which the game may not write again for
// a long while) - so the pictures move smoothly. Across the ground it expects steady flight (Q_LO) unless a reading
// disagrees with where it had you - a turn or a change of speed - or you're gliding (Q_HI). What the pages show
// eases onto each new reading's estimate over BLEND, rather than jumping. Silent for longer than the game should
// be, you've stopped (STILL, below SLOW); the next reading starts it afresh. The angles allow for the planet's curvature. The pictures are drawn as SVG and shown at the page's
// coarse pixels (pixel.js), like the rest of the site's.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$;

  // ---- ENTRY 1 ----
  var OPT = 50, STEEP = 60, SHALLOW = 10;   // degrees up from the destination: the path, and its bounds
  var LAT = 5;                               // degrees either side of the course
  // (the page's words, the pictures, the ILS's scale and the highway's gates all follow these)
  // The ILS glide-slope needle's scale. "split": each half of the needle runs to its own bound - full deflection
  // down at the 60 deg bound, full up at the 10 deg bound (so a dot down is worth less than a dot up). "even":
  // the same scale both ways, full deflection at +-(STEEP - OPT), like a real ILS.
  var GS_SCALE = "split";
  var SHOW_MID = false;   // the ILS and the highway in the sky (the middle column): off for now, the two panels half each
  var FINAL_IN = 3000, FINAL_OUT = 3300;   // metres from the settlement: the final approach starts (and ends, going away)
  // The pictures' scale in each phase (metres: the top-down view's radius, the side profile's width)
  var SCALE = { far: 1e6, near: 1e5, glide: 3e4, final: 3e3 };
  // ... unless you zoom them yourself (the COMM1 VOLUME dial, or the mouse wheel on either picture), between these
  // (metres): then the scale stays where you put it until Reset scale, a new destination, or going back into
  // orbital cruise
  var ZOOM_MIN = 300, ZOOM_MAX = 1e7;

  var RAD = Math.PI / 180, TAN_OPT = Math.tan(OPT * RAD);
  var C = { text: "#45f08a", hi: "#8affc1", muted: "#25b85c", rule: "#183a22", rule2: "#26603a", acc: "#e3a24a", bad: "#ff7b6b",
            bg: "#060606" };
  var WRITE_DEG = 0.02;   // degrees of latitude or longitude the game waits for before it writes again (in level flight)
  var SLOW = 30;          // m/s across the ground: slower, a hover or a drift - carried on only AHEAD_SLOW past a reading
  var AHEAD_SLOW = 1, AHEAD_MAX = 30;   // seconds past a reading the filter carries you on: slow, and at most
  var STILL = 2.5;        // seconds with no reading, below SLOW: you've stopped (faster: when the game's later than it should be) ...
  var DECEL = 150;        // ... plus the time it takes to stop from your speed at this many m/s² (the game goes quiet for
                          // a few seconds as you drop out of orbital cruise into the glide, at well over 1 km/s)

  var STALE = 30;         // seconds with no reading before it's worth saying so
  var MISS = 1.5;         // seconds a reading without a position is taken as a miss (the last position carries on)
  var REANCHOR = 300e3;   // metres: the filter's flat map is re-centred on you past this
  var Q_V = 900, R_H = 4, R_V = 100;   // the filter: up and down, acceleration (m/s^2)^2; readings' noise (m^2)
  // Across the ground: Q_HI (as agile as up and down) while it settles, while you glide, and when a reading lands
  // further from where it had you than NIS_HI allows (squared, in its own spread: about 1 in 1,000 by chance in
  // steady flight - a turn or a change of speed); otherwise down by Q_EASE a reading to Q_LO, steady flight, which
  // holds your speed steadier through the game's 2 to 4 s gaps (its predictions 4 s on: within about 20 m)
  var Q_LO = 4, Q_HI = 900, NIS_HI = 13.8, Q_EASE = 0.5;
  // What the pages show eases from where it had you onto each new estimate over BLEND seconds, rather than jumping
  // (a correction bigger than BLEND_MAX metres - after a silence, in orbital cruise - shows at once)
  var BLEND = 1.0, BLEND_MAX = 300;
  // In orbital cruise your speed changes by thousands of m/s a second and the readings are exact, so there the
  // speed is simply the change since the last reading (smoothed a little: CRUISE_EASE of the new one)
  var CRUISE_EASE = 0.6;
  // ---- CIRCLE: a Heading Alignment Cone, after the Shuttle's - round a tightening turn onto the course, then down the outer
  // glide slope (OGS) to the destination. WP2, the HAC's exit, is WP2_OUT out along the course; the turn round it tightens
  // from R_IN where you join it (WP1, where your line in meets it, tangent) to R_OUT at WP2, its radius growing in step with
  // the turn still to go; DESC down it (and on the line in), OGS down the course. OVHD / STRT-IN picks the side - the bigger
  // turn (overhead) or the smaller (straight in) - from where you are when it's armed: then it stays.
  var HAC = {
    OGS: 20,             // degrees: the outer glide slope, down the course from WP2 to the destination
    WP2_OUT: 4000,       // metres out along the course: WP2 (4 km x tan 20 deg = 1.46 km up)
    R_IN: 2500,          // metres: the HAC's radius where you join it ...
    R_OUT: 1500,         // ... and at WP2
    DESC: 14,            // degrees: the descent round the HAC and on the line in to it (about 1 in 4)
    WIN: 6,              // degrees either side of the slope: the vertical-velocity window
    TOL: 0.08, TOL_M: 60,   // HIGH / LOW: more than this part of the reference altitude off it (or this many metres, if more)
    CAPTURE: 400, CAPTURE_S: 4,   // on the HAC once this close to WP1 (metres - or seconds at your ground speed, if more)
    OGS_X: 1000,         // metres either side of the course: inside WP2 and this close, armed there, you're on the OGS already
    SCALE: 1e4,          // metres: the pictures' scale while you fly it (until the final approach's), within 1.2 x it of the destination
    STEP: 2              // degrees: the spiral's points (drawn, and searched for WP1)
  };
  var STOPS = ["crs", "view", "dest"];   // COMM1's stops
  var STOPS2 = ["entry", "circle", "hac", "reset"];   // COMM2's: ENTRY 1, CIRCLE, its OVHD / STRT-IN (with CIRCLE), Reset scale

  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function n360(a) { return ((a % 360) + 360) % 360; }
  function w180(a) { return n360(a + 180) - 180; }
  function degs(a) { return String(Math.round(a * 10) / 10) + "°"; }   // 50°, 2.5°
  function deg3(a) { var s = String(Math.round(n360(a)) % 360); while (s.length < 3) s = "0" + s; return s; }
  function dist(m) {
    m = Math.abs(m);
    if (m < 1000) return Math.round(m) + " m";
    if (m < 1e5) return (m / 1000).toFixed(1) + " km";
    return Math.round(m / 1000).toLocaleString("en-GB") + " km";
  }
  function speed(v) { return Math.round(Math.abs(v)) + " m/s"; }
  function niceStep(x) { var e = Math.pow(10, Math.floor(Math.log10(x))), f = x / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e; }

  // ---- what you've set, kept in this browser ----
  var kept = (function () { try { return JSON.parse(localStorage.getItem("ft3000-traj") || "{}") || {}; } catch (e) { return {}; } })();
  var T = {
    mode: kept.mode === "hud" ? "hud" : "pick",   // the destination: Nav › Syst's pick, or the game's target
    view: kept.view === "C" ? "C" : "N",          // the top-down view: north up, or course up
    prof: kept.prof === "circle" ? "circle" : "entry",   // the profile: ENTRY 1, or CIRCLE (the HAC)
    hmode: kept.hmode === "strt" ? "strt" : "ovhd",      // CIRCLE's HAC: overhead (the bigger turn) or straight in
    hac: null,                                    // CIRCLE armed: {key, crs, mode, side (1 right, -1 left), stage: acq | hac | ogs, k, psiE, psi}
    crs: kept.crs && typeof kept.crs === "object" ? kept.crs : {},   // the course for each destination (yours, or taken at the glide) ...
    took: kept.took && typeof kept.took === "object" ? kept.took : {},   // ... the ones taken at the glide (dropped when you're back in orbital cruise)
    focus: "crs", grab: false, focus2: "entry",   // COMM1's outline, the course box grabbed, COMM2's outline
    stepTxt: "", stepAt: 0, lastClick: 0, lastDir: 0, wheelAcc: 0, wheelAt: 0,
    me: null, nav: null, dest: null, g: null, phase: "wait", scale: SCALE.glide, raf: 0, frameAt: 0, textAt: 0,
    zoom: null, zoomKey: null, wasSc: null,       // your own scale (metres; null: the phase's), and what it was set for
    meFix: null, missAt: null                     // the last reading with a position, and since when there's been none
  };
  function keep() {
    try { localStorage.setItem("ft3000-traj", JSON.stringify({ mode: T.mode, view: T.view, crs: T.crs, took: T.took, prof: T.prof, hmode: T.hmode })); } catch (e) { /* storage blocked */ }
  }

  // ---- the filter: position and velocity along one axis, at uneven times ----
  function KF(r) { this.r = r; this.x = null; this.t = 0; }
  KF.prototype.update = function (t, z, q) {
    if (this.x === null) { this.x = [z, 0]; this.P = [[this.r, 0], [0, 1e6]]; this.t = t; return; }
    var dt = Math.max(1e-3, t - this.t), P = this.P;
    this.t = Math.max(this.t, t);
    var x0 = this.x[0] + dt * this.x[1], x1 = this.x[1];
    var p00 = P[0][0] + dt * (P[1][0] + P[0][1]) + dt * dt * P[1][1] + q * Math.pow(dt, 4) / 4;
    var p01 = P[0][1] + dt * P[1][1] + q * Math.pow(dt, 3) / 2;
    var p10 = P[1][0] + dt * P[1][1] + q * Math.pow(dt, 3) / 2;
    var p11 = P[1][1] + q * dt * dt;
    var s = p00 + this.r, k0 = p00 / s, k1 = p10 / s, e = z - x0;
    this.x = [x0 + k0 * e, x1 + k1 * e];
    this.P = [[(1 - k0) * p00, (1 - k0) * p01], [p10 - k1 * p00, p11 - k1 * p01]];
  };
  KF.prototype.nis = function (t, z, q) {   // how far a reading lands from where the filter expected it, squared, in its spread
    if (this.x === null) return 0;
    var dt = Math.max(1e-3, t - this.t), P = this.P, e = z - (this.x[0] + dt * this.x[1]);
    var p00 = P[0][0] + dt * (P[1][0] + P[0][1]) + dt * dt * P[1][1] + q * Math.pow(dt, 4) / 4;
    return e * e / (p00 + this.r);
  };
  KF.prototype.at = function (t, ahead) { return this.x[0] + this.x[1] * clamp(t - this.t, 0, ahead); };
  KF.prototype.reset = function (t, z) {   // after a silence (you'd stopped): afresh from this reading, speed unknown
    this.x = [z, 0]; this.P = [[this.r, 0], [0, 1e6]]; this.t = t;
  };
  KF.prototype.restart = function (z, t) {   // a jump in the readings (keeps the speed)
    if (this.x) { this.x[0] = z; this.P[0][0] = this.r; this.P[0][1] = this.P[1][0] = 0; this.t = t; }
  };

  // where you are on a flat map of the planet round a point near you (metres east, north), filtered
  function Nav(me, from) {
    this.body = me.body; this.R = me.r; this.lat0 = me.lat; this.lon0 = me.lon; this.cl = Math.max(0.05, Math.cos(me.lat * RAD));
    this.kx = new KF(R_H); this.ky = new KF(R_H); this.kz = new KF(R_V);
    this.trail = from ? from.trail : []; this.seen = null; this.avg = me.avg; this.t = 0;
    this.q = Q_HI; this.blend = null;   // across the ground: how agile; the correction being eased in
    if (from && from.kx.x) {   // re-centred: carries on at the same speed
      var o = from.at(from.kx.t, true), p = this.xy(o.lat, o.lon);   // where the filter had you, on the new map
      this.q = from.q; this.blend = from.blend; this.n = from.n; this.k = from.k;
      this.kx.x = [p[0], from.kx.x[1]]; this.kx.P = from.kx.P; this.kx.t = from.kx.t;
      this.ky.x = [p[1], from.ky.x[1]]; this.ky.P = from.ky.P; this.ky.t = from.ky.t;
      this.kz = from.kz; this.t = from.t; this.last = from.last; this.cv = from.cv;
    }
  }
  Nav.prototype.gap = function (v) {   // seconds the game should take to write again at velocity v (the WRITE_DEG rule)
    var rate = Math.max(Math.abs(v[1]) / (this.R * RAD), Math.abs(v[0]) / (this.R * this.cl * RAD));   // degrees a second
    return rate > 0 ? WRITE_DEG / rate : Infinity;
  };
  Nav.prototype.ahead = function (v) {   // how long past a reading it carries you on (the game's writes come on whole seconds: one late)
    return Math.hypot(v[0], v[1]) < SLOW ? AHEAD_SLOW : clamp(this.gap(v) + 1.5, AHEAD_SLOW, AHEAD_MAX);
  };
  Nav.prototype.stillAfter = function (v) {   // a silence this long means you've stopped (longer, the faster you were going: the
    var gs = Math.hypot(v[0], v[1]);          // game goes quiet a few seconds as you drop into the glide)
    return (gs < SLOW ? STILL : Math.max(STILL, this.ahead(v) + 1)) + Math.min(10, Math.hypot(v[0], v[1], v[2]) / DECEL);
  };
  Nav.prototype.xy = function (lat, lon) { return [this.R * this.cl * w180(lon - this.lon0) * RAD, this.R * (lat - this.lat0) * RAD]; };
  Nav.prototype.add = function (t, me, now) {   // a reading from t (page seconds), taken in at now (default: now)
    var p = this.xy(me.lat, me.lon), last = this.last, ks = [this.kx, this.ky, this.kz];
    now = now == null ? performance.now() / 1000 : now;
    this.n = (this.n || 0) + 1;   // (readings taken in: the first few settle it, and show at once)
    var was = this.kx.x ? this.shown(now) : null, snap = !was || !!me.sc || this.n <= 3;   // (what the pages showed)
    // a silence longer than the game should keep at the speed it had (once it has one: two readings since it started
    // afresh): you'd stopped - start afresh from this reading, rather than guess the speed from the gap
    var fresh = !!(last && this.kx.x && this.k >= 2 && t - last.t > this.stillAfter([this.kx.x[1], this.ky.x[1], this.kz.x[1]]) + 1);
    if (fresh) { this.cv = null; this.q = Q_HI; snap = true; this.n = 1; }
    if (this.avg !== me.avg) { this.kz.restart(me.alt, t); snap = true; }   // the game switched what it measures altitude from
    if (me.sc && last && t - last.t > 0.05 && this.avg === me.avg) {   // orbital cruise: the change since the last reading
      var dt = t - last.t, q = this.xy(last.lat, last.lon), v = [(p[0] - q[0]) / dt, (p[1] - q[1]) / dt, (me.alt - last.alt) / dt];
      var e = this.cv ? CRUISE_EASE : 1;
      this.cv = this.cv ? [this.cv[0] + (v[0] - this.cv[0]) * e, this.cv[1] + (v[1] - this.cv[1]) * e, this.cv[2] + (v[2] - this.cv[2]) * e] : v;
      [[this.kx, p[0], this.cv[0], R_H], [this.ky, p[1], this.cv[1], R_H], [this.kz, me.alt, this.cv[2], R_V]].forEach(function (a) {
        a[0].x = [a[1], a[2]]; a[0].P = [[a[3], 0], [0, 1e4]]; a[0].t = t;   // (the filter carries on from here after the glide)
      });
      this.q = Q_HI;
    } else {
      if (!me.sc) this.cv = null;
      if (fresh) { this.kx.reset(t, p[0]); this.ky.reset(t, p[1]); this.kz.reset(t, me.alt); this.k = 1; }
      else {
        this.k = (this.k || 0) + 1;   // (readings since it started afresh)
        if (me.glide || !this.kx.x || this.kx.nis(t, p[0], this.q) + this.ky.nis(t, p[1], this.q) > NIS_HI) this.q = Q_HI;
        this.kx.update(t, p[0], this.q); this.ky.update(t, p[1], this.q); this.kz.update(t, me.alt, Q_V);
        this.q = Math.max(Q_LO, this.q * Q_EASE);
      }
    }
    var is = this.raw(now), off = was && !snap ? [was.x - is.x, was.y - is.y, was.z - is.z, was.v[0] - is.v[0], was.v[1] - is.v[1], was.v[2] - is.v[2]] : null;
    this.blend = off && Math.hypot(off[0], off[1], off[2]) <= BLEND_MAX ? { t0: now, off: off } : null;
    this.avg = me.avg;
    this.last = { t: t, lat: me.lat, lon: me.lon, alt: me.alt };
    this.t = t;
    this.trail.push([me.lat, me.lon, me.alt]);
    if (this.trail.length > 40) this.trail.shift();
  };
  Nav.prototype.raw = function (t) {   // the filter's own estimate at t: metres east, north, up on its map, and m/s
    var v = [this.kx.x[1], this.ky.x[1], this.kz.x[1]], ah = this.ahead(v);
    return { x: this.kx.at(t, ah), y: this.ky.at(t, ah), z: this.kz.at(t, ah), v: v };
  };
  Nav.prototype.shown = function (t) {   // ... with the last correction still easing in (what the pages show)
    var r = this.raw(t), b = this.blend;
    if (!b) return r;
    var u = clamp((t - b.t0) / BLEND, 0, 1), w = 1 - u * u * (3 - 2 * u), o = b.off;
    return { x: r.x + o[0] * w, y: r.y + o[1] * w, z: r.z + o[2] * w, v: [r.v[0] + o[3] * w, r.v[1] + o[4] * w, r.v[2] + o[5] * w] };
  };
  Nav.prototype.at = function (t, best) {   // where you are at t (page seconds), and your velocity (m/s east, north, up): as the pages
    var r = best ? this.raw(t) : this.shown(t);   // show it, or (best) the filter's own estimate, for marking a point
    var age = t - this.t, still = age > this.stillAfter(r.v);
    return { lat: this.lat0 + r.y / this.R / RAD, lon: this.lon0 + r.x / (this.R * this.cl) / RAD, alt: r.z,
             v: still ? [0, 0, 0] : r.v, age: age, still: still };
  };

  // a reading from the board's latest state (the same reading again is skipped)
  function ingest(y) {
    var me = y.me;
    T.me = me || null;
    if (!me || me.lat == null || me.alt == null || !me.r) {   // no position: a miss starts (the last one carries on a moment)
      if (T.meFix && T.missAt == null) T.missAt = performance.now() / 1000;
      return false;
    }
    T.meFix = me; T.missAt = null;
    if (T.nav && (T.nav.body !== me.body || Math.abs(T.nav.R - me.r) > 1)) T.nav = null;
    if (T.nav && me.t != null && T.nav.seen === me.t) return false;
    var t = performance.now() / 1000 - (me.age || 0);
    if (!T.nav) T.nav = new Nav(me);
    else { var p = T.nav.xy(me.lat, me.lon); if (Math.hypot(p[0], p[1]) > REANCHOR) T.nav = new Nav(me, T.nav); }
    T.nav.seen = me.t;
    var tm = ED.timing.on(), nowS = performance.now() / 1000, nv = T.nav, pre = tm && nv.kx.x ? nv.raw(nowS) : null, preT = nv.kx.t;
    nv.add(t, me);
    if (tm) {   // timing log: how old the reading was when it got here (written to taken in), and how far it moved where the filter had you now
      var q = function (x, n) { var k = Math.pow(10, n); return Math.round(x * k) / k; };
      var o = { mt: me.t, age: me.age, e2e: me.t != null ? q(ED.timing.wall() / 1000 - me.t, 3) : null, sc: me.sc ? 1 : 0, glide: me.glide ? 1 : 0,
                vx: q(nv.kx.x[1], 1), vy: q(nv.ky.x[1], 1), vz: q(nv.kz.x[1], 1) };
      if (pre) { var post = nv.raw(nowS); o.gap = q(t - preT, 3); o.jx = q(post.x - pre.x, 2); o.jy = q(post.y - pre.y, 2); o.jz = q(post.z - pre.z, 2); }
      ED.timing.rec("p.in", o);
    }
    return true;
  }

  // the destination: what Nav › Syst has selected, or the game's target - a planetary facility with a position (and the pad
  // you've been given there, where the board knows where it is)
  function resolve(y, mode) {   // mode: "pick" (what 1 Syst has selected) or "hud"; Traj's own switch if not given (Atk has its own)
    mode = mode || T.mode;
    var entries = y.entries || [], key = mode === "hud" ? y.target : S.sySel, e = null;
    for (var i = 0; i < entries.length; i++) if (entries[i].key === key) { e = entries[i]; break; }
    if (!e) return { ok: false, title: "No destination", why: mode === "hud" ? "No DEST - target something here in the game" : "Select a planetary facility in 1 Syst" };
    var p = e.pic || {};
    if (p.kind !== "surface") {   // a body, or something in orbit
      var orb = e.icon === "carrier" || e.icon === "squadron" ? "Carrier" : e.icon === "megaship" ? "Megaship" : "Orbital station";
      return { ok: false, key: e.key, name: e.name, title: "Not a surface target",
               why: e.kind === "planet" || e.kind === "star" ? "Body selected - planetary target required" : orb };
    }
    if (p.lat == null || p.lon == null)   // on the surface, but nobody's recorded where (your journal, Spansh or EDSM)
      return { ok: false, key: e.key, name: e.name, title: "Target position unknown", why: "No surface coordinates - recon required" };
    var pad = y.pad && e.settlement && e.settlement.key === y.pad.key ? y.pad : null;
    return { ok: true, key: e.key, name: e.name, body: p.body || e.body || "", lat: p.lat, lon: p.lon, pad: pad };
  }

  // great circle from a to b: distance (m) and the bearing each way
  function arc(lat1, lon1, lat2, lon2, R) {
    var p1 = lat1 * RAD, p2 = lat2 * RAD, dl = (lon2 - lon1) * RAD;
    var h = Math.sin((p2 - p1) / 2) * Math.sin((p2 - p1) / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
    var d = 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
    function brg(a1, b1, dlo) { return n360(Math.atan2(Math.sin(dlo) * Math.cos(b1), Math.cos(a1) * Math.sin(b1) - Math.sin(a1) * Math.cos(b1) * Math.cos(dlo)) / RAD); }
    return { d: d, ab: brg(p1, p2, dl), ba: brg(p2, p1, -dl) };
  }
  // your position relative to a point on the ground: across its level (along the ground's tangent there) and up
  // from it, allowing for the planet's curve
  function rel(lat, lon, alt, d, R) {
    var a = arc(d.lat, d.lon, lat, lon, R), phi = a.d / R;
    return { d: a.d, bDS: a.ab, bSD: a.ba, X: (R + alt) * Math.sin(phi), Y: (R + alt) * Math.cos(phi) - R };
  }

  // ---- the phase, and its scale ----
  function phaseOf(me, toSite) {
    if (!me || me.lat == null) return "wait";
    if (me.landed) return toSite <= FINAL_OUT ? "final" : "landed";
    if (me.sc) return "cruise";
    if (me.glide) return "glide";
    if (toSite <= FINAL_IN || (T.phase === "final" && toSite <= FINAL_OUT)) return "final";
    return "flight";
  }
  function scaleNow() { return T.zoom || T.scale; }   // the pictures' scale: yours, else the phase's
  function scaleFor(ph, d) {   // fixed for each phase; out in orbital cruise (or flying far off), 1,000 km and 100 km
    var cur = T.scale;
    if (ph === "final") return SCALE.final;
    if (T.prof === "circle" && ph !== "cruise" && (d <= HAC.SCALE * 1.2 || (cur === HAC.SCALE && d <= HAC.SCALE * 1.5))) return HAC.SCALE;   // (flying CIRCLE)
    if (ph === "glide") return SCALE.glide;
    if (ph !== "cruise" && (d <= SCALE.glide || (cur === SCALE.glide && d <= SCALE.glide * 1.2))) return SCALE.glide;
    return d <= SCALE.near || (cur === SCALE.near && d <= SCALE.near * 1.2) ? SCALE.near : SCALE.far;
  }
  // the course: yours, else the one taken when the glide started (until then, the bearing you have to it)
  function takeCourse(d, me) {
    if (!d || !d.ok || T.crs[d.key] != null || !T.nav || !me || me.lat == null || me.sc) return;
    if (String(me.body || "").toLowerCase() !== String(d.body).toLowerCase()) return;
    T.crs[d.key] = Math.round(n360(arc(me.lat, me.lon, d.lat, d.lon, T.nav.R).ab)) % 360;
    T.took[d.key] = true;
    keep();
  }
  function dropTaken() {   // back in orbital cruise: the next glide takes its own (a course you set stays)
    var any = false;
    Object.keys(T.took).forEach(function (k) { delete T.crs[k]; delete T.took[k]; any = true; });
    if (any) keep();
  }

  // ---- CIRCLE's geometry: metres east and north of the destination, flat (it's all within a few tens of km) ----
  function hacGeom(crs, side, k) {   // the course, WP2, the HAC's centre (R_OUT beside WP2, on its side); k: metres of radius a radian of turn to go
    var c = [Math.sin(crs * RAD), Math.cos(crs * RAD)], nr = [c[1], -c[0]], w2 = [-c[0] * HAC.WP2_OUT, -c[1] * HAC.WP2_OUT];
    return { crs: crs, side: side, k: k, c: c, nr: nr, w2: w2, cc: [w2[0] + side * nr[0] * HAC.R_OUT, w2[1] + side * nr[1] * HAC.R_OUT] };
  }
  function hacAt(h, psi) {   // the point psi radians of turn short of WP2, its radius, and the way you fly there
    var b = h.crs * RAD - h.side * (Math.PI / 2 + psi), r = HAC.R_OUT + h.k * psi, u = [Math.sin(b), Math.cos(b)], du = [Math.cos(b), -Math.sin(b)];
    var m = [h.side * r * du[0] - h.k * u[0], h.side * r * du[1] - h.k * u[1]], ml = Math.hypot(m[0], m[1]);
    return { p: [h.cc[0] + r * u[0], h.cc[1] + r * u[1]], r: r, m: [m[0] / ml, m[1] / ml] };
  }
  function hacPsi(h, A) {   // the turn to go (radians, 0 - 2 pi) from where A is round the HAC's centre
    var b = Math.atan2(A[0] - h.cc[0], A[1] - h.cc[1]), psi = h.side * (h.crs * RAD - b) - Math.PI / 2, tw = 2 * Math.PI;
    return ((psi % tw) + tw) % tw;
  }
  function hacTangent(h, A) {   // WP1: the turn to go where a line from A meets the HAC tangent to it, flying on round it (null: none - you're inside it)
    var n = Math.round(360 / HAC.STEP), prev = null;
    function f(psi) { var q = hacAt(h, psi), dx = q.p[0] - A[0], dy = q.p[1] - A[1]; return { cr: dx * q.m[1] - dy * q.m[0], dot: dx * q.m[0] + dy * q.m[1] }; }
    for (var i = 0; i <= n; i++) {
      var psi = 2 * Math.PI * i / n, v = f(psi);
      if (prev && (prev.v.cr <= 0) !== (v.cr <= 0) && prev.v.dot > 0 && v.dot > 0) {
        var a = prev.psi, b = psi, fa = prev.v.cr;
        for (var j = 0; j < 40; j++) { var mid = (a + b) / 2, fm = f(mid).cr; if ((fm <= 0) === (fa <= 0)) { a = mid; fa = fm; } else b = mid; }
        return (a + b) / 2;
      }
      prev = { psi: psi, v: v };
    }
    return null;
  }
  function hacSolve(crs, side, A, k) {   // the HAC from A - its radius R_IN where you'd join it (k given: as it is)
    var kk = k != null ? k : (HAC.R_IN - HAC.R_OUT) / Math.PI, h = hacGeom(crs, side, kk), t = hacTangent(h, A);
    for (var it = 0; k == null && t != null && it < 5; it++) {
      kk = (HAC.R_IN - HAC.R_OUT) / Math.max(t, 0.5);
      h = hacGeom(crs, side, kk);
      t = hacTangent(h, A);
    }
    return { h: h, psiT: t };
  }
  function hacLen(h, psi) { return HAC.R_OUT * psi + h.k * psi * psi / 2; }   // the HAC's length from psi to go to WP2 (metres)
  function hacRef(L) {   // the reference altitude (metres above the destination) this far from it along the path
    var tO = Math.tan(HAC.OGS * RAD);
    return L <= HAC.WP2_OUT ? L * tO : HAC.WP2_OUT * tO + (L - HAC.WP2_OUT) * Math.tan(HAC.DESC * RAD);
  }
  function hacArm(key, crs, A) {   // CIRCLE armed: the side (OVHD: the bigger turn, STRT-IN: the smaller), and where you are on it
    var r = hacSolve(crs, 1, A), l = hacSolve(crs, -1, A), pick;
    if (r.psiT == null && l.psiT == null) pick = (A[0] - r.h.w2[0]) * r.h.nr[0] + (A[1] - r.h.w2[1]) * r.h.nr[1] >= 0 ? r : l;   // (inside both: the side you're on)
    else if (r.psiT == null || l.psiT == null) pick = r.psiT == null ? l : r;
    else pick = (T.hmode === "strt") === (r.psiT <= l.psiT) ? r : l;
    var h = pick.h, a = (A[0] - h.w2[0]) * h.c[0] + (A[1] - h.w2[1]) * h.c[1], x = (A[0] - h.w2[0]) * h.nr[0] + (A[1] - h.w2[1]) * h.nr[1];
    var onOgs = a >= -200 && a <= HAC.WP2_OUT + 200 && Math.abs(x) <= HAC.OGS_X;
    return { key: key, crs: crs, mode: T.hmode, side: h.side, stage: onOgs ? "ogs" : "acq", k: h.k, psiE: pick.psiT, psi: null };
  }
  function hacStep(H, A, gs) {   // where you are on CIRCLE now (and its stage: ACQ - to WP1 - then HAC, then the OGS)
    var tw = 2 * Math.PI, out = { stage: H.stage };
    if (H.stage === "acq") {
      var sv = hacSolve(H.crs, H.side, A, null), h = sv.h, w1 = sv.psiT != null ? hacAt(h, sv.psiT).p : null;
      var d1 = w1 ? Math.hypot(w1[0] - A[0], w1[1] - A[1]) : null;
      if (w1 && d1 >= Math.max(HAC.CAPTURE, gs * HAC.CAPTURE_S)) {   // on the way to WP1 (the HAC sized from here: R_IN there)
        H.k = h.k; H.psiE = sv.psiT;
        out.h = h; out.w1 = w1; out.d1 = d1; out.b1 = n360(Math.atan2(w1[0] - A[0], w1[1] - A[1]) / RAD); out.psiT = sv.psiT;
        out.L = d1 + hacLen(h, sv.psiT) + HAC.WP2_OUT;
      } else {   // there - or inside it: on the HAC as it was sized on the way in (kept from now on)
        var me0 = hacPsi(hacGeom(H.crs, H.side, H.k), A);
        if (H.psiE == null) H.psiE = me0;
        H.stage = "hac"; H.psi = me0 + Math.floor((H.psiE + 0.3 - me0) / tw) * tw;   // (the turn to go: no more than WP1's)
      }
    }
    if (H.stage === "hac") {
      var hh = hacGeom(H.crs, H.side, H.k), me = hacPsi(hh, A);
      if (H.psi != null) me += Math.round((H.psi - me) / tw) * tw;   // (the turn to go, carried on round from the last)
      H.psi = me;
      out.h = hh; out.stage = "hac";
      if (me <= 0) { H.stage = "ogs"; }
      else if (me > (H.psiE || 0) + Math.PI / 2) { H.stage = "acq"; H.psi = null; }   // (going the wrong way round: join it again)
      else {
        var q = hacAt(hh, me);
        out.psi = me; out.rr = q.r; out.rerr = Math.hypot(A[0] - hh.cc[0], A[1] - hh.cc[1]) - q.r;
        out.L = hacLen(hh, me) + HAC.WP2_OUT; out.d2 = hacLen(hh, me);
      }
    }
    if (H.stage === "ogs") {
      out.h = out.h || hacGeom(H.crs, H.side, H.k);
      out.stage = "ogs"; out.L = Math.hypot(A[0], A[1]);
    }
    return out;
  }

  // ---- everything the panels show, at time t ----
  function guide(t) {
    var d = T.dest, me = T.me, g = { ok: false, d: d, dok: !!(d && d.ok), phase: "wait", scale: scaleNow() };
    if ((!me || me.lat == null) && T.meFix && T.missAt != null && t - T.missAt < MISS) me = T.meFix;   // a short miss
    g.crs = g.dok && T.crs[d.key] != null ? T.crs[d.key] : null;
    if (!g.dok) { g.title = d ? d.title || "No destination" : "No destination"; g.why = d ? d.why : "Select a planetary facility in 1 Syst"; return g; }
    // no position: the game gives one only near a planet (orbital cruise and below)
    if (!me || me.lat == null) { g.title = "No state vector"; g.why = "No planetary surface fix - outside orbital cruise range"; T.phase = "wait"; return g; }
    if (String(me.body || "").toLowerCase() !== String(d.body).toLowerCase()) {
      g.title = "Reference body mismatch"; g.why = "Dest on " + d.body; T.phase = "wait"; return g;
    }
    if (!T.nav || !T.nav.kx.x) { g.title = "Acquiring state vector"; g.why = ""; return g; }
    var p = T.nav.at(t), R = T.nav.R, site = rel(p.lat, p.lon, p.alt, d, R);
    var ph = phaseOf(me, site.d);
    if (ph === "final" && !me.landed && T.prof === "circle" && !(T.hac && T.hac.key === d.key && T.hac.stage === "ogs")) ph = "flight";   // (CIRCLE: the HAC can pass within FINAL_IN - the final approach is from the OGS)
    T.phase = ph;
    T.scale = scaleFor(ph, site.d);
    // the final approach: to your pad, once docking's granted and the board knows where it is
    var tgt = d, onPad = false;
    if (ph === "final" && d.pad && d.pad.e != null) {
      var lat = d.lat + d.pad.n / R / RAD;
      tgt = { lat: lat, lon: d.lon + d.pad.e / (R * Math.max(0.05, Math.cos(lat * RAD))) / RAD };
      onPad = true;
    }
    var r = onPad ? rel(p.lat, p.lon, p.alt, tgt, R) : site;
    var auto = T.crs[d.key] == null, crs = auto ? Math.round(n360(r.bSD)) % 360 : T.crs[d.key];
    var vE = p.v[0], vN = p.v[1], vU = p.v[2];
    var gs = Math.hypot(vE, vN), clos = vE * Math.sin(r.bSD * RAD) + vN * Math.cos(r.bSD * RAD);
    var th = Math.atan2(r.Y, r.X) / RAD, de = auto ? 0 : w180(crs + 180 - r.bDS);
    var trail = T.nav.trail.map(function (q) { return rel(q[0], q[1], q[2], tgt, R); });
    var g = {
      ok: true, d: d, dok: true, phase: ph, scale: scaleNow(), onPad: onPad, padNum: d.pad ? d.pad.num : null, toSite: site.d,
      R: R, crs: crs, auto: auto, dist: r.d, X: r.X, Y: r.Y, bDS: r.bDS, bSD: r.bSD, alt: p.alt, age: p.age, still: p.still,
      vE: vE, vN: vN, vU: vU, gs: gs, clos: clos, vv: -vU, th: th, de: de, xtk: auto ? 0 : r.d * Math.sin(de * RAD),
      trk: n360(Math.atan2(vE, vN) / RAD), hdg: me.hdg, fpa: gs > 1 ? Math.atan2(-vU, gs) / RAD : 0,
      altErr: r.Y - r.X * TAN_OPT, trail: trail, me: me, entry: ph !== "cruise"
    };
    // ENTRY 1's vertical velocity: at your closing speed, OPT's - in the SHALLOW-STEEP window
    g.vw = { spd: clos, req: clos * TAN_OPT, lo: clos * Math.tan(SHALLOW * RAD), hi: clos * Math.tan(STEEP * RAD), max: clos * Math.tan(66 * RAD), ang: OPT };
    if (T.prof === "circle") circle(g, d, me, site, ph);
    return g;
  }
  // CIRCLE: armed from where you are (again for a new destination or course, OVHD / STRT-IN, or back in orbital cruise),
  // then where you are on it, its reference altitude and the vertical velocity it needs
  function circle(g, d, me, site, ph) {
    if (ph !== "cruise" && g.auto) {   // (it needs a course: the bearing you have now - dropped again for ENTRY 1, or back in orbital cruise)
      takeCourse(d, me);
      if (T.crs[d.key] != null) { g.crs = T.crs[d.key]; g.auto = false; T.circleTook = d.key; }
    }
    if (ph !== "cruise" && !g.auto) { g.de = w180(g.crs + 180 - g.bDS); g.xtk = g.dist * Math.sin(g.de * RAD); }   // (as ENTRY 1's, on the course it's taken)
    var A = [site.X * Math.sin(site.bDS * RAD), site.X * Math.cos(site.bDS * RAD)], H = T.hac;
    if (!H || H.key !== d.key || H.crs !== g.crs || H.mode !== T.hmode || ph === "cruise") H = T.hac = hacArm(d.key, g.crs, A);
    var o = hacStep(H, A, g.gs), tO = Math.tan(HAC.OGS * RAD), tD = Math.tan(HAC.DESC * RAD);
    o.A = A; o.side = H.side; o.mode = H.mode; o.psiE = H.psiE; o.Y = site.Y;
    o.slope = o.stage === "ogs" ? HAC.OGS : HAC.DESC;
    o.ref = o.L != null ? hacRef(o.L) : null;
    o.err = o.ref != null ? site.Y - o.ref : null;
    o.tol = o.ref != null ? Math.max(HAC.TOL_M, Math.abs(o.ref) * HAC.TOL) : null;
    o.L1 = o.h && H.psiE != null ? HAC.WP2_OUT + hacLen(o.h, H.psiE) : null;   // (the path's length from WP1)
    g.hac = o;
    var grad = o.stage === "ogs" ? tO : tD, sp = g.gs;
    g.vw = { spd: sp, req: sp * grad, lo: sp * Math.tan(Math.max(0, o.slope - HAC.WIN) * RAD), hi: sp * Math.tan((o.slope + HAC.WIN) * RAD),
             max: sp * Math.tan((o.slope + 2 * HAC.WIN) * RAD), ang: o.slope };
  }
  function latState(g) {
    if (g.auto) return { chip: g.entry ? "Course auto" : "Course at glide", col: C.rule2 };
    var a = Math.abs(g.de), side = g.de > 0 ? "R " : "L ";
    if (a > LAT) return { chip: "Out " + side + a.toFixed(1) + "°", col: C.bad };
    if (a <= 0.3) return { chip: "On course", col: C.text };
    return { chip: side + a.toFixed(1) + "°", col: C.acc };
  }
  function vertState(g) {
    if (!g.entry) return { chip: "Orbital cruise", col: C.rule2 };
    if (g.th > STEEP) return { chip: "Too steep " + g.th.toFixed(1) + "°", col: C.bad };
    if (g.th < SHALLOW) return { chip: "Too shallow " + g.th.toFixed(1) + "°", col: C.bad };
    if (Math.abs(g.th - OPT) <= 1) return { chip: "On path", col: C.text };
    return { chip: (g.th > OPT ? "High " : "Low ") + Math.abs(g.th - OPT).toFixed(1) + "°", col: C.acc };
  }
  function hacLat(g, ls) {   // CIRCLE's lateral chip: ACQ (to WP1), HAC (the turn to go), then the course (OGS)
    var h = g.hac, sd = h.side > 0 ? "R" : "L";
    if (!g.entry) return { chip: "HAC " + sd + " armed", col: C.rule2 };
    if (h.stage === "acq") return { chip: "Acq · HAC " + sd, col: C.acc };
    if (h.stage === "hac") return { chip: "HAC · " + (h.psi != null ? Math.round(h.psi / RAD) : "--") + "° to go", col: h.rerr != null && Math.abs(h.rerr) > 300 ? C.acc : C.text };
    return { chip: "OGS · " + ls.chip, col: ls.col };
  }
  function hacVert(g) {   // CIRCLE's vertical chip: on the reference altitude, or how high or low
    var h = g.hac;
    if (!g.entry) return { chip: "Orbital cruise", col: C.rule2 };
    if (h.err == null) return { chip: "No reference", col: C.rule2 };
    var a = Math.abs(h.err);
    if (a <= h.tol) return { chip: "On ref", col: C.text };
    return { chip: (h.err > 0 ? "High " : "Low ") + dist(a), col: a > 3 * h.tol ? C.bad : C.acc };
  }
  function gsDefl(th) {   // the glide-slope needle, -1 (full up: fly up) .. 1 (full down)
    var even = GS_SCALE === "even";
    return clamp(th > OPT || even ? (th - OPT) / (STEEP - OPT) : (th - OPT) / (OPT - SHALLOW), -1, 1);
  }

  // ---- drawing: SVG in the picture's own pixels (one the size of a pixel of the VGA text), shown by pixel.js ----
  function n1(v) { return Math.round(clamp(v, -99999, 99999) * 10) / 10; }
  function P2(p) { return n1(p[0]) + " " + n1(p[1]); }
  function line(pts, col, dash, closed, op) {
    if (pts.length < 2) return "";
    return '<path d="M' + pts.map(P2).join(" L") + (closed ? " Z" : "") + '" stroke="' + col + '" fill="none"' +
      (dash ? ' stroke-dasharray="' + dash.join(" ") + '"' : "") + (op != null && op < 1 ? ' opacity="' + op + '"' : "") + "></path>";
  }
  function poly(pts, fill, stroke, op) {
    return '<polygon points="' + pts.map(function (p) { return n1(p[0]) + "," + n1(p[1]); }).join(" ") + '" fill="' + (fill || "none") +
      '" stroke="' + (stroke || "none") + '"' + (op != null && op < 1 ? ' opacity="' + op + '"' : "") + "></polygon>";
  }
  function circ(x, y, r, stroke, fill, dash) {
    return '<circle cx="' + n1(x) + '" cy="' + n1(y) + '" r="' + n1(Math.max(0, r)) + '" stroke="' + (stroke || "none") + '" fill="' + (fill || "none") + '"' +
      (dash ? ' stroke-dasharray="' + dash.join(" ") + '"' : "") + "></circle>";
  }
  function txt(x, y, s, col, anchor, keepCase) {   // 5 x 7 letters on a dark band; x by anchor, y the middle
    var w = s.length * 6 - 1, cx = anchor === "start" ? x + w / 2 : anchor === "end" ? x - w / 2 : x;
    return '<text x="' + n1(cx) + '" y="' + n1(y) + '" fill="' + col + '" data-band="1"' + (keepCase ? ' data-case="keep"' : "") + ">" +
      ED.esc(s) + "</text>";
  }
  function bar(a, b, col, w) {   // a line w pixels thick
    var dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1, nx = -dy / l * w / 2, ny = dx / l * w / 2;
    return poly([[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny]], col, col);
  }
  function shipMark(at, u, k, col) {
    var p = [-u[1], u[0]];
    return poly([[at[0] + u[0] * 1.6 * k, at[1] + u[1] * 1.6 * k], [at[0] - u[0] * k + p[0] * k, at[1] - u[1] * k + p[1] * k],
                 [at[0] - u[0] * 0.4 * k, at[1] - u[1] * 0.4 * k], [at[0] - u[0] * k - p[0] * k, at[1] - u[1] * k - p[1] * k]], col, col);
  }
  function note(W, H, s, col, y0) {   // a message across the picture, broken into lines that fit
    var per = Math.max(8, Math.floor((W - 10) / 6)), words = String(s).toUpperCase().split(" "), lines = [""];
    words.forEach(function (w) { var l = lines[lines.length - 1]; if ((l + " " + w).trim().length > per && l) lines.push(w); else lines[lines.length - 1] = (l + " " + w).trim(); });
    var yc = y0 == null ? H / 2 : y0;
    return lines.map(function (l, i) { return txt(W / 2, yc + (i - (lines.length - 1) / 2) * 10, l, col || C.muted); }).join("");
  }
  function grid(svg) {   // the picture's size in its pixels (as pixel.js works it out)
    var cw = svg.clientWidth, ch = svg.clientHeight;
    if (!cw || !ch) return null;
    var fs = parseFloat(getComputedStyle(document.body).fontSize) || 24.5, dpr = window.devicePixelRatio || 1;
    var dev = Math.max(1, Math.round(fs / 16 * dpr));
    return { w: Math.max(1, Math.floor(cw * dpr / dev)), h: Math.max(1, Math.floor(ch * dpr / dev)) };
  }
  function paint(id, build) {
    var svg = $(id + "-svg"), sz = grid(svg);
    if (!sz) return;
    svg.setAttribute("viewBox", "0 0 " + sz.w + " " + sz.h);
    svg.innerHTML = build(sz.w, sz.h);
    ED.pixel.draw(svg, $(id), { x: 0, y: 0, w: sz.w, h: sz.h });
  }
  function unit(m) { return m >= 1000 ? "km" : "m"; }
  function tickLab(v, u) { return u === "km" ? String(Math.round(v / 10) / 100) : String(Math.round(v)); }
  function rings(scale) {   // the range rings, as parts of the picture's radius (the last, its edge)
    if (!T.zoom) return scale === SCALE.glide || scale === SCALE.final ? [1 / 3, 2 / 3, 1] : [0.25, 0.5, 1];
    var st = niceStep(scale / 4), out = [];   // zoomed: round distances (clear of the edge's label), then the edge
    for (var r = st; r <= scale * 0.8; r += st) out.push(r / scale);
    out.push(1);
    return out;
  }
  function scaleTxt(m) {
    if (m < 1000) return Math.round(m) + " m";
    if (m < 1e4) return String(Math.round(m / 100) / 10) + " km";
    return Math.round(m / 1000).toLocaleString("en-GB") + " km";
  }
  function pinned(at, from, edge) {   // a point outside the picture, brought to its edge along the line from 'from'
    return [from[0] + (at[0] - from[0]) * edge, from[1] + (at[1] - from[1]) * edge];
  }

  // left: the top-down view - the course in, its bounds, range rings, you
  function planSvg(W, H, g) {
    function beside(p, d, s) {   // a label's centre just off point p in direction d, clear of it whichever way d points (and on screen)
      var hw = s.length * 3, hh = 4, o = hw * Math.abs(d[0]) + hh * Math.abs(d[1]) + 3;
      return [clamp(p[0] + d[0] * o, hw + 1, W - hw - 1), clamp(p[1] + d[1] * o, hh + 1, H - hh - 1)];
    }
    var out = [], crs = g.crs != null ? g.crs : (g.ok ? g.crs : null), up = T.view === "C" && crs != null, rot0 = up ? crs : 0;
    var cx = W / 2, cy = up ? Math.round(H * 0.15) : H / 2, avail = up ? H - cy - 8 : Math.min(W, H) / 2 - (W > 160 ? 18 : 8);
    var span = g.scale, k = avail / span, u = unit(span);
    function pt(b, d) { var a = (b - rot0) * RAD; return [cx + d * k * Math.sin(a), cy - d * k * Math.cos(a)]; }
    function sd(b) { var a = (b - rot0) * RAD; return [Math.sin(a), -Math.cos(a)]; }
    var D = [cx, cy];
    rings(span).forEach(function (f, i, all) { out.push(circ(cx, cy, span * f * k, i === all.length - 1 ? C.rule2 : C.rule, null, i === all.length - 1 ? null : [1, 2])); });
    if (!up) {
      var ticks = "";
      for (var b = 0; b < 360; b += 10) ticks += line([pt(b, span), pt(b, span + (b % 30 ? 2 : 4) / k)], C.rule2);
      out.push(ticks);
      if (W > 160) [["N", 0], ["E", 90], ["S", 180], ["W", 270]].forEach(function (q) { var p = pt(q[1], span + 10 / k); out.push(txt(p[0], p[1], q[0], q[0] === "N" ? C.acc : C.muted)); });
    } else {
      var nu = sd(0), nb = [12, 14];
      out.push(line([[nb[0] - nu[0] * 7, nb[1] - nu[1] * 7], [nb[0] + nu[0] * 5, nb[1] + nu[1] * 5]], C.acc));
      out.push(shipMark([nb[0] + nu[0] * 5, nb[1] + nu[1] * 5], nu, 2.5, C.acc));
      out.push(txt(nb[0] + nu[0] * 14, nb[1] + nu[1] * 14, "N", C.acc));
    }
    var bOut = (crs != null ? crs : 0) + 180, ui = sd(crs != null ? crs : 0), pp = [-ui[1], ui[0]];
    var lb = up ? bOut - 32 : n360(bOut - 118);   // ring distances: beside the corridor, on screen, clear of N E S W
    if (!up && Math.abs(w180(lb - Math.round(lb / 90) * 90)) < 18) lb += 25;
    rings(span).forEach(function (f, i, all) {
      var p = pt(lb, span * f);
      out.push(txt(p[0] + 2, p[1], i === all.length - 1 ? scaleTxt(span) : tickLab(span * f, u), C.muted, "start", true));
    });
    if (crs != null) {   // the corridor: the course line in, its bounds fanning out from the destination
      var auto = !!g.auto, L = span * 2, A = pt(bOut - LAT, L), B = pt(bOut + LAT, L);
      out.push(poly([D, A, B], C.text, null, auto ? 0.06 : 0.14));
      out.push(line([A, D, B], auto ? C.rule2 : C.acc, [3, 2]));
      out.push(line([pt(bOut, L), D], auto ? C.muted : C.text, auto ? [3, 3] : null));
      out.push(line([D, pt(crs, span * 0.3)], C.text, [2, 2]));
      [0.35, 0.65].forEach(function (f) {
        var c = pt(bOut, span * f);
        out.push(line([[c[0] - ui[0] * 3 + pp[0] * 4, c[1] - ui[1] * 3 + pp[1] * 4], [c[0] + ui[0] * 3, c[1] + ui[1] * 3],
                       [c[0] - ui[0] * 3 - pp[0] * 4, c[1] - ui[1] * 3 - pp[1] * 4]], C.muted));
      });
      var cs = auto ? "CRS AUTO" : "CRS " + deg3(crs) + "°", cl = beside(pt(crs, span * 0.3), pp, cs);   // past the destination, where you won't be
      out.push(txt(cl[0], cl[1], cs, auto ? C.muted : C.text));
      if (!auto && !g.hac) { var bl = pt(bOut, span * 0.3); out.push(txt(bl[0] - pp[0] * 12, bl[1] - pp[1] * 12, "±" + degs(LAT), C.acc)); }   // (CIRCLE: the HAC's there)
    }
    if (g.hac && g.hac.h) {   // CIRCLE: the HAC round to WP2 (what you've flown of it dimmed), the OGS on in, WP1 and your line in to it
      var hc = g.hac, hh = hc.h, xy = function (q) { return pt(n360(Math.atan2(q[0], q[1]) / RAD), Math.hypot(q[0], q[1])); };
      var top = hc.stage === "acq" ? hc.psiT : hc.psiE, done = hc.stage === "hac" ? hc.psi : hc.stage === "ogs" ? 0 : null, sp1 = [], sp2 = [];
      if (top == null) top = 2 * Math.PI;
      for (var a = top; a > 0; a -= HAC.STEP * RAD) (done != null && a > done ? sp1 : sp2).push(xy(hacAt(hh, a).p));
      var w2p = xy(hh.w2), cp = xy(hh.cc);
      sp2.push(w2p);
      if (sp1.length) out.push(line(sp1.concat([sp2[0]]), C.muted, [2, 2]));
      out.push(line(sp2, C.hi));
      out.push(line([w2p, D], hc.stage === "ogs" ? C.hi : C.text));   // the OGS
      out.push(line([[cp[0] - 2, cp[1]], [cp[0] + 2, cp[1]]], C.muted), line([[cp[0], cp[1] - 2], [cp[0], cp[1] + 2]], C.muted));
      var away = function (p) { var dx = p[0] - cp[0], dy = p[1] - cp[1], l = Math.hypot(dx, dy) || 1; return [dx / l, dy / l]; };
      out.push(circ(w2p[0], w2p[1], 2.5, C.hi, C.bg));
      var l2 = beside(w2p, away(w2p), "WP2");
      out.push(txt(l2[0], l2[1], "WP2", C.hi));
      var w1 = hc.w1 || (hc.psiE != null ? hacAt(hh, hc.psiE).p : null);   // (on it, or past it: where you joined it, dimmed)
      if (w1) {
        var w1p = xy(w1), l1 = beside(w1p, away(w1p), "WP1"), wc = hc.w1 ? C.hi : C.muted;
        if (g.ok && hc.w1) out.push(line([xy(hc.A), w1p], C.hi, [3, 2]));
        out.push(circ(w1p[0], w1p[1], 2.5, wc, C.bg));
        out.push(txt(l1[0], l1[1], "WP1", wc));
      }
      var ht = "HAC " + (hc.side > 0 ? "R" : "L") + " - " + (hc.mode === "strt" ? "STRT-IN" : "OVHD");   // (beyond it, away from the course)
      var off = [hh.cc[0] - hh.w2[0], hh.cc[1] - hh.w2[1]], ol = Math.hypot(off[0], off[1]) || 1, far = HAC.R_IN + 200;
      var ho = xy([hh.cc[0] + off[0] / ol * far, hh.cc[1] + off[1] / ol * far]), hl = beside(ho, away(ho), ht);
      out.push(txt(hl[0], hl[1], ht, C.muted));
    }
    out.push(poly([[cx, cy - 4], [cx + 4, cy], [cx, cy + 4], [cx - 4, cy]], C.bg, C.hi));
    var ds = g.onPad ? "PAD " + g.padNum : "DEST", dl = beside(D, [-pp[0], -pp[1]], ds);   // (the other side of the course line)
    out.push(txt(dl[0], dl[1], ds, C.hi));
    if (!g.ok) return out.join("");
    // where you've been, where you are, and where you'll be in 60 s
    g.trail.forEach(function (q) { if (q.d <= span) { var p = pt(q.bDS, q.d); out.push(circ(p[0], p[1], 0.6, null, C.muted)); } });
    var ls = latState(g), col = !g.auto && Math.abs(g.de) > LAT && (!g.hac || g.hac.stage === "ogs") ? C.bad : C.hi, dirn = sd(g.gs > 5 ? g.trk : (g.hdg || 0));
    var S0 = pt(g.bDS, g.dist);
    if (g.dist > span) {   // beyond the picture: at its edge, pointing in, with how far
      var E0 = pt(g.bDS, span), inward = sd(g.bDS + 180);
      out.push(shipMark(E0, inward, 3.5, col));
      out.push(txt(E0[0] - inward[0] * 14, E0[1] - inward[1] * 14, dist(g.dist), col, "middle", true));
      return out.join("");
    }
    var len = g.gs * 60 * k;
    if (!g.auto && Math.cos(g.de * RAD) > 0 && (!g.hac || g.hac.stage === "ogs")) out.push(line([S0, pt(bOut, g.dist * Math.cos(g.de * RAD))], ls.col, [1, 2]));
    if (len > 3) out.push(line([S0, [S0[0] + dirn[0] * len, S0[1] + dirn[1] * len]], C.hi, [3, 2]));
    out.push(shipMark(S0, dirn, 4, col));
    return out.join("");
  }

  // right, with CIRCLE: the side profile along the path - unrolled round the HAC - its reference (the OGS up to WP2, DESC on
  // round the HAC to WP1 and out), the band where it's on, and you (with where you'll be in 60 s)
  function hacProfSvg(W, H, g) {
    var out = [], L0 = 26, R0 = 6, T0 = 16, B0 = 12, pw = W - L0 - R0, ph = H - T0 - B0, ox = W - R0, oy = H - B0;
    var sx = g.scale, k = pw / sx, sy = ph / k, step = niceStep(sx / 4), u = unit(step < 1000 ? 999 : 1000), gl = "";
    function P(x, y) { return [ox - x * k, oy - y * k]; }
    for (var y = 0; y <= sy + 1e-6; y += step) {
      gl += line([[L0, oy - y * k], [ox, oy - y * k]], C.rule);
      out.push(txt(L0 - 3, oy - y * k, tickLab(y, u), C.muted, "end", true));
    }
    for (var x = 0; x <= sx + 1e-6; x += step) {
      gl += line([[ox - x * k, T0], [ox - x * k, oy]], C.rule);
      if (x && ox - x * k > L0 + 18) out.push(txt(ox - x * k, oy + 7, tickLab(x, u), C.muted, "middle", true));
    }
    out.unshift(gl);
    out.push(txt(2, 5, "ALT " + u, C.muted, "start", true));
    var hc = g.hac || {}, n = 32, refL = [], band = [], bandLo = [];
    for (var i = 0; i <= n; i++) {   // (clipped at the top: the picture is as tall as it is wide, in metres)
      var bx = sx * i / n, ry = hacRef(bx), tol = Math.max(HAC.TOL_M, ry * HAC.TOL);
      refL.push(P(bx, Math.min(ry, sy))); band.push(P(bx, Math.min(ry + tol, sy))); bandLo.push(P(bx, Math.max(0, Math.min(ry - tol, sy))));
    }
    out.push(poly(band.concat(bandLo.reverse()), C.text, null, 0.11));
    out.push(bar(refL[0], P(Math.min(HAC.WP2_OUT, sx), Math.min(hacRef(Math.min(HAC.WP2_OUT, sx)), sy)), C.text, 2));
    out.push(line(refL, C.text));
    [[HAC.WP2_OUT, "WP2"], [hc.L1, "WP1"]].forEach(function (w) {   // where the HAC starts and ends, along the path
      if (w[0] == null || w[0] > sx) return;
      var q = P(w[0], Math.min(hacRef(w[0]), sy));
      out.push(line([[q[0], oy], [q[0], q[1]]], C.acc, [2, 2]));
      out.push(txt(q[0], T0 - 8, w[1], C.acc));
    });
    var mid = P(Math.min(HAC.WP2_OUT, sx) * 0.55, hacRef(Math.min(HAC.WP2_OUT, sx) * 0.55));
    out.push(txt(mid[0] - 6, mid[1] - 8, "OGS " + degs(HAC.OGS), C.text, "end"));
    if (sx > HAC.WP2_OUT * 1.6) { var mh = P(HAC.WP2_OUT + (sx - HAC.WP2_OUT) * 0.5, Math.min(hacRef(HAC.WP2_OUT + (sx - HAC.WP2_OUT) * 0.5), sy)); out.push(txt(mh[0], mh[1] - 9, "HAC " + degs(HAC.DESC), C.text, "middle")); }
    out.push(poly([[ox - 3, oy], [ox - 3, oy - 3], [ox + 3, oy - 3], [ox + 3, oy]], C.bg, C.hi));
    out.push(txt(ox, oy + 7, g.onPad ? "PAD " + g.padNum : "DEST", C.acc, "end"));
    if (!g.ok || hc.L == null) return out.join("");
    var col = hc.err == null || Math.abs(hc.err) <= hc.tol ? C.hi : Math.abs(hc.err) > 3 * hc.tol ? C.bad : C.acc;
    var at = P(hc.L, hc.Y), inPic = hc.L <= sx && hc.Y <= sy && hc.Y >= -20 / k;
    if (!inPic) {   // beyond the picture: at its edge, with how far along the path
      var ex = P(Math.min(hc.L, sx), clamp(hc.Y, 0, sy));
      out.push(shipMark([ex[0] + 9, ex[1]], [-1, 0], 2.5, col));
      out.push(circ(ex[0], ex[1], 3.5, col, C.bg));
      out.push(txt(ex[0] + 8, ex[1] + 8, dist(hc.L), col, "start", true));
      return out.join("");
    }
    if (g.gs > 1) out.push(line([at, P(Math.max(0, hc.L - g.gs * 60), hc.Y - g.vv * 60)], C.hi, [3, 2]));
    out.push(line([at, P(hc.L, Math.min(hc.ref, sy))], col, [1, 2]));   // (up or down to the reference)
    out.push(circ(at[0], at[1], 3.5, col, C.bg));
    return out.join("");
  }

  // right: the side profile - true angles, true scale, the planet curving away
  function profSvg(W, H, g) {
    if (T.prof === "circle") return hacProfSvg(W, H, g);
    var out = [], L0 = 26, R0 = 6, T0 = 16, B0 = 12, pw = W - L0 - R0, ph = H - T0 - B0, ox = W - R0, oy = H - B0;
    var sx = g.scale, k = pw / sx, sy = ph / k, step = niceStep(sx / 4), u = unit(step < 1000 ? 999 : 1000);
    var R = g.ok ? g.R : 1e9;
    function P(x, y) { return [ox - x * k, oy - y * k]; }
    var gl = "";
    for (var y = 0; y <= sy + 1e-6; y += step) {
      gl += line([[L0, oy - y * k], [ox, oy - y * k]], C.rule);
      out.push(txt(L0 - 3, oy - y * k, tickLab(y, u), C.muted, "end", true));
    }
    for (var x = 0; x <= sx + 1e-6; x += step) {
      gl += line([[ox - x * k, T0], [ox - x * k, oy]], C.rule);
      if (x && ox - x * k > L0 + 18) out.push(txt(ox - x * k, oy + 7, tickLab(x, u), C.muted, "middle", true));
    }
    out.unshift(gl);
    out.push(txt(2, 5, "ALT " + u, C.muted, "start", true));
    function rayEnd(a) { var ca = Math.cos(a * RAD), sa = Math.sin(a * RAD), d = Math.min((ox - L0) / ca, (oy - T0) / sa); return [ox - d * ca, oy - d * sa]; }
    var D = [ox, oy], e10 = rayEnd(SHALLOW), eOpt = rayEnd(OPT), e60 = rayEnd(STEEP);
    var wedge = [D, e10];
    if (e10[0] <= L0 + 0.5 && e60[1] <= T0 + 0.5) wedge.push([L0, T0]);
    wedge.push(e60);
    out.push(poly(wedge, C.text, null, 0.11));
    out.push(line([e10, D, e60], C.acc, [3, 2]));
    out.push(bar(D, eOpt, C.text, 2));
    out.push(txt(e60[0] + 4, T0 + 5, degs(STEEP), C.acc, "start"));
    var mid = [ox + (eOpt[0] - ox) * 0.55, oy + (eOpt[1] - oy) * 0.55];   // the path's name beside it, below and left
    out.push(txt(mid[0] - 6, mid[1] + 6, "OPT " + degs(OPT), C.text, "end"));
    out.push(txt(L0 + 3, e10[1] - 5, degs(SHALLOW), C.acc, "start"));
    if (g.ok) {   // the ground: the planet's surface drops away from the destination's level
      var ground = [];
      for (var i = 0; i <= 24; i++) { var gx = sx * i / 24; ground.push(P(gx, -gx * gx / (2 * R))); }
      out.push(line(ground, C.rule2));
    }
    out.push(poly([[ox - 3, oy], [ox - 3, oy - 3], [ox + 3, oy - 3], [ox + 3, oy]], C.bg, C.hi));
    out.push(txt(ox, oy + 7, g.onPad ? "PAD " + g.padNum : "DEST", C.acc, "end"));
    if (!g.ok) return out.join("");
    var vs = vertState(g), off = g.entry && (g.th > STEEP || g.th < SHALLOW), col = off ? C.bad : C.hi;
    var fit = Math.min(1, sx / Math.max(1, g.X), sy / Math.max(1, g.Y)), S0 = P(g.X * fit, g.Y * fit);
    out.push(line([D, S0], off ? C.bad : C.muted, [1, 2]));
    var ar = Math.min(28, pw * 0.15), arcp = [];
    for (var a = 0; a <= 16; a++) arcp.push([ox - ar * Math.cos(g.th * RAD * a / 16), oy - ar * Math.sin(g.th * RAD * a / 16)]);
    out.push(line(arcp, vs.col));
    out.push(txt(ox - (ar + 8) * Math.cos(g.th * RAD / 2), oy - (ar + 8) * Math.sin(g.th * RAD / 2), g.th.toFixed(1) + "°", vs.col, "end"));
    if (fit < 1) {   // beyond the picture: at its edge, along the line from the destination, with an arrow out and how far
      var outward = [-Math.cos(g.th * RAD), -Math.sin(g.th * RAD)];
      out.push(shipMark([S0[0] - outward[0] * 9, S0[1] - outward[1] * 9], outward, 2.5, col));
      out.push(circ(S0[0], S0[1], 3.5, col, C.bg));
      out.push(txt(S0[0] + 8, S0[1] + 8, dist(Math.hypot(g.X, g.Y)), col, "start", true));
      return out.join("");
    }
    var h = Math.hypot(g.clos, g.vv);
    if (h > 1) out.push(line([S0, P(g.X - g.clos * 60, g.Y - g.vv * 60)], C.hi, [3, 2]));
    out.push(circ(S0[0], S0[1], 3.5, col, C.bg));   // you: a circle (where you'll be in 60 s along the dashes)
    return out.join("");
  }

  // middle top: the ILS's two needles (waiting for the glide in orbital cruise)
  function ilsSvg(W, H, g) {
    var out = [], s = Math.min(W, H), cx = W / 2, cy = H / 2, R = s / 2 - 2, full = R * 0.74, dot = full / 2, dr = Math.max(1.5, s * 0.022);
    var live = g.ok && g.entry;
    out.push(live ? "" : '<g opacity="0.35">');
    out.push(circ(cx, cy, R, C.rule2));
    out.push(circ(cx, cy, R - 3, C.rule));
    [-2, -1, 1, 2].forEach(function (i) { out.push(circ(cx + i * dot, cy, dr, C.text)); out.push(circ(cx, cy + i * dot, dr, C.text)); });
    out.push(circ(cx, cy, Math.max(3, s * 0.045), C.hi));
    out.push(line([[cx - s * 0.17, cy], [cx - s * 0.06, cy]], C.hi));
    out.push(line([[cx + s * 0.06, cy], [cx + s * 0.17, cy]], C.hi));
    if (s >= 90) {
      var up = GS_SCALE === "even" ? STEEP - OPT : OPT - SHALLOW, dn = STEEP - OPT;   // the angle at each dot, top to bottom
      var labs = [degs(OPT - up), degs(OPT - up / 2), degs(OPT + dn / 2), degs(OPT + dn)];
      var left = live && -g.de > 0;   // the scale's angles on the side the localiser needle isn't
      [-2, -1, 1, 2].forEach(function (i, j) { out.push(txt(left ? cx - dr - 4 : cx + dr + 4, cy + i * dot, labs[j], C.muted, left ? "end" : "start")); });
      var ll = String(Math.round(LAT * 10) / 10);
      out.push(txt(cx - full, cy + dr + 7, ll, C.muted)); out.push(txt(cx + full, cy + dr + 7, ll, C.muted));
    }
    if (!live) {   // the flags show, the needles park
      out.push(txt(cx - R * 0.45, cy - R * 0.55, "LOC", C.bad)); out.push(txt(cx + R * 0.45, cy - R * 0.55, "GS", C.bad));
      out.push("</g>");
      if (g.ok) out.push(note(W, H, "ENTRY 1 from the glide", C.acc));
      return out.join("");
    }
    var w = Math.max(2, Math.round(s * 0.02)), gy = gsDefl(g.th) * full, hg = Math.sqrt(Math.max(0, (R - 4) * (R - 4) - gy * gy));
    if (g.auto) out.push(txt(cx - R * 0.45, cy - R * 0.55, "AUTO", C.muted));   // no course yet: no localiser
    else {
      var lx = clamp(-g.de / LAT, -1, 1) * full, hl = Math.sqrt(Math.max(0, (R - 4) * (R - 4) - lx * lx));
      out.push(bar([cx + lx, cy - hl], [cx + lx, cy + hl], Math.abs(g.de) > LAT ? C.bad : C.acc, w));
    }
    out.push(bar([cx - hg, cy + gy], [cx + hg, cy + gy], g.th > STEEP || g.th < SHALLOW ? C.bad : C.acc, w));
    return out.join("");
  }

  // middle bottom: the highway in the sky - looking down the path (OPT), gates sized to the bounds (LAT) (from the glide)
  function hitsSvg(W, H, g) {
    if (g.ok && !g.entry) { T.gateTxt = ""; return note(W, H, "Highway from the glide", C.muted); }
    var crs = g.crs;
    if (crs == null) { T.gateTxt = ""; return note(W, H, g.dok ? "Highway once the course is set" : "", C.muted); }
    var out = [], cx = W / 2, cy = H / 2, foc = (W / 2) / Math.tan(25 * RAD), near = 20, scale = g.scale;
    var bo = (crs + 180) * RAD, ce = Math.cos(OPT * RAD), se = Math.sin(OPT * RAD);
    var u = [Math.sin(bo) * ce, Math.cos(bo) * ce, se], fw = [-u[0], -u[1], -u[2]];
    var rt = [Math.sin((crs + 90) * RAD), Math.cos((crs + 90) * RAD), 0];
    var uc = [rt[1] * fw[2] - rt[2] * fw[1], rt[2] * fw[0] - rt[0] * fw[2], rt[0] * fw[1] - rt[1] * fw[0]];
    var al = [Math.sin(crs * RAD), Math.cos(crs * RAD), 0], R = g.ok ? g.R : 1e9;
    // you, in metres east / north / up of the destination (no position yet: a point on the path, to show the way)
    var Pc = g.ok ? [g.X * Math.sin(g.bDS * RAD), g.X * Math.cos(g.bDS * RAD), g.Y] : [u[0] * scale * 0.6, u[1] * scale * 0.6, u[2] * scale * 0.6];
    function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
    function dot3(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    function dep(q) { return dot3(sub(q, Pc), fw); }
    function prj(q) { var r = sub(q, Pc), z = dot3(r, fw); return [cx + foc * dot3(r, rt) / z, cy - foc * dot3(r, uc) / z]; }
    function seg(a, b) {
      var za = dep(a), zb = dep(b);
      if (za < near && zb < near) return null;
      if (za < near) { var ta = (near - za) / (zb - za); a = [a[0] + (b[0] - a[0]) * ta, a[1] + (b[1] - a[1]) * ta, a[2] + (b[2] - a[2]) * ta]; }
      else if (zb < near) { var tb = (near - zb) / (za - zb); b = [b[0] + (a[0] - b[0]) * tb, b[1] + (a[1] - b[1]) * tb, b[2] + (a[2] - b[2]) * tb]; }
      return [prj(a), prj(b)];
    }
    function gp(along, across) {   // a point on the ground (it curves away from the destination)
      var x = al[0] * along + rt[0] * across, y = al[1] * along + rt[1] * across;
      return [x, y, -(x * x + y * y) / (2 * R)];
    }
    // the ground grid and the gates: spacing fixed by the phase's scale
    var gsz = niceStep(scale / 15), sp = niceStep(scale / 15);
    var Hm = Math.max(Pc[2], 50), Rm = Math.hypot(Pc[0], Pc[1]);
    var a0 = Math.floor((-Rm - 3 * gsz) / gsz) * gsz, a1 = Math.ceil((-Rm + 2.4 * Hm + 3 * gsz) / gsz) * gsz, cw = Math.ceil((Hm * 1.2 + 3 * gsz) / gsz) * gsz;
    if ((a1 - a0) / gsz > 80) { a0 = -40 * gsz; a1 = 40 * gsz; }   // (never too many lines)
    if (cw / gsz > 40) cw = 40 * gsz;
    var pieces = 6, gridOut = "", centre = "";
    function curve(f, n, col) {   // a ground line in pieces, so it bends with the planet
      var s = "";
      for (var i = 0; i < n; i++) { var sg = seg(f(i / n), f((i + 1) / n)); if (sg) s += line(sg, col); }
      return s;
    }
    for (var x = -cw; x <= cw + 1; x += gsz) {
      var lx = x;
      var s1 = curve(function (t) { return gp(a0 + (a1 - a0) * t, lx); }, pieces, Math.abs(x) < 1 ? C.rule2 : C.rule);
      if (Math.abs(x) < 1) centre = s1; else gridOut += s1;
    }
    for (var y = a0; y <= a1 + 1; y += gsz) { var ly = y; gridOut += curve(function (t) { return gp(ly, -cw + 2 * cw * t); }, pieces, C.rule); }
    out.push(gridOut, centre);
    if (dep([0, 0, 0]) > near) {
      var d = prj([0, 0, 0]);
      out.push(poly([[d[0], d[1] - 3], [d[0] + 3, d[1]], [d[0], d[1] + 3], [d[0] - 3, d[1]]], C.bg, C.hi));
      if (g.ok) out.push(txt(d[0] + 6, d[1] + 6, dist(Math.hypot(Pc[0], Pc[1], Pc[2])), C.hi, "start", true));
    }
    var sShip = dot3(Pc, u), gates = [];
    for (var n = Math.floor((sShip - 0.35 * sp) / sp); n >= 1 && gates.length < 7; n--) {
      var sg2 = n * sp, c = [u[0] * sg2, u[1] * sg2, u[2] * sg2], hw = Math.max(30, sg2 * Math.tan(LAT * RAD)), hh = hw * 0.72;
      var cs = [[1, 1], [1, -1], [-1, -1], [-1, 1]].map(function (m) {
        return [c[0] + rt[0] * hw * m[0] + uc[0] * hh * m[1], c[1] + rt[1] * hw * m[0] + uc[1] * hh * m[1], c[2] + rt[2] * hw * m[0] + uc[2] * hh * m[1]];
      });
      if (cs.some(function (q) { return dep(q) < near; })) continue;
      gates.push(cs.map(prj));
    }
    for (var gi = gates.length - 1; gi >= 0; gi--) out.push(line(gates[gi], gi ? C.text : C.hi, null, true, gi ? Math.max(0.35, 1 - gi * 0.12) : 1));
    T.gateTxt = dist(sp);   // how far apart the gates are
    var vh = g.ok ? Math.hypot(g.vE, g.vN, g.vU) : 0;
    if (vh > 1) {   // the flight-path marker: where you're actually heading
      var tq = [Pc[0] + g.vE / vh * 3000, Pc[1] + g.vN / vh * 3000, Pc[2] + g.vU / vh * 3000];
      if (dep(tq) > near) {
        var m = prj(tq), mx = clamp(m[0], 10, W - 10), my = clamp(m[1], 8, H - 8);
        out.push(circ(mx, my, 3, C.hi));
        out.push(line([[mx - 9, my], [mx - 3, my]], C.hi)); out.push(line([[mx + 3, my], [mx + 9, my]], C.hi)); out.push(line([[mx, my - 3], [mx, my - 7]], C.hi));
      }
    }
    return out.join("");
  }

  // right, under the readouts: your vertical velocity against the SHALLOW-STEEP window and OPT's requirement
  function vvSvg(W, H, g) {
    var w = g.vw || {};
    if (!g.ok || !g.entry || !(w.spd >= 1)) return line([[2, H / 2], [W - 2, H / 2]], C.rule2);
    var out = [], max = w.max;
    function X(v) { return 3 + clamp(v / max, 0, 1) * (W - 6); }
    var lo = w.lo, hi = w.hi, req = w.req, inWin = g.vv >= lo && g.vv <= hi;
    out.push(line([[3, H / 2], [W - 3, H / 2]], C.rule2));
    out.push(poly([[X(lo), 2], [X(hi), 2], [X(hi), H - 3], [X(lo), H - 3]], C.text, null, 0.14));
    out.push(line([[X(lo), 2], [X(hi), 2], [X(hi), H - 3], [X(lo), H - 3]], C.acc, [2, 1], true));
    out.push(bar([X(req), 0], [X(req), H - 1], C.text, 2));
    var nx = X(g.vv), col = inWin ? C.hi : C.bad;
    out.push(poly([[nx, H / 2 - 1], [nx - 3, 0], [nx + 3, 0]], col, col));
    out.push(poly([[nx, H / 2], [nx - 3, H - 1], [nx + 3, H - 1]], col, col));
    return out.join("");
  }

  // ---- the words: readouts, chips, the switches, the course box and the waiting box ----
  function cell(lab, v, col) {
    return '<div class="cell trc"><span class="lab">' + ED.esc(lab) + '</span><span class="v"' + (col ? ' style="color:' + col + '"' : "") + ">" +
      ED.esc(v) + "</span></div>";
  }
  function chip(el, text, col) {
    el.textContent = text;
    el.style.background = col || "";
    el.hidden = !text;
  }
  var PHASES = { cruise: "Orbital cruise", glide: "Glide", flight: "", final: "Final approach", landed: "Landed", wait: "" };
  function words(g) {
    var d = T.dest || {}, ok = g.ok, e1 = ok && g.entry, side = ok && g.de > 0 ? "R " : "L ";
    $("tr-dname").textContent = d.ok ? d.name : d.name || "";
    $("tr-dsub").textContent = d.ok ? (g.onPad ? "Pad " + g.padNum : d.pad ? "Pad " + d.pad.num + " granted" : "") : d.why || "";
    $("pg-traj").classList.toggle("trnodest", !d.ok);
    $("tr-wait").hidden = ok;
    $("tr-waitt").textContent = ok ? "" : g.title || "";
    $("tr-waits").textContent = ok ? "" : g.why || "";
    var me = (ok && g.me) || T.me || {}, st = ok ? PHASES[g.phase] || "" : "", stCol = "";
    if (ok && g.me && g.age > STALE && !me.landed) { st = "No reading for " + Math.round(g.age) + " s"; stCol = "var(--bad)"; }
    chip($("tr-state"), st, stCol);
    var hc = ok ? g.hac : null, ls = ok ? latState(g) : null, vs = ok ? (hc ? hacVert(g) : vertState(g)) : null;
    if (hc) ls = hacLat(g, ls);
    chip($("tr-lat"), ok ? ls.chip : "No guidance", ok ? ls.col : "var(--rule2)");
    chip($("tr-vert"), ok ? vs.chip : "No guidance", ok ? vs.col : "var(--rule2)");
    var set = d.ok && T.crs[d.key] != null, crs = set ? deg3(T.crs[d.key]) + "°" : d.ok ? "AUTO" : "---°";
    $("tr-crsv").textContent = crs;
    $("tr-crs").classList.toggle("auto", d.ok && !set);
    $("tr-ilscrs").textContent = "Crs " + crs.replace("°", "");
    if (T.stepTxt && performance.now() - T.stepAt > 900) T.stepTxt = "";
    $("tr-step").textContent = T.grab ? T.stepTxt : "";
    var dev = ok && !g.auto, w = ok ? g.vw : {}, mmss = function (sec) { return isFinite(sec) && sec < 36000 ? Math.floor(Math.round(sec) / 60) + ":" + String(Math.round(sec) % 60).padStart(2, "0") : "--:--"; };
    var hdgCells = [cell("Trk", ok && g.gs > 5 ? deg3(g.trk) + "°" : "-"), cell("Hdg", me.hdg != null ? deg3(me.hdg) + "°" : "-")];
    var sgn = function (v) { return (v >= 0 ? "+" : "-") + dist(v); };
    if (hc && hc.stage === "acq") $("tr-lgrid").innerHTML = [
      cell("WP1 brg", hc.w1 ? deg3(hc.b1) + "°" : "-"), cell("WP1 rng", hc.w1 ? dist(hc.d1) : "-"),
      cell("Turn", hc.psiT != null ? Math.round(hc.psiT / RAD) + "° " + (hc.side > 0 ? "R" : "L") : "-"),
      cell("HAC", (hc.side > 0 ? "R" : "L") + " · " + (hc.mode === "strt" ? "Strt-in" : "Ovhd"))].concat(hdgCells).join("");
    else if (hc && hc.stage === "hac") $("tr-lgrid").innerHTML = [
      cell("Turn rem", hc.psi != null ? Math.round(hc.psi / RAD) + "° " + (hc.side > 0 ? "R" : "L") : "-"), cell("HAC R", hc.rr != null ? dist(hc.rr) : "-"),
      cell("R err", hc.rerr != null ? (hc.rerr >= 0 ? "Out " : "In ") + dist(hc.rerr) : "-", hc.rerr != null && Math.abs(hc.rerr) > 300 ? "var(--accent)" : ""),
      cell("WP2 rng", hc.d2 != null ? dist(hc.d2) : "-")].concat(hdgCells).join("");
    else $("tr-lgrid").innerHTML = [
      cell("Brg", ok ? deg3(g.bSD) + "°" : "-"), cell("Rng", ok ? dist(g.dist) : "-"),
      cell("Dev", dev ? side + Math.abs(g.de).toFixed(1) + "°" : "-", dev ? ls.col : ""),
      cell("Xtk", dev ? side + dist(g.xtk) : "-", dev ? ls.col : "")].concat(hdgCells).join("");
    var req = ok ? w.req : 0, err = ok ? g.vv - req : 0;
    if (hc) $("tr-rgrid").innerHTML = [
      cell("Alt", dist(hc.Y)), cell("Ref alt", hc.ref != null ? dist(hc.ref) : "-"),
      cell("Alt err", hc.err != null ? sgn(hc.err) : "-", e1 && hc.err != null ? vs.col : ""), cell("Req VV", e1 && w.spd > 1 ? speed(req) + " ↓" : "-"),
      cell("Path", hc.L != null ? dist(hc.L) : "-"), cell("TTG", mmss(hc.L != null && g.gs > 1 ? hc.L / g.gs : NaN))
    ].join("");
    else $("tr-rgrid").innerHTML = [
      cell("Alt", ok ? dist(g.alt) : me.alt != null ? dist(me.alt) : "-"), cell("Rng", ok ? dist(g.dist) : "-"),
      cell("Angle", ok ? g.th.toFixed(1) + "°" : "-", e1 ? vs.col : ""), cell("Fpa", ok && g.gs > 5 ? g.fpa.toFixed(1) + "°" : "-"),
      cell("Alt err", e1 ? (g.altErr >= 0 ? "+" : "-") + dist(g.altErr) : "-", e1 ? vs.col : ""),
      cell("TTG", mmss(ok && g.clos > 1 ? g.dist / g.clos : NaN))
    ].join("");
    var moving = e1 && w.spd > 1;
    $("tr-gsn").textContent = moving ? Math.round(w.spd) : "--";
    $("tr-vvreq").textContent = moving ? speed(req) + " ↓" : "--";
    $("tr-vvnow").textContent = e1 ? speed(g.vv) + (g.vv >= 0 ? " ↓" : " ↑") : "--";
    $("tr-vverr").textContent = moving ? "err " + (err >= 0 ? "+" : "-") + Math.round(Math.abs(err)) : ok && !g.entry ? "from the glide" : "";
    $("tr-vverr").style.color = moving && Math.abs(err) > 0.1 * req ? "var(--accent)" : "";
    $("tr-vvwin").textContent = moving ? Math.round(w.lo) + "-" + Math.round(w.hi) + " m/s ↓" : "--";
    fixedWords(hc ? hc.slope : null);
    var loc = e1 && !g.auto;
    $("tr-loc").textContent = loc ? (Math.abs(g.de) < 0.05 ? "Centred" : (g.de > 0 ? "Fly L " : "Fly R ") + Math.abs(g.de).toFixed(1) + "°") : e1 ? "Course auto" : "Off";
    $("tr-loc").style.color = loc ? ls.col : e1 ? "var(--rule2)" : "var(--bad)";
    $("tr-gs").textContent = e1 ? (Math.abs(g.th - OPT) < 0.05 ? "Centred" : (g.th > OPT ? "Fly dn " : "Fly up ") + Math.abs(g.th - OPT).toFixed(1) + "°") : "Off";
    $("tr-gs").style.color = e1 ? vs.col : "var(--bad)";
    $("tr-gates").textContent = T.gateTxt || "";
    $("tr-scale").textContent = scaleTxt(g.scale);
    chip($("tr-zoom"), T.zoom ? "Manual" : "Auto", T.zoom ? "var(--accent)" : "var(--rule2)");
    marks();
  }
  function marks() {   // the switches' settings, the course box grabbed, COMM1's outline (page menu only)
    var ufc = (S.ufc || {}).menu === "PAGE";
    Array.prototype.forEach.call($("tr-view").querySelectorAll("button"), function (b) { b.classList.toggle("on", b.dataset.v === T.view); b.setAttribute("aria-pressed", String(b.dataset.v === T.view)); });
    Array.prototype.forEach.call($("tr-dest").querySelectorAll("button"), function (b) { b.classList.toggle("on", b.dataset.v === T.mode); b.setAttribute("aria-pressed", String(b.dataset.v === T.mode)); });
    Array.prototype.forEach.call($("pg-traj").querySelectorAll("[data-f]"), function (el) { el.classList.toggle("focus", ufc && !T.grab && el.dataset.f === T.focus); });
    $("tr-crs").classList.toggle("grab", T.grab);
    $("tr-crs").setAttribute("aria-pressed", String(T.grab));
    $("tr-entry1").classList.toggle("focus", ufc && T.focus2 === "entry");
    $("tr-circle").classList.toggle("focus", ufc && T.focus2 === "circle");
    $("tr-hac").classList.toggle("focus", ufc && T.focus2 === "hac");
    [["tr-entry1", "entry"], ["tr-circle", "circle"]].forEach(function (q) { var o = T.prof === q[1]; $(q[0]).classList.toggle("on", o); $(q[0]).setAttribute("aria-pressed", String(o)); });
    $("tr-hac").hidden = T.prof !== "circle";
    Array.prototype.forEach.call($("tr-hac").querySelectorAll("button"), function (b) { b.classList.toggle("on", b.dataset.v === T.hmode); b.setAttribute("aria-pressed", String(b.dataset.v === T.hmode)); });
    $("tr-reset").classList.toggle("focus", ufc && T.focus2 === "reset");
    $("tr-reset").classList.toggle("off", !T.zoom);
  }

  // ---- the frame: every picture, and (five times a second) the words ----
  function frame(force) {
    var now = performance.now();
    T.g = guide(now / 1000);
    var g = T.g;
    paint("tr-plan", function (W, H) { return planSvg(W, H, g); });
    if (SHOW_MID) {
      paint("tr-ils", function (W, H) { return ilsSvg(W, H, g); });
      paint("tr-hits", function (W, H) { return hitsSvg(W, H, g); });
    }
    paint("tr-prof", function (W, H) { return profSvg(W, H, g); });
    paint("tr-vv", function (W, H) { return vvSvg(W, H, g); });
    if (force || now - T.textAt > 200) { T.textAt = now; words(g); }
  }
  function loop(ts) {
    T.raf = 0;
    if (!ED.showing("nav", 3) || S.halted || ED.hyper.on()) return;
    if (ts - T.frameAt >= (ED.reduce.matches ? 250 : 33)) { T.frameAt = ts; frame(false); }
    T.raf = requestAnimationFrame(loop);
  }
  function start() { if (!T.raf && ED.showing("nav", 3)) T.raf = requestAnimationFrame(loop); }

  // ---- setting the course, the view and the destination: the UFC's COMM1 (the left knob), or the mouse ----
  // The course can be set whenever there's a destination, with or without a position.
  function courseKey() { return T.dest && T.dest.ok ? T.dest.key : null; }
  function courseNow() {   // the course as it stands: yours, else the bearing you have to it (else north)
    var k = courseKey();
    if (!k) return 0;
    if (T.crs[k] != null) return T.crs[k];
    var g = T.g;
    return g && g.ok ? g.crs : 0;
  }
  function setCourse(v) {
    var k = courseKey();
    if (!k) return;
    T.crs[k] = n360(Math.round(v)) % 360;
    delete T.took[k];   // yours now
    keep();
  }
  function turn(clicks) {   // the course box grabbed: each click turns the course - more a click the faster they come
    var k = courseKey();
    if (!k || !clicks) return;
    var now = performance.now(), dir = clicks > 0 ? 1 : -1, n = Math.abs(clicks);
    var gap = dir === T.lastDir ? (now - T.lastClick) / n : 1e9;
    if (n > 1) gap = Math.min(gap, 60);   // several in one go: they came faster than the board could pass them on
    T.lastClick = now; T.lastDir = dir;
    var step = gap < 70 ? 10 : gap < 130 ? 5 : gap < 220 ? 2 : 1;
    setCourse(courseNow() + dir * step * n);
    T.stepTxt = (dir > 0 ? "+" : "-") + step * n + "°";
    T.stepAt = now;
    if (ED.showing("nav", 3)) frame(true);
  }
  function grab(on) {
    T.grab = on == null ? !T.grab : on;
    T.focus = "crs";
    T.stepTxt = "";
    if (ED.showing("nav", 3)) frame(true);
  }
  function setView(v) { T.view = v; keep(); if (ED.showing("nav", 3)) frame(true); }
  function setProf(p) {   // the profile: ENTRY 1 or CIRCLE (armed afresh from where you are)
    if (p !== "entry" && p !== "circle") return;
    if (p !== T.prof) {
      T.prof = p; T.hac = null;
      if (p === "entry" && T.circleTook && T.took[T.circleTook]) { delete T.crs[T.circleTook]; delete T.took[T.circleTook]; }   // (the course CIRCLE took)
      T.circleTook = null;
      keep();
    }
    if (ED.showing("nav", 3)) frame(true);
  }
  function setHmode(m) {   // CIRCLE's HAC: overhead or straight in (armed afresh)
    if (m !== "ovhd" && m !== "strt") return;
    if (m !== T.hmode) { T.hmode = m; T.hac = null; keep(); }
    if (ED.showing("nav", 3)) frame(true);
  }
  function stops2() { return STOPS2.filter(function (x) { return x !== "hac" || T.prof === "circle"; }); }
  function setMode(m) {
    T.mode = m; keep();
    T.dest = resolve((S.data || {}).syst || {});
    if (ED.showing("nav", 3)) frame(true);
  }
  function knob1(clicks) {   // COMM1 turned: the course (grabbed), or the outline to the next stop
    if (T.grab) { turn(clicks); return; }
    var i = STOPS.indexOf(T.focus);
    T.focus = STOPS[clamp((i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), STOPS.length), 0, STOPS.length - 1)];
    marks();
  }
  function pull1() {   // a COMM1 pull: grab or let go of the course box, or flip a switch
    if (T.focus === "crs") grab();
    else if (T.focus === "view") setView(T.view === "N" ? "C" : "N");
    else setMode(T.mode === "pick" ? "hud" : "pick");
  }
  // ---- the scale: zoomed with the COMM1 VOLUME dial or the mouse wheel; Reset scale (COMM2's pull, or a click) ----
  function zoomBy(f) {   // f > 1: in. False at a limit
    var from = scaleNow(), to = clamp(from / f, ZOOM_MIN, ZOOM_MAX);
    if (Math.abs(to - from) <= from * 1e-6) return false;
    T.zoom = to; T.zoomKey = courseKey();
    return true;
  }
  function unzoom() { T.zoom = null; T.zoomKey = null; }
  function resetScale() { unzoom(); if (ED.showing("nav", 3)) frame(true); }
  [$("tr-plan").parentNode, $("tr-prof").parentNode].forEach(function (el) {
    el.addEventListener("wheel", function (e) {
      e.preventDefault();
      zoomBy(Math.pow(1.0015, -e.deltaY * (e.deltaMode === 1 ? 33 : 1)));   // a notch: about 1.16 times
    }, { passive: false });
  });
  $("tr-reset").addEventListener("click", resetScale);
  $("tr-entry1").addEventListener("click", function () { T.focus2 = "entry"; setProf("entry"); });
  $("tr-circle").addEventListener("click", function () { T.focus2 = "circle"; setProf("circle"); });
  $("tr-hac").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { T.focus2 = "hac"; setHmode(b.dataset.v); } });

  $("tr-crs").addEventListener("click", function () { grab(); });
  $("tr-crs").addEventListener("wheel", function (e) {   // the mouse wheel turns it, like the knob, while it's grabbed
    if (!T.grab) return;
    e.preventDefault();
    var now = performance.now();
    if (now - T.wheelAt > 300) T.wheelAcc = 0;
    T.wheelAt = now;
    T.wheelAcc += e.deltaY;
    if (Math.abs(T.wheelAcc) >= 40) { turn(T.wheelAcc < 0 ? 1 : -1); T.wheelAcc = 0; }
  }, { passive: false });
  $("tr-crsm").addEventListener("click", function () { if (courseKey()) { setCourse(courseNow() - 1); frame(true); } });
  $("tr-crsp").addEventListener("click", function () { if (courseKey()) { setCourse(courseNow() + 1); frame(true); } });
  $("tr-view").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { T.focus = "view"; T.grab = false; setView(b.dataset.v); } });
  $("tr-dest").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { T.focus = "dest"; T.grab = false; setMode(b.dataset.v); } });
  window.addEventListener("resize", function () { if (ED.showing("nav", 3)) frame(true); });

  $("tr-mid").hidden = !SHOW_MID;
  function fixedWords(slope) {   // the page's fixed words, from the profile's settings (CIRCLE: the slope you're on - HAC's, then the OGS's)
    var sig = T.prof + "|" + slope;
    if (sig === T.wordsSig) return;
    T.wordsSig = sig;
    var opt = degs(OPT), win = SHALLOW + "-" + degs(STEEP), lat = "±" + degs(LAT);
    $("tr-bound").textContent = "Bounds " + lat;
    $("tr-hits").setAttribute("aria-label", "Highway in the sky: gates down the " + opt + " path");
    if (T.prof === "circle") {
      var sl = slope != null ? slope : HAC.DESC;
      $("tr-optwin").textContent = "OGS " + degs(HAC.OGS) + " · HAC " + degs(HAC.DESC);
      $("tr-vvreqlab").textContent = "Req = GS x tan " + degs(sl);
      $("tr-tanopt").textContent = Math.tan(sl * RAD).toFixed(3);
      $("tr-vvwinlab").textContent = "Window " + Math.max(0, sl - HAC.WIN) + "-" + degs(sl + HAC.WIN);
      $("tr-plan").setAttribute("aria-label", "Top-down: the Heading Alignment Cone round to WP2, the outer glide slope in along the course, WP1 and you");
      $("tr-prof").setAttribute("aria-label", "Side profile along the path: the " + degs(HAC.OGS) + " outer glide slope up to WP2, the " + degs(HAC.DESC) + " descent round the HAC, and you");
      return;
    }
    $("tr-optwin").textContent = "Opt " + opt + " · " + win;
    $("tr-vvreqlab").textContent = "Req = GS x tan " + opt;
    $("tr-tanopt").textContent = TAN_OPT.toFixed(3);
    $("tr-vvwinlab").textContent = "Window " + win;
    $("tr-plan").setAttribute("aria-label", "Top-down: the course into the destination, its " + lat + " bounds, and you");
    $("tr-prof").setAttribute("aria-label", "Side profile: the " + opt + " path up from the destination, the " + degs(SHALLOW) + " and " + degs(STEEP) + " bounds, and you");
  }
  fixedWords(null);

  ED.traj = T;   // (its working state: for the tests; Wpt and Atk use its filter)
  ED.trajResolve = resolve;
  ED.trajFilter = { Nav: Nav, WRITE_DEG: WRITE_DEG, SLOW: SLOW, STILL: STILL, Q_LO: Q_LO, Q_HI: Q_HI, BLEND: BLEND };   // (Wpt's MARK; the tests)
  // its drawing and its sums, for Atk's pictures (the same coarse pixels and colours)
  ED.trajDraw = { C: C, line: line, poly: poly, circ: circ, txt: txt, bar: bar, shipMark: shipMark, note: note, paint: paint,
                  niceStep: niceStep, unit: unit, tickLab: tickLab, scaleTxt: scaleTxt, clamp: clamp, n360: n360, w180: w180,
                  deg3: deg3, dist: dist, speed: speed, arc: arc, RAD: RAD };
  ED.trajGuide = function () { return guide(performance.now() / 1000); };
  ED.trajHac = { HAC: HAC, geom: hacGeom, at: hacAt, psi: hacPsi, tangent: hacTangent, solve: hacSolve, len: hacLen, ref: hacRef };   // (the tests)
  ED.page({
    tab: "nav", sub: 3, key: 2, label: "Traj", el: "pg-traj", mode: "traj", back: "2 Nav · Traj",
    update: function (s) {   // every refresh, showing or not: the filter keeps up, the destination, the course at the glide
      var y = s.syst || {};
      ingest(y);
      T.dest = resolve(y);
      if (T.me && T.me.glide) takeCourse(T.dest, T.me);
      else if (T.me && T.me.sc) dropTaken();
      if (T.prof === "circle" && !ED.showing("nav", 3)) guide(performance.now() / 1000);   // (CIRCLE keeps up with where you are on it, the page showing or not)
      // your own scale goes with a new destination, or going back into orbital cruise (for the next approach)
      var key = courseKey(), sc = !!(T.me && T.me.sc);
      if (T.zoom && ((key && key !== T.zoomKey) || (sc && T.wasSc === false))) unzoom();
      if (T.me) T.wasSc = sc;
    },
    draw: function () { frame(true); start(); },
    enter: function () { T.focus = "crs"; T.focus2 = "entry"; start(); },
    leave: function () { T.grab = false; },
    cursor: function () { marks(); },
    knob1: knob1, pull1: pull1,   // COMM1 works the page ...
    scroll: function (clicks) {   // ... COMM2 steps across ENTRY 1, CIRCLE (and its OVHD / STRT-IN) and Reset scale ...
      var st = stops2(), i = st.indexOf(T.focus2);
      T.focus2 = st[clamp((i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), st.length), 0, st.length - 1)];
      marks();
    },
    pull: function () {   // ... and a pull picks the profile, flips OVHD / STRT-IN, or resets the scale
      if (T.focus2 === "reset") resetScale();
      else if (T.focus2 === "hac") setHmode(T.hmode === "ovhd" ? "strt" : "ovhd");
      else setProf(T.focus2 === "circle" ? "circle" : "entry");
    },
    dial: function (r, dt) {   // ... and the COMM1 VOLUME dial zooms (4 times a second at full turn), as on the schematic
      var cue = { z: "", t: "" };
      if (r.zoom && zoomBy(Math.exp(Math.log(4) * r.zoom * dt))) cue.z = r.zoom > 0 ? "Z+" : "Z-";
      return cue;
    }
  });
})();
