"""O0 offline phase/recipe/observation contracts, not a dynamic solver or controller.

Readiness permits only attempting a separate model/domain evaluation. It never
certifies a prediction or advances material/roll state. See docs/operational-replay.md.
"""
from dataclasses import asdict, dataclass
import math

from .operating import PHASES, QUANTITIES, ObservedSignal


CONTRACT_VERSION = 'O0_OPERATING_CONTRACT_V1'
# Named output bundles: qualification of force does not qualify thermal fields.
MECHANICS_OUTPUTS = {
    'legacy_mechanics': ('separating_force_n', 'torque_per_work_roll_nm',
                         'roll_mechanical_power_w', 'assumed_forward_slip_fraction'),
    'spatial_slab': ('separating_force_n', 'torque_per_work_roll_nm',
                     'roll_mechanical_power_w', 'forward_slip_fraction'),
    'circular_contact': ('separating_force_n', 'torque_per_work_roll_nm',
                         'roll_mechanical_power_w', 'forward_slip_fraction'),
}
REQUIRED_ACTUALS = ('entry_thickness_m', 'entry_speed_m_s', 'entry_tension_pa', 'exit_tension_pa',
                    'exit_thickness_m')


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _time(value):
    return _finite(value) and value >= 0


def _tuple_of(items, cls, label):
    if not isinstance(items, tuple) or not all(isinstance(x, cls) for x in items):
        raise ValueError(f'{label} must be a tuple of {cls.__name__}')
    for item in items:
        item.validate()


@dataclass(frozen=True)
class PassScope:
    """Nominal recipe applicability; gauges are not measured values."""
    pass_name: str
    alloy: str
    temper: str
    entry_thickness_m: float
    exit_thickness_m: float

    def validate(self):
        if not all(_text(x) for x in (self.pass_name,self.alloy,self.temper)):
            raise ValueError('pass scope needs pass/alloy/temper identity')
        if not all(_finite(x) and x > 0 for x in (self.entry_thickness_m,self.exit_thickness_m)) or not (
                self.entry_thickness_m > self.exit_thickness_m):
            raise ValueError('nominal pass gauges must be positive and decreasing')


@dataclass(frozen=True)
class PhaseTarget:
    quantity: str
    unit: str
    value: float
    phase: str
    provenance: str

    def validate(self):
        ObservedSignal(self.quantity,self.unit,self.value,self.phase,self.provenance).validate()
        if QUANTITIES[self.quantity][1] not in ('setpoint','boundary') or self.phase == 'unknown':
            raise ValueError('recipe targets must be named-phase inputs, not predicted outputs')


@dataclass(frozen=True)
class OperatingRecipe:
    recipe_id: str
    revision: str
    scope: PassScope
    targets: tuple[PhaseTarget, ...]
    provenance: str

    def validate(self):
        if not all(_text(x) for x in (self.recipe_id,self.revision,self.provenance)):
            raise ValueError('recipe identity, revision and provenance required')
        if not isinstance(self.scope,PassScope):
            raise ValueError('recipe needs explicit PassScope')
        self.scope.validate()
        _tuple_of(self.targets,PhaseTarget,'targets')
        keys = [(t.phase,t.quantity) for t in self.targets]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate recipe phase target')


@dataclass(frozen=True)
class AppliedReference:
    """Recorded command and acknowledgement; neither is a measurement."""
    quantity: str
    unit: str
    value: float
    commanded_at_s: float
    acknowledged_at_s: float | None
    provenance: str

    def validate(self):
        PhaseTarget(self.quantity,self.unit,self.value,'steady',self.provenance).validate()
        if not _time(self.commanded_at_s) or (self.acknowledged_at_s is not None and (
                not _time(self.acknowledged_at_s) or self.acknowledged_at_s < self.commanded_at_s)):
            raise ValueError('command/acknowledgement times must be ordered')


@dataclass(frozen=True)
class MeasuredSignal:
    quantity: str
    unit: str
    value: float | None
    observed_at_s: float | None
    quality: str  # valid, suspect, unavailable; caller assertion, not authentication
    location: str
    material_coordinate_m: float | None
    uncertainty_si: float | None
    provenance: str

    def validate(self):
        units = {key:value[0] for key,value in QUANTITIES.items()}
        units['entry_thickness_m'] = 'm'
        if self.quantity not in units or self.unit != units[self.quantity]:
            raise ValueError('unknown measured quantity or incorrect SI unit')
        if not all(_text(x) for x in (self.location,self.provenance)):
            raise ValueError('measurement location and provenance required')
        if self.quality not in ('valid','suspect','unavailable'):
            raise ValueError('unknown measurement quality')
        if self.quality == 'unavailable':
            if self.value is not None or self.observed_at_s is not None:
                raise ValueError('unavailable measurement cannot contain a value/time')
        else:
            if self.quantity == 'entry_thickness_m':
                if not _finite(self.value) or self.value <= 0:
                    raise ValueError('measured entry gauge must be positive finite metres')
            else:
                ObservedSignal(self.quantity,self.unit,self.value,'steady',self.provenance).validate()
            if not _time(self.observed_at_s):
                raise ValueError('measurement time required')
        if self.material_coordinate_m is not None and not _finite(self.material_coordinate_m):
            raise ValueError('material coordinate must be finite when known')
        if self.uncertainty_si is not None and (not _finite(self.uncertainty_si) or self.uncertainty_si < 0):
            raise ValueError('measurement uncertainty must be nonnegative when known')


@dataclass(frozen=True)
class SteadyWindowEvidence:
    """Caller evidence for a named output bundle, never inferred from speed."""
    model: str
    start_s: float
    end_s: float
    max_measurement_age_s: float
    provenance: str  # output stationarity/error-budget assessment
    alignment_provenance: str  # parcel/location/timebase alignment assessment

    def validate(self):
        if self.model not in MECHANICS_OUTPUTS:
            raise ValueError('steady evidence must name a supported mechanics output bundle')
        if not all(_time(x) for x in (self.start_s,self.end_s,self.max_measurement_age_s)) or self.start_s >= self.end_s:
            raise ValueError('steady evidence needs a positive window and declared age limit')
        if not all(_text(x) for x in (self.provenance,self.alignment_provenance)):
            raise ValueError('stationarity and material alignment evidence required')


@dataclass(frozen=True)
class OperationSample:
    coil_id: str
    scope: PassScope
    recipe_id: str
    recipe_revision: str
    timebase_id: str
    timestamp_s: float
    phase: str
    phase_basis: str  # observed, inferred, unknown; commands are not phases
    phase_provenance: str
    coordinate_reference: str
    boundary_state: str  # established, absent, unknown: bite and both span boundaries
    boundary_provenance: str
    measurements: tuple[MeasuredSignal, ...] = ()
    applied_references: tuple[AppliedReference, ...] = ()
    steady_evidence: tuple[SteadyWindowEvidence, ...] = ()
    remaining_length_m: float | None = None
    remaining_length_uncertainty_m: float | None = None
    remaining_length_provenance: str | None = None
    transition_provenance: str | None = None

    def validate(self):
        if not all(_text(x) for x in (self.coil_id,self.recipe_id,self.recipe_revision,
                   self.timebase_id,self.phase_provenance,self.coordinate_reference,self.boundary_provenance)):
            raise ValueError('sample identity, timebase and evidence provenance required')
        if not isinstance(self.scope,PassScope):
            raise ValueError('sample needs PassScope')
        self.scope.validate()
        if not _time(self.timestamp_s) or self.phase not in PHASES:
            raise ValueError('sample needs finite nonnegative time and known phase tag')
        if self.phase_basis not in ('observed','inferred','unknown') or (
                (self.phase == 'unknown') != (self.phase_basis == 'unknown')):
            raise ValueError('unknown phase and evidence basis must agree')
        if self.boundary_state not in ('established','absent','unknown'):
            raise ValueError('boundary state must be established, absent or unknown')
        for items,cls,label,key in ((self.measurements,MeasuredSignal,'measurements','quantity'),
                (self.applied_references,AppliedReference,'references','quantity'),
                (self.steady_evidence,SteadyWindowEvidence,'steady evidence','model')):
            _tuple_of(items,cls,label)
            if len({getattr(x,key) for x in items}) != len(items):
                raise ValueError(f'duplicate sample {label}')
        times = [x.observed_at_s for x in self.measurements] + [
            t for x in self.applied_references for t in (x.commanded_at_s,x.acknowledged_at_s)]
        if any(t is not None and t > self.timestamp_s for t in times):
            raise ValueError('sample cannot use future measurement or command information')
        if self.remaining_length_m is None:
            if self.remaining_length_uncertainty_m is not None or self.remaining_length_provenance is not None:
                raise ValueError('length metadata needs a remaining-length value')
        elif (not _time(self.remaining_length_m) or not _time(self.remaining_length_uncertainty_m)
              or not _text(self.remaining_length_provenance)):
            raise ValueError('remaining length needs nonnegative value/uncertainty and estimator provenance')
        if self.transition_provenance is not None and not _text(self.transition_provenance):
            raise ValueError('transition provenance must be nonempty when supplied')


def assess_sample_models(sample: OperationSample) -> dict:
    """Preflight only. No solver result, domain acceptance or plant validity implied."""
    sample.validate()
    values = {x.quantity:x for x in sample.measurements}
    evidence = {x.model:x for x in sample.steady_evidence}
    result = {}
    for model,outputs in MECHANICS_OUTPUTS.items():
        reasons = []
        if sample.phase != 'steady':
            reasons.append('NONSTEADY_OR_UNKNOWN_PHASE')
        if sample.boundary_state != 'established':
            reasons.append('BOUNDARY_'+sample.boundary_state.upper())
        window = evidence.get(model)
        if window is None or not (window.start_s <= sample.timestamp_s == window.end_s):
            reasons.append('NO_CURRENT_OUTPUT_SPECIFIC_STEADY_WINDOW')
        for quantity in REQUIRED_ACTUALS:
            actual = values.get(quantity)
            if actual is None or actual.quality != 'valid':
                reasons.append('MISSING_OR_INVALID_ACTUAL:'+quantity)
            elif (actual.material_coordinate_m is None or actual.uncertainty_si is None):
                reasons.append('MISSING_ALIGNMENT_OR_UNCERTAINTY:'+quantity)
            elif window is not None and (actual.observed_at_s < window.start_s or
                    sample.timestamp_s-actual.observed_at_s > window.max_measurement_age_s):
                reasons.append('ACTUAL_OUTSIDE_WINDOW_OR_STALE:'+quantity)
        speed = values.get('entry_speed_m_s')
        if speed is not None and speed.quality == 'valid' and speed.value <= 0:
            reasons.append('NONPOSITIVE_SPEED_OUTSIDE_STEADY_SOLVER_DOMAIN')
        status = ('NOT_APPLICABLE' if sample.phase != 'steady' or sample.boundary_state == 'absent'
                  else 'WAITING_FOR_DATA' if reasons else 'READY_FOR_SEPARATE_DOMAIN_CHECKS')
        result[model] = {'status':status,'evaluation_allowed':not reasons,
                         'outputs':list(outputs),'reasons':reasons,
                         'prediction_validity':'NOT_EVALUATED',
                         'remaining_checks':['Bind actual inputs to scenario and material state.',
                                             'Run model-specific geometry/material/contact/numerical gates.',
                                             'Calibration and empirical qualification remain unestablished.']}
    # An eligible mechanics record cannot qualify an evolving roll thermal state.
    for model in ('prescribed_energy','passive_energy','standalone_thermal','equipment_snapshot'):
        result[model] = {'status':'SEPARATE_INPUT_CONTRACT_REQUIRED','evaluation_allowed':False,
                         'prediction_validity':'NOT_EVALUATED',
                         'reasons':['NO_PHASE_TO_MODEL_ADAPTER_IN_O0']}
    for model in ('dynamic_rolling','parameter_adaptation','live_control'):
        result[model] = {'status':'NOT_IMPLEMENTED','evaluation_allowed':False,
                         'prediction_validity':'NOT_EVALUATED','reasons':['OUTSIDE_O0_SCOPE']}
    return result


def assess_setup_recipe(recipe: OperatingRecipe, *, target_phase: str = 'steady') -> dict:
    """Phase-independent hypothetical setup readiness, using targets as assumptions."""
    recipe.validate()
    if target_phase not in PHASES or target_phase == 'unknown':
        raise ValueError('setup needs an explicit target phase')
    targets = {x.quantity:x.value for x in recipe.targets if x.phase == target_phase}
    missing = [q for q in REQUIRED_ACTUALS if q != 'entry_thickness_m' and q not in targets]
    reasons = ['MISSING_TARGET:'+q for q in missing]
    if targets.get('entry_speed_m_s',1.) <= 0:
        reasons.append('NONPOSITIVE_TARGET_SPEED')
    return {'status':'WAITING_FOR_INPUTS' if reasons else 'READY_FOR_HYPOTHETICAL_DOMAIN_CHECKS',
            'evaluation_allowed':not reasons,'input_basis':'RECIPE_ASSUMPTIONS_ONLY',
            'target_phase':target_phase,'reasons':reasons,'prediction_validity':'NOT_EVALUATED',
            'models':list(MECHANICS_OUTPUTS),
            'remaining_checks':['Supply geometry, friction, material state/law and model-specific parameters.',
                                'Run all numerical/domain checks; setup is not actual phase prediction.']}


def replay_operating_samples(recipes: tuple[OperatingRecipe, ...],
                             samples: tuple[OperationSample, ...]) -> dict:
    """Replay one oriented coil/pass with supplied labels; no inferred transitions.

    Recipe revisions may change, but never substitute targets for actuals.
    Reversal is a recorded unavailable phase; a new oriented pass is a new replay.
    """
    _tuple_of(recipes,OperatingRecipe,'recipes')
    _tuple_of(samples,OperationSample,'samples')
    if not recipes or not samples:
        raise ValueError('replay requires recipes and samples')
    lookup = {(r.recipe_id,r.revision):r for r in recipes}
    if len(lookup) != len(recipes):
        raise ValueError('duplicate recipe revision')
    first = samples[0]
    rows = []
    prior = None
    evidence_barrier = None
    for sample in samples:
        if (sample.coil_id,sample.scope,sample.timebase_id,sample.coordinate_reference) != (
                first.coil_id,first.scope,first.timebase_id,first.coordinate_reference):
            raise ValueError('one oriented coil/pass, timebase and coordinate reference per replay')
        if prior is not None:
            if sample.timestamp_s <= prior.timestamp_s:
                raise ValueError('sample timestamps must strictly increase')
            if sample.phase != prior.phase and sample.transition_provenance is None:
                raise ValueError('changed phase requires explicit transition provenance')
            if (sample.recipe_id,sample.recipe_revision) != (prior.recipe_id,prior.recipe_revision):
                evidence_barrier = sample.timestamp_s
        actuals = {x.quantity:x for x in sample.measurements}
        data_gap = any(q not in actuals or actuals[q].quality != 'valid'
                       or actuals[q].material_coordinate_m is None
                       or actuals[q].uncertainty_si is None for q in REQUIRED_ACTUALS)
        speed = actuals.get('entry_speed_m_s')
        stopped = speed is not None and speed.quality == 'valid' and speed.value <= 0
        # A known loss of required conditions breaks the evidence interval even
        # when an external phase annotation continues to say 'steady'. Retain
        # that unavailable row; require a fresh window only on later re-entry.
        if sample.phase != 'steady' or sample.boundary_state != 'established' or data_gap or stopped:
            evidence_barrier = sample.timestamp_s
        elif evidence_barrier is not None and any(w.start_s <= evidence_barrier for w in sample.steady_evidence):
            raise ValueError('steady evidence cannot cross a nonsteady, recipe-change, boundary-loss or data-gap event')
        recipe = lookup.get((sample.recipe_id,sample.recipe_revision))
        if recipe is None or recipe.scope != sample.scope:
            raise ValueError('recipe revision/applicability does not match the sample')
        rows.append({'sample':asdict(sample),
                     'recipe_targets':[asdict(t) for t in recipe.targets if t.phase == sample.phase],
                     'model_readiness':assess_sample_models(sample)})
        prior = sample
    return {'contract_version':CONTRACT_VERSION,'status':'OFFLINE_OBSERVATION_REPLAY_ONLY',
            'recipes':[asdict(r) for r in recipes],'samples':rows,
            'state_advanced':False,'predictions_computed':False,
            'limitations':['Phase labels and evidence are caller supplied, not detected or authenticated.',
                           'Readiness is not model validity; raw solver APIs remain hypothetical scenario tools.',
                           'No interpolation, remaining-length estimator, dynamic simulation, adaptation or control.']}
