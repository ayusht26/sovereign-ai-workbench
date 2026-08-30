import React from "react";
import { ArrowRight } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

export interface InteractiveHoverButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text?: string;
  to?: string;
  href?: string;
}

const InteractiveHoverButton = React.forwardRef<
  HTMLButtonElement,
  InteractiveHoverButtonProps
>(({ text = "Button", children, className, to, href, onClick, ...props }, ref) => {
  const content = text || (typeof children === "string" ? children : "Button");

  const inner = (
    <>
      {/* Unhovered text with left spacing for indicator dot */}
      <span className="inline-flex items-center gap-2 pl-3.5 pr-1 transition-all duration-200 ease-out group-hover:translate-x-10 group-hover:opacity-0 whitespace-nowrap select-none">
        {content}
      </span>

      {/* Hover text & arrow container: guaranteed single-line, centered, smooth slide */}
      <div className="absolute inset-0 z-10 flex h-full w-full items-center justify-center gap-2 px-3 font-medium text-obsidian-canvas opacity-0 transition-all duration-200 ease-out translate-x-4 group-hover:translate-x-0 group-hover:opacity-100 whitespace-nowrap select-none">
        <span className="whitespace-nowrap">{content}</span>
        <ArrowRight className="h-4 w-4 shrink-0 transition-transform duration-200 group-hover:translate-x-0.5" />
      </div>

      {/* Smooth expanding circle: pure scale transform clipped by parent overflow-hidden with zero corner snapping */}
      <div className="absolute left-3.5 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-signal-orange pointer-events-none transition-transform duration-300 ease-out group-hover:scale-[65] group-hover:bg-chalk origin-center" />
    </>
  );

  const buttonClasses = cn(
    "group relative inline-flex h-9 min-w-fit cursor-pointer items-center justify-center overflow-hidden rounded-md border border-ash-stroke bg-obsidian-canvas px-4 text-center text-body-sm font-medium text-bone transition-colors duration-200 hover:border-chalk select-none whitespace-nowrap",
    className,
  );

  if (to) {
    return (
      <Link to={to} className={buttonClasses} onClick={onClick as any}>
        {inner}
      </Link>
    );
  }

  if (href) {
    return (
      <a href={href} className={buttonClasses} onClick={onClick as any}>
        {inner}
      </a>
    );
  }

  return (
    <button ref={ref} className={buttonClasses} onClick={onClick} {...props}>
      {inner}
    </button>
  );
});

InteractiveHoverButton.displayName = "InteractiveHoverButton";

function InteractiveHoverButtonDemo() {
  return (
    <div className="relative justify-center">
      <InteractiveHoverButton />
    </div>
  );
}

export { InteractiveHoverButton, InteractiveHoverButtonDemo };
