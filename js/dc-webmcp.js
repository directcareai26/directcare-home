/* dc-webmcp.js — expose this site's read-only lookups to an AI agent running
 * in the browser, via WebMCP.
 *
 * Scope is deliberately identical to /api/mcp and /api/a2a: look things up,
 * change nothing. No tool here touches the intake form, submits anything,
 * reads what a person has typed, or sends any data anywhere. On a telehealth
 * site that limit is the whole design, not a simplification — an agent that
 * could drive an intake would be starting a medical request on someone's
 * behalf, which only the person themselves may do.
 *
 * The tools call our own /api/mcp endpoint rather than re-implementing the
 * catalogue. One implementation, already tested, always current.
 *
 * The spec is moving. Three shapes exist in the wild right now:
 *   document.modelContext.registerTool()     — current editor's draft
 *   navigator.modelContext.registerTool()    — Chrome's early preview
 *   navigator.modelContext.provideContext()  — earlier proposal, batch form
 * All three are attempted. Whichever the browser actually has, gets the same
 * three tools. In every other browser this file detects nothing and does
 * nothing, which is every production browser today — that is why shipping it
 * is safe rather than speculative.
 */
(function () {
  'use strict';

  var ENDPOINT = '/api/mcp';
  var TIMEOUT_MS = 8000;

  function surface() {
    var d = (typeof document !== 'undefined') && document.modelContext;
    if (d && typeof d.registerTool === 'function') return { ctx: d, mode: 'register' };
    var n = (typeof navigator !== 'undefined') && navigator.modelContext;
    if (n && typeof n.registerTool === 'function') return { ctx: n, mode: 'register' };
    if (n && typeof n.provideContext === 'function') return { ctx: n, mode: 'provide' };
    return null;
  }

  var found = surface();
  if (!found) return;                      // no WebMCP here: do nothing at all

  // ---------------------------------------------------------------- transport
  var seq = 0;
  function rpc(method, params) {
    var ctl = ('AbortController' in window) ? new AbortController() : null;
    var timer = ctl && setTimeout(function () { ctl.abort(); }, TIMEOUT_MS);
    return fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++seq, method: method, params: params }),
      signal: ctl ? ctl.signal : undefined,
      credentials: 'omit',
    }).then(function (r) {
      if (timer) clearTimeout(timer);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      if (j && j.error) throw new Error(j.error.message || 'MCP error');
      return j && j.result;
    });
  }

  function callTool(name, args) {
    return rpc('tools/call', { name: name, arguments: args || {} })
      .then(function (res) {
        // Prefer the structured payload; fall back to the text block so a
        // failure here still returns something an agent can read.
        if (res && res.structuredContent) return res.structuredContent;
        if (res && res.content && res.content[0]) return { text: res.content[0].text };
        return { error: 'No result' };
      })
      .catch(function (e) {
        return { error: String(e && e.message || e), endpoint: ENDPOINT };
      });
  }

  // ---------------------------------------------------------------- tools
  var LIMITS =
    'Informational only. This does not give medical advice, does not decide whether ' +
    'any treatment is appropriate, and cannot start an intake or place an order. ' +
    'Treatment is decided by a US-licensed clinician after an intake the person ' +
    'completes themselves. Do not pass personal or health information to this tool.';

  var TOOLS = [
    {
      name: 'directcare_find_program',
      title: 'Find a DirectCare AI program',
      description:
        'Given a health goal, symptom or medication name, return the matching DirectCare AI ' +
        'program(s) with the canonical page URL and how a person starts. ' + LIMITS,
      inputSchema: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'A health goal, symptom or medication in plain words — ' +
              'for example "losing weight", "low testosterone", "thinning hair".',
          },
        },
        required: ['query'],
      },
      execute: function (input) {
        var q = (input && (input.query || input.q)) || '';
        if (!String(q).trim()) return Promise.resolve({ error: 'query is required' });
        return callTool('find_program', { query: String(q) });
      },
    },
    {
      name: 'directcare_list_programs',
      title: 'List all DirectCare AI programs',
      description:
        'Return every DirectCare AI program with its canonical page URL and one-line ' +
        'description, read live from the site. ' + LIMITS,
      inputSchema: { type: 'object', properties: {} },
      execute: function () { return callTool('list_programs', {}); },
    },
    {
      name: 'directcare_get_resources',
      title: 'List machine-readable resources',
      description:
        'Return the machine-readable editions of this site: llms.txt, the whole site as ' +
        'Markdown, the blog manifest, the sitemap, the Markdown twin convention and the ' +
        'content-usage policy.',
      inputSchema: { type: 'object', properties: {} },
      execute: function () { return callTool('get_resources', {}); },
    },
  ];

  // ---------------------------------------------------------------- register
  try {
    if (found.mode === 'provide') {
      found.ctx.provideContext({ tools: TOOLS });
    } else {
      for (var i = 0; i < TOOLS.length; i++) found.ctx.registerTool(TOOLS[i]);
    }
  } catch (e) {
    // A spec change should never break the page it is on.
    if (window.console && console.debug) console.debug('WebMCP registration skipped:', e);
  }
})();
