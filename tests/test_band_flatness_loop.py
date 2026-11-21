"""SPEC19 package 4: the closed spray loop in the engine (width.flatness_control).

A short roll (0.6 m, 20 mm cells, 6 radial cells, 8 nozzles, 4 control zones, horizon 600 s)
with supplied shape inputs: the reading operator against the direct route, the influence
diagonal, a healthy header, a weak nozzle with stepped and on / off valves, predicted events,
zone outcomes, a supplied actuator, validation and NOT_ASSESSABLE; then one coarse diagnosis
with and without the key (nothing else changes, events identical, report renders). The loop is
a simulation with the tool's own control law, never what the plant's controller did.
"""
import copy
import json
import math
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_width as bw
from physicroll.band_report import render_band_report
from tests.test_band_lengthwise import COARSE, LONG, TRIBOLOGY, v2, width_model

STEP05 = [i / 20 for i in range(21)]
SHAPE = {'strip_stiffness_per_width_pa': 5e10, 'bite_half_length_m': 0.004,
         'exit_tension_force_sensitivity_per_width_m': 0.004, 'provenance': 'unit test'}
SHAPEMETER = {'zone_width_m': 0.05, 'zone_count': 10, 'provenance': 'unit test'}


def _fc(**kw):
    out = {'valve_levels': STEP05, 'minimum_on_time_s': 10.0, 'minimum_off_time_s': 10.0,
           'dead_band_i_units': 2.0, 'horizon_s': 600.0, 'provenance': 'unit test'}
    out.update(kw)
    return out


def _short(levels=None, **fc):
    c = v2(**LONG)
    c['pass']['width_m'] = 0.5
    w = width_model(numerics=dict(COARSE, time_step_s=1.0), shape_inputs=dict(SHAPE),
                    cooling_zone_pitch_m=0.15, bite_heat_per_width_w_m=4e5)
    w['roll']['barrel_length_m'] = 0.6
    w['spray_header'] = dict(w['spray_header'], nozzle_pitch_m=0.075)
    if levels is not None:
        w['nozzle_levels'] = levels
    w['flatness_control'] = _fc(**fc)
    c['width_model'] = w
    c['measurement'] = {'shapemeter': dict(SHAPEMETER), 'thickness_gauge': None}
    return c


def _section(case_raw, sp_none=False):
    case = bd.validate_case(case_raw)
    w = case['width_model']
    sp = None if sp_none else bw.shape_params(case, None, w, None,
                                              supplied=w['shape_inputs'])
    th = bw._Thermal(case, w, w['bite_heat_per_width_w_m'], w['roll_heat_fraction_per_roll'])
    healthy = th.steady([1.0] * th.count)
    actual = th.steady(th.levels)
    return bw.flatness_control_section(case, w, th, sp, healthy, actual), (case, w, th, sp,
                                                                          healthy, actual)


WEAK = [1.0, 1.0, 1.0, 0.7, 1.0, 1.0, 1.0, 1.0]


class ShortRollTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.step, cls.ctx = _section(_short(WEAK))
        cls.onoff, _ = _section(_short(WEAK, valve_levels=[0.0, 1.0]))
        cls.healthy, _ = _section(_short())

    def test_operator_equals_direct_route(self):
        case, w, th, sp, healthy, actual = self.ctx
        from physicroll import band_sensors as bsn
        z = actual['z_m']
        idx = bw._inside(z, sp['strip_centre_m'], sp['strip_width_m'])
        zs = [z[i] for i in idx]
        a0 = sp['strip_centre_m'] - sp['strip_width_m'] / 2
        a1 = a0 + sp['strip_width_m']
        edges = bsn.zone_edges(th.centre, 0.05, 10)
        op = bw._ReadingOperator(zs, sp, a0, a1, edges, 0.0)
        dev = [actual['radius_growth_m'][i] - healthy['radius_growth_m'][i] for i in idx]
        a, b = op.readings(dev), op.direct(dev)
        peak = max(abs(v) for v in b if v is not None)
        self.assertGreater(peak, 0.5)
        for x, y in zip(a, b):
            self.assertLessEqual(abs(x - y), 1e-9 * peak)
        self.assertEqual(len(self.step['set_up']['control_zones']), 4)

    def test_influence_diagonal_negative(self):
        for d in self.step['set_up']['influence_diagonal']:
            self.assertLess(d['i_units_per_unit_level'], 0)

    def test_healthy_header_does_nothing(self):
        r = self.healthy
        # not exactly zero: the first step of the run is the backward-Euler start-up of
        # roll_thermal.simulate, whose splitting error moves the field by a few 1e-3 I-units
        self.assertLess(r['initial']['max_abs_residual_i_units'], 0.01)
        self.assertEqual(r['valve_changes'], 0)
        self.assertEqual(r['status'], 'SETTLED')
        self.assertEqual(r['predicted_event_count'], 0)

    def test_weak_nozzle_stepped_and_on_off(self):
        r = self.step
        self.assertIn(r['status'], ('SETTLED', 'TRIMMING_WITHIN_BAND'))
        self.assertLess(r['final']['max_abs_residual_i_units'],
                        0.5 * r['initial']['max_abs_residual_i_units'])
        self.assertEqual(self.onoff['status'], 'NOT_SETTLED')
        self.assertIn(bw.FC_FLAG_NOT_SETTLED, self.onoff['flags'])
        self.assertIsNotNone(self.onoff['end_state_note'])
        self.assertIn('not the flatness the mill would have', self.onoff['end_state_note'])
        self.assertIn("tool's own", r['what_it_is'])
        for f in (bw.FC_FLAG_SIMULATED, bw.FC_FLAG_LOW_ORDER):
            self.assertIn(f, r['flags'])
        self.assertEqual(r['model_status'], bw.FC_STATUS)

    def test_predicted_events_reproduce_the_valve_log(self):
        for r in (self.step, self.onoff):
            ev = r['predicted_events']
            self.assertEqual(len(ev), min(r['predicted_event_count'],
                                          bw.PREDICTED_EVENTS_MAX))
            self.assertEqual(sum(r['valve_changes_per_control_zone']), r['valve_changes'])
            if r['predicted_event_count'] <= bw.PREDICTED_EVENTS_MAX:
                # every change away from and back to the initial level is inside an event
                self.assertEqual(sum(e['changes'] for e in ev) + sum(
                    1 for e in ev if not e['open_at_horizon']), r['valve_changes'])
            for e in ev:
                self.assertTrue({'start_s', 'duration_s', 'nozzle_indices', 'level'} <= set(e))
                self.assertGreaterEqual(e['start_s'], 0)
                if e['duration_s'] is not None:
                    self.assertLessEqual(e['start_s'] + e['duration_s'], r['horizon_s'] + 1e-9)

    def test_zone_outcomes(self):
        thr = 2.0
        for r in (self.step, self.onoff):
            for o in r['zone_outcomes']:
                if o['outcome'] is None:
                    continue
                if abs(o['residual_start_i_units']) >= thr:
                    self.assertIn(o['outcome'], ('REMOVED', 'REMAINS'))
                else:
                    self.assertIn(o['outcome'], ('MADE', 'NONE'))
                    self.assertEqual(o['outcome'] == 'MADE',
                                     o['time_above_reporting_threshold_s'] > bw.MADE_BAND_MIN_S)
            self.assertEqual([o['zone'] for o in r['bands_made_by_switching']],
                             [o['zone'] for o in r['zone_outcomes'] if o['outcome'] == 'MADE'])

    def test_supplied_actuator_removes_a_parabolic_target(self):
        cen = [0.025 + 0.05 * j - 0.25 for j in range(10)]
        par = [10.0 * (x / 0.25) ** 2 for x in cen]
        r, _ = _section(_short(target_i_units=par, low_order_removed=-1, supplied_actuators=[
            {'name': 'bender', 'influence_i_units_per_unit': par, 'minimum': -5.0,
             'maximum': 5.0}]))
        self.assertLess(r['initial']['max_abs_residual_i_units'], 0.01)   # start-up step only
        self.assertEqual(r['valve_changes'], 0)

    def test_validation(self):
        def err(raw):
            with self.assertRaises(ValueError) as cm:
                bd.validate_case(raw)
            return str(cm.exception)
        raw = _short()
        raw['measurement'] = None
        self.assertIn('width_model.flatness_control needs measurement.shapemeter', err(raw))
        for kw, msg in (({'valve_levels': [0.5]}, 'valve_levels must be 2 to 41'),
                        ({'valve_levels': [0.5, 0.2]}, 'valve_levels must be 2 to 41'),
                        ({'initial_level': 0.33}, 'initial_level must be one of valve_levels'),
                        ({'minimum_on_time_s': 700.0}, 'minimum_on_time_s must be in [0, 600]'),
                        ({'dead_band_i_units': 0.0}, 'dead_band_i_units must be in (0, 100]'),
                        ({'horizon_s': 300.0}, 'horizon_s must be in [600, 7200]'),
                        ({'control_zone_nozzles': [[0, 1], [1, 2]]}, 'disjoint'),
                        ({'control_zone_nozzles': [[0, 9]]}, 'nozzle index 9 out of range'),
                        ({'target_i_units': [0.0] * 3}, 'per shapemeter zone (10)'),
                        ({'include_local_sources': True}, 'needs width_model.local_coupling'),
                        ({'provenance': ''}, 'provenance must be a nonempty string')):
            self.assertIn('width_model.flatness_control', err(_short(**kw)))
            self.assertIn(msg, err(_short(**kw)))

    def test_not_assessable_without_shape_parameters(self):
        r, _ = _section(_short(WEAK), sp_none=True)
        self.assertEqual(r['status'], 'NOT_ASSESSABLE')
        self.assertIn('shape parameters', r['reason'])



class FitTests(unittest.TestCase):
    """SPEC19 package 5: flatness_control.fit_first_order_dead_time on synthetic data."""

    T = [0.5 * i for i in range(241)]

    def test_exact_first_order_plus_dead_time(self):
        from physicroll import flatness_control as flc
        y = [10 * (1 - math.exp(-(t - 2) / 20)) if t > 2 else 0.0 for t in self.T]
        f = flc.fit_first_order_dead_time(self.T, y, 120.0)
        self.assertEqual(f['status'], 'FITTED')
        self.assertLess(abs(math.log(f['time_constant_s'] / 20)), math.log(1.08))
        self.assertEqual(f['dead_time_s'], 2.0)
        self.assertLess(f['rms_i_units'], 0.05)
        self.assertAlmostEqual(f['gain_i_units'], 10.0, delta=0.05)
        self.assertEqual(f['flags'], [])

    def test_two_time_scales_and_ramp(self):
        from physicroll import flatness_control as flc
        y = [5 * (1 - math.exp(-t / 10)) + 5 * (1 - math.exp(-t / 200)) for t in self.T]
        taus = [flc.fit_first_order_dead_time(self.T, y, w)['time_constant_s']
                for w in (20.0, 60.0, 120.0)]
        self.assertTrue(10 < taus[0] < taus[1] < taus[2] < 200, taus)
        ramp = [min(t, 30.0) / 30.0 for t in self.T]          # a ramp to a plateau
        for w in (60.0, 120.0):
            f = flc.fit_first_order_dead_time(self.T, ramp, w)
            self.assertNotIn(flc.FIT_FLAG_LIMIT, f['flags'])
            self.assertTrue(10 < f['time_constant_s'] < 20, f)
        slow = [1 - math.exp(-t / 1e5) for t in self.T]
        f = flc.fit_first_order_dead_time(self.T, slow, 120.0)
        self.assertIn(flc.FIT_FLAG_LIMIT, f['flags'])

    def test_noise_and_short_record(self):
        from physicroll import flatness_control as flc
        noise = [0.2 * math.sin(7.3 * i) for i in range(len(self.T))]
        y = [10 * (1 - math.exp(-t / 20)) + n for t, n in zip(self.T, noise)]
        f = flc.fit_first_order_dead_time(self.T, y, 120.0)
        self.assertLess(abs(f['time_constant_s'] / 20 - 1), 0.1)
        self.assertNotIn(flc.FIT_FLAG_NOT_FIRST_ORDER, f['flags'])
        f = flc.fit_first_order_dead_time(self.T, y, 200.0)
        self.assertEqual(f['status'], flc.FIT_RECORD_TOO_SHORT)
        self.assertIsNone(f['time_constant_s'])
        f = flc.fit_first_order_dead_time([0.0, 1.0, 2.0], [0.0, 1.0, 1.5], 2.0)
        self.assertEqual(f['status'], flc.FIT_RECORD_TOO_SHORT)


class StepTestSectionTests(unittest.TestCase):
    """The step-test section on the short roll (with and without the local sources)."""

    @classmethod
    def setUpClass(cls):
        raw = _short(WEAK)
        raw['width_model']['flatness_control'] = None
        raw['width_model']['zone_step_test'] = {
            'nozzle_indices': [4, 5], 'hold_s': 600.0, 'fit_windows_s': [20, 120, 300, 600],
            'shapemeter_distance_m': 2.0, 'provenance': 'unit test'}
        cls.raw = raw
        case = bd.validate_case(raw)
        w = case['width_model']
        sp = bw.shape_params(case, None, w, None, supplied=w['shape_inputs'])
        th = bw._Thermal(case, w, w['bite_heat_per_width_w_m'], w['roll_heat_fraction_per_roll'])
        actual = th.steady(th.levels)
        cls.plain = bw.zone_step_test_section(case, w, th, sp, actual)
        cls.ctx = (case, w, th, sp, actual)

    def test_section(self):
        r = self.plain
        self.assertEqual(r['status'], 'SCREENING_RESULT_NOT_PLANT_VALIDATED')
        self.assertIn(bw.ZT_FLAG, r['flags'])
        self.assertAlmostEqual(r['transport_delay_s'], 2.0 / 10.0, delta=1e-12)
        taus = [f['time_constant_s'] for f in r['series']['roll_growth_only']['fits']]
        self.assertLess(taus[1], taus[2])                    # grows over longer tests
        self.assertLess(taus[2], taus[3])
        self.assertTrue(r['window_dependence'])
        for name in ('mechanical_net', 'as_measured_hot', 'roll_growth_plus_strip_temperature'):
            self.assertTrue(r['series'][name]['not_supplied'], name)
        self.assertIn('not evidence', r['finding'])
        self.assertEqual(r['published']['time_constant_s'], 20.0)
        self.assertIn('surface_film_s', r['time_scales']['model_scales'])
        self.assertIn('not used in the step test', r['time_scales']['surface_path'])

    def test_with_local_sources_hot_is_faster(self):
        from physicroll import band_local as bl
        from physicroll import band_process as bp
        import types
        case, w, th, sp, actual = self.ctx
        trib = dict(TRIBOLOGY)
        case = dict(case, tribology=bd.validate_case(dict(self.raw, tribology=trib))[
            'tribology'])
        w = dict(w, local_coupling=bl.validate_local_coupling(
            {'provenance': 'unit test', 'strip_roll_temperature_coupling': 1.0,
             'flow_stress_temperature_coefficient_per_k': 0.0015}))
        lub, fin, clo = bp.tribology_objects(case['tribology'])
        bite = types.SimpleNamespace(forward_slip_fraction=0.05, contact_length_m=0.008,
                                     separating_force_n=3e6)
        fr = {'film_ratio': 0.2, 'film_thickness_m': 8e-8}
        params = bl.local_params(case, w, case['tribology'], lub, clo, fin, bite,
                                 {'exit_temperature_k': 340.0}, fr, None)
        sens = {'dforce_per_width_dfriction_n_m': 2e7, 'dforce_per_width_dflow_stress_m': 0.01,
                'flow_stress_pa': case['pass']['mean_flow_stress_pa']}
        r = bw.zone_step_test_section(case, w, th, sp, actual, {'params': params,
                                                               'sens': sens}, bite)
        hot = r['series']['as_measured_hot']['fits'][0]['time_constant_s']
        roll = r['series']['roll_growth_only']['fits'][0]['time_constant_s']
        self.assertLess(hot, roll)
        self.assertEqual(len(r['ratio_to_published']), 4)

    def test_validation(self):
        def err(**kw):
            raw = _short()
            raw['width_model']['zone_step_test'] = dict(
                {'nozzle_indices': [4, 5], 'provenance': 'x'}, **kw)
            with self.assertRaises(ValueError) as cm:
                bd.validate_case(raw)
            return str(cm.exception)
        self.assertIn('width_model.zone_step_test.hold_s must be in [10, 3600]', err(hold_s=5))
        self.assertIn('fit_windows_s must be 1 to 6 increasing', err(fit_windows_s=[90]))
        self.assertIn('nozzle index 9 out of range', err(nozzle_indices=[9]))
        self.assertIn('level must be in [0, 1]', err(level=2))
        raw = _short()
        raw['width_model']['flatness_control'] = None
        raw['width_model']['zone_step_test'] = {'nozzle_indices': [4], 'provenance': 'x'}
        raw['measurement'] = None
        with self.assertRaises(ValueError) as cm:
            bd.validate_case(raw)
        self.assertIn('width_model.zone_step_test needs measurement.shapemeter',
                      str(cm.exception))
        ok = bd.validate_case(dict(_short(), width_model=dict(
            _short()['width_model'], zone_step_test={'nozzle_indices': [4],
                                                     'provenance': 'x'})))
        self.assertEqual(ok['width_model']['zone_step_test']['fit_windows_s'], [20.0, 40.0,
                                                                                60.0])


class StepTestEdgeTests(unittest.TestCase):
    """A refused first-window fit, hold times that are not a multiple of the step, and a
    failure inside the section: always that section's status, never an aborted diagnosis."""

    @staticmethod
    def _run(hold, step, windows):
        raw = _short()
        raw['width_model']['flatness_control'] = None
        raw['width_model']['zone_step_test'] = {
            'nozzle_indices': [4, 5], 'hold_s': hold, 'time_step_s': step,
            'fit_windows_s': windows, 'provenance': 'unit test'}
        return bd.diagnose(raw)

    def test_refused_first_window_is_named(self):
        # hold 10 s at 5 s steps: three points in the 10 s window (the fit needs four); before
        # the fix the finding formatted the null constant and the TypeError aborted diagnose
        r = self._run(10.0, 5.0, [10])
        zt = r['width']['zone_step_test']
        self.assertEqual(zt['status'], 'SCREENING_RESULT_NOT_PLANT_VALIDATED')
        f = zt['series']['roll_growth_only']['fits'][0]
        self.assertEqual(f['status'], 'RECORD_TOO_SHORT_FOR_WINDOW')
        self.assertIn('nothing from roll growth alone', zt['finding'])
        self.assertIn('the 10 s window holds 3 points of the record, too few', zt['finding'])
        self.assertEqual(zt['ratio_to_published']['roll_growth_only'], [None])
        self.assertEqual(zt['window_dependence'], [])
        self.assertEqual(r['width']['failures'], [])
        html = render_band_report(r)
        self.assertIn('record too short for window', html)

    def test_record_reaches_the_hold_time(self):
        for hold, step, wins in ((10.0, 3.0, [10]), (20.0, 0.7, [20]), (25.0, 2.0, [20, 25])):
            zt = self._run(hold, step, wins)['width']['zone_step_test']
            t = zt['series']['roll_growth_only']['time_s']
            self.assertGreaterEqual(t[-1], hold - 1e-9, (hold, step))
            self.assertLess(t[-1], hold + step, (hold, step))
            for f in zt['series']['roll_growth_only']['fits']:
                self.assertEqual(f['status'], 'FITTED', (hold, step, f['window_s']))

    def test_no_step_is_not_assessable(self):
        # the switched nozzles already at the test level: before, a numerical-noise response
        # was "fitted" (1 s at the end of the search grid) and reported in the finding
        zt = self._run_level(1.0)['width']['zone_step_test']      # the case runs at 1.0
        self.assertEqual(zt['status'], 'NOT_ASSESSABLE')
        self.assertIn('already at level 1 in the case: the test switches nothing', zt['reason'])

    @staticmethod
    def _run_level(level):
        raw = _short()
        raw['width_model']['flatness_control'] = None
        raw['width_model']['zone_step_test'] = {'nozzle_indices': [4, 5], 'level': level,
                                                'hold_s': 20.0, 'provenance': 'unit test'}
        return bd.diagnose(raw)

    def test_fit_at_the_search_limit_is_not_a_value_and_the_view_reads_it(self):
        from physicroll import band_plain as bpl
        r = self._run(10.0, 3.0, [10])
        zt = r['width']['zone_step_test']
        f = zt['series']['roll_growth_only']['fits'][0]
        self.assertIn('FITTED_TIME_CONSTANT_AT_SEARCH_LIMIT', f['flags'])
        self.assertIn('at least 2.04e+03 s (the end of the fit\'s search grid', zt['finding'])
        # the plain view of a step test without the local sources (three series not
        # supplied): before, it raised KeyError 'time_s'
        v = bpl.plain_summary(r)['step_test_view']
        self.assertTrue(v['available'])
        self.assertEqual(len(v['curves']), 1)

    def test_a_failure_inside_the_section_is_its_status(self):
        from unittest import mock

        def broken(*a, **kw):
            return None + 1                 # a programming error inside the section
        with mock.patch.object(bw, 'zone_step_test_section', broken):
            r = self._run(20.0, 1.0, [20])
        zt = r['width']['zone_step_test']
        self.assertEqual(zt['status'], 'FAILED')
        self.assertIn('zone_step_test: TypeError: unsupported operand', zt['error'])
        self.assertIn(zt['error'], r['width']['failures'])
        self.assertIn('hypotheses', r)

class TooFewZonesTests(unittest.TestCase):
    """A one-zone shapemeter or an actuator without effect: not assessed, never a singular
    matrix (before: FAILED 'singular matrix in the gain'); too few zones for the low order
    removed: not assessed (before: a trivial SETTLED, nothing left to control)."""

    @staticmethod
    def _fc(zones, **fc):
        c = _short(**fc)
        c['measurement']['shapemeter']['zone_count'] = zones
        return bd.diagnose(c)['width']['flatness_control']

    def test_smallest_zone_count(self):
        for zones, order, status in ((1, -1, 'NOT_ASSESSABLE'), (2, -1, None), (2, 0, None),
                                     (3, 2, 'NOT_ASSESSABLE'), (4, 2, None)):
            f = self._fc(zones, low_order_removed=order)
            if status:
                self.assertEqual(f['status'], status, (zones, order))
                need = max(2, order + 2)
                self.assertIn(f'needs at least {need} shapemeter zones over the strip (here '
                              f'{zones})', f['reason'])
            else:
                self.assertNotIn(f['status'], ('NOT_ASSESSABLE', 'FAILED'), (zones, order, f))
            self.assertNotIn('singular', json.dumps(f))

    def test_actuator_without_effect(self):
        f = self._fc(10, supplied_actuators=[{'name': 'bend', 'influence_i_units_per_unit':
                                              [0.0] * 10, 'minimum': -1.0, 'maximum': 1.0}])
        self.assertEqual(f['status'], 'NOT_ASSESSABLE')
        self.assertIn('"bend" has no effect on any zone over the strip, so no gain can be '
                      'formed', f['reason'])

    def test_step_test_with_one_zone(self):
        c = _short()
        c['width_model']['flatness_control'] = None
        c['measurement']['shapemeter']['zone_count'] = 1
        c['width_model']['zone_step_test'] = {'nozzle_indices': [3, 4], 'hold_s': 60.0,
                                              'provenance': 'unit test'}
        zt = bd.diagnose(c)['width']['zone_step_test']
        self.assertEqual(zt['status'], 'NOT_ASSESSABLE')
        self.assertIn('needs at least two shapemeter zones', zt['reason'])

EVENT = [{'start_s': 0.0, 'duration_s': 20.0, 'nozzle_indices': [12], 'level': 0.0}]


class EngineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        a = v2(**LONG)
        a['tribology'] = dict(TRIBOLOGY)
        a['width_model'] = width_model(numerics=dict(COARSE), blocked_nozzle_indices=[12],
                                       cooling_zone_pitch_m=0.104, events=copy.deepcopy(EVENT))
        a['measurement'] = {'shapemeter': {'zone_width_m': 0.052, 'zone_count': 29,
                                           'provenance': 'unit test'}, 'thickness_gauge': None}
        b = copy.deepcopy(a)
        b['width_model']['flatness_control'] = _fc(horizon_s=900.0, dead_band_i_units=2.0)
        cls.a, cls.b = bd.diagnose(a), bd.diagnose(b)

    def test_section_and_nothing_else_changes(self):
        a, b = self.a, self.b
        fc = b['width']['flatness_control']
        self.assertIn(fc['status'], ('SETTLED', 'TRIMMING_WITHIN_BAND', 'NOT_SETTLED'),
                      fc.get('reason') or fc.get('error'))
        self.assertIn(bw.FC_FLAG_SIMULATED, b['flags'])
        self.assertIn(bw.FC_FLAG_COARSE, b['flags'])             # 20 mm cells, 52 mm zones
        self.assertTrue(a['width']['flatness_control']['not_supplied'])
        self.assertEqual([(h['id'], h['score'], h['standing'], h['rank'])
                          for h in a['hypotheses']],
                         [(h['id'], h['score'], h['standing'], h['rank'])
                          for h in b['hypotheses']])
        self.assertEqual(a['leading_hypotheses'], b['leading_hypotheses'])
        for key in a:
            if key not in ('inputs', 'width', 'flags'):
                self.assertEqual(a[key], b[key], key)
        for key in a['width']:
            if key not in ('flatness_control', 'zone_step_test'):
                self.assertEqual(a['width'][key], b['width'][key], key)
        self.assertEqual(a['flags'], [f for f in b['flags'] if f not in bw.FC_TOP_FLAGS])
        ia, ib = copy.deepcopy(a['inputs']), copy.deepcopy(b['inputs'])
        ib['width_model']['flatness_control'] = None
        self.assertEqual(ia, ib)

    def test_report(self):
        ha, hb = render_band_report(self.a), render_band_report(self.b)
        self.assertNotIn('What the flatness control would do', ha)
        self.assertIn('What the flatness control would do', hb)
        self.assertIn("tool&#x27;s own", hb)
        self.assertNotIn('>nan<', hb)
        self.assertFalse(math.isnan(self.b['width']['flatness_control']['horizon_s']))


if __name__ == '__main__':
    unittest.main()
