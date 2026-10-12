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
        Text recorded from page {item.page ?? "?"} of the card{match ? "; this entry is highlighted" : ""}. Neighbouring columns of the card appear in the
        same line of text.
      </figcaption>
    </figure>
  );
}

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
      <dt>Review</dt>
      <dd>
        {item.review.reviewer_is_human ? "Human review" : "Automated (AI agent) review"} on {item.review.reviewed_at}: “{item.review.finding}”
      </dd>
      <dt>Human verified</dt>
      <dd>{item.status.human_verified ? "Yes" : "No — no human reviewer has accepted this entry yet."}</dd>
      <dt>Currentness</dt>
      <dd>{item.status.currentness === "UNKNOWN" ? "Unknown — the card has no confirmed revision or effective date." : item.status.currentness}</dd>
      <dt>Corpus status</dt>
      <dd>
        <code>{item.status.eligibility}</code> — the research corpus has not approved this as a training answer.
      </dd>
    </dl>
  );
}
