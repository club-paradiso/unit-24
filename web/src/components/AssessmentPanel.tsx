import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import type { AssessmentResult } from "../lib/assessment";
import { isAssessmentResult } from "../lib/assessment";
import { audioToWav16k } from "../lib/audioWav";

const COPY = {
  ko: {
    label: "AI 발음 분석 · 베타", summary: "실제 녹음으로 단어·음소별 발음과 유창성, 운율을 확인합니다.",
    unavailable: "AI 정밀 발음 평가는 아직 설정되지 않았어요. 녹음해서 내 목소리를 듣는 기능은 계속 이용할 수 있어요.",
    ready: "녹음이 준비됐어요. 분석을 요청하면 음성 데이터가 UNIT-24 서버를 거쳐 Microsoft Azure Speech로 전송돼요.",
    consent: "음성을 Microsoft Azure Speech로 전송해 평가하는 데 동의합니다. 평가 결과는 이 화면에서만 표시되며 UNIT-24는 음성 파일을 저장하지 않습니다.",
    analyze: "AI 발음 평가하기", analyzing: "발음 분석 중…",
    error: "발음 평가를 완료하지 못했어요. 녹음 형식·네트워크 상태를 확인하거나 다시 녹음해 보세요.",
    noSpeech: "음성을 인식하지 못했어요. 더 명확하게 말한 뒤 다시 녹음해 보세요.",
    unavailableServer: "AI 평가 서버가 준비되지 않았어요. 기존 녹음 재생은 그대로 이용할 수 있습니다.",
    rateLimited: "요청 횟수가 많아요. 잠시 후 다시 시도해 주세요.",
    overall: "종합 점수", accuracy: "정확도", fluency: "유창성", completeness: "완성도", prosody: "강세·억양·리듬",
    recognized: "인식한 문장", words: "단어별 발음", phonemes: "음소",
    absent: "평가 결과 없음", guidance: "AI 점수는 참고 지표이며 원어민 억양 일치 여부나 실제 무전 수행 능력·안전성에 대한 판정이 아닙니다.",
    low: "다시 연습해 볼 단어", redo: "다시 평가하기", failedFormat: "녹음을 16kHz WAV로 변환하지 못했어요. Safari/브라우저를 업데이트하거나 다른 녹음 형식을 시도하세요.",
  },
  en: {
    label: "AI Pronunciation Assessment · Beta", summary: "See AI-estimated speech accuracy, fluency, prosody and word/phoneme feedback.",
    unavailable: "AI assessment isn't configured yet. Listening and local recording still work.",
    ready: "When you request an assessment, this recording will be sent through UNIT-24 to Microsoft Azure Speech.",
    consent: "I agree to send my recording to Microsoft Azure Speech for evaluation. UNIT-24 does not save the recording or assessment result.",
    analyze: "Assess pronunciation", analyzing: "Analyzing speech…",
    error: "Assessment couldn't finish. Check audio format and your connection, or record again.",
    noSpeech: "Speech wasn't recognized. Speak more clearly and record again.",
    unavailableServer: "AI assessment is unavailable. Local playback still works.",
    rateLimited: "Too many requests. Please retry later.",
    overall: "Overall", accuracy: "Accuracy", fluency: "Fluency", completeness: "Completeness", prosody: "Stress, intonation and rhythm",
    recognized: "Recognized speech", words: "Word breakdown", phonemes: "Phonemes",
    absent: "Not available", guidance: "AI estimates are not proof of native accent, radio competency, legality or safety.",
    low: "Words to revisit", redo: "Assess again", failedFormat: "Couldn't convert this recording to 16 kHz WAV. Try an updated browser or another recording.",
  },
} as const;

let cachedAvailability: Promise<boolean> | null = null;
function isConfigured(): Promise<boolean> {
  if (!cachedAvailability) cachedAvailability = fetch("/api/speech-assess", { cache: "no-store" })
    .then(async r => {
      if (!r.ok || !(r.headers.get("content-type") ?? "").includes("application/json")) return false;
      const data: unknown = await r.json();
      return typeof data === "object" && data !== null && (data as { enabled?: unknown }).enabled === true;
    })
    .catch(() => false);
  return cachedAvailability;
}

const showScore = (value: number | null, missing: string) => value === null ? missing : `${Math.round(value)} / 100`;

export function AssessmentPanel({ audio, phrase }: { audio: Blob; phrase: string }) {
  const { lang } = useI18n();
  const copy = COPY[lang];
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [consent, setConsent] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AssessmentResult | null>(null);

  useEffect(() => {
    let active = true;
    void isConfigured().then(available => { if (active) setConfigured(available); });
    return () => { active = false; };
  }, []);
  useEffect(() => { setResult(null); setError(""); setConsent(false); }, [audio, phrase]);

  const analyze = async () => {
    if (!consent || !configured || working) return;
    setWorking(true); setError(""); setResult(null);
    try {
      let wav: Blob;
      try { wav = await audioToWav16k(audio); }
      catch { throw new Error("AUDIO_FORMAT"); }
      const response = await fetch("/api/speech-assess", {
        method: "POST", cache: "no-store",
        headers: { "Content-Type": "audio/wav", "X-Reference-Text": phrase },
        body: wav,
        signal: AbortSignal.timeout(18_000),
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        const reason = typeof payload === "object" && payload !== null
          ? (payload as { error?: string }).error : "";
        throw new Error(reason || "ASSESSMENT_FAILED");
      }
      if (!isAssessmentResult(payload)) throw new Error("INVALID_ASSESSMENT");
      setResult(payload);
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      setError(message === "SPEECH_NOT_RECOGNIZED" ? copy.noSpeech
        : message === "RATE_LIMITED" ? copy.rateLimited
        : message === "ASSESSMENT_UNAVAILABLE" ? copy.unavailableServer
        : message === "AUDIO_FORMAT" ? copy.failedFormat : copy.error);
    } finally { setWorking(false); }
  };

  const metric = (label: string, value: number | null) => (
    <div className="ai-score" key={label}>
      <span>{label}</span><strong>{showScore(value, copy.absent)}</strong>
      {value !== null && <progress aria-label={label} max={100} value={value} />}
    </div>
  );
  return (
    <section className="assessment-panel" aria-label={copy.label}>
      <h3>{copy.label}</h3>
      <p className="small muted">{copy.summary}</p>
      {configured === false ? <p className="assessment-unavailable small">{copy.unavailable}</p>
        : configured === null ? <p className="muted small" role="status">…</p>
        : <>
          <p className="small">{copy.ready}</p>
          <label className="assessment-consent">
            <input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} disabled={working} />
            <span>{copy.consent}</span>
          </label>
          <button type="button" className="btn btn-primary" disabled={!consent || working} onClick={() => void analyze()}>
            {working ? copy.analyzing : result ? copy.redo : copy.analyze}
          </button>
        </>
      }
      {error && <p role="alert" className="small">{error}</p>}
      {result && <div className="assessment-result" aria-live="polite">
        <div className="assessment-metrics">
          {metric(copy.overall, result.scores.overall)}
          {metric(copy.accuracy, result.scores.accuracy)}
          {metric(copy.fluency, result.scores.fluency)}
          {metric(copy.completeness, result.scores.completeness)}
          {metric(copy.prosody, result.scores.prosody)}
        </div>
        <p><strong>{copy.recognized}: </strong><span lang="en">{result.recognizedText || copy.absent}</span></p>
        {!!result.words.length && <div className="assessment-words">
          <h4>{copy.words}</h4>
          {result.words.map((word, i) => <details key={i} className="assessment-word">
            <summary lang="en"><span>{word.text}</span><strong>{showScore(word.accuracy, copy.absent)}</strong></summary>
            <div className="small">
              {word.errorType && word.errorType !== "None" && <p>{word.errorType}</p>}
              {!!word.phonemes.length && <p>{copy.phonemes}: {word.phonemes.map(x => `${x.sound} (${showScore(x.accuracy, copy.absent)})`).join(" · ")}</p>}
            </div>
          </details>)}
        </div>}
        <p className="small muted">{copy.guidance}</p>
      </div>}
    </section>
  );
}
