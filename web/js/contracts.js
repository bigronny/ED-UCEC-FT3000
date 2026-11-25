// ED Target Board page - 3 Contracts, sub-tab 1 (Active): every mission you hold; targets get a subject file - the
// board's facts from the journal (affiliation, contract, serial, incept date, status, retirement bounty, threat, the
// last scan) and the AI's parts (known as, maker, original function; background, implanted memory, behavioural notes,
// assessment). A dossier written before the subject files shows as it was written. Held, the ID picture (top right)
// has the target's file written again - here only.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- turning API data into what the screen shows ----
  function nbsp(s) { s = String(s || ""); return s.length > 18 ? s : s.replace(/ /g, "\u00a0"); }   // keep a short place name on one line
  function contractView(t, here) {   // a mission with no target: cargo, passengers, courier, on foot...
    var m = t.missions[0], done = m.status === "redirected", d = m.depot, px = m.passengers;
    var dest = [m.settlement, m.station, m.system].filter(Boolean).map(nbsp).join(", ");
    var hand = [m.return_station, m.return_system].filter(Boolean).map(nbsp).join(", ");
    var inSys = !!(here && !done && (m.system || "").toLowerCase() === here.toLowerCase());
    var status;
    if (done) status = "Hand in at " + (hand || "the issuer");
    else if (d && d.total) status = (d.delivered ? "Delivered " + ED.num(d.delivered) : "Collected " + ED.num(d.collected || 0)) + " of " + ED.num(d.total);
    else status = "Active";
    var det = m.commodity && m.count ? ["Cargo", ED.num(m.count) + " \u00d7 " + m.commodity] :
      px ? ["Passengers", [px.count, px.type, px.vip ? "VIP" : "", px.wanted ? "wanted" : ""].filter(Boolean).join(" \u00b7 ")] :
      m.donation ? ["Donation", ED.cr0(m.donation)] : m.target_faction ? ["For", m.target_faction] : ["Type", m.cat];
    var chips = [];
    if (inSys) chips.push("In system");
    if (done) chips.push("Objective complete");
    if (m.wing) chips.push("Wing");
    return {
      key: t.key, name: t.name, locked: false, done: done, contract: true,
      sys: done ? m.return_system || "" : m.system || "",   // the system the copy button copies
      label: ["Contract " + String(m.id).slice(-4), m.cat].filter(Boolean).join(" \u00b7 "),
      loc: done ? "Hand in: " + (hand || "issuer") : dest || "-",
      iss: m.issuer || "-", rew: ED.cr(m.reward), expiry: m.expiry, status: status, chips: chips,
      scanLab: det[0], scanTxt: det[1], railTag: m.cat
    };
  }
  function card(t, here) {   // what one contract's rail entry and panel show
    if (t.kind === "contract") return contractView(t, here);
    var ms = t.missions, n = ms.length, m0 = ms[0];
    var active = ms.filter(function (m) { return m.status !== "redirected"; });
    var done = n - active.length;
    var locked = !!(t.scan && Date.now() - Date.parse(t.scan.time) < ED.LOCK_MS);
    var inSys = !!(here && active.some(function (m) { return (m.system || "").toLowerCase() === here.toLowerCase(); }));
    var places = [];
    active.forEach(function (m) {
      var p = [m.settlement, m.station, m.system].filter(Boolean).map(nbsp).join(", ");   // on foot: the settlement
      if (p && places.indexOf(p) < 0) places.push(p);
    });
    var handIn = [];
    ms.forEach(function (m) {
      if (m.status === "redirected") {
        var p = [m.return_station, m.return_system].filter(Boolean).map(nbsp).join(", ");
        if (p && handIn.indexOf(p) < 0) handIn.push(p);
      }
    });
    var expiry = (active.length ? active : ms).map(function (m) { return m.expiry; }).filter(Boolean).sort()[0] || "";
    var f = t.file || {}, b = t.backstory || {}, w = b.fmt === 2 && b.status === "done" ? b.file || {} : null, u = f.units;
    var status = f.status || (active.length ? "AT LARGE" : "RETIRED");
    if (u && active.length) status += " \u00b7 " + u.left + " of " + u.need + " units";
    if (!active.length) status += " \u00b7 hand in at " + (handIn[0] || "the issuer");
    else if (done) status += " \u00b7 " + done + " of " + n + " done";
    var label = t.kind === "person"
      ? ["Subject file", "Case " + String(m0.id).slice(-4)]
      : ["Batch file", "Case " + String(m0.id).slice(-4), n > 1 ? n + " contracts" : ""];
    var issuers = [];
    ms.forEach(function (m) { if (m.issuer && issuers.indexOf(m.issuer) < 0) issuers.push(m.issuer); });
    var chips = [];
    if (inSys) chips.push("In system");
    if (locked) chips.push("Target locked");
    var foot = f.mode === "foot";
    var sysOf = (active[0] || {}).system || (ms.filter(function (m) { return m.status === "redirected"; })[0] || {}).return_system || "";
    return {
      key: t.key, name: t.name, locked: locked, done: !active.length, sys: sysOf,
      label: label.filter(Boolean).join(" \u00b7 "),
      loc: places.length ? places.join(" / ") : (handIn.length ? "Hand in: " + handIn.join(" / ") : "-"),
      iss: issuers.length ? issuers[0] + (issuers.length > 1 ? " +" + (issuers.length - 1) : "") : "-",
      rew: ED.cr(ms.reduce(function (a, m) { return a + (Number(m.reward) || 0); }, 0)),
      expiry: expiry, status: status, chips: chips,
      scanLab: foot ? "Located" : "Last scan",
      scanTxt: foot ? (f.located ? "Settlement reached " + when(f.located) : "Not yet")
        : t.scan ? [t.scan.ship, t.scan.rank].filter(Boolean).join(" \u00b7 ") : "No scan yet",
      railTag: t.kind === "person" ? "Wanted" : (n > 1 ? "Faction \u00d7" + n : "Faction"),
      con: f.contract || "-", aff: f.affiliation || "-", ser: f.serial || "-", inc: f.incept || "-", thr: f.threat || "-",
      mak: w && w.maker || "-", fun: w && w.original_function || "-", known: w && w.known_as ? "Known as \u201c" + w.known_as + "\u201d" : "",
      file: w, mode: f.mode, kind: t.kind, scanned: !!b.scanned, rescan: b.rescan || ""
    };
  }
  function when(iso) { var d = new Date(iso); return isNaN(d) ? "" : d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }
  function renderRail(views) {
    var sig = views.map(function (v) {
      return [v.key, v.name, v.railTag, v.locked, v.done, v.key === S.sel].join("|");
    }).join("~");
    if (sig === S.railSig) return;
    S.railSig = sig;
    var oldKeys = S.railKeys;
    $("list").innerHTML = views.map(function (v, i) {
      var tag = v.locked ? "Locked" : v.done ? "Hand in" : "";
      return '<button type="button" class="item' + (v.key === S.sel ? " sel" : "") + (v.locked ? " lock" : "") +
        '" data-key="' + ED.esc(v.key) + '" aria-pressed="' + (v.key === S.sel) + '">' +
        '<span class="meta"><span>' + String(i + 1).padStart(2, "0") + " " + ED.esc(v.railTag) + "</span>" +
        (tag ? '<span class="soon">' + tag + "</span>" : '<span data-exp="' + ED.esc(v.expiry) + '"></span>') +
        '</span><span class="nm">' + ED.esc(v.name) + "</span></button>";
    }).join("");
    if (oldKeys) {
      Array.prototype.forEach.call($("list").querySelectorAll(".item"), function (b) {
        if (oldKeys.indexOf(b.dataset.key) < 0) {
          var nm = b.querySelector(".nm"); nm._final = null; ED.resolve(nm, nm.textContent);
        }
      });
    }
    S.railKeys = views.map(function (v) { return v.key; });
    ED.applyCursor(false);
    ED.tick();
  }
  function renderPanel(s, t, v, newLock) {
    var panel = $("panel");
    if (!t) {   // no targets: crosses ("No information"), or a start-up/journal message
      panel.classList.remove("lock");
      panel.classList.toggle("none", !!s.note);
      panel.classList.toggle("notgt", !s.note);
      ED.showNote(s);
      S.panelKey = null;
      S.ctClip = "";
      $("f-clip").hidden = true;
      return;
    }
    panel.classList.remove("none", "notgt");
    var switched = S.panelKey !== t.key, animate = !switched && !S.first;
    if (switched && S.panelKey !== null) ED.replay($("pc"), "pull");
    if (switched) { $("sigil").innerHTML = ED.sigil(t.name); $("pc").scrollTop = 0; }
    S.panelKey = t.key;

    ED.setText($("case"), v.label, animate);
    ED.setText($("name"), v.name, animate);
    panel.classList.toggle("contract", !!v.contract);
    S.panelTarget = !v.contract;
    $("known").hidden = !v.known;
    ED.setText($("known"), v.known || "", animate);
    $("f-l2").textContent = v.contract ? "Issued by" : "Contract";
    $("f-l3").textContent = v.contract ? "Reward" : "Retirement bounty";
    if (!v.contract) {
      [["f-aff", v.aff], ["f-ser", v.ser], ["f-inc", v.inc], ["f-mak", v.mak], ["f-fun", v.fun], ["f-thr", v.thr]].forEach(function (c) {
        ED.setText($(c[0]), c[1], animate);
      });
    }
    ED.setText($("f-loc"), v.loc, animate);
    S.ctClip = v.sys || "";   // the copy / paste button beside Location (a short COMM2 pull on the UFC presses it)
    if ($("f-clip").dataset.clip !== S.ctClip) { $("f-clip").dataset.clip = S.ctClip; ED.clipShow(); }
    $("f-clip").hidden = !S.ctClip;
    ED.setText($("f-iss"), v.contract ? v.iss : v.con, animate);
    ED.setText($("f-rew"), v.rew, animate);
    $("f-l5").textContent = v.scanLab;
    ED.setText($("f-scan"), v.scanTxt, animate);
    ED.setText($("f-stat"), v.status, animate);
    $("f-exp").dataset.exp = v.expiry;

    var chipSig = t.key + "|" + v.chips.join("|");
    if (chipSig !== S.chipSig) {
      S.chipSig = chipSig;
      $("chips").innerHTML = v.chips.map(function (c) { return '<span class="chip">' + ED.esc(c) + "</span>"; }).join("");
    }
    panel.classList.toggle("lock", v.locked);
    if (newLock) { ED.replay(panel, "flk"); ED.replay($("chips"), "flk"); }

    // scan bars, with a phosphor ghost when a value changes
    var bars = $("bars");
    if (t.scan) {
      bars.hidden = false;
      var prev = S.pct[t.key] || {};
      var sh = Math.round(t.scan.shields == null ? 0 : t.scan.shields) + "%";
      var hu = Math.round(t.scan.hull == null ? 0 : t.scan.hull) + "%";
      if (!switched && prev.sh && prev.sh !== sh) ED.ghost($("p-sh"), prev.sh);
      if (!switched && prev.hu && prev.hu !== hu) ED.ghost($("p-hu"), prev.hu);
      $("b-sh").textContent = ED.blocks(t.scan.shields); $("p-sh").firstChild ? ($("p-sh").firstChild.data = sh) : ($("p-sh").textContent = sh);
      $("b-hu").textContent = ED.blocks(t.scan.hull); $("p-hu").firstChild ? ($("p-hu").firstChild.data = hu) : ($("p-hu").textContent = hu);
      $("b-ago").dataset.ago = t.scan.time;
      S.pct[t.key] = { sh: sh, hu: hu };
    } else {
      bars.hidden = true;
    }

    // the subject file's four parts (targets), a dossier written before them, or the contract's details (everything else)
    var story = $("story"), b = t.backstory || {};
    $("dlab").textContent = v.contract ? "Details" : "Dossier";
    var secs = !v.contract && !!v.file;
    $("dsecs").hidden = !secs;
    $("dhead").hidden = story.hidden = secs;
    if (v.contract) {
      var brief = contractBrief(t.missions[0]);
      if (story._final !== brief) { ED.stop(story); story._final = brief; story.className = "brief"; story.innerHTML = brief; }
      return;
    }
    var prevStatus = S.storyStatus[t.key];
    S.storyStatus[t.key] = b.status;
    if (secs) {   // (just written: typed out; its notes again from the scan: resolved in place)
      var arrived = !switched && (prevStatus === "queued" || prevStatus === "writing");
      [["s-bg", v.file.background], ["s-mem", v.file.implanted_memory], ["s-beh", v.file.behavioural_notes], ["s-ass", v.file.assessment]].forEach(function (c) {
        var el = $(c[0]);
        if (el._final === c[1]) return;
        if (arrived) ED.typeOut(el, c[1] || ""); else ED.setText(el, c[1] || "", !switched && !S.first);
      });
      var lab = "Behavioural notes \u00b7 " + (v.mode === "foot" ? "on foot" : "in ship");
      if (v.rescan) lab += " \u00b7 updating from the scan";
      else if (v.kind === "person" && v.mode !== "foot" && !v.scanned) lab += " \u00b7 provisional";
      $("s-behlab").textContent = lab;
      $("s-asslab").textContent = "Assessment" + (v.kind === "person" && v.mode !== "foot" && !v.scanned && !v.rescan ? " \u00b7 provisional" : "");
      return;
    }
    if (s.engine === "none") {
      story.className = "wait"; ED.setText(story, "Dossiers are switched off.", false);
    } else if (b.status === "done") {
      story.className = "";
      if (story._final !== b.text) {
        var arrived = !switched && (prevStatus === "queued" || prevStatus === "writing");
        if (arrived) ED.typeOut(story, b.text); else ED.setText(story, b.text, false);
      }
    } else if (b.status === "error") {
      story.className = "err"; ED.setText(story, "Dossier not compiled: " + (b.error || "unknown error"), false);
    } else if (b.status === "writing" || b.status === "queued") {
      if (story._final !== "__wait__") {
        ED.stop(story); story._final = "__wait__"; story.className = "wait";
        story.innerHTML = (b.status === "writing" ? "Compiling dossier" : "Dossier queued") + '<span class="blink">_</span>';
      }
    } else {
      story.className = "wait"; ED.setText(story, s.engine_ok === false ? (s.engine_msg || "AI not available.") : "Awaiting dossier.", false);
    }
  }

  function contractBrief(m) {   // what the journal says about a mission, as label / value rows
    var rows = [], d = m.depot, px = m.passengers;
    function row(l, v) { if (v) rows.push('<span class="lab">' + ED.esc(l) + '</span><span class="v">' + ED.esc(v) + "</span>"); }
    if (m.partial) return '<span class="note">Accepted before the journal files this board reads, so only its type and expiry are known.</span>';
    row("Objective", m.title);
    row("Contact", m.contact);   // the person to take a package to, or collect one from
    row("Recipient", m.target_faction && m.target_faction !== m.issuer ? m.target_faction : "");
    if (d && d.total) row("Cargo", "Collected " + ED.num(d.collected || 0) + " \u00b7 delivered " + ED.num(d.delivered || 0) + " of " + ED.num(d.total));
    if (px) row("Passengers", [px.count + (px.count === 1 ? " passenger" : " passengers"), px.type, px.vip ? "VIP" : "", px.wanted ? "wanted by the authorities" : ""].filter(Boolean).join(" \u00b7 "));
    if (m.donation) row("Donation", ED.cr0(m.donation));
    var gain = [m.influence ? "Influence " + m.influence : "", m.reputation ? "reputation " + m.reputation : ""].filter(Boolean).join(" \u00b7 ");
    row("Standing", gain);
    if (m.wing) row("Wing", "Shared with your wing");
    if (m.accepted) row("Accepted", new Date(m.accepted).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }));
    return rows.join("");
  }
  // ---- the page ----
  var C = { views: [], keys: [], lock: null };   // this refresh's cards, their keys, a target just locked
  function update(s) {
    var views = s.contracts.map(function (t) { return card(t, s.system); });
    var keys = views.map(function (v) { return v.key; });
    // a fresh scan of a target counts as a new lock; it's selected and the page jumps to it (main.js)
    var newLock = null;
    s.contracts.forEach(function (t, i) {
      var seen = S.scanSeen[t.key], now = t.scan ? t.scan.time : null;
      if (now && now !== seen && !S.first && views[i].locked) newLock = t.key;
      S.scanSeen[t.key] = now;
    });
    if (newLock) S.sel = newLock;
    if (keys.indexOf(S.sel) < 0) S.sel = keys[0] || null;
    if (S.sel && S.sel !== S.sentSel) {   // tell the script, so the UFC knob starts here
      S.sentSel = S.sel;
      ED.reportView({ pick: { targets: S.sel } });
    }
    C.views = views; C.keys = keys; C.lock = newLock;
    renderRail(views);
  }
  function draw(s) {
    $("pg-contracts").classList.toggle("notgt", !s.contracts.length && !s.note);
    var idx = C.keys.indexOf(S.sel);
    renderPanel(s, idx >= 0 ? s.contracts[idx] : null, idx >= 0 ? C.views[idx] : null, C.lock !== null && C.lock === S.sel);
  }
  function cursor(u, scroll) {   // the UFC knob's highlight (PAGE menu)
    var on = u.menu === "PAGE", cur = on ? (u.cursors || {}).targets : null;
    $("idx-lab").innerHTML = on ? 'Index <span class="ufc">· UFC</span>' : "Index";
    Array.prototype.forEach.call($("list").querySelectorAll(".item"), function (b) {
      var is = on && b.dataset.key === cur;
      b.classList.toggle("cur", is);
      if (is && scroll) b.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
  }
  function pick(key) {   // a click on the rail, or a COMM1 pull on the UFC
    if (!S.data || !S.data.contracts.some(function (t) { return t.key === key; })) return;
    S.sel = key;
    S.railSig = "";
    ED.render(S.data);
  }
  function tick() {   // count the expiries down
    Array.prototype.forEach.call(document.querySelectorAll("#list [data-exp]"), function (el) {
      var ms = ED.msLeft(el.dataset.exp);
      el.textContent = ED.left(el.dataset.exp, true);
      el.className = ms < 864e5 ? "soon" : "";
    });
    var fe = $("f-exp");
    if (fe.dataset.exp !== undefined) fe.textContent = ED.left(fe.dataset.exp, false);
    var ba = $("b-ago");
    if (ba.dataset.ago) ba.textContent = "(" + ED.ago(ba.dataset.ago) + ")";
  }

  $("list").addEventListener("click", function (e) {
    var b = e.target.closest(".item");
    if (b) pick(b.dataset.key);
  });
  // held (HOLD_MS), the ID picture has the target's subject file written again - a target of the Active page's only
  // (the board says no to anything else), and only with an AI to write it
  var HOLD_MS = 900, hold = null;
  function holdEnd() {
    if (hold) { clearTimeout(hold.t); hold = null; }
    $("sigil").classList.remove("hold");
  }
  $("sigil").addEventListener("pointerdown", function (e) {
    if (!S.panelKey || !S.panelTarget || !S.data || S.data.engine === "none") return;
    e.preventDefault();
    holdEnd();
    var key = S.panelKey;
    $("sigil").style.setProperty("--hold", HOLD_MS + "ms");
    $("sigil").classList.add("hold");
    hold = { t: setTimeout(async function () {
      holdEnd();
      if (S.panelKey !== key) return;
      ED.replay($("sigil"), "fired");
      await fetch("/api/regenerate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: key }) });
      ED.refresh();
    }, HOLD_MS) };
  });
  ["pointerup", "pointerleave", "pointercancel"].forEach(function (ev) { $("sigil").addEventListener(ev, holdEnd); });
  $("sigil").addEventListener("contextmenu", function (e) { e.preventDefault(); });

  ED.page({
    tab: "contracts", sub: 1, key: 1, label: "Active", el: "pg-contracts", mode: "", back: "3 Contracts · Active", list: "targets",
    update: update, draw: draw, cursor: cursor, pick: pick, tick: tick,
    enter: function () { S.railSig = ""; $("pc").scrollTop = 0; },
    leave: function () { S.panelKey = null; },   // coming back, the panel starts fresh
    scroll: function (clicks) { ED.scrollBox($("pc"), clicks); },
    pull: function () { if (S.ctClip) ED.clipPress(S.ctClip, (S.ufc || {}).c2pull_n); }   // COMM2 pull: copy, then paste
  });
  ED.contracts = { lock: function () { return C.lock; } };   // a target locked this refresh
})();
