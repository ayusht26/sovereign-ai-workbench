import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { AnimatePresence, motion } from 'motion/react';
import {
  ChevronDown,
  FileText,
  Plus,
  Paperclip,
  Check,
  ShieldCheck,
  Sliders,
  Sparkles,
  Lock,
  Trash2,
  Download,
  ImageIcon,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import AI_Input_Search from '@/components/kokonutui/ai-input-search';
import AITextLoading from '@/components/kokonutui/ai-text-loading';
import { MarkdownMessage } from '@/components/ui/markdown-message';
import { FileDeliverableCard } from '@/components/chat/file-card';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';
import {
  executeWorkbenchQuery,
  RetrievedPassage,
} from '@/lib/rag-service';
import {
  ChatMessage,
  ChatSession,
  fetchUserChatSessions,
  saveUserChatSession,
  deleteUserChatSession,
  clearAllUserChatSessions,
} from '@/lib/chat-storage';
import { BastionMark } from '@/components/site/parallax-hero';
import ProfileDropdown from '@/components/kokonutui/profile-dropdown';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

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

function ChatPage() {
  const navigate = useNavigate();
  const { user, profile, company, role, loading } = useAuth();

  const [selected, setSelected] = useState('auto');
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  // Chat sessions state
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Modals for confirmation
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [isClearAllOpen, setIsClearAllOpen] = useState(false);

  // Dropdown states for reasoning and sources per message
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({});
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const endRef = useRef<HTMLDivElement | null>(null);

  // Protected route check
  useEffect(() => {
    if (!loading && !user) {
      navigate({ to: '/login' });
    }
  }, [loading, user, navigate]);

  // Load chat sessions from storage
  useEffect(() => {
    const loaded = fetchUserChatSessions(user?.id);
    setChatSessions(loaded);
  }, [user?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

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

  const handleNewRun = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleSelectSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setMessages(session.messages || []);
  };

  const confirmDeleteSession = () => {
    if (!sessionToDelete) return;
    deleteUserChatSession(sessionToDelete, user?.id);
    const updated = fetchUserChatSessions(user?.id);
    setChatSessions(updated);
    if (currentSessionId === sessionToDelete) {
      setCurrentSessionId(null);
      setMessages([]);
    }
    setSessionToDelete(null);
  };

  const confirmClearAll = () => {
    clearAllUserChatSessions(user?.id);
    setChatSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
    setIsClearAllOpen(false);
  };

  const toggleReasoning = (messageId: string) => {
    setExpandedReasoning((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const toggleSources = (messageId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
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
    } catch {
      window.open(url, '_blank');
    }
  };

  const send = async (
    raw?: string,
    isWebSearch: boolean = false,
    attachedFile?: File | null,
    imageDataUrl?: string | null
  ) => {
    const text = (raw ?? '').trim();
    if ((!text && !attachedFile && !imageDataUrl) || busy) return;

    const userMsgId = crypto.randomUUID();
    const queryDisplayText = text || (imageDataUrl ? 'Attached image context' : `Uploaded file: ${attachedFile?.name}`);

    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      text: queryDisplayText,
      attachedFileName: attachedFile?.name,
      attachedImageDataUrl: imageDataUrl || undefined,
      createdAt: new Date().toISOString(),
    };

    // Determine session ID
    const sessionId = currentSessionId || crypto.randomUUID();
    if (!currentSessionId) {
      setCurrentSessionId(sessionId);
    }

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);

    // Compute session title
    const existingSession = chatSessions.find((s) => s.id === sessionId);
    const sessionTitle = existingSession?.title || queryDisplayText.slice(0, 36);

    const initialSession: ChatSession = {
      id: sessionId,
      userId: user?.id,
      title: sessionTitle,
      createdAt: existingSession?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: newMessages,
    };
    saveUserChatSession(initialSession, user?.id);
    setChatSessions(fetchUserChatSessions(user?.id));

    setBusy(true);

    try {
      const activeUserId = user?.id || '00000000-0000-0000-0000-000000000000';
      const activeCompanyId = profile?.company_id || '00000000-0000-0000-0000-000000000000';
      const activeRole = role || 'support';
      const companyName = company?.name || 'Tata Motors';

      const promptText =
        text ||
        (imageDataUrl
          ? 'Please analyze and inspect the attached image in detail.'
          : `Please analyze attached document: ${attachedFile?.name}`);

      const queryRes = await executeWorkbenchQuery(
        promptText,
        activeUserId,
        activeCompanyId,
        activeRole,
        companyName,
        selected === 'auto' ? 'auto' : active.name,
        isWebSearch,
        imageDataUrl || undefined
      );

      const hasPassages = Boolean(queryRes.passages && queryRes.passages.length > 0);

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: queryRes.answer,
        routedTo: queryRes.model,
        reason: queryRes.reason,
        steps: queryRes.steps,
        passages: queryRes.passages,
        isDocumentQuery: queryRes.isDocumentQuery && hasPassages,
        imageUrl: queryRes.imageUrl,
        revisedPrompt: queryRes.revisedPrompt,
        isImage: queryRes.isImage,
        generatedFiles: queryRes.generatedFiles,
        createdAt: new Date().toISOString(),
      };

      const finalMessages = [...newMessages, assistantMsg];
      setMessages(finalMessages);

      const finalSession: ChatSession = {
        id: sessionId,
        userId: user?.id,
        title: sessionTitle,
        createdAt: existingSession?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: finalMessages,
      };
      saveUserChatSession(finalSession, user?.id);
      setChatSessions(fetchUserChatSessions(user?.id));
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: `Error synthesizing response: ${err?.message || 'Inference execution exception'}`,
        routedTo: active.name,
        reason: 'Local node execution fallback',
        createdAt: new Date().toISOString(),
      };
      const finalMessages = [...newMessages, errorMsg];
      setMessages(finalMessages);

      const errorSession: ChatSession = {
        id: sessionId,
        userId: user?.id,
        title: sessionTitle,
        createdAt: existingSession?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: finalMessages,
      };
      saveUserChatSession(errorSession, user?.id);
      setChatSessions(fetchUserChatSessions(user?.id));
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

        <div className="p-4 space-y-2">
          <button
            type="button"
            onClick={handleNewRun}
            className="flex w-full items-center gap-2 rounded-[3px] bg-carbon-lift px-3 py-2.5 text-body-sm text-bone transition-colors hover:bg-secondary cursor-pointer font-medium"
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

        {/* Recent Chats Area */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="flex items-center justify-between px-1 pb-2">
            <div className="eyebrow text-warm-granite text-[10px] tracking-wider uppercase font-semibold">
              Recent Chats
            </div>
            {chatSessions.length > 0 && (
              <button
                type="button"
                onClick={() => setIsClearAllOpen(true)}
                className="text-[10px] font-mono text-warm-granite hover:text-red-400 transition cursor-pointer"
                title="Clear all recent chats"
              >
                Clear
              </button>
            )}
          </div>

          {chatSessions.length === 0 ? (
            <div className="mt-2 rounded-[6px] border border-dashed border-carbon-lift/50 p-3 text-center">
              <p className="font-mono text-[11px] text-warm-granite">No recent chats</p>
              <p className="mt-1 text-[10px] text-warm-granite/60">
                Conversations will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {chatSessions.map((session) => {
                const isActive = currentSessionId === session.id;
                return (
                  <div
                    key={session.id}
                    onClick={() => handleSelectSession(session)}
                    className={cn(
                      "group flex items-center justify-between rounded-[4px] px-2.5 py-2 text-xs transition-colors cursor-pointer",
                      isActive
                        ? "bg-carbon-lift text-bone font-medium border border-carbon-lift"
                        : "text-warm-granite hover:bg-carbon-lift/50 hover:text-bone"
                    )}
                  >
                    <span className="truncate pr-1">› {session.title}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSessionToDelete(session.id);
                      }}
                      title="Delete chat"
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-0.5 transition-opacity cursor-pointer rounded hover:bg-carbon-lift shrink-0"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                );
              })}
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
                className="py-12"
              >
                <div className="eyebrow text-warm-granite">
                  authenticated session · {company?.name || 'Tata Motors'}
                </div>
                <h1 className="mt-3 text-heading tracking-[-0.031em] text-bone">
                  What are we forging today?
                </h1>
                <p className="mt-3 max-w-lg text-body text-warm-granite">
                  Ask document-grounded questions, request code generation, or generate visual blueprints.
                </p>
              </motion.div>
            )}

            <div className="space-y-6">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                  className={cn(m.role === 'user' && 'flex justify-end')}
                >
                  {m.role === 'user' ? (
                    <div className="max-w-[85%] rounded-[10px] bg-bone px-4 py-3 text-body-sm text-obsidian-canvas font-medium shadow-sm space-y-2">
                      {m.attachedImageDataUrl && (
                        <div className="overflow-hidden rounded-lg border border-black/10 bg-black/5 p-1 max-w-[260px]">
                          <img
                            src={m.attachedImageDataUrl}
                            alt="Attached user context"
                            className="max-h-48 w-full object-cover rounded-md cursor-pointer hover:opacity-95 transition"
                            onClick={() => window.open(m.attachedImageDataUrl, '_blank')}
                          />
                        </div>
                      )}
                      <div>{m.text}</div>
                      {m.attachedFileName && !m.attachedImageDataUrl && (
                        <div className="mt-1 inline-flex items-center gap-1.5 rounded bg-black/10 px-2 py-0.5 text-[11px] font-mono">
                          <Paperclip className="h-3 w-3" />
                          <span>{m.attachedFileName}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Assistant Top Controls: Reasoning & Grounded Citations Dropdowns */}
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Dropdown 1: Reasoning Dropdown */}
                        <button
                          type="button"
                          onClick={() => toggleReasoning(m.id)}
                          className="inline-flex items-center gap-1.5 rounded-[4px] border border-carbon-lift/80 bg-carbon-lift/30 px-2.5 py-1 text-[11px] font-mono text-warm-granite hover:text-bone hover:border-ash-stroke transition cursor-pointer"
                        >
                          <Sparkles className="h-3 w-3 text-signal-orange" />
                          <span>{m.routedTo || 'Auto router'} · {expandedReasoning[m.id] ? 'Hide reasoning' : 'Show reasoning'}</span>
                          <ChevronDown
                            className={cn(
                              'h-3 w-3 transition-transform duration-200',
                              expandedReasoning[m.id] && 'rotate-180'
                            )}
                          />
                        </button>

                        {/* Dropdown 2: Grounded Citations Dropdown (ONLY if document query with passages) */}
                        {m.isDocumentQuery && m.passages && m.passages.length > 0 && (
                          <button
                            type="button"
                            onClick={() => toggleSources(m.id)}
                            className="inline-flex items-center gap-1.5 rounded-[4px] border border-carbon-lift/80 bg-carbon-lift/30 px-2.5 py-1 text-[11px] font-mono text-warm-granite hover:text-bone hover:border-ash-stroke transition cursor-pointer"
                          >
                            <FileText className="h-3 w-3 text-signal-orange" />
                            <span>Grounded citations ({m.passages.length}) · {expandedSources[m.id] ? 'Hide' : 'Show'}</span>
                            <ChevronDown
                              className={cn(
                                'h-3 w-3 transition-transform duration-200',
                                expandedSources[m.id] && 'rotate-180'
                              )}
                            />
                          </button>
                        )}
                      </div>

                      {/* Expanded Reasoning Panel */}
                      <AnimatePresence>
                        {expandedReasoning[m.id] && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-3 text-xs font-mono space-y-2">
                              <div className="flex items-center gap-2">
                                <span className="text-signal-orange font-semibold">ROUTED → {m.routedTo}</span>
                                <span className="text-[10px] text-warm-granite/70">({m.reason})</span>
                              </div>
                              {m.steps && m.steps.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 pt-1">
                                  {m.steps.map((s, idx) => (
                                    <span
                                      key={idx}
                                      className="rounded-[3px] border border-carbon-lift/60 bg-carbon-lift/40 px-2 py-0.5 text-[10px] text-pale-stone"
                                    >
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Expanded Grounded Citations Panel */}
                      <AnimatePresence>
                        {expandedSources[m.id] && m.passages && m.passages.length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="space-y-2 rounded-[8px] border border-carbon-lift bg-[#111111] p-3">
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
                                    <div className="text-warm-granite line-clamp-3 leading-relaxed">{p.content}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Generated Image rendering with download support */}
                      {m.imageUrl && (
                        <div className="mt-2 overflow-hidden rounded-[12px] border border-[#262626] bg-[#0f0f0f] p-3 shadow-xl">
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

                      {/* Main Message Text & Rich Code Block Content */}
                      <div className="text-body-sm text-bone font-sans leading-relaxed pt-1">
                        <MarkdownMessage content={m.text} />
                      </div>

                      {/* Generated Deliverables (docx, xlsx, pptx, txt) with Instant Download */}
                      {m.generatedFiles && m.generatedFiles.length > 0 && (
                        <div className="mt-3 space-y-3">
                          {m.generatedFiles.map((file) => (
                            <FileDeliverableCard key={file.id} file={file} />
                          ))}
                        </div>
                      )}

                      <div className="mt-3 flex items-center gap-3 border-t border-carbon-lift/40 pt-2 text-[11px] font-mono text-warm-granite">
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
                      'Executing sovereign model inference...',
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
              placeholder={`Ask ${role ? `as [${role.toUpperCase()}]` : ''} regarding company docs, code, or paste images…`}
              searchLabel="Web Search"
              disabled={busy}
              onSubmit={(text, isWebSearch, file, imageDataUrl) =>
                send(text, isWebSearch, file, imageDataUrl)
              }
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

      {/* Delete Single Chat Session Alert Dialog */}
      <AlertDialog open={Boolean(sessionToDelete)} onOpenChange={(isOpen) => !isOpen && setSessionToDelete(null)}>
        <AlertDialogContent className="border-carbon-lift bg-[#121212] text-bone">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-bone">Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription className="text-warm-granite text-xs">
              Are you sure you want to delete this chat session? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-carbon-lift bg-[#181818] text-bone hover:bg-carbon-lift hover:text-white cursor-pointer">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteSession}
              className="bg-red-600 text-white hover:bg-red-700 font-medium cursor-pointer"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Clear All Chats Alert Dialog */}
      <AlertDialog open={isClearAllOpen} onOpenChange={setIsClearAllOpen}>
        <AlertDialogContent className="border-carbon-lift bg-[#121212] text-bone">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-bone">Clear all recent chats?</AlertDialogTitle>
            <AlertDialogDescription className="text-warm-granite text-xs">
              Are you sure you want to clear all your saved chat sessions? This will permanently delete your conversation history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-carbon-lift bg-[#181818] text-bone hover:bg-carbon-lift hover:text-white cursor-pointer">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmClearAll}
              className="bg-red-600 text-white hover:bg-red-700 font-medium cursor-pointer"
            >
              Clear All
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
