"""Loopback-only guided editor for checked synthetic runs and saved bundles."""

import argparse
import hashlib
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
from urllib.parse import parse_qs, quote, urlsplit
from uuid import uuid4

from .model import Scenario
from .resources import read_example
from .run_bundle import create_run_bundle, verify_run_bundle
from .run_contract import RunSpec, canonical_json
from .workflows import run_workflow


TEMPLATES = {
    'checked_pass': ('v1_checked_pass.runspec.json', 'Guided synthetic checked pass'),
    'schedule_search': ('v1_schedule_search.runspec.json', 'Finite schedule search'),
    'benchmark': ('v1_shao_benchmark.runspec.json', 'Frozen conditional benchmark'),
    'sensitivity': ('v1_shao_sensitivity.runspec.json', 'Declared prior sensitivity'),
    'operating_replay': ('v1_operating_replay.runspec.json', 'Offline phase replay'),
}
SCENARIO_FIELDS = (
    ('name', 'Scenario name'),
    ('entry_thickness_m', 'Entry thickness (m)'),
    ('exit_thickness_m', 'Prescribed exit thickness (m)'),
    ('width_m', 'Strip width (m)'),
    ('entry_speed_m_s', 'Prescribed entry speed (m/s)'),
    ('work_roll_radius_m', 'Work-roll radius (m)'),
    ('density_kg_m3', 'Density (kg/m³)'),
    ('mean_flow_stress_pa', 'Positive flow-stress guard (Pa); fixed synthetic hardening law controls predictions'),
    ('friction_coefficient', 'Friction coefficient'),
    ('entry_tension_pa', 'Entry tension stress (Pa)'),
    ('exit_tension_pa', 'Exit tension stress (Pa)'),
    ('drive_efficiency', 'Drive efficiency'),
    ('cells', 'Spatial cells'),
)
RUN_ID = re.compile(r'[0-9a-f]{32}\Z')
MAX_FORM_BYTES = 1024 * 1024


def _esc(value):
    return escape(str(value), quote=True)


def _template(kind):
    if kind not in TEMPLATES:
        raise ValueError('unknown editor template')
    return RunSpec(read_example(TEMPLATES[kind][0]))


def guided_values(spec):
    data = spec.to_dict()
    if data['workflow_kind'] != 'checked_pass':
        raise ValueError('guided form requires checked_pass')
    scenario = data['resolved_inputs']['checked_pass']['scenario']
    return {**{key: str(scenario[key]) for key, _ in SCENARIO_FIELDS if key != 'cells'},
            'cells': str(data['numerical_settings']['cells'])}


def build_guided_checked(base, values):
    """Copy one complete template, keeping requested/resolved values aligned."""
    if not isinstance(base, RunSpec):
        raise ValueError('guided editor requires a RunSpec')
    data = base.to_dict()
    if data['workflow_kind'] != 'checked_pass':
        raise ValueError('guided form requires checked_pass')
    scenario = data['resolved_inputs']['checked_pass']['scenario'].copy()
    for key, _ in SCENARIO_FIELDS:
        raw = values.get(key)
        if type(raw) is not str or not raw.strip():
            raise ValueError(f'{key} is required')
        if key == 'name':
            scenario[key] = raw.strip()
        elif key == 'cells':
            try:
                cells = int(raw)
            except ValueError as exc:
                raise ValueError('cells must be an integer') from exc
        else:
            try:
                scenario[key] = float(raw)
            except ValueError as exc:
                raise ValueError(f'{key} must be a number in SI units') from exc
    Scenario.from_dict(scenario)
    data['requested_inputs']['scenario'] = scenario.copy()
    data['resolved_inputs']['checked_pass']['scenario'] = scenario
    data['resolved_inputs']['checked_pass']['operating_plan']['pass_name'] = scenario['name']
    data['numerical_settings']['cells'] = cells
    data['resolved_inputs']['checked_pass']['cells'] = cells
    data['source_hashes']['editor/embedded-scenario'] = hashlib.sha256(
        canonical_json(scenario).encode('utf-8')).hexdigest()
    return RunSpec(data)


def _page(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_esc(title)}</title><style>'
        'body{font:16px/1.5 system-ui,sans-serif;max-width:70rem;margin:2rem auto;'
        'padding:0 1rem;color:#172033}label{display:block;margin:.8rem 0}'
        'input,textarea{display:block;width:100%;max-width:48rem;box-sizing:border-box;'
        'padding:.35rem;font:inherit}textarea{height:24rem;font-family:monospace}'
        'button{padding:.5rem 1rem;margin:.5rem .5rem .5rem 0}li{margin:.35rem 0}'
        '.error{border:2px solid #9b1c1c;padding:.8rem;color:#7b1717}'
        '.ok{border:2px solid #276348;padding:.8rem}'
        '</style></head><body><nav><a href="/">Saved runs and templates</a></nav>'
        f'<h1>{_esc(title)}</h1>{body}</body></html>\n'
    )


def _form(spec, token, *, values=None, raw_json=None, error=None, checked=None):
    data = spec.to_dict()
    guided = data['workflow_kind'] == 'checked_pass'
    intro = ('<p>All values are synthetic SI inputs. Exit thickness and entry speed are '
             'prescribed; this editor does not predict transient motion or plant readiness.</p>')
    if not guided:
        intro = ('<p>This workflow uses its versioned RunSpec JSON. Frozen benchmark '
                 'declarations must remain unchanged. Edit and check before saving.</p>')
    notice = f'<p class="error" role="alert">{_esc(error)}</p>' if error else ''
    if checked:
        status = ''.join(f'<li>{_esc(key)}: {_esc(value)}</li>'
                         for key, value in checked.to_dict(
                             include_runtime_metadata=False)['assessments'].items())
        notice += (f'<div class="ok"><strong>Check passed; no run saved.</strong> '
                   f'ResultBundle SHA-256: {_esc(checked.sha256)}<ul>{status}</ul></div>')
    fields = (f'<input type="hidden" name="csrf" value="{_esc(token)}">'
              f'<input type="hidden" name="mode" value="{ "guided" if guided else "json" }">')
    if guided:
        shown = guided_values(spec) if values is None else values
        fields += ('<input type="hidden" name="base_json" value="'
                   + _esc(spec.to_json()) + '">')
        for key, label in SCENARIO_FIELDS:
            field_type = 'text' if key == 'name' else 'number'
            step = '' if key == 'name' else ' step="1"' if key == 'cells' else ' step="any"'
            fields += (f'<label>{_esc(label)}<input name="{_esc(key)}" type="{field_type}"'
                       f'{step} required value="{_esc(shown.get(key, ""))}"></label>')
    else:
        source = json.dumps(data, ensure_ascii=False, indent=2) if raw_json is None else raw_json
        fields += f'<label>RunSpec JSON<textarea name="raw_json" required>{_esc(source)}</textarea></label>'
    buttons = ('<button type="submit" formaction="/check">Check inputs and execution</button>'
               '<button type="submit" formaction="/save">Save verified run</button>')
    return _page('Edit ' + data['workflow_kind'], intro + notice +
                 f'<form method="post" action="/check">{fields}{buttons}</form>')


def _invalid_json_form(raw_json, token, error):
    return _page('Correct RunSpec JSON',
                 f'<p class="error" role="alert">{_esc(error)}</p>'
                 '<form method="post" action="/check">'
                 f'<input type="hidden" name="csrf" value="{_esc(token)}">'
                 '<input type="hidden" name="mode" value="json">'
                 f'<label>RunSpec JSON<textarea name="raw_json" required>{_esc(raw_json)}</textarea></label>'
                 '<button type="submit" formaction="/check">Check inputs and execution</button>'
                 '<button type="submit" formaction="/save">Save verified run</button></form>')


def make_editor_server(runs_dir, port=0):
    """Create a local server; the caller owns serve_forever/shutdown/close."""
    root = Path(runs_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)

    class EditorHandler(BaseHTTPRequestHandler):
        def _allowed_authority(self, write=False):
            authority = f'127.0.0.1:{self.server.server_port}'
            hosts = self.headers.get_all('Host', [])
            origins = self.headers.get_all('Origin', [])
            return (hosts == [authority] and len(origins) <= 1 and
                    (not write or not origins or origins[0] == 'http://' + authority))

        def _send(self, body, status=200):
            content = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; style-src 'unsafe-inline'; "
                             "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)

        def _bundle(self, run_id):
            if RUN_ID.fullmatch(run_id) is None:
                raise ValueError('invalid saved-run identifier')
            folder = root / run_id
            return folder, *verify_run_bundle(folder)

        def do_GET(self):
            if not self._allowed_authority():
                self._send(_page('Forbidden', '<p>Invalid request authority.</p>'), 403)
                return
            path = urlsplit(self.path).path
            try:
                if path == '/':
                    choices = ''.join(
                        f'<li><a href="/new/{_esc(kind)}">{_esc(description)}</a></li>'
                        for kind, (_, description) in TEMPLATES.items())
                    runs = ''.join(
                        f'<li><a href="/run/{_esc(item.name)}">{_esc(item.name)}</a></li>'
                        for item in sorted(root.iterdir()) if RUN_ID.fullmatch(item.name))
                    self._send(_page('PhysicRollModel local editor',
                                     '<p>Select a synthetic template, check it, then save a run. '
                                     'Saved runs can be verified and reopened here.</p>'
                                     f'<h2>Templates</h2><ul>{choices}</ul>'
                                     f'<h2>Saved runs</h2><ul>{runs}</ul>'))
                elif path.startswith('/new/'):
                    self._send(_form(_template(path[5:]), token))
                elif path.startswith('/edit/'):
                    _, spec, _ = self._bundle(path[6:])
                    self._send(_form(spec, token))
                elif path.startswith('/run/'):
                    folder, spec, result = self._bundle(path[5:])
                    report_link = (f'<a href="/report/{_esc(folder.name)}">Open saved offline report</a>'
                                   if (folder / 'report.html').is_file() else
                                   'This older bundle has no saved HTML report.')
                    self._send(_page('Saved run ' + folder.name,
                                     f'<p>Verification passed. Workflow: {_esc(spec.to_dict()["workflow_kind"])}'
                                     f'<br>ResultBundle SHA-256: {_esc(result.sha256)}</p>'
                                     f'<p>{report_link}</p><p><a href="/edit/{_esc(folder.name)}">'
                                     'Reopen inputs as a new run</a></p>'))
                elif path.startswith('/report/'):
                    folder, _, _ = self._bundle(path[8:])
                    report = folder / 'report.html'
                    if not report.is_file():
                        raise ValueError('saved run has no HTML report')
                    self._send(report.read_text(encoding='utf-8'))
                else:
                    self._send(_page('Not found', '<p>Unknown page.</p>'), 404)
            except (ValueError, OSError) as exc:
                self._send(_page('Cannot open run', f'<p class="error">{_esc(exc)}</p>'), 400)

        def do_POST(self):
            if not self._allowed_authority(write=True):
                self._send(_page('Forbidden', '<p>Invalid request authority or origin.</p>'), 403)
                return
            path = urlsplit(self.path).path
            if path not in ('/check', '/save'):
                self._send(_page('Not found', '<p>Unknown action.</p>'), 404)
                return
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 <= length <= MAX_FORM_BYTES:
                    raise ValueError('form body size is invalid or exceeds 1 MiB')
                if self.headers.get('Content-Type', '').split(';', 1)[0] != 'application/x-www-form-urlencoded':
                    raise ValueError('expected an HTML form')
                parsed = parse_qs(self.rfile.read(length).decode('utf-8'),
                                  keep_blank_values=True, strict_parsing=True)
                if any(len(items) != 1 for items in parsed.values()):
                    raise ValueError('duplicate form fields')
                form = {key: items[0] for key, items in parsed.items()}
                if not secrets.compare_digest(form.get('csrf', ''), token):
                    self._send(_page('Forbidden', '<p>Invalid editor session token.</p>'), 403)
                    return
                mode = form.get('mode')
                if mode == 'guided':
                    base = RunSpec.from_json(form['base_json'])
                    spec = build_guided_checked(base, form)
                elif mode == 'json':
                    spec = RunSpec.from_json(form['raw_json'])
                else:
                    raise ValueError('unknown editor mode')
                if path == '/check':
                    result = run_workflow(spec)
                    self._send(_form(spec, token, checked=result))
                else:
                    run_id = uuid4().hex
                    create_run_bundle(spec, root / run_id)
                    self.send_response(303)
                    self.send_header('Location', '/run/' + quote(run_id))
                    self.send_header('Content-Length', '0')
                    self.end_headers()
            except (KeyError, ValueError, TypeError, OSError, UnicodeError) as exc:
                # Preserve the submitted form so the user can correct it.
                form = locals().get('form', {})
                if form.get('mode') == 'json' and 'raw_json' in form:
                    self._send(_invalid_json_form(form['raw_json'], token, str(exc)), 400)
                    return
                try:
                    base = (RunSpec.from_json(form['base_json'])
                            if form.get('mode') == 'guided' else
                            RunSpec.from_json(form['raw_json']))
                    self._send(_form(base, token, values=form,
                                     raw_json=form.get('raw_json'), error=str(exc)), 400)
                except (KeyError, ValueError, TypeError):
                    self._send(_page('Invalid run', f'<p class="error" role="alert">'
                                     f'{_esc(exc)}</p><p><a href="/">Start again</a></p>'), 400)

    return ThreadingHTTPServer(('127.0.0.1', port), EditorHandler)


def main():
    parser = argparse.ArgumentParser(description='Local synthetic scenario editor')
    parser.add_argument('--runs-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    server = make_editor_server(args.runs_dir, args.port)
    print(f'Open http://127.0.0.1:{server.server_port}/ on this computer', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
