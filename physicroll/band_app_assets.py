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
--red:#9B2C2C;--purple:#8E4A86;--card:#FFFFFF;--focus:#2F6FA3;--bar-old:#9AA6AE;--strip:#D5DBD6;
--strip-edge:#6B7780;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--ink:#E6EBE8;--paper:#11181F;--panel:#1B252E;
--line:#33414C;--soft:#AEB9C1;--orange-text:#F0A06A;--orange:#E0702A;--blue:#7DB3E0;
--green:#7CC4A0;--amber:#E2B85C;--red:#F09A9A;--purple:#D49ACB;--card:#16202A;--focus:#7DB3E0;
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
svg .mark:focus>*:first-child{stroke:var(--ink);stroke-width:3}
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
.checklist .row{display:grid;grid-template-columns:minmax(0,1fr) 13rem;gap:.6rem;align-items:start}
.checklist .row>:last-child{justify-self:end;text-align:right}
@media (max-width:600px){.checklist .row{grid-template-columns:minmax(0,1fr)}.checklist .row>:last-child{justify-self:start;text-align:left}}
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
.evid .vw{font-weight:700}.evid .vw.ok{color:var(--green)}.evid .vw.no{color:var(--red)}
.evsub{margin:.2rem 0 0;padding-left:1.1rem}.evsub li{border:0;padding:.05rem 0}
@page{size:A4;margin:11mm}
@media print{body{font-size:9.5pt;line-height:1.35}.pr-hide,.howto,.profile details,.trust .meter+p{display:none!important}
.card{padding:6px 8px;margin-bottom:6px}.card h2{font-size:11pt;margin-bottom:2px}
.headline .text{font-size:12pt}.statusline{padding:2px 6px;margin-top:4px}
.bar{padding:1px 2px;grid-template-columns:30px minmax(0,13rem) minmax(0,1fr) 2.2rem}
.bar .pic svg{width:30px;height:20px}.axis{grid-template-columns:30px minmax(0,13rem) minmax(0,1fr) 2.2rem}
.track{height:12px}.track .fill{top:1px;height:10px}
.fig svg,#shortlist,.legend{break-inside:avoid;page-break-inside:avoid}
.fig{max-width:82%}.legend{font-size:8pt}.checklist>li{padding:2px 0}
.trust{padding:6px}.trust ul{margin:2px 0;padding-left:1rem}
.screening-note{margin:2px 0}h3{font-size:10pt;margin:4px 0 2px}}
@media print{.headline{display:grid!important;grid-template-columns:minmax(0,1fr) 190px!important}
.bar,.axis{display:grid!important;grid-template-columns:30px minmax(0,12rem) minmax(0,1fr) 2.2rem!important;grid-template-areas:none!important}
.bar .pic,.bar .nm,.bar .score,.bar .track{grid-area:auto!important}
.bar .nm b{display:inline;font-size:9pt}.bar .stand{font-size:8pt;margin-left:.3rem}
.trust details summary{display:none}.trust .small{font-size:8pt}}
@media print{#shortlist details.more,.fig+.legend+details,.trust details details{display:none!important}
.fig{max-width:68%}.legend{gap:0 .6rem}.headline p{margin:2px 0}.card>h2{margin:0}}
@media print{.bar,.axis{grid-template-columns:24px minmax(0,19rem) minmax(0,1fr) 2rem!important;gap:6px!important}
.bar .pic svg{width:24px;height:16px}.bar{padding:0 2px!important}.bars{gap:0}
.statusline{font-size:8.5pt}.flags,.cols{display:none}}
@media print{.fig{max-width:58%}.card ul.small{font-size:8pt;margin:0;padding-left:1rem}
.card ul.small li{margin:0}.legend{font-size:7.5pt;margin:2px 0}.checklist{font-size:8.5pt}
.trust{font-size:8.5pt}.headline .text{font-size:11pt}}
@media print{.fig{max-width:52%}.checklist>li{padding:0;border:0}.card{margin-bottom:4px}
.wrap>p.printonly{margin:0 0 4px}.screening-note{font-size:8.5pt}}
.notice{border-left:4px solid var(--amber);background:var(--paper);padding:.35rem .6rem;margin:.4rem 0;font-size:.92rem}
.notice.reset{border-left-color:var(--blue);font-weight:600}
.stale svg,.stale .legend{opacity:.45}
.stale-note{border-left:4px solid var(--amber);padding:.3rem .6rem;margin:.3rem 0;font-size:.92rem}
[data-view="nozzles"].busy svg{cursor:progress}
.noz .valve{fill:none;stroke:var(--blue);stroke-width:1.5;stroke-dasharray:2 2}
.notice.moved{border-left-color:var(--blue)}
.notice-slot:empty{display:none}
.zones line{stroke:var(--blue);stroke-width:1.2;stroke-dasharray:3 3}
.warnline{border-left:4px solid var(--amber);padding:.3rem .6rem;margin:.5rem 0}
@media print{#shapemeter{display:none!important}.smprint{--blue:#000;--orange:#666;--orange-text:#000;--purple:#333}.stripcard{display:flow-root}.smprint{display:block!important;float:right;width:44%;margin:0 0 2px 8px}.smprint-h,.smprint-w{font-size:7.5pt;margin:0;line-height:1.25}.smprint svg{width:100%;height:auto}}

/* add-on area of step 3: one line per group, filled state, clear in one action */
.addons{border:1px solid var(--line);border-radius:8px;margin:1rem 0;padding:.2rem .8rem;background:var(--card)}
.addons>summary{cursor:pointer;padding:.6rem 0;font-weight:700}
.addons .a-title{font-size:1.05rem}
.groups{list-style:none;margin:.2rem 0 .6rem;padding:0}
.addon-group{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;border-top:1px solid var(--line)}
.addon-group>details>summary{cursor:pointer;padding:.55rem 0;display:flex;flex-wrap:wrap;gap:.2rem .8rem;align-items:baseline}
.addon-group .g-title{font-weight:600}
.g-state{font-size:.9rem}.g-state.empty{color:var(--soft-text,var(--soft))}.g-state.filled{color:var(--ink)}
.g-clear{margin-top:.45rem}
/* the one add-on card pattern */
.addon .takeaway-line{font-size:1.05rem;margin:.2rem 0 .6rem}
.quietline{margin:.4rem 0 1rem}
.term{text-decoration:underline dotted;text-underline-offset:3px;cursor:help}
/* charts: colour plus shape and dash; both themes through the palette tokens */
/* series colours come from the chart spec (blue, orange, purple: one meaning each); references
   and ranges are neutral; the legend draws each mark with the chart's own drawing */
.interval{stroke-width:2.5}
.ref{stroke:var(--soft);stroke-width:1.6;stroke-dasharray:5 4;fill:none}
.ref-area{fill:var(--soft);opacity:.2}
svg .ref-label{fill:var(--soft)}
svg .axis-title{fill:var(--ink)}
.grid{stroke:var(--line);stroke-width:.6;opacity:.6}
.hbar{fill:var(--blue)}.hbar.low{fill:var(--orange)}.fig text.inbar{fill:var(--paper)}
.addon-group>details>summary{list-style:none}.addon-group>details>summary::-webkit-details-marker{display:none}
.addon-group>details>summary::before{content:'▸';display:inline-block;width:1em;color:var(--soft-text,var(--ink))}
.addon-group>details[open]>summary::before{content:'▾'}
.addon-group>details>summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
@media (max-width:600px){.addon-group>details>summary{display:grid;grid-template-columns:1.2em minmax(0,1fr);gap:.1rem 0;align-items:baseline}
.addon-group>details>summary>[data-view]{grid-column:2}}
/* the add-on cards under one heading per input group, and the index near the top */
.addon-index{margin:.2rem 0 1rem;padding:.5rem .8rem;border:1px solid var(--line);border-radius:8px;background:var(--card);line-height:1.9}
.addon-index a{color:var(--blue);overflow-wrap:anywhere}
.addon-section>summary{cursor:pointer;list-style:none;display:grid;grid-template-columns:1.2em minmax(0,1fr);gap:0 .2rem;align-items:baseline}
.addon-section>summary::-webkit-details-marker{display:none}
.addon-section>summary::before{content:'▸';grid-row:1/3}.addon-section[open]>summary::before{content:'▾'}
.addon-section>summary .s-title{font-weight:700;font-size:1.1rem}
.addon-section>summary .s-line{grid-column:2;color:var(--soft-text,var(--soft));font-size:.95rem}
.addon-section>summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.addon-section>.card.addon{box-shadow:none;margin:.8rem 0 0}
.valve-bracket{fill:none;stroke:var(--soft);stroke-width:1.4}
.valve-change{stroke:var(--ink);stroke-width:1;opacity:.55}
.headline .addon-index{margin:.6rem 0 0}
@media print{.lpprint{display:block!important;clear:both;margin-top:4px}.lpprint svg{width:60%;height:auto}}
.valve-outline{fill:none;stroke:var(--blue);stroke-opacity:.35;stroke-width:.5}
@media print{.checklist .row{display:flex;flex-wrap:wrap;justify-content:space-between}}
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
    var yN = 38, yTop = hasTh ? 146 : 92, yBot = yTop + 84, yRul = yBot + 8, H = yRul + 44;
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(o.label) + '"' +
      (o.id ? ' id="' + o.id + '"' : '') + ' data-barrel="' + barrel + '" data-edge="' + o.edge +
      '" data-width="' + o.width + '" data-ml="' + ML + '" data-sx="' + sx + '">';
    s += '<defs><pattern id="half" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="var(--card)"/>' +
      '<path d="M0 4L4 0" stroke="var(--ink)" stroke-width="1.4"/></pattern>' +
      '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="2" height="6" fill="var(--soft)"/></pattern></defs>';
    // roll barrel and spray header
    s += '<rect class="roll" x="' + X(0) + '" y="' + (yN - 14) + '" width="' + (barrel * sx) + '" height="' + (yBot - yN + 18) + '"/>';
    s += '<text x="' + X(0) + '" y="13" font-size="12" class="softtext">Roll barrel ' + mmInt(barrel) + ', coolant nozzles numbered from nozzle 1</text>';
    var noz = o.nozzles || [];
    var pitch = noz.length > 1 ? (noz[1].pos - noz[0].pos) * sx : 30;
    var r = Math.max(4, Math.min(10, pitch * 0.32));
    // the spray valves of the flatness control (the engine's grouping), as brackets
    (o.valves || []).forEach(function (v) {
      var xa = X(v.start_m) - r, xb = X(v.end_m) + r, yv = yN - r - 5;
      s += '<path class="valve-bracket" d="M' + xa + ' ' + (yv + 3) + 'L' + xa + ' ' + yv + 'L' + xb + ' ' + yv + 'L' + xb + ' ' + (yv + 3) + '"/>';
    });
    noz.forEach(function (n) {
      var st = n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      if (n.level > 0) {
        s += '<path class="spray' + (st === 'weak' ? ' weak' : '') + '" d="M' + X(n.pos) + ' ' + (yN + r) + 'L' +
          (X(n.pos) - pitch * 0.62) + ' ' + yTop + 'L' + (X(n.pos) + pitch * 0.62) + ' ' + yTop + 'Z"/>';
      }
    });
    noz.forEach(function (n) {
      var st = n.level === null || n.level === undefined ? 'healthy' : n.level <= 0 ? 'blocked' : n.level >= 1 ? 'healthy' : 'weak';
      var words = 'Nozzle ' + n.number + ': ' + (n.unknown ? 'not checked (the model uses full flow)' : st === 'healthy' ? 'healthy' : st === 'weak' ? 'weak (flow ' + sig(n.level, 2) + ')' : 'blocked') +
        ', at ' + mmInt(n.pos - o.edge) + ' from the strip edge' + (n.events ? '; ' + n.events : '');
      var focus = o.interactive === 'nozzles' ? ' tabindex="0" role="button" data-noz="' + n.index + '"' : ' tabindex="0" class="mark"';
      s += '<g class="noz ' + st + (o.interactive === 'nozzles' ? '' : ' mark') + '"' + focus + ' aria-label="' + esc(words) + '" data-tip="' + esc(words) + '">' +
        '<circle cx="' + X(n.pos) + '" cy="' + yN + '" r="' + r + '"/>' +
        (st === 'blocked' ? '<path d="M' + (X(n.pos) - r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) + r * .6) + ' ' + (yN + r * .6) +
          'M' + (X(n.pos) + r * .6) + ' ' + (yN - r * .6) + 'L' + (X(n.pos) - r * .6) + ' ' + (yN + r * .6) + '" stroke="var(--card)" stroke-width="2"/>' : '') +
        (n.events ? '<circle class="valve" cx="' + X(n.pos) + '" cy="' + yN + '" r="' + (r + 3) + '"/>' : '') +
        '</g>';
      if (noz.length <= 40 && (n.number === 1 || n.number % 5 === 0)) {
        s += '<text x="' + X(n.pos) + '" y="' + (yN + r + 15) + '" font-size="13" font-weight="600" text-anchor="middle">' + n.number + '</text>';
      }
    });
    // shapemeter zones (from the server's model): dashed boundaries just above the strip
    if (o.zones && o.zones.length) {
      var yZ = yTop - 7;
      s += '<g class="zones" aria-hidden="true"><line x1="' + X(o.zones[0].start_m) + '" x2="' + X(o.zones[o.zones.length - 1].end_m) + '" y1="' + yZ + '" y2="' + yZ + '"/>';
      o.zones.forEach(function (z, k) {
        s += '<line x1="' + X(z.start_m) + '" x2="' + X(z.start_m) + '" y1="' + (yZ - 6) + '" y2="' + (yTop + 6) + '"/>';
        if (k === o.zones.length - 1) { s += '<line x1="' + X(z.end_m) + '" x2="' + X(z.end_m) + '" y1="' + (yZ - 6) + '" y2="' + (yTop + 6) + '"/>'; }
      });
      s += '</g>';
    }
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
          var words = 'Your band at ' + mmInt(l.observed_m - o.edge) + ' lies within ' + mmSmall(res.tolerance_m) +
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
    s += '<text x="' + X(o.edge) + '" y="' + (yRul + 36) + '" font-size="12" class="softtext">' + (W < 600 ? 'mm from the strip edge nearest nozzle 1' : 'mm across the strip, from the strip edge nearest nozzle 1') + '</text>';
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

  // nozzles and bands exactly as the server's drawing model has them (effective levels)
  function nozzlesOf(m) {
    var h = m.header;
    if (!h) { return []; }
    return h.nozzles.map(function (n) {
      var ev = n.valve_events.map(function (k) { var e = m.valve_events[k]; return 'valve event: flow ' + sig(e.level, 2) + ' for ' + sig(e.duration_s, 3) + ' s from ' + sig(e.start_s, 3) + ' s'; });
      return {pos: n.position_m, index: n.index, number: n.number, level: n.level, unknown: !h.levels_known, events: ev.join('; ')};
    });
  }
  function bandsOf(m, withWidth) {
    var bw = m.bands.band_width_m;
    return m.bands.positions_m.map(function (x) { return {x: x, w: withWidth && isNum(bw) ? bw : null}; });
  }
  function stripArgs(m) { return {barrel: m.strip.barrel_length_m, edge: m.strip.edge_m, width: m.strip.width_m}; }
  function zonesOf(m) { return m.shapemeter ? m.shapemeter.zones : null; }
  // the shapemeter zones in words, beside the drawing (the drawing's zone lines are not focusable)
  function zonesNote(m) {
    var sm = m.shapemeter;
    if (!sm) { return ''; }
    var edge = m.strip.edge_m, z = sm.zones;
    var counts = {}; z.forEach(function (x) { var n = x.nozzle_numbers.length; counts[n] = (counts[n] || 0) + 1; });
    var per = Object.keys(counts).sort().map(function (n) { return counts[n] + ' zone' + (counts[n] > 1 ? 's' : '') + ' with ' + n + ' nozzle' + (n === '1' ? '' : 's'); }).join(', ');
    return '<p class="small">Shapemeter: ' + sm.zone_count + ' zones (dashed lines just above the strip) from ' + mmInt(z[0].start_m - edge) + ' to ' + mmInt(z[z.length - 1].end_m - edge) +
      ' from the strip edge; ' + per + '.' + (sm.uncovered_strip_width_m > 0.0005 ? ' The zones do not cover ' + mmInt(sm.uncovered_strip_width_m) + ' of the strip.' : '') + '</p>' +
      '<details class="more"><summary>The zones as a list</summary><ul class="small">' + z.map(function (x) {
        return '<li>Zone ' + (x.index + 1) + ': ' + mmInt(x.start_m - edge) + ' to ' + mmInt(x.end_m - edge) + ' from the strip edge' + (x.nozzle_numbers.length ? ', nozzle ' + x.nozzle_numbers.join(', ') : ', no nozzle') + '</li>';
      }).join('') + '</ul></details>';
  }

  function bandsInput(q, ctx) { return '<div data-view="bands">' + VIEWS.bands() + '</div>'; }
  function bandsView() {
    var m = model();
    var pos = m.bands.from_edge_mm;
    var a = stripArgs(m);
    var svg = drawStrip({id: 'strip-input', label: 'Top view of the strip. Click or tap on the strip to add a band; drag a band to move it; with the keyboard use the arrow keys on a band, Delete removes it.',
      barrel: a.barrel, edge: a.edge, width: a.width,
      nozzles: nozzlesOf(m), bands: bandsOf(m, true), interactive: 'bands', zones: zonesOf(m)});
    var list = '<ol class="poslist" aria-label="Band positions">' + pos.map(function (mm, i) {
      return '<li><label for="bp-' + i + '">Band ' + (i + 1) + '</label><input type="number" step="1" id="bp-' + i + '" data-bandpos="' + i +
        '" value="' + esc(mm) + '"><span class="unit">mm</span><button type="button" class="btn" data-band-del="' + i +
        '" aria-label="Delete band ' + (i + 1) + '">Delete</button></li>';
    }).join('') + '</ol>';
    return staleNote() + '<div class="drawing' + (S.modelStale ? ' stale' : '') + '"><div>' + svg + legend([LEG_BAND, {icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)"/>', text: 'Coolant nozzle (for orientation)'}]) +
      '</div><div class="side">' + (pos.length ? list : '<p class="empty">No bands placed yet. Click on the strip, or add one here.</p>') +
      '<div class="numrow"><label class="sr" for="bp-new">New band position in mm</label><input type="number" step="1" id="bp-new" placeholder="mm from edge">' +
      '<button type="button" class="btn" data-band-add="1">Add band</button></div>' +
      '<p class="small soft">Strip ' + mmInt(m.strip.width_m) + ' wide. ' + (pos.length ? '<button type="button" class="btn link" data-band-clear="1">Clear all ("Don\'t know")</button>' : '') + '</p></div></div>';
  }

  function nozzleInput(q, ctx) { return '<div data-view="nozzles">' + VIEWS.nozzles() + '</div>'; }
  function nozzlesView() {
    var m = model(), h = m.header;
    if (!h) {
      return '<p class="empty">This starting point has no spray header model, so nozzles cannot be marked here.</p>';
    }
    var a = stripArgs(m);
    var svg = drawStrip({id: 'strip-nozzles', label: 'Spray header over the strip. Click a nozzle to cycle healthy, weak and blocked; with the keyboard press Enter or Space on a nozzle.',
      barrel: a.barrel, edge: a.edge, width: a.width,
      nozzles: nozzlesOf(m), bands: bandsOf(m, false), interactive: 'nozzles', zones: zonesOf(m),
      valves: m.control_zones ? m.control_zones.valves : null});
    var known = h.levels_known, lst = '';
    if (known) {
      lst = '<details class="more"' + (S.nozListOpen ? ' open' : '') + ' data-nozlist="1"><summary>Nozzle list (flow level of each nozzle, 1 = full, 0 = blocked)</summary><div class="nozlist">' +
        h.nozzles.map(function (n) {
          return '<label for="nz-' + n.index + '">Nozzle ' + n.number + '<input type="number" min="0" max="1" step="0.05" id="nz-' + n.index + '" data-nozlevel="' + n.index + '" value="' + esc(n.level) + '"></label>';
        }).join('') + '</div></details>';
    }
    var ev = m.valve_events.length ? '<p class="small">Valve events (dotted ring on the drawing): ' + esc(m.valve_events.map(function (e) {
      return 'nozzle' + (e.numbers.length > 1 ? 's ' : ' ') + e.numbers.join(', ') + ' at flow ' + sig(e.level, 2) + ' for ' + sig(e.duration_s, 3) + ' s';
    }).join('; ')) + '.</p>' : '';
    return staleNote() + '<div class="' + (S.modelStale ? 'stale' : '') + '">' + svg + legend([{icon: '<circle cx="15" cy="8" r="6" fill="var(--card)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Healthy'},
      {icon: '<circle cx="15" cy="8" r="6" fill="url(#half)" stroke="var(--ink)" stroke-width="1.5"/>', text: 'Weak (flow ' + M.weak_nozzle_level + ')'},
      {icon: '<circle cx="15" cy="8" r="6" fill="var(--ink)" stroke="var(--ink)"/>', text: 'Blocked'}, LEG_BAND].concat(m.valve_events.length ? [{icon: '<circle cx="15" cy="8" r="6" fill="none" stroke="var(--blue)" stroke-width="1.5" stroke-dasharray="2 2"/>', text: 'Valve event'}] : [])) +
      '<p class="small" aria-live="polite" data-nozstatus="1">' + (known ? (h.weak + ' weak, ' + h.blocked + ' blocked of ' + h.nozzles.length +
      ' nozzles. <button type="button" class="btn link" data-noz-reset="1">Set back to "Don\'t know"</button>') :
      'Nozzle state: "Don\'t know" (nobody has checked; the model uses full flow). Click a nozzle to mark it; the others then count as healthy.') + '</p>' +
      (known ? '' : '<button type="button" class="btn" data-noz-init="1">All nozzles checked and healthy</button>') + ev + zonesNote(m) + lst + '</div>';
  }

  // "Blocked nozzles (by number)": a view of the level-0 nozzles of the drawing that edits them
  function blockedView() {
    var m = model(), h = m.header;
    if (!h) { return '<p class="empty">This starting point has no spray header model.</p>'; }
    var nums = h.levels_known ? h.nozzles.filter(function (n) { return n.level <= 0; }).map(function (n) { return n.number; }) : [];
    return '<div class="numrow"><input type="text" class="wide" id="f-in-blocked_nozzles" data-nozedit="blocked" value="' + esc(nums.join(', ')) +
      '" placeholder="' + (h.levels_known ? 'none' : "Don't know") + '" aria-describedby="f-h-blocked_nozzles"><span class="small soft">separate with commas</span></div>';
  }
  // the coverage check's blocked nozzles: the drawing's marks when it is the same header
  function coverageView() {
    var m = model(), c = m.coverage;
    if (!c) { return '<p class="empty">This starting point has no simple coverage check.</p>'; }
    if (c.same_header) {
      return '<p class="small">Same spray header as the drawing above, so the coverage check uses its marks (weak and blocked count as not spraying). Now: ' +
        (c.blocked_numbers.length ? 'nozzle' + (c.blocked_numbers.length > 1 ? 's ' : ' ') + esc(c.blocked_numbers.join(', ')) : 'none') + '.</p>';
    }
    return null;
  }
  // why the coverage check has its own numbers when its header is not the one drawn
  function coverageNote() {
    var m = model(), c = m.coverage;
    if (!c || c.same_header) { return ''; }
    return '<p class="small">' + (m.header ? 'The simple coverage check in this case uses its own header' : 'This starting point has no spray header model; the simple coverage check uses a header') +
      ' of ' + c.count + ' nozzles (barrel ' + mmInt(c.barrel_length_m) + ', pitch ' + mmSmall(c.pitch_m) + ')' + (m.header ? ', not the header drawn above, so its blocked nozzles are entered here.' : '. Its blocked nozzles are entered here.') +
      ' Now: ' + (c.blocked_numbers.length ? esc(c.blocked_numbers.join(', ')) : 'none') + '.</p>';
  }
  function routeView() {
    var r = model().route;
    if (!r.rows.length) { return '<p class="small soft">No other passes entered.</p>'; }
    var hits = r.rows.filter(function (x) { return x.is_pass; }).map(function (x) { return '"' + (x.label || 'unnamed') + '"'; });
    return '<p class="small" role="status">' + (hits.length ? 'The pass where the bands show is the same as route pass ' + esc(hits.join(', ')) + '.' :
      'The pass where the bands show is not one of the route passes: the tool treats it as one more pass.') +
      (r.computed_replaces ? ' The run replaces flow stress or friction with computed values and compares the passes again.' : '') + '</p>';
  }
  var VIEWS = {bands: bandsView, nozzles: nozzlesView, blocked: blockedView, route: routeView,
    coverage: function () { return coverageView() || ''; }, covnote: coverageNote};

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
      var prHide = (c.standing === 'CONTRADICTED' || c.standing === 'NOT_ASSESSABLE') ? ' class="pr-hide"' : '';
      h += '<div role="listitem"' + prHide + '><button type="button" class="bar' + (opts.old && old[id] && (old[id].score !== c.score || old[id].standing !== c.standing) ? ' changed' : '') + '" data-cause="' + id + '" aria-expanded="' + (S.openCause === id && !opts.compact ? 'true' : 'false') + '" aria-label="' + esc(label) + '"' + (opts.compact ? ' tabindex="-1"' : '') + '>' +
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
      var good = e.verdict === 'SUPPORTS';
      return '<li><span class="vw ' + (good ? 'ok' : 'no') + '"><span aria-hidden="true">' + (good ? '✓' : '✕') + '</span> ' + esc(e.verdict_words) +
        '</span> <span class="w">(' + esc(e.weight_words) + ')</span>: <span class="lab">' + esc(e.label) + '</span>' +
        '<ul class="evsub small">' + (e.seen_words ? '<li>' + esc(e.seen_words) + '</li>' : '') + (e.model_words ? '<li>' + esc(e.model_words) + '</li>' : '') +
        '<li>' + esc(e.expects_words) + '</li></ul></li>';
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
      '<div class="cols"><div><h4>What fits</h4>' + evidList(c.fits_because, 'Nothing entered speaks for it yet.') + '</div>' +
      '<div><h4>What speaks against it</h4>' + evidList(c.speaks_against, 'Nothing entered speaks against it.') + '</div></div>' +
      '<h4>Not looked at yet</h4>' + nl + '<h4>How to check on the floor</h4><p>' + esc(c.how_to_check) + '</p>' +
      (c.candidate_pitch ? '<h4>A candidate spacing (not evidence)</h4><p>' + esc(c.candidate_pitch.text) + '</p><ul class="small">' + c.candidate_pitch.rows.map(function (r) { return '<li>' + esc(r.text) + '</li>'; }).join('') + '</ul>' : '') + '</div>';
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
      '</ul><details class="noprint"><summary class="small">The rule</summary><p class="small soft">' + esc(t.rule) + '</p></details></details></div>' +
      '<p class="small soft noprint">The full list of what this tool assumes and cannot decide is in docs/limitations.md of the repository.</p>';
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
      (cmp.trust ? '<p>' + esc(cmp.trust.replace(/\bLOW\b/g, 'low').replace(/\bMODERATE\b/g, 'moderate').replace(/\bFAIR\b/g, 'fair')) + '</p>' : '') +
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
      items.push({icon: '<line x1="4" y1="14" x2="26" y2="2" stroke="var(--green)" stroke-width="2" stroke-dasharray="3 2"/>', text: 'Your band matches a predicted position (within ' + mmSmall(sv.tolerance_m) + ')'});
    }
    var listRows = sv.observed_positions_m.map(function (x, i) {
      var hits = [];
      sv.matches.forEach(function (m) { m.links.forEach(function (l) { if (l.matched && Math.abs(l.observed_m - x) < 1e-9) { hits.push(m.label.toLowerCase() + ' at ' + mmInt(l.predicted_m - sv.strip_start_m)); } }); });
      return '<li>Band ' + (i + 1) + ' at ' + mmInt(x - sv.strip_start_m) + ': ' + (hits.length ? 'matches ' + esc(hits.join('; ')) : 'no predicted position within ' + mmSmall(sv.tolerance_m)) + '</li>';
    }).join('');
    return '<div class="fig">' + svg + '</div>' + legend(items) + '<details><summary>The same as a list</summary><ul class="small">' + (listRows || '<li>No band positions entered.</li>') + '</ul></details>';
  }

  // ------------------------------------------------------------------ flatness roll and the other measurements
  // the flatness roll chart: one bar per zone, the modelled flatness, the neutral band level.
  // On the screen (spec = the card's chart) with its legend and axis titles; on the printed page
  // (print) at its earlier size, the caption above it saying the same.
  function shapemeterSvg(v, print, spec) {
    W = drawW();
    var barrel = v.barrel_length_m || (v.strip_end_m + v.strip_start_m);
    var sx = (W - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var t = v.threshold_i_units, mx = t;
    v.zones.forEach(function (z) { if (isNum(z.reading_i_units)) { mx = Math.max(mx, Math.abs(z.reading_i_units)); } });
    v.profile.i_units.forEach(function (y) { mx = Math.max(mx, Math.abs(y)); });
    var lg = print ? {s: '', h: 0} : chartLegend(spec || {legend: ['zone_shows', 'zone_not', 'profile']}, W, 0);
    var top = print ? 18 : lg.h + 24, hh = 150, y0 = top + hh / 2, k = (hh / 2 - 6) / mx;
    function Y(val) { return y0 - val * k; }
    var edge = v.strip_start_m, ms = markOf(spec, 'zone_shows'), mn = markOf(spec, 'zone_not'), mp = markOf(spec, 'profile');
    var s = lg.s + (print ? '' : yTitle(spec, 4, top - 10));
    s += '<rect x="' + X(v.strip_start_m) + '" y="' + top + '" width="' + ((v.strip_end_m - v.strip_start_m) * sx) + '" height="' + hh + '" fill="var(--strip)" opacity=".45"/>';
    s += '<line class="tick" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + y0 + '" y2="' + y0 + '"/>';
    [t, -t].forEach(function (y) { s += refLine(X(0), Y(y), X(barrel), Y(y), 'band_level'); });
    s += refText(X(barrel) - 2, Y(t) - 4, '± ' + sig(t, 3) + ' I-units: band level', 'end');
    v.zones.forEach(function (z) {
      var r = z.reading_i_units, x0 = X(z.start_m) + 1, wpx = Math.max(1, (z.end_m - z.start_m) * sx - 2);
      var where = 'Zone ' + (z.index + 1) + ' (' + mmInt(z.start_m - edge) + ' to ' + mmInt(z.end_m - edge) + ' from the strip edge)';
      if (!isNum(r)) {
        s += '<g class="mark" tabindex="0" aria-label="' + esc(where + ': does not cover the strip') + '" data-tip="' + esc(where + ': does not cover the strip') + '"><rect x="' + x0 + '" y="' + (y0 - 2) + '" width="' + wpx + '" height="4" fill="none" stroke="var(--soft)"/></g>';
        return;
      }
      var shows = Math.abs(r) >= t;
      var words = where + ' would read ' + sig(r, 3) + ' I-units: ' + (shows ? 'would show' : 'would probably not show');
      s += markG(barRect(shows ? ms : mn, x0, Math.min(Y(r), y0), wpx, Math.abs(Y(r) - y0)).replace('class="glyph"', 'class="glyph zbar' + (shows ? ' shows' : '') + '"'), words);
    });
    var pts = [];
    v.profile.z_m.forEach(function (z, i) { pts.push(X(z).toFixed(1) + ',' + Y(v.profile.i_units[i]).toFixed(1)); });
    if (pts.length) { s += lineOf(mp, pts); }
    var yb = top + hh;
    s += '<text x="' + X(v.strip_start_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">0</text><text x="' + X(v.strip_end_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round((v.strip_end_m - v.strip_start_m) * 1000).toLocaleString('en-GB') + '</text>';
    var label = 'What each shapemeter zone would read, with the modelled flatness as a line';
    if (print) {
      s += '<text x="' + X(v.strip_start_m) + '" y="' + (yb + 32) + '" font-size="12" class="softtext">mm from the strip edge nearest nozzle 1; up = longer (loose), down = shorter (tight)</text>';
      return '<svg viewBox="0 0 ' + W + ' ' + (yb + 40) + '" role="group" aria-label="' + label + '">' + s + '</svg>';
    }
    var xt = xTitle(spec, yb + 32, W);
    return svgOpen(W, yb + 22 + xt.h, label) + s + xt.s + '</svg>';
  }
  // the printed page: the flatness roll chart beside the strip picture (the page has room there)
  function shapemeterPrint(sum) {
    var v = sum.shapemeter_view;
    if (!v || !v.available) { return ''; }
    return '<div class="printonly smprint"><p class="smprint-h"><strong>What your flatness roll would show</strong> (bars: zone readings; line: modelled flatness; dashed: band level)</p>' +
      shapemeterSvg(v, true) + '<p class="smprint-w">' + esc(v.caveat) + '</p></div>';
  }
  // the printed page: the flatness-control card in a compact form (takeaway, valve map, the
  // fixed sentence); its card on the screen is folded under its heading
  function loopPrint(sum) {
    var c = (sum.addon_cards || []).filter(function (x) { return x.id === 'loop' && x.chart; })[0];
    if (!c) { return ''; }
    return '<div class="printonly lpprint"><p class="smprint-h"><strong>' + esc(c.title) + '</strong>: ' + esc(c.takeaway) + '</p>' +
      chartSvg(c.chart) + '<p class="smprint-w">' + esc(c.caveat || '') + '</p></div>';
  }
  function nextChecks(sum) {
    if (!sum.next_checks.length) { return '<p class="empty">No further checks listed.</p>'; }
    var more = sum.next_checks.length - 3;
    return '<ul class="checklist">' + sum.next_checks.map(function (c, i) {
      var qs = c.questions.filter(function (q) { return Q[q]; });
      var key = 'nc-' + i;
      var open = S.openChecks[key];
      return '<li' + (i >= 3 ? ' class="pr-hide"' : '') + '><div class="row"><span>' + esc(c.text) + '</span>' + (qs.length ? '<button type="button" class="btn noprint" data-check="' + key + '" data-qs="' + esc(qs.join(',')) +
        '" aria-expanded="' + (open ? 'true' : 'false') + '">' + (open ? 'Close' : 'I have checked this') + '</button>' : '<span class="small soft">(no question in the form for this)</span>') + '</div>' +
        (open ? inlineQs(qs) : '') + '</li>';
    }).join('') + '</ul>' + (more > 0 ? '<p class="printonly small">… and ' + more + ' more (see the app).</p>' : '');
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
      '<p class="statusline"><span aria-hidden="true">ⓘ</span><span>' + esc(sum.status_words) + '</span></p>' + profileLine(sum, run) + addonIndex(sum) + '</div>' + trustBox(sum.trust) + '</div></section>';
    var missing = sum.not_assessable.filter(function (x) { return x.kind === 'not_assessable' || x.kind === 'failed'; });
    if (sum.roll_gap_failed && missing.length) {
      h += '<section class="card" id="not-assessed-top"><h2>What could not be assessed</h2><p class="howto">How to read this: the roll-gap model could not compute the pass where the bands show, so these parts of the screening are missing. The shortlist below rests on the rest.</p>' +
        '<ul>' + missing.map(function (x) { return '<li><strong>' + esc(x.what) + '</strong>: ' + esc(x.why) + '</li>'; }).join('') + '</ul></section>';
    }
    h += '<section class="card" id="shortlist"><h2>The shortlist</h2><p class="howto">How to read this: each bar is one possible cause of ' + esc(sum.family.observed_words) +
      '. Bars to the right fit what you entered; bars left of zero do not fit. Select a bar for the details.</p>' + note + changeBox(sum) +
      barsHtml(sum, shortIds, {old: S.baseSummary}) +
      (otherIds.length ? '<details class="more"' + (S.otherOpen ? ' open' : '') + ' data-other="1"><summary>Causes of the other kind, and why they do not fit</summary>' + barsHtml(sum, otherIds, {old: S.baseSummary}) + '</details>' : '') +
      pendingBar() + '</section>';
    if (fam === 'transverse' || (!sum.strip_view.available && sum.along_view.available)) {
      h += '<section class="card"><h2>Along the strip</h2><p class="howto">How to read this: the top strip shows the mark spacing you measured, the bottom one the spacing of the best-fitting candidate with a spacing.</p>' +
        (sum.along_view.available ? '<div class="fig">' + alongSvg(sum.along_view) + '</div>' : '<p class="empty">No spacing measured yet: measure the mark spacing at two speeds to see this picture.</p>') + '</section>';
    } else {
      h += '<section class="card stripcard"><h2>Where across the width</h2><p class="howto">How to read this: the strip seen from above with the spray header over it. Solid bars are the bands you saw; outlined boxes with a letter are where the model puts a candidate; the line above shows where the roll grows. Hover, tap or tab to a mark for its position.</p>' +
        shapemeterPrint(sum) + stripResult(sum) + loopPrint(sum) + '</section>';
    }
    h += '<section class="card"><h2>What to check next</h2><p class="howto">How to read this: measurements that would narrow the shortlist. Tick one you have done, answer it, and update the result.</p>' + nextChecks(sum) + pendingBar() + '</section>';
    resetGloss();
    h += addonCards(sum);
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
      '<h3 class="noprint">Could not be assessed</h3><ul class="small noprint">' + (sum.not_assessable.length ? sum.not_assessable.map(function (x) { return '<li>' + esc(x.what) + ': ' + esc(x.why) + '</li>'; }).join('') : '<li>Everything was assessed.</li>') + '</ul>' +
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
  // ------------------------------------------------------------------ glossary: first use per screen
  // Technical terms carry a plain-word tooltip the first time they appear on a screen; the
  // terms and meanings are band_plain.GLOSSARY (one source), sent with /api/meta.
  var glossUsed = {};
  function resetGloss() { glossUsed = {}; }
  function gloss(text) {
    var out = esc(text);
    if (!M || !M.glossary) { return out; }
    Object.keys(M.glossary).sort(function (a, b) { return b.length - a.length; }).forEach(function (term) {
      if (glossUsed[term]) { return; }
      var re = new RegExp('(^|[^\\w-])(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + 's?)(?![\\w-])', 'i');
      var m = re.exec(out);
      if (!m || /<[^>]*$/.test(out.slice(0, m.index + m[1].length))) { return; }
      glossUsed[term] = true;
      var at = m.index + m[1].length, word = m[2];
      var tip = esc(term + ': ' + M.glossary[term]);
      out = out.slice(0, at) + '<span class="term mark" tabindex="0" data-tip="' + tip + '" aria-label="' + esc(word) + ' (' + esc(M.glossary[term]) + ')">' + word + '</span>' + out.slice(at + word.length);
    });
    return out;
  }

  // ------------------------------------------------------------------ chart helpers
  // Every chart is drawn from its spec (band_plain): each series ("mark") has one shape, fill,
  // colour and line style, used for the chart AND its legend by the same function; reference
  // lines and ranges are neutral; the axes carry their titles with units; the legend lists only
  // the marks that are not labelled on the chart. Focusable marks give the exact value (hover,
  // keyboard focus, tap); "The same as a list" is the text alternative.
  var COL = {blue: 'var(--blue)', orange: 'var(--orange)', purple: 'var(--purple)', neutral: 'var(--soft)'};
  var TEXTCOL = {blue: 'var(--blue)', orange: 'var(--orange-text)', purple: 'var(--purple)', neutral: 'var(--soft)'};
  var DASH = {solid: '', dashed: '7 4', dotted: '2 3'};
  // the flatness roll chart of the printed page has no card spec: the same marks as the card
  var ZONE_MARKS = {zone_shows: {id: 'zone_shows', label: 'zone that would show', shape: 'bar', fill: 'solid', colour: 'blue', line: 'solid'},
    zone_not: {id: 'zone_not', label: 'zone that would probably not show', shape: 'bar', fill: 'open', colour: 'blue', line: 'solid'},
    profile: {id: 'profile', label: 'modelled flatness', shape: 'line', fill: 'solid', colour: 'orange', line: 'solid'}};
  function markG(inner, tip) {
    return '<g class="mark" tabindex="0" aria-label="' + esc(tip) + '" data-tip="' + esc(tip) + '">' + inner + '</g>';
  }
  function markOf(c, id) {
    var m = ((c && c.marks) || []).filter(function (x) { return x.id === id; })[0];
    return m || ZONE_MARKS[id] || {id: id, label: id, shape: 'circle', fill: 'solid', colour: 'blue', line: 'solid'};
  }
  function paint(m) {
    var col = COL[m.colour] || COL.blue;
    if (m.shape === 'line') { return ' fill="none" stroke="' + col + '" stroke-width="2.4"' + (DASH[m.line] ? ' stroke-dasharray="' + DASH[m.line] + '"' : ''); }
    if (m.fill === 'open') { return ' fill="var(--card)" stroke="' + col + '" stroke-width="2"'; }
    return ' fill="' + col + '"' + (m.shape === 'bar' ? '' : ' stroke="var(--card)" stroke-width="1.5"');
  }
  // one mark at (x, y): the chart and the legend both draw it with this
  function glyph(m, x, y) {
    var tag = ' class="glyph" data-mark="' + esc(m.id) + '"' + paint(m), r = 5;
    if (m.shape === 'diamond') { r = 6; return '<path' + tag + ' d="M' + x + ' ' + (y - r) + 'L' + (x + r) + ' ' + y + 'L' + x + ' ' + (y + r) + 'L' + (x - r) + ' ' + y + 'Z"/>'; }
    if (m.shape === 'square') { return '<rect' + tag + ' x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r + '" height="' + 2 * r + '"/>'; }
    if (m.shape === 'line') { return '<line' + tag + ' x1="' + (x - 11) + '" x2="' + (x + 11) + '" y1="' + y + '" y2="' + y + '"/>'; }
    if (m.shape === 'bar') { return '<rect' + tag + ' x="' + (x - 8) + '" y="' + (y - 5) + '" width="16" height="10"/>'; }
    return '<circle' + tag + ' cx="' + x + '" cy="' + y + '" r="' + r + '"/>';
  }
  function barRect(m, x, y, w, h) { return '<rect class="glyph" data-mark="' + esc(m.id) + '"' + paint(m) + ' x="' + x + '" y="' + y + '" width="' + Math.max(1, w) + '" height="' + Math.max(1, h) + '"/>'; }
  function lineOf(m, pts) { return '<polyline class="glyph" data-mark="' + esc(m.id) + '"' + paint(m) + ' points="' + pts.join(' ') + '"/>'; }
  function labelText(m, x, y, anchor, px) {
    return '<text x="' + x + '" y="' + y + '" font-size="' + (px || 12) + '" style="fill:' + (TEXTCOL[m.colour] || 'var(--ink)') + '"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + ' class="dlab" data-mark="' + esc(m.id) + '">' + esc(m.label) + '</text>';
  }
  // the legend: the marks the spec lists, each drawn by glyph(), wrapped to the width
  function chartLegend(c, w, y0) {
    var ids = (c && c.legend) || [];
    if (!ids.length) { return {s: '', h: 0}; }
    var x = 4, y = y0 + 9, s = '<g class="legend" role="list" aria-label="Legend">';
    ids.forEach(function (id) {
      var m = markOf(c, id), tw = 30 + String(m.label).length * 6.5;
      if (x > 4 && x + tw > w) { x = 4; y += 20; }
      s += '<g class="legend-item" role="listitem" data-mark="' + esc(id) + '">' + glyph(m, x + 11, y) + '<text x="' + (x + 27) + '" y="' + (y + 4) + '" font-size="12">' + esc(m.label) + '</text></g>';
      x += tw + 14;
    });
    return {s: s + '</g>', h: y - y0 + 18};
  }
  function axisWords(a) { return a ? a.title + (a.unit ? ', ' + a.unit : a.dimensionless ? ' (no unit)' : '') : ''; }
  // the x title under the ticks, wrapped; returns {s, h}
  function xTitle(c, y, w) {
    var t = axisWords(c && c.x_axis);
    if (!t) { return {s: '', h: 0}; }
    return {s: wrapText(4, y, t, w - 8, 'class="axis-title" data-axis="x"'), h: wrapLines(t, w - 8).length * 14.4};
  }
  function yTitle(c, x, y) {
    var t = axisWords(c && c.y_axis);
    return t ? '<text x="' + x + '" y="' + y + '" font-size="12" class="axis-title" data-axis="y">' + esc(t) + '</text>' : '';
  }
  function refLine(x1, y1, x2, y2, id) { return '<line class="ref" data-ref="' + esc(id) + '" x1="' + x1 + '" x2="' + x2 + '" y1="' + y1 + '" y2="' + y2 + '"/>'; }
  function refArea(x, y, w, h, id) { return '<rect class="ref-area" data-ref="' + esc(id) + '" x="' + x + '" y="' + y + '" width="' + Math.max(1, w) + '" height="' + h + '"/>'; }
  function refText(x, y, text, anchor) { return '<text class="ref-label" x="' + x + '" y="' + y + '" font-size="11"' + (anchor ? ' text-anchor="' + anchor + '"' : '') + '>' + esc(text) + '</text>'; }
  function refLabel(c, id) { var r = ((c && c.references) || []).filter(function (x) { return x.id === id; })[0]; return r ? r.label : id; }
  function svgOpen(w, h, label) { return '<svg viewBox="0 0 ' + w + ' ' + Math.ceil(h) + '" role="group" aria-label="' + esc(label) + '">'; }
  function niceRange(lo, hi) {
    if (lo === hi) { lo -= 1; hi += 1; }
    var pad = (hi - lo) * 0.08; return [lo - pad, hi + pad];
  }
  function ticks(lo, hi, n) {
    var step = Math.pow(10, Math.floor(Math.log10((hi - lo) / n)));
    [1, 2, 2.5, 5, 10].some(function (k) { if ((hi - lo) / (step * k) <= n) { step *= k; return true; } return false; });
    var out = []; for (var t = Math.ceil(lo / step) * step; t <= hi + 1e-12; t += step) { out.push(Number(t.toFixed(10))); }
    return out;
  }
  function chartWidth() { return drawW(); }
  // words in a chart, broken into lines that fit maxW (about 6.4 px a character at 12 px)
  function wrapLines(text, maxW, px) {
    var n = Math.max(8, Math.floor(maxW / ((px || 12) * 0.54))), out = [], cur = '';
    String(text).split(' ').forEach(function (word) {
      if (cur && (cur + ' ' + word).length > n) { out.push(cur); cur = word; } else { cur = cur ? cur + ' ' + word : word; }
    });
    if (cur) { out.push(cur); }
    return out;
  }
  function wrapText(x, y, text, maxW, attrs, px) {
    var ls = wrapLines(text, maxW, px);
    return '<text x="' + x + '" y="' + y + '" font-size="' + (px || 12) + '" ' + (attrs || '') + '>' + ls.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 1.2 * (px || 12) : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
  }
  // row labels of a chart with one row per pass or record: up to two lines, right-aligned
  // (a "(…)" note goes on its own line; each row is as tall as its label needs)
  function rowLabels(rows, lw, base) {
    var tops = [], hs = [], y = 0;
    var ls = rows.map(function (r) {
      var t = String(r.label || ''), k = t.indexOf(' (');
      var l = k > 0 && t.length * 6.5 > lw - 10 ? [t.slice(0, k)].concat(wrapLines(t.slice(k + 1), lw - 10, 12)) : wrapLines(t, lw - 10, 12);
      return l.slice(0, 4);
    });
    ls.forEach(function (l) { var h = Math.max(base || 24, 10 + 14 * l.length); tops.push(y); hs.push(h); y += h; });
    return {lines: ls, tops: tops, hs: hs, total: y};
  }
  function rowLabel(lines, x, yMid, soft) {
    var y = yMid + 4 - (lines.length - 1) * 7;
    return '<text x="' + x + '" y="' + y + '" font-size="12" text-anchor="end"' + (soft ? ' class="softtext"' : '') + '>' + lines.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 14 : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
  }
  // a horizontal value axis under rows: ticks and their numbers
  function xTicks(tk, X, yTop, yBot, fmt) {
    return tk.map(function (t) { return '<line class="grid" x1="' + X(t) + '" x2="' + X(t) + '" y1="' + yTop + '" y2="' + yBot + '"/><text x="' + X(t) + '" y="' + (yBot + 14) + '" font-size="11" text-anchor="middle">' + (fmt ? fmt(t) : sig(t, 3)) + '</text>'; }).join('');
  }

  // a profile across the strip, on the strip picture's horizontal scale (lines labelled on the chart)
  function widthLines(c) {
    var w = chartWidth(), barrel = c.barrel_length_m || (c.strip_end_m + c.strip_start_m);
    var sx = (w - ML - MR) / barrel;
    function X(m) { return ML + m * sx; }
    var all = []; c.series.forEach(function (s) { all = all.concat(s.values); });
    var r = niceRange(Math.min.apply(null, all.concat([0])), Math.max.apply(null, all.concat([0])));
    var lg = chartLegend(c, w, 0), top = lg.h + 24, hh = 150;
    function Y(v) { return top + (r[1] - v) / (r[1] - r[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 10);
    s += '<rect x="' + X(c.strip_start_m) + '" y="' + top + '" width="' + ((c.strip_end_m - c.strip_start_m) * sx) + '" height="' + hh + '" fill="var(--strip)" opacity=".4"/>';
    ticks(r[0], r[1], 4).forEach(function (t) {
      s += '<line class="grid" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (X(0) + 2) + '" y="' + (Y(t) - 3) + '" font-size="11" class="softtext">' + sig(t, 3) + '</text>';
    });
    s += '<line class="tick" x1="' + X(0) + '" x2="' + X(barrel) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
    c.series.forEach(function (ser, k) {
      var m = markOf(c, ser.id || ('s' + k));
      s += lineOf(m, ser.z_m.map(function (z, i) { return X(z).toFixed(1) + ',' + Y(ser.values[i]).toFixed(1); }));
      var ip = 0; ser.values.forEach(function (v, i) { if (Math.abs(v) > Math.abs(ser.values[ip])) { ip = i; } });
      var x = X(ser.z_m[ip]), y = Y(ser.values[ip]);
      var tip = ser.label + ': ' + sig(ser.values[ip], 3) + ' ' + c.unit + ' at ' + mmInt(ser.z_m[ip] - c.strip_start_m) + ' from the strip edge (' + (ser.values[ip] > 0 ? 'longer fibre: loose' : 'shorter fibre: tight') + ')';
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, x, y), tip);
      var right = x > w * 0.7;
      s += labelText(m, right ? x - 8 : x + 8, y + (k ? 16 : -8), right ? 'end' : null);
    });
    var yb = top + hh;
    s += '<text x="' + X(c.strip_start_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">0</text><text x="' + X(c.strip_end_m) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round((c.strip_end_m - c.strip_start_m) * 1000).toLocaleString('en-GB') + '</text>';
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Profile across the strip in ' + c.unit) + s + xt.s + '</svg>';
  }

  // one horizontal bar per row (a share in % or a factor), with one neutral reference line
  function barsChart(c) {
    var m = markOf(c, ((c.marks || [])[0] || {}).id), pct = c.unit === 'percent';
    var w = Math.min(760, chartWidth()), lw = Math.min(200, w * 0.4);
    var rl = rowLabels(c.rows, lw, 26);
    var vals = c.rows.map(function (r) { return r.value; }).concat([c.line]);
    var lo = pct ? 0 : Math.min(0.8, Math.min.apply(null, vals)), hi = pct ? 1 : Math.max.apply(null, vals) * 1.08;
    function X(v) { return lw + (v - lo) / (hi - lo) * (w - lw - 16); }
    function fmt(v) { return pct ? sig(v * 100, 2) + ' %' : sig(v, 3) + ' times'; }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s;
    s += xTicks(pct ? [0, 0.25, 0.5, 0.75, 1] : ticks(lo, hi, 4), X, top, yb, pct ? function (t) { return Math.round(t * 100); } : null);
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i], rowH = rl.hs[i], bh = Math.min(rowH - 8, 18);
      s += rowLabel(rl.lines[i], lw - 8, y + rowH / 2);
      s += markG(barRect(m, X(lo), y + (rowH - bh) / 2, X(r.value) - X(lo), bh), r.tip || (r.label + ': ' + fmt(r.value)));
      var inside = X(r.value) + 4 + fmt(r.value).length * 6.2 > w;     // no room on the right: in the bar
      s += '<text x="' + (inside ? X(r.value) - 4 : X(r.value) + 4) + '" y="' + (y + rowH / 2 + 4) + '" font-size="11"' + (inside ? ' text-anchor="end" class="inbar"' : '') + '>' + fmt(r.value) + '</text>';
    });
    s += refLine(X(c.line), top - 4, X(c.line), yb, (c.references[0] || {}).id || 'line') + refText(X(c.line) + 4, top - 8, c.line_label);
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Bars: ' + axisWords(c.x_axis)) + s + xt.s + '</svg>';
  }

  // per pass, both friction levels on one logarithmic scale (they differ greatly)
  function passLevels(c) {
    var mw = markOf(c, 'with'), mo = markOf(c, 'without');
    var w = Math.min(760, chartWidth()), lw = Math.min(210, w * 0.4);
    var rows = c.rows.map(function (r) { var l = String(r.label); return {label: r.credible ? l : /\)$/.test(l) ? l.slice(0, -1) + ', not credible)' : l + ' (not credible)'}; });
    var rl = rowLabels(rows, lw, 26);
    var vals = []; c.rows.forEach(function (r) { vals.push(Math.abs(r.with_feedback), Math.abs(r.compliance_only)); });
    var lo = Math.floor(Math.log10(Math.min.apply(null, vals))), hi = Math.ceil(Math.log10(Math.max.apply(null, vals)));
    function X(v) { return lw + (Math.log10(Math.abs(v)) - lo) / (hi - lo) * (w - lw - 20); }
    var lg = chartLegend(c, w, 0), top = lg.h + 8, yb = top + rl.total;
    var s = lg.s;
    var tk = []; for (var e = lo; e <= hi; e++) { tk.push(Math.pow(10, e)); }
    s += xTicks(tk, X, top, yb, function (t) { return sig(t, 1); });
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y, !r.credible);
      s += '<line class="tick" x1="' + X(r.with_feedback) + '" x2="' + X(r.compliance_only) + '" y1="' + y + '" y2="' + y + '"/>';
      s += markG(glyph(mw, X(r.with_feedback), y), r.label + ', ' + mw.label + ': ' + sig(r.with_feedback, 2) + ' I-units for 1 % more friction at one place');
      s += markG(glyph(mo, X(r.compliance_only), y), r.label + ', without the feedback (compliance alone): ' + sig(r.compliance_only, 2) + ' I-units for 1 % more friction');
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Flatness per 1 % friction, with and without the exit-tension feedback, per pass') + s + xt.s + '</svg>';
  }

  // friction from each measured quantity, with the range its measuring error allows
  var KIND_WORDS = {force: 'from the force', slip: 'from the forward slip', torque: 'from the torque'};
  function recordsChart(c) {
    var w = Math.min(760, chartWidth()), lw = Math.min(150, w * 0.28);
    var rl = rowLabels(c.rows, lw, Math.max(26, 12 + 10 * Math.max.apply(null, c.rows.map(function (r) { return r.points.length; }))));
    var vals = [c.case_value]; c.rows.forEach(function (r) { r.points.forEach(function (p) { vals.push(p.value, p.low, p.high); }); });
    vals = vals.filter(isNum);
    var rg = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals));
    function X(v) { return lw + (v - rg[0]) / (rg[1] - rg[0]) * (w - lw - 16); }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s + xTicks(ticks(rg[0], rg[1], 4), X, top, yb);
    if (isNum(c.case_value)) {
      var xc = X(c.case_value), right = xc > w * 0.75;
      s += markG(refLine(xc, top - 4, xc, yb, 'case'), refLabel(c, 'case') + ': a friction coefficient of ' + sig(c.case_value, 3) + ' (no unit)') + refText(right ? xc - 4 : xc + 4, top - 8, refLabel(c, 'case'), right ? 'end' : null);
    }
    c.rows.forEach(function (r, i) {
      var y0 = top + rl.tops[i], rowH = rl.hs[i], n = r.points.length;
      s += rowLabel(rl.lines[i], lw - 8, y0 + rowH / 2);
      r.points.forEach(function (p, k) {
        var m = markOf(c, p.kind), y = y0 + rowH / 2 + (k - (n - 1) / 2) * 10;
        if (isNum(p.low) && isNum(p.high)) { s += '<line class="interval" data-mark="' + esc(m.id) + '" stroke="' + COL[m.colour] + '" x1="' + X(p.low) + '" x2="' + X(p.high) + '" y1="' + y + '" y2="' + y + '"/>'; }
        s += markG(glyph(m, X(p.value), y), r.label + ', friction ' + KIND_WORDS[p.kind] + ': ' + sig(p.value, 3) + ' (no unit)' + (isNum(p.low) ? ', between ' + sig(p.low, 3) + ' and ' + sig(p.high, 3) + ' for the measuring error' : ''));
      });
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Friction from each pass record') + s + xt.s + '</svg>';
  }

  // the roll surface over one turn: temperature against angle after the roll gap
  function cycleChart(c) {
    var w = Math.min(860, chartWidth()), l = 34, r = Math.round(Math.min(170, w * 0.3)), hh = 170;
    // labels at the line ends where each fits on one line; otherwise (a phone) the legend lists
    // the same marks, drawn the same way, and the plot takes the whole width
    var fits = c.series.every(function (ser, k) { return wrapLines(markOf(c, 's' + k).label, r - 10, 11).length === 1; });
    if (!fits) { c = Object.assign({}, c, {legend: c.series.map(function (ser, k) { return 's' + k; })}); r = 14; }
    var lg = chartLegend(c, w, 0), top = lg.h + 26;
    var labs = [], all = []; c.series.forEach(function (s) { all = all.concat(s.temperature_k); });
    var rg = niceRange(Math.min.apply(null, all) - 273.15, Math.max.apply(null, all) - 273.15);
    function X(a) { return l + a / 360 * (w - l - r); }
    function Y(tc) { return top + (rg[1] - tc) / (rg[1] - rg[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 12);
    ticks(rg[0], rg[1], 5).forEach(function (t) { s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (l - 4) + '" y="' + (Y(t) + 4) + '" font-size="11" text-anchor="end">' + sig(t, 3) + '</text>'; });
    [0, 90, 180, 270, 360].forEach(function (a) { s += '<text x="' + X(a) + '" y="' + (top + hh + 15) + '" font-size="11" text-anchor="middle">' + a + '</text>'; });
    c.series.forEach(function (ser, k) {
      var m = markOf(c, 's' + k);
      // unwrap the angle so the line runs 0..360 from the roll gap exit
      var pts = ser.angle_deg.map(function (a, i) { return [a, ser.temperature_k[i] - 273.15]; }).sort(function (p, q) { return p[0] - q[0]; });
      s += lineOf(m, pts.map(function (p) { return X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }));
      var end = pts[pts.length - 1];
      labs.push({m: m, y: Y(end[1]) + 4});
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, X(end[0]), Y(end[1])), ser.label + ': ' + sig(end[1], 3) + ' °C just before the roll gap');
    });
    // labels beside the line ends, pushed apart and kept inside the plot
    labs.sort(function (a, b) { return a.y - b.y; });
    var prev = top + 4;
    labs.forEach(function (lb) { lb.ls = wrapLines(lb.m.label, r - 10, 11); lb.y = Math.max(lb.y, prev); prev = lb.y + lb.ls.length * 13.2 + 3; });
    var floor = top + hh;
    for (var j = labs.length - 1; j >= 0; j--) {
      var lim = j === labs.length - 1 ? floor - (labs[j].ls.length - 1) * 13.2 : labs[j + 1].y - labs[j].ls.length * 13.2 - 3;
      if (labs[j].y > lim) { labs[j].y = lim; }
    }
    if (!fits) { labs = []; }
    labs.forEach(function (lb) {
      var x = w - r + 8;
      s += '<text x="' + x + '" y="' + lb.y + '" font-size="11" style="fill:' + TEXTCOL[lb.m.colour] + '" class="dlab" data-mark="' + esc(lb.m.id) + '">' + lb.ls.map(function (t, i) { return '<tspan x="' + x + '" dy="' + (i ? 13.2 : 0) + '">' + esc(t) + '</tspan>'; }).join('') + '</text>';
    });
    var yb = top + hh, xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Roll surface temperature over one turn at three places') + s + xt.s + '</svg>';
  }

  // heat share per pass: entered and computed, with the measured range as a neutral area
  function sharesChart(c) {
    var me = markOf(c, 'entered'), mc = markOf(c, 'computed');
    var w = Math.min(760, chartWidth()), lw = Math.min(200, w * 0.4);
    var rl = rowLabels(c.rows, lw, 24);
    function X(v) { return lw + v * (w - lw - 16); }
    var lg = chartLegend(c, w, 0), top = lg.h + 20, yb = top + rl.total;
    var s = lg.s;
    if (c.band) {
      s += markG(refArea(X(c.band[0]), top, X(c.band[1]) - X(c.band[0]), rl.total, 'measured'), refLabel(c, 'measured') + ': ' + sig(c.band[0] * 100, 2) + ' to ' + sig(c.band[1] * 100, 2) + ' % of the heat stays in the strip');
      s += refText(X(c.band[1]) + 4, top - 8, refLabel(c, 'measured'));
    }
    s += xTicks([0, 0.25, 0.5, 0.75, 1], X, top, yb, function (t) { return Math.round(t * 100); });
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y);
      if (isNum(r.entered)) { s += markG(glyph(me, X(r.entered), y), r.label + ', entered: ' + sig(r.entered * 100, 2) + ' % of the heat stays in the strip'); }
      s += markG(glyph(mc, X(Math.max(0, Math.min(1, r.computed))), y), r.label + ', computed by the tool: ' + sig(r.computed * 100, 2) + ' %');
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Heat share to the strip per pass, entered and computed') + s + xt.s + '</svg>';
  }

  // the published foil case on one line: two models, the published figure and the equations' range
  function loadsChart(c) {
    var w = Math.min(760, chartWidth()), l = 16, r = 16, y = 30;
    var lo = Math.min(c.range[0], c.points[1].value) - 10, hi = Math.max(c.range[1], c.published) + 10;
    function X(v) { return l + (v - lo) / (hi - lo) * (w - l - r); }
    var s = '<line class="tick" x1="' + X(lo) + '" x2="' + X(hi) + '" y1="' + y + '" y2="' + y + '"/>';
    s += markG(refArea(X(c.range[0]), y - 12, X(c.range[1]) - X(c.range[0]), 24, 'family'), refLabel(c, 'family') + ' give a load of ' + Math.round(c.range[0]) + ' to ' + Math.round(c.range[1]) + ' (no unit), depending on a detail the paper does not state');
    s += markG(refLine(X(c.published), y - 16, X(c.published), y + 16, 'published'), 'Published figure: a load of ' + c.published + ' (no unit)');
    s += refText(X(c.published), y + 30, refLabel(c, 'published'), 'middle');
    var fam = refLabel(c, 'family') + ': ' + Math.round(c.range[0]) + ' to ' + Math.round(c.range[1]), fx = X(c.range[0]);
    s += refText(fx + fam.length * 5.8 > w ? w - 2 : fx, y + 46, fam, fx + fam.length * 5.8 > w ? 'end' : null);
    s += ticks(lo, hi, 5).map(function (t) { return '<text x="' + X(t) + '" y="' + (y + 64) + '" font-size="11" text-anchor="middle">' + sig(t, 3) + '</text>'; }).join('');
    // the first model's label above the line, the second's below it: they never meet
    c.points.forEach(function (p, k) {
      var m = markOf(c, p.id), xl = X(p.value), left = xl < w * 0.6;
      s += markG(glyph(m, xl, y), p.label + ': a load of ' + Math.round(p.value) + ' (no unit) on the published foil case');
      s += labelText({id: m.id, label: p.label + ' ' + Math.round(p.value), colour: m.colour}, left ? Math.max(2, xl - 6) : Math.min(w - 2, xl + 6), k ? y + 30 : y - 18, left ? null : 'end', 11);
    });
    var xt = xTitle(c, y + 84, w);
    return svgOpen(w, y + 74 + xt.h, 'Loads on the one published foil case') + s + xt.s + '</svg>';
  }

  // the one range chart: for each row a bar from low to high (the possible range), the value the
  // scores or the model use as a distinct mark, other values as points; neutral reference lines
  function rangeChart(c) {
    var w = Math.min(760, chartWidth()), lw = Math.min(170, w * 0.32);
    var rl = rowLabels(c.rows, lw, 30);
    var vals = [];
    c.rows.forEach(function (r) { [r.low, r.high].concat(r.points.map(function (p) { return p.value; })).forEach(function (v) { if (isNum(v)) { vals.push(v); } }); });
    (c.references || []).forEach(function (x) { if (isNum(x.value)) { vals.push(x.value); } });
    var log = !!c.log && vals.every(function (v) { return v > 0; });
    var lo, hi, X, tk;
    if (log) {
      lo = Math.floor(Math.log10(Math.min.apply(null, vals))); hi = Math.ceil(Math.log10(Math.max.apply(null, vals)));
      if (hi === lo) { hi += 1; }
      X = function (v) { return lw + (Math.log10(v) - lo) / (hi - lo) * (w - lw - 20); };
      tk = []; for (var e = lo; e <= hi; e++) { tk.push(Math.pow(10, e)); }
    } else {
      var rg = niceRange(Math.min.apply(null, vals), Math.max.apply(null, vals)); lo = rg[0]; hi = rg[1];
      X = function (v) { return lw + (v - lo) / (hi - lo) * (w - lw - 20); };
      tk = ticks(lo, hi, w < 500 ? 3 : 5);
    }
    var refs = (c.references || []).filter(function (x) { return isNum(x.value); });
    var lg = chartLegend(c, w, 0), top = lg.h + 8 + refs.length * 14, yb = top + rl.total;
    var s = lg.s + xTicks(tk, X, top, yb, function (t) { return sig(t, 3); });
    refs.forEach(function (x, k) {
      var xr = X(x.value), right = xr > w * 0.7;
      s += markG(refLine(xr, top - 4, xr, yb, x.id), x.tip || (x.label + ': ' + sig(x.value, 3) + ' ' + axisWords(c.x_axis)));
      s += refText(right ? xr - 4 : xr + 4, lg.h + 10 + k * 14, x.label, right ? 'end' : null);
    });
    var mr = markOf(c, 'range');
    c.rows.forEach(function (r, i) {
      var y = top + rl.tops[i] + rl.hs[i] / 2;
      s += rowLabel(rl.lines[i], lw - 8, y);
      if (isNum(r.low) && isNum(r.high) && r.high > r.low && (c.marks || []).some(function (m) { return m.id === 'range'; })) {
        s += markG(barRect(mr, X(r.low), y - 7, X(r.high) - X(r.low), 14), r.label + ': from ' + sig(r.low, 3) + ' to ' + sig(r.high, 3) + ' ' + (r.unit || 'no unit') + (r.meaning ? '; ' + r.meaning : ''));
      }
      // the value the scores use is drawn last, so that no other point hides it
      r.points.slice().sort(function (a, b) { return (a.id === 'used') - (b.id === 'used'); }).forEach(function (p) { s += markG(glyph(markOf(c, p.id), X(p.value), y), p.tip || (r.label + ': ' + sig(p.value, 3))); });
    });
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Range: ' + axisWords(c.x_axis)) + s + xt.s + '</svg>';
  }

  // the valve map of the flatness loop: one row per valve, its level as the shade over time, and
  // under it the largest zone error the flatness roll would read
  function valveMap(c) {
    var w = chartWidth(), l = 34, r = 8, mv = markOf(c, 'level'), me = markOf(c, 'error');
    var n = (c.levels[0] || []).length, rowH = Math.max(5, Math.min(12, Math.floor(160 / Math.max(1, n))));
    var lg = chartLegend(c, w, 0), top = lg.h + 22, mapH = n * rowH, gap = 30, errH = 70;
    var t0 = 0, t1 = c.time_s[c.time_s.length - 1] || 1;
    function X(t) { return l + (t - t0) / (t1 - t0) * (w - l - r); }
    var s = lg.s + '<text x="4" y="' + (top - 8) + '" font-size="12" class="axis-title" data-axis="y">valve (control zone), 1 at the top</text>';
    for (var z = 0; z < n; z++) {
      var k0 = 0;
      for (var k = 1; k <= c.time_s.length; k++) {
        if (k === c.time_s.length || c.levels[k][z] !== c.levels[k0][z]) {
          var lev = c.levels[k0][z], xa = X(k0 ? c.time_s[k0 - 1] : t0), xb = X(c.time_s[k - 1]);
          // closed is a pale tint with an outline (never the card itself), open the full colour;
          // the lightness ramp is steep in the upper half, where most valves sit
          var op = 0.1 + 0.9 * Math.pow(lev, 2.2);
          s += '<rect class="valve-outline" x="' + xa + '" y="' + (top + z * rowH) + '" width="' + Math.max(1, xb - xa) + '" height="' + (rowH - 1) + '"/>';
          s += markG(barRect(mv, xa, top + z * rowH, xb - xa, rowH - 1).replace('/>', ' fill-opacity="' + op.toFixed(2) + '"/>'),
            'Valve ' + (z + 1) + ': ' + Math.round(lev * 100) + ' % open from ' + Math.round(k0 ? c.time_s[k0 - 1] : 0) + ' s to ' + Math.round(c.time_s[k - 1]) + ' s');
          if (k < c.time_s.length) { s += '<line class="valve-change" x1="' + xb + '" x2="' + xb + '" y1="' + (top + z * rowH) + '" y2="' + (top + z * rowH + rowH - 1) + '"/>'; }
          k0 = k;
        }
      }
      if (w >= 600 || z % Math.max(1, Math.ceil(n / 7)) === 0) { s += '<text x="' + (l - 4) + '" y="' + (top + z * rowH + rowH - 1) + '" font-size="10" text-anchor="end">' + (z + 1) + '</text>'; }
    }
    var e = c.error || {}, ey = top + mapH + gap, emax = Math.max.apply(null, (e.i_units || [1]).concat([1]));
    function Y(v) { return ey + errH - v / emax * errH; }
    s += '<text x="4" y="' + (ey - 8) + '" font-size="12" class="axis-title" data-axis="y2">' + esc(me.label) + '</text>';
    s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/><text x="' + (l - 4) + '" y="' + (Y(emax) + 4) + '" font-size="10" text-anchor="end">' + sig(emax, 2) + '</text><text x="' + (l - 4) + '" y="' + (Y(0) + 4) + '" font-size="10" text-anchor="end">0</text>';
    if (e.time_s && e.time_s.length) {
      s += lineOf(me, e.time_s.map(function (t, i) { return X(t).toFixed(1) + ',' + Y(e.i_units[i]).toFixed(1); }));
      var ip = 0; e.i_units.forEach(function (v, i) { if (v > e.i_units[ip]) { ip = i; } });
      s += markG(glyph({id: me.id, shape: 'circle', fill: 'solid', colour: me.colour}, X(e.time_s[ip]), Y(e.i_units[ip])), 'Largest zone error ' + sig(e.i_units[ip], 3) + ' I-units at ' + Math.round(e.time_s[ip]) + ' s');
    }
    var yb = ey + errH;
    s += ticks(t0, t1, w < 500 ? 3 : 6).map(function (t) { return '<text x="' + X(t) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round(t) + '</text>'; }).join('');
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Valve levels over time and the largest zone error') + s + xt.s + '</svg>';
  }

  // the zone step test: what the flatness roll zone would read after the zone was closed
  function stepResponse(c) {
    var w = Math.min(860, chartWidth()), l = 40, r = Math.round(Math.min(170, w * 0.3)), hh = 150;
    var fits = c.curves.every(function (cv, k) { return wrapLines(markOf(c, 'c' + k).label, r - 10, 11).length === 1; });
    if (!fits) { c = Object.assign({}, c, {legend: c.curves.map(function (cv, k) { return 'c' + k; })}); r = 12; }
    var lg = chartLegend(c, w, 0), top = lg.h + 26, all = [0], tmax = 0;
    c.curves.forEach(function (cv) { all = all.concat(cv.i_units); tmax = Math.max(tmax, cv.time_s[cv.time_s.length - 1]); });
    var rg = niceRange(Math.min.apply(null, all), Math.max.apply(null, all));
    function X(t) { return l + t / tmax * (w - l - r); }
    function Y(v) { return top + (rg[1] - v) / (rg[1] - rg[0]) * hh; }
    var s = lg.s + yTitle(c, 4, top - 12);
    ticks(rg[0], rg[1], 4).forEach(function (t) { s += '<line class="grid" x1="' + l + '" x2="' + (w - r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/><text x="' + (l - 4) + '" y="' + (Y(t) + 4) + '" font-size="11" text-anchor="end">' + sig(t, 3) + '</text>'; });
    (c.references || []).forEach(function (x) {
      if (!isNum(x.value)) { return; }
      s += markG(refLine(X(x.value), top, X(x.value), top + hh, x.id), x.tip || (x.label + ': ' + sig(x.value, 3) + ' s'));
      s += refText(X(x.value) + 4, top + 12, x.label);
    });
    c.curves.forEach(function (cv, k) {
      var m = markOf(c, 'c' + k), step = Math.max(1, Math.floor(cv.time_s.length / 300));
      s += lineOf(m, cv.time_s.filter(function (t, i) { return i % step === 0; }).map(function (t, j) { var i = j * step; return X(t).toFixed(1) + ',' + Y(cv.i_units[i]).toFixed(1); }));
      var e = cv.time_s.length - 1;
      s += markG(glyph({id: m.id, shape: 'circle', fill: 'solid', colour: m.colour}, X(cv.time_s[e]), Y(cv.i_units[e])), cv.label + ': ' + sig(cv.i_units[e], 3) + ' I-units after ' + Math.round(cv.time_s[e]) + ' s');
      if (fits) { s += labelText({id: m.id, label: cv.label, colour: m.colour}, w - r + 6, Y(cv.i_units[e]) + 4 + (k - 1) * 13, null, 11); }
    });
    var yb = top + hh;
    s += ticks(0, tmax, w < 500 ? 3 : 6).map(function (t) { return '<text x="' + X(t) + '" y="' + (yb + 15) + '" font-size="11" text-anchor="middle">' + Math.round(t) + '</text>'; }).join('');
    var xt = xTitle(c, yb + 32, w);
    return svgOpen(w, yb + 22 + xt.h, 'Zone step test: flatness roll reading over time') + s + xt.s + '</svg>';
  }

  function chartSvg(c) {
    if (!c) { return ''; }
    if (c.type === 'zones') { return shapemeterSvg(c, false, c); }
    if (c.type === 'width_lines') { return widthLines(c); }
    if (c.type === 'bars') { return barsChart(c); }
    if (c.type === 'pass_levels') { return passLevels(c); }
    if (c.type === 'records') { return recordsChart(c); }
    if (c.type === 'cycle') { return cycleChart(c); }
    if (c.type === 'shares') { return sharesChart(c); }
    if (c.type === 'loads') { return loadsChart(c); }
    if (c.type === 'range') { return rangeChart(c); }
    if (c.type === 'valve_map') { return valveMap(c); }
    if (c.type === 'step_response') { return stepResponse(c); }
    return '';
  }

  // ------------------------------------------------------------------ the one add-on card pattern
  function addonCard(card) {
    var h = '<section class="card addon noprint" id="' + card.id + '"><h2>' + esc(card.title) + '</h2>';
    h += '<p class="takeaway-line">' + gloss(card.takeaway) + '</p>';
    if (card.left_out) {
      return h + (S.run ? '<button type="button" class="btn" data-rerun="' + S.run.id + '" data-profile="detailed">Run in detail</button>' : '') + '</section>';
    }
    if (card.chart) { h += '<div class="fig">' + chartSvg(card.chart) + '</div>'; }
    h += '<p class="howto">' + gloss(card.how_to_read) + '</p>';
    if (card.caveat) { h += '<p class="warnline">' + gloss(card.caveat) + '</p>'; }
    // one fold: the details, then the chart as a list (its text alternative)
    h += '<details class="more"><summary>' + (card.details.length ? 'Details, and the chart as a list' : 'The chart as a list') + '</summary>' +
      (card.details.length ? '<ul class="small">' + card.details.map(function (d) { return '<li>' + gloss(d) + '</li>'; }).join('') + '</ul>' : '') +
      (card.details.length ? '<p class="small"><strong>The chart as a list</strong></p>' : '') + '<ul class="small">' + card.text_alternative.map(function (d) { return '<li>' + esc(d) + '</li>'; }).join('') + '</ul></details>';
    return h + '<p class="small soft">From "' + esc(card.group_title) + '" in step 3.</p></section>';
  }
  function addonCards(sum) {
    var cards = sum.addon_cards || [], by = {};
    cards.forEach(function (c) { by[c.id] = c; });
    var h = (sum.addon_sections || []).map(function (sec) {
      var open = S.openSections && S.openSections[sec.group];
      return '<details class="addon-section card noprint" id="sec-' + sec.group + '" data-section="' + sec.group + '"' + (open ? ' open' : '') + '><summary><span class="s-title">' + esc(sec.title) + '</span> <span class="small soft">' +
        sec.cards.length + (sec.cards.length === 1 ? ' card' : ' cards') + '</span><span class="s-line">' + esc(sec.summary) + '</span></summary>' +
        sec.cards.map(function (id) { return addonCard(by[id]); }).join('') + '</details>';
    }).join('');
    if (sum.addon_more && sum.addon_more.text) { h += '<p class="small soft quietline noprint">' + esc(sum.addon_more.text) + '</p>'; }
    return h;
  }

  // the index near the top: one link per heading (nothing when nothing was added)
  function addonIndex(sum) {
    var secs = sum.addon_sections || [];
    if (!secs.length) { return ''; }
    return '<nav class="addon-index noprint" aria-label="From what you added"><span class="small">From what you added:</span> ' + secs.map(function (sec) {
      return '<a href="#sec-' + sec.group + '" data-open-section="' + sec.group + '">' + esc(sec.title) + '</a>';
    }).join('<span class="sep" aria-hidden="true"> · </span>') + '</nav>';
  }

  // ------------------------------------------------------------------ the add-on area of step 3
  function addonStatusHtml(gid) {
    var st = (model().addons || {})[gid] || {filled: false, summary: 'not filled in'};
    return '<span class="g-state ' + (st.filled ? 'filled' : 'empty') + '">' + (st.filled ? '<span aria-hidden="true">●</span> ' : '<span aria-hidden="true">○</span> ') + esc(st.summary) + '</span>';
  }
  function addonClearHtml(gid) {
    var st = (model().addons || {})[gid] || {}, g = M.addon_groups.filter(function (x) { return x.id === gid; })[0];
    return st.filled && g ? '<button type="button" class="btn link g-clear" data-clear-group="' + gid + '" aria-label="Clear ' + esc(g.title) + '">Clear</button>' : '';
  }
  function addonCountHtml() {
    var a = model().addons || {}, n = Object.keys(a).filter(function (k) { return a[k].filled; }).length;
    return n ? n + ' of ' + M.addon_groups.length + ' in use' : 'none in use';
  }
  function addonArea() {
    resetGloss();
    var open = S.openMore && S.openMore.addons;
    var h = '<details class="addons" data-more="addons"' + (open ? ' open' : '') + '><summary><span class="a-title">Add what else you have (optional)</span> <span class="small soft" data-view="addoncount">' + addonCountHtml() + '</span></summary>' +
      '<p class="howto">A flatness roll, a gauge, a scan, pass records, oil data, or a model choice: each adds what it would show to the result. None of them changes the shortlist unless a model choice says so.</p><ul class="groups">';
    M.addon_groups.forEach(function (g) {
      var qs = g.questions.map(function (id) { return Q[id]; }).filter(function (q) { return q && shown(q) && visible(q); });
      var gopen = S.openGroups && S.openGroups[g.id];
      h += '<li class="addon-group"><details data-group="' + g.id + '"' + (gopen ? ' open' : '') + '><summary><span class="g-title">' + esc(g.title) + '</span><span data-view="addon:' + g.id + '">' + addonStatusHtml(g.id) + '</span></summary>' +
        '<p class="help">' + gloss(g.help) + '</p>' + qs.map(function (q) { return renderQ(q); }).join('') +
        '</details><span data-view="addonclear:' + g.id + '">' + addonClearHtml(g.id) + '</span></li>';
    });
    return h + '</ul></details>';
  }
  function clearGroup(gid) {
    var g = M.addon_groups.filter(function (x) { return x.id === gid; })[0];
    if (!g) { return; }
    g.questions.forEach(function (id) {
      var q = Q[id]; if (!q) { return; }
      if (q.origin_tracked) { S.answers.values[id] = clone(pv(id)); S.answers.origins[id] = 'preset'; }
      else { S.answers.values[id] = null; }
      S.touched[id] = true;
    });
    touch(); render(); checkNow();
    announce(g.title + ': cleared');
  }
  // ------------------------------------------------------------------ render and navigation
  function render() {
    var active = document.activeElement && document.activeElement.id;
    var y = window.scrollY;
    if (S.view === 'input') { renderInput(); S.drawnKey = drawnState(); }
    renderDrawer();
    if (active) { var a = document.getElementById(active); if (a) { a.focus({preventScroll: true}); } }
    restoreFocus();
    markBusy();
    window.scrollTo(0, y);
  }
  function goStep(step, qid) {
    S.view = 'input'; S.step = step;
    stopPoll();
    renderInput(); renderDrawer(); S.drawnKey = drawnState();
    if (qid) {
      var node = document.getElementById('f-q-' + qid);
      if (node) {
        var det = node.closest('details'); if (det) { det.open = true; }
        node.scrollIntoView({block: 'center'}); node.classList.add('flash');
        var inp = node.querySelector('input,select,button'); if (inp) { inp.focus({preventScroll: true}); }
      }
    } else { window.scrollTo(0, 0); }
  }

  // leaving the current view: replies that would change the view or the result are dropped
  function stopPoll() { S.nav += 1; if (S.poll) { clearTimeout(S.poll); S.poll = null; } }
  function openRun(id, opts) {
    stopPoll();
    S.drawer = false; renderDrawer();
    S.openChecks = {}; S.pending = {}; S.compare = opts && opts.keepCompare ? S.compare : null; S.whatif = null; S.openCause = null;
    S.view = 'run';
    poll(id, true);
  }
  function poll(id, first) {
    var nav = S.nav;
    api('GET', '/api/runs/' + id).then(function (r) {
      if (nav !== S.nav) { return; }                      // another run or view opened since
      if (r.status !== 200) { app.innerHTML = '<div class="wrap"><div class="card errorbox" role="alert"><p>' + esc((r.data.error || {}).text || 'This run cannot be opened.') + '</p><button type="button" class="btn" data-back-input="1">Back to the answers</button></div></div>'; return; }
      var st = r.data, run = st.run;
      S.run = run;
      if (run.status === 'queued' || run.status === 'running') {
        if (first || !document.getElementById('elapsed')) { renderRunning(st); }
        else { document.getElementById('elapsed').textContent = (isNum(run.elapsed_s) ? Math.round(run.elapsed_s) : 0) + ' s'; }
        S.poll = setTimeout(function () { poll(id, false); }, 700);
        return;
      }
      if (run.status === 'done' && run.summary_error) { renderSummaryError(st); return; }
      if (run.status !== 'done') {
        api('GET', '/api/runs/' + id + '/answers.json').then(function (a) { if (nav !== S.nav) { return; } S.runAnswers = a.status === 200 ? a.data.answers : null; renderFailed(st); });
        return;
      }
      Promise.all([api('GET', '/api/runs/' + id + '/answers.json'),
        run.base_run_id ? api('GET', '/api/runs/' + run.base_run_id) : Promise.resolve(null)]).then(function (res) {
        if (nav !== S.nav) { return; }
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
    // first let pending edits and checks settle, so the run starts from what is drawn
    settle().then(startRunNow);
  }
  function startRunNow() {
    if (S.generalError || Object.keys(S.errors).length) {
      var first = Object.keys(S.errors)[0];
      if (first && Q[first]) { goStep(Q[first].step, first); }
      return;
    }
    var b = body(), rev = S.rev, nav = S.nav; b.profile = S.profile;
    var btn = document.getElementById('runbtn'); if (btn) { btn.disabled = true; }
    api('POST', '/api/runs', b).then(function (r) {
      // the run is what was pressed; it is opened unless the person went elsewhere meanwhile
      if (r.status === 202) { if (nav === S.nav) { openRun(r.data.id); } return; }
      if (btn) { btn.disabled = false; }
      if (!accept(rev)) { runCheck(); return; }          // refused for inputs no longer held
      var e = r.data.error || {text: 'The run could not be started.'};
      var patched = applyReconciled(r.data);
      if (patched) { touch(); }
      if (patched || (r.data.reconciled || []).length) {
        // a run is never started from answers the person has not seen: show the redrawn header
        S.check = null; runCheck();
        goStep(Q[e.question] ? Q[e.question].step : S.step, e.question);
        return;
      }
      if (e.question) { S.errors[e.question] = e.text; goStep(Q[e.question] ? Q[e.question].step : S.step, e.question); markErrors(); }
      else { S.generalError = e.text; updateSide(); }
    });
  }

  function setPreset(id, info) {
    var keepSteps = ['see', 'rolling'];
    touch(); S.ctx += 1;
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
    S.model = null; S.modelKey = null; S.modelStale = false; S.notices = {};
    S.banner = p.kind === 'example' ? 'Loaded "' + p.label + '". Its observations were generated by the model, not seen on a plant.' :
      p.kind === 'file' ? 'Opened the case file. Its values are shown as your answers.' : null;
    scheduleCheck();
  }

  function cycleNozzle(i) {
    // the server applies the rule; the drawing shows the state it then reports
    sendEdit({op: 'cycle', index: i}, '[data-noz="' + i + '"]', function () {
      var h = model().header, n = h && h.nozzles[i];
      if (n) { announce('Nozzle ' + n.number + ': ' + n.state); }
    });
  }
  var live = null;
  function announce(t) {
    if (!live) { live = document.createElement('div'); live.className = 'sr'; live.setAttribute('aria-live', 'polite'); document.body.appendChild(live); }
    live.textContent = t;
  }

  function setBands(list, focusIndex) {
    var wmm = Math.round(model().strip.width_m * 1000);
    list = list.map(function (x) { return Math.max(0, Math.min(wmm, Math.round(x))); });
    setVal('band_positions', list.length ? list : null);
    // drawn when the server's model of the new case arrives (redrawn on any difference)
    S.focusSel = focusIndex !== undefined ? '[data-band="' + focusIndex + '"]' : null;
    checkNow();
  }
  // edits compose on the stored answer (what was typed); what is drawn is the model
  function bandsList() { var v = val('band_positions'); return Array.isArray(v) ? v.slice() : []; }
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
    var t = e.target.closest('[data-step],[data-run],[data-cause],[data-answer],[data-check],[data-update],[data-discard],[data-open-run],[data-rerun],[data-cancel],[data-back-input],[data-goto],[data-report],[data-download],[data-print],[data-drawer],[data-trywhatif],[data-wstep],[data-list-add],[data-list-del],[data-route-use],[data-band-add],[data-band-del],[data-band-clear],[data-noz],[data-noz-reset],[data-noz-init],[data-defaults],[data-new],[data-mark],[data-clear-group],[data-open-section]');
    if (!t) { var m = e.target.closest('.mark'); if (m) { showTip(m); } return; }
    var d = t.dataset;
    if (d.step) { goStep(d.step); }
    else if (d.run) { startRun(); }
    else if (d.cause) { S.openCause = S.openCause === d.cause ? null : d.cause; rerenderResult(); var dd = document.getElementById('detail-' + d.cause); if (dd) { dd.scrollIntoView({block: 'nearest'}); } }
    else if (d.answer) { var k = 'nl-' + S.openCause + '-' + d.answer; S.openChecks[k] = !S.openChecks[k]; rerenderResult(); }
    else if (d.check) { S.openChecks[d.check] = !S.openChecks[d.check]; rerenderResult(); }
    else if (d.update) {
      var navU = S.nav;
      api('POST', '/api/runs/' + S.run.id + '/variant', {changes: S.pending, profile: S.run.profile, label: String(S.run.name || '').replace(/ \((updated|what-if)\)$/, '') + ' (updated)'}).then(function (r) {
        if (navU !== S.nav) { return; }
        if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text || 'The update could not be started.'); }
      });
    }
    else if (d.discard) { S.pending = {}; S.openChecks = {}; rerenderResult(); }
    else if (d.openRun) { openRun(d.openRun); }
    else if (d.rerun) { var navR = S.nav; api('POST', '/api/runs/' + d.rerun + '/rerun', {profile: d.profile || 'detailed'}).then(function (r) { if (navR !== S.nav) { return; } if (r.status === 202) { openRun(r.data.id); } else { alertBox((r.data.error || {}).text); } }); }
    else if (d.cancel) { var navC = S.nav; api('POST', '/api/runs/' + d.cancel + '/cancel', {}).then(function () { if (navC === S.nav) { stopPoll(); poll(d.cancel, true); } }); }
    else if (d.backInput) { if (S.run && S.view !== 'input') { reopenRun(S.run.id, null); } else { goStep(S.step); } }
    else if (d.goto) { if (S.view !== 'input' && S.run) { reopenRun(S.run.id, d.goto); } else { goStep(Q[d.goto].step, d.goto); } }
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
        render(); checkNow();
      }
    }
    else if (d.bandAdd) { var nb = document.getElementById('bp-new'), nv = Number(nb.value); if (nb.value !== '' && isFinite(nv)) { nb.value = ''; setBands(bandsList().concat([nv]), bandsList().length); } }
    else if (d.bandDel !== undefined) { var bl = bandsList().slice(); bl.splice(Number(d.bandDel), 1); setBands(bl); }
    else if (d.bandClear) { setBands([]); }
    else if (d.noz !== undefined && !t.closest('svg').dataset.dragging) { cycleNozzle(Number(d.noz)); }
    else if (d.nozReset) { sendEdit({op: 'clear'}); }
    else if (d.nozInit) { sendEdit({op: 'all_healthy'}); }
    else if (d.defaults) { productDefaults(); }
    else if (d.clearGroup) { clearGroup(d.clearGroup); }
    else if (d.openSection) {
      e.preventDefault();
      var sec = document.getElementById('sec-' + d.openSection);
      if (sec) { sec.open = true; sec.scrollIntoView({block: 'start'}); sec.querySelector('summary').focus({preventScroll: true}); }
    }
    else if (d.new) { newScreening(); }
  });

  function alertBox(t) { announce(t || ''); window.alert(t || 'Something went wrong.'); }

  function reopenRun(runId, gotoQ) {
    // "Change the answers": the server gives the run's own starting point (a named one, or the
    // run's stored case) and answers that rebuild exactly that run's case
    var nav = S.nav, rev = S.rev;
    api('GET', '/api/runs/' + runId + '/reopen').then(function (r) {
      if (nav !== S.nav || rev !== S.rev) { return; }      // the person moved on meanwhile
      if (r.status !== 200) { alertBox((r.data.error || {}).text || 'This run cannot be reopened.'); return; }
      touch(); S.ctx += 1;
      var ro = r.data, a = ro.answers || {};
      S.presetsExtra = S.presetsExtra.filter(function (p) { return p.kind !== 'run'; });
      if (ro.preset_info) {
        var info = ro.preset_info; info.id = 'run_' + runId; info.ref = ro.preset;
        S.presetsExtra.push(info); S.presetId = info.id;
      } else { S.presetId = ro.preset; }
      S.answers = clone({values: a.values || {}, origins: a.origins || {}, own_mill: !!a.own_mill, name: a.name || ''});
      S.touched = {}; Object.keys(S.answers.values).forEach(function (k) { S.touched[k] = true; });
      S.suggested = {}; S.check = null; S.errors = {}; S.generalError = null;
      S.model = null; S.modelKey = null; S.modelStale = false; S.notices = {};
      if (ro.profile) { S.profile = ro.profile; }
      S.banner = 'These are the answers of the run "' + (a.name || '') + '". Change what you need and run again.';
      scheduleCheck();
      if (gotoQ) { goStep(Q[gotoQ].step, gotoQ); } else { goStep('see'); }
    });
  }

  function renderSummaryError(st) {
    var run = st.run;
    app.innerHTML = '<div class="wrap"><section class="card banner" role="status"><h2>The screening ran, but the visual summary could not be built</h2>' +
      '<p>' + esc(run.summary_error) + '</p><p class="screening-note">A screening result from a model that has not been compared with plant data, not a finding.</p>' +
      '<div class="takeaway">' + (run.report_available !== false ? '<button type="button" class="btn primary" data-report="' + run.id + '">Open the full engineering report</button>' : '') +
      '<button type="button" class="btn" data-download="result.json">Download the result</button><button type="button" class="btn" data-download="case.json">Download the case file</button>' +
      '<button type="button" class="btn" data-back-input="1">Change the answers</button></div></section></div>';
  }

  document.addEventListener('change', function (e) {
    var t = e.target, d = t.dataset;
    if (d.chip) { var v = JSON.parse(d.v); if (d.chip === 'orientation' && ctxOf(t) === 'f') { S.touched.orientation = true; } store(d.chip, v, t); if (ctxOf(t) === 'f') { render(); } }
    else if (d.select) {
      if (d.select === 'product' && Object.keys(S.suggested).length) {
        S.productInfo = 'You chose another product. The typical values filled in before were for the previous product: fill them in again for this one, or keep and check them.';
      }
      store(d.select, JSON.parse(t.value), t); if (ctxOf(t) === 'f') { render(); }
    }
    else if (d.origin) { S.answers.origins[d.origin] = t.value; if (t.value === 'preset') { S.answers.values[d.origin] = clone(pv(d.origin)); } S.touched[d.origin] = true; touch(); scheduleCheck(); render(); }
    else if (d.preset) { setPreset(d.preset); render(); }
    else if (d.profile) { S.profile = d.profile; }
    else if (t.id === 'ownmill') { S.answers.own_mill = t.checked; touch(); scheduleCheck(); }
    else if (t.id === 'casename') { S.answers.name = t.value; touch(); scheduleCheck(); }
    else if (t.id === 'casefile') { openCaseFile(t.files[0]); }
    else if (d.num && ctxOf(t) === 'f') { S.typingField = null; if (S.heldReset) { checkNow(); } }   // drawings follow the model
    else if (d.bandpos !== undefined) { checkNow(); }
    else if (d.nozlevel !== undefined) {
      var x = Number(t.value);
      if (t.value !== '' && isFinite(x)) { sendEdit({op: 'set_level', index: Number(d.nozlevel), level: x}, '#nz-' + d.nozlevel); }
      else { refreshViews(true); }
    }
    else if (d.nozedit === 'blocked') {
      var pn = parseNums(t.value);
      if (pn === undefined) { S.errors.blocked_nozzles = 'Type whole nozzle numbers separated by commas, for example 4, 12.'; markErrors(); updateSide(); }
      else { sendEdit({op: 'set_blocked', numbers: pn || []}, '#f-in-blocked_nozzles'); }
    }
    else if (d.wi) { S.whatif = S.whatif || {}; S.whatif[d.wi] = t.tagName === 'SELECT' ? t.value : Number(t.value); }
    else if (t.closest('[data-more]')) { /* details toggle handled below */ }
  });
  document.addEventListener('toggle', function (e) {
    var t = e.target;
    if (t.dataset && t.dataset.more) { S.openMore = S.openMore || {}; S.openMore[t.dataset.more] = t.open; }
    if (t.dataset && t.dataset.other) { S.otherOpen = t.open; }
    if (t.dataset && t.dataset.trust) { S.trustOpen = t.open; }
    if (t.dataset && t.dataset.nozlist) { S.nozListOpen = t.open; }
    if (t.dataset && t.dataset.group) { S.openGroups = S.openGroups || {}; S.openGroups[t.dataset.group] = t.open; }
    if (t.dataset && t.dataset.section) { S.openSections = S.openSections || {}; S.openSections[t.dataset.section] = t.open; }
  }, true);
  document.addEventListener('input', function (e) {
    var t = e.target, d = t.dataset;
    if (t.id === 'prod-filter') { S.prodFilter = t.value; var pos = t.selectionStart; render(); var f = document.getElementById('prod-filter'); f.focus(); f.setSelectionRange(pos, pos); return; }
    if (d.num) { if (ctxOf(t) === 'f') { S.typingField = d.num; } storeQuiet(d.num, t.value === '' ? null : Number(t.value), t); }
    else if (d.text) { storeQuiet(d.text, t.value.trim() === '' ? null : t.value, t); }
    else if (d.nums) { var p = parseNums(t.value); if (p !== undefined) { storeQuiet(d.nums, p, t); } }
    else if (d.list) {
      var q = Q[d.list], cur = clone((ctxOf(t) === 'p' ? PEND : FORM).get(q.id) || []), row = cur[Number(d.row)];
      var fk = d.fkind, v = t.tagName === 'SELECT' ? t.value : fk === 'numbers' ? (parseNums(t.value) || []) : fk === 'text' ? t.value : (t.value === '' ? null : Number(t.value));
      row[d.field] = v; storeQuiet(q.id, cur, t);
    }
    else if (d.bandpos !== undefined) { var bl = bandsList(); if (t.value !== '') { bl[Number(d.bandpos)] = Number(t.value); setVal('band_positions', bl); } }
  });
  function storeQuiet(id, v, node) {
    if (ctxOf(node) === 'p') { S.pending[id] = v; var pb = app.querySelectorAll('.pending'); if (!pb.length) { rerenderResult(); } else { var html = pendingBar(); for (var i = 0; i < pb.length; i++) { pb[i].outerHTML = html; } } return; }
    setVal(id, v);
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
      var nv = Number(t.value); if (t.value !== '' && isFinite(nv)) { t.value = ''; setBands(bandsList().concat([nv])); S.focusSel = '#bp-new'; }
      e.preventDefault();
    } else if (e.key === 'Escape') { hideTip(); if (S.drawer) { S.drawer = false; renderDrawer(); } }
  });
  document.addEventListener('focusin', function (e) { if (e.target.getAttribute && e.target.getAttribute('data-tip')) { showTip(e.target); } });
  document.addEventListener('focusout', hideTip);
  // a tooltip never stays behind at an old place: it follows its focused mark, or goes
  window.addEventListener('scroll', function () {
    var a = document.activeElement;
    if (a && a.getAttribute && a.getAttribute('data-tip')) { showTip(a); } else { hideTip(); }
  }, {passive: true});
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
      var req = ++S.openReq, rev = S.rev;
      api('POST', '/api/case/open', {case_file: c}).then(function (r) {
        if (req !== S.openReq) { return; }                // a later file was chosen
        if (rev !== S.rev) { S.banner = 'The case file was not opened: the answers changed while it was being checked. Open it again if you still want it.'; if (S.view === 'input') { render(); } return; }
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
    var req = ++S.defaultsReq, rev = S.rev;
    api('POST', '/api/product-defaults', b).then(function (r) {
      if (req !== S.defaultsReq) { return; }             // a later lookup was asked for
      if (rev !== S.rev) { S.productInfo = 'The answers changed while the typical values were looked up, so they were not filled in. Press the button again.'; if (S.view === 'input') { render(); } return; }
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
      touch();
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
    var before = S.summary, baseRun = S.run, nav = S.nav;
    api('POST', '/api/runs/' + S.run.id + '/variant', {changes: ch, profile: S.run.profile, label: (S.run.name || '') + ' (what-if)'}).then(function (r) {
      if (nav !== S.nav) { return; }                     // another run or view opened since
      if (r.status !== 202) { S.whatifError = (r.data.error || {}).text; rerenderResult(); return; }
      var id = r.data.id;
      var sec = app.querySelector('[data-trywhatif]'); if (sec) { sec.disabled = true; sec.textContent = 'Running the what-if…'; }
      (function wait() {
        api('GET', '/api/runs/' + id).then(function (s) {
          if (nav !== S.nav) { return; }                 // the what-if stays in "Previous runs"
          var st = s.data.run.status;
          if (st === 'queued' || st === 'running') { setTimeout(wait, 700); if (sec) { sec.textContent = 'Running the what-if… ' + Math.round(s.data.run.elapsed_s || 0) + ' s'; } return; }
          if (st !== 'done') { S.whatifError = (s.data.run.error || {}).text || 'The what-if did not finish.'; rerenderResult(); return; }
          var after = s.data.summary;
          S.compare = {before: before, after: after, afterId: id, changes: words, diff: after.compared_with_base ? after.compared_with_base.text : ''};
          rerenderResult(); var c = app.querySelector('.compare'); if (c) { c.scrollIntoView({block: 'start'}); }
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
