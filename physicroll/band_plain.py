"""Plain-language layer of the band screening interface (SPEC16 Part 1; standard library only).

Pure functions, no file or network I/O and no server. The band app (``physicroll.band_app``)
uses this module to (1) ask the questions of the guided form, (2) turn the answers into a
``physicroll.band_case.v2`` case for the engine (``physicroll.band_diagnosis``), and (3) turn
the engine's result into a JSON summary the page draws from. Nothing here adds physics: every
number in a summary is read from the engine result, and every word about a cause is written
from ``docs/band-diagnosis.md`` (sections 3.7, 6.2, 6.3) and the hypotheses' own mechanism
texts.

Status: the summaries describe a SCREENING result that has not been compared with plant data
(``SCREENING_RESULT_NOT_PLANT_VALIDATED``). A shortlist is a ranked tally of how well each
candidate fits what was entered; it never names a single cause.

Questions (``QUESTIONS``). One frozen ``Question`` per case-file key the form can set: every
one of the 31 ``observation`` keys of ``scenarios/band_diagnosis_template.json`` and the
machine, pass and material keys of section 5.3 of the guide (``model_options.
bite_response_override`` excepted: it is a plant-model bite, not a value a person types).
Each question carries its plain wording, help text, answer kind, the dotted case key, the unit
shown in the form and its conversion to SI (``UNITS``). Enumerated answers use the engine's own
lists (``band_diagnosis.ORIENTATIONS``, ``FIRST_SEEN``, ``band_width.CONTINUITY``,
``APPEARANCES``, ...); the two the engine validates against literals only (``faces`` and the
bearing / grinder-mark roll) are typed here and checked by a test.

"Don't know / not checked" is the default for every question and is ``None`` in the answers:
- an observation, a known nozzle fault or another case-specific fact then becomes ``null`` (or
  an empty list), which the engine always scores ``NOT_OBSERVED`` and never against a cause;
- a mill, pass or material value then stays at the starting point's value and is recorded as
  ``preset`` (a required engine input cannot be null).
Every mill, pass and material value is recorded as ``measured``, ``estimated`` or ``preset``
(``value_origins``); the case's ``provenance`` and a ``notes`` line say which is which.

Positions across the width are entered in millimetres from the strip edge on the side where
the coolant header starts (nozzle 1); the engine works on the header's barrel coordinate
(0 = header start, the convention of the case template). The conversion uses the engine's own
convention for where the strip runs: centred on the barrel unless
``width_model.strip_centre_m`` says otherwise (``strip_edge_m``).

Trust level (``trust`` in a summary) — a RULE, not a statistic:
  start at FAIR, then apply every cap below; the level is the lowest cap reached.
  - LOW when the inputs are synthetic (flag ``SYNTHETIC_INPUTS``) or any "ask first" mill
    value is left at the typical (preset) value or the person did not mark the mill values as
    their own: a result built on preset mill values is never above LOW;
  - LOW when fewer than half of the "ask first" observations for the observed kind of band
    are answered, or when no orientation is recorded;
  - LOW when nothing leads (no ``CONSISTENT_LEADING`` hypothesis);
  - LOW when the case pass has no roll bite (``bite_error``) or its bite is not credible
    (``CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE``) or any part of the
    screening failed (a flag ending in ``_FAILED``);
  - MODERATE when 50-79 % of the "ask first" observations are answered;
  - MODERATE when two or more causes tie for the lead, or the leader is less than 3 points
    ahead of the next cause of the same kind;
  - MODERATE for each of: ``EXPERIMENTAL_MATTRESS_FOIL_MODEL``, the extended-domain flags
    (``EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN``,
    ``REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN``),
    ``CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED``, ``MATERIAL_NOT_STATED_...``,
    (``USER_SUPPLIED_INPUTS_NOT_VERIFIED`` is not a cap: the engine sets it for every case
    marked as the person's own values).
  The level is never "high": nothing in the tool has been compared with plant data.

NOT done here: any physics, any re-scoring, any plant validation. The engine owns all of it.
"""
from dataclasses import dataclass, field
import copy
import json
import math
import re

from . import band_diagnosis as bd
from . import band_process as bproc
from . import band_signatures as bsig
from . import band_products as bprod
from . import band_survey as bsurvey
from . import band_thermal as bthermal
from . import band_width as bw
from . import roll_thermal as rt

SCHEMA = 'physicroll.band_plain.v1'
STATUS = bd.STATUS
ORIGINS = ('measured', 'estimated', 'preset')
STEPS = (('see', 'What do you see?'), ('rolling', 'What are you rolling?'),
         ('mill', 'Your mill'))
KINDS = ('choice', 'yesno', 'number', 'positions', 'list', 'numbers', 'text', 'nozzles')
UNKNOWN_RULES = ('null', 'empty', 'preset')
FAMILIES = ('lengthwise', 'transverse', 'foil', 'both')
WEAK_NOZZLE_LEVEL = 0.5     # analyst choice for the page's "weak" nozzle (demos use 0.45)
NOTE_PREFIX = 'Band app: '
ORIGIN_NOTE = NOTE_PREFIX + 'value origins'

# ============================================================================= units
# id -> (label, multiply, divide, offset): SI = value * multiply / divide + offset. Exact powers
# of ten are divided (correctly rounded), so 18 um -> 18 / 1e6 gives the same double as 1.8e-05.
UNITS = {
    'um': ('µm', 1.0, 1e6, 0.0), 'mm': ('mm', 1.0, 1e3, 0.0),
    'mm_dia': ('mm', 1.0, 2e3, 0.0),           # a diameter shown, a radius stored
    'm': ('m', 1.0, 1.0, 0.0), 'm_min': ('m/min', 1.0, 60.0, 0.0),
    'mm_s': ('mm/s', 1.0, 1e3, 0.0),
    'mpa': ('MPa', 1e6, 1.0, 0.0), 'gpa': ('GPa', 1e9, 1.0, 0.0),
    'degc': ('°C', 1.0, 1.0, 273.15), 'kelvin': ('K', 1.0, 1.0, 0.0),
    's': ('s', 1.0, 1.0, 0.0), 'hz': ('Hz', 1.0, 1.0, 0.0), 'kg': ('kg', 1.0, 1.0, 0.0),
    'kn_mm': ('kN/mm', 1e6, 1.0, 0.0), 'deg': ('°', math.pi, 180.0, 0.0),
    'mpa_s': ('mPa·s', 1.0, 1e3, 0.0), 'per_gpa': ('1/GPa', 1.0, 1e9, 0.0),
    'per_k': ('1/K', 1.0, 1.0, 0.0), 'um_per_mk': ('µm/(m·K)', 1.0, 1e6, 0.0),
    'w_m2k': ('W/(m²·K)', 1.0, 1.0, 0.0), 'w_mk': ('W/(m·K)', 1.0, 1.0, 0.0),
    'kg_m3': ('kg/m³', 1.0, 1.0, 0.0), 'j_kgk': ('J/(kg·K)', 1.0, 1.0, 0.0),
    'kg_m2': ('kg·m²', 1.0, 1.0, 0.0), 'knm_rad': ('kN·m/rad', 1e3, 1.0, 0.0),
    'percent': ('%', 1.0, 100.0, 0.0), 'ratio': ('', 1.0, 1.0, 0.0),
    'count': ('', 1.0, 1.0, 0.0), 'nozzle_no': ('', 1.0, 1.0, -1.0),
    'kw_m': ('kW/m', 1e3, 1.0, 0.0), 'n_m_pa': ('m', 1.0, 1.0, 0.0),
    'pos_mm': ('mm from the strip edge', 1.0, 1e3, 0.0),
}
INTEGER_UNITS = ('count', 'nozzle_no')


def _r12(x):
    """Round to 12 significant digits (display values free of binary noise)."""
    return float(f'{x:.12g}')


def to_si(value, unit):
    """Display value -> SI value."""
    _, mul, div, off = UNITS[unit]
    if unit in INTEGER_UNITS:
        return int(round(value)) + int(off)
    out = value * mul / div + off if mul != 1.0 else value / div + off
    return out


def from_si(value, unit):
    """SI value -> display value (12 significant digits; integers for counts)."""
    _, mul, div, off = UNITS[unit]
    if unit in INTEGER_UNITS:
        return int(round(value - off))
    if off:
        return _r12(round(value - off, 9))        # offset units: keep 1e-9 K, drop noise
    return _r12(value * div / mul if mul == 1.0 else value * div / mul)


def unit_label(unit):
    return UNITS[unit][0] if unit else ''


# ============================================================================= questions
@dataclass(frozen=True)
class Field:
    """One field of an item of a list question (e.g. one pass of the route)."""
    name: str
    label: str
    kind: str = 'number'            # number | text | choice | yesno | numbers
    unit: str | None = None
    choices: tuple = ()

    def validate(self):
        if self.kind not in ('number', 'text', 'choice', 'yesno', 'numbers'):
            raise ValueError(f'field {self.name}: unknown kind {self.kind!r}')
        if self.kind in ('number', 'numbers') and self.unit not in UNITS:
            raise ValueError(f'field {self.name}: unknown unit {self.unit!r}')
        if self.kind == 'choice' and not self.choices:
            raise ValueError(f'field {self.name}: a choice needs choices')

    def to_dict(self):
        return {'name': self.name, 'label': self.label, 'kind': self.kind, 'unit': self.unit,
                'unit_label': unit_label(self.unit),
                'choices': [{'value': v, 'label': lab} for v, lab in self.choices]}


@dataclass(frozen=True)
class Question:
    """One question of the guided form, mapped to one case-file key."""
    id: str
    step: str
    group: str
    key: str
    kind: str
    wording: str
    help: str
    unit: str | None = None
    ask_first: bool = False
    choices: tuple = ()
    fields: tuple = ()
    unknown: str = 'preset'
    family: str = 'both'
    also_keys: tuple = ()
    lo_si: float | None = None
    hi_si: float | None = None

    def validate(self):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', self.id):
            raise ValueError(f'question id {self.id!r} is not snake case')
        if self.step not in dict(STEPS):
            raise ValueError(f'{self.id}: unknown step {self.step!r}')
        if self.kind not in KINDS:
            raise ValueError(f'{self.id}: unknown kind {self.kind!r}')
        if self.unknown not in UNKNOWN_RULES or self.family not in FAMILIES:
            raise ValueError(f'{self.id}: bad unknown rule or family')
        if self.kind in ('number', 'positions', 'numbers') and self.unit not in UNITS:
            raise ValueError(f'{self.id}: unknown unit {self.unit!r}')
        if self.kind == 'choice' and not self.choices:
            raise ValueError(f'{self.id}: a choice needs choices')
        if self.kind == 'list':
            if not self.fields:
                raise ValueError(f'{self.id}: a list needs fields')
            for f in self.fields:
                f.validate()
        if not self.wording.strip() or not self.help.strip():
            raise ValueError(f'{self.id}: wording and help are required')
        return self

    @property
    def origin_tracked(self):
        """Mill, pass and material values carry a measured / estimated / preset mark."""
        return self.unknown == 'preset'

    def to_dict(self):
        return {'id': self.id, 'step': self.step, 'group': self.group, 'key': self.key,
                'kind': self.kind, 'wording': self.wording, 'help': self.help,
                'unit': self.unit, 'unit_label': unit_label(self.unit),
                'ask_first': self.ask_first,
                'choices': [{'value': v, 'label': lab} for v, lab in self.choices],
                'fields': [f.to_dict() for f in self.fields], 'unknown': self.unknown,
                'family': self.family, 'origin_tracked': self.origin_tracked,
                'also_keys': list(self.also_keys), 'lo_si': self.lo_si, 'hi_si': self.hi_si}


def _q(id_, step, group, key, kind, wording, help_, **kw):
    return Question(id_, step, group, key, kind, wording, help_, **kw)


def _obs(id_, key, kind, wording, help_, **kw):
    kw.setdefault('unknown', 'empty' if kind in ('positions', 'list', 'numbers') else 'null')
    kw.setdefault('group', 'More details')
    return _q(id_, 'see', kw.pop('group'), 'observation.' + key, kind, wording, help_, **kw)


ORIENTATION_WORDS = {
    'longitudinal': 'Stripes along the strip (lengthwise bands at fixed places across the width)',
    'transverse': 'Marks straight across the strip, repeating along its length',
    'diagonal': 'Marks running at an angle across the strip',
    'chevron': 'V-shaped (herringbone) marks',
    'irregular': 'Irregular marks with no clear direction'}
FIRST_SEEN_WORDS = {
    'bite_exit': 'Straight out of the roll gap',
    'incoming_strip': 'Already on the incoming coil',
    'after_bending_or_levelling': 'Only after a deflector roll, coiler or leveller'}
CONTINUITY_WORDS = {
    'continuous': 'Always there, along the whole coil',
    'intermittent': 'Come and go (short-lived bands)',
    'both': 'Some always there, some come and go'}
APPEARANCE_WORDS = {
    'gloss_or_shade': 'A bright or dull stripe (gloss or shade)',
    'loose_or_buckle': 'A loose, wavy band (buckle)',
    'tight': 'A tight stripe',
    'stain': 'An oil or coolant stain (often seen after annealing)',
    'crease_or_flute': 'A sharp fold or flute (crease)'}
FACES_WORDS = {'both': 'On both faces', 'one': 'On one face only'}
FACES_VALUES = ('both', 'one')            # literal in band_diagnosis.validate_case
ROLL_VALUES = ('work_roll', 'backup_roll')  # literal in band_signatures (bearings, grinder marks)
ROLL_WORDS = {'work_roll': 'Work roll', 'backup_roll': 'Backup roll'}
BITE_MODEL_WORDS = {'hitchcock': 'Sheet roll-gap model (Hitchcock flattening)',
                    'mattress': 'Experimental foil roll-gap model (mattress)',
                    'auto': 'Choose by gauge (sheet model, foil model where it fails)'}
THERMAL_SENS_WORDS = {'off': 'Off', 'partition': 'Heat share only (default)',
                      'full': 'Heat share and spray coefficient (slow)'}
CONSTRAINT_WORDS = {'axially_free': 'Free to expand along the barrel',
                    'plane_strain': 'Held along the barrel (plane strain)'}
HARDENING_WORDS = {'power': 'Power law', 'voce': 'Voce law'}


def _choices(values, labels):
    missing = [v for v in values if v not in labels]
    if missing or set(labels) - set(values):
        raise ValueError(f'plain words do not match the engine list: {values} vs '
                         f'{sorted(labels)}')
    return tuple((v, labels[v]) for v in values)


def _product_choices():
    fam = {'battery_electronics': 'Battery and electronics',
           'packaging_household': 'Packaging and household',
           'heat_exchanger': 'Heat exchanger', 'litho': 'Lithographic',
           'other_strip': 'Other strip'}
    return tuple((p.id, f'{fam.get(p.family, p.family)}: {p.name}') for p in bprod.products())


YESNO_HELP = ' Answer yes, no, or leave it at "Don\'t know / not checked".'
EDGE_HELP = ('Measure across the strip, in millimetres, from the strip edge nearest the first '
             'coolant nozzle (nozzle 1). If the strip does not run in the middle of the roll, set '
             '"Strip centre on the barrel" under Your mill.')

OBSERVATION_QUESTIONS = (
    _obs('orientation', 'orientation', 'choice', 'Which way do the marks run?',
         'Look at a sample under raking light. Lengthwise stripes run along the rolling '
         'direction; transverse marks run across the strip and repeat along it.',
         choices=_choices(bd.ORIENTATIONS, ORIENTATION_WORDS), ask_first=True,
         group='The marks'),
    # ---- lengthwise, ask first (section 5.1 and 3.8)
    _obs('band_positions', 'band_positions_across_width_m', 'positions',
         'Where across the width are the bands?',
         'Place each band on the drawing of the strip or type its position. ' + EDGE_HELP,
         unit='pos_mm', ask_first=True, family='lengthwise', group='The marks'),
    _obs('positions_repeat', 'positions_repeat_across_coils', 'yesno',
         'Do the bands sit at the same places on the next coils?',
         'Compare three consecutive coils. Bands that stay put point to the mill (nozzle, roll); '
         'bands that follow the mother coil point to the incoming strip.' + YESNO_HELP,
         ask_first=True, family='lengthwise', group='The marks'),
    _obs('positions_move_after_wr_change', 'positions_change_after_work_roll_change', 'yesno',
         'Did the bands move or go away after a work-roll change?',
         'Moving or vanishing points to the roll surface; staying put points to the coolant '
         'header.' + YESNO_HELP, ask_first=True, family='lengthwise', group='The marks'),
    _obs('zone_switching', 'changes_with_coolant_zone_switching', 'yesno',
         'Do the bands come and go when cooling zones switch?',
         'Log the flatness-control valve states against the times the bands appear and fade. '
         'This is the strongest single test for short-lived bands.' + YESNO_HELP,
         ask_first=True, family='lengthwise', group='The marks'),
    _obs('only_after_release', 'visible_only_after_tension_release', 'yesno',
         'Are the bands invisible in the mill and only seen on the coil, at the slitter or on '
         'the table?',
         'A band that is flat under strip tension and buckles once tension is removed is called '
         'latent. Compare the strip in the mill with a sample laid flat.' + YESNO_HELP,
         ask_first=True, family='lengthwise', group='The marks'),
    _obs('continuity', 'lengthwise_continuity', 'choice',
         'Are the bands always there or do they come and go?',
         'Watch a coil being rolled: some bands run along the whole coil, others last only a '
         'while.', choices=_choices(bw.CONTINUITY, CONTINUITY_WORDS), ask_first=True,
         family='lengthwise', group='The marks'),
    _obs('appearance', 'appearance', 'choice', 'What does a band look like?',
         'Pick the closest description of one band.',
         choices=_choices(bw.APPEARANCES, APPEARANCE_WORDS), ask_first=True,
         family='lengthwise', group='The marks'),
    # ---- foil, ask first (section 3.8)
    _obs('worse_at_lower_tension', 'worse_at_lower_tension', 'yesno',
         'Do the bands fade when the exit tension is raised?',
         'Step the exit tension and note at which tension the bands fade. A latent heat stripe '
         'also behaves like this, so the answer is useful but not decisive.' + YESNO_HELP,
         ask_first=True, family='foil', group='Foil'),
    _obs('wiper_cleaning', 'changes_after_roll_wiper_cleaning', 'yesno',
         'Did the bands change or go after the roll wipers were cleaned?',
         'Clean the wipers and watch the bands. "No" means they stayed.' + YESNO_HELP,
         ask_first=True, family='foil', group='Foil'),
    _obs('tracks_speed', 'tracks_speed_changes', 'yesno',
         'Do the bands appear, move or fade when the mill speed changes?',
         'Note what the bands do during a speed change. "No" means they ignore it.' + YESNO_HELP,
         ask_first=True, family='foil', group='Foil'),
    # ---- transverse, ask first (section 5.2)
    _obs('pitch_observations', 'pitch_observations', 'list',
         'How far apart are the marks along the strip, and at what speed?',
         'Stone or etch a sample and measure the distance between marks along the rolling '
         'direction, with the steady speed it was rolled at. Do it at two speeds at least 20 % '
         'apart: if the spacing grows with speed the source vibrates at a fixed frequency; if '
         'it stays the same the source turns with a roll, bearing, gear or coil.',
         fields=(Field('exit_speed_m_s', 'Exit speed', unit='m_min'),
                 Field('pitch_m', 'Mark spacing', unit='mm')),
         ask_first=True, family='transverse', group='The marks'),
    _obs('gauge_variation', 'gauge_variation_detected', 'yesno',
         'Does the exit thickness gauge show a repeating thickness change at the mark '
         'frequency?',
         'Check the exit gauge or X-ray trace. "No" means the gauge is clean at that '
         'frequency.' + YESNO_HELP, ask_first=True, family='transverse', group='The marks'),
    _obs('gone_after_wr_change', 'disappears_after_work_roll_change', 'yesno',
         'Did the marks disappear after a work-roll change?', 'From a roll-change test.'
         + YESNO_HELP, ask_first=True, family='transverse', group='The marks'),
    _obs('gone_after_bur_change', 'disappears_after_backup_roll_change', 'yesno',
         'Did the marks or bands disappear after a backup-roll change?', 'From a roll-change test.'
         + YESNO_HELP, ask_first=True, group='The marks'),
    _obs('faces', 'faces', 'choice', 'Are the marks on both strip faces or only one?',
         'Look at the top and bottom faces of the same sample.',
         choices=_choices(FACES_VALUES, FACES_WORDS), ask_first=True, family='transverse',
         group='The marks'),
    # ---- more details
    _obs('band_width', 'band_width_m', 'number', 'How wide is one band across the strip?',
         'Typical width of one band.', unit='mm', family='lengthwise', hi_si=10.0),
    _obs('band_spacing', 'band_spacing_m', 'number',
         'If the bands are roughly evenly spaced, how far apart are they?',
         'Distance between neighbouring bands. Leave unknown if they are not regular.',
         unit='mm', family='lengthwise', hi_si=10.0),
    _obs('intermittent_duration', 'intermittent_duration_s', 'number',
         'How long does a short-lived band last?', 'Seconds of rolling from appearing to '
         'fading.', unit='s', family='lengthwise'),
    _obs('worse_outer_wraps', 'worse_toward_outer_wraps', 'yesno',
         'Is the band stronger toward the outside of the wound coil?', 'Compare inner and outer '
         'wraps.' + YESNO_HELP, family='lengthwise'),
    _obs('changes_with_tension', 'changes_with_tension', 'yesno',
         'Does changing the strip tension change the bands?', 'Vary the span tension and watch.'
         + YESNO_HELP, family='lengthwise'),
    _obs('follows_previous_edges', 'follows_previous_strip_edges', 'yesno',
         'Do the band edges line up with the edges of narrower strip rolled earlier on the '
         'same rolls?', 'Check the rolling sequence since the last roll change.' + YESNO_HELP,
         family='lengthwise'),
    _obs('worse_at_higher_speed', 'worse_at_higher_speed', 'yesno',
         'Do the bands get worse as the mill speeds up?', YESNO_HELP.strip(),
         family='lengthwise'),
    _obs('ironing_roll', 'changes_with_ironing_roll_pressure', 'yesno',
         'Do the bands change when the ironing-roll pressure is changed?',
         'Change the pressure one side at a time.' + YESNO_HELP, family='foil'),
    _obs('air_blowoff', 'changes_with_exit_air_blowoff', 'yesno',
         'Do the bands change when the exit air blow-off is reduced or redirected?',
         'Change the blow-off alone.' + YESNO_HELP, family='foil'),
    _obs('after_narrower_coil', 'appeared_after_narrower_coil', 'yesno',
         'Did the bands start when a wider coil followed a narrower one?',
         'Without a backup-roll change in between.' + YESNO_HELP, family='foil'),
    _obs('worse_at_thinner_gauge', 'worse_at_thinner_gauge', 'yesno',
         'Are the marks more frequent or stronger at thinner exit gauge?', YESNO_HELP.strip()),
    _obs('first_seen', 'first_seen', 'choice', 'Where do the marks first appear?',
         'Follow the strip from the incoming coil to the coiler.',
         choices=_choices(bd.FIRST_SEEN, FIRST_SEEN_WORDS), family='transverse'),
    _obs('onset_speed', 'onset_above_exit_speed_m_s', 'number',
         'Above what exit speed do the marks start?', 'Only if there is such a threshold.',
         unit='m_min', family='transverse'),
    _obs('vibration_hz', 'measured_vibration_hz', 'number',
         'Dominant stand vibration frequency, if measured', 'From a chock accelerometer at the '
         'operating speed.', unit='hz', family='transverse'),
    _obs('gauge_variation_size', 'gauge_variation_amplitude_m', 'number',
         'Size of the thickness variation (peak to peak), if known',
         'Recorded only; it does not change the shortlist.', unit='um', family='transverse'),
)


def _m(id_, key, kind, wording, help_, **kw):
    kw.setdefault('group', 'More details')
    return _q(id_, 'mill', kw.pop('group'), key, kind, wording, help_, **kw)


def _p(id_, key, kind, wording, help_, **kw):
    kw.setdefault('group', 'More details')
    return _q(id_, 'rolling', kw.pop('group'), key, kind, wording, help_, **kw)


PASS_QUESTIONS = (
    _p('product', 'material.product', 'choice', 'Which product is it?',
       'The thin-gauge catalogue. With a product the tool checks the pass against the published '
       'range for it (a literature check that never changes the shortlist) and can suggest '
       'typical values to start from.', choices=_product_choices(), group='The product'),
    _p('entry_gauge', 'pass.entry_thickness_m', 'number',
       'Entry gauge of the pass where the bands show', 'Thickness going into the roll gap.',
       unit='um', ask_first=True, group='The pass'),
    _p('exit_gauge', 'pass.exit_thickness_m', 'number',
       'Exit gauge of the pass where the bands show', 'Thickness coming out of the roll gap.',
       unit='um', ask_first=True, group='The pass'),
    _p('strip_width', 'pass.width_m', 'number', 'Strip width', 'Width of the strip rolled.',
       unit='mm', ask_first=True, group='The pass'),
    _p('exit_speed', 'pass.exit_speed_m_s', 'number', 'Exit speed',
       'Steady exit speed of the pass.', unit='m_min', ask_first=True, group='The pass',
       hi_si=bsig.MAX_EXIT_SPEED_M_S),
    _p('flow_stress', 'pass.mean_flow_stress_pa', 'number', 'Mean flow stress in the pass',
       'From the setup model; the as-rolled tensile strength is a usable indicator.',
       unit='mpa'),
    _p('entry_tension', 'pass.entry_tension_pa', 'number', 'Entry tension (stress)',
       'Back tension divided by the strip cross-section.', unit='mpa'),
    _p('exit_tension', 'pass.exit_tension_pa', 'number', 'Exit tension (stress)',
       'Front tension divided by the strip cross-section.', unit='mpa'),
    _p('alloy', 'material.alloy', 'text', 'Alloy', 'For example 1235 or 8011. A prefix such as '
       'AA or EN AW- is fine.', group='Material'),
    _p('temper', 'material.temper', 'text', 'Temper', 'For example H18 or O.', group='Material'),
    _p('alloy_stated', 'material.alloy_temper_stated', 'yesno',
       'Are alloy and temper the plant\'s own statement?',
       '"No" means they are the literature suggestion for this product and gauge, still to be '
       'checked with the plant.', group='Material'),
    _p('yield_stress', 'material.yield_stress_pa', 'number', 'Yield stress', 'Proof stress of '
       'the strip.', unit='mpa', group='Material'),
    _p('youngs_modulus', 'material.youngs_modulus_pa', 'number', 'Elastic modulus of the strip',
       'About 70 GPa for aluminium.', unit='gpa', group='Material'),
    _p('luders_strain', 'material.luders_strain', 'number', 'Yield-point (Lüders) strain',
       'Length of the yield plateau in a tensile test; 0 or unknown for cold-worked strip.',
       unit='percent', group='Material'),
    _p('magnesium', 'material.magnesium_wt_pct', 'number', 'Magnesium content',
       'Weight per cent.', unit='ratio', group='Material'),
    _p('grain_size', 'material.grain_size_m', 'number', 'Grain size', 'Mean grain size.',
       unit='um', group='Material'),
    _p('doubled', 'material.final_pass_doubled', 'yesno',
       'Is the thinnest pass rolled doubled (two sheets in one roll gap)?',
       'Only read for foil below 100 µm. The tool models one sheet in the gap.' + YESNO_HELP,
       group='Material'),
    _p('route', 'schedule', 'list', 'The other passes of the route',
       'Add the passes before and after the one where the bands show. The tool uses them for '
       'the "thinner or thicker" pictures.',
       fields=(Field('label', 'Pass name', kind='text'),
               Field('entry_thickness_m', 'Entry gauge', unit='um'),
               Field('exit_thickness_m', 'Exit gauge', unit='um'),
               Field('mean_flow_stress_pa', 'Flow stress', unit='mpa'),
               Field('friction_coefficient', 'Friction', unit='ratio'),
               Field('entry_tension_pa', 'Entry tension', unit='mpa'),
               Field('exit_tension_pa', 'Exit tension', unit='mpa'),
               Field('exit_speed_m_s', 'Exit speed', unit='m_min')), group='The route'),
    _p('hardening_law', 'hardening.law', 'choice', 'Work-hardening law',
       'Only if you have a fitted hardening law for this alloy.',
       choices=_choices(tuple(bproc.HARDENING_LAW_KEYS), HARDENING_WORDS), group='Hardening'),
    _p('hardening_source', 'hardening.provenance', 'text', 'Where the hardening law comes from',
       'Paper, test report or supplier.', group='Hardening'),
    _p('hardening_prior_strain', 'hardening.prior_equivalent_strain', 'number',
       'Strain before the reference gauge', 'Equivalent strain already in the strip at the '
       'reference (annealed) gauge.', unit='ratio', group='Hardening'),
    _p('hardening_reference_gauge', 'hardening.reference_thickness_m', 'number',
       'Reference (annealed) gauge', 'Gauge at which the strip was last annealed.', unit='um',
       group='Hardening'),
    _p('hardening_use', 'hardening.use_computed_flow_stress', 'yesno',
       'Use the hardening law instead of the flow stresses typed in?', YESNO_HELP.strip(),
       group='Hardening'),
    _p('power_yield', 'hardening.yield_stress_pa', 'number', 'Power law: yield stress', 'MPa.',
       unit='mpa', group='Hardening'),
    _p('power_k', 'hardening.strength_coefficient_pa', 'number',
       'Power law: strength coefficient', 'MPa.', unit='mpa', group='Hardening'),
    _p('power_n', 'hardening.exponent', 'number', 'Power law: exponent', 'Dimensionless.',
       unit='ratio', group='Hardening'),
    _p('voce_initial', 'hardening.initial_stress_pa', 'number', 'Voce law: initial stress',
       'MPa.', unit='mpa', group='Hardening'),
    _p('voce_saturation', 'hardening.saturation_stress_pa', 'number',
       'Voce law: saturation stress', 'MPa.', unit='mpa', group='Hardening'),
    _p('voce_strain', 'hardening.characteristic_strain', 'number',
       'Voce law: characteristic strain', 'Dimensionless.', unit='ratio', group='Hardening'),
    _p('voce_slope', 'hardening.stage_iv_slope_pa', 'number', 'Voce law: late hardening slope',
       'MPa.', unit='mpa', group='Hardening'),
    _p('incoming_hardness_variation', 'incoming_variation.flow_stress_variation_fraction',
       'number', 'Hardness variation of the incoming coil',
       'Relative variation of the flow stress along the incoming coil.', unit='percent',
       group='Incoming coil', hi_si=0.5),
    _p('incoming_once_per_turn', 'incoming_variation.coil_synchronous', 'yesno',
       'Does that variation repeat once per decoiler turn?', YESNO_HELP.strip(),
       group='Incoming coil'),
    _p('bite_heat', 'width_model.bite_heat_per_width_w_m', 'number',
       'Heat made in the roll gap per metre of width',
       'Normally computed. Needed only when no roll-gap model solves the pass (foil).',
       unit='kw_m', group='Case-specific width inputs'),
    _p('gap_crown', 'width_model.gap_crown_m', 'number', 'Roll-gap crown',
       'Thickness difference centre to edge set by the roll gap.', unit='um',
       group='Case-specific width inputs'),
    _p('entry_crown', 'width_model.entry_crown_m', 'number', 'Entry strip crown',
       'Thickness difference centre to edge of the incoming strip.', unit='um',
       group='Case-specific width inputs'),
    _p('incoming_ridges', 'width_model.incoming_ridges', 'list',
       'Ridges (local high spots) in the incoming strip',
       'From an entry profile scan. ' + EDGE_HELP,
       fields=(Field('position_m', 'Position', unit='pos_mm'),
               Field('height_m', 'Height', unit='um'), Field('width_m', 'Width', unit='mm')),
       group='Case-specific width inputs'),
    _p('previous_widths', 'width_model.previous_strip_widths_m', 'numbers',
       'Widths of narrower strip rolled earlier on the same work rolls',
       'Since the last work-roll change.', unit='mm', group='Case-specific width inputs'),
    _p('lateral_stress', 'width_model.lateral_compressive_stress_pa', 'number',
       'Sideways compressive stress in the span', 'Needed for the trough check; negative is '
       'compression.', unit='mpa', group='Case-specific width inputs'),
    _p('shape_stiffness', 'width_model.shape_inputs.strip_stiffness_per_width_pa', 'number',
       'Plant model: strip stiffness per width',
       'From a plant foil model, when no roll-gap model solves the pass.', unit='gpa',
       group='Plant foil model'),
    _p('shape_sensitivity',
       'width_model.shape_inputs.exit_tension_force_sensitivity_per_width_m', 'number',
       'Plant model: force sensitivity to exit tension per width', 'Metres.', unit='n_m_pa',
       group='Plant foil model'),
    _p('shape_half_length', 'width_model.shape_inputs.bite_half_length_m', 'number',
       'Plant model: half the contact length in the roll gap', 'Millimetres.', unit='mm',
       group='Plant foil model'),
    _p('shape_source', 'width_model.shape_inputs.provenance', 'text',
       'Plant model: where these values come from', 'Model name and version.',
       group='Plant foil model'),
)

FAULT_QUESTIONS = (
    _q('nozzle_levels', 'mill', 'Spray header', 'width_model.nozzle_levels', 'nozzles',
       'Which nozzles are weak or blocked?',
       'Click a nozzle on the drawing to cycle healthy, weak and blocked, or type each flow '
       'level (1 = full flow, 0 = blocked). Leave it at "Don\'t know" if nobody has checked. '
       'The drawing shows the nozzle state the model will use.',
       unit='ratio', ask_first=True, unknown='null'),
    _q('blocked_nozzles', 'mill', 'Spray header', 'width_model.blocked_nozzle_indices',
       'numbers', 'Blocked nozzles (by number)', 'Nozzle numbers counted from the first nozzle '
       '(1 = first nozzle). The same nozzles as the blocked ones on the drawing: a number typed '
       'here is marked blocked there, and a number removed here is marked healthy again.',
       unit='nozzle_no', unknown='empty'),
    _q('coverage_blocked_nozzles', 'mill', 'Spray header', 'coolant.blocked_nozzle_indices',
       'numbers', 'Blocked nozzles for the simple coverage check (by number)',
       'The simple coverage check only knows on and off. When its header is the spray header '
       'drawn above, it uses the drawing: every nozzle marked weak or blocked there counts as '
       'not spraying. Only a case whose coverage header differs needs its own numbers here; '
       '1 = first nozzle.', unit='nozzle_no',
       unknown='empty'),
    _q('valve_events', 'mill', 'Spray header', 'width_model.events', 'list',
       'Cooling valve switching events you know of',
       'A valve closed or a nozzle blocking for a while: when it started, how long, which '
       'nozzles (numbers from 1) and the flow level during the event.',
       fields=(Field('start_s', 'Start', unit='s'), Field('duration_s', 'Duration', unit='s'),
               Field('nozzle_indices', 'Nozzles', kind='numbers', unit='nozzle_no'),
               Field('level', 'Flow level', unit='ratio'),
               Field('label', 'Note', kind='text')), unknown='empty'),
)

MILL_QUESTIONS = (
    _m('wr_diameter', 'pass.work_roll_radius_m', 'number', 'Work-roll diameter',
       'The current ground diameter, not the new-roll size.', unit='mm_dia', ask_first=True,
       group='Rolls and stand'),
    _m('friction', 'pass.friction_coefficient', 'number', 'Friction coefficient in the roll gap',
       'No catalogue value exists; back-calculated from roll force and forward slip, or from '
       'the setup model. The demos use 0.03. The result depends strongly on it.', unit='ratio',
       ask_first=True, group='Rolls and stand'),
    _m('mill_modulus', 'stand.housing_stiffness_n_m', 'number', 'Mill modulus (housing stiffness)',
       'From the mill-modulus (stretch) test or the gauge-control setup.', unit='kn_mm',
       ask_first=True, group='Rolls and stand'),
    _m('roll_contact_stiffness', 'stand.work_backup_contact_stiffness_n_m', 'number',
       'Work-roll to backup-roll contact stiffness',
       'Stand designer\'s data or a roll-contact calculation.', unit='kn_mm',
       group='Rolls and stand'),
    _m('wr_mass', 'stand.work_roll_mass_kg', 'number', 'Work-roll assembly mass',
       'Roll, necks, chocks and bearings of one work roll.', unit='kg', group='Rolls and stand'),
    _m('bur_mass', 'stand.backup_roll_mass_kg', 'number', 'Backup-roll assembly mass',
       'Roll, necks, chocks and bearings of one backup roll.', unit='kg',
       group='Rolls and stand'),
    _m('stand_damping', 'stand.modal_damping_ratio', 'number', 'Damping of the stand vibration',
       'From a modal or tap test; 0.03 is the demo value.', unit='ratio',
       group='Rolls and stand'),
    _m('roll_modulus', 'stand.roll_youngs_modulus_pa', 'number', 'Roll elastic modulus',
       'Forged steel about 210 GPa.', unit='gpa', group='Rolls and stand'),
    _m('roll_poisson', 'stand.roll_poisson_ratio', 'number', 'Roll Poisson ratio',
       'Forged steel about 0.3.', unit='ratio', group='Rolls and stand'),
    _m('bur_diameter', 'kinematics.backup_roll_diameter_m', 'number', 'Backup-roll diameter',
       'Current ground diameter.', unit='mm', group='Rolls and stand'),
    _m('entry_span', 'spans.entry_span_length_m', 'number', 'Free strip length before the roll gap',
       'From the roll gap to the first roll on the entry side. A span is the free length of '
       'strip between two rolls.', unit='mm', group='Spans'),
    _m('exit_span', 'spans.exit_span_length_m', 'number', 'Free strip length after the roll gap',
       'From the roll gap to the first roll on the exit side.', unit='mm', ask_first=True,
       group='Spans'),
    _m('strip_modulus_spans', 'spans.strip_youngs_modulus_pa', 'number',
       'Strip modulus used for the spans', '70 GPa for aluminium.', unit='gpa', group='Spans'),
    _m('gear_meshes', 'kinematics.gear_meshes', 'list', 'Gear meshes in the drive',
       'Teeth and speed ratio to the work roll; needed to check gear-borne marks.',
       fields=(Field('name', 'Name', kind='text'), Field('teeth', 'Teeth', unit='count'),
               Field('shaft_speed_ratio_to_work_roll', 'Speed ratio to work roll',
                     unit='ratio')), group='Drive and bearings'),
    _m('bearings', 'kinematics.bearings', 'list', 'Roll bearings',
       'Rolling elements, element and pitch diameters, contact angle; needed to check '
       'bearing-borne marks.',
       fields=(Field('name', 'Name', kind='text'),
               Field('shaft', 'Roll', kind='choice', choices=_choices(ROLL_VALUES, ROLL_WORDS)),
               Field('elements', 'Rolling elements', unit='count'),
               Field('element_diameter_m', 'Element diameter', unit='mm'),
               Field('pitch_diameter_m', 'Pitch diameter', unit='mm'),
               Field('contact_angle_rad', 'Contact angle', unit='deg')),
       group='Drive and bearings'),
    _m('grinder_marks', 'kinematics.grinder_marks', 'list',
       'Known grinder or chatter marks on a roll',
       'Marks per circumference counted on the roll.',
       fields=(Field('roll', 'Roll', kind='choice', choices=_choices(ROLL_VALUES, ROLL_WORDS)),
               Field('marks_per_circumference', 'Marks per turn', unit='count')),
       group='Drive and bearings'),
    _m('deflector_diameters', 'kinematics.deflector_roll_diameters_m', 'numbers',
       'Deflector roll diameters', 'Every deflector or idler roll the strip wraps.', unit='mm',
       group='Drive and bearings'),
    _m('entry_coil_diameter', 'kinematics.entry_coil_diameter_m', 'number',
       'Entry coil diameter', 'Typical diameter of the coil being unwound.', unit='mm',
       group='Drive and bearings'),
    _m('exit_coil_diameter', 'kinematics.exit_coil_diameter_m', 'number',
       'Exit coil diameter', 'Typical diameter of the coil being wound.', unit='mm',
       group='Drive and bearings'),
    _m('drive_inertias', 'drive.inertias_kg_m2', 'numbers', 'Drive-train inertias',
       'Motor to roll, in order.', unit='kg_m2', group='Drive and bearings'),
    _m('drive_stiffnesses', 'drive.stiffnesses_n_m_rad', 'numbers', 'Drive shaft stiffnesses',
       'One fewer than the inertias.', unit='knm_rad', group='Drive and bearings'),
    _m('barrel_length', 'width_model.roll.barrel_length_m', 'number', 'Work-roll barrel length',
       'Length of the roll face.', unit='mm', ask_first=True, group='Spray header',
       also_keys=('coolant.barrel_length_m',)),
    _m('nozzle_pitch', 'width_model.spray_header.nozzle_pitch_m', 'number',
       'Distance between nozzles', 'Nozzle pitch along the header.', unit='mm', ask_first=True,
       group='Spray header', also_keys=('coolant.nozzle_pitch_m',)),
    _m('nozzle_standoff', 'width_model.spray_header.standoff_m', 'number',
       'Nozzle distance from the roll', 'Stand-off of the nozzle tips.', unit='mm',
       group='Spray header', also_keys=('coolant.standoff_m',)),
    _m('spray_angle', 'width_model.spray_header.spray_angle_rad', 'number', 'Spray fan angle',
       'Full fan angle of one nozzle.', unit='deg', group='Spray header',
       also_keys=('coolant.spray_angle_rad',)),
    _m('offset_angle', 'width_model.spray_header.offset_angle_rad', 'number',
       'Nozzle offset angle', 'Twist of the fan against the header.', unit='deg',
       group='Spray header', also_keys=('coolant.offset_angle_rad',)),
    _m('spray_htc', 'width_model.spray_header.spray_mean_htc_w_m2k', 'number',
       'Spray cooling strength (heat-transfer coefficient)',
       'Not pinned down in the literature: 2500-4300 W/(m²·K) simulated for kerosene on a work '
       'roll. The stripe heights fall as it rises.', unit='w_m2k', ask_first=True,
       group='Spray header'),
    _m('background_htc', 'width_model.spray_header.background_htc_w_m2k', 'number',
       'Cooling between the sprays', 'Background heat-transfer coefficient.', unit='w_m2k',
       group='Spray header'),
    _m('coolant_temperature', 'width_model.coolant_temperature_k', 'number',
       'Coolant temperature', 'At the nozzles.', unit='degc', group='Spray header'),
    _m('cooling_zone_pitch', 'width_model.cooling_zone_pitch_m', 'number',
       'Width of one cooling zone', 'From the flatness-controller zone map.', unit='mm',
       group='Spray header'),
    _m('strip_centre', 'width_model.strip_centre_m', 'number', 'Strip centre on the barrel',
       'Leave unknown when the strip runs centred on the roll.', unit='mm',
       group='Spray header'),
    _m('roll_heat_fraction', 'width_model.roll_heat_fraction_per_roll', 'number',
       'Share of the roll-gap heat into each work roll',
       'Usually left empty: it then follows from the strip share below.', unit='percent',
       group='Heat'),
    _m('strip_heat_share', 'tribology.strip_heat_fraction', 'number',
       'Share of the roll-gap heat that stays in the strip',
       'An assumption unless measured; the only measured foil-mill value is 11-33 %. The stripe '
       'heights scale with the heat going into the rolls.', unit='percent', ask_first=True,
       group='Heat'),
    _m('rolls_carrying_stripe', 'width_model.rolls_carrying_stripe', 'choice',
       'How many work rolls carry the stripe?', '1 if one header is affected, 2 if both.',
       choices=((1, 'One work roll'), (2, 'Both work rolls')), group='Heat'),
    _m('shape_coefficient', 'width_model.shape_disturbing_coefficient', 'number',
       'Shape-disturbing coefficient', 'Analyst value; leave unknown for the default.',
       unit='ratio', group='Heat'),
    _m('heredity_coefficient', 'width_model.heredity_coefficient', 'number',
       'Profile heredity coefficient', 'Analyst value; leave unknown for the default.',
       unit='ratio', group='Heat'),
    _m('roll_conductivity', 'width_model.roll.conductivity_w_mk', 'number',
       'Roll thermal conductivity', 'From the roll supplier.', unit='w_mk', group='Roll material'),
    _m('roll_density', 'width_model.roll.density_kg_m3', 'number', 'Roll density',
       'From the roll supplier.', unit='kg_m3', group='Roll material'),
    _m('roll_specific_heat', 'width_model.roll.specific_heat_j_kgk', 'number',
       'Roll specific heat', 'From the roll supplier.', unit='j_kgk', group='Roll material'),
    _m('roll_expansion', 'width_model.roll.expansion_coefficient_per_k', 'number',
       'Roll thermal expansion', 'From the roll supplier.', unit='um_per_mk',
       group='Roll material'),
    _m('roll_poisson_thermal', 'width_model.roll.poisson_ratio', 'number',
       'Roll Poisson ratio (thermal model)', 'About 0.3.', unit='ratio', group='Roll material'),
    _m('roll_constraint', 'width_model.roll.expansion_constraint', 'choice',
       'How the roll expands along the barrel', 'Analyst choice.',
       choices=_choices(rt.EXPANSION_CONSTRAINTS, CONSTRAINT_WORDS), group='Roll material'),
    _m('coverage_expansion', 'coolant.roll_expansion_coefficient_per_k', 'number',
       'Roll expansion for the simple coverage check', 'Used by the spray coverage screen.',
       unit='um_per_mk', group='Roll material'),
    _m('coverage_excess_temperature', 'coolant.assumed_excess_temperature_k', 'number',
       'Assumed extra roll temperature under a blocked nozzle', 'For the simple coverage '
       'check.', unit='kelvin', group='Roll material'),
    _m('oil_viscosity_simple', 'lubrication.viscosity_pa_s', 'number',
       'Rolling-oil viscosity (simple film check)', 'At the inlet temperature.', unit='mpa_s',
       group='Rolling oil'),
    _m('oil_pv_simple', 'lubrication.pressure_viscosity_coefficient_per_pa', 'number',
       'Oil pressure-viscosity coefficient (simple film check)', 'From the oil supplier.',
       unit='per_gpa', group='Rolling oil'),
    _m('roll_roughness_simple', 'lubrication.roll_roughness_rq_m', 'number',
       'Work-roll roughness Rq (simple film check)', 'Measured on the roll.', unit='um',
       group='Rolling oil'),
    _m('strip_roughness_simple', 'lubrication.strip_roughness_rq_m', 'number',
       'Strip roughness Rq (simple film check)', 'Measured on the strip.', unit='um',
       group='Rolling oil'),
    _m('oil_viscosity', 'tribology.lubricant.viscosity_ref_pa_s', 'number',
       'Rolling-oil viscosity at the reference temperature', 'From the oil supplier sheet.',
       unit='mpa_s', group='Rolling oil'),
    _m('oil_reference_temperature', 'tribology.lubricant.reference_temperature_k', 'number',
       'Reference temperature of that viscosity', 'From the oil supplier sheet.', unit='degc',
       group='Rolling oil'),
    _m('oil_temperature_coefficient',
       'tribology.lubricant.temperature_viscosity_coefficient_per_k', 'number',
       'How fast the viscosity falls with temperature', 'Per kelvin.', unit='per_k',
       group='Rolling oil'),
    _m('oil_pv', 'tribology.lubricant.pressure_viscosity_coefficient_per_pa', 'number',
       'Oil pressure-viscosity coefficient', 'From the oil supplier.', unit='per_gpa',
       group='Rolling oil'),
    _m('oil_conductivity', 'tribology.lubricant.conductivity_w_mk', 'number',
       'Oil thermal conductivity', 'Leave unknown for the default.', unit='w_mk',
       group='Rolling oil'),
    _m('oil_name', 'tribology.lubricant.name', 'text', 'Rolling-oil name', 'For the record.',
       group='Rolling oil'),
    _m('roll_roughness', 'tribology.surface_finish.roll_roughness_rq_m', 'number',
       'Work-roll roughness Rq', 'Measured on the roll.', unit='um', group='Rolling oil'),
    _m('strip_roughness', 'tribology.surface_finish.strip_roughness_rq_m', 'number',
       'Strip roughness Rq', 'Measured on the strip.', unit='um', group='Rolling oil'),
    _m('closure_mu_b', 'tribology.friction_closure.mu_b', 'number',
       'Placeholder friction law: boundary friction', 'The friction law is a placeholder and '
       'not fitted; leave unknown unless you have a fit.', unit='ratio', group='Rolling oil'),
    _m('closure_mu_v', 'tribology.friction_closure.mu_v', 'number',
       'Placeholder friction law: film friction', 'See above.', unit='ratio',
       group='Rolling oil'),
    _m('closure_lambda0', 'tribology.friction_closure.lambda0', 'number',
       'Placeholder friction law: transition film ratio', 'See above.', unit='ratio',
       group='Rolling oil'),
    _m('oil_inlet_temperature', 'tribology.inlet_temperature_k', 'number',
       'Oil temperature at the roll gap inlet', 'Battery foil plants report 40-45 °C.',
       unit='degc', group='Rolling oil'),
    _m('strip_entry_temperature', 'tribology.strip_entry_temperature_k', 'number',
       'Strip temperature entering the pass', 'Coil temperature before the pass.', unit='degc',
       group='Rolling oil'),
    _m('temperature_limit', 'tribology.temperature_limit_k', 'number',
       'Strip temperature limit to check against', 'For example a coil limit.', unit='degc',
       group='Rolling oil'),
    _m('oil_flash_point', 'tribology.oil_flash_point_k', 'number',
       'Flash point of the rolling oil', 'From the oil data sheet.', unit='degc',
       group='Rolling oil'),
    _m('oil_supply_temperature_cap', 'tribology.oil_supply_temperature_cap_k', 'number',
       'Highest oil supply temperature your site allows',
       'A site or insurer limit, if there is one.', unit='degc', group='Rolling oil'),
    _m('thermal_correction', 'tribology.thermal_correction', 'yesno',
       'Correct the oil film for inlet heating?', YESNO_HELP.strip(), group='Rolling oil'),
    _m('use_computed_friction', 'tribology.use_computed_friction', 'yesno',
       'Replace the friction typed in by the placeholder friction law?',
       'Normally no: the law is not fitted.', group='Rolling oil'),
    _m('agc_gain', 'gauge_control.compensation_gain', 'number', 'Gauge-control compensation gain',
       'From the gauge-control commissioning sheet, 0 to 1.', unit='ratio',
       group='Gauge control'),
    _m('agc_bandwidth', 'gauge_control.bandwidth_hz', 'number', 'Cylinder bandwidth',
       'From the gauge-control commissioning sheet.', unit='hz', group='Gauge control'),
    _m('agc_filter', 'gauge_control.force_filter_hz', 'number', 'Force filter',
       'Leave unknown if there is none.', unit='hz', group='Gauge control'),
    _m('coil_inner', 'width_model.coil.inner_radius_m', 'number', 'Wound coil inner radius',
       'Sleeve or mandrel radius.', unit='mm', group='Coil and deflector'),
    _m('coil_outer', 'width_model.coil.outer_radius_m', 'number', 'Wound coil outer radius',
       'Full coil radius.', unit='mm', group='Coil and deflector'),
    _m('winding_tension', 'width_model.coil.winding_tension_pa', 'number',
       'Winding tension (stress)',
       'Rewind tension divided by the strip cross-section.', unit='mpa',
       group='Coil and deflector'),
    _m('coil_compaction', 'width_model.coil.compaction_factor', 'number', 'Coil compaction factor',
       'Analyst choice; leave unknown for the default 0.5.', unit='ratio',
       group='Coil and deflector'),
    _m('deflector_radius', 'width_model.deflector_roll_radius_m', 'number',
       'Deflector (or ironing) roll diameter after the gap', 'For the wrinkle check.',
       unit='mm_dia', group='Coil and deflector'),
    _m('grinding_traverse', 'width_model.grinding.traverse_speed_m_s', 'number',
       'Roll grinder traverse speed', 'From the grinder settings.', unit='mm_s',
       group='Coil and deflector'),
    _m('grinding_rotation', 'width_model.grinding.roll_rotation_hz', 'number',
       'Roll rotation on the grinder', 'Turns per second.', unit='hz', group='Coil and deflector'),
    _m('bite_model', 'model_options.bite_model', 'choice', 'Roll-gap model',
       'Keep the starting point\'s choice unless you know why.',
       choices=_choices(bd.BITE_MODELS, BITE_MODEL_WORDS), group='Model settings'),
    _m('bite_damping', 'model_options.bite_damping_transit_fraction', 'number',
       'Roll-gap damping fraction', 'A heuristic; the results without it are always shown.',
       unit='ratio', group='Model settings'),
    _m('max_radius_ratio', 'model_options.max_radius_ratio', 'number',
       'Flattening limit', 'Keep the default.', unit='ratio', group='Model settings'),
    _m('cells', 'model_options.cells', 'number', 'Roll-gap cells', 'Keep the default.',
       unit='count', group='Model settings'),
    _m('thermal_sensitivity', 'model_options.thermal_sensitivity', 'choice',
       'Heat-share sensitivity table', 'How much is recomputed for the sensitivity table. The '
       'quick run turns it off.', choices=_choices(bthermal.MODES, THERMAL_SENS_WORDS),
       group='Model settings'),
    _m('numerics_cell', 'width_model.numerics.axial_cell_m', 'number',
       'Roll temperature grid: cell along the barrel', 'Keep the default.', unit='mm',
       group='Model settings'),
    _m('numerics_radial', 'width_model.numerics.radial_cells', 'number',
       'Roll temperature grid: radial cells', 'Keep the default.', unit='count',
       group='Model settings'),
    _m('numerics_step', 'width_model.numerics.time_step_s', 'number',
       'Roll temperature grid: time step', 'Keep the default.', unit='s',
       group='Model settings'),
)

QUESTIONS = tuple(q.validate() for q in OBSERVATION_QUESTIONS + PASS_QUESTIONS + FAULT_QUESTIONS
                  + MILL_QUESTIONS)
QUESTION_BY_ID = {q.id: q for q in QUESTIONS}
if len(QUESTION_BY_ID) != len(QUESTIONS):
    raise RuntimeError('duplicate question id')
QUESTION_BY_KEY = {k: q for q in QUESTIONS for k in (q.key,) + q.also_keys}

# nullable sub-objects the form may create when the starting point has none:
# path -> (plain name, required keys, defaults)
SECTIONS = {
    'gauge_control': ('gauge control', ('compensation_gain', 'bandwidth_hz'),
                      {'force_filter_hz': None}),
    'incoming_variation': ('the incoming-coil variation',
                           ('flow_stress_variation_fraction', 'coil_synchronous'), {}),
    'drive': ('the drive train', ('inertias_kg_m2', 'stiffnesses_n_m_rad'), {}),
    'hardening': ('the hardening law', ('law', 'prior_equivalent_strain',
                                        'reference_thickness_m', 'use_computed_flow_stress'),
                  {'provenance': 'entered in the band app'}),
    'width_model.coil': ('the wound coil', ('inner_radius_m', 'outer_radius_m',
                                            'winding_tension_pa'), {'compaction_factor': None}),
    'width_model.grinding': ('the roll grinder', ('traverse_speed_m_s', 'roll_rotation_hz'), {}),
    'width_model.numerics': ('the roll temperature grid', (), dict(bw.DEFAULT_NUMERICS)),
    'width_model.shape_inputs': ('the plant foil-model inputs',
                                 ('strip_stiffness_per_width_pa',
                                  'exit_tension_force_sensitivity_per_width_m',
                                  'bite_half_length_m'),
                                 {'provenance': 'entered in the band app'}),
    'tribology.friction_closure': ('the placeholder friction law', ('mu_b', 'mu_v', 'lambda0'),
                                   {}),
}
SECTION_NAMES = {'width_model': 'a roll thermal model (width model)',
                 'tribology': 'rolling-oil data (tribology)', 'lubrication': 'a simple oil film '
                 'check', 'coolant': 'a simple spray coverage check'}


def questions(step=None):
    """The question table as JSON-ready dicts (optionally one step)."""
    return [q.to_dict() for q in QUESTIONS if step is None or q.step == step]


def ask_first_ids(family=None, exit_thickness_m=None):
    """Ids of the 'ask first' observation questions for a kind of band (None: both kinds)."""
    out = []
    for q in QUESTIONS:
        if q.step != 'see' or not q.ask_first:
            continue
        if q.family == 'foil':
            if family == 'transverse' or exit_thickness_m is None or \
                    exit_thickness_m >= bw.FOIL_GAUGE_M:
                continue
        elif q.family not in ('both', family) and family is not None:
            continue
        out.append(q.id)
    return out


# ============================================================================= case access
def _get(case, key):
    cur = case
    for part in key.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _has_path(case, key):
    cur = case
    for part in key.split('.')[:-1]:
        if not isinstance(cur, dict) or not isinstance(cur.get(part), dict):
            return False
        cur = cur[part]
    return isinstance(cur, dict)


def strip_edge_m(case):
    """Barrel coordinate [m] of the strip edge on the header-start side, by the engine's own
    convention (``band_width.Facts``): strip centre = ``width_model.strip_centre_m``, else half
    the width-model barrel, else half the coolant barrel; 0 when neither section exists."""
    w = case.get('width_model')
    width = case['pass']['width_m']
    if w is not None:
        centre = (w['strip_centre_m'] if w.get('strip_centre_m') is not None
                  else w['roll']['barrel_length_m'] / 2)
    elif case.get('coolant') is not None:
        centre = case['coolant']['barrel_length_m'] / 2
    else:
        return 0.0
    return centre - width / 2


def nozzle_layout(case):
    """Nozzle positions [m] on the barrel of the case's spray header (``roll_thermal.
    SprayHeader``, the engine's layout), or [] without a width model."""
    w = case.get('width_model')
    if w is None:
        return []
    h = w['spray_header']
    header = rt.SprayHeader(nozzle_pitch_m=h['nozzle_pitch_m'], standoff_m=h['standoff_m'],
                            spray_angle_rad=h['spray_angle_rad'],
                            offset_angle_rad=h['offset_angle_rad'],
                            spray_mean_htc_w_m2k=h['spray_mean_htc_w_m2k'],
                            background_htc_w_m2k=h['background_htc_w_m2k'])
    return list(header.nozzle_positions(w['roll']['barrel_length_m']))


def coverage_layout(case):
    """Nozzle positions [m] of the simple coverage check's header (``band_signatures.
    spray_coverage``, the engine's layout), or [] without a coolant section."""
    c = case.get('coolant')
    if c is None:
        return []
    return list(bsig.spray_coverage(c['barrel_length_m'], c['nozzle_pitch_m'], c['standoff_m'],
                                    c['spray_angle_rad'], c['offset_angle_rad'])
                ['nozzle_positions_m'])


def same_spray_header(case):
    """True when the width model's spray header and the coverage check's header have the same
    nozzles (count, and positions within 1 µm). Then they are one physical header and the band
    app keeps ONE set of nozzle marks for both (``canonical_nozzles``)."""
    try:
        a, b = nozzle_layout(case), coverage_layout(case)
    except ValueError:
        return False
    return bool(a) and len(a) == len(b) and all(abs(x - y) <= 1e-6 for x, y in zip(a, b))


def effective_nozzle_levels(case):
    """The flow level of every nozzle that the width model simulates for this case, resolved
    by the engine itself (``band_width.spray_layout``: ``nozzle_levels``, else full flow, with
    every ``blocked_nozzle_indices`` entry at 0), or None without a width model."""
    if case.get('width_model') is None:
        return None
    return [float(x) for x in bw.spray_layout(case)['nozzle_levels']]


def coverage_blocked_from_levels(levels):
    """Coverage-check blocked nozzle indices for header levels: the check only knows on and
    off, so every nozzle below full flow (weak or blocked) counts as not spraying (the rule
    the worked examples follow)."""
    return [i for i, lv in enumerate(levels or []) if lv < 1.0]


def canonical_nozzles(case):
    """One set of nozzle marks (in place). A width model that marks nozzles at all keeps them
    as ``nozzle_levels`` = the engine's effective levels and no separate blocked list; when the
    coverage check has the same header, its blocked list is derived from those levels. The
    engine simulates exactly the same nozzle state before and after."""
    w = case.get('width_model')
    if w is None:
        return case
    if w.get('nozzle_levels') is not None or w.get('blocked_nozzle_indices'):
        w['nozzle_levels'] = effective_nozzle_levels(case)
        w['blocked_nozzle_indices'] = []
    if case.get('coolant') is not None and same_spray_header(case):
        case['coolant']['blocked_nozzle_indices'] = coverage_blocked_from_levels(
            w.get('nozzle_levels'))
    return case


def _num_si(q, label, value, unit, origin):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise AnswerError(f'"{label}" must be a number in '
                          f'{unit_label(unit) or "plain numbers"}', q.id)
    if unit == 'pos_mm':
        return value / 1e3 + origin
    return to_si(value, unit)


def _num_display(value, unit, origin):
    if unit == 'pos_mm':
        return _r12((value - origin) * 1e3)
    return from_si(value, unit)


def _field_si(q, f, value, origin):
    label = f'{q.wording}: {f.label}'
    if f.kind == 'number':
        return _num_si(q, label, value, f.unit, origin)
    if f.kind == 'numbers':
        if not isinstance(value, list):
            raise AnswerError(f'"{label}" must be a list of numbers', q.id)
        return [_num_si(q, label, v, f.unit, origin) for v in value]
    if f.kind == 'text':
        if value is None:
            return None
        if not isinstance(value, str):
            raise AnswerError(f'"{label}" must be text', q.id)
        return value.strip() or None
    if f.kind == 'yesno':
        if value is not None and not isinstance(value, bool):
            raise AnswerError(f'"{label}" must be yes, no or unknown', q.id)
        return value
    if value not in [c[0] for c in f.choices]:
        raise AnswerError(f'"{label}": choose one of the listed answers', q.id)
    return value


def _field_display(f, value, origin):
    if value is None:
        return None
    if f.kind == 'number':
        return _num_display(value, f.unit, origin)
    if f.kind == 'numbers':
        return [_num_display(v, f.unit, origin) for v in value]
    return value


def answer_to_si(q, value, origin_m=0.0):
    """One answer in display units -> the case value (SI). ``None`` means unknown."""
    if value is None:
        return None
    if q.kind == 'number':
        out = _num_si(q, q.wording, value, q.unit, origin_m)
        if q.lo_si is not None and out < q.lo_si or q.hi_si is not None and out > q.hi_si:
            raise AnswerError(f'"{q.wording}" is outside the range the tool accepts', q.id)
        return out
    if q.kind in ('positions', 'numbers', 'nozzles'):
        if not isinstance(value, list):
            raise AnswerError(f'"{q.wording}" must be a list of numbers', q.id)
        return [_num_si(q, q.wording, v, q.unit, origin_m) for v in value]
    if q.kind == 'yesno':
        if not isinstance(value, bool):
            raise AnswerError(f'"{q.wording}" must be yes, no or unknown', q.id)
        return value
    if q.kind == 'text':
        if not isinstance(value, str):
            raise AnswerError(f'"{q.wording}" must be text', q.id)
        return value.strip() or None
    if q.kind == 'choice':
        if value not in [c[0] for c in q.choices]:
            raise AnswerError(f'"{q.wording}": choose one of the listed answers', q.id)
        return value
    # list of records
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        raise AnswerError(f'"{q.wording}" must be a list of entries', q.id)
    out = []
    for item in value:
        rec = {}
        for f in q.fields:
            rec[f.name] = _field_si(q, f, item.get(f.name), origin_m)
        if q.key == 'schedule' and not rec.get('label'):
            rec['label'] = f'pass {len(out) + 1}'
        if q.key == 'width_model.events' and rec.get('label') is None:
            rec.pop('label')
        if q.key == 'kinematics.gear_meshes' and not rec.get('name'):
            rec['name'] = f'gear mesh {len(out) + 1}'
        if q.key == 'kinematics.bearings' and not rec.get('name'):
            rec['name'] = f'bearing {len(out) + 1}'
        out.append(rec)
    return out


def answer_from_si(q, value, origin_m=0.0):
    """One case value (SI) -> the answer in display units (``None`` when null)."""
    if value is None:
        return None
    if q.kind == 'number':
        return _num_display(value, q.unit, origin_m)
    if q.kind in ('positions', 'numbers', 'nozzles'):
        return [_num_display(v, q.unit, origin_m) for v in value]
    if q.kind == 'list':
        return [{f.name: _field_display(f, item.get(f.name), origin_m) for f in q.fields}
                for item in value]
    return value


def _empty(value):
    return value is None or value == []


# ============================================================================= presets
WORKED_EXAMPLES = (
    ('example_battery_foil', 'band_diagnosis_battery_foil.json', 'Worked example: battery foil',
     'Battery foil 50 -> 30 µm on the synthetic foil mill, lengthwise bands at two places. The '
     'observations were generated by the model, not seen on a plant.'),
    ('example_lengthwise_bands', 'band_diagnosis_lengthwise_bands.json',
     'Worked example: lengthwise bands on sheet',
     'Sheet 300 -> 210 µm on the synthetic sheet mill, bands along the strip at three places. '
     'The observations were generated by the model, not seen on a plant.'),
    ('example_thin_gauge_chatter', 'band_diagnosis_thin_gauge_chatter.json',
     'Worked example: marks across thin sheet',
     'Transverse marks whose spacing grows with speed. The observations were generated by the '
     'model, not seen on a plant.'),
    ('example_bearing_order', 'band_diagnosis_bearing_order.json',
     'Worked example: marks with a fixed spacing',
     'Transverse marks whose spacing stays the same at two speeds, modelled on a published '
     'case. The observations were generated by the model, not seen on a plant.'),
)
MILL_PRESETS = (
    ('foil_mill', 'foil', 'Typical foil mill',
     'The synthetic single-stand four-high foil mill of the battery-foil demo (barrel 1.5 m, '
     'work rolls 270 mm). Typical values, not your mill.'),
    ('sheet_mill', 'sheet', 'Typical sheet mill',
     'The synthetic single-stand four-high sheet mill of the lengthwise demo (barrel 1.7 m, '
     'work rolls 400 mm). Typical values, not your mill.'),
)


def as_v2(case):
    """A validated ``physicroll.band_case.v2`` copy of a v1 or v2 case (v1 gains null v2
    sections and observation fields, as ``band_diagnosis.validate_case`` normalises them)."""
    out = bd.validate_case(case)
    out['case_schema'] = bd.CASE_SCHEMA_V2
    for k in bw.OBS_V2_ALL:
        out['observation'].setdefault(k, None)
    out = json.loads(json.dumps(out, allow_nan=False))
    bd.validate_case(out)
    return out


def presets(worked_examples=None):
    """Named starting points: the two packaged mills of the product survey and, when the
    caller supplies them (``{example_id: case dict}``, read from ``scenarios/``), the four demo
    scenarios as worked examples. Each: id, label, description, kind, generated_by_model,
    case (a validated v2 case)."""
    out = []
    for pid, kind, label, desc in MILL_PRESETS:
        out.append({'id': pid, 'label': label, 'description': desc, 'kind': 'mill',
                    'mill_kind': kind, 'generated_by_model': False,
                    'case': as_v2(bsurvey.default_mill_case(kind))})
    for pid, filename, label, desc in WORKED_EXAMPLES:
        if worked_examples and pid in worked_examples:
            out.append({'id': pid, 'label': label, 'description': desc, 'kind': 'example',
                        'source_file': filename, 'generated_by_model': True,
                        'case': as_v2(worked_examples[pid])})
    return out


def file_preset(case):
    """A starting point from an opened case file (validated by the engine)."""
    return {'id': 'case_file', 'label': f'Case file: {case.get("name", "unnamed")}',
            'description': 'Opened from a case file.', 'kind': 'file',
            'generated_by_model': False, 'case': as_v2(case)}


LITERATURE_LABEL = 'typical values from the literature, to confirm'


def product_defaults(product_id, exit_thickness_m=None, entry_thickness_m=None):
    """Starter values for a catalogue product (``band_survey`` starter case on the default mill
    of its gauge class; alloy and temper from ``band_products.proposed_material`` where the
    product has a grade table). Returns display-unit answers labelled as literature values."""
    case, row = bsurvey.product_starter_case(product_id, exit_thickness_m, entry_thickness_m,
                                             override_source='band app')
    ids = ('product', 'entry_gauge', 'exit_gauge', 'strip_width', 'exit_speed', 'flow_stress',
           'entry_tension', 'exit_tension', 'alloy', 'temper', 'alloy_stated', 'yield_stress',
           'doubled')
    origin = strip_edge_m(case)
    values = {i: answer_from_si(QUESTION_BY_ID[i], _get(case, QUESTION_BY_ID[i].key), origin)
              for i in ids}
    return {'product_id': product_id, 'mill_kind': row['mill'], 'label': LITERATURE_LABEL,
            'values': values,
            'suggested': ['alloy', 'temper'] if case['material'].get('alloy_temper_stated')
            is False else [],
            'notes': [n for n in case['notes'] if not n.startswith('Replace the pass')]}


# ============================================================================= answers <-> case
def _norm_answers(answers):
    if answers is None:
        answers = {}
    if not isinstance(answers, dict):
        raise ValueError('answers must be a JSON object')
    values = answers.get('values') or {}
    origins = answers.get('origins') or {}
    if not isinstance(values, dict) or not isinstance(origins, dict):
        raise ValueError('answers.values and answers.origins must be JSON objects')
    unknown = sorted(set(values) - set(QUESTION_BY_ID))
    if unknown:
        raise ValueError(f'unknown question ids: {", ".join(unknown)}')
    for k, v in origins.items():
        if k not in QUESTION_BY_ID or v not in ORIGINS:
            raise ValueError(f'origin of {k!r} must be one of {ORIGINS}')
    own = answers.get('own_mill', False)
    if not isinstance(own, bool):
        raise ValueError('own_mill must be true or false')
    name = answers.get('name')
    if name is not None and (not isinstance(name, str) or len(name) > 200):
        raise ValueError('name must be text of at most 200 characters')
    return values, origins, own, (name or '').strip()


def _preset_of(preset):
    if isinstance(preset, dict) and 'case' in preset and 'id' in preset:
        return preset
    if isinstance(preset, dict):
        return file_preset(preset)
    raise ValueError('preset must be a starting point from presets() or a case dict')


def _set(case, key, value, created, missing_section):
    parts = key.split('.')
    cur = case
    for i, part in enumerate(parts[:-1]):
        path = '.'.join(parts[:i + 1])
        if cur.get(part) is None:
            if path in SECTIONS:
                cur[part] = copy.deepcopy(SECTIONS[path][2])
                created.add(path)
            else:
                missing_section.add(path)
                return
        cur = cur[part]
    cur[parts[-1]] = value


def _decide(q, values, origins, base, base_origin, new_origin):
    """(use_answer, si_value, origin) for one question."""
    given = values.get(q.id)
    base_si = _get(base, q.key)
    base_disp = answer_from_si(q, base_si, base_origin)
    origin = origins.get(q.id)
    if q.unknown == 'preset':
        if given is None or origin == 'preset':
            return False, base_si, 'preset'
        if given == base_disp and base_origin == new_origin:
            return True, base_si, origin or 'preset'
        return True, answer_to_si(q, given, new_origin), origin or 'estimated'
    if given is None:
        return True, (None if q.unknown == 'null' else []), None
    if given == base_disp and base_origin == new_origin:
        return True, copy.deepcopy(base_si), None
    return True, answer_to_si(q, given, new_origin), None


def _origin_note(origins_by_key):
    parts = []
    for o in ORIGINS[:2]:
        ks = sorted(k for k, v in origins_by_key.items() if v == o)
        parts.append(f'{o}: {", ".join(ks) if ks else "none"}')
    return (f'{ORIGIN_NOTE} ({"; ".join(parts)}; every other mill, pass and material value: '
            'preset).')


def _parse_origin_note(notes):
    out = {}
    for n in notes or []:
        if n.startswith(ORIGIN_NOTE):
            body = n[len(ORIGIN_NOTE):].strip(' ().')
            for part in body.split('; '):
                o, _, ks = part.partition(': ')
                if o in ORIGINS[:2] and ks != 'none':
                    for k in ks.split(', '):
                        out[k.strip()] = o
    return out


def case_from_answers(answers, preset):
    """Build a validated ``physicroll.band_case.v2`` dict from form answers and a starting point
    (an entry of ``presets()``, ``file_preset(case)`` or a case dict).

    ``answers``: {'values': {question id: display value or None}, 'origins': {question id:
    'measured' | 'estimated' | 'preset'}, 'own_mill': bool ("these are my mill's real
    values"), 'name': text}. Raises ``ValueError`` naming the question in plain words."""
    values, origins, own, name = _norm_answers(answers)
    pre = _preset_of(preset)
    base = pre['case']
    case = copy.deepcopy(base)
    base_origin = strip_edge_m(base)
    created, missing = set(), set()
    origin_by_key, person_obs, example_obs, missing_q = {}, [], [], []
    # positions last: their conversion uses the strip edge of the new case
    order = sorted(QUESTIONS, key=lambda q: (q.unit == 'pos_mm' or any(
        f.unit == 'pos_mm' for f in q.fields)))
    for q in order:
        new_origin = strip_edge_m(case) if (q.unit == 'pos_mm' or any(
            f.unit == 'pos_mm' for f in q.fields)) else base_origin
        use, si, origin = _decide(q, values, origins, base, base_origin, new_origin)
        if q.origin_tracked:
            if _has_path(base, q.key) and _get(base, q.key) is not None or use:
                origin_by_key[q.key] = origin
        if not use:
            continue
        if not _has_path(case, q.key) and si in (None, []):
            continue
        before = len(missing)
        _set(case, q.key, si, created, missing)
        if len(missing) > before:
            missing_q.append(q.id)
        if q.also_keys and values.get(q.id) is not None and origin != 'preset' \
                and si != _get(base, q.key):
            for k in q.also_keys:
                if _has_path(case, k):
                    _set(case, k, si, created, missing)
        if q.step == 'see' and not _empty(values.get(q.id)):
            same = values.get(q.id) == answer_from_si(q, _get(base, q.key), base_origin)
            (example_obs if same and pre.get('generated_by_model') else person_obs).append(q.id)
    if missing:
        names = sorted({SECTION_NAMES.get(m.split('.')[0], m) for m in missing})
        raise AnswerError('Your starting point has no ' + ' or '.join(names) + ', so some '
                          'answers cannot be used. Start from the typical foil mill or sheet '
                          'mill to enter them.', missing_q[0] if missing_q else None)
    for path in sorted(created):
        label, required, _ = SECTIONS[path]
        sec = _get(case, path)
        lack = [r for r in required if sec.get(r) is None]
        if lack:
            qs = [QUESTION_BY_KEY[f'{path}.{r}'].wording for r in lack
                  if f'{path}.{r}' in QUESTION_BY_KEY]
            raise AnswerError(f'To use {label}, also answer: ' + '; '.join(qs) + '.',
                              QUESTION_BY_KEY.get(f'{path}.{lack[0]}', QUESTIONS[0]).id)
    if case.get('hardening') is not None:
        law = case['hardening'].get('law')
        if law not in bproc.HARDENING_LAW_KEYS:
            raise AnswerError('Choose the work-hardening law (power or Voce) or leave all '
                              'hardening answers unknown.', 'hardening_law')
        other = [k for lw, ks in bproc.HARDENING_LAW_KEYS.items() if lw != law for k in ks]
        for k in other:
            case['hardening'].pop(k, None)
        for k in ('provenance',) + bproc.HARDENING_LAW_KEYS[law]:
            case['hardening'].setdefault(k, None)
    # the person's identity of the case
    case['name'] = name or base.get('name') or 'band app case'
    case['synthetic'] = not own
    counts = {o: sum(1 for v in origin_by_key.values() if v == o) for o in ORIGINS}
    who = [f'{k} ({o})' for k, o in sorted(origin_by_key.items()) if o != 'preset']
    prov = [f'Built with the band app from the starting point "{pre["label"]}".',
            ('The person marked the mill values as their own mill\'s real values.' if own else
             'Not marked as the person\'s own mill values: the case is synthetic.'),
            f'Mill, pass and material values entered by the person: {counts["measured"]} '
            f'measured, {counts["estimated"]} estimated'
            + (f' ({", ".join(who[:12])}{", ..." if len(who) > 12 else ""})' if who else '')
            + f'; {counts["preset"]} left at the starting point\'s values.',
            f'Observations answered by the person: {len(person_obs)}.']
    if example_obs:
        prov.append(f'Observations kept from the worked example ({len(example_obs)}) were '
                    'generated by the model, not seen on a plant.')
    base_prov = base.get('provenance', '')
    if len(base_prov) > 400:
        cut = base_prov.rfind('. ', 0, 400)
        base_prov = base_prov[:cut + 1] if cut > 100 else base_prov[:400].rstrip() + '...'
    prov.append(f'Starting point provenance: {base_prov}')
    case['provenance'] = ' '.join(prov)
    notes = [n for n in base.get('notes', []) if not n.startswith(NOTE_PREFIX)]
    notes.append(_origin_note(origin_by_key))
    notes.append(NOTE_PREFIX + f'starting point {pre["id"]}; observations answered by the person: '
                 + (', '.join(person_obs) if person_obs else 'none') + '.')
    case['notes'] = notes
    case = json.loads(json.dumps(case, allow_nan=False))
    bd.validate_case(case)
    canonical_nozzles(case)                      # one set of nozzle marks, as the engine reads
    bd.validate_case(case)
    return case


def value_origins(case):
    """{dotted key: 'measured' | 'estimated' | 'preset'} for every mill, pass and material value
    of a case, from the band app's origin note (keys without a note: 'preset')."""
    noted = _parse_origin_note(case.get('notes'))
    out = {}
    for q in QUESTIONS:
        if q.origin_tracked and _get(case, q.key) is not None:
            out[q.key] = noted.get(q.key, 'preset')
    return out


def answers_from_case(case):
    """Form answers that reproduce a case (``case_from_answers(answers_from_case(c), c)``)."""
    case = as_v2(case) if case.get('case_schema') != bd.CASE_SCHEMA_V2 else case
    origin = strip_edge_m(case)
    noted = _parse_origin_note(case.get('notes'))
    values, origins = {}, {}
    for q in QUESTIONS:
        if not _has_path(case, q.key) and q.unknown == 'preset':
            continue
        v = answer_from_si(q, _get(case, q.key), origin)
        if q.unknown == 'empty' and v == []:
            v = None
        values[q.id] = v
        if q.origin_tracked and v is not None:
            origins[q.id] = noted.get(q.key, 'preset')
    _fold_nozzle_answers(case, values, origin)
    return {'name': case.get('name'), 'own_mill': not case.get('synthetic', True),
            'values': values, 'origins': origins}


def _fold_nozzle_answers(case, values, origin):
    """The answers keep one set of nozzle marks: blocked nozzle numbers of the case are folded
    into the levels (the engine's effective levels); the coverage check's numbers are left out
    when they are what the drawing gives, and kept (for ``reconcile_answers`` to show) when an
    opened case disagrees."""
    w = case.get('width_model')
    if w is None:
        return
    try:
        eff = (effective_nozzle_levels(case) if w.get('nozzle_levels') is not None
               or w.get('blocked_nozzle_indices') else None)
    except (ValueError, TypeError, KeyError, IndexError):
        return                                     # an invalid case: validation reports it
    values['nozzle_levels'] = answer_from_si(QUESTION_BY_ID['nozzle_levels'], eff, origin)
    values['blocked_nozzles'] = None
    c = case.get('coolant')
    if c is not None and same_spray_header(case) and \
            sorted(set(c.get('blocked_nozzle_indices') or [])) == coverage_blocked_from_levels(eff):
        values['coverage_blocked_nozzles'] = None
    elif c is not None and same_spray_header(case):
        values['coverage_blocked_nozzles'] = [i + 1 for i in sorted(
            set(c.get('blocked_nozzle_indices') or []))]


class AnswerError(ValueError):
    """A plain-language error about one answer (``question`` = its id, or None)."""

    def __init__(self, text, question=None):
        super().__init__(text)
        self.question = question


_KEY_RE = re.compile(r'([a-z_]+(?:\[\d+\])?(?:(?:\.|: )[a-z_0-9]+(?:\[\d+\])?)+)')


def question_for_error(message):
    """The question id an engine ``ValueError`` concerns (or None), from the dotted key in it."""
    if isinstance(message, AnswerError):
        return message.question
    text = str(message)
    for m in _KEY_RE.finditer(text):
        key = re.sub(r'\[\d+\]', '', m.group(1)).replace(': ', '.')
        while key:
            if key in QUESTION_BY_KEY:
                return QUESTION_BY_KEY[key].id
            key = key.rpartition('.')[0]
    for q in QUESTIONS:
        if f'"{q.wording}' in text:
            return q.id
    for word, qid in (('exit_thickness', 'exit_gauge'), ('entry_thickness', 'entry_gauge'),
                      ('nozzle index', 'nozzle_levels'), ('nozzle_levels', 'nozzle_levels')):
        if word in text:
            return qid
    return None


def engine_message_words(text):
    """An engine validation message with its case keys replaced by the form's wording."""
    def key(m):
        k = re.sub(r'\[\d+\]', '', m.group(1)).replace(': ', '.')
        while k:
            if k in QUESTION_BY_KEY:
                return f'"{QUESTION_BY_KEY[k].wording.rstrip("?")}"'
            k = k.rpartition('.')[0]
        return m.group(1)
    return words(_KEY_RE.sub(key, str(text)))


def plain_error(message):
    """A validation message in plain words: what happened and what to do, and the question
    it concerns where that can be found."""
    qid = question_for_error(message)
    q = QUESTION_BY_ID.get(qid)
    text = str(message)
    if isinstance(message, AnswerError):
        return {'question': qid, 'step': q.step if q else None, 'text': text}
    if q is not None:
        return {'question': qid, 'step': q.step,
                'text': f'The answer to "{q.wording}" is not accepted: '
                        f'{engine_message_words(text)}. Check the value and its unit, or set it '
                        'back to "Don\'t know".'}
    return {'question': None, 'step': None,
            'text': f'The inputs are not accepted: {engine_message_words(text)}. Check the '
                    'values you changed last.'}


# ============================================================================= dependent answers
NOZZLE_DEPENDENT = ('nozzle_levels', 'blocked_nozzles', 'valve_events', 'coverage_blocked_nozzles')


def _coverage_nozzle_count(case):
    """Nozzles of the simple coverage header (``band_signatures.spray_coverage`` layout)."""
    return len(coverage_layout(case)) if case.get('coolant') is not None else None


def _numbers_of(value):
    return [x for x in value if isinstance(x, (int, float)) and not isinstance(x, bool)] \
        if isinstance(value, list) else []


def _nozzle_numbers(value, count):
    """Indices of a list of nozzle numbers (1 = first), or None when it is not a clean list of
    whole numbers 1..count (validation then reports it)."""
    nums = _numbers_of(value)
    if not isinstance(value, list) or len(nums) != len(value) or \
            any(x != int(x) or not 1 <= x <= count for x in nums):
        return None
    return sorted({int(x) - 1 for x in nums})


def _numbers_words(indices):
    return ', '.join(str(i + 1) for i in indices)


def _fold_marks(vals, n, same, notices):
    """Blocked-nozzle numbers (and, for the same header, the coverage check's numbers) become
    marks in the one stored answer ``nozzle_levels``; every change comes with a notice."""
    if n is None:
        return
    levels = vals.get('nozzle_levels')
    cur = list(levels) if isinstance(levels, list) and len(levels) == n else None
    blocked = _nozzle_numbers(vals.get('blocked_nozzles'), n)
    if blocked:
        new = cur or [1.0] * n
        for i in blocked:
            new[i] = 0.0
        vals['nozzle_levels'], vals['blocked_nozzles'], cur = new, None, new
        notices.append({'question': 'nozzle_levels', 'kind': 'moved',
                        'text': f'Blocked nozzle number(s) {_numbers_words(blocked)} are now '
                                'marked blocked on the drawing: the drawing and its nozzle list '
                                'are the one place the nozzle state is kept.'})
    elif vals.get('blocked_nozzles') == []:
        vals['blocked_nozzles'] = None
    if not same:
        return
    cov = vals.get('coverage_blocked_nozzles')
    idx = _nozzle_numbers(cov, n) if isinstance(cov, list) else None
    if idx is None:
        return
    reduced = coverage_blocked_from_levels(cur)
    extra = [i for i in idx if i not in reduced]
    missing = [i for i in reduced if i not in idx]
    vals['coverage_blocked_nozzles'] = None
    if extra:
        new = cur or [1.0] * n
        for i in extra:
            new[i] = 0.0
        vals['nozzle_levels'] = new
        notices.append({'question': 'nozzle_levels', 'kind': 'reset',
                        'text': f'Nozzle(s) {_numbers_words(extra)} were marked blocked only for '
                                'the simple coverage check. It is the same spray header, so they '
                                'are now marked blocked on the drawing, and both checks use the '
                                'drawing.'})
    elif missing:
        notices.append({'question': 'coverage_blocked_nozzles', 'kind': 'moved',
                        'text': 'The simple coverage check now also counts nozzle(s) '
                                f'{_numbers_words(missing)} as not spraying, as they are marked '
                                'weak or blocked on the drawing (same spray header).'})


NOZZLE_EDITS = ('cycle', 'set_level', 'set_blocked', 'all_healthy', 'clear')


def apply_nozzle_edit(answers, preset, edit):
    """New answers after one nozzle edit from the page (the rule lives here, not in the page).

    ``edit``: {'op': 'cycle', 'index': i} (healthy -> weak -> blocked -> healthy), {'op':
    'set_level', 'index': i, 'level': x} (0..1), {'op': 'set_blocked', 'numbers': [...]}
    (exactly these nozzles blocked; a nozzle no longer listed is healthy again), {'op':
    'all_healthy'} or {'op': 'clear'} ("Don't know"). The edit starts from the nozzle state the
    engine would simulate for ``answers`` and stores the result as the one answer
    ``nozzle_levels`` (blocked numbers and, for the same header, the coverage numbers are views
    of it). "Don't know" stays "Don't know" until a nozzle is marked."""
    if not isinstance(edit, dict) or edit.get('op') not in NOZZLE_EDITS:
        raise AnswerError('Unknown nozzle change.', 'nozzle_levels')
    case = case_from_answers(answers, preset)
    n = len(nozzle_layout(case))
    if not n:
        raise AnswerError('This starting point has no spray header model, so nozzles cannot be '
                          'marked here.', 'nozzle_levels')
    cur = case['width_model']['nozzle_levels']
    cur = list(cur) if cur is not None else None
    op = edit['op']
    if op == 'clear':
        new = None
    elif op == 'all_healthy':
        new = [1.0] * n
    elif op in ('cycle', 'set_level'):
        i = edit.get('index')
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < n:
            raise AnswerError(f'There is no nozzle {i if not isinstance(i, int) else i + 1} on '
                              f'this header (it has {n}).', 'nozzle_levels')
        new = cur or [1.0] * n
        if op == 'cycle':
            new[i] = WEAK_NOZZLE_LEVEL if new[i] >= 1 else 0.0 if new[i] > 0 else 1.0
        else:
            x = edit.get('level')
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1:
                raise AnswerError('A nozzle flow level is a number from 0 (blocked) to 1 (full '
                                  'flow).', 'nozzle_levels')
            new[i] = float(x)
    else:
        nums = edit.get('numbers')
        nums = [] if nums is None else nums
        idx = _nozzle_numbers(nums, n)
        if idx is None:
            raise AnswerError(f'Blocked nozzles are whole nozzle numbers from 1 to {n}.',
                              'blocked_nozzles')
        if not idx and cur is None:
            new = None
        else:
            new = cur or [1.0] * n
            for i in range(n):
                if i in idx:
                    new[i] = 0.0
                elif new[i] <= 0:
                    new[i] = 1.0
    out = copy.deepcopy(answers)
    vals = out.setdefault('values', {})
    vals['nozzle_levels'] = new
    vals['blocked_nozzles'] = None
    if case.get('coolant') is not None and same_spray_header(case):
        vals['coverage_blocked_nozzles'] = None
    return out


def reconcile_answers(answers, preset):
    """Answers that depend on other answers, checked BEFORE the case is validated.

    Returns (answers, notices). Nozzle marks that no longer fit the spray header (nozzle levels,
    blocked nozzles, valve events, coverage-check blocked nozzles: their nozzle count depends on
    the barrel length and the nozzle pitch) are reset to "Don't know" — never re-mapped — with a
    notice of kind 'reset'. Values that are still accepted by the engine but now lie outside the
    strip or the roll (band positions, band width, incoming ridges, strip centre) are left as
    entered with a notice of kind 'check'. Nothing is changed silently: the caller shows every
    notice, and a run is not started while a 'reset' notice is pending."""
    _norm_answers(answers)                         # the same checks as case_from_answers
    answers = answers or {}
    notices = []
    probe = copy.deepcopy(answers)
    probe.setdefault('values', {})
    for qid in NOZZLE_DEPENDENT + ('band_positions', 'incoming_ridges'):
        probe['values'][qid] = None                # geometry first, then what depends on it
    try:
        case = case_from_answers(probe, preset)
    except (ValueError, TypeError, KeyError):
        return answers, []                         # validation reports the real problem
    out = copy.deepcopy(answers)
    vals = out.setdefault('values', {})
    try:
        n_header = len(nozzle_layout(case)) if case.get('width_model') else None
        n_cover = _coverage_nozzle_count(case)
    except ValueError:
        return answers, []
    levels = vals.get('nozzle_levels')
    if n_header is not None and isinstance(levels, list) and len(levels) != n_header:
        vals['nozzle_levels'] = None
        notices.append({'question': 'nozzle_levels', 'kind': 'reset',
                        'text': f'The spray header now has {n_header} nozzles instead of '
                                f'{len(levels)}, so the nozzle marks were reset. Mark them again '
                                'if you know them.'})
    for qid, count, what in (('blocked_nozzles', n_header, 'spray header'),
                             ('coverage_blocked_nozzles', n_cover, 'simple coverage header')):
        nums = _numbers_of(vals.get(qid))
        if count is not None and nums and max(nums) > count:
            vals[qid] = None
            notices.append({'question': qid, 'kind': 'reset',
                            'text': f'The {what} now has {count} nozzles, so the blocked nozzle '
                                    f'numbers (up to {int(max(nums))}) were reset. Enter them '
                                    'again if you know them.'})
    same = case.get('coolant') is not None and same_spray_header(case)
    _fold_marks(vals, n_header, same, notices)
    events = vals.get('valve_events')
    if n_header is not None and isinstance(events, list):
        used = [x for e in events if isinstance(e, dict)
                for x in _numbers_of(e.get('nozzle_indices'))]
        if used and max(used) > n_header:
            vals['valve_events'] = None
            notices.append({'question': 'valve_events', 'kind': 'reset',
                            'text': f'The spray header now has {n_header} nozzles, so the valve '
                                    f'events (which name nozzle {int(max(used))}) were reset. '
                                    'Enter them again if you know them.'})
    width_mm = case['pass']['width_m'] * 1000
    pos = _numbers_of(vals.get('band_positions'))
    outside = [x for x in pos if x < 0 or x > width_mm]
    if outside:
        notices.append({'question': 'band_positions', 'kind': 'check',
                        'text': f'{len(outside)} band position(s) lie outside the '
                                f'{width_mm:.0f} mm wide strip. Check the positions or the strip '
                                'width.'})
    bw_mm = vals.get('band_width')
    if isinstance(bw_mm, (int, float)) and not isinstance(bw_mm, bool) and bw_mm > width_mm:
        notices.append({'question': 'band_width', 'kind': 'check',
                        'text': f'The band width ({bw_mm:g} mm) is larger than the strip width '
                                f'({width_mm:.0f} mm). Check one of them.'})
    ridges = vals.get('incoming_ridges')
    if isinstance(ridges, list):
        bad = [r for r in ridges if isinstance(r, dict) and isinstance(r.get('position_m'),
                                                                        (int, float))
               and not 0 <= r['position_m'] <= width_mm]
        if bad:
            notices.append({'question': 'incoming_ridges', 'kind': 'check',
                            'text': f'{len(bad)} ridge position(s) lie outside the strip. Check '
                                    'them or the strip width.'})
    w = case.get('width_model')
    if w is not None:
        edge = strip_edge_m(case)
        barrel = w['roll']['barrel_length_m']
        if edge < -1e-9 or edge + case['pass']['width_m'] > barrel + 1e-9:
            notices.append({'question': 'strip_centre' if w.get('strip_centre_m') is not None
                            else 'strip_width', 'kind': 'check',
                            'text': f'The strip ({width_mm:.0f} mm) does not fit on the roll '
                                    f'barrel ({barrel * 1000:.0f} mm) where it is placed. Check '
                                    'the strip width, the barrel length or the strip centre.'})
    return out, notices


# ============================================================================= drawing model
def _nozzle_state(level):
    return 'blocked' if level <= 0 else 'healthy' if level >= 1 else 'weak'


def _route_model(case):
    """Which route passes ARE the pass where the bands show (``band_width.is_case_pass``, the
    engine's own test), as entered."""
    rows = []
    for r in case.get('schedule') or []:
        try:
            same = bool(bw.is_case_pass(case, r))
        except (TypeError, KeyError):
            same = None
        rows.append({'label': r.get('label'), 'is_pass': same})
    hard, trib = case.get('hardening') or {}, case.get('tribology') or {}
    return {'rows': rows, 'computed_replaces': bool(hard.get('use_computed_flow_stress'))
            or bool(trib.get('use_computed_friction'))}


SIDE_QUESTIONS = ('orientation', 'continuity', 'exit_gauge', 'exit_speed', 'product')


def _side_model(case, edge, starting_point):
    counts = {o: 0 for o in ORIGINS[:2]}
    for o in value_origins(case).values():
        if o in counts:
            counts[o] += 1
    vals = {q: answer_from_si(QUESTION_BY_ID[q], _get(case, QUESTION_BY_ID[q].key), edge)
            if _has_path(case, QUESTION_BY_ID[q].key) else None for q in SIDE_QUESTIONS}
    return dict(vals, band_count=len(case['observation'].get('band_positions_across_width_m')
                                     or []),
                starting_point=starting_point, own_mill=not case.get('synthetic', True),
                measured=counts['measured'], estimated=counts['estimated'])


def drawing_model(case, starting_point=None):
    """Everything the page draws or states about a case, computed from the BUILT case the way
    the engine reads it: the spray header (positions, footprint, EFFECTIVE level per nozzle from
    ``effective_nozzle_levels``, valve events), the coverage check's header, the strip edges on
    the barrel (``band_width.spray_layout`` / ``strip_edge_m``), the bands in barrel and strip
    coordinates, which route passes are the pass, and the side panel. The page draws only from
    this and redraws whenever it differs from what is on screen."""
    w, co = case.get('width_model'), case.get('coolant')
    width = case['pass']['width_m']
    out = {'header': None, 'coverage': None, 'valve_events': []}
    if w is not None:
        lay = bw.spray_layout(case)                # the engine's own reading of the header
        wn = bw.validate_width_model(w, case['pass'])
        edge, barrel = lay['strip_start_m'], lay['barrel_length_m']
        by = {}
        for k, e in enumerate(wn['events']):
            for j in e['nozzle_indices']:
                by.setdefault(j, []).append(k)
        levels = [float(x) for x in lay['nozzle_levels']]
        out['header'] = {
            'pitch_m': lay['nozzle_pitch_m'],
            'footprint_width_m': lay['effective_footprint_width_m'],
            'levels_known': w.get('nozzle_levels') is not None
            or bool(w.get('blocked_nozzle_indices')),
            'nozzles': [{'index': i, 'number': i + 1, 'position_m': x, 'level': lv,
                         'state': _nozzle_state(lv), 'valve_events': by.get(i, [])}
                        for i, (x, lv) in enumerate(zip(lay['nozzle_positions_m'], levels))],
            'weak': sum(1 for lv in levels if 0 < lv < 1),
            'blocked': sum(1 for lv in levels if lv <= 0)}
        out['valve_events'] = [{'start_s': e['start_s'], 'duration_s': e['duration_s'],
                                'level': e['level'], 'label': e.get('label'),
                                'numbers': [j + 1 for j in e['nozzle_indices']]}
                               for e in wn['events']]
    else:
        edge = strip_edge_m(case)
        barrel = co['barrel_length_m'] if co is not None else None
    if co is not None:
        out['coverage'] = {'count': len(coverage_layout(case)),
                           'barrel_length_m': co['barrel_length_m'],
                           'pitch_m': co['nozzle_pitch_m'],
                           'blocked_numbers': [i + 1 for i in
                                               sorted(set(co['blocked_nozzle_indices']))],
                           'same_header': w is not None and same_spray_header(case)}
    obs = case['observation']
    bands = list(obs.get('band_positions_across_width_m') or [])
    out['strip'] = {'edge_m': edge, 'width_m': width, 'end_m': edge + width,
                    'barrel_length_m': barrel}
    out['bands'] = {'positions_m': bands,
                    'from_edge_mm': [round((x - edge) * 1000, 6) for x in bands],
                    'band_width_m': obs.get('band_width_m')}
    out['route'] = _route_model(case)
    out['side'] = _side_model(case, edge, starting_point)
    return out


# ============================================================================= run profiles
QUICK_NUMERICS = {'axial_cell_m': 0.02, 'radial_cells': 6, 'time_step_s': 5.0}  # tests' COARSE
QUICK_CELLS = 128
PROFILES = {
    'quick': {'label': 'Quick', 'description': 'A faster run on a coarser grid, without the '
              'heat-share sensitivity table.',
              'left_out': ['the heat-share and spray-coefficient sensitivity table (how the '
                           'stripe heights change with the share of heat going into the rolls)',
                           'the fine roll-temperature grid: 20 mm cells along the barrel, 6 '
                           'radial cells and a 5 s time step instead of 5 mm, 16 and 1 s (only '
                           'when the case does not set its own grid)',
                           'the fine roll-gap grid: 128 cells instead of 256 (foil roll-gap '
                           'models keep at least 200)']},
    'detailed': {'label': 'Detailed', 'description': 'The case as entered, with the engine\'s '
                 'own settings (slower: up to a few minutes).', 'left_out': []},
}


def apply_profile(case, profile):
    """(case for the engine, list of what the profile changed) for 'quick' or 'detailed'."""
    if profile not in PROFILES:
        raise ValueError(f'profile must be one of {tuple(PROFILES)}')
    out = copy.deepcopy(case)
    changed = []
    if profile == 'quick':
        if out['model_options'].get('thermal_sensitivity', bthermal.DEFAULT_MODE) != 'off':
            out['model_options']['thermal_sensitivity'] = 'off'
            changed.append(PROFILES['quick']['left_out'][0])
        if out.get('width_model') is not None and out['width_model'].get('numerics') is None:
            out['width_model']['numerics'] = dict(QUICK_NUMERICS)
            changed.append(PROFILES['quick']['left_out'][1])
        if out['model_options']['cells'] > QUICK_CELLS:
            out['model_options']['cells'] = QUICK_CELLS
            changed.append(PROFILES['quick']['left_out'][2])
    return out, changed


# ============================================================================= plain tables
STANDING_WORDS = {'CONSISTENT_LEADING': 'fits best', 'CONSISTENT': 'fits',
                  'WEAKENED': 'weakened', 'NOT_ASSESSABLE': 'cannot tell',
                  'CONTRADICTED': 'does not fit'}
WEIGHT_WORDS = {'strong': 'counts strongly', 'moderate': 'counts', 'weak': 'counts a little'}
BASIS_WORDS = {'observation': 'what you saw', 'model': 'the model', 'input': 'the mill and pass '
               'data', 'model not assessable': 'the model (could not be computed)',
               'model not credible': 'the model (not credible here)'}
FAMILY_WORDS = {'lengthwise': 'stripes along the strip (lengthwise bands)',
                'transverse': 'marks across the strip (transverse marks)'}

# id -> (plain name, one-sentence description, pictogram key). Written from
# docs/band-diagnosis.md 3.7, 6.2, 6.3 and each hypothesis's mechanism text; no added physics.
CAUSES = {
    'third_octave_self_excited_chatter': (
        'Gauge chatter (self-excited roll vibration)',
        'Above a critical speed the roll stack starts to vibrate on its own at a fixed '
        'frequency, opening and closing the roll gap, which prints marks across the strip and '
        'makes the thickness vary.', 'chatter'),
    'fifth_octave_roll_stack_resonance': (
        'Roll-stack resonance (higher-pitched vibration)',
        'Both work rolls vibrate together between the backup rolls at a higher frequency '
        '(600-1200 Hz class), kept going by marks printed on a backup roll; the thickness '
        'hardly changes.', 'stack_resonance'),
    'work_roll_borne_marks': (
        'Mark on a work roll',
        'A flat, damage or grinder pattern on a work roll prints once (or a few times) per roll '
        'turn, so the marks repeat at the work-roll circumference.', 'work_roll_mark'),
    'backup_roll_borne_marks': (
        'Mark on a backup roll',
        'A mark or pattern on a backup roll passes to the work roll and then to the strip, so '
        'the marks repeat at the backup-roll circumference.', 'backup_roll_mark'),
    'order_locked_drive_or_bearing_excitation': (
        'Bearing, gear or spindle vibration',
        'A gear mesh, bearing defect or spindle shakes the rolls at a fixed multiple of the '
        'roll rotation, so the mark spacing stays the same when the speed changes.',
        'bearing_gear'),
    'torsional_or_low_frequency_drive_vibration': (
        'Drive-train twisting (low-frequency vibration)',
        'A twisting vibration of the drive train, or stick-slip, at about 5-30 Hz changes roll '
        'speed and tension and prints marks far apart along the strip.', 'drive_twist'),
    'coil_or_mandrel_locked_marks': (
        'Mark from the coil or mandrel',
        'A step, wrap or mandrel feature repeats once per coil turn, so the mark spacing equals '
        'the coil circumference and drifts as the coil grows or shrinks.', 'coil_mark'),
    'yield_point_bending_marks': (
        'Yield-point bending marks (Lüders lines, coil break)',
        'Annealed aluminium-magnesium strip with a yield plateau yields unevenly when bent over '
        'a roll or coil of an unlucky size, leaving lines or kinks.', 'yield_bend'),
    'herringbone_lubricant_film_breakdown': (
        'Herringbone (oil film breaking down)',
        'At heavy reduction the oil film fails again and again, about once per contact length, '
        'giving V-shaped marks.', 'herringbone'),
    'skidding_loss_of_forward_slip': (
        'Rolls skidding on the strip',
        'With a thick oil film, low friction or high speed the rolls slide on the strip, giving '
        'irregular skid marks and matte patches.', 'skid'),
    'nozzle_thermal_stripe': (
        'Blocked or weak coolant nozzle',
        'A blocked, partly blocked or mis-aimed nozzle leaves a less-cooled stripe; the work '
        'roll grows there and over-rolls the strip into a loose band, which may only show once '
        'the tension is released.', 'nozzle'),
    'cooling_zone_switching_transient': (
        'Cooling-zone switching (short-lived bands)',
        'When flatness-control valves switch a cooling zone off and on, the roll grows a stripe '
        'for tens of seconds that fades over about a minute: bands that come and go.',
        'zone_valve'),
    'roll_surface_band': (
        'Band on the work-roll surface',
        'A wear band, pick-up streak, wiper debris or a step at the edges of earlier narrower '
        'strip prints a band at a fixed place until the rolls are changed.', 'roll_band'),
    'grinding_feed_marks': (
        'Roll-grinding feed lines',
        'Fine spiral lines left by the roll grinder; their spacing is the grinder\'s travel per '
        'roll turn.', 'grinder'),
    'incoming_ridge_coil_buildup': (
        'Ridge in the incoming strip, built up in the coil',
        'A local high spot in the incoming strip stacks up wrap on wrap in the coil and '
        'stretches that band, leaving a tight-then-loose band that is worse toward the outer '
        'wraps.', 'coil_ridge'),
    'tension_troughs_or_creases': (
        'Tension troughs or creases',
        'Thin strip under tension buckles sideways into troughs in a free span between rolls; a '
        'roll can iron a trough into a crease.', 'troughs'),
    'profile_flatness_mismatch': (
        'Profile and flatness mismatch (edge wave, centre buckle)',
        'When the thickness profile changes too much between entry and exit, the strip gets '
        'smooth edge waves or a centre buckle rather than narrow stripes.', 'profile'),
    'heat_streak_or_film_variation': (
        'Heat streak or oil-film band',
        'Local differences in oil film or friction across the width give milky heat streaks '
        'or, in foil, a flatness band without a roll bump; such a band follows speed changes.',
        'oil_film'),
    'oil_carryover_drips_or_stain': (
        'Oil carry-over, drips or stain',
        'Coolant carried past the wipers, or drips, leave stains that often show after '
        'annealing.', 'drips'),
    'foil_tension_lines': (
        'Foil tension lines (published description, no model)',
        'Fine lengthwise lines 5-20 mm apart in very thin foil, more visible at low tension and '
        'gone above some tension; the tool only compares what you saw with a published '
        'description.', 'tension_lines'),
}

# engine evidence criterion -> (plain label, question ids that would answer it)
CRITERIA = {
    'Lueders susceptibility': ('whether the alloy and temper can show a yield point',
                               ['alloy', 'temper', 'luders_strain', 'magnesium', 'grain_size']),
    'appearance': ('what a band looks like', ['appearance']),
    'appeared after a narrower coil': ('whether the bands started after a narrower coil',
                                       ['after_narrower_coil']),
    'backup-roll change': ('what a backup-roll change did', ['gone_after_bur_change']),
    'band positions vs event nozzle positions': (
        'band positions against the nozzles of known valve events', ['band_positions',
                                                                     'valve_events']),
    'band positions vs model stripes / blocked or low-level nozzles': (
        'band positions against the model\'s stripes and the weak or blocked nozzles',
        ['band_positions', 'nozzle_levels']),
    'band positions vs supplied incoming ridges': (
        'band positions against known ridges in the incoming strip', ['incoming_ridges']),
    'band positions: edges or centre vs spread across the width': (
        'whether the bands sit at the edges or centre or spread across the width',
        ['band_positions']),
    'band spacing 5-20 mm, regular [BF-S21, excerpt]': (
        'band spacing against the published 5-20 mm', ['band_spacing', 'band_positions']),
    'band width': ('the width of one band', ['band_width']),
    'best gear / bearing / spindle source match': (
        'mark spacing against the gears, bearings and spindles', ['pitch_observations',
                                                                  'gear_meshes', 'bearings']),
    'changes after roll wiper cleaning': ('what cleaning the roll wipers did', ['wiper_cleaning']),
    'changes with coolant zone switching': ('whether the bands follow cooling-zone switching',
                                            ['zone_switching']),
    'changes with exit air blow-off': ('whether the exit air blow-off changes the bands',
                                       ['air_blowoff']),
    'changes with ironing-roll pressure': ('whether the ironing-roll pressure changes the bands',
                                           ['ironing_roll']),
    'changes with tension': ('whether changing the tension changes the bands',
                             ['changes_with_tension']),
    'continuity': ('whether the bands are always there or come and go', ['continuity']),
    'crown change vs Shohet-Townsend dead band': (
        'the change of strip crown against the allowed flatness window',
        ['gap_crown', 'entry_crown']),
    'deflector / coil in yield-point bending window': (
        'deflector roll and coil sizes against the yield-point bending range',
        ['deflector_diameters', 'entry_coil_diameter', 'exit_coil_diameter']),
    'disappears after backup-roll change': ('what a backup-roll change did',
                                            ['gone_after_bur_change']),
    'exit gauge (creasing possible below 50 um)': ('the exit gauge (creasing below 50 µm)',
                                                   ['exit_gauge']),
    'exit gauge (tension lines appear below 15 um [BF-S21, excerpt])': (
        'the exit gauge (tension lines below 15 µm)', ['exit_gauge']),
    'faces': ('whether the marks are on one face or both', ['faces']),
    'film ratio at the operating point (0.3-3: friction sensitive to local differences)': (
        'the oil film against the roughness at the operating point', ['oil_viscosity',
                                                                      'roll_roughness']),
    'film regime': ('the oil film regime', ['oil_viscosity', 'roll_roughness']),
    'first seen': ('where the marks first appear', ['first_seen']),
    'follows previous strip edges / two-tone position': (
        'whether band edges line up with earlier narrower strip', ['follows_previous_edges',
                                                                   'previous_widths']),
    'forward slip': ('how much faster the strip leaves than the roll surface (forward slip)',
                     ['friction']),
    'gauge variation': ('whether the exit gauge shows a thickness change', ['gauge_variation']),
    'intermittent band with partial affected coil length': (
        'short-lived bands over part of the coil', ['continuity']),
    'intermittent duration vs model visible time': (
        'how long a short-lived band lasts, against the model', ['intermittent_duration']),
    'loose / buckle appearance vs MANIFEST event peak band': (
        'a loose band against the model\'s short-lived band', ['appearance']),
    'loose / buckle appearance vs MANIFEST steady model band': (
        'a loose band against the model\'s steady band', ['appearance']),
    'model band at an observed position above the reporting threshold': (
        'whether the model has a band where you saw one', ['band_positions']),
    'model coil build-up of a supplied ridge': ('the model\'s build-up of a known ridge in the '
                                                'coil', ['incoming_ridges', 'coil_outer']),
    'model trough status (either span)': ('whether the model expects troughs in a span',
                                          ['lateral_stress']),
    'observed frequency u/p': ('the mark frequency (speed divided by spacing)',
                               ['pitch_observations', 'vibration_hz']),
    'onset speed': ('the speed where the marks start', ['onset_speed']),
    'order-locked source near the antisymmetric mode at u_op': (
        'a gear or bearing frequency near a roll-stack frequency', ['gear_meshes', 'bearings']),
    'orientation': ('which way the marks run', ['orientation']),
    'pass reduction': ('how much the pass reduces the gauge', ['entry_gauge', 'exit_gauge']),
    'pitch 0.1-3 m': ('mark spacing between 0.1 and 3 m', ['pitch_observations']),
    'pitch 10-40 mm': ('mark spacing between 10 and 40 mm', ['pitch_observations']),
    'pitch = pi*D_b*(1+f)/n': ('mark spacing against the backup-roll circumference',
                               ['pitch_observations', 'bur_diameter']),
    'pitch = pi*D_exit_coil or pi*D_entry_coil*h0/h1': (
        'mark spacing against the coil circumference', ['pitch_observations',
                                                        'exit_coil_diameter']),
    'pitch = pi*D_w*(1+f)/n': ('mark spacing against the work-roll circumference',
                               ['pitch_observations', 'wr_diameter']),
    'pitch vs contact length': ('mark spacing against the contact length in the roll gap',
                                ['pitch_observations']),
    'pitch-speed law': ('whether the mark spacing grows with speed', ['pitch_observations']),
    'positions change / band disappears after work-roll change': (
        'what a work-roll change did to the bands', ['positions_move_after_wr_change']),
    'positions change after work-roll change': ('what a work-roll change did to the bands',
                                                ['positions_move_after_wr_change']),
    'positions repeat across coils': ('whether the bands sit at the same places on the next '
                                      'coils', ['positions_repeat']),
    'regular fine spacing (CV < 0.15, spacing < 30 mm)': ('a regular fine spacing below 30 mm',
                                                          ['band_spacing', 'band_positions']),
    'roll-change test': ('what a roll change did', ['gone_after_wr_change',
                                                    'gone_after_bur_change']),
    'spacing vs cooling-zone (or nozzle) pitch': ('band spacing against the cooling zones',
                                                  ['band_positions', 'cooling_zone_pitch']),
    'spacing vs grinding feed pitch (1-3 x, within 10 %)': (
        'band spacing against the grinder feed', ['band_spacing', 'grinding_traverse']),
    'spacing vs nozzle pitch': ('band spacing against the nozzle pitch', ['band_positions']),
    'spacing vs trough wavelength': ('band spacing against the model\'s trough spacing',
                                     ['band_spacing', 'band_positions']),
    'speed margin': ('the operating speed against the model\'s critical speed', ['exit_speed']),
    'tracks speed changes': ('whether the bands follow speed changes', ['tracks_speed']),
    'tribology regime / exit strip temperature at the operating point': (
        'the oil regime and strip exit temperature at the operating point', []),
    'visible only after tension release': ('whether the bands show only after tension release',
                                           ['only_after_release']),
    'visible only after tension release vs event peak band': (
        'when the bands show, against the model\'s short-lived band', ['only_after_release']),
    'visible only after tension release vs steady model band': (
        'when the bands show, against the model\'s steady band', ['only_after_release']),
    'work-roll change': ('what a work-roll change did', ['gone_after_wr_change']),
    'worse at higher speed': ('whether the bands are worse at higher speed',
                              ['worse_at_higher_speed']),
    'worse at lower tension': ('whether the bands fade at higher tension',
                               ['worse_at_lower_tension']),
    'worse at thinner gauge': ('whether it is worse at thinner gauge', ['worse_at_thinner_gauge']),
    'worse toward outer wraps': ('whether the band is worse toward the outer wraps',
                                 ['worse_outer_wraps']),
}

# recommended next measurement (substring) -> question ids it would answer
NEXT_CHECK_MAP = (
    ('three consecutive coils', ['band_positions', 'positions_repeat']),
    ('band positions move after a work-roll change', ['positions_move_after_wr_change']),
    ('coolant valve states', ['zone_switching']),
    ('Spray footprint check', ['nozzle_levels']),
    ('outside-profile scan', ['worse_outer_wraps']),
    ('span tension', ['changes_with_tension']),
    ('Anneal a sample', ['appearance']),
    ('Step the exit tension', ['worse_at_lower_tension']),
    ('Raise the exit tension in steps', ['worse_at_lower_tension']),
    ('ironing-roll pressure', ['ironing_roll', 'air_blowoff']),
    ('Clean the roll wipers', ['wiper_cleaning']),
    ('mill speed changes', ['tracks_speed']),
    ('appear, move or fade with a speed change', ['tracks_speed']),
    ('wider coil followed a narrower one', ['after_narrower_coil']),
    ('online shapemeter flatness', ['only_after_release']),
    ('two clearly different steady speeds', ['pitch_observations']),
    ('two steady speeds', ['pitch_observations', 'gauge_variation']),
    ('exit thickness gauge / X-ray', ['gauge_variation']),
    ('both strip faces', ['faces']),
    ('roll-change test', ['gone_after_wr_change', 'gone_after_bur_change']),
    ('mark orientation', ['orientation']),
    ('band spacing and compare with the grinder', ['band_spacing']),
    ('start and end of the coil', ['pitch_observations']),
    ('mark morphology', ['orientation']),
    ('Entry and exit profile measurements', ['gap_crown', 'entry_crown']),
    ('Log the oil supply temperature', ['oil_inlet_temperature']),
    ('Log the coil temperature', ['strip_entry_temperature']),
)

# flag -> (plain sentence, what to do). A flag without an entry is shown by its raw name.
FLAGS = {
    'SYNTHETIC_INPUTS': (
        'The inputs are synthetic or typical values, not your mill\'s measured values.',
        'Replace the mill values with your own and mark them as measured or estimated.'),
    'USER_SUPPLIED_INPUTS_NOT_VERIFIED': (
        'The values were entered by a person and have not been checked by the tool.',
        'Have a mill engineer look over the mill values before acting on the result.'),
    'EXPERIMENTAL_MATTRESS_FOIL_MODEL': (
        'At this foil gauge the roll gap comes from an experimental model with no benchmark; '
        'its numbers are order of magnitude only.',
        'Treat the model parts of the result as rough; lean on the observations.'),
    'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL': (
        'The roll-gap numbers come from the experimental foil model.',
        'Read roll force and forward slip as order of magnitude only.'),
    'DERIVED_BY_EXPERIMENTAL_MATTRESS_MODEL': (
        'A roll-gap result was computed by the experimental foil model.',
        'Read it as order of magnitude only.'),
    'MATTRESS_REGIME_FOIL': (
        'The pass is in the foil range where the experimental roll-gap model is used.',
        'No action; it explains why the model parts are rough.'),
    'BITE_MODEL_AUTO': (
        'The tool chose the roll-gap model by gauge (sheet model, foil model where it fails).',
        'No action.'),
    'BITE_MODEL_MATTRESS': (
        'The experimental foil roll-gap model was chosen for every pass.',
        'Read the roll-gap numbers as order of magnitude only.'),
    'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE': (
        'The roll force the model finds for this pass lies outside the range reported for '
        'battery-foil passes, so its roll-gap results are not credible and are left out of the '
        'scoring.', 'Rely on the observations; check the pass inputs (gauges, friction).'),
    'CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED': (
        'At this gauge the work rolls may touch beside the strip (closed-gap rolling), which '
        'the tool does not model; it assumes an open gap.',
        'Treat speed and gauge-control advice with caution at this gauge.'),
    'DOUBLED_FINAL_PASS_NOT_MODELLED': (
        'The thinnest pass is rolled doubled (two sheets), but the tool models one sheet.',
        'Read the thinnest pass as an approximation.'),
    'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN': (
        'The exit gauge is below 20 µm, outside the range where the foil roll-gap model was '
        'probed; its numbers are unvalidated.', 'Read the roll-gap numbers as rough.'),
    'REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN': (
        'The pass reduces the gauge by more than half, outside the reviewed range of the '
        'roll-gap model.', 'Read the roll-gap numbers as rough.'),
    'EXIT_GAUGE_BELOW_BITE_MODEL_FLOOR': (
        'The exit gauge is below 8 µm, where no roll-gap model runs.',
        'Supply roll-gap values from a plant foil model, or rely on the observations.'),
    'THIN_GAUGE_BELOW_REVIEWED_SLAB_DOMAIN': (
        'The pass is thinner than the range the sheet roll-gap model was reviewed for.',
        'Read the roll-gap numbers as rough.'),
    'CIRCULAR_FLATTENING_ASSUMED_NOT_VALIDATED': (
        'The sheet roll-gap model assumes the rolls flatten into a circle, which is not '
        'validated.', 'No action; it is a standing limit of the model.'),
    'HITCHCOCK_RATIO_BEYOND_REVIEWED_ENVELOPE': (
        'The rolls flatten more than the reviewed range of the sheet roll-gap model.',
        'Read the roll-gap numbers as rough.'),
    'CONTACT_END_ZONES_ADDED_TO_SPEC_EQUATIONS': (
        'The foil roll-gap model adds contact end zones to its published equations.',
        'No action.'),
    'FOUNDATION_MODULUS_FROM_MEMORY_FORMULA': (
        'A stiffness inside the foil roll-gap model comes from an unchecked formula.',
        'Read the roll-gap numbers as rough.'),
    'FORWARD_SLIP_LARGE_CONSTANT_FRICTION_NO_SLIP_ZONE_MODEL': (
        'The foil roll-gap model gives a large forward slip, as a model with one constant '
        'friction value does; mill trials found less.',
        'Do not use the forward slip; the roll-mark spacing uses zero slip when it is very '
        'large.'),
    'FORWARD_SLIP_UNKNOWN_ZERO_USED_IN_KINEMATICS': (
        'No roll-gap result: the forward slip is unknown and zero is used for roll-mark '
        'spacings.', 'Mark spacings tied to roll turns are slightly approximate.'),
    'FORWARD_SLIP_OUTSIDE_KINEMATICS_DOMAIN_ZERO_USED_IN_KINEMATICS': (
        'The forward slip is too large for the roll-mark spacings, so zero is used there.',
        'Mark spacings tied to roll turns are slightly approximate.'),
    'MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN': (
        'Alloy and temper are a suggestion from the literature, not the plant\'s statement.',
        'Confirm the alloy and temper with the plant and mark them as stated.'),
    'LUDERS_STRAIN_NOT_SUPPLIED_ZERO_USED_IN_WINDOWS': (
        'No yield-point strain was given, so zero is used in the bending check.',
        'Give it if the strip is annealed and shows a yield plateau.'),
    'FLOW_STRESS_FROM_HARDENING_LAW': (
        'The flow stresses come from the hardening law, not from the values typed in.',
        'No action; check the hardening law if the results look odd.'),
    'MODEL_STEADY_THERMAL_STRIPES_PRESENT': (
        'The roll temperature model finds steady hot stripes on the work roll.',
        'Compare their positions with your bands in the strip picture.'),
    'OPERATING_POINT_LINEARLY_UNSTABLE': (
        'In the model the stand vibrates on its own at the operating speed (chatter).',
        'Check whether the mark spacing grows with speed.'),
    'CHATTER_NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT': (
        'The model\'s chatter frequency is above the limit where its strip-span model holds, '
        'so the chatter result is not reliable here.', 'Do not lean on the chatter result.'),
    'OPERATING_SPEED_OUTSIDE_SCANNED_RANGE': (
        'The operating speed lies outside the speed range the chatter scan covers.',
        'Read the chatter speed margin with caution.'),
    'AGC_CHATTER_INTERACTION_DEPENDS_ON_LOOP_ROLL_OFF': (
        'The effect of gauge control on chatter depends on a simple control-loop model.',
        'No action; it is a standing limit.'),
    'SHAPEMETER_OPERATOR_APPLIED': (
        'The page shows what each zone of the shapemeter you described would show for the '
        'modelled bands: zone averages of a model, not a forecast of the screen.',
        'Compare with your shapemeter record; there is no flatness control in the model.'),
    'MODEL_BAND_BELOW_SHAPEMETER_THRESHOLD': (
        'A modelled band is narrower or weaker than a zone can show: the shapemeter would '
        'probably not show it.',
        'Look for it offline (sag test of a sample), not only on the shapemeter.'),
    'SHAPEMETER_DOES_NOT_COVER_STRIP': (
        'The shapemeter zones you described do not cover the whole strip width.',
        'Check the zone count, width and centre.'),
    'SHAPEMETER_NEIGHBOUR_SPREADING_APPLIED': (
        'Part of each zone reading is shared with its neighbours, as you set it.',
        'Set the spreading to zero unless your vendor states it.'),
    'STRIP_TEMPERATURE_TERM_SUPPLIED_PROFILE': (
        'The strip temperature scan you gave is used to show flatness as measured hot and '
        'after cooling; the scan is your input, not worked out by the tool.',
        'Check where and when the scan was taken.'),
    'STRIP_EXPANSION_COEFFICIENT_FROM_MEMORY_DEFAULT': (
        'The heat expansion of aluminium is a textbook value, not checked against your alloy.',
        'Give the value from your alloy data if you have it.'),
    'STRIP_TEMPERATURE_SCAN_DOES_NOT_COVER_STRIP': (
        'The temperature scan does not reach the whole strip width; the end values are carried '
        'to the edges.', 'Scan the full strip width.'),
    'STRIP_TEMPERATURE_TERM_WITHOUT_MECHANICAL_PROFILE': (
        'There is no modelled flatness for this pass, so only the temperature part is shown.',
        'Read it as the temperature effect alone.'),
    'STRIP_TEMPERATURE_CHANGES_A_BAND_STATE': (
        'The strip temperature changes whether a band shows in the mill or after release.',
        'Compare the hot reading with a cold sample of the same coil.'),
    'SHAPEMETER_TEMPERATURE_COMPENSATED': (
        'Your shapemeter corrects for strip temperature, so it would show the flatness without '
        'the temperature part.', 'No action.'),
    'GAUGE_TRANSFER_APPLIED': (
        'The page shows about how much of each mark the thickness gauge you described keeps '
        '(spot size and response time only).',
        'Real gauges have other filters; use it as a guide.'),
    'GAUGE_KEEPS_LESS_THAN_HALF_OF_OBSERVED_MARK': (
        'The thickness gauge keeps less than half of at least one mark spacing you saw.',
        'A small gauge reading does not mean a small mark; measure the strip itself.'),
    'GAUGE_NOT_DETECTED_BUT_MARK_NOT_RESOLVABLE': (
        'You saw no gauge variation, but the gauge could not show these marks anyway, so that '
        'answer tells little; the scores were not changed.',
        'Measure the strip thickness along a mark with a hand micrometer or offline gauge.'),
    'LENGTHWISE_MODEL_BAND_NOT_UNDER_GAUGE': (
        'None of the modelled lengthwise bands passes under the thickness gauge.',
        'Do not expect the gauge to show these bands.'),
    'MEASUREMENT_SECTION_FAILED': (
        'The shapemeter part of the page could not be worked out.',
        'Check the measurement inputs; the rest of the page is unaffected.'),
    'SPRAY_COEFFICIENT_BASIS_NOT_ESTABLISHED': (
        'The spray cooling value is an average around the roll; the published values may be '
        'for the spray zone only, so the two are not compared like for like.',
        'Read the spray comparison as rough until the basis of the published value is known.'),
    'STRIP_EXIT_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT': (
        'A modelled strip exit temperature reaches the flash point of the oil you gave.',
        'Check the real strip and coil temperature; the modelled value is an indicator.'),
    'OIL_TEMPERATURE_AT_OR_ABOVE_OIL_FLASH_POINT': (
        'An oil temperature you gave reaches the flash point of the oil.',
        'Check the oil temperature and the flash point you entered.'),
    'OIL_SUPPLY_TEMPERATURE_ABOVE_SITE_CAP': (
        'An oil temperature you gave reaches the site limit you gave.',
        'Check the oil supply temperature against your site limit.'),
    'HEAT_PARTITION_INPUTS_INCONSISTENT': (
        'Two inputs for how the roll-gap heat is shared disagree.',
        'Give only the strip share, or make both agree.'),
    'MODELLED_EXIT_TEMPERATURE_ABOVE_BATTERY_COIL_LIMIT': (
        'The modelled strip exit temperature is above a published battery-foil coil limit.',
        'Log the real coil temperature after the pass; exit temperature is not coil '
        'temperature.'),
    'DUPLICATE_BAND_POSITIONS_MERGED': (
        'Some band positions were closer than 1 mm and were merged into one band.',
        'Check the positions you entered.'),
    'FORCE_SENSITIVITY_DERIVED_NOT_FROM_SUPPLIED_BITE': (
        'Some sensitivities come from the tool\'s roll-gap model, not from the supplied values.',
        'Read the gauge-control numbers as rough.'),
    'CASE_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE': (
        'A pass lies outside the published range for the chosen product.',
        'Check the pass values or the product; this never changes the shortlist.'),
    'FINAL_PASS_OUTSIDE_PUBLISHED_PRODUCT_RANGE': (
        'The final pass lies outside the published range for the chosen product.',
        'Check the pass values or the product; this never changes the shortlist.'),
    'CASE_STRENGTH_BELOW_STANDARD_MINIMUM_FOR_GAUGE': (
        'The strength entered is below the published minimum for this gauge.',
        'Check the alloy, temper and strength.'),
    'RIGID_BOUND_NOT_DEFINED_BUMP_REACHES_GAUGE': (
        'One comparison level of the flatness model is not defined because the roll bump '
        'reaches the gauge.', 'No action; the main result is unaffected.'),
    'COMPLIANCE_ONLY_LEVEL_NOT_DEFINED_CHANGE_REACHES_GAUGE': (
        'One comparison level of the flatness model is not defined for this soft strip.',
        'No action; the main result is unaffected.'),
    'HYPOTHESIS_EVALUATION_FAILED': (
        'One or more causes could not be evaluated and are shown as "cannot tell".',
        'Check the inputs those causes need (see "What could not be assessed").'),
    'NEXT_MEASUREMENTS_FAILED': ('The list of next checks could not be built.',
                                 'Use the "how to check" line of each cause instead.'),
    'STRIP_MAP_FAILED': ('The along-the-strip picture could not be built.',
                         'Use the shortlist and the engineering report.'),
    'SIGNATURES_SECTION_FAILED': ('The mark-spacing checks could not be computed.',
                                  'Check the roll and drive data.'),
    'SCREENS_SECTION_FAILED': ('The simple screens (spray coverage, oil film) could not be '
                               'computed.', 'Check the spray header and oil data.'),
    'THERMAL_CHECK_FAILED': ('The process-temperature check could not be computed.',
                             'Check the oil and temperature data.'),
    'MATERIAL_SELECTION_FAILED': ('The alloy and temper suggestion could not be built.',
                                  'Enter the alloy and temper yourself.'),
    'THERMAL_SENSITIVITY_PER_PASS_FAILED': (
        'The per-pass heat-share table could not be computed.', 'No action needed.'),
    'THERMAL_SENSITIVITY_FAILED': ('The heat-share sensitivity table could not be computed.',
                                   'No action needed.'),
    'BITE_DERIVATION_FAILED_CHATTER_NOT_ASSESSABLE': (
        'No roll-gap result, so the chatter checks could not be made.',
        'Check the pass inputs, or rely on the observations.'),
    'WIDTH_SECTION_PARTIAL_FAILURE': (
        'Part of the across-the-width model could not be computed.',
        'See "What could not be assessed".'),
    'WIDTH_SHAPE_CHAIN_NOT_ASSESSABLE_NO_BITE': (
        'Without a roll-gap result the strip-shape part of the width model is not assessed.',
        'Supply plant foil-model inputs, or rely on the observations.'),
    'WIDTH_THERMAL_NOT_ASSESSABLE_NO_BITE_HEAT': (
        'Without the roll-gap heat the roll temperature model could not run.',
        'Give the heat made in the roll gap per metre of width.'),
    'SUPPLIED_BITE_SENSITIVITIES_NOT_VERIFIED': (
        'The roll-gap values were supplied from outside and are not checked by the tool.',
        'Make sure they come from a trusted plant model.'),
    'BITE_RESPONSE_SUPPLIED': ('The roll-gap values were supplied from outside.', 'No action.'),
    'SHAPE_INPUTS_SUPPLIED': ('Strip-shape inputs were supplied from a plant model.',
                              'No action.'),
    'STEADY_STATE_NOT_CONVERGED': ('The roll temperature model did not fully settle.',
                                   'Run the detailed profile.'),
    'PLACEHOLDER_FRICTION_CLOSURE_NOT_FITTED': (
        'The friction-speed law is a placeholder and not fitted.',
        'Use only its trend with speed, not its values.'),
    'FRICTION_FROM_PLACEHOLDER_CLOSURE': (
        'The friction used comes from the placeholder law, not from your value.',
        'Prefer your own friction value.'),
}
FLAG_FALLBACK = 'no plain description yet'

GLOSSARY = {
    'span': 'The free length of strip between the roll gap and the next roll.',
    'chatter': 'A vibration of the roll stack that prints marks across the strip.',
    'onset': 'The point where something starts to happen, for example the stripe height at '
             'which a band starts to buckle.',
    'closed gap': 'At foil gauge the work rolls may touch each other beside the strip; the '
                  'tool does not model this.',
    'I-unit': 'A flatness unit: 1 I-unit is a length difference of 10 µm per metre between '
              'fibres of the strip.',
    'latent band': 'A band that is flat under strip tension and only buckles once the tension '
                   'is released.',
    'barrel coordinate': 'Position along the roll face, 0 at the start of the coolant header.',
    'forward slip': 'How much faster the strip leaves the roll gap than the roll surface turns.',
}


# ============================================================================= summary helpers
FORBIDDEN = ('the cause', 'diagnosis', 'confirmed', 'accuracy', 'probability', 'confidence')
_REWRITE = (('diagnoses', 'screenings'), ('diagnosis', 'screening'),
            ('confirmed', 'checked'), ('probability', 'likelihood'),
            ('confidence', 'certainty'), ('accuracy', 'exactness'), ('the cause', 'a cause'))


def clean(text):
    """Plain wording rules applied to text taken from the engine (words only)."""
    if not isinstance(text, str):
        return text
    out = text
    for a, b in _REWRITE:
        out = re.sub(r'\b' + re.escape(a) + r'\b', b, out, flags=re.IGNORECASE)
    return out


# engine tokens -> plain words (states, laws, statuses that appear inside evidence texts)
STATE_WORDS = {
    'MANIFEST_BUCKLE': 'buckled in the mill', 'LATENT_UNDER_TENSION': 'hidden under mill tension',
    'MANIFEST_AFTER_TENSION_RELEASE': 'visible after tension release',
    'FLAT_AFTER_TENSION_RELEASE': 'flat after tension release',
    'FIXED_FREQUENCY': 'fixed frequency (spacing grows with speed)',
    'SPEED_INDEPENDENT_PITCH': 'spacing that stays the same at any speed',
    'NO_GAPS_MATCH': 'no gaps match', 'SOME_GAPS_MATCH': 'some gaps match',
    'ALL_GAPS_MATCH': 'all gaps match', 'ELASTIC_NO_YIELD': 'bends without yielding',
    'NOT_SUSCEPTIBLE_COLD_WORKED': 'not susceptible (cold worked)',
    'RIDGE_YIELDS_STRIP': 'the ridge stretches the strip beyond yield',
    'TROUGHS_EXPECTED': 'troughs expected',
    'LATERAL_STRESS_UNKNOWN_THRESHOLDS_ONLY': 'sideways stress unknown, thresholds only',
    'NOT_RELIABLE_ABOVE_SPAN_WAVE_LIMIT': 'not reliable above the span wave limit',
    'NOT_ASSESSABLE': 'not assessable', 'BELOW_TROUGH_THRESHOLD': 'below the trough threshold',
    'IN_YIELD_POINT_WINDOW': 'inside the yield-point bending range',
    'in_mill_manifest': 'buckled in the mill',
    'manifest_after_tension_release': 'visible after tension release'}
TOKEN_WORDS = {'u_op': 'the operating speed', 'u_crit': 'the critical speed',
               'D_b': 'backup-roll diameter', 'D_w': 'work-roll diameter',
               'D_exit_coil': 'exit coil diameter', 'D_entry_coil': 'entry coil diameter',
               'f_obs': 'observed frequency', 'entry_span': 'entry span',
               'exit_span': 'exit span', 'entry_coil': 'entry coil', 'exit_coil': 'exit coil',
               'deflector_roll': 'deflector roll', 'bpfi': 'inner-race defect',
               'bpfo': 'outer-race defect', 'bsf': 'rolling-element defect', 'ftf': 'cage'}
def _choice_words(qs):
    out, clash = {}, set()
    for q in qs:
        for v, lab in list(q.choices) + [c for f in q.fields for c in f.choices]:
            if not isinstance(v, str):
                continue
            lab = lab[0].lower() + lab[1:]
            if v in out and out[v] != lab:
                clash.add(v)
            out.setdefault(v, lab)
    return {k: v for k, v in out.items() if k not in clash}


CHOICE_WORDS = _choice_words(QUESTIONS)      # values with one meaning across the form
_LEAF_WORDS = {q.key.rsplit('.', 1)[-1]: q.wording.rstrip('?').lower() for q in QUESTIONS}
_SNAKE = re.compile(r'\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b')
_UNIT_SUFFIX = re.compile(r'_(m|pa|n|m_s|hz|rad|kg|n_m|k|s|w_m|w_m2k|per_k|per_pa)$')


# A complete number: sign, digits, decimal part, exponent in either case. Matched whole, never
# in part: not inside a longer token, not as the tail of another number.
_NUM = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
# "<number> m" or "<number>-<number> m" with a bare metre: not m/s, m/min, m2, m^2, mm, MPa
# (upper case), mN, ... and not followed by a digit or letter.
_M_RE = re.compile(r'(?<![\w.])(' + _NUM + r')(?:\s*-\s*(' + _NUM + r'))?\s?m(?![\w/²³^·*])')
MM_MAX_M = 20.0          # a length of 20 m or more stays in metres (spans, coil lengths)
MM_MIN_MM = 1e-3         # below 0.001 mm the original text is left untouched (no exponent shown)
MM_MAX_SIG = 6           # at most six significant figures (repr-formatted engine numbers)


def _sig_digits(token):
    """Significant digits written in a number token (exponent and sign ignored)."""
    mant = re.split(r'[eE]', token.lstrip('+-'))[0]
    digits = mant.replace('.', '').lstrip('0')
    if not digits:
        return 1
    if '.' not in mant:
        digits = digits.rstrip('0') or digits[:1]
    return max(1, len(digits))


def _fixed(x, sig):
    """x with ``sig`` significant figures in plain fixed notation (no exponent), trailing
    zeros after the decimal point removed."""
    if x == 0:
        return '0'
    d = sig - 1 - math.floor(math.log10(abs(x)))
    if d <= 0:
        return f'{round(x, d):.0f}'
    text = f'{x:.{d}f}'
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _mm_of(token):
    """A metre token as millimetres, or None when it must stay as written."""
    try:
        v = float(token)
    except ValueError:
        return None
    if not math.isfinite(v) or abs(v) >= MM_MAX_M:
        return None
    x = v * 1000.0
    if x != 0 and abs(x) < MM_MIN_MM:
        return None
    return _fixed(x, min(_sig_digits(token), MM_MAX_SIG))


def _to_mm(m):
    """'0.667 m' -> '667 mm', '5e-05 m' -> '0.05 mm', '0.1-3 m' -> '100-3000 mm': lengths in
    millimetres on screen. Left unchanged when a value cannot be read, is 20 m or more, or is
    below 0.001 mm, or when the number continues a token before it ('x-0.5 m')."""
    a, b = m.group(1), m.group(2)
    start = m.start(1)
    text = m.string
    if a[0] not in '+-' and start >= 2 and text[start - 1] in '+-' and text[start - 2].isalnum():
        return m.group(0)
    ma = _mm_of(a)
    mb = _mm_of(b) if b else None
    if ma is None or (b and mb is None):
        return m.group(0)
    return ma + ('-' + mb if b else '') + ' mm'


def _token(tok, choice_words=None):
    if choice_words and tok in choice_words:
        return choice_words[tok]
    if tok in STATE_WORDS:
        return STATE_WORDS[tok]
    if tok in TOKEN_WORDS:
        return TOKEN_WORDS[tok]
    if tok in CHOICE_WORDS:
        return CHOICE_WORDS[tok]
    if tok in _LEAF_WORDS:
        return _LEAF_WORDS[tok]
    if tok.isupper() or tok.upper() == tok:
        return tok.replace('_', ' ').lower()
    return _UNIT_SUFFIX.sub('', tok).replace('_', ' ')


def words(text, question_ids=()):
    """Engine text in plain words: enum values, keys, statuses and formula symbols replaced,
    true / false as yes / no. Numbers are left exactly as the engine wrote them.
    ``question_ids``: questions whose answer words take precedence (e.g. 'both' of the faces
    question)."""
    if not isinstance(text, str):
        return text
    local = dict(CHOICE_WORDS, **_choice_words([QUESTION_BY_ID[q] for q in question_ids
                                                if q in QUESTION_BY_ID]))
    t = text.strip()
    if t in local:
        return local[t]
    t = re.sub(r'bearing:([^:\s]+):([0-9]*x?)_?([a-z]+)',
               lambda m: (f'bearing {m.group(1)} {m.group(2)} '
                          f'{TOKEN_WORDS.get(m.group(3), m.group(3))}'), t)
    t = re.sub(r'deflector_roll:(\d+)', lambda m: f'deflector roll {int(m.group(1)) + 1}', t)
    t = _SNAKE.sub(lambda m: _token(m.group(0), local), t)
    t = re.sub(r'\b(true|True)\b', 'yes', t)
    t = re.sub(r'\b(false|False)\b', 'no', t)
    t = re.sub(r'\b(LATENT|latent)\b', 'hidden under tension', t)
    t = re.sub(r'\b(MANIFEST|manifest)\b', 'visible', t)
    t = re.sub(r'\b([A-Z]{4,})\b', lambda m: m.group(1).lower(), t)
    t = _M_RE.sub(_to_mm, t)
    t = t.replace('on the barrel coordinate', 'along the roll').replace(
        'barrel coordinate', 'position along the roll')
    for v, lab in local.items():
        if '_' not in v and len(v) > 2:
            t = re.sub(rf'^{re.escape(v)}(?=[;,]|$)', lambda m, lab=lab: lab, t)
    return clean(t)


VERDICT_WORDS = {('SUPPORTS', 'strong'): 'Matches', ('SUPPORTS', 'moderate'): 'Matches',
                 ('SUPPORTS', 'weak'): 'Partly matches',
                 ('CONTRADICTS', 'strong'): 'Does not match',
                 ('CONTRADICTS', 'moderate'): 'Does not match',
                 ('CONTRADICTS', 'weak'): 'Does not quite match'}
OTHER_VERDICT_WORDS = {'NEUTRAL': 'Neither for nor against', 'NOT_OBSERVED': 'Not looked at yet'}
SOURCE_WORDS = {'observation': 'You saw', 'model': 'The model computed',
                'input': 'From your mill values',
                'model not assessable': 'The model could not compute this',
                'model not credible': 'The model computed (not credible here)'}
RELEASE_CRITERIA = ('visible only after tension release vs steady model band',
                    'visible only after tension release vs event peak band')
LOOSE_CRITERIA = ('loose / buckle appearance vs MANIFEST steady model band',
                  'loose / buckle appearance vs MANIFEST event peak band')
MODEL_AT_POSITION = 'model band at an observed position above the reporting threshold'
EXPECT_SENTENCES = {
    RELEASE_CRITERIA[0]: 'If the bands show only after the coil is unwound, this cause expects '
                         'the model band to be hidden under tension in the mill and visible after '
                         'release; if they show in the mill, it expects a band that buckles in '
                         'the mill.',
    RELEASE_CRITERIA[1]: 'If the bands show only after the coil is unwound, this cause expects '
                         'the short-lived model band to be hidden under tension in the mill and '
                         'visible after release; if they show in the mill, it expects a band that '
                         'buckles in the mill.',
    LOOSE_CRITERIA[0]: 'This cause expects a loose, wavy band together with a model band that '
                       'buckles in the mill.',
    LOOSE_CRITERIA[1]: 'This cause expects a loose, wavy band together with a short-lived model '
                       'band that buckles in the mill.',
    MODEL_AT_POSITION: 'This cause expects the model to put a band (hidden under tension or '
                       'buckled) where you saw one.'}
RELEASE_SEEN = {'true': 'the bands show only after tension release (on the coil, at the slitter '
                        'or on the table)',
                'false': 'the bands are seen in the mill'}


def _sentence(text):
    text = str(text).strip().rstrip('.')
    return text[:1].upper() + text[1:] + '.' if text else ''


def evidence_sentences(e, qids=()):
    """Plain sentences for one evidence item: a verdict, what the person saw, what the model
    computed (or which mill value was used) and what the cause expects. Built from the engine's
    own fields; numbers are kept, metres are shown as millimetres."""
    basis = e.get('basis', 'observation')
    crit, obs, exp = e['criterion'], str(e['observed']), str(e['expected'])
    seen, model = obs, None
    pos = re.match(r'observed (.+?) on (?:model|events) (.+?)(?: \((.+)\))?$', obs)
    if '; model ' in obs:
        seen, model = obs.split('; model ', 1)
    elif pos:
        seen = 'bands at ' + pos.group(1)
        model = 'positions at ' + pos.group(2) + (f' ({pos.group(3)})' if pos.group(3) else '')
    if crit == MODEL_AT_POSITION or basis != 'observation':
        seen, model = None, obs
    seen_w = model_w = None
    if seen is not None:
        if crit in RELEASE_CRITERIA:
            seen_txt = RELEASE_SEEN.get(seen.strip().lower(), words(seen, qids))
        else:
            seen_txt = words(seen, qids)
        seen_w = 'You saw: ' + _sentence(seen_txt)
    if model is not None:
        label = SOURCE_WORDS.get(basis, 'The model computed') if basis != 'observation' \
            else 'The model computed'
        text = words(model, qids).replace(' / ', ' and ')
        parts = []
        for part in text.split(', '):          # one entry per state, not one per band
            if part not in parts or re.search(r'\d', part):
                parts.append(part)
        text = ', '.join(parts)
        if crit in LOOSE_CRITERIA:
            text = {'visible': 'a band that buckles in the mill',
                    'hidden under tension': 'a band hidden under tension in the mill'}.get(
                        text.strip(), text)
        text = re.sub(r'^(\d[\d.,]* mm): ', r'at \1, ', text)
        model_w = label + ': ' + _sentence(text)
    expects = EXPECT_SENTENCES.get(crit) or 'This cause expects: ' + _sentence(words(exp, qids))
    verdict = VERDICT_WORDS.get((e['verdict'], e['weight'])) or \
        OTHER_VERDICT_WORDS.get(e['verdict'], 'Counted')
    return {'verdict_words': verdict, 'seen_words': seen_w, 'model_words': model_w,
            'expects_words': expects}


def _evidence_item(e):
    label, qids = CRITERIA.get(e['criterion'], (e['criterion'], []))
    out = {'criterion': e['criterion'], 'label': words(label),
           'observed': e['observed'], 'expected': e['expected'],
           'observed_words': words(e['observed'], qids),
           'expected_words': words(e['expected'], qids),
           'verdict': e['verdict'], 'weight': e['weight'],
           'weight_words': WEIGHT_WORDS.get(e['weight'], ''),
           'basis': e.get('basis', 'observation'),
           'basis_words': BASIS_WORDS.get(e.get('basis', 'observation'), e.get('basis')),
           'questions': [q for q in qids if q in QUESTION_BY_ID]}
    out.update(evidence_sentences(e, qids))
    return out


def _cause(h):
    name, desc, picto = CAUSES[h['id']]
    ev = h['evidence']
    nl = []
    seen = set()
    for e in ev:
        if e['verdict'] != 'NOT_OBSERVED':
            continue
        label, qids = CRITERIA.get(e['criterion'], (e['criterion'], []))
        qs = [q for q in qids if q in QUESTION_BY_ID]
        if label in seen:
            continue
        seen.add(label)
        nl.append({'criterion': e['criterion'], 'label': words(label), 'questions': qs,
                   'prompts': [QUESTION_BY_ID[q].wording for q in qs]})
    return {'id': h['id'], 'family': h['family'], 'family_words': FAMILY_WORDS[h['family']],
            'name': name, 'description': desc, 'pictogram': picto, 'rank': h.get('rank'),
            'score': h['score'], 'standing': h['standing'],
            'standing_words': STANDING_WORDS[h['standing']],
            'leading': h['standing'] == 'CONSISTENT_LEADING',
            'fits_because': [_evidence_item(e) for e in ev if e['verdict'] == 'SUPPORTS'],
            'speaks_against': [_evidence_item(e) for e in ev if e['verdict'] == 'CONTRADICTS'],
            'neutral': [_evidence_item(e) for e in ev if e['verdict'] == 'NEUTRAL'],
            'not_looked_at': nl, 'how_to_check': words(h['confirming_test']),
            'levers': [clean(x) for x in h.get('levers', [])]}


def _join_names(names):
    if len(names) == 1:
        return names[0]
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def _observed_family(result):
    fs = result.get('family_summary') or {}
    return fs.get('observed_family')


def _answered(obs, qid):
    q = QUESTION_BY_ID[qid]
    return not _empty(_get({'observation': obs}, q.key))


def _headline(result, causes, missing_first):
    leaders = [c for c in causes if c['leading']]
    tail = 'This is a shortlist from a screening model, not a finding.'
    if len(leaders) == 1:
        text = f'What you entered fits best with: {leaders[0]["name"]}. {tail}'
        kind = 'one_leader'
    elif len(leaders) > 1:
        text = (f'What you entered fits {_join_names([c["name"] for c in leaders])} equally '
                f'well: they tie for the lead. {tail}')
        kind = 'tie'
    else:
        fits = [c for c in causes if c['standing'] == 'CONSISTENT']
        text = 'Nothing stands out yet: no cause collects enough support from what you saw.'
        if fits:
            text += (' Causes that fit so far: '
                     + _join_names([c['name'] for c in fits[:3]]) + '.')
        text += (f' Answer more of the "ask first" questions ({missing_first} still unknown) '
                 'to narrow the shortlist.')
        kind = 'nothing_leads'
    if result.get('bite_error'):
        text += (' The roll-gap model could not compute the pass where the bands show, so the '
                 'parts of the screening that need it are missing (see "What could not be '
                 'assessed").')
    return {'text': text, 'kind': kind, 'leaders': [c['id'] for c in leaders]}


TRUST_LEVELS = ('LOW', 'MODERATE', 'FAIR')
TRUST_RULE = (
    'Rule, not a statistic: start at FAIR and take the lowest of these caps. LOW if the inputs '
    'are synthetic, if any "ask first" mill value is left at the typical value or the mill '
    'values are not marked as your own, if fewer than half of the "ask first" observations '
    'are answered or no orientation is given, if nothing leads, if the roll-gap model could '
    'not compute the pass or its result is not credible, or if a part of the screening '
    'failed. MODERATE if 50-79 % of the '
    '"ask first" observations are answered, if causes tie for the lead or the leader is less '
    'than 3 points ahead of the next cause of the same kind, or if the experimental foil '
    'roll-gap model, an extended roll-gap range, closed-gap rolling or a literature alloy '
    'suggestion is involved. Never higher than FAIR: nothing in the tool has been compared '
    'with plant data.')
_CAP_MODERATE_FLAGS = {
    'EXPERIMENTAL_MATTRESS_FOIL_MODEL': 'The foil roll-gap model is experimental.',
    'EXIT_GAUGE_BELOW_20_UM_EXTENDED_MATTRESS_DOMAIN': 'The exit gauge is below the range the '
                                                      'foil roll-gap model was probed for.',
    'REDUCTION_ABOVE_50_PERCENT_EXTENDED_BITE_DOMAIN': 'The pass reduction is beyond the '
                                                      'reviewed roll-gap range.',
    'CLOSED_GAP_ROLLING_LIKELY_ROLL_KISSING_NOT_MODELLED': 'At this gauge the rolls may touch '
                                                          '(closed gap), which is not '
                                                          'modelled.',
    'MATERIAL_NOT_STATED_LITERATURE_PROPOSAL_SHOWN': 'Alloy and temper are a literature '
                                                    'suggestion, not the plant\'s statement.'}


def _trust(result, causes, origins, own_mill, asked, answered):
    flags = set(result.get('flags') or [])
    caps = []

    def cap(level, reason):
        caps.append((level, reason))
    if 'SYNTHETIC_INPUTS' in flags:
        cap('LOW', 'The inputs are synthetic or typical values, not measured on your mill.')
    mill_first = [q for q in QUESTIONS if q.step == 'mill' and q.ask_first and q.origin_tracked
                  and q.key in origins]
    preset_mill = [q.wording for q in mill_first if origins.get(q.key) == 'preset']
    if preset_mill:
        cap('LOW', f'{len(preset_mill)} of the {len(mill_first)} key mill values are left at '
                   'the typical value: ' + ', '.join(preset_mill) + '.')
    elif not own_mill and 'SYNTHETIC_INPUTS' not in flags:
        cap('LOW', 'The mill values are not marked as your mill\'s real values.')
    if not asked:
        cap('LOW', 'No orientation of the marks is recorded, so the tool cannot tell which kind '
                   'of band to look at.')
    else:
        frac = len(answered) / len(asked)
        if frac < 0.5:
            cap('LOW', f'Only {len(answered)} of the {len(asked)} "ask first" observations are '
                       'answered.')
        elif frac < 0.8:
            cap('MODERATE', f'{len(answered)} of the {len(asked)} "ask first" observations are '
                            'answered.')
    leaders = [c for c in causes if c['leading']]
    if not leaders:
        cap('LOW', 'No cause leads the shortlist.')
    elif len(leaders) > 1:
        cap('MODERATE', f'{len(leaders)} causes tie for the lead.')
    else:
        fam = leaders[0]['family']
        rest = [c['score'] for c in causes if c['family'] == fam and not c['leading']]
        if rest:
            gap = leaders[0]['score'] - max(rest)
            if gap < 3:
                cap('MODERATE', f'The leader is only {gap} point{"s" if gap != 1 else ""} '
                                'ahead of the next cause of the same kind.')
    if result.get('bite_error'):
        cap('LOW', 'The roll-gap model could not compute the pass where the bands show, so the '
                   'model parts that need it are missing.')
    if 'CASE_BITE_FORCE_OUTSIDE_REPORTED_RANGE_MODEL_NOT_CREDIBLE' in flags:
        cap('LOW', 'The roll-gap result of this pass is not credible, so its model evidence is '
                   'left out.')
    failed = sorted(f for f in flags if f.endswith('_FAILED'))
    if failed:
        cap('LOW', 'A part of the screening could not be computed: '
            + ', '.join(FLAGS.get(f, (f,))[0] for f in failed))
    for f, reason in _CAP_MODERATE_FLAGS.items():
        if f in flags:
            cap('MODERATE', reason)
    level = 'FAIR'
    for lv, _ in caps:
        if TRUST_LEVELS.index(lv) < TRUST_LEVELS.index(level):
            level = lv
    return {'level': level, 'levels': list(TRUST_LEVELS),
            'step': TRUST_LEVELS.index(level) + 1,
            'reasons': [{'cap': lv, 'text': r} for lv, r in caps],
            'rule': TRUST_RULE,
            'status': STATUS,
            'status_words': 'Screening result, not compared with plant data.'}


def _flags_plain(result):
    out = []
    for f in result.get('flags') or []:
        if f in FLAGS:
            out.append({'flag': f, 'text': FLAGS[f][0], 'what_to_do': FLAGS[f][1],
                        'described': True})
        else:
            out.append({'flag': f, 'text': f'{f}: {FLAG_FALLBACK}.', 'what_to_do': '',
                        'described': False})
    return out


KIND_WORDS = {'steady_stripes': 'Hot stripe on the roll (model, steady)',
              'blocked_or_low_level_nozzles': 'Weak or blocked nozzle',
              'event_nozzles': 'Nozzle of a valve event',
              'event_stripe_peaks': 'Short-lived stripe (model, valve event)',
              'incoming_ridges': 'Ridge in the incoming strip',
              'two_tone': 'Edge of earlier narrower strip'}


def _good(sec):
    return isinstance(sec, dict) and sec.get('status') not in ('NOT_ASSESSABLE', 'FAILED',
                                                               'NOT_SUPPLIED')


def _strip_view(result):
    case = result['inputs']
    w = result.get('width')
    obs = case['observation']
    out = {'available': False, 'units': 'm (barrel coordinate, 0 at the header start)'}
    if case['observation'].get('orientation') not in (None, 'longitudinal'):
        out['note'] = 'Marks across the strip: see the along-the-strip picture.'
    ts = w.get('thermal_steady') if _good(w) else None
    pos = w.get('positions') if _good(w) else None
    if _good(ts):
        out.update(available=True, source='width model',
                   barrel_length_m=w['barrel_length_m'], strip_start_m=ts['strip_start_m'],
                   strip_end_m=ts['strip_end_m'],
                   nozzles=[{'index': i, 'number': i + 1, 'position_m': x, 'level': lv,
                             'state': ('blocked' if lv <= 0 else 'healthy' if lv >= 1
                                       else 'weak')}
                            for i, (x, lv) in enumerate(zip(ts['nozzle_positions_m'],
                                                            ts['nozzle_levels']))],
                   thermal_profile={'z_m': ts['z_m'],
                                    'local_deviation_m': ts['local_deviation_m'],
                                    'note': 'roll radius growth with the actual header minus '
                                            'a healthy header (hot stripes are bumps)'},
                   stripes=[{'centre_m': s['center_m'], 'start_m': s['start_m'],
                             'end_m': s['end_m'], 'peak_deviation_m': s['peak_deviation_m'],
                             'width_at_half_peak_m': s['width_at_half_peak_m'],
                             'sign': s['sign']} for s in ts.get('stripes') or []])
    elif _good(result.get('screens')) and case.get('coolant') is not None:
        sc = result['screens']
        out.update(available=True, source='spray coverage screen (no width model)',
                   barrel_length_m=case['coolant']['barrel_length_m'],
                   risk_intervals=sc.get('band_risk_stripes'),
                   geometry_basis='inputs: strip centred on the coolant barrel (the engine '
                                  'convention, strip_edge_m)')
        out['strip_start_m'] = strip_edge_m(case)
        out['strip_end_m'] = out['strip_start_m'] + case['pass']['width_m']
    if isinstance(pos, dict):
        out['observed_positions_m'] = pos.get('observed_positions_m', [])
        out['tolerance_m'] = pos.get('tolerance_m')
        out['tolerance_basis'] = pos.get('tolerance_basis')
        out['predicted'] = [{'kind': k, 'label': KIND_WORDS.get(k, k), 'positions_m': v}
                            for k, v in (pos.get('predicted_positions_m') or {}).items()]
        out['matches'] = [{'kind': k, 'label': KIND_WORDS.get(k, k),
                           'status': m.get('status'),
                           'links': [{'observed_m': x['observed_position_m'],
                                      'predicted_m': x['nearest_predicted_position_m'],
                                      'distance_m': x['distance_m'], 'matched': x['matched']}
                                     for x in m.get('matches') or []]}
                          for k, m in (pos.get('position_matches') or {}).items()]
    else:
        out['observed_positions_m'] = list(obs.get('band_positions_across_width_m') or [])
        sc = result.get('screens') or {}
        out['tolerance_m'] = sc.get('band_position_tolerance_m')
        out['tolerance_basis'] = sc.get('band_position_tolerance_basis')
        out['predicted'], out['matches'] = [], []
    out['band_width_m'] = obs.get('band_width_m')
    return out


def _along_view(result, names):
    sm = result.get('strip_map') or {}
    obs = result['inputs']['observation']
    hid = sm.get('hypothesis_id')
    return {'available': bool(obs.get('pitch_observations')) or sm.get('predicted_pitch_m')
            is not None,
            'observed': [{'exit_speed_m_s': p['exit_speed_m_s'], 'pitch_m': p['pitch_m']}
                         for p in obs.get('pitch_observations') or []],
            'observed_pitch_m': sm.get('observed_pitch_m'),
            'observed_at_exit_speed_m_s': sm.get('observed_at_exit_speed_m_s'),
            'predicted_pitch_m': sm.get('predicted_pitch_m'),
            'predicted_basis': sm.get('predicted_pitch_basis'),
            'hypothesis_id': hid, 'hypothesis_name': names.get(hid),
            'strip_length_m': sm.get('strip_length_m'),
            'operating_speed_m_s': result['inputs']['pass']['exit_speed_m_s']}


CREDIBILITY_WORDS = {None: 'model result', 'FORCE_INSIDE_REPORTED_RANGE_UNVALIDATED':
                     'unvalidated (extended roll-gap range)', 'FORCE_OUTSIDE_REPORTED_RANGE':
                     'not credible (roll force outside the reported range)'}
GAUGE_QUANTITIES = (
    ('manifest_onset_stripe_height_m', 'Roll stripe height at which a band buckles in the '
     'mill', 'um', 'lower means a smaller roll stripe already shows a band'),
    ('released_onset_stripe_height_m', 'Roll stripe height at which a band shows after '
     'tension release', 'um', 'lower means a smaller roll stripe already shows a band'),
    ('critical_ridge_height_m', 'Ridge height in the incoming strip that the coil turns into a '
     'band', 'um', 'lower means a smaller ridge already matters'),
    ('trough_critical_lateral_stress_pa', 'Sideways stress at which troughs form in the span',
     'mpa', 'closer to zero means troughs form more easily'),
)


def _gauge_view(result):
    w = result.get('width')
    g = w.get('gauge_trend') if _good(w) else None
    if not isinstance(g, dict) or not g.get('rows'):
        return {'available': False}
    rows = sorted((r for r in g['rows'] if isinstance(r, dict)),
                  key=lambda r: -(r.get('exit_thickness_m') or 0))
    passes = []
    for r in rows:
        cred = r.get('bite_credibility')
        mark = 'no roll-gap result' if 'rejected' in r else CREDIBILITY_WORDS.get(
            cred, cred)
        passes.append({'label': r.get('label'), 'exit_thickness_m': r.get('exit_thickness_m'),
                       'entry_thickness_m': r.get('entry_thickness_m'),
                       'credibility': cred, 'credibility_words': mark,
                       'not_credible': cred == 'FORCE_OUTSIDE_REPORTED_RANGE',
                       'no_bite': 'rejected' in r,
                       'rejected': r.get('rejected'),
                       'values': {k: r.get(k) for k, *_ in GAUGE_QUANTITIES},
                       'released_limited': r.get('released_onset_limited_by_reporting_'
                                                 'threshold')})
    try:
        from . import band_report
        direction = band_report.gauge_direction(g)        # the report's own sentence
    except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError):
        direction = None
    return {'available': True, 'order': 'thickest to thinnest (thinnest on the right)',
            'quantities': [{'key': k, 'label': lab, 'unit': u, 'unit_label': unit_label(u),
                            'reading': rd} for k, lab, u, rd in GAUGE_QUANTITIES],
            'passes': passes, 'direction_text': words(direction),
            'engine_text': clean(g.get('text')), 'bite_free_text': clean(g.get('bite_free_text'))}


def _temperature_view(result):
    tc = result.get('thermal_check')
    if not isinstance(tc, dict) or not tc.get('strip_exit_temperatures'):
        return {'available': False}
    rows = [{'label': r.get('label'), 'value_c': r.get('value'), 'unit': r.get('unit'),
             'published_high_c': r.get('published_high'),
             'published_low_c': r.get('published_low'), 'verdict': r.get('verdict'),
             'is_final_pass': r.get('is_final_pass'), 'basis': clean(r.get('basis'))}
            for r in tc['strip_exit_temperatures'] if r.get('value') is not None]
    return {'available': bool(rows), 'rows': rows, 'coil_limits_c': tc.get('coil_limits_c'),
            'battery_limits_apply': tc.get('battery_coil_limits_apply'),
            'caveat': 'A modelled strip exit temperature is not the coil temperature: the '
                      'published limits are for the coil. Read the bars as indicators.',
            'engine_texts': [clean(t) for t in tc.get('texts') or []]}


SECTION_WORDS = {'chatter': 'Chatter (roll-stack vibration) checks',
                 'levers': 'What-would-change table for chatter',
                 'gauge_control': 'Gauge control', 'drive': 'Drive train',
                 'incoming_variation': 'Incoming coil variation',
                 'time_simulation': 'Vibration time trace', 'process': 'Oil film, friction and '
                 'pass heating', 'width': 'Across-the-width model'}


BITE_FAILURE_PATTERNS = (     # specific phrases of the engine's roll-gap messages, first match
    ('contact radius ratio', 'the rolls would flatten more than the sheet roll-gap model allows '
                             '(thin, hard strip)'),
    ('flattening fixed point', 'the sheet roll-gap model does not converge for this pass'),
    ('floor of the roll-bite', 'the exit gauge is below the 8 µm that the roll-gap models cover'),
    ('below the 8 um floor', 'the exit gauge is below the 8 µm that the roll-gap models cover'),
    ('bite domain requires exit thickness', 'the exit gauge is below what the sheet roll-gap '
                                            'model covers'),
    ('bite domain requires reduction', 'the pass reduction is outside the range the roll-gap '
                                       'model accepts'),
    ('friction coefficient <=', 'the friction is outside the range the roll-gap model accepts'),
    ('h0/R <= 0.05', 'the strip is too thick for the roll or too narrow for the roll-gap model'),
    ('tensions must stay below', 'the strip tensions are not below the flow stress'),
)


def bite_failure_words(text):
    """A roll-gap (bite) failure in plain words: what happened, then the engine's detail."""
    t = str(text)
    why = next((w for key, w in BITE_FAILURE_PATTERNS if key in t), None)
    lead = 'The roll-gap model could not solve this pass' + (f': {why}' if why else '') + '.'
    return lead + ' Details: ' + words(t)


def _not_assessable(result, causes):
    out = []
    bite_error = result.get('bite_error')
    if bite_error:
        out.append({'what': 'Roll-gap model of the pass where the bands show',
                    'why': bite_failure_words(bite_error), 'kind': 'not_assessable'})
    for k, section_name in SECTION_WORDS.items():
        sec = result.get(k)
        if isinstance(sec, dict) and sec.get('status') in ('NOT_ASSESSABLE', 'FAILED'):
            reason = str(sec.get('reason') or sec.get('error') or 'not computed')
            if bite_error and reason == str(bite_error):
                why = 'needs the roll-gap result of this pass, which could not be computed'
            elif k == 'time_simulation':
                why = ('the vibration time trace was not computed: it would need more time '
                       'steps than the tool allows at this stiffness (the engineering report '
                       'has the detail)')
            else:
                why = engine_message_words(reason)
            out.append({'what': section_name, 'why': why, 'kind': sec['status'].lower()})
        elif isinstance(sec, dict) and sec.get('not_supplied'):
            out.append({'what': section_name, 'why': 'not supplied for this case',
                        'kind': 'not_supplied'})
    sweep = result.get('schedule_sweep')
    for row in (sweep.get('rows') or []) if isinstance(sweep, dict) else []:
        if isinstance(row, dict) and row.get('rejected'):
            out.append({'what': f'Pass {row.get("label", "")} of the route',
                        'why': bite_failure_words(row['rejected']), 'kind': 'not_assessable'})
    w = result.get('width')
    if _good(w):
        ts = w.get('thermal_steady')
        if isinstance(ts, dict) and ts.get('status') in ('NOT_ASSESSABLE', 'FAILED'):
            out.append({'what': 'Roll temperature across the width',
                        'why': engine_message_words(ts.get('reason') or ts.get('error')),
                        'kind': ts['status'].lower()})
        sc = w.get('shape_chain') or {}
        if sc.get('status') not in (None, 'EVALUATED'):
            out.append({'what': 'Strip-shape part of the width model',
                        'why': engine_message_words(sc.get('reason')), 'kind': 'not_assessable'})
        for f in w.get('failures') or []:
            out.append({'what': 'Part of the width model', 'why': engine_message_words(f),
                        'kind': 'failed'})
    for c in causes:
        if c['standing'] == 'NOT_ASSESSABLE':
            out.append({'what': c['name'], 'why': 'nothing entered so far speaks for or '
                        'against it', 'kind': 'cause_not_assessable'})
    return out


STANDING_LIMITATIONS = (
    'One stand of a four-high mill is modelled; multi-stand effects are not.',
    'Closed-gap rolling (work rolls touching beside the strip at foil gauge) is not modelled.',
    'Nothing in the tool has been compared with plant data; the weights of the evidence rules '
    'are engineering judgement.',
    'The score is an ordinal tally of fit, not a measure of how likely a cause is.')


def plain_summary(result, case=None, value_origins_=None, own_mill=None):
    """JSON-ready plain summary of an engine result. ``case``: the case as entered (default:
    the result's inputs); ``value_origins_``: {dotted key: origin} (default: from the case's
    band app note). Every number is read from ``result``; nothing is recomputed."""
    if not isinstance(result, dict) or not isinstance(result.get('hypotheses'), list):
        raise ValueError('not a band screening result (no hypotheses): the product survey and '
                         'other results have no plain summary')
    case = case if case is not None else result['inputs']
    origins = value_origins_ if value_origins_ is not None else value_origins(case)
    own = (not case.get('synthetic', True)) if own_mill is None else own_mill
    causes = [_cause(h) for h in result['hypotheses']]
    names = {c['id']: c['name'] for c in causes}
    obs = result['inputs']['observation']
    fam = _observed_family(result)
    h1 = result['inputs']['pass']['exit_thickness_m']
    asked = ask_first_ids(fam, h1) if obs.get('orientation') is not None else []
    answered = [q for q in asked if _answered(obs, q)]
    missing_first = len(asked) - len(answered) if asked else len(ask_first_ids(None, h1))
    fs = result.get('family_summary') or {}
    lead_fam = fs.get('leading_family')
    family = {'observed': fam, 'leading': lead_fam,
              'observed_words': FAMILY_WORDS.get(fam, 'not recorded'),
              'text': (f'You described {FAMILY_WORDS[fam]}.' if fam else
                       'No direction of the marks was recorded.')
              + (f' The best-fitting cause is of the same kind.' if lead_fam and lead_fam == fam
                 else f' The best-fitting cause is of the other kind '
                      f'({FAMILY_WORDS[lead_fam]}).' if lead_fam else ''),
              'engine_text': clean(fs.get('text'))}
    leading_family = fam or lead_fam
    shortlist = [c['id'] for c in causes if leading_family is None
                 or c['family'] == leading_family]
    other = [c['id'] for c in causes if c['id'] not in shortlist]
    checks = []
    for line in result.get('recommended_next_measurements') or []:
        qs = []
        for key, ids in NEXT_CHECK_MAP:
            if key in line:
                qs += [q for q in ids if q not in qs]
        checks.append({'text': words(line), 'questions': qs, 'mapped': bool(qs)})
    out = {
        'schema': SCHEMA, 'status': result['status'],
        'status_words': 'Screening result from a model that has not been compared with plant '
                        'data. It gives a shortlist of causes that fit what you entered, not a '
                        'finding.',
        'case_name': result.get('case_name'), 'synthetic': result.get('synthetic'),
        'headline': _headline(result, causes, missing_first),
        'family': family, 'causes': causes, 'shortlist_ids': shortlist,
        'other_family_ids': other,
        'score_scale': {'min': min(c['score'] for c in causes),
                        'max': max(c['score'] for c in causes),
                        'note': 'Score = points for what fits minus points for what speaks '
                                'against (an ordinal tally of fit, not a measure of how likely '
                                'a cause is).'},
        'next_checks': checks,
        'trust': _trust(result, causes, origins, own, asked, answered),
        'ask_first': {'asked': asked, 'answered': answered, 'missing': missing_first},
        'flags_plain': _flags_plain(result),
        'strip_view': _strip_view(result),
        'along_view': _along_view(result, names),
        'gauge_view': _gauge_view(result),
        'temperature_view': _temperature_view(result),
        'not_assessable': _not_assessable(result, causes),
        'roll_gap_failed': bool(result.get('bite_error')),
        'limitations': list(STANDING_LIMITATIONS),
        'engine_limitations': [clean(x) for x in result.get('limitations') or []],
        'pass': {k: result['inputs']['pass'][k] for k in ('entry_thickness_m',
                                                          'exit_thickness_m', 'width_m',
                                                          'exit_speed_m_s')},
        'product': result['inputs']['material'].get('product'),
    }
    json.dumps(out, allow_nan=False)
    return out


def compare_summaries(old, new):
    """What changed between two summaries, in words (rank and standing per cause)."""
    before = {c['id']: c for c in old['causes']}
    changes = []
    for c in new['causes']:
        b = before.get(c['id'])
        if b is None:
            continue
        if b['standing'] != c['standing'] or b['rank'] != c['rank'] or b['score'] != c['score']:
            parts = []
            if b['standing'] != c['standing']:
                parts.append(f'{b["standing_words"]} -> {c["standing_words"]}')
            if b['rank'] != c['rank']:
                parts.append(f'place {b["rank"]} -> {c["rank"]}')
            if b['score'] != c['score']:
                parts.append(f'score {b["score"]} -> {c["score"]}')
            changes.append({'id': c['id'], 'name': c['name'],
                            'standing_before': b['standing'], 'standing_after': c['standing'],
                            'rank_before': b['rank'], 'rank_after': c['rank'],
                            'score_before': b['score'], 'score_after': c['score'],
                            'text': f'{c["name"]}: ' + '; '.join(parts)})
    trust = None
    if old['trust']['level'] != new['trust']['level']:
        trust = f'Trust level {old["trust"]["level"]} -> {new["trust"]["level"]}'
    return {'changes': changes, 'trust': trust,
            'text': ('; '.join(x['text'] for x in changes[:6]) if changes
                     else 'The shortlist did not change.')}
