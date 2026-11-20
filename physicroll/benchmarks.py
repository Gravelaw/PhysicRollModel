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
   ``REFERENCE_NOT_GRID_INDEPENDENT`` [SPEC18 G'5] means the published value comes from a
   calculation whose result depends on a numerical detail the source does not state; the ratio
   is recorded and not judged.

A row (quantity) carries its own ``row_verdict``: by default the case verdict, or
``NO_REFERENCE_VALUE`` when it has no published value; a case may set a row's verdict
explicitly (one of ``VERDICTS``). A cross-check number that is not a published value goes into
the row label, never into ``reference_value``. Each pin carries the date and commit it was
taken at (``recorded_on``).

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

Steel chatter case ``TM-LC7`` [E9 FT = Niroomand, Forouzan & Salimi 2015, Tables 1, 3, 4, 5,
transcribed in docs/research/band-screening-2026-11/phase1-equations.md section 6.1]: the
paper's stand structure (two masses per half stack, its eqs (3.13), (3.14)) is the structure of
``chatter.py`` and maps exactly; its process model does not. The case is therefore a
comparison of the paper's structure with the project's own bite under the paper's flattening
assumption, with three stated substitutions (``TM_LC7_SUBSTITUTIONS``), not a re-run of the
paper's model. The equivalent Coulomb coefficient of substitution 2 is the fixed point
[D, SPEC18]::

    mu <- m*k*width*L/F          (same mean friction stress m*k as the friction factor m)

started at 0.025, tolerance 1e-9, at most 50 bite derivations (``equivalent_coulomb_friction``).
The paper's process equations (3.1)-(3.9) are NOT coded (transcribed from a page image at screen
resolution, one flagged as doubtful). The speed comparison is indicative only: it rests on one
of two readings of the reference speed and on the bite damping heuristic of ``chatter.py``.

NOT done here: no figure is digitised; no reference value outside Appendix A of the study, the
reports' own run notes and the research note phase1-equations.md is added; the mattress model is
not tuned towards any reference; no chatter mill parameter is invented.
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
            'REFERENCE_READ_BY_EYE', 'REFERENCE_ONLY_INPUTS_NOT_RECORDED', 'CONSISTENT_REGIME',
            'REFERENCE_NOT_GRID_INDEPENDENT')
# Row-level verdict of a quantity with no published value: project value recorded only.
NO_REFERENCE_VALUE = 'NO_REFERENCE_VALUE'
REFERENCE_KINDS = ('MODEL_OUTPUT', 'MEASUREMENT', 'PUBLISHED_FORMULA', 'FIGURE_READ_BY_EYE')
CASE_IDS = ('BT-V1', 'BT-V2-R89', 'BT-V2-R135', 'BT-V3-FIG1-140UM', 'BT-V3-EQ29',
            'SS-V2', 'SS-V3', 'TM-LC7', 'BT-V1-HS', 'BT-V2-R89-HS', 'BT-V2-R135-HS',
            'BT-V3-FIG1-140UM-HS', 'BT-V3-EQ29-HS', 'BT-X29-LOAD-EXPONENT-HS',
            'BT-G3-FILM-E6-T42', 'BT-V4-FILM', 'A9-PRESSURE-LAWS-KEROSINE',
            'BT-G3-CRUSHING-LAWS')
RECORDED_ON = '2026-11-19, commit 8f10cbe'
RECORDED_ON_SPEC18_P1 = '2026-11-20, on commit dc1145a (SPEC18 package 1)'
RECORDED_ON_SPEC18_P4 = '2026-11-20, on commit ec2d7b4 (SPEC18 package 4)'
RECORDED_ON_SPEC18_P5 = '2026-11-20, on commit 624f8e9 (SPEC18 package 5)'
RECORDED_ON_SPEC18_P6 = '2026-11-20, on commit f494de6 (SPEC18 package 6)'
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

# TM-LC7, stand 2 [E9 FT, Tables 1, 3, 4, 5]. The paper's "work roll spring constant" acts
# between work and backup roll in its eq. (3.13); its "backup roll spring constant" between
# backup roll and housing (3.14).
TM_LC7_SHEAR_YIELD_PA = 535.65e6          # k, stand 2 [E9 FT, Table 3]
TM_LC7_FRICTION_FACTOR = 0.054            # m on k, stand 2 [E9 FT, Table 3]
TM_LC7_STAND = {'work_roll_mass_kg': 14000.0, 'backup_roll_mass_kg': 38000.0,
                'work_backup_contact_stiffness_n_m': 7.01e10, 'housing_stiffness_n_m': 3.64e8,
                'work_backup_damping_n_s_m': 0.0, 'housing_damping_n_s_m': 9.54e5}
TM_LC7_SPANS = {'strip_youngs_modulus_pa': 200e9,          # Table 1
                'entry_span_length_m': 4.725, 'exit_span_length_m': 6.6}   # Table 4
TM_LC7_PASS = {'entry_thickness_m': 324e-6, 'exit_thickness_m': 216e-6, 'width_m': 0.732,
               'work_roll_radius_m': 0.245,
               # the project's K = 2Y/sqrt(3) equals 2k, so Y = sqrt(3)*k [D]
               'mean_flow_stress_pa': math.sqrt(3) * TM_LC7_SHEAR_YIELD_PA,
               'entry_tension_pa': 151e6, 'exit_tension_pa': 81e6}       # Table 4
TM_LC7_ROLL_YOUNGS_MODULUS_PA = 1e14      # substitution 1: upper limit of the derivation
TM_LC7_ROLL_POISSON_RATIO = 0.3
TM_LC7_SPEED_RANGE_M_S = (0.5, 60.0)
TM_LC7_CELLS = 256
TM_LC7_MEASURED_SPEED_M_S = 5.81          # Table 5, "of the first stand" in the text
TM_LC7_MEASURED_FREQUENCY_HZ = 124.6      # Table 5
# 5.81 m/s read as the strip speed between the stands: stand 2 exit speed by mass flow [D]
TM_LC7_SPEED_IF_INTERSTAND_M_S = TM_LC7_MEASURED_SPEED_M_S * 324e-6 / 216e-6
# Other Coulomb coefficients for the sensitivity to substitution 2 (0.054: the factor misread
# as a coefficient) [SPEC18 package 1]
TM_LC7_SENSITIVITY_MU = (0.02, 0.03, 0.054)
TM_LC7_SUBSTITUTIONS = (
    'Substitution 1: rigid rolls, roll Young modulus 1e14 Pa (the upper limit of the '
    'derivation). The paper has no roll flattening; the project\'s Hitchcock flattening '
    'rejects this pass with real rolls (210 GPa).',
    'Substitution 2: Coulomb friction with the same mean friction stress as the paper\'s '
    'friction FACTOR m = 0.054 on the shear yield stress k = 535.65 MPa: mu = m*k*width*L/F by '
    'fixed point [D, SPEC18].',
    'Substitution 3: stand 2 alone with its two spans (lumped, constant-speed far ends); the '
    'paper models two stands with stress waves between them.',
)

# ---------------------------------------------------------------- recorded project values
# [run] at RECORDED_ON; re-record deliberately, never loosen the tolerance.
RECORDED = {
    'BT-V1': {'w_bar': 49.772441146213005, 'force_per_width_n_m': 1018841.8702629801,
              'forward_slip_fraction': 0.1697791266870894,
              'contact_length_m': 0.0014744706490123272},   # at RECORDED_ON_SPEC18_P1
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
    # [run] at RECORDED_ON_SPEC18_P1
    'TM-LC7': {'equivalent_coulomb_friction': 0.026566358046062173,
               'separating_force_n': 4104373.065627256,
               'forward_slip_fraction': 0.02935885832187668,
               'contact_length_m': 0.005149830176213278,
               'strip_modulus_n_m': 20051543481.3828,
               'lower_loaded_symmetric_mode_hz': 121.87838720868523,
               'onset_frequency_hz': 122.3032841277549,
               'critical_exit_speed_m_s': 8.10139202893497,
               'critical_exit_speed_without_bite_damping_m_s': 0.5176731218858979,
               'onset_frequency_without_bite_damping_hz': 481.14904834135507},
    # [run] at RECORDED_ON_SPEC18_P4 (reduced half-space bite)
    'BT-V1-HS': {'w_bar_rigid_strip': 88.85871955010157,
                 'w_bar_strip_spring_80_gpa': 92.93604427034032,
                 'contact_length_rigid_strip_m': 0.0019613947598269856,
                 'contact_length_strip_spring_80_gpa_m': 0.0020384344556250494,
                 'peak_pressure_over_ys_rigid_strip': 7.521434258401501,
                 'peak_pressure_over_ys_strip_spring_80_gpa': 7.331458838064114,
                 'peak_position_rigid_strip_m': 0.00030539188604873164,
                 'peak_position_strip_spring_80_gpa_m': 0.0003494098912534436,
                 'contact_start_rigid_strip_m': -0.00111822787627059,
                 'contact_end_rigid_strip_m': 0.0008431668835563955,
                 'no_slip_zone_length_rigid_strip_m': 0.0010120889525228808,
                 'w_bar_printed_end_40_um': 78.01229524577438,
                 'w_bar_printed_end_21_um': 88.62210082746397,
                 'w_bar_printed_end_10_um': 102.61675982282605,
                 'w_bar_printed_end_5_um': 117.47031730128144,
                 'w_bar_printed_end_2.5_um': 134.1517025183796},
    'BT-V2-R89-HS': {'w_bar': 42.79958642116526},
    'BT-V2-R135-HS': {'w_bar': 67.12525266591923},
    'BT-V3-FIG1-140UM-HS': {'w_bar': 46.81955061964358},
    'BT-V3-EQ29-HS': {'entry_gauge_r50_without_no_slip_zone_m': 5.4e-05,
                      'entry_gauge_r50_with_no_slip_zone_m': 5.2e-05,
                      'entry_gauge_r25_without_no_slip_zone_m': 3.4e-05,
                      'entry_gauge_r25_with_no_slip_zone_m': 3.2e-05,
                      'entry_gauge_r10_without_no_slip_zone_m': 2.8e-05,
                      'entry_gauge_r10_with_no_slip_zone_m': 2.6e-05},
    'BT-X29-LOAD-EXPONENT-HS': {'load_exponent_in_friction': 2.460861178126231},
    # [run] at RECORDED_ON_SPEC18_P5 (oil and film)
    'BT-G3-FILM-E6-T42': {'film_thickness_30_m_s_m': 3.242311812633797e-07,
                          'film_thickness_10_m_s_m': 1.0807706042112656e-07,
                          'film_thickness_5_m_s_m': 5.403853021056328e-08,
                          'film_thickness_3_m_s_m': 3.242311812633797e-08,
                          'film_thickness_1_m_s_m': 1.0807706042112656e-08},
    'BT-V4-FILM': {'film_ratio_5_m_s': 0.20932790017290456,
                   'film_ratio_40_m_s': 1.6746232013832365},
    'A9-PRESSURE-LAWS-KEROSINE': {'viscosity_barus_100_mpa_pa_s': 0.003986366773221348,
                                  'viscosity_barus_625_mpa_pa_s': 0.9371845609595059,
                                  'viscosity_barus_945_mpa_pa_s': 26.1310680699495,
                                  'viscosity_barus_1510_mpa_pa_s': 9312.612600414626,
                                  'viscosity_roelands_100_mpa_pa_s': 0.003699132180218143,
                                  'viscosity_roelands_625_mpa_pa_s': 0.18000092137559526,
                                  'viscosity_roelands_945_mpa_pa_s': 1.2282814920250922,
                                  'viscosity_roelands_1510_mpa_pa_s': 24.36294894144888},
    # [run] at RECORDED_ON_SPEC18_P6 (crushing laws)
    'BT-G3-CRUSHING-LAWS': {'w_thesis_fit_eq_3_20_a050_p10': 1.62,
                            'w_thesis_fit_eq_3_20_a050_p06': 0.05,
                            'w_korzekwa_regression_a050_p10': 1.7608874999999997,
                            'w_korzekwa_regression_a050_p06': 0.5869268999999996,
                            'w_marsault_form_a050_p10': 1.62,
                            'w_marsault_form_a050_p06': 0.5832,
                            'w_wilson_sheu_fit_a050_p10': 5.471148310128523,
                            'w_wilson_sheu_fit_a050_p06': 1.1258163257085319},
}

NOT_ENCODED = (
    {'id': 'BT-V4', 'reason': 'film ratio encoded as BT-V4-FILM; load and slip curves need '
                              'digitising and a friction distribution through the bite'},
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
    'TM-LC7 (two-stand steel mill chatter onset) is run on stand 2 alone with three stated '
    'substitutions (rigid rolls, an equivalent Coulomb friction, one stand); it compares the '
    'paper\'s stand structure with the project\'s own bite and is not a re-run of the paper\'s '
    'model. Its speed comparison is indicative only. A tandem mill is outside the single-stand '
    'chatter model.',
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


def _quantity(name, unit, project, recorded, reference, label, row_verdict=None,
              recorded_on=None):
    """One row. ``row_verdict`` (one of ``VERDICTS`` or ``NO_REFERENCE_VALUE``) overrides the
    case verdict for this row; ``recorded_on`` overrides ``RECORDED_ON`` for a later pin."""
    if row_verdict is not None and row_verdict not in VERDICTS + (NO_REFERENCE_VALUE,):
        raise ValueError(f'unknown row verdict {row_verdict!r}')
    if row_verdict is not None and (row_verdict == NO_REFERENCE_VALUE) != (reference is None):
        raise ValueError('NO_REFERENCE_VALUE exactly when the reference value is None')
    q = {'name': name, 'unit': unit, 'project_value': project,
         'recorded_project_value': recorded,
         'recorded_on': (recorded_on or RECORDED_ON) if recorded is not None else None,
         'reference_value': reference, 'reference_label': label,
         'ratio_project_to_reference': _ratio(project, reference)}
    if row_verdict is not None:
        q['row_verdict'] = row_verdict
    return q


def _band_verdict(ratio):
    lo, hi = AGREEMENT_BAND
    return 'WITHIN_AGREEMENT_BAND' if lo <= ratio <= hi else 'RECORDED_DISCREPANCY'


def _case(case_id, title, source, source_id, read_status, kind, inputs, input_notes,
          quantities, verdict, note, flags):
    for q in quantities:   # row verdict: set by the case, else the case verdict or NO_REF...
        if 'row_verdict' not in q:
            q['row_verdict'] = NO_REFERENCE_VALUE if q['reference_value'] is None else verdict
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
_ES_NOTE = ('E_s* = 80 GPa enters only the longitudinal no-slip equations of the source and '
            'none of its loads [E1 FT].')
_BT_V2_UNSTATED_NOTE = ('Roll radius, roll modulus, speed and width are not stated in the '
                        'source [E1 FT, confirmed by a second full reading].')

# Contact length of the Fig. 9 case in Sutcliffe's thesis, which used the Mear and Zhang
# pressure distribution: b/R = 0.0241 with R 88.9 mm [E6 FT, thesis p.54; MODEL_OUTPUT].
BT_V1_CONTACT_LENGTH_E6_M = 2.14e-3
BT_V1_REFERENCE_CAVEAT = (
    'The caption value 118 is not a grid-independent number: the printed end conditions '
    '(pressure step at exit, zero slope there) give 78 to 134 for end lengths of 40 to 2.5 um in '
    'two independent re-implementations [computed, re-implementation of E1; computed, SPEC18 '
    'prototype]; 118 corresponds to about 5 um, the element size stated in the paper (about '
    '21 um) to 88-89. See case BT-V1-HS.')
BT_V1_FIG9_LANDMARKS = (
    'Fig. 9 landmarks of the full numerical solution, read by eye by the research note (no '
    'rows here; compared by the half-space case): entry -1.18 mm, p/Y_s about 6.1 at the centre '
    'line, peak about 7.7 at +0.41 mm, exit +0.95 mm; reading error about 0.03 mm and 0.2 '
    '[E1 FT figure, read by eye].')


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
    contact_ratio = _ratio(res['contact_length_m'], BT_V1_CONTACT_LENGTH_E6_M)
    q.append(_quantity(
        'contact_length_m', 'm', res['contact_length_m'], rec['contact_length_m'],
        BT_V1_CONTACT_LENGTH_E6_M,
        'contact length of the same published solution, b/R = 0.0241 with R 88.9 mm '
        '(MODEL_OUTPUT, E6 FT, thesis p.54)', row_verdict=_band_verdict(contact_ratio),
        recorded_on=RECORDED_ON_SPEC18_P1))
    ratio = q[0]['ratio_project_to_reference']
    notes = ['Every input is stated by the source (BT-S1 FT, p.128, Fig. 9): entry 20 um '
             '(b0 0.01 mm), r 25 %, R 89 mm, Y_s 230 MPa, E_R* 230 GPa, mu 0.03, no tensions.',
             'The source\'s strip modulus E_s* = 80 GPa is not an input of the rigid-plastic '
             'mattress (no elastic strip zones).', _ES_NOTE] + _CONVERSION_NOTES
    note = (f'The project\'s mattress bite is {ratio:.3f} of the half-space reference load '
            f'and {q[2]["ratio_project_to_reference"]:.3f} of the authors\' own mattress value '
            '[run]. Recorded discrepancy, not a validation; the mattress model is not tuned '
            'towards 118. ' + BT_V1_REFERENCE_CAVEAT + ' The mattress ratio stays a '
            'RECORDED_DISCREPANCY: against every member of that family (78 to 134) the mattress '
            f'value {w_bar:.1f} is low by a factor {78 / w_bar:.1f} to {134 / w_bar:.1f} [D]. '
            f'Contact length {res["contact_length_m"] * 1e3:.3f} mm against 2.14 mm of the same '
            f'published solution [E6 FT, thesis p.54]: ratio {contact_ratio:.3f}. '
            + BT_V1_FIG9_LANDMARKS)
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
             'tensions 0.107 and 0.132 Y_s (FT).', _ES_NOTE, _BT_V2_UNSTATED_NOTE] + \
        _CONVERSION_NOTES
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


def _tm_lc7_compare(mu):
    """chatter_onset_comparison of stand 2 with substitutions 1 and 3 at Coulomb ``mu``."""
    return chatter_onset_comparison(
        TM_LC7_STAND, TM_LC7_SPANS, dict(TM_LC7_PASS, friction_coefficient=mu),
        measured_critical_speed_m_s=TM_LC7_MEASURED_SPEED_M_S,
        measured_frequency_hz=TM_LC7_MEASURED_FREQUENCY_HZ, bite_damping_transit_fraction=0.5,
        roll_youngs_modulus_pa=TM_LC7_ROLL_YOUNGS_MODULUS_PA,
        roll_poisson_ratio=TM_LC7_ROLL_POISSON_RATIO, cells=TM_LC7_CELLS,
        speed_range_m_s=TM_LC7_SPEED_RANGE_M_S)


def _strip_modulus_for_lower_symmetric_mode(stand, frequency_hz):
    """Q_s that puts the lower loaded symmetric mode of ``stand`` at ``frequency_hz`` [D]:
    the determinant of ``chatter.natural_frequencies`` solved for K11 = K_wb + 2*Q_s."""
    w2 = (2 * math.pi * frequency_hz) ** 2
    kwb, kh = stand.work_backup_contact_stiffness_n_m, stand.housing_stiffness_n_m
    k11 = w2 * stand.work_roll_mass_kg + kwb ** 2 / (kwb + kh - w2 * stand.backup_roll_mass_kg)
    return (k11 - kwb) / 2


def _fmt_onset(onset):
    speed, freq = onset['critical_exit_speed_m_s'], onset['onset_frequency_hz']
    if speed is None or freq is None:
        return onset['critical_status']
    return f'{speed:.3f} m/s, {freq:.2f} Hz'


def _tm_lc7():
    eq = equivalent_coulomb_friction(
        TM_LC7_PASS, TM_LC7_FRICTION_FACTOR, TM_LC7_SHEAR_YIELD_PA,
        roll_youngs_modulus_pa=TM_LC7_ROLL_YOUNGS_MODULUS_PA,
        roll_poisson_ratio=TM_LC7_ROLL_POISSON_RATIO, cells=TM_LC7_CELLS)
    mu = eq['friction_coefficient']
    run = _tm_lc7_compare(mu)
    bite, w, z = run['bite'], run['with_bite_damping'], run['without_bite_damping']
    stand = _stand(TM_LC7_STAND)
    lower_mode = chatter.natural_frequencies(stand, bite['strip_modulus_n_m'])['symmetric_hz'][0]
    q_for_measured = _strip_modulus_for_lower_symmetric_mode(stand,
                                                             TM_LC7_MEASURED_FREQUENCY_HZ)
    rec = RECORDED['TM-LC7']
    subs = '; project value with the three substitutions of input_notes'
    nr = NO_REFERENCE_VALUE
    q = [
        _quantity('equivalent_coulomb_friction', '1', mu, rec['equivalent_coulomb_friction'],
                  None, 'substitution 2: same mean friction stress as m = 0.054 on k = 535.65 '
                  'MPa [E9 FT, Table 3; D, SPEC18]; no published value' + subs,
                  row_verdict=nr,
                  recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('separating_force_n', 'N', bite['separating_force_n'],
                  rec['separating_force_n'], None, 'not given in the paper' + subs,
                  row_verdict=nr, recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('forward_slip_fraction', '1', bite['forward_slip_fraction'],
                  rec['forward_slip_fraction'], None, 'not given in the paper' + subs,
                  row_verdict=nr, recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('contact_length_m', 'm', bite['contact_length_m'], rec['contact_length_m'],
                  None, 'not given in the paper' + subs, row_verdict=nr,
                  recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('strip_modulus_n_m', 'N/m', bite['strip_modulus_n_m'],
                  rec['strip_modulus_n_m'], None,
                  f'no published value; {q_for_measured:.5g} N/m would put the lower loaded '
                  f'symmetric mode at 124.6 Hz [D] (project / that value '
                  f'{bite["strip_modulus_n_m"] / q_for_measured:.3f})' + subs,
                  row_verdict=nr, recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('lower_loaded_symmetric_mode_hz', 'Hz', lower_mode,
                  rec['lower_loaded_symmetric_mode_hz'], TM_LC7_MEASURED_FREQUENCY_HZ,
                  'measured onset frequency (MEASUREMENT, E9 FT, Table 5)' + subs,
                  row_verdict=_band_verdict(lower_mode / TM_LC7_MEASURED_FREQUENCY_HZ),
                  recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('onset_frequency_hz', 'Hz', w['onset_frequency_hz'],
                  rec['onset_frequency_hz'], TM_LC7_MEASURED_FREQUENCY_HZ,
                  'measured onset frequency (MEASUREMENT, E9 FT, Table 5; the paper\'s model '
                  '129 Hz with stress waves, 132 Hz without); bite damping 0.5' + subs,
                  row_verdict=_band_verdict(w['onset_frequency_hz'] /
                                            TM_LC7_MEASURED_FREQUENCY_HZ),
                  recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('critical_exit_speed_m_s', 'm/s', w['critical_exit_speed_m_s'],
                  rec['critical_exit_speed_m_s'], TM_LC7_SPEED_IF_INTERSTAND_M_S,
                  'reading (a): 5.81 m/s [E9 FT, Table 5] is the strip speed between the '
                  'stands, so stand 2 exits at 5.81*324/216 m/s [D]; bite damping 0.5; '
                  'indicative only' + subs, row_verdict='INDICATIVE_ASSUMED_INPUTS',
                  recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('critical_exit_speed_m_s', 'm/s', w['critical_exit_speed_m_s'],
                  rec['critical_exit_speed_m_s'], TM_LC7_MEASURED_SPEED_M_S,
                  'reading (b): 5.81 m/s (MEASUREMENT, E9 FT, Table 5; the paper\'s model 6.42 '
                  'm/s with stress waves, 6.57 m/s without) is stand 2\'s exit speed; bite '
                  'damping 0.5; indicative only' + subs,
                  row_verdict='INDICATIVE_ASSUMED_INPUTS', recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('critical_exit_speed_without_bite_damping_m_s', 'm/s',
                  z['critical_exit_speed_m_s'],
                  rec['critical_exit_speed_without_bite_damping_m_s'], None,
                  'no bite damping (heuristic off); onset in the upper mode' + subs,
                  row_verdict=nr, recorded_on=RECORDED_ON_SPEC18_P1),
        _quantity('onset_frequency_without_bite_damping_hz', 'Hz', z['onset_frequency_hz'],
                  rec['onset_frequency_without_bite_damping_hz'], None,
                  'no bite damping (heuristic off); the upper mode' + subs, row_verdict=nr,
                  recorded_on=RECORDED_ON_SPEC18_P1),
    ]
    sens = [(m_c, _tm_lc7_compare(m_c)['with_bite_damping']) for m_c in TM_LC7_SENSITIVITY_MU]
    sens_text = '; '.join(f'{m_c:g} -> {_fmt_onset(o)}' for m_c, o in sens)
    notes = list(TM_LC7_SUBSTITUTIONS) + [
        f'Substitution 1 gives R\'/R = {bite["contact_radius_ratio"]:.3f} [run].',
        f'Substitution 2: mu = {mu:.6f} at a mean pressure of {eq["mean_pressure_pa"] / 1e6:.1f} '
        f'MPa after {eq["derivations"]} bite derivations [run].',
        'Reference speed, two readings [E9 FT, Table 5 and text]: the paper gives 5.81 m/s as '
        'the recorded critical speed "of the first stand". (a) If 5.81 m/s is the strip speed '
        f'between the stands, stand 2 exits at 5.81*324/216 = '
        f'{TM_LC7_SPEED_IF_INTERSTAND_M_S:.3f} m/s [D]; (b) if it is stand 2\'s exit speed, '
        'the reference is 5.81 m/s. Both are recorded; neither is asserted.',
        'Inputs [E9 FT, Tables 1, 3, 4, 5], stand 2: roll masses 14000 / 38000 kg; "work roll '
        'spring constant" 7.01e10 N/m between work and backup roll; "backup roll spring '
        'constant" 3.64e8 N/m to the housing; damping 0 / 9.54e5 N s/m; 324 -> 216 um; width '
        '0.732 m; work roll radius 0.245 m; k 535.65 MPa, so the mean flow stress sqrt(3)*k '
        '(the project\'s K = 2Y/sqrt(3) = 2k) [D]; tensions 151 / 81 MPa; strip E 200 GPa; '
        'spans 4.725 / 6.6 m.',
        'Bite damping comes from the paper\'s dynamic process model there and from the declared '
        'transit-fraction heuristic of chatter.py here: 0.5 and 0 are both reported.',
        'The paper\'s process equations (3.1)-(3.9) are not coded. The reduced half-space bite '
        'cannot stand in for them either (with rigid rolls and the shear cap as a friction '
        'factor the forward slip falls to 0.004 and the friction march fails '
        '[computed, SPEC18 prototype]).',
    ]
    if z['critical_exit_speed_m_s'] is not None and z['onset_frequency_hz'] is not None:
        no_damping_text = (f'the model is unstable from about {z["critical_exit_speed_m_s"]:.2f} '
                           f'm/s in its upper mode ({z["onset_frequency_hz"]:.0f} Hz)')
    else:
        no_damping_text = f'the scan gives {z["critical_status"]}'
    speed_a = w['critical_exit_speed_m_s'] / TM_LC7_SPEED_IF_INTERSTAND_M_S
    speed_b = w['critical_exit_speed_m_s'] / TM_LC7_MEASURED_SPEED_M_S
    note = ('Comparison of the paper\'s stand structure with the project\'s own bite under the '
            'paper\'s no-flattening assumption, with three substitutions; not a re-run of the '
            'paper\'s model and not a validation of the chatter screen. The frequency agrees '
            'because it is set by the stand and the strip stiffness. The speed depends on the '
            'friction substitution (5.7 to 9.3 m/s for 0.02 to 0.03) and on a damping '
            f'heuristic; without the heuristic {no_damping_text}. Project, bite damping 0.5: '
            f'{_fmt_onset(w)}; without bite damping: '
            f'{_fmt_onset(z)}; speed ratio {speed_a:.3f} on reading (a) and {speed_b:.3f} '
            'on reading (b), '
            'indicative only. Sensitivity to substitution 2 (other Coulomb coefficients, bite '
            f'damping 0.5) [run]: {sens_text} (0.054 is the friction factor misread as a '
            'coefficient). Unloaded modes of this stand: '
            + ', '.join(f'{f:.4f}' for f in chatter.natural_frequencies(stand)['symmetric_hz'])
            + ' Hz [run].')
    inputs = {'stand': dict(TM_LC7_STAND), 'spans': dict(TM_LC7_SPANS),
              'bite_pass': dict(TM_LC7_PASS, friction_coefficient=mu),
              'friction_factor': TM_LC7_FRICTION_FACTOR,
              'shear_yield_pa': TM_LC7_SHEAR_YIELD_PA,
              'roll_youngs_modulus_pa': TM_LC7_ROLL_YOUNGS_MODULUS_PA,
              'roll_poisson_ratio': TM_LC7_ROLL_POISSON_RATIO,
              'speed_range_m_s': list(TM_LC7_SPEED_RANGE_M_S), 'cells': TM_LC7_CELLS,
              'bite_damping_transit_fraction': [0.5, 0.0]}
    return _case('TM-LC7', 'Chatter onset, two-stand steel mill, stand 2 with three '
                 'substitutions', SOURCE_TM_LC7, 'TM-LC7 (= OD-22; E9)',
                 'FT (E9: sections 3-5 and all tables; section 2 skimmed)', 'MEASUREMENT',
                 inputs, notes, q, 'INDICATIVE_ASSUMED_INPUTS', note,
                 ['SUBSTITUTED_RIGID_ROLLS', 'SUBSTITUTED_EQUIVALENT_COULOMB_FRICTION',
                  'SUBSTITUTED_SINGLE_STAND', 'REFERENCE_SPEED_TWO_READINGS',
                  'TANDEM_MILL_OUTSIDE_SINGLE_STAND_MODEL'] + run['flags'])


# ------------------------------------------------- reduced half-space bite (SPEC18 package 4)
# E_s* of the strip thickness spring: 80 GPa is the source's strip modulus of Fig. 9 [E1 FT],
# used here for the planner's addition (the spring); 1e13 Pa = rigid strip, the source's
# assumption. The printed end conditions are the benchmark mode of halfspace_bite (package 3).
HS_STRIP_MODULUS_PA = 80e9
HS_RIGID_STRIP_PA = 1e13
# cross-check of the printed-end family by the research note's own numpy re-implementation
# [computed, re-implementation of E1]: end length um -> W_bar (not a published value)
PRINTED_END_CROSS_CHECK = {21: 88.0, 10: 101.9, 5: 116.6, 2.5: 133.2}
BT_V1_HS_NOTE = (
    'The printed model closes the bite with a pressure step; its load is not defined without an '
    'end length (78 at 40 um, 88.6 at 21 um, 102.6 at 10 um, 117.5 at 5 um, 134.2 at 2.5 um, '
    'computed twice independently). The caption value 118 corresponds to about 5 um; the paper '
    'states an element size of about 21 um. This solver keeps the exit contact zone instead; '
    'its value for a strip rigid in thickness, 88.86, equals the printed model at 21 um. A ratio '
    'to 118 is recorded and not judged. The published contact length (2.14 mm) corresponds to '
    'about 103 in the same family.')
_HS_NOTES = ['Reduced half-space bite (physicroll.halfspace_bite): zone structure selected by '
             'the rules of SPEC18 package 3; the strip thickness spring (planner\'s addition, '
             'not in E1) at the stated E_s*; E_s* = 1e13 Pa is a strip rigid in thickness.',
             _ES_NOTE] + _CONVERSION_NOTES


def _half_space(h0, h1, radius, mu, es, ys=FLECK_YS_PA, er=FLECK_ER_STAR_PA, tb=0.0, tf=0.0):
    """Reduced half-space bite on a BT-S1 case: (W_bar, result) [run]."""
    from .halfspace_bite import solve_half_space_bite
    y = ys * math.sqrt(3) / 2
    e = er * (1 - ROLL_NU_FOR_SOLVER ** 2)
    res = solve_half_space_bite(h0, h1, SOLVER_WIDTH_M, radius, y, mu, tb, tf,
                                roll_youngs_modulus_pa=e, roll_poisson_ratio=ROLL_NU_FOR_SOLVER,
                                strip_plane_strain_modulus_pa=es)
    return fleck_dimensionless_load(res['force_per_width_n_m'], radius, ys, er), res


def _hq(name, unit, project, key, reference, label, verdict, rec_case):
    return _quantity(name, unit, project, RECORDED[rec_case][key], reference, label,
                     row_verdict=verdict, recorded_on=RECORDED_ON_SPEC18_P4)


def _bt_v1_hs():
    from .halfspace_bite import _printed_end_condition_family
    h0, h1 = 20e-6, 15e-6
    w_r, rigid = _half_space(h0, h1, FLECK_RADIUS_M, FLECK_MU, HS_RIGID_STRIP_PA)
    w_s, spring = _half_space(h0, h1, FLECK_RADIUS_M, FLECK_MU, HS_STRIP_MODULUS_PA)
    ys = FLECK_YS_PA
    ng, eye, band = 'REFERENCE_NOT_GRID_INDEPENDENT', 'REFERENCE_READ_BY_EYE', _band_verdict
    cl = BT_V1_CONTACT_LENGTH_E6_M
    q = [
        _hq('w_bar_rigid_strip', '1', w_r, 'w_bar_rigid_strip', 118.0,
            'caption value of Fig. 9 (MODEL_OUTPUT, E1 FT); not grid-independent', ng, 'BT-V1-HS'),
        _hq('w_bar_strip_spring_80_gpa', '1', w_s, 'w_bar_strip_spring_80_gpa', 118.0,
            'caption value of Fig. 9 (MODEL_OUTPUT, E1 FT); not grid-independent', ng, 'BT-V1-HS'),
        _hq('contact_length_rigid_strip_m', 'm', rigid['contact_length_m'],
            'contact_length_rigid_strip_m', cl, 'contact length of the same published solution '
            '(MODEL_OUTPUT, E6 FT, thesis p.54)', band(rigid['contact_length_m'] / cl),
            'BT-V1-HS'),
        _hq('contact_length_strip_spring_80_gpa_m', 'm', spring['contact_length_m'],
            'contact_length_strip_spring_80_gpa_m', cl, 'contact length of the same published '
            'solution (MODEL_OUTPUT, E6 FT, thesis p.54)', band(spring['contact_length_m'] / cl),
            'BT-V1-HS'),
        _hq('peak_pressure_over_ys_rigid_strip', '1', rigid['max_pressure_pa'] / ys,
            'peak_pressure_over_ys_rigid_strip', 7.7, 'about 7.7, Fig. 9 read by eye by the '
            'research note (E1 FT figure)', eye, 'BT-V1-HS'),
        _hq('peak_pressure_over_ys_strip_spring_80_gpa', '1', spring['max_pressure_pa'] / ys,
            'peak_pressure_over_ys_strip_spring_80_gpa', 7.7, 'about 7.7, Fig. 9 read by eye',
            eye, 'BT-V1-HS'),
        _hq('peak_position_rigid_strip_m', 'm', rigid['peak_pressure_position_m'],
            'peak_position_rigid_strip_m', 0.41e-3, 'about +0.41 mm, Fig. 9 read by eye', eye,
            'BT-V1-HS'),
        _hq('peak_position_strip_spring_80_gpa_m', 'm', spring['peak_pressure_position_m'],
            'peak_position_strip_spring_80_gpa_m', 0.41e-3, 'about +0.41 mm, Fig. 9 read by '
            'eye', eye, 'BT-V1-HS'),
        _hq('contact_start_rigid_strip_m', 'm', rigid['contact_start_m'],
            'contact_start_rigid_strip_m', -1.18e-3, 'entry about -1.18 mm, Fig. 9 read by eye',
            eye, 'BT-V1-HS'),
        _hq('contact_end_rigid_strip_m', 'm', rigid['contact_end_m'], 'contact_end_rigid_strip_m',
            0.95e-3, 'exit about +0.95 mm, Fig. 9 read by eye', eye, 'BT-V1-HS'),
        _hq('no_slip_zone_length_rigid_strip_m', 'm', rigid['flat_zone_length_m'],
            'no_slip_zone_length_rigid_strip_m', None, 'regime: the figure shows regime II/III '
            '(a no-slip zone); the project finds a foil structure with a no-slip zone '
            f'({rigid["zone_structure"]}): consistent, no number to compare', NO_REFERENCE_VALUE,
            'BT-V1-HS'),
    ]
    rows = _printed_end_condition_family(h0, h1, SOLVER_WIDTH_M, FLECK_RADIUS_M,
                                         ys * math.sqrt(3) / 2, FLECK_MU, 0.0, 0.0,
                                         roll_youngs_modulus_pa=FLECK_ER_STAR_PA *
                                         (1 - ROLL_NU_FOR_SOLVER ** 2),
                                         roll_poisson_ratio=ROLL_NU_FOR_SOLVER,
                                         end_lengths_m=(40e-6, 21e-6, 10e-6, 5e-6, 2.5e-6))
    family = {}
    for row in rows:
        um = round(row['end_length_m'] * 1e6, 1)
        um = int(um) if um == int(um) else um
        w = fleck_dimensionless_load(row['force_per_width_n_m'], FLECK_RADIUS_M, ys,
                                     FLECK_ER_STAR_PA)
        family[um] = w
        cross = PRINTED_END_CROSS_CHECK.get(um)
        label = (f'printed end conditions, end length {um} um (benchmark mode); no published '
                 'value' + (f'; cross-check {cross} [computed, re-implementation of E1], ratio '
                            f'{w / cross:.3f}' if cross else ''))
        q.append(_hq(f'w_bar_printed_end_{um}_um', '1', w, f'w_bar_printed_end_{um}_um', None,
                     label, NO_REFERENCE_VALUE, 'BT-V1-HS'))
    notes = ['Every input as BT-V1 (E1 FT, Fig. 9).'] + _HS_NOTES + [
        'Printed end conditions: one pressure element of the stated length outside each end, '
        'strip rigid, structure A B F (benchmark mode, never used by the engine).']
    flags = ['MODEL_TO_MODEL_REFERENCE', 'REFERENCE_NOT_GRID_INDEPENDENT',
             'CONSISTENT_REGIME_WITH_FIGURE' if rigid['regime'] == 'foil'
             else 'REGIME_DIFFERS_FROM_FIGURE']
    note = BT_V1_HS_NOTE + (f' [run] W_bar {w_r:.3f} (rigid strip), {w_s:.3f} (80 GPa spring); '
                            f'printed-end family {family[40]:.2f} to {family[2.5]:.2f}.')
    case = _case('BT-V1-HS', 'Foil bite, published case in the reduced half-space bite',
                 SOURCE_BT_S1, 'BT-S1 (= E1)', 'FT', 'MODEL_OUTPUT',
                 _fleck_inputs(h0, h1, FLECK_RADIUS_M, FLECK_MU), notes, q, ng, note, flags)
    return case


def _bt_v2_hs(case_id, radius):
    h0 = 73e-6
    h1 = h0 * (1 - 0.57)
    mu = 0.026
    tb, tf = 0.107 * FLECK_YS_PA, 0.132 * FLECK_YS_PA
    w, res = _half_space(h0, h1, radius, mu, HS_STRIP_MODULUS_PA, tb=tb, tf=tf)
    q = [_hq('w_bar', '1', w, 'w_bar', 58.0, 'measured W_bar, AA1100 third foil pass '
             '(MEASUREMENT, E1 FT, Fig. 8)', 'INDICATIVE_ASSUMED_INPUTS', case_id)]
    notes = [f'Roll radius {radius * 1e3:g} mm ASSUMED: ' + _BT_V2_UNSTATED_NOTE,
             'Friction 0.026 was inferred by the authors from this measured load.'] + _HS_NOTES
    return _case(case_id, f'Foil mill point, reduced half-space bite, R {radius * 1e3:g} mm '
                 'assumed', SOURCE_BT_S1, 'BT-S1 (= E1)', 'FT', 'MEASUREMENT',
                 _fleck_inputs(h0, h1, radius, mu, tb=tb, tf=tf), notes, q,
                 'INDICATIVE_ASSUMED_INPUTS', f'W_bar {w:.2f} against measured 58 with an '
                 f'assumed radius ({res["zone_structure"]}); indicative only.',
                 ['ASSUMED_ROLL_RADIUS', 'FRICTION_INFERRED_FROM_REFERENCE_LOAD'])


def _bt_v3_fig1_hs():
    w, res = _half_space(140e-6, 70e-6, FLECK_RADIUS_M, FLECK_MU, HS_STRIP_MODULUS_PA)
    q = [_hq('w_bar', '1', w, 'w_bar', 50.0, '"about 50", read by eye by the bite report from '
             'the r = 50 % curve of Fig. 4 (FIGURE_READ_BY_EYE)', 'REFERENCE_READ_BY_EYE',
             'BT-V3-FIG1-140UM-HS')]
    return _case('BT-V3-FIG1-140UM-HS', 'Regime I case of Fig. 1, reduced half-space bite',
                 SOURCE_BT_S1, 'BT-S1 (= E1)', 'FT; reference read by eye from Fig. 4',
                 'FIGURE_READ_BY_EYE', _fleck_inputs(140e-6, 70e-6, FLECK_RADIUS_M, FLECK_MU),
                 _HS_NOTES, q, 'REFERENCE_READ_BY_EYE',
                 f'W_bar {w:.2f} ({res["zone_structure"]}) against a reference read by eye.',
                 ['REFERENCE_READ_BY_EYE'])


def _bt_v3_eq29_hs():
    """The regime boundary of the reduced half-space bite against eq. 29 of E1."""
    q, flags, ok = [], [], True
    for red, thick, thin in ((0.5, 54, 52), (0.25, 34, 32), (0.10, 28, 26)):
        h0c = fleck_regime_boundary_entry_gauge_m(FLECK_RADIUS_M, red, FLECK_MU, FLECK_YS_PA,
                                                  FLECK_ER_STAR_PA)
        verdict = 'CONSISTENT_REGIME' if red >= 0.25 else 'RECORDED_DISCREPANCY'
        for gauge, want in ((thick, 'conventional'), (thin, 'foil')):
            _, res = _half_space(gauge * 1e-6, gauge * 1e-6 * (1 - red), FLECK_RADIUS_M,
                                 FLECK_MU, HS_STRIP_MODULUS_PA)
            if res['regime'] != want:
                ok = False
                flags.append(f'REGIME_AT_{gauge}_UM_R_{red:g}_IS_{res["regime"].upper()}')
            name = (f'entry_gauge_r{int(red * 100):02d}_'
                    + ('without' if want == 'conventional' else 'with') + '_no_slip_zone_m')
            q.append(_hq(name, 'm', gauge * 1e-6, name, h0c,
                         f'eq. 29 of E1 (PUBLISHED_FORMULA, FT): h_0c {h0c * 1e6:.1f} um for r '
                         f'{red:g}; project structure {res["zone_structure"]} at {gauge} um',
                         verdict, 'BT-V3-EQ29-HS'))
    if not ok:
        flags.append('PROJECT_REGIME_DISAGREES_WITH_THE_PLANNER_BRACKETS')
    note = ('No-slip zone absent at 54 / 34 / 28 um and present at 52 / 32 / 26 um for r 0.5 / '
            '0.25 / 0.10 [run]; eq. 29 gives 51.2 / 36.2 / 22.9 um. For r 0.5 and 0.25 the '
            'bracket lies 2-5 % above and 6-12 % below eq. 29 (consistent); for r 0.10 it lies '
            '14-22 % above (recorded discrepancy).')
    return _case('BT-V3-EQ29-HS', 'Regime boundary of the reduced half-space bite, eq. 29',
                 SOURCE_BT_S1, 'BT-S1 (= E1)', 'FT', 'PUBLISHED_FORMULA',
                 {'friction_coefficient': FLECK_MU, 'work_roll_radius_m': FLECK_RADIUS_M,
                  'plane_strain_yield_pa': FLECK_YS_PA,
                  'roll_plane_strain_modulus_pa': FLECK_ER_STAR_PA,
                  'strip_plane_strain_modulus_pa': HS_STRIP_MODULUS_PA}, _HS_NOTES, q,
                 'CONSISTENT_REGIME', note, flags)


def _bt_x29_load_exponent_hs():
    from .halfspace_bite import derive_bite_response_half_space
    y = FLECK_YS_PA * math.sqrt(3) / 2
    _, state = derive_bite_response_half_space(
        chatter.BitePass(20e-6, 15e-6, SOLVER_WIDTH_M, FLECK_RADIUS_M, y, FLECK_MU, 0.0, 0.0),
        roll_youngs_modulus_pa=FLECK_ER_STAR_PA * (1 - ROLL_NU_FOR_SOLVER ** 2),
        roll_poisson_ratio=ROLL_NU_FOR_SOLVER, strip_plane_strain_modulus_pa=HS_STRIP_MODULUS_PA,
        with_state=True)
    e = state['extra']['load_exponent_in_friction']
    eye = 'REFERENCE_READ_BY_EYE'
    label = ('of the range 2 to 2.6 the bite report derives from the master curve (slope read '
             'by eye) [BT-S1 FT as restated in gap-bite-tribology.md]')
    q = [_hq('load_exponent_in_friction', '1', e, 'load_exponent_in_friction', 2.0,
             'lower end ' + label, eye, 'BT-X29-LOAD-EXPONENT-HS'),
         _hq('load_exponent_in_friction', '1', e, 'load_exponent_in_friction', 2.6,
             'upper end ' + label, eye, 'BT-X29-LOAD-EXPONENT-HS')]
    inside = 2.0 <= e <= 2.6
    return _case('BT-X29-LOAD-EXPONENT-HS', 'Load exponent in friction, published case',
                 SOURCE_BT_S1, 'BT-S1 (= E1)', 'FT; slope read by eye', 'FIGURE_READ_BY_EYE',
                 _fleck_inputs(20e-6, 15e-6, FLECK_RADIUS_M, FLECK_MU), _HS_NOTES, q, eye,
                 f'd ln W / d ln mu = {e:.3f} [run] ' + ('inside' if inside else 'outside') +
                 ' the range 2 to 2.6 read from the master curve.',
                 ['INSIDE_READ_RANGE' if inside else 'OUTSIDE_READ_RANGE'])


# ------------------------------------------------------- oil and film (SPEC18 package 5)
E6_FILM_SPEEDS_M_S = (30.0, 10.0, 5.0, 3.0, 1.0)
E6_FILM_UM = (0.323, 0.108, 0.054, 0.032, 0.011)     # h_w, MODEL_OUTPUT [E6 FT, Table 4.2]
E6_INLET_SLOPE = 0.0058                              # published inlet slope [E6 FT]
E6_STRIP_SPEED_FRACTION = 0.88                       # ASSUMED (note: 0.93-0.96 of u_r mean)


def _pq(name, unit, project, rec_key, reference, label, verdict, case_id):
    return _quantity(name, unit, project, RECORDED[case_id][rec_key], reference, label,
                     row_verdict=verdict, recorded_on=RECORDED_ON_SPEC18_P5)


def _bt_g3_film_e6():
    from . import bite_tribology as bt
    lub = bt.Lubricant(1.0e-3, 333.15, 0.015, 1.0e-8, name='thesis foil-case oil')
    radius = 5e-6 / E6_INLET_SLOPE ** 2
    q = []
    for u, ref in zip(E6_FILM_SPEEDS_M_S, E6_FILM_UM):
        res = bt.inlet_film_thickness(
            lub, roll_surface_speed_m_s=u, strip_entry_speed_m_s=E6_STRIP_SPEED_FRACTION * u,
            entry_thickness_m=20e-6, exit_thickness_m=15e-6, contact_radius_m=radius,
            plane_strain_yield_pa=230e6, back_tension_pa=0.0, inlet_temperature_k=333.15)
        key = f'film_thickness_{u:g}_m_s_m'
        q.append(_pq(key, 'm', res['film_thickness_m'], key, ref * 1e-6,
                     f'h_w at {u:g} m/s (MODEL_OUTPUT, E6 FT, Table 4.2)',
                     'INDICATIVE_ASSUMED_INPUTS', 'BT-G3-FILM-E6-T42'))
    notes = ['Oil 1.0e-3 Pa s at 60 C, 1.0e-8 /Pa, plane-strain yield 230 MPa, no tension; '
             'contact radius 5e-6/0.0058^2 = 0.148633 m so that the inlet angle is the published '
             'slope 0.0058 (E6 FT).',
             'Strip entry speed 0.88 of the roll speed ASSUMED: the research note reproduces the '
             'table with a mean speed of 0.93 to 0.96 of the roll speed.',
             'Project: bite_tribology.inlet_film_thickness without the thermal factor.']
    return _case('BT-G3-FILM-E6-T42', 'Inlet film of the thesis foil case (Table 4.2)',
                 'Sutcliffe (1989) PhD thesis, Cambridge (E6)', 'E6', 'FT', 'MODEL_OUTPUT', {
                     'viscosity_pa_s': 1.0e-3, 'pressure_viscosity_coefficient_per_pa': 1.0e-8,
                     'plane_strain_yield_pa': 230e6, 'contact_radius_m': radius,
                     'strip_entry_speed_fraction': E6_STRIP_SPEED_FRACTION}, notes, q,
                 'INDICATIVE_ASSUMED_INPUTS', 'The smooth inlet film formula against the '
                 'thesis table with one assumed speed ratio; a software comparison of the same '
                 'closed form, not a check of the film physics.', ['ASSUMED_STRIP_SPEED_RATIO'])


def _bt_v4_film():
    from . import bite_tribology as bt
    lub = bt.Lubricant(2.5e-3, 313.15, 0.015, 1.2e-8, name='E4 Table I oil')
    q = []
    for u, ref in ((5.0, 0.22), (40.0, 1.76)):
        res = bt.inlet_film_thickness(
            lub, roll_surface_speed_m_s=u, strip_entry_speed_m_s=0.5 * u,
            entry_thickness_m=50e-6, exit_thickness_m=25e-6, contact_radius_m=0.135,
            plane_strain_yield_pa=150e6, back_tension_pa=20e6, inlet_temperature_k=313.15)
        key = f'film_ratio_{u:g}_m_s'
        q.append(_pq(key, '1', res['film_thickness_m'] / 0.3e-6, key, ref,
                     f'film ratio at {u:g} m/s (MODEL_OUTPUT, BT-S3 EX)',
                     'INDICATIVE_ASSUMED_INPUTS', 'BT-V4-FILM'))
    notes = ['50 -> 25 um, plane-strain yield 150 MPa, tensions 20 MPa, R 135 mm, oil 2.5e-3 Pa s '
             'and 1.2e-8 /Pa, composite roughness 0.3 um [E4 EX, Table I].',
             'Roll surface speed = the quoted speed, strip entry speed half of it, contact radius '
             '= R, inlet 40 C: ASSUMED.']
    return _case('BT-V4-FILM', 'Film ratio of the E4 foil pass (film only)',
                 'Sutcliffe & Montmitonnet (2001) (E4 = BT-S3)', 'BT-S3 (= E4)', 'EX',
                 'MODEL_OUTPUT', {'entry_thickness_m': 50e-6, 'exit_thickness_m': 25e-6,
                                  'composite_roughness_m': 0.3e-6}, notes, q,
                 'INDICATIVE_ASSUMED_INPUTS', 'Film ratio only; the load and slip curves of the '
                 'source are not encoded.', ['ASSUMED_SPEEDS_AND_INLET_TEMPERATURE'])


def _a9_pressure_laws():
    from . import bite_tribology as bt
    eta0, alpha, t = 1.409e-3, 10.40e-9, 313.15
    laws = {'barus': bt.Lubricant(eta0, t, 0.0155, alpha),
            'roelands': bt.Lubricant(eta0, t, 0.0155, alpha, pressure_law='roelands')}
    measured = ((100e6, 3.985e-3, 'viscometer'), (625e6, 2.5, 'disc machine'),
                (945e6, 15.0, 'disc machine'), (1510e6, 740.0, 'disc machine'))
    q = []
    for law, lub in laws.items():
        for p, ref, how in measured:
            v = lub.dynamic_viscosity_pa_s(t, p)
            key = f'viscosity_{law}_{p / 1e6:g}_mpa_pa_s'
            q.append(_pq(key, 'Pa s', v, key, ref,
                         f'measured at {p / 1e6:g} MPa and 40 C, {how} (MEASUREMENT, E6 FT)',
                         _band_verdict(v / ref), 'A9-PRESSURE-LAWS-KEROSINE'))
    z = laws['roelands'].roelands_index(t)
    notes = ['Somentor 31, a kerosine base oil without additives (not a plant\'s rolling oil), '
             '40 C: eta0 1.409e-3 Pa s, alpha 10.40e-9 /Pa [E6 FT, Table 2.1].',
             f'Roelands index from the low-pressure slope [E5 FT (4.194)]: z = {z:.6f} [run].']
    note = ('Neither law carries this oil from the inlet to bite pressure: Barus is 0.37 to 12.6 '
            'times the measured value above 100 MPa, Roelands with the index from the '
            'low-pressure slope 0.03 to 0.08 times (low by a factor 12 to 30). Barus stays the '
            'default; enter roelands_z or a Barus coefficient fitted at the pressure of interest '
            'and read any valley friction as an order of magnitude.')
    return _case('A9-PRESSURE-LAWS-KEROSINE', 'Viscosity against pressure: Barus and Roelands '
                 'on a kerosine base oil', 'Sutcliffe (1989) thesis (E6); Boemer (2020) thesis '
                 '(E5, Roelands form)', 'E6, E5', 'FT', 'MEASUREMENT',
                 {'viscosity_pa_s': eta0, 'pressure_viscosity_coefficient_per_pa': alpha,
                  'temperature_k': t}, notes, q, 'RECORDED_DISCREPANCY', note,
                 ['ONE_OIL_WITH_DATA'])


def _bt_g3_crushing_laws():
    """The four transcribed crushing laws against the thesis's theory values [E6 FT p.38]."""
    from . import asperity_contact as ac
    laws = {'thesis_fit_eq_3_20': lambda a, p: ac.crushing_rate_thesis(a, p),
            'korzekwa_regression': lambda a, p: ac.crushing_rate_from_strain_rate(
                ac.plastic_strain_rate_korzekwa(a, ac.hardness_from_mean_pressure(a, p))),
            'marsault_form': lambda a, p: ac.crushing_rate_from_strain_rate(
                ac.plastic_strain_rate_marsault(a, ac.hardness_from_mean_pressure(a, p))),
            'wilson_sheu_fit': lambda a, p: ac.crushing_rate_from_strain_rate(
                ac.plastic_strain_rate_wilson_sheu(a, ac.hardness_from_mean_pressure(a, p)))}
    refs = {1.0: (1.47, 0.67), 0.6: (0.16, 0.32)}   # (new field, Wilson & Sheu's field)
    q = []
    for name, fun in laws.items():
        for p_ in (1.0, 0.6):
            ref = refs[p_][1] if name == 'wilson_sheu_fit' else refs[p_][0]
            key = f'w_{name}_a050_p{int(p_ * 10):02d}'
            q.append(_quantity(key, '1', fun(0.5, p_), RECORDED['BT-G3-CRUSHING-LAWS'][key],
                               ref, f'theory value at A 0.5, p_bar/2k {p_:g} '
                               + ("(Wilson & Sheu's field)" if name == 'wilson_sheu_fit'
                                  else '(new velocity field)') + ' (MODEL_OUTPUT, E6 FT p.38)',
                               recorded_on=RECORDED_ON_SPEC18_P6))
    notes = ['Laws: the thesis fit [E6 FT (3.20), clipped to 0.05-2.5], the regression of '
             'Korzekwa et al.\'s results [E5 FT (4.97)-(4.100)], the Marsault form [E5 FT '
             '(4.96)], Wilson & Sheu\'s fit [E5 FT (4.92)]; W = 1/E_p, p_bar/2k = A*H_a/2 '
             '[derived].',
             'physicroll/asperity_contact.py; nothing in the engine uses these functions.']
    return _case('BT-G3-CRUSHING-LAWS', 'Asperity crushing laws against the thesis theory '
                 'values', 'Sutcliffe (1989) thesis (E6); Boemer (2020) thesis (E5)', 'E6, E5',
                 'FT', 'MODEL_OUTPUT', {'contact_area_ratio': 0.5,
                                        'p_over_2k': [1.0, 0.6]}, notes, q,
                 'RECORDED_DISCREPANCY', 'The transcribed fits do not agree with one another or '
                 'with the theory values away from one point; they are not assembled into a '
                 'model.', ['NOT_ASSEMBLED_INTO_A_MODEL'])


_CASES = {'BT-V1': _bt_v1, 'BT-V2-R89': lambda: _bt_v2('BT-V2-R89', 0.089),
          'BT-V2-R135': lambda: _bt_v2('BT-V2-R135', 0.135),
          'BT-V3-FIG1-140UM': _bt_v3_fig1, 'BT-V3-EQ29': _bt_v3_eq29, 'SS-V2': _ss_v2,
          'SS-V3': _ss_v3, 'TM-LC7': _tm_lc7, 'BT-V1-HS': _bt_v1_hs,
          'BT-V2-R89-HS': lambda: _bt_v2_hs('BT-V2-R89-HS', 0.089),
          'BT-V2-R135-HS': lambda: _bt_v2_hs('BT-V2-R135-HS', 0.135),
          'BT-V3-FIG1-140UM-HS': _bt_v3_fig1_hs, 'BT-V3-EQ29-HS': _bt_v3_eq29_hs,
          'BT-X29-LOAD-EXPONENT-HS': _bt_x29_load_exponent_hs,
          'BT-G3-FILM-E6-T42': _bt_g3_film_e6, 'BT-V4-FILM': _bt_v4_film,
          'A9-PRESSURE-LAWS-KEROSINE': _a9_pressure_laws,
          'BT-G3-CRUSHING-LAWS': _bt_g3_crushing_laws}


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
    """Rows for the guide: id, quantity, project, reference, ratio, verdict.

    ``verdict`` is the row verdict: ``NO_REFERENCE_VALUE`` for a quantity without a published
    value (project value recorded only), else the verdict the case set for the row or, by
    default, the case verdict (also in ``case_verdict``).
    """
    result = run_all() if result is None else result
    rows = []
    for case in result['cases']:
        for q in case['quantities']:
            rows.append({'id': case['id'], 'quantity': q['name'], 'unit': q['unit'],
                         'project': q['project_value'], 'reference': q['reference_value'],
                         'reference_label': q['reference_label'],
                         'ratio': q['ratio_project_to_reference'], 'verdict': q['row_verdict'],
                         'case_verdict': case['verdict']})
    return rows


def _stand(stand):
    """``StandModel`` from a stand dict: directly when it carries the two damping coefficients
    (``work_backup_damping_n_s_m``, ``housing_damping_n_s_m``), else from
    ``modal_damping_ratio``."""
    if 'work_backup_damping_n_s_m' in stand or 'housing_damping_n_s_m' in stand:
        model = chatter.StandModel(*(stand[k] for k in (
            'work_roll_mass_kg', 'backup_roll_mass_kg', 'work_backup_contact_stiffness_n_m',
            'housing_stiffness_n_m', 'work_backup_damping_n_s_m', 'housing_damping_n_s_m')))
        model.validate()
        return model
    return chatter.StandModel.from_modal_damping(
        stand['work_roll_mass_kg'], stand['backup_roll_mass_kg'],
        stand['work_backup_contact_stiffness_n_m'], stand['housing_stiffness_n_m'],
        stand['modal_damping_ratio'])


_PASS_KEYS = ('entry_thickness_m', 'exit_thickness_m', 'width_m', 'work_roll_radius_m',
              'mean_flow_stress_pa', 'friction_coefficient', 'entry_tension_pa',
              'exit_tension_pa')


def _bite_pass(bite_pass):
    try:
        return chatter.BitePass(*(bite_pass[k] for k in _PASS_KEYS))
    except KeyError as exc:
        raise ValueError(f'missing key {exc} in bite_pass') from exc


def equivalent_coulomb_friction(bite_pass: dict, friction_factor, shear_yield_pa,
                                **bite_options) -> dict:
    """Coulomb coefficient with the same mean friction stress as a friction factor [D, SPEC18].

    Fixed point ``mu <- m*k*width*L/F`` on ``chatter.derive_bite_response`` (``bite_options``
    are passed to it), started at 0.025, tolerance 1e-9 on mu, at most 50 derivations; the
    returned ``friction_coefficient`` is the one the last bite was derived with. ``bite_pass``:
    the ``chatter.BitePass`` fields except ``friction_coefficient`` (ignored if present).
    ValueError when it does not converge or a derivation is rejected.
    """
    m = _finite_positive('friction_factor', friction_factor)
    k = _finite_positive('shear_yield_pa', shear_yield_pa)
    mu = 0.025
    for n in range(1, 51):
        bite = chatter.derive_bite_response(_bite_pass(dict(bite_pass, friction_coefficient=mu)),
                                            **bite_options)
        p_mean = bite.separating_force_n / (bite_pass['width_m'] * bite.contact_length_m)
        new = m * k / p_mean
        if abs(new - mu) <= 1e-9:
            return {'friction_coefficient': mu, 'mean_pressure_pa': p_mean,
                    'mean_friction_stress_pa': m * k, 'friction_factor': m,
                    'shear_yield_pa': k, 'derivations': n,
                    'basis': 'mu*p_mean = m*k by fixed point mu <- m*k*width*L/F on the '
                             'slab + Hitchcock bite [D, SPEC18]'}
        mu = new
    raise ValueError('equivalent Coulomb friction not converged in 50 bite derivations')


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
                             roll_poisson_ratio=0.3, cells=256,
                             speed_range_m_s=(0.05, 60.0)) -> dict:
    """Predicted chatter onset (with and without bite damping) beside a measured pair.

    ``stand``: the keys of a band case's ``stand`` section (masses, stiffnesses,
    ``modal_damping_ratio``), or the masses and stiffnesses with ``work_backup_damping_n_s_m``
    and ``housing_damping_n_s_m`` (the stand is then built directly); ``spans``:
    ``strip_youngs_modulus_pa``, ``entry_span_length_m``, ``exit_span_length_m``;
    ``bite_pass``: the eight ``chatter.BitePass`` fields. Uses ``StandModel.from_modal_damping``
    (or the direct constructor), ``derive_bite_response`` (slab + Hitchcock) and
    ``critical_speed`` over ``speed_range_m_s``. A harness: it holds no mill of its own.
    """
    speed_m = _finite_positive('measured_critical_speed_m_s', measured_critical_speed_m_s)
    freq_m = _finite_positive('measured_frequency_hz', measured_frequency_hz)
    try:
        model = _stand(stand)
        sp = chatter.StripSpans(spans['strip_youngs_modulus_pa'], spans['entry_span_length_m'],
                                spans['exit_span_length_m'])
        bp = chatter.BitePass(*(bite_pass[k] for k in _PASS_KEYS))
    except KeyError as exc:
        raise ValueError(f'missing key {exc} in stand, spans or bite_pass') from exc
    sp.validate()
    bite = chatter.derive_bite_response(bp, roll_youngs_modulus_pa=roll_youngs_modulus_pa,
                                        roll_poisson_ratio=roll_poisson_ratio, cells=cells)
    crit = chatter.critical_speed(model, bite, sp, speed_range_m_s=speed_range_m_s,
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


def _model_row(derive, bite_pass, width):
    try:
        out = derive(bite_pass)
    except ValueError as exc:
        return {'rejected': str(exc)}
    bite, extra = out if isinstance(out, tuple) else (out, None)
    row = {'force_per_width_n_m': bite.separating_force_n / width,
           'forward_slip_fraction': bite.forward_slip_fraction,
           'contact_length_m': bite.contact_length_m,
           'strip_modulus_per_width_pa': bite.strip_modulus_n_m / width,
           'exit_tension_force_sensitivity_per_width_m': -bite.dforce_dexit_tension_m2 / width,
           'flags': list(bite.flags)}
    if extra is not None:
        row['zone_structure'] = extra['extra']['zone_structure']
        row['load_exponent_in_friction'] = extra['extra']['load_exponent_in_friction']
    return row


def bite_model_comparison(case) -> dict:
    """Hitchcock, experimental mattress and reduced half-space bite of the case pass and every
    schedule pass, side by side, with the same inputs (each model's own rejection reason where
    it has no solution). A comparison of models with each other, not a correction of any of
    them: the spread is a measure of what is not known [SPEC18 package 4].

    ``case``: a band case dict (validated by ``band_diagnosis.validate_case``). The strip
    modulus of the half-space thickness spring is ``material.youngs_modulus_pa/(1 - 0.33^2)``.
    """
    from . import band_diagnosis as bd
    from . import band_process as bproc
    from .foil_bite import derive_bite_response_mattress
    from .halfspace_bite import derive_bite_response_half_space
    eff = bd.validate_case(case)
    st, o, m = eff['stand'], eff['model_options'], eff['material']
    e, nu = st['roll_youngs_modulus_pa'], st['roll_poisson_ratio']
    width = eff['pass']['width_m']
    es = m['youngs_modulus_pa'] / (1 - bd.bw.STRIP_POISSON_RATIO ** 2)
    models = {
        'hitchcock': lambda bp_: chatter.derive_bite_response(
            bp_, roll_youngs_modulus_pa=e, roll_poisson_ratio=nu, cells=o['cells'],
            max_radius_ratio=o['max_radius_ratio']),
        'experimental_mattress': lambda bp_: derive_bite_response_mattress(
            bp_, roll_youngs_modulus_pa=e, roll_poisson_ratio=nu,
            cells=max(o['cells'], bd.MATTRESS_MIN_CELLS)),
        'reduced_half_space': lambda bp_: derive_bite_response_half_space(
            bp_, roll_youngs_modulus_pa=e, roll_poisson_ratio=nu,
            strip_plane_strain_modulus_pa=es,
            shear_cap_factor=o.get('shear_cap_factor', 1.0), with_state=True)}
    rows = []
    for label, src in bproc.pass_rows(eff):
        bp_ = bproc.bite_pass(eff, src)
        row = {'label': label, 'entry_thickness_m': src['entry_thickness_m'],
               'exit_thickness_m': src['exit_thickness_m'],
               'friction_coefficient': src['friction_coefficient']}
        for name, derive in models.items():
            row[name] = _model_row(derive, bp_, width)
        rows.append(row)
    return {'status': STATUS, 'case_name': eff['name'], 'rows': rows,
            'strip_plane_strain_modulus_pa': es,
            'note': 'The same inputs in three bite models. The models disagree by up to a factor '
                    'of about 2 in force at foil gauge; the spread measures what is not known '
                    '(friction, with a load exponent of about 3 there, is the larger unknown). '
                    'Not a correction of the mattress or the Hitchcock numbers.',
            'limitations': ['Each model has its own domain and status; none is validated on a '
                            'mill.']}


def _fmt(value):
    if value is None:
        return '-'
    return f'{value:.6g}'


def main(argv=None):
    """``python -m physicroll.benchmarks [--json] [--bite-comparison CASE.json]``."""
    parser = argparse.ArgumentParser(
        description='Project values beside published benchmark values (software comparison, '
                    'not physical validation)')
    parser.add_argument('--json', action='store_true', help='print the full result as JSON')
    parser.add_argument('--bite-comparison', metavar='CASE.json',
                        help='print the three bite models side by side for a band case')
    args = parser.parse_args(argv)
    if args.bite_comparison:
        with open(args.bite_comparison, encoding='utf-8') as fh:
            comp = bite_model_comparison(json.load(fh))
        if args.json:
            print(json.dumps(comp, indent=1, allow_nan=False))
            return 0
        print(comp['note'])
        print(f'{"pass":40} {"model":22} {"F/w N/m":>12} {"slip":>8} {"L mm":>7} '
              f'{"Q/w Pa":>11}  structure')
        for row in comp['rows']:
            for name in ('hitchcock', 'experimental_mattress', 'reduced_half_space'):
                r = row[name]
                if 'rejected' in r:
                    print(f'{row["label"][:40]:40} {name:22} rejected: {r["rejected"][:60]}')
                    continue
                print(f'{row["label"][:40]:40} {name:22} {r["force_per_width_n_m"]:12.6g} '
                      f'{r["forward_slip_fraction"]:8.4f} {r["contact_length_m"] * 1e3:7.3f} '
                      f'{r["strip_modulus_per_width_pa"]:11.4g}  {r.get("zone_structure", "")}')
        return 0
    result = run_all()
    if args.json:
        print(json.dumps(result, indent=1, allow_nan=False))
        return 0
    print(STATUS)
    print(f'agreement band on project / reference: {AGREEMENT_BAND[0]}-{AGREEMENT_BAND[1]}')
    rows = table_rows(result)
    width = max([28] + [len(r['quantity']) for r in rows])
    print(f'{"id":18} {"quantity":{width}} {"project":>12} {"reference":>12} {"ratio":>8}  '
          'verdict')
    for r in rows:
        print(f'{r["id"]:18} {r["quantity"]:{width}} {_fmt(r["project"]):>12} '
              f'{_fmt(r["reference"]):>12} {_fmt(r["ratio"]):>8}  {r["verdict"]}')
    print('TM-LC7 project values rest on three substitutions; its speed rows are indicative '
          'only:')
    for line in TM_LC7_SUBSTITUTIONS:
        print('  ' + line)
    print('not encoded:')
    for e in result['not_encoded']:
        print(f'  {e["id"]}: {e["reason"]}')
    for line in result['limitations']:
        print('- ' + line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
