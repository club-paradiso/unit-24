"""Stage 6+7: text extraction and candidate fact extraction over acquired documents.

Every candidate is written as an UNVERIFIED ProtocolFact with a locator and excerpt.
Validation, cross-checking, and eligibility happen in later stages; nothing here is
"verified"."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

from radiocorpus import ids
from radiocorpus.config import PATHS
from radiocorpus.extraction.codes import parse_code_blocks
from radiocorpus.extraction.llm import Extractor, NullExtractor
from radiocorpus.extraction.phonetics import label_system, parse_phonetic_blocks
from radiocorpus.extraction.procedures import parse_procedure_blocks
from radiocorpus.extraction.text import blocks_for, full_text
from radiocorpus.models import (
    CodeMeaning,
    PhoneticLetter,
    PhoneticSystemAssertion,
    ProcedureRule,
    ProtocolFact,
    Source,
    StageRun,
)
from radiocorpus.models.common import ExtractionMethod, FactType, ReviewStatus, TemporalStatus, VerificationStatus
from radiocorpus.normalization.temporal import find_effective_date
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store


def _resolve_path(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else PATHS.root / path


def _eff_dates(src: Source) -> tuple[date | None, date | None, TemporalStatus]:
    eff = src.effective_date or src.publication_date
    if src.temporal_status == TemporalStatus.HISTORICAL:
        return eff, None, TemporalStatus.HISTORICAL
    if src.temporal_status == TemporalStatus.CURRENT:
        return eff, None, TemporalStatus.CURRENT
    return eff, None, TemporalStatus.UNCERTAIN


def extract_all(store: Store, *, extractor: Extractor | None = None, force: bool = False) -> StageRun:
    extractor = extractor or NullExtractor()
    docs = store.documents()
    fp = f"{len(docs)}:{extractor.name}"
    run = start_run(store, "extraction", fp)
    stats: Counter[str] = Counter()
    # Blobs are deduplicated by hash; source attribution and extraction are not.
    for src in store.sources():
        doc = store.get_document(src.document_hash or "")
        if doc is None:
            continue
        if src is None:
            stats["orphan_document"] += 1
            continue
        item_fp = f"parser-v2:{doc.document_hash}:{extractor.name}"
        if not force and store.progress_done("extraction", src.source_id, item_fp):
            stats["skipped_resumed"] += 1
            continue
        try:
            data = _resolve_path(doc.local_path).read_bytes()
            if ids.document_hash(data) != doc.document_hash:
                raise ValueError("document bytes no longer match provenance hash")
            blocks = blocks_for(data, doc.content_type)
        except Exception as error:
            stats["parser_failures"] += 1
            store.mark_progress("extraction", src.source_id, item_fp, "failed", run.run_id, str(error)[:200])
            continue
        if any(not b.text.strip() for b in blocks) and "pdf" in (doc.content_type or ""):
            stats["documents_requiring_ocr_review"] += 1
        text = full_text(blocks)
        # Effective date discovered in the text is recorded on the source only when the source has none.
        if src.effective_date is None:
            d = find_effective_date(text[:20000])
            if d:
                store.update_source_status(
                    src.source_id, field="effective_date", new_value=d, reason="effective date parsed from document text", run_id=run.run_id
                )
                src = store.get_source(src.source_id) or src
        agency = store.get_agency(src.agency_or_jurisdiction or "")
        agency_id = src.agency_or_jurisdiction or ""
        if not agency_id or agency is None:
            stats["source_without_agency"] += 1
            store.mark_progress("extraction", src.source_id, item_fp, "skipped", run.run_id, "no agency")
            continue
        eff_from, eff_to, tstatus = _eff_dates(src)
        n = 0
        with store.tx():
            for c in parse_code_blocks(blocks):
                val = CodeMeaning(code_system=c.code_system, code=c.code, meaning=c.meaning)
                f = _fact(agency_id, FactType.CODE_MEANING, c.code, val, c.raw, src, c.locator, c.excerpt, eff_from, eff_to, tstatus, 0.8, run.run_id)
                n += store.insert_fact(f)
            ph = parse_phonetic_blocks(blocks)
            if ph:
                label, coverage = label_system(ph)
                for c in ph:
                    val = PhoneticLetter(letter=c.letter, word=c.word, system=label)
                    f = _fact(
                        agency_id,
                        FactType.PHONETIC_LETTER,
                        f"letter:{c.letter}",
                        val,
                        f"{c.letter} {c.word}",
                        src,
                        c.locator,
                        c.excerpt,
                        eff_from,
                        eff_to,
                        tstatus,
                        0.8 if coverage >= 0.5 else 0.5,
                        run.run_id,
                    )
                    n += store.insert_fact(f)
                if coverage >= 0.5:
                    val2 = PhoneticSystemAssertion(system=label, scope=f"coverage={coverage:.2f}")
                    f = _fact(
                        agency_id,
                        FactType.PHONETIC_SYSTEM,
                        "system",
                        val2,
                        None,
                        src,
                        ph[0].locator,
                        ph[0].excerpt,
                        eff_from,
                        eff_to,
                        tstatus,
                        0.6,
                        run.run_id,
                    )
                    n += store.insert_fact(f)
            for c in parse_procedure_blocks(blocks):
                val3 = ProcedureRule(procedure=c.procedure, rule_text=c.rule_text)
                f = _fact(
                    agency_id,
                    FactType.PROCEDURE_RULE,
                    f"proc:{c.procedure}",
                    val3,
                    None,
                    src,
                    c.locator,
                    c.excerpt,
                    eff_from,
                    eff_to,
                    tstatus,
                    0.4,
                    run.run_id,
                )
                n += store.insert_fact(f)
            for mc in extractor.extract(blocks, agency_name=agency.canonical_name):
                f2 = _model_fact(agency_id, mc, src, eff_from, eff_to, tstatus, run.run_id)
                if f2:
                    n += store.insert_fact(f2)
            store.mark_progress("extraction", src.source_id, item_fp, "done", run.run_id, f"{n} facts")
        stats["documents"] += 1
        stats["facts_inserted"] += n
    return finish_run(store, run, dict(stats))


def _fact(agency_id, ftype, key, value, raw, src, locator, excerpt, eff_from, eff_to, tstatus, conf, run_id) -> ProtocolFact:  # type: ignore[no-untyped-def]
    tmp = ProtocolFact(
        fact_id="fct_tmp",
        agency_id=agency_id,
        fact_type=ftype,
        key=key,
        value=value,
        raw_value=raw,
        source_id=src.source_id,
        locator=locator,
        excerpt=excerpt,
        effective_from=eff_from,
        effective_to=eff_to,
        temporal_status=tstatus,
        confidence=conf,
        verification_status=VerificationStatus.UNVERIFIED,
        extraction_method=ExtractionMethod.DETERMINISTIC_PARSER,
        extraction_rule=f"{ftype}:candidate",
        extraction_rule_version="2",
        text_extraction_method="native_pdf_text" if "pdf" in (src.content_type or "") else ("html" if "html" in (src.content_type or "") else "text"),
        review_status=ReviewStatus.UNREVIEWED,
        run_id=run_id,
    )
    fid = ids.fact_id(agency_id, ftype, key, src.source_id, locator, tmp.value_fingerprint())
    return tmp.model_copy(update={"fact_id": fid})


def _model_fact(agency_id, mc, src, eff_from, eff_to, tstatus, run_id) -> ProtocolFact | None:  # type: ignore[no-untyped-def]
    from radiocorpus.models.fact import CallsignConvention, InteropRule, OrderedStructure, ProtocolModeAssertion

    builders = {
        "code_meaning": (FactType.CODE_MEANING, lambda p: CodeMeaning(**p), lambda p: p.get("code", "")),
        "phonetic_letter": (
            FactType.PHONETIC_LETTER,
            lambda p: PhoneticLetter(system=p.get("system", "UNKNOWN"), **{k: v for k, v in p.items() if k != "system"}),
            lambda p: f"letter:{p.get('letter', '')}",
        ),
        "procedure_rule": (FactType.PROCEDURE_RULE, lambda p: ProcedureRule(**p), lambda p: f"proc:{p.get('procedure', '')}"),
        "ordered_structure": (FactType.ORDERED_STRUCTURE, lambda p: OrderedStructure(**p), lambda p: f"struct:{p.get('structure', '')}"),
        "interop_rule": (FactType.INTEROP_RULE, lambda p: InteropRule(**p), lambda p: f"interop:{p.get('rule_kind', '')}"),
        "callsign_convention": (FactType.CALLSIGN_CONVENTION, lambda p: CallsignConvention(**p), lambda p: f"callsign:{p.get('element', '')}"),
        "protocol_mode": (FactType.PROTOCOL_MODE, lambda p: ProtocolModeAssertion(**p), lambda p: "mode"),
    }
    if mc.fact_type not in builders:
        return None
    ftype, build, keyfn = builders[mc.fact_type]
    try:
        value = build(mc.payload)
    except Exception:
        return None
    tmp = ProtocolFact(
        fact_id="fct_tmp",
        agency_id=agency_id,
        fact_type=ftype,
        key=keyfn(mc.payload),
        value=value,
        source_id=src.source_id,
        locator=mc.locator,
        excerpt=mc.excerpt,
        effective_from=eff_from,
        effective_to=eff_to,
        temporal_status=tstatus,
        confidence=0.5,
        verification_status=VerificationStatus.UNVERIFIED,
        extraction_method=ExtractionMethod.MODEL,
        extraction_model=mc.model,
        review_status=ReviewStatus.NEEDS_REVIEW,
        run_id=run_id,
    )
    return tmp.model_copy(update={"fact_id": ids.fact_id(agency_id, ftype, tmp.key, src.source_id, mc.locator, tmp.value_fingerprint())})
