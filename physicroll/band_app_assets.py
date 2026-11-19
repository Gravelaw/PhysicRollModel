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


APP_CSS = r''':root{--ink:#14202B;--paper:#F3F4F1;--panel:#E4E8E3;--line:#C9D0CA;--soft:#47545F;
--orange-text:#B5521A;--orange:#E0702A;--blue:#2F6FA3;--green:#2E6B4F;--amber:#8A5A00;
--red:#9B2C2C;--card:#FFFFFF;--focus:#2F6FA3;--bar-old:#9AA6AE;--strip:#D5DBD6;
--strip-edge:#6B7780;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--ink:#E6EBE8;--paper:#11181F;--panel:#1B252E;
--line:#33414C;--soft:#AEB9C1;--orange-text:#F0A06A;--orange:#E0702A;--blue:#7DB3E0;
--green:#7CC4A0;--amber:#E2B85C;--red:#F09A9A;--card:#16202A;--focus:#7DB3E0;
--bar-old:#5C6A74;--strip:#2A3640;--strip-edge:#8C99A2;color-scheme:dark}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
h1,h2,h3,h4{font-weight:700;line-height:1.25;margin:0 0 .5rem}
h1{font-size:1.35rem}h2{font-size:1.2rem}h3{font-size:1.05rem}h4{font-size:1rem}
p{margin:.4rem 0 .7rem}
a{color:var(--blue)}
.num,.tab{font-variant-numeric:tabular-nums}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.sr{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
white-space:nowrap}
.soft{color:var(--soft)}
.small{font-size:.875rem}
.hidden{display:none!important}
/* layout */
.topbar{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1rem;padding:12px 16px;
border-bottom:1px solid var(--line);background:var(--card)}
.topbar .brand{display:flex;flex-direction:column;margin-right:auto;min-width:0}
.topbar .brand small{color:var(--soft)}
.wrap{max-width:1180px;margin:0 auto;padding:16px}
.btn{display:inline-flex;align-items:center;gap:.4rem;border:1px solid var(--line);
background:var(--card);border-radius:6px;padding:.45rem .8rem;min-height:40px}
.btn:hover{border-color:var(--soft)}
.btn.primary{background:var(--ink);color:var(--paper);border-color:var(--ink);font-weight:700}
.btn.link{border:0;background:none;color:var(--blue);padding:.2rem .1rem;min-height:0;
text-decoration:underline}
.btn[disabled]{opacity:.55;cursor:not-allowed}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px;
margin:0 0 16px}
.card>h2{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap}
.howto{color:var(--soft);font-size:.92rem;margin:-.2rem 0 .8rem}
.screening-note{font-size:.88rem;color:var(--soft);border-left:3px solid var(--orange);
padding:.1rem .6rem;margin:.4rem 0 .8rem}
/* progress */
.progress{display:flex;gap:4px;margin:0 0 16px;padding:0;list-style:none;counter-reset:s}
.progress li{flex:1;min-width:0}
.progress button{width:100%;text-align:left;border:0;border-top:5px solid var(--line);
background:none;padding:.45rem .2rem;color:var(--soft);font-weight:600}
.progress li.done button{border-top-color:var(--green);color:var(--ink)}
.progress li.current button{border-top-color:var(--orange);color:var(--ink)}
.progress .n{display:inline-block;min-width:1.4em}
.inputgrid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start}
.sidepanel{position:sticky;top:12px}
.sidepanel .card{margin:0}
.runbar{position:sticky;bottom:0;z-index:5;background:var(--card);border-top:2px solid var(--ink);
padding:10px 16px;display:flex;flex-wrap:wrap;gap:.6rem 1rem;align-items:center}
.runbar .msg{flex:1 1 220px;font-size:.9rem;color:var(--soft)}
.runbar .msg.err{color:var(--red);font-weight:600}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.seg label{display:flex;align-items:center;gap:.3rem;padding:.35rem .7rem;cursor:pointer}
.seg input{margin:0}
.seg label:has(input:checked){background:var(--panel);font-weight:700}
/* questions */
.q{border-top:1px solid var(--line);padding:.8rem 0}
.q:first-of-type{border-top:0}
.q .w{font-weight:600;display:block;margin-bottom:.2rem}
.q .help{font-size:.88rem;color:var(--soft);margin:.1rem 0 .4rem}
.q.bad{box-shadow:inset 4px 0 0 var(--red);padding-left:10px}
.q .err{color:var(--red);font-weight:600;font-size:.9rem}
.q.flash{animation:flash 1.6s ease-out}
@keyframes flash{0%{background:var(--panel)}100%{background:transparent}}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;border:0;margin:0;padding:0}
.chips legend{padding:0;margin-bottom:.3rem}
.chip{display:inline-flex;align-items:center;gap:.35rem;border:1px solid var(--line);
border-radius:999px;padding:.3rem .8rem;background:var(--card);cursor:pointer;min-height:36px}
.chip input{margin:0;accent-color:var(--ink)}
.chip:has(input:checked){border-color:var(--ink);background:var(--panel);font-weight:600}
.chip.unknown{border-style:dashed}
.numrow{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem}
.numrow input[type=number],.numrow input[type=text]{width:9.5rem;padding:.4rem;border:1px solid var(--line);
border-radius:5px;background:var(--card)}
.numrow input.wide{width:min(26rem,100%)}
.unit{color:var(--soft)}
.typical{font-size:.85rem;color:var(--soft)}
.badge{display:inline-block;font-size:.78rem;font-weight:700;border-radius:4px;padding:.05rem .4rem;
border:1px solid currentColor}
.badge.suggest{color:var(--amber)}
.origin{display:inline-flex;flex-wrap:wrap;gap:.2rem .6rem;font-size:.85rem;border:0;margin:.3rem 0 0;padding:0}
.origin label{display:inline-flex;gap:.25rem;align-items:center}
select{padding:.4rem;border:1px solid var(--line);border-radius:5px;background:var(--card);max-width:100%}
details.more{border:1px solid var(--line);border-radius:8px;padding:.4rem .8rem;margin:.8rem 0;
background:var(--paper)}
details.more>summary{cursor:pointer;font-weight:700;padding:.3rem 0}
details.more h4{margin-top:.8rem;color:var(--soft)}
.listedit{width:100%;border-collapse:collapse;font-size:.92rem}
.listedit th{text-align:left;font-weight:600;color:var(--soft);font-size:.82rem;padding:.2rem}
.listedit td{padding:.2rem}
.listedit input,.listedit select{width:100%;min-width:4.5rem;padding:.3rem;border:1px solid var(--line);
border-radius:4px;background:var(--card)}
.scrollbox{overflow-x:auto;max-width:100%;position:relative}
.picks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:.4rem 0 .8rem}
.pick{display:flex;flex-direction:column;gap:.4rem;border:2px solid var(--line);border-radius:8px;
padding:10px;background:var(--card);cursor:pointer;text-align:left}
.pick svg{width:100%;height:auto;display:block}
.pick:has(input:checked){border-color:var(--ink);box-shadow:0 0 0 2px var(--orange) inset}
.pick input{position:absolute;opacity:0}
.pick:has(input:focus-visible){outline:3px solid var(--focus);outline-offset:2px}
.pick .t{font-weight:700}
.presets{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.preset{border:2px solid var(--line);border-radius:8px;padding:10px;background:var(--card);cursor:pointer}
.preset:has(input:checked){border-color:var(--ink);box-shadow:0 0 0 2px var(--orange) inset}
.preset .t{font-weight:700;display:block}
.preset input{margin-right:.4rem}
.banner{border:1px solid var(--amber);border-left-width:5px;border-radius:6px;padding:.5rem .8rem;
margin:.6rem 0;background:var(--card)}
/* drawings */
.drawing{display:block}
.drawing .side{margin-top:.4rem}
.poslist{display:flex;flex-wrap:wrap;gap:.3rem 1.2rem}
.drawing svg{width:100%;height:auto;display:block;touch-action:none;user-select:none}
.drawing .side{font-size:.92rem}
svg text{fill:var(--ink);font-family:inherit}
svg .softtext{fill:var(--soft)}
svg .strip{fill:var(--strip);stroke:var(--strip-edge);stroke-width:1.5}
svg .roll{fill:none;stroke:var(--line);stroke-width:1;stroke-dasharray:4 3}
svg .band{fill:var(--ink);opacity:.82;cursor:grab}
svg .band:focus{outline:none;stroke:var(--orange);stroke-width:4;opacity:1}
svg .band.drag{cursor:grabbing}
svg .tick{stroke:var(--soft);stroke-width:1}
svg .noz{cursor:pointer}
svg .noz circle{stroke:var(--ink);stroke-width:1.5}
svg .noz.healthy circle{fill:var(--card)}
svg .noz.weak circle{fill:url(#half)}
svg .noz.blocked circle{fill:var(--ink)}
svg .noz:focus{outline:none}
svg .noz:focus circle{stroke:var(--orange);stroke-width:4}
svg .spray{fill:var(--blue);opacity:.16}
svg .spray.weak{opacity:.07}
svg .pred{fill:none;stroke-width:2}
svg .thermal{fill:none;stroke:var(--orange);stroke-width:2.2}
svg .link{stroke:var(--green);stroke-width:2;stroke-dasharray:3 2}
svg .tol{fill:var(--green);opacity:.15}
svg [tabindex]{cursor:pointer}
svg .mark:focus{outline:none}
svg .mark:focus>*:first-child{stroke:var(--orange);stroke-width:3}
.legend{list-style:none;padding:0;margin:.4rem 0;display:flex;flex-wrap:wrap;gap:.3rem 1rem;font-size:.88rem}
.legend li{display:flex;align-items:center;gap:.35rem}
.legend svg{width:30px;height:16px;flex:none}
.tip{position:fixed;z-index:20;pointer-events:none;background:var(--ink);color:var(--paper);
padding:.3rem .55rem;border-radius:5px;font-size:.85rem;max-width:280px}
.poslist{list-style:none;padding:0;margin:.3rem 0}
.poslist li{display:flex;align-items:center;gap:.4rem;margin:.25rem 0}
.poslist input{width:6.5rem;padding:.3rem;border:1px solid var(--line);border-radius:4px;background:var(--card)}
.nozlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:.3rem .8rem;font-size:.88rem}
.nozlist label{display:flex;align-items:center;gap:.3rem}
.nozlist input{width:4.2rem;padding:.2rem;border:1px solid var(--line);border-radius:4px;background:var(--card)}
/* running */
.running{max-width:720px;margin:24px auto}
.spinner{width:42px;height:42px;border-radius:50%;border:5px solid var(--line);border-top-color:var(--orange);
animation:spin 1s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}
.runhead{display:flex;gap:16px;align-items:center}
.stages{padding-left:1.2rem}
.stages li{color:var(--soft)}
.elapsed{font-size:1.6rem;font-weight:700}
/* result */
.headline{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start}
.headline .text{font-size:1.25rem;font-weight:700;line-height:1.35}
.trust{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--paper)}
.meter{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:.4rem 0}
.meter span{display:block;text-align:center;font-size:.8rem;font-weight:700;padding:.35rem 0;
border:2px solid var(--line);border-radius:4px;color:var(--soft);background:var(--card)}
.meter span.on{border-color:var(--ink);color:var(--ink);background:var(--panel)}
.meter span.on::before{content:"\25B6 "}
.statusline{display:flex;gap:.5rem;align-items:flex-start;font-size:.92rem;font-weight:600;
border:1px dashed var(--soft);border-radius:6px;padding:.4rem .6rem;margin:.6rem 0 0}
.profile{display:flex;flex-wrap:wrap;gap:.4rem 1rem;align-items:flex-start;font-size:.9rem;
background:var(--panel);border-radius:6px;padding:.4rem .7rem;margin-top:.8rem}
.change{border:2px solid var(--blue);border-radius:8px;padding:.6rem .8rem;margin:.4rem 0 .8rem;background:var(--card)}
.change ul{margin:.3rem 0;padding-left:1.2rem}
.bars{display:flex;flex-direction:column;gap:2px}
.bar{display:grid;grid-template-columns:58px minmax(0,15rem) minmax(0,1fr) 3rem;gap:10px;align-items:center;
width:100%;text-align:left;border:1px solid transparent;border-radius:6px;background:none;padding:6px 4px}
.bar:hover{background:var(--panel)}
.bar[aria-expanded=true]{border-color:var(--ink);background:var(--panel)}
.bar .pic svg{width:58px;height:39px;display:block}
.bar .nm{min-width:0}
.bar .nm b{display:block;font-weight:600;line-height:1.25}
.bar .score{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.track{position:relative;height:22px}
.track .zero{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--soft)}
.track .fill{position:absolute;top:3px;height:16px;border-radius:2px;transition:left .9s ease,width .9s ease}
.track .old{position:absolute;top:9px;height:4px;background:var(--bar-old);border-radius:2px}
.fill.s-best{background:var(--green)}
.fill.s-fits{background:var(--blue)}
.fill.s-weak{background:var(--amber)}
.fill.s-none{background:var(--line)}
.fill.s-no{background:var(--red)}
.stand{display:inline-flex;align-items:center;gap:.25rem;font-size:.85rem;font-weight:700}
.stand.s-best{color:var(--green)}.stand.s-fits{color:var(--blue)}.stand.s-weak{color:var(--amber)}
.stand.s-none{color:var(--soft)}.stand.s-no{color:var(--red)}
.axis{display:grid;grid-template-columns:58px minmax(0,15rem) minmax(0,1fr) 3rem;gap:10px;font-size:.78rem;color:var(--soft)}
.axis .ax{display:flex;justify-content:space-between}
.detail{border:2px solid var(--ink);border-radius:8px;padding:12px 14px;margin:.4rem 0 .8rem;background:var(--card)}
.detail .top{display:grid;grid-template-columns:220px minmax(0,1fr);gap:16px;align-items:start}
.detail .top svg{width:100%;height:auto}
.evid{list-style:none;padding:0;margin:.2rem 0 .8rem}
.evid li{padding:.35rem 0;border-top:1px solid var(--line)}
.evid li:first-child{border-top:0}
.evid .lab{font-weight:600}
.evid .w{font-size:.8rem;font-weight:700;color:var(--soft)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.checklist{list-style:none;padding:0;margin:0}
.checklist>li{border-top:1px solid var(--line);padding:.6rem 0}
.checklist>li:first-child{border-top:0}
.checklist .row{display:flex;gap:.6rem;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
.inline-q{border:1px solid var(--line);border-radius:8px;padding:.4rem .8rem;margin:.5rem 0;background:var(--paper)}
.pending{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;background:var(--panel);border-radius:8px;
padding:.6rem .8rem;margin-top:.8rem}
.whatif{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.stepper{display:flex;align-items:center;gap:.3rem}
.stepper input{width:7rem;padding:.4rem;border:1px solid var(--line);border-radius:5px;background:var(--card)}
.stepper button{min-width:40px;min-height:40px;border:1px solid var(--line);border-radius:5px;background:var(--card)}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.compare>div{min-width:0}
.multiples{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.multiples figure{margin:0;border:1px solid var(--line);border-radius:6px;padding:8px;background:var(--paper)}
.multiples figcaption{font-size:.88rem;font-weight:600}
.multiples svg{width:100%;height:auto;display:block}
.fig svg{width:100%;height:auto;display:block}
.flags{list-style:none;padding:0}
.flags li{border-top:1px solid var(--line);padding:.5rem 0}
.flags li:first-child{border-top:0}
.takeaway{display:flex;flex-wrap:wrap;gap:.6rem}
/* drawer */
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(440px,100%);z-index:30;background:var(--card);
border-left:2px solid var(--ink);overflow-y:auto;padding:16px;box-shadow:-8px 0 24px rgba(0,0,0,.18)}
.drawer .runs{list-style:none;padding:0}
.drawer .runs li{border-top:1px solid var(--line);padding:.5rem 0}
.drawer .runs ul{list-style:none;padding-left:1rem;border-left:3px solid var(--line);margin:.3rem 0 0}
.runitem{width:100%;text-align:left;border:0;background:none;padding:.2rem}
.runitem:hover{background:var(--panel)}
.empty{color:var(--soft);font-style:italic}
.errorbox{border:2px solid var(--red);border-radius:8px;padding:12px;background:var(--card)}
.printonly{display:none}
@media (max-width:860px){
.inputgrid,.headline,.drawing,.detail .top,.cols,.compare{grid-template-columns:minmax(0,1fr)}
.sidepanel{position:static}
.picks{grid-template-columns:repeat(2,minmax(0,1fr))}
.bar,.axis{grid-template-columns:34px minmax(0,1fr) 2.5rem;grid-template-areas:"p n s" "t t t"}
.bar .pic{grid-area:p}.bar .nm{grid-area:n}.bar .score{grid-area:s}.bar .track{grid-area:t}
.bar .pic svg{width:34px;height:24px}
.axis{display:none}
.detail .top svg{max-width:240px}
.progress .lab{display:none}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media print{
body{background:#fff;color:#000;font-size:11pt}
:root{--ink:#000;--paper:#fff;--card:#fff;--panel:#eee;--line:#999;--soft:#333;--strip:#e8e8e8}
.topbar,.runbar,.progress,.noprint,.drawer,details:not([open])>*:not(summary),.btn,button.bar::after{display:none!important}
.printonly{display:block}
.card{border:1px solid #000;break-inside:avoid;page-break-inside:avoid;margin-bottom:8px;padding:8px}
.wrap{max-width:none;padding:0}
.headline{grid-template-columns:1fr 200px}
.fill{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.fill.s-best,.fill.s-fits,.fill.s-weak,.fill.s-no,.fill.s-none{background:#fff!important;border:1.5px solid #000}
.fill.s-best{background:#000!important}
.fill.s-fits{background:repeating-linear-gradient(90deg,#000 0 2px,#fff 2px 5px)!important}
.stand{color:#000!important}
.bar{break-inside:avoid}
svg .thermal{stroke:#000}svg .link{stroke:#000}svg .tol{fill:#ccc}
}
.mini .lbl{display:none}
.detail .big .lbl,.pick .lbl{display:inline}
details.inline{display:inline}
details.inline summary{display:inline;cursor:pointer;color:var(--blue);text-decoration:underline}
svg .spray{opacity:.11}
@media print{.noprint{display:none!important}.trust details{display:block}.trust details>summary{display:none}
.trust details>*{display:block!important}.detail{display:none}}
@media (max-width:860px){.runbar{padding:8px 12px;gap:.4rem .6rem}.runbar .msg{flex-basis:100%;font-size:.82rem;order:3}
.progress .short{display:inline}.topbar{padding:10px 12px}.topbar h1{font-size:1.1rem}.topbar small{display:none}
.wrap{padding:12px}.card{padding:12px}}
.progress .short{display:none}
@media (max-width:860px){.runbar .seg label{padding:.3rem .5rem}.runbar .btn.primary{padding:.45rem .7rem}
.runbar .msg{display:none}.runbar .msg.err{display:block}}
.bar.changed{box-shadow:inset 5px 0 0 var(--orange);background:var(--paper)}
@media (max-width:860px){.bar,.axis{grid-template-columns:34px minmax(0,1fr) 3.4rem}}
'''

APP_JS = r''''use strict';
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
    otherOpen: false
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
    var all = M.presets.concat(S.presetsExtra);
    for (var i = 0; i < all.length; i++) { if (all[i].id === S.presetId) { return all[i]; } }
    return all[0];
  }
  function pv(id) { var v = preset().answers.values[id]; return v === undefined ? null : v; }
  function val(id) { var v = S.answers.values[id]; return v === undefined ? null : v; }
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
  function originCounts() {
    var c = {measured: 0, estimated: 0};
    M.questions.forEach(function (q) {
      var o = S.answers.origins[q.id];
      if (q.origin_tracked && (o === 'measured' || o === 'estimated') && S.touched[q.id]) { c[o] += 1; }
    });
    return c;
  }
  function geometry() {
    return (S.check && S.check.geometry) || preset().geometry;
  }
  function body() {
    var b = {preset: S.presetId, answers: S.answers};
    if (S.presetId === 'case_file') { b.case_file = S.caseFile; }
    return b;
  }

  var checkTimer = null;
  function scheduleCheck() {
    if (checkTimer) { clearTimeout(checkTimer); }
    checkTimer = setTimeout(runCheck, 450);
    updateSide();
  }
  function runCheck() {
    var seq = ++S.checkSeq;
    api('POST', '/api/case/check', body()).then(function (r) {
      if (seq !== S.checkSeq) { return; }
      S.errors = {}; S.generalError = null;
      if (r.status === 200) {
        var oldN = geometry().nozzle_positions_m.length;
        S.check = r.data;
        if (S.check.geometry.nozzle_positions_m.length !== oldN && Array.isArray(val('nozzle_levels'))) {
          S.answers.values.nozzle_levels = null;
          S.banner = 'The spray header changed, so the nozzle marks were reset to "Don\'t know".';
          if (S.view === 'input') { render(); return; }
        }
      } else {
        S.check = null;
        var e = (r.data && r.data.error) || {text: 'The inputs could not be checked.'};
        if (e.question) { S.errors[e.question] = e.text; } else { S.generalError = e.text; }
      }
      markErrors();
      updateSide();
    });
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
    if (S.suggested[q.id]) {
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
      return '<div class="numrow"><input type="text" class="wide" id="' + id + '" data-nums="' + q.id +
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
      widget(q, ctx) + typicalLine(q, ctx) + originMark(q, ctx) +
      '<div class="err" role="alert">' + esc(S.errors[q.id] || '') + '</div></div>';
  }

  function parseNums(text) {
    var t = String(text).trim();
    if (!t) { return null; }
    var parts = t.split(/[,;\s]+/).filter(Boolean).map(Number);
    return parts.every(isFinite) ? parts : undefined;
  }
  // ------------------------------------------------------------------ the strip drawing
  // One drawing for input (place bands, mark nozzles) and for the result (what fits where).
  var W = 1000, ML = 14, MR = 14;
  // drawings are laid out at about their on-screen width, so 12 px text stays 12 px
  function drawW() { return window.innerWidth < 860 ? Math.max(300, window.innerWidth - 70) :  Math.round(Math.max(320, Math.min(1120, (app.clientWidth || window.innerWidth) - (window.innerWidth < 860 ? 70 : 120)))); }
  var KIND_STYLE = {   // dash pattern + letter: never colour alone
    steady_stripes: {dash: '', letter: 'S', colour: 'var(--orange)'},
    blocked_or_low_level_nozzles: {dash: '6 3', letter: 'N', colour: 'var(--blue)'},
    event_nozzles: {dash: '2 3', letter: 'V', colour: 'var(--blue)'},
    event_stripe_peaks: {dash: '8 3 2 3', letter: 'E', colour: 'var(--orange)'},
    incoming_ridges: {dash: '10 4', letter: 'R', colour: 'var(--soft)'},
    two_tone: {dash: '1 2', letter: 'T', colour: 'var(--soft)'}
  };

  function drawStrip(o) {
    W = o.compact ? Math.max(320, Math.round(drawW() / 2 - 30)) : drawW();
    var barrel = o.barrel || (o.edge * 2 + o.width) || 1.5;
    var sx = (W - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var res = o.result, hasTh = res && res.thermal_profile;
    var yN = 22, yTop = hasTh ? 128 : 74, yBot = yTop + 84, yRul = yBot + 8, H = yRul + 44;
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(o.label) + '"' +
      (o.id ? ' id="' + o.id + '"' : '') + ' data-barrel="' + barrel + '" data-edge="' + o.edge +
      '" data-width="' + o.width + '" data-ml="' + ML + '" data-sx="' + sx + '">';
    s += '<defs><pattern id="half" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="var(--card)"/>' +
      '<path d="M0 4L4 0" stroke="var(--ink)" stroke-width="1.4"/></pattern>' +
      '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="2" height="6" fill="var(--soft)"/></pattern></defs>';
    // roll barrel and spray header
    s += '<rect class="roll" x="' + X(0) + '" y="' + (yN - 14) + '" width="' + (barrel * sx) + '" height="' + (yBot - yN + 18) + '"/>';
    s += '<text x="' + X(0) + '" y="' + (yN - 16 > 8 ? yN - 16 : 10) + '" font-size="12" class="softtext">roll barrel ' + mmInt(barrel) + '</text>';
    var noz = o.nozzles || [];
    var pitch = noz.length > 1 ? (noz[1].pos - noz[0].pos) * sx : 30;
    var r = Math.max(4, Math.min(10, pitch * 0.32));
    noz.forEach(function (n) {
      var st = n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      if (n.level > 0) {
        s += '<path class="spray' + (st === 'weak' ? ' weak' : '') + '" d="M' + X(n.pos) + ' ' + (yN + r) + 'L' +
          (X(n.pos) - pitch * 0.62) + ' ' + yTop + 'L' + (X(n.pos) + pitch * 0.62) + ' ' + yTop + 'Z"/>';
      }
    });
    noz.forEach(function (n) {
      var st = n.level === null || n.level === undefined ? 'healthy' : n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      var words = 'Nozzle ' + n.number + ': ' + (st === 'healthy' ? 'healthy' : st === 'weak' ? 'weak (flow ' + sig(n.level, 2) + ')' : 'blocked') +
        ', at ' + mmInt(n.pos - o.edge) + ' from the strip edge';
      var focus = o.interactive === 'nozzles' ? ' tabindex="0" role="button" data-noz="' + n.index + '"' : ' tabindex="0" class="mark"';
      s += '<g class="noz ' + st + (o.interactive === 'nozzles' ? '' : ' mark') + '"' + focus + ' aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
        '<circle cx="' + X(n.pos) + '" cy="' + yN + '" r="' + r + '"/>' +
        (st === 'blocked' ? '<path d="M' + (X(n.pos) - r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) + r * .6) + ' ' + (yN + r * .6) +
          'M' + (X(n.pos) + r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) - r * .6) + ' ' + (yN + r * .6) + '" stroke="var(--card)" stroke-width="2"/>' : '') +
        '</g>';
      if (noz.length <= 40 && (n.number === 1 || n.number % 5 === 0)) {
        s += '<text x="' + X(n.pos) + '" y="' + (yN + r + 13) + '" font-size="11" text-anchor="middle" class="softtext">' + n.number + '</text>';
      }
    });
    // thermal profile of the roll (result only)
    if (hasTh) {
      var z = res.thermal_profile.z_m, d = res.thermal_profile.local_deviation_m;
      var mx = 0;
      d.forEach(function (v) { mx = Math.max(mx, Math.abs(v)); });
      var y0 = yTop - 14, k = mx > 0 ? 44 / mx : 0, pts = [];
      z.forEach(function (zz, i) { pts.push(X(zz).toFixed(1) + ',' + (y0 - d[i] * k).toFixed(1)); });
      s += '<line x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + y0 + '" y2="' + y0 + '" class="tick" stroke-dasharray="2 3"/>';
      s += '<polyline class="thermal" points="' + pts.join(' ') + '"/>';
      var ip = 0;
      d.forEach(function (v, i) { if (v > d[ip]) { ip = i; } });
      var tip = 'Roll grows most here (hot stripe): ' + um(d[ip]) + ' at ' + mmInt(z[ip] - o.edge) + ' from the strip edge';
      s += '<g class="mark" tabindex="0" aria-label="' + esc(tip) + '" data-tip="' + esc(tip) + '"><circle cx="' + X(z[ip]) + '" cy="' + (y0 - d[ip] * k) + '" r="5" fill="var(--orange)"/></g>';
      s += '<text x="' + (X(barrel) - 4) + '" y="' + (y0 - 30) + '" font-size="12" text-anchor="end">roll growth (line)</text>';
    }
    // strip
    s += '<rect class="strip" data-strip="1" x="' + X(o.edge) + '" y="' + yTop + '" width="' + (o.width * sx) + '" height="' + (yBot - yTop) + '"/>';
    // predicted positions (result)
    if (res && res.predicted) {
      var tol = res.tolerance_m || 0.01, placed = [];
      res.predicted.forEach(function (p) {
        var st = KIND_STYLE[p.kind] || {dash: '3 3', letter: '?', colour: 'var(--soft)'};
        p.positions_m.forEach(function (x) {
          var words = p.label + ' at ' + mmInt(x - o.edge) + ' from the strip edge (marked ' + st.letter + ')';
          // letters side by side when marks are close, so none hides another
          var lx = X(x), row = 0;
          while (row < 3 && placed.some(function (q) { return q.r === row && Math.abs(q.x - lx) < 11; })) { row += 1; }
          placed.push({x: lx, r: row});
          s += '<g class="mark" tabindex="0" aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
            '<rect class="pred" x="' + (X(x - tol)) + '" y="' + (yTop + 4) + '" width="' + Math.max(4, 2 * tol * sx) + '" height="' + (yBot - yTop - 8) +
            '" stroke="' + st.colour + '" stroke-dasharray="' + st.dash + '"/>' +
            '<text x="' + lx + '" y="' + (yTop - 4 - 13 * row) + '" font-size="12" font-weight="700" text-anchor="middle">' + st.letter + '</text></g>';
        });
      });
    }
    // observed bands
    var bands = o.bands || [];
    bands.forEach(function (b, i) {
      var w = Math.max(5, (b.w || 0.008) * sx);
      var words = 'Band ' + (i + 1) + ' (what you saw) at ' + mmInt(b.x - o.edge) + ' from the strip edge';
      var inter = o.interactive === 'bands';
      s += '<rect class="band' + (inter ? '' : ' mark') + '" tabindex="0"' + (inter ? ' role="slider" aria-valuemin="0" aria-valuemax="' +
        Math.round(o.width * 1000) + '" aria-valuenow="' + Math.round((b.x - o.edge) * 1000) + '" data-band="' + i + '"' : '') +
        ' aria-label="' + esc(words) + '" data-tip="' + esc(words) + '" x="' + (X(b.x) - w / 2) + '" y="' + (yTop + 2) +
        '" width="' + w + '" height="' + (yBot - yTop - 4) + '"/>';
      s += '<text x="' + X(b.x) + '" y="' + (yBot - 8) + '" font-size="12" font-weight="700" text-anchor="middle" fill="var(--card)" style="fill:var(--card);pointer-events:none">' + (i + 1) + '</text>';
    });
    // matches (result)
    if (res && res.matches) {
      var drawn = {};
      res.matches.forEach(function (m) {
        m.links.forEach(function (l) {
          if (!l.matched || l.predicted_m === null) { return; }
          var key = l.observed_m.toFixed(4);
          if (drawn[key]) { return; }
          drawn[key] = 1;
          var words = 'Your band at ' + mmInt(l.observed_m - o.edge) + ' lies within ' + mmInt(res.tolerance_m) +
            ' of: ' + m.label.toLowerCase() + ' at ' + mmInt(l.predicted_m - o.edge);
          s += '<g class="mark" tabindex="0" aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
            '<rect class="tol" x="' + X(l.observed_m - res.tolerance_m) + '" y="' + (yBot + 1) + '" width="' + (2 * res.tolerance_m * sx) + '" height="7"/>' +
            '<line class="link" x1="' + X(l.observed_m) + '" x2="' + X(l.predicted_m) + '" y1="' + (yBot + 4) + '" y2="' + (yTop + 6) + '"/></g>';
        });
      });
    }
    // ruler in mm from the strip edge on the header-start side
    var widthMm = o.width * 1000, pxPerMm = o.width * sx / widthMm;
    var step = [50, 100, 200, 250, 500].filter(function (st) { return st * pxPerMm >= 28; })[0] || 500;
    s += '<line class="tick" x1="' + X(o.edge) + '" x2="' + X(o.edge + o.width) + '" y1="' + yRul + '" y2="' + yRul + '"/>';
    for (var t = 0; t <= widthMm + 0.1; t += step) {
      var xx = X(o.edge + t / 1000);
      s += '<line class="tick" x1="' + xx + '" x2="' + xx + '" y1="' + yRul + '" y2="' + (yRul + 6) + '"/>';
      if (t % (step * 2) === 0 || step * pxPerMm >= 55) {
        s += '<text x="' + xx + '" y="' + (yRul + 19) + '" font-size="12" text-anchor="middle" class="softtext">' + t + '</text>';
      }
    }
    s += '<text x="' + X(o.edge) + '" y="' + (yRul + 36) + '" font-size="12" class="softtext">' + (W < 600 ? 'mm from the strip edge (header-start side)' : 'mm across the strip, from the edge on the side where the header starts (nozzle 1)') + '</text>';
    return s + '</svg>';
  }

  function legend(items) {
    return '<ul class="legend">' + items.map(function (it) {
      return '<li><svg viewBox="0 0 30 16" aria-hidden="true">' + it.icon + '</svg>' + esc(it.text) + '</li>';
    }).join('') + '</ul>';
  }
  var LEG_BAND = {icon: '<rect x="11" y="1" width="8" height="14" fill="var(--ink)"/>', text: 'Band you saw (solid)'};
  function legKind(k, label) {
    var st = KIND_STYLE[k] || {dash: '3 3', letter: '?', colour: 'var(--soft)'};
    return {icon: '<rect x="2" y="2" width="26" height="12" fill="none" stroke="' + st.colour + '" stroke-width="2" stroke-dasharray="' + st.dash + '"/>' +
      '<text x="15" y="12" font-size="10" font-weight="700" text-anchor="middle">' + st.letter + '</text>', text: st.letter + ': ' + label};
  }

  function bandsList() {
    var pos = Array.isArray(val('band_positions')) ? val('band_positions') : [];
    return pos;
  }
  function nozzlesFor(levels) {
    var g = geometry();
    return g.nozzle_positions_m.map(function (p, i) {
      return {pos: p, index: i, number: i + 1, level: Array.isArray(levels) ? levels[i] : 1};
    });
  }

  function bandsInput(q, ctx) {
    var g = geometry();
    var pos = bandsList();
    var bw = val('band_width');
    var bands = pos.map(function (mm) { return {x: g.strip_edge_m + mm / 1000, w: isNum(bw) ? bw / 1000 : null}; });
    var svg = drawStrip({id: 'strip-input', label: 'Top view of the strip. Click or tap on the strip to add a band; drag a band to move it; with the keyboard use the arrow keys on a band, Delete removes it.',
      barrel: g.barrel_length_m, edge: g.strip_edge_m, width: g.strip_width_m,
      nozzles: nozzlesFor(val('nozzle_levels')), bands: bands, interactive: 'bands'});
    var list = '<ol class="poslist" aria-label="Band positions">' + pos.map(function (mm, i) {
      return '<li><label for="bp-' + i + '">Band ' + (i + 1) + '</label><input type="number" step="1" id="bp-' + i + '" data-bandpos="' + i +
        '" value="' + esc(mm) + '"><span class="unit">mm</span><button type="button" class="btn" data-band-del="' + i +
        '" aria-label="Delete band ' + (i + 1) + '">Delete</button></li>';
    }).join('') + '</ol>';
    return '<div class="drawing"><div>' + svg + legend([LEG_BAND, {icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)"/>', text: 'Coolant nozzle (for orientation)'}]) +
      '</div><div class="side">' + (pos.length ? list : '<p class="empty">No bands placed yet. Click on the strip, or add one here.</p>') +
      '<div class="numrow"><label class="sr" for="bp-new">New band position in mm</label><input type="number" step="1" id="bp-new" placeholder="mm from edge">' +
      '<button type="button" class="btn" data-band-add="1">Add band</button></div>' +
      '<p class="small soft">Strip ' + mmInt(g.strip_width_m) + ' wide. ' + (pos.length ? '<button type="button" class="btn link" data-band-clear="1">Clear all ("Don\'t know")</button>' : '') + '</p></div></div>';
  }

  function nozzleInput(q, ctx) {
    var g = geometry();
    if (!g.nozzle_positions_m.length) {
      return '<p class="empty">This starting point has no spray header model, so nozzles cannot be marked here.</p>';
    }
    var levels = val('nozzle_levels');
    var svg = drawStrip({id: 'strip-nozzles', label: 'Spray header over the strip. Click a nozzle to cycle healthy, weak and blocked; with the keyboard press Enter or Space on a nozzle.',
      barrel: g.barrel_length_m, edge: g.strip_edge_m, width: g.strip_width_m,
      nozzles: nozzlesFor(levels), bands: bandsList().map(function (mm) { return {x: g.strip_edge_m + mm / 1000}; }),
      interactive: 'nozzles'});
    var lst = '';
    if (Array.isArray(levels)) {
      lst = '<details class="more"><summary>Nozzle list (flow level of each nozzle, 1 = full, 0 = blocked)</summary><div class="nozlist">' +
        levels.map(function (lv, i) {
          return '<label for="nz-' + i + '">Nozzle ' + (i + 1) + '<input type="number" min="0" max="1" step="0.05" id="nz-' + i + '" data-nozlevel="' + i + '" value="' + esc(lv) + '"></label>';
        }).join('') + '</div></details>';
    }
    var weak = Array.isArray(levels) ? levels.filter(function (x) { return x > 0 && x < 1; }).length : 0;
    var blocked = Array.isArray(levels) ? levels.filter(function (x) { return x <= 0; }).length : 0;
    return '<div>' + svg + legend([{icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Healthy'},
      {icon: '<circle cx="15" cy="8" r="6" fill="url(#half)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Weak (flow ' + M.weak_nozzle_level + ')'},
      {icon: '<circle cx="15" cy="8" r="6" fill="var(--ink)" stroke="var(--ink)"/>', text: 'Blocked'}, LEG_BAND]) +
      '<p class="small" aria-live="polite">' + (Array.isArray(levels) ? (weak + ' weak, ' + blocked + ' blocked of ' + levels.length +
      ' nozzles. <button type="button" class="btn link" data-noz-reset="1">Set back to "Don\'t know"</button>') :
      'Nozzle state: "Don\'t know" (nobody has checked). Click a nozzle to mark it; the others then count as healthy.') + '</p>' +
      (Array.isArray(levels) ? '' : '<button type="button" class="btn" data-noz-init="1">All nozzles checked and healthy</button>') + lst + '</div>';
  }

  // ------------------------------------------------------------------ tooltips
  var tipEl = null;
  function showTip(target) {
    var t = target.getAttribute('data-tip');
    if (!t) { return; }
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'tip'; tipEl.setAttribute('role', 'tooltip'); document.body.appendChild(tipEl); }
    tipEl.textContent = t;
    var r = target.getBoundingClientRect();
    tipEl.style.display = 'block';
    var x = Math.min(window.innerWidth - tipEl.offsetWidth - 8, Math.max(8, r.left + r.width / 2 - tipEl.offsetWidth / 2));
    var y = r.top - tipEl.offsetHeight - 8;
    if (y < 8) { y = r.bottom + 8; }
    tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
  }
  function hideTip() { if (tipEl) { tipEl.style.display = 'none'; } }
  // ------------------------------------------------------------------ pictograms (one per cause)
  // Simple labelled sketches of the mechanism in each cause's description; no added physics.
  var STRK = ' fill="none" stroke="var(--ink)" stroke-width="2"';
  function T(x, y, s, a) { return '<text class="lbl" x="' + x + '" y="' + y + '" font-size="9"' + (a ? ' text-anchor="' + a + '"' : '') + '>' + s + '</text>'; }
  function strip(y) { return '<rect x="6" y="' + y + '" width="108" height="14" fill="var(--strip)" stroke="var(--strip-edge)"/>'; }
  function roll(cx, cy, r) { return '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>'; }
  var PICTOS = {
    nozzle: '<rect x="8" y="6" width="104" height="6" fill="var(--soft)"/>' +
      [20, 46, 72, 98].map(function (x, i) {
        return i === 2 ? '<circle cx="' + x + '" cy="16" r="5" fill="var(--ink)"/><path d="M' + (x - 3) + ' 13l6 6m0-6l-6 6" stroke="var(--card)" stroke-width="1.5"/>'
          : '<circle cx="' + x + '" cy="16" r="5" fill="var(--card)" stroke="var(--ink)"/><path d="M' + x + ' 21l-10 22h20z" fill="var(--blue)" opacity=".3"/>';
      }).join('') + '<rect x="6" y="44" width="108" height="16" rx="3" fill="var(--panel)" stroke="var(--ink)"/>' +
      '<path d="M60 44q12-9 24 0" fill="var(--orange)" stroke="var(--orange)"/>' + strip(62) + T(72, 36, 'blocked', 'middle') + T(110, 75, 'loose band', 'end'),
    zone_valve: '<rect x="8" y="6" width="104" height="6" fill="var(--soft)"/><path d="M62 4l12 10v-10l-12 10z" fill="var(--ink)"/>' +
      '<rect x="6" y="40" width="108" height="16" rx="3" fill="var(--panel)" stroke="var(--ink)"/><path d="M56 40q12-8 24 0" fill="var(--orange)" stroke="var(--orange)"/>' +
      '<circle cx="24" cy="26" r="9"' + STRK + '/><path d="M24 26v-6m0 6h5"' + STRK + '/>' + strip(60) + T(80, 28, 'valve off') + T(110, 74, 'comes and goes', 'end'),
    roll_band: '<ellipse cx="60" cy="30" rx="50" ry="16" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' +
      '<rect x="64" y="14" width="10" height="32" fill="url(#hatch)" stroke="var(--ink)"/>' + strip(54) + '<rect x="64" y="54" width="10" height="14" fill="var(--ink)" opacity=".5"/>' +
      T(78, 12, 'worn band') + T(110, 78, 'same place', 'end'),
    grinder: '<ellipse cx="54" cy="30" rx="46" ry="16" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' +
      [20, 30, 40, 50, 60, 70, 80].map(function (x) { return '<path d="M' + x + ' 16l8 28" stroke="var(--soft)"/>'; }).join('') +
      '<circle cx="106" cy="28" r="10"' + STRK + '/>' + strip(56) + T(106, 50, 'grinder', 'middle') + T(8, 78, 'fine spiral lines'),
    coil_ridge: '<circle cx="44" cy="38" r="30"' + STRK + '/><circle cx="44" cy="38" r="20"' + STRK + '/><circle cx="44" cy="38" r="9"' + STRK + '/>' +
      '<path d="M44 8q6-5 0-10M44 18q6-5 0-10" stroke="var(--orange)" stroke-width="3" fill="none"/>' + T(80, 20, 'ridge builds') + T(80, 32, 'up wrap on') + T(80, 44, 'wrap'),
    troughs: roll(14, 40, 10) + roll(106, 40, 10) + '<path d="M14 30h92M14 50h92" stroke="var(--strip-edge)"/>' +
      '<path d="M24 36q10 4 20 0t20 0t20 0t18 0M24 44q10 4 20 0t20 0t20 0t18 0" fill="none" stroke="var(--ink)"/>' + T(60, 70, 'troughs in the free span', 'middle'),
    profile: '<path d="M8 50q10-14 20 0t20 0h40q10 14 20 0t4 0" fill="none" stroke="var(--ink)" stroke-width="2"/>' +
      '<rect x="8" y="56" width="104" height="10" fill="var(--strip)" stroke="var(--strip-edge)"/>' + T(60, 24, 'edge waves', 'middle') + T(60, 78, 'across the width', 'middle'),
    oil_film: roll(60, 20, 16) + '<path d="M10 40h100" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M44 37q8-5 16 0" stroke="var(--blue)" stroke-width="3" fill="none"/>' +
      '<rect x="70" y="44" width="12" height="20" fill="var(--soft)" opacity=".45"/>' + strip(60) + T(8, 56, 'thin film') + T(110, 78, 'milky streak', 'end'),
    drips: '<rect x="20" y="6" width="80" height="8" fill="var(--soft)"/>' +
      [40, 62, 84].map(function (x) { return '<path d="M' + x + ' 18q-5 9 0 12q5-3 0-12z" fill="var(--blue)"/>'; }).join('') +
      strip(48) + '<ellipse cx="62" cy="55" rx="10" ry="4" fill="var(--soft)" opacity=".6"/>' + T(60, 76, 'stain after annealing', 'middle'),
    tension_lines: strip(26) + '<rect x="6" y="26" width="108" height="30" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      [16, 22, 28, 34, 40, 46].map(function (y) { return '<path d="M10 ' + (y + 10) + 'h100" stroke="var(--ink)" stroke-width=".8"/>'; }).join('') +
      '<path d="M8 66h20m-6-4l6 4-6 4" stroke="var(--ink)" fill="none"/>' + T(34, 70, 'low tension: fine lines'),
    chatter: roll(40, 18, 12) + roll(40, 52, 12) + '<path d="M58 14q4 4 0 8M64 10q6 8 0 16M58 48q4 4 0 8M64 44q6 8 0 16" fill="none" stroke="var(--orange)" stroke-width="2"/>' +
      '<path d="M4 35h112" stroke="var(--strip-edge)" stroke-width="5"/>' + [76, 86, 96, 106].map(function (x) { return '<path d="M' + x + ' 31v8" stroke="var(--ink)" stroke-width="2"/>'; }).join('') +
      T(72, 76, 'gap opens and closes'),
    stack_resonance: roll(30, 12, 9) + roll(30, 30, 6) + roll(30, 44, 6) + roll(30, 62, 9) +
      '<path d="M44 26v-6m0 0l-3 4m3-4l3 4M44 40v-6m0 0l-3 4m3-4l3 4" stroke="var(--orange)" stroke-width="2" fill="none"/>' +
      '<path d="M52 37h64" stroke="var(--strip-edge)" stroke-width="4"/>' + T(58, 20, 'work rolls move') + T(58, 30, 'together (600-1200 Hz)'),
    work_roll_mark: roll(30, 26, 18) + '<circle cx="30" cy="44" r="3" fill="var(--orange)"/>' + '<path d="M4 50h112" stroke="var(--strip-edge)" stroke-width="5"/>' +
      [30, 72, 114].map(function (x) { return '<path d="M' + x + ' 46v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      '<path d="M30 62h42m-4-3l4 3-4 3" stroke="var(--ink)" fill="none"/>' + T(34, 76, 'once per work-roll turn'),
    backup_roll_mark: roll(32, 20, 17) + roll(32, 45, 8) + '<circle cx="32" cy="3" r="3" fill="var(--orange)"/>' +
      '<path d="M4 56h112" stroke="var(--strip-edge)" stroke-width="5"/>' + [40, 100].map(function (x) { return '<path d="M' + x + ' 52v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      T(56, 22, 'mark on backup roll') + T(60, 74, 'once per backup-roll turn', 'middle'),
    bearing_gear: '<circle cx="34" cy="36" r="20"' + STRK + '/>' +
      [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(function (a) {
        var r = a * Math.PI / 180; return '<path d="M' + (34 + 20 * Math.cos(r)).toFixed(1) + ' ' + (36 + 20 * Math.sin(r)).toFixed(1) + 'L' + (34 + 26 * Math.cos(r)).toFixed(1) + ' ' + (36 + 26 * Math.sin(r)).toFixed(1) + '" stroke="var(--ink)" stroke-width="3"/>';
      }).join('') + '<circle cx="34" cy="36" r="6" fill="var(--ink)"/>' + T(66, 30, 'fixed multiple') + T(66, 42, 'of roll turns'),
    drive_twist: '<rect x="6" y="28" width="24" height="20" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' + roll(102, 38, 12) +
      '<path d="M30 38h60" stroke="var(--ink)" stroke-width="4"/><path d="M50 26q8 12 0 24M62 26q8 12 0 24" fill="none" stroke="var(--orange)" stroke-width="2"/>' +
      T(18, 22, 'motor', 'middle') + T(60, 66, 'shaft twists 5-30 Hz', 'middle'),
    coil_mark: '<circle cx="34" cy="38" r="28"' + STRK + '/><circle cx="34" cy="38" r="8"' + STRK + '/><path d="M34 10v8" stroke="var(--orange)" stroke-width="4"/>' +
      '<path d="M62 38h54" stroke="var(--strip-edge)" stroke-width="5"/>' + [70, 110].map(function (x) { return '<path d="M' + x + ' 34v8" stroke="var(--ink)" stroke-width="2.5"/>'; }).join('') +
      T(90, 26, 'once per coil turn', 'middle'),
    yield_bend: roll(60, 46, 16) + '<path d="M6 22q40 0 54 8q14 8 54-8" fill="none" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M44 20l3 8M52 22l3 8M66 22l3 8" stroke="var(--ink)"/>' + T(60, 76, 'yields unevenly when bent', 'middle'),
    herringbone: strip(22) + '<rect x="6" y="22" width="108" height="36" fill="var(--strip)" stroke="var(--strip-edge)"/>' +
      [20, 44, 68, 92].map(function (x) { return '<path d="M' + x + ' 26l10 14-10 14" fill="none" stroke="var(--ink)" stroke-width="2"/>'; }).join('') +
      T(60, 72, 'V-shaped marks', 'middle'),
    skid: roll(40, 24, 16) + '<path d="M4 44h112" stroke="var(--strip-edge)" stroke-width="6"/>' +
      '<path d="M60 24h22m-5-4l5 4-5 4M60 52h12m-4-3l4 3-4 3" stroke="var(--orange)" stroke-width="2" fill="none"/>' +
      '<path d="M84 40l6 8M92 40l3 8" stroke="var(--ink)"/>' + T(86, 22, 'roll slides') + T(60, 74, 'skid marks', 'middle')
  };
  function picto(key, big) {
    return '<svg viewBox="0 0 120 80" class="' + (big ? 'big' : 'mini') + '" role="img" aria-label="' + esc(big ? 'Sketch of this cause' : '') + '"' +
      (big ? '' : ' aria-hidden="true"') + '><defs><pattern id="hatch-' + key + '" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="2" height="5" fill="var(--soft)"/></pattern></defs>' + (PICTOS[key] || '').replace(/url\(#hatch\)/g, 'url(#hatch-' + key + ')') +
      '</svg>';
  }

  // ------------------------------------------------------------------ along the strip
  function alongSvg(av, names) {
    var L = av.strip_length_m || 1, w = drawW(), sx = (w - 40) / L, H = 150;
    function X(m) { return 20 + m * sx; }
    var s = '<svg viewBox="0 0 ' + w + ' ' + H + '" role="group" aria-label="Marks along a length of strip: what you measured against the spacing of the best-fitting candidate">';
    s += '<rect class="strip" x="20" y="20" width="' + (w - 40) + '" height="44"/><rect class="strip" x="20" y="82" width="' + (w - 40) + '" height="44"/>';
    s += '<text x="20" y="14" font-size="13" font-weight="700">What you measured' + (isNum(av.observed_pitch_m) ? ': spacing ' + sig(av.observed_pitch_m * 1000, 3) + ' mm' +
      (isNum(av.observed_at_exit_speed_m_s) ? ' at ' + mpm(av.observed_at_exit_speed_m_s) : '') : ': no spacing entered') + '</text>';
    if (isNum(av.observed_pitch_m) && av.observed_pitch_m > 0) {
      for (var x = 0; x <= L + 1e-9 && x / av.observed_pitch_m < 400; x += av.observed_pitch_m) {
        s += '<line x1="' + X(x) + '" x2="' + X(x) + '" y1="22" y2="62" stroke="var(--ink)" stroke-width="2.5"/>';
      }
    }
    var nm = av.hypothesis_name || 'no candidate with a spacing';
    s += '<text x="20" y="77" font-size="13" font-weight="700">' + esc(nm) + (isNum(av.predicted_pitch_m) ? ': spacing ' + sig(av.predicted_pitch_m * 1000, 3) + ' mm (model)' : '') + '</text>';
    if (isNum(av.predicted_pitch_m) && av.predicted_pitch_m > 0) {
      for (var y = 0; y <= L + 1e-9 && y / av.predicted_pitch_m < 400; y += av.predicted_pitch_m) {
        s += '<line x1="' + X(y) + '" x2="' + X(y) + '" y1="84" y2="124" stroke="var(--orange)" stroke-width="2.5" stroke-dasharray="5 3"/>';
      }
    }
    var step = L <= 1 ? 0.1 : L <= 5 ? 0.5 : 1;
    for (var t = 0; t <= L + 1e-9; t += step) {
      s += '<line class="tick" x1="' + X(t) + '" x2="' + X(t) + '" y1="128" y2="134"/><text x="' + X(t) + '" y="146" font-size="12" text-anchor="middle" class="softtext">' + sig(t, 3) + ' m</text>';
    }
    return s + '</svg>';
  }

  // ------------------------------------------------------------------ thinner or thicker
  function shortLabel(l) { return String(l || '').split(' ')[0]; }
  function multiples(gv) {
    return '<div class="multiples">' + gv.quantities.map(function (qt) {
      var f = qt.unit === 'um' ? 1e6 : qt.unit === 'mpa' ? 1e-6 : 1;
      var ps = gv.passes, n = ps.length, w = 300, h = 170, l = 46, r = 12, t = 16, b = 46;
      var vals = ps.map(function (p) { var v = p.values[qt.key]; return isNum(v) && !p.not_credible ? v * f : null; });
      var ok = vals.filter(isNum);
      var lo = Math.min.apply(null, ok.concat([0])), hi = Math.max.apply(null, ok.concat([0]));
      if (hi === lo) { hi = lo + 1; }
      function X(i) { return l + (n === 1 ? (w - l - r) / 2 : i * (w - l - r) / (n - 1)); }
      function Y(v) { return t + (hi - v) / (hi - lo) * (h - t - b); }
      var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(qt.label + ' for each pass, thickest on the left, thinnest on the right') + '">';
      ps.forEach(function (p, i) {
        if (p.not_credible || p.no_bite) {
          s += '<rect x="' + (X(i) - 14) + '" y="' + t + '" width="28" height="' + (h - t - b) + '" fill="url(#mh)" opacity=".7"/>' +
            '<text x="' + X(i) + '" y="' + (t + 12) + '" font-size="9" text-anchor="middle">' + (p.not_credible ? 'not credible' : 'no result') + '</text>';
        }
      });
      s += '<defs><pattern id="mh" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="6" fill="var(--soft)"/></pattern></defs>';
      s += '<line class="tick" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
      s += '<text x="' + (l - 4) + '" y="' + (Y(hi) + 4) + '" font-size="10" text-anchor="end" class="softtext">' + sig(hi, 3) + '</text>';
      s += '<text x="' + (l - 4) + '" y="' + (Y(lo) + 4) + '" font-size="10" text-anchor="end" class="softtext">' + sig(lo, 3) + '</text>';
      var pts = [];
      vals.forEach(function (v, i) { if (isNum(v)) { pts.push(X(i) + ',' + Y(v)); } });
      if (pts.length > 1) { s += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="var(--blue)" stroke-width="2"/>'; }
      vals.forEach(function (v, i) {
        if (isNum(v)) {
          var words = ps[i].label + ': ' + sig(v, 3) + ' ' + qt.unit_label + ' (' + ps[i].credibility_words + ')';
          s += '<g class="mark" tabindex="0" data-tip="' + esc(words) + '" aria-label="' + esc(words) + '"><circle cx="' + X(i) + '" cy="' + Y(v) + '" r="4.5" fill="var(--blue)"/></g>';
        }
        s += '<text x="' + X(i) + '" y="' + (h - b + 16) + '" font-size="10" text-anchor="middle">' + esc(shortLabel(ps[i].label)) + '</text>';
        s += '<text x="' + X(i) + '" y="' + (h - b + 29) + '" font-size="9" text-anchor="middle" class="softtext">' + esc(gauge(ps[i].exit_thickness_m)) + '</text>';
      });
      s += '<text x="' + (w - r) + '" y="' + (h - 4) + '" font-size="9" text-anchor="end" class="softtext">thinner →</text>';
      return '<figure><figcaption>' + esc(qt.label) + ' (' + esc(qt.unit_label) + ')</figcaption>' + s + '</svg><p class="small soft">' + esc(qt.reading) + '</p></figure>';
    }).join('') + '</div>';
  }

  // ------------------------------------------------------------------ temperature
  function tempSvg(tv) {
    var rows = tv.rows, n = rows.length, w = 640, h = 220, l = 46, r = 16, t = 20, b = 50;
    var lim = tv.battery_limits_apply && tv.coil_limits_c ? tv.coil_limits_c.leaving_final_pass : null;
    var hi = Math.max.apply(null, rows.map(function (x) { return x.value_c; }).concat([lim || 0, 100]));
    function Y(v) { return t + (1 - v / hi) * (h - t - b); }
    var bw = Math.min(60, (w - l - r) / n * 0.6);
    var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Modelled strip exit temperature per pass' + (lim ? ' against the published coil limit of ' + lim + ' °C' : '') + '">';
    s += '<line class="tick" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
    rows.forEach(function (x, i) {
      var cx = l + (i + 0.5) * (w - l - r) / n;
      s += '<g class="mark" tabindex="0" data-tip="' + esc(x.label + ': ' + degc(x.value_c)) + '" aria-label="' + esc(x.label + ': ' + degc(x.value_c)) + '">' +
        '<rect x="' + (cx - bw / 2) + '" y="' + Y(x.value_c) + '" width="' + bw + '" height="' + (Y(0) - Y(x.value_c)) + '" fill="' + (x.is_final_pass ? 'var(--ink)' : 'var(--soft)') + '"/></g>';
      s += '<text x="' + cx + '" y="' + (Y(x.value_c) - 4) + '" font-size="11" text-anchor="middle">' + degc(x.value_c) + '</text>';
      s += '<text x="' + cx + '" y="' + (h - b + 16) + '" font-size="10" text-anchor="middle">' + esc(shortLabel(x.label)) + (x.is_final_pass ? ' (final)' : '') + '</text>';
    });
    if (lim) {
      s += '<line x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(lim) + '" y2="' + Y(lim) + '" stroke="var(--red)" stroke-width="2" stroke-dasharray="7 4"/>' +
        '<text x="' + (w - r) + '" y="' + (Y(lim) - 5) + '" font-size="11" text-anchor="end">published coil limit leaving the final pass: ' + lim + ' °C</text>';
    }
    return s + '</svg>';
  }
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
    h += '<h3>The route</h3>' + renderQ(Q.route);
    var rest = M.questions.filter(function (q) {
      return q.step === 'rolling' && !q.ask_first && ['product', 'alloy', 'temper', 'route'].indexOf(q.id) < 0 && shown(q);
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
        '<span class="t">' + esc(x.label) + '</span><span class="small soft">' + esc(x.description) + '</span></label>';
    });
    h += '<label class="preset" for="casefile"><span class="t">Open a case file</span><span class="small soft">A band case JSON file from this tool or the template. It is checked, not stored.</span>' +
      '<input type="file" id="casefile" accept=".json,application/json" style="margin-top:.4rem;max-width:100%"></label></div></fieldset>';
    if (!M.worked_examples_available) { h += '<p class="small soft">Worked examples are not available in this installation (they come with the source folder).</p>'; }
    if (p.generated_by_model) { h += '<p class="banner">Worked example: its observations were generated by the model, not seen on a plant.</p>'; }
    h += '<div class="q" data-q="own_mill"><label class="chip"><input type="checkbox" id="ownmill"' + (S.answers.own_mill ? ' checked' : '') +
      '> These are my mill\'s real values</label><p class="help">Tick this only when the mill values below are your mill\'s. Without it the case counts as synthetic and the trust level stays low.</p></div>';
    h += '<h3>The key mill values</h3>';
    h += M.questions.filter(function (q) { return q.step === 'mill' && q.ask_first && q.kind !== 'nozzles' && shown(q); })
      .map(function (q) { return renderQ(q); }).join('');
    h += '<h3>Spray header</h3>' + renderQ(Q.nozzle_levels);
    var rest = M.questions.filter(function (q) { return q.step === 'mill' && !q.ask_first && shown(q); });
    h += '<details class="more" data-more="mill"' + (S.openMore && S.openMore.mill ? ' open' : '') + '><summary>More details (' + rest.length + ' more values)</summary>' +
      groupBy(rest).map(function (g) { return '<h4>' + esc(g.group) + '</h4>' + g.qs.map(function (q) { return renderQ(q); }).join(''); }).join('') + '</details>';
    h += '<div class="q"><label class="w" for="casename">Name for this case</label><input type="text" class="wide" id="casename" value="' + esc(S.answers.name || '') +
      '" placeholder="for example coil 4711, stand 2" style="padding:.4rem;border:1px solid var(--line);border-radius:5px;width:min(26rem,100%)"></div>';
    return h;
  }

  function sideText() {
    var f = family(), parts = [];
    var o = val('orientation');
    if (f === 'lengthwise') {
      var n = bandsList().length, c = val('continuity');
      var cw = {continuous: 'always there', intermittent: 'come and go', both: 'some always there, some come and go'}[c];
      parts.push('Lengthwise bands' + (n ? ' at ' + n + ' position' + (n > 1 ? 's' : '') : '') + (cw ? ', ' + cw : '') + '.');
    } else if (f === 'transverse') {
      var po = val('pitch_observations');
      parts.push((o === 'transverse' ? 'Marks across the strip' : 'Marks: ' + o) + (Array.isArray(po) && po.length ? ', spacing measured at ' + po.length + ' speed' + (po.length > 1 ? 's' : '') : '') + '.');
    } else {
      parts.push('Direction of the marks: not given yet.');
    }
    var g = val('exit_gauge'), sp = val('exit_speed'), prod = val('product');
    var pname = '';
    if (prod) { M.products.forEach(function (gr) { gr.products.forEach(function (p) { if (p.id === prod) { pname = p.name.toLowerCase(); } }); }); }
    parts.push((isNum(g) ? (g < 1000 ? sig(g, 3) + ' µm' : sig(g / 1000, 3) + ' mm') + ' ' : '') + (pname || 'strip') + (isNum(sp) ? ' at ' + sig(sp, 3) + ' m/min' : '') + '.');
    var oc = originCounts();
    parts.push(preset().label + (oc.measured || oc.estimated ? ', ' + oc.measured + ' value' + (oc.measured === 1 ? '' : 's') + ' measured, ' + oc.estimated + ' estimated' : ', no values of your own yet') +
      (S.answers.own_mill ? ' (marked as your mill)' : '') + '.');
    return parts;
  }

  function updateSide() {
    var box = document.getElementById('side');
    if (!box) { return; }
    var a = askFirstUnknown();
    var st = S.generalError ? '<p class="err" role="alert">' + esc(S.generalError) + '</p>' :
      Object.keys(S.errors).length ? '<p class="err" role="alert">One answer needs a look: ' + esc(Object.keys(S.errors).map(function (k) { return Q[k] ? Q[k].wording : k; }).join(', ')) + '</p>' :
      S.check ? '<p class="small">The tool accepts these inputs.</p>' : '<p class="small soft">Checking the inputs…</p>';
    box.innerHTML = '<h2>What the tool has so far</h2><ul>' + sideText().map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
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
  // ------------------------------------------------------------------ running view
  function renderRunning(st) {
    var run = st.run;
    var prof = M.profiles[run.profile] || {label: run.profile, left_out: []};
    var queued = run.status === 'queued';
    var el_ = run.elapsed_s;
    app.innerHTML = '<div class="wrap"><section class="card running" aria-live="polite"><div class="runhead"><div class="spinner" aria-hidden="true"></div><div>' +
      '<h2>' + (queued ? 'Waiting to start' : 'Running the screening') + '</h2><p class="soft">' + esc(prof.label) + ' run' +
      (run.changes && run.changes.length ? ' of a what-if (' + esc(run.changes.join(', ')) + ')' : '') + '.' +
      (queued && st.queue_position ? ' Place in the queue: ' + st.queue_position + '.' : '') + '</p></div></div>' +
      '<p class="elapsed num" id="elapsed">' + (isNum(el_) ? Math.round(el_) + ' s' : '0 s') + '</p>' +
      '<p>The tool works through these steps (one run at a time on this computer):</p><ol class="stages">' +
      M.stages.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ol>' +
      (prof.left_out && prof.left_out.length ? '<p class="small soft">This quick run leaves out: ' + esc(prof.left_out.join('; ')) + '.</p>' : '') +
      '<p class="small soft">A quick run takes about 5 to 20 seconds on the demo cases, a detailed run up to a few minutes.</p>' +
      (queued ? '<button type="button" class="btn" data-cancel="' + run.id + '">Cancel this run</button>' : '') +
      ' <button type="button" class="btn" data-back-input="1">Back to the answers</button></section></div>';
  }

  function renderFailed(st) {
    var run = st.run, e = run.error || {text: 'The run did not finish.'};
    var q = e.question && Q[e.question];
    var title = run.status === 'cancelled' ? 'This run was cancelled' : run.status === 'interrupted' ? 'This run was interrupted' : 'The screening could not be run';
    var calm = run.status === 'cancelled' || run.status === 'interrupted';
    app.innerHTML = '<div class="wrap"><section class="card ' + (calm ? 'banner' : 'errorbox') + '" role="' + (calm ? 'status' : 'alert') + '"><h2>' + title + '</h2><p>' + esc(e.text || '') + '</p>' +
      (q ? '<p>The answer to look at: <strong>' + esc(q.wording) + '</strong>.</p><button type="button" class="btn primary" data-goto="' + q.id + '">Go to this question</button> ' : '') +
      '<button type="button" class="btn" data-back-input="1">Back to the answers</button> ' +
      '<button type="button" class="btn" data-rerun="' + run.id + '" data-profile="' + run.profile + '">Run the same inputs again</button></section></div>';
  }

  // ------------------------------------------------------------------ result view
  var SCLASS = {CONSISTENT_LEADING: 's-best', CONSISTENT: 's-fits', WEAKENED: 's-weak', NOT_ASSESSABLE: 's-none', CONTRADICTED: 's-no'};
  var SICON = {CONSISTENT_LEADING: '★', CONSISTENT: '✓', WEAKENED: '▽', NOT_ASSESSABLE: '?', CONTRADICTED: '✕'};

  function standWords(c) {
    return '<span class="stand ' + SCLASS[c.standing] + '"><span aria-hidden="true">' + SICON[c.standing] + '</span>' + esc(c.standing_words) + '</span>';
  }

  function barsHtml(sum, ids, opts) {
    opts = opts || {};
    var by = {}, old = {};
    sum.causes.forEach(function (c) { by[c.id] = c; });
    if (opts.old) { opts.old.causes.forEach(function (c) { old[c.id] = c; }); }
    var scores = [0, 1];
    ids.forEach(function (id) { if (by[id]) { scores.push(by[id].score); } if (old[id]) { scores.push(old[id].score); } });
    var lo = Math.min.apply(null, scores), hi = Math.max.apply(null, scores);
    var span = hi - lo, z = (0 - lo) / span * 100;
    function pos(sc) { var a = (Math.min(sc, 0) - lo) / span * 100, b = (Math.max(sc, 0) - lo) / span * 100; return {left: a, width: Math.max(b - a, 0.6)}; }
    var h = '<div class="axis" aria-hidden="true"><span></span><span></span><span class="ax"><span>' + (lo < 0 ? '← does not fit (' + lo + ')' : '0') + '</span><span>fits (' + hi + ') →</span></span><span>score</span></div>';
    h += '<div class="bars" role="list">';
    ids.forEach(function (id) {
      var c = by[id];
      if (!c) { return; }
      var start = opts.old && old[id] ? pos(old[id].score) : pos(c.score);
      var end = pos(c.score);
      var oldMark = opts.old && old[id] && old[id].score !== c.score ? '<span class="old" style="left:' + pos(old[id].score).left + '%;width:' + pos(old[id].score).width + '%" title="before"></span>' : '';
      var label = c.name + ': ' + c.standing_words + ', score ' + c.score + (opts.old && old[id] && old[id].score !== c.score ? ' (before ' + old[id].score + ')' : '');
      h += '<div role="listitem"><button type="button" class="bar' + (opts.old && old[id] && (old[id].score !== c.score || old[id].standing !== c.standing) ? ' changed' : '') + '" data-cause="' + id + '" aria-expanded="' + (S.openCause === id && !opts.compact ? 'true' : 'false') + '" aria-label="' + esc(label) + '"' + (opts.compact ? ' tabindex="-1"' : '') + '>' +
        '<span class="pic">' + picto(c.pictogram) + '</span><span class="nm"><b>' + esc(c.name) + '</b>' + standWords(c) + '</span>' +
        '<span class="track"><span class="zero" style="left:' + z + '%"></span>' + oldMark +
        '<span class="fill ' + SCLASS[c.standing] + '" data-left="' + end.left + '" data-width="' + end.width + '" style="left:' + start.left + '%;width:' + start.width + '%"></span></span>' +
        '<span class="score num">' + c.score + (opts.old && old[id] && old[id].score !== c.score ? '<br><span class="small soft">was ' + old[id].score + '</span>' : '') + '</span></button>';
      if (S.openCause === id && !opts.compact) { h += causeDetail(c); }
      h += '</div>';
    });
    return h + '</div>';
  }

  function evidList(items, empty) {
    if (!items.length) { return '<p class="empty">' + esc(empty) + '</p>'; }
    return '<ul class="evid">' + items.map(function (e) {
      return '<li><span class="lab">' + esc(e.label.charAt(0).toUpperCase() + e.label.slice(1)) + '</span> <span class="w">(' + esc(e.weight_words) + '; from ' + esc(e.basis_words) + ')</span><br>' +
        '<span class="small">Seen or computed: ' + esc(e.observed_words) + '. This cause needs: ' + esc(e.expected_words) + '.</span></li>';
    }).join('') + '</ul>';
  }

  function causeDetail(c) {
    var nl = c.not_looked_at.length ? '<ul class="evid">' + c.not_looked_at.map(function (x) {
      var qs = x.questions.filter(function (q) { return Q[q]; });
      return '<li>' + esc(x.label.charAt(0).toUpperCase() + x.label.slice(1)) + (qs.length ? ' <button type="button" class="btn link" data-answer="' + esc(qs.join(',')) + '">Answer this</button>' : '') +
        (S.openChecks['nl-' + c.id + '-' + qs.join(',')] ? inlineQs(qs) : '') + '</li>';
    }).join('') + '</ul>' : '<p class="empty">Everything this cause looks at has an answer.</p>';
    return '<div class="detail" id="detail-' + c.id + '"><div class="top"><div>' + picto(c.pictogram, true) + '</div><div><h3>' + esc(c.name) + '</h3>' +
      '<p>' + esc(c.description) + '</p><p>' + standWords(c) + ' <span class="num small">score ' + c.score + ', place ' + c.rank + ' of 20</span></p></div></div>' +
      '<div class="cols"><div><h4>Fits because</h4>' + evidList(c.fits_because, 'Nothing entered speaks for it yet.') + '</div>' +
      '<div><h4>Speaks against</h4>' + evidList(c.speaks_against, 'Nothing entered speaks against it.') + '</div></div>' +
      '<h4>Not looked at yet</h4>' + nl + '<h4>How to check on the floor</h4><p>' + esc(c.how_to_check) + '</p></div>';
  }

  // inline answers for the check-and-update loop (edits pending changes of the shown run)
  var PEND = {get: function (id) {
    if (Object.prototype.hasOwnProperty.call(S.pending, id)) { return S.pending[id]; }
    var v = S.runAnswers ? S.runAnswers.values[id] : null; return v === undefined ? null : v;
  }, prefix: 'p', origin: false};
  function inlineQs(ids) {
    return '<div class="inline-q">' + ids.map(function (id) {
      return Q[id].kind === 'positions' || Q[id].kind === 'nozzles' ? '<p class="small">Change this one in the answers (it needs the drawing): <button type="button" class="btn link" data-goto="' + id + '">open the question</button></p>' : renderQ(Q[id], PEND);
    }).join('') + '</div>';
  }
  function pendingBar() {
    var ids = Object.keys(S.pending);
    if (!ids.length) { return ''; }
    return '<div class="pending noprint" role="status"><span>Changed answers: ' + esc(ids.map(function (i) { return Q[i].wording + ' → ' + fmtVal(Q[i], S.pending[i]); }).join('; ')) +
      '</span><button type="button" class="btn primary" data-update="1">Update the result</button><button type="button" class="btn" data-discard="1">Discard the changes</button></div>';
  }

  function trustBox(t) {
    var words = {LOW: 'Low', MODERATE: 'Moderate', FAIR: 'Fair'};
    return '<div class="trust" aria-label="Trust level"><strong>Trust level: ' + words[t.level] + '</strong>' +
      '<div class="meter" role="img" aria-label="Trust level ' + words[t.level] + ', step ' + t.step + ' of 3">' +
      t.levels.map(function (l) { return '<span class="' + (l === t.level ? 'on' : '') + '">' + words[l] + '</span>'; }).join('') + '</div>' +
      (t.level === 'LOW' ? '<p class="small">Low is the normal level until your own mill values and more observations are entered.</p>' : '') +
      '<details' + (S.trustOpen !== false ? ' open' : '') + ' data-trust="1"><summary>Why not higher?</summary><ul class="small">' +
      (t.reasons.length ? t.reasons.map(function (r) {
        var m = /^(.*?): (.{80,})$/.exec(r.text);
        return m ? '<li>' + esc(m[1]) + '. <details class="inline"><summary>Which ones</summary>' + esc(m[2]) + '</details></li>' : '<li>' + esc(r.text) + '</li>';
      }).join('') : '<li>No cap applies; the level is never higher than fair because nothing has been compared with plant data.</li>') +
      '</ul><details class="noprint"><summary class="small">The rule</summary><p class="small soft">' + esc(t.rule) + '</p></details></details></div>';
  }

  function profileLine(sum, run) {
    var p = sum.profile || {id: run.profile, label: run.profile, left_out: []};
    return '<div class="profile"><span><strong>' + esc(p.label) + ' run</strong>' + (isNum(run.elapsed_s) ? ' (' + Math.round(run.elapsed_s) + ' s)' : '') + '.</span>' +
      (p.left_out && p.left_out.length ? '<details><summary>What the quick run left out (' + p.left_out.length + ')</summary><ul class="small">' +
        p.left_out.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></details>' +
        '<button type="button" class="btn noprint" data-rerun="' + run.id + '" data-profile="detailed">Run in detail</button>' : '<span>The case as entered, nothing left out.</span>') + '</div>';
  }

  function changeBox(sum) {
    var cmp = sum.compared_with_base;
    if (!cmp) { return ''; }
    var main = cmp.changes.filter(function (c) { return c.standing_before !== c.standing_after || c.score_before !== c.score_after; });
    var moved = cmp.changes.length - main.length;
    return '<div class="change" role="status"><strong>What changed since the earlier result</strong> (' + esc((S.run.changes || []).join(', ')) + ')' +
      (main.length ? '<ul>' + main.map(function (c) {
        return '<li><strong>' + esc(c.name) + '</strong>: ' + (c.standing_before !== c.standing_after ? esc(standingWordsOf(c.standing_before)) + ' → <strong>' + esc(standingWordsOf(c.standing_after)) + '</strong>, ' : esc(standingWordsOf(c.standing_after)) + ', ') +
          'score ' + c.score_before + ' → ' + c.score_after + ', place ' + c.rank_before + ' → ' + c.rank_after + '</li>';
      }).join('') + '</ul>' : '<p>No cause changed its standing or score.</p>') +
      (moved ? '<p class="small">' + moved + ' other cause' + (moved > 1 ? 's' : '') + ' moved place only because of the change above.</p>' : '') +
      (cmp.trust ? '<p>' + esc(cmp.trust.replace(/LOW/g, 'low').replace(/MODERATE/g, 'moderate').replace(/FAIR/g, 'fair')) + '</p>' : '') +
      '<button type="button" class="btn noprint" data-open-run="' + cmp.base_run_id + '">Back to the earlier result</button> <span class="small soft">In the bars, the thin grey line is the earlier score.</span></div>';
  }
  function standingWordsOf(s) { return M.standing_words[s] || s; }

  function stripResult(sum, compact) {
    var sv = sum.strip_view;
    if (!sv.available) { return '<p class="empty">No across-the-width picture: this case has no spray header or width model.</p>'; }
    var bw = sv.band_width_m;
    var svg = drawStrip({label: 'Across the width: bands you saw, positions the model predicts, nozzles and the roll growth', barrel: sv.barrel_length_m,
      edge: sv.strip_start_m, width: sv.strip_end_m - sv.strip_start_m,
      nozzles: (sv.nozzles || []).map(function (n) { return {pos: n.position_m, index: n.index, number: n.number, level: n.level}; }),
      bands: sv.observed_positions_m.map(function (x) { return {x: x, w: bw}; }), result: sv, compact: compact});
    if (compact) { return svg; }
    var items = [LEG_BAND];
    sv.predicted.forEach(function (p) { if (p.positions_m.length) { items.push(legKind(p.kind, p.label)); } });
    if (sv.nozzles) {
      items.push({icon: '<circle cx="15" cy="8" r="6" fill="url(#half)" stroke="var(--ink)"/>', text: 'Weak nozzle (half filled); blocked: filled with a cross'});
    }
    if (sv.thermal_profile) { items.push({icon: '<path d="M2 12q8 0 13-8q5 8 13 8" fill="none" stroke="var(--orange)" stroke-width="2"/>', text: 'Roll growth across the barrel (bumps are hot stripes)'}); }
    if (sv.matches.some(function (m) { return m.links.some(function (l) { return l.matched; }); })) {
      items.push({icon: '<line x1="4" y1="14" x2="26" y2="2" stroke="var(--green)" stroke-width="2" stroke-dasharray="3 2"/>', text: 'Your band matches a predicted position (within ' + mmInt(sv.tolerance_m) + ')'});
    }
    var listRows = sv.observed_positions_m.map(function (x, i) {
      var hits = [];
      sv.matches.forEach(function (m) { m.links.forEach(function (l) { if (l.matched && Math.abs(l.observed_m - x) < 1e-9) { hits.push(m.label.toLowerCase() + ' at ' + mmInt(l.predicted_m - sv.strip_start_m)); } }); });
      return '<li>Band ' + (i + 1) + ' at ' + mmInt(x - sv.strip_start_m) + ': ' + (hits.length ? 'matches ' + esc(hits.join('; ')) : 'no predicted position within ' + mmInt(sv.tolerance_m)) + '</li>';
    }).join('');
    return '<div class="fig">' + svg + '</div>' + legend(items) + '<details><summary>The same as a list</summary><ul class="small">' + (listRows || '<li>No band positions entered.</li>') + '</ul></details>';
  }

  function nextChecks(sum) {
    if (!sum.next_checks.length) { return '<p class="empty">No further checks listed.</p>'; }
    return '<ul class="checklist">' + sum.next_checks.map(function (c, i) {
      var qs = c.questions.filter(function (q) { return Q[q]; });
      var key = 'nc-' + i;
      var open = S.openChecks[key];
      return '<li><div class="row"><span>' + esc(c.text) + '</span>' + (qs.length ? '<button type="button" class="btn noprint" data-check="' + key + '" data-qs="' + esc(qs.join(',')) +
        '" aria-expanded="' + (open ? 'true' : 'false') + '">' + (open ? 'Close' : 'I have checked this') + '</button>' : '<span class="small soft">(no question in the form for this)</span>') + '</div>' +
        (open ? inlineQs(qs) : '') + '</li>';
    }).join('') + '</ul>';
  }

  function whatIfCard() {
    var a = S.runAnswers ? S.runAnswers.values : {};
    var w = S.whatif || {};
    function stepper(id, label, unit, stepv, v) {
      return '<div><label class="w" for="wi-' + id + '">' + esc(label) + '</label><div class="stepper"><button type="button" data-wstep="' + id + '" data-d="' + (-stepv) + '" aria-label="Less">−</button>' +
        '<input type="number" step="any" id="wi-' + id + '" data-wi="' + id + '" value="' + (isNum(v) ? esc(v) : '') + '"><button type="button" data-wstep="' + id + '" data-d="' + stepv + '" aria-label="More">+</button>' +
        '<span class="unit">' + unit + '</span></div></div>';
    }
    var g = S.resultGeometry;
    var nn = g && g.nozzles ? g.nozzles.length : 0;
    var h = '<p class="howto">Change one or two values of this run and see what the model says would change. This is what the model says would change, not what will happen on the mill.</p><div class="whatif">' +
      stepper('exit_gauge', 'Exit gauge (must stay below ' + sig(a.entry_gauge, 4) + ' µm)', 'µm', isNum(a.exit_gauge) ? Math.max(0.5, Math.round(a.exit_gauge * 0.05 * 10) / 10) : 1, 'exit_gauge' in w ? w.exit_gauge : a.exit_gauge) +
      stepper('exit_speed', 'Exit speed', 'm/min', 30, 'exit_speed' in w ? w.exit_speed : a.exit_speed) +
      stepper('exit_tension', 'Exit tension (stress, 0 or more)', 'MPa', 2, 'exit_tension' in w ? w.exit_tension : a.exit_tension);
    if (nn) {
      h += '<div><label class="w" for="wi-noz">One nozzle</label><div class="numrow"><select id="wi-noz" data-wi="noz"><option value="">none</option>' +
        g.nozzles.map(function (n) { return '<option value="' + n.index + '"' + (String(w.noz) === String(n.index) ? ' selected' : '') + '>Nozzle ' + n.number + ' (' + mmInt(n.position_m - g.strip_start_m) + ')</option>'; }).join('') +
        '</select><select id="wi-nozstate" data-wi="nozstate"><option value="weak"' + (w.nozstate === 'weak' ? ' selected' : '') + '>weak</option><option value="blocked"' + (w.nozstate === 'blocked' ? ' selected' : '') + '>blocked</option></select></div></div>';
    }
    h += '</div><p><button type="button" class="btn primary" data-trywhatif="1">Try it</button> <span class="err" role="alert">' + esc(S.whatifError || '') + '</span></p>';
    if (S.compare) { h += compareHtml(S.compare); }
    return h;
  }

  function compareHtml(cmp) {
    function col(title, sum) {
      return '<div><h3>' + esc(title) + '</h3><p class="small">' + esc(sum.headline.text) + '</p>' + barsHtml(sum, sum.shortlist_ids.slice(0, 6), {compact: true}) +
        (sum.strip_view.available && sum.family.observed !== 'transverse' ? '<div class="fig">' + stripResult(sum, true) + '</div>' : '') + gaugeTable(sum) + '</div>';
    }
    return '<div class="change"><strong>What the model says would change</strong> (' + esc(cmp.changes.join(', ')) + '). Not what will happen.' +
      '<p>' + esc(cmp.diff) + '</p><div class="compare">' + col('This run', cmp.before) + col('What-if', cmp.after) + '</div>' +
      '<button type="button" class="btn" data-open-run="' + cmp.afterId + '">Open the what-if result</button></div>';
  }
  function gaugeTable(sum) {
    var gv = sum.gauge_view;
    if (!gv.available) { return ''; }
    var p = gv.passes.filter(function (x) { return Math.abs(x.exit_thickness_m - sum.pass.exit_thickness_m) < 1e-12; })[0] || gv.passes[gv.passes.length - 1];
    return '<table class="small"><caption class="soft">Pass ' + esc(p.label) + '</caption>' + gv.quantities.map(function (q) {
      var v = p.values[q.key], f = q.unit === 'um' ? 1e6 : 1e-6;
      return '<tr><td>' + esc(q.label) + '</td><td class="num">' + (isNum(v) ? sig(v * f, 3) + ' ' + esc(q.unit_label) : '–') + '</td></tr>';
    }).join('') + '</table>';
  }

  function renderResult(st) {
    var sum = st.summary, run = st.run;
    S.summary = sum;
    S.resultGeometry = sum.strip_view.available ? {nozzles: sum.strip_view.nozzles, strip_start_m: sum.strip_view.strip_start_m} : null;
    var fam = sum.family.observed;
    var shortIds = sum.shortlist_ids, otherIds = sum.other_family_ids;
    var note = '<p class="screening-note">A shortlist from a screening model that has not been compared with plant data, not a finding.</p>';
    var h = '<div class="wrap"><p class="printonly"><strong>Band screening summary</strong> — ' + esc(sum.case_name) + '</p>';
    h += '<section class="card"><div class="headline"><div><p class="text">' + esc(sum.headline.text) + '</p><p>' + esc(sum.family.text) + '</p>' +
      '<p class="statusline"><span aria-hidden="true">ⓘ</span><span>' + esc(sum.status_words) + '</span></p>' + profileLine(sum, run) + '</div>' + trustBox(sum.trust) + '</div></section>';
    h += '<section class="card" id="shortlist"><h2>The shortlist</h2><p class="howto">How to read this: each bar is one possible cause of ' + esc(sum.family.observed_words) +
      '. Bars to the right fit what you entered; bars left of zero do not fit. Select a bar for the details.</p>' + note + changeBox(sum) +
      barsHtml(sum, shortIds, {old: S.baseSummary}) +
      (otherIds.length ? '<details class="more"' + (S.otherOpen ? ' open' : '') + ' data-other="1"><summary>Causes of the other kind, and why they do not fit</summary>' + barsHtml(sum, otherIds, {old: S.baseSummary}) + '</details>' : '') +
      pendingBar() + '</section>';
    if (fam === 'transverse' || (!sum.strip_view.available && sum.along_view.available)) {
      h += '<section class="card"><h2>Along the strip</h2><p class="howto">How to read this: the top strip shows the mark spacing you measured, the bottom one the spacing of the best-fitting candidate with a spacing.</p>' +
        (sum.along_view.available ? '<div class="fig">' + alongSvg(sum.along_view) + '</div>' : '<p class="empty">No spacing measured yet: measure the mark spacing at two speeds to see this picture.</p>') + '</section>';
    } else {
      h += '<section class="card"><h2>Where across the width</h2><p class="howto">How to read this: the strip seen from above with the spray header over it. Solid bars are the bands you saw; outlined boxes with a letter are where the model puts a candidate; the line above shows where the roll grows. Hover, tap or tab to a mark for its position.</p>' +
        stripResult(sum) + '</section>';
    }
    h += '<section class="card"><h2>What to check next</h2><p class="howto">How to read this: measurements that would narrow the shortlist. Tick one you have done, answer it, and update the result.</p>' + nextChecks(sum) + pendingBar() + '</section>';
    h += '<section class="card noprint"><h2>What if</h2>' + whatIfCard() + '</section>';
    if (sum.gauge_view.available && sum.gauge_view.passes.length < 2) {
      h += '<section class="card noprint"><h2>Thinner or thicker</h2><p class="empty">Only one pass is known. Add the other passes of the route in step 2 ("The route") to see how the result changes from thick to thin.</p></section>';
    } else if (sum.gauge_view.available) {
      h += '<section class="card noprint"><h2>Thinner or thicker</h2><p class="howto">How to read this: one small chart per quantity, passes from thickest (left) to thinnest (right). Hatched passes are not credible or have no roll-gap result and are left out.</p>' +
        multiples(sum.gauge_view) + (sum.gauge_view.direction_text ? '<p>' + esc(sum.gauge_view.direction_text) + '</p>' : '') + '</section>';
    }
    if (sum.temperature_view.available) {
      h += '<section class="card noprint"><h2>Temperature</h2><p class="howto">How to read this: modelled strip temperature leaving each pass' + (sum.temperature_view.battery_limits_apply ? ', against the published coil limit' : '') + '.</p>' +
        '<div class="fig" style="max-width:760px">' + tempSvg(sum.temperature_view) + '</div><p class="small">' + esc(sum.temperature_view.caveat) + '</p></section>';
    }
    h += '<section class="card"><h2>How far to trust this</h2><p class="howto">How to read this: what the tool noticed about this case, what it could not assess, and what it never does.</p>' +
      '<div class="noprint"><h3>Notes on this case</h3><ul class="flags">' + sum.flags_plain.map(function (f) { return '<li>' + esc(f.text) + (f.what_to_do ? '<br><span class="small soft">What to do: ' + esc(f.what_to_do) + '</span>' : '') + '</li>'; }).join('') + '</ul>' +
      '<h3 class="noprint">Could not be assessed</h3><ul class="small">' + (sum.not_assessable.length ? sum.not_assessable.map(function (x) { return '<li>' + esc(x.what) + ': ' + esc(x.why) + '</li>'; }).join('') : '<li>Everything was assessed.</li>') + '</ul>' +
      '</div><h3>Always true</h3><ul class="small">' + sum.limitations.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></section>';
    h += '<section class="card noprint"><h2>Take it with you</h2><div class="takeaway"><button type="button" class="btn" data-report="' + run.id + '">Open the full engineering report</button>' +
      '<button type="button" class="btn" data-download="case.json">Download the case file</button><button type="button" class="btn" data-download="result.json">Download the result</button>' +
      '<button type="button" class="btn" data-print="1">Print a one-page summary</button><button type="button" class="btn" data-back-input="1">Change the answers</button></div></section></div>';
    app.innerHTML = h;
    animateBars();
  }

  function animateBars() {
    var fills = app.querySelectorAll('.fill[data-left]');
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function go() { for (var i = 0; i < fills.length; i++) { fills[i].style.left = fills[i].getAttribute('data-left') + '%'; fills[i].style.width = fills[i].getAttribute('data-width') + '%'; } }
    if (reduce) { go(); } else { requestAnimationFrame(function () { requestAnimationFrame(go); }); }
  }

  // ------------------------------------------------------------------ previous runs drawer
  function renderDrawer() {
    var d = document.getElementById('drawer');
    if (!S.drawer) { if (d) { d.remove(); } return; }
    if (!d) { d = document.createElement('aside'); d.id = 'drawer'; d.className = 'drawer'; d.setAttribute('aria-label', 'Previous runs'); document.body.appendChild(d); }
    var kids = {}, roots = [];
    S.runs.forEach(function (r) { if (r.base_run_id) { (kids[r.base_run_id] = kids[r.base_run_id] || []).push(r); } else { roots.push(r); } });
    var ids = {}; S.runs.forEach(function (r) { ids[r.id] = 1; });
    S.runs.forEach(function (r) { if (r.base_run_id && !ids[r.base_run_id]) { roots.push(r); } });
    var stW = {queued: 'waiting', running: 'running', done: 'done', failed: 'failed', cancelled: 'cancelled', interrupted: 'interrupted'};
    function item(r) {
      var when = (r.created || '').replace('T', ' ').slice(0, 16);
      var lead = (r.leaders || []).map(function (x) { return x.name; }).join(', ');
      return '<button type="button" class="runitem" data-open-run="' + r.id + '"><strong>' + esc(r.name) + '</strong><br><span class="small">' + esc(when) + ' UTC · ' +
        esc(stW[r.status] || r.status) + ' · ' + esc((M.profiles[r.profile] || {}).label || '') + (isNum(r.exit_thickness_m) ? ' · ' + gauge(r.exit_thickness_m) : '') +
        (r.product ? ' · ' + esc(productName(r.product)) : '') + (lead ? '<br>Fits best: ' + esc(lead) : '') + (r.trust ? ' · trust ' + esc(r.trust.toLowerCase()) : '') +
        (r.changes && r.changes.length ? '<br>What-if: ' + esc(r.changes.join(', ')) : '') + '</span></button>';
    }
    function tree(list) {
      return '<ul class="runs">' + list.map(function (r) { return '<li>' + item(r) + (kids[r.id] ? tree(kids[r.id]) : '') + '</li>'; }).join('') + '</ul>';
    }
    d.innerHTML = '<div class="numrow" style="justify-content:space-between"><h2>Previous runs</h2><button type="button" class="btn" data-drawer="0">Close</button></div>' +
      (S.runs.length ? tree(roots) : '<p class="empty">No runs yet. Answer the three steps and press "Run the screening".</p>');
  }
  function productName(id) {
    var n = id; M.products.forEach(function (g) { g.products.forEach(function (p) { if (p.id === id) { n = p.name; } }); }); return n;
  }
  // ------------------------------------------------------------------ render and navigation
  function render() {
    var active = document.activeElement && document.activeElement.id;
    var y = window.scrollY;
    if (S.view === 'input') { renderInput(); }
    renderDrawer();
    if (active) { var a = document.getElementById(active); if (a) { a.focus({preventScroll: true}); } }
    window.scrollTo(0, y);
  }
  function goStep(step, qid) {
    S.view = 'input'; S.step = step;
    stopPoll();
    renderInput(); renderDrawer();
    if (qid) {
      var node = document.getElementById('f-q-' + qid);
      if (node) {
        var det = node.closest('details'); if (det) { det.open = true; }
        node.scrollIntoView({block: 'center'}); node.classList.add('flash');
        var inp = node.querySelector('input,select,button'); if (inp) { inp.focus({preventScroll: true}); }
      }
    } else { window.scrollTo(0, 0); }
  }

  function stopPoll() { if (S.poll) { clearTimeout(S.poll); S.poll = null; } }
  function openRun(id, opts) {
    stopPoll();
    S.drawer = false; renderDrawer();
    S.openChecks = {}; S.pending = {}; S.compare = opts && opts.keepCompare ? S.compare : null; S.whatif = null; S.openCause = null;
    S.view = 'run';
    poll(id, true);
  }
  function poll(id, first) {
    api('GET', '/api/runs/' + id).then(function (r) {
      if (r.status !== 200) { app.innerHTML = '<div class="wrap"><div class="card errorbox" role="alert"><p>' + esc((r.data.error || {}).text || 'This run cannot be opened.') + '</p><button type="button" class="btn" data-back-input="1">Back to the answers</button></div></div>'; return; }
      var st = r.data, run = st.run;
      S.run = run;
      if (run.status === 'queued' || run.status === 'running') {
        if (first || !document.getElementById('elapsed')) { renderRunning(st); }
        else { document.getElementById('elapsed').textContent = (isNum(run.elapsed_s) ? Math.round(run.elapsed_s) : 0) + ' s'; }
        S.poll = setTimeout(function () { poll(id, false); }, 700);
        return;
      }
      if (run.status !== 'done') {
        api('GET', '/api/runs/' + id + '/answers.json').then(function (a) { S.runAnswers = a.status === 200 ? a.data.answers : null; renderFailed(st); });
        return;
      }
      Promise.all([api('GET', '/api/runs/' + id + '/answers.json'),
        run.base_run_id ? api('GET', '/api/runs/' + run.base_run_id) : Promise.resolve(null)]).then(function (res) {
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
    if (S.generalError || Object.keys(S.errors).length) {
      var first = Object.keys(S.errors)[0];
      if (first && Q[first]) { goStep(Q[first].step, first); }
      return;
    }
    var b = body(); b.profile = S.profile;
    var btn = document.getElementById('runbtn'); if (btn) { btn.disabled = true; }
    api('POST', '/api/runs', b).then(function (r) {
      if (r.status === 202) { openRun(r.data.id); return; }
      if (btn) { btn.disabled = false; }
      var e = r.data.error || {text: 'The run could not be started.'};
      if (e.question) { S.errors[e.question] = e.text; goStep(Q[e.question] ? Q[e.question].step : S.step, e.question); markErrors(); }
      else { S.generalError = e.text; updateSide(); }
    });
  }

  function setPreset(id, info) {
    var keepSteps = ['see', 'rolling'];
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
    S.banner = p.kind === 'example' ? 'Loaded "' + p.label + '". Its observations were generated by the model, not seen on a plant.' :
      p.kind === 'file' ? 'Opened the case file. Its values are shown as your answers.' : null;
    scheduleCheck();
  }

  function cycleNozzle(i) {
    var lv = val('nozzle_levels');
    var n = geometry().nozzle_positions_m.length;
    lv = Array.isArray(lv) && lv.length === n ? lv.slice() : Array.apply(null, Array(n)).map(function () { return 1; });
    var w = M.weak_nozzle_level;
    lv[i] = lv[i] >= 1 ? w : lv[i] > 0 ? 0 : 1;
    setVal('nozzle_levels', lv);
    render();
    var node = app.querySelector('[data-noz="' + i + '"]'); if (node) { node.focus({preventScroll: true}); }
    announce('Nozzle ' + (i + 1) + ': ' + (lv[i] >= 1 ? 'healthy' : lv[i] > 0 ? 'weak' : 'blocked'));
  }
  var live = null;
  function announce(t) {
    if (!live) { live = document.createElement('div'); live.className = 'sr'; live.setAttribute('aria-live', 'polite'); document.body.appendChild(live); }
    live.textContent = t;
  }

  function setBands(list, focusIndex) {
    var g = geometry(), wmm = Math.round(g.strip_width_m * 1000);
    list = list.map(function (x) { return Math.max(0, Math.min(wmm, Math.round(x))); });
    setVal('band_positions', list.length ? list : null);
    render();
    if (focusIndex !== undefined) { var b = app.querySelector('[data-band="' + focusIndex + '"]'); if (b) { b.focus({preventScroll: true}); } }
  }
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
    var t = e.target.closest('[data-step],[data-run],[data-cause],[data-answer],[data-check],[data-update],[data-discard],[data-open-run],[data-rerun],[data-cancel],[data-back-input],[data-goto],[data-report],[data-download],[data-print],[data-drawer],[data-trywhatif],[data-wstep],[data-list-add],[data-list-del],[data-route-use],[data-band-add],[data-band-del],[data-band-clear],[data-noz],[data-noz-reset],[data-noz-init],[data-defaults],[data-new],[data-mark]');
    if (!t) { var m = e.target.closest('.mark'); if (m) { showTip(m); } return; }
    var d = t.dataset;
    if (d.step) { goStep(d.step); }
    else if (d.run) { startRun(); }
    else if (d.cause) { S.openCause = S.openCause === d.cause ? null : d.cause; rerenderResult(); var dd = document.getElementById('detail-' + d.cause); if (dd) { dd.scrollIntoView({block: 'nearest'}); } }
    else if (d.answer) { var k = 'nl-' + S.openCause + '-' + d.answer; S.openChecks[k] = !S.openChecks[k]; rerenderResult(); }
    else if (d.check) { S.openChecks[d.check] = !S.openChecks[d.check]; rerenderResult(); }
    else if (d.update) {
      api('POST', '/api/runs/' + S.run.id + '/variant', {changes: S.pending, profile: S.run.profile, label: String(S.run.name || '').replace(/ \((updated|what-if)\)$/, '') + ' (updated)'}).then(function (r) {
        if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text || 'The update could not be started.'); }
      });
    }
    else if (d.discard) { S.pending = {}; S.openChecks = {}; rerenderResult(); }
    else if (d.openRun) { openRun(d.openRun); }
    else if (d.rerun) { api('POST', '/api/runs/' + d.rerun + '/rerun', {profile: d.profile || 'detailed'}).then(function (r) { if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text); } }); }
    else if (d.cancel) { api('POST', '/api/runs/' + d.cancel + '/cancel', {}).then(function () { poll(d.cancel, true); }); }
    else if (d.backInput) { if (S.runAnswers && S.view !== 'input') { loadRunAnswers(); } goStep(S.step); }
    else if (d.goto) { if (S.view !== 'input' && S.runAnswers) { loadRunAnswers(); } goStep(Q[d.goto].step, d.goto); }
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
        S.banner = 'Pass "' + (r0.label || '') + '" is now the pass where the bands show.'; render();
      }
    }
    else if (d.bandAdd) { var nv = Number(document.getElementById('bp-new').value); if (document.getElementById('bp-new').value !== '' && isFinite(nv)) { setBands(bandsList().concat([nv]), bandsList().length); } }
    else if (d.bandDel !== undefined) { var bl = bandsList().slice(); bl.splice(Number(d.bandDel), 1); setBands(bl); }
    else if (d.bandClear) { setBands([]); }
    else if (d.noz !== undefined && !t.closest('svg').dataset.dragging) { cycleNozzle(Number(d.noz)); }
    else if (d.nozReset) { setVal('nozzle_levels', null); render(); }
    else if (d.nozInit) { setVal('nozzle_levels', geometry().nozzle_positions_m.map(function () { return 1; })); render(); }
    else if (d.defaults) { productDefaults(); }
    else if (d.new) { newScreening(); }
  });

  function alertBox(t) { announce(t || ''); window.alert(t || 'Something went wrong.'); }

  function loadRunAnswers() {
    // "Change the answers" from a result: continue from that run's answers
    var a = S.runAnswers; if (!a) { return; }
    S.presetsExtra = S.presetsExtra.filter(function (p) { return p.id !== 'case_file'; });
    S.answers = clone({values: a.values || {}, origins: a.origins || {}, own_mill: !!a.own_mill, name: a.name || ''});
    S.touched = {}; Object.keys(S.answers.values).forEach(function (k) { S.touched[k] = true; });
    if (S.run && S.run.preset && (M.presets.some(function (p) { return p.id === S.run.preset; }))) { S.presetId = S.run.preset; }
    scheduleCheck();
  }

  document.addEventListener('change', function (e) {
    var t = e.target, d = t.dataset;
    if (d.chip) { var v = JSON.parse(d.v); if (d.chip === 'orientation' && ctxOf(t) === 'f') { S.touched.orientation = true; } store(d.chip, v, t); if (ctxOf(t) === 'f') { render(); } }
    else if (d.select) { store(d.select, JSON.parse(t.value), t); if (ctxOf(t) === 'f') { render(); } }
    else if (d.origin) { S.answers.origins[d.origin] = t.value; if (t.value === 'preset') { S.answers.values[d.origin] = clone(pv(d.origin)); } S.touched[d.origin] = true; scheduleCheck(); render(); }
    else if (d.preset) { setPreset(d.preset); render(); }
    else if (d.profile) { S.profile = d.profile; }
    else if (t.id === 'ownmill') { S.answers.own_mill = t.checked; scheduleCheck(); }
    else if (t.id === 'casename') { S.answers.name = t.value; scheduleCheck(); }
    else if (t.id === 'casefile') { openCaseFile(t.files[0]); }
    else if (d.num && ctxOf(t) === 'f' && ['exit_gauge', 'band_width', 'strip_width', 'entry_gauge'].indexOf(d.num) >= 0) { render(); }
    else if (d.bandpos !== undefined) { render(); }
    else if (d.wi) { S.whatif = S.whatif || {}; S.whatif[d.wi] = t.tagName === 'SELECT' ? t.value : Number(t.value); }
    else if (t.closest('[data-more]')) { /* details toggle handled below */ }
  });
  document.addEventListener('toggle', function (e) {
    var t = e.target;
    if (t.dataset && t.dataset.more) { S.openMore = S.openMore || {}; S.openMore[t.dataset.more] = t.open; }
    if (t.dataset && t.dataset.other) { S.otherOpen = t.open; }
    if (t.dataset && t.dataset.trust) { S.trustOpen = t.open; }
  }, true);
  document.addEventListener('input', function (e) {
    var t = e.target, d = t.dataset;
    if (t.id === 'prod-filter') { S.prodFilter = t.value; var pos = t.selectionStart; render(); var f = document.getElementById('prod-filter'); f.focus(); f.setSelectionRange(pos, pos); return; }
    if (d.num) { storeQuiet(d.num, t.value === '' ? null : Number(t.value), t); }
    else if (d.text) { storeQuiet(d.text, t.value.trim() === '' ? null : t.value, t); }
    else if (d.nums) { var p = parseNums(t.value); if (p !== undefined) { storeQuiet(d.nums, p, t); } }
    else if (d.list) {
      var q = Q[d.list], cur = clone((ctxOf(t) === 'p' ? PEND : FORM).get(q.id) || []), row = cur[Number(d.row)];
      var fk = d.fkind, v = t.tagName === 'SELECT' ? t.value : fk === 'numbers' ? (parseNums(t.value) || []) : fk === 'text' ? t.value : (t.value === '' ? null : Number(t.value));
      row[d.field] = v; storeQuiet(q.id, cur, t);
    }
    else if (d.bandpos !== undefined) { var bl = bandsList().slice(); if (t.value !== '') { bl[Number(d.bandpos)] = Number(t.value); setVal('band_positions', bl); refreshStrip(); } }
    else if (d.nozlevel !== undefined) {
      var lv = (val('nozzle_levels') || []).slice(), x = Number(t.value);
      if (t.value !== '' && x >= 0 && x <= 1) { lv[Number(d.nozlevel)] = x; setVal('nozzle_levels', lv); refreshStrip(); }
    }
  });
  function storeQuiet(id, v, node) {
    if (ctxOf(node) === 'p') { S.pending[id] = v; var pb = app.querySelectorAll('.pending'); if (!pb.length) { rerenderResult(); } else { var html = pendingBar(); for (var i = 0; i < pb.length; i++) { pb[i].outerHTML = html; } } return; }
    setVal(id, v);
  }
  function refreshStrip() {
    var a = document.getElementById('strip-input'), b = document.getElementById('strip-nozzles');
    var host = (a || b) && (a || b).parentNode;
    if (a) { var g = geometry(); var tmp = document.createElement('div'); var bw = val('band_width');
      tmp.innerHTML = drawStrip({id: 'strip-input', label: a.getAttribute('aria-label'), barrel: g.barrel_length_m, edge: g.strip_edge_m, width: g.strip_width_m,
        nozzles: nozzlesFor(val('nozzle_levels')), bands: bandsList().map(function (mm) { return {x: g.strip_edge_m + mm / 1000, w: isNum(bw) ? bw / 1000 : null}; }), interactive: 'bands'});
      a.replaceWith(tmp.firstChild); }
    if (b) { var g2 = geometry(); var tmp2 = document.createElement('div');
      tmp2.innerHTML = drawStrip({id: 'strip-nozzles', label: b.getAttribute('aria-label'), barrel: g2.barrel_length_m, edge: g2.strip_edge_m, width: g2.strip_width_m,
        nozzles: nozzlesFor(val('nozzle_levels')), bands: bandsList().map(function (mm) { return {x: g2.strip_edge_m + mm / 1000}; }), interactive: 'nozzles'});
      b.replaceWith(tmp2.firstChild); }
    return host;
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
      var nv = Number(t.value); if (t.value !== '' && isFinite(nv)) { setBands(bandsList().concat([nv])); var f = document.getElementById('bp-new'); if (f) { f.focus(); } }
      e.preventDefault();
    } else if (e.key === 'Escape') { hideTip(); if (S.drawer) { S.drawer = false; renderDrawer(); } }
  });
  document.addEventListener('focusin', function (e) { if (e.target.getAttribute && e.target.getAttribute('data-tip')) { showTip(e.target); } });
  document.addEventListener('focusout', hideTip);
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
      api('POST', '/api/case/open', {case_file: c}).then(function (r) {
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
    api('POST', '/api/product-defaults', b).then(function (r) {
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
    var before = S.summary, baseRun = S.run;
    api('POST', '/api/runs/' + S.run.id + '/variant', {changes: ch, profile: S.run.profile, label: (S.run.name || '') + ' (what-if)'}).then(function (r) {
      if (r.status !== 202) { S.whatifError = (r.data.error || {}).text; rerenderResult(); return; }
      var id = r.data.id;
      var sec = app.querySelector('[data-trywhatif]'); if (sec) { sec.disabled = true; sec.textContent = 'Running the what-if…'; }
      (function wait() {
        api('GET', '/api/runs/' + id).then(function (s) {
          var st = s.data.run.status;
          if (st === 'queued' || st === 'running') { setTimeout(wait, 700); if (sec) { sec.textContent = 'Running the what-if… ' + Math.round(s.data.run.elapsed_s || 0) + ' s'; } return; }
          if (st !== 'done') { S.whatifError = (s.data.run.error || {}).text || 'The what-if did not finish.'; rerenderResult(); return; }
          var after = s.data.summary;
          S.compare = {before: before, after: after, afterId: id, changes: words, diff: after.compared_with_base ? after.compared_with_base.text : ''};
          if (S.run.id === baseRun.id) { rerenderResult(); var c = app.querySelector('.compare'); if (c) { c.scrollIntoView({block: 'start'}); } }
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
'''
