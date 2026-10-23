/**
 * UNIT-24 scripted, opt-in speech assessment proxy.
 * No recording or Azure key is persisted. Deliberately OFF unless explicitly enabled.
 *
 * Paid calls require Redis-backed atomic hourly/daily budgets. All failures fail closed.
 * A separate Vercel WAF rule and Azure billing alerts remain strongly recommended.
 */
import { createHmac } from "node:crypto";
// This function is self-contained because the Vercel Node ESM runtime does not
// resolve frontend TS directory imports. Update this allowlist with approved lessons.
const allowedReferences = [
  "ten one", "ten two", "ten five", "ten seven", "ten nine",
  "ten thirteen", "ten fourteen", "ten fifteen", "ten seventeen",
  "ten twenty", "ten twenty one", "ten twenty two", "ten twenty three",
  "ten twenty eight", "ten thirty", "ten thirty one", "ten thirty five",
  "ten thirty six", "eleven twenty seven", "eleven forty one",
  "eleven eighty two", "eleven eighty three", "eleven eighty six",
  "eleven ninety eight",
  "Adam", "Boy", "Charles", "David", "Edward", "Frank", "George",
  "Henry", "Ida", "John", "King", "Lincoln", "Mary", "Nora",
  "Ocean", "Paul", "Queen", "Robert", "Sam", "Tom", "Union",
  "Victor", "William", "Xray", "Yellow", "Zebra",
  "Good evening. Do you know why I pulled you over?",
  "I'm not sure. Could you tell me why?",
  "Sorry, could you repeat that?",
  "I guess I was speeding.",
  "I asked whether you know why I stopped your car.",
  "Thanks for repeating that. I'm not sure.",
  "Could you explain why you stopped me?",
  "One of your brake lights appears to be out.",
  "Thank you for letting me know. I didn't realize that.",
  "Could you clarify which brake light you mean?",
  "The left brake light, at the back of the car.",
  "Thanks for clarifying.",
  "Got it. Thank you.",
] as const;
const allowedPhrases = new Map(allowedReferences.map(phrase => [phrase.toLowerCase(), phrase]));

function score(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
}
function obj(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : {};
}
function normalizeAzureAssessment(payload: unknown, referenceText: string) {
  const root = obj(payload);
  if (root.RecognitionStatus !== "Success") throw new Error("SPEECH_NOT_RECOGNIZED");
  const best = Array.isArray(root.NBest) ? obj(root.NBest[0]) : {};
  if (best.PronScore === undefined || best.AccuracyScore === undefined) {
    throw new Error("ASSESSMENT_NOT_AVAILABLE");
  }
  const words = Array.isArray(best.Words) ? best.Words.slice(0, 50).map((input: unknown) => {
    const word = obj(input);
    return {
      text: typeof word.Word === "string" ? word.Word.slice(0, 80) : "",
      accuracy: score(word.AccuracyScore),
      errorType: typeof word.ErrorType === "string" ? word.ErrorType.slice(0, 48) : null,
      phonemes: Array.isArray(word.Phonemes) ? word.Phonemes.slice(0, 24).map((p: unknown) => {
        const phoneme = obj(p);
        return { sound: typeof phoneme.Phoneme === "string" ? phoneme.Phoneme.slice(0, 24) : "",
          accuracy: score(phoneme.AccuracyScore) };
      }) : [],
    };
  }).filter((word: { text: string }) => word.text.length > 0) : [];
  return {
    provider: "azure-pronunciation-assessment",
    referenceText, recognizedText: typeof root.DisplayText === "string" ? root.DisplayText.slice(0, 320)
      : typeof best.Display === "string" ? best.Display.slice(0, 320) : "",
    scores: { overall: score(best.PronScore), accuracy: score(best.AccuracyScore),
      fluency: score(best.FluencyScore), completeness: score(best.CompletenessScore),
      prosody: score(best.ProsodyScore) },
    words,
  };
}

export const maxDuration = 20;
const MAX_WAV_BYTES = 44 + 16000 * 2 * 21;
const LIMIT_PER_IP_HOUR = 8;
const LIMIT_GLOBAL_MINUTE = 10;
const LIMIT_GLOBAL_DAY = 50;

// This script runs atomically in the Redis database. Check all counters before
// writing to any of them. A failed reservation causes zero Azure billable calls.
const QUOTA_SCRIPT = `
  for i = 1, #KEYS do
    local current = tonumber(redis.call("GET", KEYS[i]) or "0")
    if current >= tonumber(ARGV[i]) then return {0, i} end
  end
  for i = 1, #KEYS do
    local n = redis.call("INCR", KEYS[i])
    if n == 1 then redis.call("EXPIRE", KEYS[i], tonumber(ARGV[i + #KEYS])) end
  end
  return {1, 0}
`;

function limiterConfigured(): boolean {
  const raw = process.env.UPSTASH_REDIS_REST_URL ?? "";
  try {
    const url = new URL(raw);
    return url.protocol === "https:"
      && url.hostname.endsWith(".upstash.io")
      && url.username === "" && url.password === ""
      && url.pathname === "/" && !url.search && !url.hash
      && (process.env.UPSTASH_REDIS_REST_TOKEN?.length ?? 0) >= 12
      && (process.env.UNIT24_SPEECH_IP_HASH_SECRET?.length ?? 0) >= 32;
  } catch { return false; }
}
function enabled(): boolean {
  return process.env.UNIT24_SPEECH_ASSESSMENT_ENABLED === "true"
    && Boolean(process.env.AZURE_SPEECH_KEY)
    && /^[a-z0-9-]{3,40}$/.test(process.env.AZURE_SPEECH_REGION ?? "")
    && limiterConfigured();
}

/** Redis stores an HMAC-derived bucket identifier, never a raw client IP. */
async function reserveQuota(request: Request): Promise<"allowed" | "limited" | "unavailable"> {
  const ip = (request.headers.get("x-vercel-forwarded-for")
    ?? request.headers.get("x-forwarded-for") ?? "").split(",")[0]?.trim() ?? "";
  if (!ip || ip.length > 64 || !/^[a-fA-F0-9.:]+$/.test(ip)) return "unavailable";
  const ipId = createHmac("sha256", process.env.UNIT24_SPEECH_IP_HASH_SECRET!)
    .update(ip).digest("hex").slice(0, 32);
  const now = Date.now();
  const keys = [
    `unit24:speech:ip-hour:${ipId}:${Math.floor(now / 3600_000)}`,
    `unit24:speech:global-minute:${Math.floor(now / 60_000)}`,
    `unit24:speech:global-day:${Math.floor(now / 86400_000)}`,
  ];
  try {
    const response = await fetch(process.env.UPSTASH_REDIS_REST_URL!, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN!}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(["EVAL", QUOTA_SCRIPT, 3, ...keys,
        LIMIT_PER_IP_HOUR, LIMIT_GLOBAL_MINUTE, LIMIT_GLOBAL_DAY,
        3700, 75, 90000]),
      cache: "no-store",
      signal: AbortSignal.timeout(3500),
    });
    if (!response.ok) return "unavailable";
    const data: unknown = await response.json();
    if (!data || typeof data !== "object" || !("result" in data)) return "unavailable";
    const values = (data as { result?: unknown }).result;
    if (!Array.isArray(values) || values.length !== 2) return "unavailable";
    if (Number(values[0]) === 1 && Number(values[1]) === 0) return "allowed";
    if (Number(values[0]) === 0 && [1, 2, 3].includes(Number(values[1]))) return "limited";
    return "unavailable";
  } catch {
    // Redis downtime, expired credentials, and errors must never trigger Azure.
    return "unavailable";
  }
}
function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: {
    "Cache-Control": "no-store, private",
    "X-Content-Type-Options": "nosniff",
  } });
}
function wavDurationValid(bytes: Uint8Array): boolean {
  if (bytes.byteLength < 45 || bytes.byteLength > MAX_WAV_BYTES) return false;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tag = (start: number, word: string): boolean =>
    [...word].every((letter, i) => bytes[start + i] === letter.charCodeAt(0));
  if (!tag(0, "RIFF") || !tag(8, "WAVE") || !tag(12, "fmt ") || !tag(36, "data")) return false;
  if (view.getUint32(4, true) + 8 !== bytes.byteLength) return false;
  if (view.getUint32(16, true) !== 16 || view.getUint16(20, true) !== 1) return false;
  if (view.getUint16(22, true) !== 1 || view.getUint32(24, true) !== 16000) return false;
  if (view.getUint16(34, true) !== 16 || view.getUint16(32, true) !== 2) return false;
  const dataLength = view.getUint32(40, true);
  return dataLength === bytes.byteLength - 44 && dataLength >= 16000 * 2 / 10
    && dataLength <= 16000 * 2 * 21;
}

export function GET(): Response {
  return json({ enabled: enabled(), provider: "azure-pronunciation-assessment", maxSeconds: 20 });
}

export async function POST(request: Request): Promise<Response> {
  if (!enabled()) return json({ error: "ASSESSMENT_UNAVAILABLE" }, 503);
  const url = new URL(request.url);
  const origin = request.headers.get("origin");
  if (!origin || origin !== url.origin || request.headers.get("sec-fetch-site") === "cross-site") {
    return json({ error: "ORIGIN_NOT_ALLOWED" }, 403);
  }
  const rawReference = request.headers.get("x-reference-text")?.trim() ?? "";
  if (rawReference.length < 1 || rawReference.length > 160) return json({ error: "INVALID_REFERENCE" }, 400);
  const reference = allowedPhrases.get(rawReference.toLowerCase());
  if (!reference) return json({ error: "REFERENCE_NOT_SUPPORTED" }, 400);
  if (request.headers.get("content-type") !== "audio/wav") return json({ error: "UNSUPPORTED_AUDIO" }, 415);
  const size = Number(request.headers.get("content-length") ?? 0);
  if (size > MAX_WAV_BYTES) return json({ error: "AUDIO_TOO_LARGE" }, 413);
  let wav: Uint8Array;
  try { wav = new Uint8Array(await request.arrayBuffer()); }
  catch { return json({ error: "AUDIO_READ_FAILED" }, 400); }
  if (!wavDurationValid(wav)) return json({ error: "INVALID_WAV_16K_MONO" }, 400);
  const quota = await reserveQuota(request);
  if (quota === "limited") return json({ error: "RATE_LIMITED" }, 429);
  if (quota !== "allowed") return json({ error: "QUOTA_UNAVAILABLE" }, 503);
  const settings = Buffer.from(JSON.stringify({
    ReferenceText: reference,
    GradingSystem: "HundredMark",
    Granularity: "Phoneme",
    Dimension: "Comprehensive",
    EnableMiscue: "True",
    EnableProsodyAssessment: "True",
  }), "utf8").toString("base64");
  const region = process.env.AZURE_SPEECH_REGION!;
  const endpoint = `https://${region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US&format=detailed`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": process.env.AZURE_SPEECH_KEY!,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
        "Pronunciation-Assessment": settings,
      },
      body: wav.buffer.slice(wav.byteOffset, wav.byteOffset + wav.byteLength) as ArrayBuffer,
      signal: AbortSignal.timeout(12_000),
      cache: "no-store",
    });
    if (!response.ok) return json({ error: "PROVIDER_UNAVAILABLE" }, 502);
    const result = normalizeAzureAssessment(await response.json(), reference);
    return json(result);
  } catch (error) {
    if (error instanceof Error && error.message === "SPEECH_NOT_RECOGNIZED") {
      return json({ error: "SPEECH_NOT_RECOGNIZED" }, 422);
    }
    // No logging of raw audio, recognized content, or subscription credentials.
    return json({ error: "ASSESSMENT_FAILED" }, 502);
  }
}
