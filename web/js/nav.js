// ED Target Board page - 2 Nav's waypoint system, after the F/A-18C's, shared by Wpt, HSI, Atk and Syst: the board's syst.nav
// (your marks MK1-MK9, the SEQ 1-3 flight plans and Atk's ATK one, the steer-to point, the designated target - TGT - the
// offset aimpoints and the attack plan), every point by its key (a waypoint t12, its offset aimpoint t12o, a mark mk3, an
// attack plan's point atk:1:IP), POST /api/nav, where you are now (Traj's filter), the UFC's MK, and the UFC sub-levels'
// option windows drawn on the page.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, RAD = Math.PI / 180;

  function syst() { return (S.data || {}).syst || {}; }
  function nav() { return syst().nav || {}; }
  function tgts() { return syst().tgts || []; }
  function n360(a) { return ((a % 360) + 360) % 360; }
  function low(s) { return String(s || "").toLowerCase(); }

  // every point, by key: {key, src (wpt | oap | mk | atk), label (WP3, WP3 O/S, MK2, IN), name, num, body, lat, lon, alt?, role?}
  var PTS = { data: null, out: null };
  function points() {
    if (PTS.data === S.data && PTS.out) return PTS.out;
    var nv = nav(), out = {};
    tgts().forEach(function (t) {
      out[t.key] = { key: t.key, src: "wpt", label: "WP" + t.num, name: t.name, num: t.num, body: t.body, lat: t.lat, lon: t.lon, id: t.id };
    });
    Object.keys(nv.oaps || {}).forEach(function (k) {
      var o = nv.oaps[k], w = out[k.slice(0, -1)];
      if (w) out[k] = { key: k, src: "oap", label: w.label + " O/S", name: w.name + " O/S", num: w.num, body: w.body, lat: o.lat, lon: o.lon, rng: o.rng, brg: o.brg };
    });
    (nv.marks || []).forEach(function (m) {
      out[m.key] = { key: m.key, src: "mk", label: m.name, name: m.name, num: m.slot, body: m.body, lat: m.lat, lon: m.lon, alt: m.alt };
    });
    var b = nv.built;
    if (b) Object.keys(b.roles).forEach(function (r) {
      b.roles[r].forEach(function (p, i) {
        var k = "atk:" + r + ":" + p.id;
        out[k] = { key: k, src: "atk", label: p.id, name: p.id, num: i + 1, role: +r, body: b.tgt.body, lat: p.lat, lon: p.lon, alt: p.alt, call: p.call, pt: p };
      });
    });
    PTS.data = S.data; PTS.out = out;
    return out;
  }
  function point(key) { return key ? points()[key] || null : null; }
  function tgt() { return nav().tgt || null; }   // the designated target: {key, src, name, body, lat, lon}
  function seqKeys(s) { return (nav().seqs || {})[s || nav().seq || "none"] || []; }   // (NONE: none)
  function seqName(s) { return s === "atk" ? "ATK" : s === "none" || !s ? "SEQ None" : "SEQ " + s; }
  function allKeys() {   // with no flight plan activated (SEQ NONE), the HSI's points: all the system's waypoints, then the marks
    return tgts().map(function (t) { return t.key; }).concat((nav().marks || []).map(function (m) { return m.key; }));
  }
  function cs(role) { var p = nav().plan || {}; return (p.cs || "WK5") + (role || p.role || 1); }   // a role's callsign: WK51, WK52

  // ---- the board ----
  function post(body, done) {   // (answering a UFC press: with its token - the board acts on it once, whichever pages answer)
    var u = ED.ufcU ? ED.ufcU() : undefined;
    if (u && body.u == null && body.n == null) body.u = u;
    fetch("/api/nav", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (done) done(j || {}); ED.refresh(); }, function () { if (done) done({}); });
  }
  function dsgable(key) {   // can it be designated: a waypoint, its offset aimpoint or a mark, or a surface site with a position
    var p = point(key);
    if (p) return p.src !== "atk";
    var e = key ? (syst().entries || []).filter(function (x) { return x.key === key; })[0] : null, pic = (e || {}).pic || {};
    return !!e && pic.kind === "surface" && pic.lat != null && pic.lon != null;
  }
  function dsg(key, n, done) {   // designate it (again: its offset aimpoint, if it has one, then nothing); n: the UFC's DSG it answers
    var body = { op: "dsg", key: key || null };
    if (typeof n === "number") body.n = n;
    if (!key) body.off = true;
    post(body, done);
  }

  // ---- where you are now: Traj's filter, carried on from the last reading (if it's on this body) ----
  function fix(body) {
    var me = syst().me, T = ED.traj || {}, nv = T.nav;
    if (!me || me.lat == null || !nv || !nv.kx || !nv.kx.x || low(nv.body) !== low(me.body)) return null;
    if (body && low(body) !== low(me.body)) return null;
    var p = nv.at(performance.now() / 1000), gs = Math.hypot(p.v[0], p.v[1]);
    return { body: me.body, R: nv.R, lat: p.lat, lon: ((p.lon + 540) % 360) - 180, alt: p.alt, v: p.v, gs: gs, still: p.still,
             trk: gs > 5 ? n360(Math.atan2(p.v[0], p.v[1]) / RAD) : (me.hdg != null ? me.hdg : null), hdg: me.hdg };
  }
  function radius(body) {   // a body's radius (m): the game's while you're at it (the board builds with the same), else the system data's
    var me = syst().me;
    if (me && me.r && low(me.body) === low(body)) return me.r;
    var e = (syst().entries || []).filter(function (x) { return x.kind === "planet" && low(x.name) === low(body); })[0];
    return e && e.radius ? e.radius * 1000 : null;
  }
  function cardinal(deg) { return ["NORTH", "EAST", "SOUTH", "WEST"][Math.floor((n360(deg) + 45) / 90) % 4]; }

  // the UFC's MK: a mark where you are now - every open page answers; the board takes the first (n) and, with no page, marks
  // from Status.json itself
  function markNow(n) {
    var p = ED.tgtOver ? ED.tgtOver() : { ok: false };
    if (!p.ok) return;
    post({ op: "mark", n: n, body: p.name, lat: Math.round(p.lat * 1e6) / 1e6, lon: Math.round(p.lon * 1e6) / 1e6,
           alt: p.alt != null ? Math.round(p.alt) : null, method: "overfly" }, function (j) {
      if (j.ok && j.mark) { S.navNote = "Marked " + j.mark.name; S.navNoteAt = Date.now(); }
    });
  }

  // a UFC sub-level drawn on the page, as the UFC shows it: the five option windows (':' on the one being typed) and the
  // scratchpad
  function lvHtml(opts, cue, sp) {
    sp = sp || {};
    return '<span class="lab ufclab">UFC</span><span class="ufcopts">' + opts.map(function (o, i) {
      return '<span class="ufco' + (cue === i + 1 ? " cue" : "") + (o ? "" : " off") + '"><span class="ufcc">' + (cue === i + 1 ? ":" : "") + "</span>" +
        ED.esc(o || "") + "</span>";
    }).join("") + '</span><span class="ufcsp"><span class="ufcs">' + ED.esc((sp.s1 || "").slice(0, 2)) + '</span><span class="ufcs">' +
      ED.esc((sp.s2 || "").slice(0, 2)) + '</span><span class="ufcn">' + ED.esc((sp.num || "").slice(0, 8)) + '</span></span>';
  }

  ED.nav = {
    y: syst, data: nav, tgts: tgts, points: points, point: point, tgt: tgt, seqKeys: seqKeys, seqName: seqName, allKeys: allKeys, cs: cs,
    post: post, dsg: dsg, dsgable: dsgable, fix: fix, radius: radius, cardinal: cardinal, markNow: markNow, lvHtml: lvHtml, n360: n360
  };
})();
