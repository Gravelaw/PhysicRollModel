"""Scratch helpers (SPEC19 planner). Imports the export of commit 8f10cbe, never the repo."""
import json, sys, os, time, math
HEAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 's23', 'head')
sys.path.insert(0, HEAD)
sys.dont_write_bytecode = True
from physicroll import band_diagnosis as bd, band_width as bw, roll_thermal as rt, strip_shape as ss

def load(name):
    case = bd.load_case(os.path.join(HEAD, 'scenarios', f'band_diagnosis_{name}.json'))
    art = json.load(open(os.path.join(HEAD, 'artifacts', 'band_diagnosis',
                                      name.replace('_', '-') + '-demo.result.json')))
    return case, art

def thermal(case, art):
    iu = art['width']['inputs_used']
    w = case['width_model']
    th = bw._Thermal(case, w, iu['bite_heat_per_width_w_m'], iu['roll_heat_fraction_per_roll'])
    return th

def shape_params(case, art):
    iu = art['width']['inputs_used']
    w = case['width_model']
    sup = {'strip_stiffness_per_width_pa': iu['strip_stiffness_per_width_pa'],
           'bite_half_length_m': iu['bite_half_length_m'],
           'exit_tension_force_sensitivity_per_width_m': iu['exit_tension_force_sensitivity_per_width_m']}
    return bw.shape_params(case, None, w, None, supplied=sup)
