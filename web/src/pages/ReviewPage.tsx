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
import { useTitle } from "../state";

type Filter = "all" | "undecided" | "taught" | "excluded";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "undecided", label: "Undecided" },
  { id: "taught", label: "Taught" },
  { id: "excluded", label: "Not taught" },
];
const DECISION_LABEL: Record<Decision, string> = {
  ACCEPT: "Accept — matches the card",
  REJECT: "Reject — should not be taught",
  CORRECT: "Correct — type what the card says",
};
const FILE_NAME = "chp-254---aural-brevity-card---01-2021-v2.pdf";

export function ReviewPage() {
  useTitle("Review entries");
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
    setMessage(`Downloaded ${decided.length} decision${decided.length === 1 ? "" : "s"}.`);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(jsonl);
      setMessage("Copied to the clipboard.");
    } catch {
      setMessage("The browser did not allow copying. Use the download button instead.");
    }
  };

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/about">Sources</Link> · For reviewers
        </p>
        <h1>Review CHP entries against the card</h1>
        <p className="lead">
          Compare each entry with the CHP 254 card itself. Your decisions are what make an entry human-verified, and the only way a misread entry can be taught.
        </p>
      </header>

      <section className="notice notice-info stack-sm" aria-labelledby="how-h">
        <h2 id="how-h" className="notice-title">
          How to review
        </h2>
        <ol className="steps">
          <li>
            Download the card from <a href={content.source.url}>chp.ca.gov</a>.
          </li>
          <li>
            Check it is the exact file the content came from. <code>shasum -a 256 {FILE_NAME}</code> must print{" "}
            <code className="hash">{content.source.sha256}</code>. If it does not, stop: the card has changed and these entries need re-extraction.
          </li>
          <li>For each entry, find it on the page shown and choose Accept, Reject or Correct. Type corrections exactly as printed.</li>
          <li>
            Download your decisions and add the lines to <code>data/adjudication/human/chp_reviews.jsonl</code> in a pull request. CI checks every line; once merged,
            the site shows the entries as human-verified.
          </li>
        </ol>
        <p className="small">
          Drafts are saved in this browser only{saved ? "" : " — but saving failed here, so keep this tab open until you download"}. Nothing is sent anywhere.
        </p>
      </section>

      <section className="stack-sm" aria-labelledby="who-h">
        <h2 id="who-h">Reviewer</h2>
        <label htmlFor="reviewer" className="label">
          Your name or handle (recorded with every decision)
        </label>
        <input id="reviewer" value={state.reviewer} maxLength={100} autoComplete="name" onChange={(e) => setState((s) => ({ ...s, reviewer: e.target.value }))} />
      </section>

      <section className="stack" aria-labelledby="entries-h">
        <h2 id="entries-h">Entries</h2>
        <p role="status" className="muted">
          {decided.length} of {entries.length} decided{problems.length ? ` · ${problems.length} need attention` : ""}
        </p>
        <div className="segmented" role="group" aria-label="Show">
          {FILTERS.map((f) => (
            <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
              {f.label}
            </button>
          ))}
        </div>
        <ol className="review-entries">
          {shown.map((entry) => (
            <li key={entry.factId}>
              <EntryCard entry={entry} draft={state.drafts[entry.factId] ?? null} onChange={(d) => setDraft(entry.factId, d)} />
            </li>
          ))}
        </ol>
      </section>

      <section className="card stack" aria-labelledby="export-h">
        <h2 id="export-h">Export your decisions</h2>
        {!state.reviewer.trim() && <p>Enter your name above first.</p>}
        {decided.length === 0 && <p>No decisions yet.</p>}
        {problems.length > 0 && (
          <p>
            Fix the {problems.length} entr{problems.length === 1 ? "y" : "ies"} marked “needs attention” first: {problems.map((p) => p.term).join(", ")}.
          </p>
        )}
        <div className="actions">
          <button type="button" className="btn btn-primary" disabled={!canExport} onClick={download}>
            Download reviews (.jsonl)
          </button>
          <button type="button" className="btn" disabled={!canExport} onClick={copy}>
            Copy to clipboard
          </button>
          {confirmClear ? (
            <>
              <button
                type="button"
                className="btn btn-bad"
                onClick={() => {
                  setState((s) => ({ ...s, drafts: {} }));
                  setConfirmClear(false);
                  setMessage("All drafts cleared.");
                }}
              >
                Yes, clear all drafts
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => setConfirmClear(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-quiet" disabled={decided.length === 0} onClick={() => setConfirmClear(true)}>
              Clear drafts…
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

function EntryCard({ entry, draft, onChange }: { entry: ReviewEntry; draft: Draft | null; onChange: (d: Draft | null) => void }) {
  const problem = draft ? draftProblem(entry, draft) : null;
  const id = `rv-${entry.factId}`;
  const decisions: Decision[] = entry.taught ? ["ACCEPT", "REJECT", "CORRECT"] : ["CORRECT", "REJECT"];
  const update = (patch: Partial<Draft>) =>
    onChange({ decision: draft?.decision ?? "ACCEPT", meaning: draft?.meaning ?? "", notes: draft?.notes ?? "", decidedOn: today(), ...patch });

  return (
    <article className={`card review-card ${draft ? "is-decided" : ""} ${problem ? "has-problem" : ""}`} aria-labelledby={`${id}-h`}>
      <div className="review-head">
        <h3 id={`${id}-h`} className="review-term">
          {entry.term}
        </h3>
        <span className="chip">{entry.typeLabel}</span>
        <span className={`badge ${entry.taught ? "badge-ok" : "badge-muted"}`}>{entry.taught ? "Taught" : "Not taught"}</span>
        <span className="muted small">Page {entry.page ?? "?"}</span>
      </div>
      {entry.shownAnswer !== null ? (
        <p>
          Learners see: <strong>{entry.shownAnswer}</strong>
        </p>
      ) : (
        <p className="muted">
          The extracted meaning was wrong and is withheld. Read this entry on the card. <span className="small">Review note: {entry.reason}</span>
        </p>
      )}
      <figure className="excerpt">
        <blockquote>
          <p>{entry.excerpt}</p>
        </blockquote>
        <figcaption>Raw extraction text from this part of the card. It may run into neighbouring columns.</figcaption>
      </figure>
      <fieldset className="review-decision">
        <legend>Your decision for {entry.term}</legend>
        {decisions.map((d) => (
          <label key={d} className="radio">
            <input type="radio" name={`${id}-decision`} checked={draft?.decision === d} onChange={() => update({ decision: d })} />
            {DECISION_LABEL[d]}
          </label>
        ))}
      </fieldset>
      {draft?.decision === "CORRECT" && (
        <div className="stack-sm">
          <label htmlFor={`${id}-meaning`} className="label">
            Meaning as printed on the card
          </label>
          <input id={`${id}-meaning`} value={draft.meaning} onChange={(e) => update({ meaning: e.target.value })} autoComplete="off" spellCheck={false} />
        </div>
      )}
      {draft && (
        <div className="stack-sm">
          <label htmlFor={`${id}-notes`} className="label">
            Notes {draft.decision === "ACCEPT" ? "(optional)" : ""}
          </label>
          <textarea id={`${id}-notes`} rows={2} value={draft.notes} onChange={(e) => update({ notes: e.target.value })} />
        </div>
      )}
      {problem && (
        <p className="review-problem" role="alert">
          Needs attention: {problem}
        </p>
      )}
      {draft && (
        <button type="button" className="btn btn-quiet btn-small" onClick={() => onChange(null)}>
          Undo decision
        </button>
      )}
    </article>
  );
}
