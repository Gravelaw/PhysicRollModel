"""Real partial results of the band engine, for the plain-layer and app tests (SPEC16 review).

Each case is built from the engine's own test fixtures or the repository scenarios and run
through ``band_diagnosis.diagnose`` (quick profile where it has a width model), so the
summaries are tested on what the engine really returns when parts cannot be computed, not on
hand-edited result dicts. Results are computed once per process and cached.
"""
import copy
import json
from pathlib import Path

from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl
from tests.test_band_lengthwise import v2
from tests.test_band_operating_bite_missing import _case as no_bite_case

ROOT = Path(__file__).resolve().parents[1]


def _scenario(name):
    return json.loads((ROOT / 'scenarios' / f'band_diagnosis_{name}.json').read_text())


def case_no_bite():
    """The operating pass has no roll bite (the engine's own no-bite test case)."""
    c = no_bite_case(product='battery_collector_foil')
    c['observation']['orientation'] = 'longitudinal'
    return c


def case_no_bite_width():
    """No roll bite and a width model: the roll thermal part is not assessable."""
    c = no_bite_case(width=True)
    c['observation']['orientation'] = 'longitudinal'
    c['observation']['band_positions_across_width_m'] = [0.6, 0.9]
    return c


def case_schedule_row_rejected():
    """The operating pass solves; the schedule pass is rejected by the roll-gap model."""
    c = no_bite_case(row_friction=0.03)
    c['pass']['friction_coefficient'] = 0.02
    c['observation']['orientation'] = 'longitudinal'
    return c


def case_sections_not_supplied():
    """A v2 case with no width model, no tribology and no schedule."""
    c = v2(override=False, orientation='transverse')
    c['width_model'] = c['tribology'] = c['hardening'] = None
    c['schedule'] = []
    return c


def case_v1():
    """A v1 case (the bearing-order demo as written)."""
    return _scenario('bearing_order')


def case_foil_not_credible():
    """Battery foil 25 -> 12 um: an extended-domain bite whose force is not credible."""
    c = _scenario('battery_foil')
    c['pass'].update(entry_thickness_m=25e-6, exit_thickness_m=12e-6, entry_tension_pa=38e6,
                     exit_tension_pa=42e6, mean_flow_stress_pa=185e6)   # the dry run's pass
    c['schedule'] = []
    c['hardening'] = None
    c['observation'] = {k: ([] if isinstance(v, list) else None)
                        for k, v in c['observation'].items()}
    c['observation'].update(orientation='longitudinal', lengthwise_continuity='both',
                            worse_at_thinner_gauge=True)
    return c


def case_template():
    """The case template as it stands (every observation null)."""
    return _scenario('template')


CASES = {'no_bite': case_no_bite, 'no_bite_width': case_no_bite_width,
         'schedule_row_rejected': case_schedule_row_rejected,
         'sections_not_supplied': case_sections_not_supplied, 'v1': case_v1,
         'foil_not_credible': case_foil_not_credible, 'template': case_template}
_RESULTS = {}


def result(name):
    """(case as entered, engine result) of one partial case, quick profile."""
    if name not in _RESULTS:
        case = CASES[name]()
        engine_case = case
        if case.get('case_schema') == bd.CASE_SCHEMA_V2:
            engine_case, _ = bpl.apply_profile(case, 'quick')
        _RESULTS[name] = (case, bd.diagnose(engine_case))
    return copy.deepcopy(_RESULTS[name])
