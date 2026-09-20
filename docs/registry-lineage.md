# Registry lineage and currency

Keep the 2018 FBI reporting-unit snapshot intact. ORIs can denote reporting subunits;
absence from a snapshot does not prove an agency was dissolved. A new name does not
prove legal continuity or shared protocol.

Use independent immutable registry namespaces, for example `CA_POST_2026_09_20` and
`FBI_CDE_FRONTEND_2018`, plus external ID, snapshot date, retrieval URL, artifact hash,
coverage definition and raw payload. The existing registry table keys namespace/ID;
the new collision guard rejects changed rows inside one snapshot. Agency links retain
confirmed/proposed/ambiguous status. Do not overwrite historical rows or auto-confirm
renames. Record valid dates only from primary transition evidence. For a split/merge,
keep distinct agencies and a documented relationship; do not redirect old protocol facts.

The current [California POST directory](https://post.ca.gov/le-agencies) provides
identity links and specific contract/organizational notes. It is participation-scoped,
not a complete nationwide census. The [BJS CSLLEA page](https://bjs.ojp.gov/data-collection/census-state-and-local-law-enforcement-agencies-csllea)
was inspected; its listed 2018 coverage does not replace the old snapshot with a current
roster. A national current public machine-readable replacement was not established.

[Machine-readable observations](../data/audit/registry_currency.json) distinguish
observed identities from unverified transition dates. California's directory explicitly
separates Berkeley city and university agencies, identifies a former department name,
and records contract-service relationships. Those observations never authorize shared
radio protocol. Miami-Dade's [current official site](https://www.mdso.com/) identifies a
sheriff's office; this does not identify Miami municipal police.

Still required: hashed state-directory snapshots, official formation/dissolution/merger
instruments, and reviewed temporal entity links. The inspected DCC page establishes a
current enforcement division, not its formation date. Unsuccessful searches and inaccessible
pages were not converted into historical claims.
