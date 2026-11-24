// ED Target Board page - the Syst (and Hist) picture at the screen's own coarse pixels. syst.js and schematic.js draw
// the picture as SVG (which stays, unseen, for the tests and for working out where a click lands); this
// redraws that SVG on a canvas pixel by pixel - one-pixel lines with no smoothing, as VGA graphics had - on a
// grid the size of one pixel of the page's VGA text (TEXT_PIXELS), as if the picture were part of the same
// screen: maximised, it has more of those pixels, not finer ones. Building names use a 5 x 7 pixel font,
// icons a 3 x 5 one, as the picture's own small lettering.
(function () {
  "use strict";
  var ED = window.ED;
  // 5 x 7 letters: a byte a column, top row in the lowest bit
  var F57 = {
    "A": [0x7C, 0x12, 0x11, 0x12, 0x7C], "B": [0x7F, 0x49, 0x49, 0x49, 0x36], "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C], "E": [0x7F, 0x49, 0x49, 0x49, 0x41], "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A], "H": [0x7F, 0x08, 0x08, 0x08, 0x7F], "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01], "K": [0x7F, 0x08, 0x14, 0x22, 0x41], "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F], "N": [0x7F, 0x04, 0x08, 0x10, 0x7F], "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06], "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E], "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31], "T": [0x01, 0x01, 0x7F, 0x01, 0x01], "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F], "W": [0x3F, 0x40, 0x38, 0x40, 0x3F], "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07], "Z": [0x61, 0x51, 0x49, 0x45, 0x43],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E], "1": [0x00, 0x42, 0x7F, 0x40, 0x00], "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31], "4": [0x18, 0x14, 0x12, 0x7F, 0x10], "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30], "7": [0x01, 0x71, 0x09, 0x05, 0x03], "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
    "/": [0x20, 0x10, 0x08, 0x04, 0x02], "^": [0x04, 0x02, 0x01, 0x02, 0x04], "+": [0x08, 0x08, 0x3E, 0x08, 0x08],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08], ".": [0x00, 0x60, 0x60, 0x00, 0x00], " ": [0, 0, 0, 0, 0],
    // a few small letters, for the range bar's units (m, km, Mm, ls)
    "k": [0x7F, 0x10, 0x28, 0x44, 0x00], "l": [0x00, 0x41, 0x7F, 0x40, 0x00], "m": [0x7C, 0x04, 0x18, 0x04, 0x78],
    "s": [0x48, 0x54, 0x54, 0x54, 0x20],
    // and for the Traj page's angles and times
    "\u00b0": [0x00, 0x06, 0x09, 0x09, 0x06], "\u00b1": [0x48, 0x48, 0x5E, 0x48, 0x48], ":": [0x00, 0x36, 0x36, 0x00, 0x00]
  };
  // 3 x 5 letters for the icons: rows, left to right
  var F35 = { "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
              "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001",
              "8": "111101111101111", "9": "111101111001111", "A": "010101111101101", "P": "110101110100100",
              "T": "111010010010010", "i": "010000010010010", "^": "010101000000000", "+": "000010111010000",
              "B": "110101110101110", "C": "111100100100111", "D": "110101101101110", "E": "111100111100111",
              "F": "111100111100100", "H": "101101111101101", "L": "100100100100111", "S": "011100010001110",
              "U": "101101101101111" };

  var TEXT_PIXELS = 1;   // how many of the text's pixels make one of the picture's
  // one pixel of the picture, in device pixels: TEXT_PIXELS of the page's text (the 8 x 16 VGA font at the
  // body's size), rounded to whole device pixels so every pixel of the picture is the same size
  function grain() {
    var fs = parseFloat(getComputedStyle(document.body).fontSize) || 24.5, dpr = window.devicePixelRatio || 1;
    return { dev: Math.max(1, Math.round(fs / 16 * TEXT_PIXELS * dpr)), dpr: dpr };
  }
  var COLS = {};
  function rgb(col, alpha) {   // "#rrggbb", faded by alpha towards black -> a packed pixel (null: none)
    var a = alpha == null ? 1 : Math.max(0, Math.min(1, alpha)), key = col + a;
    if (key in COLS) return COLS[key];
    var m = /^#([0-9a-f]{6})$/i.exec(col || ""), v = null;
    if (m && a > 0) {
      var n = parseInt(m[1], 16);
      var r = Math.round(((n >> 16) & 255) * a), g = Math.round(((n >> 8) & 255) * a), b = Math.round((n & 255) * a);
      v = (0xff000000 | (b << 16) | (g << 8) | r) >>> 0;
    }
    return (COLS[key] = v);
  }
  function num(el, name, dflt) { var v = parseFloat(el.getAttribute(name)); return isNaN(v) ? dflt : v; }

  function Raster(ctx, w, h) {
    this.w = w; this.h = h;
    this.img = ctx.createImageData(w, h);
    this.px = new Uint32Array(this.img.data.buffer);
  }
  Raster.prototype.dot = function (x, y, c) {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.px[y * this.w + x] = c;
  };
  // a straight line one pixel wide (Bresenham), cut to the picture first; a dash pattern [on, off] carries on
  // along a path (st.n counts its pixels, including any cut off)
  Raster.prototype.line = function (x0, y0, x1, y1, c, dash, st) {
    var dx = x1 - x0, dy = y1 - y0, t0 = 0, t1 = 1, steps = Math.max(Math.abs(dx), Math.abs(dy));
    var lim = [[-dx, x0 + 0.5], [dx, this.w - 0.5 - x0], [-dy, y0 + 0.5], [dy, this.h - 0.5 - y0]];
    for (var i = 0; i < 4; i++) {   // Liang-Barsky
      var p = lim[i][0], q = lim[i][1];
      if (p === 0) { if (q < 0) { st.n += Math.round(steps); return; } continue; }
      var t = q / p;
      if (p < 0) { if (t > t1) { st.n += Math.round(steps); return; } if (t > t0) t0 = t; }
      else { if (t < t0) { st.n += Math.round(steps); return; } if (t < t1) t1 = t; }
    }
    st.n += Math.round(steps * t0);
    var ax = Math.round(x0 + dx * t0), ay = Math.round(y0 + dy * t0), bx = Math.round(x0 + dx * t1), by = Math.round(y0 + dy * t1);
    var tail = Math.round(steps * (1 - t1));
    var ex = Math.abs(bx - ax), ey = -Math.abs(by - ay), sx = ax < bx ? 1 : -1, sy = ay < by ? 1 : -1, err = ex + ey;
    var period = dash ? dash[0] + dash[1] : 0;
    for (;;) {
      if (!dash || st.n % period < dash[0]) this.dot(ax, ay, c);
      if (ax === bx && ay === by) break;
      st.n++;
      var e2 = 2 * err;
      if (e2 >= ey) { err += ey; ax += sx; }
      if (e2 <= ex) { err += ex; ay += sy; }
    }
    st.n += tail;
  };
  Raster.prototype.span = function (y, xa, xb, c) {
    y = Math.round(y);
    if (y < 0 || y >= this.h) return;
    var a = Math.max(0, Math.round(xa)), b = Math.min(this.w - 1, Math.round(xb));
    if (b >= a) this.px.fill(c, y * this.w + a, y * this.w + b + 1);
  };
  Raster.prototype.fillPoly = function (pts, c) {   // even-odd, a row at a time
    var ys = pts.map(function (p) { return p[1]; });
    var top = Math.max(0, Math.ceil(Math.min.apply(null, ys))), bot = Math.min(this.h - 1, Math.floor(Math.max.apply(null, ys)));
    for (var y = top; y <= bot; y++) {
      var xs = [];
      for (var i = 0; i < pts.length; i++) {
        var a = pts[i], b = pts[(i + 1) % pts.length];
        if ((a[1] <= y) !== (b[1] <= y)) xs.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
      }
      xs.sort(function (p, q) { return p - q; });
      for (var k = 0; k + 1 < xs.length; k += 2) this.span(y, xs[k], xs[k + 1], c);
    }
  };
  Raster.prototype.poly = function (pts, c, dash, closed) {
    var st = { n: 0 }, n = pts.length;
    for (var i = 0; i + 1 < n; i++) this.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, dash, st);
    if (closed && n > 2) this.line(pts[n - 1][0], pts[n - 1][1], pts[0][0], pts[0][1], c, dash, st);
  };
  Raster.prototype.text35 = function (text, x, y, c) {   // the icons' 3 x 5 letters, centred on x, y
    var x0 = Math.round(x - (text.length * 4 - 1) / 2), y0 = Math.round(y - 2);
    for (var i = 0; i < text.length; i++) {
      var g = F35[text[i]] || F35[text[i].toUpperCase()];
      if (g) for (var k = 0; k < 15; k++) if (g[k] === "1") this.dot(x0 + i * 4 + k % 3, y0 + Math.floor(k / 3), c);
    }
  };
  Raster.prototype.text57 = function (text, x, y, c, bg, keep) {   // the names' 5 x 7 letters, centred (bg: on a dark band;
    if (!keep) text = text.toUpperCase();                         // keep: small letters stay small, where there's one)
    var w = text.length * 6 - 1, x0 = Math.round(x - w / 2), y0 = Math.round(y - 3.5);
    if (bg != null) for (var r = y0 - 1; r <= y0 + 7; r++) this.span(r, x0 - 1, x0 + w, bg);
    for (var i = 0; i < text.length; i++) {
      var g = F57[text[i]] || F57[text[i].toUpperCase()];
      if (!g) continue;
      for (var col = 0; col < 5; col++) for (var row = 0; row < 7; row++) if (g[col] >> row & 1) this.dot(x0 + i * 6 + col, y0 + row, c);
    }
  };

  // the SVG's drawing, through its groups' transforms (translate and scale only), onto the raster;
  // m = [scale, x offset, y offset] from the drawing's units to the raster's pixels
  function paint(r, node, m, alpha) {
    for (var el = node.firstElementChild; el; el = el.nextElementSibling) {
      var tag = el.tagName.toLowerCase(), a = alpha * num(el, "opacity", 1);
      if (a <= 0) continue;
      if (tag === "g") {
        var mm = m.slice(), re = /(translate|scale)\(([^)]*)\)/g, t;
        while ((t = re.exec(el.getAttribute("transform") || ""))) {
          var v = t[2].trim().split(/[\s,]+/).map(parseFloat);
          if (t[1] === "translate") { mm[1] += mm[0] * (v[0] || 0); mm[2] += mm[0] * (v[1] || 0); }
          else mm[0] *= v[0] || 1;
        }
        paint(r, el, mm, a);
        continue;
      }
      var s = m[0], P = function (x, y) { return [m[1] + s * x, m[2] + s * y]; };
      var stroke = rgb(el.getAttribute("stroke"), a), fill = rgb(el.getAttribute("fill"), a * num(el, "fill-opacity", 1));
      var da = (el.getAttribute("stroke-dasharray") || "").trim().split(/[\s,]+/).map(parseFloat);
      // dashes are drawn as many of the picture's pixels long as they were meant to be screen pixels, so
      // they get coarser with the pixels rather than turning into dots
      var dq = s * r.dq, dash = da.length >= 2 && !isNaN(da[0]) ? [Math.max(1, Math.round(da[0] * dq)), Math.max(1, Math.round(da[1] * dq))] : null;
      if (tag === "path") {
        if (!stroke) continue;
        var tok = (el.getAttribute("d") || "").match(/[MLZ]|-?\d*\.?\d+(?:e-?\d+)?/gi) || [], st = { n: 0 }, start = null, cur = null;
        for (var k = 0; k < tok.length; k++) {
          var cmd = tok[k].toUpperCase();
          if (cmd === "M") { start = cur = P(+tok[k + 1], +tok[k + 2]); k += 2; st = { n: 0 }; }
          else if (cmd === "L") { var nx = P(+tok[k + 1], +tok[k + 2]); if (cur) r.line(cur[0], cur[1], nx[0], nx[1], stroke, dash, st); cur = nx; k += 2; }
          else if (cmd === "Z") { if (cur && start) r.line(cur[0], cur[1], start[0], start[1], stroke, dash, st); cur = start; }
        }
      } else if (tag === "circle") {
        var c = P(num(el, "cx", 0), num(el, "cy", 0)), rad = num(el, "r", 0) * s;
        if (fill) {
          for (var y = Math.max(0, Math.ceil(c[1] - rad)); y <= Math.min(r.h - 1, c[1] + rad); y++) {
            var hw = Math.sqrt(Math.max(0, rad * rad - (y - c[1]) * (y - c[1])));
            r.span(y, c[0] - hw, c[0] + hw, fill);
          }
          if (rad < 1.5) r.dot(Math.round(c[0]), Math.round(c[1]), fill);
        }
        if (stroke) {
          var n = Math.max(12, Math.min(720, Math.round(2 * Math.PI * rad / 2))), ring = [];
          for (var q = 0; q < n; q++) ring.push([c[0] + rad * Math.cos(q / n * 2 * Math.PI), c[1] + rad * Math.sin(q / n * 2 * Math.PI)]);
          r.poly(ring, stroke, dash, true);
        }
      } else if (tag === "rect") {
        var p0 = P(num(el, "x", 0), num(el, "y", 0)), w = num(el, "width", 0) * s, h = num(el, "height", 0) * s;
        if (fill) for (var yy = Math.round(p0[1]); yy < Math.round(p0[1] + h); yy++) r.span(yy, p0[0], p0[0] + w - 1, fill);
        if (stroke) r.poly([[p0[0], p0[1]], [p0[0] + w - 1, p0[1]], [p0[0] + w - 1, p0[1] + h - 1], [p0[0], p0[1] + h - 1]], stroke, dash, true);
      } else if (tag === "polygon") {
        var nums = (el.getAttribute("points") || "").trim().split(/[\s,]+/).map(parseFloat), poly = [];
        for (var z = 0; z + 1 < nums.length; z += 2) poly.push(P(nums[z], nums[z + 1]));
        if (fill) r.fillPoly(poly, fill);
        if (stroke) r.poly(poly, stroke, dash, true);
      } else if (tag === "text") {
        var at = P(num(el, "x", 0), num(el, "y", 0)), col = fill, text = el.textContent || "";
        if (col == null || !text) continue;
        var shape = el.getAttribute("data-icon");
        if (shape === "ring") {   // a combat-zone point: its letter in a ring
          var rr = Math.max(Math.max(1, text.length) * 4 + 4, 9) / 2 + 0.5, cx0 = Math.round(at[0]), cy0 = Math.round(at[1]);
          for (var ry = Math.ceil(cy0 - rr); ry <= Math.floor(cy0 + rr); ry++) {
            var dx = Math.sqrt(Math.max(0, rr * rr - (ry - cy0) * (ry - cy0)));
            r.span(ry, Math.round(cx0 - dx), Math.round(cx0 + dx), rgb("#060606"));
          }
          var circ = [];
          for (var qa = 0; qa < 24; qa++) circ.push([cx0 + rr * Math.cos(qa / 24 * 2 * Math.PI), cy0 + rr * Math.sin(qa / 24 * 2 * Math.PI)]);
          r.poly(circ, col, null, true);
          r.text35(text, at[0] + 0.5, at[1], col);
        } else if (shape) {   // an icon: a small box - rounded, square or broken - with its 3 x 5 letters
          var bw = Math.max(1, text.length) * 4 + 4, bh = 9, bx = Math.round(at[0] - bw / 2), by = Math.round(at[1] - bh / 2);
          for (var fy = by; fy < by + bh; fy++) r.span(fy, bx, bx + bw - 1, rgb("#060606"));
          var R = bx + bw - 1, B = by + bh - 1;
          var outline = shape === "box" ? [[bx, by], [R, by], [R, B], [bx, B]]
            : [[bx + 2, by], [R - 2, by], [R, by + 2], [R, B - 2], [R - 2, B], [bx + 2, B], [bx, B - 2], [bx, by + 2]];
          r.poly(outline, col, shape === "dash" ? [2, 1] : null, true);
          r.text35(text, at[0] + 0.5, at[1], col);
        } else {
          r.text57(text, at[0], at[1], col, el.getAttribute("data-band") ? rgb("#060606") : null, el.getAttribute("data-case") === "keep");
        }
      }
    }
  }

  var RASTERS = new WeakMap();
  // draw the SVG (showing vb of its drawing) on the canvas laid over it, which sits in the same box
  function draw(svg, cv, vb) {
    var cw = svg.clientWidth, ch = svg.clientHeight;
    if (!cw || !ch) return;
    var gr = grain(), W = Math.max(1, Math.floor(cw * gr.dpr / gr.dev)), H = Math.max(1, Math.floor(ch * gr.dpr / gr.dev));
    var ctx = cv.getContext("2d"), r = RASTERS.get(cv);
    if (!r || r.w !== W || r.h !== H || r.dev !== gr.dev) {
      cv.width = W; cv.height = H;
      var cssW = W * gr.dev / gr.dpr, cssH = H * gr.dev / gr.dpr;
      cv.style.width = cssW + "px"; cv.style.height = cssH + "px";
      cv.style.left = Math.round((cw - cssW) / 2 * gr.dpr) / gr.dpr + "px";
      cv.style.top = Math.round((ch - cssH) / 2 * gr.dpr) / gr.dpr + "px";
      r = new Raster(ctx, W, H);
      r.dev = gr.dev;
      r.dq = gr.dev / gr.dpr;   // CSS pixels in one of the picture's
      RASTERS.set(cv, r);
    }
    r.px.fill(0);
    // the picture's units -> raster pixels: the same scale both ways (the SVG keeps its shape), centred
    var k = Math.min(cw / vb.w, ch / vb.h) * gr.dpr / gr.dev;
    var offX = (W - vb.w * k) / 2 - vb.x * k, offY = (H - vb.h * k) / 2 - vb.y * k;
    paint(r, svg, [k, offX, offY], 1);
    ctx.putImageData(r.img, 0, 0);
  }

  // ---- the canvases (the system map, the hyperspace screens) at the same coarse pixels ----
  // A drawing in two layers: lines and shapes on the canvas itself, which has one of its pixels per
  // coarse pixel and is shown scaled up with no smoothing; the writing on a full-resolution canvas laid
  // over it, so names stay as clear as the rest of the page's text. The drawing code uses the result as
  // it would a 2D context, in CSS pixels (setTransform included). Lines are at least one coarse pixel
  // wide, and dashes count their length in coarse pixels, so they get coarser rather than turning to dots.
  var BOTH = ["beginPath", "closePath", "moveTo", "lineTo", "arc", "arcTo", "rect", "ellipse", "quadraticCurveTo",
              "bezierCurveTo", "translate", "scale", "rotate", "transform", "clip"];
  var STYLE = ["strokeStyle", "fillStyle", "globalAlpha", "lineJoin", "lineCap", "shadowColor", "globalCompositeOperation",
               "font", "textAlign", "textBaseline"];
  function Layers(lo, tx, kl, kt) {
    this.lo = lo; this.tx = tx; this.kl = kl; this.kt = kt;
    this._lw = 1; this._dash = []; this._off = 0; this._sb = 0; this._stack = [];
  }
  BOTH.forEach(function (m) {
    Layers.prototype[m] = function () { this.lo[m].apply(this.lo, arguments); if (this.tx) this.tx[m].apply(this.tx, arguments); };
  });
  STYLE.forEach(function (p) {
    Object.defineProperty(Layers.prototype, p, {
      get: function () { return this.lo[p]; },
      set: function (v) { this.lo[p] = v; if (this.tx) this.tx[p] = v; }
    });
  });
  Object.defineProperty(Layers.prototype, "lineWidth", { get: function () { return this._lw; }, set: function (v) { this._lw = v; } });
  Object.defineProperty(Layers.prototype, "lineDashOffset", { get: function () { return this._off; }, set: function (v) { this._off = v; } });
  Object.defineProperty(Layers.prototype, "shadowBlur", {   // in CSS pixels
    get: function () { return this._sb; },
    set: function (v) { this._sb = v; this.lo.shadowBlur = v * this.kl; if (this.tx) this.tx.shadowBlur = v * this.kt; }
  });
  Layers.prototype.setLineDash = function (d) { this._dash = (d || []).slice(); if (this.tx) this.tx.setLineDash(d || []); };
  Layers.prototype.getLineDash = function () { return this._dash.slice(); };
  Layers.prototype.save = function () { this._stack.push([this._lw, this._dash, this._off, this._sb]); this.lo.save(); if (this.tx) this.tx.save(); };
  Layers.prototype.restore = function () {
    var s = this._stack.pop();
    if (s) { this._lw = s[0]; this._dash = s[1]; this._off = s[2]; this._sb = s[3]; }
    this.lo.restore(); if (this.tx) this.tx.restore();
  };
  Layers.prototype.setTransform = function (a, b, c, d, e, f) {   // CSS pixels -> each layer's own
    var k = this.kl, t = this.kt;
    this.lo.setTransform(a * k, b * k, c * k, d * k, e * k, f * k);
    if (this.tx) this.tx.setTransform(a * t, b * t, c * t, d * t, e * t, f * t);
  };
  Layers.prototype.resetTransform = function () { this.setTransform(1, 0, 0, 1, 0, 0); };
  Layers.prototype.stroke = function () {
    var m = this.lo.getTransform(), s = Math.hypot(m.a, m.b) || 1, kl = this.kl;
    this.lo.lineWidth = Math.max(this._lw, 1 / s);   // at least a pixel
    this.lo.setLineDash(this._dash.map(function (v) { return v / kl; }));
    this.lo.lineDashOffset = this._off / kl;
    this.lo.stroke();
  };
  Layers.prototype.fill = function () { this.lo.fill.apply(this.lo, arguments); };
  Layers.prototype.fillRect = function (x, y, w, h) { this.lo.fillRect(x, y, w, h); };
  Layers.prototype.strokeRect = function (x, y, w, h) { this.lo.beginPath(); this.lo.rect(x, y, w, h); this.stroke(); };
  Layers.prototype.clearRect = function (x, y, w, h) { this.lo.clearRect(x, y, w, h); if (this.tx) this.tx.clearRect(x, y, w, h); };
  Layers.prototype.fillText = function (s, x, y, mw) { if (this.tx) { if (mw === undefined) this.tx.fillText(s, x, y); else this.tx.fillText(s, x, y, mw); } };
  Layers.prototype.strokeText = function (s, x, y) { if (this.tx) this.tx.strokeText(s, x, y); };
  Layers.prototype.measureText = function (s) { return (this.tx || this.lo).measureText(s); };
  // a small square bitmap (rows of '#' lit / '.' not) centred on (x, y), each of its pixels a whole number of
  // coarse pixels - as many as fit in `fit` (current units), at least one - so it stays crisp at any zoom.
  // Says how big it came out and how big one coarse pixel is (current units); dry: only says.
  Layers.prototype.bitmap = function (rows, x, y, fit, dry) {
    var m = this.lo.getTransform(), s = Math.hypot(m.a, m.b) || 1, n = rows.length, px = Math.max(1, Math.floor(fit * s / n));
    if (!dry) {
      var lo = this.lo, x0 = Math.round(m.a * x + m.c * y + m.e - n * px / 2), y0 = Math.round(m.b * x + m.d * y + m.f - n * px / 2);
      lo.save(); lo.setTransform(1, 0, 0, 1, 0, 0);
      rows.forEach(function (r, j) {
        var re = /#+/g, k;
        while ((k = re.exec(r))) lo.fillRect(x0 + k.index * px, y0 + j * px, k[0].length * px, px);
      });
      lo.restore();
    }
    return { size: n * px / s, unit: 1 / s };
  };
  // the frame's done: the lines' soft edges (the canvas smooths them) made hard, so each coarse pixel is
  // either lit or not, as on the rest of the screen; faint touches drop out, solid ones stay
  var CRISP = new Uint8Array(256);
  for (var ci = 0; ci < 256; ci++) CRISP[ci] = ci < 56 ? 0 : Math.min(255, Math.round((ci - 56) * 2.4 + 70));
  Layers.prototype.finish = function () {
    var cv = this.lo.canvas, w = cv.width, h = cv.height;
    if (!w || !h) return;
    this.lo.save();
    this.lo.setTransform(1, 0, 0, 1, 0, 0);
    var img = this.lo.getImageData(0, 0, w, h), d = img.data;
    for (var i = 3; i < d.length; i += 4) d[i] = CRISP[d[i]];
    this.lo.putImageData(img, 0, 0);
    this.lo.restore();
  };
  Layers.prototype.createLinearGradient = function () { return this.lo.createLinearGradient.apply(this.lo, arguments); };
  Layers.prototype.createRadialGradient = function () { return this.lo.createRadialGradient.apply(this.lo, arguments); };

  // the layers for a canvas that fills its box (w x h CSS pixels); its writing layer is made beside it the
  // first time (text: false for a canvas with no writing)
  function layers(cv, w, h, text) {
    var gr = grain(), g = gr.dev / gr.dpr;   // CSS pixels in one coarse pixel
    var lw = Math.max(1, Math.round(w / g)), lh = Math.max(1, Math.round(h / g));
    if (cv.width !== lw || cv.height !== lh) { cv.width = lw; cv.height = lh; }
    cv.classList.add("pxcv");
    var tctx = null;
    if (text !== false) {
      var tx = cv._tx;
      if (!tx) {
        tx = cv._tx = document.createElement("canvas");
        tx.className = "pxtx";
        tx.setAttribute("aria-hidden", "true");
        cv.getContext("2d", { willReadFrequently: true });   // read back every frame (finish)
        cv.parentNode.insertBefore(tx, cv.nextSibling);
      }
      var dpr = Math.min(2, window.devicePixelRatio || 1), tw = Math.round(w * dpr), th = Math.round(h * dpr);
      if (tx.width !== tw || tx.height !== th) { tx.width = tw; tx.height = th; }
      tctx = tx.getContext("2d");
      tctx.setTransform(1, 0, 0, 1, 0, 0); tctx.clearRect(0, 0, tw, th);
      var L = new Layers(cv.getContext("2d"), tctx, lw / w, dpr);
      return L;
    }
    return new Layers(cv.getContext("2d"), null, lw / w, 1);
  }

  ED.pixel = { draw: draw, layers: layers };
})();
