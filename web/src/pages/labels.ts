import type { T } from "../i18n";

export function systemLabel(system: string | null, t: T): string {
  if (system === "TEN_CODE") return t("system.ten");
  if (system === "ELEVEN_CODE") return t("system.eleven");
  if (system === "CHP_CARD_ALPHABET") return t("system.alphabet");
  return t("system.other");
}

const LABELS = ["FALSE_POSITIVE", "INSUFFICIENT_CONTEXT", "HUMAN_REJECTED"] as const;

export function exclusionLabel(label: string, t: T): string {
  if (!(LABELS as readonly string[]).includes(label)) return label;
  return t(`exclusion.${label as (typeof LABELS)[number]}`);
}
