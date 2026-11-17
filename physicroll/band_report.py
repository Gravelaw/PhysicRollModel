"""Deterministic, self-contained HTML report of a band root-cause screening result.

Every number shown is read from the ``diagnose`` result dict (display-unit conversions such
as m -> mm are labelled). No JavaScript, no external assets; charts are inline SVG with axis
labels, units, a key, and dash patterns as well as colours. All text is escaped.
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


def _hypothesis_rows(result):
    out = []
    for h in result['hypotheses']:
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
        out.append([str(h['rank']), f'<code>{_e(h["id"])}</code>{details}',
                    _standing_badge(h['standing']), str(h['score']),
                    f'{t["support_points"]} / {t["contradiction_points"]}'])
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
       '@media print{details{display:block}summary{display:none}}')


def render_band_report(result):
    """Render the screening result as one self-contained HTML string (deterministic)."""
    r = result
    synthetic = r['synthetic']
    p = r['inputs']['pass']
    s = []
    s.append(f'<h1>Band / chatter-mark root-cause screening</h1>'
             f'<p>Case: <strong>{_e(r["case_name"])}</strong></p>')
    origin = 'synthetic' if synthetic else 'user-supplied (not verified)'
    s.append(f'<div class="warn"><strong>{_e(r["status"])}.</strong> This is an unvalidated '
             f'screening result on <strong>{_e(origin)}</strong> inputs. It ranks candidate '
             'mechanisms by an ordinal evidence tally; it does not certify a cause. '
             f'{_e(r["score_note"])}</div>')
    s.append(f'<p class="small-p">Provenance: {_e(r["provenance"])}</p>')
    lead = [h for h in r['hypotheses'] if h['standing'] == 'CONSISTENT_LEADING']
    if lead:
        items = ''.join(f'<li><strong>{_e(h["title"])}</strong> (<code>{_e(h["id"])}</code>): '
                        f'{_e(_reason(h))}</li>' for h in lead)
        s.append(f'<div class="lead"><h2 style="margin-top:.2rem">Leading hypotheses</h2>'
                 f'<ul>{items}</ul></div>')
    else:
        s.append('<div class="lead"><h2 style="margin-top:.2rem">Leading hypotheses</h2>'
                 '<p>None: no hypothesis reaches a score of 3 without a strong contradiction. '
                 'Take the measurements below.</p></div>')
    nm = ''.join(f'<li>{_e(x)}</li>' for x in r['recommended_next_measurements'])
    s.append(f'<h2>Next measurements</h2><ol>{nm}</ol>')
    s.append(f'<p>Flags: {_e(", ".join(r["flags"]) or "none")}</p>')

    # key numbers
    rows = [['operating exit speed', _n(p['exit_speed_m_s'], unit='m/s')],
            ['pass gauge', f'{_mm(p["entry_thickness_m"])} -> {_mm(p["exit_thickness_m"])}'],
            ['friction coefficient', _n(p['friction_coefficient'])]]
    if r['bite']:
        b = r['bite']
        rows += [['bite source', _e(b['source'])],
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
    s.append('<h3>Key model numbers</h3>' + _table(('quantity', 'value'), rows))

    # 2 strip map
    sm2 = r['strip_map']
    s.append('<section><h2>What the model predicts on the strip</h2>'
             f'<p>Bands drawn at the predicted pitch of the leading vibration-type hypothesis '
             f'(<code>{_e(sm2["hypothesis_id"] or "none")}</code>); ticks below the strip at the '
             'observed pitch. Horizontal axis to scale.</p>' + _strip_map(r) + '</section>')

    # 3 chatter
    ch = r['chatter']
    if ch.get('status') == 'NOT_ASSESSABLE':
        s.append(f'<section><h2>Chatter stability</h2><p>NOT_ASSESSABLE: '
                 f'{_e(ch["reason"])}</p></section>')
    else:
        wb, nb = ch['with_bite_damping'], ch['without_bite_damping']
        rows = []
        for label, d in ((f'beta = {_n(wb["bite_damping_transit_fraction"])}', wb),
                         ('beta = 0', nb)):
            rows.append([label, _n(d['critical_exit_speed_m_s'], unit='m/s'),
                         _e(d['critical_status']), _n(d['speed_ratio'], 3),
                         _n(d['onset_frequency_hz'], unit='Hz'), _mm(d['onset_strip_pitch_m']),
                         _n(d['max_growth_rate_per_s'], unit='1/s'),
                         _n(d['stable_at_operating_speed'])])
        s.append('<section><h2>Chatter stability</h2>'
                 '<p>Largest real part of the eigenvalues of the linear third-octave model versus '
                 'exit speed. Positive = growing vibration. The bite-damping closure (fraction '
                 'beta of the transit time) is a declared heuristic, so the beta = 0 curve is '
                 'shown as the cautious bound.</p>' + _growth_chart(r)
                 + _table(('closure', 'critical exit speed', 'status', 'operating / critical',
                           'onset frequency', 'onset pitch', 'growth at operating speed',
                           'stable at operating speed'), rows, 'num') + '</section>')

    # 4 schedule
    sw = r['schedule_sweep']
    if sw:
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
        s.append('<section><h2>Pass-schedule sweep</h2>'
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
    else:
        s.append('<section><h2>Pass-schedule sweep</h2><p>No schedule supplied.</p></section>')

    # 5 frequency-speed
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
    s.append('<section><h2>Frequency-speed map</h2>'
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

    # 6 forced response + trace
    fr = r['forced_response']
    if fr.get('status') == 'NOT_ASSESSABLE':
        s.append(f'<section><h2>Forced response and time trace</h2><p>NOT_ASSESSABLE: '
                 f'{_e(fr["reason"])}</p></section>')
    else:
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
        if sim:
            trace = ('<h3>Simulated exit thickness trace</h3>'
                     '<p>Initial gap perturbation '
                     f'{_n(sim["initial_gap_perturbation_m"] * 1e6)} um; '
                     f'measured from the trace: {_n(sim["dominant_frequency_hz"])} Hz, growth '
                     f'{_n(sim["growth_rate_per_s"])} 1/s (eigenvalues: '
                     f'{_n(sim["eigen_dominant_frequency_hz"])} Hz, '
                     f'{_n(sim["eigen_max_growth_rate_per_s"])} 1/s); predicted strip pitch '
                     f'{_mm(sim["predicted_strip_pitch_from_trace_m"])}; linear range exceeded: '
                     f'{_n(sim["linear_range_exceeded"])}.</p>' + _trace_chart(sim))
        s.append('<section><h2>Forced response and time trace</h2>' + warn
                 + '<p>Exit-thickness response per unit roll run-out (eccentricity, '
                 'out-of-round, backup-roll marks) and per unit incoming thickness ripple.</p>'
                 + _spectrum_chart(fr)
                 + _table(('disturbance', 'source', 'frequency', 'exit ripple',
                           'relative to exit gauge'), rows, 'num') + trace + '</section>')

    # 7 levers + spray
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
                 f'<p>Baseline critical exit speed {_n(lv["baseline_critical_exit_speed_m_s"])} '
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

    # other screens summary
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
    s.append('<h3>Other screens</h3>' + _table(('screen', 'result'), rows))

    # 8 hypotheses
    s.append('<section><h2>Hypotheses</h2>'
             f'<p>{_e(r["score_note"])} Standing CONTRADICTED = at least one strong '
             'contradiction; CONSISTENT_LEADING = highest non-contradicted score, at least 3; '
             'NOT_ASSESSABLE = no supporting or contradicting evidence.</p>'
             + _hypothesis_rows(r) + '</section>')

    # 9 limitations and sources
    lim = ''.join(f'<li>{_e(x)}</li>' for x in r['limitations'])
    dis = ''.join(f'<li>{_e(x)}</li>' for x in r['source_disagreements'])
    src = ''.join(f'<li>{_e(x)}</li>' for x in r['sources'])
    s.append('<section><h2>Limitations and sources</h2>'
             f'<ul>{lim}</ul><h3>Known disagreements in the literature</h3><ul>{dis}</ul>'
             f'<h3>Sources</h3><ol>{src}</ol></section>')
    title = f'Band screening: {r["case_name"]}'
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_e(title)}</title><style>{CSS}</style></head><body>'
            + ''.join(s) + '</body></html>\n')


def _speed_envelope(result):
    """Realistic speed envelope used for resonant crossings (from the result)."""
    for rs in result['signatures']['resonance_speeds'].values():
        return rs['realistic_max_exit_speed_m_s']
    return None
