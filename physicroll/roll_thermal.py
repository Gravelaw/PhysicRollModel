"""Transient, width-resolved work-roll temperature and thermal radius model (phase 2, W1).

Opt-in, standard-library-only. Every quantity is SI; every result is a plain
JSON-serialisable dict. Nothing here is plant-validated: the model turns a supplied spray
set-up, bite heat and switching history into a circumferentially averaged roll temperature
field and a thermal radius profile. All heat-transfer inputs are supplied by the caller.

Equations (tags: [V] read in a cited source, [D] derived, [M] from memory/unverified)
------------------------------------------------------------------------------------
Circumferentially averaged axisymmetric conduction in a solid cylinder, radius ``R``, barrel
length ``B``; ``z`` in [0, B] along the barrel, ``r`` in [0, R] [V: Yamaguchi et al. 2016;
Li et al. 2024]::

    rho*c*dT/dt = k_r*(1/r)*d/dr(r*dT/dr) + k_z*d2T/dz2       (k_r = k*scale, k_z = k)
    r = R:   -k_r*dT/dr = h(z,t)*(T - T_coolant) - q(z,t)
    r = 0:   symmetry;     z = 0, B:   adiabatic (neck/chock losses ignored, flagged)

- Bite heat flux (circumferential mean, only under the strip, cell-averaged at the strip
  edges) [D]: ``q = roll_heat_fraction_per_roll*bite_heat_per_width_w_m/(2*pi*R)``.
- Heat-transfer coefficient (circumferential mean) [D]:
  ``h = background_htc + spray_mean_htc*weight(z,t)``. Nozzle ``i`` at ``z_i`` with
  along-barrel footprint ``W_eff = 2*standoff*tan(angle/2)*cos(offset)`` [V: Lloyd 2010;
  Tucker 2006] and level ``s_i`` in [0, 1] adds ``s_i*pitch/W_eff`` inside
  ``[z_i - W_eff/2, z_i + W_eff/2]`` (top-hat footprint; a healthy header averages to 1).
  Default layout as ``band_signatures.spray_coverage``: ``n = floor(B/pitch)`` nozzles
  centred on the barrel.
- Thermal radius growth per axial station [V factor 1: Yamaguchi 2016; V factor 2(1+nu):
  Li 2024 -- the sources disagree; (1+nu) is the plane-strain (eps_z = 0) result and 1 the
  axially free result [D]]::

      dR(z,t) = factor*(2*alpha/R)*integral_0^R (T - T_ref) r dr
      factor = 1 ('axially_free', default) or (1 + nu) ('plane_strain')

  Each station uses its own radial integral (axial mechanical coupling ignored, flagged).
- Thermal crown = growth at strip centre minus the mean growth at the two strip edges.

Reference limits reproduced by the tests [D]: radially lumped limit (``scale`` large)
``dT/dt = a_z*T'' + 2q/(rho*c*R) - 2h(T-Tc)/(rho*c*R)`` with ``tau = rho*c*R/(2h)`` and axial
decay length ``l = sqrt(k_z*R/(2h))``; pure radial transient (Bessel series,
``zeta*J1(zeta) = Bi*J0(zeta)``); steady uniform ``T = Tc + q/h``; energy conservation.

Numerics
--------
Conservative finite volumes on a tensor grid: uniform cells in ``z``; ``radial_cells``
geometric cells in ``r`` refined toward the surface (surface cell ``0.08*R/radial_cells``,
i.e. 1 mm for R = 0.2 m and 16 cells; growth ratio solved so the cells fill R). The surface
node temperature follows from the flux balance ``q + h*(Tc - T_s) = k_r*(T_s - T_cell)/d``
(series conductance), so ``h -> 0`` and ``h -> inf`` are both exact limits.
Time stepping: Peaceman-Rachford ADI (second order, unconditionally stable because both split
operators are self-adjoint and non-positive in the capacity-weighted inner product), with the
surface source in the radial operator and Thomas solves along ``r`` and ``z``. After every
discontinuity (start of each segment) the first step is replaced by two backward-Euler
Lie-split half steps (Rannacher start-up, L-stable) to damp the stiff skin modes that a
Crank-Nicolson-type step would leave oscillating, including modes stiff in both r and z,
which Peaceman-Rachford does not damp at all for ``dt >> dz^2/a``; for the same reason the
internal step is capped at ``dz^2/a_z`` (2.3 s at 5 mm cells; ``time_step_s`` is the largest
step, flagged when subdivided). Both schemes conserve
energy exactly: the stored energy change of a step equals ``dt * (surface heat in - out)``
with the surface temperature of the intermediate state, which the ledger sums. The ADI
fixed point is the exact steady state; the start-up step adds an O(dt) splitting error.
Steady state: the same ADI operator used as an iterative solver (its fixed point is the exact
discrete steady state for any step) with a cyclic geometric sequence of pseudo-time steps
spanning the operator spectrum (Wachspress-type), in correction form with the radial solve
last. Convergence: capacity-weighted RMS residual / slowest-rate estimate <= 1e-6 K (an
error-bound estimate); if the residual stops falling (round-off floor, e.g. the very stiff
lumped-limit hook) a bound <= 1e-4 K is accepted and flagged. Reports residual and
iterations and flags non-convergence.

NOT modelled: the per-revolution surface temperature cycle (circumferential averaging), the
bite contact conductance and roll-strip temperature coupling (``q`` is supplied), spray flow
distribution inside a fan (top-hat footprint), spray drift, temperature-dependent
properties, neck/chock heat losses, axial mechanical coupling of the thermal expansion
(plane sections, each station free or plane strain), roll wear, roll bending and flattening.
"""
from dataclasses import dataclass
import json
import math
import time

SOURCES = {
    'yamaguchi_2016': 'Yamaguchi et al. (2016) ISIJ Int., '
                      'doi:10.2355/isijinternational.isijint-2016-173 (axisymmetric work-roll '
                      'temperature model; thermal expansion factor 1)',
    'li_2024': 'Li et al. (2024) Metals 14(2):166 (work-roll thermal model; expansion factor '
               '2(1+nu) for an infinitely long cylinder)',
    'dohmae_2012': 'Dohmae & Okamura (2012) Trans. SICE 48(4), doi:10.9746/sicetr.48.193 '
                   '(flatness response to one cooling zone: first order, tau ~ 20 s)',
    'yin_2003': 'Yin et al. (2003) foil-mill heat partition, abstract only (rolls+coolant '
                '0.67-0.89 of the heat)',
    'lloyd_2010': 'Lloyd (Lechler, 2010) "Fundamentals of roll cooling and control of flatness '
                  'at primary cold reduction"',
    'tucker_2006': 'Tucker (Lechler, 2006) "Flatness and profile ... spray actuators"',
    'innoval_cooling': 'Innoval Technology roll-cooling blogs (overall spray HTC 4.65-5.5 '
                       'kW/m2K, cold-mill example, coolant unspecified)',
}

STATUS_STEADY = 'UNVALIDATED_ROLL_THERMAL_STEADY_STATE'
STATUS_STEADY_FAILED = 'UNVALIDATED_ROLL_THERMAL_STEADY_STATE_NOT_CONVERGED'
STATUS_TRANSIENT = 'UNVALIDATED_ROLL_THERMAL_TRANSIENT'
EXPANSION_CONSTRAINTS = ('axially_free', 'plane_strain')
SURFACE_CELL_FRACTION = 0.08    # surface cell = 0.08*R/radial_cells (1 mm at R=0.2 m, n=16)
STEADY_TOLERANCE_K = 1e-6       # steady residual expressed as a temperature error bound
STEADY_MAX_ITERATIONS = 3000
STAGNATION_CYCLES = 4           # cycles without a 2x residual drop -> stop
STAGNATION_ACCEPT_K = 1e-4      # accept a stagnated residual below this error bound
ADI_AXIAL_STEP_FACTOR = 1.0     # internal step cap = factor * dz^2 / a_z (2.3 s at 5 mm)
STARTUP_SUBSTEPS = 2            # backward-Euler half steps replacing the first ADI step

_LIMITATIONS = [
    'Circumferentially averaged field: the per-revolution skin temperature cycle under the '
    'sprays and in the bite is not resolved.',
    'Bite heat flux, roll heat fraction and spray heat-transfer coefficients are caller '
    'inputs; no measured value for kerosene-based coolant sprays was found (planner estimate '
    '0.5-2 kW/m2K [D]).',
    'Top-hat nozzle footprints: real fans have a tapered flow distribution, so the nozzle-'
    'pitch variation of h for a healthy header is an artefact of this idealisation.',
    'Barrel ends adiabatic (neck and chock losses ignored); constant properties.',
    'Thermal expansion per axial station (no axial mechanical coupling); the expansion factor '
    'differs between sources (1 axially free vs 1+nu plane strain).',
    'Software verification against analytic limits only; no plant validation.',
]


# --------------------------------------------------------------------------- helpers
def _num(name, value, *, positive=False, nonnegative=False, lo=None, hi=None,
         lo_open=False, hi_open=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite SI number (not bool)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{name} must be > 0')
    if nonnegative and value < 0:
        raise ValueError(f'{name} must be >= 0')
    if lo is not None and (value <= lo if lo_open else value < lo):
        raise ValueError(f'{name} must be {">" if lo_open else ">="} {lo}')
    if hi is not None and (value >= hi if hi_open else value > hi):
        raise ValueError(f'{name} must be {"<" if hi_open else "<="} {hi}')
    return value


def _int(name, value, *, lo=None, hi=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an int (not bool)')
    if lo is not None and value < lo or hi is not None and value > hi:
        raise ValueError(f'{name} must be an int in [{lo}, {hi}]')
    return value


def _seq(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f'{name} must be a list or tuple')
    return list(value)


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


def _interp(xs, ys, x):
    """Linear interpolation on increasing ``xs``; clamped outside."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    t = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + t * (ys[hi] - ys[lo])


def _overlap(a, b, c, d):
    return max(0.0, min(b, d) - max(a, c))


# --------------------------------------------------------------------------- inputs
@dataclass(frozen=True)
class RollThermalProperties:
    """Work-roll steel properties (SI). ``radial_conductivity_scale`` multiplies ``k`` in r only
    (a test hook for the radially lumped limit; physically 1)."""
    radius_m: float
    barrel_length_m: float
    density_kg_m3: float = 7850.0
    specific_heat_j_kgk: float = 470.0
    conductivity_w_mk: float = 40.0
    expansion_coefficient_per_k: float = 11.7e-6
    poisson_ratio: float = 0.3
    radial_conductivity_scale: float = 1.0

    def validate(self):
        _num('radius_m', self.radius_m, positive=True, hi=2.0)
        _num('barrel_length_m', self.barrel_length_m, positive=True, hi=10.0)
        _num('density_kg_m3', self.density_kg_m3, lo=1000.0, hi=30000.0)
        _num('specific_heat_j_kgk', self.specific_heat_j_kgk, lo=100.0, hi=5000.0)
        _num('conductivity_w_mk', self.conductivity_w_mk, lo=1.0, hi=500.0)
        _num('expansion_coefficient_per_k', self.expansion_coefficient_per_k, positive=True,
             hi=1e-4)
        _num('poisson_ratio', self.poisson_ratio, lo=0.0, hi=0.5, hi_open=True)
        _num('radial_conductivity_scale', self.radial_conductivity_scale, lo=1e-3, hi=1e8)
        return self


@dataclass(frozen=True, kw_only=True)
class SprayHeader:
    """Coolant spray header along the barrel (one header per work roll). Keyword-only (the
    spec's field order puts a required field after defaulted ones)."""
    nozzle_pitch_m: float
    standoff_m: float
    spray_angle_rad: float
    spray_mean_htc_w_m2k: float
    offset_angle_rad: float = 0.0
    first_nozzle_position_m: float | None = None
    background_htc_w_m2k: float = 50.0

    def validate(self):
        _num('nozzle_pitch_m', self.nozzle_pitch_m, positive=True, hi=10.0)
        _num('standoff_m', self.standoff_m, positive=True, hi=5.0)
        _num('spray_angle_rad', self.spray_angle_rad, positive=True, hi=math.radians(170))
        _num('offset_angle_rad', self.offset_angle_rad, nonnegative=True, hi=math.radians(60))
        if self.first_nozzle_position_m is not None:
            _num('first_nozzle_position_m', self.first_nozzle_position_m, nonnegative=True,
                 hi=10.0)
        _num('spray_mean_htc_w_m2k', self.spray_mean_htc_w_m2k, nonnegative=True, hi=1e5)
        _num('background_htc_w_m2k', self.background_htc_w_m2k, nonnegative=True, hi=1e5)
        return self

    @property
    def effective_footprint_width_m(self):
        """Along-barrel footprint ``W_eff = 2*standoff*tan(angle/2)*cos(offset)``."""
        self.validate()
        return (2 * self.standoff_m * math.tan(self.spray_angle_rad / 2)
                * math.cos(self.offset_angle_rad))

    def nozzle_positions(self, barrel_length_m):
        """Nozzle positions [m] along the barrel (same default layout as spray_coverage)."""
        self.validate()
        length = _num('barrel_length_m', barrel_length_m, positive=True, hi=10.0)
        pitch = self.nozzle_pitch_m
        if pitch > length:
            raise ValueError('nozzle_pitch_m must not exceed barrel_length_m')
        if self.first_nozzle_position_m is None:
            count = max(1, int(math.floor(length / pitch + 1e-9)))
            first = (length - (count - 1) * pitch) / 2
        else:
            first = float(self.first_nozzle_position_m)
            if first > length:
                raise ValueError('first_nozzle_position_m must lie on the barrel')
            count = int(math.floor((length - first) / pitch + 1e-9)) + 1
        return [first + i * pitch for i in range(count)]

    def weight_profile(self, z_cells, levels):
        """Cell-averaged spray weight at cell centres ``z_cells`` [m].

        The cells are contiguous and cover the barrel ``[0, B]``: their edges are the midpoints
        between centres, the outer edges mirror the neighbouring half-width, and ``B`` is the
        outer edge of the last cell. ``levels``: None (all 1.0) or one level in [0, 1] per
        nozzle. A healthy header averages to 1 away from the barrel ends.
        """
        self.validate()
        z = [_num(f'z_cells[{i}]', v) for i, v in enumerate(_seq('z_cells', z_cells))]
        if len(z) < 2 or any(b <= a for a, b in zip(z, z[1:])):
            raise ValueError('z_cells needs >= 2 strictly increasing cell centres')
        edges = [z[0] - (z[1] - z[0]) / 2]
        edges += [(a + b) / 2 for a, b in zip(z, z[1:])]
        edges.append(z[-1] + (z[-1] - z[-2]) / 2)
        if abs(edges[0]) > 1e-9 * max(1.0, edges[-1]):
            raise ValueError('z_cells must be cell centres of cells starting at z = 0')
        positions = self.nozzle_positions(edges[-1])
        lv = _levels(levels, len(positions))
        w_eff = self.effective_footprint_width_m
        height = self.nozzle_pitch_m / w_eff
        out = []
        for a, b in zip(edges, edges[1:]):
            acc = 0.0
            for x, s in zip(positions, lv):
                if s > 0:
                    acc += s * _overlap(a, b, x - w_eff / 2, x + w_eff / 2)
            out.append(height * acc / (b - a))
        return out


def _levels(levels, count):
    if levels is None:
        return [1.0] * count
    lv = _seq('nozzle_levels', levels)
    if len(lv) != count:
        raise ValueError(f'nozzle_levels needs one level per nozzle ({count}), got {len(lv)}')
    return [_num(f'nozzle_levels[{i}]', v, lo=0.0, hi=1.0) for i, v in enumerate(lv)]


@dataclass(frozen=True, kw_only=True)
class ThermalSegment:
    """Piecewise-constant operating interval (bite heat, strip position, coolant, valves).
    Keyword-only. ``strip_centre_m=None`` = barrel centre; ``nozzle_levels=None`` = all 1.0."""
    duration_s: float
    bite_heat_per_width_w_m: float
    roll_heat_fraction_per_roll: float
    strip_width_m: float
    coolant_temperature_k: float
    strip_centre_m: float | None = None
    nozzle_levels: tuple | list | None = None

    def validate(self):
        _num('duration_s', self.duration_s, positive=True, hi=1e7)
        _num('bite_heat_per_width_w_m', self.bite_heat_per_width_w_m, nonnegative=True,
             hi=1e8)
        _num('roll_heat_fraction_per_roll', self.roll_heat_fraction_per_roll, lo=0.0, hi=1.0)
        _num('strip_width_m', self.strip_width_m, positive=True, hi=10.0)
        _num('coolant_temperature_k', self.coolant_temperature_k, lo=200.0, hi=600.0)
        if self.strip_centre_m is not None:
            _num('strip_centre_m', self.strip_centre_m, nonnegative=True, hi=10.0)
        if self.nozzle_levels is not None:
            lv = _seq('nozzle_levels', self.nozzle_levels)
            for i, v in enumerate(lv):
                _num(f'nozzle_levels[{i}]', v, lo=0.0, hi=1.0)
        return self


# --------------------------------------------------------------------------- grid / problem
class _Grid:
    def __init__(self, roll, axial_cell_m, radial_cells):
        length, radius = roll.barrel_length_m, roll.radius_m
        cell = _num('axial_cell_m', axial_cell_m, positive=True, hi=length / 2)
        self.nz = max(2, int(round(length / cell)))
        if self.nz > 20000:
            raise ValueError('axial_cell_m gives more than 20000 axial cells')
        self.nr = _int('radial_cells', radial_cells, lo=3, hi=200)
        self.dz = length / self.nz
        self.z = [(j + 0.5) * self.dz for j in range(self.nz)]
        w0 = SURFACE_CELL_FRACTION * radius / self.nr
        target = radius / w0          # sum_{k<n} g^k = target
        lo, hi = 1.0 + 1e-12, 2.0
        while sum(hi ** k for k in range(self.nr)) < target:
            hi *= 2
        for _ in range(200):
            mid = (lo + hi) / 2
            if sum(mid ** k for k in range(self.nr)) < target:
                lo = mid
            else:
                hi = mid
        g = (lo + hi) / 2
        widths = [w0 * g ** k for k in range(self.nr)]       # from the surface inward
        widths.reverse()
        scale = radius / sum(widths)
        faces = [0.0]
        for w in widths:
            faces.append(faces[-1] + w * scale)
        faces[-1] = radius
        self.ratio, self.surface_cell = g, faces[-1] - faces[-2]
        self.rf = faces
        self.rc = [(a + b) / 2 for a, b in zip(faces, faces[1:])]
        self.vol = [(b * b - a * a) / 2 for a, b in zip(faces, faces[1:])]   # per rad, per m

    def describe(self):
        return {'axial_cells': self.nz, 'axial_cell_m': self.dz, 'radial_cells': self.nr,
                'surface_cell_m': self.surface_cell, 'radial_growth_ratio': self.ratio,
                'r_m': list(self.rc), 'r_faces_m': list(self.rf)}


class _Problem:
    """Discrete operators for one piecewise-constant segment."""

    def __init__(self, roll, header, segment, grid):
        self.g = grid
        radius, length = roll.radius_m, roll.barrel_length_m
        rho_c = roll.density_kg_m3 * roll.specific_heat_j_kgk
        k_r = roll.conductivity_w_mk * roll.radial_conductivity_scale
        self.cap = [rho_c * v for v in grid.vol]
        self.cond = [k_r * grid.rf[k + 1] / (grid.rc[k + 1] - grid.rc[k])
                     for k in range(grid.nr - 1)]
        self.cz = roll.conductivity_w_mk / (rho_c * grid.dz ** 2)
        width = segment.strip_width_m
        centre = length / 2 if segment.strip_centre_m is None else segment.strip_centre_m
        tol = 1e-9 * length
        if centre - width / 2 < -tol or centre + width / 2 > length + tol:
            raise ValueError('strip must lie on the barrel: centre +- width/2 within [0, B]')
        self.strip_centre, self.strip_width = centre, width
        q0 = (segment.roll_heat_fraction_per_roll * segment.bite_heat_per_width_w_m
              / (2 * math.pi * radius))
        a, b = centre - width / 2, centre + width / 2
        dz = grid.dz
        self.q = [q0 * _overlap(j * dz, (j + 1) * dz, a, b) / dz for j in range(grid.nz)]
        positions = header.nozzle_positions(length)
        levels = segment.nozzle_levels
        self.levels = _levels(levels, len(positions))
        self.positions = positions
        weight = header.weight_profile(grid.z, self.levels)
        self.weight = weight
        self.h = [header.background_htc_w_m2k + header.spray_mean_htc_w_m2k * w for w in weight]
        self.tc = segment.coolant_temperature_k
        kk = k_r / (radius - grid.rc[-1])
        self.kk = kk
        # surface: flux into last cell per rad per m = S_j - Gs_j * T_last
        self.gs = [radius * kk * h / (kk + h) for h in self.h]
        self.src = [radius * kk * (q + h * self.tc) / (kk + h) for q, h in zip(self.q, self.h)]
        self.radius = radius

    def surface_temperature(self, t_last):
        kk, tc = self.kk, self.tc
        return [(q + h * tc + kk * t) / (kk + h) for q, h, t in zip(self.q, self.h, t_last)]

    def heat_rates(self, t_last):
        """(in, out) surface heat rates [W] for the whole roll at the given last-row state."""
        ts = self.surface_temperature(t_last)
        area = 2 * math.pi * self.radius * self.g.dz
        hin = area * sum(self.q)
        hout = area * sum(h * (t - self.tc) for h, t in zip(self.h, ts))
        return hin, hout

    # ---- factorisations (cached per implicit coefficient omega)
    def rsolver(self, omega):
        nr, cap, cond = self.g.nr, self.cap, self.cond
        lower = [0.0] + [-omega * cond[k - 1] / cap[k] for k in range(1, nr)]
        upper = [-omega * cond[k] / cap[k] for k in range(nr - 1)] + [0.0]
        diag = [1 + omega * ((cond[k - 1] if k > 0 else 0.0) + cond[k]) / cap[k]
                for k in range(nr - 1)]
        m = [0.0] * nr
        inv = [0.0] * (nr - 1)
        piv = diag[0]
        inv[0] = 1 / piv
        for k in range(1, nr - 1):
            m[k] = lower[k] / piv
            piv = diag[k] - m[k] * upper[k - 1]
            inv[k] = 1 / piv
        m[nr - 1] = lower[nr - 1] / piv
        clast = cap[-1]
        base = 1 + omega * cond[-1] / clast
        inv_last = [1 / (base + omega * gs / clast - m[nr - 1] * upper[nr - 2])
                    for gs in self.gs]
        src = [omega * s / clast for s in self.src]
        # explicit (I + omega*Lr) coefficients
        e_self = [1 - omega * ((cond[k - 1] if k > 0 else 0.0) + cond[k]) / cap[k]
                  for k in range(nr - 1)]
        e_last = [1 - omega * (cond[-1] + gs) / clast for gs in self.gs]
        return {'m': m, 'inv': inv, 'upper': upper, 'inv_last': inv_last, 'src': src,
                'lo': [-x for x in lower], 'up': [-x for x in upper], 'e_self': e_self,
                'e_last': e_last}

    def zsolver(self, omega):
        nz, c = self.g.nz, omega * self.cz
        diag = [1 + 2 * c] * nz
        diag[0] = diag[-1] = 1 + c
        m = [0.0] * nz
        inv = [0.0] * nz
        piv = diag[0]
        inv[0] = 1 / piv
        for j in range(1, nz):
            m[j] = -c / piv
            piv = diag[j] - m[j] * (-c)
            inv[j] = 1 / piv
        return {'m': m, 'inv': inv, 'off': -c, 'c': c}


def _r_implicit(rs, rows, source=True):
    """Solve (I - omega*Lr) X = rows [+ omega*S/C surface source] column-wise."""
    m, inv, upper = rs['m'], rs['inv'], rs['upper']
    nr = len(rows)
    y = [None] * nr
    y[0] = rows[0]
    for k in range(1, nr - 1):
        mk, prev = m[k], y[k - 1]
        y[k] = [d - mk * p for d, p in zip(rows[k], prev)]
    ml, prev = m[nr - 1], y[nr - 2]
    if source:
        last = [(d + s - ml * p) * iv for d, s, p, iv in
                zip(rows[nr - 1], rs['src'], prev, rs['inv_last'])]
    else:
        last = [(d - ml * p) * iv for d, p, iv in zip(rows[nr - 1], prev, rs['inv_last'])]
    x = [None] * nr
    x[nr - 1] = last
    for k in range(nr - 2, -1, -1):
        uk, ik, nxt = upper[k], inv[k], x[k + 1]
        x[k] = [(d - uk * n) * ik for d, n in zip(y[k], nxt)]
    return x


def _r_explicit(rs, rows):
    """(I + omega*Lr) rows + omega*S/C."""
    lo, up, es = rs['lo'], rs['up'], rs['e_self']
    nr = len(rows)
    out = [None] * nr
    out[0] = [es[0] * t + up[0] * n for t, n in zip(rows[0], rows[1])]
    for k in range(1, nr - 1):
        a, b, e = lo[k], up[k], es[k]
        out[k] = [e * t + a * p + b * n for t, p, n in zip(rows[k], rows[k - 1], rows[k + 1])]
    a = lo[nr - 1]
    out[nr - 1] = [e * t + a * p + s for e, t, p, s in
                   zip(rs['e_last'], rows[nr - 1], rows[nr - 2], rs['src'])]
    return out


def _z_implicit(zs, rows):
    m, inv, off = zs['m'], zs['inv'], zs['off']
    nz = len(m)
    out = []
    rng = range(nz - 2, -1, -1)
    for row in rows:
        y = [0.0] * nz
        prev = 0.0
        for j in range(nz):
            prev = row[j] - m[j] * prev
            y[j] = prev
        xn = y[-1] * inv[-1]
        y[-1] = xn
        for j in rng:
            xn = (y[j] - off * xn) * inv[j]
            y[j] = xn
        out.append(y)
    return out


def _z_explicit(zs, rows):
    c = zs['c']
    e = 1 - 2 * c
    out = []
    for row in rows:
        left = [row[0]] + row[:-1]
        right = row[1:] + [row[-1]]
        out.append([e * t + c * (a + b) for t, a, b in zip(row, left, right)])
    return out


class _Stepper:
    def __init__(self, prob):
        self.p = prob
        self.cache = {}

    def _get(self, kind, omega):
        key = (kind, omega)
        if key not in self.cache:
            self.cache[key] = (self.p.rsolver(omega) if kind == 'r' else self.p.zsolver(omega))
        return self.cache[key]

    def pr_step(self, rows, dt):
        """Peaceman-Rachford step; returns (new rows, intermediate last row)."""
        w = dt / 2
        rs, zs = self._get('r', w), self._get('z', w)
        star = _r_implicit(rs, _z_explicit(zs, rows))
        new = _z_implicit(zs, _r_explicit(rs, star))
        return new, star[-1]

    def delta_step(self, rows, dt):
        """Peaceman-Rachford step in correction form for the steady iteration (round-off
        scales with the residual): (I - w Lz) d1 = w F(T); (I - w Lr) d2 = w F(T + d1).
        The radial solve comes last so that round-off injected into the stiff radial modes
        (very stiff in the lumped-limit test hook) is removed within the same step."""
        w = dt / 2
        rs, zs = self._get('r', w), self._get('z', w)
        d1 = _z_implicit(zs, [[w * x for x in row] for row in _rate(self.p, rows)])
        star = [[a + b for a, b in zip(r, d)] for r, d in zip(rows, d1)]
        d2 = _r_implicit(rs, [[w * x for x in row] for row in _rate(self.p, star)], False)
        return [[a + b for a, b in zip(r, d)] for r, d in zip(star, d2)]

    def be_step(self, rows, dt):
        """Backward-Euler Lie-split step (r then z): L-stable in each direction, so it also
        removes modes that are stiff in BOTH directions, which Peaceman-Rachford (and the
        Douglas factorisation) leave undamped at large steps. Its fixed point differs from
        the exact steady state by an O(dt) splitting error (tiny; start-up use only).
        Returns (new rows, intermediate last row at which the surface flux applies)."""
        rs, zs = self._get('r', dt), self._get('z', dt)
        star = _r_implicit(rs, rows)
        return _z_implicit(zs, star), star[-1]


def _rate(prob, rows):
    """Rows of dT/dt [K/s] implied by the discrete operator (with sources) at ``rows``."""
    nr, cap, cond, cz = prob.g.nr, prob.cap, prob.cond, prob.cz
    out = []
    for k in range(nr):
        row = rows[k]
        left = [row[0]] + row[:-1]
        right = row[1:] + [row[-1]]
        ck = cap[k]
        if k == nr - 1:
            g = cond[k - 1] / ck
            out.append([cz * (a + b - 2 * t) + g * (p - t) + (s - gs * t) / ck
                        for t, a, b, p, s, gs in
                        zip(row, left, right, rows[k - 1], prob.src, prob.gs)])
        elif k == 0:
            g = cond[0] / ck
            out.append([cz * (a + b - 2 * t) + g * (n - t)
                        for t, a, b, n in zip(row, left, right, rows[1])])
        else:
            g0, g1 = cond[k - 1] / ck, cond[k] / ck
            out.append([cz * (a + b - 2 * t) + g0 * (p - t) + g1 * (n - t)
                        for t, a, b, p, n in zip(row, left, right, rows[k - 1], rows[k + 1])])
    return out


def _residual(prob, rows):
    """(max |dT/dt|, capacity-weighted RMS dT/dt) [K/s] implied at state ``rows``.

    The weighted RMS divided by the slowest decay rate bounds the capacity-weighted RMS
    temperature error (the operator is self-adjoint in that inner product)."""
    rate = _rate(prob, rows)
    worst = max(max(abs(x) for x in row) for row in rate)
    acc = sum(c * sum(x * x for x in row) for c, row in zip(prob.cap, rate))
    return worst, math.sqrt(acc / (sum(prob.cap) * prob.g.nz))


# --------------------------------------------------------------------------- post-processing
def _expansion_factor(roll, constraint):
    if constraint not in EXPANSION_CONSTRAINTS:
        raise ValueError(f'expansion_constraint must be one of {EXPANSION_CONSTRAINTS}')
    return 1.0 if constraint == 'axially_free' else 1.0 + roll.poisson_ratio


def _profiles(prob, rows, t_ref, factor, roll):
    g = prob.g
    area = roll.radius_m ** 2 / 2
    mean = [sum(v * rows[k][j] for k, v in enumerate(g.vol)) / area for j in range(g.nz)]
    coef = factor * roll.expansion_coefficient_per_k * roll.radius_m
    growth = [coef * (t - t_ref) for t in mean]
    surface = prob.surface_temperature(rows[-1])
    return mean, growth, surface


def _crown(z, growth, centre, width):
    c = _interp(z, growth, centre)
    e = (_interp(z, growth, centre - width / 2) + _interp(z, growth, centre + width / 2)) / 2
    return c - e


def _stored_energy_j(prob, rows):
    g = prob.g
    return 2 * math.pi * g.dz * sum(c * sum(row) for c, row in zip(prob.cap, rows))


def _field(grid, rows):
    return {'r_m': list(grid.rc), 'z_m': list(grid.z),
            'temperature_k': [list(r) for r in rows]}


def _initial_rows(initial, grid, tc):
    if isinstance(initial, str):
        if initial != 'uniform_coolant':
            raise ValueError("initial must be 'uniform_coolant' or a previous result's field")
        return [[tc] * grid.nz for _ in range(grid.nr)]
    if not isinstance(initial, dict):
        raise ValueError("initial must be 'uniform_coolant' or a previous result's field")
    field = initial.get('field', initial)
    if not isinstance(field, dict) or not {'r_m', 'z_m', 'temperature_k'} <= set(field):
        raise ValueError('initial field needs r_m, z_m and temperature_k')
    r, z, temp = field['r_m'], field['z_m'], field['temperature_k']
    if (not isinstance(r, list) or not isinstance(z, list) or len(r) != grid.nr
            or len(z) != grid.nz
            or any(abs(a - b) > 1e-9 for a, b in zip(r, grid.rc))
            or any(abs(a - b) > 1e-9 for a, b in zip(z, grid.z))):
        raise ValueError('initial field grid does not match this run (same roll, '
                         'axial_cell_m and radial_cells required)')
    if not isinstance(temp, list) or len(temp) != grid.nr:
        raise ValueError('initial temperature_k must have one row per radial cell')
    rows = []
    for k, row in enumerate(temp):
        if not isinstance(row, list) or len(row) != grid.nz:
            raise ValueError('initial temperature_k rows must have one value per axial cell')
        rows.append([_num(f'initial temperature [{k}]', v, lo=150.0, hi=1500.0) for v in row])
    return rows


def _common(roll, header, axial_cell_m, radial_cells, expansion_constraint):
    if not isinstance(roll, RollThermalProperties):
        raise ValueError('roll must be RollThermalProperties')
    if not isinstance(header, SprayHeader):
        raise ValueError('header must be SprayHeader')
    roll.validate()
    header.validate()
    factor = _expansion_factor(roll, expansion_constraint)
    return _Grid(roll, axial_cell_m, radial_cells), factor


def _threshold_basis():
    return ('Conduction equation and boundary conditions [V: Yamaguchi 2016, Li 2024]; bite '
            'heat flux and spray weight construction [D]; spray HTC values supplied by the '
            'caller (no source value for kerosene sprays; planner estimate [D]); expansion '
            'factor 1 or 1+nu [D] (sources disagree); numerical tolerances analyst choice.')


def _base_flags(prob, header):
    flags = ['BARREL_ENDS_ADIABATIC', 'AXIAL_MECHANICAL_COUPLING_IGNORED',
             'CIRCUMFERENTIALLY_AVERAGED']
    if any(lv < 1.0 for lv in prob.levels):
        flags.append('NOZZLES_REDUCED_OR_OFF')
    w_eff = header.effective_footprint_width_m
    ratio = w_eff / header.nozzle_pitch_m
    if abs(ratio - round(ratio)) > 1e-6:
        flags.append('TOP_HAT_FOOTPRINTS_GIVE_PITCH_PERIODIC_HTC')
    if w_eff < header.nozzle_pitch_m:
        flags.append('NO_NOMINAL_OVERLAP_GAPS_BETWEEN_FANS')
    return flags


# --------------------------------------------------------------------------- public API
def steady_state(roll, header, segment, *, axial_cell_m=0.005, radial_cells=16,
                 expansion_constraint='axially_free', reference_temperature_k=None):
    """Steady roll temperature and thermal radius profile for one operating segment.

    ``segment.duration_s`` is ignored. ``reference_temperature_k`` (default: the coolant
    temperature) is the zero of the radius growth. Rates are reported as ``heat_in_w``,
    ``heat_out_w``, ``residual_w`` (the steady energy ledger).
    """
    grid, factor = _common(roll, header, axial_cell_m, radial_cells, expansion_constraint)
    if not isinstance(segment, ThermalSegment):
        raise ValueError('segment must be ThermalSegment')
    segment.validate()
    t_ref = (segment.coolant_temperature_k if reference_temperature_k is None else
             _num('reference_temperature_k', reference_temperature_k, lo=200.0, hi=600.0))
    t0 = time.perf_counter()
    prob = _Problem(roll, header, segment, grid)
    if max(prob.h) <= 0:
        raise ValueError('steady state needs a positive heat-transfer coefficient somewhere')
    # spectrum bounds for the pseudo-time sequence
    rho_c = roll.density_kg_m3 * roll.specific_heat_j_kgk
    k_r = roll.conductivity_w_mk * roll.radial_conductivity_scale
    lam_r_max = max(max(((prob.cond[k - 1] if k > 0 else 0) + prob.cond[k]) / prob.cap[k]
                        for k in range(grid.nr - 1)) * 2,
                    max((prob.cond[-1] + gs) / prob.cap[-1] for gs in prob.gs) * 2)
    lam_max = lam_r_max + 4 * prob.cz
    cooling = sum(prob.gs) / (grid.nz * sum(prob.cap))
    lam_min = 0.5 * min(cooling, k_r / rho_c * 5.78 / roll.radius_m ** 2)
    ratio = 4.0
    count = max(2, int(math.ceil(math.log(lam_max / lam_min) / math.log(ratio))) + 1)
    omegas = [(1 / lam_max) * (lam_min / lam_max) ** (-i / (count - 1)) for i in range(count)]
    omegas.reverse()   # large steps first: the smooth error dominates the initial guess
    rows = [[prob.tc + (q / h if h > 0 else 0.0) for q, h in zip(prob.q, prob.h)]
            for _ in range(grid.nr)]
    step = _Stepper(prob)
    iterations = 0
    residual, rms = _residual(prob, rows)
    history = [rms]
    converged = rms / lam_min <= STEADY_TOLERANCE_K
    stagnated = False
    while not converged and iterations < STEADY_MAX_ITERATIONS:
        for w in omegas:
            rows = step.delta_step(rows, 2 * w)
            iterations += 1
        residual, rms = _residual(prob, rows)
        history.append(rms)
        converged = rms / lam_min <= STEADY_TOLERANCE_K
        if (not converged and len(history) > STAGNATION_CYCLES
                and min(history[-STAGNATION_CYCLES:]) >= 0.5 * history[-STAGNATION_CYCLES - 1]):
            # no progress for several cycles: round-off floor (or a true failure)
            stagnated = True
            converged = rms / lam_min <= STAGNATION_ACCEPT_K
            break
    wall = time.perf_counter() - t0
    mean, growth, surface = _profiles(prob, rows, t_ref, factor, roll)
    hin, hout = prob.heat_rates(rows[-1])
    flags = _base_flags(prob, header)
    if not converged:
        flags.append('STEADY_STATE_NOT_CONVERGED')
    elif stagnated:
        flags.append('STEADY_RESIDUAL_AT_ROUND_OFF_FLOOR')
    crown = _crown(grid.z, growth, prob.strip_centre, prob.strip_width)
    return _checked({
        'status': STATUS_STEADY if converged else STATUS_STEADY_FAILED,
        'z_m': list(grid.z), 'surface_temperature_k': surface, 'mean_temperature_k': mean,
        'radius_growth_m': growth, 'htc_w_m2k': list(prob.h), 'heat_flux_w_m2': list(prob.q),
        'spray_weight': list(prob.weight), 'nozzle_positions_m': list(prob.positions),
        'nozzle_levels': list(prob.levels), 'thermal_crown_m': crown,
        'strip_centre_m': prob.strip_centre, 'strip_width_m': prob.strip_width,
        'reference_temperature_k': t_ref, 'expansion_constraint': expansion_constraint,
        'expansion_factor': factor,
        'heat_in_w': hin, 'heat_out_w': hout, 'residual_w': hin - hout,
        'relative_energy_residual': (hin - hout) / max(abs(hin), abs(hout), 1e-300),
        'field': _field(grid, rows), 'grid': grid.describe(),
        'solver': {'method': 'PEACEMAN_RACHFORD_ADI_ITERATION_CYCLIC_PSEUDO_TIME',
                   'iterations': iterations, 'parameters_per_cycle': count,
                   'pseudo_time_steps_s': [2 * w for w in omegas],
                   'residual_max_k_per_s': residual, 'residual_rms_k_per_s': rms,
                   'residual_temperature_equivalent_k': rms / lam_min,
                   'tolerance_k': STEADY_TOLERANCE_K,
                   'round_off_floor_accept_k': STAGNATION_ACCEPT_K, 'stagnated': stagnated,
                   'slowest_rate_estimate_per_s': lam_min,
                   'converged': converged, 'wall_time_s': wall},
        'reasons': [f'Steady thermal crown {crown:.3e} m (centre minus strip-edge mean '
                    f'radius growth).'],
        'flags': flags, 'limitations': list(_LIMITATIONS),
        'threshold_basis': _threshold_basis(),
        'sources': [SOURCES['yamaguchi_2016'], SOURCES['li_2024'], SOURCES['lloyd_2010'],
                    SOURCES['tucker_2006']]})


def history_metrics(time_s, values):
    """Peak, time of peak and time to half peak of a history's change from its first value.

    ``time_to_half_peak_s`` is the first time ``|v - v0|`` reaches half the peak ``|v - v0|``
    (linear interpolation between samples), measured from the first sample.
    """
    t = [_num(f'time_s[{i}]', v) for i, v in enumerate(_seq('time_s', time_s))]
    v = [_num(f'values[{i}]', x) for i, x in enumerate(_seq('values', values))]
    if len(t) != len(v) or len(t) < 2:
        raise ValueError('time_s and values need the same length >= 2')
    if any(b < a for a, b in zip(t, t[1:])):
        raise ValueError('time_s must be non-decreasing')
    d = [x - v[0] for x in v]
    i_pk = max(range(len(d)), key=lambda i: abs(d[i]))
    peak = d[i_pk]
    half_t = None
    if peak != 0:
        for i in range(1, len(d)):
            if abs(d[i]) >= abs(peak) / 2:
                a, b = abs(d[i - 1]), abs(d[i])
                frac = 0.0 if b == a else (abs(peak) / 2 - a) / (b - a)
                half_t = t[i - 1] + frac * (t[i] - t[i - 1]) - t[0]
                break
    return {'initial_value': v[0], 'final_value': v[-1], 'peak_change': peak,
            'time_of_peak_s': t[i_pk] - t[0],
            'time_to_half_peak_s': 0.0 if half_t is None else half_t,
            'final_change': d[-1]}


def simulate(roll, header, segments, *, initial='uniform_coolant', time_step_s=1.0,
             axial_cell_m=0.005, radial_cells=16, record_times_s=(), monitor_positions_m=(),
             expansion_constraint='axially_free', reference_temperature_k=None):
    """Transient roll temperature / thermal radius for a sequence of operating segments.

    ``initial``: 'uniform_coolant' (first segment's coolant temperature) or a previous
    ``steady_state``/``simulate`` result (or its ``field``) on the same grid.
    ``time_step_s`` is the largest step (internally capped at ``dz^2/a``; steps also land
    exactly on segment boundaries and ``record_times_s``). Snapshots are taken at
    ``record_times_s``; monitor histories (every step, linear interpolation between cell
    centres) at ``monitor_positions_m``. ``reference_temperature_k`` (default: first
    segment's coolant temperature) is the zero of the radius growth.
    """
    grid, factor = _common(roll, header, axial_cell_m, radial_cells, expansion_constraint)
    segs = _seq('segments', segments)
    if not segs:
        raise ValueError('segments must be a nonempty list of ThermalSegment')
    for s in segs:
        if not isinstance(s, ThermalSegment):
            raise ValueError('segments must contain ThermalSegment items')
        s.validate()
    dt_max = _num('time_step_s', time_step_s, positive=True, hi=1e5)
    total = sum(s.duration_s for s in segs)
    records = sorted({_num('record_times_s', x, nonnegative=True, hi=total)
                      for x in _seq('record_times_s', record_times_s)})
    monitors = [_num('monitor_positions_m', x, nonnegative=True, hi=roll.barrel_length_m)
                for x in _seq('monitor_positions_m', monitor_positions_m)]
    tc0 = segs[0].coolant_temperature_k
    t_ref = (tc0 if reference_temperature_k is None else
             _num('reference_temperature_k', reference_temperature_k, lo=200.0, hi=600.0))
    rows = _initial_rows(initial, grid, tc0)
    probs = [_Problem(roll, header, s, grid) for s in segs]
    # PR leaves modes stiff in r AND z undamped when (dt/2)*4*a_z/dz^2 >> 1; cap the step
    # at (dt/2)*4*a_z/dz^2 <= 2 (amplification of such modes <= 1/3)
    a_z = roll.conductivity_w_mk / (roll.density_kg_m3 * roll.specific_heat_j_kgk)
    step_cap = ADI_AXIAL_STEP_FACTOR * grid.dz ** 2 / a_z
    dt_step = min(dt_max, step_cap)
    t_wall = time.perf_counter()
    snapshots, mon_t = [], []
    mon_g = [[] for _ in monitors]
    mon_s = [[] for _ in monitors]
    stored0 = _stored_energy_j(probs[0], rows)
    heat_in = heat_out = 0.0
    steps = startup = 0
    seg_info = []

    def record_monitors(prob, now, rows):
        mon_t.append(now)
        if not monitors:
            return
        _, growth, surface = _profiles(prob, rows, t_ref, factor, roll)
        for i, x in enumerate(monitors):
            mon_g[i].append(_interp(grid.z, growth, x))
            mon_s[i].append(_interp(grid.z, surface, x))

    def snapshot(prob, now, idx, rows):
        mean, growth, surface = _profiles(prob, rows, t_ref, factor, roll)
        snapshots.append({'time_s': now, 'segment_index': idx, 'radius_growth_m': growth,
                          'surface_temperature_k': surface, 'mean_temperature_k': mean,
                          'thermal_crown_m': _crown(grid.z, growth, prob.strip_centre,
                                                    prob.strip_width)})

    now, rec_i = 0.0, 0
    record_monitors(probs[0], now, rows)
    while rec_i < len(records) and records[rec_i] <= 1e-12:
        snapshot(probs[0], now, 0, rows)
        rec_i += 1
    for idx, (seg, prob) in enumerate(zip(segs, probs)):
        stepper = _Stepper(prob)
        start, end = now, now + seg.duration_s
        marks = [x for x in records if start + 1e-9 < x < end - 1e-9] + [end]
        first = True
        seg_steps = 0
        area = 2 * math.pi * roll.radius_m * grid.dz
        q_rate = area * sum(prob.q)
        for mark in marks:
            span = mark - now
            n = max(1, int(math.ceil(span / dt_step - 1e-9)))
            dt = span / n
            for _ in range(n):
                if first:
                    sub = dt / STARTUP_SUBSTEPS
                    for _ in range(STARTUP_SUBSTEPS):
                        rows, star = stepper.be_step(rows, sub)
                        _, hout = prob.heat_rates(star)
                        heat_in += sub * q_rate
                        heat_out += sub * hout
                    startup += 1
                    first = False
                else:
                    rows, star = stepper.pr_step(rows, dt)
                    _, hout = prob.heat_rates(star)
                    heat_in += dt * q_rate
                    heat_out += dt * hout
                now += dt
                steps += 1
                seg_steps += 1
                record_monitors(prob, now, rows)
            now = mark
            while rec_i < len(records) and records[rec_i] <= now + 1e-9:
                snapshot(prob, records[rec_i], idx, rows)
                rec_i += 1
        seg_info.append({'index': idx, 'start_s': start, 'end_s': end, 'steps': seg_steps,
                         'nozzle_levels': list(prob.levels)})
    wall = time.perf_counter() - t_wall
    last = probs[-1]
    mean, growth, surface = _profiles(last, rows, t_ref, factor, roll)
    stored = _stored_energy_j(last, rows) - stored0
    residual = stored - (heat_in - heat_out)
    scale = max(abs(stored), abs(heat_in), abs(heat_out), 1e-300)
    mon_out = []
    for i, x in enumerate(monitors):
        entry = {'position_m': x, 'time_s': list(mon_t), 'radius_growth_m': mon_g[i],
                 'surface_temperature_k': mon_s[i]}
        if len(mon_t) >= 2:
            met = history_metrics(mon_t, mon_g[i])
            entry.update({'radius_growth_peak_change_m': met['peak_change'],
                          'time_of_peak_s': met['time_of_peak_s'],
                          'time_to_half_peak_s': met['time_to_half_peak_s']})
        mon_out.append(entry)
    flags = sorted({f for p in probs for f in _base_flags(p, header)})
    if dt_max > step_cap:
        flags.append('TIME_STEP_SUBDIVIDED_FOR_ADI_DAMPING')
    crown = _crown(grid.z, growth, last.strip_centre, last.strip_width)
    return _checked({
        'status': STATUS_TRANSIENT, 'end_time_s': now,
        'z_m': list(grid.z), 'surface_temperature_k': surface, 'mean_temperature_k': mean,
        'radius_growth_m': growth, 'htc_w_m2k': list(last.h),
        'heat_flux_w_m2': list(last.q), 'thermal_crown_m': crown,
        'reference_temperature_k': t_ref, 'expansion_constraint': expansion_constraint,
        'expansion_factor': factor,
        'stored_j': stored, 'heat_in_j': heat_in, 'heat_out_j': heat_out,
        'residual_j': residual, 'relative_energy_residual': residual / scale,
        'snapshots': snapshots, 'monitors': mon_out, 'segments': seg_info,
        'field': _field(grid, rows), 'grid': grid.describe(),
        'solver': {'method': 'PEACEMAN_RACHFORD_ADI_WITH_BACKWARD_EULER_STARTUP',
                   'time_step_s': dt_max, 'internal_time_step_cap_s': step_cap,
                   'time_step_subdivided': dt_max > step_cap, 'steps': steps,
                   'startup_steps': startup, 'startup_substeps': STARTUP_SUBSTEPS,
                   'wall_time_s': wall},
        'reasons': [f'{len(segs)} segment(s), {now:g} s simulated in {steps} steps; final '
                    f'thermal crown {crown:.3e} m.'],
        'flags': flags, 'limitations': list(_LIMITATIONS),
        'threshold_basis': _threshold_basis(),
        'sources': [SOURCES['yamaguchi_2016'], SOURCES['li_2024'], SOURCES['dohmae_2012'],
                    SOURCES['lloyd_2010'], SOURCES['tucker_2006']]})


def _legendre(x, order):
    out = [1.0, x]
    for n in range(1, order):
        out.append(((2 * n + 1) * x * out[n] - n * out[n - 1]) / (n + 1))
    return out[:order + 1]


def _project_out(y, basis):
    """Residual of least squares of y on the column basis (modified Gram-Schmidt, twice)."""
    q = []
    for col in basis:
        v = list(col)
        for _ in range(2):
            for u in q:
                d = sum(a * b for a, b in zip(u, v))
                v = [a - d * b for a, b in zip(v, u)]
        norm = math.sqrt(sum(a * a for a in v))
        if norm <= 1e-12 * math.sqrt(len(v)):
            continue
        q.append([a / norm for a in v])
    res = list(y)
    for _ in range(2):
        for u in q:
            d = sum(a * b for a, b in zip(u, res))
            res = [a - d * b for a, b in zip(res, u)]
    return res


def _crossing(z, res, i, j, level):
    """Position between samples i and j where the SIGNED residual crosses the signed
    ``level`` (linear interpolation; clamped to the interval)."""
    a, b = res[i], res[j]
    if a == b:
        return (z[i] + z[j]) / 2
    t = (level - a) / (b - a)
    return z[i] + min(1.0, max(0.0, t)) * (z[j] - z[i])


def local_stripes(z_m, radius_growth_m, strip_centre_m, strip_width_m, *, threshold_m=5e-8,
                  smooth_order=4):
    """Local stripes = radius growth minus a least-squares polynomial fitted over the strip.

    The polynomial of degree ``smooth_order`` (Legendre basis on the strip half-width) stands
    for the smooth thermal crown handled elsewhere. Stripes are contiguous runs of same-sign
    residual with ``|residual| > threshold_m``; ``HOT_HIGH`` = roll locally larger (strip
    locally over-rolled), ``COLD_LOW`` = locally smaller. Start/end are interpolated threshold
    crossings; ``width_at_half_peak_m`` is the full width where |residual| >= peak/2 around the
    peak. Crossings are interpolated on the signed residual against the signed threshold
    (signed half-peak level), so adjacent opposite-sign stripes are separated between samples
    and never overlap. Runs touching the strip edge are marked: there the polynomial cannot
    follow the crown roll-off, so they are likely fit artefacts.

    ``smooth_order=None``: no de-trending (residual = the input within the strip). This is the
    recommended setting for a difference profile (actual header minus healthy header), whose
    zero background ``smooth_order=0`` (strip mean removed) would turn into a spurious
    ``COLD_LOW`` stripe.
    """
    z = [_num(f'z_m[{i}]', v) for i, v in enumerate(_seq('z_m', z_m))]
    y = [_num(f'radius_growth_m[{i}]', v, lo=-1e-2, hi=1e-2)
         for i, v in enumerate(_seq('radius_growth_m', radius_growth_m))]
    if len(z) != len(y):
        raise ValueError('z_m and radius_growth_m must have the same length')
    if any(b <= a for a, b in zip(z, z[1:])):
        raise ValueError('z_m must be strictly increasing')
    centre = _num('strip_centre_m', strip_centre_m)
    width = _num('strip_width_m', strip_width_m, positive=True, hi=20.0)
    thr = _num('threshold_m', threshold_m, positive=True, hi=1e-3)
    order = None if smooth_order is None else _int('smooth_order', smooth_order, lo=0, hi=12)
    tol = 1e-9 * max(1.0, width)
    idx = [i for i, x in enumerate(z) if abs(x - centre) <= width / 2 + tol]
    if len(idx) < (2 if order is None else order + 3):
        raise ValueError('too few samples inside the strip for the requested smooth_order')
    zs = [z[i] for i in idx]
    ys = [y[i] for i in idx]
    if order is None:
        res = list(ys)
    else:
        xs = [(x - centre) / (width / 2) for x in zs]
        leg = [_legendre(x, order) for x in xs]
        basis = [[row[n] for row in leg] for n in range(order + 1)]
        res = _project_out(ys, basis)
    smooth = [a - b for a, b in zip(ys, res)]
    n = len(res)
    stripes = []
    i = 0
    while i < n:
        if abs(res[i]) <= thr:
            i += 1
            continue
        sgn = 1 if res[i] > 0 else -1
        j = i
        while j + 1 < n and abs(res[j + 1]) > thr and (res[j + 1] > 0) == (sgn > 0):
            j += 1
        start = _crossing(zs, res, i - 1, i, sgn * thr) if i > 0 else zs[i]
        end = _crossing(zs, res, j, j + 1, sgn * thr) if j + 1 < n else zs[j]
        k_pk = max(range(i, j + 1), key=lambda k: abs(res[k]))
        peak = res[k_pk]
        half = abs(peak) / 2
        a = k_pk
        while a > 0 and abs(res[a - 1]) >= half and (res[a - 1] > 0) == (sgn > 0):
            a -= 1
        b = k_pk
        while b + 1 < n and abs(res[b + 1]) >= half and (res[b + 1] > 0) == (sgn > 0):
            b += 1
        left = _crossing(zs, res, a - 1, a, sgn * half) if a > 0 else zs[a]
        right = _crossing(zs, res, b, b + 1, sgn * half) if b + 1 < n else zs[b]
        stripes.append({'start_m': start, 'end_m': end, 'center_m': (start + end) / 2,
                        'width_m': end - start, 'peak_deviation_m': peak,
                        'peak_position_m': zs[k_pk], 'width_at_half_peak_m': right - left,
                        'sign': 'HOT_HIGH' if sgn > 0 else 'COLD_LOW',
                        'touches_strip_edge': i == 0 or j == n - 1})
        i = j + 1
    flags = []
    if any(s['touches_strip_edge'] for s in stripes):
        flags.append('STRIPES_AT_STRIP_EDGE_MAY_BE_CROWN_FIT_ARTEFACTS')
    interior = [s for s in stripes if not s['touches_strip_edge']]
    status = 'LOCAL_STRIPES_PRESENT' if interior else (
        'ONLY_STRIP_EDGE_DEVIATIONS' if stripes else 'NO_LOCAL_STRIPES_ABOVE_THRESHOLD')
    return _checked({
        'status': status, 'z_m': zs, 'local_radius_deviation_m': res,
        'smooth_profile_m': smooth, 'stripes': stripes,
        'max_abs_deviation_m': max(abs(r) for r in res),
        'rms_deviation_m': math.sqrt(sum(r * r for r in res) / n),
        'threshold_m': thr, 'smooth_order': order,
        'reasons': [f'{len(interior)} interior and {len(stripes) - len(interior)} strip-edge '
                    f'zone(s) exceed {thr:.1e} m '
                    + ('without de-trending.' if order is None else
                       f'after removing a degree-{order} polynomial.')],
        'flags': flags,
        'limitations': ['The polynomial also absorbs part of a broad stripe and creates side '
                        'lobes of opposite sign; compare against a healthy-header run when '
                        'the stripe amplitude matters.',
                        'A smooth crown with a sharp roll-off at the strip edges (bite heat '
                        'stops there) leaves residual waves of a few micrometres under a '
                        'degree-4 fit even for a healthy header; the default 5e-8 m threshold '
                        'is far below that, so apply this to the difference from a '
                        'healthy-header run before reading interior stripes as nozzle '
                        'effects; for such a difference profile use smooth_order=None (no '
                        'de-trending), since smooth_order=0 subtracts the strip mean and turns '
                        'the zero background into a spurious COLD_LOW stripe.',
                        'Radius deviation of one roll; strip thickness/flatness effects need '
                        'both work rolls and the strip model.'],
        'threshold_basis': 'Threshold and polynomial degree are analyst choices '
                           '(default 5e-8 m, degree 4; None = no de-trending) [D].',
        'sources': [SOURCES['lloyd_2010'], SOURCES['tucker_2006']]})
