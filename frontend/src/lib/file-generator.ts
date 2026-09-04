/**
 * file-generator.ts — Sovereign AI Workbench Deliverable Engine
 * 
 * Provides client-side generation for real deliverables:
 * - Plain text / code (.txt)
 * - Microsoft Word documents (.docx) with formatted headings, tables & bullets
 * - Microsoft Excel workbooks (.xlsx) with auto-sized columns & formulas
 * - Microsoft PowerPoint presentations (.pptx) with modern 16:9 widescreen layout
 */

import {
  Document,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  Packer,
  ShadingType,
} from 'docx';
import * as XLSX from 'xlsx';
import PptxGenJS from 'pptxgenjs';

export interface GeneratedFile {
  id: string;
  name: string;
  type: 'txt' | 'docx' | 'xlsx' | 'pptx';
  mimeType: string;
  sizeBytes: number;
  base64Data: string;
  createdAt: string;
  title: string;
  description?: string;
  details?: {
    slideCount?: number;
    sheetCount?: number;
    rowCount?: number;
    wordCount?: number;
    sectionCount?: number;
    previewContent?: string[];
  };
}

export interface DocxSectionInput {
  heading: string;
  level?: 1 | 2 | 3;
  content: string;
  bulletPoints?: string[];
  table?: {
    headers: string[];
    rows: string[][];
  };
}

export interface DocxGeneratorOptions {
  filename: string;
  title: string;
  subtitle?: string;
  author?: string;
  sections: DocxSectionInput[];
  classification?: string;
}

export interface XlsxSheetInput {
  sheetName: string;
  columns: string[];
  rows: (string | number | boolean)[][];
  summaryRow?: (string | number | boolean)[];
}

export interface XlsxGeneratorOptions {
  filename: string;
  title?: string;
  description?: string;
  sheets: XlsxSheetInput[];
}

export interface PptxSlideInput {
  slideTitle: string;
  subtitle?: string;
  bulletPoints?: string[];
  bodyText?: string;
  speakerNotes?: string;
}

export interface PptxGeneratorOptions {
  filename: string;
  title: string;
  subtitle?: string;
  presenter?: string;
  slides: PptxSlideInput[];
}

export interface TxtGeneratorOptions {
  filename: string;
  title?: string;
  content: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// 1. Plain Text (.txt) Generator
// ---------------------------------------------------------------------------
export function generateTxtFile(options: TxtGeneratorOptions): GeneratedFile {
  const cleanFilename = options.filename.endsWith('.txt') ? options.filename : `${options.filename}.txt`;
  const content = options.content || '';
  
  // Base64 encoding supporting UTF-8
  const base64Data = btoa(unescape(encodeURIComponent(content)));
  const sizeBytes = new TextEncoder().encode(content).length;
  const lineCount = content.split('\n').length;
  const wordCount = content.trim().split(/\s+/).filter(Boolean).length;

  const previewLines = content
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, 5);

  return {
    id: crypto.randomUUID(),
    name: cleanFilename,
    type: 'txt',
    mimeType: 'text/plain;charset=utf-8',
    sizeBytes,
    base64Data,
    createdAt: new Date().toISOString(),
    title: options.title || cleanFilename,
    description: options.description || `Text deliverable (${lineCount} lines, ${wordCount} words)`,
    details: {
      wordCount,
      previewContent: previewLines,
    },
  };
}

// ---------------------------------------------------------------------------
// 2. Microsoft Word (.docx) Generator
// ---------------------------------------------------------------------------
export async function generateDocxFile(options: DocxGeneratorOptions): Promise<GeneratedFile> {
  const cleanFilename = options.filename.endsWith('.docx') ? options.filename : `${options.filename}.docx`;
  const docElements: (Paragraph | Table)[] = [];

  // Header / Title Block
  docElements.push(
    new Paragraph({
      text: options.title,
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { after: 120 },
      run: {
        size: 38,
        bold: true,
        color: '0F172A',
        font: 'Segoe UI',
      },
    })
  );

  if (options.subtitle) {
    docElements.push(
      new Paragraph({
        text: options.subtitle,
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        run: {
          size: 24,
          italics: true,
          color: '475569',
          font: 'Segoe UI',
        },
      })
    );
  }

  // Metadata ribbon (Author, Date, Classification)
  const metaParts = [
    `Author: ${options.author || 'Bastion Sovereign AI'}`,
    `Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}`,
    `Classification: ${options.classification || 'OFFICIAL / SOVEREIGN AUDITED'}`,
  ];

  docElements.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 360 },
      children: [
        new TextRun({
          text: metaParts.join('  •  '),
          size: 18,
          color: '64748B',
          font: 'Segoe UI',
        }),
      ],
    })
  );

  // Divider spacing
  docElements.push(
    new Paragraph({
      spacing: { after: 200 },
    })
  );

  const previewSnippets: string[] = [];

  // Iterate over sections
  for (const section of options.sections) {
    let headingLevel = HeadingLevel.HEADING_1;
    let headingSize = 30;
    if (section.level === 2) {
      headingLevel = HeadingLevel.HEADING_2;
      headingSize = 26;
    } else if (section.level === 3) {
      headingLevel = HeadingLevel.HEADING_3;
      headingSize = 22;
    }

    docElements.push(
      new Paragraph({
        text: section.heading,
        heading: headingLevel,
        spacing: { before: 260, after: 140 },
        run: {
          bold: true,
          size: headingSize,
          color: '1E293B',
          font: 'Segoe UI',
        },
      })
    );

    previewSnippets.push(section.heading);

    // Section Content Body
    if (section.content) {
      const paragraphs = section.content.split('\n\n');
      for (const p of paragraphs) {
        if (!p.trim()) continue;
        docElements.push(
          new Paragraph({
            text: p.trim(),
            spacing: { after: 120, line: 276 },
            run: {
              size: 22,
              color: '334155',
              font: 'Segoe UI',
            },
          })
        );
      }
    }

    // Bullet Points
    if (section.bulletPoints && section.bulletPoints.length > 0) {
      for (const bp of section.bulletPoints) {
        docElements.push(
          new Paragraph({
            bullet: { level: 0 },
            spacing: { after: 80 },
            children: [
              new TextRun({
                text: bp,
                size: 22,
                color: '334155',
                font: 'Segoe UI',
              }),
            ],
          })
        );
      }
    }

    // Optional Table
    if (section.table && section.table.headers.length > 0) {
      const tableRows: TableRow[] = [];

      // Header Row
      tableRows.push(
        new TableRow({
          tableHeader: true,
          children: section.table.headers.map(
            (h) =>
              new TableCell({
                width: { size: Math.floor(9000 / section.table!.headers.length), type: WidthType.DXA },
                shading: { type: ShadingType.CLEAR, fill: '1E293B' },
                margins: { top: 120, bottom: 120, left: 140, right: 140 },
                children: [
                  new Paragraph({
                    alignment: AlignmentType.LEFT,
                    children: [
                      new TextRun({
                        text: h,
                        bold: true,
                        size: 20,
                        color: 'FFFFFF',
                        font: 'Segoe UI',
                      }),
                    ],
                  }),
                ],
              })
          ),
        })
      );

      // Data Rows
      section.table.rows.forEach((row, rowIdx) => {
        const isEven = rowIdx % 2 === 0;
        tableRows.push(
          new TableRow({
            children: row.map(
              (cellText) =>
                new TableCell({
                  width: { size: Math.floor(9000 / section.table!.headers.length), type: WidthType.DXA },
                  shading: { type: ShadingType.CLEAR, fill: isEven ? 'F8FAFC' : 'FFFFFF' },
                  margins: { top: 100, bottom: 100, left: 140, right: 140 },
                  children: [
                    new Paragraph({
                      alignment: AlignmentType.LEFT,
                      children: [
                        new TextRun({
                          text: cellText,
                          size: 20,
                          color: '1E293B',
                          font: 'Segoe UI',
                        }),
                      ],
                    }),
                  ],
                })
            ),
          })
        );
      });

      docElements.push(
        new Table({
          rows: tableRows,
          width: { size: 9000, type: WidthType.DXA },
          alignment: AlignmentType.CENTER,
        })
      );

      docElements.push(new Paragraph({ spacing: { after: 180 } }));
    }
  }

  // Footer banner
  docElements.push(
    new Paragraph({
      spacing: { before: 400 },
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: '— Generated by Bastion Sovereign AI Workbench · Confidential Internal Record · Zero External Egress —',
          size: 16,
          italics: true,
          color: '94A3B8',
          font: 'Segoe UI',
        }),
      ],
    })
  );

  const doc = new Document({
    title: options.title,
    description: options.subtitle,
    creator: options.author || 'Bastion Sovereign AI',
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 1440,
              right: 1440,
              bottom: 1440,
              left: 1440,
            },
          },
        },
        children: docElements,
      },
    ],
  });

  const base64Data = await Packer.toBase64String(doc);
  const sizeBytes = Math.floor((base64Data.length * 3) / 4);

  return {
    id: crypto.randomUUID(),
    name: cleanFilename,
    type: 'docx',
    mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    sizeBytes,
    base64Data,
    createdAt: new Date().toISOString(),
    title: options.title,
    description: options.subtitle || `Word Document (${options.sections.length} sections)`,
    details: {
      sectionCount: options.sections.length,
      previewContent: previewSnippets,
    },
  };
}

// ---------------------------------------------------------------------------
// 3. Microsoft Excel (.xlsx) Generator
// ---------------------------------------------------------------------------
export function generateXlsxFile(options: XlsxGeneratorOptions): GeneratedFile {
  const cleanFilename = options.filename.endsWith('.xlsx') ? options.filename : `${options.filename}.xlsx`;
  const wb = XLSX.utils.book_new();
  let totalRows = 0;
  const previewSnippets: string[] = [];

  for (const sheet of options.sheets) {
    const sheetData: (string | number | boolean)[][] = [sheet.columns];

    sheet.rows.forEach((r) => {
      sheetData.push(r);
      totalRows++;
    });

    if (sheet.summaryRow) {
      sheetData.push(sheet.summaryRow);
    }

    const ws = XLSX.utils.aoa_to_sheet(sheetData);

    // Auto-calculate column widths
    const colWidths = sheet.columns.map((col, cIdx) => {
      let maxLen = col.length;
      sheet.rows.forEach((row) => {
        const cell = row[cIdx];
        if (cell !== undefined && cell !== null) {
          maxLen = Math.max(maxLen, String(cell).length);
        }
      });
      return { wch: Math.min(Math.max(maxLen + 3, 10), 45) };
    });
    ws['!cols'] = colWidths;

    XLSX.utils.book_append_sheet(wb, ws, sheet.sheetName.slice(0, 31) || 'Sheet1');
    previewSnippets.push(`Sheet "${sheet.sheetName}": ${sheet.columns.join(', ')} (${sheet.rows.length} rows)`);
  }

  const base64Data = XLSX.write(wb, { type: 'base64', bookType: 'xlsx' });
  const sizeBytes = Math.floor((base64Data.length * 3) / 4);

  return {
    id: crypto.randomUUID(),
    name: cleanFilename,
    type: 'xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    sizeBytes,
    base64Data,
    createdAt: new Date().toISOString(),
    title: options.title || cleanFilename,
    description: options.description || `Excel Workbook (${options.sheets.length} sheets, ${totalRows} data rows)`,
    details: {
      sheetCount: options.sheets.length,
      rowCount: totalRows,
      previewContent: previewSnippets,
    },
  };
}

// ---------------------------------------------------------------------------
// 4. Microsoft PowerPoint (.pptx) Generator
// ---------------------------------------------------------------------------
export async function generatePptxFile(options: PptxGeneratorOptions): Promise<GeneratedFile> {
  const cleanFilename = options.filename.endsWith('.pptx') ? options.filename : `${options.filename}.pptx`;
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_16x9';
  pptx.title = options.title;
  pptx.subject = options.subtitle || 'Sovereign AI Executive Deck';
  pptx.author = options.presenter || 'Bastion Sovereign AI';

  const previewSnippets: string[] = [];

  // Theme Colors
  const BG_COLOR = '0B0F19'; // Obsidian Canvas
  const CARD_BG = '151C2C'; // Lifted Card Fill
  const ACCENT_COLOR = 'F97316'; // Bastion Signal Orange
  const TEXT_WHITE = 'F8FAFC';
  const TEXT_MUTED = '94A3B8';
  const BORDER_COLOR = '243048';

  // --- Slide 1: Cover / Title Slide ---
  const coverSlide = pptx.addSlide();
  coverSlide.background = { color: BG_COLOR };

  // Top Accent Stripe
  coverSlide.addShape(pptx.ShapeType.rect, {
    x: 0.8,
    y: 0.8,
    w: 0.6,
    h: 0.08,
    fill: { color: ACCENT_COLOR },
  });

  // Category eyebrow
  coverSlide.addText('BASTION SOVEREIGN AI · AIR-GAPPED WORKBENCH', {
    x: 0.8,
    y: 1.1,
    w: 11.5,
    h: 0.4,
    fontSize: 11,
    color: ACCENT_COLOR,
    bold: true,
    fontFace: 'Segoe UI',
  });

  // Main Deck Title
  coverSlide.addText(options.title, {
    x: 0.8,
    y: 1.8,
    w: 11.5,
    h: 2.2,
    fontSize: 36,
    color: TEXT_WHITE,
    bold: true,
    fontFace: 'Segoe UI',
    valign: 'top',
  });

  // Subtitle
  if (options.subtitle) {
    coverSlide.addText(options.subtitle, {
      x: 0.8,
      y: 4.2,
      w: 11.5,
      h: 1.2,
      fontSize: 18,
      color: TEXT_MUTED,
      fontFace: 'Segoe UI',
      valign: 'top',
    });
  }

  // Footer Metadata Bar
  coverSlide.addText(
    `Prepared for: ${options.presenter || 'Executive Leadership'}   |   Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}   |   Security: INTERNAL / STRICT AUDIT`,
    {
      x: 0.8,
      y: 6.5,
      w: 11.5,
      h: 0.4,
      fontSize: 10,
      color: '64748B',
      fontFace: 'Segoe UI',
    }
  );

  previewSnippets.push(`Slide 1: [Title] ${options.title}`);

  // --- Content Slides ---
  options.slides.forEach((slideData, idx) => {
    const slideNumber = idx + 2;
    const slide = pptx.addSlide();
    slide.background = { color: BG_COLOR };

    // Slide Header: Orange Accent + Eyebrow
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.8,
      y: 0.6,
      w: 0.4,
      h: 0.06,
      fill: { color: ACCENT_COLOR },
    });

    // Slide Title
    slide.addText(slideData.slideTitle, {
      x: 0.8,
      y: 0.75,
      w: 10.5,
      h: 0.8,
      fontSize: 24,
      color: TEXT_WHITE,
      bold: true,
      fontFace: 'Segoe UI',
    });

    if (slideData.subtitle) {
      slide.addText(slideData.subtitle, {
        x: 0.8,
        y: 1.55,
        w: 10.5,
        h: 0.4,
        fontSize: 13,
        color: ACCENT_COLOR,
        fontFace: 'Segoe UI',
      });
    }

    // Card background for content container
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: slideData.subtitle ? 2.1 : 1.7,
      w: 11.7,
      h: 4.6,
      rectRadius: 0.15,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
    });

    let currentY = (slideData.subtitle ? 2.1 : 1.7) + 0.3;

    // Body Text if present
    if (slideData.bodyText) {
      slide.addText(slideData.bodyText, {
        x: 1.2,
        y: currentY,
        w: 10.9,
        h: 1.0,
        fontSize: 15,
        color: TEXT_MUTED,
        fontFace: 'Segoe UI',
        valign: 'top',
      });
      currentY += 1.1;
    }

    // Bullet points
    if (slideData.bulletPoints && slideData.bulletPoints.length > 0) {
      const bulletItems = slideData.bulletPoints.map((bp) => ({
        text: `  ${bp}`,
        options: {
          fontSize: 15,
          color: TEXT_WHITE,
          bullet: { type: 'bullet', code: '2022' },
          breakLine: true,
        },
      }));

      slide.addText(bulletItems, {
        x: 1.2,
        y: currentY,
        w: 10.9,
        h: Math.max(4.6 - (currentY - (slideData.subtitle ? 2.1 : 1.7)) - 0.3, 1.0),
        fontFace: 'Segoe UI',
        lineSpacing: 26,
        valign: 'top',
      });
    }

    // Speaker notes
    if (slideData.speakerNotes) {
      slide.addNotes(slideData.speakerNotes);
    }

    // Footer with Slide Number
    slide.addText(`Slide ${slideNumber} of ${options.slides.length + 1}   ·   Bastion Sovereign AI Workbench`, {
      x: 0.8,
      y: 6.8,
      w: 11.7,
      h: 0.3,
      fontSize: 9,
      color: '475569',
      fontFace: 'Segoe UI',
    });

    previewSnippets.push(`Slide ${slideNumber}: ${slideData.slideTitle}`);
  });

  const base64Data = (await pptx.write({ outputType: 'base64' })) as string;
  const sizeBytes = Math.floor((base64Data.length * 3) / 4);

  return {
    id: crypto.randomUUID(),
    name: cleanFilename,
    type: 'pptx',
    mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    sizeBytes,
    base64Data,
    createdAt: new Date().toISOString(),
    title: options.title,
    description: options.subtitle || `PowerPoint Presentation (${options.slides.length + 1} slides)`,
    details: {
      slideCount: options.slides.length + 1,
      previewContent: previewSnippets,
    },
  };
}

// ---------------------------------------------------------------------------
// 5. Download Helper
// ---------------------------------------------------------------------------
export function downloadGeneratedFile(file: GeneratedFile): void {
  try {
    const byteCharacters = atob(file.base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: file.mimeType });
    const blobUrl = window.URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      window.URL.revokeObjectURL(blobUrl);
    }, 4000);
  } catch (err) {
    console.error('Download error:', err);
    const dataUrl = `data:${file.mimeType};base64,${file.base64Data}`;
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
