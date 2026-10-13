import { useEffect, useMemo } from "react";
import { Link, useParams } from "react-router";
import { content, getLesson, lessonItems } from "../content";
import { QuestionView } from "../components/QuestionView";
import { Excerpt } from "../components/SourceDetails";
import { TrustBadges } from "../components/Status";
import { useI18n } from "../i18n";
import { PASS_RATIO, type LessonDraft } from "../lib/progress";
import { lessonCheck } from "../lib/quiz";
import { useProgress, useStore, useTitle } from "../state";
import { firebaseConfig } from "../sync/config";
import { sendStats, sessionStats } from "../sync/stats";
import { lessonTitle } from "./Home";
import { NotFound } from "./NotFound";
import { systemLabel } from "./labels";

export function LessonPage() {
  const { lessonId = "" } = useParams();
  const lesson = getLesson(lessonId);
  if (!lesson) return <NotFound what="lesson" />;
  return <LessonFlow key={lesson.id} lessonId={lesson.id} />;
}

function LessonFlow({ lessonId }: { lessonId: string }) {
  const { t, lang } = useI18n();
  const lesson = getLesson(lessonId)!;
  const title = lessonTitle(lesson, lang);
  useTitle(title);
  const store = useStore();
  const items = useMemo(() => lessonItems(lesson), [lesson]);
  const progress = useProgress();
  const fresh = useMemo<LessonDraft>(() => ({ phase: "study", index: 0, questions: lessonCheck(items, content.items, Math.random), answers: [], contentVersion: content.content_version, updatedAt: Date.now() }), [items]);
  const saved = progress.lessonDrafts[lessonId];
  const draft = saved?.contentVersion === content.content_version && (saved.phase !== "study" || saved.index < items.length) ? saved : fresh;
  useEffect(() => { if (draft === fresh) store.saveLessonDraft(lessonId, fresh); }, [draft, fresh, store, lessonId]);
  const questions = draft.questions;
  const answers = Object.fromEntries(draft.answers.map(a => [a.questionId, a]));
  const phase = { kind: draft.phase, index: draft.index, score: draft.answers.filter(a => a.correct).length };
  const setPhase = (next: { kind: "study" | "check"; index: number }) => store.saveLessonDraft(lessonId, { ...draft, phase: next.kind, index: next.index, updatedAt: Date.now() });
  const lessonIndex = content.lessons.findIndex((l) => l.id === lesson.id);
  const nextLesson = content.lessons[lessonIndex + 1];
  const steps = items.length + questions.length;
  const step = phase.kind === "study" ? phase.index : phase.kind === "check" ? items.length + phase.index : steps;

  const header = (
    <header className="stack-sm">
      <p className="eyebrow">{t("lesson.eyebrow", { n: lessonIndex + 1, total: content.lessons.length })}</p>
      <h1 className="h-compact">{title}</h1>
      <div className="session-bar" role="progressbar" aria-label={t("lesson.progress")} aria-valuemin={0} aria-valuemax={steps} aria-valuenow={step}>
        <div style={{ width: `${(step / steps) * 100}%` }} />
      </div>
    </header>
  );

  if (phase.kind === "study") {
    const item = items[phase.index]!;
    const last = phase.index === items.length - 1;
    return (
      <div className="stack">
        {header}
        <p className="muted" aria-live="polite">
          {t("lesson.cardOf", { n: phase.index + 1, total: items.length, check: questions.length })}
        </p>
        <article className="card study-card" aria-label={`${item.term}: ${item.answer}`}>
          <p className="chip">{systemLabel(item.code_system, t)}</p>
          <p className="study-term" lang="en">
            {item.term}
          </p>
          <p className="study-answer" lang="en">
            {item.answer}
          </p>
          <TrustBadges item={item} compact />
          <Excerpt item={item} />
          <Link to={`/chp/items/${item.id}`} className="small">
            {t("lesson.sourceDetails", { term: item.term })}
          </Link>
        </article>
        <div className="sticky-actions">
          <button type="button" className="btn" disabled={phase.index === 0} onClick={() => setPhase({ kind: "study", index: phase.index - 1 })}>
            {t("common.previous")}
          </button>
          <button type="button" className="btn btn-primary btn-grow" onClick={() => setPhase(last ? { kind: "check", index: 0 } : { kind: "study", index: phase.index + 1 })}>
            {last ? t("lesson.startCheck") : t("common.next")}
          </button>
        </div>
        {!last && (
          <button type="button" className="btn btn-quiet" onClick={() => setPhase({ kind: "check", index: 0 })}>
            {t("lesson.skipToCheck")}
          </button>
        )}
      </div>
    );
  }

  if (phase.kind === "check") {
    const q = questions[phase.index]!;
    const last = phase.index === questions.length - 1;
    return (
      <div className="stack">
        {header}
        <QuestionView
          question={q}
          answered={answers[q.id] ?? null}
          position={{ index: phase.index, total: questions.length }}
          nextLabel={last ? t("lesson.seeResult") : t("question.next")}
          onAnswer={(response, correct, itemResults) => {
            store.answerLesson(lessonId, { questionId: q.id, response, correct, itemResults, at: Date.now() });
          }}
          onNext={() => {
            if (!last) return setPhase({ kind: "check", index: phase.index + 1 });
            if (store.getState().lessonDrafts[lessonId]?.phase !== "check") return;
            store.completeLesson(lessonId, Date.now());
            void sendStats(firebaseConfig, content.content_version, sessionStats("lesson", draft.answers.map(a => a.itemResults)));
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
        <h2 id="result-h">{passed ? t("lesson.passed") : t("lesson.notPassed")}</h2>
        <p className="score">{t("lesson.score", { score: phase.score, total: questions.length })}</p>
        <p>{passed ? t("lesson.passedText") : t("lesson.notPassedText", { need: Math.ceil(PASS_RATIO * questions.length), total: questions.length })}</p>
        {missed.length > 0 && (
          <>
            <h3>{t("lesson.toReview")}</h3>
            <ul className="review-list">
              {missed.map((q) => {
                const item = content.items.find((i) => i.id === q.itemIds[0])!;
                return (
                  <li key={q.id}>
                    <Link to={`/chp/items/${item.id}`} lang="en">
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
        {(
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              store.saveLessonDraft(lessonId, { ...fresh, questions: lessonCheck(items, content.items, Math.random), updatedAt: Date.now() });
            }}
          >
            {t("lesson.studyAgain")}
          </button>
        )}
        {passed && nextLesson && (
          <Link className="btn btn-primary" to={`/chp/lessons/${nextLesson.id}`}>
            {t("lesson.nextLesson", { title: lessonTitle(nextLesson, lang) })}
          </Link>
        )}
        <Link className="btn" to="/chp">
          {t("lesson.backToLessons")}
        </Link>
      </div>
    </div>
  );
}
