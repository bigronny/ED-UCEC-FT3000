// ED Target Board page - 2 Nav, sub-tab 1 (Syst), its map: the whole system across the width.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  S.map = { pan: { x: 0, y: 0 }, sig: "", sys: "", lay: null, raf: 0, t0: 0, last: 0, dirty: true, revealed: false, lastCur: null, uz: 1 };
  try { S.map.uz = Math.max(0.2, Math.min(5, parseFloat(localStorage.getItem("edtb.mapzoom")) || 1)); } catch (err) { /* no storage */ }

  // ---- drawing (about 30 times a second while the map shows; only what's in view) ----
  function mapOn() { return ED.showing("nav", 2) && !S.halted && !document.hidden && !ED.hyper.on(); }
  function mapKick() { S.map.dirty = true; if (!S.map.raf && mapOn()) S.map.raf = requestAnimationFrame(mapFrame); }
  function mapFrame(now) {
    S.map.raf = 0;
    if (!mapOn()) return;
    if (!S.map.t0) S.map.t0 = now;
    var still = reduce.matches;
    if (!still && !S.map.dirty && now - S.map.last < 33) { S.map.raf = requestAnimationFrame(mapFrame); return; }
    S.map.last = now;
    S.map.dirty = false;
    mapDraw(still ? 0 : (now - S.map.t0) / 1000);
    if (!still) S.map.raf = requestAnimationFrame(mapFrame);
  }
  function ufcCursor() { var u = S.ufc || {}; return u.menu === "PAGE" ? (u.cursors || {}).syst || null : null; }   // the UFC knob's highlight
  function mapPickKey() { return ufcCursor() || S.sySel; }
  function mapCursorOut() { return !!ufcCursor(); }
  function mapSelKey() {   // the selection; a surface site is marked on its planet
    var k = S.sySel, L = S.map.lay, hosts = ((((S.data || {}).syst || {}).map) || {}).hosts || {};
    return L && !L.nodes[k] && hosts[k] ? hosts[k] : k;
  }
  function mapHlKey() {   // a surface site (not drawn on the map) highlights its planet
    var k = mapPickKey(), L = S.map.lay, hosts = ((((S.data || {}).syst || {}).map) || {}).hosts || {};
    return L && !L.nodes[k] && hosts[k] ? hosts[k] : k;
  }
  function mapYouKey() { var y = (S.data || {}).syst || {}; return y.docked || (y.me && y.me.key) || null; }
  // The map scales to the space it has: it fills the height between the bar along the top and
  // the strip along the bottom, but a system narrow enough to fit the width at a comfortable size
  // is shown whole instead. Never smaller than its phone size. - / + (and Ctrl+wheel, pinch) adjust it.
  function mapView() {
    var cv = $("sm-cv"), bar = document.querySelector(".smtop"), info = $("sm-info"), L = S.map.lay;
    var w = cv.clientWidth, h = cv.clientHeight, top = bar ? bar.offsetTop + bar.offsetHeight + 6 : 44, bot = info ? info.offsetHeight : 34;
    var avail = Math.max(60, h - top - bot), auto = 1;
    if (L) {
      var fitW = w / L.W, base = 0.75 * avail / 290;   // 290: about the map's height on a phone
      auto = Math.max(1, Math.min(3, Math.min(avail / L.H, fitW >= 0.85 * base ? fitW : base)));
    }
    var z = Math.max(0.5, Math.min(5, auto * (S.map.uz || 1)));
    var oy = L ? Math.max(0, (avail / z - L.H) / 2) : 0;   // shorter than the space: centred up and down
    return { w: w, h: h, top: top, bot: bot, auto: auto, z: z, vw: w / z, vh: avail / z, oy: oy };
  }
  function mapClamp(v) {
    var L = S.map.lay, p = S.map.pan;
    if (!L) return;
    v = v || mapView();
    p.x = Math.max(0, Math.min(p.x, L.W - v.vw));
    p.y = Math.max(0, Math.min(p.y, L.H - v.vh));
  }
  function mapZoomAt(uz, sx, sy) {   // zoom keeping the point under (sx, sy) on the canvas still
    var v = mapView(), p = S.map.pan, nx = p.x + sx / v.z, ny = p.y - v.oy + (sy - v.top) / v.z;
    S.map.uz = Math.max(0.5 / v.auto, Math.min(5 / v.auto, uz));
    var v2 = mapView();
    p.x = nx - sx / v2.z; p.y = ny + v2.oy - (sy - v2.top) / v2.z;
    mapClamp(v2);
    try { localStorage.setItem("edtb.mapzoom", String(S.map.uz)); } catch (err) { /* no storage */ }
    mapKick();
  }
  function mapDraw(t) {
    var cv = $("sm-cv"), w = cv.clientWidth, h = cv.clientHeight;
    if (!w || !h) return;
    var ctx = ED.pixel.layers(cv, w, h), L = S.map.lay;   // wireframes in coarse pixels, names over them in full
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (!L) return;
    var v = mapView();
    mapClamp(v);
    var p = S.map.pan, x0 = p.x - 40, x1 = p.x + v.vw + 40, y0 = p.y - 40, y1 = p.y + v.vh + v.bot / v.z + 40;
    ctx.beginPath(); ctx.rect(0, v.top - 6, w, h - v.top + 6); ctx.clip();   // nothing under the bar along the top
    ctx.translate(0, v.top);
    ctx.scale(v.z, v.z);
    ctx.translate(-p.x, v.oy - p.y);
    ED.mapScene(ctx, L, t, { view: { x0: x0, x1: x1, y0: y0, y1: y1 } });   // the system map drawing (shared with hyperspace)
    // the selection (what the details show) gets bright corners, as its row is filled on the list;
    // the UFC cursor, when it's out, gets amber ones (outside the selection's, if on the same one)
    function corners(n, grow, col) {
      var hb = (n.drawR || Math.max(n.hw, n.hh)) + (n.d && n.d.land ? 9 : 6) + grow, c = Math.min(9 + grow / 2, hb * 0.7), hx = n.x, hy = n.y;
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.setLineDash([]); ctx.beginPath();
      [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(function (s) {
        ctx.moveTo(hx + s[0] * hb, hy + s[1] * (hb - c)); ctx.lineTo(hx + s[0] * hb, hy + s[1] * hb); ctx.lineTo(hx + s[0] * (hb - c), hy + s[1] * hb);
      });
      ctx.stroke();
    }
    var sn = L.nodes[mapSelKey()], cn = mapCursorOut() ? L.nodes[mapHlKey()] : null;
    if (sn) { ctx.save(); ctx.shadowColor = ED.MAP.hi; ctx.shadowBlur = 6; corners(sn, 0, ED.MAP.hi); ctx.restore(); }
    if (cn) corners(cn, cn === sn ? 7 : 0, ED.MAP.amber);
    var yn = L.nodes[mapYouKey()];
    if (yn) {   // where you are
      var ty = yn.y - (yn.reach ? yn.reach.t : yn.drawR || yn.hh) - 9 - (cn === yn && sn === yn ? 8 : 0);   // clear of both sets of corners
      ctx.fillStyle = ED.MAP.amber; ctx.beginPath(); ctx.moveTo(yn.x, ty + 5); ctx.lineTo(yn.x - 5, ty - 2); ctx.lineTo(yn.x + 5, ty - 2); ctx.closePath(); ctx.fill();
      ctx.textAlign = "center"; ctx.fillText("YOU", yn.x, ty - 6);
    }
    ctx.finish();   // hard-edged coarse pixels
  }

  // ---- what the map shows, and moving around it ----
  function mapReveal(key, centre) {   // pan so this one is in view (or in the middle)
    var L = S.map.lay, n = L && L.nodes[key], v = mapView(), p = S.map.pan, m = 40;
    if (!n || !v.w) return;
    var e = Math.max(n.hw, n.hh);
    if (centre) p.x = n.x - v.vw / 2;
    else {
      if (n.x - e - m < p.x) p.x = n.x - e - m;
      if (n.x + e + m > p.x + v.vw) p.x = n.x + e + m - v.vw;
    }
    if (n.y - e - m < p.y) p.y = n.y - e - m;
    if (n.y + e + m > p.y + v.vh) p.y = n.y + e + m - v.vh;
    mapClamp(v);
    mapKick();
  }
  // on the map, the COMM2 volume knob pans across and the brightness knob up and down (clockwise:
  // right / down); one end-to-end turn crosses the whole map, with some to spare
  function mapDial(r, dt) {   // speeds (-1..1) for dt seconds: zoom (clockwise in, 4 times a second at full turn), and
    var L = S.map.lay, v = mapView(), cue = { z: "", t: "" };   // pan (half the view a second; clockwise right / down)
    if (!L) return cue;
    if (r.zoom) {
      mapZoomAt(S.map.uz * Math.exp(Math.log(4) * r.zoom * dt), v.w / 2, v.top + (v.h - v.top - v.bot) / 2);
      cue.z = r.zoom > 0 ? "Z+" : "Z-";
      v = mapView();
    }
    if (r.yaw || r.pitch) {
      S.map.pan.x += r.yaw * v.vw * 0.5 * dt;
      S.map.pan.y += r.pitch * v.vh * 0.5 * dt;
      mapClamp(v);
      mapKick();
      cue.t = r.yaw ? (r.yaw > 0 ? ">>" : "<<") : (r.pitch > 0 ? "DN" : "UP");
    }
    return cue;
  }
  function mapPanBy(dx, dy) {   // in screen pixels
    var v = mapView();
    S.map.pan.x += dx / v.z; S.map.pan.y += dy / v.z;
    mapClamp(v);
    mapKick();
  }
  function mapDays(d) {
    d = Math.abs(d);
    return d < 1 ? (d * 24).toFixed(1) + " h" : d < 1000 ? d.toFixed(1) + " d" : (d / 365.25).toFixed(1) + " yr";
  }
  function mapInfo() {   // the strip along the bottom: the highlighted body or station
    var L = S.map.lay, n = L && L.nodes[mapHlKey()], el = $("sm-info"), name = "", bits = [], pk = mapPickKey();
    var site = L && !L.nodes[pk] && S.syByKey && S.syByKey[pk];
    if (site && n) {   // a surface site: its name and kind, then the planet it's on
      name = site.name;
      bits.push(((site.lab || "").split(" \u00b7 ")[0] || "Surface site") + " on " + n.d.name);
    } else if (n && n.t === "body") {
      var b = n.d;
      name = b.name;
      bits.push(b.sub || (b.star ? "Star" : "Planet"));
      if (b.land) {
        var sp = [];
        if (b.ports) sp.push(b.ports + (b.ports === 1 ? " port" : " ports"));
        if (b.sites) sp.push(b.sites + (b.sites === 1 ? " settlement" : " settlements"));
        bits.push("Landable" + (sp.length ? " · " + sp.join(" · ") : ""));
      }
      if ((b.rings || []).length) bits.push("Ringed");
      if (b.rot) bits.push("Day " + mapDays(b.rot) + (b.rot < 0 ? " retrograde" : "") + (b.locked ? " locked" : "") +
                           (Math.abs(b.rot) * ED.MAP.day < ED.MAP.minTurn ? " (shown slower)" : ""));
      if (b.tilt != null) bits.push("Tilt " + b.tilt.toFixed(1) + "°");
      if (b.ls && !b.main) bits.push(ED.num(b.ls) + " ls");
    } else if (n && n.t === "station") {
      var host = n.d.host && L.nodes[n.d.host];
      name = n.d.name;
      bits.push(n.d.type);
      if (host) bits.push((n.d.est ? "near " : "orbits ") + host.d.name);
    } else if (n && n.t === "carrier") {
      name = n.d.n + (n.d.n === 1 ? " fleet carrier" : " fleet carriers");
      bits.push("seen here by EDSM");
    }
    var html = name ? '<span class="hl">' + ED.esc(name) + "</span> · " + ED.esc(bits.join(" · ")) : "Tap a body or station for its details";
    if (el.innerHTML !== html) el.innerHTML = html;
  }
  function mapUpdate(y, ok) {   // every refresh, showing or not
    $("symap").classList.toggle("none", !ok);
    var u = S.ufc || {};
    if (!ok) {
      $("sm-msg").textContent = ED.SYMSG[y.status] || "No system data";
      $("sm-lab").innerHTML = (y.remote || {}).on ? '<span class="rmt">Remote · ' + ED.esc(y.system || "System") + "</span>" : ED.esc(y.system || "System");
      S.map.lay = null; S.map.sig = "";
      mapKick();
      return;
    }
    var m = y.map || { bodies: [], stations: [] }, fontOk = !document.fonts || document.fonts.check("16px VGA");
    var sig = [y.system, y.fetched, (m.bodies || []).length, (m.stations || []).length, m.carriers, fontOk].join("|");
    if (sig !== S.map.sig) {
      if (S.map.sys !== y.system) { S.map.pan = { x: 0, y: 0 }; S.map.revealed = false; }
      S.map.sig = sig; S.map.sys = y.system;
      S.map.lay = ED.mapLayout(m);
    }
    $("sm-lab").innerHTML = ((y.remote || {}).on ? '<span class="rmt">Remote · ' + ED.esc(y.system) + "</span>" : ED.esc(y.system)) + " · " +
      (m.bodies || []).length + " bodies" + (u.menu === "PAGE" ? ' <span class="ufc">· UFC</span>' : "");
    if (ED.showing("nav", 2) && !S.map.revealed && $("sm-cv").clientWidth) {   // first look: start where you are
      S.map.revealed = true;
      var k = mapYouKey() || mapHlKey();
      if (k && k !== (m.bodies[0] || {}).key) mapReveal(k, true);
    }
    mapInfo();
    mapKick();
  }
  function mapKeySymbols() {   // the planet type symbols in the key, two columns
    var rows = [["metal3", "Metal-rich"], ["metal2", "High metal"], ["rock", "Rocky"], ["rockice", "Rocky ice"],
                ["ice", "Icy"], ["earth", "Earth-like"], ["water", "Water world"], ["ammonia", "Ammonia"],
                ["gas", "Gas giant I-V"], ["helium", "Helium giant"], ["lifeW", "Life (water)"], ["lifeA", "Life (ammonia)"],
                ["watergiant", "Water giant"], ["watergiantlife", "Water giant, life"]];
    var cv = $("sm-keycv"), dpr = Math.min(2, window.devicePixelRatio || 1), w = 336, rh = 22, h = Math.ceil(rows.length / 2) * rh;
    cv.style.width = w + "px"; cv.style.height = h + "px"; cv.width = w * dpr; cv.height = h * dpr;
    var ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    ctx.font = "16px VGA"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
    rows.forEach(function (r, i) {
      var x = (i % 2) * (w / 2), y = Math.floor(i / 2) * rh + rh / 2;
      ctx.save(); ctx.translate(x + 12, y); ctx.scale(1.4, 1.4); ED.mapGlyph(ctx, { glyph: r[0], num: "II" }, 0, 0); ctx.restore();
      ctx.fillStyle = ED.MAP.green; ctx.fillText(r[1].toUpperCase(), x + 28, y + 1);
    });
  }
  (function () {   // dragging, pinching, tapping and the mouse wheel on the map
    var cv = $("sm-cv"), drag = null, pts = {}, pinch = null;
    function local(e) { var r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    function pair() {
      var k = Object.keys(pts), a = pts[k[0]], b = pts[k[1]];
      return { d: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, x: (a[0] + b[0]) / 2, y: (a[1] + b[1]) / 2 };
    }
    cv.addEventListener("pointerdown", function (e) {
      pts[e.pointerId] = local(e);
      try { cv.setPointerCapture(e.pointerId); } catch (err) { /* old browsers */ }
      if (Object.keys(pts).length === 2) { var q = pair(); pinch = { d: q.d, uz: S.map.uz }; drag = null; return; }
      if (!pinch) drag = { x: e.clientX, y: e.clientY, px: S.map.pan.x, py: S.map.pan.y, moved: false };
    });
    cv.addEventListener("pointermove", function (e) {
      if (pts[e.pointerId]) pts[e.pointerId] = local(e);
      if (pinch && Object.keys(pts).length >= 2) { var q = pair(); mapZoomAt(pinch.uz * q.d / pinch.d, q.x, q.y); return; }
      if (!drag) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) > 6) { drag.moved = true; cv.classList.add("drag"); }
      if (drag.moved) { var v = mapView(); S.map.pan.x = drag.px - dx / v.z; S.map.pan.y = drag.py - dy / v.z; mapClamp(v); mapKick(); }
    });
    function end(e) {
      delete pts[e.pointerId];
      if (pinch) { if (!Object.keys(pts).length) pinch = null; return; }
      if (!drag) return;
      var d = drag;
      drag = null;
      cv.classList.remove("drag");
      if (d.moved || e.type !== "pointerup") return;
      var v = mapView(), lp = local(e), px = lp[0] / v.z + S.map.pan.x, py = (lp[1] - v.top) / v.z + S.map.pan.y - v.oy;
      var L = S.map.lay, best = null, bd = 1e9;
      (L ? L.flat : []).forEach(function (n) {   // what was tapped (generous on small ones)
        var cx = n.labSide === "right" ? n.x + n.lw / 2 : n.x, hw = Math.max(n.hw, 11) + 5 + (n.labSide === "right" ? n.lw / 2 : 0), hh = Math.max(n.hh, 11) + 5;
        var dx = Math.abs(px - cx), dy = Math.abs(py - n.y);
        if (dx <= hw && dy <= hh && dx + dy < bd) { bd = dx + dy; best = n; }
      });
      if (best) ED.syPick(best.key);
    }
    cv.addEventListener("pointerup", end);
    cv.addEventListener("pointercancel", end);
    cv.addEventListener("wheel", function (e) {
      e.preventDefault();
      if (e.ctrlKey) { var lp = local(e); mapZoomAt(S.map.uz * Math.pow(1.0015, -e.deltaY), lp[0], lp[1]); }   // also a trackpad pinch
      else if (e.shiftKey) mapPanBy(0, e.deltaY);
      else mapPanBy(Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY, 0);
    }, { passive: false });
    cv.addEventListener("dblclick", function () { var v = mapView(); mapZoomAt(1, v.w / 2, v.top + (v.h - v.top - v.bot) / 2); });
    function zoomBy(k) { var v = mapView(); mapZoomAt(S.map.uz * k, v.w / 2, v.top + (v.h - v.top - v.bot) / 2); }
    $("sm-zin").addEventListener("click", function () { zoomBy(1.25); });
    $("sm-zout").addEventListener("click", function () { zoomBy(0.8); });
    window.addEventListener("resize", mapKick);
    document.addEventListener("visibilitychange", mapKick);
    $("sm-keyb").addEventListener("click", function () {
      var on = !$("symap").classList.contains("key");
      $("symap").classList.toggle("key", on);
      $("sm-keyb").setAttribute("aria-expanded", on ? "true" : "false");
      if (on) mapKeySymbols();
    });
  })();

  // ---- the page ----
  ED.page({
    tab: "nav", sub: 2, key: 1, label: "Syst", el: "pg-syst-map", mode: "syst symap", back: "2 Nav · Syst map", list: "syst",   // picks go to the list page
    update: function (s) {
      var y = s.syst || {}, entries = y.entries || [];
      mapUpdate(y, entries.length > 0 && (y.status === "ok" || y.status === "stale"));
    },
    enter: function (viaTab) {   // from the list: start again where you are
      if (!viaTab) S.map.revealed = false;
      mapKick();
    },
    resume: mapKick,
    cursor: function (u, scroll) {   // the map follows the UFC knob's highlight too
      if (!ED.showing("nav", 2)) return;
      var mc = ufcCursor();
      if (mc !== S.map.lastCur) { S.map.lastCur = mc; if (mc && scroll) mapReveal(mc, false); }
      mapInfo();
      mapKick();
    },
    dial: mapDial,   // the UFC's dials, as speeds: COMM1 VOLUME zooms, COMM2 VOLUME pans across and BRT up and down
    dsg: function (n) { var k = [ufcCursor(), S.sySel].filter(ED.nav.dsgable)[0]; if (k) ED.nav.dsg(k, n); }   // DSG: as the list's
  });
})();
