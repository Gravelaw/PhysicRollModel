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
            'NO_PUBLISHED_RANGE', 'INCONSISTENT_WITH_PUBLISHED_MODE')
# display unit -> (SI unit, factor to SI, label)
DISPLAY = {
    'um': ('m', 1e-6, 'µm'), 'mm': ('m', 1e-3, 'mm'), 'MPa': ('Pa', 1e6, 'MPa'),
    'kPa': ('Pa', 1e3, 'kPa'), '%': ('fraction', 0.01, '%'), 'm/min': ('m/s', 1 / 60, 'm/min'),
    'mN/m': ('N/m', 1e-3, 'mN/m'), 'per_m2': ('1/m^2', 1.0, 'per m²'),
    'g/m2': ('kg/m^2', 1e-3, 'g/m²'),
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
        if not self.id.startswith(('BF-', 'PK-', 'HX-')):
            raise ValueError(f'source id {self.id!r} must start with BF-, PK- or HX-')
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

    _STATEMENT_FIELDS = ('common_gauges', 'foil_stock', 'annealing', 'route',
                         'work_roll_roughness', 'rolls_and_oil', 'surface',
                         'thickness_tolerance', 'flatness_requirement', 'wettability',
                         'pinholes', 'other_requirements', 'caveats', 'disagreements')

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
             _i('O', 'Listed by some vendor pages (disagrees with the H18 consensus).',
                'BF-S48')),
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
        _st('1C30, 1100, 8011', 'H18', 'GB/T 33143 high-strength minima', 'BF-S2',
            rm=('min', 220, 230), grade='high_strength', note='"about ≥220–230 MPa"'),
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
    ),
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
                   _s('Toyo TY-X2: 8079 at 40 µm, 8021 at 35 µm.', 'BF-S28')),
    alloys=(_i('8021', 'GB/T 22648-2023 alloy; Toyo TY-X2 at 35 µm.', 'BF-S29 BF-S28'),
            _i('8A21', 'GB/T 22648-2023 alloy.', 'BF-S29'),
            _i('8079', 'GB/T 22648-2023 alloy; Toyo TY-X2 at 40 µm.', 'BF-S29 BF-S28')),
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
                  'anneal 240–260 °C for 40–45 h.', 'BF-S32 BF-S33'),),
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
    ),
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
        _nf('Group standard T/ZZB 2076-2021 exists; not read.'),
    ),
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

_PRODUCT_LIST = (BATTERY_COLLECTOR, POUCH, CAP_HV, CAP_LV, CAP_CATHODE, BLISTER, COLD_FORM,
                 STRIP_PACK, HOUSEHOLD, HOUSEHOLD_HD, CONVERTER, CIGARETTE, DAIRY, CONTAINER_WW,
                 CONTAINER_SW, CONTAINER_RT, BRAZED_FIN, BRAZING_SHEET, HVAC_FIN, LITHO, CAN_BODY,
                 CAN_END, CLOSURE, TRANSFORMER)
_PRODUCTS = {p.id: p for p in _PRODUCT_LIST}


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
                   GENERAL_STANDARDS), out)
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
    # alloy / temper
    alloy_names = {_norm(a.name) for a in p.alloys}
    if alloy is not None:
        known = _norm(alloy) in alloy_names
        out.append({'item': 'alloy', 'value': alloy, 'published_low': None,
                    'published_high': None, 'unit': '',
                    'verdict': 'WITHIN_PUBLISHED_RANGE' if known else 'NO_PUBLISHED_RANGE',
                    'basis': 'alloy listed for this product' if known
                    else 'alloy not listed for this product in the reports',
                    'sources': list(_union_sources([a for a in p.alloys
                                                    if _norm(a.name) == _norm(alloy)])),
                    'read_status': _weakest_of([a for a in p.alloys
                                                if _norm(a.name) == _norm(alloy)]),
                    'note': ''})
    if temper is not None:
        hits = [t for t in p.tempers if _norm(t.name) == _norm(temper)]
        out.append({'item': 'temper', 'value': temper, 'published_low': None,
                    'published_high': None, 'unit': '',
                    'verdict': 'WITHIN_PUBLISHED_RANGE' if hits else 'NO_PUBLISHED_RANGE',
                    'basis': 'temper listed for this product' if hits
                    else 'temper not listed for this product in the reports',
                    'sources': list(_union_sources(hits)), 'read_status': _weakest_of(hits),
                    'note': ''})
    if sigma is not None:
        out.append(_flow_stress_finding(p, sigma, alloy, temper))
    return _checked(out)


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


def render_reference_markdown():
    """The reference document (deterministic; ``docs/thin-gauge-products.md`` must equal it)."""
    L = ['# Thin-gauge aluminium products: literature reference', '',
         '<!-- Generated by `python -m physicroll.band_products --write '
         'docs/thin-gauge-products.md`; do not edit by hand. -->', '',
         '## What this is and is not', '',
         'This is a literature survey of thin-gauge aluminium products: gauges, alloys, tempers, '
         'properties, rolling routes, quality requirements and named band or streak defects. '
         'Every value is quoted from three research reports (battery and electronics foil, '
         'packaging and household foil, heat-exchanger stock, litho and other strip) and '
         'carries its source ids. It is not a validation: nothing here was measured on a plant, '
         'vendor and trade pages are low-confidence, and several standards were read from '
         'previews only. A value inside a published span is not evidence that a pass is good.',
         '',
         'Per-pass reductions are computed by `physicroll.band_products` from the published '
         'gauge sequences as 1 − h_exit/h_entry (per sheet for a doubled pass); a block of n '
         'passes shows its total and the equal-split mean 1 − (h_exit/h_entry)^(1/n). Ranges '
         'are kept as ranges, and the reports\' disagreements and "not found" lists are kept '
         'below.', '',
         'Source ids: `BF-` battery report, `PK-` packaging report, `HX-` heat-exchanger and '
         'litho report. A citation such as [PK-S20] shows the sources; a fact whose own read '
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
    g.add_argument('--json', action='store_true', help='print the catalogue as JSON')
    args = parser.parse_args(argv)
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
