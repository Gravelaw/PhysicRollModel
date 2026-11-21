import sys, time, json
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from physicroll import band_survey as bs, band_diagnosis as bd, band_plain as bpl, foil_bite as fb, chatter as ch
cnt = {'mat': 0, 'hit': 0, 'mat_t': 0.0, 'hit_t': 0.0}
def wrap(mod, name, key):
    f = getattr(mod, name)
    def g(*a, **k):
        t = time.perf_counter()
        try: return f(*a, **k)
        finally:
            cnt[key] += 1; cnt[key + '_t'] += time.perf_counter() - t
    setattr(mod, name, g)
for mod in (bd, bs):
    if hasattr(mod, 'derive_bite_response_mattress'): wrap(mod, 'derive_bite_response_mattress', 'mat')
    if hasattr(mod, 'derive_bite_response'): wrap(mod, 'derive_bite_response', 'hit')
if sys.argv[2] == 'survey':
    t = time.perf_counter()
    r = bs.survey()
    print('survey s', round(time.perf_counter() - t, 1), cnt, 'rows', len(r.get('rows', [])))
else:
    case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_battery_foil.json'))
    print(bpl.PROFILES)
    for prof in bpl.PROFILES:
        cnt.update(mat=0, hit=0, mat_t=0.0, hit_t=0.0)
        ec, left = bpl.apply_profile(case, prof)
        t = time.perf_counter()
        r = bd.diagnose(ec)
        print(prof, 'diagnose s', round(time.perf_counter() - t, 1), cnt, ec['model_options'], 'left out', left)
