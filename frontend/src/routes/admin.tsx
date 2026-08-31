import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import {
  Users,
  FileText,
  ShieldCheck,
  BarChart3,
  Plus,
  Trash2,
  KeyRound,
  Edit,
  Search,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  LogOut,
  Sliders,
  ExternalLink,
  MessageSquare,
  Lock,
  UserCheck,
} from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';
import { useAuth } from '@/lib/auth-context';
import { supabase, Profile, DocumentRecord, DocumentAccessLog, UserRole } from '@/lib/supabase';
import { ingestDocument } from '@/lib/rag-service';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { BastionMark } from '@/components/site/parallax-hero';

export const Route = createFileRoute('/admin')({
  head: () => ({
    meta: [
      { title: 'Admin Console — Bastion AI Workbench' },
      {
        name: 'description',
        content: 'Company-scoped administration console for users, roles, RLS policies, documents, and audit logs.',
      },
    ],
  }),
  component: AdminPage,
});

type TabType = 'users' | 'documents' | 'logs' | 'analytics';

function AdminPage() {
  const navigate = useNavigate();
  const { user, profile, company, role, loading: authLoading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [loadingData, setLoadingData] = useState(true);

  // Data states
  const [usersList, setUsersList] = useState<Profile[]>([]);
  const [documentsList, setDocumentsList] = useState<DocumentRecord[]>([]);
  const [logsList, setLogsList] = useState<DocumentAccessLog[]>([]);

  // Modals
  const [isCreateUserOpen, setIsCreateUserOpen] = useState(false);
  const [isEditUserOpen, setIsEditUserOpen] = useState(false);
  const [isResetPassOpen, setIsResetPassOpen] = useState(false);
  const [isUploadDocOpen, setIsUploadDocOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<Profile | null>(null);

  // Form states for Create User
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('tech');
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
  const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Form states for Edit User
  const [editFullName, setEditFullName] = useState('');
  const [editRole, setEditRole] = useState<UserRole>('tech');

  // Form states for Reset Password
  const [resetPassValue, setResetPassValue] = useState('');

  // Form states for Upload Document
  const [docTitle, setDocTitle] = useState('');
  const [docCategory, setDocCategory] = useState<UserRole>('tech');
  const [docContent, setDocContent] = useState('');

  // Search/Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRole, setFilterRole] = useState<string>('all');

  const loadAdminData = async () => {
    if (!profile?.company_id) return;
    setLoadingData(true);
    try {
      // 1. Fetch Users in Company
      const { data: users, error: uErr } = await supabase
        .from('profiles')
        .select('*')
        .eq('company_id', profile.company_id)
        .order('created_at', { ascending: false });

      if (!uErr && users) {
        setUsersList(users as Profile[]);
      }

      // 2. Fetch Documents in Company
      const { data: docs, error: dErr } = await supabase
        .from('documents')
        .select('*')
        .eq('company_id', profile.company_id)
        .order('created_at', { ascending: false });

      if (!dErr && docs) {
        setDocumentsList(docs as DocumentRecord[]);
      }

      // 3. Fetch Access Logs in Company
      const { data: logs, error: lErr } = await supabase
        .from('document_access_logs')
        .select('id, user_id, document_id, company_id, action, query_text, created_at, profiles(username, full_name, role), documents(title, category)')
        .eq('company_id', profile.company_id)
        .order('created_at', { ascending: false })
        .limit(100);

      if (!lErr && logs) {
        setLogsList(
          logs.map((item) => ({
            id: item.id,
            user_id: item.user_id,
            document_id: item.document_id,
            company_id: item.company_id,
            action: item.action,
            query_text: item.query_text,
            created_at: item.created_at,
            profile: Array.isArray(item.profiles) ? item.profiles[0] : item.profiles,
            document: Array.isArray(item.documents) ? item.documents[0] : item.documents,
          }))
        );
      }
    } catch (err) {
      console.error('Failed to load admin data:', err);
      toast.error('Failed to fetch administrative records');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (!authLoading && profile?.company_id) {
      loadAdminData();
    }
  }, [authLoading, profile?.company_id]);

  // Live Uniqueness Check for Username and Email
  useEffect(() => {
    if (!newUsername && !newEmail) {
      setUsernameAvailable(null);
      setEmailAvailable(null);
      return;
    }

    const timer = setTimeout(async () => {
      setCheckingAvailability(true);
      try {
        const { data, error } = await supabase.rpc('check_identifier_availability', {
          p_username: newUsername || '__none__',
          p_email: newEmail || '__none__',
        });

        if (!error && data) {
          if (newUsername) setUsernameAvailable(data.usernameAvailable);
          if (newEmail) setEmailAvailable(data.emailAvailable);
        }
      } catch (err) {
        console.error('Availability check failed:', err);
      } finally {
        setCheckingAvailability(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [newUsername, newEmail]);

  // Handle Create User
  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUsername || !newEmail || newPassword.length < 6) {
      toast.error('Please fill all required fields (password min 6 chars)');
      return;
    }

    setFormSubmitting(true);
    try {
      const { data, error } = await supabase.rpc('admin_create_user', {
        p_username: newUsername.trim(),
        p_email: newEmail.trim(),
        p_password: newPassword,
        p_full_name: newFullName.trim() || null,
        p_role: newRole,
      });

      if (error || !data?.success) {
        toast.error(data?.error || error?.message || 'Failed to create user');
        return;
      }

      toast.success(`User @${newUsername} created successfully with role [${newRole}]`);
      setIsCreateUserOpen(false);
      setNewUsername('');
      setNewEmail('');
      setNewFullName('');
      setNewPassword('');
      setNewRole('tech');
      setUsernameAvailable(null);
      setEmailAvailable(null);
      await loadAdminData();
    } catch (err) {
      toast.error(err?.message || 'Failed to provision user');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Edit User
  const handleEditUser = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;

    setFormSubmitting(true);
    try {
      const { data, error } = await supabase.rpc('admin_update_user', {
        p_target_user_id: selectedUser.id,
        p_full_name: editFullName.trim(),
        p_role: editRole,
      });

      if (error || !data?.success) {
        toast.error(data?.error || error?.message || 'Failed to update user');
        return;
      }

      toast.success(`User @${selectedUser.username} updated`);
      setIsEditUserOpen(false);
      setSelectedUser(null);
      await loadAdminData();
    } catch (err) {
      toast.error(err?.message || 'Update failed');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Reset Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!selectedUser || resetPassValue.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    setFormSubmitting(true);
    try {
      const { data, error } = await supabase.rpc('admin_reset_password', {
        p_target_user_id: selectedUser.id,
        p_new_password: resetPassValue,
      });

      if (error || !data?.success) {
        toast.error(data?.error || error?.message || 'Failed to reset password');
        return;
      }

      toast.success(`Password reset for @${selectedUser.username}`);
      setIsResetPassOpen(false);
      setSelectedUser(null);
      setResetPassValue('');
    } catch (err) {
      toast.error(err?.message || 'Password reset failed');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Delete User
  const handleDeleteUser = async (userToDelete) => {
    if (userToDelete.id === user?.id) {
      toast.error('Cannot delete your own admin account');
      return;
    }

    if (!confirm(`Are you sure you want to delete user @${userToDelete.username}? All access will be revoked immediately.`)) {
      return;
    }

    try {
      const { data, error } = await supabase.rpc('admin_delete_user', {
        p_target_user_id: userToDelete.id,
      });

      if (error || !data?.success) {
        toast.error(data?.error || error?.message || 'Failed to delete user');
        return;
      }

      toast.success(`User @${userToDelete.username} deleted`);
      await loadAdminData();
    } catch (err) {
      toast.error(err?.message || 'Failed to delete user');
    }
  };

  // Handle Upload Document
  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!docTitle.trim() || !docContent.trim() || !profile?.company_id || !user?.id) {
      toast.error('Please provide title, category, and document content');
      return;
    }

    setFormSubmitting(true);
    try {
      const res = await ingestDocument(
        docTitle.trim(),
        docCategory,
        profile.company_id,
        user.id,
        docContent.trim()
      );

      if (!res.success) {
        toast.error(res.error || 'Failed to ingest document');
        return;
      }

      toast.success(`Document "${docTitle}" ingested into [${docCategory.toUpperCase()}] corpus`);
      setIsUploadDocOpen(false);
      setDocTitle('');
      setDocContent('');
      await loadAdminData();
    } catch (err) {
      toast.error(err?.message || 'Ingestion error');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Delete Document
  const handleDeleteDoc = async (docId, title) => {
    if (!confirm(`Delete document "${title}" and its indexed chunks?`)) return;

    try {
      const { error } = await supabase.from('documents').delete().eq('id', docId);
      if (error) throw error;

      toast.success('Document removed');
      await loadAdminData();
    } catch (err) {
      toast.error(err?.message || 'Failed to delete document');
    }
  };

  // Filtered Users
  const filteredUsers = useMemo(() => {
    return usersList.filter((u) => {
      const matchesSearch =
        u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.full_name && u.full_name.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesRole = filterRole === 'all' || u.role === filterRole;
      return matchesSearch && matchesRole;
    });
  }, [usersList, searchQuery, filterRole]);

  // Analytics Computations
  const analyticsData = useMemo(() => {
    const totalUsers = usersList.length;
    const totalDocs = documentsList.length;
    const totalLogs = logsList.length;

    // Docs per category
    const docCounts = { tech: 0, finance: 0, support: 0, admin: 0 };
    documentsList.forEach((d) => {
      docCounts[d.category] = (docCounts[d.category] || 0) + 1;
    });

    // Queries per user
    const userQueryCounts = {};
    logsList.forEach((l) => {
      const uname = l.profile?.username || 'unknown';
      if (!userQueryCounts[uname]) {
        userQueryCounts[uname] = {
          username: uname,
          count: 0,
          role: l.profile?.role || 'user',
        };
      }
      userQueryCounts[uname].count += 1;
    });

    const topUsers = Object.values(userQueryCounts).sort((a, b) => b.count - a.count);

    return {
      totalUsers,
      totalDocs,
      totalLogs,
      docCounts,
      topUsers,
    };
  }, [usersList, documentsList, logsList]);

  // Access Control Check
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-obsidian-canvas text-bone">
        <div className="flex items-center gap-3 font-mono text-sm">
          <span className="h-2 w-2 rounded-full bg-signal-orange animate-ping" />
          Verifying administrative credentials...
        </div>
      </div>
    );
  }

  if (!user || role !== 'admin') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-obsidian-canvas px-4 text-bone">
        <div className="max-w-md rounded-[10px] border border-carbon-lift bg-[#141414] p-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-signal-orange" />
          <h1 className="mt-4 text-heading tracking-[-0.031em]">Admin Access Restricted</h1>
          <p className="mt-3 text-body-sm text-warm-granite">
            This dashboard is restricted to designated administrators of <strong>{company?.name || 'your company'}</strong>.
            Your current account role is <span className="font-mono text-signal-orange">[{role || 'unauthenticated'}]</span>.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Link
              to="/login"
              className="rounded-[3px] bg-bone px-4 py-2.5 text-sm font-medium text-obsidian-canvas hover:bg-chalk transition"
            >
              Sign In as Administrator
            </Link>
            <Link
              to="/chat"
              className="rounded-[3px] border border-carbon-lift px-4 py-2.5 text-sm text-warm-granite hover:text-bone transition"
            >
              Go to Employee Chat
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian-canvas text-bone flex flex-col">
      {/* Admin Top Navigation */}
      <header className="sticky top-0 z-40 border-b border-carbon-lift bg-obsidian-canvas/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <BastionMark className="h-5 w-5" color="var(--signal-orange)" />
              <span className="eyebrow tracking-[0.22em] text-bone font-bold">BASTION</span>
            </Link>
            <span className="text-carbon-lift">/</span>
            <div className="flex items-center gap-2">
              <span className="rounded bg-signal-orange/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-signal-orange border border-signal-orange/20">
                ADMIN CONSOLE
              </span>
              <span className="text-sm text-bone font-medium">
                {company?.name || 'Tata Motors'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/chat"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-[3px] border border-carbon-lift px-3 py-1.5 text-xs text-warm-granite hover:border-ash-stroke hover:text-bone transition"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Open Workbench
            </Link>
            <Link
              to="/profile"
              className="flex items-center gap-2 rounded-[3px] border border-carbon-lift px-3 py-1.5 text-xs text-bone hover:bg-carbon-lift transition"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-signal-orange/20 text-[10px] font-bold text-signal-orange">
                {profile?.username.slice(0, 2).toUpperCase()}
              </span>
              <span>@{profile?.username}</span>
            </Link>
            <button
              onClick={() => {
                logout();
                navigate({ to: '/login' });
              }}
              title="Sign Out"
              className="text-warm-granite hover:text-bone transition cursor-pointer p-1.5"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-carbon-lift pb-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('users')}
              className={cn(
                'flex items-center gap-2 rounded-[3px] px-4 py-2 text-xs font-medium transition cursor-pointer',
                activeTab === 'users'
                  ? 'bg-bone text-obsidian-canvas font-semibold'
                  : 'text-warm-granite hover:bg-carbon-lift hover:text-bone'
              )}
            >
              <Users className="h-3.5 w-3.5" />
              Users & Permissions ({usersList.length})
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={cn(
                'flex items-center gap-2 rounded-[3px] px-4 py-2 text-xs font-medium transition cursor-pointer',
                activeTab === 'documents'
                  ? 'bg-bone text-obsidian-canvas font-semibold'
                  : 'text-warm-granite hover:bg-carbon-lift hover:text-bone'
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              Documents & Corpus ({documentsList.length})
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={cn(
                'flex items-center gap-2 rounded-[3px] px-4 py-2 text-xs font-medium transition cursor-pointer',
                activeTab === 'logs'
                  ? 'bg-bone text-obsidian-canvas font-semibold'
                  : 'text-warm-granite hover:bg-carbon-lift hover:text-bone'
              )}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Access Logs & Audit ({logsList.length})
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={cn(
                'flex items-center gap-2 rounded-[3px] px-4 py-2 text-xs font-medium transition cursor-pointer',
                activeTab === 'analytics'
                  ? 'bg-bone text-obsidian-canvas font-semibold'
                  : 'text-warm-granite hover:bg-carbon-lift hover:text-bone'
              )}
            >
              <BarChart3 className="h-3.5 w-3.5" />
              Analytics & Telemetry
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAdminData}
              disabled={loadingData}
              className="flex items-center gap-1.5 rounded-[3px] border border-carbon-lift px-3 py-1.5 text-xs text-warm-granite hover:border-ash-stroke hover:text-bone transition cursor-pointer"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', loadingData && 'animate-spin')} />
              Sync DB
            </button>
          </div>
        </div>

        {/* TAB 1: USERS */}
        {activeTab === 'users' && (
          <div className="mt-6 space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-medium tracking-tight text-bone">Company Users & Role Assignment</h2>
                <p className="text-xs text-warm-granite mt-0.5">
                  Manage directory accounts for {company?.name}. Row Level Security restricts document retrieval by assigned role.
                </p>
              </div>
              <button
                onClick={() => setIsCreateUserOpen(true)}
                className="flex items-center gap-2 rounded-[3px] bg-signal-orange px-4 py-2 text-xs font-semibold text-white transition hover:bg-signal-orange/90 cursor-pointer shadow-sm"
              >
                <Plus className="h-4 w-4" /> Provision New User
              </button>
            </div>

            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-warm-granite" />
                <input
                  type="text"
                  placeholder="Search by username or name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-[3px] border border-carbon-lift bg-[#101010] pl-9 pr-3 py-2 text-xs text-bone outline-none focus:border-ash-stroke"
                />
              </div>
              <select
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
                className="rounded-[3px] border border-carbon-lift bg-[#101010] px-3 py-2 text-xs text-bone outline-none focus:border-ash-stroke"
              >
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="tech">Tech</option>
                <option value="finance">Finance</option>
                <option value="support">Support</option>
              </select>
            </div>

            {/* Users Table */}
            <div className="overflow-x-auto rounded-[6px] border border-carbon-lift bg-[#111111]">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-carbon-lift bg-carbon-lift/30 font-mono text-[11px] uppercase text-warm-granite">
                  <tr>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Assigned Role</th>
                    <th className="px-4 py-3">Document Access Scope</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-carbon-lift/50">
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-warm-granite">
                        No users found matching criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-carbon-lift/20 transition">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2.5">
                            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-carbon-lift text-xs font-bold text-bone">
                              {u.username.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-semibold text-bone">@{u.username}</div>
                              <div className="text-[11px] text-warm-granite">{u.full_name || 'No name set'}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={cn(
                              'inline-flex items-center rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase',
                              u.role === 'admin' && 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
                              u.role === 'tech' && 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
                              u.role === 'finance' && 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
                              u.role === 'support' && 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            )}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-pale-stone font-mono text-[11px]">
                          {u.role === 'admin' && 'Full Company Read/Write (All Categories)'}
                          {u.role === 'tech' && 'Category = "tech" only'}
                          {u.role === 'finance' && 'Category = "finance" only'}
                          {u.role === 'support' && 'Category = "support" only'}
                        </td>
                        <td className="px-4 py-3.5 text-warm-granite font-mono text-[11px]">
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setSelectedUser(u);
                                setEditFullName(u.full_name || '');
                                setEditRole(u.role);
                                setIsEditUserOpen(true);
                              }}
                              className="rounded p-1 text-warm-granite hover:bg-carbon-lift hover:text-bone transition cursor-pointer"
                              title="Edit Role / Name"
                            >
                              <Edit className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                setSelectedUser(u);
                                setResetPassValue('');
                                setIsResetPassOpen(true);
                              }}
                              className="rounded p-1 text-warm-granite hover:bg-carbon-lift hover:text-bone transition cursor-pointer"
                              title="Reset Password"
                            >
                              <KeyRound className="h-3.5 w-3.5" />
                            </button>
                            {u.id !== user?.id && (
                              <button
                                onClick={() => handleDeleteUser(u)}
                                className="rounded p-1 text-warm-granite hover:bg-red-500/20 hover:text-red-400 transition cursor-pointer"
                                title="Delete User"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: DOCUMENTS */}
        {activeTab === 'documents' && (
          <div className="mt-6 space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-medium tracking-tight text-bone">Company Knowledge Base & Ingestion</h2>
                <p className="text-xs text-warm-granite mt-0.5">
                  Uploaded documents are chunked and vectorized. Postgres RLS ensures each department only sees its designated category.
                </p>
              </div>
              <button
                onClick={() => setIsUploadDocOpen(true)}
                className="flex items-center gap-2 rounded-[3px] bg-bone px-4 py-2 text-xs font-semibold text-obsidian-canvas transition hover:bg-chalk cursor-pointer"
              >
                <Plus className="h-4 w-4" /> Ingest New Document
              </button>
            </div>

            {/* Document list */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {documentsList.length === 0 ? (
                <div className="col-span-full rounded-[6px] border border-carbon-lift bg-[#111111] p-8 text-center text-warm-granite">
                  No documents indexed yet. Click "Ingest New Document" to add one.
                </div>
              ) : (
                documentsList.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex flex-col justify-between rounded-[8px] border border-carbon-lift bg-[#111111] p-4 transition hover:border-ash-stroke"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={cn(
                            'rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase',
                            doc.category === 'tech' && 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
                            doc.category === 'finance' && 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
                            doc.category === 'support' && 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
                            doc.category === 'admin' && 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                          )}
                        >
                          {doc.category}
                        </span>
                        <button
                          onClick={() => handleDeleteDoc(doc.id, doc.title)}
                          className="text-warm-granite hover:text-red-400 transition cursor-pointer"
                          title="Delete Document"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>

                      <h3 className="mt-3 font-medium text-sm text-bone leading-snug">{doc.title}</h3>
                      <div className="mt-2 font-mono text-[11px] text-warm-granite">
                        › Path: {doc.storage_path || 'text_corpus'}
                      </div>
                    </div>

                    <div className="mt-4 border-t border-carbon-lift pt-3 flex items-center justify-between text-[11px] text-warm-granite font-mono">
                      <span>Indexed: {new Date(doc.created_at).toLocaleDateString()}</span>
                      <span className="text-metric-green">● Active RLS</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 3: ACCESS LOGS */}
        {activeTab === 'logs' && (
          <div className="mt-6 space-y-6">
            <div>
              <h2 className="text-xl font-medium tracking-tight text-bone">Immutable Access Audit Trail</h2>
              <p className="text-xs text-warm-granite mt-0.5">
                Every AI Workbench query, document retrieval, and data ingestion is logged for compliance and security auditing.
              </p>
            </div>

            <div className="overflow-x-auto rounded-[6px] border border-carbon-lift bg-[#111111]">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-carbon-lift bg-carbon-lift/30 font-mono text-[11px] uppercase text-warm-granite">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Operator</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Query / Event Details</th>
                    <th className="px-4 py-3">Document Target</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-carbon-lift/50 font-mono">
                  {logsList.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-warm-granite">
                        No access logs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    logsList.map((log) => (
                      <tr key={log.id} className="hover:bg-carbon-lift/20 transition">
                        <td className="px-4 py-3 text-warm-granite text-[11px]">
                          {new Date(log.created_at).toLocaleDateString()} {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="px-4 py-3 text-bone font-semibold">
                          @{log.profile?.username || 'system'}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              'rounded px-1.5 py-0.5 text-[10px] uppercase font-bold',
                              log.profile?.role === 'admin' && 'text-purple-400 bg-purple-500/10',
                              log.profile?.role === 'tech' && 'text-blue-400 bg-blue-500/10',
                              log.profile?.role === 'finance' && 'text-emerald-400 bg-emerald-500/10',
                              log.profile?.role === 'support' && 'text-amber-400 bg-amber-500/10'
                            )}
                          >
                            {log.profile?.role || 'user'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              'rounded px-2 py-0.5 text-[10px] font-bold uppercase',
                              log.action === 'query' && 'bg-signal-orange/20 text-signal-orange',
                              log.action === 'upload' && 'bg-metric-green/20 text-metric-green',
                              log.action === 'view' && 'bg-blue-500/20 text-blue-400'
                            )}
                          >
                            {log.action}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-pale-stone text-xs max-w-md truncate font-sans">
                          {log.query_text || '—'}
                        </td>
                        <td className="px-4 py-3 text-warm-granite text-[11px]">
                          {log.document?.title || 'General Reasoning'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: ANALYTICS */}
        {activeTab === 'analytics' && (
          <div className="mt-6 space-y-6">
            <div>
              <h2 className="text-xl font-medium tracking-tight text-bone">Knowledge Telemetry & Activity Metrics</h2>
              <p className="text-xs text-warm-granite mt-0.5">
                Real-time usage statistics, departmental activity volume, and document corpus breakdown for {company?.name}.
              </p>
            </div>

            {/* Stat Cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <div className="flex items-center justify-between text-caption font-mono uppercase text-warm-granite">
                  <span>Provisioned Users</span>
                  <Users className="h-4 w-4 text-signal-orange" />
                </div>
                <div className="mt-3 text-3xl font-normal text-bone">{analyticsData.totalUsers}</div>
                <div className="mt-1 text-[11px] text-warm-granite font-mono">1 Admin · {analyticsData.totalUsers - 1} Specialists</div>
              </div>

              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <div className="flex items-center justify-between text-caption font-mono uppercase text-warm-granite">
                  <span>Indexed Documents</span>
                  <FileText className="h-4 w-4 text-metric-green" />
                </div>
                <div className="mt-3 text-3xl font-normal text-bone">{analyticsData.totalDocs}</div>
                <div className="mt-1 text-[11px] text-warm-granite font-mono">Across 3 Departmental Tiers</div>
              </div>

              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <div className="flex items-center justify-between text-caption font-mono uppercase text-warm-granite">
                  <span>Total Access Queries</span>
                  <MessageSquare className="h-4 w-4 text-blue-400" />
                </div>
                <div className="mt-3 text-3xl font-normal text-bone">{analyticsData.totalLogs}</div>
                <div className="mt-1 text-[11px] text-warm-granite font-mono">100% Local Inference</div>
              </div>

              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <div className="flex items-center justify-between text-caption font-mono uppercase text-warm-granite">
                  <span>RLS Security Enforced</span>
                  <ShieldCheck className="h-4 w-4 text-purple-400" />
                </div>
                <div className="mt-3 text-3xl font-normal text-metric-green">100%</div>
                <div className="mt-1 text-[11px] text-warm-granite font-mono">Zero Cross-Tenant Egress</div>
              </div>
            </div>

            {/* Visual breakdown grids */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Category Corpus Breakdown */}
              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <h3 className="text-sm font-semibold text-bone">Documents by Department</h3>
                <div className="mt-4 space-y-3">
                  {[
                    { cat: 'tech', label: 'Tech / Engineering', count: analyticsData.docCounts.tech || 0, color: 'bg-blue-500' },
                    { cat: 'finance', label: 'Finance / Operations', count: analyticsData.docCounts.finance || 0, color: 'bg-emerald-500' },
                    { cat: 'support', label: 'Support / SLA', count: analyticsData.docCounts.support || 0, color: 'bg-amber-500' },
                  ].map((item) => {
                    const pct = analyticsData.totalDocs > 0 ? (item.count / analyticsData.totalDocs) * 100 : 0;
                    return (
                      <div key={item.cat}>
                        <div className="flex items-center justify-between text-xs font-mono mb-1">
                          <span className="text-bone">{item.label}</span>
                          <span className="text-warm-granite">{item.count} docs ({Math.round(pct)}%)</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-carbon-lift overflow-hidden">
                          <div className={cn('h-full rounded-full', item.color)} style={{ width: `${Math.max(5, pct)}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Top Active Users */}
              <div className="rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
                <h3 className="text-sm font-semibold text-bone">Most Active Users (Queries & Views)</h3>
                <div className="mt-4 space-y-3">
                  {analyticsData.topUsers.length === 0 ? (
                    <div className="text-xs text-warm-granite py-4">No user activity recorded yet.</div>
                  ) : (
                    analyticsData.topUsers.slice(0, 5).map((u, i) => (
                      <div key={u.username} className="flex items-center justify-between border-b border-carbon-lift/40 pb-2 text-xs">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-warm-granite text-[11px]">#{i + 1}</span>
                          <span className="font-semibold text-bone">@{u.username}</span>
                          <span className="rounded bg-carbon-lift px-1.5 py-0.2 font-mono text-[10px] text-warm-granite uppercase">
                            {u.role}
                          </span>
                        </div>
                        <span className="font-mono text-signal-orange font-bold">{u.count} events</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* MODAL: CREATE USER */}
      {isCreateUserOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-[10px] border border-carbon-lift bg-[#141414] p-6 shadow-2xl">
            <h3 className="text-lg font-medium text-bone">Provision New Company User</h3>
            <p className="text-xs text-warm-granite mt-1">
              Create credentials for {company?.name}. Unique username & email will be verified in real time.
            </p>

            <form onSubmit={handleCreateUser} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Username</label>
                <div className="relative mt-1">
                  <input
                    type="text"
                    required
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. rohan_tech"
                    className="w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                  />
                  {checkingAvailability && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-warm-granite">
                      Checking...
                    </span>
                  )}
                  {usernameAvailable === true && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-metric-green">
                      ✓ Available
                    </span>
                  )}
                  {usernameAvailable === false && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-red-400">
                      ✗ Taken
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Email Address</label>
                <div className="relative mt-1">
                  <input
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="e.g. rohan@tatamotors-internal.com"
                    className="w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                  />
                  {emailAvailable === true && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-metric-green">
                      ✓ Available
                    </span>
                  )}
                  {emailAvailable === false && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-red-400">
                      ✗ Taken
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Full Name (Optional)</label>
                <input
                  type="text"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="e.g. Rohan Mehta"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Department Role (Access Scope)</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange cursor-pointer"
                >
                  <option value="tech">Tech (Only Tech Documents)</option>
                  <option value="finance">Finance (Only Finance Documents)</option>
                  <option value="support">Support (Only Support Documents)</option>
                  <option value="admin">Admin (Full Company Document Access)</option>
                </select>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateUserOpen(false)}
                  className="rounded-[3px] border border-carbon-lift px-3 py-2 text-xs text-warm-granite hover:text-bone transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting || usernameAvailable === false || emailAvailable === false}
                  className="rounded-[3px] bg-signal-orange px-4 py-2 text-xs font-semibold text-white transition hover:bg-signal-orange/90 disabled:opacity-50 cursor-pointer"
                >
                  {formSubmitting ? 'Creating...' : 'Provision User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EDIT USER */}
      {isEditUserOpen && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-[10px] border border-carbon-lift bg-[#141414] p-6 shadow-2xl">
            <h3 className="text-lg font-medium text-bone">Edit User @{selectedUser.username}</h3>
            <form onSubmit={handleEditUser} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Full Name</label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Role</label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                >
                  <option value="tech">Tech</option>
                  <option value="finance">Finance</option>
                  <option value="support">Support</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditUserOpen(false)}
                  className="rounded-[3px] border border-carbon-lift px-3 py-2 text-xs text-warm-granite hover:text-bone transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-[3px] bg-bone px-4 py-2 text-xs font-semibold text-obsidian-canvas transition hover:bg-chalk cursor-pointer"
                >
                  {formSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RESET PASSWORD */}
      {isResetPassOpen && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-[10px] border border-carbon-lift bg-[#141414] p-6 shadow-2xl">
            <h3 className="text-lg font-medium text-bone">Reset Password for @{selectedUser.username}</h3>
            <form onSubmit={handleResetPassword} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">New Password</label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 6 characters"
                  value={resetPassValue}
                  onChange={(e) => setResetPassValue(e.target.value)}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsResetPassOpen(false)}
                  className="rounded-[3px] border border-carbon-lift px-3 py-2 text-xs text-warm-granite hover:text-bone transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-[3px] bg-signal-orange px-4 py-2 text-xs font-semibold text-white transition hover:bg-signal-orange/90 cursor-pointer"
                >
                  {formSubmitting ? 'Resetting...' : 'Set Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: INGEST DOCUMENT */}
      {isUploadDocOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-xs">
          <div className="w-full max-w-xl rounded-[10px] border border-carbon-lift bg-[#141414] p-6 shadow-2xl">
            <h3 className="text-lg font-medium text-bone">Ingest Company Document</h3>
            <p className="text-xs text-warm-granite mt-1">
              Add technical specs, financial tables, or support protocols to the RAG vector corpus.
            </p>

            <form onSubmit={handleUploadDocument} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Document Title</label>
                <input
                  type="text"
                  required
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. Nexon EV Fast-Charging Specifications"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Department Category</label>
                <select
                  value={docCategory}
                  onChange={(e) => setDocCategory(e.target.value)}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange cursor-pointer"
                >
                  <option value="tech">Tech (Restricted to Tech Specialists)</option>
                  <option value="finance">Finance (Restricted to Finance Specialists)</option>
                  <option value="support">Support (Restricted to Support Specialists)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Document Content / Text</label>
                <textarea
                  rows={7}
                  required
                  value={docContent}
                  onChange={(e) => setDocContent(e.target.value)}
                  placeholder="Paste the full text of the document here. It will be automatically chunked and vectorized for RAG retrieval..."
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange font-sans leading-relaxed"
                />
              </div>

              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsUploadDocOpen(false)}
                  className="rounded-[3px] border border-carbon-lift px-3 py-2 text-xs text-warm-granite hover:text-bone transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="rounded-[3px] bg-bone px-4 py-2 text-xs font-semibold text-obsidian-canvas transition hover:bg-chalk cursor-pointer"
                >
                  {formSubmitting ? 'Ingesting...' : 'Ingest & Vectorize'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
