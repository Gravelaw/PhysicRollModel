"""Linear third-octave gauge-chatter screen for one four-high stand (SI, stdlib only).

Status: ``UNVALIDATED_LINEAR_CHATTER_SCREEN``. Software-verified against closed-form
benchmarks only; no plant data, no calibrated parameters, no probability of any cause.

Sign conventions
----------------
x_w, x_b   upper work / backup roll displacement, positive AWAY from the pass line. The
           lower half stack is the mirror image (symmetric mode), so the roll-gap and the
           exit-thickness perturbation are dh = 2*x_w (no elastic strip recovery).
dF         perturbation of the total separating force, positive pushes the rolls apart.
sigma_e/x  entry / exit strip TENSILE stress perturbations [Pa].
u_e, u_x   strip entry / exit speed; V_r roll surface speed (held constant: the drive
           inertia is large at chatter frequency); forward slip f = u_x/V_r - 1.

Structure (one half stack, symmetric about the pass line)
---------------------------------------------------------
    M_w*x_w'' = -K_wb*(x_w - x_b) - C_wb*(x_w' - x_b') + dF
    M_b*x_b'' = +K_wb*(x_w - x_b) + C_wb*(x_w' - x_b') - K_h*x_b - C_h*x_b'
Static mill modulus (force per unit gap opening) K_mill = 1/(2*(1/K_wb + 1/K_h)).

Linearised roll bite
--------------------
    dF = F_h*dh + F_hdot*dh' + F_se*sigma_e + F_sx*sigma_x + F_hin*dh_in
    df = f_h*dh + f_se*sigma_e + f_sx*sigma_x + f_hin*dh_in
Strip modulus Q_s = -F_h > 0. Bite damping closure (declared heuristic, unvalidated; it
scales as 1/speed as reported by Hu, Zhao & Ehmann 2006, doi:10.1243/09544054B06804, as
reproduced by Heidari & Forouzan 2013, and by Kimura et al. 2003, ISIJ Int. 43:77):
F_hdot = F_h*beta*l_d/u_x, beta = ``bite_damping_transit_fraction`` (0 disables it). Results
are reported for the supplied beta and for beta = 0, because a large part of the stability
margin can rest on this closure.

Strip kinematics and tension (lumped elastic spans, constant-speed far ends)
---------------------------------------------------------------------------
    u_x = V_r*(1+f),  u_e = u_x*h1/h0
    du_x = V_r*df
    du_e = V_r*[(h1/h0)*df + ((1+f)/h0)*dh - ((1+f)*h1/h0**2)*dh_in]
    sigma_e' = +(E/L_e)*du_e,   sigma_x' = -(E/L_x)*du_x
State vector z = [x_w, x_w', x_b, x_b', sigma_e, sigma_x] (``STATE_NAMES``),
z' = A z + B_k d_k(t).

Feedback mechanism: the gap opens -> more strip is drawn into the bite -> the entry tension
rises as the INTEGRAL of the gap opening (90 degrees lag) -> the separating force drops ->
the force component in phase with the gap velocity does positive work on the stack, i.e.
negative damping whose size grows with speed (Tlusty et al. 1982, CIRP Ann. 31:195;
Yun, Wilson & Ehmann 1998; Niroomand et al. 2012, ISIJ Int. 52:2245).

Single-DOF benchmark (unit-tested): M*h'' + (C+D)*h' + (K+Q_s)*h = -N*sigma,
sigma' = (E/L)*(u_x/h0)*h gives M s^3 + (C+D) s^2 + (K+Q_s) s + N*E*u_x/(L*h0) = 0 and,
by Routh-Hurwitz with D = 0, u_crit = C*(K+Q_s)*L*h0/(M*N*E) at omega = sqrt((K+Q_s)/M).

Bite sensitivities may be derived from the repository's projected slab model
(``physicroll.slab._solve_grid``) with circular Hitchcock flattening by damped fixed point
(as ``physicroll/contact.py``), by central finite differences, or SUPPLIED by the caller.

NOT modelled: drive/torsional dynamics, roll-stack bending and cross-width variation,
non-circular (foil) contact, sticking, elastic strip recovery, strip inertia and axial
wave propagation in the spans (the lumped span is inaccurate near c/(2L), ~640 Hz for a
4 m aluminium span), lubricant film dynamics, hydraulic gap-control loops, limit cycles
and strip breaks (the model is linear), and thermal effects. The friction and tension
effects on chatter are disputed in the literature (Yarita: high friction; Chefneux: low
friction; Kimura: an optimum band; Heidari: little tension effect; Zeng, Zang & Gao 2016,
doi:10.1155/2016/2347386: higher tension lowers the critical speed).
"""
from dataclasses import asdict, dataclass, fields
import cmath
import math

from .model import Scenario
from .slab import _solve_grid

STATUS = 'UNVALIDATED_LINEAR_CHATTER_SCREEN'
STATE_NAMES = ('x_w_m', 'v_w_m_s', 'x_b_m', 'v_b_m_s', 'sigma_entry_pa', 'sigma_exit_pa')
DISTURBANCES = ('work_backup_runout', 'entry_thickness')

_REFERENCE_LENGTH_M = 1e-6
_REFERENCE_STRESS_PA = 1e6
_ZERO_MODE_RELATIVE = 1e-9
_LIMITATIONS = (
    'Linear small-perturbation screen: it cannot predict limit-cycle amplitude or strip break.',
    'Synthetic, uncalibrated structural and bite parameters; no plant validation is claimed.',
    'Bite damping is a declared transit-time heuristic; results without it are also reported.',
    'Lumped strip spans: inaccurate near the axial wave resonance of the span (c/(2L)).',
    'Symmetric (gap-changing) mode only; no roll bending, cross-width or drive dynamics.',
)


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _require_positive(obj, names):
    for name in names:
        value = getattr(obj, name)
        if not _finite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number in SI units')


def _require_nonnegative(obj, names):
    for name in names:
        value = getattr(obj, name)
        if not _finite(value) or value < 0:
            raise ValueError(f'{name} must be a finite nonnegative number in SI units')


def _options(bite_damping_transit_fraction=0.5, couple_tension=True):
    if not _finite(bite_damping_transit_fraction) or not 0 <= bite_damping_transit_fraction <= 5:
        raise ValueError('bite_damping_transit_fraction must be finite in [0, 5]')
    if not isinstance(couple_tension, bool):
        raise ValueError('couple_tension must be a bool')
    return float(bite_damping_transit_fraction), couple_tension


def _base_result():
    return {'status': STATUS, 'flags': [], 'limitations': list(_LIMITATIONS)}


# ----------------------------------------------------------------------------- inputs


@dataclass(frozen=True)
class BitePass:
    """Nominal pass (SI). Thicknesses are full thickness; tensions are tensile stresses."""
    entry_thickness_m: float
    exit_thickness_m: float
    width_m: float
    work_roll_radius_m: float
    mean_flow_stress_pa: float
    friction_coefficient: float
    entry_tension_pa: float
    exit_tension_pa: float

    def validate(self):
        _require_positive(self, ('entry_thickness_m', 'exit_thickness_m', 'width_m',
                                 'work_roll_radius_m', 'mean_flow_stress_pa',
                                 'friction_coefficient'))
        _require_nonnegative(self, ('entry_tension_pa', 'exit_tension_pa'))
        h0, h1 = self.entry_thickness_m, self.exit_thickness_m
        if not 2e-5 <= h1 < h0:
            raise ValueError('chatter bite domain requires 2e-5 m <= exit thickness < entry')
        if not 0.02 <= (h0 - h1) / h0 <= 0.5:
            raise ValueError('chatter bite domain requires reduction in [0.02, 0.5]')
        if h0 / self.work_roll_radius_m > 0.05 or self.width_m / h0 < 20:
            raise ValueError('requires thin, wide strip: h0/R <= 0.05 and width/h0 >= 20')
        if self.friction_coefficient > 0.3:
            raise ValueError('requires 0 < friction coefficient <= 0.3')
        if max(self.entry_tension_pa, self.exit_tension_pa) >= self.mean_flow_stress_pa:
            raise ValueError('tensions must stay below the mean flow stress')


@dataclass(frozen=True)
class BiteResponse:
    """Nominal bite state and linear sensitivities (see module docstring for symbols)."""
    separating_force_n: float
    forward_slip_fraction: float
    contact_length_m: float
    contact_radius_ratio: float
    entry_thickness_m: float
    exit_thickness_m: float
    dforce_dexit_thickness_n_m: float       # F_h (< 0); strip modulus Q_s = -F_h
    dforce_dentry_thickness_n_m: float      # F_hin
    dforce_dentry_tension_m2: float         # F_se (< 0 expected)
    dforce_dexit_tension_m2: float          # F_sx (< 0 expected)
    dslip_dexit_thickness_per_m: float      # f_h
    dslip_dentry_thickness_per_m: float     # f_hin
    dslip_dentry_tension_per_pa: float      # f_se
    dslip_dexit_tension_per_pa: float       # f_sx
    source: str
    flags: tuple = ()

    def validate(self):
        if self.source not in ('derived_slab_hitchcock', 'supplied'):
            raise ValueError("source must be 'derived_slab_hitchcock' or 'supplied'")
        if not isinstance(self.flags, tuple) or not all(isinstance(f, str) for f in self.flags):
            raise ValueError('flags must be a tuple of strings')
        for f in fields(self):
            if f.name in ('source', 'flags'):
                continue
            if not _finite(getattr(self, f.name)):
                raise ValueError(f'{f.name} must be a finite number in SI units')
        _require_positive(self, ('separating_force_n', 'contact_length_m', 'entry_thickness_m',
                                 'exit_thickness_m'))
        if self.exit_thickness_m >= self.entry_thickness_m:
            raise ValueError('exit thickness must be below entry thickness')
        if self.contact_radius_ratio < 1:
            raise ValueError('contact_radius_ratio (R_contact/R) must be >= 1')
        if not -0.5 < self.forward_slip_fraction < 1:
            raise ValueError('forward_slip_fraction outside (-0.5, 1)')
        if self.dforce_dexit_thickness_n_m >= 0:
            raise ValueError('dforce_dexit_thickness_n_m (F_h) must be negative: the strip '
                             'modulus Q_s = -F_h must be positive')

    @property
    def strip_modulus_n_m(self):
        return -self.dforce_dexit_thickness_n_m

    def to_dict(self):
        data = asdict(self)
        data['flags'] = list(self.flags)
        data['strip_modulus_n_m'] = self.strip_modulus_n_m
        return data


@dataclass(frozen=True)
class StandModel:
    """One half stack: work roll on backup roll on housing (all lumped)."""
    work_roll_mass_kg: float
    backup_roll_mass_kg: float
    work_backup_contact_stiffness_n_m: float
    housing_stiffness_n_m: float
    work_backup_damping_n_s_m: float
    housing_damping_n_s_m: float

    @classmethod
    def from_modal_damping(cls, work_roll_mass_kg, backup_roll_mass_kg,
                           work_backup_contact_stiffness_n_m, housing_stiffness_n_m,
                           damping_ratio):
        """C_h = 2*zeta*sqrt(K_h*(M_w+M_b)), C_wb = 2*zeta*sqrt(K_wb*M_w)."""
        if not _finite(damping_ratio) or not 0 <= damping_ratio < 1:
            raise ValueError('damping_ratio must be finite in [0, 1)')
        for value in (work_roll_mass_kg, backup_roll_mass_kg,
                      work_backup_contact_stiffness_n_m, housing_stiffness_n_m):
            if not _finite(value) or value <= 0:
                raise ValueError('masses and stiffnesses must be finite positive numbers')
        c_h = 2 * damping_ratio * math.sqrt(housing_stiffness_n_m *
                                            (work_roll_mass_kg + backup_roll_mass_kg))
        c_wb = 2 * damping_ratio * math.sqrt(work_backup_contact_stiffness_n_m *
                                             work_roll_mass_kg)
        stand = cls(work_roll_mass_kg, backup_roll_mass_kg, work_backup_contact_stiffness_n_m,
                    housing_stiffness_n_m, c_wb, c_h)
        stand.validate()
        return stand

    @property
    def mill_modulus_n_m(self):
        self.validate()
        return 1 / (2 * (1 / self.work_backup_contact_stiffness_n_m +
                         1 / self.housing_stiffness_n_m))

    def validate(self):
        _require_positive(self, ('work_roll_mass_kg', 'backup_roll_mass_kg',
                                 'work_backup_contact_stiffness_n_m', 'housing_stiffness_n_m'))
        _require_nonnegative(self, ('work_backup_damping_n_s_m', 'housing_damping_n_s_m'))


@dataclass(frozen=True)
class StripSpans:
    """Lumped elastic strip spans between the bite and the next velocity node."""
    youngs_modulus_pa: float
    entry_span_length_m: float
    exit_span_length_m: float

    def validate(self):
        _require_positive(self, ('youngs_modulus_pa', 'entry_span_length_m',
                                 'exit_span_length_m'))


# ------------------------------------------------------------------ bite derivation


def _converged_bite(p, exit_m, entry_m, se, sx, cells, compliance, max_ratio):
    """Slab + Hitchcock fixed point. Returns (slab result dict, contact radius ratio)."""
    s = Scenario('chatter_bite', True, entry_m, exit_m, p.width_m, 1.0, p.work_roll_radius_m,
                 2700.0, p.mean_flow_stress_pa, p.friction_coefficient, se, sx, 1.0)
    big_r = p.work_roll_radius_m
    radius = big_r
    draft = entry_m - exit_m
    for _ in range(300):
        try:
            result = _solve_grid(s, cells, 'established', None, radius)
        except ValueError:
            raise
        except (ArithmeticError, TypeError) as exc:
            raise ValueError(f'slab evaluation failed: {exc}') from exc
        target = big_r * (1 + compliance * result['separating_force_n'] / (p.width_m * draft))
        if abs(target - radius) / big_r <= 1e-10:
            ratio = radius / big_r
            if ratio > max_ratio:
                raise ValueError(
                    f'Hitchcock contact radius ratio {ratio:.3f} exceeds max_radius_ratio '
                    f'{max_ratio}: circular flattening is outside its envelope; a foil '
                    '(non-circular) contact model or supplied sensitivities are needed')
            return result, ratio
        if target / big_r > 10:
            raise ValueError('Hitchcock fixed point diverging (R\'/R > 10): circular flattening '
                             'is outside its envelope; a foil (non-circular) contact model or '
                             'supplied sensitivities are needed')
        radius += 0.5 * (target - radius)
    raise ValueError('Hitchcock flattening fixed point not converged in 300 iterations')


def derive_bite_response(bite_pass, *, roll_youngs_modulus_pa=210e9, roll_poisson_ratio=0.3,
                         cells=256, max_radius_ratio=1.5) -> BiteResponse:
    """Nominal bite and central-difference sensitivities from the slab + Hitchcock model.

    Steps: 1e-3*h1 (exit thickness), 1e-3*h0 (entry thickness), 1e-3*Y (each tension);
    every perturbed point re-converges the flattening radius. Repeated with half steps:
    a > 2 % change in any sensitivity adds ``SENSITIVITY_STEP_NOT_CONVERGED``. Nominal
    force on 2*cells changing by > 1e-4 adds ``GRID_REFINEMENT_NOT_MET``. Force and slip
    are rate independent in the slab model, so the scenario speed (1 m/s) is arbitrary.
    """
    if not isinstance(bite_pass, BitePass):
        raise ValueError('bite_pass must be a BitePass')
    bite_pass.validate()
    if not _finite(roll_youngs_modulus_pa) or not 1e9 <= roll_youngs_modulus_pa <= 1e14:
        raise ValueError('roll Young modulus must be in [1e9, 1e14] Pa')
    if not _finite(roll_poisson_ratio) or not 0 <= roll_poisson_ratio < 0.5:
        raise ValueError('roll Poisson ratio must be in [0, 0.5)')
    if isinstance(cells, bool) or not isinstance(cells, int) or not 64 <= cells <= 4096:
        raise ValueError('cells must be an integer in [64, 4096]')
    if not _finite(max_radius_ratio) or not 1 < max_radius_ratio <= 3.0:
        raise ValueError('max_radius_ratio must be in (1, 3.0]')
    p = bite_pass
    compliance = 16 * (1 - roll_poisson_ratio ** 2) / (math.pi * roll_youngs_modulus_pa)
    h0, h1, se, sx = p.entry_thickness_m, p.exit_thickness_m, p.entry_tension_pa, p.exit_tension_pa

    def evaluate(exit_m=h1, entry_m=h0, s_e=se, s_x=sx, n=cells):
        return _converged_bite(p, exit_m, entry_m, s_e, s_x, n, compliance, max_radius_ratio)

    nominal, ratio = evaluate()

    def sensitivities(scale):
        dh1, dh0, ds = scale * 1e-3 * h1, scale * 1e-3 * h0, scale * 1e-3 * p.mean_flow_stress_pa
        out = {}
        for key, plus, minus, step in (
                ('h', {'exit_m': h1 + dh1}, {'exit_m': h1 - dh1}, dh1),
                ('hin', {'entry_m': h0 + dh0}, {'entry_m': h0 - dh0}, dh0),
                ('se', {'s_e': se + ds}, {'s_e': se - ds}, ds),
                ('sx', {'s_x': sx + ds}, {'s_x': sx - ds}, ds)):
            rp, _ = evaluate(**plus)
            rm, _ = evaluate(**minus)
            out['F_' + key] = (rp['separating_force_n'] - rm['separating_force_n']) / (2 * step)
            out['f_' + key] = ((rp['forward_slip_fraction'] - rm['forward_slip_fraction'])
                               / (2 * step))
        return out

    full = sensitivities(1.0)
    half = sensitivities(0.5)
    flags = []
    if h1 < 3e-4:
        flags.append('THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN')
    if ratio > 1.5:
        flags.append('HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE')
    for key in full:
        a, b = full[key], half[key]
        if abs(a - b) > 0.02 * max(abs(a), abs(b), 1e-300):
            flags.append('SENSITIVITY_STEP_NOT_CONVERGED')
            break
    fine, _ = evaluate(n=2 * cells)
    if abs(fine['separating_force_n'] - nominal['separating_force_n']) > \
            1e-4 * abs(fine['separating_force_n']):
        flags.append('GRID_REFINEMENT_NOT_MET')
    for flag in nominal.get('flags', []):
        if flag not in flags:
            flags.append(flag)
    flags.append('CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED')
    response = BiteResponse(
        separating_force_n=nominal['separating_force_n'],
        forward_slip_fraction=nominal['forward_slip_fraction'],
        contact_length_m=nominal['contact_length_m'], contact_radius_ratio=ratio,
        entry_thickness_m=h0, exit_thickness_m=h1,
        dforce_dexit_thickness_n_m=half['F_h'], dforce_dentry_thickness_n_m=half['F_hin'],
        dforce_dentry_tension_m2=half['F_se'], dforce_dexit_tension_m2=half['F_sx'],
        dslip_dexit_thickness_per_m=half['f_h'], dslip_dentry_thickness_per_m=half['f_hin'],
        dslip_dentry_tension_per_pa=half['f_se'], dslip_dexit_tension_per_pa=half['f_sx'],
        source='derived_slab_hitchcock', flags=tuple(flags))
    response.validate()
    return response


# ------------------------------------------------------------------- state matrix


def _check_system(stand, bite, spans, exit_speed_m_s, allow_no_bite=False):
    if not isinstance(stand, StandModel):
        raise ValueError('stand must be a StandModel')
    stand.validate()
    if bite is None and allow_no_bite:
        pass
    elif not isinstance(bite, BiteResponse):
        raise ValueError('bite must be a BiteResponse')
    else:
        bite.validate()
    if not isinstance(spans, StripSpans):
        raise ValueError('spans must be a StripSpans')
    spans.validate()
    if not _finite(exit_speed_m_s) or exit_speed_m_s <= 0:
        raise ValueError('exit_speed_m_s must be a finite positive number')


def assemble_state_matrix(stand, bite, spans, exit_speed_m_s, *,
                          bite_damping_transit_fraction=0.5, couple_tension=True):
    """Physical (unscaled) 6x6 state matrix A for z = STATE_NAMES.

    ``bite=None`` gives the structure alone (no strip in the gap, tension rows zero).
    """
    _check_system(stand, bite, spans, exit_speed_m_s, allow_no_bite=True)
    beta, couple = _options(bite_damping_transit_fraction, couple_tension)
    mw, mb = stand.work_roll_mass_kg, stand.backup_roll_mass_kg
    kwb, kh = stand.work_backup_contact_stiffness_n_m, stand.housing_stiffness_n_m
    cwb, ch = stand.work_backup_damping_n_s_m, stand.housing_damping_n_s_m
    if bite is None:
        fh = fhdot = fse = fsx = 0.0
    else:
        fh = bite.dforce_dexit_thickness_n_m
        fhdot = fh * beta * bite.contact_length_m / exit_speed_m_s
        fse, fsx = bite.dforce_dentry_tension_m2, bite.dforce_dexit_tension_m2
    a = [[0.0] * 6 for _ in range(6)]
    a[0][1] = 1.0
    a[2][3] = 1.0
    # dh = 2*x_w, dh' = 2*v_w
    a[1] = [(-kwb + 2 * fh) / mw, (-cwb + 2 * fhdot) / mw, kwb / mw, cwb / mw, fse / mw, fsx / mw]
    a[3] = [kwb / mb, cwb / mb, -(kwb + kh) / mb, -(cwb + ch) / mb, 0.0, 0.0]
    if couple and bite is not None:
        h0, h1, f = bite.entry_thickness_m, bite.exit_thickness_m, bite.forward_slip_fraction
        vr = exit_speed_m_s / (1 + f)
        df = (2 * bite.dslip_dexit_thickness_per_m, bite.dslip_dentry_tension_per_pa,
              bite.dslip_dexit_tension_per_pa)        # coefficients on x_w, sigma_e, sigma_x
        due = (vr * (h1 / h0 * df[0] + (1 + f) / h0 * 2), vr * h1 / h0 * df[1],
               vr * h1 / h0 * df[2])
        dux = (vr * df[0], vr * df[1], vr * df[2])
        ke, kx = spans.youngs_modulus_pa / spans.entry_span_length_m, \
            spans.youngs_modulus_pa / spans.exit_span_length_m
        a[4][0], a[4][4], a[4][5] = ke * due[0], ke * due[1], ke * due[2]
        a[5][0], a[5][4], a[5][5] = -kx * dux[0], -kx * dux[1], -kx * dux[2]
    return a


def _input_vector(stand, bite, spans, exit_speed_m_s, disturbance, couple_tension):
    """B column per unit disturbance amplitude [m]."""
    b = [0.0] * 6
    if disturbance == 'work_backup_runout':
        # contact spring force K_wb*(x_w - x_b + e); e > 0 pushes the work roll to the strip
        b[1] = -stand.work_backup_contact_stiffness_n_m / stand.work_roll_mass_kg
        b[3] = stand.work_backup_contact_stiffness_n_m / stand.backup_roll_mass_kg
    elif disturbance == 'entry_thickness':
        b[1] = bite.dforce_dentry_thickness_n_m / stand.work_roll_mass_kg
        if couple_tension:
            h0, h1, f = bite.entry_thickness_m, bite.exit_thickness_m, bite.forward_slip_fraction
            vr = exit_speed_m_s / (1 + f)
            fhin = bite.dslip_dentry_thickness_per_m
            b[4] = spans.youngs_modulus_pa / spans.entry_span_length_m * vr * (
                h1 / h0 * fhin - (1 + f) * h1 / h0 ** 2)
            b[5] = -spans.youngs_modulus_pa / spans.exit_span_length_m * vr * fhin
    else:
        raise ValueError(f'disturbance must be one of {DISTURBANCES}')
    return b


def _state_scales(stand):
    omega = math.sqrt((stand.work_backup_contact_stiffness_n_m + stand.housing_stiffness_n_m)
                      / stand.work_roll_mass_kg)
    lr = _REFERENCE_LENGTH_M
    return [lr, lr * omega, lr, lr * omega, _REFERENCE_STRESS_PA, _REFERENCE_STRESS_PA]


def _scaled(a, scales):
    n = len(a)
    return [[a[i][j] * scales[j] / scales[i] for j in range(n)] for i in range(n)]


# --------------------------------------------------------------------- eigenvalues


def _balance(a):
    """Parlett-Reinsch diagonal similarity balancing (radix 2), in place."""
    n = len(a)
    radix, sqrdx = 2.0, 4.0
    done = False
    while not done:
        done = True
        for i in range(n):
            c = sum(abs(a[j][i]) for j in range(n) if j != i)
            r = sum(abs(a[i][j]) for j in range(n) if j != i)
            if c != 0.0 and r != 0.0:
                g, f, s = r / radix, 1.0, c + r
                while c < g:
                    f *= radix
                    c *= sqrdx
                g = r * radix
                while c > g:
                    f /= radix
                    c /= sqrdx
                if (c + r) / f < 0.95 * s:
                    done = False
                    g = 1.0 / f
                    for j in range(n):
                        a[i][j] *= g
                    for j in range(n):
                        a[j][i] *= f


def _hessenberg(a):
    """Reduction to upper Hessenberg form by stabilised elementary similarity, in place."""
    n = len(a)
    for m in range(1, n - 1):
        x, i = 0.0, m
        for j in range(m, n):
            if abs(a[j][m - 1]) > abs(x):
                x, i = a[j][m - 1], j
        if i != m:
            for j in range(m - 1, n):
                a[i][j], a[m][j] = a[m][j], a[i][j]
            for j in range(n):
                a[j][i], a[j][m] = a[j][m], a[j][i]
        if x != 0.0:
            for i in range(m + 1, n):
                y = a[i][m - 1]
                if y != 0.0:
                    y /= x
                    a[i][m - 1] = y
                    for j in range(m, n):
                        a[i][j] -= y * a[m][j]
                    for j in range(n):
                        a[j][m] += y * a[j][i]
    for i in range(2, n):
        for j in range(i - 1):
            a[i][j] = 0.0


def _hqr(a):
    """Francis double-shift QR on a real upper Hessenberg matrix (EISPACK hqr lineage)."""
    n = len(a)
    eps = 2.220446049250313e-16
    wr = [0j] * n
    anorm = sum(abs(a[i][j]) for i in range(n) for j in range(max(i - 1, 0), n))
    nn = n - 1
    t = 0.0
    total_its = 0
    while nn >= 0:
        its = 0
        while True:
            l = nn
            while l > 0:
                s = abs(a[l - 1][l - 1]) + abs(a[l][l])
                if s == 0.0:
                    s = anorm
                if abs(a[l][l - 1]) <= eps * s:
                    a[l][l - 1] = 0.0
                    break
                l -= 1
            x = a[nn][nn]
            if l == nn:
                wr[nn] = complex(x + t, 0.0)
                nn -= 1
                break
            y = a[nn - 1][nn - 1]
            w = a[nn][nn - 1] * a[nn - 1][nn]
            if l == nn - 1:
                p = 0.5 * (y - x)
                q = p * p + w
                z = math.sqrt(abs(q))
                x += t
                if q >= 0.0:
                    z = p + math.copysign(z, p)
                    wr[nn - 1] = wr[nn] = complex(x + z, 0.0)
                    if z != 0.0:
                        wr[nn] = complex(x - w / z, 0.0)
                else:
                    wr[nn] = complex(x + p, -z)
                    wr[nn - 1] = complex(x + p, z)
                nn -= 2
                break
            if its == 60:
                raise ValueError('eigenvalue QR iteration did not converge')
            if its in (10, 20, 30, 40, 50):
                t += x
                for i in range(nn + 1):
                    a[i][i] -= x
                s = abs(a[nn][nn - 1]) + abs(a[nn - 1][nn - 2])
                y = x = 0.75 * s
                w = -0.4375 * s * s
            its += 1
            total_its += 1
            m = nn - 2
            while m >= l:
                z = a[m][m]
                r = x - z
                s = y - z
                p = (r * s - w) / a[m + 1][m] + a[m][m + 1]
                q = a[m + 1][m + 1] - z - r - s
                r = a[m + 2][m + 1]
                s = abs(p) + abs(q) + abs(r)
                p /= s
                q /= s
                r /= s
                if m == l:
                    break
                u = abs(a[m][m - 1]) * (abs(q) + abs(r))
                v = abs(p) * (abs(a[m - 1][m - 1]) + abs(z) + abs(a[m + 1][m + 1]))
                if u <= eps * v:
                    break
                m -= 1
            for i in range(m, nn - 1):
                a[i + 2][i] = 0.0
                if i != m:
                    a[i + 2][i - 1] = 0.0
            for k in range(m, nn):
                if k != m:
                    p = a[k][k - 1]
                    q = a[k + 1][k - 1]
                    r = a[k + 2][k - 1] if k + 1 != nn else 0.0
                    x = abs(p) + abs(q) + abs(r)
                    if x != 0.0:
                        p /= x
                        q /= x
                        r /= x
                s = math.copysign(math.sqrt(p * p + q * q + r * r), p)
                if s != 0.0:
                    if k == m:
                        if l != m:
                            a[k][k - 1] = -a[k][k - 1]
                    else:
                        a[k][k - 1] = -s * x
                    p += s
                    x = p / s
                    y = q / s
                    z = r / s
                    q /= p
                    r /= p
                    for j in range(k, nn + 1):
                        p = a[k][j] + q * a[k + 1][j]
                        if k + 1 != nn:
                            p += r * a[k + 2][j]
                            a[k + 2][j] -= p * z
                        a[k + 1][j] -= p * y
                        a[k][j] -= p * x
                    mmin = nn if nn < k + 3 else k + 3
                    for i in range(l, mmin + 1):
                        p = x * a[i][k] + y * a[i][k + 1]
                        if k + 1 != nn:
                            p += z * a[i][k + 2]
                            a[i][k + 2] -= p * r
                        a[i][k + 1] -= p * q
                        a[i][k] -= p
    return wr


def eigenvalues(matrix):
    """All eigenvalues of a general real square matrix (n <= 12), as Python complex.

    Balancing (diagonal similarity) -> Hessenberg -> Francis double-shift QR with
    deflation. Complex pairs are returned as exact conjugates.
    """
    if not isinstance(matrix, (list, tuple)) or not matrix:
        raise ValueError('matrix must be a nonempty list of rows')
    n = len(matrix)
    if n > 12:
        raise ValueError('eigenvalues supports n <= 12')
    a = []
    for row in matrix:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError('matrix must be square')
        if not all(_finite(v) for v in row):
            raise ValueError('matrix entries must be finite real numbers')
        a.append([float(v) for v in row])
    if n == 1:
        return [complex(a[0][0], 0.0)]
    _balance(a)
    _hessenberg(a)
    return _hqr(a)


def _system_eigenvalues(stand, bite, spans, exit_speed_m_s, beta, couple):
    a = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                              bite_damping_transit_fraction=beta, couple_tension=couple)
    return eigenvalues(_scaled(a, _state_scales(stand)))


def _classify(eigs):
    """Split structural/tension modes from neutral zero modes."""
    scale = max(abs(z) for z in eigs)
    zero = [z for z in eigs if abs(z) <= _ZERO_MODE_RELATIVE * scale]
    live = [z for z in eigs if abs(z) > _ZERO_MODE_RELATIVE * scale]
    return live, zero, scale


def _growth_and_dominant(eigs):
    live, zero, scale = _classify(eigs)
    growth = max(z.real for z in live) if live else 0.0
    osc = [z for z in live if abs(z.imag) > 1e-9 * scale]
    dominant = max(osc, key=lambda z: (z.real, -abs(z.imag))) if osc else None
    return growth, dominant, zero


# ------------------------------------------------------------- modal summaries


def natural_frequencies(stand, strip_stiffness_n_m=0.0):
    """Undamped closed-form 2-DOF frequencies of one half stack.

    'symmetric_hz': [lower, upper] with K11 = K_wb + 2*Q_s (the gap-changing family; the
    lower one is the third-octave candidate). 'antisymmetric_hz': [lower, upper] with Q_s = 0
    (both work rolls move together, gap unchanged; the upper one, work rolls in phase between
    the backup rolls, is the fifth-octave candidate: 'no significant gauge change').
    """
    if not isinstance(stand, StandModel):
        raise ValueError('stand must be a StandModel')
    stand.validate()
    if not _finite(strip_stiffness_n_m) or strip_stiffness_n_m < 0:
        raise ValueError('strip_stiffness_n_m must be finite and >= 0')
    mw, mb = stand.work_roll_mass_kg, stand.backup_roll_mass_kg
    kwb, kh = stand.work_backup_contact_stiffness_n_m, stand.housing_stiffness_n_m

    def pair(k11):
        k22 = kwb + kh
        # det([[k11 - w2*mw, -kwb], [-kwb, k22 - w2*mb]]) = 0
        a, b, c = mw * mb, -(k11 * mb + k22 * mw), k11 * k22 - kwb * kwb
        disc = math.sqrt(max(b * b - 4 * a * c, 0.0))
        hi = (-b + disc) / (2 * a)
        lo = c / (a * hi)          # product of roots; avoids cancellation
        return [math.sqrt(max(lo, 0.0)) / (2 * math.pi), math.sqrt(hi) / (2 * math.pi)]

    result = _base_result()
    sym, anti = pair(kwb + 2 * strip_stiffness_n_m), pair(kwb)
    result.update(strip_stiffness_n_m=float(strip_stiffness_n_m), symmetric_hz=sym,
                  antisymmetric_hz=anti, third_octave_candidate_hz=sym[0],
                  fifth_octave_candidate_hz=anti[1],
                  mill_modulus_n_m=stand.mill_modulus_n_m)
    result['limitations'].append('Undamped lumped half stack; the antisymmetric family '
                                 'assumes the strip adds no stiffness to that mode.')
    return result


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


def stability(stand, bite, spans, exit_speed_m_s, **options) -> dict:
    """Eigen-analysis at one exit speed (supplied beta, and beta = 0 for comparison)."""
    _check_system(stand, bite, spans, exit_speed_m_s)
    beta, couple = _options(**options)
    eigs = _system_eigenvalues(stand, bite, spans, exit_speed_m_s, beta, couple)
    growth, dominant, zero = _growth_and_dominant(eigs)
    result = _base_result()
    result['flags'].extend(bite.flags)
    if zero:
        result['flags'].append('NEUTRAL_ZERO_MODE_EXCLUDED_FROM_GROWTH_RATE')
        result['limitations'].append(
            f'{len(zero)} neutral (zero) eigenvalue(s), e.g. an uncoupled tension state, are '
            'excluded from max_growth_rate_per_s.')
    dom_hz = abs(dominant.imag) / (2 * math.pi) if dominant is not None else None
    result.update(
        exit_speed_m_s=float(exit_speed_m_s), bite_damping_transit_fraction=beta,
        couple_tension=couple, state_names=list(STATE_NAMES), modes=_mode_list(eigs),
        max_growth_rate_per_s=growth, dominant_frequency_hz=dom_hz,
        dominant_growth_rate_per_s=dominant.real if dominant is not None else None,
        stable=growth < 0,
        strip_pitch_m=(exit_speed_m_s / dom_hz) if dom_hz else None,
        bite_source=bite.source)
    if beta != 0:
        g0, d0, _ = _growth_and_dominant(
            _system_eigenvalues(stand, bite, spans, exit_speed_m_s, 0.0, couple))
        result['without_bite_damping'] = {
            'bite_damping_transit_fraction': 0.0, 'max_growth_rate_per_s': g0,
            'stable': g0 < 0,
            'dominant_frequency_hz': abs(d0.imag) / (2 * math.pi) if d0 is not None else None}
    return result


def _critical(stand, bite, spans, lo, hi, points, beta, couple):
    speeds = [lo * (hi / lo) ** (i / (points - 1)) for i in range(points)]
    growth = [_growth_and_dominant(_system_eigenvalues(stand, bite, spans, u, beta, couple))[0]
              for u in speeds]
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
        g = _growth_and_dominant(_system_eigenvalues(stand, bite, spans, mid, beta, couple))[0]
        if g >= 0:
            b = mid
        else:
            a = mid
    crit = 0.5 * (a + b)
    _, dominant, _ = _growth_and_dominant(
        _system_eigenvalues(stand, bite, spans, b, beta, couple))
    freq = abs(dominant.imag) / (2 * math.pi) if dominant is not None else None
    out.update(status='UNSTABLE_ABOVE_CRITICAL_SPEED', critical_exit_speed_m_s=crit,
               onset_frequency_hz=freq, onset_strip_pitch_m=(crit / freq) if freq else None,
               restabilises_within_scan=any(g < 0 for g in growth[idx:]))
    return out


def critical_speed(stand, bite, spans, *, speed_range_m_s=(0.05, 60.0), **options) -> dict:
    """Lowest exit speed at which the max growth rate changes sign (scan + bisection)."""
    _check_system(stand, bite, spans, 1.0)
    beta, couple = _options(**options)
    if (not isinstance(speed_range_m_s, (tuple, list)) or len(speed_range_m_s) != 2
            or not all(_finite(v) and v > 0 for v in speed_range_m_s)
            or not speed_range_m_s[0] < speed_range_m_s[1]):
        raise ValueError('speed_range_m_s must be (low, high) with 0 < low < high')
    lo, hi = float(speed_range_m_s[0]), float(speed_range_m_s[1])
    points = max(80, int(math.ceil(20 * math.log10(hi / lo))) + 1)
    main = _critical(stand, bite, spans, lo, hi, points, beta, couple)
    result = _base_result()
    result['flags'].extend(bite.flags)
    if main['restabilises_within_scan']:
        result['flags'].append('RESTABILISES_WITHIN_SCANNED_RANGE')
    result.update(main)
    result.update(speed_range_m_s=[lo, hi], scan_points=points, couple_tension=couple,
                  bite_source=bite.source)
    if beta != 0:
        result['without_bite_damping'] = _critical(stand, bite, spans, lo, hi, points, 0.0,
                                                   couple)
    return result


# ------------------------------------------------------------ frequency response


def _complex_solve(m, rhs):
    n = len(m)
    a = [list(row) + [rhs[i]] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) == 0:
            raise ValueError('singular system in frequency response (e.g. omega = 0 with '
                             'an integrating state)')
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


def frequency_response(stand, bite, spans, exit_speed_m_s, frequencies_hz, *,
                       disturbance='work_backup_runout', **options) -> list:
    """Exit-thickness response dh = 2*x_w per unit disturbance [m/m] at each frequency.

    Solves (j*omega*I - A) z = B in scaled state coordinates. Returns one dict per
    frequency: frequency_hz, disturbance, exit_thickness_per_unit_disturbance (magnitude),
    phase_rad, real, imag.
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    beta, couple = _options(**options)
    if disturbance not in DISTURBANCES:
        raise ValueError(f'disturbance must be one of {DISTURBANCES}')
    if not isinstance(frequencies_hz, (list, tuple)) or not frequencies_hz:
        raise ValueError('frequencies_hz must be a nonempty list')
    if not all(_finite(f) and f > 0 for f in frequencies_hz):
        raise ValueError('frequencies must be finite and > 0 Hz')
    scales = _state_scales(stand)
    a = _scaled(assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                                      bite_damping_transit_fraction=beta, couple_tension=couple),
                scales)
    b = _input_vector(stand, bite, spans, exit_speed_m_s, disturbance, couple)
    bs = [b[i] / scales[i] for i in range(6)]
    rows = []
    for f in frequencies_hz:
        jw = 2j * math.pi * f
        m = [[(jw if i == j else 0) - a[i][j] for j in range(6)] for i in range(6)]
        z = _complex_solve(m, bs)
        dh = 2 * z[0] * scales[0]
        rows.append({'frequency_hz': float(f), 'disturbance': disturbance,
                     'exit_thickness_per_unit_disturbance': abs(dh),
                     'phase_rad': cmath.phase(dh), 'real': dh.real, 'imag': dh.imag})
    return rows


# --------------------------------------------------------------------- simulation


def _validate_forcing(forcing):
    if not isinstance(forcing, (tuple, list)):
        raise ValueError('forcing must be a tuple of dicts')
    out = []
    for item in forcing:
        if not isinstance(item, dict):
            raise ValueError('each forcing entry must be a dict')
        unknown = set(item) - {'disturbance', 'amplitude_m', 'frequency_hz', 'phase_rad'}
        if unknown:
            raise ValueError(f'unknown forcing keys {sorted(unknown)}')
        if item.get('disturbance') not in DISTURBANCES:
            raise ValueError(f'forcing disturbance must be one of {DISTURBANCES}')
        amp, freq = item.get('amplitude_m'), item.get('frequency_hz')
        phase = item.get('phase_rad', 0.0)
        if not _finite(amp) or not _finite(freq) or freq <= 0 or not _finite(phase):
            raise ValueError('forcing needs finite amplitude_m, frequency_hz > 0, phase_rad')
        out.append((item['disturbance'], float(amp), float(freq), float(phase)))
    return out


def _trace_metrics(times, signal):
    """Zero-crossing frequency and half-cycle peak envelope growth, from the second half."""
    n = len(signal)
    start = n // 2
    crossings = []
    for i in range(start, n - 1):
        a, b = signal[i], signal[i + 1]
        if (a < 0 <= b) or (a > 0 >= b):
            if a != b:
                crossings.append(times[i] + (times[i + 1] - times[i]) * a / (a - b))
    if len(crossings) < 3:
        return None, None
    freq = (len(crossings) - 1) / (2 * (crossings[-1] - crossings[0]))
    peaks = []
    j = start
    for c0, c1 in zip(crossings, crossings[1:]):
        best, best_t = 0.0, None
        while j < n and times[j] <= c1:
            if times[j] >= c0 and abs(signal[j]) > best:
                best, best_t = abs(signal[j]), times[j]
            j += 1
        if best > 0:
            peaks.append((best_t, math.log(best)))
    if len(peaks) < 3:
        return freq, None
    mt = sum(t for t, _ in peaks) / len(peaks)
    my = sum(y for _, y in peaks) / len(peaks)
    sxx = sum((t - mt) ** 2 for t, _ in peaks)
    sxy = sum((t - mt) * (y - my) for t, y in peaks)
    return freq, (sxy / sxx if sxx > 0 else None)


def simulate(stand, bite, spans, exit_speed_m_s, *, duration_s, initial_gap_perturbation_m=1e-7,
             forcing=(), time_step_s=None, max_samples=4000,
             amplitude_limit_fraction=0.2, **options) -> dict:
    """RK4 time integration of the linear system from an initial gap perturbation.

    Initial state: x_w = dh0/2, all else zero. Forcing d_k(t) = a*sin(2*pi*f*t + phase).
    """
    _check_system(stand, bite, spans, exit_speed_m_s)
    beta, couple = _options(**options)
    if not _finite(duration_s) or duration_s <= 0:
        raise ValueError('duration_s must be finite and > 0')
    if not _finite(initial_gap_perturbation_m):
        raise ValueError('initial_gap_perturbation_m must be finite')
    if isinstance(max_samples, bool) or not isinstance(max_samples, int) or max_samples < 10:
        raise ValueError('max_samples must be an integer >= 10')
    if not _finite(amplitude_limit_fraction) or not 0 < amplitude_limit_fraction <= 1:
        raise ValueError('amplitude_limit_fraction must be in (0, 1]')
    drive = _validate_forcing(forcing)
    a = assemble_state_matrix(stand, bite, spans, exit_speed_m_s,
                              bite_damping_transit_fraction=beta, couple_tension=couple)
    scales = _state_scales(stand)
    eigs = eigenvalues(_scaled(a, scales))
    growth, dominant, _ = _growth_and_dominant(eigs)
    default_dt = 0.05 / max(abs(z) for z in eigs)
    for _, _, freq, _ in drive:
        default_dt = min(default_dt, 1 / (40 * freq))
    result = _base_result()
    result['flags'].extend(bite.flags)
    if time_step_s is None:
        dt = default_dt
    else:
        if not _finite(time_step_s) or time_step_s <= 0:
            raise ValueError('time_step_s must be finite and > 0')
        dt = float(time_step_s)
        if dt > default_dt:
            result['flags'].append('TIME_STEP_ABOVE_DEFAULT_ACCURACY_NOT_ASSURED')
    steps = int(math.ceil(duration_s / dt))
    if steps > 2_000_000:
        raise ValueError('duration_s/time_step_s exceeds 2e6 steps; shorten the duration')
    dt = duration_s / steps
    # integrate in scaled coordinates for conditioning
    bs = [[b / scales[i] for i, b in enumerate(
        _input_vector(stand, bite, spans, exit_speed_m_s, d, couple))] for d, _, _, _ in drive]
    a_s = _scaled(a, scales)
    n = 6

    def rhs(t, z):
        out = [sum(a_s[i][j] * z[j] for j in range(n)) for i in range(n)]
        for (d, amp, freq, phase), b in zip(drive, bs):
            w = amp * math.sin(2 * math.pi * freq * t + phase)
            for i in range(n):
                out[i] += b[i] * w
        return out

    z = [0.0] * n
    z[0] = 0.5 * initial_gap_perturbation_m / scales[0]
    limit = amplitude_limit_fraction * bite.exit_thickness_m
    times, dh, se, sx = [0.0], [2 * z[0] * scales[0]], [0.0], [0.0]
    exceeded = abs(dh[0]) > limit
    t = 0.0
    k = 0
    while k < steps and not exceeded:
        k1 = rhs(t, z)
        k2 = rhs(t + dt / 2, [z[i] + dt / 2 * k1[i] for i in range(n)])
        k3 = rhs(t + dt / 2, [z[i] + dt / 2 * k2[i] for i in range(n)])
        k4 = rhs(t + dt, [z[i] + dt * k3[i] for i in range(n)])
        z = [z[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(n)]
        k += 1
        t = k * dt
        times.append(t)
        dh.append(2 * z[0] * scales[0])
        se.append(z[4] * scales[4])
        sx.append(z[5] * scales[5])
        if not all(math.isfinite(v) for v in z):
            raise ValueError('nonfinite state in simulation')
        if abs(dh[-1]) > limit:
            exceeded = True
    freq, rate = _trace_metrics(times, dh)
    stride = max(1, int(math.ceil(len(times) / max_samples)))
    idx = list(range(0, len(times), stride))
    if idx[-1] != len(times) - 1 and len(idx) < max_samples:
        idx.append(len(times) - 1)
    if exceeded:
        result['flags'].append('LINEAR_RANGE_EXCEEDED')
        result['limitations'].append('Integration stopped when |dh| exceeded the linear-range '
                                     'limit; the limit cycle / strip break is not predicted.')
    result.update(
        exit_speed_m_s=float(exit_speed_m_s), bite_damping_transit_fraction=beta,
        couple_tension=couple, time_step_s=dt, steps=k, simulated_duration_s=t,
        linear_range_exceeded=exceeded, linear_range_limit_m=limit,
        time_s=[times[i] for i in idx],
        strip_position_m=[exit_speed_m_s * times[i] for i in idx],
        exit_thickness_perturbation_m=[dh[i] for i in idx],
        entry_tension_perturbation_pa=[se[i] for i in idx],
        exit_tension_perturbation_pa=[sx[i] for i in idx],
        growth_rate_per_s=rate, dominant_frequency_hz=freq,
        eigen_max_growth_rate_per_s=growth,
        eigen_dominant_frequency_hz=(abs(dominant.imag) / (2 * math.pi)
                                     if dominant is not None else None),
        trace_metrics_method='zero crossings and half-cycle peak envelope, second half of record')
    return result
