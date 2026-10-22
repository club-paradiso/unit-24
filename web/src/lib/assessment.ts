/** Contract shared by assessment UI and tests. No raw audio or assessment result is persisted. */
export type AssessmentScores = {
  overall: number | null;
  accuracy: number | null;
  fluency: number | null;
  completeness: number | null;
  prosody: number | null;
};
export type AssessmentPhoneme = { sound: string; accuracy: number | null };
export type AssessmentWord = {
  text: string;
  accuracy: number | null;
  errorType: string | null;
  phonemes: AssessmentPhoneme[];
};
export type AssessmentResult = {
  provider: "azure-pronunciation-assessment";
  referenceText: string;
  recognizedText: string;
  scores: AssessmentScores;
  words: AssessmentWord[];
};

const score = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
const object = (v: unknown): Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : {};

/** REST short-audio results put scores directly on NBest[0] and each word. */
export function normalizeAzureAssessment(payload: unknown, referenceText: string): AssessmentResult {
  const root = object(payload);
  if (root.RecognitionStatus !== "Success") throw new Error("SPEECH_NOT_RECOGNIZED");
  const best = Array.isArray(root.NBest) ? object(root.NBest[0]) : {};
  if (best.AccuracyScore === undefined || best.PronScore === undefined) {
    throw new Error("ASSESSMENT_NOT_AVAILABLE");
  }
  const words = Array.isArray(best.Words) ? best.Words.slice(0, 50).map((raw): AssessmentWord => {
    const word = object(raw);
    return {
      text: typeof word.Word === "string" ? word.Word.slice(0, 80) : "",
      accuracy: score(word.AccuracyScore),
      errorType: typeof word.ErrorType === "string" ? word.ErrorType.slice(0, 48) : null,
      phonemes: Array.isArray(word.Phonemes) ? word.Phonemes.slice(0, 24).map((p): AssessmentPhoneme => {
        const phoneme = object(p);
        return { sound: typeof phoneme.Phoneme === "string" ? phoneme.Phoneme.slice(0, 24) : "", accuracy: score(phoneme.AccuracyScore) };
      }) : [],
    };
  }).filter(word => word.text.length > 0) : [];
  return {
    provider: "azure-pronunciation-assessment",
    referenceText,
    recognizedText: typeof root.DisplayText === "string"
      ? root.DisplayText.slice(0, 320) : typeof best.Display === "string" ? best.Display.slice(0, 320) : "",
    scores: {
      overall: score(best.PronScore),
      accuracy: score(best.AccuracyScore),
      fluency: score(best.FluencyScore),
      completeness: score(best.CompletenessScore),
      prosody: score(best.ProsodyScore),
    },
    words,
  };
}

export function isAssessmentResult(input: unknown): input is AssessmentResult {
  const value = object(input);
  const scores = object(value.scores);
  return value.provider === "azure-pronunciation-assessment"
    && typeof value.referenceText === "string"
    && typeof value.recognizedText === "string"
    && (scores.overall === null || score(scores.overall) !== null)
    && (scores.accuracy === null || score(scores.accuracy) !== null)
    && Array.isArray(value.words);
}
