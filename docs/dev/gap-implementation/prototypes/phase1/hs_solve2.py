"""Cold start with regime switching (planner prototype)."""
import sys, math, time
sys.path.insert(0, '.')
from run_v1 import from_mattress, interp
from hs_bite import Problem


def convert(pr, u, structure):
    """Carry a solution to the other zone structure (same physics, same lam)."""
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd)
    h, _ = pr.gap(x, p, g0)
    z = pr.base_zones
    new = Problem(pr.h0, pr.h1, pr.R, pr.K, pr.mu, pr.tb, pr.tf, pr.e_star, zones=z,
                  structure=structure, winkler=pr.winkler, lam=pr.lam, closure=pr.closure)
    new.cs, new.cap, new.base_zones = pr.cs, pr.cap, z
    i2, i3 = pr.idx[2], pr.idx[3]
    if structure == 'conventional':
        nb = [bnd[0], bnd[1], 0.5 * (bnd[2] + bnd[3]), bnd[4], bnd[5]]
        hn_new = None
    else:
        # entry-side point where the conventional profile stops thinning
        jt = i2
        while jt > pr.idx[1] + 1 and h[jt - 1] <= h[jt]:
            jt -= 1
        xa = x[jt]
        xn = bnd[2]
        width = max(xn - xa, 0.02 * (bnd[3] - bnd[1]))
        nb = [bnd[0], bnd[1], xn - width, xn + 0.5 * width, bnd[3], bnd[4]]
        hn_new = min(h[jt:i2 + 1])
    xn_ = new.nodes(nb)
    pn = [interp(x, p, v) for v in xn_]
    un = pn[1:-1] + nb + [g0] + ([hn_new] if structure == 'foil' else [])
    return new, un


def needs_foil(pr, u):
    p, bnd, g0, hn = pr.unpack(u)
    x = pr.nodes(bnd)
    h, _ = pr.gap(x, p, g0)
    i2 = pr.idx[2]
    return h[i2] - h[i2 - 1] > 0.0


def solve_cold(h0, h1, R, Y, mu, tb, tf, E, nu, zones=(3, 16, 24, 16, 3), strip_modulus=80e9,
               verbose=False, cap=1.0):
    pr, u, m = from_mattress(h0, h1, R, Y, mu, tb, tf, E, nu, zones, strip_modulus=strip_modulus)
    pr.cap = cap / 2.0
    pr.base_zones = zones
    u, it, nrm = pr.newton(u)
    lam, step, total, switches = 0.0, 0.25, it, 0
    while lam < 1.0:
        new = min(1.0, lam + step)
        pr.lam = new
        try:
            u2, it, nrm = pr.newton(u, maxit=20)
            q = pr.post(u2)
            if q['min_p'] < 0:
                raise ValueError('negative pressure')
            if q['max_dh_slip'] > 1e-7 and not (pr.structure == 'conventional' and needs_foil(pr, u2)):
                raise ValueError('strip thickens in a slip zone')
            if pr.structure == 'conventional' and needs_foil(pr, u2):
                raise ArithmeticError('to_foil')
            if pr.structure == 'foil':
                _, bnd, _, _ = pr.unpack(u2)
                if bnd[3] - bnd[2] < 0.01 * (bnd[4] - bnd[1]):
                    raise ArithmeticError('to_conventional')
            u, lam = u2, new
            total += it
            step = min(step * 1.5, 0.5)
            if verbose:
                print(f'  lam {lam:.4f} {pr.structure} it {it} W {q["force_per_width_n_m"]:.4e}')
        except ArithmeticError as sw:
            # structure switch: go back to lam, approach the switch point with small steps
            pr.lam = lam
            if step > 0.02:
                step *= 0.5
                continue
            target = 'foil' if str(sw) == 'to_foil' else 'conventional'
            if verbose:
                print(f'  switch to {target} at lam {lam:.4f}')
            pr2, u2 = convert(pr, u, target)
            pr2.lam = min(1.0, lam + step)
            try:
                u3, it, nrm = pr2.newton(u2, maxit=40)
            except ValueError as e:
                raise ValueError(f'structure switch to {target} failed at lam={lam:.4f}: {e}')
            pr, u, lam = pr2, u3, pr2.lam
            total += it
            switches += 1
            if switches > 4:
                raise ValueError('too many structure switches')
        except ValueError as e:
            pr.lam = lam
            _, bnd, _, _ = pr.unpack(u)
            if (pr.structure == 'foil' and bnd[3] - bnd[2] < 0.08 * (bnd[4] - bnd[1])
                    and switches <= 4):
                pr2, u2 = convert(pr, u, 'conventional')
                pr2.lam = new
                try:
                    u3, it, nrm = pr2.newton(u2, maxit=40)
                    if needs_foil(pr2, u3):
                        raise ValueError('conventional solution still thickens before the neutral point')
                    pr, u, lam = pr2, u3, new
                    total += it
                    switches += 1
                    if verbose:
                        print(f'  switched to conventional at lam {lam:.4f}')
                    continue
                except ValueError:
                    pass
            step *= 0.5
            if step < 1e-3:
                raise ValueError(f'homotopy failed at lam={lam:.4f} ({pr.structure}): {e}')
    return pr, u, total, m
