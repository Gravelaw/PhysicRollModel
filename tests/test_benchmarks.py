"""Published benchmark cases beside the project's numbers (``physicroll.benchmarks``).

Two kinds of assertion, never merged: SOFTWARE pins (the project value equals the literal
recorded in ``benchmarks.py`` to 1e-6 relative; when one fails, re-record deliberately, do not
loosen the tolerance) and the VERDICT literal against the published reference. A passing
``recorded_discrepancy`` test documents a gap; it is not a validation of the physics.
"""
import contextlib
import io
import json
import math
import unittest
from pathlib import Path
from unittest import mock

from physicroll import benchmarks as bm
from physicroll import chatter

REL = 1e-6


def _q(case, name, reference=None):
    for q in case['quantities']:
        if q['name'] == name and (reference is None or q['reference_value'] == reference):
            return q
    raise AssertionError(f'{case["id"]}: no quantity {name} / {reference}')


class BenchmarkTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = bm.run_all()
        cls.cases = {c['id']: c for c in cls.result['cases']}

    def assertRel(self, value, expected, rel=REL):
        self.assertLessEqual(abs(value - expected), rel * abs(expected),
                             f'{value!r} != {expected!r} (rel {rel})')

    def test_bt_v1_software_pin(self):
        case = self.cases['BT-V1']
        self.assertRel(_q(case, 'w_bar', 118.0)['project_value'], 49.772441)
        self.assertRel(_q(case, 'force_per_width_n_m')['project_value'], 1018841.8703)
        self.assertRel(_q(case, 'forward_slip_fraction')['project_value'], 0.169779, 1e-5)
        self.assertIn('MATTRESS_REGIME_FOIL', case['flags'])

    def test_bt_v1_recorded_discrepancy_mattress_is_0_42_of_half_space_load(self):
        """Passing this test does not mean the physics is right. It records that the model is
        0.42 of the reference (half-space load W_bar 118 of BT-S1, Fig. 9)."""
        case = self.cases['BT-V1']
        ratio = _q(case, 'w_bar', 118.0)['ratio_project_to_reference']
        self.assertTrue(0.415 <= ratio <= 0.428, ratio)
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        self.assertTrue(0.79 <= _q(case, 'w_bar', 62.0)['ratio_project_to_reference'] <= 0.81)
        self.assertFalse(0.9 <= ratio <= 1.1)
        self.assertEqual(case['reference_kind'], 'MODEL_OUTPUT')

    def test_bt_v1_grid_independent(self):
        base = _q(self.cases['BT-V1'], 'w_bar', 118.0)['project_value']
        for cells in (200, 800):
            other = _q(bm._bt_v1(cells=cells), 'w_bar', 118.0)['project_value']
            self.assertRel(other, base)

    def test_bt_v2_assumed_radius(self):
        for case_id, pin in (('BT-V2-R89', 41.068824), ('BT-V2-R135', 51.052946)):
            case = self.cases[case_id]
            q = _q(case, 'w_bar', 58.0)
            self.assertRel(q['project_value'], pin)
            self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
            self.assertEqual(case['reference_kind'], 'MEASUREMENT')
            self.assertTrue(any('radius' in n.lower() and 'ASSUMED' in n
                                for n in case['input_notes']), case['input_notes'])
        self.assertAlmostEqual(_q(self.cases['BT-V2-R89'], 'w_bar')['ratio_project_to_reference'],
                               0.7081, places=4)
        self.assertAlmostEqual(
            _q(self.cases['BT-V2-R135'], 'w_bar')['ratio_project_to_reference'], 0.8802, places=4)

    def test_bt_v3_fig1_and_eq29(self):
        fig1 = self.cases['BT-V3-FIG1-140UM']
        q = _q(fig1, 'w_bar', 50.0)
        self.assertRel(q['project_value'], 45.968340)
        self.assertAlmostEqual(q['ratio_project_to_reference'], 0.919, places=3)
        self.assertEqual(fig1['verdict'], 'REFERENCE_READ_BY_EYE')
        self.assertEqual(fig1['reference_kind'], 'FIGURE_READ_BY_EYE')
        self.assertIn('MATTRESS_REGIME_CONVENTIONAL', fig1['flags'])
        f = bm.fleck_regime_boundary_entry_gauge_m
        er_demo = 210e9 / 0.91
        for args, expected_um in (((0.089, 0.25, 0.03, 230e6, 230e9), 36.24),
                                  ((0.089, 0.5, 0.03, 230e6, 230e9), 51.25),
                                  ((0.135, 0.4, 0.03, 175e6, er_demo), 56.35),
                                  ((0.135, 0.4, 0.03, 175e6 * 2 / math.sqrt(3), er_demo), 62.86)):
            self.assertAlmostEqual(f(*args) * 1e6, expected_um, delta=0.01)
        eq29 = self.cases['BT-V3-EQ29']
        self.assertEqual(eq29['verdict'], 'CONSISTENT_REGIME')
        self.assertIn('PROJECT_REGIME_FOIL_AT_20_UM_ENTRY', eq29['flags'])
        self.assertIn('PROJECT_REGIME_CONVENTIONAL_AT_140_UM_ENTRY', eq29['flags'])
        self.assertIn('54-63 um', eq29['note'])
        self.assertRel(bm.fleck_dimensionless_load(1018841.8703, 0.089, 230e6, 230e9),
                       49.772441)

    def test_ss_v2_ss_v3(self):
        ss2 = self.cases['SS-V2']
        self.assertRel(_q(ss2, 'critical_stress_pa')['project_value'], 8435559.32)
        q = _q(ss2, 'critical_i_units', 5.3)
        self.assertRel(q['project_value'], 4.016933)
        self.assertAlmostEqual(q['ratio_project_to_reference'], 0.7579, places=4)
        self.assertAlmostEqual(_q(ss2, 'half_wave_m')['ratio_project_to_reference'], 2.5,
                               places=12)
        self.assertEqual(ss2['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        ss3 = self.cases['SS-V3']
        self.assertAlmostEqual(_q(ss3, 'half_wave_m')['ratio_project_to_reference'], 2.8,
                               places=12)
        self.assertEqual(ss3['verdict'], 'RECORDED_DISCREPANCY')

    def test_tm_lc7_runs_with_three_substitutions(self):
        """Software pins and row verdicts of the steel chatter case run with three stated
        substitutions (rigid rolls, equivalent Coulomb friction, stand 2 alone). Passing this
        test does not validate the chatter screen: the frequency rows lie within the band, the
        speed rows are indicative only (one of two readings of the reference speed, damping
        heuristic)."""
        case = self.cases['TM-LC7']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        nr, ok, ind = bm.NO_REFERENCE_VALUE, 'WITHIN_AGREEMENT_BAND', 'INDICATIVE_ASSUMED_INPUTS'
        for name, reference, brief_value, verdict in (
                ('equivalent_coulomb_friction', None, 0.026566, nr),
                ('separating_force_n', None, 4.1044e6, nr),
                ('forward_slip_fraction', None, 0.02936, nr),
                ('contact_length_m', None, 5.1498e-3, nr),
                ('strip_modulus_n_m', None, 2.00515e10, nr),
                ('lower_loaded_symmetric_mode_hz', 124.6, 121.878, ok),
                ('onset_frequency_hz', 124.6, 122.303, ok),
                ('critical_exit_speed_m_s', 8.715, 8.1014, ind),
                ('critical_exit_speed_m_s', 5.81, 8.1014, ind),
                ('critical_exit_speed_without_bite_damping_m_s', None, 0.5177, nr),
                ('onset_frequency_without_bite_damping_hz', None, 481.15, nr)):
            q = _q(case, name, reference)
            self.assertRel(q['project_value'], brief_value, 1e-4)
            self.assertEqual(q['row_verdict'], verdict, name)
            self.assertEqual(q['recorded_on'], bm.RECORDED_ON_SPEC18_P1)
            self.assertIn('three substitutions', q['reference_label'])
        self.assertAlmostEqual(_q(case, 'critical_exit_speed_m_s', 8.715)
                               ['ratio_project_to_reference'], 0.930, places=3)
        self.assertAlmostEqual(_q(case, 'critical_exit_speed_m_s', 5.81)
                               ['ratio_project_to_reference'], 1.394, places=3)
        self.assertAlmostEqual(bm.TM_LC7_SPEED_IF_INTERSTAND_M_S, 8.715, places=12)
        notes = ' '.join(case['input_notes'])
        for n in (1, 2, 3):
            self.assertIn(f'Substitution {n}:', notes)
        self.assertIn('1e14', notes)
        self.assertIn('friction FACTOR m = 0.054', notes)
        self.assertIn('stand 2 alone', notes)
        self.assertIn('8.715 m/s [D]', notes)
        self.assertIn('Both are recorded; neither is asserted.', notes)
        self.assertEqual(case['inputs']['bite_pass']['friction_coefficient'],
                         _q(case, 'equivalent_coulomb_friction')['project_value'])
        for text in ('The frequency agrees because it is set by the stand and the strip '
                     'stiffness.', '0.02 -> 5.731 m/s, 107.77 Hz', '0.03 -> 9.261 m/s, 128.41 Hz',
                     '0.054 -> 16.980 m/s, 160.23 Hz',
                     'unstable from about 0.52 m/s in its upper mode (481 Hz)',
                     'indicative only', 'not a validation of the chatter screen'):
            self.assertIn(text, case['note'])
        unloaded = chatter.natural_frequencies(bm._stand(bm.TM_LC7_STAND))['symmetric_hz']
        self.assertRel(unloaded[0], 13.3134, 1e-5)
        self.assertRel(unloaded[1], 416.684, 1e-5)
        with self.assertRaises(ValueError):
            bm.equivalent_coulomb_friction(bm.TM_LC7_PASS, -0.054, 535.65e6)

    def test_tm_lc7_hitchcock_rejects_the_pass_with_real_rolls(self):
        """Substitution 1 is needed: with a 210 GPa roll the slab + Hitchcock bite rejects the
        TM-LC7 pass at the equivalent friction (keeps anyone from 'simplifying' it away)."""
        p = dict(bm.TM_LC7_PASS, friction_coefficient=0.026566)
        with self.assertRaises(ValueError):
            chatter.derive_bite_response(bm._bite_pass(p), roll_youngs_modulus_pa=210e9)

    def test_bt_v1_reference_caveat(self):
        """The reference record of BT-V1 says what the caption value rests on. The mattress
        verdict against 118 is unchanged; nothing here judges the published value."""
        case = self.cases['BT-V1']
        self.assertIn(bm.BT_V1_REFERENCE_CAVEAT, case['note'])
        self.assertIn('The caption value 118 is not a grid-independent number', case['note'])
        self.assertIn('78 to 134', case['note'])
        self.assertIn('peak about 7.7 at +0.41 mm', case['note'])
        self.assertIn('REFERENCE_NOT_GRID_INDEPENDENT', bm.VERDICTS)
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        caption = _q(case, 'w_bar', 118.0)
        self.assertEqual(caption['row_verdict'], 'RECORDED_DISCREPANCY')
        self.assertEqual(caption['recorded_on'], bm.RECORDED_ON)
        contact = _q(case, 'contact_length_m', 2.14e-3)
        self.assertRel(contact['project_value'], 1.474471e-3, 1e-5)
        self.assertAlmostEqual(contact['ratio_project_to_reference'], 0.689, places=3)
        self.assertEqual(contact['row_verdict'], 'RECORDED_DISCREPANCY')
        self.assertEqual(contact['recorded_on'], bm.RECORDED_ON_SPEC18_P1)
        self.assertIn('E6 FT', contact['reference_label'])
        es = 'E_s* = 80 GPa enters only the longitudinal no-slip equations'
        for case_id in ('BT-V1', 'BT-V2-R89', 'BT-V2-R135'):
            self.assertTrue(any(es in n for n in self.cases[case_id]['input_notes']), case_id)
        for case_id in ('BT-V2-R89', 'BT-V2-R135'):
            self.assertTrue(any('confirmed by a second full reading' in n
                                for n in self.cases[case_id]['input_notes']), case_id)

    def test_chatter_harness_reproduces_the_demo(self):
        """Software check of the harness on the project's own synthetic demo (not a
        benchmark): the values of the committed thin-gauge chatter artifact."""
        from pathlib import Path
        case = json.loads((Path(__file__).resolve().parents[1] / 'scenarios' /
                           'band_diagnosis_thin_gauge_chatter.json').read_text())
        obs = case['observation']
        measured_hz = 16.0 / 0.08408       # demo pitch at 16 m/s (model-generated)
        r = bm.chatter_onset_comparison(
            case['stand'], case['spans'], case['pass'],
            measured_critical_speed_m_s=obs['onset_above_exit_speed_m_s'],
            measured_frequency_hz=measured_hz, bite_damping_transit_fraction=0.5,
            roll_youngs_modulus_pa=case['stand']['roll_youngs_modulus_pa'],
            roll_poisson_ratio=case['stand']['roll_poisson_ratio'],
            cells=case['model_options']['cells'])
        w, z = r['with_bite_damping'], r['without_bite_damping']
        self.assertRel(w['critical_exit_speed_m_s'], 13.267836)
        self.assertRel(w['onset_frequency_hz'], 189.109442)
        self.assertRel(z['critical_exit_speed_m_s'], 4.829571)
        self.assertRel(z['onset_frequency_hz'], 188.911169)
        self.assertEqual(z['bite_damping_transit_fraction'], 0.0)
        self.assertAlmostEqual(w['speed_ratio_to_measured'],
                               w['critical_exit_speed_m_s'] / 13.3)
        self.assertAlmostEqual(z['frequency_ratio_to_measured'],
                               z['onset_frequency_hz'] / measured_hz)
        self.assertEqual(r['status'], bm.STATUS)
        json.dumps(r, allow_nan=False)
        with self.assertRaises(ValueError):
            bm.chatter_onset_comparison(case['stand'], case['spans'], case['pass'],
                                        measured_critical_speed_m_s=-1.0,
                                        measured_frequency_hz=100.0)

    def test_run_all_is_json_safe_and_complete(self):
        json.dumps(self.result, allow_nan=False)
        self.assertEqual(self.result['status'],
                         'SOFTWARE_COMPARISON_WITH_PUBLISHED_VALUES_NOT_PHYSICAL_VALIDATION')
        self.assertEqual(tuple(c['id'] for c in self.result['cases']), bm.CASE_IDS)
        keys = {'id', 'title', 'source', 'source_id', 'read_status', 'reference_kind',
                'inputs', 'input_notes', 'quantities', 'verdict', 'agreement_band', 'note',
                'flags'}
        for case in self.result['cases']:
            self.assertEqual(set(case), keys)
            self.assertTrue(case['read_status'])
            self.assertIn(case['verdict'], bm.VERDICTS)
            self.assertIn(case['reference_kind'], bm.REFERENCE_KINDS)
            self.assertEqual(case['agreement_band'], [0.9, 1.1])
            for q in case['quantities']:
                if q['project_value'] is not None:   # every software pin, 1e-6 relative
                    self.assertRel(q['project_value'], q['recorded_project_value'])
                    self.assertIn(q['recorded_on'], (bm.RECORDED_ON, bm.RECORDED_ON_SPEC18_P1,
                                                     bm.RECORDED_ON_SPEC18_P4,
                                                     bm.RECORDED_ON_SPEC18_P5,
                                                     bm.RECORDED_ON_SPEC18_P6,
                                                     bm.RECORDED_ON_SPEC18_P7,
                                                     bm.RECORDED_ON_SPEC18_P9,
                                     bm.RECORDED_ON_SPEC19_P4,
                                     bm.RECORDED_ON_SPEC19_P5,
                                     bm.RECORDED_ON_SPEC19_P6))
        ids = {e['id'] for e in self.result['not_encoded']}
        self.assertTrue({'BT-V4', 'BT-V9', 'SS-V1', 'SS-V4', 'SS-V5', 'SS-V11'} <= ids)
        self.assertFalse(ids & {'BT-V1', 'BT-V2', 'BT-V3', 'SS-V2', 'SS-V3'})
        rows = bm.table_rows(self.result)
        self.assertEqual(len(rows), sum(len(c['quantities']) for c in self.result['cases']))
        for case in self.result['cases']:   # row verdict: no reference -> NO_REFERENCE_VALUE
            for q in case['quantities']:
                self.assertIn(q['row_verdict'], bm.VERDICTS + (bm.NO_REFERENCE_VALUE,))
                self.assertEqual(q['row_verdict'] == bm.NO_REFERENCE_VALUE,
                                 q['reference_value'] is None)
        for r in rows:
            self.assertEqual(r['verdict'] == bm.NO_REFERENCE_VALUE, r['reference'] is None)
        slip = [r for r in rows if r['id'] == 'BT-V1' and r['quantity'] == 'forward_slip_fraction']
        self.assertEqual([(r['verdict'], r['case_verdict']) for r in slip],
                         [('NO_REFERENCE_VALUE', 'RECORDED_DISCREPANCY')])
        # the command line prints the result already computed (run_all takes about 15 s)
        with mock.patch.object(bm, 'run_all', return_value=self.result):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(bm.main(['--json']), 0)
            self.assertEqual(json.loads(buf.getvalue())['status'], bm.STATUS)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                bm.main([])
        self.assertIn('RECORDED_DISCREPANCY', buf.getvalue())
        for line in bm.TM_LC7_SUBSTITUTIONS:   # the substitutions wherever TM-LC7 is shown
            self.assertIn(line, buf.getvalue())

    def test_bt_v1_hs_reference_not_grid_independent(self):
        """Passing this test does not mean the physics is right. It records that the published
        value depends on an unstated end length."""
        case = self.cases['BT-V1-HS']
        self.assertEqual(case['verdict'], 'REFERENCE_NOT_GRID_INDEPENDENT')
        self.assertIn(bm.BT_V1_HS_NOTE, case['note'])
        for name, pin in (('w_bar_rigid_strip', 88.859), ('w_bar_strip_spring_80_gpa', 92.936)):
            q = _q(case, name)
            self.assertRel(q['project_value'], pin, 1e-5)
            self.assertEqual(q['row_verdict'], 'REFERENCE_NOT_GRID_INDEPENDENT')
            self.assertEqual(q['reference_value'], 118.0)
        for name, ratio in (('contact_length_rigid_strip_m', 0.9166),
                            ('contact_length_strip_spring_80_gpa_m', 0.9525)):
            q = _q(case, name)
            self.assertAlmostEqual(q['ratio_project_to_reference'], ratio, delta=1e-4)
            self.assertEqual(q['row_verdict'], 'WITHIN_AGREEMENT_BAND')
        for name in ('peak_pressure_over_ys_rigid_strip', 'peak_position_rigid_strip_m',
                     'contact_start_rigid_strip_m', 'contact_end_rigid_strip_m'):
            self.assertEqual(_q(case, name)['row_verdict'], 'REFERENCE_READ_BY_EYE')
        family = {um: _q(case, f'w_bar_printed_end_{um}_um')['project_value']
                  for um in (40, 21, 10, 5, 2.5)}
        for um, pin in ((40, 78.01), (21, 88.62), (10, 102.62), (5, 117.47), (2.5, 134.15)):
            self.assertAlmostEqual(family[um], pin, delta=0.005)
            self.assertEqual(_q(case, f'w_bar_printed_end_{um}_um')['row_verdict'],
                             bm.NO_REFERENCE_VALUE)
        self.assertGreater(family[5], 1.3 * family[21])
        self.assertIn('CONSISTENT_REGIME_WITH_FIGURE', case['flags'])
        for q in case['quantities']:          # no ratio to 118 is called agreement or not
            if q['reference_value'] == 118.0:
                self.assertNotIn(q['row_verdict'], ('RECORDED_DISCREPANCY',
                                                    'WITHIN_AGREEMENT_BAND'))

    def test_other_half_space_rows(self):
        for case_id, pin, ratio in (('BT-V2-R89-HS', 42.800, 0.738),
                                    ('BT-V2-R135-HS', 67.125, 1.157),
                                    ('BT-V3-FIG1-140UM-HS', 46.820, 0.936)):
            q = _q(self.cases[case_id], 'w_bar')
            self.assertAlmostEqual(q['project_value'], pin, delta=5e-4)
            self.assertAlmostEqual(q['ratio_project_to_reference'], ratio, delta=5e-4)
        self.assertEqual(self.cases['BT-V2-R89-HS']['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        self.assertEqual(self.cases['BT-V3-FIG1-140UM-HS']['verdict'], 'REFERENCE_READ_BY_EYE')
        eq29 = self.cases['BT-V3-EQ29-HS']
        self.assertEqual(eq29['verdict'], 'CONSISTENT_REGIME')
        self.assertEqual(eq29['flags'], [])
        verdicts = {q['name']: q['row_verdict'] for q in eq29['quantities']}
        self.assertEqual(verdicts['entry_gauge_r50_with_no_slip_zone_m'], 'CONSISTENT_REGIME')
        self.assertEqual(verdicts['entry_gauge_r10_with_no_slip_zone_m'], 'RECORDED_DISCREPANCY')
        x29 = self.cases['BT-X29-LOAD-EXPONENT-HS']
        self.assertAlmostEqual(_q(x29, 'load_exponent_in_friction', 2.0)['project_value'], 2.461,
                               delta=5e-4)
        self.assertIn('INSIDE_READ_RANGE', x29['flags'])

    def test_bite_comparison_cli(self):
        fake = {'note': 'n', 'rows': [{'label': 'p', 'hitchcock': {'rejected': 'r'},
                                       'experimental_mattress': {
                                           'force_per_width_n_m': 1.0,
                                           'forward_slip_fraction': 0.1,
                                           'contact_length_m': 1e-3,
                                           'strip_modulus_per_width_pa': 1e9},
                                       'reduced_half_space': {'rejected': 'r2'}}]}
        with mock.patch.object(bm, 'bite_model_comparison', return_value=fake):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                template = str(Path(__file__).resolve().parents[1] / 'scenarios'
                               / 'band_diagnosis_template.json')
                self.assertEqual(bm.main(['--bite-comparison', template]), 0)
        self.assertIn('rejected: r2', buf.getvalue())

    def test_oil_and_film_cases(self):
        """Software comparison of the film formula and of the two pressure laws with the
        published values; the pressure-law case records that neither law carries the one foil
        oil with data to bite pressure (Roelands low by 12 to 30 times)."""
        film = self.cases['BT-G3-FILM-E6-T42']
        self.assertEqual(film['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        for u, um, ratio in ((30, 0.3242, 1.004), (10, 0.1081, 1.001), (5, 0.0540, 1.001),
                             (3, 0.0324, 1.013), (1, 0.0108, 0.983)):
            q = _q(film, f'film_thickness_{u}_m_s_m')
            self.assertAlmostEqual(q['project_value'] * 1e6, um, delta=5e-5)
            self.assertAlmostEqual(q['ratio_project_to_reference'], ratio, delta=5e-4)
        v4 = self.cases['BT-V4-FILM']
        self.assertAlmostEqual(_q(v4, 'film_ratio_5_m_s')['project_value'], 0.2093, delta=5e-5)
        self.assertAlmostEqual(_q(v4, 'film_ratio_40_m_s')['project_value'], 1.6748,
                               delta=5e-4)
        ids = {e['id']: e['reason'] for e in self.result['not_encoded']}
        self.assertIn('BT-V4-FILM', ids['BT-V4'])
        a9 = self.cases['A9-PRESSURE-LAWS-KEROSINE']
        self.assertEqual(a9['verdict'], 'RECORDED_DISCREPANCY')
        self.assertEqual(a9['reference_kind'], 'MEASUREMENT')
        verdicts = {q['name']: (q['ratio_project_to_reference'], q['row_verdict'])
                    for q in a9['quantities']}
        self.assertEqual(verdicts['viscosity_barus_100_mpa_pa_s'][1], 'WITHIN_AGREEMENT_BAND')
        for p_, rb, rr in ((625, 0.375, 0.072), (945, 1.742, 0.082), (1510, 12.6, 0.033)):
            self.assertAlmostEqual(verdicts[f'viscosity_barus_{p_}_mpa_pa_s'][0], rb,
                                   delta=0.05 * rb)
            self.assertAlmostEqual(verdicts[f'viscosity_roelands_{p_}_mpa_pa_s'][0], rr,
                                   delta=0.05 * rr)
            self.assertEqual(verdicts[f'viscosity_roelands_{p_}_mpa_pa_s'][1],
                             'RECORDED_DISCREPANCY')
        # 100 MPa Roelands row: 0.928, inside the 0.9-1.1 band (the brief's text calls it a
        # discrepancy; the rule "row verdicts by the band" gives the agreement word)
        self.assertEqual(verdicts['viscosity_roelands_100_mpa_pa_s'][1], 'WITHIN_AGREEMENT_BAND')

    def test_crushing_laws_recorded_discrepancy(self):
        """Passing this test does not mean any law is right: it records that the four
        transcribed crushing laws differ from the thesis theory values and from one another
        away from A = 0.5, p_bar/2k = 1; they are not assembled into a model."""
        case = self.cases['BT-G3-CRUSHING-LAWS']
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        self.assertIn('not assembled into a model', case['note'])
        ratios = {q['name']: q['ratio_project_to_reference'] for q in case['quantities']}
        for name, want in (('w_thesis_fit_eq_3_20_a050_p10', 1.102),
                           ('w_thesis_fit_eq_3_20_a050_p06', 0.31),
                           ('w_korzekwa_regression_a050_p10', 1.198),
                           ('w_korzekwa_regression_a050_p06', 3.67),
                           ('w_marsault_form_a050_p10', 1.102),
                           ('w_marsault_form_a050_p06', 3.65),
                           ('w_wilson_sheu_fit_a050_p10', 8.17),
                           ('w_wilson_sheu_fit_a050_p06', 3.52)):
            self.assertAlmostEqual(ratios[name], want, delta=0.005 * want + 0.003, msg=name)

    def test_friction_identified_from_bt_v2_load(self):
        case = self.cases['BT-V2-FRICTION-HS']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        # SPEC18 package 7 worked numbers: 0.03064 (slip 0.1966) and 0.02488 (slip 0.2594);
        # ratios to the source's 0.026: 1.178 and 0.957 (secant tolerance 1e-4 in force)
        for mm, mu, slip, ratio in ((89, 0.03064, 0.1966, 1.178), (135, 0.02488, 0.2594, 0.957)):
            q = _q(case, f'friction_from_force_r{mm}')
            self.assertAlmostEqual(q['project_value'], mu, delta=2e-4 * mu)
            self.assertAlmostEqual(q['ratio_project_to_reference'], ratio, delta=5e-4)
            self.assertEqual(q['row_verdict'], 'INDICATIVE_ASSUMED_INPUTS')
            q = _q(case, f'forward_slip_at_friction_r{mm}')
            self.assertAlmostEqual(q['project_value'], slip, delta=1e-4)
            self.assertEqual(q['row_verdict'], bm.NO_REFERENCE_VALUE)

    def test_ss_v8_loop_indicative_against_the_published_band(self):
        case = self.cases['SS-V8-LOOP']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        self.assertEqual(case['reference_kind'], 'MEASUREMENT')
        q = case['quantities'][0]
        self.assertEqual(q['reference_value'], 6.0)
        if q['project_value'] is not None:          # read from the committed artifact
            self.assertLess(abs(q['project_value'] / q['recorded_project_value'] - 1), 1e-6)
        self.assertNotIn('SS-V8', {e['id'] for e in self.result['not_encoded']})

    def test_a6_zone_time_constant_indicative_both_ratios(self):
        case = self.cases['A6-ZONE-TIME-CONSTANT']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        self.assertEqual([q['reference_value'] for q in case['quantities']], [20.0, 20.0])
        for q in case['quantities']:
            if q['project_value'] is not None:
                self.assertLess(abs(q['project_value'] / q['recorded_project_value'] - 1), 1e-6)

    def test_ss_v2_local_plate_indicative_close_to_published_critical_values(self):
        case = self.cases['SS-V2-LOCAL-PLATE']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        ss = _q(case, 'critical_i_units_simply_supported')
        cl = _q(case, 'critical_i_units_clamped')
        self.assertEqual((ss['reference_value'], cl['reference_value']), (5.3, 8.92))
        self.assertLess(abs(ss['project_value'] / 5.341 - 1), 5e-3)     # planner's numbers
        self.assertLess(abs(cl['project_value'] / 8.649 - 1), 5e-3)
        self.assertTrue(0.9 <= ss['ratio_project_to_reference'] <= 1.1)
        self.assertTrue(0.9 <= cl['ratio_project_to_reference'] <= 1.1)
        hs = _q(case, 'half_wave_simply_supported_m')
        hc = _q(case, 'half_wave_clamped_m')
        self.assertLess(abs(hs['project_value'] / 0.1494 - 1), 5e-3)
        self.assertLess(abs(hc['project_value'] / 0.0994 - 1), 5e-3)
        self.assertGreater(hs['ratio_project_to_reference'], 2.4)          # 2.49 x measured
        self.assertGreater(hc['ratio_project_to_reference'], 1.6)          # 1.66 x measured

    def test_ss_v2_wide_strip_recorded_discrepancy_half_wave_is_twice_the_measured_share(self):
        case = self.cases['SS-V2-WIDE-STRIP']
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        for tag, peak, half, width in (('10_mpa', 12.30, 0.1761, 0.220),
                                       ('30_mpa', 27.22, 0.1286, 0.160)):
            self.assertLess(abs(_q(case, f'critical_peak_i_units_{tag}')['project_value']
                                / peak - 1), 5e-3)
            self.assertLess(abs(_q(case, f'half_wave_m_{tag}')['project_value'] / half - 1),
                            5e-3)
            self.assertLess(abs(_q(case, f'mode_width_10_percent_m_{tag}')['project_value']
                                / width - 1), 5e-3)
            r = _q(case, f'half_wave_over_mode_width_{tag}')
            self.assertEqual(r['row_verdict'], 'RECORDED_DISCREPANCY')
            self.assertAlmostEqual(r['reference_value'], 0.4)
            self.assertGreater(r['ratio_project_to_reference'], 1.9)       # about 2.0

    def test_ss_v3_wide_strip_recorded_discrepancy_half_wave_share(self):
        case = self.cases['SS-V3-WIDE-STRIP']
        self.assertEqual(case['verdict'], 'RECORDED_DISCREPANCY')
        for tag, peak, half, width in (('5_mpa', 18.85, 0.0919, 0.115),
                                       ('15_mpa', 42.80, 0.0689, 0.085)):
            self.assertLess(abs(_q(case, f'critical_peak_i_units_{tag}')['project_value']
                                / peak - 1), 5e-3)
            self.assertLess(abs(_q(case, f'half_wave_m_{tag}')['project_value'] / half - 1),
                            5e-3)
            self.assertLess(abs(_q(case, f'mode_width_10_percent_m_{tag}')['project_value']
                                / width - 1), 5e-3)
            r = _q(case, f'half_wave_over_mode_width_{tag}')
            self.assertEqual(r['row_verdict'], 'RECORDED_DISCREPANCY')
            self.assertGreater(r['ratio_project_to_reference'], 2.0)
        reasons = {e['id']: e['reason'] for e in self.result['not_encoded']}
        self.assertIn('bifurcation force is not', reasons['SS-V1'])
        self.assertIn('stress profile of the paper', reasons['SS-V4'])

    def test_tm_la19_heat_split_inside_measured_range(self):
        case = self.cases['TM-LA19-HEAT-SPLIT']
        self.assertEqual(case['verdict'], 'INDICATIVE_ASSUMED_INPUTS')
        self.assertIn('inside the measured range; film thickness and conductivity are assumed',
                      case['note'])
        for key, want in (('perfect_contact', 0.1621), ('film_70nm_k0125', 0.2279),
                          ('film_70nm_k025', 0.1952)):
            for end, ref in (('low', 0.11), ('high', 0.33)):
                q = _q(case, f'strip_share_{key}_vs_{end}_end')
                self.assertAlmostEqual(q['project_value'], want, delta=1e-4)
                self.assertEqual(q['reference_value'], ref)
                self.assertTrue(0.11 <= q['project_value'] <= 0.33)
                self.assertEqual(q['row_verdict'], 'INDICATIVE_ASSUMED_INPUTS')

    def test_tm_la8_spray_fit_reference_only(self):
        case = self.cases['TM-LA8-SPRAY-FIT']
        self.assertEqual(case['verdict'], 'REFERENCE_ONLY_INPUTS_NOT_RECORDED')
        self.assertEqual([q['reference_value'] for q in case['quantities']], [17500.0, 22000.0])
        for q in case['quantities']:
            self.assertIsNone(q['project_value'])
            self.assertIsNone(q['ratio_project_to_reference'])

    def test_ss_v14_foil_factor_reference_only(self):
        # SPEC19 package 12: the factors are recorded, the trials' inputs are not
        case = self.cases['SS-V14']
        self.assertEqual(case['verdict'], 'REFERENCE_ONLY_INPUTS_NOT_RECORDED')
        self.assertEqual([q['reference_value'] for q in case['quantities']], [15.0, 7.0, 10.0])
        for q in case['quantities']:
            self.assertIsNone(q['project_value'])
            self.assertEqual(q['row_verdict'], 'REFERENCE_ONLY_INPUTS_NOT_RECORDED')
        reasons = {e['id']: e['reason'] for e in self.result['not_encoded']}
        self.assertNotIn('SS-V14', reasons)
        self.assertIn('critical values not quoted in the reports', reasons['SS-V15'])

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            bm.run_case('BT-V99')
        with self.assertRaises(ValueError):
            bm.fleck_regime_boundary_entry_gauge_m(0.089, 1.5, 0.03, 230e6, 230e9)


if __name__ == '__main__':
    unittest.main()
