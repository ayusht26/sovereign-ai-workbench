"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { nightOwl } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy, File, FileCode, FileText } from "lucide-react";

const Icons = {
  check: Check,
  copy: Copy,
  file: File,
  javascript: FileCode,
  typescript: FileCode,
  css: FileText,
};

export interface FileBlock {
  title: string;
  code: string;
  language?: string;
}

export interface CodeBlockProps {
  files: FileBlock[];
  defaultTitle?: string;
  className?: string;
}

const darkTheme = {
  ...nightOwl,
  'pre[class*="language-"]': {
    ...((nightOwl as any)?.['pre[class*="language-"]'] || {}),
    background: "transparent",
  },
};

export function CodeBlock({ files, defaultTitle, className }: CodeBlockProps) {
  const [activeTitle, setActiveTitle] = useState(
    defaultTitle || files[0]?.title || "code"
  );
  const [copied, setCopied] = useState(false);

  const activeFile = files.find((file) => file.title === activeTitle) || files[0];
  const code = activeFile?.code || "";
  const language =
    activeFile?.language || getLanguageFromFileName(activeFile?.title || activeTitle || "");

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div
      className={cn(
        "relative my-3 rounded-lg border border-carbon-lift bg-[#0d0d0d] text-bone",
        "backdrop-blur-md shadow-lg overflow-hidden",
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-carbon-lift/60 bg-[#141414] px-3 py-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          {files.map(({ title }) => {
            const isCurrent = title === (activeFile?.title || activeTitle);
            return (
              <Button
                key={title}
                variant={isCurrent ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setActiveTitle(title)}
                className={cn(
                  "h-7 gap-1.5 px-2.5 text-xs font-mono transition-colors",
                  isCurrent
                    ? "bg-carbon-lift text-bone font-medium border border-ash-stroke/40"
                    : "text-warm-granite hover:text-bone hover:bg-carbon-lift/50"
                )}
              >
                <FileIcon fileName={title} />
                <span>{title}</span>
              </Button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          {language && (
            <span className="hidden sm:inline font-mono text-[10px] uppercase text-warm-granite/70 px-1.5 py-0.5 rounded bg-black/40">
              {language}
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => copyToClipboard(code)}
            className="h-7 w-7 text-warm-granite hover:text-bone hover:bg-carbon-lift rounded cursor-pointer"
            title="Copy code"
          >
            {copied ? (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
              >
                <Icons.check className="h-3.5 w-3.5 text-metric-green" />
              </motion.div>
            ) : (
              <Icons.copy className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
      <div className="max-h-[500px] overflow-auto text-xs font-mono">
        <SyntaxHighlighter
          language={language.toLowerCase()}
          style={darkTheme}
          customStyle={{
            margin: 0,
            padding: "1rem",
            background: "transparent",
            fontSize: "0.85rem",
            lineHeight: "1.5",
          }}
          wrapLongLines={false}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function getLanguageFromFileName(fileName: string): string {
  const ext = fileName.split(".").pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    js: "javascript",
    jsx: "jsx",
    ts: "typescript",
    tsx: "typescript",
    html: "html",
    css: "css",
    json: "json",
    py: "python",
    python: "python",
    sh: "bash",
    bash: "bash",
    sql: "sql",
    yaml: "yaml",
    yml: "yaml",
    rs: "rust",
    go: "go",
    cpp: "cpp",
    c: "c",
    java: "java",
    md: "markdown",
  };
  return languageMap[ext || ""] || ext || "javascript";
}

function FileIcon({ fileName }: { fileName: string }) {
  const ext = fileName.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "js":
    case "jsx":
      return <Icons.javascript className="h-3.5 w-3.5 text-yellow-400" />;
    case "ts":
    case "tsx":
      return <Icons.typescript className="h-3.5 w-3.5 text-blue-400" />;
    case "css":
      return <Icons.css className="h-3.5 w-3.5 text-cyan-400" />;
    case "html":
      return <Icons.file className="h-3.5 w-3.5 text-orange-400" />;
    case "py":
    case "python":
      return <FileCode className="h-3.5 w-3.5 text-emerald-400" />;
    case "json":
      return <FileText className="h-3.5 w-3.5 text-amber-300" />;
    default:
      return <Icons.file className="h-3.5 w-3.5 text-warm-granite" />;
  }
}
