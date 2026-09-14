// Shared program catalogue for every agent-facing endpoint on this site.
//
// The single source of truth for program names, URLs and descriptions is
// /llms.txt — the same file humans and crawlers read — so a program or price
// change there reaches every endpoint on the next request without a deploy.
//
// This module exists because there is now more than one consumer: the A2A
// JSON-RPC endpoint (api/a2a.js) and the MCP server (api/mcp.js). Keeping the
// keyword aliases and matching in one place is the point — two copies would
// drift the moment a program is added, and the two endpoints would then answer
// the same question differently.
//
// Read-only by construction. No LLM, no patient data, no intake, no orders.

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
  'Every protocol is reviewed by a US-licensed clinician, who decides whether treatment is appropriate. Programs that use bloodwork dose against the person\'s own labs. ' +
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
  lines.push('How to start: open the program page and complete the online intake. A US-licensed clinician reviews it and decides whether any treatment is appropriate.');
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
      how_to_start: 'Open the program page and complete the online intake; a US-licensed clinician reviews it and decides whether any treatment is appropriate.',
      disclaimer: DISCLAIMER,
      catalog_source: catalog.source,
    },
  };
}

export {
  SITE, LLMS_TXT, CARD_URL, PORTAL, AGENT_NAME, LLMS_TTL_MS, MAX_BODY,
  ALIASES, RESOURCE_WORDS, RESOURCES, DISCLAIMER, FALLBACK_PROGRAMS,
  parseLlms, loadCatalog, pathOf, hasWord, matchPrograms, wantsResources, buildReply,
};
