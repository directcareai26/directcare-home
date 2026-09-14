// Vercel Serverless Function: the MCP (Model Context Protocol) endpoint
// described by /.well-known/mcp/server-card.json.
//
// Same scope as the A2A endpoint next door, and deliberately so: a read-only
// program directory. No LLM, no patient data, no intake, no orders, no auth —
// there is nothing here that needs protecting, which is why this site
// publishes no OAuth metadata.
//
// Both endpoints share lib/catalog.js, so the program list and the keyword
// matching cannot drift apart. Adding a program to /llms.txt updates both.
//
// Transport is Streamable HTTP: a single POST carrying one JSON-RPC 2.0
// request, answered with one JSON response. No SSE, no sessions, no
// server-initiated messages — none of which this server needs, and all of
// which are declared absent rather than stubbed.

import {
  SITE, PORTAL, MAX_BODY, RESOURCES, DISCLAIMER,
  loadCatalog, matchPrograms,
} from '../lib/catalog.js';

const SERVER_NAME = 'directcare-ai';
const SERVER_VERSION = '1.0.0';
const CARD_URL = `${SITE}/.well-known/mcp/server-card.json`;
// Newest spec revision this server implements. If a client asks for an older
// one we echo theirs back, which is what the spec asks for.
const PROTOCOL_VERSION = '2025-06-18';
const SUPPORTED = new Set(['2025-06-18', '2025-03-26', '2024-11-05']);

const HOW_TO_START =
  'Open the program page and complete the online intake. A US-licensed ' +
  'clinician reviews it and decides whether any treatment is appropriate.';

// ---------------------------------------------------------------- tools
const TOOLS = [
  {
    name: 'find_program',
    title: 'Find a DirectCare AI program',
    description:
      'Given a health goal, symptom or medication name, return the matching DirectCare AI ' +
      'program(s) with the canonical page URL and how a person starts. Informational only: ' +
      'this does not give medical advice, does not decide whether a treatment is appropriate, ' +
      'and cannot start an intake or place an order. Do not send personal or health ' +
      'information; it is not needed and not stored.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            'A health goal, symptom or medication in plain words — for example ' +
            '"losing weight", "low testosterone", "thinning hair", "semaglutide".',
        },
      },
      required: ['query'],
      additionalProperties: false,
    },
  },
  {
    name: 'list_programs',
    title: 'List all DirectCare AI programs',
    description:
      'Return every DirectCare AI program with its canonical page URL and one-line ' +
      'description, read live from the site\'s own llms.txt. Informational only.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_resources',
    title: 'List machine-readable resources',
    description:
      'Return the machine-readable editions of www.directcare.ai — llms.txt, the whole ' +
      'site as Markdown, the blog manifest, the sitemap, the Markdown twin convention, ' +
      'and the content-usage policy.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
];

function programPayload(programs, catalog) {
  return {
    programs: programs.map((p) => ({
      name: p.name,
      url: p.url,
      ...(p.description ? { description: p.description } : {}),
    })),
    how_to_start: HOW_TO_START,
    patient_portal: PORTAL,
    catalog_source: catalog.source,
    disclaimer: DISCLAIMER,
  };
}

// Every tool answers with BOTH a human-readable text block and structured
// content. Clients that only render text still show the disclaimer.
function toolResult(text, data) {
  return {
    content: [{ type: 'text', text }],
    structuredContent: data,
    isError: false,
  };
}

async function callTool(name, args) {
  const catalog = await loadCatalog();

  if (name === 'list_programs' || name === 'find_program') {
    const query = name === 'find_program' ? String((args && args.query) || '') : '';
    if (name === 'find_program' && !query.trim()) {
      return { content: [{ type: 'text', text: 'query is required.' }], isError: true };
    }
    const { matched, all } = matchPrograms(query, catalog.programs);
    const lines = [];
    lines.push(all && query.trim()
      ? 'No program matched that specifically, so here is the full list:'
      : (all ? 'DirectCare AI programs:' : 'Programs that match:'));
    for (const p of matched) {
      lines.push(`- ${p.name}${p.description ? ': ' + p.description : ''}`);
      lines.push(`  ${p.url}`);
    }
    lines.push('', HOW_TO_START, '', DISCLAIMER);
    return toolResult(lines.join('\n'), programPayload(matched, catalog));
  }

  if (name === 'get_resources') {
    const lines = ['Machine-readable editions of www.directcare.ai:'];
    for (const [k, v] of Object.entries(RESOURCES)) lines.push(`- ${k}: ${v}`);
    lines.push('', DISCLAIMER);
    return toolResult(lines.join('\n'), { resources: RESOURCES, disclaimer: DISCLAIMER });
  }

  return { content: [{ type: 'text', text: `Unknown tool: ${name}` }], isError: true };
}

// ---------------------------------------------------------------- JSON-RPC
const E = { PARSE: -32700, INVALID_REQUEST: -32600, METHOD_NOT_FOUND: -32601, INVALID_PARAMS: -32602, INTERNAL: -32603 };
const err = (id, code, message) => ({ jsonrpc: '2.0', id: id === undefined ? null : id, error: { code, message } });
const ok = (id, result) => ({ jsonrpc: '2.0', id, result });

async function dispatch(rpc) {
  if (!rpc || typeof rpc !== 'object' || Array.isArray(rpc)) {
    return err(null, E.INVALID_REQUEST, 'Expected a single JSON-RPC 2.0 request object');
  }
  const { id, method, params } = rpc;
  if (rpc.jsonrpc !== '2.0' || typeof method !== 'string') {
    return err(id, E.INVALID_REQUEST, 'jsonrpc must be "2.0" and method a string');
  }

  switch (method) {
    case 'initialize': {
      const asked = params && params.protocolVersion;
      return ok(id, {
        protocolVersion: SUPPORTED.has(asked) ? asked : PROTOCOL_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: SERVER_NAME, title: 'DirectCare AI', version: SERVER_VERSION },
        instructions:
          'Read-only directory for DirectCare AI, a US-only direct-to-patient telehealth ' +
          'service. Use find_program to map a health goal to a program, list_programs for ' +
          'the full catalogue, get_resources for the machine-readable editions of the site. ' +
          'This server gives no medical advice and holds no patient records. Treatment is ' +
          'decided by a US-licensed clinician after an intake the person completes ' +
          'themselves. Do not send personal or health information to these tools.',
      });
    }
    // Notifications carry no id and must not be answered with a result.
    case 'notifications/initialized':
    case 'notifications/cancelled':
      return null;
    case 'ping':
      return ok(id, {});
    case 'tools/list':
      return ok(id, { tools: TOOLS });
    case 'tools/call': {
      const name = params && params.name;
      if (!name || typeof name !== 'string') return err(id, E.INVALID_PARAMS, 'params.name is required');
      if (!TOOLS.some((t) => t.name === name)) return err(id, E.INVALID_PARAMS, `Unknown tool: ${name}`);
      return ok(id, await callTool(name, (params && params.arguments) || {}));
    }
    // Declared absent in the capabilities above rather than stubbed.
    case 'resources/list':
    case 'resources/templates/list':
    case 'prompts/list':
      return err(id, E.METHOD_NOT_FOUND, `${method} is not supported; this server exposes tools only`);
    default:
      return err(id, E.METHOD_NOT_FOUND, `Unknown method: ${method}`);
  }
}

// ---------------------------------------------------------------- handler
function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version');
  res.setHeader('Access-Control-Expose-Headers', 'Mcp-Session-Id');
  res.setHeader('Access-Control-Max-Age', '86400');
}

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();

  if (req.method === 'GET' || req.method === 'HEAD') {
    // A GET on an MCP endpoint is the client opening an SSE stream. This
    // server has nothing to push, so 405 is the correct answer, not an empty
    // stream a client would sit and wait on.
    res.setHeader('Cache-Control', 'public, max-age=300');
    res.setHeader('Allow', 'POST, OPTIONS');
    return res.status(405).json(err(null, E.INVALID_REQUEST,
      `This MCP server is POST-only (Streamable HTTP, no SSE). Server card: ${CARD_URL}`));
  }

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST, OPTIONS');
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
    const out = await dispatch(body);
    // A notification gets 202 with no body, per the Streamable HTTP spec.
    if (out === null) return res.status(202).end();
    return res.status(200).json(out);
  } catch (_) {
    // Never echo request content into logs or the response — no PHI ever.
    return res.status(200).json(err(body && body.id, E.INTERNAL, 'Internal error'));
  }
}

export { dispatch, TOOLS };
