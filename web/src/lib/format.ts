import type { Lang, T } from "../i18n";
import { DAY_MS } from "./srs";

export function percent(part: number, whole: number): string {
  return whole === 0 ? "—" : `${Math.round((part / whole) * 100)}%`;
}

export function relativeDue(dueAt: number, now: number, t: T): string {
  const diff = dueAt - now;
  if (diff <= 0) return t("due.now");
  const days = Math.ceil(diff / DAY_MS);
  return days === 1 ? t("due.tomorrow") : t("due.inDays", { n: days });
}

const locale = (lang: Lang) => (lang === "ko" ? "ko-KR" : "en-US");

export function shortDate(ms: number, lang: Lang): string {
  return new Date(ms).toLocaleDateString(locale(lang), { year: "numeric", month: "short", day: "numeric" });
}

export function dateTime(ms: number, lang: Lang): string {
  return new Date(ms).toLocaleString(locale(lang), { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
