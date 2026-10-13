import { Link } from "react-router";
import { content } from "../content";
import { Icon } from "../components/Icon";
import { InstallCard } from "../components/InstallCard";
import { useI18n, type Lang } from "../i18n";
import { dayKey, streak } from "../lib/streak";
import { isDue, stateOf } from "../lib/srs";
import { useProgress, useTitle } from "../state";
import { useStartSession } from "./Practice";

export function Home() {
  const { t, lang } = useI18n();
  useTitle("");
  const progress = useProgress();
  const start = useStartSession();
  const now = Date.now();
  const active = progress.activeSession;
  const due = content.items.filter((i) => isDue(progress.items[i.id], now)).length;
  const mastered = content.items.filter((i) => stateOf(progress.items[i.id]) === "mastered").length;
  const days = streak(progress.activity, now);
  const today = progress.activity[dayKey(now)] ?? 0;
  const nextLesson = content.lessons.find((l) => !progress.lessons[l.id]?.completedAt);
  const isNew = Object.keys(progress.items).length === 0;

  return (
    <div className="stack-lg">
      <section className="today card" aria-labelledby="today-h">
        <h1 id="today-h">{isNew ? t("home.welcomeTitle") : t("home.todayTitle")}</h1>
        {isNew ? (
          <p className="lead">{t("home.welcomeLead")}</p>
        ) : (
          <ul className="today-stats" aria-label={t("home.todayStats")}>
            <li>
              <Icon name="flame" />
              <span className="today-value">{t("home.streakDays", { n: days })}</span>
              <span className="today-label">{t("home.streak")}</span>
            </li>
            <li>
              <span className="today-value">{today}</span>
              <span className="today-label">{t("home.answersToday")}</span>
            </li>
            <li>
              <span className="today-value">
                {mastered}/{content.counts.teachable}
              </span>
              <span className="today-label">{t("home.mastered")}</span>
            </li>
          </ul>
        )}
        <div className="today-cta">
          {active ? (
            <Link className="btn btn-primary btn-block" to="/chp/practice/session">
              {t("home.resume", { done: active.answers.length, total: active.questions.length })}
            </Link>
          ) : due > 0 ? (
            <button type="button" className="btn btn-primary btn-block" onClick={() => start("due")}>
              {t("home.reviewDue", { n: due })}
            </button>
          ) : nextLesson ? (
            <Link className="btn btn-primary btn-block" to={`/chp/lessons/${nextLesson.id}`}>
              {isNew ? t("home.startFirst") : t("home.nextLesson", { title: lessonTitle(nextLesson, lang) })}
            </Link>
          ) : (
            <button type="button" className="btn btn-primary btn-block" onClick={() => start("mixed")}>
              {t("home.practice")}
            </button>
          )}
        </div>
      </section>

      <nav aria-label={t("home.quick")} className="tiles">
        <Link to="/chp" className="tile">
          <Icon name="book" size={26} />
          <span>{t("home.tileLessons")}</span>
        </Link>
        <Link to="/chp/flashcards" className="tile">
          <Icon name="cards" size={26} />
          <span>{t("home.tileFlashcards")}</span>
        </Link>
        <Link to="/chp/practice" className="tile">
          <Icon name="practice" size={26} />
          <span>{t("home.tilePractice")}</span>
        </Link>
        <Link to="/chp/reference" className="tile">
          <Icon name="search" size={26} />
          <span>{t("home.tileReference")}</span>
        </Link>
      </nav>

      <InstallCard />

      <section aria-labelledby="pick-h" className="stack">
        <h2 id="pick-h">{t("home.jurisdictions")}</h2>
        <ul className="jurisdictions">
          <li>
            <Link to="/chp" className="card card-link jurisdiction">
              <span className="jurisdiction-tag">{t("home.available")}</span>
              <span className="jurisdiction-name">{content.jurisdiction.name}</span>
              <span className="muted">{t("home.chpSummary", { codes: content.counts.teachable_codes, letters: content.counts.teachable_letters, lessons: content.lessons.length })}</span>
            </Link>
          </li>
          <li className="card jurisdiction is-unavailable" aria-disabled="true">
            <span className="jurisdiction-tag muted-tag">{t("home.comingLater")}</span>
            <span className="jurisdiction-name">{t("home.otherAgencies")}</span>
            <span className="muted">{t("home.otherAgenciesText")}</span>
          </li>
        </ul>
      </section>
    </div>
  );
}

export function lessonTitle(lesson: { title: string; title_ko: string }, lang: Lang): string {
  return lang === "ko" ? lesson.title_ko : lesson.title;
}

export function lessonSummary(lesson: { summary: string; summary_ko: string }, lang: Lang): string {
  return lang === "ko" ? lesson.summary_ko : lesson.summary;
}
