"""Tests of the band app server (SPEC16 Part 2): loopback bind, request guards, headers, the
run queue, variants and the run store on disk.

Software verification of the local interface only; the screening it runs is not validated
against plant data.
"""
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock

from physicroll import band_app
from physicroll import band_diagnosis as bd
from physicroll import band_plain as bpl

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = band_app.load_worked_examples(ROOT / 'scenarios')
FAST_PRESET = 'example_bearing_order'     # the fastest demo: no width model, no route


class Client:
    def __init__(self, server, host=None):
        self.port = server.server_port
        self.token = server.token
        self.host = host or f'127.0.0.1:{self.port}'

    def request(self, method, path, body=None, *, token=True, headers=None, raw=None,
                ctype='application/json', pause_s=0.0):
        """One request on a fresh connection, always closed (also when it fails), so no
        socket is left for the garbage collector. ``pause_s`` waits between the headers and
        the body (a slow client: the server must not answer before reading the body)."""
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=120)
        try:
            return self._request(conn, method, path, body, token, headers, raw, ctype, pause_s)
        finally:
            conn.close()

    def _request(self, conn, method, path, body, token, headers, raw, ctype, pause_s):
        h = {'Host': self.host}
        if token:
            h[band_app.TOKEN_HEADER] = self.token if token is True else token
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        if data is not None:
            h['Content-Type'] = ctype
            h['Content-Length'] = str(len(data))
        h.update(headers or {})
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for k, v in h.items():
            conn.putheader(k, v)
        if pause_s:
            conn.endheaders()
            time.sleep(pause_s)
            if data is not None:
                conn.send(data)
        else:
            conn.endheaders(data)
        resp = conn.getresponse()
        payload = resp.read()
        return resp, payload

    def json(self, method, path, body=None, **kw):
        resp, payload = self.request(method, path, body, **kw)
        return resp.status, json.loads(payload.decode())


class ServerCase(unittest.TestCase):
    engine = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='band-app-test-'))
        self.start()

    def start(self):
        self.server = band_app.make_server(self.tmp, 0, worked_examples=EXAMPLES,
                                           engine=self.engine, quiet=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = Client(self.server)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=30)
        self.server.server_close()
        self.server.store.stop()

    def tearDown(self):
        self.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wait(self, run_id, timeout=240):
        t0 = time.time()
        seen = []
        while time.time() - t0 < timeout:
            st, out = self.client.json('GET', f'/api/runs/{run_id}')
            self.assertEqual(st, 200)
            s = out['run']['status']
            if not seen or seen[-1] != s:
                seen.append(s)
            if s in ('done', 'failed', 'cancelled'):
                return out, seen
            time.sleep(0.05)
        self.fail(f'run {run_id} did not finish: {seen}')


def fake_engine(case):
    """A stand-in for the engine with the real result shape (the committed bearing demo
    result), so the guard tests do not spend seconds in the physics."""
    r = json.loads((ROOT / 'artifacts' / 'band_diagnosis'
                    / 'bearing-order-demo.result.json').read_text())
    r['inputs'] = bd.validate_case(case)
    r['case_name'] = case['name']
    time.sleep(0.2)
    return r


class GuardTest(ServerCase):
    engine = staticmethod(fake_engine)

    def test_loopback_bind(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')

    def test_page_assets_and_headers(self):
        for path, ctype in (('/', 'text/html'), ('/app.js', 'text/javascript'),
                            ('/app.css', 'text/css')):
            resp, body = self.client.request('GET', path, token=False)
            self.assertEqual(resp.status, 200, path)
            self.assertTrue(resp.getheader('Content-Type').startswith(ctype))
            csp = resp.getheader('Content-Security-Policy')
            for part in ("default-src 'self'", "script-src 'self'", "'unsafe-inline'"):
                self.assertIn(part, csp)
            self.assertEqual(resp.getheader('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(resp.getheader('Cache-Control'), 'no-store')
            self.assertEqual(resp.getheader('Referrer-Policy'), 'no-referrer')
            text = body.decode()
            self.assertNotIn('http://', text, path)
            self.assertNotIn('https://', text, path)
            if path == '/':
                self.assertNotIn('<script>', text)       # no inline script
                self.assertIn(self.server.token, text)
        st, meta = self.client.json('GET', '/api/meta')
        self.assertEqual(st, 200)
        self.assertNotIn(self.server.token, json.dumps(meta))
        self.assertEqual(len(meta['questions']), len(bpl.QUESTIONS))
        self.assertTrue(meta['worked_examples_available'])

    def test_wrong_host_and_origin_refused(self):
        for host in ('evil.example:80', f'127.0.0.1:{self.server.server_port + 1}',
                     f'example.com:{self.server.server_port}'):
            c = Client(self.server, host=host)
            resp, _ = c.request('GET', '/')
            self.assertEqual(resp.status, 403, host)
            resp, _ = c.request('GET', '/api/meta')
            self.assertEqual(resp.status, 403, host)
        resp, _ = Client(self.server, host=f'localhost:{self.server.server_port}').request(
            'GET', '/api/meta')
        self.assertEqual(resp.status, 200)
        resp, _ = self.client.request('POST', '/api/case/check', {'preset': 'foil_mill'},
                                      headers={'Origin': 'http://evil.example'})
        self.assertEqual(resp.status, 403)

    def test_token_required(self):
        for tok in (False, 'wrong-token'):
            st, out = self.client.json('GET', '/api/meta', token=tok)
            self.assertEqual(st, 403)
            st, out = self.client.json('POST', '/api/runs', {'preset': FAST_PRESET},
                                       token=tok)
            self.assertEqual(st, 403)
            self.assertIn('token', out['error']['text'])

    def test_body_limits_and_json_only(self):
        # (i) just over the limit: always a clean 413 with the plain message, also when the
        # client sends the body only after a pause (the server reads it before answering)
        big = b'{"a": "' + b'x' * (band_app.MAX_BODY_BYTES + 10) + b'"}'
        for pause in (0.0, 0.3):
            resp, payload = self.client.request('POST', '/api/case/check', raw=big,
                                                pause_s=pause)
            self.assertEqual(resp.status, 413)
            self.assertIn('too large', json.loads(payload)['error']['text'])
            self.assertEqual(resp.getheader('Connection'), 'close')
        # (ii) far over the drain bound: a 413 or a closed connection are both accepted, and
        # the server keeps serving
        huge = b'x' * (band_app.DRAIN_LIMIT_BYTES * 2)
        try:
            resp, _ = self.client.request('POST', '/api/case/check', raw=huge)
            self.assertEqual(resp.status, 413)
        except OSError:                               # reset or broken pipe: accepted here
            pass
        self.assertEqual(self.client.request('GET', '/app.css', token=False)[0].status, 200)
        resp, _ = self.client.request('POST', '/api/case/check', raw=b'preset=foil_mill',
                                      ctype='application/x-www-form-urlencoded')
        self.assertEqual(resp.status, 415)
        resp, _ = self.client.request('POST', '/api/case/check', raw=b'preset=foil_mill',
                                      ctype='application/x-www-form-urlencoded')
        self.assertEqual(resp.status, 415)
        resp, body = self.client.request('POST', '/api/case/check', raw=b'{not json')
        self.assertEqual(resp.status, 400)
        self.assertIn('not valid JSON', body.decode())
        resp, _ = self.client.request('POST', '/api/case/check', raw=b'[1, 2]')
        self.assertEqual(resp.status, 400)

    def test_early_refusals_read_the_body_first(self):
        # a refused request (wrong host, no token, unknown route) with a body sent after a
        # pause gets its refusal, never a reset connection
        body = {'preset': 'foil_mill', 'pad': 'x' * 200000}
        for client, kw, status in ((Client(self.server, host='evil.example:80'), {}, 403),
                                   (self.client, {'token': False}, 403),
                                   (self.client, {}, 404)):
            path = '/api/nothing-here' if status == 404 else '/api/case/check'
            resp, _ = client.request('POST', path, body, pause_s=0.2, **kw)
            self.assertEqual(resp.status, status)

    def test_body_shorter_than_declared_does_not_block_the_server(self):
        import socket
        # (iii) a client declares a length, sends nothing and closes; another sends half
        for sent in (b'', b'{"preset": '):
            s_ = socket.create_connection(('127.0.0.1', self.server.server_port), timeout=5)
            try:
                s_.sendall(b'POST /api/case/check HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n'
                           b'Content-Type: application/json\r\nContent-Length: 5000\r\n\r\n'
                           % self.server.server_port + sent)
            finally:
                s_.close()
        st, meta = self.client.json('GET', '/api/meta')
        self.assertEqual(st, 200)

    def test_bad_and_path_like_run_ids(self):
        for rid in ('abc', '0' * 31, 'G' * 32, '..%2F..%2Fetc', '%2e%2e', '0' * 32,
                    'A' * 32, '0' * 33):
            st, out = self.client.json('GET', f'/api/runs/{rid}')
            self.assertEqual(st, 404, rid)
            st, _ = self.client.json('GET', f'/api/runs/{rid}/case.json')
            self.assertEqual(st, 404, rid)
        st, _ = self.client.json('GET', '/api/runs/../../etc/passwd')
        self.assertIn(st, (403, 404))
        st, _ = self.client.json('GET', f'/api/runs/{"0" * 32}/meta.json')
        self.assertEqual(st, 404)          # only the listed files are served

    def test_case_check_maps_errors_to_questions(self):
        st, out = self.client.json('POST', '/api/case/check', {
            'preset': 'foil_mill', 'answers': {'values': {'exit_gauge': 80.0}}})
        self.assertEqual(st, 400)                     # entry gauge of the foil mill: 50 um
        self.assertEqual(out['error']['question'], 'exit_gauge')
        self.assertNotIn('Traceback', json.dumps(out))
        st, out = self.client.json('POST', '/api/case/check', {
            'preset': 'foil_mill', 'answers': {'values': {'exit_gauge': 18.0,
                                                           'entry_gauge': 30.0}}})
        self.assertEqual(st, 200)
        self.assertEqual(out['case']['pass']['exit_thickness_m'], 1.8e-05)
        self.assertEqual(len(out['geometry']['nozzle_positions_m']), 28)
        st, out = self.client.json('POST', '/api/case/check', {'preset': '../../etc'})
        self.assertEqual(st, 400)
        self.assertEqual(out['error']['question'], 'preset')

    def test_open_case_file_is_validated_not_stored(self):
        case = json.loads((ROOT / 'scenarios' / 'band_diagnosis_template.json').read_text())
        st, out = self.client.json('POST', '/api/case/open', {'case_file': case})
        self.assertEqual(st, 200)
        self.assertEqual(out['answers']['values']['exit_gauge'], 210.0)
        bad = dict(case, pass_={})
        st, out = self.client.json('POST', '/api/case/open', {'case_file': bad})
        self.assertEqual(st, 400)
        self.assertIn('not accepted', out['error']['text'])
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_product_defaults(self):
        st, out = self.client.json('POST', '/api/product-defaults',
                                   {'product': 'household_foil', 'exit_thickness_m': 10e-6})
        self.assertEqual(st, 200)
        self.assertEqual(out['values']['exit_gauge'], 10.0)
        st, out = self.client.json('POST', '/api/product-defaults', {'product': 'cheese'})
        self.assertEqual(st, 400)

    def test_run_queue_cancel_variant_and_restart(self):
        body = {'preset': FAST_PRESET, 'profile': 'quick', 'answers': {'values': {}}}
        ids = [self.client.json('POST', '/api/runs', body)[1]['id'] for _ in range(3)]
        st, out = self.client.json('POST', f'/api/runs/{ids[2]}/cancel', {})
        self.assertEqual(st, 200)
        self.assertEqual(out['run']['status'], 'cancelled')
        first, seen = self.wait(ids[0])
        self.assertEqual(first['run']['status'], 'done')
        self.assertEqual(seen[-1], 'done')
        self.assertTrue(set(seen) <= {'queued', 'running', 'done'})
        self.assertEqual(self.wait(ids[2])[0]['run']['status'], 'cancelled')
        self.assertEqual(self.wait(ids[1])[0]['run']['status'], 'done')
        st, out = self.client.json('POST', f'/api/runs/{ids[0]}/cancel', {})
        self.assertEqual(st, 409)
        st, out = self.client.json('POST', f'/api/runs/{ids[0]}/variant', {
            'changes': {'exit_speed': 400.0}})
        self.assertEqual(st, 202)
        var, _ = self.wait(out['id'])
        self.assertEqual(var['run']['base_run_id'], ids[0])
        self.assertEqual(var['run']['changes'], ['Exit speed'])
        self.assertIn('compared_with_base', var['summary'])
        case = self.client.json('GET', f'/api/runs/{out["id"]}/case.json')[1]
        self.assertEqual(case['pass']['exit_speed_m_s'], 400.0 / 60)
        st, out2 = self.client.json('POST', f'/api/runs/{ids[0]}/rerun', {'profile': 'detailed'})
        self.assertEqual(st, 202)
        rerun, _ = self.wait(out2['id'])
        self.assertEqual(rerun['run']['profile'], 'detailed')
        self.assertEqual(rerun['run']['base_run_id'], ids[0])
        self.stop()
        self.start()                                  # a new session on the same folder
        st, listing = self.client.json('GET', '/api/runs')
        self.assertEqual(st, 200)
        got = {r['id']: r for r in listing['runs']}
        self.assertEqual(set(got), set(ids) | {out['id'], out2['id']})
        self.assertEqual(got[out['id']]['base_run_id'], ids[0])


class FailingEngineTest(ServerCase):
    calls = []

    @staticmethod
    def engine(case):
        FailingEngineTest.calls.append(case['name'])
        if 'boom' in case['name']:
            raise RuntimeError('internal detail that must not reach the page')
        if 'domain' in case['name']:
            raise ValueError('pass.exit_thickness_m must be below pass.entry_thickness_m')
        return fake_engine(case)

    def test_failures_are_plain_and_the_queue_survives(self):
        def submit(name):
            return self.client.json('POST', '/api/runs', {
                'preset': FAST_PRESET, 'answers': {'name': name, 'values': {}}})[1]['id']
        a, b, c = submit('boom'), submit('domain'), submit('fine')
        out, _ = self.wait(a)
        self.assertEqual(out['run']['status'], 'failed')
        text = json.dumps(out)
        self.assertNotIn('Traceback', text)
        self.assertNotIn('internal detail', text)
        self.assertIn('internal error', out['run']['error']['text'])
        out, _ = self.wait(b)
        self.assertEqual(out['run']['status'], 'failed')
        self.assertEqual(out['run']['error']['question'], 'exit_gauge')
        self.assertIn('could not be run', out['run']['error']['text'])
        self.assertNotIn('pass.exit_thickness_m', out['run']['error']['text'])   # plain words
        out, _ = self.wait(c)
        self.assertEqual(out['run']['status'], 'done')


class DisappearingClientTest(ServerCase):
    engine = staticmethod(fake_engine)

    def test_client_that_disconnects_does_not_stop_the_server(self):
        import socket
        for payload in (b'POST /api/runs HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n'
                        b'Content-Length: 500\r\nContent-Type: application/json\r\n\r\n{"a',
                        b'GET /api/meta HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n'):
            s = socket.create_connection(('127.0.0.1', self.server.server_port), timeout=5)
            s.sendall(payload.replace(b'%d', str(self.server.server_port).encode()))
            s.close()
        rid = self.client.json('POST', '/api/runs', {'preset': FAST_PRESET})[1]['id']
        self.assertEqual(self.wait(rid)[0]['run']['status'], 'done')


class RealEngineTest(ServerCase):
    """One quick run of the fastest demo through the real engine."""

    def test_quick_run_writes_every_file(self):
        rid = self.client.json('POST', '/api/runs', {
            'preset': FAST_PRESET, 'profile': 'quick',
            'answers': bpl.answers_from_case(
                next(p for p in bpl.presets(EXAMPLES) if p['id'] == FAST_PRESET)['case'])}
        )[1]['id']
        out, seen = self.wait(rid)
        self.assertEqual(out['run']['status'], 'done', out['run'].get('error'))
        self.assertIn('running', seen)
        for name in ('answers.json', 'case.json', 'result.json', 'report.html',
                     'summary.json', 'meta.json'):
            self.assertTrue((self.tmp / rid / name).is_file(), name)
        s = out['summary']
        self.assertEqual(s['profile']['id'], 'quick')
        self.assertEqual(s['causes'][0]['id'], 'order_locked_drive_or_bearing_excitation')
        resp, body = self.client.request('GET', f'/api/runs/{rid}/report.html')
        self.assertEqual(resp.status, 200)
        self.assertNotIn(b'<script', body.lower())
        self.assertIn("default-src 'none'", resp.getheader('Content-Security-Policy'))
        meta = json.loads((self.tmp / rid / 'meta.json').read_text())
        self.assertEqual(meta['engine']['case_schema'], bd.CASE_SCHEMA_V2)


if __name__ == '__main__':
    unittest.main()
