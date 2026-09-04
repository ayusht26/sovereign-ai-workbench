import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Download,
  FileText,
  FileSpreadsheet,
  Presentation,
  FileCode,
  Check,
  ChevronDown,
  Sparkles,
  ShieldCheck,
  Eye,
} from 'lucide-react';
import { toast } from 'sonner';
import { GeneratedFile, downloadGeneratedFile } from '@/lib/file-generator';
import { cn } from '@/lib/utils';

interface FileDeliverableCardProps {
  file: GeneratedFile;
  className?: string;
}

function formatBytes(bytes?: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function FileDeliverableCard({ file, className }: FileDeliverableCardProps) {
  const [downloaded, setDownloaded] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleDownload = () => {
    try {
      downloadGeneratedFile(file);
      setDownloaded(true);
      toast.success(`Downloaded ${file.name}`, {
        description: 'File generated and saved locally to your device.',
      });
      setTimeout(() => setDownloaded(false), 3000);
    } catch (err) {
      toast.error('Failed to initiate file download');
    }
  };

  // Format-specific metadata and visual branding
  const fileMeta = (() => {
    switch (file.type) {
      case 'docx':
        return {
          label: 'Word Document',
          ext: '.DOCX',
          accentColor: 'text-blue-400',
          borderColor: 'border-blue-500/30',
          bgBadge: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
          glowHover: 'hover:border-blue-500/50 hover:shadow-[0_0_24px_rgba(59,130,246,0.12)]',
          icon: FileText,
          summaryBadge: file.details?.sectionCount
            ? `${file.details.sectionCount} ${file.details.sectionCount === 1 ? 'Section' : 'Sections'}`
            : 'Structured Document',
        };
      case 'xlsx':
        return {
          label: 'Excel Spreadsheet',
          ext: '.XLSX',
          accentColor: 'text-emerald-400',
          borderColor: 'border-emerald-500/30',
          bgBadge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
          glowHover: 'hover:border-emerald-500/50 hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]',
          icon: FileSpreadsheet,
          summaryBadge: file.details?.rowCount
            ? `${file.details.rowCount} Data Rows`
            : file.details?.sheetCount
              ? `${file.details.sheetCount} Sheets`
              : 'Multi-Sheet Workbook',
        };
      case 'pptx':
        return {
          label: 'PowerPoint Deck',
          ext: '.PPTX',
          accentColor: 'text-orange-400',
          borderColor: 'border-orange-500/30',
          bgBadge: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
          glowHover: 'hover:border-orange-500/50 hover:shadow-[0_0_24px_rgba(249,115,22,0.12)]',
          icon: Presentation,
          summaryBadge: file.details?.slideCount
            ? `${file.details.slideCount} Slides (16:9)`
            : 'Executive Presentation',
        };
      case 'txt':
      default:
        return {
          label: 'Text Deliverable',
          ext: '.TXT',
          accentColor: 'text-amber-400',
          borderColor: 'border-amber-500/30',
          bgBadge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
          glowHover: 'hover:border-amber-500/50 hover:shadow-[0_0_24px_rgba(245,158,11,0.12)]',
          icon: FileCode,
          summaryBadge: file.details?.wordCount
            ? `${file.details.wordCount} Words`
            : 'Plain Text File',
        };
    }
  })();

  const IconComponent = fileMeta.icon;

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-[10px] border bg-[#111622]/90 backdrop-blur-md p-4 transition-all duration-300',
        fileMeta.borderColor,
        fileMeta.glowHover,
        className
      )}
    >
      {/* Top Header Row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {/* File Icon Tile */}
          <div
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-[8px] border bg-black/40 shadow-inner',
              fileMeta.borderColor
            )}
          >
            <IconComponent className={cn('h-5 w-5', fileMeta.accentColor)} />
          </div>

          {/* Name & Subtitle */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-bone truncate max-w-[280px]">
                {file.name}
              </span>
              <span
                className={cn(
                  'rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider border',
                  fileMeta.bgBadge
                )}
              >
                {fileMeta.ext}
              </span>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] font-mono text-warm-granite">
              <span>{fileMeta.label}</span>
              <span>·</span>
              <span>{formatBytes(file.sizeBytes)}</span>
              <span>·</span>
              <span className="text-pale-stone">{fileMeta.summaryBadge}</span>
            </div>
          </div>
        </div>

        {/* Primary Download Button */}
        <button
          type="button"
          onClick={handleDownload}
          className={cn(
            'inline-flex shrink-0 items-center gap-1.5 rounded-[6px] px-3.5 py-2 text-xs font-mono font-semibold transition-all duration-200 cursor-pointer shadow-md',
            downloaded
              ? 'bg-emerald-600 text-white shadow-emerald-500/20'
              : 'bg-bone text-obsidian-canvas hover:bg-white hover:scale-[1.02] active:scale-[0.98]'
          )}
          title={`Download ${file.name}`}
        >
          {downloaded ? (
            <>
              <Check className="h-3.5 w-3.5" />
              <span>Saved</span>
            </>
          ) : (
            <>
              <Download className="h-3.5 w-3.5" />
              <span>Download</span>
            </>
          )}
        </button>
      </div>

      {/* Description / Summary if available */}
      {file.description && (
        <p className="mt-2.5 text-xs text-pale-stone/90 leading-relaxed font-sans line-clamp-2">
          {file.description}
        </p>
      )}

      {/* Expandable Preview Toggle (if preview snippets exist) */}
      {file.details?.previewContent && file.details.previewContent.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-carbon-lift/50">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1.5 text-[11px] font-mono text-warm-granite hover:text-bone transition cursor-pointer"
          >
            <Eye className="h-3 w-3 text-signal-orange" />
            <span>{expanded ? 'Hide outline preview' : 'Inspect outline preview'}</span>
            <ChevronDown
              className={cn(
                'h-3 w-3 transition-transform duration-200',
                expanded && 'rotate-180'
              )}
            />
          </button>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden pt-2"
              >
                <div className="space-y-1.5 rounded-[6px] border border-carbon-lift/60 bg-black/40 p-2.5 font-mono text-[11px] text-warm-granite">
                  <div className="flex items-center gap-1.5 text-[10px] uppercase text-signal-orange font-semibold">
                    <Sparkles className="h-3 w-3" />
                    <span>Deliverable Structure & Contents:</span>
                  </div>
                  <ul className="space-y-1 pl-1">
                    {file.details.previewContent.map((snippet, idx) => (
                      <li key={idx} className="flex items-start gap-1.5 text-pale-stone">
                        <span className="text-signal-orange/60">•</span>
                        <span className="line-clamp-1">{snippet}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Footer Security Badge */}
      <div className="mt-3 flex items-center justify-between text-[10px] font-mono text-warm-granite/70">
        <span className="inline-flex items-center gap-1 text-metric-green">
          <ShieldCheck className="h-3 w-3" /> Air-Gapped Local Artifact
        </span>
        <span>0 Outbound Egress · Validated</span>
      </div>
    </div>
  );
}
