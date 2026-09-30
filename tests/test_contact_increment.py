"""Independent equilibrium, closure, scaling and adversarial mechanics checks."""
import json
import math
import unittest
from pathlib import Path
from dataclasses import replace
from physicroll.model import Scenario
from physicroll.slab import solve_slab
from physicroll.materials import MaterialState, PowerHardeningLaw, BiteHardening
from physicroll.contact import CircularRollElasticity, solve_circular_contact
from physicroll.literature import load_case, simulate_schedule

ROOT=Path(__file__).resolve().parents[1]

class ContactIncrementTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
        self.law=PowerHardeningLaw('demo','unknown',70e6,160e6,.4,'synthetic test only')
        self.material=BiteHardening(MaterialState('demo','unknown',.12,('synthetic prior',),293.15),
                                   self.law,(0.,3.),(273.15,373.15))
        self.s=replace(self.s,mean_flow_stress_pa=self.material.mean_stress(self.s.entry_thickness_m,self.s.exit_thickness_m))
        self.elastic=CircularRollElasticity(210e9,.3,'assumed test steel; no calibration')

    def test_constant_material_exact_limit(self):
        law=replace(self.law,yield_stress_pa=self.s.mean_flow_stress_pa,strength_coefficient_pa=0)
        material=replace(self.material,law=law)
        a=solve_slab(self.s)
        b=solve_slab(self.s,material=material)
        for field in ('separating_force_n','torque_per_work_roll_nm','forward_slip_fraction','plastic_work_power_w'):
            self.assertAlmostEqual(a[field]/b[field],1,places=11)

    def test_history_spatial_work_and_refinement(self):
        a=solve_slab(self.s,64,material=self.material)
        b=solve_slab(self.s,256,material=self.material)
        self.assertTrue(b['numerical_converged'])
        self.assertLess(b['mechanical_work_residual_relative'],a['mechanical_work_residual_relative'])
        self.assertLess(b['mechanical_work_residual_relative'],1e-5)
        self.assertGreater(b['exit_plane_strain_strength_pa'],b['entry_plane_strain_strength_pa'])
        state=b['material']['state_out']
        self.assertEqual(state['history'],('synthetic prior',self.s.name))
        delta=2/math.sqrt(3)*math.log(self.s.entry_thickness_m/self.s.exit_thickness_m)
        exact=self.law.mean_stress(.12,.12+delta)*delta*b['volume_flow_m3_s']
        self.assertAlmostEqual(b['plastic_work_power_w']/exact,1,places=12)
        next_state=MaterialState(state['alloy'],state['temper'],state['accumulated_equivalent_plastic_strain'],state['history'],state['temperature_k'])
        next_material=replace(self.material,state=next_state)
        self.assertAlmostEqual(next_material.stress_at_thickness(.0015,.0015),b['exit_plane_strain_strength_pa']*math.sqrt(3)/2)

    def test_independent_variable_strength_pressure_reference(self):
        # Independent exponential midpoint for z=q-K, not production RK stages.
        s=self.s; n=4096; r=s.work_roll_radius_m
        dh=s.entry_thickness_m-s.exit_thickness_m
        L=math.sqrt(r*dh-dh*dh/4); dx=L/n; mu=s.friction_coefficient
        def k(x):
            y=L-x; h=s.exit_thickness_m+2*y*y/(r+math.sqrt(r*r-y*y))
            # Direct formula independent of BiteHardening convenience methods.
            e=.12+2/math.sqrt(3)*math.log(s.entry_thickness_m/h)
            return 2/math.sqrt(3)*(70e6+160e6*e**.4)
        def advance(z,x,step,sign):
            y=L-x-step/2; root=math.sqrt(r*r-y*y)
            h=s.exit_thickness_m+2*y*y/(r+root); hp=-2*y/root
            a=sign*2*mu/h; b=k(x+step/2)*(hp+sign*2*mu)/h
            return z*math.exp(a*step)+b/a*math.expm1(a*step)
        entry=[-s.entry_tension_pa]
        for i in range(n): entry.append(advance(entry[-1],i*dx,dx,1))
        back=[0]*(n+1);back[-1]=-s.exit_tension_pa
        for i in range(n,0,-1):back[i-1]=advance(back[i],i*dx,-dx,-1)
        q0=[z+k(i*dx) for i,z in enumerate(entry)];q1=[z+k(i*dx) for i,z in enumerate(back)]
        diff=[a-b for a,b in zip(q0,q1)]
        j=next(i for i in range(n) if diff[i]<0<diff[i+1])
        f=-diff[j]/(diff[j+1]-diff[j]);qn=q0[j]+f*(q0[j+1]-q0[j])
        A=sum((q0[i]+q0[i+1])*dx/2 for i in range(j))+(q0[j]+qn)*f*dx/2
        B=(qn+q1[j+1])*(1-f)*dx/2+sum((q1[i]+q1[i+1])*dx/2 for i in range(j+1,n))
        result=solve_slab(s,512,material=self.material)
        self.assertLess(abs(result['separating_force_n']/(s.width_m*(A+B))-1),2e-6)
        self.assertLess(abs(result['torque_per_work_roll_nm']/(s.width_m*r*mu*(A-B))-1),2e-6)

    def test_hitchcock_units_width_and_zero_force(self):
        e=self.elastic
        self.assertEqual(e.radius(.2,0,1,.001),.2)
        expected=.2*(1+16*(1-.3**2)/math.pi/210e9*2e6/.001)
        self.assertAlmostEqual(e.radius(.2,2e6,1,.001),expected)
        self.assertEqual(e.radius(.2,4e6,2,.001),e.radius(.2,2e6,1,.001))
        for E in (210,210000,True,float('nan')):
            with self.assertRaises(ValueError): replace(e,young_modulus_pa=E).validate()
        for nu in (.5,-.1,True):
            with self.assertRaises(ValueError):replace(e,poisson_ratio=nu).validate()
        with self.assertRaises(ValueError):e.radius(.2,2e6,1,0)
        with self.assertRaises(ValueError):e.radius(.2,2e9,1,.001)

    def test_coupling_residual_shaft_radius_and_independent_bisection(self):
        s=self.s;e=self.elastic
        o=solve_circular_contact(s,e,128,material=self.material)
        self.assertTrue(o['numerical_converged'])
        R=o['contact_radius_m'];self.assertGreater(R,s.work_roll_radius_m)
        self.assertLess(abs(e.radius(s.work_roll_radius_m,o['separating_force_n'],s.width_m,s.entry_thickness_m-s.exit_thickness_m)-R)/s.work_roll_radius_m,1e-8)
        self.assertAlmostEqual(o['roll_angular_speed_rad_s']*s.work_roll_radius_m,o['roll_surface_speed_m_s'])
        self.assertAlmostEqual(2*o['torque_per_work_roll_nm']*o['roll_angular_speed_rad_s'],o['roll_mechanical_power_both_rolls_w'])
        # Independent bracketed scalar root, same checked pressure problem.
        lo=s.work_roll_radius_m;hi=1.3*lo
        for _ in range(27):
            mid=(lo+hi)/2
            f=solve_slab(s,128,material=self.material,contact_radius_m=mid)['separating_force_n']
            target=e.radius(s.work_roll_radius_m,f,s.width_m,s.entry_thickness_m-s.exit_thickness_m)
            if target>mid:lo=mid
            else:hi=mid
        self.assertLess(abs(R-(lo+hi)/2)/s.work_roll_radius_m,3e-8)
        # If R_contact were accidentally used as torque arm this would fail.
        nominal=solve_slab(s,128,material=self.material,contact_radius_m=R)
        self.assertEqual(o['torque_per_work_roll_nm'],nominal['torque_per_work_roll_nm'])

    def test_rigid_limit_width_speed_and_nonconvergence(self):
        s=self.s;rigid=solve_slab(s)
        stiff=solve_circular_contact(s,replace(self.elastic,young_modulus_pa=1e14))
        self.assertLess(abs(stiff['separating_force_n']/rigid['separating_force_n']-1),.001)
        a=solve_circular_contact(s,self.elastic,64)
        b=solve_circular_contact(replace(s,width_m=2*s.width_m,entry_speed_m_s=3*s.entry_speed_m_s),self.elastic,64)
        self.assertEqual(a['contact_radius_m'],b['contact_radius_m'])
        self.assertAlmostEqual(b['separating_force_n']/a['separating_force_n'],2)
        self.assertAlmostEqual(b['roll_mechanical_power_both_rolls_w']/a['roll_mechanical_power_both_rolls_w'],6)
        failed=solve_circular_contact(s,self.elastic,max_iterations=1)
        self.assertFalse(failed['numerical_converged'])
        self.assertIn('FLATTENING_FIXED_POINT_NOT_CONVERGED',failed['flags'])

    def test_limits_tension_material_and_radius_reject(self):
        for s in (replace(self.s,friction_coefficient=0),replace(self.s,exit_thickness_m=self.s.entry_thickness_m,exit_tension_pa=self.s.entry_tension_pa)):
            with self.assertRaises(ValueError):solve_slab(s,material=self.material)
        z=solve_slab(replace(self.s,entry_tension_pa=0,exit_tension_pa=0),material=self.material)
        self.assertTrue(z['numerical_converged'])
        with self.assertRaises(ValueError):solve_slab(self.s,material=replace(self.material,assumed_strain_range=(0.,.13)))
        with self.assertRaises(ValueError):solve_slab(self.s,material=replace(self.material,state=replace(self.material.state,temperature_k=500)))
        with self.assertRaises(ValueError):solve_slab(self.s,contact_radius_m=2*self.s.work_roll_radius_m)
        with self.assertRaises(ValueError):solve_slab(self.s,material={})
        with self.assertRaises(ValueError):solve_slab(self.s,material=replace(self.material,law=replace(self.law,yield_stress_pa=0,strength_coefficient_pa=1)))
        b=solve_slab(self.s,material=self.material)
        front=solve_slab(replace(self.s,exit_tension_pa=self.s.exit_tension_pa+1e6),material=self.material)
        back=solve_slab(replace(self.s,entry_tension_pa=self.s.entry_tension_pa+1e6),material=self.material)
        self.assertGreater(front['forward_slip_fraction'],b['forward_slip_fraction'])
        self.assertLess(back['forward_slip_fraction'],b['forward_slip_fraction'])
        self.assertLess(front['torque_per_work_roll_nm'],b['torque_per_work_roll_nm'])
        self.assertGreater(back['torque_per_work_roll_nm'],b['torque_per_work_roll_nm'])

    def test_regenerative_signed_torque_and_zero_draft_limit(self):
        s=replace(self.s,exit_thickness_m=.99*self.s.entry_thickness_m,
                  entry_tension_pa=0,exit_tension_pa=.1*self.s.mean_flow_stress_pa)
        r=solve_slab(s,256,material=self.material)
        self.assertLess(r['torque_per_work_roll_nm'],0)
        self.assertLess(r['roll_mechanical_power_both_rolls_w'],0)
        self.assertGreater(r['solid_slip_dissipation_both_interfaces_w'],0)
        self.assertLess(r['mechanical_work_residual_relative'],1e-5)
        loads=[]
        for reduction in (1e-3,1e-5):
            tiny=replace(self.s,exit_thickness_m=self.s.entry_thickness_m*(1-reduction),
                         exit_tension_pa=self.s.entry_tension_pa)
            loads.append(solve_slab(tiny,256,material=self.material)['separating_force_n'])
        self.assertLess(loads[1],loads[0]/5)

    def test_fine_grid_coupling_entry_endpoint_and_baseline_regression(self):
        case=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
        gauges=[p['exit_thickness_m'] for p in case['passes'][:2]]
        args=dict(prior_log_strain=.05,strain_convention='log_thickness',
                  stress_convention='uniaxial',speed_interpretation='roll_surface',cells=512)
        original=simulate_schedule(case,gauges,**args)
        archived=json.loads((ROOT/'artifacts/aa5052/baseline.json').read_text())
        for a,b in zip(original['passes'],archived['passes']):
            for field in ('separating_force_n','torque_per_work_roll_nm','forward_slip_fraction'):
                self.assertAlmostEqual(a[field]/b[field],1,places=11)
        coupled=simulate_schedule(case,gauges,**args,hardening_model='spatial',elasticity=self.elastic)
        self.assertTrue(coupled['numerical_converged'])
        self.assertLess(max(p['mechanical_work_residual_relative'] for p in coupled['passes']),1e-5)
        # At specific iterated radii, an unqualified circular sagitta formerly
        # rounded the entry thickness above the exact boundary by one ULP.
        for p in coupled['passes']:
            self.assertAlmostEqual(p['entry_plane_strain_strength_pa']*math.sqrt(3)/2,
                                   p['assumed_entry_uniaxial_strength_pa'],places=5)

    def test_speed_hypotheses_and_state_carry(self):
        case=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
        gauges=[p['exit_thickness_m'] for p in case['passes'][:2]]
        args=dict(prior_log_strain=.05,strain_convention='log_thickness',stress_convention='uniaxial',hardening_model='spatial',cells=64)
        results=[simulate_schedule(case,gauges,**args,speed_interpretation=s) for s in ('roll_surface','entry_strip','exit_strip')]
        for run in results:
            for p,prev in zip(run['passes'][1:],run['passes']):
                self.assertEqual(p['material']['state_in'],prev['material']['state_out'])
        for i in range(3):
            a,b,c=(r['passes'][i] for r in results)
            for key in ('separating_force_n','torque_per_work_roll_nm','forward_slip_fraction'):
                self.assertEqual(a[key],b[key]);self.assertEqual(a[key],c[key])
            self.assertNotEqual(a['mass_flow_kg_s'],b['mass_flow_kg_s'])
            for row in (a,b,c):
                self.assertAlmostEqual(row['roll_angular_speed_rad_s']*row['physical_roll_radius_m'],row['roll_surface_speed_m_s'])

if __name__=='__main__':unittest.main()
