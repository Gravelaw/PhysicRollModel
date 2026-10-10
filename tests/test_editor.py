"""Guided local authoring, recovery and verified saved-run reopening."""

from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from physicroll.editor import (_template, guided_values, make_editor_server)
from physicroll.run_bundle import verify_run_bundle


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.runs = Path(self.temporary.name) / 'runs'
        self.server = make_editor_server(self.runs)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.running = self.pool.submit(self.server.serve_forever)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.running.result(timeout=5)
        self.pool.shutdown()
        self.temporary.cleanup()

    def get(self, path):
        with urlopen(self.url + path, timeout=10) as response:
            return response.read().decode('utf-8')

    def post(self, path, fields):
        request = Request(self.url + path, data=urlencode(fields).encode('utf-8'),
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, response.read().decode('utf-8')
        except HTTPError as exc:
            return exc.code, exc.read().decode('utf-8')

    def token(self):
        page = self.get('/new/checked_pass')
        return re.search(r'name="csrf" value="([^"]+)"', page).group(1)

    def guided_form(self):
        spec = _template('checked_pass')
        return {'csrf': self.token(), 'mode': 'guided', 'base_json': spec.to_json(),
                **guided_values(spec)}

    def test_guided_check_recovery_save_report_and_reopen(self):
        form = self.guided_form()
        form['exit_thickness_m'] = '0.0001'
        status, page = self.post('/check', form)
        self.assertEqual(status, 400)
        self.assertIn('Foil excluded', page)
        self.assertIn('value="0.0001"', page)
        self.assertEqual(list(self.runs.iterdir()), [])

        form['exit_thickness_m'] = '0.0015'
        form['name'] = 'editor_synthetic_pass'
        status, page = self.post('/check', form)
        self.assertEqual(status, 200)
        self.assertIn('Check passed; no run saved.', page)
        self.assertIn('scientific_qualification: NOT_ASSESSED', page)
        self.assertEqual(list(self.runs.iterdir()), [])

        status, page = self.post('/save', form)
        self.assertEqual(status, 200)
        self.assertIn('Verification passed', page)
        folders = list(self.runs.iterdir())
        self.assertEqual(len(folders), 1)
        spec, result = verify_run_bundle(folders[0])
        self.assertEqual(spec.to_dict()['requested_inputs']['scenario']['name'],
                         'editor_synthetic_pass')
        self.assertEqual(result.sha256, verify_run_bundle(folders[0])[1].sha256)
        self.assertIn('editor_synthetic_pass', self.get('/report/' + folders[0].name))
        self.assertIn('value="editor_synthetic_pass"',
                      self.get('/edit/' + folders[0].name))

    def test_json_workflow_errors_keep_text_and_csrf_is_required(self):
        form = self.guided_form()
        form['csrf'] = 'wrong'
        status, _ = self.post('/save', form)
        self.assertEqual(status, 403)
        self.assertEqual(list(self.runs.iterdir()), [])

        page = self.get('/new/operating_replay')
        self.assertIn('RunSpec JSON', page)
        token = self.token()
        status, page = self.post('/check', {'csrf': token, 'mode': 'json',
                                           'raw_json': '{"oops":'})
        self.assertEqual(status, 400)
        self.assertIn('{&quot;oops&quot;:', page)
        self.assertIn('Correct RunSpec JSON', page)

    def test_foreign_or_duplicate_host_and_foreign_post_origin_reject(self):
        port = self.server.server_port
        connection = HTTPConnection('127.0.0.1', port, timeout=5)
        connection.request('GET', '/new/checked_pass',
                           headers={'Host': f'attacker.example:{port}'})
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        self.assertNotIn('name="csrf"', response.read().decode('utf-8'))
        connection.close()

        connection = HTTPConnection('127.0.0.1', port, timeout=5)
        connection.putrequest('GET', '/new/checked_pass', skip_host=True)
        connection.putheader('Host', f'127.0.0.1:{port}')
        connection.putheader('Host', f'attacker.example:{port}')
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()

        form = self.guided_form()
        connection = HTTPConnection('127.0.0.1', port, timeout=5)
        connection.request('POST', '/save', body=urlencode(form), headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://attacker.example',
        })
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()
        self.assertEqual(list(self.runs.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
