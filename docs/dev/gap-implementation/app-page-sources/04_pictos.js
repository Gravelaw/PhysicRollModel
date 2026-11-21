  // ------------------------------------------------------------------ pictograms (one per cause)
  // Simple labelled sketches of the mechanism in each cause's description; no added physics.
  var STRK = ' fill="none" stroke="var(--ink)" stroke-width="2"';
  function T(x, y, s, a) { return '<text class="lbl" x="' + x + '" y="' + y + '" font-size="9"' + (a ? ' text-anchor="' + a + '"' : '') + '>' + s + '</text>'; }
  function strip(y) { return '<rect x="6" y="' + y + '" width="108" height="14" fill="var(--strip)" stroke="var(--strip-edge)"/>'; }
  function roll(cx, cy, r) { return '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>'; }
  var PICTOS = {
    nozzle: '<rect x="8" y="6" width="104" height="6" fill="var(--soft)"/>' +
      [20, 46, 72, 98].map(function (x, i) {
        return i === 2 ? '<circle cx="' + x + '" cy="16" r="5" fill="var(--ink)"/><path d="M' + (x - 3) + ' 13l6 6m0-6l-6 6" stroke="var(--card)" stroke-width="1.5"/>'
          : '<circle cx="' + x + '" cy="16" r="5" fill="var(--card)" stroke="var(--ink)"/><path d="M' + x + ' 21l-10 22h20z" fill="var(--blue)" opacity=".3"/>';
      }).join('') + '<rect x="6" y="44" width="108" height="16" rx="3" fill="var(--panel)" stroke="var(--ink)"/>' +
      '<path d="M60 44q12-9 24 0" fill="var(--orange)" stroke="var(--orange)"/>' + strip(62) + T(72, 36, 'blocked', 'middle') + T(110, 75, 'loose band', 'end'),
    zone_valve: '<rect x="8" y="6" width="104" height="6" fill="var(--soft)"/><path d="M62 4l12 10v-10l-12 10z" fill="var(--ink)"/>' +
      '<rect x="6" y="40" width="108" height="16" rx="3" fill="var(--panel)" stroke="var(--ink)"/><path d="M56 40q12-8 24 0" fill="var(--orange)" stroke="var(--orange)"/>' +
      '<circle cx="24" cy="26" r="9"' + STRK + '/><path d="M24 26v-6m0 6h5"' + STRK + '/>' + strip(60) + T(80, 28, 'valve off') + T(110, 74, 'comes and goes', 'end'),
    roll_band: '<ellipse cx="60" cy="30" rx="50" ry="16" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' +
      '<rect x="64" y="14" width="10" height="32" fill="url(#hatch)" stroke="var(--ink)"/>' + strip(54) + '<rect x="64" y="54" width="10" height="14" fill="var(--ink)" opacity=".5"/>' +
      T(78, 12, 'worn band') + T(110, 78, 'same place', 'end'),
    grinder: '<ellipse cx="54" cy="30" rx="46" ry="16" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' +
      [20, 30, 40, 50, 60, 70, 80].map(function (x) { return '<path d="M' + x + ' 16l8 28" stroke="var(--soft)"/>'; }).join('') +
      '<circle cx="106" cy="28" r="10"' + STRK + '/>' + strip(56) + T(106, 50, 'grinder', 'middle') + T(8, 78, 'fine spiral lines'),
    coil_ridge: '<circle cx="44" cy="38" r="30"' + STRK + '/><circle cx="44" cy="38" r="20"' + STRK + '/><circle cx="44" cy="38" r="9"' + STRK + '/>' +
      '<path d="M44 8q6-5 0-10M44 18q6-5 0-10" stroke="var(--orange)" stroke-width="3" fill="none"/>' + T(80, 20, 'ridge builds') + T(80, 32, 'up wrap on') + T(80, 44, 'wrap'),
    troughs: roll(14, 40, 10) + roll(106, 40, 10) + '<path d="M14 30h92M14 50h92" stroke="var(--strip-edge)"/>' +
      '<path d="M24 36q10 4 20 0t20 0t20 0t18 0M24 44q10 4 20 0t20 0t20 0t18 0" fill="none" stroke="var(--ink)"/>' + T(60, 70, 'troughs in the free span', 'middle'),
    profile: '<path d="M8 50q10-14 20 0t20 0h40q10 14 20 0t4 0" fill="none" stroke="var(--ink)" stroke-width="2"/>' +
      '<rect x="8" y="56" width="104" height="10" fill="var(--strip)" stroke="var(--strip-edge)"/>' + T(60, 24, 'edge waves', 'middle') + T(60, 78, 'across the width', 'middle'),
    oil_film: roll(60, 20, 16) + '<path d="M10 40h100" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M44 37q8-5 16 0" stroke="var(--blue)" stroke-width="3" fill="none"/>' +
      '<rect x="70" y="44" width="12" height="20" fill="var(--soft)" opacity=".45"/>' + strip(60) + T(8, 56, 'thin film') + T(110, 78, 'milky streak', 'end'),
    drips: '<rect x="20" y="6" width="80" height="8" fill="var(--soft)"/>' +
      [40, 62, 84].map(function (x) { return '<path d="M' + x + ' 18q-5 9 0 12q5-3 0-12z" fill="var(--blue)"/>'; }).join('') +
      strip(48) + '<ellipse cx="62" cy="55" rx="10" ry="4" fill="var(--soft)" opacity=".6"/>' + T(60, 76, 'stain after annealing', 'middle'),
    tension_lines: strip(26) + '<rect x="6" y="26" width="108" height="30" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      [16, 22, 28, 34, 40, 46].map(function (y) { return '<path d="M10 ' + (y + 10) + 'h100" stroke="var(--ink)" stroke-width=".8"/>'; }).join('') +
      '<path d="M8 66h20m-6-4l6 4-6 4" stroke="var(--ink)" fill="none"/>' + T(34, 70, 'low tension: fine lines'),
    chatter: roll(40, 18, 12) + roll(40, 52, 12) + '<path d="M58 14q4 4 0 8M64 10q6 8 0 16M58 48q4 4 0 8M64 44q6 8 0 16" fill="none" stroke="var(--orange)" stroke-width="2"/>' +
      '<path d="M4 35h112" stroke="var(--strip-edge)" stroke-width="5"/>' + [76, 86, 96, 106].map(function (x) { return '<path d="M' + x + ' 31v8" stroke="var(--ink)" stroke-width="2"/>'; }).join('') +
      T(72, 76, 'gap opens and closes'),
    stack_resonance: roll(30, 12, 9) + roll(30, 30, 6) + roll(30, 44, 6) + roll(30, 62, 9) +
      '<path d="M44 26v-6m0 0l-3 4m3-4l3 4M44 40v-6m0 0l-3 4m3-4l3 4" stroke="var(--orange)" stroke-width="2" fill="none"/>' +
      '<path d="M52 37h64" stroke="var(--strip-edge)" stroke-width="4"/>' + T(58, 20, 'work rolls move') + T(58, 30, 'together (600-1200 Hz)'),
    work_roll_mark: roll(30, 26, 18) + '<circle cx="30" cy="44" r="3" fill="var(--orange)"/>' + '<path d="M4 50h112" stroke="var(--strip-edge)" stroke-width="5"/>' +
      [30, 72, 114].map(function (x) { return '<path d="M' + x + ' 46v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      '<path d="M30 62h42m-4-3l4 3-4 3" stroke="var(--ink)" fill="none"/>' + T(34, 76, 'once per work-roll turn'),
    backup_roll_mark: roll(32, 20, 17) + roll(32, 45, 8) + '<circle cx="32" cy="3" r="3" fill="var(--orange)"/>' +
      '<path d="M4 56h112" stroke="var(--strip-edge)" stroke-width="5"/>' + [40, 100].map(function (x) { return '<path d="M' + x + ' 52v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      T(56, 22, 'mark on backup roll') + T(60, 74, 'once per backup-roll turn', 'middle'),
    bearing_gear: '<circle cx="34" cy="36" r="20"' + STRK + '/>' +
      [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(function (a) {
        var r = a * Math.PI / 180; return '<path d="M' + (34 + 20 * Math.cos(r)).toFixed(1) + ' ' + (36 + 20 * Math.sin(r)).toFixed(1) + 'L' + (34 + 26 * Math.cos(r)).toFixed(1) + ' ' + (36 + 26 * Math.sin(r)).toFixed(1) + '" stroke="var(--ink)" stroke-width="3"/>';
      }).join('') + '<circle cx="34" cy="36" r="6" fill="var(--ink)"/>' + T(66, 30, 'fixed multiple') + T(66, 42, 'of roll turns'),
    drive_twist: '<rect x="6" y="28" width="24" height="20" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' + roll(102, 38, 12) +
      '<path d="M30 38h60" stroke="var(--ink)" stroke-width="4"/><path d="M50 26q8 12 0 24M62 26q8 12 0 24" fill="none" stroke="var(--orange)" stroke-width="2"/>' +
      T(18, 22, 'motor', 'middle') + T(60, 66, 'shaft twists 5-30 Hz', 'middle'),
    coil_mark: '<circle cx="34" cy="38" r="28"' + STRK + '/><circle cx="34" cy="38" r="8"' + STRK + '/><path d="M34 10v8" stroke="var(--orange)" stroke-width="4"/>' +
      '<path d="M62 38h54" stroke="var(--strip-edge)" stroke-width="5"/>' + [70, 110].map(function (x) { return '<path d="M' + x + ' 34v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      T(90, 26, 'once per coil turn', 'middle'),
    yield_bend: roll(60, 46, 16) + '<path d="M6 22q40 0 54 8q14 8 54-8" fill="none" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M44 20l3 8M52 22l3 8M66 22l3 8" stroke="var(--ink)"/>' + T(60, 76, 'yields unevenly when bent', 'middle'),
    herringbone: strip(22) + '<rect x="6" y="22" width="108" height="36" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      [20, 44, 68, 92].map(function (x) { return '<path d="M' + x + ' 26l10 14-10 14" fill="none" stroke="var(--ink)" stroke-width="2"/>'; }).join('') +
      T(60, 72, 'V-shaped marks', 'middle'),
    skid: roll(40, 24, 16) + '<path d="M4 44h112" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M60 24h22m-5-4l5 4-5 4M60 52h12m-4-3l4 3-4 3" stroke="var(--orange)" stroke-width="2" fill="none"/>' +
      '<path d="M84 40l6 8M92 40l3 8" stroke="var(--ink)"/>' + T(86, 22, 'roll slides') + T(60, 74, 'skid marks', 'middle')
  };
  function picto(key, big) {
    return '<svg viewBox="0 0 120 80" class="' + (big ? 'big' : 'mini') + '" role="img" aria-label="' + esc(big ? 'Sketch of this cause' : '') + '"' +
      (big ? '' : ' aria-hidden="true"') + '><defs><pattern id="hatch-' + key + '" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="2" height="5" fill="var(--soft)"/></pattern></defs>' + (PICTOS[key] || '').replace(/url\(#hatch\)/g, 'url(#hatch-' + key + ')') +
      '</svg>';
  }

  // ------------------------------------------------------------------ along the strip
  function alongSvg(av, names) {
    var L = av.strip_length_m || 1, w = drawW(), sx = (w - 40) / L, H = 150;
    function X(m) { return 20 + m * sx; }
    var s = '<svg viewBox="0 0 ' + w + ' ' + H + '" role="group" aria-label="Marks along a length of strip: what you measured against the spacing of the best-fitting candidate">';
    s += '<rect class="strip" x="20" y="20" width="' + (w - 40) + '" height="44"/><rect class="strip" x="20" y="82" width="' + (w - 40) + '" height="44"/>';
    s += '<text x="20" y="14" font-size="13" font-weight="700">What you measured' + (isNum(av.observed_pitch_m) ? ': spacing ' + sig(av.observed_pitch_m * 1000, 3) + ' mm' +
      (isNum(av.observed_at_exit_speed_m_s) ? ' at ' + mpm(av.observed_at_exit_speed_m_s) : '') : ': no spacing entered') + '</text>';
    if (isNum(av.observed_pitch_m) && av.observed_pitch_m > 0) {
      for (var x = 0; x <= L + 1e-9 && x / av.observed_pitch_m < 400; x += av.observed_pitch_m) {
        s += '<line x1="' + X(x) + '" x2="' + X(x) + '" y1="22" y2="62" stroke="var(--ink)" stroke-width="2.5"/>';
      }
    }
    var nm = av.hypothesis_name || 'no candidate with a spacing';
    s += '<text x="20" y="77" font-size="13" font-weight="700">' + esc(nm) + (isNum(av.predicted_pitch_m) ? ': spacing ' + sig(av.predicted_pitch_m * 1000, 3) + ' mm (model)' : '') + '</text>';
    if (isNum(av.predicted_pitch_m) && av.predicted_pitch_m > 0) {
      for (var y = 0; y <= L + 1e-9 && y / av.predicted_pitch_m < 400; y += av.predicted_pitch_m) {
        s += '<line x1="' + X(y) + '" x2="' + X(y) + '" y1="84" y2="124" stroke="var(--orange)" stroke-width="2.5" stroke-dasharray="5 3"/>';
      }
    }
    var step = L <= 1 ? 0.1 : L <= 5 ? 0.5 : 1;
    for (var t = 0; t <= L + 1e-9; t += step) {
      s += '<line class="tick" x1="' + X(t) + '" x2="' + X(t) + '" y1="128" y2="134"/><text x="' + X(t) + '" y="146" font-size="12" text-anchor="middle" class="softtext">' + sig(t, 3) + ' m</text>';
    }
    return s + '</svg>';
  }

  // ------------------------------------------------------------------ thinner or thicker
  function shortLabel(l) { return String(l || '').split(' ')[0]; }
  function multiples(gv) {
    return '<div class="multiples">' + gv.quantities.map(function (qt) {
      var f = qt.unit === 'um' ? 1e6 : qt.unit === 'mpa' ? 1e-6 : 1;
      var ps = gv.passes, n = ps.length, w = 300, h = 170, l = 46, r = 12, t = 16, b = 46;
      var vals = ps.map(function (p) { var v = p.values[qt.key]; return isNum(v) && !p.not_credible ? v * f : null; });
      var ok = vals.filter(isNum);
      var lo = Math.min.apply(null, ok.concat([0])), hi = Math.max.apply(null, ok.concat([0]));
      if (hi === lo) { hi = lo + 1; }
      function X(i) { return l + (n === 1 ? (w - l - r) / 2 : i * (w - l - r) / (n - 1)); }
      function Y(v) { return t + (hi - v) / (hi - lo) * (h - t - b); }
      var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(qt.label + ' for each pass, thickest on the left, thinnest on the right') + '">';
      ps.forEach(function (p, i) {
        if (p.not_credible || p.no_bite || p.outside_model_range) {
          s += '<rect x="' + (X(i) - 14) + '" y="' + t + '" width="28" height="' + (h - t - b) + '" fill="url(#mh)" opacity=".7"/>' +
            '<text x="' + X(i) + '" y="' + (t + 12) + '" font-size="9" text-anchor="middle">' + (p.not_credible ? 'not credible' : p.outside_model_range ? 'outside range' : 'no result') + '</text>';
        }
      });
      s += '<defs><pattern id="mh" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="6" fill="var(--soft)"/></pattern></defs>';
      s += '<line class="tick" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
      s += '<text x="' + (l - 4) + '" y="' + (Y(hi) + 4) + '" font-size="10" text-anchor="end" class="softtext">' + sig(hi, 3) + '</text>';
      s += '<text x="' + (l - 4) + '" y="' + (Y(lo) + 4) + '" font-size="10" text-anchor="end" class="softtext">' + sig(lo, 3) + '</text>';
      var pts = [];
      vals.forEach(function (v, i) { if (isNum(v)) { pts.push(X(i) + ',' + Y(v)); } });
      if (pts.length > 1) { s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="var(--blue)" stroke-width="2"/>'; }
      vals.forEach(function (v, i) {
        if (isNum(v)) {
          var words = ps[i].label + ': ' + sig(v, 3) + ' ' + qt.unit_label + ' (' + ps[i].credibility_words + ')';
          s += '<g class="mark" tabindex="0" data-tip="' + esc(words) + '" aria-label="' + esc(words) + '"><circle cx="' + X(i) + '" cy="' + Y(v) + '" r="4.5" fill="var(--blue)"/></g>';
        }
        s += '<text x="' + X(i) + '" y="' + (h - b + 16) + '" font-size="10" text-anchor="middle">' + esc(shortLabel(ps[i].label)) + '</text>';
        s += '<text x="' + X(i) + '" y="' + (h - b + 29) + '" font-size="9" text-anchor="middle" class="softtext">' + esc(gauge(ps[i].exit_thickness_m)) + '</text>';
      });
      s += '<text x="' + (w - r) + '" y="' + (h - 4) + '" font-size="9" text-anchor="end" class="softtext">thinner →</text>';
      return '<figure><figcaption>' + esc(qt.label) + ' (' + esc(qt.unit_label) + ')</figcaption>' + s + '</svg><p class="small soft">' + esc(qt.reading) + '</p></figure>';
    }).join('') + '</div>';
  }

  // ------------------------------------------------------------------ temperature
  function tempSvg(tv) {
    var rows = tv.rows, n = rows.length, w = 640, h = 220, l = 46, r = 16, t = 20, b = 50;
    var lim = tv.battery_limits_apply && tv.coil_limits_c ? tv.coil_limits_c.leaving_final_pass : null;
    var hi = Math.max.apply(null, rows.map(function (x) { return x.value_c; }).concat([lim || 0, 100]));
    function Y(v) { return t + (1 - v / hi) * (h - t - b); }
    var bw = Math.min(60, (w - l - r) / n * 0.6);
    var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Modelled strip exit temperature per pass' + (lim ? ' against the published coil limit of ' + lim + ' °C' : '') + '">';
    s += '<line class="tick" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
    rows.forEach(function (x, i) {
      var cx = l + (i + 0.5) * (w - l - r) / n;
      s += '<g class="mark" tabindex="0" data-tip="' + esc(x.label + ': ' + degc(x.value_c)) + '" aria-label="' + esc(x.label + ': ' + degc(x.value_c)) + '">' +
        '<rect x="' + (cx - bw / 2) + '" y="' + Y(x.value_c) + '" width="' + bw + '" height="' + (Y(0) - Y(x.value_c)) + '" fill="' + (x.is_final_pass ? 'var(--ink)' : 'var(--soft)') + '"/></g>';
      s += '<text x="' + cx + '" y="' + (Y(x.value_c) - 4) + '" font-size="11" text-anchor="middle">' + degc(x.value_c) + '</text>';
      s += '<text x="' + cx + '" y="' + (h - b + 16) + '" font-size="10" text-anchor="middle">' + esc(shortLabel(x.label)) + (x.is_final_pass ? ' (final)' : '') + '</text>';
    });
    if (lim) {
      s += '<line x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(lim) + '" y2="' + Y(lim) + '" stroke="var(--red)" stroke-width="2" stroke-dasharray="7 4"/>' +
        '<text x="' + (w - r) + '" y="' + (Y(lim) - 5) + '" font-size="11" text-anchor="end">published coil limit leaving the final pass: ' + lim + ' °C</text>';
    }
    return s + '</svg>';
  }
