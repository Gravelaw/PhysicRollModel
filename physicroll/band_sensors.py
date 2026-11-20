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
MEASUREMENT_KEYS = ('shapemeter', 'thickness_gauge', 'pass_records')
SHAPEMETER_REQUIRED = ('zone_width_m', 'zone_count', 'provenance')
SHAPEMETER_DEFAULTS = {'edge_zone_width_m': None, 'edge_zone_count_per_side': 0,
                       'centre_m': None, 'neighbour_spreading_fraction': 0.0,
                       'resolution_i_units': None, 'temperature_compensated': None}
DILUTION_BAND_WIDTHS_M = (0.010, 0.020, 0.040, 0.080, 0.160)
EDGE_TOL_M = 1e-9
FLAG_APPLIED = 'SHAPEMETER_OPERATOR_APPLIED'
FLAG_BELOW = 'MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD'
FLAG_UNCOVERED = 'SHAPEMETER_DOES_NOT_COVER_STRIP'
FLAG_SPREAD = 'SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED'
FLAG_COMPENSATED = 'SHAPEMETER_TEMPERATURE_COMPENSATED'
FLAGS = (FLAG_APPLIED, FLAG_BELOW, FLAG_UNCOVERED, FLAG_SPREAD, FLAG_COMPENSATED)
HOT_LABEL_COMPENSATED = ("steady profile as measured hot: before the shapemeter's own "
                         'temperature compensation; a compensated system shows the mechanical '
                         'profile')
HOT_LABEL = 'steady profile as measured hot: what the shapemeter shows'
NO_CONTROLLER = ('NO flatness controller in this section: the shapemeter operator applies no '
                 "control and does not predict what the plant's control would have done with "
                 'these readings. A spray-zone loop with the tool\'s own control law is a separate '
                 'opt-in section (width.flatness_control, band-diagnosis section 7.12).')
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
    tc = s.get('temperature_compensated')
    if tc is not None and not isinstance(tc, bool):
        raise ValueError(f'{w}.temperature_compensated must be true, false or null')
    out['temperature_compensated'] = tc
    pv = s['provenance']
    if not isinstance(pv, str) or not pv.strip():
        raise ValueError(f'{w}.provenance must be a nonempty string')
    out['provenance'] = pv
    return out


def validate_measurement(m):
    """Strict keys; ``shapemeter``, ``thickness_gauge`` and ``pass_records`` (SPEC18 package 7)
    optional (null = not supplied)."""
    bp.keys('measurement', m, (), MEASUREMENT_KEYS)
    sm, tg, pr = m.get('shapemeter'), m.get('thickness_gauge'), m.get('pass_records')
    return {'shapemeter': None if sm is None else validate_shapemeter(sm),
            'thickness_gauge': None if tg is None else validate_thickness_gauge(tg),
            'pass_records': None if pr is None else validate_pass_records(pr)}


# ------------------------------------------------- pass records (SPEC18 package 7, BT-G6)
PASS_RECORD_REQUIRED = ('label', 'separating_force_n', 'provenance')
PASS_RECORD_PASS_KEYS = ('exit_speed_m_s', 'entry_thickness_m', 'exit_thickness_m',
                         'entry_tension_pa', 'exit_tension_pa', 'mean_flow_stress_pa')
PASS_RECORD_OPTIONAL = (('forward_slip_fraction', 'torque_per_work_roll_nm')
                        + PASS_RECORD_PASS_KEYS + tuple(bp.PASS_RECORD_UNCERTAINTY_DEFAULTS))
PASS_RECORDS_MAX = 8


def _record_num(where, value, lo, hi, lo_open, hi_open, text, allow_none=False):
    if value is None and allow_none:
        return None
    ok = (not isinstance(value, bool) and isinstance(value, (int, float))
          and math.isfinite(value) and (value > lo if lo_open else value >= lo)
          and (value < hi if hi_open else value <= hi))
    if not ok:
        raise ValueError(f'{where} must be {text}')
    return float(value)


def validate_pass_records(records):
    """1 to 8 records of a measured pass: force (required), forward slip and torque (optional),
    the pass values that differ from the case pass (null = the case pass), the uncertainties
    (defaults ``band_process.PASS_RECORD_UNCERTAINTY_DEFAULTS``, analyst choices [D])."""
    if not isinstance(records, list) or not 1 <= len(records) <= PASS_RECORDS_MAX:
        raise ValueError(f'measurement.pass_records must be null or a list of 1 to '
                         f'{PASS_RECORDS_MAX} records')
    out = []
    inf = float('inf')
    for i, r in enumerate(records):
        w = f'measurement.pass_records[{i}]'
        bp.keys(w, r, PASS_RECORD_REQUIRED, PASS_RECORD_OPTIONAL)
        rec = {}
        for k in ('label', 'provenance'):
            if not isinstance(r[k], str) or not r[k].strip():
                raise ValueError(f'{w}.{k} must be a nonempty string')
            rec[k] = r[k]
        rec['separating_force_n'] = _record_num(f'{w}.separating_force_n',
                                                r['separating_force_n'], 0, inf, True, True,
                                                '> 0 N')
        rec['forward_slip_fraction'] = _record_num(
            f'{w}.forward_slip_fraction', r.get('forward_slip_fraction'), -0.2, 1, True, True,
            'in (-0.2, 1) or null', True)
        rec['torque_per_work_roll_nm'] = _record_num(
            f'{w}.torque_per_work_roll_nm', r.get('torque_per_work_roll_nm'), 0, inf, True, True,
            '> 0 N m or null', True)
        rec['exit_speed_m_s'] = _record_num(f'{w}.exit_speed_m_s', r.get('exit_speed_m_s'), 0,
                                            inf, True, True, '> 0 m/s or null', True)
        for k in ('entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa'):
            rec[k] = _record_num(f'{w}.{k}', r.get(k), 0, inf, True, True, '> 0 or null', True)
        for k in ('entry_tension_pa', 'exit_tension_pa'):
            rec[k] = _record_num(f'{w}.{k}', r.get(k), 0, inf, False, True, '>= 0 or null', True)
        for k, hi in (('force_uncertainty_fraction', 0.5), ('slip_uncertainty_absolute', 0.2),
                      ('torque_uncertainty_fraction', 0.5)):
            v = r.get(k)
            rec[k] = (bp.PASS_RECORD_UNCERTAINTY_DEFAULTS[k] if v is None else
                      _record_num(f'{w}.{k}', v, 0, hi, True, False, f'in (0, {hi:g}]'))
        out.append(rec)
    return out


GAUGE_REQUIRED = ('spot_length_m', 'time_constant_s', 'provenance')
GAUGE_DEFAULTS = {'sample_interval_s': None, 'position_m': None, 'spot_width_m': None}


def _rng(where, value, lo, hi, lo_open, text, allow_none=False):
    if value is None and allow_none:
        return None
    ok = (not isinstance(value, bool) and isinstance(value, (int, float))
          and math.isfinite(value) and (value > lo if lo_open else value >= lo) and value <= hi)
    if not ok:
        raise ValueError(f'measurement.thickness_gauge.{where} must be {text}')
    return float(value)


def validate_thickness_gauge(g):
    bp.keys('measurement.thickness_gauge', g, GAUGE_REQUIRED, tuple(GAUGE_DEFAULTS))
    out = {'spot_length_m': _rng('spot_length_m', g['spot_length_m'], 0, 1, True, 'in (0, 1] m'),
           'time_constant_s': _rng('time_constant_s', g['time_constant_s'], 0, 10, False,
                                   'in [0, 10] s'),
           'sample_interval_s': _rng('sample_interval_s', g.get('sample_interval_s'), 0, 10,
                                     True, 'in (0, 10] s or null', True),
           'position_m': _rng('position_m', g.get('position_m'), 0, 10, False,
                              'on the barrel (in [0, 10] m and not beyond the barrel length) '
                              'or null', True),
           'spot_width_m': _rng('spot_width_m', g.get('spot_width_m'), 0, 1, True,
                                'in (0, 1] m or null', True)}
    pv = g['provenance']
    if not isinstance(pv, str) or not pv.strip():
        raise ValueError('measurement.thickness_gauge.provenance must be a nonempty string')
    out['provenance'] = pv
    return out


# ----------------------------------------------------------------------------- gauge transfer
# [D, re-derived in SPEC17; the gap row C7 names the effects without a source] A mark
# A*cos(2*pi*x/p) of pitch p passing at exit speed u has frequency f = u/p. Spot averaging over
# a length L keeps G_spot = |sin(pi*L/p)/(pi*L/p)|; a first-order response with time constant
# tau keeps G_tau = 1/sqrt(1 + (2*pi*f*tau)^2) (equivalent averaging length u*tau); sampling at
# dt aliases when f > 1/(2*dt). G = G_spot*G_tau.
GAUGE_RESOLVABLE_GAIN = 0.5    # [D, analyst choice] the gauge keeps less than half
GAUGE_FLAG_APPLIED = 'GAUGE_TRANSFER_APPLIED'
GAUGE_FLAG_LESS_THAN_HALF = 'GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK'
GAUGE_FLAG_NOT_DETECTED = 'GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE'
GAUGE_FLAG_BANDS = 'LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE'
GAUGE_FLAGS = (GAUGE_FLAG_APPLIED, GAUGE_FLAG_LESS_THAN_HALF, GAUGE_FLAG_NOT_DETECTED,
               GAUGE_FLAG_BANDS)
GAUGE_LIMITATIONS = (
    'The gauge keeps about the stated fraction of a mark: a spot average and a first-order lag '
    'only; real gauges have other filters (scanning frames, digital filters, noise), which are '
    'not modelled.',
    'No gauge noise, calibration or scanning-frame model.',
    'Accelerometer position and detection lead time (the third item of gap C7) have no formula '
    'in the reports and are not built.',
    'The evidence is not changed: "gauge variation not detected" counts in the tally exactly as '
    'without a gauge description (SPEC17 open decision 2).')


def spot_gain(spot_length_m, pitch_m):
    x = math.pi * spot_length_m / pitch_m
    return 1.0 if x == 0 else abs(math.sin(x) / x)


def time_constant_gain(time_constant_s, frequency_hz):
    return 1.0 / math.sqrt(1.0 + (2 * math.pi * frequency_hz * time_constant_s) ** 2)


def gauge_row(source, pitch_m, exit_speed_m_s, g):
    f = exit_speed_m_s / pitch_m
    gs, gt = spot_gain(g['spot_length_m'], pitch_m), time_constant_gain(g['time_constant_s'], f)
    dt = g['sample_interval_s']
    aliased = None if dt is None else f > 1 / (2 * dt)
    combined = gs * gt
    return {'source': source, 'pitch_m': pitch_m, 'exit_speed_m_s': exit_speed_m_s,
            'frequency_hz': f, 'spot_gain': gs, 'time_constant_gain': gt,
            'combined_gain': combined, 'aliased': aliased,
            'resolvable': combined >= GAUGE_RESOLVABLE_GAIN and not aliased}


def shortest_resolvable_pitch_m(g, exit_speed_m_s, lo=1e-4, hi=10.0):
    """Largest root of G(p) = 0.5 in [lo, hi] (pitches above it are resolvable); None when
    G(hi) < 0.5 or G never falls below 0.5 in the range."""
    def gain(p):
        return spot_gain(g['spot_length_m'], p) * time_constant_gain(g['time_constant_s'],
                                                                     exit_speed_m_s / p)
    if gain(hi) < GAUGE_RESOLVABLE_GAIN:
        return None
    n = 4000
    prev = hi
    for k in range(1, n + 1):
        p = hi * (lo / hi) ** (k / n)
        if gain(p) < GAUGE_RESOLVABLE_GAIN:
            a, b = p, prev               # gain(a) < 0.5 <= gain(b)
            for _ in range(200):
                m = 0.5 * (a + b)
                if gain(m) < GAUGE_RESOLVABLE_GAIN:
                    a = m
                else:
                    b = m
            return 0.5 * (a + b)
        prev = p
    return None


def thickness_gauge_section(case, result):
    g = case['measurement']['thickness_gauge']
    obs, u_op = case['observation'], case['pass']['exit_speed_m_s']
    rows = []
    for i, q in enumerate(obs.get('pitch_observations') or []):
        rows.append(gauge_row(f'pitch_observations[{i}]', q['pitch_m'], q['exit_speed_m_s'], g))
    n_obs = len(rows)
    fv = obs.get('measured_vibration_hz')
    if fv:
        rows.append(gauge_row('measured_vibration_hz', u_op / fv, u_op, g))
    ch = (result.get('chatter') or {}).get('with_bite_damping') if isinstance(
        result.get('chatter'), dict) else None
    fo = ch.get('onset_frequency_hz') if isinstance(ch, dict) else None
    if isinstance(fo, (int, float)) and not isinstance(fo, bool) and math.isfinite(fo) and fo > 0:
        rows.append(gauge_row('chatter.with_bite_damping.onset_frequency_hz', u_op / fo, u_op,
                              g))
    amp = obs.get('gauge_variation_amplitude_m')
    if amp is not None:
        for r in rows:
            if r['combined_gain'] > 0:
                r['amplitude_before_gauge_m'] = amp / r['combined_gain']
                r['amplitude_note'] = ('lower bound of the true amplitude if the mark has this '
                                       'pitch')
    flags = [GAUGE_FLAG_APPLIED]
    obs_rows = rows[:n_obs]
    if any(not r['resolvable'] for r in obs_rows):
        flags.append(GAUGE_FLAG_LESS_THAN_HALF)
    not_detected = (obs.get('gauge_variation_detected') is False and obs_rows
                    and not any(r['resolvable'] for r in obs_rows))
    if not_detected:
        flags.append(GAUGE_FLAG_NOT_DETECTED)
    # across the width
    pos, under, bands_exist = g['position_m'], None, False
    try:
        lay = spray_layout(case) if case.get('width_model') is not None else None
    except ValueError:
        lay = None
    if pos is None:
        pos = lay['strip_centre_m'] if lay else case['pass']['width_m'] / 2
    prof = next((p for p in shapemeter_profiles(result.get('width')) if p['name'] == 'steady'),
                None)
    if prof is not None and prof['bands']:
        bands_exist = True
        half = (g['spot_width_m'] or 0.0) / 2
        under = [{'start_m': b['start_m'], 'end_m': b['end_m'],
                  'peak_position_m': b['peak_position_m'], 'peak_i_units': b['peak_i_units']}
                 for b in prof['bands'] if b['start_m'] <= pos + half and b['end_m'] >= pos - half]
        if not under:
            flags.append(GAUGE_FLAG_BANDS)
    out = {'status': STATUS, 'not_supplied': False, 'provenance': g['provenance'],
           'spot_length_m': g['spot_length_m'], 'time_constant_s': g['time_constant_s'],
           'sample_interval_s': g['sample_interval_s'], 'position_m': pos,
           'spot_width_m': g['spot_width_m'], 'resolvable_gain': GAUGE_RESOLVABLE_GAIN,
           'resolvable_gain_basis': '[D, analyst choice] the gauge keeps less than half of the '
                                    'amplitude below it',
           'operating_exit_speed_m_s': u_op,
           'averaging_length_time_constant_m': u_op * g['time_constant_s'],
           'shortest_resolvable_pitch_m': shortest_resolvable_pitch_m(g, u_op),
           'rows': rows,
           'bands_under_gauge': under if bands_exist else None,
           'basis': {'transfer': '[D, re-derived in SPEC17] spot average |sin(pi*L/p)/(pi*L/p)| '
                                 'times first-order lag 1/sqrt(1 + (2*pi*f*tau)^2); aliased '
                                 'when f > 1/(2*dt)',
                     'response': 'foil gauge response under 10 ms [TM-LC24 VP]'},
           'flags': flags, 'limitations': list(GAUGE_LIMITATIONS)}
    if not_detected:
        out['not_detected_note'] = (
            '"Gauge variation not detected" carries no information here: the gauge keeps less '
            'than half of every observed mark pitch. The tally is NOT changed (the item counts '
            'as without a gauge description).')
    return out


def name_gauge_hypotheses(result):
    """After the hypotheses exist: name those whose evidence uses the gauge observation in
    the not-detected note (the tally itself is never changed)."""
    tg = (result.get('measurement') or {}).get('thickness_gauge')
    if not isinstance(tg, dict) or 'not_detected_note' not in tg:
        return
    ids = [h['id'] for h in result.get('hypotheses') or []
           if any(str(e.get('criterion', '')).startswith('gauge variation')
                  for e in h.get('evidence') or [])]
    tg['hypotheses_using_the_observation'] = ids
    tg['not_detected_note'] += (' Hypotheses whose evidence uses that observation: '
                                + (', '.join(ids) if ids else 'none') + '.')


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


def zone_weight_rows(z_m, strip_start_m, strip_end_m, edges):
    """The linear map of ``zone_means`` (SPEC19 package 4): per zone ``(row, coverage)``
    with ``zone_means(...)[j][0] = sum_i row[i]*values[i]`` (row None for a zone without
    strip); the same overlaps as ``zone_means``."""
    dz = z_m[1] - z_m[0] if len(z_m) > 1 else 0.0
    out = []
    for lo, hi in zip(edges, edges[1:]):
        a, b = max(lo, strip_start_m), min(hi, strip_end_m)
        if b <= a:
            out.append((None, 0.0))
            continue
        row, cov = [], 0.0
        for zi in z_m:
            cl, ch = max(zi - dz / 2, a), min(zi + dz / 2, b)
            ov = ch - cl if ch > cl else 0.0
            row.append(ov)
            cov += ov
        out.append(([v / cov for v in row] if cov > 0 else None, (b - a) / (hi - lo)))
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


def shapemeter_profiles(width, temperature_compensated=None):
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
    # SPEC17 package 6: the steady profile as measured hot (mechanical + thermal term)
    stt = width.get('strip_temperature')
    hot = ((stt.get('profiles') or {}).get('as_measured_hot')
           if isinstance(stt, dict) and not stt.get('not_supplied') else None)
    if isinstance(hot, dict) and isinstance(hot.get('i_units'), list) \
            and len(hot['i_units']) == len(stt.get('z_m') or []) and len(hot['i_units']) > 1:
        out.append({'name': 'steady_as_measured_hot',
                    'label': HOT_LABEL_COMPENSATED if temperature_compensated else HOT_LABEL,
                    'z_m': stt['z_m'], 'i_units': hot['i_units'], 'bands': hot['bands'],
                    'reporting_threshold_i_units': (st or {}).get(
                        'reporting_threshold_i_units') if isinstance(st, dict) else None})
    # SPEC19 package 2: roll growth plus the local film and flow-stress terms (and hot)
    lsrc = width.get('local_sources')
    if isinstance(lsrc, dict) and lsrc.get('status') == 'SCREENING_RESULT_NOT_PLANT_VALIDATED':
        for key, name, label in (
                ('mechanical_net', 'local_mechanical_net',
                 'roll growth plus film and flow-stress terms'),
                ('as_measured_hot', 'local_as_measured_hot',
                 'the same plus the strip temperature term')):
            pr = (lsrc.get('profiles') or {}).get(key)
            iu = lsrc.get(f'{key}_i_units')
            if isinstance(pr, dict) and isinstance(iu, list) and len(iu) == len(lsrc['z_m']):
                out.append({'name': name, 'label': label, 'z_m': lsrc['z_m'], 'i_units': iu,
                            'bands': pr['bands'],
                            'reporting_threshold_i_units': (st or {}).get(
                                'reporting_threshold_i_units') if isinstance(st, dict)
                            else None})
    # SPEC17 package 8: the measured roll ground profile (with feedback)
    rp = width.get('roll_profile')
    if isinstance(rp, dict) and isinstance(rp.get('z_m'), list) \
            and isinstance(rp.get('i_units_with_feedback'), list) \
            and len(rp['z_m']) == len(rp['i_units_with_feedback']) and len(rp['z_m']) > 1:
        out.append({'name': 'roll_ground_profile',
                    'label': 'measured roll ground profile (with exit-tension feedback)',
                    'z_m': rp['z_m'], 'i_units': rp['i_units_with_feedback'],
                    'bands': ((rp.get('levels') or {}).get('with_feedback') or {}).get('bands')
                    or [], 'reporting_threshold_i_units': 2.0})
    # SPEC17 package 7: one profile per supplied friction stripe (case pass, with feedback)
    fs = width.get('friction_stripes')
    for s in (fs.get('stripes') or []) if isinstance(fs, dict) else []:
        if isinstance(s.get('i_units'), list) and len(s['i_units']) == len(s.get('z_m') or []):
            out.append({'name': f'friction_stripe_{s["index"]}',
                        'label': ('friction stripe ' + (s.get('label') or str(s['index'] + 1))
                                  + f' ({100 * s["friction_change_fraction"]:+.3g} % friction)'),
                        'z_m': s['z_m'], 'i_units': s['i_units'], 'bands': s['bands'],
                        'reporting_threshold_i_units': s.get('reporting_threshold_i_units')})
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
    profiles = (shapemeter_profiles(result.get('width'), s['temperature_compensated'])
                if reason is None else [])
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
    if s['temperature_compensated'] and any(p['name'] == 'steady_as_measured_hot'
                                            for p in read):
        flags.append(FLAG_COMPENSATED)
    out.update(threshold_i_units=thr, threshold_basis=basis, profiles=read, flags=flags)
    return out


def measurement_section(case, result):
    """``result['measurement']``: not supplied without ``case['measurement']``."""
    m = case.get('measurement')
    if m is None:
        return bp.not_supplied('measurement is null or absent')
    sm = (bp.not_supplied('measurement.shapemeter is null or absent')
          if m.get('shapemeter') is None else shapemeter_section(case, result))
    tg = (bp.not_supplied('measurement.thickness_gauge is null or absent')
          if m.get('thickness_gauge') is None else thickness_gauge_section(case, result))
    flags = list(sm.get('flags') or []) + list(tg.get('flags') or [])
    return {'status': STATUS, 'not_supplied': False, 'shapemeter': sm, 'thickness_gauge': tg,
            'flags': flags, 'limitations': list(LIMITATIONS)}
