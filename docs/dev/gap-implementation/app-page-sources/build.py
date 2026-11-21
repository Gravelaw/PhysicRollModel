import pathlib, subprocess, sys, tempfile
src = pathlib.Path(__file__).parent
js = ''.join((src / n).read_text(encoding='utf-8') for n in sorted(p.name for p in src.glob('0*.js')))
css = (src / 'app.css').read_text(encoding='utf-8')
(pathlib.Path(tempfile.gettempdir()) / 'physicroll_band_app.js').write_text(js, encoding='utf-8')
r = subprocess.run(['node', '--check', str(pathlib.Path(tempfile.gettempdir()) / 'physicroll_band_app.js')], capture_output=True, text=True)
if r.returncode:
    print(r.stderr); sys.exit(1)
for name, text in (('js', js), ('css', css)):
    assert "'''" not in text, name
    assert 'http://' not in text and 'https://' not in text, name
target = pathlib.Path(__file__).resolve().parents[4] / 'physicroll' / 'band_app_assets.py'
old = target.read_text(encoding='utf-8')
head = old[:old.index('APP_CSS = ')]
target.write_text(head + "APP_CSS = r'''" + css + "'''\n\nAPP_JS = r'''" + js + "'''\n", encoding='utf-8', newline='\n')
print('built', len(js), len(css))
