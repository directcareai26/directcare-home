// Vercel Edge Middleware — geo gate for directcare.ai.
// US visitors and search-engine / AI crawlers pass through untouched.
// Everyone else is redirected to /unavailable (with their detected country attached).
export const config = {
  matcher: ['/((?!api|unavailable|_next|favicon|robots.txt|sitemap.xml|llms.txt|.*\\.).*)'],
};

const BOTS = /googlebot|bingbot|duckduckbot|applebot|slurp|gptbot|chatgpt|oai-searchbot|claudebot|claude-web|anthropic|ccbot|perplexitybot|baiduspider|yandex|facebookexternalhit|twitterbot|linkedinbot|pinterest|bingpreview|petalbot|amazonbot/i;

export default function middleware(request) {
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
