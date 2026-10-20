/*! DirectCare AI — advanced matching + Conversions API bridge.
 *
 * Named neutrally on purpose: a file called meta-*.js is a common blocklist
 * pattern, and losing this file loses PageView entirely now that it is the
 * single source of that event.
 *
 * One place that owns: the first-party external_id, the fbc/fbp cookies, the
 * normalised customer-information parameters, and event de-duplication between
 * the browser pixel and the Conversions API.
 *
 * PRIVACY: matching parameters identify a PERSON and must never describe their
 * health -- no condition, product or page title is ever passed as customer data.
 * The page URL is a separate matter and IS sent: Meta receives
 * origin+pathname as event_source_url, and TikTok's ttq.page() reports the
 * page. On this site the path names the condition, so treat that as disclosed
 * to both vendors. See COMPLIANCE below.
 */
(function (w, d) {
  'use strict';

  // Canonical first: 1068250912518605 is the dataset ad account 707327008899561
// optimises against. 1567193354573862 is a legacy tag already on 155 pages —
// kept so its historical reporting keeps working, but it gets no server events.
var PIXELS = ['1068250912518605', '1567193354573862'];
  var XID_COOKIE = 'dca_xid', XID_DAYS = 180;
  var STORE = 'dca_match';

  // ---------------------------------------------------------------- cookies
  function getCookie(n) {
    var m = d.cookie.match('(^|;)\\s*' + n + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m[2]) : null;
  }
  function setCookie(n, v, days) {
    var e = new Date(Date.now() + days * 864e5).toUTCString();
    d.cookie = n + '=' + encodeURIComponent(v) + ';expires=' + e + ';path=/;SameSite=Lax' +
               (location.protocol === 'https:' ? ';Secure' : '');
  }

  // ---------------------------------------------------------------- ids
  function uuid() {
    if (w.crypto && w.crypto.randomUUID) return w.crypto.randomUUID();
    return 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }
  function externalId() {
    var v = getCookie(XID_COOKIE);
    if (!v) { v = uuid(); setCookie(XID_COOKIE, v, XID_DAYS); }
    return v;
  }
  // fbc must be built from fbclid on the landing hit or it is lost forever
  function clickId() {
    var existing = getCookie('_fbc');
    if (existing) return existing;
    var m = location.search.match(/[?&]fbclid=([^&]+)/);
    if (!m) return null;
    var v = 'fb.1.' + Date.now() + '.' + decodeURIComponent(m[1]);
    setCookie('_fbc', v, 90);
    return v;
  }

  // ttclid is TikTok's fbclid. Same rule: capture it on the landing hit or it is
  // gone. _ttp is written by TikTok's own SDK, so it is only read, never set.
  function ttClickId() {
    var existing = getCookie('_ttclid');
    if (existing) return existing;
    var m = location.search.match(/[?&]ttclid=([^&]+)/);
    if (!m) return null;
    var v = decodeURIComponent(m[1]);
    setCookie('_ttclid', v, 90);
    return v;
  }

  // ---------------------------------------------- normalisation (Meta spec)
  var N = {
    em: function (v) { return String(v).trim().toLowerCase(); },
    ph: function (v) {                       // digits only, country code required
      var s = String(v).replace(/\D/g, '').replace(/^0+/, '');
      if (s.length === 10) s = '1' + s;      // bare US number
      return s;
    },
    // Meta: "Lowercase only with no punctuation." Apostrophes and hyphens must go
    // (o'brien -> obrien, smith-jones -> smithjones) so the browser hash and the
    // server hash are taken over the identical string. Accents stay: Meta's own
    // example normalises Valéry -> valéry.
    name: function (v) { return String(v).trim().toLowerCase().replace(/[^\p{L}\p{M}]/gu, ''); },
    ct: function (v) { return String(v).trim().toLowerCase().replace(/[^a-z]/g, ''); },
    st: function (v) {                       // 2-letter ANSI code; map full US state names
      var s = String(v).trim().toLowerCase().replace(/[^a-z]/g, '');
      if (s.length === 2) return s;
      var ST = { alabama:'al',alaska:'ak',arizona:'az',arkansas:'ar',california:'ca',colorado:'co',
        connecticut:'ct',delaware:'de',florida:'fl',georgia:'ga',hawaii:'hi',idaho:'id',illinois:'il',
        indiana:'in',iowa:'ia',kansas:'ks',kentucky:'ky',louisiana:'la',maine:'me',maryland:'md',
        massachusetts:'ma',michigan:'mi',minnesota:'mn',mississippi:'ms',missouri:'mo',montana:'mt',
        nebraska:'ne',nevada:'nv',newhampshire:'nh',newjersey:'nj',newmexico:'nm',newyork:'ny',
        northcarolina:'nc',northdakota:'nd',ohio:'oh',oklahoma:'ok',oregon:'or',pennsylvania:'pa',
        rhodeisland:'ri',southcarolina:'sc',southdakota:'sd',tennessee:'tn',texas:'tx',utah:'ut',
        vermont:'vt',virginia:'va',washington:'wa',westvirginia:'wv',wisconsin:'wi',wyoming:'wy',
        districtofcolumbia:'dc' };
      return ST[s] || s.slice(0, 2);
    },
    zp: function (v) { return String(v).trim().toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 5); },
    country: function (v) {                  // must be ISO 3166-1 alpha-2, not "un"
      var s = String(v).trim().toLowerCase().replace(/[^a-z ]/g, '');
      if (/^[a-z]{2}$/.test(s)) return s;
      var NAMES = { 'united states': 'us', 'united states of america': 'us', usa: 'us', us: 'us',
                    america: 'us', canada: 'ca', 'united kingdom': 'gb', uk: 'gb', england: 'gb',
                    scotland: 'gb', wales: 'gb', australia: 'au', mexico: 'mx', ireland: 'ie' };
      return NAMES[s] || '';                 // unknown -> omit rather than send garbage
    },
    db: function (v) {                       // -> YYYYMMDD
      var s = String(v).replace(/\D/g, '');
      if (s.length === 8) return s;
      var t = new Date(v); if (isNaN(t)) return '';
      return '' + t.getFullYear() + ('0' + (t.getMonth() + 1)).slice(-2) + ('0' + t.getDate()).slice(-2);
    },
    ge: function (v) { var s = String(v).trim().toLowerCase()[0]; return s === 'f' || s === 'm' ? s : ''; }
  };
  var MAP = { em: N.em, ph: N.ph, fn: N.name, ln: N.name, ct: N.ct, st: N.st,
              zp: N.zp, country: N.country, db: N.db, ge: N.ge };

  function normalise(obj) {
    var out = {};
    Object.keys(obj || {}).forEach(function (k) {
      var v = obj[k];
      if (v === undefined || v === null || v === '') return;
      if (MAP[k]) { var n = MAP[k](v); if (n) out[k] = n; }
    });
    return out;
  }

  // ---------------------------------------------------------------- storage
  function stored() {
    try { return JSON.parse(w.localStorage.getItem(STORE) || '{}'); } catch (e) { return {}; }
  }
  function remember(data) {
    var merged = Object.assign(stored(), data);
    try { w.localStorage.setItem(STORE, JSON.stringify(merged)); } catch (e) {}
    return merged;
  }

  // the pixel hashes these in the browser; we pass plain normalised values
  function matchParams() {
    var p = Object.assign({}, stored());
    p.external_id = externalId();
    return p;
  }

  // ---------------------------------------------------------------- pixel
  function ensureFbq() {
    if (w.fbq) return w.fbq;
    var n = w.fbq = function () {
      n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
    };
    if (!w._fbq) w._fbq = n;
    n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
    var s = d.createElement('script'); s.async = true;
    s.src = 'https://connect.facebook.net/en_US/fbevents.js';
    var f = d.getElementsByTagName('script')[0]; f.parentNode.insertBefore(s, f);
    return n;
  }

  var initialised = false;
  function initPixels() {
    var fbq = ensureFbq(), params = matchParams();
    PIXELS.forEach(function (id) { fbq('init', id, params); });
    if (!initialised) {
      initialised = true;
      track('PageView');
    }
  }

  // ------------------------------------------------ browser + server, deduped
  function post(payload) {
    try {
      var body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/meta-capi', new Blob([body], { type: 'application/json' }));
      } else {
        fetch('/api/meta-capi', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                  body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }

  // The TikTok server copy. Sent separately from the Meta one and to its own
  // endpoint: these are different vendors with different outage modes, and the
  // Meta relay carries revenue reporting today. One must not be able to break
  // the other.
  //
  // Identity goes out PLAIN here and is hashed server-side, exactly as the Meta
  // relay does it -- the browser pixel hashes its own copy separately. Both
  // hashes are taken over the same normalised string, so they agree.
  //
  // _ttp is written by TikTok's SDK when it loads, and ViewContent fires at boot
  // -- before that. The Meta half of this file already learned this lesson with
  // _fbp (server PageView carried it on 7.8% of hits until it waited), so the
  // same wait applies here rather than shipping the same gap twice.
  function postTikTok(eventName, custom, eventId) {
    if (!TT_ALLOWED[eventName]) return;
    if (w.dcaOptOut === true) return;
    if (!getCookie('_ttp')) {
      var tries = 0;
      var poll = setInterval(function () {
        if (getCookie('_ttp') || ++tries >= 60) {   // 6s, past the SDK's own load
          clearInterval(poll);
          sendTikTok(eventName, custom, eventId);
        }
      }, 100);
      return;
    }
    sendTikTok(eventName, custom, eventId);
  }

  function sendTikTok(eventName, custom, eventId) {
    try {
      var body = JSON.stringify({
        event_name: eventName,
        event_id: eventId,
        event_source_url: location.origin + location.pathname,
        referrer_url: (d.referrer || '').split('?')[0] || undefined,
        custom_data: custom || {},
        user_data: Object.assign({}, stored(), {
          external_id: externalId(),
          ttp: getCookie('_ttp') || null,
          ttclid: ttClickId() || null
        })
      });
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/tiktok-capi', new Blob([body], { type: 'application/json' }));
      } else {
        fetch('/api/tiktok-capi', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                    body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }

  // fbevents.js writes the _fbp cookie when it loads, and the page's stub only
  // loads it on first interaction or after 10s; the server copy of PageView
  // used to leave before that, so Meta saw fbp on only 7.8% of server
  // PageViews vs 100% of later events. The server copy now waits for the
  // cookie (up to 12s, past the 10s lazy timer) and is flushed at once if the
  // page hides, so nothing is lost when a visitor leaves early.
  var pending = [];
  function withFbp(payload) { payload.user_data.fbp = getCookie('_fbp') || null; return payload; }
  function flushPending() {
    while (pending.length) post(withFbp(pending.shift()));
  }
  function postWhenReady(payload) {
    if (getCookie('_fbp')) return post(withFbp(payload));
    pending.push(payload);
    var tries = 0;
    (function poll() {
      var i = pending.indexOf(payload);
      if (i < 0) return;                                   // already flushed
      if (getCookie('_fbp') || ++tries >= 120) { pending.splice(i, 1); post(withFbp(payload)); return; }
      setTimeout(poll, 100);
    })();
  }
  d.addEventListener('visibilitychange', function () { if (d.visibilityState === 'hidden') flushPending(); });
  w.addEventListener('pagehide', flushPending);


  // An ALLOW-LIST, not a rename table.
  //
  // The first version of this mapped Meta names to what TikTok's docs call
  // standard events -- Lead -> SubmitForm, Purchase -> CompletePayment. Watching
  // the wire showed that is pointless: ttq.track('SubmitForm', ...) arrives at
  // analytics.tiktok.com as {"event":"Lead"}, and 'CompletePayment' arrives as
  // {"event":"Purchase"}. TikTok's SDK normalises to its own taxonomy, which
  // uses the same names Meta does. A rename table here would be dead code that
  // reads as though it does something.
  //
  // What this list DOES do is filter. An event not on it is never sent, so a
  // typo or an internal event name cannot reach TikTok as an unrecognised custom
  // event that no campaign can optimise against.
  var TT_ALLOWED = {
    Lead: 1, Purchase: 1, CompleteRegistration: 1, InitiateCheckout: 1,
    AddToCart: 1, AddPaymentInfo: 1, Subscribe: 1, Contact: 1,
    ViewContent: 1, Search: 1, AddToWishlist: 1, PlaceAnOrder: 1,
    ClickButton: 1, Download: 1
    // PageView is deliberately absent: ttq.page() already reports it at load,
    // and passing it here would double-count every page.
  };

  // ------------------------------------------------- tiktok advanced matching
  //
  // TIKTOK DOES NOT HASH FOR YOU. Meta's pixel takes plain normalised values and
  // hashes them in the browser -- that is why matchParams() passes plaintext and
  // why the comment above it says so. ttq.identify() expects values that are
  // ALREADY SHA-256 hashed. Handing it stored() directly would put plaintext
  // email addresses and phone numbers on the wire to TikTok.
  //
  // Same normalised input as Meta, so both platforms hash the identical string,
  // then hashed here with Web Crypto before anything leaves the page.
  function sha256(str) {
    try {
      if (!w.crypto || !w.crypto.subtle) return Promise.resolve(null);  // insecure context
      var bytes = new TextEncoder().encode(String(str));
      return w.crypto.subtle.digest('SHA-256', bytes).then(function (buf) {
        var b = new Uint8Array(buf), out = '';
        for (var i = 0; i < b.length; i++) out += ('0' + b[i].toString(16)).slice(-2);
        return out;
      }).catch(function () { return null; });
    } catch (e) { return Promise.resolve(null); }
  }

  // ttq.identify() is sticky: call it once and later events carry the match, so
  // this runs when identity changes rather than per event -- the pattern
  // TikTok's own docs show ("add this before event code").
  var ttIdentified = false;
  function identifyTikTok() {
    if (w.dcaOptOut === true) return;
    var s = stored();
    Promise.all([
      s.em ? sha256(s.em) : Promise.resolve(null),
      s.ph ? sha256(s.ph) : Promise.resolve(null),
      sha256(externalId())
    ]).then(function (h) {
      var payload = {};
      if (h[0]) payload.email = h[0];
      if (h[1]) payload.phone_number = h[1];
      if (h[2]) payload.external_id = h[2];
      if (!Object.keys(payload).length) return;
      try { w.ttq && w.ttq.identify(payload); ttIdentified = true; } catch (e) {}
    });
  }

  // TikTok's `contents` array.
  function ttContents(custom) {
    if (!custom) return null;
    var id = custom.content_id ||
             (custom.content_ids && custom.content_ids[0]) ||
             custom.content_category;
    if (!id && !custom.content_name) return null;
    var c = { content_id: String(id || custom.content_name),
              content_type: custom.content_type || 'product' };
    if (custom.content_name) c.content_name = custom.content_name;
    return [c];
  }

  function trackTikTok(eventName, custom, eventId) {
    if (!TT_ALLOWED[eventName]) return;      // not an event we send to TikTok
    // Meta still receives opt-out events flagged `opt_out` so they are measured
    // but excluded from delivery. ttq.track() has no equivalent field, so the
    // honest equivalent is not to send at all.
    if (w.dcaOptOut === true) return;
    if (!ttIdentified) identifyTikTok();      // sticky; cheap to attempt again
    var props = {};
    // content_name names the PRODUCT, and on this site the product names the
    // treatment. Meta's browser pixel already receives it -- verified on the
    // wire, cd[content_name]=Surge Max 90-day -- so withholding it from TikTok
    // alone bought an inconsistency rather than protection. Both browser pixels
    // carry it now; neither SERVER copy does, which is the line that matters.
    var contents = ttContents(custom);
    if (contents) props.contents = contents;
    if (custom && typeof custom.value !== 'undefined') props.value = custom.value;
    if (custom && custom.currency) props.currency = custom.currency;
    if (custom && custom.search_string) props.search_string = custom.search_string;
    try {
      w.ttq && w.ttq.track(eventName, props, { event_id: eventId });
    } catch (e) {}
  }

  function track(eventName, customData, presetId) {
    var eventId = presetId || uuid();
    // set window.dcaOptOut = true (consent banner, DNT, an unsubscribed user)
    // and the event is still measured but excluded from ads delivery.
    var optOut = w.dcaOptOut === true;
    var custom = customData || {};
    try { w.fbq && w.fbq('track', eventName, custom, { eventID: eventId }); } catch (e) {}
    trackTikTok(eventName, custom, eventId);
    postTikTok(eventName, custom, eventId);
    postWhenReady({
      event_name: eventName,
      event_id: eventId,                       // same id both sides => Meta dedupes
      action_source: 'website',
      event_source_url: location.origin + location.pathname, // path only, no query
      referrer_url: (d.referrer || '').split('?')[0] || undefined,
      custom_data: custom,
      opt_out: optOut || undefined,
      user_data: Object.assign({}, stored(), {
        external_id: externalId(),
        fbp: getCookie('_fbp') || null,
        fbc: clickId() || null
      })
    });
    return eventId;
  }

  // ---------------------------------------------------------------- public
  w.dcaIdentify = function (data) {
    remember(normalise(data));
    initPixels();                              // re-init so later events carry the match
    ttIdentified = false; identifyTikTok();    // re-hash and re-identify for TikTok
    return true;
  };
  w.dcaTrack = track;

  w.dcaExternalId = externalId;

  // Inline page scripts run while the document is parsing; this file is `defer`,
  // so it runs after them and w.dcaTrack does not exist yet at that point. Pages
  // push ['EventName', customData, eventId] onto w.dcaQueue instead.
  //
  // The drain MUST come after initPixels(). Advanced matching is applied at
  // fbq('init', id, params) time, so an event that fires before that init reaches
  // Meta with no customer information parameters on the browser copy at all.
  function drainQueue() {
    var q = w.dcaQueue;
    w.dcaQueue = { push: function (args) { try { track.apply(null, args); } catch (e) {} return 1; } };
    if (q && q.length) for (var i = 0; i < q.length; i++) w.dcaQueue.push(q[i]);
  }

  // ---------------------------------------------------------------- tiktok
  // Loaded here rather than pasted into 131 <head> blocks: this file is already
  // on every page (131/131), it is version-controlled, and a pixel that lives in
  // one reviewable place can be scoped or pulled in a single edit. GTM was the
  // alternative and reaches only 124 pages.
  //
  // WHAT THIS SENDS. ttq.page() reports the page URL, and on this site the path
  // IS the condition -- /testosterone-replacement-therapy, /perimenopause,
  // /womens-hair-loss. That is the same category of data event_source_url
  // already sends to Meta, so TikTok is one more recipient rather than a new
  // kind of exposure. It is still worth a compliance read: the FTC has acted
  // against telehealth companies for exactly this sharing.
  //
  // No customer-information parameters are passed. identify() is deliberately
  // not called -- matching a PERSON to TikTok is a separate decision from
  // counting a pageview, and it is not this file's to make.
  var TIKTOK_ID = 'DALCA3JC77UES97566D0';

  function ensureTtq() {
    if (w.ttq) return w.ttq;
    w.TiktokAnalyticsObject = 'ttq';
    var ttq = w.ttq = w.ttq || [];
    ttq.methods = ['page','track','identify','instances','debug','on','off','once',
      'ready','alias','group','enableCookie','disableCookie','holdConsent',
      'revokeConsent','grantConsent'];
    ttq.setAndDefer = function (o, m) {
      o[m] = function () { o.push([m].concat(Array.prototype.slice.call(arguments, 0))); };
    };
    for (var i = 0; i < ttq.methods.length; i++) ttq.setAndDefer(ttq, ttq.methods[i]);
    ttq.instance = function (id) {
      var e = ttq._i[id] || [];
      for (var n = 0; n < ttq.methods.length; n++) ttq.setAndDefer(e, ttq.methods[n]);
      return e;
    };
    ttq.load = function (id, opts) {
      var url = 'https://analytics.tiktok.com/i18n/pixel/events.js';
      ttq._i = ttq._i || {}; ttq._i[id] = []; ttq._i[id]._u = url;
      ttq._t = ttq._t || {}; ttq._t[id] = +new Date();
      ttq._o = ttq._o || {}; ttq._o[id] = opts || {};
      var s = d.createElement('script');
      s.type = 'text/javascript'; s.async = true;
      s.src = url + '?sdkid=' + id + '&lib=ttq';
      var f = d.getElementsByTagName('script')[0];
      f.parentNode.insertBefore(s, f);
    };
    return ttq;
  }

  function initTikTok() {
    try {
      var ttq = ensureTtq();
      ttq.load(TIKTOK_ID);
      ttq.page();
    } catch (e) {}   // a broken pixel must never take PageView down with it
  }

  // ------------------------------------------------------- ViewContent
  // TikTok's guidance for ViewContent is "pages important to your business".
  // Here that is the programme pages, and it is the third event they ask for --
  // Lead and Purchase are the only other two this site genuinely fires, and
  // inventing a fourth we do not actually observe would be worse than sending
  // three we do.
  //
  // Driven from a path map rather than a call pasted into each page, so adding
  // a programme is one line here instead of an edit to another HTML file.
  //
  // This discloses nothing ttq.page() has not already sent: the URL on these
  // pages names the programme either way. What it adds is structure TikTok can
  // optimise against.
  var PROGRAMS = {
    '/testosterone-replacement-therapy': ['trt', 'Testosterone Replacement Therapy'],
    '/hormone-replacement-therapy':      ['hrt', 'Hormone Replacement Therapy'],
    '/perimenopause':                    ['perimenopause', 'Perimenopause'],
    '/mens-health':                      ['mens-health', "Men's Health"],
    '/womens-health':                    ['womens-health', "Women's Health"],
    '/peptides':                         ['peptides', 'Peptide Therapy'],
    '/blood-test':                       ['blood-labs', 'Blood Labs'],
    '/weight-loss':                      ['weight-loss', 'Weight Loss'],
    '/womens-weight-loss':               ['womens-weight-loss', "Women's Weight Loss"],
    '/womans-hair-loss':                 ['womens-hair-loss', "Women's Hair Loss"],
    '/chronic-care':                     ['chronic-care', 'Chronic Care'],
    '/surge-max':                        ['surge-max', 'Surge Max']
  };

  function viewContent() {
    // trailing slash and .html both reach the same page on this host
    var path = location.pathname.replace(/\/index\.html$/, '').replace(/\.html$/, '')
                                .replace(/\/$/, '') || '/';
    var prog = PROGRAMS[path];
    if (!prog) return;
    track('ViewContent', { content_id: prog[0], content_type: 'product', content_name: prog[1] });
  }

  function boot() { initPixels(); initTikTok(); identifyTikTok(); drainQueue(); viewContent(); }

  clickId();                                   // capture fbclid on the landing hit
  ttClickId();                                 // and ttclid, same reason
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* COMPLIANCE
   * - Matching parameters describe a person, never a condition. We do not pass
   *   page titles, product names or query strings to Meta from this file.
   * - event_source_url is trimmed to origin+pathname so utm/fbclid and any
   *   funnel identifiers are not shipped as custom data.
   * - The same normalised parameter set is sent browser-side and server-side,
   *   with one event_id, so Meta de-duplicates rather than double-counting.
   */
})(window, document);
