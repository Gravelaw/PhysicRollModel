import dataclasses
import json
import math
from pathlib import Path
import unittest

from physicroll.model import Scenario
from physicroll.materials import MaterialState, PowerHardeningLaw, pass_with_history
from physicroll.thermal import ThermalStep, step
from physicroll.lubrication import FluidObservation, EffectiveFriction, declared_closure
from physicroll.profile import diagnose_profile
from physicroll.slab import solve_slab, _rk4

ROOT=Path(__file__).resolve().parents[1]


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
        self.state=MaterialState('Al demo','H0',0.1,('annealed:declared',),293.15)
        self.law=PowerHardeningLaw('Al demo','H0',100e6,200e6,0.5,'SYNTHETIC_EXAMPLE')

    def test_integral_and_history(self):
        a,b=.1,.4
        expected=100e6+200e6*(b**1.5-a**1.5)/(1.5*(b-a))
        self.assertAlmostEqual(self.law.mean_stress(a,b),expected)
        first=pass_with_history(self.s,self.state,self.law)
        next_s=dataclasses.replace(self.s,entry_thickness_m=self.s.exit_thickness_m,
            exit_thickness_m=self.s.exit_thickness_m*.75,
            entry_speed_m_s=first['baseline_mechanics']['exit_speed_m_s'])
        second=pass_with_history(next_s,MaterialState(**first['state_out']),self.law)
        self.assertGreater(second['mean_flow_stress_pa'],first['mean_flow_stress_pa'])
        self.assertEqual(len(second['state_out']['history']),3)
        self.assertAlmostEqual(second['baseline_mechanics']['mass_flow_kg_s'],
                               first['baseline_mechanics']['mass_flow_kg_s'])
        self.assertAlmostEqual(first['equivalent_plastic_strain_increment'],2/math.sqrt(3)*math.log(self.s.entry_thickness_m/self.s.exit_thickness_m))

    def test_identification_and_constant_limit(self):
        with self.assertRaises(ValueError):
            pass_with_history(self.s,dataclasses.replace(self.state,alloy='wrong'),self.law)
        constant=dataclasses.replace(self.law,strength_coefficient_pa=0)
        self.assertEqual(constant.mean_stress(.1,.3),constant.yield_stress_pa)


class ThermalTests(unittest.TestCase):
    def setUp(self):
        self.x=ThermalStep(300,320,2,10,900,450,.01,.001,.1,1000,.5,1e6,.2,.6,1000,10,20,290,290)

    def test_energy_contact_and_slip(self):
        r=step(self.x)
        self.assertAlmostEqual(r['contact_heat_to_strip_w'],-r['contact_heat_to_roll_w'])
        self.assertAlmostEqual(r['energy_residual_j'],0,places=8)
        self.assertEqual(r['plastic_heat_volumetric_w_m3'],500000)
        self.assertEqual(r['solid_slip_heat_flux_w_m2'],200000)
        zero=step(dataclasses.replace(self.x,signed_relative_slip_m_s=0))
        self.assertEqual(zero['solid_slip_heat_flux_w_m2'],0)
        with self.assertRaises(ValueError):
            step(dataclasses.replace(self.x,contact_law='fitted_effective'))

    def test_passive_cooling_refinement(self):
        x=dataclasses.replace(self.x,roll_temperature_k=300,plastic_power_w=0,
            signed_relative_slip_m_s=0,contact_conductance_w_m2_k=0,
            roll_cooling_conductance_w_k=0,strip_cooling_conductance_w_k=100,
            strip_coolant_temperature_k=290,duration_s=1)
        exact=290+10*math.exp(-100/(2*900))
        for n,tolerance in [(10,.004),(100,.0004)]:
            y=x
            for _ in range(n):
                out=step(dataclasses.replace(y,duration_s=1/n))
                y=dataclasses.replace(y,strip_temperature_k=out['strip_temperature_k'])
            self.assertLess(abs(y.strip_temperature_k-exact),tolerance)

    def test_rejections(self):
        with self.assertRaises(ValueError):
            step(dataclasses.replace(self.x,signed_relative_slip_m_s=-.2))
        with self.assertRaises(ValueError):
            step(dataclasses.replace(self.x,duration_s=50))


class ClosureTests(unittest.TestCase):
    def test_fluid_unknowns_and_identification(self):
        fluid=FluidObservation('demo oil','neat_oil',None,300,None,None,None,'SYNTHETIC','synthetic')
        f=EffectiveFriction(.08,'SYNTHETIC',False,False)
        out=declared_closure(fluid,f)
        self.assertIn('dynamic_viscosity_pa_s',out['unobserved_inputs'])
        self.assertFalse(out['film_dissipation_resolved'])
        with self.assertRaises(ValueError):
            declared_closure(fluid,dataclasses.replace(f,calibrated=True))

    def test_profile_fields_stay_distinct(self):
        p=diagnose_profile([-1,0,1],[.001,.0011,.001],[.01,0,-.01],[0,1,0],
                           temperature_k=293.15,applied_tension_pa=10e6)
        self.assertAlmostEqual(p['center_crown_m'],.0001)
        self.assertAlmostEqual(p['wedge_m'],0)
        self.assertIsNone(p['unloaded_wave_amplitude_m'])
        self.assertNotEqual(p['membrane_mismatch_rms'],p['through_thickness_curvature_range_inv_m'])


class SlabTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))

    def test_constant_gap_analytic_ode_reference(self):
        # At h'=0 the entry branch is q=q0 exp(2 mu x/h).
        q=100.0; h=.002; mu=.05; length=.01; n=100
        for i in range(n):
            q=_rk4(q,i*length/n,length/n,lambda x,y:2*mu*y/h)
        self.assertAlmostEqual(q,100*math.exp(2*mu*length/h),places=8)

    def test_refinement_and_signs(self):
        a,b,c=(solve_slab(self.s,n) for n in (128,256,512))
        self.assertLess(abs(c['separating_force_n']-b['separating_force_n']),
                        abs(b['separating_force_n']-a['separating_force_n']))
        self.assertLess(abs(c['torque_per_work_roll_nm']-b['torque_per_work_roll_nm']),
                        abs(b['torque_per_work_roll_nm']-a['torque_per_work_roll_nm']))
        self.assertTrue(0<c['neutral_position_from_entry_m']<c['contact_length_m'])
        self.assertGreater(c['forward_slip_fraction'],0)
        self.assertGreater(c['pressure_at_neutral_pa'],max(c['entry_pressure_pa'],c['exit_pressure_pa']))

    def test_no_neutral_is_flagged(self):
        with self.assertRaises(ValueError):
            solve_slab(dataclasses.replace(self.s,friction_coefficient=0))

    def test_tension_boundary_sensitivity(self):
        base=solve_slab(self.s)
        loaded=solve_slab(dataclasses.replace(self.s,
            entry_tension_pa=self.s.entry_tension_pa+5e6,
            exit_tension_pa=self.s.exit_tension_pa+5e6))
        self.assertLess(loaded['entry_pressure_pa'],base['entry_pressure_pa'])
        self.assertLess(loaded['exit_pressure_pa'],base['exit_pressure_pa'])
        self.assertLess(loaded['separating_force_n'],base['separating_force_n'])


if __name__=='__main__':
    unittest.main()
