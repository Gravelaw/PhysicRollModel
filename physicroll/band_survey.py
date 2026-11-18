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
from . import band_survey_mills
from . import band_width as bw
from . import strip_shape as ss
from .band_report import CSS, COLOURS, ML, MR, W, _Axis, _Chart, _e, _table, _tick_label

SCHEMA = 'physicroll.band_survey.v1'
STATUS = 'SYNTHETIC_SURVEY_LITERATURE_INPUTS_UNVALIDATED'
SLUG = 'product-survey'
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


USER_MILL_LIMITATION = (
    'Mill from the user\'s case file(s): its machine keys are used as entered and not verified '
    'by the tool; product and pass values remain literature values or stated assumptions '
    'unless overridden.')


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


def survey_material(p, h1):
    """The standard literature proposal for a battery product with a grade table at exit gauge
    ``h1`` (``band_products.proposed_material``), when it is a hard (H1x) temper with a
    published tensile value; else None (annealed finished tempers keep the as-rolled rule)."""
    if not bp.grade_bands(p.id):
        return None
    pr = bp.proposed_material(p.id, h1, grade='standard')
    if (pr['status'] != bp.BG_STATUS or not H1X.match(pr['temper'])
            or pr['tensile_strength_pa']['value_pa'] is None):
        return None
    return pr


def _proposal_used(pr, what='flow stress'):
    t = pr['tensile_strength_pa']
    return _used(what, t['value_pa'], 'Pa',
                 f'standard LITERATURE PROPOSAL {pr["alloy"]}-{pr["temper"]} of the '
                 f'{pr["band_label"]} band (band_products.proposed_material; {t["basis"]}; '
                 f'evidence {pr["evidence"]}; to confirm with the plant); finished tensile '
                 'strength used as an indicator of the rolling flow stress',
                 pr['sources'], pr['read_status'])


def survey_speed(p, doubled, mill):
    """(speed, used, assumed); ``mill`` is a ``_Mill`` (its default speed when none is
    published)."""
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
    v = mill.default_speed_m_s
    return v, [], [_assumed('exit speed', v, 'm/s',
                            'no published speed for this product: ' +
                            mill.default_speed_basis)]


# --------------------------------------------------------------------------- mill models
# Which case keys describe the MACHINE (stand and line) and which the PRODUCT / pass or the
# observations, decided from how the engine uses them. A mill file supplies the machine keys;
# the survey supplies the product keys (catalogue, assumptions, overrides).
MACHINE_KEYS = {
    'pass': ('width_m', 'work_roll_radius_m', 'friction_coefficient'),
    'stand': 'all', 'spans': 'all', 'kinematics': 'all', 'lubrication': 'all',
    'coolant': ('barrel_length_m', 'nozzle_pitch_m', 'standoff_m', 'spray_angle_rad',
                'offset_angle_rad', 'roll_expansion_coefficient_per_k',
                'assumed_excess_temperature_k'),
    'tribology': 'all', 'gauge_control': 'all', 'drive': 'all',
    'model_options': ('bite_damping_transit_fraction', 'max_radius_ratio', 'cells',
                      'bite_model'),
    'width_model': ('roll', 'spray_header', 'coolant_temperature_k', 'strip_centre_m',
                    'roll_heat_fraction_per_roll', 'numerics', 'rolls_carrying_stripe',
                    'shape_disturbing_coefficient', 'heredity_coefficient', 'coil',
                    'grinding', 'cooling_zone_pitch_m', 'deflector_roll_radius_m'),
}
PRODUCT_KEYS = {
    'pass': ('entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
             'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s'),
    'material': 'all', 'hardening': 'all', 'schedule': 'all', 'incoming_variation': 'all',
    'model_options': ('bite_response_override',),
    'coolant': ('blocked_nozzle_indices',),
    'width_model': ('bite_heat_per_width_w_m', 'blocked_nozzle_indices', 'nozzle_levels',
                    'events', 'gap_crown_m', 'entry_crown_m', 'incoming_ridges',
                    'previous_strip_widths_m', 'lateral_compressive_stress_pa',
                    'shape_inputs'),
    'observation': 'all', 'name': 'all', 'provenance': 'all', 'notes': 'all',
}
_CASE_SPECIFIC_WIDTH = PRODUCT_KEYS['width_model']


def machine_keys_taken(case):
    """Dotted machine keys a mill case supplies (sections present in the file)."""
    out = []
    for sec, ks in MACHINE_KEYS.items():
        if case.get(sec) is None:
            continue
        if ks == 'all':
            out.append(sec)
        else:
            out += [f'{sec}.{k}' for k in ks if k in case[sec]]
    return out


def _machine_case(case, where):
    """The mill case with the product / case-specific keys reset (validated case dict)."""
    if case.get('case_schema') != bd.CASE_SCHEMA_V2:
        raise ValueError(f'{where}: the mill file must be a {bd.CASE_SCHEMA_V2} case')
    if case.get('width_model') is None:
        raise ValueError(f'{where}: the mill file needs a width_model (roll, spray header, '
                         'coil and deflector of the line)')
    if case['model_options']['bite_response_override'] is not None:
        raise ValueError(f'{where}: model_options.bite_response_override is a pass-specific '
                         'bite and cannot describe a mill; set it to null')
    c = copy.deepcopy(case)
    for k in _CASE_SPECIFIC_WIDTH:
        c['width_model'][k] = copy.deepcopy(bw.WIDTH_DEFAULTS[k])
    if c.get('coolant') is not None:
        c['coolant']['blocked_nozzle_indices'] = []
    c['material']['youngs_modulus_pa'] = ss.ALUMINIUM_E_PA
    return c


def _describe(case, kind, name, source, user):
    p, st, sp, w = case['pass'], case['stand'], case['spans'], case['width_model']
    desc = {'kind': kind, 'name': name, 'scenario': source,
            'work_roll_radius_m': p['work_roll_radius_m'], 'strip_width_m': p['width_m'],
            'backup_roll_diameter_m': case['kinematics']['backup_roll_diameter_m'],
            'work_roll_mass_kg': st['work_roll_mass_kg'],
            'backup_roll_mass_kg': st['backup_roll_mass_kg'],
            'work_backup_contact_stiffness_n_m': st['work_backup_contact_stiffness_n_m'],
            'housing_stiffness_n_m': st['housing_stiffness_n_m'],
            'entry_span_length_m': sp['entry_span_length_m'],
            'exit_span_length_m': sp['exit_span_length_m'],
            'deflector_roll_radius_m': w['deflector_roll_radius_m'],
            'coil': None if w['coil'] is None else dict(w['coil']),
            'barrel_length_m': w['roll']['barrel_length_m'],
            'bite_model': case['model_options']['bite_model'],
            'bite_damping_transit_fraction': case['model_options'][
                'bite_damping_transit_fraction'],
            'span_wave_limit_hz': bd._span_wave_limit_hz(case)}
    if user:
        # keys only for a user-supplied mill, so the default survey keeps its exact content
        desc.update(source='user mill file', file=source,
                    keys_taken=machine_keys_taken(case),
                    keys_not_taken=sorted(PRODUCT_KEYS),
                    friction_coefficient=p['friction_coefficient'],
                    default_speed_m_s=p['exit_speed_m_s'])
    return desc


def load_mill_file(path, kind):
    """Validated machine case and description from a user's v2 case file."""
    path = Path(path)
    try:
        case = bd.load_case(path)
    except (ValueError, OSError) as exc:
        raise ValueError(f'mill file {path}: {exc}') from exc
    case = _machine_case(case, f'mill file {path}')
    return case, _describe(case, kind, f'user mill from {path.name}', path.name, True)


# placeholder product side of a default mill case (every value is replaced per product)
_PLACEHOLDER_PASS = {
    'foil': {'entry_thickness_m': 5e-05, 'exit_thickness_m': 3e-05,
             'mean_flow_stress_pa': 175e6, 'entry_tension_pa': 35e6, 'exit_tension_pa': 40e6},
    'sheet': {'entry_thickness_m': 3e-04, 'exit_thickness_m': 2.1e-04,
              'mean_flow_stress_pa': 270e6, 'entry_tension_pa': 25e6, 'exit_tension_pa': 30e6}}


def default_mill_case(kind):
    """A validated v2 case of a default mill: the packaged machine sections
    (``band_survey_mills.MACHINES``, generated from the demo scenarios) with a placeholder
    product side. Needs no file from the repository checkout (review finding: the survey
    used to read ``scenarios/`` next to the package, absent in a wheel installation)."""
    m = copy.deepcopy(band_survey_mills.MACHINES[kind])
    w = dict(copy.deepcopy(bw.WIDTH_DEFAULTS), **m['width_model'])
    case = {
        'case_schema': bd.CASE_SCHEMA_V2, 'name': f'default {kind} mill', 'synthetic': True,
        'provenance': f'machine of the demo scenario {MILLS[kind]["scenario"]} (packaged)',
        'pass': dict(m['pass'], exit_speed_m_s=MILLS[kind]['default_speed_m_s'],
                     **_PLACEHOLDER_PASS[kind]),
        'material': {'alloy': 'placeholder', 'temper': 'H18',
                     'yield_stress_pa': _PLACEHOLDER_PASS[kind]['mean_flow_stress_pa'],
                     'youngs_modulus_pa': ss.ALUMINIUM_E_PA, 'luders_strain': None,
                     'magnesium_wt_pct': None, 'grain_size_m': None},
        'stand': m['stand'], 'spans': m['spans'], 'kinematics': m['kinematics'],
        'lubrication': m['lubrication'],
        'coolant': (None if m['coolant'] is None
                    else dict(m['coolant'], blocked_nozzle_indices=[])),
        'model_options': dict(m['model_options'], bite_response_override=None),
        'observation': {k: ([] if k in ('pitch_observations',
                                        'band_positions_across_width_m') else None)
                        for k in bd.OBS_KEYS + bw.OBS_V2_ALL},
        'schedule': [], 'width_model': w, 'tribology': m['tribology'], 'hardening': None,
        'gauge_control': m['gauge_control'], 'drive': m['drive'], 'incoming_variation': None}
    return bd.validate_case(case)


def _load_mill(kind):
    case = _machine_case(default_mill_case(kind), MILLS[kind]['scenario'])
    return case, _describe(case, kind, MILLS[kind]['name'], MILLS[kind]['scenario'], False)


class _Mill:
    def __init__(self, kind, loaded=None):
        self.kind = kind
        self.user = loaded is not None
        self.case, self.desc = loaded if loaded is not None else _load_mill(kind)
        self.cache = bd._BiteCache(self.case)
        self.stand = bd._stand(self.case)
        self.spans = bd._spans(self.case)
        self.beta = self.case['model_options']['bite_damping_transit_fraction']
        if self.user:
            self.friction = self.case['pass']['friction_coefficient']
            self.friction_basis = (f'from the mill file {self.desc["file"]} '
                                   '(pass.friction_coefficient)')
            self.default_speed_m_s = self.case['pass']['exit_speed_m_s']
            self.default_speed_basis = (f'the mill file\'s pass speed '
                                        f'({self.default_speed_m_s * 60:.4g} m/min)')
        else:
            self.friction = FRICTION
            self.friction_basis = 'the demos\' supplied 0.03 (no catalogue value)'
            self.default_speed_m_s = MILLS[kind]['default_speed_m_s']
            self.default_speed_basis = MILLS[kind]['default_speed_basis']
        w = self.case['width_model']
        length = w['roll']['barrel_length_m']
        n = max(4, int(round(length / bw.ONSET_GRID_M)))
        self.z = [i * length / n for i in range(n + 1)]
        self.centre = (w['strip_centre_m'] if w['strip_centre_m'] is not None
                       else length / 2)
        # the grid point nearest the strip centre carries the stripe peak
        self.centre = min(self.z, key=lambda x: abs(x - self.centre))

    def case_for(self, row, sigma, width=None):
        c = copy.deepcopy(self.case)
        c['pass'].update({k: row[k] for k in (
            'entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa',
            'friction_coefficient', 'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s')})
        if width is not None:
            c['pass']['width_m'] = width
        c['material']['yield_stress_pa'] = sigma
        c['schedule'] = [row]
        return c


def bite_free(mill, h1, sigma, exit_tension, width=None):
    """Bite-free thresholds of one sheet (the engine's strip_shape calls)."""
    d = mill.desc
    width = d['strip_width_m'] if width is None else width
    out = {}
    win = ss.shohet_townsend_window(h1, width)
    out['dead_band_half_width_i_units'] = (win['upper_bound_i_units']
                                           - win['lower_bound_i_units']) / 2
    coil = d['coil']
    try:
        if coil is None:
            raise ValueError('the mill has no width_model.coil')
        cb = ss.coil_ridge_buildup(0.0, h1, coil['inner_radius_m'], coil['outer_radius_m'],
                                   sigma, coil['winding_tension_pa'], ss.ALUMINIUM_E_PA,
                                   coil['compaction_factor'] or ss.DEFAULT_COMPACTION_FACTOR)
        out['critical_ridge_height_m'] = cb['critical_ridge_height_at_outer_radius_m']
    except ValueError as exc:
        out['critical_ridge_height_m'] = None
        out['critical_ridge_error'] = str(exc)
    tr = ss.tension_trough_screen(h1, d['exit_span_length_m'], exit_tension, width,
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
    dom = {f'{k}_onset_domain_limit_m': on[f'{n}_domain_limit'] * peak
           for k, n in (('in_mill', 'mill'), ('after_release', 'released'))
           if f'{n}_domain_limit' in on}          # keys only then: never an onset
    return {**dom, 'linear_feedback_i_units': lv['linear_feedback_peak_i_units'],
            'state_in_mill': st['state'],
            'state_after_tension_release': st['state_after_tension_release'],
            'in_mill_onset_height_m': h(on['mill']),
            'after_release_onset_height_m': h(on['released']),
            'reporting_onset_height_m': h(on['reporting']),
            'after_release_onset_limited_by_reporting_threshold': bw._limited(
                on['released'], on['reporting']),
            'onset_search_ceiling_m': bw.ONSET_SEARCH_MAX_M}


# --------------------------------------------------------------------------- one product
OVERRIDE_KEYS = ('entry_thickness_m', 'exit_thickness_m', 'mean_flow_stress_pa', 'exit_speed_m_s',
                 'entry_tension_pa', 'exit_tension_pa', 'friction_coefficient', 'width_m',
                 'doubled')
_OVERRIDE_ITEMS = {   # override key -> provenance items it replaces
    'entry_thickness_m': ('final pass gauges', 'exit gauge', 'reduction'),
    'exit_thickness_m': ('final pass gauges', 'exit gauge', 'reduction'),
    'mean_flow_stress_pa': ('flow stress',), 'exit_speed_m_s': ('exit speed',),
    'entry_tension_pa': ('tensions',), 'exit_tension_pa': ('tensions',),
    'friction_coefficient': ('friction',), 'width_m': (), 'doubled': ('rolling mode',)}
_OVERRIDE_UNITS = {'entry_thickness_m': 'm', 'exit_thickness_m': 'm',
                   'mean_flow_stress_pa': 'Pa', 'exit_speed_m_s': 'm/s',
                   'entry_tension_pa': 'Pa', 'exit_tension_pa': 'Pa',
                   'friction_coefficient': '', 'width_m': 'm', 'doubled': ''}


def validate_overrides(raw, where='overrides'):
    """Strict per-product overrides ``{product_id: {key: value}}`` of the survey pass."""
    if not isinstance(raw, dict):
        raise ValueError(f'{where} must be a JSON object {{product_id: {{key: value}}}}')
    ids = bp.product_ids()
    out = {}
    for pid, ov in raw.items():
        if pid not in ids:
            raise ValueError(f'{where}: unknown product id {pid!r}; valid ids: {", ".join(ids)}')
        if not isinstance(ov, dict) or not ov:
            raise ValueError(f'{where}.{pid} must be a nonempty JSON object')
        bad = [k for k in ov if k not in OVERRIDE_KEYS]
        if bad:
            raise ValueError(f'{where}.{pid}: unknown key(s) {", ".join(map(repr, bad))}; '
                             f'allowed: {", ".join(OVERRIDE_KEYS)}')
        clean = {}
        for k, v in ov.items():
            name = f'{where}.{pid}.{k}'
            if k == 'doubled':
                if not isinstance(v, bool):
                    raise ValueError(f'{name} must be true or false')
                clean[k] = v
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f'{name} must be a finite number')
            v = float(v)
            if k == 'friction_coefficient':
                if not 0 < v < 1:
                    raise ValueError(f'{name} must be in (0, 1)')
            elif k in ('entry_tension_pa', 'exit_tension_pa'):
                if v < 0:
                    raise ValueError(f'{name} must be >= 0')
            elif v <= 0:
                raise ValueError(f'{name} must be > 0')
            clean[k] = v
        out[pid] = clean
    return out


def load_overrides(path):
    path = Path(path)
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f'overrides file {path}: {exc}') from exc
    return validate_overrides(raw, f'overrides file {path.name}')


def survey_row(p, mills, index, override=None, override_source='overrides file'):
    sp = survey_pass(p)
    h0, h1, dbl = sp['entry_thickness_m'], sp['exit_thickness_m'], sp['doubled']
    ov = override or {}
    h0, h1 = ov.get('entry_thickness_m', h0), ov.get('exit_thickness_m', h1)
    dbl = ov.get('doubled', dbl)
    if not h1 < h0:
        raise ValueError(f'{p.id}: the survey pass needs exit_thickness_m < entry_thickness_m '
                         f'(got {h0:g} -> {h1:g} m after overrides)')
    kind = 'foil' if h1 < FOIL_MILL_MAX_EXIT_M else 'sheet'
    mill = mills[kind]
    sigma, temper, used_s, assumed_s = survey_flow_stress(p)
    proposal = survey_material(p, h1)
    if proposal is not None:
        # SPEC13: battery products with a grade table take the strength from the literature
        # proposal for the survey pass's exit gauge instead of the product-wide median
        sigma, temper = proposal['tensile_strength_pa']['value_pa'], proposal['temper']
        used_s, assumed_s = [_proposal_used(proposal)], []
    u, used_u, assumed_u = survey_speed(p, dbl, mill)
    sigma = ov.get('mean_flow_stress_pa', sigma)
    u = ov.get('exit_speed_m_s', u)
    t_in = ov.get('entry_tension_pa', ENTRY_TENSION_FRACTION * sigma)
    t_out = ov.get('exit_tension_pa', EXIT_TENSION_FRACTION * sigma)
    mu = ov.get('friction_coefficient', mill.friction)
    width = ov.get('width_m')
    alloy = proposal['alloy'] if proposal is not None else p.alloys[0].name
    assumed = sp['assumed'] + assumed_s + assumed_u + [
        _assumed('tensions', [t_in, t_out], 'Pa',
                 f'entry {ENTRY_TENSION_FRACTION:g} and exit {EXIT_TENSION_FRACTION:g} of the '
                 'flow stress [D, stated]'),
        _assumed('friction', mu, '', mill.friction_basis),
        _assumed('mill', kind, '', mill.desc['name'] + (
            ': the user\'s mill for every product of this gauge class' if mill.user else
            ': the same synthetic mill for every product of this gauge class')),
        _assumed('alloy for the product check', alloy, '',
                 'the standard literature proposal for the exit gauge (to confirm with the '
                 'plant)' if proposal is not None else
                 'first alloy listed for the product in the catalogue')]
    used = sp['used'] + used_s + used_u
    user = []
    if ov:
        gone = {i for k in ov for i in _OVERRIDE_ITEMS[k]}
        used = [x for x in used if x['item'] not in gone]
        assumed = [x for x in assumed if x['item'] not in gone]
        for k in OVERRIDE_KEYS:
            if k in ov:
                user.append({'item': k, 'value': ov[k], 'unit': _OVERRIDE_UNITS[k],
                             'basis': f'user-supplied ({override_source})'})
        for k, v in (('entry_thickness_m', h0), ('exit_thickness_m', h1)):
            if k not in ov and gone & {'final pass gauges'}:
                assumed.append(_assumed(k, v, 'm', 'kept from the survey rule while the '
                                        'other gauge is user-supplied'))
        if ('entry_tension_pa' in ov) != ('exit_tension_pa' in ov):
            k = 'exit_tension_pa' if 'entry_tension_pa' in ov else 'entry_tension_pa'
            assumed.append(_assumed(k, t_out if k == 'exit_tension_pa' else t_in, 'Pa',
                                    'stated fraction of the flow stress (the other tension '
                                    'is user-supplied)'))
    statuses = [x['read_status'] for x in used if x.get('read_status')]
    out = {'index': index, 'product_id': p.id, 'product_name': p.name, 'family': p.family,
           'mill': kind, 'label': f'{index} {p.id}',
           'entry_thickness_m': h0, 'exit_thickness_m': h1,
           'reduction_fraction': 1 - h1 / h0, 'doubled': dbl,
           'rolling_mode_published': p.rolled_mode, 'gauge_basis': sp['gauge_basis'],
           'schedule': sp['schedule'], 'final_temper': temper, 'alloy_checked': alloy,
           'mean_flow_stress_pa': sigma,
           'material_proposal': (None if proposal is None else {
               k: proposal[k] for k in ('status', 'alloy', 'temper', 'band_id', 'band_label',
                                        'evidence', 'rule', 'sources')}
               | {'tensile_strength_pa': proposal['tensile_strength_pa']['value_pa'],
                  'proof_strength_pa': proposal['proof_strength']['value_pa'],
                  'proof_strength_published': proposal['proof_strength']['published']}),
           'flow_stress_assumed': bool(assumed_s) and 'mean_flow_stress_pa' not in ov,
           'entry_tension_pa': t_in, 'exit_tension_pa': t_out, 'exit_speed_m_s': u,
           'friction_coefficient': mu,
           'catalogue_values_used': used, 'assumed_values': assumed,
           'weakest_read_status': bp._weakest(statuses) if statuses else None,
           'vendor_level_input': any(s in ('vendor_or_trade_page', 'memory_unverified')
                                     for s in statuses),
           'closed_gap_likely': h1 < CLOSED_GAP_BELOW_M,
           'flags': []}
    if user:
        out['user_supplied_values'] = user
    if width is not None:
        out['strip_width_m'] = width
    if h1 < CLOSED_GAP_BELOW_M:
        out['flags'].append(bd.CLOSED_GAP_FLAG)
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
    try:
        bf = bite_free(mill, h1, sigma, t_out, width)
    except ValueError as exc:
        # the mill cannot take this pass (a domain guard): a rejected row, not a crash
        out.update(bite_status='REJECTED', rejected=f'rejected by the mill: {exc}',
                   bite_note=f'rejected by the mill: {exc}')
        return out
    out.update(bf)
    if dbl:
        out['bite_status'] = 'DOUBLED_PASS_NOT_MODELLED'
        out['bite_note'] = (f'{DOUBLED_NOT_MODELLED}: the tool has no model of two sheets in '
                            'one bite; bite-free thresholds are per sheet')
        out['flags'].append('DOUBLED_FINAL_PASS_NOT_MODELLED')
        return out
    row = {'label': out['label'], 'entry_thickness_m': h0, 'exit_thickness_m': h1,
           'mean_flow_stress_pa': sigma, 'friction_coefficient': mu,
           'entry_tension_pa': t_in, 'exit_tension_pa': t_out, 'exit_speed_m_s': u}
    case = mill.case_for(row, sigma, width)
    cache = mill.cache if width is None else bd._BiteCache(case)
    sw = bd._schedule_rows(case, cache, mill.stand, mill.spans, mill.beta)['rows'][0]
    if 'rejected' in sw:
        out['bite_status'] = 'NO_BITE'
        out['bite_note'] = sw['rejected']
        out['rejected'] = f'no roll bite: {sw["rejected"]}'
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
    bite = cache.get(bd._bite_pass(case, row))
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
    try:
        out['stripe'] = _stripe(mill, case, bite, row)
    except ValueError as exc:
        out['stripe_error'] = str(exc)
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


def _domain(r, key):
    st = r.get('stripe') or {}
    return {'cooling_stripes_in_mill': st.get('in_mill_onset_domain_limit_m'),
            'cooling_stripes_after_release': st.get('after_release_onset_domain_limit_m')
            }.get(key)


def rankings(rows):
    out = []
    for key, title, get, scale, unit, needs_bite, small_first, meaning in MECHANISMS:
        ranked, excluded = [], []
        for r in rows:
            why = None
            if r.get('bite_status') == 'REJECTED':
                why = r['rejected']
            elif needs_bite and r['bite_status'] != 'BITE':
                why = (DOUBLED_NOT_MODELLED if r['bite_status'] == 'DOUBLED_PASS_NOT_MODELLED'
                       else r.get('rejected') or 'no roll bite')
            elif needs_bite and not _credible(r):
                why = 'bite NOT CREDIBLE (force outside the range reported for battery foil)'
            elif key == 'chatter_margin' and bd._outside_scan(r['exit_speed_m_s']):
                why = ('survey speed outside the critical-speed scan (the margin is not '
                       'assessable there)')
            elif key == 'chatter_margin' and r.get('chatter_reliability') != \
                    'WITHIN_SPAN_WAVE_LIMIT':
                why = 'chatter onset above the span-wave limit (not reliable)'
            elif get(r) is None and _domain(r, key):
                why = bw.domain_limit_text(_domain(r, key))
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


def summary(rows, ranks, user_mill=False):
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
    parts.append(('These are model sensitivities on the user\'s mill with literature inputs '
                  'unless overridden, not plant defect rates.') if user_mill else
                 ('These are model sensitivities on one synthetic mill per gauge class with '
                  'literature inputs, not plant defect rates.'))
    return ' '.join(parts)


# --------------------------------------------------------------------------- battery grade matrix
GRADE_MATRIX_GAUGES_UM = (20, 18, 15, 13, 12, 10)
GRADE_MATRIX_PLANT_ROUTES = {
    18: (30, 'plant route 50 -> 30 -> 18 um, its second pass (the 30 um intermediate is the '
             'battery demo\'s assumption)'),
    12: (25, 'plant route 50 -> 25 -> 12 um, its second pass (the 25 um intermediate is the '
             'battery demo\'s assumption)')}
RIDGE_STRENGTH_BASIS = (
    'critical ridge height computed with the proposal\'s proof strength Rp0.2 as the yield '
    'stress of the wound foil (the coil-ridge criterion is a yield criterion; Rp0.2 is '
    'published only for some grades, otherwise assumed from the median Rp0.2/Rm ratio, see '
    'band_products.proposed_material); the main survey table uses the flow stress there, '
    'kept here as critical_ridge_height_at_flow_stress_m for comparison')


def _matrix_pass(p, g_um):
    """(entry m, exit m, basis, sources): the plant route where the gauge matches, else the
    nearest published single-sheet single pass of the product (reduction kept)."""
    h1 = g_um * 1e-6
    if g_um in GRADE_MATRIX_PLANT_ROUTES:
        e, why = GRADE_MATRIX_PLANT_ROUTES[g_um]
        return e * 1e-6, h1, why, []
    cands = []
    for s in p.schedules:
        g, passes = s.gauges(), s.passes()
        for i in range(s.steps()):
            if passes[i] != 1 or s.is_doubled(i):
                continue
            x0, x1 = _gmid(*g[i]), _gmid(*g[i + 1])
            cands.append((abs(math.log(x1 / h1)), s.label, i, x0, x1, s))
    _, label, i, x0, x1, s = min(cands, key=lambda c: c[:3])
    h0 = _sig(h1 * x0 / x1)
    why = (f'nearest published single-sheet pass {x0 * 1e6:.4g} -> {x1 * 1e6:.4g} um of '
           f'"{label}" (step {i + 1})')
    if abs(x1 - h1) > 1e-12:
        why += f', reduction kept and exit set to {g_um:g} um'
    return h0, h1, why, list(s.sources)


_CELL_KEYS = ('entry_thickness_m', 'exit_thickness_m', 'reduction_fraction', 'mill',
              'mean_flow_stress_pa', 'entry_tension_pa', 'exit_tension_pa', 'exit_speed_m_s',
              'bite_status', 'bite_model', 'bite_flags', 'separating_force_per_width_n_m',
              'bite_credibility', 'bite_force_ratio_to_reported_range', 'extended_domain_flags',
              'dead_band_half_width_i_units', 'trough_onset_lateral_stress_pa',
              'roller_wrinkle_threshold_pa', 'stripe', 'critical_exit_speed_m_s',
              'critical_exit_speed_without_bite_damping_m_s', 'speed_ratio_without_bite_damping',
              'chatter_reliability', 'rejected')


def _matrix_cell(p, mills, g_um, grade):
    h0, h1, why, srcs = _matrix_pass(p, g_um)
    pr = bp.proposed_material(p.id, h1, grade=grade)
    cell = {'gauge_um': g_um, 'grade': grade, 'pass_basis': why, 'pass_sources': srcs,
            'proposal_status': pr['status']}
    if pr['status'] != bp.BG_STATUS or pr['tensile_strength_pa']['value_pa'] is None:
        cell.update(status='NO_PROPOSAL', reason=pr.get('reason') or 'no tensile value')
        return cell
    sigma = pr['tensile_strength_pa']['value_pa']
    rp = pr['proof_strength']['value_pa']
    row = survey_row(p, mills, 0, {'entry_thickness_m': h0, 'exit_thickness_m': h1,
                                   'mean_flow_stress_pa': sigma}, 'battery grade matrix')
    fallback = 'no usual choice' in pr['rule']
    cell.update(status='EVALUATED', alloy=pr['alloy'], temper=pr['temper'],
                band_id=pr['band_id'], band_label=pr['band_label'],
                tensile_strength_pa=sigma, proof_strength_pa=rp,
                proof_strength_published=pr['proof_strength']['published'],
                evidence=pr['evidence'], proposal_rule=pr['rule'],
                fallback_rule_weak=fallback, proposal_sources=pr['sources'],
                **{k: row.get(k) for k in _CELL_KEYS if k in row})
    cell['critical_ridge_height_at_flow_stress_m'] = row.get('critical_ridge_height_m')
    try:
        cell['critical_ridge_height_m'] = bite_free(mills['foil'], h1, rp,
                                                    row['exit_tension_pa'])[
            'critical_ridge_height_m']
    except ValueError:
        cell['critical_ridge_height_m'] = None
    cell['credible'] = row.get('bite_status') == 'BITE' and _credible(row)
    if row.get('bite_status') != 'BITE':
        cell['bite_excluded_reason'] = row.get('rejected') or row.get('bite_note') or 'no bite'
    elif not _credible(row):
        cell['bite_excluded_reason'] = (
            f'bite NOT CREDIBLE (force x{row["bite_force_ratio_to_reported_range"]:.3g} the '
            'reported battery-foil range)')
    return cell


def _pct(a, b):
    return (b / a - 1) * 100


def _span_txt(vals, scale, unit, d=3):
    return f'{vals[0] * scale:.{d}g} -> {vals[-1] * scale:.{d}g} {unit}'


def _grade_sentences(cells):
    by = {(c['gauge_um'], c['grade']): c for c in cells if c['status'] == 'EVALUATED'}
    gauges = list(GRADE_MATRIX_GAUGES_UM)
    parts = []
    for grade in bp.GRADES:
        cs = [by[(g, grade)] for g in gauges if (g, grade) in by]
        if len(cs) < 2:
            continue
        free = []
        for key, scale, unit, name, absval in (
                ('critical_ridge_height_m', 1e6, 'um', 'critical ridge height', False),
                ('trough_onset_lateral_stress_pa', 1e-3, 'kPa', 'trough onset magnitude', True),
                ('roller_wrinkle_threshold_pa', 1e-6, 'MPa', 'roller-wrinkle threshold '
                 'magnitude', True)):
            v = [c.get(key) for c in cs]
            if any(x is None for x in v):
                continue
            v = [abs(x) if absval else x for x in v]
            free.append(f'{name} {_span_txt(v, scale, unit)}')
        cred = [c for c in cs if c['credible']]
        excl = [f'{c["gauge_um"]:g} um' for c in cs if not c['credible']]
        bd_txt = ''
        on = [(c['gauge_um'], (c.get('stripe') or {}).get('in_mill_onset_height_m'))
              for c in cred]
        on = [x for x in on if x[1] is not None]
        if len(on) >= 2:
            bd_txt = (f'; on credible bites only ({", ".join(f"{g:g}" for g, _ in on)} um) the '
                      f'in-mill stripe onset height goes {on[0][1] * 1e6:.3g} -> '
                      f'{on[-1][1] * 1e6:.3g} um from {on[0][0]:g} to {on[-1][0]:g} um')
        elif cred:
            bd_txt = '; fewer than two credible bites, so no bite-dependent gauge trend'
        parts.append(f'{grade.replace("_", "-")} grade, {cs[0]["gauge_um"]:g} -> '
                     f'{cs[-1]["gauge_um"]:g} um: ' + ', '.join(free) + bd_txt
                     + (f' (bite-dependent results excluded at {", ".join(excl)}: not credible '
                        'or no bite)' if excl else ''))
    rises = []
    for grade in bp.GRADES:
        cs = [by[(g, grade)] for g in gauges if (g, grade) in by]
        for k, name in (('critical_ridge_height_m', 'critical ridge height'),
                        ('trough_onset_lateral_stress_pa', 'trough onset'),
                        ('roller_wrinkle_threshold_pa', 'roller-wrinkle threshold')):
            for a, b in zip(cs, cs[1:]):
                if a.get(k) is not None and b.get(k) is not None and \
                        abs(b[k]) > abs(a[k]) * (1 + 1e-9):
                    rises.append(
                        f'{grade.replace("_", "-")} {name} rises from {a["gauge_um"]:g} to '
                        f'{b["gauge_um"]:g} um because the proposal steps from '
                        f'{a["alloy"]} {a["tensile_strength_pa"] * 1e-6:.0f} to {b["alloy"]} '
                        f'{b["tensile_strength_pa"] * 1e-6:.0f} MPa between the bands')
    gauge_sentence = ('At fixed grade, thinner foil lowers the bite-free thresholds'
                      + (' except where the proposed strength steps up between bands ('
                         + '; '.join(rises) + ')' if rises else ' at every step')
                      + ': ' + '; '.join(parts) + '.')
    rows, weak, both = [], [], []
    for g in gauges:
        s, h = by.get((g, 'standard')), by.get((g, 'high_strength'))
        if not s or not h:
            continue
        for c in (s, h):
            if c['fallback_rule_weak']:
                weak.append(f'the {c["grade"].replace("_", "-")} proposal at {g:g} um '
                            f'({c["alloy"]})')
        txt = (f'{g:g} um {s["alloy"]} {s["tensile_strength_pa"] * 1e-6:.0f} -> {h["alloy"]} '
               f'{h["tensile_strength_pa"] * 1e-6:.0f} MPa (Rm {_pct(s["tensile_strength_pa"], h["tensile_strength_pa"]):+.0f} %, '
               f'ridge {_pct(s["critical_ridge_height_m"], h["critical_ridge_height_m"]):+.0f} %, '
               f'trough {_pct(abs(s["trough_onset_lateral_stress_pa"]), abs(h["trough_onset_lateral_stress_pa"])):+.0f} %')
        if s['credible'] and h['credible']:
            a = (s.get('stripe') or {}).get('in_mill_onset_height_m')
            b = (h.get('stripe') or {}).get('in_mill_onset_height_m')
            if a is not None and b is not None:
                txt += f', in-mill stripe onset {_pct(a, b):+.0f} %'
                both.append(f'{g:g}')
        rows.append(txt + ')')
    grade_sentence = (
        'At fixed gauge, the high-strength proposal instead of the standard one: '
        + '; '.join(rows) + '. Ridge height follows the proof strength and the trough and '
        'roller-wrinkle thresholds follow the tensions, set as fixed fractions of the flow '
        'stress in this survey; bite-dependent changes are given only where both bites are '
        'credible' + (f' ({", ".join(both)} um)' if both else ' (none)') + '.'
        + (f' Evidence WEAK (fallback rule: no usual choice of that grade is published for '
           f'the band, so the option with the highest standard minimum is used): '
           f'{"; ".join(weak)}. These rows are less supported than those where the research '
           'names a usual choice.' if weak else ''))
    return gauge_sentence, grade_sentence


def battery_grade_matrix(mills):
    """SPEC13 2.3: the battery collector foil at 20, 18, 15, 13, 12 and 10 um, standard and
    high-strength literature proposals, on the foil mill (literature strengths, synthetic mill,
    extended-domain bites flagged, non-credible bites excluded from every comparison)."""
    p = bp.product(LOAD_RANGE_PRODUCT)
    cells = [_matrix_cell(p, mills, g, grade) for g in GRADE_MATRIX_GAUGES_UM
             for grade in bp.GRADES]
    gauge_sentence, grade_sentence = _grade_sentences(cells)
    return {'status': bp.BG_STATUS, 'product_id': p.id, 'mill': mills['foil'].desc['name'],
            'gauges_um': list(GRADE_MATRIX_GAUGES_UM), 'grades': list(bp.GRADES),
            'cells': cells, 'ridge_strength_basis': RIDGE_STRENGTH_BASIS,
            'gauge_sentence': gauge_sentence, 'grade_sentence': grade_sentence,
            'rules': 'final pass: the plant route where the gauge matches (18 and 12 um), else '
                     'the nearest published single-sheet pass of the product; tensions, '
                     'friction and speed by the survey rules; a bite outside the reported '
                     'battery-foil force range is NOT CREDIBLE and excluded from every '
                     'bite-dependent comparison and sentence',
            'note': 'Literature strengths (proposals to confirm with the plant) on a synthetic '
                    'mill; model sensitivities, not plant defect rates.'}


# --------------------------------------------------------------------------- top level
def select_products(ids):
    """Catalogue products (with their catalogue index) restricted to ``ids`` (None: all)."""
    allp = list(enumerate(bp.products(), 1))
    if ids is None:
        return allp
    valid = bp.product_ids()
    bad = [x for x in ids if x not in valid]
    if bad or not ids:
        raise ValueError(f'unknown product id(s) {", ".join(map(repr, bad)) or "(none given)"}; '
                         f'valid ids: {", ".join(valid)}')
    return [(i, p) for i, p in allp if p.id in ids]


def survey(products=None, foil_mill=None, sheet_mill=None, overrides=None,
           override_source='overrides file'):
    """The survey result (see ``survey_with_mills``)."""
    return survey_with_mills(products, foil_mill, sheet_mill, overrides, override_source)[0]


def survey_with_mills(products=None, foil_mill=None, sheet_mill=None, overrides=None,
                      override_source='overrides file'):
    """Run the survey. ``products``: ids to keep (None: all); ``foil_mill`` / ``sheet_mill``:
    paths of v2 case files whose machine keys replace the demo mills; ``overrides``: validated
    per-product overrides (``validate_overrides``). Without options the result equals the
    committed artifact."""
    mills = {'foil': _Mill('foil', None if foil_mill is None else
                           load_mill_file(foil_mill, 'foil')),
             'sheet': _Mill('sheet', None if sheet_mill is None else
                            load_mill_file(sheet_mill, 'sheet'))}
    overrides = overrides or {}
    rows = [survey_row(p, mills, i, overrides.get(p.id), override_source)
            for i, p in select_products(products)]
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
              'rows': rows, 'rankings': ranks,
              'battery_grade_matrix': (battery_grade_matrix(mills) if any(
                  r['product_id'] == LOAD_RANGE_PRODUCT for r in rows) else None),
              'summary': summary(rows, ranks, any(m.user for m in mills.values())),
              'limitations': ([USER_MILL_LIMITATION] + list(LIMITATIONS[1:])
                              if any(m.user for m in mills.values()) else list(LIMITATIONS))
              + list(bp.LIMITATIONS),
              'sources': sorted({s for r in rows for x in r['catalogue_values_used']
                                 for s in x['sources']})}
    opts = {}
    if products is not None:
        opts['products'] = [r['product_id'] for r in rows]
    if foil_mill is not None or sheet_mill is not None:
        opts['mill_files'] = {k: m.desc['file'] for k, m in mills.items() if m.user}
    if overrides:
        opts['overrides'] = {'source': override_source, 'products': sorted(overrides)}
    if opts:
        # key only with options, so the default survey keeps its exact content
        result['options'] = opts
        result['synthetic'] = not any(m.user for m in mills.values()) and not overrides
    json.dumps(result, allow_nan=False)
    return result, mills


def result_json(result):
    return bd.result_json(result)


# --------------------------------------------------------------------------- report
def _f(v, scale=1.0, d=3):
    if v is None:
        return '–'
    return f'{v * scale:.{d}g}'


def _cell_bite(r, text):
    if r['bite_status'] == 'REJECTED':
        return f'<em>{_e(r["rejected"])}</em>'
    if r['bite_status'] == 'DOUBLED_PASS_NOT_MODELLED':
        return f'<em>{_e(DOUBLED_NOT_MODELLED)}</em>'
    if r['bite_status'] != 'BITE':
        return f'<em>{_e(r.get("rejected") or "no roll bite")}</em>'
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


def _onset(h, dom=None):
    if h is None and dom:
        return bw.domain_limit_text(dom).replace(' um', ' µm')
    return (f'not reached within {bw.ONSET_SEARCH_MAX_M * 1e6:.3g} µm' if h is None
            else f'{h * 1e6:.3g} µm')


def _table_rows(rows):
    out = []
    for r in rows:
        st = r.get('stripe') or {}
        dm = st.get('in_mill_onset_domain_limit_m')
        dr = st.get('after_release_onset_domain_limit_m')
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
            _e(_f(r.get('dead_band_half_width_i_units'))),
            _e(_f(r.get('critical_ridge_height_m'), 1e6)),
            _e(_f(r.get('trough_onset_lateral_stress_pa'), 1e-3)),
            _e(_f(r.get('roller_wrinkle_threshold_pa'), 1e-6)),
            _cell_bite(r, lambda: _e(f'{_f(st.get("linear_feedback_i_units"))} I; in mill '
                                     f'{_onset(st.get("in_mill_onset_height_m"), dm)}; '
                                     f'after release '
                                     f'{_onset(st.get("after_release_onset_height_m"), dr)}'
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


def _matrix_chart(m):
    series = []
    for i, grade in enumerate(bp.GRADES):
        pts = [(c['gauge_um'], c['critical_ridge_height_m'] * 1e6, c['fallback_rule_weak'])
               for c in m['cells'] if c['grade'] == grade and c['status'] == 'EVALUATED'
               and c.get('critical_ridge_height_m')]
        series.append((grade, COLOURS[i], sorted(pts)))
    allp = [p for _, _, pts in series for p in pts]
    if len(allp) < 2:
        return ''
    key = [(f'{g.replace("_", "-")} proposal', c, '', 'line') for g, c, _ in series]
    key.append(('open marker: evidence WEAK (fallback rule)', '#374151', '', 'dot'))
    ch = _Chart('Battery collector foil: critical coil ridge height by gauge and grade', key,
                height=300)
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    ch.axes(_Axis(min(xs) - 1, max(xs) + 1, ML, W - MR), _Axis(0.0, max(ys) * 1.15,
                                                                ch.h - 52, ch.mt),
            'final gauge [µm]', 'critical ridge height [µm] (at Rp0.2)')
    for g, c, pts in series:
        d = ' '.join(f'{"M" if i == 0 else "L"}{ch.x(x):.1f} {ch.y(y):.1f}'
                     for i, (x, y, _) in enumerate(pts))
        ch.inner.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2"/>')
        for x, y, weak in pts:
            ch.inner.append(f'<circle cx="{ch.x(x):.1f}" cy="{ch.y(y):.1f}" r="4" '
                            f'fill="{"#fff" if weak else c}" stroke="{c}" stroke-width="1.5"/>')
    return ch.render('grade-matrix')


def _matrix_section(m):
    if not m:
        return ''
    head = ['gauge', 'grade', 'material (literature proposal)', 'evidence', 'final pass',
            'bite', 'dead band [I]', 'ridge at Rp0.2 [µm]', 'trough onset [kPa]',
            'roller wrinkle [MPa]', '1 µm stripe', 'chatter u_crit with / without']
    rows = []
    for c in m['cells']:
        if c['status'] != 'EVALUATED':
            rows.append([f'{c["gauge_um"]:g} µm', _e(c['grade']), _e(c.get('reason', '')),
                         '', '', '', '', '', '', '', '', ''])
            continue
        st = c.get('stripe') or {}
        if c['credible']:
            bite = _e(f'{c["bite_model"]}, {c["separating_force_per_width_n_m"] * 1e-6:.3g} '
                      'kN/mm' + (' (extended domain, unvalidated)'
                                 if c.get('extended_domain_flags') else ''))
            stripe = _e(f'{_f(st.get("linear_feedback_i_units"))} I; in mill '
                        f'{_onset(st.get("in_mill_onset_height_m"), st.get("in_mill_onset_domain_limit_m"))}; '
                        f'after release {_onset(st.get("after_release_onset_height_m"), st.get("after_release_onset_domain_limit_m"))}')
            uc, uc0 = c.get('critical_exit_speed_m_s'), c.get('critical_exit_speed_without_bite_damping_m_s')
            chat = _e(f'{"stable" if uc is None else _f(uc)} / '
                      f'{"stable" if uc0 is None else _f(uc0)} m/s')
        else:
            bite = '<strong>' + _e(c.get('bite_excluded_reason', 'excluded')) + '</strong>'
            stripe = chat = 'excluded'
        ev = _e(c['evidence']) + (' <strong>WEAK: fallback rule</strong>'
                                  if c['fallback_rule_weak'] else '')
        rows.append([
            f'{c["gauge_um"]:g} µm', _e(c['grade'].replace('_', '-')),
            _e(f'{c["alloy"]}-{c["temper"]}, Rm {c["tensile_strength_pa"] * 1e-6:.0f} MPa, '
               f'Rp0.2 {c["proof_strength_pa"] * 1e-6:.0f} MPa '
               f'({"published" if c["proof_strength_published"] else "assumed"})'),
            ev,
            _e(f'{c["entry_thickness_m"] * 1e6:.4g} → {c["exit_thickness_m"] * 1e6:.4g} µm: '
               f'{c["pass_basis"]}'),
            bite, _e(_f(c.get('dead_band_half_width_i_units'))),
            _e(_f(c.get('critical_ridge_height_m'), 1e6)),
            _e(_f(c.get('trough_onset_lateral_stress_pa'), 1e-3)),
            _e(_f(c.get('roller_wrinkle_threshold_pa'), 1e-6)), stripe, chat])
    return ('<section><h2>Battery foil by gauge and grade</h2>'
            f'<p class="note">{_e(m["status"])}: {_e(m["note"])} {_e(m["rules"])}. '
            f'{_e(m["ridge_strength_basis"])}.</p>'
            f'<p>{_e(m["gauge_sentence"])}</p><p>{_e(m["grade_sentence"])}</p>'
            + _matrix_chart(m) + _table(head, rows, 'survey') + '</section>')


def _inputs_section(rows):
    out = []
    for r in rows:
        mine = ''.join(f'<li>{_e(x["item"])} = {_e(x["value"])} {_e(x["unit"])}: '
                       f'{_e(x["basis"])}</li>' for x in r.get('user_supplied_values') or [])
        used = ''.join(f'<li>{_e(x["item"])}: {_e(x["basis"])} [{_e(", ".join(x["sources"]))}; '
                       f'{_e(x["read_status"] or "")}]</li>' for x in r['catalogue_values_used'])
        ass = ''.join(f'<li>{_e(x["item"])}: {_e(x["basis"])}</li>' for x in r['assumed_values'])
        pc = ', '.join(f'{x["item"]} {x["verdict"]}' for x in r['product_check'])
        nd = ', '.join(d['name'] for d in r['named_defects']) or 'none in the catalogue'
        out.append(f'<details><summary>{_e(r["label"])}: {_e(r["product_name"])}</summary>'
                   f'<p>From the catalogue:</p><ul>{used or "<li>nothing</li>"}</ul>'
                   f'<p>Assumed:</p><ul>{ass}</ul>'
                   + (f'<p>User-supplied:</p><ul>{mine}</ul>' if mine else '')
                   + f'<p>Product check of the survey pass: {_e(pc)}.</p>'
                   f'<p>Named defects in the catalogue: {_e(nd)}.</p>'
                   + (f'<p class="note">{_e(r["bite_note"])}</p>' if r.get('bite_note') else '')
                   + '</details>')
    return ''.join(out)


def _mill_line(m):
    coil = m.get('coil')
    txt = (f'<li>{_e(m["name"])} (<code>{_e(m["scenario"])}</code>): work roll radius '
           f'{m["work_roll_radius_m"]:.3g} m, strip width {m["strip_width_m"]:.3g} m, spans '
           f'{m["entry_span_length_m"]:.3g} / {m["exit_span_length_m"]:.3g} m, deflector radius '
           + ('not given' if m['deflector_roll_radius_m'] is None
              else f'{m["deflector_roll_radius_m"]:.3g} m')
           + ', coil ' + ('not given' if coil is None else
                          f'{coil["inner_radius_m"]:.3g}-{coil["outer_radius_m"]:.3g} m at '
                          f'{coil["winding_tension_pa"] * 1e-6:.3g} MPa winding tension')
           + f', span-wave limit {m["span_wave_limit_hz"]:.4g} Hz')
    if m.get('source') == 'user mill file':
        txt += (f'. Machine keys taken from the file: {_e(", ".join(m["keys_taken"]))}; the '
                'product and pass, material, schedule, observations and case-specific inputs '
                '(blocked nozzles, events, ridges, crowns, shape inputs, bite heat) come from '
                f'the survey, not the file. Friction {m["friction_coefficient"]:g} from the '
                'file')
    return txt + '</li>'


def render_survey_report(result):
    r = result
    rows = r['rows']
    mills = ''.join(_mill_line(m) for m in r['mills'].values())
    user = any(m.get('source') == 'user mill file' for m in r['mills'].values())
    head = ['#', 'product', 'survey pass', 'bite', 'dead band [I]', 'ridge height [µm]',
            'trough onset [kPa]', 'roller wrinkle [MPa]', '1 µm stripe',
            'chatter u_crit with / without bite damping', 'marks']
    body = [
        '<h1>Product survey</h1>',
        (f'<div class="warn"><strong>{_e(r["status"])}</strong>: one synthetic final pass per '
         'catalogue product on one stated synthetic mill per gauge class, built from literature '
         'values; nothing here is validated against plant data.</div>' if not user else
         f'<div class="warn"><strong>{_e(r["status"])}</strong>: one final pass per catalogue '
         'product on the mill(s) from the user\'s file(s) listed below, built from literature '
         'values unless overridden; nothing here is validated against plant data.</div>'),
        f'<p class="lead">{_e(r["summary"])}</p>',
        f'<section><h2>Mills</h2><ul>{mills}</ul><p class="note">Exit gauge below '
        f'{r["rules"]["foil_mill_below_exit_m"] * 1e3:.3g} mm: foil mill; otherwise the sheet '
        f'mill. Friction {r["rules"]["friction_coefficient"]:g}'
        + (' (a user mill uses the friction of its file)' if user else '') + '; tensions '
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
        _matrix_section(r.get('battery_grade_matrix')),
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


# --------------------------------------------------------------------------- starter cases
def _fmt_value(v, unit):
    if isinstance(v, list):
        return ' / '.join(_fmt_value(x, unit) for x in v)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    return f'{v:.4g}{(" " + unit) if unit else ""}'


def starter_case(row, mill):
    """A ready-to-edit v2 case for one survey row: the survey pass on the chosen mill,
    ``material.product`` set, every observation null, notes on where each value came from."""
    c = copy.deepcopy(mill.case)
    p = c['pass']
    p.update(entry_thickness_m=row['entry_thickness_m'],
             exit_thickness_m=row['exit_thickness_m'],
             mean_flow_stress_pa=row['mean_flow_stress_pa'],
             friction_coefficient=row['friction_coefficient'],
             entry_tension_pa=row['entry_tension_pa'], exit_tension_pa=row['exit_tension_pa'],
             exit_speed_m_s=row['exit_speed_m_s'])
    if row.get('strip_width_m') is not None:
        p['width_m'] = row['strip_width_m']
    c['material'] = {'alloy': row['alloy_checked'], 'temper': row['final_temper'],
                     'yield_stress_pa': row['mean_flow_stress_pa'],
                     'youngs_modulus_pa': ss.ALUMINIUM_E_PA, 'luders_strain': None,
                     'magnesium_wt_pct': None, 'grain_size_m': None,
                     'final_pass_doubled': row['doubled'], 'product': row['product_id']}
    pr = (bp.proposed_material(row['product_id'], row['exit_thickness_m'])
          if bp.grade_bands(row['product_id']) else None)
    mat_notes = []
    if pr is not None and pr['status'] == bp.BG_STATUS:
        # SPEC13 2.4: alloy and temper from the literature proposal for the final gauge
        c['material']['alloy'], c['material']['temper'] = pr['alloy'], pr['temper']
        c['material']['alloy_temper_stated'] = False
        hard = pr['temper'].upper().startswith('H')
        if hard and pr['proof_strength']['value_pa'] is not None:
            c['material']['yield_stress_pa'] = pr['proof_strength']['value_pa']
        t = pr['tensile_strength_pa']
        mat_notes.append(
            f'MATERIAL: LITERATURE PROPOSAL TO CONFIRM OR CORRECT WITH THE PLANT, not a plant '
            f'statement (material.alloy_temper_stated false): {pr["alloy"]}-{pr["temper"]}, the '
            f'standard proposal of the {pr["band_label"]} band (band_products.proposed_material; '
            f'rule: {pr["rule"]}; evidence {pr["evidence"]}) [{", ".join(pr["sources"])}].')
        if hard:
            mat_notes.append(
                f'Flow stress {row["mean_flow_stress_pa"] * 1e-6:.4g} MPa = the proposal\'s '
                f'tensile strength ({t["basis"]}), an indicator of the rolling flow stress; '
                f'yield stress {c["material"]["yield_stress_pa"] * 1e-6:.4g} MPa = its proof '
                f'strength ({pr["proof_strength"]["basis"]}).')
        else:
            mat_notes.append(
                f'{pr["temper"]} is the finished temper reached by annealing after rolling; the '
                'pass is rolled hard, so the flow stress and yield stress keep the survey\'s '
                'as-rolled rule and the annealed strength '
                f'({t["value_pa"] * 1e-6:.4g} MPa) is not used.' if t['value_pa'] else
                f'{pr["temper"]} is the finished temper reached by annealing after rolling.')
    c['schedule'] = []
    c['hardening'] = None
    c['incoming_variation'] = None
    c['observation'] = {k: ([] if isinstance(v, list) else None)
                        for k, v in c['observation'].items()}
    d = mill.desc
    c['name'] = f'Starter case: {row["product_name"]} ({row["product_id"]})'
    c['synthetic'] = True
    c['provenance'] = (
        f'STARTER CASE written by physicroll.band_survey for {row["product_id"]} on '
        f'{d["name"]}: a starting point to replace with plant values, not plant data. The '
        'survey pass comes from the product catalogue (a literature survey) with the '
        'assumptions listed in notes; every observation is null.')
    notes = [f'Machine (stand, spans, kinematics, lubrication, coolant, tribology, gauge '
             f'control, drive, model options, width-model roll / header / coil / deflector, '
             f'pass width, roll radius and friction) from '
             + (f'the user mill file {d["file"]}' if mill.user
                else f'the demo scenario {d["scenario"]} (synthetic)')
             + '. Case-specific inputs (width-model blocked nozzles, nozzle levels, events, '
             'ridges, crowns, previous widths, lateral stress, shape inputs, bite heat, and '
             'coolant.blocked_nozzle_indices) are reset; enter your own when you have them.']
    notes += mat_notes
    for x in row['catalogue_values_used']:
        notes.append(f'From the catalogue: {x["item"]} = {_fmt_value(x["value"], x["unit"])}: '
                     f'{x["basis"]} [{", ".join(x["sources"])}; {x["read_status"]}]')
    for x in row['assumed_values']:
        notes.append(f'ASSUMED: {x["item"]} = {_fmt_value(x["value"], x["unit"])}: '
                     f'{x["basis"]}')
    for x in row.get('user_supplied_values') or []:
        notes.append(f'User-supplied: {x["item"]} = {_fmt_value(x["value"], x["unit"])} '
                     f'({x["basis"]})')
    if row['doubled']:
        notes.append('The final pass is doubled: the tool models one sheet in the bite '
                     '(flag DOUBLED_FINAL_PASS_NOT_MODELLED); the gauges are per sheet.')
    notes.append('Replace the pass, material and mill values with plant values, then record '
                 'the observations (docs/band-diagnosis.md, section 5) before reading a '
                 'diagnosis from this file.')
    c['notes'] = notes
    return bd.validate_case(json.loads(json.dumps(c)))


def write_cases(result, mills, out_dir):
    """Write one starter case per surveyed product; returns the written paths."""
    from .__main__ import _save_complete
    out_dir = Path(out_dir)
    paths = []
    for row in result['rows']:
        case = starter_case(row, mills[row['mill']])
        path = out_dir / f'{row["product_id"]}.case.json'
        _save_complete(path, json.dumps(case, indent=2, sort_keys=True, allow_nan=False)
                       + '\n')
        paths.append(path)
    return paths


def write(out_dir, products=None, foil_mill=None, sheet_mill=None, overrides=None,
          override_source='overrides file', cases_dir=None):
    from .__main__ import _save_complete
    result, mills = survey_with_mills(products, foil_mill, sheet_mill, overrides,
                                      override_source)
    html = render_survey_report(result)
    out_dir = Path(out_dir)
    jp, hp = out_dir / f'{SLUG}.result.json', out_dir / f'{SLUG}.report.html'
    _save_complete(jp, result_json(result))
    _save_complete(hp, html)
    cases = write_cases(result, mills, cases_dir) if cases_dir is not None else []
    return result, jp, hp, cases


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Product survey: one final pass per catalogue product (literature inputs, '
                    'unvalidated), on the demo mills or on your own mill')
    parser.add_argument('--out', type=Path, required=True, help='output directory')
    parser.add_argument('--mill', type=Path,
                        help='v2 case file whose machine keys are used for every product')
    parser.add_argument('--foil-mill', type=Path,
                        help='v2 case file for exit gauges below 0.2 mm (overrides --mill)')
    parser.add_argument('--sheet-mill', type=Path,
                        help='v2 case file for exit gauges of 0.2 mm and above '
                             '(overrides --mill)')
    parser.add_argument('--products', help='comma-separated catalogue product ids to survey')
    parser.add_argument('--overrides', type=Path,
                        help='JSON file {product_id: {key: value}} replacing survey-pass values '
                             f'({", ".join(OVERRIDE_KEYS)})')
    parser.add_argument('--write-cases', type=Path,
                        help='directory for one ready-to-edit v2 case file per product')
    args = parser.parse_args(argv)
    try:
        products = (None if args.products is None else
                    [x.strip() for x in args.products.split(',') if x.strip()])
        overrides = None
        if args.overrides is not None:
            overrides = load_overrides(args.overrides)
        result, jp, hp, cases = write(
            args.out, products, args.foil_mill or args.mill, args.sheet_mill or args.mill,
            overrides, f'overrides file {args.overrides.name}' if args.overrides else
            'overrides file', args.write_cases)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'{result["status"]}: {len(result["rows"])} products')
    print(result['summary'])
    print(f'result: {jp}')
    print(f'report: {hp}')
    for c in cases:
        print(f'case: {c}')


if __name__ == '__main__':
    main(sys.argv[1:])
