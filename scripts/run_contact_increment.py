"""Fixed-gauge structural comparisons and conditional sensitivities; no fitting/search."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.contact import CircularRollElasticity
from physicroll.literature import load_case, simulate_schedule, compare_measurements


def run(out, cells):
    out.mkdir(parents=True,exist_ok=True)
    case=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
    if case['unit_audit']['converted_numeric_values']!=49:
        raise ValueError('source import changed; repeat dimensional review')
    gauges=[p['exit_thickness_m'] for p in case['passes'][:2]]
    assumptions=dict(prior_log_strain=.05,strain_convention='log_thickness',
                     stress_convention='uniaxial',speed_interpretation='roll_surface')
    elastic=CircularRollElasticity(210e9,.3,'Analyst assumed steel E=210 GPa, nu=0.3; NOT Shao benchmark data')
    def save(name,value):
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    def evaluate(label,hardening,el,changes=None):
        row={'case':label,'parameter_changes':changes or {},'structural_hardening':hardening,
             'structural_contact':'rigid' if el is None else 'circular_hitchcock'}
        try:
            result=simulate_schedule(case,gauges,**{**assumptions,**(changes or {})},cells=cells,
                                     hardening_model=hardening,elasticity=el)
            comparison=compare_measurements(case,result)
            row.update(status='CONDITIONAL_NUMERICAL_RESULT' if result['numerical_converged'] else 'REJECTED_NUMERICAL_CONVERGENCE',
                       result=result,comparison=comparison,
                       force_mean_absolute_relative_residual=sum(abs(p['force_relative_residual']) for p in comparison)/3,
                       slip_mean_absolute_relative_residual=sum(abs(p['slip_relative_residual']) for p in comparison)/3)
        except ValueError as e:
            row.update(status='REJECTED_MODEL_OR_ASSUMPTION',reason=str(e))
        return row
    structures=[evaluate('reviewed_rigid_mean','pass_mean',None),evaluate('rigid_spatial','spatial',None),
                evaluate('circular_mean','pass_mean',elastic),evaluate('circular_spatial','spatial',elastic)]
    save('structural_comparisons.json',structures)
    if any(row['status']!='CONDITIONAL_NUMERICAL_RESULT' for row in structures):
        raise ValueError('a structural comparison failed; details retained in structural_comparisons.json')
    changes=[('zero_prior',{'prior_log_strain':0}),('prior_0.01',{'prior_log_strain':.01}),
             ('prior_0.20',{'prior_log_strain':.2}),('friction_minus10pct',{'friction_factor':.9}),
             ('friction_plus10pct',{'friction_factor':1.1}),('K_minus10pct',{'strength_factor':.9}),
             ('K_plus10pct',{'strength_factor':1.1}),('equivalent_strain_interpretation',{'strain_convention':'equivalent'}),
             ('plane_strain_strength_interpretation',{'stress_convention':'plane_strain_difference'}),
             ('diameter_prose_interpretation',{'radius_factor':.5}),
             ('speed_as_entry_strip',{'speed_interpretation':'entry_strip'}),
             ('speed_as_exit_strip',{'speed_interpretation':'exit_strip'}),
             ('joint_alternative',{'radius_factor':.5,'prior_log_strain':.2,'stress_convention':'plane_strain_difference'})]
    hypotheses=[evaluate(label,'spatial',elastic,delta) for label,delta in changes]
    hypotheses += [evaluate('assumed_E_180GPa','spatial',CircularRollElasticity(180e9,.3,'assumed elasticity sensitivity')),
                   evaluate('assumed_E_230GPa','spatial',CircularRollElasticity(230e9,.3,'assumed elasticity sensitivity'))]
    # Cross-grid checks of the complete radius+material solve, beyond inner refinement.
    coarse=simulate_schedule(case,gauges,**assumptions,cells=cells//2,hardening_model='spatial',elasticity=elastic)
    refinement=[]
    for a,b in zip(coarse['passes'],structures[-1]['result']['passes']):
        refinement.append({'pass_id':a['pass_id'],
            'force_relative_change':b['separating_force_n']/a['separating_force_n']-1,
            'slip_absolute_change':b['forward_slip_fraction']-a['forward_slip_fraction'],
            'radius_relative_change':b['contact_radius_m']/a['contact_radius_m']-1,
            'torque_relative_change':b['torque_per_work_roll_nm']/a['torque_per_work_roll_nm']-1})
    valid=[row for row in structures+hypotheses if row['status']=='CONDITIONAL_NUMERICAL_RESULT']
    envelopes=[]
    for i in range(3):
        envelope={'pass_id':i+1}
        for key in ('force_relative_residual','slip_relative_residual'):
            values=[row['comparison'][i][key] for row in valid]
            envelope[key]={'minimum':min(values),'maximum':max(values),
                           'all_positive':min(values)>0,'all_negative':max(values)<0}
        envelopes.append(envelope)
    summary={'status':'CONDITIONAL_MECHANICS_INCREMENT_NOT_EXPERIMENTAL_VALIDATION',
        'reviewed_base_commit':'09d0d5b2e754ddcc9840e9b2d11fbdb07efd9b89',
        'fixed_product':'AA5052 1360 mm wide, 4.10 to 1.72 mm in published three-pass gauges; temper unknown',
        'assumptions':assumptions,'reported_measurements_fitted':False,'new_optimisation_run':False,
        'structures':[{k:v for k,v in row.items() if k!='result'} for row in structures],
        'hypothesis_count':len(hypotheses),'rejected_hypotheses':[{k:v for k,v in row.items() if k not in ('result','comparison')} for row in hypotheses if row['status']!='CONDITIONAL_NUMERICAL_RESULT'],
        'tested_hypothesis_envelopes_not_confidence_intervals':envelopes,
        'combined_refinement':refinement,
        'max_mechanical_work_residual_relative':max(p['mechanical_work_residual_relative'] for r in valid for p in r['result']['passes']),
        'max_mass_flow_residual_kg_s':max(abs(p['mass_flow_residual_kg_s']) for r in valid for p in r['result']['passes']),
        'max_flattening_residual_over_nominal':max(abs(p['flattening']['radius_residual_over_nominal']) for r in valid for p in r['result']['passes'] if 'flattening' in p),
        'data_gate':'Flow curve/history, measured speed locations, torque, elastic geometry, repeat coils and uncertainty remain missing. No parameter identification or plant recommendation.',
        'limitations':['Sampled hypotheses have no probabilities or confidence coverage.',
          'Rate-independent mechanics cannot distinguish speed locations from force or slip; throughput/power differ.',
          'Circular compliance and friction/hardening can compensate in force; joint evidence is required.',
          'No sticking/noncircular contact, elastic recovery, calibrated aluminium response or mill ratings.',
          'No new thermal, metallurgical, flatness or fracture validation.']}
    save('summary.json',summary);save('structural_comparisons.json',structures)
    save('hypotheses.json',hypotheses);save('unit_audit.json',case['unit_audit'])
    rows=[{'case':r['case'],**v} for r in structures for v in r['comparison']]
    with (out/'before_after.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    source_paths=sorted((ROOT/'physicroll').glob('*.py'))+[Path(__file__).resolve()]+sorted((ROOT/'scenarios/literature/shao2015_aa5052').glob('*'))
    save('reproducibility.json',{'python':sys.version,'cells_coarse':cells,'cells_fine':2*cells,
        'command':f'python scripts/run_contact_increment.py --cells {cells} --out artifacts/contact_increment',
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths if p.is_file()}})
    names=['summary.json','structural_comparisons.json','hypotheses.json','unit_audit.json','before_after.csv','reproducibility.json']
    save('checksums.json',{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in names})
    print(json.dumps({'comparisons':[(r['case'],r['force_mean_absolute_relative_residual'],r['slip_mean_absolute_relative_residual']) for r in structures],
                      'rejections':summary['rejected_hypotheses'],'max_work_residual_relative':summary['max_mechanical_work_residual_relative'],
                      'output':str(out)},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'artifacts/contact_increment')
    parser.add_argument('--cells',type=int,default=512)
    args=parser.parse_args()
    if not 64<=args.cells<=4096:parser.error('--cells must be in [64,4096]')
    run(args.out,args.cells)
