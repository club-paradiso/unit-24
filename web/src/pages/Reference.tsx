import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { content, SYSTEM_LABEL } from "../content";
import { LearnState } from "../components/Status";
import { FAILURE_TEXT, LABEL_TEXT } from "../lib/format";
import { useProgress, useTitle } from "../state";

type Filter = "all" | "TEN_CODE" | "ELEVEN_CODE" | "CHP_CARD_ALPHABET";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "TEN_CODE", label: "10-codes" },
  { id: "ELEVEN_CODE", label: "11-codes" },
  { id: "CHP_CARD_ALPHABET", label: "Alphabet" },
];

export function Reference() {
  useTitle("Reference");
  const progress = useProgress();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const filter = (FILTERS.find((f) => f.id === params.get("type"))?.id ?? "all") as Filter;
  const [showExcluded, setShowExcluded] = useState(false);

  const update = (q: string, type: Filter) => {
    const next = new URLSearchParams();
    if (q) next.set("q", q);
    if (type !== "all") next.set("type", type);
    setParams(next, { replace: true });
  };

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return content.items.filter(
      (i) => (filter === "all" || i.code_system === filter) && (!q || i.term.toLowerCase().includes(q) || i.answer.toLowerCase().includes(q)),
    );
  }, [query, filter]);

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp">CHP</Link>
        </p>
        <h1>Reference</h1>
        <p className="lead">Every teachable entry from the CHP 254 card. Select an entry for its source and verification details.</p>
      </header>

      <div role="search" className="stack">
        <label htmlFor="ref-q" className="label">
          Search codes, meanings or letters
        </label>
        <input id="ref-q" type="search" value={query} onChange={(e) => update(e.target.value, filter)} placeholder="e.g. 10-20, crash, Yellow" autoComplete="off" />
        <div className="segmented" role="group" aria-label="Filter by type">
          {FILTERS.map((f) => (
            <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => update(query, f.id)}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <p className="muted" role="status">
        {results.length} {results.length === 1 ? "entry" : "entries"}
      </p>
      {results.length > 0 ? (
        <ul className="ref-list">
          {results.map((item) => (
            <li key={item.id}>
              <Link to={`/chp/items/${item.id}`} className="ref-row">
                <span className="ref-term">{item.term}</span>
                <span className="ref-answer">{item.answer}</span>
                <span className="ref-meta">
                  <span className="muted small">{SYSTEM_LABEL[item.code_system]}</span>
                  <LearnState progress={progress.items[item.id]} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="card">
          Nothing matches “{query}”. The code may be one of the entries that are not taught yet (below), or it is not on this card.
        </p>
      )}

      <section className="stack" aria-labelledby="excluded-h">
        <h2 id="excluded-h">Not yet teachable ({content.excluded.length})</h2>
        <p>
          These entries are on the card but were extracted incorrectly, so the meaning the extractor produced is not shown. They will be added once the
          meaning is re-read from the card and checked.
        </p>
        <button type="button" className="btn" aria-expanded={showExcluded} aria-controls="excluded-list" onClick={() => setShowExcluded((v) => !v)}>
          {showExcluded ? "Hide" : "Show"} the {content.excluded.length} entries
        </button>
        {showExcluded && (
          <ul id="excluded-list" className="excluded-list">
            {content.excluded.map((e) => (
              <li key={e.fact_id}>
                <strong>{e.term === "APCO_1941" ? "Alphabet label “APCO 1941”" : e.term}</strong>
                <span className="badge badge-muted">{LABEL_TEXT[e.label] ?? e.label}</span>
                <span className="muted small">
                  {e.reason}
                  {FAILURE_TEXT[e.failure_class] ? ` — ${FAILURE_TEXT[e.failure_class]}.` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
