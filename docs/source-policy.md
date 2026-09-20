# Source policy

## Evidence hierarchy

Preferred, in order:

1. official agency policy / manual / general order (`agency_policy_manual`)
2. official dispatch-centre documentation (`dispatch_center_document`)
3. official city / county / state government documents (`government_document`)
4. official training / accreditation material (`training_accreditation`)
5. other governmental records (`other_government_record`)
6. standards bodies (APCO, FEMA/NIMS, NPSTC) (`standards_body`) — for interoperability rules only, never for an agency's own codes

Scanner-enthusiast sites, forums, wikis, crowdsourced code lists and social media
(`enthusiast_or_crowdsourced`, `social_media`) are **discovery leads only**. The `Source`
validator refuses to assign them any `OFFICIAL_*` quality. Search-engine results are always
`UNVERIFIED`.

## Quality states

| state | meaning | how assigned |
|---|---|---|
| `OFFICIAL_CURRENT` | official type, official host, bytes hashed, dated within 10 years, not superseded | `provenance/classify.py` |
| `OFFICIAL_HISTORICAL` | official, but superseded by a newer official source | supersession link |
| `OFFICIAL_PARTIAL` | official but undated, or dated more than 10 years ago | classifier |
| `SECONDARY_CORROBORATED` | reserved for reviewer use when ≥2 independent non-official sources agree; the policy tracks corroboration on the fact level | manual |
| `CONFLICTING` | reserved for reviewer use on a source known to contradict official sources | manual |
| `UNVERIFIED` | default for anything not acquired, non-official, or unclassifiable | default |
| `NO_PUBLIC_SOURCE` | discovery completed and nothing public exists | agency research status |

An `OFFICIAL_*` quality requires a document hash. A lead without bytes is never official.

## Host judgement

`discovery/classify.py::judge_host` returns **True** for government TLDs (.gov/.us/.mil) and
state portal hosts; **False** for a maintained list of non-official platforms (Wikipedia,
social media, Quizlet, RadioReference, PowerDMS public portals, Scribd, MuckRock, ACLU
mirrors...); **None** ("plausible, unproven") for agency-branded .org/.com/.edu hosts such as
`lapdonline.org` or `lasd.org`. Only True sets `official_website` on an agency, and only when
the search result title also names the agency. None keeps the field UNKNOWN.

## Currency

An undated official document is `OFFICIAL_PARTIAL` (playable with limitations), never
current. The effective-date parser (`normalization/temporal.py`) only accepts a date that
follows an explicit "Effective/Revised/Issued/Approved" hint; anything else stays `None`.

## Excerpts

Facts store at most 400 characters of verbatim text plus a locator (page or HTML path).
Acquired documents are stored content-addressed under `data/raw/documents/` and are
git-ignored; the corpus is not a document mirror.

## Ethics and access

Public information only. robots.txt is honoured; 401/403/407 are recorded and never retried;
no authentication, CAPTCHA, paywall or technical-restriction circumvention. Egress denials
from the build environment are recorded as `blocked_egress` with the reason so they can be
resumed from an environment with access.
