// ED Target Board page - 2 Nav › HSI: flying your flight plans, as an F/A-18C's HSI. The flight plan (SEQ 1-3, or Atk's
// ATK once built - or SEQ NONE, no plan) on a moving map of the body round you, the steer-to point (COMM2 steps it: the
// activated plan's points in order - only those; with NONE, all your waypoints then your marks - round again) and its name, its bearing, range and time to go at your ground
// speed, and the designated target (TGT). The HSI flies a plan as it is: plans are put in order on Wpt. With a TOT on
// the activated plan (Wpt: its TGT - boxed in the plan - TOT and GSPD, as the Hornet's): TIME ON TARGET - the TOT and the
// time now (Zulu), the ground speed you need now (to the IP, so you fly the IP > TGT leg at GSPD; on that leg, or with no
// GSPD, to the TGT) and how early or late you'd be at your ground speed now. The body's planetary facilities (1 Syst's
// settlements, ports, outposts...) are on the map too: each a TACAN symbol, with a light dashed ring 10 km round it. The
// scale: automatic (in round steps) or zoomed, in km or NM (KM / NM, kept). Bottom left of the map, under the rose: the
// timer (timer.js) - the T-6A's clock: ET / CD (its SEL: the stopwatch or the countdown), then the time (CTL: start, again
// reset; a countdown with no time set: type it - on the keypad, or clicked, the keyboard). AUTO sequencing steps the steer-to point on along the plan as you reach each point - or
// pass it close by. With no fix on the plan's body (in orbital cruise far off, docked...), the map shows the plan
// itself, north up, round its steer-to point. Your position and speeds: Traj's filter, carried on between the game's
// readings. Exobiology: sampling a species with the genetic sampler on the body you're on, the map's on that body (the
// plan's elsewhere: its chip says so), each sample you've taken is on it (S1-S3), ringed at its genus's colony range -
// amber while you're inside it, too close for the next - and the auto scale fits them while you're within EXO_NEAR;
// the panel gives the species, the samples, the range, how far you are from the nearest and how much further to GO (or
// CLEAR) - with no steer-to point, the scratchpad too: EX, the count, GO and the metres still to go - or CLEAR.
// The UFC (page menu): COMM2 turns the steer-to point and a pull designates it (WPDSG; DSG - Opt4 - too); COMM1 steps
// across SEQ, AUTO / MAN, TRK-UP / N-UP, RESET SCALE, KM / NM, then the timer's ET / CD and its time, and a pull flips or
// presses one (the time, a countdown with none set: the keypad types it, ENT sets it, CLR clears; ENT on the timer types a
// new one); the COMM1 VOLUME dial zooms. The scratchpad shows the steer-to point and its range (km) - with COMM1 on the
// timer, the timer; COM1 its place in the plan, COM2 the plan (A: ATK).
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, D = ED.trajDraw, N = ED.nav;
  var C = D.C, RAD = D.RAD, clamp = D.clamp;

  var CAPTURE_S = 3, CAPTURE_M = 400;   // AUTO: within this many seconds at your ground speed (or metres) of the steer-to point, on to the next ...
  var PASS_S = 8, PASS_M = 1500;        // ... or once it's behind you and this close (you flew past it)
  var AUTO_AGAIN = 3000;                // ms before AUTO asks again for the same point (the board may not have answered yet)
  var ZOOM_MIN = 300, ZOOM_MAX = 1e7;   // metres: the map's reach, from its middle to the rose
  var SITE_RING = 10000;                // metres: the dashed ring round each planetary facility
  var EXO_NEAR = 5000;                  // metres: this close to a sample of the species you're on, the auto scale fits its rings
  var SEQS = ["none", "1", "2", "3", "atk"], STOPS1 = ["seq", "auto", "view", "reset", "units", "tmode", "timer"];   // (COMM1's)
  var kept = (function () { try { return JSON.parse(localStorage.getItem("ft3000-hsi") || "{}") || {}; } catch (e) { return {}; } })();
  var H = { view: kept.view === "N" ? "N" : "T", units: kept.units === "nm" ? "nm" : "km", zoom: null, scale: 0, focus1: "seq", raf: 0, frameAt: 0,
            textAt: 0, told: "", autoFrom: null, autoAt: 0, note: "", noteAt: 0, g: null, drawn: null,
            tin: null, ktold: "", tsig: "" };   // (tin: the countdown's time being typed - {d: its digits (the UFC's keypad)} or {kbd: true})
  function keep() { try { localStorage.setItem("ft3000-hsi", JSON.stringify({ view: H.view, units: H.units })); } catch (e) { /* storage blocked */ } }
  function low(s) { return String(s || "").toLowerCase(); }
  function on() { return ED.showing("nav", 5); }
  function say(t) { H.note = t; H.noteAt = Date.now(); }

  // ---- the exobiology: the species you're sampling (the board's, from the game's ScanOrganic) ----
  function exo() { var x = ((S.data || {}).exo || {}).cur; return x && x.body && x.samples ? x : null; }
  function exoLast() { var x = ((S.data || {}).exo || {}).last; return x && x.species ? x : null; }

  // ---- the sums ----
  function solve() {
    var nv = N.data(), seq = nv.seq || "none", keys = seq === "none" ? [] : N.seqKeys(seq), pts = N.points(), st = N.point(nv.steer), tg = N.tgt();
    var first = keys.length ? pts[keys[0]] : null, body = st ? st.body : first ? first.body : tg ? tg.body : null;
    // (sampling a species on the body you're on: the map's on it, whatever body the plan's on)
    var f = N.fix(), ex = exo(), exoOn = !!(ex && f && low(ex.body) === low(f.body)), away = null;
    if (exoOn && (!body || low(body) !== low(f.body))) { away = body; body = f.body; }
    // (keys: the activated plan's points - its legs, AUTO; list: the points listed and stepped through - with SEQ NONE, all of them)
    var g = { seq: seq, keys: keys, list: seq === "none" ? N.allKeys() : keys, st: st, tg: tg, body: body, away: away, fix: null, pts: pts, nv: nv };
    if (f && body && low(f.body) === low(body)) g.fix = f;
    g.R = g.fix ? g.fix.R : body ? N.radius(body) : null;
    var c = g.fix || st || first || tg;
    g.c = c ? { lat: c.lat, lon: c.lon } : null;
    g.idx = st ? keys.indexOf(st.key) : -1;
    var me = N.y().me, stOn = !!(st && body && low(st.body) === low(body));
    if (away) { g.title = "Plan on " + away; g.why = ""; }
    else if (!st && seq === "none") { if (!exoOn) { g.title = "No steer-to point"; g.why = g.list.length ? "SEQ None: COMM2 steps through your waypoints and marks" : "No waypoints or marks in this system"; } }
    else if (!st && !keys.length) { if (!exoOn) { g.title = "No flight plan"; g.why = "Activate a plan (Wpt › SEQ, or Atk's BUILD) - or SEQ None"; } }
    else if (!me || me.lat == null) { g.title = "No state vector"; g.why = "No planetary surface fix - the plan, round its steer-to point"; }
    else if (f && body && low(f.body) !== low(body)) { g.title = "Reference body mismatch"; g.why = "The plan is on " + body; }
    else if (!f) { g.title = "Acquiring state vector"; g.why = ""; }
    if (!g.R || !g.c) return g;
    if (exoOn && g.fix) {   // how far you are from each sample (a new one must be clear of them all by the colony range)
      g.exo = { x: ex, d: ex.samples.map(function (q) { return D.arc(f.lat, f.lon, q.lat, q.lon, g.R).d; }) };
      g.exo.near = g.exo.d.length ? Math.min.apply(null, g.exo.d) : null;
    }
    if (g.fix && stOn) {
      var a = D.arc(f.lat, f.lon, st.lat, st.lon, g.R);
      g.brg = a.ab; g.dist = a.d; g.gs = f.gs; g.trk = f.trk;
      g.ttg = f.gs > 5 ? a.d / f.gs : null;
      g.rel = f.trk != null ? D.w180(a.ab - f.trk) : null;
    }
    if (g.fix && tg && low(tg.body) === low(g.fix.body)) {
      var b = D.arc(f.lat, f.lon, tg.lat, tg.lon, g.R);
      g.tbrg = b.ab; g.tdist = b.d;
    }
    return g;
  }
  function at(g, lat, lon) {   // a point, metres east and north of the map's middle
    var a = D.arc(g.c.lat, g.c.lon, lat, lon, g.R);
    return [a.d * Math.sin(a.ab * RAD), a.d * Math.cos(a.ab * RAD)];
  }

  // ---- the scale: auto (the steer-to point in view, in round steps of km or NM) or yours ----
  function niceUp(x) { var e = Math.pow(10, Math.floor(Math.log10(x))), f = x / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e; }
  function niceIn(m) { var u = H.units === "nm" ? 1852 : 1; return niceUp(m / u) * u; }   // (metres: 1, 2, 5... km - or NM)
  function autoScale(g) {
    var far = 0, e = g.exo, atExo = !!(e && e.near != null && e.near < EXO_NEAR);
    if (atExo !== !!H.atExo) { H.atExo = atExo; H.scale = 0; }   // (at the samples, or leaving them: the scale fits afresh)
    if (atExo) far = (Math.max.apply(null, e.d) + (e.x.range || 100)) * 1.1;   // (at the samples: them, rings and all)
    else if (g.fix && g.dist != null) far = g.dist * 1.15;
    else if (g.R && g.c) g.keys.forEach(function (k) { var p = g.pts[k]; if (p) { var v = at(g, p.lat, p.lon); far = Math.max(far, Math.hypot(v[0], v[1]) * 1.1); } });
    if (!far) return H.scale || (H.scale = niceIn(5000));
    var need = clamp(niceIn(Math.max(far, 500)), ZOOM_MIN, ZOOM_MAX);
    if (!H.scale || need > H.scale || need < H.scale / (atExo ? 2 : 3)) H.scale = need;   // (steps out at once, back in only well inside)
    return H.scale;
  }
  function scaleNow(g) { return H.zoom || autoScale(g); }
  function zoomBy(f) {
    var from = H.zoom || H.scale || niceIn(5000), to = clamp(from / f, ZOOM_MIN, ZOOM_MAX);
    if (Math.abs(to - from) <= from * 1e-6) return false;
    H.zoom = to;
    return true;
  }
  function resetScale() { H.zoom = null; if (on()) frame(true); }
  function setUnits(u) {   // the scale in km or NM (the automatic one in round steps of each)
    if (u !== "nm" && u !== "km") return;
    if (u !== H.units) { H.units = u; H.scale = 0; keep(); }
    if (on()) frame(true);
  }
  function scaleLab(m) {   // a distance on the scale: m / km, or NM
    if (H.units !== "nm") return D.scaleTxt(m);
    var n = m / 1852;
    return (n >= 10 ? Math.round(n).toLocaleString("en-GB") : String(n >= 1 ? Math.round(n * 10) / 10 : Math.round(n * 100) / 100)) + " NM";
  }

  // ---- the planetary facilities: 1 Syst's settlements, ports, outposts... on the map's body (with a position) ----
  function sites(g) {
    return (N.y().entries || []).filter(function (e) {
      var p = e.pic || {};
      return e.kind === "station" && p.kind === "surface" && p.lat != null && p.lon != null && low(p.body || e.body) === low(g.body);
    });
  }
  function tacan(x, y, r) {   // the Hornet's TACAN symbol: a hexagon (flat top and bottom) with three ears - up left, up right, down
    var d = r * 1.25, pts = [];
    function v(b, out) {
      var a = b * RAD, o = out == null ? 0 : out * RAD, k = out == null ? 0 : d;
      return [x + Math.sin(a) * r + Math.sin(o) * k, y - Math.cos(a) * r - Math.cos(o) * k];
    }
    [[30, 90, 60], [90], [150, 210, 180], [210], [270, 330, 300], [330]].forEach(function (s) {
      if (s.length === 1) pts.push(v(s[0]));
      else pts.push(v(s[0]), v(s[0], s[2]), v(s[1], s[2]));
    });
    return pts;
  }

  // ---- the map: you in the middle, the compass rose round you, the plan, the target ----
  function mapSvg(W, Hh, g) {
    var out = [], cx = W / 2, cy = Hh / 2, rad = Math.max(20, Math.min(W, Hh) / 2 - 14), span = scaleNow(g), k = rad / span;
    var up = H.view === "T" && g.fix && g.fix.trk != null ? g.fix.trk : 0;   // the heading at the top
    function P(e, n) { var x = e * Math.cos(up * RAD) - n * Math.sin(up * RAD), y = e * Math.sin(up * RAD) + n * Math.cos(up * RAD); return [cx + x * k, cy - y * k]; }
    function onRose(brg, r) { var a = (brg - up) * RAD; return [cx + Math.sin(a) * r, cy - Math.cos(a) * r]; }
    function inside(p) { return Math.hypot(p[0] - cx, p[1] - cy) <= rad - 2; }
    function edge(p) { var dx = p[0] - cx, dy = p[1] - cy, l = Math.hypot(dx, dy) || 1; return [cx + dx / l * (rad - 3), cy + dy / l * (rad - 3)]; }
    function clip(a, b) {   // the part of the line a-b inside the rose (or null)
      var r = rad - 2, dx = b[0] - a[0], dy = b[1] - a[1], fx = a[0] - cx, fy = a[1] - cy;
      var A2 = dx * dx + dy * dy, B = 2 * (fx * dx + fy * dy), Cc = fx * fx + fy * fy - r * r, disc = B * B - 4 * A2 * Cc;
      if (A2 < 1e-9 || disc <= 0) return null;
      var sq = Math.sqrt(disc), t0 = Math.max(0, (-B - sq) / (2 * A2)), t1 = Math.min(1, (-B + sq) / (2 * A2));
      return t1 > t0 ? [[a[0] + dx * t0, a[1] + dy * t0], [a[0] + dx * t1, a[1] + dy * t1]] : null;
    }
    // the rose: ticks every 10 degrees, numbers every 30 (N E S W at the quarters), and the half-scale ring
    out.push(D.circ(cx, cy, rad, C.rule2));
    out.push(D.circ(cx, cy, rad / 2, C.rule, null, [1, 2]));
    out.push(D.txt(cx + rad / 2 * 0.71 + 2, cy + rad / 2 * 0.71 + 2, scaleLab(span / 2), C.muted, "start", true));
    for (var d = 0; d < 360; d += 10) {
      var long = d % 30 === 0, p1 = onRose(d, rad), p2 = onRose(d, rad - (long ? 6 : 3));
      out.push(D.line([p1, p2], long ? C.text : C.rule2));
      if (long) {
        var lp = onRose(d, rad - 12), lab = { 0: "N", 90: "E", 180: "S", 270: "W" }[d] || String(d / 10);
        out.push(D.txt(lp[0], lp[1], lab, d % 90 === 0 ? C.hi : C.muted));
      }
    }
    if (!g.R || !g.c) { out.push(D.note(W, Hh, g.title || "Nothing to show", C.muted)); return out.join(""); }
    var col = function (key) { return key === (g.st || {}).key ? C.hi : C.text; };
    // the body's planetary facilities: each a TACAN symbol, with a light dashed ring 10 km round it (the part in the rose)
    function ring(p, rr) {   // the points of a circle round p (rr pixels) inside the rose - one run (or none)
      var R0 = rad - 2, dx = cx - p[0], dy = cy - p[1], dc = Math.hypot(dx, dy), a0 = 0, a1 = 2 * Math.PI;
      if (dc >= rr + R0 || dc + R0 <= rr) return [];   // all outside the rose - or the rose all inside it
      if (dc + rr > R0) {   // crossing the rose: the arc on its inside, either side of the way to the middle
        var th = Math.atan2(dy, dx), al = Math.acos(clamp((dc * dc + rr * rr - R0 * R0) / (2 * dc * rr), -1, 1));
        a0 = th - al; a1 = th + al;
      }
      var step = 2 * Math.acos(Math.max(-1, 1 - 0.25 / rr)), n = clamp(Math.ceil((a1 - a0) / Math.max(step, 1e-3)), 12, 720), pts = [];
      for (var i = 0; i <= n; i++) { var a = a0 + (a1 - a0) * i / n; pts.push([p[0] + Math.cos(a) * rr, p[1] + Math.sin(a) * rr]); }
      return pts;
    }
    var fac = sites(g).map(function (e) { var v = at(g, e.pic.lat, e.pic.lon); return { key: e.key, p: P(v[0], v[1]) }; }), rr = SITE_RING * k;
    H.drawn = { sites: 0, rings: 0, units: H.units, span: span };
    if (rr >= 7) fac.forEach(function (x) {   // (too small to tell from the symbol: no ring)
      var pts = ring(x.p, rr);
      if (pts.length > 1) { out.push(D.line(pts, C.muted, [2, 3], false, 0.6)); H.drawn.rings++; }
    });
    fac.forEach(function (x) {
      if (!inside(x.p)) return;
      out.push(D.poly(tacan(x.p[0], x.p[1], 2.5), null, C.text));
      H.drawn.sites++;
    });
    // the species you're sampling: each sample taken, ringed at its colony range (amber: you're inside it - too close for the next)
    H.drawn.exo = 0; H.drawn.exoRings = 0;
    if (g.exo) {
      var ex = g.exo.x, er = (ex.range || 0) * k;
      ex.samples.forEach(function (q, i) {
        var v = at(g, q.lat, q.lon), p = P(v[0], v[1]), close = ex.range && g.exo.d[i] < ex.range;
        if (er >= 3) {
          var pts = ring(p, er);
          if (pts.length > 1) { out.push(D.line(pts, close ? C.acc : C.text, close ? null : [4, 2], false, 0.9)); H.drawn.exoRings++; }
        }
        if (!inside(p)) return;
        out.push(D.line([[p[0] - 3, p[1] - 3], [p[0] + 3, p[1] + 3]], close ? C.acc : C.hi));
        out.push(D.line([[p[0] - 3, p[1] + 3], [p[0] + 3, p[1] - 3]], close ? C.acc : C.hi));
        out.push(D.txt(p[0] + 6, p[1] - 6, "S" + (q.n || i + 1), close ? C.acc : C.hi, "start", true));
        H.drawn.exo++;
      });
    }
    // the body's other waypoints and the marks
    N.tgts().forEach(function (t) {
      if (g.keys.indexOf(t.key) >= 0 || low(t.body) !== low(g.body)) return;
      var v = at(g, t.lat, t.lon), p = P(v[0], v[1]);
      if (!inside(p)) return;
      out.push(D.circ(p[0], p[1], 1.5, C.muted, C.muted));
      out.push(D.txt(p[0] + 4, p[1], String(t.num), t.key === (g.st || {}).key ? C.hi : C.muted, "start"));
    });
    ((g.nv.marks) || []).forEach(function (m) {
      if (low(m.body) !== low(g.body)) return;
      var v = at(g, m.lat, m.lon), p = P(v[0], v[1]);
      if (!inside(p)) return;
      out.push(D.poly([[p[0] - 2, p[1] - 2], [p[0] + 2, p[1] - 2], [p[0] + 2, p[1] + 2], [p[0] - 2, p[1] + 2]], null, m.key === (g.st || {}).key ? C.hi : C.acc));
      out.push(D.txt(p[0] + 5, p[1], m.name, m.key === (g.st || {}).key ? C.hi : C.acc, "start"));
    });
    // the plan: its legs and points (ATK: the other role's track dashed too)
    function track(keys, dim) {
      var ps = keys.map(function (key) { var q = g.pts[key]; if (!q || low(q.body) !== low(g.body)) return null; var v = at(g, q.lat, q.lon); return { key: key, q: q, p: P(v[0], v[1]) }; })
        .filter(function (x) { return x; });
      for (var i = 1; i < ps.length; i++) {
        var seg = clip(ps[i - 1].p, ps[i].p);
        if (seg) out.push(D.line(seg, dim ? C.muted : C.text, dim ? [2, 2] : null, false, dim ? 0.7 : 1));
      }
      ps.forEach(function (x) {
        if (!inside(x.p)) return;
        var me = !dim && x.key === (g.st || {}).key;
        out.push(D.circ(x.p[0], x.p[1], me ? 4 : 2.5, dim ? C.muted : col(x.key), me ? C.hi : null));
        if (!dim || x.q.label === "IN") out.push(D.txt(x.p[0] + 6, x.p[1] - 6, x.q.label, dim ? C.muted : col(x.key), "start", true));
      });
    }
    if (g.seq === "atk" && g.nv.built) {
      var mine = String((g.nv.plan || {}).role || 1), other = mine === "1" ? "2" : "1";
      track((g.nv.built.roles[other] || []).map(function (p) { return "atk:" + other + ":" + p.id; }), true);
    }
    track(g.keys, false);
    // the target: a red diamond (at the rose's edge when it's further out)
    if (g.tg && low(g.tg.body) === low(g.body)) {
      var tv = at(g, g.tg.lat, g.tg.lon), tp = P(tv[0], tv[1]), tin = inside(tp);
      if (!tin) tp = edge(tp);
      out.push(D.poly([[tp[0], tp[1] - 5], [tp[0] + 5, tp[1]], [tp[0], tp[1] + 5], [tp[0] - 5, tp[1]]], null, C.bad));
      if (!tin) out.push(D.txt(tp[0], tp[1] + 10, "TGT", C.bad));
    }
    // the steer-to point: the line to it and its pointer on the rose (or, off the map, at the rose's edge)
    if (g.st && low(g.st.body) === low(g.body)) {
      var sv = at(g, g.st.lat, g.st.lon), sp = P(sv[0], sv[1]), sin = inside(sp);
      if (g.fix) {
        out.push(D.line([[cx, cy], sin ? sp : edge(sp)], C.hi, [3, 2]));
        var b = g.brg, tip = onRose(b, rad + 1), l1 = onRose(b - 4, rad + 9), l2 = onRose(b + 4, rad + 9);
        out.push(D.poly([tip, l1, l2], C.hi, C.hi));
      }
      if (!sin) { var ep = edge(sp); out.push(D.circ(ep[0], ep[1], 4, C.hi)); out.push(D.txt(ep[0], ep[1] + 10, g.st.label, C.hi, "middle", true)); }
    }
    // you
    if (g.fix) {
      var hd = g.fix.trk != null ? (g.fix.trk - up) * RAD : 0;
      out.push(D.shipMark([cx, cy], [Math.sin(hd), -Math.cos(hd)], 4, C.hi));
    } else out.push(D.txt(cx, cy + rad / 2 + 10, "Plan view · no fix", C.muted));
    return out.join("");
  }

  // ---- the words ----
  function cell(lab, v, col) {
    return '<div class="cell trc"><span class="lab">' + ED.esc(lab) + '</span><span class="v"' + (col ? ' style="color:' + col + '"' : "") + ">" + ED.esc(v) + "</span></div>";
  }
  function cell2(lab, a, b) {   // across the panel: metres, and a pilot's units
    return '<div class="cell trc split wide"><span class="lab">' + ED.esc(lab) + '</span><span class="v">' + ED.esc(a) + '</span><span class="v v2">' + ED.esc(b) + "</span></div>";
  }
  function nm(m) { var n = Math.abs(m) / 1852; return (n < 10 ? n.toFixed(2) : n < 100 ? n.toFixed(1) : Math.round(n).toLocaleString("en-GB")) + " NM"; }
  function kts(v) { return Math.round(Math.abs(v) * 3600 / 1852).toLocaleString("en-GB") + " kts"; }
  function mmss(s) { if (s == null || !isFinite(s)) return "--"; s = Math.round(s); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
  function words(g) {
    var st = g.st, f = g.fix;
    $("hs-sname").textContent = st ? st.label + (st.name && st.name !== st.label ? " · " + st.name : "") : "No steer-to point";
    $("hs-ssub").textContent = N.seqName(g.seq) + (g.idx >= 0 ? " · " + (g.idx + 1) + " of " + g.keys.length : st && g.seq !== "none" ? " · off the plan" : "");
    $("hs-state").hidden = true;
    $("hs-wait").hidden = !g.title || !!(g.R && g.c);
    $("hs-fix").textContent = g.title || "";
    $("hs-fix").hidden = !g.title || !(g.R && g.c);
    $("hs-waitt").textContent = g.title || "";
    $("hs-waits").textContent = g.why || "";
    $("hs-sto").textContent = st ? st.label : "--";
    $("hs-stn").textContent = st ? (st.name && st.name !== st.label ? st.name : st.label) : "No steer-to point";
    var alt = f ? D.dist(Math.max(0, f.alt)) : "-", plan = st && st.alt != null;
    $("hs-grid").innerHTML = [
      cell("Brg", g.brg != null ? D.deg3(g.brg) + "°" : "-"), cell("TTG", mmss(g.ttg)),
      cell2("Rng", g.dist != null ? D.dist(g.dist) : "-", g.dist != null ? nm(g.dist) : "-"),
      cell2("GS", f ? D.speed(f.gs) : "-", f ? kts(f.gs) : "-"),
      cell("Trk", f && f.trk != null && f.gs > 5 ? D.deg3(f.trk) + "°" : "-"),
      cell("Alt", alt + (plan ? " · plan " + D.dist(st.alt) : ""), plan && f && Math.abs(f.alt - st.alt) > Math.max(50, st.alt * 0.25) ? "var(--accent)" : "")
    ].join("");
    var leg = st && st.src === "atk" && g.idx > 0 ? g.pts[g.keys[g.idx - 1]] : null;
    var call = st && st.call ? st.call : "", legTxt = leg && leg.pt && leg.pt.secs != null ? "Leg in " + D.deg3(leg.pt.hdg) + "° · " + Math.round(leg.pt.secs) + " s" : "";
    $("hs-call").innerHTML = (call ? '<span class="lab">Call</span> <span class="hscv">' + ED.esc(call) + "</span>" : "") + (legTxt ? ' <span class="lab">' + ED.esc(legTxt) + "</span>" : "");
    $("hs-call").hidden = !call && !legTxt;
    // time on target (the activated plan's TOT): the ground speed you need now, and how early or late you'd be at yours
    var tc = totCalc(g);
    $("hs-totlab").hidden = $("hs-totgrid").hidden = !tc;
    if (tc) {
      var off = tc.late, ontime = off != null && Math.abs(off) < 5;
      $("hs-totgrid").innerHTML = [
        cell("TOT", zulu(tc.tot)), cell("Now", zulu(tc.now)),
        cell("TGT", tc.tgt.label + (tc.ip ? " · IP " + tc.ip.label : "")), cell("GSPD", tc.gspd != null ? tc.gspd + " kts" : "-"),
        cell2("Req GS" + (tc.to ? " · to " + tc.to : ""), tc.req != null ? D.speed(tc.req) : tc.why || "-", tc.req != null ? kts(tc.req) : "-"),
        cell("At GS", off == null ? "-" : ontime ? "On time" : mmss(Math.abs(off)) + (off > 0 ? " late" : " early"),
             off == null || ontime ? "" : "var(--accent)")
      ].join("");
    }
    exoWords(g);
    var tg = g.tg;
    $("hs-tgrid").innerHTML = tg ? [cell("Tgt", (tg.label || tg.name || "TGT").toUpperCase(), "var(--bad)"), cell("Brg", g.tbrg != null ? D.deg3(g.tbrg) + "°" : "-"),
      cell2("Rng", g.tdist != null ? D.dist(g.tdist) : "-", g.tdist != null ? nm(g.tdist) : "-")].join("") : cell("Tgt", "None - DSG designates");
    var ptgt = g.seq !== "none" && g.seq !== "atk" ? (((g.nv.tots || {})[g.seq]) || {}).tgt : null;   // (the plan's TGT: boxed)
    var csig = JSON.stringify([g.seq, g.list.map(function (k) { var p = g.pts[k] || {}; return [k, p.label, p.name, p.alt]; }), st && st.key, tg && tg.key, ptgt]);
    if (csig !== H.chainSig) {
      H.chainSig = csig;
      $("hs-chainlab").textContent = g.seq === "none" ? "All waypoints and marks" : "Flight plan";
      $("hs-chain").innerHTML = g.list.length ? g.list.map(function (k, i) {
        var p = g.pts[k] || {};
        return '<button type="button" class="srow' + (st && k === st.key ? " sel" : "") + '" data-key="' + ED.esc(k) + '"><span class="nm">' + (i + 1) + ". " +
          '<span class="' + (k === ptgt ? "tgbox" : "") + (tg && (tg.key === k || tg.key === k + "o") ? " tgdsg" : "") + '">' + ED.esc(p.label || "?") + "</span>" + (p.name && p.name !== p.label ? " " + ED.esc(p.name) : "") +
          '</span><span class="rt">' + (p.alt != null ? D.dist(p.alt) : "") + "</span></button>";
      }).join("") : '<div class="tgnil">Empty</div>';
    }
    $("hs-scale").textContent = scaleLab(scaleNow(g));
    var z = $("hs-zoom");
    z.textContent = H.zoom ? "Manual" : "Auto";
    z.style.background = H.zoom ? "var(--accent)" : "var(--rule2)";
    if (H.note && Date.now() - H.noteAt > 6000) H.note = "";
    $("hs-note").textContent = H.note;
    timerWords();
    marks(g);
    scratch(g);
    tellKeys();
  }
  function exoWords(g) {   // the species you're sampling: its samples, colony range, and how far you are from the nearest
    var ex = exo(), last = exoLast(), me = N.y().me || {}, rows = [];
    var lastHere = !ex && last && me.body && low(last.body) === low(me.body);
    if (ex) {
      var e = g.exo, need = ex.need || 3, n = ex.n || ex.samples.length, rng = ex.range, near = e ? e.near : null;
      var close = near != null && rng && near < rng, go;   // (Go: how much further before the next - or CLEAR)
      if (n >= need) go = "Analysing";   // (the game says it's done once the sampler's finished)
      else if (near == null) go = "-";
      else if (!rng) go = "Range ?";
      else go = close ? D.dist(rng - near) : "Clear";
      rows.push('<div class="cell trc wide"><span class="lab">Species</span><span class="v">' + ED.esc(ex.species) + "</span></div>",
        cell("Samples", n + " of " + need), cell("Range", rng ? D.dist(rng) : "?"));
      if (e) rows.push(cell("Nearest", near != null ? D.dist(near) : "-", close ? "var(--accent)" : ""), cell("Go", go, close ? "var(--accent)" : ""));
      else rows.push('<div class="cell trc wide"><span class="lab">On</span><span class="v">' + ED.esc(ex.body) + "</span></div>");
    } else if (lastHere) rows.push('<div class="cell trc wide"><span class="lab">Analysed</span><span class="v">' + ED.esc(last.species) + "</span></div>");
    var show = !!(ex || lastHere), sig = rows.join("");
    $("hs-exolab").hidden = $("hs-exogrid").hidden = !show;
    if (sig !== H.exoSig) { H.exoSig = sig; $("hs-exogrid").innerHTML = sig; }
  }
  function marks(g) {
    var ufc = (S.ufc || {}).menu === "PAGE", nv = (g || {}).nv || N.data(), built = !!nv.built;
    Array.prototype.forEach.call($("hs-seq").querySelectorAll("button"), function (b) {
      var o = b.dataset.v === (nv.seq || "none");
      b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o));
      if (b.dataset.v === "atk") b.disabled = !built;
    });
    Array.prototype.forEach.call($("hs-auto").querySelectorAll("button"), function (b) {
      var o = (b.dataset.v === "auto") === (nv.auto !== false);
      b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o));
    });
    Array.prototype.forEach.call($("hs-view").querySelectorAll("button"), function (b) {
      var o = b.dataset.v === H.view;
      b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o));
    });
    Array.prototype.forEach.call($("hs-units").querySelectorAll("button"), function (b) {
      var o = b.dataset.v === H.units;
      b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o));
    });
    Array.prototype.forEach.call($("pg-hsi").querySelectorAll("[data-f]"), function (el) { el.classList.toggle("focus", ufc && el.dataset.f === H.focus1); });
    $("hs-sto").classList.toggle("focus", ufc);   // (COMM2 turns it)
    $("hs-reset").classList.toggle("off", !H.zoom);
  }
  // ---- the timer (timer.js): ET / CD and the time, bottom left of the map ----
  function timerWords() {
    var o = ED.timer.read(), ufcIn = H.tin && !H.tin.kbd, kbd = !!(H.tin && H.tin.kbd);
    var txt = ufcIn ? ED.timer.typed(H.tin.d) : (o.up ? "+" : "") + ED.timer.fmt(o.secs);
    var cls = "hstd" + (ufcIn ? " typing" : o.alarm ? " alarm" : o.up ? " up" : o.run ? " run" : o.mode === "cd" && o.set ? " set" : "");
    var sig = [o.mode, txt, cls, kbd].join("|");
    if (sig === H.tsig) return;
    H.tsig = sig;
    $("hs-tmode").textContent = o.mode === "cd" ? "CD" : "ET";
    $("hs-tmode").setAttribute("aria-label", o.mode === "cd" ? "Countdown (SEL)" : "Stopwatch (SEL)");
    var dig = $("hs-tdig");
    dig.textContent = txt;
    dig.className = cls + (dig.classList.contains("focus") ? " focus" : "");
    dig.hidden = kbd;
    $("hs-tin").hidden = !kbd;
  }
  function timerScratch() {   // the scratchpad with COMM1 on the timer: ET / CD, the time (UP: a countdown past zero)
    var o = ED.timer.read();
    return { s1: o.mode === "cd" ? "CD" : "ET", s2: o.up ? "UP" : "", num: ED.timer.fmt(o.secs) };
  }
  function timerSel() {   // SEL: the stopwatch or the countdown (not while it runs - a countdown past zero: its alarm seen)
    if (H.tin) closeEntry();
    ED.timer.post({ op: "sel" }, function (j) {
      if (j.ok === false && j.why === "running") say("Timer running: CTL (the time) resets it first");
      redraw();
    });
  }
  function timerCtl() {   // CTL: start it - and again, reset it; a countdown with no time set: type its time
    var o = ED.timer.read();
    if (H.tin && !H.tin.kbd) { entryEnt(); return; }   // (typing it: a pull sets it, as ENT)
    if (o.mode === "cd" && !o.set && !o.run) { openEntry(false); return; }
    ED.timer.post({ op: "ctl" }, function (j) {
      if (j.ok === false && j.why === "set") openEntry(false);
      redraw();
    });
  }
  function openEntry(kbd) {   // the countdown's time: typed on the keypad (the scratchpad shows it) - or the keyboard
    if (kbd) {
      H.tin = { kbd: true };
      timerWords();
      var box = $("hs-tin"), o = ED.timer.read();
      box.value = o.mode === "cd" && o.set ? ED.timer.fmt(o.secs) : "";
      box.focus();
      box.select();
    } else H.tin = { d: "" };
    redraw();
  }
  function closeEntry() { H.tin = null; redraw(); }
  function entryEnt() {   // ENT (or a pull, or Enter): the countdown set to what's typed
    var text = H.tin ? (H.tin.kbd ? $("hs-tin").value : H.tin.d) : "", v = ED.timer.parse(text);
    if (v == null) { say("Countdown: HH:MM:SS (1 s to 99:59:59)"); redraw(); return; }
    H.tin = null;
    ED.timer.post({ op: "set", cd: v }, function (j) { if (j.ok) say("Countdown set: " + ED.timer.fmt(v) + " - CTL starts it"); redraw(); });
    redraw();
  }
  function onTimer() { return H.focus1 === "tmode" || H.focus1 === "timer"; }
  function key(k) {   // the keypad: its digits while typing the countdown's time (the page has said so); ENT and CLR always
    var o = ED.timer.read();
    if (H.tin && !H.tin.kbd) {
      if (/^\d$/.test(k) && H.tin.d.length < 6) H.tin.d += k;
      else if (k === "Clr") { if (H.tin.d) H.tin.d = ""; else H.tin = null; }
      else if (k === "Ent") { entryEnt(); return; }
    } else if (k === "Ent" && onTimer() && o.mode === "cd" && !o.run) openEntry(false);   // ENT on the timer: a new countdown time
    else if (k === "Clr" && onTimer() && o.mode === "cd" && !o.run && o.set) ED.timer.post({ op: "clr" }, function () { redraw(); });
    redraw();
  }
  function tellKeys(off) {   // the board: whether the keypad's ours (typing the countdown's time), and the scratchpad meanwhile
    var o = !off && !!H.tin && !H.tin.kbd && on(), show = { on: o, page: ED.pageId };
    if (o) { show.s1 = "CD"; show.s2 = ""; show.num = ED.timer.typed(H.tin.d).replace(/_/g, " ").replace(/[: ]+$/, ""); }
    var sig = JSON.stringify(show);
    if (sig === H.ktold) return;
    H.ktold = sig;
    try { fetch("/api/keypad", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {}); } catch (e) { /* nothing to tell */ }
  }
  function redraw() { if (on()) { H.textAt = 0; words(H.g || solve()); } }

  // the activated plan's time on target (the Hornet's TOT): {tot, now (s), tgt, ip (points), gspd (kts), to: "IP" | "TGT",
  // req: the ground speed you need now (m/s) - to the IP, to fly IP > TGT at GSPD and be over the TGT on the TOT (on that
  // leg, or with no GSPD: to the TGT) - late: how late you'd be at your ground speed now (s; - early), why: no req} - or null
  function zulu(t) { var d = new Date(t * 1000); return [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()].map(function (x) { return String(x).padStart(2, "0"); }).join(":") + " Z"; }
  function totCalc(g) {
    if (g.seq === "none" || g.seq === "atk") return null;
    var t = (g.nv.tots || {})[g.seq] || {}, ti = t.tgt ? g.keys.indexOf(t.tgt) : -1;
    if (ti < 0 || t.tot == null) return null;
    var now = Date.now() / 1000, tot = Math.floor(now / 86400) * 86400 + t.tot;   // (the TOT nearest now: within 12 hours)
    if (tot - now > 43200) tot -= 86400; else if (now - tot > 43200) tot += 86400;
    var out = { tot: tot, now: now, gspd: t.gspd, tgt: g.pts[g.keys[ti]], ip: ti > 0 ? g.pts[g.keys[ti - 1]] : null, to: "", req: null, late: null, why: "" };
    if (!out.tgt) return null;
    var i = g.idx;
    if (!g.fix || g.dist == null) { out.why = "No fix"; return out; }
    if (i < 0) { out.why = "Off the plan"; return out; }
    if (i > ti) { out.why = "Past the TGT"; return out; }
    var leg = function (a, b) { var p = g.pts[g.keys[a]], q = g.pts[g.keys[b]]; return p && q ? D.arc(p.lat, p.lon, q.lat, q.lon, g.R).d : 0; };
    var viaIp = out.gspd != null && ti > 0 && i < ti, end = viaIp ? ti - 1 : ti, d = g.dist, k;
    for (k = i; k < end; k++) d += leg(k, k + 1);
    var tLeg = viaIp ? leg(ti - 1, ti) / (out.gspd * 1852 / 3600) : 0, left = tot - now - tLeg;
    out.to = viaIp ? "IP" : "TGT";
    if (left > 0) out.req = d / left; else out.why = "Too late";
    if (g.gs > 1) out.late = now + d / g.gs + tLeg - tot;
    return out;
  }
  function scratch(g, off) {   // the steer-to point on the scratchpad, its place in the plan and the plan on COM1 / COM2 (only when they change)
    var show = { page: ED.pageId, s1: "", s2: "", num: "" }, st = g && g.st;
    if (!off && g && on() && onTimer() && (S.ufc || {}).menu === "PAGE") {   // (COMM1 on the timer: it)
      var ts = timerScratch();
      show.s1 = ts.s1; show.s2 = ts.s2; show.num = ts.num;
      show.com1 = g.idx >= 0 ? String(g.idx + 1) : "";
      show.com2 = g.seq === "atk" ? "A" : g.seq === "none" ? "" : g.seq;
    } else if (!off && g && on()) {
      var e = g.exo;
      show.s1 = !st ? (e ? "EX" : "") : st.src === "mk" ? "MK" : st.src === "atk" ? "AT" : st.src === "oap" ? "OS" : "WP";
      show.s2 = st ? String(st.src === "atk" ? g.idx + 1 : st.num || "").slice(0, 2) : "";
      show.num = st ? (g.dist != null ? (g.dist / 1000).toFixed(g.dist >= 1e5 ? 0 : 1) + "KM" : st.label.slice(0, 8)) : "NO STR";
      if (!st && e) {   // (sampling, with no steer-to point: the sample count, and how much further to go - or CLEAR)
        show.s2 = String(e.x.n || e.x.samples.length);
        show.num = e.near == null || !e.x.range ? "SAMPLE" : e.near < e.x.range ? "GO " + Math.ceil(e.x.range - e.near) + "M" : "CLEAR";
      }
      show.com1 = g.idx >= 0 ? String(g.idx + 1) : "";
      show.com2 = g.seq === "atk" ? "A" : g.seq === "none" ? "" : g.seq;
    }
    var sig = JSON.stringify(show);
    if (sig === H.told) return;
    H.told = sig;
    try { fetch("/api/scratch", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {}); } catch (e) { /* nothing to tell */ }
  }

  // ---- AUTO sequencing: you've reached the steer-to point (or flown past it close by): on to the next ----
  function autoSeq(g) {
    if (g.nv.auto === false || !g.fix || !g.st || g.idx < 0 || g.idx >= g.keys.length - 1 || g.dist == null) return;
    var gs = g.gs || 0, reach = g.dist < Math.max(CAPTURE_M, gs * CAPTURE_S);
    var past = gs > 20 && g.rel != null && Math.abs(g.rel) > 90 && g.dist < Math.max(PASS_M, gs * PASS_S);
    if (!reach && !past) return;
    var now = Date.now();
    if (H.autoFrom === g.st.key && now - H.autoAt < AUTO_AGAIN) return;
    H.autoFrom = g.st.key; H.autoAt = now;
    var nxt = g.pts[g.keys[g.idx + 1]];
    N.post({ op: "auto", from: g.st.key }, function (j) { if (j.steer && nxt) say("Auto: on to " + nxt.label); });
  }

  // ---- the frame ----
  function frame(force) {
    var now = performance.now(), g = solve();
    H.g = g;
    D.paint("hs-map", function (W, Hh) { return mapSvg(W, Hh, g); });
    if (force || now - H.textAt > 150) { H.textAt = now; words(g); }
    autoSeq(g);
  }
  function loop(ts) {
    H.raf = 0;
    if (!on() || S.halted || ED.hyper.on()) return;
    if (ts - H.frameAt >= (ED.reduce.matches ? 250 : 50)) { H.frameAt = ts; frame(false); }
    H.raf = requestAnimationFrame(loop);
  }
  function start() { if (!H.raf && on()) H.raf = requestAnimationFrame(loop); }

  // ---- the steer-to point: COMM2 - the activated plan's points (SEQ NONE: your waypoints, then your marks), round again
  // (the board's order, as here) ----
  function order() {   // the activated plan's points only; with SEQ NONE, all your waypoints then your marks
    var seq = N.data().seq || "none";
    return seq === "none" ? N.allKeys() : N.seqKeys(seq);
  }
  // (stepped on the board, from where it is there - COMM2 can click faster than the page hears back - each turn of COMM2 by
  // its count, so with two pages open each is stepped once; turns: [[n, clicks]...], or null: the clicks in one)
  function stepSteer(clicks, turns) {
    if (!clicks || !order().length) return;
    var told = function (j) {
      var p = j.steer ? N.point(j.steer) : null;
      if (j.steer) say("Steer to " + (p ? p.label : j.steer));
      if (on()) frame(true);
    };
    if (turns) turns.forEach(function (q) { N.post({ op: "steer", step: q[1], u: "c2t." + q[0] }, told); });
    else N.post({ op: "steer", step: clicks }, told);
  }
  function setSeq(s) { N.post({ op: "setseq", seq: s }, function (j) { if (!j.ok) say("Nothing to fly in " + N.seqName(s)); }); }
  function cycleSeq() {
    var nv = N.data(), list = SEQS.filter(function (s) { return s !== "atk" || nv.built; }), i = list.indexOf(nv.seq || "none");
    setSeq(list[(i + 1) % list.length]);
  }
  function setAuto(v) { N.post({ op: "automode", on: v }); }
  function setView(v) { H.view = v; keep(); if (on()) frame(true); }
  function pull1() {   // COMM1's pull: flip or press what it's on
    if (H.focus1 === "seq") cycleSeq();
    else if (H.focus1 === "auto") setAuto(N.data().auto === false);
    else if (H.focus1 === "view") setView(H.view === "T" ? "N" : "T");
    else if (H.focus1 === "units") setUnits(H.units === "nm" ? "km" : "nm");
    else if (H.focus1 === "tmode") timerSel();
    else if (H.focus1 === "timer") timerCtl();
    else resetScale();
  }
  function dsgSteer(n) {   // COMM2's pull, or DSG: the steer-to point designated (WPDSG; an attack plan's points aren't targets)
    var st = N.point(N.data().steer);
    if (!st) { say("No steer-to point"); return; }
    if (st.src === "atk") { say("ATK points can't be designated"); return; }
    N.dsg(st.key, n, function (j) { if (j.did !== "already") say(j.ok ? (j.tgt ? "TGT: " + ((N.point(j.tgt) || {}).label || j.tgt) : "Undesignated") : "Couldn't designate it"); });
  }

  $("hs-seq").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b && !b.disabled) { H.focus1 = "seq"; setSeq(b.dataset.v); } });
  $("hs-auto").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { H.focus1 = "auto"; setAuto(b.dataset.v === "auto"); } });
  $("hs-view").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { H.focus1 = "view"; setView(b.dataset.v); } });
  $("hs-reset").addEventListener("click", resetScale);
  $("hs-tmode").addEventListener("click", function () { H.focus1 = "tmode"; timerSel(); });
  $("hs-tdig").addEventListener("click", function () {   // (as CTL - a countdown with no time set: the keyboard types it)
    H.focus1 = "timer";
    var o = ED.timer.read();
    if (o.mode === "cd" && !o.set && !o.run) openEntry(true);
    else timerCtl();
  });
  $("hs-tin").addEventListener("input", function () {   // the digits, shown as HH:MM:SS as they're typed
    var box = $("hs-tin"), d = box.value.replace(/\D/g, "").slice(0, 6);
    box.value = d.replace(/^(\d{2})(\d)/, "$1:$2").replace(/^(\d{2}:\d{2})(\d)/, "$1:$2");
  });
  $("hs-tin").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); entryEnt(); }
    else if (e.key === "Escape") { e.preventDefault(); closeEntry(); }
  });
  $("hs-tin").addEventListener("blur", function () { if (H.tin && H.tin.kbd) closeEntry(); });
  $("hs-units").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { H.focus1 = "units"; setUnits(b.dataset.v); } });
  $("hs-chain").addEventListener("click", function (e) { var b = e.target.closest(".srow[data-key]"); if (b) N.post({ op: "steer", key: b.dataset.key }); });
  $("hs-map").parentNode.addEventListener("wheel", function (e) {
    e.preventDefault();
    zoomBy(Math.pow(1.0015, -e.deltaY * (e.deltaMode === 1 ? 33 : 1)));
  }, { passive: false });
  window.addEventListener("resize", function () { if (on()) frame(true); });

  ED.hsi = H;   // (its working state: for the tests)
  ED.hsiSolve = solve;
  ED.hsiTot = function () { return totCalc(solve()); };
  ED.page({
    tab: "nav", sub: 5, key: 4, label: "HSI", el: "pg-hsi", mode: "hsi", back: "2 Nav · HSI",
    draw: function () { frame(true); start(); },
    enter: function () { H.focus1 = "seq"; start(); },
    leave: function () { H.tin = null; scratch(null, true); tellKeys(true); },
    tick: function () {   // AUTO sequencing goes on with the HSI not showing (each second; showing, each frame)
      if (on() || S.halted || ED.hyper.on() || !S.data) return;
      var nv = N.data();
      if (nv.auto !== false && nv.steer) autoSeq(solve());
    },
    cursor: function () { marks(H.g); },
    knob1: function (clicks) {   // COMM1 steps across SEQ, AUTO / MAN, the view, RESET SCALE, KM / NM, then the timer's ET / CD and time
      var i = STOPS1.indexOf(H.focus1);
      H.focus1 = STOPS1[clamp((i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), STOPS1.length), 0, STOPS1.length - 1)];
      if (H.tin && !H.tin.kbd && H.focus1 !== "timer") H.tin = null;   // (off the time: no longer typing it)
      redraw();
      marks(H.g);
    },
    keypad: key,
    pull1: pull1,
    scroll: stepSteer,                       // COMM2 turns the steer-to point ...
    pull: function () { dsgSteer(); },       // ... and a pull designates it
    dsg: dsgSteer,                           // DSG: so does the page menu's
    dial: function (r, dt) {   // the COMM1 VOLUME dial zooms (4 times a second at full turn)
      var cue = { z: "", t: "" };
      if (r.zoom && zoomBy(Math.exp(Math.log(4) * r.zoom * dt))) cue.z = r.zoom > 0 ? "Z+" : "Z-";
      return cue;
    }
  });
})();
