// ED Target Board page - The system map drawing: laying out a system and drawing it (bodies as wireframes,
// stations as icons) - shared by the Syst map and the hyperspace overlay.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- System tab, map view ----
  // The whole system as wireframes, laid out like the game's system map: the main star on the
  // left, the bodies orbiting it along a line in orbit order (belts first), moons hanging below
  // their planet, the next level out to the right of each moon, orbital stations beside their
  // body, and fleet carriers as one marker under the main star. Bodies sharing a barycentre are
  // bracketed together. Sizes are compressed (radius^0.35) so stars and small moons both fit.
  // Each body spins at its real rotation period, every one sped up alike (1 day = 3 s; the very
  // fastest are capped at a 0.75 s turn), about an axis leaning by its axial tilt.
  var MAP = { day: 3, minTurn: 0.75, el: 0.3, pad: 18, top: 26, gk: 1.35, gapX: 28, gapY: 10, lab: 20, sta: 14,
              green: "#45f08a", grid: "#25b85c", back: "#1d4a2a", hi: "#8affc1", amber: "#e3a24a",
              amberDim: "#a8732f", fill: "#07140b", bg: "#0c0c0c", link: "rgba(37, 184, 92, 0.55)" };
  function mapRng(seed) {   // small seeded random numbers, so each body always looks the same
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function mapHash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0; }

  function mapRadius(b) {
    var sub = (b.sub || "").toLowerCase();
    if (b.star) {
      if (/black hole/.test(sub)) return 15;
      if (/neutron/.test(sub)) return 8;
      if (/white dwarf/.test(sub)) return 10;
      return Math.max(14, Math.min(64, 20 + 15 * Math.log2(1 + (b.km || 400000) / 695700)));   // by solar radii, so classes differ
    }
    return Math.max(4.5, Math.min(30, 0.488 * Math.pow(b.km || 1500, 0.348)));
  }

  // what a body's wireframe looks like, from its type
  function mapStyle(b) {
    var sub = (b.sub || "").toLowerCase(), cls = (b.cls || "").toUpperCase();
    if (b.star) {
      var s = { star: true, col: MAP.amber, kind: "ms", rays: 14, len: 0.17 };
      if (/black hole/.test(sub)) s.kind = "bh";
      else if (/neutron/.test(sub)) s.kind = "ns";
      else if (/white dwarf/.test(sub)) s.kind = "wd";
      else if (/wolf-rayet/.test(sub)) { s.kind = "wr"; s.rays = 22; s.len = 0.32; }
      else if (/t tauri/.test(sub)) { s.kind = "disc"; s.rays = 12; s.len = 0.16; }
      else if (/herbig/.test(sub)) { s.kind = "disc"; s.rays = 18; s.len = 0.24; }
      else if (/brown dwarf/.test(sub) || /^[LTY]\d/.test(cls)) { s.kind = "bd"; s.col = MAP.amberDim; s.rays = 0; }
      else if (/^(C|CS|CN|CJ|CH|CHD|MS|S)\d*$/.test(cls) || /^(c|cs|cn|cj|ch|chd|ms|s)(-type)? star/.test(sub)) { s.kind = "carbon"; s.rays = 10; s.len = 0.13; }
      else {   // main sequence and giants: hotter = more and longer rays, paler amber; cooler = deeper orange
        var t = { O: [26, 0.36, "#ffe7bd"], B: [22, 0.3, "#ffdca6"], A: [20, 0.26, "#f9cd8a"], F: [18, 0.22, "#f2bb6c"],
                  G: [16, 0.2, "#eaae5a"], K: [14, 0.17, MAP.amber], M: [12, 0.14, "#d9822f"] }[(cls || sub).charAt(0).toUpperCase()];
        if (t) { s.rays = t[0]; s.len = t[1]; s.col = t[2]; }
      }
      if (s.kind === "carbon") s.col = "#d46a2a";
      if (s.kind === "wd") s.col = "#ffe7bd";
      if (/giant/.test(sub)) { s.len *= 1.5; s.giant = true; }
      return s;
    }
    var p = { star: false, col: MAP.green, kind: "rocky" };
    if (/water giant/.test(sub)) p.kind = "watergiant";
    else if (/gas giant/.test(sub)) {
      p.kind = "gas";
      p.cls = /helium/.test(sub) ? "he" : /life/.test(sub) ? "life" : ((sub.match(/class (iv|v|i{1,3})\b/) || [])[1] || "i");
    }
    else if (/earth-like/.test(sub)) p.kind = "earth";
    else if (/water world/.test(sub)) p.kind = "water";
    else if (/ammonia world/.test(sub)) p.kind = "ammonia";
    else if (/metal-rich/.test(sub)) p.kind = "metal";
    else if (/high metal/.test(sub)) p.kind = "hmc";
    else if (/rocky ice/.test(sub)) p.kind = "rockyice";
    else if (/icy/.test(sub)) p.kind = "icy";
    // the type symbol under the planet's number
    p.glyph = { metal: "metal3", hmc: "metal2", rocky: "rock", rockyice: "rockice", icy: "ice", earth: "earth",
                water: "water", ammonia: "ammonia", watergiant: /life/.test(sub) ? "watergiantlife" : "watergiant" }[p.kind];
    if (p.kind === "gas") {
      p.glyph = p.cls === "he" ? "helium" : p.cls === "life" ? (/ammonia/.test(sub) ? "lifeA" : "lifeW") : "gas";
      p.num = (p.cls || "").toUpperCase();
    }
    return p;
  }

  // type symbols, about 12 units across, centred on (x, y):
  // metal-rich three gold bars, high metal two; a rock; rock and snowflake; snowflake; the Earth; a water drop;
  // an ammonia flask; gas giants a banded ball with their class in numerals; helium a balloon;
  // life-bearing giants a leaf (green: water-based, amber: ammonia-based); water giants a banded drop
  function mapGlyph(ctx, st, x, y, k) {
    var g = st && st.glyph;
    if (!g) return;
    var A = MAP.amber, G = MAP.green, H = MAP.hi, F = MAP.fill;
    ctx.save();
    ctx.translate(x, y);
    if (k) ctx.scale(k, k);
    ctx.setLineDash([]); ctx.lineWidth = 1; ctx.lineJoin = "round"; ctx.lineCap = "round";
    function path(pts, close) { ctx.beginPath(); pts.forEach(function (q, i) { if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); }); if (close) ctx.closePath(); }
    function bar(cx, cy) {
      path([[cx - 3.2, cy + 1.6], [cx + 3.2, cy + 1.6], [cx + 2.2, cy - 1.6], [cx - 2.2, cy - 1.6]], true);
      ctx.fillStyle = A; ctx.fill(); ctx.strokeStyle = "#6a4310"; ctx.stroke();
    }
    function rock(k, ox, oy) {
      path([[-5, 2], [-3.2, -2.6], [0.6, -4.4], [4.6, -1.4], [4.4, 3.2], [-1.6, 4.2]].map(function (q) { return [ox + q[0] * k, oy + q[1] * k]; }), true);
      ctx.fillStyle = F; ctx.fill(); ctx.strokeStyle = G; ctx.stroke();
      path([[ox - k, oy - k], [ox + 1.4 * k, oy + 1.2 * k]]); ctx.stroke();
    }
    function flake(r, ox, oy) {
      ctx.strokeStyle = H; ctx.beginPath();
      for (var k = 0; k < 6; k++) {
        var a = k * Math.PI / 3 - Math.PI / 2, c = Math.cos(a), d = Math.sin(a);
        ctx.moveTo(ox, oy); ctx.lineTo(ox + c * r, oy + d * r);
        if (r > 4) {   // little branches
          var bx = ox + c * r * 0.6, by = oy + d * r * 0.6;
          ctx.moveTo(bx, by); ctx.lineTo(bx + Math.cos(a + 0.8) * r * 0.3, by + Math.sin(a + 0.8) * r * 0.3);
          ctx.moveTo(bx, by); ctx.lineTo(bx + Math.cos(a - 0.8) * r * 0.3, by + Math.sin(a - 0.8) * r * 0.3);
        }
      }
      ctx.stroke();
    }
    function drop(r, ox, oy) {
      ctx.beginPath();
      ctx.moveTo(ox, oy - r * 1.55);
      ctx.bezierCurveTo(ox + r * 0.5, oy - r * 0.8, ox + r, oy - r * 0.2, ox + r, oy + r * 0.3);
      ctx.arc(ox, oy + r * 0.3, r, 0, Math.PI, false);
      ctx.bezierCurveTo(ox - r, oy - r * 0.2, ox - r * 0.5, oy - r * 0.8, ox, oy - r * 1.55);
      ctx.closePath();
      ctx.fillStyle = "rgba(138, 255, 193, 0.22)"; ctx.fill(); ctx.strokeStyle = H; ctx.stroke();
    }
    function banded(r, ox, oy) {
      ctx.beginPath(); ctx.arc(ox, oy, r, 0, 2 * Math.PI);
      ctx.fillStyle = F; ctx.fill(); ctx.strokeStyle = G; ctx.stroke();
      ctx.save(); ctx.clip();
      ctx.beginPath(); [-0.45, 0.05, 0.5].forEach(function (k) { ctx.moveTo(ox - r, oy + k * r); ctx.lineTo(ox + r, oy + k * r - 0.6); }); ctx.stroke();
      ctx.restore();
    }
    function leaf(ox, oy, col) {
      ctx.beginPath(); ctx.moveTo(ox - 2.6, oy + 2.6);
      ctx.quadraticCurveTo(ox - 2.9, oy - 2.9, ox + 2.8, oy - 2.8);
      ctx.quadraticCurveTo(ox + 2.6, oy + 2.4, ox - 2.6, oy + 2.6);
      ctx.fillStyle = col; ctx.fill();
      ctx.strokeStyle = F; path([[ox - 1.8, oy + 1.8], [ox + 1.6, oy - 1.6]]); ctx.stroke();
    }
    function numeral(t, ox) {   // roman numerals drawn as strokes, so they stay sharp at any zoom
      ctx.strokeStyle = G; ctx.beginPath();
      t.split("").forEach(function (ch) {
        if (ch === "I") { ctx.moveTo(ox, -3.5); ctx.lineTo(ox, 3.5); ox += 2.4; }
        else { ctx.moveTo(ox, -3.5); ctx.lineTo(ox + 1.7, 3.5); ctx.lineTo(ox + 3.4, -3.5); ox += 4.6; }
      });
      ctx.stroke();
    }
    if (g === "metal3") { bar(-3.3, 2.4); bar(3.3, 2.4); bar(0, -1.0); }
    else if (g === "metal2") { bar(-1.2, 1.8); bar(1.2, -1.6); }
    else if (g === "rock") rock(1, 0, 0);
    else if (g === "rockice") { rock(0.75, -1.8, 1.2); flake(3.2, 3.4, -2.8); }
    else if (g === "ice") flake(5.6, 0, 0);
    else if (g === "earth") {
      ctx.beginPath(); ctx.arc(0, 0, 5.2, 0, 2 * Math.PI); ctx.fillStyle = F; ctx.fill();
      ctx.save(); ctx.clip();
      ctx.fillStyle = G;
      path([[-5, -1.2], [-2.8, -3.9], [0.2, -3.2], [0.4, -0.8], [-1.6, 0.8], [-3.6, 1.6]], true); ctx.fill();
      path([[0.8, 1.6], [3.8, 0.4], [4.4, 3.4], [1.8, 4.6]], true); ctx.fill();
      ctx.restore();
      ctx.beginPath(); ctx.arc(0, 0, 5.2, 0, 2 * Math.PI); ctx.strokeStyle = H; ctx.stroke();
    }
    else if (g === "water") drop(3.9, 0, 0.4);
    else if (g === "ammonia") {
      path([[-3.6, 2], [3.6, 2], [4.8, 4.8], [-4.8, 4.8]], true); ctx.fillStyle = "rgba(227, 162, 74, 0.6)"; ctx.fill();
      ctx.strokeStyle = G;
      path([[-1.3, -5.2], [-1.3, -1.8], [-4.8, 4.8], [4.8, 4.8], [1.3, -1.8], [1.3, -5.2]]); ctx.stroke();
      path([[-2.2, -5.2], [2.2, -5.2]]); ctx.stroke();
    }
    else if (g === "gas") { banded(4.6, -3.2, 0); numeral(st.num || "I", 3.2); }
    else if (g === "helium") {
      ctx.beginPath(); ctx.ellipse(0, -1.6, 3.6, 4.3, 0, 0, 2 * Math.PI); ctx.fillStyle = F; ctx.fill(); ctx.strokeStyle = H; ctx.stroke();
      path([[-0.9, 3.3], [0.9, 3.3], [0, 2.5]], true); ctx.fillStyle = H; ctx.fill();
      ctx.beginPath(); ctx.moveTo(0, 3.3); ctx.quadraticCurveTo(1.8, 4.6, 0, 6.2); ctx.stroke();
    }
    else if (g === "lifeW" || g === "lifeA") { banded(4.6, -1.2, 0.8); leaf(3.4, -3.2, g === "lifeW" ? H : A); }
    else if (g === "watergiant" || g === "watergiantlife") {
      drop(3.9, g === "watergiantlife" ? -1.2 : 0, 0.4);
      ctx.save(); ctx.beginPath(); ctx.arc(g === "watergiantlife" ? -1.2 : 0, 1.6, 3.9, 0, 2 * Math.PI); ctx.clip();
      ctx.strokeStyle = H; path([[-6, 1], [6, 0.4]]); ctx.stroke(); path([[-6, 3.2], [6, 2.6]]); ctx.stroke();
      ctx.restore();
      if (g === "watergiantlife") leaf(3.4, -3.4, H);
    }
    ctx.restore();
  }

  // the lines drawn on a body's surface (latitude / longitude in radians), made once per body:
  // the grid, plus craters, cracks, ice caps, continents, waves, storms or cloud bands by type
  function mapFeatures(b, st, r) {
    var R = mapRng(mapHash(b.key + "|" + b.name)), D = Math.PI / 180, out = [], i, j;
    var n = Math.max(16, Math.min(56, Math.round(r * 1.8)));
    var big = r >= 14, mid = r >= 8;
    var gcol = st.star ? st.col : MAP.grid, fcol = st.star ? st.col : MAP.hi;
    function add(pts, col, dash, w) { out.push({ p: pts, c: col, d: dash, w: w || 1 }); }
    function par(lat, col, dash, wave, amp, ph) {   // a circle of latitude (degrees), optionally wavy
      var pts = [];
      for (i = 0; i <= n; i++) {
        var lo = -Math.PI + i / n * 2 * Math.PI;
        pts.push([(lat + (wave ? amp * Math.sin(lo * wave + (ph || 0)) : 0)) * D, lo]);
      }
      add(pts, col, dash);
    }
    function mer(lon, col, dash) {
      var pts = [], m = Math.ceil(n / 2);
      for (i = 0; i <= m; i++) pts.push([-Math.PI / 2 + i / m * Math.PI, lon * D]);
      add(pts, col, dash);
    }
    function spot(lat, lon, rad, squash, wobble) {   // a small closed shape on the surface (degrees)
      var pts = [], k = 14;
      for (i = 0; i <= k; i++) {
        var a = (i % k) / k * 2 * Math.PI, rr = rad * (wobble ? 0.65 + ((mapHash(b.key + lat + "/" + (i % k)) % 100) / 100) * 0.6 : 1);
        var la = lat + rr * Math.sin(a);
        pts.push([la * D, (lon + rr * Math.cos(a) * (squash || 1) / Math.max(0.25, Math.cos(la * D))) * D]);
      }
      return pts;
    }
    var gas = st.kind === "gas" || st.kind === "watergiant" || st.kind === "bd";
    if (st.kind === "ns" || st.kind === "bh") return out;
    if (gas) {
      var cfg = { i: [5, [6, 3]], ii: [7, [4, 2]], iii: [3, [2, 4]], iv: [9, [3, 2]], v: [9, [5, 1.5]], he: [6, [1, 3]], life: [6, [5, 2]] }[st.cls] || [6, [4, 2]];
      var nb = big ? cfg[0] : mid ? Math.ceil(cfg[0] / 2) : 2;
      for (j = 1; j <= nb; j++) {
        var lat = -75 + j * 150 / (nb + 1) + (R() - 0.5) * 6;
        par(lat, j % 2 ? gcol : fcol, cfg[1], st.kind === "watergiant" ? 5 : 0, 3, R() * 6);
      }
      for (j = 0; j < 4; j++) mer(j * 90, gcol, [1, 5]);   // faint meridians, so the turning shows
      if (mid && (st.cls === "i" || st.cls === "ii" || st.cls === "v" || st.kind === "bd")) add(spot((R() - 0.5) * 50, R() * 360, 9, 1.8), fcol, [2, 1.5]);
      if (mid && st.cls === "life") for (j = 0; j < 4; j++) add(spot((R() - 0.5) * 100, R() * 360, 3), fcol, [1, 1.5]);
      return out;
    }
    var lats = big ? [-60, -30, 0, 30, 60] : mid ? [-45, 0, 45] : [0], mers = big ? 8 : mid ? 4 : 3;
    var gdash = st.star ? [3, 2] : (r >= 10 ? [4, 2] : [2.5, 1.5]);
    if (st.kind === "wd") { lats = [0]; mers = 3; }
    lats.forEach(function (l) { par(l, gcol, gdash); });
    for (j = 0; j < mers; j++) mer(j * 360 / mers, gcol, gdash);
    if (!mid) return out;
    var craters = { hmc: 8, rocky: 5, rockyice: 4, metal: 3 }[st.kind] || 0;
    for (j = 0; j < craters; j++) add(spot((R() - 0.5) * 120, R() * 360, 5 + R() * 9), fcol, [2, 1.5]);
    if (st.kind === "icy" || st.kind === "rockyice") {
      for (j = 0; j < (big ? 4 : 2); j++) {   // cracks: short random walks
        var la = (R() - 0.5) * 100, lo = R() * 360, hd = R() * 360, pts = [];
        for (i = 0; i < 7; i++) {
          pts.push([la * D, lo * D]);
          hd += (R() - 0.5) * 70;
          la = Math.max(-80, Math.min(80, la + 13 * Math.cos(hd * D)));
          lo += 13 * Math.sin(hd * D) / Math.max(0.3, Math.cos(la * D));
        }
        add(pts, fcol, [3, 1.5]);
      }
    }
    if (st.kind === "icy" || st.kind === "earth") { par(74, fcol, [1, 2]); par(-74, fcol, [1, 2]); }
    if (st.kind === "earth") for (j = 0; j < 3; j++) add(spot((R() - 0.5) * 100, R() * 360, 16 + R() * 16, 1.3, true), fcol, [3, 1.5]);
    if (st.kind === "water") [-45, -15, 15, 45].forEach(function (l, k) { par(l, fcol, [4, 2], 5 + k, 4, R() * 6); });
    if (st.kind === "ammonia") {
      for (j = 0; j < 3; j++) add(spot((R() - 0.5) * 90, R() * 360, 8 + R() * 6, 2), fcol, [3, 1.5]);
      par(35, fcol, [1, 2.5], 3, 5); par(-35, fcol, [1, 2.5], 3, 5);
    }
    if (st.kind === "metal") for (j = 0; j < 5; j++) {   // angular facets
      var fl = (R() - 0.5) * 110, fo = R() * 360, s = 6 + R() * 6;
      add([[fl * D, fo * D], [(fl + s) * D, (fo + s * 0.4) * D], [(fl + s * 0.2) * D, (fo + s) * D], [fl * D, fo * D]], fcol, [2, 1]);
    }
    if (st.kind === "carbon") for (j = 0; j < 5; j++) add(spot((R() - 0.5) * 110, R() * 360, 6 + R() * 8, 1, true), st.col, [2, 2]);
    return out;
  }

  // a body's projection: the camera sits a little above its orbital plane, the spin axis leans
  // by the axial tilt, and spin turns the surface. Returns [x, y, depth]; depth > 0 faces you.
  function mapProj(x, y, r, spin, tilt) {
    var ce = Math.cos(MAP.el), se = Math.sin(MAP.el), ct = Math.cos(tilt), sn = Math.sin(tilt);
    return function (lat, lon, k) {
      k = k || 1;
      var cl = Math.cos(lat), a = lon + spin, px = k * cl * Math.sin(a), py = k * Math.sin(lat), pz = k * cl * Math.cos(a);
      var y1 = py * ce - pz * se, z1 = py * se + pz * ce;
      return [x + r * (px * ct + y1 * sn), y - r * (-px * sn + y1 * ct), z1];
    };
  }
  function mapStroke(ctx, P, pts, front) {   // the front (or back) runs of a surface line
    ctx.beginPath();
    var on = false;
    for (var i = 0; i < pts.length; i++) {
      var q = P(pts[i][0], pts[i][1]);
      if ((q[2] > 0) === front) { if (on) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); on = true; }
      else on = false;
    }
    ctx.stroke();
  }
  function mapEllipses(ctx, P, list, front) {   // rings, discs: circles in the equatorial plane
    list.forEach(function (e) {
      ctx.strokeStyle = e.c; ctx.setLineDash(e.d); ctx.lineWidth = e.w || 1;
      ctx.beginPath();
      var on = false;
      for (var i = 0; i <= 56; i++) {
        var q = P(0, i / 56 * 2 * Math.PI, e.k);
        if ((q[2] > 0) === front) { if (on) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); on = true; }
        else on = false;
      }
      ctx.stroke();
    });
  }
  function mapRings(n) {   // a body's rings as circles, in body radii (compressed if very wide)
    var b = n.d, st = n.st, out = [];
    if (st.kind === "disc") [1.45, 1.9, 2.35].forEach(function (k) { out.push({ k: k, c: st.col, d: [2, 3] }); });
    if (st.kind === "bh") [1.5, 2.0, 2.6, 3.2].forEach(function (k, i) { out.push({ k: k, c: st.col, d: i ? [3, 2] : [], w: i ? 1 : 1.4 }); });
    var rings = (b.rings || []).filter(function (g) { return g.o && b.km; });
    if (!rings.length) return out;
    var kmax = Math.max.apply(null, rings.map(function (g) { return g.o / b.km; })), sc = kmax > 2.5 ? 2.5 / kmax : 1;
    rings.forEach(function (g) {
      var dash = /icy/i.test(g.t) ? [6, 2] : /metallic/i.test(g.t) ? [1, 1.5] : /metal/i.test(g.t) ? [2, 2] : [3, 2];
      var ki = Math.max(1.12, (g.i || g.o * 0.8) / b.km * sc), ko = Math.max(ki + 0.08, g.o / b.km * sc);
      [ki, (ki + ko) / 2, ko].forEach(function (k, i) { out.push({ k: k, c: i === 1 ? MAP.grid : MAP.green, d: dash }); });
    });
    return out;
  }
  function mapSpin(n, t) {
    var b = n.d, spin = n.phase;
    if (b.rot && t) spin += (b.rot < 0 ? -1 : 1) * t / Math.max(MAP.minTurn, Math.abs(b.rot) * MAP.day) * 2 * Math.PI;
    return spin;
  }

  function mapBody(ctx, n, t) {
    var b = n.d, st = n.st, r = n.hw, x = n.x, y = n.y, tilt = (b.tilt || 0) * Math.PI / 180;
    var P = mapProj(x, y, r, mapSpin(n, t), tilt), Pr = mapProj(x, y, r, 0, tilt);
    var feats = n.feats || (n.feats = mapFeatures(b, st, r)), rings = n.rings || (n.rings = mapRings(n));
    var axisLen = st.kind === "ns" ? 3.4 : 1.45, acol = st.star ? st.col : MAP.grid;
    // behind the body: the far halves of rings and discs, and the far end of the spin axis
    mapEllipses(ctx, Pr, rings, false);
    var s1 = Pr(-Math.PI / 2, 0, 1), s2 = Pr(-Math.PI / 2, 0, axisLen);
    ctx.setLineDash(st.kind === "ns" ? [] : [2, 2]); ctx.strokeStyle = acol; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(s1[0], s1[1]); ctx.lineTo(s2[0], s2[1]); ctx.stroke();
    // the body
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = st.kind === "bh" ? "#000" : st.star ? "#120d05" : MAP.fill; ctx.fill();
    if (r >= 16 && !st.star) {
      ctx.strokeStyle = MAP.back; ctx.setLineDash([2, 3]); ctx.lineWidth = 0.8;
      feats.forEach(function (f) { mapStroke(ctx, P, f.p, false); });
    }
    feats.forEach(function (f) { ctx.strokeStyle = f.c; ctx.setLineDash(f.d); ctx.lineWidth = f.w; mapStroke(ctx, P, f.p, true); });
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.setLineDash(st.star || r < 10 ? [] : [4, 2]); ctx.strokeStyle = st.star ? st.col : MAP.green; ctx.lineWidth = st.star ? 1.4 : 1.2; ctx.stroke();
    if (st.kind === "bh") { ctx.beginPath(); ctx.arc(x, y, r * 1.12, 0, 2 * Math.PI); ctx.setLineDash([]); ctx.strokeStyle = st.col; ctx.lineWidth = 1.5; ctx.stroke(); }
    // in front: the near halves, and the near end of the axis
    mapEllipses(ctx, Pr, rings, true);
    var n1 = Pr(Math.PI / 2, 0, 1), n2 = Pr(Math.PI / 2, 0, axisLen);
    ctx.setLineDash(st.kind === "ns" ? [] : [2, 2]); ctx.strokeStyle = st.star ? st.col : MAP.hi; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(n1[0], n1[1]); ctx.lineTo(n2[0], n2[1]); ctx.stroke();
    ctx.setLineDash([]);
    if (st.kind === "ns") {   // jets along the axis
      [[n1, n2], [s1, s2]].forEach(function (j) {
        var dx = j[1][0] - x, dy = j[1][1] - y, L = Math.hypot(dx, dy) || 1, px = -dy / L * r * 0.7, py = dx / L * r * 0.7;
        ctx.beginPath(); ctx.moveTo(j[0][0], j[0][1]); ctx.lineTo(j[1][0] + px, j[1][1] + py);
        ctx.moveTo(j[0][0], j[0][1]); ctx.lineTo(j[1][0] - px, j[1][1] - py); ctx.stroke();
      });
    }
    if (st.rays) {   // corona: longer and more rays for hotter stars, turning slowly
      ctx.strokeStyle = st.col; ctx.lineWidth = 1.1; ctx.beginPath();
      for (var a = 0; a < st.rays; a++) {
        var ang = a / st.rays * 2 * Math.PI + t * 0.06 + n.phase, len = r * st.len * (a % 2 ? 1 : 1.5);
        ctx.moveTo(x + (r + 3) * Math.cos(ang), y + (r + 3) * Math.sin(ang));
        ctx.lineTo(x + (r + 3 + len) * Math.cos(ang), y + (r + 3 + len) * Math.sin(ang));
      }
      ctx.stroke();
    }
    if (st.kind === "wr") {   // Wolf-Rayet: shells blowing off
      ctx.setLineDash([3, 3]); ctx.strokeStyle = st.col;
      [1.55, 1.95].forEach(function (k, i) { ctx.beginPath(); ctx.arc(x, y, r * (k + 0.1 * Math.sin(t * 1.5 + i * 2)), 0, 2 * Math.PI); ctx.stroke(); });
    }
    if (st.kind === "wd" || st.kind === "ns") { ctx.setLineDash([1, 2]); ctx.strokeStyle = st.col; ctx.beginPath(); ctx.arc(x, y, r * 1.7, 0, 2 * Math.PI); ctx.stroke(); }
    if (st.giant) { ctx.setLineDash([5, 3]); ctx.strokeStyle = st.col; ctx.beginPath(); ctx.arc(x, y, r * 1.08, 0, 2 * Math.PI); ctx.stroke(); }   // giants: a swollen outer shell
    ctx.setLineDash([]);
    if (b.land) {   // landable: a solid ring; settlements (squares) and ports (triangles) on it
      var lr = r + 3.5, marks = [];
      for (var i = 0; i < b.ports; i++) marks.push("p");
      for (i = 0; i < b.sites; i++) marks.push("s");
      ctx.beginPath(); ctx.arc(x, y, lr, 0, 2 * Math.PI); ctx.strokeStyle = MAP.hi; ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = MAP.amber;
      var sz = r < 8 ? 2 : 2.5, shown = marks.length > 5 ? marks.slice(0, 4) : marks, step = Math.min(40, Math.max(20, (sz * 2 + 2.5) / lr * 57.3));
      shown.forEach(function (m, k) {
        var ang = ((shown.length - 1) / 2 - k) * step * Math.PI / 180, mx = x + lr * Math.cos(ang), my = y - lr * Math.sin(ang);
        ctx.beginPath();
        if (m === "p") { ctx.moveTo(mx, my - sz * 1.4); ctx.lineTo(mx + sz * 1.3, my + sz); ctx.lineTo(mx - sz * 1.3, my + sz); ctx.closePath(); }
        else ctx.rect(mx - sz, my - sz, sz * 2, sz * 2);
        ctx.fill();
      });
      if (marks.length > 5) {   // more than fit: a plus after the first four
        var pa = -((shown.length - 1) / 2 + 1) * step * Math.PI / 180, px = x + lr * Math.cos(pa), py = y - lr * Math.sin(pa);
        ctx.strokeStyle = MAP.amber; ctx.lineWidth = 1.5; ctx.beginPath();
        ctx.moveTo(px - 2.5, py); ctx.lineTo(px + 2.5, py); ctx.moveTo(px, py - 2.5); ctx.lineTo(px, py + 2.5); ctx.stroke();
      }
    }
  }

  // a small bitmap, crisp on the coarse-pixel layers (see pixel.js); on a plain canvas, just scaled
  function mapBitmap(ctx, rows, x, y, fit, dry) {
    if (ctx.bitmap) return ctx.bitmap(rows, x, y, fit, dry);
    var n = rows.length, px = fit / n;
    if (!dry) rows.forEach(function (r, j) {
      for (var i = 0; i < r.length; i++) if (r[i] === "#") ctx.fillRect(x - fit / 2 + i * px, y - fit / 2 + j * px, px, px);
    });
    return { size: fit, unit: 1 };
  }

  // a station, carrier, megaship, installation, beacon or construction site: the List view's icon for it,
  // in a circle (at the display's resolution these read better than wireframes; bodies keep theirs). The
  // icon's pixels are whole coarse pixels, so it grows in steps as you zoom in; zoomed too far out for it
  // to fit without crowding its neighbours, just the circle and a dot.
  function mapMarker(ctx, n) {
    var icons = ED.ICONS || {}, rows = icons[n.t === "carrier" ? "carrier" : (n.d.icon || n.d.kind)] || icons.station;
    if (!rows) return;
    var r = n.hw, sz = mapBitmap(ctx, rows, n.x, n.y, r * 1.5, true), R = sz.size * 0.7 + 0.6 * sz.unit;
    var room = r + MAP.gapY / 2 + 0.2 * sz.unit, fits = R <= room;
    if (!fits) R = r;
    n.drawR = R;   // (for the selection's corners)
    if (n.d && n.d.est) ctx.globalAlpha = 0.6;   // where it is is a guess
    ctx.beginPath(); ctx.arc(n.x, n.y, R, 0, 2 * Math.PI);
    ctx.fillStyle = MAP.bg; ctx.fill();   // hides the line behind
    ctx.strokeStyle = MAP.grid; ctx.lineWidth = 1; ctx.setLineDash([]); ctx.stroke();
    ctx.fillStyle = MAP.green;
    if (fits) mapBitmap(ctx, rows, n.x, n.y, r * 1.5);
    else mapBitmap(ctx, ["##", "##"], n.x, n.y, 0);
    ctx.globalAlpha = 1;
  }

  function mapBelt(ctx, n, t) {   // an asteroid belt: rocks drifting slowly down a narrow oval
    var R = mapRng(mapHash(n.key + "belt" + n.belt)), hw = n.hw, hh = n.hh, type = (n.d.belt.t || "").toLowerCase();
    var sides = /icy/.test(type) ? 4 : /metal/.test(type) ? 6 : 5;
    ctx.strokeStyle = MAP.green; ctx.setLineDash([]); ctx.lineWidth = 1;
    for (var i = 0; i < 18; i++) {
      var ry = ((R() * 2 * hh + t * 2.5) % (2 * hh)) - hh, rx = (R() - 0.5) * 2 * hw * Math.sqrt(Math.max(0, 1 - (ry / hh) * (ry / hh)));
      var s = 1.3 + R() * 2.2, a0 = R() * 6.28 + t * 0.3;
      ctx.beginPath();
      for (var k = 0; k <= sides; k++) {
        var a = a0 + k / sides * 2 * Math.PI, q = s * (k % 2 ? 0.75 : 1);
        if (k) ctx.lineTo(n.x + rx + q * Math.cos(a), n.y + ry + q * Math.sin(a)); else ctx.moveTo(n.x + rx + q * Math.cos(a), n.y + ry + q * Math.sin(a));
      }
      ctx.stroke();
    }
  }

  function mapReach(n) {   // how far a body's drawing reaches from its centre: rings, corona, axis, landable marks
    var b = n.d, st = n.st, r = n.hw, P = mapProj(0, 0, r, 0, (b.tilt || 0) * Math.PI / 180), e = { l: r, r: r, t: r, b: r };
    function take(q) { e.l = Math.max(e.l, -q[0]); e.r = Math.max(e.r, q[0]); e.t = Math.max(e.t, -q[1]); e.b = Math.max(e.b, q[1]); }
    function round(k) { e.l = Math.max(e.l, k); e.r = Math.max(e.r, k); e.t = Math.max(e.t, k); e.b = Math.max(e.b, k); }
    (n.rings || (n.rings = mapRings(n))).forEach(function (g) { for (var i = 0; i < 32; i++) take(P(0, i / 32 * 2 * Math.PI, g.k)); });
    var ax = st.kind === "ns" ? 3.4 : 1.45;
    take(P(Math.PI / 2, 0, ax)); take(P(-Math.PI / 2, 0, ax));
    if (st.rays) round(r + 3 + r * st.len * 1.5);
    if (st.kind === "wr") round(r * 2.05);
    if (st.kind === "wd" || st.kind === "ns") round(r * 1.7);
    if (b.land) { round(r + 4); if (b.ports + b.sites) e.r = Math.max(e.r, r + 9); }
    e.l = Math.ceil(e.l); e.r = Math.ceil(e.r); e.t = Math.ceil(e.t); e.b = Math.ceil(e.b);
    return e;
  }

  // ---- layout: works out where everything goes (once per EDSM update) ----
  function mapLayout(m) {
    var mc = S.map.mctx || (S.map.mctx = document.createElement("canvas").getContext("2d"));
    mc.font = "16px VGA";
    function tw(t) { return Math.ceil(mc.measureText(t).width); }
    function mk(t, d, hw, hh, lab, key) {
      return { t: t, d: d, hw: hw, hh: hh, lab: lab || "", lw: lab ? tw(lab) : 0, kids: [], sta: [], bk: [], key: key, phase: (mapHash(key) % 628) / 100 };
    }
    var byKey = {}, roots = [], orphans = [], items = [], flat = [], links = [], brks = [], nodes = {};
    (m.bodies || []).forEach(function (b) {
      var r = mapRadius(b), n = mk("body", b, r, r, b.lbl + (b.mine ? " \u221a" : ""), b.key);   // (a tick: you've scanned it)
      n.st = mapStyle(b);
      n.reach = mapReach(n);
      byKey[b.key] = n;
    });
    (m.bodies || []).forEach(function (b) {
      var n = byKey[b.key];
      if (b.parent && byKey[b.parent] && b.parent !== b.key) byKey[b.parent].bk.push(n); else roots.push(n);
    });
    (m.stations || []).forEach(function (s) {
      var n = mk("station", s, MAP.sta, MAP.sta, "", s.key);
      (s.host && byKey[s.host] ? byKey[s.host].sta : orphans).push(n);
    });
    var main = roots.filter(function (n) { return n.d.main; })[0] || roots[0];
    roots.forEach(function (rt) {
      rt.kids = rt.sta.slice();
      rt.set = true;
      if (rt === main) {   // under the main star: stations with no known body, then the carriers
        rt.kids = rt.kids.concat(orphans);
        if (m.carriers) {
          var c = mk("carrier", { n: m.carriers }, MAP.sta, MAP.sta, "×" + m.carriers, "carriers");
          c.labSide = "right";
          rt.kids.push(c);
        }
      }
      if (!rt.d.star) rt.kids = rt.kids.concat(rt.bk);
      items.push(rt);
      (rt.d.belts || []).forEach(function (bl, i) {
        var bn = mk("belt", { star: rt.d, belt: bl }, 7, Math.max(12, rt.hh * 0.8), "", rt.key);
        bn.belt = i;
        items.push(bn);
      });
      if (rt.d.star) rt.bk.forEach(function (k) { items.push(k); });   // a star's planets line up beside it
    });
    // sizes: "row" = sits in a row, its children hang below in a column; "col" = sits in a column,
    // its children go to its right. ext = how far it and its children reach from its centre.
    function measure(n, dir) {
      if (!n.set) { n.set = true; n.kids = n.sta.concat(n.bk); }
      n.dir = dir;
      var rc = n.reach || { l: n.hw, r: n.hw, t: n.hh, b: n.hh }, e = { l: rc.l, r: rc.r, t: rc.t, b: rc.b };
      if (n.lab) {
        if (n.labSide === "right") e.r = n.hw + 5 + n.lw;
        else if (dir === "row") {
          var gw = n.st && n.st.glyph ? 15 : 0;
          e.b = rc.b + MAP.lab + (gw ? 19 : 0); e.l = Math.max(e.l, n.lw / 2 + 3, gw); e.r = Math.max(e.r, n.lw / 2 + 3, gw);
        }
        else { e.l = rc.l + 6 + n.lw + (n.st && n.st.glyph ? 24 : 0); e.t = Math.max(e.t, 10); e.b = Math.max(e.b, 10); }
      }
      if (n.kids.length) {
        if (dir === "row") {
          var y = e.b + MAP.gapY;
          n.kids.forEach(function (k) { var ke = measure(k, "col"); k.dx = 0; k.dy = y + ke.t; y = k.dy + ke.b + MAP.gapY; e.l = Math.max(e.l, ke.l); e.r = Math.max(e.r, ke.r); });
          e.b = y - MAP.gapY;
        } else {
          var x = e.r + MAP.gapX * 0.6;
          n.kids.forEach(function (k) { var ke = measure(k, "row"); k.dy = 0; k.dx = x + ke.l; x = k.dx + ke.r + MAP.gapX * 0.6; e.t = Math.max(e.t, ke.t); e.b = Math.max(e.b, ke.b); });
          e.r = x - MAP.gapX * 0.6;
        }
      }
      n.ext = e;
      return e;
    }
    function place(n, x, y) {
      n.x = x; n.y = y;
      flat.push(n);
      if (n.t !== "belt") nodes[n.key] = n;
      n.kids.forEach(function (k) { place(k, x + k.dx, y + k.dy); });
      if (n.kids.length) {
        var last = n.kids[n.kids.length - 1];
        links.push(n.dir === "row" ? [x, y, x, last.y] : [x, y, last.x, y]);
      }
    }
    var maxT = 0, x = MAP.pad, maxB = 0;
    items.forEach(function (n) {   // room above the line for the tallest body, or a body and its brackets
      measure(n, "row");
      var nl = n.t === "body" ? (n.d.nulls || []).length : 0;
      maxT = Math.max(maxT, n.ext.t + (nl ? 10 + nl * 10 : 0));
    });
    var axisY = MAP.top + maxT;
    items.forEach(function (n) { n.cx = x + n.ext.l; x = n.cx + n.ext.r + MAP.gapX; maxB = Math.max(maxB, n.ext.b); });
    if (items.length > 1) links.push([items[0].cx, axisY, items[items.length - 1].cx, axisY]);
    items.forEach(function (n) { place(n, n.cx, axisY); });
    // barycentres: bodies orbiting one together are bracketed, above a row or left of a column;
    // a pair inside a bigger group joins the outer bracket from the middle of its own
    function bracket(list, above) {
      var groups = {}, gl = [];
      list.forEach(function (n) {
        if (n.t !== "body") return;
        (n.d.nulls || []).forEach(function (id, lvl) {
          var g = groups[id];
          if (!g) { g = groups[id] = { m: [], lvl: 0 }; gl.push(g); }
          g.m.push(n); g.lvl = Math.max(g.lvl, lvl);
        });
      });
      gl = gl.filter(function (g) { return g.m.length > 1; }).sort(function (a, b) { return a.lvl - b.lvl || a.m.length - b.m.length; });
      gl.forEach(function (g) {
        var pts = [], taken = [];
        gl.forEach(function (h) {
          if (h !== g && h.anchor && h.m.length < g.m.length && h.m.every(function (n) { return g.m.indexOf(n) >= 0 && taken.indexOf(n) < 0; })) {
            pts.push(h.anchor); taken = taken.concat(h.m);
          }
        });
        g.m.forEach(function (n) {
          if (taken.indexOf(n) < 0) pts.push(above ? [n.x, n.y - n.reach.t - 3] : [n.x - n.ext.l - 3, n.y]);
        });
        var xs = pts.map(function (p) { return p[0]; }), ys = pts.map(function (p) { return p[1]; });
        if (above) {
          var yl = Math.min.apply(null, ys) - 9, x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
          pts.forEach(function (p) { brks.push([p[0], p[1], p[0], yl]); });
          brks.push([x0, yl, x1, yl]);
          g.anchor = [(x0 + x1) / 2, yl];
        } else {
          var xl = Math.min.apply(null, xs) - 8, y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
          pts.forEach(function (p) { brks.push([p[0], p[1], xl, p[1]]); });
          brks.push([xl, y0, xl, y1]);
          g.anchor = [xl, (y0 + y1) / 2];
        }
      });
    }
    bracket(items, true);
    flat.forEach(function (n) { if (n.kids.length > 1) bracket(n.kids, n.dir !== "row"); });
    return { flat: flat, nodes: nodes, links: links, brks: brks, W: x - MAP.gapX + MAP.pad, H: axisY + maxB + MAP.pad, axisY: axisY };
  }

  // ---- drawing a laid-out system: the lines, each body (wireframe), station (icon), belt, name and type
  // symbol. The Syst map and the hyperspace overlay both draw it with this; each adds its own on top (the
  // map: the selection, the UFC cursor and YOU; hyperspace: its band and scan-in).
  // o.view {x0, x1, y0, y1}: draw only what's in it; o.bg: the ground (behind the names under a body) ----
  function mapScene(ctx, L, t, o) {
    o = o || {};
    var v = o.view, bg = o.bg || MAP.bg;
    ctx.lineWidth = 1; ctx.setLineDash([]);
    ctx.strokeStyle = MAP.link; ctx.beginPath();
    L.links.forEach(function (l) { ctx.moveTo(l[0], l[1]); ctx.lineTo(l[2], l[3]); });
    ctx.stroke();
    ctx.strokeStyle = MAP.grid; ctx.beginPath();
    L.brks.forEach(function (l) { ctx.moveTo(l[0], l[1]); ctx.lineTo(l[2], l[3]); });
    ctx.stroke();
    ctx.font = "16px VGA"; ctx.textBaseline = "alphabetic";
    L.flat.forEach(function (n) {
      var rc = n.reach || { l: n.hw, r: n.hw, t: n.hh, b: n.hh };
      if (v && (n.x + rc.r + n.lw < v.x0 || n.x - rc.l - n.lw > v.x1 || n.y + rc.b + 20 < v.y0 || n.y - rc.t > v.y1)) return;
      ctx.save();
      if (n.t === "body") mapBody(ctx, n, t);
      else if (n.t === "station" || n.t === "carrier") mapMarker(ctx, n);
      else mapBelt(ctx, n, t);
      ctx.restore();
      if (!n.lab) return;
      ctx.fillStyle = MAP.grid; ctx.setLineDash([]);
      if (n.labSide === "right") { ctx.textAlign = "left"; ctx.fillText(n.lab, n.x + n.hw + 5, n.y + 5); }
      else if (n.dir === "row") {
        var gl = n.st && n.st.glyph;
        ctx.fillStyle = bg; ctx.fillRect(n.x - Math.max(n.lw / 2 + 2, gl ? 13 : 0), n.y + rc.b + 2, Math.max(n.lw + 4, gl ? 26 : 0), gl ? 36 : 16);
        ctx.fillStyle = MAP.grid; ctx.textAlign = "center"; ctx.fillText(n.lab, n.x, n.y + rc.b + 15);
        if (gl) mapGlyph(ctx, n.st, n.x, n.y + rc.b + 28, MAP.gk);
      } else {
        ctx.textAlign = "right"; ctx.fillText(n.lab, n.x - rc.l - 5, n.y + 5);
        if (n.st && n.st.glyph) mapGlyph(ctx, n.st, n.x - rc.l - 5 - n.lw - 13, n.y, MAP.gk);
      }
    });
  }

  ED.MAP = MAP;
  ED.mapBelt = mapBelt;
  ED.mapBody = mapBody;
  ED.mapGlyph = mapGlyph;
  ED.mapLayout = mapLayout;
  ED.mapRadius = mapRadius;
  ED.mapRng = mapRng;
  ED.mapMarker = mapMarker;
  ED.mapScene = mapScene;
  ED.mapStyle = mapStyle;
})();
