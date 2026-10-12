import { Link, useParams } from "react-router";
import { content, getItem, SYSTEM_LABEL } from "../content";
import { Excerpt, SourceDetails } from "../components/SourceDetails";
import { LearnState, TrustBadges } from "../components/Status";
import { percent, relativeDue, shortDate } from "../lib/format";
import { useProgress, useTitle } from "../state";
import { NotFound } from "./NotFound";

export function ItemDetail() {
  const { itemId = "" } = useParams();
  const item = getItem(itemId);
  const progress = useProgress();
  useTitle(item ? `${item.term} — ${item.answer}` : "Not found");
  if (!item) return <NotFound what="entry" />;
  const p = progress.items[item.id];
  const idx = content.items.indexOf(item);
  const prev = content.items[idx - 1];
  const next = content.items[idx + 1];
  const lesson = content.lessons.find((l) => l.item_ids.includes(item.id));

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp/reference">Reference</Link> · {SYSTEM_LABEL[item.code_system]}
        </p>
        <h1 className="item-heading">
          <span className="study-term">{item.term}</span>
          <span className="study-answer">{item.answer}</span>
        </h1>
        <TrustBadges item={item} />
      </header>

      <section className="stack" aria-labelledby="src-h">
        <h2 id="src-h">Source and verification</h2>
        <Excerpt item={item} />
        <SourceDetails item={item} />
      </section>

      <section className="stack" aria-labelledby="lim-h">
        <h2 id="lim-h">Limitations</h2>
        <ul>
          {item.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
          {item.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>

      <section className="stack" aria-labelledby="mine-h">
        <h2 id="mine-h">Your progress</h2>
        {p ? (
          <p>
            <LearnState progress={p} /> · answered {p.seen} time{p.seen === 1 ? "" : "s"}, {percent(p.correct, p.seen)} correct · last seen {shortDate(p.lastSeenAt)} ·{" "}
            {relativeDue(p.dueAt, Date.now())}
          </p>
        ) : (
          <p>
            Not studied yet.
            {lesson && (
              <>
                {" "}
                It is in the lesson <Link to={`/chp/lessons/${lesson.id}`}>{lesson.title}</Link>.
              </>
            )}
          </p>
        )}
      </section>

      <nav className="pager" aria-label="Neighbouring entries">
        {prev ? (
          <Link to={`/chp/items/${prev.id}`} rel="prev">
            ← {prev.term}
          </Link>
        ) : (
          <span />
        )}
        {next && (
          <Link to={`/chp/items/${next.id}`} rel="next">
            {next.term} →
          </Link>
        )}
      </nav>
    </div>
  );
}
