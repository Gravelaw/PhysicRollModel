from pathlib import Path
import unittest
from physicroll.literature import load_case,simulate_schedule,optimise_gauges

ROOT=Path(__file__).resolve().parents[1]

class LiteratureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
        cls.args=dict(prior_log_strain=.05,strain_convention='log_thickness',
                      stress_convention='uniaxial',speed_interpretation='roll_surface')
        cls.gauges=[.0029024,.0022087]
    def test_missing_history_and_speed_are_not_silently_filled(self):
        for changes in ({'prior_log_strain':0},{'speed_interpretation':None}):
            with self.assertRaises(ValueError):
                simulate_schedule(self.case,self.gauges,**{**self.args,**changes})
    def test_source_fixed_inputs_and_speed_interpretations(self):
        r=simulate_schedule(self.case,self.gauges,**self.args)
        alt=simulate_schedule(self.case,self.gauges,**{**self.args,'speed_interpretation':'entry_strip'})
        exit_case=simulate_schedule(self.case,self.gauges,**{**self.args,'speed_interpretation':'exit_strip'})
        self.assertTrue(r['numerical_converged'])
        for p,a,src in zip(r['passes'],alt['passes'],self.case['passes']):
            self.assertAlmostEqual(p['roll_surface_speed_m_s'],src['rolling_speed_m_s'])
            self.assertAlmostEqual(a['entry_speed_m_s'],src['rolling_speed_m_s'])
            self.assertAlmostEqual(p['separating_force_n'],a['separating_force_n'])
            self.assertAlmostEqual(p['forward_slip_fraction'],a['forward_slip_fraction'])
            self.assertAlmostEqual(p['mass_flow_residual_kg_s'],0)
            self.assertEqual(p['friction_coefficient'],src['friction_coefficient'])
        self.assertFalse(r['passes'][0]['unassisted_bite_feasible'])
        # Numerical solution of an already established pass is allowed, but not threading certification.
        self.assertIn('UNASSISTED_BITE_SCREEN_FAILED_ESTABLISHED_DIAGNOSTIC_ONLY',r['passes'][0]['flags'])
        for p,src in zip(exit_case['passes'],self.case['passes']):
            self.assertAlmostEqual(p['exit_speed_m_s'],src['rolling_speed_m_s'])
    def test_constrained_search_recheck(self):
        result=optimise_gauges(self.case,assumptions=self.args,grid_sizes=(5,),cells=32)
        chosen=result['selected']
        self.assertTrue(chosen['numerical_converged'])
        self.assertLessEqual(chosen['peak_force_n'],result['baseline']['peak_force_n'])
        for p in chosen['passes']:
            self.assertGreaterEqual(p['reduction_fraction'],result['trust_region']['reduction_min']-1e-12)
            self.assertLessEqual(p['reduction_fraction'],result['trust_region']['reduction_max']+1e-12)
        self.assertAlmostEqual(chosen['passes'][0]['entry_thickness_m'],.0041)
        self.assertAlmostEqual(chosen['passes'][-1]['exit_thickness_m'],.00172)
        self.assertFalse(result['global_optimum_proven'])
        self.assertTrue(any('UNOBSERVED_GAUGE_COMBINATION' in p['flags'] for p in chosen['passes']))

if __name__=='__main__':unittest.main()
