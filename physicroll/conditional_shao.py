"""Explicit conditional Shao AA5052 replay, without fitting or mill certification."""
import csv
import hashlib
import json
import math
from pathlib import Path

from .checked_schedule import CheckedPass, InterpassHandoff
from .materials import MaterialState, PowerHardeningLaw
from .model import Scenario
from .operating import PassOperatingPlan
from .schedule_search import OperatingChoice, SearchSpace, checked_replay, search_schedules


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / 'docs/research/data/shao2015_raw.json'
ADAPTER_PATH = ROOT / 'docs/research/data/shao2015_conditional_adapter.json'
SENSITIVITY_PATH = ROOT / 'docs/research/data/shao2015_prior_sensitivity.json'
EXISTING = ROOT / 'scenarios/literature/shao2015_aa5052'
TEMPER_LABEL = 'unknown_source_temper_conditional'
RAW_SHA256 = '7825df6a53edcfa10f6c5c679f697150d8d43b96ea25f9dda51f76c15aa6e31b'
DECLARED_PRIOR_LOG_STRAINS = (0.0, 0.01, 0.05, 0.2)
SUPPORTED_CONTRACT = {
    'speed_mapping': 'reported_as_entry_strip',
    'roll_radius_interpretation': 'table_1_radius',
    'strain_mapping': 'log_thickness_to_plane_strain_equivalent',
    'stress_mapping': 'current_bite_hardening_plane_strain',
    'source_history_law': 'unresolved_not_reproduced',
    'solver': 'spatial_slab', 'cells': 256, 'bite_mode': 'established',
    'interpass_temperature': 'prescribed_constant_bookkeeping',
    'thermal_enabled': False, 'fit_performed': False,
}
SUPPORTED_ASSUMPTIONS = {
    'prior_log_thickness_strain': 0.05,
    'material_temper_label': TEMPER_LABEL,
    'material_temperature_k': 293.15,
    'density_kg_m3': 2680,
    'drive_efficiency': 1.0,
    'assumed_equivalent_strain_range': [0.0, 2.0],
    'assumed_temperature_range_k': [273.15, 350.0],
}


class CheckedReplayFailure(ValueError):
    """A complete route was rejected by the checked solver, not adapter setup."""


def audited_raw():
    """Load source-only transcription; assumptions live in a separate adapter."""
    raw_bytes = RAW_PATH.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != RAW_SHA256:
        raise ValueError('audited raw source checksum changed; re-audit before replay')
    return json.loads(raw_bytes)


def _adapter_config():
    config = json.loads(ADAPTER_PATH.read_text())
    if (config['adapter_id'] != 'shao2015_fixed_rigid_slab_prior_log_005' or
            config.get('executable_contract') != SUPPORTED_CONTRACT or
            any(config.get('explicit_assumptions', {}).get(key) != value
                for key, value in SUPPORTED_ASSUMPTIONS.items()) or
            config.get('equipment_limits') is not None):
        raise ValueError('conditional adapter conventions differ from executable contract')
    return config


def compare_existing_fixture(raw=None):
    """Return precise source-table differences, without modifying either record."""
    raw = audited_raw() if raw is None else raw
    with (EXISTING / 'inputs.csv').open(newline='') as stream:
        inputs = list(csv.DictReader(stream))
    with (EXISTING / 'measured_validation.csv').open(newline='') as stream:
        measured = list(csv.DictReader(stream))
    with (EXISTING / 'reference_model_outputs.csv').open(newline='') as stream:
        calculated = list(csv.DictReader(stream))
    if not all(len(rows) == len(raw['passes']) for rows in (inputs, measured, calculated)):
        return ['pass-count mismatch between raw extraction and existing fixture']
    differences = []
    input_map = {'entry_thickness_mm': ('table_1', 'entry_mm'),
                 'exit_thickness_mm': ('table_1', 'exit_mm'),
                 'width_mm': ('table_1', 'width_mm'),
                 'back_tension_MPa': ('table_1', 'back_tension_mpa'),
                 'front_tension_MPa': ('table_1', 'front_tension_mpa'),
                 'work_roll_radius_mm': ('table_1', 'radius_labelled_mm'),
                 'rolling_speed_m_s': ('table_1', 'reported_speed_m_s'),
                 'friction_coefficient': ('table_2_model_input', 'friction_coefficient')}
    measured_map = {'force_kN': 'force_kn', 'forward_slip_fraction': 'forward_slip_fraction'}
    calculated_map = {'force_kN': 'force_kn', 'forward_slip_fraction': 'forward_slip_fraction',
                      'flattened_radius_mm': 'flattened_radius_mm'}
    for index, (source, old_in, old_meas, old_calc) in enumerate(
            zip(raw['passes'], inputs, measured, calculated), 1):
        if (source['pass'] != index or any(int(old['pass_id']) != index
                                           for old in (old_in, old_meas, old_calc))):
            differences.append(f'pass {index}: pass identifier')
        for field, (section, key) in input_map.items():
            if float(old_in[field]) != source[section][key]:
                differences.append(f'pass {index}: inputs.{field}')
        for field, key in measured_map.items():
            if float(old_meas[field]) != source['table_2_measured'][key]:
                differences.append(f'pass {index}: measured.{field}')
        for field, key in calculated_map.items():
            if float(old_calc[field]) != source['table_2_author_calculated'][key]:
                differences.append(f'pass {index}: author_calculated.{field}')
    return differences


def fixed_conditional_route():
    """The one published three-pass path; no optimization freedoms or safety caps."""
    raw = audited_raw()
    if compare_existing_fixture(raw):
        raise ValueError('audited raw and established fixture disagree')
    rows = raw['passes']
    gauges = (rows[0]['table_1']['entry_mm']/1000,) + tuple(
        row['table_1']['exit_mm']/1000 for row in rows)
    choices = tuple(OperatingChoice(row['table_1']['reported_speed_m_s'],
                                    row['table_1']['back_tension_mpa']*1e6,
                                    row['table_1']['front_tension_mpa']*1e6,
                                    'Shao Table 1; speed assumed entry-strip') for row in rows)
    space = SearchSpace(gauges, gauges[1:-1], 3, 3,
                        tuple((choice,) for choice in choices), 1)
    return space, choices


def _build_fixed_route(gauges, choices, *, cells=256, prior_log_strain=None):
    raw = audited_raw()
    config = _adapter_config()
    assumptions = config['explicit_assumptions']
    space, expected = fixed_conditional_route()
    if gauges != space.gauges_m or choices != expected:
        raise ValueError('conditional Shao adapter only accepts the reported fixed route')
    if isinstance(cells, bool) or not isinstance(cells, int) or cells not in (256, 512):
        raise ValueError('conditional replay supports reviewed 256 or 512 cell grids')
    if prior_log_strain is None:
        prior_log_strain = assumptions['prior_log_thickness_strain']
    elif prior_log_strain not in DECLARED_PRIOR_LOG_STRAINS or isinstance(prior_log_strain, bool):
        raise ValueError('prior strain must be a predeclared sensitivity case')
    initial_state = MaterialState('AA5052', assumptions['material_temper_label'],
                                  2/math.sqrt(3)*prior_log_strain,
                                  (f'assumed_prior_log_strain_{prior_log_strain:g}',),
                                  assumptions['material_temperature_k'])
    n = raw['material_source']['hardening_exponent']
    law = PowerHardeningLaw('AA5052', assumptions['material_temper_label'], 0.0,
                            raw['material_source']['strength_coefficient_mpa']*1e6
                            *(math.sqrt(3)/2)**n, n,
                            'Shao Eq. 2 K,n; assumed log-to-equivalent conversion; Eq. 3 unresolved')
    passes = []
    for index, (row, choice) in enumerate(zip(raw['passes'], choices), 1):
        table = row['table_1']
        scenario = Scenario(f'shao_conditional_pass_{index}', True,
                            gauges[index-1], gauges[index], table['width_mm']/1000,
                            choice.entry_speed_m_s, table['radius_labelled_mm']/1000,
                            assumptions['density_kg_m3'], 1e8,
                            row['table_2_model_input']['friction_coefficient'],
                            choice.entry_tension_pa, choice.exit_tension_pa,
                            assumptions['drive_efficiency'])
        passes.append(CheckedPass(scenario, PassOperatingPlan(scenario.name),
                                  SUPPORTED_CONTRACT['solver'], cells,
                                  SUPPORTED_CONTRACT['bite_mode'],
                                  tuple(assumptions['assumed_equivalent_strain_range']),
                                  tuple(assumptions['assumed_temperature_range_k'])))
    events = tuple(InterpassHandoff(i, 'prescribed', assumptions['material_temperature_k'],
                                    'not_modeled', None,
                                    'assumed constant bookkeeping temperature; no thermal model')
                   for i in range(1, len(passes)))
    try:
        return checked_replay(tuple(passes), initial_state, law,
                              interpass_handoffs=events)
    except ValueError as exc:
        raise CheckedReplayFailure(str(exc)) from exc


def _compare_observations(replay):
    """Keep published measurements separate from solver inputs and capacities."""
    comparisons = []
    for row, item in zip(audited_raw()['passes'], replay['passes']):
        observed = row['table_2_measured']
        predicted_force = item['mechanics']['separating_force_n']
        predicted_slip = item['mechanics']['forward_slip_fraction']
        comparisons.append({'pass': row['pass'],
                            'observed_force_n': observed['force_kn']*1000,
                            'predicted_force_n': predicted_force,
                            'signed_force_residual_fraction': predicted_force/(observed['force_kn']*1000)-1,
                            'observed_forward_slip_fraction': observed['forward_slip_fraction'],
                            'predicted_forward_slip_fraction': predicted_slip,
                            'signed_slip_residual_fraction': predicted_slip/observed['forward_slip_fraction']-1})
    return comparisons


def run_conditional_comparison():
    """Return source-measurement residuals and a one-candidate checked replay."""
    _adapter_config()  # Configuration errors must not become grid rejections.
    space, _ = fixed_conditional_route()
    search = search_schedules(space, _build_fixed_route)
    if search['selected'] is None:
        raise ValueError('fixed conditional route rejected by checked replay')
    replay = search['selected']['checked_replay']
    finer_replay = _build_fixed_route(search['selected']['gauges_m'],
                                     search['selected']['choices'], cells=512)
    numerical_differences = []
    for coarse, fine in zip(replay['passes'], finer_replay['passes']):
        numerical_differences.append({
            'pass': coarse['pass_number'],
            'force_relative_change': (fine['mechanics']['separating_force_n'] /
                                      coarse['mechanics']['separating_force_n'] - 1),
            'slip_absolute_change': (fine['mechanics']['forward_slip_fraction'] -
                                     coarse['mechanics']['forward_slip_fraction'])})
    return {'status': 'CONDITIONAL_COMPARISON_NOT_VALIDATION',
            'adapter_id': _adapter_config()['adapter_id'],
            'fixture_differences': compare_existing_fixture(),
            'search': search, 'finer_grid_replay': finer_replay,
            'numerical_differences': numerical_differences,
            'comparisons': _compare_observations(replay)}


def run_declared_prior_sensitivity():
    """No-fit replay of pre-existing assumed histories; reject unsupported cases."""
    adapter = _adapter_config()
    space, choices = fixed_conditional_route()
    study = json.loads(SENSITIVITY_PATH.read_text())
    historical = json.loads((EXISTING / 'assumptions.json').read_text())
    if (study.get('study_id') != 'shao2015_declared_prior_log_strain_sensitivity_v1' or
            study.get('fixed_adapter_id') != adapter['adapter_id'] or
            study.get('axis') != 'assumed_prior_log_thickness_strain' or
            tuple(study.get('values', ())) != DECLARED_PRIOR_LOG_STRAINS or
            tuple(historical['material']['prior_log_strain_sensitivity']) != DECLARED_PRIOR_LOG_STRAINS or
            study.get('fit_performed') is not False or study.get('equipment_limits') is not None):
        raise ValueError('declared prior-strain study differs from executable contract')
    cases = []
    for prior in DECLARED_PRIOR_LOG_STRAINS:
        try:
            replay = _build_fixed_route(space.gauges_m, choices, prior_log_strain=prior)
        except CheckedReplayFailure as exc:
            cases.append({'assumed_prior_log_thickness_strain': prior,
                          'status': 'REJECTED_BY_CHECKED_MODEL', 'reason': str(exc),
                          'comparisons': None})
            continue
        cases.append({'assumed_prior_log_thickness_strain': prior,
                      'status': ('CONDITIONAL_REPLAY_INDETERMINATE'
                                 if replay['declared_bounds_status'] == 'INDETERMINATE'
                                 else 'DECLARED_BOUNDS_VIOLATED'),
                      'declared_bounds_status': replay['declared_bounds_status'],
                      'reason': None, 'comparisons': _compare_observations(replay)})
    return {'status': 'NO_FIT_ASSUMPTION_SENSITIVITY', 'study_id': study['study_id'],
            'fixed_adapter_id': adapter['adapter_id'], 'cases': cases,
            'limitations': ['Predeclared values are analyst assumptions, not an uncertainty distribution.',
                            'No source-independent material or friction calibration.',
                            'Observed force/slip are comparison outputs, not equipment limits.']}
