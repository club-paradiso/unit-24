import { Link } from "react-router";
import { content, getItem } from "../content";
import { Icon } from "../components/Icon";
import { Meter } from "../components/Status";
import { useI18n } from "../i18n";
import { dateTime, percent } from "../lib/format";
import { isDue, needsReview, stateOf } from "../lib/srs";
import { streak } from "../lib/streak";
import { useProgress, useTitle } from "../state";
import { lessonTitle } from "./Home";

export function ProgressPage() {
  const { t, lang } = useI18n();
  useTitle(t("progress.title"));
  const progress = useProgress();
  const now = Date.now();

  const stats = Object.entries(progress.items).filter(([id]) => getItem(id));
  const seen = stats.reduce((n, [, p]) => n + p.seen, 0);
  const correct = stats.reduce((n, [, p]) => n + p.correct, 0);
  const states = content.items.map((i) => stateOf(progress.items[i.id]));
  const count = (s: string) => states.filter((x) => x === s).length;
  const due = content.items.filter((i) => isDue(progress.items[i.id], now));
  const review = content.items.filter((i) => needsReview(progress.items[i.id]));
  const lessonsDone = content.lessons.filter((l) => progress.lessons[l.id]?.completedAt);

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <h1>{t("progress.title")}</h1>
        <p className="lead">
          {t("progress.lead")} <Link to="/settings">{t("progress.syncLink")}</Link>
        </p>
      </header>

      <section className="card stats" aria-label={t("progress.summary")}>
        <div>
          <span className="stat-value">
            <Icon name="flame" /> {streak(progress.activity, now)}
          </span>
          <span className="stat-label">{t("progress.streak")}</span>
        </div>
        <div>
          <span className="stat-value">{percent(correct, seen)}</span>
          <span className="stat-label">{t("progress.accuracy", { n: seen })}</span>
        </div>
        <div>
          <span className="stat-value">{due.length}</span>
          <span className="stat-label">{t("progress.dueNow")}</span>
        </div>
        <div>
          <span className="stat-value">
            {lessonsDone.length}/{content.lessons.length}
          </span>
          <span className="stat-label">{t("progress.lessonsDone")}</span>
        </div>
      </section>

      {due.length > 0 && (
        <Link className="btn btn-primary btn-block" to="/chp/practice">
          {t("progress.reviewDue", { n: due.length })}
        </Link>
      )}

      <section className="stack" aria-labelledby="items-h">
        <h2 id="items-h">{t("progress.items")}</h2>
        <Meter label={t("state.mastered")} value={count("mastered")} max={content.items.length} />
        <Meter label={t("state.reviewing")} value={count("reviewing")} max={content.items.length} />
        <Meter label={t("state.learning")} value={count("learning")} max={content.items.length} />
        <Meter label={t("state.new")} value={count("new")} max={content.items.length} />
        <p className="muted small">{t("progress.stateHelp")}</p>
      </section>

      <section className="stack" aria-labelledby="review-h">
        <h2 id="review-h">{t("progress.needsReview", { n: review.length })}</h2>
        {review.length === 0 ? (
          <p className="muted">{t("progress.nothingFlagged")}</p>
        ) : (
          <ul className="review-list">
            {review.map((i) => (
              <li key={i.id}>
                <Link to={`/chp/items/${i.id}`} lang="en">
                  <strong>{i.term}</strong> — {i.answer}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="stack" aria-labelledby="lessons-h">
        <h2 id="lessons-h">{t("hub.lessons")}</h2>
        <ul className="plain-list">
          {content.lessons.map((l) => {
            const r = progress.lessons[l.id];
            return (
              <li key={l.id}>
                <Link to={`/chp/lessons/${l.id}`}>{lessonTitle(l, lang)}</Link> —{" "}
                {r?.completedAt
                  ? t("progress.lessonComplete", { best: r.bestScore, total: r.total })
                  : r
                    ? t("progress.lessonAttempted", { best: r.bestScore, total: r.total })
                    : t("hub.lessonNotStarted")}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="stack" aria-labelledby="hist-h">
        <h2 id="hist-h">{t("progress.history")}</h2>
        {progress.sessions.length === 0 ? (
          <p className="muted">{t("progress.noHistory")}</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("progress.colFinished")}</th>
                  <th scope="col">{t("progress.colMode")}</th>
                  <th scope="col">{t("progress.colScore")}</th>
                </tr>
              </thead>
              <tbody>
                {progress.sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{dateTime(s.finishedAt, lang)}</td>
                    <td>{t(`mode.${s.mode}`)}</td>
                    <td>
                      {s.correct}/{s.total} ({percent(s.correct, s.total)})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
