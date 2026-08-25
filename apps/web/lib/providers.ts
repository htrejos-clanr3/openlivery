// Supported AI providers (must match backend app/services/providers.py).
export const PROVIDERS = [
  {
    id: "openai",
    label: "OpenAI",
    keyPlaceholder: "sk-proj-...",
    keyUrl: "https://platform.openai.com/api-keys",
    models: [
      "gpt-5.6-sol",
      "gpt-5.6-terra",
      "gpt-5.6-luna",
      "gpt-5.5",
      "gpt-5.4",
      "gpt-5.4-mini",
      "gpt-5.4-nano",
      "gpt-5.2",
      "gpt-5.1",
      "gpt-5",
      "gpt-5-mini",
      "gpt-5-nano",
      "gpt-4.1",
      "gpt-4.1-mini",
      "gpt-4.1-nano",
    ],
  },
  {
    id: "anthropic",
    label: "Anthropic",
    keyPlaceholder: "sk-ant-...",
    keyUrl: "https://console.anthropic.com/settings/keys",
    models: [
      "claude-opus-4-8",
      "claude-opus-4-7",
      "claude-opus-4-6",
      "claude-sonnet-4-6",
      "claude-sonnet-4-5",
      "claude-haiku-4-5",
    ],
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    keyPlaceholder: "sk-...",
    keyUrl: "https://platform.deepseek.com/api_keys",
    models: ["deepseek-chat", "deepseek-reasoner"],
  },
  {
    id: "moonshot",
    label: "Kimi (Moonshot)",
    keyPlaceholder: "sk-...",
    keyUrl: "https://platform.moonshot.cn/console/api-keys",
    models: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-k2-0711-preview"],
  },
  {
    id: "dashscope",
    label: "Qwen (DashScope)",
    keyPlaceholder: "sk-...",
    keyUrl: "https://dashscope.console.aliyun.com/apiKey",
    models: ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
  },
] as const;

export type ProviderId = (typeof PROVIDERS)[number]["id"];

// Transcription models for the audio-recognition capability (OpenAI).
export const AUDIO_MODELS = ["gpt-transcribe", "whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "gpt-4o-transcribe-diarize"] as const;
// Vision-capable models for the image-recognition capability.
export const IMAGE_MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-4.1", "gpt-4.1-mini", "gpt-5.5", "gpt-5.4", "gpt-5", "gpt-5-mini"] as const;

export function providerById(id: string) {
  return PROVIDERS.find((p) => p.id === id);
}

export function providerLabel(id: string): string {
  return providerById(id)?.label ?? id;
}

export function modelsFor(id: string): readonly string[] {
  return providerById(id)?.models ?? [];
}

export function defaultModelFor(id: string): string {
  return modelsFor(id)[0] ?? "";
}

// ~4 characters per token: same approximation as the backend, for the token
// counter in the agent creation wizard.
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

// Approximate context window (in tokens) per model family, used only for the
// "context window usage" bar. Values are representative, not exact.
export function modelContextWindow(id: string): number {
  if (id.startsWith("gpt-4.1")) return 1_000_000;
  if (id.startsWith("gpt-5")) return 400_000;
  if (id.startsWith("claude")) return 200_000;
  if (id.startsWith("deepseek")) return 128_000;
  if (id.startsWith("moonshot") || id.startsWith("kimi")) return 128_000;
  if (id.startsWith("qwen")) return 128_000;
  return 128_000;
}

export function isOpenAIOnlyCapabilityProvider(id: string): boolean {
  return id !== "openai";
}
