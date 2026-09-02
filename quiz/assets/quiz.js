/* DirectCare AI — quiz engine.
   Evaluates the branching + disqualification logic extracted from Tellescope,
   renders one question per screen, and submits to /api/quiz-submit (GHL).

   PRIVACY RULE: clinical answers never leave this page except in the POST to
   /api/quiz-submit. Nothing health-related is pushed to dataLayer or any pixel. */
(function () {
  "use strict";

  var cfg = null, answers = {}, stack = [], idx = 0, contact = {}, submitting = false;
  var phase = "intro";           // intro -> contact -> questions -> result
  var partialSent = false;
  var shownInter = {};

  // Reassurance beats, modelled on how Hims/Ro/Hers pace their intakes.
  // NOTE: no quote is attributed to a named clinician - these are general
  // statements about the process, not words put in a real person's mouth.
  function interstitials() {
    var mid = (cfg.images && cfg.images.mid) || "/optimized/dr-pepin-800.webp";
    return [
      { at: 0.22, img: "/optimized/clinician-n-computer-800.webp",
        title: "A clinician reads every answer",
        body: "Not an algorithm. A US-licensed clinician reviews your full intake before anything is prescribed." },
      { at: 0.55, img: mid,                       // funnel's own audience
        title: "You're over halfway",
        body: "The next questions cover your medical history. They're what let a clinician prescribe safely — and rule things out when they shouldn't." },
      { at: 0.85, img: "/optimized/dr-pepin-800.webp",
        title: "Almost there",
        body: "Once you submit, a clinician reviews everything and you'll hear back within one business day." }
    ];
  }
  var TRUST = ["HIPAA compliant", "US-licensed clinicians", "No video visit required", "Discreet shipping"];
  var root, elBar, elBack, elMain, elFoot, KEY;

  /* ---------- helpers ---------- */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  }
  function isBlank(v) {
    return v == null || v === "" || (Array.isArray(v) && v.length === 0) ||
      (typeof v === "object" && !Array.isArray(v) && !Object.keys(v).some(function (k) { return v[k]; }));
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ a: answers, c: contact, t: Date.now() })); }
    catch (e) {}
  }
  function restore() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return;
      var d = JSON.parse(raw);
      // drop anything older than 7 days
      if (!d || !d.t || Date.now() - d.t > 6048e5) { localStorage.removeItem(KEY); return; }
      answers = d.a || {}; contact = d.c || {};
    } catch (e) {}
  }

  /* ---------- condition evaluation ---------- */
  function calcAge() {
    var q = cfg.questions.filter(function (x) { return x.type === "date"; })[0];
    if (!q || !answers[q.id]) return null;
    var d = new Date(answers[q.id]);
    if (isNaN(d.getTime())) return null;
    var t = new Date(), a = t.getFullYear() - d.getFullYear();
    var m = t.getMonth() - d.getMonth();
    if (m < 0 || (m === 0 && t.getDate() < d.getDate())) a--;
    return a;
  }
  function resolve(field) {
    if (typeof field === "string" && field.indexOf("Calculated") === 0) return calcAge();
    return answers[field];
  }
  function cmp(a, op, b) {
    if (op === "eq") {
      if (Array.isArray(a)) return a.indexOf(b) !== -1;
      return String(a) === String(b);
    }
    if (op === "ne") {
      if (Array.isArray(a)) return a.indexOf(b) === -1;
      return String(a) !== String(b);
    }
    var x = parseFloat(a), y = parseFloat(b);
    if (isNaN(x) || isNaN(y)) return false;
    if (op === "gt") return x > y;
    if (op === "lt") return x < y;
    if (op === "gte") return x >= y;
    if (op === "lte") return x <= y;
    return false;
  }
  function evalCond(c) {
    if (!c) return true;
    if (c.all) return c.all.every(evalCond);
    if (c.any) return c.any.some(evalCond);
    if (c.field) {
      var v = resolve(c.field);
      if (v == null || v === "") return false;
      return cmp(v, c.op || "eq", c.value);
    }
    return true;
  }

  /* ---------- flow ---------- */
  function visible() {
    return cfg.questions.filter(function (q) {
      return !q.showWhen || evalCond(q.showWhen);
    });
  }
  // Tellescope encodes product selection as gated checkout fields; reuse that logic
  // to show the patient what their answers actually point to.
  function matchProducts() {
    var seen = {}, out = [];
    (cfg.products || []).forEach(function (p) {
      if (p.when && !evalCond(p.when)) return;
      if (seen[p.name]) return;
      seen[p.name] = 1;
      out.push({ name: p.name, price: (p.stripe && p.stripe.label) || null });
    });
    return out.slice(0, 4);
  }
  function productNames() {
    return matchProducts().map(function (p) { return p.name; });
  }
  function dqCheck() {
    var hard = false, flags = [];
    (cfg.dqRules || []).forEach(function (r) {
      if (evalCond(r.when)) {
        if (String(r.flag).toUpperCase() === "DQ") hard = true;
        else flags.push(r.flag);
      }
    });
    return { disqualified: hard, flags: flags };
  }

  /* ---------- rendering ---------- */
  function setProgress(p) { elBar.style.width = Math.max(2, Math.min(100, p * 100)) + "%"; }

  function renderQuestion(q, pos, total) {
    elMain.innerHTML = "";
    var w = el("div", "q-wrap");
    if (q.section) w.appendChild(el("p", "q-section", q.section));
    if (q.type !== "info") w.appendChild(el("p", "q-step", "Question " + pos + " of " + total));
    w.appendChild(el("h1", "q-title", q.title || ""));
    if (q.help) w.appendChild(el("p", "q-help", q.help));

    var current = answers[q.id];
    // Safety net: a screen with nothing to answer must never gate Continue,
    // or the user is stranded with a permanently disabled button.
    var answerable = q.type !== "info" &&
      !((q.type === "single" || q.type === "multi") && !(q.options || []).length);
    var valid = function () {
      if (!answerable) return true;
      return !q.required || !isBlank(answers[q.id]);
    };
    var refreshCta = function () { $(".q-cta").disabled = !valid(); };

    if (q.type === "single" || q.type === "multi") {
      var multi = q.type === "multi";
      var box = el("div", "q-opts");
      (q.options || []).forEach(function (opt) {
        var b = el("button", "q-opt");
        b.type = "button";
        b.setAttribute("role", multi ? "checkbox" : "radio");
        b.setAttribute("data-multi", multi ? "1" : "0");
        var chosen = multi ? (Array.isArray(current) && current.indexOf(opt) !== -1)
                           : current === opt;
        b.setAttribute("aria-checked", chosen ? "true" : "false");
        b.appendChild(el("span", "q-mark"));
        b.appendChild(el("span", "q-opt-label", opt));
        b.addEventListener("click", function () {
          if (multi) {
            var arr = Array.isArray(answers[q.id]) ? answers[q.id].slice() : [];
            var i = arr.indexOf(opt);
            // "none of these" style answers are exclusive
            var exclusive = /^(none|no,? i do not|none of these|none apply)/i.test(opt);
            if (i === -1) { arr = exclusive ? [opt] : arr.filter(function (o) {
              return !/^(none|no,? i do not|none of these|none apply)/i.test(o); }).concat([opt]); }
            else { arr.splice(i, 1); }
            answers[q.id] = arr;
            Array.prototype.forEach.call(box.children, function (c) {
              var lbl = $(".q-opt-label", c).textContent;
              c.setAttribute("aria-checked", arr.indexOf(lbl) !== -1 ? "true" : "false");
            });
            save(); refreshCta();
          } else {
            answers[q.id] = opt;
            Array.prototype.forEach.call(box.children, function (c) {
              c.setAttribute("aria-checked", c === b ? "true" : "false");
            });
            save();
            setTimeout(next, 190); // auto-advance on single-select
          }
        });
        box.appendChild(b);
      });
      w.appendChild(box);
    } else if (q.type === "info") {
      // nothing extra; continue button only
    } else if (q.type === "address") {
      var g = el("div", "q-grid");
      var parts = [["line1", "Street address", 1], ["city", "City", 0],
                   ["state", "State", 0], ["zip", "ZIP", 0]];
      var cur = (current && typeof current === "object") ? current : {};
      parts.forEach(function (p) {
        var i = el("input", "q-field" + (p[2] ? " q-span" : ""));
        i.type = "text"; i.placeholder = p[1]; i.value = cur[p[0]] || "";
        i.addEventListener("input", function () {
          var o = (answers[q.id] && typeof answers[q.id] === "object") ? answers[q.id] : {};
          o[p[0]] = i.value; answers[q.id] = o; save(); refreshCta();
        });
        g.appendChild(i);
      });
      w.appendChild(g);
    } else {
      var input;
      if (q.type === "longtext") { input = el("textarea", "q-field"); }
      else {
        input = el("input", "q-field");
        input.type = q.type === "date" ? "date" : q.type === "phone" ? "tel"
                   : q.type === "email" ? "email" : q.type === "number" ? "number" : "text";
      }
      input.value = current || "";
      if (q.type === "longtext") input.placeholder = "Start typing…";
      input.addEventListener("input", function () {
        answers[q.id] = input.value; save(); refreshCta();
      });
      w.appendChild(input);
    }
    elMain.appendChild(w);

    elFoot.innerHTML = "";
    var fi = el("div", "q-foot-in");
    var cta = el("button", "q-cta", q.type === "info" ? "Continue" : "Continue");
    cta.type = "button";
    cta.addEventListener("click", next);
    fi.appendChild(cta);
    elFoot.appendChild(fi);
    cta.disabled = !valid();
    elBack.hidden = idx === 0;
    window.scrollTo(0, 0);
  }

  function renderIntro() {
    elMain.innerHTML = ""; elFoot.innerHTML = "";
    elBack.hidden = true;
    elBar.style.width = "0%";
    var w = el("div", "q-wrap");
    var hero = el("img", "q-hero");
    hero.src = (cfg.images && cfg.images.hero) || "/optimized/virtual-clinician-consult-1200.webp";
    hero.alt = ""; hero.setAttribute("aria-hidden", "true");
    hero.loading = "eager";
    w.appendChild(hero);
    w.appendChild(el("h1", "q-title", cfg.intro || ("Let's find the right " + cfg.title + " treatment for you")));
    w.appendChild(el("p", "q-help",
      "A few questions about your health and history. It takes about 3 minutes, and a licensed clinician reviews every answer before anything is prescribed."));
    var ul = el("ul", "q-trust");
    TRUST.forEach(function (t) { ul.appendChild(el("li", null, t)); });
    w.appendChild(ul);
    elMain.appendChild(w);
    var fi = el("div", "q-foot-in");
    var cta = el("button", "q-cta", "Get started");
    cta.type = "button";
    cta.addEventListener("click", function () { phase = "contact"; render(); });
    fi.appendChild(cta);
    fi.appendChild(el("p", "q-legal",
      "Your answers are private and shared only with your care team."));
    elFoot.appendChild(fi);
    window.scrollTo(0, 0);
  }

  function renderContact() {
    elMain.innerHTML = "";
    var w = el("div", "q-wrap");
    w.appendChild(el("p", "q-step", "First, the basics"));
    w.appendChild(el("h1", "q-title", "Where should your care team reach you?"));
    w.appendChild(el("p", "q-help", "We ask up front so a clinician can follow up even if you don't finish today."));
    var g = el("div", "q-grid");
    var fields = [["firstName", "First name", "text", 0], ["lastName", "Last name", "text", 0],
                  ["email", "Email address", "email", 1], ["phone", "Mobile number", "tel", 1]];
    fields.forEach(function (f) {
      var i = el("input", "q-field" + (f[3] ? " q-span" : ""));
      i.type = f[2]; i.placeholder = f[1]; i.value = contact[f[0]] || "";
      i.autocomplete = f[0] === "firstName" ? "given-name" : f[0] === "lastName" ? "family-name"
                     : f[0] === "email" ? "email" : "tel";
      i.addEventListener("input", function () {
        contact[f[0]] = i.value.trim(); save();
        $(".q-cta").disabled = !contactValid();
      });
      g.appendChild(i);
    });
    w.appendChild(g);
    clinCard(w, "Reviewed by a US-licensed clinician",
      "Your answers go to a clinician, not an automated system.");
    w.appendChild(el("p", "q-legal",
      "By continuing you agree to our Telehealth Consent, Terms of Service and Privacy Policy. Message and data rates may apply."));
    elMain.appendChild(w);

    elFoot.innerHTML = "";
    var fi = el("div", "q-foot-in");
    var cta = el("button", "q-cta", "Continue");
    cta.type = "button";
    cta.addEventListener("click", function () {
      sendPartial();                 // capture the lead before any clinical questions
      phase = "questions"; idx = 0; stack = [];
      render();
    });
    fi.appendChild(cta);
    elFoot.appendChild(fi);
    cta.disabled = !contactValid();
    elBack.hidden = false;
    elBar.style.width = "3%";
    window.scrollTo(0, 0);
  }
  function clinCard(parent, title, sub, img) {
    var c = el("div", "q-clin");
    var i = el("img");
    i.src = img || "/optimized/dr-pepin-400.webp";
    i.alt = ""; i.setAttribute("aria-hidden", "true"); i.loading = "lazy";
    c.appendChild(i);
    var b = el("div");
    b.appendChild(el("p", "q-clin-t", title));
    b.appendChild(el("p", "q-clin-s", sub));
    c.appendChild(b);
    parent.appendChild(c);
    return c;
  }
  function contactValid() {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(contact.email || "") &&
           (contact.phone || "").replace(/\D/g, "").length >= 10 &&
           (contact.firstName || "").length > 0;
  }

  function renderInterstitial(item) {
    elMain.innerHTML = ""; elFoot.innerHTML = "";
    var w = el("div", "q-wrap q-inter");
    if (item.img) {
      var im = el("img");
      im.src = item.img; im.alt = ""; im.setAttribute("aria-hidden", "true");
      im.loading = "lazy";
      w.appendChild(im);
    } else {
      w.appendChild(el("div", "q-tick"));
    }
    w.appendChild(el("h1", "q-title", item.title));
    w.appendChild(el("p", "q-help", item.body));
    elMain.appendChild(w);
    var fi = el("div", "q-foot-in");
    var cta = el("button", "q-cta", "Continue");
    cta.type = "button";
    cta.addEventListener("click", function () { render(); });
    fi.appendChild(cta);
    elFoot.appendChild(fi);
    elBack.hidden = false;
    window.scrollTo(0, 0);
  }
  function pendingInterstitial(pct) {
    var list = interstitials();
    for (var i = 0; i < list.length; i++) {
      var it = list[i];
      if (!shownInter[i] && pct >= it.at) { shownInter[i] = 1; return it; }
    }
    return null;
  }
  function renderLoading() {
    elFoot.innerHTML = "";
    elBack.hidden = true;
    elMain.innerHTML = "";
    var w = el("div", "q-wrap q-center");
    w.appendChild(el("div", "q-spin"));
    w.appendChild(el("h1", "q-title", "Reviewing your answers…"));
    w.appendChild(el("p", "q-help", "This takes a moment."));
    elMain.appendChild(w);
    setProgress(1);
  }

  function renderResult(dq) {
    try { localStorage.removeItem(KEY); } catch (e) {}
    elMain.innerHTML = "";
    elBack.hidden = true;
    var w = el("div", "q-wrap");
    if (dq.disqualified) {
      w.appendChild(el("p", "q-eyebrow warn", "We can't prescribe this online"));
      w.appendChild(el("h1", "q-title", "Your answers need a conversation, not a form"));
      w.appendChild(el("p", "q-help",
        "Something you told us means an online-only visit isn't the right or safe path for this treatment. That's not a rejection — it's the system working the way it should."));
      var c = el("div", "q-card");
      c.appendChild(el("h3", null, "What you can do next"));
      var ul = el("ul");
      ["Book a telehealth visit with a DirectCare AI clinician",
       "Speak with your primary care provider about these symptoms",
       "Explore our blood testing panel to understand the underlying cause"
      ].forEach(function (t) { ul.appendChild(el("li", null, t)); });
      c.appendChild(ul);
      w.appendChild(c);
      w.appendChild(el("p", "q-alert",
        "If you're experiencing chest pain, fainting, or a medical emergency, seek emergency care now."));
      elMain.appendChild(w);
      cta("Book a visit instead", "/about");
    } else {
      w.appendChild(el("p", "q-eyebrow ok", "Your results"));
      w.appendChild(el("h1", "q-title", "You may be a good candidate for treatment"));
      var matches = matchProducts();
      var b = el("div", "q-card brand");
      b.appendChild(el("p", "q-eyebrow", matches.length > 1 ? "Options for review" : "Suggested for review"));
      if (matches.length) {
        b.appendChild(el("h3", null, matches[0].name));
        if (matches[0].price) b.appendChild(el("p", "q-price", "From " + matches[0].price));
        if (matches.length > 1) {
          var ul = el("ul");
          matches.slice(1).forEach(function (m) {
            ul.appendChild(el("li", null, m.name + (m.price ? " — from " + m.price : "")));
          });
          b.appendChild(ul);
        }
      } else {
        b.appendChild(el("h3", null, cfg.product));
      }
      b.appendChild(el("p", null,
        "Matched to what you told us about your symptoms, history and current medications."));
      w.appendChild(b);
      w.appendChild(el("p", "q-help",
        "This is not a prescription. A licensed clinician reviews your intake and decides what — if anything — is appropriate for you. You'll hear back within one business day."));
      clinCard(w, "Next: clinician review",
        "A US-licensed clinician reviews your full intake before anything is prescribed.");
      elMain.appendChild(w);
      cta("Done", "/thankyou?p=" + encodeURIComponent(cfg.slug));
    }
    window.scrollTo(0, 0);
    function cta(label, href) {
      elFoot.innerHTML = "";
      var fi = el("div", "q-foot-in");
      var a = el("a", "q-cta", label);
      a.href = href; a.style.display = "block"; a.style.textAlign = "center";
      a.style.textDecoration = "none";
      fi.appendChild(a); elFoot.appendChild(fi);
    }
  }

  /* ---------- navigation ---------- */
  function next() {
    var vis = visible();
    var q = vis[idx];
    if (q && q.required && isBlank(answers[q.id])) return;
    stack.push(idx);
    // a hard DQ can trigger mid-quiz — stop asking clinical questions
    if (dqCheck().disqualified) return finish();
    idx++;
    render();
  }
  function back() {
    if (phase === "contact") { phase = "intro"; return render(); }
    if (phase === "questions" && idx === 0 && !stack.length) {
      phase = "contact"; return render();
    }
    if (stack.length) { idx = stack.pop(); }
    else if (idx > 0) { idx--; }
    render();
  }
  function render() {
    if (phase === "intro") return renderIntro();
    if (phase === "contact") return renderContact();
    var vis = visible();
    if (idx >= vis.length) return finish();     // all questions answered -> submit
    setProgress((idx + 1) / (vis.length + 1));
    var inter = pendingInterstitial(idx / vis.length);
    if (inter) return renderInterstitial(inter);
    renderQuestion(vis[idx], idx + 1, vis.length);
  }

  /* ---------- submit ---------- */
  function payload(partial) {
    var dq = dqCheck();
    var out = { funnel: cfg.slug, formId: cfg.formId, partial: !!partial,
                contact: contact, outcome: dq, products: productNames(),
                answers: [], meta: {} };
    cfg.questions.forEach(function (q) {
      var v = answers[q.id];
      if (isBlank(v)) return;
      if (typeof v === "object" && !Array.isArray(v)) {
        v = [v.line1, v.city, v.state, v.zip].filter(Boolean).join(", ");
      }
      out.answers.push({ id: q.id, title: q.title, type: q.type,
                         value: Array.isArray(v) ? v : String(v) });
    });
    try {
      var p = new URLSearchParams(location.search);
      ["utm_source","utm_medium","utm_campaign","utm_content","utm_term","gclid","fbclid"]
        .forEach(function (k) { if (p.get(k)) out.meta[k] = p.get(k); });
      out.meta.page = location.pathname;
    } catch (e) {}
    return out;
  }
  function sendPartial() {
    if (partialSent) return;
    partialSent = true;
    try {
      fetch("/api/quiz-submit", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload(true)), keepalive: true
      }).catch(function () {});
    } catch (e) {}
  }
  function finish() {
    if (submitting) return;
    submitting = true;
    renderLoading();
    var body = payload(false);
    fetch("/api/quiz-submit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json().catch(function () { return {}; }); })
      .catch(function () { return {}; })
      .then(function () {
        // Conversion signal only — never any clinical answer.
        try {
          window.dataLayer = window.dataLayer || [];
          window.dataLayer.push({ event: "quiz_complete", quiz_funnel: cfg.slug,
                                  quiz_outcome: body.outcome.disqualified ? "not_eligible" : "eligible" });
        } catch (e) {}
        submitting = false;
        renderResult(body.outcome);
      });
  }

  /* ---------- boot ---------- */
  function boot() {
    root = $("[data-quiz]");
    if (!root) return;
    var slug = root.getAttribute("data-quiz");
    KEY = "dca_quiz_" + slug;
    root.innerHTML =
      '<div class="q-shell">' +
        '<div class="q-top">' +
          '<a class="q-logo" href="/" aria-label="DirectCare AI home">' +
            '<img src="/quiz/assets/dca-logo.png" alt="DirectCare AI" width="600" height="150" />' +
          '</a>' +
          '<div class="q-top-in">' +
            '<button class="q-back" type="button" aria-label="Go back">&#8592;</button>' +
            '<div class="q-bar"><i></i></div>' +
          '</div>' +
        '</div>' +
        '<div class="q-main"></div>' +
        '<div class="q-foot"></div>' +
      '</div>';
    elBar = $(".q-bar > i", root);
    elBack = $(".q-back", root);
    elMain = $(".q-main", root);
    elFoot = $(".q-foot", root);
    elBack.addEventListener("click", back);
    document.body.classList.add("dca-quiz");
    restore();
    fetch("/quiz/config/" + slug + ".json")
      .then(function (r) { return r.json(); })
      .then(function (c) {
        cfg = c;
        if (contactValid() && Object.keys(answers).length) { phase = "questions"; partialSent = true; }
        render();
      })
      .catch(function () {
        elMain.innerHTML = '<div class="q-wrap"><h1 class="q-title">' +
          'We couldn\'t load this questionnaire</h1><p class="q-help">' +
          'Please refresh, or contact us and we\'ll help you get started.</p></div>';
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
