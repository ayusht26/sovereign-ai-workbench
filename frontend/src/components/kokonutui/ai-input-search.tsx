"use client";

/**
 * @author: @kokonutui & Bastion Sovereign AI
 * @description: AI Input Search with clipboard paste, image preview thumbnail, web toggle, and auto-resizing textarea
 */

import { Globe, Paperclip, Send, X, FileCheck, ImageIcon, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";
import { cn } from "@/lib/utils";

interface AIInputSearchProps {
  placeholder?: string;
  searchLabel?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSubmit?: (
    value: string,
    isWebSearch?: boolean,
    file?: File | null,
    imageDataUrl?: string | null
  ) => void;
  disabled?: boolean;
  className?: string;
}

export default function AI_Input_Search({
  placeholder = "Ask anything or query verified company documents...",
  searchLabel = "Web Search",
  value: controlledValue,
  onChange: controlledOnChange,
  onSubmit,
  disabled = false,
  className,
}: AIInputSearchProps) {
  const [internalValue, setInternalValue] = useState("");
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 52,
    maxHeight: 200,
  });

  const [showSearch, setShowSearch] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const setValue = (val: string) => {
    if (!isControlled) {
      setInternalValue(val);
    }
    controlledOnChange?.(val);
  };

  const processImageFile = (file: File) => {
    setAttachedFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setImageDataUrl(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault();
          processImageFile(file);
          return;
        }
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith("image/")) {
        processImageFile(file);
      } else {
        setAttachedFile(file);
        setImageDataUrl(null);
      }
    }
  };

  const handleSubmit = () => {
    if ((!value || !value.trim()) && !attachedFile && !imageDataUrl) return;
    if (disabled) return;

    onSubmit?.(value.trim(), showSearch, attachedFile, imageDataUrl);
    setValue("");
    setAttachedFile(null);
    setImageDataUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    adjustHeight(true);
  };

  const handleFocus = () => {
    setIsFocused(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
  };

  const handleContainerClick = () => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith("image/")) {
        processImageFile(file);
      } else {
        setAttachedFile(file);
        setImageDataUrl(null);
      }
    }
  };

  const removeFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setAttachedFile(null);
    setImageDataUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="relative mx-auto w-full max-w-3xl">
        <div
          aria-label="Search input container"
          className={cn(
            "relative flex w-full cursor-text flex-col rounded-2xl text-left transition-all duration-200 border",
            "border-[#262626] bg-[#111111] shadow-2xl backdrop-blur-md",
            isFocused && "border-signal-orange/60 ring-1 ring-signal-orange/30",
            isDragging && "border-signal-orange border-dashed bg-signal-orange/5",
            disabled && "opacity-60 cursor-not-allowed"
          )}
          onClick={handleContainerClick}
          onPaste={handlePaste}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              handleContainerClick();
            }
          }}
          role="textbox"
          tabIndex={0}
        >
          {/* Attached Image Thumbnail Preview Card (Matches reference UI) */}
          <AnimatePresence>
            {imageDataUrl && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 4 }}
                transition={{ duration: 0.2 }}
                className="px-4 pt-3"
              >
                <div className="group relative inline-block rounded-xl border border-white/15 bg-black/60 p-1.5 shadow-xl transition-all hover:border-signal-orange/60">
                  <div className="relative h-20 w-24 overflow-hidden rounded-lg bg-[#141414]">
                    <img
                      src={imageDataUrl}
                      alt="Pasted context thumbnail"
                      className="h-full w-full object-cover rounded-lg"
                    />
                    <button
                      type="button"
                      onClick={removeFile}
                      className="absolute top-1 right-1 flex h-5 w-5 items-center justify-center rounded-full bg-black/85 text-white/90 backdrop-blur-sm transition-transform hover:scale-110 hover:bg-red-600 hover:text-white cursor-pointer shadow-md"
                      title="Remove image"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="mt-1 flex items-center justify-between px-1 text-[10px] font-mono text-warm-granite">
                    <span className="truncate max-w-[70px]">{attachedFile?.name || "image.png"}</span>
                    <span className="text-signal-orange">vision</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Non-image File Attachment Pill */}
          <AnimatePresence>
            {!imageDataUrl && attachedFile && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                className="px-4 pt-3"
              >
                <div className="inline-flex items-center gap-1.5 rounded-md bg-signal-orange/15 border border-signal-orange/30 px-2.5 py-1 text-xs font-mono text-signal-orange">
                  <FileCheck className="h-3.5 w-3.5" />
                  <span className="max-w-[200px] truncate">{attachedFile.name}</span>
                  <span className="text-[10px] text-warm-granite">
                    ({(attachedFile.size / 1024).toFixed(1)} KB)
                  </span>
                  <button
                    type="button"
                    onClick={removeFile}
                    className="ml-1 rounded p-0.5 hover:bg-signal-orange/20 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="max-h-[200px] overflow-y-auto">
            <Textarea
              className="w-full resize-none rounded-xl rounded-b-none border-none bg-transparent px-4 py-3.5 leading-[1.4] text-bone placeholder:text-warm-granite/70 focus-visible:ring-0 text-sm font-sans"
              id="ai-input-search-textarea"
              disabled={disabled}
              onBlur={handleBlur}
              onChange={(e) => {
                setValue(e.target.value);
                adjustHeight();
              }}
              onFocus={handleFocus}
              onPaste={handlePaste}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder={placeholder}
              ref={textareaRef}
              value={value}
            />
          </div>

          <div className="h-12 rounded-b-2xl bg-black/40 border-t border-carbon-lift/30 flex items-center justify-between px-3">
            <div className="flex items-center gap-2">
              <label
                className="cursor-pointer rounded-lg bg-carbon-lift/50 p-2 text-warm-granite transition-colors hover:text-bone hover:bg-carbon-lift flex items-center gap-1"
                title="Attach image or document (or paste Ctrl+V)"
              >
                <input
                  ref={fileInputRef}
                  className="hidden"
                  type="file"
                  accept="image/*,.pdf,.doc,.docx,.txt,.csv,.json"
                  onChange={handleFileChange}
                />
                <Paperclip className="h-4 w-4" />
              </label>

              <button
                className={cn(
                  "flex h-8 cursor-pointer items-center gap-2 rounded-full border px-2.5 py-1 transition-all text-xs font-mono",
                  showSearch
                    ? "border-signal-orange/60 bg-signal-orange/15 text-signal-orange shadow-sm"
                    : "border-transparent bg-carbon-lift/40 text-warm-granite hover:text-bone hover:bg-carbon-lift"
                )}
                onClick={(e) => {
                  e.stopPropagation();
                  setShowSearch(!showSearch);
                }}
                type="button"
                title="Toggle Web Search Mode"
              >
                <div className="flex h-4 w-4 shrink-0 items-center justify-center">
                  <motion.div
                    animate={{
                      rotate: showSearch ? 180 : 0,
                      scale: showSearch ? 1.1 : 1,
                    }}
                    transition={{
                      type: "spring",
                      stiffness: 260,
                      damping: 25,
                    }}
                    whileHover={{
                      rotate: showSearch ? 180 : 15,
                      scale: 1.1,
                      transition: {
                        type: "spring",
                        stiffness: 300,
                        damping: 10,
                      },
                    }}
                  >
                    <Globe
                      className={cn("h-3.5 w-3.5", showSearch ? "text-signal-orange" : "text-inherit")}
                    />
                  </motion.div>
                </div>
                <AnimatePresence>
                  {showSearch && (
                    <motion.span
                      animate={{
                        width: "auto",
                        opacity: 1,
                      }}
                      className="shrink-0 overflow-hidden whitespace-nowrap text-signal-orange font-medium"
                      exit={{ width: 0, opacity: 0 }}
                      initial={{ width: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      {searchLabel}
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                className={cn(
                  "rounded-lg p-2 transition-all flex items-center justify-center",
                  (value.trim() || attachedFile || imageDataUrl) && !disabled
                    ? "bg-signal-orange text-obsidian-canvas font-bold hover:brightness-110 shadow-md cursor-pointer"
                    : "bg-carbon-lift/40 text-warm-granite/40 cursor-not-allowed"
                )}
                disabled={(!value.trim() && !attachedFile && !imageDataUrl) || disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSubmit();
                }}
                type="button"
                title="Send query (Enter)"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
