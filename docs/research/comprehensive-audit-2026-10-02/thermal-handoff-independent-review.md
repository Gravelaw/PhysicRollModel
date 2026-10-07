# Independent review of the thermal numerical handoff

Review date: 2 October 2026. Scope: [thermal handoff](thermal-numerical-handoff.md), [structured numerical evidence](thermal-demo-checks.json), the corresponding current APIs, and immutable physics baseline `caec37ef86a8b78e1eb88292ea6368bfb64bcbdc`. This reviewer did not author the handoff or its audit driver. No implementation, scenario, test or stored demonstration artifact was changed. This review does not certify physical rolling predictions.

## Outcome and corrected findings

The mathematical diagnosis and proposed division of corrective work are supported. The evidence distinguishes an unchanged-law rejection, a temporal integrator change and an explicit spatial-contact model revision. Time subdivision alone cannot repair the demonstrated stream overshoot. The ordinary examples remain bounded synthetic demonstrations at their supplied inputs, with full-process entropy explicitly unresolved.

Two small publication corrections were requested:

- **TH01:** Both ordinary passive demonstrations have strip-to-roll heat transfer. Their two isolated-contact tests do not demonstrate both heat-flow directions. Describe both recorded pass inlet states; retain reversal as separate future acceptance coverage.
- **TH02:** The necessary-and-sufficient zero-source bound `G/2*abs(1/Cs−1/Cr) <= 1` assumes unequal inlet temperatures. Equal inlets give zero heat transfer for any nonnegative G, so they are a separate trivial case.

Both corrections are now present in the handoff. Neither changes the numerical counterexamples or recommended scope. Final artifact hashes and integration checks are recorded below.

## Independent mathematical check

The inspected public API uses a steady strip enthalpy rate and finite roll storage over a time interval. Consequently `Cs=mdot*cp_s` and `Cr=M*cp_r/dt` both have units W/K, although only the latter contains the time interval. The contact law combines the strip's inlet/outlet representative temperature with the roll's temporal midpoint. Treating these as two closed thermal masses would change the problem.

With no other sources and constant positive specific heats, direct substitution gives

```text
Q = G*(Tr,in−Ts,in) / [1 + G/(2*Cs) + G/(2*Cr)]
Ts,out = Ts,in + Q/Cs
Tr,out = Tr,in − Q/Cr.
```

For unequal inlets, requiring both outlets to lie between the two inlets gives the stated absolute-difference criterion. This is a finite-step endpoint bound, not a proof of local temperature ordering, a resolved bite field, or aluminium accuracy. Equal initial temperatures remain unchanged. Exact entropy requires the stream entropy gain plus roll storage, not heat divided by representative temperatures.

The handoff's general constant-property formula including powers A and B follows from the same substitution. Its continuous-time roll alternative has `Gamma=G/[1+G/(2*Cs)]`; the exact exponential roll solution is valid for the stated constant inputs. Its backward-Euler alternative is appropriately presented as a different time evaluation, not an already implemented remedy. In a fixed-roll limit the retained stream closure has factor `(1−NTU/2)/(1+NTU/2)` and overshoots for `NTU>2`. The exponential plug-flow reference eliminates that issue only by adopting a declared spatial conductance/source distribution. Dividing G during time subdivision would change the supplied physical law.

The variable-cp entropy expression is correct: integrate `cp(T)/T`, split at property knots and respect the supplied temperature domain. No cooling-transfer temperature or nonthermal-material entropy is inferred. Positive thermal-state entropy in the ordinary heated examples is therefore correctly not called full-process entropy validation.

## Reproduced probes and numerical evidence

The reviewer rebuilt dataclass inputs from the durable JSON and called the current `handoff_pass` API for all three counterexamples, all four ordinary flowing/passive pass inputs and all four isolated-contact variants. Tuple restoration is necessary for heat-capacity knots and material history. The handoff's minimal replay provides that conversion. All recorded outlet temperatures reproduced.

An independent direct algebra evaluation gave:

| Probe | Strip outlet, K | Roll outlet, K | Whole-step entropy rate, W/K | Conclusion |
|---|---:|---:|---:|---|
| Temporal I01, M=1 kg, dt=5 s |300.407251355|280.415168321|−0.018978788|Endpoint bound and entropy fail |
| Stream I01, M=500 kg, dt=0.001 s |339.235731887|319.998474515|+2.923883|Endpoint bound fails although entropy is positive |
| Same stream, dt=0.00001 s |339.237213318|319.999984745|+2.924143|Reducing dt does not repair spatial overshoot |

The first case reproduces `Q=3958.483167894 W`, the positive midpoint diagnostic `0.000173868142 W/K` and first-law residual about `−2.21e−10 W`. The shortest-step case has more cancellation in the storage calculation: the API first-law residual is approximately `0.000185093 W`, but its relative residual remains within the present gate. The handoff appropriately calls for dimensional and cancellation-aware checks rather than treating any small relative residual as complete verification.

For all eight ordinary/isolated evaluations, a separately written composite Simpson integration of `cp(T)/T`, split at knots with 1,000 intervals per traversed segment, agrees with the JSON's exact piecewise-linear entropy values within `2e−8 W/K`. This checks the diagnostic independently of the author's exact-integration implementation. It does not supply absent cooling/nonthermal entropy closures.

The reviewer also reproduced 32-substep temporal compositions for all four ordinary pass inputs: G, mass flow and source powers stay fixed; fresh inlet strip is processed each interval; roll temperature alone is carried within the pass. The enthalpy-mean strip and roll outputs match the recorded values. For passive passes 1/2, the final instantaneous strip outlet exceeds the enthalpy-mean outlet by approximately `0.0343873/0.0357474 K`. Thus an implementation must explicitly define the time-varying outlet/aggregation contract before schedule propagation. Refeeding that outlet as the next time-substep inlet would be a different physical problem.

The standalone closed-capacity ordinary and isolated outputs were also reproduced as exact dictionaries. The JSON contains all 36 stated partition-sensitivity records, each explicitly a first-law/property-domain check. No full test suite was rerun by this independent review. The author's 27 selected existing tests are separately reported evidence; the present work independently reproduced the focused APIs, algebra, entropy and refinements rather than repeating that suite. The checked schedule fixture is correctly distinguished from the stored two-pass demonstration because its second-pass mechanical inputs and cell counts differ. Its `INDETERMINATE` bound status is retained.

## Provenance and ordinary-demo scope

All 15 source/configuration/script/test SHA-256 values in the structured evidence were independently checked against both the current files and the corresponding Git blobs at the stated physics baseline. All four stored/fresh artifact hash pairs matched the JSON. The fresh foundations artifact differs from its stored counterpart only by the five listed added `slab_optional` metadata fields; there are no changed existing values or thermal outputs. The other three ordinary artifact comparisons are byte-identical.

The isolated counterexamples retain synthetic mechanical state metadata while zeroing the specified heat/work/residual fields to expose the thermal operator. This is appropriately identified as an operator test, not a mechanically complete rolling experiment. The ordinary parameters, heat partitions, effective roll mass and conductance remain synthetic. Neither retained examples nor passed numerical checks establish measured aluminium accuracy, qualified equipment limits, interpass kinetics, thermal feedback to force, or deployment readiness.

## Acceptance and remaining decisions

The proposed later task has an appropriate first boundary: preserve the current equations, add the regressions and define admissible results/rejections before extending the model. A guard established only for zero sources must not be advertised as a general-source guarantee. Legitimate source-driven heating can exceed the initial temperature interval; any broader bound needs a corresponding derivation or independently qualified reference.

The acceptance matrix covers energy, exact isolated entropy, endpoint bounds, zero/reversed/equal-temperature cases, property knots and domains, source partitions, fixed-G temporal refinement, separately versioned spatial refinement, failures and schedule composition. Its proposed numerical tolerances are explicitly provisional verification targets. They are not measurement uncertainty or a physical validation allowance. Keeping midpoint diagnostic semantics explicit, rejecting unsupported roots rather than clipping them, and preserving pass-history increments independently of numerical substeps are necessary conditions.

TH01/TH02 are resolved. No publication-blocking mathematical or evidence issue remains in the reviewed handoff. Implementation choices, empirical calibration and plant deployment remain outside this documentation review. The consolidated inventory/README cross-check is recorded below.


## Final acceptance and integration check

**Accepted for documentation publication; TH01 and TH02 resolved.** Both executable Markdown replay blocks were extracted verbatim and executed from repository root. The short block reproduced all three open counterexamples. Appendix A passed all four isolated/refinement/partition replays and reproduced all three counterexamples. No temporary driver is needed to reproduce that documented evidence. The final JSON metadata update does not change the numerical inputs or outputs.

Reviewed thermal artifacts:

| Artifact | SHA-256 |
|---|---|
| `thermal-numerical-handoff.md` | `13dcd958806723d0ddeb13d40bc05722d9d8d2fc1542c4a3663616e914e706d4` |
| `thermal-demo-checks.json` | `2ca0562b8db97b8527b6525e418648be8f6c64df3c106d31003d61213e6869a4` |

The parent-integrated source ledger independently reconciles to **182 identities: 171 technical and 11 orientation**. All 159 previously published IDs retain their original DOI, source type and identity URLs. The 23 new identities are the 14 fundamentals sources R149–R163, excluding intentionally unused R153, and nine operational sources R164–R172. There are still 146 baseline identities; 36 were added by this research across both publications. No historical U001 book identity has been silently recovered or replaced.

The access totals independently match the ledger and README: 16 full-text, 37 partial-text, 57 relevant official-document, 34 abstract-only, 21 metadata-only, six unavailable and 11 orientation. Every technical source has review annotations. The fundamentals subset retains six partial-body, five metadata and three abstract/summary records; R161 remains abstract-only and its reviewed teaching material remains separate R163. All six fundamentals artifact hashes still match their independent review. No whole-book review is claimed. R165 retains the corrected official document edition `3BDD017150-EN 08.2017`, distinguished from the later filename.

All 52 traceability IDs are unique and their source references resolve. All 98 local Markdown links present at this review checkpoint resolved. README source-category/access tables and scholarly-plus-thesis counts agree with the ledger, and it labels the original 159-source review as historical. Parent validation also reports 182/171 sources, 52 trace rows and no missing links; its earlier link count reflects the files present when it ran. Final publication should rerun the existing validator after all independent review files are written.

The remaining gaps are substantive and explicit: historical book identities/access, case-specific conventions and raw data, independent aluminium validation, the open thermal admissibility limitation, output aggregation/model-version decisions, and later deployment requirements. They do not block publication of this qualified research handoff; they block the corresponding stronger implementation or physical-validity claims.
