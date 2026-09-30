"""Small, labelled synthetic parameter sensitivity; never a production optimiser."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.model import Scenario
from physicroll.materials import MaterialState,PowerHardeningLaw,pass_with_history
from physicroll.thermal import ThermalStep,step
from physicroll.slab import solve_slab

p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=ROOT/'artifacts/v03_sensitivity.json')
a=p.parse_args()
s=Scenario.from_dict(json.loads((ROOT/'scenarios/baseline.json').read_text()))
c=json.loads((ROOT/'scenarios/v03_foundations.json').read_text())
state=MaterialState(**{**c['material_state'],'history':tuple(c['material_state']['history'])})
law=PowerHardeningLaw(**c['hardening_law'])
thermal=ThermalStep(**c['thermal_step'])
friction=[]
for mu in (.08,.10,.12):
    result=solve_slab(replace(s,friction_coefficient=mu),cells=512)
    friction.append({'effective_friction_coefficient':mu,
                     'separating_force_n':result['separating_force_n'],
                     'torque_per_work_roll_nm':result['torque_per_work_roll_nm'],
                     'neutral_position_from_entry_m':result['neutral_position_from_entry_m'],
                     'forward_slip_fraction':result['forward_slip_fraction']})
heat=[]
for beta in (0,.5,1):
    result=step(replace(thermal,plastic_heat_fraction=beta))
    heat.append({'supplied_plastic_heat_fraction':beta,
                 'strip_temperature_k':result['strip_temperature_k'],
                 'roll_temperature_k':result['roll_temperature_k'],
                 'energy_residual_j':result['energy_residual_j']})
passes=[]
pass_scenario=s
for i in range(2):
    result=pass_with_history(replace(pass_scenario,name=f'synthetic-pass-{i+1}'),state,law)
    passes.append({'pass':i+1,'strain_start':state.accumulated_equivalent_plastic_strain,
                   'strain_end':result['state_out']['accumulated_equivalent_plastic_strain'],
                   'entry_thickness_m':pass_scenario.entry_thickness_m,
                   'exit_thickness_m':pass_scenario.exit_thickness_m,
                   'mass_flow_kg_s':result['baseline_mechanics']['mass_flow_kg_s'],
                   'mean_flow_stress_pa':result['mean_flow_stress_pa']})
    state=MaterialState(**{**result['state_out'],'history':tuple(result['state_out']['history'])})
    pass_scenario=replace(pass_scenario,entry_thickness_m=pass_scenario.exit_thickness_m,
                          exit_thickness_m=pass_scenario.exit_thickness_m*.75,
                          entry_speed_m_s=result['baseline_mechanics']['exit_speed_m_s'])
out={'status':'SYNTHETIC_SENSITIVITY_ONLY',
     'warning':'Separate parameter perturbations are not a coupled calibrated mill or optimisation.',
     'friction_cases':friction,'plastic_heat_fraction_cases':heat,'history_cases':passes}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(a.out)
