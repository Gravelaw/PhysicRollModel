  // ------------------------------------------------------------------ running view
  function renderRunning(st) {
    var run = st.run;
    var prof = M.profiles[run.profile] || {label: run.profile, left_out: []};
    var queued = run.status === 'queued';
    var el_ = run.elapsed_s;
    app.innerHTML = '<div class="wrap"><section class="card running" aria-live="polite"><div class="runhead"><div class="spinner" aria-hidden="true"></div><div>' +
      '<h2>' + (queued ? 'Waiting to start' : 'Running the screening') + '</h2><p class="soft">' + esc(prof.label) + ' run' +
      (run.changes && run.changes.length ? ' of a what-if (' + esc(run.changes.join(', ')) + ')' : '') + '.' +
      (queued && st.queue_position ? ' Place in the queue: ' + st.queue_position + '.' : '') + '</p></div></div>' +
      '<p class="elapsed num" id="elapsed">' + (isNum(el_) ? Math.round(el_) + ' s' : '0 s') + '</p>' +
      '<p>The tool works through these steps (one run at a time on this computer):</p><ol class="stages">' +
      M.stages.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ol>' +
      (prof.left_out && prof.left_out.length ? '<p class="small soft">This quick run leaves out: ' + esc(prof.left_out.join('; ')) + '.</p>' : '') +
      '<p class="small soft">A quick run takes about 5 to 20 seconds on the demo cases, a detailed run up to a few minutes.</p>' +
      (queued ? '<button type="button" class="btn" data-cancel="' + run.id + '">Cancel this run</button>' : '') +
      ' <button type="button" class="btn" data-back-input="1">Back to the answers</button></section></div>';
  }

  function renderFailed(st) {
    var run = st.run, e = run.error || {text: 'The run did not finish.'};
    var q = e.question && Q[e.question];
    var title = run.status === 'cancelled' ? 'This run was cancelled' : run.status === 'interrupted' ? 'This run was interrupted' : 'The screening could not be run';
    var calm = run.status === 'cancelled' || run.status === 'interrupted';
    app.innerHTML = '<div class="wrap"><section class="card ' + (calm ? 'banner' : 'errorbox') + '" role="' + (calm ? 'status' : 'alert') + '"><h2>' + title + '</h2><p>' + esc(e.text || '') + '</p>' +
      (q ? '<p>The answer to look at: <strong>' + esc(q.wording) + '</strong>.</p><button type="button" class="btn primary" data-goto="' + q.id + '">Go to this question</button> ' : '') +
      '<button type="button" class="btn" data-back-input="1">Back to the answers</button> ' +
      '<button type="button" class="btn" data-rerun="' + run.id + '" data-profile="' + run.profile + '">Run the same inputs again</button></section></div>';
  }

  // ------------------------------------------------------------------ result view
  var SCLASS = {CONSISTENT_LEADING: 's-best', CONSISTENT: 's-fits', WEAKENED: 's-weak', NOT_ASSESSABLE: 's-none', CONTRADICTED: 's-no'};
  var SICON = {CONSISTENT_LEADING: '★', CONSISTENT: '✓', WEAKENED: '▽', NOT_ASSESSABLE: '?', CONTRADICTED: '✕'};

  function standWords(c) {
    return '<span class="stand ' + SCLASS[c.standing] + '"><span aria-hidden="true">' + SICON[c.standing] + '</span>' + esc(c.standing_words) + '</span>';
  }

  function barsHtml(sum, ids, opts) {
    opts = opts || {};
    var by = {}, old = {};
    sum.causes.forEach(function (c) { by[c.id] = c; });
    if (opts.old) { opts.old.causes.forEach(function (c) { old[c.id] = c; }); }
    var scores = [0, 1];
    ids.forEach(function (id) { if (by[id]) { scores.push(by[id].score); } if (old[id]) { scores.push(old[id].score); } });
    var lo = Math.min.apply(null, scores), hi = Math.max.apply(null, scores);
    var span = hi - lo, z = (0 - lo) / span * 100;
    function pos(sc) { var a = (Math.min(sc, 0) - lo) / span * 100, b = (Math.max(sc, 0) - lo) / span * 100; return {left: a, width: Math.max(b - a, 0.6)}; }
    var h = '<div class="axis" aria-hidden="true"><span></span><span></span><span class="ax"><span>' + (lo < 0 ? '← does not fit (' + lo + ')' : '0') + '</span><span>fits (' + hi + ') →</span></span><span>score</span></div>';
    h += '<div class="bars" role="list">';
    ids.forEach(function (id) {
      var c = by[id];
      if (!c) { return; }
      var start = opts.old && old[id] ? pos(old[id].score) : pos(c.score);
      var end = pos(c.score);
      var oldMark = opts.old && old[id] && old[id].score !== c.score ? '<span class="old" style="left:' + pos(old[id].score).left + '%;width:' + pos(old[id].score).width + '%" title="before"></span>' : '';
      var label = c.name + ': ' + c.standing_words + ', score ' + c.score + (opts.old && old[id] && old[id].score !== c.score ? ' (before ' + old[id].score + ')' : '');
      var prHide = (c.standing === 'CONTRADICTED' || c.standing === 'NOT_ASSESSABLE') ? ' class="pr-hide"' : '';
      h += '<div role="listitem"' + prHide + '><button type="button" class="bar' + (opts.old && old[id] && (old[id].score !== c.score || old[id].standing !== c.standing) ? ' changed' : '') + '" data-cause="' + id + '" aria-expanded="' + (S.openCause === id && !opts.compact ? 'true' : 'false') + '" aria-label="' + esc(label) + '"' + (opts.compact ? ' tabindex="-1"' : '') + '>' +
        '<span class="pic">' + picto(c.pictogram) + '</span><span class="nm"><b>' + esc(c.name) + '</b>' + standWords(c) + '</span>' +
        '<span class="track"><span class="zero" style="left:' + z + '%"></span>' + oldMark +
        '<span class="fill ' + SCLASS[c.standing] + '" data-left="' + end.left + '" data-width="' + end.width + '" style="left:' + start.left + '%;width:' + start.width + '%"></span></span>' +
        '<span class="score num">' + c.score + (opts.old && old[id] && old[id].score !== c.score ? '<br><span class="small soft">was ' + old[id].score + '</span>' : '') + '</span></button>';
      if (S.openCause === id && !opts.compact) { h += causeDetail(c); }
      h += '</div>';
    });
    return h + '</div>';
  }

  function evidList(items, empty) {
    if (!items.length) { return '<p class="empty">' + esc(empty) + '</p>'; }
    return '<ul class="evid">' + items.map(function (e) {
      var good = e.verdict === 'SUPPORTS';
      return '<li><span class="vw ' + (good ? 'ok' : 'no') + '"><span aria-hidden="true">' + (good ? '✓' : '✕') + '</span> ' + esc(e.verdict_words) +
        '</span> <span class="w">(' + esc(e.weight_words) + ')</span>: <span class="lab">' + esc(e.label) + '</span>' +
        '<ul class="evsub small">' + (e.seen_words ? '<li>' + esc(e.seen_words) + '</li>' : '') + (e.model_words ? '<li>' + esc(e.model_words) + '</li>' : '') +
        '<li>' + esc(e.expects_words) + '</li></ul></li>';
    }).join('') + '</ul>';
  }

  function causeDetail(c) {
    var nl = c.not_looked_at.length ? '<ul class="evid">' + c.not_looked_at.map(function (x) {
      var qs = x.questions.filter(function (q) { return Q[q]; });
      return '<li>' + esc(x.label.charAt(0).toUpperCase() + x.label.slice(1)) + (qs.length ? ' <button type="button" class="btn link" data-answer="' + esc(qs.join(',')) + '">Answer this</button>' : '') +
        (S.openChecks['nl-' + c.id + '-' + qs.join(',')] ? inlineQs(qs) : '') + '</li>';
    }).join('') + '</ul>' : '<p class="empty">Everything this cause looks at has an answer.</p>';
    return '<div class="detail" id="detail-' + c.id + '"><div class="top"><div>' + picto(c.pictogram, true) + '</div><div><h3>' + esc(c.name) + '</h3>' +
      '<p>' + esc(c.description) + '</p><p>' + standWords(c) + ' <span class="num small">score ' + c.score + ', place ' + c.rank + ' of 20</span></p></div></div>' +
      '<div class="cols"><div><h4>What fits</h4>' + evidList(c.fits_because, 'Nothing entered speaks for it yet.') + '</div>' +
      '<div><h4>What speaks against it</h4>' + evidList(c.speaks_against, 'Nothing entered speaks against it.') + '</div></div>' +
      '<h4>Not looked at yet</h4>' + nl + '<h4>How to check on the floor</h4><p>' + esc(c.how_to_check) + '</p>' +
      (c.candidate_pitch ? '<h4>A candidate spacing (not evidence)</h4><p>' + esc(c.candidate_pitch.text) + '</p><ul class="small">' + c.candidate_pitch.rows.map(function (r) { return '<li>' + esc(r.text) + '</li>'; }).join('') + '</ul>' : '') + '</div>';
  }

  // inline answers for the check-and-update loop (edits pending changes of the shown run)
  var PEND = {get: function (id) {
    if (Object.prototype.hasOwnProperty.call(S.pending, id)) { return S.pending[id]; }
    var v = S.runAnswers ? S.runAnswers.values[id] : null; return v === undefined ? null : v;
  }, prefix: 'p', origin: false};
  function inlineQs(ids) {
    return '<div class="inline-q">' + ids.map(function (id) {
      return Q[id].kind === 'positions' || Q[id].kind === 'nozzles' ? '<p class="small">Change this one in the answers (it needs the drawing): <button type="button" class="btn link" data-goto="' + id + '">open the question</button></p>' : renderQ(Q[id], PEND);
    }).join('') + '</div>';
  }
  function pendingBar() {
    var ids = Object.keys(S.pending);
    if (!ids.length) { return ''; }
    return '<div class="pending noprint" role="status"><span>Changed answers: ' + esc(ids.map(function (i) { return Q[i].wording + ' → ' + fmtVal(Q[i], S.pending[i]); }).join('; ')) +
      '</span><button type="button" class="btn primary" data-update="1">Update the result</button><button type="button" class="btn" data-discard="1">Discard the changes</button></div>';
  }

  function trustBox(t) {
    var words = {LOW: 'Low', MODERATE: 'Moderate', FAIR: 'Fair'};
    return '<div class="trust" aria-label="Trust level"><strong>Trust level: ' + words[t.level] + '</strong>' +
      '<div class="meter" role="img" aria-label="Trust level ' + words[t.level] + ', step ' + t.step + ' of 3">' +
      t.levels.map(function (l) { return '<span class="' + (l === t.level ? 'on' : '') + '">' + words[l] + '</span>'; }).join('') + '</div>' +
      (t.level === 'LOW' ? '<p class="small">Low is the normal level until your own mill values and more observations are entered.</p>' : '') +
      '<details' + (S.trustOpen !== false ? ' open' : '') + ' data-trust="1"><summary>Why not higher?</summary><ul class="small">' +
      (t.reasons.length ? t.reasons.map(function (r) {
        var m = /^(.*?): (.{80,})$/.exec(r.text);
        return m ? '<li>' + esc(m[1]) + '. <details class="inline"><summary>Which ones</summary>' + esc(m[2]) + '</details></li>' : '<li>' + esc(r.text) + '</li>';
      }).join('') : '<li>No cap applies; the level is never higher than fair because nothing has been compared with plant data.</li>') +
      '</ul><details class="noprint"><summary class="small">The rule</summary><p class="small soft">' + esc(t.rule) + '</p></details></details></div>' +
      '<p class="small soft noprint">The full list of what this tool assumes and cannot decide is in docs/limitations.md of the repository.</p>';
  }

  function profileLine(sum, run) {
    var p = sum.profile || {id: run.profile, label: run.profile, left_out: []};
    return '<div class="profile"><span><strong>' + esc(p.label) + ' run</strong>' + (isNum(run.elapsed_s) ? ' (' + Math.round(run.elapsed_s) + ' s)' : '') + '.</span>' +
      (p.left_out && p.left_out.length ? '<details><summary>What the quick run left out (' + p.left_out.length + ')</summary><ul class="small">' +
        p.left_out.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></details>' +
        '<button type="button" class="btn noprint" data-rerun="' + run.id + '" data-profile="detailed">Run in detail</button>' : '<span>The case as entered, nothing left out.</span>') + '</div>';
  }

  function changeBox(sum) {
    var cmp = sum.compared_with_base;
    if (!cmp) { return ''; }
    var main = cmp.changes.filter(function (c) { return c.standing_before !== c.standing_after || c.score_before !== c.score_after; });
    var moved = cmp.changes.length - main.length;
    return '<div class="change" role="status"><strong>What changed since the earlier result</strong> (' + esc((S.run.changes || []).join(', ')) + ')' +
      (main.length ? '<ul>' + main.map(function (c) {
        return '<li><strong>' + esc(c.name) + '</strong>: ' + (c.standing_before !== c.standing_after ? esc(standingWordsOf(c.standing_before)) + ' → <strong>' + esc(standingWordsOf(c.standing_after)) + '</strong>, ' : esc(standingWordsOf(c.standing_after)) + ', ') +
          'score ' + c.score_before + ' → ' + c.score_after + ', place ' + c.rank_before + ' → ' + c.rank_after + '</li>';
      }).join('') + '</ul>' : '<p>No cause changed its standing or score.</p>') +
      (moved ? '<p class="small">' + moved + ' other cause' + (moved > 1 ? 's' : '') + ' moved place only because of the change above.</p>' : '') +
      (cmp.trust ? '<p>' + esc(cmp.trust.replace(/\bLOW\b/g, 'low').replace(/\bMODERATE\b/g, 'moderate').replace(/\bFAIR\b/g, 'fair')) + '</p>' : '') +
      '<button type="button" class="btn noprint" data-open-run="' + cmp.base_run_id + '">Back to the earlier result</button> <span class="small soft">In the bars, the thin grey line is the earlier score.</span></div>';
  }
  function standingWordsOf(s) { return M.standing_words[s] || s; }

  function stripResult(sum, compact) {
    var sv = sum.strip_view;
    if (!sv.available) { return '<p class="empty">No across-the-width picture: this case has no spray header or width model.</p>'; }
    var bw = sv.band_width_m;
    var svg = drawStrip({label: 'Across the width: bands you saw, positions the model predicts, nozzles and the roll growth', barrel: sv.barrel_length_m,
      edge: sv.strip_start_m, width: sv.strip_end_m - sv.strip_start_m,
      nozzles: (sv.nozzles || []).map(function (n) { return {pos: n.position_m, index: n.index, number: n.number, level: n.level}; }),
      bands: sv.observed_positions_m.map(function (x) { return {x: x, w: bw}; }), result: sv, compact: compact});
    if (compact) { return svg; }
    var items = [LEG_BAND];
    sv.predicted.forEach(function (p) { if (p.positions_m.length) { items.push(legKind(p.kind, p.label)); } });
    if (sv.nozzles) {
      items.push({icon: '<circle cx="15" cy="8" r="6" fill="url(#half)" stroke="var(--ink)"/>', text: 'Weak nozzle (half filled); blocked: filled with a cross'});
    }
    if (sv.thermal_profile) { items.push({icon: '<path d="M2 12q8 0 13-8q5 8 13 8" fill="none" stroke="var(--orange)" stroke-width="2"/>', text: 'Roll growth across the barrel (bumps are hot stripes)'}); }
    if (sv.matches.some(function (m) { return m.links.some(function (l) { return l.matched; }); })) {
      items.push({icon: '<line x1="4" y1="14" x2="26" y2="2" stroke="var(--green)" stroke-width="2" stroke-dasharray="3 2"/>', text: 'Your band matches a predicted position (within ' + mmSmall(sv.tolerance_m) + ')'});
    }
    var listRows = sv.observed_positions_m.map(function (x, i) {
      var hits = [];
      sv.matches.forEach(function (m) { m.links.forEach(function (l) { if (l.matched && Math.abs(l.observed_m - x) < 1e-9) { hits.push(m.label.toLowerCase() + ' at ' + mmInt(l.predicted_m - sv.strip_start_m)); } }); });
      return '<li>Band ' + (i + 1) + ' at ' + mmInt(x - sv.strip_start_m) + ': ' + (hits.length ? 'matches ' + esc(hits.join('; ')) : 'no predicted position within ' + mmSmall(sv.tolerance_m)) + '</li>';
    }).join('');
    return '<div class="fig">' + svg + '</div>' + legend(items) + '<details><summary>The same as a list</summary><ul class="small">' + (listRows || '<li>No band positions entered.</li>') + '</ul></details>';
  }

  // ------------------------------------------------------------------ flatness roll and the other measurements
  // the flatness roll chart: one bar per zone, the modelled flatness, the neutral band level.
  // On the screen (spec = the card's chart) with its legend and axis titles; on the printed page
  // (print) at its earlier size, the caption above it saying the same.
  function shapemeterSvg(v, print, spec) {
    W = drawW();
    var barrel = v.barrel_length_m || (v.strip_end_m + v.strip_start_m);
    var sx = (W - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var t = v.threshold_i_units, mx = t;
    v.zones.forEach(function (z) { if (isNum(z.reading_i_units)) { mx = Math.max(mx, Math.abs(z.reading_i_units)); } });
    v.profile.i_units.forEach(function (y) { mx = Math.max(mx, Math.abs(y)); });
    var lg = print ? {s: '', h: 0} : chartLegend(spec || {legend: ['zone_shows', 'zone_not', 'profile']}, W, 0);
    var top = print ? 18 : lg.h + 24, hh = 150, y0 = top + hh / 2, k = (hh / 2 - 6) / mx;
    function Y(val) { return y0 - val * k; }
    var edge = v.strip_start_m, ms = markOf(spec, 'zone_shows'), mn = markOf(spec, 'zone_not'), mp = markOf(spec, 'profile');
    var s = lg.s + (print ? '' : yTitle(spec, 4, top - 10));
    s += '<rect x="' + X(v.strip_start_m) + '" y="' + top + '" width="' + ((v.strip_end_m - v.strip_start_m) * sx) + '" height="' + hh + '" fill="var(--strip)" opacity=".45"/>';
    s += '<line class="tick" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + y0 + '" y2="' + y0 + '"/>';
    [t, -t].forEach(function (y) { s += refLine(X(0), Y(y), X(barrel), Y(y), 'band_level'); });
    s += refText(X(barrel) - 2, Y(t) - 4, '± ' + sig(t, 3) + ' I-units: band level', 'end');
    v.zones.forEach(function (z) {
      var r = z.reading_i_units, x0 = X(z.start_m) + 1, wpx = Math.max(1, (z.end_m - z.start_m) * sx - 2);
      var where = 'Zone ' + (z.index + 1) + ' (' + mmInt(z.start_m - edge) + ' to ' + mmInt(z.end_m - edge) + ' from the strip edge)';
      if (!isNum(r)) {
        s += '<g class="mark" tabindex="0" aria-label="' + esc(where + ': does not cover the strip') + '" data-tip="' + esc(where + ': does not cover the strip') + '"><rect x="' + x0 + '" y="' + (y0 - 2) + '" width="' + wpx + '" height="4" fill="none" stroke="var(--soft)"/></g>';
        return;
      }
      var shows = Math.abs(r) >= t;
      var words = where + ' would read ' + sig(r, 3) + ' I-units: ' + (shows ? 'would show' : 'would probably not show');
      s += markG(barRect(shows ? ms : mn, x0, Math.min(Y(r), y0), wpx, Math.abs(Y(r) - y0)).replace('class="glyph"', 'class="glyph zbar' + (shows ? ' shows' : '') + '"'), words);
    });
    var pts = [];
    v.profile.z_m.forEach(function (z, i) { pts.push(X(z).toFixed(1) + ',' + Y(v.profile.i_units[i]).toFixed(1)); });
    if (pts.length) { s += lineOf(mp, pts); }
    var yb = top + hh;
    s += '<text x="' + X(v.strip_start_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">0</text><text x="' + X(v.strip_end_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round((v.strip_end_m - v.strip_start_m) * 1000).toLocaleString('en-GB') + '</text>';
    var label = 'What each shapemeter zone would read, with the modelled flatness as a line';
    if (print) {
      s += '<text x="' + X(v.strip_start_m) + '" y="' + (yb + 32) + '" font-size="12" class="softtext">mm from the strip edge nearest nozzle 1; up = longer (loose), down = shorter (tight)</text>';
      return '<svg viewBox="0 0 ' + W + ' ' + (yb + 40) + '" role="group" aria-label="' + label + '">' + s + '</svg>';
    }
    var xt = xTitle(spec, yb + 32, W);
    return svgOpen(W, yb + 22 + xt.h, label) + s + xt.s + '</svg>';
  }
  // the printed page: the flatness roll chart beside the strip picture (the page has room there)
  function shapemeterPrint(sum) {
    var v = sum.shapemeter_view;
    if (!v || !v.available) { return ''; }
    return '<div class="printonly smprint"><p class="smprint-h"><strong>What your flatness roll would show</strong> (bars: zone readings; line: modelled flatness; dashed: band level)</p>' +
      shapemeterSvg(v, true) + '<p class="smprint-w">' + esc(v.caveat) + '</p></div>';
  }
  // the printed page: the flatness-control card in a compact form (takeaway, valve map, the
  // fixed sentence); its card on the screen is folded under its heading
  function loopPrint(sum) {
    var c = (sum.addon_cards || []).filter(function (x) { return x.id === 'loop' && x.chart; })[0];
    if (!c) { return ''; }
    return '<div class="printonly lpprint"><p class="smprint-h"><strong>' + esc(c.title) + '</strong>: ' + esc(c.takeaway) + '</p>' +
      chartSvg(c.chart) + '<p class="smprint-w">' + esc(c.caveat || '') + '</p></div>';
  }
  function nextChecks(sum) {
    if (!sum.next_checks.length) { return '<p class="empty">No further checks listed.</p>'; }
    var more = sum.next_checks.length - 3;
    return '<ul class="checklist">' + sum.next_checks.map(function (c, i) {
      var qs = c.questions.filter(function (q) { return Q[q]; });
      var key = 'nc-' + i;
      var open = S.openChecks[key];
      return '<li' + (i >= 3 ? ' class="pr-hide"' : '') + '><div class="row"><span>' + esc(c.text) + '</span>' + (qs.length ? '<button type="button" class="btn noprint" data-check="' + key + '" data-qs="' + esc(qs.join(',')) +
        '" aria-expanded="' + (open ? 'true' : 'false') + '">' + (open ? 'Close' : 'I have checked this') + '</button>' : '<span class="small soft">(no question in the form for this)</span>') + '</div>' +
        (open ? inlineQs(qs) : '') + '</li>';
    }).join('') + '</ul>' + (more > 0 ? '<p class="printonly small">… and ' + more + ' more (see the app).</p>' : '');
  }

  function whatIfCard() {
    var a = S.runAnswers ? S.runAnswers.values : {};
    var w = S.whatif || {};
    function stepper(id, label, unit, stepv, v) {
      return '<div><label class="w" for="wi-' + id + '">' + esc(label) + '</label><div class="stepper"><button type="button" data-wstep="' + id + '" data-d="' + (-stepv) + '" aria-label="Less">−</button>' +
        '<input type="number" step="any" id="wi-' + id + '" data-wi="' + id + '" value="' + (isNum(v) ? esc(v) : '') + '"><button type="button" data-wstep="' + id + '" data-d="' + stepv + '" aria-label="More">+</button>' +
        '<span class="unit">' + unit + '</span></div></div>';
    }
    var g = S.resultGeometry;
    var nn = g && g.nozzles ? g.nozzles.length : 0;
    var h = '<p class="howto">Change one or two values of this run and see what the model says would change. This is what the model says would change, not what will happen on the mill.</p><div class="whatif">' +
      stepper('exit_gauge', 'Exit gauge (must stay below ' + sig(a.entry_gauge, 4) + ' µm)', 'µm', isNum(a.exit_gauge) ? Math.max(0.5, Math.round(a.exit_gauge * 0.05 * 10) / 10) : 1, 'exit_gauge' in w ? w.exit_gauge : a.exit_gauge) +
      stepper('exit_speed', 'Exit speed', 'm/min', 30, 'exit_speed' in w ? w.exit_speed : a.exit_speed) +
      stepper('exit_tension', 'Exit tension (stress, 0 or more)', 'MPa', 2, 'exit_tension' in w ? w.exit_tension : a.exit_tension);
    if (nn) {
      h += '<div><label class="w" for="wi-noz">One nozzle</label><div class="numrow"><select id="wi-noz" data-wi="noz"><option value="">none</option>' +
        g.nozzles.map(function (n) { return '<option value="' + n.index + '"' + (String(w.noz) === String(n.index) ? ' selected' : '') + '>Nozzle ' + n.number + ' (' + mmInt(n.position_m - g.strip_start_m) + ')</option>'; }).join('') +
        '</select><select id="wi-nozstate" data-wi="nozstate"><option value="weak"' + (w.nozstate === 'weak' ? ' selected' : '') + '>weak</option><option value="blocked"' + (w.nozstate === 'blocked' ? ' selected' : '') + '>blocked</option></select></div></div>';
    }
    h += '</div><p><button type="button" class="btn primary" data-trywhatif="1">Try it</button> <span class="err" role="alert">' + esc(S.whatifError || '') + '</span></p>';
    if (S.compare) { h += compareHtml(S.compare); }
    return h;
  }

  function compareHtml(cmp) {
    function col(title, sum) {
      return '<div><h3>' + esc(title) + '</h3><p class="small">' + esc(sum.headline.text) + '</p>' + barsHtml(sum, sum.shortlist_ids.slice(0, 6), {compact: true}) +
        (sum.strip_view.available && sum.family.observed !== 'transverse' ? '<div class="fig">' + stripResult(sum, true) + '</div>' : '') + gaugeTable(sum) + '</div>';
    }
    return '<div class="change"><strong>What the model says would change</strong> (' + esc(cmp.changes.join(', ')) + '). Not what will happen.' +
      '<p>' + esc(cmp.diff) + '</p><div class="compare">' + col('This run', cmp.before) + col('What-if', cmp.after) + '</div>' +
      '<button type="button" class="btn" data-open-run="' + cmp.afterId + '">Open the what-if result</button></div>';
  }
  function gaugeTable(sum) {
    var gv = sum.gauge_view;
    if (!gv.available) { return ''; }
    var p = gv.passes.filter(function (x) { return Math.abs(x.exit_thickness_m - sum.pass.exit_thickness_m) < 1e-12; })[0] || gv.passes[gv.passes.length - 1];
    return '<table class="small"><caption class="soft">Pass ' + esc(p.label) + '</caption>' + gv.quantities.map(function (q) {
      var v = p.values[q.key], f = q.unit === 'um' ? 1e6 : 1e-6;
      return '<tr><td>' + esc(q.label) + '</td><td class="num">' + (isNum(v) ? sig(v * f, 3) + ' ' + esc(q.unit_label) : '–') + '</td></tr>';
    }).join('') + '</table>';
  }

  function renderResult(st) {
    var sum = st.summary, run = st.run;
    S.summary = sum;
    S.resultGeometry = sum.strip_view.available ? {nozzles: sum.strip_view.nozzles, strip_start_m: sum.strip_view.strip_start_m} : null;
    var fam = sum.family.observed;
    var shortIds = sum.shortlist_ids, otherIds = sum.other_family_ids;
    var note = '<p class="screening-note">A shortlist from a screening model that has not been compared with plant data, not a finding.</p>';
    var h = '<div class="wrap"><p class="printonly"><strong>Band screening summary</strong> — ' + esc(sum.case_name) + '</p>';
    h += '<section class="card"><div class="headline"><div><p class="text">' + esc(sum.headline.text) + '</p><p>' + esc(sum.family.text) + '</p>' +
      '<p class="statusline"><span aria-hidden="true">ⓘ</span><span>' + esc(sum.status_words) + '</span></p>' + profileLine(sum, run) + addonIndex(sum) + '</div>' + trustBox(sum.trust) + '</div></section>';
    var missing = sum.not_assessable.filter(function (x) { return x.kind === 'not_assessable' || x.kind === 'failed'; });
    if (sum.roll_gap_failed && missing.length) {
      h += '<section class="card" id="not-assessed-top"><h2>What could not be assessed</h2><p class="howto">How to read this: the roll-gap model could not compute the pass where the bands show, so these parts of the screening are missing. The shortlist below rests on the rest.</p>' +
        '<ul>' + missing.map(function (x) { return '<li><strong>' + esc(x.what) + '</strong>: ' + esc(x.why) + '</li>'; }).join('') + '</ul></section>';
    }
    h += '<section class="card" id="shortlist"><h2>The shortlist</h2><p class="howto">How to read this: each bar is one possible cause of ' + esc(sum.family.observed_words) +
      '. Bars to the right fit what you entered; bars left of zero do not fit. Select a bar for the details.</p>' + note + changeBox(sum) +
      barsHtml(sum, shortIds, {old: S.baseSummary}) +
      (otherIds.length ? '<details class="more"' + (S.otherOpen ? ' open' : '') + ' data-other="1"><summary>Causes of the other kind, and why they do not fit</summary>' + barsHtml(sum, otherIds, {old: S.baseSummary}) + '</details>' : '') +
      pendingBar() + '</section>';
    if (fam === 'transverse' || (!sum.strip_view.available && sum.along_view.available)) {
      h += '<section class="card"><h2>Along the strip</h2><p class="howto">How to read this: the top strip shows the mark spacing you measured, the bottom one the spacing of the best-fitting candidate with a spacing.</p>' +
        (sum.along_view.available ? '<div class="fig">' + alongSvg(sum.along_view) + '</div>' : '<p class="empty">No spacing measured yet: measure the mark spacing at two speeds to see this picture.</p>') + '</section>';
    } else {
      h += '<section class="card stripcard"><h2>Where across the width</h2><p class="howto">How to read this: the strip seen from above with the spray header over it. Solid bars are the bands you saw; outlined boxes with a letter are where the model puts a candidate; the line above shows where the roll grows. Hover, tap or tab to a mark for its position.</p>' +
        shapemeterPrint(sum) + stripResult(sum) + loopPrint(sum) + '</section>';
    }
    h += '<section class="card"><h2>What to check next</h2><p class="howto">How to read this: measurements that would narrow the shortlist. Tick one you have done, answer it, and update the result.</p>' + nextChecks(sum) + pendingBar() + '</section>';
    resetGloss();
    h += addonCards(sum);
    h += '<section class="card noprint"><h2>What if</h2>' + whatIfCard() + '</section>';
    if (sum.gauge_view.available && sum.gauge_view.passes.length < 2) {
      h += '<section class="card noprint"><h2>Thinner or thicker</h2><p class="empty">Only one pass is known. Add the other passes of the route in step 2 ("The route") to see how the result changes from thick to thin.</p></section>';
    } else if (sum.gauge_view.available) {
      h += '<section class="card noprint"><h2>Thinner or thicker</h2><p class="howto">How to read this: one small chart per quantity, passes from thickest (left) to thinnest (right). Hatched passes are not credible or have no roll-gap result and are left out.</p>' +
        multiples(sum.gauge_view) + (sum.gauge_view.direction_text ? '<p>' + esc(sum.gauge_view.direction_text) + '</p>' : '') + '</section>';
    }
    if (sum.temperature_view.available) {
      h += '<section class="card noprint"><h2>Temperature</h2><p class="howto">How to read this: modelled strip temperature leaving each pass' + (sum.temperature_view.battery_limits_apply ? ', against the published coil limit' : '') + '.</p>' +
        '<div class="fig" style="max-width:760px">' + tempSvg(sum.temperature_view) + '</div><p class="small">' + esc(sum.temperature_view.caveat) + '</p></section>';
    }
    h += '<section class="card"><h2>How far to trust this</h2><p class="howto">How to read this: what the tool noticed about this case, what it could not assess, and what it never does.</p>' +
      '<div class="noprint"><h3>Notes on this case</h3><ul class="flags">' + sum.flags_plain.map(function (f) { return '<li>' + esc(f.text) + (f.what_to_do ? '<br><span class="small soft">What to do: ' + esc(f.what_to_do) + '</span>' : '') + '</li>'; }).join('') + '</ul>' +
      '<h3 class="noprint">Could not be assessed</h3><ul class="small noprint">' + (sum.not_assessable.length ? sum.not_assessable.map(function (x) { return '<li>' + esc(x.what) + ': ' + esc(x.why) + '</li>'; }).join('') : '<li>Everything was assessed.</li>') + '</ul>' +
      '</div><h3>Always true</h3><ul class="small">' + sum.limitations.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></section>';
    h += '<section class="card noprint"><h2>Take it with you</h2><div class="takeaway"><button type="button" class="btn" data-report="' + run.id + '">Open the full engineering report</button>' +
      '<button type="button" class="btn" data-download="case.json">Download the case file</button><button type="button" class="btn" data-download="result.json">Download the result</button>' +
      '<button type="button" class="btn" data-print="1">Print a one-page summary</button><button type="button" class="btn" data-back-input="1">Change the answers</button></div></section></div>';
    app.innerHTML = h;
    animateBars();
  }

  function animateBars() {
    var fills = app.querySelectorAll('.fill[data-left]');
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function go() { for (var i = 0; i < fills.length; i++) { fills[i].style.left = fills[i].getAttribute('data-left') + '%'; fills[i].style.width = fills[i].getAttribute('data-width') + '%'; } }
    if (reduce) { go(); } else { requestAnimationFrame(function () { requestAnimationFrame(go); }); }
  }

  // ------------------------------------------------------------------ previous runs drawer
  function renderDrawer() {
    var d = document.getElementById('drawer');
    if (!S.drawer) { if (d) { d.remove(); } return; }
    if (!d) { d = document.createElement('aside'); d.id = 'drawer'; d.className = 'drawer'; d.setAttribute('aria-label', 'Previous runs'); document.body.appendChild(d); }
    var kids = {}, roots = [];
    S.runs.forEach(function (r) { if (r.base_run_id) { (kids[r.base_run_id] = kids[r.base_run_id] || []).push(r); } else { roots.push(r); } });
    var ids = {}; S.runs.forEach(function (r) { ids[r.id] = 1; });
    S.runs.forEach(function (r) { if (r.base_run_id && !ids[r.base_run_id]) { roots.push(r); } });
    var stW = {queued: 'waiting', running: 'running', done: 'done', failed: 'failed', cancelled: 'cancelled', interrupted: 'interrupted'};
    function item(r) {
      var when = (r.created || '').replace('T', ' ').slice(0, 16);
      var lead = (r.leaders || []).map(function (x) { return x.name; }).join(', ');
      return '<button type="button" class="runitem" data-open-run="' + r.id + '"><strong>' + esc(r.name) + '</strong><br><span class="small">' + esc(when) + ' UTC · ' +
        esc(stW[r.status] || r.status) + ' · ' + esc((M.profiles[r.profile] || {}).label || '') + (isNum(r.exit_thickness_m) ? ' · ' + gauge(r.exit_thickness_m) : '') +
        (r.product ? ' · ' + esc(productName(r.product)) : '') + (lead ? '<br>Fits best: ' + esc(lead) : '') + (r.trust ? ' · trust ' + esc(r.trust.toLowerCase()) : '') +
        (r.changes && r.changes.length ? '<br>What-if: ' + esc(r.changes.join(', ')) : '') + '</span></button>';
    }
    function tree(list) {
      return '<ul class="runs">' + list.map(function (r) { return '<li>' + item(r) + (kids[r.id] ? tree(kids[r.id]) : '') + '</li>'; }).join('') + '</ul>';
    }
    d.innerHTML = '<div class="numrow" style="justify-content:space-between"><h2>Previous runs</h2><button type="button" class="btn" data-drawer="0">Close</button></div>' +
      (S.runs.length ? tree(roots) : '<p class="empty">No runs yet. Answer the three steps and press "Run the screening".</p>');
  }
  function productName(id) {
    var n = id; M.products.forEach(function (g) { g.products.forEach(function (p) { if (p.id === id) { n = p.name; } }); }); return n;
  }
