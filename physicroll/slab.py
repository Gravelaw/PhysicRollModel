"""Optional rigid-circular-roll, constant-yield slab pressure experiment.

This leading-order full-thickness equilibrium is motivated by Erfanian et al.
(2024), https://arxiv.org/html/2408.01347v1. Their rigid, perfectly plastic
asymptotics do not validate this code or the separate hardening/compliance model.
No roll flattening, elasticity, film shear or thermal closure is included.
"""
import math

from .model import Scenario


def _rk4(y, x, dx, rhs):
    a = rhs(x, y)
    b = rhs(x + dx/2, y + dx*a/2)
    c = rhs(x + dx/2, y + dx*b/2)
    d = rhs(x + dx, y + dx*c)
    return y + dx*(a+2*b+2*c+d)/6


def solve_slab(s: Scenario, cells: int = 256) -> dict:
    """Integrate entry and exit pressure branches and join at one neutral point.

    x runs entry to exit. q is compressive pressure, K plane-strain yield,
    h full strip thickness. Branch ODE: h dq/dx = K dh/dx +/- 2 mu q.
    Positive tangential traction accelerates strip before neutral; after it,
    negative traction retards strip. Signed per-roll torque is R*b*int(tau dx).
    """
    s.validate()
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 32 or cells > 32768:
        raise ValueError('cells must be an integer in [32,32768]')
    h0, h1, r, mu = s.entry_thickness_m, s.exit_thickness_m, s.work_roll_radius_m, s.friction_coefficient
    if h0 == h1 or mu == 0:
        raise ValueError('slab solution needs positive draft and friction')
    draft = h0-h1
    length = math.sqrt(r*draft-draft*draft/4)
    if math.tan(math.atan2(length,r-draft/2)) > mu+1e-12:
        raise ValueError('unassisted bite infeasible')
    k = 2/math.sqrt(3)*s.mean_flow_stress_pa
    q0, q1 = k-s.entry_tension_pa, k-s.exit_tension_pa
    if min(q0,q1) <= 0:
        raise ValueError('tension exceeds local pressure boundary capacity')
    dx=length/cells
    def geometry(x):
        y=length-x
        root=math.sqrt(r*r-y*y)
        return h1+2*(r-root), -2*y/root
    def rhs(sign):
        def f(x,q):
            h,dh=geometry(x)
            return (k*dh+sign*2*mu*q)/h
        return f
    entry=[q0]
    for i in range(cells):
        entry.append(_rk4(entry[-1],i*dx,dx,rhs(1)))
    exit_=[0.0]*(cells+1)
    exit_[-1]=q1
    for i in range(cells,0,-1):
        exit_[i-1]=_rk4(exit_[i],i*dx,-dx,rhs(-1))
    difference=[a-b for a,b in zip(entry,exit_)]
    crossings=[i for i in range(cells) if difference[i]*difference[i+1] < 0]
    if len(crossings)!=1:
        raise ValueError('no unique interior neutral point; slab case out of domain')
    i=crossings[0]
    fraction=-difference[i]/(difference[i+1]-difference[i])
    neutral=(i+fraction)*dx
    pressure=[]
    for j in range(cells+1):
        pressure.append(entry[j] if j*dx<=neutral else exit_[j])
    if min(pressure)<=0 or not all(map(math.isfinite,pressure)):
        raise ValueError('nonpositive or nonfinite pressure profile')
    # Integrate both smooth branches with a fractional neutral cell, preserving
    # opposite traction signs instead of assigning the entire cell one sign.
    force_integral=0.0
    signed_traction_integral=0.0
    for j in range(cells):
        left=j*dx
        right=(j+1)*dx
        if left < neutral < right:
            qn=entry[j]+fraction*(entry[j+1]-entry[j])
            force_integral+=(entry[j]+qn)*(neutral-left)/2+(qn+exit_[j+1])*(right-neutral)/2
            signed_traction_integral+=mu*((entry[j]+qn)*(neutral-left)/2-(qn+exit_[j+1])*(right-neutral)/2)
        elif right <= neutral:
            integral=(entry[j]+entry[j+1])*dx/2
            force_integral+=integral
            signed_traction_integral+=mu*integral
        else:
            integral=(exit_[j]+exit_[j+1])*dx/2
            force_integral+=integral
            signed_traction_integral-=mu*integral
    h_neutral=geometry(neutral)[0]
    strip_flux=s.entry_thickness_m*s.entry_speed_m_s
    surface_speed=strip_flux/h_neutral
    return {'status':'SYNTHETIC_RIGID_ROLL_SLAB', 'model':'constant_yield_rigid_circle',
            'cells':cells, 'neutral_position_from_entry_m':neutral,
            'contact_length_m':length, 'neutral_thickness_m':h_neutral,
            'roll_surface_speed_m_s':surface_speed,
            'forward_slip_fraction':s.entry_thickness_m*s.entry_speed_m_s/h1/surface_speed-1,
            'separating_force_n':s.width_m*force_integral,
            'torque_per_work_roll_nm':r*s.width_m*signed_traction_integral,
            'entry_pressure_pa':q0, 'exit_pressure_pa':q1,
            'pressure_at_neutral_pa':entry[i]+fraction*(entry[i+1]-entry[i]),
            'pressure_branch_mismatch_pa':abs((entry[i]+fraction*(entry[i+1]-entry[i]))-(exit_[i]+fraction*(exit_[i+1]-exit_[i]))),
            'min_pressure_pa':min(pressure),
            'limitations':['Rigid circular rolls and constant yield; no calibrated aluminium force prediction.',
                           'No flattening, elastic recovery, lubrication film or transient dynamics.']}
