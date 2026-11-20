"""The v2 part of the degenerate-input sweep and the perturbed-bite-model tests, split from
tests/test_band_robustness.py (DegenerateInputSweepTests, PerturbedBiteModelTests) to keep
each module under the time limit; fixtures are shared from there."""
import unittest

from tests import test_band_robustness as _base

# the shared fixtures, helpers and imports of the original module (test classes excluded,
# so no test runs twice)
globals().update({k: v for k, v in vars(_base).items() if not k.startswith('__')
                  and not (isinstance(v, type) and issubclass(v, unittest.TestCase))})


class DegenerateInputSweepV2Tests(unittest.TestCase):
    """Every accepted degenerate v2 input: diagnose returns, the report renders."""

    def test_v2_sweep(self):
        for label, obs in {**SWEEP, **SWEEP_V2}.items():
            with self.subTest(label):
                _ok(self, v2case(**obs), label)
        _ok(self, v2case(), 'all null')
        _ok(self, _all_bools(v2case(), True), 'all true')
        _ok(self, _all_bools(v2case(), False), 'all false')

    def test_v2_thermal_inputs(self):
        # SPEC14 review: zero roll-heat fraction and a cooling (restore) event return and render
        c = v2case(width=True)
        c['width_model']['roll_heat_fraction_per_roll'] = 0.0
        _ok(self, c, 'zero roll heat fraction')
        c = v2case(width=True)
        c['width_model']['events'] = [{'start_s': 0.0, 'duration_s': 20.0,
                                       'nozzle_indices': [12], 'level': 1.0}]
        _ok(self, c, 'cooling restore event')

    def test_v2_width_model_inputs(self):
        r, _ = _ok(self, v2case(width=True, orientation='longitudinal',
                                band_positions_across_width_m=[0.6, 0.6, 0.7]), 'dup + width')
        self.assertIn('DUPLICATE_BAND_POSITIONS_MERGED', r['flags'])
        for idx in ([12, 12], [0, 31]):
            c = v2case(width=True, band_positions_across_width_m=[0.6])
            c['width_model']['blocked_nozzle_indices'] = idx
            _ok(self, c, f'blocked {idx}')


class PerturbedBiteModelTests(unittest.TestCase):
    """Review fix: the lever table and the speed-consistent critical speed derive their
    perturbed bites with the operating bite's model; a pass that model rejects is a
    not-assessable row, never a silent switch."""

    def test_mattress_operating_bite_keeps_mattress_in_the_levers(self):
        from physicroll import band_diagnosis as bd
        from physicroll.foil_bite import derive_bite_response_mattress
        from tests.test_band_foil import foil_case
        c = foil_case(friction=0.03, h0=50e-6, h1=30e-6, schedule=False, width=False)
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertIn('BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL', r['bite']['flags'])
        eff = validate_case(c)
        base = bd._bite_pass(eff)
        from dataclasses import replace
        checked = 0
        for row in r['levers']['rows']:
            if row['lever'] not in ('friction', 'reduction', 'entry_tension', 'exit_tension') \
                    or 'rejected' in row:
                continue
            change = {'friction': {'friction_coefficient': base.friction_coefficient
                                   * row['factor']},
                      'entry_tension': {'entry_tension_pa': base.entry_tension_pa
                                        * row['factor']},
                      'exit_tension': {'exit_tension_pa': base.exit_tension_pa
                                       * row['factor']},
                      'reduction': {'exit_thickness_m': base.entry_thickness_m * (
                          1 - (1 - base.exit_thickness_m / base.entry_thickness_m)
                          * row['factor'])}}[row['lever']]
            b = derive_bite_response_mattress(replace(base, **change),
                                              cells=max(64, bd.MATTRESS_MIN_CELLS))
            c_, _ = bd._crit_pair(bd._stand(eff), b, bd._spans(eff), 0.5)
            self.assertEqual(row['critical_exit_speed_m_s'], c_['critical_exit_speed_m_s'],
                             row['change'])
            checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_variant_the_operating_model_rejects_is_not_assessable(self):
        c = v2(override=False)
        c['pass'].update(entry_thickness_m=0.3e-3, exit_thickness_m=0.21e-3,
                         mean_flow_stress_pa=270e6, friction_coefficient=0.03,
                         exit_speed_m_s=12.0)
        c['model_options']['bite_model'] = 'auto'
        r = diagnose(c)
        self.assertEqual(r['bite']['source'], 'derived_slab_hitchcock')
        rej = {(x['lever'], x['factor']): x for x in r['levers']['rows'] if 'rejected' in x}
        self.assertIn(('friction', 1.3), rej)
        self.assertIn('Hitchcock contact radius ratio', rej[('friction', 1.3)]['rejected'])
        self.assertIsNone(rej[('friction', 1.3)]['ratio_to_baseline'])

if __name__ == '__main__':
    unittest.main()
