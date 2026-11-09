"""Audited source import and conditional AA5052 mechanical comparisons.

No fitted parameters or independent validation: see scenarios/literature/shao2015_aa5052.
"""
import csv
import json
import math
from pathlib import Path
from dataclasses import replace
from .units import audited_value, to_si
from .materials import PowerHardeningLaw, MaterialState, BiteHardening
from .contact import solve_circular_contact
from .model import Scenario
from .slab import solve_slab

INPUT_FIELDS = {
    'entry_thickness_mm':('entry_thickness_m','mm','length','full entry thickness'),
    'exit_thickness_mm':('exit_thickness_m','mm','length','full exit thickness'),
    'width_mm':('width_m','mm','length','full strip width'),
    'back_tension_MPa':('back_tension_pa','MPa','stress','entry tensile stress, not force'),
    'front_tension_MPa':('front_tension_pa','MPa','stress','exit tensile stress, not force'),
    'work_roll_radius_mm':('work_roll_radius_m','mm','length','Table1 radius label; Eq6 diameter prose unresolved'),
    'rolling_speed_m_s':('rolling_speed_m_s','m/s','speed','measurement location unresolved'),
    'friction_coefficient':('friction_coefficient','1','dimensionless','reported effective coefficient, identification unknown'),
}


def load_case(directory):
    if isinstance(directory, (str, Path)):
        directory = Path(directory)
    assumptions = json.loads((directory/'assumptions.json').read_text())
    audit, passes, measurements, references = [], [], [], []
    def convert(value,unit,dimension,convention,source,location,category,pass_id,field):
        row = audited_value(value=float(value),unit=unit,dimension=dimension,
                            convention=convention,source_id=source,location=location)
        row.update(category=category,pass_id=pass_id,field=field)
        audit.append(row)
        return row['si_value']
    with (directory/'inputs.csv').open() as f:
        for raw in csv.DictReader(f):
            i = int(raw['pass_id'])
            row = {'pass_id':i}
            for field,(target,unit,dim,convention) in INPUT_FIELDS.items():
                row[target] = convert(raw[field],unit,dim,convention,'S1','p94 Tables1-2','reported_input',i,target)
            passes.append(row)
    for filename,target,category in [('measured_validation.csv',measurements,'author_reported_measurement'),
                                     ('reference_model_outputs.csv',references,'source_model_output')]:
        with (directory/filename).open() as f:
            for raw in csv.DictReader(f):
                i = int(raw['pass_id']); row = {'pass_id':i}
                row['force_n'] = convert(raw['force_kN'],'kN','force','total stand separating force, not twice per-roll load','S1','p94 Table2',category,i,'force_n')
                row['forward_slip_fraction'] = convert(raw['forward_slip_fraction'],'1','dimensionless','reported fraction; measured speed normalization unspecified','S1','p94 Table2',category,i,'forward_slip_fraction')
                if category == 'source_model_output':
                    row['flattened_radius_m'] = convert(raw['flattened_radius_mm'],'mm','length','source-calculated effective radius, NOT measured','S1','p94 Table2',category,i,'flattened_radius_m')
                    for name in ('force','slip'):
                        row[f'printed_{name}_error_fraction'] = convert(raw[f'printed_{name}_error_percent'],'%','dimensionless','printed relative error, preserve rounding','S1','p94 Table2',category,i,f'printed_{name}_error_fraction')
                else:
                    row.update(force_uncertainty_n=None,slip_uncertainty_fraction=None)
                target.append(row)
    k = assumptions['material']['K_original']
    strength = convert(k['value'],k['unit'],'stress','deformation resistance coefficient; strain/stress pairing unresolved','S1',k['location'],'material_coefficient',0,'K_pa')
    exponent = convert(assumptions['material']['n'],'1','dimensionless','power exponent','S1','p94 section4','material_coefficient',0,'n')
    rho = assumptions['density']
    density = convert(rho['value'],rho['unit'],'density','generic alloy density, not benchmark measurement','S2',rho['location'],'generic_manufacturer',0,'density_kg_m3')
    elastic = assumptions['generic_strip_E']
    convert(elastic['value'],elastic['unit'],'stress','generic manufacturer Young modulus, NOT used in rigid model','S2',elastic['location'],'generic_manufacturer',0,'strip_E_pa_unused')
    if any([p['pass_id'] for p in group] != [1,2,3] for group in (passes,measurements,references)):
        raise ValueError('expected exactly three ordered passes and observations')
    for j,p in enumerate(passes):
        if not .0003 <= p['exit_thickness_m'] < p['entry_thickness_m'] <= .02:
            raise ValueError('gauge outside import sanity envelope; check mm/m')
        if not .05 <= p['work_roll_radius_m'] <= 1 or not .1 <= p['width_m'] <= 3:
            raise ValueError('roll radius/width outside import sanity envelope')
        if not 0 <= min(p['back_tension_pa'],p['front_tension_pa']) <= max(p['back_tension_pa'],p['front_tension_pa']) < 300e6:
            raise ValueError('tension outside import sanity envelope; check MPa/Pa')
        if not 0 < p['friction_coefficient'] <= .3 or not 0 < p['rolling_speed_m_s'] <= 100:
            raise ValueError('friction/speed outside import sanity envelope')
        if j and not math.isclose(passes[j-1]['exit_thickness_m'],p['entry_thickness_m'],rel_tol=1e-12):
            raise ValueError('pass gauges do not connect')
    if not 1000 <= density <= 10000 or not 1e6 < strength < 2e9 or not 0 < exponent < 1:
        raise ValueError('material coefficient/density outside import sanity envelope')
    derived = []
    for p,m,r in zip(passes,measurements,references):
        if not 0 < m['force_n'] < 1e8 or not 0 < m['forward_slip_fraction'] < .3:
            raise ValueError('measurement import sanity check failed')
        h0,h1,rad,w = p['entry_thickness_m'],p['exit_thickness_m'],p['work_roll_radius_m'],p['width_m']
        length = math.sqrt(rad*(h0-h1)-(h0-h1)**2/4)
        derived.append({'pass_id':p['pass_id'],'reduction_fraction':1-h1/h0,
            'draft_m':h0-h1,'log_thickness_strain':math.log(h0/h1),
            'homogeneous_equivalent_strain_increment':2/math.sqrt(3)*math.log(h0/h1),
            'back_tension_force_n':p['back_tension_pa']*w*h0,
            'front_tension_force_n':p['front_tension_pa']*w*h1,
            'measured_force_per_width_n_m':m['force_n']/w,
            'contact_length_m':length,'unassisted_bite_tangent':length/(rad-(h0-h1)/2),
            'source_model_radius_ratio':r['flattened_radius_m']/rad,
            'source_model_force_error_fraction_recomputed':r['force_n']/m['force_n']-1,
            'source_model_slip_error_fraction_recomputed':r['forward_slip_fraction']/m['forward_slip_fraction']-1})
    return {'case_id':assumptions['case_id'],'passes':passes,'measurements':measurements,
            'source_model_outputs':references,'K_pa':strength,'n':exponent,'density_kg_m3':density,
            'assumptions':assumptions,'sources':json.loads((directory/'sources.json').read_text()),
            'unit_audit':{'status':'ARITHMETIC_AND_IMPORT_SANITY_PASSED_SEMANTICS_UNRESOLVED',
                          'converted_numeric_values':len(audit),'values':audit,'derived':derived,
                          'resolved_speed_mapping':None,'resolved_constitutive_convention':None}}


def simulate_schedule(case, intermediate_gauges_m, *, prior_log_strain, strain_convention,
                      stress_convention, speed_interpretation, friction_factor=1.0,
                      strength_factor=1.0, radius_factor=1.0, cells=256, verify_refinement=True,
                      hardening_model="pass_mean", elasticity=None):
    """Conditional what-if: default mean strength/rigid; explicit optional extensions.

    All unresolved conventions must be selected by name. No fit to measurements.
    Speeds vary between sequential single-stand passes: within-pass mass continuity
    is enforced, but instantaneous throughput is not forced equal between passes.
    """
    if hardening_model not in ('pass_mean','spatial'):
        raise ValueError('hardening_model must be pass_mean or spatial')
    if speed_interpretation not in ('roll_surface','entry_strip','exit_strip'):
        raise ValueError('select an explicit speed interpretation; source convention unresolved')
    if strain_convention not in ('log_thickness','equivalent') or stress_convention not in ('uniaxial','plane_strain_difference'):
        raise ValueError('select explicit constitutive conventions')
    for value in (prior_log_strain,friction_factor,strength_factor,radius_factor):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('sensitivity parameters must be finite')
    if prior_log_strain < 0 or min(friction_factor,strength_factor,radius_factor) <= 0:
        raise ValueError('inadmissible sensitivity parameter')
    if len(intermediate_gauges_m) != 2:
        raise ValueError('exactly two intermediate gauges required')
    gauges = [case['passes'][0]['entry_thickness_m'], *intermediate_gauges_m,
              case['passes'][-1]['exit_thickness_m']]
    if any(isinstance(h,bool) or not isinstance(h,(int,float)) or not math.isfinite(h) for h in gauges) or any(a<=b for a,b in zip(gauges,gauges[1:])):
        raise ValueError('gauges must be finite and strictly decreasing')
    c = 2/math.sqrt(3)
    coefficient = case['K_pa']*strength_factor
    if strain_convention == 'log_thickness':
        coefficient /= c**case['n']
    if stress_convention == 'plane_strain_difference':
        coefficient /= c
    # Conversion is a stated interpretation, not identification of source material.
    law = PowerHardeningLaw('AA5052','UNREPORTED',0,coefficient,case['n'],
                            'S1 coefficients with explicit assumed stress/strain mapping; no calibration')
    accumulated = c*prior_log_strain
    state=MaterialState('AA5052','UNREPORTED',accumulated,('Assumed initial history; not reported by S1',),293.15)
    outputs=[]
    for j,p in enumerate(case['passes']):
        h0,h1 = gauges[j:j+2]
        increment = c*math.log(h0/h1)
        strength_in, strength_out = law.stress(accumulated),law.stress(accumulated+increment)
        if p['back_tension_pa'] >= strength_in or p['front_tension_pa'] >= strength_out:
            raise ValueError(f'pass {j+1}: boundary tension reaches assumed local uniaxial strength; initial history unresolved')
        mean = law.mean_stress(accumulated,accumulated+increment)
        scenario = Scenario(f'literature_assumption_bridge_pass_{j+1}',True,h0,h1,p['width_m'],
            1.0,p['work_roll_radius_m']*radius_factor,case['density_kg_m3'],mean,
            p['friction_coefficient']*friction_factor,p['back_tension_pa'],p['front_tension_pa'],1.0)
        material = BiteHardening(state,law,(0.,3.),(273.15,373.15)) if hardening_model=='spatial' else None
        if elasticity is None:
            result = solve_slab(scenario,cells,bite_mode='established',verify_refinement=verify_refinement,material=material)
        else:
            result = solve_circular_contact(scenario,elasticity,cells,bite_mode='established',
                                            verify_refinement=verify_refinement,material=material)
        # Pressure/neutral point are rate-independent in this model. Map the
        # prescribed speed explicitly and scale the homogeneous work/flow terms.
        reported_speed = p['rolling_speed_m_s']
        if speed_interpretation == 'roll_surface':
            speed_scale = reported_speed/result['roll_surface_speed_m_s']
        elif speed_interpretation == 'entry_strip':
            speed_scale = reported_speed/result['entry_speed_m_s']
        else:
            speed_scale = reported_speed/result['exit_speed_m_s']
        for field in ('roll_surface_speed_m_s','roll_angular_speed_rad_s','entry_speed_m_s','exit_speed_m_s',
                      'volume_flow_m3_s','mass_flow_kg_s','mass_flow_residual_kg_s',
                      'roll_mechanical_power_both_rolls_w','plastic_work_power_w',
                      'solid_slip_dissipation_both_interfaces_w','net_tension_power_w',
                      'traction_power_to_strip_w','mechanical_work_residual_w'):
            result[field] *= speed_scale  # dimensionless ratio of two speeds
        result.update(pass_id=j+1,entry_thickness_m=h0,exit_thickness_m=h1,
            reduction_fraction=1-h1/h0,mean_uniaxial_flow_stress_pa=mean,
            assumed_entry_uniaxial_strength_pa=strength_in,assumed_exit_uniaxial_strength_pa=strength_out,
            equivalent_strain_start=accumulated,equivalent_strain_end=accumulated+increment,
            entry_tension_force_n=p['back_tension_pa']*p['width_m']*h0,
            exit_tension_force_n=p['front_tension_pa']*p['width_m']*h1,
            speed_interpretation=speed_interpretation)
        result['flags'] += ['CALIBRATION_DOMAIN_UNKNOWN','PRIOR_STATE_AND_CONSTITUTIVE_CONVENTIONS_ASSUMED',
                            'MILL_RATINGS_UNKNOWN']
        if hardening_model=='pass_mean' and elasticity is None:
            result['flags'].append('PASS_MEAN_HARDENING_RIGID_CONTACT_APPROXIMATION')
        if not (math.isclose(h0,p['entry_thickness_m'],rel_tol=1e-12) and math.isclose(h1,p['exit_thickness_m'],rel_tol=1e-12)):
            result['flags'].append('UNOBSERVED_GAUGE_COMBINATION')
        if friction_factor != 1:
            result['flags'].append('FRICTION_SENSITIVITY_NOT_A_REPORTED_SETTING')
        if radius_factor != 1:
            result['flags'].append('ALTERNATIVE_RADIUS_INTERPRETATION')
        trust=case['assumptions']['optimisation']
        if not trust['reduction_min']-1e-12 <= result['reduction_fraction'] <= trust['reduction_max']+1e-12:
            result['flags'].append('OUTSIDE_ASSUMED_REDUCTION_TRUST_REGION')
        outputs.append(result)
        accumulated += increment
        state=replace(state,accumulated_equivalent_plastic_strain=accumulated,history=state.history+(scenario.name,))
    return {'status':'CONDITIONAL_LITERATURE_COMPARISON_NOT_VALIDATED',
            'intermediate_gauges_m':list(intermediate_gauges_m),
            'assumptions':{'prior_log_strain':prior_log_strain,'strain_convention':strain_convention,
                           'stress_convention':stress_convention,'speed_interpretation':speed_interpretation,
                           'friction_factor':friction_factor,'strength_factor':strength_factor,
                           'radius_factor':radius_factor,'hardening_model':hardening_model,
                           'contact_model':'rigid' if elasticity is None else 'circular_hitchcock',
                           'material_temperature_k_assumed':293.15 if hardening_model=='spatial' else None,
                           'incoming_temper':None,'outgoing_temper':None},
            'passes':outputs,'peak_force_n':max(p['separating_force_n'] for p in outputs),
            'numerical_converged':all(p['numerical_converged'] for p in outputs),
            'physical_calibration_domain':'UNKNOWN',
            'thermal_validation':False,'product_quality_certified':False}


def compare_measurements(case, result):
    """Residuals only; no invented measurement uncertainty or validation threshold."""
    rows=[]
    for p,m,ref in zip(result['passes'],case['measurements'],case['source_model_outputs']):
        rows.append({'pass_id':p['pass_id'],
            'predicted_force_n':p['separating_force_n'],'author_measured_force_n':m['force_n'],
            'force_residual_n':p['separating_force_n']-m['force_n'],
            'force_relative_residual':p['separating_force_n']/m['force_n']-1,
            'predicted_forward_slip_fraction':p['forward_slip_fraction'],
            'author_measured_forward_slip_fraction':m['forward_slip_fraction'],
            'slip_residual_fraction':p['forward_slip_fraction']-m['forward_slip_fraction'],
            'slip_relative_residual':p['forward_slip_fraction']/m['forward_slip_fraction']-1,
            'source_model_force_n_separate':ref['force_n'],
            'source_model_slip_fraction_separate':ref['forward_slip_fraction'],
            'measurement_uncertainty':None,'independent_validation':False})
    return rows


def optimise_gauges(case, *, assumptions, grid_sizes=(21,41), cells=64):
    """Deterministic constrained mesh search + local mesh refinement; no global proof.

    Decisions are two intermediate gauges, parameterised by the first two
    reductions. The final reduction is constrained by the fixed product gauge.
    Coarse search grids do not claim convergence; the winning candidate and
    baseline are re-evaluated with checked 512/1024-cell integration.
    """
    limits=case['assumptions']['optimisation']
    lo,hi=limits['reduction_min'],limits['reduction_max']
    h0=case['passes'][0]['entry_thickness_m']; hf=case['passes'][-1]['exit_thickness_m']
    if any(isinstance(n,bool) or not isinstance(n,int) or n<3 for n in grid_sizes):
        raise ValueError('grid sizes must be integers >= 3')
    records=[]; best=None; stages=[]
    baseline_gauges=[p['exit_thickness_m'] for p in case['passes'][:2]]
    baseline=simulate_schedule(case,baseline_gauges,**assumptions,cells=512)
    if not baseline['numerical_converged']:
        raise ValueError('baseline failed numerical refinement gate')
    def candidate(r1,r2,stage):
        nonlocal best
        h1=h0*(1-r1); h2=h1*(1-r2); r3=1-hf/h2
        record={'stage':stage,'r1':r1,'r2':r2,'r3':r3,'h1_m':h1,'h2_m':h2}
        if min(r1,r2,r3)<lo-1e-12 or max(r1,r2,r3)>hi+1e-12:
            record.update(status='REJECTED_TRUST_REGION',peak_force_n=None)
        else:
            try:
                run=simulate_schedule(case,[h1,h2],**assumptions,cells=cells,verify_refinement=False)
                record.update(status='UNCHECKED_SEARCH_EVALUATION',peak_force_n=run['peak_force_n'])
                if best is None or run['peak_force_n']<best['peak_force_n']:
                    best=dict(record)
            except ValueError as e:
                record.update(status='REJECTED_SOLVER',peak_force_n=None,reason=str(e))
        records.append(record)
    # Include the published schedule explicitly so search cannot omit its point.
    candidate(1-baseline_gauges[0]/h0,1-baseline_gauges[1]/baseline_gauges[0],'published_point')
    for n in grid_sizes:
        for i in range(n):
            for j in range(n): candidate(lo+(hi-lo)*i/(n-1),lo+(hi-lo)*j/(n-1),f'global_{n}')
        stages.append({'stage':f'global_{n}','best_peak_force_n_search_grid':best['peak_force_n'] if best else None})
    if best is None:
        raise ValueError('no model-admissible candidate in assumed trust region')
    span=(hi-lo)/(grid_sizes[-1]-1)
    center=(best['r1'],best['r2'])
    for i in range(21):
        for j in range(21):
            candidate(center[0]+span*(i/10-1),center[1]+span*(j/10-1),'local_21')
    selected=simulate_schedule(case,[best['h1_m'],best['h2_m']],**assumptions,cells=512)
    if not selected['numerical_converged']:
        raise ValueError('selected schedule failed numerical refinement gate')
    if selected['peak_force_n']>baseline['peak_force_n']:
        selected=baseline
    return {'status':'CONDITIONAL_MESH_SEARCH_NOT_PLANT_OPTIMISATION',
            'objective':'minimise peak predicted stand separating force',
            'decision_variables':['pass1_exit_gauge_m','pass2_exit_gauge_m'],
            'fixed':'entry/final gauges, pass count, reported speeds/tensions/friction',
            'baseline':baseline,'selected':selected,
            'peak_force_change_fraction':selected['peak_force_n']/baseline['peak_force_n']-1,
            'trust_region':limits,'mesh_stages':stages,'global_optimum_proven':False,
            'candidate_count':len(records),'accepted_search_count':sum(r['peak_force_n'] is not None for r in records),
            'search_records':records}
