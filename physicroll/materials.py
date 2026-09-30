"""Synthetic history-aware isotropic hardening, separate from the v0.2 load closure.

The plane-strain thickness increment is a kinematic idealisation. Material constants
must be fitted to the named alloy/temper; this module predicts no grain or damage state.
"""
from dataclasses import asdict, dataclass, replace
import math

from .model import Scenario, solve


def _finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (float, int)) and math.isfinite(value)


@dataclass(frozen=True)
class MaterialState:
    alloy: str
    temper: str
    accumulated_equivalent_plastic_strain: float
    history: tuple[str, ...]
    temperature_k: float

    def validate(self):
        if not isinstance(self.alloy,str) or not self.alloy.strip() or not isinstance(self.temper,str) or not self.temper.strip() or not isinstance(self.history, tuple):
            raise ValueError("alloy, temper and tuple history are required")
        if any(not isinstance(item, str) or not item for item in self.history):
            raise ValueError("history entries must be nonempty strings")
        if not _finite_number(self.accumulated_equivalent_plastic_strain) or self.accumulated_equivalent_plastic_strain < 0:
            raise ValueError("accumulated strain must be finite and nonnegative")
        if not _finite_number(self.temperature_k) or self.temperature_k <= 0:
            raise ValueError("absolute temperature must be positive")


@dataclass(frozen=True)
class PowerHardeningLaw:
    alloy: str
    temper: str
    yield_stress_pa: float
    strength_coefficient_pa: float
    exponent: float
    provenance: str
    synthetic: bool = True

    def validate(self):
        if not self.alloy or not self.temper or not self.provenance or self.synthetic is not True:
            raise ValueError("a named synthetic curve and provenance are required")
        for value in (self.yield_stress_pa, self.strength_coefficient_pa, self.exponent):
            if not _finite_number(value) or value < 0:
                raise ValueError("hardening parameters must be finite and nonnegative")
        if self.yield_stress_pa + self.strength_coefficient_pa <= 0 or self.exponent > 1:
            raise ValueError("nonzero strength and exponent <= 1 required")

    def stress(self, equivalent_strain: float) -> float:
        self.validate()
        if not _finite_number(equivalent_strain) or equivalent_strain < 0:
            raise ValueError("equivalent strain must be nonnegative")
        value = self.yield_stress_pa + self.strength_coefficient_pa * equivalent_strain ** self.exponent
        if not math.isfinite(value):
            raise ValueError('flow stress exceeds numerical domain')
        return value

    def mean_stress(self, start: float, end: float) -> float:
        self.validate()
        if not (_finite_number(start) and _finite_number(end)) or start < 0 or end < start:
            raise ValueError("invalid strain interval")
        if start == end:
            return self.stress(start)
        n = self.exponent
        # Avoid subtracting almost equal powers for a vanishing strain interval.
        if start == 0:
            power_mean = end**n/(n+1)
        elif end <= 1.5*start:
            ratio = (end-start)/start
            power_mean = start**n * math.expm1((n+1)*math.log1p(ratio))/((n+1)*ratio)
        else:
            ratio = start/end
            power_mean = end**n * (1-ratio**(n+1))/((n+1)*(1-ratio))
        value = self.yield_stress_pa + self.strength_coefficient_pa * power_mean
        if not math.isfinite(value):
            raise ValueError('mean flow stress exceeds numerical domain')
        return value


def pass_with_history(scenario: Scenario, state: MaterialState, law: PowerHardeningLaw) -> dict:
    """Run one synthetic pass and return an explicit next material state.

    The old v0.2 heuristic mechanics are retained; this merely supplies its mean
    uniaxial flow stress. No temperature evolution or annealing is inferred here.
    """
    scenario.validate()
    state.validate()
    law.validate()
    if (state.alloy, state.temper) != (law.alloy, law.temper):
        raise ValueError("material state and calibrated curve identity differ")
    increment = 2 / math.sqrt(3) * math.log(scenario.entry_thickness_m / scenario.exit_thickness_m)
    end = state.accumulated_equivalent_plastic_strain + increment
    if scenario.entry_tension_pa >= law.stress(state.accumulated_equivalent_plastic_strain) or scenario.exit_tension_pa >= law.stress(end):
        raise ValueError('boundary tension reaches local uniaxial strength; prior state inadmissible')
    mean = law.mean_stress(state.accumulated_equivalent_plastic_strain, end)
    solved = solve(replace(scenario, mean_flow_stress_pa=mean))
    next_state = replace(state, accumulated_equivalent_plastic_strain=end,
                         history=state.history + (scenario.name,))
    return {'status': 'SYNTHETIC_UNCALIBRATED', 'state_in': asdict(state),
            'state_out': asdict(next_state), 'equivalent_plastic_strain_increment': increment,
            'mean_flow_stress_pa': mean, 'hardening_provenance': law.provenance,
            'hardening_units':{'yield_stress':'Pa','strength_coefficient':'Pa','strain':'1','exponent':'1'},
            'calibrated_strain_range':None,'calibrated_temperature_range_k':None,
            'baseline_mechanics': solved}


@dataclass(frozen=True)
class BiteHardening:
    """Optional homogeneous path through a bite, with explicit assumed envelope.

    eps_eq(x)=eps_in+2/sqrt(3)*ln(h_in/h(x)). No redundant shear, recovery,
    temperature feedback or fitted aluminium curve. Kps=2Y/sqrt(3).
    The variable-strength equilibrium is derived in docs/contact-increment.md;
    https://arxiv.org/html/2408.01347v1 supplies only its constant-strength limit.
    """
    state: MaterialState
    law: PowerHardeningLaw
    assumed_strain_range: tuple[float, float]
    assumed_temperature_range_k: tuple[float, float]

    def validate_pass(self, scenario):
        self.state.validate()
        self.law.validate()
        if (self.state.alloy,self.state.temper) != (self.law.alloy,self.law.temper):
            raise ValueError('material identity mismatch')
        for interval in (self.assumed_strain_range,self.assumed_temperature_range_k):
            if not isinstance(interval,tuple) or len(interval)!=2 or not all(_finite_number(v) for v in interval) or not 0 <= interval[0] < interval[1]:
                raise ValueError('explicit finite increasing assumed material envelope required')
        end = self.strain_at_thickness(scenario.entry_thickness_m,scenario.exit_thickness_m)
        if not self.assumed_strain_range[0] <= self.state.accumulated_equivalent_plastic_strain <= end <= self.assumed_strain_range[1]:
            raise ValueError('material strain outside assumed envelope (not calibration range)')
        if not self.assumed_temperature_range_k[0] <= self.state.temperature_k <= self.assumed_temperature_range_k[1]:
            raise ValueError('material temperature outside assumed envelope')
        if self.law.stress(self.state.accumulated_equivalent_plastic_strain) <= scenario.entry_tension_pa or self.law.stress(end) <= scenario.exit_tension_pa:
            raise ValueError('boundary tension reaches local uniaxial strength')

    def strain_at_thickness(self, entry_m, local_m):
        if not all(_finite_number(v) for v in (entry_m,local_m)) or not 0 < local_m <= entry_m:
            raise ValueError('positive full thickness with local <= entry required')
        return self.state.accumulated_equivalent_plastic_strain+2/math.sqrt(3)*math.log(entry_m/local_m)

    def stress_at_thickness(self, entry_m, local_m):
        return self.law.stress(self.strain_at_thickness(entry_m,local_m))

    def mean_stress(self, entry_m, exit_m):
        return self.law.mean_stress(self.state.accumulated_equivalent_plastic_strain,
                                    self.strain_at_thickness(entry_m,exit_m))

    def pass_metadata(self, entry_m, exit_m, name):
        end = self.strain_at_thickness(entry_m,exit_m)
        state_out = replace(self.state,accumulated_equivalent_plastic_strain=end,
                            history=self.state.history+(name,))
        return {'state_in':asdict(self.state),'state_out':asdict(state_out),
                'law':asdict(self.law),'stress_units':'Pa','strain_units':'1',
                'assumed_strain_range':self.assumed_strain_range,
                'assumed_temperature_range_k':self.assumed_temperature_range_k,
                'calibrated_strain_range':None,'calibrated_temperature_range_k':None,
                'temperature_feedback':False,'strain_rate_dependence':False}
