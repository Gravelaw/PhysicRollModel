'use strict';
/* Band screening page. Vanilla JavaScript, no external assets. Everything a person reads
   comes from the plain-language layer (physicroll.band_plain) through the API. */
(function () {
  var TOKEN = document.querySelector('meta[name="band-app-token"]').content;
  var M = null;                       // /api/meta
  var Q = {};                         // question id -> question
  var S = {
    view: 'input', step: 'see', presetId: 'foil_mill', caseFile: null, presetsExtra: [],
    answers: {values: {}, origins: {}, own_mill: false, name: ''},
    touched: {}, suggested: {}, profile: 'quick', check: null, errors: {}, generalError: null,
    checkSeq: 0, run: null, runAnswers: null, summary: null, baseSummary: null,
    openCause: null, pending: {}, pendingOrigins: {}, openChecks: {}, whatif: null,
    compare: null, drawer: false, runs: [], poll: null, banner: null, productInfo: null,
    otherOpen: false,
    // what is drawn comes ONLY from the server's drawing model of the built case
    model: null, modelKey: null, modelStale: false, drawnKey: null,
    focusSel: null, editChain: null, busy: false,
    rev: 0, ctx: 0, nav: 0, appliedRev: -1, defaultsReq: 0, openReq: 0
  };
  var app = document.getElementById('app');

  // ------------------------------------------------------------------ helpers
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }
  function sig(x, n) {
    if (!isNum(x)) { return '–'; }
    if (x === 0) { return '0'; }
    var d = Math.max(0, (n || 3) - 1 - Math.floor(Math.log10(Math.abs(x))));
    var v = Number(x.toFixed(Math.min(d, 10)));
    return v.toLocaleString('en-GB', {maximumFractionDigits: Math.min(d, 10)});
  }
  function um(m) { return isNum(m) ? sig(m * 1e6, 3) + ' µm' : '–'; }
  // a small length (a tolerance, a band width) in mm without rounding it away: 0.05 mm, 13 mm
  function mmSmall(m) { if (!isNum(m)) { return '–'; } var x = m * 1000; return (Math.abs(x) >= 10 ? Math.round(x).toLocaleString('en-GB') : sig(x, 2)) + ' mm'; }
  function mmInt(m) { return isNum(m) ? Math.round(m * 1000).toLocaleString('en-GB') + ' mm' : '–'; }
  function gauge(m) {
    if (!isNum(m)) { return '–'; }
    return m < 1e-3 ? sig(m * 1e6, 3) + ' µm' : sig(m * 1e3, 3) + ' mm';
  }
  function mpm(ms) { return isNum(ms) ? sig(ms * 60, 3) + ' m/min' : '–'; }
  function degc(c) { return isNum(c) ? Math.round(c) + ' °C' : '–'; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
  function el(sel) { return app.querySelector(sel); }

  function api(method, path, body) {
    var opt = {method: method, headers: {'X-Band-App-Token': TOKEN}};
    if (body !== undefined) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    return fetch(path, opt).then(function (r) {
      return r.json().then(function (d) { return {status: r.status, data: d}; },
                          function () { return {status: r.status, data: {}}; });
    }, function () {
      return {status: 0, data: {error: {text: 'The app does not answer. Is it still running? ' +
        'Start it again and reload this page.'}}};
    });
  }
  function apiBlob(path) {
    return fetch(path, {headers: {'X-Band-App-Token': TOKEN}}).then(function (r) {
      if (!r.ok) { throw new Error('not available'); }
      return r.blob();
    });
  }

  // ------------------------------------------------------------------ answers
  function preset() {
    // never fall back silently to another mill: an unknown id is an error the page shows
    var all = M.presets.concat(S.presetsExtra);
    for (var i = 0; i < all.length; i++) { if (all[i].id === S.presetId) { return all[i]; } }
    throw new Error('unknown starting point ' + S.presetId);
  }
  function pv(id) { var v = preset().answers.values[id]; return v === undefined ? null : v; }
  function val(id) { var v = S.answers.values[id]; return v === undefined ? null : v; }
  // a question with a condition (for example the Tome-form hardening values) shows only when
  // the answer it depends on has one of the listed values
  function visible(q) { return shown(q) && (!q.show_if || q.show_if.values.indexOf(val(q.show_if.question)) >= 0); }
  function shown(q) {
    if (q.unknown !== 'preset') { return true; }
    var vals = preset().answers.values;
    if (Object.prototype.hasOwnProperty.call(vals, q.id)) { return true; }
    var key = q.key;
    for (var i = 0; i < M.sections.length; i++) {
      var sec = M.sections[i];
      if (key.indexOf(sec + '.') === 0) {
        var parent = sec.split('.').slice(0, -1).join('.');
        if (!parent) { return true; }
        for (var k in vals) {
          if (Q[k] && Q[k].key.indexOf(parent + '.') === 0) { return true; }
        }
      }
    }
    return false;
  }
  function setVal(id, v, opts) {
    var q = Q[id];
    opts = opts || {};
    S.touched[id] = true;
    delete S.suggested[id];
    if (q.origin_tracked) {
      if (v === null || v === '' || (Array.isArray(v) && !v.length && pv(id) !== null)) {
        S.answers.values[id] = clone(pv(id));
        S.answers.origins[id] = 'preset';
      } else {
        S.answers.values[id] = v;
        var o = S.answers.origins[id];
        S.answers.origins[id] = opts.origin || (o && o !== 'preset' ? o : 'estimated');
      }
    } else {
      S.answers.values[id] = (v === '' ? null : v);
    }
    if (id === 'alloy' || id === 'temper') {
      S.answers.values.alloy_stated = true;
      S.answers.origins.alloy_stated = 'estimated';
    }
    touch();
    scheduleCheck();
  }
  function family() {
    var o = val('orientation');
    if (o === 'longitudinal') { return 'lengthwise'; }
    if (o) { return 'transverse'; }
    return null;
  }
  function isFoil() { var g = val('exit_gauge'); return isNum(g) && g < 100; }
  function obsVisible(q, askFirstOnly) {
    if (q.step !== 'see' || q.id === 'orientation') { return false; }
    if (askFirstOnly !== undefined && q.ask_first !== askFirstOnly) { return false; }
    var f = family();
    if (q.family === 'both') { return true; }
    if (q.family === 'foil') { return f !== 'transverse' && (isFoil() || f === null); }
    return f === null || q.family === f;
  }
  function askFirstUnknown() {
    var n = 0, total = 0;
    M.questions.forEach(function (q) {
      if (q.step === 'see' && q.ask_first && (q.id === 'orientation' || obsVisible(q, true))) {
        total += 1;
        var v = val(q.id);
        if (v === null || (Array.isArray(v) && !v.length)) { n += 1; }
      }
    });
    return {unknown: n, total: total};
  }
  // the drawing model: the last one the server computed from the built case (or the starting
  // point's own, before the first check); never computed here
  function model() { return S.model || preset().model; }
  function modelKey() { return S.model ? S.modelKey : preset().model_key; }
  function body() {
    var p = preset();
    var b = {preset: p.ref || S.presetId, answers: S.answers};
    if (S.presetId === 'case_file') { b.case_file = S.caseFile; }
    return b;
  }

  // ------------------------------------------------------------------ replies and the inputs
  // THE RULE: a reply from the server may write into the page state (answers patch, model,
  // notices, errors, S.check, the starting point, the result view) only if it was computed from
  // the inputs the page holds when it arrives.
  //  - S.rev counts local changes of the inputs (every answer, its origin, the name, "my mill",
  //    the starting point, the opened case file): touch() advances it, synchronously, at the
  //    change. Every request records the revision it was built from; accept() drops a reply from
  //    an older revision whole and sends a fresh check. Applying the patch of an accepted reply
  //    is not a local change (it does not invalidate the reply carrying it), but it advances the
  //    revision so that other replies, computed without it, are dropped.
  //  - S.ctx counts starting points (typical mill, worked example, case file, reopened run, new
  //    screening). A nozzle edit whose reply comes back after another answer changed is not
  //    lost: its nozzle marks are applied to the current answers (the same as the edit first,
  //    then that change) and a check follows; after a change of starting point it is dropped.
  //  - S.nav counts navigation (a run opened, back to the answers, new screening): replies that
  //    change the view or the result state are dropped once the person has moved on.
  // Nothing here depends on the debounce timer or on timing.
  function touch() { S.rev += 1; }
  var checkTimer = null;
  function scheduleCheck() {
    if (checkTimer) { clearTimeout(checkTimer); }
    checkTimer = setTimeout(runCheck, 450);
    updateSide();
  }
  // the one gate for /api/case/check and /api/case/edit replies: true = apply it
  function accept(rev) { return rev === S.rev; }
  function runCheck() {
    if (checkTimer) { clearTimeout(checkTimer); checkTimer = null; }
    var rev = S.rev;
    return api('POST', '/api/case/check', body()).then(function (r) {
      if (!accept(rev)) { return runCheck(); }          // older inputs: dropped whole, check again
      takeCheck(r);
    });
  }
  function checkNow() { updateSide(); return runCheck(); }
  // the page is settled when the last reply applied was computed from the current inputs
  function settle() {
    return (S.editChain || Promise.resolve()).then(function () {
      return S.appliedRev === S.rev && !checkTimer ? null : runCheck().then(settle);
    });
  }
  var NOZZLE_KEYS = ['nozzle_levels', 'blocked_nozzles', 'coverage_blocked_nozzles'];
  // one nozzle edit: the server applies the rule and answers with the new answers and model;
  // edits are sent one after another, each from the answers the previous one left
  function sendEdit(edit, focusSel, after) {
    if (checkTimer) { clearTimeout(checkTimer); checkTimer = null; }
    var ctx = S.ctx;
    S.editChain = (S.editChain || Promise.resolve()).then(function () {
      if (ctx !== S.ctx) { return null; }                 // starting point switched: dropped
      var rev = S.rev, b = body();
      b.edit = edit; S.busy = true; markBusy();
      return api('POST', '/api/case/edit', b).then(function (r) {
        S.busy = false; markBusy();
        if (ctx !== S.ctx) { return null; }               // starting point switched: dropped
        if (accept(rev)) {
          if (r.status === 200) { S.touched.nozzle_levels = true; S.focusSel = focusSel || null; }
          takeCheck(r);
          if (r.status === 200 && after) { after(); }
          return null;
        }
        // another answer changed while the edit was on its way: keep the edit (its nozzle
        // marks only), then check the current answers
        if (r.status === 200) {
          var p = r.data.answers_patch || {}, hit = false;
          NOZZLE_KEYS.forEach(function (k) { if (Object.prototype.hasOwnProperty.call(p, k)) { S.answers.values[k] = p[k]; hit = true; } });
          if (hit) { S.touched.nozzle_levels = true; touch(); }
        }
        return runCheck();
      });
    });
    return S.editChain;
  }
  function takeCheck(r) {
    S.errors = {}; S.generalError = null;
    // dependent answers the server reconciled (never silently): apply its patch, show notices.
    // A reset is held while a number is still being typed (an intermediate "5" of "53" mm must
    // not wipe the marks): the notice and the server's drawing show it, the answers keep the
    // marks, and leaving the field checks again (a run is refused while a reset is pending)
    var hold = !!S.typingField && ((r.data && r.data.reconciled) || []).some(function (n) { return n.kind === 'reset'; });
    S.heldReset = hold;
    var changed = hold ? applyReconciled({reconciled: r.data.reconciled}) : applyReconciled(r.data);
    if (changed) { touch(); }       // replies computed without this patch are now older
    S.appliedRev = S.rev;
    if (r.status === 200) {
      S.check = r.data; S.model = r.data.model; S.modelKey = r.data.model_key; S.modelStale = false;
    } else {
      S.check = null; S.modelStale = true;
      var e = (r.data && r.data.error) || {text: 'The inputs could not be checked.'};
      if (e.question) { S.errors[e.question] = e.text; } else { S.generalError = e.text; }
    }
    if (S.view === 'input') { if (changed) { render(); } else { refreshViews(); refreshNotices(); } }
    markErrors();
    updateSide();
  }
  function markBusy() {
    var n = app.querySelectorAll('[data-view="nozzles"]');
    for (var i = 0; i < n.length; i++) { n[i].classList.toggle('busy', S.busy); n[i].setAttribute('aria-busy', S.busy ? 'true' : 'false'); }
  }
  // redraw every part of the page that shows the drawing model whenever the model on screen
  // differs from the server's (the whole model, by its key), never on a hand-picked field
  function drawnState() { return modelKey() + (S.modelStale ? ':stale' : ''); }
  function refreshViews(force) {
    if (!force && S.drawnKey === drawnState()) { return; }
    // every view is redrawn; the focused field gets its focus back and keeps what the person is
    // still typing in it (sent when they leave the field)
    var act = document.activeElement, keep = null;
    if (act && act.id && app.contains(act) && act.closest('[data-view]')) {
      keep = {id: act.id, value: act.value, typing: act.tagName === 'INPUT' && act.type !== 'checkbox' && act.type !== 'radio'};
      try { keep.s = act.selectionStart; keep.e = act.selectionEnd; } catch (err) { keep.s = null; }
    }
    var nodes = app.querySelectorAll('[data-view]');
    for (var i = 0; i < nodes.length; i++) {
      var name = nodes[i].getAttribute('data-view');
      nodes[i].innerHTML = name.indexOf('addon:') === 0 ? addonStatusHtml(name.slice(6)) : name.indexOf('addonclear:') === 0 ? addonClearHtml(name.slice(11)) : name === 'addoncount' ? addonCountHtml() : VIEWS[name]();
    }
    S.drawnKey = drawnState();
    if (keep) {
      var n = document.getElementById(keep.id);
      if (n) {
        if (keep.typing && n.value !== keep.value) { n.value = keep.value; }
        n.focus({preventScroll: true});
        try { if (keep.s !== null && keep.s !== undefined) { n.setSelectionRange(keep.s, keep.e); } } catch (err) { /* number fields */ }
      }
    }
    restoreFocus();
    markBusy();
  }
  function restoreFocus() {
    if (!S.focusSel) { return; }
    var f = app.querySelector(S.focusSel); S.focusSel = null;
    if (f) { f.focus({preventScroll: true}); }
  }
  // notices of the last check, under their question (refreshed with every check)
  function noticeHtml(qid) {
    var n = S.notices && S.notices[qid];
    if (!n) { return ''; }
    return '<div class="notice ' + n.kind + '" role="status">' + esc(n.text) +
      (n.kind === 'reset' && S.heldReset ? ' (Not applied while you are still typing: it applies when you leave the field.)' : '') + '</div>';
  }
  function refreshNotices() {
    var slots = app.querySelectorAll('[data-notice]');
    for (var i = 0; i < slots.length; i++) { slots[i].innerHTML = noticeHtml(slots[i].getAttribute('data-notice')); }
  }
  function staleNote() {
    return S.modelStale ? '<p class="stale-note" role="status">Not updated: an answer is not accepted (marked in red). This shows the last accepted inputs.</p>' : '';
  }
  function applyReconciled(data) {
    var notes = (data && data.reconciled) || [], patch = (data && data.answers_patch) || {};
    S.notices = {};
    notes.forEach(function (n) { S.notices[n.question] = {text: n.text, kind: n.kind}; });
    var changed = false;
    Object.keys(patch).forEach(function (q) {
      if (!Q[q]) { return; }
      if (!same(S.answers.values[q], patch[q])) { S.answers.values[q] = patch[q]; changed = true; }
    });
    return changed;
  }
  function markErrors() {
    var nodes = app.querySelectorAll('.q');
    for (var i = 0; i < nodes.length; i++) {
      var id = nodes[i].getAttribute('data-q');
      var bad = S.errors[id];
      nodes[i].classList.toggle('bad', !!bad);
      var slot = nodes[i].querySelector('.err');
      if (slot) { slot.textContent = bad || ''; }
    }
  }
