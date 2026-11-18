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


def _event_rows(ev_section, scale):
    """Peak, states and visible times of each event, its history scaled by ``scale``."""
    rows = []
    for e in (ev_section or {}).get('events') or []:
        if 'history' not in e:
            continue
        times, dev = e['history']['time_s'], [v * scale for v in
                                             e['history']['radius_deviation_m']]
        peak = e['peak_deviation_m'] * scale
        man, rel = e.get('manifest_threshold_m'), e.get('released_threshold_m')
        rows.append({
            'label': e['label'], 'peak_deviation_m': peak,
            'manifest_threshold_m': man, 'released_threshold_m': rel,
            'in_mill': (None if man is None else
                        ('MANIFEST_IN_MILL' if peak >= man else 'LATENT_UNDER_TENSION')),
            'after_release': (None if rel is None else
                              ('MANIFEST_AFTER_TENSION_RELEASE' if peak >= rel
                               else 'BELOW_RELEASED_THRESHOLD')),
            'time_visible_in_mill_s': _time_above(times, dev, man),
            'time_visible_after_release_s': _time_above(times, dev, rel),
            'ratio_peak_to_in_mill_threshold': (None if not man else peak / man)})
    return rows


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
    case_share = fraction_to_share(case_frac)
    case_htc = th.header.spray_mean_htc_w_m2k
    shares = [(case_share, 'case value')]
    for s, why in ((MEASURED_STRIP_SHARES[0], 'measured high [PT-T16, abstract only, net '
                    'balance]'), (MEASURED_STRIP_SHARES[1], 'measured low [PT-T16, abstract '
                                  'only, net balance]'),
                   (PREVIOUS_DEMO_STRIP_SHARE, 'the demos\' value before SPEC14')):
        if all(abs(s - x) > 1e-9 for x, _ in shares):
            shares.append((s, why))
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
        ref = max(abs(v) for v in d2) or 1.0
        lin = max(abs(p - k * q) for p, q in zip(d2, steady['local_deviation_m'])) / ref
    rows, htc_info = [], []
    for htc, hwhy in htcs:
        if htc == case_htc:
            st = steady
            ev = events_out
            ev_basis = 'case event transient, history scaled by the roll heat share'
        else:
            th2, _, act2, st = _variant(th, htc, bw)
            ev = None
            ev_basis = 'no width_model.events'
            if w['events']:
                try:
                    ev = bw._events_section(th2, sp, act2, w['events'])
                    ev_basis = ('event transient rerun at this spray coefficient, history '
                                'scaled by the roll heat share')
                except ValueError as exc:
                    ev_basis = f'event transient failed: {exc}'
        s0 = _largest(st, th, bw)
        if s0 is None:
            htc_info.append({'spray_htc_w_m2k': htc, 'basis': hwhy,
                             'largest_stripe': None})
            for share, swhy in shares:
                rows.append({'strip_heat_share': share, 'share_basis': swhy,
                             'roll_heat_fraction_per_roll': share_to_fraction(share),
                             'spray_htc_w_m2k': htc, 'spray_basis': hwhy,
                             'stripe_peak_m': 0.0, 'status': 'NO_STRIPE_ABOVE_THRESHOLD'})
            continue
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
        htc_info.append({'spray_htc_w_m2k': htc, 'basis': hwhy,
                         'stripe_position_m': s0['peak_position_m'],
                         'stripe_peak_at_case_share_m': pk,
                         'in_mill_onset_height_m': None if on['mill'] is None
                         else on['mill'] * pk,
                         'after_release_onset_height_m': None if on['released'] is None
                         else on['released'] * pk,
                         'thermal_crown_at_case_share_m': st['thermal_crown_m'],
                         'event_basis': ev_basis})
        for share, swhy in shares:
            k = share_to_fraction(share) / case_frac
            sd = [v * k for v in dev]
            lv = bw.shape_levels(z, sd, sp)
            mill, rel, iu = _state(bw.stripe_states(lv, s0['peak_position_m']))
            peak = pk * k
            m_on = None if on['mill'] is None else on['mill'] * pk
            r_on = None if on['released'] is None else on['released'] * pk
            rows.append({
                'strip_heat_share': share, 'share_basis': swhy,
                'roll_heat_fraction_per_roll': share_to_fraction(share),
                'spray_htc_w_m2k': htc, 'spray_basis': hwhy, 'status': 'EVALUATED',
                'stripe_position_m': s0['peak_position_m'], 'stripe_peak_m': peak,
                'stripe_peak_on_diameter_m': 2 * peak,
                'with_feedback_i_units': iu, 'linear_feedback_i_units':
                    lv['linear_feedback_peak_i_units'],
                'state_in_mill': mill, 'state_after_tension_release': rel,
                'in_mill_onset_height_m': m_on, 'after_release_onset_height_m': r_on,
                'ratio_stripe_to_in_mill_onset': None if not m_on else peak / m_on,
                'ratio_stripe_to_after_release_onset': None if not r_on else peak / r_on,
                'thermal_crown_m': st['thermal_crown_m'] * k,
                'events': _event_rows(ev, k) if ev is not None else None})
    base = next((r for r in rows if r['strip_heat_share'] == case_share
                 and r['spray_htc_w_m2k'] == case_htc), None)
    changed = []
    if base is not None and base['status'] == 'EVALUATED':
        for r in rows:
            if r is base or r['status'] != 'EVALUATED':
                continue
            what = [k for k in ('state_in_mill', 'state_after_tension_release')
                    if r[k] != base[k]]
            for i, (e0, e1) in enumerate(zip(base['events'] or [], r['events'] or [])):
                for k in ('in_mill', 'after_release'):
                    if e0[k] != e1[k]:
                        what.append(f'event {e0["label"]} {k}')
            if what:
                changed.append({'strip_heat_share': r['strip_heat_share'],
                                'spray_htc_w_m2k': r['spray_htc_w_m2k'], 'changes': what})
    check = bp.check_thermal(case['material'].get('product') or 'battery_collector_foil',
                             strip_heat_fraction=case_share, spray_htc_w_m2k=case_htc)
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
        'linearity_check_max_relative_difference': lin,
        'linearity_note': ('stripe and event histories scaled with the roll heat share for a '
                           'fixed spray coefficient (linear roll thermal model, coolant '
                           'temperature as the zero); checked by one direct solve: maximum '
                           f'relative difference {lin:.2g}' if lin is not None else
                           'no second share to check'),
        'literature_check_of_case_inputs': check,
        'note': ('The heat partition [PT-T16] was read as an abstract only and is a net balance '
                 '(not necessarily the split inside the bite); the spray coefficients are '
                 'simulated [PT-T18] or computed from a plate test [PT-T19]. Model '
                 'sensitivities, not plant data.')}


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
        for s in ts['shares']:
            share = s['strip_heat_share']
            k = share_to_fraction(share) / ts['case_roll_heat_fraction_per_roll']
            stripe = (None if heat is None else
                      peak0 * k * heat / op['bite_heat_per_width_w_m'])
            on = g.get('manifest_onset_stripe_height_m')
            ron = g.get('released_onset_stripe_height_m')
            rise = None if h is None else h['strip_temperature_rise_k'] * share / case_share
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
    ts['per_pass_note'] = (
        'Stripe at a pass = the case-pass stripe x (that pass\'s bite heat / the case pass\'s) x '
        '(roll share / case roll share), at the case spray coefficient (linear model, same '
        'stripe shape); onsets from the gauge trend (the case stripe\'s shape at each pass). '
        'Strip exit temperature = entry + pass-heating rise x (share / case share); a strip '
        'exit temperature is not a coil temperature (the 80 C battery limit is for the coil '
        '[PT-T1]), and the experimental mattress bite inflates friction heat.')
