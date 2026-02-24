import { NextRequest, NextResponse } from "next/server";

// Reads BACKEND_URL at request time (Node.js runtime), not build time.
// This is why we use a route handler instead of next.config.mjs rewrites:
// standalone mode bakes rewrites into routes-manifest.json at build time,
// so process.env.BACKEND_URL would always resolve to its build-time value.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function proxy(request: NextRequest, path: string): Promise<NextResponse> {
  const url = `${BACKEND_URL}/api/${path}${request.nextUrl.search}`;

  try {
    const init: RequestInit = {
      method: request.method,
      headers: { "Content-Type": "application/json" },
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.text();
    }

    const response = await fetch(url, init);
    const text = await response.text();

    // Try to return JSON if the backend sent JSON, otherwise return raw text
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: response.status });
    } catch {
      return new NextResponse(text, {
        status: response.status,
        headers: { "Content-Type": "text/plain" },
      });
    }
  } catch (err) {
    console.error(`[proxy] Failed to reach backend at ${url}:`, err);
    return NextResponse.json(
      { detail: "Backend unavailable" },
      { status: 503 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(request, path.join("/"));
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxy(request, path.join("/"));
}
