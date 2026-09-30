import math
import unittest
from physicroll.observations import (tension_stress_pa,strip_mass_flow_kg_s,
    tension_from_wrap_reaction_n,hydraulic_differential_thrust_n,forward_slip_fraction,reel_shaft_torque_nm)
from test_model import BASE
from physicroll import solve


class ObservationTests(unittest.TestCase):
    def test_force_stress_and_mass_flow(self):
        p=solve(BASE)
        self.assertAlmostEqual(tension_stress_pa(p['entry_tension_force_n'],BASE.width_m,BASE.entry_thickness_m),BASE.entry_tension_pa)
        self.assertAlmostEqual(tension_stress_pa(p['exit_tension_force_n'],BASE.width_m,BASE.exit_thickness_m),BASE.exit_tension_pa)
        self.assertAlmostEqual(strip_mass_flow_kg_s(BASE.density_kg_m3,BASE.width_m,BASE.entry_thickness_m,BASE.entry_speed_m_s),
                               strip_mass_flow_kg_s(BASE.density_kg_m3,BASE.width_m,BASE.exit_thickness_m,p['exit_speed_m_s']))
        with self.assertRaises(ValueError): tension_stress_pa(10,1,0)
        with self.assertRaises(ValueError): strip_mass_flow_kg_s(2700,1,.002,float('inf'))

    def test_qualified_wrap_reaction(self):
        self.assertAlmostEqual(tension_from_wrap_reaction_n(2000,math.pi/2,tare_n=100,geometry_qualified=True),
                               1900/math.sqrt(2))
        with self.assertRaises(ValueError): tension_from_wrap_reaction_n(2000,math.pi/2,tare_n=100)
        for reaction,angle,tare in [(50,math.pi/2,100),(100,0,0),(100,math.pi+1,0)]:
            with self.assertRaises(ValueError): tension_from_wrap_reaction_n(reaction,angle,tare_n=tare,geometry_qualified=True)

    def test_double_acting_thrust(self):
        self.assertAlmostEqual(hydraulic_differential_thrust_n(10e6,4e6,.1,.05),math.pi*(100000-30000))
        self.assertLess(hydraulic_differential_thrust_n(1e6,10e6,.1,.05),0)
        with self.assertRaises(ValueError): hydraulic_differential_thrust_n(1e6,1e6,.1,.1)

    def test_slip_and_reel_torque(self):
        p=solve(BASE)
        self.assertAlmostEqual(forward_slip_fraction(p['exit_speed_m_s'],p['roll_surface_speed_m_s']),p['assumed_forward_slip_fraction'])
        self.assertEqual(reel_shaft_torque_nm(100,2,10,3,5,winding=True),235)
        self.assertEqual(reel_shaft_torque_nm(100,2,10,3,5,winding=False),-165)
        with self.assertRaises(ValueError): forward_slip_fraction(1,1e-9)
        with self.assertRaises(ValueError): reel_shaft_torque_nm(100,2,-1,0)
