import type { EncounterCategory, EncounterLevel, EncounterScenario, LocalizedText } from "./types";

export type * from "./types";

/** Draft topics only: no scripted dialogue or legal assertions are published in this phase. */
function planned(
  id: string,
  category: EncounterCategory,
  level: EncounterLevel,
  title: LocalizedText,
  summary: LocalizedText,
  learningGoals: LocalizedText[],
): EncounterScenario {
  return {
    id, category, level, title, summary, learningGoals,
    jurisdiction: { country: "US", state: null },
    stage: "planned", legalReview: "pending", sources: [], turns: [],
  };
}

const draftScenarios: EncounterScenario[] = [
  planned("traffic-stop", "traffic", "B1-B2",
    { en: "Traffic Stop", ko: "교통 단속" },
    { en: "Understand why an officer stopped a vehicle and ask for clarification.", ko: "단속 사유를 듣고 모르는 내용을 정중하게 확인하는 상황." },
    [{ en: "Recognize common traffic-stop questions.", ko: "교통 단속 중 자주 들리는 질문 이해" }, { en: "Ask for clarification without guessing.", ko: "추측하지 않고 설명을 요청하는 표현 연습" }]),
  planned("street-encounter", "street", "B1-B2",
    { en: "Street Encounter", ko: "길거리에서 경찰을 만났을 때" },
    { en: "Respond clearly when an officer approaches you in public.", ko: "거리에서 경찰이 말을 걸었을 때 질문을 이해하고 응답하는 상황." },
    [{ en: "Understand common opening questions.", ko: "첫 질문의 의미와 어조 파악" }, { en: "Respond calmly and precisely.", ko: "차분하고 명확하게 대답하기" }]),
  planned("id-request", "identification", "B2",
    { en: "ID Request", ko: "신분 확인 요청" },
    { en: "Understand requests for identification and clarify what is being asked.", ko: "신분증 제시 요청을 이해하고 구체적인 지시를 확인하는 상황." },
    [{ en: "Distinguish a request from an instruction.", ko: "요청과 지시를 구분해 듣기" }, { en: "Ask which document is requested.", ko: "어떤 서류를 요청하는지 되묻기" }]),
  planned("witness-interview", "witness", "B2-C1",
    { en: "Witness Interview", ko: "목격자 진술" },
    { en: "Describe what you observed, without inventing details.", ko: "목격한 사건을 사실과 추측을 구분하여 설명하는 상황." },
    [{ en: "Describe events in chronological order.", ko: "사건을 시간순으로 설명하기" }, { en: "Separate what you saw from what you inferred.", ko: "직접 본 것과 추측한 것을 구분하기" }]),
  planned("reporting-a-crime", "reporting", "B2-C1",
    { en: "Reporting an Incident", ko: "사건 신고" },
    { en: "Report an incident and answer follow-up questions accurately.", ko: "사건을 신고하고 후속 질문에 정확하게 대답하는 상황." },
    [{ en: "Explain location, time and what happened.", ko: "장소·시간·발생 사실 설명하기" }, { en: "Check that important details were understood.", ko: "중요 정보가 정확히 전달됐는지 확인하기" }]),
  planned("detention-clarification", "detention", "C1",
    { en: "Detention & Clarification", ko: "구금 상황과 지시 확인" },
    { en: "Understand formal language and ask clear, non-confrontational questions.", ko: "공식적인 표현을 이해하고 현재 상황과 지시사항을 확인하는 상황." },
    [{ en: "Recognize formal police language.", ko: "공식적이고 단호한 경찰 표현 이해" }, { en: "Ask a concise question when an instruction is unclear.", ko: "불명확한 지시를 간결하게 되묻기" }]),
];

const validText = (s: LocalizedText) => !!s && !!s.ko?.trim() && !!s.en?.trim();

/** Guardrails for future branching lessons. Planned topics must never look playable. */
export function validateEncounterCatalog(items: readonly EncounterScenario[]): readonly EncounterScenario[] {
  const ids = new Set<string>();
  if (!Array.isArray(items) || items.length === 0) throw new Error("Encounter catalog must not be empty");
  for (const s of items) {
    if (!s.id || ids.has(s.id)) throw new Error("Encounter scenario ID missing or duplicated");
    ids.add(s.id);
    if (!validText(s.title) || !validText(s.summary) || !s.learningGoals?.length || !s.learningGoals.every(validText)) {
      throw new Error("Encounter scenario missing localized educational text: " + s.id);
    }
    if (s.jurisdiction?.country !== "US" || !["planned", "playable"].includes(s.stage)) {
      throw new Error("Encounter scenario jurisdiction or stage invalid: " + s.id);
    }
    if (s.stage === "planned") {
      if (s.turns.length !== 0 || s.legalReview !== "pending") throw new Error("Planned scenarios must not include playable dialogue");
      continue;
    }
    if (s.legalReview !== "reviewed" || !s.sources.length || !s.turns.length) {
      throw new Error("Playable scenarios require editorial review, sources and dialogue");
    }
    const turns = new Set(s.turns.map(t => t.id));
    if (turns.size !== s.turns.length) throw new Error("Duplicate encounter turn: " + s.id);
    for (const turn of s.turns) {
      if (!turn.id || !turn.utterance.trim() || !validText(turn.translation) || !turn.responses.length) {
        throw new Error("Incomplete encounter dialogue turn: " + s.id);
      }
      const responseIds = new Set<string>();
      for (const response of turn.responses) {
        if (!response.id || responseIds.has(response.id) || !response.utterance.trim() || !validText(response.feedback)
          || (response.nextTurnId !== null && !turns.has(response.nextTurnId))) {
          throw new Error("Invalid encounter response or branch target: " + s.id);
        }
        responseIds.add(response.id);
      }
    }
  }
  return items;
}

export const encounterCatalog = validateEncounterCatalog(draftScenarios);
