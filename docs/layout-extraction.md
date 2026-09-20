# Layout-aware extraction

## Why the previous design failed

The old abstraction was `TextBlock(locator, text)`: one flattened string per page, addressed
as `p.16`. An independent review of four real documents found 61 of 116 candidate meanings
supported and 24 complete facts. Nearly every failure was a consequence of discarded
geometry rather than of a bad pattern:

| failure | real example | root cause |
|---|---|---|
| revision date read as a code | `*3 0172 09-11-18 Changes` → eleven-code `11-18` | no notion of a revision-history table |
| section heading read as a phonetic pair | `*5 C. COMMUNICATIONS FAILURE:` → `C → COMMUNICAT` | no notion of an enumerator, and a 10-character word cap |
| adjacent columns merged | `10-4 Message received armed 11-85 Tow truck` | four columns flattened into one line |
| wrapped cell lost | `10-36A Confidential information, subject possibly` (the word `armed` landed on the next code) | no cell continuation |
| page furniture ingested | footer text absorbed into a rule | no header/footer detection |
| rule truncated at a page break | broadcast format promised, then dropped | no cross-page context |
| records paperwork read as radio procedure | "a copy will be retained in the unit files" | keyword match with no medium test |

## The representation

`LayoutBlock` is the unit. It carries text plus: physical page, printed page number, reading
order, bounding box, block type (heading, paragraph, table cell, header, footer, list item,
unknown), column / table / row / cell identity, the backend that produced it, and
`structural_evidence` — the list of reasons for every structural claim it makes. Blocks that
are page furniture are marked `excluded` with a reason and **kept**, so suppression is
auditable rather than destructive.

Locators address a region, not a page:

```
p.2:tbl[1]:row[7]:col[2]@(180.0,85.7,292.0,93.7)
p.16@(40.0,120.5,300.2,132.5)
html:table[1]>tr[3]>cell[2]
```

They are stable: the same bytes and the same layout code always produce the same address, and
bounding boxes are serialised at full precision so a cache round-trip cannot move a fact.

## Segmentation

Every routine is biased toward the weaker answer. A document wrongly called single-column
loses precision in one table; a document wrongly called multi-column corrupts every line on
the page.

**Columns.** Word boxes are projected onto the x-axis, counting *lines* rather than words so
one wide title cannot outvote the body. A gutter is a band at least 12 pt wide that at least
85% of rows leave empty; columns are the bands between gutters, and each must carry text on
three or more rows. If most rows straddle a gutter, the page is single-column.

**Spanning lines.** A line whose own word spacing does not contain the gutter is a full-width
line — a banner or a note — and is kept intact rather than shredded across columns.

**Reading order** is column-major. The foot of column one is never joined to the head of
column two. Row identity is retained separately so a table can still be read across.

**Page furniture** needs cross-page evidence: a line in the outer 8% band whose *exact* text
repeats on at least half the pages, or whose digit-normalised form repeats *and* is shaped
like furniture (`Page 3 of 11`, a bare number, a revision stamp). The shape restriction is
what stops a numbered section heading being normalised into a repeat and suppressed.

**Paragraphs** are reassembled from wrapped lines, except where either line opens a list
entry — a code, an alphabet pair or an enumerator. Without that exception paragraph assembly
destroys code lists; with it, a rule split across two lines becomes one readable sentence.

**Records.** `assemble_records` groups blocks within a column lane, given a caller-supplied
"does this line open a record" predicate. A line that does not open a record continues the one
above it when the two are vertically adjacent. Text with no coordinates never continues
anything: without geometry we cannot show two lines were neighbours.

## Structural gating

### Codes

A candidate needs one of:

* `TABLE_CELL_PAIR` — the code alone in a cell, the meaning in the adjacent cell;
* `COLUMN_SERIES` — three or more records in one lane each opening with a code token;
* `CODE_TABLE_HEADING` — a heading naming a code list governs the block.

Rejected by shape, not by literal: a code token preceded by `digit-separator` or followed by
`separator-digit` sits inside a date; a revision label within 40 characters governs it;
statutory citations; structural cross-references; telephone numbers.

### Phonetics

`LETTER + WORD` is not a mapping. One of these must hold: a phonetic or alphabet heading
governs the region; the region is a table of pairs; or four or more distinct letters pair up
in the same region. List enumerators are rejected, including behind margin change-bars.

System labels are **descriptive metadata**. A local alphabet matching APCO on 25 letters and
diverging on one keeps all 26 local mappings; the divergence is reported in
`AlphabetReport.divergences` and never normalised away.

### Procedures

Four questions, all of which must pass:

* **Medium** — radio, or a telephone call, a form, a memo? Telephone and written media are
  rejected. The section heading can supply radio context the sentence omits.
* **Actor** — who is directed to act, or is the sentence imperative?
* **Act** — is there a communication verb, as opposed to motion or handling?
* **Object** — for topic-bound procedures, is the topic governed by the *nearest preceding*
  verb being a communication verb? "advise the RDC of their location" passes; "notify a
  supervisor to take the officer's location" does not, because `take` intervenes.

Candidates carry the section heading and path, the preceding and following sentence, and
`has_condition`, `has_exception`, `crosses_page` and `context_complete`. A clause ending in
`;` or `and` is one item of a continuing list and is marked incomplete, as is a clause whose
qualifying exception sits in the next sentence.

## Caching

Layout is cached by document hash. The key also contains the layout version **and a SHA-256
digest of the layout package source**, because a version constant can be forgotten. Editing
any layout module invalidates every entry automatically. This was not theoretical: during
development a paragraph-assembly change silently served stale layout until the fingerprint
was added.

The extraction stage's resume key pins the layout version, the layout fingerprint and all
three parser versions, so no run reuses progress from incompatible code.

## What is unchanged

OCR remains fail-closed: a PDF page with fewer than 20 native-text characters and embedded
images raises `OCRRequired` unless an OCR backend is explicitly supplied. Layout work never
enables OCR. No evidence, currency, eligibility or identity rule was touched; a better parser
produces better candidates, not authority.
