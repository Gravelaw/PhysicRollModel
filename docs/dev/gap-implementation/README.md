# Working material for the coverage-gap implementation

These are the working briefs and prototypes for implementing
[simulation-coverage-gaps.md](../../simulation-coverage-gaps.md), section 8, phases 0 to 3. They
are kept in the repository so the work can be resumed from a fresh checkout. They are working
documents, not maintained ones: the maintained description of what was built is
[band-diagnosis.md](../../band-diagnosis.md) and the implementation-status section of the gap
study. Whether this folder stays in the final pull request is to be decided when it is opened.

## Files

| File | What it is |
|---|---|
| `SPEC-house-rules.md` | House rules every brief refers to (its section 0). |
| `SPEC17.md` | Phase 0 brief: nine packages. |
| `SPEC18.md` | Phase 1 brief: twelve packages (amended 2026-11-20 after the equation research; its header lists the changes). |
| `SPEC19.md` | Phase 2 brief: fifteen packages. |
| `SPEC20.md` | One inserted package: four corrections of the grinding rules, from `docs/research/band-screening-2026-11/roll-grinding.md`. |
| `SPEC21.md` | One inserted package: the register of limitations and exceptions, `docs/limitations.md`, with its generator and tests. |
| `SPEC22.md` | One inserted package: spray header step 1 (nozzle footprint, pattern width, flow exponent, a realistic-header demo), from `docs/research/band-screening-2026-11/spray-nozzles.md`. |
| `research_phase1_equations.md` | Literature research for Phase 1 (source prefix `E`). Moved by Phase 1 package 1 to [phase1-equations.md](../../research/band-screening-2026-11/phase1-equations.md); no longer in this folder. |
| `prototypes/` | The planners' and the researcher's scratch scripts. Prototypes, not specifications; where they differ from a brief, the brief holds. Inside the briefs they are named by their original scratch folders: `s21` is `prototypes/phase0`, `s23` is `prototypes/phase1`, `s24` is `prototypes/phase1-research`, `s25` is `prototypes/phase2`. |
| `verify_additive.py` | Compares the working-tree artifacts with the last commit and reports added, grown, changed and removed paths. Run from the repository root. |
| `verify_tests.sh` | Runs the band test modules in four parallel groups and the smoke script. Run from the repository root. |

## Status

The commit history of the branch is the record of which packages are done. Briefs: Phase 0
`SPEC17.md`, Phase 1 `SPEC18.md`, Phase 2 `SPEC19.md` (it still names Phase 1 packages by their numbers
before the amendment; the mapping is in `SPEC18.md` section 5);
the Phase 3 brief is not written yet.

Decisions taken on the open decisions of `SPEC17.md` section 3: all as the planner chose. In
addition, the flag `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD` stays set in the battery-foil demo (the
brief's sentence that no conditional flag is set there was wrong).

## Standing requirement for the guided app (owner, 2026-11-20)

The app must stay streamlined and simple as the gap add-ons are attached, and its outputs (graphs,
tooltips, other visualisations) must be good and clear to look at: people should want to use it.
Every app package, and one consolidation pass before the pull request, is held to this:

- The default path stays the three input steps and the result. Nothing an add-on needs is asked
  on the default path.
- Add-on inputs sit behind progressive disclosure, grouped by what the person has (a flatness
  roll, a thickness gauge, a temperature scan, a roll grinder report, pass records, oil data),
  one line per group when collapsed, showing whether it is filled in.
- Add-on results appear only when their input was given, and all use one card pattern: one
  sentence saying what it means, one chart, one "how to read this" line, details collapsed.
- Charts share the strip's width scale where they show the width, have labelled axes with units,
  label lines directly where they can, use a palette that survives colour blindness and both
  themes, and give the exact value with its plain meaning in a tooltip on hover and on keyboard
  focus.
- Technical terms carry a plain-word tooltip the first time they appear on a screen.
- Desktop and phone screenshots of every new or changed screen are reviewed before the package
  is accepted.
