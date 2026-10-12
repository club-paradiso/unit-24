import { Link } from "react-router";
import { content } from "../content";
import { MODE_LABEL } from "../lib/quiz";
import { isDue } from "../lib/srs";
import { useProgress, useTitle } from "../state";

export function Home() {
  useTitle("");
  const progress = useProgress();
  const now = Date.now();
  const active = progress.activeSession;
  const due = content.items.filter((i) => isDue(progress.items[i.id], now)).length;
  const seen = content.items.filter((i) => progress.items[i.id]).length;
  const lessonsDone = content.lessons.filter((l) => progress.lessons[l.id]?.completedAt).length;

  return (
    <div className="stack-lg">
      <section className="hero">
        <h1>Learn public-safety radio language — with the source for every answer.</h1>
        <p className="lead">
          Study radio codes and spelling alphabets one agency at a time. Every entry shows where it came from and how far it has been checked, so you know
          what you are learning.
        </p>
      </section>

      {active && (
        <section className="card card-accent" aria-labelledby="resume-h">
          <h2 id="resume-h">Continue where you left off</h2>
          <p>
            {MODE_LABEL[active.mode]} — {active.answers.length} of {active.questions.length} questions answered.
          </p>
          <Link className="btn btn-primary" to="/chp/practice/session">
            Resume session
          </Link>
        </section>
      )}

      <section aria-labelledby="pick-h" className="stack">
        <h2 id="pick-h">Choose a jurisdiction</h2>
        <ul className="jurisdictions">
          <li>
            <Link to="/chp" className="card card-link jurisdiction">
              <span className="jurisdiction-tag">Available</span>
              <span className="jurisdiction-name">{content.jurisdiction.name}</span>
              <span className="muted">{content.jurisdiction.region}</span>
              <span>
                {content.counts.teachable_codes} radio codes · {content.counts.teachable_letters}-letter card alphabet · {content.lessons.length} lessons
              </span>
              {seen > 0 && (
                <span className="muted">
                  You have studied {seen} of {content.counts.teachable} items · {lessonsDone} of {content.lessons.length} lessons complete
                  {due > 0 ? ` · ${due} due for review` : ""}
                </span>
              )}
            </Link>
          </li>
          <li className="card jurisdiction is-unavailable" aria-disabled="true">
            <span className="jurisdiction-tag muted-tag">Not yet available</span>
            <span className="jurisdiction-name">Other agencies</span>
            <span className="muted">
              The research corpus has no reviewed learning content for other agencies yet. Codes differ between agencies, so they are not borrowed from
              CHP.
            </span>
          </li>
        </ul>
      </section>
    </div>
  );
}
