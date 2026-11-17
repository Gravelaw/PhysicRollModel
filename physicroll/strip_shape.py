"""Width-resolved strip shape: local roll bumps, crown heredity, flatness, ridges, troughs.

Opt-in, standard-library-only screening model for LENGTHWISE bands (bands that run along
the rolling direction at fixed width positions). Every quantity is SI; every public result
is a plain JSON-serialisable dict (or a float). Nothing here is plant-validated: results are
software-verified formula evaluations with labelled assumptions, not certified causes.
Independent of ``physicroll.roll_thermal`` (roll radius profiles come in as plain lists) and
of ``physicroll.chatter``.

Basis tags (carried into each result's ``formula_basis``/``threshold_basis``):
[V] read in a cited source, [D] derived by the project planner (re-derived here where
stated), [M] from memory / unverified.

Sign conventions
----------------
- ``z`` [m] is the across-width (barrel) coordinate. A positive radius deviation ``dR`` is
  a locally LARGER roll (hot stripe), which over-rolls the strip: ``dh < 0``.
- Elongation ``eps(z)`` > 0 = that fibre is relatively longer = "loose"; residual stress
  ``sigma_res = -E*(eps - mean(eps))`` is then compressive (negative). Tension positive.
- Lateral (cross-width) critical stresses for troughs/wrinkles are returned NEGATIVE
  (compressive), as in the source formulas.

W2.1 Local roll bump -> local thickness [D]
-------------------------------------------
Roll-surface compliance to a sinusoidal line load of wavelength ``lam`` along the barrel,
spread uniformly over the bite half-length ``a`` in the rolling direction (Boussinesq point
load integrated over the bite, displacement taken on the bite centre line), valid for
``2a << lam << R``::

    C(lam) = w*/f* = (2*(1-nu^2)/(pi*E)) * (ln(lam/(pi*a)) + (1 - gamma_Euler))   [m2/N]

``1 - gamma_Euler = 0.42278`` (re-derived here: the z-integral of ``cos(kz)/r`` is
``2*K0(k|x|)`` and ``K0(u) ~ -ln(u/2) - gamma``; averaging over ``|x| < a`` gives the
constant). Averaging the displacement over the bite as well would give ``+0.2297`` instead
(about 7 % lower C at lam = 50 mm, a = 2 mm); the bite-centre form is used. Plane-strain
check ``p* = pi*E_star*Delta/lam``: Johnson, Contact Mechanics s13.2 (read second-hand).
With strip stiffness per unit width ``Q = -d(F/width)/dh_exit`` [Pa] and ``n_rolls``
(1 or 2) rolls carrying the bump::

    T(lam) = 1/(1 + 2*C(lam)*Q)        (both roll surfaces deform under the extra load)
    dh_local(z) = -n_rolls * T * dR_local(z)

``transfer_radius_profile`` applies ``T`` per DFT component of the already de-trended local
deviation (periodic over the supplied window). Components with ``lam < 4a`` are attenuated
with ``T(4a)``; components with ``lam > R`` (including the mean) with ``T(R)``; short content
is flagged above 5 %, long content above 75 % of the spectrum energy (an isolated stripe of
width w always carries about 2w/R of its energy at wavelengths > R).

Exit-tension feedback [D, planner; re-derived here], optional: a locally over-rolled fibre
is longer, so its exit tension drops, which raises the local roll force and flattens the
bump. With ``N_x' = -d(F/width)/d(sigma_exit)`` [m] > 0::

    dp' = -Q*dh - N_x'*dsigma_x,  dsigma_x = -E_strip*eps,  eps = -xi*dh/h_exit
    => Q_eff = Q + N_x'*E_strip*xi/h_exit,   T(lam) = 1/(1 + 2*C(lam)*Q_eff)

Pointwise, so it applies per Fourier component like Q, except the mean (k = 0): a uniform
elongation does not change the reel-controlled mean tension, so k = 0 keeps Q (strictly,
``dsigma_x = -E*(eps - mean(eps))``). When the feedback term dominates,
``eps -> n_rolls*dR/(2*C*N_x'*E_strip)``, independent of gauge: the thin-gauge trend then
comes from the buckling stress (t^2) and the dead band, not from raw I-units. Entry-tension
redistribution is ignored (entry tension uniform); it would attenuate further. The feedback
needs a tensioned fibre: ``thermal_stripe_flatness`` caps it band-wise for slack (manifest)
bands (approximate, see there).

W2.2 Crown heredity, elongation, flatness
-----------------------------------------
- Heredity [V: Qu et al. 2025, eq. 4]: ``C_h = (1-eta)*C_gap + eta*(h/H)*C_H``.
- Differential elongation [M form; coefficient per US 5,927,117 V]:
  ``eps(z) = xi*(dH(z)/H_mean - dh(z)/h_mean)`` (arithmetic means over the samples).
- I-units [V: IHI; Vollmer 2019]: ``I(z) = 1e5*(eps(z) - mean(eps))``; sinusoidal wave
  ``I = (pi*H_w/(2*L_w))^2*1e5`` [V: QCA-1; Bailey].
- ``sigma_res(z) = -E*(eps(z) - mean(eps))`` (0.7 MPa per I-unit for E = 70 GPa) [D];
  local total ``sigma_T + sigma_res`` [V description of latent/manifest: Abdelkhalek et al.
  2008; Lloyd 2010]. In-mill criterion [D, planner]: only NET compression buckles;
  ``S = -min(sigma_T + sigma_res)`` over the band, LATENT if ``S <= 0``, else ``b`` = half-peak
  width of the net compression (interpolated edges; analyst choice) and MANIFEST_BUCKLE iff
  ``S >= sigma_cr(b)``. Near onset b shrinks with S, so onset S ~ t*sqrt(K*c/2) for stress
  curvature c. After tension release the compression is ``-sigma_res`` itself (same rule,
  ``S_rel``, ``b_rel``): this carries the t^2 gauge trend. Known weakness: an overshoot spike
  at a sharp stripe edge sets a narrow half-peak width and can hide a broad compressed
  plateau (see the test of the 3 um top-hat).
- Narrow-band buckling ``sigma_cr = k*pi^2*E/(12*(1-nu^2))*(t/b)^2``, k = 4 [M, Timoshenko].
- Shohet-Townsend dead band [V: Qu 2025; Zambrano et al. 2006; Hajduk & Bernardes 2009]:
  ``-80*(h/w)^beta < C_H/H - C_h/h < +40*(h/w)^beta``; beta 1.86 (attributed to Somers et
  al. 1984) or 2 (original).

W2.3 Coil ridge build-up [D criterion; V mechanism: Zhang 2016, Sun 2016, Melfo 2006]
------------------------------------------------------------------------------------
``N(R) = (R-R_i)/h``; ``dRad = c*N*r``; yield when ``dRad/R > (sigma_y - sigma_T)/E``;
``r_crit(R) = h*R*(sigma_y-sigma_T)/(E*c*(R-R_i))``; onset radius
``R_on = c*r*R_i/(c*r - s*h)`` with ``s = (sigma_y-sigma_T)/E`` (never if ``c*r <= s*h``);
affected wound-length fraction ``(R_o^2 - R_on^2)/(R_o^2 - R_i^2)``.

W2.4 Tension troughs and wrinkles
---------------------------------
Cerda & Mahadevan 2003 (reconstructed, cross-checked against Panaitescu et al.)::

    lam = sqrt(2*pi*L*t)/(3*(1-nu^2)*gamma)^(1/4),   gamma = sigma_x/E
    A   = sqrt(nu*L*t)*(16*gamma/(3*pi^2*(1-nu^2)))^(1/4)

Good, Beisel & Yurtcu 2009 (isotropic reduction): trough onset in a free span ``a``
``sigma_y_cr = -(pi*h/a)*sqrt(E*sigma_x/(3*(1-nu^2)))``; roller wrinkle on radius R
``sigma_y_cr = -E*h/(R*sqrt(3*(1-nu^2)))``.
Metal-strip creases (Jacques et al. 2007): roll crown/taper under tension buckles the span at
~1 MPa lateral compression, roll friction adds lateral compression and plastic ratcheting
forms a ~10 mm crease at a critical tension. Aluminium terms: longitudinal creases (pinch
marks, wrinkles) from idler/leveler rolls [V: QCA-1]; foil "grooves" from an unfavourable
flatness profile or deviating roll line [V: EAFA 2020].

W2.5 Helpers: two-tone band edges at earlier narrower strip edges [V: QCA-1]; grinding
feed pitch = traverse per revolution [V: EN 12258-1 grinding streak; trade sources];
spacing analysis and matching against candidate pitches (analyst tolerances).

Thin-gauge trend carried by this module: a fixed roll bump is a larger RELATIVE thickness
error on thinner strip (I ~ dR/h); the Shohet-Townsend dead band shrinks as (h/w)^beta so
lateral flow no longer absorbs crown changes; narrow-band buckling stress falls as t^2; the
critical coil ridge height and the trough threshold scale with h, the trough wavelength with
sqrt(h).

NOT modelled: lateral metal flow beyond the constant xi, entry-tension redistribution, the
exit-tension feedback beyond its linear form and an approximate band-wise saturation (and
not at all unless N_x' is supplied), shear lag of the tension field, roll
bending/backup-roll contact (crown model), post-buckling stress relief, plasticity of the
strip outside the bite, interlayer slip/pressure in coils, strip tracking/oscillation that
spreads ridges, temperature fields (see ``roll_thermal``), orthotropy and roll friction in
troughs. Analyst-chosen thresholds are labelled in each result's ``threshold_basis``.
"""
import cmath
import json
import math
import statistics

SOURCES = {
    'johnson_contact': 'Johnson, Contact Mechanics, s13.2 (plane-strain sinusoidal surface '
                       'check, read second-hand)',
    'qu_2025': 'Qu et al. (2025) ISIJ Int. 65(9), doi:10.2355/isijinternational.isijint-2024-371'
               ' (crown heredity eq. 4; Shohet-Townsend criterion)',
    'li_2022': 'Li et al. (2022) Int. J. Adv. Manuf. Technol., doi:10.1007/s00170-022-08997-5 '
               '(inheritance factor 0.03-0.50 across a tandem mill, 0.67 high-strength strip)',
    'us_5927117': 'US 5,927,117 (shape disturbing coefficient)',
    'ihi_sheetflat': 'IHI Sheetflat (I-unit definition; foil control within 6 I-units)',
    'vollmer_2019': 'Vollmer (2019) (I-unit definition; customer flatness 5-6 I-units)',
    'aa_qca1': 'Aluminum Association (2002) Visual Quality Characteristics of Aluminum Sheet '
               'and Plate QCA-1, 4th ed. (wave I-units, two-tone, creases)',
    'bailey': 'Bailey (I-units from wave height and wavelength)',
    'abdelkhalek_2008': 'Abdelkhalek et al. (2008) (latent vs manifest flatness defects)',
    'lloyd_2010': 'Lloyd (Lechler, 2010) "Fundamentals of roll cooling and control of flatness '
                  'at primary cold reduction"',
    'timoshenko_plate': 'Timoshenko plate buckling, k = 4 simply supported (quoted from memory)',
    'zambrano_2006': 'Zambrano et al. (2006) (Shohet-Townsend dead band)',
    'hajduk_2009': 'Hajduk & Bernardes (2009) (Shohet-Townsend dead band)',
    'somers_1984': 'Somers et al. (1984) (exponent 1.86, as attributed in later sources)',
    'lorin': 'Lorin (fabricator quoting the Aluminum Association flatness limit ~27 I-units)',
    'zhang_2016_lmi': 'Zhang et al. (2016) La Metallurgia Italiana (coil ridge build-up)',
    'sun_2016': 'Sun et al. (2016) IJSIMM (coil ridge build-up)',
    'melfo_2006': 'Melfo (2006) PhD thesis, University of Wollongong (ridge buckling; steel '
                  'criteria)',
    'zhu_2009': 'Zhu et al. (2009) (interwrap gap variation up to ~4 um under load)',
    'cerda_2003': 'Cerda & Mahadevan (2003) Phys. Rev. Lett. 90, 074302, '
                  'doi:10.1103/PhysRevLett.90.074302',
    'panaitescu': 'Panaitescu et al., arXiv:1906.10054 (cross-check of Cerda-Mahadevan)',
    'good_2009': 'Good, Beisel & Yurtcu (2009), doi:10.15376/frc.2009.1.517 (troughs and '
                 'roller wrinkles)',
    'jacques_2007': 'Jacques et al. (2007) J. Mater. Process. Technol. (strip creasing)',
    'eafa_2020': 'EAFA (2020) (foil grooves)',
    'en_12258_1': 'EN 12258-1 (grinding streak)',
}

GAMMA_EULER = 0.5772156649015329
COMPLIANCE_CONSTANT = 1.0 - GAMMA_EULER  # 0.42278, quoted as 0.4228 in the spec
I_UNIT = 1e-5
SHORT_WAVELENGTH_FACTOR = 4.0          # lam < 4a outside compliance validity (spec)
SPECTRUM_FLAG_FRACTION = 0.05          # analyst choice (spec), short-wavelength flag
LONG_WAVELENGTH_FLAG_FRACTION = 0.75   # raised from 0.05: isolated stripes carry ~2w/R
DEFAULT_REPORTING_THRESHOLD_I_UNITS = 2.0
DEFAULT_BETA = 1.86
SHOHET_UPPER_COEFFICIENT = 40.0
SHOHET_LOWER_COEFFICIENT = -80.0
PLATE_BUCKLING_COEFFICIENT = 4.0
DEFAULT_COMPACTION_FACTOR = 0.5
OBSERVED_SPACING_RATIO_BAND = (0.5, 2.0)
REGULAR_SPACING_CV_LIMIT = 0.1
MAX_DFT_POINTS = 2048
STEEL_E_PA, STEEL_NU = 210e9, 0.3
ALUMINIUM_E_PA, ALUMINIUM_NU = 70e9, 0.33
TOLERANCE_CONTEXT_I_UNITS = {
    'aluminum_association_limit_as_quoted_by_fabricator': 27.0,
    'mill_customer_1_to_3_mm_low': 5.0,
    'mill_customer_1_to_3_mm_high': 6.0,
    'foil_control_within': 6.0,
    'basis': 'Context only, not pass/fail [V: Lorin; Vollmer 2019; IHI Sheetflat].',
}
NOT_VALIDATED = ('Not plant-validated: a software-verified formula evaluation with labelled '
                 'assumptions, not a certified cause.')


# --------------------------------------------------------------------------- helpers
def _num(name, value, *, positive=False, nonnegative=False, lo=None, hi=None,
         lo_open=False, hi_open=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite SI number (not bool)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{name} must be > 0')
    if nonnegative and value < 0:
        raise ValueError(f'{name} must be >= 0')
    if lo is not None and (value <= lo if lo_open else value < lo):
        raise ValueError(f'{name} must be {">" if lo_open else ">="} {lo}')
    if hi is not None and (value >= hi if hi_open else value > hi):
        raise ValueError(f'{name} must be {"<" if hi_open else "<="} {hi}')
    return value


def _opt(name, value, **kw):
    return None if value is None else _num(name, value, **kw)


def _list(name, values, *, min_len=1, **kw):
    if not isinstance(values, (list, tuple)):
        raise ValueError(f'{name} must be a list of numbers')
    if len(values) < min_len:
        raise ValueError(f'{name} needs at least {min_len} values')
    return [_num(f'{name}[{i}]', v, **kw) for i, v in enumerate(values)]


def _grid(z_m, min_len=2):
    z = _list('z_m', z_m, min_len=min_len, lo=-100.0, hi=100.0)
    if any(b <= a for a, b in zip(z, z[1:])):
        raise ValueError('z_m must be strictly increasing')
    return z


def _uniform(z):
    n = len(z)
    dz = (z[-1] - z[0]) / (n - 1)
    return all(abs((b - a) - dz) <= 1e-6 * dz for a, b in zip(z, z[1:])), dz


def _n_rolls(value):
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2):
        raise ValueError('n_rolls must be the int 1 or 2')
    return value


def _modulus(name, value):
    return _num(name, value, lo=1e9, hi=1e13)


def _poisson(name, value):
    return _num(name, value, lo=0.0, hi=0.5, hi_open=True)


def _thickness(name, value):
    return _num(name, value, positive=True, hi=0.1)


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


def _mean(values):
    return math.fsum(values) / len(values)


# --------------------------------------------------------------------------- W2.1
def _compliance(lam, a, e, nu):
    return 2 * (1 - nu * nu) / (math.pi * e) * (math.log(lam / (math.pi * a))
                                                 + COMPLIANCE_CONSTANT)


def _transfer(lam, a, e, nu, q):
    return 1.0 / (1.0 + 2.0 * _compliance(lam, a, e, nu) * q)


def roll_line_compliance_m2_n(wavelength_m, bite_half_length_m,
                              youngs_modulus_pa=STEEL_E_PA, poisson_ratio=STEEL_NU):
    """Roll-surface compliance ``C(lam)`` [m2/N] to a sinusoidal line load [D].

    ``C = (2*(1-nu^2)/(pi*E))*(ln(lam/(pi*a)) + 0.4228)``; requires ``lam >= 4a``.
    """
    lam = _num('wavelength_m', wavelength_m, positive=True, hi=100.0)
    a = _num('bite_half_length_m', bite_half_length_m, positive=True, hi=0.1)
    e = _modulus('youngs_modulus_pa', youngs_modulus_pa)
    nu = _poisson('poisson_ratio', poisson_ratio)
    if lam < SHORT_WAVELENGTH_FACTOR * a:
        raise ValueError('wavelength_m must be >= 4*bite_half_length_m (compliance validity)')
    return _compliance(lam, a, e, nu)


def _transfer_limitations(feedback=False):
    fb = ('Exit-tension feedback included as a linear effective stiffness (elastic, unbuckled '
          'fibres); entry tension is assumed uniform (its redistribution, ignored, would '
          'attenuate further) and the exit-side compatibility is local (no shear lag).'
          if feedback else
          'No feedback of the local tension redistribution on the local roll force; in a '
          'real bite it opposes the thickness change, so dh is an upper estimate for the '
          'given Q (pass exit_tension_force_sensitivity_per_width_m to include it).')
    return ['Half-space compliance (2a << lam << R): roll bending, backup-roll contact and '
            'the finite roll radius are outside it.', fb,
            'The strip stiffness per unit width Q (and N_x\', if used) is supplied; it is not '
            'computed here.',
            NOT_VALIDATED]


def _feedback(sensitivity_m, exit_thickness_m, strip_youngs_modulus_pa, xi):
    """Return ``(N_x', N_x'*E_strip*xi/h_exit)`` or ``(None, 0.0)`` when feedback is off."""
    if sensitivity_m is None:
        return None, 0.0
    nx = _num('exit_tension_force_sensitivity_per_width_m', sensitivity_m, positive=True,
              hi=10.0)
    if exit_thickness_m is None:
        raise ValueError('exit_thickness_m is required with '
                         'exit_tension_force_sensitivity_per_width_m')
    h = _thickness('exit_thickness_m', exit_thickness_m)
    e = _modulus('strip_youngs_modulus_pa', strip_youngs_modulus_pa)
    x = _num('xi', xi, lo=0.0, hi=1.0, lo_open=True)
    return nx, nx * e * x / h


def _feedback_keys(q, nx, q_fb):
    return {'effective_strip_stiffness_per_width_pa': q + q_fb,
            'tension_feedback_applied': nx is not None,
            'tension_feedback_stiffness_per_width_pa': q_fb,
            'exit_tension_force_sensitivity_per_width_m': nx}


FEEDBACK_BASIS = ('[D] planner: dp\' = -Q*dh - N_x\'*dsigma_x, dsigma_x = -E*eps, '
                  'eps = -xi*dh/h -> Q_eff = Q + N_x\'*E*xi/h')


def local_bump_transfer(wavelength_m, bite_half_length_m, strip_stiffness_per_width_pa, *,
                        n_rolls=2, roll_youngs_modulus_pa=STEEL_E_PA,
                        roll_poisson_ratio=STEEL_NU, roll_radius_m=None,
                        radius_deviation_m=None,
                        exit_tension_force_sensitivity_per_width_m=None,
                        exit_thickness_m=None, strip_youngs_modulus_pa=ALUMINIUM_E_PA, xi=1.0):
    """Transfer factor ``T = 1/(1+2*C*Q_eff)`` of a sinusoidal roll bump into thickness [D].

    ``dh = -n_rolls*T*dR``. ``Q_eff = Q`` unless the exit-tension feedback is switched on
    with ``exit_tension_force_sensitivity_per_width_m`` (N_x' [m], needs ``exit_thickness_m``):
    then ``Q_eff = Q + N_x'*E_strip*xi/h_exit``. Optional ``radius_deviation_m`` gives the
    thickness change; optional ``roll_radius_m`` flags ``lam > R`` (crown model).
    """
    lam = _num('wavelength_m', wavelength_m, positive=True, hi=100.0)
    a = _num('bite_half_length_m', bite_half_length_m, positive=True, hi=0.1)
    q = _num('strip_stiffness_per_width_pa', strip_stiffness_per_width_pa, positive=True,
             hi=1e14)
    n = _n_rolls(n_rolls)
    radius = _opt('roll_radius_m', roll_radius_m, positive=True, hi=5.0)
    dr = _opt('radius_deviation_m', radius_deviation_m, lo=-1e-3, hi=1e-3)
    nx, q_fb = _feedback(exit_tension_force_sensitivity_per_width_m, exit_thickness_m,
                         strip_youngs_modulus_pa, xi)
    q_eff = q + q_fb
    c = roll_line_compliance_m2_n(lam, a, roll_youngs_modulus_pa, roll_poisson_ratio)
    t = 1.0 / (1.0 + 2.0 * c * q_eff)
    t_c = 1.0 / (1.0 + 2.0 * c * q)
    flags = ['RESTS_ON_PLANNER_DERIVED_FORMULA']
    if nx is not None:
        flags.append('EXIT_TENSION_FEEDBACK_LINEAR')
    if radius is not None and lam > radius:
        flags.append('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL')
    reasons = [f'Compliance {c:.3e} m2/N x stiffness {q_eff:.3e} Pa: 2CQ = '
               f'{2 * c * q_eff:.3f}, so {t:.3f} of the radius deviation on each of {n} '
               'roll(s) reaches the strip.']
    if nx is not None:
        reasons.append(f'Exit-tension feedback adds {q_fb:.3e} Pa to Q = {q:.3e} Pa '
                       f'(compliance-only transfer {t_c:.3f}).')
    return _checked({
        'status': 'UNVALIDATED_LOCAL_TRANSFER_ESTIMATE',
        'wavelength_m': lam, 'bite_half_length_m': a, 'n_rolls': n,
        'roll_radius_m': radius, 'compliance_m2_n': c, 'strip_stiffness_per_width_pa': q,
        **_feedback_keys(q, nx, q_fb),
        'compliance_stiffness_product': 2 * c * q_eff, 'transfer_factor': t,
        'compliance_only_transfer_factor': t_c,
        'thickness_change_per_radius_deviation': -n * t,
        'rigid_thickness_change_per_radius_deviation': float(-n),
        'radius_deviation_m': dr,
        'local_thickness_change_m': None if dr is None else -n * t * dr,
        'rigid_local_thickness_change_m': None if dr is None else -n * dr,
        'formula_basis': {'compliance': '[D] Boussinesq over the bite; Johnson s13.2 check',
                          'transfer': '[D] T = 1/(1+2*C*Q_eff), dh = -n*T*dR',
                          'tension_feedback': FEEDBACK_BASIS},
        'threshold_basis': 'Validity lam >= 4a enforced; lam > R flagged (spec choices) [D].',
        'reasons': reasons, 'flags': flags,
        'limitations': _transfer_limitations(nx is not None),
        'sources': [SOURCES['johnson_contact']]})


def _dft(x, sign=-1):
    n = len(x)
    tw = [cmath.exp(sign * 2j * math.pi * m / n) for m in range(n)]
    return [sum(x[j] * tw[(j * k) % n] for j in range(n)) for k in range(n)]


def transfer_radius_profile(z_m, local_radius_deviation_m, *, bite_half_length_m,
                            strip_stiffness_per_width_pa, roll_radius_m, n_rolls=2,
                            roll_youngs_modulus_pa=STEEL_E_PA, roll_poisson_ratio=STEEL_NU,
                            exit_tension_force_sensitivity_per_width_m=None,
                            exit_thickness_m=None, strip_youngs_modulus_pa=ALUMINIUM_E_PA,
                            xi=1.0):
    """Apply ``T(lam)`` per DFT component of a de-trended local radius deviation [D].

    ``z_m`` must be uniformly spaced (the window is treated as one period). Components with
    ``lam < 4a`` use ``T(4a)``, with ``lam > R`` (and the mean) use ``T(R)``. Short content is
    flagged above 5 %, long content above 75 % of the spectrum energy. With the exit-tension
    feedback on, every non-zero component uses ``Q_eff``; the mean (k = 0) keeps ``Q`` because
    a uniform elongation does not redistribute the reel-controlled mean tension.
    """
    z = _grid(z_m, min_len=4)
    dr = _list('local_radius_deviation_m', local_radius_deviation_m, min_len=4,
               lo=-1e-3, hi=1e-3)
    if len(dr) != len(z):
        raise ValueError('local_radius_deviation_m must have the same length as z_m')
    if len(z) > MAX_DFT_POINTS:
        raise ValueError(f'at most {MAX_DFT_POINTS} points (plain O(N^2) DFT)')
    uniform, dz = _uniform(z)
    if not uniform:
        raise ValueError('z_m must be uniformly spaced for the DFT transfer')
    a = _num('bite_half_length_m', bite_half_length_m, positive=True, hi=0.1)
    q = _num('strip_stiffness_per_width_pa', strip_stiffness_per_width_pa, positive=True,
             hi=1e14)
    radius = _num('roll_radius_m', roll_radius_m, positive=True, hi=5.0)
    n_r = _n_rolls(n_rolls)
    e = _modulus('roll_youngs_modulus_pa', roll_youngs_modulus_pa)
    nu = _poisson('roll_poisson_ratio', roll_poisson_ratio)
    nx, q_fb = _feedback(exit_tension_force_sensitivity_per_width_m, exit_thickness_m,
                         strip_youngs_modulus_pa, xi)
    q_eff = q + q_fb
    lam_short = SHORT_WAVELENGTH_FACTOR * a
    if radius <= lam_short:
        raise ValueError('roll_radius_m must exceed 4*bite_half_length_m')
    n = len(z)
    period = n * dz
    spectrum = _dft(dr)
    gains, energy = [], []
    e_short = e_long = 0.0
    t_used = []
    for k in range(n):
        kk = min(k, n - k)
        lam = math.inf if kk == 0 else period / kk
        p = abs(spectrum[k]) ** 2
        energy.append(p)
        if lam < lam_short:
            e_short += p
            lam_eff = lam_short
        elif lam > radius:
            e_long += p
            lam_eff = radius
        else:
            lam_eff = lam
        t = _transfer(lam_eff, a, e, nu, q if kk == 0 else q_eff)
        t_used.append(t)
        gains.append(-n_r * t)
    total = math.fsum(energy)
    out = _dft([g * s for g, s in zip(gains, spectrum)], sign=+1)
    dh = [v.real / n for v in out]
    f_short = e_short / total if total > 0 else 0.0
    f_long = e_long / total if total > 0 else 0.0
    t_weighted = (math.fsum(t * p for t, p in zip(t_used, energy)) / total
                  if total > 0 else _transfer(radius, a, e, nu, q_eff))
    flags = ['RESTS_ON_PLANNER_DERIVED_FORMULA', 'PERIODIC_WINDOW_DFT']
    if nx is not None:
        flags.append('EXIT_TENSION_FEEDBACK_LINEAR')
    if f_short > SPECTRUM_FLAG_FRACTION:
        flags.append('SHORT_WAVELENGTH_OUTSIDE_COMPLIANCE_VALIDITY')
    if f_long > LONG_WAVELENGTH_FLAG_FRACTION:
        flags.append('LONG_WAVELENGTH_BELONGS_TO_CROWN_MODEL')
    i_pk = max(range(n), key=lambda i: abs(dr[i]))
    j_pk = max(range(n), key=lambda i: abs(dh[i]))
    peak_dr, peak_dh = dr[i_pk], dh[j_pk]
    ratio = peak_dh / (-n_r * peak_dr) if peak_dr != 0 else None
    reasons = [f'Energy-weighted transfer factor {t_weighted:.3f}; peak thickness change '
               f'{peak_dh:.3e} m from peak radius deviation {peak_dr:.3e} m on {n_r} roll(s).',
               f'Spectrum energy below lam = 4a ({lam_short:.4f} m): {f_short:.3f}; above '
               f'lam = R ({radius:.4f} m, incl. mean): {f_long:.3f}. An isolated stripe of '
               'width w carries roughly 2w/R of its energy at wavelengths > R; those '
               'components are clamped to T(R).']
    if nx is not None:
        reasons.append(f'Exit-tension feedback: Q_eff = {q_eff:.3e} Pa (Q = {q:.3e} Pa).')
    return _checked({
        'status': 'UNVALIDATED_LOCAL_TRANSFER_ESTIMATE',
        'z_m': z, 'local_radius_deviation_m': dr, 'local_thickness_change_m': dh,
        'rigid_local_thickness_change_m': [-n_r * v for v in dr],
        'n_rolls': n_r, 'sample_spacing_m': dz, 'period_m': period,
        'nyquist_wavelength_m': 2 * dz, 'short_wavelength_limit_m': lam_short,
        'long_wavelength_limit_m': radius,
        'strip_stiffness_per_width_pa': q, **_feedback_keys(q, nx, q_fb),
        'short_wavelength_energy_fraction': f_short, 'long_wavelength_energy_fraction': f_long,
        'transfer_factor_min': min(t_used), 'transfer_factor_max': max(t_used),
        'energy_weighted_transfer_factor': t_weighted,
        'peak_radius_deviation_m': peak_dr, 'peak_local_thickness_change_m': peak_dh,
        'peak_transfer_ratio': ratio,
        'formula_basis': {'transfer': '[D] dh_k = -n*T(lam_k)*dR_k per DFT component',
                          'tension_feedback': FEEDBACK_BASIS + '; k = 0 keeps Q'},
        'threshold_basis': 'lam < 4a -> T(4a), lam > R -> T(R); flags above 5 % (short) / '
                           '75 % (long) of the spectrum energy (spec/analyst choices) [D].',
        'reasons': reasons, 'flags': flags,
        'limitations': _transfer_limitations(nx is not None)
        + ['The DFT treats the window as periodic: content near one end wraps to the other.'],
        'sources': [SOURCES['johnson_contact']]})


# --------------------------------------------------------------------------- W2.2
def crown_heredity(gap_crown_m, entry_crown_m, entry_thickness_m, exit_thickness_m,
                   heredity_coefficient):
    """Exit crown ``C_h = (1-eta)*C_gap + eta*(h/H)*C_H`` [V: Qu 2025 eq. 4]."""
    cg = _num('gap_crown_m', gap_crown_m, lo=-1e-3, hi=1e-3)
    ce = _num('entry_crown_m', entry_crown_m, lo=-1e-3, hi=1e-3)
    big_h = _thickness('entry_thickness_m', entry_thickness_m)
    h = _thickness('exit_thickness_m', exit_thickness_m)
    if h > big_h:
        raise ValueError('exit_thickness_m must not exceed entry_thickness_m')
    eta = _num('heredity_coefficient', heredity_coefficient, lo=0.0, hi=1.0)
    ch = (1 - eta) * cg + eta * (h / big_h) * ce
    delta = ce / big_h - ch / h
    return _checked({
        'status': 'UNVALIDATED_CROWN_HEREDITY_ESTIMATE',
        'exit_crown_m': ch, 'gap_crown_m': cg, 'entry_crown_m': ce,
        'proportional_crown_m': (h / big_h) * ce, 'heredity_coefficient': eta,
        'entry_relative_crown': ce / big_h, 'exit_relative_crown': ch / h,
        'relative_crown_change': delta, 'relative_crown_change_i_units': delta / I_UNIT,
        'formula_basis': {'heredity': '[V] Qu et al. 2025 eq. 4'},
        'threshold_basis': 'No threshold; eta is supplied (0.03-0.50 across a steel tandem '
                           'mill, 0.67 high-strength strip [V: Li et al. 2022]).',
        'reasons': ['eta -> 1 (thin hard strip) keeps the relative crown, i.e. no crown-'
                    'driven elongation; eta -> 0 imposes the gap crown.'],
        'flags': [], 'limitations': ['Single centre-minus-edge crown number; no profile '
                                     'shape or edge drop.', NOT_VALIDATED],
        'sources': [SOURCES['qu_2025'], SOURCES['li_2022']]})


def shohet_townsend_window(thickness_m, width_m, beta=DEFAULT_BETA):
    """Flatness dead band ``-80*(h/w)^beta < C_H/H - C_h/h < 40*(h/w)^beta`` [V]."""
    h = _thickness('thickness_m', thickness_m)
    w = _num('width_m', width_m, positive=True, hi=10.0)
    b = _num('beta', beta, lo=1.0, hi=3.0)
    if h >= w:
        raise ValueError('thickness_m must be below width_m')
    s = (h / w) ** b
    up, low = SHOHET_UPPER_COEFFICIENT * s, SHOHET_LOWER_COEFFICIENT * s
    return _checked({
        'status': 'LITERATURE_CRITERION_EVALUATED',
        'thickness_m': h, 'width_m': w, 'beta': b, 'thickness_to_width_ratio': h / w,
        'upper_bound': up, 'lower_bound': low,
        'upper_bound_i_units': up / I_UNIT, 'lower_bound_i_units': low / I_UNIT,
        'formula_basis': {'window': '[V] Shohet-Townsend as given by Qu 2025, Zambrano 2006, '
                                    'Hajduk & Bernardes 2009'},
        'threshold_basis': 'beta = 1.86 is attributed to Somers et al. 1984, beta = 2 is the '
                           'original; the default 1.86 is a choice, the sources disagree.',
        'reasons': [f'Dead band {low:.3e} .. {up:.3e} ({low / I_UNIT:.2f} .. '
                    f'{up / I_UNIT:.2f} I-units) for h/w = {h / w:.3e}; it shrinks as '
                    f'(h/w)^{b:g}, so thin strip turns any relative crown change into '
                    'elongation.'],
        'flags': [],
        'limitations': ['Quantity is entry minus exit relative crown; above the upper bound '
                        'centre buckle, below the lower edge wave. Zambrano et al. 2006 is '
                        'internally inconsistent about this sign.',
                        'Empirical criterion for wide strip; no alloy dependence.',
                        NOT_VALIDATED],
        'sources': [SOURCES['qu_2025'], SOURCES['zambrano_2006'], SOURCES['hajduk_2009'],
                    SOURCES['somers_1984']]})


def classify_crown_change(entry_crown_m, entry_thickness_m, exit_crown_m, exit_thickness_m,
                          width_m, beta=DEFAULT_BETA):
    """Compare ``C_H/H - C_h/h`` with the Shohet-Townsend window at the exit thickness."""
    ce = _num('entry_crown_m', entry_crown_m, lo=-1e-3, hi=1e-3)
    big_h = _thickness('entry_thickness_m', entry_thickness_m)
    ch = _num('exit_crown_m', exit_crown_m, lo=-1e-3, hi=1e-3)
    h = _thickness('exit_thickness_m', exit_thickness_m)
    win = shohet_townsend_window(h, width_m, beta)
    delta = ce / big_h - ch / h
    if delta > win['upper_bound']:
        status, reason = 'CENTRE_BUCKLE_RISK', 'centre relatively over-reduced (centre long)'
    elif delta < win['lower_bound']:
        status, reason = 'EDGE_WAVE_RISK', 'edges relatively over-reduced (edges long)'
    else:
        status, reason = 'WITHIN_DEAD_BAND', 'lateral flow can absorb the change'
    excess = (delta - win['upper_bound'] if delta > win['upper_bound']
              else delta - win['lower_bound'] if delta < win['lower_bound'] else 0.0)
    return _checked({
        'status': status, 'relative_crown_change': delta,
        'relative_crown_change_i_units': delta / I_UNIT,
        'excess_beyond_window': excess, 'excess_beyond_window_i_units': excess / I_UNIT,
        'window': {k: win[k] for k in ('upper_bound', 'lower_bound', 'upper_bound_i_units',
                                       'lower_bound_i_units', 'beta',
                                       'thickness_to_width_ratio')},
        'formula_basis': win['formula_basis'], 'threshold_basis': win['threshold_basis'],
        'reasons': [f'Relative crown change {delta:.3e} ({delta / I_UNIT:.2f} I-units): '
                    f'{reason}.'],
        'flags': [], 'limitations': win['limitations'], 'sources': win['sources']})


def differential_elongation(z_m, entry_profile_m, exit_profile_m, *, xi=1.0):
    """``eps(z) = xi*(dH/H_mean - dh/h_mean)`` from entry/exit thickness profiles [M form].

    Profiles are absolute thicknesses on the same ``z`` grid; means are arithmetic over the
    samples (equally spaced samples assumed; non-uniform grids are flagged).
    """
    z = _grid(z_m)
    entry = _list('entry_profile_m', entry_profile_m, min_len=2, positive=True, hi=0.1)
    exit_ = _list('exit_profile_m', exit_profile_m, min_len=2, positive=True, hi=0.1)
    if not len(z) == len(entry) == len(exit_):
        raise ValueError('z_m, entry_profile_m and exit_profile_m must have equal length')
    x = _num('xi', xi, lo=0.0, hi=1.0, lo_open=True)
    hm, em = _mean(entry), _mean(exit_)
    rel_in = [(v - hm) / hm for v in entry]
    rel_out = [(v - em) / em for v in exit_]
    eps = [x * (a - b) for a, b in zip(rel_in, rel_out)]
    flags = ['FORMULA_FORM_FROM_MEMORY']
    if not _uniform(z)[0]:
        flags.append('NONUNIFORM_GRID_ARITHMETIC_MEAN')
    return _checked({
        'status': 'UNVALIDATED_ELONGATION_ESTIMATE', 'z_m': z, 'elongation': eps,
        'entry_mean_thickness_m': hm, 'exit_mean_thickness_m': em,
        'entry_relative_profile': rel_in, 'exit_relative_profile': rel_out, 'xi': x,
        'formula_basis': {'elongation': '[M] form; xi per US 5,927,117 [V]'},
        'threshold_basis': 'xi = 1 (no lateral flow) is appropriate for thin wide strip; '
                           'supplied value.',
        'reasons': ['Positive elongation = fibre rolled relatively thinner = longer (loose).'],
        'flags': flags,
        'limitations': ['Constant xi; no width-dependent lateral flow near the edges.',
                        NOT_VALIDATED],
        'sources': [SOURCES['us_5927117']]})


def narrow_band_buckling_stress_pa(thickness_m, band_width_m, youngs_modulus_pa=ALUMINIUM_E_PA,
                                   poisson_ratio=ALUMINIUM_NU,
                                   buckling_coefficient=PLATE_BUCKLING_COEFFICIENT):
    """Compressive buckling stress magnitude ``k*pi^2*E/(12*(1-nu^2))*(t/b)^2`` [M]."""
    t = _thickness('thickness_m', thickness_m)
    b = _num('band_width_m', band_width_m, positive=True, hi=10.0)
    e = _modulus('youngs_modulus_pa', youngs_modulus_pa)
    nu = _poisson('poisson_ratio', poisson_ratio)
    k = _num('buckling_coefficient', buckling_coefficient, positive=True, hi=100.0)
    return k * math.pi ** 2 * e / (12 * (1 - nu * nu)) * (t / b) ** 2


def i_units_from_wave(wave_height_m, wavelength_m):
    """``I = (pi*H/(2*L))^2*1e5`` for a sinusoidal wave, peak-to-valley H [V: QCA-1; Bailey]."""
    hw = _num('wave_height_m', wave_height_m, nonnegative=True, hi=1.0)
    lw = _num('wavelength_m', wavelength_m, positive=True, hi=100.0)
    return (math.pi * hw / (2 * lw)) ** 2 / I_UNIT


def i_units_to_stress_pa(i_units, youngs_modulus_pa=ALUMINIUM_E_PA):
    """Stress equivalent ``E*I*1e-5`` (0.7 MPa per I-unit at 70 GPa) [D]; sign follows I."""
    i = _num('i_units', i_units, lo=-1e6, hi=1e6)
    return _modulus('youngs_modulus_pa', youngs_modulus_pa) * i * I_UNIT


def _bands(z, i_units, thr):
    n = len(z)
    bands, k = [], 0
    while k < n:
        if abs(i_units[k]) <= thr:
            k += 1
            continue
        sign = 1 if i_units[k] > 0 else -1
        j = k
        while j + 1 < n and abs(i_units[j + 1]) > thr and (i_units[j + 1] > 0) == (sign > 0):
            j += 1
        start = (z[k] + z[k - 1]) / 2 if k > 0 else z[0] - (z[1] - z[0]) / 2
        end = (z[j] + z[j + 1]) / 2 if j < n - 1 else z[-1] + (z[-1] - z[-2]) / 2
        p = max(range(k, j + 1), key=lambda m: abs(i_units[m]))
        bands.append((k, j, start, end, p, sign))
        k = j + 1
    return bands


def _half_peak_width(z, comp, p):
    """Width around ``p`` where ``comp >= comp[p]/2`` (comp > 0 = compression), edges
    linearly interpolated between samples; at the grid ends half a spacing is added."""
    level = comp[p] / 2
    n = len(z)
    i = p
    while i > 0 and comp[i - 1] >= level:
        i -= 1
    if i == 0:
        left = z[0] - (z[1] - z[0]) / 2
    else:
        f = (level - comp[i - 1]) / (comp[i] - comp[i - 1])
        left = z[i - 1] + f * (z[i] - z[i - 1])
    j = p
    while j < n - 1 and comp[j + 1] >= level:
        j += 1
    if j == n - 1:
        right = z[-1] + (z[-1] - z[-2]) / 2
    else:
        f = (comp[j] - level) / (comp[j] - comp[j + 1])
        right = z[j] + f * (z[j + 1] - z[j])
    return right - left


def flatness_from_elongation(z_m, elongation, *, youngs_modulus_pa, poisson_ratio, thickness_m,
                             mean_tension_pa,
                             reporting_threshold_i_units=DEFAULT_REPORTING_THRESHOLD_I_UNITS,
                             buckling_coefficient=PLATE_BUCKLING_COEFFICIENT,
                             yield_stress_pa=None):
    """I-unit and residual-stress profiles plus in-mill and tension-released band states.

    ``I = 1e5*(eps - mean)``; ``sigma_res = -E*(eps - mean)``. Bands are contiguous |I| above
    the reporting threshold (one sign). In the mill only NET compression can buckle: with
    ``S = -min(sigma_T + sigma_res)`` over the band, a band is LATENT if ``S <= 0``; otherwise
    ``b`` is the half-peak width of the net compression (interpolated edges) and the band is
    MANIFEST_BUCKLE iff ``S >= sigma_cr(b)``. After tension release the compression is the
    residual stress itself: ``S_rel = -min(sigma_res)``, ``b_rel`` its half-peak width,
    MANIFEST_AFTER_TENSION_RELEASE iff ``S_rel >= sigma_cr(b_rel)``.
    """
    z = _grid(z_m)
    eps = _list('elongation', elongation, min_len=2, lo=-0.5, hi=0.5)
    if len(eps) != len(z):
        raise ValueError('elongation must have the same length as z_m')
    e = _modulus('youngs_modulus_pa', youngs_modulus_pa)
    nu = _poisson('poisson_ratio', poisson_ratio)
    t = _thickness('thickness_m', thickness_m)
    sig_t = _num('mean_tension_pa', mean_tension_pa, nonnegative=True, hi=2e9)
    thr = _num('reporting_threshold_i_units', reporting_threshold_i_units, nonnegative=True,
               hi=1e4)
    k_b = _num('buckling_coefficient', buckling_coefficient, positive=True, hi=100.0)
    sy = _opt('yield_stress_pa', yield_stress_pa, positive=True, hi=5e9)
    m = _mean(eps)
    dev = [v - m for v in eps]
    iu = [d / I_UNIT for d in dev]
    resid = [-e * d for d in dev]
    total = [sig_t + r for r in resid]
    comp_mill = [-v for v in total]
    comp_rel = [-v for v in resid]
    bands = []
    for k, j, start, end, p, sign in _bands(z, iu, thr):
        width = end - start
        q = min(range(k, j + 1), key=lambda i: total[i])   # most compressed sample
        s_net = comp_mill[q]
        if s_net > 0:
            b_eff = _half_peak_width(z, comp_mill, q)
            s_cr = narrow_band_buckling_stress_pa(t, b_eff, e, nu, k_b)
            basis = 'NET_COMPRESSION_HALF_PEAK_WIDTH'
            manifest = s_net >= s_cr
        else:
            b_eff = None
            s_cr = narrow_band_buckling_stress_pa(t, width, e, nu, k_b)
            basis = 'REPORTING_CONTOUR_WIDTH_NOT_IN_NET_COMPRESSION'
            manifest = False
        s_rel = comp_rel[q]
        if s_rel > 0:
            b_rel = _half_peak_width(z, comp_rel, q)
            s_cr_rel = narrow_band_buckling_stress_pa(t, b_rel, e, nu, k_b)
            released = s_rel >= s_cr_rel
        else:
            b_rel = s_cr_rel = None
            released = False
        bands.append({
            'start_m': start, 'end_m': end, 'center_m': (start + end) / 2, 'width_m': width,
            'peak_position_m': z[p], 'peak_i_units': iu[p],
            'sense': 'LOOSE_LONG' if sign > 0 else 'TIGHT_SHORT',
            'residual_stress_at_peak_pa': resid[p], 'local_total_stress_pa': total[p],
            'band_buckling_stress_pa': s_cr,
            'band_buckling_width_basis': basis,
            'buckling_margin_pa': total[q] + s_cr,
            'net_compression_peak_pa': s_net,
            'effective_buckling_width_m': b_eff,
            'state': 'MANIFEST_BUCKLE' if manifest else 'LATENT_UNDER_TENSION',
            'released_compression_peak_pa': s_rel,
            'released_buckling_width_m': b_rel,
            'released_buckling_stress_pa': s_cr_rel,
            'state_after_tension_release': ('MANIFEST_AFTER_TENSION_RELEASE' if released
                                            else 'FLAT_AFTER_TENSION_RELEASE')})
    if any(b['state'] == 'MANIFEST_BUCKLE' for b in bands):
        status = 'MANIFEST_BUCKLE_BANDS'
    elif bands:
        status = 'LATENT_BANDS_UNDER_TENSION'
    else:
        status = 'NO_BANDS_ABOVE_THRESHOLD'
    n_rel = sum(1 for b in bands
                if b['state_after_tension_release'] == 'MANIFEST_AFTER_TENSION_RELEASE')
    released_status = 'MANIFEST_AFTER_RELEASE_BANDS' if n_rel else 'FLAT_AFTER_RELEASE'
    flags = ['BUCKLING_FORMULA_FROM_MEMORY', 'RESIDUAL_STRESS_RELATION_PLANNER_DERIVED',
             'HALF_PEAK_BUCKLING_WIDTH_ANALYST_CHOICE']
    if not _uniform(z)[0]:
        flags.append('NONUNIFORM_GRID_ARITHMETIC_MEAN')
    if sy is not None and max(abs(v) for v in total) > sy:
        flags.append('STRESS_EXCEEDS_YIELD_ELASTIC_RESULT_INDICATIVE_ONLY')
    loose = [b for b in bands if b['sense'] == 'LOOSE_LONG']
    reasons = [f'{len(bands)} band(s) above {thr:g} I-units ({len(loose)} loose); peak '
               f'{max(iu):.2f} / min {min(iu):.2f} I-units under mean tension '
               f'{sig_t / 1e6:.3f} MPa.',
               'Latent bands stay flat under tension (stress stripes on a shapemeter); only '
               'net compression can buckle in the mill.',
               f'{n_rel} band(s) buckle once tension is released (coil surface, slitter, '
               'inspection table): the released buckling stress falls as t^2.']
    return _checked({
        'status': status, 'released_status': released_status,
        'z_m': z, 'i_units': iu, 'residual_stress_pa': resid,
        'total_stress_pa': total, 'mean_elongation': m,
        'max_i_units': max(iu), 'min_i_units': min(iu),
        'peak_to_peak_i_units': max(iu) - min(iu), 'bands': bands,
        'manifest_band_count': sum(1 for b in bands if b['state'] == 'MANIFEST_BUCKLE'),
        'manifest_after_release_band_count': n_rel,
        'mean_tension_pa': sig_t, 'thickness_m': t,
        'reporting_threshold_i_units': thr, 'buckling_coefficient': k_b,
        'stress_per_i_unit_pa': e * I_UNIT,
        'tolerance_context_i_units': dict(TOLERANCE_CONTEXT_I_UNITS),
        'formula_basis': {'i_units': '[V] IHI; Vollmer 2019',
                          'residual_stress': '[D] sigma_res = -E*(eps - mean)',
                          'buckling': '[M] Timoshenko plate, k = 4 simply supported',
                          'latent_manifest': '[V description] Abdelkhalek 2008; Lloyd 2010',
                          'net_compression_width': '[D] planner: half-peak width of the net '
                                                   '(in-mill) or residual (released) '
                                                   'compression'},
        'threshold_basis': f'Reporting threshold {thr:g} I-units (analyst choice) delimits '
                           'bands only; buckling width = half-peak width of the net '
                           'compression in the mill, of the residual compression after '
                           'release (ANALYST_CHOICE, interpolated edges); the reporting-'
                           'contour width is used for sigma_cr only when a band is not in net '
                           'compression; k = 4 ignores the elastic restraint of neighbours '
                           '(conservative) [M].',
        'reasons': reasons, 'flags': flags,
        'limitations': ['Linear elastic flat-strip stresses: after buckling the real stress is '
                        'relieved and the residual stress shown is the would-be value.',
                        'The buckling stress depends on the half-peak compression width as '
                        '(t/b)^2; the half-peak choice is an analyst convention, not a plate '
                        'solution for a non-uniform stress field.',
                        'The released state assumes the residual stress is unchanged by '
                        'coiling, slitting or levelling.', NOT_VALIDATED],
        'sources': [SOURCES['ihi_sheetflat'], SOURCES['vollmer_2019'],
                    SOURCES['abdelkhalek_2008'], SOURCES['lloyd_2010'],
                    SOURCES['timoshenko_plate'], SOURCES['lorin']]})


def _peak_abs(values):
    return max(abs(v) for v in values)


def _signed_peak(values):
    return max(values, key=abs)


def thermal_stripe_flatness(z_m, local_radius_deviation_m, *, exit_thickness_m,
                            strip_stiffness_per_width_pa, bite_half_length_m, roll_radius_m,
                            strip_width_m, mean_tension_pa, strip_centre_m=None, n_rolls=2,
                            roll_youngs_modulus_pa=STEEL_E_PA, roll_poisson_ratio=STEEL_NU,
                            strip_youngs_modulus_pa=ALUMINIUM_E_PA,
                            strip_poisson_ratio=ALUMINIUM_NU, xi=1.0,
                            reporting_threshold_i_units=DEFAULT_REPORTING_THRESHOLD_I_UNITS,
                            yield_stress_pa=None,
                            exit_tension_force_sensitivity_per_width_m=None):
    """Chain W2.1 -> elongation -> flatness for a local roll-radius profile (flat entry).

    Samples with ``|z - centre| <= width/2`` are used (centre defaults to the middle of the
    z range). Three levels are reported: the rigid-transfer bound
    ``I = 1e5*n_rolls*max|dR|/h``, the compliance-only result (``Q``) and, when
    ``exit_tension_force_sensitivity_per_width_m`` (N_x') is given, the exit-tension feedback
    result (``Q_eff``), which is then the main ``flatness``/``bands``.

    Saturation (approximate, band-wise) [D, planner]: a LOOSE band that the linear feedback
    leaves MANIFEST (net-compression criterion, half-peak width b) cannot lose more tension
    than ``sigma_T + sigma_cr(b)``; its force increase is
    capped at ``dP'_max = N_x'*(sigma_T + sigma_cr)`` and the peak thickness change becomes
    ``|dh| = (n*dR_peak - 2*C(2b)*dP'_max)/(1 + 2*C(2b)*Q)`` (floored at the linear-feedback
    value); the band's samples are scaled by the peak ratio and flatness recomputed.
    """
    z = _grid(z_m, min_len=4)
    dr = _list('local_radius_deviation_m', local_radius_deviation_m, min_len=4,
               lo=-1e-3, hi=1e-3)
    if len(dr) != len(z):
        raise ValueError('local_radius_deviation_m must have the same length as z_m')
    h = _thickness('exit_thickness_m', exit_thickness_m)
    w = _num('strip_width_m', strip_width_m, positive=True, hi=10.0)
    c = (z[0] + z[-1]) / 2 if strip_centre_m is None else _num('strip_centre_m',
                                                               strip_centre_m, lo=-100.0,
                                                               hi=100.0)
    n_r = _n_rolls(n_rolls)
    sig_t = _num('mean_tension_pa', mean_tension_pa, nonnegative=True, hi=2e9)
    e_r = _modulus('roll_youngs_modulus_pa', roll_youngs_modulus_pa)
    nu_r = _poisson('roll_poisson_ratio', roll_poisson_ratio)
    idx = [i for i, v in enumerate(z) if abs(v - c) <= w / 2 * (1 + 1e-12)]
    if len(idx) < 4:
        raise ValueError('fewer than 4 samples lie inside the strip width')
    zs, drs = [z[i] for i in idx], [dr[i] for i in idx]
    common = dict(bite_half_length_m=bite_half_length_m,
                  strip_stiffness_per_width_pa=strip_stiffness_per_width_pa,
                  roll_radius_m=roll_radius_m, n_rolls=n_r, roll_youngs_modulus_pa=e_r,
                  roll_poisson_ratio=nu_r)

    def chain(dh):
        exit_profile = [h + v for v in dh]
        if min(exit_profile) <= 0:
            raise ValueError('local thickness change exceeds the exit thickness')
        el = differential_elongation(zs, [h] * len(zs), exit_profile, xi=xi)
        fl = flatness_from_elongation(
            zs, el['elongation'], youngs_modulus_pa=strip_youngs_modulus_pa,
            poisson_ratio=strip_poisson_ratio, thickness_m=h, mean_tension_pa=sig_t,
            reporting_threshold_i_units=reporting_threshold_i_units,
            yield_stress_pa=yield_stress_pa)
        return exit_profile, el, fl

    tr_c = transfer_radius_profile(zs, drs, **common)
    feedback = exit_tension_force_sensitivity_per_width_m is not None
    if not feedback:
        tr = tr_c
        dh = tr['local_thickness_change_m']
        exit_profile, el, fl = chain(dh)
        fl_c, fl_lin, saturated = fl, None, []
    else:
        _, _, fl_c = chain(tr_c['local_thickness_change_m'])
        tr = transfer_radius_profile(
            zs, drs, **common,
            exit_tension_force_sensitivity_per_width_m=exit_tension_force_sensitivity_per_width_m,
            exit_thickness_m=h, strip_youngs_modulus_pa=strip_youngs_modulus_pa, xi=xi)
        dh_lin = tr['local_thickness_change_m']
        _, _, fl_lin = chain(dh_lin)
        nx = tr['exit_tension_force_sensitivity_per_width_m']
        q = tr['strip_stiffness_per_width_pa']
        a = tr['short_wavelength_limit_m'] / SHORT_WAVELENGTH_FACTOR
        radius = tr['long_wavelength_limit_m']
        dh = list(dh_lin)
        saturated = []
        for b in fl_lin['bands']:
            if b['sense'] != 'LOOSE_LONG' or b['state'] != 'MANIFEST_BUCKLE':
                continue
            members = [i for i, v in enumerate(zs) if b['start_m'] < v < b['end_m']]
            dr_pk = max(drs[i] for i in members)
            dh_pk = max(-dh_lin[i] for i in members)
            if dr_pk <= 0 or dh_pk <= 0:
                continue
            lam = min(max(2 * b['width_m'], SHORT_WAVELENGTH_FACTOR * a), radius)
            cc = _compliance(lam, a, e_r, nu_r)
            dp_max = nx * (sig_t + b['band_buckling_stress_pa'])
            mag = max((n_r * dr_pk - 2 * cc * dp_max) / (1 + 2 * cc * q), dh_pk)
            for i in members:
                dh[i] *= mag / dh_pk
            saturated.append({
                'start_m': b['start_m'], 'end_m': b['end_m'],
                'linear_feedback_peak_i_units': b['peak_i_units'],
                'band_buckling_stress_pa': b['band_buckling_stress_pa'],
                'effective_buckling_width_m': b['effective_buckling_width_m'],
                'dominant_wavelength_m': lam, 'capped_force_increase_per_width_n_m': dp_max,
                'linear_feedback_peak_thickness_change_m': -dh_pk,
                'saturated_peak_thickness_change_m': -mag, 'scale_factor': mag / dh_pk})
        exit_profile, el, fl = chain(dh)
        for b in fl['bands']:
            hit = [s for s in saturated if s['start_m'] <= b['peak_position_m'] <= s['end_m']]
            members = [i for i, v in enumerate(zs) if b['start_m'] < v < b['end_m']]
            b['saturated'] = bool(hit)
            b['linear_feedback_peak_i_units'] = (
                hit[0]['linear_feedback_peak_i_units'] if hit
                else _signed_peak([fl_lin['i_units'][i] for i in members]))
    peak_dr = max(abs(v) for v in drs)
    rigid_i = n_r * peak_dr / h / I_UNIT
    peak_abs_i = max(abs(fl['max_i_units']), abs(fl['min_i_units']))
    peak_dh = _signed_peak(dh)
    rel_dh = peak_dh / h
    flags = sorted(set(tr['flags'] + el['flags'] + fl['flags']
                       + (['TENSION_FEEDBACK_SATURATED_BAND_SLACK'] if saturated else [])))
    comp_i = _peak_abs(fl_c['i_units'])
    reasons = [f'Peak local thickness change {peak_dh:.3e} m = {rel_dh:.3e} of the {h:.3e} m '
               f'gauge; flatness peak {peak_abs_i:.1f} I-units vs compliance-only '
               f'{comp_i:.1f} and rigid-transfer bound {rigid_i:.1f} I-units.',
               'The same roll stripe is a larger relative thickness error on thinner strip, '
               'and the band buckling stress falls as thickness squared.']
    if feedback:
        reasons.append('With exit-tension feedback dominant, eps tends to '
                       'n*dR/(2*C*N_x\'*E_strip), independent of gauge; the thin-gauge trend '
                       'then comes from the t^2 buckling stress and the shrinking dead band.')
    if saturated:
        reasons.append(f'{len(saturated)} loose band(s) slack: tension feedback saturated at '
                       'sigma_T + sigma_cr; band-wise peak correction applied (approximate).')
    reasons += fl['reasons']
    limitations = ['Entry strip assumed flat (no incoming profile).'] + tr['limitations'] \
        + fl['limitations'][:2]
    if feedback:
        limitations.append('Saturation is an approximate band-wise peak correction: the band '
                           'samples are scaled by one factor, the dominant wavelength is taken '
                           'as twice the band width, and no iteration is made.')
    sub = ('z_m', 'local_radius_deviation_m', 'local_thickness_change_m', 'reasons',
           'limitations', 'sources', 'status')
    return _checked({
        'status': fl['status'], 'z_m': zs, 'strip_centre_m': c, 'strip_width_m': w,
        'exit_thickness_m': h, 'n_rolls': n_r,
        'local_radius_deviation_m': drs, 'local_thickness_change_m': dh,
        'exit_profile_m': exit_profile, 'elongation': el['elongation'],
        'peak_local_thickness_change_m': peak_dh,
        'peak_relative_thickness_change': rel_dh,
        'rigid_transfer_bound_i_units': rigid_i,
        'compliance_only_peak_i_units': comp_i,
        'compliance_only_peak_local_thickness_change_m':
            tr_c['peak_local_thickness_change_m'],
        'compliance_only_status': fl_c['status'],
        'released_status': fl['released_status'],
        'manifest_after_release_band_count': fl['manifest_after_release_band_count'],
        'compliance_only_released_status': fl_c['released_status'],
        'linear_feedback_peak_i_units': None if fl_lin is None else _peak_abs(fl_lin['i_units']),
        'feedback_peak_i_units': peak_abs_i if feedback else None,
        'compliant_to_rigid_i_unit_ratio': peak_abs_i / rigid_i if rigid_i > 0 else None,
        **{k: tr[k] for k in ('effective_strip_stiffness_per_width_pa',
                              'tension_feedback_applied',
                              'tension_feedback_stiffness_per_width_pa',
                              'exit_tension_force_sensitivity_per_width_m')},
        'saturated_bands': saturated,
        'transfer': {k: v for k, v in tr.items() if k not in sub},
        'flatness': {k: v for k, v in fl.items()
                     if k not in ('z_m', 'reasons', 'limitations', 'sources')},
        'bands': fl['bands'], 'formula_basis': {**tr['formula_basis'], **el['formula_basis'],
                                                **fl['formula_basis'],
                                                'rigid_bound': '[D] I = 1e5*n*dR/h',
                                                'saturation': '[D] planner, approximate'},
        'threshold_basis': fl['threshold_basis'] + ' ' + tr['threshold_basis'],
        'reasons': reasons, 'flags': flags, 'limitations': limitations,
        'sources': tr['sources'] + el['sources'] + fl['sources']})


# --------------------------------------------------------------------------- W2.3
def coil_ridge_buildup(ridge_height_m, thickness_m, inner_radius_m, outer_radius_m,
                       yield_stress_pa, winding_tension_pa, youngs_modulus_pa=ALUMINIUM_E_PA,
                       compaction_factor=DEFAULT_COMPACTION_FACTOR):
    """Ridge stacking over coil wraps and the radius beyond which it yields the strip [D].

    ``r_crit(R) = h*R*(sigma_y - sigma_T)/(E*c*(R - R_i))``; onset radius
    ``R_on = c*r*R_i/(c*r - s*h)``; affected length ``(R_o^2-R_on^2)/(R_o^2-R_i^2)``.
    """
    r = _num('ridge_height_m', ridge_height_m, nonnegative=True, hi=1e-3)
    h = _thickness('thickness_m', thickness_m)
    ri = _num('inner_radius_m', inner_radius_m, positive=True, hi=5.0)
    ro = _num('outer_radius_m', outer_radius_m, positive=True, hi=5.0)
    if ro <= ri:
        raise ValueError('outer_radius_m must exceed inner_radius_m')
    sy = _num('yield_stress_pa', yield_stress_pa, positive=True, hi=5e9)
    st = _num('winding_tension_pa', winding_tension_pa, nonnegative=True, hi=5e9)
    if st >= sy:
        raise ValueError('winding_tension_pa must be below yield_stress_pa')
    e = _modulus('youngs_modulus_pa', youngs_modulus_pa)
    c = _num('compaction_factor', compaction_factor, lo=0.0, hi=1.0, lo_open=True)
    s = (sy - st) / e
    wraps = (ro - ri) / h
    build = c * wraps * r
    strain = build / ro
    r_crit = h * ro * s / (c * (ro - ri))
    if c * r > s * h:
        onset = c * r * ri / (c * r - s * h)
    else:
        onset = math.inf
    yields = onset <= ro
    frac = (ro * ro - onset * onset) / (ro * ro - ri * ri) if yields else 0.0
    frac = min(1.0, max(0.0, frac))
    status = 'RIDGE_YIELDS_STRIP' if yields else 'ELASTIC_BUILD_UP'
    reasons = [f'{wraps:.0f} wraps stack the {r:.2e} m ridge to {build:.3e} m radial build-up '
               f'(compaction {c:g}), hoop strain {strain:.3e} vs elastic margin {s:.3e}.',
               f'Critical ridge height at the outer radius {r_crit:.3e} m '
               f'({r_crit / h:.3e} x thickness).']
    if yields:
        reasons.append(f'Yielding from radius {onset:.3f} m outward: the band shows on the '
                       f'outer {frac:.3f} of the wound length only.')
    return _checked({
        'status': status, 'ridge_height_m': r, 'thickness_m': h,
        'inner_radius_m': ri, 'outer_radius_m': ro,
        'wraps_at_outer_radius': wraps, 'radial_build_up_at_outer_radius_m': build,
        'hoop_strain_at_outer_radius': strain, 'yield_margin_strain': s,
        'critical_ridge_height_at_outer_radius_m': r_crit,
        'critical_ridge_height_per_thickness': r_crit / h,
        'ridge_to_critical_ratio': r / r_crit,
        'yield_onset_radius_m': onset if yields else None,
        'affected_length_fraction': frac, 'compaction_factor': c,
        'compaction_factor_basis': 'ANALYST_CHOICE (default 0.5): interwrap gaps are '
                                   'compressible, up to ~4 um gap variation under load '
                                   '[V: Zhu et al. 2009].',
        'thin_gauge_scaling': 'r_crit is proportional to thickness h (fixed coil, tension and '
                              'yield): a ridge harmless at 2 mm can yield foil stock.',
        'formula_basis': {'criterion': '[D] planner criterion', 'mechanism': '[V] Zhang 2016; '
                          'Sun 2016; Melfo 2006'},
        'threshold_basis': 'Yield when build-up hoop strain exceeds (sigma_y - sigma_T)/E '
                           '[D]; compaction factor is an analyst choice.',
        'reasons': reasons,
        'flags': ['RESTS_ON_PLANNER_DERIVED_FORMULA', 'COMPACTION_FACTOR_ANALYST_CHOICE'],
        'limitations': ['Uniform winding tension and perfectly registered ridge (no tracking '
                        'or oscillation spreading it); no interlayer pressure, slip or '
                        'tension loss of inner wraps.',
                        'Steel context: hot-band ridge above ~6-7 um on 0.35 mm strip; a 6 um '
                        'high point yields 0.5 mm strip [V: Melfo 2006 and related].',
                        NOT_VALIDATED],
        'sources': [SOURCES['zhang_2016_lmi'], SOURCES['sun_2016'], SOURCES['melfo_2006'],
                    SOURCES['zhu_2009']]})


# --------------------------------------------------------------------------- W2.4
def _trough_inputs(thickness_m, span_length_m, tension_stress_pa, e, nu):
    return (_thickness('thickness_m', thickness_m),
            _num('span_length_m', span_length_m, positive=True, hi=100.0),
            _num('tension_stress_pa', tension_stress_pa, positive=True, hi=5e9),
            _modulus('youngs_modulus_pa', e), _poisson('poisson_ratio', nu))


def tension_wrinkle_wavelength_m(thickness_m, span_length_m, tension_stress_pa,
                                 youngs_modulus_pa=ALUMINIUM_E_PA, poisson_ratio=ALUMINIUM_NU):
    """``lam = sqrt(2*pi*L*t)/(3*(1-nu^2)*gamma)^(1/4)``, gamma = sigma_x/E [Cerda 2003]."""
    t, length, sx, e, nu = _trough_inputs(thickness_m, span_length_m, tension_stress_pa,
                                          youngs_modulus_pa, poisson_ratio)
    return math.sqrt(2 * math.pi * length * t) / (3 * (1 - nu * nu) * sx / e) ** 0.25


def tension_wrinkle_amplitude_m(thickness_m, span_length_m, tension_stress_pa,
                                youngs_modulus_pa=ALUMINIUM_E_PA, poisson_ratio=ALUMINIUM_NU):
    """``A = sqrt(nu*L*t)*(16*gamma/(3*pi^2*(1-nu^2)))^(1/4)`` [Cerda 2003]."""
    t, length, sx, e, nu = _trough_inputs(thickness_m, span_length_m, tension_stress_pa,
                                          youngs_modulus_pa, poisson_ratio)
    return math.sqrt(nu * length * t) * (16 * sx / e / (3 * math.pi ** 2 * (1 - nu * nu))) ** 0.25


def trough_critical_lateral_stress_pa(thickness_m, span_length_m, tension_stress_pa,
                                      youngs_modulus_pa=ALUMINIUM_E_PA,
                                      poisson_ratio=ALUMINIUM_NU):
    """Trough onset ``-(pi*h/a)*sqrt(E*sigma_x/(3*(1-nu^2)))`` (negative) [Good 2009]."""
    t, a, sx, e, nu = _trough_inputs(thickness_m, span_length_m, tension_stress_pa,
                                     youngs_modulus_pa, poisson_ratio)
    return -(math.pi * t / a) * math.sqrt(e * sx / (3 * (1 - nu * nu)))


def roller_wrinkle_critical_lateral_stress_pa(thickness_m, roller_radius_m,
                                              youngs_modulus_pa=ALUMINIUM_E_PA,
                                              poisson_ratio=ALUMINIUM_NU):
    """Roller wrinkle ``-E*h/(R*sqrt(3*(1-nu^2)))`` (negative) [Good 2009]."""
    t = _thickness('thickness_m', thickness_m)
    rr = _num('roller_radius_m', roller_radius_m, positive=True, hi=5.0)
    e = _modulus('youngs_modulus_pa', youngs_modulus_pa)
    nu = _poisson('poisson_ratio', poisson_ratio)
    return -e * t / (rr * math.sqrt(3 * (1 - nu * nu)))


def tension_trough_screen(thickness_m, span_length_m, tension_stress_pa, strip_width_m,
                          roller_radius_m=None, lateral_compressive_stress_pa=None,
                          observed_spacing_m=None, youngs_modulus_pa=ALUMINIUM_E_PA,
                          poisson_ratio=ALUMINIUM_NU):
    """Trough wavelength, count across the width and trough/wrinkle thresholds.

    ``lateral_compressive_stress_pa`` is a MAGNITUDE (>= 0, compressive) compared with the
    magnitudes of the (negative) critical stresses.
    """
    t, length, sx, e, nu = _trough_inputs(thickness_m, span_length_m, tension_stress_pa,
                                          youngs_modulus_pa, poisson_ratio)
    w = _num('strip_width_m', strip_width_m, positive=True, hi=10.0)
    rr = _opt('roller_radius_m', roller_radius_m, positive=True, hi=5.0)
    lat = _opt('lateral_compressive_stress_pa', lateral_compressive_stress_pa,
               nonnegative=True, hi=5e9)
    obs = _opt('observed_spacing_m', observed_spacing_m, positive=True, hi=10.0)
    lam = tension_wrinkle_wavelength_m(t, length, sx, e, nu)
    amp = tension_wrinkle_amplitude_m(t, length, sx, e, nu)
    trough = trough_critical_lateral_stress_pa(t, length, sx, e, nu)
    wrinkle = None if rr is None else roller_wrinkle_critical_lateral_stress_pa(t, rr, e, nu)
    ratio = None if wrinkle is None else wrinkle / trough
    if lat is None:
        status = 'LATERAL_STRESS_UNKNOWN_THRESHOLDS_ONLY'
    elif wrinkle is not None and lat >= abs(wrinkle):
        status = 'ROLLER_WRINKLE_EXPECTED'      # independent of the trough comparison
    elif lat < abs(trough):
        status = 'BELOW_TROUGH_THRESHOLD'
    else:
        status = 'TROUGHS_EXPECTED'
    spacing_ratio = consistent = None
    if obs is not None:
        spacing_ratio = obs / lam
        consistent = OBSERVED_SPACING_RATIO_BAND[0] <= spacing_ratio \
            <= OBSERVED_SPACING_RATIO_BAND[1]
    flags = ['FORMULAS_RECONSTRUCTED_CROSS_CHECKED']
    if w >= length:
        flags.append('WIDTH_NOT_BELOW_SPAN_OUTSIDE_CERDA_ASSUMPTIONS')
    if lat is not None and wrinkle is None and lat >= abs(trough):
        flags.append('ROLLER_RADIUS_NOT_GIVEN_WRINKLE_NOT_ASSESSED')
    reasons = [f'Trough wavelength {lam:.4f} m ({w / lam:.2f} across the {w:g} m width), '
               f'trough onset at {trough / 1e6:.4f} MPa lateral stress.']
    short_span = wrinkle is not None and abs(wrinkle) < abs(trough)
    if short_span:
        flags.append('ROLLER_WRINKLE_THRESHOLD_BELOW_TROUGH_THRESHOLD_SHORT_SPAN')
        reasons.append(f'Roller wrinkle threshold {wrinkle / 1e6:.3f} MPa is below the trough '
                       f'threshold in magnitude (ratio {ratio:.3f}): the usual ordering '
                       '(troughs first) does not hold for this span/roller, whatever the '
                       'lateral stress.')
    elif wrinkle is not None:
        reasons.append(f'Roller wrinkle threshold {wrinkle / 1e6:.3f} MPa, {ratio:.0f}x the '
                       'trough threshold: troughs come first for this span/roller.')
    if obs is not None:
        reasons.append(f'Observed spacing / wavelength = {spacing_ratio:.3f}: '
                       + ('within' if consistent else 'outside') + ' the 0.5-2 band.')
    return _checked({
        'status': status, 'thickness_m': t, 'span_length_m': length, 'tension_stress_pa': sx,
        'tensile_strain': sx / e, 'strip_width_m': w,
        'wrinkle_wavelength_m': lam, 'wrinkle_amplitude_m': amp,
        'expected_trough_count_across_width': w / lam,
        'trough_critical_lateral_stress_pa': trough,
        'roller_radius_m': rr, 'roller_wrinkle_critical_lateral_stress_pa': wrinkle,
        'wrinkle_to_trough_threshold_ratio': ratio,
        'lateral_compressive_stress_pa': lat, 'observed_spacing_m': obs,
        'observed_spacing_to_wavelength_ratio': spacing_ratio,
        'observed_spacing_consistent': consistent,
        'thin_gauge_scaling': {'trough_threshold': 'proportional to h',
                               'roller_wrinkle_threshold': 'proportional to h',
                               'wavelength': 'proportional to sqrt(h)'},
        'formula_basis': {'wavelength_amplitude': '[V reconstructed] Cerda & Mahadevan 2003, '
                                                  'cross-checked vs Panaitescu et al.',
                          'thresholds': '[V] Good, Beisel & Yurtcu 2009 isotropic reduction'},
        'threshold_basis': 'Literature thresholds; the 0.5-2 spacing band is an analyst '
                           'choice.',
        'reasons': reasons, 'flags': flags,
        'limitations': ['Cerda-Mahadevan assumes t << W < L, far above threshold, small '
                        'slopes and lateral inextensibility; clamped span ends.',
                        'Isotropic sheet; roll friction, roll crown/taper and misalignment '
                        'that generate the lateral compression are not computed here.',
                        'Creases (plastic ratcheting, ~10 mm, Jacques et al. 2007) are not '
                        'predicted, only the elastic precursors.',
                        'Wavelength and amplitude describe wrinkles that exist (far above '
                        'threshold); below the trough threshold the amplitude is zero.',
                        NOT_VALIDATED],
        'sources': [SOURCES['cerda_2003'], SOURCES['panaitescu'], SOURCES['good_2009'],
                    SOURCES['jacques_2007'], SOURCES['aa_qca1'], SOURCES['eafa_2020']]})


# --------------------------------------------------------------------------- W2.5
def two_tone_positions_m(previous_strip_widths_m, strip_centre_m, current_strip_width_m):
    """Band edges at earlier, narrower strip edges that fall inside the current strip [V]."""
    widths = _list('previous_strip_widths_m', previous_strip_widths_m, min_len=0,
                   positive=True, hi=10.0)
    c = _num('strip_centre_m', strip_centre_m, lo=-100.0, hi=100.0)
    w = _num('current_strip_width_m', current_strip_width_m, positive=True, hi=10.0)
    edges = []
    for k, pw in enumerate(widths):
        if pw < w:
            edges.extend({'previous_width_index': k, 'previous_strip_width_m': pw,
                          'position_m': c + s * pw / 2, 'side': side}
                         for s, side in ((-1, 'LOW_SIDE'), (1, 'HIGH_SIDE')))
    positions = sorted({e['position_m'] for e in edges})
    return _checked({
        'status': 'TWO_TONE_EDGES_PREDICTED' if positions else 'NO_NARROWER_PREVIOUS_WIDTHS',
        'band_positions_m': positions, 'edges': edges, 'strip_centre_m': c,
        'current_strip_width_m': w,
        'reasons': [f'{len(positions)} roll-surface band edge position(s) from narrower '
                    'earlier widths inside the current strip.'],
        'flags': [], 'threshold_basis': 'Geometric: previous edges strictly inside the '
                                        'current strip.',
        'limitations': ['Assumes earlier strips ran on the same centre line (no tracking '
                        'offset or roll shifting).'],
        'sources': [SOURCES['aa_qca1']]})


def grinding_feed_pitch_m(traverse_speed_m_s, roll_rotation_hz):
    """Grinding feed pitch = traverse per roll revolution [V: EN 12258-1; trade sources]."""
    v = _num('traverse_speed_m_s', traverse_speed_m_s, positive=True, hi=1.0)
    f = _num('roll_rotation_hz', roll_rotation_hz, positive=True, hi=1e3)
    return v / f


def spacing_analysis(positions_m):
    """Sorted positions, gaps, mean/min/max gap and coefficient of variation."""
    p = sorted(_list('positions_m', positions_m, min_len=2, lo=-100.0, hi=100.0))
    gaps = [b - a for a, b in zip(p, p[1:])]
    mean = _mean(gaps)
    if mean <= 0:
        raise ValueError('positions_m must not all coincide')
    cv = statistics.pstdev(gaps) / mean if len(gaps) > 1 else 0.0
    regular = cv <= REGULAR_SPACING_CV_LIMIT
    return _checked({
        'status': 'REGULAR_SPACING' if regular else 'IRREGULAR_SPACING',
        'positions_m': p, 'gaps_m': gaps, 'mean_gap_m': mean, 'min_gap_m': min(gaps),
        'max_gap_m': max(gaps), 'coefficient_of_variation': cv, 'regular': regular,
        'threshold_basis': f'REGULAR when CV <= {REGULAR_SPACING_CV_LIMIT} (analyst choice).',
        'reasons': [f'{len(gaps)} gap(s), mean {mean:.4f} m, CV {cv:.3f}.'],
        'flags': ['SINGLE_GAP'] if len(gaps) == 1 else [],
        'limitations': ['Positions must share one coordinate (barrel or strip).'],
        'sources': []})


def match_spacing(gaps_m, candidate_pitch_m, tolerance_fraction=0.1):
    """Is each gap within ``tolerance_fraction*pitch`` of ``m*pitch`` for m in 1..8?"""
    gaps = _list('gaps_m', gaps_m, min_len=1, positive=True, hi=100.0)
    p = _num('candidate_pitch_m', candidate_pitch_m, positive=True, hi=100.0)
    tol = _num('tolerance_fraction', tolerance_fraction, positive=True, hi=0.5)
    rows = []
    for g in gaps:
        m = min(8, max(1, round(g / p)))
        dev = g / p - m
        rows.append({'gap_m': g, 'nearest_multiple': m, 'deviation_in_pitches': dev,
                     'matched': abs(dev) <= tol})
    hits = sum(r['matched'] for r in rows)
    status = ('ALL_GAPS_MATCH' if hits == len(rows) else
              'NO_GAPS_MATCH' if hits == 0 else 'SOME_GAPS_MATCH')
    return _checked({
        'status': status, 'candidate_pitch_m': p, 'tolerance_fraction': tol, 'gaps': rows,
        'matched_count': hits, 'multiples': [r['nearest_multiple'] for r in rows if r['matched']],
        'threshold_basis': 'Tolerance relative to one pitch, multiples 1..8 (analyst choice).',
        'reasons': [f'{hits} of {len(rows)} gap(s) are integer multiples of {p:g} m.'],
        'flags': [], 'limitations': ['A match is consistency, not proof: small pitches match '
                                     'many gaps.'], 'sources': []})


def match_positions(predicted_positions_m, observed_positions_m, tolerance_m):
    """Nearest predicted position for each observed band position, within a tolerance."""
    pred = _list('predicted_positions_m', predicted_positions_m, min_len=0,
                 lo=-100.0, hi=100.0)
    obs = _list('observed_positions_m', observed_positions_m, min_len=1, lo=-100.0, hi=100.0)
    tol = _num('tolerance_m', tolerance_m, nonnegative=True, hi=10.0)
    rows, used = [], set()
    for x in obs:
        best = min(range(len(pred)), key=lambda i: abs(pred[i] - x)) if pred else None
        dist = None if best is None else abs(pred[best] - x)
        ok = dist is not None and dist <= tol
        if ok:
            used.add(best)
        rows.append({'observed_position_m': x, 'nearest_predicted_index': best,
                     'nearest_predicted_position_m': None if best is None else pred[best],
                     'distance_m': dist, 'matched': ok})
    hits = sum(r['matched'] for r in rows)
    status = ('ALL_OBSERVED_POSITIONS_MATCHED' if hits == len(rows) else
              'NO_OBSERVED_POSITIONS_MATCHED' if hits == 0 else
              'SOME_OBSERVED_POSITIONS_MATCHED')
    return _checked({
        'status': status, 'matches': rows,
        'unmatched_positions_m': [r['observed_position_m'] for r in rows if not r['matched']],
        'unexplained_predicted_indices': [i for i in range(len(pred)) if i not in used],
        'tolerance_m': tol, 'threshold_basis': 'Tolerance supplied by the caller.',
        'reasons': [f'{hits} of {len(rows)} observed position(s) within {tol:g} m of a '
                    'prediction.'],
        'flags': [] if pred else ['NO_PREDICTED_POSITIONS'],
        'limitations': ['Positions must share one coordinate; tracking offsets are the '
                        "caller's to remove."], 'sources': []})
