import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router";
import { content, getItem } from "../content";
import { Meter } from "../components/Status";
import { dateTime, percent } from "../lib/format";
import { MODE_LABEL } from "../lib/quiz";
import { isDue, needsReview, stateOf } from "../lib/srs";
import { useProgress, useStore, useTitle } from "../state";

export function ProgressPage() {
  useTitle("Your progress");
  const progress = useProgress();
  const store = useStore();
  const [message, setMessage] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const now = Date.now();

  const stats = Object.entries(progress.items).filter(([id]) => getItem(id));
  const seen = stats.reduce((n, [, p]) => n + p.seen, 0);
  const correct = stats.reduce((n, [, p]) => n + p.correct, 0);
  const states = content.items.map((i) => stateOf(progress.items[i.id]));
  const count = (s: string) => states.filter((x) => x === s).length;
  const due = content.items.filter((i) => isDue(progress.items[i.id], now));
  const review = content.items.filter((i) => needsReview(progress.items[i.id]));
  const lessonsDone = content.lessons.filter((l) => progress.lessons[l.id]?.completedAt);

  const download = () => {
    const blob = new Blob([store.exportJson()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `unit24-progress-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage("Progress file downloaded.");
  };

  const upload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      store.importJson(await file.text());
      setMessage("Progress restored from file.");
    } catch (err) {
      setMessage(`Could not restore: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <h1>Your progress</h1>
        <p className="lead">Saved in this browser only. Use “Download progress” to keep a copy or move it to another device.</p>
      </header>

      <section className="card stats" aria-label="Summary">
        <div>
          <span className="stat-value">{percent(correct, seen)}</span>
          <span className="stat-label">accuracy ({seen} answers)</span>
        </div>
        <div>
          <span className="stat-value">{count("mastered")}</span>
          <span className="stat-label">mastered</span>
        </div>
        <div>
          <span className="stat-value">{due.length}</span>
          <span className="stat-label">due now</span>
        </div>
        <div>
          <span className="stat-value">
            {lessonsDone.length}/{content.lessons.length}
          </span>
          <span className="stat-label">lessons complete</span>
        </div>
      </section>

      <section className="stack" aria-labelledby="items-h">
        <h2 id="items-h">Items</h2>
        <Meter label="Mastered" value={count("mastered")} max={content.items.length} />
        <Meter label="Reviewing" value={count("reviewing")} max={content.items.length} />
        <Meter label="Learning" value={count("learning")} max={content.items.length} />
        <Meter label="Not started" value={count("new")} max={content.items.length} />
        {due.length > 0 && (
          <Link className="btn btn-primary" to="/chp/practice">
            Review {due.length} due item{due.length === 1 ? "" : "s"}
          </Link>
        )}
      </section>

      <section className="stack" aria-labelledby="review-h">
        <h2 id="review-h">Needs review ({review.length})</h2>
        {review.length === 0 ? (
          <p className="muted">Nothing flagged. Items you get wrong appear here.</p>
        ) : (
          <ul className="review-list">
            {review.map((i) => (
              <li key={i.id}>
                <Link to={`/chp/items/${i.id}`}>
                  <strong>{i.term}</strong> — {i.answer}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="stack" aria-labelledby="lessons-h">
        <h2 id="lessons-h">Lessons</h2>
        <ul className="plain-list">
          {content.lessons.map((l) => {
            const r = progress.lessons[l.id];
            return (
              <li key={l.id}>
                <Link to={`/chp/lessons/${l.id}`}>{l.title}</Link> —{" "}
                {r?.completedAt ? `complete (best ${r.bestScore}/${r.total})` : r ? `attempted, best ${r.bestScore}/${r.total}` : "not started"}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="stack" aria-labelledby="hist-h">
        <h2 id="hist-h">Recent sessions</h2>
        {progress.sessions.length === 0 ? (
          <p className="muted">No finished practice sessions yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Finished</th>
                  <th scope="col">Mode</th>
                  <th scope="col">Score</th>
                </tr>
              </thead>
              <tbody>
                {progress.sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{dateTime(s.finishedAt)}</td>
                    <td>{MODE_LABEL[s.mode] ?? s.mode}</td>
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

      <section className="stack" aria-labelledby="data-h">
        <h2 id="data-h">Your data</h2>
        <div className="actions">
          <button type="button" className="btn" onClick={download}>
            Download progress
          </button>
          <button type="button" className="btn" onClick={() => fileRef.current?.click()}>
            Restore from file
          </button>
          <input ref={fileRef} type="file" accept="application/json,.json" onChange={upload} hidden aria-hidden="true" tabIndex={-1} />
          {confirmReset ? (
            <>
              <button
                type="button"
                className="btn btn-bad"
                onClick={() => {
                  store.reset();
                  setConfirmReset(false);
                  setMessage("All progress was erased.");
                }}
              >
                Yes, erase everything
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => setConfirmReset(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-quiet" onClick={() => setConfirmReset(true)}>
              Reset progress…
            </button>
          )}
        </div>
        <p role="status" className="muted">
          {message}
        </p>
      </section>
    </div>
  );
}
