"""Thin-gauge aluminium product catalogue: gauges, alloys, tempers, rolling routes, requirements.

Opt-in, standard-library-only reference data for the band-screening engine and for the generated
document ``docs/thin-gauge-products.md``. It is a LITERATURE SURVEY, not a model and not a
validation: nothing here was measured on a plant, vendor pages are low-confidence, and a value
being inside a published span says nothing about whether a pass is good.

Sources and read status
-----------------------
Every value comes from one of three research reports (battery and electronics foil, packaging and
household foil, heat-exchanger / litho / other strip). Source ids are prefixed so they are unique
across the reports: ``BF-`` battery, ``PK-`` packaging, ``HX-`` heat exchanger and litho. Each
source carries the report's own read tag (``report_tag``) mapped onto one ``read_status``:
``full_text``, ``excerpt``, ``abstract_or_snippet``, ``vendor_or_trade_page``,
``memory_unverified``; ``computed`` marks numbers this module computes from published gauges.
Mapping choices (never upgrading a status):

- battery [FT] -> full_text, [EX] -> excerpt, [VP] -> vendor_or_trade_page, [MEM] ->
  memory_unverified; BF-S17 is tagged [FT] but is a trade page, so it is recorded as
  vendor_or_trade_page;
- packaging [F] -> full_text, except where the report qualifies it as excerpts, preview pages,
  partial or clauses only (-> excerpt); [S] -> abstract_or_snippet; [V] -> vendor_or_trade_page;
- heat exchanger [F] means "full text or long excerpt" in that report, so it is recorded as
  excerpt; [A] -> abstract_or_snippet; [V] and [V/A] -> vendor_or_trade_page;
- a source the report lists without any tag gets the weakest non-memory status that fits its
  kind (vendor page -> vendor_or_trade_page, otherwise abstract_or_snippet), with a note.

A fact's effective read status is its own override (only ever weaker than its sources, or
``computed``) or else the weakest status among its sources. Summary-table facts in the packaging
and heat-exchanger reports are cited per table row, so they carry the whole row's source list.

Computed quantities
-------------------
Per-step reduction ``r = 1 - h_exit/h_entry`` (per sheet for a doubled pass). A gauge given as a
range (lo, hi) gives a reduction span ``[1 - hi_exit/lo_entry, 1 - lo_exit/hi_entry]``. A block
of n passes reports its total reduction and the equal-split mean per pass
``1 - (h_exit/h_entry)**(1/n)``. Schedules published as reductions (Hydro litho) keep the
published reductions and compute the gauges ``h_(i+1) = h_i*(1 - r_i)``. Product per-pass spans
and final-pass spans are computed from the schedules, not stored as literals.

NOT covered: any physics, any plant measurement, alloy chemistry limits beyond what the reports
quote, standards text beyond the reports' reads (several standards were read from previews only).
"""
from dataclasses import dataclass, fields, is_dataclass
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

SCHEMA = 'physicroll.band_products.v1'
STATUS = 'LITERATURE_SURVEY_UNVALIDATED'
READ_STATUSES = ('full_text', 'excerpt', 'abstract_or_snippet', 'vendor_or_trade_page',
                 'memory_unverified', 'computed')
_RANK = {'full_text': 0, 'excerpt': 1, 'abstract_or_snippet': 2, 'vendor_or_trade_page': 3,
         'memory_unverified': 4}
FAMILIES = ('battery_electronics', 'packaging_household', 'heat_exchanger', 'litho',
            'other_strip')
ROLLED_MODES = ('single_sheet', 'doubled', 'either', 'not_published')
SURFACES = ('two_side_bright', 'one_side_bright')
BOUNDS = ('span', 'minimum', 'maximum', 'typical')
VERDICTS = ('WITHIN_PUBLISHED_RANGE', 'BELOW_PUBLISHED_RANGE', 'ABOVE_PUBLISHED_RANGE',
            'ABOVE_PUBLISHED_LIMIT',
            'NO_PUBLISHED_RANGE', 'INCONSISTENT_WITH_PUBLISHED_MODE')
# display unit -> (SI unit, factor to SI, label)
DISPLAY = {
    'um': ('m', 1e-6, 'µm'), 'mm': ('m', 1e-3, 'mm'), 'MPa': ('Pa', 1e6, 'MPa'),
    'kPa': ('Pa', 1e3, 'kPa'), '%': ('fraction', 0.01, '%'), 'm/min': ('m/s', 1 / 60, 'm/min'),
    'mN/m': ('N/m', 1e-3, 'mN/m'), 'per_m2': ('1/m^2', 1.0, 'per m²'),
    'g/m2': ('kg/m^2', 1e-3, 'g/m²'), '%IACS': ('fraction', 0.01, '% IACS'),
    # process temperatures (SPEC14); temperatures stay in °C (an offset scale, no conversion)
    'C': ('degC', 1.0, '°C'), 'K': ('K', 1.0, 'K'), 'cSt': ('m^2/s', 1e-6, 'cSt'),
    'kW/m2K': ('W/m^2K', 1e3, 'kW/m²K'), 'kW/m2': ('W/m^2', 1e3, 'kW/m²'),
    's': ('s', 1.0, 's'), 'min': ('s', 60.0, 'min'),
    'h': ('s', 3600.0, 'h'), 'days': ('s', 86400.0, 'days'),
    'kJ/mol': ('J/mol', 1e3, 'kJ/mol'), 'ratio': ('1', 1.0, ''),
    'um/K': ('m/K', 1e-6, 'µm/K'),
}
UNITS = tuple(sorted({v[0] for v in DISPLAY.values()}))
LIMITATIONS = (
    'Literature survey only: every value is quoted from three research reports, not measured.',
    'No plant validation: a value inside a published span is not evidence that a pass is good.',
    'Vendor and trade pages are low-confidence; several standards were read from previews only.',
    'Finished-product tensile strength is not the rolling flow stress; that comparison is an '
    'indicator only.',
    'Spans mix minima, typical values and ranges from different sources; read the basis.',
)
EVIDENCE_RATINGS = ('strong', 'medium', 'weak', 'vendor_level', 'not_rated')
GRADES = ('standard', 'high_strength')
BG_STATUS = 'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT'
_BAND_TOL = 1e-9
FLAGS = ('LITERATURE_SURVEY_NOT_VALIDATION', 'VENDOR_PAGES_LOW_CONFIDENCE',
         'REDUCTIONS_COMPUTED_FROM_PUBLISHED_GAUGES')


# --------------------------------------------------------------------------- helpers
def _num(name, value, *, positive=False, hi=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number (not bool)')
    value = float(value)
    if positive and value <= 0:
        raise ValueError(f'{name} must be > 0')
    if hi is not None and value > hi:
        raise ValueError(f'{name} must be <= {hi}')
    return value


def _text(name, value, *, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f'{name} must be a {"" if allow_empty else "nonempty "}string')
    return value


def _src_tuple(name, value):
    if not isinstance(value, tuple) or not all(isinstance(s, str) for s in value):
        raise ValueError(f'{name} must be a tuple of source id strings')
    for s in value:
        if s not in _SOURCES:
            raise ValueError(f'{name}: unknown source id {s!r}')
    if len(set(value)) != len(value):
        raise ValueError(f'{name}: duplicate source ids')
    return value


def _weakest(statuses):
    statuses = [s for s in statuses if s != 'computed']
    return max(statuses, key=_RANK.__getitem__) if statuses else None


def _check_status(owner, sources, read_status, *, require_sources=True):
    _src_tuple(f'{owner}.sources', sources)
    if read_status is not None and read_status not in READ_STATUSES:
        raise ValueError(f'{owner}: read_status must be one of {READ_STATUSES}')
    if not sources:
        if read_status == 'memory_unverified' or not require_sources:
            return
        raise ValueError(f'{owner}: sources required (only memory_unverified facts may be '
                         'unsourced)')
    if read_status not in (None, 'computed'):
        weakest = _weakest(_SOURCES[s].read_status for s in sources)
        if _RANK[read_status] < _RANK[weakest]:
            raise ValueError(f'{owner}: read_status {read_status!r} would upgrade its sources '
                             f'({weakest!r})')


def _effective(sources, read_status):
    if read_status is not None:
        return read_status
    return _weakest(_SOURCES[s].read_status for s in sources)


def _source_status(obj):
    """Weakest non-computed status behind a fact (its override, else its sources)."""
    if obj.read_status not in (None, 'computed'):
        return obj.read_status
    return _weakest(_SOURCES[s].read_status for s in obj.sources)


def _json(value):
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    if isinstance(value, (tuple, list)):
        return [_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    return value


def _checked(result):
    json.dumps(result, allow_nan=False)
    return result


def _split(src):
    return tuple(src.split()) if isinstance(src, str) else tuple(src)


# --------------------------------------------------------------------------- value carriers
@dataclass(frozen=True)
class Source:
    """One cited document (several URLs when the report reads it through mirrors)."""
    id: str
    title: str
    urls: tuple
    read_status: str
    report_tag: str
    note: str = ''

    def validate(self):
        _text('Source.id', self.id)
        if not self.id.startswith(('BF-', 'PK-', 'HX-', 'BG-', 'PT-', 'TM-')):
            raise ValueError(f'source id {self.id!r} must start with BF-, PK-, HX-, BG-, PT- '
                             'or TM-')
        _text('Source.title', self.title)
        if not isinstance(self.urls, tuple) or not self.urls:
            raise ValueError(f'source {self.id}: urls must be a nonempty tuple')
        for u in self.urls:
            if not isinstance(u, str) or not u.startswith(('http://', 'https://')):
                raise ValueError(f'source {self.id}: bad URL {u!r}')
        if self.read_status not in READ_STATUSES or self.read_status == 'computed':
            raise ValueError(f'source {self.id}: invalid read_status {self.read_status!r}')
        _text('Source.report_tag', self.report_tag)
        _text('Source.note', self.note, allow_empty=True)
        return self

    def to_dict(self):
        return {'id': self.id, 'title': self.title, 'urls': list(self.urls),
                'read_status': self.read_status, 'report_tag': self.report_tag,
                'note': self.note}


@dataclass(frozen=True)
class Range:
    """A published number or span in SI units; ``None`` marks an open side (minimum/maximum)."""
    low: float | None
    high: float | None
    unit: str
    sources: tuple
    note: str = ''
    bound: str = 'span'
    read_status: str | None = None
    display_unit: str | None = None

    def validate(self):
        if self.low is None and self.high is None:
            raise ValueError('Range needs low or high')
        for k in ('low', 'high'):
            v = getattr(self, k)
            if v is not None:
                _num(f'Range.{k}', v)
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError(f'Range low {self.low} > high {self.high} ({self.note})')
        if self.unit not in UNITS:
            raise ValueError(f'Range unit must be one of {UNITS}')
        if self.bound not in BOUNDS:
            raise ValueError(f'Range bound must be one of {BOUNDS}')
        if self.display_unit is not None and (self.display_unit not in DISPLAY
                                              or DISPLAY[self.display_unit][0] != self.unit):
            raise ValueError(f'Range display_unit {self.display_unit!r} does not fit {self.unit}')
        _text('Range.note', self.note, allow_empty=True)
        _check_status('Range', self.sources, self.read_status)
        return self

    def effective_read_status(self):
        return _effective(self.sources, self.read_status)

    def to_dict(self):
        return {'low': self.low, 'high': self.high, 'unit': self.unit, 'bound': self.bound,
                'display_unit': self.display_unit, 'note': self.note,
                'sources': list(self.sources), 'read_status': self.effective_read_status()}


@dataclass(frozen=True)
class Statement:
    """A sourced sentence, optionally with machine-readable ``values`` (each a sourced Range)."""
    text: str
    sources: tuple
    values: tuple = ()
    topic: str = ''
    read_status: str | None = None

    def validate(self, *, require_sources=True):
        _text('Statement.text', self.text)
        _text('Statement.topic', self.topic, allow_empty=True)
        _check_status(f'Statement {self.text[:40]!r}', self.sources, self.read_status,
                      require_sources=require_sources)
        if not isinstance(self.values, tuple):
            raise ValueError('Statement.values must be a tuple')
        for v in self.values:
            if not isinstance(v, Range):
                raise ValueError('Statement.values entries must be Range')
            v.validate()
        return self

    def effective_read_status(self):
        if not self.sources:
            return self.read_status
        return _effective(self.sources, self.read_status)

    def to_dict(self):
        return {'topic': self.topic, 'text': self.text, 'sources': list(self.sources),
                'read_status': self.effective_read_status(), 'values': _json(self.values)}


@dataclass(frozen=True)
class Item:
    """A named entry (alloy, temper or standard) with a role/scope note and sources."""
    name: str
    text: str
    sources: tuple
    read_status: str | None = None

    def validate(self):
        _text('Item.name', self.name)
        _text('Item.text', self.text)
        _check_status(f'Item {self.name!r}', self.sources, self.read_status)
        return self

    def to_dict(self):
        return {'name': self.name, 'text': self.text, 'sources': list(self.sources),
                'read_status': _effective(self.sources, self.read_status)}


@dataclass(frozen=True)
class Defect:
    """A named band/streak defect: appearance and published cause, as the report gives them."""
    name: str
    appearance: str
    published_cause: str
    sources: tuple
    values: tuple = ()
    read_status: str | None = None

    def validate(self):
        _text('Defect.name', self.name)
        _text('Defect.appearance', self.appearance)
        _text('Defect.published_cause', self.published_cause)
        _check_status(f'Defect {self.name!r}', self.sources, self.read_status)
        for v in self.values:
            v.validate()
        return self

    def to_dict(self):
        return {'name': self.name, 'appearance': self.appearance,
                'published_cause': self.published_cause, 'sources': list(self.sources),
                'read_status': _effective(self.sources, self.read_status),
                'values': _json(self.values)}


@dataclass(frozen=True)
class Strength:
    """Published tensile data for alloy(s)/temper; each Range carries its own sources."""
    alloys: tuple
    temper: str
    condition: str
    sources: tuple
    rm_pa: Range | None = None
    rp_pa: Range | None = None
    elongation: Range | None = None
    grade: str = ''
    note: str = ''

    def validate(self):
        if not isinstance(self.alloys, tuple) or not self.alloys:
            raise ValueError('Strength.alloys must be a nonempty tuple')
        for a in self.alloys:
            _text('Strength alloy', a)
        _text('Strength.temper', self.temper)
        _text('Strength.condition', self.condition)
        _check_status('Strength', self.sources, None)
        if self.rm_pa is None and self.rp_pa is None and self.elongation is None:
            raise ValueError('Strength needs at least one of rm_pa, rp_pa, elongation')
        for k, unit in (('rm_pa', 'Pa'), ('rp_pa', 'Pa'), ('elongation', 'fraction')):
            r = getattr(self, k)
            if r is not None:
                r.validate()
                if r.unit != unit:
                    raise ValueError(f'Strength.{k} must be in {unit}')
        if self.grade not in ('', 'standard', 'high_strength'):
            raise ValueError("Strength.grade must be '', 'standard' or 'high_strength'")
        return self

    def to_dict(self):
        return {'alloys': list(self.alloys), 'temper': self.temper, 'condition': self.condition,
                'grade': self.grade, 'rm_pa': _json(self.rm_pa), 'rp_pa': _json(self.rp_pa),
                'elongation': _json(self.elongation), 'note': self.note,
                'sources': list(self.sources),
                'read_status': _effective(self.sources, None)}


def _gauge_pair(name, g):
    if isinstance(g, tuple):
        if len(g) != 2:
            raise ValueError(f'{name}: a gauge range must be (low, high)')
        lo = _num(name, g[0], positive=True, hi=0.02)
        hi = _num(name, g[1], positive=True, hi=0.02)
        if lo > hi:
            raise ValueError(f'{name}: gauge range low > high')
        return lo, hi
    v = _num(name, g, positive=True, hi=0.02)
    return v, v


@dataclass(frozen=True)
class PassSchedule:
    """A published gauge sequence. ``gauges_m``: entry then the exit of each step; an entry may
    be a (low, high) tuple. ``doubled_from_index``: first doubled step (gauges are per sheet).
    ``passes_per_step``: None = every step is one pass; else an int per step, or None where the
    report does not say. ``published_reductions``: the schedule is published as reductions from
    ``gauges_m[0]``; gauges are then computed."""
    label: str
    gauges_m: tuple
    sources: tuple
    alloy: str = ''
    doubled_from_index: int | None = None
    passes_per_step: tuple | None = None
    published_reductions: tuple | None = None
    speeds_m_s: tuple | None = None
    note: str = ''
    display_unit: str = 'um'
    read_status: str | None = None

    def steps(self):
        if self.published_reductions is not None:
            return len(self.published_reductions)
        return len(self.gauges_m) - 1

    def passes(self):
        return self.passes_per_step if self.passes_per_step is not None else (1,) * self.steps()

    def gauges(self):
        """Gauges as (low, high) pairs in m, entry first (computed in published-reduction mode)."""
        if self.published_reductions is None:
            return tuple(_gauge_pair('gauge', g) for g in self.gauges_m)
        lo, hi = _gauge_pair('gauge', self.gauges_m[0])
        out = [(lo, hi)]
        for r in self.published_reductions:
            lo, hi = lo * (1 - r), hi * (1 - r)
            out.append((lo, hi))
        return tuple(out)

    def reductions(self):
        """Per-step reduction (low, high) as fractions; per sheet for doubled steps."""
        if self.published_reductions is not None:
            return tuple((float(r), float(r)) for r in self.published_reductions)
        g = self.gauges()
        return tuple((1 - g[i + 1][1] / g[i][0], 1 - g[i + 1][0] / g[i][1])
                     for i in range(self.steps()))

    def per_pass_reductions(self):
        """(step, low, high, kind): single passes, and equal-split means of known-size blocks."""
        out = []
        for i, ((lo, hi), n) in enumerate(zip(self.reductions(), self.passes())):
            if n == 1:
                out.append((i, lo, hi, 'single_pass'))
            elif n is not None:
                out.append((i, 1 - (1 - lo) ** (1 / n), 1 - (1 - hi) ** (1 / n),
                            'equal_split_mean'))
        return tuple(out)

    def is_doubled(self, step):
        return self.doubled_from_index is not None and step >= self.doubled_from_index

    def validate(self):
        _text('PassSchedule.label', self.label)
        _text('PassSchedule.alloy', self.alloy, allow_empty=True)
        _text('PassSchedule.note', self.note, allow_empty=True)
        _check_status(f'PassSchedule {self.label!r}', self.sources, self.read_status)
        if not isinstance(self.gauges_m, tuple) or not self.gauges_m:
            raise ValueError(f'{self.label}: gauges_m must be a nonempty tuple')
        if self.published_reductions is not None:
            if len(self.gauges_m) != 1 or not self.published_reductions:
                raise ValueError(f'{self.label}: published-reduction mode takes one entry gauge')
            for r in self.published_reductions:
                _num('published reduction', r, positive=True, hi=0.99)
        elif len(self.gauges_m) < 2:
            raise ValueError(f'{self.label}: needs at least entry and one exit gauge')
        g = self.gauges()
        for i in range(self.steps()):
            if not g[i + 1][1] < g[i][0]:
                raise ValueError(f'{self.label}: step {i} does not reduce the gauge')
        n = self.steps()
        if self.doubled_from_index is not None:
            if isinstance(self.doubled_from_index, bool) or not isinstance(
                    self.doubled_from_index, int) or not 0 <= self.doubled_from_index < n:
                raise ValueError(f'{self.label}: doubled_from_index out of range')
        if self.passes_per_step is not None:
            if len(self.passes_per_step) != n:
                raise ValueError(f'{self.label}: passes_per_step length must equal steps')
            for p in self.passes_per_step:
                if p is not None and (isinstance(p, bool) or not isinstance(p, int) or p < 1):
                    raise ValueError(f'{self.label}: passes_per_step entries int >= 1 or None')
        if self.speeds_m_s is not None:
            if len(self.speeds_m_s) != n:
                raise ValueError(f'{self.label}: speeds_m_s length must equal steps')
            for s in self.speeds_m_s:
                _num('speed', s, positive=True, hi=200.0)
        if self.display_unit not in ('um', 'mm', 'auto'):
            raise ValueError("PassSchedule.display_unit must be 'um', 'mm' or 'auto'")
        return self

    def to_dict(self):
        g = self.gauges()
        return {
            'label': self.label, 'alloy': self.alloy, 'note': self.note,
            'gauges_m': [list(p) for p in g],
            'gauges_computed': self.published_reductions is not None,
            'doubled_from_index': self.doubled_from_index, 'passes_per_step': list(self.passes()),
            'reductions': [list(r) for r in self.reductions()],
            'reductions_read_status': ('published' if self.published_reductions is not None
                                       else 'computed'),
            'per_pass_reductions': [list(r) for r in self.per_pass_reductions()],
            'speeds_m_s': list(self.speeds_m_s) if self.speeds_m_s is not None else None,
            'sources': list(self.sources),
            'read_status': _effective(self.sources, self.read_status),
        }


@dataclass(frozen=True)
class FinalPass:
    """Published final-pass facts; entry gauge and reduction may be computed from schedules."""
    entry_gauge_m: Range | None = None
    reduction: Range | None = None
    speed_m_s: Range | None = None
    doubled_speed_m_s: Range | None = None
    notes: tuple = ()

    def validate(self):
        for k, unit in (('entry_gauge_m', 'm'), ('reduction', 'fraction'),
                        ('speed_m_s', 'm/s'), ('doubled_speed_m_s', 'm/s')):
            r = getattr(self, k)
            if r is not None:
                r.validate()
                if r.unit != unit:
                    raise ValueError(f'FinalPass.{k} must be in {unit}')
        for s in self.notes:
            s.validate()
        return self

    def to_dict(self):
        return {f.name: _json(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class Product:
    """One thin-gauge product with every value sourced (see module docstring)."""
    id: str
    name: str
    family: str
    final_gauge_m: Range
    alloys: tuple
    tempers: tuple
    rolled_mode: str
    key_requirement: Statement
    mode_note: Statement | None = None
    common_gauges: tuple = ()
    strength: tuple = ()
    single_sheet_gauge_m: Range | None = None
    per_pass_reduction: Range | None = None
    schedules: tuple = ()
    final_pass: FinalPass | None = None
    pass_speed_m_s: Range | None = None
    foil_stock: tuple = ()
    annealing: tuple = ()
    route: tuple = ()
    work_roll_roughness: tuple = ()
    rolls_and_oil: tuple = ()
    surface: tuple = ()
    thickness_tolerance: tuple = ()
    flatness_requirement: tuple = ()
    wettability: tuple = ()
    pinholes: tuple = ()
    other_requirements: tuple = ()
    named_defects: tuple = ()
    standards: tuple = ()
    caveats: tuple = ()
    disagreements: tuple = ()
    not_found: tuple = ()
    evidence: tuple = ()

    _STATEMENT_FIELDS = ('common_gauges', 'foil_stock', 'annealing', 'route',
                         'work_roll_roughness', 'rolls_and_oil', 'surface',
                         'thickness_tolerance', 'flatness_requirement', 'wettability',
                         'pinholes', 'other_requirements', 'caveats', 'disagreements',
                         'evidence')

    def validate(self):
        _text('Product.id', self.id)
        _text('Product.name', self.name)
        if self.family not in FAMILIES:
            raise ValueError(f'{self.id}: family must be one of {FAMILIES}')
        if self.rolled_mode not in ROLLED_MODES:
            raise ValueError(f'{self.id}: rolled_mode must be one of {ROLLED_MODES}')
        for k, unit in (('final_gauge_m', 'm'), ('single_sheet_gauge_m', 'm'),
                        ('per_pass_reduction', 'fraction'), ('pass_speed_m_s', 'm/s')):
            r = getattr(self, k)
            if r is None:
                if k == 'final_gauge_m':
                    raise ValueError(f'{self.id}: final_gauge_m required')
                continue
            r.validate()
            if r.unit != unit:
                raise ValueError(f'{self.id}: {k} must be in {unit}')
        if not self.alloys or not self.tempers:
            raise ValueError(f'{self.id}: alloys and tempers required')
        for i in self.alloys + self.tempers + self.standards:
            if not isinstance(i, Item):
                raise ValueError(f'{self.id}: alloys/tempers/standards must be Item')
            i.validate()
        self.key_requirement.validate()
        if self.mode_note is not None:
            self.mode_note.validate()
        for k in self._STATEMENT_FIELDS:
            for s in getattr(self, k):
                if not isinstance(s, Statement):
                    raise ValueError(f'{self.id}.{k} entries must be Statement')
                s.validate()
        for s in self.not_found:
            s.validate(require_sources=False)
        for s in self.strength:
            s.validate()
        labels = set()
        for s in self.schedules:
            s.validate()
            if s.label in labels:
                raise ValueError(f'{self.id}: duplicate schedule label {s.label!r}')
            labels.add(s.label)
        if self.final_pass is not None:
            self.final_pass.validate()
        for d in self.named_defects:
            d.validate()
        return self

    def to_dict(self):
        out = {}
        for f in fields(self):
            out[f.name] = _json(getattr(self, f.name))
        return out


@dataclass(frozen=True)
class GradeOption:
    """One alloy option of a gauge band (battery grade table). ``standard_min_rm_pa`` is the
    GB/T 33143-2022 Table 9 minimum for this alloy and band (None: the standard sets none);
    ``typical`` holds producer values that apply to this alloy in this band; ``usual`` is set
    when the research calls it the usual choice (the text says for which cells or condition);
    ``usual_surface`` restricts that to one surface; ``gauge_m`` restricts the option itself to
    a published gauge span (e.g. pouch alloys)."""
    alloy: str
    grade: str
    temper_labels: tuple
    standard_min_rm_pa: Range | None = None
    typical: tuple = ()
    usual: Statement | None = None
    usual_surface: str | None = None
    gauge_m: Range | None = None
    grade_names: tuple = ()
    note: str = ''
    basis_sources: tuple = ()

    def validate(self):
        _text('GradeOption.alloy', self.alloy)
        _src_tuple('GradeOption.basis_sources', self.basis_sources)
        if self.grade not in GRADES:
            raise ValueError(f'GradeOption {self.alloy}: grade must be one of {GRADES}')
        if not self.temper_labels or not all(isinstance(t, str) and t for t in
                                             self.temper_labels):
            raise ValueError(f'GradeOption {self.alloy}: temper_labels required')
        if self.standard_min_rm_pa is not None:
            self.standard_min_rm_pa.validate()
            if self.standard_min_rm_pa.unit != 'Pa' or self.standard_min_rm_pa.bound != 'minimum':
                raise ValueError(f'GradeOption {self.alloy}: standard minimum must be a Pa minimum')
        for s in self.typical:
            if not isinstance(s, Strength):
                raise ValueError(f'GradeOption {self.alloy}: typical entries must be Strength')
            s.validate()
        if self.usual is not None:
            self.usual.validate()
        if self.usual_surface not in (None,) + SURFACES:
            raise ValueError(f'GradeOption {self.alloy}: bad usual_surface')
        if self.gauge_m is not None:
            self.gauge_m.validate()
        for g in self.grade_names:
            _text('GradeOption.grade_names', g)
        _text('GradeOption.note', self.note, allow_empty=True)
        if self.standard_min_rm_pa is None and not self.typical and self.usual is None \
                and not self.basis_sources and self.gauge_m is None:
            raise ValueError(f'GradeOption {self.alloy}: needs a sourced value, gauge span, '
                             'usual-choice statement or basis source')
        return self

    def option_sources(self):
        objs = ([self.standard_min_rm_pa] if self.standard_min_rm_pa else []) + list(
            self.typical) + ([self.usual] if self.usual else []) + (
            [self.gauge_m] if self.gauge_m else [])
        out = list(_union_sources(objs))
        out += [s for s in self.basis_sources if s not in out]
        return tuple(out)

    def to_dict(self):
        return {'alloy': self.alloy, 'grade': self.grade,
                'temper_labels': list(self.temper_labels),
                'standard_min_rm_pa': _json(self.standard_min_rm_pa),
                'typical': _json(self.typical), 'usual': _json(self.usual),
                'usual_surface': self.usual_surface, 'gauge_m': _json(self.gauge_m),
                'grade_names': list(self.grade_names), 'note': self.note,
                'basis_sources': list(self.basis_sources),
                'sources': list(self.option_sources())}


@dataclass(frozen=True)
class GaugeBand:
    """One gauge band of a product's grade table: ``low_m`` < gauge <= ``high_m`` (``low_m``
    inclusive when ``low_inclusive``). Ratings are the report's evidence column kept as data:
    ``minima_evidence`` for the standard minima, ``choice_evidence`` for the usual choice."""
    id: str
    label: str
    low_m: float
    high_m: float
    low_inclusive: bool
    gauges_named: str
    options: tuple
    usual_choice: Statement
    typical_producer: Statement | None
    typical_cells: Statement | None
    evidence: Statement
    minima_evidence: str
    choice_evidence: str
    elongation: Statement | None = None
    surface: tuple = ()
    pinholes: Statement | None = None
    notes: tuple = ()

    def validate(self):
        _text('GaugeBand.id', self.id)
        _text('GaugeBand.label', self.label)
        _num('GaugeBand.low_m', self.low_m, hi=0.02)
        _num('GaugeBand.high_m', self.high_m, positive=True, hi=0.02)
        if not self.low_m < self.high_m:
            raise ValueError(f'GaugeBand {self.id}: low_m must be < high_m')
        for r in (self.minima_evidence, self.choice_evidence):
            if r not in EVIDENCE_RATINGS:
                raise ValueError(f'GaugeBand {self.id}: rating must be one of {EVIDENCE_RATINGS}')
        if not self.options:
            raise ValueError(f'GaugeBand {self.id}: options required')
        names = [o.alloy for o in self.options]
        if len(set(names)) != len(names):
            raise ValueError(f'GaugeBand {self.id}: duplicate alloy options')
        for o in self.options:
            if not isinstance(o, GradeOption):
                raise ValueError(f'GaugeBand {self.id}: options must be GradeOption')
            o.validate()
        for s in (self.usual_choice, self.typical_producer, self.typical_cells, self.evidence,
                  self.elongation, self.pinholes) + self.surface + self.notes:
            if s is not None:
                s.validate()
        return self

    def contains(self, h):
        lo_ok = (h >= self.low_m * (1 - _BAND_TOL) if self.low_inclusive
                 else h > self.low_m * (1 + _BAND_TOL))
        return lo_ok and h <= self.high_m * (1 + _BAND_TOL)

    def to_dict(self):
        return {'id': self.id, 'label': self.label, 'low_m': self.low_m, 'high_m': self.high_m,
                'low_inclusive': self.low_inclusive, 'gauges_named': self.gauges_named,
                'minima_evidence': self.minima_evidence,
                'choice_evidence': self.choice_evidence,
                'options': [o.to_dict() for o in self.options],
                'usual_choice': _json(self.usual_choice),
                'typical_producer': _json(self.typical_producer),
                'typical_cells': _json(self.typical_cells), 'evidence': _json(self.evidence),
                'elongation': _json(self.elongation), 'surface': _json(self.surface),
                'pinholes': _json(self.pinholes), 'notes': _json(self.notes)}


@dataclass(frozen=True)
class HeatingStep:
    """One condition of a strength-after-heating series: temperature in °C (a number, a
    (low, high) span, or None for as rolled) and duration in s (None when not given)."""
    label: str
    temperature_c: object
    duration_s: float | None
    rm_pa: Range

    def validate(self):
        _text('HeatingStep.label', self.label)
        t = self.temperature_c
        if isinstance(t, tuple):
            if len(t) != 2 or not _num('temperature', t[0]) <= _num('temperature', t[1]):
                raise ValueError('HeatingStep.temperature_c span must be (low, high)')
        elif t is not None:
            _num('HeatingStep.temperature_c', t, hi=700)
        if self.duration_s is not None:
            _num('HeatingStep.duration_s', self.duration_s, positive=True)
        self.rm_pa.validate()
        if self.rm_pa.unit != 'Pa':
            raise ValueError('HeatingStep.rm_pa must be in Pa')
        return self

    def to_dict(self):
        t = self.temperature_c
        return {'label': self.label, 'temperature_c': list(t) if isinstance(t, tuple) else t,
                'duration_s': self.duration_s, 'rm_pa': self.rm_pa.to_dict()}


@dataclass(frozen=True)
class StrengthAfterHeating:
    """Tensile strength of hard foil as rolled and after heating (a temperature-dependent fact;
    kept as data for a later process-temperature package, not used by any calculation)."""
    material: str
    steps: tuple
    note: str = ''

    def validate(self):
        _text('StrengthAfterHeating.material', self.material)
        if len(self.steps) < 2:
            raise ValueError('StrengthAfterHeating needs as-rolled and at least one heated step')
        for s in self.steps:
            s.validate()
        return self

    def loss_fraction(self):
        """Computed loss from as rolled to the last step, (low, high) over the spans."""
        a, b = self.steps[0].rm_pa, self.steps[-1].rm_pa
        if a.low is None or b.low is None:
            return None
        ahi = a.high if a.high is not None else a.low
        bhi = b.high if b.high is not None else b.low
        vals = (1 - b.low / a.low, 1 - bhi / ahi)
        return (min(vals), max(vals))

    def to_dict(self):
        loss = self.loss_fraction()
        return {'material': self.material, 'steps': _json(self.steps), 'note': self.note,
                'loss_fraction_computed': list(loss) if loss else None}


@dataclass(frozen=True)
class TemperRow:
    """How a temper is defined and how battery foil reaches it."""
    temper: str
    definition: Statement
    route: Statement

    def validate(self):
        _text('TemperRow.temper', self.temper)
        self.definition.validate()
        self.route.validate()
        return self

    def to_dict(self):
        return {'temper': self.temper, 'definition': self.definition.to_dict(),
                'route': self.route.to_dict()}


# --------------------------------------------------------------------------- sources
def _S(sid, title, urls, status, tag, note=''):
    return Source(sid, title, _split(urls), status, tag, note)


_FT, _EX, _AB, _VP = 'full_text', 'excerpt', 'abstract_or_snippet', 'vendor_or_trade_page'
_NOTAG = 'the report lists this source without a read tag'
_SOURCE_LIST = (
    # ---- battery report
    _S('BF-S1', 'GB/T 33143-2022 text mirror', 'https://www.duodown.com/biaozhun/2046559.html '
       'https://www.bzxz.net/bzxz/195767.html', _FT, 'FT'),
    _S('BF-S2', 'GB/T 33143 draft English translation with tables',
       'http://www.cnsmq.com/uploadfile/2025/0227/20250227042900196.pdf', _EX, 'EX',
       'tables partly garbled in the report\'s read'),
    _S('BF-S3', 'UACJ Foil battery foil', 'https://ufo.uacj-group.com/en/techno/rd/battery.html',
       _VP, 'VP'),
    _S('BF-S4', 'UACJ/Nagase collector foil datasheet',
       'https://nagase.eu/wp-content/uploads/2025/09/Battery-Show-2025_UACJ_Aluminium-Collector_'
       '2025_09_QR-PDF-Downloads-Mobi.pdf', _VP, 'VP'),
    _S('BF-S5', 'UACJ Technical Reports 2014 (Motoi et al.)',
       'https://www.uacj.co.jp/development/rd/review/vol1no1/pdf/vol1no1_18.pdf', _EX, 'EX'),
    _S('BF-S6', 'UACJ Technical Reports 2022 (Saito, Tanaka)',
       'https://www.uacj.co.jp/development/rd/review/vol9no1/pdf/vol9no1_11.pdf', _EX, 'EX'),
    _S('BF-S8', 'Speira US11495801 (high-strength)',
       'https://exa.ai/library/legal/patent/8474559yxs4', _EX, 'EX'),
    _S('BF-S9', 'Speira EP3714077B1', 'https://patents.google.com/patent/EP3714077B1/en', _FT,
       'FT'),
    _S('BF-S10', 'Speira EP3931895A1 (corona)',
       'https://patents.google.com/patent/EP3931895A1/en', _FT, 'FT'),
    _S('BF-S11', 'CN112934979A', 'https://patents.google.com/patent/CN112934979A/en', _EX, 'EX'),
    _S('BF-S12', 'CN116237363A (Jiangsu Daya)',
       'https://patents.google.com/patent/CN116237363A/zh', _EX, 'EX'),
    _S('BF-S13', 'CN111438187A', 'https://patents.google.com/patent/CN111438187A/zh', _EX, 'EX'),
    _S('BF-S14', 'CN113385536A (Shandong Deli)', 'https://eureka.patsnap.com/patent-CN113385536A',
       _EX, 'EX'),
    _S('BF-S15', 'CN102744255B (North China Aluminium)',
       'https://patents.google.com/patent/CN102744255B/en', _FT, 'FT'),
    _S('BF-S16', 'Three-pass battery foil patent',
       'https://www.xjishu.com/zhuanli/23/202311439469.html', _EX, 'EX'),
    _S('BF-S17', 'Battery foil production procedure (trade page)',
       'https://alfoilworld.com/knowledge/knowledge-a38e503a/?lang=zh', _VP, 'FT',
       'tagged [FT] (page read) by the report, but it is a trade page; recorded as '
       'vendor_or_trade_page'),
    _S('BF-S18', 'JP5927614B2 / CN103003457A (Kobe Steel, Sun Aluminium)',
       'https://patents.google.com/patent/JP5927614B2/en '
       'https://patents.google.com/patent/CN103003457A/en', _EX, 'EX'),
    _S('BF-S20', 'JP6694265B2', 'https://patents.google.com/patent/JP6694265B2/en', _EX, 'EX'),
    _S('BF-S21', 'SMM report of North China Aluminium talk on ≤10 µm foil',
       'https://news.smm.cn/news/103277336', _EX, 'EX'),
    _S('BF-S22', 'Achenbach foil mills',
       'https://www.achenbach.de/en/machines-equipment/optimill-rolling-mills/'
       'optimill-foil-rolling-mills/', _VP, 'none',
       _NOTAG + ' and cites it nowhere in the body; manufacturer page'),
    _S('BF-S24', 'Achenbach automation article',
       'https://www.bachmann.info/media/881/download/Applikationsbeitrag_Achenbach_EN.pdf?v=1',
       _VP, 'VP'),
    _S('BF-S25', 'Mino battery foil finishing mill',
       'https://mino.it/italy-powers-up-in-battery-foil-sector/', _VP, 'VP'),
    _S('BF-S26', 'Primetals foil mills',
       'https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/'
       'aluminum-foil-rolling-mill/', _VP, 'VP'),
    _S('BF-S27', 'Work-roll diameters (catalogue and mill listing)',
       'http://www.aluminum-casting-mill.com/product/Aluminum-foil-rolling-mill.html '
       'https://www.usedequip.com/listings/3684', _VP, 'VP'),
    _S('BF-S28', 'Toyo TY-X2', 'https://en.toyal.co.jp/products/4', _VP, 'VP'),
    _S('BF-S29', 'GB/T 22648-2023', 'https://www.duodown.com/biaozhun/2155908.html '
       'https://www.duodown.com/biaozhun/2164044.html', _FT, 'FT'),
    _S('BF-S30', 'GB/T 22648 secondary summary',
       'https://m.antpedia.com/standard/1936982121-10.html', _EX, 'EX',
       'self-disclaimed secondary summary'),
    _S('BF-S31', 'EN 546-2:2006 preview',
       'https://cdn.standards.iteh.ai/samples/24064/6f0a23931a8b4680aae303172470dec2/'
       'SIST-EN-546-2-2007.pdf', _EX, 'EX', 'same document as PK-S9'),
    _S('BF-S32', 'CN106011708 (8021 pouch foil anneal)',
       'https://www.xjishu.com/zhuanli/24/CN106011708.html', _EX, 'EX'),
    _S('BF-S33', '8021 pouch foil stock patent',
       'https://www.xjishu.com/zhuanli/24/202511388492.html', _EX, 'EX'),
    _S('BF-S34', 'CN103695723A (8021 thin foil)',
       'https://patents.google.com/patent/CN103695723A/en', _EX, 'EX'),
    _S('BF-S36', 'GB/T 3615-2016', 'https://www.guifanku.com/911932.html '
       'https://kpt-bj.com/gb-t-3615-2016-aluminium-foils-for-electrolytic-capacitor-8373548.html',
       _EX, 'EX'),
    _S('BF-S37', 'Yamanoi, J. JILM 64 (2014) 419',
       'https://www.jstage.jst.go.jp/article/jilm/64/9/64_419/_pdf', _EX, 'EX'),
    _S('BF-S38', 'UACJ Technical Reports 2024, HV capacitor foil',
       'https://www.uacj.co.jp/development/rd/review/vol11no1/pdf/vol11no1_10.pdf', _EX, 'EX'),
    _S('BF-S41', 'Sumitomo Electric tab-lead',
       'https://sumitomoelectric.com/sites/default/files/2020-12/download_documents/E88-13.pdf',
       _EX, 'EX'),
    _S('BF-S42', 'HDM cell case sheet', 'https://hdmetalm.com/lithium-ion-battery-casing-material/',
       _VP, 'VP'),
    _S('BF-S43', 'CSIRO cell cans report',
       'https://www.csiro.au/-/media/Manufacturing/Files/26-00168_TEC_REPORT_'
       'LithiumIonBatteryCells_1_CellCans_WEB_260911.pdf', _EX, 'EX'),
    _S('BF-S44', 'GB/T 33824-2025', 'https://chinastandards.org/standards/gb-t-33824-2025', _EX,
       'EX'),
    _S('BF-S45', 'Sam-A', 'https://sama-al.com/eng/business/foil/car', _VP, 'VP'),
    _S('BF-S46', 'Dongwon Systems',
       'https://www.tradewheel.com/p/aluminum-foil-for-battery-cathode-2461364/', _VP, 'VP'),
    _S('BF-S48', 'MC Aluminum', 'https://www.alummc-foil.com/product/battery-aluminum-foil.html',
       _VP, 'VP'),
    _S('BF-S49', 'Carbon-coated foil vendors',
       'https://www.china-aluminumfoils.com/product/ultra-thin-12-15m-carbon-coated-aluminum-foil-'
       'lfp-lithium-battery-cathode-current-collector-strong-adhesion-high-conductivity/ '
       'https://www.lyhsmetal.com/lithium-battery-materials/carbon-coated-aluminum-foil-'
       'conductive.html', _VP, 'VP'),
    _S('BF-S51', 'Wang & Wang, Chin. J. Nonferrous Met. 29 (2019) 1250',
       'http://www.ysxbcn.com/down/2019/06_cn/14-p1250-39255.pdf', _EX, 'EX'),
    _S('BF-S52', 'Zuo & Lv, Metals 14 (2024) 156', 'https://www.mdpi.com/2075-4701/14/2/156', _AB,
       'none', _NOTAG + '; cited only as describing a hot mill despite its title'),
    # ---- packaging report
    _S('PK-S1', 'Kerth, Amann, Raber, Weber, "Aluminium Foil Production", Int. Metall. Rev. 20 '
       '(1975) 185-207', 'https://www.scribd.com/document/949516974/kerth1975', _FT, 'F',
       'about 80 % read'),
    _S('PK-S2', 'US 2004/0088840 A1, "Aluminium foil rolling method"',
       'https://patents.justia.com/patent/20040088840 '
       'https://patents.google.com/patent/US20040088840A1/en', _FT, 'F'),
    _S('PK-S3', 'Can, Arikan, Çınar, twin-roll casting AA8079 6.35 µm foil rolling, Mater. '
       'Tehnol. 50 (2016) 861', 'http://mit.imt.si/izvodi/mit166/can.pdf', _EX, 'F, excerpts'),
    _S('PK-S4', 'Moschini, Sinagra, Gioachin, "The Engineering Design of Rolling Mill", A&L 2019',
       'https://www.publiteconline.it/ael/the-engineering-design-of-rolling-mill/', _EX,
       'F, excerpt'),
    _S('PK-S5', 'Achenbach, "Aluminium Rolling Mill Technology" extract (EAFA library)',
       'https://www.alufoil.org/files/images_alufoil/about_alufoil/reference_library/'
       'achenbach_extract.pdf', _FT, 'F', 'same document as HX-S36'),
    _S('PK-S6', 'EAFA, Alufoil production; Assan EPD',
       'https://www.alufoil.org/Alufoil-Production https://www.environdec.com/library/epd17784',
       _FT, 'F / S', 'EAFA page read in full; the Assan EPD only as a snippet'),
    _S('PK-S7', 'EAFA, "Surface Characteristics of Aluminium Foil" (June 2020)',
       'https://www.alufoil.org/surface-characteristics?file=files%2Fimages_alufoil%2Fabout_alufoil'
       '%2Freference_library%2Fsurface_characteristics%2FAluminium_Foil_Surface_Characteristics_'
       'Catalogue_June20.pdf', _FT, 'F', 'same document as HX-S34b'),
    _S('PK-S8', 'EN 546-1:2006 preview',
       'https://preview.sist.si/sist-preview/24063/54988c6b69d94bbdb02eb270fce046e6/'
       'SIST-EN-546-1-2007.pdf', _EX, 'F, preview pages'),
    _S('PK-S9', 'EN 546-2:2006 preview',
       'https://cdn.standards.iteh.ai/samples/24064/6f0a23931a8b4680aae303172470dec2/'
       'SIST-EN-546-2-2007.pdf http://m.mydoc123.com/p-671667.html', _EX, 'F',
       'preview; Table 2 partly garbled, 8011A row cross-checked at the second URL; same '
       'document as BF-S31'),
    _S('PK-S10', 'EN 546-3:2006 preview',
       'https://preview.sist.si/sist-preview/24065/6ff880dc1b8146afb986de85fbf405ae/'
       'SIST-EN-546-3-2007.pdf', _EX, 'F', 'preview'),
    _S('PK-S11', 'EN 546-4:2006 preview',
       'https://preview.sist.si/sist-preview/24066/c2c3207c4f6f4237a44395ee49086090/'
       'SIST-EN-546-4-2007.pdf', _EX, 'F, clauses 1-6.3 only'),
    _S('PK-S12', 'ASTM B479-19 sample',
       'https://www.normadoc.com/media/file/1b/ef/26213ef991a09691757eaa3e6c37.pdf '
       'https://www.astm.org/b0479-19.html', _EX, 'F, partial'),
    _S('PK-S13', 'ASTM B373-19', 'https://www.astm.org/b0373-19.html', _AB, 'S'),
    _S('PK-S14', 'GB/T 3198-2020 text; pinhole table transcription',
       'https://www.foodcontactscience.com/uploads/20230517/1a7d21c14a7d15e5b723fcb613cd09c4.pdf '
       'https://chinastandards.org/standards/gb-t-3198-2020 '
       'https://www.zhengchongcai.cn/tools/aluminum-foil.html', _EX, 'F, excerpts / V',
       'standard text read as excerpts; the pinhole table is a third-party transcription [V]'),
    _S('PK-S15', 'YBB00152002-2015', 'https://www.gb-gbt.com/PDF/Chinese.aspx/YBB00152002-2015',
       _AB, 'S', 'snippet that reproduces the clauses'),
    _S('PK-S16', 'Mansell, PhD thesis, UTS 2007 (Alcoa Yennora)',
       'https://opus.lib.uts.edu.au/bitstream/10453/44028/13/02Whole%20part%202.pdf '
       'https://opus.lib.uts.edu.au/bitstream/10453/44028/10/01Front%20part%201.pdf', _AB, 'S'),
    _S('PK-S17', 'Symetal, foil for food containers',
       'https://www.symetal.gr/en/foil-for-food-containers', _VP, 'V'),
    _S('PK-S18', 'Impol foils', 'https://www.impol.com/products/rolled-products/foils/', _VP, 'V'),
    _S('PK-S19', 'Aluberg TDS 39A05, cold-form laminate',
       'https://www.aluberg.it/images/certificati/TDS/39A05_Ed_11.pdf', _VP, 'V'),
    _S('PK-S20', 'Hind Foils; Technofoils; RS Foils; Sambhav; Greenpack',
       'https://hindfoils.com/pharmaceuticals/ https://hindfoils.com/dairy/ '
       'https://technofoils.com/strip-pack-foils.php https://www.rsfoils.com/IndustriesDetail.html '
       'https://www.sambhavfoilsandflexibles.com/pharmaceutical-packaging/ '
       'https://crfoilgreenpack.com/child-resistant-blister-foil.html', _VP, 'V'),
    _S('PK-S21', 'Amcor, blister foil thicknesses',
       'https://www.amcor.com/insights/blogs/5-most-popular-foil-blister-pack-material-thicknesses-'
       'for-pharmaceuticals', _VP, 'V'),
    _S('PK-S22', 'SRF "Raflar" brochure',
       'https://images.nuernbergmesse.de/files/1b022469-a28f-8699-14a2-54daa3ac9692.pdf', _VP, 'V'),
    _S('PK-S23', 'Hindalco foil-stock sheet (reseller copies); HMC Korea',
       'https://3.imimg.com/data3/UA/FB/MY-2221993/aluminium-foil.pdf '
       'http://www.hmckorea.com/en/sub02_06.php', _VP, 'V'),
    _S('PK-S24', 'Haomei, cigarette foil',
       'https://www.aluminum-hm.com/application/cigarette-aluminum-foil/', _VP, 'V'),
    _S('PK-S25', 'Symetal, chewing-gum foil', 'https://symetal.gr/en/chewing-gum-foil', _VP, 'V'),
    _S('PK-S26', 'Kerry, "Aluminium foil packaging" (book chapter)',
       'https://oyairmaksahin.wordpress.com/wp-content/uploads/2019/01/Aluminium.pdf', _EX,
       'F, excerpt'),
    _S('PK-S27', 'Le and Sutcliffe, Wear 244 (2000) 71',
       'https://www.sciencedirect.com/science/article/abs/pii/S0043164800004415', _AB, 'S'),
    _S('PK-S28', 'Achenbach OPTIMILL; Bachmann/Achenbach; Primetals; Mino',
       'https://www.achenbach.de/en/machines-equipment/optimill-rolling-mills/'
       'optimill-foil-rolling-mills/ '
       'https://www.bachmann.info/media/881/download/Applikationsbeitrag_Achenbach_EN.pdf?v=1 '
       'https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/'
       'aluminum-foil-rolling-mill/ https://mino.it/laminazione-sottile-foil-finishing-mill/',
       _VP, 'V'),
    _S('PK-S29', 'Foil rolling oil notes (trade pages)',
       'https://www.tomorrowal.com/news/matters-needing-attention-in-rolling-aluminum-foil '
       'https://www.alufoil-china.com/news/aluminum-foil-rolling-oil-selection-management-'
       '75812933.html', _VP, 'V'),
    _S('PK-S30', 'Wikipedia, Aluminium foil; Telegraph supermarket foil test',
       'https://en.wikipedia.org/wiki/Aluminium_foil '
       'https://www.telegraph.co.uk/food-and-drink/features/best-worst-supermarket-aluminium-'
       'foils/', _AB, 'S'),
    _S('PK-S31', 'TMS 2024 abstract (TRC 8079 pinholes); Chen et al. (TRC 8021 stock); '
       'Kevorkijan et al. (Impol roll casting)',
       'https://www.programmaster.org/PM/PM.nsf/ApprovedAbstracts/F07C049FCFE77D8A852589DA0044E5B8'
       '?OpenDocument= https://www.scientific.net/MSF.877.296 '
       'http://www.metalurgija.org.rs/mjom/vol10/No%203/1KEVORKIJAN.pdf', _AB, 'S'),
    _S('PK-S32', 'Converter foil purchase specs',
       'https://www.jolybar.com/wp-content/uploads/2017/01/ALLM.pdf '
       'https://www.shrijay.in/wp-content/uploads/2026/02/TDS-SFL.pdf', _VP, 'V'),
    _S('PK-S33', 'Alucoat linfoil; Alborz; wine-capsule and cable-foil vendors',
       'https://www.alucoat-conversion.com/coated-aluminium-foil-food-packaging-lidding-linfoil/ '
       'https://alborziron.com/en/aluminum-factory/ '
       'https://www.htmmgroup.com/aluminium-foil/laminated-aluminium-foil/aluminum-wine-bottle-'
       'capsule.html https://www.alumfoils.com/a/aluminum-foil-roll-for-wine-capsule.html '
       'https://www.al-foils.com/product/12358011-aluminum-foil-for-cable-wrapping.html',
       _VP, 'V'),
    # ---- heat-exchanger / litho / other strip report
    _S('HX-S1', 'Gränges HEX catalogue 2025',
       'https://www.granges.com/contentassets/0fc3ddcf7f9d4dbe8870cb0917625b8b/granges_hex-'
       'catalogue_2025.pdf', _EX, 'F'),
    _S('HX-S2', 'EAA Aluminium Automotive Manual, Heat exchangers (2011)',
       'https://european-aluminium.eu/wp-content/uploads/2022/11/aam-applications-power-train-7-'
       'heat-exchangers.pdf', _EX, 'F'),
    _S('HX-S3', 'Novelis/Denso US 11,933,553', 'https://patents.us/US11933553', _EX, 'F'),
    _S('HX-S4', 'Novelis EP1250468', 'https://patents.google.com/patent/EP1250468A1/en', _EX, 'F'),
    _S('HX-S5', 'Novelis US2015/0041027', 'https://www.freepatentsonline.com/y2015/0041027.html',
       _EX, 'F'),
    _S('HX-S6', 'Mitsubishi Aluminum JP2002256403A',
       'https://patents.google.com/patent/JP2002256403A/en', _AB, 'A'),
    _S('HX-S7', 'Furukawa-Sky Review No. 4 (2008)',
       'https://www.uacj.co.jp/development/rd/review/furukawasky/004/pdf/04_abst07.pdf', _EX, 'F'),
    _S('HX-S8', 'UACJ US 10,161,693',
       'https://www.patents-review.com/a/20160116236-aluminum-alloy-fin-material-heat-exchangers-'
       'method.html', _AB, 'A'),
    _S('HX-S9', 'UACJ MONOBRAZE', 'https://www.uacj.co.jp/english/products/sheeting/mb-fin.html',
       _VP, 'none', _NOTAG + '; product page'),
    _S('HX-S10', 'Signi fin stock',
       'https://www.brazing-welding-aluminum.com/clad_unclad_aluminum_fin_stock_material.html',
       _VP, 'V'),
    _S('HX-S11', 'Chalco brazing foil',
       'https://www.chalcoaluminum.com/knowledge/aluminum-brazing-foil-2506-lx/ '
       'https://www.chalcoaluminum.com/application/aluminum-automotive/auto-brazed-foil/', _VP,
       'V'),
    _S('HX-S12', 'Brazing sheet table',
       'https://www.automotive-aluminum-sheet.com/aluminium-brazing-sheet-for-automotive/'
       'Aluminium-Brazing-sheet-strip-foil.html', _VP, 'V'),
    _S('HX-S13', 'Sapa SAE 2005-01-2012; US 7,691,489',
       'https://doi.org/10.4271/2005-01-2012 https://patents.google.com/patent/US7691489B2/en',
       _AB, 'A'),
    _S('HX-S14', 'Chalco B-tube',
       'https://www.chalcoaluminum.com/knowledge/aluminum-b-type-tube-2609-lyg/', _VP, 'V'),
    _S('HX-S16', 'SAE 2005-01-1390', 'https://doi.org/10.4271/2005-01-1390', _AB, 'A'),
    _S('HX-S17', 'EN 683-1/-2/-3 previews; EN 683-2:2024 catalogue',
       'https://preview.sist.si/sist-preview/24067/cf40fd9d7e6745b4a99f0a22bbbe6c6b/'
       'SIST-EN-683-1-2007.pdf https://preview.sist.si/sist-preview/24068/'
       '1ae515ace8074b17af58e169bad64f8e/SIST-EN-683-2-2007.pdf https://preview.sist.si/'
       'sist-preview/24069/ee6cb88d0c0140518cd3fa5ab7afd9a3/SIST-EN-683-3-2007.pdf '
       'https://standards.iteh.ai/catalog/standards/cen/9d06d0e4-d273-4152-8367-5b32b5b89050/'
       'en-683-2-2024', _EX, 'F, preview pages'),
    _S('HX-S18', 'EN 485-4 summaries',
       'https://www.aalco.co.uk/datasheets/Aluminium-Alloy-EN-Standards-for-Rolled-Aluminium_'
       '51.ashx https://www.alumeco.com/aluminium/data/tolerances/plates-and-sheets-cold-rolled/',
       _AB, 'A'),
    _S('HX-S19', 'European Aluminium ordering guide',
       'https://european-aluminium.eu/wp-content/uploads/2022/10/how-to-order-aluminium-according-'
       'to-european-standards_june-2019.pdf', _AB, 'A'),
    _S('HX-S20', 'HVAC fin vendors',
       'https://www.chalcoaluminum.com/knowledge/hydrophilic-lacquered-foil/ '
       'https://www.brazing-welding-aluminum.com/Aluminium_Aluminum_Precoated_Aluminium_Finstock/ '
       'https://www.stekalu.com/product/aluminum-fin-stock/ '
       'https://www.worthwillaluminium.com/product/aluminum-fin-stock-for-heat-exchanger/'
       'hydrophilic-aluminum-fin-stock/', _VP, 'V'),
    _S('HX-S21', 'CN102329992A', 'https://patents.google.com/patent/CN102329992A/en', _EX, 'F'),
    _S('HX-S22', 'Novelis CA2411128C', 'https://patents.google.com/patent/CA2411128C/en', _EX,
       'F'),
    _S('HX-S23', 'CN101805878A', 'https://eureka.patsnap.com/patent-CN101805878A', _AB, 'A'),
    _S('HX-S25', 'Hydro US 10,696,040 (litho strip, high cold-rolling pass reduction)',
       'https://patents.google.com/patent/US10696040B2/en '
       'https://www.patents-review.com/a/20190047279-litho-strip-high-cold-rolling-pass-'
       'reduction.html', _EX, 'F'),
    _S('HX-S26', 'Hydro US2011/0039121', 'https://www.freepatentsonline.com/y2011/0039121.html',
       _AB, 'none', _NOTAG + '; patent'),
    _S('HX-S27', 'Novelis US 7,267,734', 'https://exa.ai/library/legal/patent/rh0m3z823mz', _AB,
       'A'),
    _S('HX-S28', 'Alusuisse US2002/0189725', 'https://www.freepatentsonline.com/y2002/0189725.html',
       _EX, 'F'),
    _S('HX-S29', 'US 6,387,198', 'https://exa.ai/library/legal/patent/5r0rzldtgrq', _AB, 'A'),
    _S('HX-S30', 'US 5,562,784', 'https://exa.ai/library/legal/patent/f23bbk2kyrk', _AB, 'A'),
    _S('HX-S31', 'Mariglis, MPhil thesis, Manchester 2012',
       'https://research.manchester.ac.uk/en/studentTheses/da1f2345-26b3-46ee-9843-63475797aaa0',
       _AB, 'A'),
    _S('HX-S32', 'Ratchev et al. 2000', 'https://doi.org/10.1515/ijmr-2000-910613', _AB, 'A'),
    _S('HX-S33', 'Alcoa US 5,508,119; Reich et al. 1996',
       'https://patents.google.com/patent/US5508119A/en https://doi.org/10.1080/'
       '10402009608983498', _AB, 'A'),
    _S('HX-S34', 'Speira US 11,807,027; Hydro US2017/0190204',
       'https://exa.ai/library/legal/patent/r424c9bj2g7 https://www.patents-review.com/a/'
       '20170190204-litho-strip-electrochemical-roughening-method-manufacture.html', _AB, 'A'),
    _S('HX-S34b', 'EAFA foil surface catalogue',
       'https://www.alufoil.org/surface-characteristics?file=files%2Fimages_alufoil%2Fabout_alufoil'
       '%2Freference_library%2Fsurface_characteristics%2FAluminium_Foil_Surface_Characteristics_'
       'Catalogue_June20.pdf', _AB, 'A', 'same document as PK-S7'),
    _S('HX-S35', 'BWG litho line; Innoval levelling-line blog',
       'https://aluminiumtoday.com/news/bwg-litho-line-for-bridgnorth-aluminium '
       'https://www.innovaltec.com/levelling-line-blog/', _VP, 'V'),
    _S('HX-S35b', 'ISO 12635:2008 preview',
       'https://cdn.standards.iteh.ai/samples/43886/7056ec08d5114c6695e4dbc4c9f2d236/'
       'ISO-12635-2008.pdf', _AB, 'A'),
    _S('HX-S36', 'Achenbach book extract',
       'https://www.alufoil.org/files/images_alufoil/about_alufoil/reference_library/'
       'achenbach_extract.pdf', _EX, 'F', 'same document as PK-S5'),
    _S('HX-S36b', 'Litho vendors',
       'https://www.chalcoaluminum.com/knowledge/printing-aluminum-substrate/ '
       'http://www.henryaluminum.com/aluminum_coil/50.html '
       'https://www.uacj.co.jp/english/products/sheeting/printing-plate.html', _VP, 'V'),
    _S('HX-S37', 'Mill data (Primetals reference; IET paper; Achenbach news)',
       'https://www.primetals.com/en/references/nanshan-aluminum-co-limited-single-stand-6hi-non-'
       'reversing-cold-aluminum-mill/ https://digital-library.theiet.org/doi/full/10.1049/'
       'joe.2016.0182 '
       'http://news.hi-techinternational.com/2012/02/achenbach-foil-rolling-mill.html',
       _VP, 'V/A'),
    _S('HX-S38', 'Kaiser Warrick can sheet specification',
       'https://online.kaiseraluminum.com/depot/PublicProductInformation/Document/1081/'
       'Kaiser_Aluminum_Can_Sheet_Products.pdf', _EX, 'F'),
    _S('HX-S39', 'Closure, transformer and cable vendors',
       'https://www.worthwillaluminium.com/application/aluminum-in-packaging/aluminum-closure-'
       'stock/ https://www.worthwillaluminium.com/product/aluminum-coil-strip/aluminum-strip-foil-'
       'for-transformer-windings/ https://www.gneealuminum.com/info/aluminum-foil-for-cable-'
       '93970330.html', _VP, 'V'),
    _S('HX-S40', '3003 work-hardening study', 'https://pdf.hanspub.org/ms20180500000_10774181.pdf',
       _AB, 'A'),
    _S('HX-S41', 'Vollmer flatness paper',
       'https://vollmergmbh.de/fileadmin/user_upload/news/2019/aktuelles-2019-03.pdf', _AB, 'A',
       'a copper/thin-strip paper'),
    # ---- battery grade-by-gauge report (second survey); ids BG-G<n>
    _S('BG-G1', 'GB/T 33143-2022 draft English translation',
       'http://www.cnsmq.com/uploadfile/2025/0227/20250227042900196.pdf', _EX, 'EX',
       'same document as BF-S2; tables garbled'),
    _S('BG-G2', 'Chalco page reproducing GB/T 33143-2022 Tables 1, 2, 9',
       'https://www.chalcoaluminum.com/knowledge/lithium-ion-battery-foil/', _VP, 'VP',
       'producer page; the second survey\'s reading of GB/T 33143 Table 9'),
    _S('BG-G3', 'T/ZZB 2638-2022', 'https://www.ttbz.org.cn/Home/PdfFileStreamGet/c3QsNTk5MjU(eq)',
       _FT, 'FT', 'group standard; copies four rows of GB/T 33143 Table 9'),
    _S('BG-G4', 'T/ZZB 1203-2019 (power-cell foil, 10–16 µm)',
       'https://qxb-img-osscache.qixin.com/standards/e7007ea8cb458ac1eb6e98d305058bfd.pdf', _FT,
       'FT'),
    _S('BG-G5', 'UACJ Foil battery foil page (Japanese)',
       'https://ufo.uacj-group.com/techno/rd/battery.html', _VP, 'VP',
       'Japanese version of the BF-S3 page'),
    _S('BG-G6', 'Motoi et al., UACJ Technical Reports 1 (2014) 125',
       'https://www.uacj.co.jp/development/rd/review/vol1no1/pdf/vol1no1_18.pdf', _EX, 'EX',
       'same document as BF-S5'),
    _S('BG-G7', 'Ashizawa, Yamamoto, Furukawa-Sky Review 5 (2009) 1',
       'https://www.uacj.co.jp/development/rd/review/furukawasky/005/pdf/05_abst01.pdf', _FT, 'FT'),
    _S('BG-G8', 'Ihara et al., Kobe Steel Engineering Reports 65(2) (2015) 29',
       'https://www.kobelco.co.jp/r-d/technology-review/dumm/__icsFiles/afieldfile/2025/03/19/'
       '235_029-032.pdf', _FT, 'FT'),
    _S('BG-G9', 'Kohan Shoji high-strength collector foil',
       'https://battery-jp.net/strong_positive_electrode.html', _VP, 'VP'),
    _S('BG-G10', 'Sam-A product page (Korean)', 'https://sama-al.com/kor/business/foil/car', _VP,
       'VP', 'Korean version of the BF-S45 page'),
    _S('BG-G11', 'ETNews, Sam-A talk, 2021-04-28', 'https://www.etnews.com/20210428000130', _FT,
       'FT, trade press', 'trade-press article read in full'),
    _S('BG-G12', 'Newspim, Lotte Aluminium, 2020-09-16',
       'https://www.newspim.com/news/view/20200916000922', _EX, 'EX'),
    _S('BG-G13', 'Asia Economy, 2024-03-02',
       'https://www.asiae.co.kr/article/2024022716372407494', _EX, 'EX'),
    _S('BG-G14', 'Gränges cathode foil datasheet 2024',
       'https://www.granges.com/globalassets/09.-kampanjer/06.-battery-cathode-foil/03.-contact/'
       'granges-datablad_cathode-foil_2024.pdf', _FT, 'FT'),
    _S('BG-G15', 'Symetal battery foil', 'https://www.symetal.gr/en/battery-foil', _VP, 'VP'),
    _S('BG-G16', 'Speira battery foil',
       'https://www.speira.com/markets-products/battery-systems/battery-foil/', _VP, 'VP'),
    _S('BG-G17', 'Innoval Technology, "Aluminium battery foil", 2023',
       'https://www.innovaltec.com/www-innovaltec-com-insights-aluminium_battery_foil/', _EX,
       'EX'),
    _S('BG-G18', 'Armor primed foil',
       'https://www.armorbatteryfilms.com/our-products/primed-aluminium-foil/', _VP, 'VP'),
    _S('BG-G19', 'Mingtai and Haomei alloy-by-gauge pages',
       'https://www.mt5083lb.com/knowledge/585.html '
       'https://www.aluminum-hm.com/application/battery-aluminum-foil/', _VP, 'VP'),
    _S('BG-G20', 'OFweek, 1060 against 1100',
       'https://libattery.ofweek.com/2025-06/ART-36000-8110-30665024.html', _VP, 'VP'),
    _S('BG-G21', 'Orient Securities, battery foil report, 2023-02',
       'https://pdf.dfcfw.com/pdf/H3_AP202302131583078254_1.pdf', _EX, 'EX',
       'broker report; one figure read from a flattened chart'),
    _S('BG-G22', 'Huaxin Securities, 2022-12',
       'https://pdf.dfcfw.com/pdf/H3_AP202212191581210899_1.pdf', _EX, 'EX', 'broker report'),
    _S('BG-G23', 'LeadLeo, Li-ion battery foil, 2023',
       'https://pdf.dfcfw.com/pdf/H3_AP202303271584589758_1.pdf', _EX, 'EX'),
    _S('BG-G24', 'Targray cathode foil specification',
       'https://www.targray.com/li-ion-battery/cathode-materials/foils', _VP, 'VP'),
    _S('BG-G25', 'JIS H 4160, 1994 text', 'https://jis.eomec.com/jish41601994', _FT, 'FT',
       'mirror of the 1994 text; JIS H 4160:2006 itself not found'),
    _S('BG-G26', 'UACJ US 9,698,426 B2', 'https://exa.ai/library/legal/patent/z7mfjkqz2bs', _EX,
       'EX, with Table 3', 'Table 3 read; the composition and process tables were not in the '
       'excerpt'),
    _S('BG-G27', 'UACJ CN application 201380010002',
       'https://www.xjishu.com/zhuanli/24/201380010002.html', _EX, 'EX'),
    _S('BG-G28', 'GB/T 22648-2023 mirrors', 'https://www.duodown.com/biaozhun/2155908.html '
       'https://www.guifanku.com/784986.html', _EX, 'EX',
       'same standard as BF-S29; the second survey read it as excerpts (Tables 5–9 dropped)'),
    _S('BG-G29', 'T/ZZB 2076-2021 reseller summary',
       'https://kpt-bj.com/t-zzb-2076-2021-aluminum-foil-for-aluminum-laminate-film-of-pouch-'
       'cell-1302142151.html', _VP, 'VP'),
    _S('BG-G30', 'Laminate structures',
       'https://www.libmachine.cn/?products_66%2F372.html= '
       'https://xiaoweitop.com/zh-CN/equipments/aluminum-laminated-film-for-pouch-cell-case-t-'
       '113um/ http://www.taiwanbattery.org.tw/media/file/admin/20230901094346tBWI.pdf', _VP,
       'VP, EX', 'tagged VP and EX; recorded at the weaker status'),
    _S('BG-G31', 'HDM battery foil', 'https://hdmetalm.com/battery-aluminum-foil/', _VP, 'VP'),
    _S('BG-G32', '8021 pouch-foil stock patent',
       'https://www.xjishu.com/zhuanli/24/202511388492.html', _EX, 'EX',
       'same document as BF-S33'),
    _S('BG-G33', 'He et al., Material Sciences 12 (2022) 123',
       'https://pdf.hanspub.org/ms20220200000_28186169.pdf', _EX, 'EX'),
    _S('BG-G34', 'Mingtai tab foil', 'https://www.mt6061lb.com/lvbannews/1102.html '
       'https://www.mt6061lb.com/lvbannews/1103.html', _VP, 'VP'),
    _S('BG-G35', 'MC Aluminum', 'https://www.alummc-foil.com/product/battery-aluminum-foil.html',
       _VP, 'VP', 'same page as BF-S48'),
    _S('BG-G36', 'Supercapacitor electrode and etched foil',
       'https://www.ssntm.com/product/dry-coating-electrode-edlc-eletrode-tape/ '
       'https://www.sciencegears.com.au/eal-foil-etched-aluminum-foil', _VP, 'VP'),
    _S('BG-G37', 'Xia et al., Electronic Components and Materials 2025(11)',
       'http://www.qikanvip.com/qkml/141553.html', _AB, 'SN'),
    _S('BG-G38', 'HSMetal carbon-coated foil',
       'https://www.lyhsmetal.com/lithium-battery-materials/double-side-carbon-coated-aluminium-'
       'foil.html', _VP, 'VP'),
    _S('BG-G39', 'Sodium-ion foil gauges',
       'http://www.newsijie.com/chanye/dianzidianqi/jujiao/2026/0608/11366463.html '
       'https://www.xjishu.com/zhuanli/59/202511576733.html', _VP, 'VP, EX',
       'tagged VP and EX; recorded at the weaker status'),
    _S('BG-G40', 'Temper definitions',
       'https://www.totalmateria.com/en-us/articles/work-hardening-aluminum-alloys-1/ '
       'https://unitedaluminum.com/aluminum-technical-data-alloy-chemistry-and-mechanical/ '
       'https://www.chalcoaluminum.com/blog/temper-aluminum-alloys/', _VP, 'EX, VP',
       'tagged EX and VP; recorded at the weaker status'),
    _S('BG-G41', 'Saito, Tanaka, UACJ Technical Reports 9 (2022) 63',
       'https://www.uacj.co.jp/development/rd/review/vol9no1/pdf/vol9no1_11.pdf', _FT, 'FT',
       'same document as BF-S6, which the first survey read as excerpts'),
    _S('BG-G42', 'Lab-supply battery foil page, 16 µm 1235',
       'http://www.scimaterials.cn/ProDetail.aspx?ProId=1797', _VP, 'VP'),
    _S('BG-G43', '1235 foil vendor note', 'https://www.cnal.com/product/39026221.shtml', _VP,
       'VP'),
    _S('BG-G44', 'Matsuoka, Higashi, J. JILM 67 (2017) 641',
       'https://www.jstage.jst.go.jp/article/jilm/67/12/67_671206/_pdf', _EX, 'EX'),
    # ---- process-temperature report (third research pass); ids PT-T<n>; T35 = PK-S7
    _S('PT-T1', 'CN112934967B, battery foil and processing method',
       'https://patents.google.com/patent/CN112934967B/zh', _EX, 'EX'),
    _S('PT-T2', 'CN application 202110122451 (same applicant, slitting variant)',
       'https://www.xjishu.com/zhuanli/23/202110122451.html', _EX, 'EX'),
    _S('PT-T3', 'Mansell, PhD thesis, UTS 2007, part 2',
       'https://opus.lib.uts.edu.au/bitstream/10453/44028/13/02Whole%20part%202.pdf', _EX, 'EX'),
    _S('PT-T4', 'Kerth, Amann, Raber, Weber, Int. Metall. Rev. 20 (1975) 185',
       'https://www.scribd.com/document/949516974/kerth1975', _EX, 'EX',
       'same document as PK-S1; read from the text copy saved by the packaging survey'),
    _S('PT-T5', 'Li, Yang, Huang, foil rolling process factors, 2019',
       'https://www.zzqklm.com/w/kjlw/24793.html https://bbs.plcjs.com/thread-601856-1-1.html',
       _EX, 'EX'),
    _S('PT-T6', 'Three-pass battery foil patent (Jiangyin Xinren)',
       'https://www.xjishu.com/zhuanli/23/202311439469.html', _EX, 'EX',
       'same document as BF-S16'),
    _S('PT-T7', 'Bátorfi, Pál, Chakravarty, Sidor, Appl. Sci. 13 (2023) 4359',
       'https://www.mdpi.com/2076-3417/13/7/4359', _AB, 'AB'),
    _S('PT-T8', 'Chen Jiuxia, rolling-oil control for electronic foil, Metal World 2008(2)',
       'https://metalworld.ustb.edu.cn/cn/article/pdf/preview/JSSJ200802016.pdf', _EX, 'EX'),
    _S('PT-T9', 'ExxonMobil Somentor 29 sales specification',
       'https://www.exxonmobilchemical.com/en/chemicals/webapi/dps/v1/datasheets/130000107309/'
       '1/en', _FT, 'FT'),
    _S('PT-T10', 'Eastto aluminium rolling oils 80 and 110',
       'https://www.eastopet.com/Aluminium_Rolling_Oil/ALUMINIUM_ROLLING_OILS.pdf', _VP, 'VP'),
    _S('PT-T11', 'Mobil Wyrol additive concentrates',
       'https://www.mobil.com/en/sap/our-products/product-series/wyrol', _VP, 'VP'),
    _S('PT-T12', 'Exxsol D80 safety data sheets',
       'https://nextsds.com/sds/en/281331501287376/exxsol-d80-fluid '
       'https://pure-chemical.com/site/others/msds/Exxsol%20D80.pdf', _AB, 'AB'),
    _S('PT-T13', 'Missouri rule 10 CSR 10-5.451, aluminium foil rolling',
       'https://www.epa.gov/sites/default/files/2017-09/documents/10-5451_0.pdf', _FT, 'FT'),
    _S('PT-T14', 'AXA XL PRC.17.13.1, Aluminum Rolling Mills',
       'https://axaxl.com/prc-guidelines/-/media/axaxl/files/pdfs/prc-guidelines/prc-17/'
       'prc17131aluminumrollingmillsv1.pdf', _EX, 'EX'),
    _S('PT-T15', 'Foil rolling and lubrication technology (presentation text)',
       'https://alfoilworld.com/knowledge/knowledge-2d1c71f1/?lang=zh', _VP, 'VP'),
    _S('PT-T16', 'Yin, Li, Zhang, Li, J. Univ. Sci. Technol. Beijing 25(6) 2003 (heat partition)',
       'https://cje.ustb.edu.cn/article/doi/10.13374/j.issn1001-053x.2003.06.020', _AB, 'AB',
       'abstract only; a net heat balance from measured strip surface temperature'),
    _S('PT-T17', 'Yin, Li, Zhang, J. Univ. Sci. Technol. Beijing 27(4) 2005',
       'https://cje.ustb.edu.cn/article/doi/10.13374/j.issn1001-053x.2005.04.023', _AB, 'AB'),
    _S('PT-T18', 'Shao, He, Yang et al., Chin. J. Eng. 37(8) 2015, 1092',
       'http://download.cucdc.com/wenku/7e866ecc01884bf4b0beb581b59e030c.html', _EX,
       'FT, garbled mirror', 'tagged FT by the report but read from a garbled mirror; '
       'recorded as excerpt'),
    _S('PT-T19', 'Horák, Raudenský, Pohanka et al., Engineering Mechanics 18 (2011) 81',
       'https://www.engineeringmechanics.cz/pdf/18_2_081.pdf', _EX, 'EX'),
    _S('PT-T20', 'Innoval, "Optimising spray cooling", 2016',
       'https://www.innovaltec.com/optimising-spray-cooling-blog/', _FT, 'FT'),
    _S('PT-T21', 'Lechler SELECTOSPRAY brochure and product page',
       'https://www.lechlerusa.com/fileadmin/media-usa/Literature/Brochures/metal/'
       'Roll_Cooling_SELECTOSPRAY_brochure.pdf '
       'https://www.lechlerusa.com/en/products/product-by-market/metals/nozzles-for-roll-cooling/'
       'selectospray', _VP, 'VP'),
    _S('PT-T22', 'Tucker (Lechler), flatness and profile: spray actuator design, 2006',
       'https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_'
       'walzenkuehlung_01-2006_flatness-and-profile-the-problems-that-can-exist-in-the-design-'
       'of-the-spray-actuators_dtucker_en.pdf', _EX, 'EX'),
    _S('PT-T23', 'Lloyd (Lechler), fundamentals of roll cooling and flatness control, 2010',
       'https://www.lechler.com/fileadmin/media/fachberichte/metallurgy/lechler_fachbericht_'
       'walzenkuehlung_09-2010_fundamentals-of-roll-cooling-and-control-of-flatness-at-primary-'
       'cold-reduction_dlloyd_en.pdf', _EX, 'EX'),
    _S('PT-T24', 'Primetals hot edge induction heating',
       'https://www.primetals.com/en/portfolio/solutions/cold-rolling/non-ferrous/aluminum/'
       'hot-edge-induction-heating/', _VP, 'VP'),
    _S('PT-T25', 'Liu, Wu, He, Yang, Chen, J. Univ. Sci. Technol. Beijing 27(1) 2005',
       'http://download.cucdc.com.cn/wenku/e4745e5b77164f1b8568a4905130a323.html', _EX, 'EX'),
    _S('PT-T26', 'Davies, Sivilotti, Tulett, Metals Technology 2 (1975)',
       'https://doi.org/10.1179/030716975803277735', _AB, 'AB'),
    _S('PT-T27', 'Li Fang, additive for aluminium cold rolling lubrication, thesis',
       'https://www.collectionscanada.gc.ca/obj/thesescanada/vol2/OWA/TC-OWA-5135.pdf', _EX,
       'EX'),
    _S('PT-T28', 'Reich, Wise, Colbert, Tribology Transactions 2008',
       'https://doi.org/10.1080/10402000801911796', _AB, 'AB'),
    _S('PT-T29', 'CN111438187A, high-hardness rolls for battery foil',
       'https://patents.google.com/patent/CN111438187A/zh', _EX, 'EX', 'same document as BF-S13'),
    _S('PT-T30', 'CN application 202310021340, raising wetting tension of battery foil',
       'https://www.xjishu.com/zhuanli/23/202310021340.html', _EX, 'EX'),
    _S('PT-T31', 'Matmatch, AA 1100-H18', 'https://matmatch.com/materials/mitf51-aa-1100-h18',
       _AB, 'AB'),
    _S('PT-T32', 'Recovery kinetics in AA1050 deformed to ultrahigh strain (DTU postprint)',
       'https://backend.orbit.dtu.dk/ws/portalfiles/portal/125728953/postprint.pdf', _EX, 'EX'),
    _S('PT-T33', 'Allazadeh, strain-rate sensitivity of AA1050, 2020',
       'https://strathprints.strath.ac.uk/74717/1/Allazadeh_ISSJ_2020_Computing_strain_rate_'
       'sensitivity_of_aluminium_alloy_1050.pdf', _EX, 'EX'),
    _S('PT-T34', 'Wu, Liang, Tang, Pan, Appl. Therm. Eng. 106 (2016) 1002 (introduction)',
       'https://www.sciencedirect.com/science/article/abs/pii/S1359431116309929', _EX, 'EX'),
    _S('PT-T36', 'Fu, Zhang, Liao, Jiang, Heat Treatment of Metals 50(9) 2025, 181',
       'http://www.jsrcl.net/CN/10.13251/j.issn.0254-6051.2025.09.029', _AB, 'AB'),
    _S('PT-T37', '"Milling Over Rolling Oils", Lubes\'n\'Greases 2017',
       'https://www.lubesngreases.com/magazine/23_9/milling-over-rolling-oils/', _EX, 'EX'),
    _S('PT-T38', 'CN202803755U, coolant spray device for a foil roughing mill',
       'https://www.xjishu.com/zhuanli/23/201220412752.html', _FT, 'FT'),
    _S('PT-T39', 'Toei Denka, typical mechanical properties of aluminium alloys',
       'https://toeidenka.co.jp/refer/mechanical_strength_of_aluminum.html', _EX, 'EX'),
    # ---- thermal, material and dynamics gap report (SPEC17 B3, B4; ids and read tags as in
    # section 9 of docs/simulation-coverage-gaps.md)
    _S('TM-LB1', 'Bonatti, Mohr, anisotropic viscoplasticity and fracture of fine grained '
       'metallic aluminum foil used in Li-ion batteries', 'https://old.mohr.ethz.ch/papers/56.pdf',
       _EX, 'EX', 'excerpt of the full paper'),
    _S('TM-LB2', 'Hara, Egusa, Mihara, Tanaka, Ohnuma, Abe, Mater. Trans. 62(4) (2021)',
       'https://www.jstage.jst.go.jp/article/matertrans/62/4/62_MT-M2020349/_pdf/-char/en',
       _EX, 'EX', 'most of the text'),
    _S('TM-LB3', 'Liu, Huang, Lloyd, Hansen, Acta Mater. 50 (2002) 3789',
       'https://doi.org/10.1016/s1359-6454(02)00174-x', _AB, 'AB'),
    _S('TM-LB6', 'Hasenclever, ICAA9 (2004), AlFe alloys AA1050-AA8021',
       'http://www.icaa-conference.net/ICAA9/data/papers/GP%20124.pdf', _EX, 'EX'),
    _S('TM-LB10', 'Allazadeh (2020), rate sensitivity of AA1050-H14',
       'https://strathprints.strath.ac.uk/74717/1/Allazadeh_ISSJ_2020_Computing_strain_rate_'
       'sensitivity_of_aluminium_alloy_1050.pdf', _EX, 'EX', '= PT-T33'),
    _S('TM-LB12', 'Ha, Fones, Kinsey, Korkolis, Materials (2020), AA1100-O',
       'https://pmc.ncbi.nlm.nih.gov/articles/PMC7579055/', _EX, 'EX'),
    _S('TM-LB13', 'Batorfi et al., Appl. Sci. 13 (2023) 4359',
       'https://www.mdpi.com/2076-3417/13/7/4359', _EX, 'EX', '= PT-T7'),
    _S('TM-LB15', 'Zhang, Chen, Fan, Chen, Xiao, Coatings 15 (2025) 472',
       'https://www.mdpi.com/2079-6412/15/4/472', _EX, 'EX', 'excerpt of the full paper'),
    _S('TM-LB18', 'Chen et al., Mater. Res. Express (2020), AA8021 foil',
       'https://google.iopscience.iop.org/article/10.1088/2053-1591/abb7ab', _EX, 'EX'),
)
_SOURCES = {s.id: s for s in _SOURCE_LIST}

# --------------------------------------------------------------------------- data helpers


def _q(x):
    """Round an SI conversion to 12 significant digits (removes binary noise only)."""
    return float(f'{x:.12g}')


def _r(lo, hi, disp, src, note='', bound='span', status=None):
    unit, k, _ = DISPLAY[disp]
    return Range(None if lo is None else _q(lo * k), None if hi is None else _q(hi * k), unit,
                 _split(src), note, bound, status, disp)


def _pt(v, disp, src, note='', status=None):
    return _r(v, v, disp, src, note, 'typical', status)


def _min(v, disp, src, note='', hi=None, status=None):
    return _r(v, hi, disp, src, note, 'minimum', status)


def _max(v, disp, src, note='', status=None):
    return _r(None, v, disp, src, note, 'maximum', status)


def _s(text, src='', *values, topic='', status=None):
    return Statement(text, _split(src), tuple(values), topic, status)


def _nf(text, src='', status=None):
    """A 'not found' entry: an absence, so sources are optional."""
    return Statement(text, _split(src), (), 'not_found', status)


def _i(name, text, src, status=None):
    return Item(name, text, _split(src), status)


def _items(names, text, src, status=None):
    return tuple(_i(n, text, src, status) for n in names)


def _d(name, appearance, cause, src, *values):
    return Defect(name, appearance, cause, _split(src), tuple(values))


def _sv(spec, disp, src):
    """Strength value DSL: ('typ', v) | ('min', v[, v_hi]) | ('max', v) | ('span', lo, hi)."""
    if spec is None:
        return None
    kind = spec[0]
    if kind == 'typ':
        return _pt(spec[1], disp, src)
    if kind == 'min':
        return _min(spec[1], disp, src, hi=spec[2] if len(spec) > 2 else None,
                    note='range of published minima' if len(spec) > 2 else '')
    if kind == 'max':
        return _max(spec[1], disp, src)
    return _r(spec[1], spec[2], disp, src)


def _st(alloys, temper, condition, src, rm=None, rp=None, a=None, grade='', note=''):
    names = tuple(a.strip() for a in alloys.split(',')) if isinstance(alloys, str) else alloys
    return Strength(tuple(names), temper,
                    condition, _split(src), _sv(rm, 'MPa', src), _sv(rp, 'MPa', src),
                    _sv(a, '%', src), grade, note)


def _um(*g):
    return tuple(tuple(_q(x * 1e-6) for x in v) if isinstance(v, tuple) else _q(v * 1e-6)
                 for v in g)


def _mm(*g):
    return tuple(tuple(_q(x * 1e-3) for x in v) if isinstance(v, tuple) else _q(v * 1e-3)
                 for v in g)


def _mpm(*v):
    return tuple(_q(x / 60) for x in v)


def _sched(label, gauges, src, **kw):
    return PassSchedule(label, gauges, _split(src), **kw)


def _union_sources(objs):
    out = []
    for o in objs:
        for s in o.sources:
            if s not in out:
                out.append(s)
    return tuple(out)


def _per_pass_span(schedules, basis, *, include_block_means=False):
    """Computed span of per-pass reductions: single passes, plus the equal-split means of
    known-size blocks only when ``include_block_means`` (the basis text must say so)."""
    vals, used = [], []
    for s in schedules:
        ppr = [r for r in s.per_pass_reductions()
               if include_block_means or r[3] == 'single_pass']
        if ppr:
            used.append(s)
        for _, lo, hi, _kind in ppr:
            vals += [_q(lo), _q(hi)]
    if not vals:
        return None
    return Range(min(vals), max(vals), 'fraction', _union_sources(used), basis, 'span',
                 'computed', '%')


def _final_pass_from(schedules, *, max_exit_m=None, speed=None, doubled_speed=None, notes=(),
                     reduction=None, basis=''):
    """Final-pass entry gauge and reduction computed from the last step of each schedule."""
    entries, reds, used = [], [], []
    for s in schedules:
        if s.passes()[-1] != 1:
            continue
        g = s.gauges()
        if max_exit_m is not None and g[-1][1] > max_exit_m * (1 + 1e-12):
            continue
        used.append(s)
        entries += [_q(x) for x in g[-2]]
        reds += [_q(x) for x in s.reductions()[-1]]
    src = _union_sources(used)
    entry = (Range(min(entries), max(entries), 'm', src, basis, 'span', 'computed',
                   'um' if max(entries) < 1e-4 else 'mm') if entries else None)
    if reduction is None and reds:
        reduction = Range(min(reds), max(reds), 'fraction', src, basis, 'span', 'computed', '%')
    return FinalPass(entry, reduction, speed, doubled_speed, tuple(notes))


def _speed_span(schedules, note):
    v = [x for s in schedules if s.speeds_m_s for x in s.speeds_m_s]
    if not v:
        return None
    used = [s for s in schedules if s.speeds_m_s]
    return Range(min(v), max(v), 'm/s', _union_sources(used), note, 'span', None, 'm/min')


# --------------------------------------------------------------------------- shared facts
FOIL_DEFECTS = (
    _d('Rolling stripes', 'Gloss side only, constant along the rolling direction.',
       'Local work-roll wear, or rolls damaged by foreign material from casting or foil stock.',
       'PK-S7'),
    _d('Heat stripes', 'Grey, straight to snaking.',
       'Temperature or flatness differences across the width, or a locally overheated roll.',
       'PK-S7'),
    _d('Gloss difference', 'Matt side only.',
       'Unstable separating-oil application at doubling.', 'PK-S7'),
    _d('Broken matt', 'Bright spots on the matt side.',
       'Too much deformation or too high speed in the doubled pass.', 'PK-S7'),
    _d('Chatter marks', 'Not described beyond the name in the report.',
       'Mill or grinder vibration.', 'PK-S7'),
    _d('Grooves', 'Not described beyond the name in the report.',
       'Unfavourable flatness profile.', 'PK-S7'),
)
STRIP_DEFECTS = (
    _d('Rolled-in dirt and black streaks', 'Dirt and black streaks rolled into the surface.',
       'Roll coating and pick-up re-transfer; debris rises with reduction and roll roughness, '
       'moving from abrasive to adhesive wear.', 'HX-S33'),
    _d('Herringbone', 'Not described beyond the name in the report.',
       'Appears at ≥55 % per pass on hard alloys with ground rolls (stick-slip film breakdown); '
       'hard alloys are usually held to about 45 % per pass.', 'HX-S33',
       _min(55, '%', 'HX-S33', 'onset per-pass reduction on hard alloys with ground rolls'),
       _pt(45, '%', 'HX-S33', 'usual per-pass limit for hard alloys ("about")')),
    _d('Heat stripes', 'Not described beyond the name in the report.',
       'Cross-width temperature or flatness differences.', 'HX-S34b'),
    _d('Rolling stripes', 'Not described beyond the name in the report.',
       'Local work-roll wear.', 'HX-S34b'),
    _d('Smut', 'Not described beyond the name in the report.',
       'Mixed intermetallic phases in un-homogenised cast strip.', 'HX-S22'),
)
_STRIP_DEFECT_CAVEAT = _s('No fin-stock- or strip-product-specific study of streak and band '
                          'causes was found; the named defects listed are the report\'s general '
                          'cold-rolling causes.', 'HX-S33 HX-S34b HX-S22')

STD_EN546_1 = _i('EN 546-1', 'Covers 6–200 µm. Defines converter foil (6–200 µm, single or '
                 'double rolled), consumer foil (10–24 µm) and container foil (single-rolled, '
                 '35–200 µm).', 'PK-S8')
STD_EN546_2 = _i('EN 546-2', 'Mechanical properties: 15 mm strip, 50 or 100 mm gauge length; '
                 'Table 1 (O and H18 by gauge band), Table 2 (container tempers; partly garbled '
                 'in the report\'s read).', 'PK-S9')
STD_EN546_3 = _i('EN 546-3', 'Tolerances: single spot ±6 % single-rolled, ±8 % double-rolled; '
                 'lot average ±6 / 5 / 4 % (single) and ±8 / 6 / 4 % (double) for ≤3 t, 3–10 t, '
                 '>10 t; width ±1 mm up to 1000 mm, ±2 mm above; weighing is the referee method.',
                 'PK-S10')
STD_EN546_4 = _i('EN 546-4', 'Pinholes are <0.2 mm in 6–20 µm foil; roll holes are >0.2 mm and '
                 'periodic; light box 1000–1500 lux, ignore <0.02 mm; limits by agreement; burst '
                 'test for consumer foil, Erichsen for container foil.', 'PK-S11')
STD_B479 = _i('ASTM B479-19', 'Annealed foil, ≥98 % Al, 6.4 µm to <150 µm; alloys 1100, 1145, '
              '1235, 8011, 8079, 8111; thickness ±10 % per roll; tensile by agreement; pinholes '
              'by B926 with no numeric limit (≥50 µm "virtually free").', 'PK-S12')
STD_GBT3198 = _i('GB/T 3198-2020', 'Local thickness ±6 % (ordinary) or ±5 % (high precision) at '
                 '≤9 µm, ±5 % or ±4 % above; lot average ±5 / 4 / 3 %; pinhole limits per grade '
                 '(third-party transcription).', 'PK-S14')
STD_GBT22638 = _i('GB/T 22638', 'Test methods: .1 thickness, .2 pinholes, .3 stickiness, .4 '
                  'wetting tension, .5 wettability, .6 DC resistance, .7 heat-seal strength.',
                  'PK-S14')
STD_YBB = _i('YBB00152002-2015 (China, pharma lidding)', 'No pinholes >0.3 mm; ≤1 per m² at '
             '0.1–0.3 mm; burst ≥98 kPa; heat seal ≥7.0 N/15 mm to PVC.', 'PK-S15')
STD_B373 = _i('ASTM B373', 'Capacitor foil, 4.3–12.7 µm, 1145 / 1235. The report does not say '
              'which capacitor foil type it covers.', 'PK-S13')
STD_EN573_3 = _i('EN 573-3', 'Chemistry only; not read directly.', 'PK-S9')
STD_EN683 = _i('EN 683-1/-2/-3', 'Finstock: scope 60–400 µm, unclad only; 3003 and 1050A '
               'properties by temper; gauge ±6 % single reading, average ±5 / ±4 / ±3 % for '
               'lots ≤3 t / 3–10 t / >10 t; width ±0.2 to ±1.0 mm; the O/H22/H24 table was not '
               'read.', 'HX-S17')
STD_EN485_4 = _i('EN 485-4', 'Applies above 0.20 mm: ±0.02 mm for 0.2–0.4 mm at ≤1000 mm width '
                 '(soft-alloy group); strip flatness is not specified.', 'HX-S18')
STD_EN485_1 = _i('EN 485-1 with special requirements', 'How litho strip is ordered, plus '
                 'qualification.', 'HX-S19')
STD_ISO12635 = _i('ISO 12635', 'Litho plate thickness ±0.010 mm; CtP edge wave ≤3.0 mm (1.5 mm '
                  'recommended).', 'HX-S35b')
FOIL_STANDARDS = (STD_EN546_1, STD_EN546_2, STD_EN546_3, STD_EN546_4, STD_B479, STD_GBT3198,
                  STD_GBT22638)
GENERAL_STANDARDS = FOIL_STANDARDS + (STD_YBB, STD_B373, STD_EN573_3, STD_EN683, STD_EN485_4,
                                      STD_EN485_1, STD_ISO12635)
GENERAL_STANDARDS_NOT_READ = _nf('EN 573-3, ASTM B209, JIS H4000/H4160, GB/T 3880 and YS/T 95.1 '
                                 'limits were not read (catalogue records only); anything beyond '
                                 'their scope would be from memory.', 'HX-S17')

EN683_STRENGTH = (
    _st('3003', 'H14', 'EN 683 finstock minimum/range', 'HX-S17', rm=('span', 145, 185),
        rp=('min', 120), a=('min', 1)),
    _st('3003', 'H16', 'EN 683 finstock minimum/range', 'HX-S17', rm=('span', 165, 205),
        rp=('min', 145)),
    _st('3003', 'H18', 'EN 683 finstock minimum', 'HX-S17', rm=('min', 190), rp=('min', 160)),
    _st('3003', 'H19', 'EN 683 finstock minimum', 'HX-S17', rm=('min', 210), rp=('min', 180),
        a=('min', 0.5)),
    _st('1050A', 'H14', 'EN 683 finstock minimum/range', 'HX-S17', rm=('span', 105, 145),
        rp=('min', 85)),
)

# --------------------------------------------------------------------------- battery collector
BATTERY_SCHEDULE_CAVEAT = _s(
    'Most important flag of the battery report: the two schedules quoted in earlier versions '
    'of this project\'s documentation as single-sheet battery-foil practice '
    '(260→135→65→30 µm and 280→120→55→24 µm) come from the trade page BF-S17. There the next '
    'pass is listed as 24×2→12×2 µm and 28×2→15×2 µm, i.e. doubled. So 30 µm and 24 µm are '
    'doubling-entry gauges for one-side-bright foil, not single-sheet final gauges. The '
    'trade page\'s first-plant row prints "302→152", which the report reads as '
    '30×2→15×2 µm.', 'BF-S17',
    _pt(30, 'um', 'BF-S17', 'doubling-entry gauge, trade-page plant 1 schedule'),
    _pt(24, 'um', 'BF-S17', 'doubling-entry gauge, trade-page plant 2 schedule'),
    topic='doubling_entry_schedules')

TENSION_LINES = _s(
    '"Tension lines": longitudinal stripes at 5–20 mm pitch appear below 15 µm and worsen as '
    'gauge falls; drivers are tension, roll roughness, roll parallelism, roll pressure and pass '
    'reduction.', 'BF-S21',
    _r(5, 20, 'mm', 'BF-S21', 'stripe pitch'),
    _max(15, 'um', 'BF-S21', 'gauge below which the stripes appear'),
    topic='tension_lines')

_BF_SINGLE = (
    _sched('BF-S12 1100, 4 passes from 300 µm', _um(300, 140, 66, 32, 15), 'BF-S12',
           alloy='1100', note='single-sheet, two-side-bright'),
    _sched('BF-S12 1100, 4 passes from 270 µm', _um(270, 128, 58, 26, 13), 'BF-S12',
           alloy='1100', note='single-sheet, two-side-bright'),
    _sched('BF-S12 1100, 4 passes from 260 µm', _um(260, 115, 55, 25, 12), 'BF-S12',
           alloy='1100', note='single-sheet, two-side-bright'),
    _sched('BF-S11 5 passes from 240 µm', _um(240, 125, 64, 34, 20, 13), 'BF-S11',
           note='single-sheet, two-side-bright'),
    _sched('BF-S13 5 passes from 260 µm', _um(260, 130, 65, 32, 17, 12), 'BF-S13',
           note='single-sheet, two-side-bright; the BF-S13 text also says "doubled rolling" on '
                'the finishing mill (see disagreements)'),
    _sched('BF-S14 5 passes from 250 µm', _um(250, 100, 59, 30, 15, (9, 10)), 'BF-S14',
           note='single-sheet, two-side-bright; final gauge published as 9–10 µm'),
    _sched('BF-S15 1070, 5 passes from 360 µm', _um(360, 200, 100, 50, 25, 15), 'BF-S15',
           alloy='1070', note='single-sheet, two-side-bright'),
    _sched('BF-S15 1070, 4 passes from 360 µm', _um(360, 165, 65, 32, 20), 'BF-S15',
           alloy='1070', note='single-sheet, two-side-bright'),
    _sched('BF-S16 3 passes from 220 µm', _um(220, 80, 30, 13), 'BF-S16',
           note='single-sheet, two-side-bright'),
    _sched('BF-S8 Speira, last 3 of 9 passes from 4.5 mm', _um(105, 57, 23, 15), 'BF-S8',
           alloy='Speira high-strength',
           note='from 4.5 mm in 9 passes, max 60 % per pass, 24 h rest between passes below '
                '0.105 mm, no anneal; only the last passes are published'),
)
_BF_DOUBLED = (
    _sched('BF-S17 trade-page plant 1 schedule, doubled last pass', _um(260, 135, 65, 30, 15), 'BF-S17',
           doubled_from_index=3,
           note='trade page; the last pass is printed "302→152", read by the report as '
                '30×2→15×2 µm; one-side-bright'),
    _sched('BF-S17 trade-page plant 2 schedule, doubled last pass', _um(280, 120, 55, 24, 12), 'BF-S17',
           doubled_from_index=3, note='trade page; last pass 24×2→12×2 µm; one-side-bright'),
    _sched('BF-S17 doubled pass 28×2→15×2 µm (schedule not stated)', _um(28, 15), 'BF-S17',
           doubled_from_index=0,
           note='trade page; the report lists this doubled pass without saying which schedule '
                'it follows'),
)

# --------------------------------------------------------------------------- battery grade table
# Second battery survey (sources BG-G<n>): which alloy and temper at which gauge. Every value is
# quoted from that report; the usual-choice and evidence columns are the report's own synthesis
# and carry the sources of the report's table row.
_GB_NOTE = ('GB/T 33143-2022 Table 9 minimum, H18 (read from a producer page reproducing the '
            'table [BG-G2]; cross-checked against BG-G1 and BG-G3)')


def _gb(v):
    return _min(v, 'MPa', 'BG-G2', _GB_NOTE)


GB_TABLE_READ = _s(
    'GB/T 33143-2022 Table 9 minima (all H18) were read from a producer page that reproduces the '
    'table, cross-checked against the garbled draft translation and against T/ZZB 2638-2022, '
    'which copies four of its rows. Where the table sets no value for an alloy in a band, none '
    'is given here. An official copy of Table 9 was not found.', 'BG-G2 BG-G1 BG-G3',
    topic='gb_table_read')
GB_ELONGATION = _s(
    'GB/T 33143-2022 elongation minima are 1.0–3.0 %, depending on alloy, gauge length and one- '
    'or two-side-bright; 8A21 is ≥4.0 %.', 'BG-G2',
    _min(1.0, '%', 'BG-G2', 'range of elongation minima', hi=3.0),
    _min(4.0, '%', 'BG-G2', '8A21'), topic='elongation')
TEMPER_NAMING = _s(
    'Temper as written: H18 in GB/T 33143, T/ZZB 2638 and JIS H 4160; "H18, H19" in T/ZZB 1203, '
    'Gränges, Symetal and Armor; "H19" at Innoval. "H18" on battery foil is a label for a '
    'strength table: the foil gets 97–99 % cold reduction after the last anneal, far above the '
    'about 75 % that defines H18, so European sources call the same product H19. Both labels '
    'are consistent with collector foil.',
    'BG-G2 BG-G3 BG-G25 BG-G4 BG-G14 BG-G15 BG-G18 BG-G17 BG-G40', topic='temper_naming')
COLLECTOR_TEMPERS = ('H18', 'H19')
SURFACE_SINGLE = _s('Single-sheet two-side-bright foil is preferred.', 'BG-G17',
                    topic='surface')
SURFACE_SAMA = _s('Sam-A rolls single-sheet down to 10 µm and says Japanese mills double at '
                  '10 µm.', 'BG-G11', topic='surface')
SURFACE_8021 = _s('UACJ sells 10 µm 8021 as bright/matte (one-side-bright).', 'BF-S4',
                  topic='surface')

_T15 = 'BG-G5 BG-G6 BG-G8 BG-G9'
TYP_LE10 = _st(('1100-type', '1C30-type'), 'not stated', '≤10 µm, Chinese patents', 'BG-G21',
               rm=('span', 240, 285), a=('span', 2.5, 3.8), grade='high_strength',
               note='band-level values from Chinese patents; not tied to one alloy')
TYP_1060_12 = _st(('1060-type',), 'H18/H19', '>10–13 µm band, Gränges datasheet', 'BG-G14',
                  rm=('span', 180, 230), a=('min', 3), grade='standard', note='A >3 %')
TYP_1100_12A = _st(('1100-type',), 'H18/H19', '>10–13 µm band, Gränges datasheet', 'BG-G14',
                   rm=('span', 230, 270), a=('min', 2.5), grade='high_strength', note='A >2.5 %')
TYP_1100_12B = _st(('1100-type',), 'H18/H19', '>10–13 µm band, Gränges datasheet, stronger '
                   'grade', 'BG-G14', rm=('span', 260, 310), a=('min', 1.5),
                   grade='high_strength', note='A >1.5 %')
TYP_SPEIRA_HS = _st(('Speira high-strength',), 'not stated', 'Speira high-strength grade',
                    'BF-S8', rm=('min', 250), grade='high_strength')
TYP_1085_15 = _st(('1085',), 'not stated', '15 µm, producers', _T15, rm=('span', 175, 180),
                  rp=('span', 163, 165), a=('span', 4, 5), grade='standard')
TYP_1N30_15 = _st(('1N30', '1230'), 'not stated', '15 µm, producers', _T15,
                  rm=('span', 185, 194), rp=('span', 165, 175), a=('typ', 4.5),
                  grade='standard', note='1N30 or 1230')
TYP_1C32_15 = _st(('1C32',), 'not stated', '15 µm, producers', _T15, rm=('typ', 230),
                  rp=('typ', 200), a=('typ', 4.5), grade='high_strength')
TYP_A730H_15 = _st(('A730H',), 'not stated', '15 µm, producers', _T15, rm=('typ', 290),
                   rp=('typ', 250), a=('typ', 4.0), grade='high_strength')
TYP_3003_15 = _st(('3003',), 'not stated', '15 µm, producers', _T15, rm=('span', 270, 275),
                  rp=('typ', 240), a=('typ', 3), grade='high_strength')
TYP_KS81_15 = _st(('KS81',), 'not stated', '15 µm, producers', _T15, rm=('typ', 274),
                  a=('typ', 5.4), grade='high_strength', note='proof strength not given')
TYP_1235_16 = _st(('1235',), 'not stated', '16 µm, lab-supply page', 'BG-G42',
                  rm=('span', 200, 220), a=('typ', 2.2), grade='standard')
TYP_1235_21_35 = _st(('1235',), 'H18', '21–35 µm, vendor', 'BG-G35', rm=('span', 170, 200),
                     a=('min', 1.6), grade='standard')

_NO_GB = 'GB/T 33143-2022 sets no minimum for this alloy in this band'
_NOT_GB = 'not a GB/T 33143-2022 alloy'


def _o(alloy, grade, gb=None, typical=(), usual=None, surface=None, names=(), note='',
       tempers=COLLECTOR_TEMPERS, gauge=None):
    basis = (('BG-G2',) if note.startswith(_NO_GB) else
             ('BF-S1',) if note.startswith(_NOT_GB) else ())
    return GradeOption(alloy, grade, tuple(tempers), None if gb is None else _gb(gb),
                       tuple(typical), usual, surface, gauge, tuple(names), note, basis)


# ---- ≤10 µm
_U_LE10 = _s('1100-type or 1C30-type is the usual choice at ≤10 µm (energy-dense EV and '
             'consumer cells).', 'BG-G21', topic='usual_choice')
_U_8021 = _s('8021 at 10 µm for one-side-bright foil (UACJ bright/matte).', 'BF-S4',
             topic='usual_choice')
BAND_LE10 = GaugeBand(
    'le10', '≤10 µm', 8e-6, 10e-6, True, '8, 9, 10',
    options=(
        _o('1100', 'high_strength', 230, (TYP_LE10,), _U_LE10),
        _o('1C30', 'high_strength', 220, (TYP_LE10,), _U_LE10),
        _o('8021', 'standard', None, (), _U_8021, 'one_side_bright',
           note=_NOT_GB + '; usual only for one-side-bright foil'),
        _o('1070', 'standard', 185),
        _o('8011', 'standard', 180),
        _o('1060', 'standard', note=_NO_GB),
        _o('1050', 'standard', note=_NO_GB),
        _o('1235', 'standard', note=_NO_GB),
    ),
    usual_choice=_s('1100-type or 1C30-type; 8021 at 10 µm one-side-bright.', 'BG-G21 BF-S4'),
    typical_producer=_s('240–285 MPa, 2.5–3.8 % in Chinese patents.', 'BG-G21', TYP_LE10.rm_pa),
    typical_cells=_s('Energy-dense EV, consumer.', 'BG-G21'),
    evidence=_s('Minima strong; alloy preference medium.', 'BG-G2 BG-G21 BF-S4'),
    minima_evidence='strong', choice_evidence='medium', elongation=GB_ELONGATION,
    surface=(SURFACE_SINGLE, SURFACE_SAMA, SURFACE_8021),
    pinholes=_s('T/ZZB 2638: ≤20 pinholes per m² at 8–10 µm.', 'BG-G3',
                _max(20, 'per_m2', 'BG-G3')),
    notes=(_s('The ≤10 µm band first appeared in GB/T 33143-2022.', 'BG-G21'),))

# ---- >10–13 µm
_U_EV = _s('1100-type for EV cells (high strength).', 'BG-G21 BG-G23', topic='usual_choice')
_U_STD12 = _s('1235 or 1060 where 180–190 MPa suffices.', 'BG-G21 BG-G23',
              topic='usual_choice')
_CORR_8011 = ('CORRECTED: the first survey grouped 8011 with the GB/T 33143 high-strength minima '
              '(about ≥220–230 MPa) [BF-S2]; the second survey reads 180 MPa [BG-G2]')
BAND_10_13 = GaugeBand(
    '10_13', '>10–13 µm', 10e-6, 13e-6, False, '12, 13',
    options=(
        _o('1100', 'high_strength', 230, (TYP_1100_12A, TYP_1100_12B), _U_EV),
        _o('1235', 'standard', 180, (), _U_STD12),
        _o('1060', 'standard', 190, (TYP_1060_12,), _U_STD12),
        _o('1C30', 'high_strength', 230),
        _o('Speira high-strength', 'high_strength', None, (TYP_SPEIRA_HS,),
           note='Speira own composition (99.35–99.5 % Al, Cu 0.03–0.08 %)'),
        _o('1050', 'standard', 190),
        _o('1070', 'standard', 185),
        _o('8011', 'standard', 180, note=_CORR_8011),
    ),
    usual_choice=_s('1100-type for EV; 1235 or 1060 where 180–190 MPa suffices.',
                    'BG-G21 BG-G23'),
    typical_producer=_s('1060-type 180–230 MPa, A >3 %; 1100-type 230–270 MPa, A >2.5 %, or '
                        '260–310 MPa, A >1.5 % [BG-G14]; Speira high-strength ≥250 MPa '
                        '[BF-S8].', 'BG-G14 BF-S8'),
    typical_cells=_s('Mainstream EV and storage.', 'BG-G21 BG-G23'),
    evidence=_s('Minima strong; cell type medium.', 'BG-G2 BG-G21 BG-G23'),
    minima_evidence='strong', choice_evidence='medium', elongation=GB_ELONGATION,
    surface=(SURFACE_SINGLE,),
    pinholes=_s('T/ZZB 2638: ≤10 pinholes per m² at 10–13 µm.', 'BG-G3',
                _max(10, 'per_m2', 'BG-G3')))

# ---- >13–15 µm
_U_STD15 = _s('1235, 1060 or 1N30 as standard.', _T15, topic='usual_choice')
_U_1085 = _s('1085 for high-power cells.', _T15 + ' BG-G7', topic='usual_choice')
_U_HS15 = _s('1100-type or 3003 when ≥250 MPa is specified.', _T15, topic='usual_choice')
BAND_13_15 = GaugeBand(
    '13_15', '>13–15 µm', 13e-6, 15e-6, False, '15',
    options=(
        _o('1235', 'standard', 185, (), _U_STD15),
        _o('1060', 'standard', 190, (), _U_STD15),
        _o('1N30', 'standard', None, (TYP_1N30_15,), _U_STD15, names=('1230',),
           note=_NOT_GB + '; 1N30 is a JIS alloy'),
        _o('1085', 'standard', None, (TYP_1085_15,), _U_1085, note=_NOT_GB),
        _o('1100', 'high_strength', 220, (), _U_HS15),
        _o('3003', 'high_strength', None, (TYP_3003_15,), _U_HS15, note=_NOT_GB),
        _o('1C30', 'high_strength', 225),
        _o('1C32', 'high_strength', None, (TYP_1C32_15,), names=('UACJ 1C32',),
           note='UACJ high-strength grade, 1N30 chemistry'),
        _o('A730H', 'high_strength', None, (TYP_A730H_15,), names=('UACJ A730H',),
           note='UACJ high-strength grade, 1100 base'),
        _o('KS81', 'high_strength', None, (TYP_KS81_15,), note='producer grade'),
        _o('1050', 'standard', 190),
        _o('1070', 'standard', 180),
        _o('8011', 'standard', 180, note=_CORR_8011),
        _o('8A21', 'standard', 165),
    ),
    usual_choice=_s('1235, 1060, 1N30 standard; 1085 for high power; 1100-type or 3003 when '
                    '≥250 MPa is specified.', _T15),
    typical_producer=_s('At 15 µm: 1085 175–180 / 163–165 MPa / 4–5 %; 1N30 or 1230 185–194 / '
                        '165–175 / 4.5 %; 1C32 230 / 200 / 4.5 %; A730H 290 / 250 / 4.0 %; 3003 '
                        '270–275 / 240 / 3 %; KS81 274 / — / 5.4 % (Rm / Rp0.2 / A).', _T15),
    typical_cells=_s('EV, storage, consumer.', _T15),
    evidence=_s('Strong: several producers agree.', 'BG-G2 ' + _T15),
    minima_evidence='strong', choice_evidence='strong', elongation=GB_ELONGATION,
    surface=(SURFACE_SINGLE,),
    pinholes=_s('T/ZZB 2638: ≤5 pinholes per m² at 13–15 µm.', 'BG-G3',
                _max(5, 'per_m2', 'BG-G3')))

# ---- >15–20 µm
_U_STD20 = _s('1235, 1060, 1070 or 1085.', 'BG-G42 BG-G19', topic='usual_choice')
BAND_15_20 = GaugeBand(
    '15_20', '>15–20 µm', 15e-6, 20e-6, False, '16, 18, 20',
    options=(
        _o('1235', 'standard', 175, (TYP_1235_16,), _U_STD20),
        _o('1060', 'standard', 185, (), _U_STD20),
        _o('1070', 'standard', 175, (), _U_STD20),
        _o('1085', 'standard', None, (), _U_STD20, note=_NOT_GB),
        _o('1050', 'standard', 185),
        _o('1100', 'high_strength', 220),
        _o('1C30', 'high_strength', 220),
        _o('8011', 'standard', note=_NO_GB),
    ),
    usual_choice=_s('1235, 1060, 1070, 1085 (same grades as at 15 µm).', 'BG-G42 BG-G19'),
    typical_producer=_s('Same grades; 16 µm 1235 typically 200–220 MPa, A 2.2 %.', 'BG-G42',
                        TYP_1235_16.rm_pa),
    typical_cells=_s('Storage, LFP [BG-G19]; carbon-coated base, 16 µm most ordered [BG-G38].',
                     'BG-G19 BG-G38'),
    evidence=_s('Minima strong; cell type vendor-level.', 'BG-G2 BG-G19 BG-G38'),
    minima_evidence='strong', choice_evidence='vendor_level', elongation=GB_ELONGATION,
    surface=(SURFACE_SINGLE,),
    pinholes=_s('T/ZZB 2638: no pinholes (0 per m²) at 15–20 µm.', 'BG-G3',
                _max(0, 'per_m2', 'BG-G3')),
    notes=(_s('The report rates the cell-type column vendor-level and gives no separate rating '
              'for the alloy column; the usual-choice rating is recorded as vendor_level.',
              'BG-G19 BG-G42'),))

# ---- >20–30 µm
_U_STD30 = _s('1235, 1N30 or 1085.', 'BG-G35 BG-G7', topic='usual_choice')
_U_3003_30 = _s('3003 (also listed for >20–30 µm).', 'BG-G35 BG-G7', topic='usual_choice')
_THICK_OPTIONS = (
    _o('1235', 'standard', None, (TYP_1235_21_35,), _U_STD30, note=_NO_GB),
    _o('1N30', 'standard', None, (), _U_STD30, note=_NO_GB),
    _o('1085', 'standard', None, (), _U_STD30, note=_NO_GB),
    _o('3003', 'high_strength', None, (), _U_3003_30, note=_NO_GB),
)
_THICK_USUAL = _s('1235, 1N30, 1085, 3003.', 'BG-G35 BG-G7')
_THICK_TYP = _s('1235-H18 21–35 µm: 170–200 MPa, A ≥1.6 %.', 'BG-G35', TYP_1235_21_35.rm_pa)
_THICK_CELLS = _s('Older and high-power Li-ion ("normally 15–30 µm", 2009); supercapacitors '
                  '20 µm.', 'BG-G7 BG-G36 BG-G37')
_THICK_NOTE = _s('GB/T 33143 stops at 20 µm: no standard minima above it.', 'BG-G2')
BAND_20_30 = GaugeBand(
    '20_30', '>20–30 µm', 20e-6, 30e-6, False, '21–30',
    options=_THICK_OPTIONS, usual_choice=_THICK_USUAL, typical_producer=_THICK_TYP,
    typical_cells=_THICK_CELLS, evidence=_s('Weak.', 'BG-G35 BG-G7'),
    minima_evidence='not_rated', choice_evidence='weak', notes=(_THICK_NOTE,))
COLLECTOR_BANDS = (BAND_LE10, BAND_10_13, BAND_13_15, BAND_15_20, BAND_20_30)

# ---- 25–60 µm products: bands of one span each
BAND_THICK = GaugeBand(
    'thick_20_50', '>20–35 µm (up to 50 µm in one specification)', 20e-6, 50e-6, False,
    '20–35, up to 50', options=_THICK_OPTIONS, usual_choice=_THICK_USUAL,
    typical_producer=_THICK_TYP, typical_cells=_THICK_CELLS,
    evidence=_s('Weak.', 'BG-G24 BG-G35'), minima_evidence='not_rated', choice_evidence='weak',
    notes=(_THICK_NOTE, _s('No standard for thick collector foil was found.', 'BG-G35')))

TYP_CC_BASE = _st(('1070', '1060', '1235'), 'H18', 'carbon-coated base foil, vendor', 'BG-G38',
                  rm=('min', 140, 180), grade='standard')
_U_CC = _s('Alloys stated for carbon-coated base foil: 1070, 1060, 1235 (vendor only).',
           'BG-G38', topic='usual_choice')
BAND_CC = GaugeBand(
    'cc_9_30', '9–30 µm (mostly 12–16 µm)', 9e-6, 30e-6, True, '9–30, mostly 12–16',
    options=tuple(_o(a, 'standard', None, (TYP_CC_BASE,), _U_CC, tempers=('H18',),
                     note='vendor values only') for a in ('1070', '1060', '1235')),
    usual_choice=_U_CC, typical_producer=_s('≥140–180 MPa.', 'BG-G38', TYP_CC_BASE.rm_pa),
    typical_cells=_s('Carbon-coated base, 16 µm most ordered.', 'BG-G38'),
    evidence=_s('Vendor only.', 'BG-G38'), minima_evidence='not_rated',
    choice_evidence='vendor_level')

TYP_TAB = _st(('1070', '1235'), 'O (implied by the values)', 'tab foil, one vendor', 'BG-G34',
              rm=('span', 85, 110), a=('min', 25, 30), grade='standard',
              note='the values imply O temper; the vendor states no temper')
BAND_TAB = GaugeBand(
    'tab_30_100', '30–100 µm', 30e-6, 100e-6, True, '30–100',
    options=(_o('1070', 'standard', None, (TYP_TAB,),
                _s('1070 for consumer cells.', 'BG-G34', topic='usual_choice'),
                tempers=('O',), note='temper implied by the values'),
             _o('1235', 'standard', None, (TYP_TAB,),
                _s('1235 for power cells.', 'BG-G34', topic='usual_choice'),
                tempers=('O',), note='temper implied by the values')),
    usual_choice=_s('1070 (consumer), 1235 (power).', 'BG-G34'),
    typical_producer=_s('85–110 MPa, ≥25–30 %.', 'BG-G34', TYP_TAB.rm_pa),
    typical_cells=_s('Consumer (1070) and power (1235) cells.', 'BG-G34'),
    evidence=_s('Weak: one vendor.', 'BG-G34'), minima_evidence='not_rated',
    choice_evidence='weak',
    notes=(_s('Tab leads are 80–400 µm.', 'BF-S41'),
           _s('No standard for tab foil was found.', 'BG-G34')))

TYP_POUCH_TOYO_8021 = _st(('8021',), 'O', 'Toyo guaranteed minimum', 'BF-S28', rm=('min', 85),
                          a=('min', 9))
TYP_POUCH_TOYO_8079 = _st(('8079',), 'O', 'Toyo guaranteed minimum', 'BF-S28', rm=('min', 75),
                          a=('min', 10))
TYP_POUCH_8021_CN = _st(('8021',), 'O', 'Chinese typical', 'BG-G32', rm=('span', 90, 110),
                        a=('span', 16, 20), note='cupping 7–7.5 mm; high-formability target '
                        '≥20 % and ≥7.5 mm')
TYP_POUCH_VENDOR = _st(('8021', '8079'), 'O', '25–45 µm, vendor', 'BG-G31',
                       rm=('span', 80, 100), a=('min', 12))
_U_POUCH = _s('8021-O is confirmed for pouch foil by Symetal (35–40 µm) and Innoval '
              '(40–50 µm).', 'BG-G15 BG-G17', topic='usual_choice')
BAND_POUCH = GaugeBand(
    'pouch_35_55', '35–55 µm', 35e-6, 55e-6, True, '35, 40, 45, 50, 55',
    options=(
        _o('8021', 'standard', None, (TYP_POUCH_TOYO_8021, TYP_POUCH_8021_CN,
                                      TYP_POUCH_VENDOR), _U_POUCH, tempers=('O',),
           gauge=_r(35, 55, 'um', 'BG-G28', 'GB/T 22648-2023 gauge for 8021')),
        _o('8079', 'standard', None, (TYP_POUCH_TOYO_8079, TYP_POUCH_VENDOR), tempers=('O',),
           gauge=_r(40, 55, 'um', 'BG-G28', 'GB/T 22648-2023 gauge for 8079')),
        _o('8A21', 'standard', None, (), tempers=('O',),
           gauge=_r(40, 50, 'um', 'BG-G28', 'GB/T 22648-2023 gauge for 8A21'),
           note='GB/T 22648-2023 alloy; its property tables were not found'),
    ),
    usual_choice=_U_POUCH,
    typical_producer=_s('Toyo minima 8079 ≥75 MPa / ≥10 %, 8021 ≥85 / ≥9 % [BF-S28]; Chinese '
                        '8021-O 90–110 MPa, 16–20 % [BG-G32]; vendor 25–45 µm 80–100 MPa, ≥12 % '
                        '[BG-G31].', 'BF-S28 BG-G32 BG-G31'),
    typical_cells=_s('Pouch cells: 35 µm in an 88 µm laminate; 40 µm in 113 and 153 µm '
                     'laminates.', 'BG-G30'),
    evidence=_s('Alloy, temper, gauge strong; values medium.', 'BG-G28 BG-G15 BG-G17 BG-G32'),
    minima_evidence='medium', choice_evidence='strong',
    notes=(_s('Rolled hard, then fully annealed; one-side-bright unless ordered otherwise.',
              'BG-G28'),
           _s('T/ZZB 2076-2021 (reseller summary only): ≥70–85 MPa, cupping ≥5.5–7.0 mm.',
              'BG-G29', _min(70, 'MPa', 'BG-G29', 'range of minima', hi=85)),
           _s('A ≥26 µm aluminium layer already gives near-zero water and oxygen transmission; '
              'the extra gauge is for drawing depth.', 'BG-G33')))

# ---- general facts of the second survey
CONDUCTIVITY = (
    _s('1085: 60–61.5 % IACS.', 'BG-G6 BG-G7 BG-G41', _r(60, 61.5, '%IACS', 'BG-G6 BG-G7 BG-G41'),
       topic='1085'),
    _s('1N30: 58–60 % IACS.', 'BG-G6 BG-G7 BG-G41', _r(58, 60, '%IACS', 'BG-G6 BG-G7 BG-G41'),
       topic='1N30'),
    _s('1235: 58–60 % IACS (given together with 1N30).', 'BG-G6 BG-G7 BG-G41',
       _r(58, 60, '%IACS', 'BG-G6 BG-G7 BG-G41'), topic='1235'),
    _s('1100: 56–59.5 % IACS.', 'BG-G6 BG-G7 BG-G41',
       _r(56, 59.5, '%IACS', 'BG-G6 BG-G7 BG-G41'), topic='1100'),
    _s('8021: 58–59 % IACS.', 'BG-G6 BG-G7 BG-G41', _r(58, 59, '%IACS', 'BG-G6 BG-G7 BG-G41'),
       topic='8021'),
    _s('3003: 47–48.5 % IACS.', 'BG-G6 BG-G7 BG-G41',
       _r(47, 48.5, '%IACS', 'BG-G6 BG-G7 BG-G41'), topic='3003'),
    _s('1060: about 62 % IACS on vendor pages; does not line up with the producer figures.',
       'BG-G20', _pt(62, '%IACS', 'BG-G20', 'vendor figure ("about")'), topic='1060'),
)
OTHER_GRADE_DOCUMENTS = (
    _s('T/ZZB 1203-2019, power cells, 10–16 µm: 1060/1070 H18 ≥160, H19 ≥180 MPa; 1100 H18 '
       '≥180, H19 ≥200 MPa; A100 ≥2.0–3.0 %; thickness ±2 %.', 'BG-G4',
       _min(160, 'MPa', 'BG-G4', '1060/1070 H18'), _min(180, 'MPa', 'BG-G4', '1060/1070 H19'),
       _min(180, 'MPa', 'BG-G4', '1100 H18'), _min(200, 'MPa', 'BG-G4', '1100 H19'),
       topic='T/ZZB 1203-2019'),
    _s('JIS H 4160 (1994 text): 1085, 1070, 1050, 1N30, 1100, 3003, 3004, 8021, 8079 in O and '
       'H18; it has no strength table.', 'BG-G25', topic='JIS H 4160'),
    _s('Targray purchase specification, 12–15 µm: 1235-H18 and 1060-H18 ≥165 MPa, ≥1.5 %; '
       '1235D-H18 ≥200 MPa, ≥2.0 %.', 'BG-G24', _min(165, 'MPa', 'BG-G24', '1235-H18, 1060-H18'),
       _min(200, 'MPa', 'BG-G24', '1235D-H18'), topic='Targray'),
)
HEADLINE_FINDINGS = (
    _s('No source gives a hard "gauge X → alloy Y" rule. What exists is a strength floor that '
       'rises as gauge falls; producers meet it by moving from 1085/1070/1060/1235 to Cu-bearing '
       '1100-type or 1C30-type alloys.', 'BG-G2 BG-G6 BG-G11 BG-G21', topic='headline'),
    _s('The first survey\'s 8011 figure was wrong: the GB/T 33143-2022 minimum for 8011 is '
       '180 MPa, not 220–230 MPa.', 'BG-G2 BF-S2', topic='headline'),
    _s('"H18" on battery foil is a label for a strength table. The foil gets 97–99 % cold '
       'reduction after the last anneal, far above the 75 % that defines H18, so European '
       'sources call the same product H19.', 'BG-G40 BG-G8 BG-G26 BG-G14 BG-G17',
       topic='headline'),
)
CORRECTIONS = (
    _s('8011 GB/T 33143-2022 minimum corrected: 180 MPa [BG-G2], not the "about ≥220–230 MPa" '
       'high-strength group the first survey read from the garbled draft translation [BF-S2]. '
       'The first-survey entry is kept for 1C30 and 1100 only; 8011 now carries 180 MPa.',
       'BG-G2 BF-S2', _min(180, 'MPa', 'BG-G2', '8011, corrected'), topic='correction'),
)
GRADE_REASONS = (
    _s('Constant line force: "thinning alone gives insufficient strength per unit width and '
       'foil breaks on the coating line", so strength must rise as gauge falls. One broker '
       'report puts numbers on it: 20 µm ≥170 MPa, 13 µm ≥190 MPa.', 'BG-G6 BG-G22',
       topic='1'),
    _s('The floor keeps rising: 1070 minimum 150 MPa (GB 2016) → 160 (2019 group standard) → '
       '185 (GB 2022); 1100 170 → 180 → 230 (read from a flattened chart). The ≤10 µm band first '
       'appeared in 2022.', 'BG-G21', topic='2'),
    _s('Calendering: higher compaction breaks strip, so buyers raise strength and elongation '
       'together; ≥200 MPa is common, some ask ≥270; a conventional route gives 200–230 MPa at '
       '3.4–3.9 %.', 'BG-G21', topic='3'),
    _s('Conductivity against strength: 3003 costs 11–13 points of IACS, so producers strengthen '
       '1xxx instead. In 2009: 1085 for automotive high-power cells; 1N30 general; 1100, 3003, '
       '8021 for consumer lines run at high productivity.', 'BG-G6 BG-G7', topic='4'),
    _s('Observed shift: Sam-A\'s A1100 (10–17 µm) rose from 4.6 % of sales in 2012 to 73 % in '
       '2020 as demand moved from ≥15 µm to ≤12 µm.', 'BG-G11', topic='5'),
    _s('Strength after drying: drying softens hard foil, purer foil most; one patent requires '
       '≥230 MPa as rolled and ≥210 MPa after drying.', 'BG-G7 BG-G26', topic='6'),
    _s('Rollability and stability: 2xxx, 5xxx, 6xxx and 7xxx are "extremely difficult to roll to '
       'foil"; 1xxx, 3003 and 8021 all passivate in LiPF6. Cu above 0.2 % caused foil-rolling '
       'breaks.', 'BG-G41 BG-G26', topic='7'),
    _s('Sodium-ion: aluminium on both electrodes, 800–900 t/GWh against 350–400 (NMC) and '
       '450–550 (LFP); 12–15 µm conventional, 8–10 µm thin.', 'BG-G21 BG-G39', topic='8'),
)


def _cold(h0_mm, h1_um):
    r = 1 - h1_um * 1e-3 / h0_mm
    return r, math.log(h0_mm / (h1_um * 1e-3))


_C1, _C2 = _cold(0.5, 15), _cold(1.0, 12)
TEMPER_TABLE = (
    TemperRow('H18', _s('Strength of about 75 % cold reduction after a full anneal.', 'BG-G40'),
              _s(f'Last anneal at 0.5–2.5 mm, or none after hot rolling; none in the foil mill. '
                 f'Computed: 0.5 mm → 15 µm is {_C1[0] * 100:.0f} % (strain {_C1[1]:.1f}); '
                 f'1 mm → 12 µm is {_C2[0] * 100:.1f} % (strain {_C2[1]:.1f}).',
                 'BG-G8 BG-G26 BF-S8 BF-S18',
                 Range(_q(_C1[0]), _q(_C1[0]), 'fraction', ('BG-G8', 'BG-G26'),
                       'computed: 0.5 mm → 15 µm', 'typical', 'computed', '%'),
                 Range(_q(_C2[0]), _q(_C2[0]), 'fraction', ('BG-G8', 'BG-G26'),
                       'computed: 1 mm → 12 µm', 'typical', 'computed', '%'))),
    TemperRow('H19', _s('Minimum Rm at least 10 MPa (2 ksi) above H18.', 'BG-G40'),
              _s('Same route, more strain or solute. T/ZZB 1203 puts H19 20 MPa above H18.',
                 'BG-G4')),
    TemperRow('High-strength grades', _s('Sold as H18 or H19.', 'BG-G26 BG-G8'),
              _s('Cu 0.05–0.2 % (1100, 1C30); Fe and Mn held in solution by hot homogenising and '
                 'no intermediate anneal; starting cold rolling at ≥1 mm so strain reaches 4–5 '
                 'instead of about 3, which raised strength and elongation together.',
                 'BG-G26 BG-G8')),
    TemperRow('H2x', _s('Strain hardened, then partially annealed.', 'BG-G40'),
              _s('Not used in any public collector-foil specification.', 'BG-G40')),
    TemperRow('O', _s('Fully annealed.', 'BG-G40'),
              _s('Pouch foil: rolled hard, then coil-annealed at 240–260 °C for 40–45 h; the '
                 'anneal also removes rolling oil.', 'BF-S32 BF-S33 BG-G44')),
)
_HEAT = (('as rolled', None, None), ('100 °C × 24 h', 100, 86400.0),
         ('150 °C × 3 h', 150, 10800.0), ('200 °C × 15 min', 200, 900.0))


def _heat(material, values, note=''):
    steps = []
    for (label, t, d), v in zip(_HEAT, values):
        rng = (_pt(v, 'MPa', 'BG-G26', 'UACJ US 9,698,426 Table 3') if not isinstance(v, tuple)
               else _r(v[0], v[1], 'MPa', 'BG-G26', 'UACJ US 9,698,426 Table 3, span of routes'))
        steps.append(HeatingStep(label, t, d, rng))
    return StrengthAfterHeating(material, tuple(steps), note)


STRENGTH_AFTER_HEATING = (
    _heat('Invention alloy, no intermediate anneal', (252, 258, 261, 227)),
    _heat('Comparison alloy at 59.1 % IACS', (266, 258, 221, 194)),
    _heat('Nine comparison process routes', ((216, 245), (199, 233), (182, 209), (155, 188))),
    StrengthAfterHeating('99.85 % Al grade (specification)', (
        HeatingStep('as rolled', None, None, _min(175, 'MPa', 'BG-G27')),
        HeatingStep('after 100–160 °C (time not given)', (100, 160), None,
                    _min(170, 'MPa', 'BG-G27'))),
        'specified minima, not measurements'),
)
HEATING_NOTE = _s('Strength after heating is from Table 3 of the patent; its composition and '
                  'process tables were not in the excerpt read. These are temperature-dependent '
                  'facts kept as data; no calculation in this package uses them.', 'BG-G26',
                  topic='strength_after_heating')
GAUGES_IN_USE = (
    _s('Sam-A lists 12–20 µm in A1050, A1100, A1235.', 'BG-G10'),
    _s('Lotte: 12 µm in 2020 with 10 µm on test.', 'BG-G12'),
    _s('Korean EV foil 10–11 µm in 2024.', 'BG-G13'),
    _s('China: 12–15 µm mainstream.', 'BG-G21'),
    _s('Single-sheet two-side-bright is preferred; Sam-A rolls single to 10 µm and says '
       'Japanese mills double at 10 µm.', 'BG-G17 BG-G11'),
)
CELL_CASE_STOCK = _s('Case, lid, busbar and cooling plate: ≥0.3 mm, 3003 and 1050; not foil '
                     '(evidence medium).', 'BG-G17', topic='cell_case_stock')
GRADE_DISAGREEMENTS = (
    _s('8011 minimum: 180 MPa [BG-G2] against 220–230 MPa in the first survey [BF-S2].',
       'BG-G2 BF-S2'),
    _s('H18 or H19: Asian standards say H18; European producers say H18/H19 or H19 for the same '
       'product.', 'BG-G2 BG-G3 BG-G25 BG-G4 BG-G14 BG-G15 BG-G17 BG-G18'),
    _s('Group standard below national: T/ZZB 1203-2019 (160–200 MPa) is lower than GB/T '
       '33143-2022 (175–230 MPa), even in its H19 column.', 'BG-G4 BG-G2'),
    _s('1060 strength: GB minimum 185–190 MPa; Gränges 180–230 MPa; a trade article claims '
       '230–250 MPa.', 'BG-G2 BG-G14 BG-G20'),
    _s('"Mainstream" alloy: 1060 and 1235 in Chinese sources; 1100 at Sam-A; 1085, 1N30, 3003 '
       'in Japan.', 'BG-G20 BG-G22 BG-G11 BG-G7'),
    _s('Gauge by cell type: vendor pages put 1070 at 10–12 µm for consumer cells and 1060 at '
       '15–20 µm for storage, with no data.', 'BG-G19'),
    _s('Soft collector foil: some reseller pages list O temper; no standard or producer '
       'datasheet supports it, and the second survey treats it as an error.', 'BF-S48 BG-G2'),
    _s('Cu in 1100: one trade article warns of micro-galvanic corrosion; no measurement was '
       'found.', 'BG-G20'),
)
GRADE_NOT_FOUND = (
    _nf('GB/T 22648-2023 Tables 5–9 (pouch-foil strength, cupping, pinholes by gauge); every '
        'mirror drops them. T/ZZB 2076-2021 is known only from a reseller summary.', 'BG-G28 '
        'BG-G29'),
    _nf('An official copy of GB/T 33143-2022 Table 9; the draft translation\'s host was outside '
        'the research session\'s allowed network domains for direct download.'),
    _nf('Any cell-maker purchase specification, and any LFP-against-NMC rule for gauge or '
        'alloy.'),
    _nf('Datasheets with numbers from Lotte, Dong-IL, Dongwon, Novelis, Hydro, Constellium, '
        'Hindalco, Assan, Dingsheng, Nanshan, Wanshun, Yong Jie, Xiashun, Shenhuo; Speira\'s page '
        'gives gauge only (12–20 µm).', 'BG-G16'),
    _nf('JIS H 4160:2006 itself; the mirror carries the 1994 text.', 'BG-G25'),
    _nf('Recrystallisation temperature by alloy for hard foil: Furukawa-Sky plots it but the '
        'values are not extractable; one vendor page says 1235-H18 softens fast above 220 °C.',
        'BG-G7 BG-G43'),
    _nf('Any standard for thick collector foil or tab foil.'),
)

# --------------------------------------------------------------------------- process temperatures
# Third research pass (sources PT-T<n>): temperatures of strip, oil and rolls in foil rolling and
# their effects. Everything here is a literature statement or the report's (or this module's)
# arithmetic; the tool has no roll-wear model and no temperature-to-surface-finish model.
@dataclass(frozen=True)
class TempMapRow:
    """One row of the temperature map: typical range, limit and the reason given."""
    name: str
    typical: Statement
    limit: Statement | None
    reason: Statement

    def validate(self):
        _text('TempMapRow.name', self.name)
        for s in (self.typical, self.limit, self.reason):
            if s is not None:
                s.validate()
        return self

    def to_dict(self):
        return {'name': self.name, 'typical': _json(self.typical), 'limit': _json(self.limit),
                'reason': _json(self.reason)}


@dataclass(frozen=True)
class ThermalDefect:
    """A defect or property with its thermal cause and the magnitude the literature gives."""
    name: str
    thermal_cause: str
    magnitude: str
    sources: tuple
    read_status: str | None = None

    def validate(self):
        for k in ('name', 'thermal_cause', 'magnitude'):
            _text(f'ThermalDefect.{k}', getattr(self, k))
        _check_status(f'ThermalDefect {self.name!r}', self.sources, self.read_status)
        return self

    def to_dict(self):
        return {'name': self.name, 'thermal_cause': self.thermal_cause,
                'magnitude': self.magnitude, 'sources': list(self.sources),
                'read_status': _effective(self.sources, self.read_status)}


PT_NOT_A_MODEL = ('Literature statements, not model outputs: the tool has no roll-wear model and '
                  'no model linking temperature to surface finish or wettability.')

# ---- named values used by check_thermal
COIL_IN_FINAL_LIMIT = _max(75, 'C', 'PT-T1', 'battery foil: coil entering the final pass, after '
                           '≥10 h natural cooling')
COIL_OUT_FINAL_LIMIT = _max(80, 'C', 'PT-T1 PT-T2', 'battery foil: coil off the final pass, '
                            'also when slit within 30 min')
COIL_OUT_FINAL_LIMIT_LOOSE = _max(90, 'C', 'PT-T1 PT-T2', 'battery foil: "≤90 °C at the least"; '
                                  'elongation decays with time above it')
COIL_OUT_SHEET_TROUBLE = _min(150, 'C', 'PT-T3', 'sheet gauge: trouble above 150–160 °C (8150 '
                              'fin stock lost over 10 % Erichsen above 160 °C)', hi=160)
COIL_OUT_SHEET_TYPICAL = _pt(121, 'C', 'PT-T14', 'coil leaving a cold-mill pass, "about 121 °C"')
COLD_ROLLING_DEF = _max(129, 'C', 'PT-T13', 'cold rolling defined as below 129 °C (regulatory '
                        'definition)')
STRIP_IN_BITE = _pt(200, 'C', 'PT-T4', 'calculated, high speed ("almost adiabatic" above about '
                    '2000 m/min roll speed)')
OIL_ROUGHING = _r(30, 40, 'C', 'PT-T5 PT-T6', 'oil supply, roughing')
OIL_INTERMEDIATE = _r(40, 50, 'C', 'PT-T5 PT-T6', 'oil supply, intermediate')
OIL_FINISHING = _r(50, 60, 'C', 'PT-T5', 'oil supply, finishing, general foil')
OIL_FINISHING_BATTERY = _r(40, 45, 'C', 'PT-T1 PT-T6', 'oil supply, finishing, battery foil')
OIL_WINDOW_PLANT = _r(38, 55, 'C', 'PT-T3', 'oil window at one plant; lower bound set by the '
                      '"ladder" tear defect')
OIL_CAP_COLD = _max(68, 'C', 'PT-T13', 'legal cap, cold mill (vapour emissions, one US rule)')
OIL_CAP_FOIL = _max(71, 'C', 'PT-T13', 'legal cap, foil mills (vapour emissions, one US rule)')
HOT_EDGE = _max(120, 'C', 'PT-T21', 'hot edge spray oil, in 25 mm zones')
ROLL_SURFACE_MODEL = _pt(50, 'C', 'PT-T18', 'cold-mill model value with 35 °C oil (not measured)')
THERMAL_LOAD_LIMIT = _r(167, 209, 'kW/m2', 'PT-T4', '40–50 kcal/m²s of roll surface, converted by '
                        'the report', status='computed')
VISC_40C = _r(1.5, 2.0, 'cSt', 'PT-T9 PT-T10 PT-T8', 'rolling-oil viscosity at 40 °C, all values '
              'found (1.50–1.75, 1.8, 2.0, 1.5–2.0)')
_VPK = (1.66 - 2.23) / (2.23 * 15)       # middles of 1.64-1.68 at 40 °C and 2.16-2.3 at 25 °C
VISC_PER_K = Range(_q(_VPK), _q(_VPK), 'fraction', ('PT-T12',), 'computed: (1.66 - 2.23) / '
                   '(2.23 x 15 K), middles of 2.16–2.3 cSt at 25 °C and 1.64–1.68 cSt at 40 °C '
                   '(linear, relative to 25 °C)', 'typical', 'computed', '%')
HEAT_STRIP_SHARE = _r(11, 33, '%', 'PT-T16', 'measured foil-mill heat partition, strip share '
                      '(abstract only; a net balance, not necessarily the split inside the bite)')
HEAT_ROLL_SHARE = _r(67, 89, '%', 'PT-T16', 'measured foil-mill heat partition, roll share '
                     '(abstract only; net balance); the roll share rises with cooling')
SPRAY_ROLL = _r(2.5, 4.3, 'kW/m2K', 'PT-T18', 'kerosene spray on a work roll, SIMULATED (1800 mm '
                'cold mill, 34 nozzles at 52 mm, roll 50 °C), 200–700 kPa')
SPRAY_JET = _r(3.0, 4.0, 'kW/m2K', 'PT-T18', 'jet zone at 500 kPa, simulated')
SPRAY_MODEL_OVERALL = _r(4.65, 5.5, 'kW/m2K', 'PT-T20', 'overall value in a cold-mill model '
                         'example; coolant not named')
OIL_VS_WATER = _r(3, 6, 'ratio', 'PT-T19', 'water spray coefficient over oil at equal impingement '
                  'density (measured on a steel plate)')
SPRAY_PLATE = Range(_q(31e3 / 6), _q(38e3 / 3), 'W/m^2K', ('PT-T19',), 'computed: water about '
                    '31–38 kW/m²K at 5 bar divided by 3–6 (steel plate at 25–250 °C, not a roll)',
                    'span', 'computed', 'kW/m2K')
THERMAL_CROWN_MAX = _max(30, 'um', 'PT-T25', 'foil mill, "from measured values"; 260 × 900 mm '
                         'work roll; whether on diameter or radius is not stated')
ZONE_AUTHORITY = _r(3.6, 4.2, 'um', 'PT-T18', '± on diameter 20 revolutions after a zone change '
                    '(simulated, 1100 alloy); grows linearly with rolled length, halves from 100 to '
                    '300 m/min')
CONTACT_MODELS = _r(25, 40, 'kW/m2K', 'PT-T34', 'bite contact conductance used in aluminium models')
CONTACT_MEASURED = _r(7, 800, 'kW/m2K', 'PT-T34', 'measured bite contact conductances (review)')
_DIFF = 1.2e-5
_LAM = 0.104
AXIAL_TAU = Range(_q(_LAM ** 2 / (4 * math.pi ** 2 * _DIFF)), _q(_LAM ** 2 / (4 * math.pi ** 2
                  * _DIFF)), 's', ('PT-T18',), 'computed: wavelength² / (4 π² × diffusivity) for '
                  'a 52 mm stripe (104 mm wavelength; 52 mm zone pitch of PT-T18), steel '
                  'diffusivity 1.2e-5 m²/s as stated by the report (the report: "about 20 s")',
                  'typical', 'computed', 's')
RADIAL_TAU = _r(4, 7, 'min', 'PT-T25', 'computed by the report for a 260 mm roll: steel '
                'diffusivity 1.2e-5 m²/s, Biot number 3–9', status='computed')
FREE_EXPANSION = _pt(3.0, 'um/K', 'PT-T25', 'computed by the report: µm on diameter per K for a '
                     '260 mm roll (its expansion coefficient is not stated)', status='computed')
PLASTIC_HEATING = (_pt(41, 'K', 'PT-T1', 'computed by the report: plastic work alone, 200 MPa, '
                       'plane strain, 20→13 µm, no heat leaving', status='computed'),
                   _pt(48, 'K', 'PT-T1', 'computed by the report: same for 50→30 or 30→18 µm',
                       status='computed'))

PT_HEADLINE = (
    _s('Battery foil has a published coil-temperature limit: ≤80 °C on the final pass (≤75 °C '
       'coil entering it, after ≥10 h cooling); above 90 °C elongation decays with time for '
       'weeks.', 'PT-T1 PT-T2', COIL_OUT_FINAL_LIMIT, COIL_IN_FINAL_LIMIT, topic='headline'),
    _s('The only measured heat partition for a foil mill gives 67–89 % of the heat to the rolls '
       'and 11–33 % to the strip (abstract only; a net balance, not necessarily the split inside '
       'the bite).', 'PT-T16', HEAT_ROLL_SHARE, HEAT_STRIP_SHARE, topic='headline'),
    _s('No measured spray coefficient for kerosene on a rotating work roll was found; the nearest '
       'are a simulated 2.5–4.3 kW/m²K on an aluminium cold mill and "3–6 times below water" on '
       'a sprayed plate (about 5–13 kW/m²K, computed).', 'PT-T18 PT-T19', SPRAY_ROLL, SPRAY_PLATE,
       topic='headline'),
    _s('No source quantifies a blocked-nozzle band on foil; the mechanism is documented in words '
       'only (under-cooled roll bands between spray footprints, blocked filter or header, a '
       'turned-down spray whose narrow roll expansion grows until a wave appears, quarter-barrel '
       'looseness from a hotter roll at 1/5–1/4 of the barrel).', 'PT-T22 PT-T23 PK-S7 PT-T38',
       topic='headline'),
)
TEMPERATURE_MAP = (
    TempMapRow('Coil entering a pass',
               _s('Not stated for foil; 60–100 °C entry gave exit above 150 °C at sheet gauge.',
                  'PT-T3', _r(60, 100, 'C', 'PT-T3', 'sheet gauge entry'), topic='typical'),
               _s('≤75 °C before the battery-foil final pass (≥10 h natural cooling).', 'PT-T1',
                  COIL_IN_FINAL_LIMIT, topic='limit'),
               _s('Keeps the final-pass coil below 80 °C.', 'PT-T1', topic='reason')),
    TempMapRow('Strip inside the bite',
               _s('Calculated to reach about 200 °C at high speed.', 'PT-T4', STRIP_IN_BITE,
                  topic='typical'),
               _s('Above 200 °C needed before softening shows.', 'PT-T4', topic='limit'),
               _s('"Almost adiabatic" above about 2000 m/min roll speed.', 'PT-T4',
                  topic='reason')),
    TempMapRow('Coil off the final pass, battery foil (20→13 µm, 35 %, oil 42 °C)',
               _s('77.2 °C at 550 m/min; 97.9 and 99.7 °C at 600 m/min; prior art "above 90 °C".',
                  'PT-T1 PT-T2', _pt(77.2, 'C', 'PT-T1', '550 m/min'),
                  _r(97.9, 99.7, 'C', 'PT-T1', '600 m/min'), topic='typical'),
               _s('≤80 °C (≤90 °C at the least), also when slit within 30 min.', 'PT-T1 PT-T2',
                  COIL_OUT_FINAL_LIMIT, COIL_OUT_FINAL_LIMIT_LOOSE, topic='limit'),
               _s('Recovery and possible solute clustering: strength and elongation fall for '
                  'weeks.', 'PT-T1 PT-T2', topic='reason')),
    TempMapRow('Coil leaving a cold-mill pass (sheet gauge)',
               _s('"About 121 °C"; cold rolling defined as below 129 °C; metal at 20–200 °C.',
                  'PT-T14 PT-T13 PT-T37', COIL_OUT_SHEET_TYPICAL, COLD_ROLLING_DEF,
                  topic='typical'),
               _s('No stated limit; trouble above 150–160 °C.', 'PT-T3', COIL_OUT_SHEET_TROUBLE,
                  topic='limit'),
               _s('Erichsen value of 8150 fin stock fell over 10 % above 160 °C; coarse grains '
                  'after anneal.', 'PT-T3', topic='reason')),
    TempMapRow('Oil supply, roughing and intermediate',
               _s('30–40 °C and 40–50 °C.', 'PT-T5 PT-T6', OIL_ROUGHING, OIL_INTERMEDIATE,
                  topic='typical'), None,
               _s('Thick stock, more heat to remove.', 'PT-T5 PT-T6', topic='reason')),
    TempMapRow('Oil supply, finishing',
               _s('50–60 °C general foil; 40–45 °C battery foil.', 'PT-T5 PT-T1 PT-T6',
                  OIL_FINISHING, OIL_FINISHING_BATTERY, topic='typical'),
               _s('Window 38–55 °C at one plant; legal cap 68 °C (cold mill), 71 °C (foil mills) '
                  'in one US rule.', 'PT-T3 PT-T13', OIL_WINDOW_PLANT, OIL_CAP_COLD, OIL_CAP_FOIL,
                  topic='limit'),
               _s('Thin film for lustre; lower bound set by the "ladder" tear defect; the cap is '
                  'for vapour emissions.', 'PT-T5 PT-T3 PT-T13', topic='reason')),
    TempMapRow('Hot edge spray',
               _s('Oil up to 120 °C in 25 mm zones.', 'PT-T21 PT-T5', HOT_EDGE, topic='typical'),
               None,
               _s('Expands the roll at the strip edge against tight edges and breaks.',
                  'PT-T21 PT-T5', topic='reason')),
    TempMapRow('Work-roll surface and bulk',
               _s('Not found measured; a cold-mill model uses 50 °C surface with 35 °C oil.',
                  'PT-T18', ROLL_SURFACE_MODEL, topic='typical'),
               _s('Thermal load 40–50 kcal/m²s of roll surface (167–209 kW/m², computed by the '
                  'report).', 'PT-T4', THERMAL_LOAD_LIMIT, topic='limit'),
               _s('Above it the thermal balance is unstable; herringbone.', 'PT-T4 PT-T18',
                  topic='reason')),
)
PT_RISE_PER_PASS = (
    _s('Coil temperature rises with speed. The one number pair is 77 °C at 550 m/min against '
       '98–100 °C at 600 m/min, but the cooler case also had a pre-cooled coil and finer rolls; '
       'the entry temperature of the hot case is not given.', 'PT-T15 PT-T1'),
    _s('Computed by the report: plastic work alone (200 MPa flow stress, plane strain) heats the '
       'strip 41 K for 20→13 µm and 48 K for 50→30 or 30→18 µm if no heat leaves; friction adds. '
       'A 77 °C coil from a ≤75 °C entry suggests most of that heat left the strip (the report\'s '
       'inference; coil and strip temperature are not the same measurement).', 'PT-T1',
       *PLASTIC_HEATING, status='computed'),
    _s('Cooling between passes: ≥10 h natural cooling; 24 h rest in the Speira patent.',
       'PT-T1 BF-S8'),
)
OIL_PROPERTIES = (
    _s('Viscosity at 40 °C: 1.50–1.75 cSt (Somentor 29); 1.8 and 2.0 (grades 80, 110); 1.5–2.0 '
       '(electronic foil); 1.8–2.0 in use at one plant.', 'PT-T9 PT-T10 PT-T8 PT-T3', VISC_40C,
       topic='viscosity_40c'),
    _s('Flash point: ≥74 °C (Somentor 29); 105–110 °C open cup (grades 80, 110); 80–111 °C for '
       'additive concentrates.', 'PT-T9 PT-T10 PT-T11', _min(74, 'C', 'PT-T9'),
       _r(105, 110, 'C', 'PT-T10'), _r(80, 111, 'C', 'PT-T11'), topic='flash_point'),
    _s('Boiling range: 192–248 °C; 204–240 °C; 210–250 and 240–280 °C.', 'PT-T9 PT-T8 PT-T10',
       topic='boiling_range'),
    _s('Viscosity against temperature: 2.16–2.3 cSt at 25 °C and 1.64–1.68 cSt at 40 °C for a '
       'comparable fluid, about −1.7 % per K (computed).', 'PT-T12', VISC_PER_K,
       topic='viscosity_per_k'),
    _s('Flow: not found for foil mills. A cold-mill example: 3, 6 and 12 L/min per nozzle in three '
       'rows, about 400 L/min per metre per header at 52 mm pitch (computed by the report).',
       'PT-T20', topic='flow'),
)
OIL_WHAT_GOES_WRONG = (
    _s('Oil too hot (thin film): film ruptures, dry contact, light-and-dark marks; more aluminium '
       'fines; herringbone when load and temperature run away.', 'PT-T8 PT-T15 PT-T4 PT-T28',
       topic='too_hot'),
    _s('Oil too cold or viscous (thick film): lower speed, more oil carried out, yellow-brown '
       'stain after anneal; ladder defect below 38 °C (the report\'s reading of "min 38 °C for '
       'ladder").', 'PT-T8 PT-T3', topic='too_cold'),
    _s('Gauge: a thicker film gives thinner foil in closed-gap rolling (speed effect).', 'PT-T4',
       topic='gauge'),
    _s('Fire: the chance rises sharply once strip reaches the flash point; ignition comes from '
       'strip breaks, static, hot bearings and electrics.', 'PT-T15 PT-T14', topic='fire'),
)
PT_MATERIAL = (
    _s('Battery foil 1060 (also 1235, 1100), 13 µm: strength and elongation tracked for days after '
       'rolling at coil temperatures 80–110 °C. Hotter coils lose more; elongation drops at '
       '≥90 °C, by over 20 % at worst. A 98 °C coil decays for over 60 days; ≤80 °C coils settle '
       'in 16–20 days (figures not seen by the report).', 'PT-T1 PT-T2',
       _min(20, '%', 'PT-T1 PT-T2', 'elongation loss at worst ("over 20 %")'),
       _min(60, 'days', 'PT-T1 PT-T2', 'decay time of a 98 °C coil ("over 60 days")'),
       _r(16, 20, 'days', 'PT-T1 PT-T2', 'settling time of ≤80 °C coils'),
       topic='battery_property_decay'),
    _s('1100-H18 tested hot after holding up to 10 000 h: 165 / 150 MPa (tensile / yield) at room '
       'temperature; 145 / 130 at 100 °C; 125 at 150 °C; 40 at 205 °C.', 'PT-T31 PT-T39',
       _pt(165, 'MPa', 'PT-T39', 'tensile, room temperature'),
       _pt(145, 'MPa', 'PT-T31 PT-T39', 'tensile at 100 °C'),
       _pt(125, 'MPa', 'PT-T31 PT-T39', 'tensile at 150 °C'),
       _pt(40, 'MPa', 'PT-T31 PT-T39', 'tensile at 205 °C'), topic='1100_h18_hot'),
    _s('99.5 % Al: flow stress at 200 °C about 35 % below room temperature; hardness after '
       'deforming at 200 °C only 10 % lower.', 'PT-T4', topic='flow_stress_200c'),
    _s('Recovery of 1050 rolled 99.6 %: measured at 140–220 °C from 1 min; activation energy 131 '
       'rising to 186 kJ/mol.', 'PT-T32', _r(131, 186, 'kJ/mol', 'PT-T32'),
       topic='recovery_kinetics'),
    _s('Strain-rate sensitivity of 1050: m about 0.04 at 100 °C and 0.07 at 200 °C (H14, slow '
       'tensile tests); taken as zero for cold deformation.', 'PT-T33 PT-T7',
       topic='strain_rate_sensitivity'),
    _s('8021 pouch foil: controlling coil and oil temperature avoids work softening during foil '
       'rolling.', 'PT-T36', topic='pouch_8021'),
    _s('Additive film: kerosene with 2.2 % fatty acid failed at 150–155 °C in ball-on-disc tests; '
       '0.022 % acid held to 250 °C.', 'PT-T27', _r(150, 155, 'C', 'PT-T27', 'failure, 2.2 % acid'),
       topic='additive_film'),
    _s('Across the width: a transverse strip temperature gradient goes unnoticed while rolling and '
       'changes shape as the coil cools; no source reports strength or thickness bands from this '
       'cause.', 'PT-T23', topic='across_width'),
)
PT_ROLL_WEAR = (
    _s('Roll coating: fresh aluminium sticks to the roll and is re-deposited; the additive limits '
       'this layer. Physically adsorbed films desorb as temperature rises.',
       'PT-T37 PT-T15 PT-T27', topic='roll_coating'),
    _s('Fines: more fines with higher oil temperature, speed, reduction and roll roughness.',
       'PT-T15', topic='fines'),
    _s('Circumferential temperature swing: keeping it small reduces thermal fatigue, surface '
       'degradation and wear (a general cold-mill statement; nothing foil-specific on spalling).',
       'PT-T23', topic='temperature_swing'),
    _s('Bending: edge heating lowers the bending force and therefore work-roll wear.', 'PT-T24',
       topic='bending'),
    _s('Roll hardness: 115–125 HSD rolls held shape on ≥250 MPa foil; 98 HSD rolls drifted after '
       '1–3 h.', 'PT-T29', topic='roll_hardness'),
)
PT_SURFACE = (
    ThermalDefect('Heat stripes (EAFA)', 'Temperature or flatness difference across the width; '
                  'locally overheated roll.', 'None', ('PK-S7',)),
    ThermalDefect('Stripes on strip', 'Gaps between spray footprints leave under-cooled roll '
                  'bands; overlap should be 10–30 %, never above 50 %.', 'Zone pitch 25–100 mm',
                  ('PT-T22', 'PT-T21')),
    ThermalDefect('Surface striping; local buckle', 'Blocked filter or header gives differential '
                  'oil plate-out and cooling; after a spray is turned down the roll first expands '
                  'in a narrow band, which grows until a wave appears.', 'None', ('PT-T23',)),
    ThermalDefect('Rib (quarter) looseness after roughing', 'Roll hotter at 1/5–1/4 of the barrel; '
                  'nozzles of twice the diameter there removed it.', 'None', ('PT-T38',)),
    ThermalDefect('Herringbone', 'Thermal runaway at the film-strength limit.', 'Thermal load above '
                  '167–209 kW/m² (computed by the report)', ('PT-T4', 'PT-T28')),
    ThermalDefect('Wettability (dyne)', 'Set mainly by oil carried out; additive at 3.5 % gave '
                  '29–30 dyn, at 8 % gave 28 dyn; dyne can start above 32 and fall below 30 within '
                  '12–24 h as base oil evaporates.', '1–2 dyn', ('PT-T29', 'PT-T30')),
)
SPRAY_OVERLAP = _s('Spray footprint overlap should be 10–30 %, never above 50 %; zone pitch '
                   '25–100 mm.', 'PT-T22 PT-T21', _r(10, 30, '%', 'PT-T22 PT-T21', 'overlap'),
                   _max(50, '%', 'PT-T22 PT-T21', 'overlap never above'),
                   _r(25, 100, 'mm', 'PT-T22 PT-T21', 'zone pitch'), topic='spray_overlap')
PT_SURFACE_NOTE = _s('No source links oil, roll or strip temperature directly to dyne level, gloss '
                     'bands or white streaks.', 'PT-T29 PT-T30', topic='surface_not_linked')
PT_SIMULATION = (
    _s('Heat partition, foil mill: strip 0.11–0.33, rolls 0.67–0.89; the roll share rises with '
       'cooling. Basis: measured strip surface temperature, three nozzle states. Abstract only; '
       'a net balance.', 'PT-T16', HEAT_STRIP_SHARE, HEAT_ROLL_SHARE, topic='heat_partition'),
    _s('Spray coefficient, kerosene on a work roll: 3.0 rising to 4.0 kW/m²K in the jet zone at '
       '500 kPa; 2.5–4.3 over 200–700 kPa. Simulated (1800 mm cold mill, 34 nozzles at 52 mm, roll '
       '50 °C); viscosity ranks first among spray factors.', 'PT-T18 PT-T17', SPRAY_ROLL,
       SPRAY_JET, topic='spray_coefficient'),
    _s('Oil against water spray: oil 3–6 times lower at equal impingement density (measured on a '
       'steel plate, full-cone nozzle); water about 31–38 kW/m²K at 5 bar, so oil about '
       '5–13 kW/m²K (computed; a plate at 25–250 °C, not a roll).', 'PT-T19', OIL_VS_WATER,
       SPRAY_PLATE, topic='oil_vs_water'),
    _s('Thermal crown, foil mill: 30 µm maximum, "from measured values"; 260 × 900 mm work roll.',
       'PT-T25', THERMAL_CROWN_MAX, topic='thermal_crown'),
    _s('Zone-cooling authority: ±3.6 to ±4.2 µm on diameter 20 revolutions after a change; grows '
       'linearly with rolled length; halves from 100 to 300 m/min (simulated, 1100 alloy).',
       'PT-T18', ZONE_AUTHORITY, topic='zone_authority'),
    _s('Bite contact conductance: 25–40 kW/m²K in aluminium models; measurements span 7–800.',
       'PT-T34', CONTACT_MODELS, CONTACT_MEASURED, topic='contact_conductance'),
    _s(f'Radial time constant of a 260 mm roll about 4–7 min; axial decay of a 52 mm stripe about '
       f'{AXIAL_TAU.low:.0f} s (recomputed here; the report says about 20 s); free expansion '
       '3.0 µm on diameter per K for a 260 mm roll. All computed.', 'PT-T25 PT-T18', RADIAL_TAU,
       AXIAL_TAU, FREE_EXPANSION, topic='time_constants', status='computed'),
)
PT_DISAGREEMENTS = (
    _s('Heat partition: 67–89 % to the rolls from measured strip surface temperature, against '
       '"almost adiabatic" strip heating to about 200 °C inside the bite at high speed. Both can '
       'hold if the strip gives heat back to roll and oil before coiling; gauge and speed of the '
       'measurement are not in the abstract.', 'PT-T16 PT-T4'),
    _s('Finishing oil temperature: 50–60 °C in general foil texts; 40–45 °C for battery foil; '
       '38–55 °C at one plant.', 'PT-T5 PT-T1 PT-T6 PT-T3'),
    _s('Spray coefficient: 2.5–4.3 kW/m²K simulated; 4.65–5.5 overall in a cold-mill model example '
       '(coolant not named); 5–13 back-computed from a plate test.', 'PT-T18 PT-T20 PT-T19'),
    _s('Hot-spray temperature: up to 120 °C is above the flash point of some base oils '
       '(74–110 °C).', 'PT-T21 PT-T9 PT-T10'),
)
PT_NOT_FOUND = (
    _nf('Measured work-roll surface or bulk temperatures on a foil mill.'),
    _nf('A quantified blocked-nozzle case on foil (temperature difference, diameter change, '
        'I-units, band width).'),
    _nf('Plant-identified time constants; Davies et al. describe three but only the abstract was '
        'reachable.', 'PT-T26'),
    _nf('A curve of strip temperature rise against reduction, speed and gauge; micrometres of gauge '
        'per kelvin of oil; oil-film thickness against temperature.'),
    _nf('Oil flow per metre of barrel on a foil mill; roll-change and regrind intervals for '
        'finishing rolls.'),
    _nf('A direct measurement of temperature against dyne, gloss or roll wear; property or '
        'thickness bands traced to a width-wise temperature difference.'),
    _nf('Full texts on hosts outside the research session\'s allowed network domains: the '
        'heat-partition paper, the Collins thesis (measured thermal cambers), the Mansell thesis, '
        'engineeringmechanics.cz, alufoil.org, aluminium-guide.com.'),
    _nf('A published heat partition or spray coefficient for sheet-gauge cold rolling: the survey '
        'has foil-mill data only.'),
)
PT_ALL_STATEMENTS = (PT_HEADLINE + PT_RISE_PER_PASS + OIL_PROPERTIES + OIL_WHAT_GOES_WRONG
                     + PT_MATERIAL + PT_ROLL_WEAR + (SPRAY_OVERLAP, PT_SURFACE_NOTE)
                     + PT_SIMULATION + PT_DISAGREEMENTS)


_BF_WAVE = 'GB/T 33143 wave height at 8 N/mm²'
BATTERY_COLLECTOR = Product(
    id='battery_collector_foil', name='Li-ion cathode current-collector foil',
    family='battery_electronics',
    final_gauge_m=_r(8, 20, 'um', 'BF-S1', 'GB/T 33143-2022 scope; width ≤1600 mm; bare and '
                     'coated'),
    common_gauges=(
        _s('UACJ offers 12, 15 and 20 µm bright/bright and 10 µm 8021 bright/matte.', 'BF-S4'),
        _s('Sam-A 12–20 µm; Dongwon 10, 12, 13.5, 15 and 20 µm.', 'BF-S45 BF-S46'),
        _s('9–10 µm is mature, 8 µm double-bright is in mass production, 7 µm is possible.',
           'BF-S21'),
    ),
    alloys=_items(('1070', '1060', '1050', '1235', '1100', '8011'),
                  'Listed in GB/T 33143-2022, all H18.', 'BF-S1') + (
        _i('1C30', 'GB/T 33143-2022: Al ≥99.3 %, Fe 0.3–0.5 %, Cu 0.05–0.15 %; H18; '
           'high-strength group.', 'BF-S1'),
        _i('8A21', 'GB/T 33143-2022: Fe 1.0–1.6 %; H18.', 'BF-S1'),
    ) + _items(('1085', '1N30', '3003', '8021'), 'Used in Japan (with 1100).', 'BF-S6') + (
        _i('A1100', 'Dominant in Korea.', 'BF-S45 BF-S46'),
        _i('A1050', 'Also used in Korea.', 'BF-S45 BF-S46'),
        _i('A1235', 'Also used in Korea.', 'BF-S45 BF-S46'),
        _i('Speira 99.35–99.5 % Al', 'Speira own compositions: 99.35–99.5 % Al with Cu '
           '0.03–0.08 %.', 'BF-S8'),
        _i('1C32', 'UACJ high-strength grade: 1N30 chemistry, process-optimised.', 'BF-S5'),
        _i('A730H', 'UACJ high-strength grade, 1100 base.', 'BF-S5'),
        _i('1100 (Cu 0.10–0.15 %)', 'Chinese high-strength variant of 1100 (or 8011).',
           'BF-S12 BF-S13'),
        _i('Al-Fe 1.0–1.7 %', 'Japanese high-strength alloy with Fe 1.0–1.7 %.', 'BF-S20'),
    ),
    tempers=(_i('H18', 'Consensus temper; all GB/T 33143 alloys are H18.', 'BF-S1'),
             _i('H19', 'The same product as labelled H18/H19 or H19 by European producers '
                '(T/ZZB 1203 also has an H19 column); see the temper naming note.',
                'BG-G4 BG-G14 BG-G15 BG-G17 BG-G18'),
             _i('O', 'Listed by some vendor pages (disagrees with the H18 consensus; the second '
                'survey treats it as an error).', 'BF-S48')),
    strength=(
        _st('1085', 'H18', '15 µm, UACJ typical', 'BF-S3 BF-S4', rm=('typ', 180),
            a=('typ', 5.0), grade='standard', note='conductivity 60 %IACS'),
        _st('1N30', 'H18', '15 µm, UACJ typical', 'BF-S3 BF-S4', rm=('typ', 185),
            a=('typ', 4.5), grade='standard', note='conductivity 58 %IACS'),
        _st('8021', 'H18', '15 µm, UACJ typical', 'BF-S3 BF-S4', rm=('typ', 190),
            a=('typ', 5.0), grade='standard', note='conductivity 58 %IACS'),
        _st('3003', 'H18', '15 µm, UACJ typical', 'BF-S3 BF-S4', rm=('typ', 270),
            a=('typ', 3.0), grade='standard', note='conductivity 47 %IACS'),
        _st('1070, 1060, 1050, 1235', 'H18', 'GB/T 33143 minima', 'BF-S2', rm=('min', 175, 190),
            a=('min', 1, 3), grade='standard',
            note='table partly garbled in the report\'s read: Rm minima "about ≥175–190 MPa"; '
                 'elongation minima 1–3 % depending on gauge, gauge length and one- or '
                 'two-side-bright'),
        _st('Speira standard grade', 'not stated', '12 µm', 'BF-S9', rm=('min', 165),
            rp=('min', 110), a=('min', 1.0), grade='standard', note='elongation is A100'),
        _st('1050A', 'H18', 'EN 546-2 minimum (EN 546-2 has no battery table)', 'BF-S31',
            rm=('min', 135)),
        _st('1200', 'H18', 'EN 546-2 minimum (EN 546-2 has no battery table)', 'BF-S31',
            rm=('min', 140)),
        _st('8011A', 'H18', 'EN 546-2 minimum (EN 546-2 has no battery table)', 'BF-S31',
            rm=('min', 160)),
        _st('1C30, 1100', 'H18', 'GB/T 33143 high-strength minima', 'BF-S2',
            rm=('min', 220, 230), grade='high_strength',
            note='"about ≥220–230 MPa"; 8011 removed from this group (see the next row)'),
        _st('8011', 'H18', 'GB/T 33143-2022 minimum (corrected)', 'BG-G2 BF-S2',
            rm=('min', 180), grade='standard', note=_CORR_8011),
        _st('1C32', 'not stated', 'UACJ', 'BF-S5', rm=('typ', 230), grade='high_strength'),
        _st('A730H', 'not stated', 'UACJ', 'BF-S5', rm=('typ', 290), a=('typ', 4.0),
            grade='high_strength', note='conductivity 56 %IACS'),
        _st('Speira high-strength', 'not stated', 'Speira high-strength grade', 'BF-S8',
            rm=('min', 250), rp=('min', 200), a=('min', 2), grade='high_strength',
            note='elongation is A100'),
        _st('Speira high-strength', 'not stated', '15 µm example', 'BF-S8', rm=('typ', 281),
            a=('typ', 2.7), grade='high_strength'),
        _st('1100, 8011, 1100 (Cu 0.10–0.15 %)', 'not stated', '12–15 µm, Chinese high-strength',
            'BF-S12 BF-S13', rm=('span', 250, 270), a=('span', 2.5, 4.5), grade='high_strength'),
        _st('Al-Fe 1.0–1.7 %', 'not stated', '12 µm', 'BF-S20', rm=('min', 250), a=('min', 3),
            grade='high_strength'),
        _st('1060', 'not stated', 'vendor claim', 'BF-S48', rm=('span', 230, 250),
            note='fits only the high-strength variants (report disagreement 1)'),
        _st('1100', 'not stated', 'vendor claim', 'BF-S48', rm=('min', 270),
            note='stated as "above 270 MPa"; fits only the high-strength variants'),
    ),
    rolled_mode='either',
    mode_note=_s('Two-side-bright (bright/bright) foil is rolled single-sheet to final gauge; '
                 'the report\'s single-sheet schedules are two-side-bright. Doubled (pack) '
                 'rolling gives one-side-bright foil: UACJ sells 10 µm 8021 as bright/matte and '
                 'the BF-S17 schedules finish with a doubled pass. Single rolling to final gauge '
                 'is feasible for 9–20 µm; below 9 µm high-strength foil is "difficult" single, '
                 'and pack rolling covers 5–20 µm. The Mino battery finishing mill minimum is '
                 '1×12 µm or 2×6 µm.',
                 'BF-S4 BF-S11 BF-S12 BF-S13 BF-S14 BF-S15 BF-S16 BF-S17 BF-S18 BF-S25'),
    single_sheet_gauge_m=_r(9, 20, 'um', 'BF-S18', 'single rolling to final gauge feasible for '
                            '9–20 µm; below 9 µm high-strength foil is "difficult" single'),
    schedules=_BF_SINGLE + _BF_DOUBLED,
    per_pass_reduction=_per_pass_span(_BF_SINGLE + _BF_DOUBLED,
                                      'computed from every published per-pass gauge pair of '
                                      'this product; the report prints 29–64 %'),
    final_pass=_final_pass_from(
        _BF_SINGLE, max_exit_m=20e-6,
        basis='computed from the last pass of the single-sheet schedules ending at ≤20 µm; the '
              'report prints entry 15–32 µm, reduction 29–57 %',
        speed=_r(430, 1200, 'm/min', 'BF-S11 BF-S12 BF-S16',
                 '450 ± 20 m/min [BF-S11]; 600–650 m/min [BF-S16]; 1000–1200 m/min claimed '
                 '[BF-S12]; the sources disagree'),
        doubled_speed=_r(350, 650, 'm/min', 'BF-S17', 'doubled final pass (trade page)'),
        notes=(
            _s('Final pass at 450 ± 20 m/min with coil temperature ≤80 °C, against 97.9 °C at '
               '600 m/min in the comparative example (thermal-softening argument).', 'BF-S11',
               _r(430, 470, 'm/min', 'BF-S11')),
            _s('Final pass 600–650 m/min.', 'BF-S16', _r(600, 650, 'm/min', 'BF-S16')),
            _s('Final pass 1000–1200 m/min claimed.', 'BF-S12', _r(1000, 1200, 'm/min',
                                                                  'BF-S12')),
            _s('Doubled final pass 350–650 m/min.', 'BF-S17', _r(350, 650, 'm/min', 'BF-S17')),
        )),
    pass_speed_m_s=_r(550, 1300, 'm/min', 'BF-S11 BF-S12 BF-S16 BF-S17',
                      'earlier passes: 550–1000 m/min [BF-S11, BF-S16, BF-S17]; 800–1300 m/min '
                      'claimed [BF-S12]'),
    foil_stock=(
        _s('Foil stock 0.22–0.36 mm, H18.', 'BF-S12 BF-S13',
           _r(0.22, 0.36, 'mm', 'BF-S12 BF-S13')),
        _s('1100 foil stock UTS ≥185–197 MPa.', 'BF-S12 BF-S13',
           _min(185, 'MPa', 'BF-S12 BF-S13', 'range of published minima', hi=197)),
    ),
    annealing=(
        _s('Intermediate anneal at 0.7–2.5 mm sheet gauge, with ≥98.5 % cold reduction after '
           'it.', 'BF-S15 BF-S18 BF-S20', _r(0.7, 2.5, 'mm', 'BF-S15 BF-S18 BF-S20'),
           _min(98.5, '%', 'BF-S15 BF-S18 BF-S20', 'cold reduction after the anneal')),
        _s('Or no anneal at all from hot band (Speira).', 'BF-S8'),
        _s('No source anneals inside the foil mill.', 'BF-S8 BF-S15 BF-S18 BF-S20'),
    ),
    route=(
        _s('Speira high-strength route: from 4.5 mm in 9 passes, maximum 60 % per pass, 24 h '
           'rest between passes below 0.105 mm, no anneal.', 'BF-S8',
           _max(60, '%', 'BF-S8', 'maximum reduction per pass')),
        _s('Three to six foil passes are published; BF-S12 says the industry norm is 5–6 passes '
           'from ≤0.24 mm stock.', 'BF-S12'),
        _s('Mill-builder speed maxima 1500–2200 m/min.', 'BF-S24 BF-S26',
           _r(1500, 2200, 'm/min', 'BF-S24 BF-S26')),
    ),
    work_roll_roughness=(
        _s('Roughing work-roll Ra 0.15–0.28 µm.', 'BF-S11 BF-S12 BF-S13 BF-S16',
           _r(0.15, 0.28, 'um', 'BF-S11 BF-S12 BF-S13 BF-S16'), topic='roughing'),
        _s('Intermediate work-roll Ra 0.09–0.17 µm.', 'BF-S11 BF-S12 BF-S13 BF-S16',
           _r(0.09, 0.17, 'um', 'BF-S11 BF-S12 BF-S13 BF-S16'), topic='intermediate'),
        _s('Finishing work-roll Ra 0.07–0.135 µm.', 'BF-S11 BF-S12 BF-S13 BF-S16',
           _r(0.07, 0.135, 'um', 'BF-S11 BF-S12 BF-S13 BF-S16'), topic='finishing'),
    ),
    rolls_and_oil=(
        _s('Work-roll crown 0.035–0.06 mm; backup-roll Ra 0.60–0.65 µm; hardened rolls of '
           '115–125 HSD improved shape stability on ≥250 MPa foil.',
           'BF-S11 BF-S12 BF-S13 BF-S16'),
        _s('Work-roll diameter 200–320 mm (catalogue) and 280 mm (one mill listing).', 'BF-S27',
           _r(200, 320, 'mm', 'BF-S27')),
        _s('Rolling oil: base oil 80#/82# (viscosity about 1.75) or 95# (2.05) with 3–11 % '
           'ester and alcohol additives; oil temperature 38–45 °C, or 50–65 °C in BF-S12. More '
           'additive lowers dyne.', 'BF-S12 BF-S13 BF-S16'),
    ),
    surface=(
        _s('Foil Ra 0.07–0.22 µm both sides, side-to-side difference ≤0.03 µm, residual carbon '
           '<5 mg/m².', 'BF-S9', _r(0.07, 0.22, 'um', 'BF-S9')),
        _s('Measured Ra 0.094 µm on 13 µm 1070-H18.', 'BF-S51'),
    ),
    thickness_tolerance=(
        _s('GB/T 33143: ±5 % ordinary, ±4 % high, ±3 % ultra-high precision.', 'BF-S2',
           _r(3, 5, '%', 'BF-S2', '± on nominal: 3 % ultra-high, 4 % high, 5 % ordinary')),
        _s('A patent targets ±3 %.', 'BF-S12'),
        _s('Some customers now ask ±2 %.', 'BF-S21'),
    ),
    flatness_requirement=(
        _s(_BF_WAVE + ': ≤5 / 3 / 2 mm at 1.0 m roll span and ≤10 / 8 / 4 mm at 1.5–2 m '
           '(ordinary / high / ultra-high precision).', 'BF-S1',
           _r(2, 5, 'mm', 'BF-S1', 'wave height limit at 1.0 m span across classes'),
           _r(4, 10, 'mm', 'BF-S1', 'wave height limit at 1.5–2 m span across classes')),
        _s('Customer practice: sag ≤5–8 mm at 2 m.', 'BF-S12'),
        _s('Customer practice: ≤5 mm across width.', 'BF-S21'),
    ),
    wettability=(
        _s('GB/T 33143: ≥30 mN/m, recommended.', 'BF-S1', _min(30, 'mN/m', 'BF-S1')),
        _s('Customers ≥32 mN/m.', 'BF-S12', _min(32, 'mN/m', 'BF-S12')),
        _s('Mino mill design ≥33 mN/m.', 'BF-S25', _min(33, 'mN/m', 'BF-S25')),
        _s('Speira corona-treated ≥34 mN/m.', 'BF-S10', _min(34, 'mN/m', 'BF-S10')),
        _s('Corona treatment at the slitter adds 1–3 dyn.', 'BF-S12'),
    ),
    pinholes=(
        _s('GB/T 33143 maximum per m² at ≤10 µm: 15 (ultra-high) / 20 (high) / 30 (ordinary).',
           'BF-S2'),
        _s('GB/T 33143 maximum per m² at 10–13 µm: 6 / 10 / 15.', 'BF-S2'),
        _s('GB/T 33143 maximum per m² at 13–15 µm: 3 / 5 / 10.', 'BF-S2'),
        _s('GB/T 33143 maximum per m² at 15–20 µm: 0 / 3 / ordinary grade not captured in the '
           'report\'s read.', 'BF-S2'),
    ),
    other_requirements=(
        _s('GB/T 33143: burr ≤150 / 100 / 50 µm, no splices, on-line pinhole and surface '
           'annexes.', 'BF-S1 BF-S2'),
        _s('Carbon-coated foil: GB/T 33143 coating areal-density class 0.30–2.00 g/m².', 'BF-S1',
           _r(0.30, 2.00, 'g/m2', 'BF-S1'), topic='carbon_coated'),
        _s('Carbon-coated foil vendors: 0.6–2 µm per side on 12–16 µm base, dyne ≥40–64.',
           'BF-S49', topic='carbon_coated'),
    ),
    named_defects=tuple(
        _d(n, 'Not described beyond the name in the report.',
           'Not given; GB/T 33143 forbids "severe" instances, with limit samples agreed.',
           'BF-S1')
        for n in ('Bright lines', 'White streaks', 'Matte-side colour difference', 'Stripes',
                  'Herringbone', 'Ridges')) + (
        _d('Tension lines', 'Longitudinal stripes at 5–20 mm pitch; appear below 15 µm and '
           'worsen as gauge falls.', 'Drivers: tension, roll roughness, roll parallelism, roll '
           'pressure and pass reduction.', 'BF-S21', *TENSION_LINES.values),
    ),
    standards=(
        _i('GB/T 33143-2022', 'Battery foil: 8–20 µm, width ≤1600 mm, bare and coated; alloys '
           'and H18; tolerance classes; flatness; wettability; pinholes; burr; no splices; '
           'streak defects forbidden when severe.', 'BF-S1 BF-S2'),
        _i('EN 546-2', 'No battery table; H18 minima 135 MPa (1050A), 140 MPa (1200), 160 MPa '
           '(8011A).', 'BF-S31'),
        _i('DIN 50154 and EN 546-2', 'Speira tests to these.', 'BF-S8'),
    ),
    key_requirement=_s('Thickness ±3–5 % by precision class, wave height ≤2–5 mm at 1.0 m span, '
                       'wettability ≥30 mN/m, pinhole limits by gauge (GB/T 33143).',
                       'BF-S1 BF-S2'),
    caveats=(
        BATTERY_SCHEDULE_CAVEAT,
        _s('The GB/T 33143 property table was partly garbled in the report\'s read; the '
           'minima are quoted as "about".', 'BF-S2'),
        CORRECTIONS[0],
    ),
    evidence=(_s('Gauge-by-gauge alloy and temper: see the battery grade table (minima strong; '
                 'usual choice medium to strong by band, vendor-level at >15–20 µm, weak above '
                 '20 µm).', 'BG-G2 BG-G21 BG-G19 BG-G35'),),
    disagreements=(
        _s('1xxx strength: EN 546-2 H18 minima are 135–140 MPa, Speira standard ≥165 MPa, '
           'GB/T 175–190 MPa, UACJ typical 180–185 MPa. One vendor page claims 1060 at '
           '230–250 MPa and 1100 above 270 MPa, which fits only the high-strength variants.',
           'BF-S31 BF-S9 BF-S2 BF-S3 BF-S4 BF-S48'),
        _s('Passes and reductions: three to six foil passes; 29–64 % per pass. BF-S12 says the '
           'industry norm is 5–6 passes from ≤0.24 mm stock.',
           'BF-S11 BF-S12 BF-S13 BF-S14 BF-S15 BF-S16'),
        _s('Final single-sheet speed: 450 m/min (thermal-softening argument) versus '
           '1000–1200 m/min claimed.', 'BF-S11 BF-S12'),
        _s('Minimum single-rolled gauge: about 9 µm, 12 µm on the Mino mill, UACJ sells 10 µm '
           'as bright/matte, yet 8 µm double-bright is reported in production.',
           'BF-S18 BF-S25 BF-S4 BF-S21'),
        _s('Rolling mode in BF-S13: the text says "doubled rolling" on the finishing mill while '
           'calling the product two-side-bright.', 'BF-S13'),
        _s('Temper: H18 is the consensus; some vendor pages list O.', 'BF-S1 BF-S48'),
        _s('BF-S17 doubled passes: the report lists them as 24×2→12×2 µm and 28×2→15×2 µm, yet '
           'reads the trade page\'s first-plant row "302→152" as 30×2→15×2 µm; which schedule the '
           '28×2→15×2 µm pass belongs to is not stated. Both readings are carried.', 'BF-S17'),
    ),
    not_found=(
        _nf('Clean copies of GB/T 33143 Tables 4 and 9.'),
        _nf('Any YS/T standard for battery foil.'),
        _nf('EN 546-3 tolerance values and JIS H 4160 content.'),
        _nf('JIS H 4160 lists 1N30, 1085, 1100, 3003, 8021 and 8079 in O and H18 (the '
            'researcher\'s memory only, unverified).', status='memory_unverified'),
        _nf('Work-roll diameters from Achenbach, SMS or Primetals for battery mills.'),
        _nf('A peer-reviewed foil-mill schedule; BF-S52, despite its title, describes a hot '
            'mill.', 'BF-S52'),
        _nf('Datasheets with numbers from Lotte, Novelis, Hydro, Dingsheng or Nanshan.'),
        _nf('chinesestandard.net and ttbz.org.cn were outside the research session\'s allowed '
            'network domains; the standards were read through mirrors instead.'),
    ),
)

# --------------------------------------------------------------------------- other battery
_POUCH_SCHED = (
    _sched('BF-S34 8021 foil passes', _um(240, 125, 64, 30), 'BF-S34', alloy='8021',
           speeds_m_s=None,
           note='from a 6–7 µm 8021 schedule; 350–600 m/min; work-roll Ra 0.12–0.14 µm then '
                '0.07–0.09 µm'),
)
POUCH = Product(
    id='battery_pouch_laminate_foil', name='Battery pouch-laminate barrier foil',
    family='battery_electronics',
    final_gauge_m=_r(35, 55, 'um', 'BF-S29', 'GB/T 22648-2023: 8021 35–55 µm, 8A21 40–50 µm, '
                     '8079 40–55 µm; width 200–1400 mm'),
    common_gauges=(_s('GB/T 22648-2023: 8021 35–55 µm, 8A21 40–50 µm, 8079 40–55 µm, width '
                      '200–1400 mm.', 'BF-S29'),
                   _s('Toyo TY-X2: 8079 at 40 µm, 8021 at 35 µm.', 'BF-S28'),
                   _s('GB/T 22648-2023 gauges by alloy: 8021 35–55, 8A21 40–50, 8079 40–55 µm.',
                      'BG-G28'),
                   _s('Laminates: 35 µm in an 88 µm laminate; 40 µm in 113 and 153 µm '
                      'laminates.', 'BG-G30')),
    alloys=(_i('8021', 'GB/T 22648-2023 alloy; Toyo TY-X2 at 35 µm.', 'BF-S29 BF-S28'),
            _i('8A21', 'GB/T 22648-2023 alloy.', 'BF-S29'),
            _i('8079', 'GB/T 22648-2023 alloy; Toyo TY-X2 at 40 µm.', 'BF-S29 BF-S28'),
            _i('8021', 'Confirmed for pouch foil (O) by Symetal (35–40 µm) and Innoval '
               '(40–50 µm).', 'BG-G15 BG-G17')),
    tempers=(_i('O', 'All GB/T 22648-2023 grades are O temper.', 'BF-S29'),),
    strength=(
        _st('8079', 'O', 'Toyo guaranteed minimum', 'BF-S28', rm=('min', 75), a=('min', 10)),
        _st('8021', 'O', 'Toyo guaranteed minimum', 'BF-S28', rm=('min', 85), a=('min', 9)),
        _st('8021', 'O', 'Chinese typical', 'BF-S32 BF-S33', rm=('span', 90, 110),
            a=('span', 16, 20), note='cupping 7–7.5 mm'),
        _st('8021', 'O', 'Chinese improved', 'BF-S32 BF-S33', rm=('typ', 108), a=('typ', 25),
            note='cupping 8.2 mm'),
        _st('8021B', 'O', 'EN 546-2', 'BF-S31', rm=('span', 70, 110), a=('min', 7, 12),
            note='A ≥7 % at 25–40 µm and ≥12 % at 40–90 µm'),
        _st('8079', 'O', 'EN 546-2', 'BF-S31', rm=('span', 55, 110), a=('min', 4, 8),
            note='A ≥4 % at 25–40 µm and ≥8 % at 40–90 µm'),
        TYP_POUCH_8021_CN,
        _st('8021', 'O', 'high-formability target', 'BG-G32', a=('min', 20),
            note='cupping ≥7.5 mm'),
        TYP_POUCH_VENDOR,
        _st(('pouch foil (alloy not stated)',), 'not stated', 'T/ZZB 2076-2021, reseller summary',
            'BG-G29', rm=('min', 70, 85), note='cupping ≥5.5–7.0 mm'),
    ),
    rolled_mode='either',
    mode_note=_s('Supplied one-side-bright unless two-side-bright is ordered (GB/T 22648).',
                 'BF-S29'),
    schedules=_POUCH_SCHED,
    per_pass_reduction=_per_pass_span(_POUCH_SCHED, 'computed from the BF-S34 foil passes; '
                                      'the report prints 48, 49, 53 %'),
    pass_speed_m_s=_r(350, 600, 'm/min', 'BF-S34', 'from a 6–7 µm 8021 schedule'),
    foil_stock=(_s('Foil stock 0.2–0.3 mm.', 'BF-S32 BF-S33', _r(0.2, 0.3, 'mm',
                                                               'BF-S32 BF-S33')),),
    annealing=(_s('Hot band, intermediate anneal at 0.5–1.0 mm, foil stock 0.2–0.3 mm, final '
                  'anneal 240–260 °C for 40–45 h.', 'BF-S32 BF-S33'),
               _s('Rolled hard, then fully annealed; one-side-bright unless ordered otherwise.',
                  'BG-G28')),
    work_roll_roughness=(
        _s('Work-roll Ra 0.12–0.14 µm on the earlier foil passes.', 'BF-S34',
           _r(0.12, 0.14, 'um', 'BF-S34'), topic='earlier passes'),
        _s('Work-roll Ra 0.07–0.09 µm on the later foil passes.', 'BF-S34',
           _r(0.07, 0.09, 'um', 'BF-S34'), topic='later passes'),
    ),
    thickness_tolerance=(_s('Local thickness ±4 % (GB/T 22648-2023).', 'BF-S29',
                            _pt(4, '%', 'BF-S29', '± on nominal')),),
    wettability=(_s('Wettability class A; contact angle ≤20° (recommended).', 'BF-S29'),),
    other_requirements=(
        _s('GB/T 22648: no splices, bright-side Ra ≤0.100 µm, cupping and bend tests.', 'BF-S29',
           _max(0.100, 'um', 'BF-S29', 'bright-side Ra')),
        _s('A ≥26 µm aluminium layer already gives near-zero water and oxygen transmission; the '
           'extra gauge is for drawing depth.', 'BG-G33'),
    ),
    evidence=(_s('Alloy, temper, gauge strong; values medium.', 'BG-G28 BG-G15 BG-G17 BG-G32'),),
    standards=(_i('GB/T 22648-2023', 'Pouch foil: alloys, gauges, O temper, ±4 %, no splices, '
                  'wettability class A, bright-side Ra, contact angle, cupping and bend tests; '
                  'one-side-bright by default.', 'BF-S29'),
               _i('EN 546-2', 'O-temper ranges for 8021B and 8079 by gauge band.', 'BF-S31')),
    key_requirement=_s('O temper with high elongation (cupping); local thickness ±4 %; '
                       'wettability class A (GB/T 22648-2023).', 'BF-S29'),
    disagreements=(
        _s('Toyo minima (75–85 MPa, 9–10 %) sit well below Chinese typical values; GB/T 22648 '
           'defaults to one-side-bright.', 'BF-S28 BF-S32 BF-S33 BF-S29'),
    ),
    not_found=(
        _nf('Clean copies of GB/T 22648 Tables 5–9.'),
        _nf('One secondary summary gives 8A21 ≥85 MPa / ≥16 % and pinholes ≤30 or ≤20 per m²; '
            'it is self-disclaimed.', 'BF-S30'),
        _nf('A pass schedule for 40 µm pouch foil.'),
        _nf('Group standard T/ZZB 2076-2021 was not read; the second survey found only a '
            'reseller summary (≥70–85 MPa, cupping ≥5.5–7.0 mm).', 'BG-G29'),
    ),
)


THICK_COLLECTOR = Product(
    id='battery_thick_collector_foil', name='Thick battery collector foil',
    family='battery_electronics',
    final_gauge_m=_r(20, 50, 'um', 'BG-G24 BG-G35', '20–35 µm; up to 50 µm in one '
                     'specification'),
    common_gauges=(_s('20–35 µm; up to 50 µm in one specification.', 'BG-G24 BG-G35'),
                   _s('Supercapacitor electrodes use 20 µm.', 'BG-G36 BG-G37')),
    alloys=_items(('1235', '1N30', '1085', '3003'), 'Listed for thick collector foil (weak '
                  'evidence).', 'BG-G35 BG-G7'),
    tempers=(_i('H18', 'Supplied hard.', 'BG-G35'),),
    strength=(TYP_1235_21_35,),
    rolled_mode='not_published',
    key_requirement=_s('Supplied hard (H18): 170–200 MPa, A ≥1.6 % (vendor; weak evidence).',
                       'BG-G35'),
    evidence=(_s('Weak.', 'BG-G24 BG-G35'),),
    not_found=(_nf('Any standard for thick collector foil.'),),
)
CARBON_COATED_BASE = Product(
    id='battery_carbon_coated_base_foil', name='Carbon-coated collector base foil',
    family='battery_electronics',
    final_gauge_m=_r(9, 30, 'um', 'BG-G38', 'mostly 12–16 µm; 16 µm most ordered'),
    common_gauges=(_s('9–30 µm, mostly 12–16 µm; 16 µm is the most ordered.', 'BG-G38'),),
    alloys=_items(('1070', '1060', '1235'), 'Base-foil alloy stated by the vendor.', 'BG-G38'),
    tempers=(_i('H18', 'Base foil supplied hard.', 'BG-G38'),),
    strength=(TYP_CC_BASE,),
    rolled_mode='not_published',
    other_requirements=(
        _s('Carbon-coated foil: GB/T 33143 coating areal-density class 0.30–2.00 g/m².', 'BF-S1',
           _r(0.30, 2.00, 'g/m2', 'BF-S1'), topic='carbon_coated'),
        _s('Carbon-coated foil vendors: 0.6–2 µm per side on 12–16 µm base, dyne ≥40–64.',
           'BF-S49', topic='carbon_coated')),
    key_requirement=_s('Base foil supplied hard (H18), ≥140–180 MPa (vendor only).', 'BG-G38'),
    evidence=(_s('Vendor only.', 'BG-G38'),),
)
TAB_FOIL = Product(
    id='battery_tab_foil', name='Battery tab foil and strip', family='battery_electronics',
    final_gauge_m=_r(30, 100, 'um', 'BG-G34'),
    common_gauges=(_s('Tab foil 30–100 µm.', 'BG-G34'), _s('Tab leads 80–400 µm.', 'BF-S41')),
    alloys=(_i('1070', 'Consumer cells.', 'BG-G34'), _i('1235', 'Power cells.', 'BG-G34')),
    tempers=(_i('O', 'Implied by the values (85–110 MPa, ≥25–30 %); annealed after rolling '
                '(inferred by the report).', 'BG-G34'),),
    strength=(TYP_TAB,),
    rolled_mode='not_published',
    key_requirement=_s('Soft (values imply O): 85–110 MPa, ≥25–30 % (one vendor; weak).',
                       'BG-G34'),
    evidence=(_s('Weak: one vendor.', 'BG-G34'),),
    not_found=(_nf('Any standard for tab foil.'),),
)

CAP_HV = Product(
    id='capacitor_anode_foil_high_voltage', name='Electrolytic capacitor anode foil, high voltage',
    family='battery_electronics',
    final_gauge_m=_r(50, 150, 'um', 'BF-S36 BF-S37', '70–130 µm [BF-S37]; GB/T 3615-2016 '
                     '50–150 µm [BF-S36]'),
    common_gauges=(_s('70–130 µm.', 'BF-S37'), _s('GB/T 3615-2016: 50–150 µm.', 'BF-S36')),
    alloys=(_i('99.99 % Al', 'High-purity aluminium.', 'BF-S37'),) + _items(
        ('1A97', '1A99'), 'GB/T 3615-2016 grades.', 'BF-S36'),
    tempers=(_i('soft', 'Soft temper.', 'BF-S37'),),
    rolled_mode='not_published',
    annealing=(_s('Route: intermediate anneal, light additional rolling, final anneal '
                  '450–550 °C.', 'BF-S38'),),
    other_requirements=(_s('Cube texture ≥90 % at 85–100 µm and ≥95 % at 100–150 µm '
                           '(GB/T 3615-2016).', 'BF-S36',
                           _min(90, '%', 'BF-S36', 'cube texture at 85–100 µm'),
                           _min(95, '%', 'BF-S36', 'cube texture at 100–150 µm')),),
    standards=(_i('GB/T 3615-2016', 'Capacitor foil: 1A97 and 1A99, 50–150 µm, cube texture '
                  'limits.', 'BF-S36'),),
    key_requirement=_s('Cube texture ≥90–95 % (GB/T 3615-2016).', 'BF-S36'),
)
CAP_LV = Product(
    id='capacitor_anode_foil_low_voltage', name='Electrolytic capacitor anode foil, low voltage',
    family='battery_electronics',
    final_gauge_m=_r(60, 110, 'um', 'BF-S37'),
    alloys=(_i('99.9–99.99 % Al', 'High-purity aluminium.', 'BF-S37'),),
    tempers=(_i('soft', 'Soft or hard.', 'BF-S37'), _i('hard', 'Soft or hard.', 'BF-S37')),
    rolled_mode='not_published',
    key_requirement=_s('99.9–99.99 % Al, soft or hard, 60–110 µm.', 'BF-S37'),
    standards=(_i('GB/T 3615-2016', 'Capacitor foil; its low-voltage anode gauge range is '
                  'quoted differently by two summaries.', 'BF-S36'),),
    disagreements=(_s('GB/T 3615 low-voltage anode gauge: 0.015–0.080 mm in one summary, '
                      '0.050–0.150 mm in another.', 'BF-S36'),),
)
CAP_CATHODE = Product(
    id='capacitor_cathode_foil', name='Electrolytic capacitor cathode foil',
    family='battery_electronics',
    final_gauge_m=_r(15, 80, 'um', 'BF-S36 BF-S37', '15–60 µm [BF-S37]; GB/T 3615 15–80 µm '
                     '[BF-S36]'),
    common_gauges=(_s('15–60 µm.', 'BF-S37'), _s('GB/T 3615: 15–80 µm.', 'BF-S36')),
    alloys=(_i('99.4–99.8 % Al', 'Cathode purity range.', 'BF-S37'),
            _i('Cu-bearing alloy', 'Alternative to 99.4–99.8 % Al.', 'BF-S37')) + _items(
        ('1A90', '1070A', '3003'), 'GB/T 3615 grades.', 'BF-S36'),
    tempers=(_i('soft', 'Soft or hard.', 'BF-S37'), _i('hard', 'Soft or hard.', 'BF-S37'),
             _i('O', 'GB/T 3615.', 'BF-S36'), _i('H18', 'GB/T 3615.', 'BF-S36'),
             _i('H22', 'GB/T 3615.', 'BF-S36')),
    rolled_mode='not_published',
    thickness_tolerance=(_s('GB/T 3615: ±5 % up to 50 µm, ±3 % above.', 'BF-S36'),),
    standards=(_i('GB/T 3615-2016', 'Cathode foil grades, tempers, 15–80 µm, tolerance.',
                  'BF-S36'), STD_B373),
    key_requirement=_s('Thickness ±5 % up to 50 µm, ±3 % above (GB/T 3615).', 'BF-S36'),
)

# --------------------------------------------------------------------------- packaging
_ROW_BLISTER = 'PK-S9 PK-S18 PK-S20 PK-S15'
BLISTER = Product(
    id='pharma_blister_lidding', name='Pharma blister lidding foil (push-through)',
    family='packaging_household',
    final_gauge_m=_r(18, 40, 'um', _ROW_BLISTER, 'common nominals 20, 25, 30 µm'),
    common_gauges=(_s('Common nominals 20, 25 and 30 µm (range 18–40 µm).', _ROW_BLISTER),),
    alloys=(_i('8011', 'Hard-temper lidding alloy (Asian vendors: 8011-H18).', _ROW_BLISTER),
            _i('8011A', 'EN designation of the lidding alloy.', _ROW_BLISTER),
            _i('1200', 'Impol lidding alloy (H18).', 'PK-S18'),
            _i('8079', 'Impol lidding alloy (H18).', 'PK-S18'),
            _i('8006', 'Also offered.', _ROW_BLISTER)),
    tempers=(_i('H18', 'Standard temper.', _ROW_BLISTER),
             _i('H19', 'By agreement.', _ROW_BLISTER)),
    strength=(
        _st('8011A', 'H18', 'minimum', 'PK-S9', rm=('min', 160)),
        _st('8079', 'H18', 'minimum', 'PK-S9', rm=('min', 150)),
        _st('1200', 'H18', 'minimum', 'PK-S9', rm=('min', 140)),
    ),
    rolled_mode='doubled',
    mode_note=_s('Doubled (bright/matt).', _ROW_BLISTER),
    annealing=(_s('H18 lidding foil is used as-rolled, without anneal.', 'PK-S1'),),
    thickness_tolerance=(_s('±8 %.', _ROW_BLISTER, _pt(8, '%', _ROW_BLISTER, '± on nominal')),),
    pinholes=(_s('0 per m² at 25–30 µm; ≤10 per m² at 20 µm.', _ROW_BLISTER),
              _s('YBB00152002-2015: no pinholes >0.3 mm; ≤1 per m² at 0.1–0.3 mm.', 'PK-S15')),
    other_requirements=(_s('Burst ≥98 kPa; heat seal ≥7.0 N/15 mm to PVC (YBB00152002-2015).',
                           'PK-S15', _min(98, 'kPa', 'PK-S15', 'burst pressure')),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_YBB, STD_EN546_2, STD_EN546_3),
    key_requirement=_s('Rm ≥160 MPa (8011A), ≥150 (8079), ≥140 (1200); pinholes 0 per m² at '
                       '25–30 µm; burst ≥98 kPa.', 'PK-S9 PK-S20 PK-S15'),
    disagreements=(_s('Blister lidding alloy: 8011-H18 (Asian vendors) versus 1200 / 8079-H18 '
                      '(Impol).', 'PK-S20 PK-S18'),),
    not_found=(_nf('Hard-temper lidding rolling schedules, or pass schedules for 20–60 µm '
                   'pharma gauges.'),),
)

_ROW_COLD = 'PK-S9 PK-S19 PK-S18'
COLD_FORM = Product(
    id='pharma_cold_form_foil', name='Pharma cold-form (alu-alu) base foil',
    family='packaging_household',
    final_gauge_m=_r(45, 60, 'um', _ROW_COLD, 'nominals 45, 50, 60 µm in OPA 25 / Al / PVC 60'),
    common_gauges=(_s('45, 50 and 60 µm, in an OPA 25 / Al / PVC 60 laminate.', _ROW_COLD),),
    alloys=(_i('8021B', 'Main cold-form alloy (also written 8021).', _ROW_COLD),
            _i('8021', 'Same alloy family as 8021B.', _ROW_COLD),
            _i('8079', 'Also offered.', _ROW_COLD), _i('8011', 'Also offered.', _ROW_COLD)),
    tempers=(_i('O', 'Soft temper for cold forming.', _ROW_COLD),),
    strength=(_st('8021B', 'O', '>40–90 µm', 'PK-S9', rm=('span', 75, 110), a=('min', 12)),),
    rolled_mode='not_published',
    mode_note=_s('Listed bright/matt at 45–60 µm (Impol).', 'PK-S18'),
    thickness_tolerance=(_s('45 ±3.6 µm.', _ROW_COLD),),
    wettability=(_s('Wettability A.', _ROW_COLD),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_2,),
    key_requirement=_s('8021B-O >40–90 µm: Rm 75–110 MPa, A ≥12 %.', 'PK-S9'),
)

_ROW_STRIP = 'PK-S20 PK-S22'
STRIP_PACK = Product(
    id='pharma_strip_pack_foil', name='Pharma strip-pack foil', family='packaging_household',
    final_gauge_m=_r(20, 50, 'um', _ROW_STRIP, 'nominals 25, 30, 40 µm, laminated with LDPE '
                     'about 37.5 µm'),
    common_gauges=(_s('25, 30 and 40 µm (20–50 µm) plus LDPE about 37.5 µm.', _ROW_STRIP),),
    alloys=_items(('8011', '1200'), 'Strip-pack alloy.', _ROW_STRIP),
    tempers=(_i('O', 'Soft temper.', _ROW_STRIP),),
    rolled_mode='not_published',
    thickness_tolerance=(_s('±8 %.', _ROW_STRIP, _pt(8, '%', _ROW_STRIP, '± on nominal')),),
    pinholes=(_s('Pinholes nil.', _ROW_STRIP),),
    other_requirements=(_s('Burst minimum 1.5 / 1.9–2.3 / 2.5–2.8 kg/cm² at 25 / 30 / 40 µm.',
                           _ROW_STRIP),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_2, STD_EN546_3),
    key_requirement=_s('±8 %; pinholes nil; burst minimum by gauge.', _ROW_STRIP),
    disagreements=(_s('Strip-foil burst strength: two converters quote different minimums for '
                      'the same gauge.', _ROW_STRIP),),
)

_HH_SCHED = (
    _sched('PK-S2 household 450 µm → 2×10.5 µm', _um(450, 215, 100, 47, 23, 10.5), 'PK-S2',
           doubled_from_index=4, speeds_m_s=_mpm(600, 900, 900, 900, 600)),
)
_ROW_HH = 'PK-S8 PK-S9 PK-S18 PK-S30'
HOUSEHOLD = Product(
    id='household_foil', name='Household foil, standard', family='packaging_household',
    final_gauge_m=_r(10, 16, 'um', _ROW_HH, 'EN "consumer" foil 10–24 µm; budget 9 µm'),
    common_gauges=(_s('10–16 µm; budget 9 µm.', _ROW_HH),
                   _s('EN 546-1 consumer foil 10–24 µm.', 'PK-S8', _r(10, 24, 'um', 'PK-S8'))),
    alloys=(_i('8011', 'Main household alloy.', _ROW_HH),
            _i('8006', 'Impol household alloy.', _ROW_HH),
            _i('1235', 'Also used.', _ROW_HH), _i('8079', 'Also used.', _ROW_HH)),
    tempers=(_i('O', 'Soft temper.', _ROW_HH),),
    strength=(_st('8011A', 'O', '10–25 µm', 'PK-S9', rm=('span', 55, 115), a=('min', 1)),
              _st('8006', 'O', 'household gauges', 'PK-S9', rm=('span', 85, 140),
                  a=('min', 2))),
    rolled_mode='doubled',
    mode_note=_s('Doubled; the final pass is the doubled pass.', _ROW_HH + ' PK-S2'),
    schedules=_HH_SCHED,
    per_pass_reduction=_per_pass_span(_HH_SCHED, 'computed from the PK-S2 household schedule; '
                                      'the report prints 52, 53, 53, 51, 54 %'),
    final_pass=_final_pass_from(_HH_SCHED, basis='computed from the PK-S2 schedule',
                                doubled_speed=_pt(600, 'm/min', 'PK-S2', 'doubled final pass')),
    pass_speed_m_s=_speed_span(_HH_SCHED, 'from the PK-S2 schedule'),
    named_defects=FOIL_DEFECTS,
    standards=FOIL_STANDARDS,
    key_requirement=_s('8011A-O 10–25 µm: Rm 55–115 MPa, A ≥1 %.', 'PK-S9'),
    caveats=(_s('The packaging report gives 8006-O as Rm 85–140 MPa in its summary table and '
                'as "80–140 MPa" in its alloy notes; both are carried.', 'PK-S9'),),
)

_ROW_HD = 'PK-S11 PK-S30'
HOUSEHOLD_HD = Product(
    id='household_foil_heavy_duty', name='Household foil, heavy-duty',
    family='packaging_household',
    final_gauge_m=_r(18, 25, 'um', _ROW_HD, '24 µm typical in the UK'),
    common_gauges=(_s('18–25 µm; 24 µm typical in the UK.', _ROW_HD),),
    alloys=_items(('8011', '8006'), 'Heavy-duty household alloy.', _ROW_HD),
    tempers=(_i('O', 'Soft temper.', _ROW_HD),),
    rolled_mode='doubled', mode_note=_s('Doubled.', _ROW_HD),
    other_requirements=(_s('Burst and stickiness tests apply (EN 546-4).', 'PK-S11'),),
    named_defects=FOIL_DEFECTS,
    standards=FOIL_STANDARDS,
    key_requirement=_s('Burst and stickiness tests (EN 546-4).', 'PK-S11'),
    not_found=(_nf('US heavy-duty household gauge from a producer.'),
               _nf('EN 546-4 burst and stickiness acceptance values.')),
)

_CONV_SCHED = (
    _sched('PK-S2 converter 450 µm → 2×6.5 µm', _um(450, 220, 110, 55, 26, 14, 6.5), 'PK-S2',
           doubled_from_index=5, speeds_m_s=_mpm(700, 1000, 1000, 1000, 1000, 700),
           note='the patent text says "400 µm" and omits 110 µm; its table is as given'),
    _sched('PK-S3 TRC 8079 8 mm → 2×6.35 µm', _um(8000, 4000, 530, 250, 100, 56, 14, 6.35),
           'PK-S3', alloy='8079', doubled_from_index=6, passes_per_step=(None, 4, 1, 1, 1, 2, 1),
           display_unit='auto',
           note='industrial twin-roll cast; homogenise 580 °C / 8 h at 4 mm; anneal 450 °C / 4 h '
                'at 0.53 mm; speeds 175 / 325 / 560 m/min on the three foil mills; work rolls '
                '240 mm; final anneal 270 °C / 11 h; about 10 pinholes/dm² reported'),
    _sched('PK-S16 Alcoa Yennora 1145, 29 µm → 2×6.5 µm', _um(29, 14, 6.5), 'PK-S16',
           alloy='1145', doubled_from_index=1, note='final pass printed "13D" (2×6.5 µm)'),
)
_ROW_CONV = 'PK-S9 PK-S14 PK-S32'
CONVERTER = Product(
    id='converter_foil', name='Converter / flexible-packaging foil', family='packaging_household',
    final_gauge_m=_r(5.5, 9, 'um', _ROW_CONV, 'nominals 6, 6.35, 6.5, 7, 8, 9 µm; down to '
                     '5.5 µm'),
    common_gauges=(_s('6, 6.35, 6.5, 7, 8 and 9 µm; down to 5.5 µm.', _ROW_CONV),),
    alloys=_items(('1235', '1145', '1200', '8079', '8011'), 'Converter-foil alloy.', _ROW_CONV),
    tempers=(_i('O', 'Soft temper.', _ROW_CONV),),
    strength=(_st('8079', 'O', '6–10 µm', 'PK-S9', rm=('span', 45, 100), a=('min', 1)),),
    rolled_mode='doubled', mode_note=_s('Doubled; the final pass is the doubled pass.',
                                        _ROW_CONV + ' PK-S2 PK-S3 PK-S16'),
    schedules=_CONV_SCHED,
    per_pass_reduction=_per_pass_span(_CONV_SCHED, 'computed from the single passes of the '
                                      'PK-S2, PK-S3 and PK-S16 schedules (multi-pass blocks '
                                      'excluded)'),
    final_pass=_final_pass_from(
        _CONV_SCHED, basis='computed from the last (doubled) pass of each schedule',
        doubled_speed=_r(490, 700, 'm/min', 'PK-S2 PK-S16',
                         '700 m/min in the PK-S2 schedule; Alcoa Yennora target 700 m/min, '
                         'actual about 490–600 m/min [PK-S16]')),
    pass_speed_m_s=_r(175, 1000, 'm/min', 'PK-S2 PK-S3', '700–1000 m/min in the PK-S2 schedule; '
                      '175 / 325 / 560 m/min on the three PK-S3 foil mills'),
    route=(
        _s('Alcoa Yennora (1145): tension-speed AGC; loads 360–460 t; exit stress 4.6–5.0 '
           'kg/mm²; target 700 m/min, actual about 490–600 m/min; coolant viscosity 1.9 (unit '
           'not shown), 38–55 °C.', 'PK-S16'),
        _s('Alcoa Yennora chromed work rolls "5–7 Ra" and "14–16 Ra" (unit not shown, probably '
           'µin).', 'PK-S16'),
        _s('Alcoa Yennora final anneal between 235 °C / 90 h and 285 °C / 2 h.', 'PK-S16'),
        _s('PK-S3 TRC 8079: final anneal 270 °C / 11 h; about 10 pinholes/dm² reported.',
           'PK-S3'),
    ),
    pinholes=(
        _s('About 500 per m² at 6 µm, falling to 50–100 per m² at 9 µm (vendor specs).',
           _ROW_CONV),
        _s('GB/T 3198-2020 limits per m², ultra-high / high / ordinary: 500 / 1000 / 1500 at '
           '6.0 µm; 150 / 300 / 500 at 6.5–7 µm; 100 / 150 / 200 at 7–9 µm; 20 / 50 / 100 at '
           '9–12 µm; 0 / 5 / 10 at 20–40 µm.', 'PK-S14', status='vendor_or_trade_page'),
    ),
    wettability=(_s('Wettability A to B.', _ROW_CONV),),
    named_defects=FOIL_DEFECTS,
    standards=FOIL_STANDARDS,
    key_requirement=_s('Pinholes about 500 per m² at 6 µm falling to 50–100 at 9 µm; '
                       'wettability A to B.', _ROW_CONV),
    disagreements=(
        _s('Pinholes at 6 µm: <500–600 per m² in vendor specs versus up to 1500 per m² in the '
           'GB ordinary grade.', 'PK-S32 PK-S14'),
        _s('Twin-roll cast suitability for 6–7 µm: "restricted" versus routine but '
           'pinhole-prone.', 'PK-S5 PK-S3 PK-S31'),
    ),
)

_ROW_CIG = 'PK-S24'
CIGARETTE = Product(
    id='cigarette_liner_foil', name='Cigarette inner-liner foil', family='packaging_household',
    final_gauge_m=_r(6, 7, 'um', _ROW_CIG, 'nominals 6.5 and 7 µm, laminated to paper'),
    common_gauges=(_s('6.5 and 7 µm plus paper.', _ROW_CIG),),
    alloys=_items(('1235', '1145', '8011'), 'Cigarette-liner alloy.', _ROW_CIG),
    tempers=(_i('O', 'Soft temper.', _ROW_CIG),),
    strength=(_st('1235, 1145', 'O', '1xxx', _ROW_CIG, rm=('span', 45, 95)),
              _st('8011', 'O', '8011', _ROW_CIG, rm=('span', 50, 105))),
    rolled_mode='doubled', mode_note=_s('Doubled.', _ROW_CIG),
    pinholes=(_s('≤500 per m² at 6.5–7 µm.', _ROW_CIG, _max(500, 'per_m2', _ROW_CIG)),),
    named_defects=FOIL_DEFECTS,
    standards=FOIL_STANDARDS,
    key_requirement=_s('Rm 45–95 MPa (1xxx), 50–105 MPa (8011); pinholes ≤500 per m².',
                       _ROW_CIG),
)

_ROW_DAIRY = 'PK-S20 PK-S33 PK-S22'
DAIRY = Product(
    id='dairy_lidding_foil', name='Dairy (yoghurt) lidding foil', family='packaging_household',
    final_gauge_m=_r(28, 50, 'um', _ROW_DAIRY, 'nominals 30, 38, 40 µm'),
    common_gauges=(_s('30, 38 and 40 µm (28–50 µm).', _ROW_DAIRY),),
    alloys=(_i('8011', 'Dairy lidding alloy.', _ROW_DAIRY),
            _i('8079', 'Preferred for punched lids.', _ROW_DAIRY),
            _i('1200', 'Dairy lidding alloy.', _ROW_DAIRY)),
    tempers=(_i('O', 'Main temper.', _ROW_DAIRY), _i('semi-hard', 'Also offered.', _ROW_DAIRY)),
    rolled_mode='not_published',
    thickness_tolerance=(_s('±8 %.', _ROW_DAIRY, _pt(8, '%', _ROW_DAIRY, '± on nominal')),),
    other_requirements=(_s('Heat-seal lacquer 6–8 g/m².', _ROW_DAIRY,
                           _r(6, 8, 'g/m2', _ROW_DAIRY)),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_2, STD_EN546_3),
    key_requirement=_s('±8 %; heat-seal lacquer 6–8 g/m².', _ROW_DAIRY),
)

_ROW_WW = 'PK-S17 PK-S9 PK-S8'
CONTAINER_WW = Product(
    id='container_foil_wrinkle_wall', name='Container foil, wrinkle-wall',
    family='packaging_household',
    final_gauge_m=_r(33, 160, 'um', _ROW_WW, 'EN single-rolled container foil 35–200 µm'),
    common_gauges=(_s('33–160 µm.', _ROW_WW),
                   _s('EN 546-1 container foil: single-rolled, 35–200 µm.', 'PK-S8',
                      _r(35, 200, 'um', 'PK-S8'))),
    alloys=(_i('8006', 'Container alloy.', _ROW_WW), _i('3104', 'Container alloy.', _ROW_WW),
            _i('8079', 'Container alloy.', _ROW_WW), _i('8011', 'Also used.', _ROW_WW),
            _i('3003', 'Also used.', _ROW_WW)),
    tempers=_items(('H21', 'H22', 'H24'), 'Container temper.', _ROW_WW),
    strength=(_st('8011A', 'H22', 'EN 546-2 Table 2', 'PK-S9', rm=('span', 90, 150),
                  note='Table 2 partly garbled in the report\'s read; 8011A row cross-checked'),
              _st('8011A', 'H24', 'EN 546-2 Table 2', 'PK-S9', rm=('span', 110, 165),
                  note='Table 2 partly garbled in the report\'s read; 8011A row cross-checked')),
    rolled_mode='single_sheet', mode_note=_s('Single-rolled (EN: 35–200 µm).', _ROW_WW),
    surface=(_s('Lubricated 100–900 mg/m².', _ROW_WW),),
    other_requirements=(_s('Erichsen test for container foil (EN 546-4).', 'PK-S11'),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_1, STD_EN546_2, STD_EN546_4),
    key_requirement=_s('8011A H22 Rm 90–150 MPa, H24 110–165 MPa; Erichsen test.',
                       'PK-S9 PK-S11'),
    caveats=(_s('EN 546-2 Table 2 was partly garbled in the report\'s read; the 8011A row was '
                'cross-checked against a second copy.', 'PK-S9'),),
)
CONTAINER_SW = Product(
    id='container_foil_smooth_wall', name='Container foil, smooth-wall',
    family='packaging_household',
    final_gauge_m=_r(90, 200, 'um', 'PK-S17'),
    alloys=_items(('8006', '8150', '3005'), 'Smooth-wall container alloy.', 'PK-S17'),
    tempers=(_i('H22', 'Smooth-wall temper.', 'PK-S17'), _i('O', 'Smooth-wall temper.',
                                                             'PK-S17')),
    rolled_mode='single_sheet', mode_note=_s('Single-rolled.', 'PK-S17'),
    other_requirements=(_s('Deeper draw and a sealable rim.', 'PK-S17'),),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_1, STD_EN546_2, STD_EN546_4),
    key_requirement=_s('Deeper draw, sealable rim.', 'PK-S17'),
)
CONTAINER_RT = Product(
    id='container_foil_retortable', name='Container foil, retortable',
    family='packaging_household',
    final_gauge_m=_r(70, 120, 'um', 'PK-S17'),
    alloys=_items(('8026', '3305'), 'Retortable container alloy.', 'PK-S17'),
    tempers=(_i('O', 'Retortable container temper.', 'PK-S17'),),
    rolled_mode='single_sheet', mode_note=_s('Single-rolled.', 'PK-S17'),
    named_defects=FOIL_DEFECTS,
    standards=(STD_EN546_1, STD_EN546_2, STD_EN546_4),
    key_requirement=_s('No requirement beyond gauge, alloy and temper given (vendor page).',
                       'PK-S17'),
)

# --------------------------------------------------------------------------- heat exchanger
_FIN_SCHED = (
    _sched('HX-S3 DC route 3.5–4 mm → 0.080 mm', _mm((3.5, 4.0), 1.0, 0.123, 0.080), 'HX-S3',
           passes_per_step=(None, None, None), display_unit='mm',
           note='multi-pass to about 1 mm, then to 0.123 mm, interanneal 350 °C × 4 h at 50 °C/h, '
                'then 35 % final reduction; pass counts not given'),
    _sched('HX-S4 TRC worked example 0.109 → 0.060 mm', _mm(0.109, 0.060), 'HX-S4',
           passes_per_step=(None,), display_unit='mm',
           note='after interanneal 400 °C × 2 h; pass count not given'),
)
_ROW_FIN_G = 'HX-S4 HX-S7 HX-S16'
_ROW_FIN_A = 'HX-S1 HX-S2 HX-S10 HX-S11 HX-S12'
BRAZED_FIN = Product(
    id='brazed_fin_stock', name='Brazed automotive fin stock (radiator, condenser, evaporator, '
                               'heater, CAC)',
    family='heat_exchanger',
    final_gauge_m=_r(0.04, 0.20, 'mm', _ROW_FIN_G, 'offered 0.04–0.20 mm; common 0.05–0.10 mm'),
    common_gauges=(_s('Common 0.05–0.10 mm. Trend: 80–100 µm "conventional" → 60 → 50 µm in '
                      'production; 40 µm in the laboratory.', _ROW_FIN_G,
                      _r(0.05, 0.10, 'mm', _ROW_FIN_G, 'common')),),
    alloys=(
        _i('3003', 'Fin core, plain or with 0.7–2.5 % Zn (sacrificial to the tube).', _ROW_FIN_A),
        _i('mod-3003', 'Fin core, plain or with 0.7–2.5 % Zn.', _ROW_FIN_A),
        _i('TRC Al-Si-Fe-Mn-Zn', 'Twin-roll-cast fin alloy.', _ROW_FIN_A),
        _i('6063', 'Vacuum-brazed fin (H18).', _ROW_FIN_A),
        _i('4343', 'Clad for CAB brazing; about 10 % per side, range 4–20 %.', _ROW_FIN_A),
        _i('4045', 'Clad for CAB brazing; about 10 % per side, range 4–20 %.', _ROW_FIN_A),
        _i('4004', 'Clad for vacuum brazing.', _ROW_FIN_A),
        _i('4104', 'Clad for vacuum brazing.', _ROW_FIN_A),
    ),
    tempers=(_i('H14', 'Standard fin temper.', 'HX-S1 HX-S12'),
             _i('H16', 'Standard fin temper.', 'HX-S1 HX-S12'),
             _i('H18', 'For 6063 fin.', 'HX-S1 HX-S12')),
    strength=(
        _st('fin stock (alloy not stated)', 'H14', 'pre-braze', 'HX-S10 HX-S11',
            rm=('span', 150, 210), rp=('min', 125, 140), a=('min', 0.5, 1)),
        _st('fin stock (alloy not stated)', 'H16', 'pre-braze', 'HX-S10 HX-S11',
            rm=('span', 170, 230), rp=('min', 160)),
        _st('fin stock (alloy not stated)', 'not stated', 'post-braze', 'HX-S1',
            rm=('span', 110, 155), rp=('span', 40, 65)),
        _st('fin stock (alloy not stated)', 'not stated', 'DC route, pre-braze UTS', 'HX-S3',
            rm=('min', 210, 220), note='post-braze 150–160 MPa; sag 21.5–33 mm'),
        _st('TRC Al-Si-Fe-Mn-Zn', 'not stated', '0.05 mm, post-braze', 'HX-S7',
            rm=('typ', 130), note='about 50 %IACS'),
        _st('3003', 'not stated', '0.06 mm, post-braze', 'HX-S7', rm=('typ', 110),
            note='under 40 %IACS'),
    ) + EN683_STRENGTH,
    rolled_mode='not_published',
    schedules=_FIN_SCHED,
    route=(
        _s('Final cold-work windows: 20–40 % [HX-S3], or 20–35 % at 45–80 µm with interanneal '
           'at 275–400 °C [HX-S5]; an H14-type temper is set by a final reduction of roughly '
           '20–40 % after the interanneal.', 'HX-S3 HX-S5',
           _r(20, 40, '%', 'HX-S3', 'final cold work after interanneal (total, not per pass)'),
           _r(20, 35, '%', 'HX-S5', 'final cold work at 45–80 µm (total, not per pass)')),
        _s('TRC route: cast 6–8 mm → 0.1–0.6 mm → interanneal 350–450 °C for 1–4 h → final '
           'reduction ≥45 % (60–90 % preferred) to 50–70 µm.', 'HX-S4',
           _min(45, '%', 'HX-S4', 'final reduction after interanneal (total)')),
        _s('Mitsubishi: interanneal 460–600 °C for under 4 h, final reduction 15–50 %.', 'HX-S6',
           _r(15, 50, '%', 'HX-S6', 'final reduction (total)')),
        _s('Interanneal temperature matters: 500 °C instead of 350 °C gave finer post-braze '
           'grain and worse sag (32 mm against 24 mm).', 'HX-S3'),
        _s('Clad fin under 80 µm loses brazeability because filler diffuses into the core.',
           'HX-S16'),
        _s('Pre-braze strength must fall as gauge falls, for corrugation forming.', 'HX-S8'),
        _s('3003 work hardening after a 420 °C/2 h anneal: +23 MPa UTS going from 15 to 25 % '
           'reduction, and +31 MPa from 25 to 35 %.', 'HX-S40'),
    ),
    other_requirements=(_s('Sag 15–35 mm, test-dependent.', 'HX-S3 HX-S9',
                           _r(15, 35, 'mm', 'HX-S3 HX-S9', 'sag; test-dependent')),),
    named_defects=STRIP_DEFECTS,
    standards=(STD_EN683,),
    key_requirement=_s('Pre-braze H14 Rm 150–210 MPa; post-braze Rp 40–65 MPa; sag 15–35 mm.',
                       'HX-S10 HX-S11 HX-S1 HX-S3 HX-S9'),
    caveats=(
        _STRIP_DEFECT_CAVEAT,
        _s('Suspected typo: HX-S10 gives its sag-test gauge as "0.008 mm"; the report says it is '
           'almost certainly 0.08 mm.', 'HX-S10'),
        _s('The report\'s disagreement list gives the fin interanneal span as 200–400 °C vs '
           '350–450 °C vs 460–600 °C, while its route text gives 275–400 °C [HX-S5]; both are '
           'carried.', 'HX-S5 HX-S4 HX-S6'),
        _s('The per-pass reduction is not published for fin stock; the final-reduction windows '
           'are totals after the interanneal.', 'HX-S3 HX-S4 HX-S5 HX-S6'),
    ),
    disagreements=(
        _s('Final reduction for fin: 20–40 % (DC) vs 15–50 % vs ≥45–90 % (TRC).',
           'HX-S3 HX-S6 HX-S4'),
        _s('Interanneal temperature for fin: 200–400 °C vs 350–450 °C vs 460–600 °C.',
           'HX-S5 HX-S4 HX-S6'),
        _s('Post-braze 3003: Rm 110 / Rp 40 MPa [HX-S1] vs 122 / 67 MPa [HX-S10]. Sag tests use '
           'different overhangs (50 or 80 mm), so the values are not comparable.',
           'HX-S1 HX-S10'),
        _s('Fin gauge floor: EN 683 stops at 60 µm, while 40–50 µm is sold.',
           'HX-S17 HX-S4 HX-S7'),
    ),
    not_found=(_nf('Pass-by-pass schedules for brazed fin.'),
               _nf('Clad-ratio tolerances.')),
)

BRAZING_SHEET = Product(
    id='brazing_sheet_tube', name='Brazing sheet (tube, header, plate)', family='heat_exchanger',
    final_gauge_m=_r(0.20, 0.40, 'mm', 'HX-S14 HX-S12 HX-S2', 'tube; folded 0.20–0.30 mm, '
                     'HF-welded 0.22–0.40 mm'),
    common_gauges=(_s('Tube 0.20–0.40 mm (folded 0.20–0.30, HF-welded 0.22–0.40); '
                      'header/plate 0.4–3.0 mm.', 'HX-S14 HX-S12 HX-S2'),
                   _s('Heater-core tube is down to 0.2 mm.', 'HX-S2')),
    alloys=(
        _i('3003', 'Core.', 'HX-S1 HX-S2'), _i('mod-3003', 'Core.', 'HX-S1 HX-S2'),
        _i('3005', 'Long-life core.', 'HX-S1 HX-S2'), _i('mod-6063', 'Core.', 'HX-S1 HX-S2'),
        _i('4343', 'Braze clad; 5–20 % one side, 5–15 % each of two.', 'HX-S1 HX-S2'),
        _i('4045', 'Braze clad.', 'HX-S1 HX-S2'), _i('4047', 'Braze clad.', 'HX-S1 HX-S2'),
        _i('7072', 'Waterside liner.', 'HX-S1 HX-S2'),
        _i('Zn-bearing 3xxx', 'Waterside liner.', 'HX-S1 HX-S2'),
    ),
    tempers=(_i('H24', 'Tube.', 'HX-S1 HX-S12'), _i('H14', 'Tube (alternative).',
                                                     'HX-S1 HX-S12'),
             _i('O', 'Plate.', 'HX-S1 HX-S12')),
    strength=(_st('brazing sheet (alloy not stated)', 'not stated', 'post-braze', 'HX-S1',
                  rm=('span', 110, 190), rp=('span', 40, 90)),),
    rolled_mode='not_published',
    route=(_s('DC core, scalped, liner plates roll-bonded in hot rolling, cold rolled to gauge '
              '(0.27 mm in the example), final partial anneal to H24; clad 10 % 4343 plus 10 % '
              'waterside.', 'HX-S13'),),
    other_requirements=(_s('Tube sag 17–22 mm at 80 mm overhang, 0.27–0.31 mm gauge.', 'HX-S13',
                           _r(17, 22, 'mm', 'HX-S13', 'sag at 80 mm overhang')),),
    named_defects=STRIP_DEFECTS,
    key_requirement=_s('Post-braze Rp 40–90 MPa, Rm 110–190 MPa.', 'HX-S1'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
    not_found=(_nf('A pass schedule for brazing sheet.'), _nf('Clad-ratio tolerances.')),
)

_HVAC_SCHED = (
    _sched('HX-S21 TRC 6.2 mm → 0.080–0.085 mm', _mm(6.2, 2.85, 1.45, 0.82, 0.42, 0.23, 0.13,
                                                     (0.080, 0.085)), 'HX-S21',
           passes_per_step=(None, None, None, None, None, 1, 1), display_unit='mm',
           note='trim after 0.82 mm; the last two steps are the foil passes; total 98.7 %, no '
                'interanneal; the report prints 36.5 % for the last pass and 34.6–38.5 % across '
                'the final-gauge range'),
    _sched('HX-S22 Novelis belt-cast 1.7 → 0.10 mm in 3 passes', _mm(1.7, 0.10), 'HX-S22',
           passes_per_step=(3,), display_unit='mm',
           note='94.1 % total, mean 61 % per pass (report calc.)'),
    _sched('HX-S23 8014-H22 6.4–7.4 → 0.17–0.24 mm in 8 passes',
           _mm((6.4, 7.4), (0.17, 0.24)), 'HX-S23', alloy='8014', passes_per_step=(8,),
           display_unit='mm', note='mean about 34–38 % per pass (report calc.)'),
)
HVAC_FIN = Product(
    id='hvac_fin_stock', name='HVAC fin stock (mechanically assembled)',
    family='heat_exchanger',
    final_gauge_m=_r(0.08, 0.20, 'mm', 'HX-S20', 'nominals 0.095 / 0.105 / 0.115 / 0.125 mm'),
    common_gauges=(_s('Nominals 0.095, 0.105, 0.115 and 0.125 mm.', 'HX-S20'),),
    alloys=_items(('8011', '1100', '1200', '3102', '8006', '1030B'), 'HVAC fin alloy.',
                  'HX-S2 HX-S20') + _items(('1050A', '8079'), 'Also used.', 'HX-S2 HX-S20'),
    tempers=_items(('O', 'H22', 'H24', 'H26'), 'HVAC fin temper; H2x by final partial anneal.',
                   'HX-S20'),
    strength=(
        _st('8011', 'H22', 'vendor', 'HX-S20', rm=('span', 100, 135), a=('min', 17, 22),
            note='Erichsen ≥6.0 mm'),
        _st('alloy not stated', 'not stated', 'HX-S21 TRC route, final anneal 265–272 °C × 25–30 h',
            'HX-S21',
            rm=('span', 133, 136), a=('span', 19, 20), note='cupping 6.5 mm'),
        _st('alloy not stated', 'not stated', 'HX-S22 belt-cast route, partial anneal 245–255 °C',
            'HX-S22',
            rm=('span', 119, 126), rp=('span', 100, 111), a=('span', 17.5, 18.5)),
    ) + EN683_STRENGTH,
    rolled_mode='not_published',
    schedules=_HVAC_SCHED,
    per_pass_reduction=_per_pass_span(_HVAC_SCHED, 'computed from the explicit foil passes of '
                                      'HX-S21 and the equal-split means of the HX-S22 and '
                                      'HX-S23 blocks; the HX-S21 hot-band steps are excluded '
                                      'because their pass counts are not stated',
                                      include_block_means=True),
    final_pass=_final_pass_from(_HVAC_SCHED, basis='computed from the HX-S21 last foil pass'),
    annealing=(
        _s('HX-S21: total 98.7 % with no interanneal; final anneal 265–272 °C × 25–30 h gave '
           'Rm 133–136 MPa, A 19–20 %, cupping 6.5 mm.', 'HX-S21'),
        _s('Novelis: partial anneal 245–255 °C with furnace overheat under 10 °C gave YS '
           '100–111, UTS 119–126 MPa, A 17.5–18.5 %; the DC route is partially annealed at '
           '240–270 °C at 0.10–0.13 mm.', 'HX-S22'),
        _s('8014-H22: cast 6.4–7.4 mm, homogenised 520–530 °C, eight passes to 0.17–0.24 mm, '
           'final anneal 360–370 °C.', 'HX-S23'),
    ),
    surface=(_s('Hydrophilic coat 1–3 µm per side, contact angle ≤5–10°.', 'HX-S20'),),
    thickness_tolerance=(_s('Vendors ±3 % or ±5 %.', 'HX-S20'),
                         _s('EN 683-3 ±6 % single reading.', 'HX-S17')),
    named_defects=STRIP_DEFECTS,
    standards=(STD_EN683,),
    key_requirement=_s('8011-H22: Rm 100–135 MPa, A ≥17–22 %, Erichsen ≥6.0 mm.', 'HX-S20'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
    disagreements=(_s('HVAC fin tolerance: ±3 % vs ±5 % (vendors) vs ±6 % single reading '
                      '(EN 683-3).', 'HX-S20 HX-S17'),),
)

_LITHO_SCHED = (
    _sched('HX-S25 Hydro 2.8 mm, 3 passes', _mm(2.8), 'HX-S25',
           published_reductions=(0.57, 0.53, 0.51), display_unit='mm',
           note='published as reductions; gauges computed (report: 1.204 → 0.566 → 0.277 mm)'),
    _sched('HX-S25 Hydro 2.3 mm, 3 passes', _mm(2.3), 'HX-S25',
           published_reductions=(0.57, 0.50, 0.45), display_unit='mm',
           note='published as reductions; gauges computed (report: 0.989 → 0.494 → 0.272 mm)'),
    _sched('HX-S25 Hydro 3.0 mm, 3 passes', _mm(3.0), 'HX-S25',
           published_reductions=(0.60, 0.53, 0.51), display_unit='mm',
           note='published as reductions; gauges computed (report: 1.20 → 0.564 → 0.276 mm)'),
    _sched('HX-S26 interanneal at 0.9–1.2 mm → 0.28 mm', _mm((0.9, 1.2), 0.28), 'HX-S26',
           passes_per_step=(None,), display_unit='mm', note='cold reduction after interanneal'),
    _sched('HX-S26 interanneal at 2.0–2.4 mm → 0.29 mm', _mm((2.0, 2.4), 0.29), 'HX-S26',
           passes_per_step=(None,), display_unit='mm', note='cold reduction after interanneal'),
    _sched('HX-S27 interanneal at 2.2 mm → 0.30 mm', _mm(2.2, 0.30), 'HX-S27',
           passes_per_step=(None,), display_unit='mm', note='cold reduction after interanneal'),
    _sched('HX-S28 TRC 4.5 → 1.5 → 0.28 mm', _mm(4.5, 1.5, 0.28), 'HX-S28',
           passes_per_step=(None, None), display_unit='mm',
           note='recovery anneal 300 °C × 2 h at 1.5 mm; gave 177 MPa against 157 MPa with a '
                'recrystallising 380 °C anneal'),
)
_ROW_LITHO_A = 'HX-S25 HX-S26 HX-S28 HX-S36'
LITHO = Product(
    id='litho_sheet', name='Lithographic sheet', family='litho',
    final_gauge_m=_r(0.10, 0.50, 'mm', 'HX-S25 HX-S35', 'common 0.15 / 0.20 / 0.24 / 0.27–0.30 '
                     '/ 0.40 mm'),
    common_gauges=(_s('Common 0.15, 0.20, 0.24, 0.27–0.30 and 0.40 mm.', 'HX-S25 HX-S35'),),
    alloys=(_i('1050', 'Main litho alloy.', _ROW_LITHO_A),
            _i('1050A', 'Main litho alloy.', _ROW_LITHO_A)) + _items(
        ('1052', '1060', '1070', '1200', '3103'), 'Litho alloy.', _ROW_LITHO_A) + (
        _i('Al-Fe-Mg 0.1–1.0 % grades', 'For fatigue and bake strength.', _ROW_LITHO_A),),
    tempers=(_i('H18', 'With interanneal.', 'HX-S25'), _i('H19', 'Without interanneal.',
                                                           'HX-S25')),
    strength=(
        _st('1050', 'H18', 'minimum', 'HX-S26 HX-S36', rm=('min', 135)),
        _st('Al-Fe-Mg 0.1–1.0 % grades', 'not stated', 'Mg grades', 'HX-S26 HX-S36',
            rm=('span', 177, 218)),
        _st('Al-Fe-Mg 0.1–1.0 % grades', 'not stated', 'after 240 °C/10 min bake',
            'HX-S26 HX-S36', rm=('min', 145)),
        _st('alloy not stated', 'not stated', 'TRC route, recovery anneal 300 °C', 'HX-S28',
            rm=('typ', 177), note='157 MPa with a recrystallising 380 °C anneal'),
    ),
    rolled_mode='single_sheet',
    mode_note=_s('Single-stand, one pass per coiling, coils cooled between passes, polished '
                 'mill-finish rolls.', 'HX-S25'),
    schedules=_LITHO_SCHED,
    per_pass_reduction=_per_pass_span(_LITHO_SCHED, 'span of the Hydro three-pass examples '
                                      '(published reductions); limits: first pass ≤65 % (≤60 % '
                                      'preferred), second ≤60 %, last ≤52 %; historically ≤50 % '
                                      'per pass'),
    final_pass=_final_pass_from(
        _LITHO_SCHED[:3], basis='entry gauge computed from the Hydro examples',
        reduction=_r(20, 52, '%', 'HX-S25 HX-S34', 'last pass ≤52 % [HX-S25]; last-pass '
                     'work-roll Ra 0.07–0.18 µm used with ≥20 % reduction [HX-S34]')),
    foil_stock=(_s('Hot band: scalp 10–20 mm per face; homogenise 450–600 °C; hot roll to '
                   '2–7 mm (2.3–3.7 preferred), finishing at 280–350 °C.', 'HX-S27 HX-S25',
                   _r(2, 7, 'mm', 'HX-S25', 'hot-band gauge')),),
    annealing=(_s('Interanneal optional, 230–490 °C for ≥1 h, usually before the last pass.',
                  'HX-S25'),),
    route=(
        _s('Historically ≤50 % per pass, so at least four passes for 0.2–0.4 mm and five below '
           '0.2 mm.', 'HX-S25', _max(50, '%', 'HX-S25', 'traditional per-pass limit')),
        _s('Limits stated: first pass ≤65 % (≤60 % preferred), second ≤60 %, last ≤52 %. A 64 % '
           'first pass gave visibly worse pickling-test streakiness.', 'HX-S25',
           _max(65, '%', 'HX-S25', 'first pass'), _max(60, '%', 'HX-S25', 'second pass'),
           _max(52, '%', 'HX-S25', 'last pass')),
    ),
    work_roll_roughness=(_s('Last-pass work-roll Ra 0.07–0.18 µm with ≥20 % reduction.',
                            'HX-S34', _r(0.07, 0.18, 'um', 'HX-S34'), topic='last pass'),),
    surface=(_s('Conventional strip Ra 0.15–0.25 µm; peak height Rp ≤1.4 µm; degrease with '
                'pickling removal ≥0.25 g/m².', 'HX-S34', _r(0.15, 0.25, 'um', 'HX-S34')),),
    thickness_tolerance=(
        _s('ISO 12635 plate thickness ±0.010 mm.', 'HX-S35b'),
        _s('Vendor strip tolerances ±0.005 mm (≤0.20 mm) and ±0.007 mm (>0.20 mm).', 'HX-S36b'),
        _s('EN 485-4: ±0.02 mm for 0.2–0.4 mm at ≤1000 mm width (soft-alloy group).', 'HX-S18'),
    ),
    flatness_requirement=(
        _s('CtP edge wave ≤3.0 mm (1.5 mm recommended).', 'HX-S35b',
           _max(3.0, 'mm', 'HX-S35b', 'edge wave')),
        _s('Pure-stretch levelling line for 0.12–0.48 mm at up to 500 m/min; the strip must be '
           'oil-free first.', 'HX-S35'),
        _s('Mill-exit targets 5–6 I-units for 1–3 mm strip, and ≤2 (down to 1) after '
           'stretch-bend levelling of thin strip (a copper/thin-strip paper).', 'HX-S41'),
    ),
    named_defects=(
        _d('Grain streaks', 'Rolling-direction streaks after graining.',
           'Coarse or mixed recrystallised grains in the hot band. Remedy: no recrystallisation '
           'between hot passes, final hot pass ≥55 %, surface grain under 50 µm across the '
           'rolling direction.', 'HX-S29 HX-S30'),
        _d('Texture bands', 'Bands that etch differently (cube against copper orientation).',
           'Texture; the interanneal controls streakiness.', 'HX-S32 HX-S31'),
        _d('Ingot-origin streaks', 'Streaky sheet.',
           'Feather grains (even after homogenising); fir-tree Al-Fe phase zones exposed by '
           'scalping; hydrogen content.', 'HX-S27 HX-S31'),
        _d('Torn, streaky surface', 'Streaky look.', 'Excessive cold-rolling pass reduction.',
           'HX-S25'),
        _d('Roll-grinding imprints', 'Imprinted ridges.',
           'Roll-grinding ridges and roll wear imprint into the strip.', 'HX-S34'),
        _d('Un-grained plateaux', 'Plateaux that do not grain.',
           'Residual oil and sub-surface oxide islands.', 'HX-S31 HX-S36b'),
    ),
    standards=(STD_EN485_1, STD_ISO12635, STD_EN485_4),
    key_requirement=_s('Streak-free electrograining; strip Ra 0.15–0.25 µm.', 'HX-S34'),
    disagreements=(
        _s('Litho pass limit: ≤50 % traditional vs 57–60 % (Hydro). Interanneal gauge ranges '
           'from 0.9 to 2.4 mm, or is omitted.', 'HX-S25 HX-S26 HX-S27'),
        _s('Litho thickness tolerance: ±5–7 µm vs ±10 µm.', 'HX-S36b HX-S35b'),
    ),
    not_found=(_nf('Primary-source I-unit specifications for litho or fin stock; "<2 I-units" '
                   'for litho appears only on a trade blog that is not in the source list.'),
               _nf('Mill speeds specific to fin or litho mills.')),
)

# --------------------------------------------------------------------------- other strip
CAN_BODY = Product(
    id='can_body_stock', name='Can body stock', family='other_strip',
    final_gauge_m=_r(0.254, 0.33, 'mm', 'HX-S38', 'tolerance band; market 0.245–0.285 mm'),
    common_gauges=(_s('0.254–0.33 mm (tolerance band); market 0.245–0.285 mm.', 'HX-S38'),),
    alloys=(_i('3104', 'Can body alloy.', 'HX-S38'), _i('3004', 'Can body alloy (alternative '
                                                         'designation given in parentheses).',
                                                         'HX-S38')),
    tempers=(_i('H19', 'Can body temper.', 'HX-S38'),),
    strength=(_st('3104, 3004', 'H19', 'yield strength', 'HX-S38', rp=('span', 255, 296)),),
    rolled_mode='not_published',
    thickness_tolerance=(_s('±5 µm.', 'HX-S38'),),
    other_requirements=(_s('Earing ≤4 %.', 'HX-S38', _max(4, '%', 'HX-S38', 'earing')),),
    named_defects=STRIP_DEFECTS,
    key_requirement=_s('YS 255–296 MPa; ±5 µm; earing ≤4 %.', 'HX-S38'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
)
CAN_END = Product(
    id='can_end_stock', name='Can end and tab stock', family='other_strip',
    final_gauge_m=_r(0.198, 0.38, 'mm', 'HX-S38', 'end; tab 0.22–0.56 mm'),
    common_gauges=(_s('End 0.198–0.38 mm; tab 0.22–0.56 mm.', 'HX-S38'),),
    alloys=(_i('5182', 'End and tab alloy.', 'HX-S38'), _i('5042', 'End and tab alloy.',
                                                           'HX-S38'),
            _i('5052', 'Food cans.', 'HX-S38')),
    tempers=_items(('H19', 'H39', 'H48'), 'End/tab temper.', 'HX-S38'),
    strength=(_st('5182', 'H48', 'coated', 'HX-S38', rm=('min', 365), rp=('span', 331, 362)),),
    rolled_mode='not_published',
    thickness_tolerance=(_s('±5 µm.', 'HX-S38'),),
    flatness_requirement=(_s('Edge wave ≤3.2 mm.', 'HX-S38', _max(3.2, 'mm', 'HX-S38')),),
    named_defects=STRIP_DEFECTS,
    key_requirement=_s('Coated 5182-H48: UTS ≥365 MPa, YS 331–362 MPa; ±5 µm; edge wave '
                       '≤3.2 mm.', 'HX-S38'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
)
CLOSURE = Product(
    id='closure_sheet', name='Closure sheet', family='other_strip',
    final_gauge_m=_r(0.15, 0.30, 'mm', 'HX-S38 HX-S39'),
    alloys=_items(('8011', '3105', '5352'), 'Closure alloy.', 'HX-S38 HX-S39'),
    tempers=_items(('H14', 'H16', 'H19', 'H25'), 'Closure temper.', 'HX-S38 HX-S39'),
    strength=(_st('8011', 'H14/H16', 'closure', 'HX-S38 HX-S39', rm=('span', 130, 165)),
              _st('3105', 'H19', 'closure', 'HX-S38 HX-S39', rm=('span', 234, 259))),
    rolled_mode='not_published',
    other_requirements=(_s('Earing ≤3–4 %.', 'HX-S38 HX-S39'),),
    named_defects=STRIP_DEFECTS,
    key_requirement=_s('8011-H14/16 Rm 130–165 MPa; 3105-H19 234–259 MPa; earing ≤3–4 %.',
                       'HX-S38 HX-S39'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
)
TRANSFORMER = Product(
    id='transformer_strip', name='Transformer strip and cable foil', family='other_strip',
    final_gauge_m=_r(0.08, 3.5, 'mm', 'HX-S39', 'transformer strip; cable foil 0.006–0.20 mm'),
    common_gauges=(_s('Strip 0.08–3.5 mm; cable foil 0.006–0.20 mm.', 'HX-S39'),),
    alloys=_items(('1050', '1060', '1070', '1350'), 'Transformer strip alloy.', 'HX-S39') +
    _items(('1235', '8011'), 'Cable foil alloy.', 'HX-S39'),
    tempers=(_i('O', 'Soft temper.', 'HX-S39'),),
    strength=(_st('1050, 1060, 1070, 1350, 1235, 8011', 'O', 'vendor', 'HX-S39',
                  rm=('span', 60, 95)),),
    rolled_mode='not_published',
    other_requirements=(_s('Conductivity ≥60–62 % IACS; burr-free edge.', 'HX-S39'),),
    named_defects=STRIP_DEFECTS,
    key_requirement=_s('≥60–62 % IACS, burr-free edge, Rm 60–95 MPa.', 'HX-S39'),
    caveats=(_STRIP_DEFECT_CAVEAT,),
)

# --------------------------------------------------------------------------- general reference
_PK_GENERAL_SCHED = _HH_SCHED + _CONV_SCHED
GENERAL_FOIL_PER_PASS_SPAN = Statement(
    'Span of the published packaging foil passes (PK-S2 household and converter, PK-S3 TRC 8079, '
    'PK-S16 Yennora); the report prints 46–54 % for PK-S2 and 44–60 % for PK-S3.',
    _union_sources(_PK_GENERAL_SCHED),
    (_per_pass_span(_PK_GENERAL_SCHED, 'computed from the published single packaging foil '
                    'passes (multi-pass blocks excluded)'),),
    'per_pass_reduction', 'computed')
SURFACE_FACT = _s('Roll-side faces are bright and the foil-to-foil faces matt; single-rolled foil '
                  'is bright on both sides.', 'PK-S6 PK-S26', topic='doubling_and_surfaces')
GENERAL_FOIL_ROLLING = (
    _s('Per-pass reduction "about 50 %", with five passes to 18–20 µm.', 'PK-S1',
       _pt(50, '%', 'PK-S1', '"about"'), topic='per_pass_reduction'),
    _s('About 50 % per pass in an industrial 1200 trial from 0.4 mm.', 'PK-S27',
       topic='per_pass_reduction'),
    GENERAL_FOIL_PER_PASS_SPAN,
    _s('Battery foil: three to six foil passes, 29–64 % per pass; BF-S12 calls 5–6 passes from '
       '≤0.24 mm stock the industry norm.', 'BF-S12', topic='per_pass_reduction'),
    _s('Closed gap: roll contact begins at 0.1–0.2 mm [PK-S1]; "<100 µm" [PK-S2]; "~0.080 mm" '
       '[PK-S4].', 'PK-S1 PK-S2 PK-S4',
       _r(80, 200, 'um', 'PK-S1 PK-S2 PK-S4', 'closed-gap onset; sources disagree'),
       topic='closed_gap'),
    _s('Roll force is ineffective for gauge below about 50 µm. Tension is the fine control and '
       'speed the coarse control (the "speed effect", through oil-film hydrodynamics).',
       'PK-S1 PK-S4', _max(50, 'um', 'PK-S1 PK-S4', 'roll force ineffective below about'),
       topic='closed_gap'),
    _s('An Achenbach mill uses position control at 300 µm and constant force on the doubled '
       'final pass.', 'PK-S28', topic='closed_gap'),
    _s('Doubling starts below 20 µm and is necessary below 10–15 µm [PK-S1]; below 25 µm '
       '[PK-S26]; below 30 µm [PK-S29]; at ≤50 µm (Impol practice) [PK-S18]. EN 546-4 lets '
       'double-rolled product run to 70 µm and single-rolled start at 35 µm.',
       'PK-S1 PK-S26 PK-S29 PK-S18 PK-S11',
       _r(20, 50, 'um', 'PK-S1 PK-S26 PK-S29 PK-S18', 'gauge below which doubling starts; '
          'sources disagree'), topic='doubling_threshold'),
    _s('Battery foil: pack rolling covers 5–20 µm; single rolling is feasible for 9–20 µm; the '
       'Mino finishing mill minimum is 1×12 µm or 2×6 µm.', 'BF-S18 BF-S25',
       topic='doubling_threshold'),
    _s('Last pass limited to about 600 m/min for lustre.', 'PK-S1',
       _pt(600, 'm/min', 'PK-S1', '"about"'), topic='speeds'),
    _s('600–1000 m/min schedule values.', 'PK-S2', _r(600, 1000, 'm/min', 'PK-S2'),
       topic='speeds'),
    _s('Foil-mill design maxima 2000–2250 m/min.', 'PK-S28',
       _r(2000, 2250, 'm/min', 'PK-S28'), topic='speeds'),
    _s('Battery foil-mill builder maxima 1500–2200 m/min.', 'BF-S24 BF-S26', topic='speeds'),
    _s('Single-stand cold mills 1200–1500 m/min maximum; foil mills up to 2500 m/min.',
       'HX-S37', topic='speeds'),
    _s('Strip reaches about 100 °C per pass, with 3–4 passes and coil cooling between.',
       'HX-S36', topic='speeds'),
    _s('Mill types: roughing 0.7 → 0.012 mm, intermediate 0.12 → 0.006 mm, finishing 0.05 → '
       '<0.006 mm.', 'PK-S28', topic='mill_types'),
    _s('Rolling oil: kerosene base with fatty acid, alcohol or ester additives [PK-S1]; alcohol '
       '2–5 % and ester 1–3 % [PK-S29].', 'PK-S1 PK-S29', topic='oil_and_rolls'),
    _s('Oil 20–40 °C in roughing, 40–60 °C in finishing; rougher rolls for roughing, finer for '
       'finishing.', 'PK-S29', topic='oil_and_rolls'),
    _s('Roll roughness about equals foil roughness after one pass.', 'PK-S3 PK-S27',
       topic='oil_and_rolls'),
    SURFACE_FACT,
    _s('The matt face is made of slip steps across the rolling direction, and pinholes are local '
       'shear-through from deep matt-side valleys.', 'PK-S1', topic='doubling_and_surfaces'),
    _s('Separation, trim and slitting happen in one operation at 300–600 m/min, with light-box '
       'inspection for porosity and roll holes.', 'PK-S1', _r(300, 600, 'm/min', 'PK-S1'),
       topic='separating'),
    _s('Final anneal (O temper): slow heating, metal at 240–280 °C, up to 70 h depending on '
       'coil width and diameter, good ventilation, controlled cooling. Aims: dry, flat (no '
       '"heat pockets"), non-sticky foil.', 'PK-S1', topic='final_anneal'),
    _s('Dryness trades off against stickiness; double-bright foil is the most sticky-prone, and '
       '>99.5 % Al risks coarse grain. H18 lidding foil is used as-rolled, without anneal.',
       'PK-S1', topic='final_anneal'),
    _s('Kerth foil stock: 0.5–0.7 mm, annealed dead-soft before foil rolling, from 5–8 mm hot '
       'band or cast strip; stock tolerance ±5 % along length and ±1 % across width, to avoid '
       'edge corrugation.', 'PK-S1', _r(0.5, 0.7, 'mm', 'PK-S1'), topic='foil_stock'),
    _s('Hindalco foil stock: 0.2–0.6 mm ±5 %, tempers "M" (as-rolled, Rm 125–180 MPa), H14 or '
       'H16; flatness <20 I-units, wedge ≤0.7 %; from DC ingot and concast.', 'PK-S23',
       _r(0.2, 0.6, 'mm', 'PK-S23'), topic='foil_stock'),
    _s('Twin-roll cast is described as limited to pure or low-alloy grades [PK-S5]; it is used '
       'industrially for 1235, 8011, 8079, 8006 and 8021 with a homogenisation step [PK-S3, '
       'PK-S31].', 'PK-S5 PK-S3 PK-S31', topic='foil_stock'),
    _s('Flatness: no numeric foil limit found; Kerth uses waviness W = 100·f/L % and notes '
       'stretching is practical only above about 100 µm.', 'PK-S1', topic='flatness'),
    _s('Wettability: EN classes A (water), B (+10 % ethanol), C (+20 %), on to G; A–C '
       'acceptable. ASTM equivalent: dry-annealed A / B / C, or "slick".', 'PK-S11 PK-S12',
       topic='wettability'),
    _s('Alloy roles (largely vendor statements, consistent with the EN 546-2 strength ranking): '
       '1235 / 1145 / 1200 softest, best rollability to 6 µm; 8079 (Fe 0.7–1.3, Si 0.05–0.3) '
       'more strength and elongation at thin gauge than 1xxx; 8011 / 8011A (Al-Fe-Si) '
       'general-purpose, the hard-temper lidding alloy; 8021 / 8021B (Fe 1.2–1.7) highest '
       'O-temper elongation (≥12 % at 45 µm), hence cold forming; 8006 (Al-Fe-Mn) strongest '
       '(O-temper Rm 80–140 MPa), for containers and down-gauged household foil; 3xxx rigidity '
       'in containers.', 'PK-S9', topic='alloy_roles', status='vendor_or_trade_page'),
    _s('5052 appears only for single-rolled technical foil.', 'PK-S18', topic='alloy_roles'),
)
GENERAL_DISAGREEMENTS = (
    _s('Gauge at which doubling starts: <20 µm and necessary below 10–15 µm [PK-S1]; <25 µm '
       '[PK-S26]; <30 µm [PK-S29]; ≤50 µm (Impol practice) [PK-S18]. EN 546-4 lets double-rolled '
       'product run to 70 µm and single-rolled start at 35 µm.',
       'PK-S1 PK-S26 PK-S29 PK-S18 PK-S11'),
    _s('Closed-gap onset: 100–200 µm [PK-S1], <100 µm [PK-S2], about 80 µm [PK-S4].',
       'PK-S1 PK-S2 PK-S4'),
    _s('Thickness tolerance: EN ±8 % and ASTM ±10 % versus vendor claims of ±3–5 %.',
       'PK-S10 PK-S12'),
)
GENERAL_NOT_FOUND = (
    _nf('Suppository-foil gauge and alloy.'),
    _nf('Numeric flatness (I-unit) limits for finished foil.'),
    _nf('Datasheets with numbers from Novelis, Speira, Hydro, Constellium, Carcano, Lotte or '
        'UACJ (packaging report); gauge datasheets from Novelis, Speira, Constellium, Arconic or '
        'Kobelco (the Gränges catalogue gives properties but no gauges).', 'HX-S1'),
    _nf('Separating-oil composition.'),
    _nf('Work-roll roughness by pass from a primary source in stated SI units (packaging).'),
    _nf('A reliable wine-capsule foil specification.'),
    _nf('Cable shield foil: no solid numbers found.'),
    _nf('Cross-width thickness-profile (crown) specifications for strip.'),
    _nf('patents.google.com was blocked for the fetch tool in the heat-exchanger research '
        'session; those patents were read through the Exa tools.'),
    GENERAL_STANDARDS_NOT_READ,
)

MINOR_PRODUCTS = (
    _s('Wine capsule (polylaminate) foil: sources conflict on gauge, 6–10 µm or 16–50 µm; '
       '8011, 8079, 1235; O temper. Low confidence.', 'PK-S33', topic='wine_capsule'),
    _s('Cable wrap: 9–23 µm Al (+ PET); 1235, 8011; O; doubled.', 'PK-S33', topic='cable_wrap'),
    _s('Battery tab lead: Al positive conductor 0.4 mm × 50 mm (automotive) and 0.08 mm × 5 mm '
       '(small devices).', 'BF-S41', topic='tab_lead'),
    _s('Battery cell case: 3003 or 1050, O or H14, 0.30–0.80 mm [BF-S42]; prismatic can wall '
       '0.7–1.5 mm [BF-S43]; GB/T 33824-2025 governs [BF-S44].', 'BF-S42 BF-S43 BF-S44',
       topic='cell_case'),
    _s('Insulation facing / tape: 8–70 µm double-rolled, 50–100 µm single; 1200, 1050A, 8006, '
       '8079; O / H18; both modes.', 'PK-S18', topic='insulation_facing'),
    _s('Child-resistant lidding: Al 9–25 µm in paper/PET/Al/HSL, or 20–25 µm Al + 15–20 µm '
       'PVC; 8011; soft or hard; doubled; total laminate 80–135 µm; peel-push = '
       'paper/PET/Al/HSC.', 'PK-S21 PK-S20', topic='child_resistant_lidding'),
    _s('Sachet / pouch laminate: 6–7 and 8–12 µm (7 / 9 / 12 µm); 8079, 1235, 8011; O; '
       'doubled; as converter foil.', 'PK-S21 PK-S22', topic='sachet'),
    _s('Chewing-gum / confectionery: 6–7 µm + paper 20–35 g/m²; alloy not found; O; doubled; '
       'fold retention, embossing.', 'PK-S25', topic='confectionery'),
    _s('Butter wrap: 6.5–7 µm + paper; 8011, 1235; O; doubled; one vendor only.', 'PK-S33',
       topic='butter_wrap'),
)
MINOR_DISAGREEMENTS = (
    _s('Wine-capsule foil gauge: 6–10 µm versus 16–50 µm.', 'PK-S33'),
)

_PRODUCT_LIST = (BATTERY_COLLECTOR, POUCH, THICK_COLLECTOR, CARBON_COATED_BASE, TAB_FOIL, CAP_HV, CAP_LV, CAP_CATHODE, BLISTER, COLD_FORM,
                 STRIP_PACK, HOUSEHOLD, HOUSEHOLD_HD, CONVERTER, CIGARETTE, DAIRY, CONTAINER_WW,
                 CONTAINER_SW, CONTAINER_RT, BRAZED_FIN, BRAZING_SHEET, HVAC_FIN, LITHO, CAN_BODY,
                 CAN_END, CLOSURE, TRANSFORMER)
_PRODUCTS = {p.id: p for p in _PRODUCT_LIST}
GRADE_TABLES = {
    'battery_collector_foil': COLLECTOR_BANDS,
    'battery_pouch_laminate_foil': (BAND_POUCH,),
    'battery_thick_collector_foil': (BAND_THICK,),
    'battery_carbon_coated_base_foil': (BAND_CC,),
    'battery_tab_foil': (BAND_TAB,),
}
GRADE_GENERAL = (GB_TABLE_READ, GB_ELONGATION, TEMPER_NAMING, HEATING_NOTE, CELL_CASE_STOCK) + \
    CONDUCTIVITY + OTHER_GRADE_DOCUMENTS + HEADLINE_FINDINGS + CORRECTIONS + GRADE_REASONS + \
    GAUGES_IN_USE + GRADE_DISAGREEMENTS


def _validate_all():
    for s in _SOURCE_LIST:
        s.validate()
    if len(_PRODUCTS) != len(_PRODUCT_LIST):
        raise ValueError('duplicate product ids')
    for p in _PRODUCT_LIST:
        p.validate()
    for s in GENERAL_FOIL_ROLLING + GENERAL_DISAGREEMENTS + MINOR_PRODUCTS + MINOR_DISAGREEMENTS:
        s.validate()
    for s in GENERAL_NOT_FOUND:
        s.validate(require_sources=False)
    for d in FOIL_DEFECTS + STRIP_DEFECTS:
        d.validate()
    for i in GENERAL_STANDARDS:
        i.validate()
    for s in (BATTERY_SCHEDULE_CAVEAT, TENSION_LINES):
        s.validate()
    for pid, bands in GRADE_TABLES.items():
        if pid not in _PRODUCTS:
            raise ValueError(f'grade table for unknown product {pid}')
        for b in bands:
            b.validate()
        for a, b in zip(bands, bands[1:]):
            if abs(a.high_m - b.low_m) > 1e-12 or b.low_inclusive:
                raise ValueError(f'{pid}: grade bands must be contiguous')
    for s in GRADE_GENERAL:
        s.validate()
    for s in GRADE_NOT_FOUND:
        s.validate(require_sources=False)
    for t in TEMPER_TABLE + STRENGTH_AFTER_HEATING + TEMPERATURE_MAP + PT_SURFACE:
        t.validate()
    for s in PT_ALL_STATEMENTS:
        s.validate()
    for s in PT_NOT_FOUND:
        s.validate(require_sources=False)


_validate_all()


# --------------------------------------------------------------------------- query API
def products():
    """All products, battery collector foil first (tuple of frozen ``Product``)."""
    return _PRODUCT_LIST


def product_ids():
    return tuple(p.id for p in _PRODUCT_LIST)


def product(product_id):
    """The product with this id; ``ValueError`` listing the valid ids otherwise."""
    if not isinstance(product_id, str) or product_id not in _PRODUCTS:
        raise ValueError(f'unknown product id {product_id!r}; valid ids: '
                         f'{", ".join(product_ids())}')
    return _PRODUCTS[product_id]


def sources():
    """All sources as ``{id: Source}`` (a fresh dict)."""
    return dict(_SOURCES)


def _walk_sourced(value, out):
    if isinstance(value, (tuple, list)):
        for v in value:
            _walk_sourced(v, out)
    elif is_dataclass(value) and not isinstance(value, type):
        if isinstance(value, Source):
            return
        if hasattr(value, 'sources'):
            out.append(value)
        for f in fields(value):
            _walk_sourced(getattr(value, f.name), out)


def _all_facts():
    out = []
    _walk_sourced(_PRODUCT_LIST, out)
    _walk_sourced((GENERAL_FOIL_ROLLING, GENERAL_DISAGREEMENTS, GENERAL_NOT_FOUND,
                   MINOR_PRODUCTS, MINOR_DISAGREEMENTS, FOIL_DEFECTS, STRIP_DEFECTS,
                   GENERAL_STANDARDS, tuple(GRADE_TABLES.values()), GRADE_GENERAL,
                   GRADE_NOT_FOUND, TEMPER_TABLE, STRENGTH_AFTER_HEATING, TEMPERATURE_MAP,
                   PT_SURFACE, PT_ALL_STATEMENTS, PT_NOT_FOUND), out)
    unique, seen = [], set()
    for f in out:
        if id(f) not in seen:
            seen.add(id(f))
            unique.append(f)
    return unique


def fact_count():
    """Number of distinct sourced value carriers (shared objects counted once)."""
    return len(_all_facts())


def catalogue_dict():
    """The whole catalogue as one JSON-serialisable dict."""
    return _checked({
        'schema': SCHEMA, 'status': STATUS, 'flags': list(FLAGS),
        'limitations': list(LIMITATIONS),
        'read_status_legend': {
            'full_text': 'page or document read in full (or the relevant pages)',
            'excerpt': 'long excerpts, previews or partial reads',
            'abstract_or_snippet': 'abstract or search snippet only',
            'vendor_or_trade_page': 'vendor, producer or trade page (low confidence)',
            'memory_unverified': 'from the researcher\'s memory, unverified',
            'computed': 'computed by this module from published gauges',
        },
        'counts': {'products': len(_PRODUCT_LIST), 'facts': fact_count(),
                   'sources': len(_SOURCES)},
        'sources': {k: v.to_dict() for k, v in _SOURCES.items()},
        'general_foil_rolling': _json(GENERAL_FOIL_ROLLING),
        'general_defects': {'foil': _json(FOIL_DEFECTS), 'strip': _json(STRIP_DEFECTS)},
        'general_standards': _json(GENERAL_STANDARDS),
        'general_disagreements': _json(GENERAL_DISAGREEMENTS + MINOR_DISAGREEMENTS),
        'general_not_found': _json(GENERAL_NOT_FOUND),
        'battery_schedule_caveat': BATTERY_SCHEDULE_CAVEAT.to_dict(),
        'tension_lines': TENSION_LINES.to_dict(),
        'products': [p.to_dict() for p in _PRODUCT_LIST],
        'minor_products': _json(MINOR_PRODUCTS),
        'battery_grades': {
            'status': BG_STATUS, 'ordering_rule': ORDERING_RULE,
            'proposal_rules': {**PROPOSAL_RULE, 'fallback': PROPOSAL_FALLBACK_RULE,
                               'value': VALUE_RULE},
            'tables': {pid: [b.to_dict() for b in bands]
                       for pid, bands in GRADE_TABLES.items()},
            'headline_findings': _json(HEADLINE_FINDINGS), 'corrections': _json(CORRECTIONS),
            'gb_table_read': GB_TABLE_READ.to_dict(), 'temper_naming': TEMPER_NAMING.to_dict(),
            'conductivity': _json(CONDUCTIVITY), 'other_documents': _json(OTHER_GRADE_DOCUMENTS),
            'reasons': _json(GRADE_REASONS), 'temper_table': _json(TEMPER_TABLE),
            'strength_after_heating': _json(STRENGTH_AFTER_HEATING),
            'strength_after_heating_note': HEATING_NOTE.to_dict(),
            'gauges_in_use': _json(GAUGES_IN_USE), 'cell_case_stock': CELL_CASE_STOCK.to_dict(),
            'disagreements': _json(GRADE_DISAGREEMENTS), 'not_found': _json(GRADE_NOT_FOUND)},
        'process_temperatures': process_temperature_reference(),
    })


# --------------------------------------------------------------------------- check_pass
_TOL = 1e-9


def _verdict(value, lo, hi):
    if lo is None and hi is None:
        return 'NO_PUBLISHED_RANGE'
    if lo is not None and value < lo * (1 - _TOL) - 1e-15:
        return 'BELOW_PUBLISHED_RANGE'
    if hi is not None and value > hi * (1 + _TOL) + 1e-15:
        return 'ABOVE_PUBLISHED_RANGE'
    return 'WITHIN_PUBLISHED_RANGE'


def _weakest_of(objs):
    st = [_source_status(o) for o in objs if o is not None]
    st = [s for s in st if s is not None]
    return _weakest(st)


def _finding(item, value, unit, rng, basis, *, extra_sources=(), verdict=None, note=''):
    srcs = list(rng.sources) if rng is not None else []
    for o in extra_sources:
        for s in o.sources:
            if s not in srcs:
                srcs.append(s)
    lo = rng.low if rng is not None else None
    hi = rng.high if rng is not None else None
    if verdict is None:
        verdict = _verdict(value, lo, hi) if isinstance(value, float) else 'NO_PUBLISHED_RANGE'
    status = _weakest_of(([rng] if rng is not None else []) + list(extra_sources))
    return {'item': item, 'value': value, 'published_low': lo, 'published_high': hi,
            'unit': unit, 'verdict': verdict, 'basis': basis, 'sources': srcs,
            'read_status': status, 'note': note or (rng.note if rng is not None else '')}


def _none_finding(item, value, unit, basis):
    return {'item': item, 'value': value, 'published_low': None, 'published_high': None,
            'unit': unit, 'verdict': 'NO_PUBLISHED_RANGE', 'basis': basis, 'sources': [],
            'read_status': None, 'note': ''}


def _norm(s):
    return s.strip().upper()


def _general_foil_span():
    return GENERAL_FOIL_PER_PASS_SPAN.values[0]


def check_pass(product_id, entry_thickness_m, exit_thickness_m, *, exit_speed_m_s=None,
               mean_flow_stress_pa=None, doubled=None, is_final_pass=False, alloy=None,
               temper=None, surface=None):
    """Compare one pass with the published spans of a product (one finding per item).

    Verdicts only say where a value sits against the literature; they are not a judgement of the
    pass and nothing is plant-validated. ``surface`` ('two_side_bright' | 'one_side_bright')
    refines the rolled-mode check. Returns a list of JSON-serialisable dicts.
    """
    p = product(product_id)
    h0 = _num('entry_thickness_m', entry_thickness_m, positive=True, hi=0.02)
    h1 = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.02)
    if not h1 < h0:
        raise ValueError('exit_thickness_m must be < entry_thickness_m')
    speed = (None if exit_speed_m_s is None
             else _num('exit_speed_m_s', exit_speed_m_s, positive=True, hi=200.0))
    sigma = (None if mean_flow_stress_pa is None
             else _num('mean_flow_stress_pa', mean_flow_stress_pa, positive=True, hi=2e9))
    if doubled is not None and not isinstance(doubled, bool):
        raise ValueError('doubled must be None or bool')
    if not isinstance(is_final_pass, bool):
        raise ValueError('is_final_pass must be bool')
    for name, v in (('alloy', alloy), ('temper', temper)):
        if v is not None:
            _text(name, v)
    if surface is not None and surface not in SURFACES:
        raise ValueError(f'surface must be None or one of {SURFACES}')
    red = 1 - h1 / h0
    out = []
    fp = p.final_pass

    if is_final_pass:
        out.append(_finding('final_gauge', h1, 'm', p.final_gauge_m,
                            f'exit gauge against the published final gauge of {p.name}'))
    # per-pass reduction
    if p.per_pass_reduction is not None:
        out.append(_finding('per_pass_reduction', red, 'fraction', p.per_pass_reduction,
                            'pass reduction 1 - h_exit/h_entry against the product\'s published '
                            'per-pass span'))
    elif p.family in ('battery_electronics', 'packaging_household'):
        out.append(_finding('per_pass_reduction', red, 'fraction', _general_foil_span(),
                            'no product-specific span published; compared with the general '
                            'packaging foil per-pass span'))
    else:
        out.append(_none_finding('per_pass_reduction', red, 'fraction',
                                 'no per-pass reduction published for this product'
                                 + ('; published final-reduction windows are totals after the '
                                    'interanneal, not per pass'
                                    if p.family == 'heat_exchanger' else '')))
    if is_final_pass:
        if fp is not None and fp.reduction is not None:
            out.append(_finding('final_pass_reduction', red, 'fraction', fp.reduction,
                                'final-pass reduction against the published final-pass span'))
        else:
            out.append(_none_finding('final_pass_reduction', red, 'fraction',
                                     'no final-pass reduction published for this product'))
        if fp is not None and fp.entry_gauge_m is not None:
            out.append(_finding('final_pass_entry_gauge', h0, 'm', fp.entry_gauge_m,
                                'final-pass entry gauge against the published final passes'))
        else:
            out.append(_none_finding('final_pass_entry_gauge', h0, 'm',
                                     'no final-pass entry gauge published for this product'))
    # speed
    if speed is not None:
        rng, basis = None, ''
        if is_final_pass and fp is not None:
            if doubled is True and fp.doubled_speed_m_s is not None:
                rng, basis = fp.doubled_speed_m_s, 'doubled final-pass speed'
            elif doubled is not True and fp.speed_m_s is not None:
                rng, basis = fp.speed_m_s, 'single-sheet final-pass speed'
            elif fp.doubled_speed_m_s is not None and fp.speed_m_s is None:
                rng, basis = fp.doubled_speed_m_s, 'final-pass speed (published for the ' \
                                                   'doubled final pass)'
        if rng is None and not is_final_pass and p.pass_speed_m_s is not None:
            rng, basis = p.pass_speed_m_s, 'speed of the earlier (non-final) passes'
        if rng is None:
            out.append(_none_finding('exit_speed', speed, 'm/s',
                                     'no published speed for this kind of pass of this product'))
        else:
            out.append(_finding('exit_speed', speed, 'm/s', rng, basis))
    # rolled mode
    if doubled is not None:
        out.append(_mode_finding(p, doubled, is_final_pass, surface, h1))
    if doubled is False and is_final_pass and p.single_sheet_gauge_m is not None:
        out.append(_finding('single_sheet_final_gauge', h1, 'm', p.single_sheet_gauge_m,
                            'single-sheet final gauge against the published single-rolling '
                            'span'))
    # alloy / temper (band-aware where the product has a grade table: the exit gauge's band)
    band = _band_of(p.id, h1)
    band_opt = None
    if band is not None and alloy is not None:
        band_opt = next((o for o in band.options if _norm(o.alloy) == _norm(alloy)), None)
    alloy_names = {_norm(a.name) for a in p.alloys}
    if alloy is not None:
        listed = [a for a in p.alloys if _norm(a.name) == _norm(alloy)]
        if band_opt is not None:
            srcs = list(band_opt.option_sources())
            out.append({'item': 'alloy', 'value': alloy, 'published_low': None,
                        'published_high': None, 'unit': '', 'verdict': 'WITHIN_PUBLISHED_RANGE',
                        'basis': f'alloy is an option of the {band.label} band of the grade '
                                 'table (exit gauge of this pass)'
                                 + (f'; usual choice: {band_opt.usual.text}' if band_opt.usual
                                    else '; not a usual choice at this gauge'),
                        'sources': srcs,
                        'read_status': _weakest(_SOURCES[s].read_status for s in srcs),
                        'note': band_opt.note})
        elif band is not None:
            out.append({'item': 'alloy', 'value': alloy, 'published_low': None,
                        'published_high': None, 'unit': '', 'verdict': 'NO_PUBLISHED_RANGE',
                        'basis': f'alloy is not an option of the {band.label} band of the grade '
                                 'table' + (' (it is listed for the product at other gauges)'
                                            if listed else ''),
                        'sources': list(_union_sources(listed)),
                        'read_status': _weakest_of(listed), 'note': ''})
        else:
            known = _norm(alloy) in alloy_names
            out.append({'item': 'alloy', 'value': alloy, 'published_low': None,
                        'published_high': None, 'unit': '',
                        'verdict': 'WITHIN_PUBLISHED_RANGE' if known else 'NO_PUBLISHED_RANGE',
                        'basis': 'alloy listed for this product' if known
                        else 'alloy not listed for this product in the reports',
                        'sources': list(_union_sources(listed)),
                        'read_status': _weakest_of(listed), 'note': ''})
    if temper is not None:
        hits = [t for t in p.tempers if _norm(t.name) == _norm(temper)]
        hard_band = band is not None and 'H18' in band.options[0].temper_labels
        if hard_band and _norm(temper) in ('H18', 'H19'):
            srcs = list(_union_sources(hits + [TEMPER_NAMING]))
            out.append({'item': 'temper', 'value': temper, 'published_low': None,
                        'published_high': None, 'unit': '', 'verdict': 'WITHIN_PUBLISHED_RANGE',
                        'basis': f'H18 and H19 are both consistent with this product at the '
                                 f'{band.label} band (naming note)',
                        'sources': srcs, 'read_status': _weakest_of(hits + [TEMPER_NAMING]),
                        'note': TEMPER_NAMING.text})
        elif hard_band and hits:
            out.append({'item': 'temper', 'value': temper, 'published_low': None,
                        'published_high': None, 'unit': '', 'verdict': 'NO_PUBLISHED_RANGE',
                        'basis': f'temper listed for this product only by low-confidence pages; '
                                 f'the grade table of the {band.label} band has H18/H19 (the '
                                 'second survey treats soft collector foil as an error)',
                        'sources': list(_union_sources(hits)), 'read_status': _weakest_of(hits),
                        'note': ''})
        else:
            out.append({'item': 'temper', 'value': temper, 'published_low': None,
                        'published_high': None, 'unit': '',
                        'verdict': 'WITHIN_PUBLISHED_RANGE' if hits else 'NO_PUBLISHED_RANGE',
                        'basis': 'temper listed for this product' if hits
                        else 'temper not listed for this product in the reports',
                        'sources': list(_union_sources(hits)), 'read_status': _weakest_of(hits),
                        'note': ''})
    if sigma is not None:
        f = _band_flow_stress_finding(band, band_opt, alloy, sigma) if band is not None else None
        out.append(f or _flow_stress_finding(p, sigma, alloy, temper))
    return _checked(out)


_FLOW_TAIL = ('; INDICATOR ONLY: finished-product tensile strength is not the rolling flow '
              'stress')


def _band_flow_stress_finding(band, opt, alloy, sigma):
    """Flow stress against the band row: standard minimum to the top of the typical range."""
    opts = [opt] if opt is not None else ([] if alloy is not None else list(band.options))
    los, his, objs = [], [], []
    for o in opts:
        lo, hi = _rm_range(o)
        if lo is not None:
            los.append(lo)
        if hi is not None:
            his.append(hi)
        objs += ([o.standard_min_rm_pa] if o.standard_min_rm_pa else []) + _typ_rm_spans(o)
    if not los:
        return None
    lo, hi = min(los), (max(his) if his else None)
    scope = (f'alloy {opt.alloy} in the {band.label} band' if opt is not None
             else f'every option of the {band.label} band')
    rng = Range(lo, hi, 'Pa', _union_sources(objs),
                f'{scope}: standard minimum (else lowest typical) to the top of the typical '
                'producer range', 'span' if hi is not None else 'minimum', None, 'MPa')
    return _finding('mean_flow_stress_indicator', sigma, 'Pa', rng,
                    f'mean flow stress against the grade table, {scope}' + _FLOW_TAIL
                    + ('; no typical upper value is published, so only the minimum is checked'
                       if hi is None else ''), extra_sources=objs)


def _mode_finding(p, doubled, is_final_pass, surface, h1):
    note_src = (p.mode_note,) if p.mode_note is not None else ()
    base = {'item': 'rolled_mode', 'value': 'doubled' if doubled else 'single_sheet',
            'published_low': None, 'published_high': None, 'unit': '',
            'sources': list(_union_sources(note_src)), 'read_status': _weakest_of(note_src),
            'note': p.mode_note.text if p.mode_note is not None else ''}
    mode = p.rolled_mode
    if mode == 'not_published':
        return {**base, 'verdict': 'NO_PUBLISHED_RANGE',
                'basis': 'no rolling mode published for this product'}
    if doubled:
        if mode == 'single_sheet':
            return {**base, 'verdict': 'INCONSISTENT_WITH_PUBLISHED_MODE',
                    'basis': 'product is published as single-rolled'}
        if surface == 'two_side_bright':
            surf = SURFACE_FACT
            return {**base, 'verdict': 'INCONSISTENT_WITH_PUBLISHED_MODE',
                    'basis': 'a doubled pass leaves the foil-to-foil faces matt; two-side-bright '
                             'foil is rolled single-sheet',
                    'sources': list(_union_sources(note_src + (surf,))),
                    'read_status': _weakest_of(note_src + (surf,))}
        return {**base, 'verdict': 'WITHIN_PUBLISHED_RANGE',
                'basis': 'doubled rolling is published for this product'
                         + (' (gives one-side-bright foil)' if mode == 'either' else '')}
    if mode == 'doubled' and is_final_pass:
        return {**base, 'verdict': 'INCONSISTENT_WITH_PUBLISHED_MODE',
                'basis': 'the published final pass of this product is doubled'}
    if mode == 'either' and surface == 'one_side_bright' and is_final_pass:
        return {**base, 'verdict': 'INCONSISTENT_WITH_PUBLISHED_MODE',
                'basis': 'one-side-bright (bright/matt) foil comes from a doubled final pass'}
    return {**base, 'verdict': 'WITHIN_PUBLISHED_RANGE',
            'basis': 'single-sheet rolling is consistent with the published mode'
                     + (' (passes before the doubled pass are single-sheet)'
                        if mode == 'doubled' else '')}


def _flow_stress_finding(p, sigma, alloy, temper):
    entries = list(p.strength)
    scope = f'all published tensile data of {p.name}'
    if alloy is not None:
        entries = [s for s in entries if _norm(alloy) in {_norm(a) for a in s.alloys}]
        scope = f'published tensile data for alloy {alloy}'
        if temper is not None:
            narrowed = [s for s in entries
                        if _norm(temper) in {_norm(t) for t in s.temper.replace('/', ' ').split()}]
            if narrowed:
                entries, scope = narrowed, scope + f' temper {temper}'
    rms = [s.rm_pa for s in entries if s.rm_pa is not None]
    basis_tail = ('; INDICATOR ONLY: finished-product tensile strength is not the rolling flow '
                  'stress, and the span mixes minima, typical values and ranges')
    if not rms:
        return _none_finding('mean_flow_stress_indicator', sigma, 'Pa',
                             f'no published tensile strength ({scope})' + basis_tail)
    vals = [v for r in rms for v in (r.low, r.high) if v is not None]
    rng = Range(min(vals), max(vals), 'Pa', _union_sources(rms), 'span of published Rm '
                'numbers', 'span', None, 'MPa')
    f = _finding('mean_flow_stress_indicator', sigma, 'Pa', rng,
                 f'mean flow stress against the span of {scope}' + basis_tail,
                 extra_sources=rms)
    return f


# --------------------------------------------------------------------------- grade selection
ORDERING_RULE = (
    'Presentation order (a rule of this module, never a claim that one alloy is best): options '
    'the research calls the usual choice at this gauge first, then by evidence rating '
    '(strong, medium, weak, vendor_level, not_rated), then by strength (middle of the first '
    'typical range, else the standard minimum) from high to low, then by name. Options outside '
    'their published gauge span or usual only for another surface come after the others.')
PROPOSAL_RULE = {
    'standard': 'the usual standard-strength choice of the gauge band (first in the report\'s '
                'list)',
    'high_strength': 'the usual high-strength choice of the gauge band (first in the report\'s '
                     'list)',
}
PROPOSAL_FALLBACK_RULE = (
    'no usual choice of this grade is published for the band: the option of this grade with the '
    'highest standard minimum (ties: the report\'s order) is used, rated weak')
VALUE_RULE = ('value used: the middle of the first published typical tensile range for this '
              'alloy in this band; if none, the standard minimum (a lower bound: finished foil '
              'is usually above it), else the lowest published typical minimum')
_EV_RANK = {r: i for i, r in enumerate(EVIDENCE_RATINGS)}


def grade_bands(product_id):
    """The grade-table bands of a product (empty tuple when it has none)."""
    product(product_id)
    return GRADE_TABLES.get(product_id, ())


def _band_of(product_id, h):
    for b in grade_bands(product_id):
        if b.contains(h):
            return b
    return None


def gauge_band(product_id, final_gauge_m):
    """The grade-table band of ``final_gauge_m`` for a product, or an 'outside' result.

    Returns a JSON-serialisable dict: ``status`` 'IN_BAND' with ``band`` (the band record), or
    'OUTSIDE_PUBLISHED_BANDS' / 'NO_GRADE_TABLE' with ``band`` None and the reason.
    """
    p = product(product_id)
    h = _num('final_gauge_m', final_gauge_m, positive=True, hi=0.02)
    bands = grade_bands(product_id)
    out = {'product_id': p.id, 'final_gauge_m': h}
    if not bands:
        return _checked({**out, 'status': 'NO_GRADE_TABLE', 'band': None,
                         'reason': f'no gauge-by-gauge grade table was published for {p.name}'})
    b = _band_of(product_id, h)
    if b is None:
        lo = min(x.low_m for x in bands)
        hi = max(x.high_m for x in bands)
        side = 'below' if h < lo else 'above'
        return _checked({**out, 'status': 'OUTSIDE_PUBLISHED_BANDS', 'band': None,
                         'reason': f'{h * 1e6:.4g} µm is {side} every published band of '
                                   f'{p.name} ({lo * 1e6:.4g}–{hi * 1e6:.4g} µm)'})
    return _checked({**out, 'status': 'IN_BAND', 'band': b.to_dict(),
                     'band_id': b.id, 'band_label': b.label})


def _conductivity(alloy):
    for s in CONDUCTIVITY:
        if _norm(s.topic) == _norm(alloy):
            return s
    return None


def _typ_rm_spans(o):
    return [s.rm_pa for s in o.typical if s.rm_pa is not None]


def _rm_value(o):
    """(value, basis) per VALUE_RULE, or (None, '')."""
    for r in _typ_rm_spans(o):
        if r.bound in ('span', 'typical') and r.low is not None and r.high is not None:
            return 0.5 * (r.low + r.high), f'middle of the typical range {_fmt_range(r)}'
    if o.standard_min_rm_pa is not None:
        return o.standard_min_rm_pa.low, 'the standard minimum (a lower bound)'
    lows = [r.low for r in _typ_rm_spans(o) if r.low is not None]
    if lows:
        return min(lows), 'the lowest published typical minimum (a lower bound)'
    return None, ''


def _typ_range(o):
    """(low, high) over the typical producer values only (None where none is published)."""
    los = [r.low for r in _typ_rm_spans(o) if r.low is not None]
    his = [r.high for r in _typ_rm_spans(o) if r.high is not None and r.bound != 'minimum']
    return (min(los) if los else None), (max(his) if his else None)


def _rm_range(o):
    los, his = [], []
    if o.standard_min_rm_pa is not None:
        los.append(o.standard_min_rm_pa.low)
    for r in _typ_rm_spans(o):
        if r.low is not None:
            los.append(r.low)
        if r.high is not None and r.bound != 'minimum':
            his.append(r.high)
        elif r.high is not None and r.bound == 'minimum':
            los.append(r.high)
    lo = (o.standard_min_rm_pa.low if o.standard_min_rm_pa is not None
          else (min(los) if los else None))
    hi = max(his) if his else None
    return lo, hi


def _option_evidence(band, o):
    if o.usual is not None:
        return band.choice_evidence, 'the report\'s rating of the usual choice in this band'
    if o.standard_min_rm_pa is not None:
        return 'not_rated', ('not a usual choice; its standard minimum is rated '
                             f'{band.minima_evidence} in this band')
    return 'not_rated', 'not a usual choice; producer values only'


def _first(o, attr):
    for s in o.typical:
        r = getattr(s, attr)
        if r is not None:
            return r
    return None


def _option_row(band, o, h, req, surface):
    ev, ev_basis = _option_evidence(band, o)
    lo, hi = _rm_range(o)
    val, _ = _rm_value(o)
    if req is None:
        check = None
    else:
        guaranteed = o.standard_min_rm_pa.low if o.standard_min_rm_pa is not None else None
        best = max([v for v in (lo, hi, guaranteed) if v is not None], default=None)
        if guaranteed is not None and guaranteed >= req * (1 - _TOL):
            check = 'MEETS_REQUESTED_MINIMUM'
        elif best is None:
            check = 'NO_DATA'
        elif best < req * (1 - _TOL):
            check = 'BELOW_REQUESTED_MINIMUM'
        elif lo is not None and lo >= req * (1 - _TOL):
            check = 'MEETS_REQUESTED_MINIMUM'
        else:
            check = 'NOT_GUARANTEED'
    outside = o.gauge_m is not None and not (
        o.gauge_m.low * (1 - _BAND_TOL) <= h <= o.gauge_m.high * (1 + _BAND_TOL))
    surf_cond = o.usual_surface
    mismatch = surf_cond is not None and surface != surf_cond
    rp, a = _first(o, 'rp_pa'), _first(o, 'elongation')
    cond = _conductivity(o.alloy)
    srcs = list(o.option_sources())
    return {
        'alloy': o.alloy, 'grade': o.grade, 'temper_labels': list(o.temper_labels),
        'grade_names': list(o.grade_names),
        'standard_min_rm_pa': o.standard_min_rm_pa.low if o.standard_min_rm_pa else None,
        'standard_min_sources': list(o.standard_min_rm_pa.sources) if o.standard_min_rm_pa
        else [],
        'typical_rm_pa': list(_typ_range(o)), 'rm_range_pa': [lo, hi], 'rm_value_pa': val,
        'typical': [s.to_dict() for s in o.typical],
        'proof_strength_pa': [rp.low, rp.high] if rp else None,
        'elongation_fraction': [a.low, a.high, a.bound] if a else None,
        'conductivity_iacs_fraction': ([cond.values[0].low, cond.values[0].high]
                                       if cond else None),
        'conductivity_sources': list(cond.sources) if cond else [],
        'usual': o.usual is not None, 'usual_for': o.usual.text if o.usual else '',
        'usual_surface': surf_cond, 'surface_mismatch': mismatch,
        'outside_alloy_gauge_span': outside,
        'evidence': ev, 'evidence_basis': ev_basis,
        'requested_minimum_check': check,
        'below_requested_minimum': check == 'BELOW_REQUESTED_MINIMUM',
        'note': o.note, 'sources': srcs,
        'read_status': _weakest(_SOURCES[s].read_status for s in srcs) if srcs else None}


def _order_key(row):
    strength = row['rm_value_pa'] or row['standard_min_rm_pa'] or 0.0
    return (row['outside_alloy_gauge_span'] or row['surface_mismatch'], not row['usual'],
            _EV_RANK[row['evidence']], -strength, row['alloy'])


def grade_options(product_id, final_gauge_m, *, min_tensile_strength_pa=None, surface=None):
    """Every alloy option of the band of ``final_gauge_m`` (marked, never removed).

    Each option: temper label(s), standard minimum, typical producer range, proof strength,
    elongation, conductivity, grade names, usual choice and for what, evidence rating, sources,
    read status, and ``requested_minimum_check`` against ``min_tensile_strength_pa``
    (MEETS_REQUESTED_MINIMUM / NOT_GUARANTEED / BELOW_REQUESTED_MINIMUM / NO_DATA).
    The order is a presentation rule stated in ``ordering_rule``.
    """
    gb = gauge_band(product_id, final_gauge_m)
    req = (None if min_tensile_strength_pa is None else
           _num('min_tensile_strength_pa', min_tensile_strength_pa, positive=True, hi=2e9))
    if surface is not None and surface not in SURFACES:
        raise ValueError(f'surface must be None or one of {SURFACES}')
    out = {'product_id': gb['product_id'], 'final_gauge_m': gb['final_gauge_m'],
           'status': gb['status'], 'band_id': gb.get('band_id'),
           'band_label': gb.get('band_label'), 'reason': gb.get('reason', ''),
           'requested_min_tensile_strength_pa': req, 'surface': surface,
           'ordering_rule': ORDERING_RULE, 'options': [], 'band_facts': None,
           'literature_status': STATUS}
    if gb['status'] != 'IN_BAND':
        return _checked(out)
    band = _band_of(product_id, gb['final_gauge_m'])
    rows = [_option_row(band, o, gb['final_gauge_m'], req, surface) for o in band.options]
    rows.sort(key=_order_key)
    out['options'] = rows
    out['band_facts'] = {
        'usual_choice': band.usual_choice.to_dict(),
        'typical_producer': _json(band.typical_producer),
        'typical_cells': _json(band.typical_cells), 'evidence': band.evidence.to_dict(),
        'minima_evidence': band.minima_evidence, 'choice_evidence': band.choice_evidence,
        'elongation': _json(band.elongation), 'surface': _json(band.surface),
        'pinholes': _json(band.pinholes), 'notes': _json(band.notes),
        'temper_naming': TEMPER_NAMING.to_dict() if 'H18' in band.options[0].temper_labels
        else None,
        'gb_table_read': GB_TABLE_READ.to_dict() if any(o.standard_min_rm_pa
                                                        for o in band.options) else None}
    return _checked(out)


def _rp_ratio():
    """Computed Rp0.2/Rm ratios of the options that publish both at 15 µm (median, span)."""
    ratios, used = [], []
    for o in BAND_13_15.options:
        for s in o.typical:
            if s.rm_pa is not None and s.rp_pa is not None:
                rm = 0.5 * (s.rm_pa.low + s.rm_pa.high)
                rp = 0.5 * (s.rp_pa.low + s.rp_pa.high)
                ratios.append(rp / rm)
                used.append(s)
    ratios.sort()
    return statistics.median(ratios), (ratios[0], ratios[-1]), _union_sources(used)


def proposed_material(product_id, final_gauge_m, *, alloy=None, grade='standard',
                      surface=None):
    """One concrete material for the tool to use when the plant has not stated one.

    ``status`` is 'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT' when a proposal is made, else
    'NO_LITERATURE_PROPOSAL' with the reason. The rule applied is stated in ``rule``.
    """
    if grade not in GRADES:
        raise ValueError(f'grade must be one of {GRADES}')
    if alloy is not None:
        _text('alloy', alloy)
    if surface is not None and surface not in SURFACES:
        raise ValueError(f'surface must be None or one of {SURFACES}')
    gb = gauge_band(product_id, final_gauge_m)
    h = gb['final_gauge_m']
    base = {'product_id': gb['product_id'], 'final_gauge_m': h, 'grade': grade,
            'requested_alloy': alloy, 'surface': surface, 'band_id': gb.get('band_id'),
            'band_label': gb.get('band_label')}
    if gb['status'] != 'IN_BAND':
        return _checked({**base, 'status': 'NO_LITERATURE_PROPOSAL', 'reason': gb['reason'],
                         'rule': '', 'alloy': None})
    band = _band_of(product_id, h)

    def applicable(o):
        if o.gauge_m is not None and not (o.gauge_m.low * (1 - _BAND_TOL) <= h
                                          <= o.gauge_m.high * (1 + _BAND_TOL)):
            return False
        return o.usual_surface is None or o.usual_surface == surface

    if alloy is not None:
        hits = [o for o in band.options if _norm(o.alloy) == _norm(alloy)]
        if not hits:
            return _checked({**base, 'status': 'NO_LITERATURE_PROPOSAL', 'alloy': None,
                             'rule': 'requested alloy',
                             'reason': f'alloy {alloy} is not an option of the {band.label} band '
                                       f'({", ".join(o.alloy for o in band.options)})'})
        o, rule, ev = hits[0], f'the requested alloy {alloy}', _option_evidence(band, hits[0])[0]
    else:
        cands = [x for x in band.options if x.grade == grade and applicable(x)]
        usual = [x for x in cands if x.usual is not None]
        if usual:
            o, rule, ev = usual[0], PROPOSAL_RULE[grade], band.choice_evidence
        else:
            withmin = [x for x in cands if x.standard_min_rm_pa is not None]
            if not withmin:
                return _checked({**base, 'status': 'NO_LITERATURE_PROPOSAL', 'alloy': None,
                                 'rule': PROPOSAL_RULE[grade],
                                 'reason': f'no {grade.replace("_", "-")} option with a usual '
                                           f'choice or a standard minimum is published for the '
                                           f'{band.label} band'})
            top = max(x.standard_min_rm_pa.low for x in withmin)
            o = next(x for x in withmin if x.standard_min_rm_pa.low == top)
            rule, ev = PROPOSAL_FALLBACK_RULE, 'weak'
    val, val_basis = _rm_value(o)
    if val is None:
        val_basis = f'tensile strength not published for {o.alloy} in this band'
    lo, hi = _rm_range(o)
    rp = _first(o, 'rp_pa')
    if rp is not None:
        rp_val = 0.5 * (rp.low + rp.high) if rp.high is not None else rp.low
        rp_out = {'value_pa': rp_val, 'range_pa': [rp.low, rp.high], 'published': True,
                  'basis': f'published typical proof strength {_fmt_range(rp)}',
                  'sources': list(rp.sources)}
    elif any(t.startswith('H') for t in o.temper_labels) and val is not None:
        med, (rlo, rhi), rsrc = _rp_ratio()
        rlo_rm = lo if lo is not None else val
        rp_out = {'value_pa': _q(med * val),
                  'range_pa': [_q(rlo * rlo_rm), None if hi is None else _q(rhi * hi)],
                  'published': False, 'ratio_used': med, 'ratio_span': [rlo, rhi],
                  'basis': f'not published for {o.alloy} in this band; assumed Rp0.2 = '
                           f'{med:.3f} x Rm, the median Rp0.2/Rm ratio of the hard-foil grades '
                           f'that publish both at 15 µm (span {rlo:.3f}–{rhi:.3f}; computed); '
                           'the range applies the ratio span to the tensile range',
                  'sources': list(rsrc), 'read_status': 'computed'}
    else:
        rp_out = {'value_pa': None, 'range_pa': None, 'published': False,
                  'basis': f'not published for {o.alloy} in this band, and no assumption is '
                           'made for this temper', 'sources': []}
    a = _first(o, 'elongation')
    if a is not None:
        el = {'range_fraction': [a.low, a.high], 'bound': a.bound,
              'basis': f'published {_fmt_range(a)}', 'sources': list(a.sources)}
    elif band.elongation is not None:
        e0 = band.elongation.values[0]
        el = {'range_fraction': [e0.low, e0.high], 'bound': 'minimum',
              'basis': 'not published for this alloy; the band\'s standard elongation minima',
              'sources': list(band.elongation.sources)}
    else:
        el = {'range_fraction': None, 'bound': None, 'basis': 'not published', 'sources': []}
    cond = _conductivity(o.alloy)
    srcs = list(o.option_sources())
    hard = any(t.startswith('H') for t in o.temper_labels)
    notes = [f'Literature proposal for the {band.label} band; confirm or correct with the '
             'plant (alloy, temper, strength).']
    if hard:
        notes.append(TEMPER_NAMING.text)
    else:
        notes.append(f'{o.temper_labels[0]} is the finished temper reached after rolling; the '
                     'finished strength is not the rolling flow stress.')
    return _checked({
        **base, 'status': BG_STATUS, 'rule': rule, 'value_rule': VALUE_RULE,
        'alloy': o.alloy, 'option_grade': o.grade, 'temper': o.temper_labels[0],
        'temper_labels': list(o.temper_labels), 'grade_names': list(o.grade_names),
        'tensile_strength_pa': {'value_pa': val, 'range_pa': [lo, hi],
                                'standard_min_pa': (o.standard_min_rm_pa.low
                                                    if o.standard_min_rm_pa else None),
                                'basis': val_basis},
        'proof_strength': rp_out, 'elongation': el,
        'conductivity_iacs_fraction': ([cond.values[0].low, cond.values[0].high]
                                       if cond else None),
        'usual_for': o.usual.text if o.usual else '', 'evidence': ev,
        'evidence_basis': band.evidence.text, 'sources': srcs,
        'read_status': _weakest(_SOURCES[s].read_status for s in srcs) if srcs else None,
        'notes': notes})


def format_grade_options(product_id, final_gauge_m, *, min_tensile_strength_pa=None,
                         surface=None):
    """Plain-text options table and the two proposals (what the CLI prints)."""
    g = grade_options(product_id, final_gauge_m, min_tensile_strength_pa=min_tensile_strength_pa,
                      surface=surface)
    L = [f'{g["product_id"]} at {g["final_gauge_m"] * 1e6:.4g} µm: '
         + (f'band {g["band_label"]}' if g['status'] == 'IN_BAND' else g['reason'])]
    if g['status'] != 'IN_BAND':
        return '\n'.join(L) + '\n'

    def mpa(v):
        return '—' if v is None else f'{v * 1e-6:.0f}'

    hdr = ('alloy', 'grade', 'temper', 'GB min', 'typical Rm', 'Rp0.2', 'A %', '% IACS',
           'usual', 'evidence', 'sources')
    rows = []
    for o in g['options']:
        lo, hi = o['typical_rm_pa']
        typ = '—' if lo is None and hi is None else (
            f'{mpa(lo)}–{mpa(hi)}' if hi is not None else f'≥{mpa(lo)}')
        rp = o['proof_strength_pa']
        rps = '—' if not rp else (mpa(rp[0]) if rp[1] in (None, rp[0]) else
                                  f'{mpa(rp[0])}–{mpa(rp[1])}')
        el = o['elongation_fraction']
        els = '—' if not el else ((('≥' if el[2] == 'minimum' else '') + f'{el[0] * 100:g}')
                                  if el[1] in (None, el[0]) or el[2] == 'minimum'
                                  else f'{el[0] * 100:g}–{el[1] * 100:g}')
        c = o['conductivity_iacs_fraction']
        cs = '—' if not c else (f'{c[0] * 100:g}' if c[0] == c[1] else
                                f'{c[0] * 100:g}–{c[1] * 100:g}')
        usual = ('yes' + (f' ({o["usual_surface"].replace("_", "-")} only)'
                          if o['usual_surface'] else '')) if o['usual'] else ''
        mark = []
        if o['below_requested_minimum']:
            mark.append('BELOW REQUESTED MIN')
        elif o['requested_minimum_check'] == 'NOT_GUARANTEED':
            mark.append('min not guaranteed')
        if o['outside_alloy_gauge_span']:
            mark.append('outside alloy gauge')
        if lo is not None and hi is None and o['typical'] and all(
                t['rm_pa'] is None or t['rm_pa']['bound'] == 'minimum' for t in o['typical']):
            typ = f'≥{mpa(lo)}'
        rows.append((o['alloy'] + (' [' + ', '.join(mark) + ']' if mark else ''),
                     o['grade'].replace('_', '-'), '/'.join(o['temper_labels']),
                     mpa(o['standard_min_rm_pa']), typ, rps, els, cs, usual, o['evidence'],
                     ' '.join(o['sources'])))
    w = [max(len(str(r[i])) for r in rows + [hdr]) for i in range(len(hdr))]
    L.append('  '.join(h.ljust(w[i]) for i, h in enumerate(hdr)).rstrip())
    for r in rows:
        L.append('  '.join(str(c).ljust(w[i]) for i, c in enumerate(r)).rstrip())
    bf = g['band_facts']
    L.append(f'Usual choice: {bf["usual_choice"]["text"]} Evidence: {bf["evidence"]["text"]}')
    L.append(g['ordering_rule'])
    for grade in GRADES:
        p = proposed_material(product_id, final_gauge_m, grade=grade, surface=surface)
        if p['status'] != BG_STATUS:
            L.append(f'Proposal ({grade.replace("_", "-")}): none — {p["reason"]}')
            continue
        t = p['tensile_strength_pa']
        rng = t['range_pa']
        if t['value_pa'] is None:
            rm_txt = 'Rm not published for this option in this band'
        else:
            rtxt = (f'{mpa(rng[0])}–{mpa(rng[1])}' if rng[1] is not None
                    else f'≥{mpa(rng[0])}')
            rm_txt = f'Rm {mpa(t["value_pa"])} MPa used ({t["basis"]}; range {rtxt} MPa)'
        ps = p['proof_strength']
        rp_txt = ('Rp0.2 not published' if ps['value_pa'] is None else
                  f'Rp0.2 {mpa(ps["value_pa"])} MPa '
                  f'({"published" if ps["published"] else "assumed, " + ps.get("basis", "")})')
        L.append(f'Proposal ({grade.replace("_", "-")}): {p["alloy"]}-{p["temper"]}, {rm_txt}, '
                 f'{rp_txt}; evidence {p["evidence"]}; rule: {p["rule"]}; '
                 f'status {p["status"]}.')
    return '\n'.join(L) + '\n'


# --------------------------------------------------------------------------- check_thermal
THERMAL_COLLECTOR_PRODUCTS = ('battery_collector_foil', 'battery_thick_collector_foil',
                              'battery_carbon_coated_base_foil')
OIL_STANDS = ('roughing', 'intermediate', 'finishing')
SHEET_FAMILIES = ('heat_exchanger', 'litho', 'other_strip')


def process_temperature_reference():
    """The process-temperature reference as one JSON-serialisable dict."""
    return _checked({
        'status': STATUS, 'not_a_model': PT_NOT_A_MODEL,
        'headline_findings': _json(PT_HEADLINE), 'temperature_map': _json(TEMPERATURE_MAP),
        'rise_per_pass': _json(PT_RISE_PER_PASS), 'oil_properties': _json(OIL_PROPERTIES),
        'oil_what_goes_wrong': _json(OIL_WHAT_GOES_WRONG), 'material': _json(PT_MATERIAL),
        'roll_wear': _json(PT_ROLL_WEAR), 'surface_finish': _json(PT_SURFACE),
        'spray_overlap': SPRAY_OVERLAP.to_dict(), 'surface_note': PT_SURFACE_NOTE.to_dict(),
        'simulation_numbers': _json(PT_SIMULATION),
        'disagreements': _json(PT_DISAGREEMENTS), 'not_found': _json(PT_NOT_FOUND),
        'check_thermal_items': list(THERMAL_ITEMS)})


# --------------------------------------------------------------------------- SPEC17 B3, B4
# Appendix A.1 part B of docs/simulation-coverage-gaps.md, as printed (values are text; nothing
# is fitted and nothing is passed to a hardening law)
_ALLOY_GROUP_ROWS = (
    ('1235-H18 foil, 16 um', 'stress at 2 % strain 160 to 200 MPa over 1e-5 to 1e-2 /s; m about '
     '0.027; r = 0.2 / 1.5 / 1.1; transverse stress +10 %; fracture strain 0.023-0.028',
     'Micro-tensile, three directions; Yld2000-2d fit', 'EX', ('TM-LB1',)),
    ('AA1200 to strain 5', 'no saturation of flow stress or boundary spacing',
     'Tensile tests on rolled sheet, reductions 40-99 %', 'AB', ('TM-LB3',)),
    ('Hardness against reduction', 'A1050 peak at 80 %, about 43 HV; Al-0.69 mol% Fe peak at '
     '60 %, softening beyond 80 %', 'Cold rolled 40-95 % after 330 C anneal', 'EX', ('TM-LB2',)),
    ('As-rolled strength at 50 um by alloy; Fe in solution', '405-469 ppm as rolled without '
     'intermediate anneal; softening start 200-220 C (8079 / 8021), above 260 C (1050)',
     '1050, 1200, 8079, 8021, industrial route', 'EX (figure values partly unreadable)',
     ('TM-LB6',)),
    ('1100-H18 against temperature', '165 / 150 MPa at RT; 145 / 130 at 100 C; 125 at 150 C',
     'Long holding', 'AB / EX', ('PT-T31', 'PT-T39')),
    ('m against temperature, 1050-H14', '0.04 at 100 C, 0.07 at 200 C', 'Slow tensile tests',
     'EX', ('TM-LB10',)),
    ('1100-O Voce', 'sigma = 133 - 81*exp(-6.1*eps) MPa', 'Tension to 0.2', 'EX', ('TM-LB12',)),
    ('1050 annealed', 'E = 69.8 GPa, K = 144.6 MPa, n = 0.3', 'Tensile and Brinell', 'EX',
     ('TM-LB13',)),
    ('8021 foil, 40 um', '47.6 HV as rolled; softening from 180 C at 40 C/h',
     '92 % cold reduction', 'EX', ('TM-LB18',)),
    ('Pinhole onset', 'interface opens above 38 % cumulative reduction; 10-70 um foreign '
     'particles perforate 40 um foil', '8021 pilot rolling', 'EX', ('TM-LB15',)),
)
ALLOY_GROUP_LIMITATIONS = (
    'Values as printed in the gap study (Appendix A.1, part B); nothing is fitted and nothing is '
    'passed to a hardening law or a bite.',
    'The stage-IV hardening slope the engine uses for every alloy is wrong in sign for purified '
    'Al-Fe and high-purity grades beyond 80 % reduction [TM-LB2 EX] (gap study X2).')


def alloy_group_reference():
    """Hardening and softening data by alloy group (gap study Appendix A.1 part B), as printed."""
    rows = []
    for quantity, value, cond, read, srcs in _ALLOY_GROUP_ROWS:
        rows.append({'quantity': quantity, 'value': value, 'conditions': cond,
                     'read_tag': read,
                     'read_status': _weakest(_SOURCES[s].read_status for s in srcs),
                     'sources': list(srcs)})
    return _checked({'status': STATUS, 'rows': rows,
                     'limitations': list(ALLOY_GROUP_LIMITATIONS),
                     'sources': {s: _SOURCES[s].to_dict() for r in _ALLOY_GROUP_ROWS
                                 for s in r[4]}})


def plane_strain_factor_hill48(r_0, r_90):
    """Plane-strain yield / uniaxial yield under Hill's 1948 criterion.

    [D, re-derived in SPEC17] Hill 1948 in plane stress on the principal axes of anisotropy:
    ``sx^2 - (2*r_0/(1+r_0))*sx*sy + (r_0*(1+r_90)/(r_90*(1+r_0)))*sy^2 = s_0^2`` (``s_0`` the
    uniaxial yield in the rolling direction). Plane strain in the width direction means
    ``d(eps_y) ~ df/d(sy) = 0``, i.e. ``sy = sx*r_90/(1+r_90)``; substituting gives
    ``sx/s_0 = sqrt((1+r_0)(1+r_90)/(1+r_0+r_90))``. Rolling adds a hydrostatic stress, which a
    pressure-independent criterion ignores. ``r_0 = r_90 = R`` gives ``(1+R)/sqrt(1+2R)``;
    ``R = 1`` gives the isotropic ``2/sqrt(3)``.
    """
    r0 = _num('r_0', r_0, positive=True, hi=100.0)
    r90 = _num('r_90', r_90, positive=True, hi=100.0)
    return math.sqrt((1 + r0) * (1 + r90) / (1 + r0 + r90))


ANISOTROPY_R_VALUES = (0.2, 1.5, 1.1)          # 16 um 1235-H18 [TM-LB1 EX]
HILL_POOR_FOR_ALUMINIUM = ('Hill-type criteria are known to be poor for aluminium [M, from '
                           'memory, as in the report].')


def anisotropy_reference():
    """Measured r-values of one 16 um 1235-H18 foil and the plane-strain factors they imply."""
    r0, r45, r90 = ANISOTROPY_R_VALUES
    iso = 2 / math.sqrt(3)
    rbar = (r0 + 2 * r45 + r90) / 4
    cases = (
        ('isotropic (the engine\'s value)', 'isotropic', iso, '[D]'),
        ('normal anisotropy R = 0.2 (the report\'s bound)', 'normal_r_0_2',
         plane_strain_factor_hill48(r0, r0), '[computed in the report; D]'),
        ('Hill 1948 with r_0 = 0.2 and r_90 = 1.1', 'hill48_r0_r90',
         plane_strain_factor_hill48(r0, r90), '[D, re-derived in SPEC17]'),
        (f'mean normal anisotropy (r_0 + 2 r_45 + r_90)/4 = {rbar:.4g}', 'mean_normal',
         plane_strain_factor_hill48(rbar, rbar), '[D, re-derived in SPEC17]'))
    return _checked({
        'status': STATUS,
        'r_values': {'values': list(ANISOTROPY_R_VALUES), 'transverse_stress_higher_fraction': 0.1,
                     'material': '1235-H18 foil, 16 um', 'sources': ['TM-LB1'],
                     'read_status': _SOURCES['TM-LB1'].read_status,
                     'note': ('The report prints them for "three directions"; 0 / 45 / 90 '
                              'degrees in that order is an assumption')},
        'factors': [{'label': lab, 'id': i, 'factor': f, 'relative_to_isotropic': f / iso - 1,
                     'tag': tag} for lab, i, f, tag in cases],
        'caveat': HILL_POOR_FOR_ALUMINIUM,
        'engine': 'The engine keeps the isotropic 2/sqrt(3); no bite uses these factors.'})


def _alloy_md():
    a = alloy_group_reference()
    L = ['## Alloy groups: hardening and softening data found', '',
         'From the thermal, material and dynamics gap report (sources `TM-`; gap study Appendix '
         'A.1, part B), values as printed.', '',
         '| Quantity | Value | Conditions | Read | Sources |', '|---|---|---|---|---|']
    for r in a['rows']:
        L.append(f'| {_esc(r["quantity"])} | {_esc(r["value"])} | {_esc(r["conditions"])} | '
                 f'{_esc(r["read_tag"])} | {", ".join(r["sources"])} |')
    L += [''] + [f'- {x}' for x in a['limitations']] + ['']
    n = anisotropy_reference()
    rv = n['r_values']
    L += ['## Anisotropy and the plane-strain factor', '',
          f'Measured r-values of {rv["material"]}: {" / ".join(f"{x:g}" for x in rv["values"])}; '
          f'transverse stress about 10 % higher [TM-LB1; {rv["read_status"]}]. {rv["note"]}.', '',
          'Plane-strain factor (plane-strain yield / uniaxial yield) under Hill\'s 1948 '
          'criterion, `sqrt((1 + r_0)(1 + r_90)/(1 + r_0 + r_90))`:', '',
          '| Case | Factor | Against isotropic | Tag |', '|---|---|---|---|']
    for f in n['factors']:
        L.append(f'| {_esc(f["label"])} | {f["factor"]:.6f} | '
                 f'{100 * f["relative_to_isotropic"]:+.1f} % | {f["tag"]} |')
    L += ['', f'{n["caveat"]} {n["engine"]}', '']
    return L


THERMAL_ITEMS = ('coil_temperature_entering_final_pass', 'coil_temperature_leaving_final_pass',
                 'oil_supply_temperature', 'oil_viscosity_40c', 'strip_heat_fraction',
                 'spray_heat_transfer_coefficient', 'thermal_crown', 'stripe_height_on_diameter',
                 'bite_contact_conductance')


def _limit_finding(item, value, unit, limit, basis, note=''):
    v = ('ABOVE_PUBLISHED_LIMIT' if value > limit.high * (1 + _TOL) + 1e-15
         else 'WITHIN_PUBLISHED_RANGE')
    return _finding(item, value, unit, limit, basis + ' (a published limit)', verdict=v,
                    note=note or limit.note)


def format_temperature_map():
    """Plain-text temperature map (what ``--temperatures`` prints)."""
    L = ['Process temperatures in foil rolling (literature; ' + PT_NOT_A_MODEL + ')']
    for r in TEMPERATURE_MAP:
        L.append(f'- {r.name}: {r.typical.text} [{", ".join(r.typical.sources)}]')
        if r.limit is not None:
            L.append(f'    limit: {r.limit.text} [{", ".join(r.limit.sources)}]')
        L.append(f'    reason: {r.reason.text}')
    return '\n'.join(L) + '\n'


def check_thermal(product_id, *, coil_temperature_entering_final_pass_c=None,
                  coil_temperature_leaving_final_pass_c=None, oil_supply_temperature_c=None,
                  stand='finishing', oil_viscosity_40c_m2_s=None, strip_heat_fraction=None,
                  spray_htc_w_m2k=None, thermal_crown_m=None, stripe_height_diameter_m=None,
                  bite_contact_conductance_w_m2k=None):
    """Compare supplied process temperatures and thermal inputs with the literature.

    One finding per supplied value, shaped as in ``check_pass``; verdicts as there plus
    ``ABOVE_PUBLISHED_LIMIT`` for a published limit. Temperatures in °C, other values SI.
    Battery coil limits [PT-T1, PT-T2] apply only to the collector-type battery products
    (``THERMAL_COLLECTOR_PRODUCTS``); the basis says which range was used. Literature
    comparison only: nothing here is a model or a validation.
    """
    p = product(product_id)
    if stand not in OIL_STANDS:
        raise ValueError(f'stand must be one of {OIL_STANDS}')
    vals = {}
    for name, v, kw in (
            ('coil_temperature_entering_final_pass_c', coil_temperature_entering_final_pass_c,
             dict(hi=700)),
            ('coil_temperature_leaving_final_pass_c', coil_temperature_leaving_final_pass_c,
             dict(hi=700)),
            ('oil_supply_temperature_c', oil_supply_temperature_c, dict(hi=400)),
            ('oil_viscosity_40c_m2_s', oil_viscosity_40c_m2_s, dict(positive=True, hi=1e-3)),
            ('strip_heat_fraction', strip_heat_fraction, dict(hi=1.0)),
            ('spray_htc_w_m2k', spray_htc_w_m2k, dict(positive=True, hi=1e7)),
            ('thermal_crown_m', thermal_crown_m, dict(hi=0.01)),
            ('stripe_height_diameter_m', stripe_height_diameter_m, dict(hi=0.01)),
            ('bite_contact_conductance_w_m2k', bite_contact_conductance_w_m2k,
             dict(positive=True, hi=1e9))):
        if v is not None:
            vals[name] = _num(name, v, **kw)
    if 'strip_heat_fraction' in vals and vals['strip_heat_fraction'] < 0:
        raise ValueError('strip_heat_fraction must be >= 0')
    collector = p.id in THERMAL_COLLECTOR_PRODUCTS
    battery = p.id in GRADE_TABLES
    out = []
    v = vals.get('coil_temperature_entering_final_pass_c')
    if v is not None:
        if collector:
            out.append(_limit_finding('coil_temperature_entering_final_pass', v, 'degC',
                                      COIL_IN_FINAL_LIMIT, 'battery collector foil: coil '
                                      'entering the final pass ≤75 °C [PT-T1]'))
        else:
            out.append(_none_finding('coil_temperature_entering_final_pass', v, 'degC',
                                     'no entry-coil temperature published for this product (the '
                                     '≤75 °C limit is for battery collector foil)'))
    v = vals.get('coil_temperature_leaving_final_pass_c')
    if v is not None:
        if collector:
            f = _limit_finding('coil_temperature_leaving_final_pass', v, 'degC',
                               COIL_OUT_FINAL_LIMIT, 'battery collector foil: coil off the final '
                               'pass ≤80 °C [PT-T1, PT-T2]')
            if v > COIL_OUT_FINAL_LIMIT_LOOSE.high:
                f['note'] = ('above 90 °C, the looser limit: elongation decays with time for '
                             'weeks (a 98 °C coil for over 60 days) [PT-T1, PT-T2]')
            out.append(f)
        elif p.family in SHEET_FAMILIES:
            f = _finding('coil_temperature_leaving_final_pass', v, 'degC', COIL_OUT_SHEET_TROUBLE,
                         'sheet gauge: no stated limit; trouble above 150–160 °C [PT-T3]',
                         verdict=('ABOVE_PUBLISHED_LIMIT' if v > COIL_OUT_SHEET_TROUBLE.low
                                  else 'WITHIN_PUBLISHED_RANGE'))
            out.append(f)
        else:
            out.append(_none_finding('coil_temperature_leaving_final_pass', v, 'degC',
                                     'no coil temperature limit published for this product'
                                     + (' (pouch and tab foil: none found; the 80 °C limit is '
                                        'for collector foil)' if battery else '')))
    v = vals.get('oil_supply_temperature_c')
    if v is not None:
        rng = {'roughing': OIL_ROUGHING, 'intermediate': OIL_INTERMEDIATE,
               'finishing': OIL_FINISHING_BATTERY if battery else OIL_FINISHING}[stand]
        basis = (f'oil supply, {stand}'
                 + (', battery foil [PT-T1, PT-T6]' if stand == 'finishing' and battery else ''))
        if v > OIL_CAP_FOIL.high:
            out.append(_finding('oil_supply_temperature', v, 'degC', OIL_CAP_FOIL,
                                'above the 71 °C legal cap for foil mills in one US rule (vapour '
                                'emissions) [PT-T13]', verdict='ABOVE_PUBLISHED_LIMIT',
                                extra_sources=(rng,)))
        else:
            f = _finding('oil_supply_temperature', v, 'degC', rng, basis)
            if v < OIL_WINDOW_PLANT.low:
                f['note'] = ('below 38 °C: ladder defect at one plant (window 38–55 °C) '
                             '[PT-T3]; oil too cold gives a thick film and stain after anneal '
                             '[PT-T8]')
            out.append(f)
    v = vals.get('oil_viscosity_40c_m2_s')
    if v is not None:
        out.append(_finding('oil_viscosity_40c', v, 'm^2/s', VISC_40C,
                            'rolling-oil kinematic viscosity at 40 °C'))
    v = vals.get('strip_heat_fraction')
    if v is not None:
        out.append(_finding('strip_heat_fraction', v, 'fraction', HEAT_STRIP_SHARE,
                            'strip share of the heat against the only measured foil-mill '
                            'partition (abstract only; a net balance, not necessarily the split '
                            'inside the bite) [PT-T16]'))
    v = vals.get('spray_htc_w_m2k')
    if v is not None:
        f = _finding('spray_heat_transfer_coefficient', v, 'W/m^2K', SPRAY_ROLL,
                     'kerosene spray on a work roll, SIMULATED 2.5–4.3 kW/m²K [PT-T18]; no '
                     'measured value on a roll was found')
        f['note'] = ('wider published values: 4.65–5.5 kW/m²K in a cold-mill model example '
                     '(coolant not named) [PT-T20]; about 5–13 kW/m²K computed from a plate test '
                     '[PT-T19]')
        out.append(f)
    v = vals.get('thermal_crown_m')
    if v is not None:
        out.append(_limit_finding('thermal_crown', v, 'm', THERMAL_CROWN_MAX,
                                  'foil-mill thermal crown, 30 µm maximum from measured values '
                                  '[PT-T25]; diameter or radius not stated'))
    v = vals.get('stripe_height_diameter_m')
    if v is not None:
        out.append(_finding('stripe_height_on_diameter', v, 'm', ZONE_AUTHORITY,
                            'against the simulated zone-cooling authority, ±3.6 to ±4.2 µm on '
                            'diameter 20 revolutions after a zone change [PT-T18]'))
    v = vals.get('bite_contact_conductance_w_m2k')
    if v is not None:
        f = _finding('bite_contact_conductance', v, 'W/m^2K', CONTACT_MODELS,
                     'bite contact conductance used in aluminium models, 25–40 kW/m²K [PT-T34]')
        f['note'] = 'measured values span 7–800 kW/m²K [PT-T34]'
        out.append(f)
    return _checked(out)


# --------------------------------------------------------------------------- nearest schedules
def nearest_published_schedules(product_id, entry_thickness_m, exit_thickness_m, n=3):
    """The published single passes of a product closest in log-gauge to a given pass.

    Distance ``sqrt((ln h0 - ln h0_pub)**2 + (ln h1 - ln h1_pub)**2)``; a published range
    contributes its nearest point. Reductions are computed (per sheet for doubled passes).
    """
    p = product(product_id)
    h0 = _num('entry_thickness_m', entry_thickness_m, positive=True, hi=0.02)
    h1 = _num('exit_thickness_m', exit_thickness_m, positive=True, hi=0.02)
    if not h1 < h0:
        raise ValueError('exit_thickness_m must be < entry_thickness_m')
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n must be an int >= 1')

    def gap(x, pair):
        lo, hi = pair
        return 0.0 if lo <= x <= hi else min(abs(math.log(x / lo)), abs(math.log(x / hi)))

    cands = []
    for s in p.schedules:
        g, red, passes = s.gauges(), s.reductions(), s.passes()
        for i in range(s.steps()):
            if passes[i] != 1:
                continue
            d = math.hypot(gap(h0, g[i]), gap(h1, g[i + 1]))
            cands.append({
                'schedule': s.label, 'step': i, 'entry_m': list(g[i]), 'exit_m': list(g[i + 1]),
                'reduction': list(red[i]), 'doubled': s.is_doubled(i),
                'log_gauge_distance': d, 'alloy': s.alloy, 'sources': list(s.sources),
                'read_status': 'computed', 'source_read_status': _source_status(s),
                'note': s.note})
    cands.sort(key=lambda c: (c['log_gauge_distance'], c['schedule'], c['step']))
    return _checked(cands[:n])


# --------------------------------------------------------------------------- markdown
def _fmt(x):
    if x == 0:
        return '0'
    s = f'{float(f"{x:.9g}"):.6g}'
    if 'e' in s:
        s = f'{x:.6f}'.rstrip('0').rstrip('.')
    return s


def _disp(r):
    if r.display_unit:
        return r.display_unit
    return {'m': 'um' if max(v for v in (r.low, r.high) if v is not None) < 1e-3 else 'mm',
            'Pa': 'MPa', 'fraction': '%', 'm/s': 'm/min', 'N/m': 'mN/m', '1/m^2': 'per_m2',
            'kg/m^2': 'g/m2'}[r.unit]


def _fmt_range(r, *, decimals=None):
    d = _disp(r)
    k, label = DISPLAY[d][1], DISPLAY[d][2]

    def f(v):
        return f'{v / k:.{decimals}f}' if decimals is not None else _fmt(v / k)
    lo = None if r.low is None else f(r.low)
    hi = None if r.high is None else f(r.high)
    if lo is not None and hi is not None:
        if lo == hi:
            txt = (('≥' if r.bound == 'minimum' else '≤' if r.bound == 'maximum' else '')
                   + lo)
        else:
            txt = ('≥' if r.bound == 'minimum' else '') + f'{lo}–{hi}'
    elif lo is not None:
        txt = '≥' + lo
    else:
        txt = '≤' + hi
    return f'{txt} {label}'


def _cite(obj):
    if not obj.sources:
        return f' [{obj.read_status}]' if obj.read_status else ''
    s = ', '.join(obj.sources)
    if obj.read_status == 'computed':
        return f' [computed from {s}]'
    if obj.read_status:
        return f' [{s}; {obj.read_status}]'
    return f' [{s}]'


def _rng_cell(r, decimals=None):
    return '—' if r is None else _fmt_range(r, decimals=decimals) + _cite(r)


def _esc(t):
    return t.replace('|', '\\|')


def _stmt_lines(stmts):
    return [f'- {s.text}{_cite(s)}' for s in stmts]


def _gauge_txt(pair, unit):
    lo, hi = pair
    if unit == 'auto':
        unit = 'mm' if lo >= 1e-3 else 'um'
    k, label = DISPLAY[unit][1], DISPLAY[unit][2]
    if unit == 'mm':
        f = lambda v: f'{v / k:.4g}' if v / k >= 1 else f'{v / k:.3f}'.rstrip('0').rstrip('.')
    else:
        f = lambda v: _fmt(v / k)
    return (f(lo) if lo == hi else f'{f(lo)}–{f(hi)}') + f' {label}'


def _pct(lo, hi):
    return f'{lo * 100:.1f} %' if abs(hi - lo) < 1e-12 else f'{lo * 100:.1f}–{hi * 100:.1f} %'


def _schedule_md(s):
    head = f'**{s.label}**' + (f' ({s.alloy})' if s.alloy else '') + _cite(s)
    if s.note:
        head += f'. {s.note[0].upper()}{s.note[1:]}.'
    lines = [head, '',
             '| Step | Entry | Exit | Passes | Reduction | Speed |', '|---|---|---|---|---|---|']
    g, red, passes = s.gauges(), s.reductions(), s.passes()
    rs = 'published' if s.published_reductions is not None else 'computed'
    for i in range(s.steps()):
        dbl = '2×' if s.is_doubled(i) else ''
        n = passes[i]
        ntxt = 'not stated' if n is None else str(n)
        r = _pct(*red[i]) + f' ({rs}'
        if n not in (1, None):
            r += f'; mean {_pct(1 - (1 - red[i][0]) ** (1 / n), 1 - (1 - red[i][1]) ** (1 / n))}'
            r += ' per pass'
        r += ')'
        sp = '—' if s.speeds_m_s is None else f'{_fmt(s.speeds_m_s[i] * 60)} m/min'
        entry = dbl + _gauge_txt(g[i], s.display_unit)
        if s.published_reductions is not None and i > 0:
            entry += ' (computed)'
        ex = dbl + _gauge_txt(g[i + 1], s.display_unit)
        if s.published_reductions is not None:
            ex += ' (computed)'
        lines.append(f'| {i + 1} | {entry} | {ex} | {ntxt} | {r} | {sp} |')
    return lines + ['']


def _alloy_list(p, limit=8):
    names = []
    for a in p.alloys:
        if a.name not in names:
            names.append(a.name)
    txt = ', '.join(names[:limit]) + (', …' if len(names) > limit else '')
    return txt + _cite_union(p.alloys)


def _cite_union(objs):
    src = _union_sources(objs)
    return f' [{", ".join(src)}]' if src else ''


def _mode_txt(p):
    return {'single_sheet': 'single', 'doubled': 'doubled', 'either': 'single or doubled',
            'not_published': 'not published'}[p.rolled_mode]


def _ppr_txt(p):
    if p.per_pass_reduction is not None:
        return _rng_cell(p.per_pass_reduction, decimals=1)
    if p.family in ('battery_electronics', 'packaging_household'):
        return 'not published (general foil span applies)'
    return 'not published'


def _product_md(p, n):
    L = [f'## {n}. {p.name} (`{p.id}`)', '',
         f'Family: {p.family}. Rolled: {_mode_txt(p)}.'
         + (f' {p.mode_note.text}{_cite(p.mode_note)}' if p.mode_note else ''), '']
    L += ['### Gauge', '', f'- Final gauge: {_rng_cell(p.final_gauge_m)}'
          + (f'. {p.final_gauge_m.note[0].upper()}{p.final_gauge_m.note[1:]}.'
             if p.final_gauge_m.note else '')]
    L += _stmt_lines(p.common_gauges)
    if p.single_sheet_gauge_m is not None:
        L.append(f'- Single-sheet final gauge: {_rng_cell(p.single_sheet_gauge_m)}')
    L += ['', '### Alloys and why', '', '| Alloy | Role | Sources |', '|---|---|---|']
    L += [f'| {_esc(a.name)} | {_esc(a.text)} | {", ".join(a.sources)} |' for a in p.alloys]
    L += ['', '### Tempers and properties', '']
    L += [f'- {t.name}: {t.text}{_cite(t)}' for t in p.tempers]
    if p.strength:
        L += ['', '| Alloy | Temper | Condition | Grade | Rm | Rp0.2 | Elongation | Note |'
              ' Sources |', '|---|---|---|---|---|---|---|---|---|']
        for s in p.strength:
            def c(r):
                return '—' if r is None else _fmt_range(r)
            L.append(f'| {_esc(", ".join(s.alloys))} | {_esc(s.temper)} | {_esc(s.condition)} | '
                     f'{s.grade.replace("_", "-") or "—"} | {c(s.rm_pa)} | {c(s.rp_pa)} | '
                     f'{c(s.elongation)} | {_esc(s.note) or "—"} | {", ".join(s.sources)} |')
    L.append('')
    route = (p.per_pass_reduction, p.pass_speed_m_s, p.foil_stock, p.annealing, p.route,
             p.schedules)
    if any(route):
        L += ['### Rolling route and schedules', '']
        if p.per_pass_reduction is not None:
            L.append(f'- Per-pass reduction span: {_rng_cell(p.per_pass_reduction, 1)}. '
                     f'{p.per_pass_reduction.note[0].upper()}{p.per_pass_reduction.note[1:]}.')
        if p.pass_speed_m_s is not None:
            L.append(f'- Pass speed: {_rng_cell(p.pass_speed_m_s)}. '
                     f'{p.pass_speed_m_s.note[0].upper()}{p.pass_speed_m_s.note[1:]}.')
        L += _stmt_lines(p.foil_stock + p.annealing + p.route)
        L.append('')
        for s in p.schedules:
            L += _schedule_md(s)
    if p.final_pass is not None:
        fp = p.final_pass
        L += ['### Final pass', '']
        for label, r, dec in (('Entry gauge', fp.entry_gauge_m, None),
                              ('Reduction', fp.reduction, 1),
                              ('Speed, single-sheet', fp.speed_m_s, None),
                              ('Speed, doubled final pass', fp.doubled_speed_m_s, None)):
            if r is not None:
                L.append(f'- {label}: {_rng_cell(r, dec)}' + (f'. {r.note[0].upper()}'
                                                             f'{r.note[1:]}.' if r.note else ''))
        L += _stmt_lines(fp.notes)
        L.append('')
    rolls = p.work_roll_roughness + p.rolls_and_oil + p.surface
    if rolls:
        L += ['### Rolls, oil and surface', '']
        L += _stmt_lines(rolls)
        L.append('')
    quality = (('Thickness tolerance', p.thickness_tolerance),
               ('Flatness', p.flatness_requirement), ('Wettability', p.wettability),
               ('Pinholes', p.pinholes), ('Other', p.other_requirements))
    if any(q for _, q in quality):
        L += ['### Quality requirements', '']
        for label, q in quality:
            for s in q:
                L.append(f'- {label}: {s.text}{_cite(s)}')
        L.append('')
    L += ['### Named band and streak defects', '']
    if p.named_defects is FOIL_DEFECTS:
        L.append('- The EAFA foil-surface defects in the general reference apply (rolling '
                 'stripes, heat stripes, gloss difference, broken matt, chatter marks, '
                 'grooves) [PK-S7].')
    elif p.named_defects is STRIP_DEFECTS:
        L.append('- The general cold-rolling streak causes in the general reference apply '
                 '(rolled-in dirt and black streaks, herringbone, heat stripes, rolling stripes, '
                 'smut) [HX-S33, HX-S34b, HX-S22].')
    elif p.named_defects:
        L += ['| Defect | Appearance | Published cause | Sources |', '|---|---|---|---|']
        L += [f'| {_esc(d.name)} | {_esc(d.appearance)} | {_esc(d.published_cause)} | '
              f'{", ".join(d.sources)} |' for d in p.named_defects]
    else:
        L.append('- None named in the reports.')
    L.append('')
    if p.standards:
        L += ['### Standards', '']
        L += [f'- {s.name}: {s.text}{_cite(s)}' for s in p.standards]
        L.append('')
    if p.caveats:
        L += ['### Caveats', '']
        L += _stmt_lines(p.caveats)
        L.append('')
    L += [f'Key requirement: {p.key_requirement.text}{_cite(p.key_requirement)}', '']
    if p.evidence:
        L += [f'Evidence: ' + ' '.join(f'{s.text}{_cite(s)}' for s in p.evidence), '']
    if p.id in GRADE_TABLES:
        L += ['Alloy and temper by gauge: see "Battery foil: alloy and temper by gauge" above.',
              '']
    return L


def _general_md():
    L = ['## General foil-rolling reference', '']
    topics = []
    for s in GENERAL_FOIL_ROLLING:
        if s.topic not in topics:
            topics.append(s.topic)
    for t in topics:
        L += [f'### {t.replace("_", " ").capitalize()}', '']
        for s in GENERAL_FOIL_ROLLING:
            if s.topic == t:
                txt = f'- {s.text}{_cite(s)}'
                if s.read_status == 'computed':
                    txt = f'- {_rng_cell(s.values[0], 1)}: {s.text}'
                L.append(txt)
        L.append('')
    L += ['### Foil surface defects (EAFA catalogue)', '',
          '| Defect | Appearance | Published cause | Sources |', '|---|---|---|---|']
    L += [f'| {d.name} | {_esc(d.appearance)} | {_esc(d.published_cause)} | '
          f'{", ".join(d.sources)} |' for d in FOIL_DEFECTS]
    L += ['', '### General cold-rolling streak causes (no fin-stock-specific study found)', '',
          '| Defect | Appearance | Published cause | Sources |', '|---|---|---|---|']
    L += [f'| {d.name} | {_esc(d.appearance)} | {_esc(d.published_cause)} | '
          f'{", ".join(d.sources)} |' for d in STRIP_DEFECTS]
    L += ['', '### Standards', '']
    L += [f'- {s.name}: {s.text}{_cite(s)}' for s in GENERAL_STANDARDS]
    L.append('')
    return L


_BC = 'battery_collector_foil'


def _mpa(v):
    return '—' if v is None else f'{v * 1e-6:.4g}'


def _band_min_txt(b):
    have = [f'{o.alloy} {_mpa(o.standard_min_rm_pa.low)}' for o in b.options
            if o.standard_min_rm_pa is not None]
    none = [o.alloy for o in b.options if o.standard_min_rm_pa is None
            and o.note.startswith(_NO_GB)]
    txt = '; '.join(have) if have else 'none'
    if none and have:
        txt += f'; {", ".join(none)} —'
    return txt + (' [BG-G2]' if have else '')


def _opt_md_row(row):
    typ = '; '.join(
        f'{_esc(", ".join(t["alloys"]))}: '
        + ' / '.join(x for x in (
            _fmt_range(_range_from(t['rm_pa'])) if t['rm_pa'] else '',
            ('Rp0.2 ' + _fmt_range(_range_from(t['rp_pa']))) if t['rp_pa'] else '',
            ('A ' + _fmt_range(_range_from(t['elongation']))) if t['elongation'] else '')
            if x) + f' ({_esc(t["condition"])}) [{", ".join(t["sources"])}]'
        for t in row['typical']) or '—'
    c = row['conductivity_iacs_fraction']
    ctxt = '—' if not c else (f'{c[0] * 100:g}' if c[0] == c[1] else
                              f'{c[0] * 100:g}–{c[1] * 100:g}')
    usual = '—'
    if row['usual']:
        usual = _esc(row['usual_for'])
    note = ('; '.join(x for x in (row['note'], 'grade names: ' + ', '.join(row['grade_names'])
                                  if row['grade_names'] else '') if x)) or '—'
    return (f'| {_esc(row["alloy"])} | {row["grade"].replace("_", "-")} | '
            f'{"/".join(row["temper_labels"])} | {_mpa(row["standard_min_rm_pa"])} | {typ} | '
            f'{ctxt} | {usual} | {row["evidence"]} | {_esc(note)} | '
            f'{", ".join(row["sources"]) or "—"} |')


def _range_from(d):
    return Range(d['low'], d['high'], d['unit'], tuple(d['sources']), d['note'], d['bound'],
                 None, d['display_unit'])


def _proposal_line(pid, h, grade):
    p = proposed_material(pid, h, grade=grade)
    g = grade.replace('_', '-')
    if p['status'] != BG_STATUS:
        return f'- {g}: no proposal ({p["reason"]}).'
    t = p['tensile_strength_pa']
    lo, hi = t['range_pa']
    if t['value_pa'] is None:
        rm = 'tensile strength not published for this option'
    else:
        rng = f'{_mpa(lo)}–{_mpa(hi)}' if hi is not None else f'≥{_mpa(lo)}'
        rm = f'Rm {_mpa(t["value_pa"])} MPa used ({t["basis"]}; range {rng} MPa)'
    ps = p['proof_strength']
    rp = ('Rp0.2 not published' if ps['value_pa'] is None else
          f'Rp0.2 {_mpa(ps["value_pa"])} MPa ({"published" if ps["published"] else "assumed: " + ps["basis"]})')
    return (f'- {g}: **{p["alloy"]}-{p["temper"]}**; {rm}; {rp}; evidence {p["evidence"]}. '
            f'Rule: {p["rule"]}. [{", ".join(p["sources"])}]')


def _grades_md():
    L = ['## Battery foil: alloy and temper by gauge', '',
         'From the second battery survey (sources `BG-`): which alloy and temper are used at '
         'each gauge. A process engineer can read off, for a final gauge: the alloys, the '
         'temper label, the standard minimum and typical strength, and the evidence. The tool '
         f'uses the proposals below when the plant has not stated a material; each carries the '
         f'status {BG_STATUS} and must be confirmed or corrected by the plant.', '',
         '### Three findings first', '']
    L += [f'{i}. {s.text}{_cite(s)}' for i, s in enumerate(HEADLINE_FINDINGS, 1)]
    L += ['', f'How the standard minima were read: {GB_TABLE_READ.text}{_cite(GB_TABLE_READ)}',
          '', 'Evidence ratings are the report\'s own (strong / medium / weak / vendor-level), '
          'kept as data: "minima" rates the standard minima of the band, "choice" rates the '
          'usual alloy choice.', '',
          '### Collector foil: selection table by gauge band', '',
          '| Gauge band | GB/T 33143-2022 minimum Rm by alloy, MPa (H18) | Typical producer '
          'values | Alloy usually chosen | Typical cells | Pinholes (T/ZZB 2638) | Evidence |',
          '|---|---|---|---|---|---|---|']
    for b in COLLECTOR_BANDS:
        tp = f'{b.typical_producer.text}{_cite(b.typical_producer)}' if b.typical_producer \
            else '—'
        cells = f'{b.typical_cells.text}{_cite(b.typical_cells)}' if b.typical_cells else '—'
        pin = f'{b.pinholes.text}{_cite(b.pinholes)}' if b.pinholes else '—'
        L.append(f'| {b.label} ({b.gauges_named}) | {_band_min_txt(b)} | {_esc(tp)} | '
                 f'{_esc(b.usual_choice.text)}{_cite(b.usual_choice)} | {_esc(cells)} | '
                 f'{_esc(pin)} | {_esc(b.evidence.text)} (minima {b.minima_evidence}, choice '
                 f'{b.choice_evidence}){_cite(b.evidence)} |')
    L += ['', f'- Elongation: {GB_ELONGATION.text}{_cite(GB_ELONGATION)}',
          f'- Temper label: {TEMPER_NAMING.text}{_cite(TEMPER_NAMING)}']
    L += [f'- Surface: {s.text}{_cite(s)}' for s in (SURFACE_SINGLE, SURFACE_SAMA, SURFACE_8021)]
    for b in COLLECTOR_BANDS:
        L += [f'- {b.label}: {s.text}{_cite(s)}' for s in b.notes]
    L += ['', '### The two bands that matter for a 17–19 µm and a 12 µm product', '']
    r1 = 1 - (18 / 50) ** 0.5
    r2 = 1 - (12 / 50) ** 0.5
    L += [f'- A usual final gauge of 17–19 µm is in the **{_band_of(_BC, 18e-6).label}** band; '
          f'12 µm is in the **{_band_of(_BC, 12e-6).label}** band. From 50 µm in two equal '
          f'single-sheet passes (computed): 50→18 µm is {r1 * 100:.0f} % per pass '
          f'(50→{50 * (1 - r1):.0f}→18 µm), 50→12 µm is {r2 * 100:.0f} % per pass '
          f'(50→{50 * (1 - r2):.1f}→12 µm).', '']
    for h in (18e-6, 12e-6):
        b = _band_of(_BC, h)
        L += [f'**{h * 1e6:.0f} µm: band {b.label}.** Proposals:', '']
        L += [_proposal_line(_BC, h, g) for g in GRADES]
        L += ['']
    L += ['The research-stated numbers for 12 µm: standard minimum 180–190 MPa for 1235/1060, '
          '230 MPa for the 1100/1C30 type that EV practice favours [BG-G2, BG-G21, BG-G23].', '',
          '### Options by band', '',
          f'Order: {ORDERING_RULE}', '',
          f'Proposal rule: standard = {PROPOSAL_RULE["standard"]}; high-strength = '
          f'{PROPOSAL_RULE["high_strength"]}; when there is none, {PROPOSAL_FALLBACK_RULE}. '
          f'Strength {VALUE_RULE}. Proof strength, where not published, is assumed from the '
          'median Rp0.2/Rm ratio of the 15 µm grades that publish both (computed).', '']
    for b in COLLECTOR_BANDS:
        g = grade_options(_BC, b.high_m)
        L += [f'#### {b.label}', '',
              '| Alloy | Grade | Temper | GB min Rm, MPa | Typical producer values | % IACS | '
              'Usual choice | Evidence | Note | Sources |',
              '|---|---|---|---|---|---|---|---|---|---|']
        L += [_opt_md_row(r) for r in g['options']]
        L += ['', _proposal_line(_BC, b.high_m, 'standard').replace('- standard:',
                                                                    '- Proposal, standard:'),
              _proposal_line(_BC, b.high_m, 'high_strength').replace(
                  '- high-strength:', '- Proposal, high-strength:'), '']
    L += ['### Conductivity', '']
    L += [f'- {s.text}{_cite(s)}' for s in CONDUCTIVITY]
    L += ['', '### Other documents that set strength by gauge', '']
    L += [f'- {s.topic}: {s.text}{_cite(s)}' for s in OTHER_GRADE_DOCUMENTS]
    L += ['', '### Gauges in use', '']
    L += _stmt_lines(GAUGES_IN_USE)
    L += ['', '### The 25–60 µm battery products', '',
          '| Product | Gauge | Alloy, temper | Properties | Last pass | Evidence |',
          '|---|---|---|---|---|---|']
    for pid, last in (('battery_pouch_laminate_foil', BAND_POUCH.notes[0]),
                      ('battery_tab_foil', None), ('battery_thick_collector_foil', None),
                      ('battery_carbon_coated_base_foil', None)):
        p = _PRODUCTS[pid]
        b = GRADE_TABLES[pid][0]
        alloys = ', '.join(o.alloy for o in b.options)
        temper = '/'.join(dict.fromkeys(t for o in b.options for t in o.temper_labels))
        props = '; '.join(f'{_esc(", ".join(s.alloys))} {_esc(s.condition)}: '
                          + ', '.join(_fmt_range(r) for r in (s.rm_pa, s.elongation) if r)
                          + f' [{", ".join(s.sources)}]' for o in b.options[:1]
                          for s in o.typical) or '—'
        if pid == 'battery_tab_foil' or pid == 'battery_carbon_coated_base_foil':
            props = (f'{b.typical_producer.text}{_cite(b.typical_producer)}')
        last_txt = (f'{last.text}{_cite(last)}' if last else
                    {'battery_tab_foil': 'Annealed after rolling (inferred) [BG-G34]',
                     'battery_thick_collector_foil': 'Supplied hard [BG-G35]',
                     'battery_carbon_coated_base_foil': 'Supplied hard [BG-G38]'}[pid])
        ev = p.evidence[0]
        L.append(f'| {p.name} | {_rng_cell(p.final_gauge_m)} | {_esc(alloys)}; '
                 f'{_esc(temper)} | {_esc(props)} | {_esc(last_txt)} | '
                 f'{_esc(ev.text)}{_cite(ev)} |')
    L.append(f'| Case, lid, busbar, cooling plate (not a catalogue product) | ≥0.3 mm | '
             f'3003, 1050 | — | Not foil | {_esc(CELL_CASE_STOCK.text)}{_cite(CELL_CASE_STOCK)} |')
    L += ['']
    L += [f'- Pouch: {s.text}{_cite(s)}' for s in BAND_POUCH.notes[1:] + (
        _PRODUCTS['battery_pouch_laminate_foil'].common_gauges[-1], BAND_POUCH.usual_choice)]
    L += ['', '### Why alloy and temper change with gauge', '']
    L += [f'{s.topic}. {s.text}{_cite(s)}' for s in GRADE_REASONS]
    L += ['', '### How each temper is produced', '', '| Temper | Definition | How battery foil '
          'reaches it |', '|---|---|---|']
    L += [f'| {t.temper} | {_esc(t.definition.text)}{_cite(t.definition)} | '
          f'{_esc(t.route.text)}{_cite(t.route)} |' for t in TEMPER_TABLE]
    L += ['', '### Strength after heating', '', f'{HEATING_NOTE.text}{_cite(HEATING_NOTE)}', '',
          '| Material | ' + ' | '.join(lbl for lbl, _, _ in _HEAT) + ' | Loss (computed) | '
          'Sources |', '|---|---|---|---|---|---|---|']
    for sh in STRENGTH_AFTER_HEATING:
        loss = sh.loss_fraction()
        lt = ('—' if loss is None else (f'{loss[0] * 100:.0f} %' if round(loss[0] * 100) ==
                                        round(loss[1] * 100) else
                                        f'{loss[0] * 100:.0f}–{loss[1] * 100:.0f} %'))
        if len(sh.steps) == len(_HEAT):
            cells = [_fmt_range(s.rm_pa) for s in sh.steps]
        else:
            cells = [_fmt_range(sh.steps[0].rm_pa), f'{sh.steps[1].label}: '
                     f'{_fmt_range(sh.steps[1].rm_pa)}', '—', '—']
        src = ', '.join(_union_sources([s.rm_pa for s in sh.steps]))
        L.append(f'| {_esc(sh.material)}{" (" + sh.note + ")" if sh.note else ""} | '
                 + ' | '.join(cells) + f' | {lt} | {src} |')
    L += ['', '### Correction', '']
    L += _stmt_lines(CORRECTIONS)
    L += ['', '### Disagreements (second survey)', '']
    L += _stmt_lines(GRADE_DISAGREEMENTS)
    L += ['', '### Not found (second survey)', '']
    L += _stmt_lines(GRADE_NOT_FOUND)
    L.append('')
    return L


def _pt_md():
    L = ['## Process temperatures in foil rolling', '',
         'From the third research pass (sources `PT-`): temperatures of strip, oil and rolls and '
         'their effects on properties, roll wear and surface finish. ' + PT_NOT_A_MODEL
         + ' `check_thermal` compares supplied values with the ranges below.', '',
         '### Temperature map', '',
         '| Temperature | Typical range | Limit | Reason given |', '|---|---|---|---|']
    for r in TEMPERATURE_MAP:
        lim = f'{r.limit.text}{_cite(r.limit)}' if r.limit else '—'
        L.append(f'| {_esc(r.name)} | {_esc(r.typical.text)}{_cite(r.typical)} | {_esc(lim)} | '
                 f'{_esc(r.reason.text)}{_cite(r.reason)} |')
    L += ['', '### Four findings first', '']
    L += [f'{i}. {s.text}{_cite(s)}' for i, s in enumerate(PT_HEADLINE, 1)]
    L += ['', '### Temperature rise per pass', '']
    L += _stmt_lines(PT_RISE_PER_PASS)
    L += ['', '### Rolling oil', '']
    L += _stmt_lines(OIL_PROPERTIES)
    L += ['', 'What goes wrong:', '']
    L += _stmt_lines(OIL_WHAT_GOES_WRONG)
    L += ['', '### Temperature and material properties', '']
    L += _stmt_lines(PT_MATERIAL)
    L += ['', '### Temperature and roll wear / roll surface', '',
          f'{PT_NOT_A_MODEL}', '']
    L += _stmt_lines(PT_ROLL_WEAR)
    L += ['- Roll change and regrind interval for foil finishing rolls: not found.', '',
          '### Temperature and surface finish', '', PT_NOT_A_MODEL, '',
          '| Defect or property | Thermal cause | Magnitude given | Sources |',
          '|---|---|---|---|']
    L += [f'| {_esc(d.name)} | {_esc(d.thermal_cause)} | {_esc(d.magnitude)} | '
          f'{", ".join(d.sources)} |' for d in PT_SURFACE]
    L += ['', f'- {SPRAY_OVERLAP.text}{_cite(SPRAY_OVERLAP)}',
          f'- {PT_SURFACE_NOTE.text}{_cite(PT_SURFACE_NOTE)}', '',
          '### Numbers for simulation', '']
    L += _stmt_lines(PT_SIMULATION)
    L += ['', f'- Axial decay time computed here: {_rng_cell(AXIAL_TAU)}. {AXIAL_TAU.note}.',
          '', '### Disagreements (process temperatures)', '']
    L += _stmt_lines(PT_DISAGREEMENTS)
    L += ['', '### Not found (process temperatures)', '']
    L += _stmt_lines(PT_NOT_FOUND)
    L.append('')
    return L


def render_reference_markdown():
    """The reference document (deterministic; ``docs/thin-gauge-products.md`` must equal it)."""
    L = ['# Thin-gauge aluminium products: literature reference', '',
         '<!-- Generated by `python -m physicroll.band_products --write '
         'docs/thin-gauge-products.md`; do not edit by hand. -->', '',
         '## What this is and is not', '',
         'This is a literature survey of thin-gauge aluminium products: gauges, alloys, tempers, '
         'properties, rolling routes, quality requirements and named band or streak defects. '
         'Every value is quoted from five research reports (battery and electronics foil, a '
         'second battery report on alloy and temper by gauge, process temperatures, packaging '
         'and household foil, '
         'heat-exchanger stock, litho and other strip) and '
         'carries its source ids. It is not a validation: nothing here was measured on a plant, '
         'vendor and trade pages are low-confidence, and several standards were read from '
         'previews only. A value inside a published span is not evidence that a pass is good.',
         '',
         'Per-pass reductions are computed by `physicroll.band_products` from the published '
         'gauge sequences as 1 − h_exit/h_entry (per sheet for a doubled pass); a block of n '
         'passes shows its total and the equal-split mean 1 − (h_exit/h_entry)^(1/n). Ranges '
         'are kept as ranges, and the reports\' disagreements and "not found" lists are kept '
         'below.', '',
         'Source ids: `BF-` battery report, `BG-` second battery report (alloy and temper by '
         'gauge), `PT-` process-temperature report, `PK-` packaging report, `HX-` heat-exchanger and litho report, `TM-` thermal, material and dynamics gap report. A citation such as [PK-S20] shows the sources; a fact whose own read '
         'status is weaker than its sources shows it, e.g. [PK-S14; vendor_or_trade_page]. '
         'Read-status legend:', '',
         '| Read status | Meaning | Report tags mapped onto it |', '|---|---|---|',
         '| full_text | page or document read in full (or the relevant pages) | FT; F |',
         '| excerpt | long excerpts, previews or partial reads | EX; F with "excerpt", '
         '"preview", "partial" or "clauses"; every F of the heat-exchanger report ("full text '
         'or long excerpt") |',
         '| abstract_or_snippet | abstract or search snippet only | S; A; no tag (non-vendor) |',
         '| vendor_or_trade_page | vendor, producer or trade page (low confidence) | VP; V; V/A; '
         'no tag (vendor); BF-S17 (tagged FT, a trade page) |',
         '| memory_unverified | researcher\'s memory, unverified | MEM; M |',
         '| computed | computed by this module from published gauges | report "calc." values '
         'are recomputed |', '',
         f'Catalogue: {len(_PRODUCT_LIST)} products, {fact_count()} sourced facts, '
         f'{len(_SOURCES)} sources. Status: {STATUS}.', '',
         '## Summary', '',
         '| Product | Final gauge | Alloys | Temper | Single or doubled | Per-pass reduction | '
         'Key requirement |', '|---|---|---|---|---|---|---|']
    for p in _PRODUCT_LIST:
        tempers = ', '.join(dict.fromkeys(t.name for t in p.tempers)) + _cite_union(p.tempers)
        L.append(f'| {p.name} | {_rng_cell(p.final_gauge_m)} | {_esc(_alloy_list(p))} | '
                 f'{_esc(tempers)} | {_mode_txt(p)} | {_ppr_txt(p)} | '
                 f'{_esc(p.key_requirement.text)}{_cite(p.key_requirement)} |')
    L += ['', '### Battery schedules: most important flag', '',
          f'{BATTERY_SCHEDULE_CAVEAT.text}{_cite(BATTERY_SCHEDULE_CAVEAT)}', '',
          f'{TENSION_LINES.text}{_cite(TENSION_LINES)}', '']
    L += _general_md()
    L += _grades_md()
    L += _pt_md()
    L += _alloy_md()
    for n, p in enumerate(_PRODUCT_LIST, 1):
        L += _product_md(p, n)
    L += ['## Minor products (one-liners, low confidence)', '']
    L += _stmt_lines(MINOR_PRODUCTS)
    L += ['', '## Disagreements between sources', '', '### General', '']
    L += _stmt_lines(GENERAL_DISAGREEMENTS + MINOR_DISAGREEMENTS)
    for p in _PRODUCT_LIST:
        if p.disagreements:
            L += ['', f'### {p.name}', '']
            L += _stmt_lines(p.disagreements)
    L += ['', '## What was not found', '', '### General', '']
    L += _stmt_lines(GENERAL_NOT_FOUND)
    for p in _PRODUCT_LIST:
        if p.not_found:
            L += ['', f'### {p.name}', '']
            L += _stmt_lines(p.not_found)
    L += ['', '## Sources', '', '| Id | Title | Read status | Report tag | URLs | Note |',
          '|---|---|---|---|---|---|']
    for s in _SOURCE_LIST:
        urls = '<br>'.join(f'<{u}>' for u in s.urls)
        L.append(f'| {s.id} | {_esc(s.title)} | {s.read_status} | {s.report_tag} | {urls} | '
                 f'{_esc(s.note) or "—"} |')
    L.append('')
    return '\n'.join(L)


# --------------------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='python -m physicroll.band_products',
        description='Thin-gauge aluminium product catalogue (literature survey, unvalidated).')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', metavar='PATH', help='write the reference markdown to PATH')
    g.add_argument('--list', action='store_true', help='list product ids and names')
    g.add_argument('--json', action='store_true', help='print the catalogue as JSON (with '
                   '--grades: the options and proposals as JSON)')
    g.add_argument('--temperatures', action='store_true',
                   help='print the process-temperature map (literature, PT- sources)')
    g.add_argument('--grades', metavar='PRODUCT_ID', help='alloy and temper options and the two '
                   'literature proposals at --gauge-um')
    parser.add_argument('--gauge-um', type=float, help='final gauge in µm (with --grades)')
    parser.add_argument('--min-strength-mpa', type=float,
                        help='mark options below this tensile strength (with --grades)')
    parser.add_argument('--surface', choices=SURFACES, help='surface (with --grades)')
    argv = list(sys.argv[1:] if argv is None else argv)
    # '--grades X --json' is allowed: --json then formats the --grades output
    as_json = '--grades' in argv and '--json' in argv
    if as_json:
        argv.remove('--json')
    args = parser.parse_args(argv)
    if args.grades:
        if args.gauge_um is None:
            parser.error('--grades needs --gauge-um')
        h = args.gauge_um * 1e-6
        req = None if args.min_strength_mpa is None else args.min_strength_mpa * 1e6
        try:
            if as_json:
                out = {'options': grade_options(args.grades, h, min_tensile_strength_pa=req,
                                                surface=args.surface),
                       'proposals': {gr: proposed_material(args.grades, h, grade=gr,
                                                           surface=args.surface)
                                     for gr in GRADES}}
                json.dump(out, sys.stdout, ensure_ascii=False, indent=1, allow_nan=False)
                print()
            else:
                sys.stdout.write(format_grade_options(args.grades, h,
                                                      min_tensile_strength_pa=req,
                                                      surface=args.surface))
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    if args.temperatures:
        sys.stdout.write(format_temperature_map())
        return 0
    if args.gauge_um is not None or args.min_strength_mpa is not None or args.surface:
        parser.error('--gauge-um, --min-strength-mpa and --surface go with --grades')
    if args.write:
        path = Path(args.write)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_reference_markdown(), encoding='utf-8')
        print(f'wrote {path}')
    elif args.list:
        for p in _PRODUCT_LIST:
            print(f'{p.id}\t{p.family}\t{p.name}')
    else:
        json.dump(catalogue_dict(), sys.stdout, ensure_ascii=False, indent=1, allow_nan=False)
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
