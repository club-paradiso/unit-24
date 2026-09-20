# ADR 0006 — pdfplumber as the position-aware PDF backend

**Status:** accepted (2026-09-20)

## Context

Extraction needs word coordinates, font metadata and page dimensions. `pypdf.extract_text`
returns a flattened string, which is what allowed a four-column brevity card to be read as
single lines and a revision date to be read as an eleven-code.

Two mature libraries expose the needed geometry:

| | licence | basis | geometry | speed |
|---|---|---|---|---|
| pdfplumber 0.11 | MIT | pdfminer.six (MIT) | words with x0/x1/top/bottom, fontname, size; page dims; table finder | pure Python, slower |
| PyMuPDF 1.28 | **AGPL-3.0 or Artifex commercial** | MuPDF | same, plus spans and more metadata | C, much faster |

Both were installed and exercised on a synthetic multi-column card before choosing.

## Decision

Use **pdfplumber**.

The deciding factor is licensing, not capability. This pipeline feeds a product intended to
ship to learners. AGPL-3.0 on the extraction path would either impose AGPL obligations on
that product or require an Artifex commercial licence; neither is a cost worth taking for a
speed gain on a workload where correctness dominates and documents are cached.

pdfplumber's word-level API is sufficient for everything the layout layer needs: column
detection, line clustering, cell assembly, header/footer detection and heading typography.
Its table finder is deliberately **not** used — it depends on ruling lines, and the
adversarial real document has none.

## Consequences

* Extraction is slower. Measured on the nine synthetic fixtures: 159 ms total, 6–76 ms per
  document. Real documents are larger; layout output is cached by content hash, so the cost
  is paid once per document version.
* `pypdf` is retained for the flattened fallback path and for the existing OCR gate, so the
  scanned-page contract is unchanged.
* If throughput later dominates, the backend is isolated behind
  `radiocorpus.layout.backends`; swapping it requires no parser change. Revisit only with a
  licence answer, not on speed alone.
