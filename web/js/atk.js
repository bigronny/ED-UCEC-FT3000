// ED Target Board page - 2 Nav › Atk: the attack plan and a mine-release computer, like a Hornet's CCRP. The target is
// the designated one (TGT: DSG on a waypoint, its offset aimpoint, a mark, or a surface site in 1 Syst - see nav.js).
//
// PLAN: a pre-made profile built round the target - the 2-ship low-level pop (the card: the IP at 10 NM, #2 splitting
// right no later than 8 NM, both popping in from different sides and coming off left) - from ATK HDG (the heading from the
// IP to the target; AUTO: the bearing you have to it when you BUILD), your role (#1 or #2 of the flight: WK51, WK52),
// the speed (the card's 480 KTAS; the profile's distances scale with it, so its times stay the card's) and BASE (the
// heights: Base / Base+1 by role, as the card's legend). The picture shows both tracks round the target, ATK HDG up -
// yours solid - as you set them; BUILD makes the points (the board: NavBoard) and the HSI flies yours (ATK). The plan
// code shares it with your wingman: COPY puts it on this PC's clipboard (again within 2 minutes: pasted into Elite - its
// chat box, say), LOAD takes one (typed in the box, else from the clipboard) and builds it with you in the other role.
// The UFC (page menu): COMM1 steps PLAN / ATTACK, ATK HDG (a pull grabs it: then each click turns it - faster clicks,
// bigger steps), ROLE and BUILD; COMM2 COPY and LOAD; ENT opens the plan on the UFC: HDG SPD BASE ROLE BLD (type the
// digits, ENT; HDG with nothing typed: AUTO; BLD twice builds).
//
// ATTACK:
// The model, from three drops on Makalu (0.64 g): a mine keeps your ground speed for CARRY seconds, then drops
// straight down - or lands first, if its fall is shorter - so it lands your ground speed x the shorter of CARRY
// and its fall time ahead of where you let it go. The drops landed 9.7, 9.9 and 10.5 s of ground speed on, from
// 720 to 1,400 m at 205 to 393 m/s (a mine that kept your speed all the way down would have gone twice as far
// from 1,400 m; one that kept it a second, a tenth as far). So above the height a fall takes CARRY seconds from
// (about 314 m at 0.64 g) your height doesn't move the release point; below it, it does. The fall assumes a level
// release, from your height averaged over LEVEL_TAU seconds (near the ground the game's height follows the terrain,
// so your vertical speed from it is too rough to use); when you're off level by more than LEVEL_FPA degrees and
// it would change the throw, it says so - a dive shortens the fall (short), a climb lengthens it (long). Your
// position and speeds: Traj's filter, carried on between the game's readings.
// Left, top-down and track up: you, your track, the release point on it, where a mine let go now would land (the
// CCIP), the target boxed in red and the body's other settlements and waypoints; zoom with the COMM1 VOLUME dial
// or the mouse wheel (RESET SCALE: COMM2, or a click). Right: the release cue - steer to put the flight-path
// marker on the azimuth steering line; the ball falls down it onto the release bar as the release comes; beside
// it, a timer that goes round once a second, at the top on each whole second (the release on one), its marker
// swelling as it passes the top - amber, then red from the release; the countdown (also on the UFC's
// scratchpad), RELEASE, then PAST.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, D = ED.trajDraw;
  var C = D.C, RAD = D.RAD, clamp = D.clamp;

  var CARRY = 10;         // seconds a released mine keeps your ground speed (three drops: 9.7, 9.9, 10.5 s)
  var ARM = 5;            // seconds a mine takes to arm: a shorter fall than this may not go off
  var LEVEL_TAU = 3;      // seconds your height (and climb) are averaged over for the fall (the game's height near the ground follows the terrain)
  var LEVEL_FPA = 2;      // degrees off level (averaged) before it says the release point's out
  var G0 = 9.80665;       // m/s² in one g
  var CUE_S = 20;         // seconds before release the ball starts down the steering line (and the second timer runs)
  var BEAT_AFTER = 3;     // seconds the second timer runs on after the release
  var BEAT_PULSE = 0.2;   // seconds its marker stays enlarged after each whole second
  var REL_WIN = 0.5;      // seconds either side of the release point that show RELEASE
  var ASL_FULL = 10;      // degrees of steering error at the panel's edge
  var ZOOM_MIN = 300, ZOOM_MAX = 1e7;   // metres: how far in and out the top-down view goes
  var kept = (function () { try { return JSON.parse(localStorage.getItem("ft3000-atk") || "{}") || {}; } catch (e) { return {}; } })();
  var A = { view: kept.view === "atk" ? "atk" : "plan", zoom: null, zoomKey: null, scale: 3000, raf: 0, frameAt: 0, textAt: 0,
            g: null, y: {}, told: "", ktold: "",
            focus1: "view", focus2: "copy", grab: false, hdg: undefined, hdgAt: 0, stepTxt: "", stepAt: 0, lastClick: 0, lastDir: 0,
            armed: false, ul: null, note: "", noteAt: 0 };
  function keep() { try { localStorage.setItem("ft3000-atk", JSON.stringify({ view: A.view })); } catch (e) { /* storage blocked */ } }
  function on() { return ED.showing("nav", 6); }
  function say(t) { A.note = t; A.noteAt = Date.now(); }
  // the target: the designated one (TGT)
  function target() {
    var t = ED.nav.tgt();
    if (!t) return { ok: false, title: "No target", why: "Designate one - DSG on a waypoint, a mark, or a site in 1 Syst" };
    var name = t.src === "site" || t.src === "plan" || !t.label ? t.name : t.label + (t.name && t.name !== t.label ? " · " + t.name : "");
    return { ok: true, key: t.key, name: name, body: t.body, lat: t.lat, lon: t.lon, src: t.src };
  }

  // ---- the sums ----
  function bodyEntry(name) {
    name = String(name || "").toLowerCase();
    return (A.y.entries || []).filter(function (e) { return e.kind === "planet" && String(e.name || "").toLowerCase() === name; })[0] || null;
  }
  function level(t, alt, vz, key) {   // your height and vertical speed, averaged over about LEVEL_TAU seconds
    var L = A.lv;
    if (!L || L.key !== key || t - L.t > 10 || t < L.t - 1) { A.lv = { key: key, t: t, alt: alt, vz: vz }; return A.lv; }
    if (t > L.t) { var k = 1 - Math.exp(-(t - L.t) / LEVEL_TAU); L.alt += (alt - L.alt) * k; L.vz += (vz - L.vz) * k; L.t = t; }
    return L;
  }
  function fall(h, vz, gm) {   // seconds to fall h metres, starting at vz m/s (up)
    return (vz + Math.sqrt(vz * vz + 2 * gm * Math.max(0, h))) / gm;
  }
  function throwOf(gs, h, vz, gm) { return gs * Math.min(CARRY, fall(h, vz, gm)); }   // how far ahead a mine let go lands
  function solve(t) {   // everything the page shows, at time t (page seconds)
    var y = A.y, d = target(), me = y.me, g = { ok: false, d: d };
    if (!d.ok) { g.title = d.title || "No target"; g.why = d.why; return g; }
    if (!me || me.lat == null) { g.title = "No state vector"; g.why = "No planetary surface fix - outside orbital cruise range"; return g; }
    if (String(me.body || "").toLowerCase() !== String(d.body).toLowerCase()) { g.title = "Reference body mismatch"; g.why = "Target on " + d.body; return g; }
    var nav = (ED.traj || {}).nav;
    if (!nav || !nav.kx || !nav.kx.x || String(nav.body).toLowerCase() !== String(me.body).toLowerCase()) { g.title = "Acquiring state vector"; g.why = ""; return g; }
    var p = nav.at(t), R = nav.R, v = p.v, gs = Math.hypot(v[0], v[1]);
    var a = D.arc(p.lat, p.lon, d.lat, d.lon, R), T = [a.d * Math.sin(a.ab * RAD), a.d * Math.cos(a.ab * RAD)];   // the target, m east / north of you
    var be = bodyEntry(d.body), gm = be && be.gravity ? be.gravity * G0 : null, alt = Math.max(0, p.alt);
    var lv = level(t, alt, v[2], String(nav.body).toLowerCase());
    var tf = gm ? fall(lv.alt, 0, gm) : null;   // the fall, let go level from your (averaged) height
    var trk = gs > 5 ? D.n360(Math.atan2(v[0], v[1]) / RAD) : (me.hdg != null ? me.hdg : 0);
    var h = [Math.sin(trk * RAD), Math.cos(trk * RAD)];
    var along = T[0] * h[0] + T[1] * h[1], cross = T[0] * h[1] - T[1] * h[0];   // ahead, and to the right of your track
    var thr = tf != null ? throwOf(gs, lv.alt, 0, gm) : null;   // the throw: how far ahead a mine let go now lands
    var thrV = tf != null ? throwOf(gs, lv.alt, lv.vz, gm) : null;   // ... allowing for your (averaged) climb or dive
    var tau = gs > 5 && thr != null ? (along - thr) / gs : null;   // seconds to the release point
    g = { ok: true, d: d, p: p, R: R, me: me, gs: gs, vU: v[2], trk: trk, T: T, dist: a.d, brg: a.ab, along: along, cross: cross, alt: alt,
          gG: be ? be.gravity : null, gm: gm, tf: tf, thr: thr, tau: tau, track: gs > 5, body: be,
          steer: gs > 5 ? Math.atan2(cross, Math.max(1, along)) / RAD : 0,
          fpa: gs > 1 ? Math.atan2(lv.vz, gs) / RAD : 0, hmin: gm ? 0.5 * gm * ARM * ARM : null, lvAlt: lv.alt, thrV: thrV };
    g.state = !g.track ? "No track" : tau == null ? "No fall time" : tau > REL_WIN ? "Run in" : tau >= -REL_WIN ? "Release" : "Past";
    g.tti = tau != null && tf != null ? Math.max(0, tau) + tf : null;
    return g;
  }

  // ---- the scale: auto (the target in view, in round steps) or yours ----
  function niceUp(x) { var e = Math.pow(10, Math.floor(Math.log10(x))), f = x / e; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e; }
  function autoScale(g) {
    if (!g.ok) return A.scale;
    var need = clamp(niceUp(Math.max(Math.abs(g.along), Math.abs(g.cross) * 2, g.thr || 0, 200) * 1.2), ZOOM_MIN, ZOOM_MAX);
    if (need > A.scale || need < A.scale / 4) A.scale = need;   // (steps out at once, back in only well inside)
    return A.scale;
  }
  function scaleNow(g) { return A.zoom || autoScale(g); }
  function zoomBy(f) {
    var from = A.zoom || A.scale, to = clamp(from / f, ZOOM_MIN, ZOOM_MAX);
    if (Math.abs(to - from) <= from * 1e-6) return false;
    A.zoom = to; A.zoomKey = (A.g && A.g.d && A.g.d.key) || null;
    return true;
  }
  function resetScale() { A.zoom = null; A.zoomKey = null; if (on()) frame(true); }

  // ---- left: top-down, track up ----
  function planSvg(W, H, g) {
    var out = [], span = scaleNow(g), cx = W / 2, cy = H - 16, k = (cy - 14) / span, u = D.unit(span);
    var trk = g.ok ? g.trk : 0;
    function P(e, n) {   // metres east / north of you -> the picture
      var x = e * Math.cos(trk * RAD) - n * Math.sin(trk * RAD), f = e * Math.sin(trk * RAD) + n * Math.cos(trk * RAD);
      return [cx + x * k, cy - f * k];
    }
    function ahead(f, x) { return [cx + x * k, cy - f * k]; }   // f ahead along your track, x to its right
    var st = D.niceStep(span / 4), rings = [];   // range arcs ahead of you: round distances, then the picture's reach
    for (var r0 = st; r0 <= span * 0.8; r0 += st) rings.push(r0);
    rings.push(span);
    rings.forEach(function (r, i) {
      var arcp = [], last = i === rings.length - 1;
      for (var a = -90; a <= 90; a += 6) arcp.push([cx + Math.sin(a * RAD) * r * k, cy - Math.cos(a * RAD) * r * k]);
      out.push(D.line(arcp, last ? C.rule2 : C.rule, last ? null : [1, 2]));
      out.push(D.txt(cx - 4, cy - r * k + 6, last ? D.scaleTxt(r) : D.tickLab(r, u), C.muted, "end", true));   // (on your track, left of it)
    });
    out.push(D.line([[cx, cy], [cx, 8]], C.rule2, [3, 2]));   // your track
    if (!g.ok) { out.push(D.shipMark([cx, cy], [0, -1], 4, C.hi)); return out.join(""); }
    // the body's other settlements and waypoints, near enough to show
    var be = g.body, others = be ? ((be.pic || {}).sites || []).map(function (s) { return [s, "site"]; }).concat(((be.pic || {}).tgts || []).map(function (s) { return [s, "wpt"]; })) : [];
    others.forEach(function (q) {
      var s = q[0];
      if (s.key === g.d.key || s.name === g.d.name || s.lat == null) return;
      var a2 = D.arc(g.p.lat, g.p.lon, s.lat, s.lon, g.R), pt = P(a2.d * Math.sin(a2.ab * RAD), a2.d * Math.cos(a2.ab * RAD));
      if (pt[0] < 4 || pt[0] > W - 4 || pt[1] < 4 || pt[1] > cy + 6) return;
      out.push(q[1] === "wpt" ? D.poly([[pt[0], pt[1] - 3], [pt[0] + 3, pt[1]], [pt[0], pt[1] + 3], [pt[0] - 3, pt[1]]], C.text, C.text)
                              : D.poly([[pt[0] - 2, pt[1] - 2], [pt[0] + 2, pt[1] - 2], [pt[0] + 2, pt[1] + 2], [pt[0] - 2, pt[1] + 2]], C.acc, C.acc, 0.8));
    });
    // the release point on your track, and where a mine let go now would land
    if (g.track && g.tau != null && g.tau > -REL_WIN && g.along - g.thr < span) {
      var rp = ahead(Math.max(0, g.along - g.thr), 0);
      out.push(D.bar([cx - 9, rp[1]], [cx + 9, rp[1]], g.state === "Release" ? C.bad : C.acc, 2));
      out.push(D.txt(cx + 12, rp[1], "REL", g.state === "Release" ? C.bad : C.acc, "start"));
    }
    if (g.track && g.thr != null) {
      var ip = ahead(g.thr, 0);
      out.push(D.circ(ip[0], ip[1], 3, C.hi));
      out.push(D.line([[ip[0] - 6, ip[1]], [ip[0] - 3, ip[1]]], C.hi));
      out.push(D.line([[ip[0] + 3, ip[1]], [ip[0] + 6, ip[1]]], C.hi));
    }
    // the target, boxed in red (at the edge, with its range, when it's out of the picture)
    var tp = P(g.T[0], g.T[1]), inside = tp[0] > 6 && tp[0] < W - 6 && tp[1] > 6 && tp[1] < cy + 6;
    if (!inside) {
      var dx = tp[0] - cx, dy = tp[1] - cy, sc = Math.min(dx ? ((dx > 0 ? W - 8 : 8) - cx) / dx : 1e9, dy ? ((dy > 0 ? cy : 8) - cy) / dy : 1e9);
      tp = [cx + dx * Math.max(0, sc), cy + dy * Math.max(0, sc)];
      out.push(D.txt(tp[0] + (tp[0] > cx ? -6 : 6), tp[1] + 9, D.dist(g.dist), C.bad, tp[0] > cx ? "end" : "start", true));
    }
    out.push(D.poly([[tp[0] - 5, tp[1] - 5], [tp[0] + 5, tp[1] - 5], [tp[0] + 5, tp[1] + 5], [tp[0] - 5, tp[1] + 5]], null, C.bad));
    out.push(D.poly([[tp[0] - 1, tp[1] - 1], [tp[0] + 1, tp[1] - 1], [tp[0] + 1, tp[1] + 1], [tp[0] - 1, tp[1] + 1]], C.bad, C.bad));
    out.push(D.shipMark([cx, cy], [0, -1], 4, C.hi));   // you
    return out.join("");
  }

  // the second timer beside the steering line: once round a second, clockwise, at 12 o'clock on each whole second
  // of the countdown (so at the top on the release); the marker swells as it passes the top; amber, then red from
  // the release beat on. Worked out from the countdown itself every frame, so it's smooth and stays in step.
  function beat(tau) {
    if (tau == null || tau > CUE_S || tau < -BEAT_AFTER) return { on: false };
    var s = -tau, p = ((s % 1) + 1) % 1;   // the part of a second since the last whole one
    return { on: true, angle: p * 360, red: s >= 0, pulse: p < BEAT_PULSE ? 1 - p / BEAT_PULSE : 0 };
  }

  // ---- right: the release cue ----
  function cueSvg(W, H, g) {
    var out = [], cx = W / 2, fy = Math.round(H * 0.7), top = 12, ok = g.ok && g.track;
    // the flight-path marker: where you're going
    out.push(D.circ(cx, fy, 4, C.hi));
    out.push(D.line([[cx - 13, fy], [cx - 4, fy]], C.hi));
    out.push(D.line([[cx + 4, fy], [cx + 13, fy]], C.hi));
    out.push(D.line([[cx, fy - 4], [cx, fy - 8]], C.hi));
    if (!ok) { out.push(D.note(W, Math.round(H * 0.4) * 2, g.ok ? "No ground track" : g.title || "No target", C.muted)); return out.join(""); }
    // the azimuth steering line: put the marker on it
    var ax = cx + clamp(g.steer / ASL_FULL, -1, 1) * W * 0.42, col = Math.abs(g.steer) <= 1 ? C.text : C.acc;
    out.push(D.line([[ax, top], [ax, H - 6]], col));
    // the release bar, at the marker, and the seconds up the line
    out.push(D.bar([ax - 10, fy], [ax + 10, fy], g.state === "Release" ? C.bad : C.acc, 2));
    for (var s = 5; s <= CUE_S; s += 5) {
      var ty = fy - (fy - top) * s / CUE_S;
      out.push(D.line([[ax - 4, ty], [ax + 4, ty]], C.rule2));
      out.push(D.txt(ax - 7, ty, String(s), C.muted, "end"));
    }
    // the ball: down the line as the release comes, on the bar at the release point
    if (g.tau != null && g.tau >= -REL_WIN) {
      var by = fy - (fy - top) * clamp(g.tau, 0, CUE_S) / CUE_S;
      out.push(D.circ(ax, by, 4, g.state === "Release" ? C.bad : C.hi, g.state === "Release" ? C.bad : C.hi));
    }
    var bt = beat(g.tau);
    if (bt.on) {   // the second timer: right of the line, a little above the release bar (left of it near the edge)
      var rr = 9, rx = ax + 24 + rr > W - 3 ? ax - 24 : ax + 24, ry = fy - 24, bc = bt.red ? C.bad : C.acc;
      var a = bt.angle * RAD, mx = rx + rr * Math.sin(a), my = ry - rr * Math.cos(a);
      out.push(D.circ(rx, ry, rr, bc));
      out.push(D.line([[rx, ry - rr - 3], [rx, ry - rr + 2]], bc));   // 12 o'clock
      out.push(D.circ(mx, my, 2 + 2 * bt.pulse, bc, bc));
    }
    if (g.state === "Release") out.push(D.txt(cx, fy + 18, "RELEASE", C.bad));
    else if (g.state === "Past") out.push(D.txt(cx, fy + 18, "PAST", C.muted));
    var side = g.cross > 0 ? "R" : "L";
    out.push(D.txt(W - 4, H - 8, Math.abs(g.steer) < 0.05 ? "ON LINE" : "STEER " + side + " " + Math.abs(g.steer).toFixed(1) + "°", col, "end"));
    return out.join("");
  }

  // ---- the words ----
  function cell(lab, v, col) {
    return '<div class="cell trc"><span class="lab">' + ED.esc(lab) + '</span><span class="v"' + (col ? ' style="color:' + col + '"' : "") + ">" + ED.esc(v) + "</span></div>";
  }
  function cell2(lab, a, b, col) {   // a box in two halves: the reading in metres, and in a pilot's units beside it
    var st = col ? ' style="color:' + col + '"' : "";
    return '<div class="cell trc split"><span class="lab">' + ED.esc(lab) + '</span><span class="v"' + st + ">" + ED.esc(a) + '</span><span class="v v2"' + st + ">" +
      ED.esc(b) + "</span></div>";
  }
  function kts(v) { return Math.round(Math.abs(v) * 3600 / 1852).toLocaleString("en-GB") + " kts"; }   // knots: nautical miles an hour
  function nm(m) { var n = Math.abs(m) / 1852; return (n < 10 ? n.toFixed(2) : n < 100 ? n.toFixed(1) : Math.round(n).toLocaleString("en-GB")) + " NM"; }
  function ft(m) { return Math.round(m / 0.3048).toLocaleString("en-GB") + " ft"; }
  function secs(x) { return x == null ? "--" : x >= 100 ? Math.round(x) + " s" : x.toFixed(1) + " s"; }
  // the fall's colour: white over CARRY seconds (the mine's done its carry before it lands: your height - or the ground's -
  // doesn't move where it lands); amber at CARRY or under (it lands while still carried: height errors move it); red under
  // the ARM time (it may not go off)
  function fallCol(ok, tf) { return !ok || tf == null ? "" : tf < ARM ? "var(--bad)" : tf <= CARRY ? "var(--accent)" : "#ffffff"; }
  function words(g) {
    var d = g.d || {}, ok = g.ok;
    $("ak-dname").textContent = d.name || "";
    $("ak-dsub").textContent = d.ok ? "" : d.why || "";
    $("pg-atk").classList.toggle("trnodest", !d.ok);
    $("ak-wait").hidden = ok;
    $("ak-waitt").textContent = ok ? "" : g.title || "";
    $("ak-waits").textContent = ok ? "" : g.why || "";
    var stCol = !ok ? "" : g.state === "Release" ? "var(--bad)" : g.state === "Run in" ? "var(--accent)" : "var(--rule2)";
    var st = $("ak-state");
    st.textContent = ok ? g.state : "";
    st.style.background = stCol;
    st.hidden = !ok;
    $("ak-count").textContent = !ok || !g.track || g.tau == null ? "--" : g.state === "Run in" ? "REL " + (g.tau >= 10 ? Math.ceil(g.tau) : g.tau.toFixed(1)) :
      g.state === "Release" ? "RELEASE" : "PAST";
    $("ak-count").className = "akcount" + (ok && g.state === "Release" ? " rel" : ok && g.state === "Past" ? " past" : "");
    var side = ok && g.cross > 0 ? "R " : "L ";
    $("ak-lgrid").innerHTML = [
      cell2("Rng", ok ? D.dist(g.dist) : "-", ok ? nm(g.dist) : "-"), cell("Xtk", ok ? side + D.dist(Math.abs(g.cross)) : "-", ok && Math.abs(g.steer) > 1 ? "var(--accent)" : ""),
      cell("Brg", ok ? D.deg3(g.brg) + "°" : "-"), cell("Trk", ok && g.track ? D.deg3(g.trk) + "°" : "-"),
      cell2("GS", ok ? D.speed(g.gs) : "-", ok ? kts(g.gs) : "-"), cell2("Alt", ok ? D.dist(g.alt) : "-", ok ? ft(g.alt) : "-")
    ].join("");
    $("ak-rgrid").innerHTML = [
      cell("Gravity", ok && g.gG != null ? g.gG.toFixed(2) + " g" : "-"), cell("Fall", ok ? secs(g.tf) : "-", fallCol(ok, g.tf)),
      cell2("Min rel alt", ok && g.hmin != null ? D.dist(g.hmin) : "-", ok && g.hmin != null ? ft(g.hmin) : "-"), cell("Throw", ok && g.thr != null ? D.dist(g.thr) : "-"),
      cell("Impact in", ok ? secs(g.tti) : "-"), cell("FPA", ok && g.track ? (g.fpa >= 0 ? "+" : "") + g.fpa.toFixed(1) + "°" : "-")
    ].join("");
    var warn = !ok ? "" : g.gm == null ? "Gravity unknown - no fall time, so no release point (Spansh or EDSM hasn't the body's gravity)"
      : g.tf < ARM ? "Fall " + g.tf.toFixed(1) + " s - under the " + ARM + " s arming time: release from " + D.dist(g.hmin) + " or higher"
      : g.track && Math.abs(g.fpa) > LEVEL_FPA && Math.abs(g.thrV - g.thr) > 0.3 * g.gs ? (g.fpa < 0 ? "Diving " : "Climbing ") +
        Math.abs(g.fpa).toFixed(1) + "° - the release point assumes a level release: let go now, it lands " + (g.thrV < g.thr ? "short" : "long") : "";
    $("ak-warn").textContent = warn;
    $("ak-model").textContent = (ED.timing.on() ? "Timing log on · " : "") + "Carry " + CARRY + " s · Arm " + ARM + " s";
    var steerTxt = !ok || !g.track ? "" : Math.abs(g.steer) <= 1 ? "On line" : "Steer " + side + Math.abs(g.steer).toFixed(1) + "°";
    var sc = $("ak-steer");
    sc.textContent = steerTxt;
    sc.style.background = !steerTxt ? "" : Math.abs(g.steer) <= 1 ? "var(--text)" : "var(--accent)";
    sc.hidden = !steerTxt;
    $("ak-scale").textContent = D.scaleTxt(scaleNow(g));
    var z = $("ak-zoom");
    z.textContent = A.zoom ? "Manual" : "Auto";
    z.style.background = A.zoom ? "var(--accent)" : "var(--rule2)";
    marks();
    scratch(g);
  }
  function marks() {   // the switches' settings, the heading grabbed, COMM1's and COMM2's outlines (page menu only)
    var ufc = (S.ufc || {}).menu === "PAGE", p = plan();
    Array.prototype.forEach.call($("ak-mode").querySelectorAll("button"), function (b) { var o = b.dataset.v === A.view; b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o)); });
    Array.prototype.forEach.call($("ak-role").querySelectorAll("button"), function (b) { var o = +b.dataset.v === (p.role || 1); b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o)); });
    Array.prototype.forEach.call($("pg-atk").querySelectorAll("[data-f]"), function (el) { el.classList.toggle("focus", ufc && !A.grab && el.dataset.f === A.focus1); });
    Array.prototype.forEach.call($("pg-atk").querySelectorAll("[data-f2]"), function (el) { el.classList.toggle("focus", ufc && el.dataset.f2 === A.focus2); });
    $("ak-reset").classList.toggle("focus", ufc && A.view === "atk");   // COMM2's, on ATTACK
    $("ak-reset").classList.toggle("off", !A.zoom);
    $("ak-hdg").classList.toggle("grab", A.grab);
    $("ak-hdg").setAttribute("aria-pressed", String(A.grab));
  }
  function scratch(g, off) {   // the countdown on the UFC's scratchpad (only when it changes)
    var show = { page: ED.pageId, s1: "", s2: "", num: "" };
    if (!off && g && g.ok && g.track && g.tau != null && on() && A.view === "atk") {
      if (g.state === "Run in") { show.s1 = "RL"; show.num = g.tau >= 10 ? String(Math.ceil(g.tau)) : g.tau.toFixed(1); }
      else show.num = g.state === "Release" ? "RELEASE" : "PAST";
    }
    var sig = JSON.stringify(show);
    if (sig === A.told) return;
    A.told = sig;
    try { fetch("/api/scratch", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {}); } catch (e) { /* nothing to tell */ }
  }

  // ---- PLAN: the profile round the target, ATK HDG up ----
  var LVOPTS = ["HDG", "SPD", "BASE", "ROLE", "BLD"];
  function plan() { return ED.nav.data().plan || {}; }
  function built() { return ED.nav.data().built || null; }
  function prof() { var ps = ED.nav.data().profiles || {}; return ps[plan().profile || "pop2"] || null; }
  function hdgSet() { return A.hdg !== undefined ? A.hdg : plan().hdg == null ? null : plan().hdg; }   // ATK HDG as set (null: AUTO)
  function autoHdg() {   // AUTO: the bearing you have to the target now (on its body)
    var d = target(), f = d.ok ? ED.nav.fix(d.body) : null;
    return f ? Math.round(D.n360(D.arc(f.lat, f.lon, d.lat, d.lon, f.R).ab)) % 360 : null;
  }
  function hdgUse() { var h = hdgSet(); return h != null ? h : autoHdg(); }   // the heading the picture shows (AUTO with no fix: none)
  function roleName(r) { var c = ED.nav.cs(r); return c.slice(-2); }
  function preview() {   // the plan as set, each role's points: x metres right of the axis, y before the target, and their legs on
    var pr = prof(), p = plan();
    if (!pr) return null;
    var per = 1852 * (p.kts || pr.ref) / pr.ref, speed = (p.kts || pr.ref) * 1852 / 3600, base = p.base != null ? p.base : 300, step = p.step != null ? p.step : 300;
    var out = {};
    Object.keys(pr.roles).forEach(function (r) {
      var alt = { base: base, "in": r === "1" ? base : base + step, off: r === "1" ? base + step : base };
      var pts = pr.roles[r].map(function (q) { return { id: q[0], x: q[2] * per, y: q[1] * per, alt: alt[q[3]], call: q[4] }; });
      pts.forEach(function (q, i) { var n = pts[i + 1]; if (n) { q.dist = Math.hypot(n.x - q.x, n.y - q.y); q.secs = q.dist / speed; } });
      out[r] = pts;
    });
    return out;
  }
  function stale() {   // why what's built isn't the plan as set (or null)
    var b = built(), p = plan(), d = target(), h = hdgSet();
    if (!b) return "Not built";
    if ((h != null && h !== b.hdg) || p.kts !== b.kts || p.base !== b.base || p.step !== b.step || p.profile !== b.profile || p.cs !== b.cs) return "Changed - BUILD again";
    if (d.ok && (Math.abs(d.lat - b.tgt.lat) > 1e-6 || Math.abs(d.lon - b.tgt.lon) > 1e-6)) return "New target - BUILD again";
    return null;
  }
  function geoSvg(W, H) {
    var out = [], pv = preview(), d = target(), h = hdgUse(), mine = String(plan().role || 1);
    if (!pv) return D.note(W, H, "No profile", C.muted);
    var hr = (h || 0) * RAD, all = [];
    Object.keys(pv).forEach(function (r) { pv[r].forEach(function (q) { all.push([q.x, q.y]); }); });
    var f = d.ok ? ED.nav.fix(d.body) : null, you = null;
    if (f) {   // you, in the plan's frame (if you're on its body)
      var a = D.arc(d.lat, d.lon, f.lat, f.lon, f.R), e = a.d * Math.sin(a.ab * RAD), n = a.d * Math.cos(a.ab * RAD);
      you = [e * Math.cos(hr) - n * Math.sin(hr), -(e * Math.sin(hr) + n * Math.cos(hr))];
    }
    var x0 = Math.min.apply(null, all.map(function (p) { return p[0]; })), x1 = Math.max.apply(null, all.map(function (p) { return p[0]; }));
    var y0 = Math.min.apply(null, all.map(function (p) { return p[1]; })), y1 = Math.max.apply(null, all.map(function (p) { return p[1]; }));
    var k = Math.min((W - 60) / Math.max(1, x1 - x0), (H - 40) / Math.max(1, y1 - y0)), ox = W / 2 - (x0 + x1) / 2 * k, oy = H / 2 - (y0 + y1) / 2 * k;
    function P(q) { return [ox + q[0] * k, oy + q[1] * k]; }
    // the axis: the IP's run in, and a north arrow
    out.push(D.line([P([0, y1]), P([0, 0])], C.rule, [1, 3]));
    var na = -hr, nc = [20, 22], nu = [Math.sin(na), -Math.cos(na)], tip = [nc[0] + nu[0] * 9, nc[1] + nu[1] * 9];
    out.push(D.line([[nc[0] - nu[0] * 9, nc[1] - nu[1] * 9], tip], C.muted));
    out.push(D.poly([tip, [tip[0] - nu[0] * 5 - nu[1] * 3, tip[1] - nu[1] * 5 + nu[0] * 3], [tip[0] - nu[0] * 5 + nu[1] * 3, tip[1] - nu[1] * 5 - nu[0] * 3]], C.muted, C.muted));
    out.push(D.txt(nc[0] + nu[0] * 16, nc[1] + nu[1] * 16, "N", C.muted));
    // the tracks: the other role's dashed, yours solid; the points, and the calls
    [mine === "1" ? "2" : "1", mine].forEach(function (r) {
      var pts = pv[r], dim = r !== mine, ps = pts.map(function (q) { return P([q.x, q.y]); });
      out.push(D.line(ps, dim ? C.muted : C.text, dim ? [3, 2] : null));
      pts.forEach(function (q, i) {
        if (q.id === "TGT") return;
        out.push(D.circ(ps[i][0], ps[i][1], dim ? 2 : 3, dim ? C.muted : C.text, dim ? null : C.text));
        out.push(D.txt(ps[i][0] + (q.x < 0 ? -6 : 6), ps[i][1] - 7, q.id, dim ? C.muted : C.hi, q.x < 0 ? "end" : "start", true));
        if (q.call && !dim) out.push(D.txt(ps[i][0] + (q.x < 0 ? -6 : 6), ps[i][1] + 7, ED.nav.cs(+r) + " " + (q.id === "IN" ? "in" : "off"), C.acc, q.x < 0 ? "end" : "start", true));
      });
    });
    var t = P([0, 0]);   // the target: a red triangle, as the card has it
    out.push(D.poly([[t[0], t[1] - 6], [t[0] + 6, t[1] + 5], [t[0] - 6, t[1] + 5]], null, C.bad));
    if (you) {
      var yp = P(you), inside = yp[0] > 4 && yp[0] < W - 4 && yp[1] > 4 && yp[1] < H - 4;
      if (!inside) yp = [clamp(yp[0], 8, W - 8), clamp(yp[1], 8, H - 8)];
      var tr = f.trk != null ? (f.trk - (h || 0)) * RAD : 0;
      out.push(D.shipMark(yp, [Math.sin(tr), -Math.cos(tr)], 4, C.hi));
      if (!inside) out.push(D.txt(yp[0], yp[1] + 10, "You", C.hi));
    }
    out.push(D.txt(W - 4, H - 8, "Atk hdg " + (h != null ? D.deg3(h) + "°" : "auto") + " up", C.muted, "end", true));
    return out.join("");
  }
  function mmss(x) { if (x == null || !isFinite(x)) return "--"; x = Math.round(x); return Math.floor(x / 60) + ":" + String(x % 60).padStart(2, "0"); }
  function planWords() {
    var d = target(), p = plan(), b = built(), why = stale(), pv = preview(), mine = String(p.role || 1), h = hdgSet(), au = autoHdg(), pr = prof();
    $("ak-dname").textContent = d.ok ? d.name : "";
    $("ak-dsub").textContent = d.ok ? "" : d.why || "";
    $("pg-atk").classList.toggle("trnodest", !d.ok);
    $("ak-state").hidden = true;
    $("ak-tr").textContent = pr ? pr.name : "";
    $("ak-pwait").hidden = d.ok;
    $("ak-pwaitt").textContent = d.ok ? "" : d.title;
    $("ak-pwaits").textContent = d.ok ? "" : d.why;
    $("ak-hdgv").textContent = h != null ? D.deg3(h) + "°" : au != null ? "A " + D.deg3(au) + "°" : "Auto";
    $("ak-hdg").classList.toggle("auto", h == null);
    if (A.stepTxt && performance.now() - A.stepAt > 1200) A.stepTxt = "";
    $("ak-hstep").textContent = A.grab ? A.stepTxt || "Turn" : "";
    $("ak-hdga").classList.toggle("off", h == null);
    var chip = $("ak-pchip");
    chip.hidden = !why;
    chip.textContent = why || "";
    chip.style.background = why ? "var(--accent)" : "";
    ["kts", "base", "step"].forEach(function (k) { var el = $("ak-" + k); if (document.activeElement !== el) el.value = p[k] != null ? p[k] : ""; });
    if (document.activeElement !== $("ak-cs")) $("ak-cs").value = p.cs || "";
    $("ak-ms").textContent = p.kts ? Math.round(p.kts * 1852 / 3600) + " m/s" : "";
    Array.prototype.forEach.call($("ak-role").querySelectorAll("button"), function (bt) { bt.textContent = roleName(+bt.dataset.v); });
    $("ak-build").textContent = A.armed ? "Confirm build" : b && !why ? "Built" : "Build";
    $("ak-build").classList.toggle("arm", A.armed);
    $("ak-build").disabled = !d.ok;
    // your points: the built plan's (if it's the plan as set), else the plan as set
    var rows = b && !why ? b.roles[mine].map(function (q) {
      return { id: q.id, from: q.id === "TGT" ? "-" : D.dist(Math.hypot(q.e, q.n)) + " · " + D.deg3(D.n360(Math.atan2(q.e, q.n) / RAD)) + "°", alt: q.alt, secs: q.secs, call: q.call };
    }) : (pv ? pv[mine].map(function (q) {
      var hr = (hdgUse() || 0) * RAD, e = q.x * Math.cos(hr) - q.y * Math.sin(hr), n = -q.x * Math.sin(hr) - q.y * Math.cos(hr);
      return { id: q.id, from: q.id === "TGT" ? "-" : D.dist(Math.hypot(e, n)) + " · " + (hdgUse() != null ? D.deg3(D.n360(Math.atan2(e, n) / RAD)) + "°" : "--"),
               alt: q.alt, secs: q.secs, call: q.call ? q.call.replace("{cs}", ED.nav.cs(+mine)).replace("{from}", "..").replace("{to}", "..") : "" };
    }) : []);
    var sig = JSON.stringify(rows);
    if (sig !== A.ptsSig) {
      A.ptsSig = sig;
      $("ak-pts").innerHTML = '<div class="akpr akph"><span>Pt</span><span>From tgt</span><span>Alt</span><span>Leg on</span></div>' + rows.map(function (q) {
        return '<div class="akpr"><span>' + ED.esc(q.id) + "</span><span>" + ED.esc(q.from) + "</span><span>" + ED.esc(D.dist(q.alt)) + "</span><span>" +
          (q.secs != null ? Math.round(q.secs) + " s" : "") + "</span>" + (q.call ? '<span class="akcall">Call: ' + ED.esc(q.call) + "</span>" : "") + "</div>";
      }).join("");
    }
    var tot = b && !why ? b.tot : pv ? (function () { var o = {}; Object.keys(pv).forEach(function (r) { var s = 0; for (var i = 0; pv[r][i].id !== "TGT"; i++) s += pv[r][i].secs || 0; o[r] = s; }); return o; })() : null;
    $("ak-tot").textContent = tot ? ED.nav.cs(1) + " over the target " + mmss(tot["1"]) + " after START · " + ED.nav.cs(2) + " " + Math.round(tot["2"] - tot["1"]) + " s after " + ED.nav.cs(1) : "";
    var code = b ? b.code : "";
    $("ak-code").textContent = code || "BUILD first";
    $("ak-copy").dataset.clip = code;
    $("ak-copy").disabled = !code;
    if (A.note && Date.now() - A.noteAt > 6000) A.note = "";
    $("ak-bnote").textContent = A.note;
    $("ak-lv").hidden = !A.ul;
    if (A.ul) $("ak-lv").innerHTML = ED.nav.lvHtml(LVOPTS, A.ul.opt || A.ul.armed || null, lvScratch());
    ED.clipShow();
    marks();
    scratch(null, true);
    tellKeys();
  }

  // ---- setting the plan: the mouse and keyboard, the UFC's knobs and its sub-level ----
  function setPlan(body, done) { ED.nav.post(Object.assign({ op: "plan" }, body), function (j) { if (!j.ok) say("Couldn't: " + (j.why || "")); if (done) done(j); }); }
  function flushHdg() { if (A.hdg !== undefined) { var v = A.hdg; setPlan({ hdg: v }, function () { if (A.hdg === v) A.hdg = undefined; }); } }
  function setHdg(v) { A.hdg = v == null ? null : D.n360(Math.round(v)) % 360; A.hdgAt = performance.now(); clearTimeout(A.hdgT); A.hdgT = setTimeout(flushHdg, 400); }
  function turn(clicks) {   // ATK HDG grabbed: each click turns it - more a click the faster they come
    if (!clicks) return;
    var now = performance.now(), dir = clicks > 0 ? 1 : -1, n = Math.abs(clicks);
    var gap = dir === A.lastDir ? (now - A.lastClick) / n : 1e9;
    if (n > 1) gap = Math.min(gap, 60);
    A.lastClick = now; A.lastDir = dir;
    var step = gap < 70 ? 10 : gap < 130 ? 5 : gap < 220 ? 2 : 1, from = hdgUse();
    setHdg((from == null ? 0 : from) + dir * step * n);
    A.stepTxt = (dir > 0 ? "+" : "-") + step * n + "°"; A.stepAt = now;
    if (on()) frame(true);
  }
  function grab(v) { A.grab = v == null ? !A.grab : v; A.focus1 = "hdg"; A.stepTxt = ""; if (!A.grab) flushHdg(); if (on()) frame(true); }
  function setRole(r) { setPlan({ role: r }); }
  function pressBuild() {
    if (!target().ok) { say("No target - designate one"); frame(true); return; }
    if (!A.armed) { A.armed = true; frame(true); return; }
    A.armed = false;
    clearTimeout(A.hdgT);
    var go = function () { ED.nav.post({ op: "build" }, function (j) { say(j.ok ? "Built · ATK HDG " + D.deg3(j.hdg) + "° · the HSI flies it" : "Couldn't build: " + (j.why || "")); frame(true); }); };
    if (A.hdg !== undefined) { var v = A.hdg; setPlan({ hdg: v }, function () { A.hdg = undefined; go(); }); } else go();
  }
  function loadCode() {
    var text = $("ak-loadin").value.trim();
    ED.nav.post(text ? { op: "load", code: text } : { op: "load", clip: true }, function (j) {
      if (j.ok) { $("ak-loadin").value = ""; say("Loaded · you're " + ED.nav.cs() + " · ATK HDG " + D.deg3(j.hdg) + "°"); }
      else say("Couldn't load " + (text ? "that" : "the clipboard") + ": " + (j.why || ""));
      frame(true);
    });
  }
  function stops1() { return A.view === "plan" ? ["view", "hdg", "role", "build"] : ["view"]; }
  function stops2() { return A.view === "plan" ? ["copy", "load"] : ["reset"]; }
  function knob1(clicks) {
    if (A.grab) { turn(clicks); return; }
    var l = stops1(), i = l.indexOf(A.focus1);
    A.focus1 = l[clamp((i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), l.length), 0, l.length - 1)];
    if (A.focus1 !== "build") A.armed = false;
    marks();
  }
  function pull1() {
    var f = A.focus1;
    if (f === "view") setView(A.view === "plan" ? "atk" : "plan");
    else if (f === "hdg") grab();
    else if (f === "role") setRole((plan().role || 1) === 1 ? 2 : 1);
    else if (f === "build") pressBuild();
  }
  function scroll2(clicks) {
    var l = stops2(), i = l.indexOf(A.focus2);
    A.focus2 = l[clamp((i < 0 ? 0 : i) + (clicks > 0 ? 1 : -1) * Math.min(Math.abs(clicks), l.length), 0, l.length - 1)];
    marks();
  }
  function pull2() {
    if (A.view === "atk") { resetScale(); return; }
    if (A.focus2 === "copy") { var c = (built() || {}).code; if (c) ED.clipPress(c, (S.ufc || {}).c2pull_n); }
    else loadCode();
  }
  // the sub-level (ENT): HDG SPD BASE ROLE BLD
  function lvScratch() {
    var L = A.ul, h = hdgSet();
    if (L.armed) return { s1: "", s2: "", num: "CONFIRM" };
    if (L.opt) return { s1: ["HD", "KT", "BS"][L.opt - 1], s2: "", num: L.digits };
    return { s1: "AK", s2: roleName(plan().role || 1), num: h != null ? D.deg3(h) : "AUTO" };
  }
  function lvKey(k) {
    var L = A.ul;
    if (/^Opt[1-5]$/.test(k)) {
      var i = +k.slice(3);
      if (i <= 3) { L.opt = i; L.digits = ""; L.armed = null; }
      else if (i === 4) { L.opt = null; L.armed = null; setRole((plan().role || 1) === 1 ? 2 : 1); }
      else if (L.armed === 5) { L.armed = null; A.armed = true; pressBuild(); }
      else { L.opt = null; L.armed = 5; }
      return;
    }
    if (k === "Clr") { if (L.digits) L.digits = ""; else if (L.opt || L.armed) { L.opt = null; L.armed = null; } else A.ul = null; return; }
    if (k === "Ent") {
      if (L.armed === 5) { L.armed = null; A.armed = true; pressBuild(); return; }
      if (!L.opt) return;
      var v = L.digits === "" ? null : +L.digits;
      if (L.opt === 1) { if (v != null && v >= 360) { say("ATK HDG 0-359 (nothing typed: AUTO)"); return; } A.hdg = undefined; setPlan({ hdg: v }); }
      else if (v == null) { L.opt = null; return; }
      else if (L.opt === 2) { if (v < 60 || v > 3000) { say("Speed 60-3,000 kts"); return; } setPlan({ kts: v }); }
      else { if (v > 20000) { say("BASE 0-20,000 m"); return; } setPlan({ base: v }); }
      L.opt = null; L.digits = "";
      return;
    }
    if (L.opt && /^\d$/.test(k) && L.digits.length < (L.opt === 1 ? 3 : 5)) L.digits += k;
  }
  function key(k) {   // ENT and CLR always; the rest while the sub-level is open
    if (A.ul) lvKey(k);
    else if (k === "Ent") { if (A.view !== "plan") setView("plan"); A.ul = { opt: null, digits: "", armed: null }; }
    frame(true);
  }
  function tellKeys(off) {   // the board: whether the keypad's ours (the sub-level open), and what the UFC shows meanwhile
    var o = !off && !!A.ul && on(), show = { on: o, page: ED.pageId };
    if (o) { var sp = lvScratch(); show.s1 = sp.s1; show.s2 = sp.s2; show.num = sp.num; show.opts = LVOPTS; show.cue = A.ul.opt || A.ul.armed || null; }
    var sig = JSON.stringify(show);
    if (sig === A.ktold) return;
    A.ktold = sig;
    try { fetch("/api/keypad", { method: "POST", headers: { "Content-Type": "application/json" }, body: sig }).catch(function () {}); } catch (e) { /* nothing to tell */ }
  }

  // ---- the frame ----
  function frame(force) {
    var now = performance.now();
    $("ak-atk").hidden = A.view !== "atk";
    $("ak-pv").hidden = A.view !== "plan";
    if (A.view === "plan") {
      D.paint("ak-geo", geoSvg);
      if (force || now - A.textAt > 200) { A.textAt = now; planWords(); }
      return;
    }
    var g = solve(now / 1000), t1 = performance.now();
    A.g = g; A.at = now;
    D.paint("ak-plan", function (W, H) { return planSvg(W, H, g); });
    var t2 = performance.now();
    D.paint("ak-cue", function (W, H) { return cueSvg(W, H, g); });
    var t3 = performance.now(), wd = force || now - A.textAt > 100;
    if (wd) { A.textAt = now; words(g); $("ak-tr").textContent = "Mines · CCRP"; tellKeys(); }
    A.prof = [t1 - now, t2 - t1, t3 - t2, wd ? performance.now() - t3 : -1];   // (timing log: the sums, each picture, the words)
  }
  function loop(ts) {
    A.raf = 0;
    if (!on() || S.halted || ED.hyper.on()) return;
    var drew = ts - A.frameAt >= (ED.reduce.matches ? 250 : A.view === "plan" ? 100 : 33), a = performance.now();
    if (drew) { A.frameAt = ts; frame(false); }
    if (ED.timing.on() && A.view === "atk") frameRec(ts, drew, a);
    A.raf = requestAnimationFrame(loop);
  }
  // timing log: every frame the browser offers while Atk's ATTACK shows - the time since the last (g), whether it was drawn
  // (d: one in every 33 ms), how long that took (ms; p: the sums, the top-down picture, the cue, the words), and what it drew
  // from: how long since the last position reading the filter had (age; it carries you on as long as the game should take to write again), the
  // countdown and the second timer's angle
  function frameRec(ts, drew, a) {
    var q = function (x, n) { var k = Math.pow(10, n == null ? 1 : n); return Math.round(x * k) / k; };
    var o = { w: ED.timing.wall(ts), g: A.lastTs ? q(ts - A.lastTs) : null, d: drew ? 1 : 0 };
    A.lastTs = ts;
    if (drew) {
      var g = A.g || {}, nav = (ED.traj || {}).nav;
      o.late = q(a - ts); o.ms = q(performance.now() - a);
      o.p = (A.prof || []).map(function (x) { return q(x); });
      if (nav && nav.kx && nav.kx.x) o.age = q(A.at / 1000 - nav.kx.t, 3);
      if (g.ok) {
        o.tau = g.tau == null ? null : q(g.tau, 3); o.gs = q(g.gs); o.alng = q(g.along);
        var bt = beat(g.tau);
        if (bt.on) o.ang = q(bt.angle);
      } else o.st = g.title || "";
    }
    ED.timing.rec("p.fr", o);
  }
  function start() { if (!A.raf && on()) A.raf = requestAnimationFrame(loop); }
  function setView(v) {
    A.view = v; keep(); A.armed = false; A.grab = false;
    if (v !== "plan" && A.ul) { A.ul = null; tellKeys(); }   // (the sub-level is PLAN's: leaving it closes it, and gives the keypad back)
    if (stops1().indexOf(A.focus1) < 0) A.focus1 = "view";
    A.focus2 = stops2()[0];
    if (on()) frame(true);
  }

  $("ak-mode").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { A.focus1 = "view"; setView(b.dataset.v); } });
  $("ak-role").addEventListener("click", function (e) { var b = e.target.closest("button[data-v]"); if (b) { A.focus1 = "role"; setRole(+b.dataset.v); } });
  $("ak-hdg").addEventListener("click", function () { grab(); });
  $("ak-hdg").addEventListener("wheel", function (e) {   // the mouse wheel turns it, like the knob, while it's grabbed
    if (!A.grab) return;
    e.preventDefault();
    var now = performance.now();
    if (now - (A.wheelAt || 0) > 300) A.wheelAcc = 0;
    A.wheelAt = now;
    A.wheelAcc = (A.wheelAcc || 0) + e.deltaY;
    if (Math.abs(A.wheelAcc) >= 40) { turn(A.wheelAcc < 0 ? 1 : -1); A.wheelAcc = 0; }
  }, { passive: false });
  $("ak-hdgm").addEventListener("click", function () { var h = hdgUse(); setHdg((h == null ? 0 : h) - 1); frame(true); });
  $("ak-hdgp").addEventListener("click", function () { var h = hdgUse(); setHdg((h == null ? 0 : h) + 1); frame(true); });
  $("ak-hdga").addEventListener("click", function () { clearTimeout(A.hdgT); A.hdg = undefined; setPlan({ hdg: null }); });
  ["kts", "base", "step"].forEach(function (k) {
    var el = $("ak-" + k);
    function take() { var v = parseFloat(el.value); if (isFinite(v)) setPlan(JSON.parse('{"' + k + '":' + v + "}")); }
    el.addEventListener("change", take);
    el.addEventListener("keydown", function (e) { if (e.key === "Enter") { take(); el.blur(); } });
  });
  $("ak-cs").addEventListener("change", function () { setPlan({ cs: $("ak-cs").value }); });
  $("ak-build").addEventListener("click", function () { A.focus1 = "build"; pressBuild(); });
  $("ak-load").addEventListener("click", loadCode);
  $("ak-loadin").addEventListener("keydown", function (e) { if (e.key === "Enter") loadCode(); });
  $("ak-reset").addEventListener("click", resetScale);
  $("ak-plan").parentNode.addEventListener("wheel", function (e) {
    e.preventDefault();
    zoomBy(Math.pow(1.0015, -e.deltaY * (e.deltaMode === 1 ? 33 : 1)));
  }, { passive: false });
  window.addEventListener("resize", function () { if (on()) frame(true); });

  ED.atk = A;   // (its working state: for the tests)
  ED.atkSolve = function () { return solve(performance.now() / 1000); };
  ED.atkBeat = function () { return beat(solve(performance.now() / 1000).tau); };
  ED.atkPreview = preview;
  ED.atkModel = { CARRY: CARRY, fall: fall, throwOf: throwOf };   // (for the tests)
  ED.page({
    tab: "nav", sub: 6, key: 5, label: "Atk", el: "pg-atk", mode: "atk", back: "2 Nav · Atk",
    update: function (s) {   // a new target: the scale's the auto one again
      A.y = s.syst || {};
      var d = target();
      if (A.zoom && d && d.key && d.key !== A.zoomKey) { A.zoom = null; A.zoomKey = null; }
    },
    draw: function () { frame(true); start(); },
    enter: function () { if (stops1().indexOf(A.focus1) < 0) A.focus1 = "view"; start(); },
    leave: function () { scratch(null, true); A.ul = null; A.grab = false; A.armed = false; flushHdg(); tellKeys(true); },
    cursor: function () { marks(); },
    knob1: knob1, pull1: pull1,      // COMM1: PLAN / ATTACK, ATK HDG, ROLE, BUILD
    scroll: scroll2, pull: pull2,    // COMM2: COPY, LOAD (ATTACK: RESET SCALE)
    keypad: key,
    dsg: function () { say("DSG: on Wpt, HSI or 1 Syst"); frame(true); },
    dial: function (r, dt) {   // the COMM1 VOLUME dial zooms the top-down view (4 times a second at full turn)
      var cue = { z: "", t: "" };
      if (A.view === "atk" && r.zoom && zoomBy(Math.exp(Math.log(4) * r.zoom * dt))) cue.z = r.zoom > 0 ? "Z+" : "Z-";
      return cue;
    }
  });
})();
