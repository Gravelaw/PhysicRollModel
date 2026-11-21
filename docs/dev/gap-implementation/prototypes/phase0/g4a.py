import sys, json, time, math
sys.path.insert(0, '/home/user/PhysicRollModel'); sys.dont_write_bytecode = True
from physicroll import band_process as bp, band_diagnosis as bd, strip_shape as ss, band_width as bw
case = bd.load_case('/home/user/PhysicRollModel/scenarios/band_diagnosis_battery_foil.json')
eff = case
cache = bd._BiteCache(eff)
rows = []
for label, src in bp.pass_rows(eff):
    t = time.time()
    try:
        bite = cache.get(bp.bite_pass(eff, src))
        model = bd.perturbed_bite_model(eff, bite)
        def gb(bpass, model=model): return cache.get(bpass, model=model)
        t1 = time.time()
        s = bp.friction_force_sensitivity(gb, bp.bite_pass(eff, src))
        t2 = time.time()
        W = eff['pass']['width_m']
        fpw = bite.separating_force_n / W
        m_mu = s['dforce_dfriction_n'] / W
        n = m_mu * src['friction_coefficient'] / fpw
        rows.append(dict(label=label, h1=src['exit_thickness_m'], fpw=fpw, m_mu=m_mu, n=n, q=bite.strip_modulus_n_m / W,
                         a=bite.contact_length_m / 2, nx=-bite.dforce_dexit_tension_m2 / W, mattress=bp.is_mattress(bite), tb=t1 - t, ts=t2 - t1, sens={k: v for k, v in s.items() if not isinstance(v, (dict, list))}))
        print(label[:14], 'h1', src['exit_thickness_m'], 'F/w', fpw, 'M_mu', m_mu, 'exponent', n, 'bite s', round(t1 - t, 2), 'sens s', round(t2 - t1, 2), 'mattress', bp.is_mattress(bite))
    except ValueError as e:
        print(label[:14], 'REJECTED', e)
json.dump(rows, open('g4rows.json', 'w'), indent=1)
print(rows[0]['sens'])
