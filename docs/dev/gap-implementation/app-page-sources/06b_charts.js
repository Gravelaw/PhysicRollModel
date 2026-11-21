  // ------------------------------------------------------------------ glossary: first use per screen
  // Technical terms carry a plain-word tooltip the first time they appear on a screen; the
  // terms and meanings are band_plain.GLOSSARY (one source), sent with /api/meta.
  var glossUsed = {};
  function resetGloss() { glossUsed = {}; }
  function gloss(text) {
    var out = esc(text);
    if (!M || !M.glossary) { return out; }
    Object.keys(M.glossary).sort(function (a, b) { return b.length - a.length; }).forEach(function (term) {
      if (glossUsed[term]) { return; }
      var re = new RegExp('(^|[^\\w-])(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + 's?)(?![\\w-])', 'i');
      var m = re.exec(out);
      if (!m || /<[^>]*$/.test(out.slice(0, m.index + m[1].length))) { return; }
      glossUsed[term] = true;
      var at = m.index + m[1].length, word = m[2];
      var tip = esc(term + ': ' + M.glossary[term]);
      out = out.slice(0, at) + '<span class="term mark" tabindex="0" data-tip="' + tip + '" aria-label="' + esc(word) + ' (' + esc(M.glossary[term]) + ')">' + word + '</span>' + out.slice(at + word.length);
    });
    return out;
  }

  // ------------------------------------------------------------------ chart helpers
  // Every chart is drawn from its spec (band_plain): each series ("mark") has one shape, fill,
  // colour and line style, used for the chart AND its legend by the same function; reference
  // lines and ranges are neutral; the axes carry their titles with units; the legend lists only
  // the marks that are not labelled on the chart. Focusable marks give the exact value (hover,
  // keyboard focus, tap); "The same as a list" is the text alternative.
  var COL = {blue: 'var(--blue)', orange: 'var(--orange)', purple: 'var(--purple)', neutral: 'var(--soft)'};
  var TEXTCOL = {blue: 'var(--blue)', orange: 'var(--orange-text)', purple: 'var(--purple)', neutral: 'var(--soft)'};
  var DASH = {solid: '', dashed: '7 4', dotted: '2 3'};
  // the flatness roll chart of the printed page has no card spec: the same marks as the card
  var ZONE_MARKS = {zone_shows: {id: 'zone_shows', label: 'zone that would show', shape: 'bar', fill: 'solid', colour: 'blue', line: 'solid'},
    zone_not: {id: 'zone_not', label: 'zone that would probably not show', shape: 'bar', fill: 'open', colour: 'blue', line: 'solid'},
    profile: {id: 'profile', label: 'modelled flatness', shape: 'line', fill: 'solid', colour: 'orange', line: 'solid'}};
  function markG(inner, tip) {
    return '<g class="mark" tabindex="0" aria-label="' + esc(tip) + '" data-tip="' + esc(tip) + '">' + inner + '</g>';
  }
  function markOf(c, id) {
    var m = ((c && c.marks) || []).filter(function (x) { return x.id === id; })[0];
    return m || ZONE_MARKS[id] || {id: id, label: id, shape: 'circle', fill: 'solid', colour: 'blue', line: 'solid'};
  }
  function paint(m) {
    var col = COL[m.colour] || COL.blue;
    if (m.shape === 'line') { return ' fill="none" stroke="' + col + '" stroke-width="2.4"' + (DASH[m.line] ? ' stroke-dasharray="' + DASH[m.line] + '"' : ''); }
    if (m.fill === 'open') { return ' fill="var(--card)" stroke="' + col + '" stroke-width="2"'; }
    return ' fill="' + col + '"' + (m.shape === 'bar' ? '' : ' stroke="var(--card)" stroke-width="1.5"');
  }
  // one mark at (x, y): the chart and the legend both draw it with this
  function glyph(m, x, y) {
    var tag = ' class="glyph" data-mark="' + esc(m.id) + '"' + paint(m), r = 5;
    if (m.shape === 'diamond') { r = 6; return '<path' + tag + ' d="M' + x + ' ' + (y - r) + 'L' + (x + r) + ' ' + y + 'L' + x + ' ' + (y + r) + 'L' + (x - r) + ' ' + y + 'Z"/>'; }
    if (m.shape === 'square') { return '<rect' + tag + ' x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r + '" height="' + 2 * r + '"/>'; }
    if (m.shape === 'line') { return '<line' + tag + ' x1="' + (x - 11) + '" x2="' + (x + 11) + '" y1="' + y + '" y2="' + y + '"/>'; }
    if (m.shape === 'bar') { return '<rect' + tag + ' x="' + (x - 8) + '" y="' + (y - 5) + '" width="16" height="10"/>'; }
    return '<circle' + tag + ' cx="' + x + '" cy="' + y + '" r="' + r + '"/>';
  }
  function barRect(m, x, y, w, h) { return '<rect class="glyph" data-mark="' + esc(m.id) + '"' + paint(m) + ' x="' + x + '" y="' + y + '" width="' + Math.max(1, w) + '" height="' + Math.max(1, h) + '"/>'; }
  function lineOf(m, pts) { return '<polyline class="glyph" data-mark="' + esc(m.id) + '"' + paint(m) + ' points="' + pts.join(' ') + '"/>'; }
  function labelText(m, x, y, anchor, px) {
    return '<text x="' + x + '" y="' + y + '" font-size="' + (px || 12) + '" style="fill:' + (TEXTCOL[m.colour] || 'var(--ink)') + '"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + ' class="dlab" data-mark="' + esc(m.id) + '">' + esc(m.label) + '</text>';
  }
  // the legend: the marks the spec lists, each drawn by glyph(), wrapped to the width
  function chartLegend(c, w, y0) {
    var ids = (c && c.legend) || [];
    if (!ids.length) { return {s: '', h: 0}; }
    var x = 4, y = y0 + 9, s = '<g class="legend" role="list" aria-label="Legend">';
    ids.forEach(function (id) {
      var m = markOf(c, id), tw = 30 + String(m.label).length * 6.5;
      if (x > 4 && x + tw > w) { x = 4; y += 20; }
      s += '<g class="legend-item" role="listitem" data-mark="' + esc(id) + '">' + glyph(m, x + 11, y) + '<text x="' + (x + 27) + '" y="' + (y + 4) + '" font-size="12">' + esc(m.label) + '</text></g>';
      x += tw + 14;
    });
    return {s: s + '</g>', h: y - y0 + 18};
  }
  function axisWords(a) { return a ? a.title + (a.unit ? ', ' + a.unit : a.dimensionless ? ' (no unit)' : '') : ''; }
  // the x title under the ticks, wrapped; returns {s, h}
  function xTitle(c, y, w) {
    var t = axisWords(c && c.x_axis);
    if (!t) { return {s: '', h: 0}; }
    return {s: wrapText(4, y, t, w - 8, 'class="axis-title" data-axis="x"'), h: wrapLines(t, w - 8).length * 14.4};
  }
  function yTitle(c, x, y) {
    var t = axisWords(c && c.y_axis);
    return t ? '<text x="' + x + '" y="' + y + '" font-size="12" class="axis-title" data-axis="y">' + esc(t) + '</text>' : '';
  }
  function refLine(x1, y1, x2, y2, id) { return '<line class="ref" data-ref="' + esc(id) + '" x1="' + x1 + '" x2="' + x2 + '" y1="' + y1 + '" y2="' + y2 + '"/>'; }
  function refArea(x, y, w, h, id) { return '<rect class="ref-area" data-ref="' + esc(id) + '" x="' + x + '" y="' + y + '" width="' + Math.max(1, w) + '" height="' + h + '"/>'; }
  function refText(x, y, text, anchor) { return '<text class="ref-label" x="' + x + '" y="' + y + '" font-size="11"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + '>' + esc(text) + '</text>'; }
  function refLabel(c, id) { var r = ((c && c.references) || []).filter(function (x) { return x.id === id; })[0]; return r ? r.label : id; }
  function svgOpen(w, h, label) { return '<svg viewBox="0 0 ' + w + ' ' + Math.ceil(h) + '" role="group" aria-label="' + esc(label) + '">'; }
  function niceRange(lo, hi) {
    if (lo === hi) { lo -= 1; hi += 1; }
    var pad = (hi - lo) * 0.08; return [lo - pad, hi + pad];
  }
  function ticks(lo, hi, n) {
    var step = Math.pow(10, Math.floor(Math.log10((hi - lo) / n)));
    [1, 2, 2.5, 5, 10].some(function (k) { if ((hi - lo) / (step * k) <= n) { step *= k; return true; } return false; });
    var out = []; for (var t = Math.ceil(lo / step) * step; t <= hi + 1e-12; t += step) { out.push(Number(t.toFixed(10))); }
    return out;
  }
  function chartWidth() { return drawW(); }
  // words in a chart, broken into lines that fit maxW (about 6.4 px a character at 12 px)
  function wrapLines(text, maxW, px) {
    var n = Math.max(8, Math.floor(maxW / ((px || 12) * 0.54))), out = [], cur = '';
    String(text).split(' ').forEach(function (word) {
      if (cur && (cur + ' ' + word).length > n) { out.push(cur); cur = word; } else { cur = cur ? cur + ' ' + word : word; }
    });
    if (cur) { out.push(cur); }
    return out;
  }
  function wrapText(x, y, text, maxW, attrs, px) {
    var ls = wrapLines(text, maxW, px);
    return '<text x="' + x + '" y="' + y + '" font-size="' + (px || 12) + '" ' + (attrs || '') + '>' + ls.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 1.2 * (px || 12) : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
  }
  // row labels of a chart with one row per pass or record: up to two lines, right-aligned
  // (a "(…)" note goes on its own line; each row is as tall as its label needs)
  function rowLabels(rows, lw, base) {
    var tops = [], hs = [], y = 0;
    var ls = rows.map(function (r) {
      var t = String(r.label || ''), k = t.indexOf(' (');
      var l = k > 0 && t.length * 6.5 > lw - 10 ? [t.slice(0, k)].concat(wrapLines(t.slice(k + 1), lw - 10, 12)) : wrapLines(t, lw - 10, 12);
      return l.slice(0, 4);
    });
    ls.forEach(function (l) { var h = Math.max(base || 24, 10 + 14 * l.length); tops.push(y); hs.push(h); y += h; });
    return {lines: ls, tops: tops, hs: hs, total: y};
  }
  function rowLabel(lines, x, yMid, soft) {
    var y = yMid + 4 - (lines.length - 1) * 7;
    return '<text x="' + x + '" y="' + y + '" font-size="12" text-anchor="end"' + (soft ? ' class="softtext"' : '') + '>' + lines.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 14 : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
  }
  // a horizontal value axis under rows: ticks and their numbers
  function xTicks(tk, X, yTop, yBot, fmt) {
    return tk.map(function (t) { return '<line class="grid" x1="' + X(t) + '" x2="' + X(t) + '" y1="' + yTop + '" y2="' + yBot + '"/><text x="' + X(t) + '" y="' + (yBot + 14) + '" font-size="11" text-anchor="middle">' + (fmt ? fmt(t) : sig(t, 3)) + '</text>'; }).join('');
  }

  // a profile across the strip, on the strip picture's horizontal scale (lines labelled on the chart)
  function widthLines(c) {
    var w = chartWidth(), barrel = c.barrel_length_m || (c.strip_end_m + c.strip_start_m);
    var sx = (w - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var all = []; c.series.forEach(function (s) { all = all.concat(s.values); });
    var r = niceRange(Math.min.apply(null, all.concat([0])), Math.max.apply(null, all.concat([0])));
    var lg = chartLegend(c, w, 0), top = lg.h + 24, hh = 150;
    function Y(v) { return top + (r[1] - v) / (r[1] - r[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 10);
    s += '<rect x="' + X(c.strip_start_m) + '" y="' + top + '" width="' + ((c.strip_end_m - c.strip_start_m) * sx) + '" height="' + hh + '" fill="var(--strip)" opacity=".4"/>';
    ticks(r[0], r[1], 4).forEach(function (t) {
      s += '<line class="grid" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (X(0) + 2) + '" y="' + (Y(t) - 3) + '" font-size="11" class="softtext">' + sig(t, 3) + '</text>';
    });
    s += '<line class="tick" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
    c.series.forEach(function (ser, k) {
      var m = markOf(c, ser.id || ('s' + k));
      s += lineOf(m, ser.z_m.map(function (z, i) { return X(z).toFixed(1) + ',' + Y(ser.values[i]).toFixed(1); }));
      var ip = 0; ser.values.forEach(function (v, i) { if (Math.abs(v) > Math.abs(ser.values[ip])) { ip = i; } });
      var x = X(ser.z_m[ip]), y = Y(ser.values[ip]);
      var tip = ser.label + ': ' + sig(ser.values[ip], 3) + ' ' + c.unit + ' at ' + mmInt(ser.z_m[ip] - c.strip_start_m) + ' from the strip edge (' + (ser.values[ip] > 0 ? 'longer fibre: loose' : 'shorter fibre: tight') + ')';
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, x, y), tip);
      var right = x > w * 0.7;
      s += labelText(m, right ? x - 8 : x + 8, y + (k ? 16 : -8), right ? 'end' : null);
    });
    var yb = top + hh;
    s += '<text x="' + X(c.strip_start_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">0</text><text x="' + X(c.strip_end_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round((c.strip_end_m - c.strip_start_m) * 1000).toLocaleString('en-GB') + '</text>';
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Profile across the strip in ' + c.unit) + s + xt.s + '</svg>';
  }

  // one horizontal bar per row (a share in % or a factor), with one neutral reference line
  function barsChart(c) {
    var m = markOf(c, ((c.marks || [])[0] || {}).id), pct = c.unit === 'percent';
    var w = Math.min(760, chartWidth()), lw = Math.min(200, w * 0.4);
    var rl = rowLabels(c.rows, lw, 26);
    var vals = c.rows.map(function (r) { return r.value; }).concat([c.line]);
    var lo = pct ? 0 : Math.min(0.8, Math.min.apply(null, vals)), hi = pct ? 1 : Math.max.apply(null, vals) * 1.08;
    function X(v) { return lw + (v - lo) / (hi - lo) * (w - lw - 16); }
    function fmt(v) { return pct ? sig(v * 100, 2) + ' %' : sig(v, 3) + ' times'; }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s;
    s += xTicks(pct ? [0, 0.25, 0.5, 0.75, 1] : ticks(lo, hi, 4), X, top, yb, pct ? function (t) { return Math.round(t * 100); } : null);
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i], rowH = rl.hs[i], bh = Math.min(rowH - 8, 18);
      s += rowLabel(rl.lines[i], lw - 8, y + rowH / 2);
      s += markG(barRect(m, X(lo), y + (rowH - bh) / 2, X(r.value) - X(lo), bh), r.tip || (r.label + ': ' + fmt(r.value)));
      var inside = X(r.value) + 4 + fmt(r.value).length * 6.2 > w;     // no room on the right: in the bar
      s += '<text x="' + (inside ? X(r.value) - 4 : X(r.value) + 4) + '" y="' + (y + rowH / 2 + 4) + '" font-size="11"' + (inside ? ' text-anchor="end" class="inbar"' : '') + '>' + fmt(r.value) + '</text>';
    });
    s += refLine(X(c.line), top - 4, X(c.line), yb, (c.references[0] || {}).id || 'line') + refText(X(c.line) + 4, top - 8, c.line_label);
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Bars: ' + axisWords(c.x_axis)) + s + xt.s + '</svg>';
  }

  // per pass, both friction levels on one logarithmic scale (they differ greatly)
  function passLevels(c) {
    var mw = markOf(c, 'with'), mo = markOf(c, 'without');
    var w = Math.min(760, chartWidth()), lw = Math.min(210, w * 0.4);
    var rows = c.rows.map(function (r) { var l = String(r.label); return {label: r.credible ? l : /\)$/.test(l) ? l.slice(0, -1) + ', not credible)' : l + ' (not credible)'}; });
    var rl = rowLabels(rows, lw, 26);
    var vals = []; c.rows.forEach(function (r) { vals.push(Math.abs(r.with_feedback), Math.abs(r.compliance_only)); });
    var lo = Math.floor(Math.log10(Math.min.apply(null, vals))), hi = Math.ceil(Math.log10(Math.max.apply(null, vals)));
    function X(v) { return lw + (Math.log10(Math.abs(v)) - lo) / (hi - lo) * (w - lw - 20); }
    var lg = chartLegend(c, w, 0), top = lg.h + 8, yb = top + rl.total;
    var s = lg.s;
    var tk = []; for (var e = lo; e <= hi; e++) { tk.push(Math.pow(10, e)); }
    s += xTicks(tk, X, top, yb, function (t) { return sig(t, 1); });
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y, !r.credible);
      s += '<line class="tick" x1="' + X(r.with_feedback) + '" x2="' + X(r.compliance_only) + '" y1="' + y + '" y2="' + y + '"/>';
      s += markG(glyph(mw, X(r.with_feedback), y), r.label + ', ' + mw.label + ': ' + sig(r.with_feedback, 2) + ' I-units for 1 % more friction at one place');
      s += markG(glyph(mo, X(r.compliance_only), y), r.label + ', without the feedback (compliance alone): ' + sig(r.compliance_only, 2) + ' I-units for 1 % more friction');
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Flatness per 1 % friction, with and without the exit-tension feedback, per pass') + s + xt.s + '</svg>';
  }

  // friction from each measured quantity, with the range its measuring error allows
  var KIND_WORDS = {force: 'from the force', slip: 'from the forward slip', torque: 'from the torque'};
  function recordsChart(c) {
    var w = Math.min(760, chartWidth()), lw = Math.min(150, w * 0.28);
    var rl = rowLabels(c.rows, lw, Math.max(26, 12 + 10 * Math.max.apply(null, c.rows.map(function (r) { return r.points.length; }))));
    var vals = [c.case_value]; c.rows.forEach(function (r) { r.points.forEach(function (p) { vals.push(p.value, p.low, p.high); }); });
    vals = vals.filter(isNum);
    var rg = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals));
    function X(v) { return lw + (v - rg[0]) / (rg[1] - rg[0]) * (w - lw - 16); }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s + xTicks(ticks(rg[0], rg[1], 4), X, top, yb);
    if (isNum(c.case_value)) {
      var xc = X(c.case_value), right = xc > w * 0.75;
      s += markG(refLine(xc, top - 4, xc, yb, 'case'), refLabel(c, 'case') + ': a friction coefficient of ' + sig(c.case_value, 3) + ' (no unit)') + refText(right ? xc - 4 : xc + 4, top - 8, refLabel(c, 'case'), right ? 'end' : null);
    }
    c.rows.forEach(function (r, i) {
      var y0 = top + rl.tops[i], rowH = rl.hs[i], n = r.points.length;
      s += rowLabel(rl.lines[i], lw - 8, y0 + rowH / 2);
      r.points.forEach(function (p, k) {
        var m = markOf(c, p.kind), y = y0 + rowH / 2 + (k - (n - 1) / 2) * 10;
        if (isNum(p.low) && isNum(p.high)) { s += '<line class="interval" data-mark="' + esc(m.id) + '" stroke="' + COL[m.colour] + '" x1="' + X(p.low) + '" x2="' + X(p.high) + '" y1="' + y + '" y2="' + y + '"/>'; }
        s += markG(glyph(m, X(p.value), y), r.label + ', friction ' + KIND_WORDS[p.kind] + ': ' + sig(p.value, 3) + ' (no unit)' + (isNum(p.low) ? ', between ' + sig(p.low, 3) + ' and ' + sig(p.high, 3) + ' for the measuring error' : ''));
      });
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Friction from each pass record') + s + xt.s + '</svg>';
  }

  // the roll surface over one turn: temperature against angle after the roll gap
  function cycleChart(c) {
    var w = Math.min(860, chartWidth()), l = 34, r = Math.round(Math.min(170, w * 0.3)), hh = 170;
    // labels at the line ends where each fits on one line; otherwise (a phone) the legend lists
    // the same marks, drawn the same way, and the plot takes the whole width
    var fits = c.series.every(function (ser, k) { return wrapLines(markOf(c, 's' + k).label, r - 10, 11).length === 1; });
    if (!fits) { c = Object.assign({}, c, {legend: c.series.map(function (ser, k) { return 's' + k; })}); r = 14; }
    var lg = chartLegend(c, w, 0), top = lg.h + 26;
    var labs = [], all = []; c.series.forEach(function (s) { all = all.concat(s.temperature_k); });
    var rg = niceRange(Math.min.apply(null, all) - 273.15, Math.max.apply(null, all) - 273.15);
    function X(a) { return l + a / 360 * (w - l - r); }
    function Y(tc) { return top + (rg[1] - tc) / (rg[1] - rg[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 12);
    ticks(rg[0], rg[1], 5).forEach(function (t) { s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (l - 4) + '" y="' + (Y(t) + 4) + '" font-size="11" text-anchor="end">' + sig(t, 3) + '</text>'; });
    [0, 90, 180, 270, 360].forEach(function (a) { s += '<text x="' + X(a) + '" y="' + (top + hh + 15) + '" font-size="11" text-anchor="middle">' + a + '</text>'; });
    c.series.forEach(function (ser, k) {
      var m = markOf(c, 's' + k);
      // unwrap the angle so the line runs 0..360 from the roll gap exit
      var pts = ser.angle_deg.map(function (a, i) { return [a, ser.temperature_k[i] - 273.15]; }).sort(function (p, q) { return p[0] - q[0]; });
      s += lineOf(m, pts.map(function (p) { return X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }));
      var end = pts[pts.length - 1];
      labs.push({m: m, y: Y(end[1]) + 4});
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, X(end[0]), Y(end[1])), ser.label + ': ' + sig(end[1], 3) + ' °C just before the roll gap');
    });
    // labels beside the line ends, pushed apart and kept inside the plot
    labs.sort(function (a, b) { return a.y - b.y; });
    var prev = top + 4;
    labs.forEach(function (lb) { lb.ls = wrapLines(lb.m.label, r - 10, 11); lb.y = Math.max(lb.y, prev); prev = lb.y + lb.ls.length * 13.2 + 3; });
    var floor = top + hh;
    for (var j = labs.length - 1; j >= 0; j--) {
      var lim = j === labs.length - 1 ? floor - (labs[j].ls.length - 1) * 13.2 : labs[j + 1].y - labs[j].ls.length * 13.2 - 3;
      if (labs[j].y > lim) { labs[j].y = lim; }
    }
    if (!fits) { labs = []; }
    labs.forEach(function (lb) {
      var x = w - r + 8;
      s += '<text x="' + x + '" y="' + lb.y + '" font-size="11" style="fill:' + TEXTCOL[lb.m.colour] + '" class="dlab" data-mark="' + esc(lb.m.id) + '">' + lb.ls.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 13.2 : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
    });
    var yb = top + hh, xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Roll surface temperature over one turn at three places') + s + xt.s + '</svg>';
  }

  // heat share per pass: entered and computed, with the measured range as a neutral area
  function sharesChart(c) {
    var me = markOf(c, 'entered'), mc = markOf(c, 'computed');
    var w = Math.min(760, chartWidth()), lw = Math.min(200, w * 0.4);
    var rl = rowLabels(c.rows, lw, 24);
    function X(v) { return lw + v * (w - lw - 16); }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s;
    if (c.band) {
      s += markG(refArea(X(c.band[0]), top, X(c.band[1]) - X(c.band[0]), rl.total, 'measured'), refLabel(c, 'measured') + ': ' + sig(c.band[0] * 100, 2) + ' to ' + sig(c.band[1] * 100, 2) + ' % of the heat stays in the strip');
      s += refText(X(c.band[1]) + 4, top - 8, refLabel(c, 'measured'));
    }
    s += xTicks([0, 0.25, 0.5, 0.75, 1], X, top, yb, function (t) { return Math.round(t * 100); });
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y);
      if (isNum(r.entered)) { s += markG(glyph(me, X(r.entered), y), r.label + ', entered: ' + sig(r.entered * 100, 2) + ' % of the heat stays in the strip'); }
      s += markG(glyph(mc, X(Math.max(0, Math.min(1, r.computed))), y), r.label + ', computed by the tool: ' + sig(r.computed * 100, 2) + ' %');
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Heat share to the strip per pass, entered and computed') + s + xt.s + '</svg>';
  }

  // the published foil case on one line: two models, the published figure and the equations' range
  function loadsChart(c) {
    var w = Math.min(760, chartWidth()), l = 16, r = 16, y = 30;
    var lo = Math.min(c.range[0], c.points[1].value) - 10, hi = Math.max(c.range[1], c.published) + 10;
    function X(v) { return l + (v - lo) / (hi - lo) * (w - l - r); }
    var s = '<line class="tick" x1="' + X(lo) + '" x2="' + X(hi) + '" y1="' + y + '" y2="' + y + '"/>';
    s += markG(refArea(X(c.range[0]), y - 12, X(c.range[1]) - X(c.range[0]), 24, 'family'), refLabel(c, 'family') + ' give a load of ' + Math.round(c.range[0]) + ' to ' + Math.round(c.range[1]) + ' (no unit), depending on a detail the paper does not state');
    s += markG(refLine(X(c.published), y - 16, X(c.published), y + 16, 'published'), 'Published figure: a load of ' + c.published + ' (no unit)');
    s += refText(X(c.published), y + 30, refLabel(c, 'published'), 'middle');
    var fam = refLabel(c, 'family') + ': ' + Math.round(c.range[0]) + ' to ' + Math.round(c.range[1]), fx = X(c.range[0]);
    s += refText(fx + fam.length * 5.8 > w ? w - 2 : fx, y + 46, fam, fx + fam.length * 5.8 > w ? 'end' : null);
    s += ticks(lo, hi, 5).map(function (t) { return '<text x="' + X(t) + '" y="' + (y + 64) + '" font-size="11" text-anchor="middle">' + sig(t, 3) + '</text>'; }).join('');
    // the first model's label above the line, the second's below it: they never meet
    c.points.forEach(function (p, k) {
      var m = markOf(c, p.id), xl = X(p.value), left = xl < w * 0.6;
      s += markG(glyph(m, xl, y), p.label + ': a load of ' + Math.round(p.value) + ' (no unit) on the published foil case');
      s += labelText({id: m.id, label: p.label + ' ' + Math.round(p.value), colour: m.colour}, left ? Math.max(2, xl - 6) : Math.min(w - 2, xl + 6), k ? y + 30 : y - 18, left ? null : 'end', 11);
    });
    var xt = xTitle(c, y + 84, w);
    return svgOpen(w, y + 74 + xt.h, 'Loads on the one published foil case') + s + xt.s + '</svg>';
  }

  // the one range chart: for each row a bar from low to high (the possible range), the value the
  // scores or the model use as a distinct mark, other values as points; neutral reference lines
  function rangeChart(c) {
    var w = Math.min(760, chartWidth()), lw = Math.min(170, w * 0.32);
    var rl = rowLabels(c.rows, lw, 30);
    var vals = [];
    c.rows.forEach(function (r) { [r.low, r.high].concat(r.points.map(function (p) { return p.value; })).forEach(function (v) { if (isNum(v)) { vals.push(v); } }); });
    (c.references || []).forEach(function (x) { if (isNum(x.value)) { vals.push(x.value); } });
    var log = !!c.log && vals.every(function (v) { return v > 0; });
    var lo, hi, X, tk;
    if (log) {
      lo = Math.floor(Math.log10(Math.min.apply(null, vals))); hi = Math.ceil(Math.log10(Math.max.apply(null, vals)));
      if (hi === lo) { hi += 1; }
      X = function (v) { return lw + (Math.log10(v) - lo) / (hi - lo) * (w - lw - 20); };
      tk = []; for (var e = lo; e <= hi; e++) { tk.push(Math.pow(10, e)); }
    } else {
      var rg = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals)); lo = rg[0]; hi = rg[1];
      X = function (v) { return lw + (v - lo) / (hi - lo) * (w - lw - 20); };
      tk = ticks(lo, hi, w < 500 ? 3 : 5);
    }
    var refs = (c.references || []).filter(function (x) { return isNum(x.value); });
    var lg = chartLegend(c, w, 0), top = lg.h + 8 + refs.length * 14, yb = top + rl.total;
    var s = lg.s + xTicks(tk, X, top, yb, function (t) { return sig(t, 3); });
    refs.forEach(function (x, k) {
      var xr = X(x.value), right = xr > w * 0.7;
      s += markG(refLine(xr, top - 4, xr, yb, x.id), x.tip || (x.label + ': ' + sig(x.value, 3) + ' ' + axisWords(c.x_axis)));
      s += refText(right ? xr - 4 : xr + 4, lg.h + 10 + k * 14, x.label, right ? 'end' : null);
    });
    var mr = markOf(c, 'range');
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y);
      if (isNum(r.low) && isNum(r.high) && r.high > r.low && (c.marks || []).some(function (m) { return m.id === 'range'; })) {
        s += markG(barRect(mr, X(r.low), y - 7, X(r.high) - X(r.low), 14), r.label + ': from ' + sig(r.low, 3) + ' to ' + sig(r.high, 3) + ' ' + (r.unit || 'no unit') + (r.meaning ? '; ' + r.meaning : ''));
      }
      // the value the scores use is drawn last, so that no other point hides it
      r.points.slice().sort(function (a, b) { return (a.id === 'used') - (b.id === 'used'); }).forEach(function (p) { s += markG(glyph(markOf(c, p.id), X(p.value), y), p.tip || (r.label + ': ' + sig(p.value, 3))); });
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Range: ' + axisWords(c.x_axis)) + s + xt.s + '</svg>';
  }

  // the valve map of the flatness loop: one row per valve, its level as the shade over time, and
  // under it the largest zone error the flatness roll would read
  function valveMap(c) {
    var w = chartWidth(), l = 34, r = 8, mv = markOf(c, 'level'), me = markOf(c, 'error');
    var n = (c.levels[0] || []).length, rowH = Math.max(5, Math.min(12, Math.floor(160 / Math.max(1, n))));
    var lg = chartLegend(c, w, 0), top = lg.h + 22, mapH = n * rowH, gap = 30, errH = 70;
    var t0 = 0, t1 = c.time_s[c.time_s.length - 1] || 1;
    function X(t) { return l + (t - t0) / (t1 - t0) * (w - l - r); }
    var s = lg.s + '<text x="4" y="' + (top - 8) + '" font-size="12" class="axis-title" data-axis="y">valve (control zone), 1 at the top</text>';
    for (var z = 0; z < n; z++) {
      var k0 = 0;
      for (var k = 1; k <= c.time_s.length; k++) {
        if (k === c.time_s.length || c.levels[k][z] !== c.levels[k0][z]) {
          var lev = c.levels[k0][z], xa = X(k0 ? c.time_s[k0 - 1] : t0), xb = X(c.time_s[k - 1]);
          // closed is a pale tint with an outline (never the card itself), open the full colour;
          // the lightness ramp is steep in the upper half, where most valves sit
          var op = 0.1 + 0.9 * Math.pow(lev, 2.2);
          s += '<rect class="valve-outline" x="' + xa + '" y="' + (top + z * rowH) + '" width="' + Math.max(1, xb - xa) + '" height="' + (rowH - 1) + '"/>';
          s += markG(barRect(mv, xa, top + z * rowH, xb - xa, rowH - 1).replace('/>', ' fill-opacity="' + op.toFixed(2) + '"/>'),
            'Valve ' + (z + 1) + ': ' + Math.round(lev * 100) + ' % open from ' + Math.round(k0 ? c.time_s[k0 - 1] : 0) + ' s to ' + Math.round(c.time_s[k - 1]) + ' s');
          if (k < c.time_s.length) { s += '<line class="valve-change" x1="' + xb + '" x2="' + xb + '" y1="' + (top + z * rowH) + '" y2="' + (top + z * rowH + rowH - 1) + '"/>'; }
          k0 = k;
        }
      }
      if (w >= 600 || z % Math.max(1, Math.ceil(n / 7)) === 0) { s += '<text x="' + (l - 4) + '" y="' + (top + z * rowH + rowH - 1) + '" font-size="10" text-anchor="end">' + (z + 1) + '</text>'; }
    }
    var e = c.error || {}, ey = top + mapH + gap, emax = Math.max.apply(null, (e.i_units || [1]).concat([1]));
    function Y(v) { return ey + errH - v / emax * errH; }
    s += '<text x="4" y="' + (ey - 8) + '" font-size="12" class="axis-title" data-axis="y2">' + esc(me.label) + '</text>';
    s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/><text x="' + (l - 4) + '" y="' + (Y(emax) + 4) + '" font-size="10" text-anchor="end">' + sig(emax, 2) + '</text><text x="' + (l - 4) + '" y="' + (Y(0) + 4) + '" font-size="10" text-anchor="end">0</text>';
    if (e.time_s && e.time_s.length) {
      s += lineOf(me, e.time_s.map(function (t, i) { return X(t).toFixed(1) + ',' + Y(e.i_units[i]).toFixed(1); }));
      var ip = 0; e.i_units.forEach(function (v, i) { if (v > e.i_units[ip]) { ip = i; } });
      s += markG(glyph({id: me.id, shape: 'circle', fill: 'solid', colour: me.colour}, X(e.time_s[ip]), Y(e.i_units[ip])), 'Largest zone error ' + sig(e.i_units[ip], 3) + ' I-units at ' + Math.round(e.time_s[ip]) + ' s');
    }
    var yb = ey + errH;
    s += ticks(t0, t1, w < 500 ? 3 : 6).map(function (t) { return '<text x="' + X(t) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round(t) + '</text>'; }).join('');
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Valve levels over time and the largest zone error') + s + xt.s + '</svg>';
  }

  // the zone step test: what the flatness roll zone would read after the zone was closed
  function stepResponse(c) {
    var w = Math.min(860, chartWidth()), l = 40, r = Math.round(Math.min(170, w * 0.3)), hh = 150;
    var fits = c.curves.every(function (cv, k) { return wrapLines(markOf(c, 'c' + k).label, r - 10, 11).length === 1; });
    if (!fits) { c = Object.assign({}, c, {legend: c.curves.map(function (cv, k) { return 'c' + k; })}); r = 12; }
    var lg = chartLegend(c, w, 0), top = lg.h + 26, all = [0], tmax = 0;
    c.curves.forEach(function (cv) { all = all.concat(cv.i_units); tmax = Math.max(tmax, cv.time_s[cv.time_s.length - 1]); });
    var rg = niceRange(Math.min.apply(null, all), Math.max.apply(null, all));
    function X(t) { return l + t / tmax * (w - l - r); }
    function Y(v) { return top + (rg[1] - v) / (rg[1] - rg[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 12);
    ticks(rg[0], rg[1], 4).forEach(function (t) { s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (l - 4) + '" y="' + (Y(t) + 4) + '" font-size="11" text-anchor="end">' + sig(t, 3) + '</text>'; });
    (c.references || []).forEach(function (x) {
      if (!isNum(x.value)) { return; }
      s += markG(refLine(X(x.value), top, X(x.value), top + hh, x.id), x.tip || (x.label + ': ' + sig(x.value, 3) + ' s'));
      s += refText(X(x.value) + 4, top + 12, x.label);
    });
    c.curves.forEach(function (cv, k) {
      var m = markOf(c, 'c' + k), step = Math.max(1, Math.floor(cv.time_s.length / 300));
      s += lineOf(m, cv.time_s.filter(function (t, i) { return i % step === 0; }).map(function (t, j) { var i = j * step; return X(t).toFixed(1) + ',' + Y(cv.i_units[i]).toFixed(1); }));
      var e = cv.time_s.length - 1;
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, X(cv.time_s[e]), Y(cv.i_units[e])), cv.label + ': ' + sig(cv.i_units[e], 3) + ' I-units after ' + Math.round(cv.time_s[e]) + ' s');
      if (fits) { s += labelText({id: m.id, label: cv.label, colour: m.colour}, w - r + 6, Y(cv.i_units[e]) + 4 + (k - 1) * 13, null, 11); }
    });
    var yb = top + hh;
    s += ticks(0, tmax, w < 500 ? 3 : 6).map(function (t) { return '<text x="' + X(t) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round(t) + '</text>'; }).join('');
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Zone step test: flatness roll reading over time') + s + xt.s + '</svg>';
  }

  function chartSvg(c) {
    if (!c) { return ''; }
    if (c.type === 'zones') { return shapemeterSvg(c, false, c); }
    if (c.type === 'width_lines') { return widthLines(c); }
    if (c.type === 'bars') { return barsChart(c); }
    if (c.type === 'pass_levels') { return passLevels(c); }
    if (c.type === 'records') { return recordsChart(c); }
    if (c.type === 'cycle') { return cycleChart(c); }
    if (c.type === 'shares') { return sharesChart(c); }
    if (c.type === 'loads') { return loadsChart(c); }
    if (c.type === 'range') { return rangeChart(c); }
    if (c.type === 'valve_map') { return valveMap(c); }
    if (c.type === 'step_response') { return stepResponse(c); }
    return '';
  }

  // ------------------------------------------------------------------ the one add-on card pattern
  function addonCard(card) {
    var h = '<section class="card addon noprint" id="' + card.id + '"><h2>' + esc(card.title) + '</h2>';
    h += '<p class="takeaway-line">' + gloss(card.takeaway) + '</p>';
    if (card.left_out) {
      return h + (S.run ? '<button type="button" class="btn" data-rerun="' + S.run.id + '" data-profile="detailed">Run in detail</button>' : '') + '</section>';
    }
    if (card.chart) { h += '<div class="fig">' + chartSvg(card.chart) + '</div>'; }
    h += '<p class="howto">' + gloss(card.how_to_read) + '</p>';
    if (card.caveat) { h += '<p class="warnline">' + gloss(card.caveat) + '</p>'; }
    // one fold: the details, then the chart as a list (its text alternative)
    h += '<details class="more"><summary>' + (card.details.length ? 'Details, and the chart as a list' : 'The chart as a list') + '</summary>' +
      (card.details.length ? '<ul class="small">' + card.details.map(function (d) { return '<li>' + gloss(d) + '</li>'; }).join('') + '</ul>' : '') +
      (card.details.length ? '<p class="small"><strong>The chart as a list</strong></p>' : '') + '<ul class="small">' + card.text_alternative.map(function (d) { return '<li>' + esc(d) + '</li>'; }).join('') + '</ul></details>';
    return h + '<p class="small soft">From "' + esc(card.group_title) + '" in step 3.</p></section>';
  }
  function addonCards(sum) {
    var cards = sum.addon_cards || [], by = {};
    cards.forEach(function (c) { by[c.id] = c; });
    var h = (sum.addon_sections || []).map(function (sec) {
      var open = S.openSections && S.openSections[sec.group];
      return '<details class="addon-section card noprint" id="sec-' + sec.group + '" data-section="' + sec.group + '"' + (open ? ' open' : '') + '><summary><span class="s-title">' + esc(sec.title) + '</span> <span class="small soft">' +
        sec.cards.length + (sec.cards.length === 1 ? ' card' : ' cards') + '</span><span class="s-line">' + esc(sec.summary) + '</span></summary>' +
        sec.cards.map(function (id) { return addonCard(by[id]); }).join('') + '</details>';
    }).join('');
    if (sum.addon_more && sum.addon_more.text) { h += '<p class="small soft quietline noprint">' + esc(sum.addon_more.text) + '</p>'; }
    return h;
  }

  // the index near the top: one link per heading (nothing when nothing was added)
  function addonIndex(sum) {
    var secs = sum.addon_sections || [];
    if (!secs.length) { return ''; }
    return '<nav class="addon-index noprint" aria-label="From what you added"><span class="small">From what you added:</span> ' + secs.map(function (sec) {
      return '<a href="#sec-' + sec.group + '" data-open-section="' + sec.group + '">' + esc(sec.title) + '</a>';
    }).join('<span class="sep" aria-hidden="true"> · </span>') + '</nav>';
  }

  // ------------------------------------------------------------------ the add-on area of step 3
  function addonStatusHtml(gid) {
    var st = (model().addons || {})[gid] || {filled: false, summary: 'not filled in'};
    return '<span class="g-state ' + (st.filled ? 'filled' : 'empty') + '">' + (st.filled ? '<span aria-hidden="true">●</span> ' : '<span aria-hidden="true">○</span> ') + esc(st.summary) + '</span>';
  }
  function addonClearHtml(gid) {
    var st = (model().addons || {})[gid] || {}, g = M.addon_groups.filter(function (x) { return x.id === gid; })[0];
    return st.filled && g ? '<button type="button" class="btn link g-clear" data-clear-group="' + gid + '" aria-label="Clear ' + esc(g.title) + '">Clear</button>' : '';
  }
  function addonCountHtml() {
    var a = model().addons || {}, n = Object.keys(a).filter(function (k) { return a[k].filled; }).length;
    return n ? n + ' of ' + M.addon_groups.length + ' in use' : 'none in use';
  }
  function addonArea() {
    resetGloss();
    var open = S.openMore && S.openMore.addons;
    var h = '<details class="addons" data-more="addons"' + (open ? ' open' : '') + '><summary><span class="a-title">Add what else you have (optional)</span> <span class="small soft" data-view="addoncount">' + addonCountHtml() + '</span></summary>' +
      '<p class="howto">A flatness roll, a gauge, a scan, pass records, oil data, or a model choice: each adds what it would show to the result. None of them changes the shortlist unless a model choice says so.</p><ul class="groups">';
    M.addon_groups.forEach(function (g) {
      var qs = g.questions.map(function (id) { return Q[id]; }).filter(function (q) { return q && shown(q) && visible(q); });
      var gopen = S.openGroups && S.openGroups[g.id];
      h += '<li class="addon-group"><details data-group="' + g.id + '"' + (gopen ? ' open' : '') + '><summary><span class="g-title">' + esc(g.title) + '</span><span data-view="addon:' + g.id + '">' + addonStatusHtml(g.id) + '</span></summary>' +
        '<p class="help">' + gloss(g.help) + '</p>' + qs.map(function (q) { return renderQ(q); }).join('') +
        '</details><span data-view="addonclear:' + g.id + '">' + addonClearHtml(g.id) + '</span></li>';
    });
    return h + '</ul></details>';
  }
  function clearGroup(gid) {
    var g = M.addon_groups.filter(function (x) { return x.id === gid; })[0];
    if (!g) { return; }
    g.questions.forEach(function (id) {
      var q = Q[id]; if (!q) { return; }
      if (q.origin_tracked) { S.answers.values[id] = clone(pv(id)); S.answers.origins[id] = 'preset'; }
      else { S.answers.values[id] = null; }
      S.touched[id] = true;
    });
    touch(); render(); checkNow();
    announce(g.title + ': cleared');
  }
