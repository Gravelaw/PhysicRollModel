"""What a shapemeter would show: zone means of the modelled flatness profile (SPEC17 package 4).

Status: ``SCREENING_RESULT_NOT_PLANT_VALIDATED``. Integration layer in the style of
``band_thermal.py``: it reads the case and finished result sections and never changes them;
no hypothesis reads it (evidence-neutral). It builds the MEASUREMENT operator only. There is no
flatness controller (actuator fitting, valve logic; gap G5, Phase 2): the tool does not predict
what a control would have done with these readings.

Zone geometry. ``edge_zone_count_per_side`` zones of ``edge_zone_width_m`` at each end, the
rest ``zone_width_m``; edges ``e_0 = centre - sum(widths)/2``, ``e_{j+1} = e_j + w_j``. Zone
``j`` holds a position ``x`` when ``e_j - 1e-9 <= x < e_{j+1} - 1e-9`` (bands and nozzles).

Zone mean [D, re-derived in SPEC17: a stress-measuring roll senses the radial force per zone,
i.e. the mean tension over the zone; the flatness shown is its deviation from the mean over the
zones]. Sample ``i`` of the profile is constant on ``[z_i - dz/2, z_i + dz/2]`` clipped to the
strip ``[a_0, a_1]``; ``o_ij`` = |cell i ∩ zone j ∩ strip|;
``m_j = sum_i(I_i*o_ij)/sum_i(o_ij)``;
coverage ``c_j = |zone j ∩ strip|/w_j`` (``c_j = 0``: the zone reads null); roll mean
``m_bar = sum_j(c_j*w_j*m_j)/sum_j(c_j*w_j)``; unspread reading ``u_j = m_j - m_bar``.

Neighbour spreading [D, an interpretation of the vendor statement "max. 2 x 12.5 % force
spreading to adjacent measurement zones", SS-S29 VP; the vendor's own algorithm was not read]:
``r_j = (1 - 2s)*u_j + s*(u_{j-1} + u_{j+1})``, a missing or uncovered neighbour replaced by
``u_j``; off by default (``s = 0`` gives ``r_j = u_j``).

Dilution of a reference band of peak 1 in a zone of width ``w`` [D, re-derived in SPEC17]:
top-hat of width ``b``: centred ``min(b, w)/w``, on a zone boundary ``min(b/2, w)/w``; Gaussian
of half-peak width ``b``, ``k = sqrt(pi/(4 ln 2))``: centred ``(b/w)*k*erf(sqrt(ln 2)*w/b)``, on
a boundary ``(b/(2w))*k*erf(2*sqrt(ln 2)*w/b)``.

Vendor facts [SS-S29, SS-S30 VP; SS-S31, SS-S32 EX]: zones of 26 or 52 mm on rolls, 25-100 mm
on rotors; spreading to neighbours; a band narrower than a zone is diluted; a tight edge and a
loose pocket in one zone are missed. The vendor accuracy figure (0.5 I-units typical, SS-S29 VP)
is never used as a default threshold.

NOT modelled: roll wrap, measurement noise, calibration, temperature compensation, dynamics and
filters, the evolution of the stress between bite and shapemeter [SS-S22 EX], the stress relief
of a buckled band, any vendor edge rule, any controller.
"""
import math

from . import band_process as bp
from .band_width import spray_layout

STATUS = 'SCREENING_RESULT_NOT_PLANT_VALIDATED'
MEASUREMENT_KEYS = ('shapemeter', 'thickness_gauge')
SHAPEMETER_REQUIRED = ('zone_width_m', 'zone_count', 'provenance')
SHAPEMETER_DEFAULTS = {'edge_zone_width_m': None, 'edge_zone_count_per_side': 0,
                       'centre_m': None, 'neighbour_spreading_fraction': 0.0,
                       'resolution_i_units': None}
DILUTION_BAND_WIDTHS_M = (0.010, 0.020, 0.040, 0.080, 0.160)
EDGE_TOL_M = 1e-9
FLAG_APPLIED = 'SHAPEMETER_OPERATOR_APPLIED'
FLAG_BELOW = 'MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD'
FLAG_UNCOVERED = 'SHAPEMETER_DOES_NOT_COVER_STRIP'
FLAG_SPREAD = 'SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED'
FLAGS = (FLAG_APPLIED, FLAG_BELOW, FLAG_UNCOVERED, FLAG_SPREAD)
NO_CONTROLLER = ('NO flatness controller: the tool does not predict what the control would have '
                 'done with these readings (gap G5, Phase 2).')
LIMITATIONS = (
    'Readings are zone means of the modelled far-field stress profile, not a prediction of the '
    "operator's screen.",
    'No roll wrap, no measurement noise, no calibration, no temperature compensation, no '
    'dynamics or filter.',
    'The stress still evolves between the bite and the shapemeter [SS-S22 EX].',
    'A buckled (manifest) band no longer carries the stress the linear profile assigns to it.',
    NO_CONTROLLER)
NOZZLE_MAP_STATEMENT = ('Cooling zones are built at the shapemeter pitch and each spray is driven '
                        'by its zone [SS-S31 EX, SS-S33 EX, SS-S34 EX]; the tool has one header '
                        'row and no controller.')
SPREADING_BASIS = ('[D] interpretation of "max. 2 x 12.5 % force spreading to adjacent '
                   'measurement zones" [SS-S29 VP]; the vendor algorithm was not read; off by '
                   'default')
BASIS = {
    'zone_mean': '[D, re-derived in SPEC17] mean tension over the zone; reading = zone mean '
                 'minus the mean over the zones',
    'neighbour_spreading': SPREADING_BASIS,
    'zone_widths': '26 or 52 mm on rolls, 25-100 mm on rotors [SS-S29, SS-S30 VP; SS-S31 EX]',
    'dilution': '[D, re-derived in SPEC17] zone mean of a top-hat or Gaussian band of peak 1',
    'vendor_accuracy': '0.5 I-units typical [SS-S29 VP]; quoted only, never a default'}


# ----------------------------------------------------------------------------- validation
def _num(where, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{where} must be a finite number')
    return float(value)


def _int(value):
    return not isinstance(value, bool) and isinstance(value, int)


def validate_shapemeter(s):
    w = 'measurement.shapemeter'
    bp.keys(w, s, SHAPEMETER_REQUIRED, tuple(SHAPEMETER_DEFAULTS))
    out = dict(SHAPEMETER_DEFAULTS)
    zw = s['zone_width_m']
    if isinstance(zw, bool) or not isinstance(zw, (int, float)) or not math.isfinite(zw) \
            or not 0 < zw <= 0.5:
        raise ValueError(f'{w}.zone_width_m must be in (0, 0.5] m')
    out['zone_width_m'] = float(zw)
    n = s['zone_count']
    if not _int(n) or not 1 <= n <= 400:
        raise ValueError(f'{w}.zone_count must be an int in [1, 400]')
    out['zone_count'] = n
    ew = s.get('edge_zone_width_m')
    if ew is not None:
        if isinstance(ew, bool) or not isinstance(ew, (int, float)) or not math.isfinite(ew) \
                or not 0 < ew <= zw:
            raise ValueError(f'{w}.edge_zone_width_m must be in (0, zone_width_m] or null')
        ew = float(ew)
    out['edge_zone_width_m'] = ew
    ec = s.get('edge_zone_count_per_side', 0)
    if not _int(ec) or ec < 0 or 2 * ec > n or (ew is None and ec != 0) \
            or (ew is not None and ec < 1):
        raise ValueError(f'{w}.edge_zone_count_per_side must be an int >= 0 with 2*count <= '
                         'zone_count; 0 when edge_zone_width_m is null and >= 1 when it is given')
    out['edge_zone_count_per_side'] = ec
    c = s.get('centre_m')
    if c is not None:
        if isinstance(c, bool) or not isinstance(c, (int, float)) or not math.isfinite(c) \
                or not 0 <= c <= 10:
            raise ValueError(f'{w}.centre_m must be in [0, 10] m or null')
        c = float(c)
    out['centre_m'] = c
    sp = s.get('neighbour_spreading_fraction', 0.0)
    if isinstance(sp, bool) or not isinstance(sp, (int, float)) or not math.isfinite(sp) \
            or not 0 <= sp <= 0.25:
        raise ValueError(f'{w}.neighbour_spreading_fraction must be in [0, 0.25]')
    out['neighbour_spreading_fraction'] = float(sp)
    res = s.get('resolution_i_units')
    if res is not None:
        if isinstance(res, bool) or not isinstance(res, (int, float)) or not math.isfinite(res) \
                or not 0 < res <= 100:
            raise ValueError(f'{w}.resolution_i_units must be in (0, 100] or null')
        res = float(res)
    out['resolution_i_units'] = res
    pv = s['provenance']
    if not isinstance(pv, str) or not pv.strip():
        raise ValueError(f'{w}.provenance must be a nonempty string')
    out['provenance'] = pv
    return out


def validate_measurement(m):
    """Strict keys; ``shapemeter`` and ``thickness_gauge`` optional (null = not supplied)."""
    bp.keys('measurement', m, (), MEASUREMENT_KEYS)
    if m.get('thickness_gauge') is not None:
        raise ValueError('measurement.thickness_gauge is not available yet: it must be null')
    sm = m.get('shapemeter')
    return {'shapemeter': None if sm is None else validate_shapemeter(sm),
            'thickness_gauge': None}


# ----------------------------------------------------------------------------- operator
def zone_edges(centre_m, zone_width_m, zone_count, edge_zone_width_m=None,
               edge_zone_count_per_side=0):
    widths = [zone_width_m] * zone_count
    if edge_zone_width_m is not None:
        for k in range(edge_zone_count_per_side):
            widths[k] = widths[-1 - k] = edge_zone_width_m
    e = [centre_m - math.fsum(widths) / 2]
    for w in widths:
        e.append(e[-1] + w)
    return e


def zone_of(edges, x):
    """Index of the zone that holds ``x`` (``e_j - 1e-9 <= x < e_{j+1} - 1e-9``), else None."""
    for j in range(len(edges) - 1):
        if edges[j] - EDGE_TOL_M <= x < edges[j + 1] - EDGE_TOL_M:
            return j
    return None


def zone_means(z_m, values, strip_start_m, strip_end_m, edges):
    """Per zone ``(m_j, c_j)``: overlap-weighted mean of the profile and the coverage."""
    dz = z_m[1] - z_m[0] if len(z_m) > 1 else 0.0
    out = []
    for lo, hi in zip(edges, edges[1:]):
        a, b = max(lo, strip_start_m), min(hi, strip_end_m)
        if b <= a:
            out.append((None, 0.0))
            continue
        acc = cov = 0.0
        for zi, v in zip(z_m, values):
            cl, ch = max(zi - dz / 2, a), min(zi + dz / 2, b)
            if ch > cl:
                acc += v * (ch - cl)
                cov += ch - cl
        out.append((acc / cov if cov > 0 else None, (b - a) / (hi - lo)))
    return out


def readings(means, edges, spreading_fraction):
    """``(r, u, m_bar)``: spread readings, unspread readings and the roll mean."""
    parts = [(m, c, hi - lo) for (m, c), lo, hi in zip(means, edges, edges[1:])]
    wsum = math.fsum(c * w for m, c, w in parts if m is not None)
    if wsum <= 0:
        return [None] * len(parts), [None] * len(parts), None
    m_bar = math.fsum(m * c * w for m, c, w in parts if m is not None) / wsum
    u = [None if m is None else m - m_bar for m, c, w in parts]
    s = spreading_fraction
    r = []
    for j, uj in enumerate(u):
        if uj is None:
            r.append(None)
            continue
        left = u[j - 1] if j > 0 and u[j - 1] is not None else uj
        right = u[j + 1] if j + 1 < len(u) and u[j + 1] is not None else uj
        r.append((1 - 2 * s) * uj + s * (left + right))
    return r, u, m_bar


def half_peak_width_m(z_m, values, peak_position_m):
    """Contiguous samples around the peak sample with the peak's sign and |I| >= |peak|/2."""
    if len(z_m) < 2:
        return None
    dz = z_m[1] - z_m[0]
    k = min(range(len(z_m)), key=lambda i: abs(z_m[i] - peak_position_m))
    p = values[k]
    if p == 0:
        return 0.0

    def ok(i):
        return values[i] * p > 0 and abs(values[i]) >= abs(p) / 2
    lo = hi = k
    while lo - 1 >= 0 and ok(lo - 1):
        lo -= 1
    while hi + 1 < len(values) and ok(hi + 1):
        hi += 1
    return (hi - lo + 1) * dz


def dilution(band_width_m, zone_width_m):
    """Zone mean of a band of peak 1: top-hat and Gaussian, centred and on a boundary."""
    b, w = band_width_m, zone_width_m
    k = math.sqrt(math.pi / (4 * math.log(2)))
    return {'band_width_m': b,
            'tophat_centred': min(b, w) / w, 'tophat_on_boundary': min(b / 2, w) / w,
            'gaussian_centred': (b / w) * k * math.erf(math.sqrt(math.log(2)) * w / b),
            'gaussian_on_boundary': (b / (2 * w)) * k * math.erf(2 * math.sqrt(math.log(2))
                                                                  * w / b)}


def dilution_table(zone_width_m):
    return {'zone_width_m': zone_width_m, 'basis': BASIS['dilution'],
            'rows': [dilution(b, zone_width_m) for b in DILUTION_BAND_WIDTHS_M]}


def shapemeter_profiles(width):
    """Modelled flatness profiles the operator reads (later packages append to this list)."""
    out = []
    if not isinstance(width, dict):
        return out
    shape = width.get('shape') if isinstance(width.get('shape'), dict) else {}
    st = shape.get('steady')

    def usable(d):
        return (isinstance(d, dict) and isinstance(d.get('z_m'), list)
                and isinstance(d.get('i_units_with_feedback'), list)
                and isinstance(d.get('levels'), dict)
                and isinstance(d['levels'].get('with_feedback'), dict)
                and len(d['z_m']) == len(d['i_units_with_feedback']) and len(d['z_m']) > 1)
    if usable(st):
        out.append({'name': 'steady', 'label': 'steady stripe profile (with exit-tension '
                    'feedback)', 'z_m': st['z_m'], 'i_units': st['i_units_with_feedback'],
                    'bands': st['levels']['with_feedback'].get('bands') or [],
                    'reporting_threshold_i_units': st.get('reporting_threshold_i_units')})
    ev = width.get('thermal_events') if isinstance(width.get('thermal_events'), dict) else {}
    for k, e in enumerate(ev.get('events') or []):
        ps = e.get('peak_shape') if isinstance(e, dict) else None
        if usable(ps):
            out.append({'name': f'event_{k}_peak',
                        'label': f'event {k + 1} at its peak ('
                                 f'{e.get("label") or "cooling-zone event"})',
                        'z_m': ps['z_m'], 'i_units': ps['i_units_with_feedback'],
                        'bands': ps['levels']['with_feedback'].get('bands') or [],
                        'reporting_threshold_i_units': ps.get('reporting_threshold_i_units')})
    rip = shape.get('nozzle_pattern_ripple')
    if usable(st) and isinstance(rip, dict) and isinstance(rip.get('i_units_with_feedback'),
                                                           list) \
            and len(rip['i_units_with_feedback']) == len(st['z_m']):
        out.append({'name': 'nozzle_pattern_ripple', 'label': 'nozzle-pattern ripple of the '
                    'healthy header', 'z_m': st['z_m'], 'i_units': rip['i_units_with_feedback'],
                    'bands': [], 'reporting_threshold_i_units':
                        st.get('reporting_threshold_i_units')})
    return out


def read_profile(profile, edges, strip_start_m, strip_end_m, spreading_fraction,
                 resolution_i_units=None):
    """Apply the operator to one profile; returns (profile dict, threshold, basis)."""
    z, vals = profile['z_m'], profile['i_units']
    means = zone_means(z, vals, strip_start_m, strip_end_m, edges)
    r, u, m_bar = readings(means, edges, spreading_fraction)
    if resolution_i_units is not None:
        thr, basis = resolution_i_units, 'measurement.shapemeter.resolution_i_units (supplied)'
    else:
        thr = profile.get('reporting_threshold_i_units')
        basis = ("the profile's reporting_threshold_i_units (the tool's own band threshold); "
                 'no vendor resolution is assumed')
    cov = [(j, x) for j, x in enumerate(r) if x is not None]
    jmax = max(cov, key=lambda t: abs(t[1]))[0] if cov else None
    bands = []
    for b in profile['bands']:
        x = b.get('peak_position_m')
        peak = b.get('peak_i_units')
        j = zone_of(edges, x) if x is not None else None
        rd = r[j] if j is not None else None
        above = None if (rd is None or thr is None) else abs(rd) >= thr
        bands.append({
            'peak_position_m': x, 'start_m': b.get('start_m'), 'end_m': b.get('end_m'),
            'sense': b.get('sense'), 'state': b.get('state'), 'peak_i_units': peak,
            'half_peak_width_m': half_peak_width_m(z, vals, x) if x is not None else None,
            'zone_index': j, 'zone_reading_i_units': rd,
            'reading_to_peak_ratio': (rd / peak) if (rd is not None and peak) else None,
            'reads_above_threshold': above,
            'shows': (None if above is None else
                      'would show' if above else 'would probably not show')})
    return {'name': profile['name'], 'label': profile['label'], 'readings_i_units': r,
            'unspread_readings_i_units': u, 'zone_means_i_units': [m for m, _ in means],
            'roll_mean_i_units': m_bar,
            'max_abs_reading_i_units': abs(r[jmax]) if jmax is not None else None,
            'max_abs_zone_index': jmax,
            'profile_max_abs_i_units': max((abs(v) for v in vals), default=None),
            'bands': bands}, thr, basis


def nozzle_map(case, edges, zone_width_m):
    """Nozzles per zone from ``band_width.spray_layout`` (the width section's geometry)."""
    lay = spray_layout(case)
    zones = [[] for _ in range(len(edges) - 1)]
    outside = []
    for i, x in enumerate(lay['nozzle_positions_m']):
        j = zone_of(edges, x)
        (zones[j] if j is not None else outside).append(i)
    counts = [len(z) for z in zones]
    pitch = case['width_model'].get('cooling_zone_pitch_m')
    return {'zones': [{'zone_index': j, 'nozzle_indices': zs,
                       'nozzle_levels': [lay['nozzle_levels'][i] for i in zs]}
                      for j, zs in enumerate(zones)],
            'nozzles_per_zone_min': min(counts), 'nozzles_per_zone_max': max(counts),
            'zones_without_nozzle': [j for j, c in enumerate(counts) if c == 0],
            'nozzles_outside_the_zones': outside,
            'nozzle_pitch_m': lay['nozzle_pitch_m'],
            'cooling_zone_pitch_m': pitch,
            'cooling_zone_pitch_to_zone_width': None if pitch is None else pitch / zone_width_m,
            'statement': NOZZLE_MAP_STATEMENT}, lay


def shapemeter_section(case, result):
    s = case['measurement']['shapemeter']
    flags = []
    lay, nmap, reason = None, None, None
    if case.get('width_model') is not None:
        try:
            lay = spray_layout(case)
        except ValueError as exc:
            reason = f'width model layout not available: {exc}'
    else:
        reason = 'no width_model: no modelled flatness profile across the width'
    if lay is not None:
        a0, a1, centre = lay['strip_start_m'], lay['strip_end_m'], lay['strip_centre_m']
    else:
        a0, a1 = 0.0, case['pass']['width_m']
        centre = a1 / 2
    if s['centre_m'] is not None:
        centre = s['centre_m']
    edges = zone_edges(centre, s['zone_width_m'], s['zone_count'], s['edge_zone_width_m'],
                       s['edge_zone_count_per_side'])
    if lay is not None:
        nmap, _ = nozzle_map(case, edges, s['zone_width_m'])
    covered = [max(0.0, min(hi, a1) - max(lo, a0)) for lo, hi in zip(edges, edges[1:])]
    zones = [{'index': j, 'start_m': lo, 'end_m': hi, 'width_m': hi - lo,
              'coverage_fraction': covered[j] / (hi - lo),
              'nozzle_indices': nmap['zones'][j]['nozzle_indices'] if nmap else None,
              'nozzle_levels': nmap['zones'][j]['nozzle_levels'] if nmap else None}
             for j, (lo, hi) in enumerate(zip(edges, edges[1:]))]
    uncovered = (a1 - a0) - math.fsum(covered)
    layout = {'zone_count': s['zone_count'],
              'covered_zone_count': sum(1 for c in covered if c > 0),
              'first_edge_m': edges[0], 'last_edge_m': edges[-1], 'strip_start_m': a0,
              'strip_end_m': a1, 'uncovered_strip_width_m': uncovered}
    out = {'status': STATUS, 'not_supplied': False, 'provenance': s['provenance'],
           'zone_layout': layout, 'zones': zones,
           'neighbour_spreading_fraction': s['neighbour_spreading_fraction'],
           'neighbour_spreading_basis': SPREADING_BASIS,
           'dilution_table': dilution_table(s['zone_width_m']),
           'nozzle_map': nmap if nmap is not None else bp.not_supplied(
               'no width_model: no spray header to map'),
           'basis': dict(BASIS), 'limitations': list(LIMITATIONS)}
    profiles = shapemeter_profiles(result.get('width')) if reason is None else []
    if not profiles:
        out.update(status='NOT_ASSESSABLE', reason=reason or 'no modelled flatness profile in '
                   'the width section', profiles=[], threshold_i_units=None,
                   threshold_basis=None, flags=flags)
        return out
    read, thr, basis = [], None, None
    for prof in profiles:
        p, t, b = read_profile(prof, edges, a0, a1, s['neighbour_spreading_fraction'],
                               s['resolution_i_units'])
        if thr is None:
            thr, basis = t, b
        read.append(p)
    flags.append(FLAG_APPLIED)
    if any(b['reads_above_threshold'] is False for p in read
           if p['name'] == 'steady' or p['name'].startswith('event_') for b in p['bands']):
        flags.append(FLAG_BELOW)
    dz = profiles[0]['z_m'][1] - profiles[0]['z_m'][0]
    if uncovered > dz:
        flags.append(FLAG_UNCOVERED)
    if s['neighbour_spreading_fraction'] > 0:
        flags.append(FLAG_SPREAD)
    out.update(threshold_i_units=thr, threshold_basis=basis, profiles=read, flags=flags)
    return out


def measurement_section(case, result):
    """``result['measurement']``: not supplied without ``case['measurement']``."""
    m = case.get('measurement')
    if m is None:
        return bp.not_supplied('measurement is null or absent')
    sm = (bp.not_supplied('measurement.shapemeter is null or absent')
          if m.get('shapemeter') is None else shapemeter_section(case, result))
    flags = list(sm.get('flags') or [])
    return {'status': STATUS, 'not_supplied': False, 'shapemeter': sm,
            'thickness_gauge': bp.not_supplied('measurement.thickness_gauge is null or absent'),
            'flags': flags, 'limitations': list(LIMITATIONS)}
