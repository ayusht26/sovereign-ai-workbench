"use client";

/**
 * @author: @dorianbaffier
 * @description: Card Flip (Bastion Edition)
 * @version: 1.0.0
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 */

import { ArrowRight, Sparkles, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export interface CardFlipProps {
  title?: string;
  subtitle?: string;
  description?: string;
  features?: string[];
  actionLabel?: string;
  className?: string;
  icon?: LucideIcon | React.ComponentType<{ className?: string }>;
}

export default function CardFlip({
  title = "Design Systems",
  subtitle = "Explore the fundamentals",
  description = "Dive deep into the world of modern UI/UX design.",
  features = ["UI/UX", "Modern Design", "Tailwind CSS", "Kokonut UI"],
  actionLabel = "Inspect tier",
  className,
  icon: Icon,
}: CardFlipProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div
      className={cn(
        "group relative h-[340px] w-full max-w-[270px] [perspective:2000px] select-none",
        className,
      )}
      onMouseEnter={() => setIsFlipped(true)}
      onMouseLeave={() => setIsFlipped(false)}
      onClick={() => setIsFlipped((prev) => !prev)}
    >
      <div
        className={cn(
          "relative h-full w-full",
          "[transform-style:preserve-3d]",
          "transition-[transform] duration-500 ease-[cubic-bezier(0.77,0,0.175,1)]",
          "motion-reduce:transition-none cursor-pointer",
          isFlipped ? "[transform:rotateY(180deg)]" : "[transform:rotateY(0deg)]",
        )}
      >
        {/* Front of card */}
        <div
          className={cn(
            "absolute inset-0 h-full w-full",
            "[backface-visibility:hidden] [transform:rotateY(0deg)]",
            "overflow-hidden rounded-2xl",
            "bg-gradient-to-b from-[#141414] to-[#0a0a0a]",
            "border border-carbon-lift",
            "shadow-lg",
            "transition-all duration-500",
            "group-hover:border-ash-stroke group-hover:shadow-[0_8px_30px_rgba(0,0,0,0.6)]",
          )}
        >
          {/* Ambient Glowing Rings Visual */}
          <div className="relative h-full overflow-hidden bg-gradient-to-b from-carbon-lift/30 to-obsidian-canvas">
            <div
              aria-hidden="true"
              className="absolute inset-0 flex items-start justify-center pt-20"
            >
              <div className="relative flex h-[100px] w-[200px] items-center justify-center">
                {[...Array(8)].map((_, i) => (
                  <div
                    className={cn(
                      "absolute h-[50px] w-[50px]",
                      "rounded-[140px]",
                      "animate-[scale_3s_linear_infinite]",
                      "motion-reduce:animate-none",
                      "opacity-0",
                      "shadow-[0_0_40px_rgba(235,94,40,0.35)]",
                      "group-hover:animate-[scale_2s_linear_infinite]",
                    )}
                    key={i}
                    style={{
                      animationDelay: `${i * 0.35}s`,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Front Bottom Info */}
          <div className="absolute right-0 bottom-0 left-0 p-5 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a]/95 to-transparent pt-8">
            <div className="flex items-center justify-between gap-3">
              <div className="space-y-1">
                <h3 className="font-medium text-base text-bone leading-snug tracking-tight transition-transform duration-500 ease-out-expo group-hover:translate-y-[-2px]">
                  {title}
                </h3>
                <p className="line-clamp-1 font-mono text-xs text-warm-granite tracking-tight transition-transform delay-[50ms] duration-500 ease-out-expo group-hover:translate-y-[-2px]">
                  {subtitle}
                </p>
              </div>
              <div className="group/icon relative shrink-0">
                <div
                  className={cn(
                    "absolute inset-[-6px] rounded-lg transition-opacity duration-300",
                    "bg-gradient-to-br from-signal-orange/20 via-signal-orange/10 to-transparent",
                  )}
                />
                {Icon ? (
                  <Icon
                    aria-hidden="true"
                    className="relative z-10 h-4 w-4 text-signal-orange transition-transform duration-300 group-hover/icon:scale-110"
                  />
                ) : (
                  <Sparkles
                    aria-hidden="true"
                    className="relative z-10 h-4 w-4 text-signal-orange transition-transform duration-300 group-hover/icon:scale-110"
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Back of card */}
        <div
          className={cn(
            "absolute inset-0 h-full w-full",
            "[backface-visibility:hidden] [transform:rotateY(180deg)]",
            "rounded-2xl p-5",
            "bg-gradient-to-b from-[#141414] to-[#0a0a0a]",
            "border border-carbon-lift",
            "shadow-lg",
            "flex flex-col justify-between",
            "transition-all duration-500",
            "group-hover:border-signal-orange/60 group-hover:shadow-[0_8px_30px_rgba(0,0,0,0.7)]",
          )}
        >
          <div className="space-y-4">
            <div className="space-y-1.5 border-b border-carbon-lift/60 pb-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-sm text-bone tracking-tight">
                  {title}
                </h3>
                <span className="font-mono text-[0.65rem] text-signal-orange uppercase tracking-wider">
                  Details
                </span>
              </div>
              <p className="text-xs text-warm-granite leading-relaxed">
                {description}
              </p>
            </div>

            <div className="space-y-2">
              {features.map((feature, index) => (
                <div
                  className="flex items-center gap-2 text-xs text-pale-stone transition-[transform,opacity] duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]"
                  key={feature}
                  style={{
                    transform: isFlipped ? "translateX(0)" : "translateX(-10px)",
                    opacity: isFlipped ? 1 : 0,
                    transitionDelay: `${index * 40 + 120}ms`,
                  }}
                >
                  <ArrowRight aria-hidden="true" className="h-3 w-3 shrink-0 text-signal-orange" />
                  <span className="truncate">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 border-carbon-lift border-t pt-3">
            <div
              className={cn(
                "group/start relative w-full",
                "flex items-center justify-between",
                "rounded-[6px] px-3 py-2",
                "transition-all duration-300",
                "bg-obsidian-canvas border border-carbon-lift/80",
                "hover:border-ash-stroke hover:bg-carbon-lift/40",
              )}
            >
              <span className="font-mono text-[0.7rem] uppercase tracking-wider text-pale-stone transition-colors duration-300 group-hover/start:text-bone">
                {actionLabel}
              </span>
              <div className="group/icon relative">
                <ArrowRight
                  aria-hidden="true"
                  className="relative z-10 h-3.5 w-3.5 text-signal-orange transition-transform duration-300 group-hover/start:translate-x-0.5"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes scale {
          0% {
            transform: scale(2);
            opacity: 0;
            box-shadow: 0px 0px 40px rgba(235, 94, 40, 0.35);
          }
          50% {
            transform: translate(0px, -5px) scale(1);
            opacity: 1;
            box-shadow: 0px 8px 16px rgba(235, 94, 40, 0.35);
          }
          100% {
            transform: translate(0px, 5px) scale(0.1);
            opacity: 0;
            box-shadow: 0px 10px 16px rgba(235, 94, 40, 0);
          }
        }
      `}</style>
    </div>
  );
}
