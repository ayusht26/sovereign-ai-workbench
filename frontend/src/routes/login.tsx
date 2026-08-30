import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useState } from "react";
import { Nav } from "@/components/site/nav";
import { Eyebrow } from "@/components/site/reveal";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — Bastion Workbench" },
      {
        name: "description",
        content:
          "Sign in to your Bastion site with your organisation email. Authentication is handled by your local identity provider — credentials never leave the network.",
      },
      { property: "og:title", content: "Sign in — Bastion Workbench" },
      {
        property: "og:description",
        content: "Local-only sign in for the Bastion sovereign AI workbench.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.includes("@") || password.length < 6) {
      setError("Enter a valid organisation email and a password of 6+ characters.");
      return;
    }
    setPending(true);
    setTimeout(() => {
      setPending(false);
      navigate({ to: "/chat" });
    }, 900);
  };

  return (
    <div className="min-h-screen bg-obsidian-canvas">
      <Nav />

      <main className="mx-auto grid min-h-screen max-w-[1200px] items-center gap-16 px-6 pt-28 pb-20 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <Eyebrow>site access</Eyebrow>
          <h1 className="mt-6 text-heading tracking-[-0.031em] text-bone md:text-heading-lg">
            Sign in to your Bastion site.
          </h1>
          <p className="mt-5 max-w-md text-body text-warm-granite">
            Authentication is brokered by your own directory. Your credentials, prompts and
            documents stay on the subnet — there is no vendor account behind this form.
          </p>

          <div className="mt-12 space-y-4 font-mono text-caption text-warm-granite">
            <div>› node: bastion-01.plant.local</div>
            <div>› egress: deny · dns: blocked</div>
            <div>› runtime: vLLM 4 models loaded</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-[10px] bg-bone p-6 md:p-8"
        >
          <Eyebrow tone="dark">local identity provider</Eyebrow>
          <h2 className="mt-4 text-heading tracking-[-0.031em] text-obsidian-canvas">Log in</h2>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="eyebrow block text-obsidian-canvas/60">
                Organisation email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="a.tiwari@plant.local"
                className="mt-3 w-full rounded-[3px] border border-obsidian-canvas/15 bg-chalk px-3 py-3 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/35 focus:border-obsidian-canvas/50"
              />
            </div>

            <div>
              <label htmlFor="password" className="eyebrow block text-obsidian-canvas/60">
                Password
              </label>
              <div className="relative mt-3">
                <input
                  id="password"
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-[3px] border border-obsidian-canvas/15 bg-chalk px-3 py-3 pr-11 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/35 focus:border-obsidian-canvas/50"
                />
                <button
                  type="button"
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow((v) => !v)}
                  className="absolute top-1/2 right-3 -translate-y-1/2 text-obsidian-canvas/45 transition-colors hover:text-obsidian-canvas"
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-body-sm text-obsidian-canvas/70">
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 rounded-[2px] accent-[oklch(0.176_0_0)]"
                />
                Keep this workstation signed in
              </label>
              <span className="text-body-sm text-obsidian-canvas/50">Reset via IT</span>
            </div>

            {error && (
              <p className="font-mono text-caption text-[oklch(0.577_0.2_27)]">› {error}</p>
            )}

            <button
              type="submit"
              disabled={pending}
              className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-obsidian-canvas px-[14px] py-3 text-body-sm text-bone transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {pending && <Loader2 className="h-4 w-4 animate-spin" />}
              {pending ? "Verifying on node…" : "Log in"}
            </button>
          </form>

          <p className="mt-6 text-body-sm text-obsidian-canvas/60">
            No account on this node?{" "}
            <Link to="/" className="text-obsidian-canvas underline underline-offset-4">
              Ask your site administrator
            </Link>
          </p>
        </motion.div>
      </main>
    </div>
  );
}
