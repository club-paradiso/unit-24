# Evidence policy, version 2026-09-20.2

Government hosting, target identity, operative status and applicability are separate
claims. A search result, ranking, domain suffix or document date proves none of the
other claims. All evidence starts unverified.

Official classification requires acquired bytes, a hash, an eligible document type,
and reviewed identity evidence matching the source owner, canonical name, state and
host. Playback separately requires reviewed document-issuer evidence. Official non-.gov sites can qualify through a government directory or reviewed
agency page. Search candidates never set an agency website automatically.

Currentness is explicit: OFFICIAL_CURRENT_CONFIRMED, OFFICIAL_CURRENT_PRESUMED,
OFFICIAL_UNDATED, OFFICIAL_HISTORICAL, OFFICIAL_SUPERSEDED or CURRENTNESS_UNKNOWN.
A reviewed active portal/index or explicit operative-policy assertion may confirm
status; a revision alone is presumed. A recent effective date alone cannot confirm
status. Supersession and expired periods take precedence. Historical evidence stays
stored. Legacy OFFICIAL_CURRENT/PARTIAL quality fields are derived compatibility
fields; callers must evaluate the evidence, not trust an imported status string.

Evidence pointers carry source ID, locator, short excerpt, review state and reviewer.
A currentness claim is an observation on checked_on; it is not proof of future
currency. Confirmed observations require an explicit recheck_by date; expired or unspecified deadlines fall to presumed.

Corroboration requires distinct URLs, document hashes, issuing authorities and known,
disjoint evidence lineages. Unknown lineage is not independence. Mirrored bytes,
copied pages and repeated enthusiast tables cannot become authority. Even genuine
secondary corroboration remains RESEARCH_ONLY. Official evidence is preferred.

A parent, county, state or dispatch relationship grants no protocol inheritance.
Cross-agency facts need reviewed applicability evidence naming the source entity,
target, source document, fact types, exact fact keys and effective interval. Incomplete
membership lists do not authorize unlisted agencies or unrelated unit conventions.

No parser has earned automatic verification. All extracted candidates require
independent acceptance. A human review record must bind the fact ID, source ID, hash, normalized value, reviewer
and review date. A review enum alone is insufficient: playback also needs
hashed official evidence, confirmed currentness, identity, applicability, valid fact
dates, an excerpt and absence of unresolved conflicts. PLAYABLE_WITH_LIMITATIONS is
retained for compatibility but this policy does not award it. Model source comparison
in the audit is explicitly not HUMAN_ACCEPTED review.

Facts retain extraction rule/version and text method. Native PDF and HTML extraction
are demonstrated. Image-only PDFs are detected and blocked pending an OCR backend;
only the interface and synthetic page-locator behavior have been tested. Narrative
regex output and multi-column code tables remain research candidates.

Short excerpts and hashes are committed; full acquired third-party documents remain
in ignored local storage. Synthetic fixtures are authored for this project. Public
access only; no authentication, paywall, CAPTCHA or access-control circumvention.
