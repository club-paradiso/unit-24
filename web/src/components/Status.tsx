import type { LearningItem } from "../content";
import { STATE_LABEL, stateOf, type ItemProgress } from "../lib/srs";

/** The verification status of an item, always shown in words (never colour alone). */
export function TrustBadges({ item, compact = false }: { item: LearningItem; compact?: boolean }) {
  const { status } = item;
  const latest = item.review.human[item.review.human.length - 1];
  return (
    <ul className="badges" aria-label="Verification status">
      {status.answer_basis === "human_reading" ? (
        <li className="badge badge-ok" title="The extractor misread this entry; a person read the meaning from the card">
          <span aria-hidden="true">✓</span> Read from the card by a person
        </li>
      ) : (
        <li className="badge badge-ok" title="An automated review matched this to the source document">
          <span aria-hidden="true">✓</span> Source-matched
        </li>
      )}
      {status.human_verified ? (
        <li className="badge badge-ok" title={latest ? `Verified by ${latest.reviewer} on ${latest.reviewed_at}` : "Verified by a human reviewer"}>
          <span aria-hidden="true">✓</span> Human-verified
        </li>
      ) : status.human_review === "disputed" ? (
        <li className="badge badge-warn" title="Human reviewers disagree about this entry">
          <span aria-hidden="true">!</span> Reviewers disagree
        </li>
      ) : (
        <li className="badge badge-warn" title="No human reviewer has verified this entry">
          <span aria-hidden="true">!</span> {compact ? "Unverified" : "Not human-verified"}
        </li>
      )}
      {status.currentness === "UNKNOWN" ? (
        <li className="badge badge-muted" title="It is unknown whether this card is still in use">
          <span aria-hidden="true">?</span> {compact ? "Currentness unknown" : "Current use unknown"}
        </li>
      ) : (
        <li className="badge badge-muted" title="CHP was seen listing this card; that does not prove operational use">
          <span aria-hidden="true">i</span> Listed by CHP
        </li>
      )}
    </ul>
  );
}

export function LearnState({ progress }: { progress: ItemProgress | undefined }) {
  const state = stateOf(progress);
  return <span className={`state state-${state}`}>{STATE_LABEL[state]}</span>;
}

export function Meter({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max === 0 ? 0 : Math.round((value / max) * 100);
  return (
    <div className="meter">
      <div className="meter-label">
        <span>{label}</span>
        <span>
          {value} / {max}
        </span>
      </div>
      <div className="meter-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <div className="meter-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
