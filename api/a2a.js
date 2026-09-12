// Vercel Serverless Function: the A2A (Agent2Agent) JSON-RPC endpoint behind
// the agent card at /.well-known/agent-card.json.
//
// Scope, on purpose: a read-only program directory. No LLM, no patient data,
// no intake, no orders. The single source of truth for program names, URLs
// and descriptions is /llms.txt — the same file humans and crawlers read — so
// a price or program change there is reflected here on the next request
// without touching this file.
//
// Speaks A2A v0.3 (method "message/send", parts carry kind:"text") and the
// v1.0 method names ("SendMessage", role ROLE_AGENT). Streaming, tasks and
// push notifications are declared unsupported in the card and answered with
// the A2A error codes rather than pretended.

const SITE = 'https://www.directcare.ai';
const LLMS_TXT = `${SITE}/llms.txt`;
const CARD_URL = `${SITE}/.well-known/agent-card.json`;
const PORTAL = 'https://directcareai.portal.tellescope.com/';
const AGENT_NAME = 'DirectCare AI Concierge';
const MAX_BODY = 64 * 1024;
const LLMS_TTL_MS = 10 * 60 * 1000;

// Keyword aliases keyed by the program page path as it appears in llms.txt.
const ALIASES = {
  '/testosterone-replacement-therapy': ['testosterone', 'trt', 'enclomiphene', 'low t', 'low-t', 'cypionate', 'undecanoate'],
  '/hormone-replacement-therapy': ['hrt', 'hormone replacement', 'menopause', 'perimenopause', 'estradiol', 'progesterone', 'hot flash', 'hot flashes', 'night sweats'],
  '/weight-loss': ['weight', 'glp', 'glp-1', 'glp1', 'semaglutide', 'tirzepatide', 'ozempic', 'wegovy', 'zepbound', 'mounjaro', 'obesity'],
  '/surge-max': ['erectile', 'ed', 'sildenafil', 'tadalafil', 'viagra', 'cialis', 'sexual', 'surge', 'libido', 'performance', 'pde5'],
  '/mens-hair-loss': ['hair', 'finasteride', 'minoxidil', 'dutasteride', 'balding', 'alopecia', 'thinning'],
  '/womans-hair-loss': ['hair', 'minoxidil', 'alopecia', 'thinning'],
  '/blood-test': ['lab', 'labs', 'blood', 'biomarker', 'biomarkers', 'panel', 'bloodwork'],
  '/supplements': ['supplement', 'supplements', 'vitamin', 'vitamins', 'magnesium', 'creatine', 'omega'],
};
const RESOURCE_WORDS = ['llms', 'sitemap', 'markdown', 'machine-readable', 'machine readable', 'json', 'rss', 'resources', 'feed'];

const RESOURCES = {
  llms_txt: LLMS_TXT,
  llms_full_txt: `${SITE}/llms-full.txt`,
  blog_posts_json: `${SITE}/blog/posts.json`,
  blog_rss: `${SITE}/blog/rss.xml`,
  sitemap: `${SITE}/sitemap.xml`,
  markdown_twins: `Any page path plus ".md", e.g. ${SITE}/blood-test.md`,
  content_usage_policy: `${SITE}/robots.txt`,
  agent_card: CARD_URL,
  patient_portal: PORTAL,
};

const DISCLAIMER =
  'Informational only, not medical advice. DirectCare AI serves people in the United States. ' +
  'Every protocol is reviewed by a US-licensed clinician and dosed against the person\'s own bloodwork. ' +
  'Compounded medications are not FDA-approved as finished products; their active ingredients are individually FDA-approved. ' +
  'If this is an emergency, call 911.';

// Used only if llms.txt cannot be fetched. Names and URLs only — no prices,
// no descriptions, so nothing here can go stale in a way that misleads.
const FALLBACK_PROGRAMS = [
  { name: 'Testosterone Replacement Therapy (TRT)', url: `${SITE}/testosterone-replacement-therapy` },
  { name: 'Hormone Replacement Therapy (HRT)', url: `${SITE}/hormone-replacement-therapy` },
  { name: 'Weight Loss (GLP-1)', url: `${SITE}/weight-loss/` },
  { name: 'Sexual Health (Surge Max)', url: `${SITE}/surge-max/` },
  { name: 'Hair Regrowth — Men', url: `${SITE}/mens-hair-loss/` },
  { name: 'Hair Regrowth — Women', url: `${SITE}/womans-hair-loss/` },
  { name: 'Blood Labs', url: `${SITE}/blood-test/` },
  { name: 'Supplements', url: `${SITE}/supplements/` },
];

// ---------------------------------------------------------------- llms.txt
let cache = { at: 0, data: null };

function parseLlms(txt) {
  const programs = [];
  let section = '';
  for (const line of txt.split('\n')) {
    const h = line.match(/^##\s+(.*)/);
    if (h) { section = h[1].trim(); continue; }
    const m = line.match(/^- \[([^\]]+)\]\((https?:\/\/[^)\s]+)\):\s*(.+)$/);
    if (m && /^products/i.test(section)) {
      programs.push({ name: m[1].trim(), url: m[2], description: m[3].trim() });
    }
  }
  const summary = (txt.match(/^>\s*(.+)$/m) || [])[1] || '';
  return { programs, summary };
}

async function loadCatalog() {
  const now = Date.now();
  if (cache.data && now - cache.at < LLMS_TTL_MS) return cache.data;
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 3000);
    const r = await fetch(LLMS_TXT, { signal: ctl.signal, headers: { 'user-agent': 'directcare-a2a/1.0' } });
    clearTimeout(t);
    if (!r.ok) throw new Error(`llms.txt HTTP ${r.status}`);
    const parsed = parseLlms(await r.text());
    if (parsed.programs.length === 0) throw new Error('llms.txt parsed to zero programs');
    cache = { at: now, data: { ...parsed, source: 'llms.txt' } };
    return cache.data;
  } catch (err) {
    if (cache.data) return cache.data; // stale beats empty
    return { programs: FALLBACK_PROGRAMS, summary: '', source: 'fallback' };
  }
}

// ---------------------------------------------------------------- matching
function pathOf(url) {
  try { return new URL(url).pathname.replace(/\/$/, ''); } catch (_) { return ''; }
}

function hasWord(text, phrase) {
  const esc = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(^|[^a-z0-9])${esc}([^a-z0-9]|$)`, 'i').test(text);
}

function matchPrograms(text, programs) {
  const q = (text || '').toLowerCase();
  if (!q.trim()) return { matched: programs, all: true };
  let hits = programs.filter((p) => (ALIASES[pathOf(p.url)] || []).some((a) => hasWord(q, a)));
  const women = /\b(women|woman|female|her|she)\b/.test(q);
  const men = /\b(men|man|male|him|he|his)\b/.test(q);
  if (women && !men) hits = hits.filter((p) => !/mens-hair-loss/.test(p.url));
  if (men && !women) hits = hits.filter((p) => !/womans-hair-loss/.test(p.url));
  return hits.length ? { matched: hits, all: false } : { matched: programs, all: true };
}

function wantsResources(text) {
  const q = (text || '').toLowerCase();
  return RESOURCE_WORDS.some((w) => hasWord(q, w));
}

// ---------------------------------------------------------------- reply
function buildReply(text, catalog) {
  const { matched, all } = matchPrograms(text, catalog.programs);
  const resources = wantsResources(text);
  const lines = [];
  lines.push(`${AGENT_NAME}${catalog.summary ? ' — ' + catalog.summary : ''}`);
  lines.push('');
  lines.push(all ? 'Programs:' : 'Programs that match your question:');
  for (const p of matched) {
    lines.push(`- ${p.name}${p.description ? ': ' + p.description : ''}`);
    lines.push(`  ${p.url}`);
  }
  lines.push('');
  lines.push('How to start: open the program page and complete the online intake. A US-licensed clinician reviews it before anything is prescribed.');
  lines.push(`Patient portal: ${PORTAL}`);
  if (resources || all) {
    lines.push('');
    lines.push('Machine-readable resources:');
    lines.push(`- llms.txt: ${RESOURCES.llms_txt}`);
    lines.push(`- llms-full.txt (whole site as Markdown): ${RESOURCES.llms_full_txt}`);
    lines.push(`- Blog posts manifest (JSON): ${RESOURCES.blog_posts_json}`);
    lines.push(`- Sitemap: ${RESOURCES.sitemap}`);
    lines.push(`- Markdown twin of any page: ${RESOURCES.markdown_twins}`);
  }
  lines.push('');
  lines.push(DISCLAIMER);
  return {
    text: lines.join('\n'),
    data: {
      agent: AGENT_NAME,
      programs: matched,
      resources: RESOURCES,
      how_to_start: 'Open the program page and complete the online intake; a US-licensed clinician reviews it.',
      disclaimer: DISCLAIMER,
      catalog_source: catalog.source,
    },
  };
}

function uuid() {
  return (globalThis.crypto && crypto.randomUUID) ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function userText(params) {
  const msg = params && params.message;
  const parts = (msg && Array.isArray(msg.parts)) ? msg.parts : [];
  return parts.map((p) => (p && typeof p.text === 'string') ? p.text : '').filter(Boolean).join('\n');
}

function messageV03(reply, params) {
  const inMsg = (params && params.message) || {};
  return {
    kind: 'message',
    role: 'agent',
    messageId: uuid(),
    contextId: inMsg.contextId || uuid(),
    parts: [
      { kind: 'text', text: reply.text },
      { kind: 'data', data: reply.data },
    ],
    metadata: { agent: AGENT_NAME, agentCard: CARD_URL },
  };
}

function messageV10(reply, params) {
  const inMsg = (params && params.message) || {};
  return {
    message: {
      role: 'ROLE_AGENT',
      messageId: uuid(),
      contextId: inMsg.contextId || uuid(),
      parts: [{ text: reply.text }],
      metadata: { agent: AGENT_NAME, agentCard: CARD_URL, directcare: reply.data },
    },
  };
}

// ---------------------------------------------------------------- JSON-RPC
const E = {
  PARSE: -32700, INVALID_REQUEST: -32600, METHOD_NOT_FOUND: -32601, INVALID_PARAMS: -32602, INTERNAL: -32603,
  TASK_NOT_FOUND: -32001, PUSH_UNSUPPORTED: -32003, UNSUPPORTED_OP: -32004, EXTENDED_CARD_NOT_CONFIGURED: -32007,
};
const err = (id, code, message) => ({ jsonrpc: '2.0', id: id === undefined ? null : id, error: { code, message } });
const ok = (id, result) => ({ jsonrpc: '2.0', id, result });

const SEND_V03 = new Set(['message/send']);
const SEND_V10 = new Set(['SendMessage']);
const STREAM = new Set(['message/stream', 'SendStreamingMessage', 'tasks/resubscribe', 'SubscribeToTask']);
const TASKS = new Set(['tasks/get', 'GetTask', 'tasks/cancel', 'CancelTask', 'tasks/list', 'ListTasks']);
const PUSH = new Set(['tasks/pushNotificationConfig/set', 'tasks/pushNotificationConfig/get', 'tasks/pushNotificationConfig/list', 'tasks/pushNotificationConfig/delete',
  'CreateTaskPushNotificationConfig', 'GetTaskPushNotificationConfig', 'ListTaskPushNotificationConfigs', 'DeleteTaskPushNotificationConfig']);
const EXTENDED = new Set(['agent/getAuthenticatedExtendedCard', 'agent/authenticatedExtendedCard', 'GetExtendedAgentCard']);

async function dispatch(rpc) {
  if (!rpc || typeof rpc !== 'object' || Array.isArray(rpc)) return err(null, E.INVALID_REQUEST, 'Expected a single JSON-RPC 2.0 request object');
  const { id, method, params } = rpc;
  if (rpc.jsonrpc !== '2.0' || typeof method !== 'string') return err(id, E.INVALID_REQUEST, 'jsonrpc must be "2.0" and method a string');
  if (SEND_V03.has(method) || SEND_V10.has(method)) {
    if (!params || typeof params !== 'object' || !params.message) return err(id, E.INVALID_PARAMS, 'params.message is required');
    const reply = buildReply(userText(params), await loadCatalog());
    return ok(id, SEND_V03.has(method) ? messageV03(reply, params) : messageV10(reply, params));
  }
  if (STREAM.has(method)) return err(id, E.UNSUPPORTED_OP, 'Streaming is not supported; use message/send');
  if (TASKS.has(method)) return err(id, E.TASK_NOT_FOUND, 'This agent replies with a Message and never creates Tasks');
  if (PUSH.has(method)) return err(id, E.PUSH_UNSUPPORTED, 'Push notifications are not supported');
  if (EXTENDED.has(method)) return err(id, E.EXTENDED_CARD_NOT_CONFIGURED, `No extended card; the public card is at ${CARD_URL}`);
  return err(id, E.METHOD_NOT_FOUND, `Unknown method: ${method}`);
}

// ---------------------------------------------------------------- handler
function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Max-Age', '86400');
}

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET' || req.method === 'HEAD') {
    res.setHeader('Cache-Control', 'public, max-age=300');
    return res.status(200).json({ agent: AGENT_NAME, agentCard: CARD_URL, protocol: 'A2A JSON-RPC 2.0 over HTTPS POST', send: 'message/send' });
  }
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'GET, POST, OPTIONS');
    return res.status(405).json(err(null, E.INVALID_REQUEST, 'Method not allowed'));
  }
  res.setHeader('Cache-Control', 'no-store');

  let body = req.body;
  if (typeof body === 'string' || Buffer.isBuffer(body)) {
    if (body.length > MAX_BODY) return res.status(413).json(err(null, E.INVALID_REQUEST, 'Request body too large'));
    try { body = JSON.parse(body.toString()); }
    catch (_) { return res.status(200).json(err(null, E.PARSE, 'Invalid JSON')); }
  }
  if (body === undefined || body === null) return res.status(200).json(err(null, E.PARSE, 'Empty body'));

  try {
    return res.status(200).json(await dispatch(body));
  } catch (_) {
    // Never echo request content into logs or the response — no PHI ever.
    return res.status(200).json(err(body && body.id, E.INTERNAL, 'Internal error'));
  }
}
