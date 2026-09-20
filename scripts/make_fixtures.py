"""Generate the synthetic fixture documents under data/fixtures/.

Everything here is FICTIONAL (state ZZ, made-up agencies and hosts). The documents exercise:
current vs historical official manuals, an undated manual, a dispatch-centre document that
disagrees with the agency's own policy, two equally dated official sources that disagree, a
secondary (enthusiast) page that disagrees with official policy, and an agency with no
documents at all. Run: uv run python scripts/make_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "data" / "fixtures"


def minimal_pdf(pages: list[list[str]]) -> bytes:
    """Text-only PDF (Helvetica) that pypdf can read. One content stream per page."""
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    pages_obj_index = len(objs) + 1 + 2 * len(pages)  # reserved after all page+content objects
    for lines in pages:
        esc = [ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for ln in lines]
        body = "BT /F1 11 Tf 14 TL 50 760 Td " + " ".join(f"({ln}) Tj T*" for ln in esc) + " ET"
        stream = body.encode("latin-1", errors="replace")
        content = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page = add(
            f"<< /Type /Page /Parent {pages_obj_index} 0 R /MediaBox [0 0 612 792] /Contents {content} 0 R /Resources << /Font << /F1 {font} 0 R >> >> >>".encode()
        )
        page_ids.append(page)
    pages_obj = add(("<< /Type /Pages /Kids [" + " ".join(f"{p} 0 R" for p in page_ids) + f"] /Count {len(page_ids)} >>").encode())
    assert pages_obj == pages_obj_index
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def html_codes_page() -> str:
    codes = [
        ("10-4", "Acknowledged"),
        ("10-7", "Out of service"),
        ("10-8", "In service"),
        ("10-9", "Repeat last transmission"),
        ("10-20", "Location"),
        ("10-33", "Emergency traffic"),
        ("10-50", "Traffic collision"),
        ("10-97", "Arrived on scene"),
    ]
    phon = [
        ("A", "Adam"),
        ("B", "Boy"),
        ("C", "Charles"),
        ("D", "David"),
        ("E", "Edward"),
        ("F", "Frank"),
        ("G", "George"),
        ("H", "Henry"),
        ("I", "Ida"),
        ("J", "John"),
        ("K", "King"),
        ("L", "Lincoln"),
        ("M", "Mary"),
        ("N", "Nora"),
        ("O", "Ocean"),
        ("P", "Paul"),
        ("Q", "Queen"),
        ("R", "Robert"),
        ("S", "Sam"),
        ("T", "Tom"),
        ("U", "Union"),
        ("V", "Victor"),
        ("W", "William"),
        ("X", "X-ray"),
        ("Y", "Young"),
        ("Z", "Zebra"),
    ]
    rows = "\n".join(f"<tr><td>{c}</td><td>{m}</td></tr>" for c, m in codes)
    prows = "\n".join(f"<tr><td>{letter}</td><td>{w}</td></tr>" for letter, w in phon)
    return f"""<!DOCTYPE html><html><head><title>Exampleville Police Department - Radio Communications Policy 4.10</title></head>
<body><h1>Exampleville Police Department</h1><h2>Policy 4.10 Radio Communications</h2>
<p>Effective: March 1, 2024. Supersedes General Order 2009-05.</p>
<h3>Section 4.10.2 Ten-Codes</h3>
<table id="codes"><tr><th>Code</th><th>Meaning</th></tr>
{rows}
</table>
<h3>Section 4.10.3 Phonetic Alphabet</h3>
<table id="phonetic"><tr><th>Letter</th><th>Word</th></tr>
{prows}
</table>
<h3>Section 4.10.4 Procedures</h3>
<p>Units shall read back all license plate numbers to the dispatcher using the phonetic alphabet.</p>
<p>Officers shall acknowledge every dispatch with their unit number followed by 10-4.</p>
<p>A request to repeat a transmission shall be made with 10-9; the dispatcher will repeat the entire message.</p>
<p>Vehicle descriptions shall be given in the order color, year, make, model, body style, and license plate.</p>
<p>During mutual aid operations with outside agencies, members shall use plain language and shall not use ten-codes.</p>
</body></html>"""


def main() -> None:
    FX.mkdir(parents=True, exist_ok=True)
    (FX / "fx001_exampleville_policy_4_10_2024.html").write_text(html_codes_page(), encoding="utf-8")
    (FX / "fx001_exampleville_general_order_2009.pdf").write_bytes(
        minimal_pdf(
            [
                [
                    "EXAMPLEVILLE POLICE DEPARTMENT",
                    "GENERAL ORDER 2009-05  RADIO PROCEDURES",
                    "Effective Date: May 1, 2009",
                    "",
                    "SECTION 3  TEN-CODES",
                    "10-4  Acknowledged",
                    "10-7  Out of service",
                    "10-8  In service",
                    "10-33  Emergency traffic",
                    "10-50  Vehicle accident",
                    "10-97  Arrived on scene",
                    "",
                    "SECTION 4  PROCEDURES",
                    "Units shall read back all license plate numbers to the dispatcher.",
                ]
            ]
        )
    )
    (FX / "fx001_scanner_site_codes.html").write_text(
        """<html><head><title>Exampleville PD scanner codes (fan page)</title></head>
<body><h1>Exampleville PD 10 codes</h1><p>Compiled by listeners; not official.</p>
<table><tr><td>10-4</td><td>Acknowledged</td></tr><tr><td>10-50</td><td>Officer down</td></tr><tr><td>10-33</td><td>Emergency traffic</td></tr></table>
</body></html>""",
        encoding="utf-8",
    )
    (FX / "fx002_example_county_so_policy_undated.pdf").write_bytes(
        minimal_pdf(
            [
                [
                    "EXAMPLE COUNTY SHERIFF'S OFFICE",
                    "POLICY 300  COMMUNICATIONS",
                    "",
                    "300.4 RADIO CODES",
                    "10-4  Acknowledged",
                    "10-7  Off duty",
                    "10-8  In service",
                    "10-97  Arrived on scene",
                    "",
                    "300.5 PHONETIC ALPHABET",
                    "A Alpha",
                    "B Bravo",
                    "C Charlie",
                    "D Delta",
                    "E Echo",
                    "F Foxtrot",
                    "G Golf",
                    "H Hotel",
                    "I India",
                    "J Juliett",
                    "K Kilo",
                    "L Lima",
                    "M Mike",
                    "N November",
                    "O Oscar",
                    "P Papa",
                    "Q Quebec",
                    "R Romeo",
                    "S Sierra",
                    "T Tango",
                    "U Uniform",
                    "V Victor",
                    "W Whiskey",
                    "X X-ray",
                    "Y Yankee",
                    "Z Zulu",
                ]
            ]
        )
    )
    (FX / "fx002_regional_dispatch_sop_2023.pdf").write_bytes(
        minimal_pdf(
            [
                [
                    "EXAMPLE COUNTY REGIONAL DISPATCH CENTER",
                    "STANDARD OPERATING PROCEDURE 12  RADIO CODES FOR SERVED AGENCIES",
                    "Revised: January 15, 2023",
                    "",
                    "10-4  Acknowledged",
                    "10-7  Out of service",
                    "10-8  In service",
                ]
            ]
        )
    )
    (FX / "fx003_example_state_patrol_manual_a_2021.pdf").write_bytes(
        minimal_pdf(
            [
                [
                    "EXAMPLE STATE PATROL",
                    "COMMUNICATIONS MANUAL  VOLUME A",
                    "Effective: June 1, 2021",
                    "",
                    "Signal 7  Dead person",
                    "Signal 20  Mental subject",
                    "10-4  Acknowledged",
                ]
            ]
        )
    )
    (FX / "fx003_example_state_patrol_manual_b_2021.pdf").write_bytes(
        minimal_pdf(
            [
                [
                    "EXAMPLE STATE PATROL",
                    "DISTRICT TRAINING BULLETIN  RADIO SIGNALS",
                    "Effective: June 1, 2021",
                    "",
                    "Signal 7  Fatal collision",
                    "Signal 20  Mental subject",
                    "10-4  Acknowledged",
                ]
            ]
        )
    )
    manifest = {
        "note": "All agencies, hosts, and documents here are fictional. State ZZ is reserved for fixtures.",
        "agencies": [
            {"fixture_id": "FX-001", "name": "Exampleville Police Department", "agency_type": "municipal_police", "dispatch_fixture_id": "FX-005"},
            {"fixture_id": "FX-002", "name": "Example County Sheriff's Office", "agency_type": "sheriff", "dispatch_fixture_id": "FX-005"},
            {"fixture_id": "FX-003", "name": "Example State Patrol", "agency_type": "highway_patrol"},
            {
                "fixture_id": "FX-004",
                "name": "Neighbor Township Police Department",
                "agency_type": "municipal_police",
                "dispatch_fixture_id": "FX-005",
            },
            {"fixture_id": "FX-005", "name": "Example County Regional Dispatch Center", "agency_type": "other"},
        ],
        "documents": [
            {
                "agency_fixture_id": "FX-001",
                "file": "fx001_exampleville_policy_4_10_2024.html",
                "content_type": "text/html",
                "url": "https://police.exampleville.zz.gov/policies/4-10-radio-communications",
                "title": "Policy 4.10 Radio Communications",
                "source_type": "agency_policy_manual",
                "issuing_authority": "Exampleville Police Department",
                "effective_date": "2024-03-01",
            },
            {
                "agency_fixture_id": "FX-001",
                "file": "fx001_exampleville_general_order_2009.pdf",
                "content_type": "application/pdf",
                "url": "https://police.exampleville.zz.gov/archive/go-2009-05.pdf",
                "title": "General Order 2009-05 Radio Procedures",
                "source_type": "agency_policy_manual",
                "issuing_authority": "Exampleville Police Department",
                "effective_date": "2009-05-01",
            },
            {
                "agency_fixture_id": "FX-001",
                "file": "fx001_scanner_site_codes.html",
                "content_type": "text/html",
                "url": "https://scanner-fans.example.net/exampleville-codes",
                "title": "Exampleville PD scanner codes (fan page)",
                "source_type": "enthusiast_or_crowdsourced",
                "official_host": False,
            },
            {
                "agency_fixture_id": "FX-002",
                "file": "fx002_example_county_so_policy_undated.pdf",
                "content_type": "application/pdf",
                "url": "https://sheriff.examplecounty.zz.gov/policy-300.pdf",
                "title": "Policy 300 Communications",
                "source_type": "agency_policy_manual",
                "issuing_authority": "Example County Sheriff's Office",
            },
            {
                "agency_fixture_id": "FX-002",
                "file": "fx002_regional_dispatch_sop_2023.pdf",
                "content_type": "application/pdf",
                "url": "https://dispatch.examplecounty.zz.gov/sop-12.pdf",
                "title": "SOP 12 Radio Codes for Served Agencies",
                "source_type": "dispatch_center_document",
                "issuing_authority": "Example County Regional Dispatch Center",
                "effective_date": "2023-01-15",
            },
            {
                "agency_fixture_id": "FX-003",
                "file": "fx003_example_state_patrol_manual_a_2021.pdf",
                "content_type": "application/pdf",
                "url": "https://patrol.zz.gov/manuals/comms-vol-a.pdf",
                "title": "Communications Manual Volume A",
                "source_type": "agency_policy_manual",
                "issuing_authority": "Example State Patrol",
                "effective_date": "2021-06-01",
            },
            {
                "agency_fixture_id": "FX-003",
                "file": "fx003_example_state_patrol_manual_b_2021.pdf",
                "content_type": "application/pdf",
                "url": "https://patrol.zz.gov/training/radio-signals-bulletin.pdf",
                "title": "District Training Bulletin Radio Signals",
                "source_type": "agency_policy_manual",
                "issuing_authority": "Example State Patrol",
                "effective_date": "2021-06-01",
            },
        ],
    }
    (FX / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("fixtures written to", FX)


if __name__ == "__main__":
    main()
