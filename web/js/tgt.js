// ED Target Board page - 2 Nav › Wpt: your own waypoints on a body's surface (a mission's crash site, a settlement's
// building), kept by the board for good (settlements.sqlite) and listed in 1 Syst under their body - as an F/A-18C's HSI ›
// DATA › WYPT page: the waypoints, the marks (MK1-MK9) and the flight plans (SEQ 1-3) that the HSI flies. (Inside, a
// waypoint is still a "tgt": the board's /api/tgt, its tgts; the marks, flight plans and designation are the board's
// /api/nav - see nav.js.)
//
// Left: how to make one - MANUAL (a name and its coordinates: the UFC's keypad, or the keyboard), OVERFLY (MARK the
// point beneath you, from orbital cruise down: a mark), HUD VV (once HUD DESIG: DESIG the point your flight path meets the
// ground - your heading left and right, your flight-path angle up and down - the average of the last few seconds' points,
// with how far they wander: a mark, designated as the target), HUD X-B (cross bearings: TAKE BEARING with the dot on the
// target - your position and heading - from places round it, up to 10 (an 11th: the oldest goes); where they cross, or
// their best fit, with how far out it may be and how far each line misses it; DESIG: a mark, designated) - each lit while
// its panel shows - then the waypoints in this system, by body (each by its number - WP3 - and name: its position is on
// the right); the marks; the three flight plans.
// Right: the method's controls, or what's selected - a waypoint (EDIT its name and coordinates; DESIGNATE it - again: its
// offset aimpoint, if it has one, then nothing; O/S: its offset aimpoint, a range and bearing from it; DELETE, then
// CONFIRM), a mark (DESIGNATE; STORE AS WP; DELETE) or a flight plan (its waypoints in order - pick one and INSERT puts
// the one whose number is in ADD WP # after it, the up and down arrows move it up and down the plan, REMOVE takes it out;
// ACTIVATE SEQ makes it the HSI's - SEQ ACTIVATED; CLEAR PLAN) and its time on target, as the Hornet's HSI DATA / WYPT
// page: SET TGT makes the picked waypoint the plan's TGT (boxed; the target you designate - DSG - is red), then its TOT
// (Zulu, HH:MM:SS) and GSPD (knots, the leg from the waypoint before it - the IP - to the TGT); TOT and GSPD only with a
// TGT. Plans are put in order here only (the HSI flies them as they are). Along the bottom: the flight plan the HSI flies,
// the steer-to point (>), its TGT [bracketed] and the target you've designated.
// The UFC (page menu): COMM1 steps through the left panel and a pull picks; COMM2 steps through the right panel's
// controls and a pull presses one; DSG (Opt4) designates what COMM1 has highlighted. In a flight plan, a COMM2 pull on a
// waypoint grabs it (lit): COMM2 then moves it up and down the plan, and a pull lets it go; on ADD WP #, TOT and GSPD the
// keypad types (TOT's digits fill HH:MM:SS), ENT (or a pull) takes it, CLR clears what's typed (again: the plan's TOT or
// GSPD). ENT opens what COMM1 has
// highlighted on the UFC, as the Hornet's UFC button does: the option windows become its fields - a waypoint: POSN NAME
// O/S DEL; a mark: POSN STOR DEL; a flight plan: INS AFT DEL CLR ACT - press one (':' beside it) and type, ENT takes it,
// CLR clears it (again: leaves it; again: closes the sub-level). On the keypad:
//   coordinates, as on an F/A-18's UFC: each field starts with its hemisphere key (latitude N = 2, S = 8;
//   longitude E = 6, W = 4), then its digits fill it with the decimal point already placed (DD.DDDD, DDD.DDDD);
//   a name, like an arcade's high-score table: 2 and 8 step the letter under the cursor up and down (A-Z, 0-9,
//   hyphen, space), 4 moves the cursor back and 6 forward;
//   numbers (O/S range in metres, then bearing in degrees; a waypoint's number for INS / AFT / DEL): the digits.
//   In MANUAL and EDIT: ENT takes the field and moves on (name, latitude, longitude, SAVE); CLR clears it (again: stops
//   typing). SAVE takes two presses (ENT or a COMM2 pull): it turns to CONFIRM, then saves.
//   A flight plan's INS puts the waypoint after AFT's (0: at the start; none: at the end) and stays open for the next.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$;

  var FIELD = { lat: { hemi: { "2": "N", "8": "S" }, whole: 2, max: 90 }, lon: { hemi: { "6": "E", "4": "W" }, whole: 3, max: 180 } };
  var PLACES = 4;     // decimal places typed (and shown, as the game's HUD shows them)
  var CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ", NAME_MAX = 24;   // what the keypad can put in a name
  var DESIG_MIN = 0.5;   // degrees below the horizon your flight path must be to meet the ground
  var METHODS = { manual: "Manual", overfly: "Overfly", desig: "HUD VV", xb: "HUD X-B" };   // ("desig": HUD VV - once HUD DESIG)
  var VV_WINDOW = 3, VV_SETTLE = 1.2;   // HUD VV: seconds of points averaged - and steady this long before it averages them
  var VV_WANDER = 1.5;                  // ... its flight-path angle wandering more than this (degrees) in them: unsteady
  var XB_SIG = 1.0;                     // HUD X-B: how far out each bearing may be (degrees: the game's heading is whole degrees, and the aim)
  var XB_WIDE = 30;                     // ... the lines crossing at less than this (degrees): too nearly parallel to trust
  var RAD = Math.PI / 180;
  // the UFC sub-levels (ENT): the option windows' fields for a waypoint, a mark, a flight plan
  var LV = { wpt: ["POSN", "NAME", "O/S", "DEL", ""], mk: ["POSN", "STOR", "DEL", "", ""], seq: ["INS", "AFT", "DEL", "CLR", "ACT"] };
  var G = {
    method: "manual",     // the method picked (MANUAL / OVERFLY / HUD VV / HUD X-B)
    view: "manual",       // what the right panel shows: "manual", "overfly", "desig", a waypoint's key ("t12"), a mark's ("mk3"), a plan ("seq:1")
    edit: null,           // the target being edited (its key), on its own view
    os: null,             // the waypoint whose offset aimpoint is being set (its key), on its own view
    src: "pick",          // MANUAL's body: what 1 Syst has selected ("pick"), or the body the game's target (DEST) is on ("hud")
    mform: { name: "", lat: null, lon: null },   // MANUAL's name and coordinates, as entered
    eform: { name: "", lat: null, lon: null },   // EDIT's
    oform: { rng: "", brg: "" },                 // O/S's, as typed
    entry: null,          // typing on the keypad: {field: "lat" | "lon", hemi, digits} or {field: "name", chars, pos}
    armed: false,         // SAVE pressed once: CONFIRM showing
    confirm: false,       // DELETE pressed: CONFIRM DELETE / CANCEL showing
    sconfirm: false,      // CLEAR PLAN pressed once
    cur: {},              // each flight plan's picked waypoint (its key): INSERT puts the next after it, REMOVE takes it out
    grab: null,           // a flight plan's waypoint grabbed with COMM2 (moved up and down it): {s, key, base: its place then, n: clicks since}
    tt: null,             // a flight plan's TOT or GSPD being typed on the keypad: {f: "stot" | "sgspd", d: the digits}
    lv: null,             // a UFC sub-level open: {kind: "wpt" | "mk" | "seq", key, opt: the field typed (1-5), step, en, armed}
    focus1: "m:manual", focus2: null,   // COMM1's and COMM2's outlines
    note: "", noteAt: 0, y: {}, told: "",
    vv: [],               // HUD VV: its last few seconds' points, {t, lat, lon, range, fpa, hdg}
    xconfirm: false       // HUD X-B: CLEAR ALL pressed once
  };

  // ---- where things are ----
  function entries() { return G.y.entries || []; }
  function byKey(k) { return entries().filter(function (e) { return e.key === k; })[0] || null; }
  function byName(n) { n = String(n || "").toLowerCase(); return entries().filter(function (e) { return String(e.name || "").toLowerCase() === n; })[0] || null; }
  function short(n) {
    var sys = String(G.y.system || "");
    return sys && String(n || "").toLowerCase().indexOf(sys.toLowerCase() + " ") === 0 ? n.slice(sys.length + 1) : n || "";
  }
  function tgts() { return G.y.tgts || []; }
  function tgtOf(k) { return tgts().filter(function (t) { return t.key === k; })[0] || null; }
  function wpNum(n) { return tgts().filter(function (t) { return t.num === n; })[0] || null; }
  function nv() { return G.y.nav || {}; }
  function marks() { return nv().marks || []; }
  function mkOf(k) { return marks().filter(function (m) { return m.key === k; })[0] || null; }
  function seqOf(v) { var m = /^seq:([123])$/.exec(v || ""); return m ? m[1] : null; }
  function seqIds(s) { return ((nv().seqs || {})[s] || []); }
  function tgtKey() { return (nv().tgt || {}).key || null; }
  function bodyOf(e) {   // the body something is, or is on: {name, ok, why}
    if (!e) return null;
    var b = e.kind === "planet" || e.kind === "star" ? e : byName(e.body || (e.pic || {}).body);
    if (!b) return { name: e.body || "", ok: false, why: "Its body isn't in this system's data" };
    if (b.kind === "star") return { name: b.name, ok: false, why: "A star - select a body that isn't" };
    return { name: b.name, ok: true };
  }
  function manualBody() {   // MANUAL's body, from the switch
    if (G.src === "hud") {
      var hb = G.y.target_body ? byKey(G.y.target_body) : null;
      return hb ? bodyOf(hb) : { name: "", ok: false, why: G.y.target_name ? "Your DEST isn't on a body here" : "No DEST - target something in the game" };
    }
    var e = S.sySel ? byKey(S.sySel) : null;
    return e ? bodyOf(e) : { name: "", ok: false, why: "Nothing selected in 1 Syst" };
  }
  // where Traj's filter has you right now (its own estimate, carried on from the last reading - not the pages' easing
  // onto it), if it's on this body; but not while you hover or drift (below its SLOW): then the game's last position,
  // rather than a drift carried on past it
  function filtered(me) {
    var nav = (ED.traj || {}).nav;
    if (!nav || !nav.kx || !nav.kx.x || String(nav.body).toLowerCase() !== String(me.body || "").toLowerCase()) return null;
    var p = nav.at(performance.now() / 1000, true);
    return Math.hypot(p.v[0], p.v[1]) < ED.trajFilter.SLOW ? null : p;
  }
  function overBody() {   // OVERFLY: the body beneath you, and the point beneath you now (the filter's, else the last reading)
    var me = G.y.me;
    if ((G.y.remote || {}).on) return { name: "", ok: false, why: "Remote system - this marks where you are: 1 Syst's CURRENT SYSTEM" };
    if (!me || me.lat == null) return { name: "", ok: false, why: "No position - outside orbital cruise range" };
    var b = me.key ? byKey(me.key) : byName(me.body);
    if (!b) return { name: me.body || "", ok: false, why: "This body isn't in the system's data" };
    if (b.kind === "star") return { name: b.name, ok: false, why: "A star - no surface" };
    var f = filtered(me);
    return f ? { name: b.name, ok: true, lat: f.lat, lon: ((f.lon + 540) % 360) - 180, alt: f.alt, filtered: true }
             : { name: b.name, ok: true, lat: me.lat, lon: me.lon, alt: me.alt };
  }
  // HUD VV (once HUD DESIG): where a line from you - along your heading, at your flight-path angle (Traj's filter: your speeds) -
  // meets the ground (the level of the ground beneath you, on the planet's curve)
  function desigPoint() {
    var ob = overBody(), me = G.y.me || {}, T = ED.traj || {}, nav = T.nav;
    if (!ob.ok) return ob;
    if (me.hdg == null) return { name: ob.name, ok: false, why: "No heading" };
    if (!nav || !nav.kx || !nav.kx.x || String(nav.body).toLowerCase() !== String(me.body || "").toLowerCase())
      return { name: ob.name, ok: false, why: "Acquiring state vector" };
    var p = nav.at(performance.now() / 1000, true), gs = Math.hypot(p.v[0], p.v[1]), fpa = Math.atan2(p.v[2], gs) / RAD;
    var out = { name: ob.name, ok: false, fpa: fpa, hdg: me.hdg };
    if (p.still || gs + Math.abs(p.v[2]) < 1) { out.why = "No flight path - you're stopped"; return out; }
    if (fpa > -DESIG_MIN) { out.why = "Path not descending"; return out; }
    var R = nav.R, r0 = R + Math.max(0, p.alt), g = fpa * RAD, sg = Math.sin(g), disc = r0 * r0 * sg * sg - (r0 * r0 - R * R);
    if (disc < 0) { out.why = "Path misses the surface"; return out; }
    var s = -r0 * sg - Math.sqrt(disc), th = Math.atan2(s * Math.cos(g), r0 + s * sg);   // the angle it reaches round the planet
    var p1 = p.lat * RAD, b = me.hdg * RAD;
    var p2 = Math.asin(Math.sin(p1) * Math.cos(th) + Math.cos(p1) * Math.sin(th) * Math.cos(b));
    var l2 = p.lon * RAD + Math.atan2(Math.sin(b) * Math.sin(th) * Math.cos(p1), Math.cos(th) - Math.sin(p1) * Math.sin(p2));
    out.ok = true;
    out.lat = p2 / RAD;
    out.lon = ((l2 / RAD + 540) % 360) - 180;
    out.range = R * th;
    return out;
  }

  // HUD VV: the points that line gives, five times a second while it shows - the average of the last few seconds'
  // (once it's been steady that long), with how far they wander about it (err: m), unsteady (the flight-path angle
  // wandering), low (the game's altitude from the ground beneath you: slopes under you skew the range)
  function vvSample() {
    var d = desigPoint(), t = performance.now() / 1000;
    if (!d.ok) { G.vv = []; return; }
    G.vv.push({ t: t, lat: d.lat, lon: d.lon, range: d.range, fpa: d.fpa, hdg: d.hdg });
    G.vv = G.vv.filter(function (x) { return x.t >= t - VV_WINDOW; });
  }
  function vvPoint() {
    var d = desigPoint(), me = G.y.me || {};
    if (!d.ok) return d;
    d.low = me.avg === false;
    var now = performance.now() / 1000, pts = G.vv.filter(function (x) { return x.t >= now - VV_WINDOW; });
    if (pts.length < 4 || now - pts[0].t < VV_SETTLE) { d.settling = true; return d; }
    var R = ((ED.traj || {}).nav || {}).R || 1e6, c = Math.cos(d.lat * RAD), ex = [], ny = [];
    pts.forEach(function (x) { ex.push(D180(x.lon - d.lon) * RAD * R * c); ny.push((x.lat - d.lat) * RAD * R); });
    var mx = mean(ex), my = mean(ny), err = Math.sqrt(mean(ex.map(function (v, i) { return Math.pow(v - mx, 2) + Math.pow(ny[i] - my, 2); })));
    var fpas = pts.map(function (x) { return x.fpa; }), hdgs = pts.map(function (x) { return D180(x.hdg - d.hdg); });
    var out = { name: d.name, ok: true, lat: d.lat + my / (R * RAD), lon: ((d.lon + mx / (R * c * RAD) + 540) % 360) - 180, alt: d.alt,
                range: mean(pts.map(function (x) { return x.range; })), fpa: mean(fpas), hdg: d.hdg, err: err, n: pts.length, low: d.low };
    out.unsteady = Math.max.apply(null, fpas) - Math.min.apply(null, fpas) > VV_WANDER || Math.max.apply(null, hdgs) - Math.min.apply(null, hdgs) > 2;
    return out;
  }
  function mean(a) { return a.reduce(function (s, v) { return s + v; }, 0) / (a.length || 1); }
  function D180(a) { return ((a + 540) % 360) - 180; }

  // HUD X-B: each bearing a line across the ground from where you were (a great circle, at your heading); where two cross,
  // or (3-10) the point nearest them all, each weighted by how far it is from where it was taken (a degree's further out
  // further away). On a gnomonic projection (great circles straight lines), centred again on the answer till it settles.
  // {ok, lat, lon, err: how far out it may be (m), cross: the widest angle between the lines (degrees), miss: {id: m},
  // far: the bearings well off the rest (3+: more than 3 degrees from where the others put it - a bad sighting?), behind:
  // the bearings it's behind, why} - and the body, the bearings
  function xbSolve(list, R) {   // -> {ok, c: [lat, lon], lines: [{id, t: its range to it, miss, u}] (on a projection centred on it), why}
    var c = centroid(list), w = list.map(function () { return 1; }), pr, lines;
    function lay(b) {
      var p = pr.fwd(b.lat, b.lon), q = dest(b.lat, b.lon, b.brg, Math.min(5000, R * 0.01), R), q2 = pr.fwd(q[0], q[1]);
      var u = [q2[0] - p[0], q2[1] - p[1]], l = Math.hypot(u[0], u[1]) || 1;
      return { id: b.id, p: p, u: [u[0] / l, u[1] / l] };
    }
    for (var it = 0; it < 5; it++) {
      pr = gnomonic(c, R);
      lines = list.map(lay);
      var a = 0, bb = 0, cc = 0, r0 = 0, r1 = 0;
      lines.forEach(function (L, i) {
        var n0 = -L.u[1], n1 = L.u[0], d = n0 * L.p[0] + n1 * L.p[1];
        a += w[i] * n0 * n0; bb += w[i] * n0 * n1; cc += w[i] * n1 * n1; r0 += w[i] * n0 * d; r1 += w[i] * n1 * d;
      });
      var det = a * cc - bb * bb;
      if (!(det > 1e-9 * (a + cc) * (a + cc))) return { ok: false, why: "The lines are parallel - take one from further round" };
      var x = [(cc * r0 - bb * r1) / det, (a * r1 - bb * r0) / det];
      c = pr.inv(x[0], x[1]);
      w = lines.map(function (L) { var t = (x[0] - L.p[0]) * L.u[0] + (x[1] - L.p[1]) * L.u[1]; return 1 / Math.pow(Math.max(Math.abs(t), 200), 2); });
    }
    pr = gnomonic(c, R);   // centred on the answer: each line's range to it (t) and how far it misses it
    lines = list.map(lay).map(function (L) {
      return { id: L.id, u: L.u, t: -(L.p[0] * L.u[0] + L.p[1] * L.u[1]), miss: Math.abs(L.p[0] * L.u[1] - L.p[1] * L.u[0]) };
    });
    return { ok: true, c: c, lines: lines };
  }
  function xbFix() {
    var xb = nv().xb || {}, list = (xb.list || []).slice(), out = { ok: false, body: xb.body || "", list: list, miss: {}, far: [], behind: [] };
    if (list.length < 2) { out.why = list.length ? "One bearing - take another from 60-90° round" : "No bearings yet"; return out; }
    var R = ED.nav.radius(xb.body) || 1e6, sol = xbSolve(list, R), sig = XB_SIG * RAD, cov = [0, 0, 0], chi = 0, cross = 0;
    if (!sol.ok) { out.why = sol.why; return out; }
    sol.lines.forEach(function (L) {
      var s2 = Math.pow(Math.max(Math.abs(L.t), 50) * sig, 2);
      out.miss[L.id] = L.miss;
      if (L.t < 0) out.behind.push(L.id);
      cov[0] += L.u[1] * L.u[1] / s2; cov[1] += -L.u[1] * L.u[0] / s2; cov[2] += L.u[0] * L.u[0] / s2;
      chi += L.miss * L.miss / s2;
    });
    for (var i = 0; i < sol.lines.length; i++) for (var j = i + 1; j < sol.lines.length; j++) {
      var A = sol.lines[i].u, B = sol.lines[j].u;
      cross = Math.max(cross, Math.asin(Math.min(1, Math.abs(A[0] * B[1] - A[1] * B[0]))) / RAD);
    }
    var dt = cov[0] * cov[2] - cov[1] * cov[1];   // the answer's spread: the inverse of cov, its larger axis
    if (!(dt > 0)) { out.why = "The lines are parallel - take one from further round"; return out; }
    var ia = cov[2] / dt, ib = -cov[1] / dt, ic = cov[0] / dt, big = (ia + ic) / 2 + Math.sqrt(Math.pow((ia - ic) / 2, 2) + ib * ib);
    var scale = list.length > 2 ? Math.max(1, chi / (list.length - 2)) : 1;   // (3+: as far as the lines really miss, if that's more)
    // a bad sighting: the one furthest off where the others put it, if it's well off (then again, without it - while 3 are left)
    var set = list.slice();
    while (set.length > 2) {
      var worst = null, most = 0;
      set.forEach(function (b) {
        var rest = xbSolve(set.filter(function (x) { return x.id !== b.id; }), R);
        if (!rest.ok) return;
        var pr = gnomonic(rest.c, R), p = pr.fwd(b.lat, b.lon), q = dest(b.lat, b.lon, b.brg, Math.min(5000, R * 0.01), R), q2 = pr.fwd(q[0], q[1]);
        var u = [q2[0] - p[0], q2[1] - p[1]], l = Math.hypot(u[0], u[1]) || 1, t = -(p[0] * u[0] + p[1] * u[1]) / l, m = Math.abs(p[0] * u[1] - p[1] * u[0]) / l;
        var ang = Math.atan2(m, Math.max(Math.abs(t), 50)) / RAD;
        if (ang > most) { most = ang; worst = b; }
      });
      if (!worst || most <= 3 * XB_SIG) break;
      out.far.push(worst.id);
      set = set.filter(function (x) { return x.id !== worst.id; });
    }
    out.cross = cross;
    out.err = Math.sqrt(big * scale);
    if (list.length === 2 && out.behind.length) { out.why = "The lines cross behind you - take another"; return out; }
    out.ok = true;
    out.lat = sol.c[0];
    out.lon = ((sol.c[1] + 540) % 360) - 180;
    return out;
  }
  function centroid(list) {   // the middle of where the bearings were taken
    var v = [0, 0, 0];
    list.forEach(function (b) { var p = b.lat * RAD, l = b.lon * RAD; v[0] += Math.cos(p) * Math.cos(l); v[1] += Math.cos(p) * Math.sin(l); v[2] += Math.sin(p); });
    return [Math.atan2(v[2], Math.hypot(v[0], v[1])) / RAD, Math.atan2(v[1], v[0]) / RAD];
  }
  function gnomonic(c, R) {   // centred on c [lat, lon]: great circles are straight lines (metres at the middle)
    var p0 = c[0] * RAD, l0 = c[1] * RAD, sp0 = Math.sin(p0), cp0 = Math.cos(p0);
    return {
      fwd: function (lat, lon) {
        var p = lat * RAD, dl = lon * RAD - l0, cc = sp0 * Math.sin(p) + cp0 * Math.cos(p) * Math.cos(dl);
        return [R * Math.cos(p) * Math.sin(dl) / cc, R * (cp0 * Math.sin(p) - sp0 * Math.cos(p) * Math.cos(dl)) / cc];
      },
      inv: function (x, y) {
        var rho = Math.hypot(x, y);
        if (rho < 1e-9) return [c[0], c[1]];
        var cc = Math.atan(rho / R), sc = Math.sin(cc), ccs = Math.cos(cc);
        var p = Math.asin(ccs * sp0 + y * sc * cp0 / rho), l = l0 + Math.atan2(x * sc, rho * cp0 * ccs - y * sp0 * sc);
        return [p / RAD, l / RAD];
      }
    };
  }
  function dest(lat, lon, brg, d, R) {   // the point d metres on from lat, lon at brg (a great circle)
    var p1 = lat * RAD, b = brg * RAD, th = d / R;
    var p2 = Math.asin(Math.sin(p1) * Math.cos(th) + Math.cos(p1) * Math.sin(th) * Math.cos(b));
    var l2 = lon * RAD + Math.atan2(Math.sin(b) * Math.sin(th) * Math.cos(p1), Math.cos(th) - Math.sin(p1) * Math.sin(p2));
    return [p2 / RAD, l2 / RAD];
  }
  function xbTake() {   // TAKE BEARING: where you are and which way your nose points (the dot on the target)
    var ob = overBody(), me = G.y.me || {};
    if (!ob.ok) { say(ob.why); draw(); return; }
    if (me.hdg == null) { say("No heading"); draw(); return; }
    var had = (nv().xb || {}).list || [];
    ED.nav.post({ op: "xb", act: "take", body: ob.name, lat: Math.round(ob.lat * 1e6) / 1e6, lon: Math.round(ob.lon * 1e6) / 1e6, brg: me.hdg }, function (j) {
      if (j.did === "already") return;
      if (!j.ok) say("Couldn't take it");
      else say("Bearing " + String(Math.round(me.hdg) % 360).padStart(3, "0") + "°" + (j.fresh ? " · a new body: started again" : j.dropped ? " · the oldest dropped" : " · " + Math.min(had.length + 1, (nv().xb || {}).max || 10) + " taken"));
      draw();
    });
  }
  function xbDel(id) {
    ED.nav.post({ op: "xb", act: "del", id: id }, function (j) { if (j.did !== "already") say(j.ok ? "Bearing deleted" : "Couldn't"); draw(); });
  }
  function xbClear() {
    if (!G.xconfirm) { G.xconfirm = true; draw(); return; }
    G.xconfirm = false;
    ED.nav.post({ op: "xb", act: "clr" }, function (j) { if (j.did !== "already") say(j.ok ? "Bearings cleared" : "Couldn't"); draw(); });
  }
  function xbPoint() {   // DESIG: the fix, as a point to mark
    var f = xbFix();
    return f.ok ? { name: f.body, ok: true, lat: f.lat, lon: f.lon, alt: null } : { name: f.body, ok: false, why: f.why };
  }

  // ---- coordinates and names ----
  function fmt(v) { return v == null ? "" : (v < 0 ? "-" : "") + Math.abs(v).toFixed(PLACES); }   // as the game writes them
  function dist(m) { return m >= 1000 ? (m / 1000).toFixed(m >= 1e4 ? 0 : 1) + " km" : Math.round(m) + " m"; }
  function parse(text, field) {   // typed on the keyboard: "-59.742", "59.742 W", "N26.97" (null if it isn't one)
    var s = String(text || "").trim().toUpperCase(), sign = 1;
    var m = s.match(/^([NSEW])?\s*(-?\d{1,3}(?:\.\d*)?)\s*([NSEW])?$/);
    if (!m) return null;
    var h = m[1] || m[3], v = parseFloat(m[2]);
    if (h) {
      if (FIELD[field].hemi["2"] && "EW".indexOf(h) >= 0 || FIELD[field].hemi["6"] && "NS".indexOf(h) >= 0) return null;
      if (h === "S" || h === "W") sign = -1;
      v = Math.abs(v);
    }
    v *= sign;
    return isFinite(v) && Math.abs(v) <= FIELD[field].max ? Math.round(v * 1e6) / 1e6 : null;
  }
  function tidy(name) { return String(name || "").replace(/\s+/g, " ").trim().slice(0, 40); }
  function coordText(en) {   // what's typed so far: "N 26.97", the decimal point placed
    var w = FIELD[en.field].whole, d = en.digits;
    return { hemi: en.hemi || "", num: d.length > w ? d.slice(0, w) + "." + d.slice(w) : d };
  }
  function coordValue(en) {
    var f = FIELD[en.field], d = en.digits;
    while (d.length < f.whole + PLACES) d += "0";
    var v = parseFloat(d.slice(0, f.whole) + "." + d.slice(f.whole));
    return v <= f.max ? (en.hemi === "S" || en.hemi === "W" ? -1 : 1) * v : null;
  }
  function hintOf(field) { return field === "lat" ? "Latitude starts N (2) or S (8)" : "Longitude starts E (6) or W (4)"; }
  function form() { return G.edit ? G.eform : G.mform; }
  function formView() { return G.view === "manual" || (!!G.edit && G.view === G.edit); }

  // ---- the keypad (UFC) ----
  function addView() { return !!seqOf(G.view) && G.focus2 === "sadd"; }   // ADD WP # highlighted: the keypad types its number
  function totView() { return !!seqOf(G.view) && (G.focus2 === "stot" || G.focus2 === "sgspd"); }   // TOT / GSPD: the keypad types them
  function keypadWanted() { return !!G.lv || !!G.entry || (formView() && G.focus2 === "save") || addView() || totView(); }
  function tell(off) {   // the board: whether the keypad's ours, and what the scratchpad (and, in a sub-level, the option windows) show
    var on = !off && keypadWanted() && ED.showing("nav", 4), show = { on: on, page: ED.pageId }, en = G.entry;
    if (on && G.lv) {
      var sp = lvScratch();
      show.s1 = sp.s1; show.s2 = sp.s2; show.num = sp.num; show.opts = LV[G.lv.kind]; show.cue = G.lv.opt || G.lv.armed || null;
    } else if (on && en && en.field === "name") {
      var from = Math.max(0, en.pos - 7), win = en.chars.slice(from, from + 8);
      if (en.pos === en.chars.length && win.length < 8) win.push("_");
      show.s1 = "NM";
      show.num = win.join("");
    } else if (on && en) {
      var t = coordText(en);
      show.s1 = t.hemi || (en.field === "lat" ? "LA" : "LO");
      show.num = t.num;
    } else if (on && addView()) {
      show.s1 = "WP";
      show.num = $("tg-sadd").value;
    } else if (on && totView()) {
      var tv = totShown(seqOf(G.view), G.focus2);
      show.s1 = G.focus2 === "stot" ? "TO" : "GS";
      show.s2 = G.focus2 === "stot" ? "T" : "";
      show.num = tv;
    } else if (on) {
      show.num = G.armed ? "CONFIRM" : "SAVE";
    }
    var sig = JSON.stringify(show);
    if (sig === G.told) return;
    G.told = sig;
    try {
      fetch("/api/keypad", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {});
    } catch (e) { /* nothing to tell */ }
  }
  function startEntry(field) {
    G.armed = false;
    if (field === "name") {
      var cs = tidy(form().name).toUpperCase().split("").slice(0, NAME_MAX);
      G.entry = { field: "name", chars: cs, pos: cs.length };
    } else {
      G.entry = { field: field, hemi: null, digits: "" };
    }
    G.focus2 = field;
    draw();
  }
  function stopEntry() { G.entry = null; }
  function nameKey(en, k) {
    var ch = en.chars, i;
    if (k === "2" || k === "8") {   // the letter under the cursor, up or down (a new one past the end)
      if (en.pos >= ch.length) {
        if (ch.length >= NAME_MAX) return;
        ch.push(k === "2" ? CHARS[0] : CHARS[CHARS.length - 1]);
      } else {
        i = CHARS.indexOf(ch[en.pos]);
        ch[en.pos] = i < 0 ? CHARS[0] : CHARS[(i + (k === "2" ? 1 : CHARS.length - 1)) % CHARS.length];
      }
    } else if (k === "6") {
      en.pos = Math.min(Math.min(ch.length, NAME_MAX - 1), en.pos + 1);
    } else if (k === "4") {
      en.pos = Math.max(0, en.pos - 1);
    } else if (k === "Clr") {
      if (ch.length) { en.chars = []; en.pos = 0; } else stopEntry();
    } else if (k === "Ent") {
      form().name = tidy(ch.join(""));
      next("name");
    }
  }
  function coordKey(en, k) {
    var f = FIELD[en.field], hint = hintOf(en.field);
    if (k === "Clr") {
      if (en.hemi || en.digits) { en.hemi = null; en.digits = ""; } else stopEntry();
    } else if (k === "Ent") {
      if (!en.hemi && !en.digits) next(en.field);   // nothing typed: keep what the field had, on to the next
      else if (!en.hemi) say(hint);
      else {
        var v = coordValue(en);
        if (v == null) say((en.field === "lat" ? "Latitude" : "Longitude") + " is at most " + f.max);
        else { form()[en.field] = v; next(en.field); }
      }
    } else if (!en.hemi) {
      if (f.hemi[k]) en.hemi = f.hemi[k];
      else say(hint);
    } else if (/^\d$/.test(k) && en.digits.length < f.whole + PLACES) {
      en.digits += k;
    }
  }
  function key(k) {   // a keypad key, while the page has the keypad (and ENT / CLR always)
    if (G.lv) { lvKey(k); draw(); return; }
    var en = G.entry;
    if (en && en.field === "name") nameKey(en, k);
    else if (en) coordKey(en, k);
    else if (formView() && G.focus2 === "save") {   // SAVE highlighted: ENT presses it, CLR backs off CONFIRM
      if (k === "Ent") { pressSave(); return; }
      if (k === "Clr") G.armed = false;
    } else if (addView()) {   // ADD WP #: digits type it, ENT inserts it, CLR clears it
      var box = $("tg-sadd");
      if (/^\d$/.test(k) && box.value.length < 3) box.value = box.value.replace(/\D/g, "") + k;
      else if (k === "Clr") box.value = "";
      else if (k === "Ent") { insTyped(); return; }
    } else if (totView()) {   // TOT / GSPD: digits type it, ENT sets it, CLR clears what's typed (again: the plan's)
      var f = G.focus2, s = seqOf(G.view);
      if (!G.tt || G.tt.f !== f) G.tt = { f: f, d: "" };
      if (/^\d$/.test(k) && G.tt.d.length < (f === "stot" ? 6 : 4)) G.tt.d += k;
      else if (k === "Clr") { if (G.tt.d) G.tt.d = ""; else { G.tt = null; totSet(s, f === "stot" ? { tot: null } : { gspd: null }); return; } }
      else if (k === "Ent") { totEnter(s, f); return; }
    } else if (k === "Ent") lvOpen();   // ENT: what COMM1 has highlighted, on the UFC
    draw();
  }
  function next(field) {   // a field done: on to the next (name, latitude, longitude), then SAVE
    var order = ["name", "lat", "lon"], i = order.indexOf(field);
    if (i < order.length - 1) startEntry(order[i + 1]);
    else { stopEntry(); G.focus2 = "save"; }
  }
  function say(t) { G.note = t; G.noteAt = Date.now(); }

  // ---- the UFC sub-levels: ENT on a waypoint, a mark or a flight plan ----
  function lvOpen() {
    var k = G.focus1 || "", kind = /^t\d+$/.test(k) && tgtOf(k) ? "wpt" : /^mk\d$/.test(k) && mkOf(k) ? "mk" : seqOf(k) ? "seq" : null;
    if (!kind) { say("ENT: highlight a waypoint, mark or flight plan (COMM1)"); return; }
    stopEntry(); G.armed = false;
    G.lv = { kind: kind, key: k, opt: null, step: null, en: null, armed: null };
    if (G.view !== k) show(k);
  }
  function lvClose() { G.lv = null; }
  function lvStart(opt, step, en) { var L = G.lv; L.opt = opt; L.step = step; L.en = en; L.armed = null; }
  function lvCoord(field) { return { field: field, hemi: null, digits: "" }; }
  function lvOpt(i) {
    var L = G.lv, label = LV[L.kind][i - 1];
    if (!label) return;
    if (L.kind === "wpt") {
      var t = tgtOf(L.key);
      if (!t) { lvClose(); return; }
      if (label === "POSN") { lvStart(i, "lat", lvCoord("lat")); L.vals = { lat: t.lat, lon: t.lon }; }
      else if (label === "NAME") { var cs = tidy(t.name).toUpperCase().split("").slice(0, NAME_MAX); lvStart(i, "name", { field: "name", chars: cs, pos: cs.length }); }
      else if (label === "O/S") { lvStart(i, "rng", { digits: "" }); L.vals = {}; }
      else if (label === "DEL") { if (L.armed === i) { L.armed = null; del(t); lvClose(); } else { lvStart(null, null, null); L.armed = i; } }
    } else if (L.kind === "mk") {
      var m = mkOf(L.key);
      if (!m) { lvClose(); return; }
      if (label === "POSN") { lvStart(i, "lat", lvCoord("lat")); L.vals = { lat: m.lat, lon: m.lon }; }
      else if (label === "STOR") { lvStart(null, null, null); stor(m); }
      else if (label === "DEL") { if (L.armed === i) { L.armed = null; mkDel(m); lvClose(); } else { lvStart(null, null, null); L.armed = i; } }
    } else {
      var s = seqOf(L.key);
      if (label === "INS" || label === "AFT" || label === "DEL") lvStart(i, "wp", { digits: "" });
      else if (label === "CLR") { if (L.armed === i) { L.armed = null; seqClear(s); } else { lvStart(null, null, null); L.armed = i; } }
      else if (label === "ACT") { lvStart(null, null, null); seqFly(s); }
    }
  }
  function lvKey(k) {
    var L = G.lv, en = L.en;
    if (/^Opt[1-5]$/.test(k)) { lvOpt(+k.slice(3)); return; }
    if (k === "Clr") {   // clears what's typed; again (or nothing typed): stops typing (or disarms); again: closes the sub-level
      if (en && (en.digits || en.hemi || (en.chars && en.chars.length))) { if (en.chars) { en.chars = []; en.pos = 0; } else { en.digits = ""; en.hemi = null; } }
      else if (L.opt || L.armed) lvStart(null, null, null);
      else lvClose();
      return;
    }
    if (k === "Ent") {
      if (L.armed) { lvOpt(L.armed); return; }
      if (L.step) lvEnter();
      return;
    }
    if (!en) return;
    if (L.step === "name") { nameKey(en, k); return; }
    if (L.step === "lat" || L.step === "lon") {
      var f = FIELD[L.step];
      if (!en.hemi) { if (f.hemi[k]) en.hemi = f.hemi[k]; else say(hintOf(L.step)); }
      else if (/^\d$/.test(k) && en.digits.length < f.whole + PLACES) en.digits += k;
      return;
    }
    if (/^\d$/.test(k) && en.digits.length < (L.step === "rng" ? 7 : 3)) en.digits += k;
  }
  function lvEnter() {   // ENT on a field being typed
    var L = G.lv, en = L.en, s = seqOf(L.key), v;
    if (L.step === "lat" || L.step === "lon") {
      if (en.hemi || en.digits) {
        if (!en.hemi) { say(hintOf(L.step)); return; }
        v = coordValue(en);
        if (v == null) { say((L.step === "lat" ? "Latitude" : "Longitude") + " is at most " + FIELD[L.step].max); return; }
        L.vals[L.step] = v;
      }
      if (L.step === "lat") { L.step = "lon"; L.en = lvCoord("lon"); return; }
      lvStart(null, null, null);
      if (L.kind === "wpt") { var t = tgtOf(L.key); if (t) saveEdit(t, t.name, L.vals.lat, L.vals.lon); }
      else ED.nav.post({ op: "mkedit", slot: +L.key.slice(2), lat: L.vals.lat, lon: L.vals.lon }, function (j) { say(j.ok ? "Moved " + L.key.toUpperCase() : "Couldn't move it"); draw(); });
      return;
    }
    if (L.step === "name") {
      var w = tgtOf(L.key);
      lvStart(null, null, null);
      if (w) saveEdit(w, tidy(en.chars.join("")), w.lat, w.lon);
      return;
    }
    if (L.step === "rng") { L.vals.rng = en.digits ? +en.digits : 0; if (!L.vals.rng) { lvStart(null, null, null); osSave(L.key, 0, 0); return; } L.step = "brg"; L.en = { digits: "" }; return; }
    if (L.step === "brg") {
      v = en.digits ? +en.digits : 0;
      if (v >= 360) { say("Bearing 0-359"); return; }
      lvStart(null, null, null);
      osSave(L.key, L.vals.rng, v);
      return;
    }
    if (L.step === "wp") {   // a waypoint's number, for INS / AFT / DEL
      var label = LV.seq[L.opt - 1], n = en.digits === "" ? null : +en.digits, w2 = n ? wpNum(n) : null;
      en.digits = "";
      if (label === "AFT") {
        if (n === null) { G.cur[s] = null; say("INS: at the end"); }
        else if (n === 0) { G.cur[s] = "start"; say("INS: at the start"); }
        else if (!w2 || seqIds(s).indexOf(w2.key) < 0) say("WP" + n + " isn't in SEQ " + s);
        else { G.cur[s] = w2.key; say("INS: after WP" + n); }
        lvStart(null, null, null);
      } else if (!w2) say(n === null ? "Type a waypoint's number" : "No WP" + n + " in this system");
      else if (label === "INS") seqIns(s, w2);   // (stays open for the next)
      else { seqDel(s, w2); lvStart(null, null, null); }
    }
  }
  function lvScratch() {   // what the scratchpad shows in a sub-level
    var L = G.lv, en = L.en, t;
    if (L.armed) return { s1: "", s2: "", num: "CONFIRM" };
    if (L.step === "lat" || L.step === "lon") { t = coordText(en); return { s1: t.hemi || (L.step === "lat" ? "LA" : "LO"), s2: "", num: t.num }; }
    if (L.step === "name") {
      var from = Math.max(0, en.pos - 7), win = en.chars.slice(from, from + 8);
      if (en.pos === en.chars.length && win.length < 8) win.push("_");
      return { s1: "NM", s2: "", num: win.join("") };
    }
    if (L.step === "rng") return { s1: "RG", s2: "", num: en.digits };
    if (L.step === "brg") return { s1: "BR", s2: "", num: en.digits };
    if (L.step === "wp") return { s1: "WP", s2: "", num: en.digits };
    var p = ED.nav.point(L.key);
    return L.kind === "seq" ? { s1: "SQ", s2: seqOf(L.key), num: "" } : { s1: L.kind === "mk" ? "MK" : "WP", s2: String(p ? p.num : ""), num: "" };
  }

  // ---- saving, marking, editing, deleting ----
  function post(body, done) {   // (answering a UFC press: with its token, as ED.nav.post)
    var u = ED.ufcU ? ED.ufcU() : undefined;
    if (u) body.u = u;
    fetch("/api/tgt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) { done(j || {}); ED.refresh(); }, function () { done({}); });
  }
  function formReady() {   // why SAVE can't go yet, or null
    var f = form();
    if (!G.edit) { var b = manualBody(); if (!b || !b.ok) return b ? b.why : "No body"; }
    return f.lat == null || f.lon == null ? "Enter the latitude and longitude" : null;
  }
  function pressSave() {   // SAVE: once for CONFIRM, again to save
    var why = formReady();
    stopEntry();
    G.focus2 = "save";
    if (why) { G.armed = false; say(why); draw(); return; }
    if (!G.armed) { G.armed = true; draw(); return; }
    G.armed = false;
    var f = form(), t = G.edit ? tgtOf(G.edit) : null;
    if (G.edit && !t) { G.edit = null; draw(); return; }
    var body = t ? { op: "edit", id: t.id, name: tidy(f.name), lat: f.lat, lon: f.lon }
                 : { op: "add", body: manualBody().name, name: tidy(f.name), lat: f.lat, lon: f.lon, method: "manual" };
    post(body, function (j) {
      if (j.ok && t) { say("Changed " + j.tgt.name); G.edit = null; G.focus2 = "edit"; }
      else if (j.ok) { say("Saved " + j.tgt.name); G.mform = { name: "", lat: null, lon: null }; G.focus2 = "name"; ED.replay($("tg-list"), "flk"); }
      else say(t ? "Couldn't change it" : "Couldn't save that");
      draw();
    });
    draw();
  }
  function saveEdit(t, name, lat, lon) {   // a sub-level's POSN or NAME
    post({ op: "edit", id: t.id, name: name, lat: lat, lon: lon }, function (j) { say(j.ok ? "Changed " + j.tgt.name : "Couldn't change it"); draw(); });
  }
  function markAt(p, method, dsg, verb) {   // MARK, DESIG: a mark, at once (DESIG designates it too)
    if (!p.ok) { say(p.why); draw(); return; }
    ED.nav.post({ op: "mark", body: p.name, lat: Math.round(p.lat * 1e6) / 1e6, lon: Math.round(p.lon * 1e6) / 1e6,
                  alt: p.alt != null ? Math.round(p.alt) : null, method: method, dsg: !!dsg }, function (j) {
      say(j.ok ? verb + " " + j.mark.name + (dsg ? " · TGT" : "") : "Couldn't mark it");
      if (j.ok) ED.replay($("tg-list"), "flk");
      draw();
    });
  }
  function dsgIt(k, n) {   // DESIGNATE: a waypoint (again: its offset aimpoint, then nothing) or a mark
    if (!k) return;
    ED.nav.dsg(k, n, function (j) {
      if (j.did === "already") return;
      var p = j.tgt ? ED.nav.point(j.tgt) : null;
      say(!j.ok ? "Couldn't designate it" : j.tgt ? "TGT: " + (p ? p.label : j.tgt) : "Undesignated");
      draw();
    });
  }
  function startEdit() {
    var t = tgtOf(G.view);
    if (!t) return;
    G.edit = t.key;
    G.eform = { name: t.name, lat: t.lat, lon: t.lon };
    G.armed = false;
    G.focus2 = "name";
    draw();
  }
  function cancelEdit() { stopEntry(); G.edit = null; G.armed = false; G.focus2 = "edit"; draw(); }
  function del(t) {
    t = t || tgtOf(G.view);
    if (!t) return;
    post({ op: "delete", id: t.id }, function (j) {
      G.confirm = false;
      if (j.ok) { say("Deleted " + t.name); if (G.view === t.key) { G.view = G.method; G.focus1 = "m:" + G.method; } }
      else say("Couldn't delete it");
      draw();
    });
  }
  function startOs() {
    var t = tgtOf(G.view), o = t ? (nv().oaps || {})[t.key + "o"] : null;
    if (!t) return;
    G.os = t.key;
    G.oform = { rng: o ? String(Math.round(o.rng)) : "", brg: o ? String(Math.round(o.brg)) : "" };
    G.focus2 = "osave";
    draw();
  }
  function osSave(k, rng, brg) {
    var t = tgtOf(k);
    if (!t) return;
    ED.nav.post({ op: "oap", id: t.id, rng: rng, brg: brg }, function (j) {
      say(!j.ok ? "Couldn't set the offset" : rng ? "O/S: " + dist(rng) + " at " + String(Math.round(brg)).padStart(3, "0") + "° from " + t.name : "O/S cleared");
      if (j.ok) G.os = null;
      if (G.focus2 && /^o/.test(G.focus2)) G.focus2 = "os";
      draw();
    });
  }
  function osForm() {   // O/S typed on the keyboard: range in metres, bearing in degrees
    var r = parseFloat(G.oform.rng), b = parseFloat(G.oform.brg);
    if (!isFinite(r) || r < 0 || r > 1e6) { say("Range: metres, 0 to 1,000,000"); draw(); return; }
    if (r && (!isFinite(b) || b < 0 || b >= 360)) { say("Bearing: 0-359 degrees true"); draw(); return; }
    osSave(G.os, r, r ? b : 0);
  }
  function stor(m) {   // a mark kept as a waypoint
    ED.nav.post({ op: "mkstor", slot: m.slot }, function (j) { say(j.ok ? "Stored " + m.name + " as " + j.tgt.name : "Couldn't store it"); if (j.ok) ED.replay($("tg-list"), "flk"); draw(); });
  }
  function mkDel(m) {
    ED.nav.post({ op: "mkdel", slot: m.slot }, function (j) {
      G.confirm = false;
      if (j.ok) { say("Deleted " + m.name); if (G.view === m.key) { G.view = G.method; G.focus1 = "m:" + G.method; } }
      else say("Couldn't delete it");
      draw();
    });
  }
  // a flight plan: INSERT after the picked waypoint (or at the start / end), REMOVE, CLEAR, FLY IT
  function seqIns(s, t) {
    var cur = G.cur[s], after = cur === "start" ? 0 : cur && seqIds(s).indexOf(cur) >= 0 ? tgtOf(cur).id : null;
    ED.nav.post({ op: "seq", seq: +s, act: "ins", id: t.id, after: after }, function (j) {
      if (j.ok) { G.cur[s] = t.key; say("SEQ " + s + ": WP" + t.num + " in"); }
      else say({ "already in it": "WP" + t.num + " is in SEQ " + s + " already", "another body": "SEQ " + s + " is on another body" }[j.why] || "Couldn't add it");
      draw();
    });
  }
  function seqDel(s, t) {
    ED.nav.post({ op: "seq", seq: +s, act: "del", id: t.id }, function (j) {
      if (j.ok && G.cur[s] === t.key) G.cur[s] = null;
      say(j.ok ? "SEQ " + s + ": WP" + t.num + " out" : "WP" + t.num + " isn't in SEQ " + s);
      draw();
    });
  }
  function seqMove(s, t, to, done) {   // a waypoint moved up or down its flight plan, to a place in it (0: the first)
    ED.nav.post({ op: "seq", seq: +s, act: "mv", id: t.id, to: to }, function (j) {
      if (!j.ok) say("Couldn't move it");
      if (done) done(j);
      draw();
    });
  }
  function nudge(s, by) {   // the up / down arrows: the picked waypoint one place up (-1) or down (+1)
    var ids = seqIds(s), t = tgtOf(G.cur[s]), i = ids.indexOf(G.cur[s]);
    if (!t || i < 0) { say("Pick a waypoint in the plan"); draw(); return; }
    var to = Math.max(0, Math.min(ids.length - 1, i + by));
    if (to === i) { say("WP" + t.num + " is " + (by < 0 ? "first" : "last") + " already"); draw(); return; }
    seqMove(s, t, to, function (j) { if (j.ok) say("WP" + t.num + (by < 0 ? " up" : " down")); });
  }
  function grabTurn(clicks) {   // COMM2 turned with a waypoint grabbed: it moves to its place then plus the clicks since
    var g = G.grab, ids = seqIds(g.s), t = tgtOf(g.key);
    if (!t || ids.indexOf(g.key) < 0) { G.grab = null; draw(); return; }
    var to = Math.max(0, Math.min(ids.length - 1, g.base + g.n + clicks));
    g.n = to - g.base;   // (held at the ends, so turning back moves it at once)
    if (to !== ids.indexOf(g.key)) seqMove(g.s, t, to);   // (a place, not a step: two pages answering one turn move it once)
    else draw();
  }
  function grabPull(s, k) {   // a COMM2 pull on a flight plan's waypoint: grab it, or let it go
    var t = tgtOf(k);
    if (G.grab && G.grab.key === k) { G.grab = null; say(t ? "WP" + t.num + " placed" : ""); draw(); return; }
    G.cur[s] = k;
    G.grab = t ? { s: s, key: k, base: seqIds(s).indexOf(k), n: 0 } : null;
    if (t) say("WP" + t.num + " grabbed: COMM2 moves it, a pull lets go");
    draw();
  }
  function seqClear(s) {
    ED.nav.post({ op: "seq", seq: +s, act: "clr" }, function (j) { G.sconfirm = false; G.cur[s] = null; say(j.ok ? "SEQ " + s + " cleared" : "Couldn't clear it"); draw(); });
  }
  // a flight plan's time on target (the Hornet's HSI DATA / WYPT): its TGT, TOT (Zulu seconds into the day) and GSPD (knots)
  function totOf(s) { return ((nv().tots || {})[s]) || {}; }
  function hms(v) { v = Math.round(v); return [Math.floor(v / 3600), Math.floor(v / 60) % 60, v % 60].map(function (x) { return String(x).padStart(2, "0"); }).join(":"); }
  function hmsDigits(d) { return d.replace(/^(\d{2})(\d)/, "$1:$2").replace(/^(\d{2}:\d{2})(\d)/, "$1:$2"); }   // 1405 -> 14:05 as typed
  function totParse(text) {   // HH:MM:SS or HH:MM (or their digits) -> seconds into the day, or null
    var d = String(text || "").replace(/\D/g, "");
    if (d.length === 4) d += "00";
    if (d.length !== 6) return null;
    var h = +d.slice(0, 2), m = +d.slice(2, 4), sec = +d.slice(4, 6);
    return h < 24 && m < 60 && sec < 60 ? h * 3600 + m * 60 + sec : null;
  }
  function totShown(s, f) {   // what TOT's or GSPD's box shows: what's being typed, else the plan's
    if (G.tt && G.tt.f === f) return f === "stot" ? hmsDigits(G.tt.d) : G.tt.d;
    var t = totOf(s);
    return f === "stot" ? (t.tot != null ? hms(t.tot) : "") : (t.gspd != null ? String(t.gspd) : "");
  }
  function totSet(s, body, done) {
    ED.nav.post(Object.assign({ op: "tot", seq: +s }, body), function (j) {
      if (!j.ok) say({ "set the TGT first": "Set the plan's TGT first", tot: "TOT is HH:MM:SS (Zulu)", gspd: "GSPD is " + 60 + "-" + 3000 + " kts" }[j.why] || "Couldn't");
      else if ("tgt" in body) { var t = j.tot.tgt ? tgtOf(j.tot.tgt) : null; say(t ? "SEQ " + s + " TGT: WP" + t.num : "SEQ " + s + ": no TGT"); }
      else if ("tot" in body) say(j.tot.tot != null ? "SEQ " + s + " TOT " + hms(j.tot.tot) + " Z" : "SEQ " + s + ": TOT cleared");
      else if ("gspd" in body) say(j.tot.gspd != null ? "SEQ " + s + " GSPD " + j.tot.gspd + " kts" : "SEQ " + s + ": GSPD cleared");
      if (done) done(j);
      draw();
    });
  }
  function totEnter(s, f) {   // TOT / GSPD typed (the keypad's digits, or the box): set it
    var text = G.tt && G.tt.f === f ? G.tt.d : $(f === "stot" ? "tg-stot" : "tg-sgspd").value;
    G.tt = null;
    if (f === "stot") {
      var v = totParse(text);
      if (v == null) { say("TOT is HH:MM:SS (Zulu)"); draw(); return; }
      totSet(s, { tot: v });
    } else {
      var n = parseInt(String(text).replace(/\D/g, ""), 10);
      if (!isFinite(n)) { say("Type the GSPD (kts)"); draw(); return; }
      totSet(s, { gspd: n });
    }
  }
  function totTgt(s) {   // SET TGT: the picked waypoint is the plan's TGT (it again: none)
    var k = G.cur[s], t = tgtOf(k);
    if (!t || seqIds(s).indexOf(k) < 0) { say("Pick a waypoint in the plan, then SET TGT"); draw(); return; }
    totSet(s, { tgt: totOf(s).tgt === k ? null : t.id });
  }
  function seqFly(s) {
    ED.nav.post({ op: "setseq", seq: s }, function (j) { say(j.ok ? "SEQ " + s + " activated: the HSI flies it" : "Couldn't"); draw(); });
  }

  // ---- the panels ----
  function stops1() {
    return ["m:manual", "m:overfly", "m:desig", "m:xb"].concat(tgts().map(function (t) { return t.key; }), marks().map(function (m) { return m.key; }),
                                                      ["seq:1", "seq:2", "seq:3"]);
  }
  function stops2() {
    if (G.view === "manual") return ["src", "name", "lat", "lon", "save"];
    if (G.view === "overfly") return ["mark"];
    if (G.view === "desig") return ["desig"];
    if (G.view === "xb") return G.xconfirm ? ["xclr"] : ["xtake", "xdsg", "xclr"].concat(((nv().xb || {}).list || []).slice().reverse().map(function (b) { return "x:" + b.id; }));
    var s = seqOf(G.view);
    if (s) return seqIds(s).map(function (k) { return "c:" + k; }).concat(G.sconfirm ? ["sclr"] :
      ["sadd", "stgt"].concat(totOf(s).tgt ? ["stot", "sgspd"] : [], ["sact", "sdel", "sclr"]));
    if (mkOf(G.view)) return G.confirm ? ["mcancel", "mconfirm"] : ["mdsg", "mstor", "mdel"];
    if (!tgtOf(G.view)) return [];
    if (G.edit === G.view) return ["name", "lat", "lon", "save", "ecancel"];
    if (G.os === G.view) return ["osave", "oclr", "ocancel"];
    return G.confirm ? ["cancel", "confirm"] : ["edit", "dsg", "os", "del"];
  }
  function show(view) {
    if (view !== G.view) { stopEntry(); G.confirm = false; G.sconfirm = false; G.xconfirm = false; G.armed = false; G.edit = null; G.os = null; G.grab = null; if (G.lv && G.lv.key !== view) lvClose(); }
    G.view = view;
    if (METHODS[view]) G.method = view;
    var s2 = stops2();
    G.focus2 = s2.indexOf(G.focus2) >= 0 ? G.focus2 : s2[0] || null;
    draw();
  }
  function rowHtml(key, icon, num, name, right, extra) {   // (the target's row: its name in red). num: WP3, MK2 (or "")
    return '<button type="button" class="srow tgr' + (key === G.view ? " sel" : "") + (extra || "") + '" data-key="' + ED.esc(key) + '">' +
      '<span class="nm">' + ED.icon(icon) + (num ? '<span class="tgnum">' + ED.esc(num) + "</span> " : "") + ED.esc(name) + '</span><span class="rt">' +
      ED.esc(right) + "</span></button>";
  }
  function listHtml() {
    var groups = [], seen = {}, tk = tgtKey(), out = "";
    tgts().forEach(function (t) {
      var k = t.body.toLowerCase();
      if (!seen[k]) { seen[k] = { body: t.body, list: [] }; groups.push(seen[k]); }
      seen[k].list.push(t);
    });
    out += groups.length ? groups.map(function (g) {
      return '<div class="tghd">' + ED.esc(short(g.body)) + "</div>" + g.list.map(function (t) {
        return rowHtml(t.key, "tgt", "WP" + t.num, t.name, "", tk === t.key || tk === t.key + "o" ? " istgt" : "");
      }).join("");
    }).join("") : '<div class="tgnil" id="tg-railx">No waypoints in this system</div>';
    out += '<div class="tghd tgsub">Marks · next MK' + (nv().next || 1) + "</div>";
    out += marks().length ? marks().map(function (m) {
      return rowHtml(m.key, "mark", m.name, "· " + short(m.body), "", tk === m.key ? " istgt" : "");
    }).join("") : '<div class="tgnil">None yet - MK on the UFC, Overfly, HUD VV or HUD X-B</div>';
    out += '<div class="tghd tgsub">Flight plans</div>';
    out += ["1", "2", "3"].map(function (s) {
      var n = seqIds(s).length, fly = nv().seq === s;
      return rowHtml("seq:" + s, "seq", "", "SEQ " + s + (fly ? " · HSI" : ""), n ? n + " WP" : "Empty", fly ? " tgfly" : "");
    }).join("");
    return out;
  }
  function grid(rows) {
    return rows.map(function (r) {
      return '<div class="cell' + (r[2] ? " wide" : "") + '"><span class="lab">' + ED.esc(r[0]) + '</span><span class="v">' + ED.esc(r[1]) + "</span></div>";
    }).join("");
  }
  function boxText(field) {   // a box: what's being typed, or the value
    var en = G.entry, f = form();
    if (en && en.field === field) {
      if (field === "name") return en.chars.join("");
      var t = coordText(en);
      return (t.hemi ? t.hemi + " " : "") + t.num;
    }
    return field === "name" ? f.name : fmt(f[field]);
  }
  function live(id, p) {   // OVERFLY / HUD VV: the body and the point, live
    $(id + "body").textContent = p.ok || p.name ? short(p.name) + (p.ok ? "" : " · " + p.why) : p.why;
    $(id + "body").classList.toggle("bad", !p.ok);
    $(id + "lat").textContent = p.ok ? fmt(p.lat) : "--";
    $(id + "lon").textContent = p.ok ? fmt(p.lon) : "--";
  }
  function made(t) {
    return new Date(t * 1000).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  function chainHtml(s) {   // a flight plan's waypoints in order: the picked one, the steer-to point (>), its TGT (boxed) and the target (red)
    var ids = seqIds(s), cur = G.cur[s], st = nv().steer, tk = tgtKey(), pt = totOf(s).tgt;
    if (!ids.length) return '<div class="tgnil">Empty - type a waypoint\'s number and INSERT (or ENT on the UFC: INS)</div>';
    return (cur === "start" ? '<div class="tgins">Inserting at the start</div>' : "") + ids.map(function (k, i) {
      var t = tgtOf(k);
      return '<button type="button" class="srow tgc' + (k === cur ? " sel" : "") + (G.grab && G.grab.key === k ? " grab" : "") + '" data-c="' + ED.esc(k) + '" data-f2="c:' + ED.esc(k) + '">' +
        '<span class="nm">' + (i + 1) + ". " + (k === st && nv().seq === s ? "&gt; " : "") + '<span class="' + (k === pt ? "tgbox" : "") + (k === tk || k + "o" === tk ? " tgdsg" : "") + '">WP' + (t ? t.num : "?") + "</span> " +
        ED.esc(t ? t.name : "") + '</span><span class="rt">' + (t ? fmt(t.lat) + ", " + fmt(t.lon) : "") + "</span></button>";
    }).join("");
  }
  function strip() {   // along the bottom: the flight plan the HSI flies, the steer-to point and the target
    var n = nv(), s = n.seq || "none", keys = (n.seqs || {})[s] || [], pt = (((n.tots || {})[s]) || {}).tgt, tp = n.tgt;
    var chain = s === "none" ? "" : keys.length ? keys.map(function (k) {
      var p = ED.nav.point(k), l = p ? p.label : "?";
      l = k === pt ? "[" + l + "]" : l;   // (its TGT)
      return k === n.steer ? "&gt;" + ED.esc(l) : ED.esc(l);
    }).join(" - ") : "Empty";
    var sp = ED.nav.point(n.steer);
    return '<span class="lab">HSI</span> <span class="tgsq">' + ED.nav.seqName(s) + "</span> " + chain +
      ' <span class="lab">Str</span> ' + ED.esc(sp ? sp.label : "--") + ' <span class="lab">Tgt</span> <span class="tgtv">' +
      ED.esc(tp ? tp.label || tp.name : "None") + "</span>";
  }
  function draw() {
    var y = G.y, ufc = (S.ufc || {}).menu === "PAGE";
    if (G.note && Date.now() - G.noteAt > 6000) G.note = "";
    if (S.navNote && Date.now() - S.navNoteAt < 6000 && !G.note) { G.note = S.navNote; G.noteAt = S.navNoteAt; S.navNote = ""; }
    if (!METHODS[G.view] && !tgtOf(G.view) && !mkOf(G.view) && !seqOf(G.view)) { G.view = G.method; G.edit = null; G.os = null; }   // (deleted, or another system)
    if (G.edit && G.edit !== G.view) G.edit = null;
    if (G.os && G.os !== G.view) G.os = null;
    if (G.lv && ((G.lv.kind === "wpt" && !tgtOf(G.lv.key)) || (G.lv.kind === "mk" && !mkOf(G.lv.key)))) lvClose();   // (deleted)
    // left: the methods, the waypoints, marks and flight plans
    Array.prototype.forEach.call($("tg-meth").querySelectorAll("button[data-m]"), function (b) {
      var on = b.dataset.m === G.view;   // (lit only while its panel shows)
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", String(on));
    });
    $("tg-sys").innerHTML = "Waypoints" + (y.system ? " · " + ((y.remote || {}).on ? '<span class="rmt">Remote · ' + ED.esc(y.system) + "</span>" : ED.esc(y.system)) : "");
    var n = nv(), sig = JSON.stringify([tgts().map(function (t) { return [t.key, t.name, t.lat, t.lon]; }), marks(), n.seqs, n.seq, n.next, tgtKey(), G.view]);
    if (sig !== G.listSig) { G.listSig = sig; $("tg-list").innerHTML = listHtml(); }
    $("pg-tgt").classList.toggle("tgnone", !tgts().length);
    // right: the method, the waypoint, mark or flight plan, or the waypoint being edited
    var t = tgtOf(G.view), m = mkOf(G.view), s = seqOf(G.view), editing = !!t && G.edit === t.key, osing = !!t && G.os === t.key;
    var fv = G.view === "manual" || editing;
    $("tg-bodysec").hidden = !fv;
    $("tg-form").hidden = !fv;
    $("tg-over").hidden = G.view !== "overfly";
    $("tg-desig").hidden = G.view !== "desig";
    $("tg-xb").hidden = G.view !== "xb";
    $("tg-one").hidden = !t || editing || osing;
    $("tg-osf").hidden = !osing;
    $("tg-mk").hidden = !m;
    $("tg-seq").hidden = !s;
    if (fv) {
      var mb = editing ? { name: t.body, ok: true } : manualBody();
      $("tg-case").textContent = editing ? "Edit · your waypoint" : "Create · manual";
      $("tg-name").textContent = editing ? t.name : "Manual";
      $("tg-srcrow").hidden = editing;
      Array.prototype.forEach.call($("tg-src").querySelectorAll("button"), function (b) {
        b.classList.toggle("on", b.dataset.v === G.src);
        b.setAttribute("aria-pressed", String(b.dataset.v === G.src));
      });
      $("tg-body").textContent = mb.ok ? short(mb.name) : mb.why;
      $("tg-body").classList.toggle("bad", !mb.ok);
      ["nm", "lat", "lon"].forEach(function (id) {
        var field = id === "nm" ? "name" : id, el = $("tg-" + id), typing = !!(G.entry && G.entry.field === field);
        if (document.activeElement !== el || typing) el.value = boxText(field);
        el.classList.toggle("typing", typing);
        el.readOnly = typing;
      });
      var nameTyping = G.entry && G.entry.field === "name";
      $("tg-car").hidden = !nameTyping;
      if (nameTyping) $("tg-car").style.setProperty("--at", String(G.entry.pos));
      $("tg-nm").placeholder = editing ? "WPT " + t.num + " - " + short(t.body) : "WPT n - " + (mb.ok ? short(mb.name) : "body");
      $("tg-save").textContent = G.armed ? "Confirm" : editing ? "Save changes" : "Save waypoint";
      $("tg-save").classList.toggle("arm", G.armed);
      $("tg-save").disabled = !!formReady() && !G.armed;
      $("tg-ecancel").hidden = !editing;
    } else if (G.view === "overfly") {
      var ob = overBody();
      $("tg-case").textContent = "Create · overfly · a mark";
      $("tg-name").textContent = "Overfly";
      live("tg-o", ob);
      $("tg-oalt").textContent = ob.ok && ob.alt != null ? dist(ob.alt) : "--";
      $("tg-mark").disabled = !ob.ok;
      $("tg-mark").textContent = "Mark · MK" + (n.next || 1);
    } else if (G.view === "desig") {
      var dp = vvPoint(), wide = dp.ok && dp.err != null && dp.err > Math.max(100, dp.range * 0.05);
      $("tg-case").textContent = "Create · HUD VV · a mark, designated";
      $("tg-name").textContent = "HUD VV";
      live("tg-d", dp);
      $("tg-drng").textContent = !dp.ok ? "--" : dist(dp.range) + (dp.settling ? " · settling" : " ± " + dist(dp.err));
      $("tg-drng").classList.toggle("bad", !!(wide || dp.unsteady));
      $("tg-dpath").textContent = dp.hdg != null ? "Hdg " + String(Math.round(dp.hdg) % 360).padStart(3, "0") + "°" +
        (dp.fpa != null ? " · " + (dp.fpa >= 0 ? "+" : "") + dp.fpa.toFixed(1) + "°" : "") : "--";
      var dw = [];
      if (dp.ok && dp.unsteady) dw.push("Unsteady - hold the dive and the dot");
      if (dp.ok && dp.low) dw.push("Low: the game's altitude is from the ground beneath you - slopes under you skew the range");
      $("tg-dwarn").textContent = dw.join(" · ");
      $("tg-dwarn").hidden = !dw.length;
      $("tg-dbtn").disabled = !dp.ok;
      $("tg-dbtn").textContent = "Desig · MK" + (n.next || 1);
    } else if (G.view === "xb") {
      var xf = xbFix(), ob2 = overBody(), me2 = y.me || {}, xl = xf.list, xmax = (n.xb || {}).max || 10;
      $("tg-case").textContent = "Create · HUD X-B · cross bearings · a mark, designated";
      $("tg-name").textContent = "HUD X-B";
      $("tg-xbody").textContent = xf.body ? short(xf.body) + (ob2.ok && ob2.name.toLowerCase() !== xf.body.toLowerCase() ? " · you're over " + short(ob2.name) : "") :
        ob2.ok ? short(ob2.name) : ob2.why;
      $("tg-xbody").classList.toggle("bad", !xf.body && !ob2.ok);
      $("tg-xhdg").textContent = me2.hdg != null ? String(Math.round(me2.hdg) % 360).padStart(3, "0") + "° · put the dot on the target" : "--";
      $("tg-xlat").textContent = xf.ok ? fmt(xf.lat) : "--";
      $("tg-xlon").textContent = xf.ok ? fmt(xf.lon) : "--";
      var rb = xf.ok && ob2.ok && ob2.name.toLowerCase() === xf.body.toLowerCase() ? ED.trajDraw.arc(ob2.lat, ob2.lon, xf.lat, xf.lon, ED.nav.radius(xf.body)) : null;
      $("tg-xfix").textContent = !xf.ok ? xf.why : "± " + dist(xf.err) + " · crossing " + Math.round(xf.cross) + "°" +
        (rb ? " · " + dist(rb.d) + " at " + String(Math.round(rb.ab) % 360).padStart(3, "0") + "°" : "");
      $("tg-xfix").classList.toggle("bad", !xf.ok || xf.err > 150);
      var xw = [];
      if (xf.ok && xf.cross < XB_WIDE) xw.push("The lines cross at " + Math.round(xf.cross) + "° - take one from 60-90° round");
      var bnum = function (id) { return xl.map(function (b) { return b.id; }).indexOf(id) + 1; };
      if (xf.ok && xf.far.length) xw.push("Bearing " + xf.far.map(bnum).join(", ") + (xf.far.length > 1 ? " look" : " looks") + " well off the rest - delete " + (xf.far.length > 1 ? "them" : "it") + "?");
      if (xf.ok && xf.behind.length) xw.push("Behind bearing " + xf.behind.map(bnum).join(", "));
      $("tg-xwarn").textContent = xw.join(" · ");
      $("tg-xwarn").hidden = !xw.length;
      $("tg-xtake").textContent = "Take bearing · " + Math.min(xl.length + 1, xmax);
      $("tg-xtake").disabled = !ob2.ok || me2.hdg == null;
      $("tg-xdsg").disabled = !xf.ok;
      $("tg-xdsg").textContent = "Desig · MK" + (n.next || 1);
      $("tg-xclr").textContent = G.xconfirm ? "Confirm clear" : "Clear all";
      $("tg-xclr").classList.toggle("tgdanger", G.xconfirm);
      $("tg-xclr").disabled = !xl.length;
      $("tg-xhd").textContent = "Bearings · " + xl.length + " of " + xmax + (xl.length >= xmax ? " · the next drops the oldest" : "");
      var xsig = JSON.stringify([xl, xf.ok && xl.map(function (b) { return Math.round(xf.miss[b.id]); }), xf.far]);
      if (xsig !== G.xSig) {
        G.xSig = xsig;
        $("tg-xlist").innerHTML = xl.length ? xl.map(function (b, i) { return i; }).reverse().map(function (i) {
          var b = xl[i], miss = xf.ok ? xf.miss[b.id] : null;
          return '<div class="srow tgx" data-f2="x:' + b.id + '"><span class="nm">' + (i + 1) + ". " + String(Math.round(b.brg) % 360).padStart(3, "0") + "° · " +
            new Date(b.saved * 1000).toLocaleTimeString("en-GB") + '</span><span class="rt' + (xf.ok && xf.far.indexOf(b.id) >= 0 ? " far" : "") + '">' +
            (miss != null ? "misses by " + dist(miss) : "") + '</span><button type="button" class="tgxdel" data-x="' + b.id + '" title="Delete this bearing">Del</button></div>';
        }).join("") : '<div class="tgnil">None yet - the dot on the target, then TAKE BEARING; again from 60-90° round</div>';
      }
    } else if (t) {
      var oap = (n.oaps || {})[t.key + "o"], tk = tgtKey(), inSeq = ["1", "2", "3"].filter(function (q) { return seqIds(q).indexOf(t.key) >= 0; });
      $("tg-case").textContent = "WP" + t.num + " · " + short(t.body) + " surface" + (tk === t.key ? " · TGT" : tk === t.key + "o" ? " · TGT (O/S)" : "");
      $("tg-name").textContent = t.name;
      var rows = [["Body", short(t.body), true], ["Position", fmt(t.lat) + ", " + fmt(t.lon), true],
                  ["Made", (METHODS[t.method] || "Manual") + " · " + made(t.saved), true]];
      if (oap) rows.push(["Offset (O/S)", dist(oap.rng) + " at " + String(Math.round(oap.brg)).padStart(3, "0") + "° · " + fmt(oap.lat) + ", " + fmt(oap.lon), true]);
      rows.push(["Flight plans", inSeq.length ? inSeq.map(function (q) { return "SEQ " + q; }).join(", ") : "None", true]);
      $("tg-grid").innerHTML = grid(rows);
      if (osing) {
        $("tg-case").textContent = "Offset aimpoint · WP" + t.num;
        ["rng", "brg"].forEach(function (f) { var el = $("tg-o" + f); if (document.activeElement !== el) el.value = G.oform[f]; });
        $("tg-oclr").disabled = !oap;
      }
      $("tg-dsg").textContent = tk === t.key && oap ? "Desig O/S" : tk === t.key || tk === t.key + "o" ? "Undesignate" : "Designate";
      $("tg-edit").hidden = $("tg-dsg").hidden = $("tg-os").hidden = $("tg-del").hidden = G.confirm;
      $("tg-cancel").hidden = $("tg-confirm").hidden = !G.confirm;
    } else if (m) {
      $("tg-case").textContent = "Mark · " + short(m.body) + " surface" + (tgtKey() === m.key ? " · TGT" : "");
      $("tg-name").textContent = m.name;
      $("tg-mgrid").innerHTML = grid([["Body", short(m.body), true], ["Position", fmt(m.lat) + ", " + fmt(m.lon), true],
        ["Made", (METHODS[m.method] || "Overfly") + " · " + made(m.saved) + (m.alt != null ? " · " + dist(m.alt) + " up" : ""), true]]);
      $("tg-mdsg").textContent = tgtKey() === m.key ? "Undesignate" : "Designate";
      $("tg-mdsg").hidden = $("tg-mstor").hidden = $("tg-mdel").hidden = G.confirm;
      $("tg-mcancel").hidden = $("tg-mconfirm").hidden = !G.confirm;
    } else if (s) {
      var ids = seqIds(s), first = ids.length ? tgtOf(ids[0]) : null;
      $("tg-case").textContent = "Flight plan" + (first ? " · " + short(first.body) : "") + (n.seq === s ? " · the HSI's" : "");
      $("tg-name").textContent = "SEQ " + s;
      if (G.grab && (G.grab.s !== s || ids.indexOf(G.grab.key) < 0)) G.grab = null;   // (gone from the plan)
      var tt = totOf(s), ttw = tt.tgt ? tgtOf(tt.tgt) : null;
      var csig = JSON.stringify([ids, G.cur[s], n.steer, n.seq, tgtKey(), tt.tgt, G.grab && G.grab.key, tgts().map(function (q) { return [q.key, q.name, q.num]; })]);
      if (csig !== G.chainSig) { G.chainSig = csig; $("tg-chain").innerHTML = chainHtml(s); }
      $("tg-sact").disabled = !ids.length;
      $("tg-sact").textContent = n.seq === s ? "SEQ activated" : "Activate SEQ";
      $("tg-sdel").disabled = !G.cur[s] || G.cur[s] === "start";
      var at = ids.indexOf(G.cur[s]);
      $("tg-sup").disabled = at <= 0;
      $("tg-sdn").disabled = at < 0 || at >= ids.length - 1;
      $("tg-sclr").textContent = G.sconfirm ? "Confirm clear" : "Clear plan";
      $("tg-sclr").classList.toggle("tgdanger", G.sconfirm);
      $("tg-sclr").disabled = !ids.length;
      $("tg-sact").hidden = $("tg-sdel").hidden = $("tg-sup").hidden = $("tg-sdn").hidden = G.sconfirm;
      // time on target: SET TGT (the picked one - or CLEAR TGT, it picked), then TOT and GSPD
      if (G.tt && G.focus2 !== G.tt.f) G.tt = null;   // (moved off what was being typed: dropped)
      var ip = ttw ? ids.indexOf(tt.tgt) : -1, ipw = ip > 0 ? tgtOf(ids[ip - 1]) : null;
      $("tg-stgt").textContent = tt.tgt && G.cur[s] === tt.tgt ? "Clear TGT" : "Set TGT";
      $("tg-stgtv").textContent = ttw ? "WP" + ttw.num : "None";
      $("tg-stgtv").classList.toggle("tgbox", !!ttw);
      ["stot", "sgspd"].forEach(function (f) {
        var el = $("tg-" + f);
        el.disabled = !ttw;
        el.classList.toggle("typing", !!G.tt && G.tt.f === f);
        if (document.activeElement !== el) el.value = ttw ? totShown(s, f) : "";
      });
      $("tg-totl").textContent = !ttw ? "Set the plan's TGT (pick a waypoint in it) - then its TOT and GSPD" :
        (tt.tot != null ? "TOT " + hms(tt.tot) + " Z over WP" + ttw.num : "No TOT yet") + " · " +
        (ipw ? "WP" + ipw.num + " (IP) > WP" + ttw.num + (tt.gspd != null ? " at " + tt.gspd + " kts" : ": no GSPD") : "no IP (the TGT is first)");
    }
    $("tg-note").textContent = G.note;
    $("tg-strip").innerHTML = strip();
    // the UFC sub-level, as the UFC shows it
    $("tg-lv").hidden = !G.lv;
    if (G.lv) $("tg-lv").innerHTML = ED.nav.lvHtml(LV[G.lv.kind], G.lv.opt || G.lv.armed || null, lvScratch());
    // the UFC's outlines (page menu only)
    var s1 = stops1(), s2 = stops2();
    if (s1.indexOf(G.focus1) < 0) G.focus1 = s1[0];
    if (s2.indexOf(G.focus2) < 0) G.focus2 = s2[0] || null;
    if (G.focus2 !== "save") G.armed = false;   // CONFIRM only while SAVE is highlighted
    Array.prototype.forEach.call($("pg-tgt").querySelectorAll("[data-f]"), function (el) { el.classList.toggle("focus", ufc && el.dataset.f === G.focus1); });
    Array.prototype.forEach.call($("tg-list").querySelectorAll(".srow"), function (el) { el.classList.toggle("cur", ufc && el.dataset.key === G.focus1); });
    Array.prototype.forEach.call($("pg-tgt").querySelectorAll("[data-f2]"), function (el) { el.classList.toggle("focus", ufc && el.dataset.f2 === G.focus2); });
    tell();
  }

  // ---- the UFC ----
  function step(list, cur, clicks) {
    var i = list.indexOf(cur);
    return list[Math.max(0, Math.min(list.length - 1, (i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), list.length)))];
  }
  function knob1(clicks) {
    if (G.lv) lvClose();   // (moving on: the sub-level closes)
    G.focus1 = step(stops1(), G.focus1, clicks);
    draw();
    var el = $("tg-list").querySelector('.srow[data-key="' + G.focus1 + '"]');
    if (el) el.scrollIntoView({ block: "nearest" });
  }
  function pull1() {
    var f = G.focus1 || "";
    show(f.indexOf("m:") === 0 ? f.slice(2) : f);
  }
  function scroll(clicks) {
    if (G.entry) return;   // (typing: the keypad has it)
    if (G.grab) { grabTurn(clicks); return; }   // (a flight plan's waypoint grabbed: COMM2 moves it)
    var s2 = stops2();
    if (s2.length) { G.focus2 = step(s2, G.focus2, clicks); draw(); }
    var row = /^x:/.test(G.focus2 || "") ? $("tg-xlist").querySelector('[data-f2="' + G.focus2 + '"]') : null;   // (HUD X-B's bearings scroll)
    if (row) row.scrollIntoView({ block: "nearest" });
  }
  function pull() {   // COMM2: press what it's on
    var f = G.focus2 || "", t = tgtOf(G.view), m = mkOf(G.view), s = seqOf(G.view);
    if (f === "src") { G.src = G.src === "pick" ? "hud" : "pick"; draw(); }
    else if (f === "name" || f === "lat" || f === "lon") { if (G.entry && G.entry.field === f) key("Ent"); else startEntry(f); }
    else if (f === "save") pressSave();
    else if (f === "ecancel") cancelEdit();
    else if (f === "mark") markAt(overBody(), "overfly", false, "Marked");
    else if (f === "desig") markAt(vvPoint(), "desig", true, "Designated");
    else if (f === "xtake") xbTake();
    else if (f === "xdsg") markAt(xbPoint(), "xb", true, "Designated");
    else if (f === "xclr") xbClear();
    else if (f.indexOf("x:") === 0) xbDel(+f.slice(2));
    else if (f === "edit") startEdit();
    else if (f === "dsg") dsgIt(G.view);
    else if (f === "os") startOs();
    else if (f === "osave") osForm();
    else if (f === "oclr" && t) osSave(t.key, 0, 0);
    else if (f === "ocancel") { G.os = null; G.focus2 = "os"; draw(); }
    else if (f === "del") { G.confirm = true; G.focus2 = "cancel"; draw(); }
    else if (f === "cancel") { G.confirm = false; G.focus2 = "del"; draw(); }
    else if (f === "confirm") del();
    else if (f === "mdsg" && m) dsgIt(m.key);
    else if (f === "mstor" && m) stor(m);
    else if (f === "mdel") { G.confirm = true; G.focus2 = "mcancel"; draw(); }
    else if (f === "mcancel") { G.confirm = false; G.focus2 = "mdel"; draw(); }
    else if (f === "mconfirm" && m) mkDel(m);
    else if (f.indexOf("c:") === 0 && s) grabPull(s, f.slice(2));
    else if (f === "sadd" && s) insTyped();
    else if (f === "stgt" && s) totTgt(s);
    else if ((f === "stot" || f === "sgspd") && s) totEnter(s, f);
    else if (f === "sact" && s) seqFly(s);
    else if (f === "sdel" && s && tgtOf(G.cur[s])) seqDel(s, tgtOf(G.cur[s]));
    else if (f === "sclr" && s) { if (G.sconfirm) seqClear(s); else { G.sconfirm = true; draw(); } }
  }
  function dsgKey() {   // DSG: what COMM1 has highlighted (else what the right panel shows), if it's a waypoint or a mark
    var ok = function (k) { return !!k && ((/^t\d+$/.test(k) && tgtOf(k)) || (/^mk\d$/.test(k) && mkOf(k))); };
    return ok(G.focus1) ? G.focus1 : ok(G.view) ? G.view : null;
  }

  // ---- the mouse and keyboard ----
  $("tg-meth").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-m]");
    if (b && !b.disabled) { G.focus1 = "m:" + b.dataset.m; show(b.dataset.m); }
  });
  $("tg-list").addEventListener("click", function (e) {
    var b = e.target.closest(".srow[data-key]");
    if (b) { G.focus1 = b.dataset.key; show(b.dataset.key); }
  });
  $("tg-src").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-v]");
    if (b) { G.src = b.dataset.v; G.focus2 = "src"; draw(); }
  });
  ["nm", "lat", "lon"].forEach(function (id) {
    var el = $("tg-" + id), field = id === "nm" ? "name" : id;
    function take() {
      if (G.entry && G.entry.field === field) return;
      G.armed = false;
      if (field === "name") { form().name = tidy(el.value); draw(); return; }
      var v = el.value.trim() === "" ? null : parse(el.value, field);
      if (el.value.trim() !== "" && v == null) say(field === "lat" ? "Latitude: -90 to 90 (or N / S)" : "Longitude: -180 to 180 (or E / W)");
      form()[field] = v;
      draw();
    }
    el.addEventListener("change", take);
    el.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      take();
      if (field === "name") $("tg-lat").focus(); else if (field === "lat") $("tg-lon").focus(); else pressSave();
    });
    el.addEventListener("focus", function () { G.focus2 = field; });
  });
  ["rng", "brg"].forEach(function (f) {
    var el = $("tg-o" + f);
    el.addEventListener("input", function () { G.oform[f] = el.value; });
    el.addEventListener("keydown", function (e) { if (e.key === "Enter") { G.oform[f] = el.value; if (f === "rng") $("tg-obrg").focus(); else osForm(); } });
  });
  $("tg-save").addEventListener("click", pressSave);
  $("tg-ecancel").addEventListener("click", cancelEdit);
  $("tg-mark").addEventListener("click", function () { markAt(overBody(), "overfly", false, "Marked"); });
  $("tg-dbtn").addEventListener("click", function () { markAt(vvPoint(), "desig", true, "Designated"); });
  $("tg-xtake").addEventListener("click", function () { G.focus2 = "xtake"; xbTake(); });
  $("tg-xdsg").addEventListener("click", function () { G.focus2 = "xdsg"; markAt(xbPoint(), "xb", true, "Designated"); });
  $("tg-xclr").addEventListener("click", function () { G.focus2 = "xclr"; xbClear(); });
  $("tg-xlist").addEventListener("click", function (e) { var b = e.target.closest("button[data-x]"); if (b) xbDel(+b.dataset.x); });
  $("tg-edit").addEventListener("click", startEdit);
  $("tg-dsg").addEventListener("click", function () { dsgIt(G.view); });
  $("tg-os").addEventListener("click", startOs);
  $("tg-osave").addEventListener("click", osForm);
  $("tg-oclr").addEventListener("click", function () { osSave(G.view, 0, 0); });
  $("tg-ocancel").addEventListener("click", function () { G.os = null; draw(); });
  $("tg-del").addEventListener("click", function () { G.confirm = true; G.focus2 = "cancel"; draw(); });
  $("tg-cancel").addEventListener("click", function () { G.confirm = false; G.focus2 = "del"; draw(); });
  $("tg-confirm").addEventListener("click", function () { del(); });
  $("tg-mdsg").addEventListener("click", function () { dsgIt(G.view); });
  $("tg-mstor").addEventListener("click", function () { var m = mkOf(G.view); if (m) stor(m); });
  $("tg-mdel").addEventListener("click", function () { G.confirm = true; G.focus2 = "mcancel"; draw(); });
  $("tg-mcancel").addEventListener("click", function () { G.confirm = false; G.focus2 = "mdel"; draw(); });
  $("tg-mconfirm").addEventListener("click", function () { var m = mkOf(G.view); if (m) mkDel(m); });
  $("tg-chain").addEventListener("click", function (e) {
    var b = e.target.closest(".srow[data-c]"), s = seqOf(G.view);
    if (b && s) { G.cur[s] = b.dataset.c; G.focus2 = "c:" + b.dataset.c; draw(); }
  });
  function insTyped() {
    var s = seqOf(G.view), n = parseInt($("tg-sadd").value, 10), t = isFinite(n) ? wpNum(n) : null;
    if (!s) return;
    if (!t) { say(isFinite(n) ? "No WP" + n + " in this system" : "Type a waypoint's number"); draw(); return; }
    $("tg-sadd").value = "";
    seqIns(s, t);
  }
  $("tg-sins").addEventListener("click", insTyped);
  $("tg-sadd").addEventListener("keydown", function (e) { if (e.key === "Enter") insTyped(); });
  $("tg-sact").addEventListener("click", function () { var s = seqOf(G.view); if (s) seqFly(s); });
  $("tg-sdel").addEventListener("click", function () { var s = seqOf(G.view); if (s && tgtOf(G.cur[s])) seqDel(s, tgtOf(G.cur[s])); });
  $("tg-sup").addEventListener("click", function () { var s = seqOf(G.view); if (s) nudge(s, -1); });
  $("tg-stgt").addEventListener("click", function () { var s = seqOf(G.view); if (s) { G.focus2 = "stgt"; totTgt(s); } });
  ["stot", "sgspd"].forEach(function (f) {
    $("tg-" + f).addEventListener("keydown", function (e) { var s = seqOf(G.view); if (e.key === "Enter" && s) { G.tt = null; totEnter(s, f); } });
  });
  $("tg-sdn").addEventListener("click", function () { var s = seqOf(G.view); if (s) nudge(s, 1); });
  $("tg-sclr").addEventListener("click", function () { var s = seqOf(G.view); if (!s) return; if (G.sconfirm) seqClear(s); else { G.sconfirm = true; draw(); } });

  // OVERFLY, HUD VV and HUD X-B: their points move between readings (the filter), so they're redrawn five times a second while
  // they show (HUD VV: its points kept, for their average)
  setInterval(function () {
    if (G.view !== "desig" || !ED.showing("nav", 4)) G.vv = [];   // (HUD VV's points: only while it shows)
    if (!ED.showing("nav", 4) || S.halted || document.hidden || !(G.view === "overfly" || G.view === "desig" || G.view === "xb")) return;
    if (G.view === "desig") vvSample();
    draw();
  }, 200);

  ED.tgt = G;   // (its working state: for the tests)
  ED.tgtDesig = desigPoint;
  ED.tgtVV = vvPoint;
  ED.tgtXb = xbFix;
  ED.tgtOver = overBody;   // (the UFC's MK marks the point beneath you, wherever you are on the page)
  ED.page({
    tab: "nav", sub: 4, key: 3, label: "Wpt", el: "pg-tgt", mode: "tgt", back: "2 Nav · Wpt",
    update: function (s) { G.y = s.syst || {}; },
    draw: function () { draw(); },
    enter: function () { G.focus1 = "m:" + G.method; draw(); },
    leave: function () { stopEntry(); lvClose(); G.confirm = false; G.armed = false; tell(true); },   // (the keypad back to the sub-tabs)
    cursor: function () { draw(); },
    tick: function () { if (ED.showing("nav", 4) && G.note && Date.now() - G.noteAt > 6000) draw(); },
    knob1: knob1, pull1: pull1, scroll: scroll, pull: pull, keypad: key,
    dsg: function (n) { var k = dsgKey(); if (k) dsgIt(k, n); }
  });
})();
