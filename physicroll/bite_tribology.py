"""Roll-bite tribology, pass heating and work hardening for synthetic aluminium cold rolling.

Opt-in, standard-library-only process-model helpers. SI units everywhere, every result is a
plain JSON-serialisable dict with ``status``, ``flags``, ``limitations``, ``basis`` and
``sources``. Nothing here is plant-validated. Independent of ``physicroll.chatter``; any
coupling loop (friction -> bite response -> chatter) belongs to an integration layer.

Basis tags (carried into every result's ``basis`` dict):
``[V]`` read in a cited source, ``[D]`` derived by the planner/analyst, ``[M]`` from memory,
unverified. Anything resting on [D] or [M] says so.

Viscosity (W3.1)
----------------
``eta0(T) = eta_ref*exp(-beta*(T - T_ref))`` (exponential temperature law) and Barus
``eta(T, p) = eta0(T)*exp(alpha*p)``. Kerosene-based aluminium rolling oils: base oil
0.75-4.25 cSt at 40 C (commercial 1.9-2.4); 3.0 / 1.4 / 0.7 cSt at 20 / 70 / 130 C
[V: US 4,844,830; Petroyag data sheet] -> beta ~ 0.015 /K (20-70 C), ~ 0.012 /K (70-130 C)
[D from those points]. Foil-rolling oil eta0 = 2.5e-3 Pa s, alpha = 1.2e-8 /Pa
[V: Sutcliffe & Montmitonnet 2001, Rev. Metall. 435]. Kerosene density ~ 800 kg/m3 [M].

Inlet film thickness (W3.2; Wilson & Walowit 1972 as restated by Sutcliffe 2002 and Le &
Sutcliffe 2000/2001 [V], original not read)
--------------------------------------------------------------------------------------------
``h_s = 6*eta0*alpha*U_mean / (theta0*(1 - exp(-alpha*(Y_ps - sigma_back))))``,
``U_mean = (u_roll + u_strip_entry)/2``, ``theta0 = sqrt((h_entry - h_exit)/R_contact)``
[D for the arc], ``Y_ps = 2*Y/sqrt(3)``. The exponent uses the bite-entry pressure
``Y_ps - sigma_back`` [D: yield condition p + sigma = Y_ps]; Sutcliffe / Le write Y_ps alone,
Yarita (1984) writes the entry pressure -- the disagreement is recorded, and the Y_ps-only
value is reported alongside. Optional thermal thinning ``phi_T = 3.94/(3.94 + L^0.62)``,
``L = eta0*beta*U_mean^2/k_oil`` (thermal loading parameter [V: Ghosh & Hamrock 1985]; the
Murch & Wilson factor form is [M]); off by default, its value always reported.

Friction closure (W3.3) -- PLACEHOLDER, NOT FITTED
--------------------------------------------------
``Lambda = h_s/sqrt(Rq_roll^2 + Rq_strip^2)``; first asperity contact below ~3, substantial
contact below ~1 [V: Sutcliffe 2002]; regimes BOUNDARY (< 1), MIXED (1-3), HYDRODYNAMIC (> 3).
Mixed-film ``mu = A*mu_c + (1-A)*mu_v`` with boundary mu_c ~ 0.1 [V]. On aluminium strip mu ~
0.09 at lowest speeds falling below 0.01 at highest speeds; Lambda and reduction dominate,
oil temperature 40-60 C secondary [V abstract: Tabary, Sutcliffe et al. 1996, J. Tribol.
118:629]. No closed-form A(Lambda) was read, so the default closure is an analyst placeholder
``mu(Lambda) = mu_v + (mu_b - mu_v)*exp(-Lambda/Lambda0)`` [D], defaults mu_b = 0.09 [V],
mu_v = 0.008 [D within 0.005-0.01], Lambda0 = 1.0 [D]. Le & Sutcliffe (2001) needed a
boundary friction that varies with film thickness and reduction to fit the same data.
Sign convention: ``dmu_dspeed_per_m_s < 0`` means friction falls as speed rises.

Pass heating (W3.4)
-------------------
``w_pl = (2/sqrt(3))*Y_mean*ln(h_entry/h_exit)`` [J/m3]; adiabatic rise ``w_pl/(rho*c)``,
``rho*c ~ 2.43e6 J/(m3 K)`` for aluminium [D]. Bite heat per unit width
``Q = w_pl*h_exit*u_exit + P_friction`` [W/m] (friction power from the caller's slab
solution, both interfaces). Strip keeps ``strip_heat_fraction`` (supplied; foil mills
0.11-0.33 to the foil [V abstract: Yin et al. 2003]; thicker strip keeps much more [M]); each
work roll receives ``(1 - strip_heat_fraction)/2``. Exit temperature
``T_exit = T_entry + f_s*Q/(rho*c*h_exit*u_exit)``. Strip reaches ~100 C per pass
[V: Achenbach basics]; set-up models cap exit/coiling temperature [V: ABB Review], no
numeric cap was found, so a limit is only checked when supplied.

Work hardening (W3.5)
---------------------
Equivalent strain ``eps = (2/sqrt(3))*ln(h_ref/h)`` (as ``physicroll.materials``). Laws:
``physicroll.materials.PowerHardeningLaw`` (``sigma = sigma_y + K*eps^n``, reused) and a
generalised Voce law with a stage-IV term [D form; Hirsch et al., Ryen et al. 2006 read
second-hand] ``sigma = s0 + (ss - s0)*(1 - exp(-eps/eps_c)) + theta4*eps`` with analytic mean
``s0 + (ss - s0)*(1 - eps_c*(exp(-a/eps_c) - exp(-b/eps_c))/(b - a)) + theta4*(a + b)/2``.
Strain-rate sensitivity is taken as zero (room-temperature m ~ 0.002-0.02 [M]).

NOT modelled: inlet starvation, surface roughness lay / asperity flattening, micro-
plasto-hydrodynamic lubrication, film collapse through the bite, shear heating beyond the
optional inlet factor, additive chemistry, plate-out, temperature dependence of flow stress,
recovery/ageing between passes, through-thickness temperature gradients, roll/coolant heat
transfer (see the roll thermal model), any coupling loop to the chatter model.
"""
from dataclasses import asdict, dataclass
import json
import math

from .materials import PowerHardeningLaw

STATUS_FILM = 'UNVALIDATED_INLET_FILM_ESTIMATE'
STATUS_FRICTION = 'UNVALIDATED_PLACEHOLDER_FRICTION_CLOSURE'
STATUS_HEATING = 'UNVALIDATED_PASS_HEATING_ESTIMATE'
STATUS_HARDENING = 'UNVALIDATED_UNCALIBRATED_HARDENING_SCHEDULE'

PLACEHOLDER_FLAG = 'PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED'
ENTRY_PRESSURE_FLAG = 'EXPONENT_USES_ENTRY_PRESSURE_SOURCES_DISAGREE'

# Defaults and context values, each with its basis tag.
KEROSENE_DENSITY_KG_M3 = 800.0                       # [M]
DEFAULT_OIL_CONDUCTIVITY_W_MK = 0.13                 # [M] typical light mineral oil
FOIL_OIL_VISCOSITY_PA_S = 2.5e-3                     # [V] Sutcliffe & Montmitonnet 2001
FOIL_OIL_PRESSURE_VISCOSITY_PER_PA = 1.2e-8          # [V] Sutcliffe & Montmitonnet 2001
KEROSENE_BETA_20_70C_PER_K = 0.015                   # [D] from 3.0/1.4 cSt at 20/70 C
KEROSENE_BETA_70_130C_PER_K = 0.012                  # [D] from 1.4/0.7 cSt at 70/130 C
ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K = 2.43e6    # [D] rho*c
REGIME_BOUNDARY_BELOW = 1.0                          # [V] Sutcliffe 2002
REGIME_HYDRODYNAMIC_ABOVE = 3.0                      # [V] Sutcliffe 2002
TYPICAL_PASS_EXIT_TEMPERATURE_K = 373.15             # [V] Achenbach basics, ~100 C per pass
VISCOSITY_EXTRAPOLATION_WARN_K = 60.0                # [D] analyst choice
SPEED_DERIVATIVE_RELATIVE_STEP = 1e-4                # [D] numerical choice
MAX_SPEED_M_S = 200.0                                # input sanity envelope (analyst choice)

SOURCES = {
    'us_4844830': 'US 4,844,830 (aluminium rolling oil base-oil viscosity range)',
    'petroyag': 'Petroyag rolling-oil data sheet (3.0/1.4/0.7 cSt at 20/70/130 C)',
    'sutcliffe_montmitonnet_2001': 'Sutcliffe & Montmitonnet (2001) Rev. Metall. 435 '
                                   '(foil oil eta0 = 2.5e-3 Pa s, alpha = 1.2e-8 /Pa)',
    'wilson_walowit_1972': 'Wilson & Walowit (1972) inlet film formula, as restated by '
                           'Sutcliffe (2002) and Le & Sutcliffe (2000/2001); original not read',
    'sutcliffe_2002': 'Sutcliffe (2002) in Lenard (ed.) Metal Forming Science and Practice, '
                      'doi:10.1016/b978-008044024-8/50004-7 (film ratio regimes)',
    'le_sutcliffe_2001': 'Le & Sutcliffe (2000/2001) mixed lubrication in strip rolling '
                         '(boundary friction varying with film thickness and reduction)',
    'yarita_1984': 'Yarita (1984) (inlet exponent written with the entry pressure)',
    'ghosh_hamrock_1985': 'Ghosh & Hamrock (1985) (thermal loading parameter L)',
    'murch_wilson': 'Murch & Wilson thermal reduction factor form (quoted from memory)',
    'tabary_1996': 'Tabary, Sutcliffe et al. (1996) J. Tribol. 118:629 (abstract: aluminium '
                   'strip friction ~0.09 at low speed to < 0.01 at high speed)',
    'yin_2003': 'Yin et al. (2003) (abstract: 0.11-0.33 of bite heat to foil)',
    'achenbach': 'Achenbach, rolling basics (strip reaches ~100 C per pass)',
    'abb_review': 'ABB Review (set-up models limit exit/coiling temperature)',
    'kazaoka_2015': 'Kazaoka et al. (2015) (tensile Hollomon fits over-predict beyond '
                    'eps ~ 0.3)',
    'kalpakjian': 'Kalpakjian, strength coefficient / exponent table (via secondary source)',
    'batorfi_2023': 'Batorfi et al. (2023) (1050 annealed Ludwik fit)',
    'hirsch': 'Hirsch et al. (Voce-type saturation of cold-rolled yield; second-hand)',
    'ryen_2006': 'Ryen et al. (2006) (nearly constant low stage-IV hardening; abstract)',
}

HOLLOMON_WARNING = ('Tensile-fitted power laws over-predict beyond eps ~ 0.3 '
                    '[V: Kazaoka et al. 2015] and are not calibrated for rolling.')

LITERATURE_FITS = {
    '1100-O_kalpakjian': {
        'alloy': '1100', 'temper': 'O', 'law': 'hollomon', 'yield_stress_pa': 0.0,
        'strength_coefficient_pa': 180e6, 'exponent': 0.20, 'tag': 'V',
        'source': SOURCES['kalpakjian'], 'warning': HOLLOMON_WARNING},
    '5052-O_kalpakjian': {
        'alloy': '5052', 'temper': 'O', 'law': 'hollomon', 'yield_stress_pa': 0.0,
        'strength_coefficient_pa': 210e6, 'exponent': 0.13, 'tag': 'V',
        'source': SOURCES['kalpakjian'], 'warning': HOLLOMON_WARNING},
    '1050-annealed_batorfi': {
        'alloy': '1050', 'temper': 'annealed', 'law': 'ludwik', 'yield_stress_pa': 15.3e6,
        'strength_coefficient_pa': 144.6e6, 'exponent': 0.37, 'tag': 'V',
        'source': SOURCES['batorfi_2023'], 'warning': HOLLOMON_WARNING},
}


# --------------------------------------------------------------------------- helpers
def _num(name, value, *, positive=False, nonnegative=False, lo=None, hi=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite SI number (not bool)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{name} must be > 0')
    if nonnegative and value < 0:
        raise ValueError(f'{name} must be >= 0')
    if lo is not None and value < lo:
        raise ValueError(f'{name} must be >= {lo}')
    if hi is not None and value > hi:
        raise ValueError(f'{name} must be <= {hi}')
    return value


def _name(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


def _thickness_pair(entry_thickness_m, exit_thickness_m):
    h0 = _num('entry_thickness_m', entry_thickness_m, positive=True, hi=0.1)
    h1 = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.1)
    if h1 >= h0:
        raise ValueError('exit_thickness_m must be below entry_thickness_m')
    return h0, h1


def _temperature(name, value):
    return _num(name, value, lo=150.0, hi=1000.0)


# --------------------------------------------------------------------------- W3.1 viscosity
def kinematic_cst_to_dynamic_viscosity_pa_s(kinematic_viscosity_cst, density_kg_m3):
    """Dynamic viscosity [Pa s] = nu [cSt]*1e-6 [m2/s per cSt]*rho [kg/m3].

    The density is supplied; ``KEROSENE_DENSITY_KG_M3`` (800, [M]) is a typical value.
    """
    nu = _num('kinematic_viscosity_cst', kinematic_viscosity_cst, positive=True, hi=1e5)
    rho = _num('density_kg_m3', density_kg_m3, positive=True, hi=3000.0)
    return nu * 1e-6 * rho


def temperature_viscosity_coefficient_per_k(viscosity_1, temperature_1_k, viscosity_2,
                                            temperature_2_k):
    """``beta = ln(nu1/nu2)/(T2 - T1)`` from two viscosity points (any consistent unit)."""
    v1 = _num('viscosity_1', viscosity_1, positive=True)
    v2 = _num('viscosity_2', viscosity_2, positive=True)
    t1 = _temperature('temperature_1_k', temperature_1_k)
    t2 = _temperature('temperature_2_k', temperature_2_k)
    if t1 == t2:
        raise ValueError('temperatures must differ')
    return math.log(v1 / v2) / (t2 - t1)


@dataclass(frozen=True)
class Lubricant:
    """Rolling oil: exponential temperature law and Barus pressure law.

    ``viscosity_ref_pa_s`` is the dynamic viscosity at ``reference_temperature_k`` and zero
    gauge pressure. ``conductivity_w_mk`` is optional; when None the thermal loading
    parameter uses ``DEFAULT_OIL_CONDUCTIVITY_W_MK`` [M] and says so.
    """
    viscosity_ref_pa_s: float
    reference_temperature_k: float
    temperature_viscosity_coefficient_per_k: float
    pressure_viscosity_coefficient_per_pa: float
    conductivity_w_mk: float | None = None
    name: str = 'rolling oil'

    def validate(self):
        _num('viscosity_ref_pa_s', self.viscosity_ref_pa_s, positive=True, hi=10.0)
        _temperature('reference_temperature_k', self.reference_temperature_k)
        _num('temperature_viscosity_coefficient_per_k',
             self.temperature_viscosity_coefficient_per_k, nonnegative=True, hi=0.2)
        _num('pressure_viscosity_coefficient_per_pa', self.pressure_viscosity_coefficient_per_pa,
             positive=True, hi=1e-7)
        if self.conductivity_w_mk is not None:
            _num('conductivity_w_mk', self.conductivity_w_mk, positive=True, hi=10.0)
        _name('name', self.name)

    def dynamic_viscosity_pa_s(self, temperature_k, pressure_pa=0.0):
        """``eta = eta_ref*exp(-beta*(T - T_ref))*exp(alpha*p)``."""
        self.validate()
        t = _temperature('temperature_k', temperature_k)
        p = _num('pressure_pa', pressure_pa, nonnegative=True, hi=3e9)
        exponent = (-self.temperature_viscosity_coefficient_per_k
                    * (t - self.reference_temperature_k)
                    + self.pressure_viscosity_coefficient_per_pa * p)
        if exponent > 700:
            raise ValueError('viscosity exceeds numerical domain')
        return self.viscosity_ref_pa_s * math.exp(exponent)

    def effective_conductivity_w_mk(self):
        return (DEFAULT_OIL_CONDUCTIVITY_W_MK if self.conductivity_w_mk is None
                else float(self.conductivity_w_mk))


@dataclass(frozen=True)
class SurfaceFinish:
    roll_roughness_rq_m: float
    strip_roughness_rq_m: float

    def validate(self):
        rr = _num('roll_roughness_rq_m', self.roll_roughness_rq_m, nonnegative=True, hi=1e-4)
        rs = _num('strip_roughness_rq_m', self.strip_roughness_rq_m, nonnegative=True, hi=1e-4)
        if math.hypot(rr, rs) <= 0:
            raise ValueError('composite roughness must be > 0')

    def composite_rq_m(self):
        self.validate()
        return math.hypot(self.roll_roughness_rq_m, self.strip_roughness_rq_m)


@dataclass(frozen=True)
class FrictionClosure:
    """Placeholder ``mu = mu_v + (mu_b - mu_v)*exp(-Lambda/lambda0)`` [D], not fitted."""
    mu_b: float = 0.09     # [V] Tabary et al. 1996 low-speed (boundary additive) value
    mu_v: float = 0.008    # [D] within 0.005-0.01
    lambda0: float = 1.0   # [D]

    def validate(self):
        mu_b = _num('mu_b', self.mu_b, positive=True, hi=1.0)
        mu_v = _num('mu_v', self.mu_v, nonnegative=True, hi=1.0)
        _num('lambda0', self.lambda0, positive=True, hi=100.0)
        if mu_v > mu_b:
            raise ValueError('mu_v must not exceed mu_b')

    def basis(self):
        default = FrictionClosure()
        return {
            'mu_b': '[V] Tabary et al. 1996 abstract' if self.mu_b == default.mu_b
                    else 'supplied by caller',
            'mu_v': '[D] analyst choice within 0.005-0.01' if self.mu_v == default.mu_v
                    else 'supplied by caller',
            'lambda0': '[D] analyst placeholder' if self.lambda0 == default.lambda0
                       else 'supplied by caller',
            'closure_form': '[D] analyst placeholder exp(-Lambda/lambda0); not fitted'}


def _regime(film_ratio):
    if film_ratio < REGIME_BOUNDARY_BELOW:
        return 'BOUNDARY'
    if film_ratio <= REGIME_HYDRODYNAMIC_ABOVE:
        return 'MIXED'
    return 'HYDRODYNAMIC'


# --------------------------------------------------------------------------- W3.2 film
def _film_core(lub, ur, us, h0, h1, rc, yps, sb, t_in, thermal):
    theta = math.sqrt((h0 - h1) / rc)
    u_mean = 0.5 * (ur + us)
    eta0 = lub.dynamic_viscosity_pa_s(t_in)
    alpha = lub.pressure_viscosity_coefficient_per_pa
    p_entry = yps - sb
    h_iso = 6 * eta0 * alpha * u_mean / (theta * -math.expm1(-alpha * p_entry))
    h_yonly = 6 * eta0 * alpha * u_mean / (theta * -math.expm1(-alpha * yps))
    k = lub.effective_conductivity_w_mk()
    load = eta0 * lub.temperature_viscosity_coefficient_per_k * u_mean ** 2 / k
    phi = 3.94 / (3.94 + load ** 0.62)
    h = h_iso * phi if thermal else h_iso
    return {'theta': theta, 'u_mean': u_mean, 'eta0': eta0, 'p_entry': p_entry,
            'h_iso': h_iso, 'h_yonly': h_yonly, 'load': load, 'phi': phi, 'h': h, 'k': k}


def _film_inputs(lubricant, roll_surface_speed_m_s, strip_entry_speed_m_s, entry_thickness_m,
                 exit_thickness_m, contact_radius_m, plane_strain_yield_pa, back_tension_pa,
                 inlet_temperature_k, thermal_correction):
    if not isinstance(lubricant, Lubricant):
        raise ValueError('lubricant must be a Lubricant')
    lubricant.validate()
    ur = _num('roll_surface_speed_m_s', roll_surface_speed_m_s, positive=True, hi=MAX_SPEED_M_S)
    us = _num('strip_entry_speed_m_s', strip_entry_speed_m_s, positive=True, hi=MAX_SPEED_M_S)
    h0, h1 = _thickness_pair(entry_thickness_m, exit_thickness_m)
    rc = _num('contact_radius_m', contact_radius_m, positive=True, hi=10.0)
    yps = _num('plane_strain_yield_pa', plane_strain_yield_pa, positive=True, hi=5e9)
    sb = _num('back_tension_pa', back_tension_pa, nonnegative=True, hi=5e9)
    if sb >= yps:
        raise ValueError('back_tension_pa must be below plane_strain_yield_pa '
                         '(entry pressure must be positive)')
    t_in = _temperature('inlet_temperature_k', inlet_temperature_k)
    if not isinstance(thermal_correction, bool):
        raise ValueError('thermal_correction must be a bool')
    return lubricant, ur, us, h0, h1, rc, yps, sb, t_in, thermal_correction


def inlet_film_thickness(lubricant, *, roll_surface_speed_m_s, strip_entry_speed_m_s,
                         entry_thickness_m, exit_thickness_m, contact_radius_m,
                         plane_strain_yield_pa, back_tension_pa, inlet_temperature_k,
                         thermal_correction=False):
    """Smooth-surface inlet film thickness (Wilson & Walowit form, entry-pressure exponent).

    ``contact_radius_m`` is the (possibly flattened) roll radius used for the inlet angle.
    """
    args = _film_inputs(lubricant, roll_surface_speed_m_s, strip_entry_speed_m_s,
                        entry_thickness_m, exit_thickness_m, contact_radius_m,
                        plane_strain_yield_pa, back_tension_pa, inlet_temperature_k,
                        thermal_correction)
    lub, ur, us, h0, h1, rc, yps, sb, t_in, thermal = args
    c = _film_core(*args)
    flags = [ENTRY_PRESSURE_FLAG, 'SMOOTH_ISOTHERMAL_INLET_ASSUMED' if not thermal
             else 'THERMAL_REDUCTION_FACTOR_APPLIED']
    if lub.conductivity_w_mk is None:
        flags.append('OIL_CONDUCTIVITY_DEFAULT_FROM_MEMORY')
    if abs(t_in - lub.reference_temperature_k) > VISCOSITY_EXTRAPOLATION_WARN_K:
        flags.append('VISCOSITY_TEMPERATURE_EXTRAPOLATED_OVER_60K')
    if us > ur:
        flags.append('STRIP_ENTRY_FASTER_THAN_ROLL')
    reasons = [f'Inlet film {c["h"] * 1e9:.1f} nm at mean entrainment speed '
               f'{c["u_mean"]:.3f} m/s; film rises linearly with speed and inlet viscosity.']
    if not thermal:
        reasons.append(f'Thermal reduction factor {c["phi"]:.4f} computed but not applied.')
    return _checked({
        'status': STATUS_FILM,
        'film_thickness_m': c['h'],
        'isothermal_film_thickness_m': c['h_iso'],
        'film_thickness_yield_only_exponent_m': c['h_yonly'],
        'thermal_correction_applied': thermal,
        'thermal_reduction_factor': c['phi'],
        'thermal_loading_parameter': c['load'],
        'oil_conductivity_w_mk': c['k'],
        'inlet_viscosity_pa_s': c['eta0'],
        'pressure_viscosity_coefficient_per_pa': lub.pressure_viscosity_coefficient_per_pa,
        'mean_entrainment_speed_m_s': c['u_mean'],
        'roll_surface_speed_m_s': ur, 'strip_entry_speed_m_s': us,
        'inlet_angle_rad': c['theta'],
        'entry_pressure_pa': c['p_entry'],
        'alpha_times_entry_pressure': lub.pressure_viscosity_coefficient_per_pa * c['p_entry'],
        'plane_strain_yield_pa': yps, 'back_tension_pa': sb,
        'inlet_temperature_k': t_in,
        'formula': 'h_s = 6*eta0*alpha*U_mean/(theta0*(1-exp(-alpha*(Y_ps-sigma_back)))); '
                   'phi_T = 3.94/(3.94+L^0.62), L = eta0*beta*U_mean^2/k_oil',
        'basis': {
            'film_formula': '[V] Wilson & Walowit 1972 as restated by Sutcliffe 2002 / Le & '
                            'Sutcliffe; original not read',
            'inlet_angle': '[D] theta0 = sqrt((h_entry-h_exit)/R_contact)',
            'entry_pressure_exponent': '[D] Y_ps - sigma_back; Sutcliffe/Le write Y_ps alone, '
                                       'Yarita 1984 the entry pressure (sources disagree)',
            'thermal_loading_parameter': '[V] Ghosh & Hamrock 1985',
            'thermal_factor_form': '[M] Murch & Wilson form, quoted from memory',
            'oil_conductivity': ('[M] default 0.13 W/mK' if lub.conductivity_w_mk is None
                                 else 'supplied by caller'),
            'viscosity_law': '[D] exponential temperature law with Barus pressure law'},
        'reasons': reasons, 'flags': flags,
        'limitations': [
            'Smooth surfaces, Newtonian Barus oil, fully flooded inlet (no starvation).',
            'Inlet shear heating is represented only by the optional factor phi_T.',
            'The entry-pressure exponent differs from Sutcliffe/Le (Y_ps alone); both values '
            'are reported.',
            'Not plant-validated; for sensitivity studies only.'],
        'sources': [SOURCES['wilson_walowit_1972'], SOURCES['sutcliffe_2002'],
                    SOURCES['le_sutcliffe_2001'], SOURCES['yarita_1984'],
                    SOURCES['ghosh_hamrock_1985'], SOURCES['murch_wilson']]})


# --------------------------------------------------------------------------- W3.3 friction
def _mu(lam, closure):
    return closure.mu_v + (closure.mu_b - closure.mu_v) * math.exp(-lam / closure.lambda0)


def friction_coefficient(film_ratio, closure=None):
    """Placeholder closure ``mu(Lambda)`` and its slope ``dmu/dLambda`` (always <= 0)."""
    closure = FrictionClosure() if closure is None else closure
    if not isinstance(closure, FrictionClosure):
        raise ValueError('closure must be a FrictionClosure')
    closure.validate()
    lam = _num('film_ratio', film_ratio, nonnegative=True, hi=1e6)
    mu = _mu(lam, closure)
    slope = -(closure.mu_b - closure.mu_v) / closure.lambda0 * math.exp(-lam / closure.lambda0)
    regime = _regime(lam)
    return _checked({
        'status': STATUS_FRICTION, 'friction_coefficient': mu,
        'dmu_dlambda': slope, 'film_ratio': lam, 'regime': regime,
        'closure': asdict(closure),
        'formula': 'mu = mu_v + (mu_b - mu_v)*exp(-Lambda/lambda0)',
        'regime_boundaries': {'boundary_below': REGIME_BOUNDARY_BELOW,
                              'hydrodynamic_above': REGIME_HYDRODYNAMIC_ABOVE},
        'basis': dict(closure.basis(), regime_boundaries='[V] Sutcliffe 2002'),
        'reasons': [f'Film ratio {lam:.3f} ({regime.lower()}): placeholder mu = {mu:.4f}.'],
        'flags': [PLACEHOLDER_FLAG],
        'limitations': [
            'The closure is an analyst placeholder, not fitted to any data.',
            'Le & Sutcliffe (2001) needed a boundary friction that varies with film thickness '
            'and reduction to fit the same aluminium data; a single mu_b cannot.',
            'Regime boundaries are conventional; transitions are gradual.'],
        'sources': [SOURCES['sutcliffe_2002'], SOURCES['tabary_1996'],
                    SOURCES['le_sutcliffe_2001']]})


def friction_at_speed(lubricant, finish, closure, *, roll_surface_speed_m_s,
                      strip_entry_speed_m_s, entry_thickness_m, exit_thickness_m,
                      contact_radius_m, plane_strain_yield_pa, back_tension_pa,
                      inlet_temperature_k, thermal_correction=False):
    """Oil + speed + temperature -> film -> Lambda -> placeholder friction, with speed slope.

    ``dmu_dspeed_per_m_s`` is the central finite difference of mu with respect to the roll
    surface speed, the strip entry speed scaled in proportion (fixed slip); negative means
    friction falls as speed rises.
    """
    if not isinstance(finish, SurfaceFinish):
        raise ValueError('finish must be a SurfaceFinish')
    closure = FrictionClosure() if closure is None else closure
    if not isinstance(closure, FrictionClosure):
        raise ValueError('closure must be a FrictionClosure')
    closure.validate()
    rq = finish.composite_rq_m()
    film = inlet_film_thickness(
        lubricant, roll_surface_speed_m_s=roll_surface_speed_m_s,
        strip_entry_speed_m_s=strip_entry_speed_m_s, entry_thickness_m=entry_thickness_m,
        exit_thickness_m=exit_thickness_m, contact_radius_m=contact_radius_m,
        plane_strain_yield_pa=plane_strain_yield_pa, back_tension_pa=back_tension_pa,
        inlet_temperature_k=inlet_temperature_k, thermal_correction=thermal_correction)
    args = list(_film_inputs(lubricant, roll_surface_speed_m_s, strip_entry_speed_m_s,
                             entry_thickness_m, exit_thickness_m, contact_radius_m,
                             plane_strain_yield_pa, back_tension_pa, inlet_temperature_k,
                             thermal_correction))
    lam = film['film_thickness_m'] / rq
    fric = friction_coefficient(lam, closure)
    step = SPEED_DERIVATIVE_RELATIVE_STEP
    mus = []
    for sign in (1, -1):
        scaled = list(args)
        scaled[1] = args[1] * (1 + sign * step)
        scaled[2] = args[2] * (1 + sign * step)
        mus.append(_mu(_film_core(*scaled)['h'] / rq, closure))
    dmu_dspeed = (mus[0] - mus[1]) / (2 * step * args[1])
    regime = fric['regime']
    flags = [PLACEHOLDER_FLAG] + [f for f in film['flags'] if f not in (PLACEHOLDER_FLAG,)]
    if regime == 'HYDRODYNAMIC':
        flags.append('THICK_FILM_SKIDDING_MATTE_RISK')
    reasons = film['reasons'] + fric['reasons'] + [
        f'Speed slope dmu/dV_roll = {dmu_dspeed:.3e} s/m (negative: friction falls as speed '
        f'rises; lower friction shrinks the chatter margin).']
    basis = dict(film['basis'])
    basis.update({f'closure_{k}': v for k, v in fric['basis'].items()})
    basis['speed_derivative'] = '[D] central difference, relative step 1e-4, fixed slip'
    return _checked({
        'status': STATUS_FRICTION,
        'film_thickness_m': film['film_thickness_m'],
        'isothermal_film_thickness_m': film['isothermal_film_thickness_m'],
        'film_thickness_yield_only_exponent_m': film['film_thickness_yield_only_exponent_m'],
        'thermal_correction_applied': film['thermal_correction_applied'],
        'thermal_reduction_factor': film['thermal_reduction_factor'],
        'thermal_loading_parameter': film['thermal_loading_parameter'],
        'inlet_viscosity_pa_s': film['inlet_viscosity_pa_s'],
        'mean_entrainment_speed_m_s': film['mean_entrainment_speed_m_s'],
        'roll_surface_speed_m_s': film['roll_surface_speed_m_s'],
        'strip_entry_speed_m_s': film['strip_entry_speed_m_s'],
        'inlet_angle_rad': film['inlet_angle_rad'],
        'entry_pressure_pa': film['entry_pressure_pa'],
        'inlet_temperature_k': film['inlet_temperature_k'],
        'composite_roughness_rq_m': rq,
        'film_ratio': lam, 'regime': regime,
        'friction_coefficient': fric['friction_coefficient'],
        'dmu_dlambda': fric['dmu_dlambda'],
        'dmu_dspeed_per_m_s': dmu_dspeed,
        'closure': fric['closure'],
        'regime_boundaries': fric['regime_boundaries'],
        'basis': basis, 'reasons': reasons, 'flags': flags,
        'limitations': film['limitations'] + fric['limitations'] + [
            'Rq-based film ratio ignores roughness lay and asperity flattening in the bite.'],
        'sources': film['sources'] + [s for s in fric['sources'] if s not in film['sources']]})


def friction_speed_curve(lubricant, finish, closure, *, exit_speeds_m_s, entry_thickness_m,
                         exit_thickness_m, contact_radius_m, plane_strain_yield_pa,
                         back_tension_pa, inlet_temperature_k, forward_slip_fraction=0.0,
                         thermal_correction=False):
    """Friction versus exit strip speed, for plots.

    For each exit speed ``u_x``: roll speed ``V_r = u_x/(1 + f)`` (forward slip ``f``), strip
    entry speed ``u_x*h_exit/h_entry`` (mass flow). Each point also carries
    ``dmu_dexit_speed_per_m_s = dmu_dspeed_per_m_s/(1 + f)``.
    """
    if isinstance(exit_speeds_m_s, (str, bytes)) or not hasattr(exit_speeds_m_s, '__iter__'):
        raise ValueError('exit_speeds_m_s must be a sequence of speeds')
    speeds = [_num('exit_speeds_m_s[i]', v, positive=True, hi=MAX_SPEED_M_S)
              for v in exit_speeds_m_s]
    if not speeds:
        raise ValueError('exit_speeds_m_s must not be empty')
    f = _num('forward_slip_fraction', forward_slip_fraction, lo=-0.4, hi=0.4)
    h0, h1 = _thickness_pair(entry_thickness_m, exit_thickness_m)
    points, flags = [], [PLACEHOLDER_FLAG]
    last = None
    for ux in speeds:
        r = friction_at_speed(
            lubricant, finish, closure, roll_surface_speed_m_s=ux / (1 + f),
            strip_entry_speed_m_s=ux * h1 / h0, entry_thickness_m=h0, exit_thickness_m=h1,
            contact_radius_m=contact_radius_m, plane_strain_yield_pa=plane_strain_yield_pa,
            back_tension_pa=back_tension_pa, inlet_temperature_k=inlet_temperature_k,
            thermal_correction=thermal_correction)
        for fl in r['flags']:
            if fl not in flags:
                flags.append(fl)
        last = r
        points.append({
            'exit_speed_m_s': ux, 'roll_surface_speed_m_s': r['roll_surface_speed_m_s'],
            'strip_entry_speed_m_s': r['strip_entry_speed_m_s'],
            'film_thickness_m': r['film_thickness_m'], 'film_ratio': r['film_ratio'],
            'regime': r['regime'], 'friction_coefficient': r['friction_coefficient'],
            'dmu_dspeed_per_m_s': r['dmu_dspeed_per_m_s'],
            'dmu_dexit_speed_per_m_s': r['dmu_dspeed_per_m_s'] / (1 + f),
            'thermal_reduction_factor': r['thermal_reduction_factor']})
    basis = dict(last['basis'])
    basis['speed_mapping'] = '[D] mass flow with supplied forward slip'
    return _checked({
        'status': STATUS_FRICTION, 'points': points,
        'forward_slip_fraction': f, 'thermal_correction_applied': thermal_correction,
        'composite_roughness_rq_m': last['composite_roughness_rq_m'],
        'closure': last['closure'], 'basis': basis,
        'reasons': ['Friction falls monotonically with speed as the inlet film thickens.'],
        'flags': flags, 'limitations': last['limitations'], 'sources': last['sources']})


# --------------------------------------------------------------------------- W3.4 heating
def pass_heating(*, entry_thickness_m, exit_thickness_m, exit_speed_m_s, mean_flow_stress_pa,
                 strip_heat_fraction, entry_temperature_k, friction_power_per_width_w_m=0.0,
                 volumetric_heat_capacity_j_m3k=ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K,
                 temperature_limit_k=None):
    """Plastic + friction bite heat per unit width and its strip / work-roll partition.

    ``mean_flow_stress_pa`` is the mean UNIAXIAL flow stress over the pass;
    ``friction_power_per_width_w_m`` is the total over both interfaces (caller's slab model).
    """
    h0, h1 = _thickness_pair(entry_thickness_m, exit_thickness_m)
    ux = _num('exit_speed_m_s', exit_speed_m_s, positive=True, hi=MAX_SPEED_M_S)
    y = _num('mean_flow_stress_pa', mean_flow_stress_pa, positive=True, hi=5e9)
    fs = _num('strip_heat_fraction', strip_heat_fraction, lo=0.0, hi=1.0)
    t_in = _temperature('entry_temperature_k', entry_temperature_k)
    p_f = _num('friction_power_per_width_w_m', friction_power_per_width_w_m,
               nonnegative=True, hi=1e9)
    rho_c = _num('volumetric_heat_capacity_j_m3k', volumetric_heat_capacity_j_m3k,
                 positive=True, hi=1e8)
    limit = None if temperature_limit_k is None else _temperature('temperature_limit_k',
                                                                  temperature_limit_k)
    w_pl = 2 / math.sqrt(3) * y * math.log(h0 / h1)
    flow = h1 * ux
    p_pl = w_pl * flow
    total = p_pl + p_f
    to_strip = fs * total
    per_roll = (1 - fs) / 2
    to_roll = per_roll * total
    dt_strip = to_strip / (rho_c * flow)
    t_out = t_in + dt_strip
    flags = ['STRIP_HEAT_FRACTION_SUPPLIED_NOT_COMPUTED']
    if p_f == 0:
        flags.append('FRICTION_POWER_NOT_SUPPLIED')
    if limit is not None and t_out > limit:
        flags.append('EXIT_TEMPERATURE_ABOVE_SUPPLIED_LIMIT')
    if t_out > TYPICAL_PASS_EXIT_TEMPERATURE_K:
        flags.append('EXIT_TEMPERATURE_ABOVE_TYPICAL_100C')
    reasons = [f'Plastic work {w_pl / 1e6:.2f} MJ/m3 (adiabatic rise '
               f'{w_pl / rho_c:.1f} K); bite heat {total / 1e3:.2f} kW/m, strip keeps '
               f'{fs:.2f} -> exit {t_out - 273.15:.1f} C.']
    return _checked({
        'status': STATUS_HEATING,
        'plastic_work_per_volume_j_m3': w_pl,
        'plane_strain_mean_flow_stress_pa': 2 / math.sqrt(3) * y,
        'adiabatic_plastic_temperature_rise_k': w_pl / rho_c,
        'volume_flow_per_width_m2_s': flow,
        'plastic_power_per_width_w_m': p_pl,
        'friction_power_per_width_w_m': p_f,
        'bite_heat_per_width_w_m': total,
        'strip_heat_fraction': fs,
        'roll_heat_fraction_per_roll': per_roll,
        'strip_heat_per_width_w_m': to_strip,
        'heat_to_each_work_roll_per_width_w_m': to_roll,
        'strip_temperature_rise_k': dt_strip,
        'entry_temperature_k': t_in, 'exit_temperature_k': t_out,
        'temperature_limit_k': limit,
        'volumetric_heat_capacity_j_m3k': rho_c,
        'formula': 'w_pl = (2/sqrt(3))*Y_mean*ln(h_entry/h_exit); Q = w_pl*h_exit*u_exit + '
                   'P_friction; T_exit = T_entry + f_s*Q/(rho*c*h_exit*u_exit)',
        'basis': {
            'plastic_work': '[D] homogeneous plane-strain work, no redundant shear',
            'volumetric_heat_capacity': ('[D] 2.43e6 J/m3K for aluminium'
                                         if rho_c == ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K
                                         else 'supplied by caller'),
            'strip_heat_fraction': 'supplied by caller; foil mills 0.11-0.33 [V abstract: Yin '
                                   'et al. 2003], thicker strip keeps more [M]',
            'roll_split': '[D] equal split between the two work rolls',
            'typical_exit_temperature': '[V] Achenbach basics, ~100 C per pass',
            'temperature_limit': ('supplied by caller; no numeric cap found [V: ABB Review]'
                                  if limit is not None else 'none supplied; no numeric cap '
                                  'found [V: ABB Review]')},
        'reasons': reasons, 'flags': flags,
        'limitations': [
            'Partition fraction is an input, not solved from contact conductance.',
            'Strip temperature is a through-thickness mean; no conduction, coolant or air '
            'loss between bite and coiler.',
            'Flow stress is not temperature dependent; no recovery.',
            'Not plant-validated.'],
        'sources': [SOURCES['yin_2003'], SOURCES['achenbach'], SOURCES['abb_review']]})


# --------------------------------------------------------------------------- W3.5 hardening
@dataclass(frozen=True)
class VoceHardening:
    """Generalised Voce with stage-IV slope; parameters are supplied, never defaulted.

    ``sigma = s0 + (ss - s0)*(1 - exp(-eps/eps_c)) + theta4*eps`` [D form].
    """
    initial_stress_pa: float
    saturation_stress_pa: float
    characteristic_strain: float
    stage_iv_slope_pa: float
    provenance: str

    def validate(self):
        s0 = _num('initial_stress_pa', self.initial_stress_pa, nonnegative=True, hi=5e9)
        ss = _num('saturation_stress_pa', self.saturation_stress_pa, positive=True, hi=5e9)
        _num('characteristic_strain', self.characteristic_strain, positive=True, hi=100.0)
        _num('stage_iv_slope_pa', self.stage_iv_slope_pa, nonnegative=True, hi=5e10)
        _name('provenance', self.provenance)
        if ss < s0:
            raise ValueError('saturation_stress_pa must be >= initial_stress_pa')

    def stress(self, equivalent_strain):
        self.validate()
        e = _num('equivalent_strain', equivalent_strain, nonnegative=True, hi=100.0)
        return (self.initial_stress_pa
                + (self.saturation_stress_pa - self.initial_stress_pa)
                * -math.expm1(-e / self.characteristic_strain)
                + self.stage_iv_slope_pa * e)

    def mean_stress(self, start, end):
        self.validate()
        a = _num('start', start, nonnegative=True, hi=100.0)
        b = _num('end', end, nonnegative=True, hi=100.0)
        if b < a:
            raise ValueError('invalid strain interval')
        if b == a:
            return self.stress(a)
        ec = self.characteristic_strain
        # mean of exp(-e/ec) over [a, b], written to avoid cancellation for short intervals
        mean_exp = math.exp(-a / ec) * -math.expm1(-(b - a) / ec) * ec / (b - a)
        return (self.initial_stress_pa
                + (self.saturation_stress_pa - self.initial_stress_pa) * (1 - mean_exp)
                + self.stage_iv_slope_pa * 0.5 * (a + b))


def literature_power_law(fit_id):
    """A ``PowerHardeningLaw`` from ``LITERATURE_FITS`` (tensile fits, not rolling-calibrated)."""
    if fit_id not in LITERATURE_FITS:
        raise ValueError(f'unknown fit_id; choose from {sorted(LITERATURE_FITS)}')
    fit = LITERATURE_FITS[fit_id]
    law = PowerHardeningLaw(
        alloy=fit['alloy'], temper=fit['temper'], yield_stress_pa=fit['yield_stress_pa'],
        strength_coefficient_pa=fit['strength_coefficient_pa'], exponent=fit['exponent'],
        provenance=f"[{fit['tag']}] {fit['source']}; {fit['warning']}")
    law.validate()
    return law


def schedule_flow_stress(gauges_m, law, *, prior_equivalent_strain=0.0):
    """Per-pass equivalent strain and flow stress along a gauge schedule.

    ``gauges_m = [h_0, h_1, ..., h_N]`` (strictly decreasing) defines N passes; strain is
    ``eps = prior + (2/sqrt(3))*ln(h_0/h)``. ``law`` is a ``PowerHardeningLaw`` or a
    ``VoceHardening``. Rate sensitivity is zero.
    """
    if not isinstance(law, (PowerHardeningLaw, VoceHardening)):
        raise ValueError('law must be a PowerHardeningLaw or VoceHardening')
    law.validate()
    if isinstance(gauges_m, (str, bytes)) or not hasattr(gauges_m, '__iter__'):
        raise ValueError('gauges_m must be a sequence of thicknesses')
    gauges = [_num(f'gauges_m[{i}]', h, positive=True, hi=0.1) for i, h in enumerate(gauges_m)]
    if len(gauges) < 2:
        raise ValueError('gauges_m needs at least an entry and one exit gauge')
    if any(b >= a for a, b in zip(gauges, gauges[1:])):
        raise ValueError('gauges_m must be strictly decreasing')
    prior = _num('prior_equivalent_strain', prior_equivalent_strain, nonnegative=True, hi=100.0)
    k = 2 / math.sqrt(3)
    passes = []
    for i, (h0, h1) in enumerate(zip(gauges, gauges[1:])):
        e0 = prior + k * math.log(gauges[0] / h0)
        e1 = prior + k * math.log(gauges[0] / h1)
        mean = law.mean_stress(e0, e1)
        passes.append({
            'pass_index': i, 'entry_thickness_m': h0, 'exit_thickness_m': h1,
            'reduction_fraction': 1 - h1 / h0,
            'entry_equivalent_strain': e0, 'exit_equivalent_strain': e1,
            'entry_flow_stress_pa': law.stress(e0), 'exit_flow_stress_pa': law.stress(e1),
            'mean_flow_stress_pa': mean, 'plane_strain_mean_flow_stress_pa': k * mean})
    is_power = isinstance(law, PowerHardeningLaw)
    flags = ['STRAIN_RATE_SENSITIVITY_IGNORED', 'UNCALIBRATED_FOR_ROLLING']
    final_strain = passes[-1]['exit_equivalent_strain']
    if is_power and final_strain > 0.3:
        flags.append('POWER_LAW_BEYOND_EPS_0P3_OVERPREDICTS')
    return _checked({
        'status': STATUS_HARDENING,
        'law_type': 'power_hardening' if is_power else 'voce_stage_iv',
        'law': asdict(law), 'prior_equivalent_strain': prior,
        'final_equivalent_strain': final_strain, 'passes': passes,
        'formula': 'eps = prior + (2/sqrt(3))*ln(h_0/h); mean = (1/(eps1-eps0))*int sigma deps',
        'basis': {
            'strain_convention': '[D] same as physicroll.materials (homogeneous plane strain)',
            'law': ('PowerHardeningLaw reused from physicroll.materials; provenance: '
                    + law.provenance if is_power else
                    '[D] generalised Voce form; parameters supplied: ' + law.provenance),
            'rate_sensitivity': '[M] taken as zero (room-temperature m ~ 0.002-0.02)'},
        'reasons': [f'{len(passes)} passes to equivalent strain {final_strain:.3f}.'],
        'flags': flags,
        'limitations': [
            HOLLOMON_WARNING,
            'No redundant shear, recovery, ageing or temperature dependence between passes.',
            'Voce coefficients are never defaulted; they must be supplied and sourced.'],
        'sources': [SOURCES['kazaoka_2015'], SOURCES['hirsch'], SOURCES['ryen_2006']]})
