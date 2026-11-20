# SPEC20 — Grinding rules: four corrections from the roll-grinding research

Repository `/home/user/PhysicRollModel`. One work package, inserted into Phase 2 after its
Package 2. House rules: section 0 of `SPEC.md`, section G of `SPEC17.md` as amended by
`SPEC18.md` G' and by the Phase 2 rules (standard library only, tags travel with numbers,
`tests/json_close.first_difference` for comparisons with artifacts, no `unittest discover`,
`verify_tests.sh` and `verify_additive.py` at the end). Do not commit.

Source of every new fact: `docs/research/band-screening-2026-11/roll-grinding.md` (source prefix
`RG`), sections 4.1, 4.2, 3.4 and 8 (b), (d). Read those sections first. Almost all foil-specific
numbers in it come from printed grinder settings in patents and trade pages: carry the tags as
they stand (`RG5`, `RG7`, `RG8 FT`, `RG11 VP`, `RG16 VP`, `RG24 VP`, `RG25 AB`, `RG26 AB`,
`[computed]`); never promote one.

## Why

The owner approved fixing the four points where the report shows the tool's grinding rules and
the measured-roll-profile input do not match what grinders do. Two of them (parts 1 and 2) change
evidence rules, so this package is of kind (b) of `SPEC17.md` G3: it may move scores. Every moved
score, standing or flag must be listed; see "Proof" below.

## Part 1 — feed marks: the spacing ceiling (`band_width._h_grinding`)

Today the supporting test is `regular fine spacing (CV < 0.15, spacing < 30 mm)`, weak support.
Printed final-pass traverse feeds are 9-25 mm per roll revolution on an aluminium cold-mill roll
[RG5] and 24-53 mm on a foil roll [RG7, computed from the printed settings]; the law "pitch =
traverse per roll revolution" is confirmed [RG8 FT, RG11 VP].

- Raise the ceiling to 60 mm: a module constant `FEED_MARK_SPACING_CEILING_M = 0.060` with the
  comment "printed final-pass feeds 9-53 mm [RG5; RG7 computed]; ceiling set just above the
  largest, an analyst choice [D]".
- The criterion string changes to name the constant's value (`... spacing < 60 mm`). Update the
  matching entry in `band_plain.CRITERIA` (plain words, no engine tokens) and every test that
  names the string.
- The `SUPPORTS` weight stays weak. The `NEUTRAL` branch is unchanged.
- Add to the hypothesis's prediction dict a `feed_range_note`: one sentence with the two printed
  ranges and their tags, and the sentence that a wide, irregular spiral from table float does not
  follow the feed law and belongs with `roll_surface_band` [RG8 FT].

## Part 2 — grinder chatter marks on the work roll (`band_diagnosis._mark_count`, `_roll_mark`)

Today one count n from 1..8, or a supplied `kinematics.grinder_marks[].marks_per_circumference`,
must explain every pitch. Grinder chatter leaves `n = f / n_roll` marks [RG25 AB, RG26 AB,
RG24 VP]: 12-240 per circumference for once-per-wheel-revolution forcing, 100-190 for a foil roll
finished at 5 r/min [computed from printed settings]. The search over 1..8 cannot find it.

1. **Computed count.** A `grinder_marks` entry may now give the grinder's last-pass settings
   instead of a count: `wheel_rotation_hz` and `roll_rotation_hz` (both > 0), optionally
   `vibration_frequency_hz` (> 0) in place of the wheel rotation. Exactly one of
   `marks_per_circumference` or the settings must be present; validation messages name the entry
   index. The count is `f / roll_rotation_hz` with `f` the vibration frequency if given, else the
   wheel rotation frequency. It need NOT be an integer: grinder chatter is a spiral on the roll
   and the strip carries its local pitch, `circumference / n`. Keep the real value; do not round.
   Each candidate count in the result carries how it was obtained (`supplied` / `computed from
   wheel and roll speed` / `computed from vibration frequency and roll speed`) and the basis tags.
2. **Without grinder data.** When no entry exists for the roll and the pitch fits no count in
   1..8 within the rule's existing tolerance, but the implied count `circumference / pitch` lies
   in [12, 240] for every observed pitch, the pitch criterion can no longer contradict a roll-borne
   source: its status becomes `NEUTRAL` (not `CONTRADICTS`) with the note "a grinder chatter
   pattern (12-240 marks per circumference [RG25 AB, RG26 AB, RG24 VP; range computed from printed
   settings]) cannot be excluded without the grinder's wheel and roll speeds or a supplied count",
   and the result gains the top-level flag `GRINDER_CHATTER_NOT_EXCLUDED_NO_GRINDER_DATA` with its
   plain sentence in `band_plain.FLAGS`. Module constants `GRINDER_CHATTER_COUNT_RANGE = (12, 240)`
   with the tags. Implied counts between 8 and 12, or above 240, keep today's behaviour.
   **Owner's addition (2026-11-20): entered data decides, typical data only bounds.** The two
   cases must read as one design, in the result and in the app:
   - *Grinder data entered* (a count, or wheel and roll speed, or vibration frequency and roll
     speed): the pitch test is decisive again with the rule's existing tolerance and weights —
     `SUPPORTS` when one entered or computed count explains every pitch, `CONTRADICTS` when none
     does. The neutral case never applies. The evidence line states the count, how it was
     obtained and the mismatch.
   - *No grinder data*: the tool falls back on the typical range of printed grinder settings
     (the constant above) and is neutral inside it, as specified. In BOTH cases the result
     reports, per observed pitch, `implied_marks_per_circumference = circumference / pitch`,
     whether it lies in the typical range, and the sentence that entering the grinder's last-pass
     wheel and roll speeds turns this into a test. The typical range is never used to compute a
     count or a pitch: it bounds what cannot be excluded, it is not a default grinder.
   - The app asks, in the group "A roll grinder report", for either the number of marks counted
     around the roll, or the wheel speed and roll speed of the last grinding pass (r/min, both
     optional as a pair), with a plain line on where to find them (the grinder's program sheet)
     and what happens if they are left empty (the tool cannot rule a grinder pattern in or out).
3. The same two functions serve the backup roll: apply 1 to it (a backup roll is ground too);
   apply 2 to the WORK roll only (the range is from work-roll grinding) and say so in a comment.
4. Orientation (guide text only): marks from wheel-spindle vibration are spiral on the roll, those
   from work-rest, tailstock or headstock are axial [RG24 VP], so a slightly oblique transverse
   mark is compatible with a grinder source. No rule change.

## Part 3 — measured roll profile: the de-trend (`band_width._validate_roll_profile`, `roll_profile_section`)

A second-order polynomial removes a parabolic crown only. On a cosine-ground roll (80 um crown on
diameter, 70 degree half angle) it leaves a W-shaped residual of 0.68 um peak to peak on radius,
1.2 um at 90 degrees; order 4 leaves under 0.02 um [computed, `prototypes/grinding-research/
detrend_check.py`, curve form assumed]. That exceeds the 0.3 um bump of the guide's worked case.

- Default `detrend_order` becomes 4. A constant `ROLL_PROFILE_DETREND_ORDER_DEFAULT = 4` with the
  tagged comment. Tests of the worked case that rely on order 2 pass `detrend_order: 2`
  explicitly and keep their numbers.
- New result block `detrend_sensitivity` in the roll-profile section, always computed: the bands
  found with order 2 and with order 4 (positions, peaks, states), the largest difference of the
  local deviation between the two with its position, and `bands_depend_on_order` (true when the
  set of bands above the reporting threshold differs, by position within the tool's position
  tolerance, or a state differs). When true, the flag
  `ROLL_PROFILE_BANDS_DEPEND_ON_DETREND_ORDER` is set (with its `band_plain.FLAGS` sentence) and
  the report says: subtract the grinder's target curve before entering the profile, or state the
  curve.
- Reproduce the report's check as a unit test: a pure cosine crown of 40 um on radius with a 70
  degree half angle, no other deviation, on a 1.7 m barrel: order 2 leaves a residual of about
  0.68 um peak to peak (within 10 %), order 4 below 0.02 um, and the section finds no band with
  the default order. Copy the curve definition from the research script; state it in the test.
- Limitation sentences added to the section: a report on a roll not thermally settled carries a
  thermal profile of the size of the grinding tolerance, 3.3 um per K on a 280 mm roll [computed;
  rest time about a day, RG5]; grinder gauges measure diameter, so deviations are halved for the
  radius input.
- Guide 7.9: replace the worked case's "crown 2 um" by a representative example crown of 40 um on
  radius, labelled as an example from plant-level sources that cannot be defended as a default
  (report section 2.2), and regenerate the worked numbers from the code with `detrend_order`
  stated.

## Part 4 — measured roll profile: the grid (`roll_profile_section`)

A 21-station grinder report has stations 70-100 mm apart on a foil barrel [RG16 VP, computed]; a
stripe of 20-30 mm half-peak width cannot be carried by it. The input accepts five positions.

- Report `grid`: `{largest_spacing_inside_strip_m, smallest_resolvable_width_m}` with
  `smallest_resolvable_width_m = 2 * largest spacing` (two samples per feature, [D]).
- Flag `ROLL_PROFILE_GRID_TOO_COARSE` (with its plain sentence) when
  `smallest_resolvable_width_m` exceeds the observed band width (`observation.band_width_m`) when
  that is given, otherwise when it exceeds 0.030 m (the narrow stripe of the guide's worked case,
  constant `NARROW_STRIPE_REFERENCE_WIDTH_M`, [D]). The report sentence: "this profile cannot show
  a mark narrower than X mm; a missing band here does not mean the roll has none".
- No change to which bands are computed: this is a flag and a sentence.

## Guided app (minimum only)

- The new grinder settings are plant-facing: add the questions needed for the wheel and roll
  speeds of the last grinding pass to the existing group "A roll grinder report", with conversion
  both ways, so that the app invariants hold. Keep the wording plain ("how fast the grinding wheel
  turned", "how fast the roll turned in the last grinding pass"). The app agent refines the group
  in the Phase 2 app package; do not redesign anything.
- New flags get their `band_plain.FLAGS` sentences in this package.

## Docs

- `docs/band-diagnosis.md`: 6.2 (feed marks: the new ceiling and why), 6.3 (roll-borne marks: the
  computed count, the neutral case and the orientation note), 7.9 (default order, sensitivity
  block, grid flag, the two limitations, the new worked example), 5.3 (inputs), 12 (flags), 14
  (limits: no amplitude of grinder marks on foil rolls is published; none of this was checked on
  a mill).
- `docs/simulation-coverage-gaps.md` section 11: extend the G13 and C4 rows.
- `docs/research/band-screening-2026-11/README.md`, "Statements later corrected": one bullet per
  corrected rule, pointing to the guide.

## Proof (end of package)

1. Tests: the changed and new modules, then `bash scratchpad/verify_tests.sh [new modules]`.
2. Regenerate the five artifact pairs into scratch and compare each with HEAD using
   `scratchpad/verify_additive.py`. This package may change existing values, so the script may
   NOT end "additive only": for every changed or removed path say which part of this brief causes
   it. Expected: evidence text and possibly scores of `grinding_feed_marks` (part 1) and of
   `work_roll_borne_marks` (part 2), the new flags, new prediction keys. Nothing else may move.
3. List, per artifact: every hypothesis whose score, rank or standing changed, before and after,
   and the leader before and after. **If a leader or a standing changes in any committed demo,
   stop before copying that artifact and report it.**
4. Copy the regenerated artifacts into `artifacts/band_diagnosis/` only when every difference is
   accounted for.

## Do not

- Do not add an amplitude for grinder marks: none is published for foil rolls.
- Do not use the report's camber magnitudes as defaults anywhere: they are examples only.
- Do not change the weights of existing evidence items, the feed-pitch match rule (1-3 x within
  10 %), or any other hypothesis.
- Do not let a non-integer computed count be rounded, and do not let the neutral case of part 2
  apply when grinder data was supplied.

## Hand back

At most 350 words: files and line counts; each new test in one line; commands and results; the
list of moved scores, ranks, standings and flags per artifact with the cause; anything that could
not be implemented as written; new test module names.
