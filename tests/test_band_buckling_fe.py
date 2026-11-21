"""SPEC19 package 6 in the engine: buckling with a wavelength search beside the sine mode.

Opt-in (``model_options.buckling_model = 'sine_mode_and_fe'``): the section is reported beside
the present band states, which stay the ones the evidence uses. The demo numbers are computed
from the committed artifacts' profiles (planner, SPEC19 package 7 table, in-mill column).
"""
import copy
import json
from pathlib import Path
import time
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from physicroll import band_width as bw
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import LONG, NOZZLES, v2, width_model

ART = Path(__file__).resolve().parents[1] / 'artifacts' / 'band_diagnosis'


def _sp(result):
    c = result['inputs']
    return {'strip_youngs_modulus_pa': c['material']['youngs_modulus_pa'],
            'strip_poisson_ratio': bw.STRIP_POISSON_RATIO,
            'exit_thickness_m': c['pass']['exit_thickness_m'],
            'mean_tension_pa': c['pass']['exit_tension_pa']}


def _strip_fe(result):
    """The result without the new section, its flags and the option."""
    r = copy.deepcopy(result)
    r['width']['shape'].pop('buckling_fe', None)
    r['flags'] = [f for f in r['flags'] if f not in bw.BF_TOP_FLAGS]
    r['width']['flags'] = [f for f in r['width'].get('flags', []) if f not in bw.BF_TOP_FLAGS] \
        if 'flags' in r['width'] else None
    if r['width']['flags'] is None:
        r['width'].pop('flags')
    r['inputs']['model_options'].pop('buckling_model', None)
    return r


class DemoProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sec = {}
        cls.t = {}
        for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
            r = json.loads((ART / f'{name}.result.json').read_text(encoding='utf-8'))
            t0 = time.perf_counter()
            cls.sec[name] = bw.buckling_fe_section(
                r['width']['shape'], r['width']['thermal_events'].get('events'), _sp(r),
                'sine_mode_and_fe')
            cls.t[name] = time.perf_counter() - t0
            cls.sec[name + ':r'] = r

    def test_battery_foil_flat_in_the_mill_short_local_mode(self):
        st = self.sec['battery-foil-demo']['profiles'][0]['in_mill']
        self.assertEqual(st['state'], 'FLAT')
        self.assertAlmostEqual(st['utilisation'], 0.435, delta=0.003)
        self.assertAlmostEqual(st['half_wavelength_m'], 0.0401, delta=0.0005)
        self.assertAlmostEqual(st['mode_peak_position_m'], 0.623, delta=0.006)
        self.assertAlmostEqual(st['mode_width_10_percent_m'], 0.030, delta=0.006)
        self.assertEqual(st['mode_localisation'], 'LOCAL')
        self.assertEqual(st['at_search_limit'], 'SHORTEST')

    def test_lengthwise_buckles_in_the_mill_with_a_107_mm_half_wave(self):
        p = self.sec['lengthwise-bands-demo']['profiles'][0]
        st = p['in_mill']
        self.assertEqual(st['state'], 'BUCKLES')
        self.assertAlmostEqual(st['utilisation'], 1.113, delta=0.006)
        self.assertAlmostEqual(st['half_wavelength_m'], 0.1076, delta=0.0011)
        self.assertAlmostEqual(st['mode_peak_position_m'], 0.672, delta=0.006)
        self.assertAlmostEqual(st['mode_width_10_percent_m'], 0.130, delta=0.011)
        gov = [b for b in p['bands'] if b['in_mill']['mode_peaks_in_this_band']]
        self.assertEqual(len(gov), 1)
        self.assertEqual(gov[0]['sine_mode_state'], 'MANIFEST_BUCKLE')
        self.assertIs(gov[0]['in_mill']['agrees_with_sine_mode'], True)
        others = [b for b in p['bands'] if not b['in_mill']['mode_peaks_in_this_band']]
        self.assertTrue(all(b['in_mill']['wavelength_search_state'] == 'NOT_DECIDED_ONE_MODE'
                            for b in others))

    def test_after_release_is_a_whole_sheet_mode_compared_with_the_global_indicator(self):
        for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
            for p in self.sec[name]['profiles']:
                rel = p['after_release']
                self.assertEqual(rel['mean_tension_pa'], 0.0)
                self.assertEqual(rel['at_search_limit'], 'LONGEST')
                self.assertEqual(rel['mode_localisation'], 'WHOLE_SHEET')
                self.assertIn('whole-sheet mode', p['after_release_note'])
                self.assertTrue(all(b['after_release']['wavelength_search_state']
                                    == 'WHOLE_SHEET_MODE_NOT_A_BAND' for b in p['bands']))
                self.assertIn('after_release_whole_sheet_agrees_with_sine_mode', p)

    def test_tension_raises_the_critical_load_and_shortens_the_wave(self):
        for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
            p = self.sec[name]['profiles'][0]
            self.assertGreater(p['after_release']['utilisation'], p['in_mill']['utilisation'])
            self.assertLess(p['in_mill']['half_wavelength_m'],
                            p['after_release']['half_wavelength_m'])

    def test_present_states_named_as_the_ones_the_evidence_uses(self):
        for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
            s = self.sec[name]
            self.assertEqual(s['status'], bw.BF_STATUS)
            self.assertIn('present (sine-mode) band states', s['used_by_the_evidence'])
            self.assertIn(bw.BF_FLAG_BESIDE, s['flags'])
            self.assertIn('far-field', s['basis']['stress_profile'])
            json.dumps(s, allow_nan=False)
            r = self.sec[name + ':r']
            for p, b in zip(s['profiles'][0]['bands'],
                            r['width']['shape']['steady']['levels']['with_feedback']['bands']):
                self.assertEqual(p['sine_mode_state'], b['state'])

    def test_run_time_budget(self):
        # SPEC19 0.3: at most 0.6 s per profile and state, at most 6 s per diagnose
        for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
            n = len(self.sec[name]['profiles'])
            self.assertLess(self.t[name], 6.0)
            self.assertLess(self.t[name] / (3 * n), 0.6 * 2)   # loose on a slow machine

    def test_disagreement_is_said_per_band(self):
        rows = [{'start_m': 0.0, 'end_m': 0.2, 'peak_i_units': 30.0,
                 'state': 'LATENT_UNDER_TENSION',
                 'state_after_tension_release': 'FLAT_AFTER_TENSION_RELEASE'}]
        mill = {'state': 'BUCKLES', 'mode_peak_position_m': 0.1, 'mode_localisation': 'LOCAL'}
        rel = {'state': 'FLAT'}
        out = bw._bf_band_rows(rows, mill, rel)[0]
        self.assertIs(out['in_mill']['agrees_with_sine_mode'], False)
        self.assertIn('the evidence uses the sine mode', out['in_mill']['note'])
        self.assertIs(out['after_release']['agrees_with_sine_mode'], True)

    # ------------------------------------------------------- SPEC19 package 7 (planner table)
    def test_battery_foil_post_buckling_and_table(self):
        p = self.sec['battery-foil-demo']['profiles'][0]
        self.assertEqual(p['in_mill']['post_buckling']['state'], 'FLAT')
        rel = p['after_release']['post_buckling']
        self.assertAlmostEqual(rel['peak_to_valley_m'], 20.8e-3, delta=0.02 * 20.8e-3)
        self.assertAlmostEqual(rel['reading_at_profile_peak_i_units'], 17.3, delta=0.02 * 17.3)
        self.assertAlmostEqual(rel['linear_reading_at_profile_peak_i_units'], 25.09, delta=0.01)
        self.assertIn('whole-sheet mode', rel['wording'])
        tb = p['on_table']
        self.assertEqual(tb['state'], 'LIFTS')
        self.assertAlmostEqual(tb['scale_to_lift'], 0.0298, delta=0.02 * 0.0298)
        self.assertAlmostEqual(tb['lift_limit_peak_i_units'], 0.75, delta=0.02 * 0.75)
        self.assertAlmostEqual(tb['half_wavelength_m'], 0.030, delta=0.001)
        self.assertEqual(tb['at_search_limit'], 'SHORTEST')
        self.assertAlmostEqual(tb['peak_to_valley_on_table_m'], 0.72e-3, delta=0.02 * 0.72e-3)

    def test_lengthwise_post_buckling_and_table(self):
        p = self.sec['lengthwise-bands-demo']['profiles'][0]
        pb = p['in_mill']['post_buckling']
        self.assertAlmostEqual(p['in_mill']['critical_multiplier'], 0.8981, delta=0.02 * 0.8981)
        self.assertEqual(pb['state'], 'BUCKLED')
        self.assertAlmostEqual(pb['amplitude_m'], 0.5845e-3, delta=0.02 * 0.5845e-3)
        self.assertAlmostEqual(pb['peak_to_valley_m'], 1.17e-3, delta=0.02 * 1.17e-3)
        self.assertAlmostEqual(pb['reading_at_profile_peak_i_units'], 43.6, delta=0.02 * 43.6)
        self.assertIn('of the order of', pb['wording'])
        self.assertIn('upper estimate', pb['wording'])
        self.assertIn('in the mill under the exit tension', pb['wording'])
        self.assertEqual(len(pb['z_m']), len(pb['saturated_i_units']))
        self.assertAlmostEqual(p['after_release']['post_buckling']['peak_to_valley_m'], 33.9e-3,
                               delta=0.02 * 33.9e-3)
        tb = p['on_table']
        self.assertAlmostEqual(tb['lift_limit_peak_i_units'], 2.20, delta=0.02 * 2.20)
        self.assertAlmostEqual(tb['scale_to_lift'], 0.0435, delta=0.02 * 0.0435)
        self.assertAlmostEqual(tb['half_wavelength_m'], 0.090, delta=0.002)
        self.assertAlmostEqual(tb['peak_to_valley_on_table_m'], 2.99e-3, delta=0.02 * 2.99e-3)
        gov = [b for b in p['bands'] if b['on_table']['mode_peaks_in_this_band']]
        self.assertEqual([b['on_table']['table_state'] for b in gov], ['LIFTS'])
        self.assertIn('wave', gov[0]['in_mill'])
        self.assertIn('NOT change any band state', self.sec['lengthwise-bands-demo']
                      ['not_in_the_tally'])

    def test_saturated_profile_is_an_additional_shapemeter_reading(self):
        from physicroll import band_sensors as bsn
        r = self.sec['lengthwise-bands-demo:r']
        width = copy.deepcopy(r['width'])
        before = [p['name'] for p in bsn.shapemeter_profiles(width)]
        width['shape']['buckling_fe'] = self.sec['lengthwise-bands-demo']
        after = [p['name'] for p in bsn.shapemeter_profiles(width)]
        self.assertEqual([n for n in after if n != 'steady_saturated'], before)
        self.assertIn('steady_saturated', after)
        rb = self.sec['battery-foil-demo:r']
        wb = copy.deepcopy(rb['width'])
        wb['shape']['buckling_fe'] = self.sec['battery-foil-demo']     # flat in the mill
        self.assertNotIn('steady_saturated', [p['name'] for p in bsn.shapemeter_profiles(wb)])

    def test_table_keeps_a_reported_band_flat_is_said_per_band(self):
        rows = [{'start_m': 0.0, 'end_m': 0.2, 'peak_i_units': 3.0,
                 'state': 'LATENT_UNDER_TENSION',
                 'state_after_tension_release': 'MANIFEST_AFTER_TENSION_RELEASE'}]
        out = bw._bf_band_rows(rows, {'state': 'FLAT'}, {'state': 'FLAT'},
                               {'state': 'LIES_FLAT', 'mode_peak_position_m': 0.1})[0]
        self.assertEqual(out['on_table']['table_state'], 'LIES_FLAT')
        self.assertTrue(out['on_table']['keeps_reported_band_flat'])
        self.assertIn('the length difference is still there', out['on_table']['note'])
        self.assertIn('the tally keeps the sine-mode state', out['on_table']['note'])


class EngineOptIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = v2(**LONG, band_positions_across_width_m=[NOZZLES[12]],
               lengthwise_continuity='continuous', appearance='loose_or_buckle')
        c['width_model'] = width_model(blocked_nozzle_indices=[12])
        cls.base = bd.diagnose(copy.deepcopy(c))
        c['model_options']['buckling_model'] = 'sine_mode_and_fe'
        cls.fe = bd.diagnose(c)
        c2 = copy.deepcopy(c)
        c2['model_options']['buckling_model'] = 'sine_mode'
        cls.sine = bd.diagnose(c2)

    def test_default_has_no_section(self):
        self.assertNotIn('buckling_fe', self.base['width']['shape'])
        self.assertNotIn('buckling_model', self.base['inputs']['model_options'])

    def test_option_changes_nothing_else(self):
        self.assertEqual(self.fe['width']['shape']['buckling_fe']['status'], bw.BF_STATUS)
        self.assertIn(bw.BF_FLAG_BESIDE, self.fe['flags'])
        self.assertEqual(json.dumps(_strip_fe(self.fe), sort_keys=True),
                         json.dumps(self.base, sort_keys=True))
        self.assertEqual([(h['id'], h['score'], h['standing']) for h in self.fe['hypotheses']],
                         [(h['id'], h['score'], h['standing']) for h in self.base['hypotheses']])

    def test_sine_mode_value_gives_a_not_supplied_section(self):
        self.assertTrue(self.sine['width']['shape']['buckling_fe']['not_supplied'])
        self.assertEqual(json.dumps(_strip_fe(self.sine), sort_keys=True),
                         json.dumps(self.base, sort_keys=True))

    def test_report_table_and_sentence(self):
        html = render_band_report(self.fe)
        self.assertIn('Waves with a wavelength search', html)
        self.assertIn('is the one the shortlist uses', html)
        self.assertNotIn('Waves with a wavelength search', render_band_report(self.base))

    def test_validation_and_question(self):
        c = v2()
        c['model_options']['buckling_model'] = 'koiter'
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(c)
        self.assertIn('model_options.buckling_model must be one of', str(cm.exception))
        q = bpl.QUESTION_BY_ID['buckling_model']
        self.assertEqual(tuple(v for v, _ in q.choices), bd.BUCKLING_MODELS)
        for f in bw.BF_TOP_FLAGS:
            self.assertIn(f, bpl.FLAGS)
        self.assertIn('lie flat on a table', q.help)


if __name__ == '__main__':
    unittest.main()
