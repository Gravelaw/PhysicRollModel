"""Offline finite-candidate feasibility/ranking; not online control or an optimiser.

An evaluator is injectable for future *validated* FEM/surrogate adapters. It must
retain the result contract, SI units, provenance and its own validity checks.
"""
from dataclasses import asdict, dataclass
import math
from typing import Callable, Iterable
from .model import Scenario, solve


@dataclass(frozen=True)
class Constraints:
    target_exit_thickness_m: float
    max_separating_force_n: float
    max_roll_drive_electrical_power_w: float
    min_mass_flow_kg_s: float

    def validate(self):
        for key, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be finite and positive')


def rank_candidates(candidates: Iterable[Scenario], constraints: Constraints,
                    evaluator: Callable[[Scenario], dict] = solve) -> dict:
    """Maximise throughput within explicit synthetic study constraints.

No candidate generation, plant writes, calibration or learned model is supplied.
All candidates (including rejected ones) and evaluator provenance are retained.
"""
    constraints.validate()
    rows = []
    for scenario in candidates:
        row = {'scenario':asdict(scenario),'feasible':False}
        try:
            scenario.validate()
            if not math.isclose(scenario.exit_thickness_m,constraints.target_exit_thickness_m,rel_tol=0,abs_tol=1e-12):
                raise ValueError('candidate does not meet target exit thickness')
            result = evaluator(scenario)
            if result['scenario'] != asdict(scenario):
                raise ValueError('evaluator returned mismatched scenario provenance')
            for key in ['mass_flow_kg_s','separating_force_n','roll_drive_electrical_power_w']:
                if not math.isfinite(result[key]) or result[key] < 0:
                    raise ValueError(f'evaluator returned invalid {key}')
            reasons = []
            if result['separating_force_n'] > constraints.max_separating_force_n:
                reasons.append('force limit')
            if result['roll_drive_electrical_power_w'] > constraints.max_roll_drive_electrical_power_w:
                reasons.append('electrical power limit')
            if result['mass_flow_kg_s'] < constraints.min_mass_flow_kg_s:
                reasons.append('minimum throughput')
            row.update(result=result,feasible=not reasons,reason=', '.join(reasons))
        except ValueError as exc:
            row['reason'] = str(exc)
        rows.append(row)
    feasible = sorted((r for r in rows if r['feasible']),key=lambda r:-r['result']['mass_flow_kg_s'])
    return {'status':'SYNTHETIC_OFFLINE_CANDIDATE_STUDY','constraints':asdict(constraints),
            'objective':'maximise mass flow among the supplied feasible candidates',
            'selected_scenario':feasible[0]['scenario']['name'] if feasible else None,'candidates':rows}
