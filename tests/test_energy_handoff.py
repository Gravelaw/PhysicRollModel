"""Analytic, conservation, unit and continuity checks for the optional energy ledger."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import math
import random
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from physicroll.model import Scenario
from physicroll.materials import MaterialState, PowerHardeningLaw, BiteHardening
from physicroll.slab import solve_slab
from physicroll.energy_handoff import HeatCapacityCurve, PassHeatBoundary, handoff_pass
from physicroll.lubrication import FluidObservation
from scripts.run_flowing_energy_demo import run

ROOT=Path(__file__).resolve().parents[1]

class FlowingEnergyTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
        self.state=MaterialState('Al-demo','unknown',.1,('synthetic prior',),300.)
        self.law=PowerHardeningLaw('Al-demo','unknown',100e6,100e6,.3,'SYNTHETIC',True)
        self.material=BiteHardening(self.state,self.law,(0.,3.),(273.15,420.))
        self.s=replace(self.s,mean_flow_stress_pa=self.material.mean_stress(self.s.entry_thickness_m,self.s.exit_thickness_m))
        self.mechanics=solve_slab(self.s,256,material=self.material)
        self.strip_cp=HeatCapacityCurve('Al-demo',(250.,450.),(900.,900.),'SYNTHETIC STRIP','synthetic')
        self.roll_cp=HeatCapacityCurve('roll',(250.,450.),(500.,500.),'SYNTHETIC ROLL','synthetic')
        self.boundary=PassHeatBoundary(.2,.6,-2000.,5000.,3000.,500.,295.,5.,'SYNTHETIC','synthetic')

    def energy(self, mechanics=None, state=None, strip_cp=None, roll_cp=None, boundary=None):
        return handoff_pass(mechanics or self.mechanics,state or self.state,
                            strip_cp or self.strip_cp,roll_cp or self.roll_cp,
                            boundary or self.boundary)

    def test_piecewise_heat_capacity_integral_and_inverse(self):
        cp=HeatCapacityCurve('Al-demo',(300.,400.,500.),(1000.,1200.,1400.),'SYNTHETIC','synthetic')
        self.assertAlmostEqual(cp.enthalpy_j_kg(350.),52500.)
        self.assertAlmostEqual(cp.enthalpy_j_kg(450.),172500.)
        for t in (300.,320.,400.,470.,500.):
            self.assertAlmostEqual(cp.temperature_for_enthalpy(cp.enthalpy_j_kg(t)),t,places=11)
        with self.assertRaises(ValueError):cp.enthalpy_j_kg(299.99)
        with self.assertRaises(ValueError):cp.temperature_for_enthalpy(-1.)
        with self.assertRaises(ValueError):cp.temperature_for_enthalpy(240001.)
        with self.assertRaises(ValueError):replace(cp,heat_capacity_j_kg_k=(.9,1.2,1.4)).validate()
        with self.assertRaises(ValueError):replace(cp,temperature_k=(300.,300.,500.)).validate()
        with self.assertRaises(ValueError):replace(cp,quality='calibrated').validate()

    def test_independent_constant_cp_solution_and_full_energy_balance(self):
        r=self.energy();p=self.mechanics;b=self.boundary
        strip_rate=.2*p['plastic_work_power_w']+.6*p['solid_slip_dissipation_both_interfaces_w']-2000-5000
        roll_rate=.4*p['solid_slip_dissipation_both_interfaces_w']+2000-3000
        self.assertAlmostEqual(r['strip_temperature_out_k'],300+strip_rate/(p['mass_flow_kg_s']*900),places=11)
        self.assertAlmostEqual(r['roll_temperature_out_k'],295+roll_rate*5/(500*500),places=11)
        self.assertAlmostEqual(r['contact_heat_to_strip_w']+r['contact_heat_to_roll_w'],0)
        self.assertAlmostEqual(r['solid_slip_heat_to_strip_w']+r['solid_slip_heat_to_roll_w'],
                               p['solid_slip_dissipation_both_interfaces_w'],places=8)
        self.assertAlmostEqual(r['plastic_heat_w']+r['nonthermal_plastic_work_w'],p['plastic_work_power_w'],places=8)
        self.assertLess(abs(r['thermal_allocation_residual_w']),1e-7)
        self.assertAlmostEqual(r['combined_mechanical_to_outlets_residual_w'],
                               p['mechanical_work_residual_w']-r['thermal_allocation_residual_w'],places=7)
        # Integrate the steady stream over the roll interval: kg/s*s differs
        # from the roll's fixed kg, and each W term becomes J only once.
        dt=b.duration_s
        sensible_j=(p['mass_flow_kg_s']*dt*900*(r['strip_temperature_out_k']-300)
                    +b.roll_effective_mass_kg*500*(r['roll_temperature_out_k']-295))
        outgoing_j=sensible_j+dt*(r['nonthermal_plastic_work_w']+b.strip_cooling_w+b.roll_cooling_w)
        incoming_j=dt*(p['roll_mechanical_power_both_rolls_w']+p['net_tension_power_w'])
        self.assertAlmostEqual(incoming_j-outgoing_j,dt*p['mechanical_work_residual_w'],places=6)
        self.assertIn('NO_TEMPERATURE_FEEDBACK_IN_MECHANICS',r['flags'])
        self.assertFalse(r['temperature_feedback_to_mechanics'])

    def test_zero_sliding_partition_bounds_and_contact_sign(self):
        p=dict(self.mechanics)
        p['solid_slip_dissipation_both_interfaces_w']=0.
        p['roll_mechanical_power_both_rolls_w']=p['plastic_work_power_w']-p['net_tension_power_w']
        p['mechanical_work_residual_w']=0.
        p['mechanical_work_residual_relative']=0.
        z=self.energy(mechanics=p)
        self.assertEqual(z['solid_slip_heat_to_strip_w'],0)
        self.assertEqual(z['solid_slip_heat_to_roll_w'],0)
        b=replace(self.boundary,plastic_to_heat_fraction=0.,solid_slip_to_strip_fraction=0.,
                  contact_heat_to_strip_w=0.,strip_cooling_w=0.,roll_cooling_w=0.)
        none=self.energy(boundary=b)
        self.assertAlmostEqual(none['nonthermal_plastic_work_w'],self.mechanics['plastic_work_power_w'])
        self.assertEqual(none['strip_temperature_out_k'],300.)
        self.assertGreater(none['roll_temperature_out_k'],295.)
        all_heat=self.energy(boundary=replace(b,plastic_to_heat_fraction=1.,solid_slip_to_strip_fraction=1.))
        self.assertEqual(all_heat['nonthermal_plastic_work_w'],0.)
        self.assertEqual(all_heat['solid_slip_heat_to_roll_w'],0.)
        self.assertEqual(all_heat['roll_temperature_out_k'],295.)
        contact=self.energy(boundary=replace(self.boundary,contact_heat_to_strip_w=2000.))
        self.assertGreater(contact['strip_temperature_out_k'],self.energy()['strip_temperature_out_k'])
        self.assertLess(contact['roll_temperature_out_k'],self.energy()['roll_temperature_out_k'])
        self.assertAlmostEqual(contact['contact_heat_to_strip_w'],-contact['contact_heat_to_roll_w'])

    def test_units_scaling_and_property_domain(self):
        p=dict(self.mechanics)
        for name in ('mass_flow_kg_s','plastic_work_power_w','solid_slip_dissipation_both_interfaces_w',
                     'mechanical_work_residual_w','roll_mechanical_power_both_rolls_w','net_tension_power_w'):
            p[name]*=2
        b=replace(self.boundary,contact_heat_to_strip_w=2*self.boundary.contact_heat_to_strip_w,
                  strip_cooling_w=2*self.boundary.strip_cooling_w,
                  roll_cooling_w=2*self.boundary.roll_cooling_w,
                  roll_effective_mass_kg=2*self.boundary.roll_effective_mass_kg)
        a=self.energy();d=self.energy(mechanics=p,boundary=b)
        self.assertAlmostEqual(a['strip_temperature_out_k'],d['strip_temperature_out_k'],places=11)
        self.assertAlmostEqual(a['roll_temperature_out_k'],d['roll_temperature_out_k'],places=11)
        self.assertAlmostEqual(2*a['flowing_strip_enthalpy_gain_w'],d['flowing_strip_enthalpy_gain_w'],places=7)
        with self.assertRaises(ValueError):self.energy(boundary=replace(self.boundary,contact_heat_to_strip_w=-2e6))
        with self.assertRaises(ValueError):self.energy(boundary=replace(self.boundary,strip_cooling_w=-1))
        with self.assertRaises(ValueError):self.energy(boundary=replace(self.boundary,plastic_to_heat_fraction=1.01))
        with self.assertRaises(ValueError):self.energy(boundary=replace(self.boundary,roll_effective_mass_kg=0))
        with self.assertRaises(ValueError):self.energy(boundary=replace(self.boundary,duration_s=True))
        with self.assertRaises(ValueError):self.energy(strip_cp=replace(self.strip_cp,material_id='wrong'))
        with self.assertRaises(ValueError):self.energy(mechanics={**self.mechanics,'mass_flow_kg_s':0})
        with self.assertRaises(ValueError):self.energy(mechanics={**self.mechanics,'mechanical_work_residual_w':12345.})

    def test_material_coordinate_and_temperature_contracts(self):
        with self.assertRaisesRegex(ValueError,'material-coordinate'):
            self.energy(state=replace(self.state,accumulated_equivalent_plastic_strain=.2))
        with self.assertRaisesRegex(ValueError,'mechanics temperature'):
            p=dict(self.mechanics);p['material']={**p['material'],'temperature_feedback':True}
            self.energy(mechanics=p,state=replace(self.state,temperature_k=310.))
        carried=self.energy(state=replace(self.state,temperature_k=305.))
        self.assertIn('MECHANICS_REFERENCE_TEMPERATURE_DIFFERS_FROM_CURRENT_STRIP_STATE',carried['flags'])
        self.assertEqual(carried['strip_state_out']['history'],self.mechanics['material']['state_out']['history'])
        self.assertGreater(carried['strip_state_out']['accumulated_equivalent_plastic_strain'],self.state.accumulated_equivalent_plastic_strain)
        after=dict(self.mechanics['material']['state_out']);after['alloy']='wrong'
        p={**self.mechanics,'material':{**self.mechanics['material'],'state_out':after}}
        with self.assertRaisesRegex(ValueError,'alloy'):
            self.energy(mechanics=p)
        # Temperature is carried, but the deliberately temperature-independent
        # mechanical law gives the same force at a different declared temperature.
        warmer=replace(self.state,temperature_k=320.)
        m=solve_slab(self.s,256,material=replace(self.material,state=warmer))
        self.assertEqual(m['separating_force_n'],self.mechanics['separating_force_n'])

    def test_fluid_identity_is_observed_but_not_a_calibrated_closure(self):
        fluid=FluidObservation('demo neat oil','neat_oil',None,290.,None,None,None,'SYNTHETIC','synthetic')
        a=handoff_pass(self.mechanics,self.state,self.strip_cp,self.roll_cp,self.boundary,fluid=fluid)
        b=handoff_pass(self.mechanics,self.state,self.strip_cp,self.roll_cp,self.boundary,
                       fluid=replace(fluid,identity='another declared oil'))
        self.assertEqual(a['strip_temperature_out_k'],b['strip_temperature_out_k'])
        self.assertEqual(a['roll_temperature_out_k'],b['roll_temperature_out_k'])
        self.assertEqual(a['fluid_observation']['identity'],'demo neat oil')
        self.assertIn('FLUID_OBSERVATION_NOT_A_HEAT_OR_FRICTION_CLOSURE',a['flags'])
        with self.assertRaises(ValueError):
            handoff_pass(self.mechanics,self.state,self.strip_cp,self.roll_cp,self.boundary,
                         fluid=replace(fluid,flow_m3_s=-1))

    def test_two_pass_cli_continuity(self):
        with TemporaryDirectory() as directory,redirect_stdout(io.StringIO()):
            path=Path(directory)/'result.json'
            run(Path('scenarios/flowing_energy_demo.json'),path)
            data=json.loads(path.read_text())
        p1,p2=data['passes']
        self.assertEqual(p1['energy']['strip_state_out'],p2['energy']['strip_state_in'])
        self.assertEqual(p1['energy']['roll_temperature_out_k'],p2['energy']['boundary']['roll_temperature_k'])
        self.assertAlmostEqual(p1['energy']['mass_flow_kg_s'],p2['energy']['mass_flow_kg_s'])
        self.assertGreater(p2['energy']['strip_temperature_out_k'],p1['energy']['strip_temperature_out_k'])
        self.assertLess(data['max_thermal_allocation_residual_w'],1e-6)
        self.assertEqual(len(p2['energy']['strip_state_out']['history']),3)

    def test_property_knots_decreasing_cp_and_strict_endpoints(self):
        # This ordinary cp curve previously rejected its own upper endpoint.
        cp=HeatCapacityCurve('test',(250.,300.3,350.7,420.),
                             (707.02,764.2,886.72,578.96),'SYNTHETIC','synthetic')
        self.assertEqual(cp.temperature_for_enthalpy(cp.enthalpy_j_kg(420.)),420.)
        top=cp.enthalpy_j_kg(420.)
        with self.assertRaises(ValueError):cp.temperature_for_enthalpy(math.nextafter(top,math.inf))
        with self.assertRaises(ValueError):cp.temperature_for_enthalpy(math.nextafter(0.,-math.inf))
        # Independent analytic integral for decreasing cp: c=1000-2*(T-300).
        falling=HeatCapacityCurve('test',(300.,400.),(1000.,800.),'SYNTHETIC','synthetic')
        self.assertAlmostEqual(falling.enthalpy_j_kg(350.),47500.)
        self.assertAlmostEqual(falling.temperature_for_enthalpy(47500.),350.)
        rng=random.Random(412)
        for _ in range(100):
            temperatures=tuple(sorted([250.,450.]+[rng.uniform(250.,450.) for _ in range(8)]))
            capacities=tuple(rng.uniform(400.,1400.) for _ in temperatures)
            curve=HeatCapacityCurve('test',temperatures,capacities,'SYNTHETIC','synthetic')
            for t in temperatures:
                self.assertEqual(curve.temperature_for_enthalpy(curve.enthalpy_j_kg(t)),t)
            for a,b in zip(temperatures,temperatures[1:]):
                t=(a+b)/2
                self.assertAlmostEqual(curve.temperature_for_enthalpy(curve.enthalpy_j_kg(t)),t,places=10)

    def test_flowing_strip_duration_and_roll_step_composition(self):
        cp=replace(self.roll_cp,heat_capacity_j_kg_k=(400.,700.))
        one=self.energy(roll_cp=cp)
        short=replace(self.boundary,duration_s=self.boundary.duration_s/2)
        first=self.energy(roll_cp=cp,boundary=short)
        second=self.energy(roll_cp=cp,boundary=replace(short,roll_temperature_k=first['roll_temperature_out_k']))
        self.assertAlmostEqual(one['roll_temperature_out_k'],second['roll_temperature_out_k'],places=10)
        # Each half step processes fresh steady flow at the same strip inlet;
        # duration belongs to roll storage, not strip residence mass.
        self.assertEqual(one['strip_temperature_out_k'],first['strip_temperature_out_k'])
        self.assertEqual(one['strip_temperature_out_k'],second['strip_temperature_out_k'])
        self.assertAlmostEqual(cp.enthalpy_j_kg(one['roll_temperature_out_k'])-cp.enthalpy_j_kg(295.),
                               2*(cp.enthalpy_j_kg(first['roll_temperature_out_k'])-cp.enthalpy_j_kg(295.)),places=7)
        same_capacity_time=self.energy(boundary=replace(self.boundary,duration_s=5000.,roll_effective_mass_kg=500000.))
        self.assertAlmostEqual(same_capacity_time['roll_temperature_out_k'],self.energy()['roll_temperature_out_k'])

    def test_zero_source_flow_and_pure_contact_budget(self):
        p=dict(self.mechanics)
        for name in ('plastic_work_power_w','solid_slip_dissipation_both_interfaces_w',
                     'roll_mechanical_power_both_rolls_w','net_tension_power_w',
                     'mechanical_work_residual_w','mechanical_work_residual_relative'):
            p[name]=0.
        b=replace(self.boundary,contact_heat_to_strip_w=0.,strip_cooling_w=0.,roll_cooling_w=0.)
        z=self.energy(mechanics=p,boundary=b)
        self.assertEqual(z['strip_temperature_out_k'],300.)
        self.assertEqual(z['roll_temperature_out_k'],295.)
        self.assertEqual(z['thermal_allocation_residual_w'],0.)
        self.assertEqual(z['combined_mechanical_to_outlets_residual_w'],0.)
        exchange=self.energy(mechanics=p,boundary=replace(b,contact_heat_to_strip_w=-1000.))
        self.assertAlmostEqual(exchange['flowing_strip_enthalpy_gain_w'],-1000.,places=7)
        self.assertAlmostEqual(exchange['roll_thermal_storage_rate_w'],1000.,places=7)
        with self.assertRaises(ValueError):self.energy(mechanics={**p,'mass_flow_kg_s':0.},boundary=b)

    def test_thousand_million_scaling_and_regenerative_power(self):
        baseline=self.energy()
        for factor in (1e-3,1e3,1e6):
            p=dict(self.mechanics)
            for name in ('mass_flow_kg_s','plastic_work_power_w','solid_slip_dissipation_both_interfaces_w',
                         'mechanical_work_residual_w','roll_mechanical_power_both_rolls_w','net_tension_power_w'):
                p[name]*=factor
            b=replace(self.boundary,contact_heat_to_strip_w=-2000.*factor,
                      strip_cooling_w=5000.*factor,roll_cooling_w=3000.*factor,
                      roll_effective_mass_kg=500.*factor)
            result=self.energy(mechanics=p,boundary=b)
            self.assertAlmostEqual(result['strip_temperature_out_k'],baseline['strip_temperature_out_k'],places=10)
            self.assertAlmostEqual(result['roll_temperature_out_k'],baseline['roll_temperature_out_k'],places=10)
        p=dict(self.mechanics)
        p['net_tension_power_w']+=1e6;p['roll_mechanical_power_both_rolls_w']-=1e6
        p['mechanical_work_residual_w']=(p['roll_mechanical_power_both_rolls_w']+p['net_tension_power_w']
            -p['plastic_work_power_w']-p['solid_slip_dissipation_both_interfaces_w'])
        p['mechanical_work_residual_relative']=abs(p['mechanical_work_residual_w'])/max(
            abs(p['roll_mechanical_power_both_rolls_w']),abs(p['net_tension_power_w']),
            p['plastic_work_power_w'],p['solid_slip_dissipation_both_interfaces_w'])
        self.assertLess(p['roll_mechanical_power_both_rolls_w'],0.)
        self.assertEqual(self.energy(mechanics=p)['strip_temperature_out_k'],baseline['strip_temperature_out_k'])

    def test_reject_false_mechanical_residual_and_feedback_metadata(self):
        for value in (-1.,0.,1e-3):
            with self.assertRaises(ValueError):
                self.energy(mechanics={**self.mechanics,'mechanical_work_residual_relative':value})
        for value in (True,None,0):
            with self.assertRaisesRegex(ValueError,'temperature feedback'):
                self.energy(mechanics={**self.mechanics,'material':{**self.mechanics['material'],'temperature_feedback':value}})
        p=dict(self.mechanics)
        p['roll_mechanical_power_both_rolls_w']+=1000.
        p['mechanical_work_residual_w']+=1000.
        p['mechanical_work_residual_relative']=0.
        with self.assertRaisesRegex(ValueError,'relative work residual'):self.energy(mechanics=p)

    def test_enforce_material_temperature_envelope_and_history(self):
        p={**self.mechanics,'material':{**self.mechanics['material'],'assumed_temperature_range_k':(299.,301.)}}
        with self.assertRaisesRegex(ValueError,'outgoing strip temperature'):self.energy(mechanics=p)
        with self.assertRaisesRegex(ValueError,'incoming strip temperature'):
            self.energy(state=replace(self.state,temperature_k=430.))
        for interval in (None,(300.,300.),(True,400.)):
            with self.assertRaisesRegex(ValueError,'temperature range'):
                self.energy(mechanics={**self.mechanics,'material':{**self.mechanics['material'],'assumed_temperature_range_k':interval}})
        for changed in ({'accumulated_equivalent_plastic_strain':0.},
                        {'history':('different prior','pass')},
                        {'history':self.state.history},
                        {'temperature_k':310.}):
            p={**self.mechanics,'material':{**self.mechanics['material'],
                'state_out':{**self.mechanics['material']['state_out'],**changed}}}
            with self.assertRaises(ValueError):self.energy(mechanics=p)

if __name__=='__main__':unittest.main()
