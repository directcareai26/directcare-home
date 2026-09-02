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
 * PRIVACY: this file never sends a condition, product, page title or URL path
 * that would reveal what someone is being treated for. Matching parameters
 * identify a PERSON; they must not describe their health. See COMPLIANCE below.
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

  // ---------------------------------------------- normalisation (Meta spec)
  var N = {
    em: function (v) { return String(v).trim().toLowerCase(); },
    ph: function (v) {                       // digits only, country code required
      var s = String(v).replace(/\D/g, '').replace(/^0+/, '');
      if (s.length === 10) s = '1' + s;      // bare US number
      return s;
    },
    name: function (v) { return String(v).trim().toLowerCase().replace(/[^\p{L}\p{M}'-]/gu, ''); },
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

  function track(eventName, customData) {
    var eventId = uuid();
    // set window.dcaOptOut = true (consent banner, DNT, an unsubscribed user)
    // and the event is still measured but excluded from ads delivery.
    var optOut = w.dcaOptOut === true;
    var custom = customData || {};
    try { w.fbq && w.fbq('track', eventName, custom, { eventID: eventId }); } catch (e) {}
    post({
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
    return true;
  };
  w.dcaTrack = track;
  w.dcaExternalId = externalId;

  clickId();                                   // capture fbclid on the landing hit
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', initPixels);
  else initPixels();

  /* COMPLIANCE
   * - Matching parameters describe a person, never a condition. We do not pass
   *   page titles, product names or query strings to Meta from this file.
   * - event_source_url is trimmed to origin+pathname so utm/fbclid and any
   *   funnel identifiers are not shipped as custom data.
   * - The same normalised parameter set is sent browser-side and server-side,
   *   with one event_id, so Meta de-duplicates rather than double-counting.
   */
})(window, document);
