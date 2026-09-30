"""Portable standard-library-only smoke test. Run from any working directory."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll import Scenario, solve
from physicroll.materials import MaterialState, PowerHardeningLaw, pass_with_history
from physicroll.slab import solve_slab
from physicroll.thermal import ThermalStep, step
from physicroll.literature import load_case

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
candidate=json.loads((ROOT/'scenarios/v03_foundations.json').read_text())
mat=pass_with_history(base,MaterialState(**{**candidate['material_state'],
    'history':tuple(candidate['material_state']['history'])}),PowerHardeningLaw(**candidate['hardening_law']))
assert mat['state_out']['accumulated_equivalent_plastic_strain']>mat['state_in']['accumulated_equivalent_plastic_strain']
slab=solve_slab(base)
assert slab['separating_force_n']>0 and slab['numerical_converged']
assert slab['mechanical_work_residual_relative']<1e-4
assert load_case(ROOT/'scenarios/literature/shao2015_aa5052')['unit_audit']['converted_numeric_values']==49
assert abs(step(ThermalStep(**candidate['thermal_step']))['energy_residual_j'])<1e-7
hashfile=ROOT/'artifacts/checksums.json'
if hashfile.exists():
    hashes=json.loads(hashfile.read_text())
    for path,expected in hashes.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
print('PASS: baseline, v0.3 foundations, disconnected sensors, bundled asset checksums')
print(json.dumps({k:r[k] for k in ['mass_flow_kg_s','separating_force_n','roll_mechanical_power_w']},indent=2))
