import { describe, expect, it } from "vitest";
import { isAssessmentResult, normalizeAzureAssessment } from "./assessment";

describe("Azure assessment result normalization", () => {
  const example = {
    RecognitionStatus: "Success", DisplayText: "Ten four.",
    NBest: [{
      PronScore: 87.5, AccuracyScore: 90, FluencyScore: 83.2,
      CompletenessScore: 100, ProsodyScore: 76,
      Words: [{ Word: "ten", AccuracyScore: 96, ErrorType: "None",
        Phonemes: [{ Phoneme: "t", AccuracyScore: 99 }, { Phoneme: "eh", AccuracyScore: 93 }] },
        { Word: "four", AccuracyScore: 85, ErrorType: "Mispronunciation" }],
    }],
  };
  it("parses full text, word and phoneme scores", () => {
    const r = normalizeAzureAssessment(example, "ten four");
    expect(r.scores.overall).toBe(87.5);
    expect(r.scores.fluency).toBe(83.2);
    expect(r.words[0]?.phonemes[0]).toEqual({ sound: "t", accuracy: 99 });
    expect(r.words[1]?.errorType).toBe("Mispronunciation");
    expect(isAssessmentResult(r)).toBe(true);
  });
  it("retains genuinely unavailable prosody rather than fabricating a value", () => {
    const r = normalizeAzureAssessment({
      ...example, NBest: [{ ...example.NBest[0], ProsodyScore: undefined }],
    }, "ten four");
    expect(r.scores.prosody).toBeNull();
  });
  it("never replaces missing provider scores with invented marks", () => {
    expect(() => normalizeAzureAssessment({ RecognitionStatus: "Success", NBest: [{}] }, "test"))
      .toThrow("ASSESSMENT_NOT_AVAILABLE");
    expect(() => normalizeAzureAssessment({ RecognitionStatus: "NoMatch" }, "test"))
      .toThrow("SPEECH_NOT_RECOGNIZED");
  });
  it("clamps invalid values to unavailable", () => {
    const r = normalizeAzureAssessment({
      ...example, NBest: [{ ...example.NBest[0], FluencyScore: 999, ProsodyScore: -2 }],
    }, "ten four");
    expect(r.scores.fluency).toBeNull();
    expect(r.scores.prosody).toBeNull();
  });
});
