// ED Target Board page - Overlay: hyperspace jumps.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- System tab: the hyperspace overlay ----
  // From StartJump until arrival the tab shows the jump: a judder and blur as the drive fires, then
  // candidate paths try to join the two stars through folded space. The fold is drawn from the paths
  // themselves: at every point between the stars its width is two standard deviations of where the
  // paths are, so while they're wild it's wide, and it tightens with them as the plot converges.
  // The route locks, your marker sets off, and the destination's system map (Spansh's) scans in. FSDJump: a last
  // judder and flash, then the page is back in the view you left it in. Stars are drawn at the map's
  // own scale and style, so their relative size and type show; a star known only by its class is
  // drawn at a typical size for that class until Spansh (or your journal) gives the real figures.
  var HY = { J: 1.5, LOCK: 7.5, SCHEM: 9.5, ARRIVE: 3.4, X: 1.7, XS: 0.92, NS: 25 };   // ARRIVE: seconds from arrival to closing
  S.hy = { id: null, start: 0, arrivedAt: 0, done: null, cands: [], rf: null, raf: 0, last: 0, on: false, j: null, sig: "" };

  function hyEnv(s) { return 0.1 + 0.55 * Math.pow(Math.abs(2 * s - 1), 1.4); }   // spread profile: wide by the stars, narrow mid-way
  function hyMin(s) { return 0.035 + 0.16 * Math.pow(Math.abs(2 * s - 1), 1.6); }  // the fold once the route has locked
  function hyMess(t) {   // how wild the paths are: falls while plotting, gone once locked
    if (t < HY.J) return 1;
    if (t < HY.LOCK) { var u = (t - HY.J) / (HY.LOCK - HY.J); return 1 - 0.78 * (u * u * (3 - 2 * u)); }
    return 0.22 * Math.max(0, 1 - (t - HY.LOCK) / 1.6);
  }
  function hyBody(star, key) {   // a star record -> what the map drawing takes
    var st = star || {};
    return { key: key, name: key, star: true, sub: st.sub || "Star", cls: st.cls || "", km: (st.rsol || 1) * 695700,
             rot: st.rot || 3, tilt: st.tilt || 0, rings: [], belts: [] };
  }
  function hyNode(star, key, r, x, y) {
    var b = hyBody(star, key), cache = S.hy.nodes || (S.hy.nodes = {}), sig = key + JSON.stringify(star);
    var n = cache[sig] || (cache[sig] = { t: "body", d: b, st: ED.mapStyle(b), key: key, phase: key === "dep" ? 0.4 : 2.1 });
    n.hw = n.hh = r; n.x = x; n.y = y;
    if (n.r0 !== r) { n.r0 = r; n.feats = null; n.rings = null; }
    return n;
  }
  function hyCam(w, h, t) {
    var yaw = 0.5 + 0.035 * Math.sin(t * 0.21), pitch = 0.3, roll = -0.17, D = 5.2;
    var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch), cr = Math.cos(roll), sr = Math.sin(roll);
    var unit = function (x, y, z) {
      var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
      var y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      var k = D / (D + z2), px = x1 * k, py = y2 * k;
      return [px * cr - py * sr, -(px * sr + py * cr), z2];
    };
    // scale so both stars sit a margin in from the sides, and centre the route between them
    var a = unit(-HY.XS, 0, 0), b = unit(HY.XS, 0, 0), m = Math.max(150, w * 0.11);
    var sc = Math.min((w - 2 * m) / (b[0] - a[0]), h * 1.15), ox = w / 2 - (a[0] + b[0]) / 2 * sc, oy = h / 2 - (a[1] + b[1]) / 2 * sc;
    var P = function (x, y, z) { var q = unit(x, y, z); return [ox + q[0] * sc, oy + q[1] * sc, q[2]]; };
    P.sc = sc;
    return P;
  }
  function hyFoldR(x) {   // the fold's radius along its axis: the paths' spread between the stars, flaring beyond them
    var rf = S.hy.rf, XS = HY.XS;
    if (Math.abs(x) <= XS) {
      var f = (x + XS) / (2 * XS) * (HY.NS - 1), i = Math.min(HY.NS - 2, Math.floor(f)), k = f - i;
      return rf[i] * (1 - k) + rf[i + 1] * k;
    }
    var edge = x < 0 ? rf[0] : rf[HY.NS - 1];
    return edge + 1.5 * Math.pow((Math.abs(x) - XS) / (HY.X - XS), 1.6);
  }
  function hyRuns(ctx, pts, aFront, aBack) {
    [true, false].forEach(function (front) {
      ctx.beginPath();
      var on = false;
      for (var i = 0; i < pts.length; i++) {
        var q = pts[i];
        if ((q[2] <= 0) === front) { if (on) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); on = true; } else on = false;
      }
      ctx.globalAlpha = front ? aFront : aBack; ctx.stroke();
    });
    ctx.globalAlpha = 1;
  }
  function hyFold(ctx, P, t, dim) {
    ctx.lineWidth = 1; ctx.setLineDash([]); ctx.strokeStyle = ED.MAP.green;
    var X = HY.X, XS = HY.XS, i, j, pts;
    for (j = 0; j < 34; j++) {   // lines running through the fold
      var th = j / 34 * 2 * Math.PI + t * 0.09; pts = [];
      for (i = 0; i <= 90; i++) { var x = -X + i / 90 * 2 * X, r = hyFoldR(x); pts.push(P(x, r * Math.cos(th), r * Math.sin(th))); }
      hyRuns(ctx, pts, 0.42 * dim, 0.13 * dim);
    }
    var xs = [];
    for (i = -9; i <= 9; i++) xs.push(Math.sign(i) * Math.pow(Math.abs(i) / 9, 1.3) * XS);   // rings, closer near the throat
    for (i = 1; i <= 4; i++) { var o = XS + i / 4 * (X - XS); xs.push(o, -o); }
    xs.forEach(function (xr) {
      var rr = hyFoldR(xr); pts = [];
      for (j = 0; j <= 64; j++) { var a = j / 64 * 2 * Math.PI; pts.push(P(xr, rr * Math.cos(a), rr * Math.sin(a))); }
      hyRuns(ctx, pts, 0.36 * dim, 0.1 * dim);
    });
  }
  var HY_ICO = (function () {
    var g = (1 + Math.sqrt(5)) / 2, V = [[-1, g, 0], [1, g, 0], [-1, -g, 0], [1, -g, 0], [0, -1, g], [0, 1, g], [0, -1, -g], [0, 1, -g], [g, 0, -1], [g, 0, 1], [-g, 0, -1], [-g, 0, 1]], E = [];
    for (var a = 0; a < 12; a++) for (var b = a + 1; b < 12; b++) {
      if (Math.abs(Math.hypot(V[a][0] - V[b][0], V[a][1] - V[b][1], V[a][2] - V[b][2]) - 2) < 1e-6) E.push([a, b]);
    }
    var L = Math.hypot(1, g);
    return { V: V.map(function (v) { return [v[0] / L, v[1] / L, v[2] / L]; }), E: E };
  })();
  function hyRot(v, ax, ay, az) {
    var x = v[0], y = v[1], z = v[2], c, s, q;
    c = Math.cos(ax); s = Math.sin(ax); q = y * c - z * s; z = y * s + z * c; y = q;
    c = Math.cos(ay); s = Math.sin(ay); q = x * c + z * s; z = -x * s + z * c; x = q;
    c = Math.cos(az); s = Math.sin(az); q = x * c - y * s; y = x * s + y * c; x = q;
    return [x, y, z];
  }
  function hyCage(ctx, P, cx, t, rad, speed, col, dim) {   // an icosahedron cage and two rings turning round a star
    var a = t * speed, i, pts;
    ctx.setLineDash([3, 2]); ctx.lineWidth = 1; ctx.strokeStyle = ED.MAP.hi;
    HY_ICO.E.forEach(function (e) {
      var p = hyRot(HY_ICO.V[e[0]], a * 0.7, a, a * 0.3), q = hyRot(HY_ICO.V[e[1]], a * 0.7, a, a * 0.3);
      var A = P(cx + p[0] * rad, p[1] * rad, p[2] * rad), B = P(cx + q[0] * rad, q[1] * rad, q[2] * rad);
      ctx.globalAlpha = ((p[2] + q[2]) / 2 < 0 ? 0.8 : 0.28) * dim;
      ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke();
    });
    [[1.0, 0.9, 0], [-0.8, 0.4, 1.1]].forEach(function (tl, k) {
      pts = [];
      for (i = 0; i <= 60; i++) {
        var u = i / 60 * 2 * Math.PI, v = hyRot([Math.cos(u) * 1.25, 0, Math.sin(u) * 1.25], tl[0] - a * 0.5, tl[1] + (k ? a : -a) * 0.8, tl[2]);
        pts.push(P(cx + v[0] * rad, v[1] * rad, v[2] * rad));
      }
      ctx.setLineDash(k ? [6, 3] : [2, 3]); ctx.strokeStyle = col;
      ctx.beginPath(); pts.forEach(function (q, n) { if (n) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
      ctx.globalAlpha = 0.5 * dim; ctx.stroke();
    });
    ctx.globalAlpha = 1; ctx.setLineDash([]);
  }

  // the candidate paths
  function hyBase(s) { return [-HY.XS + 2 * HY.XS * s, 0.12 * Math.sin(2 * Math.PI * s), 0.04 * Math.sin(Math.PI * s)]; }
  function hyCand(t, seed) {
    var R = ED.mapRng(seed);
    return { born: t + R() * 0.5, reachMax: 0.35 + R() * 0.62, speed: 0.25 + R() * 0.35, hold: 0.25 + R() * 0.7,
             f1: 4 + R() * 8, f2: 9 + R() * 12, p1: R() * 6, p2: R() * 6, s1: 0.6 + R() * 1.6, s2: 0.8 + R() * 2, g: 0.7 + R() * 0.6, seed: seed, failAt: null };
  }
  function hyOff(c, s, t, m) {   // a path's offset from the straight route at s (0 = departure, 1 = destination)
    var e = hyEnv(s) * m * c.g;
    return [e * (Math.sin(s * c.f1 + c.p1 + t * c.s1) + 0.5 * Math.sin(s * c.f2 + c.p2 - t * c.s2)),
            e * (Math.cos(s * c.f2 * 0.7 + c.p2 + t * c.s2) + 0.4 * Math.sin(s * c.f1 * 1.3 - t * c.s1))];
  }
  function hyPathPts(c, t, reach, m) {
    var pts = [], n = 70;
    for (var i = 0; i <= n * reach; i++) { var s = i / n, b = hyBase(s), o = hyOff(c, s, t, m); pts.push([b[0], b[1] + o[0], b[2] + o[1]]); }
    return pts;
  }
  function hyStroke(ctx, P, pts, col, alpha, dash, off, width, from) {
    if (pts.length < 2) return;
    var first = P(pts[0][0], pts[0][1], pts[0][2]);
    if (from) {   // a faint thread from the star to where the path sets off
      ctx.setLineDash([1, 3]); ctx.lineWidth = 1; ctx.strokeStyle = col; ctx.globalAlpha = alpha * 0.5;
      ctx.beginPath(); ctx.moveTo(from[0], from[1]); ctx.lineTo(first[0], first[1]); ctx.stroke();
    }
    ctx.setLineDash(dash); ctx.lineDashOffset = off; ctx.lineWidth = width; ctx.strokeStyle = col; ctx.globalAlpha = alpha;
    ctx.beginPath();
    pts.forEach(function (q, i) { var p = P(q[0], q[1], q[2]); if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
    ctx.stroke();
    var e = P(pts[pts.length - 1][0], pts[pts.length - 1][1], pts[pts.length - 1][2]);
    ctx.setLineDash([]); ctx.fillStyle = col; ctx.fillRect(e[0] - 2, e[1] - 2, 4, 4);
    ctx.globalAlpha = 1; ctx.lineDashOffset = 0;
  }
  // the fold follows the paths: two standard deviations of their offsets at each point, smoothed
  function hySpread(live, t, m, locked) {
    var rf = S.hy.rf, NS = HY.NS;
    for (var i = 0; i < NS; i++) {
      var s = i / (NS - 1), sum = 0, n = 0, target;
      if (!locked) live.forEach(function (c) {
        if (c.reach < s) return;
        var o = hyOff(c, s, t, m);
        sum += o[0] * o[0] + o[1] * o[1]; n++;
      });
      target = locked ? hyMin(s) : n ? Math.max(hyMin(s), 2 * Math.sqrt(sum / n / 2) * 1.6) : rf[i];
      rf[i] += (target - rf[i]) * 0.1;
    }
  }
  function hySearch(ctx, P, t, m, fade, A) {
    var cs = S.hy.cands, live = [];
    while (cs.length < 8) cs.push(hyCand(t, (Math.random() * 1e9) | 0));
    cs.forEach(function (c, i) {
      var tau = t - c.born;
      if (tau < 0) return;
      var reach = Math.min(c.reachMax, tau * c.speed + 0.03 * Math.sin(tau * 9 + c.p1)), col = ED.MAP.hi, a = 0.75, dash = [5, 4];
      if (reach >= c.reachMax - 0.005 && c.failAt === null) c.failAt = t + c.hold;
      if (c.failAt !== null && t > c.failAt) {   // gives up: goes amber, breaks up and pulls back
        var f = (t - c.failAt) / 0.7;
        if (f >= 1) { cs[i] = hyCand(t, c.seed * 7 + 13); return; }
        reach = c.reachMax * (1 - f * 0.8); col = ED.MAP.amber; a = 0.8 * (1 - f) * (Math.random() < 0.15 ? 0.3 : 1); dash = [2, 5 + f * 8];
      }
      c.reach = Math.max(0, reach);
      live.push(c);
      hyStroke(ctx, P, hyPathPts(c, t, c.reach, m), col, a * fade, dash, -t * 30, 1.2, A);
    });
    return live;
  }
  function hyLocked(ctx, P, t, m, k, travel) {   // the route that won, straightening as the spread goes
    var win = { f1: 7, f2: 13, p1: 1, p2: 2, s1: 1.1, s2: 1.4, g: 1 };
    var pts = hyPathPts(win, t, Math.min(1, 0.55 + k * 0.6), m);
    ctx.save(); ctx.shadowColor = ED.MAP.hi; ctx.shadowBlur = 10 * k;
    hyStroke(ctx, P, pts, ED.MAP.hi, 0.95, [12, 7], -t * 42, 2.4);
    ctx.restore();
    if (travel !== null) {   // you
      var q = hyBase(travel), o = hyOff(win, travel, t, m), p = P(q[0], q[1] + o[0], q[2] + o[1]);
      ctx.save(); ctx.shadowColor = "#ffffff"; ctx.shadowBlur = 12; ctx.fillStyle = "#f2fff6"; ctx.fillRect(p[0] - 5, p[1] - 5, 10, 10); ctx.restore();
    }
    var th = P(0, 0, 0);
    ctx.strokeStyle = ED.MAP.amber; ctx.lineWidth = 1; ctx.globalAlpha = 0.8 * k;
    ctx.beginPath(); ctx.moveTo(th[0] - 9, th[1]); ctx.lineTo(th[0], th[1] - 9); ctx.lineTo(th[0] + 9, th[1]); ctx.lineTo(th[0], th[1] + 9); ctx.closePath(); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  function hyStar(ctx, star, key, p, r, t, dim) {   // the board's own star drawing, with a soft glow
    var n = hyNode(star, key, r, p[0], p[1]), est = star && star.estimate;
    var g = ctx.createRadialGradient(p[0], p[1], r * 0.6, p[0], p[1], r * 2.6);
    g.addColorStop(0, n.st.col); g.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.globalAlpha = 0.22 * dim; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p[0], p[1], r * 2.6, 0, 2 * Math.PI); ctx.fill();
    ctx.globalAlpha = (est ? 0.55 + 0.15 * Math.sin(t * 6) : 1) * dim;
    ctx.save(); ED.mapBody(ctx, n, t); ctx.restore();
    ctx.globalAlpha = 1;
  }
  function hyTag(ctx, p, r, name, role, left) {
    var nx = left ? p[0] - r - 26 : p[0] + r + 26, ny = p[1] - r - 46;
    ctx.font = "16px VGA"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
    var w1 = ctx.measureText(name.toUpperCase()).width + 14, h1 = 22, bx = left ? nx - w1 : nx;
    ctx.strokeStyle = ED.MAP.hi; ctx.lineWidth = 1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(p[0] + (left ? -r * 0.7 : r * 0.7), p[1] - r * 0.7); ctx.lineTo(left ? bx + w1 : bx, ny + h1); ctx.stroke();
    ctx.fillStyle = "rgba(6, 6, 6, 0.85)"; ctx.fillRect(bx, ny, w1, h1); ctx.strokeRect(bx + 0.5, ny + 0.5, w1 - 1, h1 - 1);
    ctx.fillStyle = ED.MAP.hi; ctx.fillText(name.toUpperCase(), bx + 7, ny + h1 / 2 + 1);
    ctx.fillStyle = ED.MAP.grid; ctx.textAlign = left ? "right" : "left"; ctx.fillText(role, left ? bx + w1 : bx, ny + h1 + 12);
  }
  function hyRuler(ctx, w, P, ly) {   // light years along the top, departure to destination
    var a = P(-HY.XS, 0, 0), b = P(HY.XS, 0, 0);
    ctx.strokeStyle = "#26603a"; ctx.fillStyle = ED.MAP.grid; ctx.font = "16px VGA"; ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.lineWidth = 1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(0, 22.5); ctx.lineTo(w, 22.5); ctx.stroke();
    if (!ly) { ctx.fillText("DISTANCE NOT KNOWN YET", w / 2, 4); return; }
    var step = ly > 60 ? 10 : ly > 25 ? 5 : 1, big = ly > 60 ? 20 : ly > 25 ? 10 : 5;
    for (var v = -3 * big; v <= ly + 3 * big; v += step) {
      var x = a[0] + (b[0] - a[0]) * v / ly;
      if (x < 4 || x > w - 4) continue;
      ctx.beginPath(); ctx.moveTo(x, 22.5); ctx.lineTo(x, v % big === 0 ? 30 : 26); ctx.stroke();
      if (v % big === 0 && v >= 0 && v <= ly - big * 0.6) ctx.fillText(String(v), x, 4);
    }
    ctx.fillStyle = ED.MAP.amber; ctx.fillText(ly.toFixed(2) + " LY", Math.min(w - 44, b[0]), 4);
  }
  function hySchematic(ctx, w, h, t, reveal, lay, j) {   // the destination's map (the Syst map's own drawing) in a band
    var top = 32, bh = h - top - 4, pad = 8;
    ctx.fillStyle = "rgba(10, 12, 10, 0.92)"; ctx.fillRect(0, top, w * reveal, bh);
    ctx.strokeStyle = "#26603a"; ctx.lineWidth = 1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(0, top + 0.5); ctx.lineTo(w * reveal, top + 0.5); ctx.moveTo(0, top + bh - 0.5); ctx.lineTo(w * reveal, top + bh - 0.5); ctx.stroke();
    var z = Math.min((bh - 2 * pad - 14) / lay.H, (w - 2 * pad) / lay.W, 1.6), ox = (w - lay.W * z) / 2, oy = top + (bh - 14 - lay.H * z) / 2;
    ctx.save();
    ctx.beginPath(); ctx.rect(0, top, w * reveal, bh); ctx.clip();
    ctx.translate(ox, oy); ctx.scale(z, z);
    ED.mapScene(ctx, lay, t, { bg: "rgb(10, 12, 10)" });   // the system map drawing (shared with the Syst map)
    ctx.restore();
    if (reveal < 1) { ctx.fillStyle = ED.MAP.hi; ctx.globalAlpha = 0.9; ctx.fillRect(w * reveal - 2, top, 3, bh); ctx.globalAlpha = 1; }
    var sv = j.survey || {};
    ctx.font = "16px VGA"; ctx.fillStyle = ED.MAP.grid; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
    ctx.fillText(String(sv.src || "Spansh").toUpperCase() + " SURVEY · " + String(j.to).toUpperCase() + " · " + (sv.bodies || 0) + " BODIES · " + (sv.stations || 0) + " STATIONS" + (sv.carriers ? " · " + sv.carriers + " CARRIERS" : ""), 10, top + bh - 4);
  }
  function hyNotice(ctx, w, h, text, warn) {   // no schematic (yet): a boxed line under the fold
    ctx.font = "16px VGA"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    var tw = ctx.measureText(text).width + 24, y = h - 30;
    ctx.fillStyle = "rgba(6, 6, 6, 0.9)"; ctx.fillRect(w / 2 - tw / 2, y - 13, tw, 26);
    ctx.strokeStyle = warn ? ED.MAP.amber : ED.MAP.green; ctx.lineWidth = 1; ctx.setLineDash([]); ctx.strokeRect(w / 2 - tw / 2 + 0.5, y - 12.5, tw - 1, 25);
    ctx.fillStyle = warn ? ED.MAP.amber : ED.MAP.hi; ctx.fillText(text, w / 2, y + 1);
  }

  // ---- what shows, and when ----
  function hyPhase(t) {
    if (S.hy.arrivedAt) return "A";
    return t < HY.J ? "J" : t < HY.LOCK ? "P" : t < HY.SCHEM ? "L" : "S";
  }
  function hyFmt(v, d) { return v == null || isNaN(v) ? "…" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: d }); }
  function hyStarText(st) {   // "K2 V · Yellow-Orange", "DA · White Dwarf (DA) star"
    if (!st) return "Unknown star";
    var sub = String(st.sub || "Star"), m = /^([A-Z]+) \((.+)\) Star$/.exec(sub);
    var name = m ? m[2] : sub.replace(/ Star$/, " star");
    return [st.cls, st.lum].filter(Boolean).join(" ") + (st.cls ? " · " : "") + name;
  }
  function hyDataText(st, survey, src) {   // where a star's figures came from (src: where the survey comes from)
    src = src || "Spansh";
    if (st && st.source === "journal") return "Your scan";
    if (st && st.source === "edsm") return "EDSM";
    if (st && st.source === "spansh") return "Spansh";
    return survey === "none" ? "Not in " + src : survey === "error" ? src + " unreachable" : survey === "off" ? "Class only" : "Awaiting " + src;
  }
  function hyRows(st, extra) {
    var est = !st || st.estimate, h = "";
    function row(l, v, wait) { h += "<span>" + ED.esc(l) + '</span><span class="v' + (wait ? " wait" : "") + '">' + ED.esc(v) + "</span>"; }
    row("Temperature", est || !st.temp ? "…" : hyFmt(st.temp, 0) + " K", est || !st.temp);
    row("Radius", (est ? "~" : "") + hyFmt(st && st.rsol, st && st.rsol < 0.1 ? 3 : 2) + " suns", est);   // ~ and amber: typical for the class
    row("Mass", est || !st.mass ? "…" : hyFmt(st.mass, 2) + " suns", est || !st.mass);
    if (extra) row(extra[0], extra[1], extra[2]);
    return h;
  }
  function hyPanels(j, t, ph) {
    var sv = (j.survey || {}).status, locked = ph === "S" || ph === "A" || (ph === "L" && t > HY.LOCK + 0.8);
    var active = ph === "J" ? 2 : ph === "A" ? 5 : 3;
    var src = (j.survey || {}).src || "Spansh";
    var survey = sv === "ok" ? "OK" : sv === "none" ? "NOT IN " + src.toUpperCase() : sv === "error" ? "UNREACHABLE" : sv === "off" ? "OFF" : "FETCHING";
    var names = ["Route solution", "Mass alignment", "Fold initiation", "Hyperspace transit", "System survey · " + src, "Arrival"];
    var stat = names.map(function (n, i) { return i === 4 ? survey : i < active ? "OK" : i === active ? "ACTIVE" : "PENDING"; });
    var sig = [j.id, ph, locked, survey, JSON.stringify(j.to_star), j.fuel_used, j.ly, j.fuel_now].join("|");
    if (sig === S.hy.sig) return;
    S.hy.sig = sig;
    $("hy-list").innerHTML = names.map(function (n, i) {
      var ok = stat[i] === "OK" || stat[i] === "ACTIVE";
      return '<div class="' + (i === active ? "act" : "") + '"><span class="o">' + (i + 1) + "</span><span>" + n + '</span><span class="s' + (ok ? "" : " wait") + '">' + stat[i] + "</span></div>";
    }).join("");
    $("hy-state").textContent = ph === "J" ? "FSD fold initiating" : ph === "P" ? "Plotting route" : ph === "A" ? "Arriving" :
      locked ? (sv === "ok" ? "Route locked · surveyed" : "Route solution locked") : "Locking route";
    $("hy-state").className = "state" + (locked ? " ok" : "");
    var checks = [["Calculated", "OK"], ["Mass correction", ph === "J" ? "…" : "OK"],
                  ["Phase alignment", ph === "J" || ph === "P" ? "…" : "OK"], ["Transit vector", locked || ph === "L" ? "LOCKED" : "SEARCHING"]];
    $("hy-checks").innerHTML = checks.map(function (c) { return "<span>" + c[0] + '</span><span class="v' + (c[1] === "OK" || c[1] === "LOCKED" ? "" : " wait") + '">' + c[1] + "</span>"; }).join("");
    $("hy-dep-nm").textContent = j.from || "Departure";
    $("hy-dep-sub").textContent = hyStarText(j.dep_star);
    $("hy-dep-rows").innerHTML = hyRows(j.dep_star, ["Data", hyDataText(j.dep_star, "", src), j.dep_star && j.dep_star.estimate]);
    $("hy-dst-nm").textContent = j.to;
    $("hy-dst-sub").textContent = hyStarText(j.to_star);
    $("hy-dst-rows").innerHTML = hyRows(j.to_star, ["Data", hyDataText(j.to_star, sv, src), j.to_star && j.to_star.estimate]);
    $("hy-o").textContent = j.from || "-";
    $("hy-d").textContent = j.to;
    $("hy-ly").textContent = j.ly ? j.ly.toFixed(2) + " LY" : "";
    // fuel: what's in the tank, the slice this jump burns, what's left (exact once you've arrived)
    var cap = j.fuel_cap, fuelBox = $("hy-fuel");
    fuelBox.hidden = !!j.taxi || !cap;
    if (!j.taxi && cap) {
      var arrived = j.fuel_used != null && j.fuel_level != null, before = j.fuel_before, use = arrived ? j.fuel_used : j.fuel_est;
      var left = arrived ? j.fuel_level : (before != null && use != null ? before - use : before);
      var pct = function (v) { return Math.max(0, Math.min(100, (v || 0) / cap * 100)); };
      $("hy-fl").style.width = pct(left) + "%";
      $("hy-fu").style.width = (use > 0 ? Math.max(0.8, pct(use)) : 0) + "%";   // a sliver at least, so a short hop still shows
      $("hy-fu").className = "fu" + (arrived ? " done" : "");
      $("hy-ft").textContent = arrived ? "Used " + use.toFixed(2) + " t · " + left.toFixed(1) + " / " + Math.round(cap) + " t left"
        : (before != null ? before.toFixed(1) + " / " + Math.round(cap) + " t" : "? / " + Math.round(cap) + " t") +
          (use != null ? " · jump ≈" + use.toFixed(2) + " t" : " · jump cost known after a jump") +
          (j.route_left ? " · " + j.route_left + " more in route" : "");
      fuelBox.title = arrived ? "From the journal (FSDJump)" : j.fuel_how === "measured" ? "Estimated from your recent jumps with this drive" :
        j.fuel_how ? "Estimated from the drive's standard figures" : "";
    }
  }

  function renderHyper(s) {
    var j = s.jump, now = Date.now();
    if (j && j.id !== S.hy.id) {   // a new jump: start its clock from the journal's times (whatever this device's clock says)
      var lag = Math.max(0, (Date.parse(j.now) - Date.parse(j.started)) / 1000);
      S.hy.id = j.id; S.hy.start = now - Math.min(lag, 60) * 1000; S.hy.arrivedAt = 0; S.hy.cands = []; S.hy.rf = null;
      S.hy.sig = ""; S.hy.lay = null; S.hy.laySig = ""; S.hy.schemAt = 0;
      if (j.arrived && Date.parse(j.now) - Date.parse(j.arrived) > 2500) S.hy.done = j.id;   // opened after it was over
    }
    if (j && j.arrived && !S.hy.arrivedAt && S.hy.done !== j.id) {   // out of hyperspace: play the arrival from now (journal times are whole seconds)
      if (Date.parse(j.now) - Date.parse(j.arrived) > 6000) S.hy.done = j.id; else S.hy.arrivedAt = now;
    }
    S.hy.j = j;
    var on = !!j && S.hy.done !== j.id, was = S.hy.on;   // whichever tab is showing
    S.hy.on = on;
    $("app").classList.toggle("hyper", on);
    if (!on) {
      if (was) { $("hy").style.transform = ""; $("hy").style.filter = ""; ED.resume(); }   // jump called off: the page underneath picks up again
      return;
    }
    var sv = j.survey || {};
    if (sv.status === "ok" && sv.map) {
      var lsig = j.to + "|" + (sv.map.bodies || []).length + "|" + (sv.map.stations || []).length;
      if (lsig !== S.hy.laySig) { S.hy.laySig = lsig; S.hy.lay = ED.mapLayout(sv.map); }
    }
    var t = (now - S.hy.start) / 1000;
    hyPanels(j, t, hyPhase(t));
    hyKick();
  }
  function hyKick() { if (!S.hy.raf && S.hy.on && !S.halted && !document.hidden) S.hy.raf = requestAnimationFrame(hyFrame); }
  function hyFrame(now) {
    S.hy.raf = 0;
    if (!S.hy.on || S.halted || document.hidden) return;
    S.hy.raf = requestAnimationFrame(hyFrame);
    if (now - S.hy.last < 30) return;
    S.hy.last = now;
    var j = S.hy.j, t = (Date.now() - S.hy.start) / 1000, ph = hyPhase(t), still = reduce.matches;
    if (still) t = Math.max(t, HY.SCHEM + 2);
    if (ph === "A" && Date.now() - S.hy.arrivedAt > HY.ARRIVE * 1000) {   // arrived: back to the tab as it was
      S.hy.done = j.id; S.hy.on = false;
      $("app").classList.remove("hyper"); $("hy").style.transform = ""; $("hy").style.filter = "";
      if (S.data) ED.render(S.data);
      return;
    }
    var cv = $("hy-cv"), w = cv.clientWidth, h = cv.clientHeight;
    if (!w || !h) return;
    if (S.hy.fw !== w || S.hy.fh !== h) {   // a new size: a new star field for it
      S.hy.fw = w; S.hy.fh = h;
      var R = ED.mapRng(5); S.hy.field = [];
      for (var i = 0; i < 200; i++) S.hy.field.push([R() * w, R() * h, R() * 1.4 + 0.4, R() * 6]);
    }
    var ctx = ED.pixel.layers(cv, w, h);   // lines in coarse pixels, writing over them in full
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, w, h);
    if (!S.hy.rf) { S.hy.rf = []; for (var k = 0; k < HY.NS; k++) S.hy.rf.push(2.6 * hyEnv(k / (HY.NS - 1))); }   // starts wide
    // judder as the drive fires, and again on arrival
    var at = ph === "A" ? (Date.now() - S.hy.arrivedAt) / 1000 : 0;
    var jt = still ? 0 : ph === "J" ? 1 - t / HY.J : ph === "A" ? Math.min(1, at / 0.3) * Math.max(0, 1 - Math.max(0, at - 0.9) / 0.6) : 0;
    var hy = $("hy");
    if (jt > 0) {
      var amp = 12 * jt;
      hy.style.transform = "translate(" + ((Math.random() - 0.5) * amp).toFixed(1) + "px," + ((Math.random() - 0.5) * amp * 0.6).toFixed(1) + "px)";
      hy.style.filter = "blur(" + (5 * jt).toFixed(2) + "px) brightness(" + (1 + 0.6 * jt * Math.random() + (ph === "A" && at > 0.6 && at < 1.0 ? 1.2 : 0)).toFixed(2) + ")";
    } else { hy.style.transform = ""; hy.style.filter = ""; }
    $("hy-arrive").hidden = !(ph === "A" && at > 1.0);
    var back = ED.here();
    if ($("hy-arrive-to").textContent !== j.to) $("hy-arrive-to").textContent = j.to;
    $("hy-arrive-back").textContent = "Back to " + (back ? back.back : "1 Home");
    var sv = j.survey || {}, schem = (ph === "S" || ph === "A") && sv.status === "ok" && S.hy.lay;
    if (schem && !S.hy.schemAt) S.hy.schemAt = Math.max(HY.SCHEM, t);   // scans in from when it's there
    if (!schem) S.hy.schemAt = 0;
    var reveal = schem ? (still ? 1 : Math.min(1, Math.max(0, (t - S.hy.schemAt) / 1.2))) : 0;
    var dim = schem ? 1 - 0.45 * reveal : 1, m = hyMess(t), P = hyCam(w, h, t);
    S.hy.field.forEach(function (f) { ctx.globalAlpha = (0.35 + 0.35 * Math.sin(t * 1.3 + f[3])) * dim; ctx.fillStyle = ED.MAP.hi; ctx.fillRect(f[0], f[1], f[2], f[2]); });
    ctx.globalAlpha = 1;
    // stars at the map's own scale (so their relative size shows), a little smaller here
    var A = P(-HY.XS, 0, 0), B = P(HY.XS, 0, 0);
    var rA = ED.mapRadius(hyBody(j.dep_star, "dep")) * 0.75, rB = ED.mapRadius(hyBody(j.to_star, "dst")) * 0.75;
    var live = [], plotting = ph === "J" || ph === "P";
    var under = reveal < 1;   // once the schematic covers it, the fold and cages behind it aren't drawn
    if (under) hyFold(ctx, P, t, dim);   // the fold, shaped by the paths' spread (measured as they're drawn, below)
    var col = function (st) { return ED.mapStyle(hyBody(st, "x")).col; };
    if (under) hyCage(ctx, P, -HY.XS, t, Math.max(rA * 1.9, 34) / P.sc, plotting ? 1.2 : 0.35, col(j.dep_star), dim);
    if (under) hyCage(ctx, P, HY.XS, t + 3, Math.max(rB * 1.9, 34) / P.sc, -(plotting ? 1.2 : 0.35) * 0.9, col(j.to_star), dim);
    if (plotting) live = hySearch(ctx, P, t, m, ph === "J" ? Math.max(0, (t - 0.6) / 0.9) : 1, A);
    else {
      var lk = still ? 1 : Math.min(1, Math.max(0, (t - HY.LOCK) / 1.6));
      var travel = ph === "A" ? 1 : t > HY.LOCK + 1 ? Math.min(0.97, (t - HY.LOCK - 1) / 12) : null;
      hyLocked(ctx, P, t, m, lk, travel);
    }
    hySpread(live || [], t, m, !plotting);
    hyStar(ctx, j.dep_star, "dep", A, rA, t, dim);
    hyStar(ctx, j.to_star, "dst", B, rB, t + 1, dim);
    if (!schem || reveal < 1) {
      hyTag(ctx, A, rA, j.from || "Departure", "DEPARTURE", false);
      hyTag(ctx, B, rB, j.to, j.to_star && j.to_star.estimate ? "TYPICAL SIZE · " + hyDataText(j.to_star, sv.status, sv.src).toUpperCase() : "DESTINATION", true);
    }
    hyRuler(ctx, w, P, j.ly);
    if (schem && reveal > 0) hySchematic(ctx, w, h, t, reveal, S.hy.lay, j);
    else if (ph === "S" || (ph === "A" && sv.status !== "ok")) {
      var sn = String(sv.src || "Spansh").toUpperCase();
      var msg = sv.status === "none" ? String(j.to).toUpperCase() + " IS NOT IN " + sn + " · UNCHARTED" : sv.status === "error" ? sn + " UNREACHABLE · NO SURVEY" :
                sv.status === "off" ? "LOOKUPS SWITCHED OFF" : "SURVEYING " + String(j.to).toUpperCase() + " · " + sn + ".".repeat(1 + Math.floor(t * 2) % 3);
      hyNotice(ctx, w, h, msg, sv.status === "none" || sv.status === "error");
    }
    if (jt > 0) { for (var q = 0; q < 26 * jt; q++) { ctx.fillStyle = "rgba(138, 255, 193," + (Math.random() * 0.4 * jt).toFixed(2) + ")"; ctx.fillRect(0, Math.random() * h, w, 1 + Math.random() * 3); } }
    ctx.finish();   // hard-edged coarse pixels
    var sc = Math.min(1, 46 / Math.max(rA, rB) * 0.75);   // panel globes: one scale for both, so their sizes compare
    if ((S.hy.gf = !S.hy.gf)) {   // the panel globes turn slowly: every other frame is plenty
      hyGlobe("hy-g-dep", j.dep_star, "dep", rA / 0.75 * sc, t);
      hyGlobe("hy-g-dst", j.to_star, "dst", rB / 0.75 * sc, t + 2);
    }
    hyPanels(j, t, ph);
  }
  function hyGlobe(id, star, key, r, t) {
    var c = $(id), cw = c.clientWidth;
    if (!cw) return;
    var ctx = ED.pixel.layers(c, cw, c.clientHeight, false);   // coarse pixels, like the rest
    ctx.setTransform(cw / 150, 0, 0, cw / 150, 0, 0); ctx.clearRect(0, 0, 150, 150);
    var n = hyNode(star, key + "-g", r, 75, 75);
    ctx.globalAlpha = star && star.estimate ? 0.6 : 1;
    ctx.save(); ED.mapBody(ctx, n, t); ctx.restore();
    ctx.globalAlpha = 1;
    ctx.finish();
  }
  // an overlay above every page: main.js keeps the UFC's knobs and pulls from the page while it's up
  ED.hyper = { update: renderHyper, on: function () { return !!S.hy.on; } };
})();
