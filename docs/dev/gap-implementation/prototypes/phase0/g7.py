import sys, json, dataclasses
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import band_process as bp, band_diagnosis as bd, band_signatures as bs
from physicroll.band_report import render_band_report
name = sys.argv[1]; out = sys.argv[2]
_mu = bp._mu_inputs
MATT = {'on': False}
def mu_inputs(trib, src, radius, ratio, slip, exit_speed):
    # scratch proxy: Hitchcock ratios in the demos are <= 1.5; mattress ratios are above
    return _mu(trib, src, radius, 1.0 if ratio > 1.5 else ratio, slip, exit_speed)
bp._mu_inputs = mu_inputs
_fc = bp.friction_curve
def fcurve(case, trib, bite):
    if bp.is_mattress(bite): bite = dataclasses.replace(bite, contact_radius_ratio=1.0)
    return _fc(case, trib, bite)
bp.friction_curve = fcurve
_ss = bd._section_screens
def screens(case, bite, slip, contact_length, ratio, flags):
    if bite is not None and bp.is_mattress(bite): ratio = 1.0
    return _ss(case, bite, slip, contact_length, ratio, flags)
bd._section_screens = screens
case = bd.load_case(f'/home/user/PhysicRollModel/scenarios/band_diagnosis_{name}.json')
r = bd.diagnose(case)
open(f'{out}/{name}.result.json', 'w').write(bd.result_json(r))
open(f'{out}/{name}.report.html', 'w').write(render_band_report(r))
