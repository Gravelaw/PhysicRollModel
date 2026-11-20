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
  thicker" pictures. A line under the route says which route pass is the pass where the bands
  show, by the engine's own test (same gauges, flow stress, friction and tensions), or that none
  is; when the run computes flow stress or friction itself it says that the run compares them
  again with the computed values.
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
  "Don't know" (the model then uses full flow for every nozzle). Nozzles of a known valve event
  have a dotted ring.
- **Add what else you have (optional)**: one folded entry point under the spray header. Inside
  it the add-on inputs are grouped by what you have; each group is one line when closed, with a
  filled mark (● or ○, never colour alone) and a short summary ("24 zones of 52 mm", "2 records",
  "not filled in"), and a **Clear** button when filled that sets every answer of the group back to
  "Don't know" in one action. None of these answers is "ask first", none changes the shortlist or
  the trust level unless a model choice says so, and each stays "Don't know" until you answer it.
  The nine groups (41 questions):
  - **A flatness roll (shapemeter)** (7): the width of one measuring zone and the number of zones
    (both needed), narrower edge zones if any, the share of a zone's signal that spreads to each
    neighbour (only if your vendor states it; otherwise none), the smallest flatness difference
    your system shows (otherwise the tool's own 2 I-unit band level), and whether it corrects for
    strip temperature. From the shapemeter data sheet or its configuration. Once width and count
    are answered, the strip drawing shows the zone boundaries as dashed lines just above the strip,
    placed by the same engine code the run uses (centred where the tool puts the strip centre),
    with the zones and the nozzles under each one in words and as a list beside the drawing;
  - **A thickness gauge** (5): spot length along the strip and response time (both needed), time
    between readings, where it sits across the strip and its spot width;
  - **A strip temperature scan** (1) across the width after the roll gap (a pyrometer or probe
    reading; at least three points, positions from the strip edge, °C). The tool uses the scan as
    given and never works out a strip temperature itself;
  - **A roll grinder report** (1): the deviation of the radius (half of a diameter deviation), in
    µm, at positions from the barrel end where nozzle 1 is (at least five points). The tool removes
    the smooth crown and keeps the local marks;
  - **Pass records (force, torque, slip)** (1): up to 8 logged coils of this pass, each with the
    rolling force (needed) and, if you have them, the forward slip, the torque of one work roll and
    the exit speed. The tool works out which friction each one corresponds to; it changes nothing
    in the case;
  - **Oil data** (9): viscosity at several temperatures, the pressure law and its Roelands index,
    the Eyring stress and limiting shear (with their temperature coefficients), the flash point and
    the site's supply-temperature cap;
  - **A known friction difference across the width** (1): position, half-peak width and how much
    higher or lower the friction is there, as a share of the pass friction;
  - **How the roll is cooled around its circumference** (2): how much of the circumference the
    sprays wet (an angle) and, for the roll surface within one turn, where each spray band starts
    (degrees after the roll gap in the direction of rotation) and how long it is;
  - **Model choices** (14): the roll-gap model (the reduced half-space foil model is an option,
    named with its benchmark standing: on the one published foil case it gives a load of 89 and the
    standard foil model 50, while the published 118 depends on a numerical detail the paper does
    not state) and its friction cap; the friction law with the oil film (the placeholder law, or
    the share of touching surface from a published foil pass, which needs only **your contact
    friction**, asked for with what to measure: the roll force or forward slip, or a strip-drawing
    test with your oil and roll finish; the placeholder law's own three numbers are not asked
    for); the interface conductance and whether to use the computed heat share; and a speed and
    temperature factor on the metal's strength (rate exponent, its reference rate, the temperature
    softening in % per K, its reference temperature, and whether the roll forces use it).
  Two questions show only when they apply (the extra numbers of the Tome-Voce hardening law).
  A spray calibration from a measured roll temperature or camber scan is not in the app: the
  engine runs it from the command line only (`python -m physicroll.band_cli CASE.json
  --calibrate-spray FILE.json`, with a case file downloaded from a run and the scan in its own
  file).
- Under "More details": everything else of section 5.3 of the guide (stand masses and stiffnesses,
  spans, bearings and gears, rolling oil, gauge control, drive, coil, grinder, model settings).

If an answer is not accepted (for example an exit gauge above the entry gauge), the question is
marked in red with a plain explanation, and pressing Run takes you there.

**What the drawings show.** Every drawing and every statement about the case on the input pages
(the strip and band drawing with its ruler, the band list, the spray header with its nozzle
states, the nozzle counts and list, the blocked-nozzle numbers, the coverage line, the route line
and the side panel "What the tool has so far") is drawn from the case the engine will be given:
after each change the app builds that case and sends back what to draw, computed from it the way
the engine reads it (for example the flow level of each nozzle after the blocked nozzles are
applied). The page redraws whenever that differs from what is on the screen. While an answer is
not accepted, the drawings stay at the last accepted inputs, greyed, with the note "Not updated".
Pressing Run first waits for the last change to be checked.

**One set of nozzle marks.** The nozzle state is kept in one place: the flow level of each nozzle
(the drawing and its nozzle list). "Blocked nozzles (by number)" shows the nozzles at level 0 and
edits them: a number typed there is marked blocked on the drawing, a number removed there is
marked healthy again. An opened case file or an earlier answer set with blocked numbers gets
them as blocked nozzles on the drawing (the engine simulates the same thing), with a notice.
"Don't know" stays "Don't know" until you mark a nozzle (an empty blocked-number list leaves it).
The simple spray coverage check uses the same physical header whenever its barrel length and
nozzle distance give the same nozzles (always so when you change them here): it then uses the
drawing, counting every nozzle marked weak or blocked as not spraying, because it only knows on
and off (the worked examples are built that way), and the page shows its nozzles as a line, not as
a second field. If an opened case marks nozzles blocked only for the coverage check, they are
marked blocked on the drawing with a notice, and the run waits until that notice has been shown.
Only a case whose coverage header is different (or which has no spray header model) has its own
coverage numbers, and the page says why.

**Answers that depend on other answers.** The nozzle marks (the drawing, the blocked-nozzle
numbers and the valve events) belong to one spray header. When the distance between nozzles
changes and the number of nozzles stays the same, the marks stay on their nozzles and the header
is redrawn at the new positions; when you change the barrel length or the distance between
nozzles and the number of nozzles changes, the marks are reset to "Don't know"
(never moved to other nozzles), the header is redrawn and a notice says so ("The spray header now
has 25 nozzles instead of 28, so the nozzle marks were reset. Mark them again if you know them.").
A run is not started until the page has shown that notice: pressing Run with stale marks shows the
redrawn header instead, and the next press runs. Band positions, the band width and incoming ridges
that lie outside the strip, or a strip that does not fit on the roll where it is placed, get a
notice on the question without being changed. Choosing another product after filling in its
typical values says that those values were for the previous product.

**Changing the answers of an earlier run.** "Change the answers" (on a result, or on a run opened
from "Previous runs") brings back that run's answers on that run's own starting point. A run
started from a typical mill or a worked example reopens on that starting point. A what-if, an
updated result, a run in detail of one of those, and a run from an opened case file reopen on the
case of that run as it was run: step 3 then shows "Starting point: the earlier run '<name>'" (or
"the case file you opened"), and every value you do not change stays as it was in that run. This
also works after the app was restarted or the page reloaded, because the app reads the run's
stored case from the runs folder. If that folder can no longer be read, the page says so ("the
earlier run this one was built on can no longer be read") instead of using another mill.

## 3. Running

The running view shows the elapsed time, the kind of run (quick or detailed), what quick leaves
out, and the steps the tool works through. Runs are done one at a time on this computer; a run
that is still waiting can be cancelled. If a run fails, the page says what happened and which
answer to look at ("Go to this question"); it never shows a program error trace. A run cut short
because the app was closed shows as "interrupted" and can be started again with the same inputs.

If the screening ran but the picture page could not be built from its result, the page says "The
screening ran, but the visual summary could not be built" and offers the full engineering report
and the result and case files to download: the engine result and the report are saved before the
picture page is built, so they are never lost.

When the roll-gap model could not compute the pass where the bands show, the result page opens with
a "What could not be assessed" block right under the headline, the headline says so, and the trust
level stays low.

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
   **The add-on cards.** What you gave under "Add what else you have" comes back as cards after
   the temperature block, all built the same way: the title; one sentence that says what it
   shows (the takeaway); one chart; one "how to read this" sentence that adds only what the axes
   and the legend do not say; the caveat that must stay with it; **Details, and the chart as a
   list** (the chart in words) folded; and "From '<group>' in step 3". A card appears only when
   its group is in use, so a run with no add-on shows no add-on card; one quiet line under the
   cards names the groups that would add more.
   Every chart is drawn from one description in the plain layer: each series has one shape,
   fill, colour and line style, and its legend entry is drawn by the same code as the mark
   itself. One colour carries one meaning in a chart (blue, orange and purple, readable for
   colour-blind people in the light and dark theme, with filled and open marks, shapes and
   dashes so that colour is never the only signal); reference lines and ranges (the friction of
   the case, the band level, half, no change, the measured foil-mill range, the published
   figure) are always the neutral grey. The value axes carry their title with the unit; the
   legend appears only where the series cannot be labelled on the chart (on a phone the roll
   surface lines are listed in the legend instead). Charts across the width use the strip
   picture's scale. Passes are named the way the route is entered, by their gauges ("50 → 30
   µm"), with "(this pass)" on the pass where the bands show and "(alternative route)" where the
   route row says so. Hover, tap or keyboard focus on a mark gives its exact value. A technical
   term (I-unit, forward slip, heat share, half-space model, ...) is underlined with its plain
   meaning on its first use on a screen; the meanings come from one glossary in the plain layer.
   **What your flatness roll would show** (when you described a flatness roll and the model has
   a flatness profile across the width). One bar per zone on the same scale across the width as
   the strip picture: the average of the modelled flatness over that zone; the line is the
   modelled flatness itself; the dashed lines are the band level (the resolution you gave, or the
   tool's own 2 I-units). Under it one sentence per modelled band, for example (battery-foil
   example) "At 472 mm the model has a band of 25.1 I-units; a zone of 52 mm would read 24.5: it
   would show on the flatness display", or, for a narrow ground mark of a roll profile, "At 348 mm
   the model has a band of 3.13 I-units; a zone of 52 mm would read 1.07, below 2: the flatness
   display would probably not show it". What these mean: zone averages of a model, what a flatness roll with those zones
   would show; not a forecast of your flatness display. What they do not mean: "would probably not
   show" is a statement about the display, not that the band is not there or about which cause it
   is. The card always ends with "The tool does not model what the flatness control would do with
   these readings." This card is part of the printed page.
   **Flatness measured hot and after cooling** (with a temperature scan): "Measured hot the band
   reads 30.5 I-units, after the coil has cooled 25.1", always with "The temperature profile was
   supplied as an input (entered), not computed by the tool."
   **A friction or oil-film stripe** (when the case carries the friction estimate, as the
   battery-foil example does): the friction difference at one place that would make a 2 I-unit
   band, said together with both levels of the model for 1 % more friction (with the exit-tension
   feedback, and without it: roll and strip compliance alone) and a chart of both for every pass
   (filled and open marks). A quick run leaves this estimate out unless you entered a stripe; the
   card then says so and offers **Run in detail**.
   They differ greatly (-3.1 against -390 I-units in the battery-foil example) and neither is
   checked on a mill; read them together, never one alone. Your own stripes are listed with their state. It never changes the scores.
   **Your measured roll profile**: the bands the profile makes in the model, with what your
   flatness roll would show of them (a narrow ground mark is diluted by wide zones).
   **What the thickness gauge keeps**: for each mark spacing you measured, about how much of it
   the gauge keeps (spot size and response time only); when you saw no gauge variation but the
   gauge could not show these marks, the card says that answer tells little and that the scores
   were not changed.
   **Friction from your pass records**: for each logged coil the friction its force, forward slip
   and torque correspond to in this model, each with the range its measuring error allows (the
   app asks for no error, so the tool's assumption of ±5 % force, ±1 percentage point slip and
   ±10 % torque is used and named), for example "Your force of 1200 kN corresponds to a friction
   of 0.0308 in this model (between 0.0299 and 0.0317 for a force error of ±5 %, the tool's
   assumption); your forward slip to 0.017 (between 0.0164 and 0.0175 for a slip error of ±1
   percentage point, the tool's assumption)", and whether they agree within these measuring
   errors. "Nothing was changed; enter the value yourself if you want to use it."
   **The roll surface within one turn** (with the spray bands placed around the roll): "Just
   before the roll gap the roll surface is at 59.4 °C at the band position and 45.4 °C beside it;
   the average the model works with is 59.4 °C", with the temperature over one turn at three
   places across the barrel. Reported only; it does not change the stripe heights.
   **The metal's strength with speed and temperature** (with the speed and temperature factor):
   the factor per pass, said as "shown only, the roll forces do not use it" unless you chose to
   use it, and always "The speed part is an extrapolation".
   **The heat share: entered and computed** (when you use "Model choices" or "Oil data" and the
   run computes the share, which needs the oil data the examples carry): "You entered that 22 % of the heat stays in the strip; the tool's own
   estimate is 44 %", per pass, beside the range measured on a foil mill. A comparison: the
   entered share is used unless you choose the computed one under "Model choices".
   **The roll-gap model** (when you use "Model choices" and a foil roll-gap model ran): which model gave this pass's numbers,
   and the standing of the half-space option on the one published foil case: a load of 89 against
   50 for the standard foil model, the published 118 depending on a numerical detail the paper
   does not state (the same equations give 78 to 134), and its contact length against the
   published solution's. The loads are the recorded benchmark runs of the repository; no ratio is
   shown.
   For foil tension lines the cause detail adds **A candidate spacing (not evidence)**: the
   wrinkle spacing that air trapped while winding would give for the rolls and coil of the case.
   Almost any foil coil gives a spacing inside the published 5 to 20 mm, so a match proves
   nothing; the detail says how to test it (the spacing at two coil sizes and two gauges).
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

**Quick** is the default. It leaves out up to four things:

- the heat-share and spray-coefficient sensitivity table;
- the fine roll-temperature grid: it uses 20 mm cells, 6 radial cells and a 5 s step instead of
  5 mm, 16 and 1 s (only when the case does not set its own grid);
- the fine roll-gap grid: 128 cells instead of 256 (foil roll-gap models keep at least 200);
- the friction stripe estimate per pass, when the case carries it (the battery-foil example
  does). The friction card then says the quick run left it out and offers "Run in detail". When
  you entered friction stripes yourself it is kept: the tool works out your stripes only
  together with the per-pass table. Leaving it out changes no score, standing or other value.

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
  leads, when the roll-gap model could not compute the pass or its result is not credible, or
  when part of the screening could not be computed.
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
| `summary.json` | the plain-language summary the page draws from (missing when it could not be built; `meta.json` then says why) |
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
  written under a name from the browser. Request bodies are limited to 1 MiB and must be JSON; a larger file gets a plain "too large" message (the page itself refuses a case file above 900 KiB before sending it).
- The engineering report is served under a stricter policy (no scripts at all).

## 9. What it cannot tell you

- It screens; it does not find "the cause". The shortlist ranks how well each candidate fits what
  you entered, with evidence weights that are engineering judgement.
- It models one stand of a four-high mill. Multi-stand effects are not modelled.
- At foil gauge the work rolls may touch beside the strip (closed-gap rolling); this is not
  modelled, and the tool assumes an open gap.
- Nothing in the tool has been compared with plant data. The typical mills, the worked examples
  and the product values are synthetic or literature values.
- The printed summary fits on one A4 page for a result like the lengthwise worked example
  printed from a desktop-size window. A long shortlist of tied causes (for example the typical
  foil mill with nothing answered) or the battery-foil example takes two pages, and so does any
  print made from a phone-size window.
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
