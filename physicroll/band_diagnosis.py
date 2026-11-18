"""Band / chatter-mark root-cause SCREENING engine (opt-in, standard library only).

Status: ``SCREENING_RESULT_NOT_PLANT_VALIDATED``. This module wires the linear chatter
model (``physicroll.chatter``) and the kinematic / material / lubrication / spray screens
(``physicroll.band_signatures``) to one case file, then tallies observations against twenty
candidate band mechanisms in two families: ten TRANSVERSE (marks across the strip) and ten
LENGTHWISE (bands along the strip at fixed width positions, ``physicroll.band_width``). It
does NOT certify a cause and does NOT produce probabilities: each hypothesis gets an ordinal
evidence tally (score = sum of supports 3/2/1 minus sum of contradictions 6/2/1 for
strong/moderate/weak), and a standing.

Case file: JSON ``physicroll.band_case.v1`` or ``physicroll.band_case.v2`` with strict keys
(see ``docs/band-diagnosis.md``). v2 = v1 plus optional sections ``width_model``,
``tribology``, ``hardening``, ``gauge_control``, ``drive``, ``incoming_variation``, the option
``model_options.bite_model`` and thirteen lengthwise observation fields; the coupled process
sections live in ``physicroll.band_process``, the lengthwise physics and hypotheses in
``physicroll.band_width``. All quantities SI; unit suffix in every field name. ``null``
observations mean "not observed" and always give ``NOT_OBSERVED`` evidence, never a
contradiction.

Physics used (see the two modules for the equations and sign conventions):
- third-octave chatter: tension-feedback instability of the symmetric (gap-changing) stack
  mode; critical exit speed with the supplied bite-damping closure fraction beta and with
  beta = 0 (Tlusty et al. 1982; Hu, Zhao & Ehmann 2006; Kimura et al. 2003);
- pitch laws: fixed frequency F gives pitch p = u_x/F (proportional to speed); roll-borne or
  order-locked marks give p = pi*D*(1+f)/n (speed independent); coil-locked p = pi*D_coil
  (Kim et al. 2012, f = v/p; Krueger, Richard & Peretic 2019, order analysis);
- fifth octave: antisymmetric mode (both work rolls in phase between the backup rolls,
  600-1200 Hz, 10-40 mm pitch, little gauge change; Innoval Technology);
- bearing orders (Randall & Antoni 2011), Lueders / yield-point bending window, herringbone,
  forward slip, inlet film, spray coverage and free thermal growth (see band_signatures).

Interpretations of the evidence rules that the written rules leave open (documented in
``docs/band-diagnosis.md``):
- the set of observed frequencies f_obs is u/p for every pitch observation plus
  ``measured_vibration_hz`` when given (a measured stand frequency at the operating speed);
- a criterion evaluated per observation (frequency band, pitch band, pitch match) is reported
  as ONE evidence item whose verdict is the least favourable over the observations, because a
  single source must explain every observation and repeated observations must not be counted
  as independent evidence;
- coil-locked hypothesis: coil diameters supplied but no pitch match -> CONTRADICTS weak
  (mirrors the drive/bearing rule); coolant data with under-cooled stripes but observed band
  positions matching none of them -> CONTRADICTS weak (mirrors the uniform-coverage rule);
- only ``BLOCKED_NOZZLE`` stripes and ``UNCOVERED`` zones count as band-risk positions; the
  regular ``NOZZLE_PATTERN`` overlap alternation of a healthy header does not.
Rule CHANGED against the written spec: ``CONSISTENT_LEADING`` also needs at least one
SUPPORTS item based on a plant observation (model-only support could otherwise make a
hypothesis 'leading' with every observation null; see ``rank_hypotheses``).

Phase-2 fixes (SPEC6 6.0): lever directions are NOT_ASSESSABLE when the variant input equals
the baseline (zero tension) or both ratios are within 1e-9 of 1; span / damping variants are
built inside the handler, so a rejected variant is a rejected row, not an aborted diagnosis.

Phase 3 (SPEC9, battery foil 25-60 um): the v2 observation schema gains six OPTIONAL fields
(``bw.OBS_FOIL_BOOL``) and ``width_model.shape_inputs``; the width section runs without a bite
(its bite-free parts; shape parts individually NOT_ASSESSABLE); an exit gauge below 100 um adds
the flag ``CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED`` and the ``foil_regime`` block
(closed-gap onset 50-200 um reported, sources disagree [V S8, S16, S17]; NO roll-kissing
model; the lever table and gauge control assume an open gap; wrinkle rule of thumb
I = 1e5 * exit tension / E [V S27; D]); the strip map handles a leading torsional hypothesis
(pitch = u_op / matched computed torsional mode); a new rule-based lengthwise hypothesis
``foil_tension_lines`` [V S27, S28].

NOT modelled: anything band_signatures / chatter / the phase-2 modules do not model (limit
cycles, strip break, roll bending, film dynamics beyond the placeholder closure, time-domain
fifth-octave regeneration), and any plant calibration.
"""
import copy
from dataclasses import replace
import json
import math

from . import band_process as bp
from . import band_signatures as bs
from . import band_width as bw
from .chatter import (BitePass, BiteResponse, StandModel, StripSpans, critical_speed,
                      derive_bite_response, frequency_response, natural_frequencies, simulate,
                      stability)
from .foil_bite import derive_bite_response_mattress

CASE_SCHEMA_V1 = 'physicroll.band_case.v1'
CASE_SCHEMA_V2 = 'physicroll.band_case.v2'
CASE_SCHEMA = CASE_SCHEMA_V1          # phase-1 name kept (the v1 schema)
CASE_SCHEMAS = (CASE_SCHEMA_V1, CASE_SCHEMA_V2)
BITE_MODELS = ('hitchcock', 'mattress', 'auto')
MATTRESS_MIN_CELLS = 200
STATUS = 'SCREENING_RESULT_NOT_PLANT_VALIDATED'
REALISTIC_MAX_EXIT_SPEED_M_S = 35.0     # analyst choice: resonant speeds above are dropped
SPEED_SCAN_M_S = (0.05, 60.0)
GROWTH_CURVE_POINTS = 60
SPECTRUM_POINTS = 150
SPECTRUM_RANGE_HZ = (1.0, 2000.0)
TRACE_PERIODS = 40
TRACE_MAX_SAMPLES = 1200
RUNOUT_REFERENCE_M = 1e-6
TORSIONAL_GENERIC_BAND_HZ = (5.0, 30.0)
LEVER_UNITY_TOLERANCE = 1e-9
WEIGHT_POINTS_SUPPORT = {'strong': 3, 'moderate': 2, 'weak': 1}
WEIGHT_POINTS_CONTRADICT = {'strong': 6, 'moderate': 2, 'weak': 1}
VERDICTS = ('SUPPORTS', 'CONTRADICTS', 'NEUTRAL', 'NOT_OBSERVED')
ORIENTATIONS = ('transverse', 'diagonal', 'chevron', 'longitudinal', 'irregular')
FIRST_SEEN = ('bite_exit', 'incoming_strip', 'after_bending_or_levelling')
SCORE_NOTE = ('The score is an ordinal evidence tally (supports 3/2/1 minus contradictions '
              '6/2/1 for strong/moderate/weak), not a probability and not a certified cause.')

SOURCES = (
    'Tlusty, Chandra, Critchley, Paton (1982) "Chatter in Cold Rolling", CIRP Ann. 31:195, '
    'doi:10.1016/s0007-8506(07)63296-x (abstract only read).',
    'Yun, Wilson, Ehmann (1998) Int. J. Mach. Tools Manuf., doi:10.1016/s0890-6955(97)00133-8 '
    '(cited, not read).',
    'Hu, Zhao, Ehmann (2006) Proc. IMechE B, doi:10.1243/09544054B06804, as reproduced in '
    'Heidari & Forouzan (2013) J. Adv. Res., https://pmc.ncbi.nlm.nih.gov/articles/PMC4260885/',
    'Kimura, Sodani, Nishiura, Ikeuchi, Mihara (2003) ISIJ Int. 43:77 (5-DOF model, stability '
    'index, friction band).',
    'Niroomand, Forouzan, Salimi, Shojaei (2012) ISIJ Int. 52:2245, '
    'doi:10.2355/isijinternational.52.2245; (2015) ISIJ Int. 55:637.',
    'Zeng, Zang, Gao (2016) Shock & Vib., doi:10.1155/2016/2347386 (tension lowers critical '
    'speed).',
    'Innoval Technology (Farley): innovaltec.com mill-vibration, strip-chatter-marks and '
    'chatter-cold-rolling-mill blogs (fifth octave 600-1200 Hz, 10-40 mm pitch; aluminium '
    'case 315 Hz at 470 m/min = 2xBPFI of a work-roll bearing, 20-25 mm pitch).',
    'Krueger, Richard, Peretic (SMS group) AISTech 2019 "Chatter Management at Cold Rolling '
    'Mills Today" (order analysis).',
    'Kim, Kim, Park et al. (2012) ISIJ Int. 52:2042, doi:10.2355/isijinternational.52.2042 '
    '(f = v/p).',
    'Randall & Antoni (2011) MSSP, doi:10.1016/j.ymssp.2010.07.017 (bearing frequencies).',
    'Zhang et al. (2016) IET J. Eng., doi:10.1049/joe.2016.0182 (aluminium single-stand 4-high '
    'geometry).',
    'Heidari, Forouzan, Akbarzadeh (2014) ISIJ Int. 54:2349 (lumped stack values, steel mill).',
    'Aluminum Association (2002) Visual Quality Characteristics of Aluminum Sheet and Plate '
    'QCA-1, 4th ed.',
    'Choi, Jin, Kang (1998) Scripta Mater. 38(6):887 (Type A Lueders below ~40 um grain size).',
    'de Codes, Hopperstad, Engler, Lademo, Embury, Benallal (2011) Metall. Mater. Trans. A 42, '
    'doi:10.1007/s11661-011-0749-1 (5182-O band strain ~0.01).',
    'Reynolds US 4,081,294 (1978); Li et al. (2020) (cold work / pre-stretch removes the '
    'yield plateau).',
    'Mucsi (2018) Eng. Fail. Anal. 83, doi:10.1016/j.engfailanal.2017.09.022 (coil breaks).',
    'Komori (1996) J. Mater. Process. Technol. 60:377, doi:10.1016/0924-0136(96)02357-6 '
    '(herringbone pitch = arc of contact).',
    'Szucs et al. (2020) Mater. Sci. Eng. (Miskolc) 45(1):284; Alcoa US 5,508,119 (1996) citing '
    'Schey (1983) (herringbone onset ~40-45 % reduction).',
    'Reid & Schey (1978) ASLE Trans. 21(3), doi:10.1080/05698197808982874 (full film, negative '
    'forward slip).',
    'Sutcliffe (2002) in Lenard (ed.) Metal Forming Science and Practice, '
    'doi:10.1016/b978-008044024-8/50004-7 (film ratio regimes).',
    'Lloyd (Lechler, 2010) "Fundamentals of roll cooling and control of flatness at primary '
    'cold reduction"; Tucker (Lechler, 2006) "Flatness and profile ... spray actuators".',
)
DISAGREEMENTS = (
    'Effect of friction on chatter is disputed: Yarita (high friction worse), Chefneux (low '
    'friction worse), Kimura et al. 2003 (an optimum band). This model gives whatever its '
    'slab-derived sensitivities give; see the lever table.',
    'Effect of tension is disputed: Heidari (little effect) vs Zeng, Zang & Gao 2016 (higher '
    'tension lowers the critical speed).',
    'The lumped-spring strip span is inaccurate near the span axial wave resonance c/(2L) '
    '(about 640 Hz for a 4 m aluminium span); Niroomand et al. 2015 compare lumped and wave '
    'span models.',
)
LIMITATIONS = (
    'Screening result on unvalidated, uncalibrated models; no plant validation is claimed.',
    SCORE_NOTE,
    'The chatter model is linear: it cannot predict limit-cycle amplitude, mark severity or '
    'strip break, and a forced response at an unstable operating point is formal only.',
    'Strip spans are lumped springs (inaccurate near the span wave resonance c/(2L)).',
    'Circular (Hitchcock) roll flattening is not valid toward foil gauges; thinner passes need '
    'supplied bite sensitivities (model_options.bite_response_override).',
    'The bite-damping closure (fraction beta of transit time) is a declared heuristic; results '
    'without it (beta = 0) are reported alongside.',
    'Friction is an input unless tribology.use_computed_friction is set; the friction-speed '
    'closure of bite_tribology is an unfitted placeholder whose slope, not level, is used.',
    'Fifth-octave regeneration (backup-roll marking) is screened kinematically, not simulated '
    'in time; the antisymmetric mode frequency is an undamped lumped estimate.',
    'Spray coverage is a geometric footprint count; the phase-1 thermal growth is a '
    'free-expansion upper bound with no axial conduction (the v2 width_model solves the '
    'roll temperature field instead).',
    'The lengthwise physics (roll thermal stripes, shape chain, coil ridges, troughs) rests on '
    'planner-derived and memory formulas flagged in each result; no plant validation.',
)

# confirming tests and levers per hypothesis (drawn from mill practice; plain words)
HYPOTHESES = (
    ('third_octave_self_excited_chatter', 'Third-octave self-excited gauge chatter',
     'Tension-feedback instability of the symmetric (gap-changing) roll-stack mode: the gap '
     'opens, more strip is drawn in, entry tension rises with a 90 degree lag and the force '
     'component in phase with gap velocity feeds energy into the stack above a critical speed.',
     'Stone the strip and measure the mark pitch at two steady speeds: pitch should scale with '
     'speed (fixed frequency near the loaded symmetric mode); confirm thickness variation on '
     'the exit gauge or X-ray trace at that frequency during a slow speed ramp.',
     ('reduce exit speed below the critical speed', 'raise friction / adjust lubricant '
      'concentration or viscosity', 'lower the pass reduction', 'lower the entry tension',
      'lengthen or alter the free entry span', 'add damping to the stack')),
    ('fifth_octave_roll_stack_resonance', 'Fifth-octave roll-stack resonance',
     'Forced or resonant vibration of the antisymmetric mode (both work rolls moving together '
     'between the backup rolls, little gauge change), regenerated by marks printed on the '
     'backup roll.',
     'Chock accelerometers during a speed ramp: a resonance near the antisymmetric mode '
     '(600-1200 Hz class) with the two work-roll chocks in phase; inspect the backup-roll '
     'barrel for a faint regular pattern.',
     ('change speed away from the resonant speed of the exciting order',
      'regrind or change the backup rolls if they carry a printed pattern',
      'remove the order-locked excitation (bearing, gear, spindle)')),
    ('work_roll_borne_marks', 'Work-roll-borne marks (damage, ovality, grinder chatter)',
     'A mark, flat or grinder-chatter pattern on a work roll prints once (or n times) per '
     'revolution, so the strip pitch is the work-roll circumference over n.',
     'Measure the pitch and compare with the work-roll circumference times (1 + forward '
     'slip); inspect / profile the work roll; roll-change test.',
     ('change the work rolls', 'check grinding (wheel balance, chatter on the grinder)',
      'inspect the work-roll surface for damage or pick-up')),
    ('backup_roll_borne_marks', 'Backup-roll-borne marks',
     'A mark or pattern on a backup roll transfers at equal surface pitch to the work roll and '
     'then to the strip, so the pitch is the backup-roll circumference over n.',
     'Inspect the backup-roll barrel; compare the pitch with the backup-roll circumference '
     'times (1 + forward slip); backup-roll change test.',
     ('change / regrind the backup rolls', 'check backup-roll grinding quality')),
    ('order_locked_drive_or_bearing_excitation', 'Order-locked drive or bearing excitation',
     'A gear mesh, bearing defect or spindle order forces the stack at a fixed multiple of '
     'roll rotation, so the pitch stays constant when speed changes.',
     'Chock accelerometer speed-ramp order map: a line at a fixed order of work-roll rotation '
     'matching the mark pitch; bearing inspection (inner/outer race) or gearbox check.',
     ('replace the defective bearing / gear', 'align spindles and couplings',
      'avoid speeds where the order crosses a stack mode')),
    ('torsional_or_low_frequency_drive_vibration', 'Torsional / low-frequency drive vibration',
     'A drivetrain torsional mode or stick-slip in the 5-30 Hz range modulates roll speed and '
     'tension, printing long-pitch marks.',
     'Motor current / torque and tension signals: a 5-30 Hz component; check whether the '
     'mark pitch scales with speed.',
     ('retune drive speed / tension controllers', 'check couplings and spindle backlash')),
    ('coil_or_mandrel_locked_marks', 'Coil- or mandrel-locked marks',
     'A step, wrap or mandrel feature repeats once per coil revolution, so the pitch equals '
     'the coil circumference (drifting as the coil builds or pays off).',
     'Measure the pitch at the start and end of the coil: it should follow the coil '
     'circumference; inspect the mandrel, sleeve and tail/lead steps.',
     ('inspect the mandrel / sleeve and coil lead-end step', 'adjust coiling tension')),
    ('yield_point_bending_marks', 'Yield-point (Lueders Type A / coil-break) bending marks',
     'Annealed Al-Mg with a yield plateau yields discontinuously when bent over a roll or '
     'coil inside the yield-point window, leaving Lueders lines or coil-break kinks.',
     'Tensile test of the incoming strip for a yield-point plateau; check where the marks '
     'first appear (incoming coil, deflector roll, leveller).',
     ('temper / light pre-stretch (about 1-2 %) before bending', 'change deflector / coil '
      'diameters out of the yield-point window', 'raise strip tension at the bend')),
    ('herringbone_lubricant_film_breakdown', 'Herringbone (lubricant film breakdown)',
     'Periodic lubricant-film failure at heavy reduction repeats about once per arc of '
     'contact, giving chevron-shaped marks.',
     'Inspect the mark morphology (chevron); compare the pitch with the arc of contact; '
     'repeat the pass at lower reduction or with a more viscous lubricant.',
     ('lower the pass reduction', 'raise lubricant viscosity / concentration',
      'adjust roll roughness')),
    ('skidding_loss_of_forward_slip', 'Skidding / loss of forward slip',
     'With a thick film, low friction or high speed the neutral point moves to the exit and '
     'the rolls skid on the strip, giving irregular skid marks and a matte surface.',
     'Measure forward slip from roll and strip speed sensors; look for irregular skid marks '
     'and matte patches.',
     ('raise friction (lubricant change)', 'lower speed', 'raise reduction slightly')),
)
TRANSVERSE_HYPOTHESES = HYPOTHESES
HYPOTHESES = (tuple(h + ('transverse',) for h in TRANSVERSE_HYPOTHESES)
              + tuple(h + (bw.FAMILY,) for h in bw.LENGTHWISE_HYPOTHESES))
HYPOTHESIS_IDS = tuple(h[0] for h in HYPOTHESES)
HYPOTHESIS_FAMILIES = {h[0]: h[5] for h in HYPOTHESES}


# ============================================================================= validation
def _is_num(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _num(where, value, *, positive=False, nonnegative=False, lo=None, hi=None):
    if not _is_num(value):
        raise ValueError(f'{where} must be a finite number in SI units (not bool/null)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{where} must be > 0')
    if nonnegative and value < 0:
        raise ValueError(f'{where} must be >= 0')
    if lo is not None and value < lo:
        raise ValueError(f'{where} must be >= {lo}')
    if hi is not None and value > hi:
        raise ValueError(f'{where} must be <= {hi}')
    return value


def _opt_num(where, value, **kw):
    return None if value is None else _num(where, value, **kw)


def _opt_bool(where, value):
    if value is not None and not isinstance(value, bool):
        raise ValueError(f'{where} must be true, false or null')
    return value


def _text(where, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{where} must be a nonempty string')
    return value


def _keys(where, data, required, optional=()):
    if not isinstance(data, dict):
        raise ValueError(f'{where} must be a JSON object')
    missing = set(required) - set(data)
    unknown = set(data) - set(required) - set(optional)
    if missing or unknown:
        raise ValueError(f'{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}')


def _list(where, value):
    if not isinstance(value, list):
        raise ValueError(f'{where} must be a list')
    return value


PASS_KEYS = ('entry_thickness_m', 'exit_thickness_m', 'width_m', 'work_roll_radius_m',
             'mean_flow_stress_pa', 'friction_coefficient', 'entry_tension_pa',
             'exit_tension_pa', 'exit_speed_m_s')
MATERIAL_KEYS = ('alloy', 'temper', 'yield_stress_pa', 'youngs_modulus_pa', 'luders_strain',
                 'magnesium_wt_pct', 'grain_size_m')
STAND_KEYS = ('work_roll_mass_kg', 'backup_roll_mass_kg', 'work_backup_contact_stiffness_n_m',
              'housing_stiffness_n_m', 'modal_damping_ratio', 'roll_youngs_modulus_pa',
              'roll_poisson_ratio')
SPAN_KEYS = ('strip_youngs_modulus_pa', 'entry_span_length_m', 'exit_span_length_m')
KIN_KEYS = ('backup_roll_diameter_m', 'gear_meshes', 'bearings', 'grinder_marks',
            'deflector_roll_diameters_m', 'entry_coil_diameter_m', 'exit_coil_diameter_m')
LUB_KEYS = ('viscosity_pa_s', 'pressure_viscosity_coefficient_per_pa', 'roll_roughness_rq_m',
            'strip_roughness_rq_m')
COOLANT_KEYS = ('barrel_length_m', 'nozzle_pitch_m', 'standoff_m', 'spray_angle_rad',
                'offset_angle_rad', 'blocked_nozzle_indices', 'roll_expansion_coefficient_per_k',
                'assumed_excess_temperature_k')
OPTION_KEYS = ('bite_damping_transit_fraction', 'max_radius_ratio', 'cells',
               'bite_response_override')
OPTION_OPTIONAL = ('bite_model',)
OBS_KEYS = ('orientation', 'pitch_observations', 'faces', 'gauge_variation_detected',
            'gauge_variation_amplitude_m', 'first_seen', 'disappears_after_work_roll_change',
            'disappears_after_backup_roll_change', 'onset_above_exit_speed_m_s',
            'worse_at_thinner_gauge', 'band_positions_across_width_m', 'measured_vibration_hz')
SCHEDULE_KEYS = ('label', 'entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
                 'friction_coefficient', 'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s')
OVERRIDE_KEYS = tuple(k for k in BiteResponse.__dataclass_fields__ if k not in ('source', 'flags'))
TOP_REQUIRED = ('case_schema', 'name', 'synthetic', 'provenance', 'pass', 'material', 'stand',
                'spans', 'kinematics', 'lubrication', 'coolant', 'model_options', 'observation')
TOP_OPTIONAL = ('notes', 'schedule')
V2_SECTIONS = ('width_model', 'tribology', 'hardening', 'gauge_control', 'drive',
               'incoming_variation')


def _speed_value(where, value):
    return _num(where, value, positive=True, hi=bs.MAX_EXIT_SPEED_M_S)


def validate_case(case):
    """Strictly validate a band case dict; returns a normalised deep copy (floats, lists).

    Raises ValueError naming the offending key. Physics-domain checks that need the models
    (bite domain, roll geometry) are repeated by the models themselves.
    """
    if not isinstance(case, dict) or case.get('case_schema') not in CASE_SCHEMAS:
        raise ValueError(f'case_schema must be one of {CASE_SCHEMAS}')
    v2 = case['case_schema'] == CASE_SCHEMA_V2
    if not v2:
        # a validated v1 case carries the v2 sections as null: accept exactly that
        extra = [k for k in V2_SECTIONS if k in case and case[k] is not None]
        if extra:
            raise ValueError(f'sections {extra} need case_schema {CASE_SCHEMA_V2!r}')
        case = {k: v for k, v in case.items() if k not in V2_SECTIONS}
        ob = case.get('observation')
        if isinstance(ob, dict):
            extra = [k for k in bw.OBS_V2_ALL if k in ob and ob[k] is not None]
            if extra:
                raise ValueError(f'observation fields {extra} need case_schema '
                                 f'{CASE_SCHEMA_V2!r}')
            case['observation'] = {k: v for k, v in ob.items() if k not in bw.OBS_V2_ALL}
    _keys('case', case, TOP_REQUIRED, TOP_OPTIONAL + (V2_SECTIONS if v2 else ()))
    out = {'case_schema': case['case_schema'], 'name': _text('name', case['name'])}
    if not isinstance(case['synthetic'], bool):
        raise ValueError('synthetic must be true or false')
    out['synthetic'] = case['synthetic']
    out['provenance'] = _text('provenance', case['provenance'])
    notes = case.get('notes', [])
    if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
        raise ValueError('notes must be a list of strings')
    out['notes'] = list(notes)

    p = case['pass']
    _keys('pass', p, PASS_KEYS)
    out['pass'] = {k: _num(f'pass.{k}', p[k], nonnegative=True) for k in PASS_KEYS}
    _speed_value('pass.exit_speed_m_s', p['exit_speed_m_s'])
    for k in ('width_m', 'work_roll_radius_m', 'mean_flow_stress_pa', 'friction_coefficient',
              'exit_thickness_m'):
        _num(f'pass.{k}', p[k], positive=True)
    if not out['pass']['exit_thickness_m'] < out['pass']['entry_thickness_m']:
        raise ValueError('pass.exit_thickness_m must be below pass.entry_thickness_m')

    m = case['material']
    _keys('material', m, MATERIAL_KEYS)
    out['material'] = {
        'alloy': _text('material.alloy', m['alloy']),
        'temper': _text('material.temper', m['temper']),
        'yield_stress_pa': _num('material.yield_stress_pa', m['yield_stress_pa'], positive=True),
        'youngs_modulus_pa': _num('material.youngs_modulus_pa', m['youngs_modulus_pa'],
                                  lo=1e9, hi=1e12),
        'luders_strain': _opt_num('material.luders_strain', m['luders_strain'],
                                  nonnegative=True, hi=0.1),
        'magnesium_wt_pct': _opt_num('material.magnesium_wt_pct', m['magnesium_wt_pct'],
                                     nonnegative=True, hi=15.0),
        'grain_size_m': _opt_num('material.grain_size_m', m['grain_size_m'], positive=True,
                                 hi=5e-3)}

    s = case['stand']
    _keys('stand', s, STAND_KEYS)
    out['stand'] = {k: _num(f'stand.{k}', s[k], nonnegative=True) for k in STAND_KEYS}
    sp = case['spans']
    _keys('spans', sp, SPAN_KEYS)
    out['spans'] = {k: _num(f'spans.{k}', sp[k], positive=True) for k in SPAN_KEYS}

    k = case['kinematics']
    _keys('kinematics', k, KIN_KEYS)
    out['kinematics'] = {
        'backup_roll_diameter_m': _num('kinematics.backup_roll_diameter_m',
                                       k['backup_roll_diameter_m'], positive=True),
        'gear_meshes': [dict(g) if isinstance(g, dict) else g
                        for g in _list('kinematics.gear_meshes', k['gear_meshes'])],
        'bearings': [dict(b) if isinstance(b, dict) else b
                     for b in _list('kinematics.bearings', k['bearings'])],
        'grinder_marks': [dict(g) if isinstance(g, dict) else g
                          for g in _list('kinematics.grinder_marks', k['grinder_marks'])],
        'deflector_roll_diameters_m': [
            _num(f'kinematics.deflector_roll_diameters_m[{i}]', d, positive=True)
            for i, d in enumerate(_list('kinematics.deflector_roll_diameters_m',
                                        k['deflector_roll_diameters_m']))],
        'entry_coil_diameter_m': _opt_num('kinematics.entry_coil_diameter_m',
                                          k['entry_coil_diameter_m'], positive=True),
        'exit_coil_diameter_m': _opt_num('kinematics.exit_coil_diameter_m',
                                         k['exit_coil_diameter_m'], positive=True)}
    _mill(out, structural_modes=()).validate()   # nested gear/bearing/grinder dict checks

    lub = case['lubrication']
    if lub is None:
        out['lubrication'] = None
    else:
        _keys('lubrication', lub, LUB_KEYS)
        out['lubrication'] = {k2: _num(f'lubrication.{k2}', lub[k2], positive=True)
                              for k2 in LUB_KEYS}

    c = case['coolant']
    if c is None:
        out['coolant'] = None
    else:
        _keys('coolant', c, COOLANT_KEYS)
        blocked = _list('coolant.blocked_nozzle_indices', c['blocked_nozzle_indices'])
        for i, b in enumerate(blocked):
            if isinstance(b, bool) or not isinstance(b, int) or b < 0:
                raise ValueError(f'coolant.blocked_nozzle_indices[{i}] must be an int >= 0')
        out['coolant'] = {k2: _num(f'coolant.{k2}', c[k2])
                          for k2 in COOLANT_KEYS if k2 != 'blocked_nozzle_indices'}
        out['coolant']['blocked_nozzle_indices'] = sorted(set(blocked))

    o = case['model_options']
    _keys('model_options', o, OPTION_KEYS, OPTION_OPTIONAL)
    cells = o['cells']
    if isinstance(cells, bool) or not isinstance(cells, int) or not 64 <= cells <= 4096:
        raise ValueError('model_options.cells must be an integer in [64, 4096]')
    override = o['bite_response_override']
    if override is not None:
        _keys('model_options.bite_response_override', override, OVERRIDE_KEYS)
        override = {k2: _num(f'model_options.bite_response_override.{k2}', override[k2])
                    for k2 in OVERRIDE_KEYS}
    out['model_options'] = {
        'bite_damping_transit_fraction': _num('model_options.bite_damping_transit_fraction',
                                              o['bite_damping_transit_fraction'], lo=0, hi=5),
        'max_radius_ratio': _num('model_options.max_radius_ratio', o['max_radius_ratio'],
                                 lo=1.0, hi=3.0),
        'cells': cells, 'bite_response_override': override,
        'bite_model': o.get('bite_model', 'hitchcock')}
    if out['model_options']['bite_model'] not in BITE_MODELS:
        raise ValueError(f'model_options.bite_model must be one of {BITE_MODELS}')

    ob = case['observation']
    _keys('observation', ob, OBS_KEYS + (bw.OBS_V2_KEYS if v2 else ()),
          bw.OBS_V2_OPTIONAL if v2 else ())
    if ob['orientation'] is not None and ob['orientation'] not in ORIENTATIONS:
        raise ValueError(f'observation.orientation must be one of {ORIENTATIONS} or null')
    if ob['faces'] is not None and ob['faces'] not in ('both', 'one'):
        raise ValueError("observation.faces must be 'both', 'one' or null")
    if ob['first_seen'] is not None and ob['first_seen'] not in FIRST_SEEN:
        raise ValueError(f'observation.first_seen must be one of {FIRST_SEEN} or null')
    pitches = []
    for i, item in enumerate(_list('observation.pitch_observations', ob['pitch_observations'])):
        _keys(f'observation.pitch_observations[{i}]', item, ('exit_speed_m_s', 'pitch_m'))
        pitches.append({
            'exit_speed_m_s': _speed_value(f'observation.pitch_observations[{i}].exit_speed_m_s',
                                           item['exit_speed_m_s']),
            'pitch_m': _num(f'observation.pitch_observations[{i}].pitch_m', item['pitch_m'],
                            positive=True, hi=100.0)})
    out['observation'] = {
        'orientation': ob['orientation'], 'pitch_observations': pitches, 'faces': ob['faces'],
        'gauge_variation_detected': _opt_bool('observation.gauge_variation_detected',
                                              ob['gauge_variation_detected']),
        'gauge_variation_amplitude_m': _opt_num('observation.gauge_variation_amplitude_m',
                                                ob['gauge_variation_amplitude_m'],
                                                nonnegative=True),
        'first_seen': ob['first_seen'],
        'disappears_after_work_roll_change': _opt_bool(
            'observation.disappears_after_work_roll_change',
            ob['disappears_after_work_roll_change']),
        'disappears_after_backup_roll_change': _opt_bool(
            'observation.disappears_after_backup_roll_change',
            ob['disappears_after_backup_roll_change']),
        'onset_above_exit_speed_m_s': _opt_num('observation.onset_above_exit_speed_m_s',
                                               ob['onset_above_exit_speed_m_s'], positive=True),
        'worse_at_thinner_gauge': _opt_bool('observation.worse_at_thinner_gauge',
                                            ob['worse_at_thinner_gauge']),
        'band_positions_across_width_m': [
            _num(f'observation.band_positions_across_width_m[{i}]', x, nonnegative=True)
            for i, x in enumerate(_list('observation.band_positions_across_width_m',
                                        ob['band_positions_across_width_m']))],
        'measured_vibration_hz': _opt_num('observation.measured_vibration_hz',
                                          ob['measured_vibration_hz'], positive=True)}
    if v2:
        out['observation'].update(bw.validate_observation_v2(ob))
    else:
        out['observation'].update({k: None for k in bw.OBS_V2_ALL})

    sched = case.get('schedule', [])
    labels = set()
    out['schedule'] = []
    for i, row in enumerate(_list('schedule', sched)):
        _keys(f'schedule[{i}]', row, SCHEDULE_KEYS)
        label = _text(f'schedule[{i}].label', row['label'])
        if label in labels:
            raise ValueError(f'schedule label {label!r} is duplicated')
        labels.add(label)
        entry = {'label': label}
        for k2 in SCHEDULE_KEYS[1:]:
            entry[k2] = _num(f'schedule[{i}].{k2}', row[k2], nonnegative=True)
        _speed_value(f'schedule[{i}].exit_speed_m_s', row['exit_speed_m_s'])
        out['schedule'].append(entry)
    out.update(_validate_v2_sections(case if v2 else {}, out))
    return out


def _validate_v2_sections(case, out):
    """v2 optional sections (null/absent = not supplied), strict keys inside each."""
    sec = {k: case.get(k) for k in V2_SECTIONS}
    res = {}
    res['tribology'] = (None if sec['tribology'] is None
                        else bp.validate_tribology(sec['tribology']))
    res['hardening'] = (None if sec['hardening'] is None
                        else bp.validate_hardening(sec['hardening'], out['material']))
    res['gauge_control'] = (None if sec['gauge_control'] is None
                            else bp.validate_gauge_control(sec['gauge_control']))
    res['drive'] = None if sec['drive'] is None else bp.validate_drive(sec['drive'])
    res['incoming_variation'] = (None if sec['incoming_variation'] is None
                                 else bp.validate_incoming_variation(sec['incoming_variation']))
    res['width_model'] = (None if sec['width_model'] is None
                          else bw.validate_width_model(sec['width_model'], out['pass']))
    w = res['width_model']
    if w is not None and w['roll_heat_fraction_per_roll'] is None and res['tribology'] is None:
        raise ValueError('width_model.roll_heat_fraction_per_roll is required when tribology '
                         'is null (otherwise it is (1 - tribology.strip_heat_fraction)/2)')
    if (res['hardening'] is not None and res['hardening']['use_computed_flow_stress']
            and out['pass']['entry_thickness_m'] > res['hardening']['reference_thickness_m']
            * (1 + 1e-9)):
        raise ValueError('hardening.reference_thickness_m must be >= pass.entry_thickness_m')
    return res


def load_case(path):
    """Read and validate a case JSON file (NaN/Infinity literals are rejected)."""
    def reject(token):
        raise ValueError(f'non-finite JSON literal {token} is not allowed')
    with open(path, 'r', encoding='utf-8') as stream:
        raw = json.load(stream, parse_constant=reject)
    return validate_case(raw)


# ============================================================================= helpers
def _mill(case, structural_modes=()):
    k = case['kinematics']
    return bs.MillKinematics(
        work_roll_diameter_m=2 * case['pass']['work_roll_radius_m'],
        backup_roll_diameter_m=k['backup_roll_diameter_m'],
        gear_meshes=tuple(k['gear_meshes']), bearings=tuple(k['bearings']),
        grinder_marks=tuple(k['grinder_marks']),
        deflector_roll_diameters_m=tuple(k['deflector_roll_diameters_m']),
        entry_coil_diameter_m=k['entry_coil_diameter_m'],
        exit_coil_diameter_m=k['exit_coil_diameter_m'],
        structural_modes_hz=tuple(structural_modes))


def _stand(case, damping_scale=1.0):
    s = case['stand']
    return StandModel.from_modal_damping(
        s['work_roll_mass_kg'], s['backup_roll_mass_kg'], s['work_backup_contact_stiffness_n_m'],
        s['housing_stiffness_n_m'], s['modal_damping_ratio'] * damping_scale)


def _spans(case, entry_scale=1.0):
    sp = case['spans']
    return StripSpans(sp['strip_youngs_modulus_pa'], sp['entry_span_length_m'] * entry_scale,
                      sp['exit_span_length_m'])


def _bite_pass(case, row=None):
    p = case['pass']
    src = p if row is None else row
    return BitePass(src['entry_thickness_m'], src['exit_thickness_m'], p['width_m'],
                    p['work_roll_radius_m'], src['mean_flow_stress_pa'],
                    src['friction_coefficient'], src['entry_tension_pa'], src['exit_tension_pa'])


# chatter.BitePass.validate requires 2e-5 m <= exit thickness; both roll-bite models (slab /
# Hitchcock and the experimental mattress model) take a BitePass, so neither can represent a
# thinner pass (SPEC9 addendum: 16-18 um collector-foil final passes). Not changed here.
BITE_FLOOR_M = 2e-5
BITE_FLOOR_FLAG = 'EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR'
BITE_FLOOR_REASON = ('not derivable (exit gauge {:.3g} um below the 20 um floor of the roll-bite '
                     'models: chatter.BitePass.validate requires 2e-5 m <= exit thickness)')


class _BiteCache:
    """Caches bite derivations per (BitePass, options) within one diagnose call.

    ``model_options.bite_model``: 'hitchcock' (slab + circular flattening), 'mattress' (the
    EXPERIMENTAL elastic-foundation model, ``foil_bite``) or 'auto' (Hitchcock, and the
    mattress model when Hitchcock rejects the pass). Mattress bites carry the flag
    ``BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL``.
    """

    def __init__(self, case):
        self.case = case
        self.store = {}
        self.derivations = 0
        self.fallbacks = {}

    def _mattress(self, bite_pass):
        s, o = self.case['stand'], self.case['model_options']
        bite = derive_bite_response_mattress(
            bite_pass, roll_youngs_modulus_pa=s['roll_youngs_modulus_pa'],
            roll_poisson_ratio=s['roll_poisson_ratio'], cells=max(o['cells'], MATTRESS_MIN_CELLS))
        return bp.replace_bite_flags(bite, (bp.MATTRESS_FLAG,))

    def get(self, bite_pass, model=None):
        """Bite of ``bite_pass`` with the case's bite model, or with ``model`` ('hitchcock' /
        'mattress') to keep perturbed bites on the model of a reference bite."""
        s, o = self.case['stand'], self.case['model_options']
        model = o['bite_model'] if model is None else model
        key = (bite_pass, s['roll_youngs_modulus_pa'], s['roll_poisson_ratio'], o['cells'],
               o['max_radius_ratio'], model)
        if key not in self.store:
            try:
                if bite_pass.exit_thickness_m < BITE_FLOOR_M:
                    raise ValueError(BITE_FLOOR_REASON.format(
                        bite_pass.exit_thickness_m * 1e6))
                bite_pass.validate()
                self.derivations += 1
                if model == 'mattress':
                    self.store[key] = self._mattress(bite_pass)
                else:
                    try:
                        self.store[key] = derive_bite_response(
                            bite_pass, roll_youngs_modulus_pa=s['roll_youngs_modulus_pa'],
                            roll_poisson_ratio=s['roll_poisson_ratio'], cells=o['cells'],
                            max_radius_ratio=o['max_radius_ratio'])
                    except ValueError as exc:
                        if model != 'auto':
                            raise
                        try:
                            self.store[key] = self._mattress(bite_pass)
                        except ValueError as exc2:
                            raise ValueError(f'{exc}; experimental mattress fallback also '
                                             f'rejected: {exc2}') from exc2
                        self.fallbacks[key] = str(exc)
            except ValueError as exc:
                self.store[key] = exc
        value = self.store[key]
        if isinstance(value, Exception):
            raise ValueError(str(value))
        return value


def _opts(beta):
    return {'bite_damping_transit_fraction': beta}


def _crit_pair(stand, bite, spans, beta):
    c = critical_speed(stand, bite, spans, speed_range_m_s=SPEED_SCAN_M_S, **_opts(beta))
    zero = c.get('without_bite_damping', c)
    return c, zero


def _crit_value(c):
    """Critical speed for margin logic: None = stable over scan, lowest scan if unstable."""
    if c['status'] == 'UNSTABLE_AT_LOWEST_SCANNED_SPEED':
        return SPEED_SCAN_M_S[0]
    return c['critical_exit_speed_m_s']


def _roll_freqs(case, exit_speed, slip):
    vr = exit_speed / (1 + slip)
    dw = 2 * case['pass']['work_roll_radius_m']
    db = case['kinematics']['backup_roll_diameter_m']
    return {'work_roll_1x': vr / (math.pi * dw), 'work_roll_2x': 2 * vr / (math.pi * dw),
            'backup_roll_1x': vr / (math.pi * db), 'backup_roll_2x': 2 * vr / (math.pi * db)}


def _logspace(lo, hi, n):
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def _fmt(value, unit='', digits=4):
    if value is None:
        return 'n/a'
    return f'{value:.{digits}g}{(" " + unit) if unit else ""}'


def _ev(criterion, observed, expected, verdict, weight=None, basis='observation'):
    assert verdict in VERDICTS
    if verdict in ('SUPPORTS', 'CONTRADICTS'):
        assert weight in WEIGHT_POINTS_SUPPORT
    else:
        weight = None
    return {'criterion': criterion, 'observed': observed, 'expected': expected,
            'verdict': verdict, 'weight': weight, 'basis': basis}


_RANK = {('CONTRADICTS', 'strong'): 0, ('CONTRADICTS', 'moderate'): 1,
         ('CONTRADICTS', 'weak'): 2, ('NEUTRAL', None): 3, ('SUPPORTS', 'weak'): 4,
         ('SUPPORTS', 'moderate'): 5, ('SUPPORTS', 'strong'): 6}


def _least_favourable(items):
    """items: [(verdict, weight, note)] -> the least favourable one (see module docstring)."""
    return min(items, key=lambda t: _RANK[(t[0], t[1])])


# ============================================================================= sections
def _supplied_bite(case):
    """The operating bite from ``model_options.bite_response_override`` (validated), or None.
    Built once per diagnosis so every section that needs the operating bite uses this object."""
    override = case['model_options']['bite_response_override']
    if override is None:
        return None
    bp = _bite_pass(case)
    bite = BiteResponse(**override, source='supplied',
                        flags=('SUPPLIED_BITE_SENSITIVITIES_NOT_VERIFIED',))
    bite.validate()
    if (abs(bite.entry_thickness_m - bp.entry_thickness_m) > 1e-12
            or abs(bite.exit_thickness_m - bp.exit_thickness_m) > 1e-12):
        raise ValueError('bite_response_override thicknesses must equal the pass thicknesses')
    return bite


def _section_bite(case, cache, flags, supplied=None):
    bp = _bite_pass(case)
    if supplied is not None:
        flags.append('BITE_RESPONSE_SUPPLIED')
        return supplied, None
    try:
        return cache.get(bp), None
    except ValueError as exc:
        flags.append('BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE')
        return None, str(exc)


def _section_chatter(stand, bite, spans, u_op, beta):
    stab = stability(stand, bite, spans, u_op, **_opts(beta))
    crit, crit0 = _crit_pair(stand, bite, spans, beta)
    uc, uc0 = crit['critical_exit_speed_m_s'], crit0['critical_exit_speed_m_s']
    curve = []
    for u in _logspace(SPEED_SCAN_M_S[0], SPEED_SCAN_M_S[1], GROWTH_CURVE_POINTS):
        s = stability(stand, bite, spans, u, **_opts(beta))
        g0 = s['without_bite_damping']['max_growth_rate_per_s'] if 'without_bite_damping' in s \
            else s['max_growth_rate_per_s']
        curve.append({'exit_speed_m_s': u, 'max_growth_rate_per_s': s['max_growth_rate_per_s'],
                      'max_growth_rate_without_bite_damping_per_s': g0})
    stab0 = stab.get('without_bite_damping', {'max_growth_rate_per_s':
                                              stab['max_growth_rate_per_s'],
                                              'stable': stab['stable'],
                                              'dominant_frequency_hz':
                                              stab['dominant_frequency_hz']})
    return {
        'status': stab['status'], 'operating_exit_speed_m_s': u_op,
        'bite_damping_transit_fraction': beta,
        'stability': stab, 'critical_speed': crit,
        'with_bite_damping': {
            'bite_damping_transit_fraction': beta, 'critical_exit_speed_m_s': uc,
            'critical_status': crit['status'], 'onset_frequency_hz': crit['onset_frequency_hz'],
            'onset_strip_pitch_m': crit['onset_strip_pitch_m'],
            'speed_ratio': (u_op / uc) if uc else None,
            'stable_at_operating_speed': stab['stable'],
            'max_growth_rate_per_s': stab['max_growth_rate_per_s']},
        'without_bite_damping': {
            'bite_damping_transit_fraction': 0.0, 'critical_exit_speed_m_s': uc0,
            'critical_status': crit0['status'], 'onset_frequency_hz': crit0['onset_frequency_hz'],
            'onset_strip_pitch_m': crit0['onset_strip_pitch_m'],
            'speed_ratio': (u_op / uc0) if uc0 else None,
            'stable_at_operating_speed': stab0['stable'],
            'max_growth_rate_per_s': stab0['max_growth_rate_per_s']},
        'growth_curve': curve,
        'flags': list(crit['flags']), 'limitations': list(crit['limitations'])}


def _section_time(stand, bite, spans, u_op, beta, dominant_hz):
    duration = TRACE_PERIODS / dominant_hz
    sim = simulate(stand, bite, spans, u_op, duration_s=duration,
                   initial_gap_perturbation_m=1e-3 * bite.exit_thickness_m,
                   max_samples=TRACE_MAX_SAMPLES, **_opts(beta))
    f = sim['dominant_frequency_hz']
    sim['duration_requested_s'] = duration
    sim['initial_gap_perturbation_m'] = 1e-3 * bite.exit_thickness_m
    sim['predicted_strip_pitch_from_trace_m'] = (u_op / f) if f else None
    return sim


def _section_forced(case, stand, bite, spans, u_op, beta, unstable):
    h1 = bite.exit_thickness_m
    freqs = _roll_freqs(case, u_op, bite.forward_slip_fraction)
    out = {'reference_disturbance_m': RUNOUT_REFERENCE_M, 'operating_exit_speed_m_s': u_op,
           'operating_point_unstable': unstable, 'flags': [], 'limitations': []}
    if unstable:
        out['flags'].append('FORCED_RESPONSE_AT_UNSTABLE_OPERATING_POINT_FORMAL_ONLY')
        out['limitations'].append('The operating point is linearly unstable: the transfer '
                                  'function exists but no steady forced response does.')
    for dist in ('work_backup_runout', 'entry_thickness'):
        names = sorted(freqs)
        rows = frequency_response(stand, bite, spans, u_op, [freqs[n] for n in names],
                                  disturbance=dist, **_opts(beta))
        table = []
        for name, row in zip(names, rows):
            ripple = row['exit_thickness_per_unit_disturbance'] * RUNOUT_REFERENCE_M
            table.append({'source': name, 'frequency_hz': row['frequency_hz'],
                          'exit_thickness_per_unit_disturbance': row[
                              'exit_thickness_per_unit_disturbance'],
                          'exit_ripple_per_um_m': ripple,
                          'relative_exit_ripple_per_um': ripple / h1})
        spec = frequency_response(stand, bite, spans, u_op,
                                  _logspace(*SPECTRUM_RANGE_HZ, SPECTRUM_POINTS),
                                  disturbance=dist, **_opts(beta))
        out[dist] = {'roll_orders': table,
                     'spectrum': [{'frequency_hz': r['frequency_hz'],
                                   'exit_thickness_per_unit_disturbance':
                                       r['exit_thickness_per_unit_disturbance']} for r in spec]}
    return out


def _section_signatures(case, mill_kw_modes, slip, u_op, h_ratio, obs, flags):
    mill = _mill(case, mill_kw_modes)
    catalogue = bs.source_catalogue(mill, u_op, slip, entry_exit_thickness_ratio=h_ratio)
    sig = {'forward_slip_fraction_used': slip, 'catalogue': catalogue,
           'pitch_speed_exponent': None, 'law': None, 'observations': []}
    pitches = obs['pitch_observations']
    speeds = {p['exit_speed_m_s'] for p in pitches}
    if len(pitches) >= 2 and len(speeds) >= 2:
        pse = bs.pitch_speed_exponent([(p['exit_speed_m_s'], p['pitch_m']) for p in pitches])
        sig['pitch_speed_exponent'] = pse
        sig['law'] = pse['classification']
    elif pitches:
        sig['law_note'] = 'Pitch-speed law needs pitch at two or more distinct exit speeds.'
    for p in pitches:
        cat = bs.source_catalogue(mill, p['exit_speed_m_s'], slip,
                                  entry_exit_thickness_ratio=h_ratio)
        hits = bs.match_observed_pitch(cat, p['pitch_m'])
        sig['observations'].append({
            'exit_speed_m_s': p['exit_speed_m_s'], 'pitch_m': p['pitch_m'],
            'implied_frequency_hz': p['exit_speed_m_s'] / p['pitch_m'],
            'matches': [{'id': h['id'], 'kind': h['kind'], 'strip_pitch_m': h['strip_pitch_m'],
                         'frequency_hz': h['frequency_hz'],
                         'relative_pitch_mismatch': h['relative_pitch_mismatch']}
                        for h in hits]})
    sig['resonance_speeds'] = {}
    plain = _mill(case, ())
    for m in mill_kw_modes:
        if m['name'] not in ('antisymmetric_upper', 'symmetric_lower_loaded'):
            continue
        rows = bs.resonance_speeds(plain, slip, m['frequency_hz'])
        kept = [r for r in rows if r['resonant_exit_speed_m_s'] <= REALISTIC_MAX_EXIT_SPEED_M_S]
        sig['resonance_speeds'][m['name']] = {
            'mode_frequency_hz': m['frequency_hz'], 'family': m['family'],
            'realistic_max_exit_speed_m_s': REALISTIC_MAX_EXIT_SPEED_M_S,
            'dropped_above_realistic_speed': len(rows) - len(kept), 'crossings': kept}
    return sig


def _section_screens(case, bite, slip, contact_length, contact_radius_ratio, flags):
    p, m, k = case['pass'], case['material'], case['kinematics']
    h0, h1 = p['entry_thickness_m'], p['exit_thickness_m']
    red = (h0 - h1) / h0
    scr = {}
    scr['luders_susceptibility'] = bs.luders_susceptibility(
        m['alloy'], m['temper'], m['magnesium_wt_pct'], m['grain_size_m'])
    el = m['luders_strain']
    el_used = 0.0 if el is None else el
    if el is None:
        flags.append('LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS')
    windows = []
    bends = [(f'deflector_roll:{i}', d, h1, p['exit_tension_pa'])
             for i, d in enumerate(k['deflector_roll_diameters_m'])]
    if k['entry_coil_diameter_m'] is not None:
        bends.append(('entry_coil', k['entry_coil_diameter_m'], h0, p['entry_tension_pa']))
    if k['exit_coil_diameter_m'] is not None:
        bends.append(('exit_coil', k['exit_coil_diameter_m'], h1, p['exit_tension_pa']))
    for name, d, t, tension in bends:
        try:
            w = bs.yield_point_bending_window(t, d, m['yield_stress_pa'], m['youngs_modulus_pa'],
                                              el_used, tension)
            w = {'location': name, 'diameter_m': d, 'thickness_m': t, **w}
        except ValueError as exc:
            w = {'location': name, 'diameter_m': d, 'thickness_m': t, 'status': 'REJECTED',
                 'error': str(exc)}
        windows.append(w)
    scr['bending_windows'] = windows
    scr['pass_reduction_vs_luders'] = bs.pass_reduction_vs_luders(red, el_used)
    contact_basis = 'derived_bite'
    if contact_length is None:
        contact_length = math.sqrt(p['work_roll_radius_m'] * (h0 - h1))
        contact_basis = 'undeformed_roll_estimate_sqrt_R_draft'
    pitches = case['observation']['pitch_observations']
    hb = bs.herringbone_screen(red, contact_length,
                               pitches[0]['pitch_m'] if len(pitches) == 1 else None)
    hb['contact_length_basis'] = contact_basis
    scr['herringbone'] = hb
    scr['forward_slip'] = bs.forward_slip_screen(slip) if bite is not None else None
    lub = case['lubrication']
    if lub is not None and bite is not None:
        vr = p['exit_speed_m_s'] / (1 + slip)
        theta = bs.inlet_angle_rad(h0, h1, p['work_roll_radius_m'] * contact_radius_ratio)
        film = bs.inlet_film_thickness_wilson_walowit(
            lub['viscosity_pa_s'], lub['pressure_viscosity_coefficient_per_pa'], vr,
            p['exit_speed_m_s'] * h1 / h0, theta, 2 / math.sqrt(3) * p['mean_flow_stress_pa'])
        film['inlet_angle_rad'] = theta
        scr['film'] = film
        scr['film_regime'] = bs.film_ratio_regime(film['film_thickness_m'],
                                                  lub['roll_roughness_rq_m'],
                                                  lub['strip_roughness_rq_m'])
    else:
        scr['film'] = scr['film_regime'] = None
    c = case['coolant']
    if c is not None:
        cov = bs.spray_coverage(c['barrel_length_m'], c['nozzle_pitch_m'], c['standoff_m'],
                                c['spray_angle_rad'], c['offset_angle_rad'],
                                tuple(c['blocked_nozzle_indices']))
        risk = [s for s in cov['stripes']
                if s['cause'] == 'BLOCKED_NOZZLE' or (s['kind'] == 'UNCOVERED'
                                                      and not s['at_barrel_edge'])]
        tol = 0.25 * c['nozzle_pitch_m']
        scr['spray_coverage'] = cov
        scr['coverage_profile'] = _coverage_profile(cov, c['barrel_length_m'])
        scr['band_risk_stripes'] = risk
        scr['band_risk_rule'] = ('Band-risk stripes are BLOCKED_NOZZLE stripes and interior '
                                 'UNCOVERED zones; the regular NOZZLE_PATTERN overlap '
                                 'alternation and barrel-edge zones are not counted.')
        scr['thermal'] = bs.thermal_stripe_screen(
            p['work_roll_radius_m'], c['roll_expansion_coefficient_per_k'],
            c['assumed_excess_temperature_k'], h1)
        positions = case['observation']['band_positions_across_width_m']
        if positions and risk:
            match = bs.match_band_positions(risk, positions, tol)
        elif positions:
            match = {'status': 'NO_BAND_RISK_STRIPES', 'tolerance_m': tol, 'matches': []}
        else:
            match = None
        scr['band_position_match'] = match
        scr['band_position_tolerance_m'] = tol
        scr['band_position_tolerance_basis'] = 'ANALYST_CHOICE: one quarter of the nozzle pitch'
    else:
        scr['spray_coverage'] = scr['thermal'] = scr['band_position_match'] = None
        scr['coverage_profile'] = None
        scr['band_risk_stripes'] = None
    return scr


def _coverage_profile(cov, length):
    """Full piecewise-constant fan-overlap count across the barrel (for plotting)."""
    w = cov['effective_footprint_width_m']
    active = [x for i, x in enumerate(cov['nozzle_positions_m'])
              if i not in cov['blocked_nozzle_indices']]
    cuts = sorted({0.0, length} | {e for x in active for e in (x - w / 2, x + w / 2)
                                    if 0 < e < length})
    zones = []
    for a, b in zip(cuts, cuts[1:]):
        count = sum(1 for x in active if abs((a + b) / 2 - x) < w / 2)
        if zones and zones[-1]['coverage_count'] == count:
            zones[-1]['end_m'] = b
        else:
            zones.append({'start_m': a, 'end_m': b, 'coverage_count': count})
    return {'barrel_length_m': length, 'zones': zones}


def _lever_rows(case, cache, stand, spans, bite, beta, override):
    p = case['pass']
    h0, h1 = p['entry_thickness_m'], p['exit_thickness_m']
    red = (h0 - h1) / h0
    base_c, base_c0 = _crit_pair(stand, bite, spans, beta)
    base = base_c['critical_exit_speed_m_s']
    specs = []
    for k in (0.7, 1.3):
        specs.append(('friction', 'friction_coefficient', k,
                      {'friction_coefficient': p['friction_coefficient'] * k}))
    for k in (0.8, 1.2):
        specs.append(('reduction', 'reduction_fraction (exit thickness varied, entry fixed)', k,
                      {'exit_thickness_m': h0 * (1 - red * k)}))
    for k in (0.5, 1.5):
        specs.append(('entry_tension', 'entry_tension_pa', k,
                      {'entry_tension_pa': p['entry_tension_pa'] * k}))
    for k in (0.5, 1.5):
        specs.append(('exit_tension', 'exit_tension_pa', k,
                      {'exit_tension_pa': p['exit_tension_pa'] * k}))
    rows = []
    bp = _bite_pass(case)
    for lever, param, k, change in specs:
        row = {'lever': lever, 'parameter': param, 'factor': k,
               'change': f'{param} x{k:g}'}
        variant = replace(bp, **change)
        if variant == bp:
            # SPEC6 6.0 bug 2: a multiplicative change of a zero parameter is no change
            row['variant_equals_baseline'] = True
        try:
            if override is not None:
                raise ValueError('bite sensitivities were supplied: this lever needs a '
                                 're-derived or re-supplied bite response')
            b = cache.get(variant)
            c, c0 = _crit_pair(stand, b, spans, beta)
            row.update(critical_exit_speed_m_s=c['critical_exit_speed_m_s'],
                       critical_exit_speed_without_bite_damping_m_s=c0['critical_exit_speed_m_s'],
                       contact_radius_ratio=b.contact_radius_ratio)
        except ValueError as exc:
            row['rejected'] = str(exc)
        rows.append(row)
    # SPEC6 6.0 bug 3: each span / damping variant is built inside the handler, so a rejected
    # variant (e.g. a doubled modal damping ratio >= 1) becomes a rejected row instead of
    # aborting the whole diagnosis
    for lever, param, k, build in (
            ('entry_span', 'entry_span_length_m', 0.5, lambda: (stand, _spans(case, 0.5))),
            ('entry_span', 'entry_span_length_m', 2.0, lambda: (stand, _spans(case, 2.0))),
            ('structural_damping', 'modal_damping_ratio', 0.5, lambda: (_stand(case, 0.5), spans)),
            ('structural_damping', 'modal_damping_ratio', 2.0, lambda: (_stand(case, 2.0), spans))):
        row = {'lever': lever, 'parameter': param, 'factor': k, 'change': f'{param} x{k:g}'}
        try:
            st, sp = build()
            c, c0 = _crit_pair(st, bite, sp, beta)
            row.update(critical_exit_speed_m_s=c['critical_exit_speed_m_s'],
                       critical_exit_speed_without_bite_damping_m_s=c0['critical_exit_speed_m_s'],
                       contact_radius_ratio=bite.contact_radius_ratio)
        except ValueError as exc:
            row['rejected'] = str(exc)
        rows.append(row)
    for row in rows:
        if 'rejected' in row:
            row['ratio_to_baseline'] = None
            continue
        u = row['critical_exit_speed_m_s']
        row['ratio_to_baseline'] = (u / base) if (u is not None and base) else None
        if row['ratio_to_baseline'] is None:
            row['note'] = 'critical speed outside the scanned range for baseline or variant'
    rows.sort(key=lambda r: (r['ratio_to_baseline'] is None,
                             -abs(math.log(r['ratio_to_baseline']))
                             if r['ratio_to_baseline'] else 0.0, r['lever'], r['factor']))
    names = {'friction': 'friction', 'reduction': 'pass reduction',
             'entry_tension': 'entry tension', 'exit_tension': 'exit tension',
             'entry_span': 'entry span length', 'structural_damping': 'structural damping'}
    directions = []
    for lever in ('friction', 'reduction', 'entry_tension', 'exit_tension', 'entry_span',
                  'structural_damping'):
        pair = sorted((r for r in rows if r['lever'] == lever), key=lambda r: r['factor'])
        lo, hi = pair[0], pair[1]
        rl, rh = lo['ratio_to_baseline'], hi['ratio_to_baseline']
        nm = names[lever]
        same_input = all(r.get('variant_equals_baseline') for r in pair)
        unity = (rl is not None and rh is not None and abs(rl - 1) <= LEVER_UNITY_TOLERANCE
                 and abs(rh - 1) <= LEVER_UNITY_TOLERANCE)
        if same_input or unity:
            reason = ('both variants equal the baseline input (the parameter is zero, so a '
                      'multiplicative change has no effect)' if same_input else
                      f'both ratios are within {LEVER_UNITY_TOLERANCE:g} of 1')
            text = f'{nm}: not assessable ({reason})'
            trend = 'NOT_ASSESSABLE'
        elif rl is None and rh is None:
            text = f'{nm}: not assessable (both variants rejected or outside the scan)'
            trend = 'NOT_ASSESSABLE'
        elif rl is not None and rh is not None and (rl - 1) * (rh - 1) > 0:
            text = (f'{nm}: non-monotonic over x{lo["factor"]:g}..x{hi["factor"]:g} '
                    f'(ratios {rl:.3f}, {rh:.3f})')
            trend = 'NON_MONOTONIC'
        else:
            # direction of the critical speed when the parameter is RAISED
            if rh is not None:
                raises = rh > 1
                evidence = f'x{hi["factor"]:g} -> ratio {rh:.3f}'
            else:
                raises = rl < 1
                evidence = f'x{lo["factor"]:g} -> ratio {rl:.3f}'
            if rl is not None and rh is not None:
                evidence = (f'x{lo["factor"]:g} -> ratio {rl:.3f}; '
                            f'x{hi["factor"]:g} -> ratio {rh:.3f}')
            trend = 'RAISES' if raises else 'LOWERS'
            text = (f'lower {nm} {"lowers" if raises else "raises"} the chatter-free (critical) '
                    f'exit speed; higher {nm} {"raises" if raises else "lowers"} it ({evidence})')
        directions.append({'lever': lever, 'raising_parameter_effect_on_critical_speed': trend,
                           'direction': text})
    return {'baseline_critical_exit_speed_m_s': base,
            'baseline_critical_exit_speed_without_bite_damping_m_s':
                base_c0['critical_exit_speed_m_s'],
            'bite_damping_transit_fraction': beta, 'rows': rows, 'directions': directions,
            'note': 'Work-roll radius is not a lever. Ratios are critical exit speed of the '
                    'variant over the baseline with the supplied bite-damping fraction.'}


def _case_bite(case, cache, op_bite, bite_pass_, src):
    """Bite of a schedule pass: the operating bite when the row IS the case pass (every
    bite-defining parameter equal, ``bw.is_case_pass`` on the effective case) and one exists
    (review finding: with a supplied bite the row re-derived a different one); else derived."""
    if op_bite is not None and bw.is_case_pass(case, src):
        return op_bite
    return cache.get(bite_pass_)


def _schedule_rows(case, cache, stand, spans, beta, op_bite=None):
    rows = []
    p = case['pass']
    k = case['kinematics']
    defl = min(k['deflector_roll_diameters_m']) if k['deflector_roll_diameters_m'] else None
    c = case['coolant']
    growth = None
    if c is not None:
        growth = bs.free_thermal_radius_growth_m(p['work_roll_radius_m'],
                                                 c['roll_expansion_coefficient_per_k'],
                                                 c['assumed_excess_temperature_k'])
    for row in case['schedule']:
        h0, h1, u = row['entry_thickness_m'], row['exit_thickness_m'], row['exit_speed_m_s']
        out = {'label': row['label'], 'entry_thickness_m': h0, 'exit_thickness_m': h1,
               'reduction_fraction': (h0 - h1) / h0 if h0 > 0 else None,
               'exit_speed_m_s': u, 'friction_coefficient': row['friction_coefficient'],
               'mean_flow_stress_pa': row['mean_flow_stress_pa'],
               'entry_tension_pa': row['entry_tension_pa'],
               'exit_tension_pa': row['exit_tension_pa'],
               'bending_strain_smallest_deflector': (
                   bs.bending_surface_strain(h1, defl) if defl and 0 < h1 < defl else None),
               'thermal_gap_closure_fraction_upper_bound': (
                   bs.local_gap_closure_fraction(growth, h1) if growth is not None and h1 > 0
                   else None)}
        try:
            bp = _bite_pass(case, row)
            b = _case_bite(case, cache, op_bite, bp, row)
            cr, cr0 = _crit_pair(stand, b, spans, beta)
            uc, uc0 = cr['critical_exit_speed_m_s'], cr0['critical_exit_speed_m_s']
            fr = _roll_freqs(case, u, b.forward_slip_fraction)['work_roll_2x']
            resp = frequency_response(stand, b, spans, u, [fr], **_opts(beta))[0]
            st = stability(stand, b, spans, u, **_opts(beta))
            ripple = resp['exit_thickness_per_unit_disturbance'] * RUNOUT_REFERENCE_M
            out.update(
                separating_force_n=b.separating_force_n,
                separating_force_per_width_n_m=b.separating_force_n / p['width_m'],
                bite_model=bw.bite_model_name(b),
                contact_radius_ratio=b.contact_radius_ratio,
                forward_slip_fraction=b.forward_slip_fraction,
                strip_modulus_n_m=b.strip_modulus_n_m,
                strip_to_mill_modulus_ratio=b.strip_modulus_n_m / stand.mill_modulus_n_m,
                bite_flags=list(b.flags),
                critical_exit_speed_m_s=uc, critical_status=cr['status'],
                critical_exit_speed_without_bite_damping_m_s=uc0,
                speed_ratio=(u / uc) if uc else None,
                speed_ratio_without_bite_damping=(u / uc0) if uc0 else None,
                onset_frequency_hz=cr['onset_frequency_hz'],
                onset_strip_pitch_m=cr['onset_strip_pitch_m'],
                pitch_at_operating_speed_m=(u / cr['onset_frequency_hz']
                                            if cr['onset_frequency_hz'] else None),
                stable_at_operating_speed=st['stable'],
                work_roll_2x_frequency_hz=fr,
                exit_ripple_per_um_runout_at_work_roll_2x_m=ripple,
                relative_ripple_per_um_runout_at_work_roll_2x=ripple / h1)
            if not st['stable']:
                out['note'] = ('operating point linearly unstable: forced ripple is formal only')
        except ValueError as exc:
            out['rejected'] = str(exc)
        # same pass at the case (final-pass) friction: separates gauge from friction effects
        ref_mu = p['friction_coefficient']
        same = {'friction_coefficient': ref_mu}
        try:
            b2 = _case_bite(case, cache, op_bite,
                            replace(_bite_pass(case, row), friction_coefficient=ref_mu),
                            dict(row, friction_coefficient=ref_mu))
            c2, c20 = _crit_pair(stand, b2, spans, beta)
            same.update(critical_exit_speed_m_s=c2['critical_exit_speed_m_s'],
                        critical_exit_speed_without_bite_damping_m_s=c20[
                            'critical_exit_speed_m_s'],
                        strip_modulus_n_m=b2.strip_modulus_n_m)
        except ValueError as exc:
            same['rejected'] = str(exc)
        out['at_case_friction'] = same
        rows.append(out)
    return {'bite_damping_transit_fraction': beta, 'rows': rows,
            'smallest_deflector_roll_diameter_m': defl,
            'thermal_radius_growth_upper_bound_m': growth,
            'note': ('Each pass uses its own gauge, flow stress, friction, tensions and speed on '
                     'the case stand and spans. at_case_friction repeats the critical-speed '
                     'calculation at the case pass friction so the gauge effect can be read '
                     'separately from the friction effect. pitch_at_operating_speed_m = '
                     'exit speed / onset frequency (beta as supplied).')}


# ============================================================================= hypotheses
class _Ctx:
    pass


def _orientation_chatter(o):
    if o is None:
        return _ev('orientation', 'not observed', 'transverse', 'NOT_OBSERVED')
    if o == 'transverse':
        return _ev('orientation', o, 'transverse', 'SUPPORTS', 'moderate')
    if o == 'longitudinal':
        return _ev('orientation', o, 'transverse', 'CONTRADICTS', 'strong')
    if o in ('diagonal', 'chevron'):
        return _ev('orientation', o, 'transverse', 'CONTRADICTS', 'moderate')
    return _ev('orientation', o, 'transverse', 'NEUTRAL')


def _law_ev(ctx, sup, contra, label_ff='FIXED_FREQUENCY', criterion='pitch-speed law'):
    """sup/contra: dict law -> weight."""
    if ctx.law is None:
        return _ev(criterion, 'pitch not observed at two distinct speeds', label_ff,
                   'NOT_OBSERVED')
    obs = f'{ctx.law} (exponent {ctx.slope:.3f})'
    if ctx.law in sup:
        return _ev(criterion, obs, label_ff, 'SUPPORTS', sup[ctx.law])
    if ctx.law in contra:
        return _ev(criterion, obs, label_ff, 'CONTRADICTS', contra[ctx.law])
    return _ev(criterion, obs, label_ff, 'NEUTRAL')


def _per_freq(ctx, criterion, expected, rule):
    if not ctx.freqs:
        return _ev(criterion, 'no pitch or vibration frequency observed', expected,
                   'NOT_OBSERVED')
    items = [rule(f) + (label,) for label, f in ctx.freqs]
    v, w, _ = _least_favourable(items)
    observed = '; '.join(f'{label}: {f:.4g} Hz' for label, f in ctx.freqs)
    if len(items) > 1:
        observed += ' (least favourable observation decides)'
    return _ev(criterion, observed, expected, v, w)


def _per_pitch(ctx, criterion, expected, rule, basis='observation'):
    if not ctx.pitches:
        return _ev(criterion, 'pitch not observed', expected, 'NOT_OBSERVED', basis=basis)
    items = [rule(p) for p in ctx.pitches]
    v, w, _ = _least_favourable(items)
    observed = '; '.join(f'{p["pitch_m"] * 1e3:.4g} mm at {p["exit_speed_m_s"]:.4g} m/s'
                         + (f' ({note})' if note else '')
                         for p, (_, _, note) in zip(ctx.pitches, items))
    return _ev(criterion, observed, expected, v, w, basis)


def _faces(ctx, both=None, one=None):
    f = ctx.obs['faces']
    if f is None:
        return _ev('faces', 'not observed', 'both or one face', 'NOT_OBSERVED')
    rule = both if f == 'both' else one
    if rule is None:
        return _ev('faces', f, 'n/a', 'NEUTRAL')
    return _ev('faces', f, rule[2], rule[0], rule[1])


def _h_chatter(ctx):
    o = ctx.obs
    ev = [_orientation_chatter(o['orientation']),
          _law_ev(ctx, {'FIXED_FREQUENCY': 'strong'}, {'SPEED_INDEPENDENT_PITCH': 'strong'})]
    model_f = [] if ctx.chatter_unreliable else [f for f in (ctx.dominant_hz, ctx.onset_hz)
                                                 if f]

    def rule(f):
        if model_f and any(abs(f - m) <= 0.15 * m for m in model_f):
            return ('SUPPORTS', 'strong')
        if 90 <= f <= 300:
            return ('SUPPORTS', 'moderate')
        if f < 60 or f > 400:
            return ('CONTRADICTS', 'strong')
        return ('NEUTRAL', None)
    exp = ('within +-15 % of model frequency ' +
           (', '.join(f'{m:.4g} Hz' for m in model_f) if model_f else
            '(NOT_ASSESSABLE: ' + str(ctx.bite_error) + ')') +
           '; else 90-300 Hz; outside 60-400 Hz contradicts')
    ev.append(_per_freq(ctx, 'observed frequency u/p', exp, rule))
    g = o['gauge_variation_detected']
    ev.append(_ev('gauge variation', 'not observed' if g is None else
                  ('detected' if g else 'not detected'), 'detected',
                  'NOT_OBSERVED' if g is None else ('SUPPORTS' if g else 'CONTRADICTS'),
                  None if g is None else ('strong' if g else 'moderate')))
    ev.append(_faces(ctx, both=('SUPPORTS', 'weak', 'both'), one=('CONTRADICTS', 'moderate',
                                                                  'both')))
    u = ctx.u_op
    if ctx.chatter is None:
        ev.append(_ev('speed margin', f'operating {u:.4g} m/s',
                      f'NOT_ASSESSABLE: {ctx.bite_error}', 'NEUTRAL', basis='model'))
    elif ctx.chatter_unreliable:
        ev.append(_ev('speed margin', f'operating {u:.4g} m/s; onset frequency above the span '
                      'wave limit c/(2L)', 'NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT: no model-based '
                      'evidence', 'NEUTRAL', basis='model'))
    else:
        uc, uc0 = ctx.ucrit, ctx.ucrit0
        obs_txt = (f'operating {u:.4g} m/s; u_crit(beta={ctx.beta:g}) = {_fmt(uc, "m/s")}, '
                   f'u_crit(0) = {_fmt(uc0, "m/s")}')
        if uc is not None and u >= uc:
            ev.append(_ev('speed margin', obs_txt, 'u_op >= u_crit(beta)', 'SUPPORTS', 'strong',
                          'model'))
        elif uc0 is not None and u >= uc0:
            ev.append(_ev('speed margin', obs_txt + ' (inside the band set by the unvalidated '
                          'bite-damping closure)', 'u_op >= u_crit(beta)', 'SUPPORTS', 'weak',
                          'model'))
        else:
            ev.append(_ev('speed margin', obs_txt, 'u_op >= u_crit(0)', 'CONTRADICTS',
                          'moderate', 'model'))
    on = o['onset_above_exit_speed_m_s']
    if on is None:
        ev.append(_ev('onset speed', 'not observed', 'a speed threshold', 'NOT_OBSERVED'))
    elif ctx.ucrit is not None and 0.6 * ctx.ucrit <= on <= 1.6 * ctx.ucrit:
        ev.append(_ev('onset speed', f'{on:.4g} m/s',
                      f'0.6-1.6 x u_crit(beta) = {0.6 * ctx.ucrit:.4g}-{1.6 * ctx.ucrit:.4g} m/s',
                      'SUPPORTS', 'moderate'))
    else:
        ev.append(_ev('onset speed', f'{on:.4g} m/s', 'a speed threshold (characteristic); '
                      'not within 0.6-1.6 x u_crit(beta)' if ctx.ucrit else
                      'a speed threshold (characteristic)', 'SUPPORTS', 'weak'))
    wr, br = o['disappears_after_work_roll_change'], o['disappears_after_backup_roll_change']
    if wr is None and br is None:
        ev.append(_ev('roll-change test', 'not observed', 'persists', 'NOT_OBSERVED'))
    elif wr or br:
        ev.append(_ev('roll-change test', f'disappears after work-roll change: {wr}; '
                      f'backup-roll change: {br}', 'persists', 'CONTRADICTS', 'moderate'))
    else:
        ev.append(_ev('roll-change test', f'work-roll change: {wr}; backup-roll change: {br}',
                      'persists', 'NEUTRAL'))
    ev.append(_worse_thin(o, 'SUPPORTS', 'weak'))
    pred = {'critical_exit_speed_m_s': ctx.ucrit, 'critical_exit_speed_without_bite_damping_m_s':
            ctx.ucrit0, 'speed_ratio': ctx.speed_ratio, 'onset_frequency_hz': ctx.onset_hz,
            'dominant_frequency_at_operating_speed_hz': ctx.dominant_hz,
            'predicted_pitch_at_operating_speed_m': (ctx.u_op / ctx.dominant_hz
                                                     if ctx.dominant_hz else None),
            'bite_error': ctx.bite_error}
    return ev, pred


def _worse_thin(o, verdict, weight):
    w = o['worse_at_thinner_gauge']
    if w is None:
        return _ev('worse at thinner gauge', 'not observed', 'true', 'NOT_OBSERVED')
    if w:
        return _ev('worse at thinner gauge', 'true', 'true' if verdict == 'SUPPORTS' else
                   'false (bending strain t/D falls with gauge)', verdict, weight)
    return _ev('worse at thinner gauge', 'false', 'n/a', 'NEUTRAL')


def _h_fifth(ctx):
    o = ctx.obs
    fa = ctx.anti_upper_hz
    ev = [_orientation_chatter(o['orientation'])]

    def rule(f):
        if abs(f - fa) <= 0.15 * fa:
            return ('SUPPORTS', 'strong')
        if 500 <= f <= 1200:
            return ('SUPPORTS', 'moderate')
        if f < 300:
            return ('CONTRADICTS', 'strong')
        return ('NEUTRAL', None)
    ev.append(_per_freq(ctx, 'observed frequency u/p',
                        f'within +-15 % of antisymmetric upper mode {fa:.4g} Hz; else '
                        '500-1200 Hz; below 300 Hz contradicts', rule))
    ev.append(_per_pitch(ctx, 'pitch 10-40 mm', '10-40 mm',
                         lambda p: ('SUPPORTS', 'moderate', '') if 0.010 <= p['pitch_m'] <= 0.040
                         else ('NEUTRAL', None, '')))
    g = o['gauge_variation_detected']
    ev.append(_ev('gauge variation', 'not observed' if g is None else
                  ('detected' if g else 'not detected'), 'not detected',
                  'NOT_OBSERVED' if g is None else ('CONTRADICTS' if g else 'SUPPORTS'),
                  None if g is None else ('weak' if g else 'moderate')))
    if ctx.law == 'SPEED_INDEPENDENT_PITCH':
        def near_int(p):
            n = math.pi * ctx.db * (1 + ctx.slip) / p['pitch_m']
            ok = n >= 0.95 and abs(n - round(n)) <= 0.05
            return (('SUPPORTS', 'moderate', f'pi*D_b*(1+f)/p = {n:.3f}') if ok
                    else ('NEUTRAL', None, f'pi*D_b*(1+f)/p = {n:.3f}'))
        e = _per_pitch(ctx, 'pitch-speed law',
                       'FIXED_FREQUENCY, or SPEED_INDEPENDENT_PITCH with pi*D_b*(1+f)/p '
                       'within 0.05 of an integer (backup roll already marked)', near_int)
        e['observed'] = f'SPEED_INDEPENDENT_PITCH (exponent {ctx.slope:.3f}); ' + e['observed']
        ev.append(e)
    else:
        ev.append(_law_ev(ctx, {'FIXED_FREQUENCY': 'moderate'}, {}))
    near = [e for e in ctx.catalogue if e['kind'] == bs.KIND_ORDER_LOCKED
            and e['frequency_hz'] and abs(e['frequency_hz'] - fa) <= 0.10 * fa]
    near.sort(key=lambda e: (abs(e['frequency_hz'] - fa), e['id']))
    if near:
        e0 = near[0]
        ev.append(_ev('order-locked source near the antisymmetric mode at u_op',
                      f'{e0["id"]} at {e0["frequency_hz"]:.4g} Hz', f'within +-10 % of {fa:.4g} Hz',
                      'SUPPORTS', 'moderate', 'model'))
    else:
        ev.append(_ev('order-locked source near the antisymmetric mode at u_op', 'none',
                      f'within +-10 % of {fa:.4g} Hz', 'NEUTRAL', basis='model'))
    br = o['disappears_after_backup_roll_change']
    ev.append(_ev('backup-roll change', 'not observed' if br is None else str(br).lower(),
                  'disappears', 'NOT_OBSERVED' if br is None else ('SUPPORTS' if br else
                                                                    'NEUTRAL'),
                  'moderate' if br else None))
    ev.append(_faces(ctx, both=('SUPPORTS', 'weak', 'both')))
    res = ctx.signatures['resonance_speeds'].get('antisymmetric_upper', {})
    pred = {'antisymmetric_upper_mode_hz': fa,
            'pitch_at_operating_speed_m': ctx.u_op / fa,
            'resonant_crossings_within_realistic_speed': [
                {'id': r['id'], 'resonant_exit_speed_m_s': r['resonant_exit_speed_m_s'],
                 'strip_pitch_m': r['strip_pitch_m']} for r in res.get('crossings', [])[:6]]}
    return ev, pred


def _roll_mark(ctx, diameter, roll, label):
    marks = sorted({g['marks_per_circumference'] for g in ctx.case['kinematics']['grinder_marks']
                    if g['roll'] == roll})
    ns = sorted(set(range(1, 9)) | set(marks))

    def rule(p):
        best = min(ns, key=lambda n: abs(math.pi * diameter * (1 + ctx.slip) / n - p['pitch_m']))
        pred = math.pi * diameter * (1 + ctx.slip) / best
        mis = abs(pred - p['pitch_m']) / p['pitch_m']
        if mis <= 0.03:
            return ('SUPPORTS', 'strong', f'n = {best}, mismatch {mis:.2%}')
        return ('CONTRADICTS', 'moderate', f'closest n = {best}, mismatch {mis:.2%}')
    return _per_pitch(ctx, f'pitch = pi*D_{label}*(1+f)/n',
                      f'within 3 % for n in 1..8 or grinder marks {marks}', rule)


def _h_roll(ctx, which):
    o = ctx.obs
    work = which == 'work'
    d = ctx.dw if work else ctx.db
    ev = [_law_ev(ctx, {'SPEED_INDEPENDENT_PITCH': 'strong'}, {'FIXED_FREQUENCY': 'strong'},
                  'SPEED_INDEPENDENT_PITCH'),
          _roll_mark(ctx, d, 'work_roll' if work else 'backup_roll', 'w' if work else 'b')]
    own = o['disappears_after_work_roll_change' if work else
            'disappears_after_backup_roll_change']
    name = 'work-roll change' if work else 'backup-roll change'
    ev.append(_ev(name, 'not observed' if own is None else str(own).lower(), 'disappears',
                  'NOT_OBSERVED' if own is None else ('SUPPORTS' if own else 'CONTRADICTS'),
                  None if own is None else 'strong'))
    if not work:
        wr = o['disappears_after_work_roll_change']
        ev.append(_ev('work-roll change', 'not observed' if wr is None else str(wr).lower(),
                      'persists', 'NOT_OBSERVED' if wr is None else
                      ('CONTRADICTS' if wr else 'NEUTRAL'), 'strong' if wr else None))
    ev.append(_faces(ctx, both=('CONTRADICTS', 'weak', 'one'), one=('SUPPORTS', 'moderate',
                                                                     'one')))
    ori = o['orientation']
    ev.append(_ev('orientation', 'not observed' if ori is None else ori, 'not longitudinal',
                  'NOT_OBSERVED' if ori is None else
                  ('CONTRADICTS' if ori == 'longitudinal' else 'NEUTRAL'),
                  'strong' if ori == 'longitudinal' else None))
    pred = {'roll_diameter_m': d, 'pitch_one_mark_m': math.pi * d * (1 + ctx.slip),
            'pitch_two_marks_m': math.pi * d * (1 + ctx.slip) / 2,
            'forward_slip_fraction_used': ctx.slip}
    return ev, pred


def _h_order(ctx):
    o = ctx.obs
    k = ctx.case['kinematics']
    ev = [_law_ev(ctx, {'SPEED_INDEPENDENT_PITCH': 'strong'}, {'FIXED_FREQUENCY': 'strong'},
                  'SPEED_INDEPENDENT_PITCH')]
    cands = [e for e in ctx.catalogue if e['source_group'] in ('gear_mesh', 'bearing')
             or e['id'] == 'work_roll_2x']
    best = None
    crit = 'best gear / bearing / spindle source match'
    # the spindle / coupling candidate (work_roll_2x) follows from the work-roll diameter and
    # speed, so it is matched even without gear or bearing geometry; the missing geometry
    # only qualifies the absence of a gear / bearing match
    no_geometry = not k['gear_meshes'] and not k['bearings']
    if not ctx.pitches and ctx.obs['measured_vibration_hz'] is None:
        ev.append(_ev(crit, 'no pitch or vibration frequency observed', 'match within 5 %',
                      'NOT_OBSERVED'))
    elif not cands:
        ev.append(_ev(crit, 'no drive/bearing geometry supplied', 'match within 5 %',
                      'NOT_OBSERVED', basis='input'))
    else:
        scored = []
        for e in cands:
            mis = [abs(e['strip_pitch_m'] - p['pitch_m']) / p['pitch_m'] for p in ctx.pitches]
            fm = ctx.obs['measured_vibration_hz']
            if fm is not None:
                mis.append(abs(e['frequency_hz'] - fm) / fm)
            scored.append((max(mis), e['id'], e))
        scored.sort(key=lambda t: (t[0], t[1]))
        mis, _, e = scored[0]
        best = {'id': e['id'], 'description': e['description'],
                'order_of_work_roll_rotation': e['order_of_work_roll_rotation'],
                'strip_pitch_m': e['strip_pitch_m'], 'frequency_at_operating_speed_hz':
                e['frequency_hz'], 'worst_relative_mismatch': mis}
        txt = (f'{e["id"]} (order {e["order_of_work_roll_rotation"]:.4g}, pitch '
               f'{e["strip_pitch_m"] * 1e3:.4g} mm, {e["frequency_hz"]:.4g} Hz at u_op), '
               f'mismatch {mis:.2%}')
        if mis <= 0.05:
            if no_geometry:
                txt += ('; no drive/bearing geometry supplied, so only the spindle / coupling '
                        'candidate was checked')
            ev.append(_ev(crit, txt, 'match within 5 %', 'SUPPORTS', 'strong'))
        elif no_geometry:
            ev.append(_ev(crit, 'no drive/bearing geometry supplied (no gear / bearing match '
                          'assessable); spindle / coupling candidate ' + txt,
                          'match within 5 %', 'NOT_OBSERVED', basis='input'))
        else:
            ev.append(_ev(crit, txt, 'match within 5 %', 'CONTRADICTS', 'weak'))
    wr, br = o['disappears_after_work_roll_change'], o['disappears_after_backup_roll_change']
    if wr is None and br is None:
        ev.append(_ev('roll-change test', 'not observed', 'persists after both',
                      'NOT_OBSERVED'))
    elif wr is False and br is False:
        ev.append(_ev('roll-change test', 'persists after work- and backup-roll change',
                      'persists after both', 'SUPPORTS', 'weak'))
    else:
        ev.append(_ev('roll-change test', f'work-roll change: {wr}; backup-roll change: {br}',
                      'persists after both', 'NEUTRAL'))
    ev.append(_faces(ctx, both=('SUPPORTS', 'weak', 'both')))
    ori = o['orientation']
    ev.append(_ev('orientation', 'not observed' if ori is None else ori, 'not longitudinal',
                  'NOT_OBSERVED' if ori is None else
                  ('CONTRADICTS' if ori == 'longitudinal' else 'NEUTRAL'),
                  'strong' if ori == 'longitudinal' else None))
    pred = {'best_match': best, 'candidate_count': len(cands),
            'candidates': [{'id': e['id'], 'strip_pitch_m': e['strip_pitch_m'],
                            'frequency_at_operating_speed_hz': e['frequency_hz']}
                           for e in sorted(cands, key=lambda e: e['id'])]}
    return ev, pred


def _h_torsional(ctx):
    o = ctx.obs
    modes = [m['frequency_hz'] for m in ctx.drive_modes]
    if modes:
        # SPEC6 6.2: computed torsional modes replace the generic 5-30 Hz band
        top = max(TORSIONAL_GENERIC_BAND_HZ[1] * 2, 1.5 * max(modes))

        def rule(f):
            if any(abs(f - m) <= 0.15 * m for m in modes):
                return ('SUPPORTS', 'strong')
            if f > top:
                return ('CONTRADICTS', 'strong')
            return ('NEUTRAL', None)
        expected = (f'within +-15 % of a torsional mode ({", ".join(f"{m:.4g}" for m in modes)} '
                    f'Hz); above {top:.4g} Hz contradicts')
    else:
        def rule(f):
            if 5 <= f <= 30:
                return ('SUPPORTS', 'strong')
            if f > 60:
                return ('CONTRADICTS', 'strong')
            return ('NEUTRAL', None)
        expected = '5-30 Hz; above 60 Hz contradicts'
    ev = [_per_freq(ctx, 'observed frequency u/p', expected, rule),
          _per_pitch(ctx, 'pitch 0.1-3 m', '0.1-3 m',
                     lambda p: ('SUPPORTS', 'weak', '') if 0.1 <= p['pitch_m'] <= 3
                     else ('NEUTRAL', None, '')),
          _law_ev(ctx, {'FIXED_FREQUENCY': 'moderate'}, {})]
    ori = o['orientation']
    ev.append(_ev('orientation', 'not observed' if ori is None else ori, 'not longitudinal',
                  'NOT_OBSERVED' if ori is None else
                  ('CONTRADICTS' if ori == 'longitudinal' else 'NEUTRAL'),
                  'strong' if ori == 'longitudinal' else None))
    pred = {'pitch_range_at_operating_speed_m': [ctx.u_op / 30, ctx.u_op / 5]}
    if modes:
        pred = {'torsional_modes_hz': modes,
                'pitch_at_operating_speed_m': [ctx.u_op / m for m in modes]}
    return ev, pred


def _h_coil(ctx):
    o = ctx.obs
    k = ctx.case['kinematics']
    p = ctx.case['pass']
    targets = []
    if k['exit_coil_diameter_m'] is not None:
        targets.append(('exit coil', math.pi * k['exit_coil_diameter_m']))
    if k['entry_coil_diameter_m'] is not None:
        targets.append(('entry coil', math.pi * k['entry_coil_diameter_m'] *
                        p['entry_thickness_m'] / p['exit_thickness_m']))
    crit = 'pitch = pi*D_exit_coil or pi*D_entry_coil*h0/h1'
    if not targets:
        ev = [_ev(crit, 'coil diameters not supplied', 'within 10 %', 'NOT_OBSERVED',
                  basis='input')]
    else:
        def rule(pp):
            name, t = min(targets, key=lambda t: abs(t[1] - pp['pitch_m']))
            mis = abs(t - pp['pitch_m']) / pp['pitch_m']
            note = f'{name} pitch {t:.4g} m, mismatch {mis:.1%}'
            return (('SUPPORTS', 'strong', note) if mis <= 0.10 else
                    ('CONTRADICTS', 'weak', note))
        ev = [_per_pitch(ctx, crit, 'within 10 % (no match: CONTRADICTS weak, filled rule)',
                         rule)]
        if ctx.pitches:
            # the coil that matches the observations best (smallest worst mismatch) is the one
            # the strip map draws
            worst = sorted((max(abs(t - pp['pitch_m']) / pp['pitch_m'] for pp in ctx.pitches),
                            name) for name, t in targets)
            matched, matched_mis = worst[0][1], worst[0][0]
    fs = o['first_seen']
    ev.append(_ev('first seen', 'not observed' if fs is None else fs, 'incoming_strip',
                  'NOT_OBSERVED' if fs is None else
                  ('SUPPORTS' if fs == 'incoming_strip' else 'NEUTRAL'),
                  'weak' if fs == 'incoming_strip' else None))
    ev.append(_law_ev(ctx, {}, {'FIXED_FREQUENCY': 'moderate'}, 'drifting / speed independent'))
    pred = {'coil_pitches_m': {n: t for n, t in targets}}
    if targets and ctx.pitches:
        pred.update(matched_coil=matched, matched_coil_worst_relative_mismatch=matched_mis)
    return ev, pred


def _h_yield(ctx):
    o = ctx.obs
    scr = ctx.screens
    sus = scr['luders_susceptibility']['status']
    if sus.startswith('NOT_SUSCEPTIBLE'):
        ev = [_ev('Lueders susceptibility', sus, 'SUSCEPTIBLE', 'CONTRADICTS', 'strong',
                  'input')]
    elif sus.startswith('SUSCEPTIBLE'):
        ev = [_ev('Lueders susceptibility', sus, 'SUSCEPTIBLE', 'SUPPORTS', 'moderate',
                  'input')]
    else:
        ev = [_ev('Lueders susceptibility', sus, 'SUSCEPTIBLE', 'NOT_OBSERVED', basis='input')]
    ori = o['orientation']
    if ori is None:
        ev.append(_ev('orientation', 'not observed', 'diagonal or irregular', 'NOT_OBSERVED'))
    elif ori in ('diagonal', 'irregular'):
        ev.append(_ev('orientation', ori, 'diagonal or irregular', 'SUPPORTS', 'moderate'))
    elif ori in ('chevron', 'longitudinal'):
        ev.append(_ev('orientation', ori, 'diagonal or irregular', 'CONTRADICTS', 'moderate'))
    else:
        ev.append(_ev('orientation', ori, 'diagonal or irregular', 'NEUTRAL'))
    ev.append(_law_ev(ctx, {}, {'FIXED_FREQUENCY': 'moderate',
                                'SPEED_INDEPENDENT_PITCH': 'moderate'},
                      'no regular machine-locked pitch'))
    fs = o['first_seen']
    if fs is None:
        ev.append(_ev('first seen', 'not observed', 'incoming or after bending/levelling',
                      'NOT_OBSERVED'))
    elif fs in ('incoming_strip', 'after_bending_or_levelling'):
        ev.append(_ev('first seen', fs, 'incoming or after bending/levelling', 'SUPPORTS',
                      'strong'))
    elif ctx.reduction > 0.02:
        ev.append(_ev('first seen', f'{fs} with pass reduction {ctx.reduction:.3f}',
                      'not at bite exit after a > 2 % reduction', 'CONTRADICTS', 'strong'))
    else:
        ev.append(_ev('first seen', f'{fs} with pass reduction {ctx.reduction:.3f}',
                      'incoming or after bending/levelling', 'NEUTRAL'))
    wins = [w for w in scr['bending_windows'] if w.get('status') != 'REJECTED']
    inside = [w['location'] for w in wins if w['status'] == 'IN_YIELD_POINT_WINDOW']
    if not wins:
        ev.append(_ev('deflector / coil in yield-point bending window',
                      'no deflector or coil diameters supplied', 'at least one', 'NOT_OBSERVED',
                      basis='input'))
    elif inside:
        ev.append(_ev('deflector / coil in yield-point bending window', ', '.join(inside),
                      'at least one', 'SUPPORTS', 'moderate', 'model'))
    else:
        ev.append(_ev('deflector / coil in yield-point bending window',
                      ', '.join(f'{w["location"]}: {w["status"]}' for w in wins),
                      'at least one', 'CONTRADICTS', 'weak', 'model'))
    ev.append(_worse_thin(o, 'CONTRADICTS', 'moderate'))
    pred = {'luders_susceptibility': sus,
            'bending_windows': [{'location': w['location'], 'status': w['status'],
                                 'bending_surface_strain': w.get('bending_surface_strain')}
                                for w in scr['bending_windows']],
            'pass_reduction_vs_luders': scr['pass_reduction_vs_luders']['status']}
    return ev, pred


def _h_herringbone(ctx):
    o = ctx.obs
    scr = ctx.screens
    ori = o['orientation']
    if ori is None:
        ev = [_ev('orientation', 'not observed', 'chevron', 'NOT_OBSERVED')]
    elif ori == 'chevron':
        ev = [_ev('orientation', ori, 'chevron', 'SUPPORTS', 'strong')]
    elif ori == 'diagonal':
        ev = [_ev('orientation', ori, 'chevron', 'SUPPORTS', 'weak')]
    elif ori == 'longitudinal':
        ev = [_ev('orientation', ori, 'chevron', 'CONTRADICTS', 'strong')]
    else:
        ev = [_ev('orientation', ori, 'chevron', 'NEUTRAL')]
    red = ctx.reduction
    ev.append(_ev('pass reduction', f'{red:.3f}', '>= 0.40 (< 0.25 contradicts)',
                  'SUPPORTS' if red >= 0.40 else ('CONTRADICTS' if red < 0.25 else 'NEUTRAL'),
                  'moderate' if (red >= 0.40 or red < 0.25) else None, 'input'))
    lc = scr['herringbone']['contact_length_m']

    def rule(p):
        r = p['pitch_m'] / lc
        if 0.5 <= r <= 2:
            return ('SUPPORTS', 'strong', f'{r:.3g} x contact length')
        if r > 5:
            return ('CONTRADICTS', 'moderate', f'{r:.3g} x contact length')
        return ('NEUTRAL', None, f'{r:.3g} x contact length')
    ev.append(_per_pitch(ctx, 'pitch vs contact length',
                         f'0.5-2 x contact length {lc * 1e3:.4g} mm (> 5 x contradicts)', rule))
    g = o['gauge_variation_detected']
    ev.append(_ev('gauge variation', 'not observed' if g is None else
                  ('detected' if g else 'not detected'), 'not detected',
                  'NOT_OBSERVED' if g is None else ('NEUTRAL' if g else 'SUPPORTS'),
                  None if (g is None or g) else 'weak'))
    reg = scr['film_regime']
    if reg is None:
        ev.append(_ev('film regime', 'no lubrication data', 'boundary (Lambda < 1)',
                      'NOT_OBSERVED', basis='input'))
    else:
        lam = reg['film_ratio']
        ev.append(_ev('film regime', f'Lambda = {lam:.3g} ({reg["regime"]})',
                      'boundary (Lambda < 1)', 'SUPPORTS' if lam < 1 else 'NEUTRAL',
                      'weak' if lam < 1 else None, 'model'))
    pred = {'contact_length_m': lc, 'reduction_fraction': red,
            'risk_level': scr['herringbone']['risk_level'],
            'contact_length_basis': scr['herringbone']['contact_length_basis']}
    return ev, pred


def _h_skid(ctx):
    o = ctx.obs
    scr = ctx.screens
    if scr['forward_slip'] is None:
        ev = [_ev('forward slip', f'NOT_ASSESSABLE: {ctx.bite_error}', '<= 0 or < 0.005',
                  'NEUTRAL', basis='model')]
    else:
        f = ctx.slip
        if f <= 0:
            v, w = 'SUPPORTS', 'strong'
        elif f < 0.005:
            v, w = 'SUPPORTS', 'moderate'
        elif f >= 0.02:
            v, w = 'CONTRADICTS', 'moderate'
        else:
            v, w = 'NEUTRAL', None
        ev = [_ev('forward slip', f'{f:.4f}', '<= 0 (strong), < 0.005 (moderate); >= 0.02 '
                  'contradicts', v, w, 'model')]
    reg = scr['film_regime']
    if reg is None:
        ev.append(_ev('film regime', 'no lubrication data', 'hydrodynamic (Lambda > 3)',
                      'NOT_OBSERVED', basis='input'))
    else:
        lam = reg['film_ratio']
        ev.append(_ev('film regime', f'Lambda = {lam:.3g} ({reg["regime"]})',
                      'hydrodynamic (Lambda > 3)', 'SUPPORTS' if lam > 3 else 'NEUTRAL',
                      'weak' if lam > 3 else None, 'model'))
    ori = o['orientation']
    if ori is None:
        ev.append(_ev('orientation', 'not observed', 'irregular', 'NOT_OBSERVED'))
    elif ori == 'irregular':
        ev.append(_ev('orientation', ori, 'irregular', 'SUPPORTS', 'weak'))
    elif ori == 'longitudinal':
        ev.append(_ev('orientation', ori, 'irregular', 'CONTRADICTS', 'strong'))
    else:
        ev.append(_ev('orientation', ori, 'irregular', 'NEUTRAL'))
    ev.append(_law_ev(ctx, {}, {'FIXED_FREQUENCY': 'weak', 'SPEED_INDEPENDENT_PITCH': 'weak'},
                      'no regular pitch law'))
    pred = {'forward_slip_fraction': ctx.slip if scr['forward_slip'] else None,
            'forward_slip_status': scr['forward_slip']['status'] if scr['forward_slip'] else None,
            'film_ratio': reg['film_ratio'] if reg else None}
    return ev, pred


_BUILDERS = {
    'third_octave_self_excited_chatter': _h_chatter,
    'fifth_octave_roll_stack_resonance': _h_fifth,
    'work_roll_borne_marks': lambda c: _h_roll(c, 'work'),
    'backup_roll_borne_marks': lambda c: _h_roll(c, 'backup'),
    'order_locked_drive_or_bearing_excitation': _h_order,
    'torsional_or_low_frequency_drive_vibration': _h_torsional,
    'coil_or_mandrel_locked_marks': _h_coil,
    'yield_point_bending_marks': _h_yield,
    'herringbone_lubricant_film_breakdown': _h_herringbone,
    'skidding_loss_of_forward_slip': _h_skid,
}


def score_evidence(evidence):
    """Tallies, score and provisional standing (before the leading rule) of one hypothesis."""
    t = {'supports': 0, 'contradicts': 0, 'neutral': 0, 'not_observed': 0,
         'support_points': 0, 'contradiction_points': 0, 'strong_contradictions': 0,
         'observation_supports': 0}
    for e in evidence:
        v = e['verdict']
        t[v.lower()] += 1
        if v == 'SUPPORTS':
            t['support_points'] += WEIGHT_POINTS_SUPPORT[e['weight']]
            if e.get('basis', 'observation') == 'observation':
                t['observation_supports'] += 1
        elif v == 'CONTRADICTS':
            t['contradiction_points'] += WEIGHT_POINTS_CONTRADICT[e['weight']]
            if e['weight'] == 'strong':
                t['strong_contradictions'] += 1
    score = t['support_points'] - t['contradiction_points']
    if t['strong_contradictions']:
        standing = 'CONTRADICTED'
    elif t['supports'] == 0 and t['contradicts'] == 0:
        standing = 'NOT_ASSESSABLE'
    elif score > 0:
        standing = 'CONSISTENT'
    else:
        standing = 'WEAKENED'
    return t, score, standing


def rank_hypotheses(hyps):
    """Apply standings (incl. CONSISTENT_LEADING) and rank in place; returns leading ids.

    Rule change against the written spec (reported in docs/band-diagnosis.md): a hypothesis
    can only be CONSISTENT_LEADING if at least one SUPPORTS item comes from a plant
    observation. Without it, model-only evidence (e.g. the speed margin, strong support on
    its own) made the chatter hypothesis 'leading' for a case with no observation at all.
    """
    alive = [h for h in hyps if h['standing'] != 'CONTRADICTED']
    top = max((h['score'] for h in alive), default=None)
    leading = []
    if top is not None and top >= 3:
        for h in alive:
            if h['score'] == top and h['tallies']['observation_supports'] > 0:
                h['standing'] = 'CONSISTENT_LEADING'
                leading.append(h['id'])
    hyps.sort(key=lambda h: (h['standing'] == 'CONTRADICTED', -h['score'], h['id']))
    for i, h in enumerate(hyps, 1):
        h['rank'] = i
    return [h['id'] for h in hyps if h['standing'] == 'CONSISTENT_LEADING']


def _hypotheses(ctx):
    out = []
    facts = bw.Facts(ctx.case, ctx.width, ctx.screens, ctx.process)
    for hid, title, mech, test, levers, family in HYPOTHESES:
        if family == bw.FAMILY:
            evidence, pred = bw.LENGTHWISE_BUILDERS[hid](facts)
        else:
            evidence, pred = _BUILDERS[hid](ctx)
        tallies, score, standing = score_evidence(evidence)
        h = {'id': hid, 'family': family, 'title': title, 'mechanism': mech,
             'model_prediction': pred,
             'evidence': evidence, 'tallies': tallies, 'score': score, 'standing': standing,
             'confirming_test': test, 'levers': list(levers)}
        if hid == 'third_octave_self_excited_chatter' and ctx.lever_directions:
            h['computed_lever_directions'] = [d['direction'] for d in ctx.lever_directions]
        out.append(h)
    leading = rank_hypotheses(out)
    return out, leading


def _next_measurements(hyps, obs, law, exit_thickness_m=None):
    lines = []
    for h in hyps[:3]:
        if h['confirming_test'] not in lines:
            lines.append(h['confirming_test'])
    longitudinal = obs['orientation'] == 'longitudinal'
    if law is None and not longitudinal:
        lines.append('Measure the mark pitch at two clearly different steady speeds (at least '
                     '20 % apart): this single measurement separates fixed-frequency vibration '
                     '(pitch scales with speed) from roll-, order- or coil-locked marks (pitch '
                     'constant).')
    if obs['gauge_variation_detected'] is None and not longitudinal:
        lines.append('Check the exit thickness gauge / X-ray trace for a periodic thickness '
                     'variation at the mark frequency (gauge chatter) or its absence '
                     '(fifth-octave / surface marks).')
    if obs['faces'] is None:
        lines.append('Record whether the marks appear on both strip faces or only one.')
    if (not longitudinal and (obs['disappears_after_work_roll_change'] is None
                              or obs['disappears_after_backup_roll_change'] is None)):
        lines.append('Note whether the marks disappear after a work-roll change and after a '
                     'backup-roll change (roll-change test).')
    if obs['orientation'] is None:
        lines.append('Record the mark orientation (transverse, diagonal, chevron, '
                     'longitudinal or irregular).')
    if obs['orientation'] in (None, 'longitudinal'):
        for line in bw.lengthwise_next_measurements(obs, exit_thickness_m):
            topic = bw.measurement_topic(line)
            if topic is None or not any(topic in x for x in lines):
                lines.append(line)
    out = []
    for line in lines:
        if line not in out:
            out.append(line)
    return out


def _strip_map(hyps, ctx):
    vib = ('third_octave_self_excited_chatter', 'fifth_octave_roll_stack_resonance',
           'work_roll_borne_marks', 'backup_roll_borne_marks',
           'order_locked_drive_or_bearing_excitation',
           'torsional_or_low_frequency_drive_vibration', 'coil_or_mandrel_locked_marks')
    lead = next((h for h in hyps if h['id'] in vib and h['standing'] != 'CONTRADICTED'
                 and h['score'] > 0), None)
    pitch, basis = None, None
    if lead is not None:
        pr = lead['model_prediction']
        if lead['id'] == 'third_octave_self_excited_chatter':
            pitch, basis = pr['predicted_pitch_at_operating_speed_m'], \
                'u_op / dominant frequency at the operating speed'
        elif lead['id'] == 'fifth_octave_roll_stack_resonance':
            pitch, basis = pr['pitch_at_operating_speed_m'], 'u_op / antisymmetric upper mode'
        elif lead['id'] in ('work_roll_borne_marks', 'backup_roll_borne_marks'):
            note = next((e['observed'] for e in lead['evidence']
                         if e['criterion'].startswith('pitch = pi*D') and
                         e['verdict'] == 'SUPPORTS'), None)
            n = 1
            if note and 'n = ' in note:
                n = int(note.split('n = ')[1].split(',')[0])
            pitch = pr['pitch_one_mark_m'] / n
            basis = f'pi*D*(1+f)/{n}'
        elif lead['id'] == 'order_locked_drive_or_bearing_excitation' and pr['best_match']:
            pitch, basis = pr['best_match']['strip_pitch_m'], pr['best_match']['id']
        elif lead['id'] == 'coil_or_mandrel_locked_marks' and pr['coil_pitches_m']:
            name = pr.get('matched_coil') or sorted(pr['coil_pitches_m'])[0]
            pitch, basis = pr['coil_pitches_m'][name], name
        elif (lead['id'] == 'torsional_or_low_frequency_drive_vibration'
              and pr.get('torsional_modes_hz')):
            # SPEC9 9.5: the computed torsional mode matching the observed frequencies best
            # (smallest worst relative mismatch), else the lowest mode; pitch = u_op / f
            modes = pr['torsional_modes_hz']
            if ctx.freqs:
                f = min(modes, key=lambda m: (max(abs(fo - m) / m for _, fo in ctx.freqs), m))
                how = 'best-matching computed torsional mode'
            else:
                f, how = min(modes), 'lowest computed torsional mode (no observed frequency)'
            pitch = ctx.u_op / f
            basis = f'u_op / {how} ({f:.4g} Hz)'
    observed = None
    if ctx.pitches:
        near = min(ctx.pitches, key=lambda p: (abs(p['exit_speed_m_s'] - ctx.u_op),
                                                p['exit_speed_m_s']))
        observed = near['pitch_m']
    longest = max([v for v in (pitch, observed) if v] or [0.0])
    length = 1.0 if longest <= 0.25 else float(math.ceil(4 * longest))
    return {'hypothesis_id': lead['id'] if lead else None, 'predicted_pitch_m': pitch,
            'predicted_pitch_basis': basis, 'observed_pitch_m': observed,
            'observed_at_exit_speed_m_s': (min(ctx.pitches, key=lambda p: (
                abs(p['exit_speed_m_s'] - ctx.u_op), p['exit_speed_m_s']))['exit_speed_m_s']
                if ctx.pitches else None),
            'strip_length_m': length}


# ============================================================================= main entry
def _process_inputs(eff, cache, flags, supplied=None):
    """Flow stress and friction from the process models (before the bite is derived).

    When ``use_computed_*`` is set the computed value replaces the supplied one in the
    effective case (pass and every schedule pass), and so in every downstream section.
    """
    out = {'flow_stress': None, 'friction': None, 'heating': None, 'friction_speed_curve': None}
    if eff['hardening'] is not None:
        try:
            fs = bp.flow_stress_section(eff, eff['hardening'])
            if eff['hardening']['use_computed_flow_stress']:
                bp.apply_flow_stress(eff, fs)
                flags.append('FLOW_STRESS_FROM_HARDENING_LAW')
            else:
                for r in fs['passes']:
                    r['used_mean_flow_stress_pa'] = r['supplied_mean_flow_stress_pa']
            out['flow_stress'] = fs
        except ValueError as exc:
            out['flow_stress'] = bp.failed('process.flow_stress', exc)
    if eff['tribology'] is not None:
        try:
            fr = bp.friction_section(eff, eff['tribology'], cache, supplied)
            if eff['tribology']['use_computed_friction']:
                bp.apply_friction(eff, fr)
                flags.append('FRICTION_FROM_PLACEHOLDER_CLOSURE')
            else:
                for r in [fr['operating']] + fr['schedule']:
                    r['used_friction_coefficient'] = r['supplied_friction_coefficient']
            out['friction'] = fr
        except ValueError as exc:
            out['friction'] = bp.failed('process.friction', exc)
    return out


FOIL_GAUGE_M = bw.FOIL_GAUGE_M
CLOSED_GAP_FLAG = 'CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED'
CLOSED_GAP_ONSET_RANGE_M = (50e-6, 200e-6)
CLOSED_GAP_SOURCES = (
    {'source': 'S8 Mysteel foil-rolling reference', 'tag': 'V',
     'onset_exit_gauge_m': [100e-6, 200e-6], 'text': 'rolls touch outside the strip at 0.1-0.2 mm'},
    {'source': 'S16 Publitec, The engineering design of rolling mill', 'tag': 'V',
     'onset_exit_gauge_m': [50e-6, 100e-6], 'text': 'below 100 um, about 80 um; force '
                                                     'ineffective for gauge below 50 um'},
    {'source': 'S17 Jiangsu Huafeng foil flatness note', 'tag': 'V',
     'onset_exit_gauge_m': [None, 50e-6], 'text': 'below 50 um'})
FOIL_LOAD_RANGE_N_M = (0.9e6, 2.3e6)    # [V S3, S4; kN/mm conversion D]
FOIL_SOURCES = (
    '[S3] alfoilworld.com battery-foil rolling procedure (passes, tensions, speeds, load).',
    '[S4] alfoilworld.com 1235D procedure (passes, roughness, oil, H18 UTS).',
    '[S5] SMM / Shenhuo battery-foil quality note (tension lines, ridge marks, offline sag).',
    '[S8] Mysteel foil-rolling reference (closed gap 0.1-0.2 mm, roll sizes).',
    '[S11] Sutcliffe & Montmitonnet 2001, Rev. Metall. (film ratio 1.76 -> 0.22).',
    '[S16] Publitec, The engineering design of rolling mill (closed gap ~80 um).',
    '[S17] Jiangsu Huafeng foil flatness note (closed gap < 50 um, online vs offline).',
    '[S25] foil defect compilation (hot spot, creasing, mill lines).',
    '[S26] EAFA, Surface Characteristics of Aluminium Foil (2020).',
    '[S27] CNFA foil rolling research note (wrinkle rule, tension lines).',
    '[S28] patent text on battery-foil tension lines.')
BITE_RELIABILITY = {
    'hitchcock': 'Slab model with circular (Hitchcock) flattening: not valid toward foil gauge '
                 '(flag THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN); force, slip and sensitivities '
                 'are indicative only and assume an open roll gap.',
    'experimental_mattress': 'EXPERIMENTAL elastic-foundation (mattress) foil model with a '
                             'foundation modulus from a memory formula and no elastic strip '
                             'zones (forward slip flagged implausible); not validated; it '
                             'models the contact on the strip only, not the load the rolls '
                             'carry outside the strip in closed gap.',
    'supplied': 'Supplied bite sensitivities, not verified by the tool.',
    None: 'No bite: chatter, levers, gauge control, forward slip and the derived shape chain '
          'are not assessable.'}


def _largest_model_band(width):
    """(largest linear-feedback |I| of a model band, where) from the width section, or None."""
    best = None
    if not isinstance(width, dict):
        return None
    st = (width.get('shape') or {}).get('steady')
    if isinstance(st, dict) and st.get('status') not in ('FAILED', 'NOT_ASSESSABLE'):
        v = st.get('linear_feedback_peak_i_units', st.get('feedback_peak_i_units'))
        if _is_num(v):
            best = (abs(v), 'steady stripes (linear exit-tension feedback)')
    te = width.get('thermal_events')
    for e in (te.get('events') or []) if isinstance(te, dict) else []:
        ps = e.get('peak_shape')
        v = ps.get('linear_feedback_peak_i_units') if isinstance(ps, dict) else None
        if _is_num(v) and (best is None or abs(v) > best[0]):
            best = (abs(v), f'event {e.get("label")} at its peak (linear exit-tension feedback)')
    return best


def _foil_regime(eff, bite, bite_error, result, flags):
    """SPEC9 9.2 foil-regime block for an exit gauge below 100 um (None otherwise).

    Closed-gap rolling (work rolls touching outside the strip) is reported for exit gauges
    between 50 and 200 um, sources disagree [V S8, S16, S17]; the tool has NO roll-kissing
    model. Wrinkle rule of thumb [V S27] evaluated as I = 1e5 * exit tension / E_strip [D].
    """
    p, m = eff['pass'], eff['material']
    h1 = p['exit_thickness_m']
    below = [{'label': 'case pass', 'exit_thickness_m': h1}] if h1 < BITE_FLOOR_M else []
    below += [{'label': r['label'], 'exit_thickness_m': r['exit_thickness_m']}
              for r in eff['schedule'] if r['exit_thickness_m'] < BITE_FLOOR_M
              and not bw.is_case_pass(eff, r)]
    if below:
        flags.append(BITE_FLOOR_FLAG)
    if h1 >= FOIL_GAUGE_M:
        return None
    flags.append(CLOSED_GAP_FLAG)
    lo, hi = CLOSED_GAP_ONSET_RANGE_M
    if h1 < lo:
        where, where_text = ('BELOW_EVERY_REPORTED_ONSET',
                             f'{h1 * 1e6:.3g} um is below every reported closed-gap onset '
                             '(50-200 um): the work rolls very likely touch outside the strip.')
    else:
        where, where_text = ('INSIDE_REPORTED_ONSET_RANGE',
                             f'{h1 * 1e6:.3g} um lies inside the reported closed-gap onset '
                             'range (50-200 um): the work rolls may touch outside the strip.')
    model = bw.bite_model_name(bite)
    fpw = bite.separating_force_n / p['width_m'] if bite is not None else None
    bite_block = {'model': model, 'reliability': BITE_RELIABILITY[model],
                  'flags': list(bite.flags) if bite is not None else [],
                  'fallback_reason': result.get('bite_fallback_reason'),
                  'bite_error': bite_error,
                  'separating_force_n': bite.separating_force_n if bite is not None else None,
                  'separating_force_per_width_n_m': fpw,
                  'forward_slip_fraction': (bite.forward_slip_fraction if bite is not None
                                            else None),
                  'reported_battery_foil_load_per_width_n_m': list(FOIL_LOAD_RANGE_N_M),
                  'reported_load_basis': '0.9-2.3 kN/mm of width for battery-foil passes '
                                         '[V S3, S4; conversion D]',
                  'force_per_width_within_reported_range': (
                      None if fpw is None else FOIL_LOAD_RANGE_N_M[0] <= fpw
                      <= FOIL_LOAD_RANGE_N_M[1])}
    passes = []
    sw = result.get('schedule_sweep') or {}
    for row in sw.get('rows') or []:
        passes.append({'label': row['label'], 'exit_thickness_m': row['exit_thickness_m'],
                       'bite_model': row.get('bite_model'),
                       'separating_force_per_width_n_m': row.get(
                           'separating_force_per_width_n_m'),
                       'rejected': row.get('rejected')})
    e_strip = m['youngs_modulus_pa']
    wrinkle = 1e5 * p['exit_tension_pa'] / e_strip
    band = _largest_model_band(result.get('width'))
    if band is None:
        comp = 'MODEL_BAND_NOT_ASSESSABLE'
        comp_text = ('No model band I-units available (no width model, or its shape chain is '
                     'not assessable).')
    elif band[0] >= wrinkle:
        comp = 'MODEL_BAND_AT_OR_ABOVE_WRINKLE_ONSET'
        comp_text = (f'The largest model band ({band[0]:.3g} I-units, {band[1]}) reaches the '
                     f'rule-of-thumb wrinkle onset of {wrinkle:.3g} I-units at this tension.')
    else:
        comp = 'MODEL_BAND_BELOW_WRINKLE_ONSET'
        comp_text = (f'The largest model band ({band[0]:.3g} I-units, {band[1]}) stays below '
                     f'the rule-of-thumb wrinkle onset of {wrinkle:.3g} I-units at this '
                     'tension.')
    temper = m['temper']
    return {
        'status': STATUS, 'exit_thickness_m': h1,
        'closed_gap_onset_range_m': [lo, hi],
        'closed_gap_onset_sources': [dict(x) for x in CLOSED_GAP_SOURCES],
        'closed_gap_note': 'Reported onsets of closed-gap rolling disagree (50-200 um exit '
                           'gauge); the tool has no roll-kissing model.',
        'case_position': where, 'case_position_text': where_text,
        'implications': [
            'In closed gap the load is no longer a gauge actuator: more screw-down only bends '
            'the rolls and changes flatness; the gauge is set by tension, speed and '
            'lubrication [V S8, S16, S17].',
            'The lever table (critical chatter speed against friction, reduction, tensions, '
            'span, damping) and the gauge-control section assume an OPEN roll gap; read them '
            'as open-gap reasoning, not as foil-mill predictions.',
            'The local transfer of a roll stripe to the strip is by roll / strip compliance, '
            'which the shape chain models, but without the load shunted outside the strip '
            'where the rolls touch; the transfer may be misestimated.',
            'Online (shapemeter) and offline flatness diverge at foil gauge: front tension '
            'masks the true shape [V S17, S8]; the in-mill and after-release states of the '
            'shape chain are the tool\'s proxy for that difference.',
            'Foil band defects with no physical model in the tool (tension lines, hot spots '
            'from roll wipers, creasing from ironing rolls) are screened by rules only.'],
        'bite': bite_block,
        'schedule_bites': passes,
        'below_bite_model_floor': {
            'floor_exit_thickness_m': BITE_FLOOR_M,
            'passes': below,
            'case_pass_below_floor': h1 < BITE_FLOOR_M,
            'text': (None if not below else
                     'No roll-bite result exists for '
                     + ', '.join(f'{x["label"]} ({x["exit_thickness_m"] * 1e6:.3g} um)'
                                 for x in below)
                     + ': the exit gauge is below the 20 um floor of both roll-bite models '
                       '(chatter.BitePass.validate). For such a pass the chatter, lever, '
                       'process-friction fixed point (and pass heating) and gauge-control '
                       'sections are not assessable, and its strip-shape chain runs only with '
                       'supplied width_model.shape_inputs (case pass). Collector foil of '
                       '16-18 um may in practice be rolled as a DOUBLED (two-sheet) pass, which '
                       'the tool does not model at all. Ask the plant: single-sheet or '
                       'doubled?')},
        'wrinkle_rule': {
            'wrinkle_onset_i_units': wrinkle,
            'formula': 'wrinkle_onset_i_units = 1e5 * exit_tension_pa / strip_youngs_modulus_pa '
                       '[D]: residual compression E*I*1e-5 exceeding the tension',
            'source_rule': 'At 20 MPa tension, flatness worse than 30 I-units necessarily '
                           'wrinkles [V S27] (3e-4 x 70 GPa = 21 MPa, the same condition [D]).',
            'exit_tension_pa': p['exit_tension_pa'], 'strip_youngs_modulus_pa': e_strip,
            'model_largest_band_i_units': band[0] if band else None,
            'model_largest_band_basis': band[1] if band else None,
            'comparison': comp, 'comparison_text': comp_text},
        'product_question': {
            'case_temper': temper,
            'text': 'Ask the plant which product this is: 25-60 um can be pouch-laminate '
                    'barrier foil (8021 / 8079, annealed O temper, 35-50 um), thick collector '
                    'foil (1235 / 1060 / 1070 / 1100-H18, 21-35 um), or an intermediate pass of '
                    'thinner collector foil; a final pass of 16-18 um (plant statement) points '
                    'to cathode current-collector foil in H18 with 25-60 um as intermediate '
                    'passes. Ask also whether the last pass is single-sheet or doubled (doubling '
                    'starts at about 18-32 um entry, or not at all for two-side-bright foil '
                    '[V S3]). O against H18 changes buckling and winding behaviour; this case '
                    f'uses temper {temper}.'},
        'flags': [CLOSED_GAP_FLAG] + ([BITE_FLOOR_FLAG] if below else []),
        'limitations': [
            'No roll-kissing (closed-gap) model; the bite models see only the strip contact.',
            'Foil facts are cited from a research pass (tags V / D / M), not plant-validated.'],
        'sources': list(FOIL_SOURCES)}


def _family_summary(obs, hyps, leading):
    ori = obs['orientation']
    fam = (bw.FAMILY if ori == 'longitudinal' else None if ori is None else 'transverse')
    lead_fam = HYPOTHESIS_FAMILIES[leading[0]] if leading else None
    if fam is None:
        text = ('The observed orientation is not recorded, so the observations do not yet '
                'point to the transverse (across the strip) or the lengthwise (along the '
                'strip) family.')
    else:
        text = (f'The observed orientation ({ori}) points to the {fam} family of band '
                'mechanisms' + (' (bands along the rolling direction at fixed width '
                                'positions).' if fam == bw.FAMILY else
                                ' (marks across the strip, repeating along its length).'))
    if lead_fam is not None:
        text += f' The leading hypothesis ({leading[0]}) belongs to the {lead_fam} family.'
    counts = {f: sum(1 for h in hyps if h['family'] == f and h['standing'] != 'CONTRADICTED')
              for f in ('transverse', bw.FAMILY)}
    return {'observed_family': fam, 'leading_family': lead_fam,
            'not_contradicted_per_family': counts, 'text': text}


def diagnose(case):
    """Run the band screening on a case dict (validated here). Returns a JSON-safe dict."""
    case = validate_case(case)
    flags = []
    if not case['synthetic']:
        flags.append('USER_SUPPLIED_INPUTS_NOT_VERIFIED')
    else:
        flags.append('SYNTHETIC_INPUTS')
    if case['model_options']['bite_model'] != 'hitchcock':
        flags.append(f'BITE_MODEL_{case["model_options"]["bite_model"].upper()}')
    eff = copy.deepcopy(case)          # effective inputs (computed values may replace supplied)
    cache = _BiteCache(eff)
    supplied = _supplied_bite(eff)
    process = _process_inputs(eff, cache, flags, supplied)
    p, obs = eff['pass'], eff['observation']
    beta = eff['model_options']['bite_damping_transit_fraction']
    u_op = p['exit_speed_m_s']
    h0, h1 = p['entry_thickness_m'], p['exit_thickness_m']
    stand, spans = _stand(eff), _spans(eff)
    bite, bite_error = _section_bite(eff, cache, flags, supplied)
    override = eff['model_options']['bite_response_override']
    trib = eff['tribology']

    result = {'status': STATUS, 'case_schema': case['case_schema'], 'case_name': case['name'],
              'synthetic': case['synthetic'], 'provenance': case['provenance'],
              'score_note': SCORE_NOTE, 'inputs': case}
    if eff['pass'] != case['pass'] or eff['schedule'] != case['schedule']:
        result['effective_inputs'] = {
            'pass': eff['pass'], 'schedule': eff['schedule'],
            'note': 'Computed flow stress and/or friction replaced the supplied values; every '
                    'downstream section uses these.'}
    result['bite'] = bite.to_dict() if bite is not None else None
    result['bite_error'] = bite_error
    if bite is not None and bp.is_mattress(bite):
        fb = [v for k, v in cache.fallbacks.items() if k[0] == _bite_pass(eff)]
        result['bite_fallback_reason'] = fb[0] if fb else None

    q_s = bite.strip_modulus_n_m if bite is not None else 0.0
    nf = natural_frequencies(stand, q_s)
    km = stand.mill_modulus_n_m
    modes = [{'name': 'antisymmetric_lower', 'frequency_hz': nf['antisymmetric_hz'][0],
              'family': 'antisymmetric'},
             {'name': 'antisymmetric_upper', 'frequency_hz': nf['antisymmetric_hz'][1],
              'family': 'fifth_octave_antisymmetric'}]
    if bite is not None:
        modes = [{'name': 'symmetric_lower_loaded', 'frequency_hz': nf['symmetric_hz'][0],
                  'family': 'third_octave_symmetric'},
                 {'name': 'symmetric_upper_loaded', 'frequency_hz': nf['symmetric_hz'][1],
                  'family': 'symmetric'}] + modes
    drive_modes = []
    if eff['drive'] is not None:
        _, drive_modes = bp.drive_modes(eff['drive'])
        modes = modes + drive_modes
    result['stand_modes'] = {
        'natural_frequencies': nf, 'mill_modulus_n_m': km,
        'strip_modulus_n_m': q_s if bite is not None else None,
        'strip_to_mill_modulus_ratio': (q_s / km) if bite is not None else None,
        'structural_modes_for_catalogue': modes,
        'note': None if bite is not None else
        'Symmetric (loaded) modes need the strip modulus: NOT_ASSESSABLE without a bite.'}

    ctx = _Ctx()
    ctx.case, ctx.obs, ctx.u_op, ctx.beta = eff, obs, u_op, beta
    ctx.bite_error = bite_error
    ctx.reduction = (h0 - h1) / h0
    ctx.dw, ctx.db = 2 * p['work_roll_radius_m'], eff['kinematics']['backup_roll_diameter_m']
    ctx.anti_upper_hz = nf['antisymmetric_hz'][1]
    ctx.drive_modes = drive_modes
    ctx.chatter_unreliable = False
    if bite is not None:
        ctx.slip = bite.forward_slip_fraction
    else:
        ctx.slip = 0.0
        flags.append('FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS')

    if bite is not None:
        chat = _section_chatter(stand, bite, spans, u_op, beta)
        limit = bp.span_wave_limit_hz(eff)
        onset = [f for f in (chat['with_bite_damping']['onset_frequency_hz'],
                             chat['without_bite_damping']['onset_frequency_hz'],
                             chat['stability']['dominant_frequency_hz']) if f]
        chat['span_wave_limit_hz'] = limit
        chat['span_wave_limit_basis'] = (f'c/(2L) of the shorter span, c = sqrt(E/rho), rho = '
                                         f'{bp.STRIP_DENSITY_KG_M3:g} kg/m3')
        chat['reliability'] = 'WITHIN_SPAN_WAVE_LIMIT'
        if onset and max(onset) > limit:
            chat['reliability'] = 'NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT'
            flags.append('CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT')
            ctx.chatter_unreliable = True
        result['chatter'] = chat
        ctx.chatter = chat
        ctx.ucrit = _crit_value(chat['critical_speed'])
        ctx.ucrit0 = _crit_value(chat['critical_speed'].get('without_bite_damping',
                                                            chat['critical_speed']))
        ctx.onset_hz = chat['with_bite_damping']['onset_frequency_hz']
        ctx.dominant_hz = chat['stability']['dominant_frequency_hz']
        ctx.speed_ratio = chat['with_bite_damping']['speed_ratio']
        unstable = not chat['stability']['stable']
        if unstable:
            flags.append('OPERATING_POINT_LINEARLY_UNSTABLE')
        if trib is not None and override is None:
            try:
                sc = bp.speed_consistent_critical_speed(eff, trib, cache, stand, spans, beta,
                                                        bite, SPEED_SCAN_M_S)
                sc['fixed_friction_critical_exit_speed_m_s'] = \
                    chat['with_bite_damping']['critical_exit_speed_m_s']
                sc['fixed_friction_critical_exit_speed_without_bite_damping_m_s'] = \
                    chat['without_bite_damping']['critical_exit_speed_m_s']
                sc['fixed_friction_coefficient'] = p['friction_coefficient']
                chat['speed_consistent'] = sc
            except ValueError as exc:
                chat['speed_consistent'] = bp.failed('chatter.speed_consistent', exc)
        else:
            chat['speed_consistent'] = bp.not_supplied(
                'needs tribology and a derived (not supplied) bite')
        result['time_simulation'] = (_section_time(stand, bite, spans, u_op, beta,
                                                   ctx.dominant_hz) if ctx.dominant_hz else None)
        result['forced_response'] = _section_forced(eff, stand, bite, spans, u_op, beta,
                                                    unstable)
        levers = _lever_rows(eff, cache, stand, spans, bite, beta, override)
        result['levers'] = levers
        ctx.lever_directions = levers['directions']
    else:
        na = {'status': 'NOT_ASSESSABLE', 'reason': bite_error}
        result['chatter'] = result['time_simulation'] = result['forced_response'] = na
        result['levers'] = na
        ctx.chatter = None
        ctx.ucrit = ctx.ucrit0 = ctx.onset_hz = ctx.dominant_hz = ctx.speed_ratio = None
        ctx.lever_directions = None

    sig = _section_signatures(eff, modes, ctx.slip, u_op, h0 / h1, obs, flags)
    result['signatures'] = sig
    ctx.signatures = sig
    ctx.catalogue = sig['catalogue']
    ctx.law = sig['law']
    ctx.slope = sig['pitch_speed_exponent']['slope'] if sig['pitch_speed_exponent'] else None
    ctx.pitches = obs['pitch_observations']
    ctx.freqs = [(f'u/p at {q["exit_speed_m_s"]:.4g} m/s', q['exit_speed_m_s'] / q['pitch_m'])
                 for q in ctx.pitches]
    if obs['measured_vibration_hz'] is not None:
        ctx.freqs.append(('measured vibration', obs['measured_vibration_hz']))

    contact = bite.contact_length_m if bite is not None else None
    ratio = bite.contact_radius_ratio if bite is not None else 1.0
    result['screens'] = _section_screens(eff, bite, ctx.slip, contact, ratio, flags)
    ctx.screens = result['screens']

    result['schedule_sweep'] = (_schedule_rows(eff, cache, stand, spans, beta, bite)
                                if eff['schedule'] else None)

    # ---- v2 process sections
    s_ = eff['stand']
    heat_row = None
    if bite is not None and (trib is not None or eff['width_model'] is not None):
        try:
            if trib is not None:
                process['heating'] = bp.heating_section(
                    eff, trib, cache, bite, eff['model_options']['cells'],
                    s_['roll_youngs_modulus_pa'], s_['roll_poisson_ratio'])
                heat_row = process['heating']['operating']
            else:
                heat_row = bp.heating_row(eff, p, bite, None, eff['model_options']['cells'],
                                          s_['roll_youngs_modulus_pa'], s_['roll_poisson_ratio'])
        except ValueError as exc:
            process['heating'] = bp.failed('process.heating', exc)
    if trib is not None and bite is not None:
        try:
            process['friction_speed_curve'] = bp.friction_curve(eff, trib, bite)
        except ValueError as exc:
            process['friction_speed_curve'] = bp.failed('process.friction_speed_curve', exc)
    if eff['tribology'] is None and eff['hardening'] is None:
        result['process'] = bp.not_supplied('tribology and hardening are null or absent')
    else:
        process.update(status=STATUS, not_supplied=False)
        result['process'] = process
    ctx.process = result['process']

    # perturbed bites of the sensitivities: same bite model as the operating bite (a supplied
    # bite keeps the selected model, Hitchcock for 'auto')
    sens_model = ('mattress' if (bite is not None and bp.is_mattress(bite))
                  or eff['model_options']['bite_model'] == 'mattress' else 'hitchcock')

    def sens_bite(bite_pass_):
        return cache.get(bite_pass_, model=sens_model)
    gc = eff['gauge_control']
    if gc is None:
        result['gauge_control'] = bp.not_supplied('gauge_control is null or absent')
    elif bite is None:
        result['gauge_control'] = {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                                   'reason': bite_error}
    else:
        try:
            result['gauge_control'] = bp.gauge_control_section(
                eff, gc, stand, bite, spans, beta, _roll_freqs(eff, u_op, ctx.slip), trib,
                sens_bite, SPEED_SCAN_M_S)
            flags.append('AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF')
        except ValueError as exc:
            result['gauge_control'] = bp.failed('gauge_control', exc)
    if eff['drive'] is None:
        result['drive'] = bp.not_supplied('drive is null or absent')
    else:
        try:
            result['drive'] = bp.drive_section(eff, eff['drive'], stand, bite, spans, beta, gc)
        except ValueError as exc:
            result['drive'] = bp.failed('drive', exc)
    iv = eff['incoming_variation']
    if iv is None:
        result['incoming_variation'] = bp.not_supplied('incoming_variation is null or absent')
    elif bite is None:
        result['incoming_variation'] = {'status': 'NOT_ASSESSABLE', 'not_supplied': False,
                                        'reason': bite_error}
    else:
        try:
            result['incoming_variation'] = bp.incoming_section(eff, iv, stand, bite, spans,
                                                               beta, gc, sens_bite)
        except ValueError as exc:
            result['incoming_variation'] = bp.failed('incoming_variation', exc)

    for key in ('gauge_control', 'incoming_variation'):
        sec = result.get(key)
        if isinstance(sec, dict) and bp.SENSITIVITY_MIX_FLAG in (sec.get('flags') or []):
            flags.append(bp.SENSITIVITY_MIX_FLAG)     # also on the rendered top-level list

    def get_bite(src):
        return cache.get(bp.bite_pass(eff, src))
    try:
        result['width'] = bw.width_section(eff, bite, get_bite, heat_row, trib, flags,
                                           bite_error)
    except ValueError as exc:
        result['width'] = bp.failed('width', exc)
    ctx.width = result['width']

    hyps, leading = _hypotheses(ctx)
    result['hypotheses'] = hyps
    result['leading_hypotheses'] = leading
    result['family_summary'] = _family_summary(obs, hyps, leading)
    result['foil_regime'] = _foil_regime(eff, bite, bite_error, result, flags)
    if result['foil_regime'] is not None:
        note = ('OPEN ROLL GAP ASSUMED: at this exit gauge the mill is in or near closed-gap '
                'rolling (not modelled), where load is no longer a gauge actuator.')
        for key in ('levers', 'gauge_control'):
            sec = result.get(key)
            if (isinstance(sec, dict) and not sec.get('not_supplied')
                    and sec.get('status') not in ('NOT_ASSESSABLE', 'FAILED')):
                sec['foil_regime_note'] = note
    result['recommended_next_measurements'] = _next_measurements(hyps, obs, ctx.law,
                                                                 h1)
    result['strip_map'] = _strip_map(hyps, ctx)
    result['bite_derivations'] = cache.derivations
    if bite is not None:
        flags.extend(bite.flags)
    result['flags'] = sorted(set(flags))
    result['limitations'] = list(LIMITATIONS)
    result['sources'] = list(SOURCES)
    result['source_disagreements'] = list(DISAGREEMENTS)
    json.dumps(result, allow_nan=False)
    return result


def result_json(result):
    """Deterministic JSON text (sorted keys, no NaN) for saving."""
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
