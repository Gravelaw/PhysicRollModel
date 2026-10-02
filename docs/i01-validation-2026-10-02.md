# I01 bounded passive-contact validation — 2 October 2026

Base: verified remote main `caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`.
Development branch: `dev/i01-passive-contact-admissibility`.
Research source: immutable commit
[`a993fc40549061da5a2b1848656ec5257a9419a6`](https://github.com/Gravelaw/PhysicRollModel/tree/a993fc40549061da5a2b1848656ec5257a9419a6/docs/research/comprehensive-audit-2026-10-02),
read through `git show`; not merged. No AGENTS.md or populated `.agents/skills`
was present in the workspace/repository. All work ran in the saved Codex cloud environment.

## Regression and compatibility evidence

The initial 86 tests passed. Before implementation the new I01 rejection tests
failed on all three counterexamples; the old large-G test also demonstrated that
an energy/representative-entropy pass admitted unsupported results. The final
suite has 92 passing tests, including all existing standalone and schedule tests.

```
python -m unittest discover -s tests -q
python scripts/smoke.py
python scripts/run_flowing_energy_demo.py --config scenarios/passive_contact_demo.json --out /tmp/i01-passive-demo.json
python scripts/run_flowing_energy_demo.py --config scenarios/flowing_energy_demo.json --out /tmp/i01-flowing-demo.json
git diff --check
```

All passed. Prescribed demo SHA-256 remains
`70ba963e8a53d718dee4a14f81aa488072f888a73547982488f214b54cebd5c4`.
Fresh passive demo SHA-256 is
`e3ed6a5b903dd87250b70bc36b5773c74174afa29dd543d4ac81f0ece4ea7144`.
Deleting only the four new entropy/domain fields reproduces the entire historical
passive JSON object exactly, including every prior numerical field and pass.
Historical artifacts were preserved. Both demos have maximum absolute energy
residual `1.1496013030409813e-9 W`.

The research handoff Appendix A driver was extracted from the immutable research
commit and run using its `thermal-demo-checks.json` snapshots. Only the evidence
path and final counterexample expectations changed: the three findings must
raise `ValueError` containing `passive contact outside supported monotone capacity
domain`. All four ordinary cases passed their isolated-contact, six temporal
refinements (1/2/4/8/16/32) and nine heat-partition comparisons: 24 refinements and
36 partition cases. G, mass and powers were preserved, fresh strip was used at
each temporal subdivision, and enthalpy/entropy aggregation followed the handoff.
All three exact counterexample snapshots rejected. This replay verifies existing
ordinary computations; no new integrator or convergence order is claimed.

New retained tests cover the temporal and spatial counterexamples, their differing
entropy signs, reversed/equal inlets, capacity-domain edge and rejection, variable
cp across knots and asymmetric domains, independent Simpson entropy integration,
antisymmetry/additivity, zero G and property endpoints, small G, numerical capacity
over/underflow, source-driven heating/cooling, cancelling sources with incomplete
entropy accounting, property-root rejection inside the capacity domain, and
propagation of passive rejection through checked schedules.

## Independent review

A separate Astra physics reviewer approved the final domain, matrix proof,
entropy contract and unchanged equations, with no blocking findings. It also
ran the passive/schedule suites and compared the entropy integral against a
70-digit Decimal analytic reference over 36 ordinary, steep and narrow segments
(100/300/2900 K; widths 1e-9/1e-5/0.1/50 K; cp endpoints 1/100000, 100000/1,
900/901). Worst relative discrepancy was `4.65e-15`.

A separate correctness reviewer found no blocking implementation/API regression,
ran the full suite at its 89-test stage, and checked 1,000 deterministic randomized
supported variable-cp pure-exchange cases. All met inlet bounds and nonnegative
entropy (smallest observed rate `4.265688e-5 W/K`). Its cooling-only probe admitted
both outlets below their inlets and reported incomplete entropy correctly.
Review suggestions were resolved by retained cooling/cancelling-source tests,
variable-cp exchange tests, and whole-object historical demo comparison. The
final full suite was rerun after those changes.

This evidence establishes bounded software/numerical behavior only. The domain
is sufficient and conservative; outside-domain rejection does not prove every
rejected case is physically impossible. Sources/exports still lack complete
entropy closure; no thermal calibration, new material/contact law, optimizer,
main merge or deployment is included.
