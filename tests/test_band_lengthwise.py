"""Lengthwise-band diagnosis (case schema v2): planted truths, process sections, robustness.

Numerics are deliberately coarse to keep the module fast: cells 64, thermal cells 20 mm,
6 radial cells, 5 s time steps, and most planted cases use a SUPPLIED bite response (derived
once with cells 64) so that the lever table does not re-derive bites. The planted observations
are generated from the model inputs (nozzle, event, ridge, two-tone and trough positions).
"""
import copy
from pathlib import Path
import unittest

from physicroll import band_width as bw
from physicroll import strip_shape as ss
from physicroll.band_diagnosis import CASE_SCHEMA_V2, HYPOTHESIS_FAMILIES, diagnose, load_case
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
        # 8 heat streak: gloss bands that wander, worse at speed, tribology supplied
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
        # visible time = time above the in-mill threshold when the band buckles in the mill
        self.assertEqual(ev['visible_time_basis'], 'in_mill_manifest')
        self.assertEqual(ev['visible_time_s'], ev['time_above_manifest_threshold_s'])
        self.assertLess(ev['visible_time_s'], ev['band_life_s'])
        # released threshold: below the in-mill one (tension no longer stabilises the band)
        self.assertLess(ev['released_threshold_m'], ev['manifest_threshold_m'])
        self.assertLessEqual(ev['time_to_released_threshold_s'],
                             ev['time_to_manifest_threshold_s'])
        self.assertIn(ev['peak_state_after_tension_release'],
                      ('MANIFEST_AFTER_TENSION_RELEASE', 'FLAT_AFTER_TENSION_RELEASE'))
        self.assertEqual(ev['label'], 'event 0')
        self.assertEqual(self.r['zone']['width']['barrel_length_m'], 1.7)
        lw = _h(self.r['zone'])['cooling_zone_switching_transient']['evidence']
        self.assertTrue(any(e['criterion'] == 'intermittent duration vs model visible time'
                            for e in lw))

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
                         'MIXED_SUBSTANTIAL_CONTACT')

    def test_heat_streak_regime_item(self):
        """SPEC17 BT-G8: the film-ratio label no longer supports the heat-streak hypothesis;
        only an exit temperature above the supplied limit does (weak)."""
        crit = 'tribology regime / exit strip temperature at the operating point'

        def item(result):
            h = _h(result)['heat_streak_or_film_variation']
            return next(e for e in h['evidence'] if e['criterion'] == crit)

        e = item(self.r['heat'])                        # tribology, no temperature limit
        self.assertEqual(e['verdict'], 'NEUTRAL')
        self.assertEqual(e['basis'], 'model')
        self.assertIn('no longer counts', e['expected'])
        self.assertIn('MIXED_SUBSTANTIAL_CONTACT', e['observed'])
        exit_k = self.r['heat']['process']['heating']['operating']['exit_temperature_k']
        c = v2(**LONG, appearance='gloss_or_shade', gauge_variation_detected=False,
               positions_repeat_across_coils=False, lengthwise_continuity='intermittent',
               worse_at_higher_speed=True)
        c['tribology'] = dict(TRIBOLOGY, temperature_limit_k=exit_k - 1.0)
        hot = diagnose(c)
        e = item(hot)
        self.assertEqual((e['verdict'], e['weight'], e['basis']), ('SUPPORTS', 'weak', 'model'))
        self.assertIn('exit temperature above limit: True', e['observed'])
        self.assertEqual(hot['leading_hypotheses'][:1], ['heat_streak_or_film_variation'])

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
            self.assertIn(row[level]['state_after_tension_release'],
                          ('MANIFEST_AFTER_TENSION_RELEASE', 'FLAT_AFTER_TENSION_RELEASE'))
            self.assertGreaterEqual(row[level]['released_buckling_utilisation'], 0)
            self.assertEqual(row[level]['state'] == 'MANIFEST_BUCKLE',
                             row[level]['buckling_utilisation'] >= 1)
        self.assertIsNotNone(row['manifest_onset_peak_height_m'])
        self.assertLess(row['released_onset_peak_height_m'], row['manifest_onset_peak_height_m'])
        band = steady['levels']['with_feedback']['bands'][0]
        for key in ('buckling_utilisation', 'effective_buckling_width_m',
                    'state_after_tension_release', 'released_buckling_utilisation',
                    'released_global_buckling_utilisation', 'net_compression_peak_pa'):
            self.assertIn(key, band)
        # the linear-feedback profile is the plotting profile: equal to the reported one
        # unless a band is saturated, and then smaller at that band's peak
        lin, fb = steady['i_units_linear_feedback'], steady['i_units_with_feedback']
        self.assertEqual(len(lin), len(fb))
        if steady['levels']['with_feedback']['saturated_bands']:
            self.assertLess(max(lin), max(fb))
        else:
            self.assertEqual(lin, fb)
        self.assertAlmostEqual(max(map(abs, lin)), steady['linear_feedback_peak_i_units'],
                               delta=1e-6 * max(map(abs, lin)))
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
        # smooth Gaussian reference: the after-release onset carries the gauge trend; the
        # in-mill onset falls less (the residual must first exceed the tension)
        self.assertGreater(a['released_onset_height_reference_m'],
                           2 * b['released_onset_height_reference_m'])
        self.assertGreaterEqual(a['manifest_onset_height_reference_m'],
                                b['manifest_onset_height_reference_m'])
        for row in (a, b):
            self.assertLess(row['released_onset_height_reference_m'],
                            row['manifest_onset_height_reference_m'])
            self.assertGreaterEqual(row['released_onset_stripe_height_m'],
                                    row['reporting_onset_stripe_height_m'] * 0.99)
            for key in ('state_after_tension_release', 'buckling_utilisation',
                        'released_buckling_utilisation', 'released_onset_stripe_height_m'):
                self.assertIn(key, row)
            self.assertFalse(any('50mm' in k for k in row))
        self.assertIn('Gaussian', gt['reference_stripe_description'])
        self.assertIn('after release', gt['text'])
        self.assertGreater(a['trough_critical_lateral_stress_pa'],
                           -1e9)
        self.assertLess(abs(a['trough_critical_lateral_stress_pa']),
                        abs(b['trough_critical_lateral_stress_pa']) * 10)
        self.assertIn('I-units', gt['text'])

    def test_tension_release_rules(self):
        class F:
            obs = {'visible_only_after_tension_release': None, 'appearance': None}
        f = F()
        latent_rel = [('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE')]
        manifest = [('MANIFEST_BUCKLE', 'MANIFEST_AFTER_TENSION_RELEASE')]
        latent_flat = [('LATENT_UNDER_TENSION', 'FLAT_AFTER_TENSION_RELEASE')]
        cases = [(True, latent_rel, ('SUPPORTS', 'moderate')),
                 (True, manifest, ('CONTRADICTS', 'weak')),
                 (False, manifest, ('SUPPORTS', 'moderate')),
                 (False, latent_rel, ('CONTRADICTS', 'weak')),
                 (False, latent_flat, ('CONTRADICTS', 'weak')),
                 (True, latent_flat, ('NEUTRAL', None)),
                 (None, manifest, ('NOT_OBSERVED', None))]
        for v, states, want in cases:
            f.obs = {'visible_only_after_tension_release': v, 'appearance': 'loose_or_buckle'}
            first, second = bw._tension_release_rules(f, states, 'x')
            self.assertEqual((first['verdict'], first['weight']), want, (v, states))
            self.assertEqual(second['verdict'], 'SUPPORTS' if states == manifest else 'NEUTRAL')

    def test_spacing_match_not_comparable_beyond_8_pitches(self):
        m = bw.spacing_match([0.31, 0.426], 0.008)
        self.assertEqual(m['status'], 'NOT_COMPARABLE_GAP_EXCEEDS_8_PITCHES')
        self.assertAlmostEqual(m['min_gap_in_pitches'], 0.31 / 0.008)
        self.assertEqual(bw.spacing_match([0.104, 0.208], 0.052)['status'], 'ALL_GAPS_MATCH')
        sm = self.r['nozzle']['width']['positions']['spacing_matches']
        self.assertEqual(sm, {})          # one observed position: no gaps

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


class EventAttributionTests(unittest.TestCase):
    """Reproducers of code-review findings 3, 4 and 6 (zone-switching event metrics); supplied
    bite heat 1e6 W/m, coarse numerics (5 s time step)."""

    @classmethod
    def setUpClass(cls):
        def run(events):
            c = v2(**LONG)
            c['width_model'] = width_model(bite_heat_per_width_w_m=1e6, events=events)
            return diagnose(c)
        cls.same = run([{'start_s': 0.0, 'duration_s': 5.0, 'nozzle_indices': [12], 'level': 0.0},
                        {'start_s': 100.0, 'duration_s': 90.0, 'nozzle_indices': [12],
                         'level': 0.0}])
        cls.short = run([{'start_s': 0.0, 'duration_s': 2.0, 'nozzle_indices': [16],
                          'level': 0.0}])
        cls.split = run([{'start_s': 0.0, 'duration_s': 30.0, 'nozzle_indices': [6, 26],
                          'level': 0.0}])

    def test_later_event_on_same_nozzle_not_attributed_to_earlier(self):
        # finding 3: the 5 s event reported the 90 s event's peak (at t = 190 s) and a band
        # life of 222 s that included the later event
        first, second = self.same['width']['thermal_events']['events']
        self.assertEqual(first['attribution_window_end_s'], 100.0)
        self.assertLessEqual(first['time_of_peak_s'], 100.0)
        self.assertLess(first['peak_deviation_m'], 0.25 * second['peak_deviation_m'])
        self.assertIn('LATER_EVENT_IN_SAME_REGION', first['flags'])
        # the stripe of the 5 s event is still above the reporting threshold when the second
        # event starts: its life is only bounded, never the combined value
        self.assertIsNone(first['band_life_s'])
        self.assertEqual(first['band_life_lower_bound_s'], 100.0)
        self.assertIn('FADE_BEYOND_ATTRIBUTION_WINDOW', first['flags'])
        self.assertIn('EARLIER_EVENT_IN_SAME_REGION', second['flags'])
        self.assertAlmostEqual(second['time_of_peak_s'], 90.0)
        self.assertGreater(second['band_life_s'], 90.0)
        html = render_band_report(self.same)
        self.assertIn('not attributable after 100 s', html)

    def test_short_event_peak_profile_is_the_measured_peak(self):
        # finding 4: a 2 s outage (shorter than the 5 s snapshot interval) took the snapshot at
        # t = 0 (unchanged state): zero deviation and BELOW_REPORTING_THRESHOLD
        ev = self.short['width']['thermal_events']['events'][0]
        self.assertEqual(ev['time_of_peak_s'], 2.0)
        self.assertEqual(ev['peak_snapshot_time_s'], ev['time_of_peak_s'])
        self.assertGreater(ev['stripe_peak_deviation_m'], 1.5e-7)
        self.assertLess(abs(ev['stripe_peak_position_m'] - NOZZLES[16]), 0.021)
        shape = ev['peak_shape']
        self.assertGreater(shape['feedback_peak_i_units'], shape['reporting_threshold_i_units'])
        self.assertNotEqual(ev['peak_state_with_feedback'], 'BELOW_REPORTING_THRESHOLD')
        self.assertIsNotNone(ev['reporting_threshold_m'])

    def test_separated_nozzles_monitored_per_stripe(self):
        # finding 6: nozzles 6 and 26 were monitored at their mean position (an unaffected
        # region, ~ -3 nm) although both nozzle positions grow ~2.08 um
        ev = self.split['width']['thermal_events']['events'][0]
        stripes = ev['stripes']
        self.assertEqual([s['nozzle_indices'] for s in stripes], [[6], [26]])
        self.assertEqual([s['monitor_position_m'] for s in stripes], [NOZZLES[6], NOZZLES[26]])
        for s in stripes:
            self.assertGreater(s['peak_deviation_m'], 1.9e-6)
        gov = stripes[ev['governing_stripe_index']]
        self.assertTrue(gov['governing'])
        self.assertEqual(ev['monitor_position_m'], gov['monitor_position_m'])
        self.assertEqual(ev['peak_deviation_m'], max(s['peak_deviation_m'] for s in stripes))
        self.assertNotEqual(ev['peak_state_with_feedback'], 'BELOW_REPORTING_THRESHOLD')
        self.assertGreater(ev['reporting_threshold_m'], 0)
        self.assertGreater(ev['band_life_s'], ev['duration_s'])
        html = render_band_report(self.split)
        self.assertIn('stripes (one monitor per group of adjacent nozzles)', html)


class LengthwiseScenarioTests(unittest.TestCase):
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
        # gauge_trend, the schedule sweep and the per-pass friction do not enter the evidence:
        # keep only the final schedule pass (= the case pass) to save time
        demo['schedule'] = demo['schedule'][-1:]
        r = diagnose(demo)
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        self.assertEqual(_h(r)['cooling_zone_switching_transient']['standing'], 'CONSISTENT')
        self.assertEqual(r['family_summary']['observed_family'], 'lengthwise')
        self.assertTrue(2e-6 < r['width']['thermal_steady']['healthy_thermal_crown_m'] < 16e-6)
        # (the two phase-1 demos are run in tests.test_band_diagnosis)


class SprayLayoutTests(unittest.TestCase):
    """band_width.spray_layout: the header and strip as the width section reads them."""

    def assert_matches(self, layout, ts):
        self.assertEqual(layout['nozzle_positions_m'], ts['nozzle_positions_m'])
        self.assertEqual(layout['nozzle_levels'], ts['nozzle_levels'])
        self.assertEqual(layout['effective_footprint_width_m'],
                         ts['effective_footprint_width_m'])
        for k in ('strip_start_m', 'strip_end_m', 'strip_centre_m'):
            self.assertEqual(layout[k], ts[k], k)

    def test_lengthwise_demo_without_blocked_indices(self):
        import json
        r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                        / 'lengthwise-bands-demo.result.json').read_text())
        self.assertEqual(r['inputs']['width_model']['blocked_nozzle_indices'], [])
        self.assert_matches(bw.spray_layout(r['inputs']), r['width']['thermal_steady'])

    def test_lengthwise_demo_with_blocked_indices(self):
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        demo['model_options']['cells'] = 64
        demo['width_model']['numerics'] = dict(COARSE)
        demo['schedule'] = demo['schedule'][-1:]
        demo['width_model']['blocked_nozzle_indices'] = [3, 12]      # 12 is also weak (0.45)
        layout = bw.spray_layout(demo)
        self.assertEqual([layout['nozzle_levels'][i] for i in (3, 12)], [0.0, 0.0])
        self.assert_matches(layout, diagnose(demo)['width']['thermal_steady'])

    def test_invalid_cases_raise_the_width_model_errors(self):
        demo = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        bad = copy.deepcopy(demo)
        bad['width_model']['blocked_nozzle_indices'] = [99]
        with self.assertRaisesRegex(ValueError, 'nozzle index 99 out of range'):
            bw.spray_layout(bad)
        bad = copy.deepcopy(demo)
        bad['width_model'] = None
        with self.assertRaises(ValueError):
            bw.spray_layout(bad)


if __name__ == '__main__':
    unittest.main()
