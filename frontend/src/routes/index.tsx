import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect } from "react";
import { motion } from "motion/react";
import { ShieldCheck, Cpu, FileStack, Route as RouteIcon, Lock, Boxes, Brain, Terminal, ScanEye } from "lucide-react";
import { Nav } from "@/components/site/nav";
import { Footer } from "@/components/site/footer";
import { Reveal, ScrollExpand, ScrollRule, Eyebrow } from "@/components/site/reveal";
import { DashboardFrame } from "@/components/site/dashboard-frame";
import CardFlip from "@/components/kokonutui/card-flip";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { ParallaxHero } from "@/components/site/parallax-hero";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Bastion — Sovereign Agentic AI Workbench" },
      {
        name: "description",
        content:
          "Agentic AI that never leaves your network. Automatic open-weight model routing, grounded retrieval on your SOPs, and real Word, Excel and code output.",
      },
      { property: "og:title", content: "Bastion — Sovereign Agentic AI Workbench" },
      {
        property: "og:description",
        content:
          "On-premise agentic AI for confidential industrial work. Auto model routing, zero egress, real file output.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Home,
});

const features = [
  {
    icon: RouteIcon,
    title: "Automatic model routing",
    body: "A rule plus embedding router reads the task and picks the right open-weight model — reasoning, coding, or vision-OCR — per turn. You never pick a dropdown you don't understand.",
  },
  {
    icon: ShieldCheck,
    title: "Provable air-gap",
    body: "Egress is denied at the container network layer. Every request, tool call and file write lands in a tamper-evident audit log you can hand to an auditor.",
  },
  {
    icon: FileStack,
    title: "Real deliverables",
    body: "Approval notes as .docx, costings as .xlsx, briefings as .pptx, patches as verified code — generated from your own SOPs and manuals, not from a public corpus.",
  },
  {
    icon: Cpu,
    title: "Runs on your iron",
    body: "vLLM on a single workstation GPU for a department, or a multi-GPU tier for a site. Quantized AWQ/GPTQ weights keep the footprint honest.",
  },
  {
    icon: Boxes,
    title: "Agentic, not autocomplete",
    body: "The planner decomposes work, calls tools in a sandbox, checks its own output against retrieved SOP clauses, and iterates until the artifact holds up.",
  },
  {
    icon: Lock,
    title: "Grounded on your corpus",
    body: "Multilingual embeddings index scanned SOPs, drawings and handwritten notes — including Hindi and regional-language documents — with citations on every claim.",
  },
];

const comparison = [
  [
    "Where your data goes",
    "Third-party datacentre, retained by policy",
    "Stays on your subnet — egress denied",
  ],
  [
    "Availability",
    "Depends on an internet link and a vendor's uptime",
    "Runs during a WAN outage, on the plant floor",
  ],
  [
    "Model choice",
    "One model per API key, priced per token",
    "Per-task routing across open weights, priced per GPU-hour",
  ],
  [
    "Compliance story",
    "Vendor attestation you cannot inspect",
    "Packet-level proof plus a local audit log",
  ],
  ["Cost curve", "Scales with every token forever", "Fixed hardware, marginal cost near zero"],
];

function Home() {
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      const targetId = window.location.hash.slice(1);
      const element = document.getElementById(targetId);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
      }
    }
  }, []);

  return (
    <div className="min-h-screen bg-obsidian-canvas">
      <Nav />

      {/* Parallax Hero */}
      <ParallaxHero />

      {/* v1 Hero — two-column product intro */}
      <section className="mx-auto max-w-[1200px] px-6 pt-24 pb-20">
        <div className="grid items-center gap-16 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <Reveal>
            <Eyebrow>local / air-gapped / sovereign</Eyebrow>
            <h2 className="mt-6 text-[2.75rem] leading-[1.05] tracking-[-0.04em] text-bone md:text-display">
              Agentic AI that never leaves the building.
            </h2>
            <p className="mt-6 max-w-md text-body text-warm-granite">
              Bastion gives refineries, PSUs and defence-linked manufacturers a Claude-class
              assistant that plans, uses tools and produces real files — entirely inside their own
              network.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link
                to="/chat"
                className="rounded-[3px] bg-chalk px-[14px] py-3 text-body-sm text-obsidian-canvas transition-opacity hover:opacity-90"
              >
                Open the workbench
              </Link>
              <Link
                to="/login"
                className="border border-ash-stroke px-[14px] py-3 text-body-sm text-bone transition-colors hover:border-chalk hover:text-chalk"
              >
                Sign in to your site →
              </Link>
            </div>
            <div className="mt-10 flex items-center gap-3">
              <span className="eyebrow text-warm-granite">router</span>
              <AITextLoading
                texts={[
                  "Classifying task...",
                  "Selecting model...",
                  "Retrieving SOPs...",
                  "Drafting artifact...",
                ]}
                className="!text-body-sm !font-normal"
              />
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <DashboardFrame />
          </Reveal>
        </div>
      </section>

      {/* Trust bar */}
      <section className="overflow-hidden py-16">
        <div className="flex w-max marquee-track gap-16 pr-16">
          {[0, 1].map((dup) => (
            <div key={dup} className="flex gap-16">
              {[
                "REFINERY EAST",
                "NATIONAL POWER",
                "DEFENCE FORGE",
                "PORT AUTHORITY",
                "STEEL WORKS 4",
                "NUCLEAR OPS",
              ].map((name) => (
                <span
                  key={`${dup}-${name}`}
                  className="eyebrow whitespace-nowrap tracking-[0.2em] text-warm-granite"
                >
                  {name}
                </span>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* Scroll-expanding product panel */}
      <section id="product" className="mx-auto max-w-[1200px] px-6 py-24 scroll-mt-20">
        <Reveal className="mx-auto max-w-xl text-center">
          <Eyebrow>the workbench</Eyebrow>
          <h2 className="mt-5 text-heading text-bone md:text-heading-lg">
            One surface. Every model. Zero egress.
          </h2>
          <p className="mt-4 text-body text-warm-granite">
            Drop in a scanned inspection report and watch the run expand: vision OCR, SOP retrieval,
            reasoning, then a signed Word note on the other side.
          </p>
        </Reveal>

        <ScrollExpand className="mt-16">
          <div className="rounded-[20px] border border-carbon-lift bg-[#0d0d0d] p-4 md:p-8">
            <div className="grid gap-6 md:grid-cols-3">
              {[
                { k: "01 — ingest", v: "Scanned PDF, drawing, photo, handwriting" },
                { k: "02 — route", v: "Vision → retrieval → reasoning tier" },
                { k: "03 — forge", v: "approval_note.docx · costing.xlsx · patch.diff" },
              ].map((s, i) => (
                <motion.div
                  key={s.k}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15, duration: 0.6 }}
                  className="border border-carbon-lift p-5"
                >
                  <div className="eyebrow text-signal-orange">{s.k}</div>
                  <div className="mt-3 text-body text-bone">{s.v}</div>
                </motion.div>
              ))}
            </div>
            <div className="mt-8">
              <ScrollRule />
            </div>
            <div className="mt-8 grid gap-4 font-mono text-caption text-warm-granite md:grid-cols-2">
              <div>› network policy: egress=deny · dns=blocked · usb=audited</div>
              <div>› audit: 1,204 events sealed · hash chain intact</div>
            </div>
          </div>
        </ScrollExpand>
      </section>

      {/* Feature card row */}
      <section id="capabilities" className="mx-auto max-w-[1200px] px-6 py-24 scroll-mt-20">
        <Reveal>
          <Eyebrow>capabilities</Eyebrow>
          <h2 className="mt-5 max-w-2xl text-heading text-bone">
            Built for confidential industrial work, not for demos.
          </h2>
        </Reveal>
        <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.06}>
              <div className="group h-full rounded-[10px] border border-carbon-lift p-5 transition-colors hover:border-ash-stroke">
                <f.icon className="h-5 w-5 text-signal-orange" strokeWidth={1.25} />
                <h3 className="mt-6 text-body text-bone">{f.title}</h3>
                <p className="mt-3 text-body-sm text-warm-granite">{f.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Why better than API calls */}
      <section id="security" className="mx-auto max-w-[1200px] px-6 py-24 scroll-mt-20">
        <div className="grid gap-14 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <Reveal>
            <Eyebrow>vs. a hosted api</Eyebrow>
            <h2 className="mt-5 text-heading text-bone md:text-heading-lg">
              A token you send outside is a token you no longer control.
            </h2>
            <p className="mt-5 max-w-md text-body text-warm-granite">
              Today the real failure mode is not "no AI" — it is an engineer quietly pasting a
              confidential inspection report into a public chatbot. Bastion removes the incentive by
              making the local path the fast path.
            </p>
            <div className="mt-10 rounded-[10px] bg-bone p-6">
              <Eyebrow tone="dark">measured on a single workstation</Eyebrow>
              <div className="mt-5 grid grid-cols-3 gap-4">
                {[
                  ["0", "bytes egressed"],
                  ["148", "tok / sec"],
                  ["100%", "audit coverage"],
                ].map(([v, l]) => (
                  <div key={l}>
                    <div className="text-heading tracking-[-0.031em] text-obsidian-canvas">{v}</div>
                    <div className="eyebrow mt-2 text-obsidian-canvas/60">{l}</div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="overflow-hidden rounded-[10px] border border-carbon-lift">
              <div className="grid grid-cols-[1.1fr_1fr_1fr] border-b border-carbon-lift">
                <div className="eyebrow p-4 text-pale-stone">Dimension</div>
                <div className="eyebrow p-4 text-pale-stone">Hosted API</div>
                <div className="eyebrow p-4 text-signal-orange">Bastion, on-prem</div>
              </div>
              {comparison.map(([dim, api, local], i) => (
                <motion.div
                  key={dim}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                  className="grid grid-cols-[1.1fr_1fr_1fr] border-b border-carbon-lift last:border-b-0"
                >
                  <div className="p-4 text-body-sm text-bone">{dim}</div>
                  <div className="p-4 text-body-sm text-warm-granite">{api}</div>
                  <div className="p-4 text-body-sm text-bone">{local}</div>
                </motion.div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Model tiers — 3D interactive flip cards */}
      <section id="models" className="mx-auto max-w-[1200px] px-6 py-24 scroll-mt-20">
        <Reveal>
          <Eyebrow>model tiers</Eyebrow>
          <h2 className="mt-5 max-w-2xl text-heading text-bone">
            Open weights, chosen for you, per task.
          </h2>
          <p className="mt-4 max-w-xl text-body text-warm-granite">
            Every request is automatically routed to an on-device open-weight specialist. Zero cloud fallback, zero token egress.
          </p>
        </Reveal>
        <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 justify-items-center">
          <Reveal className="w-full flex justify-center">
            <CardFlip
              icon={RouteIcon}
              title="Task Router"
              subtitle="Llama3.2-3B · Zero Latency"
              description="Always resident in VRAM. Classifies requests in <40ms into 6 categories at zero temperature."
              features={[
                "Resident in VRAM (~2GB)",
                "0-temp JSON dispatch",
                "6 routing categories",
                "Zero cloud telemetry",
              ]}
              actionLabel="Always Resident"
            />
          </Reveal>
          <Reveal delay={0.08} className="w-full flex justify-center">
            <CardFlip
              icon={Brain}
              title="Reasoning Tier"
              subtitle="Qwen3.5-9B · Doc Synthesis"
              description="Formulates multi-step plans, cross-checks SOPs, and drafts formal .docx approval notes."
              features={[
                "128K context window",
                "Native .docx / .pptx",
                "Strict SOP citations",
                "LangGraph orchestrator",
              ]}
              actionLabel="Worker Model"
            />
          </Reveal>
          <Reveal delay={0.16} className="w-full flex justify-center">
            <CardFlip
              icon={Terminal}
              title="Coding Sandbox"
              subtitle="Qwen2.5-Coder-7B · Docker"
              description="Generates verified scripts and spreadsheets executed in an isolated network-less container."
              features={[
                "Docker --network=none",
                "pandas & openpyxl engine",
                "Code diff preview",
                "Syntax verification",
              ]}
              actionLabel="Worker Model"
            />
          </Reveal>
          <Reveal delay={0.24} className="w-full flex justify-center">
            <CardFlip
              icon={ScanEye}
              title="Vision & OCR"
              subtitle="Qwen2.5-VL-7B · Schematics"
              description="Extracts data from degraded plant paperwork, handwritten logs, tables, and blueprints."
              features={[
                "OmniDocBench OCR mode",
                "Handwritten shift logs",
                "Complex table parser",
                "Local image pipeline",
              ]}
              actionLabel="Worker Model"
            />
          </Reveal>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-[1200px] px-6 py-24">
        <Reveal className="flex justify-center">
          <div className="w-full max-w-[480px] rounded-[10px] bg-bone p-6">
            <Eyebrow tone="dark">deployment</Eyebrow>
            <h2 className="mt-5 text-heading tracking-[-0.031em] text-obsidian-canvas">
              Install it behind your firewall this quarter.
            </h2>
            <p className="mt-4 text-body-sm text-obsidian-canvas/70">
              One workstation for a pilot department, a GPU tier for a full site. No accounts, no
              keys, no outbound calls.
            </p>
            <Link
              to="/contact"
              className="mt-8 inline-flex rounded-[3px] bg-obsidian-canvas px-[14px] py-3 text-body-sm text-bone transition-opacity hover:opacity-90"
            >
              Request a site key
            </Link>
          </div>
        </Reveal>
      </section>

      <Footer />
    </div>
  );
}
