"""Lengthwise-band diagnosis (case schema v2): planted truths, process sections, robustness.

Numerics are deliberately coarse to keep the module fast: cells 64, thermal cells 20 mm,
6 radial cells, 5 s time steps, and most planted cases use a SUPPLIED bite response (derived
once with cells 64) so that the lever table does not re-derive bites. The planted observations
are generated from the model inputs (nozzle, event, ridge, two-tone and trough positions).
"""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from physicroll import strip_shape as ss
from physicroll.band_diagnosis import (CASE_SCHEMA_V2, HYPOTHESIS_FAMILIES, HYPOTHESIS_IDS,
                                       diagnose, load_case, result_json, validate_case)
from physicroll.band_report import render_band_report
from physicroll.chatter import BitePass, derive_bite_response
from physicroll.roll_thermal import SprayHeader

ROOT = Path(__file__).resolve().parents[1]
SCEN = ROOT / 'scenarios'
COARSE = {'axial_cell_m': 0.02, 'radial_cells': 6, 'time_step_s': 5.0}
HEADER = {'nozzle_pitch_m': 0.052, 'standoff_m': 0.2, 'spray_angle_rad': 0.8,
          'offset_angle_rad': 0.17, 'spray_mean_htc_w_m2k': 3000.0,
          'background_htc_w_m2k': 50.0}
NOZZLES = SprayHeader(**HEADER).nozzle_positions(1.7)
V2_NULL_OBS = {
    'orientation': None, 'pitch_observations': [], 'faces': None,
    'gauge_variation_detected': None, 'gauge_variation_amplitude_m': None, 'first_seen': None,
    'disappears_after_work_roll_change': None, 'disappears_after_backup_roll_change': None,
    'onset_above_exit_speed_m_s': None, 'worse_at_thinner_gauge': None,
    'band_positions_across_width_m': [], 'measured_vibration_hz': None,
    'lengthwise_continuity': None, 'intermittent_duration_s': None, 'band_width_m': None,
    'band_spacing_m': None, 'positions_repeat_across_coils': None,
    'positions_change_after_work_roll_change': None, 'changes_with_coolant_zone_switching': None,
    'appearance': None, 'visible_only_after_tension_release': None,
    'worse_toward_outer_wraps': None, 'changes_with_tension': None,
    'follows_previous_strip_edges': None, 'worse_at_higher_speed': None}
TRIBOLOGY = {
    'lubricant': {'viscosity_ref_pa_s': 1.8e-3, 'reference_temperature_k': 313.15,
                  'temperature_viscosity_coefficient_per_k': 0.015,
                  'pressure_viscosity_coefficient_per_pa': 1.2e-8},
    'surface_finish': {'roll_roughness_rq_m': 2.5e-7, 'strip_roughness_rq_m': 3e-7},
    'friction_closure': None, 'inlet_temperature_k': 318.15, 'strip_entry_temperature_k': 313.15,
    'strip_heat_fraction': 0.84, 'temperature_limit_k': None, 'thermal_correction': False,
    'use_computed_friction': False}
HARDENING = {'law': 'voce', 'provenance': 'unit test synthetic Voce law',
             'initial_stress_pa': 1.0e8, 'saturation_stress_pa': 2.6e8,
             'characteristic_strain': 0.6, 'stage_iv_slope_pa': 1.0e7,
             'prior_equivalent_strain': 0.0, 'reference_thickness_m': 2.2e-3,
             'use_computed_flow_stress': False}
_BITE = {}


def _override():
    if 'b' not in _BITE:
        b = derive_bite_response(BitePass(0.6e-3, 0.42e-3, 1.5, 0.2, 250e6, 0.05, 25e6, 30e6),
                                 cells=64).to_dict()
        _BITE['b'] = {k: b[k] for k in b if k not in ('source', 'flags', 'strip_modulus_n_m')}
    return dict(_BITE['b'])


def width_model(**kw):
    w = {'roll': {'barrel_length_m': 1.7, 'conductivity_w_mk': 40.0, 'density_kg_m3': 7850.0,
                  'specific_heat_j_kgk': 470.0, 'expansion_coefficient_per_k': 1.17e-5,
                  'poisson_ratio': 0.3, 'expansion_constraint': 'axially_free'},
         'spray_header': dict(HEADER), 'coolant_temperature_k': 318.15,
         'roll_heat_fraction_per_roll': 0.08, 'numerics': dict(COARSE)}
    w.update(kw)
    return w


def v2(override=True, **observation):
    """0.6 -> 0.42 mm pass on the phase-1 demo mill, schema v2, every observation null."""
    obs = dict(V2_NULL_OBS)
    obs.update(observation)
    return {
        'case_schema': CASE_SCHEMA_V2, 'name': 'unit v2', 'synthetic': True,
        'provenance': 'unit test synthetic case',
        'pass': {'entry_thickness_m': 0.6e-3, 'exit_thickness_m': 0.42e-3, 'width_m': 1.5,
                 'work_roll_radius_m': 0.2, 'mean_flow_stress_pa': 250e6,
                 'friction_coefficient': 0.05, 'entry_tension_pa': 25e6,
                 'exit_tension_pa': 30e6, 'exit_speed_m_s': 10.0},
        'material': {'alloy': 'AA3104', 'temper': 'H19', 'yield_stress_pa': 285e6,
                     'youngs_modulus_pa': 70e9, 'luders_strain': None,
                     'magnesium_wt_pct': 1.1, 'grain_size_m': None},
        'stand': {'work_roll_mass_kg': 3000.0, 'backup_roll_mass_kg': 22000.0,
                  'work_backup_contact_stiffness_n_m': 4e10, 'housing_stiffness_n_m': 1.4e10,
                  'modal_damping_ratio': 0.03, 'roll_youngs_modulus_pa': 210e9,
                  'roll_poisson_ratio': 0.3},
        'spans': {'strip_youngs_modulus_pa': 70e9, 'entry_span_length_m': 4.0,
                  'exit_span_length_m': 4.0},
        'kinematics': {'backup_roll_diameter_m': 1.15, 'gear_meshes': [], 'bearings': [],
                       'grinder_marks': [], 'deflector_roll_diameters_m': [],
                       'entry_coil_diameter_m': None, 'exit_coil_diameter_m': None},
        'lubrication': None, 'coolant': None,
        'model_options': {'bite_damping_transit_fraction': 0.5, 'max_radius_ratio': 1.5,
                          'cells': 64, 'bite_response_override': _override() if override
                          else None},
        'observation': obs}


LONG = dict(orientation='longitudinal')


def _h(result):
    return {h['id']: h for h in result['hypotheses']}


class LengthwisePlantedTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = {}
        # 1 blocked nozzle -> continuous loose band at the nozzle
        c = v2(**LONG, band_positions_across_width_m=[NOZZLES[12]],
               lengthwise_continuity='continuous', positions_repeat_across_coils=True,
               positions_change_after_work_roll_change=False, appearance='loose_or_buckle',
               worse_at_thinner_gauge=True)
        c['width_model'] = width_model(blocked_nozzle_indices=[12])
        cls.nozzle_case = c
        cls.r['nozzle'] = diagnose(c)
        # 2 zone switching -> intermittent band at the event nozzle
        c = v2(**LONG, band_positions_across_width_m=[NOZZLES[20]],
               lengthwise_continuity='intermittent', changes_with_coolant_zone_switching=True,
               positions_repeat_across_coils=False, appearance='loose_or_buckle',
               worse_at_thinner_gauge=True)
        c['width_model'] = width_model(events=[{'start_s': 0.0, 'duration_s': 90.0,
                                                'nozzle_indices': [20, 21], 'level': 0.0}])
        cls.r['zone'] = diagnose(c)
        # 3 roll-surface two-tone step at the edges of an earlier 1.2 m strip
        c = v2(**LONG, band_positions_across_width_m=[0.25, 1.45],
               positions_change_after_work_roll_change=True, follows_previous_strip_edges=True,
               positions_repeat_across_coils=True, lengthwise_continuity='continuous',
               appearance='gloss_or_shade', faces='one')
        c['width_model'] = width_model(previous_strip_widths_m=[1.2])
        cls.r['two_tone'] = diagnose(c)
        # 4 grinding feed marks: 8 mm feed pitch, regular 8 mm spacing
        pos = [0.80 + 0.008 * i for i in range(5)]
        c = v2(**LONG, band_positions_across_width_m=pos,
               positions_change_after_work_roll_change=True, appearance='gloss_or_shade',
               lengthwise_continuity='continuous')
        c['width_model'] = width_model(grinding={'traverse_speed_m_s': 0.004,
                                                 'roll_rotation_hz': 0.5})
        cls.r['grinding'] = diagnose(c)
        # 5 incoming ridge that yields the strip in the coil
        c = v2(**LONG, band_positions_across_width_m=[1.2], positions_repeat_across_coils=False,
               worse_toward_outer_wraps=True, lengthwise_continuity='both',
               visible_only_after_tension_release=True, worse_at_thinner_gauge=True)
        c['width_model'] = width_model(
            incoming_ridges=[{'position_m': 1.2, 'height_m': 10e-6, 'width_m': 0.03}],
            coil={'inner_radius_m': 0.3, 'outer_radius_m': 0.9, 'winding_tension_pa': 20e6,
                  'compaction_factor': 0.5})
        cls.r['ridge'] = diagnose(c)
        # 6 tension troughs: spacing = model trough wavelength of the exit span
        lam = ss.tension_wrinkle_wavelength_m(0.42e-3, 4.0, 30e6, 70e9)
        cls.trough_wavelength = lam
        c = v2(**LONG, band_spacing_m=lam, appearance='crease_or_flute',
               changes_with_tension=True, lengthwise_continuity='intermittent',
               worse_at_thinner_gauge=True)
        c['width_model'] = width_model(lateral_compressive_stress_pa=5e6,
                                       deflector_roll_radius_m=0.15)
        cls.r['troughs'] = diagnose(c)
        # 7 profile / flatness mismatch: crowns outside the dead band, bands at the edges
        c = v2(**LONG, band_positions_across_width_m=[0.15, 1.55], band_width_m=0.2,
               appearance='loose_or_buckle', visible_only_after_tension_release=True,
               worse_at_thinner_gauge=True)
        c['width_model'] = width_model(gap_crown_m=40e-6, entry_crown_m=3e-6,
                                       heredity_coefficient=0.3)
        cls.r['profile'] = diagnose(c)
        # 8 heat streak: gloss bands that wander, worse at speed, boundary-regime tribology
        c = v2(**LONG, appearance='gloss_or_shade', gauge_variation_detected=False,
               positions_repeat_across_coils=False, lengthwise_continuity='intermittent',
               worse_at_higher_speed=True)
        c['tribology'] = dict(TRIBOLOGY)
        cls.r['heat'] = diagnose(c)
        # 9 stain
        c = v2(**LONG, appearance='stain', faces='one', lengthwise_continuity='intermittent',
               positions_repeat_across_coils=True, changes_with_tension=False)
        cls.r['stain'] = diagnose(c)

    def _leads(self, key, hid):
        r = self.r[key]
        self.assertEqual(r['leading_hypotheses'][:1], [hid],
                         [(h['id'], h['score'], h['standing']) for h in r['hypotheses'][:4]])
        self.assertEqual(r['family_summary']['leading_family'], 'lengthwise')
        self.assertEqual(r['family_summary']['observed_family'], 'lengthwise')

    def test_blocked_nozzle_stripe_leads(self):
        self._leads('nozzle', 'nozzle_thermal_stripe')
        st = self.r['nozzle']['width']['thermal_steady']
        hot = [s for s in st['stripes'] if s['sign'] == 'HOT_HIGH']
        self.assertEqual(len(hot), 1)
        self.assertLess(abs(hot[0]['peak_position_m'] - NOZZLES[12]), 0.0131)
        self.assertGreater(hot[0]['peak_deviation_m'], 1e-6)
        # thermal crown from the healthy header lands in the reported 2-16 um range
        self.assertTrue(2e-6 < st['healthy_thermal_crown_m'] < 16e-6)

    def test_zone_switching_leads(self):
        self._leads('zone', 'cooling_zone_switching_transient')
        ev = self.r['zone']['width']['thermal_events']['events'][0]
        self.assertGreater(ev['peak_deviation_m'], 0)
        # initial growth rate: analytic 2*alpha*dq/(rho*c) vs simulated within 40 %
        self.assertLess(abs(ev['simulated_initial_growth_rate_m_s']
                            / ev['analytic_initial_growth_rate_m_s'] - 1), 0.4)
        self.assertEqual(ev['peak_state_with_feedback'], 'MANIFEST_BUCKLE')
        self.assertEqual(ev['band_life_basis'], 'manifest')
        self.assertGreater(ev['band_life_s'], ev['duration_s'])
        self.assertLess(ev['time_to_manifest_threshold_s'], ev['duration_s'])
        self.assertAlmostEqual(ev['time_above_manifest_threshold_s'],
                               ev['band_life_s'] - ev['time_to_manifest_threshold_s'])

    def test_roll_surface_two_tone_leads(self):
        self._leads('two_tone', 'roll_surface_band')
        self.assertEqual(self.r['two_tone']['width']['two_tone']['band_positions_m'],
                         [0.25, 1.45])

    def test_grinding_feed_marks_lead(self):
        self._leads('grinding', 'grinding_feed_marks')
        self.assertAlmostEqual(self.r['grinding']['width']['grinding_feed_pitch_m'], 0.008)

    def test_incoming_ridge_buildup_leads(self):
        self._leads('ridge', 'incoming_ridge_coil_buildup')
        ridge = self.r['ridge']['width']['shape']['ridges'][0]
        self.assertEqual(ridge['coil']['status'], 'RIDGE_YIELDS_STRIP')
        self.assertTrue(0 < ridge['exit_to_entry_ridge_ratio'] < 1)

    def test_tension_troughs_lead(self):
        self._leads('troughs', 'tension_troughs_or_creases')
        tr = self.r['troughs']['width']['troughs']['exit_span']
        self.assertEqual(tr['status'], 'TROUGHS_EXPECTED')
        self.assertAlmostEqual(tr['wrinkle_wavelength_m'], self.trough_wavelength)

    def test_profile_mismatch_leads(self):
        self._leads('profile', 'profile_flatness_mismatch')
        crown = self.r['profile']['width']['shape']['crown']
        self.assertNotEqual(crown['classification']['status'], 'WITHIN_DEAD_BAND')
        self.assertAlmostEqual(crown['gap_crown_used_m'],
                               40e-6 - 2 * crown['healthy_thermal_crown_m'])

    def test_heat_streak_leads(self):
        self._leads('heat', 'heat_streak_or_film_variation')
        self.assertEqual(self.r['heat']['process']['friction']['operating']['regime'],
                         'BOUNDARY')

    def test_stain_leads(self):
        self._leads('stain', 'oil_carryover_drips_or_stain')

    # ------------------------------------------------------------------ width physics
    def test_shape_chain_three_levels_and_feedback_always_on(self):
        w = self.r['nozzle']['width']
        self.assertEqual(w['inputs_used']['exit_tension_feedback'], 'always applied (SPEC6 6.7)')
        self.assertGreater(w['inputs_used']['exit_tension_force_sensitivity_per_width_m'], 0)
        steady = w['shape']['steady']
        self.assertGreater(steady['rigid_transfer_bound_i_units'],
                           steady['compliance_only_peak_i_units'])
        self.assertGreater(steady['compliance_only_peak_i_units'],
                           steady['linear_feedback_peak_i_units'])
        row = w['shape']['steady_stripe_table'][0]
        for level in ('rigid', 'compliance_only', 'with_feedback'):
            self.assertIn(row[level]['state'], ('LATENT_UNDER_TENSION', 'MANIFEST_BUCKLE'))
        self.assertIsNotNone(row['manifest_onset_peak_height_m'])
        # stripes come from the difference to a healthy header: a healthy header has none
        c = copy.deepcopy(self.nozzle_case)
        c['width_model']['blocked_nozzle_indices'] = []
        healthy = diagnose(c)['width']['thermal_steady']
        self.assertEqual(healthy['stripes'], [])
        self.assertTrue(all(v == 0.0 for v in healthy['local_deviation_m']))
        self.assertGreater(healthy['nozzle_pattern_ripple']['peak_to_peak_m'], 0)

    def test_gauge_trend_thin_gauge(self):
        c = copy.deepcopy(self.nozzle_case)
        c['model_options']['bite_response_override'] = None
        c['schedule'] = [
            {'label': 'A 2.2->1.4', 'entry_thickness_m': 2.2e-3, 'exit_thickness_m': 1.4e-3,
             'mean_flow_stress_pa': 190e6, 'friction_coefficient': 0.08,
             'entry_tension_pa': 15e6, 'exit_tension_pa': 20e6, 'exit_speed_m_s': 3.0},
            {'label': 'B 0.6->0.42', 'entry_thickness_m': 0.6e-3, 'exit_thickness_m': 0.42e-3,
             'mean_flow_stress_pa': 250e6, 'friction_coefficient': 0.05,
             'entry_tension_pa': 25e6, 'exit_tension_pa': 30e6, 'exit_speed_m_s': 10.0}]
        gt = diagnose(c)['width']['gauge_trend']
        a, b = gt['rows']
        self.assertGreater(a['band_buckling_stress_pa'], b['band_buckling_stress_pa'])
        self.assertGreater(a['shohet_townsend_half_width_i_units'],
                           b['shohet_townsend_half_width_i_units'])
        self.assertGreater(a['manifest_onset_height_50mm_reference_m'],
                           2 * b['manifest_onset_height_50mm_reference_m'])
        self.assertGreater(a['trough_critical_lateral_stress_pa'],
                           -1e9)
        self.assertLess(abs(a['trough_critical_lateral_stress_pa']),
                        abs(b['trough_critical_lateral_stress_pa']) * 10)
        self.assertIn('I-units', gt['text'])

    def test_rule_details(self):
        h = _h(self.r['nozzle'])['nozzle_thermal_stripe']
        pos = next(e for e in h['evidence'] if e['criterion'].startswith('band positions'))
        self.assertEqual((pos['verdict'], pos['weight']), ('SUPPORTS', 'strong'))
        orient = next(e for e in h['evidence'] if e['criterion'] == 'orientation')
        self.assertEqual((orient['verdict'], orient['weight']), ('SUPPORTS', 'moderate'))
        # any other observed orientation contradicts every lengthwise hypothesis strongly
        c = copy.deepcopy(self.nozzle_case)
        c['observation']['orientation'] = 'transverse'
        r = diagnose(c)
        for hid, fam in HYPOTHESIS_FAMILIES.items():
            if fam == 'lengthwise':
                self.assertEqual(_h(r)[hid]['standing'], 'CONTRADICTED', hid)


class LengthwiseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = v2(override=False, **LONG)
        c['tribology'] = dict(TRIBOLOGY, use_computed_friction=True)
        c['hardening'] = dict(HARDENING, use_computed_flow_stress=True)
        c['gauge_control'] = {'compensation_gain': 0.9, 'bandwidth_hz': 25.0,
                              'force_filter_hz': None}
        c['drive'] = {'inertias_kg_m2': [600.0, 120.0, 90.0],
                      'stiffnesses_n_m_rad': [4.0e6, 1.5e6]}
        c['incoming_variation'] = {'flow_stress_variation_fraction': 0.02,
                                   'coil_synchronous': True}
        c['kinematics']['entry_coil_diameter_m'] = 1.2
        c['pass']['exit_speed_m_s'] = 6.0
        cls.full_case = c
        cls.full = diagnose(c)
        p = v2(**LONG)
        p['tribology'] = dict(TRIBOLOGY)
        p['hardening'] = dict(HARDENING)
        cls.plain = diagnose(p)

    def test_computed_values_replace_only_when_flagged(self):
        plain, full = self.plain, self.full
        self.assertNotIn('effective_inputs', plain)
        fr = plain['process']['friction']['operating']
        self.assertNotAlmostEqual(fr['computed_friction_coefficient'], 0.05, places=3)
        self.assertEqual(fr['used_friction_coefficient'], 0.05)
        fs = plain['process']['flow_stress']['passes'][0]
        self.assertEqual(fs['used_mean_flow_stress_pa'], 250e6)
        self.assertNotIn('FRICTION_FROM_PLACEHOLDER_CLOSURE', plain['flags'])
        self.assertNotIn('FLOW_STRESS_FROM_HARDENING_LAW', plain['flags'])
        eff = full['effective_inputs']['pass']
        op = full['process']['friction']['operating']
        self.assertEqual(eff['friction_coefficient'], op['computed_friction_coefficient'])
        self.assertEqual(eff['mean_flow_stress_pa'],
                         full['process']['flow_stress']['passes'][0][
                             'computed_mean_flow_stress_pa'])
        self.assertIn('FRICTION_FROM_PLACEHOLDER_CLOSURE', full['flags'])
        self.assertIn('FLOW_STRESS_FROM_HARDENING_LAW', full['flags'])
        self.assertEqual(full['inputs']['pass']['friction_coefficient'], 0.05)
        self.assertLessEqual(len(op['iterations']), 6)
        self.assertTrue(op['converged'])
        curve = full['process']['friction_speed_curve']
        mus = [q['friction_coefficient'] for q in curve['points']]
        self.assertEqual(mus, sorted(mus, reverse=True))
        self.assertLess(curve['mean_slope_per_m_s'], 0)
        heat = full['process']['heating']['operating']
        self.assertGreater(heat['friction_power_per_width_w_m'], 0)
        self.assertAlmostEqual(heat['bite_heat_per_width_w_m'],
                               heat['plastic_power_per_width_w_m']
                               + heat['friction_power_per_width_w_m'])

    def test_speed_consistent_critical_speed_below_fixed_friction(self):
        sc = self.full['chatter']['speed_consistent']
        fixed = sc['fixed_friction_critical_exit_speed_m_s']
        self.assertGreater(fixed, self.full['inputs']['pass']['exit_speed_m_s'])
        self.assertEqual(sc['status'], 'CROSSING_FOUND')
        self.assertLess(sc['speed_consistent_critical_exit_speed_m_s'], fixed)
        u = sc['speed_consistent_critical_exit_speed_m_s']
        self.assertGreater(u, self.full['inputs']['pass']['exit_speed_m_s'])

    def test_gauge_control_static_amplification(self):
        g = self.full['gauge_control']
        m, q = g['mill_modulus_n_m'], g['strip_modulus_n_m']
        self.assertAlmostEqual(g['eccentricity_amplification_vs_no_agc'],
                               (m + q) / (m + 0.1 * q))
        self.assertAlmostEqual(g['runout']['analytic_static_with_agc_tension_off'],
                               -2 * m / (m + 0.1 * q))
        self.assertIsNotNone(g['chatter_with_loop']['with_25_hz_force_filter'])
        self.assertIn('AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF', self.full['flags'])
        self.assertIn('tension coupling OFF', g['static_formulas_label'])
        self.assertEqual(len(g['runout']['responses']), 4)
        shift = g['speed_change_gauge_shift']
        self.assertLess(shift['delta_friction'], 0)
        self.assertLess(abs(shift['exit_thickness_change_m']),
                        abs(shift['exit_thickness_change_without_agc_m']))

    def test_drive_and_incoming_sections(self):
        d = self.full['drive']
        modes = [m['frequency_hz'] for m in d['catalogue_modes']]
        self.assertEqual(len(modes), 2)
        cat = {e['id'] for e in self.full['signatures']['catalogue']}
        self.assertIn('structural_mode:torsional_1', cat)
        self.assertEqual(len(d['roll_speed_ripple']['responses']), 2)
        tors = _h(self.full)['torsional_or_low_frequency_drive_vibration']
        self.assertIn('torsional_modes_hz', tors['model_prediction'])
        iv = self.full['incoming_variation']
        self.assertLess(abs(iv['static']['exit_thickness_change_m']),
                        abs(iv['static']['exit_thickness_change_without_agc_m']))
        self.assertEqual(len(iv['coil_synchronous']['harmonics']), 3)

    def test_bite_model_auto_falls_back_to_mattress(self):
        c = v2(override=False, **LONG)
        c['pass'].update(entry_thickness_m=0.30e-3, exit_thickness_m=0.21e-3,
                         mean_flow_stress_pa=270e6, friction_coefficient=0.05)
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertIsNotNone(r['bite'])
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['flags'])
        self.assertIn('max_radius_ratio', r['bite_fallback_reason'])
        self.assertIn(r['chatter']['reliability'], ('WITHIN_SPAN_WAVE_LIMIT',
                                                    'NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT'))
        c['model_options']['bite_model'] = 'hitchcock'
        self.assertIsNone(diagnose(c)['bite'])

    def test_missing_sections_not_supplied_and_v1_unchanged(self):
        r = diagnose(v2(**LONG))
        for key in ('process', 'gauge_control', 'drive', 'incoming_variation', 'width'):
            self.assertEqual(r[key]['status'], 'NOT_SUPPLIED', key)
            self.assertTrue(r[key]['not_supplied'])
        self.assertEqual(len(r['hypotheses']), len(HYPOTHESIS_IDS))
        v1 = load_case(SCEN / 'band_diagnosis_bearing_order.json')
        self.assertEqual(validate_case(v1), v1)          # a validated v1 case round-trips
        self.assertIsNone(v1['width_model'])
        bad = dict(v1, width_model={'roll': {}})
        with self.assertRaisesRegex(ValueError, 'band_case.v2'):
            validate_case(bad)

    def test_validation_v2(self):
        c = v2(**LONG)
        c['observation']['appearance'] = 'sparkly'
        with self.assertRaisesRegex(ValueError, 'appearance'):
            validate_case(c)
        c = v2(**LONG)
        del c['observation']['band_width_m']
        with self.assertRaisesRegex(ValueError, 'missing keys'):
            validate_case(c)
        c = v2(**LONG)
        c['width_model'] = width_model(blocked_nozzle_indices=[99])
        with self.assertRaisesRegex(ValueError, 'out of range'):
            validate_case(c)
        c = v2(**LONG)
        c['width_model'] = width_model(roll_heat_fraction_per_roll=None)
        with self.assertRaisesRegex(ValueError, 'roll_heat_fraction_per_roll'):
            validate_case(c)
        c = v2(**LONG)
        c['tribology'] = dict(TRIBOLOGY, unexpected=1)
        with self.assertRaisesRegex(ValueError, 'unknown keys'):
            validate_case(c)
        c = v2(**LONG)
        c['model_options']['bite_model'] = 'magic'
        with self.assertRaisesRegex(ValueError, 'bite_model'):
            validate_case(c)

    def test_determinism_json_report_and_cli(self):
        c = v2(**LONG, band_positions_across_width_m=[NOZZLES[12]])
        c['width_model'] = width_model(blocked_nozzle_indices=[12], events=[
            {'start_s': 0.0, 'duration_s': 30.0, 'nozzle_indices': [20], 'level': 0.0}])
        a, b = diagnose(c), diagnose(copy.deepcopy(c))
        self.assertEqual(result_json(a), result_json(b))
        for r in (a, self.full, self.plain):
            json.dumps(r, allow_nan=False)
        c['name'] = '<script>alert(1)</script>'
        html = render_band_report(diagnose(c))
        self.assertNotIn('<script>', html)
        self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', html, re.IGNORECASE))
        self.assertIn('Hypotheses', html)
        html = render_band_report(self.full)
        self.assertIsNone(re.search(r'\b(nan|inf|infinity)\b', html, re.IGNORECASE))
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.json'
            c['name'] = 'unit v2 cli'
            case.write_text(json.dumps(c))
            out = Path(tmp) / 'out'
            proc = subprocess.run([sys.executable, '-m', 'physicroll.band_cli', str(case),
                                   '--out', str(out)], cwd=ROOT, capture_output=True, text=True,
                                  timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((out / 'unit-v2-cli.result.json').is_file())
            self.assertTrue((out / 'unit-v2-cli.report.html').is_file())

    def test_scenarios_load(self):
        names = ('band_diagnosis_template.json', 'band_diagnosis_thin_gauge_chatter.json',
                 'band_diagnosis_bearing_order.json', 'band_diagnosis_lengthwise_bands.json')
        for name in names:
            load_case(SCEN / name)
        t = load_case(SCEN / 'band_diagnosis_template.json')
        self.assertEqual(t['case_schema'], CASE_SCHEMA_V2)
        self.assertTrue(all(v in (None, []) for v in t['observation'].values()))
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        self.assertIn('GENERATED FROM THE MODEL', demo['provenance'])
        # SPEC6 6.5 lengthwise demo: coarse cells and thermal numerics, same leading hypothesis
        demo['model_options']['cells'] = 64
        demo['width_model']['numerics'] = dict(COARSE)
        r = diagnose(demo)
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        self.assertEqual(_h(r)['cooling_zone_switching_transient']['standing'], 'CONSISTENT')
        self.assertEqual(r['family_summary']['observed_family'], 'lengthwise')
        self.assertTrue(2e-6 < r['width']['thermal_steady']['healthy_thermal_crown_m'] < 16e-6)
        # (the two phase-1 demos are run in tests.test_band_diagnosis)


if __name__ == '__main__':
    unittest.main()
