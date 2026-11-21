  // ------------------------------------------------------------------ the strip drawing
  // One drawing for input (place bands, mark nozzles) and for the result (what fits where).
  var W = 1000, ML = 14, MR = 14;
  // drawings are laid out at about their on-screen width, so 12 px text stays 12 px
  function drawW() { return window.innerWidth < 860 ? Math.max(300, window.innerWidth - 70) :  Math.round(Math.max(320, Math.min(1120, (app.clientWidth || window.innerWidth) - (window.innerWidth < 860 ? 70 : 120)))); }
  var KIND_STYLE = {   // dash pattern + letter: never colour alone
    steady_stripes: {dash: '', letter: 'S', colour: 'var(--orange)'},
    blocked_or_low_level_nozzles: {dash: '6 3', letter: 'N', colour: 'var(--blue)'},
    event_nozzles: {dash: '2 3', letter: 'V', colour: 'var(--blue)'},
    event_stripe_peaks: {dash: '8 3 2 3', letter: 'E', colour: 'var(--orange)'},
    incoming_ridges: {dash: '10 4', letter: 'R', colour: 'var(--soft)'},
    two_tone: {dash: '1 2', letter: 'T', colour: 'var(--soft)'}
  };

  function drawStrip(o) {
    W = o.compact ? Math.max(320, Math.round(drawW() / 2 - 30)) : drawW();
    var barrel = o.barrel || (o.edge * 2 + o.width) || 1.5;
    var sx = (W - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var res = o.result, hasTh = res && res.thermal_profile;
    var yN = 38, yTop = hasTh ? 146 : 92, yBot = yTop + 84, yRul = yBot + 8, H = yRul + 44;
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(o.label) + '"' +
      (o.id ? ' id="' + o.id + '"' : '') + ' data-barrel="' + barrel + '" data-edge="' + o.edge +
      '" data-width="' + o.width + '" data-ml="' + ML + '" data-sx="' + sx + '">';
    s += '<defs><pattern id="half" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="var(--card)"/>' +
      '<path d="M0 4L4 0" stroke="var(--ink)" stroke-width="1.4"/></pattern>' +
      '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="2" height="6" fill="var(--soft)"/></pattern></defs>';
    // roll barrel and spray header
    s += '<rect class="roll" x="' + X(0) + '" y="' + (yN - 14) + '" width="' + (barrel * sx) + '" height="' + (yBot - yN + 18) + '"/>';
    s += '<text x="' + X(0) + '" y="13" font-size="12" class="softtext">Roll barrel ' + mmInt(barrel) + ', coolant nozzles numbered from nozzle 1</text>';
    var noz = o.nozzles || [];
    var pitch = noz.length > 1 ? (noz[1].pos - noz[0].pos) * sx : 30;
    var r = Math.max(4, Math.min(10, pitch * 0.32));
    // the spray valves of the flatness control (the engine's grouping), as brackets
    (o.valves || []).forEach(function (v) {
      var xa = X(v.start_m) - r, xb = X(v.end_m) + r, yv = yN - r - 5;
      s += '<path class="valve-bracket" d="M' + xa + ' ' + (yv + 3) + 'L' + xa + ' ' + yv + 'L' + xb + ' ' + yv + 'L' + xb + ' ' + (yv + 3) + '"/>';
    });
    noz.forEach(function (n) {
      var st = n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      if (n.level > 0) {
        s += '<path class="spray' + (st === 'weak' ? ' weak' : '') + '" d="M' + X(n.pos) + ' ' + (yN + r) + 'L' +
          (X(n.pos) - pitch * 0.62) + ' ' + yTop + 'L' + (X(n.pos) + pitch * 0.62) + ' ' + yTop + 'Z"/>';
      }
    });
    noz.forEach(function (n) {
      var st = n.level === null || n.level === undefined ? 'healthy' : n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      var words = 'Nozzle ' + n.number + ': ' + (n.unknown ? 'not checked (the model uses full flow)' : st === 'healthy' ? 'healthy' : st === 'weak' ? 'weak (flow ' + sig(n.level, 2) + ')' : 'blocked') +
        ', at ' + mmInt(n.pos - o.edge) + ' from the strip edge' + (n.events ? '; ' + n.events : '');
      var focus = o.interactive === 'nozzles' ? ' tabindex="0" role="button" data-noz="' + n.index + '"' : ' tabindex="0" class="mark"';
      s += '<g class="noz ' + st + (o.interactive === 'nozzles' ? '' : ' mark') + '"' + focus + ' aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
        '<circle cx="' + X(n.pos) + '" cy="' + yN + '" r="' + r + '"/>' +
        (st === 'blocked' ? '<path d="M' + (X(n.pos) - r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) + r * .6) + ' ' + (yN + r * .6) +
          'M' + (X(n.pos) + r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) - r * .6) + ' ' + (yN + r * .6) + '" stroke="var(--card)" stroke-width="2"/>' : '') +
        (n.events ? '<circle class="valve" cx="' + X(n.pos) + '" cy="' + yN + '" r="' + (r + 3) + '"/>' : '') +
        '</g>';
      if (noz.length <= 40 && (n.number === 1 || n.number % 5 === 0)) {
        s += '<text x="' + X(n.pos) + '" y="' + (yN + r + 15) + '" font-size="13" font-weight="600" text-anchor="middle">' + n.number + '</text>';
      }
    });
    // shapemeter zones (from the server's model): dashed boundaries just above the strip
    if (o.zones && o.zones.length) {
      var yZ = yTop - 7;
      s += '<g class="zones" aria-hidden="true"><line x1="' + X(o.zones[0].start_m) + '" x2="' + X(o.zones[o.zones.length - 1].end_m) + '" y1="' + yZ + '" y2="' + yZ + '"/>';
      o.zones.forEach(function (z, k) {
        s += '<line x1="' + X(z.start_m) + '" x2="' + X(z.start_m) + '" y1="' + (yZ - 6) + '" y2="' + (yTop + 6) + '"/>';
        if (k === o.zones.length - 1) { s += '<line x1="' + X(z.end_m) + '" x2="' + X(z.end_m) + '" y1="' + (yZ - 6) + '" y2="' + (yTop + 6) + '"/>'; }
      });
      s += '</g>';
    }
    // thermal profile of the roll (result only)
    if (hasTh) {
      var z = res.thermal_profile.z_m, d = res.thermal_profile.local_deviation_m;
      var mx = 0;
      d.forEach(function (v) { mx = Math.max(mx, Math.abs(v)); });
      var y0 = yTop - 14, k = mx > 0 ? 44 / mx : 0, pts = [];
      z.forEach(function (zz, i) { pts.push(X(zz).toFixed(1) + ',' + (y0 - d[i] * k).toFixed(1)); });
      s += '<line x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + y0 + '" y2="' + y0 + '" class="tick" stroke-dasharray="2 3"/>';
      s += '<polyline class="thermal" points="' + pts.join(' ') + '"/>';
      var ip = 0;
      d.forEach(function (v, i) { if (v > d[ip]) { ip = i; } });
      var tip = 'Roll grows most here (hot stripe): ' + um(d[ip]) + ' at ' + mmInt(z[ip] - o.edge) + ' from the strip edge';
      s += '<g class="mark" tabindex="0" aria-label="' + esc(tip) + '" data-tip="' + esc(tip) + '"><circle cx="' + X(z[ip]) + '" cy="' + (y0 - d[ip] * k) + '" r="5" fill="var(--orange)"/></g>';
      s += '<text x="' + (X(barrel) - 4) + '" y="' + (y0 - 30) + '" font-size="12" text-anchor="end">roll growth (line)</text>';
    }
    // strip
    s += '<rect class="strip" data-strip="1" x="' + X(o.edge) + '" y="' + yTop + '" width="' + (o.width * sx) + '" height="' + (yBot - yTop) + '"/>';
    // predicted positions (result)
    if (res && res.predicted) {
      var tol = res.tolerance_m || 0.01, placed = [];
      res.predicted.forEach(function (p) {
        var st = KIND_STYLE[p.kind] || {dash: '3 3', letter: '?', colour: 'var(--soft)'};
        p.positions_m.forEach(function (x) {
          var words = p.label + ' at ' + mmInt(x - o.edge) + ' from the strip edge (marked ' + st.letter + ')';
          // letters side by side when marks are close, so none hides another
          var lx = X(x), row = 0;
          while (row < 3 && placed.some(function (q) { return q.r === row && Math.abs(q.x - lx) < 11; })) { row += 1; }
          placed.push({x: lx, r: row});
          s += '<g class="mark" tabindex="0" aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
            '<rect class="pred" x="' + (X(x - tol)) + '" y="' + (yTop + 4) + '" width="' + Math.max(4, 2 * tol * sx) + '" height="' + (yBot - yTop - 8) +
            '" stroke="' + st.colour + '" stroke-dasharray="' + st.dash + '"/>' +
            '<text x="' + lx + '" y="' + (yTop - 4 - 13 * row) + '" font-size="12" font-weight="700" text-anchor="middle">' + st.letter + '</text></g>';
        });
      });
    }
    // observed bands
    var bands = o.bands || [];
    bands.forEach(function (b, i) {
      var w = Math.max(5, (b.w || 0.008) * sx);
      var words = 'Band ' + (i + 1) + ' (what you saw) at ' + mmInt(b.x - o.edge) + ' from the strip edge';
      var inter = o.interactive === 'bands';
      s += '<rect class="band' + (inter ? '' : ' mark') + '" tabindex="0"' + (inter ? ' role="slider" aria-valuemin="0" aria-valuemax="' +
        Math.round(o.width * 1000) + '" aria-valuenow="' + Math.round((b.x - o.edge) * 1000) + '" data-band="' + i + '"' : '') +
        ' aria-label="' + esc(words) + '" data-tip="' + esc(words) + '" x="' + (X(b.x) - w / 2) + '" y="' + (yTop + 2) +
        '" width="' + w + '" height="' + (yBot - yTop - 4) + '"/>';
      s += '<text x="' + X(b.x) + '" y="' + (yBot - 8) + '" font-size="12" font-weight="700" text-anchor="middle" fill="var(--card)" style="fill:var(--card);pointer-events:none">' + (i + 1) + '</text>';
    });
    // matches (result)
    if (res && res.matches) {
      var drawn = {};
      res.matches.forEach(function (m) {
        m.links.forEach(function (l) {
          if (!l.matched || l.predicted_m === null) { return; }
          var key = l.observed_m.toFixed(4);
          if (drawn[key]) { return; }
          drawn[key] = 1;
          var words = 'Your band at ' + mmInt(l.observed_m - o.edge) + ' lies within ' + mmSmall(res.tolerance_m) +
            ' of: ' + m.label.toLowerCase() + ' at ' + mmInt(l.predicted_m - o.edge);
          s += '<g class="mark" tabindex="0" aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
            '<rect class="tol" x="' + X(l.observed_m - res.tolerance_m) + '" y="' + (yBot + 1) + '" width="' + (2 * res.tolerance_m * sx) + '" height="7"/>' +
            '<line class="link" x1="' + X(l.observed_m) + '" x2="' + X(l.predicted_m) + '" y1="' + (yBot + 4) + '" y2="' + (yTop + 6) + '"/></g>';
        });
      });
    }
    // ruler in mm from the strip edge on the header-start side
    var widthMm = o.width * 1000, pxPerMm = o.width * sx / widthMm;
    var step = [50, 100, 200, 250, 500].filter(function (st) { return st * pxPerMm >= 28; })[0] || 500;
    s += '<line class="tick" x1="' + X(o.edge) + '" x2="' + X(o.edge + o.width) + '" y1="' + yRul + '" y2="' + yRul + '"/>';
    for (var t = 0; t <= widthMm + 0.1; t += step) {
      var xx = X(o.edge + t / 1000);
      s += '<line class="tick" x1="' + xx + '" x2="' + xx + '" y1="' + yRul + '" y2="' + (yRul + 6) + '"/>';
      if (t % (step * 2) === 0 || step * pxPerMm >= 55) {
        s += '<text x="' + xx + '" y="' + (yRul + 19) + '" font-size="12" text-anchor="middle" class="softtext">' + t + '</text>';
      }
    }
    s += '<text x="' + X(o.edge) + '" y="' + (yRul + 36) + '" font-size="12" class="softtext">' + (W < 600 ? 'mm from the strip edge nearest nozzle 1' : 'mm across the strip, from the strip edge nearest nozzle 1') + '</text>';
    return s + '</svg>';
  }

  function legend(items) {
    return '<ul class="legend">' + items.map(function (it) {
      return '<li><svg viewBox="0 0 30 16" aria-hidden="true">' + it.icon + '</svg>' + esc(it.text) + '</li>';
    }).join('') + '</ul>';
  }
  var LEG_BAND = {icon: '<rect x="11" y="1" width="8" height="14" fill="var(--ink)"/>', text: 'Band you saw (solid)'};
  function legKind(k, label) {
    var st = KIND_STYLE[k] || {dash: '3 3', letter: '?', colour: 'var(--soft)'};
    return {icon: '<rect x="2" y="2" width="26" height="12" fill="none" stroke="' + st.colour + '" stroke-width="2" stroke-dasharray="' + st.dash + '"/>' +
      '<text x="15" y="12" font-size="10" font-weight="700" text-anchor="middle">' + st.letter + '</text>', text: st.letter + ': ' + label};
  }

  // nozzles and bands exactly as the server's drawing model has them (effective levels)
  function nozzlesOf(m) {
    var h = m.header;
    if (!h) { return []; }
    return h.nozzles.map(function (n) {
      var ev = n.valve_events.map(function (k) { var e = m.valve_events[k]; return 'valve event: flow ' + sig(e.level, 2) + ' for ' + sig(e.duration_s, 3) + ' s from ' + sig(e.start_s, 3) + ' s'; });
      return {pos: n.position_m, index: n.index, number: n.number, level: n.level, unknown: !h.levels_known, events: ev.join('; ')};
    });
  }
  function bandsOf(m, withWidth) {
    var bw = m.bands.band_width_m;
    return m.bands.positions_m.map(function (x) { return {x: x, w: withWidth && isNum(bw) ? bw : null}; });
  }
  function stripArgs(m) { return {barrel: m.strip.barrel_length_m, edge: m.strip.edge_m, width: m.strip.width_m}; }
  function zonesOf(m) { return m.shapemeter ? m.shapemeter.zones : null; }
  // the shapemeter zones in words, beside the drawing (the drawing's zone lines are not focusable)
  function zonesNote(m) {
    var sm = m.shapemeter;
    if (!sm) { return ''; }
    var edge = m.strip.edge_m, z = sm.zones;
    var counts = {}; z.forEach(function (x) { var n = x.nozzle_numbers.length; counts[n] = (counts[n] || 0) + 1; });
    var per = Object.keys(counts).sort().map(function (n) { return counts[n] + ' zone' + (counts[n] > 1 ? 's' : '') + ' with ' + n + ' nozzle' + (n === '1' ? '' : 's'); }).join(', ');
    return '<p class="small">Shapemeter: ' + sm.zone_count + ' zones (dashed lines just above the strip) from ' + mmInt(z[0].start_m - edge) + ' to ' + mmInt(z[z.length - 1].end_m - edge) +
      ' from the strip edge; ' + per + '.' + (sm.uncovered_strip_width_m > 0.0005 ? ' The zones do not cover ' + mmInt(sm.uncovered_strip_width_m) + ' of the strip.' : '') + '</p>' +
      '<details class="more"><summary>The zones as a list</summary><ul class="small">' + z.map(function (x) {
        return '<li>Zone ' + (x.index + 1) + ': ' + mmInt(x.start_m - edge) + ' to ' + mmInt(x.end_m - edge) + ' from the strip edge' + (x.nozzle_numbers.length ? ', nozzle ' + x.nozzle_numbers.join(', ') : ', no nozzle') + '</li>';
      }).join('') + '</ul></details>';
  }

  function bandsInput(q, ctx) { return '<div data-view="bands">' + VIEWS.bands() + '</div>'; }
  function bandsView() {
    var m = model();
    var pos = m.bands.from_edge_mm;
    var a = stripArgs(m);
    var svg = drawStrip({id: 'strip-input', label: 'Top view of the strip. Click or tap on the strip to add a band; drag a band to move it; with the keyboard use the arrow keys on a band, Delete removes it.',
      barrel: a.barrel, edge: a.edge, width: a.width,
      nozzles: nozzlesOf(m), bands: bandsOf(m, true), interactive: 'bands', zones: zonesOf(m)});
    var list = '<ol class="poslist" aria-label="Band positions">' + pos.map(function (mm, i) {
      return '<li><label for="bp-' + i + '">Band ' + (i + 1) + '</label><input type="number" step="1" id="bp-' + i + '" data-bandpos="' + i +
        '" value="' + esc(mm) + '"><span class="unit">mm</span><button type="button" class="btn" data-band-del="' + i +
        '" aria-label="Delete band ' + (i + 1) + '">Delete</button></li>';
    }).join('') + '</ol>';
    return staleNote() + '<div class="drawing' + (S.modelStale ? ' stale' : '') + '"><div>' + svg + legend([LEG_BAND, {icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)"/>', text: 'Coolant nozzle (for orientation)'}]) +
      '</div><div class="side">' + (pos.length ? list : '<p class="empty">No bands placed yet. Click on the strip, or add one here.</p>') +
      '<div class="numrow"><label class="sr" for="bp-new">New band position in mm</label><input type="number" step="1" id="bp-new" placeholder="mm from edge">' +
      '<button type="button" class="btn" data-band-add="1">Add band</button></div>' +
      '<p class="small soft">Strip ' + mmInt(m.strip.width_m) + ' wide. ' + (pos.length ? '<button type="button" class="btn link" data-band-clear="1">Clear all ("Don\'t know")</button>' : '') + '</p></div></div>';
  }

  function nozzleInput(q, ctx) { return '<div data-view="nozzles">' + VIEWS.nozzles() + '</div>'; }
  function nozzlesView() {
    var m = model(), h = m.header;
    if (!h) {
      return '<p class="empty">This starting point has no spray header model, so nozzles cannot be marked here.</p>';
    }
    var a = stripArgs(m);
    var svg = drawStrip({id: 'strip-nozzles', label: 'Spray header over the strip. Click a nozzle to cycle healthy, weak and blocked; with the keyboard press Enter or Space on a nozzle.',
      barrel: a.barrel, edge: a.edge, width: a.width,
      nozzles: nozzlesOf(m), bands: bandsOf(m, false), interactive: 'nozzles', zones: zonesOf(m),
      valves: m.control_zones ? m.control_zones.valves : null});
    var known = h.levels_known, lst = '';
    if (known) {
      lst = '<details class="more"' + (S.nozListOpen ? ' open' : '') + ' data-nozlist="1"><summary>Nozzle list (flow level of each nozzle, 1 = full, 0 = blocked)</summary><div class="nozlist">' +
        h.nozzles.map(function (n) {
          return '<label for="nz-' + n.index + '">Nozzle ' + n.number + '<input type="number" min="0" max="1" step="0.05" id="nz-' + n.index + '" data-nozlevel="' + n.index + '" value="' + esc(n.level) + '"></label>';
        }).join('') + '</div></details>';
    }
    var ev = m.valve_events.length ? '<p class="small">Valve events (dotted ring on the drawing): ' + esc(m.valve_events.map(function (e) {
      return 'nozzle' + (e.numbers.length > 1 ? 's ' : ' ') + e.numbers.join(', ') + ' at flow ' + sig(e.level, 2) + ' for ' + sig(e.duration_s, 3) + ' s';
    }).join('; ')) + '.</p>' : '';
    return staleNote() + '<div class="' + (S.modelStale ? 'stale' : '') + '">' + svg + legend([{icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Healthy'},
      {icon: '<circle cx="15" cy="8" r="6" fill="url(#half)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Weak (flow ' + M.weak_nozzle_level + ')'},
      {icon: '<circle cx="15" cy="8" r="6" fill="var(--ink)" stroke="var(--ink)"/>', text: 'Blocked'}, LEG_BAND].concat(m.valve_events.length ? [{icon: '<circle cx="15" cy="8" r="6" fill="none" stroke="var(--blue)" stroke-width="1.5" stroke-dasharray="2 2"/>', text: 'Valve event'}] : [])) +
      '<p class="small" aria-live="polite" data-nozstatus="1">' + (known ? (h.weak + ' weak, ' + h.blocked + ' blocked of ' + h.nozzles.length +
      ' nozzles. <button type="button" class="btn link" data-noz-reset="1">Set back to "Don\'t know"</button>') :
      'Nozzle state: "Don\'t know" (nobody has checked; the model uses full flow). Click a nozzle to mark it; the others then count as healthy.') + '</p>' +
      (known ? '' : '<button type="button" class="btn" data-noz-init="1">All nozzles checked and healthy</button>') + ev + zonesNote(m) + lst + '</div>';
  }

  // "Blocked nozzles (by number)": a view of the level-0 nozzles of the drawing that edits them
  function blockedView() {
    var m = model(), h = m.header;
    if (!h) { return '<p class="empty">This starting point has no spray header model.</p>'; }
    var nums = h.levels_known ? h.nozzles.filter(function (n) { return n.level <= 0; }).map(function (n) { return n.number; }) : [];
    return '<div class="numrow"><input type="text" class="wide" id="f-in-blocked_nozzles" data-nozedit="blocked" value="' + esc(nums.join(', ')) +
      '" placeholder="' + (h.levels_known ? 'none' : "Don't know") + '" aria-describedby="f-h-blocked_nozzles"><span class="small soft">separate with commas</span></div>';
  }
  // the coverage check's blocked nozzles: the drawing's marks when it is the same header
  function coverageView() {
    var m = model(), c = m.coverage;
    if (!c) { return '<p class="empty">This starting point has no simple coverage check.</p>'; }
    if (c.same_header) {
      return '<p class="small">Same spray header as the drawing above, so the coverage check uses its marks (weak and blocked count as not spraying). Now: ' +
        (c.blocked_numbers.length ? 'nozzle' + (c.blocked_numbers.length > 1 ? 's ' : ' ') + esc(c.blocked_numbers.join(', ')) : 'none') + '.</p>';
    }
    return null;
  }
  // why the coverage check has its own numbers when its header is not the one drawn
  function coverageNote() {
    var m = model(), c = m.coverage;
    if (!c || c.same_header) { return ''; }
    return '<p class="small">' + (m.header ? 'The simple coverage check in this case uses its own header' : 'This starting point has no spray header model; the simple coverage check uses a header') +
      ' of ' + c.count + ' nozzles (barrel ' + mmInt(c.barrel_length_m) + ', pitch ' + mmSmall(c.pitch_m) + ')' + (m.header ? ', not the header drawn above, so its blocked nozzles are entered here.' : '. Its blocked nozzles are entered here.') +
      ' Now: ' + (c.blocked_numbers.length ? esc(c.blocked_numbers.join(', ')) : 'none') + '.</p>';
  }
  function routeView() {
    var r = model().route;
    if (!r.rows.length) { return '<p class="small soft">No other passes entered.</p>'; }
    var hits = r.rows.filter(function (x) { return x.is_pass; }).map(function (x) { return '"' + (x.label || 'unnamed') + '"'; });
    return '<p class="small" role="status">' + (hits.length ? 'The pass where the bands show is the same as route pass ' + esc(hits.join(', ')) + '.' :
      'The pass where the bands show is not one of the route passes: the tool treats it as one more pass.') +
      (r.computed_replaces ? ' The run replaces flow stress or friction with computed values and compares the passes again.' : '') + '</p>';
  }
  var VIEWS = {bands: bandsView, nozzles: nozzlesView, blocked: blockedView, route: routeView,
    coverage: function () { return coverageView() || ''; }, covnote: coverageNote};

  // ------------------------------------------------------------------ tooltips
  var tipEl = null;
  function showTip(target) {
    var t = target.getAttribute('data-tip');
    if (!t) { return; }
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'tip'; tipEl.setAttribute('role', 'tooltip'); document.body.appendChild(tipEl); }
    tipEl.textContent = t;
    var r = target.getBoundingClientRect();
    tipEl.style.display = 'block';
    var x = Math.min(window.innerWidth - tipEl.offsetWidth - 8, Math.max(8, r.left + r.width / 2 - tipEl.offsetWidth / 2));
    var y = r.top - tipEl.offsetHeight - 8;
    if (y < 8) { y = r.bottom + 8; }
    tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
  }
  function hideTip() { if (tipEl) { tipEl.style.display = 'none'; } }
