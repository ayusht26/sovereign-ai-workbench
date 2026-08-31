"use client";

import { LogOut, ShieldCheck, Sliders, User } from "lucide-react";
import { Link, useNavigate } from "@tanstack/react-router";
import * as React from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { UserAvatar } from "./avatar-data";

export interface ProfileDropdownProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export default function ProfileDropdown({
  className,
  ...props
}: ProfileDropdownProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const { user, profile, company, role, logout } = useAuth();
  const navigate = useNavigate();

  if (!profile) return null;

  const displayName = profile.full_name || `@${profile.username}`;
  const companyName = company?.name || "Tata Motors";

  const handleSignOut = async () => {
    await logout();
    navigate({ to: "/login" });
  };

  const getRoleBadgeClasses = (userRole?: string | null) => {
    switch (userRole) {
      case "admin":
        return "border-purple-500/30 bg-purple-500/10 text-purple-400";
      case "tech":
        return "border-blue-500/30 bg-blue-500/10 text-blue-400";
      case "finance":
        return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
      case "support":
        return "border-amber-500/30 bg-amber-500/10 text-amber-400";
      default:
        return "border-carbon-lift bg-carbon-lift text-warm-granite";
    }
  };

  return (
    <div className={cn("relative inline-block", className)} {...props}>
      <DropdownMenu onOpenChange={setIsOpen}>
        <div className="group relative">
          <DropdownMenuTrigger asChild>
            <button
              className="flex h-9 items-center gap-2.5 rounded-full border border-carbon-lift bg-[#121212]/90 pl-3.5 pr-1.5 transition-all duration-200 hover:border-ash-stroke hover:bg-[#181818] hover:shadow-md focus:outline-none cursor-pointer select-none"
              type="button"
              aria-label="User profile menu"
            >
              <span className="font-medium text-xs text-bone tracking-tight truncate max-w-[130px] md:max-w-[160px]">
                {displayName}
              </span>
              <div className="relative shrink-0">
                <div className="h-6.5 w-6.5 rounded-full bg-gradient-to-br from-signal-orange via-purple-500 to-blue-500 p-0.5 shadow-sm">
                  <div className="h-full w-full overflow-hidden rounded-full bg-[#121212] flex items-center justify-center">
                    <UserAvatar
                      avatarUrl={profile.avatar_url}
                      username={profile.username}
                      size={22}
                      className="h-full w-full"
                    />
                  </div>
                </div>
              </div>
            </button>
          </DropdownMenuTrigger>

          {/* Bending line indicator on the right */}
          <div
            className={cn(
              "absolute top-1/2 -right-3 -translate-y-1/2 transition-all duration-200 pointer-events-none hidden sm:block",
              isOpen ? "opacity-100" : "opacity-40 group-hover:opacity-100"
            )}
          >
            <svg
              aria-hidden="true"
              className={cn(
                "transition-all duration-200",
                isOpen
                  ? "scale-110 text-signal-orange"
                  : "text-warm-granite group-hover:text-bone"
              )}
              fill="none"
              height="20"
              viewBox="0 0 12 24"
              width="10"
            >
              <path
                d="M2 4C6 8 6 16 2 20"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeWidth="1.5"
              />
            </svg>
          </div>

          <DropdownMenuContent
            align="end"
            className="w-60 origin-top-right rounded-2xl border border-carbon-lift bg-[#121212]/95 p-2 shadow-2xl backdrop-blur-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 z-50 text-bone"
            sideOffset={8}
          >
            {/* Header info in dropdown */}
            <div className="px-3 py-2 border-b border-carbon-lift/60 mb-1">
              <div className="text-xs font-semibold text-bone truncate">{displayName}</div>
              <div className="text-[10px] font-mono text-warm-granite truncate">
                {user?.email || `@${profile.username}`} · {companyName}
              </div>
            </div>

            <div className="space-y-1">
              {/* Profile Link */}
              <DropdownMenuItem asChild>
                <Link
                  to="/profile"
                  className="group flex cursor-pointer items-center rounded-xl border border-transparent p-2.5 transition-all duration-200 hover:border-carbon-lift hover:bg-carbon-lift/50 text-warm-granite hover:text-bone"
                >
                  <div className="flex flex-1 items-center gap-2.5">
                    <User className="h-4 w-4 text-signal-orange" />
                    <span className="whitespace-nowrap font-medium text-xs text-bone leading-tight tracking-tight">
                      Profile
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-warm-granite/70 group-hover:text-warm-granite">
                    Edit
                  </span>
                </Link>
              </DropdownMenuItem>

              {/* Role Info Item */}
              <DropdownMenuItem asChild>
                <Link
                  to="/profile"
                  className="group flex cursor-pointer items-center rounded-xl border border-transparent p-2.5 transition-all duration-200 hover:border-carbon-lift hover:bg-carbon-lift/50 text-warm-granite hover:text-bone"
                >
                  <div className="flex flex-1 items-center gap-2.5">
                    <ShieldCheck className="h-4 w-4 text-metric-green" />
                    <span className="whitespace-nowrap font-medium text-xs text-bone leading-tight tracking-tight">
                      Role
                    </span>
                  </div>
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase border",
                      getRoleBadgeClasses(role)
                    )}
                  >
                    {role || "guest"}
                  </span>
                </Link>
              </DropdownMenuItem>

              {/* Admin Console Link (if admin) */}
              {role === "admin" && (
                <DropdownMenuItem asChild>
                  <Link
                    to="/admin"
                    className="group flex cursor-pointer items-center rounded-xl border border-transparent p-2.5 transition-all duration-200 hover:border-purple-500/20 hover:bg-purple-500/10 text-purple-300"
                  >
                    <div className="flex flex-1 items-center gap-2.5">
                      <Sliders className="h-4 w-4 text-purple-400" />
                      <span className="whitespace-nowrap font-medium text-xs text-purple-200 leading-tight tracking-tight">
                        Admin Console
                      </span>
                    </div>
                    <span className="rounded px-1.5 py-0.2 font-mono text-[9px] font-semibold uppercase bg-purple-500/20 text-purple-300">
                      Manage
                    </span>
                  </Link>
                </DropdownMenuItem>
              )}
            </div>

            <DropdownMenuSeparator className="my-2 bg-carbon-lift" />

            {/* Sign Out Button */}
            <DropdownMenuItem asChild>
              <button
                onClick={handleSignOut}
                className="group flex w-full cursor-pointer items-center gap-2.5 rounded-xl border border-transparent bg-red-500/10 p-2.5 transition-all duration-200 hover:border-red-500/30 hover:bg-red-500/20"
                type="button"
              >
                <LogOut className="h-4 w-4 text-red-400 group-hover:text-red-300" />
                <span className="font-medium text-red-400 text-xs group-hover:text-red-300">
                  Sign Out
                </span>
              </button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </div>
      </DropdownMenu>
    </div>
  );
}
