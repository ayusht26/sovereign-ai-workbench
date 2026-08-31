import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { AnimatePresence, motion } from 'motion/react';
import {
  ChevronDown,
  FileText,
  Plus,
  Send,
  Paperclip,
  Check,
  ShieldCheck,
  LogOut,
  Sliders,
  Sparkles,
  Building,
  Lock,
  Trash2,
  Download,
  ImageIcon,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import AI_Input_Search from '@/components/kokonutui/ai-input-search';
import AITextLoading from '@/components/kokonutui/ai-text-loading';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';
import {
  executeWorkbenchQuery,
  fetchUserRecentQueries,
  deleteUserRecentQuery,
  clearAllUserRecentQueries,
  RetrievedPassage,
} from '@/lib/rag-service';
import { RecentQuery } from '@/lib/supabase';
import { BastionMark } from '@/components/site/parallax-hero';
import ProfileDropdown from '@/components/kokonutui/profile-dropdown';

export const Route = createFileRoute('/chat')({
  head: () => ({
    meta: [
      { title: 'Workbench — Bastion Sovereign AI Chat' },
      {
        name: 'description',
        content:
          'Multi-tenant role-segregated RAG chat. Row Level Security guarantees strict document partition by department and company.',
      },
      { property: 'og:title', content: 'Workbench — Bastion Sovereign AI Chat' },
      {
        property: 'og:description',
        content:
          'On-premise agentic chat with automatic model routing and Postgres RLS security boundary.',
      },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
  }),
  component: ChatPage,
});

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  routedTo?: string;
  reason?: string;
  steps?: string[];
  passages?: RetrievedPassage[];
  isDocumentQuery?: boolean;
  imageUrl?: string;
  revisedPrompt?: string;
  isImage?: boolean;
  attachedFileName?: string;
}

const MODELS = [
  { id: 'auto', name: 'Auto router', detail: 'Picks best sovereign tier per task', tag: 'recommended' },
  {
    id: 'reasoning',
    name: 'Qwen3.6-27B',
    detail: 'Synthesis, notes, SOP checks',
    tag: 'reasoning',
  },
  { id: 'coding', name: 'Qwen3-Coder-Next', detail: 'Patches, scripts, sandbox runs', tag: 'code' },
  { id: 'vision', name: 'Qwen3-VL-32B', detail: 'Scans, tables, visual diffusion', tag: 'vision' },
  { id: 'lite', name: 'Qwen3.5-8B', detail: 'Fast drafts, low GPU load', tag: 'lite' },
];

export default function ChatPage() {
  const navigate = useNavigate();
  const { user, profile, company, role, loading, logout } = useAuth();

  const [selected, setSelected] = useState('auto');
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([]);
  const [loadingQueries, setLoadingQueries] = useState<boolean>(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  // Protected route check
  useEffect(() => {
    if (!loading && !user) {
      navigate({ to: '/login' });
    }
  }, [loading, user, navigate]);

  const active = useMemo(
    () =>
      MODELS.find((m) => m.id === selected) ?? {
        id: 'auto',
        name: 'Auto router',
        detail: 'Picks the best tier per task',
        tag: 'recommended',
      },
    [selected]
  );

  // Load Recent Queries from DB (with localStorage fallback)
  useEffect(() => {
    let isMounted = true;
    async function loadQueries() {
      setLoadingQueries(true);
      try {
        const queries = await fetchUserRecentQueries(user?.id);
        if (isMounted) {
          setRecentQueries(queries);
        }
      } catch (err) {
        console.error('Error fetching recent queries:', err);
      } finally {
        if (isMounted) setLoadingQueries(false);
      }
    }
    loadQueries();
    return () => {
      isMounted = false;
    };
  }, [user?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  // Suggestions customized by active user role
  const suggestions = useMemo(() => {
    if (role === 'tech') {
      return [
        'What is the CAN bus baud rate and BMS architecture?',
        'Explain high voltage battery pack cooling circuits',
        'Write a Python script to parse the vibration telemetry CSV',
        'Generate an image of an aerodynamic EV chassis with exposed battery pack',
      ];
    }
    if (role === 'finance') {
      return [
        'What is the Q3 FY26 Capex budget for Passenger EV division?',
        'What are the battery cell cost projections with Agratas?',
        'Write a Python script to project EBITDA margin growth',
        'Summarize operating margin targets for Q4 FY26',
      ];
    }
    if (role === 'support') {
      return [
        'What is the SLA for high-voltage battery warranty triage?',
        'When does the customer loaner vehicle policy apply?',
        'Show diagnostic fault codes for BMS communication errors',
        'Write a summary of modular pack replacement criteria',
      ];
    }
    // Admin or default
    return [
      'Check CAN-FD bus communication specs for Curvv EV [Tech]',
      'Summarize Q3 FY26 Capex allocation and battery cost targets [Finance]',
      'Generate an image of an enterprise sovereign AI node in a dark server rack',
      'Write a Python data processor for CAN telemetry',
    ];
  }, [role]);

  const handleDeleteRecentQuery = async (e: React.MouseEvent, queryId: string) => {
    e.stopPropagation();
    setRecentQueries((prev) => prev.filter((q) => q.id !== queryId));
    await deleteUserRecentQuery(queryId, user?.id);
  };

  const handleClearAllRecentQueries = async () => {
    setRecentQueries([]);
    await clearAllUserRecentQueries(user?.id);
  };

  const handleDownloadImage = async (url: string, filename: string = 'sovereign-ai-render.png') => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (e) {
      // Direct window open fallback
      window.open(url, '_blank');
    }
  };

  const send = async (raw?: string, isWebSearch: boolean = false, attachedFile?: File | null) => {
    const text = (raw ?? '').trim();
    if ((!text && !attachedFile) || busy) return;

    const userMsgId = crypto.randomUUID();
    const queryDisplayText = text || `Uploaded file: ${attachedFile?.name}`;

    setMessages((m) => [
      ...m,
      {
        id: userMsgId,
        role: 'user',
        text: queryDisplayText,
        attachedFileName: attachedFile?.name,
      },
    ]);

    // Prepend to recent queries state immediately for instant feedback
    if (text) {
      const optimisticRecent: RecentQuery = {
        id: crypto.randomUUID(),
        user_id: user?.id || '00000000-0000-0000-0000-000000000000',
        company_id: profile?.company_id || '00000000-0000-0000-0000-000000000000',
        query_text: text,
        created_at: new Date().toISOString(),
      };
      setRecentQueries((prev) => [
        optimisticRecent,
        ...prev.filter((q) => q.query_text.toLowerCase() !== text.toLowerCase()),
      ].slice(0, 20));
    }

    setBusy(true);

    try {
      const activeUserId = user?.id || '00000000-0000-0000-0000-000000000000';
      const activeCompanyId = profile?.company_id || '00000000-0000-0000-0000-000000000000';
      const activeRole = role || 'support';
      const companyName = company?.name || 'Tata Motors';

      const queryRes = await executeWorkbenchQuery(
        text || `Please analyze attached document: ${attachedFile?.name}`,
        activeUserId,
        activeCompanyId,
        activeRole,
        companyName,
        selected === 'auto' ? 'auto' : active.name,
        isWebSearch
      );

      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: queryRes.answer,
          routedTo: queryRes.model,
          reason: queryRes.reason,
          steps: queryRes.steps,
          passages: queryRes.passages,
          isDocumentQuery: queryRes.isDocumentQuery,
          imageUrl: queryRes.imageUrl,
          revisedPrompt: queryRes.revisedPrompt,
          isImage: queryRes.isImage,
        },
      ]);
    } catch (err: any) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: `Error synthesizing response: ${err?.message || 'Inference execution exception'}`,
          routedTo: active.name,
          reason: 'Local node execution fallback',
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-screen bg-obsidian-canvas text-bone">
      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-carbon-lift md:flex">
        <div className="flex h-16 items-center justify-between border-b border-carbon-lift px-5">
          <Link to="/" className="flex items-center gap-2">
            <BastionMark className="h-4 w-4" color="var(--signal-orange)" />
            <span className="eyebrow tracking-[0.22em] text-bone font-bold">BASTION</span>
          </Link>
          <span
            className={cn(
              'rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase',
              role === 'admin' && 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
              role === 'tech' && 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
              role === 'finance' && 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
              role === 'support' && 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
            )}
          >
            {role || 'guest'}
          </span>
        </div>

        {/* Company Badge */}
        <div className="border-b border-carbon-lift px-4 py-3 bg-carbon-lift/20">
          <div className="flex items-center gap-2 text-caption font-mono text-warm-granite">
            <Building className="h-3.5 w-3.5 text-signal-orange" />
            <span className="truncate text-bone">{company?.name || 'Tata Motors'}</span>
          </div>
          <div className="mt-1 text-[10px] font-mono text-metric-green flex items-center gap-1">
            <ShieldCheck className="h-3 w-3" />
            <span>RLS Active: {role ? `[${role.toUpperCase()}] Scope` : 'Public'}</span>
          </div>
        </div>

        <div className="p-4 space-y-2">
          <button
            type="button"
            onClick={() => setMessages([])}
            className="flex w-full items-center gap-2 rounded-[3px] bg-carbon-lift px-3 py-2.5 text-body-sm text-bone transition-colors hover:bg-secondary cursor-pointer"
          >
            <Plus className="h-4 w-4" /> New run
          </button>

          {role === 'admin' && (
            <Link
              to="/admin"
              className="flex w-full items-center gap-2 rounded-[3px] border border-signal-orange/30 bg-signal-orange/10 px-3 py-2 text-xs font-mono font-semibold text-signal-orange hover:bg-signal-orange/20 transition cursor-pointer"
            >
              <Sliders className="h-3.5 w-3.5" /> Admin Console
            </Link>
          )}
        </div>

        {/* Recent Queries Area */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="flex items-center justify-between px-1 pb-2">
            <div className="eyebrow text-warm-granite">Recent Queries</div>
            {recentQueries.length > 0 && (
              <button
                type="button"
                onClick={handleClearAllRecentQueries}
                className="text-[10px] font-mono text-warm-granite hover:text-red-400 transition cursor-pointer"
                title="Clear all recent queries"
              >
                Clear
              </button>
            )}
          </div>

          {recentQueries.length === 0 ? (
            <div className="mt-2 rounded-[6px] border border-dashed border-carbon-lift/50 p-3 text-center">
              <p className="font-mono text-[11px] text-warm-granite">No recent queries</p>
              <p className="mt-1 text-[10px] text-warm-granite/60">
                Queries you execute will be archived here.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {recentQueries.map((q) => (
                <div
                  key={q.id}
                  onClick={() => send(q.query_text)}
                  className="group flex items-center justify-between rounded-[4px] px-2 py-1.5 text-xs text-warm-granite transition-colors hover:bg-carbon-lift hover:text-bone cursor-pointer"
                >
                  <span className="truncate pr-1">› {q.query_text}</span>
                  <button
                    type="button"
                    onClick={(e) => handleDeleteRecentQuery(e, q.id)}
                    title="Delete query"
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 transition-opacity cursor-pointer rounded hover:bg-carbon-lift/80 shrink-0"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-carbon-lift p-4">
          <div className="flex items-center gap-2 text-caption font-mono text-warm-granite">
            <ShieldCheck className="h-4 w-4 text-metric-green" />
            <span>Audit log: Sealed · No egress</span>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex h-16 items-center justify-between gap-4 border-b border-carbon-lift px-5">
          <div className="flex items-center gap-3">
            {/* Sovereign Model Selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-2 rounded-[3px] border border-ash-stroke px-3 py-1.5 text-body-sm text-bone transition-colors hover:border-chalk cursor-pointer"
              >
                <span className="eyebrow text-signal-orange">{active.tag}</span>
                {active.name}
                <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} />
              </button>

              <AnimatePresence>
                {open && (
                  <motion.div
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.18 }}
                    className="absolute top-11 left-0 z-30 w-80 rounded-[10px] border border-carbon-lift bg-[#0d0d0d] p-2 shadow-2xl"
                  >
                    {MODELS.map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          setSelected(m.id);
                          setOpen(false);
                        }}
                        className="flex w-full items-start gap-3 rounded-[3px] px-3 py-2.5 text-left transition-colors hover:bg-carbon-lift cursor-pointer"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-body-sm text-bone">{m.name}</span>
                            <span className="eyebrow text-warm-granite">{m.tag}</span>
                          </div>
                          <div className="mt-0.5 text-caption text-warm-granite">{m.detail}</div>
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
              node: bastion-01.plant.local
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden eyebrow text-metric-green sm:inline">● local vLLM</span>

            {/* Profile Dropdown */}
            {profile ? (
              <ProfileDropdown />
            ) : (
              <Link
                to="/login"
                className="rounded-[3px] bg-bone px-3 py-1 text-xs font-semibold text-obsidian-canvas hover:bg-chalk transition"
              >
                Sign in
              </Link>
            )}
          </div>
        </header>

        {/* Chat Transcript Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-5 py-8">
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <div className="eyebrow text-warm-granite">
                  authenticated session · {company?.name || 'tata motors'}
                </div>
                <h1 className="mt-3 text-heading tracking-[-0.031em] text-bone">
                  What are we forging today?
                </h1>
                <p className="mt-3 max-w-lg text-body text-warm-granite">
                  Ask document-grounded questions, request code generation, or generate visual blueprints. Row Level Security enforces document access under role <span className="font-mono text-signal-orange font-bold">[{role || 'guest'}]</span>.
                </p>

                <div className="mt-6 grid gap-2.5 sm:grid-cols-2">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => send(s)}
                      className="rounded-[8px] border border-carbon-lift bg-[#121212] p-3.5 text-left text-xs text-pale-stone transition hover:border-ash-stroke hover:text-bone cursor-pointer"
                    >
                      › {s}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            <div className="space-y-8 mt-4">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                  className={cn(m.role === 'user' && 'flex justify-end')}
                >
                  {m.role === 'user' ? (
                    <div className="max-w-[85%] rounded-[10px] bg-bone px-4 py-3 text-body-sm text-obsidian-canvas font-medium shadow-sm">
                      {m.text}
                      {m.attachedFileName && (
                        <div className="mt-2 inline-flex items-center gap-1.5 rounded bg-black/10 px-2 py-0.5 text-[11px] font-mono">
                          <Paperclip className="h-3 w-3" />
                          <span>{m.attachedFileName}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="eyebrow text-signal-orange">routed → {m.routedTo}</span>
                        <span className="font-mono text-caption text-warm-granite">{m.reason}</span>
                      </div>

                      {m.steps && (
                        <div className="mt-2.5 flex flex-wrap gap-2">
                          {m.steps.map((s) => (
                            <span
                              key={s}
                              className="rounded-[3px] border border-carbon-lift px-2 py-0.5 font-mono text-[11px] text-pale-stone bg-carbon-lift/30"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Generated Image rendering with download support */}
                      {m.imageUrl && (
                        <div className="mt-4 overflow-hidden rounded-[12px] border border-[#262626] bg-[#0f0f0f] p-3 shadow-xl">
                          <div className="relative group overflow-hidden rounded-[8px] bg-black/50">
                            <img
                              src={m.imageUrl}
                              alt={m.revisedPrompt || 'Sovereign AI Asset'}
                              className="w-full max-h-[500px] object-contain rounded-[8px] transition-transform duration-300 group-hover:scale-[1.01]"
                            />
                            <div className="absolute top-3 right-3 flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleDownloadImage(m.imageUrl!, `sovereign-ai-${Date.now()}.png`)}
                                className="flex items-center gap-1.5 rounded-lg bg-black/80 backdrop-blur-md border border-white/20 px-3 py-1.5 text-xs font-semibold text-white shadow-lg transition hover:bg-signal-orange hover:text-black cursor-pointer"
                                title="Download generated image"
                              >
                                <Download className="h-3.5 w-3.5" />
                                <span>Download</span>
                              </button>
                            </div>
                          </div>

                          <div className="mt-3 flex items-center justify-between text-caption font-mono text-warm-granite">
                            <div className="flex items-center gap-1.5 text-signal-orange">
                              <ImageIcon className="h-3.5 w-3.5" />
                              <span>Diffusion Asset Generated</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleDownloadImage(m.imageUrl!, `sovereign-ai-${Date.now()}.png`)}
                              className="text-signal-orange hover:underline flex items-center gap-1 cursor-pointer text-xs"
                            >
                              <Download className="h-3 w-3" /> Save to disk
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Document Citations if any */}
                      {m.passages && m.passages.length > 0 && (
                        <div className="mt-4 space-y-2 rounded-[8px] border border-carbon-lift bg-[#121212] p-3">
                          <div className="flex items-center gap-2 text-caption font-mono uppercase text-warm-granite">
                            <FileText className="h-3.5 w-3.5 text-signal-orange" />
                            Grounded Retrieval Citations ({m.passages.length} passages):
                          </div>
                          <div className="grid gap-2">
                            {m.passages.map((p) => (
                              <div
                                key={p.id}
                                className="rounded border border-ash-stroke/30 bg-carbon-lift/30 p-2.5 text-xs text-pale-stone"
                              >
                                <div className="flex items-center justify-between gap-2 font-mono text-[11px] text-bone font-semibold mb-1">
                                  <span>{p.documentTitle}</span>
                                  <span className="rounded bg-signal-orange/20 px-1.5 py-0.2 text-[10px] text-signal-orange uppercase">
                                    {p.category}
                                  </span>
                                </div>
                                <div className="text-warm-granite line-clamp-2">{p.content}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-4 whitespace-pre-wrap text-body-sm text-bone/90 font-sans leading-relaxed">
                        {m.text}
                      </div>

                      <div className="mt-4 flex items-center gap-3 border-t border-carbon-lift/50 pt-2 text-[11px] font-mono text-warm-granite">
                        <span className="flex items-center gap-1 text-metric-green">
                          <ShieldCheck className="h-3 w-3" /> Sealed in Access Log
                        </span>
                        <span>·</span>
                        <span>0 Outbound Egress</span>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Kokonut UI AI Text Loading */}
              {busy && (
                <div className="py-2">
                  <AITextLoading
                    texts={[
                      'Evaluating Postgres RLS security...',
                      `Searching ${role ? role.toUpperCase() : 'company'} document chunks...`,
                      'Running sovereign model inference...',
                      'Synthesizing audited response...',
                      'Polishing technical output...',
                    ]}
                    className="!text-lg !font-semibold text-bone"
                    interval={1400}
                  />
                </div>
              )}
              <div ref={endRef} />
            </div>
          </div>
        </div>

        {/* Kokonut UI AI Input Search Box Area */}
        <div className="border-t border-carbon-lift bg-obsidian-canvas/90 backdrop-blur-md px-5 py-4">
          <div className="mx-auto max-w-3xl">
            <AI_Input_Search
              placeholder={`Ask ${role ? `as [${role.toUpperCase()}]` : ''} regarding company docs, code, or images…`}
              searchLabel="Web Search"
              disabled={busy}
              onSubmit={(text, isWebSearch, file) => send(text, isWebSearch, file)}
            />
            <div className="mt-2 flex items-center justify-between px-2 text-[11px] font-mono text-warm-granite">
              <span className="flex items-center gap-1.5">
                <Lock className="h-3 w-3 text-signal-orange" />
                RLS Active: {role ? role.toUpperCase() : 'Public'}
              </span>
              <span>Enter to run · Shift+Enter for newline</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
