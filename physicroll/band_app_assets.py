"""Page assets of the band app (HTML, CSS and JavaScript as string constants).

Kept as Python strings so that they ship in a wheel without changing ``pyproject.toml``'s
package data (which lists JSON and CSV resources only). No external URL, no web font, no
inline script: the page loads ``/app.js`` and ``/app.css`` from the app itself.
"""
from html import escape

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="band-app-token" content="{token}">
<title>Band screening</title>
<link rel="stylesheet" href="/app.css">
<script src="/app.js" defer></script>
</head>
<body>
<main id="app"><p>Loading the band screening tool.</p></main>
<noscript><p>This page needs JavaScript (it runs only on this computer).</p></noscript>
</body>
</html>
"""


def page_html(token):
    return PAGE_TEMPLATE.format(token=escape(token, quote=True))


APP_CSS = """:root{--ink:#14202B;--paper:#F3F4F1}
body{font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);
background:var(--paper);margin:0;padding:16px}
"""

APP_JS = """'use strict';
(function () {
  var token = document.querySelector('meta[name="band-app-token"]').content;
  fetch('/api/meta', {headers: {'X-Band-App-Token': token}})
    .then(function (r) { return r.json(); })
    .then(function (m) {
      document.getElementById('app').textContent =
        'Band screening: ' + m.questions.length + ' questions loaded.';
    });
})();
"""
