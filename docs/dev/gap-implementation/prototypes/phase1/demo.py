import sys, math, time, json
sys.path.insert(0, '.'); sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
from hs_solve2 import solve_cold
from sens import derive
for name in ('battery_foil', 'lengthwise_bands'):
    case = json.load(open(f'{sys.argv[1]}/scenarios/band_diagnosis_{name}.json'))
    p = case['pass']; st = case['stand']
    rows = [('case pass', p)] + [(r['label'], r) for r in case.get('schedule', [])]
    print(name, 'R', p['work_roll_radius_m'], 'E', st['roll_youngs_modulus_pa'], 'strip E', case['material'].get('youngs_modulus_pa'))
    for label, s in rows:
        h0, h1 = s['entry_thickness_m'], s['exit_thickness_m']
        t = time.perf_counter()
        try:
            pr, u, tot, m = solve_cold(h0, h1, p['work_roll_radius_m'], s['mean_flow_stress_pa'], s['friction_coefficient'],
                                       s['entry_tension_pa'], s['exit_tension_pa'], st['roll_youngs_modulus_pa'], st['roll_poisson_ratio'],
                                       strip_modulus=case['material']['youngs_modulus_pa'] / (1 - 0.33 ** 2))
            tc = time.perf_counter() - t
            q = pr.post(u)
            d = derive(pr, u)
            F = q['force_per_width_n_m']
            print(f'  {label:10s} {h0*1e6:6.1f}->{h1*1e6:6.1f} um Y {s["mean_flow_stress_pa"]/1e6:.0f} mu {s["friction_coefficient"]} {pr.structure:12s} F/w {F:.4e} (mattress {m["force_per_width_n_m"]:.4e} {m["regime"]}) slip {q["forward_slip"]:.3f} (m {m["forward_slip_fraction"]:.3f}) L {q["contact_length_m"]*1e3:.3f} mm (m {m["contact_length_m"]*1e3:.3f}) Q {-d["F_h1"]:.3e} Pa Nx {-d["F_tf"]:.3e} m e_mu {d["F_mu"]*pr.mu/F:.2f} cold {tc:.2f}s sens {d["time_s"]:.2f}s')
        except ValueError as e:
            print(f'  {label:10s} {h0*1e6:6.1f}->{h1*1e6:6.1f} FAILED {str(e)[:140]} ({time.perf_counter()-t:.2f}s)')
