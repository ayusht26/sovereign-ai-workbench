import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase, Profile, Company, UserRole } from './supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: Profile | null;
  company: Company | null;
  role: UserRole | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<{ error: Error | null }>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  updateProfile: (data: { full_name?: string; avatar_url?: string }) => Promise<{ error: Error | null }>;
  updatePassword: (password: string) => Promise<{ error: Error | null }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchProfileAndCompany = useCallback(async (userId: string) => {
    try {
      const { data: profData, error: profError } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle();

      if (profError) {
        console.error('Error fetching profile:', profError);
        return;
      }

      if (profData) {
        setProfile(profData as Profile);
        if (profData.company_id) {
          const { data: compData, error: compError } = await supabase
            .from('companies')
            .select('*')
            .eq('id', profData.company_id)
            .maybeSingle();

          if (!compError && compData) {
            setCompany(compData as Company);
          }
        }
      }
    } catch (err) {
      console.error('Error loading user profile:', err);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfileAndCompany(user.id);
    }
  }, [user?.id, fetchProfileAndCompany]);

  useEffect(() => {
    let isMounted = true;

    async function initSession() {
      try {
        const { data: { session: initSess } } = await supabase.auth.getSession();
        if (isMounted) {
          setSession(initSess);
          setUser(initSess?.user ?? null);
          if (initSess?.user) {
            await fetchProfileAndCompany(initSess.user.id);
          }
        }
      } catch (e) {
        console.error('Auth initialization error:', e);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    initSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      setSession(newSession);
      setUser(newSession?.user ?? null);
      if (newSession?.user) {
        await fetchProfileAndCompany(newSession.user.id);
      } else {
        setProfile(null);
        setCompany(null);
      }
      setLoading(false);
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [fetchProfileAndCompany]);

  const login = async (identifier: string, password: string): Promise<{ error: Error | null }> => {
    try {
      let resolvedEmail = identifier.trim();

      // If user typed username or non-standard identifier
      if (!resolvedEmail.includes('@')) {
        const { data: emailData, error: rpcError } = await supabase.rpc('get_email_for_username', {
          uname: resolvedEmail,
        });

        if (rpcError || !emailData) {
          return { error: new Error('Invalid username or password') };
        }
        resolvedEmail = emailData;
      }

      // Try initial sign in
      let { data, error } = await supabase.auth.signInWithPassword({
        email: resolvedEmail,
        password,
      });

      // Fallback: If failed and input had @ (e.g. admin@tata-motor), try resolving prefix as username
      if (error && identifier.includes('@')) {
        const prefix = identifier.split('@')[0].trim();
        const { data: emailData } = await supabase.rpc('get_email_for_username', {
          uname: prefix,
        });
        if (emailData) {
          const secondAttempt = await supabase.auth.signInWithPassword({
            email: emailData,
            password,
          });
          data = secondAttempt.data;
          error = secondAttempt.error;
        }
      }

      if (error) {
        return { error: new Error(error.message || 'Invalid credentials') };
      }

      if (data.user) {
        setUser(data.user);
        setSession(data.session);
        await fetchProfileAndCompany(data.user.id);
      }

      return { error: null };
    } catch (err: any) {
      return { error: err instanceof Error ? err : new Error(err?.message || 'Login failed') };
    }
  };

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
    setProfile(null);
    setCompany(null);
  };

  const updateProfile = async (data: { full_name?: string; avatar_url?: string }) => {
    if (!user) return { error: new Error('Not authenticated') };
    try {
      const { error } = await supabase
        .from('profiles')
        .update({
          ...data,
          updated_at: new Date().toISOString(),
        })
        .eq('id', user.id);

      if (error) throw error;
      await refreshProfile();
      return { error: null };
    } catch (err: any) {
      return { error: err instanceof Error ? err : new Error(err?.message || 'Update failed') };
    }
  };

  const updatePassword = async (password: string) => {
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      return { error: null };
    } catch (err: any) {
      return { error: err instanceof Error ? err : new Error(err?.message || 'Password update failed') };
    }
  };

  const role = profile?.role ?? null;

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        company,
        role,
        loading,
        login,
        logout,
        refreshProfile,
        updateProfile,
        updatePassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
