# -*- coding: utf-8 -*-
# Ad funnel landing pages for weight loss, hair loss (men/women), TRT and HRT.
#
# STATUS: CURRENT as of 2026-09-19. This generator IS the source of truth for
# everything under ~/directcare-home/lp/. If you edit the generated HTML
# directly, reconcile the edit back into this file before running it again —
# that is exactly how scripts/lp/build.py (the ED/surge generator) went stale.
#
# This file does NOT touch surge/f1..f5. build.py owns those and is stale;
# the shell below was lifted from the CURRENT on-disk surge/f1/index.html,
# not from core.py, whose head() has drifted (no GTM, no Ahrefs, old favicons).
#
# Every page here is noindex,nofollow, canonicalises to its organic parent, and
# is deliberately ABSENT from sitemap.xml. It is deliberately NOT disallowed in
# robots.txt: a blocked page can never be crawled, so its noindex is never seen,
# and Google Ads/AdsBot must be able to fetch a landing page or the ad is
# disapproved. Crawlable + noindex is the correct combination.
#
# NO THIRD-PARTY AD PIXELS ON THESE PAGES — 2026-09-20. Deliberate, do not "fix".
#
# These pages carry GTM (GTM-N7ZG3PT8) and nothing else. dc-signal.js, dc-webmcp.js
# and the Ahrefs tag were REMOVED, and the dataLayer push no longer carries
# product/category. The reason is specific and survives a casual reading of the code:
#
#   The path IS the condition. /lp/trt/f1, /lp/hair-loss-women/f1. dc-signal.js sends
#   origin+pathname to Meta as event_source_url and reports the page to TikTok via
#   ttq.page() — its own header says to treat that as disclosed to both vendors. On
#   the ORGANIC pages that is a considered trade. Here it was paired with
#   dcaIdentify(em, ph, fn) on lead capture, so Meta received a named person joined
#   to a health condition. That is the GoodRx/BetterHelp/Cerebral fact pattern and it
#   is what a dca-risk-compliance review BLOCKED these pages on.
#
#   Note the earlier review located the leak in the dataLayer `category` key. That was
#   wrong: GTM-N7ZG3PT8 contains no Meta, Pinterest or TikTok tags at all (verified
#   2026-09-20 against the published container — only GA4 G-8D0RZ5YEDL, the Google
#   tag and Google Ads enhanced conversions). `category` never reached an ad platform.
#   dc-signal.js did, independently of GTM. Removing the script is the fix; removing
#   `category` alone would have looked like a fix and changed nothing.
#
# Restoring either script re-opens the disclosure. If Meta measurement is ever needed
# here, the answer is condition-neutral URLs, not putting dc-signal.js back.

# Hard rule: NO prescription drug names and NO mg doses on these pages. Drug
# names stay on the organic pages. Routes of administration (patch, cream,
# injection, oral) are delivery formats, not drug names, and are allowed.
#
#   python3 scripts/lp/funnels.py          # writes lp/<slug>/f1..f5/index.html

import pathlib

# Derived from this file's location, not $HOME: running the generator from a git
# worktree must not write into a different checkout of the repo.
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "lp"
IMG = "/optimized/%s-1200.webp"
LOGO_D = "/logo-color.png"

SHELL_CSS = r"""
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:Archivo,-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  color:#1c1024;background:#fff;line-height:1.5;-webkit-font-smoothing:antialiased;
  font-synthesis-weight:none;letter-spacing:-.005em}
img{max-width:100%;display:block}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
.bar{background:#241432;color:#cdb9d8;font-size:11px;letter-spacing:.06em;text-align:center;
  padding:9px 16px;font-weight:600;text-transform:uppercase}
.bar.gold{color:#f3c969}
header.nav{padding:16px 0}
header.nav img{width:132px;height:auto}
h1{font-size:clamp(34px,5.4vw,52px);line-height:1.03;letter-spacing:-.03em;margin:0 0 18px;font-weight:900}
h2{font-size:clamp(24px,4.4vw,40px);line-height:1.08;letter-spacing:-.028em;margin:0 0 14px;font-weight:800}
h3{font-size:18px;line-height:1.25;margin:0 0 6px;font-weight:700;letter-spacing:-.015em}
p{margin:0 0 14px}
.lede{font-size:clamp(16px,2.2vw,19px);color:#4b3d59;line-height:1.55}
.muted{color:#7a6d88}
.tiny{font-size:12px;line-height:1.5;color:#7a6d88}
section{padding:40px 0}
@media(min-width:860px){section{padding:64px 0}}
.lilac{background:#f2ecf6}
.plum{background:#241432;color:#f4eefb}
.plum h2,.plum h3{color:#fff}
.plum .lede,.plum p{color:#cdb9d8}
.ink{background:#0d0812;color:#fff}
.cta{display:block;width:100%;max-width:440px;margin:0 auto;text-align:center;text-decoration:none;
  background:linear-gradient(95deg,#0b6f37 0%,#16a84f 50%,#2bb866 100%);color:#fff;font-size:18px;font-weight:800;
  padding:18px 20px;border-radius:999px;border:0;cursor:pointer;box-shadow:0 8px 24px rgba(24,201,101,.32)}
.cta{transition:transform .13s ease,box-shadow .13s ease}
.cta:hover{transform:translateY(-1px);box-shadow:0 12px 30px rgba(24,201,101,.42)}
.cta:active{transform:translateY(1px);box-shadow:0 4px 14px rgba(24,201,101,.3)}
.cta:focus-visible{outline:3px solid #241432;outline-offset:3px}
.cta.light{background:#fff;color:#44215A;box-shadow:0 6px 20px rgba(0,0,0,.28)}
.grid{display:grid;gap:14px}
@media(min-width:860px){.grid.g3{grid-template-columns:repeat(3,1fr)}.grid.g2{grid-template-columns:1fr 1fr}
  .split{display:grid;grid-template-columns:1.05fr .95fr;gap:48px;align-items:center}}
.card{background:#fff;border:1px solid #e5dbec;border-radius:18px;padding:22px;
  box-shadow:0 1px 2px rgba(36,20,50,.04),0 12px 28px -22px rgba(36,20,50,.5)}
.plum .card,.ink .card{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.14)}
.pill{display:inline-block;background:#6d28d9;color:#fff;font-size:11px;font-weight:800;letter-spacing:.12em;
  padding:7px 14px;border-radius:999px;text-transform:uppercase}
.price{font-size:34px;font-weight:900;letter-spacing:-.02em}
.hero-img{border-radius:18px;overflow:hidden;background:#f2ecf6}
.hero-img img{width:100%;height:auto;object-fit:cover}
.band{width:100%;height:230px;object-fit:cover;object-position:center 22%}
@media(min-width:860px){.band{height:380px}}
.scrim{position:relative;overflow:hidden}
.scrim img{width:100%;height:100%;object-fit:cover;display:block}
.scrim:after{content:"";position:absolute;inset:0;
  background:linear-gradient(to bottom,rgba(36,20,50,0) 38%,rgba(36,20,50,.72) 100%)}
.scrim .over{position:absolute;left:0;right:0;bottom:0;padding:22px 20px;z-index:2;color:#fff}
.scrim .over h1{color:#fff;text-shadow:0 2px 18px rgba(0,0,0,.45);margin:0}
.trust{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.trust div{background:#faf7fb;border:1px solid #e5dbec;border-radius:12px;padding:13px 8px;text-align:center;
  font-size:12.5px;font-weight:800;line-height:1.3}
.plum .trust div{background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.14);color:#fff}
/* quiz */
.quiz{background:#241432;border-radius:20px;padding:24px 20px 26px;color:#fff;
  box-shadow:0 24px 60px -30px rgba(36,20,50,.85)}
@media(min-width:860px){.quiz{padding:32px 30px 34px}}
.dots{display:flex;gap:6px;margin-bottom:14px}
.dots i{flex:1;height:4px;border-radius:2px;background:rgba(255,255,255,.22)}
.dots i.on{background:#f3c969}
.q{font-size:clamp(21px,3.4vw,30px);font-weight:800;line-height:1.15;margin:0 0 16px;letter-spacing:-.01em}
.opts{display:grid;gap:10px}
.opt{display:block;width:100%;text-align:left;background:#fff;color:#241432;border:0;border-radius:14px;
  padding:17px 18px;font-size:17px;font-weight:700;cursor:pointer;font-family:inherit;letter-spacing:-.01em;
  box-shadow:0 1px 0 rgba(0,0,0,.04),0 6px 16px -10px rgba(0,0,0,.5);
  transition:transform .13s ease,box-shadow .13s ease,background .13s ease}
.opt:hover{background:#faf7fb;transform:translateY(-1px);box-shadow:0 2px 0 rgba(0,0,0,.05),0 12px 22px -12px rgba(0,0,0,.55)}
.opt:active{transform:translateY(1px);box-shadow:none}
.opt:focus-visible{outline:3px solid #f3c969;outline-offset:2px}
.step{animation:rise .22s ease both}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.step{animation:none}.opt{transition:none}}
.skip{display:block;text-align:center;margin-top:14px;color:#d185ff;font-size:14px;font-weight:600;
  text-decoration:none;background:0;border:0;cursor:pointer;width:100%;font-family:inherit}
.field{width:100%;padding:15px 16px;border-radius:13px;border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.08);color:#fff;font-size:16px;font-family:inherit;margin-bottom:10px}
.field::placeholder{color:#9c87a8}
.err{color:#ffb3c6;font-size:13px;margin:2px 0 10px;display:none}
/* plan rows */
.plan{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 16px;border-radius:14px;
  background:#faf7fb;border:1px solid #e5dbec;text-decoration:none;color:inherit}
.plum .plan{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.14);color:#fff}
.plan b{display:block;font-size:16px}
.plan span{font-size:13px;color:#7a6d88}
.plum .plan span{color:#cdb9d8}
.plan em{font-style:normal;font-size:19px;font-weight:900;color:#6d28d9;white-space:nowrap}
.packshot{width:100%;max-width:460px;height:auto;border-radius:18px;margin:4px 0 18px}
@media(min-width:860px){.packshot{margin:8px auto 26px;display:block}}
.plan-grid{display:grid;gap:10px}
.plan{transition:transform .13s ease,box-shadow .13s ease}
.plan:hover{transform:translateY(-2px);box-shadow:0 14px 30px -18px rgba(36,20,50,.55)}
@media(min-width:860px){
  .plan-grid{grid-template-columns:repeat(3,1fr);gap:16px}
  .plan{flex-direction:column;align-items:flex-start;gap:10px;padding:24px 22px;min-height:152px}
  .plan em{font-size:30px}
  section{padding:72px 0}
}
.plum .plan em{color:#f3c969}
/* sticky */
.sticky{position:fixed;left:0;right:0;bottom:0;padding:10px 16px calc(10px + env(safe-area-inset-bottom));
  background:rgba(255,255,255,.94);backdrop-filter:blur(8px);border-top:1px solid #e5dbec;z-index:50;
  transform:translateY(120%);transition:transform .25s ease}
.sticky.show{transform:translateY(0)}
.sticky .cta{font-size:16px;padding:15px 18px}
body{padding-bottom:0}
/* height is set from Tellescope's postMessage; this is only the pre-JS fallback */
#intake{border:0;width:100%;height:1240px;background:#fff;border-radius:18px;display:block;
  box-shadow:0 1px 2px rgba(36,20,50,.05),0 24px 60px -34px rgba(36,20,50,.6);
  transition:height .18s ease}
#intake[data-autosized]{transition:height .18s ease}
/* the form renders as a ~640px column, so a full-width box on desktop is mostly dead space */
.intake-shell{max-width:760px;margin:0 auto}
.intake-grid{display:block}
.rail-extra{display:none}
.rail-list{list-style:none;margin:18px 0 0;padding:0;display:grid;gap:12px}
.rail-list li{position:relative;padding-left:24px;font-size:15px;color:#4b3d59;line-height:1.45}
.rail-list li:before{content:"";position:absolute;left:0;top:7px;width:9px;height:9px;border-radius:50%;
  background:#16a84f;box-shadow:0 0 0 4px rgba(22,168,79,.14)}
.rail-list b{color:#1c1024}
.plum .rail-list li{color:#cdb9d8}
.plum .rail-list b{color:#fff}
.rail-price{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-top:22px;
  padding-top:18px;border-top:1px solid #e5dbec;font-size:15px;color:#4b3d59}
.rail-price b{font-size:30px;font-weight:900;color:#241432;letter-spacing:-.02em}
.plum .rail-price{border-color:rgba(255,255,255,.16);color:#cdb9d8}
.plum .rail-price b{color:#f3c969}
@media(min-width:1000px){
  .intake-grid{display:grid;grid-template-columns:330px minmax(0,1fr);gap:56px;align-items:start}
  .intake-rail{position:sticky;top:28px}
  .rail-extra{display:block}
  .intake-shell{margin:0}
  #intakeWrap h2{margin-bottom:10px}
}
@media(min-width:860px){#intake{height:1040px}}
.hide{display:none!important}
.hero{position:relative;overflow:hidden;background:#241432}
.hero .heroimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 18%}
.hero:before{content:"";position:absolute;inset:0;z-index:1;
  background:linear-gradient(to bottom,rgba(36,20,50,.35) 0%,rgba(36,20,50,.62) 46%,rgba(36,20,50,.96) 100%)}
.hero .inner{position:relative;z-index:2;padding-top:150px}
.hero h1,.hero .lede{color:#fff}
.hero .lede{color:#e2d6ec}
.hero .card{background:rgba(255,255,255,.97)}
@media(min-width:860px){
  /* desktop keeps the text|quiz split and lets the photography run as its own
     full-bleed band below, so the hero image is not needed twice */
  .hero{background:#f2ecf6}
  .hero:before{display:none}
  .hero .heroimg{display:none}
  .hero .inner{padding-top:0}
  .hero h1{color:#241432}
  .hero .lede{color:#4b3d59}
  .hero .card{background:#fff}
  .hero .grid2{display:grid;grid-template-columns:1.05fr .95fr;gap:48px;align-items:center}
  .hero .grid2 > div:last-child{margin-top:0!important}
}
footer{padding:26px 0 40px;border-top:1px solid #e5dbec;margin-top:10px}
footer .tiny{max-width:78ch}
@media(min-width:860px){
  .quiz{max-width:620px}
  #capture.quiz{margin:0 auto}
}
"""

SHELL_JS = r"""
(function(){
  var V = document.body.dataset.variant;
  var dl = function(ev, extra){ window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({event:ev, variant:V}, extra||{})); };
  dl('lp_view');

  // sticky CTA appears once the hero is behind you
  var bar = document.getElementById('stickyBar'), hero = document.querySelector('[data-hero]');
  if (bar && hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(function(es){ bar.classList.toggle('show', !es[0].isIntersecting); },
      {rootMargin:'-80px 0px 0px 0px'}).observe(hero);
  }
  document.addEventListener('click', function(e){
    var a = e.target.closest('[data-cta]'); if (a) dl('cta_click', {placement:a.dataset.cta});
  });

  // ---- lead capture: this is what puts an abandoner into the follow-up sequence ----
  // funnel slug must stay one of the keys in api/quiz-submit.js FUNNEL_NAME,
  // or the contact lands in GHL without the "funnel - <name>" tag every
  // downstream segment and workflow is built on.
  (function(){
    var form = document.getElementById('leadForm');
    if (form) form.addEventListener('submit', function(e){
      e.preventDefault();
      var fd = new FormData(form), email = (fd.get('email')||'').trim();
      var errEl = form.querySelector('.err');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
        errEl.textContent = 'Enter an email we can send your results to.'; errEl.style.display='block'; return;
      }
      errEl.style.display='none';
      var body = { funnel:'__FUNNEL__', partial:true, source:'lp-'+V,
        contact:{ firstName:(fd.get('first_name')||'').trim(), email:email,
                  phone:(fd.get('phone')||'').trim() },
        answers: [] };
      fetch('/api/quiz-submit', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
        .catch(function(){});
      dl('lead_captured');
      document.getElementById('capture').classList.add('hide');
      window.startIntake();
    });
  })();

  // ---- the intake is embedded; CTAs just take you to it ----
  var startedFired = false;
  window.startIntake = function(){
    var host = document.getElementById('intakeWrap'); if (!host) return;
    host.scrollIntoView({behavior:'smooth', block:'start'});
    if (!startedFired) { startedFired = true; dl('intake_start'); }
  };
  // count it as started once the form actually comes into view, however they got there
  if ('IntersectionObserver' in window) {
    var iw = document.getElementById('intakeWrap');
    if (iw) new IntersectionObserver(function(es, o){
      if (es[0].isIntersecting && !startedFired) { startedFired = true; dl('intake_start'); o.disconnect(); }
    }, {threshold:.35}).observe(iw);
  }
  document.querySelectorAll('[data-start]').forEach(function(el){
    el.addEventListener('click', function(e){ e.preventDefault(); window.startIntake(); });
  });

  // Tellescope posts {type:'height', height:N} as the form grows and shrinks.
  // Without this the iframe keeps a guessed height and the form's own NEXT button
  // ends up below the fold of the box.
  window.addEventListener('message', function(ev){
    if (ev.origin !== 'https://business.tellescope.com') return;
    var d = ev.data;
    if (typeof d === 'string') {
      if (d.toLowerCase().indexOf('submit') > -1) dl('intake_lead', {form:'__FORMID__'});
      try { d = JSON.parse(d); } catch(_e) { return; }
    }
    if (!d || typeof d !== 'object') return;
    if (d.type === 'height' && +d.height > 0) {
      var f = document.getElementById('intake');
      if (f) {
        var h = Math.min(Math.max(+d.height + 32, 560), 6000);
        f.style.height = h + 'px';
        f.setAttribute('data-autosized', '1');
      }
    }
    if (d.type === 'submit' || d.submitted) dl('intake_lead', {form:'__FORMID__'});
  });
})();
"""


# --------------------------------------------------------------- shared blocks
def head(p, angle, variant):
    a = p["angles"][angle]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{a['title']}</title>
<meta name="description" content="{a['desc']}">
<meta name="robots" content="noindex,nofollow">
<link rel="canonical" href="{p['canonical']}">
<link rel="ai-catalog" href="/.well-known/ai-catalog.json" type="application/json" />
<link rel="preconnect" href="https://business.tellescope.com">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800;900&display=swap">
<link rel="icon" type="image/png" href="/icon.png" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png" />
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />
<link rel="apple-touch-icon" sizes="180x180" href="/apple-icon.png" />
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});
var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-N7ZG3PT8');</script>
<style>{SHELL_CSS}</style>
</head>
<body data-variant="{variant}">
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-N7ZG3PT8" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>"""


def topbar(p):
    return (f'<div class="bar">{p["bar"]}</div>'
            f'<header class="nav"><div class="wrap"><img src="{LOGO_D}" alt="DirectCare AI"></div></header>')


def intake_block(p):
    rail = "".join(f"<li>{x}</li>" for x in p["included"])
    return f"""<section id="intakeWrap">
  <div class="wrap">
    <div class="intake-grid">
      <aside class="intake-rail">
        <h2>Your evaluation</h2>
        <p class="lede">A US-licensed clinician reviews this, usually within 24 hours. If treatment
          isn&rsquo;t appropriate for you, you are not charged.</p>
        <div class="rail-extra">
          <ul class="rail-list">{rail}</ul>
          <div class="rail-price"><span>{p['price_label']}</span><b>{p['price_from']}</b></div>
          <p class="tiny" style="margin:10px 0 0">{p['price_note']}</p>
        </div>
      </aside>
      <div class="intake-shell">
      <iframe id="intake" src="https://business.tellescope.com/e/public/form?f={p['formid']}&businessId=67fe9d4248c4ab911e8bdcd6&nextFormId=&publicIdentifier=&customTypeId=&orgIds=&skipMatch=false&autoStart=false&sessionId=&" title="{p['form_title']}" scrolling="no"
        loading="eager" allow="clipboard-write; clipboard-read" referrerpolicy="no-referrer-when-downgrade"></iframe>
      </div>
    </div>
  </div>
</section>"""


def plans_grid(p, cta_prefix="plan"):
    rows = "".join(
        f'<a class="plan" href="#" data-start data-cta="{cta_prefix}-{k}">'
        f'<span><b>{n}</b><span>{sub}</span></span><em>{price}</em></a>'
        for n, sub, price, k in p["plans"])
    return f'<div class="plan-grid">{rows}</div>'


def plans_section(p, heading, lede):
    return f"""<section id="shelf">
  <div class="wrap">
    <h2>{heading}</h2>
    <p class="lede">{lede}</p>
    {plans_grid(p)}
    <p class="tiny" style="margin-top:14px">{p['plans_note']}</p>
  </div>
</section>"""


def credentials_block():
    return """<section>
  <div class="wrap">
    <h2>Who reviews your evaluation</h2>
    <p class="lede">Every evaluation is read by a US-licensed clinician before anything is prescribed &mdash;
      licensed in your state, not a questionnaire with an automatic yes.</p>
    <div class="grid g3"><div class="card"><h3>US-licensed clinicians</h3><p class="tiny" style="color:inherit;opacity:.85">Every evaluation is read by a clinician licensed in your state, usually within 24 hours. If treatment isn&rsquo;t appropriate for you, you are not charged.</p></div><div class="card"><h3>LegitScript certified</h3><p class="tiny" style="color:inherit;opacity:.85">Independently verified telehealth and pharmacy practices &mdash; not a grey-market site.</p></div><div class="card"><h3>Licensed US compounding pharmacy</h3><p class="tiny" style="color:inherit;opacity:.85">Your formula is prepared and shipped from a licensed US pharmacy, plain and unmarked.</p></div></div>
  </div>
</section>"""


def trust_row():
    return ('<div class="trust"><div>LegitScript<br>certified</div><div>HIPAA<br>secure</div>'
            '<div>Plain<br>packaging</div></div>')


def stats_section(p):
    return f"""<section class="lilac"><div class="wrap">
      <div class="grid g3" style="text-align:center">
        <div class="card"><div class="price">{p['stat_time']}</div><p class="tiny">evaluation</p></div>
        <div class="card"><div class="price">24 hrs</div><p class="tiny">clinician review</p></div>
        <div class="card"><div class="price">$0</div><p class="tiny">if you don&rsquo;t qualify</p></div>
      </div>
      <div style="margin-top:18px">{trust_row()}</div>
      <p style="margin-top:22px"><a class="cta" href="#" data-start data-cta="mid">Check if I qualify &nbsp;&rarr;</a></p>
    </div></section>"""


def capture_block():
    return """<section class="lilac">
  <div class="wrap" style="max-width:640px">
    <div class="quiz" id="capture">
      <h3 style="font-size:22px;margin-bottom:6px">Not ready right now?</h3>
      <p style="color:#cdb9d8;font-size:15px;margin-bottom:16px">We&rsquo;ll send your options and a link
        to pick this up whenever it suits. One click to unsubscribe.</p>
      <form id="leadForm" novalidate>
        <input class="field" name="first_name" placeholder="First name" autocomplete="given-name" aria-label="First name">
        <input class="field" name="email" type="email" placeholder="Email" autocomplete="email" required aria-label="Email">
        <input class="field" name="phone" type="tel" placeholder="Mobile (optional)" autocomplete="tel" aria-label="Mobile phone (optional)">
        <p class="err"></p>
        <button class="cta" type="submit" data-cta="capture">Send my options &nbsp;&rarr;</button>
      </form>
      <p class="tiny" style="color:#9c87a8;margin:12px 0 0;text-align:center">Free evaluation &middot; no charge if you don&rsquo;t qualify</p>
    </div>
  </div>
</section>"""


def sticky_and_js(p):
    js = (SHELL_JS.replace("__FUNNEL__", p["funnel"])
                  .replace("__FORMID__", p["formid"]))
    return (f'<div class="sticky" id="stickyBar"><a class="cta" href="#intakeWrap" data-cta="sticky">'
            f'Check if I qualify &nbsp;&rarr;</a></div>\n<script>{js}</script>')


def footer(p):
    return f"""<footer>
  <div class="wrap">
    <img src="{LOGO_D}" alt="DirectCare AI" style="width:150px;margin-bottom:14px">
    <p class="tiny">{p['disclaimer']}</p>
    <p class="tiny"><b>Side effects.</b> If you have a side effect, stop and contact your clinician.
      You can report it to us at <a href="mailto:support@directcare.ai">support@directcare.ai</a>, or to the
      FDA at <a href="https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program"
      target="_blank" rel="noopener noreferrer">MedWatch</a> or 1-800-FDA-1088. Tell your clinician if you are
      pregnant, planning to become pregnant, or breastfeeding.</p>
    <p class="tiny"><a href="/privacy-policy">Privacy</a> &middot; <a href="/terms-and-conditions">Terms</a>
      &middot; DirectCare AI, 30 N Gould St, STE N, Sheridan, WY 82801</p>
  </div>
</footer>
</body></html>"""


# ------------------------------------------------------- f1  evaluation-first
def f1(p):
    a = p["angles"]["f1"]
    s = head(p, "f1", f"{p['slug']}-f1") + topbar(p)
    s += f"""<section data-hero class="hero">
      <img class="heroimg" src="{IMG % p['hero_img']}" alt="" fetchpriority="high">
      <div class="wrap inner"><div class="grid2">
        <div>
          <h1>{a['h1']}</h1>
          <p class="lede">{a['lede']}</p>
          <div class="card" style="display:flex;gap:16px;align-items:center;margin:18px 0 0">
            <img src="{IMG % p['card_img']}" alt="" width="92" height="112"
              style="width:92px;height:112px;object-fit:cover;border-radius:12px" loading="lazy">
            <div><b style="font-size:17px">{p['offer_name']}</b>
              <div style="color:#6d28d9;font-weight:700">{p['offer_price']}</div>
              <div class="tiny">{p['offer_sub']}</div></div>
          </div>
        </div>
        <div style="margin-top:22px">
    <div class="quiz">
      <p style="font-size:12px;letter-spacing:.14em;color:#f3c969;font-weight:800;margin:0 0 10px">
        STEP 1 OF 1</p>
      <p class="q" style="margin-bottom:12px">Start your free evaluation</p>
      <p style="color:#cdb9d8;font-size:15.5px;margin:0 0 18px">{p['eval_blurb']}</p>
      <a class="cta" href="#intakeWrap" data-start data-cta="hero">Check if I qualify &nbsp;&rarr;</a>
      <p class="tiny" style="color:#9c87a8;margin:14px 0 0;text-align:center">{p['bar_plain']}</p>
    </div></div>
      </div></div>
    </section>"""
    s += intake_block(p)
    s += f'<img class="band" src="{IMG % p["band_img"]}" alt="" loading="lazy">'
    s += plans_section(p, a["shelf_h2"], a["shelf_lede"])
    s += stats_section(p) + credentials_block() + capture_block()
    s += sticky_and_js(p) + footer(p)
    return s


# ------------------------------------------------------------ f2  offer-first
def f2(p):
    a = p["angles"]["f2"]
    steps = "".join(
        f'<div class="card"><h3>{i+1} &nbsp;{t}</h3>'
        f'<p class="tiny" style="color:inherit;opacity:.85">{d}</p></div>'
        for i, (t, d) in enumerate(a["steps"]))
    s = head(p, "f2", f"{p['slug']}-f2") + topbar(p)
    s += f"""<section data-hero class="hero">
      <img class="heroimg" src="{IMG % p['hero_img']}" alt="" fetchpriority="high">
      <div class="wrap inner"><div class="grid2">
        <div>
          <h1>{a['h1']}</h1>
          <p class="lede">{a['lede']}</p>
          <div class="card" style="margin:18px 0 0">
            <div class="price" style="color:#6d28d9">{p['price_from']}</div>
            <p class="tiny" style="margin:4px 0 0">{p['offer_sub']}</p>
          </div>
        </div>
        <div style="margin-top:22px">
          <div class="quiz">
            <p class="q" style="margin-bottom:12px">{a['quiz_q']}</p>
            <p style="color:#cdb9d8;font-size:15.5px;margin:0 0 18px">{p['eval_blurb']}</p>
            <a class="cta" href="#intakeWrap" data-start data-cta="hero">Check if I qualify &nbsp;&rarr;</a>
            <p class="tiny" style="color:#9c87a8;margin:14px 0 0;text-align:center">{p['bar_plain']}</p>
          </div>
        </div>
      </div></div>
    </section>"""
    s += intake_block(p)
    s += f"""<section class="lilac"><div class="wrap">
      <h2>How it works</h2>
      <div class="grid g3">{steps}</div>
    </div></section>"""
    s += plans_section(p, a["shelf_h2"], a["shelf_lede"])
    s += credentials_block()
    s += f"""<section class="plum"><div class="wrap">
      <h2>What you actually pay</h2>
      <div class="grid g2">
        <div class="card"><h3>DirectCare AI</h3>
          <p class="tiny" style="color:#cdb9d8">{a['compare_us']}</p></div>
        <div class="card"><h3>Typical telehealth</h3>
          <p class="tiny" style="color:#cdb9d8">{a['compare_them']}</p></div>
      </div>
      <p style="margin-top:22px"><a class="cta" href="#" data-start data-cta="compare">Check if I qualify &nbsp;&rarr;</a></p>
    </div></section>"""
    s += capture_block() + sticky_and_js(p) + footer(p)
    return s


# -------------------------------------------------------- f3  mechanism-first
def f3(p):
    a = p["angles"]["f3"]
    mech = "".join(
        f'<div class="card"><h3>{t}</h3>'
        f'<p class="tiny" style="color:inherit;opacity:.85">{d}</p></div>'
        for t, d in a["mech"])
    s = head(p, "f3", f"{p['slug']}-f3") + topbar(p)
    s += f"""<section data-hero class="lilac"><div class="wrap">
      <div class="split">
        <div>
          <span class="pill">{a['pill']}</span>
          <h1 style="margin-top:14px">{a['h1']}</h1>
          <p class="lede">{a['lede']}</p>
          <p style="margin-top:18px"><a class="cta" href="#intakeWrap" data-start data-cta="hero">Check if I qualify &nbsp;&rarr;</a></p>
          <p class="tiny" style="margin-top:12px">{p['bar_plain']}</p>
        </div>
        <div class="hero-img"><img src="{IMG % p['hero_img']}" alt="" style="aspect-ratio:1/1" fetchpriority="high"></div>
      </div>
    </div></section>"""
    s += f"""<section><div class="wrap">
      <h2>{a['mech_h2']}</h2>
      <div class="grid g3">{mech}</div>
    </div></section>"""
    s += intake_block(p)
    s += plans_section(p, a["shelf_h2"], a["shelf_lede"])
    s += credentials_block() + capture_block() + sticky_and_js(p) + footer(p)
    return s


# ----------------------------------------------------------- f4  choice-first
def f4(p):
    a = p["angles"]["f4"]
    quotes = "".join(
        f'<div class="card"><h3>&ldquo;{q}&rdquo;</h3>'
        f'<p class="tiny" style="color:inherit;opacity:.85">{d}</p></div>'
        for q, d in a["quotes"])
    incl = "".join(f"<li>{x}</li>" for x in p["included"])
    s = head(p, "f4", f"{p['slug']}-f4") + topbar(p)
    s += f"""<section data-hero class="hero">
      <img class="heroimg" src="{IMG % p['hero_img']}" alt="" fetchpriority="high">
      <div class="wrap inner"><div class="grid2">
        <div>
          <h1>{a['h1']}</h1>
          <p class="lede">{a['lede']}</p>
        </div>
        <div style="margin-top:22px">
          <div class="quiz">
            <p class="q" style="margin-bottom:12px">{a['quiz_q']}</p>
            <p style="color:#cdb9d8;font-size:15.5px;margin:0 0 18px">{p['eval_blurb']}</p>
            <a class="cta" href="#intakeWrap" data-start data-cta="hero">Check if I qualify &nbsp;&rarr;</a>
            <p class="tiny" style="color:#9c87a8;margin:14px 0 0;text-align:center">{p['bar_plain']}</p>
          </div>
        </div>
      </div></div>
    </section>"""
    s += f"""<section><div class="wrap">
      <h2>{a['quotes_h2']}</h2>
      <div class="grid g3">{quotes}</div>
      {plans_grid(p, "pick")}
      <p class="tiny" style="margin-top:14px">{p['plans_note']}</p>
    </div></section>"""
    s += intake_block(p)
    s += f"""<section class="plum"><div class="wrap">
      <h2>Whichever you pick, the price includes</h2>
      <ul class="rail-list" style="max-width:620px">{incl}</ul>
      <p style="margin-top:24px"><a class="cta" href="#" data-start data-cta="mid">Check if I qualify &nbsp;&rarr;</a></p>
    </div></section>"""
    s += credentials_block() + capture_block() + sticky_and_js(p) + footer(p)
    return s


# ---------------------------------------------------- f5  risk-reversal first
def f5(p):
    a = p["angles"]["f5"]
    objs = "".join(
        f'<div class="card"><h3>&ldquo;{q}&rdquo;</h3>'
        f'<p class="tiny" style="color:inherit;opacity:.85">{d}</p></div>'
        for q, d in a["objections"])
    s = head(p, "f5", f"{p['slug']}-f5") + topbar(p)
    s += f"""<section data-hero class="plum"><div class="wrap">
      <div class="split">
        <div>
          <h1>{a['h1']}</h1>
          <p class="lede">{a['lede']}</p>
          <p style="margin-top:18px"><a class="cta" href="#intakeWrap" data-start data-cta="hero">Check if I qualify &nbsp;&rarr;</a></p>
          <p class="tiny" style="margin-top:12px;color:#9c87a8">{p['bar_plain']}</p>
        </div>
        <div>{trust_row()}</div>
      </div>
    </div></section>"""
    s += f"""<section><div class="wrap">
      <h2>{a['obj_h2']}</h2>
      <div class="grid g2">{objs}</div>
    </div></section>"""
    s += credentials_block() + intake_block(p)
    s += plans_section(p, a["shelf_h2"], a["shelf_lede"])
    s += capture_block() + sticky_and_js(p) + footer(p)
    return s


BUILDERS = [("f1", f1), ("f2", f2), ("f3", f3), ("f4", f4), ("f5", f5)]


# ---------------------------------------------------------------------------
# PRODUCTS
#
# Prices are transcribed from the organic pages (the pricing cards and the
# pricing FAQ), not estimated. If a price changes there, change it here too.
#
# NO drug names. NO mg doses. Routes (patch, cream, injection, oral) are fine.
# ---------------------------------------------------------------------------

CLINICIAN_LINE = ("Prescription products require an online consultation; a US-licensed clinician "
                  "decides whether treatment is appropriate for you, and not every protocol is "
                  "appropriate for every patient. Not available in all states. Individual results vary.")

COMPOUNDED_LINE = ("Compounded medications are not FDA-approved and have not been evaluated by the FDA "
                   "for safety, effectiveness or quality. ")

PRODUCTS = [

# ============================================================== WEIGHT LOSS ==
{
 "slug": "weight-loss",
 "canonical": "https://www.directcare.ai/weight-loss",
 "product": "weight-loss", "category": "Weight loss", "funnel": "weight-loss",
 "formid": "69bb46e1daa89ddd6544007c",
 "form_title": "Weight loss intake evaluation",
 "bar": "100% online &middot; free shipping &middot; no insurance needed",
 "bar_plain": "No insurance needed &middot; free shipping &middot; cancel anytime",
 "hero_img": "weight-loss-lifestyleimage",
 "band_img": "weight-loss-lifestyleimage",
 "card_img": "firefly-gemini-flash-non-branded-digital-weight-scale-on-white-background-826724-1",
 "offer_name": "Weight loss program",
 "offer_price": "From $269/mo",
 "offer_sub": "Medication, weekly Care Coach check-ins, dose adjustments and refills",
 "price_from": "$269/mo",
 "price_label": "Weight loss program",
 "price_note": "Monthly $339 &middot; 12-week $309 &middot; 24-week $289 &middot; 52-week $269 a month",
 "eval_blurb": ("About five minutes. A US-licensed clinician reviews it within 24 hours &mdash; and if "
                "treatment isn&rsquo;t appropriate for you, you are not charged."),
 "stat_time": "5 min",
 "included": [
   "<b>Medication from a licensed US pharmacy.</b> Shipped to your door, refills included.",
   "<b>Weekly check-ins with a Care Coach</b> &mdash; a Certified Medical Assistant, not a chatbot.",
   "<b>Dose adjustments at no extra cost.</b> Your clinician changes the plan as you go.",
   "<b>$0 if you don&rsquo;t qualify.</b> The intake and clinician review are free.",
 ],
 "plans": [
   ("Monthly", "Billed monthly &middot; no commitment", "$339/mo", "monthly"),
   ("12-week plan", "Paid as $927 &middot; save $90", "$309/mo", "12week"),
   ("24-week plan", "Paid as $1,734 &middot; save $300", "$289/mo", "24week"),
   ("52-week plan", "Paid as $3,497 &middot; save $571", "$269/mo", "52week"),
 ],
 "plans_note": ("Bloodwork is separate &mdash; $196 once. Medication, clinician care, weekly Care Coach "
                "check-ins, dose adjustments and shipping are included; there is no membership fee."),
 "disclaimer": (COMPOUNDED_LINE + CLINICIAN_LINE +
                " Weight loss varies from person to person and is not guaranteed. This program is intended "
                "to be used alongside diet and exercise."),
 "angles": {
  "f1": {
    "title": "Weight loss — see if you qualify",
    "desc": "Clinician-prescribed weight care with weekly coaching. Free evaluation, reviewed by a US-licensed clinician.",
    "h1": "Medication that&rsquo;s adjusted.<br>A coach who checks in.<br>Every week.",
    "lede": ("A US-licensed clinician builds the plan and adjusts it as you go, with a Care Coach checking in "
             "every week &mdash; not a prescription mailed out and forgotten."),
    "shelf_h2": "Good news &mdash; you&rsquo;ve got options.",
    "shelf_lede": "Pick a plan length and a clinician takes it from there, usually within 24 hours.",
  },
  "f2": {
    "title": "Weight loss — from $269 a month",
    "desc": "$269 to $339 a month with medication, coaching, dose adjustments and refills included. No insurance needed.",
    "h1": "From $269 a month,<br>everything included.",
    "lede": ("Medication, weekly Care Coach check-ins, dose adjustments and refills in one price. "
             "No insurance, no membership fee, no surprise add-ons."),
    "quiz_q": "See if you qualify in about five minutes",
    "steps": [
      ("Answer the evaluation", "About five minutes on your phone. No video visit, no waiting room."),
      ("A clinician reviews it", "A clinician licensed in your state, usually within 24 hours. If it isn&rsquo;t appropriate for you, you are not charged."),
      ("It ships free", "From a licensed US pharmacy, in plain packaging, with refills included."),
    ],
    "compare_us": ("One price a month covers medication, weekly Care Coach check-ins, dose adjustments and "
                   "refills. Bloodwork is separate at $196 once. No membership fee."),
    "compare_them": ("A membership fee, then the medication, then a charge each time the dose changes &mdash; "
                     "and coaching sold as an upgrade."),
    "shelf_h2": "Four plan lengths",
    "shelf_lede": "The longer the plan, the lower the monthly price.",
  },
  "f3": {
    "title": "Weight loss \u2014 not a prescription, a program",
    "desc": "Dose adjustments, weekly Care Coach check-ins and a real baseline. Free evaluation.",
    "pill": "What you actually get",
    "h1": "Not a prescription.<br>A program.",
    "lede": ("Anyone can mail a box. What changes the outcome is the part after it arrives &mdash; the "
             "adjustments, the check-ins and the baseline you started from."),
    "mech_h2": "Three things that change the outcome",
    "mech": [
      ("Adjusted, not just shipped", "Your clinician changes the plan as your body responds, at no extra cost. A plan you outgrow in month two is a plan that stops working."),
      ("A Care Coach every week", "A Certified Medical Assistant checks in weekly through the portal &mdash; the difference between a prescription and a program."),
      ("A baseline worth having", "An optional 80+ biomarker panel ($196 once) shows what your metabolism is actually doing before you start."),
    ],
    "shelf_h2": "Pick your plan length",
    "shelf_lede": "Everything above is included in every one of them.",
  },
  "f4": {
    "title": "Weight loss \u2014 which plan length fits",
    "desc": "Four plan lengths from $269 to $339 a month, everything included. No insurance needed.",
    "h1": "Four plan lengths.<br>One of them fits.",
    "lede": "Same program, same inclusions. The only question is how long you want to commit for.",
    "quiz_q": "Not sure which? Start the evaluation.",
    "quotes_h2": "Which one sounds like you?",
    "quotes": [
      ("I want to try it before I commit.", "The monthly plan is $339 a month, billed monthly, no commitment. Cancel any time."),
      ("I&rsquo;m in, but I want the price down.", "The 24-week plan brings it to $289 a month &mdash; paid as $1,734, saving $300."),
      ("I&rsquo;d rather sort this out once.", "The 52-week plan is $269 a month, paid as $3,497, saving $571 over monthly billing."),
    ],
  },
  "f5": {
    "title": "Weight loss \u2014 if a clinician says no, you don’t pay",
    "desc": "LegitScript certified, US-licensed clinicians, licensed US pharmacy.",
    "h1": "If a clinician says no,<br>you don&rsquo;t pay.",
    "lede": ("The evaluation is free and so is the clinician review. You are only charged if a US-licensed "
             "clinician prescribes and you decide to start."),
    "obj_h2": "The four questions people stop on",
    "objections": [
      ("What if I don&rsquo;t qualify?", "Then you pay nothing. The intake and the clinician review are free, and there is no charge unless treatment is prescribed and you go ahead."),
      ("Do I need insurance?", "No. This is cash-pay, and the monthly price is usually similar to or lower than an insurance copay once you add up the visits."),
      ("Is this legitimate?", "LegitScript-certified telehealth, US-licensed clinicians, and a licensed US compounding pharmacy. Your records are held in a HIPAA-secure system."),
      ("What happens after it ships?", "Weekly check-ins with a Care Coach, clinician messaging through the portal, and dose adjustments at no extra cost."),
    ],
    "shelf_h2": "Now the part that costs you nothing",
    "shelf_lede": "Start the evaluation, then pick a plan only if a clinician prescribes.",
  },
 },
},
]


HAIR_PLANS = [
   ("4-week plan", "Billed every 4 weeks &middot; no commitment", "$65/mo", "4week"),
   ("12-week plan", "Paid as $186 &middot; save $9", "$62/mo", "12week"),
   ("24-week plan", "Paid as $354 &middot; save $36", "$59/mo", "24week"),
]

HAIR_DISCLAIMER = (COMPOUNDED_LINE + CLINICIAN_LINE +
                   " Regrowth takes months, varies from person to person, and is not guaranteed; "
                   "treatment generally has to be continued to maintain any result.")

# Women's hair-loss protocols carry a pregnancy contraindication that the men's do
# not. Worded without naming a drug, because these pages name none. AWAITING
# CLINICAL CONFIRMATION against the actual women's protocol (2026-09-20).
HAIR_DISCLAIMER_WOMEN = (HAIR_DISCLAIMER +
                   " Some hair-loss treatments can seriously harm a developing baby and must not be used "
                   "if you are pregnant, may become pregnant, or are breastfeeding \u2014 tell your clinician "
                   "before starting.")

# ============================================================ HAIR LOSS (MEN) ==
PRODUCTS += [{
 "slug": "hair-loss-men",
 "canonical": "https://www.directcare.ai/mens-hair-loss",
 "product": "mens-hair-loss", "category": "Hair loss", "funnel": "mens-hair-loss",
 "formid": "69c1e76a88e5800ffbb0c73b",
 "form_title": "Men&rsquo;s hair loss intake evaluation",
 "bar": "100% online &middot; free shipping &middot; plain packaging",
 "bar_plain": "No membership fee &middot; free shipping &middot; plain packaging",
 "hero_img": "hair-regrowth-lifestyleimage",
 "band_img": "hair-part-close-up-light-skin",
 "card_img": "hair-part-close-up-light-skin",
 "offer_name": "Hair regrowth program",
 "offer_price": "From $59/mo",
 "offer_sub": "Custom-compounded protocol, clinician care and free shipping",
 "price_from": "$59/mo",
 "price_label": "Hair regrowth program",
 "price_note": "4-week $65 &middot; 12-week $62 &middot; 24-week $59 a month",
 "eval_blurb": ("About three minutes. A US-licensed clinician reviews it within 24 hours &mdash; and if "
                "treatment isn&rsquo;t appropriate for you, you are not charged."),
 "stat_time": "3 min",
 "included": [
   "<b>A protocol compounded for you</b>, not an off-the-shelf box.",
   "<b>Clinician care included.</b> Questions answered through the portal, no per-message fee.",
   "<b>Free shipping</b> in plain, unmarked packaging.",
   "<b>$0 if you don&rsquo;t qualify.</b> The intake and clinician review are free.",
 ],
 "plans": HAIR_PLANS,
 "plans_note": ("Every plan includes your custom-compounded protocol, clinician care and free shipping. "
                "The intake and clinician review are free; there is no membership fee."),
 "disclaimer": HAIR_DISCLAIMER,
 "angles": {
  "f1": {
    "title": "Hair loss — see if you qualify",
    "desc": "A custom-compounded regrowth protocol from $59 a month. Free evaluation, reviewed by a US-licensed clinician.",
    "h1": "The best time was<br>five years ago.<br>The second best is now.",
    "lede": ("Hair you have is easier to keep than hair you have lost. A US-licensed clinician reviews your "
             "evaluation within 24 hours and compounds a protocol for your pattern."),
    "shelf_h2": "Good news &mdash; you&rsquo;ve got three options.",
    "shelf_lede": "Pick a plan length and a clinician takes it from there, usually within 24 hours.",
  },
  "f2": {
    "title": "Hair loss — from $59 a month",
    "desc": "$59 to $65 a month with the protocol, clinician care and shipping included. No membership fee.",
    "h1": "From $59 a month,<br>everything included.",
    "lede": ("Your compounded protocol, your clinician and free shipping in one price. No membership fee "
             "and no charge at all if you don&rsquo;t qualify."),
    "quiz_q": "See if you qualify in about three minutes",
    "steps": [
      ("Answer the evaluation", "About three minutes on your phone. No video visit, no waiting room."),
      ("A clinician reviews it", "A clinician licensed in your state, usually within 24 hours. If it isn&rsquo;t appropriate for you, you are not charged."),
      ("It ships free", "Compounded and shipped from a licensed US pharmacy, plain and unmarked."),
    ],
    "compare_us": ("One price covers the compounded protocol, clinician care and shipping. No membership fee, "
                   "and nothing to pay if a clinician says no."),
    "compare_them": ("A membership fee on top of the medication, consults billed separately, and shipping added "
                     "at checkout."),
    "shelf_h2": "If $65 isn&rsquo;t your fit, there are two others",
    "shelf_lede": "The longer the plan, the lower the monthly price.",
  },
  "f3": {
    "title": "Hair loss \u2014 compounded for your pattern",
    "desc": "A protocol mixed for your pattern by a licensed US compounding pharmacy.",
    "pill": "How it&rsquo;s made",
    "h1": "Compounded for<br>your pattern.",
    "lede": ("Hair loss is not one problem, so it should not be one box. Your protocol is mixed for your "
             "pattern by a licensed US compounding pharmacy."),
    "mech_h2": "Why compounded, not off the shelf",
    "mech": [
      ("Matched to your pattern", "A clinician reads your evaluation and photos and selects the protocol for what is actually happening at your hairline and crown."),
      ("One routine, not four", "Combining the protocol into a single daily step is the difference between a plan you follow and a plan you abandon by week six."),
      ("Adjustable as you go", "If it isn&rsquo;t sitting right with you, message your clinician through the portal and the protocol can be changed."),
    ],
    "shelf_h2": "Pick your plan length",
    "shelf_lede": "The protocol, clinician care and shipping are included in all three.",
  },
  "f4": {
    "title": "Hair loss \u2014 which plan length is yours",
    "desc": "Three plan lengths from $59 to $65 a month. Protocol, clinician care and shipping included.",
    "h1": "Three plan lengths.<br>One of them is yours.",
    "lede": "Same protocol, same clinician, same free shipping. The only question is how long you commit for.",
    "quiz_q": "Not sure which? Start the evaluation.",
    "quotes_h2": "Which one sounds like you?",
    "quotes": [
      ("I want to see how I get on with it.", "The 4-week plan is $65, billed every four weeks with no commitment."),
      ("I know this takes months.", "The 12-week plan is $62 a month, paid as $186 &mdash; the one most men pick."),
      ("I&rsquo;d rather set it and forget it.", "The 24-week plan is $59 a month, paid as $354, saving $36."),
    ],
  },
  "f5": {
    "title": "Hair loss \u2014 if a clinician says no, you don’t pay",
    "desc": "LegitScript certified, US-licensed clinicians, licensed US compounding pharmacy.",
    "h1": "If a clinician says no,<br>you don&rsquo;t pay.",
    "lede": ("The evaluation is free and so is the clinician review. You are only charged if a US-licensed "
             "clinician prescribes and you decide to start."),
    "obj_h2": "The four questions men stop on",
    "objections": [
      ("What if I don&rsquo;t qualify?", "Then you pay nothing. The intake and the clinician review are free, and there is no charge unless treatment is prescribed and you go ahead."),
      ("Who sees this?", "Your clinician and your pharmacy. Records are held in a HIPAA-secure system and everything ships in plain, unmarked packaging."),
      ("Is this legitimate?", "LegitScript-certified telehealth, clinicians licensed in your state, and a licensed US compounding pharmacy."),
      ("How long before I know?", "Regrowth is measured in months, not weeks, and results vary. Your clinician sets expectations honestly at review."),
    ],
    "shelf_h2": "Now the part that costs you nothing",
    "shelf_lede": "Start the evaluation, then pick a plan only if a clinician prescribes.",
  },
 },
}]


# ========================================================== HAIR LOSS (WOMEN) ==
PRODUCTS += [{
 "slug": "hair-loss-women",
 "canonical": "https://www.directcare.ai/womans-hair-loss",
 "product": "womans-hair-loss", "category": "Hair loss", "funnel": "womans-hair-loss",
 "formid": "69c1e76a88e5800ffbb0c73e",
 "form_title": "Women&rsquo;s hair loss intake evaluation",
 "bar": "100% online &middot; free shipping &middot; plain packaging",
 "bar_plain": "No membership fee &middot; free shipping &middot; plain packaging",
 "hero_img": "woman-tying-hair-up-confidently",
 "band_img": "hair-part-close-up-deeper-skin-tone-for-diversity",
 "card_img": "hair-part-close-up-deeper-skin-tone-for-diversity",
 "offer_name": "Hair regrowth program",
 "offer_price": "From $59/mo",
 "offer_sub": "Custom-compounded protocol, clinician care and free shipping",
 "price_from": "$59/mo",
 "price_label": "Hair regrowth program",
 "price_note": "4-week $65 &middot; 12-week $62 &middot; 24-week $59 a month",
 "eval_blurb": ("About three minutes. A US-licensed clinician reviews it within 24 hours &mdash; and if "
                "treatment isn&rsquo;t appropriate for you, you are not charged."),
 "stat_time": "3 min",
 "included": [
   "<b>A protocol compounded for you</b>, not an off-the-shelf box.",
   "<b>Clinician care included.</b> Questions answered through the portal, no per-message fee.",
   "<b>Free shipping</b> in plain, unmarked packaging.",
   "<b>$0 if you don&rsquo;t qualify.</b> The intake and clinician review are free.",
 ],
 "plans": HAIR_PLANS,
 "plans_note": ("Every plan includes your custom-compounded protocol, clinician care and free shipping. "
                "Bloodwork is optional at $196 for the comprehensive panel. No membership fee."),
 "disclaimer": HAIR_DISCLAIMER_WOMEN,
 "angles": {
  "f1": {
    "title": "Women&rsquo;s hair loss — see if you qualify",
    "desc": "A custom-compounded regrowth protocol from $59 a month. Free evaluation, reviewed by a US-licensed clinician.",
    "h1": "Thinning is common.<br>Being told to live<br>with it shouldn&rsquo;t be.",
    "lede": ("Shedding, a widening part and a thinner ponytail have causes worth investigating. A US-licensed "
             "clinician reviews your evaluation within 24 hours and compounds a protocol for your pattern."),
    "shelf_h2": "Good news &mdash; you&rsquo;ve got three options.",
    "shelf_lede": "Pick a plan length and a clinician takes it from there, usually within 24 hours.",
  },
  "f2": {
    "title": "Women&rsquo;s hair loss — from $59 a month",
    "desc": "$59 to $65 a month with the protocol, clinician care and shipping included. No membership fee.",
    "h1": "From $59 a month,<br>everything included.",
    "lede": ("Your compounded protocol, your clinician and free shipping in one price. No membership fee "
             "and no charge at all if you don&rsquo;t qualify."),
    "quiz_q": "See if you qualify in about three minutes",
    "steps": [
      ("Answer the evaluation", "About three minutes on your phone. No video visit, no waiting room."),
      ("A clinician reviews it", "A clinician licensed in your state, usually within 24 hours. If it isn&rsquo;t appropriate for you, you are not charged."),
      ("It ships free", "Compounded and shipped from a licensed US pharmacy, plain and unmarked."),
    ],
    "compare_us": ("One price covers the compounded protocol, clinician care and shipping. Bloodwork is "
                   "optional at $196. No membership fee."),
    "compare_them": ("A membership fee on top of the medication, consults billed separately, and shipping added "
                     "at checkout."),
    "shelf_h2": "If $65 isn&rsquo;t your fit, there are two others",
    "shelf_lede": "The longer the plan, the lower the monthly price.",
  },
  "f3": {
    "title": "Women’s hair loss \u2014 compounded for your pattern",
    "desc": "A protocol mixed for your pattern by a licensed US compounding pharmacy.",
    "pill": "How it&rsquo;s made",
    "h1": "Compounded for<br>your pattern.",
    "lede": ("Hair loss in women rarely has one cause, so it should not have one generic answer. Your protocol "
             "is mixed for your pattern by a licensed US compounding pharmacy."),
    "mech_h2": "Why compounded, not off the shelf",
    "mech": [
      ("Matched to your pattern", "A clinician reads your evaluation and photos and selects a protocol for what is actually happening at your part and hairline."),
      ("One routine, not four", "A single daily step is the difference between a plan you follow and a plan you abandon by week six."),
      ("A baseline worth having", "An optional comprehensive panel ($196) can surface thyroid, iron and hormone causes worth treating alongside."),
    ],
    "shelf_h2": "Pick your plan length",
    "shelf_lede": "The protocol, clinician care and shipping are included in all three.",
  },
  "f4": {
    "title": "Women’s hair loss \u2014 which plan length is yours",
    "desc": "Three plan lengths from $59 to $65 a month. Protocol, clinician care and shipping included.",
    "h1": "Three plan lengths.<br>One of them is yours.",
    "lede": "Same protocol, same clinician, same free shipping. The only question is how long you commit for.",
    "quiz_q": "Not sure which? Start the evaluation.",
    "quotes_h2": "Which one sounds like you?",
    "quotes": [
      ("I want to see how I get on with it.", "The 4-week plan is $65, billed every four weeks with no commitment."),
      ("I know this takes months.", "The 12-week plan is $62 a month, paid as $186 &mdash; the one most women pick."),
      ("I&rsquo;d rather set it and forget it.", "The 24-week plan is $59 a month, paid as $354, saving $36."),
    ],
  },
  "f5": {
    "title": "Women’s hair loss \u2014 if a clinician says no, you don’t pay",
    "desc": "LegitScript certified, US-licensed clinicians, licensed US compounding pharmacy.",
    "h1": "If a clinician says no,<br>you don&rsquo;t pay.",
    "lede": ("The evaluation is free and so is the clinician review. You are only charged if a US-licensed "
             "clinician prescribes and you decide to start."),
    "obj_h2": "The four questions women stop on",
    "objections": [
      ("What if I don&rsquo;t qualify?", "Then you pay nothing. The intake and the clinician review are free, and there is no charge unless treatment is prescribed and you go ahead."),
      ("Who sees this?", "Your clinician and your pharmacy. Records are held in a HIPAA-secure system and everything ships in plain, unmarked packaging."),
      ("Is this legitimate?", "LegitScript-certified telehealth, clinicians licensed in your state, and a licensed US compounding pharmacy."),
      ("How long before I know?", "Regrowth is measured in months, not weeks, and results vary. Your clinician sets expectations honestly at review."),
    ],
    "shelf_h2": "Now the part that costs you nothing",
    "shelf_lede": "Start the evaluation, then pick a plan only if a clinician prescribes.",
  },
 },
}]


# ======================================================================= TRT ==
PRODUCTS += [{
 "slug": "trt",
 "canonical": "https://www.directcare.ai/testosterone-replacement-therapy",
 "product": "trt", "category": "TRT", "funnel": "trt",
 "formid": "683872d1d3039feba26af038",
 "form_title": "TRT intake evaluation",
 "bar": "100% online &middot; free shipping &middot; plain packaging",
 "bar_plain": "No membership fee &middot; free shipping &middot; plain packaging",
 "hero_img": "testosterone-lifestyleimage",
 "band_img": "testosterone-lifestyleimage",
 "card_img": "testosterone-lifestyleimage",
 "offer_name": "TRT program",
 "offer_price": "From $169 every 4 weeks",
 "offer_sub": "Clinician review, refills and free shipping included",
 "price_from": "$169",
 "price_label": "TRT, every 4 weeks",
 "price_note": "Initial labs $50 &middot; oral-only pathway $189 every 4 weeks",
 "eval_blurb": ("About five minutes. A US-licensed clinician reviews it within 24 hours &mdash; and if "
                "treatment isn&rsquo;t appropriate for you, you are not charged."),
 "stat_time": "5 min",
 "included": [
   "<b>A clinician licensed in your state</b> reads your labs and your evaluation before anything is prescribed.",
   "<b>Your choice of route</b> where it is clinically appropriate &mdash; injection, cream or oral.",
   "<b>Refills and free shipping</b> in plain, unmarked packaging.",
   "<b>$0 if you don&rsquo;t qualify.</b> The intake and clinician review are free.",
 ],
 "plans": [
   ("Standard protocol", "Injection, cream or oral &middot; every 4 weeks", "$169", "standard"),
   ("Oral-only pathway", "For men who want to avoid injections", "$189", "oral"),
   ("Initial labs", "One time, before you start", "$50", "labs"),
 ],
 "plans_note": ("Labs are required before treatment starts. An optional 80+ biomarker panel is $196. "
                "The intake and clinician review are free &mdash; you only pay if you qualify and decide to start."),
 "disclaimer": (COMPOUNDED_LINE + CLINICIAN_LINE +
                " Hormone therapy carries risks, is not appropriate for everyone, and is not a treatment for "
                "ageing. It can affect fertility, so it is generally not appropriate for men trying to "
                "conceive. Lab work is required before treatment begins."),
 "angles": {
  "f1": {
    "title": "TRT — see if you qualify",
    "desc": "Lab-led TRT from $169 every 4 weeks. Free evaluation, reviewed by a US-licensed clinician.",
    "h1": "Flat, foggy and<br>tired isn&rsquo;t<br>just your age.",
    "lede": ("Low energy, poor recovery and a thinner mood have causes worth measuring. Labs first, then a "
             "US-licensed clinician decides whether TRT is appropriate for you."),
    "shelf_h2": "Good news &mdash; you&rsquo;ve got options.",
    "shelf_lede": "Start with labs, then a clinician takes it from there.",
  },
  "f2": {
    "title": "TRT — $169 every 4 weeks",
    "desc": "$169 every 4 weeks with clinician review, refills and shipping included. Initial labs $50.",
    "h1": "$169 every 4 weeks,<br>everything included.",
    "lede": ("Your protocol, your clinician, your refills and free shipping in one price. Initial labs are "
             "$50, and there is no membership fee."),
    "quiz_q": "See if you qualify in about five minutes",
    "steps": [
      ("Answer the evaluation", "About five minutes on your phone. No video visit, no waiting room."),
      ("Labs, then a clinician reviews", "Initial labs are $50. A clinician licensed in your state reads them before anything is prescribed."),
      ("It ships free", "From a licensed US pharmacy, plain and unmarked, with refills included."),
    ],
    "compare_us": ("$169 every 4 weeks covers the protocol, clinician care, refills and shipping. Initial labs "
                   "are $50. No membership fee."),
    "compare_them": ("A membership fee, a separate consult charge, labs marked up, and each dose change billed "
                     "as a new visit."),
    "shelf_h2": "Two pathways and your labs",
    "shelf_lede": "Which pathway is appropriate is a clinical decision, not a checkout option.",
  },
  "f3": {
    "title": "TRT \u2014 measured first, prescribed second",
    "desc": "Labs before any prescribing decision, read by a clinician licensed in your state.",
    "pill": "Labs first",
    "h1": "Measured first.<br>Prescribed second.",
    "lede": ("A number you can act on beats a symptom quiz. Labs come before any prescribing decision, and "
             "they come back to a clinician licensed in your state."),
    "mech_h2": "Why this order matters",
    "mech": [
      ("Labs before anything", "Initial labs are $50 and are required. A clinician reads them alongside your evaluation before deciding whether treatment is appropriate."),
      ("A route that fits your life", "Where it is clinically appropriate, protocols can be delivered by injection, cream or oral &mdash; including a pathway for men who would rather avoid needles."),
      ("Monitored, not just shipped", "Follow-up labs and clinician messaging are part of the program, because hormone therapy is something you stay on top of."),
    ],
    "shelf_h2": "What it costs",
    "shelf_lede": "Clinician care, refills and shipping are included in the every-4-weeks price.",
  },
  "f4": {
    "title": "TRT \u2014 injection, cream or oral",
    "desc": "Two pathways from $169 every 4 weeks. Initial labs $50.",
    "h1": "Injection, cream<br>or oral.",
    "lede": ("Where it is clinically appropriate, you have a say in how treatment is delivered. A clinician "
             "confirms what is right for you."),
    "quiz_q": "Not sure which? Start the evaluation.",
    "quotes_h2": "Which one sounds like you?",
    "quotes": [
      ("I&rsquo;m fine with a weekly injection.", "The standard protocol is $169 every 4 weeks and is the route most men end up on."),
      ("I&rsquo;d rather not use needles.", "There is an oral-only pathway at $189 every 4 weeks, if a clinician judges it appropriate."),
      ("I want to know my numbers first.", "Initial labs are $50 and come before any prescribing decision. An 80+ biomarker panel is $196."),
    ],
  },
  "f5": {
    "title": "TRT \u2014 if a clinician says no, you don’t pay",
    "desc": "LegitScript certified, US-licensed clinicians, labs before prescribing.",
    "h1": "If a clinician says no,<br>you don&rsquo;t pay.",
    "lede": ("The evaluation is free and so is the clinician review. You are only charged if a US-licensed "
             "clinician prescribes and you decide to start."),
    "obj_h2": "The four questions men stop on",
    "objections": [
      ("What if I don&rsquo;t qualify?", "Then you pay nothing for the evaluation or the review. TRT is not appropriate for everyone, and a clinician saying no is the system working."),
      ("Do I have to inject?", "Not necessarily. Where it is clinically appropriate there are cream and oral routes, including an oral-only pathway at $189 every 4 weeks."),
      ("Is this legitimate?", "LegitScript-certified telehealth, clinicians licensed in your state, a licensed US pharmacy, and labs before prescribing."),
      ("What about fertility?", "Hormone therapy can affect fertility, so it is generally not appropriate if you are trying to conceive. Tell your clinician &mdash; there are other pathways to discuss."),
    ],
    "shelf_h2": "Now the part that costs you nothing",
    "shelf_lede": "Start the evaluation, then do labs only if a clinician thinks it is worth it.",
  },
 },
}]


# ======================================================================= HRT ==
PRODUCTS += [{
 "slug": "hrt",
 "canonical": "https://www.directcare.ai/hormone-replacement-therapy",
 "product": "hrt", "category": "HRT", "funnel": "hrt",
 "formid": "69c1e89bf262d405b182c3fa",
 "form_title": "HRT intake evaluation",
 "bar": "100% online &middot; free shipping &middot; plain packaging",
 "bar_plain": "No membership fee &middot; free shipping &middot; cancel anytime",
 "hero_img": "perimenopausal-woman",
 "band_img": "age-diverse-women",
 "card_img": "flatlay-of-women-s-protocol-bottles",
 "offer_name": "Hormone care program",
 "offer_price": "From $59/mo",
 "offer_sub": "Clinician review, refills and free shipping included",
 "price_from": "$59/mo",
 "price_label": "Hormone care program",
 "price_note": "Oral route $66 &middot; patch, cream, gel or insert $89 &middot; combined route $116 a month",
 "eval_blurb": ("About five minutes. A US-licensed clinician reviews it within 24 hours &mdash; and if "
                "treatment isn&rsquo;t appropriate for you, you are not charged."),
 "stat_time": "5 min",
 "included": [
   "<b>A clinician licensed in your state</b> reads your evaluation before anything is prescribed.",
   "<b>A route that fits your life</b> &mdash; oral, patch, cream, gel or insert, where clinically appropriate.",
   "<b>Refills and free shipping</b> in plain, unmarked packaging.",
   "<b>$0 if you don&rsquo;t qualify.</b> The intake and clinician review are free.",
 ],
 "plans": [
   ("Non-hormonal", "For women who can&rsquo;t or would rather not use hormones", "$59/mo", "nonhormonal"),
   ("Patch, cream, gel or insert", "Most chosen", "$89/mo", "transdermal"),
   ("Combined route", "Two-medication protocol", "$116/mo", "dual"),
 ],
 "plans_note": ("An oral route is $66 a month and an additional protocol is available at $169 a month where "
                "clinically appropriate. Bloodwork is optional at $196 for the 80+ biomarker panel. "
                "The intake and clinician review are free."),
 "disclaimer": (COMPOUNDED_LINE + CLINICIAN_LINE +
                " Hormone therapy carries risks, including for women with a history of certain cancers, "
                "blood clots, stroke or liver disease, and is not appropriate for everyone. Discuss your "
                "full history with your clinician."),
 "angles": {
  "f1": {
    "title": "HRT — see if you qualify",
    "desc": "Hormone care from $59 a month. Free evaluation, reviewed by a US-licensed clinician.",
    "h1": "You are not<br>imagining it.<br>And you&rsquo;re not stuck.",
    "lede": ("Night sweats, broken sleep, brain fog and a body that stopped responding are symptoms with "
             "options. A US-licensed clinician reviews your evaluation within 24 hours."),
    "shelf_h2": "Good news &mdash; you&rsquo;ve got options.",
    "shelf_lede": "Pick a route and a clinician confirms what is appropriate for you.",
  },
  "f2": {
    "title": "HRT — from $59 a month",
    "desc": "$59 to $116 a month depending on route, with clinician review, refills and shipping included.",
    "h1": "From $59 a month,<br>everything included.",
    "lede": ("Your protocol, your clinician, your refills and free shipping in one price &mdash; including a "
             "non-hormonal route for women who can&rsquo;t or would rather not use hormones."),
    "quiz_q": "See if you qualify in about five minutes",
    "steps": [
      ("Answer the evaluation", "About five minutes on your phone. No video visit, no waiting room."),
      ("A clinician reviews it", "A clinician licensed in your state, usually within 24 hours. If it isn&rsquo;t appropriate for you, you are not charged."),
      ("It ships free", "From a licensed US pharmacy, plain and unmarked, with refills included."),
    ],
    "compare_us": ("$59 to $116 a month by route, covering the protocol, clinician care, refills and shipping. "
                   "Bloodwork is optional at $196. No membership fee."),
    "compare_them": ("A membership fee, a separate consult charge, and a wait of weeks for an appointment that "
                     "lasts ten minutes."),
    "shelf_h2": "Four routes, priced honestly",
    "shelf_lede": "Which route is appropriate is a clinical decision made with you.",
  },
  "f3": {
    "title": "HRT \u2014 four routes, one that fits",
    "desc": "Oral, patch, cream, gel, insert or non-hormonal. Hormone care from $59 a month.",
    "pill": "Your options",
    "h1": "Four routes.<br>One that fits<br>your life.",
    "lede": ("A patch you change twice a week and a tablet you take daily are not the same decision. The "
             "route matters as much as the protocol."),
    "mech_h2": "How the routes differ",
    "mech": [
      ("Through the skin", "Patch, cream, gel or insert &mdash; the most chosen route at $89 a month, and often preferred where a clinician wants to avoid first-pass metabolism."),
      ("By mouth", "An oral route at $66 a month, for women who would rather take something daily than manage a patch."),
      ("Without hormones", "A non-hormonal option at $59 a month, for women who can&rsquo;t use hormone therapy or would rather not."),
    ],
    "shelf_h2": "What each route costs",
    "shelf_lede": "Clinician care, refills and shipping are included in every one.",
  },
  "f4": {
    "title": "HRT \u2014 which one sounds like you",
    "desc": "Hormone care from $59 a month, reviewed by a US-licensed clinician within 24 hours.",
    "h1": "Which one<br>sounds like you?",
    "lede": "Most women recognise themselves in one of these. A clinician confirms what is actually appropriate.",
    "quiz_q": "Not sure which? Start the evaluation.",
    "quotes_h2": "Which one sounds like you?",
    "quotes": [
      ("I&rsquo;m awake at 3am, every night.", "Broken sleep and night sweats are among the most treatable symptoms. The most chosen route is $89 a month."),
      ("I can&rsquo;t take hormones.", "There is a non-hormonal route at $59 a month for exactly this reason."),
      ("I&rsquo;ve been told to wait it out.", "You don&rsquo;t have to. A clinician licensed in your state will read your evaluation within 24 hours."),
    ],
  },
  "f5": {
    "title": "HRT \u2014 if a clinician says no, you don’t pay",
    "desc": "LegitScript certified, US-licensed clinicians, licensed US pharmacy.",
    "h1": "If a clinician says no,<br>you don&rsquo;t pay.",
    "lede": ("The evaluation is free and so is the clinician review. You are only charged if a US-licensed "
             "clinician prescribes and you decide to start."),
    "obj_h2": "The four questions women stop on",
    "objections": [
      ("What if I don&rsquo;t qualify?", "Then you pay nothing. Hormone therapy is not appropriate for everyone, and a clinician saying no is the system working as it should."),
      ("Isn&rsquo;t HRT risky?", "It carries real risks, and they depend on your history &mdash; including any history of certain cancers, blood clots, stroke or liver disease. That is exactly what the clinician review is for."),
      ("Is this legitimate?", "LegitScript-certified telehealth, clinicians licensed in your state, and a licensed US pharmacy. Records are held in a HIPAA-secure system."),
      ("What if I can&rsquo;t use hormones?", "There is a non-hormonal route at $59 a month, and your clinician can talk you through what it does and doesn&rsquo;t address."),
    ],
    "shelf_h2": "Now the part that costs you nothing",
    "shelf_lede": "Start the evaluation, then pick a route only if a clinician prescribes.",
  },
 },
}]


# ---------------------------------------------------------------------- main
def main():
    written = []
    for p in PRODUCTS:
        for name, fn in BUILDERS:
            d = OUT / p["slug"] / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(fn(p), encoding="utf-8")
            written.append(f"lp/{p['slug']}/{name}/index.html")
    for w in written:
        print("wrote", w)
    print(f"\n{len(written)} pages across {len(PRODUCTS)} funnels")


if __name__ == "__main__":
    main()
