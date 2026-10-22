/** ENCOUNTER is editorial learning content, never part of the CHP radio corpus. */
export type EncounterLanguage = "ko" | "en";
export type LocalizedText = Record<EncounterLanguage, string>;
export type EncounterLevel = "B1-B2" | "B2" | "B2-C1" | "C1";
export type EncounterCategory =
  | "traffic" | "street" | "identification" | "witness" | "reporting" | "detention";
export type EncounterStage = "planned" | "playable";

export interface EncounterSource {
  /** Verified source URL for any legal or operational claim; do not infer law from radio-card data. */
  title: string;
  url: string;
  checkedAt: string;
  jurisdiction: string;
}

export interface EncounterResponse {
  id: string;
  /** The words a learner may choose or later say aloud. */
  utterance: string;
  feedback: LocalizedText;
  /** Null ends a path; otherwise it must target an existing turn. */
  nextTurnId: string | null;
}

export interface EncounterTurn {
  id: string;
  speaker: "officer" | "dispatcher" | "witness";
  utterance: string;
  translation: LocalizedText;
  responses: EncounterResponse[];
}

export interface EncounterScenario {
  id: string;
  category: EncounterCategory;
  title: LocalizedText;
  summary: LocalizedText;
  level: EncounterLevel;
  /** Advisory jurisdiction metadata, not a claim that one law applies everywhere. */
  jurisdiction: { country: "US"; state: string | null };
  learningGoals: LocalizedText[];
  stage: EncounterStage;
  legalReview: "pending" | "reviewed";
  sources: EncounterSource[];
  turns: EncounterTurn[];
}
