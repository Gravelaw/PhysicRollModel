import json
import math
from dataclasses import replace
from pathlib import Path
import unittest

from physicroll import Scenario, solve
from physicroll.equipment import EquipmentAssumptions, evaluate_equipment
from physicroll.sensors import SPECS, marker_positions, sensor_manifest

ROOT=Path(__file__).resolve().parents[1]
BASE=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
EQ=EquipmentAssumptions.from_dict(json.loads((ROOT/'scenarios/baseline.equipment.json').read_text()))


class EquipmentAndSensorsTests(unittest.TestCase):
    def test_load_path_and_gap(self):
        p=solve(BASE)
        e=evaluate_equipment(BASE,EQ,p)
        self.assertEqual(e['stand_reaction_total_n'],p['separating_force_n'])
        self.assertAlmostEqual(2*e['stand_reaction_per_side_n'],p['separating_force_n'])
        self.assertAlmostEqual(e['assumed_stand_extension_m'],p['separating_force_n']/EQ.stand_stiffness_n_m)
        self.assertAlmostEqual(e['implied_unloaded_gap_m']+e['assumed_stand_extension_m'],BASE.exit_thickness_m)
        self.assertIsNone(e['recovered_strip_thickness_m'])

    def test_reel_force_torque_power_and_inertia(self):
        p=solve(BASE)
        e=evaluate_equipment(BASE,EQ,p)
        self.assertAlmostEqual(e['entry_reel_signed_torque_on_strip_nm'],-BASE.entry_tension_pa*BASE.width_m*BASE.entry_thickness_m*EQ.entry_reel_radius_m)
        self.assertAlmostEqual(e['exit_reel_signed_torque_on_strip_nm'],BASE.exit_tension_pa*BASE.width_m*BASE.exit_thickness_m*EQ.exit_reel_radius_m)
        self.assertAlmostEqual(e['net_reel_power_on_strip_w'],p['net_tension_power_w'])
        self.assertAlmostEqual(e['reel_tension_power_residual_w'],0)
        self.assertIsNone(e['reel_acceleration_torque_nm'])
        larger=evaluate_equipment(BASE,replace(EQ,entry_reel_radius_m=1.4),p)
        self.assertAlmostEqual(larger['entry_reel_signed_torque_on_strip_nm'],2*e['entry_reel_signed_torque_on_strip_nm'])
        self.assertAlmostEqual(larger['entry_reel_angular_speed_rad_s'],e['entry_reel_angular_speed_rad_s']/2)
        self.assertAlmostEqual(larger['entry_reel_signed_power_on_strip_w'],e['entry_reel_signed_power_on_strip_w'])
        self.assertAlmostEqual(larger['entry_reel_rotational_energy_j'],e['entry_reel_rotational_energy_j']/4)

    def test_limits_and_provenance(self):
        p=solve(BASE)
        for change in [dict(stand_stiffness_n_m=1e6),dict(entry_reel_radius_m=0),
                       dict(exit_reel_inertia_kg_m2=-1),dict(synthetic=False),
                       dict(stand_stiffness_n_m=float('nan'))]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                evaluate_equipment(BASE,replace(EQ,**change),p)
        with self.assertRaises(ValueError):
            evaluate_equipment(replace(BASE,name='other'),EQ,p)
        with self.assertRaises(ValueError):
            EquipmentAssumptions.from_dict({'synthetic':True})
        no_draft=replace(BASE,exit_thickness_m=BASE.entry_thickness_m,exit_tension_pa=BASE.entry_tension_pa)
        e=evaluate_equipment(no_draft,EQ)
        self.assertEqual(e['stand_reaction_total_n'],0)
        self.assertEqual(e['implied_unloaded_gap_m'],no_draft.exit_thickness_m)

    def test_disconnected_sensor_map(self):
        m=sensor_manifest(BASE,solve(BASE))
        ids=[x['sensor_id'] for x in m['signals']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(ids,[s.sensor_id for s in SPECS])
        self.assertEqual(set(ids),set(marker_positions(BASE)))
        for signal in m['signals']:
            self.assertIsNone(signal['observed_value_si'])
            self.assertIsNone(signal['observed_timestamp_utc'])
            self.assertEqual(signal['quality'],'unavailable')
            self.assertEqual(signal['data_origin'],'no_plant_connection')
            self.assertEqual(set(signal['position_m']),{'x','y','z'})
            self.assertTrue(all(math.isfinite(v) for v in signal['position_m'].values()))
        p=solve(BASE)
        self.assertEqual(next(x for x in m['signals'] if x['sensor_id']=='roll_force')['model_estimate_si'],p['separating_force_n'])
        self.assertIsNone(next(x for x in m['signals'] if x['sensor_id']=='flatness')['model_estimate_si'])
        with self.assertRaises(ValueError):
            sensor_manifest(replace(BASE,name='other'),p)


if __name__=='__main__':
    unittest.main()
