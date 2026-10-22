import { useMemo, useState } from "react";
import { Link } from "react-router";
import { content } from "../content";
import { SpeechCoach } from "../components/SpeechCoach";
import { ListenButton } from "../components/ListenButton";
import { useI18n } from "../i18n";
import { radioDisplayReading, radioReading } from "../lib/radioSpeech";
import { useTitle } from "../state";

type Topic = "codes" | "alphabet";
const koGloss: Record<string, string> = {
  "10-1": "수신 상태 불량", "10-2": "수신 상태 양호", "10-5": "메시지 중계",
  "10-7": "근무/운용 중지", "10-9": "다시 송신해 주세요",
  "10-13": "도로 또는 기상 상태 안내", "10-14": "호송 지원",
  "10-15": "피구금자 관리 중", "10-17": "문서·물품 중계",
  "10-20": "위치 확인 요청", "10-21": "전화 연락",
  "10-22": "지시·메시지 취소", "10-23": "대기",
  "10-28": "차량 등록 조회 요청", "10-4": "수신 확인",
};
const UI = {
  ko: {
    eyebrow: "UNIT-24 / RADIO LAB", title: "코드를 읽기만 하지 말고, 직접 말해 보세요.",
    subtitle: "발음을 듣고, 천천히 따라 하고, 내 목소리를 확인하는 순서로 연습합니다.",
    step1: "01 · 읽는 법 이해", step2: "02 · 발음 듣기", step3: "03 · 직접 말하기",
    code: "무전 코드", alphabet: "철자 통신용 단어", meaning: "영어 뜻", korean: "한국어 뜻",
    source: "해당 코드 근거 확인", next: "다음 표현", prev: "이전 표현",
    convention: "발음 표기는 일반적인 학습용 숫자 읽기입니다. 실제 관할·기관별 무전 발성 관행과 다를 수 있으며, 재생 음성은 기기에서 합성합니다.",
    choose: "다른 코드 선택", review: "기존 무전 학습 돌아가기",
  },
  en: {
    eyebrow: "UNIT-24 / RADIO LAB", title: "Don't just read radio codes. Say them.",
    subtitle: "Listen to an example, repeat it slowly and review your own voice.",
    step1: "01 · Decode", step2: "02 · Listen", step3: "03 · Say it",
    code: "Radio codes", alphabet: "Spelling alphabet", meaning: "English meaning", korean: "Korean gloss",
    source: "Source for this item", next: "Next phrase", prev: "Previous phrase",
    convention: "These are learner-friendly number readings, not certified agency radio recordings. Real phrasing varies by agency and context; audio is device-generated.",
    choose: "Choose another code", review: "Return to radio course",
  },
} as const;

export function RadioLab() {
  const { lang } = useI18n();
  const ui = UI[lang];
  const [topic, setTopic] = useState<Topic>("codes");
  const [index, setIndex] = useState(0);
  useTitle(lang === "ko" ? "무전 말하기 연습" : "Radio Speaking Lab");
  const items = useMemo(() => content.items.filter(i => topic === "alphabet" ? i.kind === "letter" : i.kind === "code"), [topic]);
  const item = items[index] ?? items[0]!;
  const spoken = radioReading(item);
  const switchTopic = (next: Topic) => { setTopic(next); setIndex(0); };
  return (
    <div className="stack-lg radio-lab">
      <header className="radio-lab-hero card">
        <p className="eyebrow">{ui.eyebrow}</p>
        <h1>{ui.title}</h1>
        <p className="lead">{ui.subtitle}</p>
        <div className="radio-lab-steps">
          <span>{ui.step1}</span><span>{ui.step2}</span><span>{ui.step3}</span>
        </div>
      </header>
      <div className="segmented radio-topic-switch" role="group" aria-label={lang === "ko" ? "학습 종류" : "Study topic"}>
        <button type="button" aria-pressed={topic === "codes"} onClick={() => switchTopic("codes")}>{ui.code}</button>
        <button type="button" aria-pressed={topic === "alphabet"} onClick={() => switchTopic("alphabet")}>{ui.alphabet}</button>
      </div>
      <section className="card radio-now" aria-label={ui.step1}>
        <div className="radio-now-heading">
          <p className="eyebrow">{ui.step1}</p>
          <span className="radio-count">{index + 1} / {items.length}</span>
        </div>
        <p className="radio-symbol" lang="en">{item.term}</p>
        <p className="radio-reading" lang="en">{radioDisplayReading(item)}</p>
        <div className="radio-meaning">
          <div><span className="eyebrow">{ui.meaning}</span><p lang="en">{item.answer}</p></div>
          {koGloss[item.term] && <div><span className="eyebrow">{ui.korean}</span><p>{koGloss[item.term]}</p></div>}
        </div>
        <div className="actions">
          <ListenButton text={item.answer} />
          <Link to={`/chp/items/${item.id}`} className="btn btn-quiet">{ui.source} ↗</Link>
        </div>
      </section>
      <div className="radio-voice-section">
        <p className="eyebrow">{ui.step2} / {ui.step3}</p>
        <SpeechCoach key={item.id} phrase={spoken} />
        <p className="muted small">{ui.convention}</p>
      </div>
      <div className="radio-lab-navigation">
        <button type="button" className="btn" disabled={index === 0} onClick={() => setIndex(n => n - 1)}>← {ui.prev}</button>
        <button type="button" className="btn btn-primary" onClick={() => setIndex(n => (n + 1) % items.length)}>{ui.next} →</button>
      </div>
      <details className="card radio-picker">
        <summary>{ui.choose} ({items.length})</summary>
        <div className="radio-picker-grid">
          {items.map((candidate, n) => (
            <button key={candidate.id} type="button" className="radio-picker-item"
              aria-pressed={n === index} onClick={() => setIndex(n)}>
              <strong>{candidate.term}</strong>
              <span>{radioReading(candidate)}</span>
            </button>
          ))}
        </div>
      </details>
      <Link className="btn btn-quiet" to="/chp">← {ui.review}</Link>
    </div>
  );
}
