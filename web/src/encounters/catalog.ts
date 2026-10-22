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

const trafficStopPilot: EncounterScenario = {
  "id": "traffic-stop",
  "category": "traffic",
  "level": "B1-B2",
  "title": {
    "en": "Traffic Stop",
    "ko": "교통 단속"
  },
  "summary": {
    "en": "Understand why an officer stopped a vehicle and ask for clarification.",
    "ko": "단속 사유를 듣고 모르는 내용을 정중하게 확인하는 상황."
  },
  "learningGoals": [
    {
      "en": "Recognize common traffic-stop questions.",
      "ko": "교통 단속 중 자주 들리는 질문 이해"
    },
    {
      "en": "Ask for clarification without guessing.",
      "ko": "추측하지 않고 설명을 요청하는 표현 연습"
    }
  ],
  "jurisdiction": {
    "country": "US",
    "state": null
  },
  "stage": "pilot",
  "legalReview": "pending",
  "sources": [
    {
      "title": "U.S. Department of Justice · procedural justice traffic-stop example",
      "url": "https://www.justice.gov/ag/media/1079466/dl?inline=",
      "checkedAt": "2026-10-22",
      "jurisdiction": "US · illustrative training context"
    },
    {
      "title": "ACLU · Stopped by Police",
      "url": "https://www.aclu.org/know-your-rights/stopped-by-police",
      "checkedAt": "2026-10-22",
      "jurisdiction": "United States · general educational resource"
    }
  ],
  "turns": [
    {
      "id": "opening",
      "speaker": "officer",
      "utterance": "Good evening. Do you know why I pulled you over?",
      "translation": {
        "ko": "안녕하세요. 제가 왜 차를 세웠는지 아시겠어요?",
        "en": "Do you know the reason for this traffic stop?"
      },
      "responses": [
        {
          "id": "request-reason",
          "utterance": "I'm not sure. Could you tell me why?",
          "feedback": {
            "ko": "모른다는 점을 명확히 밝히고 이유를 묻는 자연스러운 응답이에요.",
            "en": "Clear and polite: you say you do not know and ask for the reason."
          },
          "nextTurnId": "reason",
          "languageRating": "natural"
        },
        {
          "id": "repeat",
          "utterance": "Sorry, could you repeat that?",
          "feedback": {
            "ko": "잘 들리지 않았을 때 다시 말해 달라고 요청하는 적절한 표현이에요.",
            "en": "A polite way to ask for repetition when you did not hear the question."
          },
          "nextTurnId": "repeated",
          "languageRating": "natural"
        },
        {
          "id": "assume",
          "utterance": "I guess I was speeding.",
          "feedback": {
            "ko": "확인하지 않은 사실을 추측해서 말하는 표현이에요. 언어 연습에서는 추측하지 않고 되묻는 방법도 익혀 보세요.",
            "en": "This guesses at a reason you do not know. Practice asking for clarification instead."
          },
          "nextTurnId": "reason",
          "languageRating": "needs_clarification"
        }
      ]
    },
    {
      "id": "repeated",
      "speaker": "officer",
      "utterance": "I asked whether you know why I stopped your car.",
      "translation": {
        "ko": "왜 차를 세웠는지 알고 계시냐고 물었습니다.",
        "en": "I am repeating the question about the reason for the stop."
      },
      "responses": [
        {
          "id": "repeat-understood",
          "utterance": "Thanks for repeating that. I'm not sure.",
          "feedback": {
            "ko": "감사 표현 뒤에 모른다는 사실을 명확히 전달해요.",
            "en": "Natural acknowledgment followed by a clear statement that you do not know."
          },
          "nextTurnId": "reason",
          "languageRating": "natural"
        },
        {
          "id": "repeat-clarify",
          "utterance": "Could you explain why you stopped me?",
          "feedback": {
            "ko": "질문에 직접 답하지는 않지만 정중하게 이유를 확인하는 표현이에요.",
            "en": "A polite request for the explanation instead of a direct answer."
          },
          "nextTurnId": "reason",
          "languageRating": "acceptable"
        }
      ]
    },
    {
      "id": "reason",
      "speaker": "officer",
      "utterance": "One of your brake lights appears to be out.",
      "translation": {
        "ko": "브레이크등 중 하나가 작동하지 않는 것 같습니다.",
        "en": "The officer says a brake light appears not to be working."
      },
      "responses": [
        {
          "id": "acknowledge",
          "utterance": "Thank you for letting me know. I didn't realize that.",
          "feedback": {
            "ko": "알려준 사실에 대한 감사와 몰랐다는 정보를 자연스럽게 전해요.",
            "en": "A polite acknowledgment that does not add unsupported details."
          },
          "nextTurnId": null,
          "languageRating": "natural"
        },
        {
          "id": "which-light",
          "utterance": "Could you clarify which brake light you mean?",
          "feedback": {
            "ko": "어느 쪽인지 구체적으로 설명해 달라고 요청하는 정확한 표현이에요.",
            "en": "A precise and polite clarification request."
          },
          "nextTurnId": "clarification",
          "languageRating": "natural"
        }
      ]
    },
    {
      "id": "clarification",
      "speaker": "officer",
      "utterance": "The left brake light, at the back of the car.",
      "translation": {
        "ko": "차 뒤쪽 왼쪽 브레이크등입니다.",
        "en": "The rear left brake light."
      },
      "responses": [
        {
          "id": "thank-you",
          "utterance": "Thanks for clarifying.",
          "feedback": {
            "ko": "짧지만 적절하고 자연스러운 감사 표현이에요.",
            "en": "Concise and natural acknowledgment of the explanation."
          },
          "nextTurnId": null,
          "languageRating": "natural"
        },
        {
          "id": "got-it",
          "utterance": "Got it. Thank you.",
          "feedback": {
            "ko": "구어체에서 매우 자연스러운 이해 확인 표현이에요.",
            "en": "Natural conversational acknowledgment."
          },
          "nextTurnId": null,
          "languageRating": "natural"
        }
      ]
    }
  ]
};

const draftScenarios: EncounterScenario[] = [
  trafficStopPilot,
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
  if (items.length === 0) throw new Error("Encounter catalog must not be empty");
  for (const s of items) {
    if (!s.id || ids.has(s.id)) throw new Error("Encounter scenario ID missing or duplicated");
    ids.add(s.id);
    if (!validText(s.title) || !validText(s.summary) || !s.learningGoals?.length || !s.learningGoals.every(validText)) {
      throw new Error("Encounter scenario missing localized educational text: " + s.id);
    }
    if (s.jurisdiction?.country !== "US" || !["planned", "pilot", "playable"].includes(s.stage)) {
      throw new Error("Encounter scenario jurisdiction or stage invalid: " + s.id);
    }
    if (s.stage === "planned") {
      if (s.turns.length !== 0 || s.legalReview !== "pending") throw new Error("Planned scenarios must not include playable dialogue");
      continue;
    }
    if (!s.sources.length || !s.turns.length || (s.stage === "playable" && s.legalReview !== "reviewed")
      || (s.stage === "pilot" && s.legalReview !== "pending")) {
      throw new Error("Interactive scenarios require appropriate review state, sources and dialogue");
    }
    for (const source of s.sources) {
      if (!source.title.trim() || !source.url.startsWith("https://") || !/^\\d{4}-\\d{2}-\\d{2}$/.test(source.checkedAt)
        || !source.jurisdiction.trim()) throw new Error("Invalid encounter source: " + s.id);
    }
    const turns = new Set(s.turns.map(t => t.id));
    if (turns.size !== s.turns.length) throw new Error("Duplicate encounter turn: " + s.id);
    for (const turn of s.turns) {
      if (!turn.id || !turn.utterance.trim() || !validText(turn.translation) || !turn.responses.length) {
        throw new Error("Incomplete encounter dialogue turn: " + s.id);
      }
      const responseIds = new Set<string>();
      for (const response of turn.responses) {
        if (!response.id || responseIds.has(response.id) || !response.utterance.trim() || !validText(response.feedback) || !["natural", "acceptable", "needs_clarification"].includes(response.languageRating)
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
