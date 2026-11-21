"""Published asperity-contact and flow-factor fits, transcribed and tested (SI, stdlib only).

Status: ``PUBLISHED_FITS_TRANSCRIBED_NOT_ASSEMBLED_INTO_A_MODEL``. NOTHING in the engine
imports this module (SPEC18 package 6). It holds checked transcriptions so that a later inlet
analysis of the mixed-lubrication type can start from them. Sources: the two open theses that
reproduce the fits [E5 FT = Boemer 2020, sec. 4.7.1, 4.8.1.3, equations read on page images;
E6 FT = Sutcliffe 1989, ch. 3]; the original papers (Wilson & Sheu 1988; Korzekwa, Dawson &
Wilson 1992; Patir & Cheng 1978/79; Wilson & Marsault 1998) were not read [CIT]. Transcribed in
docs/research/band-screening-2026-11/phase1-equations.md, sections 2.1 and 2.2.

Why they are NOT assembled (SPEC18 package 6, planner's checks): the height-distribution
relation (E5 (4.18), (4.20)) gives 0.905 / 0.788 / 0.689 / 0.495 of the source table's own mean
film at A = 0.28 / 0.53 / 0.69 / 0.88, so the thesis's surface model is not the one transcribed;
and the four crushing laws agree only near A = 0.5, p_bar/2k = 1, differing by up to two orders
of magnitude elsewhere (benchmark BT-G3-CRUSHING-LAWS). A model built from them would have five
published points to meet and no way to decide which transcription is at fault. The crushing law
to use when an inlet analysis is built later: the regression of Korzekwa's results (E5
(4.97)-(4.100)), the one the foil papers use [E4 EX, E7 FT], defined for all 0 < A < 1.

Variables: A real contact-area ratio; H_a = (p_a - p_l)/tau_Y non-dimensional hardness;
E_p = D_x^p*l/(v_a + v_b) non-dimensional plastic strain rate [E5 (4.89), (4.90)];
W = (v_a - v_v)/(c*eps_dot) crushing rate [E6 p.36]; W = 1/E_p; p_bar/2k = A*H_a/2
[derived from E6 eq. 4.12]. R_q combined r.m.s. roughness; h separation of the mean lines;
gamma Peklenik parameter (> 1 longitudinal lay).

No function here is called "Sutcliffe (1988)": the thesis form (c) and the Marsault form (b)
agree only at p_bar/2k = 1 and the 1988 paper, which would decide, was not read.
"""
import math

STATUS = 'PUBLISHED_FITS_TRANSCRIBED_NOT_ASSEMBLED_INTO_A_MODEL'


def _num(name, value, lo=None, hi=None, open_lo=False, open_hi=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    v = float(value)
    if lo is not None and (v <= lo if open_lo else v < lo):
        raise ValueError(f'{name} out of range')
    if hi is not None and (v >= hi if open_hi else v > hi):
        raise ValueError(f'{name} out of range')
    return v


def _area(a):
    return _num('contact_area_ratio', a, 0.0, 1.0, open_lo=True, open_hi=True)


def christensen_contact_ratio(h_over_rq):
    """Contact-area ratio of the Christensen (quasi-Gaussian) height density [E5 FT (4.18)]:
    ``A = (16 - 35H + 35H^3 - 21H^5 + 5H^7)/32``, ``H = h/(3 R_q)``; 1 for H <= -1, 0 for
    H >= 1."""
    hh = _num('h_over_rq', h_over_rq) / 3.0
    if hh <= -1:
        return 1.0
    if hh >= 1:
        return 0.0
    return (16 - 35 * hh + 35 * hh ** 3 - 21 * hh ** 5 + 5 * hh ** 7) / 32


def christensen_mean_film_over_rq(h_over_rq):
    """Mean film h_t/R_q of the Christensen density [E5 FT (4.20)]:
    ``h_t = (3 R_q/256)(35 + 128H + 140H^2 - 70H^4 + 28H^6 - 5H^8)``; h_t = h for H >= 1, 0 for
    H <= -1."""
    h = _num('h_over_rq', h_over_rq)
    hh = h / 3.0
    if hh <= -1:
        return 0.0
    if hh >= 1:
        return h
    return 3 * (35 + 128 * hh + 140 * hh ** 2 - 70 * hh ** 4 + 28 * hh ** 6 - 5 * hh ** 8) / 256


def crushing_rate_thesis(contact_area_ratio, p_over_2k):
    """Crushing rate of the thesis fit [E6 FT eq. (3.20)]: ``W = 3.81*(p_bar/2k)^2 - 4.38*A``,
    clipped to [0.05, 2.5] as the thesis states ("most appropriate around A = 0.5 with
    p_bar/2k < 1")."""
    a = _area(contact_area_ratio)
    p = _num('p_over_2k', p_over_2k, 0.0, 10.0)
    return min(2.5, max(0.05, 3.81 * p * p - 4.38 * a))


def plastic_strain_rate_marsault(contact_area_ratio, hardness):
    """E_p of the form Marsault's thesis gives [E5 FT (4.96)]:
    ``E_p = 4/(H_a^2 A^2 (3.81 - 4.38 A))``; degenerates for A -> 0 and A > 0.87 (E5)."""
    a = _area(contact_area_ratio)
    h = _num('hardness', hardness, 0.0, 100.0, open_lo=True)
    bracket = 3.81 - 4.38 * a
    if bracket <= 0:
        raise ValueError('the Marsault form is undefined for A >= 0.87 (bracket <= 0)')
    return 4 / (h * h * a * a * bracket)


def plastic_strain_rate_wilson_sheu(contact_area_ratio, hardness):
    """E_p of Wilson & Sheu's fit [E5 FT (4.92)]:
    ``E_p = (2/H_a - f2)/f1``, ``f1 = 0.515 + 0.345A - 0.860A^2``,
    ``f2 = 1/(2.571 - A - A ln(1 - A))``; reported as poor below A = 0.3 (E5)."""
    a = _area(contact_area_ratio)
    h = _num('hardness', hardness, 0.0, 100.0, open_lo=True)
    f1 = 0.515 + 0.345 * a - 0.860 * a * a
    f2 = 1 / (2.571 - a - a * math.log(1 - a))
    return (2 / h - f2) / f1


def plastic_strain_rate_korzekwa(contact_area_ratio, hardness):
    """E_p of the regression of Korzekwa et al.'s finite-element results [E5 FT (4.97)-(4.100)]:
    ``E_p = 1/(A(1 - A)(c1 + c2 A + c3 A^2))``, ``D = H_a/2``,
    ``c1 = 5.1206D - 4.5258D^2 + 3.5599D^3``, ``c2 = -9.5761D + 11.3854D^2 - 8.6069D^3``,
    ``c3 = 8.3193D - 11.7954D^2 + 7.6475D^3``. The law to use for a later inlet analysis."""
    a = _area(contact_area_ratio)
    d = _num('hardness', hardness, 0.0, 100.0, open_lo=True) / 2
    c1 = 5.1206 * d - 4.5258 * d ** 2 + 3.5599 * d ** 3
    c2 = -9.5761 * d + 11.3854 * d ** 2 - 8.6069 * d ** 3
    c3 = 8.3193 * d - 11.7954 * d ** 2 + 7.6475 * d ** 3
    return 1 / (a * (1 - a) * (c1 + c2 * a + c3 * a * a))


def hardness_wilson_sheu_no_bulk(contact_area_ratio):
    """H_a without bulk deformation [E5 FT (4.94)]: ``2*(2.571 - A - A ln(1 - A))``
    (2 + pi at A -> 0)."""
    a = _num('contact_area_ratio', contact_area_ratio, 0.0, 1.0, open_hi=True)
    return 2 * (2.571 - a - (a * math.log(1 - a) if a > 0 else 0.0))


def crushing_rate_from_strain_rate(plastic_strain_rate):
    """W = 1/E_p [E8 EX, consistent with the two definitions]."""
    return 1 / _num('plastic_strain_rate', plastic_strain_rate, 0.0, None, open_lo=True)


def hardness_from_mean_pressure(contact_area_ratio, p_over_2k):
    """H_a = 2*(p_bar/2k)/A, from p_bar/2k = A*H_a/2 [derived from E6 eq. 4.12]."""
    return 2 * _num('p_over_2k', p_over_2k, 0.0, 10.0, open_lo=True) / _area(contact_area_ratio)


def pressure_flow_factor(h_over_rq, gamma):
    """Pressure flow factor phi_x of a Gaussian surface, Patir & Cheng as fitted by Marsault
    [E5 FT (4.160)]: gamma <= 1: ``1 - C exp(-r h/R_q)``, ``C = 0.89679 - 0.26591 ln(gamma)``,
    ``r = 0.43006 - 0.10828 gamma + 0.23821 gamma^2``; gamma > 1: ``1 + C (h/R_q)^-1.5``,
    ``C = -0.10667 + 0.10750 gamma``."""
    h = _num('h_over_rq', h_over_rq, 0.0, 1e3, open_lo=True)
    g = _num('gamma', gamma, 0.0, 1e3, open_lo=True)
    if g <= 1:
        c = 0.89679 - 0.26591 * math.log(g)
        r = 0.43006 - 0.10828 * g + 0.23821 * g * g
        return 1 - c * math.exp(-r * h)
    return 1 + (-0.10667 + 0.10750 * g) * h ** -1.5


def percolation_film_over_rq(gamma):
    """Percolation threshold h_tc/R_q of the Wilson-Marsault flow factors [E5 FT (4.171)]:
    ``3*(1 - 1/(0.47476/gamma + 1)^0.25007)`` (0.0383 at gamma 9; E4 EX quotes 0.038)."""
    g = _num('gamma', gamma, 0.0, 1e3, open_lo=True)
    return 3 * (1 - 1 / (0.47476 / g + 1) ** 0.25007)
