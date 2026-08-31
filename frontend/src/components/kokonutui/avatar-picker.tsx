"use client";

import { Check, Upload, Sparkles, Image as ImageIcon } from "lucide-react";
import type { Variants } from "motion/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  avatars,
  AVATAR_RGB,
  AvatarPreset,
  getAvatarById,
  parseAvatarId,
  UserAvatar,
} from "./avatar-data";

export interface AvatarPickerProps {
  currentAvatarUrl?: string | null;
  username?: string | null;
  onSaveAvatar: (avatarUrl: string) => Promise<void> | void;
  onUploadCustomFile?: (file: File) => Promise<string | void>;
  isSubmitting?: boolean;
  className?: string;
}

const containerVariants: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.04 },
  },
};

const thumbnailVariants: Variants = {
  initial: { opacity: 0, y: 6 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.25, ease: "easeOut" },
  },
};

export default function AvatarPicker({
  currentAvatarUrl,
  username,
  onSaveAvatar,
  onUploadCustomFile,
  isSubmitting = false,
  className,
}: AvatarPickerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const shouldReduceMotion = useReducedMotion();

  // Mode: "preset" | "custom"
  const parsedPresetId = parseAvatarId(currentAvatarUrl);
  const initialPreset = parsedPresetId ? getAvatarById(parsedPresetId) : avatars[0];

  const isInitiallyCustom =
    Boolean(currentAvatarUrl) &&
    (currentAvatarUrl!.startsWith("http") || currentAvatarUrl!.startsWith("data:"));

  const [selectedType, setSelectedType] = useState<"preset" | "custom">(
    isInitiallyCustom ? "custom" : "preset"
  );
  const [selectedPreset, setSelectedPreset] = useState<AvatarPreset>(initialPreset);
  const [customAvatarPreview, setCustomAvatarPreview] = useState<string | null>(
    isInitiallyCustom ? currentAvatarUrl! : null
  );
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const id = parseAvatarId(currentAvatarUrl);
    if (id) {
      setSelectedPreset(getAvatarById(id));
      setSelectedType("preset");
    } else if (
      currentAvatarUrl &&
      (currentAvatarUrl.startsWith("http") || currentAvatarUrl.startsWith("data:"))
    ) {
      setCustomAvatarPreview(currentAvatarUrl);
      setSelectedType("custom");
    }
  }, [currentAvatarUrl]);

  const handleSelectPreset = (preset: AvatarPreset) => {
    setSelectedPreset(preset);
    setSelectedType("preset");
  };

  const handleCustomFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Local preview immediately
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setCustomAvatarPreview(dataUrl);
      setSelectedType("custom");
    };
    reader.readAsDataURL(file);

    if (onUploadCustomFile) {
      setIsUploading(true);
      try {
        const uploadedUrl = await onUploadCustomFile(file);
        if (uploadedUrl) {
          setCustomAvatarPreview(uploadedUrl);
        }
      } finally {
        setIsUploading(false);
      }
    }
  };

  const handleSave = () => {
    if (selectedType === "preset") {
      onSaveAvatar(`avatar:${selectedPreset.id}`);
    } else if (customAvatarPreview) {
      onSaveAvatar(customAvatarPreview);
    }
  };

  const rgb =
    selectedType === "preset"
      ? AVATAR_RGB[selectedPreset.id] || "255, 125, 16"
      : "249, 115, 22";

  return (
    <div className={cn("flex flex-col items-center space-y-6", className)}>
      {/* Avatar Stage */}
      <div className="flex flex-col items-center gap-3">
        <div className="relative h-36 w-36 md:h-40 md:w-40">
          {/* Animated per-avatar color ring */}
          <motion.div
            animate={{
              boxShadow: `0 0 0 2px rgba(${rgb}, 0.55), 0 6px 24px rgba(${rgb}, 0.25)`,
            }}
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 rounded-full"
            transition={
              shouldReduceMotion
                ? { duration: 0 }
                : { duration: 0.4, ease: "easeOut" }
            }
          />

          {/* Avatar circle — clips content */}
          <div className="relative h-full w-full overflow-hidden rounded-full bg-[#0a0a0a]">
            <AnimatePresence mode="wait">
              {selectedType === "preset" ? (
                <motion.div
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute inset-0 flex items-center justify-center"
                  exit={{ opacity: 0, scale: 0.95 }}
                  initial={{ opacity: 0, scale: 0.95 }}
                  key={`preset-${selectedPreset.id}`}
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : { duration: 0.2, ease: "easeOut" }
                  }
                >
                  <div className="scale-[3.8] md:scale-[4] transform select-none">
                    {selectedPreset.svg}
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute inset-0 flex items-center justify-center"
                  exit={{ opacity: 0, scale: 0.95 }}
                  initial={{ opacity: 0, scale: 0.95 }}
                  key="custom-avatar"
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : { duration: 0.2, ease: "easeOut" }
                  }
                >
                  {customAvatarPreview ? (
                    <img
                      src={customAvatarPreview}
                      alt="Custom avatar"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-warm-granite">
                      <ImageIcon className="h-8 w-8" />
                      <span className="mt-1 text-[11px]">Upload custom</span>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Selected Avatar Label */}
        <AnimatePresence mode="wait">
          <motion.span
            animate={{ opacity: 1 }}
            className="text-[11px] text-warm-granite uppercase tracking-[0.15em] font-mono font-medium"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            key={selectedType === "preset" ? selectedPreset.alt : "custom-label"}
            transition={{ duration: 0.15 }}
          >
            {selectedType === "preset" ? selectedPreset.alt : "Your Custom Avatar"}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* Thumbnail Strip: 4 Presets + 1 Custom Option */}
      <div className="space-y-2 text-center w-full">
        <span className="text-xs font-mono uppercase text-warm-granite">
          Choose a preset or upload your own
        </span>

        <motion.div
          animate="animate"
          className="flex gap-2.5 md:gap-3 justify-center items-center flex-wrap pt-1"
          initial="initial"
          variants={containerVariants}
        >
          {/* Preset 1-4 */}
          {avatars.map((avatar) => {
            const isSelected = selectedType === "preset" && selectedPreset.id === avatar.id;
            return (
              <motion.button
                aria-label={`Select ${avatar.alt}`}
                aria-pressed={isSelected}
                className={cn(
                  "relative h-13 w-13 md:h-14 md:w-14 overflow-hidden rounded-xl border bg-carbon-lift/60 transition-[opacity,box-shadow,border-color] duration-200 ease-out cursor-pointer",
                  isSelected
                    ? "border-signal-orange opacity-100 ring-2 ring-signal-orange ring-offset-2 ring-offset-obsidian-canvas"
                    : "border-carbon-lift opacity-50 hover:opacity-100 hover:border-ash-stroke"
                )}
                key={avatar.id}
                onClick={() => handleSelectPreset(avatar)}
                type="button"
                variants={thumbnailVariants}
                whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
                whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="scale-[2.1] md:scale-[2.3] transform select-none">
                    {avatar.svg}
                  </div>
                </div>
                {isSelected && (
                  <div className="absolute -right-0.5 -bottom-0.5 flex h-4.5 w-4.5 md:h-5 md:w-5 items-center justify-center rounded-full bg-signal-orange text-white shadow-sm">
                    <Check aria-hidden="true" className="h-3 w-3 stroke-[3]" />
                  </div>
                )}
              </motion.button>
            );
          })}

          {/* Option 5: Your Own Avatar */}
          <motion.button
            aria-label="Your own custom avatar"
            aria-pressed={selectedType === "custom"}
            className={cn(
              "relative h-13 w-13 md:h-14 md:w-14 overflow-hidden rounded-xl border bg-carbon-lift/60 transition-[opacity,box-shadow,border-color] duration-200 ease-out cursor-pointer flex items-center justify-center",
              selectedType === "custom"
                ? "border-signal-orange opacity-100 ring-2 ring-signal-orange ring-offset-2 ring-offset-obsidian-canvas"
                : "border-carbon-lift opacity-60 hover:opacity-100 hover:border-ash-stroke"
            )}
            onClick={() => {
              if (customAvatarPreview) {
                setSelectedType("custom");
              } else {
                fileInputRef.current?.click();
              }
            }}
            type="button"
            variants={thumbnailVariants}
            whileHover={shouldReduceMotion ? {} : { scale: 1.08 }}
            whileTap={shouldReduceMotion ? {} : { scale: 0.92 }}
            title="Choose or upload your custom avatar"
          >
            {customAvatarPreview ? (
              <img
                src={customAvatarPreview}
                alt="Custom avatar"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-warm-granite">
                <Upload className="h-5 w-5" />
                <span className="text-[9px] font-mono mt-0.5">Custom</span>
              </div>
            )}
            {selectedType === "custom" && (
              <div className="absolute -right-0.5 -bottom-0.5 flex h-4.5 w-4.5 md:h-5 md:w-5 items-center justify-center rounded-full bg-signal-orange text-white shadow-sm">
                <Check aria-hidden="true" className="h-3 w-3 stroke-[3]" />
              </div>
            )}
          </motion.button>
        </motion.div>
      </div>

      {/* Upload button for custom image */}
      <div className="flex items-center gap-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleCustomFileChange}
          accept="image/*"
          className="hidden"
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="h-8 text-xs border-carbon-lift bg-[#181818] text-bone hover:border-ash-stroke hover:bg-carbon-lift cursor-pointer gap-1.5"
        >
          <Upload className="h-3.5 w-3.5 text-signal-orange" />
          {isUploading ? "Uploading..." : "Upload New Image"}
        </Button>
      </div>

      {/* Save Avatar Button */}
      <div className="w-full pt-2">
        <Button
          type="button"
          onClick={handleSave}
          disabled={isSubmitting || isUploading || (selectedType === "custom" && !customAvatarPreview)}
          className="h-10 w-full text-xs md:text-sm bg-signal-orange text-white hover:bg-signal-orange/90 cursor-pointer font-medium shadow-md"
        >
          {isSubmitting ? "Saving..." : "Save Avatar"}
        </Button>
      </div>
    </div>
  );
}
