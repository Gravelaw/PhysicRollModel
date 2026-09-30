"""Execute audited, assumption-bearing AA5052 comparison and constrained mesh search."""
import argparse
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from physicroll.literature import load_case,simulate_schedule,compare_measurements,optimise_gauges

p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=ROOT/'artifacts/aa5052')
p.add_argument('--speed-interpretation',required=True,choices=['roll_surface','entry_strip','exit_strip'])
p.add_argument('--strain-convention',required=True,choices=['log_thickness','equivalent'])
p.add_argument('--stress-convention',required=True,choices=['uniaxial','plane_strain_difference'])
p.add_argument('--prior-log-strain',required=True,type=float)
p.add_argument('--grid-sizes',type=int,nargs='+',default=[21,41])
a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
c=load_case(ROOT/'scenarios/literature/shao2015_aa5052')
def save(name,data):
    (a.out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def csvsave(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (a.out/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
save('unit_audit.json',c['unit_audit'])
csvsave('values_long.csv',c['unit_audit']['values'])
csvsave('process_inputs_si.csv',c['passes'])
csvsave('measured_validation_si.csv',c['measurements'])
csvsave('reference_model_outputs_si.csv',c['source_model_outputs'])
save('source_context.json',{'sources':c['sources'],'assumptions':c['assumptions'],
    'measurement_data':c['measurements'],'source_model_outputs_separate':c['source_model_outputs']})
assumptions=dict(prior_log_strain=a.prior_log_strain,strain_convention=a.strain_convention,
                 stress_convention=a.stress_convention,speed_interpretation=a.speed_interpretation)
optimised=optimise_gauges(c,assumptions=assumptions,grid_sizes=tuple(a.grid_sizes))
records=optimised.pop('search_records')
csvsave('search_candidates.csv',records)
save('optimisation.json',optimised)
baseline=optimised['baseline']; selected=optimised['selected']
save('baseline.json',baseline)
comparison=compare_measurements(c,baseline)
csvsave('baseline_vs_measurements.csv',comparison)
variations=[('zero_prior',{'prior_log_strain':0}),('prior_0.01',{'prior_log_strain':.01}),
    ('prior_0.20',{'prior_log_strain':.2}),('friction_minus10pct',{'friction_factor':.9}),
    ('friction_plus10pct',{'friction_factor':1.1}),('K_minus10pct',{'strength_factor':.9}),
    ('K_plus10pct',{'strength_factor':1.1}),('K_as_equivalent_strain',{'strain_convention':'equivalent'}),
    ('K_as_plane_strain_difference',{'stress_convention':'plane_strain_difference'}),
    ('diameter_prose_interpretation',{'radius_factor':.5}),
    ('speed_as_entry_strip',{'speed_interpretation':'entry_strip'}),
    ('speed_as_exit_strip',{'speed_interpretation':'exit_strip'})]
sensitivities=[]
for name,changes in variations:
    condition={**assumptions,**changes}
    row={'case':name,'explicit_assumptions':condition}
    try:
        b=simulate_schedule(c,baseline['intermediate_gauges_m'],**condition,cells=512)
        o=simulate_schedule(c,selected['intermediate_gauges_m'],**condition,cells=512)
        row.update(status='CONDITIONAL_EVALUATION',baseline=b,selected_schedule=o,
                   selected_peak_force_change_fraction=o['peak_force_n']/b['peak_force_n']-1,
                   baseline_comparison=compare_measurements(c,b))
    except ValueError as e:
        row.update(status='REJECTED_ASSUMPTION',reason=str(e))
    sensitivities.append(row)
save('sensitivity.json',{'status':'ASSUMED_RANGES_NOT_CONFIDENCE_INTERVALS','cases':sensitivities})
summary={'status':'CONDITIONAL_MECHANICS_ONLY_NOT_ALUMINIUM_VALIDATION',
    'case_id':c['case_id'],'assumptions':assumptions,'baseline_comparison':comparison,
    'baseline_peak_force_n':baseline['peak_force_n'],'selected_peak_force_n':selected['peak_force_n'],
    'selected_intermediate_gauges_m':selected['intermediate_gauges_m'],
    'selected_reductions':[x['reduction_fraction'] for x in selected['passes']],
    'peak_force_change_fraction':optimised['peak_force_change_fraction'],
    'candidate_count':optimised['candidate_count'],'accepted_search_count':optimised['accepted_search_count'],
    'all_final_baseline_selected_grids_converged':baseline['numerical_converged'] and selected['numerical_converged'],
    'max_final_mechanical_work_residual_relative':max(p['mechanical_work_residual_relative'] for r in (baseline,selected) for p in r['passes']),
    'force_mean_absolute_relative_residual':sum(abs(x['force_relative_residual']) for x in comparison)/3,
    'slip_mean_absolute_relative_residual':sum(abs(x['slip_relative_residual']) for x in comparison)/3,
    'credible_scope':'Numerical objective improvement only inside the declared rigid mean-flow model and assumed trust region; measured slip mismatch prevents a predictive accuracy claim.',
    'uncertainty':None,'physical_calibration_domain':'UNKNOWN','thermal_validation':False,
    'source_model_reproduced':False,'incoming_temper':None,'final_temper':None,
    'independent_measurements_used_for_fit':False}
save('summary.json',summary)
print(json.dumps(summary,indent=2))
print('Results:',a.out)
