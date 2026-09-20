"""Deterministic classification of search hits into leads.

Two questions are answered separately, each with a stated basis:
  1. Is the host plausibly the agency's (or its parent government's) official host?
  2. Does the title/URL suggest a radio-protocol document?
A "yes" to (1) makes the lead an OFFICIAL_* candidate; it never makes it evidence. Evidence
requires acquisition + hashing + review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from radiocorpus.models.common import LeadClass
from radiocorpus.normalization.names import core_tokens, name_tokens
from radiocorpus.normalization.states import STATE_NAMES

NON_OFFICIAL_HOSTS = (
    "wikipedia.org",
    "wikimedia.org",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "linkedin.com",
    "reddit.com",
    "quizlet.com",
    "radioreference.com",
    "broadcastify.com",
    "scribd.com",
    "coursehero.com",
    "studylib.net",
    "yumpu.com",
    "issuu.com",
    "pdffiller.com",
    "glassdoor.com",
    "indeed.com",
    "zippia.com",
    "nextdoor.com",
    "tiktok.com",
    "medium.com",
    "blogspot.com",
    "wordpress.com",
    "fandom.com",
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "yelp.com",
    "mapquest.com",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "synthasite.com",
    "weebly.com",
    "wixsite.com",
    "tripod.com",
    "angelfire.com",
    "muckrock.com",
    "documentcloud.org",
    "aclu.org",
    "aclu-wi.org",
    "law.cornell.edu",
    "justia.com",
    "casetext.com",
    "findlaw.com",
    "ballotpedia.org",
    "powerdms.com",
    "policeone.com",
    "police1.com",
    "officer.com",
    "govtribe.com",
    "usa.gov",
)
ENTHUSIAST_HOSTS = (
    "radioreference.com",
    "broadcastify.com",
    "quizlet.com",
    "synthasite.com",
    "weebly.com",
    "wixsite.com",
    "tripod.com",
    "angelfire.com",
    "fandom.com",
    "scribd.com",
    "studylib.net",
    "coursehero.com",
)
STANDARDS_HOSTS = ("apcointl.org", "fema.gov", "npstc.org", "cisa.gov", "dhs.gov", "safecom", "nist.gov")

RADIO_TERMS = re.compile(
    r"(radio|10[- ]?code|ten[- ]?code|ten[- ]?signal|signal code|phonetic|communications? (manual|procedure|policy|division|order|directive)|"
    r"brevity|dispatch|call ?sign|unit designat|status code|disposition code|general order|policy manual|directive|"
    r"standard operating|sop\b|interoperab|plain (language|talk|speech)|mutual aid)",
    re.I,
)
CODE_LIST_TERMS = re.compile(r"(10[- ]?codes?|ten[- ]?codes?|ten[- ]?signals?|signal codes?|brevity|status codes?|radio codes?)", re.I)
PHONETIC_TERMS = re.compile(r"phonetic", re.I)


@dataclass(frozen=True)
class HostJudgment:
    host: str
    is_official: bool | None
    basis: str


def host_of(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def _state_gov_hosts(state: str | None) -> set[str]:
    if not state:
        return set()
    s = state.lower()
    full = STATE_NAMES.get(state, "").lower().replace(" ", "")
    hosts = {f"{s}.gov", f"state.{s}.us", f"{full}.gov", f"my{full}.com" if full == "florida" else f"{full}.gov"}
    return {h for h in hosts if h}


def _acronyms(agency_name: str) -> set[str]:
    toks = name_tokens(agency_name)
    out = {"".join(t[0] for t in toks)}
    out.add("".join(t[0] for t in toks if t not in {"county", "city", "of", "the"}))
    return {a for a in out if a}


def judge_host(url: str, agency_name: str, state: str | None) -> HostJudgment:
    host = host_of(url)
    if not host:
        return HostJudgment(host, None, "no host")
    for bad in NON_OFFICIAL_HOSTS:
        if host == bad or host.endswith("." + bad):
            return HostJudgment(host, False, f"host {host} is a known non-official platform ({bad})")
    tokens = core_tokens(agency_name)
    compact = host.replace("-", "").replace(".", "")
    name_hit = [t for t in tokens if len(t) >= 4 and t in compact]
    first_label = host.split(".")[0]
    for acr in _acronyms(agency_name):
        if len(acr) >= 3 and (
            first_label == acr
            or first_label.startswith(acr)
            and not first_label[len(acr) : len(acr) + 1].isalpha()
            or first_label.startswith(acr + "online")
        ):
            name_hit.append(f"acronym:{acr}")
    gov_like = host.endswith(".gov") or host.endswith(".us") or host.endswith(".mil")
    if gov_like:
        return HostJudgment(host, True, f"government TLD host {host}" + (f"; name tokens {name_hit}" if name_hit else ""))
    for sg in _state_gov_hosts(state):
        if host == sg or host.endswith("." + sg):
            return HostJudgment(host, True, f"state government host {host}")
    # agency-branded non-.gov hosts (lapdonline.org, lasd.org, lsp.org, phillypolice.com ...) are plausible but not
    # provable from the host alone
    if name_hit and (host.endswith(".org") or host.endswith(".com") or host.endswith(".net") or host.endswith(".edu")):
        return HostJudgment(host, None, f"agency-named non-government host {host} (tokens {name_hit}); needs confirmation")
    if host.endswith(".edu"):
        return HostJudgment(host, None, f"educational host {host}; official only if it is the campus agency's institution")
    return HostJudgment(host, False, f"host {host} has no official signal")


def classify_hit(url: str, title: str | None, snippet: str | None, agency_name: str, state: str | None) -> tuple[LeadClass, HostJudgment, str]:
    hj = judge_host(url, agency_name, state)
    text = f"{title or ''} {url} {snippet or ''}"
    is_doc = url.lower().endswith(".pdf") or bool(RADIO_TERMS.search(text))
    is_radio = bool(RADIO_TERMS.search(text))
    for h in STANDARDS_HOSTS:
        if h in hj.host:
            return LeadClass.STANDARDS_BODY_DOCUMENT, hj, f"standards/federal host; {'radio terms' if is_radio else 'no radio terms'}"
    for h in ENTHUSIAST_HOSTS:
        if hj.host.endswith(h):
            return LeadClass.ENTHUSIAST_LEAD, hj, "enthusiast/crowdsourced host; discovery lead only"
    if hj.is_official:
        if is_radio:
            return LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE, hj, f"official host + radio terms in title/url ({RADIO_TERMS.search(text).group(0)})"  # type: ignore[union-attr]
        if is_doc:
            return LeadClass.OFFICIAL_DOCUMENT_CANDIDATE, hj, "official host + document"
        return LeadClass.OFFICIAL_HOMEPAGE_CANDIDATE, hj, "official host; general page"
    if hj.is_official is None:
        if is_radio:
            return LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE, hj, "agency-named host (unconfirmed) + radio terms"
        return LeadClass.OFFICIAL_HOMEPAGE_CANDIDATE, hj, "agency-named host (unconfirmed)"
    if is_radio:
        return LeadClass.SECONDARY_LEAD, hj, "non-official host with radio terms"
    return LeadClass.UNRELATED, hj, "non-official host, no radio terms"


def title_mentions_agency(title: str | None, agency_name: str) -> bool:
    if not title:
        return False
    t = core_tokens(title)
    a = core_tokens(agency_name)
    return len(a) > 0 and len(t & a) / len(a) >= 0.6
