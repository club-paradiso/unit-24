import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { content, getItem } from "../content";
import { QuestionView } from "../components/QuestionView";
import { useT } from "../i18n";
import { percent } from "../lib/format";
import type { SessionSummary } from "../lib/progress";
import { buildQuestions, itemsForMode, type PracticeMode } from "../lib/quiz";
import { newId } from "../lib/random";
import { useProgress, useStore, useTitle } from "../state";

const MODES: PracticeMode[] = ["mixed", "codes", "alphabet", "due", "mistakes"];

export const SESSION_SIZE = 10;

/** Starts a session and navigates to it. Returns false if the mode has nothing to practise. */
export function useStartSession() {
  const store = useStore();
  const navigate = useNavigate();
  return (mode: PracticeMode, onlyIds?: readonly string[]) => {
    const now = Date.now();
    const questions = buildQuestions({
      mode,
      items: content.items,
      progress: store.getState().items,
      now,
      rng: Math.random,
      size: SESSION_SIZE,
      ...(onlyIds ? { onlyIds } : {}),
    });
    if (questions.length === 0) return false;
    store.startSession({ id: newId(), mode, startedAt: now, questions, answers: [], cursor: 0 });
    navigate("/chp/practice/session");
    return true;
  };
}

export function PracticeHome() {
  const t = useT();
  useTitle(t("practice.title"));
  const progress = useProgress();
  const store = useStore();
  const start = useStartSession();
  const [empty, setEmpty] = useState<PracticeMode | null>(null);
  const now = Date.now();
  const active = progress.activeSession;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <h1>{t("practice.title")}</h1>
        <p className="lead">{t("practice.lead", { n: SESSION_SIZE })}</p>
      </header>

      {active && (
        <section className="card card-accent stack-sm" aria-labelledby="active-h">
          <h2 id="active-h">{t("practice.inProgress")}</h2>
          <p>{t("practice.inProgressText", { mode: t(`mode.${active.mode}`), done: active.answers.length, total: active.questions.length })}</p>
          <div className="actions">
            <Link className="btn btn-primary" to="/chp/practice/session">
              {t("practice.resume")}
            </Link>
            <button type="button" className="btn btn-quiet" onClick={() => store.abandonSession()}>
              {t("practice.discard")}
            </button>
          </div>
        </section>
      )}

      <section aria-labelledby="modes-h" className="stack">
        <h2 id="modes-h">{active ? t("practice.orNew") : t("practice.start")}</h2>
        <ul className="mode-list">
          {MODES.map((mode) => {
            const count = itemsForMode(mode, content.items, progress.items, now).length;
            return (
              <li key={mode}>
                <button
                  type="button"
                  className="card card-link mode"
                  onClick={() => setEmpty(start(mode) ? null : mode)}
                  aria-describedby={`mode-${mode}`}
                  disabled={count === 0}
                >
                  <span className="mode-title">{t(`mode.${mode}`)}</span>
                  <span id={`mode-${mode}`} className="muted small">
                    {t(`modeDetail.${mode}`)} {count === 0 ? t("practice.nothing") : t("practice.available", { n: count })}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {empty && (
          <p role="status" className="muted">
            {t("practice.emptyMode", { mode: t(`mode.${empty}`) })}
          </p>
        )}
      </section>
    </div>
  );
}

export function PracticeSession() {
  const t = useT();
  useTitle(t("practice.sessionTitle"));
  const progress = useProgress();
  const store = useStore();
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const active = progress.activeSession;

  if (summary) return <Summary summary={summary} onRestart={() => setSummary(null)} />;
  if (!active) {
    return (
      <div className="stack">
        <h1>{t("practice.noSession")}</h1>
        <p>
          <Link to="/chp/practice">{t("practice.startLink")}</Link>
        </p>
      </div>
    );
  }

  const viewingIndex = active.cursor;
  const question = active.questions[viewingIndex]!;
  const record = active.answers.find((a) => a.questionId === question.id) ?? null;
  const isLast = viewingIndex === active.questions.length - 1;

  return (
    <div className="stack">
      <header className="stack-sm">
        <p className="eyebrow">{t(`mode.${active.mode}`)}</p>
        <h1 className="visually-hidden">{t("practice.sessionTitle")}</h1>
        <div
          className="session-bar"
          role="progressbar"
          aria-label={t("practice.sessionProgress")}
          aria-valuemin={0}
          aria-valuemax={active.questions.length}
          aria-valuenow={active.answers.length}
        >
          <div style={{ width: `${(active.answers.length / active.questions.length) * 100}%` }} />
        </div>
      </header>
      <QuestionView
        key={question.id}
        question={question}
        answered={record ? { response: record.response, correct: record.correct } : null}
        position={{ index: viewingIndex, total: active.questions.length }}
        nextLabel={isLast ? t("practice.finish") : t("question.next")}
        onAnswer={(response, correct, itemResults) => {
          store.answer({ questionId: question.id, response, correct, itemResults, at: Date.now() });
        }}
        onNext={() => {
          if (!isLast) return store.advance();
          const s = store.finishSession(Date.now());
          if (s) setSummary(s);
        }}
      />
      <p className="muted small">{t("practice.savedAsYouGo")}</p>
    </div>
  );
}

function Summary({ summary, onRestart }: { summary: SessionSummary; onRestart: () => void }) {
  const t = useT();
  const start = useStartSession();
  const missed = summary.missedItemIds.map(getItem).filter((i) => i !== undefined);
  const mastered = summary.masteredItemIds.map(getItem).filter((i) => i !== undefined);
  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">{t(`mode.${summary.mode}`)}</p>
        <h1>{t("summary.title")}</h1>
      </header>
      <section className="card stats" aria-label={t("summary.results")}>
        <div>
          <span className="stat-value">{percent(summary.correct, summary.total)}</span>
          <span className="stat-label">{t("summary.accuracy")}</span>
        </div>
        <div>
          <span className="stat-value">
            {summary.correct}/{summary.total}
          </span>
          <span className="stat-label">{t("summary.correct")}</span>
        </div>
        <div>
          <span className="stat-value">{mastered.length}</span>
          <span className="stat-label">{t("summary.newlyMastered")}</span>
        </div>
      </section>

      {missed.length > 0 ? (
        <section className="stack" aria-labelledby="missed-h">
          <h2 id="missed-h">{t("summary.reviewThese")}</h2>
          <ul className="review-list">
            {missed.map((item) => (
              <li key={item.id}>
                <Link to={`/chp/items/${item.id}`} lang="en">
                  <strong>{item.term}</strong> — {item.answer}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="card card-success">{t("summary.noMistakes")}</p>
      )}

      <div className="actions actions-stack">
        {missed.length > 0 && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              onRestart();
              start(
                "mixed",
                missed.map((i) => i.id),
              );
            }}
          >
            {t("summary.practiseAgain", { n: missed.length })}
          </button>
        )}
        <button
          type="button"
          className={missed.length ? "btn" : "btn btn-primary"}
          onClick={() => {
            onRestart();
            start(summary.mode === "mistakes" || summary.mode === "due" ? "mixed" : summary.mode);
          }}
        >
          {t("summary.newSession")}
        </button>
        <Link className="btn btn-quiet" to="/progress">
          {t("summary.viewProgress")}
        </Link>
      </div>
    </div>
  );
}
