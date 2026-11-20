# Band screening research reports (November 2026)

These are the nine literature reports written for the band screening work, and one later research
note on the equations and constants they cite. They are kept as they were delivered: only file
names in cross-references were changed when they were moved here. They are working research
notes, not maintained documents. Where a later check corrected a statement,
the maintained documents below carry the correction and the report does not.

Maintained documents built from these reports:

- [thin-gauge-products.md](../../thin-gauge-products.md), generated from the product catalogue in
  `physicroll/band_products.py`. It holds the product, alloy-and-temper and process-temperature
  facts, each with its source id and how the source was read.
- [simulation-coverage-gaps.md](../../simulation-coverage-gaps.md), the merged gap study.
- [band-diagnosis.md](../../band-diagnosis.md), the user and theory guide for the screening tool.

## The reports

| Report | What it covers | Source prefix in the maintained documents |
|---|---|---|
| [products-battery-foil.md](products-battery-foil.md) | Battery and electronics foil: gauges, alloys, tempers, rolling routes | `BF-` |
| [products-packaging-foil.md](products-packaging-foil.md) | Packaging and household foil: gauges, alloys, tempers, rolling routes, named stripe defects | `PK-` |
| [products-heat-exchanger-litho.md](products-heat-exchanger-litho.md) | Heat-exchanger stock, litho sheet and other thin strip | `HX-` |
| [battery-foil-grades-by-gauge.md](battery-foil-grades-by-gauge.md) | Battery foil: which alloy and temper at which gauge | `BG-` |
| [process-temperatures.md](process-temperatures.md) | Strip, oil and roll temperatures in foil rolling and their effects | `PT-` |
| [gap-bite-tribology.md](gap-bite-tribology.md) | Gap study: roll bite, friction, lubrication, surface generation | `BT-` |
| [gap-shape-stack-winding.md](gap-shape-stack-winding.md) | Gap study: strip shape, roll stack, web handling, winding, flatness control | `SS-` |
| [gap-thermal-material-dynamics.md](gap-thermal-material-dynamics.md) | Gap study: thermal modelling and coolant, material behaviour, mill dynamics and control | `TM-` |
| [gap-open-data-codes.md](gap-open-data-codes.md) | Open datasets, open-source codes, published benchmark data, validation plan | `OD-` |
| [phase1-equations.md](phase1-equations.md) (2026-11-19) | Equations and constants the gap reports cite without giving | `E` (ids `E1`-`E19`) |
| [roll-grinding.md](roll-grinding.md) (2026-11-20) | Roll grinding for foil and thin-strip mills: ground camber, accuracy and roughness, grinding marks that print, wear, open data | `RG` (ids `RG1`-`RG51`) |
| [spray-nozzles.md](spray-nozzles.md) (2026-11-20) | Coolant nozzles and spray headers on aluminium cold and foil mills: nozzle types, rows and pitch, zone control and valves, flow and pressure, footprint and heat transfer, the basis of published coefficients | `SN` |

Inside each report the sources carry the report's own numbering (for example `S12`, `G7`,
`T25`). The maintained documents put the prefix above in front of that number.

## How to read them

- Every source is tagged with how it was read: full text, excerpt, abstract or snippet, vendor or
  trade page, landing page, or seen only as a citation. A tag was never upgraded later.
- Numbers marked "computed", "derived" or "from memory" are the report author's own arithmetic or
  recollection, not literature values.
- Nothing in these reports was checked on a mill. The screening tool itself has not been compared
  with plant data.

Tags of [phase1-equations.md](phase1-equations.md), from its own list (never upgraded):

- `FT`: full text read; the part read is stated.
- `EX`: excerpt only.
- `AB`: abstract or snippet only.
- `VP`: vendor, trade or teaching page.
- `CIT`: seen only as a citation inside another source.
- `[derived]`: computed or inferred by the note's author, with the derivation or the script named.
- `[from memory]`: recalled without a source, not verified.
- "as printed": transcribed although it looks wrong, with the reason given beside it.

## Statements later corrected

- **8011 minimum strength.** The first battery-foil report grouped 8011 with the high-strength
  grades of the collector-foil standard, at about 220–230 MPa or more. The grade report found the
  standard's minimum for 8011 to be 180 MPa; the catalogue records the correction with both
  sources.
- **"No foil-bite benchmark with fully known inputs was found."** The bite gap study found one
  (Fleck et al. 1992) and ran the tool's foil model on it: 0.42 of the reference load. The merged
  gap study records this.
- **Feed-mark spacing below 30 mm** (`grinding_feed_marks`): printed final-pass feeds reach
  53 mm on foil rolls (roll-grinding report, 4.1); the ceiling is now 60 mm (guide 6.2).
- **One mark count from 1 to 8** (`work_roll_borne_marks`): grinder chatter leaves 12-240 marks
  per circumference; the count can now be computed from the grinder's wheel and roll speeds, and
  without grinder data such a pitch is neutral, not a contradiction (roll-grinding report 4.2;
  guide 6.3).
- **De-trending order 2 for a measured roll profile**: it leaves a residual of a cosine crown
  larger than the worked case's bump; the default is now 4 with both orders reported, and the
  worked case's 2 um crown is replaced by an example of 40 um on radius (roll-grinding report
  3.4, 8 (b); guide 7.9).
- **"At least five positions" for a measured roll profile**: a 21-station report cannot carry a
  20-30 mm stripe; the section now reports the smallest resolvable width and flags a coarse grid
  (roll-grinding report 3.4; guide 7.9).
- **Disagreements between the gap reports** (the size of the elastic strip zones at foil gauge,
  the share of load carried outside the strip in a closed gap, which gap best explains "worse at
  thin gauge") are listed in the merged gap study and were not resolved.
