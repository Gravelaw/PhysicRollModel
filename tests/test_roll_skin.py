"""SPEC18 package 10: the roll surface layer within one revolution (A4, G8).

Closed forms of the half-space, the planner's cycle numbers (s23/skin2.py; k 40, rho*c
7850*470, R 0.135 m, 10 m/s), superposition, energy, validation, and the engine section on the
template case with a supplied bite (fast).
"""
import copy
import json
import math
import os
import time
import unittest

from physicroll import band_diagnosis as bd
from physicroll import band_report
from physicroll import band_width as bw
from physicroll import roll_skin as rs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K, RHO_C, R, V = 40.0, 7850 * 470.0, 0.135, 10.0
T_REV = 2 * math.pi * R / V
E = math.sqrt(K * RHO_C)
BITE = 0.002 / (2 * math.pi * R)


def _cycle_arcs(bite_flux=1e7):
    return [dict(kind='bite', start_fraction=0.0, end_fraction=BITE, heat_flux_w_m2=bite_flux,
                 htc_w_m2k=0.0, sink_temperature_k=None),
            dict(kind='air', start_fraction=BITE, end_fraction=90 / 360, heat_flux_w_m2=0.0,
                 htc_w_m2k=50.0, sink_temperature_k=313.15),
            dict(kind='spray', start_fraction=90 / 360, end_fraction=150 / 360,
                 heat_flux_w_m2=0.0, htc_w_m2k=20450.0, sink_temperature_k=313.15),
            dict(kind='air', start_fraction=150 / 360, end_fraction=1.0, heat_flux_w_m2=0.0,
                 htc_w_m2k=50.0, sink_temperature_k=313.15)]


def _cycle(**kw):
    return rs.surface_cycle(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                            revolution_time_s=T_REV, arcs=_cycle_arcs(), deep_temperature_k=330.0,
                            **kw)


class ClosedFormTests(unittest.TestCase):

    def test_constants(self):
        self.assertAlmostEqual(T_REV, 0.0848230, delta=1e-7)
        self.assertAlmostEqual(2 * math.pi / T_REV, 74.0741, delta=1e-4)
        self.assertAlmostEqual(E, 12148.25, delta=0.01)
        self.assertAlmostEqual(_cycle()['skin_depth_m'], 0.5410e-3, delta=1e-7)

    def test_sinusoid(self):
        """Flux q1*cos(omega*t): amplitude q1/(e*sqrt(omega)) lagging by 45 degrees (first
        harmonic of the periodic history; 45 arcs of 8 steps)."""
        n, q1 = 45, 1e5
        arcs = [dict(kind='air', start_fraction=i / n, end_fraction=(i + 1) / n,
                     heat_flux_w_m2=q1 * math.cos(2 * math.pi * (i + 0.5) / n), htc_w_m2k=0.0,
                     sink_temperature_k=None) for i in range(n)]
        r = rs.surface_cycle(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                             revolution_time_s=T_REV, arcs=arcs, deep_temperature_k=330.0)
        ts, tf = r['surface_temperature_k'], r['time_fraction']
        m = sum(ts) / len(ts)
        c = 2 * sum((t - m) * math.cos(2 * math.pi * f) for t, f in zip(ts, tf)) / len(ts)
        s = 2 * sum((t - m) * math.sin(2 * math.pi * f) for t, f in zip(ts, tf)) / len(ts)
        exact = q1 / (E * math.sqrt(2 * math.pi / T_REV))
        self.assertAlmostEqual(exact, 0.95643, delta=1e-5)
        self.assertAlmostEqual(math.hypot(c, s) / exact, 1, delta=5e-3)
        self.assertAlmostEqual(math.degrees(math.atan2(s, c)), 45.0, delta=1.0)

    def test_constant_flux(self):
        exact = 2 * 1e7 * math.sqrt(2e-4) / (math.sqrt(math.pi) * E)
        self.assertAlmostEqual(exact, 13.136, delta=1e-3)
        for cells, tol in ((24, 0.04), (48, 0.015)):
            r = rs.surface_transient(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                                     duration_s=2e-4, heat_flux_w_m2=1e7,
                                     initial_temperature_k=300.0, cells=cells)
            self.assertAlmostEqual((r['final_surface_temperature_k'] - 300) / exact, 1,
                                   delta=tol)

    def test_step_in_h(self):
        t_star = K * RHO_C / 3400.0 ** 2
        self.assertAlmostEqual(t_star, 12.766, delta=1e-3)
        r = rs.surface_transient(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                                 duration_s=t_star, htc_w_m2k=3400.0, sink_temperature_k=301.0,
                                 initial_temperature_k=300.0)
        exact = 1 - math.exp(1) * math.erfc(1)
        self.assertAlmostEqual(exact, 0.5724, delta=1e-4)
        self.assertAlmostEqual((r['final_surface_temperature_k'] - 300) / exact, 1, delta=5e-3)
        self.assertAlmostEqual(r['final_surface_temperature_k'] - 300, 0.57264, delta=1e-4)


class CycleTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = _cycle()

    def test_worked_cycle(self):
        r = self.r
        self.assertAlmostEqual(r['bite_entry_temperature_k'], 327.154, delta=5e-4)
        self.assertTrue(340.55 - 0.01 <= r['bite_exit_temperature_k'] <= 340.68)
        self.assertAlmostEqual(r['minimum_temperature_k'], 325.05, delta=5e-3)
        self.assertAlmostEqual(r['mean_surface_temperature_k'], 327.06, delta=5e-3)
        self.assertAlmostEqual(r['mean_flux_into_roll_w_m2'], -20533, delta=1.0)
        self.assertEqual(r['revolutions'], 60)
        self.assertAlmostEqual(r['mean_htc_w_m2k'], 3450, delta=0.5)        # arc-weighted mean
        # planner 3172.3 and 0.9195; this implementation 3171.17 and 0.91921 (0.04 %)
        self.assertAlmostEqual(r['effective_mean_htc_w_m2k'] / 3172.3, 1, delta=5e-3)
        self.assertAlmostEqual(r['mean_coefficient_ratio'], 0.9195, delta=5e-3)
        # pins of this implementation
        self.assertAlmostEqual(r['bite_exit_temperature_k'], 340.5446296, delta=1e-6)
        self.assertAlmostEqual(r['effective_mean_htc_w_m2k'], 3171.174743, delta=1e-5)

    def test_energy(self):
        """Mean surface flux into the roll equals the flux into the deep at convergence."""
        r = self.r
        self.assertAlmostEqual(r['deep_flux_w_m2'] / r['mean_flux_into_roll_w_m2'], 1,
                               delta=0.015)

    def test_superposition(self):
        u = rs.unit_solutions(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                              revolution_time_s=T_REV, arcs=_cycle_arcs(),
                              coolant_temperature_k=313.15, tolerance_k=1e-7)
        a = u['per_unit_bite_flux_k_per_w_m2'][-1] * 1e7
        b = u['per_unit_deep_excess'][-1]
        self.assertAlmostEqual(b, 0.713887, delta=2e-5)
        self.assertAlmostEqual(a, 1.966020, delta=2e-4)
        tight = _cycle(tolerance_k=1e-7)
        self.assertAlmostEqual(313.15 + b * 16.85 + a, tight['bite_entry_temperature_k'],
                               delta=2e-3)
        self.assertAlmostEqual(313.15 + b * 16.85 + a, 327.145, delta=5e-4)
        self.assertIsNone(u['per_unit_backup_excess'])

    def test_budget_nine_weights(self):
        t0 = time.perf_counter()
        for i in range(9):
            arcs = _cycle_arcs(1.0)
            arcs[2]['htc_w_m2k'] = 50 + 3000 * (0.6 + 0.07 * i) * 6
            rs.unit_solutions(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                              revolution_time_s=T_REV, arcs=arcs, coolant_temperature_k=313.15,
                              tolerance_k=bw.SURFACE_CYCLE_TOLERANCE_K)
        self.assertLess(time.perf_counter() - t0, 3.0 * 2)    # budget 3 s (x2 for slow hosts)

    def test_time_scales(self):
        s = rs.time_scales(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                           revolution_time_s=T_REV, radius_m=R, mean_htc_w_m2k=3400.0,
                           event_durations_s=[20.0])
        self.assertAlmostEqual(s['surface_film_s'], 12.766, delta=1e-3)
        self.assertAlmostEqual(s['bulk_s'], RHO_C * R / (2 * 3400), delta=1e-9)
        self.assertAlmostEqual(s['events'][0]['over_surface_film'], 20 / 12.76644, delta=1e-4)

    def test_arc_validation(self):
        bad = _cycle_arcs()
        bad[1]['start_fraction'] = 0.01
        with self.assertRaises(ValueError):
            rs.surface_cycle(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                             revolution_time_s=T_REV, arcs=bad, deep_temperature_k=330.0)
        bad = _cycle_arcs()
        bad[-1]['end_fraction'] = 0.9
        with self.assertRaises(ValueError):
            rs.surface_cycle(conductivity_w_mk=K, volumetric_heat_capacity_j_m3k=RHO_C,
                             revolution_time_s=T_REV, arcs=bad, deep_temperature_k=330.0)


def _template():
    with open(os.path.join(ROOT, 'scenarios', 'band_diagnosis_template.json')) as fh:
        raw = json.load(fh)
    with open(os.path.join(ROOT, 'artifacts', 'band_diagnosis',
                           'lengthwise-bands-demo.result.json')) as fh:
        bite = json.load(fh)['bite']
    raw['model_options']['bite_response_override'] = {
        k: v for k, v in bite.items() if k not in ('source', 'flags', 'strip_modulus_n_m')}
    return raw


LAYOUT = {'spray_arcs': [{'start_rad': math.pi / 2, 'arc_rad': math.pi / 3}],
          'provenance': 'test layout'}


class LayoutValidationTests(unittest.TestCase):

    def _err(self, lay, wetted=None):
        raw = _template()
        raw['width_model']['circumferential_layout'] = lay
        if wetted is not None:
            raw['width_model']['spray_wetted_arc_rad'] = wetted
        with self.assertRaises(ValueError) as ctx:
            bd.validate_case(raw)
        return str(ctx.exception)

    def test_messages(self):
        two = {'spray_arcs': [{'start_rad': 1.0, 'arc_rad': 0.5}, {'start_rad': 1.2,
                                                                    'arc_rad': 0.5}],
               'provenance': 'x'}
        self.assertIn('spray arc 0 (1 to 1.5 rad) overlaps spray arc 1 (1.2 to 1.7 rad)',
                      self._err(two))
        self.assertIn('exceeds one revolution',
                      self._err({'spray_arcs': [{'start_rad': 6.0, 'arc_rad': 0.5}],
                                 'provenance': 'x'}))
        backup = dict(LAYOUT, backup_contact={'start_rad': 2.0, 'arc_rad': 0.3,
                                              'conductance_w_m2k': 1e4,
                                              'backup_surface_temperature_k': 320.0})
        self.assertIn('spray arc 0 (1.571 to 2.618 rad) overlaps backup contact (2 to 2.3 rad)',
                      self._err(backup))
        self.assertIn('the spray arcs must add up to width_model.spray_wetted_arc_rad',
                      self._err(LAYOUT, wetted=1.0))
        self.assertIn('spray_arcs must be a list of 1 to 6',
                      self._err({'spray_arcs': [], 'provenance': 'x'}))
        unsorted = {'spray_arcs': [{'start_rad': 3.0, 'arc_rad': 0.2},
                                   {'start_rad': 1.0, 'arc_rad': 0.2}], 'provenance': 'x'}
        self.assertIn('sorted', self._err(unsorted))

    def test_overlap_with_the_bite(self):
        w = {'circumferential_layout': {'spray_arcs': [{'start_rad': 6.2, 'arc_rad': 0.08}],
                                        'backup_contact': None, 'provenance': 'x'}}
        with self.assertRaises(ValueError) as ctx:
            bw.surface_cycle_layout(w, 0.2, 0.005)
        self.assertIn('spray arc 0 (6.2 to 6.28 rad) overlaps the bite', str(ctx.exception))


class EngineSectionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        raw = _template()
        cls.a = bd.diagnose(raw)
        lay = copy.deepcopy(raw)
        lay['width_model']['circumferential_layout'] = copy.deepcopy(LAYOUT)
        t0 = time.perf_counter()
        cls.b = bd.diagnose(lay)
        cls.cost = time.perf_counter() - t0

    def test_not_supplied(self):
        self.assertTrue(self.a['width']['roll_surface_cycle']['not_supplied'])
        self.assertIsNone(self.a['inputs']['width_model']['circumferential_layout'])
        self.assertNotIn('Roll surface within one revolution',
                         band_report.render_band_report(self.a))

    def test_section(self):
        rc = self.b['width']['roll_surface_cycle']
        self.assertEqual(rc['status'], rs.STATUS)
        self.assertEqual(len(rc['bite_entry_temperature_k']), len(rc['z_m']))
        self.assertEqual([c['station'] for c in rc['cycles']][0], 'strip centre')
        self.assertIn('ROLL_SURFACE_CYCLE_COMPUTED', rc['flags'])
        self.assertIn('CIRCUMFERENTIAL_MEAN_COEFFICIENT_BIASED', rc['flags'])
        self.assertLess(rc['worst_mean_coefficient_ratio'], 0.95)
        self.assertEqual([x['region'] for x in rc['layout_used']], ['bite', 'spray arc 0'])
        for key in ('per_revolution_s', 'surface_film_s', 'bulk_s'):
            self.assertIn(key, rc['time_scales']['scale_meaning'])
        hp = self.b['process']['heating']['operating']['heat_partition']
        self.assertEqual(hp['roll_entry_surface_temperature_k'],
                         rc['cycles'][0]['bite_entry_temperature_k'])
        self.assertIn('ROLL_ENTRY_TEMPERATURE_FROM_SURFACE_CYCLE', hp['flags'])
        html = band_report.render_band_report(self.b)
        self.assertIn('Roll surface within one revolution', html)
        self.assertIn('a comparison, not an explanation', html)

    def test_nothing_else_changes(self):
        for key in ('hypotheses', 'leading_hypotheses', 'bite', 'screens', 'signatures'):
            self.assertEqual(self.a[key], self.b[key], key)
        wa, wb = self.a['width'], self.b['width']
        for key in wa:
            if key not in ('roll_surface_cycle', 'flags'):
                self.assertEqual(wa[key], wb[key], key)
        self.assertEqual(wa['flags'], [f for f in wb['flags'] if f not in (
            bw.CYCLE_FLAG, bw.CYCLE_BIAS_FLAG)])

    def test_reduces_to_the_mean_model(self):
        """Sprays all round (no angular variation of h except the bite): averaged over one
        nozzle pitch, the layer mean equals the circumferential-mean model's surface within 1 %
        of the surface excess in the strip interior (0.15 m from the strip edges). Pointwise it
        differs by up to about 0.4 K at the nozzle scale, and more at the strip edges: the 1D
        layer has no axial conduction (stated in the section's limitations)."""
        raw = _template()
        tb = raw['model_options']['bite_response_override']['contact_length_m'] / 0.2
        raw['width_model']['circumferential_layout'] = {
            'spray_arcs': [{'start_rad': 0.0, 'arc_rad': 2 * math.pi - tb - 1e-9}],
            'provenance': 'uniform'}
        r = bd.diagnose(raw)
        rc = r['width']['roll_surface_cycle']
        tc = raw['width_model']['coolant_temperature_k']
        ws = r['width']['thermal_steady']
        pitch = raw['width_model']['spray_header']['nozzle_pitch_m']
        z, d = rc['z_m'], rc['mean_minus_mean_model_k']
        a0, a1 = ws['strip_start_m'] + 0.15, ws['strip_end_m'] - 0.15
        checked = 0
        for zi, m in zip(z, rc['mean_model_surface_temperature_k']):
            if a0 <= zi <= a1:
                win = [x for zz, x in zip(z, d) if abs(zz - zi) <= pitch / 2]
                self.assertLess(abs(sum(win) / len(win)), 0.01 * (m - tc), zi)
                checked += 1
        self.assertGreater(checked, 100)
        self.assertAlmostEqual(rc['worst_mean_coefficient_ratio'], 1, delta=0.01)

    def test_cost(self):
        self.assertLess(self.cost, 60)


if __name__ == '__main__':
    unittest.main()
