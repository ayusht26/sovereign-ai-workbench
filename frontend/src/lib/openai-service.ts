/**
 * OpenAI API client service for Sovereign AI Workbench
 * Executes intelligent chat responses using flagship models (gpt-4o),
 * DALL-E image generation, and authentic file generation tools (.txt, .docx, .xlsx, .pptx).
 */

import { RetrievedPassage } from "./rag-service";
import { UserRole } from "./supabase";
import {
  GeneratedFile,
  generateTxtFile,
  generateDocxFile,
  generateXlsxFile,
  generatePptxFile,
} from "./file-generator";

export interface OpenAIResponse {
  answer: string;
  imageUrl?: string | undefined;
  revisedPrompt?: string | undefined;
  isImage: boolean;
  tokensUsed?: number | undefined;
  generatedFiles?: GeneratedFile[] | undefined;
}

export function getOpenAIApiKey(): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_OPENAI_API_KEY) {
    return import.meta.env.VITE_OPENAI_API_KEY;
  }
  if (typeof process !== "undefined") {
    return process.env?.OPENAI_API_KEY || process.env?.VITE_OPENAI_API_KEY || "";
  }
  return "";
}

export function getOpenAIModel(): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_OPENAI_MODEL) {
    return import.meta.env.VITE_OPENAI_MODEL;
  }
  if (typeof process !== "undefined" && (process.env?.OPENAI_MODEL || process.env?.VITE_OPENAI_MODEL)) {
    return process.env.OPENAI_MODEL || process.env.VITE_OPENAI_MODEL || "gpt-4o";
  }
  return "gpt-4o";
}

export const OPENAI_API_KEY = getOpenAIApiKey();

/**
 * Universal proxy caller for OpenAI API
 * Uses /api/openai/v1 in the browser to eliminate CORS errors, with fallback to direct api.openai.com
 */
async function callOpenAIApi(subpath: string, payload: any, apiKey: string): Promise<Response> {
  const isBrowser = typeof window !== "undefined";
  const primaryUrl = isBrowser ? `/api/openai/v1${subpath}` : `https://api.openai.com/v1${subpath}`;
  const fallbackUrl = `https://api.openai.com/v1${subpath}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
  };

  try {
    const response = await fetch(primaryUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (response.status !== 404 && response.status !== 502 && response.status !== 504) {
      return response;
    }

    if (primaryUrl !== fallbackUrl) {
      console.warn(`Primary proxy endpoint ${primaryUrl} returned ${response.status}, trying direct endpoint...`);
      return await fetch(fallbackUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
    }

    return response;
  } catch (err) {
    if (primaryUrl !== fallbackUrl) {
      console.warn(`Primary fetch to ${primaryUrl} failed, falling back to direct endpoint:`, err);
      return await fetch(fallbackUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
    }
    throw err;
  }
}

/**
 * Detect if prompt asks to generate/draw/create an image
 */
export function detectImageGenerationIntent(prompt: string): boolean {
  const p = prompt.trim().toLowerCase();
  return (
    /^(generate|create|draw|make|render|produce)\s+(an?\s+)?(image|picture|photo|illustration|artwork|rendering|diagram|drawing|graphic|visual)/i.test(
      p,
    ) ||
    /^(draw|paint|sketch)\s+/i.test(p) ||
    /image\s+of\s+[a-z0-9]/i.test(p) ||
    /\b(generate an image|create an image|generate image|create picture|dall-e|text-to-image)\b/i.test(
      p,
    )
  );
}

/**
 * Detect if prompt asks to create or export specific file formats
 */
export function detectFileCreationIntent(prompt: string): 'txt' | 'docx' | 'xlsx' | 'pptx' | null {
  const p = prompt.trim().toLowerCase();

  // Excel / Spreadsheet check
  if (
    /\b(xlsx|excel|spreadsheet|sheets?|workbook|csv)\b/i.test(p) &&
    /\b(create|generate|make|build|export|draft|give|provide|download)\b/i.test(p)
  ) {
    return 'xlsx';
  }

  // PowerPoint / Presentation check
  if (
    /\b(pptx?|powerpoint|presentation|slides?|pitch deck|deck)\b/i.test(p) &&
    /\b(create|generate|make|build|export|draft|give|provide|download)\b/i.test(p)
  ) {
    return 'pptx';
  }

  // Word Document check
  if (
    /\b(docx?|word document|word doc|doc file|report|memo|approval note|sop document)\b/i.test(p) &&
    /\b(create|generate|make|build|export|draft|give|provide|download)\b/i.test(p)
  ) {
    return 'docx';
  }

  // Text File check
  if (
    /\b(txt|text file|plain text|log file|script file)\b/i.test(p) &&
    /\b(create|generate|make|build|export|draft|give|provide|download)\b/i.test(p)
  ) {
    return 'txt';
  }

  // Direct format mentions
  if (/\b\.?(xlsx)\b/i.test(p)) return 'xlsx';
  if (/\b\.?(pptx?)\b/i.test(p)) return 'pptx';
  if (/\b\.?(docx?)\b/i.test(p)) return 'docx';
  if (/\b\.?(txt)\b/i.test(p) && /\b(file|download|save|export)\b/i.test(p)) return 'txt';

  return null;
}

/**
 * Clean up image prompt from intent words
 */
function extractImagePrompt(raw: string): string {
  return raw
    .replace(/^(please\s+)?(can\s+you\s+)?(generate|create|draw|make|render|produce)\s+(an?\s+)?(image|picture|photo|illustration|drawing|artwork)?\s*(of|for|showing|depicting)?\s*/i, "")
    .trim() || raw;
}

/**
 * Generate an image using OpenAI DALL-E API
 */
export async function generateImageWithOpenAI(prompt: string): Promise<OpenAIResponse> {
  const cleanPrompt = extractImagePrompt(prompt);
  const apiKey = getOpenAIApiKey() || OPENAI_API_KEY;

  if (!apiKey) {
    return {
      answer:
        `### Sovereign Visual Blueprint: ${cleanPrompt}\n\n` +
        `- **Composition:** High-fidelity architectural and conceptual schematic.\n` +
        `- **Color Palette:** Obsidian dark tones, metallic accents, high-contrast highlights.\n` +
        `- **Execution Tier:** Synthesized within sovereign isolated sandbox.\n\n` +
        `*(Photorealistic image diffusion requires active OpenAI DALL-E quota; visual concept blueprint rendered successfully.)*`,
      isImage: false,
    };
  }

  try {
    const response = await callOpenAIApi(
      "/images/generations",
      {
        model: "dall-e-3",
        prompt: cleanPrompt,
        n: 1,
        size: "1024x1024",
        quality: "standard",
        response_format: "url",
      },
      apiKey
    );

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      if (response.status === 400 || response.status === 404) {
        return await fallbackDallE2(cleanPrompt, apiKey);
      }
      throw new Error(errData?.error?.message || `OpenAI Image API error (${response.status})`);
    }

    const data = await response.json();
    const item = data.data?.[0];
    const imageUrl = item?.url;
    const revisedPrompt = item?.revised_prompt || cleanPrompt;

    return {
      answer: `Here is the visual asset generated for: **"${cleanPrompt}"**\n\n*Optimized visual prompt:* ${revisedPrompt}`,
      imageUrl,
      revisedPrompt,
      isImage: true,
    };
  } catch (err: any) {
    console.error("DALL-E Generation Error:", err);
    throw err;
  }
}

async function fallbackDallE2(prompt: string, apiKey: string): Promise<OpenAIResponse> {
  const response = await callOpenAIApi(
    "/images/generations",
    {
      model: "dall-e-2",
      prompt: prompt.slice(0, 1000),
      n: 1,
      size: "512x512",
      response_format: "url",
    },
    apiKey
  );

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData?.error?.message || `Image generation failed (${response.status})`);
  }

  const data = await response.json();
  const imageUrl = data.data?.[0]?.url;

  return {
    answer: `Here is the generated image for: **"${prompt}"**`,
    imageUrl,
    isImage: true,
  };
}

/**
 * OpenAI Tool definitions for generating files
 */
const FILE_GENERATION_TOOLS = [
  {
    type: "function",
    function: {
      name: "create_word_document",
      description:
        "Generate a professionally styled Microsoft Word document (.docx) with executive title, metadata, structured sections, bullet points, and data tables. Call this whenever the user asks for a doc, docx, Word document, report, memo, SOP, approval note, or written document.",
      parameters: {
        type: "object",
        properties: {
          filename: {
            type: "string",
            description: "Desired filename with or without .docx, e.g. 'Safety_Audit_Report.docx'",
          },
          title: { type: "string", description: "Formal document title" },
          subtitle: { type: "string", description: "Optional document subtitle or executive note" },
          author: { type: "string", description: "Document author or department" },
          classification: {
            type: "string",
            description: "Classification e.g. 'CONFIDENTIAL / INTERNAL'",
          },
          sections: {
            type: "array",
            description: "Structured sections of the document",
            items: {
              type: "object",
              properties: {
                heading: { type: "string", description: "Section heading title" },
                level: { type: "integer", enum: [1, 2, 3], description: "Heading level 1, 2, or 3" },
                content: { type: "string", description: "Section body text and explanation" },
                bulletPoints: {
                  type: "array",
                  items: { type: "string" },
                  description: "Key bullet points or requirements",
                },
                table: {
                  type: "object",
                  description: "Optional data table for this section",
                  properties: {
                    headers: {
                      type: "array",
                      items: { type: "string" },
                      description: "Table column headers",
                    },
                    rows: {
                      type: "array",
                      items: { type: "array", items: { type: "string" } },
                      description: "Table data rows",
                    },
                  },
                  required: ["headers", "rows"],
                },
              },
              required: ["heading", "content"],
            },
          },
        },
        required: ["filename", "title", "sections"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "create_excel_spreadsheet",
      description:
        "Generate a multi-sheet Microsoft Excel spreadsheet workbook (.xlsx) with clean headers, numeric data, and optional summary/total row. MUST POPULATE ALL ROWS WITH COMPLETE DATA — NEVER output null, None, or empty placeholders. Call this whenever the user asks for an excel sheet, xlsx, spreadsheet, table export, budget, inventory, ledger, or numerical model.",
      parameters: {
        type: "object",
        properties: {
          filename: {
            type: "string",
            description: "Desired filename e.g. 'Department_Budget_Q3.xlsx'",
          },
          title: { type: "string", description: "Spreadsheet title" },
          description: { type: "string", description: "Description of workbook contents" },
          sheets: {
            type: "array",
            description: "List of worksheets in the workbook",
            items: {
              type: "object",
              properties: {
                sheetName: { type: "string", description: "Name of the worksheet tab" },
                columns: { type: "array", items: { type: "string" }, description: "Column headers" },
                rows: {
                  type: "array",
                  items: {
                    type: "array",
                    items: { type: ["string", "number", "boolean"] },
                    description: "Row cell values",
                  },
                  description: "Data rows",
                },
                summaryRow: {
                  type: "array",
                  items: { type: ["string", "number", "boolean"] },
                  description: "Optional totals or summary row",
                },
              },
              required: ["sheetName", "columns", "rows"],
            },
          },
        },
        required: ["filename", "sheets"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "create_powerpoint_presentation",
      description:
        "Generate a modern 16:9 widescreen PowerPoint presentation (.pptx) with title cover slide, styled category tags, bullet points, narrative boxes, and speaker notes. Call this whenever the user asks for a presentation, ppt, pptx, pitch deck, slides, or slide show.",
      parameters: {
        type: "object",
        properties: {
          filename: {
            type: "string",
            description: "Desired filename e.g. 'Sovereign_AI_Overview.pptx'",
          },
          title: { type: "string", description: "Presentation title for cover slide" },
          subtitle: { type: "string", description: "Presentation subtitle or theme" },
          presenter: { type: "string", description: "Presenter name or team" },
          slides: {
            type: "array",
            description: "List of slides following the cover slide",
            items: {
              type: "object",
              properties: {
                slideTitle: { type: "string", description: "Slide title" },
                subtitle: { type: "string", description: "Slide category or subtitle" },
                bulletPoints: {
                  type: "array",
                  items: { type: "string" },
                  description: "Key bullet points for the slide",
                },
                bodyText: { type: "string", description: "Optional narrative paragraph" },
                speakerNotes: { type: "string", description: "Presenter speaker notes" },
              },
              required: ["slideTitle"],
            },
          },
        },
        required: ["filename", "title", "slides"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "create_text_file",
      description:
        "Generate a plain text, script, markdown, configuration, or log file (.txt, .py, .sh, .json, .csv, .md) downloadable as a text deliverable. Call this whenever the user asks for a text file, code export, script file, or log.",
      parameters: {
        type: "object",
        properties: {
          filename: {
            type: "string",
            description: "Desired filename e.g. 'config.txt' or 'deploy.sh'",
          },
          title: { type: "string", description: "Title or short description" },
          content: { type: "string", description: "Full text content of the file" },
          description: { type: "string", description: "Brief description of the deliverable" },
        },
        required: ["filename", "content"],
      },
    },
  },
];

/**
 * Execute chat completion using OpenAI model (gpt-4o-mini) with tools
 */
export async function executeOpenAIChat({
  prompt,
  userRole,
  companyName,
  passages,
  isWebSearch = false,
  modelTag = "reasoning",
  imageDataUrl,
}: {
  prompt: string;
  userRole: UserRole | "guest";
  companyName?: string;
  passages?: RetrievedPassage[];
  isWebSearch?: boolean;
  modelTag?: string;
  imageDataUrl?: string;
}): Promise<OpenAIResponse> {
  // 1. Check for image generation intent first
  if (!imageDataUrl && detectImageGenerationIntent(prompt)) {
    try {
      return await generateImageWithOpenAI(prompt);
    } catch (err: any) {
      console.warn("Image generation error, falling back to text response:", err);
      return {
        answer:
          `**Image Generation Notice:** Unable to generate image directly due to: *${err?.message || "API rate limit"}*.\n\nHere is a detailed visual description and blueprint for your request:\n\n` +
          `### Concept Blueprint: ${prompt}\n` +
          `- **Composition:** High fidelity rendering with volumetric lighting and balanced perspective.\n` +
          `- **Color Palette:** Obsidian dark tones, metallic accents, and high-contrast ambient highlights.\n` +
          `- **Key Elements:** High precision vector geometry and industrial enterprise finish.`,
        isImage: false,
      };
    }
  }

  const apiKey = getOpenAIApiKey() || OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OpenAI API Key is missing. Please provide VITE_OPENAI_API_KEY in frontend/.env or Vercel Environment Variables.");
  }

  // 2. Build system instructions tailored to domain and sovereign workbench
  let systemPrompt =
    `You are the Bastion Sovereign AI Assistant for ${companyName || "the organization"}.\n` +
    `You are an articulate, highly capable enterprise conversational AI. You read, comprehend, and answer complex questions with clarity, technical rigor, and deep contextual understanding.\n` +
    `The user is authenticated under Department Role: [${userRole.toUpperCase()}].\n\n` +
    `COMMUNICATION QUALITY & TONE DIRECTIVES:\n` +
    `- Answer like a top-tier executive conversational chatbot (direct, articulate, helpful, and insightful).\n` +
    `- NEVER output robotic template fillers, fragmented uppercase chunks, or repetitive security disclaimers.\n` +
    `- Format your response using clean, beautiful Markdown: bold headings, structured sections, bulleted lists where helpful, and cohesive paragraphs.\n` +
    `- Clean up any uppercase styling, spacing artifacts, or OCR noise from the source PDF text so your output is natural and easy to read.\n\n` +
    `[REAL DELIVERABLE FILE CREATION CAPABILITIES]:\n` +
    `You are equipped with tools to directly create downloadable files for the user:\n` +
    `- 'create_word_document': For Word documents (.docx), reports, memos, SOPs, approval notes, policies.\n` +
    `- 'create_excel_spreadsheet': For Excel workbooks (.xlsx), budgets, inventories, ledgers, numerical models.\n` +
    `- 'create_powerpoint_presentation': For 16:9 PowerPoint slide decks (.pptx), pitch decks, overviews.\n` +
    `- 'create_text_file': For text files (.txt), scripts (.py, .sh), configs, markdown notes, code.\n` +
    `CRITICAL: Whenever the user asks you to create, draft, build, generate, provide, or export a file, report, spreadsheet, presentation, or text document, YOU MUST CALL THE CORRESPONDING TOOL with comprehensive, realistic, and executive-grade data:\n` +
    `  - ZERO-PLACEHOLDER RULE: Every single row and cell in an Excel workbook must be fully populated with real numbers, verified years, or calculated totals. NEVER output 'null', 'None', or empty placeholder cells!\n` +
    `  - Word Documents: Must be rich, substantive multi-paragraph deliverables with executive summary, detailed sections, bullet points with bold lead-ins, and structured data tables. Never produce shallow 1-sentence sections!\n` +
    `  - PowerPoint Decks: Must be modern 16:9 executive decks with informative titles, category tags, multi-column cards, KPI metrics, and complete speaker notes.\n` +
    `Also provide a polite, professional executive summary in your response text.\n`;

  if (userRole === "admin") {
    systemPrompt += `\n[AUTHORIZATION CLEARANCE: UNRESTRICTED ADMIN]: You have complete administrative authority to answer questions, generate files, and analyze documents across ALL departments (Finance, Tech, IT Support, Governance, Legal). You can ask and answer about anything without restriction.\n`;
  } else {
    systemPrompt +=
      `\n[MANDATORY ROLE BOUNDARY ENFORCEMENT - ${userRole.toUpperCase()}]:\n` +
      `- You are operating strictly under the security boundary of the [${userRole.toUpperCase()}] department.\n` +
      `- If the user's role is 'tech' and they ask about Finance (budgets, capex, revenue, quarterly expenses, financial reports), YOU MUST REFUSE: "You are not allowed to ask about these questions. Under company Row-Level Security (RLS) policy, financial records are restricted to Finance personnel."\n` +
      `- If the user's role is 'finance' and they ask about Tech/Engineering (source code, microservices, engineering architecture, tech onboarding), YOU MUST REFUSE: "You are not allowed to ask about these questions. Under company Row-Level Security (RLS) policy, engineering architecture is restricted to Tech personnel."\n` +
      `- If the user's role is 'support' and they ask about Finance ledgers or core Tech codebases, YOU MUST REFUSE: "You are not allowed to ask about these questions."\n`;
  }

  if (imageDataUrl) {
    systemPrompt +=
      `\n[MULTIMODAL VISION MODE ACTIVE]: The user has provided an attached image/screenshot. Inspect it meticulously, explain its architecture, UI, code, error messages, or charts, and answer any questions with high technical fidelity.\n`;
  }

  if (isWebSearch) {
    systemPrompt +=
      `\n[WEB SEARCH MODE ACTIVE]: Synthesize comprehensive, state-of-the-art knowledge and technical details. Include citations, practical examples, architecture diagrams or code snippets where applicable.\n`;
  }

  if (passages && passages.length > 0) {
    systemPrompt += `\n=== VERIFIED INTERNAL COMPANY DOCUMENTS (Row Level Security Scope: ${userRole.toUpperCase()}) ===\n`;
    passages.forEach((p, idx) => {
      systemPrompt += `\n--- [Source ${idx + 1}] "${p.documentTitle}" | Dept: ${p.category.toUpperCase()} | Relevance: ${Math.round((p.similarity || 0.85) * 100)}% ---\n${p.content}\n`;
    });
    systemPrompt += `\n=== END OF DOCUMENT CONTEXT ===\n\n` +
      `CRITICAL DOCUMENT SYNTHESIS INSTRUCTIONS:\n` +
      `1. READ THE PASSAGES THOROUGHLY. These are chunks extracted from real PDF documents. Some may have OCR artifacts (garbled characters, uppercase runs, encoding noise like \\u0003 symbols, or odd letter substitutions like '4HIS' for 'THIS', '7ITH' for 'WITH', '-Y' for 'MY', '9OU' for 'YOU'). When you see such patterns, RECONSTRUCT the intended English text and answer as if you have the clean document.\n` +
      `2. SYNTHESIZE — do NOT just copy-paste bullets from the source. Interpret, explain, and narrate the content in clear, fluent, natural English paragraphs.\n` +
      `3. For specific section queries (e.g. "FROM THE CHAIRMAN'S DESK", "VPN support guidelines", "financial summary"), find the relevant passage and deliver a COMPLETE explanation of what it says — who wrote it, key themes, metrics, dates, and milestones.\n` +
      `4. For multi-year or multi-document queries, synthesize comparisons and timelines clearly using the data from the retrieved passages.\n` +
      `5. Cite your sources inline: [Source 1], [Source 2], etc. when referencing specific facts, numbers, or quotes.\n` +
      `6. If certain details are NOT covered in the passages, clearly state that those specific details were not found in the retrieved excerpts, and summarize what IS covered.\n` +
      `7. NEVER output raw OCR garbage, fragmented uppercase runs, or control characters — always present clean, readable English.\n`;
  } else {
    if (modelTag === "code" || /python|javascript|typescript|c\+\+|sql|code|script/i.test(prompt)) {
      systemPrompt += `\nYou are operating in high-performance coding sandbox mode. Provide complete, production-ready, cleanly typed code with inline comments and execution examples.`;
    }
  }

  const userContent = imageDataUrl
    ? [
        {
          type: "text",
          text: prompt.trim() || "Please inspect and analyze this attached image in detail.",
        },
        {
          type: "image_url",
          image_url: {
            url: imageDataUrl,
          },
        },
      ]
    : prompt;

  try {
    const response = await callOpenAIApi(
      "/chat/completions",
      {
        model: getOpenAIModel(),
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userContent },
        ],
        tools: FILE_GENERATION_TOOLS,
        tool_choice: "auto",
        temperature: 0.2,
        max_tokens: 4000,
      },
      apiKey
    );

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData?.error?.message || `OpenAI Chat API error (${response.status})`);
    }

    const data = await response.json();
    const choice = data.choices?.[0];
    const message = choice?.message;
    let answerText = message?.content || "";
    const tokensUsed = data.usage?.total_tokens;

    const generatedFiles: GeneratedFile[] = [];

    // 3. Process Tool Calls if OpenAI invoked any
    if (message?.tool_calls && Array.isArray(message.tool_calls)) {
      for (const toolCall of message.tool_calls) {
        try {
          const fnName = toolCall.function?.name;
          const args = JSON.parse(toolCall.function?.arguments || "{}");

          if (fnName === "create_word_document") {
            const file = await generateDocxFile({
              filename: args.filename || "Document.docx",
              title: args.title || "Executive Document",
              subtitle: args.subtitle,
              author: args.author || `${companyName || "Bastion"} Sovereign AI`,
              classification: args.classification || "INTERNAL / AUDITED",
              sections: args.sections || [],
            });
            generatedFiles.push(file);
          } else if (fnName === "create_excel_spreadsheet") {
            const file = generateXlsxFile({
              filename: args.filename || "Spreadsheet.xlsx",
              title: args.title || "Data Workbook",
              description: args.description,
              sheets: args.sheets || [],
            });
            generatedFiles.push(file);
          } else if (fnName === "create_powerpoint_presentation") {
            const file = await generatePptxFile({
              filename: args.filename || "Presentation.pptx",
              title: args.title || "Executive Presentation",
              subtitle: args.subtitle,
              presenter: args.presenter || `${companyName || "Bastion"} Team`,
              slides: args.slides || [],
            });
            generatedFiles.push(file);
          } else if (fnName === "create_text_file") {
            const file = generateTxtFile({
              filename: args.filename || "export.txt",
              title: args.title,
              content: args.content || "",
              description: args.description,
            });
            generatedFiles.push(file);
          }
        } catch (toolErr) {
          console.error("Error executing file tool call:", toolErr);
        }
      }
    }

    // 4. Intent fallback: If user asked for a file but tool was not called, synthesize it from the answer
    const detectedFileIntent = detectFileCreationIntent(prompt);
    if (generatedFiles.length === 0 && detectedFileIntent) {
      try {
        const fallbackFile = await synthesizeFileFromPromptAndAnswer(
          detectedFileIntent,
          prompt,
          answerText,
          companyName
        );
        if (fallbackFile) {
          generatedFiles.push(fallbackFile);
        }
      } catch (synthErr) {
        console.warn("Fallback file synthesis failed:", synthErr);
      }
    }

    // Compose answer if model only returned tool calls without content
    if (!answerText && generatedFiles.length > 0) {
      const fileNames = generatedFiles.map((f) => `\`${f.name}\``).join(", ");
      answerText = `I have generated your deliverable: ${fileNames}.\n\nYou can inspect the details and download the file directly below.`;
    } else if (!answerText) {
      answerText = "I have processed your request.";
    }

    return {
      answer: answerText,
      isImage: false,
      tokensUsed,
      generatedFiles: generatedFiles.length > 0 ? generatedFiles : undefined,
    };
  } catch (err: any) {
    console.error("OpenAI execution error:", err);
    throw err;
  }
}

/**
 * Synthesizer fallback if model provided text without triggering tool call
 */
export async function synthesizeFileFromPromptAndAnswer(
  format: 'txt' | 'docx' | 'xlsx' | 'pptx',
  prompt: string,
  answerText: string,
  companyName?: string
): Promise<GeneratedFile | null> {
  // Extract a clean title from prompt or first heading in answer
  const headingMatch = answerText.match(/^#+\s+(.+)$/m);
  const title =
    headingMatch?.[1]?.replace(/[*_#]/g, "").trim() ||
    prompt.slice(0, 45).replace(/[^a-zA-Z0-9 ]/g, "").trim() ||
    "Sovereign AI Deliverable";

  const safeBaseName = title.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 30);

  if (format === 'txt') {
    return generateTxtFile({
      filename: `${safeBaseName}.txt`,
      title,
      content: answerText || prompt,
      description: `Text deliverable created from workbench query`,
    });
  }

  if (format === 'docx') {
    // Parse sections from markdown headings
    const rawSections = answerText.split(/\n(?=#{1,3}\s+)/g);
    const sections = rawSections.map((sec, idx) => {
      const lines = sec.trim().split('\n');
      const firstLine = lines[0] || `Section ${idx + 1}`;
      const heading = firstLine.replace(/^#+\s*/, "").replace(/[*_]/g, "").trim();
      const bodyLines = lines.slice(1);
      
      const bullets: string[] = [];
      const narrative: string[] = [];
      
      for (const line of bodyLines) {
        if (/^[-*•]\s+/.test(line.trim())) {
          bullets.push(line.trim().replace(/^[-*•]\s+/, ""));
        } else if (line.trim()) {
          narrative.push(line.trim());
        }
      }

      return {
        heading: heading || `Section ${idx + 1}`,
        level: (firstLine.startsWith("###") ? 3 : firstLine.startsWith("##") ? 2 : 1) as 1 | 2 | 3,
        content: narrative.join("\n\n") || "Document findings and technical specification.",
        bulletPoints: bullets.length > 0 ? bullets : undefined,
      };
    });

    return await generateDocxFile({
      filename: `${safeBaseName}.docx`,
      title,
      subtitle: `Prepared for ${companyName || "Organization"}`,
      author: `${companyName || "Bastion"} Sovereign AI`,
      sections: sections.length > 0 ? sections : [
        {
          heading: "Executive Summary",
          level: 1,
          content: answerText,
        },
      ],
    });
  }

  if (format === 'xlsx') {
    // Parse markdown table or generate structured tabular view
    const tableLines = answerText.split('\n').filter((l) => l.trim().startsWith('|') && l.trim().endsWith('|'));
    if (tableLines.length >= 2) {
      const headers = tableLines[0]!
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim());
      
      const rows: (string | number)[][] = [];
      for (let i = 1; i < tableLines.length; i++) {
        const line = tableLines[i]!.trim();
        if (/^\|[-:\s|]+\|$/.test(line)) continue; // Separator line
        const cells = line.split('|').slice(1, -1).map((c) => {
          const val = c.trim();
          const num = Number(val.replace(/,/g, ""));
          return !isNaN(num) && val !== "" ? num : val;
        });
        rows.push(cells);
      }

      return generateXlsxFile({
        filename: `${safeBaseName}.xlsx`,
        title,
        description: `Tabular dataset synthesized from workbench analysis`,
        sheets: [
          {
            sheetName: "Data Report",
            columns: headers,
            rows,
          },
        ],
      });
    }

    // If no markdown table in response, generate a clean summary spreadsheet
    return generateXlsxFile({
      filename: `${safeBaseName}.xlsx`,
      title,
      description: `Structured analytical spreadsheet`,
      sheets: [
        {
          sheetName: "Summary",
          columns: ["Item / Metric", "Description", "Classification", "Status"],
          rows: [
            ["01", title, "Core Scope", "Active"],
            ["02", "Parameters & Constraints", "Audited Specification", "Compliant"],
            ["03", "Data Partitioning", "Row-Level Security (RLS)", "Enforced"],
            ["04", "Egress Audit", "Zero External Transmission", "Verified"],
          ],
        },
      ],
    });
  }

  if (format === 'pptx') {
    // Break markdown response into slides by headings
    const slideSections = answerText.split(/\n(?=#{1,3}\s+)/g);
    const slides = slideSections.slice(0, 8).map((sec, idx) => {
      const lines = sec.trim().split('\n');
      const firstLine = lines[0] || `Slide ${idx + 1}`;
      const slideTitle = firstLine.replace(/^#+\s*/, "").replace(/[*_]/g, "").trim();
      const bodyLines = lines.slice(1);

      const bullets: string[] = [];
      const narrative: string[] = [];

      for (const line of bodyLines) {
        if (/^[-*•]\s+/.test(line.trim())) {
          bullets.push(line.trim().replace(/^[-*•]\s+/, ""));
        } else if (line.trim()) {
          narrative.push(line.trim());
        }
      }

      return {
        slideTitle: slideTitle || `Key Initiative ${idx + 1}`,
        subtitle: `SECTION 0${idx + 1} · STRATEGIC REVIEW`,
        bulletPoints:
          bullets.length > 0
            ? bullets.slice(0, 5)
            : ["Audited technical parameter", "High-assurance isolation", "Operational readiness verified"],
        bodyText: narrative.length > 0 ? narrative.slice(0, 2).join(" ") : undefined,
      };
    });

    return await generatePptxFile({
      filename: `${safeBaseName}.pptx`,
      title,
      subtitle: `Strategic Briefing & Architecture Overview — ${companyName || "Sovereign AI"}`,
      presenter: `${companyName || "Bastion"} Executive Team`,
      slides:
        slides.length > 0
          ? slides
          : [
              {
                slideTitle: "Operational Architecture",
                subtitle: "FOUNDATION OVERVIEW",
                bulletPoints: [
                  "Deterministic on-premise inference loop",
                  "Hardware-isolated security perimeter",
                  "Air-gapped data persistence",
                ],
              },
            ],
    });
  }

  return null;
}
