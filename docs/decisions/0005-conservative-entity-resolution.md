# ADR 0005 — Conservative entity resolution

**Status:** accepted (2026-09-20)

**Decision.** Auto-confirm only exact normalized-name + same-state matches. Reporting
sub-units ("Agency: County") link as *proposed sub-units*. Fuzzy candidates need core-token
Jaccard ≥ 0.6 and token-sort ratio ≥ 80, are stored as *proposed*, and multiple candidates
are *ambiguous* with competitors recorded. Unmatched records become their own agency.

**Evidence.** On the FBI 2018 roster: 54 confirmed, 1,183 sub-unit proposals, 10 fuzzy
proposals (all plausible-but-unproven, e.g. "State Troopers" → Alaska State Troopers;
"Indiana State Excise Police" → Indiana State Police correctly left unconfirmed), 0
ambiguous. Before tightening, token-set matching proposed Miami Beach PD → Miami PD and
Berkeley PD → UC Berkeley PD; those are now blocked and covered by tests.
