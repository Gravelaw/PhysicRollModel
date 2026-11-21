import json, math, sys
A='/home/user/PhysicRollModel/artifacts/band_diagnosis/'
def zone_edges(centre, zone_width, count, edge_width=None, edge_count=0):
    widths = [zone_width]*count
    if edge_width is not None and edge_count:
        for k in range(edge_count):
            widths[k] = edge_width; widths[-1-k] = edge_width
    total = math.fsum(widths)
    e = [centre - total/2]
    for w in widths: e.append(e[-1] + w)
    return e
def zone_means(z, vals, a0, a1, edges):
    dz = z[1]-z[0]
    out = []
    for lo, hi in zip(edges, edges[1:]):
        l, h = max(lo, a0), min(hi, a1)
        if h <= l: out.append((None, 0.0)); continue
        acc = 0.0; cov = 0.0
        for zi, v in zip(z, vals):
            cl, ch = max(zi - dz/2, l), min(zi + dz/2, h)
            if ch > cl: acc += v*(ch-cl); cov += ch-cl
        out.append((acc/cov if cov > 0 else None, (h-l)/(hi-lo)))
    return out
def readings(means, edges, s):
    cov = [(m, c, hi-lo) for (m, c), lo, hi in zip(means, edges, edges[1:])]
    wsum = math.fsum(c*w for m, c, w in cov if m is not None)
    mean = math.fsum(m*c*w for m, c, w in cov if m is not None)/wsum
    m0 = [None if m is None else m-mean for m, c, w in cov]
    out = []
    for j, m in enumerate(m0):
        if m is None: out.append(None); continue
        left = m0[j-1] if j > 0 and m0[j-1] is not None else m
        right = m0[j+1] if j+1 < len(m0) and m0[j+1] is not None else m
        out.append((1-2*s)*m + s*(left+right))
    return out, mean
if __name__ == '__main__':
    for name in ('battery-foil-demo', 'lengthwise-bands-demo'):
        r = json.load(open(A+name+'.result.json'))
        st = r['width']['shape']['steady']; ts = r['width']['thermal_steady']
        z, iu = st['z_m'], st['i_units_with_feedback']; lin = st['i_units_linear_feedback']
        a0, a1 = ts['strip_start_m'], ts['strip_end_m']; c = ts['strip_centre_m']
        print('==', name, 'strip', a0, a1, 'n', len(z), 'dz', z[1]-z[0], 'z0', z[0], 'zN', z[-1])
        print(' bands:', [(round(b['start_m'],4), round(b['end_m'],4), round(b['peak_position_m'],4), round(b['peak_i_units'],3), b['sense'], b['state'], b['state_after_tension_release']) for b in st['levels']['with_feedback']['bands']])
        print(' max/min', max(iu), min(iu), 'equal lin', iu == lin)
        for zw, n, s in ((0.052, 23, 0.0), (0.052, 23, 0.125), (0.026, 46, 0.0), (0.052, 29, 0.0), (0.050, 24, 0.0)):
            e = zone_edges(c, zw, n)
            mm = zone_means(z, iu, a0, a1, e)
            rd, mean = readings(mm, e, s)
            covered = [(j, x) for j, x in enumerate(rd) if x is not None]
            jmax = max(covered, key=lambda t: abs(t[1]))
            print(f'  zone {zw*1e3:.0f} mm x{n} s={s}: mean {mean:.3e} maxabs zone {jmax[0]} [{e[jmax[0]]:.4f},{e[jmax[0]+1]:.4f}] reading {jmax[1]!r} cov {[round(c_,3) for m_,c_ in (mm[0], mm[-1])]} ncovered {len(covered)}')
            for b in st['levels']['with_feedback']['bands']:
                j = max(i for i in range(len(e)-1) if e[i] <= b['peak_position_m'])
                print(f'     band peak {b["peak_i_units"]:.4f} at {b["peak_position_m"]:.4f} width {b["width_m"]:.4f} -> zone {j} reading {rd[j]!r} ratio {rd[j]/b["peak_i_units"]:.4f}')
