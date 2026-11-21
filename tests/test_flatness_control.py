"""SPEC19 package 3: the parts of the flatness loop (physicroll/flatness_control.py).

Weighted low-order basis, the two-zone hand case of the brief, hysteresis, dwell times, dead
band, clipping, supplied actuators, and a synthetic first-order plant: proportional valves
settle, two-level valves with a demand between the levels do not (switch count at the dwell
bound), delay FIFO and display filter, history thinning, JSON safety. The control law is the
tool's own [D, SPEC19: analyst design], not a vendor's.
"""
import json
import math
import unittest

from physicroll import flatness_control as fc

HAND_B = [[-10.0, -2.0], [-2.0, -10.0]]
STEP05 = [i / 20 for i in range(21)]
TAU = 20.0


def _ctrl(dead_band=0.0, dwell=0.0, levels=STEP05, initial=0.5, **kw):
    kw.setdefault('low_order', -1)
    kw.setdefault('regularisation_fraction', 0.0)
    return fc.ZoneController(HAND_B, [1.0, 1.0], [[0], [1]], levels, initial, dwell, dwell,
                             dead_band, **kw)


def _plant(n=4, b=-10.0, d=5.0, u0=1.0):
    """r_k' = (b*u_k + d - r_k)/tau, exact over each interval; steady r = b*u + d."""
    st = {'r': [d + b * u0] * n, 'calls': 0}

    def advance(levels, dur, dt):
        st['calls'] += 1
        st['r'] = [d + b * u + (r - (d + b * u)) * math.exp(-dur / TAU)
                   for r, u in zip(st['r'], levels)]
        return st['r']
    return advance, (lambda x: list(x)), st


def _diag_ctrl(levels, dwell, n=4, b=-10.0, dead_band=0.5, **kw):
    return fc.ZoneController([[b if j == k else 0.0 for k in range(n)] for j in range(n)],
                             [1.0] * n, [[k] for k in range(n)], levels, 1.0, dwell, dwell,
                             dead_band, low_order=-1, **kw)


class BasisTests(unittest.TestCase):

    def test_orthonormal_and_parabola(self):
        x = [0.026 + 0.052 * i for i in range(12)]
        w = [0.4] + [1.0] * 10 + [0.7]
        basis = fc.low_order_basis(x, w, 2)
        for a in basis:
            for b in basis:
                dot = sum(wi * ai * bi for wi, ai, bi in zip(w, a, b))
                self.assertAlmostEqual(dot, 1.0 if a is b else 0.0, delta=1e-12)
        par = [3 + 2 * xi - 7 * xi * xi for xi in x]
        res, coef = fc.remove_low_order(par, basis, w)
        self.assertLess(max(abs(v) for v in res), 1e-9)
        self.assertEqual(len(coef), 3)
        res1, _ = fc.remove_low_order(par, fc.low_order_basis(x, w, 1), w)
        self.assertGreater(max(abs(v) for v in res1), 0.1)
        self.assertEqual(fc.low_order_basis(x, w, -1), [])
        res_none, _ = fc.remove_low_order([None] + par[1:], basis, [0.0] + w[1:])
        self.assertIsNone(res_none[0])


class HandCaseTests(unittest.TestCase):

    def test_gain_and_one_step(self):
        g = fc.regularised_gain(HAND_B, [1, 1], 0.0)
        for got, want in zip(sum(g, []), (-0.104167, 0.020833, 0.020833, -0.104167)):
            self.assertAlmostEqual(got, want, delta=1e-6)
        c = _ctrl()
        c.step(0.0, [5.0, 0.0])
        self.assertAlmostEqual(c.last['correction'][0], -0.520833, delta=1e-6)
        self.assertAlmostEqual(c.last['correction'][1], 0.104167, delta=1e-6)
        self.assertAlmostEqual(c.demand[0], 0.552083, delta=1e-6)
        self.assertAlmostEqual(c.demand[1], 0.489583, delta=1e-6)

    def test_dead_band_and_dwell(self):
        c = _ctrl(dead_band=2.0, dwell=10.0)
        lv = c.step(2.0, [5.0, 0.0])                # |d1|*b1 = 5.21 moves, 1.04 does not
        self.assertAlmostEqual(c.demand[0], 0.552083, delta=1e-6)
        self.assertEqual(c.demand[1], 0.5)
        self.assertEqual(lv, [0.5, 0.5])            # dwell from the start not yet passed
        lv = c.step(10.0, [0.0, 0.0])               # residual gone: demand kept
        self.assertEqual(lv, [0.55, 0.5])

    def test_hysteresis(self):
        c = _ctrl(levels=[0.0, 0.5, 1.0], hysteresis_fraction=0.1)
        c.demand[0] = 0.74                          # nearest is still 0.5 (tie goes lower)
        c.step(1.0, [0.0, 0.0])
        self.assertEqual(c.valve[0], 0.5)
        c.demand[0] = 0.77                          # nearest 1.0 but closer by 0.04 < 0.05
        c.step(2.0, [0.0, 0.0])
        self.assertEqual(c.valve[0], 0.5)
        c.demand[0] = 0.8                           # closer by 0.1 > 0.05
        c.step(3.0, [0.0, 0.0])
        self.assertEqual(c.valve[0], 1.0)

    def test_clipping(self):
        c = _ctrl(levels=[0.0, 1.0], initial=1.0)
        for t in range(50):
            c.step(float(t), [500.0, 500.0])
        self.assertEqual(c.demand, [1.0, 1.0])
        for t in range(50, 100):
            c.step(float(t), [-500.0, -500.0])
        self.assertEqual(c.demand, [0.0, 0.0])

    def test_square_wave_demand_cannot_switch_faster_than_dwell(self):
        c = _ctrl(levels=[0.0, 1.0], dwell=30.0, initial=0.0, integral_gain=10.0)
        times = []
        for i in range(300):
            before = c.valve[0]
            c.step(float(i), [50.0 if (i // 3) % 2 == 0 else -50.0, 0.0])
            if c.valve[0] != before:
                times.append(i)
        self.assertTrue(times)
        self.assertTrue(all(b - a >= 30 for a, b in zip(times, times[1:])))

    def test_supplied_actuator_removes_its_vector(self):
        col = [1.0, 2.0, 3.0, 4.0]
        rem, st = fc.fit_supplied_actuators([3 * v for v in col], [
            {'name': 'bender', 'influence_i_units_per_unit': col, 'minimum': -10.0,
             'maximum': 10.0}], [1.0] * 4)
        self.assertAlmostEqual(st[0]['setting'], 3.0, delta=1e-9)
        self.assertLess(max(abs(v) for v in rem), 1e-9)
        rem, st = fc.fit_supplied_actuators([3 * v for v in col], [
            {'name': 'bender', 'influence_i_units_per_unit': col, 'minimum': -1.0,
             'maximum': 1.0}], [1.0] * 4)
        self.assertEqual(st[0]['setting'], 1.0)                 # clipped
        self.assertAlmostEqual(rem[3], 8.0, delta=1e-9)

    def test_influence_matrix(self):
        def readings(lv):
            return [sum(b * u for b, u in zip(row, lv)) + 1.0 for row in HAND_B]
        b = fc.influence_matrix(readings, [0.5, 0.1], [[0], [1]], step=0.2)
        for row, want in zip(b, HAND_B):
            for x, y in zip(row, want):
                self.assertAlmostEqual(x, y, delta=1e-12)


class LoopTests(unittest.TestCase):

    def test_proportional_valves_settle(self):
        adv, rd, _ = _plant()
        r = fc.run_loop(adv, rd, _diag_ctrl(STEP05, 10.0), horizon_s=1800,
                        control_interval_s=2.0, time_step_s=1.0)
        self.assertEqual(r['status'], 'SETTLED')
        self.assertLess(r['final']['max_abs_residual_i_units'],
                        r['initial']['max_abs_residual_i_units'])
        self.assertEqual(r['model_status'], fc.STATUS)
        self.assertIn("not a vendor's algorithm", r['control_law'])
        json.dumps(r, allow_nan=False)

    def test_two_level_valves_do_not_settle(self):
        dwell = 60.0
        adv, rd, _ = _plant()
        r = fc.run_loop(adv, rd, _diag_ctrl([0.0, 1.0], dwell), horizon_s=1800,
                        control_interval_s=2.0, time_step_s=1.0)
        self.assertEqual(r['status'], 'NOT_SETTLED')
        bound = 4 * 1800 / dwell
        self.assertLessEqual(r['valve_changes'], bound)
        self.assertGreaterEqual(r['valve_changes'], 0.9 * bound)     # at the dwell bound
        per_zone = {}
        for x in r['valve_log']:
            per_zone[x['control_zone']] = per_zone.get(x['control_zone'], 0) + 1
        self.assertTrue(all(v <= 1800 / dwell for v in per_zone.values()))
        self.assertGreater(r['last_window']['max_abs_residual_i_units_highest'], 4.0)

    def test_delay_filter_history_and_validation(self):
        adv, rd, _ = _plant()
        seen = []

        class Spy(fc.ZoneController):
            def step(self, t, readings):
                seen.append(list(readings))
                return super().step(t, readings)
        c = Spy([[-10.0 if j == k else 0.0 for k in range(4)] for j in range(4)], [1.0] * 4,
                [[k] for k in range(4)], STEP05, 1.0, 10.0, 10.0, 0.5, low_order=-1)
        raw = []

        def rd2(x):
            raw.append(list(x))
            return list(x)
        r = fc.run_loop(adv, rd2, c, horizon_s=3000, control_interval_s=2.0, time_step_s=1.0,
                        delay_intervals=3)
        self.assertEqual(seen[0], raw[0])
        self.assertEqual(seen[10], raw[7])                       # three intervals old
        self.assertLessEqual(len(r['history']['time_s']), fc.HISTORY_MAX_POINTS)
        self.assertEqual(r['history']['time_s'][-1], 3000.0)
        adv, rd, _ = _plant()
        seen.clear()
        c = Spy([[-10.0 if j == k else 0.0 for k in range(4)] for j in range(4)], [1.0] * 4,
                [[k] for k in range(4)], STEP05, 1.0, 10.0, 10.0, 0.5, low_order=-1)
        raw.clear()
        fc.run_loop(adv, rd2, c, horizon_s=600, control_interval_s=2.0, time_step_s=1.0,
                    display_time_constant_s=8.0)
        a = 2.0 / 10.0
        self.assertAlmostEqual(seen[1][0], seen[0][0] + a * (raw[1][0] - seen[0][0]),
                               delta=1e-12)
        with self.assertRaises(ValueError):
            fc.run_loop(adv, rd, c, horizon_s=500, control_interval_s=2.0, time_step_s=1.0)

    def test_trimming_and_flags(self):
        adv, rd, _ = _plant(d=5.2)
        r = fc.run_loop(adv, rd, _diag_ctrl([0.0, 0.5, 1.0], 20.0, dead_band=2.0),
                        horizon_s=1800, control_interval_s=2.0, time_step_s=1.0)
        self.assertIn(r['status'], fc.LOOP_STATUSES)
        adv, rd, _ = _plant(d=50.0)            # needs more cooling than the valves give
        r = fc.run_loop(adv, rd, _diag_ctrl(STEP05, 10.0), horizon_s=1800,
                        control_interval_s=2.0, time_step_s=1.0)
        self.assertIn(fc.FLAG_AT_LIMIT, r['flags'])
        self.assertEqual(r['zones_at_limit'], [0, 1, 2, 3])


if __name__ == '__main__':
    unittest.main()
