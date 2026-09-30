"""Leading-order, constant-yield, rigid-roll slab (SI/full thickness).

See docs/mechanics-audit.md. Equations 21--28 in Erfanian et al. (2024),
https://arxiv.org/html/2408.01347v1 motivate this approximation, not its validation.
The projected traction/velocity convention is used consistently for torque/work;
this is not exact finite-angle contact mechanics or a sticking/flattening model.
"""
import math
from .model import Scenario


def _rk4(y, x, dx, rhs):
    a = rhs(x, y)
    b = rhs(x + dx/2, y + dx*a/2)
    c = rhs(x + dx/2, y + dx*b/2)
    d = rhs(x + dx, y + dx*c)
    return y + dx*(a+2*b+2*c+d)/6


def _neutral_location(difference, dx):
    """Include an exact nodal root, reject boundary/nonunique roots."""
    roots = [i*dx for i, value in enumerate(difference) if value == 0]
    for i, (a, b) in enumerate(zip(difference, difference[1:])):
        if (a < 0 < b) or (b < 0 < a):
            roots.append((i-a/(b-a))*dx)
    if len(roots) != 1 or not 0 < roots[0] < (len(difference)-1)*dx:
        raise ValueError('no unique interior neutral point; slab case out of domain')
    return roots[0]


def _solve_grid(s, cells, bite_mode):
    h0, h1, r, mu = s.entry_thickness_m, s.exit_thickness_m, s.work_roll_radius_m, s.friction_coefficient
    draft = h0-h1
    length = math.sqrt(r*draft-draft*draft/4)
    tangent = length/(r-draft/2)
    unassisted_ok = tangent <= mu+1e-12
    if bite_mode == 'unassisted' and not unassisted_ok:
        raise ValueError('unassisted bite infeasible: tan(alpha) > mu')
    k = 2/math.sqrt(3)*s.mean_flow_stress_pa
    q0, q1 = k-s.entry_tension_pa, k-s.exit_tension_pa
    dx = length/cells
    def geometry(x):
        y = length-x
        root = math.sqrt(r*r-y*y)
        # Rationalised circle sagitta avoids cancellation at small draft.
        return h1+2*y*y/(r+root), -2*y/root
    def rhs(sign):
        def f(x, q):
            h, dh = geometry(x)
            return (k*dh+sign*2*mu*q)/h
        return f
    entry = [q0]
    for i in range(cells):
        entry.append(_rk4(entry[-1], i*dx, dx, rhs(1)))
    exit_ = [0.0]*(cells+1)
    exit_[-1] = q1
    for i in range(cells, 0, -1):
        exit_[i-1] = _rk4(exit_[i], i*dx, -dx, rhs(-1))
    if not all(math.isfinite(q) for q in entry+exit_):
        raise ValueError('nonfinite integrated pressure')
    neutral = _neutral_location([a-b for a,b in zip(entry,exit_)], dx)
    j = min(int(neutral/dx), cells-1)
    fraction = (neutral-j*dx)/dx
    qn = entry[j]+fraction*(entry[j+1]-entry[j])
    h_neutral = geometry(neutral)[0]
    flux = h0*s.entry_speed_m_s  # volume flow per unit width [m2/s]
    surface_speed = flux/h_neutral
    # Split at neutral so no quadrature cell averages opposite traction signs.
    segments = []
    for i in range(cells):
        left, right = i*dx, (i+1)*dx
        if left < neutral < right:
            segments += [(left,neutral,entry[i],qn,1), (neutral,right,qn,exit_[i+1],-1)]
        elif right <= neutral:
            segments.append((left,right,entry[i],entry[i+1],1))
        else:
            segments.append((left,right,exit_[i],exit_[i+1],-1))
    pressures = [q for _,_,a,b,_ in segments for q in (a,b)]
    if min(pressures) <= 0:
        raise ValueError('nonpositive pressure profile')
    shear_ratio = mu*max(pressures)/(k/2)
    if shear_ratio > 1:
        raise ValueError('Coulomb shear exceeds material shear yield; sticking model required')
    load_terms, traction_terms, slip_terms, strip_work_terms = [], [], [], []
    for left,right,a,b,sign in segments:
        ds = right-left
        va, vb = flux/geometry(left)[0], flux/geometry(right)[0]
        ta, tb = sign*mu*a, sign*mu*b
        load_terms.append(ds*(a+b)/2)
        traction_terms.append(ds*(ta+tb)/2)
        slip_terms.append(ds*(ta*(surface_speed-va)+tb*(surface_speed-vb))/2)
        strip_work_terms.append(ds*(ta*va+tb*vb)/2)
    force = s.width_m*math.fsum(load_terms)
    torque = r*s.width_m*math.fsum(traction_terms)  # ONE work roll
    slip_power = 2*s.width_m*math.fsum(slip_terms)  # BOTH interfaces
    volume_flow = s.width_m*flux
    plastic_power = volume_flow*k*math.log(h0/h1)
    tension_power = volume_flow*(s.exit_tension_pa-s.entry_tension_pa)
    roll_power = 2*torque*surface_speed/r
    strip_traction_power = 2*s.width_m*math.fsum(strip_work_terms)
    residual = roll_power+tension_power-plastic_power-slip_power
    scale = max(abs(roll_power), abs(tension_power), plastic_power, slip_power, 1e-30)
    if slip_power < 0:
        raise ValueError('negative interface dissipation')
    result = {
        'status':'UNVALIDATED_RIGID_ROLL_SLAB', 'model':'constant_yield_projected_contact',
        'cells':cells, 'numerical_converged':False, 'refinement_checked':False,
        'bite_mode':bite_mode, 'unassisted_bite_feasible':unassisted_ok,
        'bite_tangent':tangent, 'friction_coefficient':mu,
        'neutral_position_from_entry_m':neutral, 'contact_length_m':length,
        'neutral_thickness_m':h_neutral, 'roll_surface_speed_m_s':surface_speed,
        'entry_speed_m_s':s.entry_speed_m_s, 'exit_speed_m_s':flux/h1,
        'forward_slip_fraction':h_neutral/h1-1,
        'volume_flow_m3_s':volume_flow, 'mass_flow_kg_s':s.density_kg_m3*volume_flow,
        'mass_flow_residual_kg_s':s.density_kg_m3*s.width_m*h1*(flux/h1)-s.density_kg_m3*volume_flow,
        'separating_force_n':force, 'torque_per_work_roll_nm':torque,
        'roll_mechanical_power_both_rolls_w':roll_power,
        'plastic_work_power_w':plastic_power, 'solid_slip_dissipation_both_interfaces_w':slip_power,
        'net_tension_power_w':tension_power, 'traction_power_to_strip_w':strip_traction_power,
        'mechanical_work_residual_w':residual, 'mechanical_work_residual_relative':abs(residual)/scale,
        'entry_pressure_pa':q0, 'exit_pressure_pa':q1,
        'pressure_at_neutral_pa':qn, 'max_pressure_pa':max(pressures), 'min_pressure_pa':min(pressures),
        'pressure_branch_mismatch_pa':abs(qn-(exit_[j]+fraction*(exit_[j+1]-exit_[j]))),
        'max_coulomb_shear_over_yield_shear':shear_ratio,
        'flags':([] if unassisted_ok else ['UNASSISTED_BITE_SCREEN_FAILED_ESTABLISHED_DIAGNOSTIC_ONLY']),
        'limitations':['Constant yield and rigid circular rolls; no aluminium calibration.',
                       'Projected small-angle traction/work; no elastic recovery, sticking or flattening.',
                       'No mill ratings or threading dynamics; numerical convergence is not physical validity.']}
    if not all(math.isfinite(v) for v in result.values() if isinstance(v,(int,float))):
        raise ValueError('nonfinite slab output')
    return result


def solve_slab(s: Scenario, cells: int = 256, *, bite_mode: str = 'unassisted',
               verify_refinement: bool = True) -> dict:
    """Checked two-grid result, or explicitly unchecked grid for coarse searches.

    Established mode bypasses only the conservative *unassisted threading* check,
    recording its failure. It is not evidence that a mill can thread that draft.
    Coordinate x runs entry to exit, h is full thickness, q positive compression.
    h*q' = K*h' +/- 2*mu*q. Positive strip traction precedes the neutral point.
    """
    s.validate()
    if isinstance(cells,bool) or not isinstance(cells,int) or not 32 <= cells <= 16384:
        raise ValueError('cells must be an integer in [32,16384]')
    if not isinstance(verify_refinement,bool) or bite_mode not in ('unassisted','established'):
        raise ValueError('invalid refinement or bite mode')
    if s.entry_thickness_m == s.exit_thickness_m or s.friction_coefficient == 0:
        raise ValueError('slab solution needs positive draft and friction')
    low = _solve_grid(s,cells,bite_mode)
    if not verify_refinement:
        low['flags'].append('GRID_REFINEMENT_NOT_CHECKED')
        return low
    high = _solve_grid(s,2*cells,bite_mode)
    # Torque scaled by friction capacity so near-zero signed torque is well posed.
    force_error = abs(high['separating_force_n']-low['separating_force_n'])/high['separating_force_n']
    torque_scale = s.friction_coefficient*high['separating_force_n']*s.work_roll_radius_m
    torque_error = abs(high['torque_per_work_roll_nm']-low['torque_per_work_roll_nm'])/torque_scale
    slip_error = abs(high['forward_slip_fraction']-low['forward_slip_fraction'])
    high['refinement_checked'] = True
    high['refinement'] = {'coarse_cells':cells,'force_relative_change':force_error,
                          'torque_change_over_capacity':torque_error,'slip_absolute_change':slip_error}
    high['numerical_converged'] = (force_error <= 1e-4 and torque_error <= 1e-4 and
                                   slip_error <= 1e-6 and high['mechanical_work_residual_relative'] <= 1e-4)
    if not high['numerical_converged']:
        high['flags'].append('NUMERICAL_TOLERANCE_NOT_MET')
    return high
