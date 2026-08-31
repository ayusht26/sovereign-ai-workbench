import { createClient } from '@supabase/supabase-js';

export type UserRole = 'admin' | 'tech' | 'finance' | 'support';

export interface Company {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface Profile {
  id: string;
  company_id: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  created_at: string;
  updated_at: string;
  company?: Company;
}

export interface DocumentRecord {
  id: string;
  company_id: string;
  category: UserRole;
  title: string;
  storage_path: string | null;
  uploaded_by: string | null;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  company_id: string;
  category: UserRole;
  chunk_index: number;
  content: string;
  similarity?: number;
  created_at: string;
}

export interface DocumentAccessLog {
  id: string;
  user_id: string;
  document_id: string | null;
  company_id: string;
  action: 'query' | 'view' | 'upload' | 'download';
  query_text: string | null;
  created_at: string;
  profile?: {
    username: string;
    full_name: string | null;
    role: UserRole;
  };
  document?: {
    title: string;
    category: UserRole;
  };
}
export interface RecentQuery {
  id: string;
  user_id: string;
  company_id: string;
  query_text: string;
  created_at: string;
}

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL ||
  (typeof process !== 'undefined' ? process.env?.NEXT_PUBLIC_SUPABASE_URL || process.env?.VITE_SUPABASE_URL : '') ||
  'https://tybbzdbglhfnpdvgvrjs.supabase.co';

const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  (typeof process !== 'undefined' ? process.env?.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env?.VITE_SUPABASE_ANON_KEY : '') ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YmJ6ZGJnbGhmbnBkdmd2cmpzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MDc5NjYsImV4cCI6MjEwMzQ4Mzk2Nn0.ooAz_wKezqDKd-XxKAI_xZlkY1Hu8w_Tk5EEtzyCYzo';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
