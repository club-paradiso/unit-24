import { content, type LearningItem } from "../content";
import { useT } from "../i18n";

/** Splits the excerpt around this item's own entry so it can be highlighted among neighbouring columns. */
export function excerptParts(item: LearningItem): [string, string, string] {
  const target = `${item.term} ${item.answer}`.toLowerCase();
  const at = item.excerpt.toLowerCase().indexOf(target);
  if (at === -1) return [item.excerpt, "", ""];
  return [item.excerpt.slice(0, at), item.excerpt.slice(at, at + target.length), item.excerpt.slice(at + target.length)];
}

export function Excerpt({ item }: { item: LearningItem }) {
  const t = useT();
  const [before, match, after] = excerptParts(item);
  return (
    <figure className="excerpt">
      <blockquote lang="en">
        <p>
          {before}
          {match && <mark>{match}</mark>}
          {after}
        </p>
      </blockquote>
      <figcaption>
        {[
          t(item.status.answer_basis === "human_reading" ? "source.excerptExtraction" : "source.excerptRecorded", { page: item.page ?? "?" }),
          match ? t("source.excerptHighlighted") : "",
          t("source.excerptColumns"),
        ]
          .filter(Boolean)
          .join(" ")}
      </figcaption>
    </figure>
  );
}

export function SourceDetails({ item }: { item: LearningItem }) {
  const t = useT();
  const src = content.source;
  const decision = { ACCEPT: t("review.accepted"), REJECT: t("review.rejected"), CORRECT: t("review.corrected") } as const;
  return (
    <dl className="facts">
      <dt>{t("source.jurisdiction")}</dt>
      <dd>{src.issuing_agency}</dd>
      <dt>{t("source.document")}</dt>
      <dd>
        <span lang="en">{src.title}</span>
        <br />
        <a href={src.url} target="_blank" rel="noreferrer noopener">
          {t("source.originalPdf")}
          <span className="visually-hidden"> {t("a11y.newTab")}</span>
        </a>
      </dd>
      <dt>{t("source.version")}</dt>
      <dd>
        {src.version} <span className="muted">— {src.human_source_review?.printed_revision ? t("source.versionPrinted") : t("source.versionFilename")}</span>
      </dd>
      <dt>{t("source.location")}</dt>
      <dd>
        {t("source.page", { page: item.page ?? "?" })} ({t("source.physicalPage")})
      </dd>
      <dt>{t("source.fingerprint")}</dt>
      <dd>
        <code className="hash">sha256:{src.sha256}</code>
        <br />
        <span className="muted">
          {t("source.fingerprintNote", { bytes: src.byte_length.toLocaleString(), pages: src.page_count, date: src.retrieved_at.slice(0, 10) })}
        </span>
      </dd>
      <dt>{t("source.automatedReview")}</dt>
      <dd>
        {t("source.automatedReviewText", { date: item.review.reviewed_at })} <span lang="en">“{item.review.finding}”</span>
      </dd>
      <dt>{t("source.humanReview")}</dt>
      <dd>
        {item.review.human.length === 0 ? (
          t("source.noHumanReview")
        ) : (
          <ul className="plain-list">
            {item.review.human.map((h) => (
              <li key={`${h.reviewer}-${h.reviewed_at}`}>
                {t("source.humanDecision", { decision: decision[h.decision], who: h.reviewer, date: h.reviewed_at })}
                {h.notes ? <span className="muted"> — “{h.notes}”</span> : null}
              </li>
            ))}
          </ul>
        )}
        {item.status.human_review === "disputed" && <p className="muted">{t("source.disputedNote")}</p>}
      </dd>
      <dt>{t("source.corpusStatus")}</dt>
      <dd>
        <code>{item.status.eligibility}</code> — {t("source.researchOnly")}
      </dd>
    </dl>
  );
}
