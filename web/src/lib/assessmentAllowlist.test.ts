import { describe, expect, it } from "vitest";
import { allowedReferences } from "../../api/speech-assess";
import { content } from "../content";
import { encounterCatalog } from "../encounters/catalog";
import { radioReading } from "./radioSpeech";

/**
 * Activation guard: the assessment proxy only accepts phrases on its server
 * allowlist. If a lesson or encounter phrase drifts off that list, enabling
 * Azure would turn that phrase's assessment into a silent 400 dead end.
 * Every phrase a SpeechCoach can send must stay covered.
 */
describe("assessment reference allowlist covers every teachable phrase", () => {
  const allowed = new Set(allowedReferences.map((phrase) => phrase.toLowerCase()));

  it("covers every CHP item reading (codes and card alphabet)", () => {
    const phrases = content.items.map((item) => radioReading(item));
    expect(phrases.length).toBeGreaterThan(0);
    expect(phrases.filter((phrase) => !allowed.has(phrase.toLowerCase()))).toEqual([]);
  });

  it("covers every encounter utterance (officer turns and learner responses)", () => {
    const utterances = encounterCatalog.flatMap((scenario) =>
      (scenario.turns ?? []).flatMap((turn) => [
        turn.utterance,
        ...turn.responses.map((response) => response.utterance),
      ]),
    );
    expect(utterances.length).toBeGreaterThan(0);
    expect(utterances.filter((phrase) => !allowed.has(phrase.toLowerCase()))).toEqual([]);
  });
});
