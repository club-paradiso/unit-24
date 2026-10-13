import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { content } from "../content";
import {
  draftProblem,
  loadReviewState,
  reviewEntries,
  saveReviewState,
  today,
  toJsonl,
  toRecord,
  type Decision,
  type Draft,
  type ReviewEntry,
  type ReviewState,
} from "../review/records";
import { useT, type T } from "../i18n";
import { useTitle } from "../state";
import { systemLabel } from "./labels";

type Filter = "all" | "undecided" | "taught" | "excluded";
const FILTERS: Filter[] = ["all", "undecided", "taught", "excluded"];
const FILE_NAME = "chp-254---aural-brevity-card---01-2021-v2.pdf";

export function ReviewPage() {
  const t = useT();
  useTitle(t("rv.title"));
  const entries = useMemo(reviewEntries, []);
  const [state, setState] = useState<ReviewState>(loadReviewState);
  const [saved, setSaved] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [message, setMessage] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    setSaved(saveReviewState(state));
  }, [state]);

  const setDraft = (factId: string, draft: Draft | null) =>
    setState((s) => {
      const drafts = { ...s.drafts };
      if (draft) drafts[factId] = draft;
      else delete drafts[factId];
      return { ...s, drafts };
    });

  const decided = entries.filter((e) => state.drafts[e.factId]);
  const problems = decided.filter((e) => draftProblem(e, state.drafts[e.factId]!));
  const shown = entries.filter((e) =>
    filter === "all" ? true : filter === "undecided" ? !state.drafts[e.factId] : filter === "taught" ? e.taught : !e.taught,
  );
  const canExport = state.reviewer.trim() !== "" && decided.length > 0 && problems.length === 0;
  const jsonl = canExport ? toJsonl(decided.map((e) => toRecord(e, state.drafts[e.factId]!, state.reviewer))) : "";

  const download = () => {
    const url = URL.createObjectURL(new Blob([jsonl], { type: "application/x-ndjson" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `chp_reviews-${state.reviewer.trim().replace(/[^A-Za-z0-9]+/g, "_")}-${today()}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage(t("rv.downloaded", { n: decided.length }));
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(jsonl);
      setMessage(t("rv.copied"));
    } catch {
      setMessage(t("rv.copyFailed"));
    }
  };

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/about">{t("nav.sources")}</Link> · {t("rv.eyebrow")}
        </p>
        <h1>{t("rv.title")}</h1>
        <p className="lead">{t("rv.lead")}</p>
      </header>

      <section className="notice notice-info stack-sm" aria-labelledby="how-h">
        <h2 id="how-h" className="notice-title">
          {t("rv.howH")}
        </h2>
        <ol className="steps">
          <li>
            {t("rv.step1")} <a href={content.source.url}>chp.ca.gov</a>
          </li>
          <li>
            {t("rv.step2")} <code>shasum -a 256 {FILE_NAME}</code> → <code className="hash">{content.source.sha256}</code> {t("rv.step2b")}
          </li>
          <li>{t("rv.step3")}</li>
          <li>
            {t("rv.step4")} <code>data/adjudication/human/chp_reviews.jsonl</code>
          </li>
        </ol>
        <p className="small">{saved ? t("rv.drafts") : t("rv.draftsFailed")}</p>
      </section>

      <section className="stack-sm" aria-labelledby="who-h">
        <h2 id="who-h">{t("rv.reviewer")}</h2>
        <label htmlFor="reviewer" className="label">
          {t("rv.nameLabel")}
        </label>
        <input id="reviewer" value={state.reviewer} maxLength={100} autoComplete="name" onChange={(e) => setState((s) => ({ ...s, reviewer: e.target.value }))} />
      </section>

      <section className="stack" aria-labelledby="entries-h">
        <h2 id="entries-h">{t("rv.entries")}</h2>
        <p role="status" className="muted">
          {t("rv.decided", { n: decided.length, total: entries.length })}
          {problems.length ? ` · ${t("rv.needAttentionCount", { n: problems.length })}` : ""}
        </p>
        <div className="chips-scroll" role="group" aria-label={t("rv.show")}>
          {FILTERS.map((f) => (
            <button key={f} type="button" className="filter-chip" aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {t(`rv.filter.${f}`)}
            </button>
          ))}
        </div>
        <ol className="review-entries">
          {shown.map((entry) => (
            <li key={entry.factId}>
              <EntryCard entry={entry} draft={state.drafts[entry.factId] ?? null} onChange={(d) => setDraft(entry.factId, d)} t={t} />
            </li>
          ))}
        </ol>
      </section>

      <section className="card stack" aria-labelledby="export-h">
        <h2 id="export-h">{t("rv.exportH")}</h2>
        {!state.reviewer.trim() && <p>{t("rv.needName")}</p>}
        {decided.length === 0 && <p>{t("rv.noDecisions")}</p>}
        {problems.length > 0 && <p>{t("rv.fixFirst", { list: problems.map((p) => p.term).join(", ") })}</p>}
        <div className="actions">
          <button type="button" className="btn btn-primary" disabled={!canExport} onClick={download}>
            {t("rv.download")}
          </button>
          <button type="button" className="btn" disabled={!canExport} onClick={copy}>
            {t("rv.copy")}
          </button>
          {confirmClear ? (
            <>
              <button
                type="button"
                className="btn btn-bad"
                onClick={() => {
                  setState((s) => ({ ...s, drafts: {} }));
                  setConfirmClear(false);
                  setMessage(t("rv.cleared"));
                }}
              >
                {t("rv.confirmClear")}
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => setConfirmClear(false)}>
                {t("common.cancel")}
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-quiet" disabled={decided.length === 0} onClick={() => setConfirmClear(true)}>
              {t("rv.clear")}
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

function EntryCard({ entry, draft, onChange, t }: { entry: ReviewEntry; draft: Draft | null; onChange: (d: Draft | null) => void; t: T }) {
  const problem = draft ? draftProblem(entry, draft) : null;
  const decisionLabel: Record<Decision, string> = { ACCEPT: t("rv.accept"), REJECT: t("rv.reject"), CORRECT: t("rv.correct") };
  const id = `rv-${entry.factId}`;
  const decisions: Decision[] = entry.taught ? ["ACCEPT", "REJECT", "CORRECT"] : ["CORRECT", "REJECT"];
  const update = (patch: Partial<Draft>) =>
    onChange({ decision: draft?.decision ?? "ACCEPT", meaning: draft?.meaning ?? "", notes: draft?.notes ?? "", decidedOn: today(), ...patch });

  return (
    <article className={`card review-card ${draft ? "is-decided" : ""} ${problem ? "has-problem" : ""}`} aria-labelledby={`${id}-h`}>
      <div className="review-head">
        <h3 id={`${id}-h`} className="review-term" lang="en">
          {entry.term}
        </h3>
        <span className="chip">{systemLabel(entry.system, t)}</span>
        <span className={`badge ${entry.taught ? "badge-ok" : "badge-muted"}`}>{entry.taught ? t("rv.taught") : t("rv.notTaught")}</span>
        <span className="muted small">{t("source.page", { page: entry.page ?? "?" })}</span>
      </div>
      {entry.shownAnswer !== null ? (
        <p>
          {t("rv.learnersSee")} <strong lang="en">{entry.shownAnswer}</strong>
        </p>
      ) : (
        <p className="muted">
          {t("rv.withheld")}{" "}
          <span className="small" lang="en">
            ({entry.reason})
          </span>
        </p>
      )}
      <figure className="excerpt">
        <blockquote lang="en">
          <p>{entry.excerpt}</p>
        </blockquote>
        <figcaption>{t("rv.rawExcerpt")}</figcaption>
      </figure>
      <fieldset className="review-decision">
        <legend>{t("rv.yourDecision", { term: entry.term })}</legend>
        {decisions.map((d) => (
          <label key={d} className="radio">
            <input type="radio" name={`${id}-decision`} checked={draft?.decision === d} onChange={() => update({ decision: d })} />
            {decisionLabel[d]}
          </label>
        ))}
      </fieldset>
      {draft?.decision === "CORRECT" && (
        <div className="stack-sm">
          <label htmlFor={`${id}-meaning`} className="label">
            {t("rv.meaningLabel")}
          </label>
          <input id={`${id}-meaning`} value={draft.meaning} onChange={(e) => update({ meaning: e.target.value })} autoComplete="off" spellCheck={false} />
        </div>
      )}
      {draft && (
        <div className="stack-sm">
          <label htmlFor={`${id}-notes`} className="label">
            {draft.decision === "ACCEPT" ? t("rv.notesOptional") : t("rv.notes")}
          </label>
          <textarea id={`${id}-notes`} rows={2} value={draft.notes} onChange={(e) => update({ notes: e.target.value })} />
        </div>
      )}
      {problem && (
        <p className="review-problem" role="alert">
          {t("rv.needsAttention")} {t(`rv.problem.${problem}`)}
        </p>
      )}
      {draft && (
        <button type="button" className="btn btn-quiet btn-small" onClick={() => onChange(null)}>
          {t("rv.undo")}
        </button>
      )}
    </article>
  );
}
