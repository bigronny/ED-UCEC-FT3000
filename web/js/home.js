// ED Target Board page - 1 Home: the commander's case file, the local situation and the session log.
(function () {
  "use strict";
  var ED = window.ED, S = ED.S, $ = ED.$, reduce = ED.reduce;
  var HOT = ["War", "Civil War", "Pirate Attack", "Lockdown", "Civil Unrest", "Terrorism"];
  var MONEY = { KILL: 1, BOND: 1, CASH: 1, DONE: 1, TARGET: 1, READY: 1 };
  var BADTAG = { DIED: 1, CRIME: 1, FAILED: 1, ABANDON: 1, INTRDCT: 1 };
  function repLabel(v) {
    if (v === null || v === undefined || isNaN(v)) return "";
    v = Number(v);
    if (v <= -90) return "Hostile";
    if (v <= -35) return "Unfriendly";
    if (v < 4) return "Neutral";
    if (v < 35) return "Cordial";
    if (v < 90) return "Friendly";
    return "Allied";
  }
  function pop(n) {
    n = Number(n) || 0;
    if (!n) return "Unpopulated";
    if (n >= 1e9) return (n / 1e9).toFixed(1) + " billion";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + " million";
    return n.toLocaleString("en-GB");
  }

  function renderIdle(s) {
    var c = s.cmdr || {}, se = c.session || {}, st = s.sit || {}, stx = c.stats || {}, a = !!S.idleShown;
    ED.setText($("cf-name"), c.name || "Unknown", a);
    ED.setText($("cf-ship"), c.ship || "-", a);
    ED.setText($("cf-shipid"), [c.ship_name, c.ship_ident].filter(Boolean).join(" · "), a);
    ED.setText($("cf-mode"), c.mode || "-", a);
    ED.setText($("cf-cr"), c.credits == null ? "-" : ED.cr0(c.credits), a);
    ED.setText($("cf-combat"), c.combat || "-", a);
    ED.setText($("cf-cbar"), c.combat_pct == null ? "" : ED.blocks(c.combat_pct) + " " + Math.round(c.combat_pct) + "%", a);
    var navy = [];
    if (c.fed && c.fed !== "None") navy.push("Fed: " + c.fed);
    if (c.emp && c.emp !== "None") navy.push("Emp: " + c.emp);
    $("cf-navy-row").hidden = !navy.length;
    ED.setText($("cf-navy"), navy.join("\n"), a);
    var rep = (c.rep || []).map(function (r) {
      return (r.who === "Federation" ? "Fed" : r.who === "Empire" ? "Emp" : r.who) + ": " + repLabel(r.value);
    });
    $("cf-rep-row").hidden = !rep.length;
    ED.setText($("cf-rep"), rep.join("\n"), a);
    var pp = c.power && c.power.power ? c.power.power + (c.power.rank ? " · rank " + c.power.rank : "") : "";
    $("cf-pp-row").hidden = !pp;
    ED.setText($("cf-pp"), pp, a);
    ED.setText($("cf-bc"), ED.num(stx.bounties), a);
    ED.setText($("cf-bp"), stx.bounty_profit == null ? "-" : ED.cr0(stx.bounty_profit), a);
    ED.setText($("cf-as"), ED.num(stx.assassinations), a);
    ED.setText($("cf-hi"), stx.highest == null ? "-" : ED.cr0(stx.highest), a);
    ED.setText($("cf-sk"), ED.num(se.kills || 0), a);
    ED.setText($("cf-sb"), ED.cr0(se.bounty), a);
    ED.setText($("cf-se"), ED.cr0(se.earned), a);
    ED.setText($("cf-sj"), ED.num(se.jumps || 0), a);

    // local situation; a jump to a new system gets a focus pull
    var name = st.system || s.system || "Awaiting location";
    var moved = S.lastSys !== undefined && S.lastSys !== name;
    if (moved) ED.replay($("sit"), "pull");
    S.lastSys = name;
    $("st-lab").textContent = "Local situation" + (st.docked ? " · docked: " + st.docked : "");
    ED.setText($("st-name"), name, a && moved);
    ED.setText($("st-all"), st.allegiance || "-", a);
    ED.setText($("st-gov"), st.government || "-", a);
    ED.setText($("st-sec"), st.security || "-", a);
    ED.setText($("st-eco"), [st.economy, st.economy2].filter(Boolean).join(" / ") || "-", a);
    ED.setText($("st-pop"), st.system ? pop(st.population) : "-", a);
    ED.setText($("st-pow"), st.power ? st.power + (st.power_state ? " · " + st.power_state : "") : "None", a);

    var fac = st.factions || [], wars = st.conflicts || [];
    var chips = [];
    if (/anarchy/i.test(st.security || "")) chips.push("Anarchy");
    else if (/low/i.test(st.security || "")) chips.push("Low security");
    if (wars.some(function (w) { return w.status !== "pending"; })) chips.push("Conflict zones");
    if (fac.some(function (f) { return f.states.indexOf("Pirate Attack") >= 0; })) chips.push("Pirate attack");
    var chipSig = chips.join("|");
    if (chipSig !== S.stChips) {
      S.stChips = chipSig;
      $("st-chips").innerHTML = chips.map(function (x) { return '<span class="chip">' + ED.esc(x) + "</span>"; }).join("");
      if (a) ED.replay($("st-chips"), "flk");
    }
    var warSig = JSON.stringify(wars);
    if (warSig !== S.stWars) {
      S.stWars = warSig;
      $("st-war").innerHTML = wars.map(function (w) {
        return "<div>" + ED.esc(w.type) + ": " + ED.esc(w.a) + " vs " + ED.esc(w.b) + " (" + w.a_won + "-" + w.b_won + ")" +
          (w.status === "pending" ? " · pending" : "") + "</div>";
      }).join("");
    }
    var facSig = JSON.stringify(fac);
    if (facSig !== S.stFac) {
      S.stFac = facSig;
      $("st-flab").hidden = !fac.length;
      $("st-fac").innerHTML = fac.map(function (f) {
        var hot = f.states.some(function (x) { return HOT.indexOf(x) >= 0; });
        var rep = repLabel(f.rep);
        return '<div class="fr' + (hot ? " hot" : "") + '"><div class="l1"><span class="fn">' +
          (f.controlling ? "► " : "") + ED.esc(f.name) + "</span><span>" + Number(f.influence).toFixed(1) + "%</span></div>" +
          '<div class="l2"><span class="st">' + ED.esc(f.states.join(", ") || "No state") + "</span>" +
          (rep ? " · " + ED.esc(rep) : "") +
          (f.pending && f.pending.length ? " · next: " + ED.esc(f.pending.join(", ")) : "") + "</div></div>";
      }).join("");
    }
    S.idleShown = true;
  }

  function renderLog(s) {
    var box = $("slog"), lines = $("lg-lines"), log = s.log || [];
    var since = ((s.cmdr || {}).session || {}).since || "";
    if (S.logSince !== since) { lines.innerHTML = ""; S.lastN = 0; S.logSince = since; }
    $("lg-lab").textContent = "Session log" + (since ? " · since " + ED.clock(since).slice(0, 5) : "");
    var fresh = log.filter(function (e) { return e.n > (S.lastN || 0); });
    if (!fresh.length) { S.logPrimed = true; return; }
    var stick = !S.logPrimed || box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    fresh.forEach(function (e, i) {
      var row = document.createElement("div");
      row.className = "ll" + (MONEY[e.tag] ? " money" : BADTAG[e.tag] ? " bad" : "");
      row.innerHTML = '<span class="lt">' + ED.esc(ED.clock(e.t).slice(0, 5)) + '</span><span class="lg">' +
        ED.esc(e.tag) + '</span><span class="lx"></span>';
      lines.appendChild(row);
      var lx = row.querySelector(".lx");
      if (S.logPrimed && i >= fresh.length - 3) ED.typeOut(lx, e.text); else lx.textContent = e.text;
      S.lastN = e.n;
    });
    while (lines.children.length > 60) lines.removeChild(lines.firstChild);
    S.logStick = stick;
    if (stick) box.scrollTop = box.scrollHeight;
    S.logPrimed = true;
  }
  $("slog").addEventListener("scroll", function () {
    var box = $("slog");
    S.logStick = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  });

  ED.page({
    tab: "home", sub: 1, key: 1, label: "Home", el: "pg-home", mode: "idle", back: "1 Home",
    update: renderLog,   // the log keeps up even while another page shows
    draw: function (s) {
      $("home-panel").classList.toggle("none", !!s.note);   // a start-up / journal message in place of the panel
      ED.showNote(s);
      renderIdle(s);
    },
    scroll: function (clicks) { ED.scrollBox($("sit"), clicks); },
    tick: function () { if (S.logStick) { var box = $("slog"); box.scrollTop = box.scrollHeight; } }
  });
})();
