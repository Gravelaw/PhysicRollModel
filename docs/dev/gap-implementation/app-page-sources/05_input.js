  // ------------------------------------------------------------------ input view
  var STEP_IDS = ['see', 'rolling', 'mill'];
  var PICK_ART = {
    longitudinal: '<svg viewBox="0 0 160 80" aria-hidden="true"><rect x="6" y="10" width="148" height="60" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      '<rect x="40" y="10" width="7" height="60" fill="var(--ink)"/><rect x="92" y="10" width="7" height="60" fill="var(--ink)"/>' +
      '<rect x="118" y="10" width="5" height="60" fill="var(--ink)" opacity=".7"/><path d="M14 76h40m-6-4l6 4-6 4" stroke="var(--soft)" fill="none"/>' +
      '<text x="58" y="79" font-size="9" class="softtext">rolling direction</text></svg>',
    transverse: '<svg viewBox="0 0 160 80" aria-hidden="true"><rect x="6" y="10" width="148" height="60" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      [24, 46, 68, 90, 112, 134].map(function (x) { return '<rect x="' + x + '" y="10" width="3.5" height="60" fill="var(--ink)"/>'; }).join('') +
      '<path d="M14 76h40m-6-4l6 4-6 4" stroke="var(--soft)" fill="none"/><text x="58" y="79" font-size="9" class="softtext">rolling direction</text></svg>',
    unsure: '<svg viewBox="0 0 160 80" aria-hidden="true"><rect x="6" y="10" width="148" height="60" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      '<text x="80" y="52" font-size="34" text-anchor="middle" class="softtext">?</text></svg>'
  };

  function pickCard(value, title, text, art) {
    var cur = val('orientation');
    var checked = value === 'unsure' ? (cur === null && S.touched.orientation) : cur === value;
    return '<label class="pick"><input type="radio" name="f-orientation" data-chip="orientation" data-v="' +
      esc(JSON.stringify(value === 'unsure' ? null : value)) + '"' + (checked ? ' checked' : '') + '>' + art +
      '<span class="t">' + esc(title) + '</span><span class="small soft">' + esc(text) + '</span></label>';
  }

  function groupBy(list) {
    var out = [], idx = {};
    list.forEach(function (q) {
      if (!(q.group in idx)) { idx[q.group] = out.length; out.push({group: q.group, qs: []}); }
      out[idx[q.group]].qs.push(q);
    });
    return out;
  }

  function stepSee() {
    var o = val('orientation');
    var h = '<h2>1. What do you see?</h2><p class="howto">Start with the direction of the marks. Answer what you know; ' +
      '"Don\'t know" is always fine and never counts against a cause.</p>';
    h += '<div class="picks" role="radiogroup" aria-label="Which way do the marks run?">' +
      pickCard('longitudinal', 'Stripes along the strip', 'Lengthwise bands at fixed places across the width', PICK_ART.longitudinal) +
      pickCard('transverse', 'Marks across the strip', 'Lines across the width, repeating along the strip', PICK_ART.transverse) +
      pickCard('unsure', 'Not sure', 'You will see the questions for both kinds', PICK_ART.unsure) + '</div>';
    var others = Q.orientation.choices.filter(function (c) { return ['diagonal', 'chevron', 'irregular'].indexOf(c.value) >= 0; });
    h += '<div class="q" data-q="orientation" id="f-q-orientation"><span class="w">Other shapes of mark across the strip</span>' +
      chipGroup(Q.orientation, FORM, others, ['diagonal', 'chevron', 'irregular'].indexOf(o) >= 0 ? o : '__', null) +
      '<div class="err" role="alert"></div></div>';
    var f = family();
    if (f === null && !S.touched.orientation) {
      h += '<p class="banner">Pick one of the pictures above to see the few questions that matter most for that kind of mark.</p>';
      return h;
    }
    var first = M.questions.filter(function (q) { return obsVisible(q, true); });
    h += '<h3>Ask first</h3><p class="howto">These observations separate the causes best' + (f ? ' for ' + (f === 'lengthwise' ? 'stripes along the strip' : 'marks across the strip') : '') + '.</p>';
    h += first.map(function (q) { return renderQ(q); }).join('');
    var rest = M.questions.filter(function (q) { return obsVisible(q, false); });
    if (rest.length) {
      h += '<details class="more" data-more="see"' + (S.openMore && S.openMore.see ? ' open' : '') + '><summary>More details (' + rest.length + ' more observations)</summary>' +
        rest.map(function (q) { return renderQ(q); }).join('') + '</details>';
    }
    return h;
  }

  function productBlock() {
    var q = Q.product, v = val('product');
    var h = '<div class="q" data-q="product" id="f-q-product"><label class="w" for="prod-filter">' + esc(q.wording) + '</label>' +
      '<p class="help">' + esc(q.help) + '</p><div class="numrow"><input type="search" id="prod-filter" placeholder="Type to search, for example battery" value="' +
      esc(S.prodFilter || '') + '" aria-controls="f-in-product"></div><div class="numrow" style="margin-top:.4rem"><select id="f-in-product" data-select="product"><option value="null">Not chosen</option>';
    var filt = (S.prodFilter || '').toLowerCase();
    M.products.forEach(function (g) {
      var items = g.products.filter(function (p) { return !filt || (p.name + ' ' + g.label).toLowerCase().indexOf(filt) >= 0 || p.id === v; });
      if (!items.length) { return; }
      h += '<optgroup label="' + esc(g.label) + '">' + items.map(function (p) {
        return '<option value="' + esc(JSON.stringify(p.id)) + '"' + (p.id === v ? ' selected' : '') + '>' + esc(p.name) + '</option>';
      }).join('') + '</optgroup>';
    });
    h += '</select><button type="button" class="btn" data-defaults="1"' + (v ? '' : ' disabled') + '>Fill in typical values for this product</button></div>';
    if (S.productInfo) { h += '<div class="banner small" role="status">' + S.productInfo + '</div>'; }
    return h + '<div class="err" role="alert">' + esc(S.errors.product || '') + '</div></div>';
  }

  function stepRolling() {
    var h = '<h2>2. What are you rolling?</h2><p class="howto">The product and the pass where the bands show. Values you do not change stay at the starting point\'s typical values.</p>';
    h += productBlock();
    h += '<h3>The pass where the bands show</h3>';
    h += ['entry_gauge', 'exit_gauge', 'strip_width', 'exit_speed'].filter(function (id) { return shown(Q[id]); }).map(function (id) { return renderQ(Q[id]); }).join('');
    h += '<h3>Alloy and temper</h3>' + ['alloy', 'temper'].map(function (id) { return renderQ(Q[id]); }).join('');
    h += '<h3>The route</h3>' + renderQ(Q.route) + '<div data-view="route">' + routeView() + '</div>';
    var rest = M.questions.filter(function (q) {
      return q.step === 'rolling' && !q.ask_first && !q.addon_group && ['product', 'alloy', 'temper', 'route'].indexOf(q.id) < 0 && visible(q);
    });
    h += '<details class="more" data-more="rolling"' + (S.openMore && S.openMore.rolling ? ' open' : '') + '><summary>More details (' + rest.length + ' more values)</summary>' +
      groupBy(rest).map(function (g) { return '<h4>' + esc(g.group) + '</h4>' + g.qs.map(function (q) { return renderQ(q); }).join(''); }).join('') + '</details>';
    return h;
  }

  function stepMill() {
    var p = preset();
    var h = '<h2>3. Your mill</h2><p class="howto">Pick a starting point, then replace the values that matter most with your own and say where each comes from.</p>';
    h += '<fieldset style="border:0;padding:0;margin:0"><legend class="w" style="font-weight:700">Starting point</legend><div class="presets">';
    M.presets.concat(S.presetsExtra).forEach(function (x) {
      h += '<label class="preset"><input type="radio" name="preset" data-preset="' + esc(x.id) + '"' + (x.id === S.presetId ? ' checked' : '') + '>' +
        '<span class="t">' + esc(x.label.charAt(0).toUpperCase() + x.label.slice(1)) + '</span><span class="small soft">' + esc(x.description) + '</span></label>';
    });
    h += '<label class="preset" for="casefile"><span class="t">Open a case file</span><span class="small soft">A band case JSON file from this tool or the template. It is checked, not stored.</span>' +
      '<input type="file" id="casefile" accept=".json,application/json" style="margin-top:.4rem;max-width:100%"></label></div></fieldset>';
    if (!M.worked_examples_available) { h += '<p class="small soft">Worked examples are not available in this installation (they come with the source folder).</p>'; }
    if (p.generated_by_model) { h += '<p class="banner">Worked example: its observations were generated by the model, not seen on a plant.</p>'; }
    if (p.kind === 'run') { h += '<p class="banner" role="status"><strong>Starting point: ' + esc(p.label) + '.</strong> Values you do not change stay as they were in that run.</p>'; }
    h += '<div class="q" data-q="own_mill"><label class="chip"><input type="checkbox" id="ownmill"' + (S.answers.own_mill ? ' checked' : '') +
      '> These are my mill\'s real values</label><p class="help">Tick this only when the mill values below are your mill\'s. Without it the case counts as synthetic and the trust level stays low.</p></div>';
    h += '<h3>The key mill values</h3>';
    h += M.questions.filter(function (q) { return q.step === 'mill' && q.ask_first && q.kind !== 'nozzles' && shown(q); })
      .map(function (q) { return renderQ(q); }).join('');
    h += '<h3>Spray header</h3>' + renderQ(Q.nozzle_levels);
    var rest = M.questions.filter(function (q) { return q.step === 'mill' && !q.ask_first && !q.addon_group && visible(q); });
    h += '<details class="more" data-more="mill"' + (S.openMore && S.openMore.mill ? ' open' : '') + '><summary>More details (' + rest.length + ' more values)</summary>' +
      groupBy(rest).map(function (g) { return '<h4>' + esc(g.group) + '</h4>' + g.qs.map(function (q) { return renderQ(q); }).join(''); }).join('') + '</details>';
    h += addonArea();
    h += '<div class="q"><label class="w" for="casename">Name for this case</label><input type="text" class="wide" id="casename" value="' + esc(S.answers.name || '') +
      '" placeholder="for example coil 4711, stand 2" style="padding:.4rem;border:1px solid var(--line);border-radius:5px;width:min(26rem,100%)"></div>';
    return h;
  }

  // the side panel states what the tool has, from the built case (the drawing model)
  function sideText() {
    var sd = model().side, parts = [];
    var o = sd.orientation, f = o === 'longitudinal' ? 'lengthwise' : o ? 'transverse' : null;
    if (f === 'lengthwise') {
      var n = sd.band_count, c = sd.continuity;
      var cw = {continuous: 'always there', intermittent: 'come and go', both: 'some always there, some come and go'}[c];
      parts.push('Lengthwise bands' + (n ? ' at ' + n + ' position' + (n > 1 ? 's' : '') : '') + (cw ? ', ' + cw : '') + '.');
    } else if (f === 'transverse') {
      var po = val('pitch_observations');
      parts.push((o === 'transverse' ? 'Marks across the strip' : 'Marks: ' + o) + (Array.isArray(po) && po.length ? ', spacing measured at ' + po.length + ' speed' + (po.length > 1 ? 's' : '') : '') + '.');
    } else {
      parts.push('Direction of the marks: not given yet.');
    }
    var g = sd.exit_gauge, sp = sd.exit_speed, prod = sd.product;
    var pname = '';
    if (prod) { M.products.forEach(function (gr) { gr.products.forEach(function (p) { if (p.id === prod) { pname = p.name.toLowerCase(); } }); }); }
    parts.push((isNum(g) ? (g < 1000 ? sig(g, 3) + ' µm' : sig(g / 1000, 3) + ' mm') + ' ' : '') + (pname || 'strip') + (isNum(sp) ? ' at ' + sig(sp, 3) + ' m/min' : '') + '.');
    var oc = {measured: sd.measured, estimated: sd.estimated};
    parts.push((sd.starting_point || preset().label) + (oc.measured || oc.estimated ? ', ' + oc.measured + ' value' + (oc.measured === 1 ? '' : 's') + ' measured, ' + oc.estimated + ' estimated' : ', no values of your own yet') +
      (sd.own_mill ? ' (marked as your mill)' : '') + '.');
    return parts;
  }

  function updateSide() {
    var box = document.getElementById('side');
    if (!box) { return; }
    var a = askFirstUnknown();
    var st = S.generalError ? '<p class="err" role="alert">' + esc(S.generalError) + '</p>' :
      Object.keys(S.errors).length ? '<p class="err" role="alert">One answer needs a look: ' + esc(Object.keys(S.errors).map(function (k) { return Q[k] ? Q[k].wording : k; }).join(', ')) + '</p>' :
      S.check ? '<p class="small">The tool accepts these inputs.</p>' : '<p class="small soft">Checking the inputs…</p>';
    box.innerHTML = '<h2>What the tool has so far</h2>' + (S.modelStale ? '<p class="small soft">As last accepted:</p>' : '') + '<ul>' + sideText().map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
      '<p><strong class="num">' + a.unknown + '</strong> of ' + a.total + ' "ask first" questions still unknown.</p>' + st;
    var rb = document.getElementById('runmsg');
    if (rb) {
      var bad = S.generalError || Object.keys(S.errors).length;
      rb.className = 'msg' + (bad ? ' err' : '');
      rb.textContent = bad ? 'Fix the answer marked in red before running.' :
        (a.unknown ? a.unknown + ' "ask first" questions unknown: you can run now and add them later.' : 'Ready to run.');
    }
  }

  function renderInput() {
    var i = STEP_IDS.indexOf(S.step);
    var prog = '<ol class="progress">' + M.steps.map(function (s, k) {
      return '<li class="' + (k < i ? 'done' : k === i ? 'current' : '') + '"><button type="button" data-step="' + s.id + '"' +
        (k === i ? ' aria-current="step"' : '') + '><span class="n">' + (k + 1) + '.</span><span class="lab">' + esc(s.label) + '</span><span class="short" aria-hidden="true">' + ['See', 'Rolling', 'Mill'][k] + '</span></button></li>';
    }).join('') + '</ol>';
    var stepHtml = S.step === 'see' ? stepSee() : S.step === 'rolling' ? stepRolling() : stepMill();
    var nav = '<div class="numrow noprint" style="justify-content:space-between;margin-top:1rem">' +
      (i > 0 ? '<button type="button" class="btn" data-step="' + STEP_IDS[i - 1] + '">Back: ' + esc(M.steps[i - 1].label) + '</button>' : '<span></span>') +
      (i < 2 ? '<button type="button" class="btn" data-step="' + STEP_IDS[i + 1] + '">Next: ' + esc(M.steps[i + 1].label) + '</button>' : '') + '</div>';
    var ban = S.banner ? '<p class="banner" role="status">' + esc(S.banner) + '</p>' : '';
    app.innerHTML = '<div class="wrap">' + prog + ban + '<div class="inputgrid"><section class="card" aria-label="' + esc(M.steps[i].label) + '">' + stepHtml + nav +
      '</section><aside class="sidepanel"><div class="card" id="side" aria-live="polite"></div>' +
      '<p class="screening-note">The result will be a shortlist from a screening model that has not been compared with plant data.</p></aside></div></div>' +
      '<div class="runbar"><div class="seg" role="radiogroup" aria-label="Kind of run">' +
      ['quick', 'detailed'].map(function (p) {
        return '<label title="' + esc(M.profiles[p].description) + '"><input type="radio" name="profile" data-profile="' + p + '"' + (S.profile === p ? ' checked' : '') + '>' + esc(M.profiles[p].label) + '</label>';
      }).join('') + '</div><button type="button" class="btn primary" id="runbtn" data-run="1">Run the screening</button><span id="runmsg" class="msg" aria-live="polite"></span></div>';
    updateSide();
  }
