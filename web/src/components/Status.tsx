import type { LearningItem } from "../content";
import { useT } from "../i18n";
import { stateOf, type ItemProgress } from "../lib/srs";

/** The verification status of an item, always shown in words (never colour alone). */
export function TrustBadges({ item, compact = false }: { item: LearningItem; compact?: boolean }) {
  const t = useT();
  const { status } = item;
  const latest = item.review.human[item.review.human.length - 1];
  return (
    <ul className="badges" aria-label={t("trust.label")}>
      {status.answer_basis === "human_reading" ? (
        <li className="badge badge-ok" title={t("trust.humanReadingTitle")}>
          <span aria-hidden="true">✓</span> {t("trust.humanReading")}
        </li>
      ) : (
        <li className="badge badge-ok" title={t("trust.sourceMatchedTitle")}>
          <span aria-hidden="true">✓</span> {t("trust.sourceMatched")}
        </li>
      )}
      {status.human_verified ? (
        <li className="badge badge-ok" title={latest ? t("trust.verifiedBy", { who: latest.reviewer, date: latest.reviewed_at }) : undefined}>
          <span aria-hidden="true">✓</span> {t("trust.humanVerified")}
        </li>
      ) : status.human_review === "disputed" ? (
        <li className="badge badge-warn" title={t("trust.disputedTitle")}>
          <span aria-hidden="true">!</span> {t("trust.disputed")}
        </li>
      ) : (
        <li className="badge badge-warn" title={t("trust.notVerifiedTitle")}>
          <span aria-hidden="true">!</span> {compact ? t("trust.notVerifiedShort") : t("trust.notVerified")}
        </li>
      )}
      {status.currentness === "UNKNOWN" ? (
        <li className="badge badge-muted" title={t("trust.currentUnknownTitle")}>
          <span aria-hidden="true">?</span> {t("trust.currentUnknown")}
        </li>
      ) : (
        <li className="badge badge-muted" title={t("trust.listedTitle")}>
          <span aria-hidden="true">i</span> {t("trust.listed")}
        </li>
      )}
    </ul>
  );
}

/** Plain-language limitations, built from the item's structured status (not from English prose). */
export function useLimitations(item: LearningItem): string[] {
  const t = useT();
  const humans = item.review.human.map((h) => `${h.reviewer} (${h.reviewed_at})`).join(", ");
  const out: string[] = [];
  if (item.status.human_review === "disputed") out.push(t("limit.disputed", { who: humans }));
  else if (item.status.human_review === "corrected") out.push(t("limit.corrected", { who: humans }));
  else if (item.status.human_verified) out.push(t("limit.accepted", { who: humans }));
  else out.push(t("limit.notVerified"));
  out.push(item.status.currentness === "UNKNOWN" ? t("limit.currentUnknown") : t("limit.listed"));
  out.push(t("limit.agencyOnly"));
  out.push(item.kind === "letter" ? t("limit.cardAlphabet") : t("limit.meaningOnly"));
  return out;
}

export function LearnState({ progress }: { progress: ItemProgress | undefined }) {
  const t = useT();
  const state = stateOf(progress);
  return <span className={`state state-${state}`}>{t(`state.${state}`)}</span>;
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
