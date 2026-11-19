from wind import *
def run(dh, er_fun, label, n_layers=150, nl_lanes=24, sy=165e6, e_hard=0.0, Tw=30e6, air=None):
    rc, R, E, nu, h = 0.15, 0.60, 70e9, 0.33, 30e-6
    nl = (R - rc)/h/n_layers
    hs = [h]*nl_lanes; hard = nl_lanes//2; hs[hard] = h + dh
    widths = [0.05]*nl_lanes; e_nat = [0.0]*nl_lanes; e_nat[hard] = e_hard
    lanes = [Lane(rc, hj, nl, E, nu, er_fun) for hj in hs]
    t0 = time.perf_counter(); rows = []
    for k in range(n_layers):
        s0, alloc = allocate(lanes, widths, e_nat, Tw, E, sy)
        for ln, (sig, ep) in zip(lanes, alloc): ln.add_layer(sig, ep)
        if k + 1 in (1, 2, 5, 10, 20, 50, 100, 150):
            hd, nb = lanes[hard], lanes[0]
            laps = (k + 1)*nl
            rows.append((k + 1, round(laps), round(alloc[hard][0]/1e6, 2), round(alloc[0][0]/1e6, 2), round((hd.outer_radius() - nb.outer_radius())*1e6, 3),
                         round(laps*dh*1e6, 2), round(alloc[hard][1]*1e5, 3)))
    dt = time.perf_counter() - t0
    hd, nb = lanes[hard], lanes[0]
    print(label, 'dh', dh*1e6, 'um; time', round(dt, 2), 's')
    print('   (layer, laps, wound-on tension hard / neighbour MPa, radius difference um, laps*dh um, plastic strain of the lap in I-units)')
    for r in rows: print('   ', r)
    dR = hd.outer_radius() - nb.outer_radius()
    c_eff = dR/((R - rc)/h*dh) if dh else None
    pmax_h, pmax_n = max(-v for v in hd.sr), max(-v for v in nb.sr)
    ep = hd.ep; first = next((i for i, v in enumerate(ep) if v > 0), None)
    print('   effective compaction factor', None if c_eff is None else round(c_eff, 4), ' max interlayer pressure hard / neighbour MPa', round(pmax_h/1e6, 3), round(pmax_n/1e6, 3),
          ' min in-coil hoop stress hard MPa', round(min(hd.st)/1e6, 2), ' first yielding layer', first, 'of', n_layers, ' max plastic strain I-units', round(max(ep)*1e5, 2),
          ' yielding length fraction', round(sum(1 for i, v in enumerate(ep) if v > 0)/n_layers, 3))
    return lanes
E = 70e9
print('--- uniform strip (all lanes equal): tensions must stay at the mean')
run(0.0, lambda p: E/100, 'constant E_r = E/100')
for dh in (1e-6, 0.1e-6):
    run(dh, lambda p: E, 'isotropic E_r = E_t (stiff stack)')
    run(dh, lambda p: E/100, 'constant E_r = E_t/100 (S40 VP: two orders softer)')
    run(dh, lambda p: 100.0*(p + 1e4), 'Pfeiffer K2 = 100, K1 = 10 kPa (assumed)')
    run(dh, lambda p: 30.0*(p + 1e4), 'Pfeiffer K2 = 30, K1 = 10 kPa (assumed)')
