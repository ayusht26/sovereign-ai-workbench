import "./lib/error-capture";

import { consumeLastCapturedError } from "./lib/error-capture";
import { renderErrorPage } from "./lib/error-page";

type ServerEntry = {
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

let serverEntryPromise: Promise<ServerEntry> | undefined;

async function getServerEntry(): Promise<ServerEntry> {
  if (!serverEntryPromise) {
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  return serverEntryPromise;
}

// h3 swallows in-handler throws into a normal 500 Response with body
// {"unhandled":true,"message":"HTTPError"} — try/catch alone never fires for those.
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  if (response.status < 500) return response;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return response;

  const body = await response.clone().text();
  if (!isH3SwallowedErrorBody(body)) return response;

  console.error(consumeLastCapturedError() ?? new Error(`h3 swallowed SSR error: ${body}`));
  return new Response(renderErrorPage(), {
    status: 500,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function isH3SwallowedErrorBody(body: string): boolean {
  try {
    const payload = JSON.parse(body) as { unhandled?: unknown; message?: unknown };
    return payload.unhandled === true && payload.message === "HTTPError";
  } catch {
    return false;
  }
}

export default {
  async fetch(request: Request, env: unknown, ctx: unknown) {
    // Proxy /api/openai requests to OpenAI API for zero-egress/CORS handling
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/openai")) {
      try {
        const subPath = url.pathname.replace(/^\/api\/openai/, "");
        const targetUrl = `https://api.openai.com${subPath}${url.search}`;
        const apiKey =
          (typeof process !== "undefined" && (process.env.OPENAI_API_KEY || process.env.VITE_OPENAI_API_KEY)) ||
          "";

        const headers = new Headers(request.headers);
        headers.set("host", "api.openai.com");
        if (apiKey && !headers.get("authorization")) {
          headers.set("authorization", `Bearer ${apiKey}`);
        }

        const body =
          request.method !== "GET" && request.method !== "HEAD"
            ? await request.arrayBuffer()
            : undefined;

        const proxyResponse = await fetch(targetUrl, {
          method: request.method,
          headers,
          body,
        });

        const responseHeaders = new Headers(proxyResponse.headers);
        responseHeaders.set("access-control-allow-origin", "*");
        responseHeaders.set("access-control-allow-methods", "GET, POST, OPTIONS");
        responseHeaders.set("access-control-allow-headers", "authorization, content-type");

        return new Response(proxyResponse.body, {
          status: proxyResponse.status,
          statusText: proxyResponse.statusText,
          headers: responseHeaders,
        });
      } catch (proxyError) {
        console.error("Server /api/openai proxy error:", proxyError);
        return new Response(
          JSON.stringify({ error: { message: "Internal server proxy error connecting to OpenAI" } }),
          {
            status: 502,
            headers: { "content-type": "application/json" },
          }
        );
      }
    }

    try {
      const handler = await getServerEntry();
      const response = await handler.fetch(request, env, ctx);
      return await normalizeCatastrophicSsrResponse(response);
    } catch (error) {
      console.error(error);
      return new Response(renderErrorPage(), {
        status: 500,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
