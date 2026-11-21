  // ------------------------------------------------------------------ question widgets
  // ctx: {get(id), prefix} lets the same widgets edit the form answers or pending changes
  var FORM = {get: val, prefix: 'f', origin: true};

  function unitText(q) { return q.unit_label ? '<span class="unit">' + esc(q.unit_label) + '</span>' : ''; }
  function fmtVal(q, v) {
    if (v === null || v === undefined) { return 'not set'; }
    if (q.kind === 'yesno') { return v ? 'yes' : 'no'; }
    if (q.kind === 'choice') {
      for (var i = 0; i < q.choices.length; i++) { if (q.choices[i].value === v) { return q.choices[i].label; } }
    }
    if (Array.isArray(v)) { return v.length + ' entr' + (v.length === 1 ? 'y' : 'ies'); }
    if (typeof v === 'number') { return sig(v, 4) + (q.unit_label ? ' ' + q.unit_label : ''); }
    return String(v);
  }

  function originMark(q, ctx) {
    if (!q.origin_tracked || !ctx.origin) { return ''; }
    var o = S.answers.origins[q.id] || 'preset';
    var opts = [['measured', 'Measured'], ['estimated', 'Estimated'], ['preset', 'Left at the typical value']];
    return '<fieldset class="origin"><legend class="sr">Where this value comes from</legend>' +
      opts.map(function (x) {
        return '<label><input type="radio" name="' + ctx.prefix + '-o-' + q.id + '" value="' + x[0] +
          '" data-origin="' + q.id + '"' + (o === x[0] ? ' checked' : '') + '>' + x[1] + '</label>';
      }).join('') + '</fieldset>';
  }

  function typicalLine(q, ctx) {
    if (!q.origin_tracked || !ctx.origin) { return ''; }
    var p = pv(q.id), out = '';
    if (p !== null && !same(p, ctx.get(q.id))) { out = 'Typical value: ' + esc(fmtVal(q, p)) + '. '; }
    if (S.suggested[q.id] || ((q.id === 'alloy' || q.id === 'temper') && S.answers.values.alloy_stated === false)) {
      out += '<span class="badge suggest">suggested — confirm</span> ' +
        'Typical value from the literature for this product and gauge. Change it or mark it to confirm it.';
    }
    return out ? '<div class="typical">' + out + '</div>' : '';
  }

  function chipGroup(q, ctx, choices, current, unknownLabel) {
    var name = ctx.prefix + '-' + q.id;
    var h = '<fieldset class="chips"><legend class="sr">' + esc(q.wording) + '</legend>';
    choices.forEach(function (c, i) {
      h += '<label class="chip"><input type="radio" name="' + name + '" id="' + name + '-' + i +
        '" data-chip="' + q.id + '" data-v="' + esc(JSON.stringify(c.value)) + '"' +
        (same(current, c.value) ? ' checked' : '') + '>' + esc(c.label) + '</label>';
    });
    if (unknownLabel) {
      h += '<label class="chip unknown"><input type="radio" name="' + name + '" id="' + name +
        '-u" data-chip="' + q.id + '" data-v="null"' + (current === null ? ' checked' : '') + '>' +
        esc(unknownLabel) + '</label>';
    }
    return h + '</fieldset>';
  }

  function widget(q, ctx) {
    var v = ctx.get(q.id), id = ctx.prefix + '-in-' + q.id;
    var unk = q.unknown === 'preset' ? null : "Don't know / not checked";
    // nozzle marks: views of the drawing model (one stored answer, see apply_nozzle_edit)
    if (q.id === 'blocked_nozzles' && ctx.prefix === 'f') { return '<div data-view="blocked">' + blockedView() + '</div>'; }
    if (q.id === 'coverage_blocked_nozzles' && ctx.prefix === 'f' && coverageView() !== null) { return '<div data-view="coverage">' + coverageView() + '</div>'; }
    var note = q.id === 'coverage_blocked_nozzles' && ctx.prefix === 'f' ? '<div data-view="covnote">' + coverageNote() + '</div>' : '';
    if (q.kind === 'yesno') {
      return chipGroup(q, ctx, [{value: true, label: 'Yes'}, {value: false, label: 'No'}], v, unk);
    }
    if (q.kind === 'choice') {
      if (q.choices.length <= 6 && q.unknown !== 'preset') {
        return chipGroup(q, ctx, q.choices, v, unk);
      }
      var h = '<select id="' + id + '" data-select="' + q.id + '">';
      if (q.unknown !== 'preset' || v === null) { h += '<option value="null">' + (q.id === 'product' ? 'Not chosen' : "Don't know") + '</option>'; }
      q.choices.forEach(function (c) {
        h += '<option value="' + esc(JSON.stringify(c.value)) + '"' + (same(c.value, v) ? ' selected' : '') + '>' + esc(c.label) + '</option>';
      });
      return h + '</select>';
    }
    if (q.kind === 'number') {
      return '<div class="numrow"><input type="number" step="any" inputmode="decimal" id="' + id +
        '" data-num="' + q.id + '" value="' + (isNum(v) ? esc(v) : '') + '" placeholder="' +
        (q.unknown === 'preset' ? 'typical value' : "Don't know") + '" aria-describedby="' + ctx.prefix +
        '-h-' + q.id + '">' + unitText(q) + '</div>';
    }
    if (q.kind === 'text') {
      return '<div class="numrow"><input type="text" class="wide" id="' + id + '" data-text="' + q.id +
        '" value="' + esc(v === null ? '' : v) + '" aria-describedby="' + ctx.prefix + '-h-' + q.id + '"></div>';
    }
    if (q.kind === 'numbers') {
      return note + '<div class="numrow"><input type="text" class="wide" id="' + id + '" data-nums="' + q.id +
        '" value="' + esc(Array.isArray(v) ? v.join(', ') : '') + '" placeholder="' +
        (q.unknown === 'preset' ? 'none' : "Don't know") + '" aria-describedby="' + ctx.prefix + '-h-' + q.id +
        '">' + unitText(q) + '<span class="small soft">separate with commas</span></div>';
    }
    if (q.kind === 'list') { return listEditor(q, ctx); }
    if (q.kind === 'positions') { return bandsInput(q, ctx); }
    if (q.kind === 'nozzles') { return nozzleInput(q, ctx); }
    return '';
  }

  function listEditor(q, ctx) {
    var rows = Array.isArray(ctx.get(q.id)) ? ctx.get(q.id) : [];
    var h = '<div class="scrollbox"><table class="listedit"><thead><tr>';
    q.fields.forEach(function (f) { h += '<th scope="col">' + esc(f.label) + (f.unit_label ? ' (' + esc(f.unit_label) + ')' : '') + '</th>'; });
    if (q.id === 'route') { h += '<th scope="col">Bands show</th>'; }
    h += '<th scope="col"><span class="sr">Remove</span></th></tr></thead><tbody>';
    rows.forEach(function (row, i) {
      h += '<tr>';
      q.fields.forEach(function (f) {
        var v = row[f.name], a = ' data-list="' + q.id + '" data-row="' + i + '" data-field="' + f.name + '"';
        var lab = ' aria-label="' + esc(f.label + ', entry ' + (i + 1)) + '"';
        if (f.kind === 'choice') {
          h += '<td><select' + a + lab + '>' + f.choices.map(function (c) {
            return '<option value="' + esc(c.value) + '"' + (c.value === v ? ' selected' : '') + '>' + esc(c.label) + '</option>';
          }).join('') + '</select></td>';
        } else if (f.kind === 'numbers') {
          h += '<td><input type="text"' + a + lab + ' data-fkind="numbers" value="' + esc(Array.isArray(v) ? v.join(', ') : '') + '"></td>';
        } else if (f.kind === 'text') {
          h += '<td><input type="text"' + a + lab + ' data-fkind="text" value="' + esc(v === null || v === undefined ? '' : v) + '"></td>';
        } else {
          h += '<td><input type="number" step="any"' + a + lab + ' data-fkind="number" value="' + (isNum(v) ? esc(v) : '') + '"></td>';
        }
      });
      if (q.id === 'route') {
        h += '<td><button type="button" class="btn link" data-route-use="' + i + '">Use as the pass</button></td>';
      }
      h += '<td><button type="button" class="btn" data-list-del="' + q.id + '" data-row="' + i + '" aria-label="Remove entry ' + (i + 1) + '">Remove</button></td></tr>';
    });
    h += '</tbody></table></div><button type="button" class="btn" data-list-add="' + q.id + '">Add ' +
      (q.id === 'route' ? 'a pass' : q.id === 'pitch_observations' ? 'a measurement' : 'an entry') + '</button>';
    if (!rows.length) { h += ' <span class="small soft">Nothing entered: counts as "Don\'t know".</span>'; }
    return h;
  }

  function renderQ(q, ctx) {
    ctx = ctx || FORM;
    return '<div class="q" id="' + ctx.prefix + '-q-' + q.id + '" data-q="' + q.id + '">' +
      '<label class="w" for="' + ctx.prefix + '-in-' + q.id + '">' + esc(q.wording) +
      (q.ask_first ? '' : '') + '</label>' +
      '<p class="help" id="' + ctx.prefix + '-h-' + q.id + '">' + esc(q.help) + '</p>' +
      (ctx.prefix === 'f' ? '<div class="notice-slot" data-notice="' + q.id + '">' + noticeHtml(q.id) + '</div>' : '') +
      widget(q, ctx) + typicalLine(q, ctx) + originMark(q, ctx) +
      '<div class="err" role="alert">' + esc(S.errors[q.id] || '') + '</div></div>';
  }

  function parseNums(text) {
    var t = String(text).trim();
    if (!t) { return null; }
    var parts = t.split(/[,;\s]+/).filter(Boolean).map(Number);
    return parts.every(isFinite) ? parts : undefined;
  }
