"use client";

import { motion, useScroll, useTransform, type Variants } from "motion/react";
import { useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const variants: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

/** Scroll-linked expansion: the panel widens, scales up and un-rounds as it enters. */
export function ScrollExpand({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "center center"],
  });

  const scale = useTransform(scrollYProgress, [0, 1], [0.86, 1]);
  const width = useTransform(scrollYProgress, [0, 1], ["72%", "100%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.4, 1], [0.25, 0.8, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [60, 0]);

  return (
    <div ref={ref} className={cn("flex justify-center", className)}>
      <motion.div style={{ scale, width, opacity, y }} className="origin-bottom">
        {children}
      </motion.div>
    </div>
  );
}

/** A hairline that draws itself across the viewport as you scroll. */
export function ScrollRule() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end center"],
  });
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <div ref={ref} className="h-px w-full overflow-hidden bg-carbon-lift">
      <motion.div style={{ scaleX }} className="h-px w-full origin-left bg-signal-orange/70" />
    </div>
  );
}

export function Eyebrow({
  children,
  tone = "bone",
}: {
  children: ReactNode;
  tone?: "bone" | "dark";
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal-orange" />
      <span
        className={cn("eyebrow", tone === "bone" ? "text-pale-stone" : "text-obsidian-canvas/70")}
      >
        {children}
      </span>
    </div>
  );
}
