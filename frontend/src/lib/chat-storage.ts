import { RetrievedPassage } from "./rag-service";
import { GeneratedFile } from "./file-generator";

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  routedTo?: string | undefined;
  reason?: string | undefined;
  steps?: string[] | undefined;
  passages?: RetrievedPassage[] | undefined;
  isDocumentQuery?: boolean | undefined;
  imageUrl?: string | undefined;
  revisedPrompt?: string | undefined;
  isImage?: boolean | undefined;
  generatedFiles?: GeneratedFile[] | undefined;
  attachedFileName?: string | undefined;
  attachedImageDataUrl?: string | undefined;
  createdAt?: string | undefined;
}

export interface ChatSession {
  id: string;
  userId?: string | undefined;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

function getStorageKey(userId?: string): string {
  return `bastion_chat_sessions_${userId || 'guest'}`;
}

/**
 * Fetch all saved chat sessions for the active user
 */
export function fetchUserChatSessions(userId?: string): ChatSession[] {
  if (typeof window === 'undefined') return [];
  try {
    const key = getStorageKey(userId);
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const sessions = JSON.parse(raw);
    if (!Array.isArray(sessions)) return [];
    return sessions.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  } catch (err) {
    console.warn('Error reading chat sessions from localStorage:', err);
    return [];
  }
}

/**
 * Save or update a chat session
 */
export function saveUserChatSession(session: ChatSession, userId?: string): void {
  if (typeof window === 'undefined') return;
  try {
    const key = getStorageKey(userId);
    const existing = fetchUserChatSessions(userId);
    const filtered = existing.filter((s) => s.id !== session.id);
    const updated = [
      {
        ...session,
        updatedAt: new Date().toISOString(),
      },
      ...filtered,
    ].slice(0, 50); // Keep last 50 sessions
    localStorage.setItem(key, JSON.stringify(updated));
  } catch (err) {
    console.warn('Error saving chat session to localStorage:', err);
  }
}

/**
 * Delete a specific chat session
 */
export function deleteUserChatSession(sessionId: string, userId?: string): void {
  if (typeof window === 'undefined') return;
  try {
    const key = getStorageKey(userId);
    const existing = fetchUserChatSessions(userId);
    const filtered = existing.filter((s) => s.id !== sessionId);
    localStorage.setItem(key, JSON.stringify(filtered));
  } catch (err) {
    console.warn('Error deleting chat session:', err);
  }
}

/**
 * Clear all chat sessions for a user
 */
export function clearAllUserChatSessions(userId?: string): void {
  if (typeof window === 'undefined') return;
  try {
    const key = getStorageKey(userId);
    localStorage.removeItem(key);
    // Also clear legacy keys
    localStorage.removeItem('bastion_recent_queries');
  } catch (err) {
    console.warn('Error clearing chat sessions:', err);
  }
}
