// ED Target Board page - 2 Nav, sub-tab 1 (Syst), its list: bodies and stations from EDSM, the details and the picture.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- System tab: bodies and stations from EDSM, with your live position ----
  var SYW = { c: 70, r: 62, R2D: Math.PI / 180 };
  var SYMSG = { loading: "Fetching {src}", empty: "No {src} data", error: "{src} unreachable", off: "Lookups switched off", waiting: "Awaiting location" };
  var SRCNAME = { spansh: "Spansh", edsm: "EDSM", journal: "your journal" };
  function sySrcText(src) {   // "spansh+journal" -> "Spansh + your journal"; "journal" -> "From your journal only"
    if (!src || src === "journal") return "From your journal only";
    return src.split("+").map(function (p) { return SRCNAME[p] || p; }).join(" + ");
  }
  S.syMode = "auto"; S.syFocus = "switch"; S.syGrab = false; S.syHeld = false; S.syRot = 0; S.syTilt = -12; S.syZoom = 1;   // (zoom: a planet or star)
  // the picture's options: maximised, and an Odyssey settlement's schematic (view: planet or schematic; anim:
  // the zoom between them; plans: its economy's layouts, idx: the one showing; picking: choosing one;
  // rot / tilt: the schematic's heading and tilt; icons: which icons it shows)
  S.sc = { max: false, view: "planet", anim: null, plans: null, idx: 0, picking: false, rot: 0, tilt: 0, zoom: 1, pan: [0, 0],
           icons: { term: false, door: false, power: false, exp: false, loot: false, cz: false },
           align: null };   // Align layout, while on (see scAlign)
  var PX = 1;   // how much of the 140-wide picture one screen pixel covers
  var VB = { x: 0, y: 0, w: 140, h: 140 };   // the part of the picture showing: maximised, it takes the shape of its space
  function u(n) { return (n * PX).toFixed(2); }

  function syDay(iso) {
    if (!iso) return "";
    var d = new Date(iso), now = new Date();
    if (isNaN(d)) return "";
    if (d.toDateString() === now.toDateString()) return "today";
    if (d.toDateString() === new Date(now - 864e5).toDateString()) return "yesterday";
    return d.toLocaleDateString("en-GB", d.getFullYear() === now.getFullYear() ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" });
  }
  function syKm(km) { return Number(km).toLocaleString("en-GB") + "km"; }

  // picture: orthographic globe with dashed grid, surface sites and you; or a station wireframe
  function syOrtho(lat, lon, lat0, lon0) {
    var R = SYW.R2D, la = lat * R, lo = lon * R, la0 = lat0 * R, lo0 = lon0 * R;
    var cosc = Math.sin(la0) * Math.sin(la) + Math.cos(la0) * Math.cos(la) * Math.cos(lo - lo0);
    return { x: SYW.c + SYW.r * Math.cos(la) * Math.sin(lo - lo0),
             y: SYW.c - SYW.r * (Math.cos(la0) * Math.sin(la) - Math.sin(la0) * Math.cos(la) * Math.cos(lo - lo0)),
             vis: cosc > 0 };
  }
  function syPath(d, front, grid) {
    return '<path d="' + d + '" fill="none" stroke="' + (front ? (grid ? "#25b85c" : "#45f08a") : "#1d4a2a") +
      '" stroke-width="' + u(front ? (grid ? 0.9 : 1.3) : 0.8) + '" stroke-dasharray="' + (front ? u(4) + " " + u(2) : u(2) + " " + u(3)) + '"></path>';
  }
  // your targets (2 Nav › Tgt) on a planet: a green diamond, ringed when it's the one selected
  function syTgtMark(p, lit) {
    var d = (lit ? 4.5 : 3) * PX, x = p.x, y = p.y;
    return '<polygon points="' + [[x, y - d], [x + d, y], [x, y + d], [x - d, y]].map(function (q) { return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" ") +
      '" fill="#8affc1"></polygon>' + (lit ? '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + u(9) + '" fill="none" stroke="#8affc1" stroke-width="' + u(1.2) + '"></circle>' : "");
  }
  function syTgtsAll() {   // the targets on the planet showing (its own, or the one a selected site or target is on)
    var e = S.syEntry || {}, pic = e.pic || {};
    if (pic.kind === "globe") return pic.tgts || [];
    var host = pic.kind === "surface" ? (S.syByName || {})[(pic.body || "").toLowerCase()] : null;
    return host ? host.pic.tgts || [] : [];
  }
  function syGlobe(sites, hl, me, rot, tilt, star, tgts) {
    var out = ['<circle cx="70" cy="70" r="62" fill="#07140b" stroke="#45f08a" stroke-width="' + u(1.3) + '" stroke-dasharray="' + u(4) + " " + u(2) + '"></circle>'];
    var front = [], back = [];
    function line(pts) {
      var cur = [], vis = null;
      function flush() { if (cur.length > 1) (vis ? front : back).push("M" + cur.join(" L")); cur = []; }
      pts.forEach(function (p) {
        if (vis !== null && p.vis !== vis) { var last = cur[cur.length - 1]; flush(); if (last) cur.push(last); }
        vis = p.vis;
        cur.push(p.x.toFixed(1) + " " + p.y.toFixed(1));
      });
      flush();
    }
    var lat, lon, pts;
    for (lat = -60; lat <= 60; lat += 30) { pts = []; for (lon = -180; lon <= 180; lon += 6) pts.push(syOrtho(lat, lon, tilt, rot)); line(pts); }
    for (lon = -180; lon < 180; lon += 30) { pts = []; for (lat = -90; lat <= 90; lat += 6) pts.push(syOrtho(lat, lon, tilt, rot)); line(pts); }
    back.forEach(function (d) { out.push(syPath(d, false, true)); });
    front.forEach(function (d) { out.push(syPath(d, true, true)); });
    if (star) {
      for (var a = 0; a < 360; a += 20) {
        var t = (a + rot * 0.5) * SYW.R2D, r1 = 65, r2 = a % 40 ? 70 : 74;
        out.push('<path d="M' + (70 + r1 * Math.cos(t)).toFixed(1) + " " + (70 + r1 * Math.sin(t)).toFixed(1) + " L" +
                 (70 + r2 * Math.cos(t)).toFixed(1) + " " + (70 + r2 * Math.sin(t)).toFixed(1) + '" stroke="#e3a24a" stroke-width="' + u(1.2) + '"></path>');
      }
    }
    (sites || []).forEach(function (s) {
      if (s.lat == null) return;
      var p = syOrtho(s.lat, s.lon, tilt, rot);
      if (!p.vis) return;
      if (s.name === hl) {
        out.push('<rect x="' + (p.x - 4 * PX).toFixed(1) + '" y="' + (p.y - 4 * PX).toFixed(1) + '" width="' + u(8) + '" height="' + u(8) + '" fill="#e3a24a"></rect>' +
                 '<rect x="' + (p.x - 8 * PX).toFixed(1) + '" y="' + (p.y - 8 * PX).toFixed(1) + '" width="' + u(16) + '" height="' + u(16) +
                 '" fill="none" stroke="#e3a24a" stroke-width="' + u(1) + '"></rect>');
      } else {
        out.push('<rect x="' + (p.x - 2.5 * PX).toFixed(1) + '" y="' + (p.y - 2.5 * PX).toFixed(1) + '" width="' + u(5) + '" height="' + u(5) + '" fill="#e3a24a" opacity="0.85"></rect>');
      }
    });
    (tgts || []).forEach(function (t) {
      var p = syOrtho(t.lat, t.lon, tilt, rot);
      if (p.vis) out.push(syTgtMark(p, t.name === hl));
    });
    if (me) {
      var m = syOrtho(me.lat, me.lon, tilt, rot);
      var c5 = 5 * PX;
      if (m.vis) out.push('<path d="M' + (m.x - c5).toFixed(1) + " " + (m.y - c5).toFixed(1) + " L" + (m.x + c5).toFixed(1) + " " + (m.y + c5).toFixed(1) +
                          " M" + (m.x + c5).toFixed(1) + " " + (m.y - c5).toFixed(1) + " L" + (m.x - c5).toFixed(1) + " " + (m.y + c5).toFixed(1) +
                          '" stroke="#8affc1" stroke-width="' + u(2) + '" fill="none"></path>');
    }
    return out.join("");
  }

  // a planet zoomed in: the part of it in the picture, its grid at a spacing that suits the zoom (with the next
  // finer one faintly in between as it comes), its settlements at their real size once they're bigger than a
  // marker - those with a confirmed layout drawn as their schematic - you, and (near the hand-over) the
  // settlement's schematic growing in
  var SC_SHOW = 8, SC_BOX = 24, SC_FULL = 160;   // screen pixels across: a schematic shows / loses its yellow box / gets names and icons
  var SY_FETCHING = {};   // the layout types being fetched to draw settlements on a planet
  function syGlobeNear(rot, tilt, m, hl) {
    var R = SYW.r * m, km = syPlanetKm(), hw = VB.w / 2, hh = VB.h / 2, reach = Math.hypot(hw, hh), out = [];
    var y = (S.data || {}).syst || {}, me = y.me, t = S.desc.lock;
    if (R < reach * 1.02) out.push('<circle cx="70" cy="70" r="' + R.toFixed(2) + '" fill="#07140b" stroke="#45f08a" stroke-width="' + u(1.3) +
                                   '" stroke-dasharray="' + u(4) + " " + u(2) + '"></circle>');
    else out.push('<rect x="' + VB.x.toFixed(2) + '" y="' + VB.y.toFixed(2) + '" width="' + VB.w.toFixed(2) + '" height="' + VB.h.toFixed(2) + '" fill="#07140b"></rect>');
    function proj(lat, lon) { var p = syOrtho(lat, lon, tilt, rot); return { x: 70 + (p.x - 70) * m, y: 70 + (p.y - 70) * m, vis: p.vis }; }
    var across = 2 * Math.min(hw, hh) / R / SYW.R2D, win = Math.min(90, reach * 1.1 / R / SYW.R2D);   // degrees
    var gi = 0;
    while (gi < GRID.length - 1 && across / GRID[gi] < 3) gi++;
    S.syGrid = GRID[gi];
    var la0 = Math.max(-90, tilt - win), la1 = Math.min(90, tilt + win), cl = Math.cos(tilt * SYW.R2D);
    var lw = Math.abs(tilt) + win >= 89 || cl < 0.02 ? 180 : Math.min(180, win / cl), lo0 = rot - lw, lo1 = rot + lw;
    function grid(g, faint) {
      var paths = [], k, i, pts, v;
      function line(pts) {   // the near side only
        var cur = [];
        pts.forEach(function (p) {
          if (p.vis) cur.push(p.x.toFixed(2) + " " + p.y.toFixed(2));
          else { if (cur.length > 1) paths.push("M" + cur.join(" L")); cur = []; }
        });
        if (cur.length > 1) paths.push("M" + cur.join(" L"));
      }
      for (k = Math.ceil(la0 / g - 1e-9); k * g <= la1 + 1e-9; k++) {   // parallels
        v = k * g;
        if (Math.abs(v) >= 90) continue;
        pts = [];
        for (i = 0; i <= 48; i++) pts.push(proj(v, lo0 + (lo1 - lo0) * i / 48));
        line(pts);
      }
      for (k = Math.ceil(lo0 / g - 1e-9); k * g <= lo1 + 1e-9; k++) {   // meridians
        v = k * g;
        pts = [];
        for (i = 0; i <= 48; i++) pts.push(proj(la0 + (la1 - la0) * i / 48, v));
        line(pts);
      }
      paths.forEach(function (d) {
        out.push('<path d="' + d + '" fill="none" stroke="' + (faint ? "#1d4a2a" : "#25b85c") + '" stroke-width="' + u(faint ? 0.8 : 0.9) +
                 '" stroke-dasharray="' + (faint ? u(2) + " " + u(3) : u(4) + " " + u(2)) + '"></path>');
      });
    }
    if (gi < GRID.length - 1 && across / GRID[gi + 1] <= 14) grid(GRID[gi + 1], true);   // the next finer, coming in
    grid(GRID[gi], false);
    var mh = t ? syHandover(t) : 0, grow = t && t.plan && m >= mh * 0.6;   // the schematic takes over at mh
    var upm = km ? R / (km * 1000) : 0, plans = [], marks = [];   // (the picture's units per metre on the ground here)
    S.syShown = {};   // how each settlement with a schematic shows: {wpx: its size on the screen, how: "plan", "plan+box" or "box"}
    function mark(p, lit) {   // a settlement's yellow box
      marks.push(lit ? '<rect x="' + (p.x - 4 * PX).toFixed(1) + '" y="' + (p.y - 4 * PX).toFixed(1) + '" width="' + u(8) + '" height="' + u(8) + '" fill="#e3a24a"></rect>' +
                       '<rect x="' + (p.x - 8 * PX).toFixed(1) + '" y="' + (p.y - 8 * PX).toFixed(1) + '" width="' + u(16) + '" height="' + u(16) +
                       '" fill="none" stroke="#e3a24a" stroke-width="' + u(1) + '"></rect>'
                     : '<rect x="' + (p.x - 2.5 * PX).toFixed(1) + '" y="' + (p.y - 2.5 * PX).toFixed(1) + '" width="' + u(5) + '" height="' + u(5) + '" fill="#e3a24a" opacity="0.85"></rect>');
    }
    sySitesAll().forEach(function (s) {
      if (s.lat == null) return;
      var p = proj(s.lat, s.lon);
      if (!p.vis || p.x < VB.x - 40 || p.x > VB.x + VB.w + 40 || p.y < VB.y - 40 || p.y > VB.y + VB.h + 40) return;
      var mine = t && s.key === t.key, lit = s.name === hl || mine;
      // a confirmed layout is drawn at its real size, in its real place, once it's a few pixels across: the yellow box
      // over it while it's small, alone when it's smaller still (the one going down to: its layout to pick from, near the hand-over)
      var plan = sySitePlan(s) || (mine && grow ? t.plan : null);
      if (plan && upm) {
        var wpx = ED.schem.sizeM(plan) * upm / PX, big = wpx >= SC_FULL;   // how big it is on the screen (pixels)
        if (wpx >= SC_SHOW) plans.push(ED.schem.draw(plan, { at: [p.x, p.y], k: upm * ED.schem.mpu(plan), rot: sySiteRot(s, plan), tilt: 0,
                                                              px: PX, max: big && S.sc.max, icons: big ? S.sc.icons : {} }));
        if (wpx < SC_BOX) mark(p, lit);
        S.syShown[s.key] = { wpx: wpx, how: wpx < SC_SHOW ? "box" : wpx < SC_BOX ? "plan+box" : "plan" };
        return;
      }
      var wkm = mine && t.plan ? ED.schem.widthKm(t.plan) : DESC_KM, size = km ? wkm * R / km : 0;
      if (size > 7 * PX) {   // big enough to show its real size: its footprint
        marks.push('<rect x="' + (p.x - size / 2).toFixed(2) + '" y="' + (p.y - size / 2).toFixed(2) + '" width="' + size.toFixed(2) + '" height="' + size.toFixed(2) +
                   '" fill="none" stroke="#e3a24a" stroke-width="' + u(lit ? 1.6 : 1) + '"></rect>' +
                   '<rect x="' + (p.x - 2 * PX).toFixed(2) + '" y="' + (p.y - 2 * PX).toFixed(2) + '" width="' + u(4) + '" height="' + u(4) + '" fill="#e3a24a"></rect>');
      } else {
        mark(p, lit);
      }
    });
    syTgtsAll().forEach(function (tg) {
      var p = proj(tg.lat, tg.lon);
      if (p.vis && p.x > VB.x - 20 && p.x < VB.x + VB.w + 20 && p.y > VB.y - 20 && p.y < VB.y + VB.h + 20)
        marks.push(syTgtMark(p, tg.name === hl || tg.key === (S.syEntry || {}).key));
    });
    out.push.apply(out, plans.concat(marks));
    var e = S.syEntry || {}, pic = e.pic || {}, host = pic.kind === "surface" ? (S.syByName || {})[(pic.body || "").toLowerCase()] : e;
    if (me && host && me.key === host.key) {   // you, on this planet
      var mp = proj(me.lat, me.lon), c5 = 5 * PX;
      if (mp.vis) out.push('<path d="M' + (mp.x - c5).toFixed(1) + " " + (mp.y - c5).toFixed(1) + " L" + (mp.x + c5).toFixed(1) + " " + (mp.y + c5).toFixed(1) +
                           " M" + (mp.x + c5).toFixed(1) + " " + (mp.y - c5).toFixed(1) + " L" + (mp.x - c5).toFixed(1) + " " + (mp.y + c5).toFixed(1) +
                           '" stroke="#8affc1" stroke-width="' + u(2) + '" fill="none"></path>');
    }
    return out.join("");
  }
  // the range bar, bottom left: a round length (1, 2 or 5 of a unit) up to about a quarter of the picture across,
  // in the units the game uses - metres, km, then megametres (from 1,000 km) and light-seconds (past 30 Mm)
  var LS_M = 299792458;
  function syRange(upm) {   // upm: the picture's units per metre
    if (!(upm > 0) || !isFinite(upm)) return "";
    var most = VB.w * 0.28 / upm;   // metres
    var unit = most < 1000 ? [1, "m"] : most < 1e6 ? [1000, "km"] : most < 3e7 ? [1e6, "Mm"] : [LS_M, "ls"];
    var v = most / unit[0], p = Math.pow(10, Math.floor(Math.log10(v)) ), n = p;
    [5, 2, 1].some(function (f) { if (f * p <= v * (1 + 1e-9)) { n = f * p; return true; } return false; });
    var len = n * unit[0] * upm, x0 = VB.x + 10 * PX, x1 = x0 + len, yb = VB.y + VB.h - 7 * PX, tk = 4 * PX;
    var f = function (q) { return q.toFixed(2); }, txt = parseFloat(n.toPrecision(3)) + " " + unit[1];
    return '<path data-range="1" d="M' + f(x0) + " " + f(yb - tk) + " L" + f(x0) + " " + f(yb) + " L" + f(x1) + " " + f(yb) + " L" + f(x1) + " " + f(yb - tk) +
      '" fill="none" stroke="#8affc1" stroke-width="' + u(1.4) + '"></path>' +
      '<text data-range="1" x="' + f(Math.max((x0 + x1) / 2, x0 - 2 * PX + txt.length * 6 * PX)) + '" y="' + f(yb - 13 * PX) + '" data-band="1" data-case="keep" font-family="VGA, monospace" font-size="' + u(14) +
      '" fill="#8affc1" text-anchor="middle" dominant-baseline="central">' + txt + "</text>";
  }
  function syGridText() {   // "GRID 1° (≈ 35 KM)": the spacing, and what that is on this planet
    var g = S.syGrid || 30, d = syPlanetKm() * Math.PI / 180 * g;
    var len = d >= 100 ? Math.round(d).toLocaleString("en-GB") + " km" : d >= 10 ? Math.round(d) + " km" : d >= 1 ? d.toFixed(1) + " km" :
      d * 1000 >= 10 ? Math.round(d * 1000) + " m" : (d * 1000).toFixed(1) + " m";
    return "Grid " + parseFloat(g.toPrecision(3)) + "\u00b0" + (d ? " (\u2248 " + len + ")" : "");
  }

  function syBox(x0, x1, y0, y1, z0, z1) {
    var v = [[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]];
    return [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]].map(function (e) { return [v[e[0]], v[e[1]]]; });
  }
  function syRing(r, y, n, axis) {   // a circle of segments (axis "y": flat ring; "z": upright)
    var segs = [], prev = null;
    for (var i = 0; i <= n; i++) {
      var a = i / n * 2 * Math.PI, p = axis === "z" ? [r * Math.cos(a), r * Math.sin(a), y] : [r * Math.cos(a), y, r * Math.sin(a)];
      if (prev) segs.push([prev, p]);
      prev = p;
    }
    return segs;
  }
  function syRingX(r, x, n) {   // a circle of segments standing across the x axis
    var segs = [], prev = null;
    for (var i = 0; i <= n; i++) {
      var a = i / n * 2 * Math.PI, p = [x, r * Math.cos(a), r * Math.sin(a)];
      if (prev) segs.push([prev, p]);
      prev = p;
    }
    return segs;
  }
  function syCyl(cx, cz, r, y0, y1, n) {   // an upright cylinder: its two rims and a few sides
    var segs = [], prev = null;
    for (var i = 0; i <= n; i++) {
      var a = i / n * 2 * Math.PI, lo = [cx + r * Math.cos(a), y0, cz + r * Math.sin(a)], hi = [cx + r * Math.cos(a), y1, cz + r * Math.sin(a)];
      if (prev) { segs.push([prev[0], lo], [prev[1], hi]); }
      if (i < n && i % Math.max(1, Math.round(n / 4)) === 0) segs.push([lo, hi]);
      prev = [lo, hi];
    }
    return segs;
  }
  function syShape(kind) {
    var e = [], i, j, k, V;
    if (kind === "beacon") {   // a nav beacon: a sphere in two halves either side of a band, with antennae
      [1, -1].forEach(function (sx) {
        [0.22, 0.55, 0.82].forEach(function (x) { e = e.concat(syRingX(Math.sqrt(1 - x * x), sx * x, 16)); });
        for (i = 0; i < 6; i++) {   // the halves' meridians, from the band to the pole
          var ph = i / 6 * 2 * Math.PI, last = null;
          for (j = 0; j <= 5; j++) {
            var th = Math.asin(0.22) + (Math.PI / 2 - Math.asin(0.22)) * j / 5, q = [sx * Math.sin(th), Math.cos(th) * Math.cos(ph), Math.cos(th) * Math.sin(ph)];
            if (last) e.push([last, q]);
            last = q;
          }
        }
      });
      e = e.concat(syRingX(1.04, 0.16, 8)).concat(syRingX(1.04, -0.16, 8));   // the band: two octagons and their struts
      for (i = 0; i < 8; i++) { var b = i / 8 * 2 * Math.PI; e.push([[0.16, 1.04 * Math.cos(b), 1.04 * Math.sin(b)], [-0.16, 1.04 * Math.cos(b), 1.04 * Math.sin(b)]]); }
      e = e.concat(syBox(-0.14, 0.14, 0.98, 1.2, -0.28, 0.28));   // the panel on the band
      [0.6, 2.6, 4.3].forEach(function (b, n) {   // antennae out of the band
        var c = Math.cos(b), d = Math.sin(b), L = n === 0 ? 1.75 : 1.5;
        e.push([[0, 1.04 * c, 1.04 * d], [0, L * c, L * d]]);
      });
      return { edges: e, scale: 34 };
    }
    if (kind === "tourist") {   // a tourist beacon: a small body with two fins raised in a V, a drum and dish below
      e = syBox(-0.36, 0.36, -0.12, 0.34, -0.24, 0.24);
      [[-1, 1.25, 0.62], [1, 1.0, 0.56]].forEach(function (f) {   // the fins (the left one taller), each with its tip band
        var s = f[0], top = f[1], out = f[2], P = [[s * 0.36, 0.02, -0.18], [s * 0.36, 0.02, 0.18], [s * out, top, 0.18], [s * out, top, -0.18]];
        for (i = 0; i < 4; i++) e.push([P[i], P[(i + 1) % 4]]);
        var tb = top - 0.28, tx = s * (0.36 + (out - 0.36) * (tb - 0.02) / (top - 0.02));
        e.push([[tx, tb, -0.18], [tx, tb, 0.18]]);
      });
      e = e.concat(syCyl(0, 0, 0.17, -0.62, -0.12, 12)).concat(syRing(0.3, -0.72, 16)).concat(syRing(0.12, -0.86, 10));
      e.push([[0, -0.62, 0], [0, -0.86, 0]], [[-0.06, 0.34, 0], [-0.06, 1.5, 0]]);   // the mast and the aerial on top
      return { edges: e, scale: 44 };
    }
    if (kind === "installation") {   // an installation: drum modules and blocks joined by long trusses in a loop
      var at = { a: [-1.2, -0.18], b: [-0.31, -0.69], c: [0.49, -0.64], d: [1.2, 0.22], m: [-0.02, -0.04], n: [-0.13, 0.71] };
      ["a", "b", "c", "d"].forEach(function (key) {   // the drums
        var c = at[key];
        e = e.concat(syCyl(c[0], c[1], 0.27, -0.09, 0.09, 12)).concat(syCyl(c[0], c[1], 0.1, -0.11, 0.11, 6));
      });
      ["m", "n"].forEach(function (key) { var c = at[key]; e = e.concat(syBox(c[0] - 0.2, c[0] + 0.2, -0.12, 0.12, c[1] - 0.2, c[1] + 0.2)); });
      [["a", "b"], ["b", "m"], ["m", "c"], ["c", "d"], ["d", "n"], ["n", "a"]].forEach(function (t) {   // the trusses: two rails
        var p = at[t[0]], q = at[t[1]], L = Math.hypot(q[0] - p[0], q[1] - p[1]), nx = -(q[1] - p[1]) / L * 0.03, nz = (q[0] - p[0]) / L * 0.03;
        e.push([[p[0] + nx, 0, p[1] + nz], [q[0] + nx, 0, q[1] + nz]], [[p[0] - nx, 0, p[1] - nz], [q[0] - nx, 0, q[1] - nz]]);
      });
      return { edges: e, scale: 40, pitch: -30 };
    }
    if (kind === "construction") {   // an orbital construction site: a tall spine of tanks, a ring of modules, a wheel, side arrays
      e.push([[0, 1.4, 0], [0, -1.25, 0]]);
      e = e.concat(syBox(-0.05, 0.05, 1.0, 1.12, -0.05, 0.05)).concat(syBox(-0.09, 0.09, 0.56, 0.92, -0.09, 0.09));
      [[0.08, 0.08], [-0.08, 0.08], [0.08, -0.08], [-0.08, -0.08]].forEach(function (c) { e = e.concat(syCyl(c[0], c[1], 0.065, 0.0, 0.48, 8)); });
      e = e.concat(syRing(0.58, -0.2, 18)).concat(syRing(0.36, -0.2, 14));   // the ring of modules, on its lattice
      for (i = 0; i < 8; i++) {
        var g = i / 8 * 2 * Math.PI, cx = 0.58 * Math.cos(g), cz = 0.58 * Math.sin(g);
        e.push([[0, -0.2, 0], [0.36 * Math.cos(g), -0.2, 0.36 * Math.sin(g)]]);
        e = e.concat(syBox(cx - 0.06, cx + 0.06, -0.26, -0.14, cz - 0.06, cz + 0.06));
      }
      e = e.concat(syRing(0.46, -0.48, 20)).concat(syRing(0.46, -0.56, 20)).concat(syRing(0.08, -0.52, 8));   // the wheel
      for (i = 0; i < 8; i++) { var w = i / 8 * 2 * Math.PI; e.push([[0.08 * Math.cos(w), -0.52, 0.08 * Math.sin(w)], [0.46 * Math.cos(w), -0.52, 0.46 * Math.sin(w)]]); }
      e.push([[-0.12, -1.15, 0], [0.12, -1.15, 0]], [[0, -1.15, -0.12], [0, -1.15, 0.12]]);   // the foot
      [[-1, 1.45, 0.95, 1.2, 0.3], [1, 1.25, 0.95, 1.0, 0.45]].forEach(function (a) {   // the arrays either side, on booms
        var s = a[0], x0 = s * a[1], x1 = s * a[2], y1 = a[3], y0 = a[4];
        e.push([[x0, y0, 0], [x1, y0, 0]], [[x0, y1, 0], [x1, y1, 0]], [[x1, (y0 + y1) / 2, 0], [s * 0.09, (y0 + y1) / 2, 0]]);
        for (i = 0; i <= 4; i++) { var xx = x0 + (x1 - x0) * i / 4; e.push([[xx, y0, 0], [xx, y1, 0]]); }
      });
      return { edges: e, scale: 44 };
    }
    if (kind === "squadron") kind = "carrier";
    function byLength(V, len, tol) {
      for (i = 0; i < V.length; i++) for (j = i + 1; j < V.length; j++) {
        var d = 0;
        for (k = 0; k < 3; k++) d += (V[i][k] - V[j][k]) * (V[i][k] - V[j][k]);
        if (Math.abs(Math.sqrt(d) - len) < tol) e.push([V[i], V[j]]);
      }
    }
    if (kind === "coriolis") {
      V = [];
      [1, -1].forEach(function (a) { [1, -1].forEach(function (b) { V.push([a, b, 0], [a, 0, b], [0, a, b]); }); });
      byLength(V, Math.SQRT2, 1e-6);
      return { edges: e, scale: 42, slot: [[1, 0.36, 0.11], [1, -0.36, 0.11], [1, -0.36, -0.11], [1, 0.36, -0.11]] };
    }
    if (kind === "dodec") {
      var g = (1 + Math.sqrt(5)) / 2, h = 1 / g;
      V = [];
      [1, -1].forEach(function (a) { [1, -1].forEach(function (b) {
        [1, -1].forEach(function (c) { V.push([a, b, c]); });
        V.push([0, a * h, b * g], [a * h, b * g, 0], [a * g, 0, b * h]);
      }); });
      byLength(V, 2 * h, 1e-6);
      return { edges: e, scale: 34, slot: [[1.2, 0.3, 0.1], [1.2, -0.3, 0.1], [1.2, -0.3, -0.1], [1.2, 0.3, -0.1]] };
    }
    if (kind === "asteroid") {
      var t = (1 + Math.sqrt(5)) / 2, jit = [1.1, 0.85, 1.0, 1.2, 0.9, 1.05, 0.8, 1.15, 0.95, 1.1, 0.88, 1.0];
      V = [[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]];
      byLength(V, 2, 1e-6);
      e = e.map(function (s) { return s.map(function (p) { var q = jit[V.indexOf(p)]; return [p[0] * q, p[1] * q, p[2] * q]; }); });
      return { edges: e, scale: 30 };
    }
    if (kind === "orbis") {
      e = syRing(1.0, 0, 28).concat(syRing(0.82, 0, 28)).concat(syBox(-0.14, 0.14, -0.95, 0.95, -0.14, 0.14));
      for (i = 0; i < 4; i++) { var a = i * Math.PI / 2; e.push([[0.14 * Math.cos(a), 0, 0.14 * Math.sin(a)], [0.82 * Math.cos(a), 0, 0.82 * Math.sin(a)]]); }
      return { edges: e, scale: 54 };
    }
    if (kind === "ocellus") {
      e = syRing(0.9, 0, 24).concat(syRing(0.62, 0.65, 18)).concat(syRing(0.62, -0.65, 18)).concat(syRing(0.9, 0, 24, "z"))
        .concat(syBox(-0.1, 0.1, -1.2, 1.2, -0.1, 0.1));
      return { edges: e, scale: 50, slot: [[0, 0.2, 0.9], [0, -0.2, 0.9], [0.12, -0.2, 0.89], [0.12, 0.2, 0.89]] };
    }
    if (kind === "megaship") {
      e = syBox(-1.3, 1.3, -0.16, 0.16, -0.24, 0.24).concat(syBox(0.7, 1.05, 0.16, 0.42, -0.14, 0.14));
      for (i = -2; i <= 2; i++) e = e.concat(syBox(i * 0.42 - 0.05, i * 0.42 + 0.05, -0.26, 0.26, -0.34, 0.34));
      return { edges: e, scale: 46 };
    }
    if (kind === "carrier") {
      e = syBox(-1.3, 1.1, -0.1, 0.06, -0.36, 0.36).concat(syBox(1.1, 1.4, -0.1, 0.06, -0.2, 0.2))
        .concat(syBox(-1.05, -0.7, 0.06, 0.55, 0.12, 0.3)).concat(syBox(-0.4, 0.6, -0.3, -0.1, -0.2, 0.2));
      return { edges: e, scale: 46 };
    }
    if (kind === "settlement") {
      e = syBox(-1, 1, -0.02, 0, -1, 1).concat(syBox(-0.6, -0.1, 0, 0.35, -0.5, 0)).concat(syBox(0.2, 0.7, 0, 0.22, -0.2, 0.5))
        .concat(syBox(-0.4, -0.15, 0, 0.6, 0.3, 0.55));
      return { edges: e, scale: 46 };
    }
    e = syBox(-0.22, 0.22, -1.15, 1.15, -0.22, 0.22).concat(syBox(-0.95, 0.95, 0.35, 0.58, -0.14, 0.14))
      .concat(syBox(-0.14, 0.14, -0.62, -0.38, -0.95, 0.95)).concat(syBox(-0.42, 0.42, 1.15, 1.32, -0.42, 0.42));
    return { edges: e, scale: 46 };   // outpost
  }
  function syWire(kind, rot, tilt) {
    var sh = S.syShapes[kind] || (S.syShapes[kind] = syShape(kind));
    var yaw = rot * SYW.R2D, pitch = (tilt + (sh.pitch || 0)) * SYW.R2D, s = sh.scale, out = [], back = [], front = [];   // pitch: a flat one is seen from higher up
    function rp(p) {
      var x = p[0] * Math.cos(yaw) + p[2] * Math.sin(yaw), z = -p[0] * Math.sin(yaw) + p[2] * Math.cos(yaw), y = p[1];
      return [x, y * Math.cos(pitch) - z * Math.sin(pitch), y * Math.sin(pitch) + z * Math.cos(pitch)];
    }
    function xy(p) { return (70 + p[0] * s).toFixed(1) + " " + (70 - p[1] * s).toFixed(1); }
    sh.edges.forEach(function (e) {
      var a = rp(e[0]), b = rp(e[1]), d = "M" + xy(a) + " L" + xy(b);
      ((a[2] + b[2]) / 2 < -0.15 ? back : front).push(d);
    });
    back.forEach(function (d) { out.push(syPath(d, false)); });
    front.forEach(function (d) { out.push(syPath(d, true)); });
    if (sh.slot) {
      var sl = sh.slot.map(rp);
      if ((sl[0][2] + sl[2][2]) / 2 > -0.1) {
        out.push('<polygon points="' + sl.map(function (p) { return xy(p).replace(" ", ","); }).join(" ") +
                 '" fill="#e3a24a" fill-opacity="0.35" stroke="#e3a24a" stroke-width="' + u(1.2) + '"></polygon>');
      }
    }
    return out.join("");
  }
  S.syShapes = {};

  // the surface sites drawn on the current globe, with where they appear right now
  function sySitesShown() {
    var e = S.syEntry, pic = (e && e.pic) || {}, sites = [];
    if (pic.kind === "globe") sites = pic.sites || [];
    else if (pic.kind === "surface") { var host = S.syByName[(pic.body || "").toLowerCase()]; sites = host ? host.pic.sites || [] : []; }
    var k = S.syZoom || 1;   // (where they are on the screen, the planet zoomed about the middle)
    return sites.map(function (s) { var p = syOrtho(s.lat, s.lon, S.syTilt, S.syRot); return { site: s, x: 70 + (p.x - 70) * k, y: 70 + (p.y - 70) * k, vis: p.vis }; });
  }
  function syIsGlobe() { var k = ((S.syEntry || {}).pic || {}).kind; return k === "globe" || k === "star" || (k === "surface" && !!S.syByName[(S.syEntry.pic.body || "").toLowerCase()]); }

  function planetHtml(e, rot, tilt, hl) {   // the planet (with its surface sites) or the station
    var y = (S.data || {}).syst || {}, pic = e.pic || {}, me = y.me;
    if (pic.kind === "globe" || pic.kind === "star") {
      return syGlobe(pic.sites, hl || ((y.auto || {}).why === "nearest" ? S.syAutoSite : null), me && me.key === e.key ? me : null,
                     rot, tilt, pic.kind === "star", pic.tgts);
    }
    if (pic.kind === "surface") {
      var host = S.syByName[(pic.body || "").toLowerCase()];
      return host ? syGlobe(host.pic.sites, hl || e.name, me && me.key === host.key ? me : null, rot, tilt, false, host.pic.tgts)
                  : syWire("settlement", rot, tilt);
    }
    return syWire(pic.kind, rot, tilt);
  }
  function syMeasure() {   // the picture's size now: the 140 x 140 middle always shows; a wide (or tall) space shows more round it
    var svg = $("sy-svg"), cw = svg.clientWidth, ch = svg.clientHeight;
    if (cw > 0 && ch > 0) {
      var w = 140 * Math.max(1, cw / ch), h = 140 * Math.max(1, ch / cw);
      if (Math.abs(w - VB.w) > 0.05 || Math.abs(h - VB.h) > 0.05) {
        VB = { x: 70 - w / 2, y: 70 - h / 2, w: w, h: h };
        svg.setAttribute("viewBox", VB.x.toFixed(2) + " " + VB.y.toFixed(2) + " " + w.toFixed(2) + " " + h.toFixed(2));
      }
      PX = VB.w / cw;
    }
  }
  function syPicture() {   // redraws the picture for the selected entry at the current rotation
    var e = S.syEntry, svg = $("sy-svg");
    if (!e) return;
    syMeasure();
    var html;
    S.syAim = null;
    if (S.sc.anim) {
      html = scZoomFrame();
    } else if (S.sc.view === "schematic" && S.sc.plans) {
      html = ED.schem.draw(S.sc.plans[S.sc.idx], scOpts({ px: PX, max: S.sc.max, icons: S.sc.icons, me: scYou(scHeading()) }));
    } else {
      // while grabbed, a planet shows the cursor; the site nearest it is what a long pull selects
      if (S.syGrab && syIsGlobe()) {
        var best = 17;
        sySitesShown().forEach(function (p) {
          var d = Math.hypot(p.x - 70, p.y - 70);
          if (p.vis && d < best) { best = d; S.syAim = p.site; }
        });
      }
      var k = syIsGlobe() ? S.syZoom || 1 : 1, base = PX;   // a planet or star zoomed in: drawn bigger about the middle
      if (syDescOn() && k >= 2) {   // maximised and well in: the part in view, at a grid that suits (the descent)
        html = syGlobeNear(S.syRot, S.syTilt, k, S.syAim ? S.syAim.name : null);
      } else {
        S.syGrid = 30;
        if (k > 1.001) PX = base / k;
        html = planetHtml(e, S.syRot, S.syTilt, S.syAim ? S.syAim.name : null);
        PX = base;
        if (k > 1.001) html = '<g transform="translate(70 70) scale(' + k.toFixed(4) + ') translate(-70 -70)">' + html + "</g>";
      }
      if (S.syGrab && syIsGlobe()) {   // the cursor: an open circle with a plus
        html += '<circle cx="70" cy="70" r="' + u(9) + '" fill="none" stroke="#8affc1" stroke-width="' + u(1.5) + '"></circle>' +
                '<path d="M70 ' + (70 - 8 * PX).toFixed(1) + " L70 " + (70 + 8 * PX).toFixed(1) + " M" + (70 - 8 * PX).toFixed(1) + " 70 L" +
                (70 + 8 * PX).toFixed(1) + ' 70" stroke="#8affc1" stroke-width="' + u(1.5) + '"></path>';
      }
    }
    if (S.sc.max && !S.sc.anim) {   // maximised: the range bar (a planet or star's scale at the middle of the picture)
      html += syRange(S.sc.view === "schematic" && S.sc.plans ? ED.schem.scale(S.sc.plans[S.sc.idx], scOpts())
                      : syIsGlobe() && syPlanetKm() ? SYW.r * (S.syZoom || 1) / (syPlanetKm() * 1000) : 0);
    }
    svg.innerHTML = html;
    ED.pixel.draw(svg, $("sy-px"), VB);   // what shows: the drawing in the screen's coarse pixels
    var lab = S.sc.view === "schematic" && !S.sc.anim
      ? scLabel()
      : (S.syAim ? "(+) " + S.syAim.name : S.desc.lock ? "To " + S.desc.lock.name : "Rotate") +
        (syDescOn() ? " \u00b7 " + syGridText() : "") +
        (syIsGlobe() && S.syZoom > 1.01 ? " \u00b7 Zoom " + (S.syZoom < 10 ? S.syZoom.toFixed(1) : Math.round(S.syZoom).toLocaleString("en-GB")) + "\u00d7" : "");
    if ($("sy-rotlab").textContent !== lab) $("sy-rotlab").textContent = lab;
    if (S.sc.align) scAlignNote();
  }

  // ---- an Odyssey settlement's schematic ----
  function scSettlement() { var e = S.syEntry; return e && e.settlement ? e.settlement : null; }
  // its type (whose layouts show): the one you picked, else the data's - its economy, or (where that has no
  // layouts, as a construction site's "Colony" hasn't) what its name says, or the first type with layouts
  var SC_ORDER = ["tourism", "agriculture", "military", "industrial", "extraction", "hightech"];
  function scTypes() {   // the types that have layouts, in a set order
    var counts = (S.data || {}).schematics || {};
    var have = Object.keys(counts).filter(function (k) { return counts[k] > 0; });
    return SC_ORDER.filter(function (k) { return have.indexOf(k) >= 0; })
      .concat(have.filter(function (k) { return SC_ORDER.indexOf(k) < 0; }).sort());
  }
  function scDefault(st) {
    var types = scTypes();
    if (types.indexOf(st.category) >= 0) return st.category;
    if (st.guess && types.indexOf(st.guess) >= 0) return st.guess;
    return types[0] || st.category;
  }
  function scCategory(st) {
    if (!st) return "";
    var picked = (((S.data || {}).syst || {}).types || {})[st.key];
    return picked && scTypes().indexOf(picked) >= 0 ? picked : scDefault(st);
  }
  function scTypeName(c) { return c === "hightech" ? "High tech" : c ? c.charAt(0).toUpperCase() + c.slice(1) : "-"; }
  function scCount(st) { return st ? ((S.data || {}).schematics || {})[scCategory(st)] || 0 : 0; }
  function scSaved(st) { return st ? (((S.data || {}).syst || {}).layouts || {})[st.key] || null : null; }
  function scUnsure(st) { return !!st && !!st.unsure && !scSaved(st); }   // not known to be an Odyssey settlement (a layout confirmed: it is)
  function scPlan() { return S.sc.plans ? S.sc.plans[S.sc.idx] : null; }
  function scSavedHere() { var p = scPlan(); return !!p && scSaved(scSettlement()) === p.id; }
  function scOpts(more) {   // how the schematic is shown: heading, tilt, zoom and pan, in this picture
    return Object.assign({ rot: S.sc.rot, tilt: S.sc.tilt, zoom: S.sc.zoom, pan: S.sc.pan, hw: VB.w / 2, hh: VB.h / 2 }, more || {});
  }
  // zoom (by f, about the picture point sx, sy) and pan (by dx, dy of the picture): the COMM2 knob and
  // dials while the picture's grabbed, the mouse wheel and right-drag, two fingers
  function scZoom(f, sx, sy) {
    var plan = scPlan();
    if (!plan || S.sc.anim) return;
    var r = ED.schem.zoomAt(plan, scOpts(), sx, sy, f);
    S.sc.zoom = r.zoom; S.sc.pan = r.pan;
    syPicture();
  }
  function scPan(dx, dy) {
    var plan = scPlan();
    if (!plan || S.sc.anim) return;
    S.sc.pan = ED.schem.panBy(plan, scOpts(), dx, dy);
    syPicture();
  }
  function scWhole() { S.sc.zoom = 1; S.sc.pan = [0, 0]; syPicture(); }   // back to the whole settlement

  // ---- which way the settlement faces (its heading: the compass bearing of its layout's up), and you ----
  // The board keeps each settlement's heading for its confirmed layout: worked out when you dock on a pad
  // whose direction SrvSurvey recorded, or set with Align layout. The picture's turn (S.sc.rot) is how
  // far the layout's up is turned clockwise from the picture's up, so the picture's up points to heading - rot:
  // rot = heading puts north up; rot = heading - your heading puts the way you face up.
  function scNorm(a) { return ((a % 360) + 360) % 360; }
  function scHost() {   // the planet the selected settlement is on
    var pic = (S.syEntry || {}).pic || {};
    return pic.kind === "surface" ? (S.syByName || {})[(pic.body || "").toLowerCase()] || null : null;
  }
  function scMe() {   // you, if you're on (or over) the settlement's planet: {lat, lon, alt, hdg, r (metres)}
    var me = ((S.data || {}).syst || {}).me, host = scHost();
    return me && host && me.key === host.key ? me : null;
  }
  function scLiveH() { var me = scMe(); return me && typeof me.hdg === "number" ? scNorm(me.hdg) : null; }
  function scHdgRec(st, plan) {   // the heading kept for this settlement's layout (confirmed, and the one shown)
    st = st || scSettlement(); plan = plan || scPlan();
    var r = st && plan ? (((S.data || {}).syst || {}).headings || {})[st.key] : null;
    return r && r.layout === plan.id && scSaved(st) === plan.id ? r : null;
  }
  function scHeading() {   // the settlement's heading as things stand: the one being aligned, else the one kept
    if (S.sc.align) return S.sc.align.h;
    var r = scHdgRec();
    return r ? r.h : null;
  }
  function scStartRot() {   // a schematic opening: the way you face up if you're there, else north up (its heading known)
    var r = scHdgRec(), H = scLiveH();
    return r ? scNorm(r.h - (H != null ? H : 0)) : 0;
  }
  function scYou(h) {   // you in the plan's metres (the settlement's position at 0,0, its heading up), with h its heading
    var me = scMe(), pic = (S.syEntry || {}).pic || {}, plan = scPlan(), host = scHost();
    if (!me || h == null || pic.lat == null || !plan || !plan.metric) return null;
    var R = me.r || (host && host.radius ? host.radius * 1000 : 0), d2r = Math.PI / 180;
    if (!R) return null;
    var dN = (me.lat - pic.lat) * d2r * R, dE = (scNorm(me.lon - pic.lon + 180) - 180) * d2r * R * Math.cos(pic.lat * d2r);
    var hr = h * d2r, x = dE * Math.cos(hr) - dN * Math.sin(hr), y = dE * Math.sin(hr) + dN * Math.cos(hr);
    return { at: [x, -y], dir: typeof me.hdg === "number" ? scNorm(me.hdg - h) : null, d: Math.hypot(dN, dE) };
  }
  function scViewTilt() {   // the tilt you see the settlement at: from your height and how far away it is (up to 70°)
    var me = scMe(), pic = (S.syEntry || {}).pic || {}, host = scHost();
    if (!me || typeof me.alt !== "number" || pic.lat == null) return null;
    var R = me.r || (host && host.radius ? host.radius * 1000 : 0), d2r = Math.PI / 180;
    if (!R) return null;
    var d = Math.hypot((me.lat - pic.lat) * d2r * R, (scNorm(me.lon - pic.lon + 180) - 180) * d2r * R * Math.cos(pic.lat * d2r));
    return Math.max(0, Math.min(70, Math.atan2(d, Math.max(1, me.alt)) / d2r));
  }
  // Align layout: the schematic turns with you - the way you face stays up the picture - and you turn it
  // (COMM2 VOLUME, or drag) until it matches what you see; Confirm heading keeps it (a docking no longer
  // changes it), Cancel puts the picture back. Its tilt follows your height and distance until you tilt it.
  function scAlign() {
    if (S.sc.anim || S.sc.align || S.sc.view !== "schematic" || !scSavedHere() || S.sc.picking) return;
    var H = scLiveH(), r = scHdgRec();
    S.sc.align = { h: null, rot0: S.sc.rot, tilt0: S.sc.tilt, max0: S.sc.max, auto: true };
    if (H != null) {   // from the heading kept (if any), else the picture as it is
      S.sc.align.h = r ? r.h : scNorm(S.sc.rot + H);
      S.sc.rot = scNorm(S.sc.align.h - H);
    }
    var t = scViewTilt();
    if (t != null) S.sc.tilt = t;
    S.sc.max = true;   // aligning wants the big picture
    S.syGrab = false;
    S.syFocus = "al-ok";
    $("sy-snote").textContent = "";
    scButtons();
    syPicture();
  }
  function scAlignTrack() {   // a new position: the settlement stays put on the ground (so turns on the screen as you turn)
    var a = S.sc.align, H = scLiveH();
    if (!a || H == null) return false;
    if (a.h == null) a.h = scNorm(S.sc.rot + H);   // your heading's come in: from the picture as it is
    var rot = scNorm(a.h - H), t = a.auto ? scViewTilt() : null, moved = Math.abs(((rot - S.sc.rot + 540) % 360) - 180) > 0.05;
    S.sc.rot = rot;
    if (t != null && Math.abs(t - S.sc.tilt) > 0.05) { S.sc.tilt = t; moved = true; }
    return moved;
  }
  function scTurned() {   // you turned the schematic: aligning, that's the settlement's heading changing
    var a = S.sc.align, H = scLiveH();
    if (a && H != null) a.h = scNorm(S.sc.rot + H);
  }
  function scAlignEnd(kept) {   // Confirm heading (kept: the picture stays as aligned) or Cancel
    var a = S.sc.align;
    if (!a) return;
    S.sc.align = null;
    if (!kept) { S.sc.rot = a.rot0; S.sc.tilt = a.tilt0; }
    S.sc.max = a.max0;
    if (S.syFocus === "al-ok" || S.syFocus === "al-cancel") S.syFocus = "align";
    scButtons();
    syPicture();
  }
  function scAlignOk() {
    var a = S.sc.align, st = scSettlement(), plan = scPlan(), y = (S.data || {}).syst || {};
    if (!a || a.h == null || !st || !plan) return;
    var h = scNorm(Math.round(a.h * 10) / 10);
    fetch("/api/settlement-heading", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: st.key, layout: plan.id, heading: h, system: y.system || "", name: (S.syEntry || {}).name || "" }) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { a.failed = a.h; $("sy-alnote").textContent = "Couldn't save that"; return; }
        (y.headings = y.headings || {})[st.key] = j.heading || { layout: plan.id, h: h, src: "manual", locked: false, pad: null };
        scAlignEnd(true);
        ED.replay($("sy-pick"), "flk");
        ED.refresh();
      }, function () { a.failed = a.h; $("sy-alnote").textContent = "Couldn't reach the FT3000"; });
  }
  function scAlignNote() {   // the overlay's note: what to do, and the heading it would keep
    var al = S.sc.align, note = $("sy-alnote"), txt = "";
    if (!al) { if (note.textContent) note.textContent = ""; return; }
    $("sy-alok").disabled = al.h == null;
    $("sy-alok").title = al.h == null ? "Your heading comes from the game while you're on or over this planet" : "";
    if (/^Couldn't/.test(note.textContent) && al.h != null && al.h === al.failed) return;   // (until it's turned again)
    txt = al.h == null ? "· Needs your heading" : "· Faces " + String(Math.round(al.h) % 360).padStart(3, "0") + "°";
    if (note.textContent !== txt) note.textContent = txt;
  }
  function scLabel() {   // under the schematic: which way its top points (or its turn), tilt, zoom, where the heading's from, you
    var h = scHeading(), r = S.sc.align ? null : scHdgRec(), you = scYou(h), bits = [];
    if (S.sc.align) bits.push(h == null ? "Be at this settlement: your heading comes from the game" : "Turn it to match your view");
    else bits.push(h == null ? "Heading " + String(Math.round(S.sc.rot) % 360).padStart(3, "0") + "°"
                             : "Up " + String(Math.round(scNorm(h - S.sc.rot)) % 360).padStart(3, "0") + "°");
    bits.push("Tilt " + Math.round(S.sc.tilt) + "°");
    if (S.sc.zoom > 1.01) bits.push("Zoom " + S.sc.zoom.toFixed(1) + "×");
    if (r) bits.push(r.src === "dock" ? "From pad " + r.pad : "Aligned");
    if (you) bits.push("You " + (you.d < 1000 ? Math.round(you.d) + " m" : (you.d / 1000).toFixed(you.d < 1e4 ? 1 : 0) + " km"));
    return bits.join(" · ");
  }

  // the zoom between the planet and the schematic: the planet turns the settlement to the middle and
  // zooms in on it, and the schematic grows out of it; going back, the schematic shrinks into its spot
  // as the planet zooms out
  var ZOOM_IN = 1150, ZOOM_OUT = 1000, ZOOM_K = 14;
  var PAN_SWEEP = 210;   // a whole sweep of a dial pans a schematic this far (of the picture's 140 across)
  function ease(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }
  function scZoomFrame() {
    var a = S.sc.anim, e = S.syEntry, p = Math.min(1, (performance.now() - a.t0) / a.dur), html = "", plan = scPlan(), base = PX;
    function group(inner, k, alpha) {
      return '<g opacity="' + alpha.toFixed(2) + '" transform="translate(70 70) scale(' + k.toFixed(4) + ') translate(-70 -70)">' + inner + "</g>";
    }
    function globe(rot, tilt, k, alpha) { PX = base / k; var g = planetHtml(e, rot, tilt, null); PX = base; return group(g, k, alpha); }
    function schem(s, alpha) {
      var k = 0.06 + 0.94 * s;
      return group(ED.schem.draw(plan, scOpts({ px: base / k, max: S.sc.max, icons: S.sc.icons })), k, alpha);
    }
    if (a.dir === "in") {
      var turn = ease(p / 0.4), dRot = ((a.lon - a.rot0 + 540) % 360) - 180;
      var zoom = Math.pow(ZOOM_K, ease((p - 0.38) / 0.45)), fade = 1 - ease((p - 0.6) / 0.25), grow = ease((p - 0.62) / 0.38);
      if (fade > 0) html += globe(a.rot0 + dRot * turn, a.tilt0 + (a.lat - a.tilt0) * turn, zoom, fade);
      if (grow > 0) html += schem(grow, grow);
    } else {
      var shrink = 1 - ease(p / 0.35), back = Math.pow(ZOOM_K, 1 - ease((p - 0.15) / 0.65)), show = ease((p - 0.15) / 0.25);
      if (show > 0) html += globe(a.lon, a.lat, back, show);
      if (shrink > 0) html += schem(shrink, shrink);
    }
    return html;
  }
  function scZoomDone() {   // the zoom has finished
    S.sc.anim = null;
    scButtons();
    syPicture();
  }
  function scGo(view) {   // to the schematic or back to the planet
    var e = S.syEntry, pic = (e && e.pic) || {}, spot = pic.lat != null && pic.lon != null && syIsGlobe();
    S.sc.view = view;
    S.sc.align = null;
    if (view === "planet") { S.sc.picking = false; syUnlock(); }
    S.syGrab = false;
    S.sc.zoom = 1; S.sc.pan = [0, 0]; S.syZoom = 1;
    if (reduce.matches || !spot) {   // no zoom (or nowhere on the planet to zoom to): straight there
      if (view === "planet" && spot) { S.syRot = pic.lon; S.syTilt = Math.max(-90, Math.min(90, pic.lat)); }
      S.sc.anim = null;
    } else {
      S.sc.anim = { dir: view === "schematic" ? "in" : "out", t0: performance.now(), dur: view === "schematic" ? ZOOM_IN : ZOOM_OUT,
                    rot0: S.syRot, tilt0: S.syTilt, lat: Math.max(-90, Math.min(90, pic.lat)), lon: pic.lon };
      if (view === "planet") { S.syRot = pic.lon; S.syTilt = S.sc.anim.lat; }   // it comes back centred on the settlement
    }
    scButtons();
    syPicture();
    syAnimate();
  }
  function scToggleView() {
    if (S.sc.anim || S.sc.align) return;
    if (S.sc.view === "schematic") { scGo("planet"); return; }
    var st = scSettlement(), n = scCount(st), key = S.syKey;
    if (!st || !n) return;
    $("sy-snote").textContent = "";
    ED.schem.get(scCategory(st), n).then(function (plans) {
      if (S.syKey !== key || !plans.length) return;   // the selection moved on meanwhile
      var saved = scSaved(st), i = plans.findIndex(function (p) { return p.id === saved; });
      S.sc.plans = plans;
      S.sc.idx = i >= 0 ? i : 0;
      S.sc.picking = i < 0;   // not confirmed yet: choose one
      S.sc.rot = scStartRot();   // (its heading known: the way you face up, or north up; else its layout's up)
      S.sc.tilt = 0;
      var pic = (S.syEntry || {}).pic || {};
      S.desc.lock = { key: S.syEntry.key, name: S.syEntry.name, lat: pic.lat, lon: pic.lon, plans: plans, idx: S.sc.idx,
                      picking: S.sc.picking, plan: plans[S.sc.idx] };   // (zooming out past it goes back to the planet)
      scGo("schematic");
    }, function () { $("sy-snote").textContent = "Couldn't load the schematics"; });
  }
  function scStep(d) {   // the previous / next layout
    if (!S.sc.plans || S.sc.anim || S.sc.align) return;
    S.sc.idx = (S.sc.idx + d + S.sc.plans.length) % S.sc.plans.length;
    S.sc.zoom = 1; S.sc.pan = [0, 0];   // a different layout: the whole of it
    scButtons();
    syPicture();
  }
  function scConfirm() {   // Confirm layout, or Set layout (to pick again)
    var st = scSettlement(), plan = scPlan(), y = (S.data || {}).syst || {};
    if (!st || !plan || S.sc.anim || S.sc.align) return;
    if (!S.sc.picking) { S.sc.picking = true; scButtons(); return; }
    fetch("/api/settlement-layout", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: st.key, layout: plan.id, system: y.system || "", name: S.syEntry.name, economy: st.economy }) })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { $("sy-snote").textContent = "Couldn't save that"; return; }
        if (S.data && S.data.syst) (S.data.syst.layouts = S.data.syst.layouts || {})[st.key] = plan.id;
        S.sc.picking = false;
        ED.replay($("sy-pick"), "flk");
        scButtons();
        ED.refresh();
      }, function () { $("sy-snote").textContent = "Couldn't reach the FT3000"; });
  }
  function scType() {   // the Type toggle: the next type's layouts (remembered for this settlement)
    var st = scSettlement(), types = scTypes(), key = S.syKey, y = (S.data || {}).syst || {};
    if (!st || !types.length || S.sc.anim || S.sc.align) return;
    var next = types[(types.indexOf(scCategory(st)) + 1) % types.length], own = next !== scDefault(st);
    y.types = y.types || {};
    if (own) y.types[st.key] = next; else delete y.types[st.key];
    fetch("/api/settlement-type", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: st.key, category: own ? next : "", system: y.system || "", name: S.syEntry.name }) })
      .catch(function () { $("sy-snote").textContent = "Couldn't reach the FT3000"; });
    scButtons();
    if (S.sc.view !== "schematic") return;
    ED.schem.get(next, scCount(st)).then(function (plans) {
      if (S.syKey !== key || !plans.length || scCategory(st) !== next) return;   // moved on meanwhile
      var saved = scSaved(st), i = plans.findIndex(function (p) { return p.id === saved; });
      S.sc.plans = plans;
      S.sc.idx = i >= 0 ? i : 0;
      S.sc.picking = i < 0;
      S.sc.zoom = 1; S.sc.pan = [0, 0];
      scButtons();
      syPicture();
    }, function () { $("sy-snote").textContent = "Couldn't load the schematics"; });
  }
  // zooming: a schematic (about the middle), or a planet or star; orbital stations don't zoom (or maximise)
  function syZoomable() {
    var k = ((S.syEntry || {}).pic || {}).kind;
    return (S.sc.view === "schematic" && !S.sc.anim && !!scPlan()) || k === "globe" || k === "star" || k === "surface";
  }
  // ---- the true-scale descent (a planet or moon, small or maximised): zooming carries on past the planet's size, centred
  // on a settlement, until its marker is the settlement's real size (1 km across, or its plan's own scale);
  // there its schematic takes over at the same scale, and zooms on to 8 times. The settlement is the one
  // selected, or (the planet selected) the one nearest the middle when you're a fifth of the way down, where
  // the planet stops spinning and turns it to the middle. The grid gets finer on the way down. ----
  var DESC_KM = 1, DESC_LOCK = 0.2;
  var GRID = [30, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001];
  S.desc = { lock: null };   // lock: the settlement going down to {key, name, lat, lon, plans, idx, picking, plan}
  function syPlanetKm() {   // the radius of the planet the picture shows (km)
    var e = S.syEntry || {}, pic = e.pic || {};
    var host = pic.kind === "surface" ? (S.syByName || {})[(pic.body || "").toLowerCase()] : e;
    return (host && host.radius) || 0;
  }
  function syDescOn() {
    var k = ((S.syEntry || {}).pic || {}).kind;
    return k !== "star" && syIsGlobe() && syPlanetKm() > 0;   // (small or maximised)
  }
  function sySitesAll() {   // the settlements on the planet showing
    var e = S.syEntry || {}, pic = e.pic || {};
    if (pic.kind === "globe") return pic.sites || [];
    var host = pic.kind === "surface" ? (S.syByName || {})[(pic.body || "").toLowerCase()] : null;
    return host ? host.pic.sites || [] : [];
  }
  function syDescRot(t) {   // the descent's schematic: north up where its heading's known (as the planet is), else its layout's up
    var se = t && (S.syByKey || {})[t.key], r = se && se.settlement && t.plan && !t.picking ? scHdgRec(se.settlement, t.plan) : null;
    return r ? scNorm(r.h) : 0;
  }
  function sySitePlan(s) {   // a settlement's confirmed layout, to draw on the planet (its type's layouts fetched the first time)
    var se = (S.syByKey || {})[s.key], st = se && se.settlement, id = scSaved(st);
    if (!id) return null;
    var plan = ED.schem.byId(id), cat = scCategory(st);
    if (!plan && scCount(st) && !SY_FETCHING[cat]) {
      SY_FETCHING[cat] = true;
      ED.schem.get(cat, scCount(st)).then(function () { syPicture(); }, function () { delete SY_FETCHING[cat]; });
    }
    return plan;
  }
  function sySiteRot(s, plan) {   // a settlement drawn on the planet: north up where its heading's known, else its layout's up
    var se = (S.syByKey || {})[s.key], r = se && se.settlement ? scHdgRec(se.settlement, plan) : null;
    return r ? scNorm(r.h) : 0;
  }
  function syHandover(t) {   // the zoom at which the settlement's marker is as big as its schematic drawn whole
    var sch = S.sc.view === "schematic" && scPlan(), plan = sch || (t && t.plan);   // (at the turn it's drawn with)
    var ws = plan ? ED.schem.width(plan, VB.w / 2, VB.h / 2, sch ? S.sc.rot : syDescRot(t)) : 0.9 * Math.min(VB.w, VB.h);
    return ws * syPlanetKm() / ((plan ? ED.schem.widthKm(plan) : DESC_KM) * SYW.r);
  }
  function syLockAt() { return Math.max(2, Math.exp(DESC_LOCK * Math.log(syHandover(null) * 8))); }
  function syLock() {   // choose the settlement to go down to, and fetch its layouts
    var e = S.syEntry, pic = e.pic || {}, t = null;
    if (pic.kind === "surface" && pic.lat != null) t = { key: e.key, name: e.name, lat: pic.lat, lon: pic.lon };
    else {
      var best = 1e9, la0 = S.syTilt * SYW.R2D, lo0 = S.syRot * SYW.R2D;
      sySitesAll().forEach(function (s) {   // the nearest to the middle of the picture (by the angle between them)
        if (s.lat == null || !s.key) return;
        var la = s.lat * SYW.R2D, lo = s.lon * SYW.R2D;
        var d = Math.acos(Math.max(-1, Math.min(1, Math.sin(la0) * Math.sin(la) + Math.cos(la0) * Math.cos(la) * Math.cos(lo - lo0))));
        if (d < best) { best = d; t = { key: s.key, name: s.name, lat: s.lat, lon: s.lon }; }
      });
    }
    if (!t) return false;
    S.desc.lock = t;
    var se = (S.syByKey || {})[t.key], st = se && se.settlement, n = scCount(st);
    if (st && n) ED.schem.get(scCategory(st), n).then(function (plans) {
      if (S.desc.lock !== t || !plans.length) return;
      var saved = scSaved(st), i = plans.findIndex(function (p) { return p.id === saved; });
      t.plans = plans; t.idx = i >= 0 ? i : 0; t.picking = i < 0; t.plan = plans[t.idx];
    }, function () { /* the footprint only, then */ });
    syAnimate();   // (it turns to the middle)
    return true;
  }
  function syUnlock() { S.desc.lock = null; }
  function syToSchematic(t, m) {   // the marker's as big as the schematic: the schematic takes over
    if (S.syEntry.key !== t.key) {   // the planet was selected: now the settlement, keeping the view as it is
      S.syKeep = true;
      S.sySel = t.key;
      S.syMode = "manual";
      if (S.data) ED.render(S.data);
    }
    S.sc.plans = t.plans; S.sc.idx = t.idx; S.sc.picking = t.picking;
    S.sc.view = "schematic"; S.sc.rot = syDescRot(t); S.sc.tilt = 0;   // (north up, as the planet was, its heading known)
    S.sc.pan = ED.schem.originPan(scPlan());   // its position in the middle, where the planet had it
    S.syGrab = false;
    scButtons();
    syMeasure();   // (the buttons under it change the picture's shape: the scale's worked out for the new one)
    S.sc.zoom = Math.max(1, m / syHandover(t));
    syPicture();
  }
  function syFromSchematic(z) {   // zoomed out past the whole settlement: back to the planet, at the same scale
    var e = S.syEntry, pic = e.pic || {}, t = S.desc.lock;
    if (!t || t.key !== e.key) t = S.desc.lock = { key: e.key, name: e.name, lat: pic.lat, lon: pic.lon };
    t.plans = S.sc.plans; t.idx = S.sc.idx; t.picking = S.sc.picking; t.plan = scPlan();
    S.sc.view = "planet";
    S.syRot = t.lon; S.syTilt = Math.max(-90, Math.min(90, t.lat));
    scButtons();
    syMeasure();   // (as above: the scale for the picture's new shape, and just short of the schematic again)
    var mh = syHandover(t);
    S.syZoom = Math.max(1, Math.min(mh * z, mh * 0.98));
    syPicture();
  }
  // zoom by f: a schematic (about the middle, or the point given), a planet or star; orbital stations don't zoom
  function syZoomable() {
    var k = ((S.syEntry || {}).pic || {}).kind;
    return (S.sc.view === "schematic" && !S.sc.anim && !!scPlan()) || k === "globe" || k === "star" || k === "surface";
  }
  function syZoomBy(f, sx, sy) {
    if (S.sc.anim) return false;
    if (S.sc.view === "schematic") {
      if (!scPlan()) return false;
      if (!S.sc.align && pic0().lat != null && S.sc.zoom * f < 0.999) { syFromSchematic(S.sc.zoom * f); return true; }
      scZoom(f, sx == null ? 70 : sx, sy == null ? 70 : sy);
      return true;
    }
    if (!syIsGlobe()) return false;
    if (!syDescOn()) {   // a star: up to 8 times
      S.syZoom = Math.max(1, Math.min(8, (S.syZoom || 1) * f));
      if (S.desc.lock) syUnlock();
      syPicture();
      return true;
    }
    var m = Math.max(1, (S.syZoom || 1) * f), lockAt = syLockAt();
    if (m >= lockAt && !S.desc.lock && !syLock()) m = Math.min(m, lockAt);   // no settlement to go down to: stop here
    if (m < lockAt && S.desc.lock) syUnlock();
    var t = S.desc.lock;
    if (t) {
      var mh = syHandover(t);
      if (t.plan && m >= mh) { syToSchematic(t, m); return true; }
      m = Math.min(m, mh * (t.plan ? 1 : 1.5));   // (no layouts: as far as the footprint filling the picture)
    }
    S.syZoom = m;
    syPicture();
    return true;
  }
  function pic0() { return (S.syEntry || {}).pic || {}; }
  function scMax() {   // Maximise / Minimise
    if (S.sc.align) return;
    S.sc.max = !S.sc.max;
    scButtons();
    syPicture();
  }
  function scIcon(g) {
    S.sc.icons[g] = !S.sc.icons[g];
    scButtons();
    syPicture();
  }
  function scReset() {   // a different body or station: small, and the planet
    S.sc.max = false;
    S.sc.view = "planet";
    S.sc.anim = null;
    S.sc.plans = null;
    S.sc.picking = false;
    S.sc.align = null;
    $("sy-snote").textContent = "";
  }
  // the buttons under the picture, as things stand
  function scButtons() {
    var st = scSettlement(), n = scCount(st), sch = S.sc.view === "schematic", plan = scPlan(), anim = !!S.sc.anim;
    var saved = sch && scSavedHere(), picking = sch && (S.sc.picking || !saved);
    $("sy-pc").classList.toggle("max", S.sc.max);
    $("sy-pic").classList.toggle("max", S.sc.max);
    $("sy-pic").classList.toggle("sch", sch && !anim);
    $("sy-max").textContent = S.sc.max ? "Minimise" : "Maximise";
    $("sy-max").hidden = !S.sc.max && !syZoomable();   // only bodies and things on the ground (and their schematics)
    // a surface site with a position: DESIGNATE it (the target: Atk attacks it), or STORE it as one of your waypoints
    var se = S.syEntry, sp = (se || {}).pic || {}, surf = !!se && sp.kind === "surface" && sp.lat != null && sp.lon != null;
    var tk = (((((S.data || {}).syst || {}).nav || {}).tgt) || {}).key;
    var plain = surf && !S.sc.max && !sch;   // (not over a maximised picture or a schematic)
    $("sy-dsg").hidden = !plain;
    $("sy-dsg").textContent = surf && (tk === se.key || tk === se.key + "o") ? "Undesignate" : "Designate";
    $("sy-stor").hidden = !plain || se.kind === "tgt";
    $("sy-type").textContent = "Type: " + scTypeName(scCategory(st));
    // a surface station only your journal knows, of no known type (it may be an Odyssey settlement): Schematic view
    // looks as it does where there's none - greyed, no note, no UFC highlight - but still opens its schematics,
    // until you confirm a layout for it (or its type turns up)
    var quiet = !sch && !!n && scUnsure(st);
    $("sy-sch").textContent = sch ? "Planetary view" : "Schematic view";
    $("sy-sch").disabled = !sch && (!st || !n);
    $("sy-sch").classList.toggle("off", quiet);
    $("sy-sch").title = st && !quiet ? "" : "Odyssey settlements only";
    var problem = /^Couldn't/.test($("sy-snote").textContent);   // a load or save problem stays until the next try
    if (quiet && !problem) $("sy-snote").textContent = "";
    else if (!sch && !problem) {
      var cat = scCategory(st), own = st && (((S.data || {}).syst || {}).types || {})[st.key] === cat;
      $("sy-snote").textContent = !st ? "" : !n ? (st.economy ? "No " + st.economy + " schematics yet" : "Economy not known") :
        own ? "Type: " + scTypeName(cat) + " (your choice)" :
        cat !== st.category ? "Type: " + scTypeName(cat) + " (no " + (st.economy || "known") + " layouts yet)" : "";
    }
    var al = S.sc.align && sch && !anim ? S.sc.align : null;   // Align layout: only its own two buttons
    if (S.sc.align && !al) S.sc.align = null;
    $("sy-pick").hidden = !sch || anim || !plan || !!al;
    if (plan) {
      $("sy-pname").textContent = plan.name;
      $("sy-pnum").textContent = picking ? (S.sc.idx + 1) + " of " + S.sc.plans.length : "Set";
      $("sy-prev").hidden = $("sy-next").hidden = !picking;
      $("sy-ok").textContent = picking ? "Confirm layout" : "Set layout";
      $("sy-align").hidden = picking;   // a confirmed layout: which way does it face?
    }
    $("sy-icons").hidden = !sch || anim || !S.sc.max || !!al;
    $("sy-max").hidden = $("sy-max").hidden || !!al;
    $("sy-sch").hidden = !!al;
    if (al) $("sy-dsg").hidden = $("sy-stor").hidden = true;
    $("sy-win").classList.toggle("align", !!al);
    $("sy-alignbar").hidden = !al;
    scAlignNote();
    Array.prototype.forEach.call($("sy-icons").querySelectorAll("button[data-ic]"), function (b) {
      var on = !!S.sc.icons[b.dataset.ic];
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (syStops().indexOf(S.syFocus) < 0) S.syFocus = "picture";   // what the UFC had highlighted has gone
    syFocusClasses();
  }

  function syLoop(t) {
    S.syRaf = null;
    if (!ED.showing("nav", 1) || S.halted || ED.hyper.on()) return;   // the picture rests while the map (or a jump) shows
    var dt = S.syT ? Math.min(100, t - S.syT) : 0;
    S.syT = t;
    if (S.sc.anim) {
      if (performance.now() - S.sc.anim.t0 >= S.sc.anim.dur) scZoomDone(); else syPicture();
    } else if (S.sc.view === "schematic") {
      // the schematic only moves when you turn it
    } else if (S.desc.lock && S.syEntry) {   // going down: the settlement turns to the middle, and stays there
      var lk = S.desc.lock, k = 1 - Math.exp(-dt / 250), dl = ((lk.lon - S.syRot + 540) % 360) - 180, dp = lk.lat - S.syTilt;
      if (Math.abs(dl) > 1e-7 || Math.abs(dp) > 1e-7) {
        S.syRot = Math.abs(dl) < 1e-6 ? lk.lon : S.syRot + dl * k;
        S.syTilt = Math.abs(dp) < 1e-6 ? lk.lat : S.syTilt + dp * k;
        syPicture();
      }
    } else if (!S.syGrab && !S.syHeld && !reduce.matches && S.syEntry) {
      var still = S.syEntry.pic && /globe|star|surface/.test(S.syEntry.pic.kind);
      S.syRot = (S.syRot + dt * (still ? 0.008 : 0.014)) % 360;   // planets turn slowly, stations a bit quicker
      syPicture();
    }
    S.syRaf = requestAnimationFrame(syLoop);
  }
  function syAnimate() {
    if (ED.showing("nav", 1) && !S.syRaf && !S.halted) { S.syT = 0; S.syRaf = requestAnimationFrame(syLoop); }
  }

  function syFocusClasses() {
    var ufc = (S.ufc || {}).menu === "PAGE";
    $("sy-sw").classList.toggle("focus", ufc && S.syFocus === "switch");
    $("sy-pic").classList.toggle("focus", ufc && S.syFocus === "picture");
    $("sy-pic").classList.toggle("grab", S.syGrab);
    $("sy-scroll").classList.toggle("focus", ufc && S.syFocus === "data");
    Array.prototype.forEach.call($("sy-pic").querySelectorAll("[data-f]"), function (b) {
      b.classList.toggle("focus", ufc && S.syFocus === b.dataset.f);
    });
  }

  function renderSyst(s) {
    var y = s.syst || {}, entries = y.entries || [];
    if (ED.showing("nav", 1)) ED.remote.sync();   // (a keypad claim left over - a reload, another page's - let go; told once)
    var ok = entries.length > 0 && (y.status === "ok" || y.status === "stale");
    $("pg-syst-list").classList.toggle("synone", !ok);
    var rm = y.remote || {};   // (REMOTE: the system's name in amber)
    S.syLab = (rm.on ? '<span class="rmt">Remote · ' + ED.esc(y.system || rm.system || "System") + "</span>" : ED.esc(y.system || "System")) +
      (ok ? " · " + y.bodies + " bodies" : "");
    Array.prototype.forEach.call($("sy-rem").querySelectorAll("button"), function (b) {
      var o = (b.dataset.v === "rem") === !!rm.on;
      b.classList.toggle("on", o); b.setAttribute("aria-pressed", String(o));
    });
    $("sy-rly").textContent = rm.on && rm.ly != null ? rm.ly + " ly away" : "";
    $("sy-rly").title = rm.on ? "From " + (rm.here || "where you are") : "";
    if (!ok) {
      $("sy-railmsg").textContent = (SYMSG[y.status] || "No system data").replace("{src}", y.status === "error" && /^EDSM:/.test(y.error || "") ? "EDSM" : y.from || "Spansh");
      S.syEntry = null;
      ED.applyCursor(false);
      return;
    }
    var byKey = {};
    S.syByName = {};
    S.syByKey = byKey;
    entries.forEach(function (e) { byKey[e.key] = e; S.syByName[e.name.toLowerCase()] = e; });
    if (S.sySystem !== y.system) { S.sySystem = y.system; S.sySel = null; S.sySig = ""; S.syKey = null; }
    var auto = y.auto || {}, near = y.near || {}, me = y.me;
    S.syAutoSite = auto.why === "nearest" && byKey[auto.key] ? byKey[auto.key].name : null;
    if (S.syMode === "auto" && auto.key && byKey[auto.key]) S.sySel = auto.key;
    if (!byKey[S.sySel]) S.sySel = auto.key && byKey[auto.key] ? auto.key : entries[0].key;
    if (S.sySel !== S.sySent) { S.sySent = S.sySel; ED.reportView({ pick: { syst: S.sySel } }); }

    // left: bodies with their stations
    var rows = entries.map(function (e) { return e.key + ":" + e.label + ":" + (e.right || "") + (e.mine ? "*" : ""); }).join(",");
    var sig = [y.system, rows, S.sySel, JSON.stringify(near), y.docked, me && me.key].join("|");
    if (sig !== S.sySig) {
      var moved = S.sySig && S.syListSel !== S.sySel;
      S.sySig = sig;
      S.syListSel = S.sySel;
      $("sy-list").innerHTML = entries.map(function (e) {
        var st = e.kind === "station", right = e.right, here = false;
        if (st && near[e.key]) { right = syKm(near[e.key][0]); here = auto.key === e.key; }
        if (st && y.docked === e.key) { right = "Docked"; here = true; }
        if (!st && me && me.key === e.key) here = true;
        return '<button type="button" class="srow' + (st ? " st" : "") + (e.key === S.sySel ? " sel" : "") + '" data-key="' + ED.esc(e.key) +
          '" style="padding-left: ' + (8 + e.depth * 22) + 'px"><span class="nm">' + ED.icon(e.icon) + ED.esc(e.label) +
          (e.mine ? ' <span class="mine" title="Scanned by you">\u221a</span>' : "") +   // a tick: you've scanned it yourself
          '</span><span class="rt' + (here ? " here" : "") + '">' + ED.esc(right) + "</span></button>";
      }).join("");
      ED.applyCursor(false);
      if (moved) {
        var row = $("sy-list").querySelector(".srow.sel");
        if (row) row.scrollIntoView({ block: "nearest" });
      }
    }

    // commanders here: EDSM's counts, then yours from your journals
    var t = y.traffic || {}, you = y.you || {};
    var seen = (t.seen || []).map(function (p) { return p[0] + (p[1] > 1 ? " ×" + p[1] : ""); }).join(", ");
    if ((y.uplinking || {}).edsm === false) {   // EDSM Uplink off: nothing to count
      $("sy-edsm1").innerHTML = 'EDSM <span class="v">Uplink off</span>';
      $("sy-edsm2").innerHTML = "";
    } else {
      $("sy-edsm1").innerHTML = 'EDSM <span class="v">' + ED.num(t.day || 0) + '</span> day · <span class="v">' + ED.num(t.week || 0) +
        '</span> wk · <span class="v">' + ED.num(t.total || 0) + "</span>";
      $("sy-edsm2").innerHTML = 'EDSM seen <span class="v">' + ED.esc(seen || "none today") + "</span>";
    }
    $("sy-you").innerHTML = '<span class="you">You</span> ' + (you.visits
      ? '<span class="v">' + you.visits + "</span> visit" + (you.visits === 1 ? "" : "s") + ' · last <span class="v">' + ED.esc(syDay(you.last)) + "</span>"
      : '<span class="v">first visit</span>');
    $("sy-you").title = you.first ? "First visit " + new Date(you.first).toLocaleDateString("en-GB") : "";
    syUplink(y);

    // right: the selected body or station
    var e = byKey[S.sySel], key = y.system + ":" + e.key, switched = S.syKey !== key;
    S.syEntry = e;
    if (switched) {
      if (S.syKey) ED.replay($("sy-scroll"), "pull");
      S.syKey = key;
      $("sy-scroll").scrollTop = 0;
      if (S.syKeep) {   // the descent went down into this settlement: the view carries on as it is
        S.syKeep = false;
      } else {
        S.syGrab = false;
        S.syHeld = false;   // spinning on its own again
        S.syZoom = 1;
        syUnlock();
        scReset();
        if (ED.dialsDisarm) ED.dialsDisarm();
        var pic = e.pic || {}, focusLon = null, focusLat = -12;
        if (pic.kind === "surface" && pic.lon != null) { focusLon = pic.lon; focusLat = Math.max(-60, Math.min(60, pic.lat)); }
        else if (me && me.key === e.key) { focusLon = me.lon; focusLat = Math.max(-60, Math.min(60, me.lat)); }
        S.syRot = focusLon != null ? focusLon : (S.syRot || 0);
        S.syTilt = focusLat;
      }
      ED.setText($("sy-case"), e.lab, false);
      $("sy-name").textContent = e.name;
      $("sy-grid").innerHTML = e.rows.map(function (r) {
        return '<div class="cell' + (r[2] ? " wide" : "") + '"><span class="lab">' + ED.esc(r[0]) + '</span><span class="v">' + ED.esc(r[1]) + "</span></div>";
      }).join("");
    }
    var chips = [];
    if (y.docked === e.key) chips.push(["Docked", true]);
    if (near[e.key]) {
      chips.push(S.syMode === "auto" && auto.why === "nearest" && auto.key === e.key
        ? ["Nearest · " + ED.num(near[e.key][0]) + " km · " + String(near[e.key][1]).padStart(3, "0") + "°", true]
        : [ED.num(near[e.key][0]) + " km from you", false]);
    }
    if (me && me.key === e.key) chips.push(["You are here", true]);
    (e.chips || []).forEach(function (c) { chips.push([c.t, false]); });
    var chipSig = key + JSON.stringify(chips);
    if (chipSig !== S.syChips) {
      S.syChips = chipSig;
      $("sy-chips").innerHTML = chips.map(function (c) { return '<span class="chip' + (c[1] ? "" : " dim") + '">' + ED.esc(c[0]) + "</span>"; }).join("");
    }
    $("sy-auto").classList.toggle("on", S.syMode === "auto");
    $("sy-man").classList.toggle("on", S.syMode !== "auto");
    var src = e.src || y.source || "journal";   // where the selected item comes from
    $("sy-age").textContent = sySrcText(src);
    // a schematic shows you and which way it faces: redrawn when you move or turn, or its heading changes (a docking)
    var schem = S.sc.view === "schematic" && !S.sc.anim, turned = schem && scAlignTrack();
    var youSig = schem ? JSON.stringify([me && [me.lat, me.lon, me.hdg, me.alt], scHdgRec()]) : "";
    scButtons();
    if (switched || reduce.matches || S.syGrab || turned || youSig !== S.sc.youSig) syPicture();
    S.sc.youSig = youSig;
    syAnimate();
  }

  // ---- System Data Uplink Synchronise (under Commanders here): fetches this system's EDSM data now ----
  // The board says how it stands (in progress, how it went and how long ago, how long until it can be
  // pressed again); the page counts on from when it heard, so the button changes on time between updates.
  function syUpDate(iso) {   // "29 Oct 2026 10:21", in this device's time
    var d = new Date(iso);
    if (isNaN(d)) return "-";
    return d.getDate() + " " + d.toLocaleString("en-GB", { month: "short" }) + " " + d.getFullYear() + " " +
      String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  function syUplink(y) {
    S.syUp = { at: Date.now(), u: y.uplinking || {}, last: y.uplink || null, status: y.status, error: y.error || "", from: y.from };
    syUpShow();
  }
  function syUpShow() {
    var b = $("sy-up"), up = S.syUp;
    if (!b || !up) return;
    var u = up.u, el = (Date.now() - up.at) / 1000, since = u.since == null ? null : u.since + el, wait = Math.max(0, (u.wait || 0) - el);
    var st = u.off ? "off" : u.busy ? "busy" : since != null && since < 4 && u.result === "ok" ? "ok" :
      since != null && since < 6 && u.result === "error" ? "fail" : wait > 0 ? "wait" : "";
    var txt = { off: ["Uplink", "Offline"], busy: ["Uplink", "In progress\u2026"], ok: ["System data", "Synchronised"],
                fail: ["Uplink", "Failed"] }[st] || ["System data", "Uplink synchronise"];
    if (b.dataset.st !== st) {
      b.dataset.st = st;
      b.className = "syup" + (st ? " " + st : "") + (b.classList.contains("cur") ? " cur" : "");
      b.querySelector(".l1").textContent = txt[0];
      b.querySelector(".l2").textContent = txt[1];
      b.disabled = st !== "";
    }
    b.title = st === "wait" ? "Ready again in " + Math.ceil(wait) + " s" : st === "fail" && u.error ? u.error : "";
    ["spansh", "edsm"].forEach(function (k) {   // the two toggles
      var t = $("sy-src-" + k), on = u[k] !== false;
      if (t && t.classList.contains("on") !== on) { t.classList.toggle("on", on); t.setAttribute("aria-pressed", on ? "true" : "false"); }
    });
    var line = u.off ? "Uplinks off: your journal only" : "Last uplink " + (up.last ? syUpDate(up.last) : "-");
    if (!u.off && (up.status === "stale" || up.status === "error")) line += ' <span class="am">\u00b7 ' + (/^EDSM:/.test(up.error || "") ? "EDSM" : up.from || "Spansh") + " unreachable</span>";
    if ($("sy-upt").innerHTML !== line) $("sy-upt").innerHTML = line;
    clearTimeout(S.syUpT);
    if (st && st !== "off") S.syUpT = setTimeout(syUpShow, 500);   // until it's ready again
  }
  Array.prototype.forEach.call(document.querySelectorAll("#sy-hum .sysrcb"), function (t) {   // Spansh Uplink / EDSM Uplink
    t.addEventListener("click", function () {
      var k = t.dataset.src, on = !t.classList.contains("on");
      t.classList.toggle("on", on);   // at once; the board confirms
      t.setAttribute("aria-pressed", on ? "true" : "false");
      if (S.syUp) S.syUp.u[k] = on;
      fetch("/api/uplink-source", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: k, on: on }) })
        .then(function () { ED.refresh(); }, function () {});
    });
  });
  $("sy-up").addEventListener("click", function () {
    var b = $("sy-up");
    if (b.disabled) return;
    if (S.syUp) { S.syUp.u = Object.assign({}, S.syUp.u, { busy: true }); S.syUp.at = Date.now(); syUpShow(); }   // at once; the board confirms
    try { fetch("/api/uplink", { method: "POST" }).catch(function () {}); } catch (err) { /* nothing to tell */ }
  });

  // picking yourself switches to Manual; AUTO goes back to following where you are
  function syPick(key) {
    S.syMode = "manual";
    S.sySel = key;
    S.syFocus = "switch";
    if (ED.showing("nav", 2)) ED.setView("nav", 1);   // picked on the map: show its details
    if (S.data) ED.render(S.data);
  }
  function sySetMode(mode) {
    S.syMode = mode;
    if (S.data) ED.render(S.data);
  }
  function syGrab(on) {   // grabbed: the spin stops and the picture turns only when you turn it
    S.syGrab = on;
    syFocusClasses();
    syPicture();
  }
  // the UFC's dials, as speeds (-1..1) for dt seconds (see main.js): COMM1 VOLUME zooms (4 times a second at
  // full turn), COMM2 VOLUME spins a planet (90° a second) or turns a schematic, BRT tilts (60° a second) - or,
  // a schematic grabbed, they pan it (half the picture a second). Centred, a planet spins on its own again.
  function syDial(r, dt) {
    var cue = { z: "", t: "" };
    if (!S.syEntry || S.sc.anim) return cue;
    if (r.zoom && syZoomBy(Math.exp(Math.log(4) * r.zoom * dt))) cue.z = r.zoom > 0 ? "Z+" : "Z-";
    if (!r.yaw && !r.pitch) return cue;
    if (S.sc.view === "schematic") {
      if (S.syGrab) scPan(r.yaw * 70 * dt, r.pitch * 70 * dt);   // grabbed: pans it (clockwise: right / down, as on the map)
      else {
        S.sc.rot = ((S.sc.rot + r.yaw * 90 * dt) % 360 + 360) % 360;
        S.sc.tilt = Math.max(0, Math.min(80, S.sc.tilt + r.pitch * 60 * dt));
        if (r.yaw) scTurned();
        if (r.pitch && S.sc.align) S.sc.align.auto = false;   // tilted yourself: it stays where you put it
        syPicture();
      }
    } else if (S.desc.lock) {
      return cue;   // going down to a settlement: it stays in the middle
    } else {
      if (r.yaw || r.pitch) S.syHeld = true;   // turned or tilted yourself: it stays where you leave it (no spin of its own)
      if (r.yaw) S.syRot = ((S.syRot - r.yaw * 90 * dt) % 360 + 360) % 360;
      S.syTilt = Math.max(-90, Math.min(90, S.syTilt + r.pitch * 60 * dt));
      syPicture();
    }
    cue.t = r.yaw ? (r.yaw > 0 ? ">>" : "<<") : (r.pitch > 0 ? "UP" : "DN");
    return cue;
  }
  // a 2-second COMM2 pull selects the site under the cursor
  function syLongPull() {
    if (S.sc.anim) return;
    if (S.sc.view === "schematic") { scWhole(); return; }   // back to the whole settlement
    if (S.syAim) { ED.replay($("sy-pic"), "flk"); syPick(S.syAim.key); }
    else syReset();   // nothing under the cursor: as a double-click
  }
  // the whole planet again (out of the descent), spinning on its own; a station spins on its own again
  function syReset() {
    if (syIsGlobe()) { S.syZoom = 1; syUnlock(); }
    S.syHeld = false;
    if (S.syGrab) syGrab(false); else syPicture();
  }
  // COMM2 channel knob on the System tab: switch -> picture -> its buttons -> details, then scrolls them
  function syStops() {
    var stops = ["switch", "picture"], sch = S.sc.view === "schematic" && !S.sc.anim;
    if (sch && S.sc.align) return ["picture", "al-cancel", "al-ok"];   // Align layout: the picture and its two buttons
    if (!$("sy-max").hidden) stops.push("max");
    if (!$("sy-sch").disabled) stops.push("sch");
    if (!$("sy-dsg").hidden) stops.push("dsg");
    if (!$("sy-stor").hidden) stops.push("stor");
    if (sch && !$("sy-pick").hidden) {
      if (!$("sy-prev").hidden) stops.push("prev", "next");
      stops.push("ok");
      if (!$("sy-align").hidden) stops.push("align");
    }
    if (sch && S.sc.max) stops.push("ic-term", "ic-door", "ic-power", "ic-exp", "ic-cz", "ic-type");
    if (!S.sc.max) stops.push("data");
    return stops;
  }
  function syComm2(dir) {
    if (S.syGrab && S.sc.view === "schematic" && !S.sc.anim) return;   // grabbed: the dials pan it (COMM1 VOLUME zooms)
    var order = syStops(), i = order.indexOf(S.syFocus), box = $("sy-scroll");
    var step = Math.round(parseFloat(getComputedStyle(document.body).fontSize) * 1.25 * 2);
    if (i < 0) {
      S.syFocus = order[0];
    } else if (dir > 0) {
      if (S.syFocus === "data") box.scrollTop += step;
      else if (i < order.length - 1) S.syFocus = order[i + 1];
    } else if (S.syFocus === "data" && box.scrollTop > 0) {
      box.scrollTop -= step;
    } else if (i > 0) {
      S.syFocus = order[i - 1];
      if (S.syFocus !== "data") box.scrollTop = 0;
    }
    syFocusClasses();
  }
  function syComm2Pull() {   // short pull: flip the switch, grab / let go of the picture, or press the button
    var b = document.querySelector('#sy-pic [data-f="' + S.syFocus + '"]');
    if (S.syFocus === "switch") sySetMode(S.syMode === "auto" ? "manual" : "auto");
    else if (S.syFocus === "picture") { if (!S.sc.anim) syGrab(!S.syGrab); }   // a schematic grabbed: the dials pan it
    else if (b) { if (!b.disabled && !b.hidden) b.click(); }
    else if (S.syGrab) syGrab(false);
  }
  $("sy-list").addEventListener("click", function (e) {
    var b = e.target.closest(".srow");
    if (b && S.data) syPick(b.dataset.key);
  });
  $("sy-auto").addEventListener("click", function () { sySetMode("auto"); });
  $("sy-dsg").addEventListener("click", function () { if (S.syEntry) ED.nav.dsg(S.syEntry.key); });
  $("sy-stor").addEventListener("click", function () {   // its position, kept as one of your waypoints (named after it)
    var e = S.syEntry, p = (e || {}).pic || {};
    if (!e || p.lat == null) return;
    fetch("/api/tgt", { method: "POST", headers: { "Content-Type": "application/json" },   // (COMM2 pulled: with the pull's token)
                        body: JSON.stringify({ op: "add", body: p.body || e.body, lat: p.lat, lon: p.lon, method: "manual", name: String(e.name || "").slice(0, 40), u: ED.ufcU() }) })
      .then(function () { ED.refresh(); }, function () {});
  });
  $("sy-man").addEventListener("click", function () { sySetMode("manual"); });
  // the picture: tap to grab, drag to turn it (up/down tilts), tap again to let go. A schematic: drag to turn
  // and tilt it, right-drag (or Shift and drag) to pan, the wheel to zoom where the pointer is, a double-click
  // for the whole settlement again; on a touch screen, two fingers pinch to zoom and move to pan
  var PTRS = {};   // the pointers down on the picture
  function syPt(cx, cy) {   // a point on the screen -> the picture's units
    var r = $("sy-svg").getBoundingClientRect();
    return [VB.x + (cx - r.left) * VB.w / r.width, VB.y + (cy - r.top) * VB.h / r.height];
  }
  function syPinch() {   // two fingers: their middle and how far apart
    var ids = Object.keys(PTRS);
    if (ids.length !== 2) return null;
    var a = PTRS[ids[0]], b = PTRS[ids[1]];
    return { mid: syPt((a.x + b.x) / 2, (a.y + b.y) / 2), d: Math.hypot(a.x - b.x, a.y - b.y) };
  }
  $("sy-svg").addEventListener("pointerdown", function (e) {
    PTRS[e.pointerId] = { x: e.clientX, y: e.clientY };
    var pan = e.button === 2 || e.shiftKey;
    S.syDrag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, moved: false, pan: pan };
    S.syPinch = S.sc.view === "schematic" || syIsGlobe() ? syPinch() : null;
    if (S.syPinch) S.syDrag.moved = true;   // a pinch isn't a tap
    try { $("sy-svg").setPointerCapture(e.pointerId); } catch (err) {}
  });
  $("sy-svg").addEventListener("contextmenu", function (e) { if (S.sc.view === "schematic") e.preventDefault(); });
  $("sy-svg").addEventListener("dblclick", function () {
    if (S.sc.view === "schematic" && !S.sc.anim) scWhole();
    else if (!S.sc.anim) syReset();   // a planet: the whole of it again, spinning on its own
  });
  $("sy-svg").addEventListener("wheel", function (e) {
    var f = Math.pow(1.0015, -e.deltaY * (e.deltaMode === 1 ? 33 : 1));   // a notch: about 1.16 times
    if (S.sc.anim) return;
    if (S.sc.view === "schematic") {
      if (!scPlan()) return;
      e.preventDefault();
      var p = syPt(e.clientX, e.clientY);
      syZoomBy(f, p[0], p[1]);
    } else if (syIsGlobe()) {   // a planet or star: about its middle (it turns under you)
      e.preventDefault();
      syZoomBy(f);
    }
  }, { passive: false });
  $("sy-svg").addEventListener("pointermove", function (e) {
    var d = S.syDrag;
    if (PTRS[e.pointerId]) PTRS[e.pointerId] = { x: e.clientX, y: e.clientY };
    if (!d || S.sc.anim) return;
    if (S.sc.view === "schematic") {
      var was = S.syPinch, now = syPinch();
      if (was && now) {   // two fingers: zoom by how far apart they've moved, pan by where their middle went
        S.syPinch = now;
        scPan(was.mid[0] - now.mid[0], was.mid[1] - now.mid[1]);
        if (was.d > 0) scZoom(now.d / was.d, now.mid[0], now.mid[1]);
        return;
      }
      if (d.pan) {   // the settlement follows the pointer
        var a = syPt(d.x, d.y), b = syPt(e.clientX, e.clientY);
        scPan(a[0] - b[0], a[1] - b[1]);
      } else {
        S.sc.rot = ((S.sc.rot + (e.clientX - d.x) * 0.6) % 360 + 360) % 360;
        S.sc.tilt = Math.max(0, Math.min(80, S.sc.tilt + (e.clientY - d.y) * 0.4));
        if (e.clientX !== d.x) scTurned();
        if (e.clientY !== d.y && S.sc.align) S.sc.align.auto = false;
        syPicture();
      }
      d.x = e.clientX; d.y = e.clientY; d.moved = true;
      return;
    }
    var wasP = S.syPinch, nowP = syPinch();
    if (wasP && nowP && syIsGlobe()) {   // two fingers on a planet: zoom
      S.syPinch = nowP;
      if (wasP.d > 0) syZoomBy(nowP.d / wasP.d);
      d.moved = true;
      return;
    }
    if (!S.syGrab) return;
    var dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (Math.abs(dx) + Math.abs(dy) > 2) d.moved = true;
    d.x = e.clientX; d.y = e.clientY;
    S.syRot = (S.syRot - dx * 0.8 + 360) % 360;
    S.syTilt = Math.max(-90, Math.min(90, S.syTilt + dy * 0.5));
    syPicture();
  });
  function syUp(e) {
    delete PTRS[e.pointerId];
    S.syPinch = null;
    var d = S.syDrag;
    S.syDrag = Object.keys(PTRS).length ? S.syDrag : null;   // one finger still down: carry on with it
    if (S.syDrag) { var rest = PTRS[Object.keys(PTRS)[0]]; S.syDrag.x = rest.x; S.syDrag.y = rest.y; return; }
    if (!d || d.moved || S.sc.view === "schematic" || S.sc.anim) return;
    var r = $("sy-svg").getBoundingClientRect(), x = VB.x + (d.x0 - r.left) * VB.w / r.width, y = VB.y + (d.y0 - r.top) * VB.h / r.height;
    var hit = null, best = 13;
    if (syIsGlobe()) sySitesShown().forEach(function (p) {
      var dist = Math.hypot(p.x - x, p.y - y);
      if (p.vis && dist < best) { best = dist; hit = p.site; }
    });
    if (hit && hit.key) syPick(hit.key);   // tapped a settlement: select it
    else syGrab(!S.syGrab);
  }
  $("sy-svg").addEventListener("pointerup", syUp);
  $("sy-svg").addEventListener("pointercancel", function (e) { delete PTRS[e.pointerId]; S.syDrag = S.syPinch = null; });
  $("sy-max").addEventListener("click", scMax);
  $("sy-type").addEventListener("click", scType);
  $("sy-sch").addEventListener("click", scToggleView);
  $("sy-prev").addEventListener("click", function () { scStep(-1); });
  $("sy-next").addEventListener("click", function () { scStep(1); });
  $("sy-ok").addEventListener("click", scConfirm);
  $("sy-align").addEventListener("click", scAlign);
  $("sy-alcancel").addEventListener("click", function () { scAlignEnd(false); });
  $("sy-alok").addEventListener("click", scAlignOk);
  $("sy-icons").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-ic]");
    if (b) scIcon(b.dataset.ic);
  });
  window.addEventListener("resize", function () { if (S.sc.max && ED.showing("nav", 1)) syPicture(); });
  // ---- the page ----
  function cursor(u, scroll) {   // the UFC knob's highlight (PAGE menu)
    var on = u.menu === "PAGE", cur = on ? (u.cursors || {}).syst : null;
    $("sy-lab").innerHTML = (S.syLab || "System") + (on ? ' <span class="ufc">· UFC</span>' : "");
    Array.prototype.forEach.call($("sy-list").querySelectorAll(".srow"), function (b) {
      var is = on && b.dataset.key === cur;
      b.classList.toggle("cur", is);
      if (is && scroll) b.scrollIntoView({ block: "nearest" });
    });
    $("sy-rem").classList.toggle("cur", on && cur === "remote");   // CURRENT SYSTEM / REMOTE: the stop before the list's first row
    if (on && cur === "remote" && scroll) $("sy-rem").scrollIntoView({ block: "nearest" });
    $("sy-up").classList.toggle("cur", on && cur === "uplink");   // the uplink button: the stop after the list's last row
    $("sy-src-spansh").classList.toggle("cur", on && cur === "src:spansh");   // then the two toggles
    $("sy-src-edsm").classList.toggle("cur", on && cur === "src:edsm");
    if (on && (cur === "uplink" || /^src:/.test(cur || "")) && scroll) $("sy-src-edsm").scrollIntoView({ block: "nearest" });   // (and the toggles under it)
    if (S.syEntry) syFocusClasses();
  }
  function pick(key) {   // a COMM1 pull on the UFC
    var ys = ((S.data || {}).syst || {}).entries || [];
    if (key === "remote") {   // (REMOTE: its list - on the page showing 1 Syst only; on a remote system: the current one)
      if (ED.remote.on()) ED.remote.current();
      else if (ED.showing("nav", 1)) ED.remote.open();
      return;
    }
    if (key && ys.some(function (e) { return e.key === key; })) syPick(key);
  }
  $("sy-rem").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-v]");
    if (!b) return;
    if (b.dataset.v === "cur") ED.remote.current();
    else ED.remote.open();   // (on a remote system already: the list again, to pick another)
  });
  // the picture for another page (Nav's Hist): a planet or star - its settlements (one highlighted, hl) and a
  // cross for you (me) - or a station's wireframe, as SVG in a 140 x 140 picture where a screen pixel is px of it
  ED.sysPic = function (pic, rot, tilt, px) {
    var keep = PX;
    PX = px || 1;
    try {
      if (pic.kind === "globe" || pic.kind === "star") return syGlobe(pic.sites, pic.hl || null, pic.me || null, rot, tilt, pic.kind === "star");
      return syWire(pic.kind === "surface" ? "settlement" : pic.kind, rot, tilt);
    } finally { PX = keep; }
  };

  ED.page({
    tab: "nav", sub: 1, key: 1, label: "Syst", el: "pg-syst-list", mode: "syst", back: "2 Nav · Syst", list: "syst",
    update: renderSyst,   // keeps the selection (and AUTO) current while another page shows
    cursor: cursor, pick: pick,
    enter: function () { ED.remote.sync(); syAnimate(); }, resume: syAnimate,   // (the board told: the keypad's not the list's unless it's open)
    leave: function () { if (ED.remote.isOpen()) ED.remote.close(); },   // (REMOTE's list goes with the page)
    knob1: function (clicks) { ED.remote.knob1(clicks); },   // (COMM1, the keypad: REMOTE's list's while it's open)
    pull1: function () { ED.remote.pull1(); },
    keypad: function (k) { ED.remote.key(k); },
    scroll: function (clicks) {   // COMM2 knob: switch -> picture -> details, then scrolls them
      if (!S.syEntry) { ED.scrollBox(null, clicks); return; }
      for (var c = 0; c < Math.min(12, Math.abs(clicks)); c++) syComm2(clicks > 0 ? 1 : -1);
    },
    dial: syDial,   // the UFC's dials, as speeds
    pull: function () { if (S.syEntry) syComm2Pull(); },
    longPull: function () { if (S.syEntry) syLongPull(); },
    // DSG: what COMM1 has highlighted, if it can be designated (a waypoint, or a surface site with a position), else what's picked
    dsg: function (n) { var k = [((S.ufc || {}).cursors || {}).syst, S.sySel].filter(ED.nav.dsgable)[0]; if (k) ED.nav.dsg(k, n); }
  });
  ED.SYMSG = SYMSG;
  ED.syPick = syPick;
  ED.syShape = syShape;
})();
