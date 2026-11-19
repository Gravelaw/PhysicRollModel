import sys, time, math
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
from physicroll import foil_bite as fb
from physicroll.chatter import BitePass, derive_bite_response
calls = {'core': 0, 'conv': 0}
_core = fb._solve_core
def core(*a, **k):
    calls['core'] += 1
    return _core(*a, **k)
fb._solve_core = core
_conv = fb._converged
def conv(*a, **k):
    calls['conv'] += 1
    return _conv(*a, **k)
fb._converged = conv
Ys = 230e6; Y = Ys*math.sqrt(3)/2; E = 230e9*(1-0.09)
t = time.perf_counter()
r = fb.solve_mattress_bite(20e-6, 15e-6, 1.0, 0.089, Y, 0.03, 0.0, 0.0, roll_youngs_modulus_pa=E, roll_poisson_ratio=0.3)
dt = time.perf_counter()-t
print('solve_mattress_bite BT-V1', dt, calls, r['force_per_width_n_m'], r['force_per_width_n_m']*230e9/(0.089*Ys**2), r['regime'], r['forward_slip_fraction'], r['contact_length_m'])
calls.update(core=0, conv=0)
bpass = BitePass(20e-6, 15e-6, 1.0, 0.089, Y, 0.03, 0.0, 0.0)
t = time.perf_counter()
b = fb.derive_bite_response_mattress(bpass, roll_youngs_modulus_pa=E, roll_poisson_ratio=0.3, cells=400)
print('derive mattress BT-V1 cells400', time.perf_counter()-t, calls)
calls.update(core=0, conv=0)
# battery foil F1: 50->30 um R 0.135
bp2 = BitePass(50e-6, 30e-6, 1.2, 0.135, 175e6, 0.03, 30e6, 30e6)
t = time.perf_counter()
try:
    b = fb.derive_bite_response_mattress(bp2, cells=400)
    print('derive mattress 50->30', time.perf_counter()-t, calls, b.separating_force_n/1.2, b.forward_slip_fraction, b.contact_length_m)
except ValueError as e:
    print('rej', e)
# hitchcock sheet
bp3 = BitePass(0.4e-3, 0.28e-3, 1.2, 0.2, 150e6, 0.05, 30e6, 30e6)
t = time.perf_counter()
b = derive_bite_response(bp3, cells=256)
print('derive hitchcock sheet', time.perf_counter()-t, b.separating_force_n/1.2)
