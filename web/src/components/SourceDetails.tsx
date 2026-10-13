import { content, type LearningItem } from "../content";

/** Splits the excerpt around this item's own entry so it can be highlighted among neighbouring columns. */
export function excerptParts(item: LearningItem): [string, string, string] {
  const target = `${item.term} ${item.answer}`.toLowerCase();
  const at = item.excerpt.toLowerCase().indexOf(target);
  if (at === -1) return [item.excerpt, "", ""];
  return [item.excerpt.slice(0, at), item.excerpt.slice(at, at + target.length), item.excerpt.slice(at + target.length)];
}

export function Excerpt({ item }: { item: LearningItem }) {
  const [before, match, after] = excerptParts(item);
  return (
    <figure className="excerpt">
      <blockquote>
        <p>
          {before}
          {match && <mark>{match}</mark>}
          {after}
        </p>
      </blockquote>
      <figcaption>
        {item.status.answer_basis === "human_reading" ? "Extraction text" : "Text recorded"} from page {item.page ?? "?"} of the card
        {match ? "; this entry is highlighted" : ""}. Neighbouring columns of the card appear in the
        same line of text.
      </figcaption>
    </figure>
  );
}

const HUMAN_DECISION = { ACCEPT: "Accepted", REJECT: "Rejected", CORRECT: "Corrected" } as const;

export function SourceDetails({ item }: { item: LearningItem }) {
  const src = content.source;
  return (
    <dl className="facts">
      <dt>Jurisdiction</dt>
      <dd>
        {src.issuing_agency} — {src.jurisdiction}
      </dd>
      <dt>Source document</dt>
      <dd>
        {src.title}
        <br />
        <a href={src.url} target="_blank" rel="noreferrer noopener">
          Original PDF on chp.ca.gov<span className="visually-hidden"> (opens in a new tab)</span>
        </a>
      </dd>
      <dt>Version</dt>
      <dd>
        {src.version} <span className="muted">— {src.version_basis}</span>
      </dd>
      <dt>Location in document</dt>
      <dd>
        Page {item.page ?? "?"} ({item.locator_kind})
      </dd>
      <dt>Document fingerprint</dt>
      <dd>
        <code className="hash">sha256:{src.sha256}</code>
        <br />
        <span className="muted">
          {src.byte_length.toLocaleString()} bytes, {src.page_count} pages, retrieved {src.retrieved_at.slice(0, 10)}. {src.document_note}
        </span>
      </dd>
      <dt>Automated review</dt>
      <dd>
        {item.review.reviewer_is_human ? "Human review" : "Automated (AI agent) review"} on {item.review.reviewed_at}: “{item.review.finding}”
      </dd>
      <dt>Human review</dt>
      <dd>
        {item.review.human.length === 0 ? (
          "None yet — no human reviewer has checked this entry against the card."
        ) : (
          <ul className="plain-list">
            {item.review.human.map((h) => (
              <li key={`${h.reviewer}-${h.reviewed_at}`}>
                {HUMAN_DECISION[h.decision]} by {h.reviewer} on {h.reviewed_at}
                {h.notes ? <span className="muted"> — “{h.notes}”</span> : null}
              </li>
            ))}
          </ul>
        )}
        {item.status.human_review === "disputed" && <p className="muted">Reviewers disagree, so this entry is not marked human-verified.</p>}
      </dd>
      <dt>Currentness</dt>
      <dd>{item.limitations[1]}</dd>
      <dt>Corpus status</dt>
      <dd>
        <code>{item.status.eligibility}</code> — the research corpus has not approved this as a training answer.
      </dd>
    </dl>
  );
}
