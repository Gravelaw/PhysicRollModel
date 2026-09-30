"""Synthetic history-aware isotropic hardening, separate from the v0.2 load closure.

The plane-strain thickness increment is a kinematic idealisation. Material constants
must be fitted to the named alloy/temper; this module predicts no grain or damage state.
"""
from dataclasses import asdict, dataclass, replace
import math

from .model import Scenario, solve


@dataclass(frozen=True)
class MaterialState:
    alloy: str
    temper: str
    accumulated_equivalent_plastic_strain: float
    history: tuple[str, ...]
    temperature_k: float

    def validate(self):
        if not self.alloy or not self.temper or not isinstance(self.history, tuple):
            raise ValueError("alloy, temper and tuple history are required")
        if any(not isinstance(item, str) or not item for item in self.history):
            raise ValueError("history entries must be nonempty strings")
        if not math.isfinite(self.accumulated_equivalent_plastic_strain) or self.accumulated_equivalent_plastic_strain < 0:
            raise ValueError("accumulated strain must be finite and nonnegative")
        if not math.isfinite(self.temperature_k) or self.temperature_k <= 0:
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
            if not math.isfinite(value) or value < 0:
                raise ValueError("hardening parameters must be finite and nonnegative")
        if self.yield_stress_pa <= 0 or self.exponent > 1:
            raise ValueError("yield stress must be positive and exponent <= 1")

    def stress(self, equivalent_strain: float) -> float:
        self.validate()
        if not math.isfinite(equivalent_strain) or equivalent_strain < 0:
            raise ValueError("equivalent strain must be nonnegative")
        return self.yield_stress_pa + self.strength_coefficient_pa * equivalent_strain ** self.exponent

    def mean_stress(self, start: float, end: float) -> float:
        self.validate()
        if not (math.isfinite(start) and math.isfinite(end)) or start < 0 or end < start:
            raise ValueError("invalid strain interval")
        if start == end:
            return self.stress(start)
        n = self.exponent
        power_mean = (end ** (n + 1) - start ** (n + 1)) / ((n + 1) * (end - start))
        return self.yield_stress_pa + self.strength_coefficient_pa * power_mean


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
    mean = law.mean_stress(state.accumulated_equivalent_plastic_strain, end)
    solved = solve(replace(scenario, mean_flow_stress_pa=mean))
    next_state = replace(state, accumulated_equivalent_plastic_strain=end,
                         history=state.history + (scenario.name,))
    return {'status': 'SYNTHETIC_UNCALIBRATED', 'state_in': asdict(state),
            'state_out': asdict(next_state), 'equivalent_plastic_strain_increment': increment,
            'mean_flow_stress_pa': mean, 'hardening_provenance': law.provenance,
            'baseline_mechanics': solved}
