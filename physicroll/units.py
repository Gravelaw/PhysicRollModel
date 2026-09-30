"""Explicit boundary conversions. Internal mechanics use SI; no unit guessing.

A quantity's dimension and scope (per roll, both interfaces, per width) are
separate. This converter never changes scope; the caller must retain it.
"""
import math
from decimal import Decimal

# unit: (quantity dimension, SI unit, scale, offset). Offsets apply only to absolute temperature.
UNITS = {
    'm':('length','m',1,0), 'mm':('length','m',1e-3,0),
    'Pa':('stress','Pa',1,0), 'MPa':('stress','Pa',1e6,0),
    'GPa':('stress','Pa',1e9,0),
    'N':('force','N',1,0), 'kN':('force','N',1e3,0),
    'MN':('force','N',1e6,0),
    'N/m':('line_load','N/m',1,0), 'kN/m':('line_load','N/m',1e3,0),
    'N*m':('torque','N*m',1,0), 'kN*m':('torque','N*m',1e3,0),
    'm/s':('speed','m/s',1,0), 'm/min':('speed','m/s',1/60,0),
    'rad/s':('angular_speed','rad/s',1,0), 'rpm':('angular_speed','rad/s',2*math.pi/60,0),
    's':('time','s',1,0), 'min':('time','s',60,0),
    '1':('dimensionless','1',1,0), '%':('dimensionless','1',.01,0),
    'K':('absolute_temperature','K',1,0), 'degC':('absolute_temperature','K',1,273.15),
    'delta_K':('temperature_difference','delta_K',1,0),
    'delta_degC':('temperature_difference','delta_K',1,0),
    'kg/m3':('density','kg/m3',1,0), 'g/cm3':('density','kg/m3',1e3,0),
    'W':('power','W',1,0), 'kW':('power','W',1e3,0),
    'W/m':('line_power','W/m',1,0), 'W/m2':('heat_flux','W/m2',1,0),
    'W/m3':('volumetric_heat_source','W/m3',1,0),
    'J':('energy','J',1,0), 'kg/s':('mass_flow','kg/s',1,0),
    'm3/s':('volume_flow','m3/s',1,0), '1/s':('strain_rate','1/s',1,0),
}


def _contract(value, unit, dimension):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('unit conversion needs a finite number')
    if unit not in UNITS or UNITS[unit][0] != dimension:
        raise ValueError(f'unknown or dimensionally incompatible unit {unit!r} for {dimension!r}')
    return UNITS[unit]


def to_si(value, unit, dimension):
    _,_,scale,offset = _contract(value,unit,dimension)
    # Preserve decimal table arithmetic (e.g. 4165.9 kN -> 4165900 N),
    # then enter binary SI floating-point once at the model boundary.
    result = float(Decimal(str(value))*Decimal(str(scale))+Decimal(str(offset)))
    if not math.isfinite(result) or (dimension == 'absolute_temperature' and result <= 0):
        raise ValueError('converted value outside finite/absolute-temperature domain')
    return result


def from_si(value, unit, dimension):
    _,_,scale,offset = _contract(value,unit,dimension)
    if dimension == 'absolute_temperature' and value <= 0:
        raise ValueError('absolute SI temperature must be positive')
    result = float((Decimal(str(value))-Decimal(str(offset)))/Decimal(str(scale)))
    if not math.isfinite(result):
        raise ValueError('display conversion outside finite domain')
    return result


def audited_value(*, value, unit, dimension, convention, source_id, location):
    if not convention or not source_id or not location:
        raise ValueError('source, location and quantity convention are required')
    converted = to_si(value,unit,dimension)
    return {'original_value':value,'original_unit':unit,'quantity_dimension':dimension,
            'si_value':converted,'si_unit':UNITS[unit][1],'convention':convention,
            'source_id':source_id,'source_location':location}
