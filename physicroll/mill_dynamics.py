"""Gauge control, incoming hardness, drive torsion and speed changes around the chatter model.

Status: ``UNVALIDATED_LINEAR_MILL_DYNAMICS_SCREEN``. Software-verified against closed-form
limits derived from the equations below; no plant data, no calibrated parameters, no
probability of any cause. Tags: [V] read in a cited source, [D] derived (planner or this
module), [M] from memory / unverified.

This module wraps ``physicroll.chatter`` WITHOUT modifying it: the 6x6 matrix of
``chatter.assemble_state_matrix`` is extended by one state, eigenvalues come from
``chatter.eigenvalues``, bite sensitivities from ``chatter.derive_bite_response``.

Sign conventions (as chatter.py)
--------------------------------
x_w, x_b   upper work / backup roll displacement, positive AWAY from the pass line; the
           exit-thickness perturbation is dh = 2*x_w (symmetric half-stack model).
x_s        NEW: displacement of the housing-spring anchor (hydraulic gap cylinder), positive
           = gap opening. Total actuator stroke S = 2*x_s.
e          work/backup run-out [m]; positive e pushes the work roll toward the strip at both
           contacts (contact force K_wb*(x_w - x_b + e)); unloaded-gap disturbance d = -2e.
dF         separating-force perturbation, positive pushes the rolls apart.
sigma_e/x  entry / exit TENSILE stress perturbations [Pa].
dV_r       roll surface speed perturbation [m/s] (both work rolls in phase).

Gaugemeter AGC with a hydraulic gap cylinder (W4.1)
---------------------------------------------------
BISRA gaugemeter h = S + F/M, correction dS = -alpha*dF/M [V: IJCA 9(2) AGC paper];
cylinder closed-loop bandwidth 20-30 Hz [V: Scheidl et al. 2016; Karl et al. 2011].
Half-stack extension [D]:
    M_b*x_b'' = K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*(x_b - x_s) - C_h*x_b'
    dF_meas   = K_h*(x_b - x_s)            (load-cell force; the housing damper acts to
                                            ground and is not measured - modelling choice)
    x_s'      = omega_c*(x_s_ref - x_s),  x_s_ref = -alpha*dF_meas/(2*M),  omega_c = 2*pi*f_c
with M = stand.mill_modulus_n_m. State z = [x_w, v_w, x_b, v_b, sigma_e, sigma_x, x_s]
(``AGC_STATE_NAMES``).

Static limits [D, re-derived here; tension coupling off]. Equilibrium gives
dF = K_wb*(x_w - x_b + e) = K_h*(x_b - x_s) and so dh = 2*x_s + dF/M - 2e; the loop gives
2*x_s = -alpha*dF/M, hence dh = (1 - alpha)*dF/M - 2e. With dF = -Q*dh + dF0 (Q = -F_h the
strip modulus, dF0 the force change at fixed gap from any bite input):
    run-out          dh = -2e*M/(M + (1-alpha)*Q)
    bite input dF0   dh = (1-alpha)*dF0/(M + (1-alpha)*Q)
            (entry thickness dF0 = F_hin*dh_in; flow stress dF0 = dF/dY*dY;
             friction dF0 = dF/dmu*dmu)
alpha = 0 recovers chatter.py; alpha = 1 prints run-out through in full (dh = -2e, an
amplification (M+Q)/M over alpha = 0) [V: Ichiryu, J. JHPS 26(6):778] and removes every
bite-input gauge error.

"Tension coupling off" is the constant-tension idealisation (reel tension regulators hold
the tension). With coupling ON, the chatter.py spans have constant-speed far ends, which act
as integral mass-flow control at DC [D]: du_e = du_x = 0 forces dh -> 0 for run-out,
flow-stress and roll-speed inputs, and dh -> (h1/h0)*dh_in for incoming gauge, whatever the
AGC gain (for alpha < 1). At alpha = 1 with coupling on the DC equations become singular
(the force level is undetermined: a neutral zero mode), which is reported, not hidden.

AGC / chatter interaction [D, finding of this module]: well above its bandwidth a
first-order loop lags 90 degrees, x_s ~ -j*(alpha*K_h/(2*M))*(omega_c/omega)*x_b, so the anchor
force K_h*x_s on the backup roll is in phase with its velocity: an equivalent NEGATIVE damping
of about alpha*K_h^2*omega_c/(2*M*omega^2). For the SPEC.md 1.6 stand at 179 Hz, alpha = 0.9 and
25 Hz this is ~2e6 N*s/m, larger than the housing damping (~1.1e6), so the spec's 7-state loop
lowers the chatter critical speed markedly instead of negligibly. ``agc_stability`` reports the
number; the optional ``force_filter_hz`` shows that it largely disappears once the loop rolls
off faster than first order (real servo-valve / oil-column / force-filter dynamics).

Incoming hardness (W4.2)
------------------------
Cyclic ~2 % hardness variation from a soft/hard coil sector, synchronous with the decoiler,
first harmonic dominant [V: ABB "Improvement of thickness tolerances"]. dF/dY and df/dY by
central differences (+-0.5 %) of chatter.derive_bite_response [D]. Decoiler frequency
n*u_e/(pi*D_coil); exit-strip pitch pi*D_coil*h0/(h1*n) [D, continuity].

Drive train and speed changes (W4.3)
------------------------------------
Free-free torsional chain J*theta'' + K*theta = 0 (2-5 inertias), solved by Jacobi rotations
on J^-1/2 K J^-1/2 [D]. Benchmark [V: J. Phys. Conf. Ser. 2419 (2022) 012027]. First mode
design guidance 10-20 Hz [V: Gao et al.]. Reel inertia reflected to the motor:
J = J_motor + pi*rho*W*(R^4 - R_m^4)/(2*N^2) [V: Soler, Isermann & Feldmann 2008].
Roll-speed ripple (torsional oscillation of the work rolls), from chatter.py continuity [D]:
du_x = (1+f)*dV_r, du_e = (1+f)*(h1/h0)*dV_r, entering the tension rows only (the slab force
and slip are rate independent). DC limit with coupling on and alpha < 1 [D]: dh = 0 and
F_se*s_e + F_sx*s_x = 0, f_se*s_e + f_sx*s_x = -(1+f)*dV_r/V_r.
Quasi-static gauge shift on a speed change: friction changes with speed so the force changes
at fixed gap [V context: Zhang et al. 2017 IJCA 10(6)]; dh = (1-alpha)*dF0/(M + (1-alpha)*Q),
dF0 = dF/dmu*dmu [D].

NOT modelled: the cylinder as anything but a first-order position loop (no servo-valve,
oil-column or pressure dynamics), AGC monitor / feed-forward / mass-flow AGC, eccentricity
compensation, tension regulators (only the two idealisations: constant far-end speed or
constant tension), torsional-to-vertical coupling other than through a supplied roll-speed
ripple, motor/drive control loops, gear backlash, strip elastic recovery, rate sensitivity
of the flow stress, thermal effects, roll bending and cross-width variation.
"""
from dataclasses import dataclass, replace
from typing import Optional
import cmath
import math

from . import chatter
from .chatter import (BitePass, BiteResponse, StandModel, StripSpans, assemble_state_matrix,
                      critical_speed, derive_bite_response, eigenvalues)

STATUS = 'UNVALIDATED_LINEAR_MILL_DYNAMICS_SCREEN'
AGC_STATE_NAMES = tuple(chatter.STATE_NAMES) + ('x_cylinder_m',)
AGC_DISTURBANCES = ('work_backup_runout', 'entry_thickness', 'flow_stress', 'roll_speed')
DISTURBANCE_UNITS = {'work_backup_runout': 'm', 'entry_thickness': 'm', 'flow_stress': 'Pa',
                     'roll_speed': 'm/s'}

_REFERENCE_LENGTH_M = 1e-6
_REFERENCE_STRESS_PA = 1e6
_ZERO_MODE_RELATIVE = 1e-9
_LIMITATIONS = (
    'Linear small-perturbation screen around one operating point; no plant validation.',
    'Synthetic, uncalibrated structural, cylinder, drive and bite parameters.',
    'The gap cylinder is a first-order position loop; servo-valve and oil-column dynamics, '
    'AGC monitor/feed-forward and eccentricity compensation are not modelled.',
    'Strip spans use either constant far-end speed (coupling on) or constant tension '
    '(coupling off); real tension regulators lie between these idealisations.',
)
_BASIS = {
    'gaugemeter_law': '[V] BISRA gaugemeter h = S + F/M, dS = -alpha*dF/M (IJCA 9(2))',
    'cylinder_bandwidth': '[V] 20-30 Hz closed loop (Scheidl et al. 2016; Karl et al. 2011)',
    'half_stack_cylinder_extension': '[D] anchor state x_s, dF_meas = K_h*(x_b - x_s), '
                                     'first-order loop',
    'static_limits': '[D] derived from the equilibrium equations in the module docstring',
    'eccentricity_amplification': '[V] Ichiryu, J. JHPS 26(6):778',
}


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _base_result(extra_limitations=()):
    return {'status': STATUS, 'flags': [], 'limitations': list(_LIMITATIONS) +
            list(extra_limitations), 'basis': dict(_BASIS)}


def _options(bite_damping_transit_fraction=0.5, couple_tension=True):
    if not _finite(bite_damping_transit_fraction) or not 0 <= bite_damping_transit_fraction <= 5:
        raise ValueError('bite_damping_transit_fraction must be finite in [0, 5]')
    if not isinstance(couple_tension, bool):
        raise ValueError('couple_tension must be a bool')
    return float(bite_damping_transit_fraction), couple_tension


def _check_system(stand, bite, spans, exit_speed_m_s):
    if not isinstance(stand, StandModel):
        raise ValueError('stand must be a StandModel')
    stand.validate()
    if not isinstance(bite, BiteResponse):
        raise ValueError('bite must be a BiteResponse')
    bite.validate()
    if not isinstance(spans, StripSpans):
        raise ValueError('spans must be a StripSpans')
    spans.validate()
    if not _finite(exit_speed_m_s) or exit_speed_m_s <= 0:
        raise ValueError('exit_speed_m_s must be a finite positive number')


def _check_frequencies(frequencies_hz):
    if not isinstance(frequencies_hz, (list, tuple)) or not frequencies_hz:
        raise ValueError('frequencies_hz must be a nonempty list')
    if not all(_finite(f) and f > 0 for f in frequencies_hz):
        raise ValueError('frequencies must be finite and > 0 Hz')
    return [float(f) for f in frequencies_hz]


# ----------------------------------------------------------------------------- inputs


@dataclass(frozen=True)
class GaugemeterAGC:
    """Gaugemeter AGC: compensation gain alpha in [0, 1] and cylinder bandwidth [Hz].

    ``force_filter_hz`` (optional, default None = the W4 7-state model) adds a first-order
    low-pass on the measured force, F_f' = omega_f*(dF_meas - F_f), x_s_ref = -alpha*F_f/(2*M),
    as an 8th state. It is an analyst option [D], not from a cited source: it shows how much
    of the AGC/chatter interaction rests on the single first-order roll-off of the loop.
    """
    compensation_gain: float
    bandwidth_hz: float
    force_filter_hz: Optional[float] = None

    def validate(self):
        if not _finite(self.compensation_gain) or not 0 <= self.compensation_gain <= 1:
            raise ValueError('compensation_gain (alpha) must be finite in [0, 1]; '
                             'over-compensation alpha > 1 is not supported')
        if not _finite(self.bandwidth_hz) or not 0 < self.bandwidth_hz <= 1000:
            raise ValueError('bandwidth_hz must be finite in (0, 1000] Hz')
        if self.force_filter_hz is not None and (
                not _finite(self.force_filter_hz) or not 0 < self.force_filter_hz <= 10000):
            raise ValueError('force_filter_hz must be None or finite in (0, 10000] Hz')

    @property
    def omega_c_rad_s(self):
        return 2 * math.pi * self.bandwidth_hz

    @property
    def state_names(self):
        names = AGC_STATE_NAMES
        return names + ('force_filtered_n',) if self.force_filter_hz is not None else names

    def to_dict(self):
        self.validate()
        return {'compensation_gain': float(self.compensation_gain),
                'bandwidth_hz': float(self.bandwidth_hz),
                'force_filter_hz': (float(self.force_filter_hz)
                                    if self.force_filter_hz is not None else None),
                'omega_c_rad_s': self.omega_c_rad_s}


def _check_agc(agc):
    if not isinstance(agc, GaugemeterAGC):
        raise ValueError('agc must be a GaugemeterAGC')
    agc.validate()


def _agc_flags(agc):
    flags = []
    if not 20 <= agc.bandwidth_hz <= 30:
        flags.append('CYLINDER_BANDWIDTH_OUTSIDE_CITED_20_30_HZ')
    if agc.force_filter_hz is not None:
        flags.append('ANALYST_FORCE_FILTER_OPTION_NOT_FROM_CITED_SOURCE')
    return flags


def _flow_values(flow_sensitivity):
    """(dF/dY, df/dY) from a mapping such as the dict returned by flow_stress_sensitivity."""
    if not isinstance(flow_sensitivity, dict):
        raise ValueError("disturbance 'flow_stress' needs flow_sensitivity: a dict with "
                         "dforce_dflow_stress_m2 and dslip_dflow_stress_per_pa "
                         '(e.g. from flow_stress_sensitivity)')
    out = []
    for key in ('dforce_dflow_stress_m2', 'dslip_dflow_stress_per_pa'):
        value = flow_sensitivity.get(key)
        if not _finite(value):
            raise ValueError(f'flow_sensitivity[{key!r}] must be a finite number')
        out.append(float(value))
    return out


# ------------------------------------------------------------------- state matrices


def assemble_agc_state_matrix(stand, bite, spans, exit_speed_m_s, agc, **options):
    """Physical (unscaled) state matrix for z = agc.state_names (7x7; 8x8 with a force filter).

    Rows 0-5 are chatter.assemble_state_matrix plus the anchor term K_h*x_s/M_b in the
    backup-roll row; row 6 is the cylinder loop x_s' = omega_c*(x_s_ref - x_s); row 7 (only
    with ``force_filter_hz``) is the measured-force low-pass.
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    _check_agc(agc)
    beta, couple = _options(**options)
    a6 = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                               bite_damping_transit_fraction=beta, couple_tension=couple)
    n = len(agc.state_names)
    a = [list(row) + [0.0] * (n - 6) for row in a6] + [[0.0] * n for _ in range(n - 6)]
    kh, mb = stand.housing_stiffness_n_m, stand.backup_roll_mass_kg
    a[3][6] = kh / mb
    wc, alpha, m = agc.omega_c_rad_s, agc.compensation_gain, stand.mill_modulus_n_m
    if agc.force_filter_hz is None:
        g = alpha * kh / (2 * m)                  # x_s_ref = -g*(x_b - x_s)
        a[6][2] = -wc * g
        a[6][6] = wc * (g - 1)
    else:
        wf = 2 * math.pi * agc.force_filter_hz
        a[6][6] = -wc
        a[6][7] = -wc * alpha / (2 * m)           # x_s_ref = -alpha*F_f/(2*M)
        a[7][2], a[7][6], a[7][7] = wf * kh, -wf * kh, -wf
    return a


def _input_vector(stand, bite, spans, exit_speed_m_s, disturbance, couple, flow=None, n=7):
    """B column per unit disturbance (m, m, Pa, m/s); same convention as chatter.py."""
    b = [0.0] * n
    h0, h1, f = bite.entry_thickness_m, bite.exit_thickness_m, bite.forward_slip_fraction
    vr = exit_speed_m_s / (1 + f)
    ke = spans.youngs_modulus_pa / spans.entry_span_length_m
    kx = spans.youngs_modulus_pa / spans.exit_span_length_m
    mw = stand.work_roll_mass_kg
    if disturbance == 'work_backup_runout':
        b[1] = -stand.work_backup_contact_stiffness_n_m / mw
        b[3] = stand.work_backup_contact_stiffness_n_m / stand.backup_roll_mass_kg
    elif disturbance == 'entry_thickness':
        b[1] = bite.dforce_dentry_thickness_n_m / mw
        if couple:
            fhin = bite.dslip_dentry_thickness_per_m
            b[4] = ke * vr * (h1 / h0 * fhin - (1 + f) * h1 / h0 ** 2)
            b[5] = -kx * vr * fhin
    elif disturbance == 'flow_stress':
        dfy, dsy = _flow_values(flow)
        b[1] = dfy / mw
        if couple:
            b[4] = ke * vr * h1 / h0 * dsy
            b[5] = -kx * vr * dsy
    elif disturbance == 'roll_speed':
        if couple:
            b[4] = ke * (1 + f) * h1 / h0
            b[5] = -kx * (1 + f)
    else:
        raise ValueError(f'disturbance must be one of {AGC_DISTURBANCES}')
    return b


def _scales(stand, n):
    omega = math.sqrt((stand.work_backup_contact_stiffness_n_m + stand.housing_stiffness_n_m)
                      / stand.work_roll_mass_kg)
    lr = _REFERENCE_LENGTH_M
    s = [lr, lr * omega, lr, lr * omega, _REFERENCE_STRESS_PA, _REFERENCE_STRESS_PA, lr,
         lr * stand.housing_stiffness_n_m]
    return s[:n]


def _scaled(a, s):
    n = len(a)
    return [[a[i][j] * s[j] / s[i] for j in range(n)] for i in range(n)]


def _complex_solve(m, rhs):
    """Gaussian elimination with partial pivoting (complex)."""
    n = len(m)
    a = [list(row) + [rhs[i]] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) == 0:
            raise ValueError('singular system in frequency response')
        a[col], a[piv] = a[piv], a[col]
        for r in range(col + 1, n):
            factor = a[r][col] / a[col][col]
            if factor != 0:
                for c in range(col, n + 1):
                    a[r][c] -= factor * a[col][c]
    x = [0j] * n
    for r in range(n - 1, -1, -1):
        x[r] = (a[r][n] - sum(a[r][c] * x[c] for c in range(r + 1, n))) / a[r][r]
    return x


def _response(a, b, stand, freq_hz):
    """Physical state response z (complex) to unit disturbance at freq_hz."""
    n = len(a)
    s = _scales(stand, n)
    a_s = _scaled(a, s)
    b_s = [b[i] / s[i] for i in range(n)]
    jw = 2j * math.pi * freq_hz
    m = [[(jw if i == j else 0) - a_s[i][j] for j in range(n)] for i in range(n)]
    z = _complex_solve(m, b_s)
    return [z[i] * s[i] for i in range(n)]


def _complex_entry(prefix, value):
    return {prefix + '_per_unit_disturbance': abs(value),
            prefix + '_phase_rad': cmath.phase(value),
            prefix + '_real': value.real, prefix + '_imag': value.imag}


# ------------------------------------------------------------------ eigen helpers


def _eigs(a, stand):
    return eigenvalues(_scaled(a, _scales(stand, len(a))))


def _growth_and_dominant(eigs):
    scale = max(abs(z) for z in eigs)
    live = [z for z in eigs if abs(z) > _ZERO_MODE_RELATIVE * scale]
    zero = [z for z in eigs if abs(z) <= _ZERO_MODE_RELATIVE * scale]
    growth = max(z.real for z in live) if live else 0.0
    osc = [z for z in live if abs(z.imag) > 1e-9 * scale]
    dominant = max(osc, key=lambda z: (z.real, -abs(z.imag))) if osc else None
    return growth, dominant, zero


def _mode_list(eigs):
    modes = []
    for z in eigs:
        if z.imag < 0:
            continue
        mag = abs(z)
        modes.append({'real_per_s': z.real, 'imag_rad_s': z.imag,
                      'frequency_hz': z.imag / (2 * math.pi),
                      'damping_ratio': (-z.real / mag) if mag > 0 else 0.0})
    modes.sort(key=lambda m: (m['frequency_hz'], m['real_per_s']))
    return modes


def _critical_agc(stand, bite, spans, agc, lo, hi, points, beta, couple):
    """Same scan + bisection rule as chatter.critical_speed, on the 7-state matrix."""
    def growth_at(u):
        a = assemble_agc_state_matrix(stand, bite, spans, u, agc,
                                      bite_damping_transit_fraction=beta, couple_tension=couple)
        return _growth_and_dominant(_eigs(a, stand))

    speeds = [lo * (hi / lo) ** (i / (points - 1)) for i in range(points)]
    growth = [growth_at(u)[0] for u in speeds]
    out = {'bite_damping_transit_fraction': beta, 'critical_exit_speed_m_s': None,
           'onset_frequency_hz': None, 'onset_strip_pitch_m': None,
           'restabilises_within_scan': False}
    if growth[0] >= 0:
        out['status'] = 'UNSTABLE_AT_LOWEST_SCANNED_SPEED'
        return out
    idx = next((i for i, g in enumerate(growth) if g >= 0), None)
    if idx is None:
        out['status'] = 'STABLE_OVER_SCANNED_RANGE'
        return out
    a, b = speeds[idx - 1], speeds[idx]
    while b / a - 1 > 1e-6:
        mid = math.sqrt(a * b)
        if growth_at(mid)[0] >= 0:
            b = mid
        else:
            a = mid
    crit = 0.5 * (a + b)
    dominant = growth_at(b)[1]
    freq = abs(dominant.imag) / (2 * math.pi) if dominant is not None else None
    out.update(status='UNSTABLE_ABOVE_CRITICAL_SPEED', critical_exit_speed_m_s=crit,
               onset_frequency_hz=freq, onset_strip_pitch_m=(crit / freq) if freq else None,
               restabilises_within_scan=any(g < 0 for g in growth[idx:]))
    return out


# ------------------------------------------------------------------- AGC analyses


def _static_analytic(stand, bite, agc, disturbance, flow):
    """Coupling-off static exit-thickness transfer [D] (see module docstring)."""
    m, q, alpha = stand.mill_modulus_n_m, bite.strip_modulus_n_m, agc.compensation_gain
    den = m + (1 - alpha) * q
    if disturbance == 'work_backup_runout':
        return -2 * m / den
    if disturbance == 'entry_thickness':
        return (1 - alpha) * bite.dforce_dentry_thickness_n_m / den
    if disturbance == 'flow_stress':
        return (1 - alpha) * _flow_values(flow)[0] / den
    return 0.0


def agc_frequency_response(stand, bite, spans, exit_speed_m_s, agc, frequencies_hz, *,
                           disturbance='work_backup_runout', flow_sensitivity=None,
                           **options) -> dict:
    """Exit-thickness, tension and cylinder response per unit disturbance, AGC on and off.

    disturbance: 'work_backup_runout' [m], 'entry_thickness' [m], 'flow_stress' [Pa; needs
    ``flow_sensitivity``, a dict with dforce_dflow_stress_m2 and dslip_dflow_stress_per_pa]
    or 'roll_speed' [m/s of roll surface speed]. Each row holds, with AGC,
    exit_thickness_{per_unit_disturbance, phase_rad, real, imag}, entry_tension_*,
    exit_tension_*, cylinder_stroke_* (S = 2*x_s) and, without AGC (6-state chatter.py
    model), no_agc_exit_thickness_* , no_agc_entry_tension_*, no_agc_exit_tension_*, plus
    agc_to_no_agc_magnitude_ratio (None when the no-AGC response is zero).
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    _check_agc(agc)
    beta, couple = _options(**options)
    if disturbance not in AGC_DISTURBANCES:
        raise ValueError(f'disturbance must be one of {AGC_DISTURBANCES}')
    freqs = _check_frequencies(frequencies_hz)
    a7 = assemble_agc_state_matrix(stand, bite, spans, exit_speed_m_s, agc,
                                   bite_damping_transit_fraction=beta, couple_tension=couple)
    a6 = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                               bite_damping_transit_fraction=beta, couple_tension=couple)
    b7 = _input_vector(stand, bite, spans, exit_speed_m_s, disturbance, couple, flow_sensitivity,
                       n=len(a7))
    b6 = b7[:6]
    rows = []
    for f in freqs:
        z7, z6 = _response(a7, b7, stand, f), _response(a6, b6, stand, f)
        row = {'frequency_hz': f}
        row.update(_complex_entry('exit_thickness', 2 * z7[0]))
        row.update(_complex_entry('entry_tension', z7[4]))
        row.update(_complex_entry('exit_tension', z7[5]))
        row.update(_complex_entry('cylinder_stroke', 2 * z7[6]))
        row.update(_complex_entry('no_agc_exit_thickness', 2 * z6[0]))
        row.update(_complex_entry('no_agc_entry_tension', z6[4]))
        row.update(_complex_entry('no_agc_exit_tension', z6[5]))
        ref = abs(2 * z6[0])
        row['agc_to_no_agc_magnitude_ratio'] = abs(2 * z7[0]) / ref if ref > 0 else None
        rows.append(row)
    result = _base_result()
    result['flags'].extend(bite.flags)
    result['flags'].extend(_agc_flags(agc))
    if disturbance == 'roll_speed' and not couple:
        result['flags'].append('NO_ROLL_SPEED_PATH_WITH_TENSION_COUPLING_OFF')
    m, q, alpha = stand.mill_modulus_n_m, bite.strip_modulus_n_m, agc.compensation_gain
    result.update(
        disturbance=disturbance, disturbance_unit=DISTURBANCE_UNITS[disturbance],
        exit_speed_m_s=float(exit_speed_m_s), bite_damping_transit_fraction=beta,
        couple_tension=couple, agc=agc.to_dict(), state_names=list(agc.state_names),
        mill_modulus_n_m=m, strip_modulus_n_m=q, responses=rows,
        analytic_static_exit_thickness_per_unit_disturbance_tension_off=_static_analytic(
            stand, bite, agc, disturbance, flow_sensitivity),
        analytic_static_exit_thickness_per_unit_disturbance_tension_off_no_agc=_static_analytic(
            stand, bite, GaugemeterAGC(0.0, agc.bandwidth_hz), disturbance, flow_sensitivity),
        eccentricity_amplification_vs_no_agc=(m + q) / (m + (1 - alpha) * q),
        bite_source=bite.source)
    result['limitations'].append(
        'analytic_static_* values assume constant tension (coupling off); with coupling on '
        'the constant-speed spans drive the DC gauge response to the mass-flow limit.')
    return result


def agc_stability(stand, bite, spans, exit_speed_m_s, agc, *, speed_range_m_s=(0.05, 60.0),
                  **options) -> dict:
    """Eigen-analysis of the 7-state AGC system and the change in chatter critical speed.

    Keys: modes, max_growth_rate_per_s, stable, dominant_frequency_hz,
    dominant_growth_rate_per_s, cylinder_mode_real_per_s (least-damped real eigenvalue
    with |lambda| < 3*omega_c, if any), no_agc_max_growth_rate_per_s,
    critical_speed_with_agc / critical_speed_without_agc (each: status,
    critical_exit_speed_m_s, onset_frequency_hz, onset_strip_pitch_m,
    restabilises_within_scan, bite_damping_transit_fraction, and without_bite_damping when
    beta != 0), critical_speed_relative_change (with/without - 1, or None).
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    _check_agc(agc)
    beta, couple = _options(**options)
    if (not isinstance(speed_range_m_s, (tuple, list)) or len(speed_range_m_s) != 2
            or not all(_finite(v) and v > 0 for v in speed_range_m_s)
            or not speed_range_m_s[0] < speed_range_m_s[1]):
        raise ValueError('speed_range_m_s must be (low, high) with 0 < low < high')
    lo, hi = float(speed_range_m_s[0]), float(speed_range_m_s[1])
    a7 = assemble_agc_state_matrix(stand, bite, spans, exit_speed_m_s, agc,
                                   bite_damping_transit_fraction=beta, couple_tension=couple)
    eigs = _eigs(a7, stand)
    growth, dominant, zero = _growth_and_dominant(eigs)
    a6 = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                               bite_damping_transit_fraction=beta, couple_tension=couple)
    growth6 = _growth_and_dominant(_eigs(a6, stand))[0]
    wc = agc.omega_c_rad_s
    slow_real = [z.real for z in eigs if abs(z.imag) <= 1e-9 * max(abs(w) for w in eigs)
                 and 0 < abs(z) < 3 * wc]
    points = max(80, int(math.ceil(20 * math.log10(hi / lo))) + 1)
    with_agc = _critical_agc(stand, bite, spans, agc, lo, hi, points, beta, couple)
    if beta != 0:
        with_agc['without_bite_damping'] = _critical_agc(stand, bite, spans, agc, lo, hi,
                                                         points, 0.0, couple)
    base = critical_speed(stand, bite, spans, speed_range_m_s=(lo, hi),
                          bite_damping_transit_fraction=beta, couple_tension=couple)
    keys = ('status', 'critical_exit_speed_m_s', 'onset_frequency_hz', 'onset_strip_pitch_m',
            'restabilises_within_scan', 'bite_damping_transit_fraction')
    without_agc = {k: base[k] for k in keys}
    if 'without_bite_damping' in base:
        without_agc['without_bite_damping'] = {k: base['without_bite_damping'][k] for k in keys}

    def rel(w, wo):
        cw, co = w['critical_exit_speed_m_s'], wo['critical_exit_speed_m_s']
        return (cw / co - 1) if (cw is not None and co) else None

    result = _base_result()
    result['flags'].extend(bite.flags)
    result['flags'].extend(_agc_flags(agc))
    if zero:
        result['flags'].append('NEUTRAL_ZERO_MODE_EXCLUDED_FROM_GROWTH_RATE')
        result['limitations'].append(
            f'{len(zero)} neutral (zero) eigenvalue(s) are excluded from max_growth_rate_per_s '
            '(uncoupled tension states, or alpha = 1 with tension coupling on).')
    change = rel(with_agc, without_agc)
    if with_agc['status'] == 'UNSTABLE_AT_LOWEST_SCANNED_SPEED' or (
            beta != 0 and with_agc['without_bite_damping']['status'] ==
            'UNSTABLE_AT_LOWEST_SCANNED_SPEED'):
        result['flags'].append('AGC_SYSTEM_UNSTABLE_AT_LOWEST_SCANNED_SPEED')
    if change is not None and change < -0.05:
        result['flags'].append('AGC_LOWERS_CHATTER_CRITICAL_SPEED_BY_MORE_THAN_5_PERCENT')
    result['limitations'].append(
        'A first-order cylinder position loop has a -90 degree lag well above its bandwidth; '
        'acting on the backup-roll anchor this is NEGATIVE damping of the loaded stand mode '
        '(about alpha*K_h^2*omega_c/(2*M*omega^2) in the simple limit) and can lower the '
        'critical speed. A real loop rolls off faster (valve, oil column, force filtering); '
        'use force_filter_hz to see how strongly the number depends on that roll-off.')
    dom_hz = abs(dominant.imag) / (2 * math.pi) if dominant is not None else None
    result.update(
        exit_speed_m_s=float(exit_speed_m_s), bite_damping_transit_fraction=beta,
        couple_tension=couple, agc=agc.to_dict(), state_names=list(agc.state_names),
        modes=_mode_list(eigs), max_growth_rate_per_s=growth, stable=growth < 0,
        dominant_frequency_hz=dom_hz,
        dominant_growth_rate_per_s=dominant.real if dominant is not None else None,
        cylinder_mode_real_per_s=max(slow_real) if slow_real else None,
        no_agc_max_growth_rate_per_s=growth6,
        speed_range_m_s=[lo, hi], scan_points=points,
        critical_speed_with_agc=with_agc, critical_speed_without_agc=without_agc,
        critical_speed_relative_change=change,
        bite_source=bite.source)
    if beta != 0:
        result['critical_speed_relative_change_without_bite_damping'] = rel(
            with_agc['without_bite_damping'], without_agc['without_bite_damping'])
    return result


# ------------------------------------------------------- bite input sensitivities


def _central_bite(bite_pass, field, relative_step, derive_options):
    if not isinstance(bite_pass, BitePass):
        raise ValueError('bite_pass must be a BitePass')
    bite_pass.validate()
    if not _finite(relative_step) or not 1e-4 <= relative_step <= 0.1:
        raise ValueError('relative_step must be finite in [1e-4, 0.1]')
    nominal = getattr(bite_pass, field)
    step = relative_step * nominal
    plus = derive_bite_response(replace(bite_pass, **{field: nominal + step}), **derive_options)
    minus = derive_bite_response(replace(bite_pass, **{field: nominal - step}), **derive_options)
    flags = []
    for f in plus.flags + minus.flags:
        if f not in flags:
            flags.append(f)
    return {
        'dforce': (plus.separating_force_n - minus.separating_force_n) / (2 * step),
        'dslip': (plus.forward_slip_fraction - minus.forward_slip_fraction) / (2 * step),
        'step': step, 'plus': plus, 'minus': minus, 'flags': flags}


def flow_stress_sensitivity(bite_pass, *, relative_step=0.005, **derive_options) -> dict:
    """dF/dY [m^2] and df/dY [1/Pa] by central differences of derive_bite_response (+-0.5 %).

    Keys: dforce_dflow_stress_m2, dslip_dflow_stress_per_pa, flow_stress_step_pa,
    mean_flow_stress_pa, mean_separating_force_n, force_per_flow_stress_m2 (F/Y, for
    comparison: dF/dY > F/Y because flattening grows with load), flags, basis.
    """
    d = _central_bite(bite_pass, 'mean_flow_stress_pa', relative_step, derive_options)
    mean_force = 0.5 * (d['plus'].separating_force_n + d['minus'].separating_force_n)
    result = _base_result(('Rate sensitivity of the flow stress is taken as zero.',))
    result['flags'].extend(d['flags'])
    result['basis']['flow_stress_sensitivity'] = ('[D] central difference of '
                                                  'chatter.derive_bite_response')
    result['basis']['hardness_variation'] = ('[V] ~2 % cyclic, decoiler-synchronous (ABB '
                                             '"Improvement of thickness tolerances")')
    result.update(dforce_dflow_stress_m2=d['dforce'], dslip_dflow_stress_per_pa=d['dslip'],
                  flow_stress_step_pa=d['step'], relative_step=float(relative_step),
                  mean_flow_stress_pa=float(bite_pass.mean_flow_stress_pa),
                  mean_separating_force_n=mean_force,
                  force_per_flow_stress_m2=mean_force / bite_pass.mean_flow_stress_pa)
    return result


def friction_force_sensitivity(bite_pass, *, relative_step=0.02, **derive_options) -> dict:
    """dF/dmu [N] and df/dmu by central differences of derive_bite_response (+-2 %).

    Keys: dforce_dfriction_n, dslip_dfriction, friction_step, friction_coefficient,
    mean_separating_force_n, flags, basis.
    """
    d = _central_bite(bite_pass, 'friction_coefficient', relative_step, derive_options)
    result = _base_result()
    result['flags'].extend(d['flags'])
    result['basis']['friction_force_sensitivity'] = ('[D] central difference of '
                                                     'chatter.derive_bite_response')
    result.update(dforce_dfriction_n=d['dforce'], dslip_dfriction=d['dslip'],
                  friction_step=d['step'], relative_step=float(relative_step),
                  friction_coefficient=float(bite_pass.friction_coefficient),
                  mean_separating_force_n=0.5 * (d['plus'].separating_force_n +
                                                 d['minus'].separating_force_n))
    return result


def _static_shift(force_change_n, mill_modulus_n_m, strip_stiffness_n_m, compensation_gain):
    for name, value in (('mill_modulus_n_m', mill_modulus_n_m),
                        ('strip_stiffness_n_m', strip_stiffness_n_m)):
        if not _finite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number')
    if not _finite(compensation_gain) or not 0 <= compensation_gain <= 1:
        raise ValueError('compensation_gain must be finite in [0, 1]')
    m, q, a = mill_modulus_n_m, strip_stiffness_n_m, compensation_gain
    dh = (1 - a) * force_change_n / (m + (1 - a) * q)
    dh0 = force_change_n / (m + q)
    return {'exit_thickness_change_m': dh,
            'exit_thickness_change_without_agc_m': dh0,
            'separating_force_change_n': force_change_n - q * dh,
            'cylinder_stroke_change_m': -a * (force_change_n - q * dh) / m,
            'force_change_at_fixed_gap_n': force_change_n,
            'mill_modulus_n_m': float(m), 'strip_stiffness_n_m': float(q),
            'compensation_gain': float(a)}


def speed_change_gauge_shift(dforce_dfriction_n, delta_friction, mill_modulus_n_m,
                             strip_stiffness_n_m, compensation_gain=0.0) -> dict:
    """Quasi-static exit-gauge shift when friction changes with speed [D].

    dh = (1-alpha)*dF0/(M + (1-alpha)*Q), dF0 = dF/dmu*dmu. Constant tension assumed.
    Keys: exit_thickness_change_m, exit_thickness_change_without_agc_m,
    separating_force_change_n, cylinder_stroke_change_m, force_change_at_fixed_gap_n,
    mill_modulus_n_m, strip_stiffness_n_m, compensation_gain, delta_friction.
    """
    if not _finite(dforce_dfriction_n) or not _finite(delta_friction):
        raise ValueError('dforce_dfriction_n and delta_friction must be finite numbers')
    result = _base_result(('Linear in the friction change; large changes need a re-derived '
                           'bite.', 'Constant tension (tension regulators) assumed.'))
    result['basis']['speed_change_gauge_shift'] = ('[D] dh = (1-alpha)*dF0/(M+(1-alpha)*Q); '
                                                   '[V context] Zhang et al. 2017 IJCA 10(6)')
    result.update(_static_shift(dforce_dfriction_n * delta_friction, mill_modulus_n_m,
                                strip_stiffness_n_m, compensation_gain))
    result['delta_friction'] = float(delta_friction)
    return result


def hardness_gauge_shift(dforce_dflow_stress_m2, delta_flow_stress_pa, mill_modulus_n_m,
                         strip_stiffness_n_m, compensation_gain=0.0) -> dict:
    """Quasi-static exit-gauge change for a flow-stress change [D] (same keys as
    speed_change_gauge_shift, with delta_flow_stress_pa instead of delta_friction)."""
    if not _finite(dforce_dflow_stress_m2) or not _finite(delta_flow_stress_pa):
        raise ValueError('dforce_dflow_stress_m2 and delta_flow_stress_pa must be finite')
    result = _base_result(('Constant tension (tension regulators) assumed.',))
    result['basis']['hardness_gauge_shift'] = '[D] dh = (1-alpha)*dF0/(M+(1-alpha)*Q)'
    result.update(_static_shift(dforce_dflow_stress_m2 * delta_flow_stress_pa,
                                mill_modulus_n_m, strip_stiffness_n_m, compensation_gain))
    result['delta_flow_stress_pa'] = float(delta_flow_stress_pa)
    return result


def coil_synchronous_frequencies(entry_speed_m_s, coil_diameter_m, harmonics=3, *,
                                 entry_thickness_m=None, exit_thickness_m=None) -> dict:
    """Decoiler-synchronous disturbance frequencies n*u_e/(pi*D) and exit-strip pitches.

    Keys: decoiler_rotation_hz, harmonics [{order, frequency_hz,
    exit_strip_pitch_m (None unless both thicknesses are given)}].
    """
    for name, value in (('entry_speed_m_s', entry_speed_m_s),
                        ('coil_diameter_m', coil_diameter_m)):
        if not _finite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number')
    if isinstance(harmonics, bool) or not isinstance(harmonics, int) or not 1 <= harmonics <= 20:
        raise ValueError('harmonics must be an integer in [1, 20]')
    pitch_base = None
    if entry_thickness_m is not None or exit_thickness_m is not None:
        if not (_finite(entry_thickness_m) and _finite(exit_thickness_m)
                and 0 < exit_thickness_m < entry_thickness_m):
            raise ValueError('entry_thickness_m and exit_thickness_m must both be given, '
                             'finite, with 0 < exit < entry')
        pitch_base = math.pi * coil_diameter_m * entry_thickness_m / exit_thickness_m
    f1 = entry_speed_m_s / (math.pi * coil_diameter_m)
    result = _base_result(('The coil diameter shrinks as the coil unwinds, so the frequency '
                           'rises through the coil; evaluate at the diameter of interest.',))
    result['basis']['coil_synchronous'] = ('[V] decoiler-synchronous hardness sector (ABB); '
                                           '[D] f = n*u_e/(pi*D), pitch = pi*D*h0/(h1*n)')
    result.update(entry_speed_m_s=float(entry_speed_m_s), coil_diameter_m=float(coil_diameter_m),
                  decoiler_rotation_hz=f1,
                  harmonics=[{'order': n, 'frequency_hz': n * f1,
                              'exit_strip_pitch_m': (pitch_base / n) if pitch_base else None}
                             for n in range(1, harmonics + 1)])
    return result


# ----------------------------------------------------------------- drive train


def _jacobi(a):
    """Eigenvalues/vectors of a small real symmetric matrix by cyclic Jacobi rotations."""
    n = len(a)
    a = [list(r) for r in a]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        diag = sum(a[i][i] ** 2 for i in range(n))
        if off <= 1e-30 * diag:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if a[p][q] == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    else:
        raise ValueError('Jacobi eigen-iteration did not converge')
    return [a[i][i] for i in range(n)], [[v[k][i] for k in range(n)] for i in range(n)]


def torsional_modes(inertias_kg_m2, stiffnesses_n_m_rad) -> dict:
    """Free-free torsional chain (2-5 inertias, shaft i joins inertia i and i+1).

    Keys: frequencies_hz (ascending, rigid-body 0 first), elastic_frequencies_hz,
    mode_shapes (one list per frequency, max |component| = 1, largest component positive),
    rigid_body_mode_present, first_elastic_frequency_hz.
    """
    if not isinstance(inertias_kg_m2, (list, tuple)) or not 2 <= len(inertias_kg_m2) <= 5:
        raise ValueError('inertias_kg_m2 must be a list of 2-5 inertias')
    if (not isinstance(stiffnesses_n_m_rad, (list, tuple))
            or len(stiffnesses_n_m_rad) != len(inertias_kg_m2) - 1):
        raise ValueError('stiffnesses_n_m_rad must have one entry fewer than inertias_kg_m2')
    for value in list(inertias_kg_m2) + list(stiffnesses_n_m_rad):
        if not _finite(value) or value <= 0:
            raise ValueError('inertias and stiffnesses must be finite positive numbers')
    j = [float(v) for v in inertias_kg_m2]
    k = [float(v) for v in stiffnesses_n_m_rad]
    n = len(j)
    kmat = [[0.0] * n for _ in range(n)]
    for i, ks in enumerate(k):
        kmat[i][i] += ks
        kmat[i + 1][i + 1] += ks
        kmat[i][i + 1] -= ks
        kmat[i + 1][i] -= ks
    r = [1 / math.sqrt(v) for v in j]
    d = [[kmat[a][b] * r[a] * r[b] for b in range(n)] for a in range(n)]
    lam, vecs = _jacobi(d)
    order = sorted(range(n), key=lambda i: lam[i])
    lam_max = max(abs(v) for v in lam)
    freqs, shapes = [], []
    rigid = False
    for i in order:
        w2 = lam[i]
        if abs(w2) <= 1e-9 * lam_max:
            w2, rigid = 0.0, True
        freqs.append(math.sqrt(max(w2, 0.0)) / (2 * math.pi))
        phi = [vecs[i][a] * r[a] for a in range(n)]
        big = max(phi, key=abs)
        shapes.append([p / big for p in phi])
    result = _base_result(('Free-free undamped chain; no motor control loop, backlash or '
                           'coupling to the vertical stack.',))
    result['basis']['torsional'] = ('[D] J^-1/2 K J^-1/2 Jacobi; benchmark [V] J. Phys. Conf. '
                                    'Ser. 2419 (2022) 012027; first mode 10-20 Hz [V] Gao et al.')
    elastic = [f for f in freqs if f > 0]
    if elastic and not 10 <= elastic[0] <= 20:
        result['flags'].append('FIRST_TORSIONAL_MODE_OUTSIDE_10_20_HZ_GUIDANCE')
    result.update(inertias_kg_m2=j, stiffnesses_n_m_rad=k, frequencies_hz=freqs,
                  elastic_frequencies_hz=elastic, mode_shapes=shapes,
                  rigid_body_mode_present=rigid,
                  first_elastic_frequency_hz=elastic[0] if elastic else None)
    return result


def reel_inertia_kg_m2(motor_inertia_kg_m2, strip_density_kg_m3, width_m, coil_radius_m,
                       mandrel_radius_m, gear_ratio) -> float:
    """Reel inertia reflected to the motor shaft [kg m^2] [V: Soler, Isermann & Feldmann 2008]:
    J_motor + pi*rho*W*(R^4 - R_m^4)/(2*N^2), N = motor speed / reel speed."""
    for name, value in (('motor_inertia_kg_m2', motor_inertia_kg_m2),
                        ('strip_density_kg_m3', strip_density_kg_m3), ('width_m', width_m),
                        ('coil_radius_m', coil_radius_m), ('mandrel_radius_m', mandrel_radius_m),
                        ('gear_ratio', gear_ratio)):
        if not _finite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number')
    if coil_radius_m < mandrel_radius_m:
        raise ValueError('coil_radius_m must be >= mandrel_radius_m')
    return motor_inertia_kg_m2 + (math.pi * strip_density_kg_m3 * width_m *
                                  (coil_radius_m ** 4 - mandrel_radius_m ** 4) /
                                  (2 * gear_ratio ** 2))


def _roll_speed_dc(bite, exit_speed_m_s):
    """Coupling-on DC tensions per unit roll-speed change [D]; None if singular."""
    f = bite.forward_slip_fraction
    vr = exit_speed_m_s / (1 + f)
    a11, a12 = bite.dforce_dentry_tension_m2, bite.dforce_dexit_tension_m2
    a21, a22 = bite.dslip_dentry_tension_per_pa, bite.dslip_dexit_tension_per_pa
    det = a11 * a22 - a12 * a21
    if det == 0 or abs(det) <= 1e-12 * (abs(a11 * a22) + abs(a12 * a21)):
        return None
    rhs = -(1 + f) / vr
    return {'exit_thickness_per_m_s': 0.0,
            'entry_tension_pa_per_m_s': -a12 * rhs / det,
            'exit_tension_pa_per_m_s': a11 * rhs / det}


def roll_speed_ripple_response(stand, bite, spans, exit_speed_m_s, frequencies_hz, *,
                               agc=None, **options) -> dict:
    """Exit-thickness and entry/exit-tension response per unit roll-speed ripple [per m/s].

    Rows: frequency_hz, exit_thickness_{per_unit_disturbance, phase_rad, real, imag} [m per
    m/s], entry_tension_* and exit_tension_* [Pa per m/s], plus the same per unit RELATIVE
    speed ripple (exit_thickness_per_relative_speed_m = per-m/s value * V_r). With ``agc``
    the 7-state model is used. analytic_dc_limit (coupling on, alpha < 1) [D]: dh = 0 and
    tensions from F_se*s_e + F_sx*s_x = 0, f_se*s_e + f_sx*s_x = -(1+f)*dV_r/V_r.
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    beta, couple = _options(**options)
    freqs = _check_frequencies(frequencies_hz)
    if agc is None:
        a = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                                  bite_damping_transit_fraction=beta, couple_tension=couple)
    else:
        a = assemble_agc_state_matrix(stand, bite, spans, exit_speed_m_s, agc,
                                      bite_damping_transit_fraction=beta, couple_tension=couple)
    n = len(a)
    b = _input_vector(stand, bite, spans, exit_speed_m_s, 'roll_speed', couple, n=n)
    vr = exit_speed_m_s / (1 + bite.forward_slip_fraction)
    rows = []
    for f in freqs:
        z = _response(a, b, stand, f)
        row = {'frequency_hz': f}
        row.update(_complex_entry('exit_thickness', 2 * z[0]))
        row.update(_complex_entry('entry_tension', z[4]))
        row.update(_complex_entry('exit_tension', z[5]))
        row['exit_thickness_per_relative_speed_m'] = abs(2 * z[0]) * vr
        rows.append(row)
    result = _base_result(('Roll-speed ripple enters only through strip continuity; the slab '
                           'force and slip are rate independent and the bite-damping transit '
                           'time is not modulated.',))
    result['flags'].extend(bite.flags)
    if agc is not None:
        _check_agc(agc)
        result['flags'].extend(_agc_flags(agc))
    if not couple:
        result['flags'].append('NO_ROLL_SPEED_PATH_WITH_TENSION_COUPLING_OFF')
    dc = None
    if couple and (agc is None or agc.compensation_gain < 1):
        dc = _roll_speed_dc(bite, exit_speed_m_s)
    result['basis']['roll_speed_ripple'] = ('[D] du_x = (1+f)*dV_r, du_e = (1+f)*(h1/h0)*dV_r '
                                            'from chatter.py continuity')
    result.update(exit_speed_m_s=float(exit_speed_m_s), roll_surface_speed_m_s=vr,
                  bite_damping_transit_fraction=beta, couple_tension=couple,
                  agc=agc.to_dict() if agc is not None else None,
                  disturbance_unit='m/s', responses=rows, analytic_dc_limit=dc)
    return result
