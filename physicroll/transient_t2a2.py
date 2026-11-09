"""Restricted fixed-material, massive-bar/two-shaft verification case.

The continuum eigenmode is a manufactured initial condition for this standalone
benchmark. There is no moving web, reel inventory, contact, or restart API.
"""

from dataclasses import dataclass
import math


MODEL_ID = 'T2A2_FIXED_MATERIAL_BAR_SHAFT_V1'
LENGTH_M = 1.0
EA_N = 1000.0
LINE_MASS_KG_M = 10.0
SHAFT_MASS_KG = 100.0
RADIUS_M = 0.1
PRELOAD_N = 1.0
AMPLITUDE_M = 1e-6
WAVE_SPEED_M_S = 10.0
FIRST_ROOT = 0.4435207878818884
FREQUENCY_RAD_S = WAVE_SPEED_M_S * FIRST_ROOT
PERIOD_S = 2 * math.pi / FREQUENCY_RAD_S


@dataclass(frozen=True)
class T2A2Case:
    elements: int
    maximum_step_s: float
    mode: str = 'first_elastic'

    def __post_init__(self):
        if type(self.elements) is not int or not 2 <= self.elements <= 64:
            raise ValueError('T2A2 elements must be an integer from 2 to 64')
        if (type(self.maximum_step_s) not in (float, int) or
                not math.isfinite(self.maximum_step_s) or self.maximum_step_s <= 0):
            raise ValueError('T2A2 maximum step must be finite and positive')
        if self.mode not in ('first_elastic', 'rigid_translation'):
            raise ValueError('unsupported T2A2 benchmark mode')
        if self.maximum_step_s * WAVE_SPEED_M_S * self.elements > 0.5:
            raise ValueError('T2A2 step exceeds wave-resolution budget')
        if math.ceil(PERIOD_S / self.maximum_step_s) > 2000:
            raise ValueError('T2A2 episode exceeds 2000 steps')


def _matvec(diag, off, vector):
    out = [diag[i] * vector[i] for i in range(len(diag))]
    for i, entry in enumerate(off):
        out[i] += entry * vector[i + 1]
        out[i + 1] += entry * vector[i]
    return out


def _solve_tridiagonal(diag, off, rhs):
    """Thomas elimination for the positive definite midpoint operator."""
    n = len(diag)
    d = diag.copy()
    r = rhs.copy()
    for i in range(1, n):
        factor = off[i - 1] / d[i - 1]
        d[i] -= factor * off[i - 1]
        r[i] -= factor * r[i - 1]
    answer = [0.0] * n
    answer[-1] = r[-1] / d[-1]
    for i in range(n - 2, -1, -1):
        answer[i] = (r[i] - off[i] * answer[i + 1]) / d[i]
    return answer


def _matrices(elements):
    dx = LENGTH_M / elements
    n = elements + 1
    mass_bar_diag = [2 * LINE_MASS_KG_M * dx / 3] * n
    mass_bar_diag[0] = mass_bar_diag[-1] = LINE_MASS_KG_M * dx / 3
    mass_off = [LINE_MASS_KG_M * dx / 6] * elements
    mass_diag = mass_bar_diag.copy()
    mass_diag[0] += SHAFT_MASS_KG
    mass_diag[-1] += SHAFT_MASS_KG
    stiffness_diag = [2 * EA_N / dx] * n
    stiffness_diag[0] = stiffness_diag[-1] = EA_N / dx
    stiffness_off = [-EA_N / dx] * elements
    return mass_diag, mass_off, mass_bar_diag, stiffness_diag, stiffness_off


def _state(time_s, displacement, velocity, case, mass_diag, mass_off,
           stiffness_diag, stiffness_off):
    dx = LENGTH_M / case.elements
    tensions = [PRELOAD_N + EA_N * (displacement[i + 1] - displacement[i]) / dx
                for i in range(case.elements)]
    if min(tensions) <= 0:
        raise ValueError('T2A2 left the positive-tension benchmark domain')
    mv = _matvec(mass_diag, mass_off, velocity)
    ku = _matvec(stiffness_diag, stiffness_off, displacement)
    kinetic = sum(a * b for a, b in zip(velocity, mv)) / 2
    elastic = sum(a * b for a, b in zip(displacement, ku)) / 2
    values = displacement + velocity + tensions + [kinetic, elastic]
    if not all(math.isfinite(value) for value in values):
        raise ValueError('T2A2 state exceeded the finite numerical domain')
    return {
        'time_s': time_s,
        'bar_displacement_m': displacement.copy(),
        'bar_velocity_m_s': velocity.copy(),
        'element_tension_n': tensions,
        'left_angle_rad': displacement[0] / RADIUS_M,
        'right_angle_rad': displacement[-1] / RADIUS_M,
        'left_speed_rad_s': velocity[0] / RADIUS_M,
        'right_speed_rad_s': velocity[-1] / RADIUS_M,
        'kinetic_energy_j': kinetic,
        'elastic_perturbation_energy_j': elastic,
        'perturbation_energy_j': kinetic + elastic,
    }


def run_coupled_bar(case: T2A2Case):
    """Advance one period with consistent bar mass and endpoint shaft masses."""
    if not isinstance(case, T2A2Case):
        raise ValueError('T2A2 requires a T2A2Case')
    md, mo, bar_md, kd, ko = _matrices(case.elements)
    if case.mode == 'first_elastic':
        displacement = [AMPLITUDE_M * (math.cos(FIRST_ROOT * i / case.elements) -
                        10 * FIRST_ROOT * math.sin(FIRST_ROOT * i / case.elements))
                        for i in range(case.elements + 1)]
        velocity = [0.0] * (case.elements + 1)
    else:
        displacement = [0.0] * (case.elements + 1)
        velocity = [AMPLITUDE_M] * (case.elements + 1)
    states = [_state(0.0, displacement, velocity, case, md, mo, kd, ko)]
    max_energy_defect = 0.0
    max_interface_work_defect = 0.0
    while states[-1]['time_s'] < PERIOD_S - 1e-12:
        t = states[-1]['time_s']
        h = min(case.maximum_step_s, PERIOD_S - t)
        kv = _matvec(kd, ko, velocity)
        rhs = _matvec(md, mo, velocity)
        ku = _matvec(kd, ko, displacement)
        rhs = [rhs[i] - h * ku[i] - h * h * kv[i] / 4 for i in range(len(rhs))]
        system_diag = [md[i] + h * h * kd[i] / 4 for i in range(len(md))]
        system_off = [mo[i] + h * h * ko[i] / 4 for i in range(len(mo))]
        next_velocity = _solve_tridiagonal(system_diag, system_off, rhs)
        next_displacement = [displacement[i] + h * (velocity[i] + next_velocity[i]) / 2
                             for i in range(len(displacement))]
        midpoint_displacement = [(a + b) / 2 for a, b in
                                 zip(displacement, next_displacement)]
        midpoint_velocity = [(a + b) / 2 for a, b in zip(velocity, next_velocity)]
        acceleration = [(b - a) / h for a, b in zip(velocity, next_velocity)]
        # The bar endpoint residual is the shaft-on-bar force. Its opposite
        # acts on each shaft; this is the discrete action/reaction work check.
        bar_mass_a = _matvec(bar_md, mo, acceleration)
        midpoint_ku = _matvec(kd, ko, midpoint_displacement)
        left_bar_force = bar_mass_a[0] + midpoint_ku[0]
        right_bar_force = bar_mass_a[-1] + midpoint_ku[-1]
        left_shaft_force = SHAFT_MASS_KG * acceleration[0]
        right_shaft_force = SHAFT_MASS_KG * acceleration[-1]
        max_interface_work_defect = max(
            max_interface_work_defect,
            abs(h * midpoint_velocity[0] * (left_bar_force + left_shaft_force)),
            abs(h * midpoint_velocity[-1] * (right_bar_force + right_shaft_force)),
        )
        displacement, velocity = next_displacement, next_velocity
        next_state = _state(min(t + h, PERIOD_S), displacement, velocity,
                            case, md, mo, kd, ko)
        max_energy_defect = max(max_energy_defect,
                                abs(next_state['perturbation_energy_j'] -
                                    states[0]['perturbation_energy_j']))
        states.append(next_state)
    return {
        'model_id': MODEL_ID,
        'mode': case.mode,
        'shaft_speed_role': 'predicted_from_coupled_inertia',
        'bar_material_role': 'fixed_material_no_flux',
        'episode_outcome': 'COMPLETED_REQUESTED_DURATION',
        'requested_duration_s': PERIOD_S,
        'completed_duration_s': states[-1]['time_s'],
        'states': states,
        'maximum_energy_defect_j': max_energy_defect,
        'maximum_interface_work_defect_j': max_interface_work_defect,
        'combined_mass_kg': LINE_MASS_KG_M * LENGTH_M + 2 * SHAFT_MASS_KG,
        'limitations': ['fixed material, radii, inertia and geometry',
                        'undamped linear elastic bar',
                        'no material flux, reel inventory, bite or contact'],
    }
