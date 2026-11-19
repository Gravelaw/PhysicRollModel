# Band app: guided band screening in your browser

The band app is a front door to the band screening tool (`docs/band-diagnosis.md`) for people who
know the mill and the product but not the model: a plant supervisor, a quality engineer, an
operator. It asks three short sets of questions, runs the screening on this computer and shows
the result as pictures: which few causes fit what you saw, what to check next, and how far to
trust it.

**What it is not.** The result is a shortlist from a screening model that has not been compared
with plant data. It never names "the cause". Every screen that shows a ranking says so, and the
trust level is never higher than "fair".

## Contents

1. [Starting it](#1-starting-it)
2. [The three steps](#2-the-three-steps)
3. [Running](#3-running)
4. [The result, block by block](#4-the-result-block-by-block)
5. [Quick and detailed runs](#5-quick-and-detailed-runs)
6. [The trust level](#6-the-trust-level)
7. [Where runs are kept](#7-where-runs-are-kept)
8. [Safeguards](#8-safeguards)
9. [What it cannot tell you](#9-what-it-cannot-tell-you)
10. [Troubleshooting](#10-troubleshooting)

## 1. Starting it

You need Python 3.10 or newer. Nothing else is installed: the app uses only the Python standard
library and opens in the web browser you already have.

**Double click**, in the repository folder:

| Computer | File | Notes |
|---|---|---|
| Windows | `start-band-app.bat` | tries `py -3`, then `python` |
| macOS | `start-band-app.command` | opens in Terminal; tries `python3`, then `python` |
| Linux | `start-band-app.sh` | run it from a terminal, or with "Run in terminal" in the file manager; tries `python3`, then `python` |

Each launcher checks that the Python it finds is 3.10 or newer, starts the app with the runs kept
in the folder `band-app-runs` next to it, and keeps its window open with a readable message if
something goes wrong. On macOS and Linux the file must be executable (`chmod +x
start-band-app.command`) if your copy lost that mark.

**One command**, from the repository folder:

```
python -m physicroll.band_app --runs-dir my_runs
python -m physicroll.band_app --runs-dir my_runs --no-browser --port 8765
```

- `--runs-dir` (required): the folder where runs are kept; it is created if it does not exist.
- `--port`: the port to use; without it the app picks a free one.
- `--no-browser`: do not open the browser; open the address it prints yourself.

The app prints its address, for example `http://127.0.0.1:52817/`, and opens it. Press Ctrl-C in
the window (or close it) to stop the app. Runs stay on disk.

**Installed from a wheel** (`pip install physicroll-...whl`) the same command works from any folder.
The four worked examples (section 2.3) are then not offered: they are read from the `scenarios/`
folder of a source checkout, which a wheel does not contain. Everything else works the same.

## 2. The three steps

A progress line at the top shows the three steps; you can move between them freely. A panel at
the side says in plain words what the tool has so far ("Lengthwise bands at 3 positions, come and
go; 18 µm battery foil at 600 m/min; typical foil mill, 2 values measured") and how many of the
"ask first" questions are still unknown. The **Run the screening** button at the bottom is always
there; you can run at any time and add answers later.

Every question has a "Don't know / not checked" answer, and that is where every question starts.

- For an **observation** (what you saw), "Don't know" means nobody has looked. The tool then
  scores it as "not looked at" and it never counts against a cause.
- For a **mill, pass or material value**, "Don't know" keeps the starting point's typical value
  and marks it as "left at the typical value".

Each step shows a short "ask first" set: the questions that separate the causes best (from
sections 3.8, 5.1 and 5.2 of `docs/band-diagnosis.md`). "More details" opens the rest.

### 2.1 What do you see?

Pick the picture that matches: **stripes along the strip** (lengthwise bands at fixed places
across the width), **marks across the strip** (lines repeating along the length), or **not
sure**. Diagonal, V-shaped and irregular marks are below the pictures.

For stripes along the strip the step asks, first:

- **where across the width the bands are**: placed on a drawing of the strip. The drawing is a
  top view of the strip at its width, with a ruler in millimetres and the coolant nozzles above
  it. Click or tap on the strip to add a band, drag a band to move it, or use the list beside the
  drawing (type a position, delete a band). With the keyboard, the arrow keys move a selected
  band by 1 mm (with Shift by 10 mm) and Delete removes it. Measure from the strip edge nearest
  the first coolant nozzle (nozzle 1); if the strip does not run in the middle of the roll, set
  "Strip centre on the barrel" under "Your mill";
- whether the bands sit at the same places on the next coils;
- whether they moved or went away after a work-roll change;
- whether they come and go when cooling zones switch;
- whether they are invisible in the mill and only seen on the coil, at the slitter or on the
  table;
- whether they are always there or come and go;
- what a band looks like (bright or dull stripe, loose wavy band, tight stripe, stain, crease);
- for foil below 100 µm: whether they fade at higher exit tension, what cleaning the roll wipers
  did, and whether they follow speed changes.

For marks across the strip it asks, first: the mark spacing along the strip at two speeds at least
20 % apart; whether the exit thickness gauge shows a repeating thickness change; what a work-roll
and a backup-roll change did; and whether the marks are on one face or both.

### 2.2 What are you rolling?

- **Product**: the thin-gauge catalogue, grouped by family and searchable by typing. "Fill in
  typical values for this product" fills the pass and the material from the literature (the
  product survey's starter values on the default mill of the product's gauge class). They are
  marked "suggested — confirm" until you change or confirm them, and the alloy and temper count as
  a literature suggestion until you say they are the plant's own statement.
- **The pass where the bands show**: entry and exit gauge (µm), strip width (mm), exit speed
  (m/min); under "More details" flow stress and tensions (MPa).
- **The route**: the other passes, as a list you can add to and remove from; "Use as the pass"
  copies a route pass into the pass where the bands show. The route feeds the "thinner or
  thicker" pictures.
- Under "More details": the rest of the material (yield stress, modulus, yield-point strain,
  magnesium, grain size, doubled final pass), a hardening law, incoming-coil hardness variation,
  case-specific width inputs (crowns, incoming ridges, earlier narrower widths) and inputs from a
  plant foil model.

### 2.3 Your mill

- **Starting point**: the typical foil mill or the typical sheet mill (the two synthetic mills of
  the product survey), a worked example (the four demos, with their observations; these were
  generated by the model, not seen on a plant, and the page says so), or **open a case file**
  (a band case JSON from this tool or the template; it is checked by the engine and not stored).
- **"These are my mill's real values"**: tick it only when the mill values are your mill's.
  Without it the case counts as synthetic and the trust level stays low.
- **The key mill values**, each with a mark: measured, estimated, or left at the typical value:
  work-roll diameter, friction in the roll gap, mill modulus, free strip length after the roll
  gap, barrel length, distance between nozzles, spray cooling strength and the share of the
  roll-gap heat that stays in the strip.
- **The spray header**: the same strip drawing with the row of nozzles above it. Click a nozzle
  (or press Enter or Space on it) to cycle healthy, weak (flow level 0.5) and blocked. The nozzle
  list under the drawing takes any flow level from 0 to 1. Until you mark a nozzle the state is
  "Don't know".
- Under "More details": everything else of section 5.3 of the guide (stand masses and stiffnesses,
  spans, bearings and gears, rolling oil, gauge control, drive, coil, grinder, model settings).

If an answer is not accepted (for example an exit gauge above the entry gauge), the question is
marked in red with a plain explanation, and pressing Run takes you there.

## 3. Running

The running view shows the elapsed time, the kind of run (quick or detailed), what quick leaves
out, and the steps the tool works through. Runs are done one at a time on this computer; a run
that is still waiting can be cancelled. If a run fails, the page says what happened and which
answer to look at ("Go to this question"); it never shows a program error trace. A run cut short
because the app was closed shows as "interrupted" and can be started again with the same inputs.

## 4. The result, block by block

Each block starts with a one-line "How to read this".

1. **Headline and trust.** One or two sentences: which causes fit best ("What you entered fits
   best with: ... This is a shortlist from a screening model, not a finding."), whether leaders
   tie, or, when nothing leads, what is missing. Beside it the trust level on a three-step meter
   (low, moderate, fair) with "Why not higher?" (section 6). The not-validated status is always
   shown here in plain words. Below the headline: whether this was a quick or a detailed run, what
   quick left out, and **Run in detail**.
2. **The shortlist.** One horizontal bar per cause of the kind of mark you described, on one
   scale that includes negative scores: bars to the right fit what you entered, bars left of
   zero do not. Each bar has a small sketch of the mechanism, its plain name and its standing word
   (fits best, fits, weakened, cannot tell, does not fit; colour is never the only signal). The
   score is a tally of what fits minus what speaks against; it is not a measure of how likely a
   cause is. Select a bar to open its detail: a one-sentence description, a labelled sketch, what
   fits and what speaks against (each line says whether it is something you saw, something the
   model computed or one of your mill values, and what the cause expects), what has not been
   looked at yet (each with "Answer this"), and how to check it on the floor. Causes of the other
   kind are folded underneath.
3. **Where across the width** (stripes along the strip). The strip seen from above with the spray
   header over it. Solid bars are the bands you saw. Outlined boxes with a letter are where the
   model puts a candidate: S a hot stripe on the roll, N a weak or blocked nozzle, V a nozzle of a
   valve event, E a short-lived stripe after a valve event, R a ridge in the incoming strip, T the
   edge of earlier narrower strip. The line above the strip is how much the roll grows across the
   barrel (bumps are hot stripes). A dashed link with a shaded box under the strip marks a band
   that lies within the matching tolerance of a predicted position. Hover, tap or move the
   keyboard focus to any mark for its position in millimetres. "The same as a list" gives the
   matches in words. **Along the strip** (marks across the strip) shows instead the spacing you
   measured against the spacing of the best-fitting candidate with a spacing.
4. **What to check next.** The measurements that would narrow the shortlist. For those that
   answer a question of the form, "I have checked this" opens the question in place; answer it and
   press **Update the result**. The new result shows what changed: the bars move from the old to
   the new score (a thin grey line marks the earlier score), changed rows are marked, and a box
   says it in words, for example "Tension troughs or creases: fits → does not fit, score 6 → 0".
   **Back to the earlier result** returns to the run before. This is the main loop: answer one
   question, see the shortlist narrow.
5. **What if.** Change the exit gauge, the speed, the exit tension or one nozzle (weak or
   blocked) and press **Try it**. The two results are shown side by side (shortlist, strip picture,
   the gauge numbers of the pass), labelled "what the model says would change", never what will
   happen.
6. **Thinner or thicker.** One small chart per quantity over the passes of the route, thickest on
   the left: the roll-stripe height at which a band buckles in the mill and at which it shows after
   tension release, the ridge height the coil turns into a band, and the sideways stress at which
   troughs form. Lower heights (or a stress closer to zero) mean a smaller disturbance already
   shows. Passes whose roll-gap result is not credible, or that have none, are hatched and named
   and left out of the trend sentence under the charts.
7. **Temperature.** The modelled strip temperature leaving each pass, as bars against the
   published coil limit when the product has one. A strip exit temperature is not a coil
   temperature; read the bars as indicators.
8. **How far to trust this.** The tool's notes on this case in plain words with what to do about
   each, what could not be assessed and why, and what is always true (one stand of a four-high
   mill; no closed-gap rolling; nothing compared with plant data; the score is a tally, not a
   likelihood).
9. **Take it with you.** Open the full engineering report (`docs/band-diagnosis.md`, section 12),
   download the case file or the result, or print a one-page summary (headline, trust, shortlist,
   strip picture, the first next checks and the standing limitations, in black and white with
   patterns and words instead of colour).

**Previous runs** (top right) lists every run with its time, product, gauge, best-fitting causes
and trust level; updates and what-ifs are listed under the run they came from.

## 5. Quick and detailed runs

**Quick** is the default. It leaves out three things:

- the heat-share and spray-coefficient sensitivity table;
- the fine roll-temperature grid: it uses 20 mm cells, 6 radial cells and a 5 s step instead of
  5 mm, 16 and 1 s (only when the case does not set its own grid);
- the fine roll-gap grid: 128 cells instead of 256 (foil roll-gap models keep at least 200).

**Detailed** runs the case as entered with the engine's own settings. Every result says which
kind produced it and what quick left out, and offers "Run in detail".

Measured one run at a time on the development machine (seconds). On the four demos and on two
plant dry-run cases the quick runs gave the same scores, standings and ranks as the detailed runs:

| Case | Quick | Detailed |
|---|---|---|
| battery-foil demo | 13.2 | 67.3 |
| lengthwise-bands demo | 20.0 | 47.7 |
| thin-gauge chatter demo | 8.8 | 16.6 |
| bearing-order demo | 4.6 | 8.4 |
| plant dry run, 18 µm final pass | 9.6 | 13.4 |
| plant dry run, 12 µm thinnest pass | 5.3 | 9.2 |

The battery-foil demo asks for the full sensitivity table, which is most of its detailed time.

## 6. The trust level

The trust level is a rule, not a statistic. It starts at **fair** and takes the lowest of these
limits:

- **Low** when the inputs are synthetic or typical values, when any key mill value is left at the
  typical value or the mill values are not marked as your own, when fewer than half of the
  "ask first" observations are answered or the direction of the marks is not given, when no cause
  leads, when the roll-gap result of the pass is not credible, or when part of the screening
  could not be computed.
- **Moderate** when half to four fifths of the "ask first" observations are answered, when causes
  tie for the lead or the leader is less than 3 points ahead of the next cause of the same kind,
  or when the experimental foil roll-gap model, an extended roll-gap range, closed-gap rolling or
  a literature alloy suggestion is involved.

It is never higher than fair, because nothing in the tool has been compared with plant data.
**Low is the normal level** until your own mill values and more observations are entered; "Why not
higher?" lists the reasons for this case.

## 7. Where runs are kept

Every run gets a folder under the runs folder (`band-app-runs` for the launchers), named by a
random 32-character id:

| File | What it is |
|---|---|
| `answers.json` | the answers as entered (with the starting point and the kind of run) |
| `case.json` | the band case the answers make (`physicroll.band_case.v2`); it opens with `python -m physicroll.band_cli case.json --out DIR` or in the app |
| `result.json` | the engine's full result |
| `report.html` | the full engineering report |
| `summary.json` | the plain-language summary the page draws from |
| `meta.json` | when it was made, its status, the kind of run, the run it came from (for updates and what-ifs), the engine version and the time it took |

When the app starts it lists the runs already in the folder and skips any it cannot read. A run
that was still waiting or running when the app was closed is marked as interrupted. Delete a run
by deleting its folder while the app is stopped.

## 8. Safeguards

- **Only this computer.** The app listens on 127.0.0.1 only and refuses any request whose address
  is not `127.0.0.1:<port>` or `localhost:<port>`.
- **A session token.** Every page load carries a random token; every request that reads or changes
  data must present it, so another web page open in your browser cannot use the app.
- **Nothing leaves the computer.** The page loads no external files, fonts or scripts, sends
  nothing anywhere else and is served with a strict content security policy.
- **Nothing the browser sends is used as a file path.** Runs are addressed by ids the app makes
  itself; an opened case file is read as JSON, checked by the engine's own validation and never
  written under a name from the browser. Request bodies are limited to 1 MiB and must be JSON.
- The engineering report is served under a stricter policy (no scripts at all).

## 9. What it cannot tell you

- It screens; it does not find "the cause". The shortlist ranks how well each candidate fits what
  you entered, with evidence weights that are engineering judgement.
- It models one stand of a four-high mill. Multi-stand effects are not modelled.
- At foil gauge the work rolls may touch beside the strip (closed-gap rolling); this is not
  modelled, and the tool assumes an open gap.
- Nothing in the tool has been compared with plant data. The typical mills, the worked examples
  and the product values are synthetic or literature values.
- The guide `docs/band-diagnosis.md` (section 14) lists the model limitations in full.

## 10. Troubleshooting

- **"Python 3.10 or newer was not found."** Install Python 3.10 or newer (on Windows from
  python.org, ticking "Add python.exe to PATH"), then start the launcher again.
- **The browser did not open.** Copy the address the window prints (`http://127.0.0.1:.../`) into
  your browser. On a computer without a desktop browser start with `--no-browser`.
- **"Port ... is already in use."** Another band app (or another program) uses that port. Start
  without `--port` to let the app pick a free one, or choose another port.
- **The page says the app does not answer.** The window running the app was closed or stopped.
  Start it again and reload the page; your runs are still in the runs folder.
- **No worked examples are offered.** The app was started from an installed wheel; the examples
  come with the source folder (`scenarios/`).
- **A run takes long.** Detailed runs can take a few minutes; use the quick run first.
