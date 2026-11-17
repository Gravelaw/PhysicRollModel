"""Tests for physicroll.roll_thermal (W1). Coarse grids / short barrels keep this module fast;
the default 2 m grid is exercised only by the performance guard.

Analytic references (derived here, [D]):
- steady uniform q, h: T = Tc + q/h at every r;
- radially lumped (k_r -> inf): rho*c*R/2 dT/dt = q - h (T - Tc) per unit surface ->
  T - Tc = q/h (1 - exp(-t/tau)), tau = rho*c*R/(2h); steady step in h at z0 along z:
  k T'' = (2h/R)(T - Tc - q/h) -> exponentials with l = sqrt(k*R/(2h)), T and k*T' continuous;
- pure radial transient, uniform h, step in q from T = Tc: theta = T - Tc - q/h starts at
  -q/h; separation of variables gives the area-mean
  theta_mean/theta_0 = sum_n 4 Bi^2/(zeta_n^2 (zeta_n^2 + Bi^2)) exp(-zeta_n^2 a t/R^2)
  with zeta_n J1(zeta_n) = Bi J0(zeta_n) (mean of J0(zeta r/R) over the disc is
  2 J1(zeta)/zeta; J0^2 + J1^2 = J1^2 (zeta^2 + Bi^2)/Bi^2 on a root);
- radius growth: d(dR)/dt = factor*(2*alpha/R) * d/dt integral (T r dr)
  = factor*2*alpha/(rho*c) * (net surface flux), so right after a nozzle switch-off from a
  steady state the growth rate is factor*2*alpha*dh*(T_s - Tc)/(rho*c) in ANY radial model.
"""
import json
import math
import time
import unittest

from physicroll.roll_thermal import (
    RollThermalProperties, SprayHeader, ThermalSegment, history_metrics, local_stripes,
    simulate, steady_state)

RHO, CP, K, ALPHA, NU = 7850.0, 470.0, 40.0, 11.7e-6, 0.3
TC = 313.15


def dumps(value):
    return json.dumps(value, allow_nan=False)


def uniform_header(h):
    """No spray, uniform background h (exactly uniform along the barrel)."""
    return SprayHeader(nozzle_pitch_m=0.05, standoff_m=0.1, spray_angle_rad=0.5,
                       spray_mean_htc_w_m2k=0.0, background_htc_w_m2k=h)


def double_overlap_header(pitch=0.052, h_spray=1000.0, h_bg=50.0):
    """W_eff = 2*pitch: uniform weight 1 in the interior; a blocked nozzle halves it."""
    angle = 2 * math.atan(pitch / 0.15)
    return SprayHeader(nozzle_pitch_m=pitch, standoff_m=0.15, spray_angle_rad=angle,
                       spray_mean_htc_w_m2k=h_spray, background_htc_w_m2k=h_bg)


def bessel_j(order, x):
    term = (x / 2) ** order / math.factorial(order)
    total, m = term, 0
    while abs(term) > 1e-18 * max(1.0, abs(total)) or m < 5:
        m += 1
        term *= -(x / 2) ** 2 / (m * (m + order))
        total += term
    return total


def bessel_roots(bi, count):
    f = lambda z: z * bessel_j(1, z) - bi * bessel_j(0, z)  # noqa: E731
    roots, z, step = [], 1e-6, 0.01
    while len(roots) < count:
        a, b = z, z + step
        if f(a) * f(b) < 0:
            for _ in range(80):
                mid = (a + b) / 2
                if f(a) * f(mid) <= 0:
                    b = mid
                else:
                    a = mid
            roots.append((a + b) / 2)
        z += step
    return roots


def segment(duration=1.0, levels=None, width=1.5, centre=None, heat=5e5, frac=0.1):
    return ThermalSegment(duration_s=duration, bite_heat_per_width_w_m=heat,
                          roll_heat_fraction_per_roll=frac, strip_width_m=width,
                          strip_centre_m=centre, coolant_temperature_k=TC,
                          nozzle_levels=levels)


class ReferenceLimitTests(unittest.TestCase):
    def test_steady_uniform_is_q_over_h_at_every_radius(self):
        roll = RollThermalProperties(radius_m=0.2, barrel_length_m=0.2)
        seg = segment(width=0.2, heat=4e5, frac=0.1)
        res = steady_state(roll, uniform_header(800.0), seg, axial_cell_m=0.02,
                           radial_cells=12)
        q = 0.1 * 4e5 / (2 * math.pi * 0.2)
        for row in res['field']['temperature_k']:
            for t in row:
                self.assertAlmostEqual(t, TC + q / 800.0, delta=1e-6)
        for t in res['surface_temperature_k']:
            self.assertAlmostEqual(t, TC + q / 800.0, delta=1e-6)
        self.assertTrue(res['solver']['converged'])
        self.assertAlmostEqual(res['radius_growth_m'][0], ALPHA * 0.2 * q / 800.0, delta=1e-12)
        self.assertLess(abs(res['relative_energy_residual']), 1e-8)

    def test_lumped_limit_exponential_approach(self):
        h, radius = 1000.0, 0.2
        roll = RollThermalProperties(radius_m=radius, barrel_length_m=0.2,
                                     radial_conductivity_scale=1e6)
        seg = segment(duration=600.0, width=0.2)
        q = 0.1 * 5e5 / (2 * math.pi * radius)
        tau = RHO * CP * radius / (2 * h)
        res = simulate(roll, uniform_header(h), [seg], time_step_s=2.0, axial_cell_m=0.1,
                       radial_cells=8, monitor_positions_m=(0.1,))
        mon = res['monitors'][0]
        for t, dr in zip(mon['time_s'], mon['radius_growth_m']):
            if t in (20.0, 100.0, 300.0, 600.0):
                expect = ALPHA * radius * q / h * (1 - math.exp(-t / tau))
                self.assertAlmostEqual(dr / expect, 1.0, delta=2e-4, msg=f't={t}')

    def test_lumped_limit_axial_decay_length_at_htc_step(self):
        # W_eff = pitch: exact tiling, weight 1; left half sprayed (h1), right half not (h2)
        pitch, h_bg, h_sp = 0.05, 500.0, 1500.0
        header = SprayHeader(nozzle_pitch_m=pitch, standoff_m=0.1,
                             spray_angle_rad=2 * math.atan(pitch / 0.2),
                             spray_mean_htc_w_m2k=h_sp, background_htc_w_m2k=h_bg)
        length, radius = 1.0, 0.2
        roll = RollThermalProperties(radius_m=radius, barrel_length_m=length,
                                     radial_conductivity_scale=1e6)
        levels = [1.0] * 10 + [0.0] * 10
        res = steady_state(roll, header, segment(width=length, levels=levels),
                           axial_cell_m=0.0025, radial_cells=6)
        self.assertTrue(res['solver']['converged'])
        q = 0.1 * 5e5 / (2 * math.pi * radius)
        h1, h2, z0 = h_bg + h_sp, h_bg, 0.5
        l1, l2 = math.sqrt(K * radius / (2 * h1)), math.sqrt(K * radius / (2 * h2))
        jump = q / h2 - q / h1
        # adiabatic ends: theta1 = A cosh(z/l1)/cosh(z0/l1), theta2 = B cosh((L-z)/l2)/...;
        # T and k*T' continuous at z0 -> A = jump*k2/(k1+k2), B = -A*k1/k2,
        # k1 = tanh(z0/l1)/l1, k2 = tanh((L-z0)/l2)/l2 (-> exponentials with l1/(l1+l2))
        k1, k2 = math.tanh(z0 / l1) / l1, math.tanh((length - z0) / l2) / l2
        amp_a = jump * k2 / (k1 + k2)
        amp_b = -amp_a * k1 / k2
        worst = 0.0
        for z, t in zip(res['z_m'], res['mean_temperature_k']):
            if z < z0:
                expect = TC + q / h1 + amp_a * math.cosh(z / l1) / math.cosh(z0 / l1)
            else:
                expect = (TC + q / h2 + amp_b * math.cosh((length - z) / l2)
                          / math.cosh((length - z0) / l2))
            worst = max(worst, abs(t - expect))
        self.assertLess(worst / jump, 5e-4)
        # the decay lengths themselves: e-folding of the deviation on each side
        dev = {round(z, 6): t - TC - (q / h1 if z < z0 else q / h2)
               for z, t in zip(res['z_m'], res['mean_temperature_k'])}
        ratio_left = dev[round(z0 - 0.00125 - 0.05, 6)] / dev[round(z0 - 0.00125, 6)]
        self.assertAlmostEqual(ratio_left, math.exp(-0.05 / l1), delta=2e-3)

    def test_pure_radial_transient_matches_bessel_series(self):
        h, radius = 1000.0, 0.2
        bi = h * radius / K
        a = K / (RHO * CP)
        roots = bessel_roots(bi, 6)
        for z in roots:   # roots really satisfy the characteristic equation
            self.assertLess(abs(z * bessel_j(1, z) - bi * bessel_j(0, z)), 1e-9)
        self.assertEqual(round(sum(4 * bi ** 2 / (z ** 2 * (z ** 2 + bi ** 2)) for z in roots)
                               + 0.0, 2), 1.0)
        roll = RollThermalProperties(radius_m=radius, barrel_length_m=0.1)
        q = 0.1 * 5e5 / (2 * math.pi * radius)
        times = (60.0, 300.0, 1000.0, 2500.0, 5000.0)
        res = simulate(roll, uniform_header(h), [segment(duration=5000.0, width=0.1)],
                       time_step_s=2.0, axial_cell_m=0.05, radial_cells=32,
                       record_times_s=times)
        deficits = {}
        for snap in res['snapshots']:
            t = snap['time_s']
            theta = snap['mean_temperature_k'][0] - TC - q / h
            series = sum(4 * bi ** 2 / (z ** 2 * (z ** 2 + bi ** 2))
                         * math.exp(-z ** 2 * a * t / radius ** 2) for z in roots)
            self.assertAlmostEqual(theta / (-q / h), series, delta=1.5e-3, msg=f't={t}')
            deficits[t] = -theta
        rate = math.log(deficits[2500.0] / deficits[5000.0]) / 2500.0
        # radial discretisation error 2.1e-3 at 32 cells (9.0e-3 at 16, 5.2e-4 at 64:
        # second order, checked in development)
        self.assertAlmostEqual(rate / (a * roots[0] ** 2 / radius ** 2), 1.0, delta=3e-3)
        # the lumped time constant would be much faster for Bi = 5
        self.assertLess(rate, 0.5 * 2 * h / (RHO * CP * radius))
        # second-order radial convergence: 16 cells are ~4x worse than 32
        coarse = simulate(roll, uniform_header(h), [segment(duration=300.0, width=0.1)],
                          time_step_s=2.0, axial_cell_m=0.05, radial_cells=16)
        fine = res['snapshots'][1]
        self.assertEqual(fine['time_s'], 300.0)
        exact = -q / h * sum(4 * bi ** 2 / (z ** 2 * (z ** 2 + bi ** 2))
                             * math.exp(-z ** 2 * a * 300.0 / radius ** 2) for z in roots)
        err_c = abs(coarse['mean_temperature_k'][0] - TC - q / h - exact)
        err_f = abs(fine['mean_temperature_k'][0] - TC - q / h - exact)
        self.assertGreater(err_c / err_f, 3.0)

    def test_long_transient_reaches_steady_solution(self):
        roll = RollThermalProperties(radius_m=0.15, barrel_length_m=0.5)
        header = double_overlap_header(pitch=0.05, h_spray=800.0)
        n = len(header.nozzle_positions(0.5))
        levels = [1.0] * n
        levels[3] = 0.2
        seg = segment(20000.0, levels, width=0.35, centre=0.3)
        kw = dict(axial_cell_m=0.02, radial_cells=8)
        ss = steady_state(roll, header, seg, **kw)
        tr = simulate(roll, header, [seg], time_step_s=200.0, **kw)
        self.assertIn('TIME_STEP_SUBDIVIDED_FOR_ADI_DAMPING', tr['flags'])
        self.assertLess(tr['solver']['internal_time_step_cap_s'], 200.0)
        for a, b in zip(ss['surface_temperature_k'], tr['surface_temperature_k']):
            self.assertAlmostEqual(a, b, delta=1e-4)
        self.assertAlmostEqual(ss['heat_in_w'], ss['heat_out_w'], delta=1e-7 * ss['heat_in_w'])

    def test_energy_conservation_to_round_off(self):
        roll = RollThermalProperties(radius_m=0.2, barrel_length_m=0.6)
        header = double_overlap_header()
        n = len(header.nozzle_positions(0.6))
        off = [1.0] * n
        off[n // 2] = 0.0
        segs = [segment(20.0, width=0.4, centre=0.25), segment(17.3, off, 0.4, 0.25),
                segment(31.0, [0.5] * n, 0.5, heat=3e5)]
        res = simulate(roll, header, segs, time_step_s=1.7, axial_cell_m=0.01,
                       radial_cells=10, record_times_s=(5.0, 21.1, 50.0))
        self.assertLess(abs(res['relative_energy_residual']), 1e-11)
        self.assertGreater(res['stored_j'], 0.0)
        self.assertAlmostEqual(res['stored_j'], res['heat_in_j'] - res['heat_out_j'],
                               delta=1e-9 * res['heat_in_j'])


class BlockedNozzleTests(unittest.TestCase):
    LENGTH, RADIUS, WIDTH = 0.8, 0.2, 0.6

    def setUp(self):
        self.roll = RollThermalProperties(radius_m=self.RADIUS, barrel_length_m=self.LENGTH)
        self.header = double_overlap_header()
        self.positions = self.header.nozzle_positions(self.LENGTH)
        self.index = min(range(len(self.positions)),
                         key=lambda i: abs(self.positions[i] - 0.55))
        self.levels = [1.0] * len(self.positions)
        self.levels[self.index] = 0.0

    def stripe_peak(self, dz, nr):
        base = steady_state(self.roll, self.header, segment(width=self.WIDTH),
                            axial_cell_m=dz, radial_cells=nr)
        blk = steady_state(self.roll, self.header, segment(levels=self.levels,
                                                           width=self.WIDTH),
                           axial_cell_m=dz, radial_cells=nr)
        return max(a - b for a, b in zip(blk['radius_growth_m'], base['radius_growth_m']))

    def test_grid_convergence(self):
        peaks = [self.stripe_peak(dz, nr) for dz, nr in ((0.02, 6), (0.01, 12), (0.005, 24))]
        self.assertLess(abs(peaks[2] - peaks[1]), abs(peaks[1] - peaks[0]))
        self.assertLess(abs(peaks[2] / peaks[1] - 1), 5e-3)

    def test_time_step_convergence(self):
        base = steady_state(self.roll, self.header, segment(width=self.WIDTH),
                            axial_cell_m=0.01, radial_cells=12)
        x = self.positions[self.index]
        growth = []
        for dt in (4.0, 2.0, 1.0):
            res = simulate(self.roll, self.header, [segment(30.0, self.levels, self.WIDTH)],
                           initial=base, time_step_s=dt, axial_cell_m=0.01, radial_cells=12,
                           monitor_positions_m=(x,))
            mon = res['monitors'][0]
            growth.append(mon['radius_growth_m'][-1] - mon['radius_growth_m'][0])
        self.assertLess(abs(growth[2] - growth[1]), abs(growth[1] - growth[0]))
        self.assertLess(abs(growth[2] / growth[1] - 1), 2e-3)

    def test_blocked_nozzle_hot_high_stripe_below_unsmoothed_estimate(self):
        dz = 0.005
        base = steady_state(self.roll, self.header, segment(width=self.WIDTH),
                            axial_cell_m=dz, radial_cells=16)
        blk = steady_state(self.roll, self.header, segment(levels=self.levels,
                                                           width=self.WIDTH),
                           axial_cell_m=dz, radial_cells=16)
        x = self.positions[self.index]
        ls = local_stripes(blk['z_m'], blk['radius_growth_m'], self.LENGTH / 2, self.WIDTH)
        hot = [s for s in ls['stripes'] if s['sign'] == 'HOT_HIGH' and
               s['start_m'] <= x <= s['end_m']]
        self.assertEqual(len(hot), 1)
        # the crown polynomial tilts the residual a little: allow ~1/4 of the footprint
        self.assertLess(abs(hot[0]['peak_position_m'] - x), 0.025)
        self.assertLess(abs(hot[0]['center_m'] - x), 0.025)
        diff = [a - b for a, b in zip(blk['radius_growth_m'], base['radius_growth_m'])]
        q = 0.1 * 5e5 / (2 * math.pi * self.RADIUS)
        unsmoothed = ALPHA * self.RADIUS * (q / (50.0 + 500.0) - q / (50.0 + 1000.0))
        self.assertGreater(max(diff), 0.1 * unsmoothed)
        self.assertLess(max(diff), 0.6 * unsmoothed)
        self.assertLess(hot[0]['peak_deviation_m'], unsmoothed)
        i_pk = max(range(len(diff)), key=lambda i: diff[i])
        self.assertLess(abs(blk['z_m'][i_pk] - x), 2 * dz)
        # the same stripe found on the difference to a healthy-header run
        hs = local_stripes(base['z_m'], diff, self.LENGTH / 2, self.WIDTH)
        self.assertEqual(hs['status'], 'LOCAL_STRIPES_PRESENT')
        top = max((s for s in hs['stripes'] if not s['touches_strip_edge']),
                  key=lambda s: s['peak_deviation_m'])
        self.assertEqual(top['sign'], 'HOT_HIGH')
        self.assertLess(abs(top['peak_position_m'] - x), 0.025)

    def test_zone_off_then_on_grows_then_decays_and_skin_effects(self):
        x = self.positions[self.index]
        ref = x - 0.2
        results = {}
        for scale in (1.0, 1e4):
            roll = RollThermalProperties(radius_m=self.RADIUS, barrel_length_m=self.LENGTH,
                                         radial_conductivity_scale=scale)
            base = steady_state(roll, self.header, segment(width=self.WIDTH),
                                axial_cell_m=0.01, radial_cells=12)
            res = simulate(roll, self.header, [segment(60.0, self.levels, self.WIDTH),
                                               segment(240.0, None, self.WIDTH)],
                           initial=base, time_step_s=1.0, axial_cell_m=0.01,
                           radial_cells=12, monitor_positions_m=(x, ref))
            m, r = res['monitors']
            t = m['time_s']
            stripe = [a - a0 - (b - b0) for a, b, a0, b0 in
                      zip(m['radius_growth_m'], r['radius_growth_m'],
                          [m['radius_growth_m'][0]] * len(t), [r['radius_growth_m'][0]] * len(t))]
            ts = [v - m['surface_temperature_k'][0] for v in m['surface_temperature_k']]
            results[scale] = (t, stripe, ts, base)
        t, s2d, ts2d, base = results[1.0]
        _, slump, tslump, base_lump = results[1e4]
        i60 = t.index(60.0)
        self.assertEqual(max(range(len(s2d)), key=lambda i: s2d[i]), i60)   # grows then decays
        self.assertLess(s2d[-1], 0.5 * s2d[i60])
        self.assertGreater(s2d[-1], 0.0)
        # early growth: the flux-step rate 2*alpha*dh*(Ts - Tc)/(rho*c) (dh = 500 W/m2K at
        # the blocked nozzle), the SAME law in the 2-D and lumped models; the 2-D skin heats
        # within seconds and loses a few per cent of it, so the 2-D stripe starts no faster.
        def rate(b):
            j = min(range(len(b['z_m'])), key=lambda i: abs(b['z_m'][i] - x))
            return 2 * ALPHA * 500.0 * (b['surface_temperature_k'][j] - TC) / (RHO * CP)
        i2 = t.index(2.0)
        self.assertAlmostEqual(slump[i2] / (2.0 * rate(base_lump)), 1.0, delta=0.01)
        self.assertAlmostEqual(s2d[i2] / (2.0 * rate(base)), 1.0, delta=0.08)
        self.assertLess(s2d[i2], slump[i2])
        # skin response: the 2-D surface temperature reacts much faster than the lumped one
        i10 = t.index(10.0)
        self.assertGreater(ts2d[i10], 5 * tslump[i10])
        # and the stripe from a short switch-off decays faster after re-cooling
        def half_decay(series):
            pk = series[i60]
            return next(t[i] for i in range(i60, len(t)) if series[i] <= pk / 2) - 60.0
        # (measured: 2-D ~79 s, lumped ~113 s, lumped tau 351 s: faster, but minutes, not
        # the ~20 s of the plant identification)
        tau_lumped = RHO * CP * self.RADIUS / (2 * 1050.0)
        self.assertLess(half_decay(s2d), 0.8 * half_decay(slump))
        self.assertLess(half_decay(s2d), 0.3 * tau_lumped)
        self.assertGreater(half_decay(s2d), 30.0)


class HeaderAndExpansionTests(unittest.TestCase):
    def test_healthy_header_weight_averages_to_one(self):
        pitch = 0.05
        for ratio in (1.0, 1.5, 2.0, 2.7):
            header = SprayHeader(nozzle_pitch_m=pitch, standoff_m=0.2,
                                 spray_angle_rad=2 * math.atan(ratio * pitch / 0.4),
                                 spray_mean_htc_w_m2k=1000.0)
            self.assertAlmostEqual(header.effective_footprint_width_m, ratio * pitch)
            dz = 0.001
            z = [(j + 0.5) * dz for j in range(1000)]
            w = header.weight_profile(z, None)
            interior = [v for zz, v in zip(z, w) if 0.3 <= zz < 0.7]   # 8 whole pitches
            self.assertAlmostEqual(sum(interior) / len(interior), 1.0, delta=1e-9)
            if ratio in (1.0, 2.0):
                self.assertAlmostEqual(min(interior), 1.0, delta=1e-12)
                self.assertAlmostEqual(max(interior), 1.0, delta=1e-12)
        # default layout matches band_signatures.spray_coverage
        header = double_overlap_header()
        pos = header.nozzle_positions(2.0)
        self.assertEqual(len(pos), 38)
        self.assertAlmostEqual(pos[0], (2.0 - 37 * 0.052) / 2)

    def test_offset_angle_narrows_footprint(self):
        header = SprayHeader(nozzle_pitch_m=0.05, standoff_m=0.2, spray_angle_rad=0.5,
                             offset_angle_rad=0.3, spray_mean_htc_w_m2k=1.0)
        self.assertAlmostEqual(header.effective_footprint_width_m,
                               2 * 0.2 * math.tan(0.25) * math.cos(0.3))

    def test_expansion_constraints_differ_by_one_plus_nu(self):
        roll = RollThermalProperties(radius_m=0.2, barrel_length_m=0.4)
        header = double_overlap_header()
        kw = dict(axial_cell_m=0.02, radial_cells=8)
        free = steady_state(roll, header, segment(width=0.3), **kw)
        plane = steady_state(roll, header, segment(width=0.3),
                             expansion_constraint='plane_strain', **kw)
        for a, b in zip(free['radius_growth_m'], plane['radius_growth_m']):
            self.assertAlmostEqual(b, (1 + NU) * a, delta=1e-15)
        self.assertAlmostEqual(plane['thermal_crown_m'], (1 + NU) * free['thermal_crown_m'],
                               delta=1e-15)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.roll = RollThermalProperties(radius_m=0.2, barrel_length_m=0.4)
        self.header = double_overlap_header()

    def test_validation_errors(self):
        bad_rolls = [dict(radius_m=0.0, barrel_length_m=1.0),
                     dict(radius_m=True, barrel_length_m=1.0),
                     dict(radius_m=0.2, barrel_length_m=float('nan')),
                     dict(radius_m=0.2, barrel_length_m=1.0, poisson_ratio=0.5),
                     dict(radius_m=0.2, barrel_length_m=1.0, radial_conductivity_scale=0.0)]
        for kw in bad_rolls:
            with self.assertRaises(ValueError):
                RollThermalProperties(**kw).validate()
        with self.assertRaises(ValueError):
            SprayHeader(nozzle_pitch_m=0.05, standoff_m=0.1, spray_angle_rad=0.5,
                        spray_mean_htc_w_m2k=-1.0).validate()
        with self.assertRaises(ValueError):
            SprayHeader(nozzle_pitch_m=0.05, standoff_m=0.1, spray_angle_rad=4.0,
                        spray_mean_htc_w_m2k=1.0).validate()
        with self.assertRaises(ValueError):
            segment(levels=[1.0, 1.5]).validate()
        with self.assertRaises(ValueError):
            ThermalSegment(duration_s=0.0, bite_heat_per_width_w_m=1.0,
                           roll_heat_fraction_per_roll=0.1, strip_width_m=1.0,
                           coolant_temperature_k=TC).validate()
        with self.assertRaises(ValueError):    # wrong number of nozzle levels
            steady_state(self.roll, self.header, segment(levels=[1.0] * 3, width=0.3),
                         axial_cell_m=0.02, radial_cells=6)
        with self.assertRaises(ValueError):    # strip off the barrel
            steady_state(self.roll, self.header, segment(width=0.3, centre=0.3),
                         axial_cell_m=0.02, radial_cells=6)
        with self.assertRaises(ValueError):
            steady_state(self.roll, self.header, segment(width=0.3),
                         expansion_constraint='free')
        with self.assertRaises(ValueError):
            steady_state(self.roll, self.header, segment(width=0.3), radial_cells=2)
        with self.assertRaises(ValueError):
            simulate(self.roll, self.header, [], axial_cell_m=0.02, radial_cells=6)
        with self.assertRaises(ValueError):
            simulate(self.roll, self.header, [segment(width=0.3)], initial='hot')
        with self.assertRaises(ValueError):
            simulate(self.roll, self.header, [segment(width=0.3)], record_times_s=(5.0,),
                     axial_cell_m=0.02, radial_cells=6)
        good = steady_state(self.roll, self.header, segment(width=0.3), axial_cell_m=0.02,
                            radial_cells=6)
        with self.assertRaises(ValueError):    # grid mismatch on restart
            simulate(self.roll, self.header, [segment(width=0.3)], initial=good,
                     axial_cell_m=0.01, radial_cells=6)
        with self.assertRaises(ValueError):
            local_stripes([0.0, 1.0], [0.0], 0.5, 1.0)
        with self.assertRaises(ValueError):
            local_stripes([0.0, 0.1, 0.2], [0.0] * 3, 0.1, 0.2, smooth_order=4)

    def test_json_restart_and_result_keys(self):
        kw = dict(axial_cell_m=0.02, radial_cells=6)
        base = steady_state(self.roll, self.header, segment(width=0.3), **kw)
        dumps(base)
        for key in ('status', 'flags', 'limitations', 'z_m', 'surface_temperature_k',
                    'mean_temperature_k', 'radius_growth_m', 'htc_w_m2k', 'heat_flux_w_m2',
                    'thermal_crown_m', 'heat_in_w', 'heat_out_w', 'residual_w', 'field',
                    'solver', 'threshold_basis', 'sources'):
            self.assertIn(key, base)
        self.assertTrue(base['status'].startswith('UNVALIDATED'))
        res = simulate(self.roll, self.header, [segment(30.0, width=0.3)], initial=base,
                       record_times_s=(0.0, 10.0, 30.0), monitor_positions_m=(0.2,), **kw)
        text = dumps(res)
        self.assertNotIn('NaN', text)
        for key in ('stored_j', 'heat_in_j', 'heat_out_j', 'residual_j', 'snapshots',
                    'monitors', 'field', 'solver', 'end_time_s'):
            self.assertIn(key, res)
        self.assertEqual([s['time_s'] for s in res['snapshots']], [0.0, 10.0, 30.0])
        for a, b in zip(res['radius_growth_m'], base['radius_growth_m']):
            # restart from steady stays steady; the backward-Euler start-up step's O(dt)
            # splitting error moves it by ~2e-5 K (5e-11 m) on this coarse grid
            self.assertAlmostEqual(a, b, delta=1e-10)
        mon = res['monitors'][0]
        for key in ('time_s', 'radius_growth_m', 'surface_temperature_k',
                    'time_to_half_peak_s'):
            self.assertIn(key, mon)
        ls = local_stripes(base['z_m'], base['radius_growth_m'], 0.2, 0.3, smooth_order=2)
        dumps(ls)

    def test_local_stripes_on_synthetic_profile(self):
        z = [(j + 0.5) * 0.005 for j in range(400)]
        bump = lambda x, c, s: math.exp(-0.5 * ((x - c) / s) ** 2)  # noqa: E731
        y = [40e-6 * (1 - ((x - 1.0) / 0.9) ** 2) + 2e-6 * bump(x, 0.7, 0.02)
             - 1e-6 * bump(x, 1.3, 0.02) for x in z]
        res = local_stripes(z, y, 1.0, 1.5, threshold_m=2e-7)
        interior = [s for s in res['stripes'] if not s['touches_strip_edge']]
        hot = [s for s in interior if s['sign'] == 'HOT_HIGH' and s['peak_deviation_m'] > 1e-6]
        cold = [s for s in interior if s['sign'] == 'COLD_LOW' and s['peak_deviation_m'] < -5e-7]
        self.assertEqual(len(hot), 1)
        self.assertEqual(len(cold), 1)
        self.assertAlmostEqual(hot[0]['center_m'], 0.7, delta=0.005)
        self.assertAlmostEqual(cold[0]['center_m'], 1.3, delta=0.005)
        self.assertAlmostEqual(hot[0]['width_at_half_peak_m'], 2.3548 * 0.02, delta=0.006)
        smooth = [40e-6 * (1 - ((x - 1.0) / 0.9) ** 2) for x in z]
        flat = local_stripes(z, smooth, 1.0, 1.5)
        self.assertEqual(flat['status'], 'NO_LOCAL_STRIPES_ABOVE_THRESHOLD')
        self.assertLess(flat['max_abs_deviation_m'], 1e-15)

    def test_history_metrics(self):
        m = history_metrics([0.0, 1.0, 2.0, 3.0], [1.0, 2.0, 5.0, 3.0])
        self.assertEqual(m['peak_change'], 4.0)
        self.assertEqual(m['time_of_peak_s'], 2.0)
        self.assertAlmostEqual(m['time_to_half_peak_s'], 1.0 + 1.0 / 3.0)


class PerformanceTests(unittest.TestCase):
    def test_performance_guard_default_grid_2m_barrel(self):
        roll = RollThermalProperties(radius_m=0.2, barrel_length_m=2.0)
        header = double_overlap_header()
        t0 = time.perf_counter()
        base = steady_state(roll, header, segment())
        t_steady = time.perf_counter() - t0
        self.assertTrue(base['solver']['converged'])
        t0 = time.perf_counter()
        simulate(roll, header, [segment(300.0)], initial=base, time_step_s=1.0)
        t_transient = time.perf_counter() - t0
        self.assertLess(t_steady, 15.0)
        self.assertLess(t_transient, 20.0)


if __name__ == '__main__':
    unittest.main()
