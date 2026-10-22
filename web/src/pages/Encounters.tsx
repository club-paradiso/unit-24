import { Link } from "react-router";
import { encounterCatalog } from "../encounters/catalog";
import { useI18n } from "../i18n";
import { useTitle } from "../state";

const COPY = {
  ko: {
    title: "경찰과 마주하는 순간의 영어",
    intro: "교통 단속부터 사건 신고까지, 상황을 이해하고 자연스럽고 정확한 영어 표현을 익히는 학습 공간입니다.",
    sectionTitle: "학습 시나리오",
    overview: "상황 카드를 펼치면 학습 목표를 확인할 수 있어요.",
    preview: "준비 중",
    goals: "이 상황에서 배울 내용",
    notice: "현재는 시나리오 목록을 미리 보는 단계입니다. 대화형 연습·음성 평가 기능은 아직 제공되지 않습니다.",
    legal: "미국의 경찰 관련 절차와 권리는 주·장소·상황에 따라 달라질 수 있습니다. 이 목록은 영어 학습용이며 법률 조언이나 실제 대응 지침이 아닙니다.",
    back: "무전 영어 학습으로 돌아가기",
    levels: "영어 난이도",
    categories: {
      traffic: "교통", street: "거리", identification: "신분 확인",
      witness: "목격자", reporting: "신고", detention: "지시 이해",
    },
  },
  en: {
    title: "English for police encounters",
    intro: "Build the language to understand questions, clarify instructions and describe incidents in everyday public-safety situations.",
    sectionTitle: "Learning scenarios",
    overview: "Expand any card to preview its learning goals.",
    preview: "Coming soon",
    goals: "Learning goals",
    notice: "These are scenario previews, not playable lessons. Interactive dialogue and speech feedback are not available yet.",
    legal: "Police procedures and rights vary by state, location and circumstances. This is language education, not legal advice or real-world response instructions.",
    back: "Return to radio English",
    levels: "English level",
    categories: {
      traffic: "Traffic", street: "Public contact", identification: "Identification",
      witness: "Witness", reporting: "Reporting", detention: "Clarification",
    },
  },
} as const;

export function Encounters() {
  const { lang } = useI18n();
  const copy = COPY[lang];
  useTitle("ENCOUNTER");

  return (
    <div className="stack-lg encounter-page">
      <section className="card encounter-hero" aria-labelledby="encounter-title">
        <p className="eyebrow">UNIT-24 / ENCOUNTER</p>
        <h1 id="encounter-title">{copy.title}</h1>
        <p className="lead">{copy.intro}</p>
        <Link to="/chp" className="encounter-back">{copy.back} <span aria-hidden="true">→</span></Link>
      </section>

      <section className="stack" aria-labelledby="encounter-list-title">
        <div className="encounter-section-heading">
          <div>
            <h2 id="encounter-list-title">{copy.sectionTitle}</h2>
            <p className="muted small">{copy.overview}</p>
          </div>
          <span className="encounter-count">{encounterCatalog.length}</span>
        </div>
        <ul className="encounter-grid">
          {encounterCatalog.map((scenario, index) => (
            <li key={scenario.id}>
              <details className="card encounter-card" data-scenario={scenario.id}>
                <summary className="encounter-card-summary">
                  <span className="encounter-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                  <span className="encounter-card-content">
                    <span className="eyebrow">{copy.categories[scenario.category]} · {scenario.level}</span>
                    <strong className="encounter-card-title">{scenario.title.en}</strong>
                    <span className="muted small">{scenario.summary[lang]}</span>
                    <span className="encounter-stage">{copy.preview}</span>
                  </span>
                  <span className="encounter-expand" aria-hidden="true">⌄</span>
                </summary>
                <div className="encounter-card-details">
                  <h3>{copy.goals}</h3>
                  <ul>
                    {scenario.learningGoals.map((goal, i) => <li key={i}>{goal[lang]}</li>)}
                  </ul>
                  <p className="muted small">{copy.notice}</p>
                </div>
              </details>
            </li>
          ))}
        </ul>
      </section>
      <aside className="card encounter-disclaimer" aria-label={lang === "ko" ? "학습 내용 안내" : "Learning disclaimer"}>
        <p>{copy.legal}</p>
      </aside>
    </div>
  );
}
