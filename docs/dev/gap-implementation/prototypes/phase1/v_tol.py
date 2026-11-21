import sys, math
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
import hs_select as S
from hs_solve2 import solve_cold
Ys = 230e6; Y = Ys * math.sqrt(3) / 2; Es = 230e9; E = Es * 0.91
cases = [(f'r{r} {g}um', g * 1e-6, g * 1e-6 * (1 - r), 0.089, Y, 0.03, 0.0, 0.0, E, 80e9) for r, g in ((0.5, 54), (0.5, 52), (0.5, 50), (0.5, 48), (0.5, 46), (0.25, 34), (0.25, 32), (0.25, 30), (0.1, 28), (0.1, 26), (0.1, 24))]
cases.append(('cap case mu0.03', 50e-6, 25e-6, 0.135, 150e6 * math.sqrt(3) / 2, 0.03, 20e6, 20e6, 210e9, 80e9))
for name, h0, h1, R, Yv, mu, tb, tf, Ev, sm in cases:
    K = 2 * Yv / math.sqrt(3); es = Ev / 0.91; scale = es / (R * K ** 2)
    pr, u, tot, m = solve_cold(h0, h1, R, Yv, mu, tb, tf, Ev, 0.3, strip_modulus=sm)
    p3, u3 = S.p3_of(pr, u, K, es, sm)
    out = []
    def rec(tag, p, v):
        q = p.post(v)
        r = S.shear_ratios(p, v)[0] if p.flat else []
        bm = q['bounds_m']
        out.append(f'{tag}: Wbar {q["force_per_width_n_m"]*scale:.3f} slip {q["forward_slip"]:.4f} B {1e6*(bm[3]-bm[2]):.0f} E {1e6*(bm[4]-bm[3]):.0f} um max ratio {max(r) if r else None} count>1 {sum(1 for v_ in r if v_ > 1+1e-6)} maxdh {max(q["max_dh"]):.1e}')
    if p3.flat:
        rec('ABF(march)', p3, u3)
        try:
            o = S.add_e(p3, u3, K, es, sm)
            if o: rec('ABEF', *o)
        except ValueError as e:
            out.append(f'ABEF failed {e}')
    try:
        pc, uc = S.conventional_of(p3, u3, K, es, sm)
        rec('AF', pc, uc)
        for base in ((3, 16, 24, 8, 16, 3), (3, 16, 8, 16, 16, 3), (3, 16, 12, 12, 16, 3)):
            try:
                o = S.six_from_conventional(pc, uc, K, es, sm, base=base)
                if o: rec(f'ABEF from AF {base[2]}/{base[3]}', *o)
            except ValueError as e:
                out.append(f'ABEF from AF {base[2]}/{base[3]} failed {e}')
    except ValueError as e:
        out.append(f'AF failed {e}')
    print(name); [print('   ', o) for o in out]
