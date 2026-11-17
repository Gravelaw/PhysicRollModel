"""Kinematic band signatures and non-vibration screens for transverse/lengthwise strip bands.

Opt-in, standard-library-only screening helpers. Every quantity is SI; every result is a
plain JSON-serialisable dict (or float/list of dicts). Nothing here is plant-validated: the
screens tally kinematic and rule-based consistency, they do not assign probabilities or
certify a root cause. Independent of ``physicroll.chatter``.

Sign conventions and symbols
----------------------------
- ``u_x`` exit strip speed [m/s]; ``V_r`` roll surface speed; forward slip
  ``f = u_x/V_r - 1`` (negative = strip slower than roll = neutral point at/after exit).
- Strip pitch ``p`` [m] = distance between successive marks measured on the exit strip.
- Work-roll rotation frequency ``f_wr = V_r/(pi*D_w)`` with ``V_r = u_x/(1+f)``; the backup
  roll has the same surface speed, so ``f_br = V_r/(pi*D_b)``.

Pitch laws (``f = v/p``, Kim et al. 2012; order analysis, Krueger, Richard & Peretic 2019)
------------------------------------------------------------------------------------------
- fixed frequency F (structural resonance, self-excited chatter): ``p = u_x/F`` (pitch
  proportional to speed);
- roll-borne marks, n per circumference of a roll of diameter D (work or backup roll; a
  backup-roll mark transfers at equal surface pitch to the work roll and then to the
  strip): ``p = pi*D*(1+f)/n`` (speed independent); an excitation at ``order`` x the
  work-roll rotation: ``p = pi*D_w*(1+f)/order``;
- coil/mandrel-locked (exit coil): ``p = pi*D_coil`` (drifts as the coil builds);
  entry coil: ``p = pi*D_coil*h_in/h_out`` on the exit strip;
- a later pass stretches an existing pitch by ``h_in/h_out``.

Bearing defect orders (Randall & Antoni 2011), ``r = (d/D)*cos(phi)``:
``BPFO = n/2*(1-r)``, ``BPFI = n/2*(1+r)``, ``FTF = (1-r)/2``, ``BSF = D/(2d)*(1-r^2)``,
all as multiples of the shaft frequency (nominal, no rolling-element slip).

Material screens (Al-Mg yield-point marks; Aluminum Association QCA-1; Choi, Jin & Kang
1998; de Codes et al. 2011; Reynolds US 4,081,294; Li et al. 2020; Mucsi 2018):
bending surface strain ``eps_b = t/D``; yield strain ``eps_y = sigma_y/E``; onset with
tension ``eps_on = max(eps_y - sigma_t/E, 0)``; plateau end ``eps_y + eps_L``; risky
diameter window ``[t/(eps_y+eps_L), t/eps_on]``.

Lubrication screens: forward-slip screen (Reid & Schey 1978 for full-film negative slip);
herringbone (Komori 1996; Szucs et al. 2020; Alcoa US 5,508,119 citing Schey); inlet film
``h_s = 3*eta0*alpha*(U_r+U_s)/(theta*(1-exp(-alpha*Y_ps)))`` attributed in the project
spec to Wilson & Walowit (1972) and QUOTED FROM MEMORY (not in the verified source list;
flagged in every result); film ratio ``Lambda = h_s/sqrt(Rq_r^2+Rq_s^2)`` with boundary
< 1 <= mixed <= 3 < hydrodynamic (Sutcliffe 2002).

Coolant sprays (Lloyd, Lechler 2010; Tucker, Lechler 2006): flat-fan footprint
``W = 2*s*tan(angle/2)``; along-header width ``W_eff = W*cos(offset)``; overlap
``(W_eff - pitch)/W_eff``; free thermal radius growth ``dR = alpha*R*dT`` (upper bound);
local gap closure fraction ``2*dR/h_exit`` (both work rolls grow).

NOT modelled: roll-stack dynamics (see ``physicroll.chatter``), strip wave propagation,
rolling-element slip, gear transmission error amplitude, mark severity/amplitude, any
temperature field (axial conduction, spray heat-transfer coefficients), plate-out
chemistry, non-circular contact, strain-rate/ageing kinetics of yield-point materials.
Analyst-chosen thresholds are labelled in each result's ``threshold_basis``.
"""
from dataclasses import dataclass
import json
import math
import re

SOURCES = {
    'kim_2012': 'Kim, Kim, Park et al. (2012) ISIJ Int. 52:2042, '
                'doi:10.2355/isijinternational.52.2042 (f = v/p)',
    'kruger_2019': 'Krueger, Richard, Peretic (SMS group) AISTech 2019 "Chatter Management at '
                   'Cold Rolling Mills Today" (order analysis, mark distance = '
                   'circumference/order)',
    'innoval': 'Innoval Technology (Farley): innovaltec.com mill-vibration, strip-chatter-marks '
               'and chatter-cold-rolling-mill blogs (fifth octave 600-1200 Hz, 2xBPFI case)',
    'randall_antoni_2011': 'Randall & Antoni (2011) MSSP, doi:10.1016/j.ymssp.2010.07.017 '
                           '(bearing frequencies)',
    'aa_qca1': 'Aluminum Association (2002) Visual Quality Characteristics of Aluminum Sheet '
               'and Plate QCA-1, 4th ed.',
    'choi_1998': 'Choi, Jin, Kang (1998) Scripta Mater. 38(6):887 (Type A Luders below ~40 um '
                 'grain size)',
    'de_codes_2011': 'de Codes, Hopperstad, Engler, Lademo, Embury, Benallal (2011) Metall. '
                     'Mater. Trans. A 42, doi:10.1007/s11661-011-0749-1 (5182-O band strain ~0.01)',
    'reynolds_patent': 'Reynolds US 4,081,294 (1978) (>= 2 % cold reduction suppresses Type A; '
                       '5182-O yield ~139 MPa)',
    'li_2020': 'Li et al. (2020) (1 % pre-stretch removes the yield plateau)',
    'mucsi_2018': 'Mucsi (2018) Eng. Fail. Anal. 83, doi:10.1016/j.engfailanal.2017.09.022 '
                  '(coil breaks)',
    'komori_1996': 'Komori (1996) J. Mater. Process. Technol. 60:377, '
                   'doi:10.1016/0924-0136(96)02357-6 (herringbone pitch = arc of contact)',
    'szucs_2020': 'Szucs et al. (2020) Mater. Sci. Eng. (Miskolc) 45(1):284 (herringbone onset '
                  '~40-45 % reduction on 5754-O)',
    'alcoa_patent': 'Alcoa US 5,508,119 (1996) citing Schey (1983)',
    'reid_schey_1978': 'Reid & Schey (1978) ASLE Trans. 21(3), doi:10.1080/05698197808982874 '
                       '(full-film lubrication, negative forward slip, matte surface)',
    'sutcliffe_2002': 'Sutcliffe (2002) in Lenard (ed.) Metal Forming Science and Practice, '
                      'doi:10.1016/b978-008044024-8/50004-7 (film ratio regimes)',
    'lloyd_2010': 'Lloyd (Lechler, 2010) "Fundamentals of roll cooling and control of flatness '
                  'at primary cold reduction"',
    'tucker_2006': 'Tucker (Lechler, 2006) "Flatness and profile ... spray actuators"',
}

KIND_ORDER_LOCKED = 'order_locked'
KIND_FIXED_FREQUENCY = 'fixed_frequency'
KIND_COIL_LOCKED = 'coil_locked'
LAW_INDEPENDENT = 'independent_of_speed'
LAW_PROPORTIONAL = 'proportional_to_speed'
LAW_COIL = 'drifts_with_coil_diameter'

FIXED_FREQUENCY_MIN_SLOPE = 0.7
SPEED_INDEPENDENT_MAX_ABS_SLOPE = 0.3
MARGINAL_FORWARD_SLIP = 0.005
HERRINGBONE_ELEVATED_REDUCTION = 0.40
HERRINGBONE_HIGH_REDUCTION = 0.45
LUDERS_SUPPRESSING_REDUCTION = 0.02
COLD_WORK_SUPPRESSION_FRACTION = 0.01
FINE_GRAIN_LIMIT_M = 40e-6
COARSE_GRAIN_RULE_LIMIT_M = 70e-6
MG_SUSCEPTIBLE_WT_PCT = 2.0
GAP_CLOSURE_NOTABLE_FRACTION = 1e-3
MAX_EXIT_SPEED_M_S = 200.0  # input sanity envelope (analyst choice), far above real mills
WILSON_WALOWIT_FLAG = 'FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE'


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


def _int(name, value, *, lo=None, hi=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an int (not bool)')
    if lo is not None and value < lo or hi is not None and value > hi:
        raise ValueError(f'{name} must be an int in [{lo}, {hi}]')
    return value


def _name(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value.strip()


def _speed(value, name='exit_speed_m_s'):
    return _num(name, value, positive=True, hi=MAX_EXIT_SPEED_M_S)


def _slip(value, name='forward_slip_fraction'):
    return _num(name, value, lo=-0.5, hi=0.5, lo_open=True, hi_open=True)


def _diameter(name, value):
    return _num(name, value, positive=True, hi=10.0)


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


# --------------------------------------------------------------------------- 2.1 pitch laws
def fixed_frequency_pitch_m(exit_speed_m_s, frequency_hz):
    """Strip pitch ``p = u_x/F`` of a fixed-frequency source (proportional to speed)."""
    return _speed(exit_speed_m_s) / _num('frequency_hz', frequency_hz, positive=True, hi=1e6)


def roll_mark_pitch_m(roll_diameter_m, forward_slip_fraction, marks_per_circumference=1):
    """Pitch ``p = pi*D*(1+f)/n`` of n marks on a work or backup roll (speed independent)."""
    d = _diameter('roll_diameter_m', roll_diameter_m)
    n = _int('marks_per_circumference', marks_per_circumference, lo=1, hi=100000)
    return math.pi * d * (1 + _slip(forward_slip_fraction)) / n


def order_locked_pitch_m(work_roll_diameter_m, forward_slip_fraction, order):
    """Pitch ``p = pi*D_w*(1+f)/order`` of an excitation at order x work-roll rotation."""
    d = _diameter('work_roll_diameter_m', work_roll_diameter_m)
    k = _num('order', order, positive=True, hi=1e5)
    return math.pi * d * (1 + _slip(forward_slip_fraction)) / k


def coil_locked_pitch_m(coil_diameter_m):
    """Pitch ``p = pi*D_coil`` of a coil/mandrel-locked source (drifts with coil diameter)."""
    return math.pi * _diameter('coil_diameter_m', coil_diameter_m)


def stretched_pitch_m(pitch_m, entry_thickness_m, exit_thickness_m):
    """Pitch after a later pass: ``p_out = p_in*h_in/h_out`` (volume constancy, no spread)."""
    p = _num('pitch_m', pitch_m, positive=True, hi=100.0)
    h0 = _num('entry_thickness_m', entry_thickness_m, positive=True, hi=0.1)
    h1 = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.1)
    if h1 > h0:
        raise ValueError('exit_thickness_m must not exceed entry_thickness_m')
    return p * h0 / h1


def _observation_pair(index, item):
    if isinstance(item, dict):
        if set(item) - {'exit_speed_m_s', 'pitch_m'} or len(item) != 2:
            raise ValueError(f'observation {index} needs exactly keys exit_speed_m_s, pitch_m')
        speed, pitch = item['exit_speed_m_s'], item['pitch_m']
    elif isinstance(item, (tuple, list)) and len(item) == 2:
        speed, pitch = item
    else:
        raise ValueError(f'observation {index} must be (exit_speed_m_s, pitch_m) or a dict')
    return (_speed(speed, f'observation {index} exit_speed_m_s'),
            _num(f'observation {index} pitch_m', pitch, positive=True, hi=100.0))


def pitch_speed_exponent(observations):
    """Least-squares slope of ln(pitch) vs ln(exit speed); ~1 fixed frequency, ~0 roll-borne.

    Returns status == classification: 'FIXED_FREQUENCY' (slope >= 0.7),
    'SPEED_INDEPENDENT_PITCH' (|slope| <= 0.3) or 'INDETERMINATE'. Thresholds are the
    project-spec analyst choices, not literature values.
    """
    if isinstance(observations, (str, bytes, dict)) or not hasattr(observations, '__iter__'):
        raise ValueError('observations must be a sequence of (exit_speed_m_s, pitch_m) pairs')
    pairs = [_observation_pair(i, item) for i, item in enumerate(observations)]
    if len(pairs) < 2:
        raise ValueError('at least two observations are required')
    xs = [math.log(u) for u, _ in pairs]
    ys = [math.log(p) for _, p in pairs]
    if max(xs) - min(xs) < 1e-9:
        raise ValueError('observations need at least two distinct exit speeds')
    distinct = len({round(x, 12) for x in xs})
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    intercept = my - slope * mx
    rms = math.sqrt(sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys)) / len(xs))
    if slope >= FIXED_FREQUENCY_MIN_SLOPE:
        status = 'FIXED_FREQUENCY'
        reasons = [f'Pitch rises with speed (exponent {slope:.3f} >= 0.7): consistent with a '
                   'fixed-frequency source such as a structural resonance or self-excited chatter.']
    elif abs(slope) <= SPEED_INDEPENDENT_MAX_ABS_SLOPE:
        status = 'SPEED_INDEPENDENT_PITCH'
        reasons = [f'Pitch roughly independent of speed (|exponent| {abs(slope):.3f} <= 0.3): '
                   'consistent with a roll-borne, order-locked or coil-locked source.']
    else:
        status = 'INDETERMINATE'
        reasons = [f'Exponent {slope:.3f} lies between the classification bands; mixed sources, '
                   'coil drift or measurement scatter are possible.']
    flags = []
    if len(pairs) == 2:
        flags.append('TWO_POINT_FIT_NO_RESIDUAL_CHECK')
    if max(xs) - min(xs) < math.log(1.2):
        flags.append('NARROW_SPEED_RANGE_BELOW_20_PERCENT')
    if slope > 1.3:
        flags.append('EXPONENT_ABOVE_UNITY_UNEXPLAINED')
    obs = [{'exit_speed_m_s': u, 'pitch_m': p, 'implied_frequency_hz': u / p} for u, p in pairs]
    return _checked({
        'status': status, 'classification': status,
        'slope': slope, 'intercept_ln_pitch': intercept,
        'pitch_at_unit_speed_m': math.exp(intercept), 'residual_rms_ln': rms,
        'observation_count': len(pairs), 'distinct_speed_count': distinct,
        'observations': obs, 'implied_frequency_hz': [o['implied_frequency_hz'] for o in obs],
        'thresholds': {'fixed_frequency_min_slope': FIXED_FREQUENCY_MIN_SLOPE,
                       'speed_independent_max_abs_slope': SPEED_INDEPENDENT_MAX_ABS_SLOPE},
        'threshold_basis': 'ANALYST_CHOICE_PROJECT_SPEC (classification bands are not sourced)',
        'reasons': reasons, 'flags': flags,
        'limitations': ['Pitch-speed regression discriminates kinematic families only; it does '
                        'not identify which source within a family.',
                        'Coil-locked pitch drifts with coil diameter and can mimic intermediate '
                        'exponents if observations come from different coil positions.'],
        'sources': [SOURCES['kim_2012'], SOURCES['kruger_2019']]})


# --------------------------------------------------------------------------- 2.2 bearings
def bearing_defect_orders(elements, element_diameter_m, pitch_diameter_m, contact_angle_rad):
    """Nominal bearing defect orders (multiples of shaft frequency), Randall & Antoni 2011."""
    n = _int('elements', elements, lo=3, hi=1000)
    d = _num('element_diameter_m', element_diameter_m, positive=True, hi=2.0)
    pd = _num('pitch_diameter_m', pitch_diameter_m, positive=True, hi=5.0)
    phi = _num('contact_angle_rad', contact_angle_rad, nonnegative=True, hi=math.pi / 2,
               hi_open=True)
    if d >= pd:
        raise ValueError('element_diameter_m must be smaller than pitch_diameter_m')
    if n * d > math.pi * pd:
        raise ValueError('elements do not fit on the pitch circle (n*d > pi*D)')
    r = d / pd * math.cos(phi)
    return _checked({
        'status': 'NOMINAL_KINEMATIC_ORDERS',
        'geometry_ratio': r,
        'bpfo_order': n / 2 * (1 - r), 'bpfi_order': n / 2 * (1 + r),
        'ftf_order': (1 - r) / 2, 'bsf_order': pd / (2 * d) * (1 - r * r),
        'flags': [],
        'limitations': ['Nominal kinematics with no rolling-element slip; measured defect '
                        'frequencies typically deviate by a percent or two.',
                        'A rolling-element defect contacting both races repeats at 2 x BSF.'],
        'sources': [SOURCES['randall_antoni_2011']]})


# --------------------------------------------------------------------------- 2.3 catalogue
def _seq(name, value):
    if not isinstance(value, (tuple, list)):
        raise ValueError(f'{name} must be a tuple')
    return tuple(value)


def _keys(name, item, required):
    if not isinstance(item, dict) or set(item) != set(required):
        raise ValueError(f'{name} entries must be dicts with exactly keys {sorted(required)}')


@dataclass(frozen=True)
class MillKinematics:
    """Rotating-element geometry of one stand; diameters in m, all optional lists as tuples."""
    work_roll_diameter_m: float
    backup_roll_diameter_m: float
    gear_meshes: tuple = ()
    bearings: tuple = ()
    grinder_marks: tuple = ()
    deflector_roll_diameters_m: tuple = ()
    entry_coil_diameter_m: float | None = None
    exit_coil_diameter_m: float | None = None
    structural_modes_hz: tuple = ()

    def validate(self):
        dw = _diameter('work_roll_diameter_m', self.work_roll_diameter_m)
        db = _diameter('backup_roll_diameter_m', self.backup_roll_diameter_m)
        if db < dw:
            raise ValueError('backup_roll_diameter_m must be >= work_roll_diameter_m (four-high)')
        names = set()

        def unique(kind, label):
            key = (kind, label)
            if key in names:
                raise ValueError(f'duplicate {kind} name {label!r}')
            names.add(key)

        for g in _seq('gear_meshes', self.gear_meshes):
            _keys('gear_meshes', g, ('name', 'teeth', 'shaft_speed_ratio_to_work_roll'))
            unique('gear', _name('gear name', g['name']))
            _int('gear teeth', g['teeth'], lo=1, hi=10000)
            _num('shaft_speed_ratio_to_work_roll', g['shaft_speed_ratio_to_work_roll'],
                 positive=True, hi=1000.0)
        for b in _seq('bearings', self.bearings):
            _keys('bearings', b, ('name', 'shaft', 'elements', 'element_diameter_m',
                                  'pitch_diameter_m', 'contact_angle_rad'))
            unique('bearing', _name('bearing name', b['name']))
            if b['shaft'] not in ('work_roll', 'backup_roll'):
                raise ValueError("bearing shaft must be 'work_roll' or 'backup_roll'")
            bearing_defect_orders(b['elements'], b['element_diameter_m'], b['pitch_diameter_m'],
                                  b['contact_angle_rad'])
        for g in _seq('grinder_marks', self.grinder_marks):
            _keys('grinder_marks', g, ('roll', 'marks_per_circumference'))
            if g['roll'] not in ('work_roll', 'backup_roll'):
                raise ValueError("grinder mark roll must be 'work_roll' or 'backup_roll'")
            _int('marks_per_circumference', g['marks_per_circumference'], lo=1, hi=100000)
        for i, d in enumerate(_seq('deflector_roll_diameters_m', self.deflector_roll_diameters_m)):
            _diameter(f'deflector_roll_diameters_m[{i}]', d)
        for label in ('entry_coil_diameter_m', 'exit_coil_diameter_m'):
            if getattr(self, label) is not None:
                _diameter(label, getattr(self, label))
        for m in _seq('structural_modes_hz', self.structural_modes_hz):
            _keys('structural_modes_hz', m, ('name', 'frequency_hz', 'family'))
            unique('mode', _name('mode name', m['name']))
            _num('mode frequency_hz', m['frequency_hz'], positive=True, hi=1e5)
            _name('mode family', m['family'])


def _entry(id_, description, kind, frequency_hz, pitch_m, law, order, group, sources,
           family=None):
    return {'id': id_, 'description': description, 'kind': kind,
            'frequency_hz': frequency_hz, 'strip_pitch_m': pitch_m, 'pitch_speed_law': law,
            'order_of_work_roll_rotation': order, 'source_group': group, 'family': family,
            'sources': list(sources)}


def source_catalogue(mill, exit_speed_m_s, forward_slip_fraction, *,
                     entry_exit_thickness_ratio=None):
    """Candidate periodic sources with frequency and strip pitch at this exit speed.

    ``entry_exit_thickness_ratio`` (h_in/h_out of this pass, optional) is needed only to put
    an entry-coil-locked source onto the exit strip; without it that entry has
    ``frequency_hz`` and ``strip_pitch_m`` set to None.
    """
    if not isinstance(mill, MillKinematics):
        raise ValueError('mill must be a MillKinematics')
    mill.validate()
    ux = _speed(exit_speed_m_s)
    f = _slip(forward_slip_fraction)
    ratio = None
    if entry_exit_thickness_ratio is not None:
        ratio = _num('entry_exit_thickness_ratio', entry_exit_thickness_ratio, lo=1.0, hi=100.0)
    dw, db = float(mill.work_roll_diameter_m), float(mill.backup_roll_diameter_m)
    vr = ux / (1 + f)
    fwr = vr / (math.pi * dw)
    fbr = vr / (math.pi * db)
    order_src = [SOURCES['kruger_2019'], SOURCES['kim_2012']]
    out = []

    def locked(id_, desc, order_wr, group, extra_sources=()):
        freq = order_wr * fwr
        out.append(_entry(id_, desc, KIND_ORDER_LOCKED, freq, ux / freq, LAW_INDEPENDENT,
                          order_wr, group, order_src + list(extra_sources)))

    locked('work_roll_1x', 'Work roll 1x rotation (eccentricity, single roll mark)', 1.0,
           'work_roll')
    locked('work_roll_2x', 'Work roll 2x rotation (ovality, spindle/coupling misalignment)',
           2.0, 'work_roll')
    locked('backup_roll_1x', 'Backup roll 1x rotation (eccentricity, single roll mark)',
           dw / db, 'backup_roll')
    locked('backup_roll_2x', 'Backup roll 2x rotation (ovality)', 2 * dw / db, 'backup_roll')
    for g in mill.gear_meshes:
        order = g['teeth'] * float(g['shaft_speed_ratio_to_work_roll'])
        locked(f"gear_mesh:{g['name'].strip()}",
               f"Gear mesh {g['name'].strip()} ({g['teeth']} teeth x shaft frequency)",
               order, 'gear_mesh')
    for b in mill.bearings:
        orders = bearing_defect_orders(b['elements'], b['element_diameter_m'],
                                       b['pitch_diameter_m'], b['contact_angle_rad'])
        scale = 1.0 if b['shaft'] == 'work_roll' else dw / db
        label = b['name'].strip()
        for key, desc, mult in (('bpfo', 'outer-race defect (BPFO)', orders['bpfo_order']),
                                ('bpfi', 'inner-race defect (BPFI)', orders['bpfi_order']),
                                ('2x_bpfi', 'inner-race defect 2nd harmonic (2xBPFI)',
                                 2 * orders['bpfi_order']),
                                ('bsf', 'rolling-element spin (BSF)', orders['bsf_order']),
                                ('ftf', 'cage (FTF)', orders['ftf_order'])):
            locked(f'bearing:{label}:{key}', f"{b['shaft']} bearing {label} {desc}",
                   mult * scale, 'bearing', [SOURCES['randall_antoni_2011'], SOURCES['innoval']])
    for i, g in enumerate(mill.grinder_marks):
        n = g['marks_per_circumference']
        scale = 1.0 if g['roll'] == 'work_roll' else dw / db
        locked(f"grinder_marks:{g['roll']}:{i}",
               f"{n} grinder/chatter marks per circumference on the {g['roll']}",
               n * scale, 'grinder_marks')
    for i, d in enumerate(mill.deflector_roll_diameters_m):
        d = float(d)
        freq = ux / (math.pi * d)
        out.append(_entry(f'deflector_roll:{i}',
                          f'Exit-side deflector roll {i} 1x rotation (D = {d:g} m)',
                          KIND_ORDER_LOCKED, freq, math.pi * d, LAW_INDEPENDENT,
                          freq / fwr, 'deflector_roll', order_src))
    if mill.exit_coil_diameter_m is not None:
        d = float(mill.exit_coil_diameter_m)
        out.append(_entry('exit_coil', 'Exit coil / mandrel 1x rotation at the current coil '
                          'diameter', KIND_COIL_LOCKED, ux / (math.pi * d), math.pi * d,
                          LAW_COIL, None, 'coil', [SOURCES['kim_2012'], SOURCES['mucsi_2018']]))
    if mill.entry_coil_diameter_m is not None:
        d = float(mill.entry_coil_diameter_m)
        pitch = None if ratio is None else math.pi * d * ratio
        out.append(_entry('entry_coil', 'Entry (pay-off) coil 1x rotation at the current coil '
                          'diameter, pitch stretched by h_in/h_out onto the exit strip',
                          KIND_COIL_LOCKED, None if pitch is None else ux / pitch, pitch,
                          LAW_COIL, None, 'coil', [SOURCES['kim_2012'], SOURCES['mucsi_2018']]))
    for m in mill.structural_modes_hz:
        freq = float(m['frequency_hz'])
        out.append(_entry(f"structural_mode:{m['name'].strip()}",
                          f"Structural mode {m['name'].strip()} ({freq:g} Hz)",
                          KIND_FIXED_FREQUENCY, freq, ux / freq, LAW_PROPORTIONAL, None,
                          'structural_mode', [SOURCES['kim_2012'], SOURCES['innoval']],
                          family=m['family'].strip()))
    return _checked(out)


def match_observed_pitch(catalogue, pitch_m, tolerance_fraction=0.08):
    """Catalogue entries whose pitch is within tolerance of the observed pitch.

    Adds ``relative_pitch_mismatch = |p_entry - p_obs|/p_obs`` to copies of matching entries,
    sorted by it; entries with no pitch (``strip_pitch_m`` None) are skipped.
    """
    if not isinstance(catalogue, (list, tuple)):
        raise ValueError('catalogue must be a list of source_catalogue entries')
    p = _num('pitch_m', pitch_m, positive=True, hi=100.0)
    tol = _num('tolerance_fraction', tolerance_fraction, positive=True, hi=1.0, hi_open=True)
    hits = []
    for entry in catalogue:
        if not isinstance(entry, dict) or 'strip_pitch_m' not in entry or 'id' not in entry:
            raise ValueError('catalogue entries must be dicts from source_catalogue')
        if entry['strip_pitch_m'] is None:
            continue
        mismatch = abs(entry['strip_pitch_m'] - p) / p
        if mismatch <= tol:
            hit = dict(entry)
            hit['relative_pitch_mismatch'] = mismatch
            hits.append(hit)
    hits.sort(key=lambda e: e['relative_pitch_mismatch'])
    return _checked(hits)


def resonance_speeds(mill, forward_slip, mode_frequency_hz):
    """Exit speed at which each order-locked source crosses a structural mode.

    Order-locked pitch is speed independent, so ``u_res = F_mode * p``; marks printed there
    have pitch ``p`` (forced/resonant fifth-octave mechanism with possible regeneration via
    backup-roll marking). Sorted by resonant speed.
    """
    fmode = _num('mode_frequency_hz', mode_frequency_hz, positive=True, hi=1e5)
    out = []
    for e in source_catalogue(mill, 1.0, forward_slip):
        if e['kind'] != KIND_ORDER_LOCKED:
            continue
        speed = fmode * e['strip_pitch_m']
        out.append({'id': e['id'], 'description': e['description'],
                    'order_of_work_roll_rotation': e['order_of_work_roll_rotation'],
                    'mode_frequency_hz': fmode, 'resonant_exit_speed_m_s': speed,
                    'strip_pitch_m': e['strip_pitch_m'],
                    'within_speed_envelope': speed <= MAX_EXIT_SPEED_M_S})
    out.sort(key=lambda e: e['resonant_exit_speed_m_s'])
    return _checked(out)


# --------------------------------------------------------------------------- 2.4 material
def bending_surface_strain(thickness_m, roll_or_coil_diameter_m):
    """Outer-fibre bending strain ``t/D`` of strip wrapped on a roll/coil of diameter D."""
    t = _num('thickness_m', thickness_m, positive=True, hi=0.1)
    d = _diameter('roll_or_coil_diameter_m', roll_or_coil_diameter_m)
    if t >= d:
        raise ValueError('thickness_m must be smaller than the diameter')
    return t / d


def yield_point_bending_window(thickness_m, diameter_m, yield_stress_pa, youngs_modulus_pa,
                               luders_strain, tension_stress_pa):
    """Is bending over diameter D inside the discontinuous-yield window? (Al-Mg, O temper)."""
    eps_b = bending_surface_strain(thickness_m, diameter_m)
    t = float(thickness_m)
    e = _num('youngs_modulus_pa', youngs_modulus_pa, lo=1e9, hi=1e12)
    sy = _num('yield_stress_pa', yield_stress_pa, positive=True)
    if sy >= e:
        raise ValueError('yield_stress_pa must be far below youngs_modulus_pa')
    el = _num('luders_strain', luders_strain, nonnegative=True, hi=0.1)
    st = _num('tension_stress_pa', tension_stress_pa, nonnegative=True)
    if st >= sy:
        raise ValueError('tension_stress_pa must be below yield_stress_pa (strip would yield '
                         'in tension alone)')
    eps_y = sy / e
    onset = max(eps_y - st / e, 0.0)
    plateau_end = eps_y + el
    if eps_b < onset:
        status = 'ELASTIC_NO_YIELD'
        reasons = [f'Bending strain {eps_b:.3e} is below the yield onset {onset:.3e}.']
    elif eps_b <= plateau_end:
        status = 'IN_YIELD_POINT_WINDOW'
        reasons = [f'Bending strain {eps_b:.3e} lies between onset {onset:.3e} and the plateau '
                   f'end {plateau_end:.3e}: discontinuous yielding, kinks (coil breaks) or '
                   'Luders bands are possible if the material has a yield point.']
    else:
        status = 'BEYOND_PLATEAU_UNIFORM_YIELD'
        reasons = [f'Bending strain {eps_b:.3e} exceeds the plateau end {plateau_end:.3e}: '
                   'the outer fibre yields through the plateau (uniform yielding).']
    reasons.append('Bending strain t/D falls as gauge thins, so bending-type yield-point marks '
                   'become less likely at thinner gauge: the opposite trend to chatter.')
    return _checked({
        'status': status, 'bending_surface_strain': eps_b, 'yield_strain': eps_y,
        'onset_strain': onset, 'plateau_end_strain': plateau_end,
        'window_min_diameter_m': t / plateau_end,
        'window_max_diameter_m': None if onset == 0 else t / onset,
        'reasons': reasons,
        'flags': ['REQUIRES_YIELD_POINT_MATERIAL_SEE_LUDERS_SUSCEPTIBILITY']
                 + (['TENSION_ALONE_REACHES_YIELD_ONSET_ZERO'] if onset == 0 else []),
        'limitations': ['Elastic-perfectly-plastic outer fibre; neutral axis at mid-thickness.',
                        'Tension lowers the onset but the plateau end is kept at eps_y + eps_L '
                        'as in the project spec.',
                        'Only says whether the strain path crosses the plateau; the material '
                        'must actually show a yield point (see luders_susceptibility).'],
        'threshold_basis': 'Material constants supplied by the caller; window bounds follow '
                           'from them (no analyst threshold).',
        'sources': [SOURCES['aa_qca1'], SOURCES['de_codes_2011'], SOURCES['reynolds_patent'],
                    SOURCES['mucsi_2018']]})


def _alloy_series(alloy):
    m = re.search(r'(?<!\d)([1-8])\d{3}(?!\d)', alloy)
    return int(m.group(1)) if m else None


def luders_susceptibility(alloy, temper, magnesium_wt_pct=None, grain_size_m=None, *,
                          prior_cold_work_fraction=None):
    """Rule-based Type A Luders susceptibility of an aluminium sheet (no probabilities)."""
    alloy = _name('alloy', alloy)
    temper_raw = _name('temper', temper)
    t = temper_raw.upper()
    mg = None if magnesium_wt_pct is None else _num('magnesium_wt_pct', magnesium_wt_pct,
                                                     nonnegative=True, hi=15.0)
    gs = None if grain_size_m is None else _num('grain_size_m', grain_size_m, positive=True,
                                                 hi=5e-3)
    cw = None if prior_cold_work_fraction is None else _num(
        'prior_cold_work_fraction', prior_cold_work_fraction, nonnegative=True, hi=0.99)
    series = _alloy_series(alloy)
    al_mg = series == 5 or (mg is not None and mg >= MG_SUSCEPTIBLE_WT_PCT)
    reasons, flags = [], []
    if series == 5 and mg is not None and mg < MG_SUSCEPTIBLE_WT_PCT:
        flags.append('LOW_MAGNESIUM_5XXX_RULE_APPLIED_BY_SERIES')
    if t.startswith('H'):
        status = 'NOT_SUSCEPTIBLE_COLD_WORKED'
        reasons.append(f'Temper {temper_raw} is strain hardened; cold work of about 1-2 % '
                       'removes the yield plateau.')
        if t.startswith('H111') or t.startswith('H112'):
            flags.append('LIGHT_STRAIN_HARDENING_TEMPER_VERIFY')
    elif cw is not None and cw >= COLD_WORK_SUPPRESSION_FRACTION:
        status = 'NOT_SUSCEPTIBLE_COLD_WORKED'
        reasons.append(f'Prior cold work/stretch {cw:.3f} >= 0.01 removes the yield plateau.')
    elif series is None and mg is None:
        status = 'INDETERMINATE_ALLOY'
        reasons.append(f'Alloy {alloy!r} not recognised as an AA four-digit designation and no '
                       'magnesium content given.')
    elif not al_mg:
        status = 'NOT_SUSCEPTIBLE_ALLOY'
        reasons.append('Not a 5xxx (Al-Mg) alloy and Mg below ~2 wt%: Type A Luders bands are '
                       'not expected.')
    elif not t.startswith('O'):
        status = 'INDETERMINATE_TEMPER'
        reasons.append(f'Temper {temper_raw} is neither O (annealed) nor H; the rule set does '
                       'not cover it.')
    elif gs is None:
        status = 'SUSCEPTIBLE'
        reasons.append('Annealed (O) Al-Mg: a yield plateau and Type A Luders bands are '
                       'possible; grain size unknown.')
    elif gs < FINE_GRAIN_LIMIT_M:
        status = 'SUSCEPTIBLE_FINE_GRAIN'
        reasons.append(f'Annealed Al-Mg with grain size {gs * 1e6:.1f} um < 40 um: Type A '
                       'Luders bands are strengthened.')
    else:
        status = 'SUSCEPTIBLE_WEAKENED_COARSE_GRAIN'
        reasons.append(f'Annealed Al-Mg with grain size {gs * 1e6:.1f} um >= 40 um: the Type A '
                       'yield plateau is weakened.')
        if gs > COARSE_GRAIN_RULE_LIMIT_M:
            flags.append('GRAIN_SIZE_BEYOND_STATED_40_70_UM_RULE_RANGE')
    if status.startswith('SUSCEPTIBLE') and cw is not None and cw > 0:
        reasons.append(f'Prior cold work {cw:.3f} is below the 0.01 suppression threshold.')
    return _checked({
        'status': status, 'alloy': alloy, 'alloy_series': series, 'temper': temper_raw,
        'magnesium_wt_pct': mg, 'grain_size_m': gs, 'prior_cold_work_fraction': cw,
        'reasons': reasons, 'flags': flags,
        'limitations': ['Rule-based screen for Type A (yield-point) Luders lines only; Type B '
                        '(serrated-flow) lines in Al-Mg are not covered.',
                        'Ageing, strain rate and temperature effects are not modelled.'],
        'threshold_basis': 'Mg >= 2 wt% and 1 % cold-work limits are analyst choices within '
                           'the cited ranges (Reynolds: >= 2 %; Li et al.: 1 % pre-stretch); '
                           '40 um grain limit from Choi, Jin & Kang 1998.',
        'sources': [SOURCES['choi_1998'], SOURCES['reynolds_patent'], SOURCES['li_2020'],
                    SOURCES['aa_qca1']]})


def pass_reduction_vs_luders(reduction_fraction, luders_strain):
    """A rolling pass with strain far above the Luders strain cannot leave Luders bands."""
    r = _num('reduction_fraction', reduction_fraction, nonnegative=True, hi=0.95)
    el = _num('luders_strain', luders_strain, nonnegative=True, hi=0.1)
    strain = -math.log(1 - r)
    if r > LUDERS_SUPPRESSING_REDUCTION and strain > el:
        status = 'BITE_CANNOT_LEAVE_LUDERS_BANDS'
        reasons = [f'Pass thickness strain {strain:.4f} (reduction {r:.3f} > 0.02) exceeds the '
                   f'Luders strain {el:.4f}: the bite strains the whole strip through the '
                   'plateau, and the cold work suppresses later yield-point marks. Only skin '
                   'passes, levelling or bending can leave Luders bands.']
    else:
        status = 'LIGHT_REDUCTION_LUDERS_BANDS_POSSIBLE'
        reasons = [f'Reduction {r:.3f} is in the skin-pass range (<= 0.02) or its strain '
                   f'{strain:.4f} does not exceed the Luders strain {el:.4f}.']
    return _checked({
        'status': status, 'reduction_fraction': r, 'thickness_true_strain': strain,
        'luders_strain': el, 'suppressing_reduction_fraction': LUDERS_SUPPRESSING_REDUCTION,
        'reasons': reasons, 'flags': [],
        'limitations': ['Ignores entry/exit bending at deflector rolls and coilers, which is '
                        'screened separately by yield_point_bending_window.'],
        'threshold_basis': '2 % reduction from Reynolds US 4,081,294; comparison of strains is '
                           'an analyst rule.',
        'sources': [SOURCES['reynolds_patent'], SOURCES['de_codes_2011']]})


# --------------------------------------------------------------------------- 2.5 lubrication
def forward_slip_screen(forward_slip_fraction):
    """Forward-slip screen: skidding (f <= 0), marginal (f < 0.005, analyst), normal."""
    f = _slip(forward_slip_fraction)
    if f <= 0:
        status = 'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT'
        reasons = ['Forward slip <= 0: neutral point at or beyond the exit; roll skid marks, '
                   'matte surface and loss of tension control are possible (full-film '
                   'lubrication can give negative forward slip).']
    elif f < MARGINAL_FORWARD_SLIP:
        status = 'MARGINAL_FORWARD_SLIP'
        reasons = [f'Forward slip {f:.4f} below the 0.005 analyst threshold: little friction '
                   'margin before skidding.']
    else:
        status = 'NORMAL'
        reasons = [f'Forward slip {f:.4f} >= 0.005.']
    return _checked({
        'status': status, 'forward_slip_fraction': f,
        'marginal_threshold_fraction': MARGINAL_FORWARD_SLIP,
        'threshold_basis': 'ANALYST_THRESHOLD_UNVERIFIED for the 0.005 marginal limit; the '
                           'f <= 0 skidding limit is kinematic.',
        'reasons': reasons, 'flags': [],
        'limitations': ['Forward slip from a model or from speed sensors carries their error; '
                        'small values need sensor-level accuracy.'],
        'sources': [SOURCES['reid_schey_1978']]})


def herringbone_screen(reduction_fraction, contact_length_m, observed_pitch_m=None):
    """Herringbone (periodic lubricant-film breakdown) risk and pitch-vs-contact-arc check."""
    r = _num('reduction_fraction', reduction_fraction, positive=True, hi=0.95)
    lc = _num('contact_length_m', contact_length_m, positive=True, hi=1.0)
    p = None if observed_pitch_m is None else _num('observed_pitch_m', observed_pitch_m,
                                                    positive=True, hi=100.0)
    if r >= HERRINGBONE_HIGH_REDUCTION:
        risk = 'HIGH'
    elif r >= HERRINGBONE_ELEVATED_REDUCTION:
        risk = 'ELEVATED'
    else:
        risk = 'LOW'
    reasons = [f'Reduction {r:.3f}: herringbone risk {risk} (onset typically ~0.40-0.45 on '
               'hard Al-Mg).']
    ratio = consistent = None
    if p is not None:
        ratio = p / lc
        consistent = 0.5 <= ratio <= 2.0
        reasons.append(f'Observed pitch / contact length = {ratio:.3f}: '
                       + ('within' if consistent else 'outside') + ' the 0.5-2 band expected '
                       'for film breakdown repeating once per arc of contact.')
    return _checked({
        'status': f'HERRINGBONE_RISK_{risk}', 'risk_level': risk, 'reduction_fraction': r,
        'contact_length_m': lc, 'observed_pitch_m': p, 'pitch_to_contact_length_ratio': ratio,
        'pitch_consistent_with_contact_length': consistent,
        'reduction_thresholds': {'elevated': HERRINGBONE_ELEVATED_REDUCTION,
                                 'high': HERRINGBONE_HIGH_REDUCTION},
        'threshold_basis': 'Reduction band 0.40-0.45 from Szucs et al. 2020 / Alcoa citing '
                           'Schey (hard Al-Mg); the split into ELEVATED/HIGH and the 0.5-2 '
                           'pitch band are analyst choices.',
        'reasons': reasons, 'flags': [],
        'limitations': ['Alloy hardness, lubricant and roll roughness are not inputs; the '
                        'reduction thresholds come from hard Al-Mg.',
                        'Herringbone has a chevron pattern; check the visual morphology.'],
        'sources': [SOURCES['komori_1996'], SOURCES['szucs_2020'], SOURCES['alcoa_patent']]})


def inlet_angle_rad(entry_thickness_m, exit_thickness_m, contact_radius_m):
    """Approximate inlet (bite) angle ``theta ~ sqrt((h0-h1)/R')`` with flattened radius R'."""
    h0 = _num('entry_thickness_m', entry_thickness_m, positive=True, hi=0.1)
    h1 = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.1)
    rc = _num('contact_radius_m', contact_radius_m, positive=True, hi=10.0)
    if h1 >= h0:
        raise ValueError('exit_thickness_m must be below entry_thickness_m')
    return math.sqrt((h0 - h1) / rc)


def inlet_film_thickness_wilson_walowit(viscosity_pa_s, pressure_viscosity_coefficient_per_pa,
                                        roll_surface_speed_m_s, strip_entry_speed_m_s,
                                        inlet_angle_rad, plane_strain_yield_pa):
    """Smooth isothermal inlet film ``h_s = 3*eta0*alpha*(U_r+U_s)/(theta*(1-exp(-alpha*Y)))``.

    Formula attributed in the project spec to Wilson & Walowit (1972) and quoted from
    memory; the result always carries FORMULA_QUOTED_FROM_MEMORY_VERIFY_BEFORE_USE.
    """
    eta = _num('viscosity_pa_s', viscosity_pa_s, positive=True, hi=10.0)
    alpha = _num('pressure_viscosity_coefficient_per_pa', pressure_viscosity_coefficient_per_pa,
                 positive=True, hi=1e-6)
    ur = _speed(roll_surface_speed_m_s, 'roll_surface_speed_m_s')
    us = _speed(strip_entry_speed_m_s, 'strip_entry_speed_m_s')
    theta = _num('inlet_angle_rad', inlet_angle_rad, positive=True, hi=0.5)
    y = _num('plane_strain_yield_pa', plane_strain_yield_pa, positive=True, hi=5e9)
    h = 3 * eta * alpha * (ur + us) / (theta * -math.expm1(-alpha * y))
    return _checked({
        'status': 'UNVERIFIED_FORMULA_ESTIMATE', 'film_thickness_m': h,
        'entrainment_speed_sum_m_s': ur + us, 'alpha_times_yield': alpha * y,
        'formula': 'h_s = 3*eta0*alpha*(U_r+U_s)/(theta*(1-exp(-alpha*Y_ps)))',
        'formula_attribution': 'Wilson & Walowit (1972) as named in the project spec; quoted '
                               'from memory, not in the verified source list',
        'reasons': ['Film thickness rises linearly with entrainment speed and viscosity.'],
        'flags': [WILSON_WALOWIT_FLAG, 'SMOOTH_ISOTHERMAL_INLET_ASSUMED'],
        'limitations': ['Smooth surfaces, isothermal Barus-viscosity inlet, no starvation, '
                        'no inlet shear heating (which thins the film at high speed).',
                        'Some textbook forms subtract the entry tension from Y in the '
                        'exponent; verify the exact form before quantitative use.'],
        'threshold_basis': 'No threshold; formula quoted from memory.',
        'sources': []})


def film_ratio_regime(film_thickness_m, roll_roughness_rq_m, strip_roughness_rq_m):
    """Film ratio ``Lambda = h/sqrt(Rq_r^2+Rq_s^2)``: < 1 boundary, 1-3 mixed, > 3 hydrodynamic."""
    h = _num('film_thickness_m', film_thickness_m, nonnegative=True, hi=1e-3)
    rr = _num('roll_roughness_rq_m', roll_roughness_rq_m, nonnegative=True, hi=1e-4)
    rs = _num('strip_roughness_rq_m', strip_roughness_rq_m, nonnegative=True, hi=1e-4)
    rq = math.hypot(rr, rs)
    if rq <= 0:
        raise ValueError('composite roughness must be > 0')
    lam = h / rq
    if lam < 1:
        regime = 'BOUNDARY'
    elif lam <= 3:
        regime = 'MIXED'
    else:
        regime = 'HYDRODYNAMIC'
    reasons = [f'Film ratio {lam:.3f}: {regime.lower()} lubrication.',
               'Film thickness rises with speed and viscosity, lowering friction; lower '
               'friction shrinks the chatter margin.']
    flags = []
    if regime == 'HYDRODYNAMIC':
        reasons.append('A thick film risks skidding (negative forward slip) and a matte '
                       'surface.')
        flags.append('THICK_FILM_SKIDDING_MATTE_RISK')
    return _checked({
        'status': f'{regime}_LUBRICATION', 'regime': regime, 'film_ratio': lam,
        'composite_roughness_rq_m': rq, 'film_thickness_m': h,
        'regime_boundaries': {'boundary_below': 1.0, 'hydrodynamic_above': 3.0},
        'threshold_basis': 'Conventional regime boundaries (Sutcliffe 2002); transitions are '
                           'gradual, not sharp.',
        'reasons': reasons, 'flags': flags,
        'limitations': ['Rq-based ratio ignores roughness lay/orientation and asperity '
                        'flattening in the bite.'],
        'sources': [SOURCES['sutcliffe_2002'], SOURCES['reid_schey_1978']]})


# --------------------------------------------------------------------------- 2.6 sprays
def flat_fan_footprint_width_m(standoff_m, spray_angle_rad):
    """Flat-fan footprint width ``W = 2*s*tan(angle/2)`` at standoff s."""
    s = _num('standoff_m', standoff_m, positive=True, hi=5.0)
    a = _num('spray_angle_rad', spray_angle_rad, positive=True, hi=math.radians(170))
    return 2 * s * math.tan(a / 2)


def spray_coverage(barrel_length_m, nozzle_pitch_m, standoff_m, spray_angle_rad,
                   offset_angle_rad=0.0, blocked_nozzle_indices=(), first_nozzle_position_m=None,
                   resolution_m=0.002):
    """Overlap count of flat fans along a header; under-covered stripes -> lengthwise bands.

    Positions are along the barrel from 0 to L. Default layout: n = floor(L/pitch) nozzles
    (at least 1) centred on the barrel. Coverage is computed exactly from fan edges;
    ``resolution_m`` is the narrowest zone reported (narrower slivers are merged away).
    """
    length = _num('barrel_length_m', barrel_length_m, positive=True, hi=10.0)
    pitch = _num('nozzle_pitch_m', nozzle_pitch_m, positive=True)
    if pitch > length:
        raise ValueError('nozzle_pitch_m must not exceed barrel_length_m')
    width = flat_fan_footprint_width_m(standoff_m, spray_angle_rad)
    offset = _num('offset_angle_rad', offset_angle_rad, nonnegative=True,
                  hi=math.radians(60))
    res = _num('resolution_m', resolution_m, positive=True, hi=0.1 * length)
    if first_nozzle_position_m is None:
        count = max(1, int(math.floor(length / pitch + 1e-9)))
        first = (length - (count - 1) * pitch) / 2
    else:
        first = _num('first_nozzle_position_m', first_nozzle_position_m, nonnegative=True,
                     hi=length)
        count = int(math.floor((length - first) / pitch + 1e-9)) + 1
    positions = [first + i * pitch for i in range(count)]
    if not isinstance(blocked_nozzle_indices, (tuple, list)):
        raise ValueError('blocked_nozzle_indices must be a tuple of ints')
    blocked = sorted({_int('blocked nozzle index', i, lo=0, hi=count - 1)
                      for i in blocked_nozzle_indices})
    w_eff = width * math.cos(offset)
    active = [x for i, x in enumerate(positions) if i not in blocked]
    cuts = {0.0, length}
    for x in active:
        for edge in (x - w_eff / 2, x + w_eff / 2):
            if 0 < edge < length:
                cuts.add(edge)
    cuts = sorted(cuts)
    zones = []
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        c = sum(1 for x in active if abs(mid - x) < w_eff / 2)
        if zones and (zones[-1][2] == c or b - a < res):
            zones[-1][1] = b
        else:
            zones.append([a, b, c])
    if len(zones) > 1 and zones[0][1] - zones[0][0] < res:
        zones[1][0] = zones[0][0]
        zones.pop(0)
    merged = []
    for z in zones:
        if merged and merged[-1][2] == z[2]:
            merged[-1][1] = z[1]
        else:
            merged.append(z)
    weight = {}
    for a, b, c in merged:
        weight[c] = weight.get(c, 0.0) + (b - a)
    modal = max(sorted(weight), key=lambda c: weight[c])
    tol = 1e-9 * length
    blocked_x = [positions[i] for i in blocked]
    stripes = []
    for a, b, c in merged:
        # zero-coverage zones are always kept: when gaps between fans dominate the barrel the
        # modal count is 0 and a ``c >= modal`` test alone would discard every gap
        if c >= modal and c > 0:
            continue
        edge = a <= tol or b >= length - tol
        if any(x - w_eff / 2 < b and x + w_eff / 2 > a for x in blocked_x):
            cause = 'BLOCKED_NOZZLE'
        elif edge:
            cause = 'BARREL_EDGE'
        else:
            cause = 'NOZZLE_PATTERN'
        stripes.append({'start_m': a, 'end_m': b, 'center_m': (a + b) / 2, 'width_m': b - a,
                        'coverage_count': c,
                        'kind': 'UNCOVERED' if c == 0 else 'UNDER_COVERED',
                        'cause': cause, 'at_barrel_edge': edge})
    counts = [c for _, _, c in merged]
    interior = [s for s in stripes if not s['at_barrel_edge']]
    if any(s['coverage_count'] == 0 for s in interior):
        status = 'UNCOVERED_STRIPES_PRESENT'
    elif any(s['cause'] == 'BLOCKED_NOZZLE' for s in stripes):
        status = 'BLOCKED_NOZZLE_STRIPES_PRESENT'
    elif interior:
        status = 'PERIODIC_COVERAGE_VARIATION_AT_NOZZLE_PITCH'
    elif min(counts) == 0:
        status = 'UNCOVERED_AT_BARREL_EDGES_ONLY'
    else:
        status = 'UNIFORM_COVERAGE'
    reasons = [f'{len(active)} of {count} nozzles active; effective footprint {w_eff:.4f} m '
               f'vs pitch {pitch:.4f} m (overlap fraction {(w_eff - pitch) / w_eff:.3f}).']
    if interior:
        reasons.append('Under-cooled stripes give a local thermal crown and differential oil '
                       'plate-out, which can print a lengthwise band at that width position.')
    if any(s['cause'] == 'NOZZLE_PATTERN' for s in stripes):
        reasons.append('Coverage alternates between overlap and single-fan zones at the '
                       'nozzle pitch even with no blocked nozzle (cause NOZZLE_PATTERN).')
    flags = []
    if blocked:
        flags.append('BLOCKED_NOZZLES_SPECIFIED')
    if w_eff < pitch:
        flags.append('NO_NOMINAL_OVERLAP_GAPS_BETWEEN_FANS')
    return _checked({
        'status': status, 'nozzle_count': count, 'active_nozzle_count': len(active),
        'nozzle_positions_m': positions, 'blocked_nozzle_indices': blocked,
        'footprint_width_m': width, 'effective_footprint_width_m': w_eff,
        'overlap_fraction': (w_eff - pitch) / w_eff,
        'min_coverage_count': min(counts), 'max_coverage_count': max(counts),
        'modal_coverage_count': modal, 'fully_covered': min(counts) >= 1,
        'stripes': stripes, 'resolution_m': res,
        'reasons': reasons, 'flags': flags,
        'limitations': ['Geometric footprint count only: no flow-rate distribution across '
                        'the fan, no heat-transfer coefficient, no drift or deflection.',
                        'Positions are barrel coordinates; map strip edges onto the barrel '
                        'before comparing with observed bands.'],
        'threshold_basis': 'Under-coverage is defined relative to the length-weighted modal '
                           'coverage count (analyst choice); stripe cause labels are '
                           'geometric (blocked-nozzle footprint overlap, barrel edge, else '
                           'nozzle pattern).',
        'sources': [SOURCES['lloyd_2010'], SOURCES['tucker_2006']]})


def free_thermal_radius_growth_m(roll_radius_m, expansion_coefficient_per_k,
                                 excess_temperature_k):
    """Free radial growth ``dR = alpha*R*dT``: an UPPER BOUND (no axial conduction)."""
    r = _num('roll_radius_m', roll_radius_m, positive=True, hi=5.0)
    a = _num('expansion_coefficient_per_k', expansion_coefficient_per_k, positive=True,
             hi=1e-4)
    dt = _num('excess_temperature_k', excess_temperature_k, lo=-200.0, hi=500.0)
    return a * r * dt


def local_gap_closure_fraction(radius_growth_m, exit_thickness_m):
    """Local gap closure ``2*dR/h_exit`` (both work rolls grow); rises as gauge thins."""
    dr = _num('radius_growth_m', radius_growth_m, lo=-1e-3, hi=1e-3)
    h = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.1)
    return 2 * dr / h


def thermal_stripe_screen(roll_radius_m, expansion_coefficient_per_k, excess_temperature_k,
                          exit_thickness_m):
    """Upper-bound local gap closure from a hot (under-cooled) stripe on both work rolls."""
    dr = free_thermal_radius_growth_m(roll_radius_m, expansion_coefficient_per_k,
                                      excess_temperature_k)
    frac = local_gap_closure_fraction(dr, exit_thickness_m)
    notable = abs(frac) >= GAP_CLOSURE_NOTABLE_FRACTION
    status = 'LOCAL_GAP_EFFECT_NOT_NEGLIGIBLE' if notable else 'LOCAL_GAP_EFFECT_SMALL'
    return _checked({
        'status': status, 'radius_growth_upper_bound_m': dr,
        'local_gap_closure_fraction': frac, 'exit_thickness_m': float(exit_thickness_m),
        'notable_fraction_threshold': GAP_CLOSURE_NOTABLE_FRACTION,
        'threshold_basis': 'ANALYST_CHOICE (1e-3); even smaller local gap differences can show '
                           'as flatness defects.',
        'reasons': [f'Free-expansion radius growth {dr:.3e} m closes the local gap by '
                    f'{frac:.3e} of the exit gauge.',
                    'The same roll growth is a larger fraction of thinner strip, so spray '
                    'stripes matter more as gauge thins.'],
        'flags': ['UPPER_BOUND_FREE_EXPANSION'],
        'limitations': ['Free expansion with no axial heat conduction overestimates the growth '
                        'of a narrow hot stripe, possibly by a large factor.',
                        'Strip lateral constraint converts most of a local gap difference into '
                        'elongation (flatness) rather than a thickness band.'],
        'sources': [SOURCES['lloyd_2010'], SOURCES['tucker_2006']]})


def match_band_positions(stripes, observed_positions_m, tolerance_m):
    """Match observed lengthwise-band positions to coverage stripes (same barrel coordinate)."""
    if not isinstance(stripes, (list, tuple)):
        raise ValueError('stripes must be a list of stripe dicts')
    checked = []
    for i, s in enumerate(stripes):
        if not isinstance(s, dict) or not {'start_m', 'end_m', 'coverage_count'} <= set(s):
            raise ValueError('stripes need start_m, end_m and coverage_count')
        a = _num(f'stripes[{i}].start_m', s['start_m'])
        b = _num(f'stripes[{i}].end_m', s['end_m'])
        if b < a:
            raise ValueError(f'stripes[{i}] end_m < start_m')
        checked.append((i, a, b, s))
    if not isinstance(observed_positions_m, (list, tuple)) or not observed_positions_m:
        raise ValueError('observed_positions_m must be a nonempty list of positions')
    tol = _num('tolerance_m', tolerance_m, nonnegative=True, hi=10.0)
    matches, unmatched = [], []
    used = set()
    for k, x in enumerate(observed_positions_m):
        x = _num(f'observed_positions_m[{k}]', x)
        hits = []
        for i, a, b, s in checked:
            dist = 0.0 if a <= x <= b else min(abs(x - a), abs(x - b))
            if dist <= tol:
                hits.append({'stripe_index': i, 'distance_m': dist, 'start_m': a, 'end_m': b,
                             'coverage_count': s['coverage_count']})
                used.add(i)
        hits.sort(key=lambda h: h['distance_m'])
        matches.append({'observed_position_m': x, 'matched_stripes': hits})
        if not hits:
            unmatched.append(x)
    n = len(matches)
    if not unmatched:
        status = 'ALL_OBSERVED_POSITIONS_MATCHED'
    elif len(unmatched) == n:
        status = 'NO_OBSERVED_POSITIONS_MATCHED'
    else:
        status = 'SOME_OBSERVED_POSITIONS_MATCHED'
    return _checked({
        'status': status, 'matches': matches, 'unmatched_positions_m': unmatched,
        'unexplained_stripe_indices': [i for i, *_ in checked if i not in used],
        'tolerance_m': tol,
        'reasons': [f'{n - len(unmatched)} of {n} observed band positions lie within '
                    f'{tol:g} m of a predicted stripe.'],
        'flags': [] if stripes else ['NO_PREDICTED_STRIPES'],
        'limitations': ['Observed positions and stripes must share one barrel coordinate; '
                        'strip tracking offsets must be removed by the caller.'],
        'threshold_basis': 'Tolerance supplied by the caller.',
        'sources': [SOURCES['lloyd_2010'], SOURCES['tucker_2006']]})
