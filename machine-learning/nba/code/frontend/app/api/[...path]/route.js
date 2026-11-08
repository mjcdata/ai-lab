export const dynamic = 'force-dynamic';
export async function GET(request, context) {
  const { path } = await context.params;
  const endpoint = path.join('/');
  if (!/^(health|players|players\/\d+(\/comparisons)?)$/.test(endpoint))
    return Response.json({ detail: 'Unknown API route' }, { status: 404 });
  try {
    const url = new URL(endpoint, (process.env.NBA_API_URL || 'http://127.0.0.1:8000') + '/');
    url.search = new URL(request.url).search;
    const response = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
    return new Response(await response.text(), { status: response.status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ detail: 'The local NBA API is unavailable. Start FastAPI on port 8000 and retry.' }, { status: 503 });
  }
}
