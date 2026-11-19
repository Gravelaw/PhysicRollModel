import sys, time, json, cProfile, pstats, io
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import band_diagnosis as bd, foil_bite as fb, chatter as ch
name = sys.argv[2]
case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_{name}.json'))
cnt = {'mat': 0, 'hit': 0, 'mat_t': 0.0, 'hit_t': 0.0, 'smb': 0, 'smb_t': 0.0}
_m = bd.derive_bite_response_mattress
def m(*a, **k):
    t = time.perf_counter()
    try: return _m(*a, **k)
    finally:
        cnt['mat'] += 1; cnt['mat_t'] += time.perf_counter()-t
bd.derive_bite_response_mattress = m
_h = bd.derive_bite_response
def h(*a, **k):
    t = time.perf_counter()
    try: return _h(*a, **k)
    finally:
        cnt['hit'] += 1; cnt['hit_t'] += time.perf_counter()-t
bd.derive_bite_response = h
from physicroll import band_process as bpr
_s = bpr.solve_mattress_bite
def s(*a, **k):
    t = time.perf_counter()
    try: return _s(*a, **k)
    finally:
        cnt['smb'] += 1; cnt['smb_t'] += time.perf_counter()-t
bpr.solve_mattress_bite = s
t = time.perf_counter()
r = bd.diagnose(case)
print(name, 'diagnose s', round(time.perf_counter()-t, 2), cnt, 'derivations', r.get('bite_derivations'))
