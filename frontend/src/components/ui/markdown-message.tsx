"use client";

import React, { useMemo } from "react";
import { CodeBlock, FileBlock } from "./code-block";
import { cn } from "@/lib/utils";

interface MarkdownMessageProps {
  content: string;
  className?: string;
}

type ContentBlock =
  | { type: "code"; language: string; filename: string; code: string }
  | { type: "text"; text: string };

export function MarkdownMessage({ content, className }: MarkdownMessageProps) {
  const blocks = useMemo(() => {
    return parseMarkdownBlocks(content);
  }, [content]);

  return (
    <div className={cn("space-y-3 leading-relaxed text-bone/90", className)}>
      {blocks.map((block, index) => {
        if (block.type === "code") {
          const file: FileBlock = {
            title: block.filename,
            code: block.code,
            language: block.language,
          };
          return (
            <CodeBlock
              key={`code-${index}`}
              files={[file]}
              defaultTitle={block.filename}
            />
          );
        }

        return (
          <div key={`text-${index}`} className="text-body-sm font-sans">
            {renderFormattedText(block.text)}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Split markdown text into alternating text blocks and code blocks
 */
function parseMarkdownBlocks(raw: string): ContentBlock[] {
  if (!raw) return [];

  const blocks: ContentBlock[] = [];
  // Regex to match code blocks: ```[lang][:filename] [optional file/title]\n code \n```
  const codeBlockRegex = /```([a-zA-Z0-9_-]+)?(?::([^\n]+))?([^\n]*)\n([\s\S]*?)```/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(raw)) !== null) {
    const textBefore = raw.substring(lastIndex, match.index);
    if (textBefore.trim()) {
      blocks.push({ type: "text", text: textBefore });
    }

    const rawLang = (match[1] || "").trim();
    let filename = (match[2] || "").trim();
    const extraTitle = (match[3] || "").trim();
    const code = match[4].replace(/\n$/, ""); // strip single trailing newline

    if (!filename && extraTitle) {
      filename = extraTitle;
    }

    const language = rawLang || "typescript";
    if (!filename) {
      filename = getDefaultFileName(language);
    }

    blocks.push({
      type: "code",
      language,
      filename,
      code,
    });

    lastIndex = match.index + match[0].length;
  }

  const remainingText = raw.substring(lastIndex);
  if (remainingText.trim() || blocks.length === 0) {
    blocks.push({ type: "text", text: remainingText });
  }

  return blocks;
}

function getDefaultFileName(lang: string): string {
  const l = lang.toLowerCase();
  switch (l) {
    case "typescript":
    case "ts":
      return "snippet.ts";
    case "tsx":
      return "Component.tsx";
    case "javascript":
    case "js":
      return "script.js";
    case "jsx":
      return "Component.jsx";
    case "python":
    case "py":
      return "main.py";
    case "sql":
      return "query.sql";
    case "css":
      return "styles.css";
    case "html":
      return "index.html";
    case "json":
      return "data.json";
    case "bash":
    case "sh":
    case "shell":
      return "terminal.sh";
    case "yaml":
    case "yml":
      return "config.yaml";
    case "rust":
    case "rs":
      return "main.rs";
    case "go":
      return "main.go";
    case "c":
    case "cpp":
    case "c++":
      return "main.cpp";
    default:
      return `${l || "code"}.txt`;
  }
}

/**
 * Format markdown paragraphs, headings, bold, bullet points, inline code
 */
function renderFormattedText(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null;

  const flushList = () => {
    if (currentList) {
      if (currentList.type === "ul") {
        elements.push(
          <ul
            key={`list-${elements.length}`}
            className="my-2 list-disc pl-5 space-y-1 text-pale-stone"
          >
            {currentList.items.map((item, i) => (
              <li key={i}>{formatInline(item)}</li>
            ))}
          </ul>
        );
      } else {
        elements.push(
          <ol
            key={`list-${elements.length}`}
            className="my-2 list-decimal pl-5 space-y-1 text-pale-stone"
          >
            {currentList.items.map((item, i) => (
              <li key={i}>{formatInline(item)}</li>
            ))}
          </ol>
        );
      }
      currentList = null;
    }
  };

  lines.forEach((line, lineIndex) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      elements.push(<div key={`empty-${lineIndex}`} className="h-2" />);
      return;
    }

    // Headings
    if (trimmed.startsWith("### ")) {
      flushList();
      elements.push(
        <h4
          key={`h3-${lineIndex}`}
          className="mt-3 mb-1 font-semibold text-bone text-sm tracking-tight"
        >
          {formatInline(trimmed.slice(4))}
        </h4>
      );
      return;
    }
    if (trimmed.startsWith("## ")) {
      flushList();
      elements.push(
        <h3
          key={`h2-${lineIndex}`}
          className="mt-4 mb-1.5 font-bold text-bone text-base tracking-tight text-signal-orange"
        >
          {formatInline(trimmed.slice(3))}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith("# ")) {
      flushList();
      elements.push(
        <h2
          key={`h1-${lineIndex}`}
          className="mt-4 mb-2 font-bold text-bone text-lg tracking-tight"
        >
          {formatInline(trimmed.slice(2))}
        </h2>
      );
      return;
    }

    // Blockquote
    if (trimmed.startsWith("> ")) {
      flushList();
      elements.push(
        <blockquote
          key={`quote-${lineIndex}`}
          className="my-2 border-l-2 border-signal-orange/60 pl-3 italic text-warm-granite bg-carbon-lift/20 py-1 rounded-r text-xs"
        >
          {formatInline(trimmed.slice(2))}
        </blockquote>
      );
      return;
    }

    // Bullet lists
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!currentList || currentList.type !== "ul") {
        flushList();
        currentList = { type: "ul", items: [] };
      }
      currentList.items.push(trimmed.slice(2));
      return;
    }

    // Numbered lists
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      if (!currentList || currentList.type !== "ol") {
        flushList();
        currentList = { type: "ol", items: [] };
      }
      currentList.items.push(numMatch[2]);
      return;
    }

    flushList();
    elements.push(
      <p key={`p-${lineIndex}`} className="my-1 text-pale-stone leading-relaxed">
        {formatInline(line)}
      </p>
    );
  });

  flushList();
  return elements;
}

/**
 * Handle inline markdown: bold, italic, inline code (`code`), links
 */
function formatInline(str: string): React.ReactNode[] {
  // Regex to split by inline code, bold, italic
  const parts: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)/g;
  let lastIdx = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIdx) {
      parts.push(str.substring(lastIdx, match.index));
    }

    const token = match[0];
    if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={`code-${match.index}`}
          className="rounded border border-carbon-lift/80 bg-carbon-lift/50 px-1.5 py-0.5 font-mono text-[11px] text-signal-orange"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (
      (token.startsWith("**") && token.endsWith("**")) ||
      (token.startsWith("__") && token.endsWith("__"))
    ) {
      parts.push(
        <strong key={`bold-${match.index}`} className="font-semibold text-bone">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (
      (token.startsWith("*") && token.endsWith("*")) ||
      (token.startsWith("_") && token.endsWith("_"))
    ) {
      parts.push(
        <em key={`italic-${match.index}`} className="italic text-pale-stone">
          {token.slice(1, -1)}
        </em>
      );
    }

    lastIdx = match.index + token.length;
  }

  if (lastIdx < str.length) {
    parts.push(str.substring(lastIdx));
  }

  return parts;
}
