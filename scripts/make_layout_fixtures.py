"""Generate tiny synthetic PDFs that reproduce each layout failure found in the real corpus.

Every fixture is fictional and purpose-built. None reproduces a meaningful portion of a real
third-party document: the geometry is copied, the wording is not. Run:

    uv run python scripts/make_layout_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from radiocorpus.evaluation.pdfwrite import pdf, wrap

OUT = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "layout"


def column_streams(cols: list[tuple[float, float]], streams: list[list[str]], *, top: float, size: float, lead: float) -> list[tuple]:
    """Lay independent entry streams down each column, wrapping inside the column width."""
    runs: list[tuple] = []
    for (x, w), entries in zip(cols, streams, strict=False):
        y = top
        for entry in entries:
            for line in wrap(entry, size, w):
                runs.append((x, y, size, line))
                y -= lead
    return runs


# ---------------------------------------------------------------- fixtures

def fx_multicolumn_code_table() -> bytes:
    """Four independent columns; one cell wraps so its remainder lands beside the next code."""
    cols = [(40, 130), (180, 150), (340, 105), (450, 145)]
    streams = [
        ["10-2 Reception good", "10-4 Message received", "10-5 Relay message", "10-6 Busy stand by", "10-7 Out of service", "10-8 In service"],
        [
            "10-36A Confidential information subject possibly armed",
            "10-36F Confidential information possible felony wants",
            "10-37 What time is it",
        ],
        ["11-84 Direct traffic", "11-85 Tow truck", "11-86 Bomb threat", "11-87 Bomb found", "11-98 Meet"],
        ["23152 VC Misdemeanor drunk driving", "23153 VC Felony drunk driving", "187 PC Murder", "211 PC Robbery"],
    ]
    runs = [(40, 752, 12, "EXAMPLE STATE PATROL", "bold"), (40, 736, 9, "AURAL BREVITY CODES", "bold")]
    runs += column_streams(cols, streams, top=700, size=8, lead=11.0)
    return pdf([runs])


def fx_revision_table() -> bytes:
    """A revision history whose dates are shaped exactly like eleven-codes."""
    runs = [
        (40, 740, 11, "EXAMPLE POLICE DEPARTMENT", "bold"),
        (40, 724, 10, "DIRECTIVE 7.1 REVISION HISTORY", "bold"),
        (40, 700, 9, "Marker", "bold"),
        (110, 700, 9, "Number", "bold"),
        (190, 700, 9, "Date", "bold"),
        (280, 700, 9, "Description", "bold"),
        (40, 686, 9, "*3"),
        (110, 686, 9, "0172"),
        (190, 686, 9, "09-11-18"),
        (280, 686, 9, "Changes"),
        (40, 672, 9, "*4"),
        (110, 672, 9, "0181"),
        (190, 672, 9, "03-08-13"),
        (280, 672, 9, "Additions"),
        (40, 658, 9, "*5"),
        (110, 658, 9, "0190"),
        (190, 658, 9, "12-05-19"),
        (280, 658, 9, "Corrections"),
        (40, 620, 9, "Issued Date: 03-08-13   Effective Date: 03-08-13   Updated Date: 12-05-19"),
    ]
    return pdf([runs])


def fx_enumerated_headings() -> bytes:
    """Enumerated section headings whose letter+word shape mimics a phonetic alphabet."""
    runs = [
        (40, 742, 11, "EXAMPLE POLICE DEPARTMENT", "bold"),
        (40, 716, 10, "*5  C. COMMUNICATIONS FAILURE:", "bold"),
        (40, 698, 9, "Officers unable to reach the dispatcher will proceed to the nearest district."),
        (40, 672, 10, "A. Attempt to Locate messages are for non-criminal activity.", "bold"),
        (40, 646, 10, "B. Broadcasts relative to district-wide information shall be transmitted.", "bold"),
        (40, 620, 10, "D. Deployment of additional units requires supervisor approval.", "bold"),
    ]
    return pdf([runs])


def fx_local_alphabet() -> bytes:
    """A local alphabet matching APCO on 25 letters and diverging on one."""
    pairs = [
        ("A", "ADAM"), ("B", "BOY"), ("C", "CHARLES"), ("D", "DAVID"), ("E", "EDWARD"), ("F", "FRANK"),
        ("G", "GEORGE"), ("H", "HENRY"), ("I", "IDA"), ("J", "JOHN"), ("K", "KING"), ("L", "LINCOLN"),
        ("M", "MARY"), ("N", "NORA"), ("O", "OCEAN"), ("P", "PAUL"), ("Q", "QUEEN"), ("R", "ROBERT"),
        ("S", "SAM"), ("T", "TOM"), ("U", "UNION"), ("V", "VICTOR"), ("W", "WILLIAM"), ("X", "XRAY"),
        ("Y", "YOUNG"), ("Z", "ZULU"),  # local divergence: APCO reference says ZEBRA
    ]
    runs = [(40, 750, 11, "EXAMPLE COUNTY SHERIFF", "bold"), (40, 732, 10, "PHONETIC ALPHABET", "bold")]
    y = 706
    for i, (letter, word) in enumerate(pairs):
        col = 40 + (i // 13) * 220
        yy = y - (i % 13) * 14
        runs.append((col, yy, 9, f"{letter} {word}"))
    return pdf([runs])


def fx_footer_code_token() -> bytes:
    """A repeated footer carrying a code-shaped token on every page."""
    pages = []
    for n in (1, 2, 3):
        runs = [
            (40, 740, 11, "EXAMPLE POLICE DEPARTMENT", "bold"),
            (40, 716, 10, "SECTION 4 RADIO USE", "bold"),
            (40, 696, 9, f"Members will monitor the assigned radio channel during tour {n}."),
            (40, 44, 8, "Form 10-42 Rev. 3   Example Police Department   Communications Bureau"),
            (300, 30, 8, str(n)),
        ]
        pages.append(runs)
    return pdf(pages)


def fx_page_boundary_rule() -> bytes:
    """A rule whose qualifying exception sits at the top of the following page."""
    p1 = [
        (40, 740, 11, "EXAMPLE POLICE DEPARTMENT", "bold"),
        (40, 716, 10, "SECTION 6 RADIO BROADCAST FORMAT", "bold"),
        (40, 120, 9, "Members will broadcast the assignment over the radio until the dispatcher"),
        (40, 108, 9, "acknowledges the transmission at least three times using the required format."),
        (40, 44, 8, "Example Police Department   Directive 7.1"),
    ]
    p2 = [
        (40, 740, 9, "Members need not repeat the broadcast when a supervisor has already"),
        (40, 728, 9, "acknowledged the assignment on the same radio channel."),
        (40, 44, 8, "Example Police Department   Directive 7.1"),
    ]
    return pdf([p1, p2])


def fx_non_radio_copy_and_plate() -> bytes:
    """'copy' meaning a document, and 'plate' meaning impounded property."""
    runs = [
        (40, 742, 11, "EXAMPLE POLICE DEPARTMENT", "bold"),
        (40, 718, 10, "SECTION 9 REPORTS AND PROPERTY", "bold"),
        (40, 698, 9, "The incident report will be forwarded to the unit secretary, who will make one"),
        (40, 686, 9, "copy for the unit file and forward the original to the commanding officer."),
        (40, 662, 9, "NOTE: A copy will be retained in the unit files in accordance with existing"),
        (40, 650, 9, "records-retention requirements."),
        (40, 626, 9, "Members must have a license plate impounded with the vehicle and recorded on"),
        (40, 614, 9, "the property receipt before the tow operator removes it."),
    ]
    return pdf([runs])


def fx_repeated_header() -> bytes:
    """The same banner on every page: furniture, not content."""
    pages = []
    for n in (1, 2, 3):
        runs = [
            (40, 760, 9, "EXAMPLE POLICE DEPARTMENT - DIRECTIVE 7.1 - RADIO PROCEDURES"),
            (40, 730, 11, f"PART {n}", "bold"),
            (40, 706, 9, f"Officers shall advise the dispatcher of their location before leaving part {n}."),
            (40, 40, 8, f"Page {n} of 3"),
        ]
        pages.append(runs)
    return pdf(pages)


def fx_single_column_narrative() -> bytes:
    """A normal one-column policy page: column detection must NOT fire here."""
    body = (
        "Members assigned to a district will answer the radio when called by car number. "
        "When communication cannot be maintained by portable radio, members shall advise "
        "the dispatcher of their location and the reason for the out-of-service status. "
        "The dispatcher will repeat the assignment when a member requests it."
    )
    runs = [(40, 742, 11, "EXAMPLE STATE POLICE", "bold"), (40, 718, 10, "COMMUNICATIONS PROCEDURES", "bold")]
    y = 696
    for line in wrap(body, 9, 480):
        runs.append((40, y, 9, line))
        y -= 13
    return pdf([runs])


FIXTURES = {
    "lx01_multicolumn_code_table.pdf": fx_multicolumn_code_table,
    "lx02_revision_date_table.pdf": fx_revision_table,
    "lx03_enumerated_headings.pdf": fx_enumerated_headings,
    "lx04_local_alphabet_divergence.pdf": fx_local_alphabet,
    "lx05_footer_code_token.pdf": fx_footer_code_token,
    "lx06_page_boundary_rule.pdf": fx_page_boundary_rule,
    "lx07_non_radio_copy_and_plate.pdf": fx_non_radio_copy_and_plate,
    "lx08_repeated_header.pdf": fx_repeated_header,
    "lx09_single_column_narrative.pdf": fx_single_column_narrative,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in FIXTURES.items():
        (OUT / name).write_bytes(fn())
    print(f"wrote {len(FIXTURES)} layout fixtures to {OUT}")


if __name__ == "__main__":
    main()
