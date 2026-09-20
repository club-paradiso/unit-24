"""Model-backed extraction behind an interface.

The default extractor is NullExtractor (does nothing). A model extractor must:
  * return candidates only, always with verification_status=UNVERIFIED and review NEEDS_REVIEW;
  * quote a locator + short excerpt for every candidate, or the candidate is dropped;
  * record the model id so provenance shows AI involvement.
No model output ever enters the verified corpus without human acceptance (enforced in
ProtocolFact validation and the eligibility policy)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from radiocorpus.extraction.text import TextBlock


@dataclass(frozen=True)
class ModelCandidate:
    fact_type: str  # code_meaning | phonetic_letter | procedure_rule | ordered_structure | interop_rule | callsign_convention | protocol_mode
    payload: dict
    locator: str
    excerpt: str
    model: str


class Extractor(Protocol):
    name: str

    def extract(self, blocks: list[TextBlock], *, agency_name: str) -> list[ModelCandidate]: ...


class NullExtractor:
    name = "null"

    def extract(self, blocks: list[TextBlock], *, agency_name: str) -> list[ModelCandidate]:
        return []


_PROMPT = """You extract radio-protocol facts from an official document for the agency "{agency}".
Return ONLY a JSON array. Each element: {{"fact_type": one of [code_meaning, phonetic_letter, procedure_rule,
ordered_structure, interop_rule, callsign_convention, protocol_mode], "payload": {{...}}, "locator": "<locator id
copied from the input>", "excerpt": "<verbatim sentence or row, max 300 chars>"}}.
Rules: never infer; only state what the text says; if unsure, omit. payload shapes:
code_meaning: {{"code_system","code","meaning"}}; phonetic_letter: {{"letter","word"}};
procedure_rule: {{"procedure","rule_text","prescribed_phrases":[]}}; ordered_structure: {{"structure","ordered_fields":[]}};
interop_rule: {{"rule_kind","rule_text"}}; callsign_convention: {{"element","pattern","examples":[]}};
protocol_mode: {{"mode","statement"}}.
Input blocks (locator :: text):
{blocks}
"""


class AnthropicExtractor:
    """Uses the Anthropic Messages API. Requires ANTHROPIC_API_KEY and explicit opt-in
    (RADIOCORPUS_ENABLE_MODEL_EXTRACTION=1). Not used by the default pipeline."""

    def __init__(self, model: str | None = None) -> None:
        if os.environ.get("RADIOCORPUS_ENABLE_MODEL_EXTRACTION") != "1":
            raise RuntimeError("model extraction disabled; set RADIOCORPUS_ENABLE_MODEL_EXTRACTION=1 to opt in")
        try:
            import anthropic  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("pip install anthropic to use AnthropicExtractor") from e
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("RADIOCORPUS_EXTRACTION_MODEL", "claude-sonnet-5")
        self.name = f"anthropic:{self.model}"

    def extract(self, blocks: list[TextBlock], *, agency_name: str) -> list[ModelCandidate]:  # pragma: no cover - network
        text = "\n".join(f"{b.locator} :: {b.text[:1500]}" for b in blocks)[:150_000]
        msg = self.client.messages.create(
            model=self.model, max_tokens=8000, messages=[{"role": "user", "content": _PROMPT.format(agency=agency_name, blocks=text)}]
        )
        raw = "".join(getattr(p, "text", "") for p in msg.content)
        return parse_model_output(raw, self.name, {b.locator for b in blocks})


def parse_model_output(raw: str, model: str, valid_locators: set[str]) -> list[ModelCandidate]:
    """Strict: drop anything without a known locator or an excerpt. Deterministic, testable."""
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < 0:
        return []
    try:
        arr = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    out: list[ModelCandidate] = []
    for el in arr if isinstance(arr, list) else []:
        if not isinstance(el, dict):
            continue
        loc, exc = el.get("locator"), el.get("excerpt")
        if loc not in valid_locators or not exc or not isinstance(el.get("payload"), dict):
            continue
        out.append(ModelCandidate(fact_type=str(el.get("fact_type")), payload=el["payload"], locator=str(loc), excerpt=str(exc)[:300], model=model))
    return out
