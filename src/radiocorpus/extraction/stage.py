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
from radiocorpus.extraction.codes import PARSER_VERSION as CODE_PARSER_VERSION
from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.llm import Extractor, NullExtractor
from radiocorpus.extraction.phonetics import PARSER_VERSION as PHONETIC_PARSER_VERSION
from radiocorpus.extraction.phonetics import describe_alphabet, parse_phonetics
from radiocorpus.extraction.procedures import PARSER_VERSION as PROCEDURE_PARSER_VERSION
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.layout import cache as layout_cache
from radiocorpus.layout.backends import layout_for
from radiocorpus.layout.model import LAYOUT_VERSION, layout_code_fingerprint
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
        # Every component that can change emitted facts is pinned in the resume key, so a
        # parser or layout change never reuses a previous run's progress.
        item_fp = (
            f"layout:{LAYOUT_VERSION}:{layout_code_fingerprint()}:code:{CODE_PARSER_VERSION}"
            f":phon:{PHONETIC_PARSER_VERSION}:proc:{PROCEDURE_PARSER_VERSION}:{doc.document_hash}:{extractor.name}"
        )
        if not force and store.progress_done("extraction", src.source_id, item_fp):
            stats["skipped_resumed"] += 1
            continue
        try:
            data = _resolve_path(doc.local_path).read_bytes()
            if ids.document_hash(data) != doc.document_hash:
                raise ValueError("document bytes no longer match provenance hash")
            cache_root = PATHS.intermediate / "layout_cache"
            layout = layout_cache.load(cache_root, doc.document_hash)
            if layout is None:
                layout = layout_for(data, doc.content_type, document_hash=doc.document_hash)
                layout_cache.save(layout, cache_root, doc.document_hash)
            blocks = layout.included_blocks()
        except Exception as error:
            stats["parser_failures"] += 1
            store.mark_progress("extraction", src.source_id, item_fp, "failed", run.run_id, str(error)[:200])
            continue
        if any(not b.text.strip() for b in blocks) and "pdf" in (doc.content_type or ""):
            stats["documents_requiring_ocr_review"] += 1
        if max((p.column_count for p in layout.pages), default=1) > 1:
            stats["multi_column_documents"] += 1
        text = layout.full_text()
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
            for c in parse_codes(layout):
                val = CodeMeaning(code_system=c.code_system, code=c.code, meaning=c.meaning)
                f = _fact(
                    agency_id, FactType.CODE_MEANING, c.code, val, c.raw, src, c.locator, c.excerpt,
                    eff_from, eff_to, tstatus, 0.8, run.run_id,
                    rule=c.parser_rule, rule_version=c.parser_version,
                    notes=f"structural_reason={c.structural_reason}; evidence={'; '.join(c.evidence)[:400]}",
                )
                n += store.insert_fact(f)
            ph = parse_phonetics(layout)
            if ph:
                report = describe_alphabet(ph)
                label, coverage = report.label, report.coverage
                for c in ph:
                    diverges = c.letter in report.divergences
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
                        rule=c.parser_rule,
                        rule_version=c.parser_version,
                        notes=(
                            f"structural_reason={c.structural_reason}; label_is_descriptive_only=true; "
                            f"diverges_from_{label}={diverges}"
                        ),
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
            for c in parse_procedures(layout):
                val3 = ProcedureRule(procedure=c.procedure, rule_text=c.rule_text)
                scope_bits = [b for b in (c.section_heading, *(c.section_path or ())) if b]
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
                    0.5 if c.context_complete else 0.3,
                    run.run_id,
                    rule=c.parser_rule,
                    rule_version=c.parser_version,
                    scope=" / ".join(dict.fromkeys(scope_bits))[:200] or None,
                    notes=(
                        f"medium={c.medium}; context_complete={c.context_complete}; has_condition={c.has_condition}; "
                        f"has_exception={c.has_exception}; crosses_page={c.crosses_page}; "
                        f"context_before={(c.context_before or '')[:160]!r}; context_after={(c.context_after or '')[:160]!r}"
                    ),
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


def _fact(  # type: ignore[no-untyped-def]
    agency_id, ftype, key, value, raw, src, locator, excerpt, eff_from, eff_to, tstatus, conf, run_id,
    *, rule=None, rule_version=None, scope=None, notes=None,
) -> ProtocolFact:
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
        extraction_rule=rule or f"{ftype}:candidate",
        extraction_rule_version=rule_version or "3",
        text_extraction_method="native_pdf_text" if "pdf" in (src.content_type or "") else ("html" if "html" in (src.content_type or "") else "text"),
        review_status=ReviewStatus.UNREVIEWED,
        applicability_scope=scope,
        notes=notes,
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
