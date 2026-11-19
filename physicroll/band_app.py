"""Local, guided web interface for band screening ("band app", SPEC16 Part 2).

    python -m physicroll.band_app --runs-dir my_runs          # opens the browser
    python -m physicroll.band_app --runs-dir my_runs --no-browser --port 8765

A loopback-only server (standard library only) in the spirit of ``physicroll.editor``: it binds
127.0.0.1, refuses any request whose Host is not ``127.0.0.1:<port>`` or ``localhost:<port>``,
embeds a random session token in the page and requires it (header ``X-Band-App-Token``) on
every POST and every ``/api/`` call, limits request bodies, accepts JSON only, and never uses
anything the client sends as a file path: runs are addressed by server-generated ids matching
``[0-9a-f]{32}``, and an opened case file is parsed as JSON, validated by the engine's own
validator and never written under a client-chosen name.

The engine (``physicroll.band_diagnosis.diagnose``) runs in ONE worker thread fed by a queue
(it is CPU-bound; one run at a time), so the page stays responsive and polls
``GET /api/runs/<id>``. A run can be cancelled only while it is queued. Each run is stored
under ``--runs-dir/<id>/`` as ``answers.json``, ``case.json``, ``result.json``,
``report.html``, ``summary.json`` and ``meta.json``. At start the server lists the runs already
in that directory and skips unreadable ones; a run left queued or running by an earlier session
is marked as interrupted.

Routes (all JSON unless stated):
  GET  /                         the page (HTML)            GET /app.js, /app.css
  GET  /api/meta                 questions, starting points, products, units, profiles, engine
  POST /api/case/check           answers -> case, the drawing model and plain validation messages
  POST /api/case/edit            one nozzle edit (answers + edit) -> the check answer for the
                                 edited answers, with the new nozzle marks as the answers patch
  POST /api/case/open            an opened case file -> answers (validated by the engine)
  POST /api/product-defaults     literature starter values for one product and gauge
  POST /api/runs                 start a run -> {id}
  GET  /api/runs                 the list for the "previous runs" drawer
  GET  /api/runs/<id>            status, elapsed seconds, and the plain summary when done
  GET  /api/runs/<id>/{answers.json,case.json,result.json,report.html}
  GET  /api/runs/<id>/reopen     starting point and answers to change this run's inputs
                                 (a named starting point, or {"run": id}: the run's own case)
  POST /api/runs/<id>/variant    a what-if: the base run's case with a few changed answers
  POST /api/runs/<id>/cancel     cancel a queued run
  POST /api/runs/<id>/rerun      the same inputs again (e.g. in detail after a quick run)

Status: every result is ``SCREENING_RESULT_NOT_PLANT_VALIDATED``; the page says so on every
screen that shows a ranking. Nothing here adds physics.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import re
import secrets
import signal
import sys
import threading
import time
import traceback
from urllib.parse import urlsplit
from uuid import uuid4
import webbrowser

from . import band_diagnosis as bd
from . import band_plain as bpl
from . import band_products as bprod
from .__main__ import _save_complete
from .band_app_assets import APP_CSS, APP_JS, page_html
from .band_report import render_band_report

RUN_ID = re.compile(r'[0-9a-f]{32}\Z')
MAX_BODY_BYTES = 1024 * 1024
WRITE_RETRIES = 6
DRAIN_LIMIT_BYTES = 4 * MAX_BODY_BYTES   # an oversized body up to this size is read and dropped
DRAIN_CHUNK_BYTES = 64 * 1024
SOCKET_TIMEOUT_S = 30                    # no request can hang a handler thread for longer
TOKEN_HEADER = 'X-Band-App-Token'
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
REPORT_CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; "
              "form-action 'none'; frame-ancestors 'none'")
RUN_FILES = {'answers.json': 'application/json', 'case.json': 'application/json',
             'result.json': 'application/json', 'report.html': 'text/html'}
STATUSES = ('queued', 'running', 'done', 'failed', 'cancelled', 'interrupted')
SCENARIOS_DIR = Path(__file__).resolve().parent.parent / 'scenarios'
RUN_UNREADABLE_TEXT = ('The earlier run this one was built on can no longer be read (its '
                       'folder is missing or damaged). Choose another starting point.')
INTERNAL_ERROR_TEXT = ('The screening stopped with an internal error. Your answers are kept; '
                       'try the quick profile, or check the values you changed last. The '
                       'details are in the window where the app was started.')
SUMMARY_ERROR_TEXT = ('The screening ran, but the visual summary could not be built. The '
                      'engine result and the full engineering report are saved: open the report '
                      'or download the result below. The details are in the window where the '
                      'app was started.')
STAGES = ('Checking the inputs', 'Roll gap and stand vibration (chatter)',
          'Roll temperature across the width and strip flatness', 'Scoring the twenty causes',
          'Writing the report')


def engine_version():
    try:
        from importlib.metadata import version
        pkg = version('physicroll')
    except Exception:                                   # source checkout without metadata
        pkg = 'source checkout'
    return {'package': pkg, 'case_schema': bd.CASE_SCHEMA_V2, 'status': bd.STATUS,
            'plain_schema': bpl.SCHEMA}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _dump(obj):
    return json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n'


def load_worked_examples(directory=SCENARIOS_DIR):
    """The demo scenarios of a source checkout ({example id: case}); {} in a wheel install."""
    out = {}
    for pid, filename, _, _ in bpl.WORKED_EXAMPLES:
        path = Path(directory) / filename
        try:
            out[pid] = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
    return out


class RequestError(Exception):
    """An error with an HTTP status and a plain message for the page."""

    def __init__(self, status, text, question=None, step=None, extra=None):
        super().__init__(text)
        self.status, self.text, self.question, self.step = status, text, question, step
        self.extra = extra or {}

    def body(self):
        return dict({'error': {'text': self.text, 'question': self.question,
                               'step': self.step}}, **self.extra)


class RunStore:
    """Runs on disk plus the one-worker queue that executes them."""

    def __init__(self, root, worked_examples=None, engine=None, quiet=False, summarise=None):
        self.quiet = quiet
        self.summarise = summarise or bpl.plain_summary
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.runs = {}
        self.skipped = 0
        self.queue = queue.Queue()
        self.engine = engine or bd.diagnose
        self.presets = {p['id']: p for p in bpl.presets(
            load_worked_examples() if worked_examples is None else worked_examples)}
        self._load()
        self.stopping = threading.Event()
        self.worker = threading.Thread(target=self._work, name='band-app-worker', daemon=True)
        self.worker.start()

    # ------------------------------------------------------------------ disk
    def _folder(self, run_id):
        if not isinstance(run_id, str) or RUN_ID.fullmatch(run_id) is None:
            raise RequestError(404, 'There is no run with this id.')
        folder = self.root / run_id
        if folder.parent != self.root:
            raise RequestError(404, 'There is no run with this id.')
        return folder

    def _load(self):
        for item in sorted(self.root.iterdir()):
            if not item.is_dir() or RUN_ID.fullmatch(item.name) is None:
                continue
            try:
                meta = json.loads((item / 'meta.json').read_text(encoding='utf-8'))
                if not isinstance(meta, dict) or meta.get('id') != item.name:
                    raise ValueError('meta.json does not belong to this folder')
            except (OSError, ValueError):
                self.skipped += 1
                continue
            if meta.get('status') in ('queued', 'running'):
                meta['status'] = 'interrupted'
                meta['error'] = {'text': 'This run was interrupted: the app was closed before '
                                         'it finished. Start it again.', 'question': None,
                                 'step': None}
                try:
                    _save_complete(item / 'meta.json', _dump(meta))
                except OSError:
                    pass
            self.runs[item.name] = meta

    def log_exception(self):
        if not self.quiet:
            traceback.print_exc(file=sys.stderr)

    def _write(self, run_id, name, content):
        # On Windows a file being read at that moment (or held by a virus scanner) can make the
        # atomic replace fail briefly with PermissionError: retry a few times.
        for attempt in range(WRITE_RETRIES):
            try:
                _save_complete(self.root / run_id / name, content)
                return
            except PermissionError:
                if attempt == WRITE_RETRIES - 1:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _save_meta(self, meta):
        self._write(meta['id'], 'meta.json', _dump(meta))

    # ------------------------------------------------------------------ inputs
    def run_preset(self, run_id):
        """An earlier run's stored case as a starting point (variants, updates, reruns and
        runs from an opened case file are reopened on their own case, never on another mill)."""
        if not isinstance(run_id, str) or RUN_ID.fullmatch(run_id) is None:
            raise RequestError(400, RUN_UNREADABLE_TEXT, 'preset', 'mill')
        with self.lock:
            meta = copy.deepcopy(self.runs.get(run_id))
        try:
            case = json.loads((self._folder(run_id) / 'case.json').read_text(encoding='utf-8'))
            bd.validate_case(case)
        except (OSError, ValueError, TypeError, KeyError, RequestError):
            raise RequestError(409, RUN_UNREADABLE_TEXT, 'preset', 'mill')
        from_file = bool(meta) and meta.get('preset') == 'case_file'
        name = case.get('name') or 'unnamed'
        label = (f'the case file you opened ("{name}")' if from_file
                 else f'the earlier run "{name}"')
        return {'id': f'run_{run_id}', 'ref': {'run': run_id}, 'label': label,
                'description': ('The case of an earlier run, as it was run. Values you do not '
                                'change stay as they were in that run.'),
                'kind': 'run', 'generated_by_model': False, 'case': case}

    def preset(self, body):
        pid = body.get('preset')
        if isinstance(pid, dict):
            return self.run_preset(pid.get('run'))
        if pid == 'case_file':
            case = body.get('case_file')
            if not isinstance(case, dict):
                raise RequestError(400, 'Open a case file first, or choose another starting '
                                        'point.', 'preset', 'mill')
            try:
                return bpl.file_preset(case)
            except (ValueError, TypeError, KeyError) as exc:
                err = bpl.plain_error(exc)
                raise RequestError(400, 'The case file is not accepted: ' + err['text'],
                                   err['question'], err['step'])
        if pid not in self.presets:
            raise RequestError(400, 'Choose a starting point (a typical mill, a worked example '
                                    'or a case file).', 'preset', 'mill')
        return self.presets[pid]

    @staticmethod
    def reconcile(answers, preset):
        """(answers, notices, patch): dependent answers checked before validation
        (``band_plain.reconcile_answers``); ``patch`` = {question id: new value} of the answers
        that were reset, for the page to apply."""
        try:
            fixed, notices = bpl.reconcile_answers(answers, preset)
        except (ValueError, TypeError, KeyError):
            return answers, [], {}
        return fixed, notices, _answers_patch(answers, fixed)

    @classmethod
    def check(cls, answers, preset, edit=None):
        """The /api/case/check and /api/case/edit answer: the built case, the drawing model
        computed from it (``band_plain.drawing_model``) with its key, the reconciliation
        notices and the answers patch the page applies (an edit's new nozzle marks included)."""
        new = answers
        if edit is not None:
            fixed, _, _ = cls.reconcile(answers, preset)
            try:
                new = bpl.apply_nozzle_edit(fixed, preset, edit)
            except (ValueError, TypeError, KeyError) as exc:
                err = bpl.plain_error(exc)
                raise RequestError(400, err['text'], err['question'], err['step'])
        case, notices, patch = cls.build_case(new, preset)
        model, key = _drawing(case, preset)
        return {'ok': True, 'case': case, 'origins': bpl.value_origins(case), 'model': model,
                'model_key': key, 'reconciled': notices,
                'answers_patch': _answers_patch(answers, _patched(new, patch))}

    @classmethod
    def build_case(cls, answers, preset, for_run=False):
        """(case, notices, patch). For a run, a pending reset is refused (409) with the
        notices, so a run never starts from answers the person has not seen."""
        fixed, notices, patch = cls.reconcile(answers, preset)
        if for_run and any(n['kind'] == 'reset' for n in notices):
            first = next(n for n in notices if n['kind'] == 'reset')
            raise RequestError(409, first['text'] + ' Check the redrawn spray header, then '
                                    'run again.', first['question'],
                               bpl.QUESTION_BY_ID[first['question']].step,
                               extra={'reconciled': notices, 'answers_patch': patch})
        try:
            return bpl.case_from_answers(fixed, preset), notices, patch
        except (ValueError, TypeError, KeyError) as exc:
            err = bpl.plain_error(exc)
            raise RequestError(400, err['text'], err['question'], err['step'],
                               extra={'reconciled': notices, 'answers_patch': patch})

    # ------------------------------------------------------------------ runs
    def submit(self, case, answers, preset, profile, base_run_id=None, changes=None):
        if profile not in bpl.PROFILES:
            raise RequestError(400, 'Choose the quick or the detailed run.')
        run_id = uuid4().hex
        meta = {'id': run_id, 'created': _now(), 'base_run_id': base_run_id,
                'status': 'queued', 'profile': profile,
                'profile_label': bpl.PROFILES[profile]['label'],
                'engine': engine_version(), 'elapsed_s': None, 'preset': preset['id'],
                'preset_label': preset['label'], 'name': case['name'],
                'product': case['material'].get('product'),
                'exit_thickness_m': case['pass']['exit_thickness_m'],
                'orientation': case['observation']['orientation'],
                'synthetic': case['synthetic'], 'changes': changes or [],
                'leaders': [], 'trust': None, 'error': None}
        (self.root / run_id).mkdir()
        self._write(run_id, 'answers.json', _dump({'preset': preset['id'],
                                                   'preset_ref': preset.get('ref'),
                                                   'profile': profile,
                                                   'answers': answers,
                                                   'base_run_id': base_run_id,
                                                   'changes': changes or []}))
        self._write(run_id, 'case.json', _dump(case))
        with self.lock:
            self.runs[run_id] = meta
            self._save_meta(meta)
        self.queue.put(run_id)
        return run_id

    def cancel(self, run_id):
        self._folder(run_id)
        with self.lock:
            meta = self.runs.get(run_id)
            if meta is None:
                raise RequestError(404, 'There is no run with this id.')
            if meta['status'] != 'queued':
                raise RequestError(409, 'Only a run that is still waiting can be cancelled.')
            meta['status'] = 'cancelled'
            self._save_meta(meta)
        return meta

    def get(self, run_id):
        self._folder(run_id)
        with self.lock:
            meta = self.runs.get(run_id)
            if meta is None:
                raise RequestError(404, 'There is no run with this id.')
            meta = copy.deepcopy(meta)
        if meta['status'] == 'running' and meta.get('started_monotonic') is not None:
            meta['elapsed_s'] = round(time.monotonic() - meta['started_monotonic'], 1)
        meta.pop('started_monotonic', None)
        return meta

    def read_json(self, run_id, name):
        try:
            return json.loads((self._folder(run_id) / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise RequestError(404, 'This file is not available for this run.')

    def list(self):
        with self.lock:
            metas = [copy.deepcopy(m) for m in self.runs.values()]
        for m in metas:
            m.pop('started_monotonic', None)
        metas.sort(key=lambda m: m.get('created') or '', reverse=True)
        return metas

    def queue_position(self, run_id):
        with self.lock:
            waiting = sorted((m['created'], i) for i, m in self.runs.items()
                             if m['status'] == 'queued')
        ids = [i for _, i in waiting]
        return ids.index(run_id) + 1 if run_id in ids else None

    # ------------------------------------------------------------------ worker
    def _work(self):
        while not self.stopping.is_set():
            try:
                run_id = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._run(run_id)
            except Exception:                         # the queue must survive anything
                self.log_exception()
                self._fail(run_id, {'text': INTERNAL_ERROR_TEXT, 'question': None,
                                    'step': None})
            finally:
                self.queue.task_done()

    def _fail(self, run_id, error):
        with self.lock:
            meta = self.runs.get(run_id)
            if meta is None:
                return
            if meta.get('started_monotonic') is not None:
                meta['elapsed_s'] = round(time.monotonic() - meta.pop('started_monotonic'), 1)
            meta['status'] = 'failed'
            meta['error'] = error
            try:
                self._save_meta(meta)
            except OSError:
                pass

    def _run(self, run_id):
        with self.lock:
            meta = self.runs.get(run_id)
            if meta is None or meta['status'] != 'queued':
                return
            meta['status'] = 'running'
            meta['started'] = _now()
            meta['started_monotonic'] = time.monotonic()
            self._save_meta({k: v for k, v in meta.items() if k != 'started_monotonic'})
        case = self.read_json(run_id, 'case.json')
        engine_case, left_out = bpl.apply_profile(case, meta['profile'])
        try:
            result = self.engine(engine_case)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            self.log_exception()
            err = bpl.plain_error(exc)
            self._fail(run_id, {'text': 'The screening could not be run on these inputs. '
                                        + err['text'], 'question': err['question'],
                                'step': err['step']})
            return
        # the engine result and the engineering report are kept whatever happens next
        self._write(run_id, 'result.json', bd.result_json(result))
        report_ok = True
        try:
            self._write(run_id, 'report.html', render_band_report(result))
        except Exception:                             # keep the result; say so on the page
            self.log_exception()
            report_ok = False
        summary, summary_error = None, None
        try:
            summary = self.summarise(result, case, bpl.value_origins(case),
                                     own_mill=not case['synthetic'])
            summary['profile'] = {'id': meta['profile'], 'label': meta['profile_label'],
                                  'left_out': left_out,
                                  'description': bpl.PROFILES[meta['profile']]['description']}
            base = meta.get('base_run_id')
            if base:
                try:
                    old = self.read_json(base, 'summary.json')
                    summary['compared_with_base'] = dict(bpl.compare_summaries(old, summary),
                                                         base_run_id=base)
                except RequestError:
                    summary['compared_with_base'] = None
            self._write(run_id, 'summary.json', _dump(summary))
        except Exception:                             # traceback to the console only
            self.log_exception()
            summary = None
            summary_error = SUMMARY_ERROR_TEXT
        with self.lock:
            meta['elapsed_s'] = round(time.monotonic() - meta.pop('started_monotonic'), 1)
            meta['status'] = 'done'
            meta['finished'] = _now()
            meta['summary_error'] = summary_error
            meta['report_available'] = report_ok
            if summary is not None:
                meta['leaders'] = [{'id': c['id'], 'name': c['name']}
                                   for c in summary['causes'] if c['leading']]
                meta['trust'] = summary['trust']['level']
                meta['headline'] = summary['headline']['text']
            else:
                meta['leaders'] = [{'id': h, 'name': bpl.CAUSES.get(h, (h,))[0]}
                                   for h in result.get('leading_hypotheses') or []]
            self._save_meta(meta)

    def stop(self):
        self.stopping.set()
        self.worker.join(timeout=5)


# ============================================================================= meta for the page
def _products():
    groups = {}
    for p in bprod.products():
        groups.setdefault(p.family, []).append({'id': p.id, 'name': p.name,
                                                'family': p.family})
    return [{'family': fam, 'label': dict(bpl.QUESTION_BY_ID['product'].choices)[
        items[0]['id']].split(':')[0], 'products': items} for fam, items in groups.items()]


def _drawing(case, preset):
    """(drawing model, key): what the page draws for a built case and a short key of its
    canonical JSON, so the page can redraw whenever the model differs from the one drawn."""
    model = bpl.drawing_model(case, preset.get('label'))
    canon = json.dumps(model, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return model, hashlib.sha256(canon.encode()).hexdigest()[:20]


def _answers_patch(before, after):
    """{question id: new value} for every answer that differs between two answer sets."""
    a = (before or {}).get('values') or {} if isinstance(before, dict) else {}
    b = (after or {}).get('values') or {} if isinstance(after, dict) else {}
    return {k: b.get(k) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


def _patched(answers, patch):
    out = copy.deepcopy(answers) if isinstance(answers, dict) else {}
    out.setdefault('values', {}).update(patch)
    return out


def _preset_info(p):
    case = p['case']
    out = {'id': p['id'], 'label': p['label'], 'description': p['description'],
           'kind': p['kind'], 'generated_by_model': p['generated_by_model'],
           'answers': bpl.answers_from_case(case)}
    out['model'], out['model_key'] = _drawing(case, p)
    return out


def page_meta(store):
    return {'engine': engine_version(), 'steps': [{'id': i, 'label': lab}
                                                  for i, lab in bpl.STEPS],
            'questions': bpl.questions(), 'units': {k: v[0] for k, v in bpl.UNITS.items()},
            'presets': [_preset_info(p) for p in store.presets.values()],
            'worked_examples_available': any(p['kind'] == 'example'
                                             for p in store.presets.values()),
            'products': _products(), 'profiles': bpl.PROFILES, 'stages': list(STAGES),
            'causes': {k: {'name': v[0], 'description': v[1], 'pictogram': v[2]}
                       for k, v in bpl.CAUSES.items()},
            'glossary': bpl.GLOSSARY, 'standing_words': bpl.STANDING_WORDS,
            'sections': list(bpl.SECTIONS),
            'weak_nozzle_level': bpl.WEAK_NOZZLE_LEVEL,
            'trust_rule': bpl.TRUST_RULE, 'limitations': list(bpl.STANDING_LIMITATIONS),
            'status_words': 'Screening result from a model that has not been compared with '
                            'plant data: a shortlist of causes that fit, not a finding.'}


# ============================================================================= server
def make_server(runs_dir, port=0, worked_examples=None, engine=None, quiet=False,
                summarise=None):
    """Create the server (bound to 127.0.0.1). The caller owns serve_forever / shutdown /
    server_close; ``server.store.stop()`` stops the worker."""
    store = RunStore(runs_dir, worked_examples, engine, quiet, summarise)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'band-app'
        sys_version = ''
        timeout = SOCKET_TIMEOUT_S         # socket timeout for every read (StreamRequestHandler)

        def log_message(self, fmt, *args):            # quiet console; errors still print
            pass

        # -------------------------------------------------------------- helpers
        def _authority_ok(self):
            port_ = self.server.server_port
            hosts = self.headers.get_all('Host', [])
            allowed = {f'127.0.0.1:{port_}', f'localhost:{port_}'}
            if len(hosts) != 1 or hosts[0] not in allowed:
                return False
            origins = self.headers.get_all('Origin', [])
            if len(origins) > 1:
                return False
            if origins and origins[0] not in {'http://' + a for a in allowed}:
                return False
            return True

        def _token_ok(self):
            got = self.headers.get_all(TOKEN_HEADER, [])
            return len(got) == 1 and secrets.compare_digest(got[0].encode(), token.encode())

        def _send(self, status, body, ctype, csp=CSP, extra=None):
            data = body if isinstance(body, bytes) else body.encode('utf-8')
            try:
                self.send_response(status)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Content-Security-Policy', csp)
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Frame-Options', 'DENY')
                if self.close_connection:
                    self.send_header('Connection', 'close')
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass                                    # the client went away: nothing to do

        def _json(self, status, obj):
            self._send(status, json.dumps(obj, allow_nan=False), 'application/json')

        def _error(self, exc):
            self._json(exc.status, exc.body())

        def _read_body(self):
            """Read the request body BEFORE any check that may refuse the request, so the
            client is never answered while it is still sending (which it would see as a reset
            connection instead of the message). Returns (raw bytes, None) or (None, error).
            An oversized body up to DRAIN_LIMIT_BYTES is read and dropped; a larger one, a body
            without a length or one shorter than declared ends the connection after the reply
            (the socket timeout bounds the wait)."""
            if self.headers.get('Transfer-Encoding'):
                self.close_connection = True
                return None, RequestError(411, 'Send the request with a length.')
            text = self.headers.get('Content-Length')
            if text is None:
                return b'', None                      # no body (a GET-like POST)
            try:
                length = int(text)
            except ValueError:
                self.close_connection = True
                return None, RequestError(411, 'Send the request with a length.')
            if length < 0:
                self.close_connection = True
                return None, RequestError(411, 'Send the request with a length.')
            too_large = RequestError(413, 'The request is too large (more than 1 MiB). A case '
                                          'file is normally far smaller: check that you chose '
                                          'a band case file.')
            if length > MAX_BODY_BYTES:
                self.close_connection = True
                if length <= DRAIN_LIMIT_BYTES:
                    left = length
                    try:
                        while left > 0:
                            chunk = self.rfile.read(min(DRAIN_CHUNK_BYTES, left))
                            if not chunk:
                                break
                            left -= len(chunk)
                    except OSError:                   # timeout or reset: reply anyway
                        pass
                return None, too_large
            try:
                raw = self.rfile.read(length)
            except OSError:
                self.close_connection = True
                return None, RequestError(400, 'The request arrived incomplete. Try again.')
            if len(raw) < length:
                self.close_connection = True
                return None, RequestError(400, 'The request arrived incomplete. Try again.')
            return raw, None

        def _body(self, raw):
            ctype = self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
            if ctype != 'application/json':
                raise RequestError(415, 'The app only accepts JSON.')
            try:
                data = json.loads(raw.decode('utf-8'))
            except (UnicodeDecodeError, ValueError):
                raise RequestError(400, 'The request is not valid JSON.')
            if not isinstance(data, dict):
                raise RequestError(400, 'The request must be a JSON object.')
            return data

        def _route(self):
            parts = [p for p in urlsplit(self.path).path.split('/') if p]
            return parts

        # -------------------------------------------------------------- GET
        def do_GET(self):
            if not self._authority_ok():
                self._json(403, {'error': {'text': 'Request refused: wrong host or origin.'}})
                return
            parts = self._route()
            try:
                if parts == []:
                    self._send(200, page_html(token), 'text/html; charset=utf-8')
                    return
                if parts == ['app.js']:
                    self._send(200, APP_JS, 'text/javascript; charset=utf-8')
                    return
                if parts == ['app.css']:
                    self._send(200, APP_CSS, 'text/css; charset=utf-8')
                    return
                if not parts or parts[0] != 'api':
                    raise RequestError(404, 'Unknown page.')
                if not self._token_ok():
                    raise RequestError(403, 'Request refused: missing or wrong session token. '
                                            'Reload the page.')
                if parts == ['api', 'meta']:
                    self._json(200, page_meta(store))
                elif parts == ['api', 'runs']:
                    self._json(200, {'runs': store.list(), 'skipped_unreadable': store.skipped})
                elif len(parts) == 3 and parts[1] == 'runs':
                    self._json(200, self._status(parts[2]))
                elif len(parts) == 4 and parts[1] == 'runs' and parts[3] == 'reopen':
                    self._json(200, self._reopen(parts[2]))
                elif len(parts) == 4 and parts[1] == 'runs' and parts[3] in RUN_FILES:
                    folder = store._folder(parts[2])
                    try:
                        data = (folder / parts[3]).read_bytes()
                    except OSError:
                        raise RequestError(404, 'This file is not available for this run '
                                                '(it may still be running).')
                    ctype = RUN_FILES[parts[3]]
                    if ctype == 'text/html':
                        self._send(200, data, 'text/html; charset=utf-8', csp=REPORT_CSP)
                    else:
                        self._send(200, data, ctype + '; charset=utf-8', extra={
                            'Content-Disposition': f'attachment; filename="{parts[3]}"'})
                else:
                    raise RequestError(404, 'Unknown request.')
            except RequestError as exc:
                self._error(exc)
            except Exception:
                store.log_exception()
                self._json(500, {'error': {'text': INTERNAL_ERROR_TEXT}})

        def _status(self, run_id):
            meta = store.get(run_id)
            out = {'run': meta, 'queue_position': store.queue_position(run_id)}
            if meta['status'] == 'done' and not meta.get('summary_error'):
                out['summary'] = store.read_json(run_id, 'summary.json')
            return out

        # -------------------------------------------------------------- POST
        def do_POST(self):
            raw, early = self._read_body()            # first, so no refusal races the client
            if not self._authority_ok():
                self._json(403, {'error': {'text': 'Request refused: wrong host or origin.'}})
                return
            parts = self._route()
            try:
                if early is not None:
                    raise early
                if not self._token_ok():
                    raise RequestError(403, 'Request refused: missing or wrong session token. '
                                            'Reload the page.')
                if len(parts) < 2 or parts[0] != 'api':
                    raise RequestError(404, 'Unknown request.')
                body = self._body(raw)
                if parts == ['api', 'case', 'check']:
                    self._json(200, store.check(body.get('answers'), store.preset(body)))
                elif parts == ['api', 'case', 'edit']:
                    edit = body.get('edit')
                    if not isinstance(edit, dict):
                        raise RequestError(400, 'Unknown nozzle change.', 'nozzle_levels',
                                           'mill')
                    self._json(200, store.check(body.get('answers'), store.preset(body), edit))
                elif parts == ['api', 'case', 'open']:
                    preset = store.preset(dict(body, preset='case_file'))
                    self._json(200, {'ok': True, 'answers': bpl.answers_from_case(
                        preset['case']), 'preset': _preset_info(preset)})
                elif parts == ['api', 'product-defaults']:
                    self._json(200, self._product_defaults(body))
                elif parts == ['api', 'runs']:
                    preset = store.preset(body)
                    answers = body.get('answers')
                    case, _, patch = store.build_case(answers, preset, for_run=True)
                    run_id = store.submit(case, _patched(answers, patch), preset,
                                          body.get('profile', 'quick'))
                    self._json(202, {'id': run_id})
                elif len(parts) == 4 and parts[1] == 'runs' and parts[3] == 'variant':
                    self._json(202, {'id': self._variant(parts[2], body)})
                elif len(parts) == 4 and parts[1] == 'runs' and parts[3] == 'cancel':
                    self._json(200, {'run': store.cancel(parts[2])})
                elif len(parts) == 4 and parts[1] == 'runs' and parts[3] == 'rerun':
                    self._json(202, {'id': self._rerun(parts[2], body)})
                else:
                    raise RequestError(404, 'Unknown request.')
            except RequestError as exc:
                self._error(exc)
            except Exception:
                store.log_exception()
                self._json(500, {'error': {'text': INTERNAL_ERROR_TEXT}})

        def _product_defaults(self, body):
            pid = body.get('product')
            if pid not in bprod.product_ids():
                raise RequestError(400, 'Choose a product from the list.', 'product', 'rolling')
            gauges = {}
            for k, qid in (('exit_thickness_m', 'exit_gauge'),
                           ('entry_thickness_m', 'entry_gauge')):
                v = body.get(k)
                if v is not None:
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
                        raise RequestError(400, 'The gauge must be a positive number.', qid,
                                           'rolling')
                    gauges[k] = float(v)
            try:
                return bpl.product_defaults(pid, **gauges)
            except (ValueError, TypeError, KeyError) as exc:
                raise RequestError(400, 'No literature values for this product and gauge: '
                                        + bpl.words(str(exc)), 'exit_gauge', 'rolling')

        def _reopen(self, run_id):
            """What "Change the answers" needs for run R: R's own starting point (a named one
            with R's answers, or else R's stored case with answers that reproduce it)."""
            meta = store.get(run_id)
            pid = meta.get('preset')
            if pid in store.presets:
                stored = store.read_json(run_id, 'answers.json')
                return {'preset': pid, 'preset_info': None, 'answers': stored.get('answers'),
                        'profile': meta.get('profile')}
            preset = store.run_preset(run_id)
            info = _preset_info(preset)
            info['ref'] = preset['ref']
            return {'preset': preset['ref'], 'preset_info': info,
                    'answers': bpl.answers_from_case(preset['case']),
                    'profile': meta.get('profile')}

        def _rerun(self, run_id, body):
            meta = store.get(run_id)
            profile = body.get('profile', 'detailed')
            preset = store.run_preset(run_id)
            case = preset['case']
            stored = store.read_json(run_id, 'answers.json')
            preset = dict(preset, id=meta.get('preset') or preset['id'],
                          label=meta.get('preset_label') or preset['label'])
            label = (bpl.PROFILES[profile]['label'] + ' run' if profile in bpl.PROFILES
                     else 'run again')
            base = run_id if meta['status'] == 'done' else None
            return store.submit(case, stored.get('answers'), preset, profile, base_run_id=base,
                                changes=[f'{label} of the same inputs'] if base else [])

        def _variant(self, base_id, body):
            meta = store.get(base_id)
            if meta['status'] != 'done':
                raise RequestError(409, 'The base run has not finished yet.')
            changes = body.get('changes')
            if not isinstance(changes, dict) or not changes:
                raise RequestError(400, 'Change at least one answer for the what-if.')
            origins = body.get('origins') or {}
            base_preset = store.run_preset(base_id)
            base_case = base_preset['case']
            answers = bpl.answers_from_case(base_case)
            answers['values'].update(changes)
            if not isinstance(origins, dict):
                raise RequestError(400, 'origins must be a JSON object.')
            for qid in changes:
                q = bpl.QUESTION_BY_ID.get(qid)
                if q is not None and q.origin_tracked:
                    answers['origins'][qid] = origins.get(qid, 'estimated')
            label = body.get('label')
            answers['name'] = (label if isinstance(label, str) and label.strip()
                               else f'{base_case["name"]} (what-if)')[:200]
            preset = base_preset
            case, _, patch = store.build_case(answers, preset, for_run=True)
            answers = _patched(answers, patch)
            words = [bpl.QUESTION_BY_ID[q].wording for q in changes if q in bpl.QUESTION_BY_ID]
            return store.submit(case, answers, preset, body.get('profile', meta['profile']),
                                base_run_id=base_id, changes=words)

        do_HEAD = do_GET

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.store = store
    server.token = token
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Guided band screening in your browser (local only; screening results '
                    'are not validated against plant data)')
    parser.add_argument('--runs-dir', type=Path, required=True,
                        help='folder where runs are kept (created if missing)')
    parser.add_argument('--port', type=int, default=0, help='port (default: a free port)')
    parser.add_argument('--no-browser', action='store_true',
                        help='do not open the browser, only print the address')
    args = parser.parse_args(argv)
    try:
        server = make_server(args.runs_dir, args.port)
    except OSError as exc:
        if args.port and getattr(exc, 'errno', None) in (48, 98, 10013, 10048):
            parser.error(f'port {args.port} is already in use (another band app may be running). '
                         'Start without --port to pick a free port, or choose another port.')
        parser.error(f'cannot start: {exc}')
    url = f'http://127.0.0.1:{server.server_port}/'
    print(f'Band app running at {url}  (this computer only; press Ctrl-C to stop)', flush=True)
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:                               # no browser: the address is printed
            pass

    def _stop(signum, frame):                        # a closed window / kill: stop cleanly too
        raise KeyboardInterrupt
    sigterm = getattr(signal, 'SIGTERM', None)
    if sigterm is not None and threading.current_thread() is threading.main_thread():
        try:
            signal.signal(sigterm, _stop)
        except (ValueError, OSError, RuntimeError):    # e.g. an embedded interpreter
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping the band app.', flush=True)
    finally:
        server.server_close()
        server.store.stop()


if __name__ == '__main__':
    main()
