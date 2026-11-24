// ED Target Board page - Overlay: the terminal itself (UCEC FT3000: power-on, boot screen, waiting for
// a signal) and changing vehicle (disconnect / start-up and each vehicle's boot screen).
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- changing vehicle: leaving one "disconnects" (randomised static, then the tube
  //      switches off); arriving starts up (warm-up static, then that vehicle's boot
  //      screen - on foot, the static alone) ----
  // on: an effect is showing; seq: it's the terminal's own (power-on / no signal), not a change of vehicle;
  // hold: a preview of the no-signal screen, which the game coming back doesn't end
  var BOOT = { on: false, seq: false, hold: false, phase: "", raf: 0, timers: [] };
  var VEHICLES = { ship: 1, srv: 1, nomad: 1, fighter: 1 };
  var TINT = { green: [0.27, 0.94, 0.54], mint: [0.54, 1, 0.76], amber: [0.89, 0.64, 0.29], lime: [0.62, 0.86, 0.32] };
  function later(ms, fn) { BOOT.timers.push(setTimeout(fn, ms)); }
  function pick(a) { return a[(Math.random() * a.length) | 0]; }
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function rep0(ch, n) { return n > 0 ? new Array(n + 1).join(ch) : ""; }
  function fit(t, n) { t = String(t); return t.length > n ? t.slice(0, Math.max(0, n - 1)) + "\u2026" : t + rep0(" ", n - t.length); }

  // static is drawn small and scaled up (cheap on a phone); gain(y) gives each row's
  // brightness, or -1 to leave the row see-through
  function noiseCanvas(scale) {
    var cv = $("bt-noise");
    var w = Math.max(60, Math.round(window.innerWidth / scale)), h = Math.max(40, Math.round(window.innerHeight / scale));
    cv.width = w; cv.height = h;
    cv.style.transition = ""; cv.style.transform = ""; cv.style.opacity = "1";
    var ctx = cv.getContext("2d"), img = ctx.createImageData(w, h), px = new Uint32Array(img.data.buffer);
    return { w: w, h: h, cv: cv, draw: function (gain, tint) {
      for (var y = 0; y < h; y++) {
        var k = gain(y), i = y * w, end = i + w;
        if (k < 0) { for (; i < end; i++) px[i] = 0; continue; }
        for (; i < end; i++) {
          var v = Math.min(255, Math.random() * 255 * k);
          px[i] = 0xff000000 | ((v * tint[2]) << 16) | ((v * tint[1]) << 8) | (v * tint[0]);
        }
      }
      ctx.putImageData(img, 0, 0);
    } };
  }

  function playTransition(tr) {
    if (BOOT.on || S.halted) return;
    var from = VEHICLES[tr.from] ? tr.from : "", to = tr.to || "ship";
    BOOT.on = true;
    BOOT.timers = [];
    var box = $("boot");
    box.className = "";
    box.hidden = false;
    $("bt-text").innerHTML = ""; $("bt-text").className = "";
    $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
    if (reduce.matches) {   // no static or flicker: a vehicle's boot screen, briefly; nothing on foot
      if (!VEHICLES[to]) { box.hidden = true; BOOT.on = false; return; }
      BOOT.phase = "boot";
      box.classList.add("sig");
      bootScreen(to, tr.label, true);
      later(3000, endBoot);
      return;
    }
    if (from) disconnect(function () { startup(to, tr.label); }, false);   // changing vehicle: just the signal lost
    else startup(to, tr.label);
  }

  // the signal lost: the picture tears into static and the signal fades - leaving a vehicle (then straight
  // on to the next one's start-up) - and, off: true, the tube then switches off, shrinking to a dot (back to
  // the game's main menu, or the game closed). Different every time: grain, tint, rolling bars, tearing,
  // frame roll and length are random.
  function disconnect(done, off) {
    var box = $("boot"), app = $("app");
    var D = rnd(1700, 2500), tint = pick([TINT.green, TINT.mint, TINT.lime]);
    var n = noiseCanvas(pick([2, 3, 4, 5])), bands = [], nb = 1 + ((Math.random() * 3) | 0);
    for (var j = 0; j < nb; j++) {
      bands.push({ speed: rnd(0.5, 2.2) * (Math.random() < 0.35 ? -1 : 1), size: rnd(0.05, 0.2), off: Math.random() });
    }
    var tearP = rnd(0.02, 0.09), roll = Math.random() < 0.6 ? rnd(0.5, 1.6) : 0, t0 = performance.now();
    var tube = off ? 0.78 : 1;   // when the tube switches off (never, for a vehicle)
    box.classList.add("thru");      // the page shows through while it breaks up
    app.classList.add("glitch");
    BOOT.phase = "disconnect";
    function inBand(y, sec, grow) {
      for (var b = 0; b < bands.length; b++) {
        var c = ((bands[b].off + sec * bands[b].speed) % 1 + 1) % 1 * n.h;
        if (Math.abs(y - c) < bands[b].size * grow * n.h) return true;
      }
      return false;
    }
    function frame(now) {
      if (BOOT.phase !== "disconnect") return;
      var t = now - t0, p = t / D, sec = t / 1000;
      if (p >= 1) {   // black for a moment, then the next start-up
        n.cv.style.opacity = "0";
        later(rnd(250, 550), done);
        return;
      }
      if (p < 0.35) {          // breaking up: bars of static tear across the page, growing
        var grow = 0.4 + p / 0.35 * 1.6, cover = p / 0.35 * 0.35;
        n.draw(function (y) { return inBand(y, sec, grow) || Math.random() < cover ? rnd(0.6, 1.35) : -1; }, tint);
      } else if (p < tube) {   // all static now, the signal fading; a dark frame bar rolls through
        if (box.classList.contains("thru")) { box.classList.remove("thru"); app.classList.remove("glitch"); }
        var fade = 1.1 - 0.6 * (p - 0.35) / (tube - 0.35), gap = roll ? ((sec * roll) % 1) * n.h : -99;
        n.draw(function (y) {
          if (Math.abs(y - gap) < n.h * 0.05) return 0.06;
          return fade * (inBand(y, sec, 1) ? 1.5 : 0.75) * (Math.random() < tearP ? 2 : 1);
        }, tint);
        n.cv.style.transform = Math.random() < 0.06 ? "translateX(" + rnd(-3, 3).toFixed(1) + "%)" : "";
      } else {                 // the tube switches off: down to a bright line, then a dot, then gone
        var r = (p - 0.78) / 0.22;
        n.draw(function () { return 1.3; }, tint);
        var sy = r < 0.5 ? Math.max(0.004, 1 - r / 0.5) : 0.004;
        var sx = r < 0.5 ? 1 : Math.max(0.01, 1 - (r - 0.5) / 0.35);
        n.cv.style.transform = "scale(" + sx.toFixed(3) + "," + sy.toFixed(3) + ")";
        n.cv.style.opacity = r > 0.88 ? String(Math.max(0, 1 - (r - 0.88) / 0.12)) : "1";
      }
      BOOT.raf = requestAnimationFrame(frame);
    }
    BOOT.raf = requestAnimationFrame(frame);
  }

  // arriving: the signal comes in - static that brightens over 3 s, rolling and slipping, then the picture locks
  function startup(to, label) {
    var n = noiseCanvas(3), t0 = performance.now();
    var tint = to === "srv" ? TINT.amber : to === "nomad" ? TINT.mint : TINT.green;   // matches its boot screen
    BOOT.phase = "static";
    function frame(now) {
      if (BOOT.phase !== "static") return;
      var t = now - t0;
      if (t >= 3000) { signal(to, label); return; }
      var p = t / 3000;   // the tube is on already (it only switches off when you leave the game): the signal comes in
      var bright = (0.06 + 0.94 * p * p) * (0.88 + Math.random() * 0.24);   // slow rise, with flicker
      var band = (t % 1150) / 1150 * n.h * 1.5 - n.h * 0.25, bandH = n.h * 0.16;   // one rolling bar
      n.draw(function (y) {
        return bright * (Math.abs(y - band) < bandH ? 1.6 : 0.78) * (Math.random() < 0.015 ? 1.9 : 1);
      }, tint);
      var slip = Math.random() < 0.04 ? " translateY(" + ((Math.random() - 0.5) * 8).toFixed(1) + "%)" : "";
      n.cv.style.transform = slip;
      BOOT.raf = requestAnimationFrame(frame);
    }
    BOOT.raf = requestAnimationFrame(frame);
  }

  function flash() {   // the picture locking in
    var fl = $("bt-flash");
    fl.style.transition = "none";
    fl.style.opacity = "0.9";
    void fl.offsetWidth;
    fl.style.transition = "";
    later(60, function () { fl.style.opacity = "0"; });
  }
  function signal(to, label) {   // the picture locks: a flash and a jolt
    BOOT.phase = "boot";
    flash();
    if (!VEHICLES[to]) { later(120, endBoot); return; }   // on foot: the static is the whole start-up
    $("boot").classList.add("sig");
    ED.replay($("bt-text"), "lockin");
    bootScreen(to, label, false);
  }

  // ---- boot screens: each vehicle's computer comes from a different maker ----
  function bootScreen(kind, label, instant) {
    var el = $("bt-text");
    ufcFx(VEHICLES[kind] ? kind : "");
    el.className = "bt-" + kind;
    var k = bootKit(el, instant);
    ({ ship: bootShip, srv: bootSrv, fighter: bootFighter, nomad: bootNomad }[kind] || bootShip)(k, label);
    if (!instant) later(4550, endBoot);   // fades over the last half second: 5 s from the signal
  }

  function bootKit(el, instant) {
    var probe = document.createElement("span");   // characters per line, so layouts fit any screen
    probe.textContent = "0000000000";
    el.appendChild(probe);
    var cw = probe.getBoundingClientRect().width / 10 || 12, phase = BOOT.phase;
    el.removeChild(probe);
    var cs = getComputedStyle(el), s = S.data || {};
    var k = {
      instant: instant, s: s, c: s.cmdr || {}, year: new Date().getUTCFullYear() + 1286, cw: cw,
      cols: Math.max(20, Math.floor((el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) / cw)),
      at: function (ms, fn) { if (instant) fn(); else later(ms, fn); },
      row: function (html, cls) {
        var d = document.createElement("div");
        if (cls) d.className = cls;
        d.innerHTML = html;
        el.appendChild(d);
        return d;
      },
      anim: function (dur, fn) {   // fn(0..1) every frame for dur ms
        if (instant) { fn(1); return; }
        var t0 = performance.now();
        (function step() {
          if (BOOT.phase !== phase) return;   // the screen has moved on
          var f = Math.min(1, (performance.now() - t0) / dur);
          fn(f);
          if (f < 1) BOOT.raf = requestAnimationFrame(step);
        })();
      },
      reveal: function (row, ms) {   // the last part of a row (its result) appears a beat later
        var v = row.lastElementChild;
        if (instant || !v) return;
        v.style.visibility = "hidden";
        later(ms || 110, function () { v.style.visibility = ""; });
      },
      lead: function (label, value, cls, ch) {   // LABEL ........ VALUE, flush to the right edge
        var gap = k.cols - label.length - String(value).length - 2;
        var dots = gap >= 3 ? " " + rep0(ch || ".", gap) + " " : " ";
        return ED.esc(label) + '<span class="dim">' + dots + '</span><span class="' + (cls || "hi") + '">' + ED.esc(value) + "</span>";
      }
    };
    k.vessel = [k.c.ship, k.c.ship_ident].filter(Boolean).join(" \u00b7 ") || "Unknown";
    k.where = [s.system, s.body && s.body !== s.system ? String(s.body).replace(s.system + " ", "") : ""].filter(Boolean).join(" \u00b7 ") || "Unknown";
    k.cmdr = k.c.name || s.commander || "Unknown";
    k.contracts = (s.contracts || []).length;
    return k;
  }

  // Each screen reserves its lines in order first (empty lines take no space), then fills
  // them in on cue, so lines that animate stay in their place.

  // Ship: Case File OS - the board's own system. Green, dotted leaders, the commander's mark.
  function bootShip(k) {
    var b = k.s.ocor || {}, n = k.contracts;
    var old = !!b.pasted && Date.now() - Date.parse(b.pasted) > ED.STALE_MS;
    var checks = [
      ["Signal", "Locked"], ["Baseline", "Nominal"], ["Cmdr", k.cmdr], ["Vessel", k.vessel],
      ["Position", k.s.system || "Unknown"],
      ["Contracts", n ? n + " active" : "None", n ? "am" : "hi"],
      ["OCOR brief", !(b.pasted && (b.objectives || []).length) ? "None"
        : Date.now() - Date.parse(b.pasted) < 6e4 ? "Just fetched" : ED.sinceTxt(b.pasted, true) + " old", old ? "bad" : "hi"]
    ];
    k.row('<span class="hi">Case File OS 2.049</span>');
    k.row('<span class="dim">(c) ' + k.year + " Pilots Federation data net</span>");
    var mem = k.row(""), lines = checks.map(function () { return k.row(""); }), bar = k.row(""), prompt = k.row("");
    k.at(250, function () {
      k.anim(600, function (f) {
        mem.innerHTML = "Memory test " + Math.round(f * 65536) + "K" + (f >= 1 ? ' <span class="hi">OK</span>' : "");
      });
    });
    k.at(1580, function () {   // the commander's ID mark resolves as the CMDR line reads in
      $("bt-sig").innerHTML = ED.sigil(k.cmdr);
      ED.replay($("bt-sig"), "flk");
    });
    checks.forEach(function (ck, i) {
      k.at(1000 + i * 290, function () { lines[i].innerHTML = k.lead(ck[0], ck[1], ck[2]); k.reveal(lines[i]); });
    });
    k.at(3100, function () {
      k.anim(800, function (f) {
        var on = Math.round(f * 12);
        bar.innerHTML = 'Loading case files <span class="hi">' + rep0("\u2588", on) + '</span><span class="dim">' + rep0("\u2591", 12 - on) + "</span>";
      });
    });
    k.at(4000, function () {
      prompt.innerHTML = 'C:\\ED&gt; <span class="pt"></span><span class="blink">_</span>';
      var pt = prompt.querySelector(".pt"), cmd = "casefile", i = 0;
      if (k.instant) { pt.textContent = cmd; return; }
      (function type() { pt.textContent = cmd.slice(0, ++i); if (i < cmd.length) later(45, type); })();
    });
  }

  // SRV: Surface Recon Systems RoverBIOS - an amber terminal, a framed summary, a badge.
  function bootSrv(k, label) {
    var sig = $("bt-sig");
    sig.className = "logo srv";
    sig.textContent = "\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\n\u2588 \u25b2 SRS  \u2588\n\u2580\u2580\u2580\u2580\u2580\u2580\u2580\u2580\u2580\u2580";
    k.row('<span class="hi">Surface Recon Systems</span>');
    k.row("RoverBIOS R7.12  (c) " + k.year + " SRS Inc.");
    var bw = Math.min(k.cols, 42), inner = bw - 4;
    var info = [["Unit", label || "SRV"], ["Carrier", k.vessel], ["Surface", k.where], ["Cmdr", k.cmdr]];
    var det = k.row(""), mem = k.row(""), top = k.row(""), box = info.map(function () { return k.row(""); });
    var bottom = k.row(""), ver = k.row(""), setup = k.row("");
    k.at(200, function () {
      k.anim(500, function (f) {
        det.innerHTML = "Detecting drive units" + rep0(".", Math.round(f * 6)) + (f >= 1 ? ' <span class="hi">OK</span>' : "");
      });
    });
    k.at(800, function () {
      k.anim(550, function (f) {
        mem.innerHTML = "Memory Test : " + Math.round(f * 32768) + "K" + (f >= 1 ? ' <span class="hi">OK</span>' : "");
      });
    });
    k.at(1500, function () { top.textContent = "\u2554" + rep0("\u2550", bw - 2) + "\u2557"; });
    info.forEach(function (r, i) {
      k.at(1650 + i * 220, function () {
        box[i].innerHTML = "\u2551 " + '<span class="dim">' + ED.esc(fit(r[0], 9)) + '</span><span class="hi">' + ED.esc(fit(r[1], inner - 9)) + "</span> \u2551";
      });
    });
    k.at(1650 + info.length * 220, function () { bottom.textContent = "\u255a" + rep0("\u2550", bw - 2) + "\u255d"; });
    k.at(2800, function () {
      k.anim(500, function (f) {
        ver.innerHTML = "Verifying terrain mesh" + rep0(".", Math.round(f * 6)) + (f >= 1 ? ' <span class="hi">Update Success</span>' : "");
      });
    });
    k.at(3600, function () { setup.innerHTML = 'Hold <span class="hi">BRAKE</span> to enter SETUP<span class="blink">_</span>'; });
  }

  // Fighter: Talon Avionics flight core - bright, terse, inverse-video bars, self-test grid.
  function bootFighter(k, label) {
    var w = k.cols, two = w >= 40, colw = two ? Math.floor(w / 2) : w;
    var tests = ["T01 PWR BUS", "T02 THRUST", "T03 GIMBAL", "T04 WEAPONS", "T05 SHIELDS", "T06 SENSORS"];
    var grid = [];
    for (var i = 0; i < tests.length; i += two ? 2 : 1) grid.push(two ? [tests[i], tests[i + 1]] : [tests[i]]);
    k.row(ED.esc(fit(" TALON AVIONICS \u2261 FLIGHT CORE POST 3.3", w)), "inv");
    var hex = k.row(""), rows = grid.map(function () { return k.row(""); });
    var up = k.row(""), tp = k.row(""), lo = k.row(""), tg = k.row(""), go = k.row("");
    k.at(150, function () {
      k.anim(550, function (f) {
        var a = ("00000000" + Math.round(f * 0x3ffff).toString(16).toUpperCase()).slice(-8);
        hex.innerHTML = "CORE SCAN 0x" + a + (f >= 1 ? ' <span class="hi">PASS</span>' : "");
      });
    });
    grid.forEach(function (g, i) {
      k.at(800 + i * (two ? 300 : 160), function () {
        rows[i].innerHTML = g.map(function (t) { return ED.esc(fit(t, colw - 6)) + '<span class="hi">PASS</span>'; }).join("  ");
        k.reveal(rows[i], 90);
      });
    });
    k.at(1900, function () { up.innerHTML = 'UPLINK    <span class="dim">\u25ba</span> <span class="hi">' + ED.esc(k.vessel) + "</span>"; });
    k.at(2150, function () {
      k.anim(1000, function (f) {
        var on = Math.round(f * 12);
        tp.innerHTML = "TELEPRESENCE " + '<span class="hi">' + rep0("\u2588", on) + '</span><span class="dim">' + rep0("\u2591", 12 - on) + "</span> " +
          (f >= 1 ? '<span class="hi">SYNC</span>' : Math.round(f * 100) + "%");
      });
    });
    k.at(3250, function () { lo.innerHTML = 'LOADOUT   <span class="hi">' + ED.esc(label || "Standard") + "</span>"; });
    k.at(3450, function () {
      var n = k.contracts;
      tg.innerHTML = 'CONTRACTS <span class="' + (n ? "am" : "hi") + '">' + (n ? n + " ACTIVE" : "NONE") + "</span>";
    });
    k.at(3750, function () { go.className = "inv blink"; go.textContent = fit(" \u25ba LAUNCH CLEARANCE GRANTED", w); });
  }

  // Nomad: Faulcon DeLacy - quiet and centred, a terrain trace scrolling under the masthead.
  function bootNomad(k, label) {
    var w = Math.min(k.cols - 2, 40);
    function spaced(t) { return t.split("").join(" "); }
    k.row('<span class="hi">' + ED.esc(spaced("FAULCON DELACY")) + "</span>");
    k.row('<span class="dim">' + ED.esc(spaced((label || "Nomad").toUpperCase())) + " \u00b7 " + ED.esc(spaced("SLV")) + "</span>");
    var info = [["Discovery scanner Mk II", "Online"], ["Surface", k.where], ["Mothership", k.vessel], ["Cmdr", k.cmdr]];
    var rule = k.row(""), top = k.row(""), low = k.row(""), lines = info.map(function () { return k.row(""); });
    var bio = k.row(""), ready = k.row("");
    k.at(250, function () {
      k.anim(600, function (f) { rule.innerHTML = '<span class="am">' + rep0("\u2500", Math.round(f * w)) + "</span>"; });
    });
    // a strip of terrain drawn in half-blocks, scrolling past like a ground scan
    var hts = [], hgt = 2;
    function step() { hgt = Math.max(1, Math.min(4, hgt + (Math.random() < 0.5 ? -1 : 1) * (Math.random() < 0.6 ? 1 : 0))); hts.push(hgt); }
    for (var i = 0; i < w; i++) step();
    function drawTerrain() {
      top.innerHTML = '<span class="dim">' + hts.map(function (v) { return v >= 4 ? "\u2588" : v === 3 ? "\u2584" : " "; }).join("") + "</span>";
      low.innerHTML = '<span class="dim">' + hts.map(function (v) { return v >= 2 ? "\u2588" : "\u2584"; }).join("") + "</span>";
    }
    k.at(950, function () {
      drawTerrain();
      if (k.instant) return;
      (function scroll() {
        if (BOOT.phase !== "boot") return;
        hts.shift(); step(); drawTerrain();
        later(85, scroll);
      })();
    });
    info.forEach(function (r, i) {
      k.at(1500 + i * 300, function () {
        lines[i].innerHTML = '<span class="dim">' + ED.esc(r[0]) + "</span>  " + '<span class="hi">' + ED.esc(r[1]) + "</span>";
        k.reveal(lines[i], 140);
      });
    });
    k.at(2800, function () {
      k.anim(900, function (f) {
        var on = Math.min(5, Math.floor(f * 6));
        bio.innerHTML = '<span class="dim">Bio sensors</span>  <span class="hi">' + rep0("\u25a0", on) + "</span>" +
          '<span class="dim">' + rep0("\u25a1", 5 - on) + "</span>" + (f >= 1 ? ' <span class="hi">Ready</span>' : "");
      });
    });
    k.at(3800, function () { ready.className = "blink"; ready.innerHTML = '<span class="hi">\u25c4 Ready for surface operations \u25ba</span>'; });
  }

  // ---- the terminal itself: the UCEC FT3000 ----
  // Opening the page powers it on: black for 2 s, the tube warms up (static, judders), the UCEC
  // boot screen, then - with no game to show - light static under WAITING FOR INPUT SIGNAL until
  // you're in, when it snaps to that vehicle's start-up. In the game already: straight to it.
  // Losing the game later (main menu, closed) breaks the picture up into static and waits again.
  // A tap (or Esc) skips to the board.
  var COL = null;   // the palette, from the CSS
  function palette() {
    var cs = getComputedStyle(document.documentElement), c = {};
    ["text", "hi", "muted", "track"].forEach(function (k) { c[k] = cs.getPropertyValue("--" + k).trim(); });
    return c;
  }

  // The UCEC logo: the Milky Way as a dot-matrix picture - a barred spiral seen tilted, its two
  // main arms leaving the ends of the bar, two fainter ones between. Each dot's brightness is
  // 0 (unlit) to 3, or -1 outside the galaxy. The same every time: it's a logo.
  var LOGO = { cols: 64, rows: 30, pitch: 5, dots: null };
  function galaxyDots(cols, rows) {
    var seed = 3312;
    function rand() { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; }
    var bar = -0.5, wind = 1 / Math.tan(20 * Math.PI / 180), out = [];   // the arms open out at about 20 degrees
    var arms = [[0, 1], [Math.PI, 1], [Math.PI / 2, 0.6], [Math.PI * 1.5, 0.6]];
    for (var gy = 0; gy < rows; gy++) {
      var line = [];
      for (var gx = 0; gx < cols; gx++) {
        var x = (gx - (cols - 1) / 2) / ((cols - 1) / 2), y = (gy - (rows - 1) / 2) / ((rows - 1) / 2);
        var r = Math.sqrt(x * x + y * y), th = Math.atan2(y, x), clump = rand();
        if (r > 1.04) { line.push(-1); continue; }
        var d = 2.0 * Math.exp(-r * r / 0.016);                                 // the bulge
        var bx = x * Math.cos(bar) + y * Math.sin(bar), by = -x * Math.sin(bar) + y * Math.cos(bar);
        d += 1.3 * Math.exp(-bx * bx / 0.06 - by * by / 0.006);                 // the bar
        if (r > 0.15) {
          arms.forEach(function (a) {
            var ta = bar + a[0] + Math.log(r / 0.22) * wind;
            var dt = ((th - ta) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI;
            var off = dt * r, w = 0.07 + 0.1 * r;
            d += a[1] * 1.25 * Math.exp(-off * off / (w * w)) * Math.exp(-Math.max(0, r - 0.22));
          });
        }
        d += 0.35 * Math.exp(-r * r / 0.3);                                     // the faint disc between them
        d *= 1 - Math.max(0, Math.min(1, (r - 0.8) / 0.24));                    // fading out at the edge
        d *= 0.7 + 0.6 * clump;                                                 // clouds of stars
        line.push(d > 1.05 ? 3 : d > 0.62 ? 2 : d > 0.34 ? 1 : 0);
      }
      out.push(line);
    }
    return out;
  }
  function drawLogo(cv, upto) {   // upto: how much has printed so far (0-1, left to right)
    var L = LOGO, dpr = Math.min(2, window.devicePixelRatio || 1), w = L.cols * L.pitch, h = L.rows * L.pitch;
    L.dots = L.dots || galaxyDots(L.cols, L.rows);
    COL = COL || palette();
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    var ctx = cv.getContext("2d"), lim = Math.round(upto * L.cols);
    var fill = [COL.track, COL.muted, COL.text, COL.hi], size = [0.22, 0.28, 0.36, 0.44];
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    for (var gy = 0; gy < L.rows; gy++) {
      for (var gx = 0; gx < lim; gx++) {
        var v = L.dots[gy][gx];
        if (v < 0) continue;
        ctx.shadowBlur = v ? 5 : 0;
        ctx.shadowColor = "rgba(69, 240, 138, 0.55)";
        ctx.fillStyle = fill[v];
        ctx.beginPath();
        ctx.arc((gx + 0.5) * L.pitch, (gy + 0.5) * L.pitch, size[v] * L.pitch, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
  }

  // the tube warming up: a dot stretches into a line that opens into a raster of static, dim at
  // first and brightening unsteadily, rolling and juddering until it settles - then the boot screen
  function warmUp() {
    var n = noiseCanvas(3), t0 = performance.now(), last = t0, D = 3600, roll = Math.random(), hold = 0, sx = 0, sy = 0;
    BOOT.phase = "warm";
    function frame(now) {
      if (BOOT.phase !== "warm") return;
      var t = now - t0, dt = now - last;
      last = now;
      if (t >= D) { n.cv.style.transform = ""; post(); return; }
      var wide = Math.min(1, t / 550), tall = t < 550 ? 0 : Math.min(1, (t - 550) / 600);
      tall *= tall;
      var warm = Math.max(0, Math.min(1, (t - 600) / (D - 1000)));
      var bright = (0.07 + 0.88 * warm * warm) * (0.8 + Math.random() * 0.4);   // a slow, unsteady rise
      if (t < 1150) bright = Math.max(bright, 1.15 - tall * 0.85);              // the switch-on line is bright
      roll = (roll + dt / 1000 * 1.6 * (1 - warm * 0.85)) % 1;                   // the frame rolls, slowing as it locks
      var gap = roll * n.h * 1.3 - n.h * 0.15;
      if (hold > 0) hold--;
      else if (Math.random() < 0.08 * (1 - warm * 0.5)) {                        // a judder: the picture jumps
        sx = rnd(-2.5, 2.5) * (1 - warm * 0.5); sy = rnd(-8, 8) * (1 - warm * 0.5); hold = 2 + ((Math.random() * 3) | 0);
      } else { sx = 0; sy = 0; }
      n.draw(function (y) {
        if (Math.abs(y - gap) < n.h * 0.06) return bright * 0.12;
        return bright * 0.86 * (Math.random() < 0.012 ? 1.9 : 1);
      }, TINT.green);
      n.cv.style.transform = "translate(" + sx.toFixed(1) + "%," + sy.toFixed(1) + "%) scale(" +
        (0.015 + 0.985 * wide).toFixed(3) + "," + Math.max(0.004, tall).toFixed(3) + ")";
      BOOT.raf = requestAnimationFrame(frame);
    }
    BOOT.raf = requestAnimationFrame(frame);
  }

  // the UCEC boot screen, then a look for the game: found -> that vehicle's start-up, none -> wait
  var CHARTS = { ok: "Online", stale: "Cached", empty: "Online", loading: "Linking", waiting: "Standby", error: "Offline", off: "Off" };
  // the UFC's displays follow this page (the board drives them): blank while the terminal is off, every
  // digit lit through its BIOS and the waiting screen, the version and test patterns through a vehicle's
  // start-up, the menu once the board shows ("")
  function ufcFx(kind, again) {
    if (ufcFx.last === kind && !again) return;
    ufcFx.last = kind;
    try {
      fetch("/api/bootfx", { method: "POST", headers: { "Content-Type": "application/json" },
                             body: JSON.stringify({ fx: kind, page: ED.pageId }) }).catch(function () {});
    } catch (err) { /* nothing to tell */ }
  }

  function post() {
    var box = $("boot"), el = $("bt-text"), instant = reduce.matches;
    BOOT.phase = "post";
    ufcFx("ucec");
    $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
    el.innerHTML = ""; el.className = "bt-ucec";
    box.classList.add("sig");
    if (!instant) { flash(); ED.replay(el, "lockin"); }
    var logo = document.createElement("div");
    logo.className = "ucec-logo";
    logo.innerHTML = '<canvas aria-hidden="true"></canvas><div class="ucec-word">UCEC</div>';
    el.appendChild(logo);
    var cv = logo.querySelector("canvas"), k = bootKit(el, instant);
    var beside = getComputedStyle(logo).cssFloat !== "none";   // beside the text, or above it on an upright phone
    k.cols = Math.max(20, Math.min(56, beside ? k.cols - Math.ceil((logo.getBoundingClientRect().width + 28) / k.cw) : k.cols));
    k.anim(1200, function (f) { drawLogo(cv, f); });   // the dots print in, left to right
    var s = k.s, sy = s.syst || {};
    var checks = [
      ["Processor", "Q-86 @ 4.77 THz"],
      ["Display", "P1 green phosphor"],
      ["Journal link", s.note ? "Searching" : s.journal ? "OK" : "No journal", s.note || !s.journal ? "am" : "hi"],
      ["Star charts", CHARTS[sy.status] || "Standby", sy.status === "error" ? "am" : "hi"],
      ["Commander", k.cmdr]
    ];
    k.row('<span class="hi">UCEC FT3000 Field Terminal</span>');
    k.row('<span class="dim">BIOS ' + ED.esc(s.version || "") + "  (c) " + k.year + (k.cols < 40 ? " UCEC" : " Universal Computer Equipment Corp.") + "</span>");
    k.row(" ");
    var lines = [k.row("")], mem = k.row("");   // the processor, then the memory test, then the rest
    lines = lines.concat(checks.slice(1).map(function () { return k.row(""); }));
    var gap = k.row(""), det = k.row("");
    k.at(900, function () {
      var foot = document.createElement("div");
      foot.className = "ucec-foot";
      foot.innerHTML = 'Tap the screen or press <span class="hi">ESC</span> to skip';
      el.appendChild(foot);
    });
    k.at(1400, function () { lines[0].innerHTML = k.lead(checks[0][0], checks[0][1]); k.reveal(lines[0], 220); });
    k.at(1800, function () {
      k.anim(2400, function (f) {
        mem.innerHTML = k.lead("Memory test", Math.round(f * 655360) + "K" + (f >= 1 ? " OK" : ""), f >= 1 ? "hi" : "dim");
      });
    });
    checks.slice(1).forEach(function (ck, i) {
      k.at(4600 + i * 600, function () { lines[i + 1].innerHTML = k.lead(ck[0], ck[1], ck[2]); k.reveal(lines[i + 1], 220); });
    });
    k.at(7000, function () { gap.textContent = " "; });
    k.at(7600, function () {
      k.anim(instant ? 0 : 3000, function (f) {
        det.innerHTML = "Detecting input signal" + rep0(".", Math.round(f * 6));
        if (f < 1) return;
        var g = (S.data || {}).game || {};
        det.innerHTML += g.in ? ' <span class="hi">Found</span>' : ' <span class="am">None</span>';
        later(instant ? 1500 : 850, function () {
          var now = (S.data || {}).game || {};
          if (now.in) snap(now); else waitSignal();
        });
      });
    });
  }

  // no game to show: light static, the terminal's message on top
  function waitSignal() {
    var box = $("boot");
    BOOT.phase = "wait";
    ufcFx("ucec");
    box.className = "wait";
    $("bt-text").innerHTML = ""; $("bt-text").className = "";
    $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
    if (reduce.matches) return;   // no static: the message on black
    // a few frames of static made once and shown at random (cheap enough to leave running through the
    // main menu), a faint bar drifting down as if the picture can't hold, now and then a line tearing
    var n = noiseCanvas(4), ctx = n.cv.getContext("2d"), frames = [];
    for (var f = 0; f < 6; f++) {
      n.draw(function () { return 0.34; }, TINT.green);
      frames.push(ctx.getImageData(0, 0, n.w, n.h));
    }
    n.cv.style.opacity = "0";
    n.cv.style.transition = "opacity 0.6s ease-in";
    void n.cv.offsetWidth;
    n.cv.style.opacity = "1";
    var last = 0, band = Math.random();
    function frame(now) {
      if (BOOT.phase !== "wait") return;
      BOOT.raf = requestAnimationFrame(frame);
      if (now - last < 55) return;   // about 18 frames a second is plenty for static
      last = now;
      ctx.putImageData(frames[(Math.random() * frames.length) | 0], 0, 0);
      band = (band + 0.0045) % 1;
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = "rgba(69, 240, 138, 0.07)";
      ctx.fillRect(0, band * n.h * 1.4 - n.h * 0.2, n.w, n.h * 0.12);
      ctx.globalCompositeOperation = "source-over";
      if (Math.random() < 0.05) {
        var ty = Math.random() * n.h, th = 1 + Math.random() * 3;
        ctx.drawImage(n.cv, 0, ty, n.w, th, rnd(-10, 10), ty, n.w, th);
      }
    }
    BOOT.raf = requestAnimationFrame(frame);
  }

  // the signal: straight into that vehicle's start-up (on foot, the static was it)
  function snap(g) {
    var to = g.vehicle || "ship", box = $("boot");
    cancelAnimationFrame(BOOT.raf);
    box.classList.remove("wait");
    $("bt-text").innerHTML = ""; $("bt-text").className = "";
    $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
    if (reduce.matches) {
      if (!VEHICLES[to]) { endBoot(); return; }
      BOOT.phase = "boot";
      box.classList.add("sig");
      bootScreen(to, g.label, true);
      later(3000, endBoot);
      return;
    }
    signal(to, g.label || "");
  }

  function start(seq) {   // the overlay comes up
    BOOT.on = true;
    BOOT.seq = seq;
    BOOT.timers = [];
    var box = $("boot");
    box.className = "";
    box.hidden = false;
    $("bt-text").innerHTML = ""; $("bt-text").className = "";
    $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
    return box;
  }
  function powerOn() {   // the page has just opened
    if (S.halted) return;
    ufcFx("off");
    start(true).className = "power";
    BOOT.phase = "off";
    later(2000, reduce.matches ? post : warmUp);
  }
  function lost(hold) {   // the game's gone: the picture breaks up, then no signal
    if (BOOT.on || S.halted) return;
    start(true);
    BOOT.hold = !!hold;
    if (reduce.matches) waitSignal(); else disconnect(waitSignal, true);   // the tube switches off
  }

  function endBoot() {
    ufcFx("");
    if (!BOOT.on || BOOT.phase === "end") return;
    BOOT.phase = "end";
    cancelAnimationFrame(BOOT.raf);
    BOOT.timers.forEach(clearTimeout);
    BOOT.timers = [];
    var box = $("boot");
    box.classList.remove("thru");
    $("app").classList.remove("glitch");
    box.classList.add("out");
    ED.replay($("app"), "pullbig");
    BOOT.timers.push(setTimeout(function () {
      box.hidden = true;
      box.className = "";
      $("bt-text").innerHTML = ""; $("bt-text").className = "";
      $("bt-sig").innerHTML = ""; $("bt-sig").className = "";
      $("bt-noise").style.transition = ""; $("bt-noise").style.transform = ""; $("bt-noise").style.opacity = "1";
      BOOT.on = BOOT.seq = BOOT.hold = false;
      BOOT.phase = "";
    }, 460));
  }

  // previews: add #boot (ship), #boot-srv, #boot-nomad, #boot-fighter or #boot-foot to the
  // address for a start-up; #exit-foot, #exit-srv, #exit-nomad, #exit-fighter or #exit-ship
  // (back from the SRV) for leaving one vehicle for another; #nosignal for losing the game
  function hashFx() {
    if (location.hash === "#nosignal") return { nosignal: true };
    var m = /^#(boot|exit)(?:-(ship|srv|nomad|fighter|foot))?$/.exec(location.hash);
    if (!m) return null;
    var to = m[2] || "ship";
    var names = { srv: "SRV Scarab", nomad: "Nomad", fighter: "Gelid F" };
    return { from: m[1] === "exit" ? (to === "ship" ? "srv" : "ship") : "", to: to, label: names[to] || "" };
  }
  function preview(hf) { if (hf.nosignal) lost(true); else playTransition(hf); }

  // tap or Esc to skip: whatever's showing, or the power-on before it has begun
  var opened = false, skipped = false;
  function skip() {
    if (BOOT.on) { endBoot(); return; }
    if (!opened) { skipped = true; $("boot").hidden = true; $("boot").className = ""; }
  }
  $("boot").addEventListener("click", skip);
  document.addEventListener("keydown", function (e) {
    if ((BOOT.on || !opened) && (e.key === "Escape" || e.key === "Enter" || e.key === " ")) { e.preventDefault(); skip(); }
  });
  window.addEventListener("hashchange", function () { var hf = hashFx(); if (hf) preview(hf); });

  // every refresh: the terminal's start-up when the page opens, then a change of vehicle plays its
  // effect, and losing the game (main menu, closed) shows the no-signal screen
  var bootId, wasIn = false;   // the board's last change of vehicle, and whether you were in the game, as seen here
  function update(s) {
    var bt = s.boot || {}, bid = bt.id || "", g = s.game || {};
    if (!opened) {   // the page has just opened
      opened = true;
      bootId = bid;
      wasIn = !!g.in;
      var hf = hashFx();
      if (hf) { $("boot").hidden = true; $("boot").className = ""; ufcFx(""); setTimeout(function () { preview(hf); }, 400); }
      else if (!skipped) powerOn();
      else ufcFx("");   // skipped before it began: straight to the board
      return;
    }
    if (BOOT.seq) {   // the terminal's own screens: a load-in is their cue, not a separate effect
      bootId = bid || bootId;
      wasIn = !!g.in;
      if (BOOT.phase === "wait" && g.in && !BOOT.hold) snap(g);
      return;
    }
    if (bid && bid !== bootId) {
      bootId = bid;
      wasIn = !!g.in;
      playTransition(bt);
      return;
    }
    if (wasIn && !g.in) {   // out of the game (once any effect showing has finished)
      if (!BOOT.on) { wasIn = false; lost(false); }
      return;
    }
    wasIn = !!g.in;
  }
  // an overlay above every page
  ED.boot = { update: update, end: function () { if (BOOT.on) endBoot(); }, on: function () { return BOOT.on; },
              ufcAgain: function () { if (ufcFx.last !== undefined) ufcFx(ufcFx.last, true); } };
})();
