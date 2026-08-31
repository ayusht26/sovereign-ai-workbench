/**
 * OpenAI API client service for Sovereign AI Workbench
 * Executes intelligent chat responses using cost-effective models (gpt-4o-mini)
 * and DALL-E image generation with download capability.
 */

import { RetrievedPassage } from "./rag-service";
import { UserRole } from "./supabase";

export interface OpenAIResponse {
  answer: string;
  imageUrl?: string;
  revisedPrompt?: string;
  isImage: boolean;
  tokensUsed?: number;
}

const OPENAI_API_KEY =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_OPENAI_API_KEY) ||
  (typeof process !== "undefined" ? process.env?.OPENAI_API_KEY || process.env?.VITE_OPENAI_API_KEY : "") ||
  "";

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
  const apiKey = OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("OpenAI API Key is not configured in .env (VITE_OPENAI_API_KEY)");
  }

  try {
    const response = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "dall-e-3",
        prompt: cleanPrompt,
        n: 1,
        size: "1024x1024",
        quality: "standard",
        response_format: "url",
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      // If DALL-E-3 fails (quota or model availability), try DALL-E-2
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
  const response = await fetch("https://api.openai.com/v1/images/generations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "dall-e-2",
      prompt: prompt.slice(0, 1000),
      n: 1,
      size: "512x512",
      response_format: "url",
    }),
  });

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
 * Execute chat completion using cost-effective OpenAI model (gpt-4o-mini)
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
  // 1. Check for image generation intent first (only if no image was attached to analyze)
  if (!imageDataUrl && detectImageGenerationIntent(prompt)) {
    try {
      return await generateImageWithOpenAI(prompt);
    } catch (err: any) {
      console.warn("Image generation error, falling back to text response:", err);
      return {
        answer: `**Image Generation Notice:** Unable to generate image directly due to: *${err?.message || "API rate limit"}*.\n\nHere is a detailed visual description and blueprint for your request:\n\n` +
          `### Concept Blueprint: ${prompt}\n` +
          `- **Composition:** High fidelity rendering with volumetric lighting and balanced perspective.\n` +
          `- **Color Palette:** Obsidian dark tones, metallic accents, and high-contrast ambient highlights.\n` +
          `- **Key Elements:** High precision vector geometry and industrial enterprise finish.`,
        isImage: false,
      };
    }
  }

  const apiKey = OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OpenAI API Key is missing in environment (VITE_OPENAI_API_KEY)");
  }

  // 2. Build system instructions tailored to domain and sovereign workbench
  let systemPrompt =
    `You are the Bastion Sovereign AI Assistant for ${companyName || "the organization"}.\n` +
    `The user is authenticated under Department Role: [${userRole.toUpperCase()}].\n` +
    `You provide authoritative, precise, professional, and well-structured technical answers.\n` +
    `Use clean Markdown formatting, code fences with syntax highlighting, bullet points, and concise executive summaries.\n`;

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
      systemPrompt += `[Document ${idx + 1}: ${p.documentTitle} | Category: ${p.category.toUpperCase()}]\n${p.content}\n\n`;
    });
    systemPrompt += `Ground your answer directly in these verified passages. Highlight specific metrics, clauses, parameters, and SLAs from the texts when available.`;
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
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini", // Cost-effective, ultra fast, high intelligence with vision
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userContent },
        ],
        temperature: 0.3,
        max_tokens: 1800,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData?.error?.message || `OpenAI Chat API error (${response.status})`);
    }

    const data = await response.json();
    const choice = data.choices?.[0];
    const answer = choice?.message?.content || "No response content generated.";
    const tokensUsed = data.usage?.total_tokens;

    return {
      answer,
      isImage: false,
      tokensUsed,
    };
  } catch (err: any) {
    console.error("OpenAI execution error:", err);
    throw err;
  }
}
