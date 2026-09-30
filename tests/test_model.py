import json
import math
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest

from physicroll import Scenario, solve

ROOT = Path(__file__).resolve().parents[1]
BASE = Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))


class ProcessModelTests(unittest.TestCase):
    def test_baseline_regression(self):
        r = solve(BASE)
        self.assertAlmostEqual(r['separating_force_n'], 2200485.4436219567, places=5)
        self.assertAlmostEqual(r['roll_mechanical_power_w'], 220924.09743962932, places=5)
        self.assertAlmostEqual(r['torque_per_work_roll_nm'], 11835.21950569443, places=6)
        self.assertEqual(r['status'], 'SYNTHETIC_UNCALIBRATED')

    def test_mass_energy_units_and_traction(self):
        r = solve(BASE)
        q1 = BASE.width_m * BASE.exit_thickness_m * r['exit_speed_m_s']
        self.assertAlmostEqual(q1, r['volume_flow_m3_s'])
        self.assertAlmostEqual(q1 * BASE.density_kg_m3, 10.8)
        self.assertAlmostEqual(r['separating_force_n'], r['mean_contact_pressure_pa'] * BASE.width_m * r['contact_length_m'])
        self.assertAlmostEqual(2*r['torque_per_work_roll_nm']*r['roll_angular_speed_rad_s'], r['roll_mechanical_power_w'])
        self.assertAlmostEqual(r['roll_drive_electrical_power_w']*.9, r['roll_mechanical_power_w'])
        self.assertLess(abs(r['energy_residual_w']), 1e-8)
        net = r['exit_tension_force_n']*r['exit_speed_m_s'] - r['entry_tension_force_n']*BASE.entry_speed_m_s
        self.assertAlmostEqual(net, r['net_tension_power_w'])
        self.assertLess(r['torque_per_work_roll_nm'],r['traction_torque_bound_per_roll_nm'])

    def test_zero_draft_and_continuity(self):
        s = replace(BASE, entry_tension_pa=0, exit_tension_pa=0)
        r0 = solve(replace(s, exit_thickness_m=s.entry_thickness_m))
        for key in ['separating_force_n','roll_mechanical_power_w','torque_per_work_roll_nm','contact_length_m']:
            self.assertEqual(r0[key], 0)
        forces = []
        powers = []
        for draft in [1e-5,1e-7,1e-9,1e-11]:
            r = solve(replace(s, exit_thickness_m=s.entry_thickness_m-draft))
            forces.append(r['separating_force_n'])
            powers.append(r['roll_mechanical_power_w'])
        self.assertEqual(forces, sorted(forces, reverse=True))
        self.assertEqual(powers, sorted(powers, reverse=True))
        self.assertLess(powers[-1], .004)

    def test_scaling(self):
        a = solve(BASE)
        b = solve(replace(BASE, entry_speed_m_s=2*BASE.entry_speed_m_s))
        for key in ['separating_force_n','torque_per_work_roll_nm']:
            self.assertAlmostEqual(a[key], b[key])
        for key in ['roll_mechanical_power_w','mass_flow_kg_s']:
            self.assertAlmostEqual(2*a[key], b[key])
        c = solve(replace(BASE, width_m=2*BASE.width_m))
        for key in ['separating_force_n','roll_mechanical_power_w','mass_flow_kg_s','torque_per_work_roll_nm']:
            self.assertAlmostEqual(2*a[key], c[key])
        # Geometric similarity at fixed speed: force and power scale with area.
        d = solve(replace(BASE, width_m=2*BASE.width_m, entry_thickness_m=2*BASE.entry_thickness_m,
                          exit_thickness_m=2*BASE.exit_thickness_m, work_roll_radius_m=2*BASE.work_roll_radius_m))
        self.assertAlmostEqual(d['separating_force_n']/a['separating_force_n'],4)
        self.assertAlmostEqual(d['torque_per_work_roll_nm']/a['torque_per_work_roll_nm'],8)

    def test_rejections(self):
        cases = [dict(exit_thickness_m=.0021), dict(exit_thickness_m=.0009), dict(width_m=.001),
                 dict(entry_thickness_m=.0003,exit_thickness_m=.0002), dict(entry_speed_m_s=0), dict(density_kg_m3=-1), dict(friction_coefficient=.001),
                 dict(friction_coefficient=.4), dict(drive_efficiency=1.1), dict(drive_efficiency=0),
                 dict(entry_tension_pa=120e6), dict(exit_tension_pa=-1), dict(synthetic=False),
                 dict(exit_thickness_m=.002), dict(exit_tension_pa=100e6),
                 dict(entry_tension_pa=119e6,exit_tension_pa=0,friction_coefficient=.045),
                 dict(density_kg_m3=1e308,entry_speed_m_s=10000),dict(entry_thickness_m=2,exit_thickness_m=1.5),dict(work_roll_radius_m=.001)]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                solve(replace(BASE, **changes))

    def test_invalid_types_and_schema(self):
        for value in [float('nan'),float('inf'),True,'0.002',None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                solve(replace(BASE,entry_thickness_m=value))
        data = json.loads((ROOT/'scenarios/baseline.json').read_text())
        with self.assertRaises(ValueError):
            Scenario.from_dict({**data,'units':'mm'})
        del data['width_m']
        with self.assertRaises(ValueError):
            Scenario.from_dict(data)

    def test_exact_bite_boundary(self):
        h0, r, mu = BASE.entry_thickness_m, BASE.work_roll_radius_m, BASE.friction_coefficient
        maxdraft = 2*r*(1-1/math.sqrt(1+mu*mu))
        s = replace(BASE, entry_thickness_m=.004, exit_thickness_m=.004-maxdraft, entry_tension_pa=0, exit_tension_pa=0)
        solve(s)
        with self.assertRaisesRegex(ValueError, 'bite'):
            solve(replace(s, exit_thickness_m=s.exit_thickness_m-1e-8))

    def test_small_perturbation(self):
        a = solve(BASE)
        b = solve(replace(BASE,exit_thickness_m=BASE.exit_thickness_m*(1+1e-7)))
        self.assertLess(abs(b['separating_force_n']/a['separating_force_n']-1),1e-6)

    def test_cli(self):
        p = subprocess.run([sys.executable,'-m','physicroll','scenarios/baseline.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['status'],'SYNTHETIC_UNCALIBRATED')


if __name__ == '__main__':
    unittest.main()
