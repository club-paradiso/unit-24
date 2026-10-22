import { describe, expect, it } from "vitest";
import { heardSimilarity, numberReading, normalizeSpeech, radioReading, radioDisplayReading } from "./radioSpeech";

describe("voice-first radio code training", () => {
  it("converts common code forms to spoken text, not a bare hyphen or integer", () => {
    expect(radioReading({ kind: "code", term: "10-4", answer: "Acknowledgment" })).toBe("ten four");
    expect(radioReading({ kind: "code", term: "10-20", answer: "Location" })).toBe("ten twenty");
    expect(radioReading({ kind: "code", term: "10-28", answer: "Registration" })).toBe("ten twenty eight");
    expect(radioReading({ kind: "code", term: "11-99", answer: "Request" })).toBe("eleven ninety nine");
  });
  it("teaches alphabet words distinctly from spelled letter names", () => {
    expect(radioReading({ kind: "letter", term: "A", answer: "Adam" })).toBe("Adam");
    expect(radioDisplayReading({ kind: "letter", term: "A", answer: "Adam" })).toBe("A as in Adam");
  });
  it("does not treat recognition transcription as a pronunciation score", () => {
    expect(numberReading(0)).toBe("zero");
    expect(normalizeSpeech("10-4!")).toBe("ten four");
    expect(heardSimilarity("ten four", "ten four")).toBe("similar");
    expect(heardSimilarity("ten one", "ten four")).toBe("partial");
    expect(heardSimilarity("unknown", "ten four")).toBe("different");
  });
});
