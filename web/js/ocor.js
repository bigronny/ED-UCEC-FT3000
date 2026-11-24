// ED Target Board page - 3 Contracts, sub-tab 3 (OCOR): objectives from the pasted briefing, with distances.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  // ---- OCOR (Contracts, sub-tab 3): objectives from the pasted briefing ----
  var TASK = { raise: "Raise influence", reduce: "Reduce influence", war: "War", election: "Election" };
  function obList(s) { return ((s && s.ocor) || {}).objectives || []; }
  function words(t) {   // each word in a no-wrap span, so a name never splits at its hyphens
    return String(t || "").split(" ").map(function (w) { return '<span class="w">' + ED.esc(w) + "</span>"; }).join(" ");
  }
  function shortDate(d) { return String(d || "").replace(/\b([A-Za-z]{3})[a-z]+\b/, "$1"); }
  function linkify(t) {
    return ED.esc(t).replace(/https?:\/\/[^\s<]+/g, function (u) {
      return '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + u + "</a>";
    });
  }
  function obRemain(o) {
    if (o.done) return "Done";
    if (o.task === "war" || o.task === "election") return o.score ? o.score.replace(/\s*\(.*\)$/, "") : "";
    return o.pct ? o.dir + o.pct + "%" : "";
  }

  // Distances, worked out only while the OCOR page is showing: straight-line light years from the
  // system you're in (from your journal) to each objective's system (coordinates from Spansh or EDSM, cached
  // by the script), and roughly how many jumps at your ship's maximum jump range ("~5 jumps").
  function obDistances(s) {
    var out = {};
    if (!ED.showing("contracts", 3)) return out;
    var d = (s.ocor || {}).dist || {}, coords = d.coords || {}, here = d.here;
    var cur = String(s.system || "").toLowerCase(), range = +s.jump_range || 0;
    obList(s).forEach(function (o) {
      var c = coords[o.system], r = { state: "wait" };
      if (cur && String(o.system).toLowerCase() === cur) r = { state: "here" };
      else if (c === "unknown") r = { state: "unknown" };
      else if (!c && d.edsm === false) r = { state: "off" };
      else if (Array.isArray(c) && here) {
        var ly = Math.hypot(c[0] - here[0], c[1] - here[1], c[2] - here[2]);
        r = { state: "ok", ly: ly, jumps: range ? Math.max(1, Math.ceil(ly / range - 1e-9)) : 0 };
      } else if (Array.isArray(c)) r = { state: "nopos" };
      out[o.id] = r;
    });
    return out;
  }
  function lyShort(ly) { return ly < 10 ? ly.toFixed(1) : Math.round(ly).toLocaleString("en-GB"); }
  function obLy(r) {   // right of the system name in the list
    if (!r) return "";
    if (r.state === "here") return '<span class="ly"><span>Here</span></span>';
    if (r.state !== "ok") return "";
    return '<span class="ly"><span>' + lyShort(r.ly) + " LY</span>" +
      (r.jumps ? '<span class="j">~' + r.jumps + (r.jumps === 1 ? " jump" : " jumps") + "</span>" : "") + "</span>";
  }
  function obDistText(r, s) {   // the details panel
    var st = (r || {}).state;
    if (st === "here") return "You're in this system";
    if (st === "ok") return r.ly.toFixed(1) + " ly from " + (s.system || "you") +
      (r.jumps ? " \u00b7 ~" + r.jumps + (r.jumps === 1 ? " jump" : " jumps") : "");
    if (st === "unknown") return "Not known to Spansh or EDSM";
    if (st === "off") return "Unknown (Spansh and EDSM Uplinks off)";
    if (st === "nopos") return "Waiting for your position";
    return "Locating\u2026";
  }

  function renderOcor(s) {
    var b = s.ocor || { objectives: [] }, obs = b.objectives || [];
    var fresh = S.obV !== undefined && b.v !== S.obV;   // a new briefing was pasted (here or elsewhere)
    if (b.v !== S.obV) { S.obV = b.v; S.obSig = ""; S.obKey = null; S.obNotesV = null; if (fresh) S.obSel = null; }
    var ids = obs.map(function (o) { return o.id; });
    var todo = obs.filter(function (o) { return !o.done; });
    if (ids.indexOf(S.obSel) < 0) S.obSel = (todo[0] || obs[0] || {}).id || null;   // start on one still to do
    if (S.obSel && S.obSel !== S.obSent) {   // tell the script, so the UFC knob starts here
      S.obSent = S.obSel;
      ED.reportView({ pick: { ocor: S.obSel } });
    }
    $("pg-ocor").classList.toggle("obnone", !obs.length);
    var ag = $("ob-age");   // "Fetched 16:14 · 3h 12m ago" above the button (kept ticking by tick())
    ag.dataset.pasted = obs.length && b.pasted ? b.pasted : "";
    ag.hidden = !ag.dataset.pasted;

    // left: system names under section separators
    var dist = obDistances(s), lys = {};
    obs.forEach(function (o) { lys[o.id] = obLy(dist[o.id]); });
    var sig = b.v + "|" + S.obSel + "|" + JSON.stringify(lys);
    if (sig !== S.obSig) {
      S.obSig = sig;
      var html = "", sec = null;
      obs.forEach(function (o, i) {
        if (o.section !== sec) { sec = o.section; html += '<div class="sep">' + ED.esc(sec) + "</div>"; }
        var on = o.id === S.obSel;
        html += '<button type="button" class="item ob' + (on ? " sel" : "") + (o.done ? " done" : "") + '" data-oid="' + ED.esc(o.id) +
          '" aria-pressed="' + on + '"><span class="meta"><span>' + String(i + 1).padStart(2, "0") + " " +
          ED.esc(o.faction || TASK[o.task] || "Objective") + "</span><span>" + ED.esc(obRemain(o)) + "</span></span>" +
          '<span class="nmrow"><span class="nm">' + words(o.system) + "</span>" + lys[o.id] + "</span></button>";
      });
      $("ob-list").innerHTML = html;
      if (fresh) {
        ED.replay($("ob-list"), "pull");
        Array.prototype.forEach.call($("ob-list").querySelectorAll(".nm"), function (nm) {
          ED.resolve(nm, nm.textContent, nm.innerHTML);
        });
      }
      ED.applyCursor(false);
    }

    // right: the selected objective's details
    var o = obs[ids.indexOf(S.obSel)];
    if (!o) return;
    var key = b.v + ":" + o.id, switched = S.obKey !== key;
    var here = !!(s.system && s.system.toLowerCase() === String(o.system).toLowerCase());
    var chipSig = key + "|" + here;
    if (chipSig !== S.obChips) {
      S.obChips = chipSig;
      $("ob-chips").innerHTML = (o.done ? '<span class="chip dim">Done</span>' : "") + (here ? '<span class="chip">In system</span>' : "");
    }
    if (ED.showing("contracts", 3)) ED.setText($("ob-dist"), obDistText(dist[o.id], s), false);   // follows you as you jump
    if (S.obNotesV !== b.v) {
      S.obNotesV = b.v;
      var notes = b.notes || [];
      $("ob-nlab").hidden = !notes.length;
      $("ob-notes").innerHTML = notes.map(function (n) {
        return '<div class="' + (n.bullet ? "bul" : "nt") + '">' + linkify(n.text) + "</div>";
      }).join("");
    }
    S.obClip = o.system || "";   // the copy / paste button beside the name (a short COMM2 pull on the UFC presses it)
    if ($("ob-clip").dataset.clip !== S.obClip) { $("ob-clip").dataset.clip = S.obClip; ED.clipShow(); }
    $("ob-clip").hidden = !S.obClip;
    if (!switched) return;   // a briefing doesn't change until the next paste
    if (S.obKey !== null && S.obKey !== undefined && !fresh) ED.replay($("ob-pc"), "pull");
    S.obKey = key;
    var vs = o.task === "war" || o.task === "election";
    $("ob-sigil").innerHTML = ED.sigil(o.system);
    $("ob-pc").scrollTop = 0;
    ED.setText($("ob-case"), [o.section, shortDate(b.date)].filter(Boolean).join(" · "), false);
    if (fresh) ED.resolve($("ob-name"), o.system, words(o.system));
    else { ED.stop($("ob-name")); $("ob-name")._final = o.system; $("ob-name").innerHTML = words(o.system); }
    ED.setText($("ob-fac"), o.faction || "-", false);
    ED.setText($("ob-gov"), o.gov || "-", false);
    $("ob-l3").textContent = vs ? "Score" : "Objective";
    ED.setText($("ob-v3"), vs ? (o.score || "-") : (TASK[o.task] || o.section || "-"), false);
    $("ob-l4").textContent = vs ? "Against" : "Remaining";
    var bar = String(o.bar || "").replace(/[\u2593\u2592]/g, "\u2588");   // solid blocks, like the board's other bars
    ED.setText($("ob-v4"), vs ? (o.enemy || "-") : ((bar ? bar + " " : "") + (o.pct ? o.dir + o.pct + "% remaining" : "-")), false);
    ED.setText($("ob-desc"), o.desc || "", false);
    $("ob-orders").innerHTML = (o.bullets || []).map(function (x) { return '<div class="bul">' + linkify(x) + "</div>"; }).join("");
    $("ob-inara").href = o.url || "#";
    $("ob-inara").hidden = !o.url;
  }
  function pick(id) {   // a click on the list, or a COMM1 pull on the UFC
    if (!S.data || !obList(S.data).some(function (o) { return o.id === id; })) return;
    S.obSel = id;
    ED.render(S.data);
  }
  function cursor(u, scroll) {   // the UFC knob's highlight (PAGE menu)
    var on = u.menu === "PAGE", cur = on ? (u.cursors || {}).ocor : null;
    $("ob-lab").innerHTML = on ? 'Index <span class="ufc">· UFC</span>' : "Index";
    Array.prototype.forEach.call($("ob-list").querySelectorAll(".item"), function (b) {
      var is = on && b.dataset.oid === cur;
      b.classList.toggle("cur", is);
      if (is && scroll) b.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
  }
  function tick() {   // "Fetched 16:14 · 3h 12m ago", red once it's old
    var ag = $("ob-age"), pa = ag.dataset.pasted;
    if (!pa) return;
    $("ob-at").textContent = "Fetched " + ED.pastedAt(pa);
    $("ob-ago").textContent = ED.sinceTxt(pa);
    ag.classList.toggle("old", Date.now() - Date.parse(pa) > ED.STALE_MS);
    ag.title = "Briefing fetched " + new Date(pa).toLocaleString("en-GB");
  }
  $("ob-list").addEventListener("click", function (e) {
    var b = e.target.closest(".item");
    if (b) pick(b.dataset.oid);
  });

  // paste box for the OCOR briefing
  function pasteMsg(text, bad) {
    $("pd-msg").textContent = text;
    $("pd-msg").className = bad ? "lab bad" : "lab";
  }
  function openPaste() {
    $("paste").hidden = false;
    $("pd-text").value = "";
    pasteMsg("", false);
    ED.replay($("paste").firstElementChild, "pull");
    $("pd-text").focus();
  }
  function closePaste() {
    $("paste").hidden = true;
    $("ob-paste").focus();
  }
  async function loadPaste() {
    var text = $("pd-text").value;
    if (!text.trim()) { pasteMsg("Nothing pasted yet.", true); $("pd-text").focus(); return; }
    $("pd-load").disabled = true;
    pasteMsg("Reading briefing...", false);
    try {
      var r = await fetch("/api/ocor", { method: "POST", headers: { "Content-Type": "application/json" },
                                         body: JSON.stringify({ text: text }) });
      var j = await r.json();
      if (!j.ok) { pasteMsg(j.error || "Couldn't read that briefing.", true); return; }
      closePaste();
      ED.setView("contracts", 3);   // show the new briefing
      ED.refresh();
    } catch (e) {
      pasteMsg("Couldn't reach the FT3000 (is the script running?).", true);
    } finally {
      $("pd-load").disabled = false;
    }
  }
  $("ob-paste").addEventListener("click", openPaste);
  $("pd-cancel").addEventListener("click", closePaste);
  $("pd-load").addEventListener("click", loadPaste);
  $("pd-text").addEventListener("input", function () { if ($("pd-msg").textContent) pasteMsg("", false); });
  $("paste").addEventListener("keydown", function (e) {
    if (e.key === "Escape") { e.preventDefault(); closePaste(); }
    else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); loadPaste(); }
  });

  ED.page({
    tab: "contracts", sub: 3, key: 3, label: "OCOR", el: "pg-ocor", mode: "ocor", back: "3 Contracts · OCOR", list: "ocor",
    update: renderOcor,   // the briefing keeps up even while another page shows
    cursor: cursor, pick: pick, tick: tick,
    enter: function () { $("ob-pc").scrollTop = 0; },
    scroll: function (clicks) { ED.scrollBox($("ob-pc"), clicks); },
    pull: function () { if (S.obClip && !$("ob-clip").hidden) ED.clipPress(S.obClip, (S.ufc || {}).c2pull_n); }   // COMM2 pull: copy, then paste
  });
})();
