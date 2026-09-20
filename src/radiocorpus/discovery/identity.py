"""Explicit website assignment, never called by search ranking or token overlap."""

from radiocorpus.discovery.classify import host_of
from radiocorpus.models import Agency
from radiocorpus.models.evidence import IdentityEvidence
from radiocorpus.normalization.names import normalize_name


def verified_website(agency: Agency, url: str, evidence: IdentityEvidence) -> bool:
    return bool(
        evidence.verification_status == "verified"
        and evidence.target_agency_id == agency.agency_id
        and evidence.state == agency.state
        and normalize_name(evidence.canonical_name) in {normalize_name(n) for n in [agency.canonical_name, *agency.alternate_names]}
        and evidence.host == host_of(url)
    )
