"""Optional circular Hitchcock coupling; physical shaft radius stays unchanged.

Li, Matsumoto & Utsunomiya (2018), Eq.1, DOI:
https://doi.org/10.2355/isijinternational.ISIJINT-2017-623
That stainless-steel experiment documents circular-model limitations; it does
not validate these parameters or this aluminium implementation. No mill spring,
elastic strip recovery, foil/sticking or noncircular deformation is represented.
"""
from dataclasses import asdict, dataclass
import math
from .slab import solve_slab


def _finite(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)


@dataclass(frozen=True)
class CircularRollElasticity:
    young_modulus_pa: float
    poisson_ratio: float
    provenance: str
    max_radius_ratio: float = 1.5

    def validate(self):
        if not isinstance(self.provenance,str) or not self.provenance.strip():
            raise ValueError('elastic parameters need provenance')
        if not _finite(self.young_modulus_pa) or not 1e9 <= self.young_modulus_pa <= 1e14:
            raise ValueError('roll Young modulus must be Pa in analyst sanity envelope [1e9,1e14]')
        if not _finite(self.poisson_ratio) or not 0 <= self.poisson_ratio < .5:
            raise ValueError('requires nonauxetic isotropic roll: 0 <= nu < 0.5')
        if not _finite(self.max_radius_ratio) or not 1 < self.max_radius_ratio <= 1.5:
            raise ValueError('radius ratio envelope must be in (1,1.5]; not a validated range')

    @property
    def compliance_pa_inv(self):
        self.validate()
        return 16*(1-self.poisson_ratio**2)/(math.pi*self.young_modulus_pa)

    def radius(self, physical_radius_m, total_force_n, width_m, draft_m):
        if not all(_finite(v) for v in (physical_radius_m,total_force_n,width_m,draft_m)) or min(physical_radius_m,width_m,draft_m)<=0 or total_force_n<0:
            raise ValueError('Hitchcock requires R,b,draft > 0 and total force >= 0 in SI')
        ratio=1+self.compliance_pa_inv*total_force_n/(width_m*draft_m)
        if ratio > self.max_radius_ratio:
            raise ValueError('circular radius outside assumed envelope; noncircular/contact model needed')
        return physical_radius_m*ratio


def solve_circular_contact(scenario, elasticity, cells=256, *, material=None,
                           bite_mode='established', verify_refinement=True,
                           radius_tolerance=1e-8, max_iterations=80, relaxation=.5):
    """Damped fixed-point R'=R*[1+C*F(R')/(b*draft)]. No uniqueness claim.

    Each final pressure grid has its own refinement/work gate. A failed fixed
    point is explicitly returned as nonconverged, never a silently accepted load.
    U=omega*R uses nominal shaft R; R' affects geometry only. Projection neglects
    local elastic surface velocity, elastic work and hysteresis; see audit.
    """
    scenario.validate()
    if not isinstance(elasticity,CircularRollElasticity):
        raise ValueError('CircularRollElasticity required')
    elasticity.validate()
    if not _finite(radius_tolerance) or not 1e-12 <= radius_tolerance <= 1e-5:
        raise ValueError('radius tolerance must be in [1e-12,1e-5]')
    if isinstance(max_iterations,bool) or not isinstance(max_iterations,int) or not 1 <= max_iterations <= 300:
        raise ValueError('iteration count must be in [1,300]')
    if not _finite(relaxation) or not 0 < relaxation <= 1:
        raise ValueError('relaxation must be in (0,1]')
    radius=scenario.work_roll_radius_m
    history=[]
    for iteration in range(1,max_iterations+1):
        result=solve_slab(scenario,cells,bite_mode=bite_mode,verify_refinement=verify_refinement,
                          material=material,contact_radius_m=radius)
        target=elasticity.radius(scenario.work_roll_radius_m,result['separating_force_n'],
                                scenario.width_m,scenario.entry_thickness_m-scenario.exit_thickness_m)
        residual=(target-radius)/scenario.work_roll_radius_m
        history.append({'iteration':iteration,'contact_radius_m':radius,
                        'force_n':result['separating_force_n'],'radius_residual_over_nominal':residual})
        if abs(residual)<=radius_tolerance:
            break
        radius += relaxation*(target-radius)
    converged=abs(residual)<=radius_tolerance
    result.update(status='UNVALIDATED_CIRCULAR_ELASTIC_CONTACT',
                  flattening={'equation':'R_contact=R_nominal*(1+C*F_total/(width*draft))',
                    'elasticity':asdict(elasticity),'compliance_pa_inv':elasticity.compliance_pa_inv,
                    'converged':converged,'radius_tolerance':radius_tolerance,
                    'radius_residual_over_nominal':residual,'iteration_history':history,
                    'source':'https://doi.org/10.2355/isijinternational.ISIJINT-2017-623',
                    'parameters_calibrated':False,'uniqueness_proven':False})
    result['numerical_converged'] = result['numerical_converged'] and converged
    result['flags'].append('CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED')
    if not converged:
        result['flags'].append('FLATTENING_FIXED_POINT_NOT_CONVERGED')
    result['limitations'] = ['Circular flattening only; no noncircular deformation or elastic strip recovery.',
        'Nominal shaft radius for torque/speed; local elastic surface kinematics and hysteresis omitted.',
        'Projected small-angle mechanics; no sticking, roll stack or stand-gap compliance.',
        'Numerical convergence does not establish aluminium accuracy or physical capacity.']
    return result
