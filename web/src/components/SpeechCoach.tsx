import { useEffect, useRef, useState } from "react";
import { heardSimilarity } from "../lib/radioSpeech";
import { useI18n } from "../i18n";

type SpeechResult = { 0?: { transcript: string }; isFinal?: boolean };
type RecognizerEvent = { results: ArrayLike<SpeechResult> };
type BrowserRecognizer = {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  onresult: ((event: RecognizerEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
};
type RecognizerConstructor = new () => BrowserRecognizer;
type SpeechWindow = Window & { SpeechRecognition?: RecognizerConstructor; webkitSpeechRecognition?: RecognizerConstructor };

export function recognitionAvailable(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as SpeechWindow;
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}

const COPY = {
  ko: {
    hear: "발음 듣기", slow: "천천히 듣기", talk: "말하고 인식하기", rec: "녹음 시작",
    stop: "녹음 중지", stopListening: "음성 인식 중지", title: "듣고, 말하고, 확인하기",
    sample: "연습할 표현", micPrivacy: "녹음은 이 기기에서만 재생되며 서버에 저장되지 않습니다. 음성 인식은 브라우저 서비스가 처리할 수 있습니다.",
    recognitionMissing: "이 브라우저의 음성 인식 기능이 없어도 녹음해서 내 목소리를 다시 들을 수 있어요.",
    recordingMissing: "이 브라우저에서는 녹음을 지원하지 않아요. 듣고 직접 따라 말해 보세요.",
    listening: "영어로 말해 보세요. 듣고 있어요…",
    recording: "녹음 중입니다. 20초 이내에 말해 보세요.",
    heard: "브라우저가 이렇게 들었어요", notGraded: "인식된 단어의 유사도입니다. 발음 정확도·억양을 평가한 점수는 아닙니다.",
    similar: "표현이 비슷하게 인식됐어요.", partial: "일부 단어가 인식됐어요. 다시 들어 보세요.",
    different: "다르게 인식됐어요. 예시를 듣고 다시 연습해 보세요.",
    replay: "내 목소리 다시 듣기", noSpeech: "음성을 알아듣지 못했어요. 다시 시도하거나 녹음 기능을 사용하세요.",
    micDenied: "마이크 접근이 차단됐어요. Safari/브라우저 설정에서 이 사이트의 마이크 권한을 확인하세요.",
    error: "음성 기능을 시작하지 못했어요. 기기 권한과 인터넷 연결을 확인하세요.",
    ttsMissing: "이 기기에서 음성 합성을 사용할 수 없어요.",
    stopped: "중지했어요. 준비되면 다시 시도할 수 있어요.",
    privacy: "녹음 저장 없음 · 마이크는 버튼을 눌렀을 때만 작동",
  },
  en: {
    hear: "Hear pronunciation", slow: "Hear slowly", talk: "Speak & transcribe", rec: "Record myself",
    stop: "Stop recording", stopListening: "Stop listening", title: "Listen, say, check",
    sample: "Phrase to practise", micPrivacy: "Recordings remain in this browser session and are not uploaded by the app. Speech recognition may be processed by your browser's speech service.",
    recognitionMissing: "Speech recognition is unavailable here. You can still record and play back your voice.",
    recordingMissing: "Recording isn't supported here. Listen and practise aloud.",
    listening: "Speak in English. Listening…", recording: "Recording. Speak for up to 20 seconds.",
    heard: "Browser transcription", notGraded: "This compares recognized words, not your pronunciation, accent or fluency.",
    similar: "Your words were recognized similarly.", partial: "Some words were recognized. Listen and try again.",
    different: "Different words were recognized. Listen and try again.",
    replay: "Replay my voice", noSpeech: "No speech was recognized. Try again or record your voice.",
    micDenied: "Microphone access is blocked. Allow microphone permission for this website in your browser settings.",
    error: "Voice capture couldn't start. Check browser permissions and your connection.",
    ttsMissing: "Text-to-speech is not available on this device.",
    stopped: "Stopped. You can try again.",
    privacy: "No recording uploads · microphone starts only when tapped",
  },
} as const;

export function SpeechCoach({ phrase, compact = false }: { phrase: string; compact?: boolean }) {
  const { lang } = useI18n();
  const copy = COPY[lang];
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState<"recognizing" | "recording" | null>(null);
  const [heard, setHeard] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const recognizer = useRef<BrowserRecognizer | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);
  const audioObjectUrl = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);
  const [recognitionSupported, setRecognitionSupported] = useState(false);
  const [recordSupported, setRecordSupported] = useState(false);

  const stopRecorder = () => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    if (recorder.current?.state === "recording") recorder.current.stop();
    mediaStream.current?.getTracks().forEach(track => track.stop());
    mediaStream.current = null;
    if (active.current) setBusy(null);
  };
  const stopRecognition = () => {
    try { recognizer.current?.abort(); } catch { /* already inactive */ }
    recognizer.current = null;
    if (active.current) setBusy(null);
  };
  useEffect(() => {
    active.current = true;
    setRecognitionSupported(recognitionAvailable());
    setRecordSupported(Boolean(typeof navigator.mediaDevices?.getUserMedia === "function" && typeof MediaRecorder !== "undefined"));
    return () => {
      active.current = false;
      if (timer.current) clearTimeout(timer.current);
      try { recognizer.current?.abort(); } catch { /* inactive */ }
      try { if (recorder.current?.state === "recording") recorder.current.stop(); } catch { /* inactive */ }
      mediaStream.current?.getTracks().forEach(track => track.stop());
      window.speechSynthesis?.cancel();
      if (audioObjectUrl.current) URL.revokeObjectURL(audioObjectUrl.current);
    };
  }, [phrase]);

  const speak = (rate: number) => {
    stopRecognition();
    stopRecorder();
    if (!window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
      setStatus(copy.ttsMissing);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(phrase);
    utterance.lang = "en-US";
    utterance.rate = rate;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.lang === "en-US") ?? voices.find(v => v.lang.startsWith("en"));
    if (preferred) utterance.voice = preferred;
    utterance.onerror = () => { if (active.current) setStatus(copy.error); };
    setStatus("");
    window.speechSynthesis.speak(utterance);
  };

  const transcribe = () => {
    stopRecorder();
    window.speechSynthesis?.cancel();
    const speechWindow = window as SpeechWindow;
    const Ctor = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Ctor) { setStatus(copy.recognitionMissing); return; }
    stopRecognition();
    const instance = new Ctor();
    recognizer.current = instance;
    instance.lang = "en-US";
    instance.continuous = false;
    instance.interimResults = false;
    instance.maxAlternatives = 1;
    instance.onresult = (event) => {
      const transcript = Array.from(event.results).map(v => v[0]?.transcript ?? "").join(" ").trim();
      if (active.current) {
        setHeard(transcript || null);
        setStatus(transcript ? "" : copy.noSpeech);
      }
    };
    instance.onerror = (event) => {
      if (!active.current) return;
      setStatus(event.error === "not-allowed" || event.error === "service-not-allowed" ? copy.micDenied : event.error === "no-speech" ? copy.noSpeech : copy.error);
      setBusy(null);
    };
    instance.onend = () => { recognizer.current = null; if (active.current) setBusy(null); };
    setHeard(null);
    setStatus(copy.listening);
    setBusy("recognizing");
    try { instance.start(); } catch { setBusy(null); setStatus(copy.error); }
  };

  const record = async () => {
    stopRecognition();
    window.speechSynthesis?.cancel();
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setStatus(copy.recordingMissing); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!active.current) { stream.getTracks().forEach(t => t.stop()); return; }
      mediaStream.current = stream;
      const chunks: BlobPart[] = [];
      const mr = new MediaRecorder(stream);
      recorder.current = mr;
      mr.ondataavailable = event => { if (event.data.size > 0) chunks.push(event.data); };
      mr.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        if (recorder.current === mr) recorder.current = null;
        if (!active.current) return;
        if (audioObjectUrl.current) URL.revokeObjectURL(audioObjectUrl.current);
        const next = chunks.length ? URL.createObjectURL(new Blob(chunks, { type: mr.mimeType || "audio/webm" })) : null;
        audioObjectUrl.current = next;
        setAudioUrl(next);
        setBusy(null);
        setStatus(next ? "" : copy.error);
      };
      mr.onerror = () => { if (active.current) setStatus(copy.error); stopRecorder(); };
      if (audioObjectUrl.current) { URL.revokeObjectURL(audioObjectUrl.current); audioObjectUrl.current = null; }
      setAudioUrl(null);
      mr.start();
      setBusy("recording");
      setStatus(copy.recording);
      timer.current = setTimeout(stopRecorder, 20000);
    } catch (error) {
      if (active.current) setStatus((error as DOMException)?.name === "NotAllowedError" ? copy.micDenied : copy.error);
      mediaStream.current?.getTracks().forEach(track => track.stop());
      mediaStream.current = null;
      setBusy(null);
    }
  };

  const rating = heard === null ? null : heardSimilarity(heard, phrase);
  return (
    <section className={`speech-coach card ${compact ? "speech-coach-compact" : ""}`} aria-label={copy.title}>
      {!compact && <h2>{copy.title}</h2>}
      <p className="eyebrow">{copy.sample}</p>
      <p className="speech-target" lang="en">{phrase}</p>
      <div className="speech-actions">
        <button type="button" className="btn btn-primary" onClick={() => speak(0.88)} disabled={busy !== null}>▶ {copy.hear}</button>
        <button type="button" className="btn" onClick={() => speak(0.66)} disabled={busy !== null}>{copy.slow}</button>
        {recognitionSupported && (
          <button type="button" className="btn" onClick={busy === "recognizing" ? stopRecognition : transcribe}
            disabled={busy === "recording"}>{busy === "recognizing" ? copy.stopListening : "🎙 " + copy.talk}</button>
        )}
        {recordSupported && (
          <button type="button" className="btn" onClick={busy === "recording" ? stopRecorder : () => void record()}
            disabled={busy === "recognizing"}>{busy === "recording" ? copy.stop : "● " + copy.rec}</button>
        )}
      </div>
      <p role="status" aria-live="polite" className="small muted">
        {status || (!recognitionSupported ? copy.recognitionMissing : !recordSupported ? copy.recordingMissing : copy.privacy)}
      </p>
      {heard !== null && (
        <div className="speech-result" aria-live="polite">
          <strong>{copy.heard}</strong>
          <p lang="en">{heard}</p>
          <p>{copy[rating ?? "different"]}</p>
          <p className="muted small">{copy.notGraded}</p>
        </div>
      )}
      {audioUrl && <div className="speech-result"><strong>{copy.replay}</strong><audio controls src={audioUrl} preload="metadata" aria-label={copy.replay} /></div>}
      {!compact && <p className="small muted">{copy.micPrivacy}</p>}
    </section>
  );
}
