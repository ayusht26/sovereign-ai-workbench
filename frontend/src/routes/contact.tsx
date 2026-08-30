import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { Loader2, CheckCircle2, Send, ArrowRight } from "lucide-react";
import { useState, useEffect } from "react";
import { Nav } from "@/components/site/nav";
import { Footer } from "@/components/site/footer";
import { Eyebrow } from "@/components/site/reveal";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact & Site Key Request — Bastion Workbench" },
      {
        name: "description",
        content:
          "Get in touch with the Bastion engineering team. Request an air-gapped evaluation site key or inquire about on-premise deployment.",
      },
      { property: "og:title", content: "Contact & Site Key Request — Bastion Workbench" },
      {
        property: "og:description",
        content: "On-premise deployment and offline site key requests for Bastion.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ContactPage,
});

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (!email.includes("@") || !email.includes(".")) {
      setError("Please enter a valid organisation email.");
      return;
    }
    if (!message.trim()) {
      setError("Please enter your message or deployment inquiry.");
      return;
    }

    setPending(true);
    setTimeout(() => {
      setPending(false);
      setSubmitted(true);
    }, 800);
  };

  const handleReset = () => {
    setName("");
    setEmail("");
    setMessage("");
    setSubmitted(false);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-obsidian-canvas text-bone flex flex-col justify-between selection:bg-signal-orange selection:text-white">
      <Nav />

      <main className="mx-auto grid min-h-screen max-w-[1200px] items-center gap-16 px-6 pt-28 pb-20 lg:grid-cols-2">
        {/* Left column */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <Eyebrow>contact & site keys</Eyebrow>
          <h1 className="mt-6 text-heading tracking-[-0.031em] text-bone md:text-heading-lg">
            Request a site key.
          </h1>
          <p className="mt-5 max-w-md text-body text-warm-granite">
            Deploy Bastion behind your firewall. Request an evaluation site key, ask about
            hardware requirements, or speak with our security engineering team.
          </p>

          <div className="mt-12 space-y-4 font-mono text-caption text-warm-granite">
            <div>› deployment: on-premise & air-gapped</div>
            <div>› key type: ed25519 offline hardware-sealed</div>
            <div>› telemetry: zero egress · 0 network calls</div>
          </div>
        </motion.div>

        {/* Right column: Normal simple form */}
        <motion.div
          initial={{ opacity: 0, y: 32, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-[10px] bg-bone p-6 md:p-8 text-obsidian-canvas shadow-xl"
        >
          <AnimatePresence mode="wait">
            {!submitted ? (
              <motion.div
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Eyebrow tone="dark">direct dispatch</Eyebrow>
                <h2 className="mt-4 text-heading tracking-[-0.031em] text-obsidian-canvas">
                  Send a message
                </h2>

                <form onSubmit={onSubmit} className="mt-6 space-y-4">
                  <div>
                    <label htmlFor="name" className="eyebrow block text-obsidian-canvas/60">
                      Full Name
                    </label>
                    <input
                      id="name"
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Dr. Aris Thorne"
                      className="mt-2 w-full rounded-[3px] border border-obsidian-canvas/15 bg-chalk px-3 py-2.5 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/35 focus:border-obsidian-canvas/60"
                    />
                  </div>

                  <div>
                    <label htmlFor="email" className="eyebrow block text-obsidian-canvas/60">
                      Organisation Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="a.thorne@plant.local"
                      className="mt-2 w-full rounded-[3px] border border-obsidian-canvas/15 bg-chalk px-3 py-2.5 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/35 focus:border-obsidian-canvas/60"
                    />
                  </div>

                  <div>
                    <label htmlFor="message" className="eyebrow block text-obsidian-canvas/60">
                      Message
                    </label>
                    <textarea
                      id="message"
                      required
                      rows={4}
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Tell us about your workstation / cluster environment or evaluation timeline..."
                      className="mt-2 w-full rounded-[3px] border border-obsidian-canvas/15 bg-chalk px-3 py-2.5 text-body-sm text-obsidian-canvas outline-none transition-colors placeholder:text-obsidian-canvas/35 focus:border-obsidian-canvas/60 resize-none"
                    />
                  </div>

                  {error && (
                    <p className="font-mono text-caption text-[oklch(0.577_0.2_27)]">
                      › {error}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={pending}
                    className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-obsidian-canvas px-[14px] py-3 text-body-sm text-bone font-medium transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer"
                  >
                    {pending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Sending request…</span>
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 text-signal-orange" />
                        <span>Request Site Key</span>
                      </>
                    )}
                  </button>
                </form>

                <p className="mt-6 text-body-sm text-obsidian-canvas/60">
                  Prefer direct terminal access?{" "}
                  <Link to="/chat" className="text-obsidian-canvas underline underline-offset-4">
                    Open the workbench demo
                  </Link>
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="confirmation"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="py-4 space-y-5"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-signal-orange/15 flex items-center justify-center text-signal-orange shrink-0">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <div>
                    <Eyebrow tone="dark">request dispatched</Eyebrow>
                    <h3 className="text-heading text-obsidian-canvas">
                      Message Sent
                    </h3>
                  </div>
                </div>

                <p className="text-body-sm text-obsidian-canvas/80 leading-relaxed">
                  Thank you, <strong className="text-obsidian-canvas font-medium">{name}</strong>. Your inquiry has been routed to our security dispatch team. An engineer will follow up at{" "}
                  <strong className="text-obsidian-canvas font-medium">{email}</strong> shortly.
                </p>

                <div className="rounded-[4px] bg-chalk border border-obsidian-canvas/15 p-4 font-mono text-caption text-obsidian-canvas/70 space-y-1">
                  <div>› ticket: BSTN-REQ-{Math.floor(1000 + Math.random() * 9000)}</div>
                  <div>› status: sealed · dispatch queued</div>
                </div>

                <div className="space-y-3 pt-2">
                  <Link
                    to="/chat"
                    className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-obsidian-canvas px-[14px] py-3 text-body-sm text-bone transition-opacity hover:opacity-90 font-medium"
                  >
                    <span>Launch Workbench Demo</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>

                  <button
                    type="button"
                    onClick={handleReset}
                    className="flex w-full items-center justify-center gap-2 rounded-[3px] border border-obsidian-canvas/20 bg-transparent px-[14px] py-2.5 text-body-sm text-obsidian-canvas hover:bg-obsidian-canvas/5 transition-colors cursor-pointer"
                  >
                    <span>Send another message</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </main>

      <Footer />
    </div>
  );
}
