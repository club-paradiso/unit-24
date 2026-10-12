import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { content, getLesson, lessonItems, SYSTEM_LABEL } from "../content";
import { QuestionView, type Answered } from "../components/QuestionView";
import { Excerpt } from "../components/SourceDetails";
import { TrustBadges } from "../components/Status";
import { PASS_RATIO, type LessonResult } from "../lib/progress";
import { lessonCheck } from "../lib/quiz";
import { useStore, useTitle } from "../state";
import { NotFound } from "./NotFound";

type Phase = { kind: "study"; index: number } | { kind: "check"; index: number } | { kind: "done"; result: LessonResult; score: number };

export function LessonPage() {
  const { lessonId = "" } = useParams();
  const lesson = getLesson(lessonId);
  if (!lesson) return <NotFound what="lesson" />;
  return <LessonFlow key={lesson.id} lessonId={lesson.id} />;
}

function LessonFlow({ lessonId }: { lessonId: string }) {
  const lesson = getLesson(lessonId)!;
  useTitle(lesson.title);
  const store = useStore();
  const items = useMemo(() => lessonItems(lesson), [lesson]);
  const [attempt, setAttempt] = useState(0);
  const questions = useMemo(() => lessonCheck(items, content.items, Math.random), [items, attempt]);
  const [phase, setPhase] = useState<Phase>({ kind: "study", index: 0 });
  const [answers, setAnswers] = useState<Record<string, Answered>>({});
  const lessonIndex = content.lessons.findIndex((l) => l.id === lesson.id);
  const nextLesson = content.lessons[lessonIndex + 1];

  const header = (
    <header className="stack-sm">
      <p className="eyebrow">
        <Link to="/chp">CHP</Link> · Lesson {lessonIndex + 1} of {content.lessons.length}
      </p>
      <h1>{lesson.title}</h1>
    </header>
  );

  if (phase.kind === "study") {
    const item = items[phase.index]!;
    const last = phase.index === items.length - 1;
    return (
      <div className="stack-lg">
        {header}
        <p className="muted" aria-live="polite">
          Card {phase.index + 1} of {items.length} · read each entry, then take a {questions.length}-question check.
        </p>
        <article className="card study-card" aria-label={`${item.term}: ${item.answer}`}>
          <p className="chip">{SYSTEM_LABEL[item.code_system]}</p>
          <p className="study-term">{item.term}</p>
          <p className="study-answer">{item.answer}</p>
          <TrustBadges item={item} compact />
          <Excerpt item={item} />
          {item.notes.map((n) => (
            <p key={n} className="muted small">
              {n}
            </p>
          ))}
          <Link to={`/chp/items/${item.id}`} className="small">
            Full source details for {item.term}
          </Link>
        </article>
        <div className="actions">
          <button type="button" className="btn" disabled={phase.index === 0} onClick={() => setPhase({ kind: "study", index: phase.index - 1 })}>
            Previous
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setPhase(last ? { kind: "check", index: 0 } : { kind: "study", index: phase.index + 1 })}>
            {last ? "Start the check" : "Next"}
          </button>
          {!last && (
            <button type="button" className="btn btn-quiet" onClick={() => setPhase({ kind: "check", index: 0 })}>
              Skip to check
            </button>
          )}
        </div>
      </div>
    );
  }

  if (phase.kind === "check") {
    const q = questions[phase.index]!;
    const last = phase.index === questions.length - 1;
    return (
      <div className="stack-lg">
        {header}
        <QuestionView
          question={q}
          answered={answers[q.id] ?? null}
          position={{ index: phase.index, total: questions.length }}
          nextLabel={last ? "See result" : "Next question"}
          onAnswer={(response, correct, itemResults) => {
            setAnswers((a) => ({ ...a, [q.id]: { response, correct } }));
            store.recordResults(itemResults, Date.now());
          }}
          onNext={() => {
            if (!last) return setPhase({ kind: "check", index: phase.index + 1 });
            const score = questions.filter((x) => answers[x.id]?.correct).length;
            const result = store.recordLessonCheck(lesson.id, score, questions.length, Date.now());
            setPhase({ kind: "done", result, score });
          }}
        />
      </div>
    );
  }

  const passed = phase.score / questions.length >= PASS_RATIO;
  const missed = questions.filter((q) => !answers[q.id]?.correct);
  return (
    <div className="stack-lg">
      {header}
      <section className={`card ${passed ? "card-success" : "card-accent"}`} aria-labelledby="result-h">
        <h2 id="result-h">{passed ? "Lesson complete" : "Not passed yet"}</h2>
        <p className="score">
          {phase.score} / {questions.length} correct
        </p>
        <p>
          {passed
            ? "Your result is saved. These items will come back in practice when they are due for review."
            : `You need ${Math.ceil(PASS_RATIO * questions.length)} of ${questions.length} to complete the lesson. Your answers still count towards practice.`}
        </p>
        {missed.length > 0 && (
          <>
            <h3>To review</h3>
            <ul className="review-list">
              {missed.map((q) => {
                const item = content.items.find((i) => i.id === q.itemIds[0])!;
                return (
                  <li key={q.id}>
                    <Link to={`/chp/items/${item.id}`}>
                      <strong>{item.term}</strong> — {item.answer}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
      <div className="actions">
        {!passed && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setAnswers({});
              setAttempt((n) => n + 1);
              setPhase({ kind: "study", index: 0 });
            }}
          >
            Study again
          </button>
        )}
        {passed && nextLesson && (
          <Link className="btn btn-primary" to={`/chp/lessons/${nextLesson.id}`}>
            Next lesson: {nextLesson.title}
          </Link>
        )}
        <Link className="btn" to="/chp">
          Back to lessons
        </Link>
      </div>
    </div>
  );
}
