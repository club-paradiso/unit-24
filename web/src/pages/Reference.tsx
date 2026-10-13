import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { content } from "../content";
import { LearnState } from "../components/Status";
import { useT } from "../i18n";
import { useProgress, useTitle } from "../state";
import { exclusionLabel, systemLabel } from "./labels";

type Filter = "all" | "TEN_CODE" | "ELEVEN_CODE" | "CHP_CARD_ALPHABET";
const FILTERS: Filter[] = ["all", "TEN_CODE", "ELEVEN_CODE", "CHP_CARD_ALPHABET"];

export function Reference() {
  const t = useT();
  useTitle(t("ref.title"));
  const progress = useProgress();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const filter = (FILTERS.find((f) => f === params.get("type")) ?? "all") as Filter;
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
        <h1>{t("ref.title")}</h1>
        <p className="lead">{t("ref.lead")}</p>
      </header>

      <div role="search" className="search-bar stack-sm">
        <label htmlFor="ref-q" className="visually-hidden">
          {t("ref.searchLabel")}
        </label>
        <input
          id="ref-q"
          type="search"
          value={query}
          onChange={(e) => update(e.target.value, filter)}
          placeholder={t("ref.placeholder")}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          enterKeyHint="search"
        />
        <div className="chips-scroll" role="group" aria-label={t("ref.filter")}>
          {FILTERS.map((f) => (
            <button key={f} type="button" className="filter-chip" aria-pressed={filter === f} onClick={() => update(query, f)}>
              {f === "all" ? t("ref.all") : systemLabel(f, t)}
            </button>
          ))}
        </div>
      </div>

      <p className="muted" role="status">
        {t("ref.count", { n: results.length })}
      </p>
      {results.length > 0 ? (
        <ul className="ref-list">
          {results.map((item) => (
            <li key={item.id}>
              <Link to={`/chp/items/${item.id}`} className="ref-row">
                <span className="ref-term" lang="en">
                  {item.term}
                </span>
                <span className="ref-answer" lang="en">
                  {item.answer}
                </span>
                <span className="ref-meta">
                  <span className="muted small">{systemLabel(item.code_system, t)}</span>
                  <LearnState progress={progress.items[item.id]} />
                  {item.status.human_verified && <span className="badge badge-ok">✓ {t("trust.humanVerifiedShort")}</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="card">{t("ref.noMatch", { q: query })}</p>
      )}

      <section className="stack" aria-labelledby="excluded-h">
        <h2 id="excluded-h">{t("ref.excludedTitle", { n: content.excluded.length })}</h2>
        <p>{t("ref.excludedText")}</p>
        <button type="button" className="btn" aria-expanded={showExcluded} aria-controls="excluded-list" onClick={() => setShowExcluded((v) => !v)}>
          {showExcluded ? t("ref.hideExcluded") : t("ref.showExcluded", { n: content.excluded.length })}
        </button>
        {showExcluded && (
          <ul id="excluded-list" className="excluded-list">
            {content.excluded.map((e) => (
              <li key={e.fact_id}>
                <strong lang="en">{e.term === "APCO_1941" ? t("ref.apcoLabel") : e.term}</strong>
                <span className="badge badge-muted">{exclusionLabel(e.label, t)}</span>
                <span className="muted small" lang="en">
                  {e.reason}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
