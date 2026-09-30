"""Calibrated-measurement conversion helpers; not a live sensor interface.

The caller must supply qualified geometry, tare/calibration and synchronized
values. Helpers return SI quantities and do not imply mill-model validation.
"""
import math


def _finite(name, value, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite SI number')
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f'{name} is outside its allowed domain')
    return value


def tension_stress_pa(force_n, width_m, local_thickness_m):
    """Convert a measured longitudinal strip force at its local gauge to stress."""
    result = _finite('force_n',force_n,nonnegative=True) / (_finite('width_m',width_m,positive=True)
              * _finite('local_thickness_m',local_thickness_m,positive=True))
    return _finite('tension stress',result,nonnegative=True)


def strip_mass_flow_kg_s(density_kg_m3, width_m, local_thickness_m, local_speed_m_s):
    """Quasi-steady local flow observer; entry/exit comparisons require parcel alignment."""
    result = (_finite('density_kg_m3',density_kg_m3,positive=True)
              * _finite('width_m',width_m,positive=True)
              * _finite('local_thickness_m',local_thickness_m,positive=True)
              * _finite('local_speed_m_s',local_speed_m_s,nonnegative=True))
    return _finite('mass flow',result,nonnegative=True)


def tension_from_wrap_reaction_n(reaction_n, wrap_angle_rad, *, tare_n, geometry_qualified=False):
    """Symmetric equal-tension deflector: T=(R-tare)/[2 sin(theta/2)].

    Only valid if incoming/outgoing tensions are approximately equal and the
    sensor bearing reaction axis resolves their symmetric resultant. Caller
    must explicitly attest geometry qualification; inertia/friction omitted.
    """
    if geometry_qualified is not True:
        raise ValueError('Deflector geometry must be explicitly qualified')
    load = _finite('reaction_n',reaction_n,nonnegative=True)-_finite('tare_n',tare_n,nonnegative=True)
    angle = _finite('wrap_angle_rad',wrap_angle_rad,positive=True)
    if load < 0 or angle > math.pi:
        raise ValueError('Negative net reaction or wrap angle outside (0, pi]')
    return _finite('tension force',load/(2*math.sin(angle/2)),nonnegative=True)


def hydraulic_differential_thrust_n(cap_pressure_pa, rod_pressure_pa, cap_radius_m, rod_radius_m):
    """Ideal double-acting cylinder F=p_cap*A_cap - p_rod*(A_cap-A_rod).

    Signed thrust; seal friction, moving mass, weight and hydraulic calibration
    are omitted. This is an actuator force estimate, not extra bite load.
    """
    pc=_finite('cap_pressure_pa',cap_pressure_pa,nonnegative=True)
    pr=_finite('rod_pressure_pa',rod_pressure_pa,nonnegative=True)
    rc=_finite('cap_radius_m',cap_radius_m,positive=True)
    rr=_finite('rod_radius_m',rod_radius_m,nonnegative=True)
    if rr >= rc:
        raise ValueError('Rod radius must be smaller than cap radius')
    result=math.pi*(pc*rc*rc-pr*(rc*rc-rr*rr))
    return _finite('hydraulic thrust',result)


def forward_slip_fraction(exit_strip_speed_m_s, roll_surface_speed_m_s):
    """Observed strip-vs-roll speed slip; denominator must be safely nonzero."""
    v=_finite('exit_strip_speed_m_s',exit_strip_speed_m_s,nonnegative=True)
    u=_finite('roll_surface_speed_m_s',roll_surface_speed_m_s,positive=True)
    if u < 1e-6:
        raise ValueError('Roll surface speed below 1e-6 m/s; slip is ill-conditioned')
    return _finite('forward slip', (v-u)/u)


def reel_shaft_torque_nm(tension_force_n, radius_m, inertia_kg_m2,
                         angular_acceleration_rad_s2, loss_torque_nm=0, *, winding=True):
    """Signed positive-rotation shaft torque: +/-T*r + I*alpha + loss.

    `winding=True` takes up strip; false pays out. Positive rotation is defined
    along local strip transport for each reel, and loss torque opposes positive
    rotation. No reversal/friction law, changing radius or acceleration solver.
    The acceleration and loss terms are user-supplied, never inferred from the
    steady-state rolling model.
    """
    tension=_finite('tension_force_n',tension_force_n,nonnegative=True)
    radius=_finite('radius_m',radius_m,positive=True)
    inertia=_finite('inertia_kg_m2',inertia_kg_m2,nonnegative=True)
    alpha=_finite('angular_acceleration_rad_s2',angular_acceleration_rad_s2)
    losses=_finite('loss_torque_nm',loss_torque_nm,nonnegative=True)
    if not isinstance(winding,bool):
        raise ValueError('winding must be boolean')
    return _finite('reel shaft torque', (1 if winding else -1)*tension*radius + inertia*alpha + losses)
