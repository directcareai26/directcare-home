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

import {
  CARD_URL, PORTAL, AGENT_NAME, MAX_BODY,
  RESOURCES, DISCLAIMER,
  loadCatalog, buildReply,
} from '../lib/catalog.js';

// The catalogue, keyword aliases and reply builder moved to lib/catalog.js when
// the MCP server (api/mcp.js) became a second consumer. Two copies would drift
// the moment a program is added, and the endpoints would answer differently.

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
