import { createFileRoute, Link } from "@tanstack/react-router";
import { AnimatePresence, motion } from "motion/react";
import {
  ChevronDown,
  FileText,
  Plus,
  Send,
  Paperclip,
  Check,
  ShieldCheck,
  LogOut,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Workbench — Bastion local agent chat" },
      {
        name: "description",
        content:
          "Chat with your on-premise agent. Pick a local open-weight model or let the auto router choose the right tier for each task.",
      },
      { property: "og:title", content: "Workbench — Bastion local agent chat" },
      {
        property: "og:description",
        content:
          "On-premise agentic chat with automatic model routing across reasoning, coding and vision tiers.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ChatPage,
});

type ModelId = "auto" | "reasoning" | "coding" | "vision" | "lite";

const MODELS: {
  id: ModelId;
  name: string;
  detail: string;
  tag: string;
}[] = [
  { id: "auto", name: "Auto router", detail: "Picks the best tier per task", tag: "recommended" },
  {
    id: "reasoning",
    name: "Qwen3.6-27B",
    detail: "Synthesis, notes, SOP checks",
    tag: "reasoning",
  },
  { id: "coding", name: "Qwen3-Coder-Next", detail: "Patches, scripts, sandbox runs", tag: "code" },
  { id: "vision", name: "Qwen3-VL-32B", detail: "Scans, tables, handwriting", tag: "vision" },
  { id: "lite", name: "Qwen3.5-8B", detail: "Fast drafts, low GPU load", tag: "lite" },
];

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  routedTo?: string;
  reason?: string;
  steps?: string[];
};

const SUGGESTIONS = [
  "Draft an approval note from this inspection report",
  "Cross-check pump SOP-114 against yesterday's readings",
  "Write a Python script to parse the vibration CSV",
  "Extract the tables from this scanned drawing",
];

function route(prompt: string): { model: string; reason: string; steps: string[] } {
  const p = prompt.toLowerCase();
  if (/scan|image|drawing|photo|handwrit|ocr|table|pdf/.test(p)) {
    return {
      model: "Qwen3-VL-32B",
      reason: "document/image cues detected → vision-OCR tier",
      steps: ["OCR pages", "Extract tables", "Normalise findings"],
    };
  }
  if (/code|script|python|patch|bug|sql|parse|regex/.test(p)) {
    return {
      model: "Qwen3-Coder-Next",
      reason: "code intent detected → coding tier (3B active MoE)",
      steps: ["Plan module", "Write code", "Execute in sandbox"],
    };
  }
  if (/sop|approval|note|report|policy|audit|compliance|check/.test(p)) {
    return {
      model: "Qwen3.6-27B",
      reason: "long-form synthesis over retrieved SOPs → reasoning tier",
      steps: ["Retrieve SOP chunks", "Cross-check clauses", "Draft artifact"],
    };
  }
  return {
    model: "Qwen3.5-8B",
    reason: "short conversational turn → lite tier, lowest GPU cost",
    steps: ["Answer directly"],
  };
}

function reply(prompt: string, model: string) {
  return `Working locally on ${model}. Here is what I found for “${prompt.slice(0, 80)}”:

1. Retrieved 6 grounded passages from your indexed corpus (SOP-114, MAINT-22, drawing rev C) — every claim below is citable.
2. Reconciled the request against the current plant revision and flagged 2 clauses that need a sign-off.
3. Prepared a deliverable — approval_note.docx — with the findings table, the SOP references and an empty signature block.

Nothing left the network: this run made 0 outbound connections and is sealed in the audit log.`;
}

export default function ChatPage() {
  const [selected, setSelected] = useState<ModelId>("auto");
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const active = useMemo(
    () =>
      MODELS.find((m) => m.id === selected) ?? {
        id: "auto" as ModelId,
        name: "Auto router",
        detail: "Picks the best tier per task",
        tag: "recommended",
      },
    [selected],
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = (raw?: string) => {
    const text = (raw ?? input).trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", text }]);
    setBusy(true);

    const decided =
      selected === "auto"
        ? route(text)
        : {
            model: active.name,
            reason: "pinned manually by operator",
            steps: ["Run on pinned model"],
          };

    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: reply(text, decided.model),
          routedTo: decided.model,
          reason: decided.reason,
          steps: decided.steps,
        },
      ]);
      setBusy(false);
    }, 1800);
  };

  return (
    <div className="flex h-screen bg-obsidian-canvas">
      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-carbon-lift md:flex">
        <div className="flex h-16 items-center gap-2 border-b border-carbon-lift px-5">
          <span className="status-pulse h-1.5 w-1.5 rounded-full bg-signal-orange" />
          <Link to="/" className="eyebrow tracking-[0.22em] text-bone">
            BASTION
          </Link>
        </div>

        <div className="p-4">
          <button
            type="button"
            onClick={() => setMessages([])}
            className="flex w-full items-center gap-2 rounded-[3px] bg-carbon-lift px-3 py-2.5 text-body-sm text-bone transition-colors hover:bg-secondary"
          >
            <Plus className="h-4 w-4" /> New run
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4">
          <div className="eyebrow px-1 pb-3 text-warm-granite">History</div>
          {[
            "Inspection report — unit 4",
            "Vibration CSV parser",
            "SOP-114 clause diff",
            "Turbine outage briefing",
          ].map((h) => (
            <div
              key={h}
              className="cursor-default truncate rounded-[3px] px-1 py-2 text-body-sm text-warm-granite transition-colors hover:bg-carbon-lift hover:text-bone"
            >
              {h}
            </div>
          ))}
        </div>

        <div className="border-t border-carbon-lift p-4">
          <div className="flex items-center gap-2 text-body-sm text-warm-granite">
            <ShieldCheck className="h-4 w-4 text-metric-green" />
            Egress denied · audited
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-4 border-b border-carbon-lift px-5">
          <div className="flex items-center gap-3">
            {/* Model selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-2 rounded-[3px] border border-ash-stroke px-3 py-2 text-body-sm text-bone transition-colors hover:border-chalk"
              >
                <span className="eyebrow text-signal-orange">{active.tag}</span>
                {active.name}
                <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
              </button>

              <AnimatePresence>
                {open && (
                  <motion.div
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.18 }}
                    className="absolute top-12 left-0 z-30 w-80 rounded-[10px] border border-carbon-lift bg-[#0d0d0d] p-2"
                  >
                    {MODELS.map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          setSelected(m.id);
                          setOpen(false);
                        }}
                        className="flex w-full items-start gap-3 rounded-[3px] px-3 py-3 text-left transition-colors hover:bg-carbon-lift"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-body-sm text-bone">{m.name}</span>
                            <span className="eyebrow text-warm-granite">{m.tag}</span>
                          </div>
                          <div className="mt-1 text-caption text-warm-granite">{m.detail}</div>
                        </div>
                        {selected === m.id && (
                          <Check className="mt-0.5 h-4 w-4 text-signal-orange" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <span className="hidden eyebrow text-warm-granite sm:inline">
              bastion-01.plant.local
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden eyebrow text-metric-green sm:inline">● local</span>
            <div className="flex items-center gap-2 rounded-[3px] border border-carbon-lift px-2 py-1.5">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-carbon-lift text-caption text-bone">
                AT
              </span>
              <span className="hidden text-body-sm text-bone sm:inline">A. Tiwari</span>
              <Link to="/login" aria-label="Sign out">
                <LogOut className="h-4 w-4 text-warm-granite transition-colors hover:text-bone" />
              </Link>
            </div>
          </div>
        </header>

        {/* Transcript */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-5 py-10">
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <div className="eyebrow text-warm-granite">session start</div>
                <h1 className="mt-4 text-heading tracking-[-0.031em] text-bone">
                  What are we forging today?
                </h1>
                <p className="mt-4 max-w-lg text-body text-warm-granite">
                  Attach a document or describe the task. With{" "}
                  <span className="text-bone">Auto router</span> selected, Bastion picks the
                  reasoning, coding or vision tier for you.
                </p>
                <div className="mt-8 grid gap-3 sm:grid-cols-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => send(s)}
                      className="rounded-[10px] border border-carbon-lift p-4 text-left text-body-sm text-pale-stone transition-colors hover:border-ash-stroke hover:text-bone"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            <div className="space-y-8">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                  className={cn(m.role === "user" && "flex justify-end")}
                >
                  {m.role === "user" ? (
                    <div className="max-w-[85%] rounded-[10px] bg-bone px-4 py-3 text-body-sm text-obsidian-canvas">
                      {m.text}
                    </div>
                  ) : (
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="eyebrow text-signal-orange">routed → {m.routedTo}</span>
                        <span className="font-mono text-caption text-warm-granite">{m.reason}</span>
                      </div>
                      {m.steps && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {m.steps.map((s) => (
                            <span
                              key={s}
                              className="rounded-[3px] border border-carbon-lift px-2 py-1 font-mono text-caption text-pale-stone"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                      <p className="mt-4 whitespace-pre-wrap text-body text-bone/90">{m.text}</p>
                      <button
                        type="button"
                        className="mt-5 inline-flex items-center gap-2 border border-ash-stroke px-3 py-2 text-body-sm text-bone transition-colors hover:border-chalk hover:text-chalk"
                      >
                        <FileText className="h-4 w-4" /> approval_note.docx
                      </button>
                    </div>
                  )}
                </motion.div>
              ))}

              {busy && (
                <div className="flex items-center gap-3">
                  <span className="status-pulse h-1.5 w-1.5 rounded-full bg-signal-orange" />
                  <AITextLoading
                    texts={[
                      "Classifying task...",
                      "Selecting local model...",
                      "Retrieving SOP chunks...",
                      "Drafting artifact...",
                    ]}
                    className="!text-body-sm !font-normal"
                  />
                </div>
              )}
              <div ref={endRef} />
            </div>
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-carbon-lift">
          <div className="mx-auto max-w-3xl px-5 py-5">
            <div className="rounded-[10px] border border-carbon-lift focus-within:border-ash-stroke">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={2}
                placeholder="Describe the task, or attach a scanned report…"
                className="w-full resize-none bg-transparent px-4 py-3 text-body-sm text-bone outline-none placeholder:text-warm-granite"
              />
              <div className="flex items-center justify-between px-3 pb-3">
                <label className="flex cursor-pointer items-center gap-2 rounded-[3px] px-2 py-1.5 text-body-sm text-warm-granite transition-colors hover:text-bone">
                  <input type="file" className="hidden" />
                  <Paperclip className="h-4 w-4" /> Attach
                </label>
                <button
                  type="button"
                  onClick={() => send()}
                  disabled={busy || !input.trim()}
                  className="flex items-center gap-2 rounded-[3px] bg-chalk px-3 py-2 text-body-sm text-obsidian-canvas transition-opacity hover:opacity-90 disabled:opacity-40"
                >
                  Run <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="mt-3 eyebrow text-warm-granite">
              demo runtime · responses are simulated until a local vLLM node is attached
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
