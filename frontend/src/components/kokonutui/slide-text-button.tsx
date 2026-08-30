"use client";

/**
 * @author: @kokonut-labs
 * @description: Slide Text Button with animated vertical text transition
 * @version: 1.0.0
 * @date: 2025-11-02
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 */

import React from "react";
import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

export interface SlideTextButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text?: string;
  hoverText?: string;
  to?: string;
  href?: string;
  className?: string;
  variant?: "default" | "ghost" | "dark" | "outline";
}

export default function SlideTextButton({
  text = "Browse Components",
  hoverText,
  to,
  href,
  className,
  variant = "default",
  children,
  onClick,
  ...props
}: SlideTextButtonProps) {
  const displayText = text || (typeof children === "string" ? children : "Button");
  const slideText = hoverText ?? displayText;

  const variantStyles =
    variant === "ghost"
      ? "border border-carbon-lift text-bone hover:bg-carbon-lift/50"
      : variant === "outline"
        ? "border border-ash-stroke text-bone hover:border-chalk hover:text-chalk"
        : variant === "dark"
          ? "bg-obsidian-canvas text-bone border border-carbon-lift hover:bg-carbon-lift"
          : "bg-chalk text-obsidian-canvas hover:bg-chalk/90";

  const content = (
    <span className="relative inline-flex h-5 items-center justify-center overflow-hidden">
      <span className="inline-flex items-center justify-center font-medium transition-all duration-200 ease-out group-hover:-translate-y-full group-hover:opacity-0">
        {displayText}
      </span>
      <span className="absolute top-full inline-flex items-center justify-center font-medium opacity-0 transition-all duration-200 ease-out group-hover:-translate-y-full group-hover:opacity-100">
        {slideText}
      </span>
    </span>
  );

  const buttonClasses = cn(
    "group relative inline-flex h-9 items-center justify-center overflow-hidden rounded-md px-5 font-medium text-body-sm tracking-tight transition-all duration-200 cursor-pointer select-none",
    variantStyles,
    className,
  );

  if (to) {
    return (
      <div className="relative inline-block">
        <Link to={to} className={buttonClasses} onClick={onClick as any}>
          {content}
        </Link>
      </div>
    );
  }

  if (href) {
    return (
      <div className="relative inline-block">
        <a href={href} className={buttonClasses} onClick={onClick as any}>
          {content}
        </a>
      </div>
    );
  }

  return (
    <div className="relative inline-block w-full">
      <button
        type={props.type || "button"}
        className={cn("w-full", buttonClasses)}
        onClick={onClick}
        {...props}
      >
        {content}
      </button>
    </div>
  );
}

export { SlideTextButton };
