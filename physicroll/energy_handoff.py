"""Optional steady strip / transient roll energy ledger, with prescribed boundaries.

Mechanical inputs are checked outputs from slab.py. This module supplies no
friction, film, heat-partition, HTC, flow-stress or roll-temperature closure.
The aluminium AA8015 FE study https://doi.org/10.1007/s00170-018-2811-2
motivates examining heat in cold rolling; its abstract supplies no parameters
or validation for this reduced AA5052/generic ledger. See docs/energy-handoff.md.
"""
from dataclasses import asdict, dataclass, replace
import math
from .materials import MaterialState
from .lubrication import FluidObservation


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class HeatCapacityCurve:
    """Piecewise-linear specific heat c_p(T) in J/(kg K), with bounded domain."""
    material_id: str
    temperature_k: tuple[float, ...]
    heat_capacity_j_kg_k: tuple[float, ...]
    source: str
    quality: str  # synthetic or measured; measured does not mean calibrated

    def validate(self):
        if not isinstance(self.material_id, str) or not self.material_id.strip() or not isinstance(self.source, str) or not self.source.strip():
            raise ValueError('heat-capacity curve needs material identity and source')
        if self.quality not in ('synthetic', 'measured'):
            raise ValueError('heat-capacity quality must be synthetic or measured')
        t, c = self.temperature_k, self.heat_capacity_j_kg_k
        if (not isinstance(t, tuple) or not isinstance(c, tuple) or len(t) < 2 or len(t) != len(c)
                or not all(_number(v) for v in t+c) or any(not 100 <= x <= 3000 for x in t)
                or any(a >= b for a, b in zip(t, t[1:]))
                or any(not 1 <= x <= 1e5 for x in c)):
            raise ValueError('heat capacity requires increasing K knots and J/(kg K) values in analyst sanity ranges')

    def _location(self, temperature_k):
        if not _number(temperature_k) or not self.temperature_k[0] <= temperature_k <= self.temperature_k[-1]:
            raise ValueError('temperature outside supplied heat-capacity range in K')
        for j in range(len(self.temperature_k)-1):
            if temperature_k <= self.temperature_k[j+1]:
                return j
        return len(self.temperature_k)-2

    def _knot_enthalpies(self):
        # Shared boundaries avoid forward/inverse disagreement by one ULP at
        # a valid knot, especially the upper property-domain endpoint.
        areas = [(a+b)*(t1-t0)/2 for a,b,t0,t1 in zip(
            self.heat_capacity_j_kg_k,self.heat_capacity_j_kg_k[1:],
            self.temperature_k,self.temperature_k[1:])]
        return [0.] + [math.fsum(areas[:i]) for i in range(1,len(areas)+1)]

    def enthalpy_j_kg(self, temperature_k):
        """Integral of c_p from the curve's first knot; reference cancels."""
        self.validate()
        j = self._location(temperature_k)
        knots = self._knot_enthalpies()
        if temperature_k == self.temperature_k[j+1]:
            return knots[j+1]
        total = knots[j]
        dt = temperature_k-self.temperature_k[j]
        slope = (self.heat_capacity_j_kg_k[j+1]-self.heat_capacity_j_kg_k[j])/(self.temperature_k[j+1]-self.temperature_k[j])
        value = total+self.heat_capacity_j_kg_k[j]*dt+slope*dt*dt/2
        if not math.isfinite(value):
            raise ValueError('enthalpy exceeds numerical domain')
        return value

    def temperature_for_enthalpy(self, enthalpy_j_kg):
        """Exact piecewise-quadratic inverse for positive piecewise-linear c_p."""
        self.validate()
        if not _number(enthalpy_j_kg):
            raise ValueError('enthalpy must be finite J/kg')
        knots = self._knot_enthalpies()
        if not knots[0] <= enthalpy_j_kg <= knots[-1]:
            raise ValueError('enthalpy outside supplied property range')
        for temperature, enthalpy in zip(self.temperature_k,knots):
            if enthalpy_j_kg == enthalpy:
                return temperature
        for j in range(len(self.temperature_k)-1):
            span = self.temperature_k[j+1]-self.temperature_k[j]
            cp0, cp1 = self.heat_capacity_j_kg_k[j:j+2]
            if enthalpy_j_kg < knots[j+1]:
                local = enthalpy_j_kg-knots[j]
                slope = (cp1-cp0)/span
                discriminant = cp0*cp0+2*slope*local
                if discriminant < 0:
                    raise ValueError('invalid heat-capacity inverse')
                delta = 2*local/(cp0+math.sqrt(discriminant))
                return self.temperature_k[j]+delta
        raise ValueError('enthalpy above supplied property range')


@dataclass(frozen=True)
class PassHeatBoundary:
    """All coefficients and powers are supplied, not inferred from fluid identity."""
    plastic_to_heat_fraction: float
    solid_slip_to_strip_fraction: float
    contact_heat_to_strip_w: float  # signed: positive means roll -> strip
    strip_cooling_w: float          # positive heat exported
    roll_cooling_w: float           # positive heat exported
    roll_effective_mass_kg: float
    roll_temperature_k: float
    duration_s: float
    source: str
    quality: str

    def validate(self):
        if not isinstance(self.source, str) or not self.source.strip() or self.quality not in ('synthetic', 'measured'):
            raise ValueError('heat boundary requires source and synthetic/measured quality')
        for key, value in vars(self).items():
            if key in ('source', 'quality'):
                continue
            if not _number(value):
                raise ValueError(f'{key} must be finite in SI units')
        if not 0 <= self.plastic_to_heat_fraction <= 1 or not 0 <= self.solid_slip_to_strip_fraction <= 1:
            raise ValueError('heat partitions must be fractions in [0,1]')
        if self.strip_cooling_w < 0 or self.roll_cooling_w < 0:
            raise ValueError('cooling export must be nonnegative W')
        if min(self.roll_effective_mass_kg,self.roll_temperature_k,self.duration_s) <= 0:
            raise ValueError('roll effective mass, absolute temperature and duration must be positive')


@dataclass(frozen=True)
class PassiveContactBoundary:
    """Supplied total conductance for both interfaces, W/K; no inferred HTC.

    The reduced closure uses arithmetic inlet/outlet strip and roll temperatures
    as its two representative contact temperatures. It does not resolve a bite
    temperature field or identify contact area, film behavior or conductance.
    """
    conductance_w_k: float
    source: str
    quality: str  # synthetic or measured; neither implies a calibrated law
    law_scope: str = 'conductive_only'

    def validate(self):
        if not _number(self.conductance_w_k) or self.conductance_w_k < 0:
            raise ValueError('passive contact conductance must be nonnegative W/K')
        if not isinstance(self.source,str) or not self.source.strip() or self.quality not in ('synthetic','measured'):
            raise ValueError('passive contact needs a source and synthetic/measured quality')
        if self.law_scope != 'conductive_only':
            raise ValueError('effective contact laws may already contain slip heat')


def _passive_contact_power(strip_cp, roll_cp, strip_in_k, roll_in_k, mass_flow,
                           roll_mass, duration, strip_without_contact_w,
                           roll_without_contact_w, strip_range, conductance):
    """Find Q in the shared property domain; Q>0 means roll heats strip.

    The scalar residual is strictly increasing: raising Q heats the flowing
    strip and cools the finite roll. Bisection cannot jump over a root.
    """
    strip_in_h = strip_cp.enthalpy_j_kg(strip_in_k)
    roll_in_h = roll_cp.enthalpy_j_kg(roll_in_k)
    strip_lo = max(strip_cp.temperature_k[0],strip_range[0])
    strip_hi = min(strip_cp.temperature_k[-1],strip_range[1])
    if strip_lo > strip_hi:
        raise ValueError('no shared strip property and mechanical temperature domain')
    lower = max(mass_flow*(strip_cp.enthalpy_j_kg(strip_lo)-strip_in_h)-strip_without_contact_w,
                roll_without_contact_w-roll_mass*(roll_cp.enthalpy_j_kg(roll_cp.temperature_k[-1])-roll_in_h)/duration)
    upper = min(mass_flow*(strip_cp.enthalpy_j_kg(strip_hi)-strip_in_h)-strip_without_contact_w,
                roll_without_contact_w-roll_mass*(roll_cp.enthalpy_j_kg(roll_cp.temperature_k[0])-roll_in_h)/duration)
    if not all(math.isfinite(v) for v in (lower,upper)):
        raise ValueError('passive contact bounds exceed numerical domain')
    if lower > upper:
        raise ValueError('passive contact has no shared thermal property domain')

    def inverse(curve, target, endpoint):
        try:
            return curve.temperature_for_enthalpy(target)
        except ValueError:
            if not endpoint or not math.isfinite(target):
                raise
            # Forming a Q boundary and reconstructing H from it involves two
            # rounded arithmetic paths. Accept only endpoint-scale roundoff;
            # the public property inverse remains strictly bounded.
            top = curve._knot_enthalpies()[-1]
            tolerance = 32*math.ulp(max(abs(target),abs(top),1.))
            if -tolerance <= target < 0:
                return curve.temperature_k[0]
            if top < target <= top+tolerance:
                return curve.temperature_k[-1]
            raise

    def state(q, *, endpoint=False):
        strip_target = strip_in_h+(strip_without_contact_w+q)/mass_flow
        roll_target = roll_in_h+(roll_without_contact_w-q)*duration/roll_mass
        strip_t = inverse(strip_cp,strip_target,endpoint)
        roll_t = inverse(roll_cp,roll_target,endpoint)
        delta = (roll_in_k+roll_t-strip_in_k-strip_t)/2
        law_power = conductance*delta
        residual = q-law_power
        if not all(math.isfinite(v) for v in (delta,law_power,residual)):
            raise ValueError('passive contact law exceeds numerical domain')
        return residual, strip_t, roll_t, delta

    if conductance == 0:
        if not lower <= 0 <= upper:
            raise ValueError('zero-conductance state outside supplied thermal domain')
        _, strip_t, roll_t, delta = state(0.)
        return 0., delta, 0., strip_t, roll_t

    def bounded_state(q):
        return state(q,endpoint=q in (lower,upper))

    if lower <= 0 <= upper:
        zero_residual, strip_t, roll_t, zero_delta = state(0.)
        if abs(zero_residual) <= 1e-12*max(abs(conductance*zero_delta),1.)+1e-9:
            return 0., zero_delta, zero_residual, strip_t, roll_t

    f_lo, *_ = bounded_state(lower)
    f_hi, *_ = bounded_state(upper)
    if f_lo > 0 or f_hi < 0:
        raise ValueError('passive contact root outside supplied thermal domain')
    if f_lo == 0:
        q = lower
    elif f_hi == 0:
        q = upper
    else:
        lo,hi = lower,upper
        for _ in range(160):
            q=(lo+hi)/2
            f, _, _, delta = bounded_state(q)
            if abs(f) <= 1e-12*max(abs(q),abs(conductance*delta),1.)+1e-9 or q == lo or q == hi:
                break
            if f < 0:lo=q
            else:hi=q
        else:
            raise ValueError('passive contact root did not converge')
    residual,strip_t,roll_t,delta=bounded_state(q)
    scale=max(abs(q),abs(conductance*delta),1.)
    if abs(residual)/scale > 1e-9 or q*delta < 0:
        raise ValueError('passive contact root or heat-flow direction failed')
    return q, delta, residual, strip_t, roll_t


def handoff_pass(mechanics: dict, state_in: MaterialState,
                 strip_cp: HeatCapacityCurve, roll_cp: HeatCapacityCurve,
                 boundary: PassHeatBoundary, *, fluid: FluidObservation | None = None,
                 passive_contact: PassiveContactBoundary | None = None) -> dict:
    """Steady strip enthalpy plus one aggregate roll thermal step.

    P_plastic and P_slip are total W from both strip/roll interfaces where
    applicable. No extra factor two is applied. P_nonthermal is an explicit
    mechanical work allocation, not a predicted microstructure state.
    """
    if not isinstance(mechanics, dict) or mechanics.get('numerical_converged') is not True:
        raise ValueError('checked converged mechanics result required')
    state_in.validate(); strip_cp.validate(); roll_cp.validate(); boundary.validate()
    if passive_contact is not None:
        if not isinstance(passive_contact,PassiveContactBoundary):
            raise ValueError('passive contact must be a PassiveContactBoundary')
        passive_contact.validate()
        if boundary.contact_heat_to_strip_w != 0:
            raise ValueError('passive and prescribed contact heat modes are mutually exclusive')
    if fluid is not None:
        if not isinstance(fluid, FluidObservation):
            raise ValueError("fluid must be a FluidObservation or None")
        fluid.validate()
    if state_in.alloy != strip_cp.material_id:
        raise ValueError('strip heat-capacity material differs from material state')
    meta = mechanics.get('material')
    if not isinstance(meta, dict) or not isinstance(meta.get('state_in'), dict) or not isinstance(meta.get('state_out'), dict):
        raise ValueError('mechanical pass must carry explicit material state transition')
    if meta.get('temperature_feedback') is not False:
        raise ValueError('mechanics temperature feedback must explicitly be disabled')
    temperature_range = meta.get('assumed_temperature_range_k')
    if (not isinstance(temperature_range,(tuple,list)) or len(temperature_range) != 2
            or not all(_number(v) for v in temperature_range)
            or not 0 < temperature_range[0] < temperature_range[1]):
        raise ValueError('explicit increasing assumed mechanical temperature range in K required')
    if not temperature_range[0] <= state_in.temperature_k <= temperature_range[1]:
        raise ValueError('incoming strip temperature outside assumed mechanical material range')
    before = dict(meta['state_in']); after = dict(meta['state_out'])
    for entry in (before, after):
        entry['history'] = tuple(entry['history'])
    mechanical_in, mechanical_out = MaterialState(**before), MaterialState(**after)
    mechanical_in.validate(); mechanical_out.validate()
    for name in ('alloy', 'temper', 'accumulated_equivalent_plastic_strain', 'history'):
        if getattr(state_in,name) != getattr(mechanical_in,name):
            raise ValueError(f'mechanical/thermal material-coordinate mismatch: {name}')
    if (mechanical_out.alloy, mechanical_out.temper) != (state_in.alloy, state_in.temper):
        raise ValueError('mechanical pass changed alloy or temper without a declared transformation')
    if mechanical_out.temperature_k != mechanical_in.temperature_k:
        raise ValueError('mechanical state changed temperature despite no feedback declaration')
    if mechanical_out.accumulated_equivalent_plastic_strain < state_in.accumulated_equivalent_plastic_strain:
        raise ValueError('mechanical history cannot decrease accumulated strain')
    if mechanical_out.history[:len(state_in.history)] != state_in.history or len(mechanical_out.history) != len(state_in.history)+1:
        raise ValueError('mechanical pass history must advance exactly once')
    temp_mismatch = state_in.temperature_k != mechanical_in.temperature_k
    if any(not _number(mechanics.get(key)) for key in ('mass_flow_kg_s','plastic_work_power_w',
             'solid_slip_dissipation_both_interfaces_w','mechanical_work_residual_relative',
             'mechanical_work_residual_w','roll_mechanical_power_both_rolls_w',
             'net_tension_power_w')):
        raise ValueError('mechanical mass/work fields must be finite SI values')
    mass_flow = mechanics['mass_flow_kg_s']
    plastic = mechanics['plastic_work_power_w']
    slip = mechanics['solid_slip_dissipation_both_interfaces_w']
    if mass_flow <= 0 or min(plastic,slip) < 0 or not 0 <= mechanics['mechanical_work_residual_relative'] <= 1e-4:
        raise ValueError('mechanical source outside flowing-energy domain')
    mechanical_input = mechanics['roll_mechanical_power_both_rolls_w']+mechanics['net_tension_power_w']
    identity = mechanical_input-plastic-slip
    # Recompute the slab's own normalization before any thermal/contact scale
    # enters. A supplied residual field cannot bypass the mechanical gate.
    slab_scale = max(abs(mechanics['roll_mechanical_power_both_rolls_w']),
                     abs(mechanics['net_tension_power_w']),plastic,slip,1e-30)
    recomputed_relative = abs(identity)/slab_scale
    if (not math.isfinite(recomputed_relative) or recomputed_relative > 1e-4
            or not math.isclose(recomputed_relative,mechanics['mechanical_work_residual_relative'],
                                rel_tol=1e-8,abs_tol=1e-12)):
        raise ValueError('mechanical relative work residual inconsistent or outside tolerance')
    mechanical_scale = max(abs(mechanical_input),plastic,slip,1.)
    if abs(identity-mechanics['mechanical_work_residual_w'])/mechanical_scale > 1e-10:
        raise ValueError('mechanical source work identity inconsistent with reported residual')
    strip_in_h = strip_cp.enthalpy_j_kg(state_in.temperature_k)
    roll_in_h = roll_cp.enthalpy_j_kg(boundary.roll_temperature_k)
    plastic_heat = boundary.plastic_to_heat_fraction*plastic
    nonthermal_plastic = plastic-plastic_heat
    strip_slip = boundary.solid_slip_to_strip_fraction*slip
    roll_slip = slip-strip_slip
    strip_without_contact = plastic_heat+strip_slip-boundary.strip_cooling_w
    roll_without_contact = roll_slip-boundary.roll_cooling_w
    contact = boundary.contact_heat_to_strip_w
    if passive_contact is not None:
        contact, contact_delta, contact_residual, passive_strip_t, passive_roll_t = _passive_contact_power(
            strip_cp,roll_cp,state_in.temperature_k,boundary.roll_temperature_k,
            mass_flow,boundary.roll_effective_mass_kg,boundary.duration_s,
            strip_without_contact,roll_without_contact,temperature_range,
            passive_contact.conductance_w_k)
    strip_rate = strip_without_contact+contact
    roll_rate = roll_without_contact-contact
    values = (plastic_heat,nonthermal_plastic,strip_slip,roll_slip,strip_rate,roll_rate,
              strip_in_h+strip_rate/mass_flow,
              roll_in_h+roll_rate*boundary.duration_s/boundary.roll_effective_mass_kg)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('thermal rate or target enthalpy exceeds numerical domain')
    if passive_contact is None:
        strip_t = (state_in.temperature_k if strip_rate == 0 else
                   strip_cp.temperature_for_enthalpy(values[-2]))
        roll_t = (boundary.roll_temperature_k if roll_rate == 0 else
                  roll_cp.temperature_for_enthalpy(values[-1]))
    else:
        # Keep endpoint-safe temperatures from the same Q root evaluation.
        strip_t, roll_t = passive_strip_t, passive_roll_t
    if not temperature_range[0] <= strip_t <= temperature_range[1]:
        raise ValueError('outgoing strip temperature outside assumed mechanical material range')
    strip_gain = mass_flow*(strip_cp.enthalpy_j_kg(strip_t)-strip_in_h)
    roll_storage = boundary.roll_effective_mass_kg*(roll_cp.enthalpy_j_kg(roll_t)-roll_in_h)/boundary.duration_s
    residual = (strip_gain+roll_storage+nonthermal_plastic+boundary.strip_cooling_w+
                boundary.roll_cooling_w-plastic-slip)
    scale = max(plastic,slip,abs(strip_gain),abs(roll_storage),abs(contact),1.)
    if not math.isfinite(residual) or abs(residual)/scale > 1e-8:
        raise ValueError('flowing energy balance failed numerical tolerance')
    combined_residual = mechanical_input-(strip_gain+roll_storage+nonthermal_plastic+
                                           boundary.strip_cooling_w+boundary.roll_cooling_w)
    if not math.isfinite(combined_residual) or abs(combined_residual)/max(mechanical_scale,scale)>1e-4:
        raise ValueError('combined mechanical/thermal energy balance failed')
    state_out = replace(mechanical_out, temperature_k=strip_t)
    flags = ['PRESCRIBED_HEAT_PARTITION_AND_BOUNDARIES','NO_TEMPERATURE_FEEDBACK_IN_MECHANICS',
             'NO_FILM_DISSIPATION_OR_TEMPERATURE_FIELD']
    if temp_mismatch:
        flags.append('MECHANICS_REFERENCE_TEMPERATURE_DIFFERS_FROM_CURRENT_STRIP_STATE')
    if fluid is not None:
        flags.append('FLUID_OBSERVATION_NOT_A_HEAT_OR_FRICTION_CLOSURE')
    if strip_cp.quality == 'synthetic' or roll_cp.quality == 'synthetic' or boundary.quality == 'synthetic':
        flags.append('SYNTHETIC_THERMAL_INPUTS_NOT_CALIBRATED')
    if passive_contact is not None:
        flags.append('SUPPLIED_PASSIVE_CONTACT_CONDUCTANCE_UNCALIBRATED')
        contact_entropy = contact*((1/((state_in.temperature_k+strip_t)/2))-
                                   (1/((boundary.roll_temperature_k+roll_t)/2)))
        if not math.isfinite(contact_entropy) or contact_entropy < 0:
            raise ValueError('passive contact entropy production failed')
    result = {'status':'CONDITIONAL_FLOWING_STRIP_ENERGY_LEDGER',
            'strip_state_in':asdict(state_in),'strip_state_out':asdict(state_out),
            'strip_temperature_out_k':strip_t,'roll_temperature_out_k':roll_t,
            'mass_flow_kg_s':mass_flow,'roll_effective_mass_kg':boundary.roll_effective_mass_kg,
            'duration_s':boundary.duration_s,'plastic_mechanical_work_w':plastic,
            'plastic_heat_w':plastic_heat,'nonthermal_plastic_work_w':nonthermal_plastic,
            'solid_slip_dissipation_both_interfaces_w':slip,
            'solid_slip_heat_to_strip_w':strip_slip,'solid_slip_heat_to_roll_w':roll_slip,
            'contact_heat_to_strip_w':contact,
            'contact_heat_to_roll_w':-contact,
            'strip_cooling_export_w':boundary.strip_cooling_w,
            'roll_cooling_export_w':boundary.roll_cooling_w,
            'flowing_strip_enthalpy_gain_w':strip_gain,
            'roll_thermal_storage_rate_w':roll_storage,
            'thermal_allocation_residual_w':residual,
            'combined_mechanical_to_outlets_residual_w':combined_residual,
            'thermal_allocation_residual_relative':abs(residual)/scale,
            'mechanical_work_residual_w':mechanics['mechanical_work_residual_w'],
            'mechanical_work_residual_relative':mechanics['mechanical_work_residual_relative'],
            'mechanical_reference_temperature_k':mechanical_in.temperature_k,
            'boundary':asdict(boundary),
            'strip_cp_source':strip_cp.source,'roll_cp_source':roll_cp.source,
            'fluid_observation':None if fluid is None else asdict(fluid),
            'coolant_or_lubricant_law':'none; exported heat rates supplied',
            'temperature_feedback_to_mechanics':False,
            'flags':flags}
    if passive_contact is not None:
        result.update({'contact_mode':'PASSIVE_SUPPLIED_TOTAL_CONDUCTANCE',
                       'passive_contact':asdict(passive_contact),
                       'contact_midpoint_roll_minus_strip_k':contact_delta,
                       'contact_law_residual_w':contact_residual,
                       'contact_entropy_production_w_k':contact_entropy})
    return result
