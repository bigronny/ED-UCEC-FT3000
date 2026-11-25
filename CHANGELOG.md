# Changes

Each build adds 0.00.01 to the version (shown on the terminal's BIOS screen, on the UFC as a vehicle starts up, and
in the console).

## 3.02.05 - 25 November 2026

- The worked examples the AI is shown for subject files (a person and a batch) use invented names, systems and
  factions.

## 3.02.04 - 25 November 2026

Targets' backstories are now **subject files**: replicant dossiers, the same shape every time.

- **3 Contracts > Active.** A target's panel is its subject file: Affiliation, Contract, Location, Expires, Serial,
  Incept date, Maker, Original function, Status, Retirement bounty, Threat and Last scan, then Background, Implanted
  memory, Behavioural notes and Assessment. The board fills in what the journal says (the serial's number and the
  incept date are made from the name, so they're always the same; the threat comes from the scan, or from the reward
  until there is one). The AI writes the rest. "Known as" sits under the name. A stack of massacres against one
  faction is one **batch file**, its status counting the units still at large.
- **Every reply is checked.** The AI is given the facts and a fixed format (JSON, each part's length, a worked
  example); a reply that doesn't fit is sent back once, saying why, and if it still doesn't fit the panel says so.
- **The first full scan** of a target written before it rewrites its behavioural notes and assessment from the scan
  (marked provisional until then). On foot, LOCATED is reaching its settlement.
- **Long press on the ID picture** (top right) has a target's file written again, on the Active page only. The
  Rewrite button and the Eliminated chip are gone. Dossiers written before this build are kept as they are until
  you do.
- **3 Contracts > History** closes each file with how its contract ended: FILE CLOSED, ESCAPED, CONTRACT WITHDRAWN,
  or RETIRED · UNPAID (killed, but the contract lapsed). The history reads your journals once more, for this.

## 3.02.03 - 24 November 2026

Three new things for flying and navigating.

- **2 Nav > Traj: CIRCLE**, a Heading Alignment Cone after the Space Shuttle's. It puts a tightening turn beside the
  course, 4 km out (2.5 km radius where you join it, 1.5 km where you leave it), then brings you down a 20 degree
  outer glide slope to the destination. OVHD / STRT-IN picks the side, giving the bigger turn or the smaller, from
  where you are when you pick it. The top-down view draws the turn, WP1 (where you join it) and WP2 (where you leave
  it). The side profile is your path unrolled: the reference altitude (14 degrees round the turn, 20 on the glide
  slope), HIGH / LOW, and the descent rate you need. The readouts show the turn still to go and how far in or out of
  the turn you are. All its numbers are together in `web/js/traj.js` (HAC). COMM2 steps to CIRCLE and OVHD / STRT-IN.
- **2 Nav > HSI: exobiology.** While you sample a species with the genetic sampler, each sample shows on the map,
  ringed at its genus's colony range (Bacterium 500 m, Osseus 800 m...); the ring turns amber while you're too close.
  The panel shows how far you are from the nearest sample and how much further to go, and so does the UFC's
  scratchpad when there's no steer-to point. The samples are kept in `exobio.json` in your data folder.
- **2 Nav > Wpt: sharing codes.** Every waypoint, mark and flight plan has a code with COPY, ready to paste into the
  game's chat (FTW1/... for a waypoint, FTP1/... for a flight plan, checked like the attack plan's FT1 code). The new
  **CODE** method loads one, typed, pasted or from the clipboard. Codes your wingmen say in the game's chat are listed
  there too, ready to LOAD with a press. A flight plan goes into your first empty SEQ, and waypoints you already have
  are reused.

## 3.02.02 - 24 November 2026

The first release.

- A **release zip** with Python included: unzip it and double-click **Start UCEC FT3000** - nothing to install.
  `release.py` builds it.
- **LICENSE** (GPL-3.0) and **CREDITS.md**. CMDR Quizengine's Odyssey settlement maps, which the schematics were
  traced from, are credited by name, alongside SrvSurvey, Raven Colonial, Spansh, EDSM and EDDiscovery.
- The project's page, <https://github.com/bigronny/ED-UCEC-FT3000>, is on 4 Setup > Settings and in what the FT3000
  tells Spansh and EDSM.
- Timing log.bat uses the release zip's own Python when it's there, and no longer says the log is beside the program
  (it's in your data folder).

## 3.02.01 - 24 November 2026

- The AI's status ("AI: CLAUDE") is gone from the line along the top; which AI writes backstories, and how its
  login check went, are on 4 Setup > Settings.

## 3.02.00 - 24 November 2026

Getting ready for other people to use it.

- **4 Setup > Settings**, a new page: the journal folder (it counts the journals it finds there), AI backstories
  (AUTO, CLAUDE, CHATGPT or NONE, and a model), VIEW FROM OTHER DEVICES (it shows the addresses to open), GAME
  CONTROLLERS and OPEN THE PAGE AT START. Kept in `settings.json` in your data folder; each takes effect at the next
  start, and RESTART NOW starts it again there and then - the page stays open and picks the new start up. An option
  given on the command line still wins, and the page says so. An About block shows the version, the program's
  folder, your data folder and the Elite bindings file in use.
- AI backstories default to **AUTO**: Claude Code if it's on the PC, else Codex, else none (it was Claude).
- Spansh and EDSM are told what's asking: `UCEC-FT3000/<version> (Elite Dangerous companion)`, with the project's
  page once it has one (it said "personal use" before).
- A README, with screenshots, and this changelog.
- The tests' made-up commander is CMDR Deckard.

## 3.01.00 - 3.01.42

Before this changelog was kept. The terminal as it grew: the mission board read live from the journal, with AI
backstories for targets; the WinWing UFC driven directly (no VoiceAttack), with menus on its displays and Elite's key
bindings looked up by action; Home's case file and session log; Contracts' Active, History and OCOR pages; Nav's
system list and map (Spansh and EDSM, plus your journal), settlement schematics, history, and the Hornet-style
navigation pages - Traj, Wpt (waypoints, marks, flight plans), HSI and Atk (the 2-ship pop-up attack plan and CCRP);
the terminal's BIOS, start-up and changing-vehicle screens; hyperspace; one copy running at a time.

The last builds before 3.02.00 added:

- Your data in `Saved Games\UCEC FT3000`, apart from the program (the first start copies it across from the
  program's folder, leaving the old copies as a backup).
- The board answering only its own page: other websites open in the same browser, and other names pointed at the
  PC, are refused.
- **4 Setup > Controls**: every UFC job on any game controller's button or dial, the UFC's own layout the default.
- **HUD VV** (the HUD designation, renamed, its velocity vector averaged) and **HUD X-B** (up to 10 cross bearings
  on a point, its position fixed from them).
- A stopwatch and countdown timer (HH:MM:SS) at the bottom left of the HSI, worked like the T-6A's.
- Planetary facilities on the HSI (a small TACAN symbol and a dashed 10 km ring each), and KM / NM for its scale.
