# SPEC21 — A register of limitations and exceptions

Repository `/home/user/PhysicRollModel`. One work package, inserted into Phase 2 after its
Package 5. House rules as for every package (section 0 of `SPEC.md`, section G of `SPEC17.md`
with the later amendments). Documentation and tests only: no engine result may change;
`python scratchpad/verify_additive.py` must show zero added and zero changed paths. Do not
commit.

## Why

The owner has asked for one document that collects the exceptions and limitations of the tool:
the places where a result depends on something nobody measured, where a model is reduced, where
the tool cannot decide, and what would lift each. Today they are scattered: section 14 of
`docs/band-diagnosis.md` ("Limitations and open discrepancies"), the `limitations` lists and
flags inside results, `band_plain.FLAGS`, the benchmark verdicts, the gap study's implementation
status, `docs/band-app.md` and commit messages. A plant reader should find them in one place,
written plainly, and the document must not drift from the code.

## What to build

### 1. `docs/limitations.md` — the register

Plain language throughout (a plant engineer reads it; no engine tokens in the prose, flag names
only in the "how the result shows it" column, in code font). Structure:

1. **How to read this register** (short): what counts as a limitation (a reduced model, a
   missing effect), an exception (a case the tool refuses, leaves neutral or cannot decide), an
   analyst choice (a number or rule the project chose because the literature gives none), and a
   recorded discrepancy (a benchmark the model does not match). The standing statement that
   nothing has been compared with plant data.
2. **Register tables, one per area**: roll bite; friction and oil; flow stress and material;
   roll cooling and heat; strip shape and flatness; measurement (shapemeter, gauge); flatness
   control loop; coil, winding and web handling; mill dynamics and chatter; roll grinding and
   roll surface; products and data; the guided app. Columns:
   `id` (stable, `L-<area>-<nn>`), `what the tool assumes or cannot do`, `what it means for a
   reader` (direction and size where the code or the guide gives one, otherwise "size not
   known"), `how the result shows it` (flag, status word, section or note key), `what would lift
   it` (a named measurement or input, or the gap id and phase), `kind` (limitation / exception /
   analyst choice / discrepancy).
3. **Outcomes that depend on an unmeasured input** — a short list drawn from the tables, because
   these are the ones a reader most needs: for example whether the spray loop settles or keeps
   trimming (zone weighting and first-change timing); the sign of the net band twenty seconds
   after a zone closes (inlet weight); stripe heights (heat share and spray coefficient, with the
   basis of published spray coefficients not established); the friction-stripe sensitivity (two
   levels two orders of magnitude apart, the exit-tension feedback not confirmed by the
   literature); the foil-bite reference load (end length not stated by the paper); the pitch test
   for grinder chatter without grinder data; the fitted step-test constant (grows with the test
   length).
4. **Analyst choices** — a table of every constant or rule tagged `[D]`, "analyst choice",
   "the tool's own" or "the project's own" in the code and the briefs' implementations: value,
   where it is used, what it stands in for, and its sensitivity where the code reports one.
   Collect them by searching the code for those tags; do not rely on memory.
5. **Recorded discrepancies with published values** — GENERATED from the benchmark harness (see
   2 below): case, quantity, project value, reference, ratio, verdict, for every row whose
   verdict is not within the agreement band, and the list of cases not encoded with the reason.
6. **What is not modelled at all** — the gaps still open after the phases done so far, by gap
   id with one plain line each, generated from or checked against section 11 (implementation
   status) of `docs/simulation-coverage-gaps.md`.
7. **How this register is kept** — the rule of 3 below.

Content comes from what exists: section 14 and the per-section limit paragraphs of
`docs/band-diagnosis.md`, the `limitations` strings and flags in the engine modules, the
`FLAGS` sentences, `docs/band-app.md` limits, the benchmark table, and the gap study. Do not
invent a limitation and do not drop one that the guide states. Where two places disagree, stop
on that point and report it.

### 2. Generated blocks and their generator

- A small generator in the package (follow the pattern of the product guide:
  `python -m physicroll.band_products --write docs/thin-gauge-products.md`): for example
  `python -m physicroll.limitations --write docs/limitations.md`, which rewrites ONLY the blocks
  between marked comment lines (the discrepancy table of part 5, the flag index below) and
  leaves the hand-written register untouched. Standard library only.
- **Flag index** (generated, at the end of the document): every top-level flag the engine can
  set, with its plain sentence from `band_plain.FLAGS` and the register id(s) it belongs to, or
  the word "informational" for flags that only say a section was applied. The mapping flag ->
  register id lives in one table in the generator module.

### 3. Tests that keep it honest (`tests/test_limitations_register.py`)

- The committed `docs/limitations.md` equals the generator's output for the generated blocks
  (compare text with line endings normalised; read as UTF-8).
- Every flag in `band_plain.FLAGS` appears in the flag index, each mapped to at least one
  existing register id or marked informational; every register id named in the mapping exists in
  the document; no register id is duplicated.
- Every benchmark row with a verdict outside the agreement band appears in part 5.
- Every `[D]` / analyst-choice constant found by the same search the document used is named in
  part 4 (the test repeats the search over `physicroll/*.py` with a stated pattern and checks
  that each hit's constant name appears; keep the pattern simple and say in the test what it
  does not catch).
- The prose contains no forbidden word of `band_plain.FORBIDDEN` (it must not read as a finding
  or a probability).
- Module under 50 s alone.

### 4. Links and the standing rule

- `README.md`, `docs/band-diagnosis.md` (a pointer at the top of section 14; section 14 itself
  stays), `docs/band-app.md` and `docs/simulation-coverage-gaps.md` point to the register.
- The guided app's result page already says the result is a shortlist from an unvalidated model;
  add one line under the trust block naming the register file ("the full list of what this tool
  assumes and cannot decide is in docs/limitations.md of the repository") — text only, through
  the page sources, no new route. If that cannot be done without rebuilding the page, leave the
  app alone and say so.
- Add to `docs/dev/gap-implementation/README.md`... NO: do not touch `docs/dev/`. Instead state
  the rule in part 7 of the register itself: every change that adds a reduced model, an
  exception, an analyst choice or a flag adds its row here in the same change, and the tests
  above fail if a flag or a discrepancy is missing.

## Do not

- Do not change any engine behaviour, flag name, limitation string or score.
- Do not soften or strengthen a statement while moving it: keep the guide's meaning, in plainer
  words where needed.
- Do not list every optional input as a limitation; an input that is simply not supplied is not
  one. A model that is reduced when the input IS supplied is.

## Hand back

At most 300 words: files and line counts; the number of register rows per area and of analyst
choices, discrepancies and open gaps; each test in one line; commands and results; any
disagreement between sources that you stopped on; anything in this brief you could not do as
written.
