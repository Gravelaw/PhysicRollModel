from common import *
case, art = load('lengthwise_bands')
th = thermal(case, art)
t0=time.perf_counter(); healthy = th.steady([1.0]*th.count); t1=time.perf_counter()
actual = th.steady(th.levels); t2=time.perf_counter()
print('steady', t1-t0, t2-t1, 'iters', healthy['solver']['iterations'], actual['solver']['iterations'], 'nz', len(actual['z_m']))
# one simulate of 600 s at 1 s
seg = th.segment(th.levels, 600.0)
t0=time.perf_counter(); sim = rt.simulate(th.roll, th.header, [seg], initial=actual, time_step_s=1.0, **th.kw); t1=time.perf_counter()
print('simulate 600 steps', t1-t0, sim['solver']['steps'])
# repeated short simulate of 2 s each (300 calls)
t0=time.perf_counter(); cur = actual
for i in range(50):
    cur = rt.simulate(th.roll, th.header, [th.segment(th.levels, 2.0)], initial=cur, time_step_s=1.0, **th.kw)
t1=time.perf_counter(); print('50 x simulate(2 s)', t1-t0)
sp = shape_params(case, art)
z = actual['z_m']; dev=[a-b for a,b in zip(actual['radius_growth_m'], healthy['radius_growth_m'])]
t0=time.perf_counter(); lv = bw.shape_levels(z, dev, sp); t1=time.perf_counter()
print('shape_levels', t1-t0, lv['feedback_peak_i_units'], lv['linear_feedback_peak_i_units'])
t0=time.perf_counter()
tr = ss.transfer_radius_profile(lv['z_m'], lv['local_radius_deviation_m'], bite_half_length_m=sp['bite_half_length_m'], strip_stiffness_per_width_pa=sp['strip_stiffness_per_width_pa'], roll_radius_m=sp['roll_radius_m'], n_rolls=1, exit_tension_force_sensitivity_per_width_m=sp['exit_tension_force_sensitivity_per_width_m'], exit_thickness_m=sp['exit_thickness_m'], strip_youngs_modulus_pa=7e10, xi=1.0)
t1=time.perf_counter(); print('transfer_radius_profile', t1-t0, len(lv['z_m']))
