import { useMemo, useState } from "react";
import { Link } from "react-router";
import { content } from "../content";
import { SpeechCoach } from "../components/SpeechCoach";
import { ListenButton } from "../components/ListenButton";
import { TrustBadges } from "../components/Status";
import { useI18n } from "../i18n";
import { radioDisplayReading, radioReading } from "../lib/radioSpeech";
import { useProgress, useTitle } from "../state";
import { useStartSession } from "./Practice";

type Topic = "codes" | "alphabet";
const koGloss: Record<string, string> = {
  "10-1": "수신 상태 불량", "10-2": "수신 상태 양호", "10-5": "메시지 중계",
  "10-7": "근무/운용 중지", "10-9": "다시 송신해 주세요",
  "10-13": "도로 또는 기상 상태 안내", "10-14": "호송 지원",
  "10-15": "피구금자 관리 중", "10-17": "문서·물품 중계",
  "10-20": "위치 확인 요청", "10-21": "전화 연락",
  "10-22": "지시·메시지 취소", "10-23": "대기",
  "10-28": "차량 등록 조회 요청", "10-4": "수신 확인",
  "10-30": "부적절한 무전 통신", "10-31": "자살 위험이 있는 대상자",
  "10-35": "용의자가 현장에 있음, 지원 필요", "10-36": "기밀 정보",
  "11-27": "운전면허 조회", "11-41": "구급차",
  "11-82": "인명 피해 없는 교통사고", "11-83": "부상 여부 미확인 교통사고",
  "11-86": "폭탄 위협", "11-98": "만남·집결",
};
const UI = {
  ko: {
    eyebrow: "UNIT-24 / RADIO LAB", title: "코드를 읽기만 하지 말고, 직접 말해 보세요.",
    subtitle: "발음을 듣고, 천천히 따라 하고, 내 목소리를 확인하는 순서로 연습합니다.",
    step1: "01 · 읽는 법 이해", step2: "02 · 발음 듣기", step3: "03 · 직접 말하기",
    code: "무전 코드", alphabet: "철자 통신용 단어", meaning: "영어 뜻", korean: "한국어 뜻",
    source: "원문·검증 기록 보기", next: "다음 표현", prev: "이전 표현",
    audioControls: "발음과 뜻 각각 듣기", codeSound: "코드 읽는 법 듣기", letterSound: "철자 단어 듣기", meaningSound: "영어 뜻 듣기",
    practiceTitle: "04 · 이해 확인", practiceIntro: "방금 듣고 말한 표현을 문제로 확인해 보세요.",
    checkItem: "이 표현 1문제 풀기", resume: "풀던 문제 이어서 하기", allPractice: "전체 연습 보기",
    practiceNote: "듣기·녹음만으로는 진도가 올라가지 않아요. 문제에 답하면 복습 기록에 반영됩니다.",
    convention: "발음 표기는 일반적인 학습용 숫자 읽기입니다. 실제 관할·기관별 무전 발성 관행과 다를 수 있으며, 재생 음성은 기기에서 합성합니다.",
    choose: "다른 코드 선택", review: "기존 무전 학습 돌아가기",
  },
  en: {
    eyebrow: "UNIT-24 / RADIO LAB", title: "Don't just read radio codes. Say them.",
    subtitle: "Listen to an example, repeat it slowly and review your own voice.",
    step1: "01 · Decode", step2: "02 · Listen", step3: "03 · Say it",
    code: "Radio codes", alphabet: "Spelling alphabet", meaning: "English meaning", korean: "Korean gloss",
    source: "Source & verification record", next: "Next phrase", prev: "Previous phrase",
    audioControls: "Listen to the spoken term and its meaning", codeSound: "Hear the code", letterSound: "Hear the spelling word", meaningSound: "Hear the English meaning",
    practiceTitle: "04 · Check understanding", practiceIntro: "Check what you just heard and said with one source-backed question.",
    checkItem: "Check this item · 1 question", resume: "Resume unfinished practice", allPractice: "See all practice",
    practiceNote: "Listening and recording do not change progress. Answering a question does.",
    convention: "These are learner-friendly number readings, not certified agency radio recordings. Real phrasing varies by agency and context; audio is device-generated.",
    choose: "Choose another code", review: "Return to radio course",
  },
} as const;

export function RadioLab() {
  const { lang } = useI18n();
  const ui = UI[lang];
  const [topic, setTopic] = useState<Topic>("codes");
  const [index, setIndex] = useState(0);
  const progress = useProgress();
  const startSession = useStartSession();
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
        <div className="radio-audio-actions" role="group" aria-label={ui.audioControls}>
          <ListenButton text={spoken} label={item.kind === "letter" ? ui.letterSound : ui.codeSound} />
          {item.kind === "code" && <ListenButton text={item.answer} label={ui.meaningSound} />}
        </div>
        <div className="radio-source-summary">
          <TrustBadges item={item} compact />
          <Link to={`/chp/items/${item.id}`} className="btn btn-quiet">{ui.source} ↗</Link>
        </div>
      </section>
      <div className="radio-voice-section">
        <p className="eyebrow">{ui.step2} / {ui.step3}</p>
        <SpeechCoach key={item.id} phrase={spoken} />
        <p className="muted small">{ui.convention}</p>
      </div>
      <section className="card radio-practice-path" aria-label={ui.practiceTitle}>
        <div>
          <h2>{ui.practiceTitle}</h2>
          <p className="muted">{ui.practiceIntro}</p>
        </div>
        <div className="radio-practice-actions">
          {progress.activeSession ? (
            <Link to="/chp/practice/session" className="btn btn-primary">{ui.resume}</Link>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => startSession("mixed", [item.id])}>
              {ui.checkItem}
            </button>
          )}
          <Link to="/chp/practice" className="btn">{ui.allPractice}</Link>
        </div>
        <p className="muted small">{ui.practiceNote}</p>
      </section>
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
