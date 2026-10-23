import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { GET, POST } from "../../api/speech-assess";

function wav(): Uint8Array {
  const out = new Uint8Array(44 + 16000 * 2); // 1 second of silence; transport only
  const view = new DataView(out.buffer);
  const mark = (offset: number, word: string) => [...word].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  mark(0, "RIFF"); view.setUint32(4, out.byteLength - 8, true);
  mark(8, "WAVE"); mark(12, "fmt "); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  mark(36, "data"); view.setUint32(40, out.byteLength - 44, true);
  return out;
}
function request(reference = "ten one", origin = "https://unit24.example"): Request {
  return new Request("https://unit24.example/api/speech-assess", {
    method: "POST",
    headers: {
      origin,
      "x-vercel-forwarded-for": "203.0.113.3",
      "content-type": "audio/wav",
      "x-reference-text": reference,
    },
    body: wav().buffer as ArrayBuffer,
  });
}
function enable(configuredLimiter = true): void {
  vi.stubEnv("UNIT24_SPEECH_ASSESSMENT_ENABLED", "true");
  vi.stubEnv("AZURE_SPEECH_KEY", "test-key-not-a-real-key");
  vi.stubEnv("AZURE_SPEECH_REGION", "eastus");
  if (configuredLimiter) {
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "https://safe-example.upstash.io/");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-rest-token-12345");
    vi.stubEnv("UNIT24_SPEECH_IP_HASH_SECRET", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
  }
}

describe("AI assessment paid-call safety gate", () => {
  beforeEach(() => {
    vi.stubEnv("UNIT24_SPEECH_ASSESSMENT_ENABLED", "false");
    vi.stubEnv("AZURE_SPEECH_KEY", "");
    vi.stubEnv("AZURE_SPEECH_REGION", "");
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "");
    vi.stubEnv("UNIT24_SPEECH_IP_HASH_SECRET", "");
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

  it("stays disabled without credentials and returns 503 without any upstream request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect((await GET().json()).enabled).toBe(false);
    const response = await POST(request());
    expect(response.status).toBe(503);
    expect((await response.json()).error).toBe("ASSESSMENT_UNAVAILABLE");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("cannot be enabled by Azure key + flag without durable quotas", async () => {
    enable(false);
    expect((await GET().json()).enabled).toBe(false);
    expect((await POST(request())).status).toBe(503);
  });

  it("refuses cross-origin and unknown lesson phrases before touching quota storage", async () => {
    enable();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request("ten one", "https://other.example"))).status).toBe(403);
    expect((await POST(request("some arbitrary Azure command"))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("atomically reserves quota before Azure and returns sanitized scores", async () => {
    enable();
    const mock = vi.fn(async (url: string, init: RequestInit) => {
      if (url.includes("upstash.io")) {
        const cmd = JSON.parse(String(init.body)) as unknown[];
        expect(cmd[0]).toBe("EVAL");
        expect(cmd[2]).toBe(3);
        expect(String(cmd[3])).not.toContain("203.0.113.3"); // hashed identifier
        return Response.json({ result: [1, 0] });
      }
      expect(url).toContain("eastus.stt.speech.microsoft.com");
      return Response.json({
        RecognitionStatus: "Success", DisplayText: "Ten one.",
        NBest: [{ PronScore: 81, AccuracyScore: 85, FluencyScore: 79,
          CompletenessScore: 100, Words: [{ Word: "ten", AccuracyScore: 90, Phonemes: [{ Phoneme: "t", AccuracyScore: 92 }] }] }],
      });
    });
    vi.stubGlobal("fetch", mock);
    expect((await GET().json()).enabled).toBe(true);
    const response = await POST(request());
    expect(response.status).toBe(200);
    expect((await response.json()).scores.prosody).toBeNull();
    expect(mock).toHaveBeenCalledTimes(2);
  });

  it("returns 429 when distributed budget denies and never invokes Azure", async () => {
    enable();
    const mock = vi.fn(async () => Response.json({ result: [0, 3] }));
    vi.stubGlobal("fetch", mock);
    const response = await POST(request());
    expect(response.status).toBe(429);
    expect((await response.json()).error).toBe("RATE_LIMITED");
    expect(mock).toHaveBeenCalledTimes(1);
  });

  it("fails closed if Redis is unreachable, returns malformed results, or has errors", async () => {
    enable();
    const mock = vi.fn(async () => { throw new Error("redis down"); });
    vi.stubGlobal("fetch", mock);
    let res = await POST(request());
    expect(res.status).toBe(503);
    expect((await res.json()).error).toBe("QUOTA_UNAVAILABLE");
    expect(mock).toHaveBeenCalledTimes(1);

    const bad = vi.fn(async () => Response.json({ error: "ERR script unavailable" }));
    vi.stubGlobal("fetch", bad);
    res = await POST(request());
    expect(res.status).toBe(503);
    expect(bad).toHaveBeenCalledTimes(1);
  });
});
