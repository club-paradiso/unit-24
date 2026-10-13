import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { getItem } from "../content";
import { useT } from "../i18n";
import { haptic } from "../lib/haptics";
import { isCorrect, spellBreakdown, type Question } from "../lib/quiz";

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
  const t = useT();
  const nextRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [typed, setTyped] = useState("");
  const labelId = useId();

  const submit = (response: string) => {
    if (answered) return;
    const correct = isCorrect(question, response);
    haptic(correct ? "success" : "error");
    onAnswer(response, correct, resultsFor(question, response));
  };

  useEffect(() => {
    setTyped("");
  }, [question.id]);

  useEffect(() => {
    if (answered) nextRef.current?.focus({ preventScroll: true });
    else if (question.type === "spell") inputRef.current?.focus();
  }, [answered, question.id, question.type]);

  useEffect(() => {
    if (question.type === "spell") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (answered) return;
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

  const subjectIsText = question.type === "meaning-to-code";
  return (
    <section className="question" aria-labelledby={labelId}>
      <div className="question-meta">
        <span className="chip">{t(`qtype.${question.type}`)}</span>
        {position && <span className="muted">{t("question.position", { n: position.index + 1, total: position.total })}</span>}
      </div>
      <h2 id={labelId} className="question-prompt">
        {t(`prompt.${question.type}`)}
      </h2>
      <p className={`question-subject ${subjectIsText ? "is-text" : ""}`} lang="en">
        {question.subject}
      </p>

      {question.type === "spell" ? (
        <form onSubmit={onSpell} className="spell-form">
          <label htmlFor={`${labelId}-input`}>{t("question.spellLabel")}</label>
          <div className="spell-row">
            <input
              id={`${labelId}-input`}
              ref={inputRef}
              lang="en"
              value={answered ? answered.response : typed}
              onChange={(e) => setTyped(e.target.value)}
              disabled={answered !== null}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="words"
              enterKeyHint="done"
              spellCheck={false}
              placeholder="Adam Boy Charles"
            />
            {!answered && (
              <button type="submit" className="btn btn-primary" disabled={!typed.trim()}>
                {t("question.check")}
              </button>
            )}
          </div>
        </form>
      ) : (
        <div className="options" role="group" aria-label={t("question.options")}>
          {question.options.map((option, i) => {
            const isAnswer = option === question.answer;
            const chosen = answered?.response === option;
            const cls = answered ? (isAnswer ? "is-correct" : chosen ? "is-wrong" : "is-dim") : "";
            return (
              <button key={option} type="button" className={`option ${cls}`} onClick={() => submit(option)} disabled={answered !== null} aria-pressed={chosen}>
                <kbd aria-hidden="true">{i + 1}</kbd>
                <span className="option-text" lang="en">
                  {option}
                </span>
                {answered && isAnswer && <span className="option-mark">{t("question.correctAnswer")}</span>}
                {answered && chosen && !isAnswer && <span className="option-mark">{t("question.yourAnswer")}</span>}
              </button>
            );
          })}
        </div>
      )}

      <div aria-live="polite" className="feedback-region">
        {answered && <Feedback question={question} answered={answered} />}
      </div>
      {!answered && question.type !== "spell" && <p className="hint muted">{t("question.keyHint", { n: question.options.length })}</p>}

      {answered && (
        <div className="sticky-actions">
          <button ref={nextRef} type="button" className="btn btn-primary btn-block" onClick={onNext}>
            {nextLabel}
          </button>
        </div>
      )}
    </section>
  );
}

function Feedback({ question, answered }: { question: Question; answered: Answered }) {
  const t = useT();
  const items = question.itemIds.map(getItem);
  return (
    <div className={`feedback ${answered.correct ? "feedback-ok" : "feedback-bad"}`}>
      <p className="feedback-title">
        <span aria-hidden="true">{answered.correct ? "✓ " : "✗ "}</span>
        {answered.correct ? t("feedback.correct") : t("feedback.wrong")}
      </p>
      {question.type === "spell" ? (
        <ul className="spell-breakdown" lang="en">
          {spellBreakdown(question, answered.response).map((b, i) => (
            <li key={i} className={b.ok ? "ok" : "bad"}>
              <strong>{b.letter}</strong> = {b.expected}
              {!b.ok && <span className="muted"> ({b.given ? `“${b.given}”` : "—"})</span>}
            </li>
          ))}
        </ul>
      ) : (
        !answered.correct && (
          <p>
            {t("feedback.cardGives")} <strong lang="en">{question.answer}</strong>
          </p>
        )
      )}
      {items.length === 1 && items[0] && (
        <p className="feedback-source">
          {t("feedback.source", { page: items[0].page ?? "?" })} <Link to={`/chp/items/${items[0].id}`}>{t("feedback.seeSource", { term: items[0].term })}</Link>
        </p>
      )}
    </div>
  );
}
