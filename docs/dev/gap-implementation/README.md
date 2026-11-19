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
| `SPEC18.md` | Phase 1 brief: nine packages. **To be amended** with the findings of `research_phase1_equations.md` before Phase 1 coding starts. |
| `SPEC19.md` | Phase 2 brief: fifteen packages. |
| `research_phase1_equations.md` | Literature research for Phase 1 (source prefix `E`). The first Phase 1 package that uses it moves it to `docs/research/band-screening-2026-11/phase1-equations.md`. |
| `prototypes/` | The planners' and the researcher's scratch scripts. Prototypes, not specifications; where they differ from a brief, the brief holds. Inside the briefs they are named by their original scratch folders: `s21` is `prototypes/phase0`, `s23` is `prototypes/phase1`, `s24` is `prototypes/phase1-research`, `s25` is `prototypes/phase2`. |
| `verify_additive.py` | Compares the working-tree artifacts with the last commit and reports added, grown, changed and removed paths. Run from the repository root. |
| `verify_tests.sh` | Runs the band test modules in four parallel groups and the smoke script. Run from the repository root. |
| `wip/phase0-package6-in-progress.patch` | Unfinished, unverified work on Phase 0 package 6, saved at the pause. Applies to commit `ab4f4ea`. It has no tests or documentation yet, and its artifacts are not included (regenerate them). |

## Status at the pause (2026-11-19)

| Phase | Brief | State |
|---|---|---|
| 0 | `SPEC17.md` | Packages 1 to 5 committed (`2d0bc71`, `7166c5f`, `9b9fade`, `4f60b5e`, `ab4f4ea`). Package 6 in progress (the patch above). Packages 7 to 9 not started. |
| 1 | `SPEC18.md` | Brief written; amendment after the equation research not yet made. |
| 2 | `SPEC19.md` | Brief written. |
| 3 | none yet | Brief not started. |

Decisions already taken on the open decisions of `SPEC17.md` section 3: all as the planner chose.
In addition, the flag `MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD` stays set in the battery-foil demo
(the brief's sentence that no conditional flag is set there was wrong).
