"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

function Sparkline({ tone = "orange" }: { tone?: "orange" | "green" }) {
  const stroke = tone === "orange" ? "var(--signal-orange)" : "var(--metric-green)";
  const d =
    tone === "orange"
      ? "M0 32 L14 26 L28 29 L42 18 L56 22 L70 12 L84 15 L98 6 L112 9 L126 2"
      : "M0 20 L14 24 L28 14 L42 17 L56 9 L70 13 L84 8 L98 12 L112 4 L126 7";
  return (
    <svg viewBox="0 0 126 40" className="mt-4 h-10 w-full" preserveAspectRatio="none">
      <motion.path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.6, ease: "easeOut" }}
      />
    </svg>
  );
}

export function DashboardFrame() {
  const [docCount, setDocCount] = useState<number>(58);
  const [chunkCount, setChunkCount] = useState<number>(1447);

  useEffect(() => {
    let isMounted = true;

    async function loadCorpusStats() {
      try {
        const { data, error } = await supabase.rpc("get_public_corpus_stats");
        if (!error && data && isMounted) {
          const stats = typeof data === "string" ? JSON.parse(data) : data;
          if (typeof stats.documents === "number") {
            setDocCount(stats.documents);
          }
          if (typeof stats.chunks === "number") {
            setChunkCount(stats.chunks);
          }
        }
      } catch (err) {
        console.warn("Could not fetch live corpus stats:", err);
      }
    }

    loadCorpusStats();

    return () => {
      isMounted = false;
    };
  }, []);

  const tiles = [
    { label: "Active model", value: "Qwen3.6-27B", tone: "orange" as const },
    { label: "Tokens / sec", value: "148", tone: "green" as const },
    { label: "Egress packets", value: "0", tone: "orange" as const },
    {
      label: "Docs indexed",
      value: docCount.toLocaleString(),
      subValue: `${chunkCount.toLocaleString()} chunks`,
      tone: "green" as const,
    },
    { label: "Agent steps", value: "36", tone: "orange" as const },
    { label: "Sandbox runs", value: "9", tone: "green" as const },
  ];

  return (
    <div className="overflow-hidden rounded-[10px] border border-carbon-lift bg-[#0d0d0d]">
      <div className="flex items-center gap-3 border-b border-carbon-lift px-4 py-3">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-graphite-mid" />
          <span className="h-2.5 w-2.5 rounded-full bg-graphite-mid" />
          <span className="h-2.5 w-2.5 rounded-full bg-graphite-mid" />
        </div>
        <span className="eyebrow text-pale-stone">bastion — runtime monitor</span>
        <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-signal-orange" />
        <span className="eyebrow text-pale-stone">local</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3">
        {tiles.map((t) => (
          <div key={t.label} className="min-w-0 border-r border-b border-carbon-lift p-5">
            <div className="eyebrow text-pale-stone truncate">{t.label}</div>
            <div className="mt-3 flex items-baseline gap-2 overflow-hidden">
              <span
                className={`text-bone font-medium tracking-tight truncate ${
                  t.value.length > 7 ? "text-xl md:text-[1.35rem]" : "text-heading"
                }`}
                title={t.value}
              >
                {t.value}
              </span>
              {"subValue" in t && t.subValue && (
                <span className="font-mono text-caption text-warm-granite shrink-0">
                  ({t.subValue})
                </span>
              )}
            </div>
            <Sparkline tone={t.tone} />
          </div>
        ))}
      </div>

      <div className="space-y-2 px-5 py-5 font-mono text-caption text-warm-granite">
        {[
          "› router: file=inspection_report.pdf → vision tier (qwen3-vl-32b)",
          "› retrieval: 6 SOP chunks matched · confidence 0.91",
          "› plan: extract findings → cross-check SOP-114 → draft approval note",
          "› forge: approval_note.docx written · 4 pages · signed hash ok",
        ].map((line, i) => (
          <motion.div
            key={line}
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 + i * 0.18, duration: 0.5 }}
          >
            {line}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
