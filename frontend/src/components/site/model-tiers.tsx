import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Route as RouteIcon,
  Brain,
  Terminal,
  Eye,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
  HardDrive,
  Database,
  ArrowRight,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type HardwareProfile = "8gb" | "24gb" | "server";

interface ModelTierData {
  id: string;
  name: string;
  category: string;
  icon: typeof RouteIcon;
  status: "Always Resident" | "On-Demand Worker";
  statusColor: string;
  models: {
    "8gb": { tag: string; vram: string; context: string; note: string };
    "24gb": { tag: string; vram: string; context: string; note: string };
    server: { tag: string; vram: string; context: string; note: string };
  };
  whyChosen: string;
  capabilities: string[];
}

const TIERS: ModelTierData[] = [
  {
    id: "router",
    name: "Zero-Latency Router",
    category: "Classification & Dispatch",
    icon: RouteIcon,
    status: "Always Resident",
    statusColor: "text-signal-orange",
    models: {
      "8gb": {
        tag: "llama3.2:3b",
        vram: "~2.0 GB (Q4)",
        context: "128K",
        note: "Default fast classifier · Ollama keep_alive: -1",
      },
      "24gb": {
        tag: "llama3.2:3b",
        vram: "~2.0 GB (Q4)",
        context: "128K",
        note: "Ultra-fast zero-temperature resident dispatcher",
      },
      server: {
        tag: "llama3.2:3b",
        vram: "~2.0 GB (FP16)",
        context: "128K",
        note: "Dedicated classification lane for parallel sessions",
      },
    },
    whyChosen:
      "Kept permanently resident in VRAM. Evaluates every request at temperature=0 in <40ms into 6 categories (general, coding, vision, spreadsheet, QA, planning) before dispatching to specialized worker weights.",
    capabilities: [
      "Zero model-swap latency",
      "Deterministic 6-category classification",
      "Sub-40-token JSON routing format",
      "Automatic fallback handling",
    ],
  },
  {
    id: "reasoning",
    name: "General Reasoning",
    category: "Synthesis & DocGen",
    icon: Brain,
    status: "On-Demand Worker",
    statusColor: "text-metric-green",
    models: {
      "8gb": {
        tag: "qwen3.5:9b",
        vram: "~6.0 GB (Q4_K_M)",
        context: "128K",
        note: "Best quality/VRAM ratio on consumer hardware",
      },
      "24gb": {
        tag: "qwen3.6:27b",
        vram: "~16.5 GB (Q5_K_M)",
        context: "128K",
        note: "Full workstation depth & multilingual mastery",
      },
      server: {
        tag: "llama3.3:70b",
        vram: "~42 GB (Multi-GPU)",
        context: "128K",
        note: "Frontier-class reasoning across distributed GPUs",
      },
    },
    whyChosen:
      "High reasoning density per GB of VRAM. Synthesizes complex multi-page plant manuals, cross-checks SOPs, drafts formal Word notes (.docx), PPT briefings, and manages stateful LangGraph planning loops.",
    capabilities: [
      "Deterministic python-docx & pptx generation",
      "Strict SOP clause citation adherence",
      "Multi-step LangGraph plan execution",
      "Hindi & regional document synthesis",
    ],
  },
  {
    id: "coding",
    name: "Deterministic Coding",
    category: "Sandboxed Code & Data",
    icon: Terminal,
    status: "On-Demand Worker",
    statusColor: "text-metric-green",
    models: {
      "8gb": {
        tag: "qwen2.5-coder:7b",
        vram: "~5.0 GB (Q4_K_M)",
        context: "32K",
        note: "Strongest coding model that fits 8GB cleanly",
      },
      "24gb": {
        tag: "qwen3-coder:30b",
        vram: "~18.0 GB (Q4_K_M)",
        context: "256K",
        note: "Deep repository-scale code intelligence",
      },
      server: {
        tag: "qwen3-coder-next:80b-moe",
        vram: "~48 GB (3B Active MoE)",
        context: "256K",
        note: "MoE architecture activating only 3B params/token",
      },
    },
    whyChosen:
      "Trained specifically for Python, Bash, and openpyxl/pandas data pipelines. Writes verified scripts executed directly inside a network-isolated Docker sandbox (--network=none) with memory and CPU safeguards.",
    capabilities: [
      "Docker sandbox execution (--network=none)",
      "Automated diff generation & preview",
      "openpyxl & pandas calculation engine",
      "Pre-execution syntax & security checks",
    ],
  },
  {
    id: "vision",
    name: "Vision & Industrial OCR",
    category: "Scans & Blueprints",
    icon: Eye,
    status: "On-Demand Worker",
    statusColor: "text-metric-green",
    models: {
      "8gb": {
        tag: "qwen2.5vl:7b",
        vram: "~5.2 GB (Q4_K_M)",
        context: "32K",
        note: "Top OCR & chart understanding in 7B class",
      },
      "24gb": {
        tag: "qwen2.5vl:32b",
        vram: "~19.5 GB (Q4_K_M)",
        context: "128K",
        note: "High-resolution blueprint & schematic parsing",
      },
      server: {
        tag: "qwen2.5vl:72b",
        vram: "~45 GB (Multi-GPU)",
        context: "128K",
        note: "Enterprise-grade multi-page document processing",
      },
    },
    whyChosen:
      "Purpose-built for industrial plants with degraded physical paperwork, skewed scanned PDFs, handwritten shift logs, P&ID diagrams, and tabular equipment reports. Eliminates reliance on cloud OCR APIs.",
    capabilities: [
      "OmniDocBench benchmark-grade OCR",
      "Handwritten log & form field extraction",
      "Complex nested table & grid parser",
      "Local multi-page scan reconstruction",
    ],
  },
];

export function ModelTiers() {
  const [profile, setProfile] = useState<HardwareProfile>("8gb");
  const [activeInfoTier, setActiveInfoTier] = useState<string | null>(null);

  return (
    <div className="w-full">
      {/* Hardware profile toggle bar */}
      <div className="flex flex-col items-center justify-between gap-4 border-b border-carbon-lift pb-6 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <Cpu className="h-4 w-4 text-signal-orange" />
          <span className="font-mono text-xs uppercase tracking-widest text-pale-stone">
            Target Hardware Profile:
          </span>
        </div>

        <div className="flex items-center rounded-[6px] border border-carbon-lift bg-obsidian-canvas/80 p-1">
          {[
            { id: "8gb" as const, label: "8GB VRAM", sub: "Default Single GPU" },
            { id: "24gb" as const, label: "24GB VRAM", sub: "RTX 4090 / Studio" },
            { id: "server" as const, label: "Multi-GPU", sub: "Enterprise Cluster" },
          ].map((item) => {
            const isActive = profile === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setProfile(item.id)}
                className={cn(
                  "relative rounded-[4px] px-3.5 py-1.5 font-mono text-xs transition-all duration-200",
                  isActive
                    ? "bg-chalk text-obsidian-canvas font-medium shadow-xs"
                    : "text-warm-granite hover:text-bone hover:bg-carbon-lift/50",
                )}
              >
                <span>{item.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="active-profile-pill"
                    className="absolute inset-0 -z-10 rounded-[4px] bg-chalk"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 4-Tier Responsive Cards Grid */}
      <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
        {TIERS.map((tier, idx) => {
          const TierIcon = tier.icon;
          const currentModel = tier.models[profile];
          const isSelected = activeInfoTier === tier.id;

          return (
            <motion.div
              key={tier.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.08, duration: 0.5 }}
              className={cn(
                "group relative flex flex-col justify-between rounded-[10px] border border-carbon-lift bg-gradient-to-b from-[#141414] to-[#0a0a0a] p-5 transition-all duration-300",
                "hover:border-ash-stroke hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)]",
                isSelected && "border-signal-orange/70 shadow-[0_0_20px_rgba(235,94,40,0.15)]",
              )}
            >
              {/* Card Top: Category & Status */}
              <div>
                <div className="flex items-center justify-between border-b border-carbon-lift/70 pb-3">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-[4px] border border-carbon-lift bg-obsidian-canvas text-signal-orange">
                      <TierIcon className="h-4 w-4" />
                    </div>
                    <span className="font-mono text-[0.7rem] uppercase tracking-wider text-warm-granite">
                      {tier.category}
                    </span>
                  </div>

                  <span
                    className={cn(
                      "font-mono text-[0.65rem] uppercase tracking-widest px-2 py-0.5 rounded-[2px] border border-carbon-lift bg-obsidian-canvas/90",
                      tier.status === "Always Resident"
                        ? "text-signal-orange border-signal-orange/30"
                        : "text-pale-stone/70",
                    )}
                  >
                    {tier.status === "Always Resident" ? "Resident" : "Worker"}
                  </span>
                </div>

                {/* Model Header */}
                <div className="mt-4">
                  <h3 className="text-base font-medium tracking-tight text-bone group-hover:text-chalk">
                    {tier.name}
                  </h3>

                  {/* Active Model Tag Badge */}
                  <div className="mt-3 rounded-[5px] border border-carbon-lift bg-obsidian-canvas p-2.5">
                    <div className="flex items-center justify-between">
                      <div className="font-mono text-xs font-semibold tracking-tight text-chalk">
                        {currentModel.tag}
                      </div>
                      <span className="font-mono text-[0.65rem] text-signal-orange">
                        {currentModel.vram}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[0.68rem] text-warm-granite">
                      <span className="truncate pr-2">{currentModel.note}</span>
                      <span className="font-mono text-pale-stone/60">{currentModel.context}</span>
                    </div>
                  </div>
                </div>

                {/* Why this model is chosen */}
                <div className="mt-4">
                  <div className="flex items-center gap-1 text-[0.7rem] font-mono uppercase tracking-wider text-pale-stone/80">
                    <Info className="h-3 w-3 text-signal-orange" />
                    <span>Implementation Rationale</span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-warm-granite/90 line-clamp-3 group-hover:line-clamp-none transition-all">
                    {tier.whyChosen}
                  </p>
                </div>

                {/* Capabilities list */}
                <div className="mt-4 space-y-1.5 border-t border-carbon-lift/60 pt-3">
                  {tier.capabilities.map((cap) => (
                    <div key={cap} className="flex items-start gap-2 text-[0.72rem] text-pale-stone">
                      <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-signal-orange/80" />
                      <span className="leading-snug">{cap}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Card Footer: Telemetry Tag */}
              <div className="mt-5 border-t border-carbon-lift/40 pt-3 flex items-center justify-between font-mono text-[0.65rem] text-warm-granite">
                <span className="flex items-center gap-1.5">
                  <HardDrive className="h-3 w-3 text-pale-stone/50" />
                  Ollama / vLLM local
                </span>
                <span className="text-signal-orange/80">Air-Gapped</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Bottom Foundation Strip: Embedding & RAG Infrastructure */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.35, duration: 0.5 }}
        className="mt-6 rounded-[10px] border border-carbon-lift bg-[#0e0e0e] p-4 sm:p-5"
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:items-center">
          {/* Embedding Tier */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-carbon-lift bg-obsidian-canvas text-signal-orange">
              <Database className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-chalk">
                  nomic-embed-text
                </span>
                <span className="rounded-[2px] bg-carbon-lift px-1.5 py-0.2 font-mono text-[0.65rem] text-pale-stone">
                  ~300 MB VRAM
                </span>
              </div>
              <p className="mt-1 text-xs text-warm-granite">
                Kept resident alongside the router for instant SOP semantic retrieval (8192-token context) without cloud vector APIs.
              </p>
            </div>
          </div>

          {/* Network Guard */}
          <div className="flex items-start gap-3 border-t border-carbon-lift pt-4 lg:border-t-0 lg:border-l lg:pl-5 lg:pt-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-carbon-lift bg-obsidian-canvas text-metric-green">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-chalk">
                  net_guard Isolation
                </span>
                <span className="rounded-[2px] bg-metric-green/15 px-1.5 py-0.2 font-mono text-[0.65rem] text-metric-green">
                  Loopback Only
                </span>
              </div>
              <p className="mt-1 text-xs text-warm-granite">
                Continuous 500ms socket poller blocking any non-127.0.0.1 outbound attempts across all agent processes.
              </p>
            </div>
          </div>

          {/* Sandboxed Code Execution */}
          <div className="flex items-start gap-3 border-t border-carbon-lift pt-4 lg:border-t-0 lg:border-l lg:pl-5 lg:pt-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-carbon-lift bg-obsidian-canvas text-pale-stone">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-chalk">
                  Docker Sandbox
                </span>
                <span className="rounded-[2px] bg-carbon-lift px-1.5 py-0.2 font-mono text-[0.65rem] text-pale-stone">
                  --network=none
                </span>
              </div>
              <p className="mt-1 text-xs text-warm-granite">
                Pre-pulled python:3.11, node:20, and gcc:13 images with 2GB memory caps and hard timeouts for verified code runs.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
