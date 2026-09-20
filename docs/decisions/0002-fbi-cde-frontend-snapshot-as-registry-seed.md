# ADR 0002 — Use the FBI CDE frontend roster (2018-06-28) as the reachable nationwide seed

**Status:** accepted (2026-09-20), to be superseded when CSLLEA/LEAR/API files are loaded

**Context.** BJS/ICPSR/FBI API hosts were egress-blocked in the build session. GitHub was
reachable. The FBI's own CDE frontend repository (org `fbi-cde`) contains
`agencies-by-state.json.gz`, 23,243 ORI-keyed reporting entities, committed 2018-06-28.

**Decision.** Load it as registry code `FBI_CDE_FRONTEND_2018` with a hash manifest. Treat
each row as a UCR reporting entity, not an agency; state police per-county rows are linked to
their agency as proposed sub-units. Never present its counts as current.

**Consequences.** Nationwide identity coverage exists today, dated 2018. Newer registries
are added as new registry codes; nothing is overwritten. The 2018 rows will need
retirement/merge review against CSLLEA 2018 and the live API.
