import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { motion } from 'motion/react';
import {
  User,
  ShieldCheck,
  KeyRound,
  Camera,
  LogOut,
  Building,
  ArrowLeft,
  Calendar,
  Sparkles,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Nav } from '@/components/site/nav';
import AvatarPicker from '@/components/kokonutui/avatar-picker';
import { UserAvatar } from '@/components/kokonutui/avatar-data';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

export const Route = createFileRoute('/profile')({
  head: () => ({
    meta: [
      { title: 'User Profile — Bastion Sovereign Workbench' },
      {
        name: 'description',
        content: 'Manage your local profile credentials, avatar, and view your assigned company role and permissions.',
      },
    ],
  }),
  component: ProfilePage,
});

function ProfilePage() {
  const navigate = useNavigate();
  const { user, profile, company, role, loading, logout, updateProfile, updatePassword } = useAuth();

  // Modal state for Avatar Picker Window
  const [isAvatarPickerOpen, setIsAvatarPickerOpen] = useState(false);
  const [isSavingAvatar, setIsSavingAvatar] = useState(false);

  // Form states for Name and Password
  const [fullName, setFullName] = useState(profile?.full_name || '');
  const [isUpdatingName, setIsUpdatingName] = useState(false);

  const [currentPass, setCurrentPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [isUpdatingPass, setIsUpdatingPass] = useState(false);

  useEffect(() => {
    if (profile?.full_name) {
      setFullName(profile.full_name);
    }
  }, [profile?.full_name]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-obsidian-canvas text-bone">
        <div className="flex items-center gap-3 font-mono text-sm">
          <span className="h-2 w-2 rounded-full bg-signal-orange animate-ping" />
          Loading user profile...
        </div>
      </div>
    );
  }

  if (!user || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-obsidian-canvas px-4 text-bone">
        <div className="max-w-md rounded-[10px] border border-carbon-lift bg-[#141414] p-8 text-center">
          <User className="mx-auto h-12 w-12 text-warm-granite" />
          <h1 className="mt-4 text-heading tracking-[-0.031em]">Not Signed In</h1>
          <p className="mt-2 text-body-sm text-warm-granite">
            Sign in with your company credentials to manage your avatar and password.
          </p>
          <div className="mt-6">
            <Link
              to="/login"
              className="inline-flex rounded-[3px] bg-bone px-5 py-2.5 text-xs font-semibold text-obsidian-canvas hover:bg-chalk transition"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Handle saving chosen Avatar (Preset or Custom URL)
  const handleSaveAvatar = async (avatarUrl: string) => {
    setIsSavingAvatar(true);
    try {
      const { error } = await updateProfile({ avatar_url: avatarUrl });
      if (error) {
        toast.error(error.message || 'Failed to save avatar');
        return;
      }
      toast.success('Avatar updated successfully!');
      setIsAvatarPickerOpen(false);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to save avatar');
    } finally {
      setIsSavingAvatar(false);
    }
  };

  // Handle uploading custom file to Supabase storage
  const handleUploadCustomFile = async (file: File): Promise<string | void> => {
    if (!user) return;
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Avatar image must be smaller than 2MB');
      return;
    }

    try {
      const fileExt = file.name.split('.').pop() || 'png';
      const filePath = `${user.id}/avatar_${Date.now()}.${fileExt}`;

      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true });

      if (uploadError) {
        // Storage bucket fallback -> Data URL
        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => {
            resolve(reader.result as string);
          };
          reader.readAsDataURL(file);
        });
      }

      const { data: urlData } = supabase.storage.from('avatars').getPublicUrl(filePath);
      return urlData.publicUrl;
    } catch (err: any) {
      toast.error(err?.message || 'Failed to upload avatar image');
    }
  };

  // Handle Full Name Update
  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingName(true);
    try {
      const { error } = await updateProfile({ full_name: fullName.trim() });
      if (error) {
        toast.error(error.message || 'Failed to update name');
        return;
      }
      toast.success('Profile name updated successfully');
    } finally {
      setIsUpdatingName(false);
    }
  };

  // Handle Password Update
  const handleSavePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPass.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    if (newPass !== confirmPass) {
      toast.error('New passwords do not match');
      return;
    }

    setIsUpdatingPass(true);
    try {
      const { error } = await updatePassword(newPass);
      if (error) {
        toast.error(error.message || 'Password update failed');
        return;
      }
      toast.success('Password changed successfully');
      setNewPass('');
      setConfirmPass('');
      setCurrentPass('');
    } finally {
      setIsUpdatingPass(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-canvas text-bone">
      <Nav />

      <main className="mx-auto max-w-4xl px-6 pt-28 pb-20">
        {/* Back Link */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 text-xs font-mono uppercase text-warm-granite hover:text-bone transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Workbench
          </Link>

          {role === 'admin' && (
            <Link
              to="/admin"
              className="inline-flex items-center gap-1.5 rounded-[3px] border border-signal-orange/30 bg-signal-orange/10 px-3 py-1 text-xs font-mono font-semibold text-signal-orange hover:bg-signal-orange/20 transition"
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Admin Console
            </Link>
          )}
        </div>

        {/* Profile Card Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="rounded-[12px] border border-carbon-lift bg-[#121212] p-6 md:p-8 shadow-xl"
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-5">
              {/* Interactive Avatar Icon — click opens Avatar Picker window */}
              <div
                className="relative group shrink-0 cursor-pointer"
                onClick={() => setIsAvatarPickerOpen(true)}
                title="Click to choose or upload avatar"
              >
                <div className="h-20 w-20 rounded-full bg-gradient-to-br from-signal-orange via-purple-500 to-blue-500 p-0.5 shadow-lg transition-transform duration-200 group-hover:scale-105">
                  <div className="h-full w-full overflow-hidden rounded-full bg-[#121212] flex items-center justify-center">
                    <UserAvatar
                      avatarUrl={profile.avatar_url}
                      username={profile.username}
                      size={76}
                      className="h-full w-full"
                    />
                  </div>
                </div>
                <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 opacity-0 transition group-hover:opacity-100">
                  <Camera className="h-6 w-6 text-white" />
                </div>
              </div>

              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-xl md:text-2xl font-semibold tracking-tight text-bone">
                    @{profile.username}
                  </h1>
                  <span
                    className={cn(
                      'rounded px-2 py-0.5 font-mono text-[11px] font-bold uppercase border',
                      role === 'admin' && 'bg-purple-500/20 text-purple-400 border-purple-500/30',
                      role === 'tech' && 'bg-blue-500/20 text-blue-400 border-blue-500/30',
                      role === 'finance' && 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
                      role === 'support' && 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                    )}
                  >
                    {role || 'user'}
                  </span>
                </div>
                <p className="text-sm text-warm-granite mt-1">
                  {profile.full_name || 'No display name set'}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-4 text-xs font-mono text-warm-granite">
                  <span className="flex items-center gap-1.5 text-pale-stone">
                    <Building className="h-3.5 w-3.5 text-signal-orange" />
                    {company?.name || 'Tata Motors'}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    Joined {new Date(profile.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={async () => {
                await logout();
                navigate({ to: '/login' });
              }}
              className="flex items-center gap-2 rounded-[3px] border border-carbon-lift px-4 py-2 text-xs text-warm-granite hover:border-red-500/40 hover:text-red-400 transition cursor-pointer self-start sm:self-center"
            >
              <LogOut className="h-3.5 w-3.5" /> Sign Out
            </button>
          </div>
        </motion.div>

        {/* Role Permissions Scope Notice */}
        <div className="mt-6 rounded-[8px] border border-carbon-lift bg-[#111111] p-5">
          <div className="flex items-center gap-2 text-xs font-mono uppercase text-warm-granite">
            <ShieldCheck className="h-4 w-4 text-metric-green" />
            Active Role Access Boundary (Row Level Security)
          </div>
          <div className="mt-2 text-xs text-pale-stone leading-relaxed font-mono">
            {role === 'admin' && (
              <p>
                As an <strong>Administrator</strong> for <strong>{company?.name || 'Tata Motors'}</strong>, you have read, write, and provisioning authority across all technical, financial, and operational corpora.
              </p>
            )}
            {role === 'tech' && (
              <p>
                As a <strong>Tech Specialist</strong>, Postgres RLS restricts your document retrieval and vector searches strictly to documents tagged with category <span className="text-signal-orange">tech</span>. Financial and executive notes remain cryptographically isolated.
              </p>
            )}
            {role === 'finance' && (
              <p>
                As a <strong>Finance Specialist</strong>, Postgres RLS restricts your document retrieval strictly to documents tagged with category <span className="text-signal-orange">finance</span>. Engineering schematics remain cryptographically isolated.
              </p>
            )}
            {role === 'support' && (
              <p>
                As a <strong>Support Specialist</strong>, Postgres RLS restricts your document retrieval strictly to documents tagged with category <span className="text-signal-orange">support</span>. Internal financial and engineering documents remain isolated.
              </p>
            )}
          </div>
        </div>

        {/* Two Column Settings Grid */}
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          {/* Display Information */}
          <div className="rounded-[10px] border border-carbon-lift bg-[#121212] p-6 shadow-lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-bone">
              <User className="h-4 w-4 text-signal-orange" />
              Display Information
            </div>
            <p className="mt-1 text-xs text-warm-granite">
              Your name displayed across audit logs and session runs.
            </p>

            <form onSubmit={handleSaveName} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Username (Immutable)</label>
                <input
                  type="text"
                  disabled
                  value={profile.username}
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-carbon-lift/30 px-3 py-2 text-xs text-warm-granite font-mono cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Rohan Mehta"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isUpdatingName}
                  className="rounded-[3px] bg-bone px-4 py-2 text-xs font-semibold text-obsidian-canvas transition hover:bg-chalk disabled:opacity-50 cursor-pointer"
                >
                  {isUpdatingName ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>

          {/* Change Password */}
          <div className="rounded-[10px] border border-carbon-lift bg-[#121212] p-6 shadow-lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-bone">
              <KeyRound className="h-4 w-4 text-signal-orange" />
              Security & Password
            </div>
            <p className="mt-1 text-xs text-warm-granite">
              Change your password. Credentials never leave the local node network.
            </p>

            <form onSubmit={handleSavePassword} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">New Password</label>
                <input
                  type="password"
                  required
                  value={newPass}
                  onChange={(e) => setNewPass(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-warm-granite">Confirm New Password</label>
                <input
                  type="password"
                  required
                  value={confirmPass}
                  onChange={(e) => setConfirmPass(e.target.value)}
                  placeholder="Repeat new password"
                  className="mt-1 w-full rounded-[3px] border border-carbon-lift bg-[#181818] px-3 py-2 text-xs text-bone outline-none focus:border-signal-orange"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isUpdatingPass}
                  className="rounded-[3px] bg-signal-orange px-4 py-2 text-xs font-semibold text-white transition hover:bg-signal-orange/90 disabled:opacity-50 cursor-pointer"
                >
                  {isUpdatingPass ? 'Updating Password...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>

      {/* Avatar Picker Modal / Window */}
      <Dialog open={isAvatarPickerOpen} onOpenChange={setIsAvatarPickerOpen}>
        <DialogContent className="max-w-[460px] border-carbon-lift bg-[#121212] text-bone p-6 sm:p-8 shadow-2xl">
          <DialogHeader className="text-center sm:text-center space-y-1">
            <DialogTitle className="text-lg md:text-xl font-semibold tracking-tight text-bone">
              Pick Your Avatar
            </DialogTitle>
            <DialogDescription className="text-xs md:text-sm text-warm-granite">
              Choose a sovereign preset or upload your own avatar
            </DialogDescription>
          </DialogHeader>

          <div className="pt-2">
            <AvatarPicker
              currentAvatarUrl={profile.avatar_url}
              username={profile.username}
              onSaveAvatar={handleSaveAvatar}
              onUploadCustomFile={handleUploadCustomFile}
              isSubmitting={isSavingAvatar}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
