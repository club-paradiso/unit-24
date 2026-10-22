import { useState } from "react";
import { Link, useParams } from "react-router";
import { encounterCatalog } from "../encounters/catalog";
import { ListenButton } from "../components/ListenButton";
import { SpeechCoach } from "../components/SpeechCoach";
import { useI18n } from "../i18n";
import { useTitle } from "../state";

const COPY = {
  ko: {
    title: "교통 단속 영어 대화", label: "ENCOUNTER · 언어 연습 베타",
    warningTitle: "실제 경찰 대응 지침이 아닙니다",
    warning: "가상의 영어 대화를 연습하는 베타 기능입니다. 미국 내 실제 법률·권리·의무는 지역과 상황에 따라 다르며, 이 대화는 법률 검증을 마치지 않았습니다. 정답 판정은 법적 적절성이 아닌 영어 표현의 명확성과 자연스러움만 평가합니다.",
    sourceIntro: "상황 구성 참고 자료", sourceNote: "대화문은 학습용으로 별도 작성했으며 위 기관의 공식 스크립트가 아닙니다.",
    prompt: "경찰의 말을 읽고 응답을 선택하세요",
    tip: "실제 상황을 가정하지 않고, 영어 표현만 연습합니다.",
    translation: "상황 해설", choose: "어떻게 대답할까요?", feedbackTitle: "영어 표현 피드백",
    next: "다음 대화", finish: "연습 마치기", replay: "다시 연습하기",
    doneTitle: "대화 연습 완료", done: "영어 표현을 이해하고 정중하게 설명을 요청하는 방법을 연습했어요. 이 연습은 법적 행동의 옳고 그름을 평가하지 않습니다.",
    back: "시나리오 목록", unavailable: "준비 중인 시나리오", unavailableText: "이 시나리오는 아직 대화형 연습이 제공되지 않습니다.",
    natural: "자연스러운 표현", acceptable: "사용할 수 있는 표현", needs_clarification: "다른 표현도 연습해 보세요",
  },
  en: {
    title: "Traffic Stop · English dialogue", label: "ENCOUNTER · Language beta",
    warningTitle: "Not real-world police guidance",
    warning: "This is a fictional English-language practice exercise, not legal advice or a response guide. Actual legal rights and obligations vary by location and circumstances, and this script has not received legal review. Feedback evaluates clarity and conversational naturalness only.",
    sourceIntro: "Context references", sourceNote: "Dialogue was independently authored for learning and is not an official transcript or script from either organization.",
    prompt: "Read the officer's words and choose a response",
    tip: "Practice language only, not decisions about what you must do in real life.",
    translation: "Situation explanation", choose: "How would you reply?", feedbackTitle: "Language feedback",
    next: "Continue conversation", finish: "Finish practice", replay: "Practice again",
    doneTitle: "Dialogue complete", done: "You practiced understanding an explanation and asking for clarification in English. This exercise does not assess whether any response is legally appropriate.",
    back: "All scenarios", unavailable: "Scenario not ready", unavailableText: "Interactive dialogue is not available for this scenario yet.",
    natural: "Natural expression", acceptable: "Acceptable expression", needs_clarification: "Try another way to phrase this",
  },
} as const;

export function EncounterPlayer() {
  const { scenarioId } = useParams();
  const { lang } = useI18n();
  const copy = COPY[lang];
  const scenario = encounterCatalog.find((item) => item.id === scenarioId);
  const [turnId, setTurnId] = useState("opening");
  const [chosenResponse, setChosenResponse] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  useTitle(scenario ? scenario.title[lang] : "ENCOUNTER");

  if (!scenario || (scenario.stage !== "pilot" && scenario.stage !== "playable")) {
    return (
      <section className="card stack encounter-player">
        <h1>{copy.unavailable}</h1>
        <p>{copy.unavailableText}</p>
        <Link to="/encounters" className="btn btn-primary">{copy.back}</Link>
      </section>
    );
  }

  const turn = scenario.turns.find((item) => item.id === turnId);
  const selected = turn?.responses.find((option) => option.id === chosenResponse);
  const advance = () => {
    if (!selected) return;
    if (selected.nextTurnId === null) {
      setCompleted(true);
    } else {
      setTurnId(selected.nextTurnId);
      setChosenResponse(null);
    }
  };
  const reset = () => {
    setTurnId(scenario.turns[0]!.id);
    setChosenResponse(null);
    setCompleted(false);
  };

  return (
    <div className="stack-lg encounter-player">
      <header className="stack">
        <p className="eyebrow">{copy.label}</p>
        <h1>{copy.title}</h1>
        <p className="muted">{copy.tip}</p>
      </header>
      <aside className="card pilot-warning stack-sm" aria-label={copy.warningTitle}>
        <strong>{copy.warningTitle}</strong>
        <p className="small">{copy.warning}</p>
        <details>
          <summary>{copy.sourceIntro}</summary>
          <div className="stack-sm">
            <div className="pilot-source-links">
              {scenario.sources.map((source) => (
                <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                </a>
              ))}
            </div>
            <p className="small muted">{copy.sourceNote}</p>
          </div>
        </details>
      </aside>

      {completed ? (
        <section className="card stack" aria-labelledby="encounter-complete">
          <h2 id="encounter-complete">{copy.doneTitle}</h2>
          <p>{copy.done}</p>
          <div className="player-actions">
            <button type="button" className="btn" onClick={reset}>{copy.replay}</button>
            <Link to="/encounters" className="btn btn-primary">{copy.back}</Link>
          </div>
        </section>
      ) : turn ? (
        <>
          <section className="card stack" aria-labelledby="encounter-officer">
            <p className="eyebrow">{copy.prompt}</p>
            <h2 id="encounter-officer" className="utterance" lang="en">{turn.utterance}</h2>
            <p className="small muted">{copy.translation}: {turn.translation[lang]}</p>
            <ListenButton text={turn.utterance} />
          </section>
          <section className="stack" aria-labelledby="encounter-responses">
            <h2 id="encounter-responses">{copy.choose}</h2>
            <div className="options">
              {turn.responses.map((option) => (
                <button
                  key={option.id} type="button"
                  className="response-choice"
                  aria-pressed={chosenResponse === option.id}
                  disabled={chosenResponse !== null}
                  onClick={() => setChosenResponse(option.id)}
                >
                  <span lang="en">{option.utterance}</span>
                </button>
              ))}
            </div>
          </section>
          {selected && (
            <section className="card response-feedback stack" aria-live="polite">
              <h2>{copy.feedbackTitle}</h2>
              <strong>{copy[selected.languageRating]}</strong>
              <p>{selected.feedback[lang]}</p>
              <SpeechCoach key={selected.id} phrase={selected.utterance} compact />
              <button type="button" className="btn btn-primary btn-block" onClick={advance}>
                {selected.nextTurnId === null ? copy.finish : copy.next}
              </button>
            </section>
          )}
        </>
      ) : (
        <section className="card stack" role="alert">
          <p>{copy.unavailableText}</p>
          <button type="button" className="btn btn-primary" onClick={reset}>{copy.replay}</button>
        </section>
      )}
    </div>
  );
}
