"use client";

import { Link } from "@tanstack/react-router";
import { motion, useScroll, useTransform } from "motion/react";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const links = [
  { label: "Product", to: "/" as const, hash: "product" },
  { label: "Security", to: "/" as const, hash: "security" },
  { label: "Models", to: "/" as const, hash: "models" },
  { label: "Workbench", to: "/chat" as const },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  const { scrollY } = useScroll();
  const bg = useTransform(scrollY, [0, 120], ["rgba(16,16,16,0)", "rgba(16,16,16,0.92)"]);
  const border = useTransform(scrollY, [0, 120], ["rgba(29,26,24,0)", "rgba(29,26,24,1)"]);

  return (
    <motion.header
      style={{ backgroundColor: bg, borderBottomColor: border }}
      className="fixed top-0 right-0 left-0 z-50 border-b backdrop-blur-[2px]"
    >
      <nav className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="status-pulse h-1.5 w-1.5 rounded-full bg-signal-orange" />
          <span className="eyebrow tracking-[0.22em] text-bone">BASTION</span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              {...("hash" in l ? { hash: l.hash } : {})}
              className="text-body-sm uppercase text-bone/80 transition-colors hover:text-chalk"
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/chat"
            className="hidden border border-ash-stroke px-4 py-2 text-body-sm text-bone transition-colors hover:border-chalk hover:text-chalk sm:inline-flex"
          >
            Open workbench →
          </Link>
          <Link
            to="/login"
            className="rounded-[3px] bg-chalk px-[14px] py-2 text-body-sm text-obsidian-canvas transition-opacity hover:opacity-90"
          >
            Log in
          </Link>
          <button
            type="button"
            aria-label="Toggle menu"
            onClick={() => setOpen((v) => !v)}
            className="md:hidden text-bone"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </nav>

      <div
        className={cn(
          "overflow-hidden border-t border-carbon-lift bg-obsidian-canvas md:hidden",
          open ? "max-h-72" : "max-h-0",
        )}
        style={{ transition: "max-height 300ms cubic-bezier(0.16,1,0.3,1)" }}
      >
        <div className="flex flex-col gap-4 px-6 py-6">
          {links.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              {...("hash" in l ? { hash: l.hash } : {})}
              onClick={() => setOpen(false)}
              className="text-body-sm uppercase text-bone/80"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </motion.header>
  );
}
