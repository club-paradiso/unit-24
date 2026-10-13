import { useState } from "react";
import { Link } from "react-router";
import { content } from "../content";
import { Meter } from "../components/Status";
import { useI18n } from "../i18n";
import { PASS_RATIO } from "../lib/progress";
import { stateOf } from "../lib/srs";
import { useProgress, useTitle } from "../state";
import { lessonSummary, lessonTitle } from "./Home";

export function Hub() {
  const { t, lang } = useI18n();
  useTitle(t("hub.title"));
  const progress = useProgress();
  const [open, setOpen] = useState(false);
  const mastered = content.items.filter((i) => stateOf(progress.items[i.id]) === "mastered").length;
  const c = content.counts;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">{content.jurisdiction.region}</p>
        <h1>{content.jurisdiction.name}</h1>
        <p className="lead">{t("hub.lead", { title: content.source.title, version: content.source.version })}</p>
      </header>

      <aside className="notice notice-info">
        <button type="button" className="notice-toggle" aria-expanded={open} aria-controls="trust-details" onClick={() => setOpen((v) => !v)}>
          <span className="notice-title">{t("hub.trustTitle")}</span>
          <span className="muted small">{c.human_verified === 0 ? t("hub.trustSummaryNone") : t("hub.trustSummary", { n: c.human_verified, total: c.teachable })}</span>
          <span aria-hidden="true" className="chevron">
            {open ? "▴" : "▾"}
          </span>
        </button>
        {open && (
          <ul id="trust-details">
            <li>{t("hub.trust1")}</li>
            <li>{c.human_verified === 0 ? t("hub.trust2None") : t("hub.trust2", { n: c.human_verified, total: c.teachable })}</li>
            <li>{t("hub.trust3")}</li>
            <li>
              {t("hub.trust4", { n: c.excluded })} <Link to="/about">{t("common.details")}</Link>
            </li>
          </ul>
        )}
      </aside>

      <div className="grid-2">
        <Meter label={t("hub.mastered")} value={mastered} max={c.teachable} />
        <Meter label={t("hub.lessonsDone")} value={content.lessons.filter((l) => progress.lessons[l.id]?.completedAt).length} max={content.lessons.length} />
      </div>

      <section className="stack" aria-labelledby="lessons-h">
        <h2 id="lessons-h">{t("hub.lessons")}</h2>
        <ol className="lesson-list">
          {content.lessons.map((lesson, n) => {
            const r = progress.lessons[lesson.id];
            const status = r?.completedAt
              ? t("hub.lessonDone")
              : r
                ? t("hub.lessonBest", { best: r.bestScore, total: r.total, pass: Math.ceil(PASS_RATIO * r.total) })
                : t("hub.lessonNotStarted");
            return (
              <li key={lesson.id}>
                <Link to={`/chp/lessons/${lesson.id}`} className="card card-link lesson-row">
                  <span className={`lesson-num ${r?.completedAt ? "is-done" : ""}`} aria-hidden="true">
                    {r?.completedAt ? "✓" : n + 1}
                  </span>
                  <span className="lesson-body">
                    <span className="lesson-title">{lessonTitle(lesson, lang)}</span>
                    <span className="muted small">
                      {t("hub.items", { n: lesson.item_ids.length })} · {lessonSummary(lesson, lang)}
                    </span>
                    <span className={`lesson-status ${r?.completedAt ? "is-done" : ""}`}>{status}</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
