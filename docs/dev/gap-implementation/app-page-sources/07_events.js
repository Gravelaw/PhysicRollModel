  // ------------------------------------------------------------------ render and navigation
  function render() {
    var active = document.activeElement && document.activeElement.id;
    var y = window.scrollY;
    if (S.view === 'input') { renderInput(); S.drawnKey = drawnState(); }
    renderDrawer();
    if (active) { var a = document.getElementById(active); if (a) { a.focus({preventScroll: true}); } }
    restoreFocus();
    markBusy();
    window.scrollTo(0, y);
  }
  function goStep(step, qid) {
    S.view = 'input'; S.step = step;
    stopPoll();
    renderInput(); renderDrawer(); S.drawnKey = drawnState();
    if (qid) {
      var node = document.getElementById('f-q-' + qid);
      if (node) {
        var det = node.closest('details'); if (det) { det.open = true; }
        node.scrollIntoView({block: 'center'}); node.classList.add('flash');
        var inp = node.querySelector('input,select,button'); if (inp) { inp.focus({preventScroll: true}); }
      }
    } else { window.scrollTo(0, 0); }
  }

  // leaving the current view: replies that would change the view or the result are dropped
  function stopPoll() { S.nav += 1; if (S.poll) { clearTimeout(S.poll); S.poll = null; } }
  function openRun(id, opts) {
    stopPoll();
    S.drawer = false; renderDrawer();
    S.openChecks = {}; S.pending = {}; S.compare = opts && opts.keepCompare ? S.compare : null; S.whatif = null; S.openCause = null;
    S.view = 'run';
    poll(id, true);
  }
  function poll(id, first) {
    var nav = S.nav;
    api('GET', '/api/runs/' + id).then(function (r) {
      if (nav !== S.nav) { return; }                      // another run or view opened since
      if (r.status !== 200) { app.innerHTML = '<div class="wrap"><div class="card errorbox" role="alert"><p>' + esc((r.data.error || {}).text || 'This run cannot be opened.') + '</p><button type="button" class="btn" data-back-input="1">Back to the answers</button></div></div>'; return; }
      var st = r.data, run = st.run;
      S.run = run;
      if (run.status === 'queued' || run.status === 'running') {
        if (first || !document.getElementById('elapsed')) { renderRunning(st); }
        else { document.getElementById('elapsed').textContent = (isNum(run.elapsed_s) ? Math.round(run.elapsed_s) : 0) + ' s'; }
        S.poll = setTimeout(function () { poll(id, false); }, 700);
        return;
      }
      if (run.status === 'done' && run.summary_error) { renderSummaryError(st); return; }
      if (run.status !== 'done') {
        api('GET', '/api/runs/' + id + '/answers.json').then(function (a) { if (nav !== S.nav) { return; } S.runAnswers = a.status === 200 ? a.data.answers : null; renderFailed(st); });
        return;
      }
      Promise.all([api('GET', '/api/runs/' + id + '/answers.json'),
        run.base_run_id ? api('GET', '/api/runs/' + run.base_run_id) : Promise.resolve(null)]).then(function (res) {
        if (nav !== S.nav) { return; }
        S.runAnswers = res[0].status === 200 ? res[0].data.answers : null;
        S.baseSummary = res[1] && res[1].status === 200 && res[1].data.summary ? res[1].data.summary : null;
        renderResult(st);
        if (first) { window.scrollTo(0, 0); var hd = app.querySelector('.headline .text'); if (hd) { hd.setAttribute('tabindex', '-1'); hd.focus({preventScroll: true}); } }
      });
    });
  }
  function rerenderResult() {
    var y = window.scrollY, active = document.activeElement && document.activeElement.id;
    var key = document.activeElement && document.activeElement.getAttribute && document.activeElement.getAttribute('data-cause');
    renderResult({run: S.run, summary: S.summary});
    if (active && document.getElementById(active)) { document.getElementById(active).focus({preventScroll: true}); }
    else if (key) { var b = app.querySelector('[data-cause="' + key + '"]'); if (b) { b.focus({preventScroll: true}); } }
    window.scrollTo(0, y);
  }

  function startRun() {
    // first let pending edits and checks settle, so the run starts from what is drawn
    settle().then(startRunNow);
  }
  function startRunNow() {
    if (S.generalError || Object.keys(S.errors).length) {
      var first = Object.keys(S.errors)[0];
      if (first && Q[first]) { goStep(Q[first].step, first); }
      return;
    }
    var b = body(), rev = S.rev, nav = S.nav; b.profile = S.profile;
    var btn = document.getElementById('runbtn'); if (btn) { btn.disabled = true; }
    api('POST', '/api/runs', b).then(function (r) {
      // the run is what was pressed; it is opened unless the person went elsewhere meanwhile
      if (r.status === 202) { if (nav === S.nav) { openRun(r.data.id); } return; }
      if (btn) { btn.disabled = false; }
      if (!accept(rev)) { runCheck(); return; }          // refused for inputs no longer held
      var e = r.data.error || {text: 'The run could not be started.'};
      var patched = applyReconciled(r.data);
      if (patched) { touch(); }
      if (patched || (r.data.reconciled || []).length) {
        // a run is never started from answers the person has not seen: show the redrawn header
        S.check = null; runCheck();
        goStep(Q[e.question] ? Q[e.question].step : S.step, e.question);
        return;
      }
      if (e.question) { S.errors[e.question] = e.text; goStep(Q[e.question] ? Q[e.question].step : S.step, e.question); markErrors(); }
      else { S.generalError = e.text; updateSide(); }
    });
  }

  function setPreset(id, info) {
    var keepSteps = ['see', 'rolling'];
    touch(); S.ctx += 1;
    S.presetId = id;
    var p = preset();
    var keepVals = {}, keepOr = {};
    if (p.kind === 'mill') {
      Object.keys(S.touched).forEach(function (k) { if (Q[k] && keepSteps.indexOf(Q[k].step) >= 0) { keepVals[k] = S.answers.values[k]; keepOr[k] = S.answers.origins[k]; } });
    }
    S.answers.values = clone(p.answers.values);
    S.answers.origins = clone(p.answers.origins);
    S.answers.own_mill = !!p.answers.own_mill;
    if (p.kind !== 'mill') { S.touched = {}; S.answers.name = p.kind === 'example' ? p.label : (p.answers.name || ''); } else {
      Object.keys(keepVals).forEach(function (k) { S.answers.values[k] = keepVals[k]; if (keepOr[k]) { S.answers.origins[k] = keepOr[k]; } });
      var t = {}; Object.keys(keepVals).forEach(function (k) { t[k] = true; }); S.touched = t;
    }
    S.suggested = {}; S.check = null; S.errors = {}; S.generalError = null; S.productInfo = null;
    S.model = null; S.modelKey = null; S.modelStale = false; S.notices = {};
    S.banner = p.kind === 'example' ? 'Loaded "' + p.label + '". Its observations were generated by the model, not seen on a plant.' :
      p.kind === 'file' ? 'Opened the case file. Its values are shown as your answers.' : null;
    scheduleCheck();
  }

  function cycleNozzle(i) {
    // the server applies the rule; the drawing shows the state it then reports
    sendEdit({op: 'cycle', index: i}, '[data-noz="' + i + '"]', function () {
      var h = model().header, n = h && h.nozzles[i];
      if (n) { announce('Nozzle ' + n.number + ': ' + n.state); }
    });
  }
  var live = null;
  function announce(t) {
    if (!live) { live = document.createElement('div'); live.className = 'sr'; live.setAttribute('aria-live', 'polite'); document.body.appendChild(live); }
    live.textContent = t;
  }

  function setBands(list, focusIndex) {
    var wmm = Math.round(model().strip.width_m * 1000);
    list = list.map(function (x) { return Math.max(0, Math.min(wmm, Math.round(x))); });
    setVal('band_positions', list.length ? list : null);
    // drawn when the server's model of the new case arrives (redrawn on any difference)
    S.focusSel = focusIndex !== undefined ? '[data-band="' + focusIndex + '"]' : null;
    checkNow();
  }
  // edits compose on the stored answer (what was typed); what is drawn is the model
  function bandsList() { var v = val('band_positions'); return Array.isArray(v) ? v.slice() : []; }
  function svgMm(svg, evt) {
    var pt = svg.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    var ml = Number(svg.getAttribute('data-ml')), sx = Number(svg.getAttribute('data-sx')), edge = Number(svg.getAttribute('data-edge'));
    return ((p.x - ml) / sx - edge) * 1000;
  }

  // pending changes (check-and-update loop) or form answers
  function ctxOf(node) { return node.closest('.inline-q') ? 'p' : 'f'; }
  function store(id, v, node) {
    if (ctxOf(node) === 'p') { S.pending[id] = v; rerenderResult(); return; }
    setVal(id, v);
  }

  // ------------------------------------------------------------------ events
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-step],[data-run],[data-cause],[data-answer],[data-check],[data-update],[data-discard],[data-open-run],[data-rerun],[data-cancel],[data-back-input],[data-goto],[data-report],[data-download],[data-print],[data-drawer],[data-trywhatif],[data-wstep],[data-list-add],[data-list-del],[data-route-use],[data-band-add],[data-band-del],[data-band-clear],[data-noz],[data-noz-reset],[data-noz-init],[data-defaults],[data-new],[data-mark],[data-clear-group],[data-open-section]');
    if (!t) { var m = e.target.closest('.mark'); if (m) { showTip(m); } return; }
    var d = t.dataset;
    if (d.step) { goStep(d.step); }
    else if (d.run) { startRun(); }
    else if (d.cause) { S.openCause = S.openCause === d.cause ? null : d.cause; rerenderResult(); var dd = document.getElementById('detail-' + d.cause); if (dd) { dd.scrollIntoView({block: 'nearest'}); } }
    else if (d.answer) { var k = 'nl-' + S.openCause + '-' + d.answer; S.openChecks[k] = !S.openChecks[k]; rerenderResult(); }
    else if (d.check) { S.openChecks[d.check] = !S.openChecks[d.check]; rerenderResult(); }
    else if (d.update) {
      var navU = S.nav;
      api('POST', '/api/runs/' + S.run.id + '/variant', {changes: S.pending, profile: S.run.profile, label: String(S.run.name || '').replace(/ \((updated|what-if)\)$/, '') + ' (updated)'}).then(function (r) {
        if (navU !== S.nav) { return; }
        if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text || 'The update could not be started.'); }
      });
    }
    else if (d.discard) { S.pending = {}; S.openChecks = {}; rerenderResult(); }
    else if (d.openRun) { openRun(d.openRun); }
    else if (d.rerun) { var navR = S.nav; api('POST', '/api/runs/' + d.rerun + '/rerun', {profile: d.profile || 'detailed'}).then(function (r) { if (navR !== S.nav) { return; } if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text); } }); }
    else if (d.cancel) { var navC = S.nav; api('POST', '/api/runs/' + d.cancel + '/cancel', {}).then(function () { if (navC === S.nav) { stopPoll(); poll(d.cancel, true); } }); }
    else if (d.backInput) { if (S.run && S.view !== 'input') { reopenRun(S.run.id, null); } else { goStep(S.step); } }
    else if (d.goto) { if (S.view !== 'input' && S.run) { reopenRun(S.run.id, d.goto); } else { goStep(Q[d.goto].step, d.goto); } }
    else if (d.report) { apiBlob('/api/runs/' + d.report + '/report.html').then(function (b) { window.open(URL.createObjectURL(new Blob([b], {type: 'text/html'})), '_blank', 'noopener'); }, function () { alertBox('The report is not available.'); }); }
    else if (d.download) {
      apiBlob('/api/runs/' + S.run.id + '/' + d.download).then(function (b) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = (S.run.name || 'band').replace(/[^A-Za-z0-9_.-]+/g, '-') + '.' + d.download;
        document.body.appendChild(a); a.click(); a.remove();
      });
    }
    else if (d.print) { window.print(); }
    else if (d.drawer !== undefined) { S.drawer = d.drawer === '1'; refreshRuns(); }
    else if (d.trywhatif) { tryWhatIf(); }
    else if (d.wstep) {
      var inp = document.getElementById('wi-' + d.wstep); var v = Number(inp.value) + Number(d.d);
      inp.value = Math.round(v * 1000) / 1000; S.whatif = S.whatif || {}; S.whatif[d.wstep] = Number(inp.value);
    }
    else if (d.listAdd) {
      var q = Q[d.listAdd], cur = (ctxOf(t) === 'p' ? PEND : FORM).get(q.id);
      var rows = Array.isArray(cur) ? clone(cur) : [], row = {};
      q.fields.forEach(function (f) { row[f.name] = f.kind === 'choice' ? f.choices[0].value : f.kind === 'numbers' ? [] : null; });
      rows.push(row); store(q.id, rows, t); if (ctxOf(t) === 'f') { render(); }
    }
    else if (d.listDel) {
      var q2 = Q[d.listDel], rows2 = clone((ctxOf(t) === 'p' ? PEND : FORM).get(q2.id) || []);
      rows2.splice(Number(d.row), 1); store(q2.id, rows2.length ? rows2 : null, t); if (ctxOf(t) === 'f') { render(); }
    }
    else if (d.routeUse) {
      var r0 = (val('route') || [])[Number(d.routeUse)];
      if (r0) {
        [['entry_gauge', 'entry_thickness_m'], ['exit_gauge', 'exit_thickness_m'], ['flow_stress', 'mean_flow_stress_pa'], ['friction', 'friction_coefficient'],
          ['entry_tension', 'entry_tension_pa'], ['exit_tension', 'exit_tension_pa'], ['exit_speed', 'exit_speed_m_s']].forEach(function (p) { if (isNum(r0[p[1]])) { setVal(p[0], r0[p[1]]); } });
        render(); checkNow();
      }
    }
    else if (d.bandAdd) { var nb = document.getElementById('bp-new'), nv = Number(nb.value); if (nb.value !== '' && isFinite(nv)) { nb.value = ''; setBands(bandsList().concat([nv]), bandsList().length); } }
    else if (d.bandDel !== undefined) { var bl = bandsList().slice(); bl.splice(Number(d.bandDel), 1); setBands(bl); }
    else if (d.bandClear) { setBands([]); }
    else if (d.noz !== undefined && !t.closest('svg').dataset.dragging) { cycleNozzle(Number(d.noz)); }
    else if (d.nozReset) { sendEdit({op: 'clear'}); }
    else if (d.nozInit) { sendEdit({op: 'all_healthy'}); }
    else if (d.defaults) { productDefaults(); }
    else if (d.clearGroup) { clearGroup(d.clearGroup); }
    else if (d.openSection) {
      e.preventDefault();
      var sec = document.getElementById('sec-' + d.openSection);
      if (sec) { sec.open = true; sec.scrollIntoView({block: 'start'}); sec.querySelector('summary').focus({preventScroll: true}); }
    }
    else if (d.new) { newScreening(); }
  });

  function alertBox(t) { announce(t || ''); window.alert(t || 'Something went wrong.'); }

  function reopenRun(runId, gotoQ) {
    // "Change the answers": the server gives the run's own starting point (a named one, or the
    // run's stored case) and answers that rebuild exactly that run's case
    var nav = S.nav, rev = S.rev;
    api('GET', '/api/runs/' + runId + '/reopen').then(function (r) {
      if (nav !== S.nav || rev !== S.rev) { return; }      // the person moved on meanwhile
      if (r.status !== 200) { alertBox((r.data.error || {}).text || 'This run cannot be reopened.'); return; }
      touch(); S.ctx += 1;
      var ro = r.data, a = ro.answers || {};
      S.presetsExtra = S.presetsExtra.filter(function (p) { return p.kind !== 'run'; });
      if (ro.preset_info) {
        var info = ro.preset_info; info.id = 'run_' + runId; info.ref = ro.preset;
        S.presetsExtra.push(info); S.presetId = info.id;
      } else { S.presetId = ro.preset; }
      S.answers = clone({values: a.values || {}, origins: a.origins || {}, own_mill: !!a.own_mill, name: a.name || ''});
      S.touched = {}; Object.keys(S.answers.values).forEach(function (k) { S.touched[k] = true; });
      S.suggested = {}; S.check = null; S.errors = {}; S.generalError = null;
      S.model = null; S.modelKey = null; S.modelStale = false; S.notices = {};
      if (ro.profile) { S.profile = ro.profile; }
      S.banner = 'These are the answers of the run "' + (a.name || '') + '". Change what you need and run again.';
      scheduleCheck();
      if (gotoQ) { goStep(Q[gotoQ].step, gotoQ); } else { goStep('see'); }
    });
  }

  function renderSummaryError(st) {
    var run = st.run;
    app.innerHTML = '<div class="wrap"><section class="card banner" role="status"><h2>The screening ran, but the visual summary could not be built</h2>' +
      '<p>' + esc(run.summary_error) + '</p><p class="screening-note">A screening result from a model that has not been compared with plant data, not a finding.</p>' +
      '<div class="takeaway">' + (run.report_available !== false ? '<button type="button" class="btn primary" data-report="' + run.id + '">Open the full engineering report</button>' : '') +
      '<button type="button" class="btn" data-download="result.json">Download the result</button><button type="button" class="btn" data-download="case.json">Download the case file</button>' +
      '<button type="button" class="btn" data-back-input="1">Change the answers</button></div></section></div>';
  }

  document.addEventListener('change', function (e) {
    var t = e.target, d = t.dataset;
    if (d.chip) { var v = JSON.parse(d.v); if (d.chip === 'orientation' && ctxOf(t) === 'f') { S.touched.orientation = true; } store(d.chip, v, t); if (ctxOf(t) === 'f') { render(); } }
    else if (d.select) {
      if (d.select === 'product' && Object.keys(S.suggested).length) {
        S.productInfo = 'You chose another product. The typical values filled in before were for the previous product: fill them in again for this one, or keep and check them.';
      }
      store(d.select, JSON.parse(t.value), t); if (ctxOf(t) === 'f') { render(); }
    }
    else if (d.origin) { S.answers.origins[d.origin] = t.value; if (t.value === 'preset') { S.answers.values[d.origin] = clone(pv(d.origin)); } S.touched[d.origin] = true; touch(); scheduleCheck(); render(); }
    else if (d.preset) { setPreset(d.preset); render(); }
    else if (d.profile) { S.profile = d.profile; }
    else if (t.id === 'ownmill') { S.answers.own_mill = t.checked; touch(); scheduleCheck(); }
    else if (t.id === 'casename') { S.answers.name = t.value; touch(); scheduleCheck(); }
    else if (t.id === 'casefile') { openCaseFile(t.files[0]); }
    else if (d.num && ctxOf(t) === 'f') { S.typingField = null; if (S.heldReset) { checkNow(); } }   // drawings follow the model
    else if (d.bandpos !== undefined) { checkNow(); }
    else if (d.nozlevel !== undefined) {
      var x = Number(t.value);
      if (t.value !== '' && isFinite(x)) { sendEdit({op: 'set_level', index: Number(d.nozlevel), level: x}, '#nz-' + d.nozlevel); }
      else { refreshViews(true); }
    }
    else if (d.nozedit === 'blocked') {
      var pn = parseNums(t.value);
      if (pn === undefined) { S.errors.blocked_nozzles = 'Type whole nozzle numbers separated by commas, for example 4, 12.'; markErrors(); updateSide(); }
      else { sendEdit({op: 'set_blocked', numbers: pn || []}, '#f-in-blocked_nozzles'); }
    }
    else if (d.wi) { S.whatif = S.whatif || {}; S.whatif[d.wi] = t.tagName === 'SELECT' ? t.value : Number(t.value); }
    else if (t.closest('[data-more]')) { /* details toggle handled below */ }
  });
  document.addEventListener('toggle', function (e) {
    var t = e.target;
    if (t.dataset && t.dataset.more) { S.openMore = S.openMore || {}; S.openMore[t.dataset.more] = t.open; }
    if (t.dataset && t.dataset.other) { S.otherOpen = t.open; }
    if (t.dataset && t.dataset.trust) { S.trustOpen = t.open; }
    if (t.dataset && t.dataset.nozlist) { S.nozListOpen = t.open; }
    if (t.dataset && t.dataset.group) { S.openGroups = S.openGroups || {}; S.openGroups[t.dataset.group] = t.open; }
    if (t.dataset && t.dataset.section) { S.openSections = S.openSections || {}; S.openSections[t.dataset.section] = t.open; }
  }, true);
  document.addEventListener('input', function (e) {
    var t = e.target, d = t.dataset;
    if (t.id === 'prod-filter') { S.prodFilter = t.value; var pos = t.selectionStart; render(); var f = document.getElementById('prod-filter'); f.focus(); f.setSelectionRange(pos, pos); return; }
    if (d.num) { if (ctxOf(t) === 'f') { S.typingField = d.num; } storeQuiet(d.num, t.value === '' ? null : Number(t.value), t); }
    else if (d.text) { storeQuiet(d.text, t.value.trim() === '' ? null : t.value, t); }
    else if (d.nums) { var p = parseNums(t.value); if (p !== undefined) { storeQuiet(d.nums, p, t); } }
    else if (d.list) {
      var q = Q[d.list], cur = clone((ctxOf(t) === 'p' ? PEND : FORM).get(q.id) || []), row = cur[Number(d.row)];
      var fk = d.fkind, v = t.tagName === 'SELECT' ? t.value : fk === 'numbers' ? (parseNums(t.value) || []) : fk === 'text' ? t.value : (t.value === '' ? null : Number(t.value));
      row[d.field] = v; storeQuiet(q.id, cur, t);
    }
    else if (d.bandpos !== undefined) { var bl = bandsList(); if (t.value !== '') { bl[Number(d.bandpos)] = Number(t.value); setVal('band_positions', bl); } }
  });
  function storeQuiet(id, v, node) {
    if (ctxOf(node) === 'p') { S.pending[id] = v; var pb = app.querySelectorAll('.pending'); if (!pb.length) { rerenderResult(); } else { var html = pendingBar(); for (var i = 0; i < pb.length; i++) { pb[i].outerHTML = html; } } return; }
    setVal(id, v);
  }

  // keyboard on drawing marks
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (t.dataset && t.dataset.band !== undefined) {
      var i = Number(t.dataset.band), bl = bandsList().slice(), step = e.shiftKey ? 10 : 1;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { bl[i] -= step; setBands(bl, i); e.preventDefault(); }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { bl[i] += step; setBands(bl, i); e.preventDefault(); }
      else if (e.key === 'Delete' || e.key === 'Backspace') { bl.splice(i, 1); setBands(bl); e.preventDefault(); }
    } else if (t.dataset && t.dataset.noz !== undefined && (e.key === 'Enter' || e.key === ' ')) {
      cycleNozzle(Number(t.dataset.noz)); e.preventDefault();
    } else if (t.id === 'bp-new' && e.key === 'Enter') {
      var nv = Number(t.value); if (t.value !== '' && isFinite(nv)) { t.value = ''; setBands(bandsList().concat([nv])); S.focusSel = '#bp-new'; }
      e.preventDefault();
    } else if (e.key === 'Escape') { hideTip(); if (S.drawer) { S.drawer = false; renderDrawer(); } }
  });
  document.addEventListener('focusin', function (e) { if (e.target.getAttribute && e.target.getAttribute('data-tip')) { showTip(e.target); } });
  document.addEventListener('focusout', hideTip);
  // a tooltip never stays behind at an old place: it follows its focused mark, or goes
  window.addEventListener('scroll', function () {
    var a = document.activeElement;
    if (a && a.getAttribute && a.getAttribute('data-tip')) { showTip(a); } else { hideTip(); }
  }, {passive: true});
  document.addEventListener('pointerover', function (e) { var m = e.target.closest && e.target.closest('[data-tip]'); if (m && e.pointerType === 'mouse') { showTip(m); } });
  document.addEventListener('pointerout', function (e) { if (e.target.closest && e.target.closest('[data-tip]')) { hideTip(); } });

  // pointer: place and drag bands on the input strip
  var drag = null;
  document.addEventListener('pointerdown', function (e) {
    var svg = e.target.closest && e.target.closest('#strip-input');
    if (!svg) { return; }
    var band = e.target.closest('[data-band]');
    if (band) {
      drag = {i: Number(band.dataset.band), svg: svg, moved: false};
      band.classList.add('drag');
      svg.setPointerCapture(e.pointerId); e.preventDefault();
    } else if (e.target.closest('[data-strip]')) {
      setBands(bandsList().concat([svgMm(svg, e)]), bandsList().length);
      announce('Band added at ' + Math.round(svgMm(svg, e)) + ' mm');
    }
  });
  document.addEventListener('pointermove', function (e) {
    if (!drag) { return; }
    var mm = svgMm(drag.svg, e), wmm = Number(drag.svg.dataset.width) * 1000;
    mm = Math.max(0, Math.min(wmm, Math.round(mm)));
    var r = drag.svg.querySelector('[data-band="' + drag.i + '"]');
    var sx = Number(drag.svg.dataset.sx), ml = Number(drag.svg.dataset.ml), edge = Number(drag.svg.dataset.edge);
    var w = Number(r.getAttribute('width'));
    r.setAttribute('x', ml + (edge + mm / 1000) * sx - w / 2);
    drag.mm = mm; drag.moved = true;
  });
  document.addEventListener('pointerup', function () {
    if (!drag) { return; }
    var d = drag; drag = null;
    if (d.moved) { var bl = bandsList().slice(); bl[d.i] = d.mm; setBands(bl, d.i); }
  });

  // ------------------------------------------------------------------ actions
  function openCaseFile(file) {
    if (!file) { return; }
    if (file.size > 900 * 1024) { alertBox('This file is too large for a case file.'); return; }
    var reader = new FileReader();
    reader.onload = function () {
      var c;
      try { c = JSON.parse(reader.result); } catch (err) { alertBox('This file is not a JSON case file. Choose a band case file (.json).'); return; }
      var req = ++S.openReq, rev = S.rev;
      api('POST', '/api/case/open', {case_file: c}).then(function (r) {
        if (req !== S.openReq) { return; }                // a later file was chosen
        if (rev !== S.rev) { S.banner = 'The case file was not opened: the answers changed while it was being checked. Open it again if you still want it.'; if (S.view === 'input') { render(); } return; }
        if (r.status !== 200) { alertBox((r.data.error || {}).text || 'The case file is not accepted.'); return; }
        S.caseFile = c;
        var info = r.data.preset; info.id = 'case_file';
        S.presetsExtra = S.presetsExtra.filter(function (p) { return p.id !== 'case_file'; }).concat([info]);
        setPreset('case_file'); render();
      });
    };
    reader.readAsText(file);
  }

  function productDefaults() {
    var pid = val('product'); if (!pid) { return; }
    var b = {product: pid};
    if (isNum(val('exit_gauge')) && S.touched.exit_gauge) { b.exit_thickness_m = val('exit_gauge') / 1e6; }
    if (isNum(val('entry_gauge')) && S.touched.entry_gauge) { b.entry_thickness_m = val('entry_gauge') / 1e6; }
    S.productInfo = 'Looking up typical values…'; render();
    var req = ++S.defaultsReq, rev = S.rev;
    api('POST', '/api/product-defaults', b).then(function (r) {
      if (req !== S.defaultsReq) { return; }             // a later lookup was asked for
      if (rev !== S.rev) { S.productInfo = 'The answers changed while the typical values were looked up, so they were not filled in. Press the button again.'; if (S.view === 'input') { render(); } return; }
      if (r.status !== 200) { S.productInfo = esc((r.data.error || {}).text || 'No typical values found.'); render(); return; }
      var v = r.data.values;
      Object.keys(v).forEach(function (k) {
        if (!Q[k] || v[k] === null) { return; }
        if (k === 'product') { return; }
        S.answers.values[k] = v[k];
        if (Q[k].origin_tracked) { S.answers.origins[k] = 'estimated'; }
        S.suggested[k] = true; S.touched[k] = true;
      });
      delete S.suggested.alloy_stated;
      touch();
      var kind = r.data.mill_kind, cur = preset();
      S.productInfo = 'Filled in ' + esc(r.data.label) + '. They are marked "suggested — confirm" until you change or confirm them.' +
        (cur.kind === 'mill' && cur.id !== kind + '_mill' ? ' This product is usually rolled on a ' + kind + ' mill: you may want the typical ' + kind + ' mill in step 3.' : '');
      scheduleCheck(); render();
    });
  }

  function tryWhatIf() {
    var a = S.runAnswers ? S.runAnswers.values : {}, w = S.whatif || {}, ch = {};
    ['exit_gauge', 'exit_speed', 'exit_tension'].forEach(function (k) {
      var inp = document.getElementById('wi-' + k); var v = inp && inp.value !== '' ? Number(inp.value) : null;
      if (isNum(v) && v !== a[k]) { ch[k] = v; }
    });
    S.whatifError = null;
    if (isNum(ch.exit_gauge) && (ch.exit_gauge <= 0 || ch.exit_gauge >= a.entry_gauge)) { S.whatifError = 'The exit gauge must stay above 0 and below the entry gauge (' + sig(a.entry_gauge, 4) + ' µm).'; }
    if (isNum(ch.exit_tension) && ch.exit_tension < 0) { S.whatifError = 'The exit tension must be 0 or more.'; }
    if (isNum(ch.exit_speed) && (ch.exit_speed <= 0 || ch.exit_speed > 12000)) { S.whatifError = 'The speed must be above 0 and at most 12000 m/min.'; }
    var nozSel = document.getElementById('wi-noz');
    if (nozSel && nozSel.value !== '') {
      var g = S.resultGeometry, lv = g.nozzles.map(function (n) { return n.level; });
      lv[Number(nozSel.value)] = document.getElementById('wi-nozstate').value === 'blocked' ? 0 : M.weak_nozzle_level;
      ch.nozzle_levels = lv;
    }
    if (!Object.keys(ch).length && !S.whatifError) { S.whatifError = 'Change at least one value first.'; }
    if (S.whatifError) { rerenderResult(); return; }
    var words = Object.keys(ch).map(function (k) {
      return k === 'nozzle_levels' ? 'nozzle ' + (Number(nozSel.value) + 1) + ' ' + document.getElementById('wi-nozstate').value :
        Q[k].wording + ' ' + fmtVal(Q[k], a[k]) + ' → ' + fmtVal(Q[k], ch[k]);
    });
    var before = S.summary, baseRun = S.run, nav = S.nav;
    api('POST', '/api/runs/' + S.run.id + '/variant', {changes: ch, profile: S.run.profile, label: (S.run.name || '') + ' (what-if)'}).then(function (r) {
      if (nav !== S.nav) { return; }                     // another run or view opened since
      if (r.status !== 202) { S.whatifError = (r.data.error || {}).text; rerenderResult(); return; }
      var id = r.data.id;
      var sec = app.querySelector('[data-trywhatif]'); if (sec) { sec.disabled = true; sec.textContent = 'Running the what-if…'; }
      (function wait() {
        api('GET', '/api/runs/' + id).then(function (s) {
          if (nav !== S.nav) { return; }                 // the what-if stays in "Previous runs"
          var st = s.data.run.status;
          if (st === 'queued' || st === 'running') { setTimeout(wait, 700); if (sec) { sec.textContent = 'Running the what-if… ' + Math.round(s.data.run.elapsed_s || 0) + ' s'; } return; }
          if (st !== 'done') { S.whatifError = (s.data.run.error || {}).text || 'The what-if did not finish.'; rerenderResult(); return; }
          var after = s.data.summary;
          S.compare = {before: before, after: after, afterId: id, changes: words, diff: after.compared_with_base ? after.compared_with_base.text : ''};
          rerenderResult(); var c = app.querySelector('.compare'); if (c) { c.scrollIntoView({block: 'start'}); }
        });
      })();
    });
  }

  function refreshRuns() {
    api('GET', '/api/runs').then(function (r) { if (r.status === 200) { S.runs = r.data.runs; } renderDrawer(); var c = document.querySelector('#drawer button'); if (c && S.drawer) { c.focus(); } });
  }
  function newScreening() {
    S.answers = {values: {}, origins: {}, own_mill: false, name: ''}; S.touched = {}; S.presetId = 'foil_mill';
    setPreset('foil_mill'); S.banner = null; S.runAnswers = null; S.step = 'see'; goStep('see');
  }

  var lastW = window.innerWidth;
  window.addEventListener('resize', function () {
    if (Math.abs(window.innerWidth - lastW) < 40) { return; }
    lastW = window.innerWidth;
    clearTimeout(S.resizeT);
    S.resizeT = setTimeout(function () { if (S.view === 'input') { render(); } else if (S.summary && S.run && S.run.status === 'done') { rerenderResult(); } }, 250);
  });

  // ------------------------------------------------------------------ start
  function topbar() {
    var bar = document.createElement('header');
    bar.className = 'topbar';
    bar.innerHTML = '<div class="brand"><h1>Band screening</h1><small>Shortlist of causes from a screening model, not compared with plant data</small></div>' +
      '<button type="button" class="btn" data-new="1">New screening</button><button type="button" class="btn" data-drawer="1">Previous runs</button>';
    document.body.insertBefore(bar, app);
  }
  api('GET', '/api/meta').then(function (r) {
    if (r.status !== 200) { app.innerHTML = '<div class="wrap"><div class="card errorbox" role="alert"><p>' + esc((r.data.error || {}).text || 'The app could not start.') + '</p></div></div>'; return; }
    M = r.data;
    M.questions.forEach(function (q) { Q[q.id] = q; });
    topbar();
    setPreset('foil_mill');
    S.banner = null;
    goStep('see');
  });
})();
