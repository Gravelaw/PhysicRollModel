# Band / chatter-mark root-cause simulation — implementation spec

Repository: `/home/user/PhysicRollModel` (Python package `physicroll`, a synthetic four-high
**aluminium cold rolling** demonstrator). The plant problem: transverse "stress marks or
bands" on strip, **more prevalent at thinner gauges** (sub-mm down toward foil stock). Goal:
an opt-in simulation + differential-diagnosis tool that reproduces candidate band mechanisms
and ranks root causes against what the plant observes, and shows which levers (speed,
reduction, tension, friction/lubrication, coolant sprays) move the result.

## 0. House rules (apply to every file)

- **Standard library only.** No numpy/scipy. Python >= 3.10 (CI runs 3.10 and 3.12; avoid
  3.11+ only syntax/APIs).
- **SI units everywhere**, unit suffix in every field name (`_m`, `_pa`, `_n`, `_m_s`, `_hz`,
  `_rad`, `_kg`, `_n_m` for stiffness N/m, `_n_s_m` for damping N·s/m). Angles in radians.
- Frozen dataclasses for inputs with a `validate()` that raises `ValueError` with a clear
  message on non-finite, bool-as-number, out-of-domain values (see `physicroll/model.py`,
  `physicroll/contact.py` for the style). Results are plain JSON-serialisable dicts
  (`json.dumps(..., allow_nan=False)` must work): no NaN/inf, no tuples-with-objects, no
  complex numbers (split into real/imag).
- Every result dict carries a `status` string that is honest about validation, e.g.
  `'UNVALIDATED_LINEAR_CHATTER_SCREEN'`, plus `flags` (list of UPPER_SNAKE strings) and
  `limitations` (list of sentences). **Never claim plant validation, probabilities or
  certified causes.** This repo is strict about separating software verification from
  physical validation. Evidence is tallied (SUPPORTS / CONTRADICTS / NOT_OBSERVED), not
  turned into probabilities.
- Do **not** modify existing modules, scenarios, artifacts, schemas or existing tests
  (several are checksum-pinned). New files only, except where a section explicitly says to
  append to `README.md` / `docs/capabilities.md`.
- Tests: `unittest`, files `tests/test_*.py`, run with
  `python -m unittest tests.test_<name> -v` from the repo root. **Do not run the whole
  suite** (`unittest discover` takes ~8 minutes); run only your own test modules. Each new
  test module must finish in well under 60 s.
- Do not commit, push, or create branches. Leave changes in the working tree.
- Keep modules readable: docstring at top stating equations, sign conventions, sources and
  what is NOT modelled. Moderate line lengths (<= 100).

## 1. Physics: third-octave gauge chatter model (`physicroll/chatter.py`)

### 1.1 Sign conventions
- `x_w`, `x_b`: vertical displacement of the *upper* work roll / backup roll, positive
  **away from the pass line** (gap opening). The lower half is the mirror image
  (symmetric mode), so roll-gap perturbation `dh = 2*x_w`. Exit-thickness perturbation is
  taken equal to the gap perturbation (no elastic strip recovery).
- `dF`: perturbation of total separating force, positive = pushes the rolls apart.
- `sigma_e`, `sigma_x`: entry / exit strip **tensile** stress perturbations [Pa].
- `u_e`, `u_x`: strip entry / exit speed [m/s]; `V_r` roll surface speed (held constant —
  drive inertia is large at chatter frequency); forward slip `f = u_x/V_r - 1`.

### 1.2 Structure (per half stack; symmetric about pass line)
```
M_w*x_w'' = -K_wb*(x_w - x_b) - C_wb*(x_w' - x_b') + dF
M_b*x_b'' = +K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*x_b - C_h*x_b'
```
`K_h` = housing/screw/chock/hydraulic stiffness seen by one half stack, `K_wb` = work-roll /
backup-roll contact stiffness. Static mill modulus (force per unit gap opening):
`K_mill = 1 / (2*(1/K_wb + 1/K_h))`.

### 1.3 Linearised roll bite
```
dF = F_h*dh + F_hdot*dh' + F_se*sigma_e + F_sx*sigma_x + F_hin*dh_in
df = f_h*dh + f_se*sigma_e + f_sx*sigma_x + f_hin*dh_in          (forward slip)
```
with `F_h = dF/dh_exit < 0` (plastic "strip modulus" `Q_s = -F_h`), `F_se = dF/dsigma_entry < 0`,
`F_sx = dF/dsigma_exit < 0`, `F_hin = dF/dh_entry > 0`.

Bite damping closure (declared heuristic, unvalidated; scales as 1/speed as reported by Hu,
Zhao & Ehmann 2006 and Kimura et al. 2003): the bite reacts to the gap a transit-time
fraction ahead, `F_hdot = F_h * beta * l_d / u_x` (negative → resists closing/opening
velocity), where `l_d` = contact length, `beta` = `bite_damping_transit_fraction`
(default 0.5; 0 disables). Report results for the supplied beta **and** for beta = 0 so the
user sees how much of the margin rests on this closure.

### 1.4 Strip kinematics and tension
Volume continuity through the bite: `u_x = V_r*(1+f)`, `u_e = u_x*h_exit/h_entry`.
Linearised (nominal `h0` entry, `h1` exit thickness):
```
du_x = V_r*df
du_e = V_r*[ (h1/h0)*df + ((1+f)/h0)*dh - ((1+f)*h1/h0**2)*dh_in ]
```
Strip spans are lumped elastic springs with constant-speed far ends (pay-off / tension reel
or a non-slipping deflector roll act as velocity nodes at chatter frequency):
```
sigma_e' = +(E/L_e)*du_e          (entry span stretches when the bite pulls strip in faster)
sigma_x' = -(E/L_x)*du_x          (exit span slackens when the bite delivers strip faster)
```
State vector (documented order) `z = [x_w, x_w', x_b, x_b', sigma_e, sigma_x]`,
`z' = A z + B_k * d_k(t)`.

Feedback mechanism to state in the docstring: gap opens → more strip drawn in → entry
tension rises as the *integral* of gap opening (90° lag) → force drops → the force component
in phase with gap velocity does positive work = negative damping, growing with speed.

### 1.5 Analytic benchmark (must be a unit test)
Single-DOF limit (one mass, gap coordinate `h`, only entry tension, `f_h = f_se = f_sx = 0`,
`F_sx = 0`):
`M*h'' + C*h' + K*h = -Q_s*h - D*h' - N*sigma`, `sigma' = (E/L)*(u_x/h0)*h`, with
`N = -F_se > 0`, `D = -F_hdot`. Characteristic cubic
`M s^3 + (C+D) s^2 + (K+Q_s) s + N*E*u_x/(L*h0) = 0`; Routh–Hurwitz gives (for D = 0)
```
u_crit = C*(K+Q_s)*L*h0 / (M*N*E)        onset angular frequency = sqrt((K+Q_s)/M)
```
In terms of the half-stack coordinates (`h = 2*x_w`, force `dF` acts on each work roll) a
single lumped mass `m` on spring `k`, damper `c` maps to `M = m/2, C = c/2, K = k/2`.
The general assembler must reproduce this (e.g. make the assembler generic over a supplied
structure, or use a very stiff `K_wb` with `m = M_w + M_b`; tolerance <= 1e-3 relative).

### 1.6 Deriving the bite response from the repo's slab model
Use `physicroll.slab._solve_grid(scenario, cells, 'established', None, contact_radius)` on
a `physicroll.model.Scenario` constructed directly (do **not** call `Scenario.validate()` —
it rejects exit gauge < 300 µm; this module declares its own extended, flagged domain).
`Scenario(name, True, h0, h1, width, entry_speed=1.0, R, density=2700.0, Y, mu, se, sx,
drive_efficiency=1.0)` — force and slip are rate-independent so the speed value is arbitrary.
Hitchcock circular flattening by damped fixed point (as `physicroll/contact.py`):
`R' = R*(1 + C_H*F/(width*(h0-h1)))`, `C_H = 16*(1-nu^2)/(pi*E_roll)`, relaxation 0.5,
tolerance 1e-10 relative, max 300 iterations (raise ValueError if not converged).
Reference prototype (numpy, for orientation only — re-implement cleanly, stdlib only):
`/tmp/claude-0/-home-user-PhysicRollModel/2f99237c-57ca-5a74-a3d6-b1fb23e86cf7/scratchpad/proto.py`.

Sensitivities by central finite differences about the nominal: step `1e-3*h1` for exit
thickness, `1e-3*h0` for entry thickness, `1e-3*Y` for each tension; each perturbed
evaluation re-converges the flattening radius. Repeat with half the step; if any
sensitivity changes by more than 2 % relative, add flag `SENSITIVITY_STEP_NOT_CONVERGED`.
Also evaluate the nominal force on `2*cells`; if relative change > 1e-4 add
`GRID_REFINEMENT_NOT_MET`.

Own domain checks (ValueError): finite positive numbers; `2e-5 <= h1 < h0`; reduction in
[0.02, 0.5]; `h0/R <= 0.05`; `width/h0 >= 20`; `0 < mu <= 0.3`; tensions >= 0 and below the
flow stress; `cells` int in [64, 4096]. Flags: `THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN` when
`h1 < 3e-4`; radius ratio `R'/R > max_radius_ratio` (default 1.5, caller may raise it up to
3.0) → ValueError explaining that circular flattening is outside its envelope and that a
foil (non-circular) contact model or supplied sensitivities are needed; if the caller's
envelope is above 1.5 and the ratio is in (1.5, max], add
`HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE`. Errors raised by `_solve_grid`
(e.g. "sticking model required") propagate as ValueError.

A `BiteResponse` may alternatively be **supplied** directly (e.g. from a plant mill model);
then `source='supplied'`.

Orientation numbers from the prototype (R=0.2 m, width 1.5 m, 30 % reduction, mu=0.05,
se=25 MPa, sx=30 MPa, half-stack M_w=3000 kg, M_b=22000 kg, K_wb=4e10, K_h=1.4e10 N/m,
3 % modal damping, E=70 GPa, L_e=L_x=4 m): 0.6→0.42 mm, Y=250 MPa: F=3.56 MN, R'/R=1.29,
f=0.0553, Q_s=12.2 GN/m, N=1.21e-2 m², critical exit speed 5.07 m/s (beta=0) and 15.2 m/s
(beta=0.5) at 179 Hz; unloaded modes 118.7 Hz and 620.8 Hz. Lower friction lowers the
critical speed strongly (mu=0.02 → 7.1 m/s at beta=0.5); higher reduction and higher entry
tension lower it; a longer entry span raises it.

### 1.7 Public API of `physicroll/chatter.py`
```python
@dataclass(frozen=True)
class BitePass:            # nominal pass, SI
    entry_thickness_m; exit_thickness_m; width_m; work_roll_radius_m
    mean_flow_stress_pa; friction_coefficient; entry_tension_pa; exit_tension_pa
    def validate(self)

@dataclass(frozen=True)
class BiteResponse:
    separating_force_n; forward_slip_fraction; contact_length_m; contact_radius_ratio
    entry_thickness_m; exit_thickness_m
    dforce_dexit_thickness_n_m          # F_h  (< 0)
    dforce_dentry_thickness_n_m         # F_hin
    dforce_dentry_tension_m2            # F_se (< 0)
    dforce_dexit_tension_m2             # F_sx
    dslip_dexit_thickness_per_m         # f_h
    dslip_dentry_thickness_per_m        # f_hin
    dslip_dentry_tension_per_pa         # f_se
    dslip_dexit_tension_per_pa          # f_sx
    source: str                         # 'derived_slab_hitchcock' | 'supplied'
    flags: tuple = ()
    def validate(self); def to_dict(self)

def derive_bite_response(bite_pass, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                         cells=256, max_radius_ratio=1.5) -> BiteResponse

@dataclass(frozen=True)
class StandModel:          # one half stack
    work_roll_mass_kg; backup_roll_mass_kg
    work_backup_contact_stiffness_n_m; housing_stiffness_n_m
    work_backup_damping_n_s_m; housing_damping_n_s_m
    @classmethod
    def from_modal_damping(cls, work_roll_mass_kg, backup_roll_mass_kg,
                           work_backup_contact_stiffness_n_m, housing_stiffness_n_m,
                           damping_ratio)   # C_h = 2*zeta*sqrt(K_h*(M_w+M_b)), C_wb = 2*zeta*sqrt(K_wb*M_w)
    @property
    def mill_modulus_n_m(self)
    def validate(self)

@dataclass(frozen=True)
class StripSpans:
    youngs_modulus_pa; entry_span_length_m; exit_span_length_m
    def validate(self)

STATE_NAMES = ('x_w_m','v_w_m_s','x_b_m','v_b_m_s','sigma_entry_pa','sigma_exit_pa')

def assemble_state_matrix(stand, bite, spans, exit_speed_m_s, *,
                          bite_damping_transit_fraction=0.5, couple_tension=True) -> list[list[float]]
def eigenvalues(matrix) -> list[complex]            # general real square matrix, n <= 12
def natural_frequencies(stand, strip_stiffness_n_m=0.0) -> dict
    # undamped closed-form 2-DOF: 'symmetric_hz' (K11 = K_wb + 2*Q_s; couples to the gap,
    # third-octave family) and 'antisymmetric_hz' (Q_s = 0: both work rolls move together,
    # gap unchanged — the fifth-octave family, 'no significant gauge change')
def stability(stand, bite, spans, exit_speed_m_s, **options) -> dict
    # modes: [{real_per_s, imag_rad_s, frequency_hz, damping_ratio}], max_growth_rate_per_s,
    # dominant_frequency_hz (of the least-stable oscillatory mode), stable (bool),
    # strip_pitch_m = exit_speed/dominant_frequency
def critical_speed(stand, bite, spans, *, speed_range_m_s=(0.05, 60.0), **options) -> dict
    # log-spaced scan (>= 80 points) for the lowest sign change of max growth rate, then
    # bisection to 1e-6 relative. status: 'UNSTABLE_ABOVE_CRITICAL_SPEED' |
    # 'STABLE_OVER_SCANNED_RANGE' | 'UNSTABLE_AT_LOWEST_SCANNED_SPEED';
    # critical_exit_speed_m_s (None if stable), onset_frequency_hz, onset_strip_pitch_m
def frequency_response(stand, bite, spans, exit_speed_m_s, frequencies_hz, *,
                       disturbance='work_backup_runout', **options) -> list[dict]
    # complex solve (j*omega*I - A) z = B. disturbances:
    #  'work_backup_runout': radial run-out e [m] at each work/backup contact (roll
    #     eccentricity, out-of-round, backup-roll surface marks), positive e pushes the work
    #     roll toward the strip: the contact spring force becomes K_wb*(x_w - x_b + e).
    #  'entry_thickness': incoming gauge ripple dh_in [m] (e.g. chatter marks from the
    #     previous pass of a reversing mill) via F_hin and the continuity term.
    # returns per frequency: exit_thickness_per_unit_disturbance (magnitude, m/m), phase_rad
def simulate(stand, bite, spans, exit_speed_m_s, *, duration_s, initial_gap_perturbation_m=1e-7,
             forcing=(), time_step_s=None, max_samples=4000,
             amplitude_limit_fraction=0.2, **options) -> dict
    # RK4 of the linear system. forcing: tuple of dicts {'disturbance': one of the two
    # above, 'amplitude_m': a, 'frequency_hz': f, 'phase_rad': 0.0}. Default time step
    # 0.05/max|eigenvalue|. Stops early and sets 'linear_range_exceeded': True when
    # |dh| > amplitude_limit_fraction*h_exit (the linear model cannot predict the limit
    # cycle / strip break). Returns decimated lists: time_s, strip_position_m (=u_x*t),
    # exit_thickness_perturbation_m, entry_tension_perturbation_pa,
    # exit_tension_perturbation_pa, plus fitted envelope growth_rate_per_s and
    # dominant_frequency_hz measured from the trace (zero-crossing based), for
    # cross-checking against the eigenvalues.
```
`**options` = `bite_damping_transit_fraction`, `couple_tension`.
Eigenvalue solver: balance (diagonal similarity scaling) → Hessenberg → shifted QR
(Francis or complex single-shift on a complex copy) with deflation; must handle complex
pairs and the widely different magnitudes here (stress states ~1e6–1e8 Pa vs displacement
~1e-6 m — scale the state vector, e.g. stress divided by a reference stress and
displacement by a reference length, before the eigen-solve; similarity scaling does not
change eigenvalues). Verify with residual checks in tests
(`|det(A - lambda*I)|` relative or reconstruct characteristic polynomial coefficients).

### 1.8 Tests `tests/test_chatter.py` (minimum)
1. `eigenvalues`: diagonal, rotation-block (±i·w), companion matrix of a known polynomial,
   a defective-ish/ill-scaled case; sum = trace, product = det within tolerance.
2. Single-DOF analytic benchmark of 1.5: critical speed and onset frequency within 1e-3;
   just below → stable, just above → unstable.
3. With bite damping: D = D0/u, `u_crit = [C*kappa + sqrt((C*kappa)^2 + 4*D0*kappa)]/2`,
   `kappa = (K+Q_s)*L*h0/(M*N*E)` (derive/confirm the form yourself from the cubic before
   asserting; if your derivation differs, trust the cubic and say so in a comment).
4. `natural_frequencies` equals the imaginary parts of the undamped, tension-decoupled,
   bite-free eigenvalues; prototype values 118.74 Hz and 620.79 Hz for the parameters above.
5. `derive_bite_response` reproduces the orientation numbers above within 1 %; signs of all
   sensitivities; force equals `solve_slab` + `solve_circular_contact` result for a
   >= 300 µm case (use `physicroll.contact.solve_circular_contact` as independent check);
   thin-gauge flag; radius-envelope rejection; supplied-response validation.
6. Critical speed for the 0.6→0.42 mm orientation case: 5.07 (beta=0) and 15.2 m/s
   (beta=0.5) within 2 %; monotonic trends: lower mu lowers it, longer entry span raises
   it, higher structural damping raises it, higher reduction lowers it.
7. `simulate`: growth rate and frequency measured from the trace agree with the dominant
   eigenvalue within 2 % (one stable and one unstable speed); undamped/decoupled case
   conserves amplitude; `linear_range_exceeded` triggers.
8. `frequency_response`: with tension coupling off, the low-frequency limit of
   `work_backup_runout` → `2*K_wb*K_h/(K_wb+K_h) / (2*K_wb*K_h/(K_wb+K_h) + ... )` — derive
   the exact static transfer from the equations and assert it (it is the classic
   gaugemeter attenuation `K_mill/(K_mill+Q_s)`-type result; work it out, including the
   factor of two for both halves); resonance peak near the loaded symmetric mode.
9. JSON-serialisability of every returned dict (`json.dumps(..., allow_nan=False)`).

## 2. Kinematic signatures and non-vibration screens (`physicroll/band_signatures.py`)

Pure functions + small frozen dataclasses. No dependency on `chatter.py`.

### 2.1 Pitch laws (the main discriminator)
- Fixed-frequency source (structural resonance, self-excited chatter): strip pitch
  `p = u_x / f` → **pitch proportional to speed**.
- Roll-borne / order-locked source (a mark or n marks on a roll, or a kinematic excitation
  locked to shaft rotation): `p = pi*D*(1+f)/n` for marks on a roll of diameter D printing
  through the work roll (backup-roll marks transfer at equal surface pitch to the work roll
  and then to the strip) → **pitch independent of speed**. An order-locked excitation at
  `order` × work-roll rotation frequency gives `p = pi*D_w*(1+f)/order`.
- Coil/mandrel-locked: `p = pi*D_coil` (drifts as the coil builds/pays off).
- Later passes stretch an existing pitch by `h_in/h_out`.
- `pitch_speed_exponent(observations)`: least-squares slope of ln(pitch) vs ln(speed) from
  >= 2 `(exit_speed_m_s, pitch_m)` observations at distinct speeds; ≈1 → fixed frequency,
  ≈0 → roll-borne; return slope, classification
  (`'FIXED_FREQUENCY'` if slope >= 0.7, `'SPEED_INDEPENDENT_PITCH'` if |slope| <= 0.3,
  else `'INDETERMINATE'`), and implied frequency per observation (`u_x/p`).

### 2.2 Bearing defect orders (Randall & Antoni 2011, MSSP, doi:10.1016/j.ymssp.2010.07.017)
n elements, element diameter d, pitch diameter D, contact angle phi, shaft frequency f_r,
`r = (d/D)*cos(phi)`: `BPFO = n/2*(1-r)`, `BPFI = n/2*(1+r)`, `FTF = (1-r)/2`,
`BSF = D/(2d)*(1-r^2)` (all as orders = multiples of f_r). Identities for tests:
`BPFO + BPFI = n`, `BPFO = n*FTF`.

### 2.3 Source catalogue
```python
@dataclass(frozen=True)
class MillKinematics:
    work_roll_diameter_m; backup_roll_diameter_m
    gear_meshes: tuple = ()      # dicts {'name', 'teeth', 'shaft_speed_ratio_to_work_roll'}
    bearings: tuple = ()         # dicts {'name','shaft':'work_roll'|'backup_roll','elements',
                                 #        'element_diameter_m','pitch_diameter_m','contact_angle_rad'}
    grinder_marks: tuple = ()    # dicts {'roll':'work_roll'|'backup_roll','marks_per_circumference'}
    deflector_roll_diameters_m: tuple = ()
    entry_coil_diameter_m: float | None = None
    exit_coil_diameter_m: float | None = None
    structural_modes_hz: tuple = ()   # dicts {'name','frequency_hz','family'}
def source_catalogue(mill, exit_speed_m_s, forward_slip_fraction) -> list[dict]
```
Each entry: `id`, `description`, `kind` (`'order_locked'`, `'fixed_frequency'`,
`'coil_locked'`), `frequency_hz` at this speed, `strip_pitch_m`, `pitch_speed_law`
(`'independent_of_speed'` / `'proportional_to_speed'` / `'drifts_with_coil_diameter'`),
`order_of_work_roll_rotation` where applicable. Include: work roll 1× and 2× (2× =
spindle/coupling misalignment, ovality), backup roll 1× and 2×, each gear mesh
(teeth × shaft frequency), each bearing BPFO/BPFI/BSF/FTF and 2×BPFI, grinder marks,
deflector rolls 1× (surface speed = strip speed on that side: exit-side by default),
coils, each structural mode. Work-roll rotation frequency = `V_r/(pi*D_w)` with
`V_r = u_x/(1+f)`; backup roll has the same surface speed.
`match_observed_pitch(catalogue, pitch_m, tolerance_fraction=0.08)` → entries whose pitch is
within tolerance, sorted by relative mismatch.
`resonance_speeds(mill, forward_slip, mode_frequency_hz)` → for every order-locked source,
the exit speed at which its frequency equals the mode frequency, and the strip pitch there
(this is the forced/resonant fifth-octave mechanism: an order-locked excitation crossing a
roll-stack mode at one speed, printing marks on the backup roll that then regenerate).

### 2.4 Material screens (Al–Mg yield-point marks: Lüders Type A, coil breaks)
- `bending_surface_strain(thickness_m, roll_or_coil_diameter_m)` = `t/D`.
- `yield_point_bending_window(thickness_m, diameter_m, yield_stress_pa, youngs_modulus_pa,
  luders_strain, tension_stress_pa)`: `eps_y = sigma_y/E`; onset `eps_y - sigma_t/E`
  (floor 0); status `'ELASTIC_NO_YIELD'` (eps_b below onset), `'IN_YIELD_POINT_WINDOW'`
  (onset <= eps_b <= eps_y + luders_strain → discontinuous yielding/kink/Lüders risk if the
  material has a yield point), `'BEYOND_PLATEAU_UNIFORM_YIELD'`. Also return the diameter
  window `[t/(eps_y+eps_L), t/onset]`.
- `luders_susceptibility(alloy, temper, magnesium_wt_pct=None, grain_size_m=None)`:
  rule-based: susceptible only if 5xxx (or Mg >= ~2 wt%) **and** O temper (annealed);
  grain size < 40 µm strengthens (Choi, Jin & Kang 1998), 40–70 µm weakens; any H temper
  or >= ~1–2 % prior cold work/stretch → `'NOT_SUSCEPTIBLE_COLD_WORKED'` (Reynolds
  US 4,081,294; Li et al. 2020). Return status + reasons list.
- `pass_reduction_vs_luders(reduction_fraction, luders_strain)`: a rolling pass with
  thickness strain far above the Lüders strain (reduction > ~2 %) cannot leave Lüders
  bands in the bite; only skin passes/levelling/bending can.
- Thin-gauge implication to expose: bending strain `t/D` falls with gauge, so bending-type
  yield-point marks get *less* likely as gauge thins — the opposite trend to chatter.

### 2.5 Lubrication / friction screens
- `forward_slip_screen(forward_slip_fraction)`: `<= 0` → `'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT'`;
  `< 0.005` → `'MARGINAL_FORWARD_SLIP'` (analyst threshold, unverified); else `'NORMAL'`.
- `herringbone_screen(reduction_fraction, contact_length_m, observed_pitch_m=None)`:
  herringbone = periodic lubricant-film breakdown, pitch ≈ projected arc of contact
  (Komori 1996), typically at reduction >= ~0.40–0.45 on hard Al–Mg (Szűcs et al. 2020;
  Alcoa US 5,508,119 citing Schey). Return risk level from reduction and, if a pitch is
  observed, whether it is within a factor 0.5–2 of the contact length.
- `inlet_film_thickness_wilson_walowit(viscosity_pa_s, pressure_viscosity_coefficient_per_pa,
  roll_surface_speed_m_s, strip_entry_speed_m_s, inlet_angle_rad, plane_strain_yield_pa)`:
  `h_s = 3*eta0*alpha*(U_r + U_s) / (theta*(1 - exp(-alpha*Y_ps)))` (Wilson & Walowit 1972,
  smooth isothermal inlet film; quoted from memory — flag
  `FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE` in the result). `inlet_angle` ≈
  `sqrt((h0-h1)/R')`.
- `film_ratio_regime(film_thickness_m, roll_roughness_rq_m, strip_roughness_rq_m)`:
  `Lambda = h_s/sqrt(Rq_r^2+Rq_s^2)`; `< 1` boundary, `1–3` mixed, `> 3` hydrodynamic
  (Sutcliffe 2002). Film thickness rises with speed and viscosity → friction falls →
  (per section 1) chatter margin shrinks; very thick film → skidding/matte surface.

### 2.6 Coolant spray coverage (lengthwise bands)
- `flat_fan_footprint_width_m(standoff_m, spray_angle_rad)` = `2*s*tan(angle/2)`.
- `spray_coverage(barrel_length_m, nozzle_pitch_m, standoff_m, spray_angle_rad,
  offset_angle_rad=0.0, blocked_nozzle_indices=(), first_nozzle_position_m=None,
  resolution_m=0.002)`: nozzles along the header; footprint width along the header axis
  = `W*cos(offset_angle)` (fans are rotated ~5–15° about the nozzle axis so neighbours do
  not collide); count overlapping fans at each width position. Return nozzle count,
  footprint width, overlap fraction `(W_eff - pitch)/W_eff`, min/max coverage count, and a
  list of `stripes` `{start_m, end_m, coverage_count}` for zones with zero coverage and
  zones with lower coverage than the modal coverage (under-cooled stripes → local thermal
  crown, differential oil plate-out → lengthwise band at that width position; Lechler
  technical papers by Lloyd 2010 and Tucker 2006).
- `free_thermal_radius_growth_m(roll_radius_m, expansion_coefficient_per_k, excess_temperature_k)`
  = `alpha*R*dT` — an **upper bound** (free expansion, no axial heat conduction smoothing);
  `local_gap_closure_fraction = 2*dR/h_exit`. Expose that this fraction grows as gauge
  thins (a few µm of local roll growth is negligible on 2 mm strip and large on 100 µm).
- `match_band_positions(stripes, observed_positions_m, tolerance_m)`.

### 2.7 Tests `tests/test_band_signatures.py`
Pitch laws under speed doubling; exponent classification with exact synthetic data;
bearing identities; catalogue contains expected ids and consistent `pitch*frequency = u_x`;
resonance-speed round trip; bending window numbers for AA5182-O (sigma_y = 139 MPa,
E = 70 GPa, eps_L = 0.01, zero tension, t = 2 mm → window ≈ 167–1007 mm diameter; derive
exactly); susceptibility rules; slip and herringbone screens; film formula monotonic in
speed and viscosity + flag present; coverage: uniform header fully covered, a blocked
nozzle produces a stripe at the right position, footprint formula; JSON-serialisable
outputs; validation errors on bad inputs.

## 3. Diagnosis engine, report, CLI, docs (built after sections 1–2 exist)
See the task prompt of the integration agent.

## 4. Source list (cite in docstrings/docs where used; do not invent others)
- Tlusty, Chandra, Critchley, Paton (1982) "Chatter in Cold Rolling", CIRP Ann. 31:195,
  doi:10.1016/s0007-8506(07)63296-x (abstract only read).
- Yun, Wilson, Ehmann (1998) Int. J. Mach. Tools Manuf., doi:10.1016/s0890-6955(97)00133-8
  (cited, not read).
- Hu, Zhao, Ehmann (2006), Proc. IMechE B, doi:10.1243/09544054B06804 — as reproduced in
  Heidari & Forouzan (2013) J. Adv. Res., https://pmc.ncbi.nlm.nih.gov/articles/PMC4260885/
- Kimura, Sodani, Nishiura, Ikeuchi, Mihara (2003) ISIJ Int. 43:77 (5-DOF model, stability
  index, friction band).
- Niroomand, Forouzan, Salimi, Shojaei (2012) ISIJ Int. 52:2245,
  doi:10.2355/isijinternational.52.2245; (2015) ISIJ Int. 55:637 (lumped strip spring vs
  wave model; measured 124.6 Hz; critical speed 6.4–6.6 m/s model vs 5.81 measured).
- Zeng, Zang, Gao (2016) Shock & Vib., doi:10.1155/2016/2347386 (tension lowers critical
  speed; measured critical speeds 1059–1300 m/min).
- Innoval Technology (Farley): https://www.innovaltec.com/mill-vibration-blog/ ,
  https://www.innovaltec.com/strip-chatter-marks-blog/ (fifth octave: 600–1200 Hz,
  10–40 mm pitch, both work rolls in phase between backup rolls),
  https://www.innovaltec.com/chatter-cold-rolling-mill-blog/ (aluminium case: 315 Hz at
  470 m/min = 2×BPFI of a work-roll bearing, 20–25 mm pitch, ~0.6 µm chock displacement,
  speed-independent pitch).
- Krüger, Richard, Peretic (SMS group) AISTech 2019 "Chatter Management at Cold Rolling
  Mills Today" (order analysis, mark distance = backup-roll circumference / order).
- Kim, Kim, Park et al. (2012) ISIJ Int. 52:2042, doi:10.2355/isijinternational.52.2042
  (f = v/p).
- Randall & Antoni (2011) MSSP, doi:10.1016/j.ymssp.2010.07.017 (bearing frequencies).
- Zhang et al. (2016) IET J. Eng., doi:10.1049/joe.2016.0182 (aluminium single-stand
  4-high: WR 370–400 mm, BUR 1110–1150 mm, max 1500 m/min, 16 MN).
- Heidari, Forouzan, Akbarzadeh (2014) ISIJ Int. 54:2349 (lumped values M_w = 14 t,
  M_b = 38 t, K_w = 4.97e10, K_b = 1.22e10 N/m — steel mill).
- Aluminum Association (2002) *Visual Quality Characteristics of Aluminum Sheet and Plate*
  QCA-1, 4th ed. (Lüders lines Type A/B, herringbone streak, heat streak, roll skid mark…).
- Choi, Jin, Kang (1998) Scripta Mater. 38(6):887 (Type A Lüders below ~40 µm grain size).
- de Codes, Hopperstad, Engler, Lademo, Embury, Benallal (2011) Metall. Mater. Trans. A 42,
  doi:10.1007/s11661-011-0749-1 (5182-O band strain ~0.01).
- Reynolds US 4,081,294 (1978) (>= 2 % cold reduction suppresses Type A; 5182-O yield
  ~139 MPa); Li et al. (2020) (1 % pre-stretch removes the plateau).
- Mucsi (2018) Eng. Fail. Anal. 83, doi:10.1016/j.engfailanal.2017.09.022 (coil breaks).
- Komori (1996) J. Mater. Process. Technol. 60:377, doi:10.1016/0924-0136(96)02357-6
  (herringbone pitch = arc of contact, periodic film failure).
- Szűcs et al. (2020) Mater. Sci. Eng. (Miskolc) 45(1):284 (herringbone onset ~40–45 %
  reduction on 5754-O); Alcoa US 5,508,119 (1996) citing Schey (1983).
- Reid & Schey (1978) ASLE Trans. 21(3), doi:10.1080/05698197808982874 (full-film
  lubrication, negative forward slip, matte surface).
- Sutcliffe (2002) in Lenard (ed.) *Metal Forming Science and Practice*,
  doi:10.1016/b978-008044024-8/50004-7 (film ratio regimes).
- Lloyd (Lechler, 2010) "Fundamentals of roll cooling and control of flatness at primary
  cold reduction"; Tucker (Lechler, 2006) "Flatness and profile … spray actuators".
Known disagreements to state honestly: effect of friction on chatter (Yarita: high
friction; Chefneux: low friction; Kimura: an optimum band); effect of tension (Heidari:
little; Zeng: higher tension lowers critical speed); lumped-spring span is inaccurate near
the span's axial wave resonance (`c/(2L)`, c = sqrt(E/rho) ≈ 5.1 km/s → ~640 Hz for 4 m).
