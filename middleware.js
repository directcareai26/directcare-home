// Vercel Edge Middleware for directcare.ai.
//
//  1. Markdown content negotiation. A request whose Accept header prefers
//     text/markdown over text/html is rewritten to the page's Markdown twin —
//     the same file the `Link: rel="alternate"` header advertises — so an agent
//     gets Markdown without guessing URLs. Browsers never ask for markdown, so
//     human traffic never takes this branch.
//  2. Geo gate. US visitors and search / AI crawlers pass through untouched.
//     Everyone else is redirected to /unavailable (with their detected country).
export const config = {
  matcher: ['/((?!api|unavailable|_next|favicon|robots.txt|sitemap.xml|llms.txt|.*\\.).*)'],
};

const BOTS = /googlebot|bingbot|duckduckbot|applebot|slurp|gptbot|chatgpt|oai-searchbot|claudebot|claude-web|anthropic|ccbot|perplexitybot|baiduspider|yandex|facebookexternalhit|twitterbot|linkedinbot|pinterest|bingpreview|petalbot|amazonbot/i;

// q-value of one media type in an Accept header; 0 when it is not listed.
function q(accept, type) {
  for (const part of accept.split(',')) {
    const [t, ...params] = part.trim().split(';');
    if (t.trim().toLowerCase() !== type) continue;
    const m = params.join(';').match(/q=([0-9.]+)/i);
    return m ? parseFloat(m[1]) : 1;
  }
  return 0;
}

// Only when markdown is asked for explicitly and ranks above HTML.
function prefersMarkdown(accept) {
  if (!accept || !/text\/markdown/i.test(accept)) return false;
  const md = q(accept, 'text/markdown');
  return md > 0 && md > q(accept, 'text/html');
}

// Flat pages: /x -> /x.md (the file exists). Directory pages: /x.md does not
// exist, so vercel.json rewrites /:slug.md -> /:slug/index.md after the miss.
function twinPath(pathname) {
  const p = pathname.replace(/\/+$/, '');
  return p === '' ? '/index.md' : `${p}.md`;
}

export default function middleware(request) {
  const url = new URL(request.url);
  const accept = request.headers.get('accept') || '';

  if (prefersMarkdown(accept) && /^\/[a-z0-9/-]*$/i.test(url.pathname)) {
    const dest = new URL(twinPath(url.pathname), request.url);
    dest.search = url.search;
    return new Response(null, { headers: { 'x-middleware-rewrite': dest.toString() } });
  }

  const country = (request.headers.get('x-vercel-ip-country') || 'US').toUpperCase();
  const region = request.headers.get('x-vercel-ip-country-region') || '';
  const ua = request.headers.get('user-agent') || '';

  // US traffic and crawlers see the normal site.
  if (country === 'US' || BOTS.test(ua)) return;

  // Non-US → the US-only page, carrying the detected country/region.
  const dest = new URL('/unavailable', request.url);
  dest.searchParams.set('c', country);
  if (region) dest.searchParams.set('r', region);
  return Response.redirect(dest.toString(), 307);
}
