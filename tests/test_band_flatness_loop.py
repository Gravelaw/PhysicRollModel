"""SPEC19 package 4: the closed spray loop in the engine (width.flatness_control).

A short roll (0.6 m, 20 mm cells, 6 radial cells, 8 nozzles, 4 control zones, horizon 600 s)
with supplied shape inputs: the reading operator against the direct route, the influence
diagonal, a healthy header, a weak nozzle with stepped and on / off valves, predicted events,
zone outcomes, a supplied actuator, validation and NOT_ASSESSABLE; then one coarse diagnosis
with and without the key (nothing else changes, events identical, report renders). The loop is
a simulation with the tool's own control law, never what the plant's controller did.
"""
import copy
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
            if key != 'flatness_control':
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
