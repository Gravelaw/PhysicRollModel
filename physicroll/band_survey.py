"""Product survey: one synthetic final pass per catalogue product, screened on one stated mill.

    python -m physicroll.band_survey --out DIR
    python -m physicroll.band_cli --product-survey --out DIR

Writes ``DIR/product-survey.result.json`` (schema ``physicroll.band_survey.v1``) and
``DIR/product-survey.report.html``.

What it is (SPEC12 stage C): for every product of the literature catalogue
(``physicroll.band_products``; every product there has a published final gauge) a synthetic
final pass is built from catalogue data only and evaluated with the band engine's own models on
ONE synthetic mill per gauge class: the battery-foil demo mill for an exit gauge below 0.2 mm and
the lengthwise (sheet) demo mill above. Per product it reports the roll bite (model, flags,
force per width, the engine's credibility mark), the closed-gap flag, the strip-to-mill modulus
ratio, the bite-free thresholds (flatness dead band, critical coil ridge height, trough onset
and roller-wrinkle thresholds of the exit span), the response to a 1 um reference roll stripe
(I-units with the exit-tension feedback, in-mill and after-release onset heights), chatter
critical speeds with and without bite damping against the survey speed, the product-check
verdicts of the survey pass and the catalogue's named stripe defects; then a ranking per
mechanism and a generated plain-language summary.

What it is not: a plant result. One synthetic mill, literature inputs (many from excerpts,
patents or vendor pages), stated assumptions where the catalogue is silent, nothing validated.
A doubled (pack-rolled) final pass is not modelled: its bite-dependent cells read "doubled pass
not modelled" and only the per-sheet bite-free thresholds are given.

Rules for the survey pass (each row states which values came from the catalogue, with source
ids and read status, and which were assumed):

- gauges: the last pass of a published schedule when the product has one whose last step is a
  single published pass (preferring an exit inside the published final-gauge span, the
  product's own rolling mode, then the exit closest in log-gauge to the middle of that span,
  then the label); otherwise the geometric middle of the published final-gauge span as exit and
  the entry from the middle of the published final-pass reduction span, else the per-pass span,
  else (foil families) the general packaging-foil per-pass span, else an assumed reduction;
- flow stress: the as-rolled strength of the pass. For an H1x final temper the median of the
  published tensile-strength numbers of that temper (standard grade where both are published).
  For O, H2x and other annealed tempers the final cold pass is rolled hard and annealed
  afterwards: an as-rolled H1x strength published for the product is used if there is one, else
  an assumed value, labelled; annealed strength is never used as rolling flow stress;
- tensions: stated fractions of the flow stress; speed: the middle of the published final-pass
  speed span (doubled or single as the pass is), else of the published pass-speed span, else the
  mill demo's speed; friction: the demos' 0.03.
"""
import argparse
import copy
import json
import math
import re
import statistics
import sys
from pathlib import Path

from . import band_diagnosis as bd
from . import band_products as bp
from . import band_width as bw
from . import strip_shape as ss
from .band_report import CSS, COLOURS, ML, MR, W, _Axis, _Chart, _e, _table, _tick_label

SCHEMA = 'physicroll.band_survey.v1'
STATUS = 'SYNTHETIC_SURVEY_LITERATURE_INPUTS_UNVALIDATED'
SLUG = 'product-survey'
SCENARIOS = Path(__file__).resolve().parents[1] / 'scenarios'
FOIL_MILL_MAX_EXIT_M = 0.2e-3          # below: the battery-foil demo mill; at or above: sheet
MILLS = {
    'foil': {'scenario': 'band_diagnosis_battery_foil.json',
             'name': 'battery-foil demo mill (single-stand four-high foil mill, synthetic)',
             'default_speed_m_s': 10.0,
             'default_speed_basis': 'the foil demo final-pass speed (600 m/min)'},
    'sheet': {'scenario': 'band_diagnosis_lengthwise_bands.json',
              'name': 'lengthwise demo mill (single-stand four-high sheet mill, synthetic)',
              'default_speed_m_s': 12.0,
              'default_speed_basis': 'the lengthwise demo case-pass speed (720 m/min)'},
}
FRICTION = 0.03                        # the demos' supplied friction (no catalogue value)
ENTRY_TENSION_FRACTION = 0.20          # of the flow stress [D, stated]
EXIT_TENSION_FRACTION = 0.23           # of the flow stress [D, stated; foil demo 40/175]
ASSUMED_AS_ROLLED_FLOW_STRESS_PA = 180e6
ASSUMED_FLOW_STRESS_BASIS = (
    'ASSUMED 180 MPa as-rolled flow stress [D]: the catalogue publishes no as-rolled (H1x) '
    'strength for this product; a dilute-alloy foil value, likely low for 3xxx / 5xxx sheet')
ASSUMED_REDUCTION = 0.30
ASSUMED_REDUCTION_BASIS = ('ASSUMED 30 % final-pass reduction [D]: no final-pass or per-pass '
                           'reduction published for this product')
STRIPE_HEIGHT_M = 1e-6                 # reference roll stripe (Gaussian, half-peak 0.1 m)
CLOSED_GAP_BELOW_M = bw.FOIL_GAUGE_M   # the engine's foil-regime / closed-gap flag threshold
LOAD_RANGE_PRODUCT = 'battery_collector_foil'
NO_LOAD_RANGE = 'NO_REPORTED_LOAD_RANGE_IN_CATALOGUE'
DOUBLED_NOT_MODELLED = 'doubled pass not modelled'
H1X = re.compile(r'^H1\d$')
LIMITATIONS = (
    'Synthetic: one stated mill per gauge class (the demo mills), not any plant; the products '
    'differ in gauge, flow stress, tension and speed only.',
    'Inputs are literature values from the product catalogue (a survey of excerpts, patents, '
    'standards previews and vendor or trade pages); each row carries the read status.',
    'Assumed values are labelled per row (flow stress without a published as-rolled strength, '
    'reduction without a published span, the tension fractions, friction 0.03, the mill).',
    'Doubled (pack-rolled) final passes are not modelled: no bite, only per-sheet bite-free '
    'thresholds.',
    'Roll bites below about 60 um come from the experimental mattress model (order of '
    'magnitude); below 20 um exit gauge or above 50 % reduction from its unvalidated extended '
    'domain. The force range used for the credibility mark is reported for battery-foil passes '
    'only.',
    'Chatter numbers are open-gap linear screening values; above the span-wave limit they are '
    'flagged not reliable.',
    'Nothing here is validated against plant data; rankings compare model sensitivities on a '
    'synthetic mill, not plant defect rates.',
)


# --------------------------------------------------------------------------- helpers
def _mid(r):
    """Middle of a catalogue Range (arithmetic), or its one published bound."""
    if r.low is not None and r.high is not None:
        return (r.low + r.high) / 2
    return r.low if r.low is not None else r.high


def _gmid(lo, hi):
    return math.sqrt(lo * hi)


def _sig(x, n=3):
    return float(f'{x:.{n}g}')


def _src(*objs):
    out = []
    for o in objs:
        for s in getattr(o, 'sources', ()) or ():
            if s not in out:
                out.append(s)
    return out


def _status(*objs):
    st = [o.effective_read_status() if hasattr(o, 'effective_read_status')
          else bp._source_status(o) for o in objs]
    st = [s for s in st if s]
    weak = bp._weakest(st)
    return weak or ('computed' if 'computed' in st else None)


def _used(item, value, unit, basis, sources=(), read_status=None):
    return {'item': item, 'value': value, 'unit': unit, 'basis': basis,
            'sources': list(sources), 'read_status': read_status}


def _assumed(item, value, unit, basis):
    return {'item': item, 'value': value, 'unit': unit, 'basis': basis}


# --------------------------------------------------------------------------- survey pass
def _schedule_candidate(p):
    fg = p.final_gauge_m
    lo = fg.low if fg.low is not None else fg.high
    hi = fg.high if fg.high is not None else fg.low
    target = _gmid(lo, hi)
    want_doubled = p.rolled_mode == 'doubled'
    cands = []
    for s in p.schedules:
        last = s.steps() - 1
        if s.passes()[last] != 1:
            continue
        g = s.gauges()
        h0, h1 = _gmid(*g[last]), _gmid(*g[last + 1])
        inside = lo * (1 - 1e-9) <= h1 <= hi * (1 + 1e-9)
        dbl = s.is_doubled(last)
        cands.append(((not inside, dbl != want_doubled, abs(math.log(h1 / target)), s.label),
                      s, last, h0, h1, dbl))
    return min(cands, key=lambda c: c[0])[1:] if cands else None


def survey_pass(p):
    """Gauges, rolling mode and their basis for the survey final pass of product ``p``."""
    used, assumed = [], []
    cand = _schedule_candidate(p)
    if cand is not None:
        s, step, h0, h1, dbl = cand
        dbl = dbl or p.rolled_mode == 'doubled'
        g = s.gauges()
        used.append(_used('final pass gauges', [h0, h1], 'm',
                          f'last pass of the published schedule "{s.label}" (step {step + 1}'
                          + (f'; published as {g[step][0] * 1e6:.4g}-{g[step][1] * 1e6:.4g} -> '
                             f'{g[step + 1][0] * 1e6:.4g}-{g[step + 1][1] * 1e6:.4g} um, '
                             'geometric middles used' if g[step][0] != g[step][1]
                             or g[step + 1][0] != g[step + 1][1] else '')
                          + ('; doubled pass, gauges per sheet' if s.is_doubled(step) else '')
                          + ')', s.sources, bp._source_status(s)))
        basis = 'published_schedule'
        label = s.label
    else:
        fg = p.final_gauge_m
        lo = fg.low if fg.low is not None else fg.high
        hi = fg.high if fg.high is not None else fg.low
        h1 = _sig(_gmid(lo, hi))
        used.append(_used('exit gauge', h1, 'm', 'geometric middle of the published final-gauge '
                          f'span {lo * 1e6:.4g}-{hi * 1e6:.4g} um (common nominal gauge)',
                          fg.sources, fg.effective_read_status()))
        fp = p.final_pass
        if fp is not None and fp.reduction is not None:
            r, rng, what = _mid(fp.reduction), fp.reduction, 'published final-pass reduction'
        elif p.per_pass_reduction is not None:
            r, rng, what = _mid(p.per_pass_reduction), p.per_pass_reduction, \
                'published per-pass reduction'
        elif p.family in ('battery_electronics', 'packaging_household'):
            rng = bp._general_foil_span()
            r, what = _mid(rng), 'general packaging-foil per-pass reduction (no span of its own)'
        else:
            rng, r = None, ASSUMED_REDUCTION
        if rng is not None:
            used.append(_used('reduction', r, 'fraction',
                              f'middle of the {what} span {rng.low * 100:.3g}-'
                              f'{rng.high * 100:.3g} %', rng.sources,
                              rng.effective_read_status()))
        else:
            assumed.append(_assumed('reduction', r, 'fraction', ASSUMED_REDUCTION_BASIS))
        h0 = _sig(h1 / (1 - r))
        dbl = p.rolled_mode == 'doubled'
        basis = 'nominal_gauge'
        label = None
    if p.rolled_mode == 'not_published':
        assumed.append(_assumed('rolling mode', 'single_sheet', '',
                                'no rolling mode published for this product: single-sheet '
                                'final pass assumed'))
    elif p.mode_note is not None:
        used.append(_used('rolling mode', 'doubled' if dbl else 'single_sheet', '',
                          p.mode_note.text, p.mode_note.sources,
                          p.mode_note.effective_read_status()))
    return {'entry_thickness_m': h0, 'exit_thickness_m': h1, 'doubled': bool(dbl),
            'gauge_basis': basis, 'schedule': label, 'used': used, 'assumed': assumed}


def _temper_tokens(t):
    return [x for x in t.replace('/', ' ').split() if x]


def survey_flow_stress(p):
    """(flow stress, final temper, used, assumed): the as-rolled strength of the pass."""
    final = p.tempers[0].name
    entries = [s for s in p.strength if s.rm_pa is not None
               and any(H1X.match(t) for t in _temper_tokens(s.temper))]
    if H1X.match(final):
        same = [s for s in entries if final in _temper_tokens(s.temper)]
        entries = same or entries
    std = [s for s in entries if s.grade != 'high_strength']
    entries = std or entries
    if entries:
        nums = []
        for s in entries:
            r = s.rm_pa
            nums += [v for v in ((r.low, r.high) if r.bound != 'minimum' else (r.low,))
                     if v is not None]
        sigma = statistics.median(nums)
        tempers = sorted({t for s in entries for t in _temper_tokens(s.temper)})
        why = (f'median of the published tensile-strength numbers of the as-rolled temper '
               f'{"/".join(tempers)} ({min(nums) * 1e-6:.4g}-{max(nums) * 1e-6:.4g} MPa)')
        if not H1X.match(final):
            why += (f'; the final temper {final} is reached by annealing after the final cold '
                    'pass, which is rolled hard')
        rms = [s.rm_pa for s in entries]
        return sigma, final, [_used('flow stress', sigma, 'Pa', why, _src(*rms),
                                    _status(*rms))], []
    return (ASSUMED_AS_ROLLED_FLOW_STRESS_PA, final, [],
            [_assumed('flow stress', ASSUMED_AS_ROLLED_FLOW_STRESS_PA, 'Pa',
                      ASSUMED_FLOW_STRESS_BASIS
                      + ('' if H1X.match(final) else
                         f'; the final temper {final} is reached by annealing after the final '
                         'cold pass, so annealed strength is not used'))])


def survey_speed(p, doubled, mill):
    fp = p.final_pass
    for rng, what in ((fp.doubled_speed_m_s if fp is not None and doubled else None,
                       'published doubled final-pass speed'),
                      (fp.speed_m_s if fp is not None and not doubled else None,
                       'published single-sheet final-pass speed'),
                      (p.pass_speed_m_s, 'published pass speed (earlier passes)')):
        if rng is not None:
            v = _mid(rng)
            return v, [_used('exit speed', v, 'm/s',
                             f'middle of the {what} span {rng.low * 60:.4g}-{rng.high * 60:.4g} '
                             'm/min', rng.sources, rng.effective_read_status())], []
    v = MILLS[mill]['default_speed_m_s']
    return v, [], [_assumed('exit speed', v, 'm/s',
                            'no published speed for this product: ' +
                            MILLS[mill]['default_speed_basis'])]


# --------------------------------------------------------------------------- mill models
def _load_mill(kind):
    case = bd.load_case(SCENARIOS / MILLS[kind]['scenario'])
    p, st, sp, w = case['pass'], case['stand'], case['spans'], case['width_model']
    desc = {'kind': kind, 'name': MILLS[kind]['name'], 'scenario': MILLS[kind]['scenario'],
            'work_roll_radius_m': p['work_roll_radius_m'], 'strip_width_m': p['width_m'],
            'backup_roll_diameter_m': case['kinematics']['backup_roll_diameter_m'],
            'work_roll_mass_kg': st['work_roll_mass_kg'],
            'backup_roll_mass_kg': st['backup_roll_mass_kg'],
            'work_backup_contact_stiffness_n_m': st['work_backup_contact_stiffness_n_m'],
            'housing_stiffness_n_m': st['housing_stiffness_n_m'],
            'entry_span_length_m': sp['entry_span_length_m'],
            'exit_span_length_m': sp['exit_span_length_m'],
            'deflector_roll_radius_m': w['deflector_roll_radius_m'],
            'coil': dict(w['coil']), 'barrel_length_m': w['roll']['barrel_length_m'],
            'bite_model': case['model_options']['bite_model'],
            'bite_damping_transit_fraction': case['model_options'][
                'bite_damping_transit_fraction'],
            'span_wave_limit_hz': bd._span_wave_limit_hz(case)}
    return case, desc


class _Mill:
    def __init__(self, kind):
        self.kind = kind
        self.case, self.desc = _load_mill(kind)
        self.cache = bd._BiteCache(self.case)
        self.stand = bd._stand(self.case)
        self.spans = bd._spans(self.case)
        self.beta = self.case['model_options']['bite_damping_transit_fraction']
        w = self.case['width_model']
        length = w['roll']['barrel_length_m']
        n = max(4, int(round(length / bw.ONSET_GRID_M)))
        self.z = [i * length / n for i in range(n + 1)]
        self.centre = (w['strip_centre_m'] if w['strip_centre_m'] is not None
                       else length / 2)
        # the grid point nearest the strip centre carries the stripe peak
        self.centre = min(self.z, key=lambda x: abs(x - self.centre))

    def case_for(self, row, sigma):
        c = copy.deepcopy(self.case)
        c['pass'].update({k: row[k] for k in (
            'entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
            'friction_coefficient', 'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s')})
        c['material']['yield_stress_pa'] = sigma
        c['schedule'] = [row]
        return c


def bite_free(mill, h1, sigma, exit_tension):
    """Bite-free thresholds of one sheet (the engine's strip_shape calls)."""
    d = mill.desc
    out = {}
    win = ss.shohet_townsend_window(h1, d['strip_width_m'])
    out['dead_band_half_width_i_units'] = (win['upper_bound_i_units']
                                           - win['lower_bound_i_units']) / 2
    coil = d['coil']
    try:
        cb = ss.coil_ridge_buildup(0.0, h1, coil['inner_radius_m'], coil['outer_radius_m'],
                                   sigma, coil['winding_tension_pa'], ss.ALUMINIUM_E_PA,
                                   coil['compaction_factor'] or ss.DEFAULT_COMPACTION_FACTOR)
        out['critical_ridge_height_m'] = cb['critical_ridge_height_at_outer_radius_m']
    except ValueError as exc:
        out['critical_ridge_height_m'] = None
        out['critical_ridge_error'] = str(exc)
    tr = ss.tension_trough_screen(h1, d['exit_span_length_m'], exit_tension, d['strip_width_m'],
                                  roller_radius_m=d['deflector_roll_radius_m'],
                                  youngs_modulus_pa=ss.ALUMINIUM_E_PA,
                                  poisson_ratio=bw.STRIP_POISSON_RATIO)
    out['trough_onset_lateral_stress_pa'] = tr['trough_critical_lateral_stress_pa']
    out['roller_wrinkle_threshold_pa'] = tr['roller_wrinkle_critical_lateral_stress_pa']
    return out


def _stripe(mill, case, bite, row):
    sp = bw.shape_params(case, bite, case['width_model'], row)
    ref = bw._reference_stripe(mill.z, mill.centre, STRIPE_HEIGHT_M)
    peak = max(ref)
    lv = bw.shape_levels(mill.z, ref, sp)
    st = bw.stripe_states(lv, mill.centre)['with_feedback']
    on = bw.onsets(mill.z, ref, sp)

    def h(s):
        return None if s is None else s * peak
    return {'linear_feedback_i_units': lv['linear_feedback_peak_i_units'],
            'state_in_mill': st['state'],
            'state_after_tension_release': st['state_after_tension_release'],
            'in_mill_onset_height_m': h(on['mill']),
            'after_release_onset_height_m': h(on['released']),
            'reporting_onset_height_m': h(on['reporting']),
            'after_release_onset_limited_by_reporting_threshold': bw._limited(
                on['released'], on['reporting']),
            'onset_search_ceiling_m': bw.ONSET_SEARCH_MAX_M}


# --------------------------------------------------------------------------- one product
def survey_row(p, mills, index):
    sp = survey_pass(p)
    h0, h1, dbl = sp['entry_thickness_m'], sp['exit_thickness_m'], sp['doubled']
    kind = 'foil' if h1 < FOIL_MILL_MAX_EXIT_M else 'sheet'
    mill = mills[kind]
    sigma, temper, used_s, assumed_s = survey_flow_stress(p)
    u, used_u, assumed_u = survey_speed(p, dbl, kind)
    t_in, t_out = ENTRY_TENSION_FRACTION * sigma, EXIT_TENSION_FRACTION * sigma
    alloy = p.alloys[0].name
    assumed = sp['assumed'] + assumed_s + assumed_u + [
        _assumed('tensions', [t_in, t_out], 'Pa',
                 f'entry {ENTRY_TENSION_FRACTION:g} and exit {EXIT_TENSION_FRACTION:g} of the '
                 'flow stress [D, stated]'),
        _assumed('friction', FRICTION, '', 'the demos\' supplied 0.03 (no catalogue value)'),
        _assumed('mill', kind, '', mill.desc['name'] + ': the same synthetic mill for every '
                 'product of this gauge class'),
        _assumed('alloy for the product check', alloy, '',
                 'first alloy listed for the product in the catalogue')]
    used = sp['used'] + used_s + used_u
    statuses = [x['read_status'] for x in used if x.get('read_status')]
    out = {'index': index, 'product_id': p.id, 'product_name': p.name, 'family': p.family,
           'mill': kind, 'label': f'{index} {p.id}',
           'entry_thickness_m': h0, 'exit_thickness_m': h1,
           'reduction_fraction': 1 - h1 / h0, 'doubled': dbl,
           'rolling_mode_published': p.rolled_mode, 'gauge_basis': sp['gauge_basis'],
           'schedule': sp['schedule'], 'final_temper': temper, 'alloy_checked': alloy,
           'mean_flow_stress_pa': sigma, 'flow_stress_assumed': bool(assumed_s),
           'entry_tension_pa': t_in, 'exit_tension_pa': t_out, 'exit_speed_m_s': u,
           'friction_coefficient': FRICTION,
           'catalogue_values_used': used, 'assumed_values': assumed,
           'weakest_read_status': bp._weakest(statuses) if statuses else None,
           'vendor_level_input': any(s in ('vendor_or_trade_page', 'memory_unverified')
                                     for s in statuses),
           'closed_gap_likely': h1 < CLOSED_GAP_BELOW_M,
           'flags': []}
    if h1 < CLOSED_GAP_BELOW_M:
        out['flags'].append(bd.CLOSED_GAP_FLAG)
    out.update(bite_free(mill, h1, sigma, t_out))
    out['named_defects'] = [{'name': d.name, 'sources': list(d.sources),
                             'read_status': bp._effective(d.sources, d.read_status)}
                            for d in p.named_defects]
    chk = bp.check_pass(p.id, h0, h1, exit_speed_m_s=u, mean_flow_stress_pa=sigma,
                        doubled=dbl, is_final_pass=True, alloy=alloy, temper=temper)
    out['product_check'] = [{'item': f['item'], 'verdict': f['verdict'],
                             'sources': f['sources'], 'read_status': f['read_status']}
                            for f in chk]
    out['product_check_outside'] = [f['item'] for f in chk if f['verdict'] in (
        'BELOW_PUBLISHED_RANGE', 'ABOVE_PUBLISHED_RANGE', 'INCONSISTENT_WITH_PUBLISHED_MODE')]
    if dbl:
        out['bite_status'] = 'DOUBLED_PASS_NOT_MODELLED'
        out['bite_note'] = (f'{DOUBLED_NOT_MODELLED}: the tool has no model of two sheets in '
                            'one bite; bite-free thresholds are per sheet')
        out['flags'].append('DOUBLED_FINAL_PASS_NOT_MODELLED')
        return out
    row = {'label': out['label'], 'entry_thickness_m': h0, 'exit_thickness_m': h1,
           'mean_flow_stress_pa': sigma, 'friction_coefficient': FRICTION,
           'entry_tension_pa': t_in, 'exit_tension_pa': t_out, 'exit_speed_m_s': u}
    case = mill.case_for(row, sigma)
    sw = bd._schedule_rows(case, mill.cache, mill.stand, mill.spans, mill.beta)['rows'][0]
    if 'rejected' in sw:
        out['bite_status'] = 'NO_BITE'
        out['bite_note'] = sw['rejected']
        return out
    fpw = sw['separating_force_per_width_n_m']
    out.update(bite_status='BITE', bite_model=sw['bite_model'], bite_flags=sw['bite_flags'],
               separating_force_per_width_n_m=fpw,
               contact_radius_ratio=sw['contact_radius_ratio'],
               forward_slip_fraction=sw['forward_slip_fraction'],
               strip_to_mill_modulus_ratio=sw['strip_to_mill_modulus_ratio'],
               critical_exit_speed_m_s=sw['critical_exit_speed_m_s'],
               critical_status=sw['critical_status'],
               critical_exit_speed_without_bite_damping_m_s=sw[
                   'critical_exit_speed_without_bite_damping_m_s'],
               speed_ratio=sw['speed_ratio'],
               speed_ratio_without_bite_damping=sw['speed_ratio_without_bite_damping'],
               onset_frequency_hz=sw['onset_frequency_hz'])
    limit = mill.desc['span_wave_limit_hz']
    bite = mill.cache.get(bd._bite_pass(case, row))
    c0 = bd._crit_pair(mill.stand, bite, mill.spans, mill.beta)[1]
    onsets_hz = [f for f in (sw['onset_frequency_hz'], c0['onset_frequency_hz']) if f]
    out['chatter_reliability'] = ('NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT'
                                  if onsets_hz and max(onsets_hz) > limit
                                  else 'WITHIN_SPAN_WAVE_LIMIT')
    ext = [f for f in bd.EXTENDED_BITE_FLAGS if f in sw['bite_flags']]
    out['extended_domain_flags'] = ext
    mark, ratio = bd._bite_credibility(sw['bite_flags'], fpw)
    out['engine_bite_credibility'] = mark
    if mark is not None and p.id != LOAD_RANGE_PRODUCT:
        out['bite_credibility'] = NO_LOAD_RANGE
        out['bite_credibility_note'] = ('extended-domain bite; the catalogue has no reported '
                                        'load range for this product (the 0.9-2.3 kN/mm range is '
                                        'reported for battery-foil passes only); unvalidated')
    else:
        out['bite_credibility'] = mark
        out['bite_force_ratio_to_reported_range'] = ratio
    out['stripe'] = _stripe(mill, case, bite, row)
    return out


# --------------------------------------------------------------------------- rankings
def _credible(r):
    return r.get('bite_credibility') != bd.CREDIBILITY_OUTSIDE


MECHANISMS = (
    # key, title, value getter, unit scale, unit, needs bite, sort (True: smaller = more
    # sensitive), sensitivity wording
    ('coil_ridges', 'Coil ridges (critical ridge height at the outer coil radius)',
     lambda r: r.get('critical_ridge_height_m'), 1e6, 'um', False, True,
     'a lower critical ridge height lets a smaller incoming ridge yield the strip in the coil'),
    ('troughs', 'Troughs and creases in the exit span (trough onset lateral stress, '
     'magnitude)',
     lambda r: (abs(r['trough_onset_lateral_stress_pa'])
                if r.get('trough_onset_lateral_stress_pa') is not None else None),
     1e-3, 'kPa', False, True, 'a smaller lateral compression starts troughs'),
    ('roller_wrinkles', 'Roller wrinkles on the deflector roll (threshold magnitude)',
     lambda r: (abs(r['roller_wrinkle_threshold_pa'])
                if r.get('roller_wrinkle_threshold_pa') is not None else None),
     1e-6, 'MPa', False, True, 'a smaller lateral compression wrinkles the strip on the roll'),
    ('cooling_stripes_in_mill', 'Cooling stripes visible in the mill (in-mill onset height of '
     'a roll stripe)', lambda r: (r.get('stripe') or {}).get('in_mill_onset_height_m'),
     1e6, 'um', True, True, 'a smaller roll stripe buckles the strip under mill tension'),
    ('cooling_stripes_after_release', 'Cooling stripes visible after tension release '
     '(after-release onset height, an upper bound where reporting-limited)',
     lambda r: (r.get('stripe') or {}).get('after_release_onset_height_m'),
     1e6, 'um', True, True, 'a smaller roll stripe shows on the coil or the table'),
    ('chatter_margin', 'Chatter margin (survey speed over the critical speed without bite '
     'damping)', lambda r: r.get('speed_ratio_without_bite_damping'),
     1.0, '', True, False, 'a higher speed ratio means less margin to third-octave chatter'),
)


def rankings(rows):
    out = []
    for key, title, get, scale, unit, needs_bite, small_first, meaning in MECHANISMS:
        ranked, excluded = [], []
        for r in rows:
            why = None
            if needs_bite and r['bite_status'] != 'BITE':
                why = (DOUBLED_NOT_MODELLED if r['bite_status'] == 'DOUBLED_PASS_NOT_MODELLED'
                       else 'no roll bite')
            elif needs_bite and not _credible(r):
                why = 'bite NOT CREDIBLE (force outside the range reported for battery foil)'
            elif key == 'chatter_margin' and bd._outside_scan(r['exit_speed_m_s']):
                why = ('survey speed outside the critical-speed scan (the margin is not '
                       'assessable there)')
            elif key == 'chatter_margin' and r.get('chatter_reliability') != \
                    'WITHIN_SPAN_WAVE_LIMIT':
                why = 'chatter onset above the span-wave limit (not reliable)'
            elif get(r) is None:
                why = ('stable over the scanned speed range even without bite damping'
                       if key == 'chatter_margin' else
                       f'onset not reached within the {bw.ONSET_SEARCH_MAX_M * 1e6:.3g} um '
                       'search' if needs_bite else 'not computed')
            if why:
                excluded.append({'label': r['label'], 'reason': why})
            else:
                ranked.append(r)
        ranked.sort(key=lambda r: ((get(r) if small_first else -get(r)), r['index']))
        out.append({'mechanism': key, 'title': title, 'unit': unit, 'meaning': meaning,
                    'gauge_rank_correlation': None,
                    'most_sensitive_first': [
                        {'rank': i + 1, 'label': r['label'], 'product_id': r['product_id'],
                         'exit_thickness_m': r['exit_thickness_m'],
                         'value': get(r) * scale, 'mill': r['mill'],
                         'unvalidated_extended_bite': bool(r.get('extended_domain_flags'))}
                        for i, r in enumerate(ranked)],
                    'excluded': excluded})
    return out


def _names(items, n=3):
    return ', '.join(f'{x["product_id"]} ({x["exit_thickness_m"] * 1e6:.3g} um)'
                     for x in items[:n])


def _spearman(xs, ys):
    """Rank correlation (average ranks for ties); None for fewer than three points."""
    if len(xs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def gauge_correlation(rank):
    """Rank correlation of 'more sensitive' with 'thinner' over the ranked rows (+1: the
    thinnest products are the most sensitive, -1: the thickest)."""
    items = rank['most_sensitive_first']
    return _spearman([x['exit_thickness_m'] for x in items],
                     [float(x['rank']) for x in items])


def _trend_words(rho):
    if rho is None:
        return 'too few products for a gauge statement'
    if rho >= 0.7:
        return f'the thinner the product, the more sensitive (rank correlation {rho:+.2f})'
    if rho <= -0.7:
        return f'the thicker the product, the more sensitive (rank correlation {rho:+.2f})'
    return f'no clear gauge order (rank correlation {rho:+.2f})'


def summary(rows, ranks):
    """Generated plain-language summary from the rankings."""
    n = len(rows)
    nd = sum(r['doubled'] for r in rows)
    nb = sum(r['bite_status'] == 'BITE' for r in rows)
    nc = sum(r.get('bite_credibility') == bd.CREDIBILITY_OUTSIDE for r in rows)
    na = sum(r['flow_stress_assumed'] for r in rows)
    parts = [f'{n} catalogue products, one synthetic final pass each: {nb} with a roll bite, '
             f'{nd} doubled (bite not modelled), {nc} with a bite marked not credible, {na} '
             'with an assumed flow stress.']
    for rk in ranks:
        top = rk['most_sensitive_first']
        if not top:
            parts.append(f'{rk["title"]}: no product ranked.')
            continue
        parts.append(f'{rk["title"]}: most sensitive {_names(top)}; '
                     f'{_trend_words(gauge_correlation(rk))}'
                     + (f'; {len(rk["excluded"])} excluded' if rk['excluded'] else '') + '.')
    parts.append('These are model sensitivities on one synthetic mill per gauge class with '
                 'literature inputs, not plant defect rates.')
    return ' '.join(parts)


# --------------------------------------------------------------------------- top level
def survey():
    mills = {k: _Mill(k) for k in MILLS}
    rows = [survey_row(p, mills, i + 1) for i, p in enumerate(bp.products())]
    ranks = rankings(rows)
    for rk in ranks:
        rk['gauge_rank_correlation'] = gauge_correlation(rk)
    result = {'schema': SCHEMA, 'status': STATUS, 'synthetic': True,
              'catalogue_schema': bp.SCHEMA, 'catalogue_status': bp.STATUS,
              'mills': {k: m.desc for k, m in mills.items()},
              'rules': {'foil_mill_below_exit_m': FOIL_MILL_MAX_EXIT_M,
                        'friction_coefficient': FRICTION,
                        'entry_tension_fraction_of_flow_stress': ENTRY_TENSION_FRACTION,
                        'exit_tension_fraction_of_flow_stress': EXIT_TENSION_FRACTION,
                        'assumed_as_rolled_flow_stress_pa': ASSUMED_AS_ROLLED_FLOW_STRESS_PA,
                        'assumed_reduction': ASSUMED_REDUCTION,
                        'reference_stripe_height_m': STRIPE_HEIGHT_M,
                        'reference_stripe_half_peak_width_m': bw.REFERENCE_HALF_PEAK_WIDTH_M,
                        'closed_gap_flag_below_exit_m': CLOSED_GAP_BELOW_M,
                        'reported_load_range_n_m': list(bd.FOIL_LOAD_RANGE_N_M),
                        'reported_load_range_applies_to': LOAD_RANGE_PRODUCT},
              'rows': rows, 'rankings': ranks, 'summary': summary(rows, ranks),
              'limitations': list(LIMITATIONS) + list(bp.LIMITATIONS),
              'sources': sorted({s for r in rows for x in r['catalogue_values_used']
                                 for s in x['sources']})}
    json.dumps(result, allow_nan=False)
    return result


def result_json(result):
    return bd.result_json(result)


# --------------------------------------------------------------------------- report
def _f(v, scale=1.0, d=3):
    if v is None:
        return '–'
    return f'{v * scale:.{d}g}'


def _cell_bite(r, text):
    if r['bite_status'] == 'DOUBLED_PASS_NOT_MODELLED':
        return f'<em>{_e(DOUBLED_NOT_MODELLED)}</em>'
    if r['bite_status'] != 'BITE':
        return '<em>no roll bite</em>'
    return text() if callable(text) else text


def _marks(r):
    m = []
    if r.get('bite_credibility') == bd.CREDIBILITY_OUTSIDE:
        m.append('<strong>bite NOT CREDIBLE</strong> (force x'
                 f'{r["bite_force_ratio_to_reported_range"]:.2g} the nearer end of the range '
                 'reported for battery-foil passes)')
    elif r.get('bite_credibility') == bd.CREDIBILITY_INSIDE:
        m.append('extended-domain bite, force inside the reported range, unvalidated')
    elif r.get('bite_credibility') == NO_LOAD_RANGE:
        m.append('extended-domain bite, no reported load range in the catalogue, unvalidated')
    if r.get('extended_domain_flags'):
        m.append('extended domain: ' + ', '.join(r['extended_domain_flags']))
    if r['closed_gap_likely']:
        m.append('closed gap likely (not modelled)')
    if r['flow_stress_assumed']:
        m.append('flow stress ASSUMED')
    if r['vendor_level_input']:
        m.append('rests on vendor / trade-page data')
    if r['product_check_outside']:
        m.append('outside published: ' + ', '.join(r['product_check_outside']))
    return '; '.join(x if x.startswith('<strong>') else _e(x) for x in m) or '–'


def _chatter_cell(r):
    if r['bite_status'] != 'BITE':
        return _cell_bite(r, '')
    uc, uc0 = r['critical_exit_speed_m_s'], r['critical_exit_speed_without_bite_damping_m_s']
    if bd._outside_scan(r['exit_speed_m_s']):
        return _e(f'survey speed {r["exit_speed_m_s"]:.3g} m/s outside the scanned range')
    a = 'stable over scan' if uc is None else f'{uc:.3g} m/s'
    b = 'stable over scan' if uc0 is None else f'{uc0:.3g} m/s'
    rel = '' if r['chatter_reliability'] == 'WITHIN_SPAN_WAVE_LIMIT' else ' <em>(not reliable: ' \
        'above the span-wave limit)</em>'
    return f'{_e(a)} / {_e(b)} at {r["exit_speed_m_s"]:.3g} m/s{rel}'


def _onset(h):
    return (f'not reached within {bw.ONSET_SEARCH_MAX_M * 1e6:.3g} µm' if h is None
            else f'{h * 1e6:.3g} µm')


def _table_rows(rows):
    out = []
    for r in rows:
        st = r.get('stripe') or {}
        lim = ' (≤, reporting-limited)' if st.get(
            'after_release_onset_limited_by_reporting_threshold') else ''
        out.append([
            f'{r["index"]}',
            f'<code>{_e(r["product_id"])}</code><br>{_e(r["product_name"])}',
            _e(f'{r["entry_thickness_m"] * 1e6:.4g} → {r["exit_thickness_m"] * 1e6:.4g} µm'
               + (' per sheet, doubled' if r['doubled'] else '')
               + f' ({r["reduction_fraction"] * 100:.0f} %); {r["mill"]} mill; '
               f'{r["mean_flow_stress_pa"] * 1e-6:.3g} MPa'),
            _cell_bite(r, lambda: _e(
                f'{r["bite_model"]}, {r["separating_force_per_width_n_m"] * 1e-6:.3g} kN/mm, '
                f'strip/mill {r["strip_to_mill_modulus_ratio"]:.3g}')),
            _e(_f(r['dead_band_half_width_i_units'])),
            _e(_f(r['critical_ridge_height_m'], 1e6)),
            _e(_f(r['trough_onset_lateral_stress_pa'], 1e-3)),
            _e(_f(r['roller_wrinkle_threshold_pa'], 1e-6)),
            _cell_bite(r, lambda: _e(f'{_f(st.get("linear_feedback_i_units"))} I; in mill '
                                     f'{_onset(st.get("in_mill_onset_height_m"))}; after '
                                     f'release {_onset(st.get("after_release_onset_height_m"))}'
                                     f'{lim}')),
            _chatter_cell(r),
            _marks(r)])
    return out


def _mech_chart(rank, rows, n):
    pts = [(x['exit_thickness_m'] * 1e6, x['value'], x['label'].split()[0])
           for x in rank['most_sensitive_first'] if x['value'] and x['value'] > 0]
    if len(pts) < 2:
        return '<p class="note">Fewer than two ranked products: no chart.</p>'
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ylog = max(ys) / min(ys) > 30
    ch = _Chart(rank['title'], [('product (number as in the table)', COLOURS[0], '', 'dot')],
                height=300)
    ch.axes(_Axis(min(xs) / 1.3, max(xs) * 1.3, ML, W - MR, log=True),
            _Axis(min(ys) / 1.5 if ylog else 0.0, max(ys) * 1.15, ch.h - 52, ch.mt, log=ylog),
            'exit gauge per sheet [µm] (log)', f'{rank["unit"] or "ratio"}'
            + (' (log)' if ylog else ''))
    for x, y, lab in pts:
        px, py = ch.x(x), ch.y(y)
        ch.inner.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{COLOURS[0]}" '
                        'stroke="#111" stroke-width="0.5"/>')
        ch.inner.append(f'<text x="{px + 5:.1f}" y="{py - 5:.1f}" class="small">'
                        f'{_e(lab)}</text>')
    return ch.render(f'mech-{n}')


def _rank_section(rank, rows, n):
    items = ''.join(f'<li>{_e(x["label"])}: {x["value"]:.3g} {_e(rank["unit"])}'
                    + (' <em>(unvalidated extended-domain bite)</em>'
                       if x['unvalidated_extended_bite'] else '') + '</li>'
                    for x in rank['most_sensitive_first'])
    exc = ''.join(f'<li>{_e(x["label"])}: {_e(x["reason"])}</li>' for x in rank['excluded'])
    return (f'<h3>{_e(rank["title"])}</h3><p class="note">Most sensitive first: '
            f'{_e(rank["meaning"])}.</p>' + _mech_chart(rank, rows, n)
            + f'<details><summary>Ranking ({len(rank["most_sensitive_first"])} products)'
            f'</summary><ol>{items}</ol></details>'
            + (f'<details><summary>Excluded ({len(rank["excluded"])}) and why</summary>'
               f'<ul>{exc}</ul></details>' if exc else '<p class="note">None excluded.</p>'))


def _inputs_section(rows):
    out = []
    for r in rows:
        used = ''.join(f'<li>{_e(x["item"])}: {_e(x["basis"])} [{_e(", ".join(x["sources"]))}; '
                       f'{_e(x["read_status"] or "")}]</li>' for x in r['catalogue_values_used'])
        ass = ''.join(f'<li>{_e(x["item"])}: {_e(x["basis"])}</li>' for x in r['assumed_values'])
        pc = ', '.join(f'{x["item"]} {x["verdict"]}' for x in r['product_check'])
        nd = ', '.join(d['name'] for d in r['named_defects']) or 'none in the catalogue'
        out.append(f'<details><summary>{_e(r["label"])}: {_e(r["product_name"])}</summary>'
                   f'<p>From the catalogue:</p><ul>{used or "<li>nothing</li>"}</ul>'
                   f'<p>Assumed:</p><ul>{ass}</ul>'
                   f'<p>Product check of the survey pass: {_e(pc)}.</p>'
                   f'<p>Named defects in the catalogue: {_e(nd)}.</p>'
                   + (f'<p class="note">{_e(r["bite_note"])}</p>' if r.get('bite_note') else '')
                   + '</details>')
    return ''.join(out)


def render_survey_report(result):
    r = result
    rows = r['rows']
    mills = ''.join(
        f'<li>{_e(m["name"])} (<code>{_e(m["scenario"])}</code>): work roll radius '
        f'{m["work_roll_radius_m"]:.3g} m, strip width {m["strip_width_m"]:.3g} m, spans '
        f'{m["entry_span_length_m"]:.3g} / {m["exit_span_length_m"]:.3g} m, deflector radius '
        f'{m["deflector_roll_radius_m"]:.3g} m, coil {m["coil"]["inner_radius_m"]:.3g}-'
        f'{m["coil"]["outer_radius_m"]:.3g} m at {m["coil"]["winding_tension_pa"] * 1e-6:.3g} '
        f'MPa winding tension, span-wave limit {m["span_wave_limit_hz"]:.4g} Hz</li>'
        for m in r['mills'].values())
    head = ['#', 'product', 'survey pass', 'bite', 'dead band [I]', 'ridge height [µm]',
            'trough onset [kPa]', 'roller wrinkle [MPa]', '1 µm stripe',
            'chatter u_crit with / without bite damping', 'marks']
    body = [
        '<h1>Product survey</h1>',
        f'<div class="warn"><strong>{_e(r["status"])}</strong>: one synthetic final pass per '
        'catalogue product on one stated synthetic mill per gauge class, built from literature '
        'values; nothing here is validated against plant data.</div>',
        f'<p class="lead">{_e(r["summary"])}</p>',
        f'<section><h2>Mills</h2><ul>{mills}</ul><p class="note">Exit gauge below '
        f'{r["rules"]["foil_mill_below_exit_m"] * 1e3:.3g} mm: foil mill; otherwise the sheet '
        f'mill. Friction {r["rules"]["friction_coefficient"]:g}; tensions '
        f'{r["rules"]["entry_tension_fraction_of_flow_stress"]:g} / '
        f'{r["rules"]["exit_tension_fraction_of_flow_stress"]:g} of the flow stress; reference '
        f'stripe {r["rules"]["reference_stripe_height_m"] * 1e6:g} µm Gaussian, half-peak width '
        f'{r["rules"]["reference_stripe_half_peak_width_m"]:g} m, at the strip centre.</p>'
        '</section>',
        '<section><h2>Products</h2><p class="note">Bite-free thresholds are for the exit span '
        'and, for a doubled pass, per sheet. The stripe column gives the linear-feedback '
        'I-units of the 1 µm stripe and the stripe heights at which it buckles in the mill and '
        'after tension release. The table scrolls sideways on a narrow screen.</p>'
        + _table(head, _table_rows(rows), 'survey') + '</section>',
        '<section><h2>Rankings per mechanism</h2><p class="note">Each ranking uses only rows '
        'that carry the quantity; a not-credible bite is never ranked with credible ones; the '
        'excluded rows are listed with the reason. Rankings across the two mills compare model '
        'sensitivities, not plant defect rates.</p>'
        + ''.join(_rank_section(x, rows, i) for i, x in enumerate(r['rankings'])) + '</section>',
        f'<section><h2>Inputs per product: catalogue values and assumptions</h2>'
        f'{_inputs_section(rows)}</section>',
        '<section><h2>Limitations and sources</h2><ul>'
        + ''.join(f'<li>{_e(x)}</li>' for x in r['limitations']) + '</ul>'
        + f'<p class="note">Catalogue sources used: {_e(", ".join(r["sources"]))} (see '
        '<code>docs/thin-gauge-products.md</code> for titles, links and read status).</p>'
        '</section>']
    css = CSS + 'table.survey{min-width:72rem}'
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Product survey</title><style>{css}</style></head><body>'
            + ''.join(body) + '</body></html>\n')


def write(out_dir):
    from .__main__ import _save_complete
    result = survey()
    html = render_survey_report(result)
    out_dir = Path(out_dir)
    jp, hp = out_dir / f'{SLUG}.result.json', out_dir / f'{SLUG}.report.html'
    _save_complete(jp, result_json(result))
    _save_complete(hp, html)
    return result, jp, hp


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Product survey: one synthetic final pass per catalogue product '
                    '(literature inputs, unvalidated)')
    parser.add_argument('--out', type=Path, required=True, help='output directory')
    args = parser.parse_args(argv)
    try:
        result, jp, hp = write(args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'{result["status"]}: {len(result["rows"])} products')
    print(result['summary'])
    print(f'result: {jp}')
    print(f'report: {hp}')


if __name__ == '__main__':
    main(sys.argv[1:])
