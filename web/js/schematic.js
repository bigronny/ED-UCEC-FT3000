// ED Target Board page - 2 Nav (Syst, Hist): Odyssey settlement schematics. The layout plans come from the board
// (its schematics folder, one file per layout); this draws one as a wireframe in the System tab's picture,
// looking straight down to start with, tilted to show the buildings' heights (BRT dial) and turned (COMM2
// VOLUME dial). The picture is a 140 x 140 SVG; px is how much of it one screen pixel covers, so lines and
// icons stay the same size on screen whether it's small or maximised. pixel.js puts the SVG on the screen
// in coarse pixels, drawing the icons' boxes (data-icon) and the names' dark bands (data-band) itself.
(function () {
  "use strict";
  var ED = window.ED;
  var CACHE = {}, LOADING = {};
  var PX_PER_M = 1 / 0.45;   // plan pixels per metre for heights when a plan gives no scale (heights are estimates anyway)
  var C = { roof: "#45f08a", power: "#8affc1", wall: "#25b85c", ground: "#1d6b3a", detail: "#26603a", walk: "#25b85c",
            pad: "#e3a24a", bg: "#060606", door: "#45f08a", lock: "#ff7b6b", term: "#8affc1", term2: "#e3a24a",
            power2: "#e3a24a", exp: "#f0fff4", loot: "#d9e85a", cz: "#ff6b5b", czp: "#ffd84a" };
  // the icon toggles: each icon type belongs to one (the map website's tips aren't shown). A plan fitted to
  // SrvSurvey (metric) gives each icon its toggle (g), colour (k) and letters itself
  var GROUP = { terminal_lo: "term", terminal_above_lo: "term", airlock: "door", inner_door: "door",
                power_regulator: "power", alarm_console: "power" };
  var KCOL = { lock: C.lock, door: C.door, term: C.term, term2: C.term2, power: C.power2, exp: C.exp, loot: C.loot,
               cz: C.cz, czp: C.czp };

  // a settlement economy's layouts (cached; fetched again if the board has a different number)
  function get(category, count) {
    var have = CACHE[category];
    if (have && have.length === count) return Promise.resolve(have);
    if (!LOADING[category]) {
      LOADING[category] = fetch("/api/schematics?category=" + encodeURIComponent(category), { cache: "no-store" })
        .then(function (r) { return r.json(); })
        .then(function (j) { delete LOADING[category]; CACHE[category] = j.layouts || []; return CACHE[category]; },
              function (err) { delete LOADING[category]; throw err; });
    }
    return LOADING[category];
  }

  // a plan's centre and every point it has (for fitting it to the picture), worked out once
  function prep(plan) {
    if (plan._c) return plan._c;
    var b = plan.bounds, cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2, pts = [];
    function see(p) { pts.push([p[0] - cx, p[1] - cy]); }
    ["buildings", "pads", "details"].forEach(function (k) { plan[k].forEach(function (s) { s.outline.forEach(see); }); });
    plan.walkways.forEach(function (w) { w.line.forEach(see); });
    plan.points.forEach(function (p) { see(p.at); });
    plan._c = { cx: cx, cy: cy, pts: pts, z: plan.m_per_px ? 1 / plan.m_per_px : PX_PER_M };
    return plan._c;
  }
  // the scale that fits the plan, turned and tilted like this, in the picture (hw, hh: half its width and height)
  function fit(c, cs, sn, cp, sp, hw, hh) {
    var mx = 1, my = 1;
    c.pts.forEach(function (q) {
      mx = Math.max(mx, Math.abs(q[0] * cs - q[1] * sn));
      my = Math.max(my, Math.abs(q[0] * sn + q[1] * cs));
    });
    return 0.9 * Math.min(hw / mx, hh / (my * cp + 14 * c.z * sp));   // tilted, it's shallower (plus the roofs' height)
  }

  var ZOOM_MAX = 8;
  // how the plan sits in the picture, for these options: its centre, the turn and tilt, the scale (the whole
  // settlement fits at zoom 1) and the pan (the plan point in the middle of the picture, from the centre)
  // (o.at and o.k instead: the plan's own origin - the settlement's position - at the picture point o.at, at o.k
  // of the picture's units per plan unit: drawn on a planet at its real size)
  function view(plan, o) {
    var c = prep(plan), th = (o.rot || 0) * Math.PI / 180, ph = (o.tilt || 0) * Math.PI / 180, pan = o.pan || [0, 0];
    var v = { c: c, cs: Math.cos(th), sn: Math.sin(th), cp: Math.cos(ph), sp: Math.sin(ph), px: pan[0], py: pan[1],
              cx: c.cx, cy: c.cy, ox: 70, oy: 70 };
    if (o.at) {
      v.cx = v.cy = v.px = v.py = 0;
      v.ox = o.at[0]; v.oy = o.at[1]; v.k = o.k;
    } else {
      v.k = fit(c, v.cs, v.sn, v.cp, v.sp, o.hw || 70, o.hh || 70) * (o.zoom || 1);
    }
    return v;
  }
  function toPlan(plan, o, sx, sy) {   // a point of the picture (on the ground) -> the plan's coordinates
    var v = view(plan, o), xr = (sx - v.ox) / v.k, yr = (sy - v.oy) / (v.k * Math.max(0.05, v.cp));
    return [xr * v.cs + yr * v.sn + v.cx + v.px, -xr * v.sn + yr * v.cs + v.cy + v.py];
  }
  function mpu(plan) {   // metres in one of the plan's units: its own scale, else (no scale) 1 km across
    var b = plan.bounds;
    return plan.m_per_px || 1000 / Math.max(1, b[2] - b[0]);
  }
  function scale(plan, o) { return view(plan, o).k / mpu(plan); }   // the picture's units per metre, shown like this
  function sizeM(plan) { var b = plan.bounds; return Math.max(b[2] - b[0], b[3] - b[1], 1) * mpu(plan); }   // its larger side (m)
  function originPan(plan) { var c = prep(plan); return clampPan(plan, [-c.cx, -c.cy]); }   // the pan that has its origin in the middle
  function clampPan(plan, pan) {   // the middle of the picture stays over the settlement
    var b = plan.bounds, hx = (b[2] - b[0]) / 2, hy = (b[3] - b[1]) / 2;
    return [Math.max(-hx, Math.min(hx, pan[0])), Math.max(-hy, Math.min(hy, pan[1]))];
  }
  // zoom by f, keeping the plan point under (sx, sy) where it is; back at 1, it's the whole settlement again
  function zoomAt(plan, o, sx, sy, f) {
    var z = Math.max(1, Math.min(ZOOM_MAX, (o.zoom || 1) * f)), pan = o.pan || [0, 0];
    if (z <= 1.001) return { zoom: 1, pan: [0, 0] };
    var before = toPlan(plan, o, sx, sy), after = toPlan(plan, Object.assign({}, o, { zoom: z }), sx, sy);
    return { zoom: z, pan: clampPan(plan, [pan[0] + before[0] - after[0], pan[1] + before[1] - after[1]]) };
  }
  // move the middle of the picture by (dx, dy) of the picture's units (the way the screen faces)
  function panBy(plan, o, dx, dy) {
    var a = toPlan(plan, o, 70, 70), b = toPlan(plan, o, 70 + dx, 70 + dy), pan = o.pan || [0, 0];
    return clampPan(plan, [pan[0] + b[0] - a[0], pan[1] + b[1] - a[1]]);
  }

  // o: rot (the turn, degrees clockwise: the plan's up points this way round from the picture's up), tilt
  //    (0 = straight down .. 80), zoom (1 = the whole settlement), pan, px, max (maximised: labels and full
  //    icons), icons ({term, door, ...}: which to show), hw / hh (half the picture's width / height; 70 when
  //    small), me (you: {at: plan point, dir: degrees from the plan's up, or null}; Align Settlement)
  function draw(plan, o) {
    var v = view(plan, o), c = v.c, px = o.px || 1;
    function xy(p, hm) {   // a plan point, hm metres up -> [x, y] in the picture
      var x = p[0] - v.cx - v.px, y = p[1] - v.cy - v.py, z = (hm || 0) * c.z;
      var xr = x * v.cs - y * v.sn, yr = x * v.sn + y * v.cs;
      return [v.ox + xr * v.k, v.oy + (yr * v.cp - z * v.sp) * v.k];
    }
    function f(q) { return q[0].toFixed(1) + " " + q[1].toFixed(1); }
    // an outline, hm metres up: [its edges, its cut-off edges] - an edge the map picture cut off (cut: their
    // numbers) isn't a real wall, so it's drawn apart, faint and broken, as if it carries on
    function ring(pts, hm, cut) {
      var P = pts.map(function (p) { return f(xy(p, hm)); });
      if (!cut || !cut.length) return ["M" + P.join(" L") + " Z", ""];
      var solid = "", faint = "", pen = false;
      for (var i = 0; i < P.length; i++) {
        var a = P[i], b = P[(i + 1) % P.length];
        if (cut.indexOf(i) >= 0) { faint += "M" + a + " L" + b + " "; pen = false; }
        else { solid += (pen ? " L" : "M" + a + " L") + b; pen = true; }
      }
      return [solid, faint];
    }
    function u(n) { return (n * px).toFixed(2); }
    function path(d, col, w, dash) {
      return d ? '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="' + u(w) + '"' +
        (dash ? ' stroke-dasharray="' + u(dash[0]) + " " + u(dash[1]) + '"' : "") + ' stroke-linejoin="round"></path>' : "";
    }
    var out = [], tilted = (o.tilt || 0) > 1.5;
    function layer(rings, col, w, dash) {   // a set of outlines, with any cut-off edges faint and broken
      out.push(path(rings.map(function (r) { return r[0]; }).join(" "), col, w, dash));
      var faint = rings.map(function (r) { return r[1]; }).join("");
      if (faint) out.push(path(faint, col, w * 0.8, [1.5, 4]).replace("<path ", '<path opacity="0.45" '));
    }

    // landing pads: dashed amber outlines on the ground
    layer(plan.pads.map(function (p) { return ring(p.outline, 0, p.cut); }), C.pad, 1, [4, 3]);
    if (o.max) {   // maximised: each pad's size and number (L2: pad 2, large), as the game numbers them
      plan.pads.forEach(function (p) {
        if (p.num == null) return;
        var sx = 0, sy = 0;
        p.outline.forEach(function (q) { sx += q[0]; sy += q[1]; });
        var q = xy([sx / p.outline.length, sy / p.outline.length], 0);
        out.push('<text x="' + q[0].toFixed(1) + '" y="' + q[1].toFixed(1) + '" data-band="1" font-family="VGA, monospace" font-size="' + u(14) +
                 '" fill="' + C.pad + '" text-anchor="middle" dominant-baseline="central" opacity="0.9">' + ED.esc((p.size || "") + p.num) + "</text>");
      });
    }
    // walkways: their two edges
    var walk = [];
    plan.walkways.forEach(function (w) {
      for (var i = 0; i < w.line.length - 1; i++) {
        var a = w.line[i], b = w.line[i + 1], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        var nx = -(b[1] - a[1]) / L * w.w / 2, ny = (b[0] - a[0]) / L * w.w / 2, hm = w.kind === "bridge" ? 3 : 0;
        walk.push("M" + f(xy([a[0] + nx, a[1] + ny], hm)) + " L" + f(xy([b[0] + nx, b[1] + ny], hm)));
        walk.push("M" + f(xy([a[0] - nx, a[1] - ny], hm)) + " L" + f(xy([b[0] - nx, b[1] - ny], hm)));
      }
    });
    out.push(path(walk.join(" "), C.walk, 0.8));
    // small structures: dim outlines
    layer(plan.details.map(function (x) { return ring(x.outline, 0, x.cut); }), C.detail, 0.8);
    // buildings: footprint, walls when tilted, roof
    var ground = [], walls = [], roofs = [], power = [];
    plan.buildings.forEach(function (b) {
      var h = b.h || (b.kind === "other" ? 3 : 6);
      if (tilted) {
        ground.push(ring(b.outline, 0, b.cut));
        b.outline.forEach(function (p) { walls.push("M" + f(xy(p, 0)) + " L" + f(xy(p, h))); });
      }
      (b.kind === "power" ? power : roofs).push(ring(b.outline, h, b.cut));
    });
    layer(ground, C.ground, 0.7);
    out.push(path(walls.join(" "), C.wall, 0.6));
    layer(roofs, C.roof, 1.2);
    layer(power, C.power, 1.4);
    // names on the roofs (maximised only: too small to read otherwise). Where a plan gives where each name
    // is printed - a building can have several (HAB and MED, CMD with SEC and OPR) - they go there; otherwise
    // a building's name goes in its middle
    if (o.max) {
      var byId = {}, placed = {};
      plan.buildings.forEach(function (b) { if (b.id) byId[b.id] = b; });
      (plan.labels || []).forEach(function (l) { placed[l.building] = true; });
      var names = (plan.labels || []).map(function (l) { return { text: l.text, at: l.at, b: byId[l.building] || {} }; });
      plan.buildings.forEach(function (b) {
        if (!b.label || placed[b.id]) return;
        var sx = 0, sy = 0;
        b.outline.forEach(function (p) { sx += p[0]; sy += p[1]; });
        names.push({ text: b.label, at: [sx / b.outline.length, sy / b.outline.length], b: b });
      });
      names.forEach(function (n) {
        var q = xy(n.at, n.b.h || 6);
        out.push('<text x="' + q[0].toFixed(1) + '" y="' + q[1].toFixed(1) + '" data-band="1" font-family="VGA, monospace" font-size="' + u(14) +
                 '" fill="' + (n.b.kind === "power" ? C.power : C.roof) + '" text-anchor="middle" dominant-baseline="central" opacity="0.85">' +
                 ED.esc(n.text) + "</text>");
      });
    }
    // icons, by the toggles
    var on = o.icons || {};
    plan.points.forEach(function (p) {
      var g = "g" in p ? p.g : GROUP[p.type];
      if (!g || !on[g]) return;
      var q = xy(p.at, 0.5), x = q[0].toFixed(1), y = q[1].toFixed(1);
      var col = p.k ? KCOL[p.k] : { airlock: C.lock, inner_door: C.door, terminal_lo: C.term, terminal_above_lo: C.term2,
                  power_regulator: C.power2, alarm_console: C.power2 }[p.type];
      if (!o.max) {   // small: a dot
        out.push('<circle cx="' + x + '" cy="' + y + '" r="' + u(2.4) + '" fill="' + col + '"></circle>');
        return;
      }
      var text = p.k ? String(p.text || "") : p.type === "terminal_lo" ? "T" : p.type === "terminal_above_lo" ? "T+" :
        String(p.text || (p.access != null ? p.access : "")).replace(/^A.*/, "A");
      // its box (data-icon: square for terminals, a ring for combat-zone points, rounded otherwise) is drawn
      // with it, in pixels
      var shape = g === "cz" ? "ring" : /terminal/.test(p.type) ? "box" : "pill";
      out.push('<text x="' + x + '" y="' + y + '" data-icon="' + shape + '" font-family="VGA, monospace" font-size="' + u(13) +
               '" fill="' + col + '" text-anchor="middle" dominant-baseline="central">' + ED.esc(text) + "</text>");
    });
    if (o.me) out.push(you(o.me, xy, px, o.hw || 70, o.hh || 70));
    return out.join("");
  }
  // you (o.me: at, the plan point you're at; dir, the way you face from the plan's up, clockwise, or null):
  // an arrow the way you face (a cross if that isn't known); off the picture, a pointer at its edge towards you
  function you(me, xy, px, hw, hh) {
    var col = "#8affc1", q = xy(me.at, 0), L = 9 * px, edge = 10 * px;
    function pt(x, y) { return x.toFixed(1) + "," + y.toFixed(1); }
    var x0 = 70 - hw + edge, x1 = 70 + hw - edge, y0 = 70 - hh + edge, y1 = 70 + hh - edge;
    if (q[0] < x0 || q[0] > x1 || q[1] < y0 || q[1] > y1) {   // off the picture: along the line from the middle, at the edge
      var dx = q[0] - 70, dy = q[1] - 70, k = Math.min(dx ? (dx > 0 ? x1 - 70 : x0 - 70) / dx : 1e9, dy ? (dy > 0 ? y1 - 70 : y0 - 70) / dy : 1e9);
      var ex = 70 + dx * k, ey = 70 + dy * k, n = Math.hypot(dx, dy) || 1, ux = dx / n, uy = dy / n, s = 5 * px;
      return '<polygon points="' + [pt(ex + ux * s, ey + uy * s), pt(ex - ux * s - uy * s, ey - uy * s + ux * s), pt(ex - ux * s + uy * s, ey - uy * s - ux * s)].join(" ") +
        '" fill="' + col + '" stroke="' + col + '" stroke-width="' + (px).toFixed(2) + '"></polygon>';
    }
    if (me.dir == null) {
      return '<path d="M' + pt(q[0] - 5 * px, q[1] - 5 * px).replace(",", " ") + " L" + pt(q[0] + 5 * px, q[1] + 5 * px).replace(",", " ") +
        " M" + pt(q[0] + 5 * px, q[1] - 5 * px).replace(",", " ") + " L" + pt(q[0] - 5 * px, q[1] + 5 * px).replace(",", " ") +
        '" stroke="' + col + '" stroke-width="' + (2 * px).toFixed(2) + '" fill="none"></path>';
    }
    var a = me.dir * Math.PI / 180, ahead = xy([me.at[0] + 5 * Math.sin(a), me.at[1] - 5 * Math.cos(a)], 0);
    var vx = ahead[0] - q[0], vy = ahead[1] - q[1], vn = Math.hypot(vx, vy) || 1;
    vx /= vn; vy /= vn;   // the way you face, on the screen (tilted, it's foreshortened along the way the picture faces)
    var tip = [q[0] + vx * L, q[1] + vy * L], back = [q[0] - vx * L * 0.7, q[1] - vy * L * 0.7], notch = [q[0] - vx * L * 0.2, q[1] - vy * L * 0.2];
    return '<polygon points="' + [pt(tip[0], tip[1]), pt(back[0] - vy * L * 0.7, back[1] + vx * L * 0.7), pt(notch[0], notch[1]),
                                  pt(back[0] + vy * L * 0.7, back[1] - vx * L * 0.7)].join(" ") +
      '" fill="' + col + '" stroke="' + col + '" stroke-width="' + px.toFixed(2) + '"></polygon>';
  }

  // how wide the settlement is drawn at zoom 1 (looking straight down, turned rot degrees: 0 = its layout's up
  // at the top) in a picture hw x hh (half sizes), and how wide it really is (km): its plan's scale if it has
  // one, else 1 km (the true-scale descent)
  function width(plan, hw, hh, rot) {
    var c = prep(plan), b = plan.bounds, th = (rot || 0) * Math.PI / 180;
    return fit(c, Math.cos(th), Math.sin(th), 1, 0, hw, hh) * Math.max(1, b[2] - b[0]);
  }
  function widthKm(plan) {
    var b = plan.bounds;
    return plan.m_per_px ? Math.max(1, b[2] - b[0]) * plan.m_per_px / 1000 : 1;
  }
  function byId(id) {   // a layout plan already fetched, by its id
    for (var cat in CACHE) {
      var p = CACHE[cat].find(function (x) { return x.id === id; });
      if (p) return p;
    }
    return null;
  }
  ED.schem = { get: get, draw: draw, GROUP: GROUP, zoomAt: zoomAt, panBy: panBy, ZOOM_MAX: ZOOM_MAX, width: width, widthKm: widthKm,
               mpu: mpu, scale: scale, sizeM: sizeM, originPan: originPan, byId: byId };
})();
