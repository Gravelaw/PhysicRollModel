"""SPEC14 Part 3: sensitivity of the cooling-stripe result to the heat partition and the spray
coefficient (``width.thermal_sensitivity``).

The tool's cooling-stripe statements rest on two supplied inputs that the literature does not
pin down: the strip share of the bite heat (the battery demo used 0.84; the only measured
foil-mill partition gives 0.11-0.33 to the strip [PT-T16, abstract only, a net balance]) and the
spray heat-transfer coefficient (simulated 2.5-4.3 kW/m2K for kerosene on a work roll [PT-T18];
about 5-13 kW/m2K computed from a plate test [PT-T19]). This block re-evaluates the planted
stripe across those values.

Linearity relied on (stated in the result): for a fixed spray coefficient the roll thermal
model is linear in the heat entering the roll, with the coolant temperature as the zero of the
radius growth, so the stripe (actual header minus healthy header) and every event history scale
exactly with the roll heat share per roll; this is checked in the block by one direct solve.
The onset heights depend only on the stripe's shape, not on its height. A different spray
coefficient changes the shape and is solved again (steady state, onsets and event transients),
which costs a few seconds, so the spray-coefficient rows are computed only with
``model_options.thermal_sensitivity: "full"``; the default ``"partition"`` gives the heat-partition
rows at the case spray coefficient (the case's own onsets reused). The flatness states are recomputed for
every combination (they are not linear). Pass-heating strip temperature rises scale with the
strip share (``bite_tribology.pass_heating``: strip heat = share x bite heat).
"""
import math
from dataclasses import replace

from . import band_products as bp
from . import roll_thermal as rt

MODES = ('off', 'partition', 'full')
DEFAULT_MODE = 'partition'     # cheap: heat-partition rows at the case spray coefficient
MEASURED_STRIP_SHARES = (0.33, 0.11)        # PT-T16 measured range, high and low
PREVIOUS_DEMO_STRIP_SHARE = 0.84            # the demos' value before SPEC14 (both demos)
PUBLISHED_SPRAY_HTC = ((2500.0, 'published low, simulated kerosene on a work roll [PT-T18]'),
                       (4300.0, 'published high, simulated kerosene on a work roll [PT-T18]'),
                       (13000.0, 'upper end computed from a plate test (oil 3-6 x below '
                                 'water) [PT-T19]; not a roll'))
PREVIOUS_DEMO_SPRAY_HTC = 2000.0            # the battery demo's value before SPEC14
LINEARITY_TOLERANCE = 1e-6


def share_to_fraction(share):
    """Strip share of the bite heat -> roll heat fraction per work roll, as the engine uses it:
    (1 - strip share) / 2 (two work rolls share the rest equally)."""
    return (1.0 - share) / 2.0


def fraction_to_share(fraction):
    return 1.0 - 2.0 * fraction


def _time_above(times, dev, thr):
    """Total time with dev > thr (linear interpolation between records)."""
    if thr is None:
        return None
    tot = 0.0
    for (t0, d0), (t1, d1) in zip(zip(times, dev), zip(times[1:], dev[1:])):
        a, b = d0 > thr, d1 > thr
        if a and b:
            tot += t1 - t0
        elif a != b and d1 != d0:
            tc = t0 + (thr - d0) / (d1 - d0) * (t1 - t0)
            tot += (t1 - tc) if b else (tc - t0)
    return tot


def _state(states):
    fb = states['with_feedback']
    return fb['state'], fb['state_after_tension_release'], fb['peak_i_units']


def _largest(steady_like, th, bw):
    z = steady_like['z_m']
    stripes = steady_like['stripes']
    if not stripes:
        return None
    return max(stripes, key=lambda s: abs(s['peak_deviation_m']))


def _variant(th, htc, bw):
    """Steady healthy / actual / deviation and the largest stripe for another spray HTC."""
    th2 = _copy_thermal(th, htc)
    healthy = th2.steady([1.0] * th2.count)
    actual = healthy if all(v == 1.0 for v in th2.levels) else th2.steady(th2.levels)
    z = actual['z_m']
    dev = [a - b for a, b in zip(actual['radius_growth_m'], healthy['radius_growth_m'])]
    idx = bw._inside(z, th2.centre, th2.width)
    stripes = bw._runs([z[i] for i in idx], [dev[i] for i in idx], bw.STRIPE_THRESHOLD_M)
    return th2, healthy, actual, {'z_m': z, 'local_deviation_m': dev, 'stripes': stripes,
                                  'thermal_crown_m': actual['thermal_crown_m']}


def _copy_thermal(th, htc):
    import copy
    th2 = copy.copy(th)
    th2.header = replace(th.header, spray_mean_htc_w_m2k=htc)
    return th2


_EV_KEYS = ('peak_deviation_m', 'manifest_threshold_m', 'released_threshold_m',
           'peak_state_with_feedback', 'peak_state_after_tension_release', 'visible_time_s',
           'visible_time_basis', 'visible_time_lower_bound_s', 'time_above_manifest_threshold_s',
           'time_above_released_threshold_s', 'band_life_s', 'band_life_lower_bound_s')


def _event_rows(ev_section, scale):
    """Per event, the event section's own metrics at this roll heat scale: scale 1 is the event
    as simulated (the section's values, unchanged), any other scale its ``scaled`` entry, both
    from ``band_width.event_metrics`` (signed, on the event's own sign)."""
    rows = []
    for e in (ev_section or {}).get('events') or []:
        if abs(scale - 1.0) <= 1e-12:
            src = e
        else:
            src = next((x for x in e.get('scaled') or [] if abs(x['scale'] - scale) <= 1e-12),
                       None)
            if src is None:
                continue
        row = {'label': e['label'], 'sign': 'HEATING' if e['peak_deviation_m'] >= 0
               else 'COOLING'}
        row.update({k: src.get(k) for k in _EV_KEYS})
        row['in_mill'] = row['peak_state_with_feedback']
        row['after_release'] = row['peak_state_after_tension_release']
        man = row['manifest_threshold_m']
        row['ratio_peak_to_in_mill_threshold'] = (
            None if not man or row['peak_deviation_m'] is None
            else abs(row['peak_deviation_m']) / abs(man))
        rows.append(row)
    return rows


def share_rows(case_frac):
    """(share, basis) rows: the case value, the measured high and low, the demos' former value."""
    shares = [(fraction_to_share(case_frac), 'case value')]
    for s, why in ((MEASURED_STRIP_SHARES[0], 'measured high [PT-T16, abstract only, net '
                    'balance]'), (MEASURED_STRIP_SHARES[1], 'measured low [PT-T16, abstract '
                                  'only, net balance]'),
                   (PREVIOUS_DEMO_STRIP_SHARE, 'the demos\' value before SPEC14')):
        if all(abs(s - x) > 1e-9 for x, _ in shares):
            shares.append((s, why))
    return shares


def event_scales(case, case_frac):
    """Roll-heat scale factors the event section must also evaluate (None: no block)."""
    mode = case['model_options'].get('thermal_sensitivity', DEFAULT_MODE)
    if mode == 'off' or not case_frac or case_frac <= 0:
        return None
    return [share_to_fraction(s) / case_frac for s, _ in share_rows(case_frac)[1:]]


def thermal_sensitivity(case, w, th, sp, steady, actual, events_out, bw, stripe_table=None):
    """The sensitivity block (see the module docstring). ``bw`` is ``band_width``."""
    mode = case['model_options'].get('thermal_sensitivity', DEFAULT_MODE)
    if mode == 'off':
        return bw.not_supplied('model_options.thermal_sensitivity is "off"')
    if steady is None or actual is None or th.bite_heat is None:
        return bw.not_assessable('no steady roll thermal state (bite heat not available)')
    if sp is None:
        return bw.not_assessable('no shape parameters (no bite and no shape inputs)')
    case_frac = th.fraction
    if not case_frac > 0 or not th.bite_heat > 0:
        return bw.not_assessable(
            'the case puts no heat into the roll (roll heat fraction per roll '
            f'{case_frac:g}, bite heat {th.bite_heat:g} W/m): a zero baseline has nothing to '
            'scale; give a non-zero roll heat fraction to see the sensitivity')
    case_share = fraction_to_share(case_frac)
    case_htc = th.header.spray_mean_htc_w_m2k
    shares = share_rows(case_frac)
    scales = [share_to_fraction(s) / case_frac for s, _ in shares]
    htcs = [(case_htc, 'case value')]
    if mode == 'full':
        for h, why in PUBLISHED_SPRAY_HTC + ((PREVIOUS_DEMO_SPRAY_HTC, 'the battery demo\'s '
                                              'value before SPEC14'),):
            if all(abs(h - x) > 1e-6 for x, _ in htcs):
                htcs.append((h, why))
    # linearity check: one direct solve at the first other share, case HTC
    lin = None
    if len(shares) > 1:
        f2 = share_to_fraction(shares[1][0])
        th2 = _copy_thermal(th, case_htc)
        th2.fraction = f2
        h2 = th2.steady([1.0] * th2.count)
        a2 = h2 if all(v == 1.0 for v in th2.levels) else th2.steady(th2.levels)
        d2 = [a - b for a, b in zip(a2['radius_growth_m'], h2['radius_growth_m'])]
        k = f2 / case_frac
        ref = max(abs(v) for v in d2)
        if ref > 0:
            lin = max(abs(p - k * q) for p, q in zip(d2, steady['local_deviation_m'])) / ref
    rows, htc_info = [], []
    for htc, hwhy in htcs:
        if htc == case_htc:
            st, ev = steady, events_out
            ev_basis = ('the event section itself; other shares from its scaled entries '
                        '(band_width.event_metrics)') if w['events'] else 'no width_model.events'
        else:
            th2, _, act2, st = _variant(th, htc, bw)
            ev, ev_basis = None, 'no width_model.events'
            if w['events']:
                try:
                    ev = bw._events_section(th2, sp, act2, w['events'], scales=scales[1:])
                    ev_basis = 'event transient rerun at this spray coefficient'
                except ValueError as exc:
                    ev_basis = f'event transient failed: {exc}'
        s0 = _largest(st, th, bw)
        info = {'spray_htc_w_m2k': htc, 'basis': hwhy, 'event_basis': ev_basis,
                'thermal_crown_at_case_share_m': st['thermal_crown_m']}
        on = None
        if s0 is not None:
            z, dev = st['z_m'], st['local_deviation_m']
            pk = abs(s0['peak_deviation_m'])
            reuse = next((t for t in (stripe_table or []) if htc == case_htc
                          and abs(t['position_m'] - s0['peak_position_m']) < 1e-12
                          and 'manifest_onset_peak_height_m' in t), None)
            if reuse is not None:      # the case's own onsets (same stripe, same shape)
                on = {k: (None if reuse[key] is None else reuse[key] / pk)
                      for k, key in (('mill', 'manifest_onset_peak_height_m'),
                                     ('released', 'released_onset_peak_height_m'))}
            else:
                on = bw.onsets(z, bw._isolate(z, dev, s0), sp)
            info.update({'stripe_position_m': s0['peak_position_m'],
                         'stripe_sign': 'HOT_HIGH' if s0['peak_deviation_m'] > 0 else 'COLD_LOW',
                         'stripe_peak_at_case_share_m': s0['peak_deviation_m'],
                         'in_mill_onset_height_m': None if on['mill'] is None
                         else on['mill'] * pk,
                         'after_release_onset_height_m': None if on['released'] is None
                         else on['released'] * pk})
        else:
            info['largest_stripe'] = None
        htc_info.append(info)
        for (share, swhy), k in zip(shares, scales):
            row = {'strip_heat_share': share, 'share_basis': swhy,
                   'roll_heat_fraction_per_roll': share_to_fraction(share),
                   'spray_htc_w_m2k': htc, 'spray_basis': hwhy,
                   'thermal_crown_m': st['thermal_crown_m'] * k,
                   'events': _event_rows(ev, k) if ev is not None else None}
            if s0 is None:
                row.update(status='NO_STEADY_STRIPE_ABOVE_THRESHOLD', stripe_peak_m=0.0,
                           state_in_mill=None, state_after_tension_release=None)
            else:
                sd = [v * k for v in dev]
                lv = bw.shape_levels(z, sd, sp)
                mill, rel, iu = _state(bw.stripe_states(lv, s0['peak_position_m']))
                peak = pk * k                      # magnitude; the sign is in stripe_sign
                m_on = None if on['mill'] is None else on['mill'] * pk
                r_on = None if on['released'] is None else on['released'] * pk
                row.update({
                    'status': 'EVALUATED', 'stripe_position_m': s0['peak_position_m'],
                    'stripe_sign': info['stripe_sign'], 'stripe_peak_m': peak,
                    'stripe_peak_on_diameter_m': 2 * peak,
                    'with_feedback_i_units': iu,
                    'linear_feedback_i_units': lv['linear_feedback_peak_i_units'],
                    'state_in_mill': mill, 'state_after_tension_release': rel,
                    'in_mill_onset_height_m': m_on, 'after_release_onset_height_m': r_on,
                    'ratio_stripe_to_in_mill_onset': None if not m_on else peak / m_on,
                    'ratio_stripe_to_after_release_onset': None if not r_on else peak / r_on})
            rows.append(row)
    base = rows[0]
    changed = []
    for r in rows[1:]:
        what = [f'steady stripe {k}' for k in ('state_in_mill', 'state_after_tension_release')
                if r[k] != base[k]]
        for e0, e1 in zip(base['events'] or [], r['events'] or []):
            for k in ('in_mill', 'after_release'):
                if e0[k] != e1[k]:
                    what.append(f'event {e0["label"]} {k}')
        if what:
            changed.append({'strip_heat_share': r['strip_heat_share'],
                            'spray_htc_w_m2k': r['spray_htc_w_m2k'], 'changes': what})
    build = None
    if mode == 'full' and rows[0]['status'] == 'EVALUATED':
        try:
            build = steady_build_up(th, rows[0]['stripe_position_m'])
        except ValueError as exc:
            build = {'status': 'FAILED', 'error': str(exc)}
    pid = case['material'].get('product') or 'battery_collector_foil'
    try:
        check = bp.check_thermal(pid, strip_heat_fraction=case_share if 0 <= case_share <= 1
                                 else None, spray_htc_w_m2k=case_htc if case_htc > 0 else None)
    except ValueError as exc:
        check = [{'item': 'check_thermal', 'verdict': 'NO_PUBLISHED_RANGE', 'note': str(exc)}]
    return {
        'status': 'EVALUATED', 'not_supplied': False, 'mode': mode,
        'spray_rows_note': (None if mode == 'full' else
                            'spray-coefficient rows not computed: set '
                            'model_options.thermal_sensitivity to "full" (a few seconds)'),
        'case_strip_heat_share': case_share, 'case_roll_heat_fraction_per_roll': case_frac,
        'case_spray_htc_w_m2k': case_htc,
        'share_conversion': 'roll heat fraction per work roll = (1 - strip share) / 2',
        'shares': [{'strip_heat_share': s, 'roll_heat_fraction_per_roll': share_to_fraction(s),
                    'basis': b} for s, b in shares],
        'spray_coefficients': htc_info, 'rows': rows,
        'combinations_changing_a_state': changed,
        'steady_build_up': build,
        'linearity_check_max_relative_difference': lin,
        'linearity_note': ('stripe and event histories scaled with the roll heat share for a '
                           'fixed spray coefficient (linear roll thermal model, coolant '
                           'temperature as the zero); checked by one direct solve: maximum '
                           f'relative difference {lin:.2g}' if lin is not None else
                           'linearity not checked (no stripe in the direct solve)'),
        'literature_check_of_case_inputs': check,
        'note': ('The heat partition [PT-T16] was read as an abstract only and is a net balance '
                 '(not necessarily the split inside the bite); the spray coefficients are '
                 'simulated [PT-T18] or computed from a plate test [PT-T19]. Model '
                 'sensitivities, not plant data.')}


BUILD_UP_S = 1800.0


def steady_build_up(th, x):
    """Time for the steady stripe to build up from a healthy header (case pass, case inputs):
    one transient with the case nozzle levels from the healthy steady state, monitored at the
    stripe peak; times to 50, 63, 90 and 95 % of the steady stripe."""
    healthy = th.steady([1.0] * th.count)
    actual = th.steady(th.levels)
    z = actual['z_m']
    g0 = rt._interp(z, healthy['radius_growth_m'], x)
    target = rt._interp(z, actual['radius_growth_m'], x) - g0
    step = th.numerics['time_step_s']
    times = [k * 10.0 for k in range(int(BUILD_UP_S / 10.0) + 1)]
    sim = rt.simulate(th.roll, th.header, [th.segment(th.levels, BUILD_UP_S)], initial=healthy,
                      time_step_s=step, record_times_s=times, monitor_positions_m=[x], **th.kw)
    mon = sim['monitors'][0]
    dev = [v - g0 for v in mon['radius_growth_m']]
    out = {'status': 'EVALUATED', 'stripe_position_m': x, 'steady_stripe_m': target,
           'simulated_s': BUILD_UP_S,
           'basis': 'transient from the healthy steady state with the case nozzle levels, '
                    'monitor at the stripe peak (case pass, case heat share and spray)'}
    for f in (0.5, 0.632, 0.9, 0.95):
        t = None
        if target:
            prev = (mon['time_s'][0], 0.0)
            for tt, d in zip(mon['time_s'], dev):
                if d / target >= f:
                    t0, f0 = prev
                    f1 = d / target
                    t = tt if f1 == f0 else t0 + (f - f0) / (f1 - f0) * (tt - t0)
                    break
                prev = (tt, d / target)
        out[f'time_to_{int(round(f * 100))}_percent_s'] = t
    out['fraction_at_end'] = dev[-1] / target if target else None
    return out


def strip_rise_at_share(h, share):
    """Strip temperature rise of a pass-heating row at another strip share. The row was
    computed with ITS OWN strip fraction (``tribology.strip_heat_fraction``), which need not be
    the width model's share; rise = share x Q / (rho c h u) is linear in the share, so it is
    rescaled from the row's own fraction, or recomputed from the heat input when that is 0."""
    fs = h.get('strip_heat_fraction')
    if fs:
        return h['strip_temperature_rise_k'] * share / fs
    from .bite_tribology import ALUMINIUM_VOLUMETRIC_HEAT_CAPACITY_J_M3K as rho_c
    return share * h['bite_heat_per_width_w_m'] / (rho_c * h['exit_thickness_m']
                                                    * h['exit_speed_m_s'])


HEAT_PARTITION_FLAG = 'HEAT_PARTITION_INPUTS_INCONSISTENT'


def heat_partition_consistency(case):
    """None when consistent (or only one input given); else the two values and who uses which.
    The roll thermal model uses width_model.roll_heat_fraction_per_roll; pass heating uses
    tribology.strip_heat_fraction; leaving the former null derives it from the latter."""
    w, trib = case.get('width_model'), case.get('tribology')
    if not w or not trib or w.get('roll_heat_fraction_per_roll') is None:
        return None
    f_w, fs = w['roll_heat_fraction_per_roll'], trib['strip_heat_fraction']
    if abs(f_w - share_to_fraction(fs)) <= 1e-9:
        return None
    return {'flag': HEAT_PARTITION_FLAG,
            'width_model_roll_heat_fraction_per_roll': f_w,
            'width_model_strip_share_equivalent': fraction_to_share(f_w),
            'tribology_strip_heat_fraction': fs,
            'tribology_roll_heat_fraction_per_roll_equivalent': share_to_fraction(fs),
            'text': (f'The two heat-partition inputs disagree: the roll thermal model (stripes, '
                     f'crown, events) uses width_model.roll_heat_fraction_per_roll {f_w:.3g} '
                     f'(strip share {fraction_to_share(f_w):.3g}); pass heating (strip '
                     f'temperatures) uses tribology.strip_heat_fraction {fs:.3g} (roll fraction '
                     f'{share_to_fraction(fs):.3g} per roll). Neither is changed; leave '
                     'width_model.roll_heat_fraction_per_roll null to derive it from '
                     'tribology.strip_heat_fraction.')}


def attach_per_pass(result):
    """Per-pass stripe-to-onset ratio and strip exit temperature for each strip share (case
    spray coefficient), from the gauge-trend onsets and the pass-heating rows; the stripe at a
    pass is the case-pass stripe scaled by that pass's bite heat (same shape, linear model)."""
    w = result.get('width') or {}
    ts = w.get('thermal_sensitivity')
    if not isinstance(ts, dict) or ts.get('status') != 'EVALUATED':
        return
    heating = (result.get('process') or {}).get('heating') or {}
    gt = w.get('gauge_trend') or {}
    if not isinstance(heating, dict) or 'operating' not in heating or not gt.get('rows'):
        ts['per_pass'] = None
        ts['per_pass_note'] = 'no pass-heating schedule or gauge trend to combine'
        return
    op = heating['operating']
    by_label = {x['label']: x for x in heating.get('schedule') or []}
    base_row = next((r for r in ts['rows'] if r['strip_heat_share'] == ts['case_strip_heat_share']
                     and r['spray_htc_w_m2k'] == ts['case_spray_htc_w_m2k']), None)
    if base_row is None or base_row['status'] != 'EVALUATED':
        ts['per_pass'] = None
        return
    case_share, peak0 = ts['case_strip_heat_share'], base_row['stripe_peak_m']
    out = []
    for g in gt['rows']:
        h = by_label.get(g['label'])
        if h is None and abs(g['exit_thickness_m'] - op['exit_thickness_m']) < 1e-12:
            h = op
        heat = None if h is None else h.get('bite_heat_per_width_w_m')
        if not op.get('bite_heat_per_width_w_m'):
            heat = None                           # zero case-pass heat: nothing to scale
        for s in ts['shares']:
            share = s['strip_heat_share']
            k = share_to_fraction(share) / ts['case_roll_heat_fraction_per_roll']
            stripe = (None if heat is None else
                      peak0 * k * heat / op['bite_heat_per_width_w_m'])
            on = g.get('manifest_onset_stripe_height_m')
            ron = g.get('released_onset_stripe_height_m')
            rise = None if h is None else strip_rise_at_share(h, share)
            t_exit = None if h is None else h['entry_temperature_k'] + rise
            out.append({'label': g['label'], 'exit_thickness_m': g['exit_thickness_m'],
                        'strip_heat_share': share, 'bite_heat_per_width_w_m': heat,
                        'stripe_peak_m': stripe, 'in_mill_onset_height_m': on,
                        'after_release_onset_height_m': ron,
                        'ratio_stripe_to_in_mill_onset': (None if stripe is None or not on
                                                          else stripe / on),
                        'ratio_stripe_to_after_release_onset': (None if stripe is None
                                                                or not ron else stripe / ron),
                        'strip_exit_temperature_c': None if t_exit is None else t_exit - 273.15,
                        'above_battery_coil_limit_80c': (None if t_exit is None
                                                         else t_exit - 273.15 > 80.0)})
    ts['per_pass'] = out
    own = [r for r in out if r['strip_heat_share'] == case_share]
    man = [r['label'].split()[0] for r in own if (r['ratio_stripe_to_in_mill_onset'] or 0) >= 1]
    lat = [r['label'].split()[0] for r in own if r['ratio_stripe_to_in_mill_onset'] is not None
           and r['ratio_stripe_to_in_mill_onset'] < 1]
    ts['per_pass_text'] = (
        'Two questions, two answers. The gauge trend holds the case-pass stripe '
        f'({peak0 * 1e6:.3g} um) unchanged on every pass. The stripe each pass would itself '
        'produce scales with that pass\'s bite heat (same spray, same nozzle, steady state; the '
        'roll needs minutes to reach it, radial time constant about 4-7 min computed for a '
        '260 mm roll [PT-T25]): at the case heat share it would '
        + (f'buckle in the mill on {", ".join(man)}' if man else 'buckle in the mill on no pass')
        + (f' and stay latent on {", ".join(lat)}' if lat else '') + '.')
    # beside the gauge-trend text (which band_diagnosis may rebuild for credibility)
    gt['own_stripe_text'] = ('The text above holds the case-pass stripe on every pass. '
                             + ts['per_pass_text'].split('. ', 2)[-1]
                             + ' (width.thermal_sensitivity.per_pass)')
    ts['per_pass_note'] = (
        'Stripe at a pass = the case-pass stripe x (that pass\'s bite heat / the case pass\'s) x '
        '(roll share / case roll share), at the case spray coefficient (linear model, same '
        'stripe shape); onsets from the gauge trend (the case stripe\'s shape at each pass). '
        'Strip exit temperature = entry + pass-heating rise x (share / the strip fraction that '
        'pass-heating row used, tribology.strip_heat_fraction); a strip '
        'exit temperature is not a coil temperature (the 80 C battery limit is for the coil '
        '[PT-T1]), and the experimental mattress bite inflates friction heat.')


# --------------------------------------------------------------------------- thermal_check
PROPERTY_RISK_FLAG = 'MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT'
EXIT_IS_NOT_COIL = ('A modelled strip exit temperature is not a coil temperature (the '
                    'published limits are for the coil, PT-T1), and the experimental mattress '
                    'bite inflates friction heat; read these as indicators.')
NO_PROPERTY_MODEL = ('The tool has no model of property change after rolling, no roll-wear '
                     'model and no temperature-to-surface-finish model; the statements here are '
                     'literature statements, not model outputs.')
QUARTER_BARREL = (0.20, 0.25)
SHEET_FROM_M = 100e-6          # the engine's foil-regime threshold (band_width.FOIL_GAUGE_M)


def _k_to_c(k):
    return None if k is None else k - 273.15


def thermal_check(result, case):
    """SPEC14 Part 2: the case's thermal inputs and the modelled thermal outputs against the
    process-temperature literature (``band_products.check_thermal``). Evidence-neutral: it
    never changes a number or a score. Returns None for a v1 case or a case without any
    thermal section (results unchanged)."""
    w, trib = case.get('width_model'), case.get('tribology')
    if case.get('case_schema') != 'physicroll.band_case.v2':
        return None
    if w is None and trib is None:
        return {'status': 'NOT_SUPPLIED', 'not_supplied': True,
                'reason': 'no width_model and no tribology: nothing thermal in the case'}
    pid = case['material'].get('product')
    sheet = case['pass']['exit_thickness_m'] >= SHEET_FROM_M
    # without a product the general foil ranges apply ('household_foil' stands for any
    # non-battery foil in check_thermal: it selects the general finishing-oil range only)
    prod = pid or 'household_foil'
    collector = pid in bp.THERMAL_COLLECTOR_PRODUCTS

    def lit(f):
        if sheet and f['verdict'] != 'NO_PUBLISHED_RANGE':
            f['verdict_against_foil_literature'] = f['verdict']
            f['verdict'] = 'NO_PUBLISHED_RANGE'
            f['basis'] += ('; the case pass is sheet gauge and the literature has foil-mill data '
                           'only (verdict against the foil range kept beside)')
        return f
    flags, inputs, outputs, texts = [], [], [], []
    width = result.get('width') if isinstance(result.get('width'), dict) else {}
    ts = width.get('thermal_sensitivity') if isinstance(width, dict) else None
    # ---- inputs
    used = (width.get('inputs_used') or {}) if isinstance(width, dict) else {}
    frac = used.get('roll_heat_fraction_per_roll')
    if frac is not None:
        share = fraction_to_share(frac)
        basis = used.get('roll_heat_fraction_basis') or ''
    elif trib is not None:
        share, basis = trib['strip_heat_fraction'], 'tribology.strip_heat_fraction'
        frac = share_to_fraction(share)
    else:
        share = None
    if share is not None and 0 <= share <= 1:
        f = lit(bp.check_thermal(prod, strip_heat_fraction=share)[0])
        f['conversion'] = (f'strip share {share:.3g} <-> roll heat fraction per work roll '
                           f'{frac:.3g} = (1 - strip share) / 2 ({basis})')
        inputs.append(f)
    if w is not None:
        htc = w['spray_header']['spray_mean_htc_w_m2k']
        if htc > 0:
            # simulated on an aluminium cold mill [PT-T18]: not foil-only, no sheet caveat
            inputs.append(bp.check_thermal(prod, spray_htc_w_m2k=htc)[0])
        t_c = _k_to_c(w.get('coolant_temperature_k'))
        if t_c is not None:
            f = lit(bp.check_thermal(prod, oil_supply_temperature_c=t_c, stand='finishing')[0])
            f['item'] = 'coolant_temperature_as_oil_supply'
            f['note'] = ((f.get('note') or '') + '; width_model.coolant_temperature_k read as the '
                         'oil supply temperature of a finishing (foil) pass').strip('; ')
            inputs.append(f)
    if trib is not None and trib.get('inlet_temperature_k') is not None:
        f = lit(bp.check_thermal(prod, oil_supply_temperature_c=_k_to_c(
            trib['inlet_temperature_k']), stand='finishing')[0])
        f['item'] = 'oil_inlet_temperature'
        inputs.append(f)
    lub = (trib or {}).get('lubricant') or {}
    if lub.get('viscosity_ref_pa_s') is not None:
        inputs.append({
            'item': 'oil_viscosity_40c', 'value': lub['viscosity_ref_pa_s'],
            'published_low': bp.VISC_40C.low, 'published_high': bp.VISC_40C.high,
            'unit': 'Pa s (case, dynamic) / m^2/s (literature, kinematic)',
            'verdict': 'NO_PUBLISHED_RANGE',
            'basis': ('the case gives a dynamic viscosity at '
                      f'{_k_to_c(lub.get("reference_temperature_k")) or 0:.4g} C; the '
                      'literature gives kinematic viscosity at 40 C (1.5-2.0 cSt); the oil '
                      'density needed to convert is not a case input, so no verdict'),
            'sources': list(bp.VISC_40C.sources),
            'read_status': bp.VISC_40C.effective_read_status(), 'note': ''})
    # spray overlap against the published 10-30 % (never above 50 %)
    cov = (result.get('screens') or {}).get('spray_coverage') if isinstance(
        result.get('screens'), dict) else None
    ov = cov.get('overlap_fraction') if isinstance(cov, dict) else None
    if ov is None and w is not None:
        h = w['spray_header']
        wf = 2 * h['standoff_m'] * math.tan(h['spray_angle_rad'] / 2) * math.cos(
            h['offset_angle_rad'])
        ov = (wf - h['nozzle_pitch_m']) / wf if wf > 0 else None
    if ov is not None:
        o_rng, o_max = bp.SPRAY_OVERLAP.values[0], bp.SPRAY_OVERLAP.values[1]
        v = ('ABOVE_PUBLISHED_LIMIT' if ov > o_max.high + 1e-12 else
             'BELOW_PUBLISHED_RANGE' if ov < o_rng.low - 1e-12 else
             'ABOVE_PUBLISHED_RANGE' if ov > o_rng.high + 1e-12 else 'WITHIN_PUBLISHED_RANGE')
        inputs.append({
            'item': 'spray_footprint_overlap', 'value': ov, 'published_low': o_rng.low,
            'published_high': o_rng.high, 'unit': 'fraction', 'verdict': v,
            'basis': ('footprint overlap (W_eff - pitch) / W_eff of the spray screen against the '
                      'published 10-30 %, never above 50 % [PT-T22, PT-T21]; the spray screen '
                      'itself has no overlap threshold (it only flags gaps between fans)'),
            'sources': list(bp.SPRAY_OVERLAP.sources),
            'read_status': bp.SPRAY_OVERLAP.effective_read_status(), 'note': ''})
    # ---- outputs: strip exit temperature per pass (reused from thermal_sensitivity.per_pass)
    pc = result.get('product_check') if isinstance(result.get('product_check'), dict) else {}
    finals = set(pc.get('final_pass_labels') or [])
    # the pass-heating rows themselves (computed with tribology.strip_heat_fraction, the
    # input pass heating uses; the same numbers thermal_sensitivity.per_pass rescales)
    rows = []
    heat = (result.get('process') or {}).get('heating') if isinstance(
        result.get('process'), dict) else None
    if isinstance(heat, dict) and 'operating' in heat:
        src = list(heat.get('schedule') or []) or [heat['operating']]
        for h in src:
            rows.append((h['label'], _k_to_c(h['exit_temperature_k']), h['label'] in finals))
    temps = []
    for label, t, final in rows:
        if collector:
            f = bp.check_thermal(prod, coil_temperature_leaving_final_pass_c=t)[0]
            f['item'] = 'modelled_strip_exit_temperature'
        else:
            f = {'item': 'modelled_strip_exit_temperature', 'value': t, 'published_low': None,
                 'published_high': None, 'unit': 'degC', 'verdict': 'NO_PUBLISHED_RANGE',
                 'basis': 'no coil temperature limit published for this product', 'sources': [],
                 'read_status': None, 'note': ''}
        f['label'] = label
        f['is_final_pass'] = final
        f['above_90c'] = t > bp.COIL_OUT_FINAL_LIMIT_LOOSE.high
        temps.append(f)
    risk = [f for f in temps if collector and f['verdict'] == 'ABOVE_PUBLISHED_LIMIT'
            and (f['is_final_pass'] or not finals)]
    property_risk = None
    if risk:
        flags.append(PROPERTY_RISK_FLAG)
        decay = next(s for s in bp.PT_MATERIAL if s.topic == 'battery_property_decay')
        property_risk = {
            'passes': [f['label'] for f in risk],
            'literature_statement': decay.text, 'sources': list(decay.sources),
            'note': EXIT_IS_NOT_COIL + ' ' + NO_PROPERTY_MODEL}
    # ---- outputs: stripe height, thermal crown, growth times
    st = width.get('thermal_steady') if isinstance(width, dict) else None
    if isinstance(st, dict) and st.get('stripes') is not None:
        big = max(st['stripes'], key=lambda x: abs(x['peak_deviation_m']), default=None)
        if big is not None:
            f = bp.check_thermal(prod, stripe_height_diameter_m=2 * abs(big['peak_deviation_m']))[0]
            f['note'] = (f'largest steady stripe {abs(big["peak_deviation_m"]) * 1e6:.3g} um on '
                         'radius (x2 on diameter) at '
                         f'{big["peak_position_m"]:.4g} m; ' + f['note'])
            outputs.append(f)
        crown = st.get('thermal_crown_m')
        if crown is not None:
            f = bp.check_thermal(prod, thermal_crown_m=abs(2 * crown))[0]
            f['note'] = (f'model thermal crown {crown * 1e6:.3g} um on radius, {2 * crown * 1e6:.3g}'
                         ' um on diameter (compared); the published 30 um does not say whether '
                         'it is on diameter or radius')
            outputs.append(f)
    ev = (width.get('thermal_events') or {}).get('events') if isinstance(
        width.get('thermal_events'), dict) else None
    tau = bp.AXIAL_TAU.low
    growth = {'axial_decay_time_constant_s': tau, 'radial_time_constant_s':
              [bp.RADIAL_TAU.low, bp.RADIAL_TAU.high],
              'sources': ['PT-T18', 'PT-T25'], 'read_status': 'computed'}
    if ev:
        growth['event_time_to_half_peak_s'] = [e.get('time_to_half_peak_s') for e in ev]
    build = (ts or {}).get('steady_build_up') if isinstance(ts, dict) else None
    if isinstance(build, dict) and build.get('status') == 'EVALUATED':
        growth['steady_build_up'] = {k: build[k] for k in build if k.startswith('time_to_')}
    parts = []
    if ev and growth['event_time_to_half_peak_s'][0] is not None:
        parts.append(f'the short event reaches half its peak in '
                     f'{growth["event_time_to_half_peak_s"][0]:.3g} s (axial decay time constant '
                     f'of a 52 mm stripe about {tau:.0f} s, computed)')
    if 'steady_build_up' in growth and growth['steady_build_up']['time_to_50_percent_s']:
        b = growth['steady_build_up']
        parts.append(f'the steady stripe builds up to 50 % in {b["time_to_50_percent_s"]:.3g} s '
                     f'and to 90 % in {b["time_to_90_percent_s"]:.3g} s (radial time constant '
                     '4-7 min computed for a 260 mm roll)')
    growth['text'] = ('Growth: ' + '; '.join(parts) + '. A plant-identified flatness response '
                      'of about 20 s is of the order of the short local (axial) time scale and '
                      'of an event\'s rise, not of the minutes a steady stripe needs to build.'
                      ) if parts else None
    # ---- quarter-barrel positional note (no new observation key)
    note_q = None
    obs = case['observation']
    length = width.get('barrel_length_m') if isinstance(width, dict) else None
    if length and obs.get('band_positions_across_width_m'):
        lo, hi = QUARTER_BARREL
        hits = [x for x in obs['band_positions_across_width_m']
                if lo * length <= x <= hi * length or lo * length <= length - x <= hi * length]
        note_q = {'positions_in_quarter_zones_m': hits,
                  'zones_m': [[lo * length, hi * length],
                              [length - hi * length, length - lo * length]],
                  'text': ('Positional note only (no score): a roll hotter at 1/5-1/4 of the '
                           'barrel from each end gave quarter looseness after roughing, removed '
                           'by larger nozzles there [PT-T38]. '
                           + (f'Observed bands in those zones: {", ".join(f"{x:.3g}" for x in hits)} m.'
                              if hits else 'No observed band lies in those zones.')),
                  'sources': ['PT-T38']}
    incons = heat_partition_consistency(case)
    if incons:
        flags.append(HEAT_PARTITION_FLAG)
        texts.append(incons['text'])
    if collector:
        texts.append(EXIT_IS_NOT_COIL)
    texts.append(NO_PROPERTY_MODEL)
    return {'status': bp.STATUS, 'not_supplied': False, 'product_id': pid,
            'battery_coil_limits_apply': collector,
            'inputs': inputs, 'strip_exit_temperatures': temps,
            'coil_limits_c': {'entering_final_pass': bp.COIL_IN_FINAL_LIMIT.high,
                              'leaving_final_pass': bp.COIL_OUT_FINAL_LIMIT.high,
                              'elongation_decay_above': bp.COIL_OUT_FINAL_LIMIT_LOOSE.high},
            'outputs': outputs, 'growth': growth, 'property_risk': property_risk,
            'quarter_barrel_note': note_q, 'heat_partition_inputs': incons,
            'texts': texts, 'flags': flags,
            'note': 'Evidence-neutral literature comparison: it never changes a number or a '
                    'score.'}


THERMAL_MEASUREMENTS = (
    'Log the coil temperature before and after the final pass: published battery-foil limits '
    'are <= 75 C entering and <= 80 C leaving it (above 90 C elongation decays for weeks) '
    '[PT-T1, PT-T2].',
    'Log the oil supply temperature against the 38-45 C window (battery foil 40-45 C [PT-T1, '
    'PT-T6]; a ladder defect below 38 C at one plant [PT-T3]).',
    'Measure the dyne level at 0 h and 24 h after rolling: it can fall from above 32 to below '
    '30 dyn within 12-24 h as base oil evaporates [PT-T29, PT-T30].')


def thermal_measurements(case):
    """The temperature logs the process-temperature research makes worth taking (foil gauge or
    a battery product)."""
    pid = case['material'].get('product')
    if case['pass']['exit_thickness_m'] < SHEET_FROM_M or (pid and pid in bp.GRADE_TABLES):
        return list(THERMAL_MEASUREMENTS)
    return []
