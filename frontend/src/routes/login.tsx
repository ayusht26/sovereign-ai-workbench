import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Eye, EyeOff, ShieldCheck, UserCheck } from "lucide-react";
import { useState } from "react";
import { Nav } from "@/components/site/nav";
import { Eyebrow } from "@/components/site/reveal";
import { SlideTextButton } from "@/components/ui/slide-text-button";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — Bastion Workbench" },
      {
        name: "description",
        content:
          "Sign in to your Bastion site with your username or organisation email. Multi-tenant company and role-scoped document access with Postgres RLS.",
      },
      { property: "og:title", content: "Sign in — Bastion Workbench" },
      {
        property: "og:description",
        content: "Multi-tenant role-segregated sign in for the Bastion sovereign AI workbench.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { login, role: currentRole } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fillQuickLogin = (id: string, pass: string) => {
    setIdentifier(id);
    setPassword(pass);
    setError(null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanId = identifier.trim();
    if (!cleanId || password.length < 5) {
      setError("Enter your username or email and your password.");
      return;
    }

    setPending(true);
    try {
      const { error: loginError } = await login(cleanId, password);
      if (loginError) {
        setError(loginError.message || "Invalid username or password");
        setPending(false);
        return;
      }

      toast.success("Authentication successful");
      // Check if admin or employee for navigation
      setTimeout(() => {
        setPending(false);
        if (cleanId === "admin" || cleanId.includes("admin")) {
          navigate({ to: "/admin" });
        } else {
          navigate({ to: "/chat" });
        }
      }, 500);
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred");
      setPending(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-canvas">
      <Nav />

      <main className="mx-auto grid min-h-screen max-w-[1200px] items-center gap-12 px-6 pt-28 pb-20 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <Eyebrow>identity & access management</Eyebrow>
          <h1 className="mt-6 text-heading tracking-[-0.031em] text-bone md:text-heading-lg">
            Sign in to your sovereign AI workspace.
          </h1>
          <p className="mt-5 max-w-md text-body text-warm-granite">
            Multi-tenant company boundary with role-scoped Row Level Security (RLS). Documents, vector
            chunks, and query streams are strictly segregated by company and department role.
          </p>

          <div className="mt-8 space-y-3 font-mono text-caption text-warm-granite">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-signal-orange" />
              <span>Company: Tata Motors (Slug: tata-motors)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-metric-green" />
              <span>Postgres RLS: Active & Enforced</span>
            </div>
            <div>› node: bastion-01.plant.local</div>
          </div>

          {/* Quick Login Test Chips */}
          <div className="mt-8 rounded-[10px] border border-carbon-lift bg-[#121212] p-4">
            <div className="flex items-center gap-2 text-caption font-mono uppercase text-warm-granite mb-3">
              <UserCheck className="h-3.5 w-3.5 text-signal-orange" />
              Quick-Fill Test Accounts:
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillQuickLogin("admin", "admin123")}
                className="flex flex-col items-start rounded border border-ash-stroke/40 bg-carbon-lift/50 p-2 text-left transition hover:border-signal-orange hover:bg-carbon-lift"
              >
                <span className="font-semibold text-bone">Tata Admin</span>
                <span className="text-[11px] font-mono text-signal-orange">admin / admin123</span>
              </button>
              <button
                type="button"
                onClick={() => fillQuickLogin("tech_lead", "tech123")}
                className="flex flex-col items-start rounded border border-ash-stroke/40 bg-carbon-lift/50 p-2 text-left transition hover:border-signal-orange hover:bg-carbon-lift"
              >
                <span className="font-semibold text-bone">Tech Specialist</span>
                <span className="text-[11px] font-mono text-pale-stone">tech_lead / tech123</span>
              </button>
              <button
                type="button"
                onClick={() => fillQuickLogin("finance_lead", "finance123")}
                className="flex flex-col items-start rounded border border-ash-stroke/40 bg-carbon-lift/50 p-2 text-left transition hover:border-signal-orange hover:bg-carbon-lift"
              >
                <span className="font-semibold text-bone">Finance Lead</span>
                <span className="text-[11px] font-mono text-pale-stone">finance_lead / finance123</span>
              </button>
              <button
                type="button"
                onClick={() => fillQuickLogin("support_lead", "support123")}
                className="flex flex-col items-start rounded border border-ash-stroke/40 bg-carbon-lift/50 p-2 text-left transition hover:border-signal-orange hover:bg-carbon-lift"
              >
                <span className="font-semibold text-bone">Support Lead</span>
                <span className="text-[11px] font-mono text-pale-stone">support_lead / support123</span>
              </button>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-[10px] bg-bone p-6 md:p-8"
        >
          <Eyebrow tone="dark">supabase authenticated directory</Eyebrow>
          <h2 className="mt-4 text-heading tracking-[-0.031em] text-obsidian-canvas">Sign in</h2>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="identifier" className="eyebrow block text-obsidian-canvas/70 font-mono text-xs">
                Username or Email
              </label>
              <input
                id="identifier"
                type="text"
                autoComplete="username"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="admin, tech_lead, or admin@tatamotors-internal.com"
                className="mt-2 w-full rounded-[3px] border border-obsidian-canvas/20 bg-chalk px-3.5 py-3 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/40 focus:border-obsidian-canvas focus:ring-1 focus:ring-obsidian-canvas/30"
              />
            </div>

            <div>
              <label htmlFor="password" className="eyebrow block text-obsidian-canvas/70 font-mono text-xs">
                Password
              </label>
              <div className="relative mt-2">
                <input
                  id="password"
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-[3px] border border-obsidian-canvas/20 bg-chalk px-3.5 py-3 pr-11 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/40 focus:border-obsidian-canvas focus:ring-1 focus:ring-obsidian-canvas/30"
                />
                <button
                  type="button"
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow((v) => !v)}
                  className="absolute top-1/2 right-3 -translate-y-1/2 text-obsidian-canvas/50 transition-colors hover:text-obsidian-canvas"
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-body-sm text-obsidian-canvas/70">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked
                  className="h-3.5 w-3.5 rounded-[2px] accent-obsidian-canvas"
                />
                Keep session authenticated
              </label>
              <span className="text-caption font-mono text-obsidian-canvas/60">
                Managed by Supabase
              </span>
            </div>

            {error && (
              <div className="rounded border border-red-600/30 bg-red-500/10 p-3 font-mono text-caption text-red-700">
                › {error}
              </div>
            )}

            <div className="w-full pt-1">
              <SlideTextButton
                type="submit"
                disabled={pending}
                text={pending ? "Verifying with Supabase Auth…" : "Sign In to Bastion"}
                variant="dark"
                className="w-full h-11 rounded-md font-medium cursor-pointer"
              />
            </div>
          </form>

          <div className="mt-6 flex items-center justify-between border-t border-obsidian-canvas/10 pt-4 text-xs text-obsidian-canvas/60">
            <span className="flex items-center gap-1.5 font-mono">
              <ShieldCheck className="h-3.5 w-3.5 text-green-700" />
              Zero-Egress Secured
            </span>
            <Link to="/" className="text-obsidian-canvas underline underline-offset-4 hover:text-obsidian-canvas/80">
              Back to Overview
            </Link>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
