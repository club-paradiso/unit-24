import { DAY_MS } from "./srs";

export function percent(part: number, whole: number): string {
  return whole === 0 ? "—" : `${Math.round((part / whole) * 100)}%`;
}

export function relativeDue(dueAt: number, now: number): string {
  const diff = dueAt - now;
  if (diff <= 0) return "due now";
  const days = Math.ceil(diff / DAY_MS);
  return days === 1 ? "due tomorrow" : `due in ${days} days`;
}

export function shortDate(ms: number): string {
  return new Date(ms).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function dateTime(ms: number): string {
  return new Date(ms).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

/** Plain-language versions of the corpus status vocabulary. */
export const LABEL_TEXT: Record<string, string> = {
  FALSE_POSITIVE: "Extracted meaning was wrong",
  INSUFFICIENT_CONTEXT: "Extracted meaning was incomplete",
  WRONG_NORMALIZATION: "Meaning matched; label was wrong",
  TRUE_FACT: "Meaning matched",
  HUMAN_REJECTED: "Rejected by a human reviewer",
};

export const FAILURE_TEXT: Record<string, string> = {
  LAYOUT_COLUMN_BLEED: "text from a neighbouring column ran into it",
  LAYOUT_CONTINUATION_LOST: "the rest of the entry, on the next line, was lost",
  UNCLASSIFIED: "the entry is not what the extractor took it for",
  NOT_A_FAILURE: "",
  HUMAN_REVIEW: "",
};
