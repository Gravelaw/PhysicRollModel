"""Portable standard-library-only smoke test. Run from any working directory."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll import Scenario, solve

base=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
r=solve(base)
assert abs(r['mass_flow_kg_s']-10.8)<1e-10
assert abs(r['energy_residual_w'])<1e-7
assert 2.19e6<r['separating_force_n']<2.21e6
assert 220e3<r['roll_mechanical_power_w']<222e3
from physicroll.equipment import EquipmentAssumptions,evaluate_equipment
from physicroll.sensors import sensor_manifest
e=EquipmentAssumptions.from_dict(json.loads((ROOT/'scenarios/baseline.equipment.json').read_text()))
eq=evaluate_equipment(base,e,r)
assert abs(eq['reel_tension_power_residual_w'])<1e-7
assert abs(eq['mass_flow_residual_kg_s'])<1e-10
assert abs(eq['stand_reaction_total_n']-r['separating_force_n'])<1e-7
assert all(x['observed_value_si'] is None for x in sensor_manifest(base,r)['signals'])
hashfile=ROOT/'artifacts/checksums.json'
if hashfile.exists():
    hashes=json.loads(hashfile.read_text())
    for path,expected in hashes.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
print('PASS: pure-Python solve, stand/reel balance, disconnected sensors, bundled asset checksums')
print(json.dumps({k:r[k] for k in ['mass_flow_kg_s','separating_force_n','roll_mechanical_power_w']},indent=2))
