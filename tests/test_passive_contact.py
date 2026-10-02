"""Independent reduced-contact solution and adversarial boundary checks."""
from dataclasses import replace
from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from physicroll.energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                                      PassiveContactBoundary, handoff_pass)
from physicroll.materials import BiteHardening, MaterialState, PowerHardeningLaw
from physicroll.model import Scenario
from physicroll.slab import solve_slab
from scripts.run_flowing_energy_demo import run

ROOT=Path(__file__).resolve().parents[1]


class PassiveContactTests(unittest.TestCase):
    def setUp(self):
        scenario=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
        self.state=MaterialState('Al-demo','unknown',.1,('synthetic prior',),300.)
        law=PowerHardeningLaw('Al-demo','unknown',100e6,100e6,.3,'SYNTHETIC',True)
        material=BiteHardening(self.state,law,(0.,3.),(273.15,420.))
        scenario=replace(scenario,mean_flow_stress_pa=material.mean_stress(
            scenario.entry_thickness_m,scenario.exit_thickness_m))
        self.mechanics=solve_slab(scenario,256,material=material)
        self.scp=HeatCapacityCurve('Al-demo',(250.,450.),(900.,900.),'SYNTHETIC','synthetic')
        self.rcp=HeatCapacityCurve('roll',(250.,450.),(500.,500.),'SYNTHETIC','synthetic')
        self.boundary=PassHeatBoundary(.2,.6,0.,5000.,3000.,500.,295.,5.,'SYNTHETIC','synthetic')
        self.contact=PassiveContactBoundary(1000.,'SYNTHETIC','synthetic')

    def run_energy(self, *, mechanics=None, state=None, scp=None, rcp=None, boundary=None, contact=None):
        return handoff_pass(self.mechanics if mechanics is None else mechanics,
                            self.state if state is None else state,
                            self.scp if scp is None else scp,
                            self.rcp if rcp is None else rcp,
                            self.boundary if boundary is None else boundary,
                            passive_contact=self.contact if contact is None else contact)

    def zero_mechanics(self):
        p=dict(self.mechanics)
        for key in ('plastic_work_power_w','solid_slip_dissipation_both_interfaces_w',
                    'roll_mechanical_power_both_rolls_w','net_tension_power_w',
                    'mechanical_work_residual_w','mechanical_work_residual_relative'):
            p[key]=0.
        return p

    def test_independent_constant_cp_solution_and_energy(self):
        r=self.run_energy(); p=self.mechanics;b=self.boundary;g=self.contact.conductance_w_k
        cs=p['mass_flow_kg_s']*900.;cr=b.roll_effective_mass_kg*500./b.duration_s
        a=.2*p['plastic_work_power_w']+.6*p['solid_slip_dissipation_both_interfaces_w']-b.strip_cooling_w
        d=.4*p['solid_slip_dissipation_both_interfaces_w']-b.roll_cooling_w
        q=g*(295.-300.+d/(2*cr)-a/(2*cs))/(1+g*(1/cs+1/cr)/2)
        self.assertAlmostEqual(r['contact_heat_to_strip_w'],q,places=7)
        self.assertAlmostEqual(r['strip_temperature_out_k'],300.+(a+q)/cs,places=10)
        self.assertAlmostEqual(r['roll_temperature_out_k'],295.+(d-q)/cr,places=10)
        self.assertAlmostEqual(r['contact_heat_to_strip_w'],-r['contact_heat_to_roll_w'])
        self.assertLess(abs(r['contact_law_residual_w']),1e-7)
        self.assertGreaterEqual(r['contact_entropy_production_w_k'],0.)
        self.assertLess(abs(r['thermal_allocation_residual_w']),1e-7)
        self.assertAlmostEqual(r['combined_mechanical_to_outlets_residual_w'],
                               p['mechanical_work_residual_w']-r['thermal_allocation_residual_w'],places=7)

    def test_passivity_zero_equal_and_reverse_temperature(self):
        p=self.zero_mechanics();b=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.)
        z=self.run_energy(mechanics=p,boundary=b,
                          contact=replace(self.contact,conductance_w_k=0.))
        old=handoff_pass(p,self.state,self.scp,self.rcp,b)
        self.assertEqual(z['strip_temperature_out_k'],old['strip_temperature_out_k'])
        self.assertEqual(z['roll_temperature_out_k'],old['roll_temperature_out_k'])
        self.assertEqual(z['contact_heat_to_strip_w'],0.)
        equal=self.run_energy(mechanics=p,boundary=replace(b,roll_temperature_k=300.))
        self.assertAlmostEqual(equal['contact_heat_to_strip_w'],0.)
        for roll_t,sign in ((310.,1),(290.,-1)):
            r=self.run_energy(mechanics=p,boundary=replace(b,roll_temperature_k=roll_t))
            self.assertGreater(sign*r['contact_heat_to_strip_w'],0.)
            self.assertGreaterEqual(r['contact_entropy_production_w_k'],0.)
            self.assertLess(abs(r['thermal_allocation_residual_w']),1e-8)

    def test_large_conductance_refinement_and_variable_cp(self):
        p=self.zero_mechanics();b=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.,roll_temperature_k=320.)
        variable=replace(self.scp,temperature_k=(250.,300.,350.,450.),
                         heat_capacity_j_kg_k=(600.,900.,1100.,700.))
        with self.assertRaisesRegex(ValueError, 'passive contact.*domain'):
            self.run_energy(mechanics=p,boundary=b,scp=variable,
                            contact=replace(self.contact,conductance_w_k=1e8))
        # Repeating steady-flow substeps should converge toward the same roll
        # interval solution as the substep size shrinks, not equal one coarse step.
        def advance(n):
            temp=320.;first=None
            for _ in range(n):
                step=self.run_energy(mechanics=p,scp=variable,
                     boundary=replace(b,roll_temperature_k=temp,duration_s=b.duration_s/n))
                temp=step['roll_temperature_out_k']
                if first is None:first=step['strip_temperature_out_k']
            return temp,first
        t4,_=advance(4);t8,_=advance(8);t16,_=advance(16)
        self.assertLess(abs(t16-t8),abs(t8-t4))
        self.assertTrue(all(math.isfinite(v) for v in (t4,t8,t16)))

    def test_i01_temporal_and_stream_counterexamples_rejected(self):
        p=self.zero_mechanics()
        for mass,dt in ((1.,5.),(500.,.001),(500.,.00001)):
            with self.subTest(mass=mass,dt=dt):
                cs=p['mass_flow_kg_s']*900.;cr=mass*500./dt;g=1e6
                q=g*20/(1+g/(2*cs)+g/(2*cr))
                ts,tr=300+q/cs,320-q/cr
                self.assertTrue(ts>320 or tr<300)
                entropy=cs*math.log(ts/300)+cr*math.log(tr/320)
                self.assertEqual(entropy<0,mass==1.)
                b=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.,
                          roll_temperature_k=320.,roll_effective_mass_kg=mass,duration_s=dt)
                with self.assertRaisesRegex(ValueError,'passive contact.*domain'):
                    self.run_energy(mechanics=p,boundary=b,
                                    contact=replace(self.contact,conductance_w_k=g))

    def test_pure_exchange_entropy_and_supported_boundary(self):
        p=self.zero_mechanics();cs=p['mass_flow_kg_s']*900.
        for roll_t in (280.,300.,320.):
            b=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.,
                      roll_temperature_k=roll_t,roll_effective_mass_kg=cs*5/500.)
            r=self.run_energy(mechanics=p,boundary=b,
                              contact=replace(self.contact,conductance_w_k=2*cs))
            ts,tr=r['strip_temperature_out_k'],r['roll_temperature_out_k']
            self.assertTrue(min(300.,roll_t)-1e-9<=ts<=max(300.,roll_t)+1e-9)
            self.assertTrue(min(300.,roll_t)-1e-9<=tr<=max(300.,roll_t)+1e-9)
            exact=cs*math.log(ts/300)+cs*math.log(tr/roll_t)
            self.assertAlmostEqual(r['pure_exchange_entropy_rate_w_k'],exact,places=9)
            self.assertGreaterEqual(exact,-1e-8)
            with self.assertRaisesRegex(ValueError,'passive contact.*domain'):
                self.run_energy(mechanics=p,boundary=b,
                    contact=replace(self.contact,conductance_w_k=2*cs*(1+1e-8)))

    def test_entropy_integral_and_heated_case_semantics(self):
        cp=replace(self.scp,temperature_k=(250.,300.,350.,450.),
                   heat_capacity_j_kg_k=(1200.,900.,1100.,700.))
        a,b=280.,400.
        n=20000;h=(b-a)/n
        def f(t):
            j=cp._location(t)
            v=cp.heat_capacity_j_kg_k[j]+(t-cp.temperature_k[j])*(
                cp.heat_capacity_j_kg_k[j+1]-cp.heat_capacity_j_kg_k[j])/(cp.temperature_k[j+1]-cp.temperature_k[j])
            return v/t
        numerical=h/3*math.fsum(f(a+i*h)*(1 if i in (0,n) else 4 if i%2 else 2) for i in range(n+1))
        exact=cp.entropy_change_j_kg_k(a,b)
        self.assertAlmostEqual(exact,numerical,places=6)
        self.assertEqual(exact,-cp.entropy_change_j_kg_k(b,a))
        self.assertAlmostEqual(exact,cp.entropy_change_j_kg_k(a,350.)+cp.entropy_change_j_kg_k(350.,b),places=12)
        with self.assertRaises(ValueError):cp.entropy_change_j_kg_k(249.,b)
        r=self.run_energy()
        self.assertGreater(r['strip_temperature_out_k'],300.)
        self.assertIsNone(r['pure_exchange_entropy_rate_w_k'])
        self.assertEqual(r['entropy_balance_scope'],'INCOMPLETE_WITH_SOURCES_OR_EXPORTS')

    def test_variable_cp_exchange_and_source_bounds(self):
        p=self.zero_mechanics()
        scp=replace(self.scp,temperature_k=(280.,305.,350.),heat_capacity_j_kg_k=(1100.,700.,950.))
        rcp=replace(self.rcp,temperature_k=(290.,310.,400.),heat_capacity_j_kg_k=(400.,600.,450.))
        for roll_t in (295.,330.):
            b=replace(self.boundary,roll_temperature_k=roll_t,strip_cooling_w=0.,roll_cooling_w=0.)
            r=self.run_energy(mechanics=p,scp=scp,rcp=rcp,boundary=b,
                              contact=replace(self.contact,conductance_w_k=12000.))
            for key in ('strip_temperature_out_k','roll_temperature_out_k'):
                self.assertTrue(min(300.,roll_t)<=r[key]<=max(300.,roll_t))
            self.assertGreaterEqual(r['pure_exchange_entropy_rate_w_k'],-1e-8)
        # Admitted source-driven cooling below both inlets is legitimate.
        b=replace(self.boundary,strip_cooling_w=100000.,roll_cooling_w=100000.)
        r=self.run_energy(mechanics=p,boundary=b)
        self.assertLess(r['strip_temperature_out_k'],295.)
        self.assertIsNone(r['pure_exchange_entropy_rate_w_k'])
        # Equal net powers do not identify the missing cooling entropy transfer.
        b=replace(self.boundary,strip_cooling_w=.2*self.mechanics['plastic_work_power_w']+
                  .6*self.mechanics['solid_slip_dissipation_both_interfaces_w'],
                  roll_cooling_w=.4*self.mechanics['solid_slip_dissipation_both_interfaces_w'])
        r=self.run_energy(boundary=b)
        self.assertIsNone(r['pure_exchange_entropy_rate_w_k'])
        self.assertEqual(r['entropy_balance_scope'],'INCOMPLETE_WITH_SOURCES_OR_EXPORTS')

    def test_zero_g_endpoints_and_numerical_capacity_rejection(self):
        p=self.zero_mechanics()
        b=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.,roll_temperature_k=450.)
        r=self.run_energy(mechanics=p,boundary=b,contact=replace(self.contact,conductance_w_k=0.))
        self.assertEqual(r['strip_temperature_out_k'],300.)
        self.assertEqual(r['roll_temperature_out_k'],450.)
        self.assertEqual(r['pure_exchange_entropy_rate_w_k'],0.)
        for mass,dt in ((1e308,1e-308),(1e-308,1e308)):
            with self.assertRaisesRegex(ValueError,'passive contact.*domain'):
                self.run_energy(mechanics=p,boundary=replace(b,roll_effective_mass_kg=mass,duration_s=dt))
        # Very small but supported G recovers the uncoupled limit.
        r=self.run_energy(mechanics=p,boundary=replace(b,roll_temperature_k=320.),
                          contact=replace(self.contact,conductance_w_k=1e-8))
        self.assertAlmostEqual(r['strip_temperature_out_k'],300.,places=8)
        self.assertAlmostEqual(r['roll_temperature_out_k'],320.,places=8)

    def test_units_scaling_and_rejections(self):
        base=self.run_energy()
        factor=1000.
        p=dict(self.mechanics)
        for key in ('mass_flow_kg_s','plastic_work_power_w','solid_slip_dissipation_both_interfaces_w',
                    'mechanical_work_residual_w','roll_mechanical_power_both_rolls_w','net_tension_power_w'):
            p[key]*=factor
        b=replace(self.boundary,strip_cooling_w=self.boundary.strip_cooling_w*factor,
                  roll_cooling_w=self.boundary.roll_cooling_w*factor,
                  roll_effective_mass_kg=self.boundary.roll_effective_mass_kg*factor)
        scaled=self.run_energy(mechanics=p,boundary=b,
             contact=replace(self.contact,conductance_w_k=self.contact.conductance_w_k*factor))
        self.assertAlmostEqual(base['strip_temperature_out_k'],scaled['strip_temperature_out_k'],places=9)
        self.assertAlmostEqual(base['roll_temperature_out_k'],scaled['roll_temperature_out_k'],places=9)
        self.assertAlmostEqual(base['contact_heat_to_strip_w']*factor,scaled['contact_heat_to_strip_w'],places=6)
        for value in (-1.,float('nan'),True,1e308):
            with self.assertRaises(ValueError):
                self.run_energy(contact=replace(self.contact,conductance_w_k=value))
        with self.assertRaisesRegex(ValueError,'mutually exclusive'):
            self.run_energy(boundary=replace(self.boundary,contact_heat_to_strip_w=1.))
        with self.assertRaisesRegex(ValueError,'already contain slip heat'):
            self.run_energy(contact=replace(self.contact,law_scope='fitted_effective'))
        with self.assertRaises(ValueError):
            self.run_energy(contact=replace(self.contact,source=''))
        with self.assertRaisesRegex(ValueError,'domain'):
            self.run_energy(mechanics=self.zero_mechanics(),
                boundary=replace(self.boundary,strip_cooling_w=0.,roll_cooling_w=0.,roll_temperature_k=400.),
                scp=replace(self.scp,temperature_k=(299.9,300.1)),
                contact=replace(self.contact,conductance_w_k=1000.))

    def test_two_pass_synthetic_demo_and_legacy_artifact(self):
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            passive_path=Path(directory)/'passive.json'
            legacy_path=Path(directory)/'legacy.json'
            run(ROOT/'scenarios/passive_contact_demo.json',passive_path)
            run(ROOT/'scenarios/flowing_energy_demo.json',legacy_path)
            passive=json.loads(passive_path.read_text())
            legacy_bytes=legacy_path.read_bytes()
        self.assertEqual(legacy_bytes,(ROOT/'artifacts/flowing_energy_demo.json').read_bytes())
        # New diagnostic metadata is additive; historical numerical fields stay exact.
        historical=json.loads((ROOT/'artifacts/passive_contact_demo.json').read_text())
        projected=json.loads(json.dumps(passive))
        for item in projected['passes']:
            for key in ('contact_entropy_scope','passive_contact_domain',
                        'pure_exchange_entropy_rate_w_k','entropy_balance_scope'):
                del item['energy'][key]
        self.assertEqual(projected,historical)
        first,second=passive['passes']
        self.assertEqual(first['energy']['strip_state_out'],second['energy']['strip_state_in'])
        self.assertEqual(first['energy']['roll_temperature_out_k'],second['energy']['boundary']['roll_temperature_k'])
        self.assertEqual(first['energy']['contact_mode'],'PASSIVE_SUPPLIED_TOTAL_CONDUCTANCE')
        self.assertTrue(all(p['energy']['contact_entropy_production_w_k']>=0 for p in passive['passes']))

    def test_property_bracket_endpoint_roundoff_still_finds_interior_root(self):
        # The upper Q bracket once reconstructed roll H a few ULP outside its
        # lower knot, despite the physical root lying well inside both ranges.
        p=self.zero_mechanics();p['mass_flow_kg_s']=85.
        state=replace(self.state,temperature_k=306.)
        scp=replace(self.scp,heat_capacity_j_kg_k=(420.,420.))
        rcp=replace(self.rcp,heat_capacity_j_kg_k=(516.,516.))
        b=replace(self.boundary,strip_cooling_w=7794.,roll_cooling_w=6275.,
                  roll_effective_mass_kg=152.,roll_temperature_k=294.,duration_s=13.)
        g=1448.;cs=85.*420.;cr=152.*516./13.
        a=-7794.;d=-6275.
        expected=g*(294.-306.+d/(2*cr)-a/(2*cs))/(1+g*(1/cs+1/cr)/2)
        r=self.run_energy(mechanics=p,state=state,scp=scp,rcp=rcp,boundary=b,
                          contact=replace(self.contact,conductance_w_k=g))
        self.assertAlmostEqual(r['contact_heat_to_strip_w'],expected,places=7)
        self.assertGreaterEqual(r['contact_entropy_production_w_k'],0.)


if __name__=='__main__':unittest.main()
