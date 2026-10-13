import { Link } from "react-router";
import { content } from "../content";
import { Meter } from "../components/Status";
import { PASS_RATIO } from "../lib/progress";
import { isDue, stateOf } from "../lib/srs";
import { useProgress, useTitle } from "../state";

export function Hub() {
  useTitle("California Highway Patrol");
  const progress = useProgress();
  const now = Date.now();
  const due = content.items.filter((i) => isDue(progress.items[i.id], now)).length;
  const mastered = content.items.filter((i) => stateOf(progress.items[i.id]) === "mastered").length;
  const src = content.source;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">{content.jurisdiction.region}</p>
        <h1>{content.jurisdiction.name}</h1>
        <p className="lead">
          Radio codes and the spelling alphabet printed on the <strong>{src.title}</strong> ({src.version}).
        </p>
      </header>

      <aside className="notice notice-info" aria-labelledby="trust-h">
        <h2 id="trust-h" className="notice-title">
          How far this content has been checked
        </h2>
        <ul>
          <li>
            Entries were matched word-for-word to the card by an automated review.{" "}
            {content.counts.human_verified === 0 ? (
              <strong>No human has verified them yet.</strong>
            ) : (
              <strong>
                {content.counts.human_verified} of {content.counts.teachable} have been verified against the card by a human reviewer.
              </strong>
            )}
          </li>
          <li>The card has no confirmed revision date, so whether CHP still uses it is unknown.</li>
          <li>
            {content.counts.excluded} other entries are left out: the extractor misread them{content.counts.human_rejected ? " or a reviewer rejected them" : ""}, and they
            are taught only once a person reads them from the card.{" "}
            <Link to="/about">Details</Link>
          </li>
        </ul>
      </aside>

      <section className="stack" aria-labelledby="overview-h">
        <h2 id="overview-h" className="visually-hidden">
          Your progress
        </h2>
        <div className="grid-2">
          <Meter label="Mastered items" value={mastered} max={content.counts.teachable} />
          <Meter label="Lessons complete" value={content.lessons.filter((l) => progress.lessons[l.id]?.completedAt).length} max={content.lessons.length} />
        </div>
        <div className="actions">
          <Link className="btn btn-primary" to="/chp/practice">
            Practice{due > 0 ? ` (${due} due)` : ""}
          </Link>
          <Link className="btn" to="/chp/flashcards">
            Flashcards
          </Link>
          <Link className="btn" to="/chp/reference">
            Look up a code
          </Link>
        </div>
      </section>

      <section className="stack" aria-labelledby="lessons-h">
        <h2 id="lessons-h">Lessons</h2>
        <ol className="lesson-list">
          {content.lessons.map((lesson, n) => {
            const r = progress.lessons[lesson.id];
            const status = r?.completedAt ? "Complete" : r ? `Best ${r.bestScore}/${r.total} — pass is ${Math.ceil(PASS_RATIO * r.total)}` : "Not started";
            return (
              <li key={lesson.id}>
                <Link to={`/chp/lessons/${lesson.id}`} className="card card-link lesson-row">
                  <span className={`lesson-num ${r?.completedAt ? "is-done" : ""}`} aria-hidden="true">
                    {r?.completedAt ? "✓" : n + 1}
                  </span>
                  <span className="lesson-body">
                    <span className="lesson-title">{lesson.title}</span>
                    <span className="muted">
                      {lesson.item_ids.length} items · {lesson.summary}
                    </span>
                  </span>
                  <span className={`lesson-status ${r?.completedAt ? "is-done" : ""}`}>{status}</span>
                </Link>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
