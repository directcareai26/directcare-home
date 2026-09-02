# -*- coding: utf-8 -*-
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from core import (head, sticky_and_js, intake_block, credentials_block, plans_block, footer, standalone_capture, hero_cta,
                  LOGO_D, LOGO_W, PLANS)

OUT = pathlib.Path.home()/"directcare-home"/"surge"
IMG = "/optimized/%s-1200.webp"

QUIZ_STEPS = [
  {"k":"goal",   "q":"What do you want to fix first?",            "a":["Getting hard","Staying hard","Both"]},
  {"k":"tried",  "q":"Have you tried Viagra or Cialis before?",   "a":["Yes, they worked","Yes, they didn't","Never tried"]},
  {"k":"matters","q":"What matters most to you?",                 "a":["Works fast","Lasts through the weekend","Nothing to swallow","Discreet delivery"]},
  {"k":"setting","q":"Would you rather handle this without a waiting room?", "a":["Yes","Doesn't matter"]},
]

def quiz_block(steps=QUIZ_STEPS, intro=None):
    # single-quoted attribute + apostrophes in the answers ("Doesn't matter") would
    # terminate the attribute early, so escape for an HTML attribute context.
    payload = json.dumps(steps).replace("&", "&amp;").replace('"', "&quot;").replace("'", "&#39;")
    return f"""
    <div class="quiz" id="quiz" data-steps="{payload}">
      <div class="dots"></div>
      <p class="q"></p>
      <div class="opts"></div>
      <button class="skip" data-start data-cta="quiz-skip">Skip and start my evaluation &rarr;</button>
    </div>
    <div class="quiz hide" id="capture">
      <h3 style="font-size:22px;margin-bottom:6px">Where should we send your options?</h3>
      <p style="color:#cdb9d8;font-size:15px;margin-bottom:16px">So you can pick up where you left off if you
        don&rsquo;t finish now. We don&rsquo;t share it, and you can unsubscribe in one click.</p>
      <form id="leadForm" novalidate>
        <input class="field" name="first_name" placeholder="First name" autocomplete="given-name">
        <input class="field" name="email" type="email" placeholder="Email" autocomplete="email" required>
        <input class="field" name="phone" type="tel" placeholder="Mobile (optional)" autocomplete="tel">
        <p class="err"></p>
        <button class="cta" type="submit" data-cta="capture">Show my options &nbsp;&rarr;</button>
      </form>
      <p class="tiny" style="color:#9c87a8;margin:12px 0 0;text-align:center">Free evaluation &middot; no charge if you don&rsquo;t qualify</p>
    </div>"""

def trust_row(plum=False):
    return """<div class="trust"><div>LegitScript<br>certified</div><div>HIPAA<br>secure</div><div>Plain<br>packaging</div></div>"""

# ---------------------------------------------------------------- f1 quiz-first
def f1():
    s  = head("Surge Max — see if you qualify", "Four medications in one liquid dose. Free evaluation, reviewed by a US-licensed clinician.", "f1")
    s += '<div class="bar">100% online &middot; free rush shipping &middot; plain packaging</div>'
    s += f'<header class="nav"><div class="wrap"><img src="{LOGO_D}" alt="DirectCare AI"></div></header>'
    s += f"""<section data-hero class="hero">
      <img class="heroimg" src="{IMG % 'the-strength-couple'}" alt="" fetchpriority="high">
      <div class="wrap inner"><div class="grid2">
        <div>
          <h1>Four medications.<br>One liquid dose.<br>Ninety seconds.</h1>
          <p class="lede">SURGE MAX is a rapid-absorb liquid &mdash; no pill to swallow, no waiting around for it
            to work. A US-licensed clinician reviews your evaluation within 24 hours.</p>
          <div class="card" style="display:flex;gap:16px;align-items:center;margin:18px 0 0">
            <img src="{IMG % 'holding-4in1'}" alt="SURGE MAX single-dose vial" width="92" height="112"
              style="width:92px;height:112px;object-fit:cover;border-radius:12px" loading="lazy">
            <div><b style="font-size:17px">SURGE MAX 10-pack</b>
              <div style="color:#6d28d9;font-weight:700">$179 &middot; $17.90 a dose</div>
              <div class="tiny">Sildenafil 40 &middot; Tadalafil 11 &middot; Vardenafil 7.5 &middot; Apomorphine 2</div></div>
          </div>
        </div>
        <div id="quizTop" style="margin-top:22px">{hero_cta()}</div>
      </div></div>
    </section>"""
    s += intake_block()
    s += f'<img class="band" src="{IMG % "the-strength-couple"}" alt="" loading="lazy">'
    s += plans_block("Good news &mdash; you&rsquo;ve got three options.",
                     "Pick one and a clinician takes it from there, usually within 24 hours.")
    s += f"""<section class="lilac"><div class="wrap">
      <div class="grid g3" style="text-align:center">
        <div class="card"><div class="price">3 min</div><p class="tiny">evaluation</p></div>
        <div class="card"><div class="price">24 hrs</div><p class="tiny">clinician review</p></div>
        <div class="card"><div class="price">$0</div><p class="tiny">if you don&rsquo;t qualify</p></div>
      </div>
      <div style="margin-top:18px">{trust_row()}</div>
      <p style="margin-top:22px"><a class="cta" href="#" data-start data-cta="mid">Check if I qualify &nbsp;&rarr;</a></p>
    </div></section>"""
    s += credentials_block()
    s += standalone_capture() + sticky_and_js("f1") + footer()
    return s

# ---------------------------------------------------------------- f2 offer-first
def f2():
    s  = head("Surge Max — check your eligibility", "$179 for a 10-pack, clinician review and shipping included. No membership fee.", "f2")
    s += '<div class="bar gold">Free evaluation &middot; no charge if you don&rsquo;t qualify &middot; no membership fee</div>'
    s += f'<header class="nav"><div class="wrap"><img src="{LOGO_D}" alt="DirectCare AI"></div></header>'
    s += f"""<section data-hero><div class="wrap split">
      <div>
        <p style="color:#6d28d9;font-weight:800;letter-spacing:.14em;font-size:12px;margin:0 0 10px">SURGE MAX 4-IN-1</p>
        <h1>See if you qualify in about 3 minutes</h1>
        <div style="display:flex;gap:14px;align-items:center;margin:18px 0">
          <span class="price">$179</span>
          <span class="tiny" style="font-size:14px">10-pack &middot; $17.90 a dose<br>Clinician review and free shipping included</span>
        </div>
        <a class="cta" href="#" data-start data-cta="hero" style="margin:0 0 16px">Check My Eligibility</a>
        <ul style="padding-left:20px;color:#4b3d59;margin:0">
          <li>Online evaluation reviewed by a US-licensed clinician</li>
          <li>Shipped free in plain packaging, if prescribed</li>
          <li>Unlimited clinician messaging &mdash; no per-visit fee</li>
        </ul>
      </div>
      <div class="hero-img"><img src="{IMG % 'the-spark-man'}" alt="" style="aspect-ratio:1/1;object-position:center 20%"></div>
    </div></section>"""
    s += intake_block()
    s += f"""<section class="lilac"><div class="wrap">
      <h2>How it works</h2>
      <div class="grid g3">
        <div class="card"><h3>1 &nbsp;Answer the evaluation</h3><p class="tiny">About 3 minutes. No video visit, no waiting room.</p></div>
        <div class="card"><h3>2 &nbsp;A clinician reviews it</h3><p class="tiny">Within 24 hours. If it isn&rsquo;t right for you, you don&rsquo;t pay.</p></div>
        <div class="card"><h3>3 &nbsp;It ships free</h3><p class="tiny">Plain, unmarked packaging. Refills auto-send.</p></div>
      </div>
    </div></section>"""
    s += plans_block("If $179 isn&rsquo;t your fit, there are two others",
                     "Same clinician review, same free shipping, no membership fee on any of them.")
    s += credentials_block()
    s += f"""<section class="plum"><div class="wrap">
      <h2>What you actually pay</h2>
      <div class="grid g2">
        <div class="card" style="background:#6d28d9;border-color:#6d28d9">
          <h3>DirectCare AI</h3><div class="price" style="color:#f3c969">$179</div>
          <p style="color:#e7cdf5;margin:8px 0 0">10 doses, clinician review and shipping. No membership fee, and no charge at all if you don&rsquo;t qualify.</p>
        </div>
        <div class="card"><h3 style="color:#cdb9d8">Typical telehealth</h3>
          <div class="price" style="color:#cdb9d8">$99/mo + medication</div>
          <p style="margin:8px 0 0">A membership billed every month on top of whatever the medication costs.</p>
        </div>
      </div>
      <p style="margin-top:22px"><a class="cta" href="#" data-start data-cta="mid">Check My Eligibility</a></p>
    </div></section>"""
    s += standalone_capture() + sticky_and_js("f2") + footer()
    return s

# ---------------------------------------------------------------- f3 product drop
def f3():
    s  = head("Surge Max — the 4-in-1 liquid", "Four medications in one dose. Absorbs in about 90 seconds.", "f3", dark=True)
    s += f'<header class="nav ink"><div class="wrap"><img src="{LOGO_W}" alt="DirectCare AI"></div></header>'
    s += f"""<section data-hero class="ink"><div class="wrap split">
      <div class="hero-img" style="background:#241432"><img src="{IMG % '4in1-dorp'}" alt="SURGE MAX liquid dose" style="aspect-ratio:1/1"></div>
      <div>
        <p style="color:#f3c969;font-weight:800;letter-spacing:.18em;font-size:12px;margin:0 0 12px">THE 4-IN-1 LIQUID</p>
        <h1 style="color:#fff">Four medications.<br>One dose.<br>Ninety seconds.</h1>
        <p style="color:#a495b2">Sildenafil 40 &middot; Tadalafil 11 &middot; Vardenafil 7.5 &middot; Apomorphine 2</p>
        <div style="display:flex;gap:14px;align-items:center;margin:20px 0">
          <span class="price" style="color:#fff">$179</span>
          <span class="tiny" style="font-size:14px;color:#a495b2">10-pack &middot; $17.90 a dose<br>Clinician review + free shipping included</span>
        </div>
        <a class="cta light" href="#" data-start data-cta="hero" style="margin:0">SEE WHAT&rsquo;S RIGHT FOR ME</a>
        <p class="tiny" style="color:#6f6280;margin-top:12px">Go Long $149 &middot; Daily Boost $119 &middot; no membership fee</p>
      </div>
    </div></section>"""
    # needs the .ink class or `.ink .card` never applies and the white headings vanish on white cards
    s += intake_block(dark=True)
    s += """<section class="ink" style="background:#150e1e"><div class="wrap"><div class="grid g3">
      <div class="card"><h3 style="color:#fff">Absorbs in about 90 seconds</h3><p class="tiny" style="color:#a495b2">No pill to swallow, no waiting on a tablet to work.</p></div>
      <div class="card"><h3 style="color:#fff">A 36-hour window</h3><p class="tiny" style="color:#a495b2">One dose covers the night without watching a clock.</p></div>
      <div class="card"><h3 style="color:#fff">Bypasses the gut</h3><p class="tiny" style="color:#a495b2">Dinner and a glass of wine don&rsquo;t dull the dose.</p></div>
    </div></div></section>"""
    s += plans_block("Three formulas", "Same clinician review, same free shipping, no membership fee.", on_plum=True)
    s += credentials_block()
    s += """<section class="ink"><div class="wrap" style="text-align:center">
      <a class="cta" href="#" data-start data-cta="footer">Check if I qualify &nbsp;&rarr;</a></div></section>"""
    s += standalone_capture(dark=True) + sticky_and_js("f3") + footer()
    return s

# ---------------------------------------------------------------- f4 symptom match
def f4():
    cards = ""
    imgs = ["morning-bed-foreheads-touching", "the-stamina-couple", "dance-embrace"]
    quotes = ["&ldquo;It&rsquo;s hit or miss, and I never know which.&rdquo;",
              "&ldquo;I can get there &mdash; I just can&rsquo;t stay there.&rdquo;",
              "&ldquo;I want it handled, not scheduled.&rdquo;"]
    for (n, p, price, per, d, k), im, q in zip(PLANS, imgs, quotes):
        cards += f"""<div class="card" style="padding:0;overflow:hidden">
          <img src="{IMG % im}" alt="" style="width:100%;height:200px;object-fit:cover;object-position:center 30%" loading="lazy">
          <div style="padding:20px">
            <h3 style="font-size:21px">{q}</h3>
            <p style="color:#6d28d9;font-weight:800;font-size:13px;letter-spacing:.06em;margin:6px 0">{n.upper()} &middot; {p} &middot; {price}</p>
            <p class="tiny">{d}</p>
            <a class="cta" href="#" data-start data-cta="match-{k}" style="font-size:15px;padding:13px">That&rsquo;s me &nbsp;&rarr;</a>
          </div></div>"""
    s  = head("Surge Max — which formula fits", "Three ED formulas from $119. Pick the one that sounds like you.", "f4")
    s += '<div class="bar">Three formulas &middot; one free evaluation &middot; no membership fee</div>'
    s += f'<header class="nav"><div class="wrap"><img src="{LOGO_D}" alt="DirectCare AI"></div></header>'
    s += f"""<section data-hero><div class="wrap" style="text-align:center">
      <h1>Three formulas.<br>One of them is yours.</h1>
      <p class="lede" style="max-width:640px;margin:0 auto">Pick the line that sounds most like you. That answer
        decides which formula a clinician considers first.</p>
    </div></section>
    <section style="padding-top:6px"><div class="wrap"><div class="grid g3">{cards}</div>
      <p style="text-align:center;margin-top:18px"><a href="#quizTop" data-cta="unsure"
        style="color:#6d28d9;font-weight:700;text-decoration:none">Not sure? Take the 60-second match &rarr;</a></p>
    </div></section>"""
    s += f"""<section class="lilac" id="quizTop"><div class="wrap" style="max-width:640px">{hero_cta()}</div></section>"""
    s += intake_block()
    s += f"""<section><div class="wrap">
      <h2>Whichever you pick, the price includes</h2>
      <div class="grid g3">
        <div class="card"><p style="margin:0">A US-licensed clinician reviewing your evaluation within 24 hours</p></div>
        <div class="card"><p style="margin:0">Free rush shipping in plain, unmarked packaging</p></div>
        <div class="card"><p style="margin:0">No membership fee &mdash; and no charge at all if you don&rsquo;t qualify</p></div>
      </div>
    </div></section>"""
    s += credentials_block(on_plum=True)
    s += standalone_capture() + sticky_and_js("f4") + footer()
    return s

# ---------------------------------------------------------------- f5 proof first
def f5():
    objs = [("&ldquo;What if I don&rsquo;t qualify?&rdquo;",
             "Then you don&rsquo;t pay. A US-licensed clinician reviews your evaluation and decides. If it isn&rsquo;t appropriate, there&rsquo;s no charge."),
            ("&ldquo;Who sees this?&rdquo;",
             "A licensed clinician and the pharmacy. It ships in plain, unmarked packaging &mdash; nothing on the box says what&rsquo;s inside."),
            ("&ldquo;Is this legitimate?&rdquo;",
             "LegitScript-certified, US-licensed clinicians, compounded by a licensed US pharmacy. Not a supplement, not a grey-market site."),
            ("&ldquo;Why not just the usual pill?&rdquo;",
             "One dose covers four medications and absorbs in about 90 seconds instead of waiting on a tablet to work.")]
    cards = "".join(f'<div class="card"><h3>{q}</h3><p class="tiny">{a}</p></div>' for q, a in objs)
    s  = head("Surge Max — if a clinician says no, you don't pay", "LegitScript certified, US-licensed clinicians, licensed US pharmacy.", "f5")
    s += f'<header class="nav"><div class="wrap"><img src="{LOGO_D}" alt="DirectCare AI"></div></header>'
    s += f"""<section data-hero><div class="wrap split">
      <div>
        <h1>If a clinician says no, you don&rsquo;t pay.</h1>
        <p class="lede">Most men looking into ED treatment online are really asking one question: is this
          legitimate? Here is the answer before we ask you for anything.</p>
        <div style="margin-top:18px">{trust_row()}</div>
      </div>
      <div class="hero-img"><img src="{IMG % 'warm-confident'}" alt="" style="aspect-ratio:1/1;object-position:center 18%"></div>
    </div></section>"""
    s += f"""<section class="lilac"><div class="wrap">
      <h2>The four questions men stop on</h2>
      <div class="grid g2">{cards}</div>
    </div></section>"""
    s += credentials_block()
    s += intake_block()
    s += plans_block("Now the part that costs you nothing",
                     "Three formulas, from $119. The evaluation is free and takes about three minutes.", on_plum=True)
    s += """<section style="text-align:center"><div class="wrap">
      <a class="cta" href="#" data-start data-cta="footer">Check if I qualify &nbsp;&rarr;</a></div></section>"""
    s += standalone_capture() + sticky_and_js("f5") + footer()
    return s

if __name__ == "__main__":
    for name, fn in [("f1", f1), ("f2", f2), ("f3", f3), ("f4", f4), ("f5", f5)]:
        d = OUT/name; d.mkdir(parents=True, exist_ok=True)
        html = fn()
        (d/"index.html").write_text(html, encoding="utf-8")
        print(f"{name}: {len(html):,} bytes")
