"""Run two explicitly synthetic, checked mechanics/energy passes from JSON."""
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.model import Scenario
from physicroll.materials import MaterialState, PowerHardeningLaw, BiteHardening
from physicroll.slab import solve_slab
from physicroll.energy_handoff import (HeatCapacityCurve, PassHeatBoundary,
                                      PassiveContactBoundary, handoff_pass)
from physicroll.lubrication import FluidObservation


def run(config_path: Path, output_path: Path):
    config_path=config_path.resolve()
    data=json.loads(config_path.read_text())
    if 'SYNTHETIC' not in data.get('warning',''):
        raise ValueError('demo must label all parameters synthetic')
    state=MaterialState(**{**data['material_state'],'history':tuple(data['material_state']['history'])})
    law=PowerHardeningLaw(**data['hardening_law'])
    strip_cp=HeatCapacityCurve(**{**data['strip_heat_capacity'],
        'temperature_k':tuple(data['strip_heat_capacity']['temperature_k']),
        'heat_capacity_j_kg_k':tuple(data['strip_heat_capacity']['heat_capacity_j_kg_k'])})
    roll_cp=HeatCapacityCurve(**{**data['roll_heat_capacity'],
        'temperature_k':tuple(data['roll_heat_capacity']['temperature_k']),
        'heat_capacity_j_kg_k':tuple(data['roll_heat_capacity']['heat_capacity_j_kg_k'])})
    fluid=FluidObservation(**data['fluid_observation'])
    scenario=Scenario.from_dict(json.loads((ROOT/data['baseline_scenario_file']).read_text()))
    outputs=[]
    for index in range(2):
        if index:
            scenario=replace(scenario,name='synthetic_aluminium_second_pass',
                entry_thickness_m=scenario.exit_thickness_m,
                exit_thickness_m=data['second_pass_exit_thickness_m'],
                entry_speed_m_s=outputs[-1]['mechanics']['exit_speed_m_s'])
        material=BiteHardening(state,law,tuple(data['assumed_equivalent_strain_range']),
                                tuple(data['assumed_material_temperature_range_k']))
        scenario=replace(scenario,mean_flow_stress_pa=material.mean_stress(scenario.entry_thickness_m,scenario.exit_thickness_m))
        mechanics=solve_slab(scenario,cells=512,material=material)
        if not mechanics['numerical_converged']:
            raise ValueError(f'pass {index+1}: mechanics refinement gate failed')
        boundary_data=dict(data['boundaries'][index])
        if index:boundary_data['roll_temperature_k']=outputs[-1]['energy']['roll_temperature_out_k']
        contact_data=data.get('passive_contacts')
        passive_contact=None if contact_data is None else PassiveContactBoundary(**contact_data[index])
        energy=handoff_pass(mechanics,state,strip_cp,roll_cp,PassHeatBoundary(**boundary_data),
                            fluid=fluid,passive_contact=passive_contact)
        if energy['thermal_allocation_residual_relative']>1e-8:
            raise ValueError(f'pass {index+1}: energy conservation gate failed')
        outputs.append({'pass_id':index+1,'mechanics':mechanics,'energy':energy})
        state=MaterialState(**{**energy['strip_state_out'],'history':tuple(energy['strip_state_out']['history'])})
    try:
        config_label=str(config_path.relative_to(ROOT))
    except ValueError:
        config_label=str(config_path)
    result={'status':'SYNTHETIC_NUMERICAL_CONSERVATION_EXERCISE_NO_THERMAL_VALIDATION',
            'source_config':config_label,
            'source_config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
            'temper_certified':False,'fluid_heat_transfer_calibrated':False,
            'thermal_feedback_to_force':False,'passes':outputs,
            'max_thermal_allocation_residual_w':max(abs(p['energy']['thermal_allocation_residual_w']) for p in outputs),
            'max_mechanical_work_residual_relative':max(p['mechanics']['mechanical_work_residual_relative'] for p in outputs)}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],
        'pass_summaries':[{'pass_id':p['pass_id'],'strip_exit_k':p['energy']['strip_temperature_out_k'],
            'roll_exit_k':p['energy']['roll_temperature_out_k'],
            'mass_flow_kg_s':p['energy']['mass_flow_kg_s'],
            'thermal_residual_w':p['energy']['thermal_allocation_residual_w'],
            'nonthermal_plastic_work_w':p['energy']['nonthermal_plastic_work_w']} for p in outputs],
        'max_thermal_allocation_residual_w':result['max_thermal_allocation_residual_w'],
        'output':str(output_path)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'scenarios/flowing_energy_demo.json')
    parser.add_argument('--out',type=Path,default=ROOT/'artifacts/flowing_energy_demo.json')
    args=parser.parse_args()
    run(args.config,args.out)
