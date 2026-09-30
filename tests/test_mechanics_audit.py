import json
import math
from dataclasses import replace
from pathlib import Path
import unittest
from physicroll import Scenario
from physicroll.slab import solve_slab, _neutral_location
from physicroll.materials import PowerHardeningLaw, MaterialState, pass_with_history
from physicroll.profile import diagnose_profile
from physicroll.thermal import ThermalStep, step
from physicroll.units import to_si, from_si
from physicroll.literature import load_case

ROOT=Path(__file__).resolve().parents[1]

class UnitContractTests(unittest.TestCase):
    def test_exact_source_factors_and_roundtrip(self):
        for value,unit,dim,expected in [(4.1,'mm','length',.0041),
                (9.47,'MPa','stress',9470000),(5143.9,'kN','force',5143900),
                (2.68,'g/cm3','density',2680),(2.37,'%','dimensionless',.0237),
                (2,'kN*m','torque',2000),(60,'rpm','angular_speed',2*math.pi),
                (60,'m/min','speed',1),(2,'min','time',120),
                (20,'degC','absolute_temperature',293.15),(20,'delta_degC','temperature_difference',20)]:
            self.assertAlmostEqual(to_si(value,unit,dim),expected)
            self.assertAlmostEqual(from_si(expected,unit,dim),value)
    def test_wrong_dimensions_ambiguous_units_and_offsets(self):
        for unit,dim in [('Pa','line_load'),('N/m','stress'),('W/m','power'),
                         ('W/m2','volumetric_heat_source'),('kg/s','volume_flow'),
                         ('K','temperature_difference'),('C','absolute_temperature'),
                         ('kNm','torque'),('percent','dimensionless')]:
            with self.assertRaises(ValueError): to_si(1,unit,dim)
        with self.assertRaises(ValueError): to_si(-274,'degC','absolute_temperature')
    def test_source_import_regressions(self):
        c=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
        self.assertEqual(c['unit_audit']['converted_numeric_values'],49)
        p=c['passes'][0]
        self.assertAlmostEqual(p['work_roll_radius_m'],.21081)
        self.assertAlmostEqual(p['width_m'],1.36)
        self.assertEqual(c['K_pa'],276500000)
        self.assertEqual(c['density_kg_m3'],2680)
        self.assertEqual(c['measurements'][0]['force_n'],5143900)
        self.assertAlmostEqual(c['measurements'][0]['forward_slip_fraction'],.015)
        d=c['unit_audit']['derived'][0]
        self.assertAlmostEqual(d['back_tension_force_n'],52804.72)
        self.assertAlmostEqual(d['front_tension_force_n'],37380.59008)
        self.assertIsNone(c['unit_audit']['resolved_speed_mapping'])
        self.assertNotEqual(c['source_model_outputs'][2]['printed_slip_error_fraction'],
                            c['unit_audit']['derived'][2]['source_model_slip_error_fraction_recomputed'])
        # Independent decimal SI targets for all 49 imported numeric values.
        expected=[
            .0041,.0029024,1.36,9470000,9470000,.21081,4.2,.075,
            .0029024,.0022087,1.36,8680000,8110000,.21081,4.7,.071,
            .0022087,.00172,1.36,7510000,7250000,.21081,4.0,.069,
            5143900,.015,5017400,.0182,4301800,.0227,
            5265700,.0154,.2251,.0237,.0267,
            5066500,.0187,.2345,.0098,.0275,
            4165900,.0216,.2384,-.0316,-.0484,
            276500000,.26,2680,70000000000]
        for row,target in zip(c['unit_audit']['values'],expected):
            self.assertTrue(math.isclose(row['si_value'],target,rel_tol=1e-12,abs_tol=1e-15),row)

class MechanicsAuditTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
    def test_neutral_on_node_and_nonunique(self):
        self.assertEqual(_neutral_location([-2,0,2],.1),.1)
        self.assertAlmostEqual(_neutral_location([-1,1],.2),.1)
        for d in ([0,1,2],[-1,0,0,1],[-1,1,-1],[1,2,3]):
            with self.assertRaises(ValueError): _neutral_location(d,.1)
    def test_work_identity_refinement_and_dimensions(self):
        a,b=(solve_slab(self.s,n) for n in (64,256))
        self.assertLess(b['mechanical_work_residual_relative'],a['mechanical_work_residual_relative'])
        self.assertLess(b['mechanical_work_residual_relative'],1e-5)
        self.assertTrue(b['numerical_converged'])
        scaled=solve_slab(replace(self.s,width_m=2*self.s.width_m,entry_speed_m_s=3*self.s.entry_speed_m_s))
        for key in ('separating_force_n','torque_per_work_roll_nm'):
            self.assertAlmostEqual(scaled[key]/b[key],2)
        for key in ('plastic_work_power_w','solid_slip_dissipation_both_interfaces_w','mass_flow_kg_s'):
            self.assertAlmostEqual(scaled[key]/b[key],6)
        self.assertAlmostEqual(b['roll_mechanical_power_both_rolls_w'],
            2*b['torque_per_work_roll_nm']*b['roll_surface_speed_m_s']/self.s.work_roll_radius_m)
    def test_yield_cap_and_bad_unit_inputs(self):
        with self.assertRaisesRegex(ValueError,'shear'):
            solve_slab(replace(self.s,friction_coefficient=.3,exit_thickness_m=.001))
        with self.assertRaises(ValueError):
            solve_slab(replace(self.s,entry_thickness_m=2.0,exit_thickness_m=1.5))
        with self.assertRaises(ValueError):
            solve_slab(replace(self.s,mean_flow_stress_pa=120))
    def test_small_draft_and_checked_flag(self):
        tiny=replace(self.s,exit_thickness_m=self.s.entry_thickness_m*(1-1e-5),exit_tension_pa=self.s.entry_tension_pa)
        r=solve_slab(tiny)
        self.assertGreater(r['solid_slip_dissipation_both_interfaces_w'],0)
        self.assertLess(r['separating_force_n'],1e5)
        self.assertFalse(solve_slab(self.s,verify_refinement=False)['numerical_converged'])
    def test_independent_exponential_midpoint_pressure_reference(self):
        # Independent exponential-midpoint integration of q'=A(x)q+B(x),
        # not the production RK4 stages. Compare force and signed torque.
        s=self.s; n=4096; r=s.work_roll_radius_m
        draft=s.entry_thickness_m-s.exit_thickness_m
        length=math.sqrt(r*draft-draft*draft/4); dx=length/n
        k=2/math.sqrt(3)*s.mean_flow_stress_pa; mu=s.friction_coefficient
        def advance(q,x,step,sign):
            y=length-x-step/2; root=math.sqrt(r*r-y*y)
            h=s.exit_thickness_m+2*y*y/(r+root); hp=-2*y/root
            a=sign*2*mu/h; b=k*hp/h
            return q*math.exp(a*step)+b/a*math.expm1(a*step)
        entry=[k-s.entry_tension_pa]
        for i in range(n):entry.append(advance(entry[-1],i*dx,dx,1))
        exit_=[0]*(n+1);exit_[-1]=k-s.exit_tension_pa
        for i in range(n,0,-1):exit_[i-1]=advance(exit_[i],i*dx,-dx,-1)
        diff=[a-b for a,b in zip(entry,exit_)]
        j=next(i for i in range(n) if diff[i]<0<diff[i+1])
        f=-diff[j]/(diff[j+1]-diff[j]); qn=entry[j]+f*(entry[j+1]-entry[j])
        entry_area=sum((entry[i]+entry[i+1])*dx/2 for i in range(j))+(entry[j]+qn)*f*dx/2
        exit_area=(qn+exit_[j+1])*(1-f)*dx/2+sum((exit_[i]+exit_[i+1])*dx/2 for i in range(j+1,n))
        result=solve_slab(s,512)
        self.assertLess(abs(result['separating_force_n']/(s.width_m*(entry_area+exit_area))-1),2e-6)
        self.assertLess(abs(result['torque_per_work_roll_nm']/(s.width_m*r*mu*(entry_area-exit_area))-1),2e-6)
    def test_hardening_small_interval_and_zero_initial_strength(self):
        law=PowerHardeningLaw('demo','unknown',0,276.5e6,.26,'declared synthetic bridge')
        self.assertAlmostEqual(law.mean_stress(1,1+1e-12)/law.stress(1),1,places=10)
        self.assertAlmostEqual(law.mean_stress(1e-300,1)/law.strength_coefficient_pa,1/1.26)
        with self.assertRaises(ValueError):
            pass_with_history(self.s,MaterialState('demo','unknown',0,('unknown',),293.15),law)
        with self.assertRaises(ValueError): law.stress(True)
        eq_factor=2/math.sqrt(3)
        converted=replace(law,strength_coefficient_pa=law.strength_coefficient_pa/eq_factor**law.exponent)
        self.assertAlmostEqual(converted.stress(eq_factor*.4),law.stress(.4))
    def test_profile_nonuniform_grid_invariance_and_curvature(self):
        kw={'temperature_k':300,'applied_tension_pa':1e6}
        a=diagnose_profile([0,.1,2],[.001,.0011,.003],[0,.1,2],[2,2,2],**kw)
        b=diagnose_profile([0,1,2],[.001,.002,.003],[0,1,2],[2,2,2],**kw)
        self.assertAlmostEqual(a['center_crown_m'],0)
        self.assertAlmostEqual(a['membrane_mismatch_rms'],b['membrane_mismatch_rms'])
        self.assertAlmostEqual(a['membrane_mismatch_rms'],1/math.sqrt(3))
        self.assertEqual(a['max_abs_curvature_inv_m'],2)
        self.assertEqual(a['through_thickness_curvature_range_inv_m'],0)
    def test_thermal_exchange_exact_limit_and_nonoscillation(self):
        # Cs=2, Cr=3 J/K, G=1 W/K. Difference decays exp[-(1/2+1/3)t].
        x=ThermalStep(400,300,2,3,1,1,.01,1,1,0,0,100,0,.5,1,0,0,300,300)
        errors=[]
        for n in (20,80):
            y=replace(x,duration_s=1/n)
            for _ in range(n):
                o=step(y)
                self.assertAlmostEqual(o['energy_residual_j'],0,places=10)
                y=replace(y,strip_temperature_k=o['strip_temperature_k'],roll_temperature_k=o['roll_temperature_k'])
            equilibrium=340
            exact=equilibrium+60*math.exp(-5/6)
            errors.append(abs(y.strip_temperature_k-exact))
            self.assertAlmostEqual(2*y.strip_temperature_k+3*y.roll_temperature_k,1700,places=9)
        self.assertLess(errors[1],errors[0]/3)
        with self.assertRaises(ValueError): step(replace(x,strip_mass_kg=1,roll_mass_kg=1,duration_s=1))
        with self.assertRaises(ValueError): step(replace(x,strip_mass_kg=1e308,strip_heat_capacity_j_kg_k=1e308))
        with self.assertRaises(ValueError): step(replace(x,signed_relative_slip_m_s=-1e-20))

if __name__=='__main__': unittest.main()
