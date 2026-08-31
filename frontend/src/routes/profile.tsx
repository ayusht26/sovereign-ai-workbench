import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { motion } from 'motion/react';
import {
  User,
  ShieldCheck,
  KeyRound,
  Camera,
  LogOut,
  Building,
  Check,
  ArrowLeft,
  Lock,
  Mail,
  Calendar,
  Sparkles,
} from 'lucide-react';
import { useState, useRef } from 'react';
import { useAuth } from '@/lib/auth-context';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Nav } from '@/components/site/nav';
import { Eyebrow } from '@/components/site/reveal';
import { SlideTextButton } from '@/components/ui/slide-text-button';

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
  const fileInputRef = useRef(null);

  // Form states
  const [fullName, setFullName] = useState(profile?.full_name || '');
  const [isUpdatingName, setIsUpdatingName] = useState(false);

  const [currentPass, setCurrentPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [isUpdatingPass, setIsUpdatingPass] = useState(false);

  const [avatarUploading, setAvatarUploading] = useState(false);

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

  // Handle Full Name Update
  const handleSaveName = async (e) => {
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
  const handleSavePassword = async (e) => {
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

  // Handle Avatar Upload
  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;

    if (file.size > 2 * 1024 * 1024) {
      toast.error('Avatar image must be smaller than 2MB');
      return;
    }

    setAvatarUploading(true);
    try {
      const fileExt = file.name.split('.').pop() || 'png';
      const filePath = `${user.id}/avatar_${Date.now()}.${fileExt}`;

      // Upload to Supabase avatars bucket
      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true });

      if (uploadError) {
        // If storage bucket isn't configured, store data URL as preview
        const reader = new FileReader();
        reader.onload = async () => {
          const dataUrl = reader.result;
          await updateProfile({ avatar_url: dataUrl });
          toast.success('Avatar preview updated');
        };
        reader.readAsDataURL(file);
        return;
      }

      // Get public URL
      const { data: urlData } = supabase.storage.from('avatars').getPublicUrl(filePath);
      const publicUrl = urlData.publicUrl;

      await updateProfile({ avatar_url: publicUrl });
      toast.success('Avatar uploaded and updated!');
    } catch (err) {
      toast.error(err?.message || 'Failed to upload avatar');
    } finally {
      setAvatarUploading(false);
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
          className="rounded-[10px] border border-carbon-lift bg-[#121212] p-6 md:p-8"
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-5">
              {/* Avatar with upload button */}
              <div className="relative group">
                <div className="flex h-20 w-20 overflow-hidden items-center justify-center rounded-full border-2 border-ash-stroke bg-carbon-lift text-xl font-bold text-bone">
                  {profile.avatar_url ? (
                    <img
                      src={profile.avatar_url}
                      alt={profile.username}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span>{profile.username.slice(0, 2).toUpperCase()}</span>
                  )}
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={avatarUploading}
                  className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 opacity-0 transition group-hover:opacity-100 cursor-pointer"
                  title="Upload new avatar"
                >
                  <Camera className="h-6 w-6 text-white" />
                </button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleAvatarChange}
                  accept="image/*"
                  className="hidden"
                />
              </div>

              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold tracking-tight text-bone">
                    @{profile.username}
                  </h1>
                  <span
                    className={cn(
                      'rounded px-2 py-0.5 font-mono text-[11px] font-bold uppercase',
                      role === 'admin' && 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
                      role === 'tech' && 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
                      role === 'finance' && 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
                      role === 'support' && 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    )}
                  >
                    {role}
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
              onClick={() => {
                logout();
                navigate({ to: '/login' });
              }}
              className="flex items-center gap-2 rounded-[3px] border border-carbon-lift px-4 py-2 text-xs text-warm-granite hover:border-red-500/40 hover:text-red-400 transition cursor-pointer"
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
                As an <strong>Administrator</strong> for <strong>{company?.name}</strong>, you have read, write, and provisioning authority across all technical, financial, and operational corpora.
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
          {/* Update Display Name */}
          <div className="rounded-[10px] border border-carbon-lift bg-[#121212] p-6">
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
          <div className="rounded-[10px] border border-carbon-lift bg-[#121212] p-6">
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
    </div>
  );
}
