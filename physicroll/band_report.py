"""Deterministic, self-contained HTML report of a band root-cause screening result.

Every number shown is read from the ``diagnose`` result dict (display-unit conversions such
as m -> mm are labelled). No JavaScript, no external assets; charts are inline SVG with axis
labels, units, a key, and dash patterns as well as colours. All text is escaped.

A ``physicroll.band_case.v1`` result renders the phase-1 (transverse-band) page unchanged. A
v2 result adds the family statement, the lengthwise sections (across the width, short-lived
bands, how the result changes with gauge), process and dynamics sections and a family column in the
hypothesis table; when the observed or leading family is lengthwise those lead the page and
the chatter sections follow as supporting detail. Sections in a NOT_SUPPLIED / FAILED /
NOT_ASSESSABLE state render one line instead of charts. Optional result keys (the
after-tension-release states and thresholds) are used when present and omitted when absent.
"""
from html import escape
import math

COLOURS = ('#0b62a4', '#c2410c', '#15803d', '#7e22ce', '#a16207', '#0e7490', '#374151')
DASHES = ('', '7 4', '2 3', '9 3 2 3', '4 2', '1 2', '12 4')
W, H = 760, 340
ML, MR, MB = 70, 24, 52


def _e(text):
    return escape(str(text), quote=True)


def _n(value, digits=4, unit=''):
    if value is None:
        return 'n/a'
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, int):
        text = str(value)
    else:
        text = f'{value:.{digits}g}'
    return text + (f' {unit}' if unit else '')


def _mm(value, digits=4):
    return 'n/a' if value is None else f'{value * 1e3:.{digits}g} mm'


def _val(value):
    """Compact human rendering of nested model-prediction values."""
    if isinstance(value, dict):
        return '; '.join(f'{k}: {_val(v)}' for k, v in value.items())
    if isinstance(value, list):
        return ' | '.join(_val(v) for v in value) if value else 'none'
    if isinstance(value, float):
        return _n(value)
    return 'n/a' if value is None else str(value)


# ------------------------------------------------------------------------------ svg core
class _Axis:
    def __init__(self, lo, hi, p0, p1, log=False):
        if log:
            lo, hi = max(lo, 1e-300), max(hi, 1e-300)
        if hi <= lo:
            hi = lo * 1.1 + 1 if not log else lo * 10
        self.lo, self.hi, self.p0, self.p1, self.log = lo, hi, p0, p1, log

    def __call__(self, v):
        if self.log:
            v = max(v, self.lo)
            t = (math.log10(v) - math.log10(self.lo)) / (math.log10(self.hi) - math.log10(self.lo))
        else:
            t = (v - self.lo) / (self.hi - self.lo)
        return self.p0 + t * (self.p1 - self.p0)

    def ticks(self):
        if self.log:
            out = []
            e0, e1 = math.floor(math.log10(self.lo)), math.ceil(math.log10(self.hi))
            for e in range(e0, e1 + 1):
                for m in (1, 2, 5):
                    v = m * 10 ** e
                    if self.lo * (1 - 1e-9) <= v <= self.hi * (1 + 1e-9):
                        out.append(v)
            if len(out) > 10:
                out = [v for v in out if abs(math.log10(v) - round(math.log10(v))) < 1e-9]
            return out
        span = self.hi - self.lo
        raw = span / 6
        mag = 10 ** math.floor(math.log10(raw))
        step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
        start = math.ceil(self.lo / step - 1e-9) * step
        out, v = [], start
        while v <= self.hi + 1e-9 * span:
            out.append(0.0 if abs(v) < 1e-12 * span else v)
            v += step
        return out


def _tick_label(v):
    if v == 0:
        return '0'
    a = abs(v)
    if 1e-3 <= a < 1e5:
        return f'{v:.6g}'
    return f'{v:.0e}'.replace('e-0', 'e-').replace('e+0', 'e')


class _Chart:
    """One SVG chart: a key (legend) row block on top, then the plot frame below it."""

    def __init__(self, title, key, height=H):
        self.title, self.h = title, height
        self.key_parts, rows = self._key(key)
        self.mt = 14 + 15 * rows + 8          # plot top below the key
        self.inner = []

    @staticmethod
    def _key(entries):
        parts, x, y, rows = [], ML, 16, 1
        for label, colour, dash, kind in entries:
            width = 34 + 6.3 * len(label)
            if x + width > W - MR and x > ML:
                x, y, rows = ML, y + 15, rows + 1
            if kind == 'dot':
                parts.append(f'<circle cx="{x + 11}" cy="{y - 4}" r="4.5" fill="{colour}" '
                             'stroke="#111" stroke-width="0.6"/>')
            elif kind == 'square':
                parts.append(f'<rect x="{x + 6}" y="{y - 9}" width="10" height="10" '
                             f'fill="none" stroke="{colour}" stroke-width="2.2"/>')
            elif kind == 'block':
                parts.append(f'<rect x="{x}" y="{y - 9}" width="22" height="10" '
                             f'fill="{colour}"/>')
            else:
                parts.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 22}" y2="{y - 4}" '
                             f'stroke="{colour}" stroke-width="2.4" stroke-dasharray="{dash}"/>')
            parts.append(f'<text x="{x + 27}" y="{y}" class="key">{_e(label)}</text>')
            x += width
        return parts, rows

    def axes(self, x, y, xlabel, ylabel):
        self.x, self.y = x, y
        mt, h = self.mt, self.h
        p = [f'<rect x="{ML}" y="{mt}" width="{W - ML - MR}" height="{h - mt - MB}" '
             'fill="#fbfcfe" stroke="#9aa5b8"/>']
        for v in x.ticks():
            px = x(v)
            p.append(f'<line x1="{px:.1f}" y1="{mt}" x2="{px:.1f}" y2="{h - MB}" '
                     'stroke="#e3e7ef"/>')
            p.append(f'<text x="{px:.1f}" y="{h - MB + 16}" text-anchor="middle" '
                     f'class="tick">{_e(_tick_label(v))}</text>')
        for v in y.ticks():
            py = y(v)
            p.append(f'<line x1="{ML}" y1="{py:.1f}" x2="{W - MR}" y2="{py:.1f}" '
                     'stroke="#e3e7ef"/>')
            p.append(f'<text x="{ML - 6}" y="{py + 4:.1f}" text-anchor="end" '
                     f'class="tick">{_e(_tick_label(v))}</text>')
        p.append(f'<text x="{(ML + W - MR) / 2:.1f}" y="{h - 12}" text-anchor="middle" '
                 f'class="axis">{_e(xlabel)}</text>')
        cy = (mt + h - MB) / 2
        p.append(f'<text x="16" y="{cy:.1f}" text-anchor="middle" '
                 f'transform="rotate(-90 16 {cy:.1f})" class="axis">{_e(ylabel)}</text>')
        self.frame = p

    def poly(self, points, colour, dash, width=2.0):
        pts = ' '.join(f'{self.x(a):.1f},{self.y(b):.1f}' for a, b in points)
        self.inner.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                          f'stroke-width="{width}" stroke-dasharray="{dash}" '
                          'stroke-linejoin="round"/>')

    def vline(self, v, colour, dash, label, y_text, anchor='start'):
        px = self.x(v)
        dx = 4 if anchor == 'start' else -4
        self.inner.append(f'<line x1="{px:.1f}" y1="{self.mt}" x2="{px:.1f}" '
                          f'y2="{self.h - MB}" stroke="{colour}" stroke-width="1.6" '
                          f'stroke-dasharray="{dash}"/>')
        self.inner.append(f'<text x="{px + dx:.1f}" y="{y_text:.1f}" text-anchor="{anchor}" '
                          f'class="lab" fill="{colour}">{_e(label)}</text>')

    def render(self, clip_name):
        cid = f'clip-{clip_name}'
        return ''.join(
            [f'<svg viewBox="0 0 {W} {self.h}" role="img" aria-label="{_e(self.title)}" '
             f'xmlns="http://www.w3.org/2000/svg" class="chart"><title>{_e(self.title)}</title>']
            + self.frame
            + [f'<clipPath id="{cid}"><rect x="{ML}" y="{self.mt}" width="{W - ML - MR}" '
               f'height="{self.h - self.mt - MB}"/></clipPath>',
               f'<g clip-path="url(#{cid})">'] + self.inner + ['</g>']
            + self.key_parts + ['</svg>'])


# ------------------------------------------------------------------------------ charts
def _strip_map(result):
    sm = result['strip_map']
    length = sm['strip_length_m']
    pitch, obs = sm['predicted_pitch_m'], sm['observed_pitch_m']
    key = []
    if pitch:
        key.append((f'predicted bands, pitch {_mm(pitch)} ({sm["predicted_pitch_basis"]})',
                    COLOURS[0], '', 'line'))
    if obs:
        key.append((f'observed pitch {_mm(obs)} at {_n(sm["observed_at_exit_speed_m_s"])} m/s'
                    ' (ticks below the strip)', COLOURS[1], '', 'line'))
    if not key:
        key.append(('no vibration-type hypothesis with positive score and no observed pitch',
                    '#6b7280', '2 3', 'line'))
    key_parts, rows = _Chart._key(key)
    top = 14 + 15 * rows + 10
    bot = top + 62
    height = bot + 56
    x0, x1 = ML, W - MR
    sx = _Axis(0.0, length, x0, x1)
    parts = [f'<svg viewBox="0 0 {W} {height}" role="img" xmlns="http://www.w3.org/2000/svg"'
             ' class="chart" aria-label="strip map"><title>Predicted band positions along '
             'the strip</title>',
             f'<rect x="{x0}" y="{top}" width="{x1 - x0}" height="{bot - top}" fill="#e9edf3" '
             'stroke="#6b7280"/>']
    for value, colour, y_a, y_b in ((pitch, COLOURS[0], top, bot),
                                    (obs, COLOURS[1], bot + 2, bot + 14)):
        if not value:
            continue
        k, v = 0, 0.0
        while v <= length + 1e-12 and k < 2000:
            parts.append(f'<line x1="{sx(v):.1f}" y1="{y_a}" x2="{sx(v):.1f}" y2="{y_b}" '
                         f'stroke="{colour}" stroke-width="2"/>')
            k += 1
            v = k * value
    for v in sx.ticks():
        parts.append(f'<text x="{sx(v):.1f}" y="{bot + 30}" text-anchor="middle" class="tick">'
                     f'{_e(_tick_label(v))}</text>')
    parts.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{height - 8}" text-anchor="middle" '
                 'class="axis">position along the rolling direction [m] (to scale)</text>')
    return ''.join(parts + key_parts + ['</svg>'])


def _growth_chart(result):
    ch = result['chatter']
    curve = ch['growth_curve']
    xs = [c['exit_speed_m_s'] for c in curve]
    g1 = [c['max_growth_rate_per_s'] for c in curve]
    g0 = [c['max_growth_rate_without_bite_damping_per_s'] for c in curve]
    wb, nb = ch['with_bite_damping'], ch['without_bite_damping']
    key = [(f'beta = {_n(wb["bite_damping_transit_fraction"])} (bite-damping closure)',
            COLOURS[0], DASHES[0], 'line'),
           ('beta = 0 (no bite damping)', COLOURS[1], DASHES[1], 'line')]
    for crit, colour in ((wb, COLOURS[0]), (nb, COLOURS[1])):
        if crit['critical_exit_speed_m_s']:
            key.append((f'critical speed, beta = {_n(crit["bite_damping_transit_fraction"])}: '
                        f'{_n(crit["critical_exit_speed_m_s"])} m/s', colour, '', 'dot'))
    c = _Chart('Chatter growth rate versus exit speed', key)
    lo, hi = min(g1 + g0 + [0.0]), max(g1 + g0 + [0.0])
    pad = 0.06 * (hi - lo or 1)
    c.axes(_Axis(xs[0], xs[-1], ML, W - MR, log=True), _Axis(lo - pad, hi + pad, H - MB, c.mt),
           'exit speed [m/s] (log scale)', 'max growth rate [1/s] (> 0: growing)')
    y0 = c.y(0)
    c.inner.append(f'<line x1="{ML}" y1="{y0:.1f}" x2="{W - MR}" y2="{y0:.1f}" stroke="#111" '
                   'stroke-width="1"/>')
    c.poly(list(zip(xs, g1)), COLOURS[0], DASHES[0], 2.4)
    c.poly(list(zip(xs, g0)), COLOURS[1], DASHES[1], 2.0)
    u = ch['operating_exit_speed_m_s']
    anchor = 'end' if c.x(u) > W - MR - 120 else 'start'
    c.vline(u, '#111', '3 3', f'operating {_n(u)} m/s', c.mt + 14, anchor)
    for crit, colour in ((wb, COLOURS[0]), (nb, COLOURS[1])):
        if crit['critical_exit_speed_m_s']:
            c.inner.append(f'<circle cx="{c.x(crit["critical_exit_speed_m_s"]):.1f}" '
                           f'cy="{y0:.1f}" r="5" fill="{colour}" stroke="#111" '
                           'stroke-width="0.6"/>')
    return c.render('growth')


def _schedule_chart(sweep):
    rows = [r for r in sweep['rows'] if 'rejected' not in r]
    if not rows:
        return '<p>No schedule pass derived; see the table.</p>'
    hs = [r['exit_thickness_m'] * 1e3 for r in rows]
    s1 = [r['critical_exit_speed_m_s'] for r in rows]
    s0 = [r['critical_exit_speed_without_bite_damping_m_s'] for r in rows]
    so = [r['exit_speed_m_s'] for r in rows]
    vals = [v for v in s1 + s0 + so if v is not None]
    c = _Chart('Critical and operating exit speed per pass',
               [(f'critical speed, beta = {_n(sweep["bite_damping_transit_fraction"])}',
                 COLOURS[0], DASHES[0], 'line'),
                ('critical speed, beta = 0', COLOURS[1], DASHES[1], 'line'),
                ('operating exit speed (label: operating / critical, beta as supplied)',
                 COLOURS[2], DASHES[2], 'line')])
    c.axes(_Axis(min(hs) / 1.25, max(hs) * 1.25, ML, W - MR, log=True),
           _Axis(0.0, max(vals) * 1.18, H - MB, c.mt), 'exit gauge [mm] (log scale)',
           'exit speed [m/s]')
    for series, colour, dash, mark in ((s1, COLOURS[0], DASHES[0], 'circle'),
                                       (s0, COLOURS[1], DASHES[1], 'square'),
                                       (so, COLOURS[2], DASHES[2], 'diamond')):
        pts = [(h, v) for h, v in zip(hs, series) if v is not None]
        if len(pts) > 1:
            c.poly(pts, colour, dash, 2.2)
        for h, v in pts:
            px, py = c.x(h), c.y(v)
            if mark == 'circle':
                c.inner.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{colour}"/>')
            elif mark == 'square':
                c.inner.append(f'<rect x="{px - 4:.1f}" y="{py - 4:.1f}" width="8" height="8" '
                               f'fill="{colour}"/>')
            else:
                c.inner.append(f'<path d="M{px:.1f} {py - 6:.1f} L{px + 6:.1f} {py:.1f} '
                               f'L{px:.1f} {py + 6:.1f} L{px - 6:.1f} {py:.1f} Z" '
                               f'fill="{colour}"/>')
    for r, h, v in zip(rows, hs, so):
        # above-right of the operating point: the operating line falls to the right there
        c.inner.append(f'<text x="{c.x(h) + 7:.1f}" y="{c.y(v) - 8:.1f}" class="lab" '
                       f'fill="{COLOURS[2]}">{_e(_n(r["speed_ratio"], 3))}</text>')
    return c.render('sched')


def _freq_speed_chart(result):
    sig = result['signatures']
    modes = result['stand_modes']['structural_modes_for_catalogue']
    u_op = result['inputs']['pass']['exit_speed_m_s']
    obs = sig['observations']
    meas = result['inputs']['observation']['measured_vibration_hz']
    umax = max([u_op] + [o['exit_speed_m_s'] for o in obs]) * 1.35
    fobs = [o['implied_frequency_hz'] for o in obs]
    fmax = max([m['frequency_hz'] for m in modes] + fobs + ([meas] if meas else [])) * 1.15
    key = [('order-locked source, f proportional to speed (grey, labelled at line end)',
            '#8792a6', '', 'line')]
    for i, m in enumerate(modes):
        key.append((f'{m["name"]} {_n(m["frequency_hz"])} Hz', COLOURS[(i + 1) % 7],
                    DASHES[(i + 1) % 7], 'line'))
    key.append(('observed (exit speed, u/p)', COLOURS[1], '', 'dot'))
    if meas:
        key.append(('measured vibration at operating speed', COLOURS[3], '', 'square'))
    c = _Chart('Frequency-speed map: order-locked sources and stand modes', key, H + 60)
    c.axes(_Axis(0.0, umax, ML, W - MR), _Axis(0.0, fmax, c.h - MB, c.mt), 'exit speed [m/s]',
           'frequency [Hz]')
    locked = [e for e in sig['catalogue'] if e['kind'] == 'order_locked' and e['frequency_hz']]
    ends = []
    for e in locked:
        slope = e['frequency_hz'] / u_op
        end_u = min(umax, fmax / slope)
        c.inner.append(f'<line x1="{c.x(0):.1f}" y1="{c.y(0):.1f}" x2="{c.x(end_u):.1f}" '
                       f'y2="{c.y(slope * end_u):.1f}" stroke="#8792a6" stroke-width="1.1"/>')
        ends.append((end_u, slope * end_u, e['id']))
    for i, m in enumerate(modes):
        py = c.y(m['frequency_hz'])
        c.inner.append(f'<line x1="{ML}" y1="{py:.1f}" x2="{W - MR}" y2="{py:.1f}" '
                       f'stroke="{COLOURS[(i + 1) % 7]}" stroke-width="2" '
                       f'stroke-dasharray="{DASHES[(i + 1) % 7]}"/>')
    # line-end labels: right edge (de-overlapped downwards) and top edge (left to right)
    right = sorted((p for p in ends if p[0] >= umax * 0.999), key=lambda p: -p[1])
    last, skipped = None, 0
    for u, f, name in right:
        py = c.y(f) - 2
        if last is not None and py < last + 10:
            py = last + 10
        if py > c.h - MB - 2:
            skipped += 1
            continue
        c.inner.append(f'<text x="{W - MR - 4}" y="{py:.1f}" text-anchor="end" '
                       f'class="small">{_e(name)}</text>')
        last = py
    top = sorted((p for p in ends if p[0] < umax * 0.999), key=lambda p: p[0])
    lastx = None
    for u, f, name in top:
        px = c.x(u)
        if lastx is not None and px - lastx < 70:
            skipped += 1
            continue
        c.inner.append(f'<text x="{px - 3:.1f}" y="{c.mt + 11}" text-anchor="end" '
                       f'class="small">{_e(name)}</text>')
        lastx = px
    c.vline(u_op, '#111', '3 3', f'operating {_n(u_op)} m/s', c.h - MB - 6)
    for o in obs:
        c.inner.append(f'<circle cx="{c.x(o["exit_speed_m_s"]):.1f}" '
                       f'cy="{c.y(o["implied_frequency_hz"]):.1f}" r="5.5" fill="{COLOURS[1]}" '
                       'stroke="#111" stroke-width="0.8"/>')
    if meas:
        px, py = c.x(u_op), c.y(meas)
        c.inner.append(f'<rect x="{px - 6:.1f}" y="{py - 6:.1f}" width="12" height="12" '
                       f'fill="none" stroke="{COLOURS[3]}" stroke-width="2.2"/>')
    note = (f'<p class="note">{skipped} crowded line labels omitted; every order-locked line '
            'is listed in the source table below.</p>' if skipped else '')
    return c.render('fmap') + note


def _spectrum_chart(fr):
    a = fr['work_backup_runout']['spectrum']
    b = fr['entry_thickness']['spectrum']
    xs = [p['frequency_hz'] for p in a]
    vals = [p['exit_thickness_per_unit_disturbance'] for p in a + b]
    vals = [v for v in vals if v > 0]
    c = _Chart('Forced exit-thickness response',
               [('work/backup roll run-out', COLOURS[0], DASHES[0], 'line'),
                ('incoming (entry) thickness ripple', COLOURS[1], DASHES[1], 'line'),
                ('roll 1x / 2x orders at the operating speed', COLOURS[2], '', 'dot')])
    c.axes(_Axis(xs[0], xs[-1], ML, W - MR, log=True),
           _Axis(min(vals) / 1.5, max(vals) * 1.5, H - MB, c.mt, log=True),
           'frequency [Hz] (log scale)', 'exit thickness / disturbance [m/m]')
    for series, colour, dash in ((a, COLOURS[0], DASHES[0]), (b, COLOURS[1], DASHES[1])):
        c.poly([(p['frequency_hz'], p['exit_thickness_per_unit_disturbance']) for p in series
                if p['exit_thickness_per_unit_disturbance'] > 0], colour, dash, 2.1)
    for row in fr['work_backup_runout']['roll_orders']:
        v = row['exit_thickness_per_unit_disturbance']
        if v > 0:
            c.inner.append(f'<circle cx="{c.x(row["frequency_hz"]):.1f}" cy="{c.y(v):.1f}" '
                           f'r="4.5" fill="{COLOURS[2]}" stroke="#111" stroke-width="0.6"/>')
    return c.render('spec')


def _trace_chart(sim):
    xs = sim['strip_position_m']
    ys = [v * 1e6 for v in sim['exit_thickness_perturbation_m']]
    lim = max(abs(v) for v in ys) or 1.0
    c = _Chart('Simulated exit thickness trace',
               [(f'linear RK4 trace at {_n(sim["exit_speed_m_s"])} m/s, beta = '
                 f'{_n(sim["bite_damping_transit_fraction"])}', COLOURS[0], '', 'line')])
    c.axes(_Axis(xs[0], xs[-1], ML, W - MR), _Axis(-lim * 1.1, lim * 1.1, H - MB, c.mt),
           'strip position after the bite [m] (= exit speed x time)',
           'exit thickness perturbation [um]')
    c.poly(list(zip(xs, ys)), COLOURS[0], '', 1.2)
    return c.render('trace')


def _spray_chart(screens, positions):
    cov = screens['spray_coverage']
    prof = screens['coverage_profile']
    length = prof['barrel_length_m']
    key = [('overlapping fans (coverage count)', '#94a3b8', '', 'block'),
           ('nozzle', COLOURS[0], '', 'dot')]
    if cov['blocked_nozzle_indices']:
        key.append(('blocked nozzle', COLOURS[1], '', 'dot'))
    if screens['band_risk_stripes']:
        key.append(('band-risk stripe (blocked nozzle / interior uncovered)', COLOURS[1], '',
                    'block'))
    if positions:
        key.append(('observed band position', COLOURS[3], DASHES[2], 'line'))
    c = _Chart('Spray coverage across the barrel', key)
    c.axes(_Axis(0.0, length, ML, W - MR), _Axis(0.0, cov['max_coverage_count'] + 1.2, H - MB,
                                                 c.mt),
           'position along the roll barrel [m]', 'overlapping fans [count]')
    for z in prof['zones']:
        x0, x1 = c.x(z['start_m']), c.x(z['end_m'])
        y1 = c.y(z['coverage_count'])
        c.inner.append(f'<rect x="{x0:.1f}" y="{y1:.1f}" width="{max(x1 - x0, 0.6):.1f}" '
                       f'height="{c.y(0) - y1:.1f}" fill="#94a3b8"/>')
    for s in screens['band_risk_stripes'] or []:
        x0, x1 = c.x(s['start_m']), c.x(s['end_m'])
        c.inner.append(f'<rect x="{x0:.1f}" y="{c.mt}" width="{max(x1 - x0, 1.5):.1f}" '
                       f'height="{c.y(0) - c.mt:.1f}" fill="{COLOURS[1]}" opacity="0.35"/>')
    top = c.y(cov['max_coverage_count'] + 1.0)
    for i, xp in enumerate(cov['nozzle_positions_m']):
        colour = COLOURS[1] if i in cov['blocked_nozzle_indices'] else COLOURS[0]
        c.inner.append(f'<circle cx="{c.x(xp):.1f}" cy="{top:.1f}" r="3.2" fill="{colour}"/>')
    for p in positions:
        c.vline(p, COLOURS[3], DASHES[2], f'band {_n(p)} m', c.mt + 26)
    return c.render('spray')

# ------------------------------------------------------------------------------ tables
def _table(headers, rows, cls='', widths=None):
    head = ''.join(f'<th scope="col">{_e(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows)
    cols = ('<colgroup>' + ''.join(f'<col style="width:{w}">' for w in widths) + '</colgroup>'
            if widths else '')
    return (f'<div class="scroll"><table class="{cls}">{cols}<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _standing_badge(standing):
    return f'<span class="badge {_e(standing.lower())}">{_e(standing)}</span>'


def _reason(h):
    sup = [e['criterion'] for e in h['evidence'] if e['verdict'] == 'SUPPORTS']
    con = [e['criterion'] for e in h['evidence'] if e['verdict'] == 'CONTRADICTS']
    return (f'score {h["score"]}; supported by {", ".join(sup) or "nothing"}; '
            f'contradicted by {", ".join(con) or "nothing"}')


def _hypothesis_rows(result, family=None):
    """Hypothesis table; with ``family`` (v2) a family column, observed family first."""
    out = []
    hyps = result['hypotheses']
    if family is not None:
        hyps = sorted(hyps, key=lambda h: (h.get('family') != family, h['rank']))
    for h in hyps:
        ev_rows = [[_e(e['criterion']), _e(e['observed']), _e(e['expected']),
                    f'<span class="v-{_e(e["verdict"].lower())}">{_e(e["verdict"])}</span>',
                    _e(e['weight'] or '-'), _e(e['basis'])] for e in h['evidence']]
        t = h['tallies']
        details = (
            f'<details><summary>{_e(h["title"])}: evidence ({t["supports"]} supports, '
            f'{t["contradicts"]} contradicts, {t["neutral"]} neutral, {t["not_observed"]} not '
            'observed)</summary>'
            f'<p><strong>Mechanism.</strong> {_e(h["mechanism"])}</p>'
            + _table(('criterion', 'observed', 'expected', 'verdict', 'weight', 'basis'),
                     ev_rows, 'evidence fixed', ('16%', '31%', '26%', '11%', '8%', '8%'))
            + f'<p><strong>Model prediction.</strong> {_e(_val(h["model_prediction"]))}</p>'
            f'<p><strong>Confirming test.</strong> {_e(h["confirming_test"])}</p>'
            f'<p><strong>Levers if this is the cause.</strong> {_e("; ".join(h["levers"]))}</p>'
            + (f'<p><strong>Computed lever directions.</strong> '
               f'{_e("; ".join(h["computed_lever_directions"]))}</p>'
               if h.get('computed_lever_directions') else '')
            + '</details>')
        row = [str(h['rank']), f'<code>{_e(h["id"])}</code>{details}',
               _standing_badge(h['standing']), str(h['score']),
               f'{t["support_points"]} / {t["contradiction_points"]}']
        if family is not None:
            row.insert(2, _e(h.get('family') or 'n/a'))
        out.append(row)
    if family is not None:
        return _table(('rank', 'hypothesis (click for evidence)', 'family', 'standing', 'score',
                       'points + / -'), out, 'hyp fixed', ('3.2rem', 'auto', '6.6rem', '11.5rem',
                                                           '3.8rem', '5.5rem'))
    return _table(('rank', 'hypothesis (click for evidence)', 'standing', 'score',
                   'points + / -'), out, 'hyp fixed', ('3.2rem', 'auto', '11.5rem', '3.8rem',
                                                       '5.5rem'))


CSS = ('body{font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;max-width:64rem;'
       'overflow-wrap:break-word;'
       'margin:1.5rem auto;padding:0 1rem;color:#172033;background:#fff}'
       'h1{font-size:1.6rem;margin-bottom:.2rem}h1,h2,h3{line-height:1.25}'
       'h2{font-size:1.25rem;margin-top:2rem}h3{font-size:1.05rem}'
       'section{border-top:1px solid #ccd3df;padding-top:.4rem}'
       '.warn{border:2px solid #b45309;background:#fff7ed;padding:.7rem 1rem;border-radius:6px}'
       '.lead{border-left:5px solid #0b62a4;background:#f1f6fc;padding:.6rem 1rem}'
       'table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.88rem}'
       'th,td{border:1px solid #ccd3df;padding:.3rem .4rem;text-align:left;vertical-align:top;'
       'overflow-wrap:break-word}th{background:#f4f6fa}'
       'table.fixed{table-layout:fixed}table.fixed td{overflow-wrap:anywhere}'
       '.scroll{overflow-x:auto}'
       'table.num td{text-align:right}table.num td:first-child{text-align:left}'
       'details{margin:.3rem 0}summary{cursor:pointer;color:#17428c}'
       '.chart{width:100%;height:auto;max-width:760px;display:block;margin:.4rem 0}'
       '.tick{font-size:11px;fill:#374151}.axis{font-size:12.5px;fill:#111827}'
       '.key{font-size:11.5px;fill:#111827}.lab{font-size:11.5px;font-weight:600;'
       'paint-order:stroke;stroke:#fff;stroke-width:3px}'
       '.small{font-size:10px;fill:#4b5563;paint-order:stroke;stroke:#fff;stroke-width:2.5px}'
       '.note{font-size:.85rem;color:#4b5563}'
       '.badge{font-size:.78rem;padding:.05rem .35rem;border-radius:4px;white-space:nowrap;'
       'border:1px solid #9aa5b8}.consistent_leading{background:#dcfce7;border-color:#15803d}'
       '.contradicted{background:#fee2e2;border-color:#b91c1c}.consistent{background:#ecfeff}'
       '.weakened{background:#fef9c3}.not_assessable{background:#f3f4f6}'
       '.v-supports{color:#15803d;font-weight:600}.v-contradicts{color:#b91c1c;font-weight:600}'
       '.v-not_observed{color:#6b7280}code{font-size:.85em}'
       'table.hyp{min-width:46rem}table.evidence{min-width:38rem}'
       '@media print{details{display:block}summary{display:none}}')


# ------------------------------------------------------------------------------ phase-2 helpers
# Lengthwise-band (case schema v2) sections. Every value is read from the result dict; the
# keys of the engine's follow-up work (tension-release states and thresholds) are used when
# present and the column / line is omitted when absent.
V1_SCHEMA = 'physicroll.band_case.v1'
BAD_STATES = ('NOT_SUPPLIED', 'FAILED', 'NOT_ASSESSABLE')
CSS2 = ('.wide{overflow-x:auto;margin:.4rem 0}.wide .chart{min-width:600px;max-width:none;'
        'margin:0}.state{color:#4b5563;font-style:italic}'
        '.family{border-left:5px solid #7e22ce;background:#faf5ff;padding:.6rem 1rem;'
        'margin:.8rem 0}.family p{margin:.3rem 0}'
        '.divider{border-top:3px double #9aa5b8;margin-top:2.5rem}'
        '.match{color:#15803d;font-weight:600}.miss{color:#6b7280}'
        'table.num td{white-space:nowrap}table.num td:first-child,table.wrapall td,'
        'table.num td .wrap{white-space:normal}table.num td:first-child{min-width:7rem}'
        '.legend{font-size:.85rem;color:#374151;margin:.2rem 0 .6rem}')
C_ACT, C_HEALTHY = '#c2410c', '#374151'
C_RIGID, C_COMP, C_FB = '#a16207', '#7e22ce', '#0b62a4'
C_THR, C_OBS, C_BLOCK, C_EVENT = '#15803d', '#111827', '#b91c1c', '#0e7490'
SOURCE_NAMES = {'steady_stripes': 'steady model stripe (peak)',
                'blocked_or_low_level_nozzles': 'blocked / low-level nozzle',
                'event_nozzles': 'cooling-zone event nozzle',
                'event_stripe_peaks': 'cooling-zone event stripe peak',
                'incoming_ridges': 'incoming ridge',
                'two_tone': 'two-tone edge of a previous (narrower) strip'}
PITCH_NAMES = {'nozzle_pitch_m': 'nozzle pitch', 'cooling_zone_pitch_m': 'cooling-zone pitch',
               'grinding_feed_pitch_m': 'grinding feed pitch',
               'trough_wavelength_entry_span_m': 'trough wavelength, entry span',
               'trough_wavelength_exit_span_m': 'trough wavelength, exit span'}


def _ok(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _f(v, scale=1.0, digits=3, unit=''):
    """Finite-safe number with an optional display scale (labelled by ``unit``)."""
    if not _ok(v):
        return 'n/a'
    x = v * scale
    text = f'{x:.{digits}g}'
    if text in ('-0', '-0.0'):
        text = '0'
    return text + (f' {unit}' if unit else '')


def _um(v, d=3):
    return _f(v, 1e6, d, 'µm')


def _onset_um(x, key, d=3):
    """An onset height, or the feedback model's domain limit that ended its search (never
    shown as an onset)."""
    v = x.get(key)
    dl = x.get(key[:-2] + '_domain_limit_m')
    if not _ok(v) and _ok(dl):
        return f'not reached before the feedback model\'s domain limit (about {_um(dl, d)})'
    return _um(v, d)


def _mm2(v, d=3):
    return _f(v, 1e3, d, 'mm')


def _mpa(v, d=3):
    return _f(v, 1e-6, d, 'MPa')


def _txt(code):
    """State code in plain words (escaped)."""
    return 'n/a' if not code else _e(str(code).lower().replace('_', ' '))


SHORT_STATES = {'MANIFEST_BUCKLE': 'buckled in the mill',
                'LATENT_UNDER_TENSION': 'hidden under mill tension',
                'MANIFEST_AFTER_TENSION_RELEASE': 'visible after tension release',
                'FLAT_AFTER_TENSION_RELEASE': 'flat after tension release',
                'BELOW_REPORTING_THRESHOLD': 'below the reporting threshold'}
VISIBLE_BASIS = {'in_mill_manifest': 'band buckled in the mill',
                 'manifest_after_tension_release': 'band visible only after tension release',
                 'above_reporting_threshold_only': 'above the 2 I-unit reporting threshold only'}
FLAT_AXIS = 'linear'


def _states(in_mill, released=None):
    """The two band states in plain words (escaped)."""
    text = _short(in_mill)
    return text + (f'; {_short(released)}' if released else '')


def _util(v):
    """Buckling utilisation: only values below 1 are meaningful magnitudes."""
    if not _ok(v):
        return 'n/a'
    return '≥ 1' if v >= 1 else f'{v:.2g}'


def _fb_profile_key(st):
    """Linear-feedback I-unit profile when present (the saturated one jumps at band edges)."""
    return 'i_units_linear_feedback' if st.get('i_units_linear_feedback') else \
        'i_units_with_feedback'


def _short(code):
    """Short chart label for a band state (escaped)."""
    return _e(SHORT_STATES.get(code, str(code or 'n/a').lower().replace('_', ' ')))


def _get(d, *path):
    for k in path:
        if isinstance(d, dict):
            d = d.get(k)
        elif isinstance(d, list) and isinstance(k, int) and -len(d) <= k < len(d):
            d = d[k]
        else:
            return None
    return d


def _bad(sec):
    """State line for an absent / not-supplied / failed / not-assessable section, else ''."""
    if sec is None:
        return 'not computed: the inputs it needs are absent'
    if not isinstance(sec, dict):
        return ''
    st = sec.get('status')
    if sec.get('not_supplied') or st == 'NOT_SUPPLIED':
        return 'not supplied: ' + str(sec.get('reason', 'no reason given'))
    if st == 'FAILED':
        return 'failed: ' + str(sec.get('error', sec.get('reason', 'no error text')))
    if st == 'NOT_ASSESSABLE':
        return 'not assessable: ' + str(sec.get('reason', 'no reason given'))
    return ''


def _state_p(text):
    return f'<p class="state">{_e(text)}</p>'


def _ul(items):
    items = [x for x in items if x]
    return '<ul>' + ''.join(f'<li>{x}</li>' for x in items) + '</ul>' if items else ''


def _wide(svg):
    return f'<div class="wide">{svg}</div>'


def _key2(entries, x0=ML, width=W):
    """Key rows like ``_Chart._key`` plus marker shapes (cross, triangle, diamond, band)."""
    parts, x, y, rows = [], x0, 16, 1
    for label, colour, dash, kind in entries:
        wdt = 34 + 6.3 * len(label)
        if x + wdt > width - MR and x > x0:
            x, y, rows = x0, y + 15, rows + 1
        cx, cy = x + 11, y - 4
        if kind == 'cross':
            parts.append(_cross(cx, cy, colour))
        elif kind == 'tri':
            parts.append(_tri(cx, cy, colour))
        elif kind == 'diamond':
            parts.append(_diamond(cx, cy, colour))
        elif kind == 'dot':
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{colour}" '
                         'stroke="#111" stroke-width="0.6"/>')
        elif kind == 'hollow':
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="#fff" stroke="#374151" '
                         'stroke-width="2"/>')
        elif kind == 'square':
            parts.append(f'<rect x="{cx - 5}" y="{cy - 5}" width="10" height="10" '
                         f'fill="{colour}" stroke="#111" stroke-width="0.6"/>')
        elif kind == 'band':
            parts.append(f'<rect x="{x}" y="{y - 10}" width="22" height="12" fill="{colour}" '
                         'stroke="#9aa5b8"/>')
        else:
            sw = 3.4 if kind == 'thick' else 2.4
            parts.append(f'<line x1="{x}" y1="{cy}" x2="{x + 22}" y2="{cy}" stroke="{colour}" '
                         f'stroke-width="{sw}" stroke-dasharray="{dash}"/>')
        parts.append(f'<text x="{x + 27}" y="{y}" class="key">{_e(label)}</text>')
        x += wdt
    return parts, rows


def _cross(x, y, colour, r=5):
    return (f'<path d="M{x - r:.1f} {y - r:.1f} L{x + r:.1f} {y + r:.1f} M{x - r:.1f} '
            f'{y + r:.1f} L{x + r:.1f} {y - r:.1f}" stroke="{colour}" stroke-width="2.4"/>')


def _tri(x, y, colour, r=5.5):
    return (f'<path d="M{x:.1f} {y - r:.1f} L{x + r:.1f} {y + r * 0.8:.1f} '
            f'L{x - r:.1f} {y + r * 0.8:.1f} Z" fill="{colour}" stroke="#111" '
            'stroke-width="0.6"/>')


def _diamond(x, y, colour, r=6):
    return (f'<path d="M{x:.1f} {y - r:.1f} L{x + r:.1f} {y:.1f} L{x:.1f} {y + r:.1f} '
            f'L{x - r:.1f} {y:.1f} Z" fill="{colour}" stroke="#fff" stroke-width="1"/>')


class _Chart2(_Chart):
    """``_Chart`` with the extended key markers of ``_key2``."""
    _key = staticmethod(_key2)


class _SymLog:
    """Signed-log axis: f(v) = sign(v) log10(1 + |v|/c), so small thresholds and large peaks
    share one axis (I-units). Ticks at 0 and signed decades."""

    def __init__(self, lo, hi, p0, p1, c=1.0):
        self.c, self.p0, self.p1 = c, p0, p1
        self.lo, self.hi = min(lo, 0.0), max(hi, 0.0)
        if self.hi - self.lo <= 0:
            self.hi = 1.0
        self.a, self.b = self._f(self.lo), self._f(self.hi)

    def _f(self, v):
        return math.copysign(math.log10(1 + abs(v) / self.c), v)

    def __call__(self, v):
        return self.p0 + (self._f(v) - self.a) / (self.b - self.a) * (self.p1 - self.p0)

    def ticks(self):
        top = max(abs(self.lo), abs(self.hi))
        dec = [10.0 ** k for k in range(0, 9) if 10.0 ** k <= top * (1 + 1e-9)]
        if len(dec) >= 3:
            dec = dec[1:]
        elif len(dec) < 2:
            dec = [v for v in (0.5, 1.0, 2.0, 5.0) if v <= top] or [top]
        out = [0.0]
        for v in dec:
            if v <= self.hi * (1 + 1e-9):
                out.append(v)
            if -v >= self.lo * (1 + 1e-9):
                out.append(-v)
        return sorted(out)


def _place_labels(items, y_rows, char_w=6.4, x_lo=ML, x_hi=W - MR):
    """Greedy label rows: items (x, text) -> list of (x, y, anchor, text) without overlap."""
    placed, out = [], []
    for x, text in sorted(items, key=lambda t: t[0]):
        w = char_w * len(text) + 6
        anchor, a = 'middle', x - w / 2
        if a < x_lo:
            anchor, a = 'start', x_lo + 1
        elif a + w > x_hi:
            anchor, a = 'end', x_hi - 1 - w
        for y in y_rows:
            if all(not (a < b1 and b0 < a + w) for (b0, b1, yy) in placed if yy == y):
                placed.append((a, a + w, y))
                tx = {'middle': x, 'start': a, 'end': a + w}[anchor]
                out.append((tx, y, anchor, text))
                break
    return out


def _pts(xs, ys, fx, fy):
    return ' '.join(f'{fx(a):.1f},{fy(b):.1f}' for a, b in zip(xs, ys) if _ok(a) and _ok(b))


# ------------------------------------------------------------------------------ across the width
def _width_chart(r):
    w = r['width']
    ts, st = w['thermal_steady'], _get(w, 'shape', 'steady')
    obs = [p for p in (_get(r, 'inputs', 'observation', 'band_positions_across_width_m') or [])
           if _ok(p)]
    z = ts['z_m']
    barrel = w.get('barrel_length_m')
    if not _ok(barrel):
        barrel = _get(r, 'inputs', 'width_model', 'roll', 'barrel_length_m')
    if not _ok(barrel):
        barrel = z[-1] + (z[-1] - z[-2]) / 2 if len(z) > 1 else z[-1]
    shape_ok = isinstance(st, dict) and not _bad(st) and st.get('z_m')
    levels = st.get('levels', {}) if shape_ok else {}
    nl = ts.get('nozzle_levels') or []
    npos = ts.get('nozzle_positions_m') or []
    events = _get(w, 'thermal_events', 'events') or []
    ev_noz = {}
    for k, e in enumerate(events):
        for i in e.get('nozzle_indices') or []:
            ev_noz.setdefault(i, []).append(k + 1)
    low = [i for i, lv in enumerate(nl) if _ok(lv) and lv < 1.0]
    key = [('roll radius growth, actual header', C_ACT, '', 'line'),
           ('healthy header (all nozzles at level 1)', C_HEALTHY, '7 4', 'line'),
           ('strip extent', '#e9eef6', '', 'band'),
           ('nozzle', '#6b7280', '', 'line')]
    if low:
        key.append(('blocked / low-level nozzle', C_BLOCK, '', 'cross'))
    if ev_noz:
        key.append(('cooling-zone event nozzle', C_EVENT, '', 'tri'))
    if obs:
        key.append(('observed band position', C_OBS, '6 3', 'diamond'))
    if shape_ok:
        if st.get('i_units_rigid') is not None:
            key.append(('flatness, rigid roll (upper bound)', C_RIGID, '2 3', 'line'))
        key += [('compliance only (bound)', C_COMP, '9 3 2 3', 'line'),
                ('with exit-tension feedback' + (', linear (unsaturated)'
                                                  if _fb_profile_key(st) ==
                                                  'i_units_linear_feedback' else ''),
                 C_FB, '', 'thick'),
                (f'reporting threshold ±{_f(st.get("reporting_threshold_i_units"))} I',
                 C_THR, '4 2', 'line')]
    key_parts, rows = _key2(key)
    top0 = 14 + 15 * rows + 8
    lab_rows = (top0 + 12, top0 + 26) if obs else ()
    t1 = top0 + (32 if obs else 6)          # upper panel top
    b1 = t1 + 180                           # upper panel bottom
    nz = b1 + 22                            # nozzle row
    t2 = nz + 34 if shape_ok else nz
    b2 = t2 + 230 if shape_ok else nz
    height = b2 + MB + (0 if shape_ok else 10)
    sx = _Axis(0.0, barrel, ML, W - MR)
    g_act = [v * 1e6 for v in ts['radius_growth_m']]
    g_h = [v * 1e6 for v in ts.get('healthy_radius_growth_m') or []]
    vals = [v for v in g_act + g_h if _ok(v)]
    lo, hi = min(vals), max(vals)
    pad = 0.08 * (hi - lo or 1.0)
    sy = _Axis(lo - pad, hi + pad * 2.5, b1, t1)
    p = [f'<svg viewBox="0 0 {W} {height}" role="img" xmlns="http://www.w3.org/2000/svg" '
         'class="chart" aria-label="across the width"><title>Roll radius growth and strip '
         'flatness across the width, with observed band positions</title>']
    s0, s1 = ts.get('strip_start_m'), ts.get('strip_end_m')
    panels = [(t1, b1)] + ([(t2, b2)] if shape_ok else [])
    for (ta, tb) in panels:
        p.append(f'<rect x="{ML}" y="{ta}" width="{W - ML - MR}" height="{tb - ta}" '
                 'fill="#fbfcfe" stroke="#9aa5b8"/>')
        if _ok(s0) and _ok(s1):
            p.append(f'<rect x="{sx(s0):.1f}" y="{ta}" width="{sx(s1) - sx(s0):.1f}" '
                     f'height="{tb - ta}" fill="#e9eef6"/>')
        for v in sx.ticks():
            p.append(f'<line x1="{sx(v):.1f}" y1="{ta}" x2="{sx(v):.1f}" y2="{tb}" '
                     'stroke="#d8dee8"/>')
    for v in sy.ticks():
        p.append(f'<line x1="{ML}" y1="{sy(v):.1f}" x2="{W - MR}" y2="{sy(v):.1f}" '
                 'stroke="#d8dee8"/>')
        p.append(f'<text x="{ML - 6}" y="{sy(v) + 4:.1f}" text-anchor="end" class="tick">'
                 f'{_e(_tick_label(v))}</text>')
    cy = (t1 + b1) / 2
    p.append(f'<text x="14" y="{cy:.1f}" text-anchor="middle" transform="rotate(-90 14 '
             f'{cy:.1f})" class="axis">radius growth [µm]</text>')
    if g_h:
        p.append(f'<polyline points="{_pts(z, g_h, sx, sy)}" fill="none" stroke="{C_HEALTHY}" '
                 'stroke-width="1.8" stroke-dasharray="7 4"/>')
    p.append(f'<polyline points="{_pts(z, g_act, sx, sy)}" fill="none" stroke="{C_ACT}" '
             'stroke-width="2.4"/>')
    if _ok(s0) and _ok(s1):
        p.append(f'<text x="{sx(s0) + 4:.1f}" y="{b1 - 6}" class="small">strip '
                 f'{_e(_f(s0))}–{_e(_f(s1))} m</text>')
    # model stripes: peak annotated
    for sp in ts.get('stripes') or []:
        x = sp.get('peak_position_m')
        if not _ok(x):
            continue
        k = min(range(len(z)), key=lambda i: abs(z[i] - x))
        py = sy(g_act[k])
        p.append(f'<circle cx="{sx(x):.1f}" cy="{py:.1f}" r="3.5" fill="{C_ACT}"/>')
        txt = f'model stripe {"+" if (sp.get("peak_deviation_m") or 0) > 0 else ""}' \
              f'{_um(sp.get("peak_deviation_m"))} at {_f(x, 1, 4)} m'
        anchor = 'start' if sx(x) < W / 2 else 'end'
        dx = 7 if anchor == 'start' else -7
        p.append(f'<text x="{sx(x) + dx:.1f}" y="{max(py - 6, t1 + 12):.1f}" '
                 f'text-anchor="{anchor}" class="lab" fill="{C_ACT}">{_e(txt)}</text>')
    # nozzle row
    p.append(f'<text x="{ML - 6}" y="{nz + 4}" text-anchor="end" class="tick">nozzles</text>')
    p.append(f'<line x1="{ML}" y1="{nz}" x2="{W - MR}" y2="{nz}" stroke="#cbd2dc"/>')
    marks = []
    for i, x in enumerate(npos):
        if not _ok(x):
            continue
        px = sx(x)
        p.append(f'<line x1="{px:.1f}" y1="{nz - 4}" x2="{px:.1f}" y2="{nz + 4}" '
                 'stroke="#6b7280" stroke-width="1.4"/>')
        if i in low:
            p.append(_cross(px, nz - 10, C_BLOCK))
            lv = nl[i]
            marks.append((px, f'#{i} {"off" if lv == 0 else "level " + _f(lv)}'))
        if i in ev_noz:
            p.append(_tri(px, nz + 11, C_EVENT))
    for tx, ty, anc, text in _place_labels(marks, (nz - 17, nz - 30)):
        p.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" class="lab" '
                 f'fill="{C_BLOCK}">{_e(text)}</text>')
    ev_lab = []
    for k, e in enumerate(events):
        xs_ = [x for x in e.get('nozzle_positions_m') or [] if _ok(x)]
        if xs_:
            ev_lab.append((sx(sum(xs_) / len(xs_)), f'event {k + 1}'))
    for tx, ty, anc, text in _place_labels(ev_lab, (nz + 29,)):
        p.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" class="lab" '
                 f'fill="{C_EVENT}">{_e(text)}</text>')
    # lower panel: flatness at three levels
    if shape_ok:
        sz = st['z_m']
        fb_key = _fb_profile_key(st)
        series = [('i_units_rigid', C_RIGID, '2 3', 1.1), ('i_units_compliance_only', C_COMP,
                                                          '9 3 2 3', 1.2),
                  (fb_key, C_FB, '', 3.0)]
        thr = st.get('reporting_threshold_i_units')
        if FLAT_AXIS == 'linear':
            fbv = [v for v in st.get(fb_key) or [] if _ok(v)] + [thr or 1.0, -(thr or 1.0)]
            span = max(fbv) - min(fbv)
            yy = _Axis(min(fbv) - 0.3 * span, max(fbv) + 0.45 * span, b2, t2)
        else:
            allv = [v for k, *_ in series for v in st.get(k) or [] if _ok(v)]
            yy = _SymLog(min(allv + [-(thr or 1.0)]) * 6, max(allv + [thr or 1.0]) * 6, b2, t2)
        for v in yy.ticks():
            p.append(f'<line x1="{ML}" y1="{yy(v):.1f}" x2="{W - MR}" y2="{yy(v):.1f}" '
                     f'stroke="{"#111" if v == 0 else "#d8dee8"}" '
                     f'stroke-width="{1 if v == 0 else 0.8}"/>')
            p.append(f'<text x="{ML - 6}" y="{yy(v) + 4:.1f}" text-anchor="end" class="tick">'
                     f'{_e(_tick_label(v))}</text>')
        cy2 = (t2 + b2) / 2
        p.append(f'<text x="14" y="{cy2:.1f}" text-anchor="middle" transform="rotate(-90 14 '
                 f'{cy2:.1f})" class="axis">flatness [I] '
                 f'({"+ long" if FLAT_AXIS == "linear" else "signed log; + long"})</text>')
        p.append(f'<clipPath id="clip-wlow"><rect x="{ML}" y="{t2}" width="{W - ML - MR}" '
                 f'height="{b2 - t2}"/></clipPath><g clip-path="url(#clip-wlow)">')
        if _ok(thr):
            for v in (thr, -thr):
                p.append(f'<line x1="{ML}" y1="{yy(v):.1f}" x2="{W - MR}" y2="{yy(v):.1f}" '
                         f'stroke="{C_THR}" stroke-width="1.3" stroke-dasharray="4 2"/>')
        for k, colour, dash, wdt in series:
            ys = st.get(k) or []
            if ys:
                p.append(f'<polyline points="{_pts(sz, ys, sx, yy)}" fill="none" '
                         f'stroke="{colour}" stroke-width="{wdt}" stroke-dasharray="{dash}" '
                         'stroke-linejoin="round"/>')
        p.append('</g>')
        fb = (levels.get('with_feedback') or {}).get('bands') or []
        up, dn = [], []
        for b in fb:
            x = b.get('center_m')
            if not _ok(x):
                continue
            t = _short(b.get('state'))
            if b.get('state_after_tension_release'):
                t += f' · {_short(b.get("state_after_tension_release"))}'
            pk = b.get('peak_i_units')
            (up if (pk or 0) >= 0 else dn).append((sx(x), t))
        for items, rows_y in ((up, (t2 + 15, t2 + 29)), (dn, (b2 - 7, b2 - 21))):
            for tx, ty, anc, text in _place_labels(items, rows_y, char_w=6.0):
                p.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" class="lab" '
                         f'fill="{C_FB}">{text}</text>')
    # observed band positions across both panels
    labs = _place_labels([(sx(x), f'observed {_f(x, 1, 4)} m') for x in obs], lab_rows) \
        if obs else []
    for x in obs:
        px = sx(x)
        p.append(f'<line x1="{px:.1f}" y1="{t1}" x2="{px:.1f}" y2="{b2 if shape_ok else b1}" '
                 f'stroke="{C_OBS}" stroke-width="1.6" stroke-dasharray="6 3"/>')
        p.append(_diamond(px, t1, C_OBS, 6.5))
    for tx, ty, anc, text in labs:
        p.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" class="lab" '
                 f'fill="{C_OBS}">{_e(text)}</text>')
    xb = b2 if shape_ok else nz + 30
    for v in sx.ticks():
        p.append(f'<text x="{sx(v):.1f}" y="{xb + 16}" text-anchor="middle" class="tick">'
                 f'{_e(_tick_label(v))}</text>')
    p.append(f'<text x="{(ML + W - MR) / 2:.1f}" y="{xb + 36}" text-anchor="middle" '
             'class="axis">position along the roll barrel [m] (to scale; same axis for both '
             'panels)</text>')
    return ''.join(p + key_parts + ['</svg>'])


def _stripe_table(w):
    rows_src = _get(w, 'shape', 'steady_stripe_table') or []
    st = _get(w, 'shape', 'steady')
    if not rows_src and isinstance(st, dict) and _bad(st):
        # SPEC9 9.1: stripes exist (thermal) but the shape chain is not assessable
        stripes = _get(w, 'thermal_steady', 'stripes') or []
        listed = ', '.join(f'{_f(x.get("peak_position_m"), 1, 4)} m '
                           f'({_um(x.get("peak_deviation_m"))})' for x in stripes)
        return ('<p>Steady radius stripes: ' + (_e(listed) if listed else 'none') + '. Their '
                'flatness, band states and onset heights are '
                + _e(_bad(st)) + '.</p>')
    if not rows_src:
        return '<p>No steady stripe above the stripe threshold.</p>'
    has = lambda k: any(k in x for x in rows_src)  # noqa: E731
    head = ['position', 'peak radius growth', 'half-peak width', 'rigid [I] (bound)',
            'compliance only [I] (bound)', 'with feedback [I]', 'in the mill',
            'after tension release', 'buckling utilisation, mill / released',
            'stripe height for a band: in the mill']
    if has('released_onset_peak_height_m'):
        head.append('after tension release')
    if has('reporting_onset_peak_height_m'):
        head.append('to reach 2 I-units')
    out = []
    for x in rows_src:
        fb = x.get('with_feedback') or {}
        rel = _onset_um(x, 'released_onset_peak_height_m')
        if x.get('released_onset_limited_by_reporting_threshold'):
            rel += ' (upper bound: limited by the reporting threshold)'
        row = [_f(x.get('position_m'), 1, 4, 'm'), _um(x.get('peak_radius_deviation_m')),
               _mm2(x.get('width_at_half_peak_m')),
               _f(_get(x, 'rigid', 'peak_i_units'), digits=4),
               _f(_get(x, 'compliance_only', 'peak_i_units'), digits=4),
               '<strong>' + _f(fb.get('peak_i_units'), digits=4) + '</strong>'
               + (' (saturated: indicative only)' if fb.get('saturated') else ''),
               _short(fb.get('state')),
               _short(fb.get('state_after_tension_release'))
               if fb.get('state_after_tension_release') else 'n/a',
               f'{_util(fb.get("buckling_utilisation"))} / '
               f'{_util(fb.get("released_buckling_utilisation"))}',
               _onset_um(x, 'manifest_onset_peak_height_m')]
        if has('released_onset_peak_height_m'):
            row.append(rel)
        if has('reporting_onset_peak_height_m'):
            row.append(_um(x.get('reporting_onset_peak_height_m')))
        out.append(row)
    return (_table(head, out, 'num wrapall')
            + '<p class="note">Buckling utilisation = compression / buckling stress of the band; '
              'it is shown only below 1, because once a band buckles the saturation of the '
              'feedback inflates the number and it is no longer a meaningful magnitude.</p>')


def _shape_notes(st):
    """Saturated bands (indicative peak) and the whole-sheet after-release indicator."""
    out = []
    fbl = _get(st, 'levels', 'with_feedback') or {}
    sat = [b for b in fbl.get('bands') or [] if b.get('saturated')]
    sb = fbl.get('saturated_bands') or []
    for k, b in enumerate(sat):
        lin = b.get('linear_feedback_peak_i_units')
        out.append(f'Band {_f(b.get("start_m"), 1, 4)}–{_f(b.get("end_m"), 1, 4)} m is slack '
                   'in the mill, so the exit-tension feedback saturates there: saturated peak '
                   f'{_f(b.get("peak_i_units"), digits=3)} I-units (indicative only; the '
                   f'linear-feedback peak plotted is {_f(lin, digits=3)} I-units'
                   + (f', scale factor {_f(sb[k].get("scale_factor"), digits=3)}'
                      if k < len(sb) else '') + ').')
    if st.get('released_global_status'):
        out.append('Whole-sheet indicator after tension release (upper-bound indicator only, '
                   'not charted): ' + _txt(st.get('released_global_status'))
                   + f', utilisation {_util(st.get("released_global_max_utilisation"))}.')
    if st.get('released_status'):
        out.append(f'Bands after tension release: {_txt(st.get("released_status"))}'
                   + (f' ({_f(st.get("manifest_after_release_band_count"))} band(s))'
                      if st.get('manifest_after_release_band_count') is not None else '')
                   + '.')
    return ''.join(f'<p class="note">{x}</p>' for x in out)


def _ripple_line(w):
    rp = _get(w, 'shape', 'nozzle_pattern_ripple')
    if rp is None:
        return '<p>Nozzle-pattern ripple: none (no ripple between nozzles).</p>'
    if _bad(rp):
        return _state_p('Nozzle-pattern ripple ' + _bad(rp))
    return ('<p><strong>Nozzle-pattern ripple</strong> (the regular fan-overlap pattern, not a '
            f'fault): peak-to-peak {_um(rp.get("peak_to_peak_m"))} radius; '
            + (f'{_f(rp.get("linear_feedback_peak_i_units"))} I-units with the linear '
               'exit-tension feedback '
               if _ok(rp.get('linear_feedback_peak_i_units')) else
               f'{_f(rp.get("feedback_peak_i_units"))} I-units with the exit-tension feedback ')
            + f'({_f(rp.get("compliance_only_peak_i_units"))} compliance only, '
            f'{_f(rp.get("rigid_transfer_bound_i_units"))} rigid bound); '
            f'{_f(rp.get("band_count_with_feedback"))} bands; status '
            f'{_txt(rp.get("status"))}.</p>')


def _match_tables(pos):
    obs = pos.get('observed_positions_m') or []
    pred = pos.get('predicted_positions_m') or {}
    pm = pos.get('position_matches') or {}
    out = [f'<p>Observed positions {_e(", ".join(_f(x, 1, 4) for x in obs) or "none")} m; '
           f'match tolerance {_mm2(pos.get("tolerance_m"))} '
           f'({_e(pos.get("tolerance_basis") or "basis not given")}).</p>']
    if obs and pm:
        found = {i: [] for i in range(len(obs))}
        for name, m in pm.items():
            for j, row in enumerate(m.get('matches') or []):
                if row.get('matched') and j in found:
                    found[j].append(f'{SOURCE_NAMES.get(name, name.replace("_", " "))} '
                                    f'({_f(row.get("nearest_predicted_position_m"), 1, 4)} m)')
        items = [f'<strong>{_f(x, 1, 4)} m</strong>: '
                 + (_e('; '.join(found[i])) if found[i]
                    else '<span class="miss">no predicted source within tolerance</span>')
                 for i, x in enumerate(obs)]
        out.append('<h3>Which predicted source each observed band matches</h3>' + _ul(items))
        rows = []
        for name, plist in pred.items():
            m = pm.get(name) or {}
            cells = []
            for row in m.get('matches') or []:
                d = row.get('distance_m')
                if row.get('matched'):
                    cells.append(f'<span class="match">match</span> '
                                 f'{_f(row.get("nearest_predicted_position_m"), 1, 4)} m '
                                 f'(Δ {_mm2(d, 2)})')
                elif _ok(d):
                    cells.append(f'<span class="miss">nearest '
                                 f'{_f(row.get("nearest_predicted_position_m"), 1, 4)} m '
                                 f'(Δ {_mm2(d, 3)})</span>')
                else:
                    cells.append('<span class="miss">nothing predicted</span>')
            cells += [''] * (len(obs) - len(cells))
            rows.append([_e(SOURCE_NAMES.get(name, name.replace('_', ' '))),
                         _e(', '.join(_f(x, 1, 4) for x in plist) or 'none')] + cells[:len(obs)]
                        + [_txt(m.get('status'))])
        out.append(_table(['predicted source', 'predicted positions [m]']
                          + [f'observed {_f(x, 1, 4)} m' for x in obs] + ['status'], rows))
    elif not obs:
        out.append('<p>No observed band positions supplied: positions not matched.</p>')
    gaps = pos.get('observed_gaps_m')
    sa = pos.get('spacing_analysis')
    sm = pos.get('spacing_matches') or {}
    if gaps:
        line = (f'Gaps between bands: {_e(", ".join(_mm2(g, 4) for g in gaps))} '
                f'({_e(pos.get("observed_gaps_basis") or "")})')
        if isinstance(sa, dict):
            line += (f'; mean {_mm2(sa.get("mean_gap_m"), 4)}, coefficient of variation '
                     f'{_f(sa.get("coefficient_of_variation"), digits=2)}: '
                     f'{_txt(sa.get("status"))}')
        out.append(f'<h3>Which pitch the gaps are multiples of</h3><p>{line}.</p>')
        rows, notes = [], []
        pitches = pos.get('pitches_m') or {}
        for name, m in sm.items():
            pname = PITCH_NAMES.get(name, name.replace('_', ' '))
            if not isinstance(m, dict):
                continue
            if 'gaps' not in m:
                if str(m.get('status', '')).startswith('NOT_COMPARABLE'):
                    notes.append(f'The {_e(pname)} ({_mm2(m.get("candidate_pitch_m"), 4)}) is '
                                 'not compared: the smallest gap is '
                                 f'{_f(m.get("min_gap_in_pitches"), digits=3)} pitches, beyond '
                                 'the 8 pitches over which a multiple can be told apart.')
                else:
                    notes.append(f'{_e(pname)}: {_txt(m.get("status"))}.')
                continue
            cells = []
            for g in m.get('gaps') or []:
                dev = g.get('deviation_in_pitches')
                txt = (f'{_f(g.get("nearest_multiple"))} × ({"+" if (dev or 0) >= 0 else ""}'
                       f'{_f(dev, digits=2)} pitch)')
                cells.append(f'<span class="match">{_e(txt)}</span>' if g.get('matched')
                             else f'<span class="miss">no ({_e(txt)})</span>')
            cells += [''] * (len(gaps) - len(cells))
            pv = m.get('candidate_pitch_m', pitches.get(name))
            rows.append([_e(pname), _mm2(pv, 4)] + cells[:len(gaps)]
                        + [_txt(m.get('status'))])
        if rows:
            out.append(_table(['pitch', 'value'] + [f'gap {_mm2(g, 4)}' for g in gaps]
                              + ['status'], rows))
        out += [f'<p>{x}</p>' for x in notes]
    return ''.join(out)


def _other_width_results(w):
    out = []
    tr = w.get('troughs')
    if isinstance(tr, dict) and tr:
        rows = []
        for name in ('entry_span', 'exit_span'):
            t = tr.get(name)
            if not isinstance(t, dict):
                continue
            if 'error' in t:
                rows.append([_e(name.replace('_', ' ')), f'<em>{_e(t["error"])}</em>', '', '', '',
                             '', ''])
                continue
            ratio = t.get('observed_spacing_to_wavelength_ratio')
            rows.append([_e(name.replace('_', ' ')), _txt(t.get('status')),
                         _mm2(t.get('wrinkle_wavelength_m'), 4),
                         _f(t.get('expected_trough_count_across_width'), digits=3),
                         _mpa(t.get('trough_critical_lateral_stress_pa')),
                         _mpa(t.get('roller_wrinkle_critical_lateral_stress_pa')),
                         'not observed' if ratio is None else _f(ratio, digits=3)])
        out.append('<h3>Tension troughs (span wrinkling)</h3>'
                   + _table(('span', 'status', 'wrinkle wavelength', 'expected troughs across '
                             'the width', 'trough onset lateral stress', 'roller wrinkle lateral '
                             'stress', 'observed spacing / wavelength'), rows))
        notes = {t.get('wide_foil_note') for t in tr.values()
                 if isinstance(t, dict) and t.get('wide_foil_note')}
        for n in sorted(notes):      # SPEC17 X12
            out.append(f'<p class="note">{_e(n)}</p>')
    tt = w.get('two_tone')
    if isinstance(tt, dict):
        out.append(f'<p><strong>Two-tone (previous strip edges):</strong> {_txt(tt.get("status"))}'
                   '; band positions '
                   + _e(', '.join(_f(x, 1, 4) for x in tt.get('band_positions_m') or []) or 'none')
                   + ' m.</p>')
    elif 'two_tone' in w:
        out.append('<p><strong>Two-tone:</strong> not supplied (no previous strip widths).</p>')
    if 'grinding_feed_pitch_m' in w:
        g = w.get('grinding_feed_pitch_m')
        out.append('<p><strong>Grinding feed marks:</strong> '
                   + (f'feed pitch {_mm2(g, 4)} (tested against the gaps above).</p>' if _ok(g)
                      else 'not supplied.</p>'))
    ridges = _get(w, 'shape', 'ridges')
    if ridges:
        rows = []
        for x in ridges:
            if 'rejected' in x:
                rows.append([_f(x.get('position_m'), 1, 4, 'm'),
                             f'<em>rejected: {_e(x["rejected"])}</em>', '', '', '', '', ''])
                continue
            c = x.get('coil') or {}
            est = (' (proportional estimate, no bite)'
                   if x.get('transfer_basis') == 'PROPORTIONAL_TRANSFER_LIMIT_NO_BITE' else '')
            rows.append([_f(x.get('position_m'), 1, 4, 'm'), _um(x.get('entry_ridge_height_m')),
                         _um(x.get('exit_ridge_height_m')) + est,
                         _f(x.get('peak_i_units'), digits=3), _txt(x.get('state')),
                         _txt(c.get('status')) if c else 'no coil data',
                         _f(c.get('ridge_to_critical_ratio'), digits=3) if c else 'n/a'])
        out.append('<h3>Incoming ridges and coil build-up</h3>'
                   + _table(('position', 'entry ridge', 'exit ridge', 'flatness [I]',
                             'in-mill state', 'coil build-up', 'ridge / critical (outer wrap)'),
                            rows, 'num'))
    elif ridges is not None:
        out.append('<p><strong>Incoming ridges:</strong> none supplied.</p>')
    cr = _get(w, 'shape', 'crown')
    if isinstance(cr, dict):
        if _bad(cr):
            out.append(_state_p('Crown: ' + _bad(cr)))
        else:
            win = cr.get('shohet_townsend_window') or {}
            out.append(f'<p><strong>Crown:</strong> healthy-header thermal crown '
                       f'{_um(cr.get("healthy_thermal_crown_m"))}; Shohet–Townsend flatness '
                       f'window {_f(win.get("lower_bound_i_units"), digits=3)} to '
                       f'{_f(win.get("upper_bound_i_units"), digits=3)} I-units at this gauge; '
                       'profile heredity '
                       + (_e(cr['heredity_status']) if cr.get('heredity_status')
                          else _txt(cr.get('classification'))) + '.</p>')
    fails = w.get('failures') or []
    if fails:
        out.append('<p class="warn">Parts of the width model failed: '
                   + _e('; '.join(str(f) for f in fails)) + '</p>')
    return ''.join(out)


def _width_section(r):
    w = r.get('width')
    head = '<section><h2>Across the width: predicted against observed bands</h2>'
    if _bad(w):
        return head + _state_p(_bad(w)) + '</section>'
    ts = w.get('thermal_steady')
    sc = w.get('shape_chain')
    pre = ''
    if isinstance(sc, dict) and sc.get('status') == 'NOT_ASSESSABLE':
        pre = ('<p class="warn">Strip-shape chain not assessable: '
               + _e(sc.get('reason') or 'no reason given') + '. Thickness transfer, flatness, '
               'band states, onset heights and the case-pass gauge trend are not computed; '
               'troughs, coil ridges, positions and pitches below need no bite and are '
               'evaluated.</p>')
    elif isinstance(sc, dict) and sc.get('basis') == 'shape_inputs_supplied':
        pre = ('<p class="note">Strip-shape chain from SUPPLIED shape inputs (not verified by '
               'the tool): ' + _e(sc.get('provenance') or 'no provenance given') + '.</p>')
    if not isinstance(ts, dict) or _bad(ts) or not ts.get('z_m'):
        body = pre + _state_p('Steady roll thermal solution ' + (_bad(ts) or 'not available'))
    else:
        st = _get(w, 'shape', 'steady')
        intro = ('<p>Upper panel: steady roll radius growth with the actual spray header and '
                 'with a healthy header, nozzle positions on the axis. Lower panel, same x '
                 'axis: flatness of the exit strip at three levels of the strip-shape chain. '
                 'Dashed vertical lines: the observed band positions. The thick line is the '
                 'level with the exit-tension feedback (linear, before saturation); the rigid '
                 'and compliance-only curves are bounds and run off the scale.')
        if isinstance(st, dict) and not _bad(st):
            lin = st.get('linear_feedback_peak_i_units')
            intro += ((f' Peak flatness {_f(lin, digits=3)} I-units with linear feedback'
                       if _ok(lin) else
                       f' Peak flatness {_f(st.get("feedback_peak_i_units"), digits=4)} I-units '
                       'with feedback')
                      + f' (bounds: {_f(st.get("compliance_only_peak_i_units"), digits=4)} '
                      f'compliance only, {_f(st.get("rigid_transfer_bound_i_units"), digits=4)} '
                      f'rigid); status {_txt(st.get("status"))}.'
                      + (f' The rigid curve is omitted: {_e(st["rigid_level_reason"])}.'
                         if st.get('rigid_level_reason') else ''))
        intro += '</p>'
        body = pre + intro + _wide(_width_chart(r))
        if isinstance(st, dict) and _bad(st):
            body += _state_p('Flatness (shape chain) ' + _bad(st))
        if isinstance(st, dict) and not _bad(st):
            body += _shape_notes(st)
        body += ('<h3>Steady stripes</h3>' + _stripe_table(w) + _ripple_line(w))
    pos = w.get('positions')
    if isinstance(pos, dict) and not _bad(pos):
        body += _match_tables(pos)
    else:
        body += _state_p('Position match ' + (_bad(pos) or 'not available'))
    body += _other_width_results(w)
    return head + body + '</section>'


# ------------------------------------------------------------------------------ short-lived bands
def _visible(e):
    """(threshold [m], start, end, colour, visible time) of the visible band, or None."""
    basis = e.get('visible_time_basis')
    name, colour = {'manifest_after_tension_release': ('released', C_COMP),
                    'above_reporting_threshold_only': ('reporting', C_HEALTHY)}.get(
                        basis, ('manifest', C_THR))
    thr = e.get(f'{name}_threshold_m')
    t_on = e.get(f'time_to_{name}_threshold_s')
    if not (_ok(thr) and _ok(t_on)):
        return None
    fade = e.get(f'fade_time_below_{name}_threshold_s')
    t_off = (e.get('duration_s') or 0.0) + fade if _ok(fade) else None
    above = e.get('visible_time_s', e.get(f'time_above_{name}_threshold_s'))
    return thr, t_on, t_off, colour, above


def _event_chart(e, k):
    h = e.get('history') or {}
    ts = h.get('time_s') or []
    ys = [v * 1e6 if _ok(v) else None for v in h.get('radius_deviation_m') or []]
    if len(ts) < 2 or not any(_ok(v) for v in ys):
        return '<p>No history recorded for this event.</p>'
    dur = e.get('duration_s') or 0.0
    life = e.get('band_life_s') or e.get('band_life_lower_bound_s') or 0.0
    xmax = min(ts[-1], max(2.5 * max(dur, life), dur * 1.5, ts[1] * 10))
    sel = [(t, v) for t, v in zip(ts, ys) if _ok(v) and t <= xmax * 1.0001]
    thr = [('manifest_threshold_m', 'in-mill manifest threshold', C_THR, '4 2')]
    if _ok(e.get('released_threshold_m')):
        thr.append(('released_threshold_m', 'after-release threshold', C_COMP, '9 3 2 3'))
    vals = [v for _, v in sel] + [e[k_] * 1e6 for k_, *_ in thr if _ok(e.get(k_))] + [0.0]
    key = [(f'radius deviation at {_f(e.get("monitor_position_m"), 1, 4)} m', C_ACT, '',
            'line'),
           (f'event interval ({_f(dur)} s, nozzles off / reduced)'
            + (f'; band life {_f(life, digits=3)} s from the event start' if _ok(life) and life
               else ''), '#fde7d4', '', 'band')]
    for k_, label, colour, dash in thr:
        if _ok(e.get(k_)):
            lim = (k_ == 'released_threshold_m'
                   and e.get('released_threshold_limited_by_reporting_threshold'))
            key.append((f'{label} {_um(e[k_])}'
                        + (' (set by the 2 I-unit reporting threshold)' if lim else ''),
                        colour, dash, 'line'))
    vis = _visible(e)
    if vis:
        basis = VISIBLE_BASIS.get(e.get('visible_time_basis'), 'above the threshold')
        key.append((f'visible: {basis}', vis[3], '', 'thick'))
    c = _Chart2(f'Event {k + 1}: radius deviation against time', key, 280)
    c.axes(_Axis(0.0, xmax, ML, W - MR), _Axis(min(vals) * 1.1, max(vals) * 1.18, c.h - MB,
                                               c.mt),
           'time from the event start [s]', 'radius deviation [µm]')
    c.inner.append(f'<rect x="{c.x(0):.1f}" y="{c.mt}" width="{c.x(dur) - c.x(0):.1f}" '
                   f'height="{c.h - MB - c.mt}" fill="#fde7d4"/>')
    for k_, label, colour, dash in thr:
        v = e.get(k_)
        if not _ok(v):
            continue
        py = c.y(v * 1e6)
        c.inner.append(f'<line x1="{ML}" y1="{py:.1f}" x2="{W - MR}" y2="{py:.1f}" '
                       f'stroke="{colour}" stroke-width="1.6" stroke-dasharray="{dash}"/>')
    c.poly(sel, C_ACT, '', 2.4)
    # time the band is visible: bracket on the threshold that defines it
    if vis:
        thr_m, t_on, t_off, colour, above = vis
        py = c.y(thr_m * 1e6)
        t_off = t_off if _ok(t_off) else xmax
        c.inner.append(f'<line x1="{c.x(t_on):.1f}" y1="{py:.1f}" '
                       f'x2="{c.x(min(t_off, xmax)):.1f}" y2="{py:.1f}" stroke="{colour}" '
                       'stroke-width="5" opacity="0.55"/>')
        for t in (t_on, t_off):
            if t <= xmax:
                c.inner.append(f'<circle cx="{c.x(t):.1f}" cy="{py:.1f}" r="4" '
                               f'fill="{colour}" stroke="#111" stroke-width="0.6"/>')
        if _ok(above):
            c.inner.append(f'<text x="{c.x((t_on + min(t_off, xmax)) / 2):.1f}" '
                           f'y="{py + 17:.1f}" text-anchor="middle" class="lab" '
                           f'fill="{colour}">visible {_e(_f(above, digits=3))} s</text>')
    tp, pk = e.get('time_of_peak_s'), e.get('peak_deviation_m')
    if _ok(tp) and _ok(pk) and tp <= xmax:
        c.inner.append(f'<text x="{c.x(tp) + 6:.1f}" y="{c.y(pk * 1e6) - 6:.1f}" class="lab" '
                       f'fill="{C_ACT}">peak {_e(_um(pk))}</text>')
    note = ''
    if ts[-1] > xmax:
        note = (f'<p class="note">Time axis cut at {_f(xmax, digits=3)} s; the simulated trace '
                f'runs to {_f(ts[-1], digits=4)} s and ends at {_um(h["radius_deviation_m"][-1])}.'
                '</p>')
    return _wide(c.render(f'ev{k}')) + note


def _beyond(e):
    if 'FADE_BEYOND_ATTRIBUTION_WINDOW' in (e.get('flags') or []):
        return (f'not attributable after {_f(e.get("attribution_window_end_s"), digits=4)} s: '
                'a later event switches nozzles in the same neighbourhood')
    return 'fades beyond the run'


def _stripes_text(e):
    st = e.get('stripes') or []
    return '; '.join(f'{"governing: " if s.get("governing") else ""}'
                     f'{", ".join("#" + str(i) for i in s.get("nozzle_indices") or [])} at '
                     f'{_f(s.get("monitor_position_m"), 1, 4)} m, peak '
                     f'{_um(s.get("peak_deviation_m"))} at {_f(s.get("time_of_peak_s"), unit="s")}'
                     for s in st) or 'n/a'


def _event_table(events):
    def nozz(e):
        ids = ', '.join(f'#{i}' for i in e.get('nozzle_indices') or [])
        ps = ', '.join(_f(x, 1, 4) for x in e.get('nozzle_positions_m') or [])
        return f'{_e(ids)} at {_e(ps)} m, level {_f(e.get("level"))}'

    def rate(e, k):
        return _f(e.get(k), 1e6, 3, 'µm/s')

    def life(e):
        if _ok(e.get('band_life_s')):
            return (f'<strong>{_f(e["band_life_s"], digits=3)} s</strong> '
                    f'({_e(e.get("band_life_basis") or "")} threshold)')
        if _ok(e.get('band_life_lower_bound_s')):
            return f'> {_f(e["band_life_lower_bound_s"], digits=3)} s ({_beyond(e)})'
        return 'no band (threshold not reached)'
    def visible(e):
        v = e.get('visible_time_s')
        if _ok(v):
            return (f'<strong>{_f(v, digits=3)} s</strong> '
                    f'({_e(VISIBLE_BASIS.get(e.get("visible_time_basis"), "basis not given"))})')
        if _ok(e.get('visible_time_lower_bound_s')):
            return f'> {_f(e["visible_time_lower_bound_s"], digits=3)} s ({_beyond(e)})'
        return 'not visible' if 'visible_time_s' in e else 'n/a'

    def opt(k, unit='s'):
        return lambda e: (_f(e.get(k), unit=unit) if _ok(e.get(k)) else
                          'not reached' if k.startswith('time_to') else 'n/a')
    rows = [('start in the timeline', lambda e: _f(e.get('start_s'), unit='s')),
            ('nozzles', nozz),
            ('duration', lambda e: _f(e.get('duration_s'), unit='s')),
            ('initial growth rate, analytic',
             lambda e: rate(e, 'analytic_initial_growth_rate_m_s')),
            ('initial growth rate, simulated',
             lambda e: rate(e, 'simulated_initial_growth_rate_m_s')
             + f' (first {_f(e.get("initial_rate_window_s"))} s)'),
            ('peak radius deviation', lambda e: _um(e.get('peak_deviation_m'))
             + f' at {_f(e.get("time_of_peak_s"), unit="s")}')]
    if any(len(e.get('stripes') or []) > 1 for e in events):
        rows.append(('stripes (one monitor per group of adjacent nozzles)', _stripes_text))
    if any(e.get('flags') for e in events):
        rows.append(('attribution flags',
                     lambda e: _e(', '.join(e.get('flags') or []) or 'none')))
    rows += [('time to half peak', lambda e: _f(e.get('time_to_half_peak_s'), unit='s')),
             ('in-mill manifest threshold', lambda e: _onset_um(e, 'manifest_threshold_m')),
             ('time to the in-mill threshold',
              lambda e: _f(e.get('time_to_manifest_threshold_s'), unit='s')
              if _ok(e.get('time_to_manifest_threshold_s')) else 'not reached')]
    if any('released_threshold_m' in e for e in events):
        rows += [('after-release threshold',
                  lambda e: _onset_um(e, 'released_threshold_m')
                  + (' (set by the reporting threshold)'
                     if e.get('released_threshold_limited_by_reporting_threshold') else '')),
                 ('time to the after-release threshold', opt('time_to_released_threshold_s'))]
        if any('time_above_released_threshold_s' in e for e in events):
            rows += [('time above the after-release threshold',
                      opt('time_above_released_threshold_s')),
                     ('fade time after the event (below after-release threshold)',
                      opt('fade_time_below_released_threshold_s'))]
    rows += [('reporting threshold (2 I-units)', lambda e: _um(e.get('reporting_threshold_m'))),
             ('time to the reporting threshold',
              lambda e: _f(e.get('time_to_reporting_threshold_s'), unit='s')
              if _ok(e.get('time_to_reporting_threshold_s')) else 'not reached'),
             ('fade time after the event (below in-mill threshold)',
              lambda e: _f(e.get('fade_time_below_manifest_threshold_s'), unit='s')
              if _ok(e.get('fade_time_below_manifest_threshold_s')) else 'n/a'),
             ('time above the in-mill threshold',
              lambda e: _f(e.get('time_above_manifest_threshold_s'), unit='s')),
             ('band life (from the event start)', life),
             ('visible time', visible),
             ('state at peak, in the mill (with feedback)',
              lambda e: _short(e.get('peak_state_with_feedback')))]
    if any('peak_state_after_tension_release' in e for e in events):
        rows.append(('state at peak, after tension release',
                     lambda e: _short(e.get('peak_state_after_tension_release'))
                     if e.get('peak_state_after_tension_release') else 'n/a'))
    rows += [('flatness at peak, rigid / compliance / feedback [I]',
              lambda e: ' / '.join(_f(_get(e, 'peak_stripe_states', lv, 'peak_i_units'),
                                      digits=4)
                                   for lv in ('rigid', 'compliance_only', 'with_feedback'))),
             ('local cooling before / during',
              lambda e: f'{_f(e.get("local_htc_before_w_m2k"), digits=4)} / '
                        f'{_f(e.get("local_htc_during_w_m2k"), digits=4)} W/(m²K)')]
    body = []
    for label, fn in rows:
        cells = []
        for e in events:
            if 'shape_error' in e and label.startswith('state'):
                word = ('not assessable' if 'NOT_ASSESSABLE' in str(e['shape_error'])
                        else 'shape failed')
                cells.append(f'<em>{word}: {_e(e["shape_error"])}</em>')
            else:
                cells.append(fn(e))
        body.append([_e(label)] + cells)
    return _table(['quantity'] + [f'event {k + 1}' + (f': {_e(e["label"])}' if e.get('label')
                                                      else '')
                                  for k, e in enumerate(events)], body,
                  'num wrapall')


def _events_section(r):
    head = '<section><h2>Short-lived bands (cooling-zone switching events)</h2>'
    w = r.get('width')
    if _bad(w):
        return head + _state_p(_bad(w)) + '</section>'
    te = w.get('thermal_events')
    if not isinstance(te, dict) or _bad(te):
        return head + _state_p(_bad(te) or 'not available') + '</section>'
    events = te.get('events') or []
    obs = _get(r, 'inputs', 'observation') or {}
    out = ['<p>A spray zone switched off (or down) heats the roll locally; the band appears '
           'when the stripe crosses the threshold for a manifest buckle and disappears after '
           'the zone returns, once the stripe falls below it again. '
           f'{_e(te.get("band_life_definition") or "")}'
           + (f' {_e(te["visible_time_definition"])}' if te.get('visible_time_definition')
              else '') + '</p>']
    seen = []
    if _ok(obs.get('intermittent_duration_s')):
        seen.append(f'observed short-lived band duration '
                    f'<strong>{_f(obs["intermittent_duration_s"], digits=3)} s</strong>')
    if obs.get('lengthwise_continuity'):
        seen.append(f'lengthwise continuity: {_e(obs["lengthwise_continuity"])}')
    if seen:
        out.append('<p>Observation: ' + '; '.join(seen) + '.</p>')
    if not events:
        out.append('<p>No events.</p>')
    for k, e in enumerate(events):
        lab = f': {_e(e["label"])}' if e.get('label') else ''
        out.append(f'<h3>Event {k + 1}{lab} (nozzles '
                   f'{_e(", ".join("#" + str(i) for i in e.get("nozzle_indices") or []))}, '
                   f'{_f(e.get("duration_s"))} s)</h3>' + _event_chart(e, k))
        if e.get('neighbour_bands_text'):
            out.append(f'<p class="note">{_e(e["neighbour_bands_text"])}</p>')
    if events:
        out.append(_event_table(events))
    for name, label in (('growth_rate_note', 'Why the band appears within seconds'),
                        ('open_discrepancy', 'Open discrepancy')):
        if te.get(name):
            out.append(f'<p><strong>{_e(label)}.</strong> {_e(te[name])}</p>')
    return head + ''.join(out) + '</section>'


# ------------------------------------------------------------------------------ thin gauge
ONSET_SERIES = (
    # key, label, colour, dash, marker, key of the "limited by the reporting threshold" flag
    ('manifest_onset_stripe_height_m', 'in the mill, model stripe', C_FB, '', 'o', None),
    ('released_onset_stripe_height_m', 'after tension release, model stripe', C_FB, '2 3', 'o',
     'released_onset_limited_by_reporting_threshold'),
    ('manifest_onset_height_reference_m', 'in the mill, Gaussian reference', C_ACT, '7 4', 's',
     None),
    ('released_onset_height_reference_m', 'after tension release, Gaussian reference', C_ACT,
     '9 3 2 3', 's', 'released_onset_reference_limited_by_reporting_threshold'),
    ('reporting_onset_stripe_height_m', 'to reach 2 I-units (reporting), model stripe',
     '#6b7280', '1 3', '', None))


def _gauge_charts(rows, ref_peak=None):
    # thick -> thin by exit gauge; a not-credible extended-domain bite carries no trend line
    ok = sorted((x for x in rows if 'rejected' not in x and _ok(x.get('exit_thickness_m'))
                 and x.get('bite_credibility') != NOT_CREDIBLE),
                key=lambda x: -x['exit_thickness_m'])
    if len(ok) < 2:
        return ''
    hs = [x['exit_thickness_m'] * 1e3 for x in ok]
    xa = _Axis(min(hs) / 1.3, max(hs) * 1.3, ML, W - MR, log=True)
    series = [x for x in ONSET_SERIES if any(_ok(r.get(x[0])) for r in ok)]
    out = []
    vals = [x[k] * 1e6 for k, *_ in series for x in ok if _ok(x.get(k)) and x[k] > 0]
    ref = abs(ref_peak) * 1e6 if _ok(ref_peak) and ref_peak else None
    limited = any(x.get(lk) for *_, lk in series if lk for x in ok)
    if vals:
        key = [(lab, col, d, 'thick' if not d else 'line') for _, lab, col, d, _m, _l in series]
        if ref:
            key.append((f'model stripe peak {_f(ref)} µm: a band where it lies above a curve',
                        C_OBS, '3 3', 'line'))
            vals.append(ref)
        if limited:
            key.append(('hollow marker: limited by the reporting threshold (upper bound)',
                        '#ffffff', '', 'hollow'))
        c = _Chart2('Stripe height needed for a band against exit gauge', key, 330)
        c.axes(xa, _Axis(min(vals) / 1.5, max(vals) * 2.6, c.h - MB, c.mt, log=True),
               'exit gauge [mm] (log scale)', 'stripe height for a band [µm] (log)')
        if ref:
            c.inner.append(f'<line x1="{ML}" y1="{c.y(ref):.1f}" x2="{W - MR}" '
                           f'y2="{c.y(ref):.1f}" stroke="{C_OBS}" stroke-width="1.6" '
                           'stroke-dasharray="3 3"/>')
        _pass_labels(c, ok)
        for k, lab, col, d, mk, lk in series:
            pts = [(x['exit_thickness_m'] * 1e3, x[k] * 1e6, bool(lk and x.get(lk)))
                   for x in ok if _ok(x.get(k)) and x[k] > 0]
            if len(pts) > 1:
                c.poly([(a, b) for a, b, _ in pts], col, d, 2.4 if not d else 1.8)
            for a, b, lim in pts:
                fill = '#fff' if lim else col
                if mk == 'o':
                    c.inner.append(f'<circle cx="{c.x(a):.1f}" cy="{c.y(b):.1f}" r="4.5" '
                                   f'fill="{fill}" stroke="{col}" stroke-width="2"/>')
                elif mk == 's':
                    c.inner.append(f'<rect x="{c.x(a) - 4.5:.1f}" y="{c.y(b) - 4.5:.1f}" '
                                   f'width="9" height="9" fill="{fill}" stroke="{col}" '
                                   'stroke-width="2"/>')
        out.append(_wide(c.render('onset')))
        if limited:
            out.append('<p class="note">Hollow markers: the after-release onset there is set by '
                       'the 2 I-unit reporting threshold (a band must first be reported), so '
                       'those heights are upper bounds of the buckling onset; the stripe would '
                       'buckle after tension release at a lower height.</p>')
    iser = [('linear_feedback_i_units', 'with feedback, linear (unsaturated)', C_FB, '', 'thick'),
            ('feedback_i_units', 'with feedback, saturated (indicative only)', C_FB, '2 3',
             'line'),
            ('compliance_only_i_units', 'compliance only', C_COMP, '9 3 2 3', 'line'),
            ('shohet_townsend_half_width_i_units', 'Shohet–Townsend half-width (dead band)',
             C_THR, '7 4', 'line')]
    vals = [x[k] for k, *_ in iser for x in ok if _ok(x.get(k)) and x[k] > 0]
    if vals:
        c = _Chart2('Flatness of the same roll stripe and the flatness dead band against gauge',
                   [(lab, col, d, kind) for _, lab, col, d, kind in iser], 300)
        c.axes(xa, _Axis(min(vals) / 1.6, max(vals) * 2.8, c.h - MB, c.mt, log=True),
               'exit gauge [mm] (log scale)', 'I-units (log)')
        _pass_labels(c, ok)
        for k, lab, col, d, kind in iser:
            pts = [(x['exit_thickness_m'] * 1e3, x[k]) for x in ok if _ok(x.get(k)) and x[k] > 0]
            if len(pts) > 1:
                c.poly(pts, col, d, 3.2 if kind == 'thick' else 2.0)
            for a, b in pts:
                c.inner.append(f'<circle cx="{c.x(a):.1f}" cy="{c.y(b):.1f}" r="3.2" '
                               f'fill="{col}"/>')
        out.append(_wide(c.render('gaugei')))
    return ''.join(out)


def _pass_labels(c, rows):
    """Short pass names (first word of the label) along the top of a gauge chart."""
    items = [(c.x(x['exit_thickness_m'] * 1e3), str(x.get('label', '')).split(' ')[0][:8])
             for x in rows]
    for tx, ty, anc, text in _place_labels(items, (c.mt + 13,), char_w=6.4):
        c.inner.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" class="small">'
                       f'{_e(text)}</text>')


GAUGE_HEADING = 'How the result changes with gauge'
ONSET_SEARCH_CEILING_M = 50e-6   # band_width.ONSET_SEARCH_MAX_M: onsets are searched up to it
NOT_CREDIBLE = 'FORCE_OUTSIDE_REPORTED_RANGE'
GAUGE_TREND_TOL = 1.1   # thin/thick onset ratio within 1/1.1 .. 1.1: "roughly unchanged"


def _onset_direction(ok, key, limited_key):
    """(phrase, sign) for one onset column across the assessable passes, thick -> thin.
    sign: -1 falls toward the thin pass, +1 rises, 0 roughly unchanged, None not stated."""
    vals = [x.get(key) for x in ok]
    above = []
    if not all(_ok(v) and v > 0 for v in vals):
        # SPEC12 stage A: an onset not reached on the THIN end of the assessable passes lies
        # above the engine's 50 um search ceiling (a lower bound); anything else is not stated
        n = len(vals)
        while n and not (_ok(vals[n - 1]) and vals[n - 1] > 0):
            n -= 1
        if n < 1 or n == len(vals) or not all(_ok(v) and v > 0 for v in vals[:n]):
            return 'is not stated (not reached on every assessable pass)', None
        if any(_ok(x.get(key[:-2] + '_domain_limit_m')) for x in ok[n:]):
            # the search ended at the feedback model's domain, not at the ceiling: no bound
            return ('is not stated (on ' + ', '.join(str(x.get('label', '')) for x in ok[n:])
                    + ' the search ended where the feedback model leaves its domain)'), None
        above = [str(x.get('label', '')) for x in ok[n:]]
        vals = vals[:n] + [ONSET_SEARCH_CEILING_M] * (len(vals) - n)
    a, b = vals[0], vals[-1]
    lim = [bool(limited_key and x.get(limited_key)) for x in ok]
    ua = ('≤ ' if lim[0] else '') + _um(a)
    ub = ('≤ ' if lim[-1] else '') + _um(b)
    q = b / a
    steps = [y / x for x, y in zip(vals, vals[1:])]
    if q < 1 / GAUGE_TREND_TOL:
        sign, verb = -1, 'falls'
        every = all(t < 1 for t in steps)
    elif q > GAUGE_TREND_TOL:
        sign, verb = 1, 'rises'
        every = all(t > 1 for t in steps)
    else:
        return f'is roughly unchanged ({ua} to {ub}, x{_f(q, digits=2)})', 0
    note = ('on every pass' if every else 'overall, not on every pass') if len(vals) > 2 else ''
    if any(lim):
        note += ('; ' if note else '') + 'reporting-threshold upper bounds'
    if above:
        ub = f'above {_um(ONSET_SEARCH_CEILING_M)}'
        note += (('; ' if note else '') + 'not reached within the '
                 f'{_um(ONSET_SEARCH_CEILING_M)} search on ' + ', '.join(above))
        return (f'{verb} from {ua} to {ub} (x{_f(q, digits=2)} or more'
                f'{", " + note if note else ""})', sign)
    return f'{verb} from {ua} to {ub} (x{_f(q, digits=2)}{", " + note if note else ""})', sign


def gauge_direction(g):
    """Public name (SPEC16) of the gauge-direction sentence: one sentence on the direction of
    the gauge trend for this case, from the ``width.gauge_trend`` rows ``g``."""
    return _gauge_direction(g)


def _gauge_direction(g):
    """One sentence on the direction of the gauge trend for this case, from the rows."""
    rows = [x for x in g.get('rows') or [] if isinstance(x, dict)]
    ok = sorted((x for x in rows if 'rejected' not in x and _ok(x.get('exit_thickness_m'))
                 and x.get('bite_credibility') != NOT_CREDIBLE),
                key=lambda x: -x['exit_thickness_m'])     # thick -> thin by exit gauge
    bad = [str(x.get('label', '')) for x in rows if 'rejected' in x]
    tail = (' Not assessable (excluded from the direction): ' + ', '.join(bad) + '.') if bad else ''
    nc = [x for x in rows if x.get('bite_credibility') == NOT_CREDIBLE]
    if nc:
        # SPEC12 B: an extended-domain bite with a force outside the reported battery-foil
        # range carries no trend; the row stays in the table
        tail += (' Not credible (excluded from the direction): '
                 + '; '.join(f'{x.get("label", "")} (extended-domain bite force '
                             f'{_f(x.get("separating_force_per_width_n_m"), 1e-6, 3)} kN/mm, '
                             f'x{_f(x.get("bite_force_ratio_to_reported_range"), digits=2)} '
                             'the nearer end of the 0.9-2.3 kN/mm reported for battery-foil '
                             'passes)' for x in nc) + '.')
    if len(ok) < 2:
        return 'Fewer than two assessable passes: no gauge direction stated.' + tail
    mill, sm = _onset_direction(ok, 'manifest_onset_stripe_height_m', None)
    rel, sr = _onset_direction(ok, 'released_onset_stripe_height_m',
                               'released_onset_limited_by_reporting_threshold')
    signs = {sm, sr}
    if signs == {-1}:
        verdict = 'thinner is worse for this mechanism in the model'
    elif signs == {1}:
        verdict = 'thinner is less sensitive for this mechanism in the model'
    elif signs == {0}:
        verdict = 'gauge makes little difference for this mechanism in the model'
    elif None in signs:
        verdict = 'the direction is not fully determined'
    else:
        verdict = 'the direction is mixed for this mechanism in the model'
    a, b = ok[0], ok[-1]
    return (f'Direction for this case (model stripe, thick to thin, {a.get("label", "")} to '
            f'{b.get("label", "")}): the in-mill onset stripe height {mill}, and the '
            f'after-release onset {rel}; {verdict}.' + tail)


def _gauge_section(r):
    head = f'<section><h2>{GAUGE_HEADING}</h2>'
    w = r.get('width')
    if _bad(w):
        return head + _state_p(_bad(w)) + '</section>'
    g = w.get('gauge_trend')
    if not isinstance(g, dict) or _bad(g):
        return head + _state_p(_bad(g) or 'not available') + '</section>'
    rows = g.get('rows') or []
    ref_desc = g.get('reference_stripe_description') or g.get('onset_50mm_reference_basis')
    out = [f'<p class="lead">{_e(_gauge_direction(g))}</p>',
           f'<p>{_e(g.get("text") or "")}</p>']
    if g.get('own_stripe_text'):
        out.append(f'<p><strong>The stripe each pass would produce itself.</strong> '
                   f'{_e(g["own_stripe_text"])}</p>')
    if g.get('bite_free_text'):
        out.append(f'<p><strong>Bite-free thresholds.</strong> {_e(g["bite_free_text"])}</p>')
    out += [
           f'<p class="note">Model stripe: {_e(g.get("reference_stripe_basis") or "n/a")} '
           f'(peak {_um(g.get("reference_stripe_peak_m"))} at '
           f'{_f(g.get("reference_stripe_position_m"), 1, 4)} m). Reference stripe: '
           f'{_e(ref_desc or "n/a")}.</p>']
    out.append(_gauge_charts(rows, g.get('reference_stripe_peak_m')))

    def onset(x, k, lk=None):
        v = _onset_um(x, k)
        return ('≤ ' + v + ' (limited)') if lk and x.get(lk) else v
    cols = [('in the mill', lambda x: _short(x.get('state'))
             + (' (feedback saturated)' if x.get('saturated') else '')),
            ('after tension release', lambda x: _short(x.get('state_after_tension_release'))
             if x.get('state_after_tension_release') else 'n/a'),
            ('utilisation mill / released',
             lambda x: f'{_util(x.get("buckling_utilisation"))} / '
                       f'{_util(x.get("released_buckling_utilisation"))}')]
    short = {'manifest_onset_stripe_height_m': 'onset in mill, model',
             'released_onset_stripe_height_m': 'onset released, model',
             'manifest_onset_height_reference_m': 'onset in mill, Gaussian',
             'released_onset_height_reference_m': 'onset released, Gaussian',
             'reporting_onset_stripe_height_m': '2 I-units, model'}
    for k, lab, *_r, lk in ONSET_SERIES:
        if any(k in x for x in rows):
            cols.append((short.get(k, lab), lambda x, k=k, lk=lk: onset(x, k, lk)))
    if any('reporting_onset_height_reference_m' in x for x in rows):
        cols.append(('2 I-units, Gaussian',
                     lambda x: _um(x.get('reporting_onset_height_reference_m'))))
    cols += [('linear feedback [I]', lambda x: '<strong>' + _f(x.get('linear_feedback_i_units'),
                                                               digits=3) + '</strong>'),
             ('saturated feedback [I] (indicative)',
              lambda x: _f(x.get('feedback_i_units'), digits=3) if x.get('saturated')
              else 'not saturated'),
             ('compliance only [I]', lambda x: _f(x.get('compliance_only_i_units'), digits=4)),
             ('S–T half-width [I]',
              lambda x: _f(x.get('shohet_townsend_half_width_i_units'), digits=3)),
             ('band buckling stress', lambda x: _mpa(x.get('band_buckling_stress_pa'))),
             ('effective buckling width', lambda x: _mm2(x.get('effective_buckling_width_m'))),
             ('critical ridge height (coil)', lambda x: _um(x.get('critical_ridge_height_m')))]
    # bite-free columns: shown for a pass without a roll bite too; the span thresholds exist
    # only for foil-regime cases or schedules with such a pass
    free = {'S–T half-width [I]', 'critical ridge height (coil)'}
    for key, label, fn in (
            ('trough_critical_lateral_stress_exit_span_pa', 'trough onset, exit / entry span',
             lambda x: f'{_f(x.get("trough_critical_lateral_stress_exit_span_pa"), 1e-3, 3)}'
                       f' / {_f(x.get("trough_critical_lateral_stress_entry_span_pa"), 1e-3, 3)}'
                       ' kPa'),
            ('roller_wrinkle_critical_lateral_stress_exit_span_pa',
             'roller-wrinkle threshold, exit / entry span',
             lambda x: _mpa(x.get('roller_wrinkle_critical_lateral_stress_exit_span_pa'))
             + ' / ' + _mpa(x.get('roller_wrinkle_critical_lateral_stress_entry_span_pa')))):
        if any(key in x for x in rows):
            cols.append((label, fn))
            free.add(label)
    body = []
    for x in rows:
        mark = ''
        if x.get('bite_credibility') == NOT_CREDIBLE:
            mark = (' <em>(bite NOT CREDIBLE: force '
                    f'×{_f(x.get("bite_force_ratio_to_reported_range"), digits=2)} outside the '
                    'reported battery-foil range; excluded from the direction)</em>')
        elif x.get('bite_credibility'):
            mark = (' <em>(extended-domain bite: force inside the reported battery-foil range, '
                    'unvalidated)</em>')
        lead = [_e(x.get('label', '')) + mark, _mm2(x.get('exit_thickness_m')),
                _mpa(x.get('exit_tension_pa'))]
        if 'rejected' in x:
            cells, first = [], True
            for name, fn in cols:
                if name in free:
                    cells.append(fn(x))
                elif first:
                    cells.append(f'<em>no roll-bite result: {_e(x["rejected"])}</em>')
                    first = False
                else:
                    cells.append('<em>no roll-bite result</em>')
            body.append(lead + cells)
            continue
        body.append(lead + [fn(x) for _, fn in cols])
    out.append(_table(['pass', 'exit gauge', 'exit tension'] + [c for c, _ in cols], body,
                      'num wrapall'))
    out.append('<p class="note">Onset columns: stripe height for a band in the mill and after '
               'tension release, for the model stripe shape and the Gaussian reference; '
               '"2 I-units": height to reach the reporting threshold; "≤ ... (limited)": set by '
               'the reporting threshold, an upper bound. Buckling utilisation is shown only '
               'below 1: above 1 the band has buckled and the feedback saturation inflates the '
               'number.</p>')
    return head + ''.join(out) + '</section>'


# ------------------------------------------------------------------------------ process
def _friction_chart(fc, used=None):
    pts = [(q['exit_speed_m_s'], q['friction_coefficient']) for q in fc.get('points') or []
           if _ok(q.get('exit_speed_m_s')) and _ok(q.get('friction_coefficient'))]
    if len(pts) < 2:
        return ''
    sup = fc.get('supplied_friction_coefficient')
    u_op, mu_op = fc.get('operating_exit_speed_m_s'), fc.get('operating_friction_coefficient')
    key = [('placeholder closure mu(u) (slope is the useful output)', C_FB, '', 'line')]
    if _ok(u_op) and _ok(mu_op):
        key.append((f'closure at the operating speed {_f(u_op)} m/s: {_f(mu_op)}', C_ACT, '',
                    'dot'))
    if _ok(sup):
        key.append((f'supplied friction {_f(sup)}', C_THR, '7 4', 'line'))
    if _ok(used) and _ok(u_op):
        key.append((f'used in the model at the operating speed: {_f(used)}', C_THR, '',
                    'square'))
    c = _Chart2('Friction against exit speed', key, 300)
    ys = [b for _, b in pts] + [v for v in (sup, used) if _ok(v)]
    lo, hi = min(ys), max(ys)
    pad = 0.08 * (hi - lo or 0.01)
    c.axes(_Axis(pts[0][0], pts[-1][0], ML, W - MR, log=True),
           _Axis(max(0.0, lo - pad), hi + pad, c.h - MB, c.mt),
           'exit speed [m/s] (log scale)', 'friction coefficient [-]')
    c.poly(pts, C_FB, '', 2.4)
    if _ok(sup):
        py = c.y(sup)
        c.inner.append(f'<line x1="{ML}" y1="{py:.1f}" x2="{W - MR}" y2="{py:.1f}" '
                       f'stroke="{C_THR}" stroke-width="1.8" stroke-dasharray="7 4"/>')
    if _ok(u_op) and _ok(mu_op):
        c.vline(u_op, '#111', '3 3', f'operating {_f(u_op)} m/s',
                c.mt + 14, 'end' if c.x(u_op) > W / 2 else 'start')
        if _ok(used):
            c.inner.append(f'<rect x="{c.x(u_op) - 5:.1f}" y="{c.y(used) - 5:.1f}" width="10" '
                           f'height="10" fill="{C_THR}" stroke="#111" stroke-width="0.6"/>')
        c.inner.append(f'<circle cx="{c.x(u_op):.1f}" cy="{c.y(mu_op):.1f}" r="5.5" '
                       f'fill="{C_ACT}" stroke="#111" stroke-width="0.8"/>')
    return _wide(c.render('fric'))


def _sub_bad(sec, name):
    b = _bad(sec)
    return _state_p(f'{name} {b}') if b else ''


def _process_section(r):
    head = '<section><h2>Process: friction, flow stress, pass heating</h2>'
    pr = r.get('process')
    out = []
    if _bad(pr):
        out.append(_state_p(_bad(pr)))
    else:
        fc, fr = pr.get('friction_speed_curve'), pr.get('friction')
        out.append('<h3>Friction against speed</h3>')
        if _bad(fc) and _bad(fr):
            out.append(_state_p('Friction ' + _bad(fc)))
        else:
            if not _bad(fc):
                notes = [fc.get('note')] + ([fr.get('note')] if isinstance(fr, dict)
                                            and fr.get('note') else [])
                flags = sorted(set((fc.get('flags') or [])
                                   + ((fr or {}).get('flags') or [] if isinstance(fr, dict)
                                      else [])))
                out.append('<p class="warn"><strong>Placeholder closure.</strong> '
                           + _e(' '.join(n for n in notes if n))
                           + (f' Flags: {_e(", ".join(flags))}.' if flags else '') + '</p>')
                sl = fc.get('mean_slope_per_m_s')
                sp = fc.get('mean_slope_speeds_m_s') or []
                out.append(f'<p>Mean slope {_f(sl, digits=3)} per m/s'
                           + (f' between {_f(sp[0])} and {_f(sp[-1])} m/s' if len(sp) == 2
                              else '') + '.</p>'
                           + _friction_chart(fc, _get(fr, 'operating',
                                                      'used_friction_coefficient')))
            else:
                out.append(_sub_bad(fc, 'Friction-speed curve'))
            if isinstance(fr, dict) and not _bad(fr):
                rows = []
                for x in [fr.get('operating')] + list(fr.get('schedule') or []):
                    if not isinstance(x, dict):
                        continue
                    rows.append([_e(x.get('label', '')), _f(x.get('exit_speed_m_s'), unit='m/s'),
                                 _f(x.get('supplied_friction_coefficient')),
                                 _f(x.get('computed_friction_coefficient')),
                                 f'<strong>{_f(x.get("used_friction_coefficient"))}</strong>',
                                 _txt(x.get('regime')), _f(x.get('film_ratio'), digits=3),
                                 _f(x.get('dmu_dexit_speed_per_m_s'), digits=3)])
                out.append(_table(('pass', 'exit speed', 'supplied', 'closure (placeholder)',
                                   'used', 'regime', 'film ratio Λ', 'dμ/du [1/(m/s)]'),
                                  rows, 'num'))
            else:
                out.append(_sub_bad(fr, 'Friction per pass'))
        fs = pr.get('flow_stress')
        out.append('<h3>Flow stress per pass</h3>')
        if _bad(fs):
            out.append(_state_p(_bad(fs)))
        else:
            law = fs.get('law') or {}
            out.append(f'<p>{_e(fs.get("law_type") or "")} law '
                       f'({_e(law.get("provenance") or "")}); '
                       f'{"computed" if fs.get("use_computed_flow_stress") else "supplied"} '
                       f'values used. {_e(fs.get("note") or "")} Flags: '
                       f'{_e(", ".join(fs.get("flags") or []) or "none")}.</p>')
            rows = [[_e(x.get('label', '')),
                     f'{_mm2(x.get("entry_thickness_m"))} → {_mm2(x.get("exit_thickness_m"))}',
                     f'{_f(x.get("entry_equivalent_strain"))} → '
                     f'{_f(x.get("exit_equivalent_strain"))}',
                     _mpa(x.get('supplied_mean_flow_stress_pa'), 4),
                     _mpa(x.get('computed_mean_flow_stress_pa'), 4),
                     f'<strong>{_mpa(x.get("used_mean_flow_stress_pa"), 4)}</strong>']
                    for x in fs.get('passes') or []]
            out.append(_table(('pass', 'gauge', 'equivalent strain', 'supplied', 'computed',
                               'used'), rows, 'num'))
        he = pr.get('heating')
        out.append('<h3>Pass heating</h3>')
        if _bad(he):
            out.append(_state_p(_bad(he)))
        else:
            out.append(f'<p>{_e(he.get("note") or "")}</p>')
            if he.get('operating_pass_note'):
                out.append(f'<p class="warn">{_e(he["operating_pass_note"])}</p>')
            rows = []
            for x in [he.get('operating')] + list(he.get('schedule') or []):
                if not isinstance(x, dict):
                    continue
                if x.get('rejected'):
                    rows.append([_e(x.get('label', '')), _mm2(x.get('exit_thickness_m')),
                                 _f(x.get('exit_speed_m_s'), unit='m/s'),
                                 f'<em>not assessable: {_e(x["rejected"])}</em>', '', '', '',
                                 '', '', ''])
                    continue
                t = x.get('exit_temperature_k')
                lim = x.get('temperature_limit_k')
                hot = _ok(t) and _ok(lim) and t > lim
                rows.append([_e(x.get('label', '')), _mm2(x.get('exit_thickness_m')),
                             _f(x.get('exit_speed_m_s'), unit='m/s'),
                             _f(x.get('bite_heat_per_width_w_m'), 1e-3, 4, 'kW/m'),
                             _f(x.get('plastic_power_per_width_w_m'), 1e-3, 4, 'kW/m'),
                             _f(x.get('friction_power_per_width_w_m'), 1e-3, 4, 'kW/m'),
                             _f(x.get('strip_temperature_rise_k'), digits=3, unit='K'),
                             ('<strong>' if hot else '') + _f(t, digits=4, unit='K')
                             + (f' ({_f(t - 273.15, digits=3)} °C)' if _ok(t) else '')
                             + (' above limit</strong>' if hot else ''),
                             _f(lim, digits=4, unit='K'),
                             _f(x.get('heat_to_each_work_roll_per_width_w_m'), 1e-3, 4,
                                'kW/m')])
            out.append(_table(('pass', 'exit gauge', 'exit speed', 'bite heat per width',
                               'plastic work', 'interface slip', 'strip temperature rise',
                               'strip exit temperature', 'limit', 'heat to each work roll'),
                              rows, 'num'))
    out.append(_speed_consistent_block(r))
    return head + ''.join(out) + '</section>'


def _speed_consistent_block(r):
    ch = r.get('chatter') or {}
    out = ['<h3>Chatter critical speed with speed-dependent friction</h3>']
    if _bad(ch):
        return ''.join(out) + _state_p('Chatter ' + _bad(ch))
    sc = ch.get('speed_consistent')
    if 'speed_consistent' not in ch:
        out.append(_state_p('not computed by this engine version'))
    elif _bad(sc):
        out.append(_state_p(_bad(sc)))
    else:
        rows = [[f'fixed friction {_f(sc.get("fixed_friction_coefficient"))}',
                 _f(sc.get('fixed_friction_critical_exit_speed_m_s'), digits=4, unit='m/s'),
                 _f(sc.get('fixed_friction_critical_exit_speed_without_bite_damping_m_s'),
                    digits=4, unit='m/s'), ''],
                [f'speed-consistent μ(u), {_f(sc.get("friction_used_at_operating_speed"))} at '
                 'the operating speed',
                 '<strong>' + _f(sc.get('speed_consistent_critical_exit_speed_m_s'), digits=4,
                                 unit='m/s') + '</strong>',
                 _f(sc.get('speed_consistent_critical_exit_speed_without_bite_damping_m_s'),
                    digits=4, unit='m/s'),
                 f'{_txt(sc.get("status"))} / {_txt(sc.get("status_without_bite_damping"))}']]
        beta = sc.get('bite_damping_transit_fraction')
        out.append(_table(('friction', f'critical exit speed, beta = {_f(beta)}',
                           'critical, beta = 0', 'status (beta / 0)'), rows, 'num'))
        low = sc.get('lowest_assessable_exit_speed_m_s')
        if isinstance(low, dict) and low:
            out.append('<p class="warn">Already unstable at the lowest assessable speed ('
                       + _e(', '.join(f'{k.replace("_", " ")}: {_f(v, digits=4, unit="m/s")}'
                                      for k, v in sorted(low.items())))
                       + '): the crossing lies at or below it, and the lower scan speeds have '
                       'no roll bite with the operating bite\'s model.</p>')
        out.append(f'<p class="note">{_e(sc.get("friction_law") or "")} '
                   f'{_e(sc.get("note") or "")}</p>')
    if ch.get('reliability') or _ok(ch.get('span_wave_limit_hz')):
        out.append(f'<p>Model reliability: <strong>{_txt(ch.get("reliability"))}</strong>; '
                   f'span-wave limit {_f(ch.get("span_wave_limit_hz"), digits=4, unit="Hz")} '
                   f'({_e(ch.get("span_wave_limit_basis") or "basis not given")}).</p>')
    return ''.join(out)


# ------------------------------------------------------------------------------ dynamics
def _gc_block(gc):
    out = ['<h3>Gauge control (AGC)</h3>']
    if _bad(gc):
        return out[0] + _state_p(_bad(gc))
    if gc.get('foil_regime_note'):
        out.append(f'<p class="warn">{_e(gc["foil_regime_note"])}</p>')
    inp = gc.get('inputs') or {}
    ff = inp.get('force_filter_hz')
    out.append(f'<p>Loop: bandwidth {_f(inp.get("bandwidth_hz"), unit="Hz")}, compensation '
               f'gain {_f(inp.get("compensation_gain"))}, force filter '
               f'{_f(ff, unit="Hz") if ff is not None else "none"}. '
               f'Eccentricity amplification with the loop against without: '
               f'<strong>×{_f(gc.get("eccentricity_amplification_vs_no_agc"))}</strong>. '
               f'Static numbers: {_e(gc.get("static_formulas_label") or "n/a")}.</p>')
    rows = []
    for dk, label in (('runout', 'roll run-out'), ('entry_thickness', 'incoming thickness')):
        d = gc.get(dk) or {}
        for x in d.get('responses') or []:
            rows.append([_e(label), _txt(x.get('source')), _f(x.get('frequency_hz'), digits=4),
                         _f(x.get('no_agc_exit_thickness_per_unit_disturbance')),
                         _f(x.get('with_agc_exit_thickness_per_unit_disturbance')),
                         f'<strong>{_f(x.get("agc_to_no_agc_magnitude_ratio"))}</strong>'])
    if rows:
        out.append(_table(('disturbance', 'roll order', 'frequency [Hz]',
                           'exit / disturbance, no loop [m/m]', 'with loop [m/m]',
                           'loop / no loop'), rows, 'num'))
    cl = gc.get('chatter_with_loop') or {}
    rows, flag_lines = [], []
    for k, label in (('supplied_loop', 'supplied loop'),
                     ('with_25_hz_force_filter', 'with a 25 Hz force filter')):
        x = cl.get(k)
        if not isinstance(x, dict):
            continue
        if _bad(x):
            rows.append([_e(label), f'<em>{_e(_bad(x))}</em>', '', '', '', ''])
            continue
        rows.append([_e(label), _f(x.get('critical_exit_speed_without_agc_m_s'), digits=4),
                     f'<strong>{_f(x.get("critical_exit_speed_with_agc_m_s"), digits=4)}</strong>',
                     _f(x.get('critical_speed_relative_change'), 100, 3, '%'),
                     _f(x.get('critical_exit_speed_with_agc_without_bite_damping_m_s'), digits=4)
                     + f' ({_txt(x.get("critical_status_with_agc_without_bite_damping"))})',
                     _n(x.get('stable_at_operating_speed'))])
        if x.get('flags'):
            flag_lines.append(f'{_e(label)}: {_e(", ".join(x["flags"]))}')
    if rows:
        out.append('<p><strong>Chatter critical speed with the loop.</strong> '
                   + _e(' '.join(gc.get('limitations') or [])) + '</p>')
        out.append(_table(('loop', 'u_crit, no loop [m/s]', 'u_crit with loop [m/s]', 'change',
                           'with loop, beta = 0 [m/s]', 'stable at operating speed'),
                          rows, 'num'))
        if flag_lines:
            out.append('<p class="note">Flags. ' + '; '.join(flag_lines) + '.</p>')
    sc = gc.get('speed_change_gauge_shift')
    if isinstance(sc, dict) and not _bad(sc):
        out.append(f'<p><strong>Gauge shift for the speed change</strong> '
                   f'{_f(sc.get("from_exit_speed_m_s"))} → {_f(sc.get("to_exit_speed_m_s"))} '
                   f'm/s (friction {_f(sc.get("friction_at_low_speed"))} → '
                   f'{_f(sc.get("friction_at_operating_speed"))}, placeholder closure slope): '
                   f'exit gauge {_um(sc.get("exit_thickness_change_m"))} with the loop, '
                   f'{_um(sc.get("exit_thickness_change_without_agc_m"))} without; separating '
                   f'force {_f(sc.get("separating_force_change_n"), 1e-3, 3, "kN")}.</p>')
    return ''.join(out)


def _drive_block(dr):
    out = ['<h3>Drive train (torsional)</h3>']
    if _bad(dr):
        return out[0] + _state_p(_bad(dr))
    pitch = {x.get('name'): x for x in dr.get('pitch_at_operating_speed_m') or []}
    resp = {}
    for x in _get(dr, 'roll_speed_ripple', 'responses') or []:
        resp[x.get('frequency_hz')] = x
    rows = []
    for m in dr.get('catalogue_modes') or []:
        f = m.get('frequency_hz')
        rr = resp.get(f) or {}
        rows.append([_e(m.get('name', '')), _f(f, digits=4, unit='Hz'),
                     _mm2(_get(pitch, m.get('name'), 'strip_pitch_m'), 4),
                     _f(rr.get('exit_thickness_per_unit_disturbance'), 1e6, 3, 'µm per m/s')])
    if rows:
        out.append(_table(('mode', 'frequency', 'strip pitch at the operating speed',
                           'exit gauge per roll-speed ripple'), rows, 'num'))
    else:
        out.append('<p>No elastic torsional mode.</p>')
    return ''.join(out)


def _incoming_block(iv):
    out = ['<h3>Incoming hardness variation</h3>']
    if _bad(iv):
        return out[0] + _state_p(_bad(iv))
    st = iv.get('static') or {}
    out.append(f'<p>Flow-stress variation amplitude {_mpa(iv.get("flow_stress_amplitude_pa"))}'
               f' ({_f(_get(iv, "inputs", "flow_stress_variation_fraction"), 100, 3, "%")}). '
               f'Static exit-gauge change {_um(st.get("exit_thickness_change_m"))} with the '
               f'loop, {_um(st.get("exit_thickness_change_without_agc_m"))} without '
               f'({_f(st.get("relative_exit_thickness_change"), 100, 3, "%")} of the gauge).</p>')
    cs = iv.get('coil_synchronous')
    if isinstance(cs, dict) and cs.get('harmonics'):
        rows = [[_f(x.get('order')), _f(x.get('frequency_hz'), digits=4, unit='Hz'),
                 _f(x.get('exit_strip_pitch_m'), digits=4, unit='m'),
                 _um(x.get('exit_thickness_amplitude_no_agc_m')),
                 _um(x.get('exit_thickness_amplitude_with_agc_m'))] for x in cs['harmonics']]
        out.append(f'<p>Coil-synchronous (decoiler {_f(cs.get("decoiler_rotation_hz"), digits=4)}'
                   ' Hz):</p>' + _table(('order', 'frequency', 'pitch on the exit strip',
                                         'exit gauge amplitude, no loop', 'with loop'), rows,
                                        'num'))
    return ''.join(out)


def _dynamics_section(r):
    return ('<section><h2>Gauge control, drive and incoming variation</h2>'
            + _gc_block(r.get('gauge_control')) + _drive_block(r.get('drive'))
            + _incoming_block(r.get('incoming_variation')) + '</section>')


# ------------------------------------------------------------------------------ foil regime
CSS3 = ('.foil{border:3px solid #b91c1c;background:#fef2f2;padding:.7rem 1rem;'
        'border-radius:6px;margin:1rem 0}.foil h2{margin-top:.2rem;color:#7f1d1d}'
        '.foil p{margin:.35rem 0}')
BITE_MODEL_NAMES = {'hitchcock': 'slab + circular (Hitchcock) flattening',
                    'experimental_mattress': 'EXPERIMENTAL mattress (elastic-foundation) model',
                    'supplied': 'supplied sensitivities', None: 'no bite'}


def _foil_block(r):
    """SPEC9 9.2: the foil-regime warning, shown near the top of a foil case (exit < 100 um)."""
    fr = r.get('foil_regime')
    if not isinstance(fr, dict):
        return ''
    b = fr.get('bite') or {}
    wr = fr.get('wrinkle_rule') or {}
    pq = fr.get('product_question') or {}
    srcs = []
    for x in fr.get('closed_gap_onset_sources') or []:
        g = (list(x.get('onset_exit_gauge_m') or []) + [None, None])[:2]
        rng = (f'{_um(g[0])} to {_um(g[1])}' if _ok(g[0]) and _ok(g[1]) else
               f'below {_um(g[1])}' if _ok(g[1]) else
               f'from {_um(g[0])}' if _ok(g[0]) else 'n/a')
        srcs.append(f'{_e(x.get("source"))}: {_e(x.get("text"))} [{_e(x.get("tag"))}] '
                    f'({_e(rng)})')
    lo, hi = (fr.get('closed_gap_onset_range_m') or [None, None])[:2]
    fpw = b.get('separating_force_per_width_n_m')
    rng = b.get('reported_battery_foil_load_per_width_n_m') or [None, None]
    inside = b.get('force_per_width_within_reported_range')
    rows = []
    for x in fr.get('schedule_bites') or []:
        rows.append([_e(x.get('label')), _um(x.get('exit_thickness_m')),
                     _e(BITE_MODEL_NAMES.get(x.get('bite_model'), str(x.get('bite_model'))))
                     if not x.get('rejected') else f'<em>rejected: {_e(x["rejected"])}</em>',
                     _f(x.get('separating_force_per_width_n_m'), 1e-6, 3, 'kN/mm')])
    sched = (_table(('pass', 'exit gauge', 'bite model', 'force per width'), rows)
             if rows else '')
    return ('<div class="foil"><h2>Foil gauge: closed-gap rolling likely — not modelled</h2>'
            f'<p><strong>{_e(fr.get("case_position_text") or "")}</strong> Reported onsets of '
            f'closed-gap rolling (work rolls touching outside the strip) range from '
            f'{_um(lo)} to {_um(hi)}; the sources disagree:</p>' + _ul(srcs)
            + '<p><strong>What this means for the results below.</strong></p>'
            + _ul([_e(x) for x in fr.get('implications') or []])
            + f'<p><strong>Bite model for the case pass:</strong> '
            f'{_e(BITE_MODEL_NAMES.get(b.get("model"), str(b.get("model"))))}. '
            f'{_e(b.get("reliability") or "")} Force per width {_f(fpw, 1e-6, 3, "kN/mm")} '
            f'(battery-foil passes are reported at {_f(rng[0], 1e-6, 2)}–'
            f'{_f(rng[1], 1e-6, 2, "kN/mm")} [V S3, S4]; '
            + ('inside' if inside else 'outside' if inside is False else 'not assessed')
            + ').'
            + (f' Forward slip {_f(b.get("forward_slip_fraction"), digits=3)}.'
               if _ok(b.get('forward_slip_fraction')) else '')
            + (f' Hitchcock rejected the pass: {_e(b["fallback_reason"])}.'
               if b.get('fallback_reason') else '')
            + (f' Bite error: {_e(b["bite_error"])}.' if b.get('bite_error') else '')
            + '</p>' + sched
            + (f'<p class="warn"><strong>Extended roll-bite domain.</strong> '
               f'{_e(_get(fr, "extended_bite_domain", "text"))}</p>'
               if _get(fr, 'extended_bite_domain', 'text') else '')
            + (f'<p class="warn"><strong>Below the roll-bite model floor.</strong> '
               f'{_e(_get(fr, "below_bite_model_floor", "text"))}</p>'
               if _get(fr, 'below_bite_model_floor', 'text') else '')
            + f'<p><strong>Wrinkle rule of thumb.</strong> {_e(wr.get("source_rule") or "")} '
            f'At this exit tension ({_mpa(wr.get("exit_tension_pa"))}) the onset is '
            f'<strong>{_f(wr.get("wrinkle_onset_i_units"), digits=3)} I-units</strong>; '
            f'{_e(wr.get("comparison_text") or "")}</p>'
            f'<p><strong>Ask the plant.</strong> {_e(pq.get("text") or "")}</p>'
            '<p class="note">Flags: ' + _e(', '.join(fr.get('flags') or [])) + '. '
            + _e(' '.join(fr.get('limitations') or [])) + '</p></div>')


# ------------------------------------------------------------------------------ product check
PC_WORDS = {'WITHIN_PUBLISHED_RANGE': 'within', 'BELOW_PUBLISHED_RANGE': 'BELOW',
            'ABOVE_PUBLISHED_RANGE': 'ABOVE', 'NO_PUBLISHED_RANGE': 'no published range',
            'INCONSISTENT_WITH_PUBLISHED_MODE': 'INCONSISTENT',
            'ABOVE_PUBLISHED_LIMIT': 'ABOVE LIMIT', 'NOT_ASSESSABLE': 'not assessable'}
PC_ITEMS = ('final_gauge', 'per_pass_reduction', 'final_pass_reduction', 'final_pass_entry_gauge',
            'exit_speed', 'rolled_mode', 'single_sheet_final_gauge', 'alloy', 'temper',
            'mean_flow_stress_indicator')


def _product_block(r):
    """SPEC12 B2: compact product check (verdict words per pass and item, nearest passes)."""
    pc = r.get('product_check')
    head = '<section><h2>Product check (published envelope, literature survey)</h2>'
    if not isinstance(pc, dict):
        return ''
    if pc.get('not_supplied'):
        return (head + _state_p('not supplied: ' + str(pc.get('reason')) + '. Catalogue ids: '
                                + ', '.join(pc.get('product_ids') or [])) + '</section>')
    rows = pc.get('rows') or []
    items = [i for i in PC_ITEMS if any(f.get('item') == i for x in rows
                                         for f in x.get('findings') or [])]
    body = []
    for x in rows:
        by = {f.get('item'): f for f in x.get('findings') or []}
        cells = []
        for i in items:
            f = by.get(i)
            if not f:
                cells.append('–')
                continue
            word = PC_WORDS.get(f.get('verdict'), str(f.get('verdict')))
            cells.append(f'<strong>{_e(word)}</strong>' if word.isupper() else _e(word))
        body.append([_e(x.get('label', '')) + (' <em>(final pass)</em>' if x.get('is_final_pass')
                                               else ''),
                     f'{_um(x.get("entry_thickness_m"))} → {_um(x.get("exit_thickness_m"))}']
                    + cells)
    near = []
    for key, label in (('case_pass', 'case pass'), ('final_pass', 'final pass')):
        lst = _get(pc, 'nearest_published_schedules', key) or []
        txt = '; '.join(f'{_e(n.get("schedule"))} step {_f(n.get("step"))}: '
                        f'{_um(_get(n, "entry_m", 0))} → {_um(_get(n, "exit_m", 0))}'
                        + (' (doubled)' if n.get('doubled') else '')
                        + f' [{_e(n.get("source_read_status") or "")}]' for n in lst)
        near.append(f'<li>{_e(label)}: {txt or "none"}</li>')
    return (head + f'<p>Product <code>{_e(pc.get("product_id"))}</code> '
            f'({_e(pc.get("product_name") or "")}); alloy used {_e(pc.get("alloy_designation_used"))}'
            f', temper {_e(pc.get("temper_used"))}. {_e(pc.get("note") or "")}</p>'
            + _table(['pass', 'gauges'] + [i.replace('_', ' ') for i in items], body, 'wrapall')
            + '<p>Nearest published passes:</p><ul>' + ''.join(near) + '</ul>'
            + '<p class="note">Flags: ' + _e(', '.join(pc.get('flags') or []) or 'none') + '. '
            + _e(' '.join(pc.get('limitations') or [])) + '</p></section>')


MS_WORDS = {'INSIDE_TYPICAL_RANGE': 'inside typical', 'BELOW_STANDARD_MINIMUM':
            'BELOW STANDARD MINIMUM', 'ABOVE_TYPICAL_RANGE': 'above typical',
            'BETWEEN_STANDARD_MINIMUM_AND_TYPICAL_RANGE': 'between minimum and typical',
            'BELOW_TYPICAL_RANGE': 'below typical (no standard minimum)',
            'AT_OR_ABOVE_STANDARD_MINIMUM_NO_TYPICAL_PUBLISHED':
                'at or above minimum (no typical published)',
            'NO_PUBLISHED_VALUE': 'no published value',
            'OUTSIDE_PUBLISHED_BANDS': 'outside the published bands'}


def _mpa_txt(v):
    return _f(v, 1e-6, 3) if _ok(v) else "–"


def _material_block(r):
    """SPEC13 2.6: literature alloy and temper for the final gauge, and the case against it."""
    ms = r.get('material_selection')
    head = '<section><h2>Material selection (literature proposal, to confirm with the plant)</h2>'
    if not isinstance(ms, dict):
        return ''
    if ms.get('status') == 'FAILED':
        return head + _state_p('FAILED: ' + str(ms.get('error'))) + '</section>'
    if ms.get('not_supplied'):
        return (head + _state_p('not supplied: ' + str(ms.get('reason')) + '. '
                                + str(ms.get('hint') or '')) + '</section>')
    opts = ms.get('options') or {}
    rows = []
    for o in opts.get('options') or []:
        lo, hi = (o.get('typical_rm_pa') or [None, None])[:2]
        typ = ('–' if not _ok(lo) and not _ok(hi) else
               f'{_mpa_txt(lo)}–{_mpa_txt(hi)}' if _ok(hi) else f'≥{_mpa_txt(lo)}')
        rows.append([_e(o.get('alloy')), _e(str(o.get('grade', '')).replace('_', '-')),
                     _e('/'.join(o.get('temper_labels') or [])),
                     _mpa_txt(o.get('standard_min_rm_pa')), typ,
                     _e(o.get('usual_for') or '–'), _e(o.get('evidence')),
                     _e(', '.join(o.get('sources') or []))])
    props = []
    for g, p in (ms.get('proposals') or {}).items():
        if p.get('status') != 'LITERATURE_PROPOSAL_TO_CONFIRM_WITH_PLANT':
            props.append(f'<li>{_e(g)}: none ({_e(p.get("reason"))})</li>')
            continue
        t = p.get('tensile_strength_pa') or {}
        lo, hi = (t.get('range_pa') or [None, None])[:2]
        weak = 'no usual choice' in str(p.get('rule'))
        props.append(
            f'<li>{_e(g.replace("_", "-"))}: <strong>{_e(p.get("alloy"))}-{_e(p.get("temper"))}'
            f'</strong>, Rm {_mpa_txt(t.get("value_pa"))} MPa used (range {_mpa_txt(lo)}–'
            f'{_mpa_txt(hi)} MPa), Rp0.2 {_mpa_txt(_get(p, "proof_strength", "value_pa"))} MPa '
            f'({"published" if _get(p, "proof_strength", "published") else "assumed"}); '
            + (f'<strong>evidence WEAK (fallback rule: no usual choice of this grade at this '
               f'gauge)</strong>' if weak else f'evidence {_e(p.get("evidence"))}')
            + f'. Rule: {_e(p.get("rule"))}.</li>')
    cmp_ = ms.get('comparison') or {}
    prow = [[_e(x.get('label')), _um(x.get('exit_thickness_m')), _e(x.get('band_label') or '–'),
             _mpa_txt(x.get('mean_flow_stress_pa')), _e(x.get('option') or '–'),
             _mpa_txt(x.get('standard_min_pa')),
             _e(MS_WORDS.get(x.get('verdict'), str(x.get('verdict'))))]
            for x in cmp_.get('passes') or []]
    ys = cmp_.get('yield_stress') or {}
    fb, cb = ms.get('final_pass_band') or {}, ms.get('case_pass_band') or {}
    return (head + f'<p>{_e(ms.get("sentence"))}</p>'
            + f'<p>Final pass {_e(ms.get("final_pass_label"))} '
              f'({_um(ms.get("final_exit_thickness_m"))}): band {_e(fb.get("band_label") or fb.get("reason"))}; '
              f'case pass: band {_e(cb.get("band_label") or cb.get("reason"))}.</p>'
            + '<h3>Options at the final gauge</h3><p class="note">' + _e(opts.get('ordering_rule'))
            + '</p>' + _table(['alloy', 'grade', 'temper', 'GB min [MPa]', 'typical Rm [MPa]',
                               'usual choice', 'evidence', 'sources'], rows, 'wrapall')
            + '<h3>Proposals</h3><ul>' + ''.join(props) + '</ul>'
            + '<h3>The case against the band</h3>'
            + f'<p>Alloy: {_e(_get(cmp_, "alloy", "text"))} Temper: '
              f'{_e(_get(cmp_, "temper", "verdict"))}. Yield stress '
              f'{_mpa_txt(ys.get("value_pa"))} MPa: {_e(ys.get("verdict"))} '
              f'(proof strength {"published" if ys.get("published") else "assumed"}).</p>'
            + _table(['pass', 'exit', 'band', 'flow stress [MPa]', 'compared with',
                      'standard min [MPa]', 'verdict'], prow, 'wrapall')
            + f'<p class="note">{_e(cmp_.get("flow_stress_caveat"))} {_e(ms.get("note"))} '
              f'Flags: {_e(", ".join(ms.get("flags") or []) or "none")}. '
              + _e(' '.join(ms.get('limitations') or [])) + '</p></section>')


TC_UNITS = {'degC': ('°C', 1.0), 'fraction': ('', 1.0), 'W/m^2K': ('kW/m²K', 1e-3),
            'm': ('µm', 1e6), 'm^2/s': ('cSt', 1e6)}


def _tc_val(f, key):
    v = f.get(key)
    unit, k = TC_UNITS.get(f.get('unit'), ('', 1.0))
    if not _ok(v):
        return '–'
    return _f(v * k, 1.0, 3) + (f' {unit}' if unit else '')


def _tc_rows(fs, label_key='item'):
    rows = []
    for f in fs:
        lo, hi = _tc_val(f, 'published_low'), _tc_val(f, 'published_high')
        rng = f'{lo} – {hi}' if lo != '–' and hi != '–' else (f'≤ {hi}' if hi != '–' else lo)
        word = PC_WORDS.get(f.get('verdict'), str(f.get('verdict')))
        rows.append([_e(str(f.get(label_key) or f.get('item')).replace('_', ' ')),
                     _tc_val(f, 'value'), rng,
                     f'<strong>{_e(word)}</strong>' if word.isupper() else _e(word),
                     _e(', '.join(f.get('sources') or [])), _e(f.get('read_status') or '–'),
                     _e(' '.join(x for x in (f.get('conversion'), f.get('note')) if x))])
    return rows


def _thermal_block(r):
    """SPEC14 Part 2: process temperatures against the literature (and the sensitivity)."""
    tc = r.get('thermal_check')
    head = '<section><h2>Process temperatures</h2>'
    if not isinstance(tc, dict):
        return ''
    if tc.get('status') == 'FAILED':
        return head + _state_p('FAILED: ' + str(tc.get('error'))) + '</section>'
    if tc.get('not_supplied'):
        return head + _state_p('not supplied: ' + str(tc.get('reason'))) + '</section>'
    cols = ['item', 'value', 'published', 'verdict', 'sources', 'read status', 'note']
    out = [head, f'<p>{_e(tc.get("note"))} ' + _e(' '.join(tc.get('texts') or [])) + '</p>',
           '<h3>Case inputs against the literature</h3>',
           _table(cols, _tc_rows(tc.get('inputs') or []), 'wrapall')]
    sp = next((f for f in tc.get('inputs') or []
               if f.get('item') == 'spray_heat_transfer_coefficient'
               and f.get('basis_comparable')), None)
    if sp is not None:
        # SPEC17 A5 / X3: the bases of the model and published coefficients
        line = ('The model\'s spray coefficient is an average around the roll. The published '
                '2.5-4.3 kW/m²K is read as a value inside the jet zone. The two are not on the '
                'same basis')
        if _ok(sp.get('footprint_equivalent_w_m2k')):
            line += (f'; with a wetted arc of {_f(math.degrees(sp["spray_wetted_arc_rad"]))} '
                     f'degrees the model value corresponds to '
                     f'{_f(sp["footprint_equivalent_w_m2k"], 1e-3, 4)} kW/m²K inside the jet '
                     'zone')
        out.append(f'<p class="note">{_e(line)}.</p>')
    lim = tc.get('coil_limits_c') or {}
    out.append('<h3>Modelled outputs against the literature</h3>')
    if tc.get('battery_coil_limits_apply'):
        out.append(f'<p>Battery-foil coil limits [PT-T1, PT-T2]: ≤{_f(lim.get("entering_final_pass"))} °C '
                   f'entering the final pass, ≤{_f(lim.get("leaving_final_pass"))} °C leaving it; '
                   f'above {_f(lim.get("elongation_decay_above"))} °C elongation decays for '
                   'weeks.</p>')
    temps = tc.get('strip_exit_temperatures') or []
    if tc.get('operating_pass_note'):
        out.append(f'<p class="warn">{_e(tc["operating_pass_note"])}</p>')
    if temps:
        for f in temps:
            f.setdefault('label', f.get('item'))
        out.append(_table(['pass (strip exit, modelled)', 'value', 'published', 'verdict',
                           'sources', 'read status', 'note'], _tc_rows(temps, 'label'),
                          'wrapall'))
    out.append(_table(cols, _tc_rows(tc.get('outputs') or []), 'wrapall'))
    g = tc.get('growth') or {}
    if g.get('text'):
        out.append(f'<p>{_e(g["text"])}</p>')
    pr = tc.get('property_risk')
    if pr:
        out.append(f'<p><strong>Property risk (literature, not a model):</strong> passes '
                   f'{_e(", ".join(pr["passes"]))}. {_e(pr["literature_statement"])} '
                   f'[{_e(", ".join(pr["sources"]))}] {_e(pr["note"])}</p>')
    q = tc.get('quarter_barrel_note')
    if q:
        out.append(f'<p class="note">{_e(q["text"])}</p>')
    fl = tc.get('fire_limits')
    if isinstance(fl, dict):
        # SPEC17 A10: rule check against the user's limits only
        if fl.get('rows'):
            rows = [[_e(x.get('label') or x['item']), _f(x['value_k'] - 273.15, 1, 4),
                     _f(x['limit_k'] - 273.15, 1, 4), _f(x['margin_k'], 1, 3),
                     _txt(x['verdict']), _e(x['limit_basis'])] for x in fl['rows']]
            out.append('<h3>Fire limits</h3>'
                       + _table(['item', 'value [°C]', 'limit [°C]', 'margin [K]', 'verdict',
                                 'limit'], rows, 'wrapall')
                       + f'<p class="note">{_e(fl.get("note"))}</p>')
        else:
            out.append('<p class="note">Fire limits not checked: no flash point given.</p>')
    ts = _get(r, 'width', 'thermal_sensitivity')
    if isinstance(ts, dict) and ts.get('status') == 'EVALUATED':
        rows = []
        for x in ts.get('rows') or []:
            ev = (x.get('events') or [{}])[0] if x.get('events') else {}
            rows.append([_f(x.get('strip_heat_share'), 1, 2),
                         _f(x.get('spray_htc_w_m2k'), 1e-3, 3),
                         _um(x.get('stripe_peak_m')),
                         _e(_short(x.get('state_in_mill'))) if x.get('state_in_mill') else '–',
                         _f(x.get('ratio_stripe_to_in_mill_onset'), 1, 3),
                         _um(ev.get('peak_deviation_m')) if ev else '–',
                         _e(_short(ev.get('in_mill'))) if ev.get('in_mill') else '–',
                         _f(ev.get('visible_time_s'), 1, 3) if ev else '–'])
        out.append('<h3>Sensitivity of the stripe to the heat partition and the spray '
                   'coefficient</h3>'
                   f'<p class="note">{_e(ts.get("share_conversion"))}; {_e(ts.get("note"))} '
                   f'{_e(ts.get("linearity_note"))}. {_e(ts.get("spray_rows_note") or "")}</p>'
                   + _table(['strip share', 'spray [kW/m²K]', 'stripe (radius)', 'in mill',
                             'stripe / in-mill onset', 'event peak', 'event in mill',
                             'event visible [s]'], rows, 'wrapall'))
        if ts.get('per_pass_text'):
            out.append(f'<p>{_e(ts["per_pass_text"])}</p>')
        if ts.get('per_pass_onset_shape_basis'):
            out.append('<p class="note">The per-pass onsets are those of '
                       f'{_e(ts["per_pass_onset_shape_basis"])}.</p>')
        elif ts.get('per_pass_onsets_not_given_reason'):
            out.append('<p class="note">No per-pass onset or ratio: '
                       f'{_e(ts["per_pass_onsets_not_given_reason"])}.</p>')
    out.append('</section>')
    return ''.join(out)


# ------------------------------------------------------------------------------ family + layout
def _family_block(r):
    fs = r.get('family_summary') or {}
    counts = fs.get('not_contradicted_per_family') or {}
    obs = _get(r, 'inputs', 'observation') or {}
    seen = []
    if obs.get('orientation'):
        seen.append(f'orientation {_e(obs["orientation"])}')
    if obs.get('lengthwise_continuity'):
        seen.append(f'continuity {_e(obs["lengthwise_continuity"])}')
    pos = [x for x in obs.get('band_positions_across_width_m') or [] if _ok(x)]
    if pos:
        seen.append(f'positions {_e(", ".join(_f(x, 1, 4) for x in pos))} m across the width')
    if _ok(obs.get('intermittent_duration_s')):
        seen.append(f'short-lived bands last about {_f(obs["intermittent_duration_s"])} s')
    for k, label in (('worse_at_thinner_gauge', 'worse at thinner gauge'),
                     ('visible_only_after_tension_release',
                      'visible only after tension release'),
                     ('positions_repeat_across_coils', 'positions repeat across coils')):
        if obs.get(k) is not None:
            seen.append(f'{label}: {"yes" if obs[k] else "no"}')
    cnt = ', '.join(f'{_e(k)} {_f(v)}' for k, v in sorted(counts.items()))
    return ('<div class="family"><h2 style="margin-top:.2rem">Which family of causes</h2>'
            f'<p>{_e(fs.get("text") or "No family summary in the result.")}</p>'
            f'<p>Observed family: <strong>{_txt(fs.get("observed_family"))}</strong>; '
            f'family of the leading hypothesis: <strong>{_txt(fs.get("leading_family"))}'
            f'</strong>. Not-contradicted hypotheses per family: {cnt or "n/a"}.</p>'
            + (f'<p class="note">Observed: {"; ".join(seen)}.</p>' if seen else '') + '</div>')


def _runners_up(r, family):
    hs = [h for h in r['hypotheses'] if h.get('family') == family
          and h['standing'] == 'CONSISTENT' and h['score'] > 0][:3]
    if not hs:
        return ''
    items = ''.join(f'<li>{_e(h["title"])} (<code>{_e(h["id"])}</code>): {_e(_reason(h))}</li>'
                    for h in hs)
    return (f'<p>Also consistent in the {_e(family)} family (no strong contradiction, lower '
            f'score):</p><ul>{items}</ul>')


# ------------------------------------------------------------------------------ phase-1 blocks
def _head_blocks(r):
    synthetic = r['synthetic']
    s = [f'<h1>Band / chatter-mark root-cause screening</h1>'
         f'<p>Case: <strong>{_e(r["case_name"])}</strong></p>']
    origin = 'synthetic' if synthetic else 'user-supplied (not verified)'
    s.append(f'<div class="warn"><strong>{_e(r["status"])}.</strong> This is an unvalidated '
             f'screening result on <strong>{_e(origin)}</strong> inputs. It ranks candidate '
             'mechanisms by an ordinal evidence tally; it does not certify a cause. '
             f'{_e(r["score_note"])}</div>')
    s.append(f'<p class="small-p">Provenance: {_e(r["provenance"])}</p>')
    return s


def _lead_block(r, extra=''):
    lead = [h for h in r['hypotheses'] if h['standing'] == 'CONSISTENT_LEADING']
    if lead:
        items = ''.join(f'<li><strong>{_e(h["title"])}</strong> (<code>{_e(h["id"])}</code>): '
                        f'{_e(_reason(h))}</li>' for h in lead)
        return (f'<div class="lead"><h2 style="margin-top:.2rem">Leading hypotheses</h2>'
                f'<ul>{items}</ul>{extra}</div>')
    return ('<div class="lead"><h2 style="margin-top:.2rem">Leading hypotheses</h2>'
            '<p>None: no hypothesis reaches a score of 3 without a strong contradiction. '
            f'Take the measurements below.</p>{extra}</div>')


def _next_blocks(r):
    nm = ''.join(f'<li>{_e(x)}</li>' for x in r['recommended_next_measurements'])
    return [f'<h2>Next measurements</h2><ol>{nm}</ol>',
            f'<p>Flags: {_e(", ".join(r["flags"]) or "none")}</p>']


def _key_numbers(r):
    p = r['inputs']['pass']
    # flow stress and friction may be replaced by computed values (effective_inputs); show the
    # value every section used, and the supplied one beside it when they differ
    used = r.get('effective_inputs', {}).get('pass', p)

    def used_value(key, unit=''):
        text = _n(used[key], unit=unit)
        if used[key] != p[key]:
            text += f' (computed; supplied {_n(p[key], unit=unit)})'
        return text
    rows = [['operating exit speed', _n(p['exit_speed_m_s'], unit='m/s')],
            ['pass gauge', f'{_mm(p["entry_thickness_m"])} -> {_mm(p["exit_thickness_m"])}'],
            ['mean flow stress used', used_value('mean_flow_stress_pa', 'Pa')],
            ['friction coefficient used', used_value('friction_coefficient')]]
    if r['bite']:
        b = r['bite']
        # foil_bite marks its bites source 'supplied'; name the model actually used
        src = ('experimental_mattress' if 'BITE_FROM_EXPERIMENTAL_MATTRESS_MODEL' in
               (b.get('flags') or []) else b['source'])
        rows += [['bite source', _e(src)],
                 ['separating force', _n(b['separating_force_n'], unit='N')],
                 ['contact radius ratio R\'/R', _n(b['contact_radius_ratio'])],
                 ['forward slip', _n(b['forward_slip_fraction'])],
                 ['strip modulus Q_s', _n(b['strip_modulus_n_m'], unit='N/m')]]
    else:
        rows.append(['bite', f'NOT_ASSESSABLE: {_e(r["bite_error"])}'])
    sm = r['stand_modes']
    rows += [['mill modulus K_mill', _n(sm['mill_modulus_n_m'], unit='N/m')],
             ['Q_s / K_mill', _n(sm['strip_to_mill_modulus_ratio'])]]
    for m in sm['structural_modes_for_catalogue']:
        rows.append([f'mode {_e(m["name"])} ({_e(m["family"])})',
                     _n(m['frequency_hz'], unit='Hz')])
    return '<h3>Key model numbers</h3>' + _table(('quantity', 'value'), rows)


def _strip_section(r):
    sm2 = r['strip_map']
    if sm2.get('status') == 'FAILED':
        return ('<section><h2>What the model predicts on the strip</h2>'
                + _state_p('FAILED: ' + str(sm2.get('error'))) + '</section>')
    return ('<section><h2>What the model predicts on the strip</h2>'
            f'<p>Bands drawn at the predicted pitch of the leading vibration-type hypothesis '
            f'(<code>{_e(sm2["hypothesis_id"] or "none")}</code>); ticks below the strip at the '
            'observed pitch. Horizontal axis to scale.</p>' + _strip_map(r) + '</section>')


def _chatter_section(r):
    ch = r['chatter']
    if ch.get('status') == 'NOT_ASSESSABLE':
        return (f'<section><h2>Chatter stability</h2><p>NOT_ASSESSABLE: '
                f'{_e(ch["reason"])}</p></section>')
    wb, nb = ch['with_bite_damping'], ch['without_bite_damping']
    rows = []
    for label, d in ((f'beta = {_n(wb["bite_damping_transit_fraction"])}', wb),
                     ('beta = 0', nb)):
        rows.append([label, _n(d['critical_exit_speed_m_s'], unit='m/s'),
                     _e(d['critical_status']), _n(d['speed_ratio'], 3),
                     _n(d['onset_frequency_hz'], unit='Hz'), _mm(d['onset_strip_pitch_m']),
                     _n(d['max_growth_rate_per_s'], unit='1/s'),
                     _n(d['stable_at_operating_speed'])])
    return ('<section><h2>Chatter stability</h2>'
            '<p>Largest real part of the eigenvalues of the linear third-octave model versus '
            'exit speed. Positive = growing vibration. The bite-damping closure (fraction '
            'beta of the transit time) is a declared heuristic, so the beta = 0 curve is '
            'shown as the cautious bound.</p>'
            + (f'<p class="warn">{_e(ch["operating_speed_outside_scanned_range"]["note"])}. '
               'Here "STABLE_OVER_SCANNED_RANGE" does not mean stable at the operating speed: '
               'read the last column.</p>'
               if ch.get('operating_speed_outside_scanned_range') else '')
            + _growth_chart(r)
            + _table(('closure', 'critical exit speed', 'status', 'operating / critical',
                      'onset frequency', 'onset pitch', 'growth at operating speed',
                      'stable at operating speed'), rows, 'num') + '</section>')


def _schedule_section(r):
    sw = r['schedule_sweep']
    if not sw:
        return '<section><h2>Pass-schedule sweep</h2><p>No schedule supplied.</p></section>'
    rows = []
    for x in sw['rows']:
        if 'rejected' in x:
            rows.append([_e(x['label']), _mm(x['entry_thickness_m']),
                         _mm(x['exit_thickness_m']), _n(x['exit_speed_m_s']),
                         _n(x['friction_coefficient']),
                         f'<em>rejected: {_e(x["rejected"])}</em>', '', '', '', '', '', '',
                         '', ''])
            continue
        rows.append([_e(x['label']), _mm(x['entry_thickness_m']), _mm(x['exit_thickness_m']),
                     _n(x['exit_speed_m_s']), _n(x['friction_coefficient']),
                     _n(x['contact_radius_ratio'], 3), _n(x['strip_to_mill_modulus_ratio'], 3),
                     _n(x['critical_exit_speed_m_s'], 4),
                     _n(x['critical_exit_speed_without_bite_damping_m_s'], 4),
                     f'<strong>{_n(x["speed_ratio"], 3)}</strong>',
                     _n(x['onset_frequency_hz'], 4), _mm(x['pitch_at_operating_speed_m']),
                     _n(x['relative_ripple_per_um_runout_at_work_roll_2x'], 3),
                     _n(x['thermal_gap_closure_fraction_upper_bound'], 3)])
    rows2 = []
    for x in sw['rows']:
        same = x['at_case_friction']
        rows2.append([_e(x['label']), _n(x['friction_coefficient']),
                      _n(same['friction_coefficient']),
                      _n(same.get('critical_exit_speed_m_s'), 4) if 'rejected' not in same
                      else f'<em>rejected: {_e(same["rejected"])}</em>',
                      _n(same.get('critical_exit_speed_without_bite_damping_m_s'), 4),
                      _n(x.get('bending_strain_smallest_deflector'), 3)])
    return ('<section><h2>Pass-schedule sweep</h2>'
            f'<p>{_e(sw["note"])}</p>' + _schedule_chart(sw)
            + _table(('pass', 'entry', 'exit', 'speed [m/s]', 'friction', "R'/R",
                      'Q_s/K_mill', 'u_crit beta [m/s]', 'u_crit 0 [m/s]',
                      'operating / u_crit', 'onset [Hz]', 'pitch at speed',
                      'rel. ripple per um run-out (WR 2x)',
                      'thermal gap closure (upper bound)'), rows, 'num')
            + '<h3>Same passes at the case friction (gauge effect alone)</h3>'
            + _table(('pass', 'schedule friction', 'case friction', 'u_crit beta [m/s]',
                      'u_crit 0 [m/s]', 'bending strain t/D, smallest deflector'), rows2,
                     'num') + '</section>')


def _freq_section(r):
    sig = r['signatures']
    pse = sig['pitch_speed_exponent']
    law = (f'Pitch-speed exponent {_n(pse["slope"], 3)}: {_e(pse["classification"])}.'
           if pse else _e(sig.get('law_note', 'No pitch observations.')))
    obs_rows = []
    for o in sig['observations']:
        hits = ', '.join(f'{h["id"]} ({h["relative_pitch_mismatch"]:.1%})'
                         for h in o['matches'][:4]) or 'none within 8 %'
        obs_rows.append([_n(o['exit_speed_m_s'], unit='m/s'), _mm(o['pitch_m']),
                         _n(o['implied_frequency_hz'], unit='Hz'), _e(hits)])
    res_rows = []
    for name, rs in sorted(sig['resonance_speeds'].items()):
        for c in rs['crossings'][:8]:
            res_rows.append([_e(name), _n(rs['mode_frequency_hz'], unit='Hz'), _e(c['id']),
                             _n(c['resonant_exit_speed_m_s'], unit='m/s'),
                             _mm(c['strip_pitch_m'])])
    return ('<section><h2>Frequency-speed map</h2>'
            '<p>Order-locked sources (roll orders, gear meshes, bearing defects, deflectors) '
            'are straight lines through the origin; stand modes are horizontal. Observed '
            f'points are (exit speed, u/p). {law}</p>' + _freq_speed_chart(r)
            + (_table(('exit speed', 'pitch', 'implied frequency u/p',
                       'catalogue matches (pitch mismatch)'), obs_rows) if obs_rows else '')
            + '<details><summary>Source catalogue at the operating speed ('
            + str(len(sig['catalogue'])) + ' entries)</summary>'
            + _table(('source', 'kind', 'order of work-roll rotation', 'frequency',
                      'strip pitch', 'pitch-speed law'),
                     [[_e(e['id']), _e(e['kind']), _n(e['order_of_work_roll_rotation']),
                       _n(e['frequency_hz'], unit='Hz'), _mm(e['strip_pitch_m']),
                       _e(e['pitch_speed_law'])] for e in sig['catalogue']]) + '</details>'
            + ('<h3>Resonant crossings (order-locked source meets a stand mode, up to '
               f'{_n(_speed_envelope(r))} m/s)</h3>' + _table(('mode', 'mode frequency', 'source',
                                                         'resonant exit speed', 'pitch'),
                                                        res_rows)
               if res_rows else '<p>No order-locked source crosses the listed modes within '
               'the realistic speed envelope.</p>') + '</section>')


def _forced_section(r):
    fr = r['forced_response']
    if fr.get('status') == 'NOT_ASSESSABLE':
        return (f'<section><h2>Forced response and time trace</h2><p>NOT_ASSESSABLE: '
                f'{_e(fr["reason"])}</p></section>')
    rows = []
    for dist, label in (('work_backup_runout', 'per 1 um work/backup run-out'),
                        ('entry_thickness', 'per 1 um incoming thickness ripple')):
        for row in fr[dist]['roll_orders']:
            rows.append([_e(label), _e(row['source']), _n(row['frequency_hz'], unit='Hz'),
                         _n(row['exit_ripple_per_um_m'] * 1e9, 4, 'nm'),
                         _n(row['relative_exit_ripple_per_um'], 3)])
    warn = ''
    if fr['operating_point_unstable']:
        warn = ('<p class="warn">The operating point is linearly unstable, so this forced '
                'response is formal only (no steady state exists).</p>')
    sim = r['time_simulation']
    trace = ''
    if isinstance(sim, dict) and _bad(sim):
        trace = '<h3>Simulated exit thickness trace</h3>' + _state_p(_bad(sim))
    elif sim:
        trace = ('<h3>Simulated exit thickness trace</h3>'
                 '<p>Initial gap perturbation '
                 f'{_n(sim["initial_gap_perturbation_m"] * 1e6)} um; '
                 f'measured from the trace: {_n(sim["dominant_frequency_hz"])} Hz, growth '
                 f'{_n(sim["growth_rate_per_s"])} 1/s (eigenvalues: '
                 f'{_n(sim["eigen_dominant_frequency_hz"])} Hz, '
                 f'{_n(sim["eigen_max_growth_rate_per_s"])} 1/s); predicted strip pitch '
                 f'{_mm(sim["predicted_strip_pitch_from_trace_m"])}; linear range exceeded: '
                 f'{_n(sim["linear_range_exceeded"])}.</p>' + _trace_chart(sim))
    return ('<section><h2>Forced response and time trace</h2>' + warn
            + '<p>Exit-thickness response per unit roll run-out (eccentricity, '
            'out-of-round, backup-roll marks) and per unit incoming thickness ripple.</p>'
            + _spectrum_chart(fr)
            + _table(('disturbance', 'source', 'frequency', 'exit ripple',
                      'relative to exit gauge'), rows, 'num') + trace + '</section>')


def _levers_blocks(r):
    s = []
    lv = r['levers']
    if lv.get('status') == 'NOT_ASSESSABLE':
        s.append(f'<section><h2>Levers</h2><p>NOT_ASSESSABLE: {_e(lv["reason"])}</p>')
    else:
        rows = []
        for x in lv['rows']:
            if 'rejected' in x:
                rows.append([_e(x['change']), f'<em>rejected: {_e(x["rejected"])}</em>', '', ''])
            else:
                rows.append([_e(x['change']), _n(x['critical_exit_speed_m_s'], unit='m/s'),
                             _n(x['critical_exit_speed_without_bite_damping_m_s'], unit='m/s'),
                             _n(x['ratio_to_baseline'], 3)])
        dirs = ''.join(f'<li>{_e(d["direction"])}</li>' for d in lv['directions'])
        s.append('<section><h2>Levers</h2>'
                 + (f'<p class="warn">{_e(lv["foil_regime_note"])}</p>'
                    if lv.get('foil_regime_note') else '')
                 + f'<p>Baseline critical exit speed {_n(lv["baseline_critical_exit_speed_m_s"])} '
                 f'm/s (beta = {_n(lv["bite_damping_transit_fraction"])}), '
                 f'{_n(lv["baseline_critical_exit_speed_without_bite_damping_m_s"])} m/s with '
                 f'beta = 0. {_e(lv["note"])}</p>'
                 + _table(('change', 'critical exit speed', 'critical, beta = 0',
                           'ratio to baseline'), rows, 'num') + f'<ul>{dirs}</ul>')
    scr = r['screens']
    if scr['spray_coverage']:
        cov = scr['spray_coverage']
        th = scr['thermal']
        s.append('<h3>Coolant spray coverage</h3>'
                 f'<p>Status {_e(cov["status"])}: {_n(cov["active_nozzle_count"])} of '
                 f'{_n(cov["nozzle_count"])} nozzles active, overlap fraction '
                 f'{_n(cov["overlap_fraction"], 3)}. {_e(scr["band_risk_rule"])} '
                 'Free thermal growth upper bound '
                 f'{_n(th["radius_growth_upper_bound_m"] * 1e6)} um '
                 f'closes the local gap by {_n(th["local_gap_closure_fraction"], 3)} of the exit '
                 'gauge (upper bound).</p>'
                 + _spray_chart(scr, r['inputs']['observation']['band_positions_across_width_m']))
    else:
        s.append('<p>No coolant data supplied: spray coverage not screened.</p>')
    s.append('</section>')
    rows = [['Lueders susceptibility', _e(scr['luders_susceptibility']['status'])],
            ['pass reduction vs Lueders', _e(scr['pass_reduction_vs_luders']['status'])],
            ['herringbone', _e(scr['herringbone']['status']) + ', contact length '
             + _mm(scr['herringbone']['contact_length_m'])],
            ['forward slip', _e(scr['forward_slip']['status']) if scr['forward_slip']
             else 'NOT_ASSESSABLE']]
    for w in scr['bending_windows']:
        rows.append([f'bending window {_e(w["location"])} (D = {_n(w["diameter_m"])} m)',
                     _e(w['status']) + (f', strain {_n(w["bending_surface_strain"], 3)}'
                                        if 'bending_surface_strain' in w else '')])
    if scr['film']:
        rows.append(['inlet film (formula quoted from memory)',
                     f'{_n(scr["film"]["film_thickness_m"] * 1e6)} um, Lambda '
                     f'{_n(scr["film_regime"]["film_ratio"], 3)} '
                     f'({_e(scr["film_regime"]["regime"])})'])
    if scr.get('status') == 'FAILED':
        rows.insert(0, ['screens section', 'FAILED: ' + _e(scr.get('error', ''))])
    s.append('<h3>Other screens</h3>' + _table(('screen', 'result'), rows))
    return s


def _hyp_section(r, family=None):
    extra = ''
    if family is not None:
        extra = (' Grouped by family, the observed family'
                 + (f' ({_e(family)})' if family else '') + ' first; rank is the overall rank.')
    return ('<section><h2>Hypotheses</h2>'
            f'<p>{_e(r["score_note"])} Standing CONTRADICTED = at least one strong '
            'contradiction; CONSISTENT_LEADING = highest non-contradicted score, at least 3; '
            f'NOT_ASSESSABLE = no supporting or contradicting evidence.{extra}</p>'
            + _hypothesis_rows(r, family) + '</section>')


def _lim_section(r):
    lim = ''.join(f'<li>{_e(x)}</li>' for x in r['limitations'])
    dis = ''.join(f'<li>{_e(x)}</li>' for x in r['source_disagreements'])
    src = ''.join(f'<li>{_e(x)}</li>' for x in r['sources'])
    return ('<section><h2>Limitations and sources</h2>'
            f'<ul>{lim}</ul><h3>Known disagreements in the literature</h3><ul>{dis}</ul>'
            f'<h3>Sources</h3><ol>{src}</ol></section>')


def _notes_block(r):
    notes = [x for x in _get(r, 'inputs', 'notes') or [] if isinstance(x, str)]
    if not notes:
        return ''
    return '<p class="note">Case notes:</p>' + _ul([_e(x) for x in notes])


# ------------------------------------------------------------------------------ entry point
def render_band_report(result):
    """Render the screening result as one self-contained HTML string (deterministic).

    A ``physicroll.band_case.v1`` result renders exactly the phase-1 page. Any other schema
    also gets the family statement, the lengthwise sections, the process / dynamics sections
    and a family column; when the observed or leading family is ``lengthwise`` the page leads
    with those and moves the transverse (chatter) sections to a supporting-detail block.
    """
    r = result
    v1 = r.get('case_schema', V1_SCHEMA) == V1_SCHEMA
    css = CSS
    s = _head_blocks(r)
    foil = _foil_block(r) + _product_block(r) + _material_block(r)
    if foil:
        css += CSS3
        s.insert(len(s) - 1, foil)       # before the (long) provenance paragraph
    if v1:
        s.append(_lead_block(r))
        s += _next_blocks(r)
        s.append(_key_numbers(r))
        s += [_strip_section(r), _chatter_section(r), _schedule_section(r), _freq_section(r),
              _forced_section(r)]
        s += _levers_blocks(r)
        s.append(_hyp_section(r))
    else:
        css = css + CSS2
        fs = r.get('family_summary') or {}
        lengthwise = 'lengthwise' in (fs.get('observed_family'), fs.get('leading_family'))
        fam = fs.get('observed_family') or fs.get('leading_family')
        s.append(_notes_block(r))
        s.append(_family_block(r))
        s.append(_lead_block(r, _runners_up(r, fam) if fam else ''))
        s += _next_blocks(r)
        transverse = [_key_numbers(r), _strip_section(r), _chatter_section(r),
                      _schedule_section(r), _freq_section(r), _forced_section(r)]
        transverse += _levers_blocks(r)
        new = [_width_section(r), _events_section(r), _gauge_section(r)]
        tail = [_process_section(r), _thermal_block(r), _dynamics_section(r)]
        if lengthwise:
            s += new
            s.append(_hyp_section(r, fam or ''))
            s.append('<section class="divider"><h2>Transverse-band (chatter) screening: '
                     'supporting detail for this case</h2><p>The sections below test the '
                     'transverse family (marks across the strip, repeating along its length). '
                     'The evidence for this case points to the lengthwise family, so they are '
                     'kept as supporting detail and for the exclusions they give.</p></section>')
            s += transverse
            s += tail
        else:
            s += transverse
            s += new + tail
            s.append(_hyp_section(r, fam or ''))
    s.append(_lim_section(r))
    title = f'Band screening: {r["case_name"]}'
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_e(title)}</title><style>{css}</style></head><body>'
            + ''.join(s) + '</body></html>\n')


def _speed_envelope(result):
    """Realistic speed envelope used for resonant crossings (from the result)."""
    for rs in result['signatures']['resonance_speeds'].values():
        return rs['realistic_max_exit_speed_m_s']
    return None
