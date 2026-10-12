import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { content, getItem } from "../content";
import { QuestionView } from "../components/QuestionView";
import { percent } from "../lib/format";
import type { SessionSummary } from "../lib/progress";
import { buildQuestions, itemsForMode, MODE_LABEL, type PracticeMode } from "../lib/quiz";
import { newId } from "../lib/random";
import { useProgress, useStore, useTitle } from "../state";

const MODES: { mode: PracticeMode; detail: string }[] = [
  { mode: "mixed", detail: "Codes and alphabet together, weakest and due items first." },
  { mode: "codes", detail: "Code → meaning and meaning → code." },
  { mode: "alphabet", detail: "Card words for letters, and spelling letter groups out." },
  { mode: "due", detail: "Only items whose next review date has arrived." },
  { mode: "mistakes", detail: "Items you answered wrongly last time." },
];

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
  useTitle("Practice");
  const progress = useProgress();
  const store = useStore();
  const start = useStartSession();
  const [empty, setEmpty] = useState<PracticeMode | null>(null);
  const now = Date.now();
  const active = progress.activeSession;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp">CHP</Link>
        </p>
        <h1>Practice</h1>
        <p className="lead">Sessions of up to {SESSION_SIZE} questions. Each answer updates when the item comes back for review.</p>
      </header>

      {active && (
        <section className="card card-accent" aria-labelledby="active-h">
          <h2 id="active-h">Session in progress</h2>
          <p>
            {MODE_LABEL[active.mode]} — {active.answers.length} of {active.questions.length} answered.
          </p>
          <div className="actions">
            <Link className="btn btn-primary" to="/chp/practice/session">
              Resume session
            </Link>
            <button type="button" className="btn btn-quiet" onClick={() => store.abandonSession()}>
              Discard it
            </button>
          </div>
        </section>
      )}

      <section aria-labelledby="modes-h" className="stack">
        <h2 id="modes-h">{active ? "Or start a new session" : "Start a session"}</h2>
        <ul className="mode-list">
          {MODES.map(({ mode, detail }) => {
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
                  <span className="mode-title">{MODE_LABEL[mode]}</span>
                  <span id={`mode-${mode}`} className="muted">
                    {detail} {count === 0 ? "Nothing to practise here yet." : `${count} item${count === 1 ? "" : "s"} available.`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {empty && (
          <p role="status" className="muted">
            Nothing to practise in “{MODE_LABEL[empty]}” right now.
          </p>
        )}
      </section>
    </div>
  );
}

export function PracticeSession() {
  useTitle("Practice session");
  const progress = useProgress();
  const store = useStore();
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const active = progress.activeSession;

  if (summary) return <Summary summary={summary} onRestart={() => setSummary(null)} />;
  if (!active) {
    return (
      <div className="stack">
        <h1>No session in progress</h1>
        <p>
          <Link to="/chp/practice">Start a practice session</Link>
        </p>
      </div>
    );
  }

  const viewingIndex = active.cursor;
  const question = active.questions[viewingIndex]!;
  const record = active.answers.find((a) => a.questionId === question.id) ?? null;
  const isLast = viewingIndex === active.questions.length - 1;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp/practice">Practice</Link> · {MODE_LABEL[active.mode]}
        </p>
        <h1 className="visually-hidden">Practice session</h1>
        <div className="session-bar" role="progressbar" aria-label="Session progress" aria-valuemin={0} aria-valuemax={active.questions.length} aria-valuenow={active.answers.length}>
          <div style={{ width: `${(active.answers.length / active.questions.length) * 100}%` }} />
        </div>
      </header>
      <QuestionView
        key={question.id}
        question={question}
        answered={record ? { response: record.response, correct: record.correct } : null}
        position={{ index: viewingIndex, total: active.questions.length }}
        nextLabel={isLast ? "Finish session" : "Next question"}
        onAnswer={(response, correct, itemResults) => {
          store.answer({ questionId: question.id, response, correct, itemResults, at: Date.now() });
        }}
        onNext={() => {
          if (!isLast) return store.advance();
          const s = store.finishSession(Date.now());
          if (s) setSummary(s);
        }}
      />
      <p className="muted small">Your answers are saved as you go — you can leave and resume this session later.</p>
    </div>
  );
}

function Summary({ summary, onRestart }: { summary: SessionSummary; onRestart: () => void }) {
  const start = useStartSession();
  const missed = summary.missedItemIds.map(getItem).filter((i) => i !== undefined);
  const mastered = summary.masteredItemIds.map(getItem).filter((i) => i !== undefined);
  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp/practice">Practice</Link> · {MODE_LABEL[summary.mode]}
        </p>
        <h1>Session summary</h1>
      </header>
      <section className="card stats" aria-label="Results">
        <div>
          <span className="stat-value">{percent(summary.correct, summary.total)}</span>
          <span className="stat-label">accuracy</span>
        </div>
        <div>
          <span className="stat-value">
            {summary.correct}/{summary.total}
          </span>
          <span className="stat-label">questions correct</span>
        </div>
        <div>
          <span className="stat-value">{mastered.length}</span>
          <span className="stat-label">newly mastered</span>
        </div>
      </section>

      {missed.length > 0 ? (
        <section className="stack" aria-labelledby="missed-h">
          <h2 id="missed-h">Review these</h2>
          <ul className="review-list">
            {missed.map((item) => (
              <li key={item.id}>
                <Link to={`/chp/items/${item.id}`}>
                  <strong>{item.term}</strong> — {item.answer}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="card card-success">No mistakes in this session.</p>
      )}

      <div className="actions">
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
            Practise these {missed.length} again
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
          New session
        </button>
        <Link className="btn btn-quiet" to="/progress">
          View progress
        </Link>
      </div>
    </div>
  );
}
