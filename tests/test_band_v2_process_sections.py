"""SPEC18 split of tests/test_band_v2_sections.py (module time): the process, bite and coverage
section tests; the lengthwise integration and report tests stay in test_band_v2_sections."""
import copy
from html import escape
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from physicroll import mill_dynamics as md
from physicroll import band_process as bp
from physicroll.band_diagnosis import (CASE_SCHEMA_V2, HYPOTHESIS_IDS, MATTRESS_MIN_CELLS,
                                       diagnose, load_case, result_json, validate_case)
from physicroll.band_report import render_band_report
from physicroll.chatter import BitePass
from physicroll.foil_bite import derive_bite_response_mattress
from tests.test_band_lengthwise import (COARSE, HARDENING, LONG, NOZZLES, ROOT, SCEN, TRIBOLOGY,
                                        _h, v2, width_model)


class InletAngleTests(unittest.TestCase):
    """SPEC17 BT-G7: the film's inlet angle uses the undeformed roll for a mattress bite (its
    contact_radius_ratio L^2/(R*draft) is not a radius) and the deformed arc R' for a
    Hitchcock bite (unchanged)."""

    def test_mattress_bite_uses_undeformed_roll(self):
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                         mean_flow_stress_pa=285e6, friction_coefficient=0.03)
        c['model_options']['bite_model'] = 'mattress'
        c['tribology'] = dict(TRIBOLOGY)
        r = diagnose(c)
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        op = r['process']['friction']['operating']
        self.assertEqual(op['film_inlet_radius_ratio'], 1.0)
        self.assertEqual(op['inlet_angle_basis'], bp.INLET_ANGLE_BASIS_MATTRESS)
        ratio = op['contact_radius_ratio']
        self.assertGreater(ratio, 1.0)
        vc = validate_case(c)
        old = bp.friction_at(vc['tribology'], vc['pass'], c['pass']['work_roll_radius_m'],
                             ratio, op['forward_slip_fraction'], op['exit_speed_m_s'])
        new = op['film_ratio'] * ratio ** 0.5
        self.assertLessEqual(abs(new - old['film_ratio']), 1e-9 * old['film_ratio'])

    def test_hitchcock_bite_keeps_the_deformed_arc(self):
        # the Hitchcock operating bite of a diagnose run: LengthwiseIntegrationTests
        # (test_hitchcock_film_uses_the_deformed_arc); here the same call as before the change,
        # pinned from the lengthwise demo artifact
        art = json.loads((ROOT / 'artifacts' / 'band_diagnosis' /
                          'lengthwise-bands-demo.result.json').read_text())
        aop = art['process']['friction']['operating']
        case = validate_case(load_case(SCEN / 'band_diagnosis_lengthwise_bands.json'))
        res = bp.friction_at(case['tribology'], art['effective_inputs']['pass'],
                             case['pass']['work_roll_radius_m'], aop['contact_radius_ratio'],
                             aop['forward_slip_fraction'], aop['exit_speed_m_s'])
        self.assertAlmostEqual(res['film_ratio'], 0.180115, places=6)
        self.assertAlmostEqual(aop['film_ratio'], 0.180115, places=6)


class ReviewFindingTests(unittest.TestCase):
    """Reproducers of code-review findings 1 and 5 (process sections)."""

    def test_schedule_row_labelled_case_pass_keeps_operating_flow_stress(self):
        # finding 1: a schedule row labelled 'case pass' overwrote the operating pass in a
        # label-keyed map: both got the schedule row's 149.0 MPa instead of 267.6 / 149.0
        c = v2(**LONG)
        c['hardening'] = dict(HARDENING, use_computed_flow_stress=True)
        c['schedule'] = [{'label': 'case pass', 'entry_thickness_m': 2.2e-3,
                          'exit_thickness_m': 1.5e-3, 'mean_flow_stress_pa': 150e6,
                          'friction_coefficient': 0.05, 'entry_tension_pa': 20e6,
                          'exit_tension_pa': 25e6, 'exit_speed_m_s': 3.0}]
        r = diagnose(c)
        op, row = r['process']['flow_stress']['passes']
        self.assertAlmostEqual(op['computed_mean_flow_stress_pa'] / 1e6, 267.564, places=2)
        self.assertAlmostEqual(row['computed_mean_flow_stress_pa'] / 1e6, 149.009, places=2)
        eff = r['effective_inputs']
        self.assertEqual(eff['pass']['mean_flow_stress_pa'], op['computed_mean_flow_stress_pa'])
        self.assertEqual(op['used_mean_flow_stress_pa'], op['computed_mean_flow_stress_pa'])
        self.assertEqual(eff['schedule'][0]['mean_flow_stress_pa'],
                         row['computed_mean_flow_stress_pa'])
        self.assertEqual(row['used_mean_flow_stress_pa'], row['computed_mean_flow_stress_pa'])

    def test_mattress_bite_sensitivities_use_the_mattress_model(self):
        # finding 5: with bite_model 'mattress' the flow-stress / friction sensitivities went
        # through the Hitchcock derivation, which rejects this foil pass (R'/R ~2.6 > 1.5):
        # incoming_variation FAILED and the speed-change gauge shift was rejected
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                         mean_flow_stress_pa=285e6, friction_coefficient=0.03)
        c['model_options']['bite_model'] = 'mattress'
        c['tribology'] = dict(TRIBOLOGY)
        c['gauge_control'] = {'compensation_gain': 0.9, 'bandwidth_hz': 25.0,
                              'force_filter_hz': None}
        c['incoming_variation'] = {'flow_stress_variation_fraction': 0.02,
                                   'coil_synchronous': False}
        r = diagnose(c)
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        iv = r['incoming_variation']
        self.assertEqual(iv['status'], md.STATUS, iv.get('error'))
        self.assertEqual(iv['sensitivity_bite_model'], 'experimental_mattress')
        p = c['pass']
        kw = dict(roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                  cells=max(64, MATTRESS_MIN_CELLS))

        def force(y):
            return derive_bite_response_mattress(BitePass(
                p['entry_thickness_m'], p['exit_thickness_m'], p['width_m'],
                p['work_roll_radius_m'], y, p['friction_coefficient'], p['entry_tension_pa'],
                p['exit_tension_pa']), **kw).separating_force_n
        y, dy = p['mean_flow_stress_pa'], 0.005 * p['mean_flow_stress_pa']
        self.assertAlmostEqual(iv['dforce_dflow_stress_m2'],
                               (force(y + dy) - force(y - dy)) / (2 * dy), places=12)
        # the report names the bite model (foil_bite marks its bites source 'supplied')
        self.assertIn('<td>bite source</td><td>experimental_mattress</td>',
                      render_band_report(r))
        shift = r['gauge_control']['speed_change_gauge_shift']
        self.assertNotIn('rejected', shift)
        self.assertEqual(shift['sensitivity_bite_model'], 'experimental_mattress')
        self.assertGreater(shift['dforce_dfriction_n'], 0)


def _margin_case(damping, speed):
    c = v2(orientation='transverse')
    c['stand']['modal_damping_ratio'] = damping
    c['pass']['exit_speed_m_s'] = speed
    r = diagnose(c)
    h = _h(r)['third_octave_self_excited_chatter']
    return r, h, next(e for e in h['evidence'] if e['criterion'] == 'speed margin')


class SpeedMarginScanRangeTests(unittest.TestCase):
    """Review finding: 'no crossing inside the critical-speed scan (0.05-60 m/s)' is no
    evidence about an operating speed outside it; the operating-point stability decides."""

    def test_above_the_scan_unstable_at_the_operating_point_supports(self):
        # reviewer's reproducer: supplied baseline bite, damping 0.21, 100 m/s
        r, h, e = _margin_case(0.21, 100.0)
        ch = r['chatter']
        self.assertEqual(ch['critical_speed']['status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertFalse(ch['with_bite_damping']['stable_at_operating_speed'])
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('above the scanned range 0.05-60 m/s', e['observed'])
        self.assertIn('basis: operating-point stability', e['observed'])
        self.assertIn('operating-point stability', e['expected'])
        self.assertEqual(ch['operating_speed_outside_scanned_range']['side'], 'above')
        self.assertIn('OPERATING_SPEED_OUTSIDE_SCANNED_RANGE', r['flags'])
        self.assertEqual(h['score'], 5)          # was 0 with the contradiction (-2 -> +3)
        html = render_band_report(r)
        self.assertIn('does not mean stable at the operating speed', html)

    def test_inside_the_scan_without_crossing_still_contradicts(self):
        r, h, e = _margin_case(0.21, 10.0)
        self.assertEqual(r['chatter']['critical_speed']['status'], 'STABLE_OVER_SCANNED_RANGE')
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'moderate'))
        self.assertEqual(e['expected'], 'u_op >= u_crit(0)')
        self.assertNotIn('operating_speed_outside_scanned_range', r['chatter'])
        self.assertNotIn('OPERATING_SPEED_OUTSIDE_SCANNED_RANGE', r['flags'])

    def test_above_the_scan_stable_at_the_operating_point_contradicts(self):
        r, h, e = _margin_case(0.6, 100.0)
        self.assertTrue(r['chatter']['with_bite_damping']['stable_at_operating_speed'])
        self.assertTrue(r['chatter']['without_bite_damping']['stable_at_operating_speed'])
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'moderate'))
        self.assertIn('rests on the operating point', e['observed'])
        self.assertIn('beyond the scanned range', e['expected'])


class ZeroFeedbackSensitivityTests(unittest.TestCase):
    """Review finding: shape_inputs with exit_tension_force_sensitivity_per_width_m = 0 (no
    exit-tension feedback, the compliance-only limit) validated but failed in strip_shape."""

    def test_zero_supplied_sensitivity_is_assessed(self):
        c = v2(**LONG)
        c['width_model'] = width_model(blocked_nozzle_indices=[12], bite_heat_per_width_w_m=4e5)
        si = {'strip_stiffness_per_width_pa': 4e10,
              'exit_tension_force_sensitivity_per_width_m': 0.0,
              'bite_half_length_m': 5e-3, 'provenance': 'unit test: no feedback'}
        c['width_model']['shape_inputs'] = si
        r = diagnose(c)
        st = r['width']['shape']['steady']
        self.assertNotIn(st.get('status'), ('FAILED', 'NOT_ASSESSABLE', None))
        self.assertEqual(st['tension_feedback_stiffness_per_width_pa'], 0.0)
        self.assertEqual(st['i_units_with_feedback'], st['i_units_compliance_only'])
        self.assertEqual(st['feedback_peak_i_units'], st['compliance_only_peak_i_units'])
        row = next(x for x in r['width']['gauge_trend']['rows']
                   if x['shape_inputs_basis'] == 'shape_inputs_supplied')
        self.assertNotIn('rejected', row)
        self.assertEqual(row['linear_feedback_i_units'], row['compliance_only_i_units'])
        self.assertEqual(row['tension_feedback_stiffness_per_width_pa'], 0.0)
        json.dumps(r, allow_nan=False)
        html = render_band_report(r)
        self.assertNotRegex(html, r'\b(nan|inf|NaN|Infinity)\b')
        bad = copy.deepcopy(c)
        bad['width_model']['shape_inputs']['exit_tension_force_sensitivity_per_width_m'] = -1e-3
        with self.assertRaises(ValueError):
            validate_case(bad)


def _coverage_case(positions, standoff=0.1, half_angle_tan=0.1):
    """No width model, phase-1 coolant coverage: 1.7 m barrel, 0.1 m nozzle pitch, flat fans
    of footprint 2*standoff*half_angle_tan (0.02 m by default)."""
    import math
    c = v2(orientation='longitudinal', band_positions_across_width_m=positions)
    c['coolant'] = {'barrel_length_m': 1.7, 'nozzle_pitch_m': 0.1, 'standoff_m': standoff,
                    'spray_angle_rad': 2 * math.atan(half_angle_tan), 'offset_angle_rad': 0.0,
                    'blocked_nozzle_indices': [], 'roll_expansion_coefficient_per_k': 1.2e-5,
                    'assumed_excess_temperature_k': 5.0}
    r = diagnose(c)
    h = _h(r)['nozzle_thermal_stripe']
    e = next(x for x in h['evidence'] if x['criterion'].startswith('band positions vs model'))
    return r, h, e


class CoverageIntervalMatchTests(unittest.TestCase):
    """Review finding: phase-1 band-risk stripes are intervals; the nozzle hypothesis matched
    only their centres and contradicted a band the coverage screen had matched."""

    def test_band_inside_an_uncovered_interval_matches_as_in_the_screen(self):
        r, h, e = _coverage_case([0.065])      # inside the 0.06-0.14 m gap, 0.035 m off centre
        self.assertEqual(r['screens']['band_position_match']['status'],
                         'ALL_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertIn('inside model intervals 0.06-0.14 m', e['observed'])
        self.assertIn('inside an interval widened by 0.025 m', e['expected'])
        pred = h['model_prediction']
        self.assertAlmostEqual(pred['model_intervals_m'][0][0], 0.06)
        self.assertAlmostEqual(pred['model_intervals_m'][0][1], 0.14)

    def test_band_outside_every_interval_still_contradicts(self):
        # footprint 0.09 m: gaps of 0.01 m around x.x0 m; 0.15 m is 0.045 m from the nearest
        r, h, e = _coverage_case([0.15], half_angle_tan=0.45)
        self.assertEqual(r['screens']['band_position_match']['status'],
                         'NO_OBSERVED_POSITIONS_MATCHED')
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'weak'))
        self.assertIn('no observed position inside or within 0.025 m', e['observed'])

    def test_point_sources_still_match_by_centre(self):
        def run(x):
            c = v2(**LONG, band_positions_across_width_m=[x])
            c['width_model'] = width_model(blocked_nozzle_indices=[12],
                                           bite_heat_per_width_w_m=4e5)
            h = _h(diagnose(c))['nozzle_thermal_stripe']
            return h, next(x for x in h['evidence']
                           if x['criterion'].startswith('band positions vs model'))
        h, e = run(NOZZLES[12])
        self.assertEqual(e['verdict'], 'SUPPORTS')
        self.assertNotIn('model_intervals_m', h['model_prediction'])
        h, e = run(NOZZLES[12] + 0.03)       # tolerance: a quarter of the 52 mm pitch
        self.assertEqual((e['verdict'], e['weight']), ('CONTRADICTS', 'weak'))
        self.assertIn('no observed position near', e['observed'])


class KinematicSlipOnlyTests(unittest.TestCase):
    """Review finding: the zero-slip fallback for a slip of 0.5 or more applies to the
    roll-borne pitch kinematics only, not to the forward-slip screen or the skid evidence."""

    @staticmethod
    def _run(slip):
        c = v2(orientation='irregular')
        c['model_options']['bite_response_override']['forward_slip_fraction'] = slip
        r = diagnose(c)
        h = _h(r)['skidding_loss_of_forward_slip']
        return r, h, h['evidence'][0]

    def test_supplied_slip_above_half_is_not_skidding(self):
        r, h, e = self._run(0.6)
        fs = r['screens']['forward_slip']
        self.assertEqual(fs['status'], 'NOT_ASSESSABLE')
        self.assertEqual(fs['forward_slip_fraction'], 0.6)
        self.assertEqual((e['verdict'], e['basis']), ('NEUTRAL', 'model'))
        self.assertTrue(e['observed'].startswith('0.6000; not assessable'))
        self.assertEqual(h['model_prediction']['forward_slip_fraction'], 0.6)
        self.assertNotEqual(h['standing'], 'CONSISTENT_LEADING')
        self.assertEqual(r['signatures']['forward_slip_fraction_used'], 0.0)
        self.assertIn('FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS',
                      r['flags'])
        self.assertIn('NOT_ASSESSABLE', render_band_report(r))

    def test_non_positive_slip_still_skids(self):
        r, h, e = self._run(-0.01)
        self.assertEqual(r['screens']['forward_slip']['status'],
                         'SKIDDING_NEUTRAL_POINT_AT_OR_BEYOND_EXIT')
        self.assertEqual((e['verdict'], e['weight']), ('SUPPORTS', 'strong'))
        self.assertEqual(r['signatures']['forward_slip_fraction_used'], -0.01)
        self.assertNotIn('FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS',
                         r['flags'])


class ViscosityTableSectionTests(unittest.TestCase):
    """SPEC18 package 5: a case with a viscosity table: the friction rows carry the law and
    the flag; a two-point table equal to the exponential law changes no number. The operating
    bite is the supplied one (fast)."""

    def _section(self, lubricant_extra):
        c = v2(**LONG)
        c['tribology'] = copy.deepcopy(TRIBOLOGY)
        c['tribology']['lubricant'].update(lubricant_extra)
        case = validate_case(c)
        from physicroll import band_diagnosis as bd
        bite = bd._supplied_bite(case)

        class Cache:
            def get(self, bite_pass, model=None):
                return bite
        return bp.friction_section(case, case['tribology'], Cache(), bite)

    def test_table_flags_and_identity(self):
        lub = TRIBOLOGY['lubricant']
        eta = [lub['viscosity_ref_pa_s'] * math.exp(
            -lub['temperature_viscosity_coefficient_per_k'] * (t - lub['reference_temperature_k']))
            for t in (293.15, 363.15)]
        table = [{'temperature_k': 293.15, 'viscosity_pa_s': eta[0]},
                 {'temperature_k': 363.15, 'viscosity_pa_s': eta[1]}]
        plain = self._section({})
        tab = self._section({'viscosity_table': table})
        self.assertNotIn('VISCOSITY_FROM_TABLE', plain['flags'])
        self.assertNotIn('viscosity_law', plain['operating'])
        self.assertIn('VISCOSITY_FROM_TABLE', tab['flags'])
        self.assertIn('viscosity table', tab['operating']['viscosity_law'])
        for key in ('film_thickness_m', 'film_ratio', 'computed_friction_coefficient'):
            a, b = plain['operating'][key], tab['operating'][key]
            self.assertLessEqual(abs(b / a - 1), 1e-12, key)

    def test_lubricant_keys_validate_and_default(self):
        c = v2(**LONG)
        c['tribology'] = copy.deepcopy(TRIBOLOGY)
        v = validate_case(c)['tribology']['lubricant']
        self.assertEqual(v['pressure_law'], 'barus')
        for k in ('viscosity_table', 'roelands_z', 'eyring_stress_pa',
                  'eyring_stress_pressure_coefficient', 'limiting_shear_stress_pa',
                  'limiting_shear_pressure_coefficient'):
            self.assertIsNone(v[k])
        for key, bad, msg in (
                ('viscosity_table', [{'temperature_k': 300.0, 'viscosity_pa_s': 1e-3}],
                 'viscosity_table must be null or >= 2 points'),
                ('pressure_law', 'wlf', 'pressure_law must be one of'),
                ('limiting_shear_pressure_coefficient', 2.0,
                 'limiting_shear_pressure_coefficient must be null or in')):
            c2 = copy.deepcopy(c)
            c2['tribology']['lubricant'][key] = bad
            with self.assertRaisesRegex(ValueError, msg):
                validate_case(c2)

    def test_limiting_shear_below_the_published_bound_is_flagged(self):
        sec = self._section({'limiting_shear_pressure_coefficient': 0.03})
        self.assertIn('LIMITING_SHEAR_BELOW_PUBLISHED_LOWER_BOUND', sec['flags'])
        self.assertIn('0.045', sec['limitations'][0])
        self.assertAlmostEqual(sec['operating']['limiting_shear_stress_over_mean_pressure'],
                               0.03, places=12)


class LoadSharingClosureSectionTests(unittest.TestCase):
    """SPEC18 package 6: the load-sharing closure behind tribology.friction_closure.model."""

    CLOSURE = {'mu_b': 0.09, 'mu_v': 0.008, 'lambda0': 1.0, 'model': 'load_sharing_curve',
               'contact_friction': 0.06}

    def _case(self, closure, override=True, computed=False):
        c = v2(override=override, **LONG)
        c['tribology'] = copy.deepcopy(TRIBOLOGY)
        c['tribology']['friction_closure'] = copy.deepcopy(closure)
        c['tribology']['use_computed_friction'] = computed
        return c

    def test_rows_carry_the_closure_and_nothing_else_moves(self):
        plain = diagnose(self._case(None))
        load = diagnose(self._case(self.CLOSURE))
        f = load['process']['friction']
        self.assertEqual(f['status'],
                         'UNVALIDATED_LOAD_SHARING_ON_A_PUBLISHED_CONTACT_RATIO_CURVE')
        for flag in ('REDUCED_LOAD_SHARING_CLOSURE_NO_INLET_ANALYSIS',
                     'CONTACT_FRICTION_IS_AN_ENTERED_VALUE',
                     'CONTACT_RATIO_CURVE_OF_ONE_PUBLISHED_FOIL_PASS'):
            self.assertIn(flag, f['flags'])
        self.assertIn('read the change with speed, not the level', f['note'])
        op = f['operating']
        for key in ('contact_area_ratio', 'contact_friction', 'valley_friction',
                    'valley_model', 'dmu_dlambda', 'closure_flags'):
            self.assertIn(key, op)
        self.assertEqual(op['contact_friction'], 0.06)
        self.assertNotIn('contact_area_ratio', plain['process']['friction']['operating'])
        self.assertEqual(load['bite'], plain['bite'])
        self.assertEqual([(h['id'], h['score'], h['standing']) for h in load['hypotheses']],
                         [(h['id'], h['score'], h['standing']) for h in plain['hypotheses']])
        sc = load['chatter']['speed_consistent']
        self.assertTrue(sc.get('friction_closure') == 'load_sharing_curve'
                        or sc.get('status') in ('FAILED', 'NOT_SUPPLIED'))
        self.assertTrue(any('not a property of other surfaces' in x for x in f['limitations']))

    def test_fixed_point_converges_with_the_new_closure(self):
        r = diagnose(self._case(self.CLOSURE, override=False, computed=True))
        op = r['process']['friction']['operating']
        self.assertTrue(op['converged'])
        self.assertEqual(op['bite_source'], 'derived_slab_hitchcock')
        self.assertIn('contact_area_ratio', op)

    def test_contact_friction_is_required(self):
        closure = dict(self.CLOSURE)
        del closure['contact_friction']
        with self.assertRaisesRegex(ValueError, 'contact_friction is required for the '
                                                'load_sharing_curve model.*supply the friction'):
            validate_case(self._case(closure))
        v = validate_case(self._case({'mu_b': 0.09, 'mu_v': 0.008, 'lambda0': 1.0}))
        self.assertEqual(v['tribology']['friction_closure'],
                         {'mu_b': 0.09, 'mu_v': 0.008, 'lambda0': 1.0,
                          'model': 'placeholder_exponential', 'contact_friction': None,
                          'contact_ratio_curve': None, 'valley_film_curve': None,
                          'valley_model': 'constant'})
        bad = dict(self.CLOSURE, contact_ratio_curve=[{'film_ratio': 0.1, 'contact_ratio': 0.5},
                                                      {'film_ratio': 0.2,
                                                       'contact_ratio': 0.6}])
        with self.assertRaisesRegex(ValueError, 'contact_ratio_curve'):
            validate_case(self._case(bad))


if __name__ == '__main__':
    unittest.main()
