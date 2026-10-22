import { useEffect, useState } from "react";
import { useI18n } from "../i18n";

/** Device TTS, never described as an official CHP recording. */
export function ListenButton({ text, slow = false }: { text: string; slow?: boolean }) {
  const { lang } = useI18n();
  const [message, setMessage] = useState("");
  useEffect(() => () => window.speechSynthesis?.cancel(), [text]);
  return (
    <span className="listen-control">
      <button type="button" className="btn btn-listen" onClick={() => {
        if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
          setMessage(lang === "ko" ? "이 기기는 음성 재생을 지원하지 않습니다." : "Speech playback is unavailable.");
          return;
        }
        window.speechSynthesis.cancel();
        const say = new SpeechSynthesisUtterance(text);
        say.lang = "en-US";
        say.rate = slow ? 0.65 : 0.85;
        const voices = window.speechSynthesis.getVoices();
        say.voice = voices.find(v => v.lang === "en-US") ?? voices.find(v => v.lang.startsWith("en")) ?? null;
        say.onerror = () => setMessage(lang === "ko" ? "재생할 수 없어요. 음량과 음성 설정을 확인하세요." : "Playback failed. Check audio settings.");
        window.speechSynthesis.speak(say);
        setMessage("");
      }}>
        ▶ {lang === "ko" ? (slow ? "느리게 듣기" : "발음 듣기") : (slow ? "Hear slowly" : "Listen")}
      </button>
      {message && <span role="status" className="muted small">{message}</span>}
    </span>
  );
}
