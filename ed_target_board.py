#!/usr/bin/env python3
"""
UCEC FT3000 Field Terminal (ED Target Board)
============================================
A small local web page that lists your current Elite Dangerous missions, read
live from the player journal, with a subject file for each target: a replicant
dossier, its facts from the journal and its story written by an AI.
On screen it's the UCEC FT3000, a field terminal from the Universal Computer
Equipment Corporation. Its version (VERSION, below: shown on the terminal's BIOS
screen, on the UFC as a vehicle starts up, and here in the console) goes up by
0.00.01 with each new build.
It also runs a WinWing UFC for Elite: menus on the UFC display, and option
buttons that press your Elite key bindings (no VoiceAttack needed).

The subject files' stories come from a command-line tool that is logged in with your
SUBSCRIPTION, so no API key and no pay-per-use credits are involved:

  * Claude Pro / Max   ->  Claude Code CLI   (`claude -p ...`)
  * ChatGPT plan       ->  OpenAI Codex CLI  (`codex exec ...`)

AUTO (the default; 4 Setup > Settings) uses Claude Code if it's on this PC, else Codex,
else none - the board works without either, only without the written parts of the files.

Each target's file is written once and cached in target_backstories.json in your
data folder (see Files), so restarting doesn't spend your allowance again.

Requirements: Python 3.8+ (standard library only), plus one of the CLIs above,
installed and logged in once with your subscription account. Keep the web
folder next to this script: it holds the page itself (see "Files" below).

The page has four tabs, each with its sub-tabs (the second row; the UFC's keypad
picks them - see WinWing UFC):
  1 Home                     your case file, the local situation and the session log
  2 Nav        1 Syst        the system you're in (its list and its map)
               2 Traj        guidance down to a planetary facility or one of your waypoints (ENTRY 1)
               3 Wpt         your own waypoints on a body's surface, your marks (MK1-MK9) and flight plans (SEQ 1-3)
               4 HSI         flying a flight plan (or none: any of your points): the steer-to point, AUTO sequencing,
                             the designated target
               5 Atk         the attack plan (a 2-ship pop-up, built round the target) and a mine-release computer (CCRP)
               6 Hist        everywhere you've been
The Nav pages work as an F/A-18C's waypoint system: waypoints and the flight plans that string them together are
separate things (a flight plan is your waypoints in order); marks are quick captures, apart from both; the steer-to
point (where the HSI takes you) isn't the target (what you designate - DSG - and Atk attacks).
  3 Contracts  1 Active      the missions you hold
               2 History     the missions you've completed, failed or abandoned
               3 OCOR        the Legion's daily briefing
  4 Setup      1 Controls    which button or dial, on which game controller, does each of the UFC's jobs
               2 Settings    what the FT3000 starts with: your journal folder, the AI, other devices, controllers

Usage
-----
Everyday settings are on the page, 4 Setup > Settings (see Settings, below); the
command line still works, and an option given there wins over its setting:

    python ed_target_board.py                     # opens http://localhost:8642
    python ed_target_board.py --test              # check your login with one sample subject file
    python ed_target_board.py --engine claude     # Claude Code for subject files (auto: Claude Code if it's here, else Codex)
    python ed_target_board.py --engine codex      # use ChatGPT (Codex CLI) instead
    python ed_target_board.py --engine none       # mission board only, no AI
    python ed_target_board.py --model haiku       # lighter Claude model, stretches your allowance
    python ed_target_board.py --host 0.0.0.0      # view it on a phone/tablet on your network
    python ed_target_board.py --journal-dir "D:\\Saved Games\\Frontier Developments\\Elite Dangerous"

To stop it: Exit on the web page, close its window, or Ctrl+C there. Closing the page
alone leaves it running - so each copy, as it starts, first closes one still running
from before: whatever FT3000 answers on its port is asked to stop as Exit does (it
blanks the UFC as it goes), and one that doesn't answer - hung, or on another port -
is ended, if ft3000.pid (written in your data folder while a copy runs) shows it's
the FT3000 that this folder started. On Windows, its port is its own: a second
program can't quietly share it (as Python's usual way of opening a port there
allows), so the page always reaches this copy.

OCOR briefing (Contracts > OCOR)
--------------------------------
Press [ Fetch briefing ] on Contracts' OCOR page and paste your squadron's daily OCOR
briefing from Discord (either "Copy Text" from the message menu, or a normal
select-and-copy). The objectives are listed by system under their section
(Priority One, War, Influence work... - a section is a line in capitals, a
Discord heading, or a "Priority ..." line), and the details show when you select
one. Both layouts the briefing has used work, plain or with names in bold. Objectives
struck out in the briefing are marked Done (greyed and struck through here too),
and the UFC knob skips them; this needs "Copy Text", as a normal copy loses the
strike-through. Beside each system is its distance from the system you're in
(straight line) and roughly how many jumps that is at your ship's maximum jump
range, e.g. "~5 jumps". Your position comes from your journal; the briefing
systems' coordinates come from Spansh, then EDSM for any Spansh doesn't know (as
the System list's Spansh Uplink and EDSM Uplink toggles allow), asked only while
a page shows the OCOR page, and only for systems not already in star_coords.sqlite
(in your data folder). That file keeps every system's coordinates for good, from
those and from your own jumps; it stays fast however large it grows. The last paste is
kept in ocor_briefing.json in your data folder (the text and the time you
pasted it), so it survives a restart and shows on every device viewing the
page. "Fetched ... ago" above the button turns red after 12 hours.
Beside a system's name in the details - an objective's system on OCOR, a
contract's Location on Contracts, a place's system or a finished mission's
destination on the history pages - is COPY: press it and the name goes on this
PC's clipboard (from any screen, the phone included), and it turns to PASTE;
press it again within two minutes and it pastes the name into Elite (Ctrl+V -
into the galaxy map's search box, with that box selected), if Elite is the
active window, as it stays when you press it from the UFC: on OCOR and Contracts'
Active page a short COMM2 pull (page menu) presses it (on the history pages, COMM2
steps to it first). From the page on the PC itself, Elite
isn't in front, so paste it there with Ctrl+V yourself.

System (Nav > Syst)
-------------------
CURRENT SYSTEM / REMOTE, under the system's name: the system you're in - or a remote one,
picked to look at and plan in: its bodies and stations here and on the map, and on the Nav
pages (Wpt, HSI, Atk, Traj follow 1 Syst) its waypoints, flight plans, times on target and
attack plans, all kept for when you get there. REMOTE opens a list: MANUAL first - a name,
typed on the UFC's keypad as a waypoint's NAME (2 and 8 step the letter under the cursor,
4 and 6 move the cursor) or the keyboard, with the matching systems under it (those you know
of, and Spansh's search) - then your plotted route's destination, your active missions'
systems, OCOR's objectives, the systems you've been in lately and those picked lately, each
with how far it is. 1 Syst stays on it through any number of jumps until you switch back to
CURRENT SYSTEM - or until you arrive there, when it simply is the current system. While it's
remote its name is amber here, on the map and in the strip along the top; what needs you
there doesn't work - AUTO shows its main star, OVERFLY, HUD VV, HUD X-B and MK (they mark where you
are), Atk's AUTO heading (set ATK HDG), the HSI's and Traj's live guidance (they show the plan).
On the UFC, COMM1's first stop on the System list (above the first row) is the switch: a pull
opens the list (on a remote system: back to the current one). While the list is open, COMM1
moves through it and a pull - or ENT - picks; on MANUAL it starts the name, and then COMM1
moves through the matches; CLR clears the name, again stops typing, again closes the list.
Kept in remote_system.json in your data folder.
The system you're in, from Spansh (spansh.co.uk) and your own journals, with
EDSM's (www.edsm.net) traffic, deaths and exploration value: the bodies in orbit
order with their stations under them (Spansh doesn't say which body an orbital
station orbits, so it's matched to one by distance and marked "est."; a surface
station is on its planet, at its position), with each one's
details and a rotating dashed wireframe - planets show their settlements at
their real positions, and you as a cross. AUTO follows you: docked -> that
station; on or low over a planet -> the nearest settlement; higher up -> the
planet; otherwise your current target (read from Status.json). Picking anything
yourself switches to MANUAL. Tap the picture to grab it, drag to turn it, tap
again to let go; tap a settlement marker to select it. "Commanders here" shows
EDSM's traffic (green) and your own visits from your journals (amber). The
picture is drawn in coarse pixels, each the size of one of the text's, with
one-pixel lines and no smoothing, as a VGA screen would show it; maximised, it
has more of those pixels rather than finer ones.

LIST / MAP at the top switches to a map of the whole system across the full
width, laid out like the game's system map: the main star on the left, the
bodies orbiting it along a line in orbit order (belts first), moons hanging
below their planet, the next level out to the right, orbital stations beside
their body and fleet carriers as one marker (x count) under the main star.
Stations, carriers, megaships, installations, beacons and construction sites are
shown by their List view icon in a circle (the icon grows in whole pixels as you
zoom in; zoomed right out, just the circle and a dot); stars, planets, moons and
belts are wireframes.
Bodies sharing a barycentre are bracketed together. Every star and planet type
has its own wireframe (gas giant classes by their bands; rocky, icy, metal,
Earth-like, water and ammonia worlds by craters, cracks, continents, waves or
storms; stars by class, with brown dwarfs, T Tauri and Herbig discs,
Wolf-Rayet shells, carbon stars, white dwarfs, neutron stars and black holes
drawn differently). Each body spins at its real day length, all sped up alike
(1 day = 3 s; the fastest are capped), about an axis leaning by its axial tilt.
Landable bodies have a solid ring, with amber squares for settlements and
triangles for ports and outposts. Sizes are compressed so moons and stars both
fit. The map scales to the screen: it fills the height, or shows a small
system whole across the width. Drag (or use the mouse wheel) to look around;
- and + zoom (as do Ctrl+wheel, pinching and the UFC's COMM1 VOLUME dial), double-click to fit it again; tap
a body or station to open its details. The map is drawn in coarse pixels
(about two screen pixels each, a little finer than the picture's, so names stay
readable), with hard edges and no smoothing; its lettering stays sharp rather
than blocky. What's selected (AUTO's pick, or yours)
has bright green corners round it, a surface site's on its planet; the UFC
cursor has amber ones. Under each planet's number (before a
moon's) a symbol shows its type: gold bars for metal-rich (three) and high
metal (two), a rock, rock and snowflake for rocky ice, a snowflake for icy, the
Earth, a water drop, an ammonia flask, a banded ball with its class for gas
giants, a balloon for helium giants, a leaf for life-bearing giants (green
water-based, amber ammonia-based) and a banded drop for water giants. KEY
explains the symbols. Where a system's data comes from is up to the two toggles
at the bottom of the System list, SPANSH UPLINK and EDSM UPLINK (kept in
uplink_settings.json; on the UFC, the list's last two COMM1 stops, after the
uplink button: a COMM1 pull flips one). Both on (as EDDiscovery's "Spansh then
EDSM"): bodies and stations from Spansh - one record, looked up by the system's
64-bit address (your journal gives it; otherwise Spansh's search, by name), with
each station's landing pads, position, economies and services, and each body's
signals - and from EDSM only where Spansh has nothing for the system (or can't be
reached); EDSM's traffic, deaths and exploration value either way. Spansh alone:
no traffic, deaths or value. EDSM alone: its bodies and stations (it says which
planet an orbital station orbits; Spansh doesn't). Both off: your journal records
alone. Spansh's record includes market prices, but they're thrown away as it
arrives: none are kept. The parts are fetched together, at most once an hour: on
arriving (unless the copy kept in edsm_cache.json in your data folder is under an
hour old), again when the hour is up, while you're in hyperspace for where you're
going, and when you change a toggle. If any part fails, the copy shown stays as it
was and it tries again a minute later. The systems you've been in have their last
copy kept for good (system_archive.sqlite), so revisiting one shows it even if
neither site can be reached; others are kept a week. --no-spansh and --no-edsm
start the matching toggle off, for that run.
System Data Uplink Synchronise, the button under Commanders here, fetches them
now ("Uplink in progress" for a moment, then "Synchronised", or "Uplink failed"
in amber if Spansh or EDSM can't be reached); it can be pressed once a minute, and
is dimmed in between. Under it, "Last uplink" gives the date and time of that
system's last fetch (in this PC's time), with "Spansh unreachable" (or EDSM) if
the last try failed. On the UFC, the button is the System list's COMM1 stop after the
last row (COM1 goes blank): a COMM1 pull presses it.
The top right of the details says where the selected item comes from: Spansh
(or EDSM), Spansh + your journal, or From your journal only. A body's details
give the date and time the site last heard about it ("Spansh updated") and, at the
bottom, Spansh's signals on it (biological, geological, human, mining sites...)
and the biology genuses found there; a station's, separately, its information,
market, shipyard and outfitting ("-" for a service it doesn't have), and its
landing pads (small, medium, large). A station Spansh knows only from someone
approaching it (no type) is a settlement of some kind, as one your journal knows
that way is (see Settlement schematics). Your journal wins where it knows better
(as EDDiscovery's does, except for what changes): a body you've scanned takes your
scan's figures and is ticked (a tick after its name in the list and on the map,
"Scanned by you" in its details); a station takes your journal's type, landing
pads and position always, and its faction, government, economy and services if
your journal's are newer than the site's. Where neither site has anything - a
system, a body or station, or a settlement's position - the tab uses your own
journals instead: the bodies you've scanned, the stations you've docked at, the
installations and beacons you've picked up, and where each settlement is (the
journal notes its planet, latitude and longitude as you approach one). These are kept for good in journal_records.sqlite next to this
script; the first run reads all your old journals for them, in the background.
Anything from your journal says so in its details. Fleet carriers aren't kept
(they move), and a megaship only your journal knows of is shown for a week.
With both toggles off the tab shows your journal records alone.
Each entry in the list has an icon for what it is, after the game's system map:
a sun for stars, a circle for planets (filled if you can land), and each kind of
station, settlement, carrier, megaship, construction site, installation and
beacon its own. A construction site is listed by its own name ("Qiao Hydroponics
Range", not "Planetary Construction Site: Qiao..."), its kind in the details.

Settlement schematics: select an Odyssey settlement (or a planetary construction
site) and press SCHEMATIC VIEW (under the picture). The planet turns the
settlement to the middle and zooms in on it, and the first layout plan for its
type appears. Its type starts as its economy; where that has no layouts (a
construction site's economy is "Colony"), what its name says ("... Hydroponics
..." is agriculture, "... Bastion" military), or else the first type that has
some - the note under the button says so. A surface station known only from
someone approaching it - your journal's ApproachSettlement, or Spansh's record
with no type (approaching doesn't say what kind it is: an Odyssey settlement, or
a planetary port, outpost or older settlement) - shows
SCHEMATIC VIEW as a station with none does - greyed, no note, and no highlight
when the UFC's COMM2 knob stops on it - but it still opens its schematics (a
click, or a short COMM2 pull on that unhighlighted stop), by its economy. Once
you confirm a layout for it, or its type turns up (docking there, or Spansh
listing it with one), the button is an ordinary one. Maximised, TYPE (beside the icon
toggles) steps through the types that have layouts, for any settlement; your
choice is kept for that settlement (settlements.sqlite) until you step round to
its own type again. Step through them with
the arrows until one matches what you see, and press CONFIRM LAYOUT: next time,
that settlement opens straight on it, its name followed by SET (SET LAYOUT to pick
again). Confirmed layouts are kept for good in settlements.sqlite in your data folder, keyed by the
settlement's market ID. PLANETARY VIEW zooms back out. MAXIMISE enlarges the
picture (planet or schematic) in place of the details; selecting anything else
returns to the small picture of the planet. Only stars, planets and moons and
things on the ground (settlements, planetary ports and outposts, their
schematics) maximise and zoom; an orbital station, carrier, megaship, beacon or
installation just turns. The UFC's COMM1 VOLUME dial zooms (clockwise in) a
planet, star or schematic, and the system map; so do the mouse wheel and
pinching (double-click for the whole of it again). The UFC's three dials work as
speed controls (see WinWing UFC). A planet (or station) spins on its own until
you turn it with COMM2 VOLUME or tilt it with BRT: from then on it stays where you
leave it, so a settlement holds still to be picked, until you select something
else and come back, double-click it, or give a 2-second COMM2 pull with no
settlement under the cursor - the whole planet again, spinning on its own.
True-scale descent: small or maximised, a planet or moon zooms on past its own
size, down to a settlement at its real size and into its schematic. A fifth of the way down
it settles on the selected settlement (with the planet selected, the one nearest
the middle of the picture), stops spinning and turns it to the middle; the grid
gets finer as you go (30, 10, 5, 2, 1, 0.5, 0.2, 0.1 degrees and on), the label
under the picture giving its spacing and what that is on this planet ("Grid 0.1°
(≈ 1.4 km)"); settlements show at their real size once they're bigger than a
marker - one with a confirmed layout as its schematic, in its real place (north
up where its heading is known), once that's 8 screen pixels across: under 24
pixels with its yellow box over it, under 8 the yellow box alone (the others as
a box their real size); and where the settlement's marker is as big as its
schematic drawn whole, the schematic takes over (its details replace the
planet's) and zooms on to 8 times. Zooming out goes back up the same way. Each
settlement is drawn at its real size: a plan's site_m block gives every shape
and icon in metres (see below); an older plan with only "scale": {"m_per_px":
...} (metres per pixel of its picture) uses that, and one with neither is taken
as 1 km across. A star zooms to 8 times. Maximised, a range bar in the bottom
left corner gives the scale (at the middle of a planet or star): a round length
in metres and km near the ground, megametres (Mm) from 1,000 km and light-seconds
(ls) past 30 Mm, as the game gives distances.
A schematic starts looking
straight down: the BRT dial tilts it to show the buildings' heights, the COMM2
VOLUME dial turns it, and dragging it does both. Which way a settlement faces
(its heading: the compass bearing of its layout's up) is kept for its confirmed
layout, in settlements.sqlite. Docking on a pad gives it: your ship's heading
(Status.json) less that pad's turn from pad 1 (SrvSurvey's pad directions; every
pad 1, and the other pads with a recorded rotation - a pad without one is
ignored). Or set it yourself: with the layout confirmed, ALIGN LAYOUT
maximises the picture, frames it and puts CANCEL and CONFIRM HEADING over it. In
that mode the way you face stays up the picture (it turns as you turn) and its
tilt follows your height and distance from the settlement (up to 70°, until you
tilt it yourself); turn it (COMM2 VOLUME, or drag) until it matches what you see,
and CONFIRM HEADING keeps it - CANCEL puts the picture back. A heading you set
after a docking had set one takes priority: later dockings there are ignored
(confirming a different layout starts afresh, from your last docking there).
With its heading known, the schematic opens with the way you face up when you're
there (north up otherwise, and on the way down from the planet), the label under
it gives the compass bearing of the top of the picture ("Up 090°"), where the
heading came from (from pad 2, aligned) and how far away you are, and you show
on it as an arrow the way you face (at its edge, pointing to you, when you're
off the picture). To move across it, grab it (a
short COMM2 pull with the picture highlighted): then VOLUME pans across and BRT up
and down, a 2-second pull shows the whole settlement again and another short pull
lets go. With a mouse: the wheel zooms where the pointer is, right-drag (or Shift
and drag) pans, double-click shows the whole settlement; on a touch screen, pinch
and move two fingers. Maximised, MINIMISE, PLANETARY VIEW, the layout (its name and
SET), SET LAYOUT and ALIGN LAYOUT run along one line under the picture (no layout
description is shown while you pick), and the icon toggles show those icons (all off to
start with): TERMINALS (T a data terminal, T+ one above security level 0; AU,
PE, SH and TU the authorisation, personnel, ship and turret terminals), DOORS
(airlocks red, other doors green, numbered by security level), POWER/ALARM (P
and A, and AT for SrvSurvey's "Atmos" points - it doesn't say what they are),
EXPENDABLES (+ medkits, B batteries, i.e. energy cells; SrvSurvey records no
ammunition) and CZ (Frontline Solutions combat-zone points, in rings:
A to F the checkpoints, P the power posts). A ^ after an icon's letters puts it
one floor up (^^ two). Maximised, each landing pad shows its number and size
(L2: pad 2, large), numbered as the game numbers them when it grants docking.
The plans are the .json files in the schematics folder next to this script, one
per layout; add more and they appear. Each file's "category" is the settlement's
economy (tourism, agriculture, military, industrial, extraction, high tech) and
its "name" the layout's Raven Colonial name (Fufluns, Picumnus, ...). The plans'
site_m blocks were fitted to SrvSurvey's measured positions (pads, doors,
terminals, consoles) and carry SrvSurvey's doors, terminals, loot and
combat-zone points too, in its frame: metres from the settlement's position,
with the site's heading up (the journal doesn't give a settlement's heading:
docking or Align layout does, above), and each pad's rotation_deg (its turn
from pad 1). Heights are estimates.

Hyperspace jumps: whichever page is showing, a jump (the journal's StartJump)
swaps the page for a hyperspace overlay until you arrive. The page
judders and blurs as the drive fires, then wavy candidate routes struggle
between the two stars (failed ones turn amber and pull back) inside a folded
"hourglass" whose width follows the paths' spread (two standard deviations), so
it starts wide and messy and narrows as they settle; then one route locks and
your marker travels along it. Meanwhile the destination's bodies and stations
are fetched from Spansh (and cached, so arriving needs no second fetch) and its
system map scans in - drawn by the same code as Syst's map (the system
map drawing, mapdraw.js). Both stars are drawn at the map's own scale and style. The
departure star comes from your journal's auto-scan of it when you arrived, or
Spansh; the destination from Spansh, or - until it answers, or if it doesn't know
the system - a typical star of the class the game gives (marked ~ and amber).
The fuel bar shows the tank, the slice the jump should burn (from your own
recent jumps with this drive, or the drive's standard figures for an
unengineered one; otherwise "known after a jump") and, on arrival, the exact
amount used from FSDJump. Out of hyperspace "Arrived" and the system's name show
in the corner of its map, and then it goes back to the page you were on (Syst in list or map, as you left it). Jumps in
an Apex taxi show no fuel. If you cancel the countdown, the overlay closes
about 25 s later. Like the map, it's drawn in coarse pixels (the stars, routes,
wireframes and the route-finding screen), with its lettering kept sharp.
Data used: StartJump, FSDJump, FSDTarget, Loadout, Cargo, the arrival Scan,
NavRoute.json and Status.json (fuel and the FSD flags).

The terminal (UCEC FT3000)
--------------------------
Opening the page powers the terminal on: black for 2 s, then the tube warms up
(static that brightens unsteadily, rolling and juddering), then it snaps to the
UCEC boot screen with the company's logo - the Milky Way in dots, UCEC slanted
underneath. If you're not in the game (at the main menu, or it isn't running),
it then shows light static under a box reading UCEC FT3000 / WAITING FOR INPUT
SIGNAL, and stays like that until you're actually in your ship (or SRV, fighter,
on foot), when it snaps to that vehicle's start-up and then the board. If you're
in the game already, it goes straight from the boot screen to your vehicle's.
Going back to the main menu or closing the game later breaks the picture up into
static, switches the tube off (the picture shrinking to a line, then a dot) and
shows the waiting box again. Tap anywhere (or press Esc) to skip to
the board at any point; if you then load in, the usual start-up plays.
The faint band sweeping down the screen belongs to the steady, connected picture
(like a little interference in the cable), so it only runs while the board shows.
Whether you're in the game comes from the journal: loading a save (once
Status.json shows you in, as below), the main menu (the Music event's MainMenu
track), closing the game (Shutdown) and starting it again (a new journal).
To see the waiting screen without leaving the game: http://localhost:8642/#nosignal

Changing vehicle
----------------
Leaving your ship, SRV, Nomad or fighter plays a "disconnect" on the page
(static that tears in as the signal is lost, a little different every time; the
tube stays on - switching off is for leaving the game).
Arriving plays a start-up: warm-up static, then that vehicle's boot screen -
ship, SRV, Nomad and fighter each look like a different maker's BIOS. Arriving
on foot is the static alone. The UFC's displays keep in step with the page (see
WinWing UFC). Loading the game starts up wherever you are, once
you're actually in: the journal's LoadGame is written while the loading screen
is still up, so it waits until Status.json (rewritten since then) shows you in
your ship, SRV, fighter or on foot - or a minute, if it never does. From the
terminal's waiting screen it snaps straight to the boot screen.
Journal events used: LoadGame, Embark, Disembark, LaunchSRV, DockSRV,
LaunchVessel (the Nomad), LaunchFighter, DockFighter, VehicleSwitch and
FighterDestroyed. An Apex taxi or another player's ship plays nothing.
To preview, add one of these to the address, e.g. http://localhost:8642/#boot-srv
  #boot  #boot-srv  #boot-nomad  #boot-fighter  #boot-foot      (start-ups)
  #exit-foot  #exit-srv  #exit-nomad  #exit-fighter  #exit-ship  (leave, then arrive)
  #nosignal                                                     (the game lost: the waiting screen)
Tap the screen to skip.

Contracts (Contracts > Active)
------------------------------
Every mission you hold, soonest to expire first. Assassinations (including on-
foot ones; a named Target) and massacres (a KillCount, where the target is the
enemy faction) are "targets": grouped by target (a stack of massacres against
one faction is one entry), with ship scans and a subject file (below).
Every other mission - courier, delivery, source and return, mining, salvage,
passengers, rescue, donations, on-foot work and the rest - is one entry each,
named by what it's about ("240 x Tea", "4 passengers", "Data to Jameson
Memorial"; an on-foot delivery or collection for a named person is "Package to
..." / "Package from ...", and that person is a contact, not a target) with its
type above, and shows its destination, issuer, reward, expiry and status (cargo
collected / delivered from the journal's CargoDepot updates; "Hand in at ..."
once the objective is done), then the details: the mission's own description,
the recipient or contact, passengers, influence and reputation, wing, and when
you accepted it. No subject file for these. A mission the game lists at login but
that was accepted before the journal files read (--days) shows its type and
expiry only. COPY beside Location copies the contract's system, then pastes it
into Elite (see OCOR briefing, above).

Subject files (Contracts > Active)
----------------------------------
Each target is a replicant gone off its lease, and its panel is its subject file
(the setting: DOSSIER_SETTING, below). A person has a file of its own; a stack of
massacres against one faction is one batch file, for the units made together that
now serve it. The board fills in what the journal says: Affiliation, Contract (and
who issued it), Location, Expires, Serial (N31, the AI's letters for sex and grades,
and a number made from the name - always the same), Incept date (so long before you
first took the contract; they live four years), Status (AT LARGE; LOCATED once
it's scanned - on foot: once you reach its settlement; RETIRED once it's killed;
a batch: how many units are left of the most any one issuer wants), Retirement
bounty, Threat (from its rank and ship once scanned - "confirmed by scan" - else
from the reward: provisional) and Last scan (on foot: Located). The AI writes the
rest - Known as, Maker, Original function, Background, Implanted memory,
Behavioural notes and Assessment - as JSON with those keys and no others, each of
its length (DOSSIER_FIELDS). Every reply is checked; one that doesn't fit is sent
back once, saying why, and if the second doesn't fit either the panel says so. A
target scanned for the first time after its file was written has its behavioural
notes and assessment written again from the scan (until then they're marked
provisional); the rest stays. Files are written once and kept; holding the ID
picture (top right of the panel) for a moment has a target's file written again -
on the Active page only. A dossier written before 3.02.04 (a paragraph of prose)
is kept as it is, unless you have it written again.
On Contracts > History a target's file closes with how its contract ended:
FILE CLOSED (completed), ESCAPED (failed), CONTRACT WITHDRAWN (abandoned), or
RETIRED · UNPAID - killed, but the contract lapsed before you handed it in.

History (Nav > Hist, Contracts > History)
-----------------------------------------
Everywhere you've been and every mission you've finished, from all your journals:
the first run reads every journal you have (in the background - the pages say how
it's going), and keeps what it finds for good in journal_records.sqlite (beside
the System records); every new event adds to it. Each page has toggles above its
list, and under them the totals of what's switched on; the toggles last while the
board runs and are as they start when it starts again.
Nav > Hist: a log, newest first, a line for each day. Each jump into a system is a
row, with the places you went there under it, in the order you went: stations
docked at, planets you dropped into orbital cruise round or landed on, and
settlements and planetary ports or outposts you came within range of. An icon
beside the word on the right says how you were there: in orbit, landed or docked.
(A place in a system your journals have no jump into - where a session started -
sits under that system without one.) SYSTEMS, STATIONS and PLANETARY (planets,
settlements and planetary ports) switch each kind on or off; with SYSTEMS off the
places are listed alone, newest first, each with its system. Selecting a row shows
its place: a picture (the planet with its settlements and where you landed, the
station's wireframe, or a settlement's layout if you've confirmed one), COPY for
its system, when you were first and last there, how many times (each arrival in the
system counts once), what the journal said of it on your last visit (faction,
government, economy...) and all your visits there.
Contracts > History: every mission completed, failed or abandoned, newest first,
like Active's list (COMPLETED to start with; FAILED and ABANDONED add theirs).
Selecting one shows how it ended and when, what was paid (credits, and any
commodities or materials), its destination (with COPY), the details from when you
accepted it, and a target's subject file (see Subject files). One accepted before your
oldest journal still shows, with what its ending said.
Journal events used: FSDJump, CarrierJump, Docked, ApproachBody, Touchdown (yours,
not the ship landing to pick you up), ApproachSettlement, MissionAccepted,
MissionRedirected, MissionCompleted, MissionFailed and MissionAbandoned.

Your waypoints (Nav > Wpt)
--------------------------
Places on a body's surface of your own - a mission's crash or impact site (the game
gives no position for those: not in the journal, not in Status.json), or anywhere
you mean to go back to - kept for good in settlements.sqlite in your data folder
(with your confirmed layouts and headings) until you delete them. Each is numbered
within its system from 1, with no gaps (delete one and those after it move down one),
named by you or "WPT n - <body>" (a name of that kind follows its number), and appears in Nav > Syst under its
body (its own icon, and a green diamond on the planet's picture): select it there
and Traj's 1 SYST SEL guides you to it. Any body but a star. The page is the Hornet's HSI >
DATA > WYPT: on the left, how to make one (lit while its panel is open), then this system's
waypoints by body (each by its number - WP3 - and name; its position is on the right), your
marks (MK1-MK9) and the three flight plans (SEQ 1-3); on the right, the method's controls, or
what's selected; along the bottom, the flight plan the HSI flies (> the steer-to point, the
target boxed):
  MANUAL: the body - 1 SYST SEL (what Syst has selected: the body itself, or the one
  a station, settlement or waypoint is on) or DEST (the body your target in the
  game is, or is on: Status.json's Destination) - then a name (left blank: "WPT n -
  <body>") and its latitude and longitude in decimal degrees, as the game writes
  them (26.9707, -59.7420); SAVE WAYPOINT takes two presses (it turns to CONFIRM).
  With a keyboard, type in the boxes (a minus, or N S E W, for the hemisphere). On
  the UFC: COMM2's pull on a box starts it, ENT takes it and moves on (name,
  latitude, longitude, SAVE WAYPOINT), CLR clears it (again: stops). A name works like
  an arcade's high-score table: 2 and 8 step the letter under the cursor up and down
  (A-Z, 0-9, hyphen, space), 4 moves the cursor back and 6 forward. The coordinates
  work as on an F/A-18's UFC: the first key is the hemisphere (latitude N = 2, S = 8;
  longitude E = 6, W = 4), then the digits fill the box with the decimal point
  already placed (DD.DDDD, DDD.DDDD). ENT presses SAVE WAYPOINT too (and CONFIRM).
  The scratchpad shows what you've typed. While you type, or SAVE WAYPOINT is
  highlighted, the keypad doesn't change sub-tabs (the NAV button still does).
  OVERFLY: from orbital cruise down, the body and the latitude and longitude
  beneath you (and your altitude), live - Traj's filter, carried on to the moment,
  not the last reading (up to a second old) - and MARK makes that point a mark at once.
  HUD VV (once HUD DESIG): where a line from you meets the ground - along your heading
  (the way your nose points, from Status.json) at your flight-path angle (your descent
  against your ground speed: Status.json has no pitch, so the angle is the way
  you're moving) - over the level of the ground beneath you, allowing for the
  planet's curve; live, with its range and your heading and flight-path angle.
  Put the target under the mouse widget's dot and fly steadily at it, descending
  (flight assist on, no sideways or vertical thrust), and DESIG makes the point a mark
  at once, and designates it (the target). Once you've held it steady a moment, the point
  is the average of the last 3 s of them, and the range shows how far they wander about it
  (+-; amber when that's large); UNSTEADY: your flight-path angle wandering in them. LOW: the
  game's altitude is from the ground beneath you (low down) - so a slope under you reads as
  climbing or descending and skews the range, which the +- can't show. The closer and
  steeper, the better (a few hundred metres out from 3 km up in a 20 degree dive, less lower
  down); ground higher or lower than beneath you puts it short or long. Climbing or level:
  "Path not descending".
  HUD X-B: cross bearings - no altitude, flight-path angle or ground height in them. Put
  the dot on the target and TAKE BEARING (your position and heading: the line across the
  ground from you to it), then again from somewhere 60-90 degrees round it, at any height,
  level or diving. Two bearings: where they cross; three or more: the point nearest them
  all, each weighted by its range (a degree's error is wider further off). It shows the
  point, how far out it may be (+-: a degree on each bearing - the game's heading is whole
  degrees - or as far as they really miss, if that's more), the widest angle between the
  lines (under 30 degrees: amber - take one from further round), and where it is from you;
  each bearing, newest first, with how far its line misses the point (amber: well off the
  rest - a bad sighting?) and DEL. Up to 10 are kept (an 11th: the oldest goes); they're
  the board's, on the body they're taken on (one taken on another body starts again),
  until CLEAR ALL (twice). DESIG makes the point a mark at once, and designates it.
  CODE: a waypoint or flight plan from a wingman, as a code (below) - type or paste it in the
  box and LOAD (the box empty: LOAD takes this PC's clipboard), or LOAD one heard in the game's
  chat: any code said to you there (by your wing, a friend, in the system - not by NPCs) is
  listed, newest first, with who sent it, what it is and when (this run only; the newest 8). A
  waypoint code adds the waypoint (made: Code), unless you have one there already; a flight
  plan code adds its waypoints the same way and puts them, in order, in your first empty flight
  plan (SEQ 1-3; none empty: it says so - clear one), and shows it; Atk's plan code loads as on
  Atk. A code for a body that isn't in this system is refused, and so is a mistyped one.
  Codes: each waypoint, mark and flight plan shows its own, with COPY (again within 2 minutes:
  pasted into Elite - its chat box, say), to send to your wingman: a waypoint or mark is
  FTW1/<body>/<lat>,<lon>,<name>/<check>, a flight plan FTP1/<body>/<lat>,<lon>,<name>/...
  /<check> (up to 20 points). The name's left out where it's the usual "WPT n - <body>" (the one
  loading it numbers it), and slashes and commas are taken out of names; the check is 4 hex
  digits of a CRC of the rest, as Atk's FT1 plan code, so a mistyped code is refused.
  A waypoint: its body, position, how and when it was made, its offset aimpoint and the
  flight plans it's in; EDIT (its name and coordinates, as MANUAL's - the body stays),
  DESIGNATE (it's the target; again: its offset aimpoint, if it has one; again:
  nothing), OFFSET (O/S: a range in metres and a bearing from it - the building you're
  after, where the waypoint is the settlement), and DELETE, then CONFIRM DELETE (or CANCEL).
  A mark: MK1-MK9 are quick captures - OVERFLY's MARK, HUD VV's and HUD X-B's DESIG, the UFC's MK
  from any page - each taking the next slot, round to MK1 again after MK9 (the Hornet's
  markpoints); steer to them and designate them, but they're not in flight plans until
  STORE AS WP keeps one as a waypoint. DESIGNATE, STORE AS WP, DELETE.
  A flight plan (SEQ 1-3): your waypoints in order, all on one body, each once. Pick one
  in it and INSERT puts the waypoint whose number you type in ADD WP # after it (none
  picked: at the end), the up and down arrows move it up and down the plan, REMOVE takes it
  out; ACTIVATE SEQ makes it the HSI's (the steer-to point: its first - then it reads SEQ
  ACTIVATED); CLEAR PLAN (twice) empties it. Deleting a waypoint takes it out of its
  flight plans. Only here is a plan put in order (the HSI flies it as it is).
  Time on target, as the Hornet's HSI DATA / WYPT page: each plan has its own TGT - SET TGT
  makes the picked waypoint the plan's (boxed in it; again: none), apart from the target you
  designate (DSG: red) - then its TOT, the Zulu (UTC: the game's clock) time to be over it
  (HH:MM:SS), and GSPD, the ground speed (knots) for the last leg, from the waypoint before it
  (the IP) to the TGT. TOT and GSPD can't be set without a TGT. Plans sharing waypoints keep
  their own. The HSI then times you to it (see HSI).
On the UFC (page menu), COMM1 steps through the left panel (MANUAL, OVERFLY, HUD VV, HUD X-B, CODE,
your waypoints, marks and flight plans) and a pull picks one; COMM2 steps through the right panel's
controls and a pull presses one; DSG (Opt4) designates what COMM1 has highlighted. In a flight
plan, COMM2 steps through its waypoints, ADD WP #, SET TGT, TOT, GSPD and the buttons: a pull on
a waypoint grabs it (picked, and lit) - COMM2 then moves it up and down the plan, and a pull
lets go; on ADD WP #, TOT and GSPD the keypad types (shown on the scratchpad: TOT's digits fill
HH:MM:SS), ENT (or a pull) takes it and CLR clears it (again, with nothing typed: clears the
plan's TOT or GSPD). In HUD X-B, COMM2 steps through TAKE BEARING, DESIG, CLEAR ALL and the
bearings (a pull on one deletes it); in CODE, through LOAD (the box empty: the clipboard) and the
codes heard in chat (a pull loads one); a waypoint's, mark's and flight plan's COPY is the last of
their buttons. ENT opens
what COMM1 has highlighted on the UFC, as the Hornet's UFC pushbutton does: the option windows
take its fields - a waypoint: POSN NAME O/S DEL; a mark: POSN STOR DEL; a flight plan: INS
AFT DEL CLR ACT. Press one (the ':' goes beside it) and type: POSN the latitude then the
longitude (ENT with nothing typed keeps it), NAME as above, O/S the range then the bearing
(a range of 0: none), INS / AFT / DEL a waypoint's number (INS puts it after AFT's - 0: at
the start - and stays open for the next; DEL takes it out); ENT takes it; DEL and CLR take
two presses (CONFIRM); STOR and ACT act at once. CLR clears what's typed, again stops typing,
again closes the sub-level. The page shows the sub-level as the UFC does, under the panel.

HSI (Nav > HSI)
---------------
The page you fly a flight plan from, as the Hornet's HSI: across the top, SEQ - the flight plan
activated (NONE, SEQ 1-3, or ATK once Atk has built its plan) - and AUTO / MAN sequencing, then
the steer-to point and where it is in the plan. NONE: no flight plan - steer to any of your
points (none is activated until you activate one). The map: you in the middle with the compass rose round you (track
up or north up), the plan's legs and points (ATK: your track solid, your wingman's dashed),
the steer-to point bright with a line to it and its bearing pointer on the rose, the target
(a red diamond; at the rose's edge when it's further out), your other waypoints and marks on
the body, and the body's planetary facilities (1 Syst's settlements, ports, outposts...): each
a TACAN symbol, as the Hornet's, with a light dashed ring 10 km round it. The scale fits the
steer-to point, in round steps; the COMM1 VOLUME dial or the mouse wheel zooms it yourself,
RESET SCALE puts it back; KM / NM beside it shows the scale in kilometres or nautical miles
(its round steps in each; kept). With no fix on the plan's body, the
map shows the plan round its steer-to point, north up. Beside it: the steer-to point, its
name, then its bearing, range, time to go at your ground speed, your track, ground speed
and altitude (and the plan's height for an ATK point, amber when you're well off it), the call
due there and the leg in; the plan, its points (NONE: all your waypoints and marks; pick one
to steer to it); the target's bearing and range; with a TOT on the activated plan, TIME ON TARGET: the TOT and the time now (Zulu), the
ground speed you need now - to the IP, so you can fly the IP -> TGT leg at its GSPD and be over
the TGT on the TOT (on that leg, or with no GSPD: to the TGT) - and how early or late you'd be
at your ground speed now (the Hornet's early / late caret). AUTO steps the steer-to point on along the plan when you're within 3 s (400 m at
least) of it, or once you've flown past it close by. Your position: Traj's filter. (The HSI
flies a plan as it is: plans are put in order on Wpt.)
Exobiology: sampling a species with the genetic sampler (the journal's ScanOrganic: Log is the
first sample, Sample the second and third, Analyse once it's done), each sample is on the map
where you took it (Status.json's position then: S1-S3), ringed at its genus's colony range - how
far the next sample must be from every one before it (Bacterium 500 m, Osseus 800 m, Electricae
1 km... EXOBIO_RANGES in this script) - amber while you're inside it, too close; the map is on the
body you're on while you sample (a plan on another body: the chip over the map says where it is),
and the automatic scale fits the samples and their rings while you're within 5 km of one. The
panel gives the species, the samples taken, the colony range, how far you are from the nearest
and how much further to GO (CLEAR once you're clear of them all; ANALYSING once the third is in);
with no steer-to point, the scratchpad shows it too: EX, the count, GO and the metres
still to go - or CLEAR. Once it's analysed, ANALYSED and the species while you're on that body.
Logging a different species starts again, as the game does; dying loses it. Only samples taken
while the FT3000 runs have positions (a restart keeps them: exobio.json).
The timer, bottom left of the map (under the rose), works as the T-6A's clock: ET / CD is its
SEL - the stopwatch (ET, counting up) or the countdown (CD) - and the time its CTL: start it,
and again reset it (the stopwatch to zero; the countdown cleared, to set again). A countdown
with no time set: CTL asks for its time, HH:MM:SS (the digits fill the hours, then the minutes,
then the seconds; 1 s to 99:59:59). At zero it flashes red and counts up again (+); SEL stops
the flashing. SEL doesn't change it while it runs. A click works each as the UFC's pull does
(the time, a countdown with none set: the keyboard types it, Enter sets it, Esc leaves it).
The board keeps it, so every open page shows the same and a reload keeps it running; on the
other pages, while it runs or has a countdown set, a copy shows in the sub-tab row.
On the UFC (page menu), COMM2 turns the steer-to point (the activated plan's points in order -
only those; with NONE, all your waypoints then your marks - round again) and a pull designates it (the Hornet's WPDSG; an
ATK point can't be; DSG does too); COMM1 steps across SEQ, AUTO / MAN, TRK-UP / N-UP, RESET
SCALE, KM / NM, then the timer's ET / CD and its time, and a pull flips or presses one. Typing
a countdown's time: the keypad's digits type it (the scratchpad shows it), ENT or a pull sets
it, CLR clears what's typed (again: stops typing); ENT with COMM1 on the timer types a new one,
CLR clears the one set. The scratchpad shows the steer-to point (WP, MK, OS for an offset
aimpoint, AT for an attack plan's point, and its number) and its range in km - with COMM1 on
the timer, the timer (ET / CD, UP past zero); COM1 its place in the plan, COM2 the plan (A:
ATK; blank: NONE).

Trajectory guidance (Nav > Traj)
--------------------------------
Guidance down to a planetary facility, from orbital cruise to the pad. Across the
top: over the top-down view, the destination - 1 SYST SEL (the planetary facility,
or your own target, Nav > Syst has selected; in AUTO that's the nearest surface site once you're low)
or DEST (the one you've targeted in the game: Status.json's Destination); in the
middle, its name (and your pad, once docking's granted) and the phase you're in;
over the side profile, the profiles (ENTRY 1 or CIRCLE, and CIRCLE's OVHD / STRT-IN - the
pop-up is Atk's attack plan). The phases, from Status.json's flags:
  Orbital cruise: the pictures at 1,000 km, then 100 km inside 100 km; the vertical
  velocity check waits - ENTRY 1 starts at the glide.
  Glide, and flying on after it: the whole of ENTRY 1, at 30 km.
  Final approach (within 3 km of the settlement): at 3 km, to your pad once docking's
  granted, where the board knows where the pad is (the settlement's layout
  confirmed and its heading known for that layout - Nav > Syst's schematic), else
  to the settlement's position.
Each phase has its own fixed scale; you're pinned at the edge, with an arrow and
your distance, when you're outside it. You can zoom both pictures yourself, together
and smoothly from 300 m to 10,000 km: the COMM1 VOLUME dial (as on a schematic:
clockwise in) or the mouse wheel on either picture. Your scale then stays until
RESET SCALE (under the side profile: COMM2, or a click), a new destination, or
going back into orbital cruise; the scale and AUTO / MANUAL show beside it.
Without a destination it can use, the box says why: NO DESTINATION (nothing selected,
or no HUD target in this system), NOT A SURFACE TARGET (a body - "Body selected -
planetary target required" - or something in orbit: an orbital station, carrier or
megaship) or TARGET POSITION UNKNOWN (on the surface, but no one has recorded where:
"No surface coordinates - recon required" - approach it once and your journal does,
or make it one of your own waypoints in 2 Nav > Wpt).
With no position (the game gives one only near a planet) the panels are still
drawn, behind a box: NO STATE VECTOR (outside orbital cruise range), REFERENCE BODY
MISMATCH (the destination's on another body) or, for a moment as the first reading
comes in, ACQUIRING STATE VECTOR. A reading without a position is taken as a miss
for a second and a half (the last position carries on) before the box shows.
Below, two panels, half each:
  Top-down (left): the course in (CRS, 000-359: the way you fly towards the
  destination) with its +-5 degree bounds fanning out from the destination, range
  rings, where you've been, you, and where you'll be in 60 s; north up or course
  up. Bearing, range, deviation, cross-track distance, track and heading below.
  The course can be set whenever there's a destination, position or not; one you
  set is kept (in that browser) for each destination. Until then it's AUTO - the
  bearing you have to it - and the bearing when the glide starts is taken as the
  course (dropped when you're back in orbital cruise, so the next glide takes its
  own).
  Side profile (right): the 50 degree path up from the destination, the 10 and 60
  degree bounds and the planet's surface curving away, with you on it (a circle,
  and a dashed line to where you'll be in 60 s) - at true
  angles and true scale. Altitude, range, the angle you're at from the destination,
  your flight-path angle, how far above or below the path you are, and time to go;
  then the vertical velocity: required = ground speed (closing on the destination)
  x tan 50 deg, against yours and the 10-60 degree window. (The path, its bounds and
  the course bounds are OPT, SHALLOW, STEEP and LAT in web/js/traj.js: the
  pictures and the words follow them.)
  CIRCLE: a Heading Alignment Cone, after the Shuttle's - a tightening turn onto the course,
  then a 20 degree outer glide slope (OGS) down it to the destination. WP2, the HAC's exit, is
  4 km out along the course, 1.46 km up (4 km x tan 20); the HAC beside it turns you onto the
  course there, its radius 2.5 km where you join it (WP1, where your line in meets it, tangent)
  tightening to 1.5 km at WP2, in step with the turn still to go, descending at 14 degrees
  (about 1 in 4) - and so the line in to WP1. OVHD puts the HAC on the side that gives the
  bigger turn (overhead: past the destination and round), STRT-IN the smaller (straight in),
  from where you are when it's armed: when you pick CIRCLE, flip OVHD / STRT-IN, change the
  course or the destination, and all the while in orbital cruise; then it stays. It needs a
  course: set none, it takes the bearing you have to the destination when you pick it (as the
  glide does; ENTRY 1 again drops it). Three stages: ACQ (fly the line to WP1: its bearing and
  range, the turn it gives, the side), HAC (on it once you're within 400 m of WP1 - or 4 s at
  your ground speed - or inside it: the turn still to go, the HAC's radius there and how far in
  or out of it you are, the path to WP2), OGS (past WP2: the course, as ENTRY 1's - bearing,
  range, deviation, cross-track); the final approach, within 3 km, only from the OGS (the HAC
  can pass that close). The top-down view draws the HAC (what you've flown of it dimmed), WP1,
  WP2, the OGS and your line in; the side profile is the path to the destination unrolled
  round the HAC: the reference altitude - the OGS up to WP2, then 14 degrees on round the HAC
  and out - with its band (8%, or 60 m if more), WP2 and WP1 along it, and you. The readouts:
  your altitude and the reference's, how far above or below it (HIGH / LOW, amber; red past
  three times the band), the descent rate it needs (your ground speed x tan 14 deg - tan 20 on
  the OGS: the vertical velocity panel shows it, in a +-6 degree window), the path still to go
  and the time it takes. The pictures are at 10 km while you fly it near the destination (3 km
  on the final approach). Its numbers are HAC in web/js/traj.js.
  (An ILS and a highway in the sky are drawn in a middle column, off for now:
  SHOW_MID in web/js/traj.js. The ILS's localiser full scale is the course bounds;
  its glide slope is split, full deflection down at the 60 degree bound and full up
  at the 10 degree bound - GS_SCALE, "even" for the same scale both ways. The
  highway: gates down the path, sized to the bounds, over the ground, with a marker
  where you're actually heading.)
Where you are comes from Status.json (latitude, longitude, altitude, heading),
which the game rewrites near a planet while you move - every second while your
height is changing quickly, otherwise when your latitude or longitude has moved
about 0.02 degrees (the timing log showed it): about 1.5 km on a 4,360 km world -
every 4 s at 393 m/s, 8 s at 205 m/s - and 0.7 km on a 2,000 km one. From the glide
down each reading, timed by when the game wrote the file, goes through a Kalman
filter (position and velocity, east, north and up), which gives your speeds and
carries you on between readings for as long as the game should take to write again
at your speed, so the pictures move smoothly. Across the ground it expects steady
flight, which holds your speed steady through the gaps (8 s on at 205 m/s, it was
within 4 m), unless a reading lands further from where it had you than chance
allows - a turn or a change of speed - or you're gliding: then it follows every
reading closely until you're steady again. What the pages show eases onto each new
reading over a second rather than jumping (waypoints are marked from the filter's
own estimate). Below 30 m/s across the ground - a hover, a slow drift, which the
game may not write again for a long while - it carries you on only a second, and an
Overfly MARK takes the game's last position rather than a drift carried on. In
orbital cruise, where you speed up and slow down by thousands of m/s a second, the
speed is the change since the last reading. The game doesn't write while nothing
changes, so a silence longer than it should keep at your speed means you've stopped
(2.5 s below 30 m/s; longer the faster you were going - it goes quiet for a few
seconds as you drop into the glide); the next reading starts it afresh, rather than
guessing your speed from the gap. "No reading" shows only after 30 s. The angles allow for the planet's curvature. The altitude is the game's
- from the ground below you near the surface, from the planet's average radius
higher up - and the destination's own height isn't known, so the angle is a little
out over uneven ground. The pictures are drawn at the page's coarse pixels.
On the UFC (page menu), COMM1 - the left knob - steps between the course box, the
view switch and the destination switch; a pull on the course box grabs it, then
each click turns the course - 1 degree turned slowly, 2, 5 and 10 degrees a click
as you turn faster - until a pull lets it go; a pull on a switch flips it. COMM2
steps across ENTRY 1, CIRCLE (with CIRCLE, then OVHD / STRT-IN) and RESET SCALE, and a short
pull picks or presses (on OVHD / STRT-IN: flips it); the COMM1 VOLUME dial zooms. With the mouse: click the course box to grab it, then
scroll (or < and >).

Attack: the plan, and mine release (Nav > Atk)
----------------------------------------------
The target, across the top: the designated one (TGT - DSG on a waypoint, its offset aimpoint,
a mark, or a site in Nav > Syst: anything on the surface with a position). PLAN / ATTACK
switches between the attack plan and the release computer.
PLAN: a pre-made profile built round the target - for now the 2-ship low-level pop-up
(ATK_PROFILES in this script: from the card - 480 KTAS from 20 NM, the IP at 10 NM; #2 splits
right no later than 8 NM and runs on 18 s (the card's 15-20 s) past #1's track, then turns in
to pop from the east; #1 offsets right at 7 NM and pops in from the south; both come off left;
#2 over the target about 40 s after #1). Its settings: ATK HDG (the heading from the IP to the
target; AUTO: the bearing you have to it when you BUILD, kept), your role (#1 or #2 of the
flight, by callsign: WK51, WK52), the callsign (WK5), the speed in knots (the profile's
distances scale with it, so its times stay the card's) and BASE and the step to Base+1 in
metres (#1 attacks at BASE and comes off at Base+1, #2 the other way round, as the card's
legend has it). The picture shows both tracks round the target, ATK HDG up - yours solid, the
calls at IN and OFF - as you set them; you on it, if you're on the body. BUILD (twice) makes
the points on the body, for both roles, with each leg's heading and time and the calls
("WK51, IN SOUTH": where you come in from and go off to, north, east, south or west) - and the
HSI flies yours (ATK). Your points are listed: their range and bearing from the target, their
height, the leg on, the call. The plan code shares it with your wingman, as text
(FT1/body/lat/lon/hdg/kts/base/step/profile/callsign+role/check - the check refuses a
mistyped one): COPY puts it on this PC's clipboard (again within 2 minutes: pasted into Elite
with Ctrl+V - its chat box, say), LOAD takes one (typed in the box; empty, from this PC's
clipboard), designates its target and builds it with you in the other role.
On the UFC (page menu), COMM1 steps across PLAN / ATTACK, ATK HDG (a pull grabs it: then each
click turns it - 1 degree turned slowly, 2, 5 and 10 a click as you turn faster - until a pull
lets it go), ROLE and BUILD, and a pull flips or presses one; COMM2 COPY and LOAD; ENT opens the
plan on the UFC: HDG SPD BASE ROLE BLD (type the digits and ENT; HDG with nothing typed: AUTO;
ROLE flips at once; BLD twice builds; CLR closes it).
ATTACK: a mine-release computer, like a Hornet's CCRP. The model, from three test drops on
Makalu (0.64 g): a mine keeps your ground speed for 10 seconds (CARRY), then drops
straight down - or lands first, if its fall is shorter - so it lands your ground
speed x the shorter of 10 s and its fall time ahead of where you let it go: the
throw. The drops, from 720 to 1,400 m at 205 to 393 m/s, landed 9.7, 9.9 and 10.5 s
of ground speed on. (A mine that kept your speed all the way down would have gone
twice as far from 1,400 m; one that kept it for a second, a tenth as far.) So above
the height a fall takes 10 s from - about 314 m at 0.64 g, 44 m at 0.09 g - your
height doesn't move the release point; below it, it does. The fall assumes a level
release: the root of 2 x height / gravity, from your height averaged over the last
3 s (LEVEL_TAU - near the ground the game's height follows the terrain, which makes
your vertical speed from it too rough to use). Off level by more than 2 degrees
(LEVEL_FPA, averaged the same way), where that would change the throw - a dive
shortens the fall, a climb lengthens it - it says so: let go now, it lands short (or
long). Your position and speeds: Traj's filter, carried on between the game's
readings. Without the body's gravity there's no fall time, so no release point.
  Top-down (left), track up: you, your track, the release point on it (REL), where
  a mine let go now would land (the circle: CCIP - drop on a waypoint and see whether
  it lands short or long of it), the target boxed in red (at the
  edge with its range when it's further out) and the body's other settlements
  (amber) and waypoints (green). The scale fits the target, in round steps; the
  COMM1 VOLUME dial or the mouse wheel zooms it yourself (300 m to 10,000 km),
  RESET SCALE (COMM2, or a click) puts it back. Range, cross-track, bearing,
  track, ground speed and altitude below - range in km and nautical miles (NM),
  ground speed in m/s and knots (kts), altitude in metres and feet, each box in two
  halves.
  Release cue (right): the flight-path marker, the azimuth steering line (steer to
  put the marker on it: full scale 10 degrees), the release bar at the marker and
  the seconds up the line; the ball comes down the line from 20 s out and is on the
  bar at the release point. Beside it, for those 20 s and 3 s after: a second timer
  - a marker that goes round a ring once a second, clockwise, at 12 o'clock on each
  whole second of the countdown (so at the top on the release), swelling for a
  fifth of a second as it passes the top: a beat to time a manual release by. It's
  worked out from the countdown on every frame, so it runs smoothly and in step;
  amber, and red from the release beat on. The countdown under it - REL 12.4, then RELEASE (red,
  flashing, half a second either side), then PAST - is on the UFC's scratchpad too
  (page menu). Gravity, fall time (white over the 10 s carry: your height - or the ground's - doesn't move
  where it lands; amber at 10 s or under: it lands while still carried, so a height error -
  mountains, say - moves it; red under the arming time), the lowest height to release from, in metres and feet,
  for a fall as long as the arming time (ARM, 5 s: a shorter fall may not go off - "Fall 3.2 s -
  under the 5 s arming time"), the throw, time to impact and your flight-path angle
  (averaged, as for the warning). CARRY, ARM, LEVEL_TAU and LEVEL_FPA are at the
  top of web/js/atk.js.
On the UFC (page menu), COMM1's pull flips PLAN / ATTACK and COMM2's presses RESET SCALE; the
COMM1 VOLUME dial zooms.

Timing log (for a jerky display)
--------------------------------
Start the board with --timing-log (or double-click "Timing log.bat", which does
that) and it notes, in timing_log.jsonl in your data folder, when each Status.json
reading was written, seen, sent to the page and taken in there, and how long each
step took: the board's side (reading the file, building and sending the state, the
event stream) and the page's (each fetch and refresh, each animation frame while
Nav > Atk shows, how far the position is carried on past the last reading, and the
browser's long tasks). Atk's model note reads TIMING LOG ON while it's running. The
file starts afresh each run and stops at 40 MB (about half an hour on Atk). Open
Atk with a target, fly a straight run of a minute or so, and send the file. It
changes nothing the board does.

WinWing UFC
-----------
Needs: WinWing SimApp Pro running (it draws the UFC text), and the hidapi package
(pip install hidapi). Keys are looked up by action name in your Elite bindings,
so if you rebind something in the game, the UFC follows (reloaded automatically).
Keys are only sent while Elite is the active window.

    python ed_target_board.py --list-keys         # show what every UFC button will press
    python ed_target_board.py --test-key GXY      # press one key after a 5 s countdown
    python ed_target_board.py --no-ufc            # web board only
    python ed_target_board.py --ufc-learn         # if your UFC's BRT, COMM2 VOLUME and COMM1 VOLUME knobs don't answer

Menus are defined in UFC_MENUS below; UFC_MENU_BUTTONS says which button opens
each: ILS the page menu, D/L navigation (GXY, SYS, NEXT, CRUI, JUMP), BCN the
wing menu. The page menu controls the web page: option buttons 1-3 pick its tabs
(HOME, NAV, CTRS) - the tab showing's button again steps to its next sub-tab (Nav: Syst, Traj,
Wpt, HSI, Atk, Hist, Syst...) - and the keypad's digits pick a sub-tab of the tab showing (Nav:
1 Syst, 2 Traj, 3 Wpt, 4 HSI, 5 Atk, 6 Hist; Contracts: 1 Active, 2 History, 3 OCOR), the page
you last had in it; on Syst, 1 again flips between its list and map. A tab opens on the
sub-tab you last had there. Option button 4 is DSG: the page showing designates what COMM1 has
highlighted (Syst: a surface site - its list's or map's highlight, else its selection; Wpt: a
waypoint or mark; the HSI: the steer-to point) - the target, Atk's and the HSI's. Option button
5 is MK: a mark where you are now, whatever page shows (from the page's filter; with no page
open, from Status.json a moment later). On Wpt and Atk, ENT and CLR are always the page's: ENT
opens what COMM1 has highlighted on the UFC - a sub-level, as the Hornet's UFC pushbutton opens -
with its fields in the option windows (see Your waypoints and Attack, above); until CLR closes
it, the option buttons and the keypad are its. The
COMM1 knob scrolls/pulls to choose a contract (an objective on OCOR, a body or
station on Syst - and, after the last of those, the System Data Uplink
Synchronise button, which a pull presses - or a row on the history pages; from
Home it goes to Contracts; on Traj it works the page's course box and switches,
and COMM2 its profiles and RESET SCALE), the COMM2 knob scrolls the right panel (on the
history pages it steps across the toggles and the copy button first: a short pull
flips the toggle or presses the button), and on OCOR and Contracts' Active page a
short COMM2 pull presses COPY / PASTE beside the system's name. The COMM1 VOLUME dial zooms (clockwise in) wherever there's
something to zoom: the system map, a planet or star, a schematic, Traj's pictures.
The three dials (COMM1 VOLUME, COMM2 VOLUME, BRT) are speed controls: in the
middle fifth of its travel a dial holds; turned further either way, it moves
that way - gently just outside the middle, fastest at the end stop (zoom 4 times
a second, spin 90° and tilt 60° a second, pan half the picture a second). After a
new selection (or the page opening), a dial that's turned waits until it's been
back in the middle once, so it doesn't set things moving on its own. While one
is moving something, the scratchpad shows it: Z+ or Z- for zoom, and << >> (spin
or turn) or UP DN (tilt) - the page that drives the displays says which.
On Syst's
map, COMM1 moves the highlight across it and a pull opens the details, COMM1
VOLUME zooms, COMM2 VOLUME pans across and BRT up and down. On System's list, COMM2 steps from the AUTO/MANUAL
switch to the picture, then the buttons under it (MAXIMISE, SCHEMATIC VIEW, and on
a schematic the layout arrows, CONFIRM / SET LAYOUT, ALIGN LAYOUT, the icon toggles and TYPE),
then the details (aligning a settlement: just the picture, CANCEL and CONFIRM HEADING); a
short pull flips the switch, grabs / lets go of the picture or presses the button,
and a 2-second pull selects the settlement under the
picture's (+) cursor (page menu only) - with none under it, it shows the whole
planet again, spinning on its own, as a double-click does; a grabbed schematic pans instead
(see Settlement schematics, above). The BRT dial tilts the picture and
COMM2 VOLUME spins it (a schematic: turns it) - once you have, its own spin
stops until you select something else - and COMM1 VOLUME zooms (page
menu only). Where a UFC1's three dials sit in its reports is built in; if yours
don't answer, --ufc-learn finds them and saves ufc_axes.json, which then counts as
their default (a dial it doesn't see move keeps what it had) - or ASSIGN them on
4 Setup > Controls.

Controls (4 Setup)
------------------
Every UFC job - the COMM1 and COMM2 turns and pulls, the five option buttons, the
menu buttons, the keypad, the three dials - can be put on a button (or dial) of
any USB game controller: a button box, a HOTAS, a joystick, the UFC itself. The
UFC's own layout is the default. 1 Controls lists the controllers the board can see
(lit while they send; IN USE, those with jobs; any with a job that's not plugged
in) and the jobs in groups, each with its button or dial ("default" while it's the
UFC's own; ELITE ALSO: what the game does with that button too, from your Elite
bindings), ASSIGN and CLEAR. ASSIGN waits 12 seconds for a press on any controller
(a hat's direction counts as a button) - or, for a dial, 6 seconds for it to be
turned end to end and back - and records it; while it waits, a press only records
the button. One button, one job: a button already in use moves to the new job (the
page says which lost it). A row lights while its button's held, so a setup can be
tried out there. RESTORE DEFAULTS (twice) puts every job back on the UFC. Your
assignments are kept in controls.json (only what differs from the defaults).
A controller that describes its reports (most do, with hidapi 0.14 or later) is
learned by its parts - BUTTON 12, HAT 1 UP, X AXIS - and those are checked against
Elite's bindings; one that won't is learned from what changed when it was pressed
(BYTE 1 BIT 3; a hat's whole byte). Keyboards and mice can't be assigned (Windows
keeps them to itself, and Elite has the keys). Without a UFC, nothing shows the
menus' option words: the page's tabs and sub-levels still do. Two identical
controllers (the same USB IDs) count as one. While the page shows, every game
controller is kept open, to light it up and for ASSIGN; otherwise only those with
jobs. The board looks for controllers plugged in or out every 3 seconds.
The displays behave as if the page drives them, like a USB device with no
program running it otherwise: blank with no page open (and while the page's
terminal is still switched off); every digit 8 through the terminal's BIOS and
its waiting screen (the game not running, or back at its main menu); while a
ship, SRV, Nomad or fighter starts up, the scratchpad shows this script's version
and the other displays run test patterns; then the menu. On foot, the menu comes
straight after the waiting screen. With more than one page open (a PC and a
phone, say), the displays follow the one opened first; a page that closes counts
for two seconds more (a reload, a phone's connection blinking). The buttons work
whatever the displays show.
If Elite runs as administrator, run this script as administrator too, or
Windows will block its keypresses.

Settings (4 Setup)
------------------
2 Settings holds what the FT3000 starts with, kept in settings.json in your data
folder as each is changed: the journal folder (blank: Saved Games\\Frontier
Developments\\Elite Dangerous; it counts the journals there), the AI for subject files (AUTO -
Claude Code if it's on this PC, else Codex, else none - CLAUDE, CHATGPT or NONE, and
a model, e.g. haiku; it says which tools it finds and how the login check went),
VIEW FROM OTHER DEVICES (listening on your network as well as this PC: it shows the
addresses to open), GAME CONTROLLERS (off: the page alone, as --no-ufc) and OPEN THE
PAGE AT START. Each takes effect at the next start: the page says RESTART TO APPLY,
and RESTART NOW closes the board as Exit does and starts it again with the same
command line (a new window on Windows) - the page stays open and picks the new start
up, with no new tab. An option given on the command line (--journal-dir, --engine,
--model, --host, --no-ufc, --no-browser) wins over its setting for that run, and the
page says so (SET BY --ENGINE AT START). Set with the mouse and keyboard. The About
block shows the version, the program's folder, your data folder, the Elite bindings
file in use and the project's page (PROJECT_URL).

On a phone
----------
Built for a phone on its side. Turn on VIEW FROM OTHER DEVICES (4 Setup > Settings;
or run with --host 0.0.0.0), open the address it shows on the phone, and "Add to
Home Screen" to get it full screen without the browser bars. Motion effects switch
off if the phone's "reduce motion" setting is on. (With it on, anything on your
network can open the page and work it, as the phone can - the page has no password;
the first time, Windows may ask to let Python use the network: allow private networks.)

Only its own page
-----------------
The board answers its own page - however it's opened: localhost, this PC's name, an
IP address - and programs that aren't browsers (the next copy started, closing this
one). It refuses any other website open in the same browser (the request's Origin,
or Sec-Fetch-Site, says it came from somewhere else), so a page elsewhere can't press
UFC buttons, send keys to Elite or stop the board; and it refuses requests under any
other name pointed at this PC (its Host), so a website can't pose as it that way
either (DNS rebinding). Each is refused with 403, and noted in the console once a
minute (request_refusal).

Asking Spansh and EDSM
----------------------
The board introduces itself to Spansh and EDSM (and to anything else that asks it)
by name and version - "UCEC-FT3000/<version> (Elite Dangerous companion; +<the
project's page>)", from user_agent() and PROJECT_URL - so the people who run them
can see what's asking, and where to find it. It asks them only for systems you're in
or look at, and keeps their answers (the system data cache, the system archive).

Files
-----
The program - keep these together in one folder (a new version can replace it whole):

    ed_target_board.py      this script: journal reading, Spansh and EDSM, the UFC, the web server
    web/index.html          the page's layout: the strip, the tabs, one <section> per page, the overlays
    web/style.css           its look (the colours are the tokens at the top)
    web/vga.woff            the typeface (see Credits)
    web/js/core.js          shared by every page: the page registry, the view, formatting, text effects
    web/js/main.js          starts the page and routes the board's state and the UFC's input to the pages
    web/js/home.js          1 Home                 web/js/contracts.js  3 Contracts > Active
    web/js/ocor.js          3 Contracts > OCOR     web/js/syst.js       2 Nav > Syst, its list
    web/js/sysmap.js        2 Nav > Syst, its map  web/js/history.js    2 Nav > Hist and 3 Contracts > History
    web/js/nav.js           2 Nav's waypoint system, shared: marks, flight plans, the steer-to point, the target
    web/js/tgt.js           2 Nav > Wpt, your waypoints, marks and flight plans   web/js/hsi.js   2 Nav > HSI
    web/js/traj.js          2 Nav > Traj           web/js/atk.js        2 Nav > Atk, the attack plan and mine release
    web/js/timing.js        the page's side of the timing log (--timing-log; see Timing log, above)
    web/js/timer.js         the HSI's timer (the stopwatch and countdown) and its copy in the sub-tab row
    web/js/setup.js         4 Setup > Controls: each of the UFC's jobs on any game controller's button or dial
    web/js/settings.js      4 Setup > Settings: what the FT3000 starts with, RESTART NOW
    README.md, CHANGELOG.md what it is and how to start, for someone new; what changed in each version
    LICENSE, CREDITS.md     GPL-3.0; everyone whose work it uses (and what the release zip includes)
    docs/                   the README's screenshots
    release.py              builds the release zip: these, with Python and hidapi beside them (python/), and
                            Start UCEC FT3000.bat to start it - see release.py
    Timing log.bat          starts the board with the timing log on (Windows; the release zip's own Python if it's there)
    web/js/remote.js        1 Syst's CURRENT SYSTEM / REMOTE: the list to pick a remote system from, MANUAL's name and matches
    web/js/schematic.js     settlement schematics (drawn in Syst's and Hist's pictures)
    web/js/pixel.js         coarse pixels for the pictures, the map and hyperspace, like the rest of the terminal
    web/js/icons.js         the list icons (stars, planets, each kind of station; in orbit, landed, docked)
    web/js/mapdraw.js       the system map drawing - the layout, bodies as wireframes, stations as icons -
                            shared by Syst's map and the hyperspace overlay
    web/js/hyper.js         the hyperspace overlay
    web/js/boot.js          the terminal's own screens (power-on, boot, no signal) and changing vehicle
    schematics/             settlement layout plans, one .json file per layout (see System, above)
    tests/                  the tests (below); not needed to run the board

Your data - in your data folder, Saved Games\\UCEC FT3000 (the console says where at start-up; FT3000_DATA, set in the
environment, puts it elsewhere). Versions before 3.01.42 kept it in the program's folder: the first start copies it
across (the old copies are left there - a backup, safe to delete):

    star_coords.sqlite      every system's coordinates, and 2 Nav's waypoints, marks, flight plans and attack plans
    journal_records.sqlite  bodies, stations and settlement positions from your journals, and your history
    settlements.sqlite      the layouts you've confirmed for settlements, and which way they face
    system_archive.sqlite   Spansh's and EDSM's last answers for each system you've been in
    edsm_cache.json         the system data cache (Spansh's and EDSM's)
    target_backstories.json the subject files written         ocor_briefing.json   the OCOR briefing
    uplink_settings.json    the Spansh / EDSM Uplink switches  remote_system.json   1 Syst's REMOTE system
    exobio.json             the species you're sampling and where you took each sample (2 Nav > HSI's rings)
    controls.json           your controls, where they differ from the UFC's own layout (4 Setup > Controls)
    settings.json           what the FT3000 starts with (4 Setup > Settings)
    ufc_axes.json           where your UFC's dials are, if --ufc-learn found them
    ft3000.pid              written while a copy runs (which process, its port): the next copy closes it if it's still running
    timing_log.jsonl        the timing log (--timing-log)

How it fits together, for changing it:
  * What the board knows lives in BoardState, split by area: Commander (you, your
    ship, the session log), Place (where you are), Contracts (missions, scans,
    subject files), Vehicles (changing vehicle, start-up), Jumps (route, hyperspace,
    fuel), Exobio (the species you're sampling), ChatCodes (codes heard in the game's
    chat) and SystemTab (Syst's data). Each area handles the journal
    events it cares about in methods named on_<Event>; BoardState.apply sends each
    event to every area that has one. snapshot() is what the page is sent. Beside
    them, JournalRecords and JournalHistory keep what all your journals say (the
    System records, and the history pages' lists - which the page fetches from
    /api/hist when they change) - and NavBoard 2 Nav's waypoint system (marks, flight
    plans, the steer-to point, the target, the attack plan: syst.nav, and /api/nav).
  * The page is tabs made of pages, in sub-tabs. PAGE_TABS (below) lists them,
    PAGE_SUBTABS each page's sub-tab (its keypad digit; Syst's list and map share
    one), and each page registers itself in its own file with ED.page({...}): which
    tab, page and sub-tab it is, its <section> in index.html, and what it does on
    each refresh, when it shows, and with the UFC's knobs and pulls - main.js lists
    the hooks. Where you are (a tab and a page) is one record shared by every open
    page and the UFC (UIBus.view): the page reports it to /api/select, the UFC moves it.
  * To add a page: a <section class="page" id="pg-..." data-tab=".." data-sub="..">
    in index.html, a file in web/js that calls ED.page({...}) (and its <script> line
    before main.js), and its name in PAGE_TABS and its sub-tab in PAGE_SUBTABS (up to
    9 a tab). To add a tab, also a tab button in index.html and, for the UFC, an
    "@tab:..." option in the PAGE menu.
  * Keeping the page up to date: Status.json and the journal being written are read
    every tenth of a second (STATUS_POLL_SECONDS; the folder, for a new journal file,
    and NavRoute.json once a second). Whenever they bring something new - or a
    subject file moves on - the board bumps state_n on the event stream (/api/events),
    and every open page fetches /api/state at once: one fetch at a time, and a change
    while one is on its way fetches again as soon as it lands. Pages still fetch every
    2 seconds as well, for anything slower. (The game empties Status.json for an
    instant as it rewrites it: an empty or half-written read is skipped and read
    again, never taken as a Status.json with nothing in it.)
  * Changing page: the screen settles on the new one - the full lens pull (#app,
    "pullbig") for another tab, a lighter pull on the page alone ("pull") for another
    page of the same tab (main.js, setView).

Tests
-----
    python tests/run_tests.py              # everything
    python tests/run_tests.py server       # the board and the UFC only (standard library)
    python tests/run_tests.py page         # the page in a browser: pip install playwright,
                                           # then: playwright install chromium
Each test runs its own copy of the board in a temporary folder, with made-up
journals, a simulated UFC and no internet, so it never touches your real files,
caches or UFC. What the board and each page show is compared with saved results
(tests/golden); after a change you mean to make, --update accepts the new ones.
The README's screenshots (docs/) are taken the same way, from the tests' made-up
journals (CMDR Deckard): python tests/make_screenshots.py takes them again.

Credits
-------
Typeface: "Px437 IBM VGA 8x16" from the Ultimate Oldschool PC Font Pack by VileR
(https://int10h.org/oldschool-pc-fonts/), licensed CC BY-SA 4.0
(https://creativecommons.org/licenses/by-sa/4.0/). Included unmodified as web/vga.woff.
Settlement measurements (the schematics' positions, doors, terminals, loot and
combat-zone points): SrvSurvey by CMDR Grinning2001 (njthomson) and contributors
(https://github.com/njthomson/SrvSurvey; https://edcodex.info/?m=tools&entry=590), GPL-3.0 - each plan file says so in its
"srvsurvey" block. Settlement layout names and pad counts: Raven Colonial
(https://ravencolonial.com). The plans were traced from CMDR Quizengine's Odyssey
settlement maps (OMG - now hosted by Elite Dangereuse:
https://elitedangereuse.fr/outils/quizengine/omg_1.1.html). Systems' bodies, stations, signals and coordinates: Spansh
(https://spansh.co.uk), from players' EDDN uploads. Traffic, deaths and
exploration value (and bodies, stations and coordinates where Spansh has none):
EDSM (https://www.edsm.net). How the sources are combined follows EDDiscovery's
(https://github.com/EDDiscovery/EDDiscovery). All of them, and what the release zip
includes (Python, hidapi), are in CREDITS.md.

Licence: GPL-3.0 (LICENSE). Project page, releases and bug reports:
https://github.com/bigronny/ED-UCEC-FT3000
"""
from __future__ import annotations

import argparse
import json
import math
import os
import queue
import random
import re
import select
import shutil
import signal
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import webbrowser
from collections import OrderedDict, deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote

# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
VERSION = "3.02.05"   # the FT3000's version: + 0.00.01 each build (after .99, the middle number goes up)
PROJECT_URL = "https://github.com/bigronny/ED-UCEC-FT3000"   # the project's home page: shown on 4 Setup, and sent to Spansh/EDSM


def user_agent():
    """How the FT3000 introduces itself to Spansh and EDSM: its name, version and where to find it."""
    about = "Elite Dangerous companion"
    if PROJECT_URL:
        about += f"; +{PROJECT_URL}"
    return f"UCEC-FT3000/{VERSION} ({about})"


SCRIPT_DIR = Path(__file__).resolve().parent


def saved_games_dir():
    """Windows' Saved Games folder (wherever it's been moved to), else ~/Saved Games."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
            folder = GUID(0x4C5C32FF, 0xBB9D, 0x43B0, (ctypes.c_ubyte * 8)(0xB5, 0xB4, 0x2D, 0x72, 0xE5, 0x4E, 0xAA, 0xA4))   # FOLDERID_SavedGames
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folder), 0, None, ctypes.byref(out)) == 0 and out.value:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:
            pass
    return Path.home() / "Saved Games"


# Your data - waypoints and plans, history, caches, settings, controls, subject files - lives apart from the program, in
# Saved Games\UCEC FT3000 (FT3000_DATA, in the environment, puts it elsewhere), so a new version can replace the
# program's folder without losing any of it. The first start finds it in the program's folder (where versions
# before 3.01.42 kept it) and copies it across (move_old_data).
DATA_DIR = Path(os.environ["FT3000_DATA"]).expanduser() if os.environ.get("FT3000_DATA") else saved_games_dir() / "UCEC FT3000"
DEFAULT_JOURNAL_DIR = saved_games_dir() / "Frontier Developments" / "Elite Dangerous"
CACHE_FILE = DATA_DIR / "target_backstories.json"
WORK_DIR = Path(tempfile.gettempdir()) / "ed_target_board"  # empty folder the AI CLI runs in

# Environment variables that would make the CLIs bill an API account instead of
# your subscription. They are removed for the AI tool's process only.
PAID_KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY")

# The subject files (3 Contracts): each target is a replicant. The board fills in the facts from the journal -
# affiliation, contract, serial number, incept date, status, retirement bounty, threat - and the AI writes the rest,
# as one JSON object of fixed fields (DOSSIER_FIELDS) that the board checks (check_dossier) before it's shown: a reply
# that doesn't fit is sent back once with what was wrong, then it's an error. In ship, the behavioural notes and the
# assessment are written again (just those two) after the target's first full scan. A person's file, or a batch's (a
# massacre: a faction, a number of kills). DOSSIER_SETTING is the world they're written in.
DOSSIER_FORMAT = 2        # the subject file (its fields); dossiers kept from before it are prose, and stay as they are
DOSSIER_LINE = "N31"      # the serial's lineage: Nexus-31 (DOSSIER_SETTING)
DOSSIER_LIFESPAN_DAYS = 4 * 365   # (incept dates fall within it, before the contract)
GAME_YEARS = 1286         # Elite's calendar: this many years on from ours
DOSSIER_SLACK = 0.15      # a field may be this much over or under its words before it's sent back
DOSSIER_SETTING = """SETTING
- Replicants of the Nexus-31 lineage are made by Azimuth Biotech under a licensed Wallace
  pattern. They live four years and don't know when they were made. Their childhoods are
  implanted, built from stock memory files reused across many units.
- Units are leased to navies, corporations and security services. A unit that leaves its
  lease is a fugitive, and retiring it is legal.
- Everything else is Elite Dangerous as it is: the Federation, the Empire, the Alliance,
  independent systems, minor factions, ships."""
DOSSIER_VOICE = """VOICE
Clipped, administrative, unsentimental. Short declarative sentences: a records officer
briefing a hunter. No exclamation marks, no questions, nothing added for effect. The
assessment ends with an instruction to the hunter."""
DOSSIER_RULES = """RULES
- Use the facts you're given exactly: names, factions, governments, allegiances, systems,
  stations, ships, ranks and numbers. Don't contradict them, and don't add facts about
  real factions or systems.
- If no ship scan is given, don't name a ship.
- Never mention the game, the player, missions or the FT3000.
- Write the behavioural notes for the mode given: IN SHIP (the ship, how it flies and
  fights) or ON FOOT (the settlement, how the target moves and hides there)."""
DOSSIER_REPLY_PERSON = """REPLY
One JSON object and nothing else, with exactly these keys, plain text in each:
  "sex"                "M" or "F", inferred from the target's name (no clue: choose);
                       use pronouns to match
  "physical_grade"     "A", "B" or "C"
  "mental_grade"       "A", "B" or "C"
  "known_as"           an alias of 1-3 words, or "" for none
  "maker"              under 12 words
  "original_function"  what it was made for, then what it does now; under 15 words
  "background"         60-90 words
  "implanted_memory"   35-60 words; may borrow a station or system from the facts
  "behavioural_notes"  35-60 words
  "assessment"         20-40 words, matching the THREAT given"""
DOSSIER_REPLY_BATCH = """REPLY
This file is a BATCH: a run of units made together, now all serving one faction - the
target. One JSON object and nothing else, with exactly these keys, plain text in each:
  "known_as"           what the batch is called, 1-3 words, or "" for none
  "maker"              under 12 words
  "original_function"  what the batch was made for, then what it does now; under 15 words
  "background"         60-90 words: how the batch came to serve this faction
  "implanted_memory"   35-60 words: the stock memory every unit of the batch shares
  "behavioural_notes"  35-60 words: how its units work together
  "assessment"         20-40 words, matching the THREAT given"""
DOSSIER_EXAMPLE_PERSON = """EXAMPLE INPUT
MODE: IN SHIP
FILE: PERSON
DATE: 14 SEP 3312
TARGET: Marek Holloway
ROLE: Deserter
TARGET FACTION: Brask Free Company (Anarchy, Independent; 1% influence in Brask)
CONTRACT: Assassinate Deserter: Marek Holloway
ISSUED BY: Veltani Signal Corporation (Corporate, Empire) at Harrow Market, Veltani
ISSUER'S SITUATION: civil war with Veltani Citizens' Forum (Veltani Signal Corporation ahead, 2 days to 1)
LAST KNOWN WHEREABOUTS: Corrigan Barracks, Brask (Medium security, Patronage, Empire)
REWARD: 236,500 CR
WING CONTRACT: no
INCEPT DATE: 02 JUN 3312 (3 months ago; a four-year lifespan)
SHIP SCAN: none yet
THREAT: MODERATE (provisional - no scan yet)

EXAMPLE REPLY
{"sex": "M", "physical_grade": "B", "mental_grade": "A", "known_as": "Relay",
 "maker": "Azimuth Biotech, licensed Wallace pattern",
 "original_function": "Security. Relay-lane patrol pilot, now a deserter",
 "background": "Incepted in June for Veltani Signal Corporation, one of a security batch leased to hold the company's relay lanes through its civil war with the Veltani Citizens' Forum. Three months in, he left his post with a company ship and a signals clearance. He turned up next door in Brask, flying for the Brask Free Company, an anarchist outfit with almost no hold on the system. Signal is winning its war. It would like its relay keys kept out of the Forum's hands until it has.",
 "implanted_memory": "A childhood on the docking ring at Harrow Market. His father lets him read approach numbers to inbound traffic over a cracked handset, and calls him a natural. The father is stock: a signals-aptitude file Azimuth sells by the dozen. He kept the handset.",
 "behavioural_notes": "Solo. Last placed at Corrigan Barracks, in a system that won't hide him for long. Three months out and already running, he'll stay close to the one outfit that took him in. Expect him in supercruise near Brask, not docked.",
 "assessment": "Provisional until scanned. A deserter three months old, on a solo contract worth nearly a quarter of a million. Nobody expects much of him. Find him, scan him, retire him."}"""
DOSSIER_EXAMPLE_BATCH = """EXAMPLE INPUT
MODE: IN SHIP
FILE: BATCH (5 units)
DATE: 21 MAY 3311
TARGET: Tollan Dark Gang
ROLE: Pirates
TARGET FACTION: Tollan Dark Gang (Anarchy, Independent)
CONTRACT: Kill Tollan Dark Gang faction Pirates
ISSUED BY: Merrow State Industries
LAST KNOWN WHEREABOUTS: Faraday Settlement, Tollan
REWARD: 1,180,000 CR
WING CONTRACT: no
INCEPT DATE: 03 JAN 3309 (the batch, 2 years 4 months ago; a four-year lifespan)
UNITS STILL AT LARGE: 5 of 5
THREAT: MODERATE (provisional - no scan yet)

EXAMPLE REPLY
{"known_as": "The Tollan five", "maker": "Azimuth Biotech, Wallace pattern, salvage-grade run",
 "original_function": "Convoy escort. Now raiders working the lanes out of Tollan",
 "background": "Five escort units from a salvage-grade run, sold on when their first lease ended early. The paperwork stops at a broker in Tollan. The Tollan Dark Gang bought the batch whole and kept it together, which no buyer should. They work the traffic around Faraday Settlement. Merrow State Industries has lost enough cargo to them to pay well for the set. A batch split up is easier to retire. Nobody split this one.",
 "implanted_memory": "The same memory in all five: a flight school on a cold moon, an instructor who never raised her voice, and a long hangar with the lights going off one row at a time. Each unit believes it was the best in the class.",
 "behavioural_notes": "They fly as a pack and close on one target at a time. They don't leave a unit behind, so a damaged one slows the rest. Expect them near Faraday Settlement, waiting for traffic to drop out of supercruise.",
 "assessment": "Five units, one habit. Hit the slowest and the others turn back for it. Retire the batch. A single survivor will train the next one."}"""
DOSSIER_INSTRUCTION = "Write the subject file for the target in the input. Reply with the JSON object only."
DOSSIER_RESCAN = ("The target has now been scanned. Rewrite only \"behavioural_notes\" and \"assessment\" from the scan in "
                  "the input, keeping to the background and memory given there. Reply with one JSON object with exactly "
                  "those two keys, plain text in each.")
DOSSIER_RETRY = "Your last reply was rejected: {why}. Reply again with the JSON object only."
DOSSIER_FIELDS = {   # each kind of reply: its keys, and each one's words (min, max) or the letters it may be
    "person": {"sex": "MF", "physical_grade": "ABC", "mental_grade": "ABC", "known_as": (0, 3), "maker": (2, 12),
               "original_function": (2, 15), "background": (60, 90), "implanted_memory": (35, 60),
               "behavioural_notes": (35, 60), "assessment": (20, 40)},
    "batch": {"known_as": (0, 3), "maker": (2, 12), "original_function": (2, 15), "background": (60, 90),
              "implanted_memory": (35, 60), "behavioural_notes": (35, 60), "assessment": (20, 40)},
    "rescan": {"behavioural_notes": (35, 60), "assessment": (20, 40)},
}
DOSSIER_INTRO = ("You write subject files for UCEC FT3000, a terminal used by bounty hunters in 3312, in the galaxy of Elite "
                 "Dangerous. Every target is treated as a replicant: a manufactured person with implanted memories, hunted "
                 "for \"retirement\".")


def dossier_system(kind):
    """The system prompt for a person's subject file, or a batch's."""
    batch = kind == "batch"
    return "\n\n".join((DOSSIER_INTRO, DOSSIER_SETTING, DOSSIER_VOICE, DOSSIER_RULES,
                         DOSSIER_REPLY_BATCH if batch else DOSSIER_REPLY_PERSON,
                         DOSSIER_EXAMPLE_BATCH if batch else DOSSIER_EXAMPLE_PERSON))

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # stops console pop-ups on Windows


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
_log_lock = threading.Lock()


def log(msg: str) -> None:
    with _log_lock:   # several threads log; keep each message on its own line
        print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


TIMING_FILE = DATA_DIR / "timing_log.jsonl"   # --timing-log: the board's and the page's timings (this run's; started afresh)
TIMING_MAX_BYTES = 40_000_000                  # ... where it stops (about half an hour on Atk at 144 frames a second)


class TimingLog:
    """--timing-log, for a jerky display: when each Status.json reading was written, seen by the board, sent and
    taken in by the page, and how long each step took - the board's own steps here, the page's (POST /api/timing,
    every 2 s) frame by frame while Atk shows, with the browser's long tasks. One JSON record a line in
    timing_log.jsonl in your data folder, started afresh each run, stopping at TIMING_MAX_BYTES. "w" is the wall
    clock: seconds since 1970 in the board's records, milliseconds in the page's (one PC, one clock). Read only:
    nothing here changes what the board does."""

    def __init__(self, path, limit=TIMING_MAX_BYTES):
        self.path, self.limit, self.lock, self.size, self.full = Path(path), limit, threading.Lock(), 0, False
        self.f = open(self.path, "w", encoding="utf-8")
        self.rec("start", version=VERSION, python=sys.version.split()[0], platform=sys.platform, poll=STATUS_POLL_SECONDS)

    def rec(self, kind, **fields):
        self.lines([dict({"k": kind, "w": round(time.time(), 4)}, **fields)])

    def lines(self, recs):
        with self.lock:
            if self.full:
                return
            out = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in recs)
            if self.size + len(out) > self.limit:
                self.full = True
                out = json.dumps({"k": "full", "w": round(time.time(), 4)}) + "\n"
                log(f"Timing log full ({self.limit // 1_000_000} MB): it stops here - {self.path}")
            try:
                self.f.write(out)
                self.f.flush()
            except OSError:
                self.full = True
            self.size += len(out)


TIMING = None   # the TimingLog, with --timing-log


def _ms(seconds):
    return round(seconds * 1000, 2)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# Changing vehicle plays an effect on the page: leaving a ship, SRV or fighter
# "disconnects" (static), and arriving starts up (static, then that vehicle's boot
# screen; on foot, static only). On foot, LoadGame's "Ship" is your suit.
ONFOOT_SHIP = re.compile(r"^(FlightSuit|UtilitySuit_Class.|TacticalSuit_Class.|ExplorationSuit_Class.)$", re.I)
SRV_SHIP = re.compile(r"^(TestBuggy|Combat_Multicrew_SRV_\d+)$", re.I)
FIGHTER_SHIP = re.compile(r"Fighter", re.I)
NOMAD_TYPE = re.compile(r"lander|nomad", re.I)   # the Nomad is "lander01" in the journal
SRV_NAMES = {"testbuggy": "SRV Scarab", "combat_multicrew_srv_01": "SRV Scorpion", "lander01": "Nomad"}
BOOT_FRESH_SECONDS = 120   # only events this recent count (never ones read back at start-up)


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def clean(text) -> str:
    """Tidy journal strings, which sometimes hold untranslated keys like
    '$MissionUtil_FactionTag_PirateLord;' or '$npc_name_decorate:#name=Ana Diaz;'."""
    if not text:
        return ""
    text = str(text).strip()
    if "#name=" in text:
        return text.split("#name=", 1)[1].rstrip(";").strip()
    if text.startswith("$"):
        word = text.strip("$;").split("_")[-1]
        spaced = ""
        for ch in word:
            if ch.isupper() and spaced and not spaced.endswith(" "):
                spaced += " "
            spaced += ch
        return spaced.strip()
    return text


def target_key(name: str) -> str:
    return " ".join(name.lower().split())


# Journal ship names are internal ("federation_corvette"); these are the in-game names.
SHIP_NAMES = {
    "sidewinder": "Sidewinder", "eagle": "Eagle", "hauler": "Hauler", "adder": "Adder",
    "empire_eagle": "Imperial Eagle", "viper": "Viper Mk III", "cobramkiii": "Cobra Mk III",
    "viper_mkiv": "Viper Mk IV", "diamondback": "Diamondback Scout", "cobramkiv": "Cobra Mk IV",
    "type6": "Type-6 Transporter", "dolphin": "Dolphin", "diamondbackxl": "Diamondback Explorer",
    "empire_courier": "Imperial Courier", "independant_trader": "Keelback", "asp_scout": "Asp Scout",
    "vulture": "Vulture", "asp": "Asp Explorer", "federation_dropship": "Federal Dropship",
    "type7": "Type-7 Transporter", "typex": "Alliance Chieftain", "federation_dropship_mkii": "Federal Assault Ship",
    "empire_trader": "Imperial Clipper", "typex_2": "Alliance Crusader", "typex_3": "Alliance Challenger",
    "federation_gunship": "Federal Gunship", "krait_light": "Krait Phantom", "krait_mkii": "Krait Mk II",
    "orca": "Orca", "ferdelance": "Fer-de-Lance", "mamba": "Mamba", "python": "Python",
    "python_nx": "Python Mk II", "type9": "Type-9 Heavy", "belugaliner": "Beluga Liner",
    "type9_military": "Type-10 Defender", "type8": "Type-8 Transporter", "anaconda": "Anaconda",
    "federation_corvette": "Federal Corvette", "cutter": "Imperial Cutter", "mandalay": "Mandalay",
    "cobramkv": "Cobra Mk V", "corsair": "Corsair", "panthermkii": "Panther Clipper Mk II",
}
COMBAT_RANKS = ["Harmless", "Mostly Harmless", "Novice", "Competent", "Expert", "Master",
                "Dangerous", "Deadly", "Elite", "Elite I", "Elite II", "Elite III", "Elite IV", "Elite V"]
FED_RANKS = ["None", "Recruit", "Cadet", "Midshipman", "Petty Officer", "Chief Petty Officer",
             "Warrant Officer", "Ensign", "Lieutenant", "Lieutenant Commander", "Post Commander",
             "Post Captain", "Rear Admiral", "Vice Admiral", "Admiral"]
EMP_RANKS = ["None", "Outsider", "Serf", "Master", "Squire", "Knight", "Lord", "Baron", "Viscount",
             "Count", "Earl", "Marquis", "Duke", "Prince", "King"]


def ship_name(raw, localised=None) -> str:
    if localised and not str(localised).startswith("$"):
        return str(localised)
    if not raw:
        return ""
    key = str(raw).lower()
    return SHIP_NAMES.get(key, clean(raw).replace("_", " ").title())


def pretty(state) -> str:
    """'CivilWar' -> 'Civil War'; 'None' -> ''."""
    s = clean(state)
    if not s or s.lower() == "none":
        return ""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)


def rank_name(table, value) -> str:
    try:
        return table[int(value)]
    except (TypeError, ValueError, IndexError):
        return ""


def money(n) -> str:
    try:
        return f"{int(n):,} CR"
    except (TypeError, ValueError):
        return ""


# --------------------------------------------------------------------------- #
# OCOR briefing parser (a squadron's daily BGS objectives, pasted from Discord)
# --------------------------------------------------------------------------- #
OCOR_FILE = DATA_DIR / "ocor_briefing.json"
INARA_SYSTEM = "https://inara.cz/elite/starsystem/?search="
_MD_LINK = re.compile(r"\[([^\]]+)\]\(\s*(https?://[^)\s]+)\s*\)")
_DISCORD_TAG = re.compile(r"<(?:[@#][&!]?\d+|a?:\w+:\d+)>")       # mentions and custom emoji
_SHORTCODE = re.compile(r"(?<!\w):[a-z0-9_+\-]{2,}:(?!\w)")       # :emoji: as copied text
_KEEP_SYMBOLS = set("▓░▒█▲▼•·")
_HEADING = re.compile(r"[A-Z][A-Z0-9 &/'’\-]{1,40}")
_OBJ_SPLIT = re.compile(r"^(?P<sys>.+?)\s+[—–]\s+(?P<desc>.+)$")
_BAR = re.compile(r"[▓░▒█]{3,}")
_REMAIN = re.compile(r"([▲▼])\s*([\d.]+)\s*%\s*remaining", re.I)
_SCORE = re.compile(r"score:\s*(\d+\s*-\s*\d+(?:\s*\([^)]*\))?)", re.I)
_LINE_PREFIX = re.compile(r"^\s*(?:>{1,3}\s+)?(?:#{1,3}|-#)\s+")   # Discord quote / heading / subtext markers
_HEADING_MARK = re.compile(r"^\s*(?:>{1,3}\s+)?#{1,3}\s+")             # a Discord heading ("# Priority ONE!")
_PRIORITY = re.compile(r"^Priority\b", re.I)                            # "Priority ONE!", "Priority 2", however it was copied
_TASKS = [
    ("war", re.compile(r"^Support\s+(?P<f>.+?)\s*\[(?P<g>[^\]]+)\]\s*in their (?:civil )?war against\s+(?P<e>.+?)\.?$", re.I)),
    ("raise", re.compile(r"^Raise the influence of\s+(?P<f>.+?)\s*\[(?P<g>[^\]]+)\]", re.I)),
    ("reduce", re.compile(r"^Reduce the influence of\s+(?P<f>.+?)\s*\[(?P<g>[^\]]+)\]", re.I)),
    ("election", re.compile(r"^Support\s+(?P<f>.+?)\s*\[(?P<g>[^\]]+)\]\s*in their election against\s+(?P<e>.+?)\.?$", re.I)),
    ("other", re.compile(r"(?:of|for|Support|Help)\s+(?P<f>[^\[\]]+?)\s*\[(?P<g>[^\]]+)\]", re.I)),
]


def _ocor_plain(line: str) -> str:
    """Strip Discord markdown, links (keeping their text), mentions and emoji."""
    s = _MD_LINK.sub(r"\1", line)
    s = _DISCORD_TAG.sub("", s)
    s = _SHORTCODE.sub("", s)
    s = re.sub(r"(\*\*\*|\*\*|__|~~|`)", "", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", s)   # *italic*
    s = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", s)            # _italic_
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if ch in _KEEP_SYMBOLS or cat not in ("So", "Sk", "Cs", "Co", "Mn", "Cf"):
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _ocor_struck(raw: str) -> bool:
    """True if most of a line is struck out (~~like this~~), which is how the briefing
    marks an objective as completed. Discord's "Copy Text" can split the strike around
    a link ("~~[name](~~~~https://...~~~~ ) - ...~~"); the empty pairs just toggle."""
    parts = raw.split("~~")
    if len(parts) % 2 == 0:            # an unclosed ~~ isn't a strike: it belongs to the text after it
        parts[-2:] = ["~~".join(parts[-2:])]
    struck = sum(ch.isalnum() for seg in parts[1::2] for ch in seg)
    total = sum(ch.isalnum() for seg in parts for ch in seg)
    return total > 0 and struck / total >= 0.75


def parse_ocor(text: str) -> dict:
    """Turn a pasted OCOR briefing into sections of objectives plus standing orders.
    Works with Discord's raw markdown ("Copy Text") or plain copied text. In markdown, a
    struck-out objective counts as done (plain copied text loses the strike-through)."""
    briefing = {"title": "OCOR briefing", "date": "", "objectives": [], "notes": []}
    section, notes_mode, current = "", False, None
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        marked = bool(_HEADING_MARK.match(raw))
        raw = _LINE_PREFIX.sub("", raw)
        done = _ocor_struck(raw)
        raw = raw.replace("~~", "")   # so a struck link still reads as a link
        line = _ocor_plain(raw)
        if not line:
            continue
        if "BRIEFING" in line.upper() and not briefing["objectives"] and not section:
            briefing["title"] = re.sub(r"^[^A-Za-z0-9]+", "", line).strip() or briefing["title"]
            m = re.search(r"\bfor\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", line)
            if m:
                briefing["date"] = m.group(1)
            continue
        # a section: a short line in capitals ("WAR", "INFLUENCE WORK"), or - not in capitals - one written as a
        # Discord heading, or a priority ("Priority ONE!"); never an objective (system — task)
        if not _OBJ_SPLIT.match(line) and (_HEADING.fullmatch(line) or
                                           (len(line) <= 50 and (marked or _PRIORITY.match(line)))):
            word = line.upper()
            notes_mode = any(k in word for k in ("IMPORTANT", "NOTE", "RULE", "REMINDER"))
            section = "" if notes_mode else re.sub(r"[\s!.:]+$", "", line.title())
            current = None
            continue
        if notes_mode:
            briefing["notes"].append({"text": line.lstrip("•").strip(), "bullet": line.startswith("•")})
            continue
        if line.startswith(("•", "- ", "* ")) and current is not None:
            item = line.lstrip("•-* ").strip()
            score = _SCORE.search(item)
            if score:
                current["score"] = re.sub(r"\s+", " ", score.group(1)).replace(" - ", "-")
            else:
                current["bullets"].append(item)
            continue
        m = _OBJ_SPLIT.match(line)
        if m and section:
            link = _MD_LINK.search(raw)
            desc = m.group("desc")
            bar = _BAR.search(desc)
            remain = _REMAIN.search(desc)
            clean = _REMAIN.sub("", _BAR.sub("", desc)).strip()
            obj = {
                "id": f"o{len(briefing['objectives']) + 1}",
                "section": section, "system": m.group("sys").strip(" *[]"),
                "url": link.group(2) if link else INARA_SYSTEM + quote(m.group("sys").strip(" *[]")),
                "desc": clean,
                "task": "other", "faction": "", "gov": "", "enemy": "", "score": "",
                "bar": bar.group(0) if bar else "",
                "dir": remain.group(1) if remain else "", "pct": remain.group(2) if remain else "",
                "bullets": [], "done": done,
            }
            for task, rx in _TASKS:
                t = rx.search(clean)
                if t:
                    obj["task"] = task
                    obj["faction"] = t.group("f").strip()
                    obj["gov"] = t.group("g").strip()
                    obj["enemy"] = (t.groupdict().get("e") or "").strip().rstrip(".")
                    break
            if obj["task"] == "other" and "war" in section.lower():
                obj["task"] = "war"
            briefing["objectives"].append(obj)
            current = obj
            continue
        if current is not None:   # a continuation line of the previous objective
            current["bullets"].append(line)
        elif not section and line.lower().startswith(("you can", "submit", "http")):
            briefing["notes"].append({"text": line, "bullet": False})
    if not briefing["objectives"]:
        raise ValueError("No objectives found. Copy the whole briefing from Discord and try again.")
    return briefing


class OcorStore:
    """The latest pasted briefing. Kept next to the script so it survives a restart
    and appears on every device viewing the page. The raw paste is saved and parsed
    again on load, so parser fixes apply to an old paste too."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.raw, self.pasted, self.briefing, self.version = "", "", None, 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.raw, self.pasted = data.get("raw", ""), data.get("pasted", "")
            self.briefing = parse_ocor(self.raw)
            self.version = 1
        except FileNotFoundError:
            pass
        except Exception as exc:
            log(f"Couldn't load the saved OCOR briefing ({exc}).")

    def set(self, text: str) -> dict:
        briefing = parse_ocor(text)          # raises ValueError if nothing usable
        with self.lock:
            self.raw, self.briefing = text, briefing
            self.pasted = now_utc().isoformat()
            self.version += 1
            tmp = self.path.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps({"pasted": self.pasted, "raw": text}, indent=2,
                                          ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError as exc:
                log(f"Couldn't save the OCOR briefing ({exc}); it will be lost on restart.")
        done = sum(1 for o in briefing["objectives"] if o.get("done"))
        log(f"OCOR briefing loaded: {len(briefing['objectives'])} objectives" + (f" ({done} done)." if done else "."))
        return briefing

    def snapshot(self) -> dict:
        with self.lock:
            if not self.briefing:
                return {"v": self.version, "objectives": []}
            return dict(self.briefing, v=self.version, pasted=self.pasted)

    def systems(self) -> list:
        """Each system the briefing names, once."""
        with self.lock:
            out = []
            for o in (self.briefing or {}).get("objectives", []):
                if o["system"] and o["system"] not in out:
                    out.append(o["system"])
            return out

    def ids(self) -> list:
        """The objectives the UFC knob steps through: those still to do (all of them if every one is done)."""
        with self.lock:
            obs = (self.briefing or {}).get("objectives", [])
            return [o["id"] for o in obs if not o.get("done")] or [o["id"] for o in obs]


# --------------------------------------------------------------------------- #
# Star coordinates, for the distance from you to each OCOR system
# --------------------------------------------------------------------------- #
COORDS_FILE = DATA_DIR / "star_coords.sqlite"
SCHEMATICS_DIR = SCRIPT_DIR / "schematics"            # Odyssey settlement layout plans, one .json file each
SETTLEMENTS_FILE = DATA_DIR / "settlements.sqlite"  # the layout you've confirmed for each settlement, and which way it faces
EDSM_SYSTEMS_API = "https://www.edsm.net/api-v1/systems"
COORDS_BATCH = 40                  # system names per EDSM request
COORDS_UNKNOWN_RETRY = 86400       # a system EDSM didn't know is asked about again after a day


def coord_key(name) -> str:
    return " ".join(str(name or "").split()).casefold()


def open_sqlite(path: Path, schema: str, table: str, what: str):
    """A SQLite file next to the script, made if it's not there. A damaged one is put aside (as .bad)
    and started again; if even that fails, the data is kept in memory for this run."""
    for attempt in (1, 2):
        db = None
        try:
            db = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute(schema)
            db.execute(f"SELECT key FROM {table} LIMIT 1").fetchall()   # proves the file is readable
            db.commit()
            return db
        except sqlite3.DatabaseError as exc:
            if db is not None:
                db.close()
            if attempt == 1 and path.exists():
                try:   # damaged: put it aside and start again
                    os.replace(path, path.with_suffix(".bad"))
                    log(f"{what} was unreadable ({exc}); starting a new one "
                        f"(the old file is kept as {path.with_suffix('.bad').name}).")
                    continue
                except OSError:
                    pass
            log(f"{what} unavailable ({exc}); keeping it in memory this run.")
            break
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.execute(schema)
    return db


class CoordCache:
    """Galactic coordinates (light years) of every system seen so far, from EDSM or from your
    journal's jumps, in star_coords.sqlite next to the script. Stars don't move, so entries
    never expire. SQLite finds a name through its index without reading the whole file, and
    adds new ones without rewriting it, so it stays quick however many systems it holds.
    Systems EDSM didn't know are noted too, so they aren't asked about again for a day."""

    SCHEMA = ("CREATE TABLE IF NOT EXISTS systems (key TEXT PRIMARY KEY, name TEXT NOT NULL, "
              "x REAL, y REAL, z REAL, source TEXT, checked REAL NOT NULL) WITHOUT ROWID")

    def __init__(self, path: Path):
        self.lock = threading.Lock()
        self.db = open_sqlite(path, self.SCHEMA, "systems", "Star coordinates cache")

    def lookup(self, names):
        """({key: (x, y, z)} for known systems, {key: time checked} for systems EDSM didn't know)."""
        keys = list({coord_key(n) for n in names if n})
        known, unknown = {}, {}
        with self.lock:
            for i in range(0, len(keys), 500):
                part = keys[i:i + 500]
                try:
                    rows = self.db.execute("SELECT key, x, y, z, checked FROM systems WHERE key IN (%s)"
                                           % ",".join("?" * len(part)), part).fetchall()
                except sqlite3.Error as exc:
                    log(f"Star coordinates lookup failed ({exc}).")
                    return known, unknown
                for key, x, y, z, checked in rows:
                    if x is None:
                        unknown[key] = checked
                    else:
                        known[key] = (x, y, z)
        return known, unknown

    def search(self, text, n=10):
        """Systems whose names start with the text (any case): [(name, (x, y, z))], at most n."""
        k = coord_key(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if not k:
            return []
        with self.lock:
            try:
                rows = self.db.execute("SELECT name, x, y, z FROM systems WHERE key LIKE ? ESCAPE '\\' AND x IS NOT NULL "
                                       "ORDER BY length(key), key LIMIT ?", (k + "%", n)).fetchall()
            except sqlite3.Error:
                return []
        return [(r[0], (r[1], r[2], r[3])) for r in rows]

    def store(self, found=None, missing=(), source="edsm"):
        """found: {name: (x, y, z)}; missing: names EDSM didn't know (never overwrite real coordinates)."""
        found, now = found or {}, time.time()
        if not found and not missing:
            return
        with self.lock:
            try:
                with self.db:   # one transaction for the lot
                    self.db.executemany(
                        "INSERT OR REPLACE INTO systems (key, name, x, y, z, source, checked) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(coord_key(n), n, float(p[0]), float(p[1]), float(p[2]), source, now) for n, p in found.items()])
                    rows = [(coord_key(n), n, now) for n in missing]
                    self.db.executemany("INSERT OR IGNORE INTO systems (key, name, checked) VALUES (?, ?, ?)", rows)
                    self.db.executemany("UPDATE systems SET checked = ? WHERE key = ? AND x IS NULL",
                                        [(now, key) for key, _, _ in rows])
            except sqlite3.Error as exc:
                log(f"Couldn't save star coordinates ({exc}).")


class SettlementLayouts:
    """The layout you've confirmed for each Odyssey settlement, in settlements.sqlite next to the
    script, kept for good. Each is keyed by the settlement's market ID (or its system and name, if
    EDSM gives no ID), so a renamed settlement keeps its layout. All are held in memory too, so the
    page's refreshes never wait on the file."""

    SCHEMA = ("CREATE TABLE IF NOT EXISTS layouts (key TEXT PRIMARY KEY, layout TEXT NOT NULL, system TEXT, "
              "name TEXT, economy TEXT, saved REAL NOT NULL) WITHOUT ROWID")

    TYPES = ("CREATE TABLE IF NOT EXISTS types (key TEXT PRIMARY KEY, category TEXT NOT NULL, system TEXT, "
             "name TEXT, saved REAL NOT NULL) WITHOUT ROWID")   # the schematic type you picked, where not the data's

    # Which way a settlement faces: the compass bearing of its layout's "up" (the site heading), for the
    # layout it was found for. source 'dock' = worked out from your ship's heading on a pad; 'manual' = set
    # with Align Settlement. locked = you aligned it by hand after a docking had set it: dockings there are
    # then ignored (until the settlement's layout changes).
    HEADINGS = ("CREATE TABLE IF NOT EXISTS headings (key TEXT PRIMARY KEY, layout TEXT NOT NULL, heading REAL NOT NULL, "
                "source TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 0, pad INTEGER, system TEXT, name TEXT, "
                "saved REAL NOT NULL) WITHOUT ROWID")

    # The last time you docked at each settlement: the pad and your ship's heading on it (kept, so a layout
    # confirmed later still gets its heading from it).
    DOCKINGS = ("CREATE TABLE IF NOT EXISTS dockings (key TEXT PRIMARY KEY, pad INTEGER NOT NULL, ship REAL NOT NULL, "
                "system TEXT, name TEXT, saved REAL NOT NULL) WITHOUT ROWID")

    # Your own waypoints on a body's surface (2 Nav > Wpt): numbered within their system, 1 up with no gaps (deleting one
    # closes the gap: those after it move down one), named "WPT 3 - A 3" unless you name them (a name of that kind follows
    # its number), kept until you delete them. method: how it was made ('manual', 'overfly' or 'desig').
    TARGETS = ("CREATE TABLE IF NOT EXISTS targets (id INTEGER PRIMARY KEY AUTOINCREMENT, system TEXT NOT NULL, "
               "body TEXT NOT NULL, num INTEGER NOT NULL, name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, "
               "method TEXT NOT NULL, saved REAL NOT NULL)")

    def __init__(self, path: Path):
        self.lock = threading.Lock()
        self.db = open_sqlite(path, self.SCHEMA, "layouts", "Settlement layouts file")
        try:
            self.known = dict(self.db.execute("SELECT key, layout FROM layouts").fetchall())
        except sqlite3.Error as exc:
            log(f"Couldn't read the settlement layouts ({exc}).")
            self.known = {}
        try:
            with self.db:
                self.db.execute(self.TYPES)
            self.types = dict(self.db.execute("SELECT key, category FROM types").fetchall())
        except sqlite3.Error as exc:
            log(f"Couldn't read the settlement types ({exc}).")
            self.types = {}
        self.headings, self.dockings = {}, {}
        try:
            with self.db:
                self.db.execute(self.HEADINGS)
                self.db.execute(self.DOCKINGS)
            for key, layout, h, src, locked, pad in self.db.execute(
                    "SELECT key, layout, heading, source, locked, pad FROM headings").fetchall():
                self.headings[key] = {"layout": layout, "h": h, "src": src, "locked": bool(locked), "pad": pad}
            for key, pad, ship, system, name in self.db.execute("SELECT key, pad, ship, system, name FROM dockings").fetchall():
                self.dockings[key] = {"pad": pad, "ship": ship, "system": system or "", "name": name or ""}
        except sqlite3.Error as exc:
            log(f"Couldn't read the settlement headings ({exc}).")
        self.targets = {}
        try:
            with self.db:
                self.db.execute(self.TARGETS)
            for row in self.db.execute("SELECT id, system, body, num, name, lat, lon, method, saved FROM targets").fetchall():
                self.targets[row[0]] = self._target(*row)
            with self.lock:   # (gaps left by deleting before 3.01.30 closed too)
                for sk in sorted({coord_key(t["system"]) for t in self.targets.values()}):
                    self._renumber(sk)
        except sqlite3.Error as exc:
            log(f"Couldn't read your targets ({exc}).")
        self._nav = {}   # coord_key(system) -> its nav record (NavBoard)
        try:
            with self.db:
                self.db.execute(self.NAV)
            for k, data in self.db.execute("SELECT sk, data FROM nav").fetchall():
                try:
                    d = json.loads(data)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    self._nav[k] = d
        except sqlite3.Error as exc:
            log(f"Couldn't read your marks and flight plans ({exc}).")

    @staticmethod
    def _target(tid, system, body, num, name, lat, lon, method, saved):
        return {"id": tid, "key": f"t{tid}", "system": system, "body": body, "num": num, "name": name,
                "lat": lat, "lon": lon, "method": method, "saved": saved}

    def targets_for(self, system):
        """Your targets in a system, by number."""
        sk = coord_key(system or "")
        with self.lock:
            return sorted((dict(t) for t in self.targets.values() if coord_key(t["system"]) == sk), key=lambda t: t["num"])

    def add_target(self, system, body, short, lat, lon, method, name=""):
        """A new waypoint on a body, numbered after the system's others and named as given, else "WPT n - <the body's
        short name>". The target, or None."""
        sk = coord_key(system)
        with self.lock:
            num = 1 + max((t["num"] for t in self.targets.values() if coord_key(t["system"]) == sk), default=0)
            name, now = name or f"WPT {num} - {short}", time.time()
            try:
                with self.db:
                    cur = self.db.execute("INSERT INTO targets (system, body, num, name, lat, lon, method, saved) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                          (system, body, num, name, lat, lon, method, now))
            except sqlite3.Error as exc:
                log(f"Couldn't save the target on {body} ({exc}).")
                return None
            t = self.targets[cur.lastrowid] = self._target(cur.lastrowid, system, body, num, name, lat, lon, method, now)
        log(f"Target: {name} at {lat:.4f}, {lon:.4f} ({method}).")
        return dict(t)

    def edit_target(self, tid, short, name, lat, lon):
        """A waypoint's name (blank: its usual "WPT n - <body>") and position changed. The waypoint, or None."""
        with self.lock:
            t = self.targets.get(tid)
            if not t:
                return None
            name = name or f"WPT {t['num']} - {short}"
            try:
                with self.db:
                    self.db.execute("UPDATE targets SET name = ?, lat = ?, lon = ? WHERE id = ?", (name, lat, lon, tid))
            except sqlite3.Error as exc:
                log(f"Couldn't change {t['name']} ({exc}).")
                return None
            t.update(name=name, lat=lat, lon=lon)
        log(f"Target changed: {name} at {lat:.4f}, {lon:.4f}.")
        return dict(t)

    def delete_target(self, tid):
        with self.lock:
            t = self.targets.get(tid)
            if not t:
                return False
            try:
                with self.db:
                    self.db.execute("DELETE FROM targets WHERE id = ?", (tid,))
            except sqlite3.Error as exc:
                log(f"Couldn't delete {t['name']} ({exc}).")
                return False
            del self.targets[tid]
            self._renumber(coord_key(t["system"]))
        log(f"Target deleted: {t['name']}.")
        return True

    def _renumber(self, sk):
        """A system's waypoints numbered 1 up again, in their order, with no gaps; a name of the usual kind ("WPT 5 - A 3")
        follows its number. (Under the lock.)"""
        mine = sorted((t for t in self.targets.values() if coord_key(t["system"]) == sk), key=lambda t: (t["num"], t["id"]))
        moved = []
        for i, t in enumerate(mine, 1):
            if t["num"] == i:
                continue
            m = re.fullmatch(r"WPT (\d+) - (.+)", t["name"])
            name = f"WPT {i} - {m.group(2)}" if m and int(m.group(1)) == t["num"] else t["name"]
            moved.append((t, i, name))
        if not moved:
            return
        try:
            with self.db:
                for t, i, name in moved:
                    self.db.execute("UPDATE targets SET num = ?, name = ? WHERE id = ?", (i, name, t["id"]))
        except sqlite3.Error as exc:
            log(f"Couldn't number the waypoints again ({exc}).")
            return
        for t, i, name in moved:
            t.update(num=i, name=name)
        log(f"Waypoints in {mine[0]['system']} numbered 1-{len(mine)} again.")

    # 2 Nav's waypoint system for each system (NavBoard): your marks (MK1-MK9), the SEQ 1-3 flight plans, the steer-to
    # point, the designated target, offset aimpoints and Atk's attack plan - one JSON record a system.
    NAV = ("CREATE TABLE IF NOT EXISTS nav (sk TEXT PRIMARY KEY, system TEXT NOT NULL, data TEXT NOT NULL, "
           "saved REAL NOT NULL) WITHOUT ROWID")

    def nav_get(self, system):
        """The nav record for a system ({} if there's none)."""
        sk = coord_key(system or "")
        with self.lock:
            return json.loads(json.dumps(self._nav.get(sk) or {}))

    def nav_put(self, system, data):
        """Keep a system's nav record. True if it was saved."""
        sk = coord_key(system or "")
        if not sk:
            return False
        with self.lock:
            text = json.dumps(data, separators=(",", ":"))
            try:
                with self.db:
                    self.db.execute("INSERT OR REPLACE INTO nav (sk, system, data, saved) VALUES (?, ?, ?, ?)",
                                    (sk, system, text, time.time()))
            except sqlite3.Error as exc:
                log(f"Couldn't save your marks and flight plans ({exc}).")
                return False
            self._nav[sk] = json.loads(text)
        return True

    def headings_for(self, keys):
        """Each settlement's heading: {key: {"layout", "h", "src", "locked", "pad"}} (the page uses it only
        while that layout is the one shown)."""
        with self.lock:
            return {k: dict(self.headings[k]) for k in keys if k in self.headings}

    def save_heading(self, key, layout, heading, source, pad=None, system="", name=""):
        """A settlement's heading. A docking sets it unless you've aligned it by hand since a docking did
        (then it's ignored); aligning by hand after a docking locks it. True if saved."""
        heading = round(float(heading) % 360, 1)
        with self.lock:
            prev = self.headings.get(key)
            same = bool(prev and prev["layout"] == layout)
            if source == "dock":
                if same and prev["locked"]:
                    log(f"Settlement heading: {name or key} - docking ignored (you aligned it by hand).")
                    return False
                locked = False
            else:
                source, pad = "manual", None
                locked = same and (prev["src"] == "dock" or prev["locked"])
            try:
                with self.db:
                    self.db.execute("INSERT OR REPLACE INTO headings (key, layout, heading, source, locked, pad, system, name, saved) "
                                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (key, layout, heading, source, int(locked), pad, system, name, time.time()))
            except sqlite3.Error as exc:
                log(f"Couldn't save the heading for {name or key} ({exc}).")
                return False
            self.headings[key] = {"layout": layout, "h": heading, "src": source, "locked": locked, "pad": pad}
        how = f"from pad {pad}" if source == "dock" else "aligned by hand" + (" (dockings now ignored)" if locked else "")
        log(f"Settlement heading: {name or key} faces {heading:.0f}° ({how}).")
        return True

    def save_docking(self, key, pad, ship, system="", name=""):
        with self.lock:
            try:
                with self.db:
                    self.db.execute("INSERT OR REPLACE INTO dockings (key, pad, ship, system, name, saved) VALUES (?, ?, ?, ?, ?, ?)",
                                    (key, int(pad), float(ship), system, name, time.time()))
            except sqlite3.Error as exc:
                log(f"Couldn't save the docking at {name or key} ({exc}).")
                return False
            self.dockings[key] = {"pad": int(pad), "ship": float(ship), "system": system, "name": name}
        return True

    def types_for(self, keys):
        with self.lock:
            return {k: self.types[k] for k in keys if k in self.types}

    def save_type(self, key, category, system="", name=""):
        """The schematic type picked for a settlement ('' = back to the data's)."""
        with self.lock:
            try:
                with self.db:
                    if category:
                        self.db.execute("INSERT OR REPLACE INTO types (key, category, system, name, saved) VALUES (?, ?, ?, ?, ?)",
                                        (key, category, system, name, time.time()))
                    else:
                        self.db.execute("DELETE FROM types WHERE key = ?", (key,))
            except sqlite3.Error as exc:
                log(f"Couldn't save the type for {name or key} ({exc}).")
                return False
            if category:
                self.types[key] = category
            else:
                self.types.pop(key, None)
        log(f"Settlement type: {name or key} is {category or 'as its data says'}.")
        return True

    def for_keys(self, keys):
        with self.lock:
            return {k: self.known[k] for k in keys if k in self.known}

    def save(self, key, layout, system="", name="", economy=""):
        with self.lock:
            try:
                with self.db:
                    self.db.execute("INSERT OR REPLACE INTO layouts (key, layout, system, name, economy, saved) "
                                    "VALUES (?, ?, ?, ?, ?, ?)", (key, layout, system, name, economy, time.time()))
            except sqlite3.Error as exc:
                log(f"Couldn't save the layout for {name or key} ({exc}).")
                return False
            self.known[key] = layout
        log(f"Settlement layout: {name or key} is {layout}.")
        return True


def settlement_key(system, station):
    """What a settlement's confirmed layout is kept under: its market ID, else its system and name."""
    if station.get("marketId"):
        return f"m:{station['marketId']}"
    return f"n:{coord_key(system)}|{str(station.get('name') or '').casefold()}"


def heading_from_docking(settlements, schematics, key):
    """A settlement's heading from your last docking there: your ship's heading on the pad, less the pad's
    turn from the layout's pad 1 (SrvSurvey's pad directions). Only with a confirmed layout and a pad whose
    direction is recorded (every pad 1, and the others with a rotation). The heading, or None."""
    if not settlements or not schematics:
        return None
    with settlements.lock:
        layout, dock = settlements.known.get(key), settlements.dockings.get(key)
    if not layout or not dock:
        return None
    plan = schematics.plan(layout)
    pad = next((p for p in (plan or {}).get("pads", []) if p.get("num") == dock["pad"]), None)
    if not pad or not pad.get("rec"):
        if plan:
            log(f"Settlement heading: {dock['name'] or key} - pad {dock['pad']}'s direction isn't recorded for {layout}.")
        return None
    heading = round((dock["ship"] - (pad.get("rot") or 0)) % 360, 1)
    ok = settlements.save_heading(key, layout, heading, "dock", dock["pad"], dock["system"], dock["name"])
    return heading if ok else None


# --------------------------------------------------------------------------- #
# What your own journals say about systems (used wherever Spansh has nothing)
# --------------------------------------------------------------------------- #
RECORDS_FILE = DATA_DIR / "journal_records.sqlite"   # bodies, stations and settlement positions from your journals
RECORD_EVENTS = ("Scan", "ApproachSettlement", "Docked", "Location", "FSSSignalDiscovered", "FSDJump", "CarrierJump")
MOVING_KEEP_DAYS = 7         # a megaship moves on: one seen only in your journal is shown for a week

# The journal's names for things -> the names EDSM uses (the rest of the tab goes by them)
JOURNAL_STATION_TYPES = {
    "coriolis": "Coriolis Starport", "orbis": "Orbis Starport", "ocellus": "Ocellus Starport", "bernal": "Ocellus Starport",
    "dodec": "Dodec Starport", "outpost": "Outpost", "asteroidbase": "Asteroid base", "megaship": "Mega ship",
    "fleetcarrier": "Fleet Carrier", "squadroncarrier": "Squadron Carrier", "crateroutpost": "Planetary Outpost",
    "craterport": "Planetary Port", "surfacestation": "Planetary Port", "onfootsettlement": "Odyssey Settlement",
    "planetaryconstructiondepot": "Planetary Construction Depot", "spaceconstructiondepot": "Space Construction Depot",
}
SIGNAL_STATION_TYPES = {   # FSS signals worth keeping: fixed stations, installations and beacons (carriers move, so not them)
    "stationcoriolis": "Coriolis Starport", "stationoneilorbis": "Orbis Starport", "stationoneilcylinder": "Ocellus Starport",
    "stationbernalsphere": "Ocellus Starport", "stationasteroid": "Asteroid base", "stationdodec": "Dodec Starport",
    "stationmegaship": "Mega ship", "megaship": "Mega ship", "outpost": "Outpost", "installation": "Installation",
    "navbeacon": "Nav Beacon", "touristbeacon": "Tourist Beacon",
}
PLANET_CLASSES = {
    "metal rich body": "Metal-rich body", "high metal content body": "High metal content world", "rocky body": "Rocky body",
    "icy body": "Icy body", "rocky ice body": "Rocky Ice world", "earthlike body": "Earth-like world",
    "water world": "Water world", "ammonia world": "Ammonia world", "water giant": "Water giant",
    "water giant with life": "Water giant with life", "gas giant with water based life": "Gas giant with water-based life",
    "gas giant with ammonia based life": "Gas giant with ammonia-based life", "helium rich gas giant": "Helium-rich gas giant",
    "helium gas giant": "Helium gas giant",
}
RING_CLASSES = {"eringclass_metalrich": "Metal Rich", "eringclass_metalic": "Metallic", "eringclass_rocky": "Rocky", "eringclass_icy": "Icy"}
SERVICE_NAMES = {
    "refuel": "Refuel", "repair": "Repair", "rearm": "Restock", "contacts": "Contacts", "missions": "Missions",
    "crewlounge": "Crew Lounge", "searchrescue": "Search and Rescue", "tuning": "Tuning", "blackmarket": "Black Market",
    "materialtrader": "Material Trader", "techbroker": "Technology Broker", "facilitator": "Interstellar Factors",
    "shop": "Pioneer Supplies", "bartender": "Bartender", "vistagenomics": "Vista Genomics", "frontlinesolutions": "Frontline Solutions",
    "apexinterstellar": "Apex Interstellar", "refinery": "Refinery Contact", "exploration": "Universal Cartographics",
    "socialspace": "Social Space", "engineer": "Engineer", "powerplay": "Powerplay", "livery": "Livery",
}


def _cap(s):
    s = str(s or "").strip()
    return s[:1].upper() + s[1:]


def body_from_scan(ev):
    """A journal Scan, as EDSM would describe the body (so it can stand in for one EDSM doesn't have)."""
    name = str(ev.get("BodyName") or "")
    if not name or not (ev.get("StarType") or ev.get("PlanetClass")):   # belt clusters and the like
        return None
    star = bool(ev.get("StarType"))
    b = {"name": name, "bodyId": ev.get("BodyID"), "type": "Star" if star else "Planet",
         "distanceToArrival": ev.get("DistanceFromArrivalLS"), "parents": ev.get("Parents") or None,
         "surfaceTemperature": ev.get("SurfaceTemperature"), "axialTilt": ev.get("AxialTilt"),
         "rotationalPeriod": ev["RotationPeriod"] / 86400 if isinstance(ev.get("RotationPeriod"), (int, float)) else None,
         "orbitalPeriod": ev["OrbitalPeriod"] / 86400 if isinstance(ev.get("OrbitalPeriod"), (int, float)) else None,
         "_journal": True, "_seen": ev.get("timestamp", "")}
    rings = [{"name": r.get("Name") or "", "type": RING_CLASSES.get(str(r.get("RingClass") or "").lower(), "Rocky"),
              "innerRadius": (r.get("InnerRad") or 0) / 1000, "outerRadius": (r.get("OuterRad") or 0) / 1000}
             for r in ev.get("Rings") or [] if isinstance(r, dict)]
    if star:
        code, sub_n = str(ev["StarType"]), ev.get("Subclass")
        b["subType"] = star_placeholder(code)["sub"]
        b["spectralClass"] = f"{code}{sub_n}" if sub_n is not None and len(code) <= 3 else code
        b["luminosity"] = ev.get("Luminosity") or ""
        b["isMainStar"] = not ev.get("DistanceFromArrivalLS")
        b["isScoopable"] = code[:1] in "KGBFOAM" and "_" not in code or code in ("K_OrangeGiant", "M_RedGiant", "M_RedSuperGiant")
        b["solarMasses"] = ev.get("StellarMass")
        b["solarRadius"] = (ev.get("Radius") or 0) / SOLAR_RADIUS_M or None
        b["age"] = ev.get("Age_MY")
        b["belts"] = [{"name": r["name"], "type": r["type"]} for r in rings] or None
    else:
        pc = str(ev["PlanetClass"])
        m = re.match(r"Sudarsky class (\w+) gas giant", pc, re.I)
        b["subType"] = f"Class {m.group(1)} gas giant" if m else PLANET_CLASSES.get(pc.lower(), pc)
        b["isLandable"] = bool(ev.get("Landable"))
        tf = str(ev.get("TerraformState") or "")
        b["terraformingState"] = {"terraformable": "Candidate for terraforming"}.get(tf.lower(), tf) or "Not terraformable"
        b["radius"] = (ev.get("Radius") or 0) / 1000 or None
        b["gravity"] = ev["SurfaceGravity"] / 9.80665 if isinstance(ev.get("SurfaceGravity"), (int, float)) else None
        b["surfacePressure"] = ev["SurfacePressure"] / 101325 if isinstance(ev.get("SurfacePressure"), (int, float)) else None
        b["atmosphereType"] = _cap(ev.get("Atmosphere")) or "No atmosphere"
        b["volcanismType"] = _cap(ev.get("Volcanism")) or "No volcanism"
        b["rotationalPeriodTidallyLocked"] = bool(ev.get("TidalLock"))
        b["rings"] = rings or None
        mats = {_cap(x.get("Name")): x.get("Percent") for x in ev.get("Materials") or [] if isinstance(x, dict) and x.get("Name")}
        b["materials"] = dict(sorted(mats.items(), key=lambda kv: -(kv[1] or 0))) or None
        air = {_cap(x.get("Name")): x.get("Percent") for x in ev.get("AtmosphereComposition") or [] if isinstance(x, dict) and x.get("Name")}
        b["atmosphereComposition"] = air or None
    return {k: v for k, v in b.items() if v is not None}


def station_from_event(ev):
    """A station, settlement, installation or beacon as Docked / Location / ApproachSettlement / an FSS
    signal describes it, EDSM-shaped (missing parts are left out); None if the event names none."""
    kind = ev.get("event")
    s = {"_journal": True, "_seen": ev.get("timestamp", "")}
    if kind == "FSSSignalDiscovered":
        stype = SIGNAL_STATION_TYPES.get(str(ev.get("SignalType") or "").lower())
        name = str(ev.get("SignalName_Localised") or ev.get("SignalName") or "")
        if not stype or not name or name.startswith("$"):
            return None
        s.update(name=name, type=stype)
        return s
    name = ev.get("Name") if kind == "ApproachSettlement" else ev.get("StationName")
    if not name or (kind == "Location" and not ev.get("Docked")):
        return None
    s["name"] = str(name)
    if ev.get("MarketID"):
        s["marketId"] = ev["MarketID"]
    if ev.get("StationType"):
        s["type"] = JOURNAL_STATION_TYPES.get(str(ev["StationType"]).lower(), _cap(ev["StationType"]))
    econs = [e.get("Name_Localised") or _cap(str(e.get("Name") or "").strip("$;").replace("economy_", ""))
             for e in ev.get("StationEconomies") or [] if isinstance(e, dict)]
    econ = ev.get("StationEconomy_Localised") or (econs[0] if econs else "")
    if econ:
        s["economy"] = econ
    if len(econs) > 1 and econs[1] != econ:
        s["secondEconomy"] = econs[1]
    if ev.get("StationGovernment_Localised"):
        s["government"] = ev["StationGovernment_Localised"]
    if ev.get("StationAllegiance"):
        s["allegiance"] = ev["StationAllegiance"]
    if (ev.get("StationFaction") or {}).get("Name"):
        s["controllingFaction"] = {"name": ev["StationFaction"]["Name"]}
    services = [str(x).lower() for x in ev.get("StationServices") or []]
    if services:
        s["haveMarket"], s["haveShipyard"], s["haveOutfitting"] = ("commodities" in services, "shipyard" in services,
                                                                   "outfitting" in services)
        s["otherServices"] = [SERVICE_NAMES[x] for x in services if x in SERVICE_NAMES]
    if isinstance(ev.get("DistFromStarLS"), (int, float)):
        s["distanceToArrival"] = ev["DistFromStarLS"]
    pads = ev.get("LandingPads")
    if isinstance(pads, dict):   # (Docked gives them)
        s["landingPads"] = {k.lower(): int(pads.get(k) or 0) for k in ("Small", "Medium", "Large")}
    body = {}
    if kind == "ApproachSettlement":
        body = {"name": ev.get("BodyName"), "id": ev.get("BodyID"), "latitude": ev.get("Latitude"), "longitude": ev.get("Longitude")}
    elif kind == "Location" and ev.get("BodyType") == "Planet":
        body = {"name": ev.get("Body"), "id": ev.get("BodyID"), "latitude": ev.get("Latitude"), "longitude": ev.get("Longitude")}
    body = {k: v for k, v in body.items() if v is not None}
    if body.get("name"):
        s["body"] = body
    return s


def _merge_record(old, new):
    """One record updated with another: the newer sighting's details win, but nothing known is lost."""
    newer = str(new.get("_seen") or "") >= str(old.get("_seen") or "")
    out = dict(old)
    for k, v in new.items():
        if k == "body" and isinstance(v, dict):
            ob = old.get("body") or {}
            out["body"] = dict(ob, **v) if newer or ob.get("latitude") is None else dict(v, **ob)
        elif newer or out.get(k) in (None, "", [], {}):
            out[k] = v
    if not newer:
        out["_seen"] = old.get("_seen")
    return out


class JournalRecords:
    """What your own journals say about the systems you've been to - bodies (Scan), stations
    (Docked, Location), where settlements are (ApproachSettlement), installations and beacons (FSS
    signals) - kept for good in journal_records.sqlite next to the script. The System tab uses them
    wherever Spansh has nothing: a body or station it doesn't list, a station it can't place on its
    planet, or a system it doesn't know at all. Fleet carriers aren't kept (they move). Your older
    journals are read once, in the background, to fill it; every new event adds to it."""

    SCHEMA = ("CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, system TEXT NOT NULL, kind TEXT NOT NULL, "
              "data TEXT NOT NULL) WITHOUT ROWID")

    def __init__(self, path: Path):
        self.lock = threading.RLock()
        self.db = open_sqlite(path, self.SCHEMA, "records", "Journal records file")
        try:
            self.db.execute("CREATE INDEX IF NOT EXISTS records_system ON records (system, kind)")
            self.db.commit()
        except sqlite3.Error:
            pass
        self.names = {}       # system address -> name (FSS signals give only the address)
        self.versions = {}    # system -> how many times its records have changed (the tab rebuilds when it moves)

    def version(self, system):
        return self.versions.get(coord_key(system), 0)

    def note(self, ev):
        """Take what one journal event says. Returns True if it changed anything."""
        kind = ev.get("event")
        if kind not in RECORD_EVENTS:
            return False
        with self.lock:
            if ev.get("StarSystem") and ev.get("SystemAddress"):
                self.names[ev["SystemAddress"]] = ev["StarSystem"]
            system = ev.get("StarSystem") or self.names.get(ev.get("SystemAddress"))
            if not system:
                return False
            if kind == "Scan":
                rec = body_from_scan(ev)
                return bool(rec) and self._put(system, "body", rec["name"].lower(), rec)
            if kind in ("ApproachSettlement", "Docked", "Location", "FSSSignalDiscovered"):
                rec = station_from_event(ev)
                if not rec or "Carrier" in str(rec.get("type") or ""):   # carriers move: not kept
                    return False
                return self._put(system, "station", self._station_ident(system, rec), rec)
            return False

    def _station_ident(self, system, rec):
        """A station's record is kept under its market ID; one first seen by name only (an FSS signal)
        is folded into it when the ID turns up."""
        by_name = f"n:{rec['name'].casefold()}"
        if not rec.get("marketId"):
            row = self.db.execute("SELECT key, data FROM records WHERE system = ? AND kind = 'station'", (coord_key(system),)).fetchall()
            for key, data in row:
                try:
                    if json.loads(data).get("name", "").casefold() == rec["name"].casefold():
                        return key.split("|", 2)[2]
                except ValueError:
                    continue
            return by_name
        ident = f"m:{rec['marketId']}"
        old = self.db.execute("SELECT data FROM records WHERE key = ?", (f"station|{coord_key(system)}|{by_name}",)).fetchone()
        if old:   # seen by name before: fold it in
            try:
                self._put(system, "station", ident, json.loads(old[0]), bump=False)
                self.db.execute("DELETE FROM records WHERE key = ?", (f"station|{coord_key(system)}|{by_name}",))
            except (ValueError, sqlite3.Error):
                pass
        return ident

    def _put(self, system, kind, ident, rec, bump=True):
        key = f"{kind}|{coord_key(system)}|{ident}"
        try:
            row = self.db.execute("SELECT data FROM records WHERE key = ?", (key,)).fetchone()
            old = json.loads(row[0]) if row else None
            new = _merge_record(old, rec) if old else rec
            if new == old:
                return False
            self.db.execute("INSERT OR REPLACE INTO records (key, system, kind, data) VALUES (?, ?, ?, ?)",
                            (key, coord_key(system), kind, json.dumps(new, ensure_ascii=False)))
            if not getattr(self, "batch", False):
                self.db.commit()
        except (sqlite3.Error, ValueError) as exc:
            log(f"Couldn't keep a journal record for {system} ({exc}).")
            return False
        if bump:
            self.versions[coord_key(system)] = self.versions.get(coord_key(system), 0) + 1
        return True

    def for_system(self, system):
        """{'bodies': [...], 'stations': [...]}: what your journals say about this system, EDSM-shaped."""
        out = {"bodies": [], "stations": []}
        with self.lock:
            try:
                rows = self.db.execute("SELECT kind, data FROM records WHERE system = ?", (coord_key(system),)).fetchall()
            except sqlite3.Error:
                return out
        for kind, data in rows:
            try:
                rec = json.loads(data)
            except ValueError:
                continue
            if kind in ("body", "station"):
                out["bodies" if kind == "body" else "stations"].append(rec)
        return out

    def backfill(self, journal_dir: Path):
        """Read every journal not read before (or grown since) for records. Runs once, in the background."""
        try:
            paths = sorted(journal_dir.glob("Journal.*.log"))
        except OSError:
            return
        done = 0
        for path in paths:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            fkey = f"file||{path.name}"
            with self.lock:
                row = self.db.execute("SELECT data FROM records WHERE key = ?", (fkey,)).fetchone()
            if row and row[0] == str(size):
                continue
            needles = tuple(f'"{k}"'.encode() for k in RECORD_EVENTS)   # a quick look first; note() checks properly
            try:
                with open(path, "rb") as fh:
                    lines = [ln for ln in fh if any(n in ln for n in needles)]
            except OSError:
                continue
            with self.lock:
                self.batch = True
                try:
                    for ln in lines:
                        try:
                            ev = json.loads(ln.decode("utf-8", errors="replace"))
                        except ValueError:
                            continue
                        self.note(ev)
                    self.db.execute("INSERT OR REPLACE INTO records (key, system, kind, data) VALUES (?, '', 'file', ?)",
                                    (fkey, str(size)))
                    self.db.commit()
                except sqlite3.Error as exc:
                    log(f"Couldn't keep journal records from {path.name} ({exc}).")
                finally:
                    self.batch = False
            done += 1
        if done:
            log(f"Journal records: read {done} journal file{'s' if done != 1 else ''} for bodies, stations and settlement positions.")


STATION_FIXED = ("type", "landingPads")   # a station's facts that don't change: your journal's win
STATION_CHANGING = ("controllingFaction", "government", "allegiance", "economy", "secondEconomy",
                    "haveMarket", "haveShipyard", "haveOutfitting", "otherServices")   # ... these do: the newer record's win


def _web_time(s):
    """When Spansh or EDSM last heard about a station ("2026-10-30 08:57:07"), as the journal writes times."""
    t = str((s.get("updateTime") or {}).get("information") or "")
    return t.replace(" ", "T") + "Z" if t else ""


def merge_records(raw, rec, now=None):
    """Spansh's (or EDSM's) answers (raw, as cached) with what your journals say. Your journal wins where it
    knows: a body you've scanned takes your scan's figures (marked as yours); a station takes your journal's
    type, landing pads and position (a settlement's, from approaching it), and its faction, government,
    economy and services too if your journal's are newer than the site's; bodies and stations the site doesn't
    list are added. A station whose planet is known to neither gets a stand-in for that planet, so it can still
    be shown on it. Returns a new raw; the cache is left as it was."""
    rec = rec or {}
    out = dict(raw)
    bodies = [dict(b) for b in (raw.get("bodies") or {}).get("bodies") or [] if b.get("name")]
    by_body = {b["name"].lower(): b for b in bodies}
    extra, changed = [], False
    for j in rec.get("bodies") or []:
        if not j.get("name"):
            continue
        b = by_body.get(j["name"].lower())
        if b is None:
            extra.append(dict(j))
            continue
        for k, v in j.items():   # your scan: the body's figures are yours (the site keeps what your scan doesn't give, and its ids)
            if not k.startswith("_") and k not in ("name", "id", "bodyId", "parents") and v is not None and b.get(k) != v:
                b[k] = v
                b["_jfill"] = True
        b["_jscan"] = j.get("_seen") or True
        changed = True
    known = set(by_body) | {b["name"].lower() for b in extra}
    stations = [dict(s) for s in (raw.get("stations") or {}).get("stations") or [] if s.get("name")]
    by_mid = {s["marketId"]: s for s in stations if s.get("marketId")}
    by_name = {s["name"].lower(): s for s in stations}
    cutoff = datetime.fromtimestamp((now or time.time()) - MOVING_KEEP_DAYS * 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for j in rec.get("stations") or []:
        s = (by_mid.get(j.get("marketId")) if j.get("marketId") else None) or by_name.get(str(j.get("name", "")).lower())
        if s is None:
            if j.get("type") == "Mega ship" and str(j.get("_seen") or "") < cutoff:
                continue   # it's moved on by now
            s = dict(j, updateTime={"information": str(j.get("_seen") or "").replace("T", " ").rstrip("Z")})
            if not s.get("type") and (s.get("body") or {}).get("latitude") is not None:
                s["type"] = "Settlement"   # approached but never docked at: a settlement of some kind
            stations.append(s)
            by_name[s["name"].lower()] = s
            continue
        jb, sb = j.get("body") or {}, s.get("body") or {}
        if jb.get("latitude") is not None:   # where you found it: yours
            if (sb.get("latitude"), sb.get("longitude")) != (jb.get("latitude"), jb.get("longitude")):
                s["body"] = dict(sb, **{k: v for k, v in jb.items() if v is not None})
                s["_jpos"] = j.get("_seen") or True
        elif jb.get("name") and not sb.get("name"):
            s["body"] = dict(sb, name=jb["name"])
            s["_jfill"] = True
        for k in STATION_FIXED:
            if j.get(k) not in (None, "", {}) and s.get(k) != j[k]:
                s[k] = j[k]
                s["_jfill"] = True
        if s.get("distanceToArrival") in (None, "") and j.get("distanceToArrival") not in (None, ""):
            s["distanceToArrival"] = j["distanceToArrival"]
            s["_jfill"] = True
        if str(j.get("_seen") or "") > _web_time(s):   # your journal's newer: its faction, economy and services
            for k in STATION_CHANGING:
                if j.get(k) not in (None, "") and s.get(k) != j[k]:
                    s[k] = j[k]
                    s["_jfill"] = True
    for s in stations:   # a station on a planet nobody's body list has: a stand-in for the planet, to show it on
        sb = s.get("body") or {}
        if sb.get("name") and sb["name"].lower() not in known and sb.get("latitude") is not None:
            extra.append({"name": sb["name"], "bodyId": sb.get("id"), "type": "Planet", "subType": "Planet",
                          "distanceToArrival": s.get("distanceToArrival"), "isLandable": True, "_journal": True,
                          "_standin": True, "_seen": str(s.get("_seen") or s.get("_jpos") or "")})
            known.add(sb["name"].lower())
    if extra or changed:
        out["bodies"] = dict(raw.get("bodies") or {}, bodies=bodies + extra)
    if stations or raw.get("stations"):
        out["stations"] = dict(raw.get("stations") or {}, stations=stations)
    return out


# --------------------------------------------------------------------------- #
# Spansh (spansh.co.uk): a system's bodies and stations, in one record by its 64-bit address
# --------------------------------------------------------------------------- #
SPANSH_API = os.environ.get("EDTB_SPANSH_API") or "https://spansh.co.uk/api/"   # (the env var is for the tests)
SPANSH_TYPES = {"settlement": "Odyssey Settlement", "drake-class carrier": "Fleet Carrier"}   # Spansh's names -> the board's (EDSM's)
SPANSH_QUIET_SERVICES = {"dock", "autodock", "market", "shipyard", "outfitting", "missions generated", "flight controller",
                         "station operations", "station menu", "workshop", "commodities", "on dock mission"}   # not worth listing
SOURCE_NAMES = {"spansh": "Spansh", "edsm": "EDSM", "journal": "your journal"}


SIGNAL_NAMES = {"biological": "Biological", "geological": "Geological", "human": "Human", "guardian": "Guardian",
                "thargoid": "Thargoid", "other": "Other", "planetarymininglocation": "Mining"}   # (Spansh's codes, shortened)
GENUS_NAMES = {"aleoids": "Aleoida", "bacterial": "Bacterium", "cactoid": "Cactoida", "clypeus": "Clypeus", "conchas": "Concha",
               "electricae": "Electricae", "fonticulus": "Fonticulua", "shrubs": "Frutexa", "fumerolas": "Fumerola",
               "fungoids": "Fungoida", "osseus": "Osseus", "recepta": "Recepta", "stratum": "Stratum", "tubus": "Tubus",
               "tussocks": "Tussock", "brancae": "Brain Tree", "cone": "Bark Mound", "ground_struct_ice": "Crystalline Shards",
               "tube": "Sinuous Tubers", "vents": "Amphora Plant", "sphere": "Anemone", "seed": "Seed Pod"}


def spansh_signals(sig):
    """Spansh's signals on a body: {"counts": {"Biological": 3, "Human": 6, ...}, "genuses": ["Tubus", ...]}, or None.
    ("$SAA_SignalType_Biological;" -> Biological, "$PlanetaryMiningLocation_Name;" -> Mining, "$Codex_Ent_Tubus_Genus_Name;" -> Tubus)"""
    if not isinstance(sig, dict):
        return None
    counts = {}
    for code, n in (sig.get("signals") or {}).items():
        if not isinstance(n, (int, float)) or isinstance(n, bool) or n <= 0:
            continue
        key = re.sub(r"^\$|;$", "", str(code))
        key = re.sub(r"^SAA_SignalType_", "", key)
        key = re.sub(r"_Name$", "", key)
        name = SIGNAL_NAMES.get(key.lower()) or ("Mining" if "mining" in key.lower() else key.replace("_", " "))
        counts[name] = counts.get(name, 0) + int(n)
    genuses = []
    for code in sig.get("genuses") or []:
        key = re.sub(r"^\$Codex_Ent_|_Genus_Name;?$", "", str(code))
        name = GENUS_NAMES.get(key.lower()) or key.replace("_", " ")
        if name and name not in genuses:
            genuses.append(name)
    return {"counts": counts, "genuses": genuses} if counts or genuses else None


def strip_spansh(system):
    """Spansh's system record, cut to what the board keeps: no market prices, outfitting modules, ships
    for sale or faction lists (just when each service was last updated)."""
    if not isinstance(system, dict):
        return {}

    def cut(st):
        st = dict(st)
        for k in ("market", "outfitting", "shipyard"):
            if isinstance(st.get(k), dict):
                st[k] = {"updateTime": st[k].get("updateTime")}
        return st
    out = {k: v for k, v in system.items() if k not in ("factions", "bodies", "stations")}
    out["stations"] = [cut(x) for x in system.get("stations") or [] if isinstance(x, dict)]
    out["bodies"] = [dict({k: v for k, v in b.items() if k != "stations"},
                          stations=[cut(x) for x in b.get("stations") or [] if isinstance(x, dict)])
                     for b in system.get("bodies") or [] if isinstance(b, dict)]
    return out


def _spansh_time(v):
    """Spansh's "2026-10-30T08:57:07Z" -> "2026-10-30 08:57:07", as the rest of the tab has its times."""
    return str(v).replace("T", " ").rstrip("Z")[:19] if v else None


def spansh_raw(system):
    """A Spansh system record (stripped) in the shape the tab is built from (EDSM's): {"bodies": {...},
    "stations": {...}}. A station Spansh gives no type, on a planet, is a settlement of some kind (only
    approached, never docked at: it may be an Odyssey settlement, or not)."""
    if not isinstance(system, dict) or not system.get("name"):
        return {}
    id64, name = system.get("id64"), system["name"]

    def station(st, body):
        lat, lon = st.get("latitude"), st.get("longitude")
        kind = st.get("type")
        kind = SPANSH_TYPES.get(str(kind).lower(), kind) if kind else ("Settlement" if lat is not None else None)
        econ = {k: v for k, v in (st.get("economies") or {}).items() if isinstance(v, (int, float))} if isinstance(st.get("economies"), dict) else {}
        first = st.get("primaryEconomy") or (max(econ, key=econ.get) if econ else None)
        second = next((k for k, _ in sorted(econ.items(), key=lambda kv: -kv[1]) if k != first), None)
        services = [str(x) for x in st.get("services") or []]
        low = {x.lower() for x in services}
        upd = {"information": _spansh_time(st.get("updateTime"))}
        for part in ("market", "shipyard", "outfitting"):
            upd[part] = _spansh_time((st.get(part) or {}).get("updateTime")) if isinstance(st.get(part), dict) else None
        out = {"marketId": st.get("id"), "name": st.get("name"), "type": kind, "distanceToArrival": st.get("distanceToArrival"),
               "allegiance": st.get("allegiance"), "government": st.get("government"), "economy": first, "secondEconomy": second,
               "haveMarket": "market" in low or isinstance(st.get("market"), dict),
               "haveShipyard": "shipyard" in low or isinstance(st.get("shipyard"), dict),
               "haveOutfitting": "outfitting" in low or isinstance(st.get("outfitting"), dict),
               "otherServices": [x for x in services if x.lower() not in SPANSH_QUIET_SERVICES], "updateTime": upd, "_from": "spansh"}
        if st.get("controllingFaction"):
            out["controllingFaction"] = {"name": str(st["controllingFaction"])}
        pads = st.get("landingPads")
        if isinstance(pads, dict):
            out["landingPads"] = {k: int(pads.get(k) or 0) for k in ("small", "medium", "large")}
        if body is not None:
            out["body"] = {k: v for k, v in (("id", body.get("id64")), ("name", body.get("name")), ("latitude", lat), ("longitude", lon))
                           if v is not None}
        return {k: v for k, v in out.items() if v is not None}

    bodies, stations = [], []
    for b in system.get("bodies") or []:
        for st in b.get("stations") or []:
            if st.get("name"):
                stations.append(station(st, b))
        if b.get("type") not in ("Star", "Planet") or not b.get("name"):
            continue   # (barycentres: the tab works out its tree without them)
        x = {k: v for k, v in b.items() if k not in ("stations", "timestamps", "signals", "mainStar")}
        x.update(id=b.get("id64"), isMainStar=bool(b.get("mainStar")), updateTime=_spansh_time(b.get("updateTime")), _from="spansh")
        sig = spansh_signals(b.get("signals"))
        if sig:
            x["signals"] = sig
        if b["type"] == "Star":
            x["isScoopable"] = (str(b.get("spectralClass") or b.get("subType") or "")[:1] or "?") in "OBAFGKM"
        elif not x.get("atmosphereType"):
            x["atmosphereType"] = "No atmosphere"
        for k in ("rings", "belts"):   # Spansh gives their radii in metres, the tab (as EDSM) in km
            if isinstance(b.get(k), list):
                x[k] = [dict({f: v for f, v in r.items() if f not in ("signals", "id64")},
                             **{f: r[f] / 1000 for f in ("innerRadius", "outerRadius") if isinstance(r.get(f), (int, float))})
                        for r in b[k] if isinstance(r, dict)]
        bodies.append(x)
    for st in system.get("stations") or []:   # in orbit (Spansh doesn't say round which body)
        if st.get("name"):
            stations.append(station(st, None))
    return {"bodies": {"id64": id64, "name": name, "bodyCount": system.get("bodyCount"), "bodies": bodies},
            "stations": {"id64": id64, "name": name, "stations": stations}}


def spansh_get(path):
    """GET a Spansh API path: its answer (parsed), or None if Spansh has no such record (404)."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(SPANSH_API + path, headers={"User-Agent": user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def spansh_find(name, get=spansh_get):
    """A system by name from Spansh's search: {"name", "id64", "x", "y", "z"} for the exact name, or None."""
    from urllib.parse import quote
    answer = get(f"search/systems?q={quote(name)}") or {}
    for r in (answer.get("results") or []) if isinstance(answer, dict) else []:
        if isinstance(r, dict) and str(r.get("name", "")).lower() == name.lower() and isinstance(r.get("id64"), int):
            return r
    return None


def entry_source(x):
    """Where a body or station came from, as the page names it: "spansh", "edsm", "journal", or several
    ("spansh+journal": Spansh's, with your journal adding to it)."""
    if x.get("_journal"):
        return "journal"
    parts = [x.get("_from") or "edsm"]
    if x.get("_jpos") or x.get("_jfill"):
        parts.append("journal")
    return "+".join(parts)


# --------------------------------------------------------------------------- #
# Your history, from every journal: where you've been (Nav › Hist) and the missions you've finished
# (Contracts › History)
# --------------------------------------------------------------------------- #
HISTORY_EVENTS = ("FSDJump", "CarrierJump", "Docked", "ApproachBody", "Touchdown", "ApproachSettlement", "Location",
                  "MissionAccepted", "MissionRedirected", "MissionCompleted", "MissionFailed", "MissionAbandoned")
HISTORY_VERSION = 2   # what the history takes from the journal: a new one reads every journal again, once (2: MissionRedirected)
# a target's subject file on Contracts › History: its status, by how its contract ended (failed after it was killed -
# MissionRedirected first - it's retired, though the contract lapsed before it was handed in)
FILE_STATUS = {"completed": "FILE CLOSED", "failed": "ESCAPED", "abandoned": "CONTRACT WITHDRAWN"}
HISTORY_FILTERS = {"nav": {"systems": True, "stations": True, "planetary": True},          # each history page's toggles, as
                   "contracts": {"completed": True, "failed": False, "abandoned": False}}   # they start (kept while the board runs)
MISSION_OUTCOMES = {"MissionCompleted": "completed", "MissionFailed": "failed", "MissionAbandoned": "abandoned"}
VISIT_JUMPS = ("jump", "cjump")
VISIT_ORDER = {"jump": 0, "cjump": 0, "orbit": 1, "near": 2, "dock": 3, "land": 3}   # for events with the same time
VISIT_FILTER = {"sys": "systems", "stn": "stations", "pln": "planetary", "site": "planetary"}   # a place's toggle


def visit_cat(v):
    """What kind of place a visit is at: 'sys' (a system jumped into), 'stn' (a station or carrier docked at),
    'pln' (a planet orbited or landed on) or 'site' (a settlement, planetary port or outpost)."""
    k = v["k"]
    if k in VISIT_JUMPS or k == "here":
        return "sys"
    if k in ("orbit", "land"):
        return "pln"
    if k == "near":
        return "site"
    return "site" if v["d"].get("surface") else "stn"


def visit_place(v):
    """The key of the place a visit is at (the details are found by it)."""
    cat = visit_cat(v)
    return f"{cat}|{coord_key(v['sys'])}|{'' if cat == 'sys' else v['id']}"


def _jdest(ev):
    """A journal destination name, readable ('' for an unlocalised '$...;' one)."""
    for key in ("NearestDestination_Localised", "NearestDestination"):
        val = str(ev.get(key) or "")
        if val and not val.startswith("$"):
            return val
    return ""


class JournalHistory:
    """Everywhere you've been and every mission you've finished, from all your journals, kept for good in
    journal_records.sqlite (in its own tables, beside JournalRecords'). Your older journals are read once, in
    the background; every new event adds to it. Nav › Hist lists the places - systems jumped into, stations
    docked at, planets orbited or landed on, settlements and planetary ports come within range of - and
    Contracts › History the missions completed, failed or abandoned. Each page's toggles are kept here (so the
    UFC's knob steps through what the page shows), as they start until the board stops."""

    SCHEMA = (
        "CREATE TABLE IF NOT EXISTS hvisits (ts TEXT NOT NULL, kind TEXT NOT NULL, ident TEXT NOT NULL, system TEXT NOT NULL, "
        "data TEXT NOT NULL, PRIMARY KEY (ts, kind, ident)) WITHOUT ROWID",
        "CREATE TABLE IF NOT EXISTS hmissions (mid INTEGER PRIMARY KEY, data TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS hfiles (name TEXT PRIMARY KEY, size INTEGER NOT NULL) WITHOUT ROWID",
    )

    def __init__(self, records):
        self.db, self.lock = records.db, records.lock   # the records' own file, connection and lock
        self.visits = {}      # (ts, kind, ident) -> {"ts", "k", "id", "sys", "d"}
        self.missions = {}    # mission ID -> {"acc": its record, "out": outcome, "end": time, "fin": what it ended with}
        self.names = {}       # system address -> name (ApproachSettlement gives only the address)
        self.sites = set()    # (system, ident) of settlements and ports come within range of
        self.types = {}       # (system, ident) -> station type, from docking
        self.filters = {k: dict(v) for k, v in HISTORY_FILTERS.items()}
        self.version, self.ready, self.progress = 0, False, [0, 0]
        self._sorted, self._groups, self._built = None, None, {}
        self._live = {"sys": ""}   # where the live journal has you (for an event that doesn't say)
        self._bumped = self._committed = 0.0
        self._dirty = False
        try:
            with self.db:
                for q in self.SCHEMA:
                    self.db.execute(q)
            for ts, kind, ident, system, data in self.db.execute("SELECT ts, kind, ident, system, data FROM hvisits").fetchall():
                self._keep({"ts": ts, "k": kind, "id": ident, "sys": system, "d": json.loads(data)})
            for mid, data in self.db.execute("SELECT mid, data FROM hmissions").fetchall():
                self.missions[mid] = json.loads(data)
        except (sqlite3.Error, ValueError) as exc:
            log(f"Couldn't read your history ({exc}).")

    def _keep(self, v):
        self.visits[(v["ts"], v["k"], v["id"])] = v
        if v["k"] == "near":
            self.sites.add((coord_key(v["sys"]), v["id"]))
        if v["k"] == "dock" and v["d"].get("type"):
            self.types[(coord_key(v["sys"]), v["id"])] = v["d"]["type"]

    def _commit(self, force=False):
        """Written to the file at most once a second (anything lost is read from the journal again next time)."""
        t = time.time()
        if self._dirty and (force or t - self._committed > 1.0):
            self._committed, self._dirty = t, False
            try:
                self.db.commit()
            except sqlite3.Error as exc:
                log(f"Couldn't save your history ({exc}).")

    def _changed(self, now=False):
        """Something new: the page fetches the lists again (while the old journals are read, every few seconds)."""
        t = time.time()
        if now or self.ready or t - self._bumped > 2.0:
            self._bumped = t
            self.version += 1
            self._built = {}

    # ---- journal events ----
    def note(self, ev, ctx=None, batch=False):
        """Take what one journal event says. ctx: where that journal has you (the live one's, or the reading of an
        old one's). Returns True if it added anything."""
        kind, ts = ev.get("event"), ev.get("timestamp") or ""
        if kind not in HISTORY_EVENTS or not ts:
            return False
        ctx = self._live if ctx is None else ctx
        with self.lock:
            if ev.get("StarSystem"):
                ctx["sys"] = ev["StarSystem"]
                if ev.get("SystemAddress"):
                    self.names[ev["SystemAddress"]] = ev["StarSystem"]
            if kind == "Location":
                return False
            if kind.startswith("Mission"):
                return self._mission(ev, kind, ts, batch)
            system = ev.get("StarSystem") or self.names.get(ev.get("SystemAddress")) or ctx.get("sys")
            if not system:
                return False
            if kind in ("FSDJump", "CarrierJump"):
                fac = ev.get("SystemFaction")
                v = {"k": "jump" if kind == "FSDJump" else "cjump", "id": coord_key(system), "d": {k: x for k, x in {
                    "allegiance": ev.get("SystemAllegiance"), "economy": ev.get("SystemEconomy_Localised"),
                    "economy2": ev.get("SystemSecondEconomy_Localised"), "government": ev.get("SystemGovernment_Localised"),
                    "security": ev.get("SystemSecurity_Localised"), "population": ev.get("Population"),
                    "faction": fac.get("Name") if isinstance(fac, dict) else fac, "ly": ev.get("JumpDist")}.items() if x not in (None, "")}}
            elif kind in ("Docked", "ApproachSettlement"):
                st = station_from_event(ev)
                if not st:
                    return False
                d = {k: x for k, x in st.items() if not k.startswith("_")}
                ident = f"m:{st['marketId']}" if st.get("marketId") else f"n:{st['name'].casefold()}"
                if kind == "Docked":
                    d["surface"] = bool(_surface_type(d.get("type"), d["name"]) or (coord_key(system), ident) in self.sites)
                v = {"k": "dock" if kind == "Docked" else "near", "id": ident, "d": d}
            elif kind == "ApproachBody":
                if not ev.get("Body"):
                    return False
                v = {"k": "orbit", "id": "b:" + str(ev["Body"]).casefold(), "d": {"body": ev["Body"]}}
            else:   # Touchdown: yours (not the ship landing itself to pick you up), not a taxi's
                if not ev.get("Body") or ev.get("PlayerControlled") is False or ev.get("Taxi"):
                    return False
                v = {"k": "land", "id": "b:" + str(ev["Body"]).casefold(), "d": {k: x for k, x in {
                    "body": ev["Body"], "lat": ev.get("Latitude"), "lon": ev.get("Longitude"), "near": _jdest(ev)}.items() if x not in (None, "")}}
            v.update(ts=ts, sys=system)
            if (ts, v["k"], v["id"]) in self.visits:
                return False
            try:
                self.db.execute("INSERT OR IGNORE INTO hvisits (ts, kind, ident, system, data) VALUES (?, ?, ?, ?, ?)",
                                (ts, v["k"], v["id"], system, json.dumps(v["d"], ensure_ascii=False)))
                self._dirty = True
                if not batch:
                    self._commit()
            except sqlite3.Error as exc:
                log(f"Couldn't keep a visit to {system} in your history ({exc}).")
            self._keep(v)
            self._sorted = self._groups = None
            self._changed(now=not batch)
            return True

    def _mission(self, ev, kind, ts, batch):
        mid = ev.get("MissionID")
        if not isinstance(mid, int):
            return False
        rec = dict(self.missions.get(mid) or {})
        if kind == "MissionAccepted":
            rec["acc"] = mission_record(ev)[0]
        elif kind == "MissionRedirected":   # its objective done (a target: killed) - how it ends comes later
            if rec.get("redir"):
                return False
            rec["redir"] = ts
        else:
            rec.update(out=MISSION_OUTCOMES[kind], end=ts)
            gets = []
            for x in (ev.get("CommodityReward") or []) + (ev.get("MaterialsReward") or []):
                if isinstance(x, dict) and (x.get("Name_Localised") or x.get("Name")):
                    gets.append([str(x.get("Name_Localised") or pretty(str(x.get("Name")))), x.get("Count") or 1])
            rec["fin"] = {k: x for k, x in {
                "reward": ev.get("Reward"), "donated": ev.get("Donated"), "fine": ev.get("Fine"), "gets": gets,
                "system": ev.get("DestinationSystem"), "station": ev.get("DestinationStation"),
                "settlement": ev.get("DestinationSettlement")}.items() if x not in (None, "", [])}
            if "acc" not in rec:   # accepted before your journals begin: what the end says
                rec["acc"] = dict(mission_record(ev)[0], partial=True, accepted="")
        if rec == self.missions.get(mid):
            return False
        try:
            self.db.execute("INSERT OR REPLACE INTO hmissions (mid, data) VALUES (?, ?)", (mid, json.dumps(rec, ensure_ascii=False)))
            self._dirty = True
            if not batch:
                self._commit()
        except sqlite3.Error as exc:
            log(f"Couldn't keep a mission in your history ({exc}).")
        self.missions[mid] = rec
        self._changed(now=not batch)
        return True

    def backfill(self, journal_dir: Path):
        """Read every journal not read before (or grown since). Runs once, in the background."""
        try:
            paths = sorted(journal_dir.glob("Journal.*.log"))
        except OSError:
            paths = []
        with self.lock:
            try:
                done = dict(self.db.execute("SELECT name, size FROM hfiles").fetchall())
            except sqlite3.Error:
                done = {}
        if done.get("#version") != HISTORY_VERSION:   # (it takes more from them now: every journal again)
            done = {}
        todo = []
        for path in paths:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if done.get(path.name) != size:
                todo.append((path, size))
        self.progress = [0, len(todo)]
        needles = tuple(f'"{k}"'.encode() for k in HISTORY_EVENTS)   # a quick look first; note() checks properly
        for n, (path, size) in enumerate(todo, 1):
            try:
                with open(path, "rb") as fh:
                    lines = [ln for ln in fh if any(x in ln for x in needles)]
            except OSError:
                continue
            ctx = {"sys": ""}
            with self.lock:
                try:
                    for ln in lines:
                        try:
                            ev = json.loads(ln.decode("utf-8", errors="replace"))
                        except ValueError:
                            continue
                        if isinstance(ev, dict):
                            self.note(ev, ctx, batch=True)
                    self.db.execute("INSERT OR REPLACE INTO hfiles (name, size) VALUES (?, ?)", (path.name, size))
                    self._dirty = True
                    self._commit(force=True)
                except sqlite3.Error as exc:
                    log(f"Couldn't keep your history from {path.name} ({exc}).")
            self.progress = [n, len(todo)]
        with self.lock:
            try:
                self.db.execute("INSERT OR REPLACE INTO hfiles (name, size) VALUES (?, ?)", ("#version", HISTORY_VERSION))
                self._dirty = True
                self._commit(force=True)
            except sqlite3.Error:
                pass
            self.ready = True
            self._changed(now=True)
        if todo:
            log(f"History: read {len(todo)} journal file{'s' if len(todo) != 1 else ''} - {len(self.visits):,} visits, "
                f"{sum(1 for m in self.missions.values() if m.get('out')):,} missions finished.")

    # ---- the toggles ----
    def set_filter(self, page, name, on):
        with self.lock:
            if name not in self.filters.get(page, {}):
                return False
            self.filters[page][name] = bool(on)
            self._changed(now=True)
            return True

    # ---- what the pages list ----
    def _grouped(self):
        """The visits in time order, by arrival in a system: [(the jump - or 'here', a system you were in without
        a jump your journals have - and the visits after it, in that system)]."""
        if self._groups is None:
            self._sorted = sorted(self.visits.values(), key=lambda v: (v["ts"], VISIT_ORDER.get(v["k"], 9)))
            groups, cur = [], None
            for v in self._sorted:
                if v["k"] in VISIT_JUMPS:
                    cur = (v, [])
                    groups.append(cur)
                    continue
                if cur is None or coord_key(cur[0]["sys"]) != coord_key(v["sys"]):
                    cur = ({"ts": v["ts"], "k": "here", "id": coord_key(v["sys"]), "sys": v["sys"], "d": {}}, [])
                    groups.append(cur)
                cur[1].append(v)
            self._groups = groups
        return self._groups

    def _item(self, v, depth, flat):
        cat, k, d = visit_cat(v), v["k"], v["d"]
        if cat == "sys":
            name, icon = v["sys"], "star"
        elif cat == "pln":
            name, icon = _short_name(str(d.get("body") or ""), v["sys"]), "planet"
        else:
            stype = d.get("type") or self.types.get((coord_key(v["sys"]), v["id"])) or ("Settlement" if cat == "site" else "")
            name, icon = construction_site(d.get("name") or "")[1] or d.get("name") or "?", station_icon(stype, d.get("name") or "")
        item = {"k": f"{v['ts']}|{k}|{coord_key(v['sys'])}|{v['id']}", "t": k, "ts": v["ts"], "n": name, "i": icon,
                "p": visit_place(v), "d": depth}
        if flat or cat == "pln" and name == d.get("body"):
            item["s"] = v["sys"]
        return item

    def _nav(self):
        f = self.filters["nav"]
        rows = []
        for head, kids in reversed(self._grouped()):
            shown = [v for v in kids if f[VISIT_FILTER[visit_cat(v)]]]
            if f["systems"]:   # each arrival, the places you went there under it (in the order you went)
                rows.append(self._item(head, 0, False))
                rows += [self._item(v, 1, False) for v in shown]
            else:   # the places alone, newest first, each with its system
                rows += [self._item(v, 0, True) for v in reversed(shown)]
        places = {k: set() for k in f}   # how many different places of each kind
        for head, kids in self._grouped():
            places["systems"].add(coord_key(head["sys"]))
            for v in kids:
                places[VISIT_FILTER[visit_cat(v)]].add(visit_place(v))
        return {"rows": rows, "totals": {k: len(places[k]) for k in f}}

    def _contracts(self):
        f = self.filters["contracts"]
        done = [(mid, m) for mid, m in self.missions.items() if m.get("out") and m.get("acc")]
        done.sort(key=lambda x: x[1]["end"], reverse=True)
        rows = [{"k": f"h:{mid}", "ts": m["end"], "o": m["out"], "c": m["acc"].get("cat") or "Contract",
                 "n": m["acc"].get("target") or m["acc"].get("title") or "Contract"} for mid, m in done if f.get(m["out"])]
        totals = {k: 0 for k in f}
        for _, m in done:
            totals[m["out"]] = totals.get(m["out"], 0) + 1
        return {"rows": rows, "totals": totals}

    def _list(self, page):
        sig = (page, self.version)
        if sig not in self._built:
            built = self._nav() if page == "nav" else self._contracts()
            built["at"] = {r["k"]: i for i, r in enumerate(built["rows"])}
            self._built[sig] = built
        return self._built[sig]

    def view(self, page, start=0, count=None, want=None):
        """A history page's list - its rows from start (count of them, and at least as far as the row want; all of
        them if no count), how many there are in all ("total"), the totals, the toggles, and the reading's progress."""
        with self.lock:
            built = self._list(page)
            rows = built["rows"]
            if count is not None:
                if want in built["at"]:
                    count = max(count, built["at"][want] - start + 60)
                rows = rows[start:start + min(count, 5000)]
            return {"rows": rows, "total": len(built["rows"]), "start": start, "totals": built["totals"],
                    "filters": dict(self.filters[page]), "v": self.version, "ready": self.ready, "progress": list(self.progress)}

    def keys(self, page):
        """The keys of a history page's rows, in its order (the UFC's COMM1 knob steps through them)."""
        with self.lock:
            return [r["k"] for r in self._list(page)["rows"]]

    def recent_systems(self, n=10):
        """The systems you've been in lately, the latest first, each once."""
        with self.lock:
            out, seen = [], set()
            for head, _ in reversed(self._grouped()):
                k = coord_key(head.get("sys"))
                if k and k not in seen:
                    seen.add(k)
                    out.append(head["sys"])
                    if len(out) >= n:
                        break
            return out

    def summary(self):
        """For the board's state: whether the lists have changed, and how the reading of old journals is going."""
        with self.lock:
            self._commit()
            return {"v": self.version, "ready": self.ready, "progress": list(self.progress)}

    # ---- a place's details (Nav › Hist) ----
    def place(self, key, records=None):
        """What the page shows for a place: its name and kind, a picture, the facts the journal gave on your last
        visit, and your visits there (newest first). None if it's not known."""
        try:
            cat, skey, ident = key.split("|", 2)
        except ValueError:
            return None
        with self.lock:
            groups = self._grouped()
            mine, related, visits = [], [], 0
            for head, kids in groups:
                hit = False
                if cat == "sys":
                    if coord_key(head["sys"]) == skey:
                        mine.append(head)
                        hit = True
                else:
                    for v in kids:
                        if coord_key(v["sys"]) != skey:
                            continue
                        if visit_cat(v) == cat and v["id"] == ident:
                            mine.append(v)
                            hit = True
                        elif cat == "site" and v["k"] == "land":
                            related.append(v)
                visits += hit
            if not mine:
                return None
            last = mine[-1]
            system = last["sys"]
            out = {"key": key, "cat": cat, "system": system, "copy": system, "visits": visits,
                   "first": mine[0]["ts"], "last": last["ts"], "chips": [], "rows": [], "log": []}
            data = {}
            for v in mine:   # the newest of what each visit said
                data.update({k: x for k, x in v["d"].items() if x not in (None, "", [])})
            if cat == "site":
                name = str(data.get("name") or "")
                related = [v for v in related if str(v["d"].get("near") or "").casefold() == name.casefold()
                           and (not data.get("body") or str(v["d"].get("body") or "").casefold() == str(data["body"].get("name") or "").casefold())]
            out.update(self._place_view(cat, system, data, mine, related, records))
            out["chips"].insert(0, f"{visits} visit{'s' if visits != 1 else ''}")
            out["rows"][:0] = [["First visit", _jtime(mine[0]["ts"]), False], ["Last visit", _jtime(last["ts"]), False],
                               ["Visits", f"{visits}" + (f" · landed {len({v['ts'] for v in related + [x for x in mine if x['k'] == 'land']})}"
                                                         if cat in ("pln", "site") and (related or any(x["k"] == "land" for x in mine)) else ""), False]]
            words = {"jump": "Jumped in", "cjump": "Carrier jump", "dock": "Docked", "orbit": "Orbital cruise",
                     "near": "Came within range", "land": "Landed", "here": "In the system (no jump in your journals)"}
            for v in sorted(mine + related, key=lambda x: x["ts"], reverse=True)[:60]:
                text = words.get(v["k"], v["k"])
                if v["k"] in VISIT_JUMPS and v["d"].get("ly"):
                    text += f" · {float(v['d']['ly']):.2f} ly"
                if v["k"] == "land":
                    if v["d"].get("lat") is not None and v["d"].get("lon") is not None:
                        text += f" · {float(v['d']['lat']):.2f}, {float(v['d']['lon']):.2f}"
                    if v["d"].get("near") and cat == "pln":
                        text += f" · near {v['d']['near']}"
                    elif cat == "site":
                        text = "Landed nearby" + text[6:]
                out["log"].append([_jtime(v["ts"]), text])
            return out

    def _place_view(self, cat, system, d, mine, related, records):
        def chips_of(st):
            return [t for t, ok in (("Market", st.get("haveMarket")), ("Shipyard", st.get("haveShipyard")),
                                    ("Outfitting", st.get("haveOutfitting"))) if ok]
        if cat == "sys":
            star = None
            for b in (records.for_system(system).get("bodies") if records else None) or []:
                if b.get("type") == "Star" and (b.get("isMainStar") or not b.get("distanceToArrival")):
                    star = b
                    break
            econ = d.get("economy") or "-"
            if d.get("economy2") and d["economy2"] != econ and d["economy2"] != "None":
                econ += f" / {d['economy2']}"
            rows = [["Faction", d.get("faction") or "-", False], ["Government", d.get("government") or "-", False],
                    ["Allegiance", d.get("allegiance") or "-", False], ["Economy", econ, False],
                    ["Security", d.get("security") or "-", False],
                    ["Population", _num(d["population"]) if d.get("population") else "-", False]]
            return {"name": system, "lab": "Star system" + (f" · {_star_short(star)}" if star else ""), "rows": rows,
                    "pic": {"kind": "star"}}
        if cat == "pln":
            body = str(d.get("body") or "")
            rec = next((b for b in (records.for_system(system).get("bodies") if records else None) or []
                        if str(b.get("name") or "").casefold() == body.casefold()), None) or {}
            sites, seen = [], set()
            with self.lock:
                for v in self.visits.values():   # the settlements you've come near on it
                    vb = (v["d"].get("body") or {}) if v["k"] == "near" else {}
                    if vb.get("latitude") is not None and str(vb.get("name") or "").casefold() == body.casefold() and v["id"] not in seen:
                        seen.add(v["id"])
                        sites.append({"name": v["d"].get("name"), "lat": vb["latitude"], "lon": vb.get("longitude", 0)})
            land = next((v for v in reversed(mine) if v["k"] == "land" and v["d"].get("lat") is not None), None)
            rows = [["Type", rec["subType"], True]] if rec.get("subType") else []   # (if you've scanned it)
            if rec.get("gravity"):
                rows.append(["Gravity", f"{float(rec['gravity']):.2f} g", False])
            if rec.get("radius"):
                rows.append(["Radius", f"{_num(rec['radius'])} km", False])
            if rec.get("atmosphereType"):
                rows.append(["Atmosphere", rec["atmosphereType"], False])
            pic = {"kind": "globe", "sites": sites}
            if land:
                pic["me"] = {"lat": land["d"]["lat"], "lon": land["d"].get("lon", 0)}
                pic["lat"], pic["lon"] = land["d"]["lat"], land["d"].get("lon", 0)
            short = _short_name(body, system)
            kind = ("Moon" if re.fullmatch(r"(?:[A-Z]+ )?\d+(?: [a-z])+", short) else
                    "Planet" if re.fullmatch(r"(?:[A-Z]+ )?\d+", short) else "Body")
            return {"name": body, "lab": f"{kind} · {system}", "rows": rows, "pic": pic}
        # a station, settlement or port
        stype = d.get("type") or self.types.get((coord_key(system), mine[-1]["id"])) or ("Settlement" if cat == "site" else "Station")
        site, short = construction_site(d.get("name") or "")
        body = d.get("body") or {}
        econ = d.get("economy") or "-"
        if d.get("secondEconomy") and d["secondEconomy"] != econ:
            econ += f" / {d['secondEconomy']}"
        rows = [["Faction", (d.get("controllingFaction") or {}).get("name") or "-", False],
                ["Government", d.get("government") or "-", False], ["Economy", econ, False],
                ["Allegiance", d.get("allegiance") or "-", False]]
        if d.get("otherServices"):
            rows.append(["Services", " · ".join(d["otherServices"]), True])
        if body.get("latitude") is not None:
            rows.append(["Position", f"{float(body['latitude']):.2f}, {float(body.get('longitude') or 0):.2f}", True])
        if cat == "stn" and isinstance(d.get("distanceToArrival"), (int, float)):
            rows.append(["Distance", f"{_num(d['distanceToArrival'])} ls", False])
        chips = chips_of(d)
        if related:
            chips.insert(0, "Landed")
        if any(v["k"] == "dock" for v in mine) and cat == "site":
            chips.insert(0, "Docked")
        where = body.get("name") or system
        lab = f"{f'{site.capitalize()} construction site' if site else stype} · {where}"
        if cat == "site" and body.get("latitude") is not None:
            sites, seen = [], set()
            with self.lock:
                for v in self.visits.values():
                    vb = (v["d"].get("body") or {}) if v["k"] == "near" else {}
                    if vb.get("latitude") is not None and str(vb.get("name") or "").casefold() == str(body.get("name") or "").casefold() \
                            and v["id"] not in seen:
                        seen.add(v["id"])
                        sites.append({"name": v["d"].get("name"), "lat": vb["latitude"], "lon": vb.get("longitude", 0)})
            pic = {"kind": "globe", "sites": sites, "hl": d.get("name"), "lat": body["latitude"], "lon": body.get("longitude", 0)}
        else:
            pic = {"kind": _station_pic(stype, cat == "site", d.get("name") or "")}
        out = {"name": short or d.get("name") or "?", "lab": lab, "rows": rows, "chips": chips, "pic": pic}
        if cat == "site" and (stype == "Odyssey Settlement" or site == "planetary" or "settlement" in stype.lower()):
            out["skey"] = settlement_key(system, {"marketId": d.get("marketId"), "name": d.get("name")})
        return out

    # ---- a mission's details (Contracts › History) ----
    def mission(self, key, backstories=None):
        try:
            mid = int(str(key).split(":", 1)[1])
        except (IndexError, ValueError):
            return None
        with self.lock:
            rec = self.missions.get(mid)
            if not rec or not rec.get("out") or not rec.get("acc"):
                return None
            m, fin = rec["acc"], rec.get("fin") or {}
        dest = ", ".join(x for x in (fin.get("settlement") or m.get("settlement"), fin.get("station") or m.get("station"),
                                     fin.get("system") or m.get("system")) if x)
        paid = []
        if rec["out"] == "completed":
            if fin.get("reward"):
                paid.append(f"{int(fin['reward']):,} CR")
            paid += [f"{int(n):,} × {name}" for name, n in fin.get("gets") or []]
        rows = []
        def row(label, value, wide=True):
            if value:
                rows.append([label, value, wide])
        row("Objective", m.get("title"))
        if m.get("kind") != "contract":
            row("Target", " · ".join(x for x in (m.get("target"), m.get("target_type"), m.get("target_faction")
                                                  if m.get("target_faction") != m.get("target") else "") if x))
            if m.get("kill_count"):
                row("Kills", str(m["kill_count"]))
        row("Contact", m.get("contact"))
        if m.get("commodity") and m.get("count"):
            row("Cargo", f"{int(m['count']):,} × {m['commodity']}")
        px = m.get("passengers")
        if px:
            row("Passengers", " · ".join(x for x in (f"{px['count']} passenger" + ("s" if px["count"] != 1 else ""), px.get("type"),
                                                      "VIP" if px.get("vip") else "", "wanted" if px.get("wanted") else "") if x))
        if m.get("donation") or fin.get("donated"):
            row("Donation", f"{int(fin.get('donated') or m.get('donation') or 0):,} CR")
        row("Rewards", " · ".join(paid))
        if fin.get("fine"):
            row("Fine", f"{int(fin['fine']):,} CR")
        row("Standing", " · ".join(x for x in (f"Influence {m['influence']}" if m.get("influence") else "",
                                               f"reputation {m['reputation']}" if m.get("reputation") else "") if x))
        if m.get("wing"):
            row("Wing", "Shared with your wing")
        story, sfile = "", None
        target = m.get("kind") != "contract"
        if target:   # its subject file: the status its contract ended with, the board's facts, what was written
            b = (backstories or {}).get(m.get("key")) or {}
            done = b.get("status") == "done"
            story = (b.get("text") or "") if done and b.get("fmt") != DOSSIER_FORMAT else ""
            number, incept, _ = dossier_ids(m.get("key") or "", m.get("accepted") or "")
            fields = (b.get("file") or {}) if done and b.get("fmt") == DOSSIER_FORMAT else {}
            batch = m.get("kind") == "faction"
            serial = (f"{DOSSIER_LINE} batch {b.get('number') or number}" if batch else
                      f"{DOSSIER_LINE}{(fields.get('sex', '') + fields.get('physical_grade', '') + fields.get('mental_grade', '')) or '---'}{b.get('number') or number}")
            status = FILE_STATUS.get(rec["out"], rec["out"].upper())
            if rec["out"] == "failed" and rec.get("redir"):
                status = "RETIRED · UNPAID"
            fac = m.get("target_faction") or (m.get("target") if batch else "")
            sfile = {"status": status, "serial": serial, "incept": b.get("incept") or game_date(incept), "affiliation": fac or "",
                     "contract": mission_verb(m) + (f", for {m['issuer']}" if m.get("issuer") else ""),
                     "threat": b.get("threat") or "", "scan": b.get("scan") or "", "kind": "batch" if batch else "person",
                     "fields": fields}
        label = (f"{'Batch' if sfile['kind'] == 'batch' else 'Subject'} file · Case {str(mid)[-4:]}" if sfile else
                 " · ".join(x for x in (f"Contract {str(mid)[-4:]}", m.get("cat")) if x))
        return {"key": key, "label": label,
                "name": m.get("target") or m.get("title") or "Contract", "outcome": rec["out"].capitalize(),
                "issuer": m.get("issuer") or "-", "paid": paid[0] if paid and paid[0].endswith(" CR") else "-",
                "accepted": _jtime(m.get("accepted")) or "-", "ended": _jtime(rec.get("end")) or "-", "dest": dest or "-",
                "copy": fin.get("system") or m.get("system") or "", "rows": rows, "story": story, "file": sfile,
                "partial": bool(m.get("partial")), "target": target}


SCHEMATIC_ALIASES = {"tourist": "tourism", "hightechnology": "hightech", "hightechbio": "hightech"}


def schematic_category(name):
    """A settlement economy as one key, however it's written: 'Tourism' or 'tourist' -> tourism,
    'High Tech' or 'high-tech' -> hightech."""
    k = re.sub(r"[^a-z]", "", str(name or "").lower())
    return SCHEMATIC_ALIASES.get(k, k)


# What a settlement's name says about its economy (the game names them by it): the schematic type
# to start on when the data gives none that has layouts (a construction site's economy is "Colony")
SETTLEMENT_NAME_HINTS = (
    ("agriculture", ("hydroponic", "horticultur", "agricultur", "farm", "nursery", "botanical", "cultivat", "orchard", "ranch")),
    ("military", ("military", "bastion", "garrison", "barracks", "defence", "defense", "fort", "command", "watch")),
    ("hightech", ("biochemical", "pharmaceutic", "laborator", "research", "analytics", "technolog", "synthetics", "genetic")),
    ("extraction", ("mineralogic", "deposits", "dredging", "prospect", "claim", "mine", "excavation", "metallurgic", "drilling")),
    ("tourism", ("leisure", "resort", "hospitality", "venue", "lodgings", "sanctuary", "retreat", "boarding", "complex")),
    ("industrial", ("industr", "manufactur", "foundry", "fabricat", "factory", "works", "creations", "production", "assembly")),
)


def settlement_guess(name):
    """The economy a settlement's name points to ('Qiao Hydroponics Range' -> agriculture), or ''."""
    n = str(name or "").lower()
    return next((cat for cat, words in SETTLEMENT_NAME_HINTS if any(w in n for w in words)), "")


CONSTRUCTION_PREFIX = re.compile(r"^\s*(planetary|orbital)\s+construction\s+site\s*:\s*", re.I)


def construction_site(name):
    """'Planetary Construction Site: Qiao Hydroponics Range' -> ('planetary', 'Qiao Hydroponics Range'); else ('', name)."""
    m = CONSTRUCTION_PREFIX.match(str(name or ""))
    return (m.group(1).lower(), str(name)[m.end():].strip() or str(name)) if m else ("", name)


def _plan_points(v, least):
    """At least `least` [x, y] pairs of numbers, rounded for drawing; else None."""
    if not isinstance(v, list) or len(v) < least:
        return None
    out = []
    for p in v:
        if not (isinstance(p, (list, tuple)) and len(p) >= 2 and
                all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in p[:2])):
            return None
        out.append([round(float(p[0]), 1), round(float(p[1]), 1)])
    return out


def _cut_edges(d):
    """Which outline edges of each shape are cut off by the edge of the map picture (its menu, legend
    or border), so the page can draw them open: {shape id: [edge numbers]}. An edge counts when it runs
    along the map's border; edges a plan names itself (by number, by its two ends, or by side) count too."""
    src = d.get("source") or {}
    area = src.get("map_area") if isinstance(src.get("map_area"), list) and len(src.get("map_area")) == 4 else \
        [0, 0, src.get("width") or 0, src.get("height") or 0]
    try:
        left, top, right, bottom = (float(v) for v in area)
    except (TypeError, ValueError):
        return {}

    def near(v, *lines):
        return any(abs(v - line) <= 1.5 for line in lines)

    def side_of(a, b):   # the border both ends of an edge lie on, if any
        if near(a[0], left) and near(b[0], left):
            return "left"
        if near(a[0], right - 1, right) and near(b[0], right - 1, right):
            return "right"
        if near(a[1], top) and near(b[1], top):
            return "top"
        if near(a[1], bottom - 1, bottom) and near(b[1], bottom - 1, bottom):
            return "bottom"
        return None
    named = {}   # shape id -> what the plan says is cut
    tops = d.get("clipped_edges")
    if isinstance(tops, dict):
        for sid, v in tops.items():
            named.setdefault(str(sid), []).extend(v if isinstance(v, list) else [v])
    elif isinstance(tops, list):
        for v in tops:
            if isinstance(v, dict) and v.get("id"):
                named.setdefault(str(v["id"]), []).append(v)
    out = {}
    for kind in ("buildings", "pads", "details"):
        for x in d.get(kind) or []:
            if not isinstance(x, dict) or not isinstance(x.get("outline"), list):
                continue
            pts = [p for p in x["outline"] if isinstance(p, (list, tuple)) and len(p) >= 2]
            says = named.get(str(x.get("id")), []) + (x.get("clipped_edges") if isinstance(x.get("clipped_edges"), list) else [])
            cut = set()
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                if side_of(a, b):
                    cut.add(i)
                for v in says:
                    if isinstance(v, dict) and v.get("edge_index") == i:
                        cut.add(i)
                    elif isinstance(v, dict) and isinstance(v.get("from"), list) and isinstance(v.get("to"), list):
                        f, t = v["from"], v["to"]
                        if (math.dist(a[:2], f[:2]) <= 2 and math.dist(b[:2], t[:2]) <= 2) or \
                                (math.dist(a[:2], t[:2]) <= 2 and math.dist(b[:2], f[:2]) <= 2):
                            cut.add(i)
            if cut and x.get("id"):
                out[str(x["id"])] = sorted(cut)
    return out


# The icons of a plan's site_m points: (toggle, colour key, text). Loot is told apart by SrvSurvey's item name;
# a combat-zone point by its letter (A-F checkpoints, P power posts). Tips (the map website's) have no toggle.
SITE_TERMINALS = {"auth": "AU", "personnel": "PE", "ship": "SH", "turrets": "TU"}


def _site_icon(p):
    t, acc, fl = p.get("type"), p.get("access"), p.get("floor")
    acc = acc if isinstance(acc, int) and not isinstance(acc, bool) else None
    up = "^" * (fl - 1) if isinstance(fl, int) and not isinstance(fl, bool) and fl >= 2 else ""
    own = str((p.get("icon") or {}).get("text") or "") if isinstance(p.get("icon"), dict) else ""
    plan_only = p.get("source") == "plan"
    if t in ("airlock", "inner_door", "secure_door"):
        text = own if plan_only and own else ("" if acc is None else str(acc)) + up
        return "door", "lock" if t == "airlock" else "door", text or "D"
    if t in ("terminal_lo", "terminal_above_lo", "data_terminal"):
        hi = (acc or 0) > 0 if acc is not None else t == "terminal_above_lo"
        return "term", "term2" if hi else "term", ("T+" if hi else "T") + up
    if t == "terminal":
        return "term", "term2", SITE_TERMINALS.get(p.get("function"), "T+") + up
    if t in ("power_regulator", "alarm_console"):
        return "power", "power", ("P" if t == "power_regulator" else "A") + (own[1:] if plan_only and own else up)
    if t == "loot":
        item = str(p.get("item") or "")
        if item == "Medkit":
            return "exp", "exp", "+" + up
        if item == "Battery":
            return "exp", "exp", "B" + up
        if item == "Atmos":   # SrvSurvey doesn't say what it is; a console, by where it's found
            return "power", "power", "AT" + up
        return "loot", "loot", ("L" if item.startswith("Locker") else "U") + up
    if t == "cz_point":
        name = str(p.get("name") or "").upper()[:1]
        return "cz", "czp" if name == "P" else "cz", name or "?"
    return None, None, own or None


def _tidy_site_plan(d, stem, category):
    """A plan with a site_m block (fitted to SrvSurvey's measurements): drawn from that, in metres, with
    SrvSurvey's frame turned the page's way up (y down: the site heading points up the picture)."""
    s = d["site_m"]

    def pts(v, least):
        o = _plan_points(v, least)
        return [[x, round(-y, 1) or 0.0] for x, y in o] if o else None

    def num(v):
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None
    cuts = _cut_edges(d)   # the edges the source picture cut off (the shapes keep their ids and corners)
    plan = {"id": str(d.get("id") or stem), "category": category, "layout": d.get("layout"),
            "name": str(d.get("name") or d.get("id") or stem),
            "description": str((d.get("fingerprint") or {}).get("description") or ""),
            "m_per_px": 1.0, "metric": True,
            "buildings": [], "pads": [], "walkways": [], "details": [], "points": [], "labels": []}
    for b in s.get("buildings") or []:
        o = pts(b.get("outline_m"), 3) if isinstance(b, dict) else None
        if o:
            plan["buildings"].append({"id": str(b.get("id") or ""), "kind": str(b.get("kind") or "other"),
                                      "label": str(b.get("label") or ""), "outline": o, "h": num(b.get("height_m")),
                                      "cut": cuts.get(str(b.get("id")), [])})
    for lab in s.get("labels") or []:
        at = pts([lab.get("at_m")], 1) if isinstance(lab, dict) else None
        if at and lab.get("text"):
            plan["labels"].append({"text": str(lab["text"]), "at": at[0], "building": str(lab.get("building") or "")})
    for x in s.get("pads") or []:   # at SrvSurvey's position and pad number, the working size
        o = pts(x.get("outline_m"), 3) if isinstance(x, dict) else None
        if o:
            n = x.get("pad_number") if isinstance(x.get("pad_number"), int) and not isinstance(x.get("pad_number"), bool) else None
            rot = x.get("rotation_deg")
            rot = float(rot) % 360 if isinstance(rot, (int, float)) and not isinstance(rot, bool) and math.isfinite(rot) else None
            # rot: the pad's turn from pad 1 (a ship docked on it faces the site heading + rot). Recorded for
            # every pad 1 (0 by definition) and the pads with a rotation; a 0 on any other pad means unknown.
            plan["pads"].append({"outline": o, "cut": [], "num": n, "size": str(x.get("size") or "")[:1].upper(),
                                 "rot": rot or 0.0, "rec": n == 1 or bool(rot)})
    for w in s.get("walkways") or []:
        line = pts(w.get("line_m"), 2) if isinstance(w, dict) else None
        if line:
            plan["walkways"].append({"kind": str(w.get("kind") or "open"), "line": line, "w": num(w.get("width_m")) or 4.0})
    for x in s.get("details") or []:
        o = pts(x.get("outline_m"), 3) if isinstance(x, dict) else None
        if o:
            plan["details"].append({"kind": str(x.get("kind") or "other"), "outline": o, "cut": cuts.get(str(x.get("id")), [])})
    for p in s.get("points") or []:
        at = pts([p.get("at_m")], 1) if isinstance(p, dict) else None
        if not at:
            continue
        g, k, text = _site_icon(p)
        plan["points"].append({"type": str(p.get("type") or ""), "at": at[0], "text": text,
                               "access": p.get("access") if isinstance(p.get("access"), int) else None,
                               "g": g, "k": k, "src": str(p.get("source") or "")})
    every = [q for k in ("buildings", "pads", "details") for x in plan[k] for q in x["outline"]] + \
            [q for w in plan["walkways"] for q in w["line"]] + [p["at"] for p in plan["points"]]
    if not every:
        raise ValueError("nothing to draw")
    xs, ys = [q[0] for q in every], [q[1] for q in every]
    plan["bounds"] = [min(xs), min(ys), max(xs), max(ys)]
    return plan


def tidy_plan(d, stem):
    """A settlement layout plan (see the notes at the top), cut down to what the page draws:
    shapes only, the map website's own buttons left out, icons with no text given null text."""
    def num(v):
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None
    category = schematic_category(d.get("category"))
    if category and isinstance(d.get("site_m"), dict):
        return _tidy_site_plan(d, stem, category)
    if not category:
        raise ValueError("no category")
    cuts = _cut_edges(d)
    plan = {"id": str(d.get("id") or stem), "category": category, "layout": d.get("layout"),
            "name": str(d.get("name") or d.get("id") or stem),
            "description": str((d.get("fingerprint") or {}).get("description") or ""),
            "m_per_px": num((d.get("scale") or {}).get("m_per_px")) if isinstance(d.get("scale"), dict) else None,
            "buildings": [], "pads": [], "walkways": [], "details": [], "points": [], "labels": []}
    placed = list(d.get("printed_labels") or [])   # where each name is printed on a roof (a building can have several)
    for b in d.get("buildings") or []:
        o = _plan_points(b.get("outline"), 3) if isinstance(b, dict) else None
        if not o:
            continue
        label = str(b.get("label") or "")
        if isinstance(b.get("printed_label_positions"), list):   # a shared roof's names, each where it's printed
            placed += [dict(lab, building=b.get("id")) for lab in b["printed_label_positions"] if isinstance(lab, dict)]
        elif isinstance(b.get("printed_labels"), list):   # ... or just which they are: all of them, in one name
            names = list(dict.fromkeys(str(t) for t in b["printed_labels"] if t))
            label = "/".join(names) if len(names) > 1 else label
        plan["buildings"].append({"id": str(b.get("id") or ""), "kind": str(b.get("kind") or "other"),
                                  "label": label, "outline": o, "h": num(b.get("height_m")),
                                  "cut": cuts.get(str(b.get("id")), [])})
    for lab in placed:
        at = _plan_points([lab.get("at")], 1) if isinstance(lab, dict) else None
        if at and lab.get("text"):
            plan["labels"].append({"text": str(lab["text"]), "at": at[0], "building": str(lab.get("building") or "")})
    for x in d.get("pads") or []:
        o = _plan_points(x.get("outline"), 3) if isinstance(x, dict) else None
        if o:
            plan["pads"].append({"outline": o, "cut": cuts.get(str(x.get("id")), [])})
    for w in d.get("walkways") or []:
        line = _plan_points(w.get("line"), 2) if isinstance(w, dict) else None
        if line:
            plan["walkways"].append({"kind": str(w.get("kind") or "open"), "line": line, "w": num(w.get("width_px")) or 10.0})
    for x in d.get("details") or []:   # shapes only: a notes entry that strayed in here is left out
        o = _plan_points(x.get("outline"), 3) if isinstance(x, dict) else None
        if o:
            plan["details"].append({"kind": str(x.get("kind") or "other"), "outline": o, "cut": cuts.get(str(x.get("id")), [])})
    for p in d.get("points") or []:
        at = _plan_points([p.get("at")], 1) if isinstance(p, dict) else None
        if not at or p.get("scope") == "map_ui":   # the map website's own buttons aren't in the settlement
            continue
        icon = p.get("icon") if isinstance(p.get("icon"), dict) else {}
        plan["points"].append({"type": str(p.get("type") or ""), "at": at[0], "text": str(icon.get("text") or "") or None,
                               "access": p.get("access") if isinstance(p.get("access"), int) else None})
    every = [q for k in ("buildings", "pads", "details") for s in plan[k] for q in s["outline"]] + \
            [q for w in plan["walkways"] for q in w["line"]] + [p["at"] for p in plan["points"]]
    if not every:
        raise ValueError("nothing to draw")
    xs, ys = [q[0] for q in every], [q[1] for q in every]
    plan["bounds"] = [min(xs), min(ys), max(xs), max(ys)]
    return plan


class SchematicStore:
    """The settlement layout plans in the schematics folder next to the script, one .json file
    each (see the notes at the top). Read again when a file is added, changed or removed."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.lock = threading.Lock()
        self.sig, self.checked, self.by_cat = None, 0.0, {}

    def _scan(self):
        if time.time() - self.checked < 3:
            return
        self.checked = time.time()
        try:
            files = sorted(p for p in self.folder.glob("*.json") if p.is_file())
            sig = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files)
        except OSError:
            files, sig = [], ()
        if sig == self.sig:
            return
        self.sig, by_cat = sig, {}
        for path in files:
            try:
                plan = tidy_plan(json.loads(path.read_text(encoding="utf-8")), path.stem)
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                log(f"Schematic {path.name} left out ({exc}).")
                continue
            by_cat.setdefault(plan["category"], []).append(plan)
        for plans in by_cat.values():   # in layout order (Tourist 1, 2, ...)
            plans.sort(key=lambda x: (x["layout"] if isinstance(x["layout"], (int, float)) else 1e9, x["id"]))
        self.by_cat = by_cat
        if files:
            log("Schematics: " + ", ".join(f"{len(v)} {k}" for k, v in sorted(by_cat.items())) + ".")

    def summary(self):
        """How many layouts there are for each settlement economy."""
        with self.lock:
            self._scan()
            return {cat: len(plans) for cat, plans in self.by_cat.items()}

    def layouts(self, category):
        with self.lock:
            self._scan()
            return list(self.by_cat.get(schematic_category(category), []))

    def has(self, layout_id):
        with self.lock:
            self._scan()
            return any(p["id"] == layout_id for plans in self.by_cat.values() for p in plans)

    def plan(self, layout_id):
        with self.lock:
            self._scan()
            return next((p for plans in self.by_cat.values() for p in plans if p["id"] == layout_id), None)

    def category_of(self, layout_id):
        """(the economy a layout belongs to, how many layouts it has), or (None, 0)."""
        with self.lock:
            self._scan()
            for cat, plans in self.by_cat.items():
                if any(p["id"] == layout_id for p in plans):
                    return cat, len(plans)
        return None, 0


class StarCoords(threading.Thread):
    """Distances on the OCOR tab. Files the position of every system your journal reports
    (free, nothing fetched). Only while a page shows the OCOR tab, asks for the briefing systems not
    already in the cache - as the System list's toggles allow: Spansh (its search, one system at a time),
    then EDSM (all in one request) for any Spansh doesn't know; after that they come from the cache.
    The page works out the distances itself, also only on the OCOR tab."""

    def __init__(self, cache: CoordCache, state, ocor, bus, uplinks=None):
        super().__init__(daemon=True, name="coords")
        self.cache, self.state, self.ocor, self.bus = cache, state, ocor, bus
        self.uplinks = uplinks or UplinkSettings(None)
        self.uplinks.listeners.append(self._changed)
        self.wake = threading.Event()
        self.retry_at = 0.0

    @property
    def fetch(self):
        return not self.uplinks.offline

    def _changed(self):
        self.retry_at = 0.0
        self.wake.set()

    def poke(self):
        self.wake.set()

    def _journal(self):
        self.cache.store(self.state.place.take_seen(), source="journal")

    def _get(self, names):
        import urllib.request
        from urllib.parse import urlencode
        query = urlencode([("systemName[]", n) for n in names] + [("showCoordinates", "1")])
        req = urllib.request.Request(f"{EDSM_SYSTEMS_API}?{query}",
                                     headers={"User-Agent": user_agent()})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8") or "null")
        if not isinstance(data, list):
            raise ValueError("unexpected answer from EDSM")
        return data

    def _fill(self):
        if not self.fetch or self.bus.page() != "ocor" or time.time() < self.retry_at:
            return
        names = self.ocor.systems()
        with self.state.lock:
            place = self.state.place
            if place.system and not place.star_pos:
                names.append(place.system)   # your position isn't in the journal (rare)
        known, unknown = self.cache.lookup(names)
        now, todo, keys = time.time(), [], set()
        for n in names:
            k = coord_key(n)
            if k in known or k in keys or now - unknown.get(k, 0) < COORDS_UNKNOWN_RETRY:
                continue
            keys.add(k)
            todo.append(n)
        if not todo:
            return
        found, missing, error, asked = {}, [], "", []
        if self.uplinks.spansh:   # Spansh first, a system at a time
            asked.append("Spansh")
            for n in list(todo):
                try:
                    hit = spansh_find(n)
                except Exception as exc:   # network, Spansh busy: try again in a minute (while on the tab)
                    error = f"Spansh: {str(exc)[:110]}"
                    break
                if hit and all(isinstance(hit.get(a), (int, float)) for a in "xyz"):
                    found[n] = (hit["x"], hit["y"], hit["z"])
                    todo.remove(n)
                time.sleep(0.2)
        if self.uplinks.edsm and todo:   # EDSM for the rest, all in one request
            asked.append("EDSM")
            for i in range(0, len(todo), COORDS_BATCH):
                part = todo[i:i + COORDS_BATCH]
                try:
                    answer = {coord_key(x.get("name")): x.get("coords") for x in self._get(part) if isinstance(x, dict)}
                except Exception as exc:   # network, EDSM busy: try again in a minute (while on the tab)
                    error = (error + "; " if error else "") + f"EDSM: {str(exc)[:110]}"
                    break
                for n in part:
                    c = answer.get(coord_key(n))
                    if isinstance(c, dict) and all(isinstance(c.get(a), (int, float)) for a in "xyz"):
                        found[n] = (c["x"], c["y"], c["z"])
                    else:
                        missing.append(n)
        elif not error:
            missing = list(todo)   # (Spansh doesn't know them, and EDSM's off)
        self.cache.store(found, missing, source="+".join(asked).lower() or "edsm")
        if found or missing:
            log(f"Star coordinates: {len(found)} system(s) from {' then '.join(asked)}"
                + (f", {len(missing)} not known ({', '.join(missing[:3])})" if missing else "") + ".")
        if error:
            self.retry_at = time.time() + EDSM_RETRY
            log(f"Star coordinates: unreachable ({error}); trying again in a minute.")

    def for_page(self, objectives, system, star_pos):
        """What the OCOR tab needs to work out distances: each briefing system's coordinates
        ("unknown" if neither Spansh nor EDSM knew it) and yours."""
        names = []
        for o in objectives:
            if o.get("system") and o["system"] not in names:
                names.append(o["system"])
        known, unknown = self.cache.lookup(names + ([system] if system and not star_pos else []))
        coords = {}
        for n in names:
            k = coord_key(n)
            coords[n] = list(known[k]) if k in known else ("unknown" if k in unknown else None)
        here = star_pos or (list(known[coord_key(system)]) if system and coord_key(system) in known else None)
        return {"coords": coords, "here": here, "edsm": self.fetch, "online": self.fetch}

    def run(self):
        while True:
            self.wake.wait(5)
            self.wake.clear()
            try:
                self._journal()
                self._fill()
            except Exception as exc:
                log(f"Star coordinates: problem ({exc}).")


# --------------------------------------------------------------------------- #
# Tab 4 (System): the system you're in, from EDSM, plus your live position
# from Status.json (the file the game rewrites as you fly)
# --------------------------------------------------------------------------- #
EDSM_API = os.environ.get("EDTB_EDSM_API") or "https://www.edsm.net/api-system-v1/"   # (the env var is for the tests)
EDSM_PARTS = ("bodies", "stations", "traffic", "deaths", "estimated-value")   # all EDSM's parts for a system
EDSM_EXTRA = ("traffic", "deaths", "estimated-value")   # what's fetched from EDSM (bodies and stations too, if Spansh is off or has nothing)
CACHE_PARTS = EDSM_PARTS + ("spansh",)   # what the cache keeps for a system ("spansh": Spansh's record, stripped)
EDSM_REFRESH = 3600         # seconds: a system's data is fetched again - all its parts together - after an hour
EDSM_KEEP = 7 * 86400       # cached copies are kept a week (shown when Spansh or EDSM can't be reached), then dropped
EDSM_CACHE_FILE = DATA_DIR / "edsm_cache.json"   # (the name it's always had: Spansh's records are kept in it too)
EDSM_CACHE_MAX = 300        # systems kept (the oldest are dropped first)
EDSM_RETRY = 60             # after a failed fetch
UPLINK_EVERY = 60           # seconds between presses of System Data Uplink Synchronise
UPLINK_HOLD = (1.0, 3.0)    # "Uplink in progress" shows at least this long (picked at random each time)
NEAR_ALTITUDE = 100_000     # metres: below this (or gliding, landed, on foot) Auto shows the nearest surface site
F_DOCKED, F_LANDED, F_SUPERCRUISE, F_LATLONG, F_SRV = 1 << 0, 1 << 1, 1 << 4, 1 << 21, 1 << 26
F_FSD_CHARGING, F_FSD_JUMP = 1 << 17, 1 << 30
F2_ON_FOOT, F2_ON_PLANET, F2_GLIDE = 1 << 0, 1 << 4, 1 << 12
F_ALT_AVERAGE = 1 << 29     # Status.json's Altitude is from the planet's average radius (else from the ground below you)
F_IN_SHIP, F_IN_FIGHTER = 1 << 24, 1 << 25          # with F_SRV: you're in that vehicle
F2_IN_TAXI, F2_IN_MULTICREW = 1 << 1, 1 << 2
BOOT_WAIT_SECONDS = 60      # loading in: start the boot screen anyway if Status.json hasn't shown you in game by then
STATUS_POLL_SECONDS = 0.1   # Status.json and the journal being written are looked at this often (a file's size and time each - cheap)
JUMP_GIVE_UP = 150          # seconds: a jump that never arrives is dropped after this
SOLAR_RADIUS_M = 695_700_000

# Journal star type codes -> the name EDSM uses (the map styles go by it) and a typical radius in suns,
# for the placeholder drawn before the real figures arrive
STAR_TYPES = {
    "O": ("O (Blue-White) Star", 10), "B": ("B (Blue-White) Star", 4.5), "A": ("A (Blue-White) Star", 1.8),
    "F": ("F (White) Star", 1.3), "G": ("G (White-Yellow) Star", 1.0), "K": ("K (Yellow-Orange) Star", 0.8),
    "M": ("M (Red dwarf) Star", 0.45), "L": ("L (Brown dwarf) Star", 0.12), "T": ("T (Brown dwarf) Star", 0.1),
    "Y": ("Y (Brown dwarf) Star", 0.08), "TTS": ("T Tauri Star", 2.0), "AeBe": ("Herbig Ae/Be Star", 2.5),
    "W": ("Wolf-Rayet Star", 3), "WN": ("Wolf-Rayet N Star", 3), "WNC": ("Wolf-Rayet NC Star", 3),
    "WC": ("Wolf-Rayet C Star", 3), "WO": ("Wolf-Rayet O Star", 3),
    "CS": ("CS Star", 40), "C": ("C Star", 40), "CN": ("CN Star", 40), "CJ": ("CJ Star", 40), "CH": ("CH Star", 40),
    "CHd": ("CHd Star", 40), "MS": ("MS-type Star", 40), "S": ("S-type Star", 40),
    "N": ("Neutron Star", 0.00002), "H": ("Black Hole", 0.00003), "SupermassiveBlackHole": ("Supermassive Black Hole", 0.0001),
    "A_BlueWhiteSuperGiant": ("A (Blue-White super giant) Star", 50), "B_BlueWhiteSuperGiant": ("B (Blue-White super giant) Star", 40),
    "F_WhiteSuperGiant": ("F (White super giant) Star", 60), "G_WhiteSuperGiant": ("G (White-Yellow super giant) Star", 70),
    "K_OrangeGiant": ("K (Yellow-Orange giant) Star", 20), "M_RedGiant": ("M (Red giant) Star", 80),
    "M_RedSuperGiant": ("M (Red super giant) Star", 500), "X": ("Exotic Star", 1.0),
}


def star_placeholder(code):
    """What a star class alone says (StartJump, FSDTarget, the plotted route): its kind and a typical size."""
    code = str(code or "")
    if code.startswith("D") and code not in STAR_TYPES:
        sub, rsol = f"White Dwarf ({code}) Star", 0.012
    else:
        sub, rsol = STAR_TYPES.get(code, (f"{code} Star" if code else "Star", 1.0))
    return {"sub": sub, "cls": code.split("_")[0], "lum": "", "rsol": rsol, "mass": None, "temp": None,
            "rot": None, "tilt": None, "source": "class", "estimate": True}


def star_from_scan(ev):
    """The arrival star as the journal's automatic scan describes it (exact, needs no EDSM)."""
    code, sub_n = str(ev.get("StarType") or ""), ev.get("Subclass")
    base = star_placeholder(code)
    letter = code.split("_")[0]
    cls = f"{letter}{sub_n}" if sub_n is not None and len(letter) <= 4 else letter
    tilt = ev.get("AxialTilt")
    return {"sub": base["sub"], "cls": cls, "lum": ev.get("Luminosity") or "",
            "rsol": (ev.get("Radius") or 0) / SOLAR_RADIUS_M or base["rsol"], "mass": ev.get("StellarMass"),
            "temp": ev.get("SurfaceTemperature"), "rot": (ev.get("RotationPeriod") or 0) / 86400 or None,
            "tilt": round(math.degrees(tilt), 2) if isinstance(tilt, (int, float)) else None, "source": "journal"}


def star_from_edsm(b, source="edsm"):
    tilt = b.get("axialTilt")
    return {"sub": b.get("subType") or "Star", "cls": b.get("spectralClass") or (b.get("subType") or "?").split(" ")[0],
            "lum": b.get("luminosity") or "", "rsol": b.get("solarRadius"), "mass": b.get("solarMasses"),
            "temp": b.get("surfaceTemperature"), "rot": b.get("rotationalPeriod"),
            "tilt": round(math.degrees(tilt), 2) if isinstance(tilt, (int, float)) else None, "source": source}


# Frame shift drive fuel use: fuel = linear x 0.001 x (distance x mass / optimal mass) ^ power, where the
# linear constant goes by rating, the power constant by size, and the optimal mass by both (standard drives;
# an engineered drive states its own optimal mass in the loadout). Better still, every FSDJump in your journal
# records the distance and fuel used, so the script measures your drive's constant from your own recent jumps
# and only falls back on the tables below (SCO drives and Guardian boosters need a measured jump first).
FSD_LIN = {"A": 12, "B": 10, "C": 8, "D": 10, "E": 11}
FSD_POW = {2: 2.0, 3: 2.15, 4: 2.3, 5: 2.45, 6: 2.6, 7: 2.75, 8: 2.9}
FSD_OPT = {2: (48, 54, 60, 75, 90), 3: (80, 90, 100, 125, 150), 4: (280, 315, 350, 438, 525),   # E D C B A
           5: (560, 630, 700, 875, 1050), 6: (960, 1080, 1200, 1500, 1800), 7: (1440, 1620, 1800, 2250, 2700)}


def fsd_from_loadout(ev):
    for m in ev.get("Modules") or []:
        if str(m.get("Slot", "")).lower() != "frameshiftdrive":
            continue
        item = str(m.get("Item", "")).lower()
        found = re.search(r"size(\d)_class(\d)", item)
        if not found:
            return None
        size, grade = int(found.group(1)), int(found.group(2))
        rating = {1: "E", 2: "D", 3: "C", 4: "B", 5: "A"}.get(grade, "E")
        opt = None
        for mod in (m.get("Engineering") or {}).get("Modifiers") or []:
            if mod.get("Label") == "FSDOptimalMass" and isinstance(mod.get("Value"), (int, float)):
                opt = float(mod["Value"])
        sco = "overcharge" in item
        table = FSD_OPT.get(size)
        return {"key": f"{item}|{round(opt or 0)}", "size": size, "rating": rating, "sco": sco,
                "opt": opt or (None if sco or not table else table["EDCBA".index(rating)]),
                "lin": FSD_LIN[rating], "pow": FSD_POW.get(size, 2.45)}
    return None
PLANET_SHORT = {
    "high metal content world": "High metal", "metal-rich body": "Metal-rich", "rocky body": "Rocky",
    "rocky ice world": "Rocky ice", "icy body": "Icy", "earth-like world": "Earth-like", "water world": "Water world",
    "ammonia world": "Ammonia", "water giant": "Water giant", "helium-rich gas giant": "Helium giant",
    "helium gas giant": "Helium giant", "gas giant with water-based life": "Gas giant", "gas giant with ammonia-based life": "Gas giant",
}


def _edsm_time(value):
    """An EDSM time ('2026-10-27 17:44:32', UTC) in this PC's local time: '27 Oct 2026 17:44'; '' if none."""
    try:
        d = datetime.strptime(str(value or "")[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return str(value or "")[:16]
    return f"{d.day} {d:%b %Y %H:%M}"


def _num(value, places=0):
    try:
        return f"{float(value):,.{places}f}"
    except (TypeError, ValueError):
        return "-"


def _days(value):
    if value is None:
        return "-"
    d = abs(float(value))
    return f"{d:.1f} days" if d < 1000 else f"{d / 365.25:.1f} years"


def _short_name(name, system):
    if name.lower().startswith(system.lower() + " "):
        return name[len(system) + 1:]
    return name


def _star_short(b):
    sub = (b.get("subType") or "").lower()
    if "white dwarf" in sub:
        return "White dwarf"
    if "neutron" in sub:
        return "Neutron star"
    if "black hole" in sub:
        return "Black hole"
    cls = b.get("spectralClass") or (b.get("subType") or "?").split(" ")[0]
    return f"{cls} star"


def _planet_short(b):
    sub = b.get("subType") or "Planet"
    if sub.lower() in PLANET_SHORT:
        return PLANET_SHORT[sub.lower()]
    m = re.match(r"Class (\w+) gas giant", sub, re.I)
    return f"Gas giant {m.group(1)}" if m else sub


def _surface_type(stype, name=""):
    """Station types that sit on a planet's surface (ports, outposts and Odyssey settlements). An orbital
    construction site isn't, whatever EDSM calls it (it lists them as planetary outposts)."""
    t, n = (stype or "").lower(), str(name or "").lower()
    if "orbital construction site" in n:
        return False
    if "planetary construction site" in n:   # (your journal may know one only as an FSS "installation")
        return True
    return "planetary" in t or "settlement" in t or "surface" in t


def _station_pic(stype, surface, name=""):
    """Which wireframe the picture shows for a station: its own shape, or (on a planet) the planet."""
    t, n = (stype or "").lower(), str(name or "").lower()
    if "orbital construction site" in n or "space construction" in t:   # EDSM lists these as planetary outposts
        return "construction"
    if surface or "planetary" in t or "settlement" in t:
        return "surface"
    for key, kind in (("coriolis", "coriolis"), ("orbis", "orbis"), ("ocellus", "ocellus"), ("bernal", "ocellus"),
                      ("dodec", "dodec"), ("asteroid", "asteroid"), ("mega", "megaship"), ("carrier", "carrier"),
                      ("nav beacon", "beacon"), ("tourist", "tourist"), ("installation", "installation"),
                      ("construction", "construction"), ("outpost", "outpost")):
        if key in t:
            return kind
    return "outpost"


STATION_ICONS = (   # the list's icon for a station type, after the game's system map ("planetary outpost" before "outpost")
    ("construction", "construction"), ("coriolis", "coriolis"), ("orbis", "orbis"), ("ocellus", "ocellus"),
    ("bernal", "ocellus"), ("dodec", "dodec"), ("asteroid", "asteroid"), ("mega", "megaship"), ("squadron", "squadron"),
    ("carrier", "carrier"), ("settlement", "settlement"), ("planetary port", "port"), ("planetary outpost", "surface"),
    ("installation", "installation"), ("nav beacon", "beacon"), ("tourist", "tourist"), ("outpost", "outpost"),
)


def station_icon(stype, name=""):
    """Which icon the list shows for a station, settlement, installation or beacon."""
    t = str(stype or "").lower()
    if "construction site" in str(name or "").lower():   # colonisation sites are listed under other types
        return "construction"
    return next((icon for key, icon in STATION_ICONS if key in t), "station")


def _jtime(ts):
    """A journal time ('2026-10-28T20:36:44Z', UTC) as the tab shows times, like EDSM's: '28 Oct 2026 20:36'."""
    return _edsm_time(str(ts or "")[:19].replace("T", " "))


def _gc_km(lat1, lon1, lat2, lon2, radius_km):
    """Great-circle distance and initial bearing between two surface points."""
    import math
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    km = 2 * radius_km * math.asin(min(1.0, math.sqrt(h)))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return km, (math.degrees(math.atan2(y, x)) + 360) % 360


def count_visits(journal_dir: Path, system: str) -> dict:
    """How often you've jumped into a system, from every journal you have."""
    visits, first, last, needle = 0, "", "", f'"{system}"'
    for path in sorted(journal_dir.glob("Journal.*.log")):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if needle not in line or ('"FSDJump"' not in line and '"CarrierJump"' not in line):
                        continue
                    try:
                        ev = json.loads(line)
                    except ValueError:
                        continue
                    if ev.get("StarSystem") == system and ev.get("event") in ("FSDJump", "CarrierJump"):
                        visits += 1
                        first = first or ev.get("timestamp", "")
                        last = ev.get("timestamp", "")
        except OSError:
            continue
    return {"visits": visits, "first": first, "last": last}


def build_syst(system: str, raw: dict, you: dict):
    """Turn EDSM's answers into the tab's list: bodies in orbit order, each followed
    by its stations (placed by EDSM, or matched by distance and marked est.).
    Returns (model for the page, lookup index for the server)."""
    bodies = [b for b in (raw.get("bodies") or {}).get("bodies") or [] if b.get("name")]
    stations_raw = (raw.get("stations") or {}).get("stations") or []
    traffic = raw.get("traffic") or {}
    deaths = (raw.get("deaths") or {}).get("deaths") or {}
    value = raw.get("estimated-value") or {}
    valuable = {v.get("bodyName"): v.get("valueMax") for v in value.get("valuableBodies") or []}
    id64 = next((r.get("id64") for r in raw.values() if isinstance(r, dict) and r.get("id64")), None)

    # stations: one per name (EDSM sometimes lists a station twice), newest information wins
    stations = {}
    for s in stations_raw:
        upd = (s.get("updateTime") or {}).get("information") or ""
        if s.get("name") and (s["name"] not in stations or upd > ((stations[s["name"]].get("updateTime") or {}).get("information") or "")):
            stations[s["name"]] = s
    carriers = [s for s in stations.values() if "carrier" in (s.get("type") or "").lower()]
    stations = [s for s in stations.values() if s not in carriers]

    # body tree: parent = the nearest star or planet above it (barycentres skipped)
    by_bid = {b["bodyId"]: b for b in bodies if b.get("bodyId") is not None}
    by_name = {b["name"].lower(): b for b in bodies}
    dist = lambda x: x.get("distanceToArrival") if x.get("distanceToArrival") is not None else 1e12

    def parent_of(b):
        for p in b.get("parents") or []:
            for kind, pid in p.items():
                if kind in ("Star", "Planet"):
                    return pid if pid in by_bid and pid != b.get("bodyId") else None
        return None

    kids, roots = {}, []
    for b in bodies:
        pid = parent_of(b)
        (kids.setdefault(pid, []) if pid is not None else roots).append(b)
    roots.sort(key=lambda b: (not b.get("isMainStar"), dist(b)))

    # which body each station belongs to
    homes, surface_sites = {}, {}
    for s in stations:
        body = s.get("body") or {}
        host, est = by_name.get(str(body.get("name", "")).lower()), False
        if host is None and bodies and s.get("distanceToArrival") is not None:
            best = min(bodies, key=lambda b: abs(dist(b) - s["distanceToArrival"]))
            if abs(dist(best) - s["distanceToArrival"]) <= max(1.5, 0.004 * s["distanceToArrival"]):
                host, est = best, True
        s["_est"] = est
        s["_lat"], s["_lon"] = body.get("latitude"), body.get("longitude")
        if s.get("type") and not _surface_type(s["type"], s["name"]):   # orbital: EDSM sometimes gives one a latitude anyway
            s["_lat"] = s["_lon"] = None
        s["_host"] = host["name"] if host else ""
        homes.setdefault(host["name"] if host else None, []).append(s)
        if host and s["_lat"] is not None:
            surface_sites.setdefault(host["name"], []).append(s)
    for lst in homes.values():
        lst.sort(key=lambda s: (s["_lat"] is not None, dist(s), s["name"]))   # orbital first, then the surface

    entries, names, raw_of = [], {}, {}

    def bkey(b):
        return f"b{b['bodyId']}" if b.get("bodyId") is not None else f"e{b.get('id')}"

    def skey(s):
        return f"s{s['marketId']}" if s.get("marketId") else "s-" + re.sub(r"\W+", "-", s["name"].lower())

    def add_station(s, depth):
        surface = s["_lat"] is not None
        kind_txt = s.get("type") or "Station"
        site, short = construction_site(s["name"])   # a construction site goes by its own name, its kind after
        far = s.get("distanceToArrival")
        where = (f"{s['_host']} surface" if surface else
                 (f"near {s['_host']} (est.)" if s["_est"] else (s["_host"] or ("body unknown" if far is not None else "in this system"))))
        lab = f"{f'{site.capitalize()} construction site' if site else kind_txt} · {where}" + ("" if surface or far is None else f" · {_num(far)} ls")
        chips = [{"t": t} for t, ok in (("Market", s.get("haveMarket")), ("Shipyard", s.get("haveShipyard")),
                                         ("Outfitting", s.get("haveOutfitting"))) if ok]
        if s["_est"]:
            chips.append({"t": "Est. orbit"})
        econ = s.get("economy") or "-"
        if s.get("secondEconomy") and s.get("secondEconomy") != econ:
            econ += f" / {s['secondEconomy']}"
        icon = station_icon(kind_txt, s["name"])
        rows = [] if icon in ("installation", "beacon", "tourist") else [   # nobody runs a beacon
            ["Faction", (s.get("controllingFaction") or {}).get("name") or "-", False],
            ["Government", s.get("government") or "-", False],
            ["Economy", econ, False], ["Allegiance", s.get("allegiance") or "-", False]]
        if s.get("otherServices"):
            rows.append(["Services", " · ".join(s["otherServices"]), True])
        pads = s.get("landingPads")
        if isinstance(pads, dict):   # (Spansh's)
            rows.append(["Landing pads", " · ".join(f"{pads.get(k) or 0} {k}" for k in ("small", "medium", "large")), True])
        if surface:
            rows.append(["Position" + (" (your journal)" if s.get("_jpos") else ""), f"{s['_lat']:.2f}, {s['_lon']:.2f}", True])
        if s.get("_journal"):   # EDSM doesn't list it: it's from your own journal
            rows.append(["From your journal", _jtime(s.get("_seen")) or "-", True])
        else:   # when EDSM last heard about each part of it (in this PC's time)
            upd = s.get("updateTime") or {}
            for part in (("information",) if icon in ("installation", "beacon", "tourist") else
                         ("information", "market", "shipyard", "outfitting")):
                rows.append([f"{part.capitalize()} updated", _edsm_time(upd.get(part)) or "-", False])
        src = entry_source(s)
        e = {"key": skey(s), "kind": "station", "depth": depth, "icon": icon, "label": short, "src": src,
             "right": "est." if s["_est"] else "", "lab": lab, "name": short, "chips": chips, "rows": rows,
             "pic": {"kind": _station_pic(kind_txt, surface, s["name"]), "body": s["_host"], "lat": s["_lat"], "lon": s["_lon"]},
             "surface": surface, "body": s["_host"]}
        # only approached (your journal's ApproachSettlement, or Spansh's record of someone's): on the surface but of no
        # known type - it may be an Odyssey settlement or not (unsure: the page offers its schematics quietly)
        unsure = bool(surface and s.get("type") in (None, "", "Settlement"))   # ("Settlement": its word for one of no known kind)
        if kind_txt == "Odyssey Settlement" or (site == "planetary" and surface) or unsure:   # it has layout plans (schematics), by its economy
            e["settlement"] = {"key": settlement_key(system, s), "economy": s.get("economy") or "",
                               "category": schematic_category(s.get("economy")), "guess": settlement_guess(short)}
            if unsure:
                e["settlement"]["unsure"] = True
        entries.append(e)
        names[s["name"].lower()] = e["key"]
        raw_of[e["key"]] = s

    def add_body(b, depth):
        star = b.get("type") == "Star"
        short = _short_name(b["name"], system)
        sites = surface_sites.get(b["name"], [])
        orbiting = [s for s in homes.get(b["name"], []) if s["_lat"] is None]
        if star:
            label, icon = f"{short} · {_star_short(b)}", "star"
            lab = "Star · " + ("arrival point" if b.get("isMainStar") else f"{_num(dist(b))} ls")
            chips = [{"t": t} for t, ok in (("Scoopable", b.get("isScoopable")), ("Main star", b.get("isMainStar"))) if ok]
            rows = [["Class", f"{b.get('spectralClass') or ''} {b.get('luminosity') or ''} · {b.get('subType') or ''}".strip(" ·"), True],
                    ["Temperature", f"{_num(b.get('surfaceTemperature'))} K", False],
                    ["Mass", f"{float(b.get('solarMasses') or 0):.2f} suns", False],
                    ["Radius", f"{float(b.get('solarRadius') or 0):.2f} suns", False],
                    ["Age", f"{_num(b.get('age'))} million years", False]]
            for belt in b.get("belts") or []:
                rows.append(["Belt", f"{belt.get('name')} · {belt.get('type')}", True])
            if b.get("isMainStar"):
                d = traffic.get("discovery") or {}
                if d.get("commander"):
                    rows.append(["System first logged (EDSM)", f"CMDR {d['commander']} · {str(d.get('date', ''))[:10]}", True])
                if value.get("estimatedValue"):
                    rows.append(["Exploration value", f"{_num(value['estimatedValue'])} CR · {_num(value.get('estimatedValueMapped'))} CR mapped", True])
                if deaths:
                    rows.append(["Commander deaths (EDSM)", f"{deaths.get('week', 0)} this week · {_num(deaths.get('total', 0))} all time", True])
        else:
            label = short if b.get("_standin") else f"{short} {_planet_short(b)}"   # a stand-in: only its name is known
            icon = "landable" if b.get("isLandable") else "planet"
            host = parent_of(b)
            host_name = by_bid[host]["name"] if host is not None else system
            pair = ""
            first = (b.get("parents") or [{}])[0]
            if "Null" in first:
                mates = [o["name"] for o in bodies if o is not b and (o.get("parents") or [{}])[0] == first and o.get("type") != "Star"]
                if len(mates) == 1:
                    pair = f" · paired with {mates[0]}"
            lab = f"{'Moon' if depth else 'Planet'} · {_num(dist(b))} ls" + (pair or f" · orbits {host_name}")
            chips = []
            if b.get("isLandable"):
                chips.append({"t": "Landable"})
            tf = b.get("terraformingState") or ""
            if tf and tf.lower() not in ("not terraformable", ""):
                chips.append({"t": "Terraforming" if "terraforming" == tf.lower() else "Terraformable"})
            if b.get("rings"):
                chips.append({"t": "Ringed"})
            if sites:
                chips.append({"t": f"{len(sites)} surface site{'s' if len(sites) != 1 else ''}"})
            if orbiting:
                chips.append({"t": f"{len(orbiting)} station{'s' if len(orbiting) != 1 else ''}" + (" (est.)" if all(s["_est"] for s in orbiting) else "")})
            rows = [["Type", b.get("subType") or "-", True],
                    ["Gravity", f"{float(b.get('gravity') or 0):.2f} g", False],
                    ["Temperature", f"{_num(b.get('surfaceTemperature'))} K", False],
                    ["Atmosphere", b.get("atmosphereType") or "None", False],
                    ["Pressure", f"{float(b.get('surfacePressure') or 0):.2f} atm", False],
                    ["Radius", f"{_num(b.get('radius'))} km", False],
                    ["Day", _days(b.get("rotationalPeriod")) + (", locked" if b.get("rotationalPeriodTidallyLocked") else ""), False],
                    ["Year", _days(b.get("orbitalPeriod")), False]]
            if b.get("atmosphereComposition"):
                rows.append(["Air", " · ".join(f"{k} {v:.1f}%" for k, v in b["atmosphereComposition"].items()), True])
            if b.get("materials"):
                rows.append(["Materials", " · ".join(f"{k} {v:.1f}" for k, v in b["materials"].items()), True])
            for ring in b.get("rings") or []:
                rows.append(["Ring", f"{_short_name(ring.get('name', ''), system)} · {ring.get('type')}", True])
            if tf and tf.lower() != "not terraformable":
                rows.append(["Terraforming", tf, False])
            if b.get("volcanismType") and b["volcanismType"] != "No volcanism":
                rows.append(["Volcanism", b["volcanismType"], False])
            if valuable.get(b["name"]):
                rows.append(["Scan value", f"Up to {_num(valuable[b['name']])} CR mapped", True])
        d = b.get("discovery") or {}
        if d.get("commander"):
            rows.append(["First discovered", f"CMDR {d['commander']} · {str(d.get('date', ''))[:10]}", True])
        if b.get("_journal"):   # EDSM doesn't list it: it's from your own journal
            rows.append(["From your journal", ("Seen on approach " if b.get("_standin") else "Scanned ") + _jtime(b.get("_seen")), True])
        else:
            rows.append([f"{SOURCE_NAMES.get(b.get('_from') or 'edsm', 'EDSM')} updated", _edsm_time(b.get("updateTime")) or "-", True])
        sig = b.get("signals") or {}
        counts = sig.get("counts") or {}
        if counts:   # (Spansh's) at the bottom: what's there to find on it
            order = ["Biological", "Geological", "Human", "Guardian", "Thargoid", "Mining", "Other"]
            names_ = sorted(counts, key=lambda k: (order.index(k) if k in order else len(order), k))
            rows.append(["Signals", " · ".join(f"{k} {counts[k]}" for k in names_), True])
        if sig.get("genuses"):
            rows.append(["Biology", " · ".join(sig["genuses"]), True])
        mine = bool(b.get("_jscan") or (b.get("_journal") and not b.get("_standin")))   # scanned by you (your journal's Scan)
        if mine:
            chips.append({"t": "Scanned by you"})
        e = {"key": bkey(b), "kind": "star" if star else "planet", "depth": depth, "icon": icon, "label": label, "mine": mine,
             "src": entry_source(b),
             "right": _num(dist(b)) if dist(b) < 1e11 else "", "lab": lab, "name": b["name"], "chips": chips, "rows": rows,
             "pic": {"kind": "star" if star else "globe", "body": b["name"],
                     "sites": [{"name": s["name"], "lat": s["_lat"], "lon": s["_lon"], "key": skey(s)} for s in sites]},
             "radius": b.get("radius") or (float(b.get("solarRadius") or 0) * 695700), "bodyId": b.get("bodyId"),
             "gravity": float(b["gravity"]) if isinstance(b.get("gravity"), (int, float)) and not isinstance(b.get("gravity"), bool) else None}   # (g: Atk's fall times)
        entries.append(e)
        names[b["name"].lower()] = e["key"]
        raw_of[e["key"]] = b
        for s in homes.get(b["name"], []):
            add_station(s, depth + 1)
        for k in sorted(kids.get(b.get("bodyId"), []), key=lambda k: (k.get("bodyId") is None, k.get("bodyId") or 0, dist(k))):   # orbit order (the game numbers bodies outwards)
            add_body(k, depth + (0 if star else 1))

    for r in roots:
        add_body(r, 0)
    for b in bodies:   # anything left over (a loop in the parent data) still gets listed
        if b["name"].lower() not in names:
            add_body(b, 0)
    for s in homes.get(None, []):
        add_station(s, 0)
    if carriers:
        rows = [[c["name"], _edsm_time((c.get("updateTime") or {}).get("information")), True] for c in sorted(carriers, key=lambda c: c["name"])[:40]]
        csrc = carriers[0].get("_from") or "edsm"
        entries.append({"key": "carriers", "kind": "station", "depth": 0, "icon": "carrier", "label": f"Fleet carriers ×{len(carriers)}", "src": csrc,
                        "right": "", "lab": f"Fleet carriers seen here ({SOURCE_NAMES.get(csrc, 'EDSM')})", "name": f"{len(carriers)} fleet carrier{'s' if len(carriers) != 1 else ''}",
                        "chips": [], "rows": rows, "pic": {"kind": "carrier"}, "surface": False, "body": ""})

    # the system map (map view): every body with what its wireframe needs, in the list's order;
    # the orbital stations beside their body; surface sites counted on their planet; carriers as a count
    def nulls_of(b):   # the barycentres a body orbits, innermost first, up to its star or planet
        out = []
        for p in b.get("parents") or []:
            if "Null" not in p:
                break
            out.append(p["Null"])
        return out

    def fnum(v, places=3):
        try:
            return round(float(v), places)
        except (TypeError, ValueError):
            return None

    mbodies, mstations = [], []
    for e in entries:
        raw_b = raw_of.get(e["key"])
        if e["kind"] in ("star", "planet") and raw_b:
            b = raw_b
            par = parent_of(b)
            on_surface = [x for x in homes.get(b["name"], []) if x["_lat"] is not None or _surface_type(x.get("type"), x["name"])]
            ports = sum(1 for x in on_surface if re.search(r"port|outpost", (x.get("type") or "").lower()))
            short = _short_name(b["name"], system)
            if short.lower() == system.lower():
                short = b.get("spectralClass") or ("Star" if b.get("type") == "Star" else short)
            tilt = fnum(b.get("axialTilt"), 5)
            mbodies.append({
                "key": e["key"], "parent": bkey(by_bid[par]) if par is not None else None, "nulls": nulls_of(b),
                "star": b.get("type") == "Star", "main": bool(b.get("isMainStar")), "name": b["name"], "lbl": short,
                "sub": b.get("subType") or "", "cls": b.get("spectralClass") or "", "lum": b.get("luminosity") or "",
                "km": fnum(b.get("radius") or (float(b.get("solarRadius") or 0) * 695700) or None, 1),
                "rot": fnum(b.get("rotationalPeriod"), 5), "locked": bool(b.get("rotationalPeriodTidallyLocked")),
                "tilt": round(tilt * 57.29578, 2) if tilt is not None else None,
                "land": bool(b.get("isLandable")), "ports": ports, "sites": len(on_surface) - ports,
                "rings": [{"t": r.get("type") or "", "i": fnum(r.get("innerRadius"), 0), "o": fnum(r.get("outerRadius"), 0)}
                          for r in b.get("rings") or []],
                "belts": [{"t": r.get("type") or "", "name": _short_name(r.get("name") or "", system)} for r in b.get("belts") or []],
                "ls": fnum(b.get("distanceToArrival"), 0), "gas": "gas giant" in (b.get("subType") or "").lower(),
                "rsol": fnum(b.get("solarRadius"), 6), "mass": fnum(b.get("solarMasses"), 4), "temp": b.get("surfaceTemperature"),
                "mine": bool(e.get("mine")),   # you've scanned it yourself
            })
        elif e["kind"] == "station" and raw_b and not e.get("surface") and not _surface_type(raw_b.get("type"), raw_b["name"]):
            mstations.append({"key": e["key"], "host": names.get(raw_b["_host"].lower()) if raw_b["_host"] else None,
                              "kind": e["pic"]["kind"], "icon": e["icon"], "est": bool(raw_b["_est"]), "name": raw_b["name"],
                              "type": raw_b.get("type") or "Station"})

    # the order the UFC cursor steps through the map (as it's laid out: stations with no known
    # body and the fleet carriers sit under the main star), and the planet each surface site is on
    mkeys = {x["key"] for x in mbodies} | {x["key"] for x in mstations} | ({"carriers"} if carriers else set())
    loose = [x["key"] for x in mstations if not x["host"]] + (["carriers"] if carriers else [])
    order = [e["key"] for e in entries if e["key"] in mkeys and e["key"] not in loose]
    main_key = next((x["key"] for x in mbodies if x["main"]), mbodies[0]["key"] if mbodies else None)
    at = order.index(main_key) + 1 if main_key in order else len(order)
    host_of = {x["key"]: x["host"] for x in mstations}
    while at < len(order) and host_of.get(order[at]) == main_key:
        at += 1
    order[at:at] = loose
    site_hosts = {e["key"]: names[e["body"].lower()] for e in entries
                  if e["kind"] == "station" and e["key"] not in mkeys and e.get("body") and e["body"].lower() in names}

    sites_index = {}
    for e in entries:
        if e["kind"] == "station" and e.get("surface"):
            host_key = names.get(e["body"].lower())
            if host_key:
                sites_index.setdefault(host_key, []).append((e["key"], e["pic"]["lat"], e["pic"]["lon"]))
    radii = {e["key"]: e.get("radius") or 0 for e in entries if e["kind"] in ("planet", "star")}
    breakdown = sorted((traffic.get("breakdown") or {}).items(), key=lambda kv: -kv[1]) if isinstance(traffic.get("breakdown"), dict) else []
    model = {
        "system": system, "id64": id64,
        "entries": entries, "bodies": len(bodies),
        "traffic": {"day": (traffic.get("traffic") or {}).get("day"), "week": (traffic.get("traffic") or {}).get("week"),
                    "total": (traffic.get("traffic") or {}).get("total"), "seen": breakdown[:4]},
        "you": you,
        "map": {"bodies": mbodies, "stations": mstations, "carriers": len(carriers), "order": order, "hosts": site_hosts},
    }
    index = {"names": names, "sites": sites_index, "radii": radii}
    return model, index


def situation(ev: dict) -> dict:
    """The local-situation report from a Location / FSDJump / CarrierJump event."""
    controlling = ev.get("SystemFaction")
    if isinstance(controlling, dict):
        controlling = controlling.get("Name", "")
    factions = []
    for f in ev.get("Factions") or []:
        states = [pretty(s.get("State")) for s in (f.get("ActiveStates") or [])]
        if not states and pretty(f.get("FactionState")):
            states = [pretty(f.get("FactionState"))]
        factions.append({
            "name": f.get("Name", ""),
            "influence": round(float(f.get("Influence") or 0) * 100, 1),
            "states": [s for s in states if s],
            "pending": [pretty(s.get("State")) for s in (f.get("PendingStates") or []) if pretty(s.get("State"))],
            "rep": f.get("MyReputation"),
            "controlling": f.get("Name", "") == controlling,
        })
    factions.sort(key=lambda f: -f["influence"])
    conflicts = []
    for c in ev.get("Conflicts") or []:
        a, b = c.get("Faction1") or {}, c.get("Faction2") or {}
        war_type = str(c.get("WarType") or "").lower()
        conflicts.append({
            "type": {"war": "War", "civilwar": "Civil war", "election": "Election"}.get(war_type, pretty(war_type) or "Conflict"),
            "status": c.get("Status", ""),
            "a": a.get("Name", ""), "b": b.get("Name", ""),
            "a_won": a.get("WonDays", 0), "b_won": b.get("WonDays", 0),
        })
    econ2 = clean(ev.get("SystemSecondEconomy_Localised") or ev.get("SystemSecondEconomy"))
    return {
        "system": ev.get("StarSystem", ""),
        "allegiance": clean(ev.get("SystemAllegiance")) or "Independent",
        "government": clean(ev.get("SystemGovernment_Localised") or ev.get("SystemGovernment")),
        "security": clean(ev.get("SystemSecurity_Localised") or ev.get("SystemSecurity")).title(),
        "economy": clean(ev.get("SystemEconomy_Localised") or ev.get("SystemEconomy")),
        "economy2": "" if econ2.lower() in ("", "none") else econ2,
        "population": ev.get("Population", 0),
        "controlling": controlling or "",
        "power": ev.get("ControllingPower") or ", ".join(ev.get("Powers") or []),
        "power_state": pretty(ev.get("PowerplayState")),
        "factions": factions,
        "conflicts": conflicts,
    }


def child_env() -> dict:
    env = dict(os.environ)
    for var in PAID_KEY_VARS:
        env.pop(var, None)
    return env


def run_cli(cmd, stdin_text=None, timeout=60):
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, cwd=str(WORK_DIR), env=child_env(), creationflags=NO_WINDOW,
    )
    if stdin_text is None:
        kwargs["stdin"] = subprocess.DEVNULL
    else:
        kwargs["input"] = stdin_text
    return subprocess.run(cmd, **kwargs)


# Mission kinds, from the journal's internal mission name (first match wins). HUNTS are the kinds whose
# named target is someone to kill (the others' named person is someone to meet).
HUNTS = ("Assassination", "Massacre")
MISSION_KINDS = [
    ("massacre", "Massacre"), ("assassin", "Assassination"), ("passengerevacuation", "Evacuation"),
    ("sightseeing", "Passengers"), ("longdistanceexpedition", "Passengers"), ("passenger", "Passengers"),
    ("courier", "Courier"), ("delivery", "Delivery"), ("collect", "Source & return"), ("mining", "Mining"),
    ("salvage", "Salvage"), ("rescue", "Rescue"), ("disable", "Disable"), ("scan", "Scan"),
    ("altruismcredits", "Donation"), ("altruism", "Donation"), ("smuggle", "Smuggling"), ("piracy", "Piracy"),
    ("hack", "Hacking"), ("sabotage", "Sabotage"), ("productionheist", "Heist"), ("heist", "Heist"),
    ("reboot", "Reboot"), ("onslaught", "Onslaught"), ("defen", "Defence"), ("release", "Release"),
]


def mission_kind(name) -> str:
    """'Mission_DeliveryWing_Agriculture' -> 'Delivery'; on-foot ones say so ('On foot · Salvage')."""
    n = str(name or "").lower()
    kind = next((label for key, label in MISSION_KINDS if key in n), "Contract")
    return f"On foot · {kind}" if "onfoot" in n else kind


def commodity_name(ev) -> str:
    """The commodity a mission is about ('$Tea_Name;' -> 'Tea' when there's no localised name)."""
    loc = ev.get("Commodity_Localised")
    if loc:
        return str(loc).strip()
    raw = str(ev.get("Commodity") or "").strip("$;")
    raw = re.sub(r"_name$", "", raw, flags=re.I)
    return pretty(raw.replace("_", " ")) if raw else ""


MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def game_date(d) -> str:
    """A date in Elite's calendar: '04 JUL 3312'."""
    return f"{d.day:02d} {MONTHS[d.month - 1]} {d.year + GAME_YEARS}"


def dossier_ids(key, accepted):
    """A target's serial number (5 digits) and incept date - from its name, so they're the same every time - and the
    time they're measured from (its first contract's acceptance)."""
    import zlib
    h = zlib.crc32(str(key).encode("utf-8"))
    t = parse_time(accepted) or now_utc()
    return f"{h % 100000:05d}", (t - timedelta(days=(h >> 8) % DOSSIER_LIFESPAN_DAYS)).date(), t


def dossier_age(incept, t) -> str:
    """How long before t a unit was incepted: '3 months ago', '2 years 4 months ago'."""
    months = max(0, (t.date() - incept).days) // 30
    if months < 1:
        return "under a month ago"
    y, mo = divmod(months, 12)
    parts = ([f"{y} year" + ("s" if y != 1 else "")] if y else []) + ([f"{mo} month" + ("s" if mo != 1 else "")] if mo else [])
    return " ".join(parts) + " ago"


# The threat a target is: in ship, once scanned, from its pilot rank and ship (confirmed); before that, or on foot (no
# scans there), from the contract - its reward, a wing contract, a hard one, a batch's size (provisional; estimated).
THREAT_LEVELS = ("LOW", "MODERATE", "HIGH", "EXTREME")
RANK_THREAT = (0, 0, 1, 1, 2, 2, 3, 4, 4)   # Harmless ... Elite
SHIPS_SMALL = {"sidewinder", "eagle", "hauler", "adder", "empire_eagle", "viper", "viper_mkiv", "cobramkiii", "cobramkiv",
               "cobramkv", "diamondback", "diamondbackxl", "dolphin", "empire_courier", "vulture"}
SHIPS_LARGE = {"anaconda", "cutter", "federation_corvette", "type7", "type9", "type9_military", "belugaliner", "orca",
               "empire_trader", "panthermkii"}


def threat_of(mode, kind, reward, wing, scan=None, hard=False, units=None):
    """(level - an index into THREAT_LEVELS - and what it's from)."""
    if kind == "person" and mode == "ship" and scan and scan.get("rank") in COMBAT_RANKS:
        ship = str(scan.get("ship_id") or "").lower()
        score = (RANK_THREAT[min(8, COMBAT_RANKS.index(scan["rank"]))] + (0 if ship in SHIPS_SMALL else 2 if ship in SHIPS_LARGE else 1)
                 + (1 if wing else 0))
        return (0 if score <= 1 else 1 if score <= 3 else 2 if score <= 5 else 3), "confirmed by scan"
    try:
        reward = float(reward or 0)
    except (TypeError, ValueError):
        reward = 0.0
    score = ((0 if reward < 200_000 else 1 if reward < 750_000 else 2 if reward < 2_000_000 else 3) + (1 if wing else 0)
             + (1 if hard else 0) + (1 if (units or 0) >= 20 else 0) + (1 if (units or 0) >= 50 else 0))
    level = 0 if score == 0 else 1 if score <= 2 else 2 if score == 3 else 3
    return level, ("estimated" if mode == "foot" else "provisional - no scan yet")


_SHIP_COMMON = {"Eagle", "Hauler", "Dolphin", "Orca", "Corsair", "Mandalay", "Imperial", "Federal", "Alliance", "Beluga"}
_SHIP_WORDS = {n for n in SHIP_NAMES.values() if n not in _SHIP_COMMON} | \
              {n.split()[0] for n in SHIP_NAMES.values() if n.split()[0] not in _SHIP_COMMON and len(n.split()[0]) > 2}
_SHIP_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(_SHIP_WORDS, key=len, reverse=True)) + r")\b")
_DOSSIER_BANNED = re.compile(r"\b(players?|the game|in-game|FT3000|UCEC)\b", re.I)


def check_dossier(reply, kind, ship_known=True):
    """The AI's reply as a subject file's fields (DOSSIER_FIELDS[kind]), and what's wrong with it ([] if nothing):
    JSON with exactly those keys, each plain text of the right length (DOSSIER_SLACK either way) or one of its letters;
    nothing about the game or the player; no ship named before there's been a scan."""
    text = str(reply or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:]
    i, j = text.find("{"), text.rfind("}")
    try:
        got = json.loads(text[i:j + 1]) if i >= 0 and j > i else None
    except ValueError:
        got = None
    if not isinstance(got, dict):
        return {}, ["the reply wasn't one JSON object"]
    spec, problems, out = DOSSIER_FIELDS[kind], [], {}
    for k in got:
        if k not in spec:
            problems.append(f'"{k}" isn\'t one of the keys')
    for k, rule in spec.items():
        v = got.get(k)
        if not isinstance(v, str):
            problems.append(f'"{k}" is missing' if k not in got else f'"{k}" isn\'t text')
            continue
        v = " ".join(v.split()) if "\n" not in v else v.strip()
        if isinstance(rule, str):
            v = v.upper()
            if v not in tuple(rule):
                problems.append(f'"{k}" must be one of {", ".join(rule)}')
        else:
            if "\n" in v or any(c in v for c in "*#`|"):
                problems.append(f'"{k}" has line breaks or markdown')
            n, lo, hi = len(v.split()), rule[0], rule[1]
            if n < int(lo * (1 - DOSSIER_SLACK)) or n > round(hi * (1 + DOSSIER_SLACK)):
                problems.append(f'"{k}" is {n} words ({lo}-{hi})')
            if _DOSSIER_BANNED.search(v):
                problems.append(f'"{k}" mentions the game, the player or the FT3000')
            if not ship_known and _SHIP_RE.search(v):
                problems.append(f'"{k}" names a ship ({_SHIP_RE.search(v).group(1)}) before any scan')
        out[k] = v
    return out, problems


def mission_verb(m) -> str:
    """What a contract asks: its title up to the target's name ('Assassinate Deserter: Marek Holloway' -> 'Assassinate
    Deserter'), else its kind."""
    title = str(m.get("title") or "")
    head = title.split(":", 1)[0].strip() if ":" in title else title
    return head or m.get("cat") or "Contract"


def mission_record(ev):
    """What the board keeps of a mission from its MissionAccepted event, and whether it's a hunt (an assassination's
    named target, or a massacre's kill count: grouped by target, with a backstory). A named person on any other
    mission is someone to meet, not hunt (on foot: take a package to them, or collect one)."""
    name = clean(ev.get("Target_Localised") or ev.get("Target"))
    kill_count = ev.get("KillCount")
    cat = mission_kind(ev.get("Name"))
    is_target = bool(kill_count) or bool(name and cat.split(" · ")[-1] in HUNTS)
    contact = "" if is_target else name
    kind = ("person" if name else "faction") if is_target else "contract"
    title = clean(ev.get("LocalisedName") or ev.get("Name"))
    commodity, count = commodity_name(ev), ev.get("Count")
    pax = ev.get("PassengerCount")
    donation = ev.get("Donation")
    try:
        donation = int(donation) if donation not in (None, "") else None
    except (TypeError, ValueError):
        donation = None
    if is_target:
        name = name or clean(ev.get("TargetFaction")) or "Unknown hostiles"
        key = target_key(name)
    else:   # a line short enough for the index: who it's for, what's to be moved, or the mission's own name
        if contact and cat.endswith(("Delivery", "Source & return")):
            name = f"Package {'to' if cat.endswith('Delivery') else 'from'} {contact}"
        elif commodity and isinstance(count, (int, float)) and count:
            name = f"{int(count):,} × {commodity}"
        elif isinstance(pax, (int, float)) and pax:
            name = f"{int(pax)} passenger" + ("s" if pax != 1 else "")
        elif donation:
            name = f"Donate {donation:,} CR"
        elif mission_kind(ev.get("Name")) == "Courier" and (ev.get("DestinationStation") or ev.get("DestinationSystem")):
            name = f"Data to {ev.get('DestinationStation') or ev.get('DestinationSystem')}"
        else:
            name = title or mission_kind(ev.get("Name"))
        key = f"m:{ev.get('MissionID')}"
    m = {
        "id": ev.get("MissionID"),
        "key": key,
        "target": name,
        "kind": kind,
        "cat": cat,
        "contact": contact,
        "settlement": clean(ev.get("DestinationSettlement")),
        "commodity": commodity,
        "count": count if isinstance(count, (int, float)) else None,
        "passengers": {"count": int(pax), "vip": bool(ev.get("PassengerVIPs")), "wanted": bool(ev.get("PassengerWanted")),
                       "type": pretty(ev.get("PassengerType"))} if isinstance(pax, (int, float)) and pax else None,
        "donation": donation,
        "influence": str(ev.get("Influence") or ""),
        "reputation": str(ev.get("Reputation") or ""),
        "depot": None,
        "partial": False,
        "target_type": clean(ev.get("TargetType_Localised") or ev.get("TargetType")),
        "target_faction": clean(ev.get("TargetFaction")),
        "issuer": clean(ev.get("Faction")),
        "title": title,
        "system": ev.get("DestinationSystem", ""),
        "station": ev.get("DestinationStation", ""),
        "expiry": ev.get("Expiry", ""),
        "reward": ev.get("Reward", 0),
        "kill_count": kill_count,
        "wing": bool(ev.get("Wing")),
        "accepted": ev.get("timestamp", ""),
        "hard": "_hard" in str(ev.get("Name") or "").lower(),   # (a hard one: more of a threat, for the subject file)
        "status": "active",
    }
    return m, is_target


# --------------------------------------------------------------------------- #
# AI engines (subscription-based CLIs)
# --------------------------------------------------------------------------- #
class Engine:
    name = "none"

    def check(self):
        return False, "Dossiers are switched off (--engine none)."

    def write(self, system: str, instruction: str, details: str, timeout: int) -> str:
        raise RuntimeError("Dossiers are switched off.")


class ClaudeEngine(Engine):
    """Claude Code in print mode, signed in with a Claude Pro/Max subscription."""
    name = "claude"

    def __init__(self, model=None, exe=None):
        self.model = model
        self.exe = exe or shutil.which("claude")

    def check(self):
        if not self.exe:
            return False, ("Claude Code isn't installed or isn't on PATH. Install it, run `claude` once "
                           "and log in with your Claude Pro account.")
        try:
            proc = run_cli([self.exe, "auth", "status"], timeout=60)
            info = json.loads(proc.stdout)
        except Exception:
            return True, ("Using Claude Code (couldn't confirm the login type; `claude update` "
                          "enables that check).")
        method = info.get("authMethod")
        if method in ("claude.ai", "oauth_token"):
            return True, "Subject files: Claude, using your Claude subscription"
        if method in (None, "none"):
            return False, "Claude Code isn't logged in. Run `claude` in a terminal and log in with your Pro account."
        return False, (f"Claude Code is signed in with '{method}', which bills API credits, so subject files "
                       "are paused. Run `claude auth logout`, then `claude` and log in with your Pro account.")

    def write(self, system, instruction, details, timeout):
        # Prompt first, then flags; --tools "" (no tools) goes last.
        cmd = [self.exe, "-p", instruction,
               "--system-prompt", system,
               "--strict-mcp-config",
               "--no-session-persistence"]
        if self.model:
            cmd += ["--model", self.model]
        cmd += ["--tools", ""]
        proc = run_cli(cmd, stdin_text=details, timeout=timeout)
        if proc.returncode != 0:
            msg = (proc.stdout.strip() or proc.stderr.strip() or f"claude exited with code {proc.returncode}")
            raise RuntimeError(msg[:400])
        return proc.stdout


class CodexEngine(Engine):
    """OpenAI Codex CLI in exec mode, signed in with a ChatGPT plan."""
    name = "codex"

    def __init__(self, model=None, exe=None):
        self.model = model
        self.exe = exe or shutil.which("codex")

    def check(self):
        if not self.exe:
            return False, ("Codex CLI isn't installed or isn't on PATH. Install it, then run "
                           "`codex login` and choose 'Sign in with ChatGPT'.")
        try:
            proc = run_cli([self.exe, "login", "status"], timeout=60)
            status = (proc.stdout + "\n" + proc.stderr).lower()
        except Exception:
            return True, "Using Codex (couldn't confirm the login type)."
        if "chatgpt" in status:
            return True, "Subject files: ChatGPT, using your ChatGPT plan"
        if "api key" in status:
            return False, ("Codex is signed in with an API key, which bills credits, so dossiers are paused. "
                           "Run `codex logout`, then `codex login` and choose 'Sign in with ChatGPT'.")
        if "not logged in" in status:
            return False, "Codex isn't logged in. Run `codex login` and choose 'Sign in with ChatGPT'."
        return True, "Using Codex (couldn't confirm the login type)."

    def write(self, system, instruction, details, timeout):
        out_file = WORK_DIR / "codex_last_message.txt"
        try:
            out_file.unlink()
        except OSError:
            pass
        cmd = [self.exe, "exec", "--skip-git-repo-check", "--ephemeral", "-o", str(out_file)]
        if self.model:
            cmd += ["-m", self.model]
        cmd.append(f"{system}\n\n{instruction}")
        proc = run_cli(cmd, stdin_text=details, timeout=timeout)
        if proc.returncode != 0:
            msg = proc.stderr.strip().splitlines()[-1:] or [f"codex exited with code {proc.returncode}"]
            raise RuntimeError(msg[0][:400])
        if out_file.exists():
            return out_file.read_text(encoding="utf-8", errors="replace")
        return proc.stdout


def make_engine(name, model, exe):
    if name == "claude":
        return ClaudeEngine(model, exe)
    if name == "codex":
        return CodexEngine(model, exe)
    return Engine()


# --------------------------------------------------------------------------- #
# Shared state: what the journal (and Status.json, NavRoute.json, EDSM) has told us
# --------------------------------------------------------------------------- #
# The state is split by area. Each area keeps its own part and handles the journal events
# it cares about, in methods named on_<EventName>(ev, ts) - so to see what an event does,
# search for "on_" plus its name. BoardState calls them under its lock, area by area in the
# order of BoardState.areas (an event can matter to several). Each area also has view() for
# its part of what the page is sent (/api/state); BoardState.snapshot() puts them together.

class Commander:
    """You and your ship (the case file on Home), and this session's totals and log."""

    def __init__(self, board):
        self.board = board
        self.commander = ""
        self.ship = {"type": "", "name": "", "ident": ""}
        self.jump_range = None      # the ship's maximum jump range (Loadout), light years
        self.credits = None
        self.mode = ""
        self.ranks, self.progress, self.rep, self.stats, self.power = {}, {}, {}, {}, {}
        self.log_lines = deque(maxlen=60)
        self.log_seq = 0
        self.session = self._new_session("")

    @staticmethod
    def _new_session(since):
        return {"since": since, "kills": 0, "bounty": 0, "earned": 0, "jumps": 0}

    def log(self, ts, tag, text):
        self.log_seq += 1
        self.log_lines.append({"n": self.log_seq, "t": ts, "tag": tag, "text": text})

    def on_Commander(self, ev, ts):
        self.commander = ev.get("Name", self.commander)

    def on_LoadGame(self, ev, ts):
        # a new game session: reset the session log and totals
        self.commander = ev.get("Commander", self.commander)
        raw_ship = ev.get("Ship") or ""
        on_foot = bool(ONFOOT_SHIP.match(raw_ship))
        if not on_foot:   # on foot, "Ship" is the suit: keep the last ship we knew
            self.ship = {"type": ship_name(raw_ship, ev.get("Ship_Localised")),
                         "name": ev.get("ShipName", ""), "ident": ev.get("ShipIdent", "")}
        self.credits = ev.get("Credits")
        mode = ev.get("GameMode", "")
        self.mode = f"Group: {ev['Group']}" if mode == "Group" and ev.get("Group") else mode
        self.session = self._new_session(ts)
        self.log_lines.clear()
        where = "On foot" if on_foot else self.ship["type"]
        self.log(ts, "LOGIN", " · ".join(x for x in (where, self.mode) if x))

    def on_Loadout(self, ev, ts):
        self.ship = {"type": ship_name(ev.get("Ship")), "name": ev.get("ShipName", ""), "ident": ev.get("ShipIdent", "")}
        jr = ev.get("MaxJumpRange")
        self.jump_range = round(float(jr), 2) if isinstance(jr, (int, float)) and jr > 0 else None

    def on_Rank(self, ev, ts):
        self.ranks = {k: v for k, v in ev.items() if k not in ("timestamp", "event")}

    def on_Progress(self, ev, ts):
        self.progress = {k: v for k, v in ev.items() if k not in ("timestamp", "event")}

    def on_Promotion(self, ev, ts):
        for k, v in ev.items():
            if k in ("timestamp", "event"):
                continue
            self.ranks[k] = v
            table = {"Combat": COMBAT_RANKS, "Federation": FED_RANKS, "Empire": EMP_RANKS}.get(k)
            self.log(ts, "PROMO", f"{k}: {rank_name(table, v) if table else v}")

    def on_Reputation(self, ev, ts):
        self.rep = {k: ev[k] for k in ("Federation", "Empire", "Alliance", "Independent") if k in ev}

    def on_Statistics(self, ev, ts):
        c = ev.get("Combat") or {}
        self.stats = {"bounties": c.get("Bounties_Claimed"), "bounty_profit": c.get("Bounty_Hunting_Profit"),
                      "assassinations": c.get("Assassinations"), "highest": c.get("Highest_Single_Reward")}

    def on_Powerplay(self, ev, ts):
        self.power = {"power": ev.get("Power", ""), "rank": ev.get("Rank")}

    def on_PowerplayJoin(self, ev, ts):
        self.power = {"power": ev.get("Power", ""), "rank": None}

    def on_PowerplayDefect(self, ev, ts):
        self.power = {"power": ev.get("ToPower", ""), "rank": None}

    def on_PowerplayLeave(self, ev, ts):
        self.power = {}

    def on_FSDJump(self, ev, ts):
        self.session["jumps"] += 1
        dist = ev.get("JumpDist")
        system = ev.get("StarSystem", self.board.place.system)
        self.log(ts, "JUMP", system + (f" · {dist:.1f} ly" if isinstance(dist, (int, float)) else ""))

    def on_CarrierJump(self, ev, ts):
        self.log(ts, "JUMP", f"{ev.get('StarSystem', self.board.place.system)} · carrier")

    def on_Docked(self, ev, ts):
        self.log(ts, "DOCK", ev.get("StationName", ""))

    def on_Undocked(self, ev, ts):
        self.log(ts, "UNDOCK", ev.get("StationName", self.board.place.docked))

    def on_Bounty(self, ev, ts):
        reward = ev.get("TotalReward") or ev.get("Reward") or 0
        self.session["kills"] += 1
        self.session["bounty"] += reward
        bits = [clean(ev.get("PilotName_Localised")), ship_name(ev.get("Target"), ev.get("Target_Localised")),
                clean(ev.get("VictimFaction_Localised") or ev.get("VictimFaction"))]
        self.log(ts, "KILL", " · ".join(b for b in bits if b) + f" · +{money(reward)}")

    def on_FactionKillBond(self, ev, ts):
        reward = ev.get("Reward") or 0
        self.session["kills"] += 1
        victim = clean(ev.get("VictimFaction_Localised") or ev.get("VictimFaction"))
        self.log(ts, "BOND", f"{victim} · +{money(reward)}")

    def on_RedeemVoucher(self, ev, ts):
        amount = ev.get("Amount") or 0
        self.session["earned"] += amount
        kind_name = pretty(ev.get("Type")) or "Voucher"
        self.log(ts, "CASH", f"{kind_name[:1].upper()}{kind_name[1:]} vouchers · +{money(amount)}")

    def on_Interdicted(self, ev, ts):
        who = clean(ev.get("Interdictor_Localised") or ev.get("Interdictor")) or "unknown"
        self.log(ts, "INTRDCT", f"by {who}" + (" · submitted" if ev.get("Submitted") else ""))

    def on_EscapeInterdiction(self, ev, ts):
        who = clean(ev.get("Interdictor_Localised") or ev.get("Interdictor")) or "unknown"
        self.log(ts, "ESCAPE", f"from {who}")

    def on_Died(self, ev, ts):
        killers = ev.get("Killers") or []
        who = clean(ev.get("KillerName_Localised") or ev.get("KillerName")) or \
            ", ".join(clean(k.get("Name")) for k in killers if k.get("Name"))
        self.log(ts, "DIED", f"killed by {who}" if who else "ship destroyed")

    def on_CommitCrime(self, ev, ts):
        cost = ev.get("Fine") or ev.get("Bounty")
        self.log(ts, "CRIME", pretty(ev.get("CrimeType")) + (f" · {money(cost)}" if cost else ""))

    def view(self):
        rep = [{"who": who, "value": self.rep[who]} for who in ("Federation", "Empire", "Alliance") if who in self.rep]
        return {
            "name": self.commander,
            "ship": self.ship["type"], "ship_name": self.ship["name"], "ship_ident": self.ship["ident"],
            "mode": self.mode, "credits": self.credits,
            "combat": rank_name(COMBAT_RANKS, self.ranks.get("Combat")),
            "combat_pct": self.progress.get("Combat"),
            "fed": rank_name(FED_RANKS, self.ranks.get("Federation")),
            "emp": rank_name(EMP_RANKS, self.ranks.get("Empire")),
            "rep": rep, "stats": dict(self.stats), "power": dict(self.power),
            "session": dict(self.session),
        }


class Place:
    """Where you are: the system and its position, the body you're near, the station you're
    docked at, and the local situation (factions, conflicts) from the last Location / FSDJump."""

    def __init__(self, board):
        self.board = board
        self.system = ""
        self.address = None         # current SystemAddress
        self.star_pos = None        # [x, y, z] of the current system, light years (from the journal)
        self.body = ""
        self.docked = ""
        self.sit = {}
        self.seen_pos = {}          # system name -> (x, y, z) not yet filed in the coordinates cache
        self.addresses = {}         # system name (lower case) -> its 64-bit address (Spansh looks systems up by it)

    def take_seen(self):
        """The positions seen since last asked (for the coordinates cache)."""
        with self.board.lock:
            seen, self.seen_pos = self.seen_pos, {}
            return seen

    def _note_address(self, name, address):
        if name and isinstance(address, int) and not isinstance(address, bool) and address > 0:
            self.addresses[str(name).lower()] = address

    def address_of(self, system):
        with self.board.lock:
            return self.addresses.get(str(system or "").lower())

    def on_StartJump(self, ev, ts):   # where you're jumping to (Spansh is asked about it on the way)
        self._note_address(ev.get("StarSystem"), ev.get("SystemAddress"))

    def on_FSDTarget(self, ev, ts):
        self._note_address(ev.get("Name"), ev.get("SystemAddress"))

    def _arrive(self, ev, kind):
        self.system = ev.get("StarSystem", self.system)
        self.address = ev.get("SystemAddress", self.address)
        self._note_address(ev.get("StarSystem"), ev.get("SystemAddress"))
        pos = ev.get("StarPos")
        if isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos):
            self.star_pos = [float(v) for v in pos]
            if self.system:
                self.seen_pos[self.system] = tuple(self.star_pos)
        else:
            self.star_pos = None
        self.body = ev.get("Body", "") if kind == "Location" and ev.get("BodyType") == "Planet" else ""
        self.sit = situation(ev)

    def on_Location(self, ev, ts):
        self._arrive(ev, "Location")
        self.docked = ev.get("StationName", "") if ev.get("Docked") else ""

    def on_FSDJump(self, ev, ts):
        self._arrive(ev, "FSDJump")
        self.docked = ""

    def on_CarrierJump(self, ev, ts):
        self._arrive(ev, "CarrierJump")
        self.docked = ev.get("StationName", "") if ev.get("Docked") else self.docked

    def on_Docked(self, ev, ts):
        self.docked = ev.get("StationName", "")

    def on_Undocked(self, ev, ts):
        self.docked = ""

    def on_Embark(self, ev, ts):
        self.body = ev.get("Body") or self.body

    on_Disembark = on_ApproachBody = on_Touchdown = on_Embark

    def on_LeaveBody(self, ev, ts):
        self.body = ""


class DockHeading:
    """Docking on an Odyssey settlement's pad: the pad from DockingGranted, then (once Status.json shows
    you docked) your ship's heading, which gives the settlement's heading (see heading_from_docking).
    Only live: a docking read back at start-up counts if you're still sitting on that pad."""

    def __init__(self, board):
        self.board = board
        self.pads = {}              # MarketID -> the pad you were given
        self.pending = None         # docked, waiting for Status.json's heading

    def on_DockingGranted(self, ev, ts):
        mid, pad = ev.get("MarketID"), ev.get("LandingPad")
        if isinstance(mid, int) and isinstance(pad, int) and not isinstance(pad, bool):
            self.pads[mid] = pad

    def on_DockingCancelled(self, ev, ts):
        self.pads.pop(ev.get("MarketID"), None)

    on_DockingTimeout = on_DockingCancelled

    def on_Docked(self, ev, ts):
        mid = ev.get("MarketID")
        pad = self.pads.pop(mid, None)
        self.pending = None
        if pad is None or not isinstance(mid, int) or str(ev.get("StationType") or "").lower() != "onfootsettlement":
            return
        self.pending = {"key": f"m:{mid}", "pad": pad, "t": parse_time(ts),
                        "system": str(ev.get("StarSystem") or self.board.place.system or "")[:200],
                        "name": clean(ev.get("StationName_Localised") or ev.get("StationName"))[:200]}

    def on_Location(self, ev, ts):   # still docked there (a game loaded on the pad)?
        if self.pending and not (ev.get("Docked") and f"m:{ev.get('MarketID')}" == self.pending["key"]):
            self.pending = None

    def on_Undocked(self, ev, ts):
        self.pending = None

    def on_FSDJump(self, ev, ts):   # gone from there: any pad you were given goes too
        self.pending = None
        self.pads.clear()

    on_CarrierJump = on_Died = on_SupercruiseEntry = on_FSDJump

    def take(self):
        """The docking, once Status.json (newer than it) shows you docked with a heading. Under the board's lock."""
        p, st = self.pending, self.board.status or {}
        if not p or not self.board.live:
            return None
        hdg, t = st.get("Heading"), parse_time(st.get("timestamp", ""))
        try:
            older = t is None or (p["t"] is not None and t < p["t"])   # Status.json from before you docked
        except TypeError:
            older = False
        if older or not int(st.get("Flags") or 0) & F_DOCKED or not isinstance(hdg, (int, float)) \
                or isinstance(hdg, bool) or not math.isfinite(hdg):
            return None
        self.pending = None
        return dict(p, ship=float(hdg) % 360)

    def save(self, dock):
        """Files the docking and the heading it gives (outside the board's lock: it writes the file)."""
        layouts, plans = self.board.settlements, self.board.schematics
        if not dock or not layouts:
            return None
        if layouts.save_docking(dock["key"], dock["pad"], dock["ship"], dock["system"], dock["name"]):
            return heading_from_docking(layouts, plans, dock["key"])
        return None


# 2 Nav > HSI's exobiology rings. A species takes three samples with the genetic sampler, each clear of the others by its
# genus's colony range (metres). Found by a word in the genus's name - the game's own ($Codex_Ent_Bacterial_Genus_Name;)
# first, then as shown (Bacterium) - in this order (Tubus before the legacy Sinuous Tubers' "tube").
EXOBIO_RANGES = (("aleoid", 150), ("bacteri", 500), ("cactoid", 300), ("clypeus", 150), ("concha", 150),
                 ("electricae", 1000), ("fonticul", 500), ("shrub", 150), ("frutexa", 150), ("fumerol", 100),
                 ("fungoid", 300), ("osseus", 800), ("recepta", 150), ("stratum", 500), ("tubus", 800),
                 ("tussock", 200),
                 ("vents", 100), ("amphora", 100), ("sphere", 100), ("anemone", 100), ("cone", 100), ("bark", 100),
                 ("seed", 100), ("brancae", 100), ("brain", 100), ("ground_struct_ice", 100), ("shard", 100),
                 ("tube", 100), ("tuber", 100))
EXOBIO_SAMPLES = 3        # samples to a species: Log (the first), Sample (the second and third), then Analyse when it's done
EXOBIO_FILE = DATA_DIR / "exobio.json"   # the species you're sampling and where each sample was taken (a restart keeps them)


def exobio_range(genus, shown=""):
    """A genus's colony range in metres (None: not known) - from its name in the journal or as shown."""
    for name in (genus, shown):
        low = str(name or "").lower()
        for word, metres in EXOBIO_RANGES:
            if word in low:
                return metres
    return None


class Exobio:
    """The species you're sampling with the genetic sampler (ScanOrganic: Log is the first sample, Sample the second and
    third, Analyse once it's done), where you took each one - Status.json's position at the time - and its genus's colony
    range: 2 Nav > HSI rings each sample with it, and says how far you are from the nearest. Live events only (one read
    back at start-up has no position); kept in exobio.json, so a restart in the middle keeps the rings. Logging a
    different species starts again, as the game does (it drops the one you were on); dying loses it."""

    def __init__(self, board, path=None):
        self.board, self.path = board, path
        self.cur = None    # {"system", "body", "genus", "species", "range", "n": samples taken, "samples": [{"n", "lat", "lon", "t"}]}
        self.last = None   # the species analysed last: {"system", "body", "species", "t"}
        try:
            saved = json.loads(path.read_text(encoding="utf-8")) if path else {}
            saved = saved if isinstance(saved, dict) else {}
            self.cur = saved.get("cur") if isinstance(saved.get("cur"), dict) else None
            self.last = saved.get("last") if isinstance(saved.get("last"), dict) else None
            if self.cur and not isinstance(self.cur.get("samples"), list):
                self.cur = None
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log(f"Exobiology file unreadable ({exc}); starting afresh.")

    def _save(self):   # (under the board's lock: a few hundred bytes)
        if not self.path:
            return
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"cur": self.cur, "last": self.last}), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log(f"Couldn't save the exobiology samples ({exc}).")

    def on_ScanOrganic(self, ev, ts):
        if not self.board.fresh(ts):
            return
        kind = str(ev.get("ScanType") or "")
        species = clean(ev.get("Species_Localised") or ev.get("Species"))[:120]
        genus = clean(ev.get("Genus_Localised") or ev.get("Genus"))[:80]
        st = self.board.status or {}
        body = clean(st.get("BodyName") or self.board.place.body)[:200]
        system = clean(self.board.place.system)[:200]
        if kind == "Analyse":
            if self.cur and self.cur.get("species") == species:
                self.cur = None
            self.last = {"system": system, "body": body, "species": species, "t": ts}
            self.board.log(ts, "EXO", f"{species} analysed")
            self._save()
            return
        if kind not in ("Log", "Sample") or not species:
            return
        c = self.cur
        if kind == "Log" or not c or c.get("species") != species or str(c.get("body") or "").lower() != body.lower():
            c = self.cur = {"system": system, "body": body, "genus": genus, "species": species,
                            "range": exobio_range(ev.get("Genus"), ev.get("Genus_Localised")),
                            "n": 1 if kind == "Log" else 2, "samples": []}   # (a Sample first: the Log was before we were watching)
        else:
            c["n"] = min(EXOBIO_SAMPLES, int(c.get("n") or 0) + 1)
        lat, lon = st.get("Latitude"), st.get("Longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and not isinstance(lat, bool) \
                and str(st.get("BodyName") or "").lower() == body.lower():
            c["samples"].append({"n": c["n"], "lat": round(float(lat), 6), "lon": round(float(lon), 6), "t": ts})
        self.board.log(ts, "EXO", f"{species}: sample {c['n']} of {EXOBIO_SAMPLES}"
                       + (f" (colony range {c['range']} m)" if c.get("range") else ""))
        self._save()

    def on_Died(self, ev, ts):   # the samples go with you
        if self.cur and self.board.fresh(ts):
            self.cur = None
            self._save()

    def view(self):
        return {"cur": dict(self.cur, need=EXOBIO_SAMPLES, samples=list(self.cur.get("samples") or [])) if self.cur else None,
                "last": dict(self.last) if self.last else None}


class ChatCodes:
    """Codes heard in the game's chat (ReceiveText: from your wing, a friend, the system...): waypoint and flight plan codes
    and Atk's plan codes, for 2 Nav > Wpt's CODE to LOAD with a press. Live only, the newest SHARE_HEARD, this run only."""

    def __init__(self, board):
        self.board, self.heard, self.n = board, [], 0

    def on_ReceiveText(self, ev, ts):
        if not self.board.fresh(ts) or str(ev.get("Channel") or "").lower() == "npc":
            return
        who = clean(ev.get("From_Localised") or ev.get("From"))[:60]
        for code, got in find_share_codes(ev.get("Message")):
            self.n += 1
            self.heard = [h for h in self.heard if h["code"].upper() != code.upper()]   # (said again: the newest)
            self.heard.append({"id": self.n, "code": code, "kind": got["kind"], "body": got.get("body", ""), "pts": len(got.get("pts") or []),
                               "from": who, "channel": clean(ev.get("Channel"))[:20], "t": ts})
            self.heard = self.heard[-SHARE_HEARD:]
            what = {"wpt": "a waypoint", "plan": "a flight plan", "atk": "an attack plan"}[got["kind"]]
            self.board.log(ts, "CODE", f"{who or 'Someone'} sent {what} code (Nav > Wpt > Code)")

    def view(self):
        return [dict(h) for h in reversed(self.heard)]   # (the newest first)


class Contracts:
    """Every mission you hold (Contracts > Active), the ship scans of your targets, and their backstories."""

    def __init__(self, board, cache_file: Path):
        self.board = board
        self.missions = {}          # MissionID -> mission dict
        self.scans = {}             # target key -> latest ship scan of that target
        self.cache_file = cache_file
        self.backstories = self._load_cache()
        # for the subject files: what the journal's said lately about each faction and system (Location / FSDJump), the
        # kills of each faction (Bounty: a batch's units still at large), the targets whose first full scan came in
        self.factions = {}          # faction name (lower case) -> {"name", "gov", "alleg", "inf", "system", "states", "conflict"}
        self.systems = {}           # system name (lower case) -> "Medium security, Patronage, Empire"
        self.kills = {}             # faction name (lower case) -> times of the kills (Bounty's VictimFaction), the newest 500
        self.rescans = []           # target keys: a full scan came in (BackstoryWriter.rescan)

    # ---- backstory cache ----
    def _load_cache(self):
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return {k: v for k, v in data.items() if v.get("status") == "done"}
        except (OSError, ValueError):
            return {}

    def _save_cache(self):
        done = {k: {x: y for x, y in v.items() if x != "rescan"} for k, v in self.backstories.items() if v.get("status") == "done"}
        tmp = self.cache_file.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(done, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.cache_file)
        except OSError as exc:
            log(f"Couldn't save backstory cache: {exc}")

    def set_backstory(self, key, name, status, text="", error=""):
        with self.board.lock:
            entry = {"name": name, "status": status, "updated": now_utc().isoformat(timespec="seconds")}
            if text:
                entry["text"] = text
            if error:
                entry["error"] = error
            self.backstories[key] = entry
            if status == "done":
                self._save_cache()

    def set_dossier(self, key, name, fields, job):
        """A subject file written (DOSSIER_FORMAT): the AI's fields and the board's facts it was written from. True if
        the target's first full scan has come in since (so it's written again from that)."""
        with self.board.lock:
            self.backstories[key] = {"name": name, "status": "done", "updated": now_utc().isoformat(timespec="seconds"),
                                     "fmt": DOSSIER_FORMAT, "kind": job["kind"], "mode": job["mode"], "file": dict(fields),
                                     "number": job["number"], "incept": job["incept"], "threat": job["threat"],
                                     "scan": job["scan"], "scanned": job["ship_known"]}
            self._save_cache()
            return not job["ship_known"] and self._full_scan(key)

    def update_dossier(self, key, fields, job):
        """Its behavioural notes and assessment, written again from the target's first full scan."""
        with self.board.lock:
            e = self.backstories.get(key)
            if not e or e.get("fmt") != DOSSIER_FORMAT:
                return
            e["file"] = dict(e.get("file") or {}, **fields)
            e.update(scanned=True, threat=job["threat"], scan=job["scan"], updated=now_utc().isoformat(timespec="seconds"))
            e.pop("rescan", None)
            self._save_cache()

    def set_rescan(self, key, state):
        """A subject file's rewrite from the scan: "queued", "writing" - or None, done with (or given up)."""
        with self.board.lock:
            e = self.backstories.get(key)
            if not e:
                return False
            if state:
                e["rescan"] = state
            else:
                e.pop("rescan", None)
            return True

    def needs_rescan(self, key):
        """A subject file written before the target's first full scan, in ship, that's since come in."""
        with self.board.lock:
            e = self.backstories.get(key) or {}
            return (e.get("fmt") == DOSSIER_FORMAT and e.get("status") == "done" and e.get("mode") == "ship"
                    and e.get("kind") == "person" and not e.get("scanned") and not e.get("rescan") and self._full_scan(key))

    def _full_scan(self, key):
        return (self.scans.get(key) or {}).get("stage", 0) >= 3

    def take_rescans(self):
        with self.board.lock:
            out, self.rescans = self.rescans, []
            return out

    # ---- journal events ----
    def on_MissionAccepted(self, ev, ts):
        self.board.log(ts, "ACCEPT", clean(ev.get("LocalisedName") or ev.get("Name")))
        return self._accept(ev)

    def on_MissionCompleted(self, ev, ts):
        m = self.missions.pop(ev.get("MissionID"), None)
        title = (m or {}).get("title") or clean(ev.get("LocalisedName") or ev.get("Name"))
        reward = ev.get("Reward") or 0
        self.board.cmdr.session["earned"] += reward
        self.board.log(ts, "DONE", title + (f" · +{money(reward)}" if reward else ""))

    def on_MissionAbandoned(self, ev, ts):
        m = self.missions.pop(ev.get("MissionID"), None)
        self.board.log(ts, "ABANDON", (m or {}).get("title") or clean(ev.get("LocalisedName") or ev.get("Name")))

    def on_MissionFailed(self, ev, ts):
        m = self.missions.pop(ev.get("MissionID"), None)
        self.board.log(ts, "FAILED", (m or {}).get("title") or clean(ev.get("LocalisedName") or ev.get("Name")))

    def on_MissionRedirected(self, ev, ts):
        m = self.missions.get(ev.get("MissionID"))
        if m:
            m["status"] = "redirected"
            m["return_system"] = ev.get("NewDestinationSystem", "")
            m["return_station"] = ev.get("NewDestinationStation", "")
            where = m["return_station"] or m["return_system"]
            if m["kind"] == "contract":
                self.board.log(ts, "READY", f"{m['cat']}: {m['target']} · hand in at {where}")
            else:
                self.board.log(ts, "TARGET", f"{m['target']} done · hand in at {where}")

    def on_CargoDepot(self, ev, ts):
        m = self.missions.get(ev.get("MissionID"))
        if m:
            m["depot"] = {"collected": ev.get("ItemsCollected"), "delivered": ev.get("ItemsDelivered"),
                          "total": ev.get("TotalItemsToDeliver")}

    def on_Missions(self, ev, ts):
        # Sent at login: the authoritative list of missions still active, and of those
        # whose objective is done (waiting to be handed in).
        active = {x.get("MissionID"): x for x in ev.get("Active", []) if x.get("MissionID") is not None}
        complete = {x.get("MissionID"): x for x in ev.get("Complete", []) if x.get("MissionID") is not None}
        for mid in list(self.missions):
            if mid not in active and mid not in complete:
                del self.missions[mid]
        for mid, x in complete.items():
            if mid not in self.missions:
                self._from_login_list(x, ts)
            self.missions[mid]["status"] = "redirected"
        for mid, x in active.items():
            if mid not in self.missions:
                self._from_login_list(x, ts)

    def on_ShipTargeted(self, ev, ts):
        if ev.get("TargetLocked"):
            self._scan(ev)

    def _arrive(self, ev):   # (Location, FSDJump, CarrierJump) what each faction there is, and the system
        system = clean(ev.get("StarSystem"))
        if not system:
            return
        sec = clean(ev.get("SystemSecurity_Localised") or ev.get("SystemSecurity")).replace("$", "")
        bits = [sec[:1].upper() + sec[1:].lower() if sec else "", clean(ev.get("SystemGovernment_Localised")), clean(ev.get("SystemAllegiance"))]
        self.systems[system.lower()] = ", ".join(b for b in bits if b and b.lower() != "none")
        wars = {}
        for c in ev.get("Conflicts") or []:
            a, b = c.get("Faction1") or {}, c.get("Faction2") or {}
            kind = {"war": "war", "civilwar": "civil war", "election": "election"}.get(str(c.get("WarType") or "").lower(), "conflict")
            for us, them in ((a, b), (b, a)):
                if us.get("Name"):
                    wars[us["Name"].lower()] = (kind, them.get("Name", ""), us.get("WonDays", 0), them.get("WonDays", 0), us["Name"])
        for f in ev.get("Factions") or []:
            name = clean(f.get("Name"))
            if not name:
                continue
            self.factions[name.lower()] = {
                "name": name, "gov": clean(f.get("Government")), "alleg": clean(f.get("Allegiance")),
                "inf": round(float(f.get("Influence") or 0) * 100), "system": system,
                "states": [pretty(x.get("State")) for x in (f.get("ActiveStates") or []) if pretty(x.get("State"))],
                "conflict": wars.get(name.lower()),
            }

    def on_Location(self, ev, ts):
        self._arrive(ev)

    on_FSDJump = on_CarrierJump = on_Location

    def on_ApproachSettlement(self, ev, ts):   # an on-foot target's settlement reached: LOCATED
        name = clean(ev.get("Name_Localised") or ev.get("Name")).casefold()
        for m in self.missions.values():
            if name and m.get("settlement") and m["settlement"].casefold() == name and not m.get("located"):
                m["located"] = ts

    def on_Bounty(self, ev, ts):   # a kill: one of a batch's units, if it's of the faction a massacre is against
        who = clean(ev.get("VictimFaction_Localised") or ev.get("VictimFaction")).lower()
        if who:
            k = self.kills.setdefault(who, [])
            k.append(ts)
            del k[:-500]

    def _accept(self, ev):
        """Every mission goes on Contracts' Active page. Hunts - assassinations (a named target) and massacres
        (a kill count) - are grouped by target and get a backstory; returns those."""
        m, is_target = mission_record(ev)
        m["issued_in"], m["issued_at"] = self.board.place.system, self.board.place.docked   # (where you took it)
        self.missions[m["id"]] = m
        return dict(m) if is_target else None

    def _from_login_list(self, x, ts):
        """A mission the game lists at login that the journals read don't cover (accepted before them):
        all that's known is its kind and when it expires."""
        t, secs = parse_time(ts), x.get("Expires")
        expiry = ""
        if t is not None and isinstance(secs, (int, float)) and secs > 0:   # 0: not given (done ones can show it)
            expiry = datetime.fromtimestamp(t.timestamp() + secs, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        kind = mission_kind(x.get("Name"))
        self.missions[x["MissionID"]] = {
            "id": x["MissionID"], "key": f"m:{x['MissionID']}", "target": f"{kind} contract", "kind": "contract", "cat": kind,
            "target_type": "", "target_faction": "", "issuer": "", "title": "", "system": "", "station": "", "settlement": "",
            "expiry": expiry, "reward": 0, "kill_count": None, "wing": False, "accepted": "", "status": "active",
            "commodity": "", "count": None, "passengers": None, "donation": None, "influence": "", "reputation": "",
            "depot": None, "partial": True, "contact": "",
        }

    def _scan(self, ev):
        pilot = clean(ev.get("PilotName_Localised") or ev.get("PilotName"))
        if not pilot:
            return
        key = target_key(pilot)
        if not any(m["key"] == key for m in self.missions.values()):
            return  # only remember scans of your mission targets
        prev = self.scans.get(key, {})
        stage = ev.get("ScanStage") if isinstance(ev.get("ScanStage"), int) else 0
        if stage == 3:
            self.board.log(ev.get("timestamp", ""), "SCAN", f"{pilot} · {ship_name(ev.get('Ship'), ev.get('Ship_Localised'))}")
            if prev.get("stage", 0) < 3:
                self.rescans.append(key)   # (the first full scan: its subject file's notes and assessment are written again)
        subs = list(prev.get("subs") or [])
        sub = clean(ev.get("Subsystem_Localised") or "")
        if sub and sub not in subs:
            subs = (subs + [sub])[-6:]
        self.scans[key] = {
            "time": ev.get("timestamp", ""),
            "first": prev.get("first") or ev.get("timestamp", ""),   # (LOCATED from then)
            "stage": max(stage, prev.get("stage", 0)),
            "ship": ship_name(ev.get("Ship"), ev.get("Ship_Localised")) or prev.get("ship", ""),
            "ship_id": str(ev.get("Ship") or prev.get("ship_id") or "").lower(),
            "hull": ev.get("HullHealth", prev.get("hull")),
            "shields": ev.get("ShieldHealth", prev.get("shields")),
            "legal": ev.get("LegalStatus", prev.get("legal", "")),
            "bounty": ev.get("Bounty", prev.get("bounty")),
            "rank": ev.get("PilotRank", prev.get("rank", "")),
            "subs": subs,
        }

    # ---- views ----
    def active(self):
        """Missions not yet expired."""
        now = now_utc()
        with self.board.lock:
            return [dict(m) for m in self.missions.values()
                    if not (parse_time(m.get("expiry")) and parse_time(m["expiry"]) < now)]

    def for_backstory(self, key):
        """A target mission (for a backstory) by its target key."""
        return next((m for m in self.active() if m["key"] == key and m["kind"] != "contract"), None)

    # ---- the subject files (under the board's lock) ----
    def _faction_text(self, name, influence=True):
        """'Brask Free Company (Anarchy, Independent; 1% influence in Brask)' - as much as the journal's said."""
        f = self.factions.get(str(name or "").lower())
        if not f:
            return name
        bits = ", ".join(x for x in (f["gov"], f["alleg"]) if x)
        if influence and f.get("inf") is not None and f.get("system"):
            bits += ("; " if bits else "") + f"{f['inf']}% influence in {f['system']}"
        return f"{name} ({bits})" if bits else name

    def _situation(self, name):
        """A faction's states and war: 'civil war with X (Y ahead, 2 days to 1); Boom' - or ''."""
        f = self.factions.get(str(name or "").lower())
        if not f:
            return ""
        out = []
        c = f.get("conflict")
        if c:
            kind, other, us, them, me = c
            lead = (f"{me} ahead" if us > them else f"{other} ahead" if them > us else "level")
            out.append(f"{kind} with {other} ({lead}, {max(us, them)} days to {min(us, them)})" if us != them else f"{kind} with {other} (level, {us} days each)")
        out += [x for x in f.get("states") or [] if x.lower().replace(" ", "") not in ("civilwar", "war", "election")]
        return "; ".join(out)

    def _group(self, key):
        return [m for m in self.active() if m["key"] == key and m["kind"] != "contract"]

    def _file(self, key, ms):
        """The board's part of a target's subject file: kind, mode, serial number, incept date, status, threat,
        units (a batch), affiliation and contract - from the journal, the same every time it's asked."""
        m0 = ms[0]
        kind = "batch" if m0["kind"] == "faction" else "person"
        mode = "foot" if any(str(m.get("cat") or "").startswith("On foot") for m in ms) else "ship"
        live = [m for m in ms if m.get("status") != "redirected"]
        first = min((m.get("accepted") or "9999") for m in ms)
        number, incept, t0 = dossier_ids(key, first if first != "9999" else "")
        e = self.backstories.get(key) or {}
        if e.get("fmt") == DOSSIER_FORMAT:   # (as written: it's what the file says)
            number, incept_text = e.get("number") or number, e.get("incept") or game_date(incept)
        else:
            incept_text = game_date(incept)
        out = {"kind": kind, "mode": mode, "number": number, "incept": incept_text, "incept_d": incept, "t0": t0}
        scan = self.scans.get(key) if kind == "person" else None
        located = None
        if kind == "person":
            located = (scan or {}).get("first") or min((m.get("located") for m in ms if m.get("located")), default=None)
            out["status"] = ("LOCATED" if located else "AT LARGE") if live else "RETIRED"
        else:   # a batch: its units - the most any one issuer wants killed (kills count for each issuer at once) - less the kills since
            per = {}
            for m in live:
                per[m.get("issuer") or ""] = per.get(m.get("issuer") or "", 0) + int(m.get("kill_count") or 0)
            need = max(per.values()) if per else 0
            since = min((m.get("accepted") or "") for m in live) if live else ""
            kills = sum(1 for t in self.kills.get(str(m0.get("target_faction") or m0["target"]).lower(), []) if since and t >= since)
            out["units"] = {"need": need, "left": max(0, need - kills)} if need else None
            out["status"] = "AT LARGE" if live else "RETIRED"
        out["located"] = located
        reward = sum(float(m.get("reward") or 0) for m in (live or ms))
        level, basis = threat_of(mode, kind, reward, any(m.get("wing") for m in ms), scan=scan, hard=any(m.get("hard") for m in ms),
                                 units=(out.get("units") or {}).get("need"))
        out["threat"] = f"{THREAT_LEVELS[level]} ({basis})"
        fac = m0.get("target_faction") or (m0["target"] if kind == "batch" else "")
        out["affiliation"] = self._faction_text(fac, influence=False) if fac else ""
        issuers = []
        for m in ms:
            if m.get("issuer") and m["issuer"] not in issuers:
                issuers.append(m["issuer"])
        out["contract"] = mission_verb(m0) + (f", for {issuers[0]}" + (f" +{len(issuers) - 1}" if len(issuers) > 1 else "") if issuers else "")
        return out

    def file_view(self, key):
        """A target's subject file as Contracts' Active panel shows it: the board's facts, and the serial with the
        AI's letters (sex and grades) once it's written."""
        ms = self._group(key) if key else []
        if not ms:
            return None
        f = self._file(key, ms)
        e = self.backstories.get(key) or {}
        fields = (e.get("file") or {}) if e.get("fmt") == DOSSIER_FORMAT else {}
        if f["kind"] == "person":
            letters = (fields.get("sex", "") + fields.get("physical_grade", "") + fields.get("mental_grade", "")) or "---"
            serial = f"{DOSSIER_LINE}{letters}{f['number']}"
        else:
            n = (f.get("units") or {}).get("need") or 0
            serial = f"{DOSSIER_LINE} batch {f['number']}" + (f"-{(int(f['number']) + n - 1) % 100000:05d}" if n > 1 else "")
        out = {k: v for k, v in f.items() if k not in ("incept_d", "t0")}
        out["serial"] = serial
        return out

    def dossier_job(self, key, rescan=False):
        """What the AI is given to write a target's subject file - its facts from the journal (only what's known) -
        and what's kept with it; None if it's no longer an active target."""
        with self.board.lock:
            ms = self._group(key)
            if not ms:
                return None
            f = self._file(key, ms)
            m0, kind, mode = ms[0], f["kind"], f["mode"]
            scan = self.scans.get(key) if kind == "person" and mode == "ship" else None
            full = bool(scan) and scan.get("stage", 0) >= 3
            lines = [f"MODE: {'ON FOOT' if mode == 'foot' else 'IN SHIP'}",
                     "FILE: PERSON" if kind == "person" else f"FILE: BATCH ({(f.get('units') or {}).get('need') or 'several'} units)",
                     f"DATE: {game_date(now_utc())}", f"TARGET: {m0['target']}"]
            if m0.get("target_type"):
                lines.append(f"ROLE: {m0['target_type']}")
            fac = m0.get("target_faction") or (m0["target"] if kind == "batch" else "")
            if fac:
                lines.append(f"TARGET FACTION: {self._faction_text(fac)}")
            titles = []
            for m in ms:
                if m.get("title") and m["title"] not in titles:
                    titles.append(m["title"])
            if titles:
                lines.append("CONTRACT: " + "; ".join(titles))
            seen = set()
            for m in ms:
                iss = m.get("issuer")
                if not iss or iss in seen:
                    continue
                seen.add(iss)
                where = ", ".join(x for x in (m.get("issued_at"), m.get("issued_in")) if x)
                lines.append(f"ISSUED BY: {self._faction_text(iss, influence=False)}" + (f" at {where}" if where else ""))
                sit = self._situation(iss)
                if sit:
                    lines.append(f"ISSUER'S SITUATION: {sit}")
            places = []
            for m in ms:
                p = ", ".join(x for x in (m.get("settlement"), m.get("station"), m.get("system")) if x)
                info = self.systems.get(str(m.get("system") or "").lower())
                p = p + (f" ({info})" if p and info else "")
                if p and p not in places:
                    places.append(p)
            if places:
                lines.append("LAST KNOWN WHEREABOUTS: " + "; ".join(places))
            reward = sum(float(m.get("reward") or 0) for m in ms)
            if reward:
                lines.append(f"REWARD: {int(reward):,} CR")
            lines.append(f"WING CONTRACT: {'yes' if any(m.get('wing') for m in ms) else 'no'}")
            lines.append(f"INCEPT DATE: {f['incept']} ({'the batch, ' if kind == 'batch' else ''}{dossier_age(f['incept_d'], now_utc())}; a four-year lifespan)")
            if kind == "batch" and f.get("units"):
                lines.append(f"UNITS STILL AT LARGE: {f['units']['left']} of {f['units']['need']}")
            summary = ""
            if kind == "person" and mode == "ship":
                if scan and scan.get("ship"):
                    bits = [scan.get("ship"), scan.get("rank"), pretty(scan.get("legal")) if scan.get("legal") not in (None, "", "None") else "",
                            f"local bounty {int(scan['bounty']):,} CR" if isinstance(scan.get("bounty"), (int, float)) and scan["bounty"] else "",
                            f"shields {round(scan['shields'])}%" if isinstance(scan.get("shields"), (int, float)) else "",
                            f"hull {round(scan['hull'])}%" if isinstance(scan.get("hull"), (int, float)) else ""] + list(scan.get("subs") or [])
                    summary = ", ".join(b for b in bits if b)
                    lines.append(f"SHIP SCAN: {summary}" + ("" if full else " (partial)"))
                else:
                    lines.append("SHIP SCAN: none yet")
            if kind == "person" and mode == "foot" and f.get("located"):
                lines.append(f"SETTLEMENT REACHED: {_jtime(f['located'])}")
            lines.append(f"THREAT: {f['threat']}")
            if rescan:
                e = self.backstories.get(key) or {}
                done = e.get("file") or {}
                lines += ["", "WRITTEN SO FAR", f"BACKGROUND: {done.get('background', '')}", f"IMPLANTED MEMORY: {done.get('implanted_memory', '')}"]
            return {"key": key, "name": m0["target"], "kind": kind, "mode": mode, "facts": "\n".join(lines),
                    "ship_known": bool(scan and scan.get("ship")), "number": f["number"], "incept": f["incept"],
                    "threat": f["threat"], "scan": " · ".join(x for x in ((scan or {}).get("ship"), (scan or {}).get("rank")) if x)}

    def view(self):
        """Contracts' Active entries, soonest to expire first: target missions grouped by target,
        every other mission on its own."""
        with self.board.lock:
            groups = {}
            for m in self.active():
                g = groups.setdefault(m["key"], {
                    "key": m["key"], "name": m["target"], "kind": m["kind"],
                    "type": m["target_type"], "faction": m["target_faction"], "missions": [],
                })
                g["missions"].append(m)
            contracts = []
            for key, g in groups.items():
                g["missions"].sort(key=lambda x: x.get("expiry") or "")
                target = g["kind"] != "contract"
                g["scan"] = dict(self.scans[key]) if target and key in self.scans else None
                g["backstory"] = dict(self.backstories[key]) if target and key in self.backstories else None
                g["file"] = self.file_view(key) if target else None
                contracts.append(g)
            contracts.sort(key=lambda g: g["missions"][0].get("expiry") or "9999")
            return contracts

    def keys(self):
        """Contract keys in the same order as the index on the page."""
        return [g["key"] for g in self.view()]


class Vehicles:
    """Where you are aboard - ship, SRV, Nomad, fighter, on foot or a taxi - and the change the page
    plays (disconnect / start-up). Loading a save waits until you're actually in game.

    Also whether you're in the game at all - the page's "input signal". Loading a save gives it
    (once you're really in, as above); the main menu (the journal's Music event plays MainMenu),
    closing the game (Shutdown) or starting it again (a new journal's first Fileheader) take it away."""

    def __init__(self, board):
        self.board = board
        self.vehicle = ""           # ship / srv / nomad / fighter / foot / taxi ("" = not known yet)
        self.label = ""             # the vehicle's name for its boot screen (SRV type, fighter loadout...)
        self.ingame = False         # in the game, rather than at the main menu or with it closed
        self.srv_type, self.fighter_loadout = "", ""
        self.deployed = ""          # srv or nomad: what's out on the surface (both write Embark/Disembark with SRV: true)
        # the last change of vehicle, for the page's effect: from/to are ship, srv, fighter, foot or ""
        self.boot = {"id": "", "from": "", "to": "", "label": "", "time": ""}
        self.boot_wait = None       # loading in: waiting for Status.json to show you in game

    def view(self):
        """For the page: whether there's a signal (you're in the game), and where you are."""
        return {"in": self.ingame, "vehicle": self.vehicle or "ship", "label": self.label}

    def _switch(self, ts, frm, to, label="", only_if_changed=False):
        """You moved from one vehicle to another (or on foot). Live, recent changes
        are passed to the page, which plays the disconnect / start-up effect."""
        if only_if_changed and self.vehicle == to:
            return
        self.vehicle, self.label, self.ingame = to, label, True
        self.boot_wait = None   # anything still waiting from loading in is overtaken by this
        if not self.board.fresh(ts):
            return
        self.boot = {"id": f"{ts}|{frm}>{to}", "from": frm, "to": to, "label": label, "time": ts}

    def _switch_after_load(self, ts, to, label=""):
        """Loading a save. The journal's LoadGame comes while the loading screen is still up, so you
        count as in game (and a live load's start-up plays) once Status.json - rewritten since then -
        shows you in a ship, SRV, fighter, on foot (or in a taxi or multicrew), or BOOT_WAIT_SECONDS
        after the load. See boot_check."""
        self.vehicle, self.label, self.ingame, self.boot_wait = to, label, False, None
        since, live = parse_time(ts), self.board.fresh(ts)
        if since is None:   # can't tell when: take it you're in
            self.ingame = True
            return
        # a load read back at start-up has had its time already, unless it's very recent
        until = time.time() + BOOT_WAIT_SECONDS if live else since.timestamp() + BOOT_WAIT_SECONDS
        self.boot_wait = {"since": since, "to": to, "label": label, "until": until, "play": live}

    def _signal_lost(self):
        self.ingame, self.boot_wait = False, None

    def boot_check(self):
        """Loading in: once you're in game, the page gets its signal - and a live load's start-up.
        Returns True when that happens."""
        with self.board.lock:
            w = self.boot_wait
            if not w:
                return False
            st = self.board.status or {}
            f, f2, at = int(st.get("Flags") or 0), int(st.get("Flags2") or 0), parse_time(st.get("timestamp"))
            in_game = at is not None and at >= w["since"] and bool(
                f & (F_IN_SHIP | F_IN_FIGHTER | F_SRV) or f2 & (F2_ON_FOOT | F2_IN_TAXI | F2_IN_MULTICREW))
            if not in_game and time.time() < w["until"]:
                return False
            self.boot_wait, self.ingame = None, True
            if w["play"]:
                ts = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
                self.boot = {"id": f"{ts}|>{w['to']}", "from": "", "to": w["to"], "label": w["label"], "time": ts}
                if not in_game:
                    log(f"Start-up: Status.json didn't show you in game within {BOOT_WAIT_SECONDS} s, so playing it anyway.")
            return True

    # ---- journal events ----
    def on_Fileheader(self, ev, ts):
        if str(ev.get("part", 1)) == "1":   # the game has just started (a later part carries on the same session)
            self._signal_lost()

    def on_Music(self, ev, ts):
        if ev.get("MusicTrack") in ("MainMenu", "CQCMenu"):   # back at the main menu
            self._signal_lost()

    def on_Shutdown(self, ev, ts):   # the game closed
        self._signal_lost()

    @staticmethod
    def _srv_name(ev):
        return ev.get("SRVType_Localised") or SRV_NAMES.get(str(ev.get("SRVType", "")).lower(), "SRV")

    def on_LoadGame(self, ev, ts):
        # loading in: no disconnect, just the start-up for wherever you are, once you're in game
        raw_ship = ev.get("Ship") or ""
        if ONFOOT_SHIP.match(raw_ship):
            self._switch_after_load(ts, "foot")
        elif raw_ship and NOMAD_TYPE.search(raw_ship):
            self.deployed = "nomad"
            self._switch_after_load(ts, "nomad", ev.get("Ship_Localised") or "Nomad")
        elif raw_ship and SRV_SHIP.match(raw_ship):
            self._switch_after_load(ts, "srv", ev.get("Ship_Localised") or SRV_NAMES.get(raw_ship.lower(), "SRV"))
        elif raw_ship and FIGHTER_SHIP.search(raw_ship):
            self._switch_after_load(ts, "fighter", ev.get("Ship_Localised") or "")
        elif raw_ship:
            self._switch_after_load(ts, "ship")

    def on_Embark(self, ev, ts):
        # on foot into a vehicle (an Apex taxi or another player's ship plays nothing)
        if ev.get("Taxi") or ev.get("Multicrew"):
            self.vehicle = "taxi"
        elif ev.get("SRV") and self.deployed == "nomad":   # the Nomad also says "SRV"
            self._switch(ts, "", "nomad", "Nomad")
        elif ev.get("SRV"):
            self._switch(ts, "", "srv", self.srv_type or "SRV")
        else:
            self._switch(ts, "", "ship")

    def on_Disembark(self, ev, ts):
        # out of a ship or SRV, on foot
        if ev.get("Taxi") or ev.get("Multicrew"):
            self.vehicle = "foot"
        elif ev.get("SRV"):
            self._switch(ts, "nomad" if self.deployed == "nomad" else "srv", "foot")
        else:
            self._switch(ts, "ship", "foot")

    def _launch_nomad(self, ev, ts):
        self.deployed = "nomad"
        if ev.get("PlayerControlled") is not False:
            self._switch(ts, "ship", "nomad", ev.get("VesselType_Localised") or "Nomad")

    def on_LaunchVessel(self, ev, ts):   # the Nomad (launched from a vessel hangar)
        self._launch_nomad(ev, ts)

    def on_LaunchSRV(self, ev, ts):
        if NOMAD_TYPE.search(str(ev.get("SRVType", ""))):
            self._launch_nomad(ev, ts)
            return
        self.srv_type = self._srv_name(ev)
        self.deployed = "srv"
        if ev.get("PlayerControlled") is not False:
            self._switch(ts, "ship", "srv", self.srv_type)

    def on_DockSRV(self, ev, ts):
        nomad = ev.get("event") == "DockVessel" or NOMAD_TYPE.search(str(ev.get("SRVType", ""))) or self.deployed == "nomad"
        if not nomad:
            self.srv_type = self._srv_name(ev)
        self.deployed = ""
        if self.vehicle in ("srv", "nomad", ""):   # you were driving / flying it back aboard
            self._switch(ts, "nomad" if nomad else "srv", "ship")

    on_DockVessel = on_DockSRV

    def on_SRVDestroyed(self, ev, ts):
        self.deployed = ""

    def on_LaunchFighter(self, ev, ts):
        self.fighter_loadout = str(ev.get("Loadout") or "").replace("_", " ").title()
        if ev.get("PlayerControlled"):
            self._switch(ts, "ship", "fighter", self.fighter_loadout)

    def on_VehicleSwitch(self, ev, ts):
        if ev.get("To") == "Fighter":
            self._switch(ts, "ship", "fighter", self.fighter_loadout, only_if_changed=True)
        elif ev.get("To") == "Mothership":
            self._switch(ts, "fighter", "ship", only_if_changed=True)

    def on_DockFighter(self, ev, ts):
        if self.vehicle == "fighter":   # you were flying it: back to the ship
            self._switch(ts, "fighter", "ship")

    on_FighterDestroyed = on_DockFighter


class Jumps:
    """Hyperspace jumps, for the overlay: the jump under way (StartJump until FSDJump), the two
    stars, the route plotted in the galaxy map, the drive and the fuel the jump should take."""

    def __init__(self, board):
        self.board = board
        self.jump = None            # the jump under way: StartJump until FSDJump (live events only)
        self.survey = None          # Spansh's (or EDSM's) answer for the system being jumped to
        self.survey_off = False     # no online lookups (--no-spansh and --no-edsm)
        self.survey_src = "Spansh"  # where the survey comes from (the page names it)
        self.star_scans = {}        # system (lower case) -> its arrival star from the journal's automatic scan
        self.star_classes = {}      # system (lower case) -> star class seen in StartJump / FSDTarget / the route
        self.navroute = []          # the plotted route (NavRoute.json)
        self.fsd_target = {}
        self.fsd, self.unladen, self.fuel_cap, self.cargo_t, self.booster = None, None, None, 0.0, False
        self.fuel_k = {}            # FSD -> fuel constants measured from your recent jumps

    def set_route(self, route):
        """NavRoute.json changed: the stops' positions also go to the coordinates cache."""
        with self.board.lock:
            self.navroute = route
            for r in route:
                if r["system"] and r["pos"]:
                    self.board.place.seen_pos[r["system"]] = tuple(r["pos"])
                if r["system"] and r["cls"]:
                    self.star_classes[r["system"].lower()] = r["cls"]

    # ---- journal events ----
    def on_Loadout(self, ev, ts):
        fc = ev.get("FuelCapacity") or {}
        if fc:
            self.fuel_cap = {"Main": fc.get("Main"), "Reserve": fc.get("Reserve")}
        self.unladen = ev.get("UnladenMass") or self.unladen
        self.fsd = fsd_from_loadout(ev) or self.fsd
        self.booster = any("guardianfsdbooster" in str(m.get("Item", "")).lower() for m in ev.get("Modules") or [])

    def on_StartJump(self, ev, ts):
        if ev.get("JumpType") != "Hyperspace":
            return
        if ev.get("StarSystem") and ev.get("StarClass"):
            self.star_classes[ev["StarSystem"].lower()] = ev["StarClass"]
        if self.board.fresh(ts):
            self._start_jump(ev, ts)

    def on_FSDTarget(self, ev, ts):
        self.fsd_target = {"system": ev.get("Name", ""), "cls": ev.get("StarClass", ""), "left": ev.get("RemainingJumpsInRoute")}
        if ev.get("Name") and ev.get("StarClass"):
            self.star_classes[ev["Name"].lower()] = ev["StarClass"]

    def on_NavRouteClear(self, ev, ts):
        self.navroute = []

    def on_Cargo(self, ev, ts):
        if ev.get("Vessel", "Ship") == "Ship" and isinstance(ev.get("Count"), (int, float)):
            self.cargo_t = float(ev["Count"])

    def on_Scan(self, ev, ts):
        if ev.get("StarType") and (ev.get("DistanceFromArrivalLS") or 0) < 1:   # the arrival star's automatic scan
            where = ev.get("StarSystem") or self.board.place.system
            if where:
                self.star_scans[where.lower()] = star_from_scan(ev)
                while len(self.star_scans) > 400:
                    self.star_scans.pop(next(iter(self.star_scans)))

    def on_FSDJump(self, ev, ts):
        self._fuel_sample(ev)
        if self.jump and not self.jump.get("arrived"):   # out of hyperspace: the overlay plays its arrival
            self.jump.update(arrived=ts, fuel_used=ev.get("FuelUsed"), fuel_level=ev.get("FuelLevel"),
                             ly=round(ev["JumpDist"], 2) if isinstance(ev.get("JumpDist"), (int, float)) else self.jump.get("ly"))

    # ---- fuel ----
    def _fuel_estimate(self, dist, fuel, cargo):
        f = self.fsd
        if not f or not dist or not self.unladen or not isinstance(fuel, (int, float)):
            return None, ""
        mass = self.unladen + fuel + (cargo or 0)
        measured = self.fuel_k.get(f["key"])
        if measured:   # your own drive, from your recent jumps
            return round(statistics.median(measured) * (dist * mass) ** f["pow"], 2), "measured"
        if f["opt"] and not f["sco"] and not self.booster:
            return round(f["lin"] * 0.001 * (dist * mass / f["opt"]) ** f["pow"], 2), "drive tables"
        return None, ""

    def _fuel_sample(self, ev):
        """Measure the drive from a finished jump (skipped for boosted jumps)."""
        used, level, dist = ev.get("FuelUsed"), ev.get("FuelLevel"), ev.get("JumpDist")
        if not self.fsd or not self.unladen or ev.get("BoostUsed") or not all(isinstance(v, (int, float)) for v in (used, level, dist)):
            return
        if used <= 0 or dist <= 0:
            return
        mass = self.unladen + level + used + (self.cargo_t or 0)
        self.fuel_k.setdefault(self.fsd["key"], deque(maxlen=12)).append(used / (dist * mass) ** self.fsd["pow"])

    def _start_jump(self, ev, ts):
        to = ev.get("StarSystem", "")
        place = self.board.place
        here = place.system
        dep = self.star_scans.get(here.lower()) or self.board.systab.main_star(here) or \
            (star_placeholder(self.star_classes[here.lower()]) if here.lower() in self.star_classes else None)
        dest = next((r for r in self.navroute if r["system"].lower() == to.lower()), None)
        ly = math.dist(place.star_pos, dest["pos"]) if place.star_pos and dest and dest.get("pos") else None
        st = self.board.status or {}
        fuel = (st.get("Fuel") or {}).get("FuelMain")
        cargo = st.get("Cargo") if isinstance(st.get("Cargo"), (int, float)) else self.cargo_t
        est, how = (None, "") if ev.get("Taxi") else self._fuel_estimate(ly, fuel, cargo)
        names = [r["system"].lower() for r in self.navroute]
        left = len(names) - 1 - names.index(to.lower()) if to.lower() in names else self.fsd_target.get("left")
        self.jump = {"id": f"{ts}|{to}", "started": ts, "arrived": None, "from": here, "to": to,
                     "to_class": ev.get("StarClass", ""), "dep_star": dep, "ly": round(ly, 2) if ly else None,
                     "taxi": bool(ev.get("Taxi")), "fuel_before": fuel, "fuel_cap": (self.fuel_cap or {}).get("Main"),
                     "fuel_est": est, "fuel_how": how, "fuel_used": None, "fuel_level": None,
                     "route_left": left if isinstance(left, int) else None}
        log(f"Hyperspace: {here} -> {to} ({ev.get('StarClass', '?')} star)" + (f", about {est:.2f} t of fuel" if est else "") + ".")

    # ---- the survey of where you're going (Spansh, or EDSM) ----
    def target(self):
        """(jump id, destination) while a jump is under way, for the survey ahead of arrival."""
        with self.board.lock:
            j = self.jump
            return (j["id"], j["to"]) if j and not j.get("arrived") and j.get("to") and self._under_way(j) else None

    def _under_way(self, j):
        """A jump not yet arrived is still going unless it has been given up on (JUMP_GIVE_UP) or
        cancelled: 25 s after it started, the drive is neither charging nor jumping."""
        started = parse_time(j["started"])
        if started is None:
            return False
        age = (now_utc() - started).total_seconds()
        if age > JUMP_GIVE_UP:
            return False
        return age <= 25 or bool(int((self.board.status or {}).get("Flags") or 0) & (F_FSD_JUMP | F_FSD_CHARGING))

    def set_survey(self, system, status, map_=None, star=None, bodies=0, stations=0, carriers=0, error="", src="Spansh"):
        with self.board.lock:
            self.survey = {"system": system, "status": status, "map": map_, "star": star, "src": src,
                           "bodies": bodies, "stations": stations, "carriers": carriers, "error": error}

    def view(self):
        j = self.jump
        if not j:
            return None
        status = self.board.status or {}
        now = now_utc()
        if j.get("arrived"):
            at = parse_time(j["arrived"])
            if at is None or (now - at).total_seconds() > 15:
                return None
        elif not self._under_way(j):
            return None   # given up on, or cancelled
        v = dict(j)
        sv = self.survey if self.survey and str(self.survey.get("system", "")).lower() == j["to"].lower() else None
        v["survey"] = {k: sv.get(k) for k in ("status", "map", "bodies", "stations", "carriers", "src")} if sv else \
            {"status": "off" if self.survey_off else "waiting", "src": self.survey_src}
        v["to_star"] = self.star_scans.get(j["to"].lower()) or (sv or {}).get("star") or star_placeholder(j["to_class"])
        if not v.get("dep_star"):
            v["dep_star"] = star_placeholder("")
        v["fuel_now"] = (status.get("Fuel") or {}).get("FuelMain")
        v["now"] = now.isoformat(timespec="milliseconds")
        return v


class SystemTab:
    """Tab 4: the system you're in, from EDSM (filled in by EdsmFetcher), with your live position
    from Status.json and what AUTO shows."""

    def __init__(self, board):
        self.board = board
        self.model, self.index = None, {}
        self.status, self.system, self.error = "waiting", "", ""
        self.fetcher = None   # EdsmFetcher (it sets this)
        self.uplink = {"busy": False, "pressed": 0.0, "done": 0.0, "result": None, "error": ""}   # the last press

    def request_uplink(self):
        """System Data Uplink Synchronise pressed (on a page or the UFC): (HTTP status, answer)."""
        if not self.fetcher:
            return 409, {"ok": False, "why": "offline"}
        return self.fetcher.request_uplink()

    def toggle_source(self, name):
        """Spansh Uplink / EDSM Uplink pressed (on a page or the UFC): flips it. The new state, or None."""
        ups = getattr(self.board, "uplinks", None)
        if not ups or name not in ("spansh", "edsm"):
            return None
        ups.set(name, not getattr(ups, name))
        return ups.view()

    def _uplink_view(self):
        """The button's state for the page: in progress, just done (and how), how long until it can be
        pressed again, or off (both toggles off); and the two toggles."""
        u, now = self.uplink, time.time()
        ups = getattr(self.board, "uplinks", None)
        return {"busy": u["busy"], "result": u["result"], "error": u["error"],
                "since": round(now - u["done"], 1) if u["done"] else None,
                "wait": max(0, int(UPLINK_EVERY - (now - u["pressed"]) + 0.999)) if u["pressed"] else 0,
                "off": bool(self.fetcher is None or self.fetcher.offline),
                "spansh": bool(ups.spansh) if ups else True, "edsm": bool(ups.edsm) if ups else True}

    def set(self, system, model=None, index=None, status="ok", error=""):
        with self.board.lock:
            if model is not None or status in ("loading", "off", "waiting") or \
                    (self.model and self.model.get("system") != system):   # never show one system's data under another
                self.model, self.index = model, index or {}
            self.status, self.system, self.error = status, system, error

    def keys(self, map_view=False):
        """The System tab's bodies and stations in list order (your targets among them), or (map view) what the
        map shows, in map order."""
        with self.board.lock:
            m = self.model or {}
            if map_view and (m.get("map") or {}).get("order"):
                return list(m["map"]["order"])
            return [e["key"] for e in self._with_targets(m)[0]]

    def _with_targets(self, m):
        """The model's entries with your targets (2 Nav > Wpt) among them - each under its body, after the body's
        stations, and on its body's picture - and the targets themselves: (entries, targets)."""
        store = getattr(self.board, "settlements", None)
        tg = store.targets_for(m.get("system")) if store and m.get("entries") else []
        entries = m.get("entries", [])
        if not tg:
            return entries, []
        system = m.get("system") or ""
        by_body = {}
        for t in tg:
            by_body.setdefault(t["body"].lower(), []).append(t)

        def row(t, depth):
            made = time.strftime("%d %b %Y %H:%M", time.localtime(t["saved"]))
            return {"key": t["key"], "kind": "tgt", "depth": depth, "icon": "tgt", "label": t["name"], "src": "you", "right": "",
                    "lab": f"Your waypoint · {_short_name(t['body'], system)} surface", "name": t["name"], "chips": [{"t": "Your waypoint"}],
                    "rows": [["Position", f"{t['lat']:.4f}, {t['lon']:.4f}", True],
                             ["Made", f"{TARGET_METHODS.get(t['method'], 'Manual')} · {made}", True]],
                    "pic": {"kind": "surface", "body": t["body"], "lat": t["lat"], "lon": t["lon"]}, "surface": True, "body": t["body"],
                    "tgt": {"id": t["id"], "num": t["num"], "method": t["method"]}}
        out, i, n, placed = [], 0, len(entries), set()
        while i < n:
            e = entries[i]
            i += 1
            mine = by_body.get(str(e.get("name") or "").lower()) if e.get("kind") == "planet" else None
            if not mine:
                out.append(e)
                continue
            out.append(dict(e, pic=dict(e.get("pic") or {}, tgts=[{"name": t["name"], "lat": t["lat"], "lon": t["lon"], "key": t["key"]} for t in mine])))
            while i < n and entries[i].get("kind") == "station" and str(entries[i].get("body") or "").lower() == e["name"].lower():
                out.append(entries[i])
                i += 1
            out.extend(row(t, e.get("depth", 0) + 1) for t in mine)
            placed.add(e["name"].lower())
        out.extend(row(t, 0) for t in tg if t["body"].lower() not in placed)   # (a body the data no longer lists)
        return out, tg

    def host(self, key):
        """The planet a surface site is on (the map shows the planet, not the site)."""
        with self.board.lock:
            return (((self.model or {}).get("map") or {}).get("hosts") or {}).get(key)

    def main_star(self, system):
        """The main star of the system this tab has (from Spansh, or EDSM), if it's this one."""
        m = self.model or {}
        if str(m.get("system", "")).lower() != str(system).lower():
            return None
        b = next((x for x in (m.get("map") or {}).get("bodies", []) if x.get("main")), None)
        if not b:
            return None
        return {"sub": b.get("sub") or "Star", "cls": b.get("cls") or "", "lum": b.get("lum") or "", "rsol": b.get("rsol"),
                "mass": b.get("mass"), "temp": b.get("temp"), "rot": b.get("rot"), "tilt": b.get("tilt"),
                "source": m.get("source") if m.get("source") in ("spansh", "edsm") else "edsm"}

    def view(self):
        here = self.board.viewed_system()   # (the system you're in - or the remote one picked: REMOTE)
        remote = here != self.board.place.system
        view = {"status": self.status, "system": self.system or here, "error": self.error, "uplinking": self._uplink_view(),
                "from": self.fetcher.source() if self.fetcher else "Spansh",   # where bodies and stations come from
                "remote": self.board.remote_view()}
        moved = bool(self.system and self.system != here)
        if self.model is None or moved:
            if moved and self.status != "off":
                view["status"], view["system"] = "loading", here   # just jumped: the fetch is on its way
            return view
        view.update(self.model)
        view["entries"], view["tgts"] = self._with_targets(self.model)   # your targets (2 Nav > Wpt) among them
        view["nav"] = self.board.nav.view(self.model.get("system") or "", view["tgts"], self.model.get("entries", []))   # marks, SEQs, TGT...
        layouts = getattr(self.board, "settlements", None)   # the layouts you've confirmed for this system's settlements
        skeys = [e["settlement"]["key"] for e in self.model.get("entries", []) if e.get("settlement")]
        view["layouts"] = layouts.for_keys(skeys) if layouts else {}
        view["types"] = layouts.types_for(skeys) if layouts else {}   # schematic types you've picked
        view["headings"] = layouts.headings_for(skeys) if layouts else {}   # which way each faces (Align Settlement, dockings)
        view["pad"] = None if remote else self._granted_pad(view["layouts"], view["headings"])   # the pad docking was granted on (Traj's final approach)
        view["status"] = self.status if self.status != "ok" or self.model.get("entries") else "empty"
        if self.status == "error" and self.model.get("entries"):
            view["status"] = "stale"   # showing the last good fetch
        view.update(self._remote_live() if remote else self._live())
        return view

    def _remote_live(self):
        """_live's, for a remote system: you're not there - no position, nothing near, not docked, no HUD target; AUTO
        shows its main star (its first entry)."""
        m = self.model or {}
        first = (m.get("entries") or [{}])[0].get("key")
        return {"me": None, "near": {}, "docked": None, "auto": {"key": first, "why": "remote"} if first else None, "target": None,
                "target_body": None, "target_name": "", "live": (self.board.status or {}).get("timestamp", "")}

    def _granted_pad(self, layouts, headings):
        """The pad docking's been granted on at a settlement: {"key", "num"}, and - when the settlement's layout is
        confirmed and its heading known for that layout - where the pad is, in metres east ("e") and north ("n") of
        the settlement's position. None if no docking's been granted. (The layout plans put the settlement's
        position at 0,0 with its heading up the plan, y down.)"""
        pads = getattr(self.board.dock_heading, "pads", None) or {}
        if not pads:
            return None
        mid, num = list(pads.items())[-1]
        out = {"key": f"m:{mid}", "num": num}
        layout, hd, plans = layouts.get(out["key"]), headings.get(out["key"]), self.board.schematics
        if not layout or not hd or hd.get("layout") != layout or not plans:
            return out
        plan = plans.plan(layout)
        pad = next((p for p in (plan or {}).get("pads", []) if p.get("num") == num), None) if (plan or {}).get("metric") else None
        if not pad or not pad.get("outline"):
            return out
        x = sum(q[0] for q in pad["outline"]) / len(pad["outline"])
        up = -sum(q[1] for q in pad["outline"]) / len(pad["outline"])
        a = math.radians(hd.get("h") or 0)
        out.update(e=round(x * math.cos(a) + up * math.sin(a), 1), n=round(-x * math.sin(a) + up * math.cos(a), 1))
        return out

    def _live(self):
        """Where you are relative to the system's bodies and stations, and what Auto shows:
        docked → that station; on or low over a planet → the nearest surface site (or the
        planet when higher up); otherwise your current target; otherwise the main star."""
        st, idx, m = self.board.status or {}, self.index, self.model
        dockedname = self.board.place.docked
        names = idx.get("names", {})
        f, f2 = int(st.get("Flags") or 0), int(st.get("Flags2") or 0)
        me, near, auto = None, {}, None
        if f & F_LATLONG and st.get("BodyName") and st.get("Latitude") is not None:
            me = {"body": st["BodyName"], "lat": st["Latitude"], "lon": st.get("Longitude", 0), "alt": st.get("Altitude")}
            if isinstance(st.get("Heading"), (int, float)) and not isinstance(st.get("Heading"), bool):
                me["hdg"] = st["Heading"]   # the way you face (Align Settlement turns the schematic to it)
            if isinstance(st.get("PlanetRadius"), (int, float)) and st["PlanetRadius"] > 0:
                me["r"] = st["PlanetRadius"]   # metres
            if self.board.status_t:   # when the game wrote it, and how long ago that was now (Traj places the sample by it)
                me["t"], me["age"] = round(self.board.status_t, 3), round(max(0.0, time.time() - self.board.status_t), 3)
            me["avg"] = bool(f & F_ALT_AVERAGE)   # altitude from the average radius (high up), else from the ground below
            me["glide"] = bool(f2 & F2_GLIDE)
            me["sc"] = bool(f & F_SUPERCRUISE)
            me["landed"] = bool(f & F_LANDED)
            body_key = names.get(str(st["BodyName"]).lower())
            if body_key:
                me["key"] = body_key
                radius = (st.get("PlanetRadius") or 0) / 1000 or idx.get("radii", {}).get(body_key) or 0
                for key, lat, lon in idx.get("sites", {}).get(body_key, []):
                    if radius and lat is not None:
                        km, brg = _gc_km(me["lat"], me["lon"], lat, lon, radius)
                        near[key] = [round(km), round(brg)]
        docked = names.get(dockedname.lower()) if dockedname else None
        if docked:
            auto = {"key": docked, "why": "docked"}
        elif me and me.get("key"):
            low = (f2 & (F2_GLIDE | F2_ON_FOOT | F2_ON_PLANET) or f & (F_LANDED | F_SRV)
                   or (me["alt"] is not None and me["alt"] < NEAR_ALTITUDE))
            if low and near:
                key = min(near, key=lambda k: near[k][0])
                auto = {"key": key, "why": "nearest", "km": near[key][0], "brg": near[key][1]}
            else:
                auto = {"key": me["key"], "why": "planet"}
        else:
            dest = st.get("Destination") or {}
            if dest.get("Name") and (not m.get("id64") or dest.get("System") in (None, m.get("id64"))):
                key = names.get(str(dest["Name"]).lower())
                if key:
                    auto = {"key": key, "why": "target"}
        if auto is None and m.get("entries"):
            auto = {"key": m["entries"][0]["key"], "why": "arrival"}
        target = None   # what you've targeted in the game (the HUD), if it's in this system's list: Traj's HUD Tgt
        target_body = None   # ... and the body it is, or is on (a mission's crash site, say): Tgt's HUD TGT
        dest = st.get("Destination") or {}
        if dest and (not m.get("id64") or dest.get("System") in (None, m.get("id64"))):
            for nm in (dest.get("Name_Localised"), dest.get("Name")):
                if nm and names.get(str(nm).lower()):
                    target = names[str(nm).lower()]
                    break
            bid = dest.get("Body")
            if isinstance(bid, int) and not isinstance(bid, bool):
                target_body = next((e["key"] for e in m.get("entries", []) if e.get("bodyId") == bid and e.get("kind") in ("planet", "star")), None)
        target_name = str(dest.get("Name_Localised") or dest.get("Name") or "").replace("&NBSP;", " ").replace("&nbsp;", " ")[:120]
        return {"me": me, "near": near, "docked": docked, "auto": auto, "target": target, "target_body": target_body,
                "target_name": target_name, "live": st.get("timestamp", "")}


# --------------------------------------------------------------------------- #
# 2 Nav: your waypoint system, as an F/A-18C's - marks, flight plans, the steer-to point, the designated target, the attack plan
# --------------------------------------------------------------------------- #
MARK_SLOTS = 9            # MK1-MK9, as the Hornet's markpoints: each new mark takes the next slot, round to MK1 after MK9
SEQ_COUNT = 3             # SEQ 1-3: flight plans, each your waypoints in order, all on one body
MARK_METHODS = {"overfly": "Overfly", "desig": "HUD VV", "xb": "HUD X-B"}   # how a mark was made ("desig": HUD VV, once HUD DESIG)
XB_MAX = 10   # HUD X-B: the bearings kept (an 11th: the oldest goes)
MK_PAGE_WAIT = 1.5        # seconds the UFC's MK waits for an open page to mark the point (its filter has you now, not up to 4 s ago)
KTS = 1852 / 3600         # m/s in a knot
ATK_REF_KTS = 480         # the card's speed: the profiles' distances are nautical miles at this speed
# The attack profiles (2 Nav > Atk's PLAN). Each role's points round the target, in nautical miles at ATK_REF_KTS - so at
# the plan's speed they scale, and the times between them stay the card's - along the attack axis (ATK HDG: the heading
# from the IP to the target), before the target + and past it -, and right of the axis +; the height it's flown at
# ("base": BASE; "in" / "off": the role's attack and off-target heights - Base / Base+1, swapped between the two roles, as
# the card's legend has them); and the call made there ({cs}: your callsign; {from}: where you come in from, {to}: where
# you go off to - north, east, south or west).
# 2-ship pop (the card): 480 KTAS from 20 NM, the IP at 10 NM; #2 splits right no later than 8 NM and runs on for 18 s
# (the card's 15-20 s) past #1's track, then turns in to pop from the east; #1 offsets right at 7 NM and pops in from the
# south; both come off left. #2 is over the target about 40 s after #1.
ATK_PROFILES = {
    "pop2": {"name": "2-ship pop", "code": "POP2", "roles": {
        1: (("START", 20.0, 0.0, "base", ""), ("IP", 10.0, 0.0, "base", ""), ("OFFSET", 7.0, 0.0, "base", ""),
            ("IN", 2.7, 1.45, "in", "{cs}, IN {from}"), ("TGT", 0.0, 0.0, "in", ""),
            ("OFF", -1.66, -0.89, "off", "{cs}, OFF {to}"), ("EGRESS", 1.1, -2.65, "off", ""), ("EXIT", 6.0, -2.65, "base", "")),
        2: (("START", 20.0, -1.5, "base", ""), ("SPLIT", 8.0, -1.5, "base", ""), ("TURN", 8.0, 2.4, "base", ""),
            ("JOIN", 6.0, 1.6, "base", ""), ("IN", 0.0, 1.6, "in", "{cs}, IN {from}"), ("TGT", 0.0, 0.0, "in", ""),
            ("OFF", 0.0, -3.1, "off", "{cs}, OFF {to}, VISUAL/BLIND"), ("EXIT", 6.0, -3.1, "base", ""))}},
}
ATK_DEFAULTS = {"hdg": None, "kts": 480, "base": 300, "step": 300, "role": 1, "cs": "WK5", "profile": "pop2"}
ATK_LIMITS = {"kts": (60, 3000), "base": (0, 20000), "step": (0, 5000)}
PLAN_CODE_TAG = "FT1"     # the plan code's first field: which format it is


def _gc_m(lat1, lon1, lat2, lon2, r):
    """Great-circle distance (m) and the initial bearing from point 1 to point 2, on a body of radius r (m)."""
    km, brg = _gc_km(lat1, lon1, lat2, lon2, r / 1000)
    return km * 1000, brg


def _dest_point(lat, lon, brg, dist, r):
    """The point dist metres from (lat, lon) along the bearing brg, on a body of radius r (m)."""
    p1, l1, th, d = math.radians(lat), math.radians(lon), math.radians(brg), dist / r
    p2 = math.asin(max(-1.0, min(1.0, math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(th))))
    l2 = l1 + math.atan2(math.sin(th) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540) % 360 - 180


def cardinal(deg):
    """North, east, south or west: the quarter a heading is in (as the card's calls say it)."""
    return ("NORTH", "EAST", "SOUTH", "WEST")[int(((deg % 360) + 45) // 90) % 4]


def build_attack(tgt, hdg, kts, base, step, profile, cs, radius):
    """An attack plan's points for both roles, from the target, the attack heading (IP to target), the speed (knots),
    BASE and the step to Base+1 (m), the profile and the flight's callsign, on a body of the given radius (m):
    {"roles": {"1": [points], "2": [points]}, "tot": {"1": s, "2": s}} - each point {"id", "lat", "lon", "alt", "h",
    "call", "e", "n" (m east / north of the target), "hdg", "dist", "secs" (the leg on to the next point)}."""
    prof = ATK_PROFILES[profile]
    per = 1852.0 * kts / ATK_REF_KTS   # metres a card nautical mile is at this speed
    speed = kts * KTS
    h = math.radians(hdg)
    roles, tot = {}, {}
    for role, pts in prof["roles"].items():
        alt = {"base": base, "in": base if role == 1 else base + step, "off": base + step if role == 1 else base}
        rows = []
        for pid, a, r, ak, call in pts:
            e = (-a * math.sin(h) + r * math.cos(h)) * per
            n = (-a * math.cos(h) - r * math.sin(h)) * per
            d = math.hypot(e, n)
            lat, lon = (tgt["lat"], tgt["lon"]) if d < 0.5 else _dest_point(tgt["lat"], tgt["lon"], math.degrees(math.atan2(e, n)), d, radius)
            rows.append({"id": pid, "lat": round(lat, 6), "lon": round(lon, 6), "alt": round(alt[ak]), "h": ak, "call": call,
                         "e": round(e, 1), "n": round(n, 1)})
        for i, p in enumerate(rows):   # each leg on: its heading, length and time
            q = rows[i + 1] if i + 1 < len(rows) else None
            if q:
                de, dn = q["e"] - p["e"], q["n"] - p["n"]
                p["hdg"], p["dist"] = round((math.degrees(math.atan2(de, dn)) + 360) % 360, 1), round(math.hypot(de, dn), 1)
                p["secs"] = round(p["dist"] / speed, 1)
        ti = next(i for i, p in enumerate(rows) if p["id"] == "TGT")
        run_in = rows[ti - 1]["hdg"] if ti > 0 else hdg   # the heading over the target, in and off
        off = rows[ti]["hdg"] if ti + 1 < len(rows) else hdg
        for p in rows:
            p["call"] = p["call"].format(cs=f"{cs}{role}", **{"from": cardinal(run_in + 180), "to": cardinal(off)})
        tot[str(role)] = round(sum(p.get("secs", 0) for p in rows[:ti]), 1)
        roles[str(role)] = rows
    return {"roles": roles, "tot": tot}


def plan_code(body, tgt, hdg, kts, base, step, profile, cs, role):
    """The plan as a line of text to share with your wingman (read it out, paste it into chat, or COPY / LOAD):
    FT1/body/lat/lon/hdg/kts/base/step/profile/callsign+role/check. The check is 4 hex digits of a CRC of the rest
    (upper case), so a mistyped code is refused."""
    import zlib
    head = "/".join([PLAN_CODE_TAG, body, f"{tgt['lat']:.5f}", f"{tgt['lon']:.5f}", f"{int(round(hdg)) % 360:03d}", str(int(kts)),
                     str(int(base)), str(int(step)), ATK_PROFILES[profile]["code"], f"{cs}{role}"])
    return f"{head}/{zlib.crc32(head.upper().encode('utf-8')) & 0xFFFF:04X}"


def parse_plan_code(text):
    """A plan code's fields, or (None, why)."""
    import zlib
    parts = [" ".join(p.split()) for p in str(text or "").strip().split("/")]
    if len(parts) != 11 or parts[0].upper() != PLAN_CODE_TAG:
        return None, "not a plan code"
    head, chk = "/".join(parts[:10]), parts[10].upper()
    if f"{zlib.crc32(head.upper().encode('utf-8')) & 0xFFFF:04X}" != chk:
        return None, "check failed - mistyped?"
    try:
        lat, lon, hdg, kts, base, step = float(parts[2]), float(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]), int(parts[7])
    except ValueError:
        return None, "check failed - mistyped?"
    prof = next((k for k, p in ATK_PROFILES.items() if p["code"] == parts[8].upper()), None)
    m = re.fullmatch(r"([A-Z0-9]{1,6})([12])", parts[9].upper())
    inside = all(ATK_LIMITS[k][0] <= v <= ATK_LIMITS[k][1] for k, v in (("kts", kts), ("base", base), ("step", step)))
    if not (prof and m and inside and -90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= hdg < 360):
        return None, "not a plan this board knows"
    return {"body": parts[1], "lat": lat, "lon": lon, "hdg": hdg, "kts": kts, "base": base, "step": step, "profile": prof,
            "cs": m.group(1), "role": int(m.group(2))}, ""


# 2 Nav > Wpt's shared codes: a waypoint (or mark) or a flight plan as a line of text, as Atk's plan code (FT1) - to read
# out, paste into the game's chat, or COPY / LOAD. FTW1/body/lat,lon,name/check (the name's left out where it's the usual
# "WPT n - body": the one loading it numbers it), FTP1/body/lat,lon,name/lat,lon,name/.../check - the check as FT1's.
SHARE_WPT_TAG, SHARE_PLAN_TAG = "FTW1", "FTP1"
SHARE_PLAN_MAX = 20       # points a flight plan code can carry
SHARE_HEARD = 8           # codes heard in the game's chat that are kept (the newest; this run only)


def _share_check(head):
    import zlib
    return f"{zlib.crc32(head.upper().encode('utf-8')) & 0xFFFF:04X}"


def _share_name(name):
    """A name as a code carries it: no slashes or commas (they divide the code), 40 characters at most."""
    return " ".join(str(name or "").replace("/", " ").replace(",", " ").split())[:40]


def _share_point(lat, lon, name=""):
    nm = _share_name(name)
    return f"{lat:.5f},{lon:.5f}" + (f",{nm}" if nm else "")


def waypoint_code(body, lat, lon, name=""):
    """A waypoint (or a mark) as a code: FTW1/body/lat,lon[,name]/check."""
    head = "/".join([SHARE_WPT_TAG, body, _share_point(lat, lon, name)])
    return f"{head}/{_share_check(head)}"


def flight_plan_code(body, pts):
    """A flight plan as a code: FTP1/body/lat,lon[,name]/.../check - pts [(lat, lon, name)], in order (SHARE_PLAN_MAX at
    most). None if there are none, or too many."""
    if not pts or len(pts) > SHARE_PLAN_MAX:
        return None
    head = "/".join([SHARE_PLAN_TAG, body] + [_share_point(*p) for p in pts])
    return f"{head}/{_share_check(head)}"


def parse_share_code(text):
    """A waypoint or flight plan code: ({"kind": "wpt" | "plan", "body", "pts": [{"lat", "lon", "name"}]}, "") - Atk's
    plan code (FT1): ({"kind": "atk"}, ""); else (None, why)."""
    text = str(text or "").strip()
    parts = [" ".join(p.split()) for p in text.split("/")]
    tag = parts[0].upper() if parts else ""
    if tag == PLAN_CODE_TAG:
        got, why = parse_plan_code(text)
        return ({"kind": "atk"}, "") if got else (None, why)
    if tag not in (SHARE_WPT_TAG, SHARE_PLAN_TAG) or len(parts) < 4:
        return None, "not a waypoint or flight plan code"
    head, chk = "/".join(parts[:-1]), parts[-1].upper()
    if _share_check(head) != chk:
        return None, "check failed - mistyped?"
    body, raw = parts[1], parts[2:-1]
    if not body or (tag == SHARE_WPT_TAG and len(raw) != 1) or len(raw) > SHARE_PLAN_MAX:
        return None, "not a code this board knows"
    pts = []
    for r in raw:
        f = r.split(",")
        try:
            lat, lon = float(f[0]), float(f[1])
        except (ValueError, IndexError):
            return None, "not a code this board knows"
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            return None, "not a code this board knows"
        pts.append({"lat": round(lat, 6), "lon": round(lon, 6), "name": _share_name(",".join(f[2:]))})
    return {"kind": "wpt" if tag == SHARE_WPT_TAG else "plan", "body": body, "pts": pts}, ""


_SHARE_START = re.compile(r"\bFT[WP]?1/", re.I)
_SHARE_END = re.compile(r"/[0-9A-Fa-f]{4}(?=$|[\s.,;:!?)\]'\"])")


def find_share_codes(message):
    """The codes in a chat message (FT1, FTW1, FTP1 - each checked), in order: [(code, parsed)]."""
    out, msg = [], str(message or "")[:2000]
    for m in _SHARE_START.finditer(msg):
        for e in _SHARE_END.finditer(msg, m.start()):   # (a body's name has spaces: the code runs to the first check that's right)
            code = msg[m.start():e.end()]
            got, _ = parse_share_code(code)
            if got:
                out.append((code, got))
                break
    return out


def get_clipboard() -> str:
    """The text on this PC's clipboard (Windows); elsewhere what set_clipboard remembered. "" if there's none."""
    if sys.platform != "win32":
        return _CLIP_MEMORY.get("text", "")
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes, user32.OpenClipboard.restype = [wintypes.HWND], wintypes.BOOL
    user32.GetClipboardData.argtypes, user32.GetClipboardData.restype = [wintypes.UINT], wintypes.HANDLE
    kernel32.GlobalLock.argtypes, kernel32.GlobalLock.restype = [wintypes.HGLOBAL], wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    for _ in range(10):   # another program may have it open for a moment
        if user32.OpenClipboard(None):
            break
        time.sleep(0.03)
    else:
        return ""
    try:
        handle = user32.GetClipboardData(13)   # CF_UNICODETEXT
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)[:4000]
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


class NavBoard:
    """2 Nav's waypoint system, after the F/A-18C's: your waypoints (2 Nav > Wpt; SettlementLayouts' targets), MK1-MK9
    marks (a rolling set of quick captures: overfly, HUD VV or HUD X-B), three flight plans (SEQ 1-3: your waypoints in order,
    all on one body) and Atk's attack sequence (ATK), the steer-to point (2 Nav > HSI flies to it; AUTO steps it on along
    the flight plan), one designated target (TGT: a waypoint, its offset aimpoint, a mark, or a surface site from 1 Syst),
    and Atk's attack plan (built round the target, shared as a plan code). Kept per system in settlements.sqlite (its nav
    table) and shown to the page in the System tab's view (syst.nav). Ops come from the page (POST /api/nav) and the UFC
    (MK, through the page or straight from Status.json)."""

    def __init__(self, board):
        self.board = board
        self.lock = threading.Lock()
        # UFC presses already acted on, with what each was answered - every open page answers each press, so each is acted
        # on once, and a page answering it after another is given the same answer (marked "did": "already"): the page
        # menu's MK and DSG (by their count, n), and anything else a page does for a UFC press (its token, u: "c2.<COMM2
        # pull>", "k.<keypad key>"...)
        self.handled = {"mk": OrderedDict(), "dsg": OrderedDict(), "u": OrderedDict()}
        self.tlock = threading.Lock()   # (/api/tgt: one UFC press's waypoint change at a time)

    def answered(self, kind, k):
        """What a UFC press was answered, if a page has acted on it (else None)."""
        with self.lock:
            a = self.handled[kind].get(k)
        return dict(a, did="already") if a is not None else None

    def keep(self, kind, k, answer):
        """A UFC press acted on, and its answer."""
        with self.lock:
            self._keep(kind, k, answer)

    def _keep(self, kind, k, answer):
        d = self.handled[kind]
        d[k] = answer
        d.move_to_end(k)
        while len(d) > 256:
            d.popitem(last=False)

    @staticmethod
    def token(body):
        """A request's UFC press token (u), or None."""
        u = body.get("u")
        return u[:40] if isinstance(u, str) and u else None

    # ---- the record ----
    def _store(self):
        return getattr(self.board, "settlements", None)

    def _where(self):
        """(system, its planets {lower name: entry}, its entries) - the System tab's."""
        with self.board.lock:
            m = self.board.systab.model or {}
            entries = list(m.get("entries") or [])
            return (m.get("system") or "", {str(e.get("name") or "").lower(): e for e in entries if e.get("kind") == "planet"}, entries)

    def _radius(self, body, planets):
        """A body's radius in metres: the game's (Status.json's, while you're at it - what the pages measure with), else
        the system data's."""
        st = self.board.status or {}
        if str(st.get("BodyName") or "").lower() == str(body or "").lower() and isinstance(st.get("PlanetRadius"), (int, float)) \
                and st["PlanetRadius"] > 0:
            return float(st["PlanetRadius"])
        e = planets.get(str(body or "").lower())
        if e and isinstance(e.get("radius"), (int, float)) and e["radius"] > 0:
            return e["radius"] * 1000.0
        return None

    @staticmethod
    def _plan(rec):
        p = dict(ATK_DEFAULTS)
        p.update({k: v for k, v in (rec.get("plan") or {}).items() if k in ATK_DEFAULTS or k == "built"})
        return p

    def _points(self, rec, tgts, planets):
        """Every point the record knows, by key: your waypoints (t12), their offset aimpoints (t12o), marks (mk3) and
        the attack plan's points (atk:1:IP)."""
        out = {}
        for t in tgts:
            out[t["key"]] = {"key": t["key"], "src": "wpt", "name": t["name"], "label": f"WP{t['num']}", "num": t["num"],
                             "body": t["body"], "lat": t["lat"], "lon": t["lon"], "id": t["id"]}
        for tid, o in (rec.get("oaps") or {}).items():
            w = out.get(f"t{tid}")
            if not w or not o.get("rng"):
                continue
            r = self._radius(w["body"], planets)
            if not r:
                continue
            lat, lon = _dest_point(w["lat"], w["lon"], o["brg"], o["rng"], r)
            out[f"t{tid}o"] = {"key": f"t{tid}o", "src": "oap", "name": f"{w['name']} O/S", "label": f"WP{w['num']} O/S", "num": w["num"],
                               "body": w["body"], "lat": round(lat, 6), "lon": round(lon, 6), "rng": o["rng"], "brg": o["brg"]}
        for slot, mk in (rec.get("marks") or {}).items():
            out[f"mk{slot}"] = {"key": f"mk{slot}", "src": "mk", "name": f"MK{slot}", "label": f"MK{slot}", "num": int(slot),
                                "body": mk["body"], "lat": mk["lat"], "lon": mk["lon"]}
        built = self._plan(rec).get("built")
        if built:
            for role, pts in built["roles"].items():
                for p in pts:
                    out[f"atk:{role}:{p['id']}"] = {"key": f"atk:{role}:{p['id']}", "src": "atk", "name": p["id"], "label": p["id"],
                                                    "body": built["tgt"]["body"], "lat": p["lat"], "lon": p["lon"], "alt": p["alt"]}
        return out

    def _seq_keys(self, rec, tgts, seq):
        """A flight plan's points, in order (keys): SEQ 1-3's waypoints that still exist, or ATK's - your role's."""
        if seq == "atk":
            built = self._plan(rec).get("built")
            role = str(self._plan(rec)["role"])
            return [f"atk:{role}:{p['id']}" for p in (built or {}).get("roles", {}).get(role, [])] if built else []
        have = {t["id"] for t in tgts}
        return [f"t{i}" for i in (rec.get("seqs") or {}).get(str(seq), []) if i in have]

    @staticmethod
    def _tots(rec, seqs):
        """Each flight plan's time on target (the Hornet's HSI DATA / WYPT TOT): its TGT - one of its waypoints (key; None:
        none, or not in it now) - the TOT (Zulu, seconds into the day) and GSPD (knots, the IP -> TGT leg)."""
        out = {}
        for i in range(1, SEQ_COUNT + 1):
            t = (rec.get("tots") or {}).get(str(i)) or {}
            key = f"t{t['tgt']}" if t.get("tgt") is not None else None
            out[str(i)] = {"tgt": key if key in seqs.get(str(i), []) else None, "tot": t.get("tot"), "gspd": t.get("gspd")}
        return out

    def view(self, system, tgts, entries):
        """syst.nav: what the page shows of it, for the system the tab has (tgts: its waypoints; entries: its bodies...)."""
        store = self._store()
        rec = store.nav_get(system) if store and system else {}
        planets = {str(e.get("name") or "").lower(): e for e in entries if e.get("kind") == "planet"}
        pts = self._points(rec, tgts, planets)
        marks = sorted(({"key": f"mk{s}", "slot": int(s), "name": f"MK{s}", "body": m["body"], "lat": m["lat"], "lon": m["lon"],
                         "alt": m.get("alt"), "method": m.get("method", "overfly"), "saved": m.get("saved", 0)}
                        for s, m in (rec.get("marks") or {}).items()), key=lambda m: m["slot"])
        last = int(rec.get("last") or 0)
        seqs = {str(i): self._seq_keys(rec, tgts, i) for i in range(1, SEQ_COUNT + 1)}
        plan = self._plan(rec)
        built = plan.pop("built", None)
        seqs["atk"] = self._seq_keys(rec, tgts, "atk")
        seq = rec.get("seq") if rec.get("seq") in seqs else "none"   # (none activated: the HSI steps through all your points)
        steer = rec.get("steer") if rec.get("steer") in pts else None
        tgt = rec.get("tgt")
        if tgt and tgt.get("src") in ("wpt", "oap", "mk"):   # follows its waypoint or mark (gone with it)
            p = pts.get(tgt.get("key"))
            tgt = dict(p, src=tgt["src"]) if p and p["src"] == tgt["src"] else None
        out = {"marks": marks, "next": last % MARK_SLOTS + 1, "seqs": seqs, "seq": seq, "steer": steer, "auto": rec.get("auto", True) is not False,
               "oaps": {k: {"rng": p["rng"], "brg": p["brg"], "lat": p["lat"], "lon": p["lon"]} for k, p in pts.items() if p["src"] == "oap"},
               "tgt": tgt, "plan": plan, "built": None, "tots": self._tots(rec, seqs),
               "xb": {"body": (rec.get("xb") or {}).get("body") or "", "list": list((rec.get("xb") or {}).get("list") or []), "max": XB_MAX},
               "profiles": {k: {"name": p["name"], "ref": ATK_REF_KTS, "roles": {str(r): [list(x) for x in pts] for r, pts in p["roles"].items()}}
                            for k, p in ATK_PROFILES.items()}}   # (Atk draws the plan from them as you set it, before BUILD)
        if built:
            b = dict(built)
            b["code"] = plan_code(b["tgt"]["body"], b["tgt"], b["hdg"], b["kts"], b["base"], b["step"], b["profile"], b["cs"], plan["role"])
            out["built"] = b
        out["codes"] = self._codes(system, tgts, marks, seqs)   # (Wpt's COPY: each waypoint, mark and flight plan as a code)
        out["heard"] = self.board.chat_codes.view() if getattr(self.board, "chat_codes", None) else []   # codes heard in the game's chat
        return out

    @staticmethod
    def _codes(system, tgts, marks, seqs):
        """Each waypoint (t12), mark (mk3) and flight plan ("seq": {"1": code or None...}) as a code to share. A waypoint's
        usual name ("WPT n - body") is left out: the one loading it numbers it."""
        def name(t):
            return "" if t["name"] == f"WPT {t['num']} - {_short_name(t['body'], system)}" else t["name"]
        by = {t["key"]: t for t in tgts}
        out = {t["key"]: waypoint_code(t["body"], t["lat"], t["lon"], name(t)) for t in tgts}
        out.update({m["key"]: waypoint_code(m["body"], m["lat"], m["lon"]) for m in marks})
        plans = {}
        for i in range(1, SEQ_COUNT + 1):
            pts = [by[k] for k in seqs.get(str(i), []) if k in by]
            plans[str(i)] = flight_plan_code(pts[0]["body"], [(t["lat"], t["lon"], name(t)) for t in pts]) if pts else None
        out["seq"] = plans
        return out

    # ---- ops: from the page (POST /api/nav) and the UFC ----
    def op(self, body):
        """(HTTP status, answer) for one op. See the Handler's /api/nav for what each takes."""
        system, planets, entries = self._where()
        store = self._store()
        if not store or not system:
            return 409, {"ok": False, "why": "no system"}
        kind = body.get("op")
        num = (lambda v: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None)
        integer = (lambda v: v if isinstance(v, int) and not isinstance(v, bool) else None)
        n = integer(body.get("n"))
        u = self.token(body)
        with self.lock:
            press = ("mk" if kind == "mark" else "dsg", n) if n is not None and kind in ("mark", "dsg") else ("u", u) if u else None
            if press and press[1] in self.handled[press[0]]:   # another page has acted on this UFC press: what it was answered
                return 200, dict(self.handled[press[0]][press[1]], did="already")
            rec = store.nav_get(system)
            tgts = store.targets_for(system)
            code, answer, save = self._op(kind, body, rec, tgts, system, planets, entries, num, integer)
            if code == 200 and save:
                if not store.nav_put(system, rec):
                    return 500, {"ok": False, "why": "couldn't save"}
            if code == 200 and press:   # (acted on: only now, so a failed press can still be answered - the MK fallback)
                self._keep(press[0], press[1], answer)
        if code == 200:
            self.board.changed()
        return code, answer

    def _op(self, kind, body, rec, tgts, system, planets, entries, num, integer):
        """(status, answer, save the record?)"""
        bad = (lambda why: (400, {"ok": False, "why": why}, False))
        pts = self._points(rec, tgts, planets)
        if kind == "xb":   # HUD X-B's bearings: {"act": "take", "body", "lat", "lon", "brg"} | "del" {"id"} | "clr"
            act, xb = body.get("act"), rec.get("xb") or {}
            if act == "take":
                b = planets.get(str(body.get("body") or "").lower())
                lat, lon, brg = num(body.get("lat")), num(body.get("lon")), num(body.get("brg"))
                if not b:
                    return bad("body")
                if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return bad("position")
                if brg is None:
                    return bad("bearing")
                fresh = str(xb.get("body") or "").lower() != b["name"].lower()   # (another body: a fresh set)
                lst = [] if fresh else list(xb.get("list") or [])
                nid = int(rec.get("xbn") or 0) + 1
                lst.append({"id": nid, "lat": round(lat, 6), "lon": round(lon, 6), "brg": round(brg % 360, 2), "saved": round(time.time(), 1)})
                dropped = max(0, len(lst) - XB_MAX)
                rec["xb"], rec["xbn"] = {"body": b["name"], "list": lst[dropped:]}, nid
                return 200, {"ok": True, "id": nid, "fresh": fresh and bool(xb.get("list")), "dropped": dropped}, True
            if act == "del":
                i = integer(body.get("id"))
                lst = list(xb.get("list") or [])
                if not any(x["id"] == i for x in lst):
                    return bad("bearing")
                rec["xb"] = dict(xb, list=[x for x in lst if x["id"] != i])
                return 200, {"ok": True}, True
            if act == "clr":
                rec.pop("xb", None)
                return 200, {"ok": True}, True
            return bad("act")
        if kind == "mark":   # {"body", "lat", "lon", "alt"?, "method": overfly | desig | xb, "dsg"?: also designate it, "n"?: the UFC's MK}
            b = planets.get(str(body.get("body") or "").lower())
            lat, lon, alt = num(body.get("lat")), num(body.get("lon")), num(body.get("alt"))
            if not b:
                return bad("body")
            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return bad("position")
            if body.get("method") not in MARK_METHODS:
                return bad("method")
            slot = int(rec.get("last") or 0) % MARK_SLOTS + 1
            self._forget(rec, f"mk{slot}")   # (the old MK in this slot: what was on it isn't on the new one)
            marks = rec.setdefault("marks", {})
            marks[str(slot)] = {"body": b["name"], "lat": round(lat, 6), "lon": round(lon, 6), "alt": round(alt) if alt is not None else None,
                                "method": body["method"], "saved": time.time()}
            rec["last"] = slot
            if body.get("dsg"):
                rec["tgt"] = {"key": f"mk{slot}", "src": "mk"}
            log(f"Mark: MK{slot} at {lat:.4f}, {lon:.4f} on {b['name']} ({MARK_METHODS[body['method']].lower()}).")
            return 200, {"ok": True, "mark": {"key": f"mk{slot}", "slot": slot, "name": f"MK{slot}", "body": b["name"],
                                              "lat": round(lat, 6), "lon": round(lon, 6)}}, True
        if kind in ("mkedit", "mkdel", "mkstor"):   # {"slot"} (+ "lat", "lon" to move it; "name"? to store it as a waypoint)
            slot = integer(body.get("slot"))
            mk = (rec.get("marks") or {}).get(str(slot))
            if not mk:
                return bad("mark")
            if kind == "mkdel":
                del rec["marks"][str(slot)]
                self._forget(rec, f"mk{slot}")
                return 200, {"ok": True}, True
            if kind == "mkedit":
                lat, lon = num(body.get("lat")), num(body.get("lon"))
                if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return bad("position")
                mk.update(lat=round(lat, 6), lon=round(lon, 6))
                return 200, {"ok": True}, True
            nm = body.get("name", "")
            name = " ".join(nm.split())[:40] if isinstance(nm, str) and all(c.isprintable() for c in nm) else None
            if name is None:
                return bad("name")
            t = self._store().add_target(system, mk["body"], _short_name(mk["body"], system), mk["lat"], mk["lon"], mk.get("method", "overfly"), name)
            return (200, {"ok": True, "tgt": t}, False) if t else (500, {"ok": False, "why": "couldn't save"}, False)
        if kind == "oap":   # {"id": a waypoint, "rng": metres (0: none), "brg": degrees true from it}
            tid, rng, brg = integer(body.get("id")), num(body.get("rng")), num(body.get("brg"))
            if f"t{tid}" not in pts:
                return bad("waypoint")
            if rng is None or not 0 <= rng <= 1e6 or (rng and (brg is None or not 0 <= brg <= 360)):
                return bad("offset")
            oaps = rec.setdefault("oaps", {})
            if rng:
                oaps[str(tid)] = {"rng": round(rng, 1), "brg": round(brg % 360, 1)}
            else:
                oaps.pop(str(tid), None)
                self._forget(rec, f"t{tid}o")
            return 200, {"ok": True}, True
        if kind == "dsg":   # {"key"} - again on the target: its waypoint's offset aimpoint, if it has one, then nothing; {"off": true}
            cur = (rec.get("tgt") or {}).get("key")
            key = body.get("key") if isinstance(body.get("key"), str) else None
            if body.get("off") or key is None:
                rec.pop("tgt", None)
                return 200, {"ok": True, "tgt": None}, True
            if key.startswith("atk:"):
                return bad("target")
            if key == cur and f"{key}o" in pts:   # the waypoint again: its offset aimpoint
                rec["tgt"] = {"key": f"{key}o", "src": "oap"}
                return 200, {"ok": True, "tgt": f"{key}o"}, True
            if cur in (key, f"{key}o"):   # again: nothing designated
                rec.pop("tgt", None)
                return 200, {"ok": True, "tgt": None}, True
            p = pts.get(key)
            if p:
                rec["tgt"] = {"key": key, "src": p["src"]}
                return 200, {"ok": True, "tgt": key}, True
            e = next((x for x in entries if x.get("key") == key), None)
            pic = (e or {}).get("pic") or {}
            if not e or pic.get("kind") != "surface" or pic.get("lat") is None or pic.get("lon") is None:
                return bad("not a surface target with a position")
            rec["tgt"] = {"key": key, "src": "site", "name": e.get("name") or "", "body": pic.get("body") or e.get("body") or "",
                          "lat": pic["lat"], "lon": pic["lon"]}
            return 200, {"ok": True, "tgt": key}, True
        if kind == "seq":   # {"seq": 1-3, "act": "ins" ("id", "after": a waypoint id, or none: the end) | "del" ("id") | "clr"
            # | "mv" ("id", "to": its place in the plan, from 0 - moved up or down there)}
            s = integer(body.get("seq"))
            if s is None or not 1 <= s <= SEQ_COUNT:
                return bad("seq")
            have = {t["id"]: t for t in tgts}
            ids = [i for i in (rec.get("seqs") or {}).get(str(s), []) if i in have]
            act, tid = body.get("act"), integer(body.get("id"))
            tot = (rec.get("tots") or {}).get(str(s)) or {}
            if act == "clr":
                ids = []
                tot.pop("tgt", None)   # (the plan's TOT's TGT went with it)
            elif act == "del":
                if tid not in ids:
                    return bad("not in it")
                ids.remove(tid)
                if tot.get("tgt") == tid:
                    tot.pop("tgt", None)
            elif act == "ins":
                if tid not in have:
                    return bad("waypoint")
                if tid in ids:
                    return bad("already in it")
                if ids and have[ids[0]]["body"].lower() != have[tid]["body"].lower():
                    return bad("another body")
                after = integer(body.get("after"))   # (0: at the start; none: at the end)
                if after not in (None, 0) and after not in ids:
                    return bad("not in it")
                ids.insert(0 if after == 0 else ids.index(after) + 1 if after is not None else len(ids), tid)
            elif act == "mv":   # (to a place, not by a step: the same move from two pages answering one turn of COMM2 is one)
                to = integer(body.get("to"))
                if tid not in ids:
                    return bad("not in it")
                if to is None:
                    return bad("place")
                ids.remove(tid)
                ids.insert(max(0, min(to, len(ids))), tid)
            else:
                return bad("act")
            rec.setdefault("seqs", {})[str(s)] = ids
            return 200, {"ok": True, "seq": [f"t{i}" for i in ids]}, True
        if kind == "tot":   # {"seq": 1-3, any of "tgt": a waypoint in it (id; null: none), "tot": Zulu seconds into the day
            # (0-86399; null: none), "gspd": knots, the IP -> TGT leg (null: none)} - TOT and GSPD only with a TGT set
            s = integer(body.get("seq"))
            if s is None or not 1 <= s <= SEQ_COUNT:
                return bad("seq")
            have = {t["id"] for t in tgts}
            ids = [i for i in (rec.get("seqs") or {}).get(str(s), []) if i in have]
            tot = dict((rec.get("tots") or {}).get(str(s)) or {})
            if tot.get("tgt") not in ids:
                tot.pop("tgt", None)
            if "tgt" in body:
                tid = integer(body["tgt"])
                if body["tgt"] is not None and tid not in ids:
                    return bad("not in it")
                if tid is None:
                    tot.pop("tgt", None)
                else:
                    tot["tgt"] = tid
            for k, lo, hi in (("tot", 0, 86399), ("gspd", ATK_LIMITS["kts"][0], ATK_LIMITS["kts"][1])):
                if k not in body:
                    continue
                v = integer(body[k])
                if body[k] is not None and (v is None or not lo <= v <= hi):
                    return bad(k)
                if v is not None and tot.get("tgt") is None:
                    return bad("set the TGT first")
                if v is None:
                    tot.pop(k, None)
                else:
                    tot[k] = v
            rec.setdefault("tots", {})[str(s)] = tot
            seqs = {str(s): [f"t{i}" for i in ids]}
            return 200, {"ok": True, "tot": self._tots(rec, {**{str(i): [] for i in range(1, SEQ_COUNT + 1)}, **seqs})[str(s)]}, True
        if kind == "setseq":   # {"seq": "1"-"3" | "atk"}: the flight plan the HSI flies; steer-to its first point -
            # or "none": no flight plan (the steer-to point stays; the HSI steps through all your waypoints and marks)
            s = str(body.get("seq"))
            if s not in [str(i) for i in range(1, SEQ_COUNT + 1)] + ["atk", "none"]:
                return bad("seq")
            rec["seq"] = s
            if s == "none":
                return 200, {"ok": True}, True
            keys = self._seq_keys(rec, tgts, s)
            if keys and rec.get("steer") not in keys:
                rec["steer"] = keys[0]
            return 200, {"ok": True}, True
        if kind == "steer":   # {"key"}: steer to it (null: to nothing); or {"step": +-n}: the HSI's COMM2 turns - the
            # activated flight plan's points in order (SEQ 1-3 or ATK), or with none activated, all the system's waypoints
            # then the marks; round again
            step = integer(body.get("step"))
            if step is not None:
                seq = rec.get("seq") or "none"
                if seq == "none":
                    order = [t["key"] for t in tgts] + [f"mk{s}" for s in sorted(rec.get("marks") or {}, key=int)]
                else:
                    order = self._seq_keys(rec, tgts, seq)
                if not order or not step:
                    return bad("nothing to steer to")
                cur = rec.get("steer")
                i = order.index(cur) if cur in order else (-1 if step > 0 else 0)
                rec["steer"] = order[(i + step) % len(order)]
                return 200, {"ok": True, "steer": rec["steer"]}, True
            key = body.get("key")
            if key is not None and key not in pts:
                return bad("point")
            rec["steer"] = key
            return 200, {"ok": True}, True
        if kind == "auto":   # {"from"}: AUTO sequencing - you've reached it: on to the next point of the flight plan
            keys = self._seq_keys(rec, tgts, rec.get("seq") or "none")
            if rec.get("auto") is False or body.get("from") != rec.get("steer") or rec.get("steer") not in keys:
                return 200, {"ok": True, "did": "nothing"}, False
            i = keys.index(rec["steer"])
            if i + 1 >= len(keys):
                return 200, {"ok": True, "did": "last"}, False
            rec["steer"] = keys[i + 1]
            return 200, {"ok": True, "steer": rec["steer"]}, True
        if kind == "automode":   # {"on": true | false}
            if not isinstance(body.get("on"), bool):
                return bad("on")
            rec["auto"] = body["on"]
            return 200, {"ok": True}, True
        if kind == "plan":   # Atk's plan settings: any of "hdg" (0-359, null: AUTO), "kts", "base", "step", "role" (1 | 2), "cs", "profile"
            plan = rec.setdefault("plan", {})
            for k in ("kts", "base", "step"):
                if k in body:
                    v, (lo, hi) = num(body[k]), ATK_LIMITS[k]
                    if v is None or not lo <= v <= hi:
                        return bad(k)
                    plan[k] = int(round(v))
            if "hdg" in body:
                v = num(body["hdg"])
                if body["hdg"] is not None and (v is None or not 0 <= v <= 360):
                    return bad("hdg")
                plan["hdg"] = None if body["hdg"] is None else int(round(v)) % 360
            if "role" in body:
                if body["role"] not in (1, 2):
                    return bad("role")
                plan["role"] = body["role"]
                built = plan.get("built")
                if built and rec.get("seq") == "atk":   # the other track: steer to its point of the same name (else its first)
                    old = str(rec.get("steer") or "").split(":")[-1]
                    ids = [p["id"] for p in built["roles"][str(body["role"])]]
                    rec["steer"] = f"atk:{body['role']}:{old if old in ids else ids[0]}"
            if "cs" in body:
                cs = str(body["cs"] or "").strip().upper()
                if not re.fullmatch(r"[A-Z0-9]{1,6}", cs):
                    return bad("cs")
                plan["cs"] = cs
            if "profile" in body:
                if body["profile"] not in ATK_PROFILES:
                    return bad("profile")
                plan["profile"] = body["profile"]
            return 200, {"ok": True}, True
        if kind == "build":   # Atk's BUILD: the plan's points round the target, for both roles; the HSI flies yours (ATK)
            return self._build(rec, tgts, pts, planets, None)
        if kind == "share":   # {"code"} or {"clip": true}: a waypoint code (a waypoint here - or the one you have there already),
            # a flight plan code (its waypoints, into the first empty SEQ - or "seq": 1-3, in place of what's in it) or Atk's plan code (as "load")
            text = get_clipboard() if body.get("clip") else body.get("code")
            got, why = parse_share_code(text if isinstance(text, str) else "")
            if not got:
                return 400, {"ok": False, "why": why}, False
            if got["kind"] == "atk":
                code, answer, save = self._op("load", {"code": text}, rec, tgts, system, planets, entries, num, integer)
                return code, dict(answer, kind="atk"), save
            b = planets.get(got["body"].lower())
            if not b:
                return bad(f"{got['body']} isn't in this system")
            s = None
            if got["kind"] == "plan":
                have = {t["id"] for t in tgts}
                if body.get("seq") is not None:
                    s = integer(body.get("seq"))
                    if s is None or not 1 <= s <= SEQ_COUNT:
                        return bad("seq")
                else:
                    s = next((i for i in range(1, SEQ_COUNT + 1) if not [x for x in (rec.get("seqs") or {}).get(str(i), []) if x in have]), None)
                    if s is None:
                        return 409, {"ok": False, "why": "no empty flight plan - clear a SEQ first"}, False
            ids, added, made = [], 0, []
            for p in got["pts"]:
                t = next((t for t in tgts if t["body"].lower() == b["name"].lower()
                          and abs(t["lat"] - p["lat"]) < 6e-6 and abs(t["lon"] - p["lon"]) < 6e-6), None)   # (yours already)
                if not t:
                    t = self._store().add_target(system, b["name"], _short_name(b["name"], system), p["lat"], p["lon"], "code", p["name"])
                    if not t:
                        return 500, {"ok": False, "why": "couldn't save"}, False
                    tgts.append(t)
                    added += 1
                if t["id"] not in ids:
                    ids.append(t["id"])
                    made.append(t)
            if got["kind"] == "wpt":
                t = made[0]
                return 200, {"ok": True, "kind": "wpt", "key": t["key"], "num": t["num"], "name": t["name"], "added": added}, False
            rec.setdefault("seqs", {})[str(s)] = ids
            (rec.get("tots") or {}).pop(str(s), None)   # (what was in it before: its TOT went with it)
            return 200, {"ok": True, "kind": "plan", "seq": str(s), "keys": [f"t{i}" for i in ids], "added": added}, True
        if kind == "load":   # {"code"} or {"clip": true} (this PC's clipboard): a plan from your wingman, built here
            text = get_clipboard() if body.get("clip") else body.get("code")
            got, why = parse_plan_code(text if isinstance(text, str) else "")
            if not got:
                return 400, {"ok": False, "why": why}, False
            b = planets.get(got["body"].lower())
            if not b:
                return bad(f"{got['body']} isn't in this system")
            plan = rec.setdefault("plan", {})
            plan.update(hdg=got["hdg"], kts=got["kts"], base=got["base"], step=got["step"], profile=got["profile"], cs=got["cs"],
                        role=2 if got["role"] == 1 else 1)   # (you fly the other role)
            rec["tgt"] = {"key": "plan", "src": "plan", "name": f"Target · {got['cs']}{got['role']}'s plan", "body": b["name"],
                          "lat": got["lat"], "lon": got["lon"]}
            return self._build(rec, tgts, pts, planets, rec["tgt"])
        return bad("op")

    @staticmethod
    def _forget(rec, key):
        """A point gone (or its slot about to be reused): the target and steer-to point drop it, rather than follow its key."""
        if (rec.get("tgt") or {}).get("key") == key:
            rec.pop("tgt", None)
        if rec.get("steer") == key:
            rec["steer"] = None

    def _build(self, rec, tgts, pts, planets, tgt):
        plan = self._plan(rec)
        t = tgt or rec.get("tgt")
        if t and t.get("src") in ("wpt", "oap", "mk"):
            p = pts.get(t.get("key"))
            t = dict(p, src=t["src"]) if p else None
        if not t:
            return 400, {"ok": False, "why": "no target - designate one"}, False
        r = self._radius(t["body"], planets)
        if not r:
            return 400, {"ok": False, "why": "the body's size isn't known"}, False
        hdg = plan["hdg"]
        if hdg is None:   # AUTO: the bearing you have to it now
            st = self.board.status or {}
            if str(st.get("BodyName") or "").lower() == t["body"].lower() and st.get("Latitude") is not None:
                hdg = round(_gc_m(st["Latitude"], st.get("Longitude", 0), t["lat"], t["lon"], r)[1]) % 360
            else:
                return 400, {"ok": False, "why": "set ATK HDG (AUTO needs you on the target's body)"}, False
        tg = {"key": t.get("key"), "name": t.get("name") or "", "body": t["body"], "lat": t["lat"], "lon": t["lon"]}
        built = build_attack(tg, hdg, plan["kts"], plan["base"], plan["step"], plan["profile"], plan["cs"], r)
        built.update(tgt=tg, hdg=hdg, kts=plan["kts"], base=plan["base"], step=plan["step"], profile=plan["profile"], cs=plan["cs"],
                     radius=r, t=time.time())
        rec.setdefault("plan", {})["built"] = built
        rec["plan"]["hdg"] = hdg   # (AUTO's bearing, kept: the plan is the one built)
        rec["seq"] = "atk"
        rec["steer"] = f"atk:{plan['role']}:{built['roles'][str(plan['role'])][0]['id']}"
        log(f"Attack plan: {ATK_PROFILES[plan['profile']]['name']} on {tg['name'] or 'the target'}, ATK HDG {hdg:03d}, {plan['kts']} kts.")
        return 200, {"ok": True, "hdg": hdg}, True

    # ---- the UFC's MK: an open page marks the point (its filter has you now); with none, Status.json's ----
    def mark_soon(self, n):
        threading.Timer(MK_PAGE_WAIT, self._mark_fallback, (n,)).start()

    def _mark_fallback(self, n):
        with self.lock:
            if n in self.handled["mk"]:
                return
        st = self.board.status or {}
        f = int(st.get("Flags") or 0)
        if not (f & F_LATLONG and st.get("BodyName") and st.get("Latitude") is not None):
            log("MK: no position (outside orbital cruise range).")
            self.keep("mk", n, {"ok": False, "why": "no position"})
            return
        code, answer = self.op({"op": "mark", "n": n, "body": st["BodyName"], "lat": st["Latitude"], "lon": st.get("Longitude", 0),
                                "alt": st.get("Altitude"), "method": "overfly"})
        if code != 200:
            log(f"MK: couldn't mark the point ({answer.get('why')}).")


class BoardState:
    """Everything the board knows, by area (see above), under one lock. apply() takes each
    journal event to the areas that handle it; snapshot() is what the page is sent."""

    def __init__(self, cache_file: Path, exobio_file: Path = None):
        self.lock = threading.RLock()
        self.live = False           # set once the journal history has been read; later events are live
        self.note = "Reading journal..."
        self.journal_file = ""
        self.last_event = ""
        self.engine_ok, self.engine_msg = None, "Checking AI login..."
        self.status = {}            # the latest Status.json (live flags, target, position)
        self.status_t = None        # when the game wrote it (the file's time): Traj times its position samples by it
        self.notify = None          # called on live jumps, start-ups and going in / out of the game, so pages refresh at once
        self.nudge = None           # called when anything new comes in (Status.json, the journal, a backstory): pages fetch the state at once
        self.keys = None            # KeySender, when the UFC is on (the copy button pastes with it)
        self.settlements = None     # SettlementLayouts: the layout confirmed for each settlement
        self.uplinks = None         # UplinkSettings: the Spansh Uplink and EDSM Uplink toggles
        self.schematics = None      # SchematicStore: the settlement layout plans
        self.records = None         # JournalRecords: what your journals say about systems (where Spansh has nothing)
        self.history = None         # JournalHistory: where you've been and the missions you've finished (from every journal)
        self.remote = None          # RemoteSystem: 1 Syst's REMOTE - a system picked to look at and plan in, not the one you're in
        self.coords = None          # CoordCache: systems' galactic coordinates (the remote one's distance)
        self._ly = (None, None)     # (the pair of systems, the light years between them), as last worked out
        self.cmdr = Commander(self)
        self.place = Place(self)
        self.contracts = Contracts(self, cache_file)
        self.vehicles = Vehicles(self)
        self.jumps = Jumps(self)
        self.dock_heading = DockHeading(self)
        self.systab = SystemTab(self)
        self.nav = NavBoard(self)   # 2 Nav's marks, flight plans, steer-to point, designated target and attack plan
        self.exobio = Exobio(self, exobio_file)   # the species you're sampling (2 Nav > HSI's rings), kept in exobio_file
        self.chat_codes = ChatCodes(self)         # waypoint, flight plan and attack plan codes heard in the game's chat (2 Nav > Wpt)
        # the order the areas see an event in (Commander before Place, so the log's UNDOCK line can still name the station you left)
        self.areas = (self.cmdr, self.place, self.contracts, self.vehicles, self.jumps, self.dock_heading, self.exobio, self.chat_codes)
        self._handlers = {}

    def viewed_system(self):
        """The system 1 Syst - and the Nav pages, which follow it - show: the remote one picked, else where you are."""
        here = self.place.system
        return self.remote.viewed(here, self.live) if self.remote else here

    def remote_view(self):
        """1 Syst's REMOTE, for the page: {"on": showing a remote system, "system": it, "here": where you are, "ly": how
        far it is (None: not known)}."""
        here = self.place.system
        viewed = self.viewed_system()
        on = bool(viewed and viewed != here)
        ly = None
        if on and self.coords:
            pair = (coord_key(here), coord_key(viewed), tuple(self.place.star_pos or ()))
            if self._ly[0] == pair:
                ly = self._ly[1]
            else:
                known, _ = self.coords.lookup([viewed] + ([here] if here and not self.place.star_pos else []))
                a = self.place.star_pos or known.get(coord_key(here))
                b = known.get(coord_key(viewed))
                ly = round(math.dist(a, b), 1) if a and b else None
                self._ly = (pair, ly) if ly is not None else (None, None)
        return {"on": on, "system": viewed if on else "", "here": here, "ly": ly}

    def log(self, ts, tag, text):
        """A line in the session log (Home tab)."""
        self.cmdr.log(ts, tag, text)

    def changed(self):
        """Something the page shows has changed: the open pages fetch the state now, rather than at their next 2-second look."""
        if self.nudge:
            try:
                self.nudge()
            except Exception as exc:
                log(f"Page nudge failed: {exc}")

    def fresh(self, ts):
        """A live event recent enough to act on (never ones read back at start-up)."""
        t = parse_time(ts)
        return self.live and t is not None and abs((now_utc() - t).total_seconds()) <= BOOT_FRESH_SECONDS

    def set_status(self, data, written=None):
        with self.lock:
            self.status = data if isinstance(data, dict) else {}
            self.status_t = written if written is not None else time.time()
            dock = self.dock_heading.take()   # docked on a settlement pad: your heading is in now
        if dock:
            self.dock_heading.save(dock)

    def set_engine(self, ok, msg):
        with self.lock:
            self.engine_ok, self.engine_msg = ok, msg

    def apply(self, ev: dict):
        """Update state from one journal event. Returns a mission dict when a new
        target mission was accepted, so a backstory can be requested."""
        kind, ts = ev.get("event"), ev.get("timestamp", "")
        added = None
        with self.lock:
            self.last_event = ts or self.last_event
            was_in = self.vehicles.ingame
            handlers = self._handlers.get(kind)
            if handlers is None:
                handlers = self._handlers[kind] = [h for h in (getattr(a, f"on_{kind}", None) for a in self.areas) if h]
            for handle in handlers:
                out = handle(ev, ts)
                if out is not None:
                    added = out
            signal = self.vehicles.ingame != was_in
            dock = self.dock_heading.take() if kind == "Docked" else None   # Status.json may already show it
        if dock:
            self.dock_heading.save(dock)
        if self.records is not None and kind in RECORD_EVENTS:   # its own lock: the page never waits on the file
            self.records.note(ev)
        if self.history is not None and kind in HISTORY_EVENTS:
            self.history.note(ev)
        if self.notify and self.live and (kind in ("StartJump", "FSDJump") or signal):   # a jump, or in / out of the game
            try:
                self.notify()
            except Exception as exc:
                log(f"Page nudge failed: {exc}")
        return added

    def snapshot(self, engine_name):
        with self.lock:
            return {
                "commander": self.cmdr.commander, "system": self.place.system,
                "journal": self.journal_file, "last_event": self.last_event, "note": self.note,
                "engine": engine_name, "engine_ok": self.engine_ok, "engine_msg": self.engine_msg,
                "contracts": self.contracts.view(),
                "cmdr": self.cmdr.view(),
                "sit": dict(self.place.sit, docked=self.place.docked),
                "log": list(self.cmdr.log_lines),
                "boot": dict(self.vehicles.boot), "game": self.vehicles.view(), "body": self.place.body,
                "syst": self.systab.view(),
                "remote": self.remote_view(),   # (1 Syst on a remote system: the strip says so)
                "star_pos": self.place.star_pos, "jump_range": self.cmdr.jump_range,
                "jump": self.jumps.view(),
                "exo": self.exobio.view(),   # the species you're sampling: 2 Nav > HSI's rings
                "schematics": self.schematics.summary() if self.schematics else {},   # layouts for each settlement economy
                "hist": self.history.summary() if self.history else {},   # the history pages' lists: changed? (and the old journals' reading)
                "version": VERSION,
            }


# --------------------------------------------------------------------------- #
# Background workers
# --------------------------------------------------------------------------- #
def ask_dossier(engine, job, timeout, rescan=False):
    """The AI's reply as a subject file's fields - asked once more if it doesn't fit, saying why: (fields, what was
    still wrong)."""
    kind = "rescan" if rescan else job["kind"]
    system, instruction = dossier_system(job["kind"]), DOSSIER_RESCAN if rescan else DOSSIER_INSTRUCTION
    fields, problems = check_dossier(engine.write(system, instruction, job["facts"], timeout), kind, job["ship_known"])
    if problems:
        log(f"Subject file for {job['name']} sent back: {'; '.join(problems)}")
        again = job["facts"] + "\n\n" + DOSSIER_RETRY.format(why="; ".join(problems))
        fields, problems = check_dossier(engine.write(system, instruction, again, timeout), kind, job["ship_known"])
    return fields, problems


class BackstoryWriter(threading.Thread):
    """Writes one subject file at a time so the AI tool is never run in parallel: a target's whole file (when its
    contract is accepted, or again with a long press on Contracts' Active panel), or just its behavioural notes and
    assessment once its first full scan is in. Each reply is checked (check_dossier); one that doesn't fit is sent
    back once, saying why."""

    def __init__(self, state: BoardState, engine: Engine, timeout: int):
        super().__init__(daemon=True, name="backstories")
        self.state, self.engine, self.timeout = state, engine, timeout
        self.jobs = queue.Queue()
        self.ok, self.msg = None, ""

    def request(self, mission, force=False):
        if self.engine.name == "none" or mission.get("kind") == "contract":   # backstories are for targets only
            return False
        key = mission["key"]
        with self.state.lock:
            entry = self.state.contracts.backstories.get(key)
            if entry and not force and entry.get("status") in ("done", "queued", "writing"):
                return False
            if entry and entry.get("status") in ("queued", "writing"):
                return False  # already in hand
            self.state.contracts.set_backstory(key, mission["target"], "queued")
        self.jobs.put(("write", key, mission["target"]))
        return True

    def rescan(self, key):
        """The notes and assessment again, from the target's first full scan (a subject file written before it)."""
        if self.engine.name == "none" or not self.state.contracts.needs_rescan(key):
            return False
        self.state.contracts.set_rescan(key, "queued")
        self.jobs.put(("rescan", key, (self.state.contracts.backstories.get(key) or {}).get("name", key)))
        return True

    def run(self):
        self.ok, self.msg = self.engine.check()
        self.state.set_engine(self.ok, self.msg)
        log(self.msg)
        while True:
            what, key, name = self.jobs.get()
            rescan = what == "rescan"
            if not self.ok:  # re-check, in case you've logged in since
                self.ok, self.msg = self.engine.check()
                self.state.set_engine(self.ok, self.msg)
            job = self.state.contracts.dossier_job(key, rescan=rescan) if self.ok else None
            if not job:
                if rescan:
                    self.state.contracts.set_rescan(key, None)
                else:
                    self.state.contracts.set_backstory(key, name, "error",
                                                       error=self.msg if not self.ok else "it's no longer an active contract")
                self.state.changed()
                continue
            if rescan:
                self.state.contracts.set_rescan(key, "writing")
            else:
                self.state.contracts.set_backstory(key, name, "writing")
            self.state.changed()
            log(f"Writing {'the scan notes in the ' if rescan else 'the '}subject file for {name}...")
            try:
                fields, problems = ask_dossier(self.engine, job, self.timeout, rescan)
                if problems:
                    raise RuntimeError("the AI's reply didn't fit the subject file (" + "; ".join(problems) + ")")
                if rescan:
                    self.state.contracts.update_dossier(key, fields, job)
                elif self.state.contracts.set_dossier(key, name, fields, job):
                    self.rescan(key)   # (its full scan came in while it was being written)
                log(f"Subject file ready for {name}.")
            except subprocess.TimeoutExpired:
                self._failed(key, name, rescan, f"timed out after {self.timeout}s")
            except Exception as exc:  # usage limit reached, network, a reply that wouldn't fit, etc.
                self._failed(key, name, rescan, str(exc))
            self.state.changed()   # done, timed out or failed: the page shows it now

    def _failed(self, key, name, rescan, why):
        log(f"Subject file for {name} failed: {why}")
        if rescan:   # (the file stays as it was: provisional)
            self.state.contracts.set_rescan(key, None)
        else:
            self.state.contracts.set_backstory(key, name, "error", error=why)


class JournalWatcher(threading.Thread):
    """Reads recent journal files, then follows them for new lines."""

    def __init__(self, journal_dir: Path, state: BoardState, writer: BackstoryWriter,
                 days: int, poll: float = 1.0):
        super().__init__(daemon=True, name="journal")
        self.dir, self.state, self.writer = journal_dir, state, writer
        self.days, self.poll = days, poll
        self.offsets = {}
        self.live = False
        self.status_mtime = None

    def _read_status(self):
        """Status.json: the game rewrites it as you fly (flags, target, position). True if it had changed."""
        path = self.dir / "Status.json"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return False
        if mtime == self.status_mtime:
            return False
        seen = time.time()
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text) if text.strip() else None   # empty: the game is between emptying it and writing it
        except (OSError, ValueError):
            data = None
        if TIMING:   # written (the file's time), seen, how long reading it took; caught mid-write (ok 0)
            TIMING.rec("st", seen=round(seen, 4), m=round(mtime, 4), ms=_ms(time.time() - seen), ok=int(isinstance(data, dict)),
                       pos=int(isinstance(data, dict) and data.get("Latitude") is not None))
        if not isinstance(data, dict):
            return False   # caught mid-write: read again next poll (not taken as "no position")
        self.status_mtime = mtime
        self.state.set_status(data, mtime)
        return True

    def _read_navroute(self):
        """NavRoute.json: the route plotted in the galaxy map (each stop's position and star class). True if it had changed."""
        path = self.dir / "NavRoute.json"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return False
        if mtime == getattr(self, "route_mtime", None):
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except (OSError, ValueError):
            return False
        self.route_mtime = mtime
        route = []
        for r in (data.get("Route") if isinstance(data, dict) else None) or []:
            pos = r.get("StarPos")
            ok = isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos)
            route.append({"system": r.get("StarSystem") or "", "pos": [float(v) for v in pos] if ok else None, "cls": r.get("StarClass") or ""})
        self.state.jumps.set_route(route)
        return True

    def _files(self, since: float):
        found = []
        for path in self.dir.glob("Journal.*.log"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime >= since or path in self.offsets:
                found.append((mtime, path))
        found.sort()
        return [p for _, p in found]

    def _read(self, path: Path):
        """New lines in a journal file, to the board. True if there were any."""
        offset = self.offsets.get(path, 0)
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size < offset:
            offset = 0
        if size == offset:
            self.offsets[path] = offset
            return False
        with open(path, "rb") as fh:
            fh.seek(offset)
            data = fh.read()
        end = data.rfind(b"\n")
        if end == -1:
            return False  # half-written line; pick it up next time
        chunk = data[:end + 1]
        self.offsets[path] = offset + len(chunk)
        for raw in chunk.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw.decode("utf-8", errors="replace"))
            except ValueError:
                continue
            added = self.state.apply(ev)
            if added and self.live:
                log(f"New target: {added['target']} ({added['title']})")
                self.writer.request(added)
            if self.live and self.state.contracts.rescans:   # a target's first full scan: its notes and assessment again
                for key in self.state.contracts.take_rescans():
                    self.writer.rescan(key)
        with self.state.lock:
            self.state.journal_file = path.name
        return True

    def run(self):
        warned = False
        while not self.dir.is_dir():
            if not warned:
                msg = f"Journal folder not found: {self.dir} (use --journal-dir)"
                log(msg)
                with self.state.lock:
                    self.state.note = msg
                warned = True
            time.sleep(5)

        for path in self._files(time.time() - self.days * 86400):
            self._read(path)
        self.live = True
        active = self.state.contracts.active()
        with self.state.lock:
            self.state.live = True
        with self.state.lock:
            self.state.note = ""
        self._read_status()
        self._read_navroute()
        self.state.vehicles.boot_check()   # a save loaded before the script started: in game by now?
        targets = [m for m in active if m["kind"] != "contract"]
        log(f"Journal loaded: {len(active)} active contract(s), {len(targets)} with a target.")
        for m in targets:
            self.writer.request(m)
        self.state.contracts.take_rescans()   # (scans read back: any subject file written before its full scan, again)
        for key in {m["key"] for m in targets}:
            self.writer.rescan(key)

        # Status.json and the journal being written are looked at every STATUS_POLL_SECONDS; the folder (for a new
        # journal file) and NavRoute.json every `poll` seconds. Anything new and the open pages fetch the state at once.
        newest, next_scan, last_it = None, 0.0, None
        while True:
            time.sleep(STATUS_POLL_SECONDS)
            try:
                new, now, scan = False, time.time(), False
                if now >= next_scan:
                    next_scan, scan = now + self.poll, True
                    files = self._files(now - 2 * 86400)
                    newest = files[-1] if files else None
                    for path in files:
                        new = self._read(path) or new
                    new = self._read_navroute() or new
                elif newest is not None:
                    new = self._read(newest) or new
                st_new = self._read_status()
                new = st_new or new
                if self.state.vehicles.boot_check() and self.state.notify:   # loading in: you're in game now
                    self.state.notify()
                elif new:
                    self.state.changed()
                    if TIMING:   # the open pages told to fetch the state (st: Status.json was the news)
                        TIMING.rec("chg", st=int(bool(st_new)))
                if TIMING:   # a slow look round, or a late one (the sleep overran)
                    took, gap = time.time() - now, (now - last_it) if last_it else 0
                    if took > 0.05 or gap > STATUS_POLL_SECONDS + 0.1:
                        TIMING.rec("loop", w=round(now, 4), ms=_ms(took), gap=_ms(gap), scan=int(scan))
                last_it = now
            except Exception as exc:
                log(f"Journal read problem: {exc}")


UPLINK_FILE = DATA_DIR / "uplink_settings.json"     # the Spansh Uplink and EDSM Uplink toggles (System list)
ARCHIVE_FILE = DATA_DIR / "system_archive.sqlite"   # Spansh's and EDSM's last answers for each system you've been in


REMOTE_FILE = DATA_DIR / "remote_system.json"   # 1 Syst's REMOTE: the system picked (and the ones picked lately)
REMOTE_RECENT = 8   # systems remembered as picked lately


class RemoteSystem:
    """1 Syst's CURRENT SYSTEM / REMOTE switch. REMOTE: a system you've picked to look at - its bodies and stations, and
    to plan in (waypoints, flight plans, attacks: the Nav pages follow 1 Syst) - instead of the one you're in. It stays
    picked through any number of jumps, until you switch back to the current system - or arrive in it, when it simply
    is the current system. Kept in remote_system.json, with the systems picked lately."""

    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        self.on, self.system, self.recent = False, "", []
        try:
            d = json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}
        except (OSError, ValueError):
            d = {}
        if isinstance(d, dict):
            self.on = d.get("on") is True and isinstance(d.get("system"), str) and bool(d["system"].strip())
            self.system = d["system"].strip()[:120] if isinstance(d.get("system"), str) else ""
            self.recent = [x[:120] for x in d.get("recent") or [] if isinstance(x, str) and x.strip()][:REMOTE_RECENT]

    def _save(self):   # (under the lock)
        if not self.path:
            return
        try:
            self.path.write_text(json.dumps({"on": self.on, "system": self.system, "recent": self.recent}), encoding="utf-8")
        except OSError as exc:
            log(f"Couldn't save {self.path.name} ({exc}).")

    def viewed(self, here, live=True):
        """The system 1 Syst (and the Nav pages) show: the remote one picked - unless you've arrived in it - else where
        you are. (live: the journal's being followed now - not your old ones read at start-up, passing through it.)"""
        with self.lock:
            if not (self.on and self.system):
                return here
            if here and coord_key(self.system) == coord_key(here):   # arrived: it's the current system now
                if live:
                    self.on = False
                    self._save()
                    log(f"Arrived in {here}: 1 Syst is on the current system again.")
                return here
            return self.system

    def active(self, here):
        return self.viewed(here) != here

    def pick(self, system):
        with self.lock:
            self.on, self.system = True, system
            self.recent = [system] + [x for x in self.recent if coord_key(x) != coord_key(system)][:REMOTE_RECENT - 1]
            self._save()
        log(f"1 Syst: remote - {system}.")

    def off(self):
        with self.lock:
            was, self.on = self.on, False
            self._save()
        if was:
            log("1 Syst: the current system again.")

    def lately(self):
        with self.lock:
            return list(self.recent)


def remote_options(state, ocor=None):
    """1 Syst's REMOTE list (after MANUAL, the page's own): systems to pick, by where they come from - your plotted
    route's destination, your active missions' systems, OCOR's objectives, the systems you've been in lately, and the
    ones picked lately - each {"g", "name", "why", "ly": light years from you (None: not known)}. Where you are isn't
    listed."""
    here = coord_key(state.place.system)
    with state.lock:
        route = list(state.jumps.navroute)
        star = list(state.place.star_pos) if state.place.star_pos else None
    items, pos = [], {}

    def add(g, name, why=""):
        name = str(name or "").strip()
        if name and coord_key(name) != here and not any(i["g"] == g and coord_key(i["name"]) == coord_key(name) for i in items):
            items.append({"g": g, "name": name[:120], "why": str(why or "")[:60], "ly": None})

    if route and route[-1].get("system"):
        add("route", route[-1]["system"], f"{max(0, len(route) - 1)} jump{'' if len(route) == 2 else 's'}")
        if route[-1].get("pos"):
            pos[coord_key(route[-1]["system"])] = tuple(route[-1]["pos"])
    for m in state.contracts.active():
        add("missions", m.get("system"), m.get("title") or m.get("kind") or "")
    for name in (ocor.systems() if ocor else []):
        add("ocor", name)
    for name in (state.history.recent_systems(10) if state.history else []):
        add("hist", name)
    for name in (state.remote.lately() if state.remote else []):
        add("recent", name)
    if state.coords and star:
        known, _ = state.coords.lookup([i["name"] for i in items])
        known.update(pos)
        for i in items:
            p = known.get(coord_key(i["name"]))
            i["ly"] = round(math.dist(star, p), 1) if p else None
    return items


def remote_search(state, text):
    """MANUAL's matches for what's typed (two letters at least): systems you know of (the coordinates cache's - every
    system your journals have given a position - and REMOTE's list's) whose names start with it, then Spansh's search's
    (Spansh Uplink on) - [{"name", "ly"}], at most 10, an exact match first."""
    q = " ".join(str(text or "").split())[:60]
    if len(q) < 2:
        return []
    found = {}   # coord key -> (name, coordinates or None)
    for name, p in (state.coords.search(q, 10) if state.coords else []):
        found.setdefault(coord_key(name), (name, p))
    for i in remote_options(state):
        if coord_key(i["name"]).startswith(coord_key(q)):
            found.setdefault(coord_key(i["name"]), (i["name"], None))
    if state.uplinks and state.uplinks.spansh:
        try:
            answer = spansh_get(f"search/systems?q={quote(q)}") or {}
        except Exception:   # (no internet, Spansh busy: what's known here)
            answer = {}
        got = {}
        for r in (answer.get("results") or []) if isinstance(answer, dict) else []:
            if isinstance(r, dict) and isinstance(r.get("name"), str):
                p = (r.get("x"), r.get("y"), r.get("z"))
                p = p if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p) else None
                found.setdefault(coord_key(r["name"]), (r["name"], p))
                if p:
                    got[r["name"]] = p
        if got and state.coords:
            state.coords.store(got, source="spansh")
    star = state.place.star_pos
    k = coord_key(q)
    rank = sorted(found.items(), key=lambda kv: (kv[0] != k, not kv[0].startswith(k), len(kv[0]), kv[0]))[:10]
    known = state.coords.lookup([v[0] for _, v in rank if v[1] is None])[0] if star and state.coords else {}
    out = []
    for key, (name, p) in rank:
        p = p or known.get(key)
        out.append({"name": name, "ly": round(math.dist(star, p), 1) if star and p else None})
    return out


def remote_pick(state, text):
    """REMOTE: a system picked (by name - the list's, or MANUAL's: as Spansh spells it if it knows it, else as your
    journals do). (HTTP status, answer)."""
    name = " ".join(text.split())[:120] if isinstance(text, str) else ""
    if not name or not all(c.isprintable() for c in name):
        return 400, {"ok": False, "why": "name"}
    here = state.place.system
    if here and coord_key(name) == coord_key(here):   # (where you are: that's the current system)
        state.remote.off()
        state.changed()
        return 200, {"ok": True, "system": here, "current": True}
    known = {coord_key(i["name"]): i["name"] for i in remote_options(state)}
    if state.coords:
        known.update({coord_key(n): n for n, _ in state.coords.search(name, 3)})
    canon = known.get(coord_key(name))
    if canon is None and state.uplinks and state.uplinks.spansh:
        try:
            hit = spansh_find(name)
        except Exception:   # (Spansh unreachable: the name as typed - EDSM may know it)
            hit = {"name": name}
        if not hit:
            return 404, {"ok": False, "why": "unknown"}
        canon = hit["name"]
        if state.coords and all(isinstance(hit.get(c), (int, float)) for c in "xyz"):
            state.coords.store({canon: (hit["x"], hit["y"], hit["z"])}, source="spansh")
    state.remote.pick(canon or name)
    state.changed()
    return 200, {"ok": True, "system": canon or name}


class UplinkSettings:
    """The Spansh Uplink and EDSM Uplink toggles at the bottom of the System list (and the UFC's last COMM1
    stops there): where systems' bodies and stations come from, whether EDSM's traffic, deaths and value are
    fetched, and where OCOR's coordinates come from. Kept in uplink_settings.json; --no-spansh / --no-edsm
    start one off for that run."""

    def __init__(self, path: Path, spansh_off=False, edsm_off=False):
        self.path, self.lock, self.listeners = path, threading.Lock(), []
        saved = {}
        try:
            saved = json.loads(path.read_text(encoding="utf-8")) if path else {}
            saved = saved if isinstance(saved, dict) else {}
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log(f"Uplink settings unreadable ({exc}); both on.")
        self.spansh = saved.get("spansh") is not False and not spansh_off
        self.edsm = saved.get("edsm") is not False and not edsm_off

    @property
    def offline(self):
        return not (self.spansh or self.edsm)

    def view(self):
        return {"spansh": self.spansh, "edsm": self.edsm}

    def set(self, name, on):
        """Switch one on or off (and keep it); the fetcher and OCOR hear at once."""
        if name not in ("spansh", "edsm"):
            return False
        with self.lock:
            setattr(self, name, bool(on))
            try:
                if not self.path:
                    raise FileNotFoundError("not kept")
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.view()), encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError as exc:
                log(f"Couldn't save the uplink settings ({exc}).")
        log(f"{'Spansh' if name == 'spansh' else 'EDSM'} Uplink {'on' if on else 'off'}.")
        for listener in list(self.listeners):
            try:
                listener()
            except Exception as exc:
                log(f"Uplink change: problem ({exc}).")
        return True


class SystemArchive:
    """Spansh's and EDSM's last answers for every system you've been in, kept for good in
    system_archive.sqlite (the cache keeps others a week): revisiting one shows it even if neither site
    can be reached."""

    SCHEMA = ("CREATE TABLE IF NOT EXISTS parts (key TEXT PRIMARY KEY, system TEXT NOT NULL, part TEXT NOT NULL, "
              "t REAL NOT NULL, data TEXT NOT NULL) WITHOUT ROWID")

    def __init__(self, path: Path):
        self.lock = threading.Lock()
        self.db = open_sqlite(path, self.SCHEMA, "parts", "System archive")

    def get(self, system, part):
        with self.lock:
            try:
                row = self.db.execute("SELECT t, data FROM parts WHERE key = ?", (f"{system.lower()}|{part}",)).fetchone()
            except sqlite3.Error:
                return None
        if not row:
            return None
        try:
            return row[0], json.loads(row[1])
        except ValueError:
            return None

    def put(self, system, parts):
        """parts: {part: (fetched time, data)}."""
        with self.lock:
            try:
                with self.db:
                    self.db.executemany("INSERT OR REPLACE INTO parts (key, system, part, t, data) VALUES (?, ?, ?, ?, ?)",
                                        [(f"{system.lower()}|{p}", system, p, t, json.dumps(d, ensure_ascii=False))
                                         for p, (t, d) in parts.items()])
            except sqlite3.Error as exc:
                log(f"Couldn't archive {system} ({exc}).")


class EdsmCache:
    """Spansh's and EDSM's answers kept in edsm_cache.json next to the script, so revisiting a system or
    restarting reuses them. A system's parts are fetched together; that time (its last uplink) says when
    they're due again (EDSM_REFRESH). Copies are kept a week, then dropped - except for the systems you've
    been in, which the archive keeps (a copy no longer in the cache comes from there)."""

    def __init__(self, path: Path, archive=None):
        self.path, self.data, self.archive = path, {}, archive
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.data = data if isinstance(data, dict) else {}
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log(f"System data cache unreadable ({exc}); starting a new one.")

    def get(self, system, part):
        """(fetched time, data) or None (from the archive, for a system you've been in that's left the cache)."""
        entry = (self.data.get(system.lower()) or {}).get(part)
        if isinstance(entry, dict) and "t" in entry:
            return entry["t"], entry.get("data") or {}
        return self.archive.get(system, part) if self.archive else None

    def keep(self, system, parts):
        """A system you're in: its parts copied to the archive, kept for good."""
        if self.archive:
            got = {p: hit for p in parts for hit in [(self.data.get(system.lower()) or {}).get(p)]
                   if isinstance(hit, dict) and "t" in hit}
            if got:
                self.archive.put(system, {p: (h["t"], h.get("data") or {}) for p, h in got.items()})

    def put(self, system, part, data, t=None):
        self.data.setdefault(system.lower(), {})[part] = {"t": t or time.time(), "data": data}

    def uplink(self, system):
        """When all its parts were last fetched together, or None."""
        entry = (self.data.get(system.lower()) or {}).get("_uplink")
        return entry.get("t") if isinstance(entry, dict) else None

    def set_uplink(self, system, t):
        self.data.setdefault(system.lower(), {})["_uplink"] = {"t": t}

    def fresh(self, system, now=None, parts=()):
        """Fetched under an hour ago - with every one of these parts (a part newly asked for is due at once)."""
        t = self.uplink(system)
        return t is not None and (now or time.time()) - t < EDSM_REFRESH and all(self.get(system, p) for p in parts)

    def save(self):
        now, keep = time.time(), {}
        for system, parts in self.data.items():
            parts = {k: v for k, v in parts.items()
                     if (k in CACHE_PARTS or k == "_uplink") and isinstance(v, dict) and now - v.get("t", 0) < EDSM_KEEP}
            if parts:
                keep[system] = parts
        newest = sorted(keep, key=lambda k: -max(v["t"] for v in keep[k].values()))[:EDSM_CACHE_MAX]
        self.data = {k: keep[k] for k in newest}
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log(f"Couldn't save the system data cache ({exc}).")


class EdsmFetcher(threading.Thread):
    """Keeps Syst filled for the system you're in (or the remote one picked: REMOTE), from the sources the Spansh Uplink and EDSM Uplink toggles
    allow (UplinkSettings). Bodies and stations: Spansh's record (one, by the system's 64-bit address, market
    prices thrown away) - or EDSM's if Spansh is off, or has nothing for the system (EDDiscovery's "Spansh then
    EDSM"); traffic, deaths and exploration value: EDSM; your journal records adding to both and winning
    where they know better (merge_records). A system's parts are fetched together, at most once an hour
    (EDSM_REFRESH): on arriving (from the cache if that's younger), again when the hour is up, ahead of arrival
    while you're in hyperspace, when you press System Data Uplink Synchronise, and when a toggle changes. Also
    counts your own visits from your journals. Nothing else waits on it."""

    def __init__(self, state: BoardState, journal_dir: Path, cache: EdsmCache, records=None, uplinks=None):
        super().__init__(daemon=True, name="edsm")
        self.state, self.dir, self.cache, self.records = state, journal_dir, cache, records
        self.uplinks = uplinks or UplinkSettings(None)
        self.uplinks.listeners.append(self._sources_changed)
        self.rec_seen = None
        self.wake = threading.Event()   # an uplink asked for, or a toggle changed
        self.changed = threading.Event()   # a toggle changed: rebuild (and fetch what's now due) at once
        self.ulock = threading.Lock()
        self.ids = {}   # system name (lower case) -> its address, from Spansh's search (when your journal hasn't given it)
        state.systab.fetcher = self

    @property
    def spansh(self):
        return self.uplinks.spansh

    @property
    def edsm(self):
        return self.uplinks.edsm

    @property
    def offline(self):
        return self.uplinks.offline   # (both toggles off: your journal records only)

    def _sources_changed(self):
        self.state.jumps.survey_off, self.state.jumps.survey_src = self.offline, self.source()
        self.changed.set()
        self.wake.set()
        self._nudge()

    def source(self, system=None):
        """Where bodies and stations come from (for the system, as cached): Spansh, EDSM or your journal."""
        if system and self.spansh and self._spansh_has(system):
            return "Spansh"
        if system and self.edsm and self.cache.get(system, "bodies") and (not self.spansh or self.cache.get(system, "spansh")):
            return "EDSM"
        return "Spansh" if self.spansh else "EDSM" if self.edsm else "your journal"

    def _spansh_has(self, system, data=None):
        """Spansh's record of the system lists something (else it's EDSM's turn)."""
        if data is None:
            hit = self.cache.get(system, "spansh")
            data = hit[1] if hit else None
        return bool(isinstance(data, dict) and (data.get("bodies") or data.get("stations")))

    def _parts(self, system, spansh_data=None):
        """What the system needs as things stand: Spansh's record; EDSM's bodies and stations if Spansh is off or
        has nothing for it; EDSM's traffic, deaths and value."""
        parts = ["spansh"] if self.spansh else []
        if self.edsm:
            if not self.spansh or not self._spansh_has(system, spansh_data):
                parts += ["bodies", "stations"]
            parts += list(EDSM_EXTRA)
        return parts

    def _get(self, part, system):
        import urllib.request
        from urllib.parse import urlencode
        req = urllib.request.Request(f"{EDSM_API}{part}?{urlencode({'systemName': system})}",
                                     headers={"User-Agent": user_agent()})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8") or "null")
        return data if isinstance(data, dict) else {}

    def _spansh(self, path):
        """GET a Spansh API path: its answer, or None if Spansh has no such record (404)."""
        return spansh_get(path)

    def _id64(self, system):
        """The system's 64-bit address: from your journal (where you are, where you're jumping), else Spansh's search."""
        found = self.state.place.address_of(system) or self.ids.get(system.lower())
        if found:
            return found
        hit = spansh_find(system, self._spansh)
        if hit:
            self.ids[system.lower()] = hit["id64"]
            return hit["id64"]
        return None

    def _get_spansh(self, system):
        """Spansh's record of the system, stripped ({} if Spansh doesn't know it)."""
        id64 = self._id64(system)
        if not id64:
            return {}
        answer = self._spansh(f"dump/{id64}")
        return strip_spansh((answer or {}).get("system")) if isinstance(answer, dict) else {}

    def _fetch_all(self, system):
        """All its parts, together: Spansh's first (if it's on), then EDSM's - its bodies and stations too if
        Spansh has nothing for the system, or couldn't be reached. Only a complete set replaces the cached copy
        (and sets the uplink time); otherwise the copy stays as it was - unless there's no copy at all, when what
        did come is kept, as better than nothing. Returns (ok, error, the parts asked for)."""
        got, errors, failed = {}, [], set()
        parts = ["spansh"] if self.spansh else []
        if self.spansh:
            try:
                got["spansh"] = self._get_spansh(system)
            except Exception as exc:   # network, Spansh busy, odd data
                errors.append(f"Spansh: {str(exc)[:110]}")
                failed.add("spansh")
        if self.edsm:
            more = (["bodies", "stations"] if not self.spansh or "spansh" in failed or not self._spansh_has(system, got.get("spansh"))
                    else []) + list(EDSM_EXTRA)
            parts += more
            for part in more:
                try:
                    got[part] = self._get(part, system)
                    time.sleep(0.25)
                except Exception as exc:   # network, EDSM busy, odd data
                    errors.append(f"EDSM: {str(exc)[:110]}")
                    break
        now = time.time()
        if parts and len(got) == len(parts):
            for part, data in got.items():
                self.cache.put(system, part, data, now)
            self.cache.set_uplink(system, now)
            self.cache.save()
            return True, "", parts
        if got and not any(self.cache.get(system, p) for p in parts):
            for part, data in got.items():
                self.cache.put(system, part, data, now)
            self.cache.save()
        return False, "; ".join(errors) or "no answer", parts

    def _raw(self, system, extra=True):
        """What the tab is built from, as cached: Spansh's bodies and stations - or EDSM's, if Spansh is off or has
        nothing for the system - and EDSM's traffic, deaths and value (extra)."""
        raw = {}
        hit = self.cache.get(system, "spansh") if self.spansh else None
        if hit and self._spansh_has(system, hit[1]):
            raw.update(spansh_raw(hit[1]))
        elif self.edsm:
            for part in ("bodies", "stations"):
                h = self.cache.get(system, part)
                if h:
                    raw[part] = h[1]
        if self.edsm and extra:
            for part in EDSM_EXTRA:
                h = self.cache.get(system, part)
                if h:
                    raw[part] = h[1]
        return raw

    def update(self, system, arrived, force=False, uplink=False):
        """Fetch this system's parts if they're due (uplink: now, whatever their age); rebuild the tab if
        anything changed (force: your journal records for it have, or a toggle). Returns (seconds until the next
        check, whether a fetch was tried and worked)."""
        now = time.time()
        parts = self._parts(system)
        due = not self.offline and (uplink or not self.cache.fresh(system, now, parts))
        if not due and not arrived and not force:
            return min(60, max(1, EDSM_REFRESH - (now - (self.cache.uplink(system) or now)))), None
        if arrived and due and not any(self.cache.get(system, p) for p in parts):
            self.state.systab.set(system, status="loading")
        ok, error = True, ""
        if due:
            ok, error, parts = self._fetch_all(system)
        raw = self._raw(system)
        rec = self.records.for_system(system) if self.records else None
        has_rec = bool(rec and (rec["bodies"] or rec["stations"]))
        has_sys = not self.offline and any(self.cache.get(system, p) for p in parts)   # (an answer, even "not known")
        if not has_sys and not has_rec:
            if self.offline:
                self.state.systab.set(system, status="off")
                return 60, None
            log(f"System data: couldn't fetch {system} ({error}); retrying in a minute.")
            self.state.systab.set(system, status="error", error=error)
            return EDSM_RETRY, False
        with self.state.lock:
            if self.state.viewed_system() != system:
                return 1, (ok if due else None)   # you've moved on (or 1 Syst has); start again for the new system
            been = self.state.place.system == system
        if has_sys and been and (arrived or (due and ok)):
            self.cache.keep(system, parts)   # a system you've been in: kept for good (not one only looked at: REMOTE)
        model, index = build_syst(system, merge_records(raw, rec), count_visits(self.dir, system))
        t = self.cache.uplink(system)
        model["uplink"] = datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds") if t else None
        listed = (raw.get("bodies") or {}).get("bodies") or (raw.get("stations") or {}).get("stations")
        src = self.source(system)
        model["source"] = ("spansh" if src == "Spansh" else "edsm" if src == "EDSM" else "journal") if listed else "journal"
        status = "ok" if self.offline or ok else "error"
        self.state.systab.set(system, model, index, status=status, error=error)
        if arrived or due:
            log(f"System data: {system} - {model['bodies']} bodies, {len(model['entries']) - model['bodies']} stations from {src} "
                f"({'fetched' if due and ok else 'unavailable, showing the cached copy' if due and has_sys else 'from cache'}).")
        if due and not ok:
            return EDSM_RETRY, False
        return 60, (True if due else None)

    # ---- System Data Uplink Synchronise: fetch the system 1 Syst shows now (where you are, or REMOTE's) ----
    def request_uplink(self):
        """A press (on a page, or the UFC). Returns (HTTP status, answer)."""
        tab = self.state.systab
        if self.offline:
            return 409, {"ok": False, "why": "offline"}
        with self.state.lock:
            system = self.state.viewed_system()
        if not system:
            return 409, {"ok": False, "why": "nowhere"}
        now = time.time()
        with self.ulock:
            u = tab.uplink
            if u["busy"]:
                return 409, {"ok": False, "why": "busy"}
            if now - u["pressed"] < UPLINK_EVERY:
                return 429, {"ok": False, "why": "wait", "wait": int(UPLINK_EVERY - (now - u["pressed"])) + 1}
            u.update(busy=True, pressed=now, result=None, error="")
        self.wake.set()
        self._nudge()
        return 202, {"ok": True}

    def _uplink(self, system):
        t0, hold = time.time(), random.uniform(*UPLINK_HOLD)
        try:
            delay, ok = self.update(system, False, uplink=True)
        except Exception as exc:
            delay, ok = EDSM_RETRY, False
            log(f"System data: problem with {system} ({exc}).")
        rest = t0 + hold - time.time()
        if rest > 0:
            time.sleep(rest)   # (it shows "in progress" for a moment, however fast the answer is)
        with self.ulock:
            self.state.systab.uplink.update(busy=False, done=time.time(), result="ok" if ok else "error",
                                            error="" if ok else self.state.systab.error)
        self._nudge()
        return delay

    def _nudge(self):
        if self.state.notify:
            try:
                self.state.notify()
            except Exception:
                pass

    def prefetch(self, system):
        """The system you're jumping to: all its parts, fetched while you're in hyperspace (and cached, so
        arriving needs no second fetch). Returns False if Spansh (or EDSM) couldn't be reached."""
        self.state.jumps.set_survey(system, "fetching", src=self.source())
        error = ""
        if not self.offline and not self.cache.fresh(system, parts=self._parts(system)):
            _ok, error, _parts = self._fetch_all(system)
        raw = merge_records(self._raw(system, extra=False), self.records.for_system(system) if self.records else None)   # and what your journals add
        bodies = [b for b in (raw.get("bodies") or {}).get("bodies") or [] if b.get("name")]
        if not bodies:
            self.state.jumps.set_survey(system, "off" if self.offline else "error" if error else "none", error=error, src=self.source())
            return not error
        model, _ = build_syst(system, raw, {})
        main = next((b for b in bodies if b.get("isMainStar")), None) or next((b for b in bodies if b.get("type") == "Star"), None)
        sts = (raw.get("stations") or {}).get("stations") or []
        carriers = sum(1 for x in sts if "carrier" in str(x.get("type") or "").lower())
        self.state.jumps.set_survey(system, "ok", model["map"], star_from_edsm(main, main.get("_from") or "edsm") if main else None,
                                    len(bodies), len(sts) - carriers, carriers, src=self.source(system))
        log(f"System data: {system} surveyed ahead of arrival ({len(bodies)} bodies, {len(sts) - carriers} stations, {carriers} carriers).")
        return True

    def _keep_here(self, here):
        """REMOTE on: the system you've arrived in isn't 1 Syst's - but it's still fetched (if it's due; the jump's survey
        has usually done that) and kept for good as a system you've been in, ready for CURRENT SYSTEM."""
        parts = self._parts(here)
        if not self.offline and not self.cache.fresh(here, time.time(), parts):
            self._fetch_all(here)
        if any(self.cache.get(here, p) for p in parts):
            self.cache.keep(here, parts)

    def run(self):
        last, due, surveyed, retry = None, 0.0, None, 0.0
        kept = None   # (REMOTE on: the last system you were in that was kept)
        while True:
            target = self.state.jumps.target()
            if target and target != surveyed and time.time() >= retry:   # jumping: survey where you're going
                try:
                    ok = self.prefetch(target[1])
                except Exception as exc:
                    ok = False
                    log(f"System data: couldn't survey {target[1]} ({exc}).")
                if ok:
                    surveyed = target
                else:
                    retry = time.time() + 5
            with self.state.lock:
                system = self.state.viewed_system()   # (where you are - or the remote system 1 Syst has: REMOTE)
                here, live = self.state.place.system, self.state.live
            if here and live and here != system and here != kept:   # (REMOTE on, and you've arrived somewhere else)
                kept = here
                try:
                    self._keep_here(here)
                except Exception as exc:
                    log(f"System data: problem with {here} ({exc}).")
            if self.changed.is_set():   # a toggle changed: the tab again, from what's now allowed (fetching what's due)
                self.changed.clear()
                if system and not self.state.systab.uplink["busy"]:
                    try:
                        last = system
                        due = time.time() + self.update(system, False, force=True)[0]
                    except Exception as exc:
                        log(f"System data: problem with {system} ({exc}).")
                        due = time.time() + EDSM_RETRY
                if not self.state.systab.uplink["busy"]:
                    self.wake.clear()
                    continue
            if self.wake.is_set():   # System Data Uplink Synchronise
                self.wake.clear()
                if system:
                    last = system
                    due = time.time() + self._uplink(system)
                    continue
                with self.ulock:
                    self.state.systab.uplink.update(busy=False, done=time.time(), result="error", error="no system")
                self._nudge()
            ver = (system, self.records.version(system)) if self.records and system else None
            changed = ver is not None and ver != self.rec_seen and system == last
            if system and (system != last or time.time() >= due or changed):
                arrived = system != last
                last = system
                self.rec_seen = ver
                try:
                    due = time.time() + self.update(system, arrived, force=changed)[0]
                except Exception as exc:
                    log(f"System data: problem with {system} ({exc}); retrying in a minute.")
                    due = time.time() + EDSM_RETRY
            self.wake.wait(1)


# =========================================================================== #
# WinWing UFC: button reading, display and keypresses (replaces VoiceAttack)
# =========================================================================== #
# The UFC display is drawn by WinWing SimApp Pro, which must be running: we pose
# as DCS with an F/A-18C loaded and send it the Hornet's UFC text over UDP.
# Buttons are read directly over USB (hidapi). Option buttons send keypresses to
# Elite, looked up by action name in your Elite bindings file.

DEFAULT_BINDINGS_DIR = (Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
                        / "Frontier Developments" / "Elite Dangerous" / "Options" / "Bindings")
ELITE_PROCESS = "elitedangerous64.exe"
SIMAPP_HOST, SIMAPP_PORT = "127.0.0.1", int(os.environ.get("EDTB_SIMAPP_PORT") or 16536)   # the env var is for the tests

UFC_PRODUCT = "WINWING UFC1"
UFC_LOOP_SECONDS = 0.05      # read every waiting USB report this often
UFC_READS_PER_POLL = 64      # at most this many reports each time, then the long-pull and start-up timers
UFC_STABLE_READS = 2         # a press counts once two reports in a row agree
UFC_START_MENU = "NAV"       # menu shown when the script starts

# Bit order of the UFC's button report (report ID 1), first bit first.
UFC_BUTTONS = [
    "IP", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "0", "Ent",
    "Opt1", "Opt2", "Opt3", "Opt4", "Opt5", "EmCon",
    "AP", "IFF", "TCN", "ILS", "DL", "BCN", "ON_OFF",
    "COMM1_CCW", "COMM1_CW", "COMM1_PULL", "COMM2_CCW", "COMM2_CW", "COMM2_PULL",
]
UFC_PULSE_BUTTONS = {"COMM1_CCW", "COMM1_CW", "COMM2_CCW", "COMM2_CW"}   # knob turns: no debounce
UFC_LONG_BUTTONS = {"COMM2_PULL"}   # these also send <name>_LONG when held for UFC_LONG_PULL seconds
UFC_LONG_PULL = 2.0
# The brightness and the two volume knobs are dials (not buttons): where they sit in the
# UFC's reports is learned once with --ufc-learn and saved here.
UFC_AXES_FILE = DATA_DIR / "ufc_axes.json"
UFC_KNOBS = (("brightness", "the BRT (brightness) knob"),
             ("comm2_volume", "the COMM2 VOLUME knob (the small dial, not the COMM2 channel knob)"),
             ("comm1_volume", "the COMM1 VOLUME knob (the small dial on the left, not the COMM1 channel knob)"))
UFC_AXIS_NOISE = 0.002      # ignore changes smaller than this share of a knob's travel (or 1.5 steps of a coarse dial)

# The menus. Each function button picks a menu; each option is (label, Elite action).
# Labels are 4 characters at most. An action starting with "!" is a fixed key (FIXED_KEYS).
UFC_MENUS = {
    "AP": {"code": "FI", "num": "1", "options": [   # fighter orders, page 1
        ("", None), ("", None),
        ("RETN", "OrderRequestDock"), ("FOLL", "OrderFollow"), ("POSI", "OrderHoldPosition")]},
    "IFF": {"code": "TG", "num": "", "options": [   # targeting
        ("NXTG", "CycleNextTarget"), ("PRTG", "CyclePreviousTarget"),
        ("NXHO", "CycleNextHostileTarget"), ("PRHO", "CyclePreviousHostileTarget"),
        ("HIGH", "SelectHighestThreat")]},
    "TCN": {"code": "FI", "num": "2", "options": [   # fighter orders, page 2
        ("FREE", "OrderAggressiveBehaviour"), ("DEF", "OrderDefensiveBehaviour"),
        ("TGT", "OrderFocusTarget"), ("HOLD", "OrderHoldFire"), ("", None)]},
    "NAV": {"code": "NV", "num": "", "options": [   # navigation
        ("GXY", "GalaxyMapOpen"), ("SYS", "SystemMapOpen"), ("NEXT", "TargetNextRouteSystem"),
        ("CRUI", "Supercruise"), ("JUMP", "Hyperspace")]},
    "WING": {"code": "WG", "num": "", "options": [   # wing
        ("WG-1", "TargetWingman0"), ("WG-2", "TargetWingman1"), ("WG-3", "TargetWingman2"),
        ("WGNV", "WingNavLock"), ("WG-T", "SelectTargetsTarget")]},
    "PAGE": {"code": "BC", "num": "", "options": [   # the web page's tabs ("@tab:" = page tab, not a key), DSG and MK
        ("HOME", "@tab:home"), ("NAV", "@tab:nav"), ("CTRS", "@tab:contracts"), ("DSG", "@dsg"), ("MK", "@mk")]},
    "ON_OFF": {"code": "ON", "num": "", "options": [   # toggles
        ("CARG", "ToggleCargoScoop"), ("NVG", "NightVisionToggle"), ("LAND", "LandingGearToggle"),
        ("HUD", "!HideHUD"), ("MODE", "PlayerHUDModeToggle")]},
}

# Which menu each function button opens. The web page's menu is on ILS, navigation on D/L and the wing
# menu on BCN (the menus keep their own names: PAGE, NAV, WING).
UFC_MENU_BUTTONS = {"AP": "AP", "IFF": "IFF", "TCN": "TCN", "ILS": "PAGE", "DL": "NAV", "BCN": "WING", "ON_OFF": "ON_OFF"}
UFC_BUTTON_OF = {menu: button for button, menu in UFC_MENU_BUTTONS.items()}

# Keys the game has built in, which don't appear in the bindings file.
FIXED_KEYS = {
    "!HideHUD": (("Key_LeftControl", "Key_LeftAlt"), "Key_G"),   # Elite's hide-HUD shortcut
    "!Paste": (("Key_LeftControl",), "Key_V"),                  # paste (the copy button's second press)
}

# IP button: request docking through the left panel (same sequence VoiceAttack used).
DOCKING_MACRO = ["FocusLeftPanel", "CycleNextPanel", "CycleNextPanel", "UI_Right", "UI_Select",
                 "CyclePreviousPanel", "CyclePreviousPanel", "FocusLeftPanel"]

KEY_HOLD = 0.10       # seconds each key is held (VoiceAttack used 0.1)
MACRO_HOLD = 0.05     # shorter hold for the docking sequence
MACRO_GAP = 0.20      # pause between docking steps
MODIFIER_LEAD = 0.03  # Ctrl/Alt/Shift go down this long before the key

# Elite binding key names -> keyboard scan codes (set 1). (code, extended)
# Elite stores keys by physical position, so these hold for any keyboard layout.
SCAN_CODES = {
    "Key_Escape": (0x01, False), "Key_1": (0x02, False), "Key_2": (0x03, False), "Key_3": (0x04, False),
    "Key_4": (0x05, False), "Key_5": (0x06, False), "Key_6": (0x07, False), "Key_7": (0x08, False),
    "Key_8": (0x09, False), "Key_9": (0x0A, False), "Key_0": (0x0B, False), "Key_Minus": (0x0C, False),
    "Key_Equals": (0x0D, False), "Key_Backspace": (0x0E, False), "Key_Tab": (0x0F, False),
    "Key_Q": (0x10, False), "Key_W": (0x11, False), "Key_E": (0x12, False), "Key_R": (0x13, False),
    "Key_T": (0x14, False), "Key_Y": (0x15, False), "Key_U": (0x16, False), "Key_I": (0x17, False),
    "Key_O": (0x18, False), "Key_P": (0x19, False), "Key_LeftBracket": (0x1A, False),
    "Key_RightBracket": (0x1B, False), "Key_Enter": (0x1C, False), "Key_LeftControl": (0x1D, False),
    "Key_A": (0x1E, False), "Key_S": (0x1F, False), "Key_D": (0x20, False), "Key_F": (0x21, False),
    "Key_G": (0x22, False), "Key_H": (0x23, False), "Key_J": (0x24, False), "Key_K": (0x25, False),
    "Key_L": (0x26, False), "Key_SemiColon": (0x27, False), "Key_Apostrophe": (0x28, False),
    "Key_Grave": (0x29, False), "Key_LeftShift": (0x2A, False), "Key_BackSlash": (0x2B, False),
    "Key_Hash": (0x2B, False), "Key_Z": (0x2C, False), "Key_X": (0x2D, False), "Key_C": (0x2E, False),
    "Key_V": (0x2F, False), "Key_B": (0x30, False), "Key_N": (0x31, False), "Key_M": (0x32, False),
    "Key_Comma": (0x33, False), "Key_Period": (0x34, False), "Key_Slash": (0x35, False),
    "Key_RightShift": (0x36, False), "Key_Numpad_Multiply": (0x37, False), "Key_LeftAlt": (0x38, False),
    "Key_Space": (0x39, False), "Key_CapsLock": (0x3A, False),
    "Key_F1": (0x3B, False), "Key_F2": (0x3C, False), "Key_F3": (0x3D, False), "Key_F4": (0x3E, False),
    "Key_F5": (0x3F, False), "Key_F6": (0x40, False), "Key_F7": (0x41, False), "Key_F8": (0x42, False),
    "Key_F9": (0x43, False), "Key_F10": (0x44, False), "Key_NumLock": (0x45, False),
    "Key_ScrollLock": (0x46, False), "Key_Numpad_7": (0x47, False), "Key_Numpad_8": (0x48, False),
    "Key_Numpad_9": (0x49, False), "Key_Numpad_Subtract": (0x4A, False), "Key_Numpad_4": (0x4B, False),
    "Key_Numpad_5": (0x4C, False), "Key_Numpad_6": (0x4D, False), "Key_Numpad_Add": (0x4E, False),
    "Key_Numpad_1": (0x4F, False), "Key_Numpad_2": (0x50, False), "Key_Numpad_3": (0x51, False),
    "Key_Numpad_0": (0x52, False), "Key_Numpad_Decimal": (0x53, False), "Key_OEM_102": (0x56, False),
    "Key_F11": (0x57, False), "Key_F12": (0x58, False),
    "Key_Numpad_Enter": (0x1C, True), "Key_RightControl": (0x1D, True), "Key_Numpad_Divide": (0x35, True),
    "Key_RightAlt": (0x38, True), "Key_Home": (0x47, True), "Key_UpArrow": (0x48, True),
    "Key_PageUp": (0x49, True), "Key_LeftArrow": (0x4B, True), "Key_RightArrow": (0x4D, True),
    "Key_End": (0x4F, True), "Key_DownArrow": (0x50, True), "Key_PageDown": (0x51, True),
    "Key_Insert": (0x52, True), "Key_Delete": (0x53, True), "Key_LeftWin": (0x5B, True),
    "Key_RightWin": (0x5C, True), "Key_Apps": (0x5D, True),
}


def key_label(combo) -> str:
    """(('Key_LeftAlt',), 'Key_Q') -> 'LeftAlt+Q'"""
    mods, key = combo
    return "+".join(k.replace("Key_", "") for k in (*mods, key))


class EliteBindings:
    """Reads the active Elite bindings file and looks keyboard keys up by action name.
    Re-reads it automatically if you change your bindings in the game."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.files = []
        self.keys = {}          # action -> list of (modifiers tuple, key)
        self.joy = {}           # (device - "VVVVPPPP" or Elite's name for it - , "Joy_12" / "Joy_POV1Up") -> actions
        self.stamp = None
        self.checked = 0.0
        self.lock = threading.Lock()

    def _active_files(self):
        names = []
        for start in ("StartPreset.4.start", "StartPreset.start"):
            try:
                lines = (self.folder / start).read_text(encoding="utf-8-sig", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                line = line.strip()
                if line and line not in names:
                    names.append(line)
            break
        files = []
        for name in names:
            best = None
            for path in self.folder.glob(f"{name}.*.binds"):
                m = re.fullmatch(re.escape(name) + r"\.(\d+)\.(\d+)\.binds", path.name)
                if m:
                    version = (int(m.group(1)), int(m.group(2)))
                    if best is None or version > best[0]:
                        best = (version, path)
            if best is None and (self.folder / f"{name}.binds").exists():
                best = ((0, 0), self.folder / f"{name}.binds")
            if best:
                files.append(best[1])   # built-in presets (e.g. KeyboardMouseOnly) have no file
        return files

    def load(self):
        import xml.etree.ElementTree as ET
        files = self._active_files()
        keys, joy = {}, {}
        for path in files:
            try:
                root = ET.parse(path).getroot()
            except (OSError, ET.ParseError) as exc:
                log(f"Couldn't read bindings file {path.name}: {exc}")
                continue
            for action in root:
                for slot in ("Primary", "Secondary"):
                    el = action.find(slot)
                    if el is not None and (el.get("Key") or "").startswith("Joy_"):   # (a controller's: 4 Setup > Controls warns)
                        joy.setdefault(((el.get("Device") or "").upper(), el.get("Key")), []).append(action.tag)
                    if el is None or el.get("Device") != "Keyboard" or not el.get("Key"):
                        continue
                    mods = tuple(m.get("Key") for m in el.findall("Modifier") if m.get("Device") == "Keyboard")
                    keys.setdefault(action.tag, []).append((mods, el.get("Key")))
        with self.lock:
            self.files, self.keys, self.joy = files, keys, joy
            self.stamp = self._stamp()
        if files:
            log(f"Bindings: {', '.join(p.name for p in files)} ({len(keys)} keyboard actions)")
        else:
            log(f"No Elite bindings file found in {self.folder} (use --bindings-dir)")
        return bool(files)

    def joy_actions(self, dev, key):
        """What Elite does with a controller's button (dev: "VVVV:PPPP"; key: "Joy_12", "Joy_POV1Up") - its own
        actions, spaced out ("CycleNextTarget" -> "Cycle Next Target")."""
        if not key or not re.fullmatch(r"[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}", dev or ""):
            return []
        with self.lock:
            acts = self.joy.get((dev.replace(":", "").upper(), key), [])
        return [re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", a) for a in acts]

    def _stamp(self):
        try:
            return tuple((p.name, p.stat().st_mtime) for p in self._active_files())
        except OSError:
            return None

    def refresh(self):
        """Reload if the bindings changed; checks at most every 2 seconds."""
        now = time.time()
        if now - self.checked < 2:
            return
        self.checked = now
        if self._stamp() != self.stamp:
            log("Bindings changed - reloading.")
            self.load()

    def lookup(self, action):
        """Best keyboard key for an action, or None if it has no keyboard binding."""
        if action in FIXED_KEYS:
            return FIXED_KEYS[action]
        with self.lock:
            options = [c for c in self.keys.get(action, []) if c[1] in SCAN_CODES
                       and all(m in SCAN_CODES for m in c[0])]
        if not options:
            return None
        # prefer keys off the number pad, then fewer modifiers
        return min(options, key=lambda c: ("Numpad" in c[1], len(c[0])))


# ---- sending keypresses (Windows SendInput with scan codes) ----
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _ULONG_PTR = ctypes.c_size_t

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]

    class _INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    _kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                     ctypes.POINTER(wintypes.DWORD))
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    def _send_scan(code, extended, up):
        flags = 0x0008 | (0x0001 if extended else 0) | (0x0002 if up else 0)   # SCANCODE, EXTENDED, KEYUP
        inp = _INPUT(type=1, ki=_KEYBDINPUT(wVk=0, wScan=code, dwFlags=flags, time=0, dwExtraInfo=0))
        if _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT)) != 1:
            raise OSError(f"SendInput failed (error {ctypes.get_last_error()})")

    def foreground_process() -> str:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = _kernel32.OpenProcess(0x1000, False, pid.value)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
            return ""
        finally:
            _kernel32.CloseHandle(handle)
else:
    def _send_scan(code, extended, up):   # not Windows: report instead of pressing
        pass

    def foreground_process() -> str:
        return ""


class KeySender(threading.Thread):
    """Presses keys one job at a time on its own thread, so nothing else waits."""

    def __init__(self, bindings: EliteBindings, require_focus=True, dry_run=False):
        super().__init__(daemon=True, name="keys")
        self.bindings, self.require_focus = bindings, require_focus
        self.dry_run = dry_run or sys.platform != "win32"
        self.jobs = queue.Queue()
        self.sent = []          # (label, combos) of each job sent, for tests and diagnostics
        self._warned_focus = 0.0

    def press(self, action, label=""):
        self.jobs.put((label or action, [action], KEY_HOLD, 0.0))

    def macro(self, actions, label):
        self.jobs.put((label, list(actions), MACRO_HOLD, MACRO_GAP))

    def elite_in_front(self) -> bool:
        if not self.require_focus or self.dry_run:
            return True
        return foreground_process() == ELITE_PROCESS

    def run(self):
        while True:
            label, actions, hold, gap = self.jobs.get()
            try:
                self._do(label, actions, hold, gap)
            except Exception as exc:
                log(f"Keypress failed for {label}: {exc}")

    def _do(self, label, actions, hold, gap):
        self.bindings.refresh()
        combos = []
        for action in actions:
            combo = self.bindings.lookup(action)
            if combo is None:
                log(f"UFC: {label} - '{action}' has no keyboard binding in Elite, so nothing was sent.")
                return
            combos.append(combo)
        if not self.elite_in_front():
            if time.time() - self._warned_focus > 5:
                log(f"UFC: {label} not sent - Elite isn't the active window.")
                self._warned_focus = time.time()
            return
        desc = ", ".join(key_label(c) for c in combos)
        log(f"UFC: {label} -> {desc}" + (" (not sent: not Windows / dry run)" if self.dry_run else ""))
        self.sent.append((label, combos))
        for i, combo in enumerate(combos):
            if i and gap:
                time.sleep(gap)
            if i and not self.elite_in_front():   # switched away mid-sequence: the rest would go to another program
                log(f"UFC: {label} stopped after {i} of {len(combos)} keys - Elite isn't the active window any more.")
                return
            self._tap(combo, hold)

    def _key(self, name, up):
        if not self.dry_run:
            _send_scan(*SCAN_CODES[name], up=up)

    def _tap(self, combo, hold):
        """Modifiers down, key down, hold, then release everything in reverse order."""
        mods, key = combo
        down = []
        try:
            for m in mods:
                down.append(m)          # noted first, so it's released even if the press fails
                self._key(m, up=False)
            if mods:
                time.sleep(MODIFIER_LEAD)
            down.append(key)
            self._key(key, up=False)
            time.sleep(hold)
        finally:
            for k in reversed(down):   # always release, even if something went wrong
                try:
                    self._key(k, up=True)
                except OSError:
                    pass
                time.sleep(0.01)


# ---- the UFC display, via SimApp Pro ----
_SIMAPP_DELIM = "-----------------------------------------"


def _simapp_field(key, value) -> str:
    return f"{_SIMAPP_DELIM}\n{key}\n{value}\n"


def _simapp_com(value: str) -> str:
    # SimApp shows 10-19 specially: "`0" == 10
    return "`" + str(int(value) % 10) if value.isdigit() and 10 <= int(value) < 20 else value


def simapp_ufc_text(options, com1, com2, scratch_num, scratch1, scratch2, cue=None) -> str:
    """The Hornet UFC text block SimApp Pro expects (same format as ufc.py).
    cue = option window (1-5) to mark with ':', or None for no marker."""
    out = "".join(_simapp_field(f"UFC_OptionDisplay{i + 1}", options[i]) for i in range(5))
    out += _simapp_field("UFC_Comm1Display", _simapp_com(com1))
    out += _simapp_field("UFC_Comm2Display", _simapp_com(com2))
    out += _simapp_field("UFC_ScratchPadNumberDisplay", scratch_num)
    out += _simapp_field("UFC_ScratchPadString1Display", scratch1)
    out += _simapp_field("UFC_ScratchPadString2Display", scratch2)
    out += "".join(_simapp_field(f"UFC_OptionCueing{i}", ":" if cue is not None and str(i) == str(cue) else "")
                   for i in range(1, 6))
    return out


class UFCDisplay:
    def __init__(self, host=SIMAPP_HOST, port=SIMAPP_PORT):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send(self, msg):
        try:
            self.sock.sendto(json.dumps(msg).encode("utf-8"), self.addr)
        except OSError as exc:
            log(f"Couldn't reach SimApp Pro: {exc}")

    def hello(self):
        for msg in ({"func": "net", "msg": "ready"}, {"func": "mission", "msg": "ready"},
                    {"func": "mission", "msg": "start"}, {"func": "mod", "msg": "FA-18C_hornet"}):
            self._send(msg)

    def show(self, options, scratch_num="", scratch1="", scratch2="", com1="1", com2="1", cue=None):
        text = simapp_ufc_text(options, com1, com2, scratch_num, scratch1, scratch2, cue)
        self._send({"args": {"FA-18C_hornet": text}, "func": "addCommon", "timestamp": 0.00})
        self._send({"args": {"0": {"109": "0.95"}}, "func": "addOutput", "timestamp": 0})   # brightness


UFC_LISTS = ("targets", "ocor", "syst", "hist", "chist")   # the lists the COMM1 knob moves through (Contracts' Active
#   page, OCOR, the System list or map, Nav's Hist, Contracts' History)
UFC_UPLINK = "uplink"        # the System list's COMM1 stop after its last row: the System Data Uplink Synchronise button
UFC_SOURCES = ("src:spansh", "src:edsm")   # ... and the two after it: the Spansh Uplink and EDSM Uplink toggles
SYST_BUTTONS = (UFC_UPLINK,) + UFC_SOURCES   # (not items: COM1 / COM2 don't count them)
UFC_REMOTE = "remote"        # the System list's first COMM1 stop, above its rows: CURRENT SYSTEM / REMOTE (not an item either)
UFC_FX_VEHICLES = ("ship", "srv", "fighter", "nomad")   # whose start-ups run the displays' self-test
UFC_PAGE_FX = ("off", "ucec", "") + UFC_FX_VEHICLES      # what a page's screens ask of the displays (see UFCController.screen_tick)
UFC_FX_LONGEST = 15.0        # seconds a vehicle's self-test can keep the displays, at most (the page ends it sooner)
UFC_PAGE_GRACE = 2.0         # seconds a closed page still counts as open (a reload, or a phone's connection blinking)
UFC_FX_RATE = 8              # test pattern frames a second
UFC_FX_PATTERNS = ["8   ", " 8  ", "  8 ", "   8", "----", "0000", "____", "8888", "1111", "AAAA"]   # what the option displays cycle through


CLIP_PASTE_WINDOW = 120     # seconds after a copy that pressing the button again pastes
_CLIP_MEMORY = {"text": ""}   # where the "clipboard" is when this isn't Windows (the tests)


def set_clipboard(text: str) -> bool:
    """Put text on this PC's clipboard (Windows); elsewhere it's only remembered. True if it worked."""
    if sys.platform != "win32":
        _CLIP_MEMORY["text"] = text
        return True
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes, user32.OpenClipboard.restype = [wintypes.HWND], wintypes.BOOL
    user32.SetClipboardData.argtypes, user32.SetClipboardData.restype = [wintypes.UINT, wintypes.HANDLE], wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes, kernel32.GlobalAlloc.restype = [wintypes.UINT, ctypes.c_size_t], wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes, kernel32.GlobalLock.restype = [wintypes.HGLOBAL], wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    data = text.encode("utf-16-le") + b"\0\0"
    for _ in range(10):   # another program may have it open for a moment
        if user32.OpenClipboard(None):
            break
        time.sleep(0.03)
    else:
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(0x0002, len(data))   # GMEM_MOVEABLE
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):   # CF_UNICODETEXT (the clipboard owns it once set)
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


class ClipButton:
    """The copy / paste button beside a system's name (OCOR, Contracts). The first press puts the name on
    this PC's clipboard (whichever screen it's pressed on); pressing it again for the same name within
    CLIP_PASTE_WINDOW pastes it into Elite with Ctrl+V - into the galaxy map's search box, say - if Elite is
    the active window (as it stays when the press is the UFC's: a short COMM2 pull on those tabs). A UFC
    pull reaches every open page, so each says which pull it is, and only the first counts."""

    def __init__(self, bus, board):
        self.bus, self.board = bus, board
        self.lock = threading.Lock()
        self.text, self.t, self.state, self.n, self.pulls = "", 0.0, "", 0, deque(maxlen=50)

    def press(self, text, pull=None):
        text = re.sub(r"\s+", " ", str(text or "")).strip()[:120]
        if not text:
            return 400, {"ok": False, "why": "nothing to copy"}
        with self.lock:
            if pull is not None:
                if pull in self.pulls:
                    return 200, {"ok": True, "did": "already"}   # another page has acted on this pull
                self.pulls.append(pull)
            now = time.time()
            if self.state == "copied" and self.text == text and now - self.t < CLIP_PASTE_WINDOW:
                keys = getattr(self.board, "keys", None)
                if keys is None:
                    ok, why = False, "the UFC is off, so no keys can be sent"
                elif not keys.elite_in_front():
                    ok, why = False, "Elite isn't the active window"
                else:
                    keys.press("!Paste", f"Paste {text}")
                    ok, why = True, ""
                did = "paste"
                if ok:
                    self.state, self.t = "pasted", now
            else:
                ok = set_clipboard(text)
                why, did = ("" if ok else "couldn't reach the clipboard"), "copy"
                self.text, self.t, self.state = text, now, ("copied" if ok else "")
            self.n += 1
            clip = {"text": self.text, "state": self.state, "did": did, "ok": ok, "why": why, "n": self.n}
        log(f"Copy button: {text} - {'copied to the clipboard' if did == 'copy' and ok else 'pasted into Elite' if ok else why}.")
        self.bus.update(clip=clip)
        return 200, {"ok": ok, "did": did, "why": why}


class UIBus:
    """One record of where you are on the page and what the UFC is doing, shared by every open
    page and the UFC. Pages get changes instantly over /api/events.

    Where you are is a tab and a page (sub-tab) within it - see PAGE_TABS. A page reports it
    when you change it there (no push to other pages); the UFC changing it is pushed, with
    view_n bumped, and every page follows."""

    def __init__(self):
        self.cond = threading.Condition()
        self.version = 0
        self.data = {"run": f"{time.time_ns():x}",                    # this run of the script: a page that sees a new one starts afresh
                     "menu": "",                                     # the UFC menu showing (PAGE drives the page)
                     "view": {"tab": None, "sub": 1}, "view_n": 0,   # the UFC moved the page here
                     "cursors": {name: None for name in UFC_LISTS},   # the UFC knob's highlight in each list (PAGE menu)
                     "pick": None, "pick_n": 0,                       # a COMM1 pull: {"list": ..., "key": ...}
                     "c2pull_n": 0, "c2long_n": 0,                    # COMM2 pulls, short and 2-second
                     "knob1_pos": 0, "c1pull_n": 0,                   # COMM1 on a page it works itself (PAGE_KNOB1): clicks and pulls
                     "jump_n": 0,                                     # a hyperspace jump started or ended: refresh now
                     "state_n": 0,                                    # anything new (Status.json, the journal...): fetch the state now
                     "clip": {},                                     # the copy / paste button's last press (ClipButton)
                     "dials": {},                                    # where each dial sits, 0 (anticlockwise) - 1: the page makes them speed controls
                     "key_n": 0, "keys": [],                          # the keypad, to a page typing with it (Tgt's MANUAL): [[n, key]...], the last few
                     "dsg_n": 0, "mk_n": 0,                           # the page menu's DSG and MK (the page showing designates; an open page marks)
                     "scroll_pos": 0,   # running total of COMM2 clicks (+1 clockwise, -1 anticlockwise)
                     "scroll_n": 0, "scroll_turns": [],   # ... and each turn of it, counted: [[n, clicks]...], the last few
                     "timer": dict(TIMER_IDLE)}           # the stopwatch / countdown timer (2 Nav > HSI): see timer_op
        self.view = {"tab": None, "sub": 1}   # where you are, from whichever moved last (a page or the UFC)
        self.subs = {}                         # the page last shown on each tab
        self.keysubs = {}                      # (tab, sub-tab) -> the page last shown in that sub-tab (Syst: list or map)
        self.picks = {}                        # what was last picked in each list, on any page or by the UFC
        self.listeners = []                    # called when a page reports what it's showing
        self.plock = threading.Lock()
        self.page_list = {}   # page id -> {"fx", "t", "conns", "gone"}: the open pages, in the order they opened
        self.timer_done = OrderedDict()   # timer ops already acted on for a UFC press (its token): every open page answers it

    # ---- the open pages: the UFC's displays follow the first one opened ----
    def page_open(self, pid):
        with self.plock:
            p = self.page_list.get(pid)
            if p:
                p["conns"], p["gone"] = p["conns"] + 1, None
            else:
                self.page_list[pid] = {"fx": "off", "t": time.time(), "conns": 1, "gone": None}

    def page_close(self, pid):
        with self.plock:
            p = self.page_list.get(pid)
            if p:
                p["conns"] = max(0, p["conns"] - 1)
                if not p["conns"]:
                    p["gone"] = time.time()

    def page_cue(self, pid, cue):
        """A page says what its dials are doing ({"z": "Z+" | "Z-" | "", "t": "<<" | ">>" | "UP" | "DN" | ""}): the UFC's
        scratchpad shows it while the page menu is up."""
        with self.plock:
            p = self.page_list.setdefault(pid, {"fx": "off", "t": 0.0, "conns": 0, "gone": time.time()})
            p["cue"] = cue

    def driver_cue(self):
        """The dial cue of the page the displays follow ({} if none)."""
        with self.plock:
            for p in self.page_list.values():
                return dict(p.get("cue") or {})
        return {}

    def page_fx(self, pid, fx):
        """A page says what its screens ask of the UFC's displays (one of UFC_PAGE_FX)."""
        with self.plock:
            p = self.page_list.setdefault(pid, {"fx": "off", "t": 0.0, "conns": 0, "gone": time.time()})
            if p["fx"] != fx:
                p["fx"], p["t"] = fx, time.time()

    def page_screen(self, now=None):
        """(fx, since) of the page the displays follow - the first opened that's still open, or has only
        just closed - or None if there's none."""
        now = now or time.time()
        with self.plock:
            for pid in [k for k, p in self.page_list.items() if p["gone"] and now - p["gone"] > UFC_PAGE_GRACE]:
                del self.page_list[pid]
            for p in self.page_list.values():
                return p["fx"], p["t"]
        return None

    @property
    def pages(self):
        """Pages connected (to /api/events) right now."""
        with self.plock:
            return sum(1 for p in self.page_list.values() if p["conns"])

    def _remember(self):
        tab, sub = self.view["tab"], self.view["sub"]
        self.subs[tab] = sub
        keys = PAGE_SUBTABS.get(tab) or ()
        if 1 <= sub <= len(keys):
            self.keysubs[(tab, keys[sub - 1])] = sub

    def page(self):
        """The name of the page showing ("list", "hist", "active"...), or None."""
        tab, sub = self.view["tab"], self.view["sub"]
        pages = PAGE_TABS.get(tab) or ()
        return pages[sub - 1] if 1 <= sub <= len(pages) else None

    def note_view(self, tab=None, sub=None, picks=None):
        """A page says where it is, or what it has picked (no push to other pages)."""
        if tab:
            self.view = {"tab": tab, "sub": sub or self.subs.get(tab, 1)}
            self._remember()
        for name, key in (picks or {}).items():
            self.picks[name] = key
        for fn in self.listeners:
            try:
                fn()
            except Exception as exc:
                log(f"UFC display update failed: {exc}")

    def set_view(self, tab, sub=None):
        """The UFC moves the page: every open page follows (to the tab's last page unless given)."""
        sub = sub or self.subs.get(tab, 1)
        self.view = {"tab": tab, "sub": sub}
        self._remember()
        with self.cond:
            n = self.data["view_n"] + 1
        self.update(view=dict(self.view), view_n=n)

    def pick(self, name, key):
        """A COMM1 pull picks the highlighted item in a list."""
        self.picks[name] = key
        with self.cond:
            n = self.data["pick_n"] + 1
        self.update(pick={"list": name, "key": key}, pick_n=n)

    def bump(self, field):
        with self.cond:
            n = self.data.get(field, 0) + 1
        self.update(**{field: n})
        return n

    # ---- the stopwatch / countdown timer: the T-6A's clock (its SEL and CTL buttons), on the HSI ----
    def timer_op(self, body, now=None):
        """An op on the timer: {"op": "sel" | "ctl" | "set" | "clr", "mode"?: "et" | "cd" (sel), "cd"?: seconds (set),
        "u"?: the UFC press it answers - each acted on once, whichever pages answer it}. The timer (every page has it,
        as "timer"): {"mode": "et" (the stopwatch, counting up) | "cd" (the countdown), "run", "t0": when it started (this
        PC's clock, s), "cd": the countdown's time (s; None: none set), "ack": its alarm seen}. SEL: the other mode - not
        while it runs (a countdown that's reached zero: SEL stops its alarm flashing). CTL: start it - and again, reset it
        (the stopwatch to zero, the countdown cleared, to set again; one with no time set: why "set", and the page asks
        for one). SET: the countdown's time (stopped), CLR: none. -> {"ok", "timer", "why"?, "did"?}"""
        u = body.get("u") if isinstance(body.get("u"), str) and body.get("u") else None
        with self.cond:
            if u and u[:40] in self.timer_done:
                return dict(self.timer_done[u[:40]], did="already")
            t, op, now = dict(self.data["timer"]), body.get("op"), now or time.time()
            out = {"ok": True}
            if op == "sel":
                up = t["run"] and t["mode"] == "cd" and t["cd"] is not None and now - t["t0"] >= t["cd"]
                if up and not t["ack"]:
                    t["ack"], out["did"] = True, "ack"
                elif t["run"]:
                    out = {"ok": False, "why": "running"}
                else:
                    mode = body.get("mode") if body.get("mode") in ("et", "cd") else ("cd" if t["mode"] == "et" else "et")
                    t.update(mode=mode, t0=None, ack=False)
            elif op == "ctl":
                if t["run"]:   # (again: reset - the countdown cleared, to set again)
                    t.update(run=False, t0=None, ack=False, cd=None if t["mode"] == "cd" else t["cd"])
                    out["did"] = "reset"
                elif t["mode"] == "cd" and t["cd"] is None:
                    out = {"ok": False, "why": "set"}
                else:
                    t.update(run=True, t0=now, ack=False)
                    out["did"] = "start"
            elif op == "set":
                v = body.get("cd")
                if not isinstance(v, (int, float)) or isinstance(v, bool) or not 1 <= v <= TIMER_MAX:
                    out = {"ok": False, "why": "cd"}
                else:
                    t.update(mode="cd", run=False, t0=None, ack=False, cd=int(v))
            elif op == "clr":
                if t["run"]:
                    out = {"ok": False, "why": "running"}
                elif t["mode"] == "cd":
                    t["cd"] = None
            else:
                out = {"ok": False, "why": "op"}
            out["timer"] = t
            if u:
                self.timer_done[u[:40]] = out
                while len(self.timer_done) > 64:
                    self.timer_done.popitem(last=False)
        if out["ok"]:
            self.update(timer=t)
        return out

    def update(self, **changes):
        with self.cond:
            self.data.update(changes)
            self.version += 1
            self.cond.notify_all()

    def dial(self, name, pos):
        with self.cond:
            dials = dict(self.data["dials"], **{name: round(min(1.0, max(0.0, pos)), 3)})
        self.update(dials=dials)

    def scroll(self, clicks):
        # a running total, so a page that misses an update still scrolls the right amount - and each turn counted (a page
        # acting on the board for each, as the HSI's steer-to point, names it by its count: two pages, acted on once)
        with self.cond:
            total = self.data["scroll_pos"] + clicks
            n = self.data["scroll_n"] + 1
            turns = (self.data["scroll_turns"] + [[n, clicks]])[-KEYPAD_KEEP:]
        self.update(scroll_pos=total, scroll_n=n, scroll_turns=turns)

    def knob1(self, clicks):   # COMM1 on a page that works it itself: a running total too
        with self.cond:
            total = self.data["knob1_pos"] + clicks
        self.update(knob1_pos=total)

    def key(self, key):   # a keypad key, to the page typing with it (the last few kept, so a page that misses a push catches up)
        with self.cond:
            n = self.data["key_n"] + 1
            keys = (self.data["keys"] + [[n, key]])[-KEYPAD_KEEP:]
        self.update(key_n=n, keys=keys)

    def page_keys(self, pid, on, show=None):
        """A page says it's typing with the keypad (on), and what the scratchpad should show meanwhile:
        {"s1", "s2", "num"}."""
        with self.plock:
            p = self.page_list.setdefault(pid, {"fx": "off", "t": 0.0, "conns": 0, "gone": time.time()})
            p["keys"] = bool(on)
            p["entry"] = dict(show or {}) if on else {}

    def keypad_wanted(self):
        """True while the page showing types with the keypad (an open page has said so, on a page that does)."""
        if self.page() not in PAGE_KEYPAD:
            return False
        with self.plock:
            return any(p.get("keys") and p["conns"] for p in self.page_list.values())

    def knob1_wanted(self):
        """True while the page showing has COMM1 too (it said so with the keypad: 1 Syst's REMOTE list, scrolled with it)."""
        if self.page() not in PAGE_KEYPAD:
            return False
        with self.plock:
            return any(p.get("keys") and p["conns"] and (p.get("entry") or {}).get("knob1") for p in self.page_list.values())

    def page_scratch(self, pid, show):
        """A page's own words for the scratchpad while it shows (PAGE_SCRATCH: Atk's countdown): {"s1", "s2", "num"}, or {}."""
        with self.plock:
            p = self.page_list.setdefault(pid, {"fx": "off", "t": 0.0, "conns": 0, "gone": time.time()})
            p["scratch"] = dict(show or {})

    def driver_entry(self):
        """What the page showing wants on the scratchpad: what's being typed (PAGE_KEYPAD), or its own words
        (PAGE_SCRATCH). {} if nothing."""
        page = self.page()
        with self.plock:
            for p in self.page_list.values():
                if page in PAGE_KEYPAD and p.get("keys") and p.get("entry"):
                    return dict(p["entry"])
                if page in PAGE_SCRATCH and p.get("scratch") and p["conns"]:
                    return dict(p["scratch"])
        return {}

    def snapshot(self):
        with self.cond:
            return self.version, dict(self.data)

    def wait(self, seen, timeout=15.0):
        """Block until something changes after version `seen`; None on timeout."""
        with self.cond:
            if self.version == seen:
                self.cond.wait(timeout)
            if self.version == seen:
                return None
            return self.version, dict(self.data)


class UFCController:
    """What each UFC button does. One record of the current menu, so the display
    and the keys can't disagree. In the PAGE menu (the ILS button) the UFC drives the web page:
    option buttons pick the page's tab (the ':' marks the active one; pressing the
    active one again steps to its next sub-tab), and the keypad's digits a sub-tab of
    the tab showing (Syst's digit again flips its list and map); the COMM1 knob moves
    through the list on the page showing - contracts, the briefing's objectives, the
    system's bodies and stations, or a history page's rows (anticlockwise = up,
    clockwise = down) - and pulling it picks the highlighted one; the COMM2 knob
    scrolls the right-hand panel (the details on Contracts, the local situation on
    Home, the orders on OCOR), and on Syst and the history pages steps through the
    switch, toggles and buttons, then the details."""

    def __init__(self, display: UFCDisplay, sender: KeySender, start_menu=UFC_START_MENU,
                 board=None, bus=None, ocor=None):
        self.display, self.sender = display, sender
        self.board, self.bus, self.ocor = board, bus, ocor
        self.menu = start_menu if start_menu in UFC_MENUS else "NAV"
        self.connected = False
        self.cursors = {name: None for name in UFC_LISTS}   # the knob's highlight in each list
        self.screen, self.screen_t0, self.fx_frame, self.screen_sent = None, 0.0, None, 0.0   # see screen_tick
        self.cue_shown = ({}, {})   # the dial cue (and what's being typed) last put on the scratchpad
        if self.bus:
            self.bus.update(menu=self.menu)
            self.bus.listeners.append(self._page_changed)

    # ---- the lists the knob moves through ----
    def _tab(self):
        return self.bus.view["tab"] if self.bus else None

    def _list(self):
        """The list the COMM1 knob works on: the page showing's (PAGE_LISTS), else the contracts."""
        return PAGE_LISTS.get(self.bus.page() if self.bus else None, "targets")

    def _keys(self, name):
        if name == "ocor":
            return self.ocor.ids() if self.ocor else []   # those still to do (all of them if every one is done)
        if not self.board:
            return []
        if name in ("hist", "chist"):   # Nav's Hist, Contracts' History: as the page lists them (its toggles)
            hist = getattr(self.board, "history", None)
            return hist.keys("nav" if name == "hist" else "contracts") if hist else []
        if name == "syst":   # the map shows them in its own order; the list ends with the uplink button
            map_view = bool(self.bus) and self.bus.keysubs.get(("nav", 1), 1) == 2
            keys = self.board.systab.keys(map_view=map_view)
            if map_view:
                return keys
            return [UFC_REMOTE] + (keys + list(SYST_BUTTONS) if keys else [])   # (REMOTE first: there even with no data)
        return self.board.contracts.keys()

    def _sync(self, name):
        """Keep a list's highlight on a real item (a new paste or a jump can change the list):
        else the last one picked, else the first. On the map, a surface site hands over to its planet."""
        keys = self._keys(name)
        cur = self.cursors[name]
        if cur in keys:
            return
        last = self.bus.picks.get(name) if self.bus else None
        if name == "syst":
            host = (lambda k: self.board.systab.host(k) if self.board and k else None)
            first = next((k for k in keys if k != UFC_REMOTE), keys[0] if keys else None)
            self.cursors[name] = next((k for k in (host(cur), last, host(last)) if k and k in keys and k != UFC_REMOTE), first)
        else:
            self.cursors[name] = last if last in keys else (keys[0] if keys else None)

    def _page_changed(self):
        if self.menu == "PAGE" and self.connected:
            for name in UFC_LISTS[1:]:
                self._sync(name)
            self.show_menu()   # keeps the ':' on the tab the page is showing
            self._publish()

    def show_menu(self):
        if self.bus and self.screen != "menu":   # the displays are blank, or a page's start-up has them
            return
        page = UFC_MENUS[self.menu]
        labels = [label for label, _ in page["options"]]
        code = (page["code"] + "  ")[:2]
        com1 = com2 = "1"
        cue = None
        s1, s2 = code[0].strip(), code[1].strip()
        dial = self.bus.driver_cue() if self.bus and self.menu == "PAGE" else {}
        entry = self.bus.driver_entry() if self.bus and self.menu == "PAGE" else {}
        self.cue_shown = (dial, entry)
        num = page["num"]
        if dial.get("z") or dial.get("t"):   # a dial zooming / turning: Z+ or Z-, and << >> UP DN
            s1, s2 = dial.get("z") or "", dial.get("t") or ""
        if entry:   # typing on the page: what's typed so far
            s1, s2, num = str(entry.get("s1") or "")[:2], str(entry.get("s2") or "")[:2], str(entry.get("num") or "")[:8]
        if self.menu == "PAGE":   # COM1 = highlighted item's number, COM2 = how many in the list
            name = self._list()
            keys, cur = [k for k in self._keys(name) if k not in SYST_BUTTONS and k != UFC_REMOTE], self.cursors[name]   # (the buttons aren't items)
            com1 = str(keys.index(cur) + 1) if cur in keys else ""
            com2 = str(len(keys))
            tab = self._tab()
            for i, (_, action) in enumerate(page["options"], 1):
                if tab and action == f"@tab:{tab}":
                    cue = i   # ':' beside the active tab's option window
            com1, com2 = entry.get("com1") or com1, entry.get("com2") or com2   # the page's own (HSI: the steer-to point, the flight plan)
            if entry.get("opts"):   # one of the page's UFC sub-levels: its fields in the option windows, ':' on the one being typed
                labels, cue = list(entry["opts"]), entry.get("cue")
        self.display.show(labels, num, s1, s2, com1=com1, com2=com2, cue=cue)

    def _publish(self):
        if not self.bus:
            return
        bcn = self.menu == "PAGE"
        self.bus.update(menu=self.menu, cursors={name: (cur if bcn and cur in self._keys(name) else None)
                                                 for name, cur in self.cursors.items()})

    def on_connect(self):
        self.connected = True
        self.display.hello()
        self.screen = None   # screen_tick draws whatever's due

    def dial(self, name, delta):
        """Where a dial sits (0-1). The page reads them as speed controls (the middle holds; further from it,
        faster): COMM2 VOLUME turns or pans, BRT tilts or pans, COMM1 VOLUME zooms - in the PAGE menu only."""
        if self.bus:
            self.bus.dial(name, delta)

    def press(self, button):
        if button == "COMM2_PULL_LONG":   # System tab: select what's under the picture's cursor (PAGE menu only)
            if self.bus and self.menu == "PAGE":
                self.bus.bump("c2long_n")
            return
        if button in UFC_MENU_BUTTONS:
            self.menu = UFC_MENU_BUTTONS[button]
            if self.menu == "PAGE":   # start on what each page has picked, else the first
                self.cursors = {name: None for name in UFC_LISTS}
                for name in UFC_LISTS:
                    self._sync(name)
            self.show_menu()
            self._publish()
            return
        if self.menu == "PAGE" and button in ("COMM1_CCW", "COMM1_CW", "COMM1_PULL"):
            self._bcn_knob(button)
            return
        if self.menu == "PAGE" and button in ("COMM2_CCW", "COMM2_CW"):
            if self.bus:   # anticlockwise scrolls up, clockwise scrolls down
                self.bus.scroll(-1 if button == "COMM2_CCW" else 1)
            return
        if self.menu == "PAGE" and button == "COMM2_PULL":
            if self.bus:   # System tab: flips AUTO/MANUAL, or grabs / lets go of the picture; OCOR and Contracts:
                self.bus.bump("c2pull_n")   # the copy / paste button beside the system's name
            return
        if self.menu == "PAGE" and button.startswith("Opt") and self.bus and (self.bus.driver_entry() or {}).get("opts"):
            self.bus.key(button)   # a UFC sub-level is open on the page: the option buttons are its fields
            return
        if button.startswith("Opt"):
            label, action = UFC_MENUS[self.menu]["options"][int(button[3]) - 1]
            if action == "@dsg":   # DSG: the page showing designates what COMM1 has highlighted
                if self.bus:
                    self.bus.bump("dsg_n")
            elif action == "@mk":   # MK: a mark where you are (an open page marks it from its filter; with none, Status.json's)
                if self.bus:
                    n = self.bus.bump("mk_n")
                    nav = getattr(self.board, "nav", None)
                    if nav:
                        nav.mark_soon(n)
            elif action and action.startswith("@tab:"):
                tab = action[5:]
                if self.bus and self._tab() == tab:   # already showing: its next sub-tab (Nav: Syst -> Hist -> Traj -> Syst)
                    self.bus.set_view(tab, self._next_subtab(tab))
                elif self.bus:
                    self.bus.set_view(tab)   # the page last shown there
                self._moved()
            elif action:
                self.sender.press(action, label)
            return
        if self.menu == "PAGE" and button in KEYPAD_KEYS and self.bus and (self.bus.keypad_wanted() or (
                button in ("Ent", "Clr") and self.bus.page() in PAGE_KEYPAD)):   # typing on the page (ENT / CLR: its UFC sub-levels)
            self.bus.key(button)
            return
        if self.menu == "PAGE" and len(button) == 1 and button in "123456789":   # the keypad: a sub-tab of the tab showing
            if self.bus and self._subtab(int(button)):
                self._moved()
            return
        if button == "IP":
            self.sender.macro(DOCKING_MACRO, "Request docking")
            return
        # 0, CLR, ENT, EMCON and the COMM knobs (outside PAGE) aren't assigned yet

    def _moved(self):
        for name in UFC_LISTS[1:]:
            self._sync(name)
        self.show_menu()
        self._publish()

    def _next_subtab(self, tab):
        """The page to show for the tab's next sub-tab (the page last shown in it), round to the first again."""
        keys, sub = PAGE_SUBTABS[tab], self.bus.view["sub"]
        groups = sorted(set(keys))
        if len(groups) < 2:
            return sub
        nxt = groups[(groups.index(keys[sub - 1]) + 1) % len(groups)]
        return self.bus.keysubs.get((tab, nxt)) or keys.index(nxt) + 1

    def _subtab(self, digit):
        """Keypad digit: that sub-tab of the tab showing (the page last shown in it); its digit again, on a
        sub-tab of two pages (Syst: list and map), flips to the other. False if there's nothing to do."""
        tab = self._tab()
        keys = PAGE_SUBTABS.get(tab) or ()
        if digit not in keys:
            return False
        sub = self.bus.view["sub"]
        if keys[sub - 1] == digit:
            pages = [i + 1 for i, k in enumerate(keys) if k == digit]
            if len(pages) < 2:
                return False
            self.bus.set_view(tab, pages[(pages.index(sub) + 1) % len(pages)])
        else:
            self.bus.set_view(tab, self.bus.keysubs.get((tab, digit)) or keys.index(digit) + 1)
        return True

    # ---- what the displays show: following the page ----
    # The UFC behaves as if the page drives it, like a USB device with no program driving it otherwise:
    # blank with no page open (or while the page's terminal is still switched off); every digit 8 through
    # the terminal's BIOS and its waiting screen (no game, or back at the game's main menu); while a vehicle
    # starts up (ship, SRV, fighter or Nomad), the scratchpad shows the FT3000's version and the rest run test
    # patterns; then the menu. On foot, the menu comes straight after the waiting screen. With more than one
    # page open, the displays follow the first one opened. Pages say what their screens are showing at
    # /api/bootfx. (The buttons work whatever the displays show.)
    def _wanted(self, now):
        """('blank' | 'eights' | 'test' | 'menu', since)."""
        if not self.bus:
            return "menu", 0.0
        page = self.bus.page_screen(now)
        if page is None:
            return "blank", 0.0
        fx, t = page
        if fx == "off":
            return "blank", t
        if fx == "ucec":
            return "eights", t
        if fx in UFC_FX_VEHICLES and now - t < UFC_FX_LONGEST:
            return "test", t
        return "menu", t

    def screen_tick(self):
        """Called every UFC poll: draws what's due."""
        now = time.time()
        screen, t0 = self._wanted(now)
        changed = (screen, t0) != (self.screen, self.screen_t0)
        if changed:
            self.screen, self.screen_t0, self.fx_frame, self.screen_sent = screen, t0, None, 0.0
        if not self.connected:
            return
        if screen == "menu":
            if changed or (self.bus and self.menu == "PAGE" and (self.bus.driver_cue(), self.bus.driver_entry()) != self.cue_shown):
                self.show_menu()   # (or the dial cue, or what's being typed, has changed)
            return
        if screen == "test":
            f = int((now - t0) * UFC_FX_RATE)
            if f != self.fx_frame:
                self.fx_frame = f
                n = len(UFC_FX_PATTERNS)
                options = [UFC_FX_PATTERNS[(f + i * 2) % n] for i in range(5)]
                self.display.show(options, VERSION, "", "", com1=str(f % 10) * 2, com2=str(9 - f % 10) * 2, cue=f % 5 + 1)
            return
        if changed or now - self.screen_sent >= 1.0:   # (sent again each second, in case SimApp missed it)
            self.screen_sent = now
            if screen == "blank":
                self.display.show([""] * 5, "", "", "", com1="", com2="")
            else:   # every digit of every display
                self.display.show(["8888"] * 5, "88888888", "88", "88", com1="88", com2="88")

    def _bcn_knob(self, button):
        if self.bus and (self.bus.page() in PAGE_KNOB1 or self.bus.knob1_wanted()):   # the page's own: turns and pulls straight to it
            if button == "COMM1_PULL":
                self.bus.bump("c1pull_n")
            else:
                self.bus.knob1(-1 if button == "COMM1_CCW" else 1)
            return
        name = self._list()
        if name == "targets" and self.bus and self.bus.page() != "active":
            self.bus.set_view("contracts", 1)   # the knob works on Contracts' Active page, so show it
        keys = self._keys(name)
        cur = self.cursors[name]
        if name == "targets" and not keys:
            self.cursors[name] = None
        elif cur not in keys:
            if name == "targets":
                self.cursors[name] = keys[0]
            else:
                self._sync(name)
        elif button == "COMM1_CCW":   # anticlockwise: up the list (stops at the top)
            self.cursors[name] = keys[max(0, keys.index(cur) - 1)]
        elif button == "COMM1_CW":    # clockwise: down the list (stops at the bottom)
            self.cursors[name] = keys[min(len(keys) - 1, keys.index(cur) + 1)]
        elif button == "COMM1_PULL" and cur == UFC_UPLINK:
            if self.board:
                self.board.systab.request_uplink()   # pressed from the UFC: the page shows how it goes
        elif button == "COMM1_PULL" and cur in UFC_SOURCES:
            if self.board:
                self.board.systab.toggle_source(cur.split(":", 1)[1])
        elif button == "COMM1_PULL" and cur == UFC_REMOTE and self.board and self.board.remote and \
                self.board.remote.active(self.board.place.system):   # REMOTE on: back to the current system
            self.board.remote.off()
            self.board.changed()
        elif button == "COMM1_PULL" and self.bus:
            self.bus.pick(name, cur)
        self.show_menu()
        self._publish()


def load_ufc_axes():
    """The dial positions learned by --ufc-learn, or {} if not done yet."""
    try:
        data = json.loads(UFC_AXES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log(f"Couldn't read {UFC_AXES_FILE.name} ({exc}); run --ufc-learn again.")
        return {}
    out = {}
    for name, _ in UFC_KNOBS:
        ax = data.get(name) if isinstance(data, dict) else None
        if isinstance(ax, dict) and all(isinstance(ax.get(k), int) for k in ("report", "offset", "bits", "min", "max")):
            out[name] = ax
    return out


def find_dial(quiet, sweep, taken=(), numbered=True, skip=None):
    """Which part of a controller's report moved when a dial was turned end to end (the UFC's, by default).
    Tries 16-bit (two bytes) and 8-bit readings at every position outside the button bytes (skip: the bytes up
    to it; numbered: the first byte is the report's number); keeps the one that moved most, smoothly, beyond its
    idle noise."""
    best = None
    for rid in (sorted({r[0] for r in sweep}) if numbered else [None]):
        reps = [r for r in sweep if not numbered or r[0] == rid]
        n = min(len(r) for r in reps)
        idle = [r for r in quiet if (not numbered or r[0] == rid) and len(r) >= n]
        for bits in (16, 8):
            for off in range(1 if numbered else 0, n - (1 if bits == 16 else 0)):
                lim = ((len(UFC_BUTTONS) + 7) // 8 if rid == 1 else 0) if skip is None else skip
                if lim and off <= lim:
                    continue   # button bytes
                if any(t["report"] == rid and abs(t["offset"] - off) <= 1 for t in taken):
                    continue   # that's the other dial
                read = (lambda r, o=off: r[o] | (r[o + 1] << 8)) if bits == 16 else (lambda r, o=off: r[o])
                vals = [read(r) for r in reps]
                span = max(vals) - min(vals)
                if span < 8:
                    continue
                if bits == 16 and (len({r[off] for r in reps}) < 3 or len({r[off + 1] for r in reps}) < 2):
                    continue   # a real 16-bit dial moves both bytes
                jumps = sum(1 for a, b in zip(vals, vals[1:]) if abs(b - a) > span * 0.5)
                if jumps > 3:
                    continue   # wraps around: the low half of a bigger number, not a dial
                noise = (max(map(read, idle)) - min(map(read, idle))) if idle else 0
                score = (span - 3 * noise) / (65535 if bits == 16 else 255)
                if score > 0.02 and (best is None or score > best[0]):
                    best = (score, {"report": rid, "offset": off, "bits": bits, "min": min(vals), "max": max(vals)})
    return best[1] if best else None


# --------------------------------------------------------------------------- #
# Controls (4 Setup > 1 Controls): which button or dial, on which USB game controller, does each of the UFC's jobs
# --------------------------------------------------------------------------- #
# The WinWing UFC's own layout is the default. What you assign on the page is kept in controls.json - only what
# differs from the defaults, so RESTORE DEFAULTS just deletes it. A button is a part of what its device sends: the
# report (its ID: rid, or None for a device that doesn't number them), the byte, the bits there (mask) and what
# they read (value) while it's pressed - so a hat's direction is one too. A dial is where its number sits (offset,
# shift, bits) and its travel (min to max). The device: "VVVV:PPPP" (its USB vendor and product IDs), or its name.
CONTROLS_FILE = DATA_DIR / "controls.json"
CONTROL_GROUPS = (("comm", "COMM1 and COMM2", ""), ("opt", "Option buttons", "Each menu's five options"),
                  ("menu", "Menu buttons", "Each picks a menu for the option buttons"),
                  ("keypad", "Keypad", "Types digits - on the PAGE menu, a digit picks the tab's sub-page"), ("dial", "Dials", "Turned, not pressed"))
CONTROL_FUNCS = (   # (job, group, its name, what it does) - the jobs are the UFC's own button names
    ("COMM1_CCW", "comm", "COMM1 left", "Steps back through the page's list or its switches"),
    ("COMM1_CW", "comm", "COMM1 right", "Steps on through the page's list or its switches"),
    ("COMM1_PULL", "comm", "COMM1 pull", "Picks or presses what COMM1 has highlighted"),
    ("COMM2_CCW", "comm", "COMM2 left", "Scrolls up, or steps back through the page's second set"),
    ("COMM2_CW", "comm", "COMM2 right", "Scrolls down, or steps on through it"),
    ("COMM2_PULL", "comm", "COMM2 pull", "Presses what COMM2 has highlighted; held 2 seconds, the long pull"),
    ("Opt1", "opt", "Option 1", "PAGE menu: HOME"),
    ("Opt2", "opt", "Option 2", "PAGE menu: NAV"),
    ("Opt3", "opt", "Option 3", "PAGE menu: CONTRACTS"),
    ("Opt4", "opt", "Option 4", "PAGE menu: DSG"),
    ("Opt5", "opt", "Option 5", "PAGE menu: MK"),
    ("ILS", "menu", "PAGE menu", "The web page: its tabs, DSG and MK - the COMM knobs work the page (UFC: I/L/S)"),
    ("DL", "menu", "NAV menu", "Galaxy map, system map, next system, supercruise, jump (UFC: D/L)"),
    ("BCN", "menu", "WING menu", "Your wingmen, wing nav-lock, their target (UFC: BCN)"),
    ("IFF", "menu", "Targeting menu", "Next and previous target and hostile, the highest threat (UFC: IFF)"),
    ("AP", "menu", "Fighter orders 1", "Recall, follow, hold position (UFC: A/P)"),
    ("TCN", "menu", "Fighter orders 2", "Engage at will, defend, attack my target, hold fire (UFC: TCN)"),
    ("ON_OFF", "menu", "Toggles menu", "Cargo scoop, night vision, landing gear, HUD, HUD mode (UFC: ON/OFF)"),
    ("IP", "menu", "Request docking", "Asks the station you're at for docking (UFC: I/P)"),
) + tuple((d, "keypad", "Keypad " + d, "") for d in "1234567890") + (
    ("Clr", "keypad", "CLR", "Clears what's typed (again: closes it)"),
    ("Ent", "keypad", "ENT", "Enters what's typed; opens what COMM1 has highlighted"),
)
CONTROL_DIALS = (   # (job, group, its name, what it does) - turned, not pressed
    ("comm1_volume", "dial", "COMM1 volume", "Zooms (PAGE menu): further from the middle, faster"),
    ("comm2_volume", "dial", "COMM2 volume", "Spins the System picture, turns a schematic (PAGE menu)"),
    ("brightness", "dial", "Brightness", "Tilts the System picture (PAGE menu)"),
)
CONTROL_JOBS = {f[0]: f for f in CONTROL_FUNCS + CONTROL_DIALS}
UFC_LABELS = {"ILS": "I/L/S", "DL": "D/L", "AP": "A/P", "ON_OFF": "ON/OFF", "IP": "I/P", "Clr": "CLR", "Ent": "ENT",
              "COMM1_CCW": "COMM1 left", "COMM1_CW": "COMM1 right", "COMM1_PULL": "COMM1 pull",
              "COMM2_CCW": "COMM2 left", "COMM2_CW": "COMM2 right", "COMM2_PULL": "COMM2 pull",
              "comm1_volume": "COMM1 volume", "comm2_volume": "COMM2 volume", "brightness": "BRT"}
UFC_DIAL_DEFAULTS = {"comm1_volume": 7, "comm2_volume": 9, "brightness": 11}   # a UFC1's dials: their byte, 16-bit, 0-4095
CONTROL_LEARN_SECONDS = 12.0   # ASSIGN: how long it waits for a press
CONTROL_SWEEP_SECONDS = 6.0    # ... or for a dial turned end to end
CONTROL_SETTLE = 0.5           # ... after first watching the inputs (the click itself)
CONTROL_NOISE = 1.5            # a bit that changed this recently on its own isn't the press (a stick or dial drifting)
CONTROL_WATCH = 4.0            # the Controls page polling: every game controller kept open this long after
CONTROL_RESCAN = 3.0           # how often it looks for controllers plugged in or out


def ufc_default_binding(job):
    """The UFC's own button or dial for a job (its default)."""
    if job in UFC_DIAL_DEFAULTS:
        return {"dev": UFC_PRODUCT, "name": UFC_PRODUCT, "rid": 1, "offset": UFC_DIAL_DEFAULTS[job], "shift": 0, "bits": 16,
                "min": 0, "max": 4095, "label": "UFC " + ufc_label(job)}
    i = UFC_BUTTONS.index(job)
    return {"dev": UFC_PRODUCT, "name": UFC_PRODUCT, "rid": 1, "byte": 1 + i // 8, "mask": 1 << (i % 8), "value": 1 << (i % 8),
            "label": "UFC " + ufc_label(job)}


def same_input(a, b):
    """Two assignments the same button (or dial) of the same device (known by its IDs or its name)."""
    if not a or not b or a.get("rid") != b.get("rid") or not ({a.get("dev"), a.get("name")} - {None}) & ({b.get("dev"), b.get("name")} - {None}):
        return False
    if "offset" in a or "offset" in b:
        return a.get("offset") == b.get("offset") and a.get("shift", 0) == b.get("shift", 0)
    return a.get("byte") == b.get("byte") and a.get("mask") == b.get("mask") and a.get("value") == b.get("value")


class ControlStore:
    """Each job's assignment: yours (controls.json) over the defaults (the UFC's layout; its dials as ufc_axes.json
    has them, if --ufc-learn saved one). None: not assigned."""

    def __init__(self, path=CONTROLS_FILE):
        self.path, self.lock, self.n = Path(path), threading.Lock(), 0
        self.mine = self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            log(f"Couldn't read {self.path.name} ({exc}): the default controls, for now.")
            return {}
        out = {}
        for job, b in (data.get("jobs") or {}).items() if isinstance(data, dict) else ():
            if job in CONTROL_JOBS and (b is None or self._ok(job, b)):
                out[job] = b
        return out

    @staticmethod
    def _ok(job, b):
        if not isinstance(b, dict) or not isinstance(b.get("dev"), str) or not (b.get("rid") is None or isinstance(b.get("rid"), int)):
            return False
        keys = ("offset", "bits", "min", "max") if job in UFC_DIAL_DEFAULTS else ("byte", "mask", "value")
        return all(isinstance(b.get(k), int) for k in keys)

    def defaults(self):
        out = {job: ufc_default_binding(job) for job in CONTROL_JOBS}
        for job, ax in load_ufc_axes().items():   # (the dials as --ufc-learn found them on this UFC)
            out[job] = dict(out[job], rid=ax["report"], offset=ax["offset"], bits=ax["bits"], min=ax["min"], max=ax["max"])
        return out

    def effective(self):
        with self.lock:
            out = self.defaults()
            out.update(self.mine)
            return out

    def is_default(self, job):
        with self.lock:
            return job not in self.mine

    def _save(self):
        self.n += 1
        if not self.mine:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                log(f"Couldn't remove {self.path.name}: {exc}")
            return
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"version": 1, "jobs": self.mine}, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log(f"Couldn't save {self.path.name}: {exc}")

    def assign(self, job, b):
        """job gets b; any other job on the same button loses it. -> the jobs that lost it."""
        with self.lock:
            eff = self.defaults()
            eff.update(self.mine)
            moved = [j for j, x in eff.items() if j != job and same_input(x, b)]
            for j in moved:
                self.mine[j] = None
            self.mine[job] = b
            self._tidy(eff)
            self._save()
            return moved

    def _tidy(self, eff):   # (an assignment that's the default again needn't be kept)
        d = self.defaults()
        for j in list(self.mine):
            if self.mine[j] is not None and same_input(self.mine[j], d.get(j)) and self.mine[j].get("label") == d[j].get("label"):
                del self.mine[j]

    def clear(self, job):
        with self.lock:
            self.mine[job] = None
            self._save()

    def restore(self):
        with self.lock:
            self.mine = {}
            self._save()


def hid_fields(desc):
    """A HID report descriptor's input fields - [{rid, bit (from the report's first data byte), size, page, usage,
    const, null, lo, hi}] - and whether the device numbers its reports. Just enough for buttons, hats and axes."""
    fields, ids, g, stack, usages, umin, umax, offs, i = [], False, {"page": 0, "lo": 0, "hi": 0, "size": 0, "count": 0, "rid": 0}, [], [], None, None, {}, 0
    desc = list(desc or ())
    while i < len(desc):
        b = desc[i]
        if b == 0xFE:   # a long item: skipped
            if i + 1 >= len(desc):
                break
            i += 3 + desc[i + 1]
            continue
        n, kind, tag = (0, 1, 2, 4)[b & 3], (b >> 2) & 3, b >> 4
        raw = bytes(desc[i + 1:i + 1 + n])
        i += 1 + n
        if len(raw) < n:
            break
        u = int.from_bytes(raw, "little") if n else 0
        s = int.from_bytes(raw, "little", signed=True) if n else 0
        if kind == 1:   # global
            if tag == 0:
                g["page"] = u
            elif tag == 1:
                g["lo"] = s
            elif tag == 2:
                g["hi"] = s if s >= 0 or g["lo"] < 0 else u   # (an unsigned maximum unless the minimum is negative)
            elif tag == 7:
                g["size"] = u
            elif tag == 8:
                g["rid"], ids = u, True
            elif tag == 9:
                g["count"] = u
            elif tag == 10:
                stack.append(dict(g))
            elif tag == 11 and stack:
                g = stack.pop()
        elif kind == 2:   # local
            if tag == 0:
                usages.append((u >> 16, u & 0xFFFF) if n == 4 else (None, u))
            elif tag == 1:
                umin = u & 0xFFFF
            elif tag == 2:
                umax = u & 0xFFFF
        elif kind == 0:   # main
            if tag == 8:   # an input
                rid, start = g["rid"], offs.get(g["rid"], 0)
                for k in range(min(g["count"], 1024)):
                    if k < len(usages):
                        page, use = usages[k]
                    elif umin is not None:
                        page, use = None, min(umin + k, umax if umax is not None else umin + k)
                    elif usages:
                        page, use = usages[-1]
                    else:
                        page, use = None, 0
                    fields.append({"rid": rid, "bit": start + k * g["size"], "size": g["size"], "page": g["page"] if page is None else page,
                                   "usage": use, "const": bool(u & 1), "null": bool(u & 0x40), "lo": g["lo"], "hi": g["hi"]})
                offs[rid] = start + g["count"] * g["size"]
            if tag in (8, 9, 11, 10):
                usages, umin, umax = [], None, None
    return fields, ids


HID_AXES = {(1, u) for u in range(0x30, 0x39)} | {(2, u) for u in (0xB0, 0xB8, 0xBA, 0xBB, 0xC4, 0xC5, 0xC8)}   # X..wheel; rudder, throttle...
HAT_WORDS = ("Up", "Right", "Down", "Left")


def field_kind(f):
    if f["const"] or f["size"] < 1:
        return None
    if f["page"] == 9 and f["size"] == 1:
        return "button"
    if f["page"] == 1 and f["usage"] == 0x39 and f["size"] <= 8:
        return "hat"
    if (f["page"], f["usage"]) in HID_AXES and f["size"] >= 2:
        return "axis"
    return None


class HidDev:
    """One game controller the board has open."""

    def __init__(self, info, handle):
        self.info, self.h, self.path = info, handle, info.get("path")
        vid, pid = int(info.get("vendor_id") or 0), int(info.get("product_id") or 0)
        self.key = f"{vid:04X}:{pid:04X}"
        self.name = (info.get("product_string") or "").strip() or self.key
        self.fields, self.ids = [], None   # (ids None: not known whether it numbers its reports)
        if self.name == UFC_PRODUCT:
            self.ids = True   # (the UFC: its button and dial reports are ID 1)
        try:
            desc = handle.get_report_descriptor()
            if desc:
                self.fields, self.ids = hid_fields(desc)
        except Exception:
            pass   # (older hidapi, or a device that won't say: learned from what changes)
        self.last, self.longest, self.flips, self.hist = {}, {}, {}, deque(maxlen=400)
        self.seen, self.heads = 0.0, set()
        self.hats = [f for f in self.fields if field_kind(f) == "hat"]

    def rid(self, report):
        if self.ids is None:
            return report[0] if len(self.heads) <= 1 and report[0] else None
        return report[0] if self.ids else None

    def byte_of(self, f):
        return (1 if self.ids else 0) + f["bit"] // 8

    def field_at(self, rid, byte, bit):
        b = (byte - (1 if self.ids else 0)) * 8 + bit
        for f in self.fields:
            if (f["rid"] if self.ids else None) == rid and f["bit"] <= b < f["bit"] + f["size"]:
                return f
        return None

    def label(self, f, value=None):
        k = field_kind(f)
        if k == "button":
            return f"Button {f['usage']}", f"Joy_{f['usage']}"
        if k == "hat":
            n = self.hats.index(f) + 1
            steps = f["hi"] - f["lo"] + 1
            d = (value - f["lo"]) * 8 // steps if steps > 0 and value is not None else 0
            word = ("Up", "Up right", "Right", "Down right", "Down", "Down left", "Left", "Up left")[d % 8]
            return f"Hat {n} {word.lower()}", (f"Joy_POV{n}{word}" if word in HAT_WORDS else None)
        return "Axis", None


class HidInputs(threading.Thread):
    """Reads every game controller with a job (and, while the Controls page shows or ASSIGN waits, every one there
    is), and turns their buttons and dials into the UFC's jobs: each report, every 50 ms; a press counts once two
    reports agree (the COMM turns on the first); COMM2's pull, held 2 seconds, is the long pull. Learns a button
    (or dial) for ASSIGN; looks for controllers plugged in or out every few seconds."""

    def __init__(self, controller, hid_module, store):
        super().__init__(daemon=True, name="ufc")
        self.controller, self.hid, self.store = controller, hid_module, store
        self.devs, self.lock = {}, threading.Lock()
        self.state = {j: {"prev": 0, "stable": 0, "last_raw": 0, "count": 0, "since": 0.0, "long": False} for j, *_ in CONTROL_FUNCS}
        self.axis_last, self.lit = {}, {}
        self.binds, self.binds_n = {}, -1
        self.watch_until, self.next_scan, self.mute_until = 0.0, 0.0, 0.0
        self.learning, self.result, self.result_n = None, None, 0
        self.found, self.warned = [], set()

    # ---- the assignments, by device ----
    def _index(self):
        if self.binds_n == self.store.n:
            return
        self.binds_n, eff, by = self.store.n, self.store.effective(), {}
        for job, b in eff.items():
            if b:
                by.setdefault(b["dev"], []).append((job, b))
        self.binds = by

    def _jobs_for(self, dev):
        return self.binds.get(dev.key, []) + (self.binds.get(dev.name, []) if dev.name != dev.key else [])

    # ---- finding and opening the controllers ----
    @staticmethod
    def _controller(info):
        return (info.get("usage_page") == 1 and info.get("usage") in (4, 5, 8)) or info.get("product_string") == UFC_PRODUCT

    def _scan(self):
        self.next_scan = time.time() + CONTROL_RESCAN
        self._index()
        try:
            infos = list(self.hid.enumerate())
        except Exception as exc:
            if "enum" not in self.warned:
                self.warned.add("enum")
                log(f"Couldn't list the USB controllers: {exc}")
            return
        watching = time.time() < self.watch_until or self.learning is not None
        pick = {}   # one interface a device: its game-controller one if it says, else the first
        for info in infos:
            vid, pid = int(info.get("vendor_id") or 0), int(info.get("product_id") or 0)
            key, name = f"{vid:04X}:{pid:04X}", (info.get("product_string") or "").strip()
            bound = key in self.binds or (name and name in self.binds)
            if not (bound or self._controller(info)):
                continue
            if key not in pick or (self._controller(info) and not self._controller(pick[key][0])):
                pick[key] = (info, bound)
        self.found = [{"key": k, "name": (i.get("product_string") or "").strip() or k, "bound": b} for k, (i, b) in pick.items()]
        want = {k: i for k, (i, b) in pick.items() if b or watching}
        for path, dev in list(self.devs.items()):
            if dev.key not in want or want[dev.key].get("path") != path:
                self._close(dev, quiet=True)
        for key, info in want.items():
            if info.get("path") in self.devs:
                continue
            try:
                h = self.hid.device()
                if info.get("path") is not None and hasattr(h, "open_path"):
                    h.open_path(info["path"])
                else:
                    h.open(info["vendor_id"], info["product_id"])
                h.set_nonblocking(True)
            except Exception as exc:
                if key not in self.warned:
                    self.warned.add(key)
                    log(f"Couldn't open {(info.get('product_string') or key).strip()}: {exc}")
                continue
            self.warned.discard(key)
            dev = HidDev(info, h)
            self.devs[dev.path] = dev
            if self._jobs_for(dev):
                log("UFC connected." if dev.name == UFC_PRODUCT else f"{dev.name} connected ({len(self._jobs_for(dev))} of its buttons and dials have jobs).")
                for job, _b in self._jobs_for(dev):
                    if job in self.state:
                        self.state[job].update(prev=0, stable=0, last_raw=0, count=0, since=0.0, long=False)
        self._connected()
        if not self.controller.connected and "none" not in self.warned:
            self.warned.add("none")
            log("UFC not found - will keep looking (4 Setup > Controls can give its jobs to another controller). "
                "The web board works without it.")

    def _close(self, dev, quiet=False):
        self.devs.pop(dev.path, None)
        try:
            dev.h.close()
        except Exception:
            pass
        if not quiet and self._jobs_for(dev):
            log(("UFC" if dev.name == UFC_PRODUCT else dev.name) + " disconnected. Reconnecting...")
        self._connected()

    def _connected(self):
        on = any(self._jobs_for(d) for d in self.devs.values())
        if on and not self.controller.connected:
            self.controller.on_connect()
        elif not on and self.controller.connected:
            self.controller.connected = False

    # ---- the loop ----
    def run(self):
        while True:
            try:
                now = time.time()
                if now >= self.next_scan or self.binds_n != self.store.n:
                    self._scan()
                for dev in list(self.devs.values()):
                    try:
                        self.poll(dev)
                    except OSError as exc:
                        log(f"{dev.name}: {exc}")
                        self._close(dev)
                self.tick()
                self.controller.screen_tick()
            except Exception as exc:   # (never let one bad report stop the controls)
                log(f"Controls: {exc!r}")
            time.sleep(UFC_LOOP_SECONDS)

    def poll(self, dev):
        for _ in range(UFC_READS_PER_POLL):   # (capped, so a controller that never stops sending can't starve the rest)
            report = dev.h.read(64 if dev.name == UFC_PRODUCT else 256)
            if not report:
                break
            self.process(dev, list(report))

    def tick(self):
        """A pull held long enough counts as a long pull, even if nothing new comes meanwhile; ASSIGN's time running out."""
        now = time.time()
        for name in UFC_LONG_BUTTONS:
            s = self.state[name]
            if s["stable"] and not s["long"] and s["since"] and now - s["since"] >= UFC_LONG_PULL:
                s["long"] = True
                self._press(name + "_LONG")
        with self.lock:
            L = self.learning
            if L and L["kind"] == "dial" and now >= L["t0"] + CONTROL_SETTLE + CONTROL_SWEEP_SECONDS:
                self._finish_dial(L)
            elif L and L["kind"] == "button" and now >= L["until"]:
                self._end(L, False, why="Nothing pressed - try again")

    def _muted(self):
        return time.time() < self.mute_until or self.learning is not None   # (ASSIGN waiting, or just had a press: it only records it)

    def _press(self, name):
        if self._muted():
            return
        self.lit[name] = time.time()
        self.controller.press(name)

    def process(self, dev, report):
        now = time.time()
        if not report:
            return
        if dev.ids is None:
            dev.heads.add(report[0])
        rid = dev.rid(report)
        n = len(report)
        if n < dev.longest.get(rid, 0):
            return   # (a short report of the same number isn't its button data: phantom presses)
        dev.longest[rid] = n
        prev = dev.last.get(rid)
        if prev is not None and len(prev) == n:   # the bits that changed, and when (a stick's drift isn't a press)
            for i in range(n):
                x = prev[i] ^ report[i]
                if x:
                    for bit in range(8):
                        if x >> bit & 1:
                            dev.flips.setdefault((rid, i, bit), deque(maxlen=2)).append(now)
        dev.seen = now
        dev.hist.append((now, rid, report))
        with self.lock:
            if self.learning is not None:
                self._learn(dev, rid, prev, report, now)
        dev.last[rid] = report
        for job, b in self._jobs_for(dev):
            if b.get("rid") is not None and b["rid"] != report[0]:
                continue
            if "offset" in b:
                self._dial(job, b, report)
                continue
            if b["byte"] >= n or job not in self.state:
                continue
            self._button(job, int((report[b["byte"]] & b["mask"]) == b["value"]))

    def _button(self, name, raw):
        s = self.state[name]
        if raw and not self._muted():
            self.lit[name] = time.time()   # (lit on the Controls page while it's held)
        if name in UFC_PULSE_BUTTONS:
            if raw and not s["prev"]:
                self._press(name)
            s["prev"] = raw
            return
        if raw == s["last_raw"]:
            s["count"] += 1
        else:
            s["count"], s["last_raw"] = 1, raw
        if s["count"] >= UFC_STABLE_READS:
            s["stable"] = raw
        if name in UFC_LONG_BUTTONS:   # acts on release (short) or after UFC_LONG_PULL seconds (long)
            if s["stable"] and not s["prev"]:
                s["since"], s["long"] = time.time(), False
            elif not s["stable"] and s["prev"]:
                if not s["long"]:
                    self._press(name)
                s["since"], s["long"] = 0.0, False
            s["prev"] = s["stable"]
            self.tick()
            return
        if s["stable"] and not s["prev"]:
            self._press(name)
        s["prev"] = s["stable"]

    @staticmethod
    def _read(b, report):
        off, bits, shift = b["offset"], b["bits"], b.get("shift", 0)
        need = (shift + bits + 7) // 8
        if len(report) < off + need:
            return None
        v = (int.from_bytes(bytes(report[off:off + need]), "little") >> shift) & ((1 << bits) - 1)
        if b["min"] < 0 and v >= 1 << (bits - 1):
            v -= 1 << bits
        return v

    def _dial(self, name, b, report):
        value = self._read(b, report)
        span = b["max"] - b["min"]
        if value is None or span <= 0:
            return
        pos = (value - b["min"]) / span   # not clamped: travel past the learned ends still counts
        last = self.axis_last.get(name)
        if last is None or abs(pos - last) >= max(UFC_AXIS_NOISE, 1.5 / span):
            if self._muted():
                return   # (ASSIGN: it only records the dial - where it ends up counts once it's done)
            self.axis_last[name] = pos
            if last is not None:
                self.lit[name] = time.time()
            self.controller.dial(name, pos)   # where it sits (the page makes it a speed control)

    # ---- ASSIGN: learning a button or a dial ----
    def learn(self, job):
        """Start listening for the job's new button (or dial). -> (ok, why)"""
        if job not in CONTROL_JOBS:
            return False, "job"
        with self.lock:
            now = time.time()
            self.watch_until = max(self.watch_until, now + CONTROL_LEARN_SECONDS + 2)
            self.learning = {"job": job, "kind": "dial" if job in UFC_DIAL_DEFAULTS else "button", "t0": now,
                             "until": now + CONTROL_LEARN_SECONDS, "sweep": {}}
        self.next_scan = 0.0   # (open every controller now)
        return True, ""

    def cancel(self):
        with self.lock:
            if self.learning:
                self._end(self.learning, False, why="Cancelled")

    def _end(self, L, ok, why="", b=None, moved=()):
        self.learning, self.mute_until = None, time.time() + 0.8   # (the press just recorded: its release does nothing)
        self.result_n += 1
        self.result = {"n": self.result_n, "job": L["job"], "ok": ok, "why": why, "label": (b or {}).get("label", ""),
                       "name": (b or {}).get("name", ""), "moved": list(moved)}
        for name in self.state:   # (where each button is now counts as where it was: nothing fires on the way out)
            s = self.state[name]
            s["count"] = 0

    def _learn(self, dev, rid, prev, report, now):
        L = self.learning
        if L["kind"] == "dial":
            if now >= L["t0"] + CONTROL_SETTLE:
                L["sweep"].setdefault(dev.path, []).append(report)
            return
        if now < L["t0"] + CONTROL_SETTLE:
            return
        changed = []
        if prev is not None and len(prev) == len(report):
            for i in range(len(report)):
                x = prev[i] ^ report[i]
                for bit in range(8):
                    if x >> bit & 1:
                        times = dev.flips.get((rid, i, bit)) or ()
                        if len(times) >= 2 and now - times[-2] < CONTROL_NOISE:
                            continue   # (it was changing on its own a moment ago: drift, not the press)
                        changed.append((i, bit))
        elif dev.fields:   # its first report since it was opened: against its idle state (buttons off, hats centred)
            for f in dev.fields:
                if (f["rid"] if dev.ids else None) != rid or field_kind(f) not in ("button", "hat"):
                    continue
                i, bit = dev.byte_of(f), f["bit"] % 8
                if i < len(report) and report[i] >> bit & ((1 << min(f["size"], 8 - bit)) - 1):
                    changed.append((i, bit))
        if not changed:
            return
        b = None
        if dev.fields:   # the device says what each part is: a button, or a hat's direction (axes aren't presses)
            for i, bit in changed:
                f = dev.field_at(rid, i, bit)
                k = field_kind(f) if f else None
                if k == "button" and report[i] >> bit & 1:
                    label, joy = dev.label(f)
                    b = {"byte": i, "mask": 1 << bit, "value": 1 << bit, "label": label, "joy": joy}
                    break
                if k == "hat":
                    start = dev.byte_of(f)
                    shift = f["bit"] % 8
                    if shift + f["size"] > 8:
                        continue
                    mask = ((1 << f["size"]) - 1) << shift
                    v = (report[start] & mask) >> shift
                    if f["lo"] <= v <= f["hi"]:
                        label, joy = dev.label(f, v)
                        b = {"byte": start, "mask": mask, "value": v << shift, "label": label, "joy": joy}
                        break
        else:   # learned from what changed: one bit going on is a button; several in one byte, a hat's direction
            bytes_hit = sorted({i for i, _ in changed})
            if len(bytes_hit) != 1:
                return   # (more than one part moved at once: wait for a cleaner press)
            i = bytes_hit[0]
            bits = [bit for j, bit in changed if j == i]
            if len(bits) == 1:
                if not report[i] >> bits[0] & 1:
                    return   # (a release)
                b = {"byte": i, "mask": 1 << bits[0], "value": 1 << bits[0], "label": f"Byte {i} bit {bits[0]}"}
            else:
                mask = 0x0F if max(bits) < 4 else 0xF0 if min(bits) >= 4 else 0xFF
                b = {"byte": i, "mask": mask, "value": report[i] & mask, "label": f"Byte {i} = {report[i] & mask:#04x}"}
        if b is None:
            return
        if dev.name == UFC_PRODUCT and rid == 1 and i_ufc(b) is not None:   # (one of the UFC's own: its name)
            b["label"] = "UFC " + ufc_label(UFC_BUTTONS[i_ufc(b)])
        b.update(dev=dev.key, name=dev.name, rid=rid if dev.ids is not False else None)
        if b.get("joy") is None:
            b.pop("joy", None)
        moved = self.store.assign(L["job"], b)
        self._end(L, True, b=b, moved=moved)

    def _finish_dial(self, L):
        best = None
        for path, sweep in L["sweep"].items():
            dev = self.devs.get(path)
            if not dev or len(sweep) < 3:
                continue
            if dev.fields:   # the axis that moved furthest across its travel
                for f in dev.fields:
                    if field_kind(f) != "axis" or (f["rid"] if dev.ids else None) not in {dev.rid(r) for r in sweep}:
                        continue
                    b = {"offset": dev.byte_of(f), "shift": f["bit"] % 8, "bits": f["size"], "min": f["lo"], "max": f["hi"]}
                    rid = f["rid"] if dev.ids else None
                    vals = [v for v in (self._read(b, r) for r in sweep if dev.rid(r) == rid) if v is not None]
                    span = (max(vals) - min(vals)) / max(1, f["hi"] - f["lo"]) if vals else 0
                    if span > 0.25 and (best is None or span > best[0]):
                        names = {0x30: "X", 0x31: "Y", 0x32: "Z", 0x33: "Rx", 0x34: "Ry", 0x35: "Rz", 0x36: "Slider", 0x37: "Dial", 0x38: "Wheel"}
                        label = (names.get(f["usage"], "Axis") if f["page"] == 1 else "Axis") + " axis"
                        best = (span, dev, dict(b, rid=rid, label=label))
            else:   # learned from what changed: the part that moved most, smoothly, beyond its idle noise
                quiet = [r for t, _rid, r in dev.hist if t < L["t0"]]
                taken = [{"report": x.get("rid"), "offset": x["offset"]} for _j, x in self._jobs_for(dev) if "offset" in x and _j != L["job"]]
                hit = find_dial(quiet, sweep, taken=taken, numbered=dev.ids is not False and dev.rid(sweep[0]) is not None,
                                skip=(len(UFC_BUTTONS) + 7) // 8 if dev.name == UFC_PRODUCT else 0)
                if hit:
                    score = (hit["max"] - hit["min"]) / (65535 if hit["bits"] == 16 else 255)
                    if best is None or score > best[0]:
                        best = (score, dev, {"rid": hit["report"] if dev.ids is not False else None, "offset": hit["offset"], "shift": 0,
                                             "bits": hit["bits"], "min": hit["min"], "max": hit["max"],
                                             "label": f"Byte {hit['offset']} ({hit['bits']}-bit)"})
        if not best:
            self._end(L, False, why="Nothing turned far enough - turn it end to end, then back")
            return
        _score, dev, b = best
        if dev.name == UFC_PRODUCT:
            for job, off in UFC_DIAL_DEFAULTS.items():
                if b["offset"] == off and b.get("rid") == 1:
                    b["label"] = "UFC " + UFC_LABELS[job]
        b.update(dev=dev.key, name=dev.name)
        moved = self.store.assign(L["job"], b)
        self._end(L, True, b=b, moved=moved)

    # ---- for the page ----
    def watch(self):
        """The Controls page is showing: keep every controller open (to light them up, and for ASSIGN)."""
        if time.time() >= self.watch_until:
            self.next_scan = 0.0
        self.watch_until = max(self.watch_until, time.time() + CONTROL_WATCH)

    def view(self):
        now = time.time()
        with self.lock:
            L = self.learning
            learning = None if not L else {"job": L["job"], "kind": L["kind"], "left": round(max(0.0, (
                L["t0"] + CONTROL_SETTLE + CONTROL_SWEEP_SECONDS if L["kind"] == "dial" else L["until"]) - now), 1),
                "ready": now >= L["t0"] + CONTROL_SETTLE}
        opened = {d.key: d for d in list(self.devs.values())}   # (the reader may be opening one as the page asks)
        devices = []
        for f in self.found:
            d = opened.get(f["key"])
            devices.append({"key": f["key"], "name": f["name"], "open": bool(d), "bound": f["bound"],
                            "active": bool(d and now - d.seen < 0.6 and d.seen), "described": bool(d and d.fields)})
        return {"on": True, "devices": devices, "learning": learning, "result": self.result,
                "lit": {k: round(now - t, 2) for k, t in list(self.lit.items()) if now - t < 1.0}}


def ufc_label(name):
    """A UFC button's name as the UFC has it (I/L/S, CLR...), or its job's."""
    return UFC_LABELS.get(name) or (CONTROL_JOBS[name][2] if name in CONTROL_JOBS else name)


def i_ufc(b):
    """The UFC button a learned assignment is, if it's one of the UFC's own (report 1, a single bit)."""
    if b.get("mask") != b.get("value") or not b.get("mask") or b["mask"] & (b["mask"] - 1):
        return None
    i = (b["byte"] - 1) * 8 + b["mask"].bit_length() - 1
    return i if 0 <= i < len(UFC_BUTTONS) else None


def controls_view(store, inputs, bindings=None, why=""):
    """What 4 Setup > Controls shows: each job's assignment (or none, or the default), the controllers, ASSIGN."""
    eff = store.effective()
    jobs = []
    for job, group, name, what in CONTROL_FUNCS + CONTROL_DIALS:
        b = eff.get(job)
        elite = bindings.joy_actions(b["dev"], b.get("joy")) if (b and bindings and b.get("joy")) else []
        jobs.append({"job": job, "group": group, "name": name, "what": what, "kind": "dial" if job in UFC_DIAL_DEFAULTS else "button",
                     "default": store.is_default(job),
                     "bind": None if not b else {"label": b.get("label", ""), "dev": b["dev"], "name": b.get("name", b["dev"])},
                     "elite": elite})
    out = inputs.view() if inputs else {"on": False, "why": why, "devices": [], "learning": None, "result": None, "lit": {}}
    out.update(groups=[{"id": g, "name": n, "what": w} for g, n, w in CONTROL_GROUPS], jobs=jobs, n=store.n,
               custom=bool(store.mine))
    return out


def run_ufc_learn(hid_module=None, quiet_seconds=3.0, sweep_seconds=8.0, ask=input):
    """--ufc-learn: find where the brightness and COMM2 volume dials appear in the UFC's
    reports and save it to ufc_axes.json. Run it once, with SimApp Pro running or not."""
    if hid_module is None:
        try:
            import hid as hid_module
        except ImportError:
            print("This needs the hidapi package: pip install hidapi")
            return
    handle = None
    for dev in hid_module.enumerate():
        if dev.get("product_string") == UFC_PRODUCT:
            handle = hid_module.device()
            handle.open(dev["vendor_id"], dev["product_id"])
            handle.set_nonblocking(True)
            break
    if handle is None:
        print("UFC not found. Is it plugged in?")
        return

    def capture(seconds):
        got, end = [], time.time() + seconds
        while time.time() < end:
            r = handle.read(64)
            if r:
                got.append(list(r))
            else:
                time.sleep(0.01)
        return got

    print("Learning the UFC's brightness, COMM2 volume and COMM1 volume knobs.")
    print(f"Leave every knob and button alone for {quiet_seconds:.0f} seconds...")
    quiet = capture(quiet_seconds)
    before, found = load_ufc_axes(), {}
    for name, desc in UFC_KNOBS:
        ask(f"\nPress Enter, then slowly turn {desc} all the way one way and all the way back "
            f"({sweep_seconds:.0f} seconds)... ")
        sweep = capture(sweep_seconds)
        others = list(found.values()) + [ax for k, ax in before.items() if k != name and k not in found]
        hit = find_dial(quiet, sweep, taken=others)
        if hit:
            found[name] = hit
            print(f"  Found it: report {hit['report']}, byte {hit['offset']}, {hit['bits']}-bit, range {hit['min']}-{hit['max']}.")
        elif name in before:
            found[name] = before[name]
            print(f"  Didn't see it move ({len(sweep)} reports read); keeping what was learned before.")
        else:
            print(f"  Didn't see it move ({len(sweep)} reports read). Try again, turning it further.")
    try:
        handle.close()
    except Exception:
        pass
    if not found:
        print("\nNothing saved: none of the knobs showed up in the UFC's reports.")
        return
    UFC_AXES_FILE.parent.mkdir(parents=True, exist_ok=True)
    UFC_AXES_FILE.write_text(json.dumps(found, indent=2), encoding="utf-8")
    print(f"\nSaved to {UFC_AXES_FILE}. Start the board as usual; on the System tab BRT and COMM2 VOLUME now turn the picture"
          " and COMM1 VOLUME zooms.")


def ufc_key_table(bindings: EliteBindings) -> str:
    """Text table of what every UFC button will press, for --list-keys."""
    lines = []
    for menu, page in UFC_MENUS.items():
        lines.append(f"{UFC_BUTTON_OF.get(menu, menu)} button: {menu} menu ({page['code']}{page['num']})")
        for i, (label, action) in enumerate(page["options"], 1):
            if not action:
                lines.append(f"  Opt{i}  {'-':5}")
                continue
            if action.startswith("@tab:"):
                lines.append(f"  Opt{i}  {label:5} web page tab: {action[5:]}")
                continue
            if action.startswith("@"):   # (the page menu's DSG and MK: the page's, not a key)
                lines.append(f"  Opt{i}  {label:5} web page: {'designate' if action == '@dsg' else 'mark where you are'}")
                continue
            combo = bindings.lookup(action)
            lines.append(f"  Opt{i}  {label:5} {action:28} {key_label(combo) if combo else '** NO KEYBOARD BINDING **'}")
    lines.append("IP (request docking)")
    for action in DOCKING_MACRO:
        combo = bindings.lookup(action)
        lines.append(f"        {action:34} {key_label(combo) if combo else '** NO KEYBOARD BINDING **'}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Web page
# --------------------------------------------------------------------------- #
# The page's tabs, each made of pages, in order: 1 Home, 2 Nav (Syst - its list and map - and Hist), 3 Contracts
# (Active, History and OCOR). The page and the UFC share one record of where you are: a tab and a page within it
# (UIBus.view). web/js/main.js lays the same pages out; a test checks the two agree.
PAGE_TABS = {"home": ("home",), "nav": ("list", "map", "traj", "wpt", "hsi", "atk", "hist"), "contracts": ("active", "history", "ocor"),
             "setup": ("controls", "settings")}
# Each page's sub-tab: the keypad digit that picks it (the second row of tabs on the page). The System list and
# map are one sub-tab, SYST - its digit again flips between them.
PAGE_SUBTABS = {"home": (1,), "nav": (1, 1, 2, 3, 4, 5, 6), "contracts": (1, 2, 3), "setup": (1, 2)}
# The list the UFC's COMM1 knob moves through on each page (elsewhere - Home: the contracts, on Contracts' Active page).
PAGE_LISTS = {"active": "targets", "history": "chist", "ocor": "ocor", "list": "syst", "map": "syst", "hist": "hist"}
# Pages where the COMM1 knob works the page itself rather than a list (Traj: its course box and switches; COMM2 its profiles and RESET SCALE;
# Wpt: its methods, waypoints, marks and flight plans, COMM2 its right panel; HSI: its switches, COMM2 the steer-to point;
# Atk: PLAN / ATTACK, its plan's heading, role and BUILD, COMM2 its buttons).
PAGE_KNOB1 = ("traj", "wpt", "hsi", "atk")
# Pages that type with the keypad (Wpt's names, coordinates and flight plans; Atk's plan; the HSI's countdown): while one says it's typing, the keypad's
# keys go to it, not the sub-tabs - and ENT and CLR always do (ENT opens the UFC sub-level for what COMM1 has highlighted).
PAGE_KEYPAD = ("wpt", "atk", "list", "hsi")   # (1 Syst's list: its REMOTE list, and MANUAL's name - COMM1 too, while that's open;
#                                             the HSI: its countdown timer's time)
# Pages that put their own words on the scratchpad while they show (Atk: the release countdown; HSI: the steer-to point).
PAGE_SCRATCH = ("atk", "hsi")
KEYPAD_KEYS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Clr", "Ent")
KEYPAD_KEEP = 24   # keys the bus keeps for a page that missed a push
TIMER_IDLE = {"mode": "et", "run": False, "t0": None, "cd": None, "ack": False}   # the HSI's timer at start-up: the stopwatch, at zero
TIMER_MAX = 99 * 3600 + 59 * 60 + 59   # the longest countdown (s): 99:59:59
TARGET_METHODS = {"manual": "Manual", "overfly": "Overfly", "desig": "HUD VV", "xb": "HUD X-B", "code": "Code"}   # how a target of yours was made (2 Nav > Wpt; "code": loaded from a shared code)

WEB_DIR = SCRIPT_DIR / "web"   # the page: index.html, style.css, js/ and the font, next to this script
WEB_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
             ".woff": "font/woff", ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json"}
WEB_MISSING = """<!doctype html><meta charset="utf-8"><title>UCEC FT3000</title>
<body style="background:#060606;color:#45f08a;font:20px monospace;padding:24px">
<p>The page's files aren't here: the <b>web</b> folder must sit next to ed_target_board.py.</p>
<p>Copy the script, web and tests together into one folder, then reload.</p>"""
# The font, web/vga.woff: "Px437 IBM VGA 8x16" (WebPlus .woff, unmodified) from the Ultimate Oldschool
# PC Font Pack by VileR, https://int10h.org/oldschool-pc-fonts/ - CC BY-SA 4.0,
# https://creativecommons.org/licenses/by-sa/4.0/


def request_refusal(path, headers, own_names=()):
    """Why a request mustn't be answered - or "" to answer it. The board answers its own page, wherever that's opened
    (localhost, this PC's name, an IP address - a phone on the same network), and programs that aren't browsers (the
    next copy started, closing this one). Not another website open in the same browser: a page elsewhere can't send it
    anything (its Origin, or Sec-Fetch-Site, says it's from somewhere else) - pressing UFC buttons, sending keys to Elite,
    stopping it - and can't pose as it under a name of its own pointed at this PC (DNS rebinding: Host is checked)."""
    import ipaddress
    from urllib.parse import urlsplit

    def name_of(hostport):
        h = (hostport or "").strip().lower()
        if h.startswith("["):
            return h[1:h.find("]")] if "]" in h else h
        return h.rsplit(":", 1)[0] if h.count(":") == 1 else h

    def known(name):
        if not name:
            return False
        if name == "localhost" or name in own_names:
            return True
        try:
            ipaddress.ip_address(name)
            return True
        except ValueError:
            return False

    host = headers.get("Host") or ""
    if not known(name_of(host)):
        return "host"
    if not path.startswith("/api/"):
        return ""   # (the page's own files: another site can't read them, and a link to the page is fine)
    if (headers.get("Sec-Fetch-Site") or "").lower() in ("cross-site", "same-site"):
        return "site"
    origin = headers.get("Origin")
    if origin is not None:
        o = urlsplit(origin.strip())
        if o.scheme not in ("http", "https") or o.netloc.lower() != host.strip().lower():
            return "origin"
    return ""


def own_host_names():
    """This PC's own names, as the page may be opened by them (besides localhost and IP addresses)."""
    names = set()
    for n in (socket.gethostname(), socket.getfqdn()):
        if n:
            names.update({n.lower(), n.lower().split(".")[0], n.lower().split(".")[0] + ".local"})
    return names


def web_file(url_path):
    """The file in the web folder for a URL path ("/" is index.html), or None. Never leaves the folder."""
    rel = url_path.lstrip("/") or "index.html"
    try:
        path = (WEB_DIR / rel).resolve()
        path.relative_to(WEB_DIR.resolve())
    except (ValueError, OSError):
        return None
    return path if path.suffix in WEB_TYPES and path.is_file() else None


class Handler(BaseHTTPRequestHandler):
    server_version = f"UCEC-FT3000/{VERSION}"

    def log_message(self, *args):  # keep the console quiet
        pass

    def _send(self, code, body, ctype, cache="no-store"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def _refused(self):
        """Not the board's own page (or a program): refused, and said so once a minute (see request_refusal)."""
        why = request_refusal(self.path.split("?", 1)[0], self.headers, getattr(self.server, "names", ()))
        if not why:
            return False
        now, last = time.time(), getattr(self.server, "refused_at", 0.0)
        if now - last > 60:
            self.server.refused_at = now
            log(f"Refused a request that didn't come from the FT3000's page ({why}: "
                f"{(self.headers.get('Origin') or self.headers.get('Host') or '?')[:80]}) - another website, or a name pointed at this PC.")
        self._send(403, json.dumps({"ok": False, "why": "Refused: not from the FT3000's own page"}), "application/json")
        return True

    def do_GET(self):
        if self._refused():
            return
        state, writer, engine = self.server.app
        path = self.path.split("?", 1)[0]
        if path == "/api/remote":   # 1 Syst's REMOTE list (route, missions, OCOR, history, picked lately) and what it shows now
            self._send(200, json.dumps({"items": remote_options(state, self.server.ocor), "remote": state.remote_view()}), "application/json")
            return
        if path == "/api/sysfind":   # MANUAL's matches for what's typed: ?q=...
            q = (parse_qs(self.path.split("?", 1)[1]).get("q") or [""])[0] if "?" in self.path else ""
            self._send(200, json.dumps({"q": q, "items": remote_search(state, q)}), "application/json")
            return
        if path == "/api/controls":   # 4 Setup > Controls: each job's button or dial, the controllers, ASSIGN (asking keeps them open)
            if self.server.inputs:
                self.server.inputs.watch()
            out = controls_view(self.server.controls, self.server.inputs, self.server.binds, self.server.inputs_why)
            self._send(200, json.dumps(out), "application/json")
            return
        if path == "/api/settings":   # 4 Setup > Settings: each setting, what it started with, the About block
            self._send(200, json.dumps(settings_view(self.server)), "application/json")
            return
        if path == "/api/hello":   # who's here: the next copy started asks, to close this one (see One copy at a time)
            self._send(200, json.dumps({"app": APP_NAME, "version": VERSION, "pid": os.getpid()}), "application/json")
            return
        if path == "/api/state":
            t0 = time.time()
            snap = state.snapshot(engine.name)
            snap["ocor"] = self.server.ocor.snapshot()
            star = getattr(self.server, "star", None)
            if star:
                snap["ocor"]["dist"] = star.for_page(snap["ocor"].get("objectives", []), snap.get("system"), snap.get("star_pos"))
                j = snap.get("jump")
                if j and j.get("ly") is None:   # no plotted route: the two systems' coordinates, if known
                    known, _ = star.cache.lookup([j["from"], j["to"]])
                    a, b = known.get(coord_key(j["from"])), known.get(coord_key(j["to"]))
                    if a and b:
                        j["ly"] = round(math.dist(a, b), 2)
            if TIMING:
                snap["timing"] = True   # the page notes its side too
            t1 = time.time()
            body = json.dumps(snap)
            t2 = time.time()
            self._send(200, body, "application/json")
            if TIMING:   # building the state, turning it into text, sending it; its size; the position reading in it
                me = (snap.get("syst") or {}).get("me") or {}
                TIMING.rec("api", w=round(t0, 4), build=_ms(t1 - t0), json=_ms(t2 - t1), send=_ms(time.time() - t2),
                           kb=round(len(body) / 1024, 1), mt=me.get("t"), age=me.get("age"))
        elif path == "/api/events":
            self._events()
        elif path in ("/api/hist", "/api/hist/item"):   # ?page=nav|contracts: a history page's list (&key=: one item's details)
            query = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            page, key = (query.get("page") or [""])[0], (query.get("key") or [""])[0][:400]
            hist = state.history
            if hist is None or page not in HISTORY_FILTERS:
                self._send(404, json.dumps({"ok": False}), "application/json")
            elif path == "/api/hist":   # (&start=, &count=: a part of it; &want=: at least as far as that row)
                num = (lambda name, d: int((query.get(name) or [d])[0]) if str((query.get(name) or [d])[0]).isdigit() else d)
                count = num("count", None) if query.get("count") else None
                self._send(200, json.dumps(hist.view(page, num("start", 0), count, (query.get("want") or [None])[0])), "application/json")
            else:
                item = hist.place(key, state.records) if page == "nav" else hist.mission(key, state.contracts.backstories)
                if item and item.get("skey") and state.settlements and state.schematics:   # a settlement whose layout you've confirmed
                    layout = state.settlements.for_keys([item["skey"]]).get(item["skey"])
                    cat, count = state.schematics.category_of(layout) if layout else (None, 0)
                    if cat:
                        item["schem"] = {"id": layout, "category": cat, "count": count}
                self._send(200 if item else 404, json.dumps(item or {"ok": False}), "application/json")
        elif path == "/api/schematics":   # ?category=tourism: that economy's layout plans, ready to draw
            query = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            cat = (query.get("category") or [""])[0]
            store = state.schematics
            self._send(200, json.dumps({"category": schematic_category(cat), "layouts": store.layouts(cat) if store else []}),
                       "application/json")
        elif web_file(path):   # the page's own files, read fresh each time
            f = web_file(path)
            try:
                body = f.read_bytes()
            except OSError:
                self._send(500, "Couldn't read " + f.name, "text/plain")
                return
            self._send(200, body, WEB_TYPES[f.suffix], cache="public, max-age=604800" if f.suffix == ".woff" else "no-cache")
        elif path in ("/", "/index.html"):
            self._send(200, WEB_MISSING, "text/html; charset=utf-8")
        else:
            self._send(404, "Not found", "text/plain")

    def _events(self):
        """Server-sent events: pushes UFC changes (menu, highlighted target,
        selection) to the page the moment they happen."""
        bus = self.server.bus
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        version, data = bus.snapshot()
        query = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
        pid = (query.get("page") or [""])[0][:64] or f"anon-{id(self):x}"   # each page says who it is
        bus.page_open(pid)
        try:
            self.wfile.write(f"data: {json.dumps(dict(data, t=round(time.time(), 3)))}\n\n".encode("utf-8"))
            while not self.server.stopping:
                change = bus.wait(version, timeout=1.0)
                if change is None:
                    if self._gone():
                        break
                    self.wfile.write(b": ping\n\n")   # keeps the connection alive (and finds out soon when it's gone)
                    continue
                version, data = change
                self.wfile.write(f"data: {json.dumps(dict(data, t=round(time.time(), 3)))}\n\n".encode("utf-8"))   # (t: this PC's clock - the timer's)
                if TIMING:   # pushed to this page (sn: the state counter it fetches on)
                    TIMING.rec("sse", pid=pid[:16], sn=data.get("state_n"), jn=data.get("jump_n"))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass   # page closed or reloaded
        finally:
            bus.page_close(pid)

    def _gone(self):
        """Has the page at the other end of the event stream closed? (It sends nothing, so anything to
        read is the connection closing.)"""
        try:
            ready, _, _ = select.select([self.connection], [], [], 0)
            return bool(ready) and not self.connection.recv(1, socket.MSG_PEEK)
        except (OSError, ValueError):
            return True

    def _tgt_op(self, body, state):
        """/api/tgt's op: (HTTP status, answer)."""
        store, tab = state.settlements, state.systab
        num = (lambda v: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None)
        where = (lambda la, lo: la is not None and lo is not None and -90 <= la <= 90 and -180 <= lo <= 180)
        nm = body.get("name", "")
        name = " ".join(nm.split())[:40] if isinstance(nm, str) and all(c.isprintable() for c in nm) else None   # (None: not a name)
        tid = body.get("id") if isinstance(body.get("id"), int) and not isinstance(body.get("id"), bool) else None
        code, answer = 400, {"ok": False}
        if store and body.get("op") == "delete" and tid is not None:
            if store.delete_target(tid):
                code, answer = 200, {"ok": True}
        elif store and body.get("op") == "edit" and tid is not None:
            lat, lon = num(body.get("lat")), num(body.get("lon"))
            old = store.targets.get(tid)
            if old and name is not None and where(lat, lon):
                t = store.edit_target(tid, _short_name(old["body"], old["system"]), name, round(lat, 6), round(lon, 6))
                if t:
                    code, answer = 200, {"ok": True, "tgt": t}
            else:
                answer["why"] = "name" if name is None else "position"
        elif store and body.get("op") == "add":
            with state.lock:
                m = tab.model or {}
                system = m.get("system") or ""
                b = next((e for e in m.get("entries", []) if e.get("kind") == "planet" and isinstance(body.get("body"), str)
                          and str(e.get("name") or "").lower() == body["body"].lower()), None)
            lat, lon = num(body.get("lat")), num(body.get("lon"))
            if b and system and where(lat, lon) and body.get("method") in TARGET_METHODS and name is not None:
                t = store.add_target(system, b["name"], _short_name(b["name"], system), round(lat, 6), round(lon, 6), body["method"], name)
                if t:
                    code, answer = 200, {"ok": True, "tgt": t}
            else:
                answer["why"] = "body" if not b else "name" if name is None else "position"
        if code == 200:
            state.changed()
        return code, answer

    def _body(self, limit=65536):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > limit:
            self.rfile.read(length)
            return None
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    def do_POST(self):
        if self._refused():
            return
        state, writer, engine = self.server.app
        if self.path.split("?", 1)[0] == "/api/select":
            # a page says where it is ({"tab", "sub"}) and/or what it has picked ({"pick": {list: key}}):
            # the UFC's ':' marks that tab, and its knob starts on what was picked
            body = self._body() or {}
            tab = body.get("tab") if body.get("tab") in PAGE_TABS else None
            sub = body.get("sub") if tab and isinstance(body.get("sub"), int) and 1 <= body["sub"] <= len(PAGE_TABS[tab]) else None
            picks = {k: v for k, v in (body.get("pick") or {}).items() if k in UFC_LISTS and isinstance(v, str)} \
                if isinstance(body.get("pick"), dict) else {}
            self.server.bus.note_view(tab=tab, sub=sub, picks=picks)
            self._send(200, json.dumps({"ok": bool(tab or picks)}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/histfilter":
            # a history page's toggle: {"page": "nav" | "contracts", "name": "systems" | ... | "abandoned", "on": true | false}
            body = self._body() or {}
            hist = state.history
            ok = bool(hist) and isinstance(body.get("on"), bool) and hist.set_filter(body.get("page"), body.get("name"), body["on"])
            if ok:
                self.server.bus.note_view()   # the UFC's knob steps through the new list
            self._send(200 if ok else 400, json.dumps({"ok": ok}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/keypad":
            # a page typing with the keypad (Wpt, Atk): {"page", "on": true|false, "s1", "s2", "num": what the scratchpad shows,
            # "opts"?: the five option windows' words while one of its UFC sub-levels is open, "cue"?: the one with the ':'}
            body = self._body() or {}
            pid = body.get("page") if isinstance(body.get("page"), str) and body.get("page") else "anon"
            text = (lambda v, n: str(v)[:n] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else "")
            show = {"s1": text(body.get("s1"), 2), "s2": text(body.get("s2"), 2), "num": text(body.get("num"), 8)}
            if body.get("knob1") is True:   # (and COMM1 too: 1 Syst's REMOTE list, scrolled with it)
                show["knob1"] = True
            if isinstance(body.get("opts"), list) and len(body["opts"]) == 5:
                show["opts"] = [text(o, 4).upper() for o in body["opts"]]
                show["cue"] = body["cue"] if isinstance(body.get("cue"), int) and 1 <= body["cue"] <= 5 else None
            self.server.bus.page_keys(pid[:64], bool(body.get("on")), show)
            self._send(200, json.dumps({"ok": True}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/controls":
            # 4 Setup > Controls: {"op": "learn", "job"} (ASSIGN: the next button pressed, or dial turned) | "cancel" |
            # "clear" {"job"} | "restore" (every job back to the UFC's own layout)
            body, ins, store = self._body() or {}, self.server.inputs, self.server.controls
            op, job = body.get("op"), body.get("job")
            if op in ("learn", "clear") and job not in CONTROL_JOBS:
                self._send(400, json.dumps({"ok": False, "why": "job"}), "application/json")
                return
            if op == "learn":
                ok, why = ins.learn(job) if ins else (False, self.server.inputs_why or "Off")
                self._send(200 if ok else 409, json.dumps({"ok": ok, "why": why}), "application/json")
            elif op == "cancel":
                if ins:
                    ins.cancel()
                self._send(200, json.dumps({"ok": True}), "application/json")
            elif op == "clear":
                store.clear(job)
                self._send(200, json.dumps({"ok": True}), "application/json")
            elif op == "restore":
                if ins:
                    ins.cancel()
                store.restore()
                self._send(200, json.dumps({"ok": True}), "application/json")
            else:
                self._send(400, json.dumps({"ok": False, "why": "op"}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/timer":
            # the stopwatch / countdown timer (2 Nav > HSI): {"op": "sel" | "ctl" | "set" | "clr", ...} - see UIBus.timer_op
            body = self._body() or {}
            out = self.server.bus.timer_op(body if isinstance(body, dict) else {})
            self._send(200 if out.get("ok") or out.get("why") in ("running", "set") else 400, json.dumps(out), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/scratch":
            # a page's own words for the UFC's scratchpad while it shows (Atk's release countdown, the HSI's steer-to point):
            # {"page", "s1", "s2", "num", "com1"?, "com2"?: the COM windows}
            body = self._body() or {}
            pid = body.get("page") if isinstance(body.get("page"), str) and body.get("page") else "anon"
            text = (lambda v, n: str(v)[:n] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else "")
            show = {"s1": text(body.get("s1"), 2), "s2": text(body.get("s2"), 2), "num": text(body.get("num"), 8)}
            for k in ("com1", "com2"):
                if text(body.get(k), 2):
                    show[k] = text(body.get(k), 2)
            t0 = time.time()
            self.server.bus.page_scratch(pid[:64], show if any(show.values()) else {})
            self._send(200, json.dumps({"ok": True}), "application/json")
            if TIMING:
                TIMING.rec("scr", w=round(t0, 4), num=show["num"], ms=_ms(time.time() - t0))
            return
        if self.path.split("?", 1)[0] == "/api/timing":
            # --timing-log: the page's timings, every 2 s ({"pn": its clock, "dn": Date.now(), "recs": [records]})
            body = self._body(limit=8_000_000)
            recs = body.get("recs") if isinstance(body, dict) else None
            if not TIMING or not isinstance(recs, list):
                self._send(404 if not TIMING else 400, json.dumps({"ok": False}), "application/json")
                return
            recs = [r for r in recs[:50000] if isinstance(r, dict)]
            TIMING.lines([{"k": "batch", "w": round(time.time(), 4), "n": len(recs), "pn": body.get("pn"), "dn": body.get("dn")}] + recs)
            self._send(200, json.dumps({"ok": True}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/tgt":
            # your targets (2 Nav > Wpt): {"op": "add", "body": a body in this system (not a star), "lat", "lon",
            # "method": "manual"|"overfly"|"desig", "name" (optional)}, {"op": "edit", "id", "name", "lat", "lon"} or {"op": "delete", "id"}
            # - and "u"?: the UFC press it answers, as /api/nav's (acted on once, whichever pages answer it)
            body = self._body() or {}
            state = self.server.app[0]
            u = state.nav.token(body)
            if not u:
                code, answer = self._tgt_op(body, state)
            else:
                with state.nav.tlock:
                    answer = state.nav.answered("u", u)
                    code = 200
                    if answer is None:
                        code, answer = self._tgt_op(body, state)
                        if code == 200:
                            state.nav.keep("u", u, answer)
            self._send(code, json.dumps(answer), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/nav":
            # 2 Nav's waypoint system (NavBoard), in the system the System tab has - {"op": ...}:
            #   "mark" {"body", "lat", "lon", "alt"?, "method": "overfly"|"desig" (HUD VV)|"xb" (HUD X-B), "dsg"?: designate it too, "n"?: the UFC MK it answers}
            #   "xb" {"act": "take", "body", "lat", "lon", "brg"} | {"act": "del", "id"} | {"act": "clr"}: HUD X-B's bearings (10 kept, per body)
            #   "mkedit" {"slot", "lat", "lon"}, "mkdel" {"slot"}, "mkstor" {"slot", "name"?}: a mark kept as a waypoint
            #   "oap" {"id": a waypoint, "rng": m (0: none), "brg": degrees}: its offset aimpoint
            #   "dsg" {"key", "n"?: the UFC DSG it answers} (again: the offset aimpoint, then nothing), or {"off": true}
            #   "seq" {"seq": 1-3, "act": "ins" ("id", "after"?) | "del" ("id") | "mv" ("id", "to") | "clr"}, "setseq" {"seq": "1"-"3" | "atk" | "none"}
            #   "steer" {"key"} or {"step": +-n: the HSI's COMM2}, "auto" {"from"}: AUTO sequencing's next point, "automode" {"on"}
            #   "tot" {"seq": 1-3, "tgt"?: a waypoint in it, "tot"?: Zulu seconds into the day, "gspd"?: knots} (null: none)
            #   "plan" {"hdg", "kts", "base", "step", "role", "cs", "profile"}, "build", "load" {"code"} or {"clip": true}
            #   "share" {"code"} or {"clip": true}, "seq"?: 1-3: a waypoint or flight plan code (or Atk's plan code) loaded
            #   any of them "u"?: the UFC press it answers ("c2:<COMM2 pull>", "k:<key>"...), acted on once whichever pages answer
            body = self._body() or {}
            code, answer = self.server.app[0].nav.op(body)
            self._send(code, json.dumps(answer), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/dialcue":
            # what a page's dials are doing, for the UFC's scratchpad: {"page", "z": "Z+"|"Z-"|"", "t": "<<"|">>"|"UP"|"DN"|""}
            body = self._body() or {}
            z = body.get("z") if body.get("z") in ("Z+", "Z-", "") else ""
            t = body.get("t") if body.get("t") in ("<<", ">>", "UP", "DN", "") else ""
            pid = body.get("page") if isinstance(body.get("page"), str) and body.get("page") else "anon"
            self.server.bus.page_cue(pid[:64], {"z": z, "t": t})
            self._send(200, json.dumps({"ok": True}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/clip":
            # the copy / paste button: {"text": a system's name, "pull": the UFC pull it answers, or null}
            body = self._body() or {}
            pull = body.get("pull") if isinstance(body.get("pull"), int) else None
            code, answer = self.server.clip.press(body.get("text") if isinstance(body.get("text"), str) else "", pull)
            self._send(code, json.dumps(answer), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/uplink":
            # System Data Uplink Synchronise: fetch the system you're in from Spansh and EDSM now (202), or why not:
            # 429 {"wait": seconds} (once a minute), 409 {"why": "busy" | "offline" | "nowhere"}
            self._body()
            code, answer = state.systab.request_uplink()
            self._send(code, json.dumps(answer), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/bootfx":
            # what a page's screens are showing, for the UFC's displays: {"page": its id, "fx": the terminal
            # still off ("off"), its BIOS or waiting screen ("ucec"), a vehicle's start-up ("ship", "srv",
            # "fighter", "nomad") or the board itself ("")}
            body = self._body() or {}
            fx = body.get("fx") if body.get("fx") in UFC_PAGE_FX else None
            pid = body.get("page") if isinstance(body.get("page"), str) and body.get("page") else "anon"
            if fx is not None:
                self.server.bus.page_fx(pid[:64], fx)
            self._send(200 if fx is not None else 400, json.dumps({"ok": fx is not None}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/ocor":
            body = self._body(limit=512 * 1024)
            if body is None:
                self._send(413, json.dumps({"ok": False, "error": "That paste is too large."}), "application/json")
                return
            try:
                briefing = self.server.ocor.set(str(body.get("text") or ""))
            except ValueError as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}), "application/json")
                return
            self.server.bus.note_view()   # the UFC's objective count changes
            self._send(200, json.dumps({"ok": True, "count": len(briefing["objectives"])}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/settlement-layout":
            # the layout you've confirmed for a settlement: {"key", "layout", "system", "name", "economy"}
            body = self._body() or {}
            key, layout = body.get("key"), body.get("layout")
            store, plans = self.server.app[0].settlements, self.server.app[0].schematics
            ok = (isinstance(key, str) and re.fullmatch(r"m:\d{1,20}|n:.{1,300}", key) is not None and
                  isinstance(layout, str) and 0 < len(layout) <= 100 and bool(plans and plans.has(layout)) and bool(store))
            if ok:
                text = (lambda v: str(v)[:200] if isinstance(v, str) else "")
                ok = store.save(key, layout, text(body.get("system")), text(body.get("name")), text(body.get("economy")))
            if ok:
                heading_from_docking(store, plans, key)   # docked there before: its heading, for this layout
            self._send(200 if ok else 400, json.dumps({"ok": ok}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/settlement-heading":
            # Align Settlement: {"key", "layout", "heading" (degrees: the compass bearing of the layout's up), "system", "name"}
            body = self._body() or {}
            key, layout, h = body.get("key"), body.get("layout"), body.get("heading")
            store, plans = self.server.app[0].settlements, self.server.app[0].schematics
            ok = (isinstance(key, str) and re.fullmatch(r"m:\d{1,20}|n:.{1,300}", key) is not None and
                  isinstance(layout, str) and 0 < len(layout) <= 100 and bool(plans and plans.has(layout)) and bool(store) and
                  isinstance(h, (int, float)) and not isinstance(h, bool) and math.isfinite(h) and 0 <= h <= 360)
            if ok:
                text = (lambda v: str(v)[:200] if isinstance(v, str) else "")
                ok = store.save_heading(key, layout, h, "manual", system=text(body.get("system")), name=text(body.get("name")))
            saved = store.headings_for([key]).get(key) if ok else None
            self._send(200 if ok else 400, json.dumps({"ok": ok, "heading": saved}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/uplink-source":
            # Spansh Uplink / EDSM Uplink: {"source": "spansh"|"edsm", "on": true|false (absent: flip it)}
            body = self._body() or {}
            ups, name = getattr(self.server.app[0], "uplinks", None), body.get("source")
            ok = bool(ups) and name in ("spansh", "edsm") and (body.get("on") is None or isinstance(body.get("on"), bool))
            if ok:
                ups.set(name, (not getattr(ups, name)) if body.get("on") is None else body["on"])
            self._send(200 if ok else 400, json.dumps({"ok": ok, "sources": ups.view() if ups else None}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/settlement-type":
            # the schematic type you've picked for a settlement: {"key", "category" ("" = the data's), "system", "name"}
            body = self._body() or {}
            key, cat = body.get("key"), body.get("category")
            store = self.server.app[0].settlements
            ok = (isinstance(key, str) and re.fullmatch(r"m:\d{1,20}|n:.{1,300}", key) is not None and
                  isinstance(cat, str) and re.fullmatch(r"[a-z]{0,30}", cat) is not None and bool(store))
            if ok:
                text = (lambda v: str(v)[:200] if isinstance(v, str) else "")
                ok = store.save_type(key, cat, text(body.get("system")), text(body.get("name")))
            self._send(200 if ok else 400, json.dumps({"ok": ok}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/remote":
            # 1 Syst's CURRENT SYSTEM / REMOTE: {"system": a system to show (REMOTE)} or {"off": true} (the current system)
            body = self._body() or {}
            state = self.server.app[0]
            if body.get("off") is True:
                state.remote.off()
                state.changed()
                code, answer = 200, {"ok": True, "remote": state.remote_view()}
            else:
                code, answer = remote_pick(state, body.get("system"))
            self._send(code, json.dumps(answer), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/settings":
            # 4 Setup > Settings: {"key": a setting, "value": its new value} - kept for the next start (RESTART: now)
            body = self._body() or {}
            key = body.get("key") if isinstance(body, dict) else None
            if key not in SETTING_DEFAULTS:
                self._send(400, json.dumps({"ok": False, "why": "No such setting"}), "application/json")
                return
            try:
                value = self.server.settings.set(key, body.get("value"))
            except ValueError as exc:
                self._send(400, json.dumps({"ok": False, "why": str(exc)}), "application/json")
                return
            except OSError as exc:
                self._send(500, json.dumps({"ok": False, "why": f"Couldn't save it ({exc})"}), "application/json")
                return
            self.server.settings_cache = None
            log(f"Setting changed on the web page: {key} = {value!r} (from the next start).")
            self._send(200, json.dumps({"ok": True, "view": settings_view(self.server)}), "application/json")
            return
        if self.path.split("?", 1)[0] == "/api/restart":   # 4 Setup > Settings' RESTART: closes as Exit does, then starts again
            self._send(200, json.dumps({"ok": True}), "application/json")
            log("Restart pressed on the web page - closing, to start again.")
            self.server.restart = True
            self.server.stopping = True
            self.server.bus.update()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path.split("?", 1)[0] == "/api/quit":
            self._send(200, json.dumps({"ok": True}), "application/json")
            log("Exit pressed on the web page - stopping.")
            self.server.stopping = True
            self.server.bus.update()   # wakes event streams so they finish
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path.split("?", 1)[0] != "/api/regenerate":
            self._send(404, "Not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            key = json.loads(self.rfile.read(length) or b"{}").get("key", "")
        except ValueError:
            key = ""
        mission = state.contracts.for_backstory(key)
        ok = bool(mission) and writer.request(mission, force=True)
        self._send(200 if ok else 409, json.dumps({"ok": ok}), "application/json")


# --------------------------------------------------------------------------- #
# Settings (4 Setup > Settings)
# --------------------------------------------------------------------------- #
SETTINGS_FILE = DATA_DIR / "settings.json"
ENGINE_CHOICES = ("auto", "claude", "codex", "none")   # AUTO: Claude Code if it's on this PC, else Codex, else none
SETTING_DEFAULTS = {"journal_dir": "", "engine": "auto", "model": "", "lan": False, "controllers": True, "open_page": True}
SETTING_FLAGS = {"journal_dir": "--journal-dir", "engine": "--engine", "model": "--model", "lan": "--host",
                 "controllers": "--no-ufc", "open_page": "--no-browser"}   # the command-line option that wins over each


def clean_setting(key, value, check=True):
    """A setting's value as kept - or ValueError, saying why it can't be. check: a folder must be there (not on loading
    one saved: a drive that isn't plugged in yet keeps its setting)."""
    if key == "journal_dir":
        if not isinstance(value, str) or len(value) > 400:
            raise ValueError("Not a folder")
        value = value.strip().strip('"').strip()
        if value and check and not Path(value).expanduser().is_dir():
            raise ValueError("There's no such folder")
        return value
    if key == "engine":
        if value not in ENGINE_CHOICES:
            raise ValueError("Auto, Claude, ChatGPT or none")
        return value
    if key == "model":
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:\-]{0,60}", value.strip()):
            raise ValueError("A model's name: letters, digits and . - _ : only")
        return value.strip()
    if key in ("lan", "controllers", "open_page"):
        if not isinstance(value, bool):
            raise ValueError("On or off")
        return value
    raise ValueError("No such setting")


class Settings:
    """4 Setup > Settings: what the FT3000 starts with - your journal folder, the AI for backstories, whether other devices
    on your network may open the page, the game controllers, opening the page - kept in settings.json in your data
    folder. Each takes effect at the next start (RESTART on the page starts it again now); an option given on the command
    line wins over its setting, for that run."""

    def __init__(self, path):
        self.path, self.lock = Path(path), threading.Lock()
        self.values = dict(SETTING_DEFAULTS)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        except (OSError, ValueError) as exc:
            log(f"Couldn't read {self.path.name} ({exc}) - starting with the default settings.")
            data = {}
        for k, v in (data.items() if isinstance(data, dict) else ()):
            if k in SETTING_DEFAULTS:
                try:
                    self.values[k] = clean_setting(k, v, check=False)
                except ValueError:
                    pass

    def get(self, key):
        return self.values[key]

    def set(self, key, value):
        """Keep one (ValueError if it can't be): its value as kept."""
        value = clean_setting(key, value)
        with self.lock:
            new = dict(self.values, **{key: value})
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(new, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
            self.values = new
        return value


def auto_engine(cli_path=None):
    """AUTO's pick: Claude Code if it's on this PC, else Codex (ChatGPT), else none (no backstories)."""
    if cli_path:
        return "codex" if "codex" in Path(cli_path).name.lower() else "claude"
    if shutil.which("claude"):
        return "claude"
    if shutil.which("codex"):
        return "codex"
    return "none"


def resolve_start(args, settings):
    """What this run starts with, into args: each option given on the command line, else its setting (else the
    built-in default). Returns (the settings' values it started with, the settings the command line overrode)."""
    given = {k for k, flag in SETTING_FLAGS.items()
             if getattr(args, flag[2:].replace("-", "_")) is not None}
    started = {k: settings.get(k) for k in SETTING_DEFAULTS}
    if args.journal_dir is None:
        args.journal_dir = settings.get("journal_dir") or str(DEFAULT_JOURNAL_DIR)
    if args.engine is None:
        args.engine = settings.get("engine")
    if args.engine == "auto":
        args.engine = auto_engine(args.cli_path)
    if args.model is None:
        args.model = settings.get("model") or None
    if args.host is None:
        args.host = "0.0.0.0" if settings.get("lan") else "127.0.0.1"
    if args.no_ufc is None:
        args.no_ufc = not settings.get("controllers")
    if args.no_browser is None:
        args.no_browser = not settings.get("open_page")
    return started, given


def journal_count(folder):
    """How many journals a folder holds, and when the newest was written (or None)."""
    n, newest = 0, None
    try:
        for f in Path(folder).expanduser().glob("Journal.*.log"):
            n += 1
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            newest = m if newest is None or m > newest else newest
    except OSError:
        pass
    return n, newest


def lan_addresses():
    """This PC's addresses on your network (IPv4, not 127.x): where other devices find the page."""
    found = []
    try:   # the one it would reach the internet by (a UDP "connection" sends nothing)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    out = []
    for a in found:
        if a and not a.startswith(("127.", "0.", "169.254.")) and a not in out:
            out.append(a)
    return out


def settings_view(server):
    """4 Setup > Settings' record (GET /api/settings): each setting - kept, started with, overridden by the command line
    (flag), waiting for a restart (pending) - with what the page shows beside it, and the About block."""
    s, run = server.settings, server.run_opts
    now = time.time()
    cache = getattr(server, "settings_cache", None)
    if not cache or now - cache["t"] > 5:   # (journal counts and addresses: looked at every 5 seconds at most)
        kept = s.get("journal_dir") or str(DEFAULT_JOURNAL_DIR)
        cache = {"t": now, "addr": lan_addresses(), "tools": {"claude": bool(shutil.which("claude")), "codex": bool(shutil.which("codex"))},
                 "jr": {run["journal_dir"]: journal_count(run["journal_dir"])}}
        if kept not in cache["jr"]:
            cache["jr"][kept] = journal_count(kept)
        server.settings_cache = cache
    rows = {}
    for k in SETTING_DEFAULTS:
        rows[k] = {"value": s.get(k), "flag": SETTING_FLAGS[k] if k in server.given else "",
                   "pending": k not in server.given and s.get(k) != server.started[k]}
    kept = s.get("journal_dir") or str(DEFAULT_JOURNAL_DIR)
    n, newest = cache["jr"].get(kept, (0, None))
    rows["journal_dir"].update(folder=kept, default=str(DEFAULT_JOURNAL_DIR), found=n,
                               newest=datetime.fromtimestamp(newest, timezone.utc).isoformat() if newest else None,
                               running=run["journal_dir"])
    state = server.app[0]
    rows["engine"].update(running=run["engine"], tools=cache["tools"], auto=auto_engine(),
                          ok=state.engine_ok, msg=state.engine_msg, model=run["model"])
    rows["lan"].update(running=run["lan"], port=run["port"], addresses=cache["addr"])
    rows["controllers"].update(running=run["controllers"])
    rows["open_page"].update(running=run["open_page"])
    binds = server.binds
    about = {"version": VERSION, "program": str(SCRIPT_DIR), "data": str(DATA_DIR), "project": PROJECT_URL,
             "bindings": [Path(f).name for f in (getattr(binds, "files", None) or [])] if binds else [],
             "bindings_dir": str(binds.folder) if binds else ""}
    return {"run": server.bus.data["run"], "settings": rows, "about": about,
            "pending": any(r["pending"] for r in rows.values())}


def restart_self():
    """RESTART (4 Setup > Settings), once this copy has closed: the FT3000 run again as it was started, with the settings
    as they are now - in a window of its own on Windows. The page it had open finds the new run by itself (no new tab)."""
    cmd = [sys.executable, str(Path(sys.argv[0]).resolve())] + sys.argv[1:]
    env = dict(os.environ, FT3000_RESTARTED="1")
    kw = {"creationflags": subprocess.CREATE_NEW_CONSOLE} if sys.platform == "win32" else {"start_new_session": True}
    try:
        subprocess.Popen(cmd, cwd=os.getcwd(), env=env, **kw)
        log("Starting again (in a new window)..." if sys.platform == "win32" else "Starting again...")
    except OSError as exc:
        log(f"Couldn't start again ({exc}) - start it from its shortcut.")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def parse_args():
    p = argparse.ArgumentParser(description="UCEC FT3000: Elite Dangerous mission-target board with AI backstories, and the WinWing UFC.")
    p.add_argument("--engine", choices=list(ENGINE_CHOICES), default=None,
                   help="auto = Claude Code if it's on this PC, else Codex, else none (default: 4 Setup > Settings, else auto); "
                        "claude = Claude Code with your Claude subscription; codex = Codex CLI with your ChatGPT plan; none = no backstories")
    p.add_argument("--model", default=None,
                   help="optional model for the AI tool, e.g. haiku or sonnet for Claude (default: 4 Setup > Settings, else the tool's own)")
    p.add_argument("--cli-path", default=None,
                   help="full path to the claude/codex program, if it isn't found automatically")
    p.add_argument("--journal-dir", default=None,
                   help="folder containing Journal.*.log files (default: 4 Setup > Settings, else Saved Games\\Frontier Developments\\Elite Dangerous)")
    p.add_argument("--days", type=int, default=30,
                   help="how many days of journals to scan at startup (default 30)")
    p.add_argument("--host", default=None,
                   help="127.0.0.1 = this PC only; 0.0.0.0 = other devices on your network too (default: 4 Setup > Settings, else this PC only)")
    p.add_argument("--port", type=int, default=8642)
    p.add_argument("--timeout", type=int, default=180, help="seconds to wait for one backstory")
    p.add_argument("--no-browser", action="store_true", default=None, help="don't open the page automatically (default: 4 Setup > Settings)")
    p.add_argument("--test", action="store_true",
                   help="check the AI login and write one sample backstory, then exit")
    ufc = p.add_argument_group("WinWing UFC")
    ufc.add_argument("--no-ufc", action="store_true", default=None, help="run the web board only, without the UFC or other game controllers (default: 4 Setup > Settings)")
    p.add_argument("--no-edsm", action="store_true", help="start with EDSM Uplink off (the System list's toggle: no traffic, deaths or exploration value on Syst, no EDSM coordinates for OCOR)")
    p.add_argument("--no-spansh", action="store_true", help="start with Spansh Uplink off (the System list's toggle; with EDSM Uplink off too, Syst shows your journal records alone)")
    p.add_argument("--timing-log", action="store_true",
                   help="note when each position reading is written, seen, sent and drawn, and how long each step takes - the "
                        "board's and the page's (frame by frame on Nav > Atk) - in timing_log.jsonl in your data folder (for a jerky display)")
    ufc.add_argument("--ufc-learn", action="store_true",
                     help="find the UFC's brightness, COMM2 volume and COMM1 volume knobs (run once), then exit")
    ufc.add_argument("--bindings-dir", default=str(DEFAULT_BINDINGS_DIR),
                     help="folder holding your Elite .binds files")
    ufc.add_argument("--any-window", action="store_true",
                     help="send UFC keypresses even when Elite isn't the active window")
    ufc.add_argument("--list-keys", action="store_true",
                     help="show which key every UFC button will press, then exit")
    ufc.add_argument("--test-key", metavar="NAME",
                     help="press one key after a 5 s countdown, then exit. NAME is a UFC label "
                          "(e.g. GXY), an Elite action (e.g. GalaxyMapOpen), or DOCK for the docking sequence")
    return p.parse_args()


def run_key_test(bindings: EliteBindings, name: str, require_focus: bool):
    bindings.load()
    if name.upper() == "DOCK":
        label, actions, hold, gap = "Request docking", DOCKING_MACRO, MACRO_HOLD, MACRO_GAP
    else:
        action = next((a for page in UFC_MENUS.values() for lab, a in page["options"]
                       if a and lab.upper() == name.upper()), name)
        if action.startswith("@"):
            print(f"{name.upper()} works the web page, not Elite - there's no key to press.")
            return
        label, actions, hold, gap = name, [action], KEY_HOLD, 0.0
    for action in actions:
        combo = bindings.lookup(action)
        if combo is None:
            print(f"'{action}' has no keyboard binding in your Elite bindings, so there's nothing to press.")
            sys.exit(1)
        print(f"{action}: {key_label(combo)}")
    sender = KeySender(bindings, require_focus=require_focus)
    if sender.dry_run:
        print("Not on Windows, so this is a dry run - no keys will be pressed.")
    for i in range(5, 0, -1):
        print(f"Switch to Elite now... {i}", flush=True)
        time.sleep(1)
    sender._do(label, actions, hold, gap)
    if sender.sent:
        print("Sent. Check that Elite responded.")
    else:
        print("Nothing was sent (see the message above).")


def start_ufc(bindings: EliteBindings, require_focus: bool, board=None, bus=None, ocor=None, store=None):
    """Start reading the UFC (and whatever else has a job: 4 Setup > Controls) and sending keys.
    Returns (the controller, the reader), or (None, None)."""
    try:
        import hid
    except ImportError:
        log("UFC off: the hidapi package isn't installed (pip install hidapi).")
        return None, None
    bindings.load()
    sender = KeySender(bindings, require_focus=require_focus)
    sender.start()
    if board is not None:
        board.keys = sender   # (the copy button's second press pastes with it)
    controller = UFCController(UFCDisplay(), sender, board=board, bus=bus, ocor=ocor)
    inputs = HidInputs(controller, hid, store or ControlStore())
    inputs.start()
    if not require_focus:
        log("UFC keys will be sent to whichever window is active (--any-window).")
    return controller, inputs


def run_test(engine, timeout):
    ok, msg = engine.check()
    print(msg)
    if not ok:
        sys.exit(1)
    number, incept, t0 = dossier_ids("kirsten vance", "")
    facts = "\n".join(["MODE: IN SHIP", "FILE: PERSON", f"DATE: {game_date(now_utc())}", "TARGET: Kirsten Vance",
                       "ROLE: Pirate lord", "TARGET FACTION: Black Sun Crew", "CONTRACT: Assassinate Known Pirate: Kirsten Vance",
                       "ISSUED BY: LHS 3447 Defence Force", "LAST KNOWN WHEREABOUTS: Trevithick Dock, LHS 3447",
                       "REWARD: 1,250,000 CR", "WING CONTRACT: no",
                       f"INCEPT DATE: {game_date(incept)} ({dossier_age(incept, t0)}; a four-year lifespan)",
                       "SHIP SCAN: none yet", "THREAT: HIGH (provisional - no scan yet)"])
    print("Writing a sample subject file (this uses a small amount of your subscription allowance)...\n")
    fields, problems = ask_dossier(engine, {"name": "Kirsten Vance", "kind": "person", "facts": facts, "ship_known": False}, timeout)
    for k, v in fields.items():
        print(f"{k.replace('_', ' ').upper()}: {v}")
    if problems:
        print("\nStill didn't fit: " + "; ".join(problems))


def set_console_title(title):
    """Name the console window (Windows), so it's easy to find and close."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# One copy at a time: a copy still running from before (its page closed without Exit) is closed as this one starts
# --------------------------------------------------------------------------- #
PID_FILE = DATA_DIR / "ft3000.pid"   # the copy running on this data: {"pid", "port", "version", "started"}
OLD_PID_FILE = SCRIPT_DIR / "ft3000.pid"   # (where versions before 3.01.42 wrote it)
DATA_NAMES = ("star_coords.sqlite", "journal_records.sqlite", "settlements.sqlite", "system_archive.sqlite", "edsm_cache.json",
              "target_backstories.json", "ocor_briefing.json", "uplink_settings.json", "remote_system.json", "ufc_axes.json",
              "controls.json")   # what move_old_data copies across: your waypoints are in star_coords.sqlite


def move_old_data():
    """The first start with the data in Saved Games: copy it across from the program's folder (where versions before
    3.01.42 kept it) - once, and only into a data folder that has none of it yet. The old copies are left where they
    were (a backup; safe to delete). -> how many files were copied."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log(f"Couldn't make the data folder {DATA_DIR} ({exc}) - nothing will be saved.")
        return 0
    if DATA_DIR.resolve() == SCRIPT_DIR or any((DATA_DIR / n).exists() for n in DATA_NAMES):
        return 0
    copied = []
    for n in DATA_NAMES:
        for f in (SCRIPT_DIR / n, SCRIPT_DIR / (n + "-wal"), SCRIPT_DIR / (n + "-shm")):
            if f.is_file():
                try:
                    shutil.copy2(f, DATA_DIR / f.name)
                    copied.append(f.name)
                except OSError as exc:
                    log(f"Couldn't copy {f.name} to {DATA_DIR} ({exc}).")
    if copied:
        log(f"Your data now lives in {DATA_DIR}: copied {len(copied)} files there from {SCRIPT_DIR} "
            "(the old copies are left there - a backup, safe to delete).")
    return len(copied)
APP_NAME = "UCEC FT3000"


def proc_info(pid):
    """(what the process is - its program on Windows, its command line elsewhere - and when it started, epoch s) for a
    running process, or None (not running, or not ours to see)."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.CloseHandle.argtypes = [wintypes.HANDLE]
            k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
            k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
            h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            try:
                code = wintypes.DWORD()
                if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:   # (STILL_ACTIVE)
                    return None
                buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
                exe = buf.value if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
                ft = [wintypes.FILETIME() for _ in range(4)]
                if not k32.GetProcessTimes(h, *[ctypes.byref(f) for f in ft]):
                    return None
                return exe, ((ft[0].dwHighDateTime << 32) | ft[0].dwLowDateTime) / 1e7 - 11644473600
            finally:
                k32.CloseHandle(h)
        except Exception:
            return None
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        stat = Path(f"/proc/{pid}/stat").read_text()
        ticks = int(stat.rsplit(")", 1)[1].split()[19])   # (starttime: clock ticks after boot)
        boot = next(float(x.split()[1]) for x in Path("/proc/stat").read_text().splitlines() if x.startswith("btime "))
        if " Z " in stat.rsplit(")", 1)[1][:3]:   # (a zombie: gone)
            return None
        return cmd, boot + ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, StopIteration, IndexError):
        try:
            os.kill(pid, 0)
            return "", 0.0   # (running, but nothing more to tell)
        except OSError:
            return None


def is_our_copy(rec, info):
    """Is the process the PID file names (its info: proc_info) still that FT3000 - not another program given its number?"""
    what, started = info
    if abs(started - float(rec.get("started") or 0)) > 2:   # (started when the file says it did: the same process)
        return False
    if sys.platform == "win32":
        exe = os.path.basename(what).lower()
        return exe.startswith("python") or exe in ("py.exe", "pyw.exe")
    return "ed_target_board.py" in what


def ft3000_on(port):
    """The FT3000 answering on a port of this PC - {"version", "pid"} (an earlier version: neither) - or None (nothing
    there, or something else)."""
    import http.client
    for path in ("/api/hello", "/"):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            conn.request("GET", path)
            r = conn.getresponse()
            body = r.read(65536)
        except (OSError, http.client.HTTPException):
            return None
        finally:
            conn.close()
        if path == "/api/hello" and r.status == 200:
            try:
                j = json.loads(body)
            except ValueError:
                j = {}
            if isinstance(j, dict) and j.get("app") == APP_NAME:
                return {"version": j.get("version"), "pid": j.get("pid")}
        elif path == "/" and r.status == 200 and f"<title>{APP_NAME}</title>".encode() in body:
            return {"version": None, "pid": None}   # (before 3.01.34: no /api/hello)
    return None


def port_listening(port):
    """Is anything listening on this port of this PC?"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _gone(pid, rec, wait):
    """Wait (s) for a process to end; True once it has."""
    end = time.time() + wait
    while time.time() < end:
        info = proc_info(pid)
        if info is None or (rec and not is_our_copy(rec, info)):
            return True
        time.sleep(0.2)
    return False


def close_previous(port):
    """Before this copy starts: another FT3000 still running - on this port, or from this folder (PID_FILE) - is asked to
    stop as Exit does (it blanks the UFC as it goes), and one that doesn't (hung) is ended. The PID file is then cleared
    for this copy's own."""
    rec = None
    for f in (PID_FILE, OLD_PID_FILE):   # (an earlier version's is in the program's folder)
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            rec = rec if isinstance(rec, dict) and isinstance(rec.get("pid"), int) else None
        except (OSError, ValueError):
            rec = None
        if rec:
            break
    if rec and rec["pid"] == os.getpid():
        rec = None
    ports = [port] + ([rec["port"]] if rec and isinstance(rec.get("port"), int) and rec["port"] != port else [])
    import http.client
    for p in ports:
        who = ft3000_on(p)
        if not who:
            continue
        log(f"{APP_NAME} {who['version'] or '(an earlier version)'} is still running on port {p} - closing it, as Exit does.")
        conn = http.client.HTTPConnection("127.0.0.1", p, timeout=3)
        try:
            conn.request("POST", "/api/quit", body=b"{}", headers={"Content-Type": "application/json"})
            conn.getresponse().read()
        except (OSError, http.client.HTTPException):
            pass
        finally:
            conn.close()
        end = time.time() + 8
        while time.time() < end and port_listening(p):
            time.sleep(0.2)
        pid = who.get("pid") if isinstance(who.get("pid"), int) else None
        if pid and pid != os.getpid():
            same = rec if rec and rec["pid"] == pid else None
            if not _gone(pid, same, 6):
                log(f"It hasn't finished closing - ending it (process {pid}).")
                _end(pid)
        else:
            time.sleep(1.5)   # (an earlier version: a moment to blank the UFC and go)
        log("Closed." if not port_listening(p) else f"It's still on port {p}.")
    if rec and rec["pid"] != os.getpid():   # (one that didn't answer - hung, or on a port it no longer has)
        info = proc_info(rec["pid"])
        if info and is_our_copy(rec, info):
            log(f"{APP_NAME} {rec.get('version') or ''} started from this folder (process {rec['pid']}) is still running "
                f"but not answering - ending it.")
            _end(rec["pid"])
    for f in (PID_FILE, OLD_PID_FILE):
        try:
            f.unlink()
        except OSError:
            pass


def _end(pid):
    """End a process (Windows: at once; elsewhere: asked, then made to)."""
    try:
        os.kill(pid, signal.SIGTERM)   # (Windows: TerminateProcess)
    except OSError:
        return
    if not _gone(pid, None, 3) and hasattr(signal, "SIGKILL"):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        _gone(pid, None, 2)


def write_pid_file(port):
    """This copy, for the next to find: PID_FILE."""
    info = proc_info(os.getpid())
    try:
        PID_FILE.write_text(json.dumps({"pid": os.getpid(), "port": port, "version": VERSION,
                                        "started": info[1] if info else time.time()}), encoding="utf-8")
    except OSError as exc:
        log(f"Couldn't write {PID_FILE.name} ({exc}).")


def clear_pid_file():
    """This copy closing: its PID_FILE gone (if it's still this copy's)."""
    try:
        if json.loads(PID_FILE.read_text(encoding="utf-8")).get("pid") == os.getpid():
            PID_FILE.unlink()
    except (OSError, ValueError, AttributeError):
        pass


class BoardServer(ThreadingHTTPServer):
    """The web server. On Windows its port is its alone (SO_EXCLUSIVEADDRUSE): Python's usual SO_REUSEADDR there would
    let a second copy share a port another is still listening on, and answer the page in its place."""
    if sys.platform == "win32":
        allow_reuse_address = False

        def server_bind(self):
            opt = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if opt is not None:
                self.socket.setsockopt(socket.SOL_SOCKET, opt, 1)
            super().server_bind()


def open_server(host, port, handler):
    """The web server on its port - on Windows, exclusively; if that's refused with nothing listening there (only closed
    connections lingering, as just after another copy closed), as Python usually opens it."""
    try:
        return BoardServer((host, port), handler)
    except OSError:
        if sys.platform != "win32" or port_listening(port):
            raise
    return ThreadingHTTPServer((host, port), handler)


def main():
    global TIMING
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    args = parse_args()
    if args.ufc_learn:
        run_ufc_learn()
        return
    settings = Settings(SETTINGS_FILE)
    started, given = resolve_start(args, settings)   # (the command line's options, else 4 Setup > Settings)

    engine = make_engine(args.engine, args.model, args.cli_path)

    if args.test:
        run_test(engine, args.timeout)
        return

    bindings = EliteBindings(Path(args.bindings_dir).expanduser())
    if args.list_keys:
        bindings.load()
        print(ufc_key_table(bindings))
        return
    if args.test_key:
        run_key_test(bindings, args.test_key, require_focus=not args.any_window)
        return

    close_previous(args.port)   # (a copy still running from before - its page closed without Exit: closed first)
    move_old_data()   # (the first start with your data in Saved Games: copied across from the program's folder)
    log(f"Your data: {DATA_DIR}")

    if args.timing_log:
        try:
            TIMING = TimingLog(TIMING_FILE)
            log(f"Timing log on: {TIMING_FILE} (started afresh; open Nav > Atk with a target and fly a straight run)")
        except OSError as exc:
            log(f"Couldn't start the timing log ({TIMING_FILE}): {exc}")
    state = BoardState(CACHE_FILE, EXOBIO_FILE)
    journal_dir = Path(args.journal_dir).expanduser()
    state.records = JournalRecords(RECORDS_FILE)   # your journals' own records of systems, filled from the old ones once
    state.history = JournalHistory(state.records)  # and your history (Nav › Hist, Contracts › History), in the same file

    def read_old_journals():
        state.records.backfill(journal_dir)
        state.history.backfill(journal_dir)
    threading.Thread(target=read_old_journals, daemon=True, name="records").start()
    writer = BackstoryWriter(state, engine, args.timeout)
    writer.start()
    state.settlements = SettlementLayouts(SETTLEMENTS_FILE)   # before the journal: a docking there files a heading
    state.remote = RemoteSystem(REMOTE_FILE)   # 1 Syst's REMOTE (before the fetcher: it fetches the system 1 Syst shows)
    state.schematics = SchematicStore(SCHEMATICS_DIR)
    JournalWatcher(journal_dir, state, writer, args.days).start()
    uplinks = UplinkSettings(UPLINK_FILE, spansh_off=bool(args.no_spansh), edsm_off=bool(args.no_edsm))   # the System list's toggles
    state.uplinks = uplinks
    if uplinks.offline:
        state.systab.set("", status="off")
    fetcher = EdsmFetcher(state, journal_dir, EdsmCache(EDSM_CACHE_FILE, SystemArchive(ARCHIVE_FILE)), state.records, uplinks)
    fetcher.start()
    log("System data: Spansh Uplink " + ("on" if uplinks.spansh else "off") + ", EDSM Uplink " + ("on" if uplinks.edsm else "off")
        + " - bodies and stations from " + ("Spansh (EDSM where it has nothing)" if uplinks.spansh and uplinks.edsm else fetcher.source())
        + " and your journal.")
    bus = UIBus()
    state.notify = lambda: bus.bump("jump_n")   # jumps and start-ups: pages fetch the new state at once
    state.nudge = lambda: bus.bump("state_n")   # anything else new: the same, without a jump's fuss
    state.jumps.survey_off = uplinks.offline
    state.jumps.survey_src = fetcher.source()
    ocor = OcorStore(OCOR_FILE)
    state.coords = CoordCache(COORDS_FILE)
    star = StarCoords(state.coords, state, ocor, bus, uplinks=uplinks)
    bus.listeners.append(star.poke)   # a page switched tab (or a briefing was fetched): check at once
    star.start()
    controls = ControlStore()
    ufc, inputs = (None, None) if args.no_ufc else start_ufc(bindings, require_focus=not args.any_window,
                                                             board=state, bus=bus, ocor=ocor, store=controls)

    try:
        server = open_server(args.host, args.port, Handler)
    except OSError as exc:
        log(f"Couldn't start the web server on port {args.port}: {exc}. Another program has it? Try --port 8700.")
        sys.exit(1)
    write_pid_file(args.port)
    server.app = (state, writer, engine)
    server.bus = bus
    server.names = own_host_names()   # (the page opened by this PC's name: as good as localhost)
    server.controls, server.inputs, server.binds = controls, inputs, bindings
    server.inputs_why = (("Off: started with --no-ufc" if "controllers" in given else "Off: game controllers are off (4 Setup > Settings)")
                         if args.no_ufc else "Off: the hidapi package isn't installed (pip install hidapi)" if inputs is None else "")
    server.settings, server.started, server.given = settings, started, given
    server.run_opts = {"journal_dir": str(journal_dir), "engine": engine.name, "model": args.model or "", "port": args.port,
                       "lan": args.host not in ("127.0.0.1", "localhost", "::1"), "controllers": not args.no_ufc,
                       "open_page": not args.no_browser}
    server.restart = False
    server.clip = ClipButton(bus, state)
    server.ocor = ocor
    server.star = star
    server.stopping = False
    url = f"http://localhost:{args.port}/"
    if not (WEB_DIR / "index.html").is_file():
        log(f"The page's files are missing: put the web folder next to this script ({WEB_DIR}).")
    log(f"UCEC FT3000 {VERSION} running at {url}  (Ctrl+C to stop)")
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        where = ", ".join(f"http://{a}:{args.port}/" for a in lan_addresses()) or f"http://<this PC's IP address>:{args.port}/"
        log(f"Other devices on your network can open the page too: {where}")
    if not args.no_browser and not os.environ.get("FT3000_RESTARTED"):   # (started again by RESTART: its page is still open)
        threading.Timer(1.0, webbrowser.open, [url]).start()
    set_console_title(f"UCEC FT3000 {VERSION} - press Exit on the web page, or close this window, to stop")
    log("To stop: press Exit on the web page, close this window, or press Ctrl+C here.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopping.")
    finally:
        server.stopping = True
        server.server_close()
        clear_pid_file()
        if ufc is not None:
            ufc.display.show(["", "", "", "", ""], "", "", "", com1="", com2="")   # blank the UFC
        log("Stopped.")
    if server.restart:
        restart_self()


if __name__ == "__main__":
    main()
