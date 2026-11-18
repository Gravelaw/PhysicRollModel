"""Battery-foil phase (SPEC9): width section without a bite, supplied shape inputs, the
foil-regime block, the new observations and the foil_tension_lines hypothesis, the rule
extensions, the torsional strip map, the foil demo and the report.

Kept fast: coarse thermal numerics, cases whose bite fails (no mattress solve) wherever the
bite is not the point, and one coarse run of the foil demo.
"""
import copy
import json
import math
import unittest

from physicroll import band_width as bw
from physicroll.band_diagnosis import (BITE_FLOOR_FLAG, CASE_SCHEMA_V1, CLOSED_GAP_FLAG, diagnose,
                                       load_case, result_json, validate_case)
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import (COARSE, SCEN, TRIBOLOGY, V2_NULL_OBS, _h, v2,
                                        width_model)

FOIL_NOZZLES_BARREL = 1.5
FOIL_HEADER = {'nozzle_pitch_m': 0.052, 'standoff_m': 0.2, 'spray_angle_rad': 0.8,
               'offset_angle_rad': 0.17, 'spray_mean_htc_w_m2k': 2000.0,
               'background_htc_w_m2k': 50.0}
SHAPE_INPUTS = {'strip_stiffness_per_width_pa': 4.0e10,
                'exit_tension_force_sensitivity_per_width_m': 0.02,
                'bite_half_length_m': 2.0e-3,
                'provenance': 'unit test: assumed plant foil-model values <b>&</b>'}


def foil_case(friction=0.05, h0=60e-6, h1=30e-6, schedule=True, width=True, **observation):
    """60 -> 30 um pass on the foil demo mill; friction 0.05 makes both bite models reject
    (sticking), so no mattress bite is solved (fast). Thermal numerics coarse."""
    c = v2(override=False, **observation)
    c['name'] = 'unit foil'
    c['pass'].update(entry_thickness_m=h0, exit_thickness_m=h1, width_m=1.2,
                     work_roll_radius_m=0.135, mean_flow_stress_pa=170e6,
                     friction_coefficient=friction, entry_tension_pa=35e6,
                     exit_tension_pa=40e6, exit_speed_m_s=13.0)
    c['material'].update(alloy='AA1235', temper='H18', yield_stress_pa=165e6,
                         magnesium_wt_pct=0.0)
    c['stand'].update(work_roll_mass_kg=1100.0, backup_roll_mass_kg=9000.0,
                      work_backup_contact_stiffness_n_m=2.0e10, housing_stiffness_n_m=6.0e9)
    c['spans'].update(entry_span_length_m=3.0, exit_span_length_m=3.0)
    c['kinematics']['backup_roll_diameter_m'] = 0.75
    if schedule:
        c['schedule'] = [
            {'label': 'P2 0.135->0.068 mm', 'entry_thickness_m': 135e-6,
             'exit_thickness_m': 68e-6, 'mean_flow_stress_pa': 165e6,
             'friction_coefficient': 0.03, 'entry_tension_pa': 32e6, 'exit_tension_pa': 38e6,
             'exit_speed_m_s': 11.0},
            {'label': 'P3 case pass', 'entry_thickness_m': h0, 'exit_thickness_m': h1,
             'mean_flow_stress_pa': 170e6, 'friction_coefficient': friction,
             'entry_tension_pa': 35e6, 'exit_tension_pa': 40e6, 'exit_speed_m_s': 13.0}]
    if width:
        w = width_model(blocked_nozzle_indices=[11], bite_heat_per_width_w_m=4.0e5,
                        roll_heat_fraction_per_roll=0.08,
                        incoming_ridges=[{'position_m': 0.9, 'height_m': 0.5e-6,
                                          'width_m': 0.05}],
                        coil={'inner_radius_m': 0.15, 'outer_radius_m': 0.6,
                              'winding_tension_pa': 30e6, 'compaction_factor': 0.5},
                        events=[{'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [18],
                                 'level': 0.0}],
                        deflector_roll_radius_m=0.125)
        w['roll']['barrel_length_m'] = FOIL_NOZZLES_BARREL
        w['spray_header'] = dict(FOIL_HEADER)
        c['width_model'] = w
    return c


def _nozzle(i):
    from physicroll.roll_thermal import SprayHeader
    return SprayHeader(**FOIL_HEADER).nozzle_positions(FOIL_NOZZLES_BARREL)[i]


class NoBiteWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        obs = dict(orientation='longitudinal', band_positions_across_width_m=[
            round(_nozzle(11), 3)], visible_only_after_tension_release=True,
            lengthwise_continuity='both', intermittent_duration_s=60.0,
            appearance='loose_or_buckle', positions_repeat_across_coils=True)
        cls.case = foil_case(**obs)
        cls.r = diagnose(cls.case)
        si = foil_case(**obs)
        si['width_model']['shape_inputs'] = dict(SHAPE_INPUTS)
        cls.si = diagnose(si)
        no_heat = foil_case(**obs)
        no_heat['width_model']['bite_heat_per_width_w_m'] = None
        cls.no_heat = diagnose(no_heat)

    def test_width_section_runs_without_a_bite(self):
        r = self.r
        self.assertIsNone(r['bite'])
        self.assertIn('sticking', r['bite_error'])
        w = r['width']
        self.assertEqual(w['status'], 'SCREENING_RESULT_NOT_PLANT_VALIDATED')
        self.assertEqual(w['failures'], [])
        # parts that need no bite
        for span in ('entry_span', 'exit_span'):
            self.assertNotEqual(w['troughs'][span]['status'], 'REJECTED')
            self.assertGreater(w['troughs'][span]['wrinkle_wavelength_m'], 0)
        self.assertIn('blocked_or_low_level_nozzles', w['positions']['predicted_positions_m'])
        self.assertTrue(w['positions']['position_matches'])
        self.assertGreater(w['thermal_steady']['thermal_crown_m'], 0)
        self.assertTrue(w['thermal_steady']['stripes'])
        ridge = w['shape']['ridges'][0]
        self.assertEqual(ridge['transfer_basis'], 'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE')
        self.assertAlmostEqual(ridge['exit_to_entry_ridge_ratio'], 0.5)
        self.assertIsNotNone(ridge['coil']['critical_ridge_height_at_outer_radius_m'])
        rows = w['gauge_trend']['rows']
        self.assertTrue(all(x['critical_ridge_height_m'] > 0 for x in rows))
        self.assertTrue(all(x['trough_critical_lateral_stress_pa'] < 0 for x in rows))
        # the thicker pass has its own (Hitchcock) bite; the case pass has none
        self.assertNotIn('rejected', rows[0])
        self.assertIn('NOT_ASSESSABLE', rows[1]['rejected'])
        self.assertIn('sticking', rows[1]['rejected'])
        # shape parts individually not assessable, with the bite error as the reason
        sc = w['shape_chain']
        self.assertEqual(sc['status'], 'NOT_ASSESSABLE')
        self.assertIn('sticking', sc['reason'])
        for part in (w['shape']['steady'], w['shape']['nozzle_pattern_ripple']):
            self.assertEqual(part['status'], 'NOT_ASSESSABLE')
            self.assertIn('sticking', part['reason'])
        ev = w['thermal_events']['events'][0]
        self.assertIn('NOT_ASSESSABLE', ev['shape_error'])
        self.assertIsNone(ev['manifest_threshold_m'])
        self.assertIn('WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE', r['flags'])
        json.dumps(r, allow_nan=False)

    def test_missing_model_parts_never_contradict(self):
        for h in self.r['hypotheses']:
            if h['family'] != 'lengthwise':
                continue
            for e in h['evidence']:
                if e['basis'] in ('model', 'model not assessable'):
                    self.assertNotEqual(e['verdict'], 'CONTRADICTS', (h['id'], e))
        nz = _h(self.r)['nozzle_thermal_stripe']
        by = {e['criterion']: e for e in nz['evidence']}
        band = by['model band at an observed position above the reporting threshold']
        self.assertEqual((band['verdict'], band['basis']), ('NEUTRAL', 'model not assessable'))
        rel = by['visible only after tension release vs steady model band']
        self.assertEqual((rel['verdict'], rel['basis']), ('NEUTRAL', 'model not assessable'))
        # the blocked nozzle position still supports (needs no bite)
        pos = by['band positions vs model stripes / blocked or low-level nozzles']
        self.assertEqual((pos['verdict'], pos['weight']), ('SUPPORTS', 'strong'))
        zone = {e['criterion']: e for e in _h(self.r)['cooling_zone_switching_transient'][
            'evidence']}
        dur = zone['intermittent duration vs model visible time']
        self.assertEqual((dur['verdict'], dur['basis']), ('NEUTRAL', 'model not assessable'))
        ridge = {e['criterion']: e for e in _h(self.r)['incoming_ridge_coil_buildup']['evidence']}
        self.assertIn(ridge['model coil build-up of a supplied ridge']['verdict'],
                      ('SUPPORTS', 'NEUTRAL'))

    def test_without_bite_heat_thermal_not_assessable_rest_runs(self):
        w = self.no_heat['width']
        self.assertEqual(w['thermal_steady']['status'], 'NOT_ASSESSABLE')
        self.assertIn('bite heat', w['thermal_steady']['reason'])
        self.assertEqual(w['thermal_events']['status'], 'NOT_ASSESSABLE')
        self.assertIn('wrinkle_wavelength_m', w['troughs']['exit_span'])
        self.assertEqual(w['positions']['predicted_positions_m']['steady_stripes'], [])
        self.assertEqual(len(w['gauge_trend']['rows']), 2)
        nz = {e['criterion']: e for e in _h(self.no_heat)['nozzle_thermal_stripe']['evidence']}
        pos = nz['band positions vs model stripes / blocked or low-level nozzles']
        self.assertEqual(pos['verdict'], 'SUPPORTS')
        self.assertIn('no roll thermal solution', pos['observed'])
        self.assertIn('WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT', self.no_heat['flags'])
        html = render_band_report(self.no_heat)
        self.assertIn('not assessable', html)

    def test_shape_inputs_supplied(self):
        w = self.si['width']
        self.assertIn('SHAPE_INPUTS_SUPPLIED', self.si['flags'])
        self.assertEqual(w['shape_chain']['status'], 'EVALUATED')
        self.assertEqual(w['shape_chain']['basis'], 'shape_inputs_supplied')
        used = w['inputs_used']
        for k in ('strip_stiffness_per_width_pa', 'exit_tension_force_sensitivity_per_width_m',
                  'bite_half_length_m'):
            self.assertEqual(used[k], SHAPE_INPUTS[k])
        self.assertIn('linear_feedback_peak_i_units', w['shape']['steady'])
        self.assertTrue(w['shape']['steady_stripe_table'])
        rows = w['gauge_trend']['rows']
        self.assertEqual(rows[1]['shape_inputs_basis'], 'shape_inputs_supplied')
        self.assertEqual(rows[0]['shape_inputs_basis'], 'derived_bite')
        self.assertIsNone(rows[1]['bite_model'])
        self.assertEqual(rows[0]['bite_model'], 'hitchcock')
        ev = w['thermal_events']['events'][0]
        self.assertNotIn('shape_error', ev)
        # the ridge transfer still needs the bite's entry force sensitivity
        self.assertEqual(w['shape']['ridges'][0]['transfer_basis'],
                         'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE')
        nz = {e['criterion']: e for e in _h(self.si)['nozzle_thermal_stripe']['evidence']}
        self.assertEqual(nz['model band at an observed position above the reporting '
                            'threshold']['basis'], 'model')
        html = render_band_report(self.si)
        self.assertIn('SUPPLIED shape inputs', html)
        self.assertIn('&lt;b&gt;&amp;&lt;/b&gt;', html)
        self.assertNotIn('<b>&</b>', html)

    def test_shape_inputs_validation(self):
        c = foil_case()
        for bad, word in (({**SHAPE_INPUTS, 'extra': 1.0}, 'unknown'),
                          ({**SHAPE_INPUTS, 'strip_stiffness_per_width_pa': -1.0}, '> 0'),
                          ({**SHAPE_INPUTS, 'bite_half_length_m': 0.5}, '<='),
                          ({**SHAPE_INPUTS, 'provenance': ' '}, 'provenance')):
            c2 = copy.deepcopy(c)
            c2['width_model']['shape_inputs'] = bad
            with self.assertRaises(ValueError) as cm:
                validate_case(c2)
            self.assertIn(word, str(cm.exception))

    def test_foil_regime_block_without_bite(self):
        fr = self.r['foil_regime']
        self.assertIn(CLOSED_GAP_FLAG, self.r['flags'])
        self.assertEqual(fr['exit_thickness_m'], 30e-6)
        self.assertEqual(fr['case_position'], 'BELOW_EVERY_REPORTED_ONSET')
        self.assertIsNone(fr['bite']['model'])
        self.assertIn('sticking', fr['bite']['bite_error'])
        self.assertEqual(fr['wrinkle_rule']['comparison'], 'MODEL_BAND_NOT_ASSESSABLE')
        self.assertAlmostEqual(fr['wrinkle_rule']['wrinkle_onset_i_units'],
                               1e5 * 40e6 / 70e9)
        self.assertEqual(fr['schedule_bites'][0]['bite_model'], 'hitchcock')
        self.assertIn('sticking', fr['schedule_bites'][1]['rejected'])

    def test_determinism_and_report(self):
        again = diagnose(self.case)
        self.assertEqual(result_json(self.r), result_json(again))
        html = render_band_report(self.r)
        self.assertEqual(html, render_band_report(again))
        self.assertIn('class="foil"', html)
        self.assertIn('closed-gap rolling likely', html)
        self.assertIn('Strip-shape chain not assessable', html)
        for bad in ('nan', 'inf'):
            self.assertIsNone(__import__('re').search(rf'>\s*-?{bad}\b', html.lower()))


class FoilRulesTests(unittest.TestCase):
    """Unit-level rule branches on Facts built from a validated case (no width section)."""

    def facts(self, h1=35e-6, **obs):
        c = foil_case(h0=2 * h1, h1=h1, schedule=False, width=False,
                      **dict({'orientation': 'longitudinal'}, **obs))
        return bw.Facts(validate_case(c), None, None, None)

    def ev(self, builder, crit, **kw):
        f = kw.pop('facts', None) or self.facts(**kw)
        e, _ = builder(f)
        return {x['criterion']: x for x in e}[crit]

    def vw(self, x):
        return (x['verdict'], x['weight'])

    def test_tension_lines_rules(self):
        T, crit = bw._h_tension_lines, 'band spacing 3-30 mm'
        self.assertEqual(self.vw(self.ev(T, crit, band_spacing_m=0.01)), ('SUPPORTS', 'strong'))
        self.assertEqual(self.vw(self.ev(T, crit, band_spacing_m=0.08)),
                         ('CONTRADICTS', 'moderate'))
        self.assertEqual(self.vw(self.ev(T, crit, band_spacing_m=0.04)), ('NEUTRAL', None))
        self.assertEqual(self.vw(self.ev(T, crit, band_positions_across_width_m=[0.5, 0.51,
                                                                                 0.52])),
                         ('SUPPORTS', 'strong'))
        g = 'exit gauge (tension lines on thin foil)'
        for h1, want in ((25e-6, ('SUPPORTS', 'moderate')), (45e-6, ('SUPPORTS', 'weak')),
                         (80e-6, ('NEUTRAL', None)), (0.21e-3, ('CONTRADICTS', 'moderate'))):
            x = self.ev(T, g, h1=h1, band_spacing_m=0.01)
            self.assertEqual(self.vw(x), want, h1)
            self.assertEqual(x['basis'], 'input')
        # rule change: without a band-specific supporting observation the gauge support is
        # reported NEUTRAL (orientation alone must not let the case gauge decide); a gauge
        # contradiction stays
        x = self.ev(T, g, h1=25e-6)
        self.assertEqual(self.vw(x), ('NEUTRAL', None))
        self.assertIn('counted only with', x['observed'])
        self.assertEqual(self.vw(self.ev(T, g, h1=0.21e-3)), ('CONTRADICTS', 'moderate'))
        w = 'worse at lower tension'
        self.assertEqual(self.vw(self.ev(T, w, worse_at_lower_tension=True)),
                         ('SUPPORTS', 'strong'))
        self.assertEqual(self.vw(self.ev(T, w, worse_at_lower_tension=False)),
                         ('CONTRADICTS', 'strong'))
        t = 'changes with tension'
        self.assertEqual(self.vw(self.ev(T, t, changes_with_tension=True)),
                         ('SUPPORTS', 'moderate'))
        self.assertEqual(self.vw(self.ev(T, t, changes_with_tension=True,
                                         worse_at_lower_tension=True)), ('NEUTRAL', None))
        for key, crit2 in (('changes_with_ironing_roll_pressure',
                            'changes with ironing-roll pressure'),
                           ('changes_with_exit_air_blowoff', 'changes with exit air blow-off')):
            self.assertEqual(self.vw(self.ev(T, crit2, **{key: True})),
                             ('SUPPORTS', 'moderate'))
        self.assertEqual(self.vw(self.ev(T, 'positions repeat across coils',
                                         positions_repeat_across_coils=False)),
                         ('SUPPORTS', 'weak'))
        for a, want in (('gloss_or_shade', 'SUPPORTS'), ('crease_or_flute', 'SUPPORTS'),
                        ('loose_or_buckle', 'CONTRADICTS'), ('stain', 'CONTRADICTS')):
            self.assertEqual(self.vw(self.ev(T, 'appearance', appearance=a)), (want, 'weak'))
        self.assertEqual(self.vw(self.ev(T, 'worse at thinner gauge',
                                         worse_at_thinner_gauge=True)), ('SUPPORTS', 'weak'))
        self.assertEqual(self.vw(self.ev(T, 'orientation', orientation='transverse')),
                         ('CONTRADICTS', 'strong'))
        # missing observations never contradict
        e, pred = T(self.facts(orientation=None))
        for x in e:
            if x['basis'] == 'observation':
                self.assertEqual(x['verdict'], 'NOT_OBSERVED', x)
        self.assertIn('rule-based', pred['model'])

    def test_extended_rules(self):
        N, R, TR, HS = (bw._h_nozzle, bw._h_roll_surface, bw._h_troughs,
                        bw._h_heat_streak)
        self.assertEqual(self.vw(self.ev(N, 'tracks speed changes', tracks_speed_changes=True)),
                         ('NEUTRAL', None))
        self.assertEqual(self.vw(self.ev(N, 'changes after roll wiper cleaning',
                                         changes_after_roll_wiper_cleaning=True)),
                         ('CONTRADICTS', 'weak'))
        wc = 'changes after roll wiper cleaning'
        self.assertEqual(self.vw(self.ev(R, wc, changes_after_roll_wiper_cleaning=True)),
                         ('SUPPORTS', 'strong'))
        self.assertEqual(self.vw(self.ev(R, wc, changes_after_roll_wiper_cleaning=False)),
                         ('CONTRADICTS', 'weak'))
        self.assertEqual(self.vw(self.ev(R, 'appeared after a narrower coil',
                                         appeared_after_narrower_coil=True)),
                         ('SUPPORTS', 'strong'))
        self.assertEqual(self.vw(self.ev(R, 'disappears after backup-roll change',
                                         disappears_after_backup_roll_change=True)),
                         ('SUPPORTS', 'moderate'))
        wr = 'positions change / band disappears after work-roll change'
        self.assertEqual(self.vw(self.ev(R, wr, positions_change_after_work_roll_change=False)),
                         ('CONTRADICTS', 'strong'))
        x = self.ev(R, wr, positions_change_after_work_roll_change=False,
                    disappears_after_backup_roll_change=True)
        self.assertEqual(self.vw(x), ('CONTRADICTS', 'weak'))
        self.assertIn('backup-roll', x['observed'])
        self.assertEqual(self.vw(self.ev(R, wr, disappears_after_work_roll_change=False,
                                         disappears_after_backup_roll_change=True)),
                         ('CONTRADICTS', 'weak'))
        self.assertEqual(self.vw(self.ev(TR, 'changes with ironing-roll pressure',
                                         changes_with_ironing_roll_pressure=True)),
                         ('SUPPORTS', 'moderate'))
        g = 'exit gauge (creasing possible below 50 um)'
        self.assertEqual(self.vw(self.ev(TR, g, h1=30e-6, appearance='crease_or_flute')),
                         ('SUPPORTS', 'weak'))
        self.assertEqual(self.vw(self.ev(TR, g, h1=30e-6)), ('NEUTRAL', None))
        self.assertEqual(self.vw(self.ev(TR, g, h1=0.2e-3)), ('NEUTRAL', None))
        self.assertEqual(self.vw(self.ev(TR, 'worse at lower tension',
                                         worse_at_lower_tension=True)), ('CONTRADICTS', 'weak'))
        ts = 'tracks speed changes'
        self.assertEqual(self.vw(self.ev(HS, ts, tracks_speed_changes=True)),
                         ('SUPPORTS', 'strong'))
        self.assertEqual(self.vw(self.ev(HS, ts, tracks_speed_changes=False)),
                         ('CONTRADICTS', 'weak'))
        self.assertEqual(self.vw(self.ev(HS, 'changes with exit air blow-off',
                                         changes_with_exit_air_blowoff=True)), ('NEUTRAL', None))
        fr = 'film ratio at the operating point (0.3-3: friction sensitive to local differences)'
        f = self.facts()
        self.assertEqual(self.ev(HS, fr, facts=f)['verdict'], 'NOT_OBSERVED')
        f.film_ratio, f.film_basis = 1.0, 'unit test'
        x = self.ev(HS, fr, facts=f)          # orientation only: gated to NEUTRAL
        self.assertEqual(self.vw(x), ('NEUTRAL', None))
        self.assertIn('counted only with', x['observed'])
        f = self.facts(tracks_speed_changes=True)
        for lam, want in ((1.0, ('SUPPORTS', 'weak')), (5.0, ('NEUTRAL', None)),
                          (0.1, ('NEUTRAL', None))):
            f.film_ratio, f.film_basis = lam, 'unit test'
            self.assertEqual(self.vw(self.ev(HS, fr, facts=f)), want, lam)

    def test_next_measurements_for_foil(self):
        lines = bw.lengthwise_next_measurements(dict(V2_NULL_OBS, **{
            k: None for k in bw.OBS_FOIL_BOOL}), 35e-6)
        text = ' '.join(lines)
        for word in ('Step the exit tension', 'ironing-roll pressure', 'Clean the roll wipers',
                     'mill speed changes', 'wider coil followed a narrower',
                     'offline sag'):
            self.assertIn(word, text)
        sheet = ' '.join(bw.lengthwise_next_measurements(dict(V2_NULL_OBS), 0.21e-3))
        self.assertNotIn('Step the exit tension', sheet)


class TensionLinesPlantedTruthTests(unittest.TestCase):
    def test_tension_lines_lead(self):
        # 50 -> 25 um battery foil, regular 10 mm lines, worse at low tension, react to the
        # ironing roll and the exit blow-off, wander between coils: no width model, no bite
        pos = [0.40 + 0.010 * i for i in range(6)]
        c = foil_case(h0=50e-6, h1=25e-6, schedule=False, width=False,
                      orientation='longitudinal', band_positions_across_width_m=pos,
                      band_spacing_m=0.010, worse_at_lower_tension=True,
                      changes_with_ironing_roll_pressure=True,
                      changes_with_exit_air_blowoff=True, positions_repeat_across_coils=False,
                      appearance='gloss_or_shade', worse_at_thinner_gauge=True,
                      lengthwise_continuity='continuous')
        r = diagnose(c)
        self.assertEqual(r['leading_hypotheses'], ['foil_tension_lines'])
        h = _h(r)['foil_tension_lines']
        self.assertIn('rule-based', h['model_prediction']['model'])
        self.assertIn(CLOSED_GAP_FLAG, r['flags'])


    def test_orientation_and_gauge_alone_do_not_lead(self):
        # planted blocked nozzle on foil, but no width model / coolant data: only the
        # orientation and one position are known, so nothing may lead on the case gauge
        c = foil_case(h0=50e-6, h1=25e-6, schedule=False, width=False,
                      orientation='longitudinal', band_positions_across_width_m=[0.62])
        r = diagnose(c)
        self.assertEqual(r['leading_hypotheses'], [])
        c['tribology'] = dict(TRIBOLOGY)      # film ratio / regime alone must not lead either
        self.assertEqual(diagnose(c)['leading_hypotheses'], [])


class CasePassIdentityTests(unittest.TestCase):
    """Review finding: a schedule row is the case pass only if every bite-defining parameter
    matches (gauges, flow stress, friction, tensions), not just the gauges."""

    def row(self, c, **kw):
        p = c['pass']
        r = {k: p[k] for k in ('entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
                               'friction_coefficient', 'entry_tension_pa', 'exit_tension_pa',
                               'exit_speed_m_s')}
        r['label'] = 'row'
        r.update(kw)
        return r

    def test_same_gauges_other_friction_gets_its_own_bite(self):
        # 0.12 -> 0.084 mm, 285 MPa, max_radius_ratio 2: friction 0.03 fails (R'/R 2.56),
        # the same gauges at friction 0.02 solve
        c = v2(override=False, orientation='longitudinal')
        c['pass'].update(entry_thickness_m=0.12e-3, exit_thickness_m=0.084e-3,
                         mean_flow_stress_pa=285e6, friction_coefficient=0.03)
        c['model_options']['max_radius_ratio'] = 2.0
        c['schedule'] = [self.row(c, label='same gauges mu 0.02', friction_coefficient=0.02),
                         self.row(c, label='identical to the case pass', exit_speed_m_s=8.0)]
        c['width_model'] = width_model(bite_heat_per_width_w_m=3e5)
        r = diagnose(c)
        self.assertIsNotNone(r['bite_error'])
        self.assertNotIn('rejected', r['schedule_sweep']['rows'][0])
        rows = r['width']['gauge_trend']['rows']
        self.assertNotIn('rejected', rows[0])
        self.assertEqual(rows[0]['bite_model'], 'hitchcock')
        self.assertEqual(rows[0]['shape_inputs_basis'], 'derived_bite')
        self.assertGreater(rows[0]['linear_feedback_i_units'], 0)
        # identical in every bite parameter (exit speed is not one): the case pass
        self.assertIn('NOT_ASSESSABLE', rows[1]['rejected'])
        self.assertIn('no bite response for the case pass', rows[1]['rejected'])

    def test_shape_inputs_only_for_the_identical_row(self):
        c = foil_case(schedule=False)
        c['width_model']['shape_inputs'] = dict(SHAPE_INPUTS)
        eff = validate_case(c)
        self.assertTrue(bw.is_case_pass(eff, None))
        self.assertTrue(bw.is_case_pass(eff, self.row(eff, exit_speed_m_s=5.0)))
        w = eff['width_model']
        same = self.row(eff)
        sp, basis = bw.shape_params_or_none(eff, None, w, same)
        self.assertEqual(basis, 'shape_inputs_supplied')
        self.assertEqual(sp['strip_stiffness_per_width_pa'],
                         SHAPE_INPUTS['strip_stiffness_per_width_pa'])
        for k, v in (('exit_tension_pa', 30e6), ('entry_tension_pa', 30e6),
                     ('mean_flow_stress_pa', 180e6), ('friction_coefficient', 0.04)):
            other = self.row(eff, **{k: v})
            self.assertFalse(bw.is_case_pass(eff, other), k)
            self.assertEqual(bw.shape_params_or_none(eff, None, w, other), (None, None), k)


class ZoneDurationFallbackTests(unittest.TestCase):
    """Review finding: the literature band-life comparison only when no events were supplied;
    simulated events without a reportable band give NEUTRAL (basis model), never support."""
    CRIT = 'intermittent duration vs model visible time'

    def crit(self, events, d=60.0):
        f = bw.Facts(validate_case(v2(orientation='longitudinal', intermittent_duration_s=d)),
                     None, None, None)
        f.events = events
        e, _ = bw._h_zone(f)
        return {x['criterion']: x for x in e}[self.CRIT], e

    def test_event_below_reporting_threshold_is_neutral(self):
        # reviewer's reproducer: 2 s event on nozzle 16 at level 0.999, observed 60 s band
        c = v2(orientation='longitudinal', intermittent_duration_s=60.0)
        c['width_model'] = width_model(events=[{'start_s': 0.0, 'duration_s': 2.0,
                                                'nozzle_indices': [16], 'level': 0.999}])
        r = diagnose(c)
        ev0 = r['width']['thermal_events']['events'][0]
        self.assertEqual(ev0['peak_state_with_feedback'], 'BELOW_REPORTING_THRESHOLD')
        self.assertIsNone(ev0['visible_time_s'])
        h = _h(r)['cooling_zone_switching_transient']
        x = {e['criterion']: e for e in h['evidence']}[self.CRIT]
        self.assertEqual((x['verdict'], x['weight'], x['basis']), ('NEUTRAL', None, 'model'))
        self.assertNotIn('no model events', x['observed'])
        self.assertIn('BELOW_REPORTING_THRESHOLD', x['observed'])
        self.assertEqual(h['score'], 2)       # was 3 with the literature support point

    def test_mixed_events_and_no_events(self):
        below = {'index': 0, 'label': 'small', 'peak_state_with_feedback':
                 'BELOW_REPORTING_THRESHOLD', 'peak_state_after_tension_release':
                 'BELOW_REPORTING_THRESHOLD', 'visible_time_s': None,
                 'visible_time_lower_bound_s': None}
        broken = {'index': 1, 'label': 'broken', 'shape_error': 'shape failed: test',
                  'peak_state_with_feedback': None, 'peak_state_after_tension_release': None,
                  'visible_time_s': None, 'visible_time_lower_bound_s': None}
        x, _ = self.crit([below, broken])
        self.assertEqual((x['verdict'], x['basis']), ('NEUTRAL', 'model'))
        self.assertIn('shape failed: test', x['observed'])
        self.assertIn('small: BELOW_REPORTING_THRESHOLD', x['observed'])
        x, _ = self.crit([broken])          # all shape errors: unchanged branch
        self.assertEqual((x['verdict'], x['basis']), ('NEUTRAL', 'model not assessable'))
        x, _ = self.crit([])                # no events supplied: literature comparison
        self.assertEqual((x['verdict'], x['weight']), ('SUPPORTS', 'weak'))
        self.assertIn('no model events', x['observed'])
        x, _ = self.crit([], d=1000.0)
        self.assertEqual(x['verdict'], 'NEUTRAL')
        vis = dict(below, visible_time_s=50.0, visible_time_basis='in_mill_manifest')
        x, _ = self.crit([vis])             # visible time: unchanged
        self.assertEqual((x['verdict'], x['weight'], x['basis']),
                         ('SUPPORTS', 'moderate', 'model'))
        x, _ = self.crit([vis], d=500.0)
        self.assertEqual((x['verdict'], x['basis']), ('NEUTRAL', 'model'))


class SuppliedBiteGaugeTrendTests(unittest.TestCase):
    def test_case_pass_row_keeps_the_supplied_bite(self):
        # review finding: with a supplied bite and no shape_inputs the case-pass gauge-trend
        # row re-derived a Hitchcock bite (8.11 GPa) while the steady shape used the supplied
        # one (16.23 GPa with F_h doubled)
        c = v2(orientation='longitudinal')
        o = c['model_options']['bite_response_override']
        o['dforce_dexit_thickness_n_m'] *= 2
        p = c['pass']
        c['schedule'] = [
            {'label': 'thicker', 'entry_thickness_m': 0.9e-3, 'exit_thickness_m': 0.6e-3,
             'mean_flow_stress_pa': 240e6, 'friction_coefficient': 0.05,
             'entry_tension_pa': 20e6, 'exit_tension_pa': 25e6, 'exit_speed_m_s': 8.0},
            dict({k: p[k] for k in ('entry_thickness_m', 'exit_thickness_m',
                                    'mean_flow_stress_pa', 'friction_coefficient',
                                    'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s')},
                 label='case pass row')]
        c['width_model'] = width_model(blocked_nozzle_indices=[12])
        r = diagnose(c)
        w = r['width']
        steady_q = w['inputs_used']['strip_stiffness_per_width_pa']
        self.assertAlmostEqual(steady_q, -o['dforce_dexit_thickness_n_m'] / p['width_m'])
        rows = w['gauge_trend']['rows']
        self.assertEqual(rows[1]['strip_stiffness_per_width_pa'], steady_q)
        self.assertEqual(rows[1]['bite_source'], 'supplied')
        self.assertEqual(rows[1]['bite_model'], 'supplied')
        self.assertEqual(rows[0]['bite_source'], 'derived_slab_hitchcock')
        self.assertNotEqual(rows[0]['strip_stiffness_per_width_pa'], steady_q)


class SuppliedBiteScheduleTablesTests(unittest.TestCase):
    """Review finding: with a supplied bite, the schedule sweep, heating and friction rows of
    the case pass used a freshly derived bite instead of the supplied operating bite."""

    def test_case_pass_rows_use_the_supplied_bite(self):
        c = v2(orientation='longitudinal')
        o = c['model_options']['bite_response_override']
        o['dforce_dexit_thickness_n_m'] *= 2
        p = c['pass']
        c['schedule'] = [
            {'label': 'thicker', 'entry_thickness_m': 0.9e-3, 'exit_thickness_m': 0.6e-3,
             'mean_flow_stress_pa': 240e6, 'friction_coefficient': 0.05,
             'entry_tension_pa': 20e6, 'exit_tension_pa': 25e6, 'exit_speed_m_s': 8.0},
            dict({k: p[k] for k in ('entry_thickness_m', 'exit_thickness_m',
                                    'mean_flow_stress_pa', 'friction_coefficient',
                                    'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s')},
                 label='case pass row')]
        c['tribology'] = dict(TRIBOLOGY)
        r = diagnose(c)
        q_sup = -o['dforce_dexit_thickness_n_m']
        self.assertAlmostEqual(r['bite']['strip_modulus_n_m'], q_sup)
        thick, same = r['schedule_sweep']['rows']
        self.assertEqual(same['strip_modulus_n_m'], r['bite']['strip_modulus_n_m'])
        self.assertEqual(same['separating_force_n'], r['bite']['separating_force_n'])
        self.assertEqual(same['bite_model'], 'supplied')
        uc = r['chatter']['with_bite_damping']['critical_exit_speed_m_s']
        self.assertEqual(same['critical_exit_speed_m_s'], uc)
        self.assertEqual(same['at_case_friction']['critical_exit_speed_m_s'], uc)
        self.assertEqual(thick['bite_model'], 'hitchcock')
        heat = r['process']['heating']
        self.assertEqual(heat['schedule'][1], dict(heat['operating'], label='case pass row'))
        self.assertIn('Hitchcock', heat['schedule'][0]['friction_power_basis'])
        fr = r['process']['friction']
        self.assertEqual(fr['operating']['bite_source'], 'supplied')
        self.assertEqual(fr['schedule'][1]['bite_source'], 'supplied')
        self.assertEqual(fr['schedule'][0]['bite_source'], 'derived_slab_hitchcock')


class SensitivityMixFlagTests(unittest.TestCase):
    def test_flag_only_with_a_supplied_bite(self):
        flag = 'FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE'
        for override in (True, False):
            c = v2(override=override, orientation='longitudinal')
            c['tribology'] = dict(TRIBOLOGY)
            c['gauge_control'] = {'compensation_gain': 0.9, 'bandwidth_hz': 25.0,
                                  'force_filter_hz': None}
            c['incoming_variation'] = {'flow_stress_variation_fraction': 0.02,
                                       'coil_synchronous': False}
            r = diagnose(c)
            gc, iv = r['gauge_control'], r['incoming_variation']
            sc = gc['speed_change_gauge_shift']
            for sec in (gc, iv, sc):
                self.assertEqual(flag in (sec.get('flags') or []), override, override)
            self.assertEqual(flag in r['flags'], override)
            if override:
                for text in (gc['limitations'][-1], iv['limitations'][0], sc['note']):
                    self.assertIn('may be inconsistent', text)
                self.assertIn(flag, render_band_report(r))
            else:
                self.assertNotIn('limitations', iv)
                self.assertNotIn('note', sc)


class FinalPassDoubledTests(unittest.TestCase):
    """Plant answer: the 16-18 um final pass is rolled single-sheet
    (material.final_pass_doubled false); null keeps the question, true flags a doubled pass."""
    FLAG = 'DOUBLED_FINAL_PASS_NOT_MODELLED'
    QUESTION = 'Ask the plant: single-sheet or doubled?'
    PRODUCT_Q = 'Ask also whether the last pass is single-sheet or doubled'

    @classmethod
    def setUpClass(cls):
        # 35 um case pass with an 18 um schedule row below the bite floor; no width model
        # (the foil block does not need it), friction 0.05 so no bite is solved (fast)
        cls.r = {}
        for value in ('absent', None, False, True):
            c = foil_case(h0=60e-6, h1=35e-6, width=False, orientation='longitudinal')
            c['schedule'][1]['entry_thickness_m'] = 60e-6
            c['schedule'][1]['exit_thickness_m'] = 35e-6
            c['schedule'].append(dict(c['schedule'][1], label='P4 0.035->0.018 mm',
                                      entry_thickness_m=35e-6, exit_thickness_m=18e-6))
            if value != 'absent':
                c['material']['final_pass_doubled'] = value
            cls.r[value] = diagnose(c)

    def test_absent_and_null_keep_the_question(self):
        a, n = self.r['absent']['foil_regime'], self.r[None]['foil_regime']
        self.assertEqual(a, n)
        self.assertNotIn('final_pass_doubled', a)
        self.assertIn(self.QUESTION, a['below_bite_model_floor']['text'])
        self.assertIn(self.PRODUCT_Q, a['product_question']['text'])
        self.assertEqual(len(a['implications']), 5)
        self.assertNotIn('final_pass_doubled', self.r['absent']['inputs']['material'])

    def test_single_sheet_stated(self):
        fr = self.r[False]['foil_regime']
        self.assertIs(fr['final_pass_doubled'], False)
        floor, prod = fr['below_bite_model_floor']['text'], fr['product_question']['text']
        self.assertNotIn(self.QUESTION, floor)
        self.assertNotIn(self.PRODUCT_Q, prod)
        self.assertIn('rolled single-sheet', floor)
        self.assertIn('limit of the tool', floor)
        self.assertIn('[V S8, S16, S17]', floor)
        self.assertIn('final pass is rolled single-sheet', prod)
        self.assertEqual(len(fr['implications']), 6)
        self.assertIn('observation.faces', fr['implications'][-1])
        self.assertIn('[D]', fr['implications'][-1])
        self.assertNotIn(self.FLAG, fr['flags'])
        self.assertNotIn(self.FLAG, self.r[False]['flags'])
        html = render_band_report(self.r[False])
        self.assertIn('rolled single-sheet', html)
        self.assertNotIn(self.QUESTION, html)

    def test_doubled_stated(self):
        r = self.r[True]
        fr = r['foil_regime']
        self.assertIs(fr['final_pass_doubled'], True)
        self.assertIn(self.FLAG, fr['flags'])
        self.assertIn(self.FLAG, r['flags'])
        self.assertIn('matte sheet-to-sheet face', fr['implications'][-1])
        self.assertNotIn(self.QUESTION, fr['below_bite_model_floor']['text'])
        self.assertIn(self.FLAG, render_band_report(r))
        # no numeric change against the unstated case
        self.assertEqual(r['hypotheses'], self.r[None]['hypotheses'])
        self.assertEqual(r['schedule_sweep'], self.r[None]['schedule_sweep'])

    def test_validation_and_sheet_gauge(self):
        c = foil_case(width=False)
        for bad in ('no', 0, 1.0):
            c['material']['final_pass_doubled'] = bad
            with self.assertRaises(ValueError) as cm:
                validate_case(c)
            self.assertIn('final_pass_doubled', str(cm.exception))
        v1 = json.loads((SCEN / 'band_diagnosis_thin_gauge_chatter.json').read_text())
        v1['material']['final_pass_doubled'] = None
        self.assertNotIn('final_pass_doubled', validate_case(v1)['material'])
        v1['material']['final_pass_doubled'] = False
        with self.assertRaises(ValueError):
            validate_case(v1)
        sheet = v2(orientation='longitudinal')
        sheet['material']['final_pass_doubled'] = True
        r = diagnose(sheet)
        self.assertIsNone(r['foil_regime'])
        self.assertNotIn(self.FLAG, r['flags'])

    def test_foil_demo_states_single_sheet(self):
        demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
        self.assertIs(demo['material']['final_pass_doubled'], False)
        self.assertNotIn('Ask the plant whether this pass', ' '.join(demo['notes']))


class CollectorFoilBelowFloorTests(unittest.TestCase):
    """SPEC9 addendum: a 0.030 -> 0.017 mm case pass (below the 20 um roll-bite floor)."""

    @classmethod
    def setUpClass(cls):
        pos = [0.40 + 0.010 * i for i in range(6)]
        c = foil_case(friction=0.03, h0=30e-6, h1=17e-6, orientation='longitudinal',
                      band_positions_across_width_m=pos, band_spacing_m=0.010,
                      worse_at_lower_tension=True, changes_with_ironing_roll_pressure=True,
                      changes_with_exit_air_blowoff=True, positions_repeat_across_coils=False,
                      appearance='gloss_or_shade', worse_at_thinner_gauge=True,
                      lengthwise_continuity='continuous')
        c['tribology'] = dict(TRIBOLOGY)
        c['width_model']['roll_heat_fraction_per_roll'] = None
        cls.case = c
        cls.r = diagnose(c)

    def test_loads_diagnoses_and_flags(self):
        r = self.r
        validate_case(self.case)
        self.assertIsNone(r['bite'])
        self.assertIn('20 um floor', r['bite_error'])
        self.assertIn(BITE_FLOOR_FLAG, r['flags'])
        self.assertIn(CLOSED_GAP_FLAG, r['flags'])
        for key in ('chatter', 'levers'):
            self.assertEqual(r[key]['status'], 'NOT_ASSESSABLE')
            self.assertIn('20 um floor', r[key]['reason'])
        fl = r['foil_regime']['below_bite_model_floor']
        self.assertTrue(fl['case_pass_below_floor'])
        self.assertIn('gauge-control', fl['text'])
        self.assertIn('single-sheet or doubled', fl['text'])
        w = r['width']
        self.assertEqual(w['shape_chain']['status'], 'NOT_ASSESSABLE')
        self.assertIn('20 um floor', w['shape_chain']['reason'])
        self.assertIn('wrinkle_wavelength_m', w['troughs']['exit_span'])
        self.assertTrue(w['thermal_steady']['stripes'])
        self.assertTrue(w['positions']['position_matches'])
        self.assertEqual(w['shape']['ridges'][0]['transfer_basis'],
                         'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE')
        rows = w['gauge_trend']['rows']
        self.assertIn('20 um floor', rows[-1]['rejected'])
        self.assertGreater(rows[-1]['critical_ridge_height_m'], 0)
        json.dumps(r, allow_nan=False)

    def test_tension_lines_lead_and_no_model_contradiction(self):
        r = self.r
        self.assertEqual(r['leading_hypotheses'], ['foil_tension_lines'])
        g = {e['criterion']: e for e in _h(r)['foil_tension_lines']['evidence']}
        self.assertEqual(g['exit gauge (tension lines on thin foil)']['verdict'], 'SUPPORTS')
        for h in r['hypotheses']:
            if h['family'] == 'lengthwise':
                for e in h['evidence']:
                    if e['basis'] in ('model', 'model not assessable'):
                        self.assertNotEqual(e['verdict'], 'CONTRADICTS', (h['id'], e))

    def test_report_renders(self):
        html = render_band_report(self.r)
        self.assertIn('Below the roll-bite model floor', html)
        self.assertIn('Strip-shape chain not assessable', html)


class TorsionalStripMapTests(unittest.TestCase):
    def test_torsional_strip_map_pitch(self):
        # two 100 kg m2 inertias joined by 197392.09 N m/rad: 10 Hz; 0.6 m at 6 m/s and
        # 1.2 m at 12 m/s make it lead; predicted pitch 1.0 m at 10 m/s
        c = v2(orientation='transverse',
               pitch_observations=[{'exit_speed_m_s': 6.0, 'pitch_m': 0.6},
                                   {'exit_speed_m_s': 12.0, 'pitch_m': 1.2}])
        c['drive'] = {'inertias_kg_m2': [100.0, 100.0], 'stiffnesses_n_m_rad': [197392.09]}
        r = diagnose(c)
        sm = r['strip_map']
        self.assertEqual(r['leading_hypotheses'], ['torsional_or_low_frequency_drive_vibration'])
        self.assertEqual(sm['hypothesis_id'], 'torsional_or_low_frequency_drive_vibration')
        self.assertAlmostEqual(sm['predicted_pitch_m'], 1.0, places=5)
        self.assertIn('torsional mode', sm['predicted_pitch_basis'])
        self.assertIsNone(r['foil_regime'])
        self.assertNotIn(CLOSED_GAP_FLAG, r['flags'])


class SchemaCompatibilityTests(unittest.TestCase):
    def test_v1_and_existing_v2_files_still_load(self):
        for name in ('band_diagnosis_template.json', 'band_diagnosis_thin_gauge_chatter.json',
                     'band_diagnosis_bearing_order.json',
                     'band_diagnosis_lengthwise_bands.json',
                     'band_diagnosis_battery_foil.json'):
            case = load_case(SCEN / name)
            for k in bw.OBS_FOIL_BOOL:
                self.assertIn(k, case['observation'])
        lw = load_case(SCEN / 'band_diagnosis_lengthwise_bands.json')
        self.assertTrue(all(lw['observation'][k] is None for k in bw.OBS_FOIL_BOOL))
        self.assertIsNone(lw['width_model']['shape_inputs'])
        raw = json.loads((SCEN / 'band_diagnosis_lengthwise_bands.json').read_text())
        self.assertNotIn('worse_at_lower_tension', raw['observation'])
        # a v1 case may not carry the new fields
        v1 = json.loads((SCEN / 'band_diagnosis_thin_gauge_chatter.json').read_text())
        self.assertEqual(v1['case_schema'], CASE_SCHEMA_V1)
        validate_case(v1)
        v1['observation']['tracks_speed_changes'] = True
        with self.assertRaises(ValueError):
            validate_case(v1)
        bad = v2(tracks_speed_changes='yes')
        with self.assertRaises(ValueError):
            validate_case(bad)


class FoilDemoTests(unittest.TestCase):
    def test_foil_demo_leads_with_planted_cause(self):
        demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
        self.assertTrue(demo['synthetic'])
        self.assertIn('GENERATED FROM THE MODEL', demo['provenance'])
        red = [(x['entry_thickness_m'] - x['exit_thickness_m']) / x['entry_thickness_m']
               for x in demo['schedule']]
        self.assertTrue(all(x <= 0.5 for x in red))
        # coarse thermal numerics, final pass only, no AGC / drive (they do not enter the
        # lengthwise evidence) to keep the module fast
        demo['width_model']['numerics'] = dict(COARSE)
        demo['schedule'] = demo['schedule'][-2:]   # case pass and the 18 um final pass
        demo['gauge_control'] = demo['drive'] = None
        r = diagnose(demo)
        self.assertEqual(r['leading_hypotheses'], ['nozzle_thermal_stripe'])
        self.assertEqual(_h(r)['cooling_zone_switching_transient']['standing'], 'CONSISTENT')
        self.assertNotEqual(r['hypotheses'][0]['id'], 'foil_tension_lines')
        fr = r['foil_regime']
        self.assertIn(CLOSED_GAP_FLAG, r['flags'])
        self.assertEqual(fr['bite']['model'], 'experimental_mattress')
        self.assertTrue(fr['bite']['force_per_width_within_reported_range'])
        self.assertAlmostEqual(fr['wrinkle_rule']['wrinkle_onset_i_units'], 1e5 * 40e6 / 70e9)
        self.assertEqual(fr['wrinkle_rule']['comparison'], 'MODEL_BAND_BELOW_WRINKLE_ONSET')
        self.assertIn('H18', fr['product_question']['text'])
        st = r['width']['shape']['steady_stripe_table'][0]['with_feedback']
        self.assertEqual((st['state'], st['state_after_tension_release']),
                         ('LATENT_UNDER_TENSION', 'MANIFEST_AFTER_TENSION_RELEASE'))
        self.assertIn('OPEN ROLL GAP ASSUMED', r['levers']['foil_regime_note'])
        lines = ' '.join(r['recommended_next_measurements'])
        self.assertIn('offline sag', lines)
        self.assertTrue(math.isfinite(fr['bite']['separating_force_per_width_n_m']))
        # the 35 -> 18 um final pass is below the roll-bite floor: rows rejected with reason
        self.assertIn(BITE_FLOOR_FLAG, r['flags'])
        last = r['schedule_sweep']['rows'][-1]
        self.assertIn('20 um floor', last['rejected'])
        self.assertIn('20 um floor', r['width']['gauge_trend']['rows'][-1]['rejected'])
        self.assertIn('Not assessable', r['width']['gauge_trend']['text'])
        fl = fr['below_bite_model_floor']
        self.assertFalse(fl['case_pass_below_floor'])
        self.assertIn('doubled', fl['text'].lower())
        self.assertIn('rolled single-sheet', fl['text'])     # material.final_pass_doubled false
        self.assertIs(fr['final_pass_doubled'], False)
        html = render_band_report(r)
        self.assertLess(html.index('class="foil"'), html.index('Leading hypotheses'))
        self.assertIn('Below the roll-bite model floor', html)
        json.dumps(r, allow_nan=False)

    def test_foil_gauge_trend_direction_runs_against_thinner_is_worse(self):
        # Pinned on purpose: this is the model's answer to the plant's "worse at thinner
        # gauge" at foil gauge, and for this one mechanism (the demo's cooling stripe buckling
        # in the mill) it runs AGAINST the plant observation: the exit-tension feedback grows
        # as gauge falls, so the same roll stripe needs a taller height to buckle on the
        # thinner pass. Only the direction is pinned, not the numbers. The whole schedule
        # (P1-P3 assessable, P4 below the bite floor) is run with coarse thermal numerics and
        # cells 64 (the mattress bite uses its own minimum) and without AGC / drive, to keep
        # the module fast; the published demo result uses the scenario's own numerics.
        demo = load_case(SCEN / 'band_diagnosis_battery_foil.json')
        demo['width_model']['numerics'] = dict(COARSE)
        demo['model_options']['cells'] = 64
        demo['gauge_control'] = demo['drive'] = None
        r = diagnose(demo)
        rows = r['width']['gauge_trend']['rows']
        self.assertEqual(len(rows), 4)
        ok = [x for x in rows if 'rejected' not in x]
        self.assertEqual([x['label'][:2] for x in ok], ['P1', 'P2', 'P3'])
        self.assertTrue(all(a['exit_thickness_m'] > b['exit_thickness_m']
                            for a, b in zip(ok, ok[1:])))

        # thick -> thin: +1 increases on every step, -1 decreases on every step
        for key, sign in (('manifest_onset_stripe_height_m', +1),
                          ('linear_feedback_i_units', -1),
                          ('rigid_i_units', +1),
                          ('critical_ridge_height_m', -1),
                          ('trough_critical_lateral_stress_pa', -1)):   # magnitude
            vals = [abs(x[key]) for x in ok]
            self.assertTrue(all(sign * (b - a) > 0 for a, b in zip(vals, vals[1:])),
                            (key, vals))
        last = rows[-1]
        self.assertTrue(last['label'].startswith('P4'))
        self.assertAlmostEqual(last['exit_thickness_m'], 18e-6)
        self.assertIn('20 um floor', last['rejected'])
        # the report's neutral heading and generated direction sentence say the same
        html = render_band_report(r)
        self.assertIn('<h2>How the result changes with gauge</h2>', html)
        self.assertIn('thinner is less sensitive for this mechanism in the model', html)
        self.assertIn('Not assessable (excluded from the direction): P4', html)
        self.assertNotIn('Why thin gauge is worse', html)


if __name__ == '__main__':
    unittest.main()
