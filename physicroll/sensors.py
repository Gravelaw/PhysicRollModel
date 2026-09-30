"""Disconnected sensor taxonomy and synthetic predicted signals, SI only.

No PLC/OPC-UA/historian access, fabricated timestamps or fake measurements.
Physical marker positions refer to the generic illustrative Blender layout.
"""
from dataclasses import asdict, dataclass
import math
from .model import Scenario


@dataclass(frozen=True)
class SensorSpec:
    sensor_id: str
    instrument_type: str
    quantity: str
    unit_si: str
    station: str
    observation_kind: str
    model_result_key: str | None
    source_url: str
    quality_note: str


SPECS = (
    SensorSpec('entry_gauge', 'X-ray strip thickness gauge', 'entry thickness', 'm', 'entry', 'direct', None,
               'https://www.danieli.com/en/products/products-processes-and-technologies/product-lines/hithix_26_115.htm',
               'Alloy-specific calibration, source health and strip position needed.'),
    SensorSpec('exit_gauge', 'X-ray strip thickness gauge', 'exit thickness', 'm', 'exit', 'direct', None,
               'https://www.danieli.com/en/products/products-processes-and-technologies/product-lines/hithix_26_115.htm',
               'Exit measurement is downstream of bite; transport delay matters in dynamics.'),
    SensorSpec('roll_force', 'Load cell or hydraulic pressure-derived stand force', 'separating force', 'N', 'stand', 'direct_or_calibrated_inference', 'separating_force_n',
               'https://www.jstage.jst.go.jp/article/isijinternational/58/4/58_ISIJINT-2017-623/_html/-char/en',
               'Know sensor load path, zero and actuator/roll-bending force before comparison.'),
    SensorSpec('stand_position', 'Hydraulic cylinder displacement sensor / LVDT', 'unloaded mechanical gap or actuator position', 'm', 'stand', 'direct', None,
               'https://www.dwyeromega.com/en-us/resources/lvdt-sensors',
               'A measured cylinder position is not automatically the loaded roll gap.'),
    SensorSpec('hydraulic_cap_pressure', 'Hydraulic pressure transducer', 'cap-side cylinder pressure', 'Pa', 'stand', 'direct', None,
               'https://www.danieli.com/en/products/processes-technologies/product-lines/hydraulic-automatic-gap-control-cylinders_26_203.htm',
               'Thrust also needs cap/rod areas, both pressures, tare/friction and motion state.'),
    SensorSpec('hydraulic_rod_pressure', 'Hydraulic pressure transducer', 'rod-side cylinder pressure', 'Pa', 'stand', 'direct', None,
               'https://www.danieli.com/en/products/processes-technologies/product-lines/hydraulic-automatic-gap-control-cylinders_26_203.htm',
               'Pressure differential thrust is an alternative force observation, not an extra load.'),
    SensorSpec('roll_bending_force', 'Roll-bending hydraulic pressure or load cell', 'roll-bending actuator force', 'N', 'stand', 'direct_or_calibrated_inference', None,
               'https://www.abb.com/global/en/areas/automation/measurement-analytics/force-measurement/flatness-measurement/flatness-systems',
               'Acts within roll-stack equilibrium; no bending compliance solver is implemented.'),
    SensorSpec('entry_tension', 'Deflector-roll load cell', 'entry strip tension force', 'N', 'entry', 'direct_after_geometry_calibration', 'entry_tension_force_n',
               'https://www.abb.com/global/en/areas/automation/measurement-analytics/force-measurement/strip-tension',
               'Convert resultant roll bearing load using wrap angle and tare.'),
    SensorSpec('exit_tension', 'Deflector-roll load cell', 'exit strip tension force', 'N', 'exit', 'direct_after_geometry_calibration', 'exit_tension_force_n',
               'https://www.abb.com/global/en/areas/automation/measurement-analytics/force-measurement/strip-tension',
               'Convert force to stress with local exit cross section.'),
    SensorSpec('entry_strip_speed', 'Laser Doppler strip speed gauge', 'entry strip speed', 'm/s', 'entry', 'direct', None,
               'https://www.polytec.com/en/velocimetry',
               'Direct strip speed avoids roll-slip assumptions; installation-specific optics.'),
    SensorSpec('exit_strip_speed', 'Laser Doppler strip speed gauge', 'exit strip speed', 'm/s', 'exit', 'direct', 'exit_speed_m_s',
               'https://www.polytec.com/en/velocimetry',
               'Measure after bite; align by material parcel for transient comparisons.'),
    SensorSpec('work_roll_speed', 'Work-roll shaft rotary encoder', 'work-roll angular speed', 'rad/s', 'stand', 'direct', 'roll_angular_speed_rad_s',
               'https://www.encoder.com/',
               'Gear ratio, direction, shaft location and slip must be identified.'),
    SensorSpec('work_roll_torque', 'Drive shaft torque transducer or inferred motor torque', 'work-roll torque', 'N*m', 'stand', 'direct_or_inferred', 'torque_per_work_roll_nm',
               'https://www.kistler.com/',
               'Motor current requires calibrated motor/gear losses; model is energy-equivalent proxy.'),
    SensorSpec('flatness', 'Segmented shapemeter / flatness roll', 'widthwise flatness stress profile', 'Pa', 'exit', 'direct_after_calibration', None,
               'https://www.abb.com/global/en/areas/automation/measurement-analytics/force-measurement/flatness-measurement/flatness-systems/flatness-measurement-system',
               'No flatness model; not geometric crown or a measured residual stress field.'),
    SensorSpec('strip_temperature', 'Infrared strip pyrometer', 'surface temperature', 'K', 'exit', 'direct_after_emissivity_calibration', None,
               'https://www.flukeprocessinstruments.com/en-us/service-and-support/knowledge-center/infrared-technology/emissivity-metals',
               'Aluminium emissivity, reflections and coating state require validation.'),
)


def marker_positions(s: Scenario) -> dict[str, tuple[float,float,float]]:
    """Generic scene positions, not surveyed mill coordinates."""
    r,w,h=s.work_roll_radius_m,s.width_m,s.exit_thickness_m
    span=max(3.2,10*r)
    gauge=span*.53
    return {
        'entry_gauge':(-gauge,0,.21), 'exit_gauge':(gauge,0,.21),
        'roll_force':(0,-(w+.4)/2-.3,h/2+2*r+1.8*r),
        'stand_position':(0,-(w+.4)/2-.3,2*r+2*1.8*r+.6),
        'hydraulic_cap_pressure':(-.22,-(w+.4)/2-.3,2*r+2*1.8*r+.45),
        'hydraulic_rod_pressure':(.22,-(w+.4)/2-.3,2*r+2*1.8*r+.45),
        'roll_bending_force':(.22,-(w+.4)/2-.3,h/2+2*r+1.8*r),
        'entry_tension':(-gauge*.74,0,.25), 'exit_tension':(gauge*.74,0,.25),
        'entry_strip_speed':(-gauge*.8,-w/2-.1,.12), 'exit_strip_speed':(gauge*.8,-w/2-.1,.12),
        'work_roll_speed':(0,-(w+.4)/2-.3,r+h/2),
        'work_roll_torque':(.27,-(w+.4)/2-.3,r+h/2),
        'flatness':(gauge*.75,0,.12),
        'strip_temperature':(gauge*.91,-w/2-.1,.2),
    }


def sensor_manifest(s: Scenario, process: dict) -> dict:
    s.validate()
    if process.get('scenario') != asdict(s):
        raise ValueError('Sensor manifest requires matching scenario provenance')
    positions=marker_positions(s)
    signals=[]
    for spec in SPECS:
        info=asdict(spec)
        x,y,z=positions[spec.sensor_id]
        if not all(math.isfinite(v) for v in (x,y,z)):
            raise ValueError('Invalid scene sensor position')
        info.update(position_m={'x':x,'y':y,'z':z},position_status='synthetic_scene_marker',
                    observation_shape='widthwise_profile' if spec.sensor_id=='flatness' else 'scalar',
                    equipment_id='sensor_marker_'+spec.sensor_id,
                    raw_signal_value=None,raw_signal_unit=None,
                    calibrated_observation_value_si=None,derived_estimate_value_si=None,
                    observed_value_si=None,observed_timestamp_utc=None,quality='unavailable',
                    uncertainty_si=None,filter_delay_s=None,bandwidth_hz=None,
                    material_coordinate_m=None,material_alignment_status='unavailable',
                    sensor_to_bite_distance_m=abs(x),
                    nominal_steady_transport_time_s=abs(x)/(s.entry_speed_m_s if x<0 else process['exit_speed_m_s']) if x else 0.0,
                    data_origin='no_plant_connection',
                    model_estimate_si=process.get(spec.model_result_key) if spec.model_result_key else None)
        if spec.sensor_id=='entry_gauge': info['model_estimate_si']=s.entry_thickness_m
        if spec.sensor_id=='exit_gauge': info['model_estimate_si']=s.exit_thickness_m
        if spec.sensor_id=='entry_strip_speed': info['model_estimate_si']=s.entry_speed_m_s
        signals.append(info)
    return {'registry_version':'0.2.0','scenario_name':s.name,
            'status':'DISCONNECTED_GENERIC_SENSOR_MAP','signals':signals,
            'semantics':'model_estimate_si is a synthetic prediction/input, never a sensor reading; nominal travel time is not timestamp alignment'}
