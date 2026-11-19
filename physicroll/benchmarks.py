"""Published benchmark cases beside the project's own numbers (SI, standard library only).

Status: ``SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION``. This module runs
the project's existing solvers (``foil_bite.solve_mattress_bite``,
``strip_shape.narrow_band_buckling_stress_pa``, ``chatter``) on published cases and prints the
result beside the published value. It changes no solver and feeds nothing into ``diagnose()``
or the HTML report. Sources: Appendix A of ``docs/simulation-coverage-gaps.md`` and the gap
reports in ``docs/research/band-screening-2026-11/``; read tags are copied with every number
(FT full text, EX extract, AB abstract, [D] derived, [run] model run here).

How a discrepancy is recorded (rule for this and all later phases)
-----------------------------------------------------------------
A benchmark keeps three things apart, never merged:

1. ``project_value``: computed now by calling the solver.
2. ``recorded_project_value``: a literal in this module with the date and commit it was taken
   at. A test asserts ``project_value == recorded_project_value`` to 1e-6 relative. This is
   SOFTWARE verification: it fails loudly when a later change moves the number; the fix is to
   re-record deliberately (new literal, new date, a line in section 13 of
   ``docs/band-diagnosis.md``), never to loosen the tolerance.
3. ``verdict`` against the published reference, one of ``VERDICTS``. ``agreement_band`` is
   ``(0.9, 1.1)`` on the ratio project / reference for every case [D, analyst choice]: a
   published model-to-model value read from a paper is not expected to be met closer than
   10 %. ``RECORDED_DISCREPANCY`` means the project value lies outside the band; a test that
   passes on it records the gap, it does not say the physics is right.

Formulas [BT-S1 FT, Fleck, Johnson, Mear & Zhang 1992, as restated in gap-bite-tribology.md
section 2.1]::

    W_bar = W * E_R* / (R * Y_s^2)                                  (dimensionless load)
    h_0c  = 12 * R * r^0.5 * mu^1.24 * (Y_s / E_R*)^0.76            (eq. 29)

W roll load per unit width [N/m], E_R* = E/(1 - nu^2) roll plane-strain modulus [Pa], R
undeformed roll radius [m], Y_s plane-strain yield stress of the strip [Pa], r reduction
fraction, mu Coulomb friction, h_0c entry gauge [m] below which a neutral (no-slip) zone
appears (regime I/II boundary of BT-S1).

Input conversions for the mattress solver [D]: it takes a uniaxial flow stress, so
``Y = Y_s*sqrt(3)/2``; it takes a Young's modulus and forms E/(1 - nu^2), so
``E = E_R*(1 - 0.3^2)`` with nu = 0.3 returns E_R* exactly (nu itself is not a BT-S1 input).

NOT done here: no figure is digitised; no reference value outside Appendix A of the study and
the reports' own run notes is added; the mattress model is not tuned towards any reference;
no chatter mill parameter is invented (``TM-LC7`` stays a reference record until its inputs
are recorded from the paper's tables).
"""
import argparse
import json
import math
import sys

from . import chatter
from .foil_bite import solve_mattress_bite
from .strip_shape import narrow_band_buckling_stress_pa

STATUS = 'SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION'
AGREEMENT_BAND = (0.9, 1.1)   # ratio project / reference [D, analyst choice, SPEC17]
VERDICTS = ('RECORDED_DISCREPANCY', 'WITHIN_AGREEMENT_BAND', 'INDICATIVE_ASSUMED_INPUTS',
            'REFERENCE_READ_BY_EYE', 'REFERENCE_ONLY_INPUTS_NOT_RECORDED', 'CONSISTENT_REGIME')
REFERENCE_KINDS = ('MODEL_OUTPUT', 'MEASUREMENT', 'PUBLISHED_FORMULA', 'FIGURE_READ_BY_EYE')
CASE_IDS = ('BT-V1', 'BT-V2-R89', 'BT-V2-R135', 'BT-V3-FIG1-140UM', 'BT-V3-EQ29',
            'SS-V2', 'SS-V3', 'TM-LC7')
RECORDED_ON = '2026-11-19, commit 8f10cbe'
REL_TOL = 1e-6                # software pin, relative

# ---------------------------------------------------------------- published inputs
# BT-S1 FT (Fleck et al. 1992, p.128, Fig. 9; Figs 1, 4, eq. 29): R 89 mm, Y_s 230 MPa
# (plane strain), E_R* 230 GPa, mu 0.03.
FLECK_RADIUS_M = 0.089
FLECK_YS_PA = 230e6
FLECK_ER_STAR_PA = 230e9
FLECK_MU = 0.03
ROLL_NU_FOR_SOLVER = 0.3      # only to pass E_R* through E/(1 - nu^2) [D]
SOLVER_WIDTH_M = 1.0          # W_bar uses load per width; width is not an input [D]
DEMO_ROLL_E_STAR_PA = 210e9 / 0.91   # battery-foil demo mill, E 210 GPa, nu 0.3 [D]

SOURCE_BT_S1 = ('Fleck, Johnson, Mear & Zhang (1992) Cold rolling of foil. Proc. IMechE B '
                '206:119-131')
SOURCE_SS_S19 = ('Dai, Zhang & Qin (2011) Engineering Mechanics 28(10):236-241 (Chinese); '
                 'Zhang et al. (2013) same journal')
SOURCE_TM_LC7 = 'Niroomand, Forouzan, Salimi (2015) ISIJ Int. 55(3):637'

# ---------------------------------------------------------------- recorded project values
# [run] at RECORDED_ON; re-record deliberately, never loosen the tolerance.
RECORDED = {
    'BT-V1': {'w_bar': 49.772441146213005, 'force_per_width_n_m': 1018841.8702629801,
              'forward_slip_fraction': 0.1697791266870894},
    'BT-V2-R89': {'w_bar': 41.06882418675794},
    'BT-V2-R135': {'w_bar': 51.05294649931081},
    'BT-V3-FIG1-140UM': {'w_bar': 45.968339998547265},
    'BT-V3-EQ29': {'h_0c_bt_v1_mill_m': 3.6238616820408836e-05,
                   'h_0c_fig1_case_m': 5.124914338906394e-05,
                   'h_0c_demo_mill_ys_175_mpa_m': 5.6346776676149275e-05,
                   'h_0c_demo_mill_ys_202_mpa_m': 6.285586351870883e-05},
    'SS-V2': {'critical_stress_pa': 8435559.317170393, 'critical_i_units': 4.016933008176378,
              'assumed_half_wave_m': 0.150},
    'SS-V3': {'assumed_half_wave_m': 0.105},
}

NOT_ENCODED = (
    {'id': 'BT-V4', 'reason': 'needs the friction closure of BT-G3; the figures must be '
                              'digitised'},
    {'id': 'BT-V9', 'reason': 'forward slip without load data; needs a friction value per row, '
                              'i.e. BT-G6'},
    {'id': 'SS-V1', 'reason': 'needs the buckling model of G4'},
    {'id': 'SS-V4', 'reason': 'needs the buckling model of G4'},
    {'id': 'SS-V5', 'reason': 'needs the roll profiles of the paper'},
    {'id': 'SS-V11', 'reason': 'already encoded: physicroll/literature.py, '
                               'tests/test_literature.py (cross-reference only)'},
) + tuple(
    {'id': i, 'reason': 'needs a model of a later phase or data not in the repository'}
    for i in ('BT-V5', 'BT-V6', 'BT-V7', 'BT-V8', 'BT-V10', 'BT-V11', 'BT-V12', 'BT-V13',
              'BT-V14', 'BT-V15', 'BT-V16', 'BT-V17', 'SS-V6', 'SS-V7', 'SS-V8', 'SS-V9',
              'SS-V10', 'SS-V12', 'SS-V13', 'SS-V14', 'SS-V15', 'SS-V16', 'SS-V17', 'SS-V18',
              'SS-V19'))

LIMITATIONS = [
    'Software comparison only: a published model-to-model value or one measurement read from a '
    'paper; nothing here validates a model against a mill.',
    'A test that passes on a RECORDED_DISCREPANCY case records the gap; it does not mean the '
    'physics is right.',
    'Assumed inputs (roll radius of BT-V2, steel modulus and Poisson ratio of SS-V2) are named '
    'in input_notes; such cases are indicative only.',
    'TM-LC7 (two-stand steel mill chatter onset) has no recorded mill parameters; only the '
    'harness chatter_onset_comparison and the published reference values are held. A tandem '
    'mill is outside the single-stand chatter model.',
]


def _finite_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or \
            not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')
    return float(value)


def fleck_dimensionless_load(force_per_width_n_m, roll_radius_m, plane_strain_yield_pa,
                             roll_plane_strain_modulus_pa) -> float:
    """``W_bar = W*E_R*/(R*Y_s^2)`` [BT-S1 FT as restated in gap-bite-tribology.md 2.1]."""
    w = _finite_positive('force_per_width_n_m', force_per_width_n_m)
    r = _finite_positive('roll_radius_m', roll_radius_m)
    ys = _finite_positive('plane_strain_yield_pa', plane_strain_yield_pa)
    er = _finite_positive('roll_plane_strain_modulus_pa', roll_plane_strain_modulus_pa)
    return w * er / (r * ys ** 2)


def fleck_regime_boundary_entry_gauge_m(roll_radius_m, reduction, friction_coefficient,
                                        plane_strain_yield_pa,
                                        roll_plane_strain_modulus_pa) -> float:
    """Eq. 29 of BT-S1 [FT]: ``h_0c = 12*R*r^0.5*mu^1.24*(Y_s/E_R*)^0.76``.

    Entry gauge [m] below which a neutral (no-slip) zone appears (regime I/II boundary).
    """
    r = _finite_positive('roll_radius_m', roll_radius_m)
    red = _finite_positive('reduction', reduction)
    if red >= 1:
        raise ValueError('reduction must be a fraction in (0, 1)')
    mu = _finite_positive('friction_coefficient', friction_coefficient)
    ys = _finite_positive('plane_strain_yield_pa', plane_strain_yield_pa)
    er = _finite_positive('roll_plane_strain_modulus_pa', roll_plane_strain_modulus_pa)
    return 12 * r * red ** 0.5 * mu ** 1.24 * (ys / er) ** 0.76


def _mattress(h0, h1, radius, ys, er, mu, tb=0.0, tf=0.0, cells=400):
    """Mattress bite on a BT-S1 case: returns (W_bar, solver result) [run]."""
    y = ys * math.sqrt(3) / 2                       # uniaxial flow stress [D]
    e = er * (1 - ROLL_NU_FOR_SOLVER ** 2)          # E such that E/(1 - nu^2) = E_R* [D]
    res = solve_mattress_bite(h0, h1, SOLVER_WIDTH_M, radius, y, mu, tb, tf,
                              roll_youngs_modulus_pa=e, roll_poisson_ratio=ROLL_NU_FOR_SOLVER,
                              cells=cells, contact_end_zones=True)
    return fleck_dimensionless_load(res['force_per_width_n_m'], radius, ys, er), res


def _ratio(project, reference):
    if project is None or reference is None:
        return None
    return project / reference


def _quantity(name, unit, project, recorded, reference, label):
    return {'name': name, 'unit': unit, 'project_value': project,
            'recorded_project_value': recorded,
            'recorded_on': RECORDED_ON if recorded is not None else None,
            'reference_value': reference, 'reference_label': label,
            'ratio_project_to_reference': _ratio(project, reference)}


def _band_verdict(ratio):
    lo, hi = AGREEMENT_BAND
    return 'WITHIN_AGREEMENT_BAND' if lo <= ratio <= hi else 'RECORDED_DISCREPANCY'


def _case(case_id, title, source, source_id, read_status, kind, inputs, input_notes,
          quantities, verdict, note, flags):
    return {'id': case_id, 'title': title, 'source': source, 'source_id': source_id,
            'read_status': read_status, 'reference_kind': kind, 'inputs': inputs,
            'input_notes': input_notes, 'quantities': quantities, 'verdict': verdict,
            'agreement_band': list(AGREEMENT_BAND), 'note': note, 'flags': flags}


def _fleck_inputs(h0, h1, radius, mu, ys=FLECK_YS_PA, er=FLECK_ER_STAR_PA, tb=0.0, tf=0.0):
    return {'entry_thickness_m': h0, 'exit_thickness_m': h1, 'work_roll_radius_m': radius,
            'plane_strain_yield_pa': ys, 'mean_flow_stress_pa': ys * math.sqrt(3) / 2,
            'roll_plane_strain_modulus_pa': er,
            'roll_youngs_modulus_pa': er * (1 - ROLL_NU_FOR_SOLVER ** 2),
            'roll_poisson_ratio': ROLL_NU_FOR_SOLVER, 'friction_coefficient': mu,
            'entry_tension_pa': tb, 'exit_tension_pa': tf, 'width_m': SOLVER_WIDTH_M}


_CONVERSION_NOTES = [
    'Uniaxial flow stress for the mattress solver Y = Y_s*sqrt(3)/2 [D].',
    'Roll Young modulus E = E_R*(1 - 0.3^2) with nu 0.3, so the solver\'s E/(1 - nu^2) is '
    'E_R* exactly [D]; nu is not a BT-S1 input.',
    'Width 1 m: W_bar uses the load per unit width; the width is not an input [D].',
]


def _bt_v1(cells=400):
    h0, h1 = 20e-6, 15e-6
    w_bar, res = _mattress(h0, h1, FLECK_RADIUS_M, FLECK_YS_PA, FLECK_ER_STAR_PA, FLECK_MU,
                           cells=cells)
    rec = RECORDED['BT-V1']
    q = [
        _quantity('w_bar', '1', w_bar, rec['w_bar'], 118.0,
                  'half-space solution of BT-S1 (MODEL_OUTPUT, FT, Fig. 9 and p.128)'),
        _quantity('w_bar', '1', w_bar, rec['w_bar'], 120.0,
                  'perturbation solution (MODEL_OUTPUT, FT)'),
        _quantity('w_bar', '1', w_bar, rec['w_bar'], 62.0,
                  'Fleck-Johnson mattress (MODEL_OUTPUT, FT)'),
        _quantity('force_per_width_n_m', 'N/m', res['force_per_width_n_m'],
                  rec['force_per_width_n_m'], 2.42e6,
                  '2.42 kN/mm from W_bar 118 [derived in the report]'),
        _quantity('forward_slip_fraction', '1', res['forward_slip_fraction'],
                  rec['forward_slip_fraction'], None, 'no published value'),
    ]
    ratio = q[0]['ratio_project_to_reference']
    notes = ['Every input is stated by the source (BT-S1 FT, p.128, Fig. 9): entry 20 um '
             '(b0 0.01 mm), r 25 %, R 89 mm, Y_s 230 MPa, E_R* 230 GPa, mu 0.03, no tensions.',
             'The source\'s strip modulus E_s* = 80 GPa is not an input of the rigid-plastic '
             'mattress (no elastic strip zones).'] + _CONVERSION_NOTES
    note = (f'The project\'s mattress bite is {ratio:.3f} of the half-space reference load '
            f'and {q[2]["ratio_project_to_reference"]:.3f} of the authors\' own mattress value '
            '[run]. Recorded discrepancy, not a validation; the mattress model is not tuned '
            'towards 118.')
    return _case('BT-V1', 'Foil bite, fully specified theory case (Fig. 9)', SOURCE_BT_S1,
                 'BT-S1', 'FT', 'MODEL_OUTPUT',
                 _fleck_inputs(h0, h1, FLECK_RADIUS_M, FLECK_MU), notes, q,
                 _band_verdict(ratio), note, ['MODEL_TO_MODEL_REFERENCE'] + res['flags'])


def _bt_v2(case_id, radius):
    h0 = 73e-6
    h1 = h0 * (1 - 0.57)
    mu = 0.026
    tb, tf = 0.107 * FLECK_YS_PA, 0.132 * FLECK_YS_PA
    w_bar, res = _mattress(h0, h1, radius, FLECK_YS_PA, FLECK_ER_STAR_PA, mu, tb, tf)
    q = [_quantity('w_bar', '1', w_bar, RECORDED[case_id]['w_bar'], 58.0,
                   'measured W_bar, AA1100 third foil pass (MEASUREMENT, FT, Fig. 8, p.127)')]
    notes = [f'Roll radius {radius * 1e3:g} mm ASSUMED: the source does not state the radius, '
             'the speed or the width.',
             'Friction 0.026 was inferred by the authors from this measured load, so the '
             'comparison is not independent of the reference.',
             'Entry 73 um, r 57 % (exit 31.39 um), Y_s 230 MPa, E_R* 230 GPa (as BT-S1), '
             'tensions 0.107 and 0.132 Y_s (FT).'] + _CONVERSION_NOTES
    note = (f'W_bar {w_bar:.2f} against measured 58 with an assumed radius; indicative only.')
    return _case(case_id, f'Foil mill point AA1100 73 -> 31 um, R {radius * 1e3:g} mm assumed',
                 SOURCE_BT_S1, 'BT-S1', 'FT', 'MEASUREMENT',
                 _fleck_inputs(h0, h1, radius, mu, tb=tb, tf=tf), notes, q,
                 'INDICATIVE_ASSUMED_INPUTS', note,
                 ['ASSUMED_ROLL_RADIUS', 'FRICTION_INFERRED_FROM_REFERENCE_LOAD'] + res['flags'])


def _bt_v3_fig1():
    h0, h1 = 140e-6, 70e-6
    w_bar, res = _mattress(h0, h1, FLECK_RADIUS_M, FLECK_YS_PA, FLECK_ER_STAR_PA, FLECK_MU)
    q = [_quantity('w_bar', '1', w_bar, RECORDED['BT-V3-FIG1-140UM']['w_bar'], 50.0,
                   '"about 50", read by eye by the bite report from the r = 50 % curve of '
                   'Fig. 4 (FIGURE_READ_BY_EYE)')]
    notes = ['Entry 140 um, r 50 %, R 89 mm, Y_s 230 MPa, E_R* 230 GPa, mu 0.03, no tensions '
             '(BT-S1 FT, Fig. 1, regime I).'] + _CONVERSION_NOTES
    note = (f'W_bar {w_bar:.2f} against a reference read by eye; the ratio is shown but no '
            'agreement is claimed.')
    return _case('BT-V3-FIG1-140UM', 'Regime I case of Fig. 1 (140 um, 50 %)', SOURCE_BT_S1,
                 'BT-S1', 'FT; reference read by eye from Fig. 4', 'FIGURE_READ_BY_EYE',
                 _fleck_inputs(h0, h1, FLECK_RADIUS_M, FLECK_MU), notes, q,
                 'REFERENCE_READ_BY_EYE', note, ['REFERENCE_READ_BY_EYE'] + res['flags'])


def _bt_v3_eq29():
    rec = RECORDED['BT-V3-EQ29']
    ys_demo_2 = 175e6 * 2 / math.sqrt(3)
    rows = (
        ('h_0c_bt_v1_mill_m', (FLECK_RADIUS_M, 0.25, FLECK_MU, FLECK_YS_PA, FLECK_ER_STAR_PA),
         '(a) BT-V1 mill, r 0.25; entry 20 um lies below'),
        ('h_0c_fig1_case_m', (FLECK_RADIUS_M, 0.5, FLECK_MU, FLECK_YS_PA, FLECK_ER_STAR_PA),
         '(b) Fig. 1 case, r 0.5; entry 140 um lies above'),
        ('h_0c_demo_mill_ys_175_mpa_m', (0.135, 0.4, 0.03, 175e6, DEMO_ROLL_E_STAR_PA),
         '(c) battery-foil demo mill, Y_s 175 MPa'),
        ('h_0c_demo_mill_ys_202_mpa_m', (0.135, 0.4, 0.03, ys_demo_2, DEMO_ROLL_E_STAR_PA),
         '(c) battery-foil demo mill, Y_s 175*2/sqrt(3) MPa'),
    )
    q = [_quantity(name, 'm', fleck_regime_boundary_entry_gauge_m(*args), rec[name], None,
                   label + ' (PUBLISHED_FORMULA eq. 29, FT; evaluated here)')
         for name, args, label in rows]
    _, res_a = _mattress(20e-6, 15e-6, FLECK_RADIUS_M, FLECK_YS_PA, FLECK_ER_STAR_PA, FLECK_MU)
    _, res_b = _mattress(140e-6, 70e-6, FLECK_RADIUS_M, FLECK_YS_PA, FLECK_ER_STAR_PA,
                         FLECK_MU)
    regime_a, regime_b = res_a['regime'], res_b['regime']
    below_a = 20e-6 < q[0]['project_value']
    above_b = 140e-6 > q[1]['project_value']
    consistent = below_a and regime_a == 'foil' and above_b and regime_b == 'conventional'
    flags = [f'PROJECT_REGIME_{regime_a.upper()}_AT_20_UM_ENTRY',
             f'PROJECT_REGIME_{regime_b.upper()}_AT_140_UM_ENTRY']
    if not consistent:
        flags.append('PROJECT_REGIME_DISAGREES_WITH_EQ29')
    note = (f'(a) h_0c {q[0]["project_value"] * 1e6:.2f} um: entry 20 um is below, project '
            f'regime {regime_a}; (b) h_0c {q[1]["project_value"] * 1e6:.2f} um: entry 140 um '
            f'is above, project regime {regime_b}. (c) {q[2]["project_value"] * 1e6:.2f} and '
            f'{q[3]["project_value"] * 1e6:.2f} um with the stated inputs; the bite report\'s '
            'own figure for (c) is "54-63 um" [derived], whose lower end is not reproduced '
            'here. Inputs were not adjusted to match.')
    inputs = {name: dict(zip(('roll_radius_m', 'reduction', 'friction_coefficient',
                              'plane_strain_yield_pa', 'roll_plane_strain_modulus_pa'), args))
              for name, args, _ in rows}
    notes = ['(a), (b): BT-S1 inputs (FT). (c): the battery-foil demo mill, R 0.135 m, r 0.4, '
             'mu 0.03, E_R* = 210e9/0.91 Pa, with Y_s 175 MPa and with 175*2/sqrt(3) MPa (the '
             'demo flow stress read as uniaxial) [D].',
             'Project regimes from the mattress bite on the BT-V1 and Fig. 1 cases [run].']
    return _case('BT-V3-EQ29', 'Regime boundary, eq. 29', SOURCE_BT_S1, 'BT-S1', 'FT',
                 'PUBLISHED_FORMULA', inputs, notes, q,
                 'CONSISTENT_REGIME' if consistent else 'RECORDED_DISCREPANCY', note, flags)


def _ss_v2():
    t, b, e, nu = 0.5e-3, 0.150, 210e9, 0.3
    stress = narrow_band_buckling_stress_pa(t, b, e, nu)
    i_units = 1e5 * stress / e
    rec = RECORDED['SS-V2']
    q = [_quantity('critical_stress_pa', 'Pa', stress, rec['critical_stress_pa'], None,
                   'no published stress; compared in I-units below'),
         _quantity('critical_i_units', 'I', i_units, rec['critical_i_units'], 5.3,
                   'computed critical, simply supported (SS-S19 FT, formulas garbled)'),
         _quantity('critical_i_units', 'I', i_units, rec['critical_i_units'], 6.38,
                   'computed critical, elastic restraint (SS-S19 FT)'),
         _quantity('critical_i_units', 'I', i_units, rec['critical_i_units'], 8.92,
                   'computed critical, clamped (SS-S19 FT); waves seen at 7.5-8, none below 6'),
         _quantity('half_wave_m', 'm', b, rec['assumed_half_wave_m'], 0.060,
                   'measured half wavelength 60 mm (SS-S19 FT); project mode: half-wave = '
                   'buckle width')]
    notes = ['Steel 0.5 x 1000 mm, buckle half-width 75 mm (buckle width b 150 mm), half '
             'wavelength 60 mm (SS-S19 FT).',
             'E 210 GPa and nu 0.3 ASSUMED (not stated in the record); uniform compression over '
             'b ASSUMED.',
             'Project: strip_shape.narrow_band_buckling_stress_pa (k = 4, simply supported), '
             'I-units = 1e5*sigma/E.']
    note = (f'{i_units:.3f} I-units against the published 5.3 (simply supported), ratio '
            f'{q[1]["ratio_project_to_reference"]:.4f}; the assumed half-wave is '
            f'{q[4]["ratio_project_to_reference"]:.2f} times the measured one.')
    return _case('SS-V2', 'Local interior buckle, steel (industrial)', SOURCE_SS_S19,
                 'SS-S19', 'FT (formulas garbled)', 'MODEL_OUTPUT',
                 {'thickness_m': t, 'band_width_m': b, 'youngs_modulus_pa': e,
                  'poisson_ratio': nu}, notes, q, 'INDICATIVE_ASSUMED_INPUTS', note,
                 ['ASSUMED_MODULUS_AND_POISSON_RATIO', 'STEEL_CASE'])


def _ss_v3():
    b = 0.105
    measured_half_wave = 0.075 / 2          # wavelength about 75 mm (FT); half of it [D]
    q = [_quantity('half_wave_m', 'm', b, RECORDED['SS-V3']['assumed_half_wave_m'],
                   measured_half_wave,
                   'half of the measured wavelength of about 75 mm (MEASUREMENT, SS-S19 FT)')]
    ratio = q[0]['ratio_project_to_reference']
    notes = ['Aluminium sheet 270 mm wide, 0.4 -> 0.3 mm (25 %), ground roll profile, buckle '
             'width 105 mm, wavelength about 75 mm (SS-S19 FT).',
             'Project mode: half-wave = buckle width (k = 4, simply supported band edges).']
    note = (f'Assumed half-wave / measured half-wave = {ratio:.2f}: recorded discrepancy of '
            'the mode shape only; no critical value is compared.')
    return _case('SS-V3', 'Local buckle, aluminium (laboratory rolling)', SOURCE_SS_S19,
                 'SS-S19', 'FT', 'MEASUREMENT', {'buckle_width_m': b,
                                                 'measured_wavelength_m': 0.075},
                 notes, q, _band_verdict(ratio), note, ['MODE_SHAPE_ONLY'])


def _tm_lc7():
    q = [_quantity('critical_exit_speed_m_s', 'm/s', None, None, 5.81,
                   'measured onset (MEASUREMENT, TM-LC7 EX, OD-22 EX)'),
         _quantity('onset_frequency_hz', 'Hz', None, None, 124.6,
                   'measured onset frequency (MEASUREMENT, TM-LC7 EX)'),
         _quantity('critical_exit_speed_m_s', 'm/s', None, None, 6.42,
                   'the paper\'s own model with span wave dynamics (MODEL_OUTPUT, EX)'),
         _quantity('critical_exit_speed_m_s', 'm/s', None, None, 6.57,
                   'the paper\'s own model without span wave dynamics (MODEL_OUTPUT, EX)'),
         _quantity('onset_frequency_hz', 'Hz', None, None, 129.0,
                   'the paper\'s own model (MODEL_OUTPUT, EX)')]
    notes = ['Two-stand steel mill, 2 mm entry, third pass (TM-LC7 EX).',
             'No mill parameter (roll masses, stiffnesses, damping, gauges, flow stress, '
             'friction, tensions, span lengths) is recorded in the repository; none is filled '
             'from memory or from another mill.',
             'A tandem mill is outside the single-stand model: single-stand models over-predict '
             'two-stand critical speeds by 42 % on average (TM-LC6 EX).']
    note = ('Reference record only. Run chatter_onset_comparison once the parameters are read '
            'from the paper\'s tables (each with table number and read tag; values the paper '
            'does not give marked ASSUMED).')
    return _case('TM-LC7', 'Chatter onset, two-stand steel mill', SOURCE_TM_LC7,
                 'TM-LC7 (= OD-22)', 'EX', 'MEASUREMENT', {}, notes, q,
                 'REFERENCE_ONLY_INPUTS_NOT_RECORDED', note,
                 ['INPUTS_NOT_RECORDED', 'TANDEM_MILL_OUTSIDE_SINGLE_STAND_MODEL'])


_CASES = {'BT-V1': _bt_v1, 'BT-V2-R89': lambda: _bt_v2('BT-V2-R89', 0.089),
          'BT-V2-R135': lambda: _bt_v2('BT-V2-R135', 0.135),
          'BT-V3-FIG1-140UM': _bt_v3_fig1, 'BT-V3-EQ29': _bt_v3_eq29, 'SS-V2': _ss_v2,
          'SS-V3': _ss_v3, 'TM-LC7': _tm_lc7}


def run_case(case_id: str) -> dict:
    """One benchmark case (JSON-safe dict). ValueError for an unknown id."""
    if case_id not in _CASES:
        raise ValueError(f'unknown benchmark case {case_id!r}; known: {", ".join(CASE_IDS)}')
    return _CASES[case_id]()


def run_all() -> dict:
    """Every encoded case, the not-encoded list and the limitations."""
    return {'status': STATUS, 'cases': [run_case(i) for i in CASE_IDS],
            'not_encoded': [dict(e) for e in NOT_ENCODED], 'limitations': list(LIMITATIONS)}


def table_rows(result=None) -> list:
    """Rows for the guide: id, quantity, project, reference, ratio, verdict."""
    result = run_all() if result is None else result
    rows = []
    for case in result['cases']:
        for q in case['quantities']:
            rows.append({'id': case['id'], 'quantity': q['name'], 'unit': q['unit'],
                         'project': q['project_value'], 'reference': q['reference_value'],
                         'reference_label': q['reference_label'],
                         'ratio': q['ratio_project_to_reference'], 'verdict': case['verdict']})
    return rows


def _stand(stand):
    return chatter.StandModel.from_modal_damping(
        stand['work_roll_mass_kg'], stand['backup_roll_mass_kg'],
        stand['work_backup_contact_stiffness_n_m'], stand['housing_stiffness_n_m'],
        stand['modal_damping_ratio'])


def _onset(c, measured_speed, measured_freq):
    speed, freq = c['critical_exit_speed_m_s'], c['onset_frequency_hz']
    return {'bite_damping_transit_fraction': c['bite_damping_transit_fraction'],
            'critical_status': c['status'], 'critical_exit_speed_m_s': speed,
            'onset_frequency_hz': freq,
            'speed_ratio_to_measured': _ratio(speed, measured_speed),
            'frequency_ratio_to_measured': _ratio(freq, measured_freq)}


def chatter_onset_comparison(stand: dict, spans: dict, bite_pass: dict, *,
                             measured_critical_speed_m_s, measured_frequency_hz,
                             bite_damping_transit_fraction=0.5, roll_youngs_modulus_pa=210e9,
                             roll_poisson_ratio=0.3, cells=256) -> dict:
    """Predicted chatter onset (with and without bite damping) beside a measured pair.

    ``stand``: the keys of a band case's ``stand`` section (masses, stiffnesses,
    ``modal_damping_ratio``); ``spans``: ``strip_youngs_modulus_pa``, ``entry_span_length_m``,
    ``exit_span_length_m``; ``bite_pass``: the eight ``chatter.BitePass`` fields. Uses
    ``StandModel.from_modal_damping``, ``derive_bite_response`` (slab + Hitchcock) and
    ``critical_speed`` over the default scan. A harness: it holds no mill of its own.
    """
    speed_m = _finite_positive('measured_critical_speed_m_s', measured_critical_speed_m_s)
    freq_m = _finite_positive('measured_frequency_hz', measured_frequency_hz)
    try:
        model = _stand(stand)
        sp = chatter.StripSpans(spans['strip_youngs_modulus_pa'], spans['entry_span_length_m'],
                                spans['exit_span_length_m'])
        bp = chatter.BitePass(*(bite_pass[k] for k in (
            'entry_thickness_m', 'exit_thickness_m', 'width_m', 'work_roll_radius_m',
            'mean_flow_stress_pa', 'friction_coefficient', 'entry_tension_pa',
            'exit_tension_pa')))
    except KeyError as exc:
        raise ValueError(f'missing key {exc} in stand, spans or bite_pass') from exc
    sp.validate()
    bite = chatter.derive_bite_response(bp, roll_youngs_modulus_pa=roll_youngs_modulus_pa,
                                        roll_poisson_ratio=roll_poisson_ratio, cells=cells)
    crit = chatter.critical_speed(model, bite, sp,
                                  bite_damping_transit_fraction=bite_damping_transit_fraction)
    zero = crit.get('without_bite_damping', crit)
    return {'status': STATUS,
            'measured_critical_speed_m_s': speed_m, 'measured_frequency_hz': freq_m,
            'with_bite_damping': _onset(crit, speed_m, freq_m),
            'without_bite_damping': _onset(zero, speed_m, freq_m),
            'bite': bite.to_dict(), 'flags': list(crit['flags']),
            'limitations': ['Linear single-stand negative-damping screen (chatter.py); bite '
                            'damping is the declared beta heuristic, shown with and without.',
                            'A tandem mill is outside the single-stand model.']}


def _fmt(value):
    if value is None:
        return '-'
    return f'{value:.6g}'


def main(argv=None):
    """``python -m physicroll.benchmarks [--json]``."""
    parser = argparse.ArgumentParser(
        description='Project values beside published benchmark values (software comparison, '
                    'not physical validation)')
    parser.add_argument('--json', action='store_true', help='print the full result as JSON')
    args = parser.parse_args(argv)
    result = run_all()
    if args.json:
        print(json.dumps(result, indent=1, allow_nan=False))
        return 0
    print(STATUS)
    print(f'agreement band on project / reference: {AGREEMENT_BAND[0]}-{AGREEMENT_BAND[1]}')
    print(f'{"id":18} {"quantity":28} {"project":>12} {"reference":>12} {"ratio":>8}  verdict')
    for r in table_rows(result):
        print(f'{r["id"]:18} {r["quantity"]:28} {_fmt(r["project"]):>12} '
              f'{_fmt(r["reference"]):>12} {_fmt(r["ratio"]):>8}  {r["verdict"]}')
    print('not encoded:')
    for e in result['not_encoded']:
        print(f'  {e["id"]}: {e["reason"]}')
    for line in result['limitations']:
        print('- ' + line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
