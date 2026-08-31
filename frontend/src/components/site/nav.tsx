"use client";

import { Link } from "@tanstack/react-router";
import { motion, useScroll, useTransform } from "motion/react";
import { Menu, X, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { BastionMark } from "@/components/site/parallax-hero";
import { HyperText } from "@/components/ui/hyper-text";
import { InteractiveHoverButton } from "@/components/ui/interactive-hover-button";
import { SlideTextButton } from "@/components/ui/slide-text-button";
import { useAuth } from "@/lib/auth-context";
import { UserAvatar } from "@/components/kokonutui/avatar-data";

const links = [
  { label: "Product", to: "/" as const, hash: "product" },
  { label: "Security", to: "/" as const, hash: "security" },
  { label: "Models", to: "/" as const, hash: "models" },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  const { user, profile, role } = useAuth();
  const { scrollY } = useScroll();
  const bg = useTransform(scrollY, [0, 120], ["rgba(16,16,16,0)", "rgba(16,16,16,0.92)"]);
  const border = useTransform(scrollY, [0, 120], ["rgba(29,26,24,0)", "rgba(29,26,24,1)"]);

  const handleScroll = (e: React.MouseEvent<HTMLAnchorElement>, hash?: string) => {
    if (!hash) return;
    if (typeof window !== "undefined" && window.location.pathname === "/") {
      e.preventDefault();
      const el = document.getElementById(hash);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        window.history.pushState(null, "", `#${hash}`);
      }
    }
  };

  const handleLogoClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (typeof window !== "undefined" && window.location.pathname === "/") {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
      window.history.pushState(null, "", "/");
    }
  };

  return (
    <motion.header
      style={{ backgroundColor: bg, borderBottomColor: border }}
      className="fixed top-0 right-0 left-0 z-50 border-b backdrop-blur-[2px]"
    >
      <nav className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <Link to="/" onClick={handleLogoClick} className="group flex items-center gap-2.5">
          <BastionMark
            className="h-5 w-5 transition-transform duration-300 group-hover:scale-110"
            color="var(--signal-orange)"
          />
          <HyperText
            as="span"
            duration={600}
            className="eyebrow tracking-[0.22em] text-bone py-0 text-xs font-semibold inline-flex items-center select-none"
            animateOnHover={true}
            startOnView={false}
          >
            BASTION
          </HyperText>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              {...("hash" in l ? { hash: l.hash } : {})}
              onClick={(e) => handleScroll(e, l.hash)}
              className="text-body-sm uppercase text-bone/80 transition-colors hover:text-chalk"
            >
              {l.label}
            </Link>
          ))}
          {role === "admin" && (
            <Link
              to="/admin"
              className="flex items-center gap-1 text-body-sm uppercase text-signal-orange font-semibold transition-colors hover:text-signal-orange/80"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Admin
            </Link>
          )}
        </div>

        <div className="flex items-center gap-3">
          <InteractiveHoverButton
            to={user ? "/chat" : "/login"}
            text="Open workbench"
            className="hidden sm:inline-flex h-9 px-4 text-body-sm rounded-md"
          />

          {user && profile ? (
            <Link
              to="/profile"
              className="flex items-center gap-2 rounded-md border border-carbon-lift bg-carbon-lift/50 px-2.5 py-1 text-xs text-bone hover:border-ash-stroke transition"
            >
              <UserAvatar
                avatarUrl={profile.avatar_url}
                username={profile.username}
                size={22}
                className="h-5.5 w-5.5"
              />
              <span className="hidden sm:inline">@{profile.username}</span>
            </Link>
          ) : (
            <SlideTextButton to="/login" text="Log in" className="h-9 px-4 rounded-md" />
          )}

          <button
            type="button"
            aria-label="Toggle menu"
            onClick={() => setOpen((v) => !v)}
            className="md:hidden text-bone cursor-pointer"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </nav>

      <div
        className={cn(
          "overflow-hidden border-t border-carbon-lift bg-obsidian-canvas md:hidden",
          open ? "max-h-96" : "max-h-0",
        )}
        style={{ transition: "max-height 300ms cubic-bezier(0.16,1,0.3,1)" }}
      >
        <div className="flex flex-col gap-4 px-6 py-6">
          {links.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              {...("hash" in l ? { hash: l.hash } : {})}
              onClick={(e) => {
                setOpen(false);
                handleScroll(e, l.hash);
              }}
              className="text-body-sm uppercase text-bone/80 transition-colors hover:text-chalk"
            >
              {l.label}
            </Link>
          ))}
          {role === "admin" && (
            <Link
              to="/admin"
              onClick={() => setOpen(false)}
              className="flex items-center gap-1.5 text-body-sm uppercase text-signal-orange font-semibold"
            >
              <ShieldCheck className="h-4 w-4" />
              Admin Console
            </Link>
          )}
          <InteractiveHoverButton
            to={user ? "/chat" : "/login"}
            text="Open workbench"
            onClick={() => setOpen(false)}
            className="mt-2 w-full h-10"
          />
        </div>
      </div>
    </motion.header>
  );
}
