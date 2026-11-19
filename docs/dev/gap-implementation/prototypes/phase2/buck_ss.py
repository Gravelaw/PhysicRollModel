from buck import *
def gauss_profile(z, centre, fwhm, peak_i):
    """mean-free elongation in I-units, loose Gaussian band of the given peak (before mean removal)."""
    g = [peak_i*math.exp(-4*math.log(2)*((x - centre)/fwhm)**2) for x in z]
    W = z[-1] - z[0]
    mean = sum(0.5*(g[i] + g[i+1])*(z[i+1] - z[i]) for i in range(len(z) - 1))/W
    return [v - mean for v in g]
def width_at(z, f, level):
    idx = [i for i, v in enumerate(f) if abs(v) >= level]
    return z[idx[-1]] - z[idx[0]]
def run(E, nu, t, W, fwhm, sT, n=200, label=''):
    z = [W*i/n for i in range(n + 1)]
    iu = gauss_profile(z, W/2, fwhm, 1.0)
    sres = [-E*1e-5*v for v in iu]          # per I-unit of peak
    st = Strip(z, sres, t, E, nu, sT, ('free', 'free'))
    t0 = time.perf_counter()
    r = critical(st, math.pi/(2*W), math.pi/(4*W/n), coarse=14, refine=10)
    dt = time.perf_counter() - t0
    f = r['f']
    return {'fwhm_mm': fwhm*1e3, 'tension_mpa': sT/1e6, 'critical_peak_i_units': round(r['lambda'], 3),
            'half_wave_mm': round(r['half_wavelength_m']*1e3, 1), 'mode_width_10pct_mm': round(width_at(z, f, 0.1)*1e3, 1),
            'mode_width_50pct_mm': round(width_at(z, f, 0.5)*1e3, 1), 'time_s': round(dt, 2)}
if __name__ == '__main__':
    print('SS-V2: steel 0.5 x 1000 mm (E 210 GPa, nu 0.3 assumed); measured half wave 60 mm, buckle width 150 mm, waves at 7.5-8 I-units, none below 6')
    for fwhm in (0.05, 0.075, 0.1, 0.15):
        for sT in (0.0, 10e6, 30e6, 60e6, 100e6):
            print('  ', run(210e9, 0.3, 0.5e-3, 1.0, fwhm, sT))
    print('SS-V3: aluminium 0.3 x 270 mm; buckle width 105 mm, wavelength about 75 mm (half 37.5)')
    for fwhm in (0.03, 0.05, 0.07):
        for sT in (0.0, 5e6, 15e6, 30e6):
            print('  ', run(70e9, 0.33, 0.3e-3, 0.27, fwhm, sT, n=108))
