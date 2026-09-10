// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import fs from "node:fs";
import path from "node:path";


function getFreshOpenAIKey(): string {
  try {
    const envPath = path.resolve(process.cwd(), ".env");
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, "utf8");
      const match = content.match(/(?:VITE_)?OPENAI_API_KEY=([^\r\n]+)/);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
  } catch (e) {
    console.warn("Could not read .env for OpenAI key:", e);
  }
  return process.env.OPENAI_API_KEY || process.env.VITE_OPENAI_API_KEY || "";
}

export default defineConfig({
  vite: {
    server: {
      proxy: {
        "/api/openai": {
          target: "https://api.openai.com",
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api\/openai/, ""),
          secure: true,
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              const freshKey = getFreshOpenAIKey();
              if (freshKey) {
                proxyReq.setHeader("authorization", `Bearer ${freshKey}`);
              }
            });
          },
        },
      },
    },
  },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
});
