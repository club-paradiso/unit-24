"""Fail-closed evidence evaluation, shared by eligibility and invariants."""

from datetime import date
from itertools import combinations

from radiocorpus.discovery.classify import host_of
from radiocorpus.models.common import Currentness


def identity_matches(source, agency_id):
    evidence = source.identity_evidence
    return bool(
        evidence
        and evidence.verification_status == "verified"
        and evidence.target_agency_id == agency_id
        and evidence.host == host_of(source.canonical_url)
        and source.host_matches_target_entity is True
    )


def currentness(source, today=None):
    today = today or date.today()
    if source.superseded_by:
        return Currentness.SUPERSEDED
    if source.effective_date and source.effective_date > today:
        return Currentness.UNKNOWN
    evidence = source.currentness_evidence
    if evidence and evidence.verification_status == "verified" and evidence.target_source_id == source.source_id:
        if evidence.checked_on > today:
            return Currentness.UNKNOWN
        if evidence.effective_from and evidence.effective_from > today:
            return Currentness.UNKNOWN
        if evidence.effective_to and evidence.effective_to < today:
            return Currentness.HISTORICAL
        if evidence.basis == "archive":
            return Currentness.HISTORICAL
        if evidence.basis == "supersession":
            return Currentness.SUPERSEDED
        if evidence.recheck_by is None or evidence.recheck_by < today or evidence.recheck_by < evidence.checked_on:
            return Currentness.PRESUMED
        if evidence.basis in {"active_policy_portal", "current_policy_index", "explicit_effective_policy"}:
            return Currentness.CONFIRMED
        return Currentness.PRESUMED
    return Currentness.UNDATED if not (source.effective_date or source.publication_date) else Currentness.UNKNOWN


def acquired_bytes_match(store, source):
    """A hash string alone is not an acquisition receipt; verify the local artifact."""
    from pathlib import Path

    from radiocorpus.config import PATHS
    from radiocorpus.ids import document_hash

    if not source or not source.document_hash:
        return False
    document = store.get_document(source.document_hash)
    if document is None:
        return False
    path = Path(document.local_path)
    if not path.is_absolute():
        path = PATHS.root / path
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return bool(data and len(data) == document.byte_length and document_hash(data) == source.document_hash)


def pointer_exists(store, evidence):
    source = store.get_source(evidence.evidence_source_id) if evidence else None
    return acquired_bytes_match(store, source)


def applicability_matches(store, fact, source, today=None):
    today = today or date.today()
    if source.agency_or_jurisdiction == fact.agency_id:
        proof = source.issuing_authority_evidence
        return bool(
            source.issuing_authority_id == fact.agency_id
            and proof
            and proof.target_source_id == source.source_id
            and proof.issuing_authority_id == source.issuing_authority_id
            and proof.verification_status == "verified"
            and pointer_exists(store, proof)
        )
    for evidence in source.applicability:
        if (
            evidence.verification_status == "verified"
            and pointer_exists(store, evidence)
            and evidence.protocol_source_id == source.source_id
            and evidence.source_agency_or_dispatcher == source.agency_or_jurisdiction
            and evidence.target_agency == fact.agency_id
            and fact.fact_type in evidence.scope
            and fact.key in evidence.fact_keys
            and evidence.effective_from <= today
            and (evidence.effective_to is None or today <= evidence.effective_to)
        ):
            return True
    return False


def independently_corroborated(sources):
    """Unknown lineage is not independence; URL/hash/issuer/lineage must all differ."""
    for a, b in combinations(sources, 2):
        if (
            a.is_official
            and b.is_official
            and a.document_hash
            and b.document_hash
            and a.document_hash != b.document_hash
            and a.canonical_url != b.canonical_url
            and a.issuing_authority_id
            and b.issuing_authority_id
            and a.issuing_authority_id != b.issuing_authority_id
            and a.evidence_lineage
            and b.evidence_lineage
            and set(a.evidence_lineage).isdisjoint(b.evidence_lineage)
        ):
            return True
    return False


def reviewed_fact_matches(fact, source, today=None):
    today = today or date.today()
    review = fact.review_evidence
    return bool(
        review
        and review.reviewer_kind == "human"
        and review.decision == "accepted"
        and review.fact_id == fact.fact_id
        and review.source_id == fact.source_id
        and review.document_hash == source.document_hash
        and review.value_fingerprint == fact.value_fingerprint()
        and review.reviewed_on <= today
    )
