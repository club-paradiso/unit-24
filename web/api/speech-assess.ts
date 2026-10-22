/**
 * UNIT-24 scripted, opt-in speech assessment proxy.
 * No recording or Azure key is persisted. Deliberately OFF unless explicitly enabled.
 *
 * IMPORTANT: Public paid traffic also needs durable external quota enforcement/WAF.
 * This in-memory limiter is merely an additional per-instance safeguard.
 */
import { content } from "../src/content";
import { encounterCatalog } from "../src/encounters/catalog";
import { radioReading } from "../src/lib/radioSpeech";
import { normalizeAzureAssessment } from "../src/lib/assessment";

export const maxDuration = 20;
const MAX_WAV_BYTES = 44 + 16000 * 2 * 21;
const LIMIT_PER_IP = 3;
const LIMIT_GLOBAL = 30;
const windowMs = 60_000;
const recentByIp = new Map<string, number[]>();
let recentGlobal: number[] = [];

const allowedPhrases = new Map<string, string>();
for (const item of content.items) {
  const phrase = radioReading(item);
  allowedPhrases.set(phrase.toLowerCase(), phrase);
}
for (const s of encounterCatalog) for (const turn of s.turns) {
  allowedPhrases.set(turn.utterance.toLowerCase(), turn.utterance);
  for (const response of turn.responses) allowedPhrases.set(response.utterance.toLowerCase(), response.utterance);
}

function enabled(): boolean {
  return process.env.UNIT24_SPEECH_ASSESSMENT_ENABLED === "true"
    && Boolean(process.env.AZURE_SPEECH_KEY)
    && /^[a-z0-9-]{3,40}$/.test(process.env.AZURE_SPEECH_REGION ?? "");
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

function throttle(ip: string): boolean {
  const now = Date.now();
  const local = (recentByIp.get(ip) ?? []).filter(t => now - t < windowMs);
  recentGlobal = recentGlobal.filter(t => now - t < windowMs);
  if (local.length >= LIMIT_PER_IP || recentGlobal.length >= LIMIT_GLOBAL) return false;
  local.push(now);
  recentGlobal.push(now);
  recentByIp.set(ip, local);
  if (recentByIp.size > 500) recentByIp.clear();
  return true;
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
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  if (!throttle(ip)) return json({ error: "RATE_LIMITED" }, 429);

  let wav: Uint8Array;
  try { wav = new Uint8Array(await request.arrayBuffer()); }
  catch { return json({ error: "AUDIO_READ_FAILED" }, 400); }
  if (!wavDurationValid(wav)) return json({ error: "INVALID_WAV_16K_MONO" }, 400);
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
      body: wav,
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
