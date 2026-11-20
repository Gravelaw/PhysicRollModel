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
[D for the arc], ``Y_ps = 2*Y/sqrt(3)``. ``R_contact`` (argument ``contact_radius_m``) is the
radius of the inlet angle: the integration layer (``band_process.film_radius_ratio``) passes the
deformed arc R' of a Hitchcock bite and the undeformed roll radius R of an experimental
mattress bite, whose ``contact_radius_ratio`` L^2/(R*draft) is not a radius [BT-S3 EX: the
undeformed-roll slope is used; D, re-derived in SPEC17]. The exponent uses the bite-entry pressure
``Y_ps - sigma_back`` [D: yield condition p + sigma = Y_ps]; Sutcliffe / Le write Y_ps alone,
Yarita (1984) writes the entry pressure -- the disagreement is recorded, and the Y_ps-only
value is reported alongside. Optional thermal thinning ``phi_T = 3.94/(3.94 + L^0.62)``,
``L = eta0*beta*U_mean^2/k_oil`` (thermal loading parameter [V: Ghosh & Hamrock 1985]; the
Murch & Wilson factor form is [M]); off by default, its value always reported.

Friction closure (W3.3) -- PLACEHOLDER, NOT FITTED
--------------------------------------------------
``Lambda = h_s/sqrt(Rq_roll^2 + Rq_strip^2)``; first asperity contact below ~3, substantial
contact below ~1 [V: Sutcliffe 2002]; labels MIXED_SUBSTANTIAL_CONTACT (< 1), MIXED_FIRST_CONTACT
(1-3), HYDRODYNAMIC (> 3) [BT-S9 EX]. Below about 1 is the condition for a good roll imprint
inside the mixed regime, and 0.01-0.5 is the common industrial window [BT-S3 EX, BT-S9 EX]; no
source read gives a film-ratio threshold for boundary lubrication, so none is labelled.
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
# [V] below about 1: substantial asperity contact, good roll imprint (BT-S9 EX)
REGIME_SUBSTANTIAL_CONTACT_BELOW = 1.0
REGIME_HYDRODYNAMIC_ABOVE = 3.0          # [V] first asperity contact below about 3 (BT-S9 EX)
COMMON_INDUSTRIAL_FILM_RATIO_WINDOW = (0.01, 0.5)   # [V] BT-S3 EX, BT-S9 EX
REGIME_BOUNDARIES = {'substantial_contact_below': REGIME_SUBSTANTIAL_CONTACT_BELOW,
                     'hydrodynamic_above': REGIME_HYDRODYNAMIC_ABOVE,
                     'common_industrial_window': list(COMMON_INDUSTRIAL_FILM_RATIO_WINDOW)}
_REGIME_WORDS = {
    'MIXED_SUBSTANTIAL_CONTACT': 'mixed lubrication with substantial asperity contact (the '
                                 'normal condition for a roll imprint)',
    'MIXED_FIRST_CONTACT': 'mixed lubrication with first asperity contact',
    'HYDRODYNAMIC': 'thick film, hydrodynamic'}
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
    'sutcliffe_1989_thesis': 'Sutcliffe (1989) PhD thesis, Cambridge (E6 FT: Table 4.2 '
                             'contact-ratio curve, eq. 4.32 valley shear)',
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


ROELANDS_REFERENCE_PRESSURE_PA = 196.2e6     # p_r = 2000 kgf/cm2 [E5 FT (L.1)-(L.3)]
ROELANDS_LN_OFFSET = 9.67                    # (3 + 1.2)*ln 10 with eta in Pa s [E5 FT (L.3)]
PRESSURE_LAWS = ('barus', 'roelands')
LIMITING_SHEAR_LOWER_BOUND = 0.045           # tau_L/p not reached up to 0.045 [E6 FT, ch. 2]
LIMITING_SHEAR_FLAG = 'LIMITING_SHEAR_BELOW_PUBLISHED_LOWER_BOUND'
LIMITING_SHEAR_SENTENCE = (
    'No limiting shear stress was seen up to 0.045 of the pressure for a kerosine base oil at '
    '40 C [E6 FT]; the entered cap is lower.')

# Documentation and tests only, NEVER a default or a preset (SPEC18 package 5). Every entry
# [E6 FT: Sutcliffe 1989 thesis, ch. 2, Table 2.1 (Amsterdam viscometer) and Fig. 2.7 keys
# (disc machine), read on page images].
EXAMPLE_KEROSINE_BASE_OIL = {
    'name': ('Somentor 31, a mainly paraffinic kerosine mineral oil', '[E6 FT]'),
    'note': ('no additives; a base oil, not a plant\'s rolling oil', '[E6 FT]'),
    'viscosity_pa_s_at_0_mpa': ({'313.15': 1.409e-3, '333.15': 1.033e-3, '373.15': 0.632e-3},
                                '[E6 FT, Table 2.1]'),
    'viscosity_pa_s_at_100_mpa': ({'313.15': 3.985e-3, '333.15': 2.699e-3, '373.15': 1.625e-3},
                                  '[E6 FT, Table 2.1]'),
    'pressure_viscosity_coefficient_per_pa': ({'313.15': 10.40e-9, '333.15': 9.60e-9,
                                               '373.15': 9.44e-9},
                                              '[E6 FT, Table 2.1, 0-100 MPa]'),
    'eyring_stress_pa_at_313_k': ({'625e6': 4.5e6, '945e6': 6.0e6, '1510e6': 11.7e6},
                                  '[E6 FT, Fig. 2.7 keys; disc machine]'),
    'viscosity_pa_s_at_313_k_disc_machine': ({'625e6': 2.5, '945e6': 15.0, '1510e6': 740.0},
                                             '[E6 FT, Fig. 2.7 keys; disc machine]'),
    'limiting_shear_lower_bound_over_pressure': (
        LIMITING_SHEAR_LOWER_BOUND, '[E6 FT: none observed up to 68/1510 MPa = 0.045]'),
    'conductivity_w_mk_ambient': (0.125, '[E6 FT: assumed equal to another oil by the source]'),
    'conductivity_w_mk_in_nip': (0.25, '[E6 FT: allowing for the rise with pressure]'),
}


def _table(value):
    """Validated viscosity table: tuple of (T [K], eta [Pa s]) pairs."""
    msg = ('viscosity_table must be None or >= 2 points with increasing temperature in '
           '[230, 700] K and non-increasing viscosity in (0, 10] Pa s')
    if not isinstance(value, (tuple, list)) or len(value) < 2:
        raise ValueError(msg)
    out = []
    for pt in value:
        if not isinstance(pt, (tuple, list)) or len(pt) != 2:
            raise ValueError(msg)
        t, eta = pt
        for v in (t, eta):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(msg)
        if not 230.0 <= t <= 700.0 or not 0 < eta <= 10.0:
            raise ValueError(msg)
        out.append((float(t), float(eta)))
    for (t1, e1), (t2, e2) in zip(out, out[1:]):
        if not t2 > t1 or e2 > e1:
            raise ValueError(msg)
    return tuple(out)


@dataclass(frozen=True)
class Lubricant:
    """Rolling oil: temperature law (exponential, or a viscosity table) and pressure law
    (Barus, or Roelands as an option).

    ``viscosity_ref_pa_s`` is the dynamic viscosity at ``reference_temperature_k`` and zero
    gauge pressure. ``conductivity_w_mk`` is optional; when None the thermal loading
    parameter uses ``DEFAULT_OIL_CONDUCTIVITY_W_MK`` [M] and says so.

    ``viscosity_table`` (optional, SPEC18 package 5): data-sheet points (T [K], eta0 [Pa s]);
    ``ln eta0`` is interpolated linearly in T between neighbouring points and continued with
    the end segment's slope outside [D, SPEC18: piecewise exponential through data-sheet
    points]. With a table the reference viscosity and the constant temperature coefficient are
    not used for eta0.

    ``pressure_law``: 'barus' (default) ``eta = eta0*exp(alpha*p)`` or 'roelands'
    [E5 FT (L.3), product form; the source warns that one thesis prints a SUM of the pressure
    and temperature terms, which is wrong]::

        eta(T, p) = eta0(T)*exp{(ln eta0(T) + 9.67)*[(1 + p/p_r)^z - 1]},  p_r = 196.2 MPa
        z = roelands_z, or p_r*alpha/(ln eta0(T) + 9.67)                    [E5 FT (4.194)]

    eta0(T) from the table or the exponential law (the temperature factor of (L.3) is not
    used). Without ``roelands_z`` the index is evaluated at the temperature of the call, so the
    slope at zero pressure equals the entered Barus coefficient at every temperature
    [D, SPEC18]. On the one foil oil with data Roelands with that index is low by a factor 12
    to 30 at bite pressure (benchmark A9-PRESSURE-LAWS-KEROSINE): it is optional, never the
    default. The inlet film formula always uses the Barus coefficient (its published closed
    form).

    Eyring stress ``tau_0(p) = eyring_stress_pa + eyring_stress_pressure_coefficient*p`` and
    limiting shear stress ``tau_L(p) = limiting_shear_stress_pa +
    limiting_shear_pressure_coefficient*p`` [D, SPEC18 forms]: supplied inputs, no default
    (E6 FT data for one kerosine base oil: tau_0 4.5 / 6.0 / 11.7 MPa at 625 / 945 / 1510 MPa
    and 40 C; no limiting shear stress up to 0.045 of the pressure; no source gives a value).
    """
    viscosity_ref_pa_s: float
    reference_temperature_k: float
    temperature_viscosity_coefficient_per_k: float
    pressure_viscosity_coefficient_per_pa: float
    conductivity_w_mk: float | None = None
    name: str = 'rolling oil'
    viscosity_table: tuple | None = None
    pressure_law: str = 'barus'
    roelands_z: float | None = None
    eyring_stress_pa: float | None = None
    eyring_stress_pressure_coefficient: float | None = None
    limiting_shear_stress_pa: float | None = None
    limiting_shear_pressure_coefficient: float | None = None

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
        if self.viscosity_table is not None:
            _table(self.viscosity_table)
        if self.pressure_law not in PRESSURE_LAWS:
            raise ValueError(f'pressure_law must be one of {PRESSURE_LAWS}')
        if self.roelands_z is not None:
            z = _num('roelands_z', self.roelands_z)
            if not 0 < z <= 2:
                raise ValueError('roelands_z must be in (0, 2]')
        for name, lo, hi, open_lo in (('eyring_stress_pa', 1e4, 1e9, False),
                                      ('eyring_stress_pressure_coefficient', 0.0, 0.1, True),
                                      ('limiting_shear_stress_pa', 1e4, 5e9, False),
                                      ('limiting_shear_pressure_coefficient', 0.0, 1.0, True)):
            v = getattr(self, name)
            if v is None:
                continue
            v = _num(name, v)
            if (v <= lo if open_lo else v < lo) or v > hi:
                raise ValueError(f'{name} must be in {"(" if open_lo else "["}{lo:g}, {hi:g}]')

    def _table_segment(self, t):
        pts = _table(self.viscosity_table)
        i = 0
        while i < len(pts) - 2 and t >= pts[i + 1][0]:
            i += 1
        (t1, e1), (t2, e2) = pts[i], pts[i + 1]
        slope = (math.log(e2) - math.log(e1)) / (t2 - t1)
        return t1, math.log(e1), slope, not pts[0][0] <= t <= pts[-1][0]

    def zero_pressure_viscosity_pa_s(self, temperature_k):
        """eta0(T): from the table when given, else the exponential law."""
        t = _temperature('temperature_k', temperature_k)
        if self.viscosity_table is None:
            return self.viscosity_ref_pa_s * math.exp(
                -self.temperature_viscosity_coefficient_per_k * (t - self.reference_temperature_k))
        t1, ln1, slope, _ = self._table_segment(t)
        return math.exp(ln1 + slope * (t - t1))

    def temperature_viscosity_coefficient_at(self, temperature_k):
        """Local ``-d ln eta0/dT`` [1/K]: the table segment's, else the constant coefficient."""
        t = _temperature('temperature_k', temperature_k)
        if self.viscosity_table is None:
            return float(self.temperature_viscosity_coefficient_per_k)
        return -self._table_segment(t)[2]

    def viscosity_table_extrapolated(self, temperature_k):
        if self.viscosity_table is None:
            return False
        return self._table_segment(_temperature('temperature_k', temperature_k))[3]

    def roelands_index(self, temperature_k):
        """z: ``roelands_z`` or p_r*alpha/(ln eta0(T) + 9.67) [E5 FT (4.194)]."""
        if self.roelands_z is not None:
            return float(self.roelands_z)
        lnv = math.log(self.zero_pressure_viscosity_pa_s(temperature_k)) + ROELANDS_LN_OFFSET
        if lnv <= 0:
            raise ValueError('Roelands law needs ln(eta0) + 9.67 > 0 (eta0 above 6.3e-5 Pa s)')
        return ROELANDS_REFERENCE_PRESSURE_PA * self.pressure_viscosity_coefficient_per_pa / lnv

    def dynamic_viscosity_pa_s(self, temperature_k, pressure_pa=0.0):
        """eta(T, p): exponential law or table for eta0, Barus or Roelands for pressure."""
        self.validate()
        t = _temperature('temperature_k', temperature_k)
        p = _num('pressure_pa', pressure_pa, nonnegative=True, hi=3e9)
        if self.viscosity_table is None and self.pressure_law == 'barus':
            exponent = (-self.temperature_viscosity_coefficient_per_k
                        * (t - self.reference_temperature_k)
                        + self.pressure_viscosity_coefficient_per_pa * p)
            if exponent > 700:
                raise ValueError('viscosity exceeds numerical domain')
            return self.viscosity_ref_pa_s * math.exp(exponent)
        eta0 = self.zero_pressure_viscosity_pa_s(t)
        if self.pressure_law == 'barus':
            exponent = self.pressure_viscosity_coefficient_per_pa * p
        else:
            lnv = math.log(eta0) + ROELANDS_LN_OFFSET
            if lnv <= 0:
                raise ValueError('Roelands law needs ln(eta0) + 9.67 > 0 (eta0 above 6.3e-5 '
                                 'Pa s)')
            z = self.roelands_index(t)
            exponent = lnv * ((1 + p / ROELANDS_REFERENCE_PRESSURE_PA) ** z - 1)
        if exponent > 700:
            raise ValueError('viscosity exceeds numerical domain')
        return eta0 * math.exp(exponent)

    def eyring_stress_at(self, pressure_pa):
        """tau_0(p) [Pa], or None when neither Eyring field is supplied."""
        if self.eyring_stress_pa is None and self.eyring_stress_pressure_coefficient is None:
            return None
        return (self.eyring_stress_pa or 0.0) + (self.eyring_stress_pressure_coefficient
                                                 or 0.0) * pressure_pa

    def limiting_shear_stress_at(self, pressure_pa):
        """tau_L(p) [Pa], or None when neither limiting-stress field is supplied."""
        if self.limiting_shear_stress_pa is None and \
                self.limiting_shear_pressure_coefficient is None:
            return None
        return (self.limiting_shear_stress_pa or 0.0) + (
            self.limiting_shear_pressure_coefficient or 0.0) * pressure_pa

    def limiting_shear_check(self, mean_pressure_pa):
        """(flags, sentences) of the limiting shear stress against the published lower bound."""
        tau = self.limiting_shear_stress_at(mean_pressure_pa)
        if tau is None or mean_pressure_pa <= 0:
            return [], []
        if tau / mean_pressure_pa < LIMITING_SHEAR_LOWER_BOUND:
            return [LIMITING_SHEAR_FLAG], [LIMITING_SHEAR_SENTENCE]
        return [], []

    def viscosity_flags(self, temperature_k):
        flags = []
        if self.viscosity_table is not None:
            flags.append('VISCOSITY_FROM_TABLE')
            if self.viscosity_table_extrapolated(temperature_k):
                flags.append('VISCOSITY_TABLE_EXTRAPOLATED')
        if self.pressure_law == 'roelands':
            flags.append('ROELANDS_PRESSURE_LAW')
        return flags

    def viscosity_law_text(self):
        t = ('viscosity table (ln eta0 piecewise linear in T) [D, SPEC18]'
             if self.viscosity_table is not None else
             'exponential temperature law')
        p = ('Roelands pressure law [E5 FT (L.3)] (low by 12 to 30 times at bite pressure on '
             'the one foil oil with data)' if self.pressure_law == 'roelands'
             else 'Barus pressure law')
        return f'{t}; {p}'

    def is_default_law(self):
        return self.viscosity_table is None and self.pressure_law == 'barus'

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


# SPEC18 package 6: load sharing on a published contact-ratio curve (a REDUCED closure).
# [E6 FT, Table 4.2: the 20 -> 15 um foil pass of Fig. 9 of E1, d0 0.1 um, wavelength 15 um,
#  one oil, 1 to 30 m/s; film ratio = h_s/d0, derived]
PUBLISHED_FOIL_CONTACT_RATIO_CURVE = ((0.14, 0.88), (0.36, 0.69), (0.55, 0.53), (0.97, 0.28),
                                      (2.37, 0.01))
PUBLISHED_FOIL_VALLEY_FILM_CURVE = ((0.14, 0.42), (0.36, 0.62), (0.55, 0.79), (0.97, 1.10),
                                    (2.37, 2.17))   # (film ratio, valley film / roughness)
CLOSURE_MODELS = ('placeholder_exponential', 'load_sharing_curve')
VALLEY_MODELS = ('constant', 'eyring', 'newtonian_capped')
STATUS_LOAD_SHARING = 'UNVALIDATED_LOAD_SHARING_ON_A_PUBLISHED_CONTACT_RATIO_CURVE'
LOAD_SHARING_FLAG = 'REDUCED_LOAD_SHARING_CLOSURE_NO_INLET_ANALYSIS'
PUBLISHED_CURVE_FLAG = 'CONTACT_RATIO_CURVE_OF_ONE_PUBLISHED_FOIL_PASS'
ENTERED_CONTACT_FRICTION_FLAG = 'CONTACT_FRICTION_IS_AN_ENTERED_VALUE'
OUTSIDE_CURVE_FLAG = 'FILM_RATIO_OUTSIDE_CONTACT_RATIO_CURVE'
CONTACT_FRICTION_REQUIRED = ('friction_closure.contact_friction is required for the '
                             'load_sharing_curve model: the sources span 0.013 to 0.1')
LOAD_SHARING_NOTE = ('Load sharing on a published contact-ratio curve of one foil pass. The '
                     'friction level is your entered contact friction; read the change with '
                     'speed, not the level.')
LOAD_SHARING_LIMITATIONS = [
    'The contact-ratio curve is model output for one foil pass (20 -> 15 um, roughness 0.1 um, '
    'wavelength 15 um, one oil) [E6 FT, Table 4.2]; it is not a property of other surfaces, '
    'oils or reductions. It is the closure\'s input, so it cannot also serve as its benchmark.',
    'The level of friction is set by the entered contact friction (0.013 to 0.1 in the '
    'sources); the closure supports the change of friction with speed, not its level.',
    'Published data need a contact friction that varies with film and reduction and cannot be '
    'met with one value [E7 FT].',
    'The film ratio entered is the smooth inlet film over the composite roughness; the '
    'table\'s abscissa is the thesis\'s full inlet integration, which its own closed-form film '
    'over-states by 1.36 / 1.11 / 0.98 / 0.89 / 0.79 at 30 / 10 / 5 / 3 / 1 m/s [E6 FT]: the '
    'abscissa carries that much mismatch.',
    'Friction is the same through the bite; no roughness wavelength, lay or reduction enters; '
    'no inlet analysis (the transcribed height distribution and crushing laws do not reproduce '
    'the source table and are not assembled: physicroll/asperity_contact.py).',
]
VALLEY_STEP = 1e-4


def _curve(name, points, kind):
    """Validated curve: 2 to 12 (film ratio, value) points, film ratios increasing in (0, 100];
    contact ratios in [0, 1] non-increasing, or valley films positive non-decreasing."""
    msg = (f'{name} must have 2 to 12 points with film ratios strictly increasing in (0, 100] '
           + ('and contact ratios in [0, 1], non-increasing' if kind == 'contact'
              else 'and valley films positive, non-decreasing'))
    if not isinstance(points, (tuple, list)) or not 2 <= len(points) <= 12:
        raise ValueError(msg)
    out = []
    for pt in points:
        if not isinstance(pt, (tuple, list)) or len(pt) != 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in pt):
            raise ValueError(msg)
        lam, val = float(pt[0]), float(pt[1])
        if not 0 < lam <= 100 or (kind == 'contact' and not 0 <= val <= 1) or \
                (kind == 'valley' and not val > 0):
            raise ValueError(msg)
        out.append((lam, val))
    for (l1, v1), (l2, v2) in zip(out, out[1:]):
        if not l2 > l1 or (kind == 'contact' and v2 > v1) or (kind == 'valley' and v2 < v1):
            raise ValueError(msg)
    return tuple(out)


def contact_ratio_at(film_ratio, curve=PUBLISHED_FOIL_CONTACT_RATIO_CURVE):
    """(A, dA/dLambda, held) with A linear in ln(Lambda) between neighbouring points and the end
    values held outside [D, SPEC18: interpolation of published points, not a contact model]."""
    pts = _curve('contact_ratio_curve', curve, 'contact')
    lam = _num('film_ratio', film_ratio, positive=True, hi=1e6)
    if lam <= pts[0][0]:
        return pts[0][1], 0.0, lam < pts[0][0]
    if lam >= pts[-1][0]:
        return pts[-1][1], 0.0, lam > pts[-1][0]
    i = 0
    while lam > pts[i + 1][0]:
        i += 1
    (l1, a1), (l2, a2) = pts[i], pts[i + 1]
    k = (a2 - a1) / math.log(l2 / l1)
    return a1 + k * math.log(lam / l1), k / lam, False


def valley_film_over_rq_at(film_ratio, curve=PUBLISHED_FOIL_VALLEY_FILM_CURVE):
    """h_v/Rq: linear in ln-ln between points; first value held below the curve; above it
    Lambda*(last value/last film ratio) [D, SPEC18]."""
    pts = _curve('valley_film_curve', curve, 'valley')
    lam = _num('film_ratio', film_ratio, positive=True, hi=1e6)
    if lam <= pts[0][0]:
        return pts[0][1]
    if lam >= pts[-1][0]:
        return lam * pts[-1][1] / pts[-1][0]
    i = 0
    while lam > pts[i + 1][0]:
        i += 1
    (l1, v1), (l2, v2) = pts[i], pts[i + 1]
    return math.exp(math.log(v1) + math.log(v2 / v1) * math.log(lam / l1) / math.log(l2 / l1))


@dataclass(frozen=True)
class FrictionClosure:
    """Friction closure. ``model``: 'placeholder_exponential' (default, unchanged)
    ``mu = mu_v + (mu_b - mu_v)*exp(-Lambda/lambda0)`` [D], not fitted; or
    'load_sharing_curve' (SPEC18 package 6, a REDUCED closure): ``mu = A*mu_c + (1 - A)*mu_v``
    [BT-S9 EX; E7 FT eq. 7] with the contact ratio A(Lambda) from a curve (default: the
    published five points of one foil pass [E6 FT, Table 4.2]), ``contact_friction`` mu_c a
    REQUIRED entered value (no default) and the valley friction mu_v from ``valley_model``:
    'constant' (``mu_v``), 'eyring' ``min(tau_0*asinh(eta*u_s/(tau_0*h_v)), tau_L)/p_mean``
    [E6 FT (4.32)] or 'newtonian_capped' ``min(eta*u_s/h_v, tau_L)/p_mean`` (a cap required).
    """
    mu_b: float = 0.09     # [V] Tabary et al. 1996 low-speed (boundary additive) value
    mu_v: float = 0.008    # [D] within 0.005-0.01
    lambda0: float = 1.0   # [D]
    model: str = 'placeholder_exponential'
    contact_friction: float | None = None
    contact_ratio_curve: tuple | None = None
    valley_film_curve: tuple | None = None
    valley_model: str = 'constant'

    def validate(self):
        mu_b = _num('mu_b', self.mu_b, positive=True, hi=1.0)
        mu_v = _num('mu_v', self.mu_v, nonnegative=True, hi=1.0)
        _num('lambda0', self.lambda0, positive=True, hi=100.0)
        if mu_v > mu_b:
            raise ValueError('mu_v must not exceed mu_b')
        if self.model not in CLOSURE_MODELS:
            raise ValueError(f'friction_closure.model must be one of {CLOSURE_MODELS}')
        if self.valley_model not in VALLEY_MODELS:
            raise ValueError(f'friction_closure.valley_model must be one of {VALLEY_MODELS}')
        if self.model == 'load_sharing_curve':
            if self.contact_friction is None:
                raise ValueError(CONTACT_FRICTION_REQUIRED)
            mu_c = _num('contact_friction', self.contact_friction)
            if not 0 < mu_c <= 1:
                raise ValueError('friction_closure.contact_friction must be in (0, 1]')
        if self.contact_ratio_curve is not None:
            _curve('contact_ratio_curve', self.contact_ratio_curve, 'contact')
        if self.valley_film_curve is not None:
            _curve('valley_film_curve', self.valley_film_curve, 'valley')

    def contact_curve(self):
        return (PUBLISHED_FOIL_CONTACT_RATIO_CURVE if self.contact_ratio_curve is None
                else self.contact_ratio_curve)

    def valley_curve(self):
        return (PUBLISHED_FOIL_VALLEY_FILM_CURVE if self.valley_film_curve is None
                else self.valley_film_curve)

    def basis(self):
        default = FrictionClosure()
        if self.model == 'load_sharing_curve':
            return {'closure_form': '[BT-S9 EX; E7 FT eq. 7] mu = A*mu_c + (1 - A)*mu_v: load '
                                    'sharing on a contact-ratio curve (REDUCED: no inlet '
                                    'analysis)',
                    'contact_ratio_curve': ('[E6 FT, Table 4.2] published curve of one foil '
                                            'pass' if self.contact_ratio_curve is None
                                            else 'supplied by caller'),
                    'interpolation': '[D, SPEC18] A linear in ln(Lambda), end values held; h_v '
                                     'ln-ln',
                    'contact_friction': 'entered by the user (no default; sources 0.013-0.1)',
                    'valley_model': {'constant': '[D] mu_v constant',
                                     'eyring': '[E6 FT (4.32)] Eyring valley shear',
                                     'newtonian_capped': '[D, SPEC18] Newtonian valley shear '
                                                         'capped at the limiting stress'}[
                                         self.valley_model]}
        return {
            'mu_b': '[V] Tabary et al. 1996 abstract' if self.mu_b == default.mu_b
                    else 'supplied by caller',
            'mu_v': '[D] analyst choice within 0.005-0.01' if self.mu_v == default.mu_v
                    else 'supplied by caller',
            'lambda0': '[D] analyst placeholder' if self.lambda0 == default.lambda0
                       else 'supplied by caller',
            'closure_form': '[D] analyst placeholder exp(-Lambda/lambda0); not fitted'}


def _regime(film_ratio):
    if film_ratio < REGIME_SUBSTANTIAL_CONTACT_BELOW:
        return 'MIXED_SUBSTANTIAL_CONTACT'
    if film_ratio <= REGIME_HYDRODYNAMIC_ABOVE:
        return 'MIXED_FIRST_CONTACT'
    return 'HYDRODYNAMIC'


def in_common_industrial_window(film_ratio):
    """True when 0.01 <= Lambda <= 0.5, the common industrial window [BT-S3 EX, BT-S9 EX]."""
    lo, hi = COMMON_INDUSTRIAL_FILM_RATIO_WINDOW
    return lo <= film_ratio <= hi


# --------------------------------------------------------------------------- W3.2 film
def _film_core(lub, ur, us, h0, h1, rc, yps, sb, t_in, thermal):
    theta = math.sqrt((h0 - h1) / rc)
    u_mean = 0.5 * (ur + us)
    eta0 = (lub.dynamic_viscosity_pa_s(t_in) if lub.viscosity_table is None
            else lub.zero_pressure_viscosity_pa_s(t_in))
    alpha = lub.pressure_viscosity_coefficient_per_pa
    p_entry = yps - sb
    h_iso = 6 * eta0 * alpha * u_mean / (theta * -math.expm1(-alpha * p_entry))
    h_yonly = 6 * eta0 * alpha * u_mean / (theta * -math.expm1(-alpha * yps))
    k = lub.effective_conductivity_w_mk()
    load = eta0 * lub.temperature_viscosity_coefficient_at(t_in) * u_mean ** 2 / k
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

    ``contact_radius_m`` is the radius of the inlet angle ``theta0 = sqrt(draft/R_c)``: the
    deformed arc R' of a Hitchcock bite, the undeformed roll radius of a mattress bite (what
    ``band_process`` passes; module docstring).
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
    if lub.viscosity_table is None and \
            abs(t_in - lub.reference_temperature_k) > VISCOSITY_EXTRAPOLATION_WARN_K:
        flags.append('VISCOSITY_TEMPERATURE_EXTRAPOLATED_OVER_60K')
    flags += lub.viscosity_flags(t_in)
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
            'viscosity_law': ('[D] exponential temperature law with Barus pressure law'
                              if lub.is_default_law() else
                              lub.viscosity_law_text() + (
                                  '; the reference viscosity is not used for eta0'
                                  if lub.viscosity_table is not None else '')
                              + '; the film formula uses the Barus coefficient')},
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


def _valley(lam, closure, lub, rq, state):
    """(mu_v, h_v [m] or None, tau_v [Pa] or None, capped or None, flags, notes)."""
    if closure.valley_model == 'constant':
        return closure.mu_v, None, None, None, [], []
    if lub is None or rq is None or state is None or \
            state.get('mean_pressure_pa') is None or \
            state.get('mean_sliding_speed_m_s') is None:
        raise ValueError('valley shear needs the bite state')
    p = _num('mean_pressure_pa', state['mean_pressure_pa'], positive=True, hi=3e9)
    u_s = _num('mean_sliding_speed_m_s', state['mean_sliding_speed_m_s'], nonnegative=True,
               hi=MAX_SPEED_M_S)
    t = _temperature('inlet_temperature_k', state['inlet_temperature_k'])
    eta = lub.dynamic_viscosity_pa_s(t, p)
    h_v = valley_film_over_rq_at(lam, closure.valley_curve()) * rq
    tau_l = lub.limiting_shear_stress_at(p)
    if closure.valley_model == 'eyring':
        tau_0 = lub.eyring_stress_at(p)
        if tau_0 is None or tau_0 <= 0:
            raise ValueError('the eyring valley model needs an Eyring stress '
                             '(tribology.lubricant.eyring_stress_pa or its pressure coefficient)')
        tau = tau_0 * math.asinh(eta * u_s / (tau_0 * h_v))
    else:
        if tau_l is None:
            raise ValueError('the newtonian_capped valley model needs a limiting shear stress '
                             '(tribology.lubricant.limiting_shear_stress_pa or its pressure '
                             'coefficient)')
        tau = eta * u_s / h_v
    capped = None
    flags, notes = [], []
    if tau_l is not None:
        capped = tau > tau_l
        tau = min(tau, tau_l)
        flags, notes = lub.limiting_shear_check(p)
    return tau / p, h_v, tau, capped, flags, notes


def _load_sharing(lam, closure, lub, rq, state):
    a, da, held = contact_ratio_at(lam, closure.contact_curve())
    mu_v, h_v, tau, capped, flags, notes = _valley(lam, closure, lub, rq, state)
    mu = a * closure.contact_friction + (1 - a) * mu_v
    return {'mu': mu, 'a': a, 'da': da, 'held': held, 'mu_v': mu_v, 'h_v': h_v, 'tau': tau,
            'capped': capped, 'flags': flags, 'notes': notes}


def _closure_mu(lam, closure, lub=None, rq=None, state=None):
    if closure.model == 'placeholder_exponential':
        return _mu(lam, closure)
    return _load_sharing(lam, closure, lub, rq, state)['mu']


def friction_coefficient(film_ratio, closure=None, *, lubricant=None, finish=None,
                         bite_state=None):
    """Friction closure ``mu(Lambda)`` and its slope ``dmu/dLambda``.

    Placeholder (default): ``mu = mu_v + (mu_b - mu_v)*exp(-Lambda/lambda0)``, slope <= 0.
    'load_sharing_curve': ``mu = A*mu_c + (1 - A)*mu_v`` on the contact-ratio curve; the
    valley models 'eyring' and 'newtonian_capped' need ``lubricant``, ``finish`` and
    ``bite_state = {'mean_pressure_pa', 'mean_sliding_speed_m_s', 'inlet_temperature_k'}``
    (ValueError 'valley shear needs the bite state' without them).
    """
    closure = FrictionClosure() if closure is None else closure
    if not isinstance(closure, FrictionClosure):
        raise ValueError('closure must be a FrictionClosure')
    closure.validate()
    if closure.model == 'load_sharing_curve':
        return _friction_load_sharing(film_ratio, closure, lubricant, finish, bite_state)
    lam = _num('film_ratio', film_ratio, nonnegative=True, hi=1e6)
    mu = _mu(lam, closure)
    slope = -(closure.mu_b - closure.mu_v) / closure.lambda0 * math.exp(-lam / closure.lambda0)
    regime = _regime(lam)
    return _checked({
        'status': STATUS_FRICTION, 'friction_coefficient': mu,
        'dmu_dlambda': slope, 'film_ratio': lam, 'regime': regime,
        'in_common_industrial_window': in_common_industrial_window(lam),
        'closure': asdict(closure),
        'formula': 'mu = mu_v + (mu_b - mu_v)*exp(-Lambda/lambda0)',
        'regime_boundaries': dict(REGIME_BOUNDARIES),
        'basis': dict(closure.basis(), regime_boundaries='[V] Sutcliffe 2002; BT-S9 EX; window '
                                                         'BT-S3 EX, BT-S9 EX'),
        'reasons': [f'Film ratio {lam:.3f}: {_REGIME_WORDS[regime]}; placeholder mu = '
                    f'{mu:.4f}.'],
        'flags': [PLACEHOLDER_FLAG],
        'limitations': [
            'The closure is an analyst placeholder, not fitted to any data.',
            'Le & Sutcliffe (2001) needed a boundary friction that varies with film thickness '
            'and reduction to fit the same aluminium data; a single mu_b cannot.',
            'Regime boundaries are conventional; transitions are gradual.'],
        'sources': [SOURCES['sutcliffe_2002'], SOURCES['tabary_1996'],
                    SOURCES['le_sutcliffe_2001']]})


def _friction_load_sharing(film_ratio, closure, lub, finish, state):
    lam = _num('film_ratio', film_ratio, positive=True, hi=1e6)
    rq = finish.composite_rq_m() if finish is not None else None
    r = _load_sharing(lam, closure, lub, rq, state)
    if closure.valley_model == 'constant':
        slope = (closure.contact_friction - closure.mu_v) * r['da']
    else:
        d = VALLEY_STEP * lam
        slope = (_load_sharing(lam + d, closure, lub, rq, state)['mu']
                 - _load_sharing(lam - d, closure, lub, rq, state)['mu']) / (2 * d)
    regime = _regime(lam)
    flags = [LOAD_SHARING_FLAG, ENTERED_CONTACT_FRICTION_FLAG]
    if closure.contact_ratio_curve is None:
        flags.append(PUBLISHED_CURVE_FLAG)
    if r['held']:
        flags.append(OUTSIDE_CURVE_FLAG)
    flags += [f for f in r['flags'] if f not in flags]
    limitations = list(LOAD_SHARING_LIMITATIONS) + r['notes']
    if r['held']:
        limitations.append(f'Film ratio {lam:.3g} lies outside the contact-ratio curve '
                           f'({closure.contact_curve()[0][0]:g} to '
                           f'{closure.contact_curve()[-1][0]:g}): the end value is held, not '
                           'extrapolated.')
    return _checked({
        'status': STATUS_LOAD_SHARING, 'friction_coefficient': r['mu'],
        'dmu_dlambda': slope, 'film_ratio': lam, 'regime': regime,
        'in_common_industrial_window': in_common_industrial_window(lam),
        'closure': asdict(closure),
        'formula': 'mu = A*mu_c + (1 - A)*mu_v, A(Lambda) on the contact-ratio curve',
        'regime_boundaries': dict(REGIME_BOUNDARIES),
        'contact_area_ratio': r['a'], 'contact_friction': closure.contact_friction,
        'valley_friction': r['mu_v'], 'valley_model': closure.valley_model,
        'valley_film_thickness_m': r['h_v'], 'valley_shear_stress_pa': r['tau'],
        'valley_shear_capped': r['capped'],
        'contact_ratio_curve': [list(x) for x in closure.contact_curve()],
        'curve_is_published_default': closure.contact_ratio_curve is None,
        'basis': dict(closure.basis(), regime_boundaries='[V] Sutcliffe 2002; BT-S9 EX; window '
                                                         'BT-S3 EX, BT-S9 EX'),
        'reasons': [f'Film ratio {lam:.3f}: {_REGIME_WORDS[regime]}; contact ratio '
                    f'{r["a"]:.3f}, mu = {r["mu"]:.4f} with the entered contact friction '
                    f'{closure.contact_friction:g}.'],
        'flags': flags, 'limitations': limitations,
        'sources': [SOURCES['sutcliffe_2002'], SOURCES['le_sutcliffe_2001'],
                    SOURCES['sutcliffe_1989_thesis']]})


def friction_at_speed(lubricant, finish, closure, *, roll_surface_speed_m_s,
                      strip_entry_speed_m_s, entry_thickness_m, exit_thickness_m,
                      contact_radius_m, plane_strain_yield_pa, back_tension_pa,
                      inlet_temperature_k, thermal_correction=False, mean_pressure_pa=None,
                      backward_slip_fraction=None):
    """Oil + speed + temperature -> film -> Lambda -> closure friction, with speed slope.

    ``dmu_dspeed_per_m_s`` is the central finite difference of mu with respect to the roll
    surface speed, the strip entry speed scaled in proportion (fixed slip); negative means
    friction falls as speed rises. ``mean_pressure_pa`` (the bite's mean pressure) and
    ``backward_slip_fraction`` give the bite state the computed valley models of the
    load-sharing closure need; the mean sliding speed is ``u_s = V_r*(b + f)/2`` with
    ``f = u_entry*h0/(V_r*h1) - 1`` and ``b`` given, else ``1 - u_entry/V_r`` [D, SPEC18].
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
    h0_, h1_ = args[3], args[4]

    def state_at(ur, us):
        if mean_pressure_pa is None:
            return None
        f = us * h0_ / (ur * h1_) - 1
        b = (1 - us / ur) if backward_slip_fraction is None else backward_slip_fraction
        return {'mean_pressure_pa': mean_pressure_pa,
                'mean_sliding_speed_m_s': abs(ur * (b + f) / 2),
                'inlet_temperature_k': args[8]}
    state = state_at(args[1], args[2])
    fric = friction_coefficient(lam, closure, lubricant=lubricant, finish=finish,
                                bite_state=state)
    step = SPEED_DERIVATIVE_RELATIVE_STEP
    mus = []
    for sign in (1, -1):
        scaled = list(args)
        scaled[1] = args[1] * (1 + sign * step)
        scaled[2] = args[2] * (1 + sign * step)
        if closure.model == 'placeholder_exponential':
            mus.append(_mu(_film_core(*scaled)['h'] / rq, closure))
        else:
            mus.append(_closure_mu(_film_core(*scaled)['h'] / rq, closure, lubricant, rq,
                                   state_at(scaled[1], scaled[2])))
    dmu_dspeed = (mus[0] - mus[1]) / (2 * step * args[1])
    regime = fric['regime']
    first = PLACEHOLDER_FLAG if closure.model == 'placeholder_exponential' else LOAD_SHARING_FLAG
    flags = [first] + [f for f in film['flags'] if f not in (first,)]
    flags += [f for f in fric['flags'] if f not in flags]
    if regime == 'HYDRODYNAMIC':
        flags.append('THICK_FILM_SKIDDING_MATTE_RISK')
    reasons = film['reasons'] + fric['reasons'] + [
        f'Speed slope dmu/dV_roll = {dmu_dspeed:.3e} s/m (negative: friction falls as speed '
        f'rises; lower friction shrinks the chatter margin).']
    basis = dict(film['basis'])
    basis.update({f'closure_{k}': v for k, v in fric['basis'].items()})
    basis['speed_derivative'] = '[D] central difference, relative step 1e-4, fixed slip'
    return _checked({
        'status': fric['status'],
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
        'in_common_industrial_window': fric['in_common_industrial_window'],
        'friction_coefficient': fric['friction_coefficient'],
        'dmu_dlambda': fric['dmu_dlambda'],
        'dmu_dspeed_per_m_s': dmu_dspeed,
        'closure': fric['closure'],
        'regime_boundaries': fric['regime_boundaries'],
        **{k: fric[k] for k in ('contact_area_ratio', 'contact_friction', 'valley_friction',
                                'valley_model', 'valley_film_thickness_m',
                                'valley_shear_stress_pa', 'valley_shear_capped',
                                'curve_is_published_default') if k in fric},
        'basis': basis, 'reasons': reasons, 'flags': flags,
        'limitations': film['limitations'] + fric['limitations'] + [
            'Rq-based film ratio ignores roughness lay and asperity flattening in the bite.'],
        'sources': film['sources'] + [s for s in fric['sources'] if s not in film['sources']]})


def friction_speed_curve(lubricant, finish, closure, *, exit_speeds_m_s, entry_thickness_m,
                         exit_thickness_m, contact_radius_m, plane_strain_yield_pa,
                         back_tension_pa, inlet_temperature_k, forward_slip_fraction=0.0,
                         thermal_correction=False, mean_pressure_pa=None,
                         backward_slip_fraction=None):
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
    points = []
    flags = [PLACEHOLDER_FLAG if (closure is None or closure.model == 'placeholder_exponential')
             else LOAD_SHARING_FLAG]
    last = None
    for ux in speeds:
        r = friction_at_speed(
            lubricant, finish, closure, roll_surface_speed_m_s=ux / (1 + f),
            strip_entry_speed_m_s=ux * h1 / h0, entry_thickness_m=h0, exit_thickness_m=h1,
            contact_radius_m=contact_radius_m, plane_strain_yield_pa=plane_strain_yield_pa,
            back_tension_pa=back_tension_pa, inlet_temperature_k=inlet_temperature_k,
            thermal_correction=thermal_correction, mean_pressure_pa=mean_pressure_pa,
            backward_slip_fraction=backward_slip_fraction)
        for fl in r['flags']:
            if fl not in flags:
                flags.append(fl)
        last = r
        points.append({
            'exit_speed_m_s': ux, 'roll_surface_speed_m_s': r['roll_surface_speed_m_s'],
            'strip_entry_speed_m_s': r['strip_entry_speed_m_s'],
            'film_thickness_m': r['film_thickness_m'], 'film_ratio': r['film_ratio'],
            'regime': r['regime'],
            'in_common_industrial_window': r['in_common_industrial_window'],
            'friction_coefficient': r['friction_coefficient'],
            'dmu_dspeed_per_m_s': r['dmu_dspeed_per_m_s'],
            'dmu_dexit_speed_per_m_s': r['dmu_dspeed_per_m_s'] / (1 + f),
            'thermal_reduction_factor': r['thermal_reduction_factor']})
    basis = dict(last['basis'])
    basis['speed_mapping'] = '[D] mass flow with supplied forward slip'
    return _checked({
        'status': last['status'], 'points': points,
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

    ``sigma = s0 + (ss - s0)*(1 - exp(-eps/eps_c)) + theta4*eps`` [D form]. ``theta4`` may be
    negative (down to -5e9 Pa; SPEC18 package 8, B2): work softening of purified-matrix Al-Fe
    and high-purity grades beyond 80 % reduction [TM-LB2 EX]; ``validate`` then requires
    ``sigma(eps) > 0`` on ``[0, 10]`` (checked at 0, 10 and the stationary point).
    """
    initial_stress_pa: float
    saturation_stress_pa: float
    characteristic_strain: float
    stage_iv_slope_pa: float
    provenance: str

    def validate(self):
        s0 = _num('initial_stress_pa', self.initial_stress_pa, nonnegative=True, hi=5e9)
        ss = _num('saturation_stress_pa', self.saturation_stress_pa, positive=True, hi=5e9)
        ec = _num('characteristic_strain', self.characteristic_strain, positive=True, hi=100.0)
        th4 = _num('stage_iv_slope_pa', self.stage_iv_slope_pa, lo=-5e9, hi=5e10)
        _name('provenance', self.provenance)
        if ss < s0:
            raise ValueError('saturation_stress_pa must be >= initial_stress_pa')
        if th4 < 0:
            pts = [0.0, POSITIVITY_STRAIN_MAX]
            d = ss - s0
            if d > 0 and -th4 * ec / d < 1:      # d(sigma)/d(eps) = 0
                e_star = -ec * math.log(-th4 * ec / d)
                if 0 < e_star < POSITIVITY_STRAIN_MAX:
                    pts.append(e_star)
            for e in pts:
                if not s0 + d * -math.expm1(-e / ec) + th4 * e > 0:
                    raise ValueError(f'the flow stress must stay > 0 for equivalent strain in '
                                     f'[0, {POSITIVITY_STRAIN_MAX:g}] (it is not at {e:.4g})')

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


POSITIVITY_STRAIN_MAX = 10.0        # strain range of the positivity rule [SPEC18 package 8]
TOME_SIMPSON_PANELS = 64            # [D] composite Simpson of the Tome-Voce mean
NEGATIVE_SLOPE_FLAG = 'NEGATIVE_LATE_HARDENING_SLOPE_WORK_SOFTENING'


@dataclass(frozen=True)
class TomeVoceHardening:
    """Voce law with late slope in the Tome form (SPEC18 package 8, B2):
    ``sigma = (s_v + theta4*eps)*(1 - exp(-theta0*eps/s_v))`` [form: TM-LB4 EX]. Parameters
    supplied, never defaulted; ``s_v > 0``, ``theta0 > 0``, ``theta4`` in [-5e9, 5e10] Pa, and
    ``sigma > 0`` on (0, 10] (checked at 10, which suffices: the first factor is positive and
    increasing, the second linear). ``sigma(0) = 0`` by the form."""
    saturation_scale_pa: float
    stage_iv_slope_pa: float
    initial_hardening_rate_pa: float
    provenance: str

    def validate(self):
        sv = _num('saturation_scale_pa', self.saturation_scale_pa, positive=True, hi=5e9)
        th4 = _num('stage_iv_slope_pa', self.stage_iv_slope_pa, lo=-5e9, hi=5e10)
        _num('initial_hardening_rate_pa', self.initial_hardening_rate_pa, positive=True,
             hi=1e13)
        _name('provenance', self.provenance)
        if not sv + th4 * POSITIVITY_STRAIN_MAX > 0:
            raise ValueError(f'the flow stress must stay > 0 for equivalent strain in (0, '
                             f'{POSITIVITY_STRAIN_MAX:g}]')

    def _sigma(self, e):
        sv, th4 = self.saturation_scale_pa, self.stage_iv_slope_pa
        return (sv + th4 * e) * -math.expm1(-self.initial_hardening_rate_pa * e / sv)

    def stress(self, equivalent_strain):
        self.validate()
        return self._sigma(_num('equivalent_strain', equivalent_strain, nonnegative=True,
                                hi=100.0))

    def mean_stress(self, start, end, panels=TOME_SIMPSON_PANELS):
        """Strain mean over [start, end] by composite Simpson with ``panels`` panels [D]."""
        self.validate()
        a = _num('start', start, nonnegative=True, hi=100.0)
        b = _num('end', end, nonnegative=True, hi=100.0)
        if b < a:
            raise ValueError('invalid strain interval')
        if b == a:
            return self._sigma(a)
        n = panels + panels % 2
        h = (b - a) / n
        total = self._sigma(a) + self._sigma(b) + sum(
            (4 if i % 2 else 2) * self._sigma(a + i * h) for i in range(1, n))
        return total * h / 3 / (b - a)


# ------------------------------------------------- rate and temperature (SPEC18 package 8, B1)
RATE_TEMPERATURE_FACTOR_RANGE = (0.2, 5.0)


@dataclass(frozen=True)
class RateTemperatureFactor:
    """Flow-stress factor ``(rate/rate_ref)^m(T) * (1 - c_T*(T - T_ref))`` with
    ``m(T) = m + dm/dT*(T - T_ref)`` floored at 0 [form: TM report gap B1, "as the minimum"].
    No default instance: every number is the user's. Example values with their sources (never
    defaults): m about 0.027 for 16 um 1235-H18 over 1e-5 to 1e-2 /s [TM-LB1 EX]; m 0.04 at
    100 C and 0.07 at 200 C for 1050-H14 in slow tests [TM-LB10 EX]; c_T 0.0015 to 0.0019 /K
    [D from PT-T31, PT-T39]."""
    rate_sensitivity: float
    reference_strain_rate_per_s: float
    temperature_coefficient_per_k: float
    reference_temperature_k: float
    rate_sensitivity_slope_per_k: float = 0.0
    provenance: str = ''

    def validate(self):
        _num('rate_sensitivity', self.rate_sensitivity, lo=0.0, hi=0.2)
        r = _num('reference_strain_rate_per_s', self.reference_strain_rate_per_s, hi=1e6)
        if not r > 1e-8:
            raise ValueError('reference_strain_rate_per_s must be in (1e-8, 1e6]')
        _num('temperature_coefficient_per_k', self.temperature_coefficient_per_k, lo=0.0,
             hi=0.01)
        _num('reference_temperature_k', self.reference_temperature_k, lo=250.0, hi=700.0)
        _num('rate_sensitivity_slope_per_k', self.rate_sensitivity_slope_per_k, lo=0.0,
             hi=0.002)

    def rate_sensitivity_at(self, temperature_k):
        t = _num('temperature_k', temperature_k, positive=True, hi=2000.0)
        return max(0.0, self.rate_sensitivity + self.rate_sensitivity_slope_per_k
                   * (t - self.reference_temperature_k))

    def parts(self, strain_rate_per_s, temperature_k):
        """(rate factor, temperature factor, m(T)); ValueError when the product is outside
        [0.2, 5]."""
        self.validate()
        rate = _num('strain_rate_per_s', strain_rate_per_s, positive=True, hi=1e9)
        m = self.rate_sensitivity_at(temperature_k)
        fr = (rate / self.reference_strain_rate_per_s) ** m
        ft = 1 - self.temperature_coefficient_per_k * (temperature_k
                                                        - self.reference_temperature_k)
        lo, hi = RATE_TEMPERATURE_FACTOR_RANGE
        if not lo <= fr * ft <= hi:
            raise ValueError(f'rate and temperature factor {fr * ft:.4g} is outside '
                             f'[{lo:g}, {hi:g}]')
        return fr, ft, m

    def factor(self, strain_rate_per_s, temperature_k):
        fr, ft, _ = self.parts(strain_rate_per_s, temperature_k)
        return fr * ft


def mean_bite_strain_rate_per_s(exit_speed_m_s, contact_length_m, entry_thickness_m,
                                exit_thickness_m):
    """Mean bite strain rate ``(u/l_d)*ln(h0/h1)`` [TM report gap B1]."""
    u = _num('exit_speed_m_s', exit_speed_m_s, positive=True, hi=MAX_SPEED_M_S)
    ld = _num('contact_length_m', contact_length_m, positive=True, hi=1.0)
    h0, h1 = _thickness_pair(entry_thickness_m, exit_thickness_m)
    return u / ld * math.log(h0 / h1)


# ------------------------------------------------ fit to pass strengths (SPEC18 package 8, B2)
FIT_CHARACTERISTIC_STRAINS = (0.05, 5.0, 60)    # geometric scan of eps_c [D, SPEC18]
FIT_STRENGTH_KINDS = ('as_rolled_tensile', 'flow_stress')
FIT_UNDERDETERMINED = 'UNDERDETERMINED_FEWER_POINTS_THAN_PARAMETERS'
FIT_SINGULAR = 'UNDERDETERMINED_SINGULAR_NORMAL_EQUATIONS'
FIT_PARABOLA_STEPS = 8              # [D] repeated parabola (deviation, see the fit)
FIT_PARABOLA_TOL = 1e-6             # [D] in ln(eps_c)


def _solve_linear(a, b):
    """Gaussian elimination with partial pivoting; None when singular."""
    n = len(b)
    m = [list(r) + [v] for r, v in zip(a, b)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        scale = max(abs(x) for x in m[p][:n]) or 1.0
        if abs(m[p][c]) <= 1e-12 * scale:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(c + 1, n):
            f = m[r][c] / m[c][c]
            for k in range(c, n + 1):
                m[r][k] -= f * m[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][k] * x[k] for k in range(r + 1, n))) / m[r][r]
    return x


def _voce_lsq(eps, ys, ec, with_slope):
    cols = [[1.0] * len(eps), [-math.expm1(-e / ec) for e in eps]]
    if with_slope:
        cols.append(list(eps))
    # scale columns for conditioning
    sc = [max(abs(v) for v in c) or 1.0 for c in cols]
    cols = [[v / s_ for v in c] for c, s_ in zip(cols, sc)]
    a = [[sum(ci * cj for ci, cj in zip(c1, c2)) for c2 in cols] for c1 in cols]
    b = [sum(ci * y for ci, y in zip(c, ys)) for c in cols]
    x = _solve_linear(a, b)
    if x is None:
        return None
    x = [v / s_ for v, s_ in zip(x, sc)]
    if not with_slope:
        x.append(0.0)
    res = [y - (x[0] + x[1] * -math.expm1(-e / ec) + x[2] * e) for e, y in zip(eps, ys)]
    return x, res, sum(r * r for r in res)


def fit_voce_to_pass_strengths(gauges_m, strengths_pa, *, reference_thickness_m,
                               prior_equivalent_strain=0.0, strength_is='as_rolled_tensile'):
    """Generalised Voce law fitted to entered strengths at entered gauges [D, SPEC18].

    ``eps_i = prior + (2/sqrt(3))*ln(h_ref/h_i)``; for 60 characteristic strains (geometric,
    0.05 to 5) the model ``s0 + d*(1 - exp(-eps/eps_c)) + th4*eps`` is linear in (s0, d, th4)
    and solved by its normal equations (``th4`` fixed to 0 with 3 points); the best ``eps_c``
    is refined by a parabola in ``ln(eps_c)`` through its neighbours, repeated on the bracket
    until it settles (the first parabola's value is kept in the result). ValueError (message
    starting with the outcome name) below 3 points, for gauges that do not decrease, or when
    the normal equations are singular: no number is returned for an under-determined fit.
    Nothing is written into a case."""
    if strength_is not in FIT_STRENGTH_KINDS:
        raise ValueError(f'strength_is must be one of {FIT_STRENGTH_KINDS}')
    for name, v in (('gauges_m', gauges_m), ('strengths_pa', strengths_pa)):
        if isinstance(v, (str, bytes)) or not hasattr(v, '__iter__'):
            raise ValueError(f'{name} must be a list of numbers')
    hs = [_num(f'gauges_m[{i}]', h, positive=True, hi=0.1) for i, h in enumerate(gauges_m)]
    ys = [_num(f'strengths_pa[{i}]', y, positive=True, hi=5e9)
          for i, y in enumerate(strengths_pa)]
    if len(hs) != len(ys):
        raise ValueError('gauges_m and strengths_pa must have the same length')
    if len(hs) < 3:
        raise ValueError(f'{FIT_UNDERDETERMINED}: {len(hs)} points for at least 3 parameters '
                         '(s0, d, eps_c with th4 = 0)')
    if any(b >= a for a, b in zip(hs, hs[1:])):
        raise ValueError('gauges_m must be strictly decreasing')
    href = _num('reference_thickness_m', reference_thickness_m, positive=True, hi=0.1)
    if href < hs[0] * (1 - 1e-9):
        raise ValueError('reference_thickness_m must be >= the first gauge')
    prior = _num('prior_equivalent_strain', prior_equivalent_strain, nonnegative=True,
                 hi=100.0)
    k = 2 / math.sqrt(3)
    eps = [prior + k * math.log(href / h) for h in hs]
    with_slope = len(hs) > 3
    lo, hi, n = FIT_CHARACTERISTIC_STRAINS
    grid = [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]
    sols = [(ec, _voce_lsq(eps, ys, ec, with_slope)) for ec in grid]
    sols = [(ec, r) for ec, r in sols if r is not None]
    if not sols:
        raise ValueError(f'{FIT_SINGULAR}: the strains do not separate the parameters')
    i = min(range(len(sols)), key=lambda j: sols[j][1][2])
    ec, best = sols[i]
    refined, first = 0, None
    if 0 < i < len(sols) - 1:
        # parabola in ln(eps_c) through the best point and its neighbours; repeated on the
        # bracket until eps_c moves less than 1e-6 in ln (SPEC18 package 8 deviation, as the
        # joint fit of package 7: one parabola leaves eps_c ~5e-4 off and th4 ~1e-3 off)
        tri = [(math.log(e), r[2]) for e, r in sols[i - 1:i + 2]]
        for refined in range(1, FIT_PARABOLA_STEPS + 1):
            (x0, j0), (x1, j1), (x2, j2) = tri
            den = (x0 - x1) * (x0 - x2) * (x1 - x2)
            a = (x2 * (j1 - j0) + x1 * (j0 - j2) + x0 * (j2 - j1)) / den
            b = (x2 * x2 * (j0 - j1) + x1 * x1 * (j2 - j0) + x0 * x0 * (j1 - j2)) / den
            if not a > 0:
                refined -= 1
                break
            xv = min(max(-b / (2 * a), x0), x2)
            r = _voce_lsq(eps, ys, math.exp(xv), with_slope)
            if r is None:
                refined -= 1
                break
            if first is None:
                first = math.exp(xv)
            moved = abs(xv - math.log(ec))
            if r[2] <= best[2]:
                ec, best = math.exp(xv), r
            if moved < FIT_PARABOLA_TOL or xv in (x0, x1, x2):
                break
            pts3 = sorted(tri + [(xv, r[2])])
            k3 = min(range(1, 3), key=lambda q: pts3[q][1])
            tri = pts3[k3 - 1:k3 + 2]
    (s0, d, th4), res, sse = best
    flags = ['FIT_TO_ENTERED_STRENGTHS_NOT_VERIFIED']
    if len(hs) < 5:
        flags.append('FIT_UNDERDETERMINED_FEWER_THAN_5_POINTS')
    if strength_is == 'as_rolled_tensile':
        flags.append('TENSILE_STRENGTH_USED_AS_FLOW_STRESS')
    if th4 < 0:
        flags.append(NEGATIVE_SLOPE_FLAG)
    params = {'initial_stress_pa': s0, 'saturation_stress_pa': s0 + d,
              'characteristic_strain': ec, 'stage_iv_slope_pa': th4}
    try:
        VoceHardening(provenance='fit', **params).validate()
        valid = None
    except ValueError as exc:
        valid = str(exc)
    return _checked({
        'status': 'FITTED_TO_ENTERED_STRENGTHS_NOT_VERIFIED', 'law': 'voce',
        'parameters': params, 'equivalent_strains': eps, 'residuals_pa': res,
        'rms_residual_pa': math.sqrt(sse / len(hs)), 'points': len(hs),
        'parameters_fitted': 4 if with_slope else 3,
        'stage_iv_slope_sign': (th4 > 0) - (th4 < 0),
        'stage_iv_slope_fixed_to_zero': not with_slope,
        'parabola_steps': refined, 'first_parabola_characteristic_strain': first,
        'law_rejected_by_validation': valid,
        'strength_is': strength_is,
        'formula': 'sigma = s0 + d*(1 - exp(-eps/eps_c)) + th4*eps; eps = prior + '
                   '(2/sqrt(3))*ln(h_ref/h)',
        'basis': '[D, SPEC18 package 8] linear least squares in (s0, d, th4) for 60 eps_c from '
                 '0.05 to 5, the best refined by repeated parabolas in ln(eps_c)',
        'flags': flags,
        'limitations': [
            'The strengths are entered numbers; nothing verifies them.',
            'An as-rolled tensile strength of a hard temper is taken as the flow stress at '
            'that strain (an assumption [D]).' if strength_is == 'as_rolled_tensile' else
            'The entered values are taken as flow stresses.',
            'With fewer than 5 points the fit has no redundancy to check it.',
            'No recovery term: the gap row gives no formula for it.']})


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
    ``eps = prior + (2/sqrt(3))*ln(h_0/h)``. ``law`` is a ``PowerHardeningLaw``, a
    ``VoceHardening`` or a ``TomeVoceHardening``. Rate sensitivity is zero.
    """
    if not isinstance(law, (PowerHardeningLaw, VoceHardening, TomeVoceHardening)):
        raise ValueError('law must be a PowerHardeningLaw, VoceHardening or '
                         'TomeVoceHardening')
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
    if not is_power and law.stage_iv_slope_pa < 0:
        flags.append(NEGATIVE_SLOPE_FLAG)
    is_tome = isinstance(law, TomeVoceHardening)
    return _checked({
        'status': STATUS_HARDENING,
        'law_type': ('power_hardening' if is_power else
                     'tome_voce_stage_iv' if is_tome else 'voce_stage_iv'),
        'law': asdict(law), 'prior_equivalent_strain': prior,
        'final_equivalent_strain': final_strain, 'passes': passes,
        'formula': 'eps = prior + (2/sqrt(3))*ln(h_0/h); mean = (1/(eps1-eps0))*int sigma deps',
        'basis': {
            'strain_convention': '[D] same as physicroll.materials (homogeneous plane strain)',
            'law': ('PowerHardeningLaw reused from physicroll.materials; provenance: '
                    + law.provenance if is_power else
                    '[form: TM-LB4 EX] Tome-Voce form; parameters supplied: ' + law.provenance
                    if is_tome else
                    '[D] generalised Voce form; parameters supplied: ' + law.provenance),
            'rate_sensitivity': '[M] taken as zero (room-temperature m ~ 0.002-0.02)'},
        'reasons': [f'{len(passes)} passes to equivalent strain {final_strain:.3f}.'],
        'flags': flags,
        'limitations': [
            HOLLOMON_WARNING,
            'No redundant shear, recovery, ageing or temperature dependence between passes.',
            'Voce coefficients are never defaulted; they must be supplied and sourced.'],
        'sources': [SOURCES['kazaoka_2015'], SOURCES['hirsch'], SOURCES['ryen_2006']]})
