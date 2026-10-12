import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { getItem } from "../content";
import { isCorrect, QUESTION_LABEL, spellBreakdown, type Question } from "../lib/quiz";

export interface Answered {
  response: string;
  correct: boolean;
}

interface Props {
  question: Question;
  /** Set once the learner has answered; the view then shows feedback. */
  answered: Answered | null;
  onAnswer: (response: string, correct: boolean, itemResults: Record<string, boolean>) => void;
  onNext: () => void;
  nextLabel: string;
  position?: { index: number; total: number };
}

export function resultsFor(question: Question, response: string): Record<string, boolean> {
  if (question.type === "spell") {
    const breakdown = spellBreakdown(question, response);
    return Object.fromEntries(question.itemIds.map((id, i) => [id, breakdown[i]?.ok ?? false]));
  }
  return { [question.itemIds[0]]: isCorrect(question, response) };
}

export function QuestionView({ question, answered, onAnswer, onNext, nextLabel, position }: Props) {
  const nextRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [typed, setTyped] = useState("");
  const labelId = useId();

  const submit = (response: string) => {
    if (answered) return;
    onAnswer(response, isCorrect(question, response), resultsFor(question, response));
  };

  useEffect(() => {
    setTyped("");
  }, [question.id]);

  useEffect(() => {
    if (answered) nextRef.current?.focus();
    else if (question.type === "spell") inputRef.current?.focus();
  }, [answered, question.id, question.type]);

  useEffect(() => {
    if (question.type === "spell" || answered) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const n = Number(e.key);
      const option = Number.isInteger(n) && n >= 1 ? question.options[n - 1] : undefined;
      if (option !== undefined) {
        e.preventDefault();
        submit(option);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const onSpell = (e: FormEvent) => {
    e.preventDefault();
    if (typed.trim()) submit(typed);
  };

  return (
    <section className="question" aria-labelledby={labelId}>
      <div className="question-meta">
        <span className="chip">{QUESTION_LABEL[question.type]}</span>
        {position && (
          <span className="muted">
            Question {position.index + 1} of {position.total}
          </span>
        )}
      </div>
      <h2 id={labelId} className="question-prompt">
        {question.prompt}
      </h2>
      <p className={`question-subject ${question.type === "meaning-to-code" ? "is-text" : ""}`}>{question.subject}</p>

      {question.type === "spell" ? (
        <form onSubmit={onSpell} className="spell-form">
          <label htmlFor={`${labelId}-input`}>Your answer (one word per letter)</label>
          <div className="spell-row">
            <input
              id={`${labelId}-input`}
              ref={inputRef}
              value={answered ? answered.response : typed}
              onChange={(e) => setTyped(e.target.value)}
              disabled={answered !== null}
              autoComplete="off"
              autoCapitalize="words"
              spellCheck={false}
              placeholder="e.g. Adam Boy Charles"
            />
            {!answered && (
              <button type="submit" className="btn btn-primary" disabled={!typed.trim()}>
                Check
              </button>
            )}
          </div>
        </form>
      ) : (
        <div className="options" role="group" aria-label="Answer options">
          {question.options.map((option, i) => {
            const isAnswer = option === question.answer;
            const chosen = answered?.response === option;
            const cls = answered ? (isAnswer ? "is-correct" : chosen ? "is-wrong" : "is-dim") : "";
            return (
              <button key={option} type="button" className={`option ${cls}`} onClick={() => submit(option)} disabled={answered !== null} aria-pressed={chosen}>
                <kbd aria-hidden="true">{i + 1}</kbd>
                <span className="option-text">{option}</span>
                {answered && isAnswer && <span className="option-mark">Correct answer</span>}
                {answered && chosen && !isAnswer && <span className="option-mark">Your answer</span>}
              </button>
            );
          })}
        </div>
      )}

      <div aria-live="polite" className="feedback-region">
        {answered && <Feedback question={question} answered={answered} />}
      </div>

      {answered && (
        <div className="question-actions">
          <button ref={nextRef} type="button" className="btn btn-primary" onClick={onNext}>
            {nextLabel}
          </button>
        </div>
      )}
      {!answered && question.type !== "spell" && <p className="hint muted">Tip: press 1–{question.options.length} to answer.</p>}
    </section>
  );
}

function Feedback({ question, answered }: { question: Question; answered: Answered }) {
  const items = question.itemIds.map(getItem);
  return (
    <div className={`feedback ${answered.correct ? "feedback-ok" : "feedback-bad"}`}>
      <p className="feedback-title">
        <span aria-hidden="true">{answered.correct ? "✓ " : "✗ "}</span>
        {answered.correct ? "Correct" : "Not quite"}
      </p>
      {question.type === "spell" ? (
        <ul className="spell-breakdown">
          {spellBreakdown(question, answered.response).map((b, i) => (
            <li key={i} className={b.ok ? "ok" : "bad"}>
              <strong>{b.letter}</strong> = {b.expected}
              {!b.ok && <span className="muted"> (you wrote {b.given ? `“${b.given}”` : "nothing"})</span>}
            </li>
          ))}
        </ul>
      ) : (
        !answered.correct && (
          <p>
            The card gives <strong>{question.answer}</strong>
            {question.type === "meaning-to-code" ? ` for “${question.subject}”` : ` for ${question.subject}`}.
          </p>
        )
      )}
      {items.length === 1 && items[0] && (
        <p className="feedback-source">
          From page {items[0].page} of the CHP 254 card, matched by automated review, not human-verified.{" "}
          <Link to={`/chp/items/${items[0].id}`}>See source for {items[0].term}</Link>
        </p>
      )}
    </div>
  );
}
