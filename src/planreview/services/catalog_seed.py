from __future__ import annotations

from datetime import date


def _record(
    *,
    id: str,
    issuer: str,
    family: str,
    code: str,
    version: str,
    title: str,
    publication_date: date | None,
    effective_date: date | None,
    status: str,
    citation: str,
    tags: list[str],
    source_url: str,
) -> dict:
    return {
        "id": id,
        "issuer": issuer,
        "family": family,
        "code": code,
        "version": version,
        "title": title,
        "publication_date": publication_date,
        "effective_date": effective_date,
        "status": status,
        "is_public_metadata": True,
        "citation": citation,
        "tags_csv": ",".join(tags),
        "source_url": source_url,
    }


def _status_for(version: str, latest_version: str) -> str:
    return "active" if version == latest_version else "archived"


def _title24_seed() -> list[dict]:
    editions = {
        "2016": (date(2016, 7, 1), date(2017, 1, 1)),
        "2019": (date(2019, 7, 1), date(2020, 1, 1)),
        "2022": (date(2022, 7, 1), date(2023, 1, 1)),
        "2025": (date(2025, 7, 1), date(2026, 1, 1)),
    }
    families = [
        ("part-1", "California Administrative Code", "Title 24 Part 1", "administrative"),
        ("part-2", "California Building Code", "Title 24 Part 2", "building"),
        ("part-2-5", "California Residential Code", "Title 24 Part 2.5", "residential"),
        ("part-3", "California Electrical Code", "Title 24 Part 3", "electrical"),
        ("part-4", "California Mechanical Code", "Title 24 Part 4", "mechanical"),
        ("part-5", "California Plumbing Code", "Title 24 Part 5", "plumbing"),
        ("part-6", "California Energy Code", "Title 24 Part 6", "energy"),
        ("part-8", "California Historical Building Code", "Title 24 Part 8", "historic"),
        ("part-9", "California Fire Code", "Title 24 Part 9", "fire"),
        (
            "part-10",
            "California Existing Building Code",
            "Title 24 Part 10",
            "existing-building",
        ),
        ("part-11", "California Green Building Standards Code", "Title 24 Part 11", "green"),
        (
            "part-12",
            "California Referenced Standards Code",
            "Title 24 Part 12",
            "referenced-standards",
        ),
    ]
    tag_map = {
        "administrative": ["administrative", "local", "permit", "california", "title24"],
        "building": ["building", "local", "permit", "california", "title24", "accessibility"],
        "residential": ["residential", "local", "permit", "california", "title24"],
        "electrical": ["electrical", "local", "permit", "california", "title24"],
        "mechanical": ["mechanical", "local", "permit", "california", "title24"],
        "plumbing": ["plumbing", "local", "permit", "california", "title24", "drainage"],
        "energy": ["energy", "local", "permit", "california", "title24"],
        "historic": ["historic", "local", "permit", "california", "title24"],
        "fire": ["fire", "local", "permit", "california", "title24", "life-safety"],
        "existing-building": ["building", "local", "permit", "california", "title24"],
        "green": ["green", "local", "permit", "california", "title24"],
        "referenced-standards": [
            "referenced-standards",
            "local",
            "permit",
            "california",
            "title24",
        ],
    }
    rows: list[dict] = []
    latest = "2025"
    for version, (publication_date, effective_date) in editions.items():
        for slug, title, code, tag_key in families:
            rows.append(
                _record(
                    id=f"ca-title24-{slug}-{version}",
                    issuer="CBSC",
                    family=title,
                    code=code,
                    version=version,
                    title=f"{version} {title}",
                    publication_date=publication_date,
                    effective_date=effective_date,
                    status=_status_for(version, latest),
                    citation=f"{version} {title} (Title 24, {code.replace('Title 24 ', '')})",
                    tags=tag_map[tag_key],
                    source_url="https://www.dgs.ca.gov/en/BSC/Codes",
                )
            )
    return rows


def _icc_seed() -> list[dict]:
    editions = {
        "2015": date(2014, 6, 1),
        "2018": date(2017, 9, 27),
        "2021": date(2020, 10, 1),
        "2024": date(2024, 1, 1),
    }
    families = [
        (
            "IBC",
            "International Building Code",
            ["building", "local", "permit", "model-code", "icc"],
        ),
        (
            "IFC",
            "International Fire Code",
            ["fire", "local", "permit", "model-code", "icc", "life-safety"],
        ),
        (
            "IMC",
            "International Mechanical Code",
            ["mechanical", "local", "permit", "model-code", "icc"],
        ),
        (
            "IPC",
            "International Plumbing Code",
            ["plumbing", "local", "permit", "model-code", "icc", "drainage"],
        ),
        (
            "IECC",
            "International Energy Conservation Code",
            ["energy", "local", "permit", "model-code", "icc"],
        ),
        (
            "IEBC",
            "International Existing Building Code",
            ["building", "local", "permit", "model-code", "icc"],
        ),
        (
            "IRC",
            "International Residential Code",
            ["residential", "local", "permit", "model-code", "icc"],
        ),
        (
            "IFGC",
            "International Fuel Gas Code",
            ["mechanical", "fuel-gas", "local", "permit", "model-code", "icc"],
        ),
        (
            "IPMC",
            "International Property Maintenance Code",
            ["maintenance", "local", "permit", "model-code", "icc"],
        ),
        (
            "ISPSC",
            "International Swimming Pool and Spa Code",
            ["pool", "local", "permit", "model-code", "icc"],
        ),
        (
            "IgCC",
            "International Green Construction Code",
            ["green", "local", "permit", "model-code", "icc"],
        ),
    ]
    rows: list[dict] = []
    latest = "2024"
    for version, effective_date in editions.items():
        for code, title, tags in families:
            rows.append(
                _record(
                    id=f"{code.lower().replace('g', 'g').replace('.', '-')}-{version}",
                    issuer="ICC",
                    family=code,
                    code=code,
                    version=version,
                    title=title,
                    publication_date=effective_date,
                    effective_date=effective_date,
                    status=_status_for(version, latest),
                    citation=f"{code} {version}",
                    tags=tags,
                    source_url=f"https://codes.iccsafe.org/content/{code}{version}",
                )
            )
    rows.extend(
        [
            _record(
                id="icc-a1171-2009",
                issuer="ICC",
                family="ICC A117.1",
                code="ICC A117.1",
                version="2009",
                title="Accessible and Usable Buildings and Facilities",
                publication_date=date(2009, 1, 1),
                effective_date=date(2009, 1, 1),
                status="archived",
                citation="ICC A117.1-2009",
                tags=["accessibility", "local", "permit", "icc"],
                source_url="https://codes.iccsafe.org/",
            ),
            _record(
                id="icc-a1171-2017",
                issuer="ICC",
                family="ICC A117.1",
                code="ICC A117.1",
                version="2017",
                title="Accessible and Usable Buildings and Facilities",
                publication_date=date(2017, 1, 1),
                effective_date=date(2017, 1, 1),
                status="archived",
                citation="ICC A117.1-2017",
                tags=["accessibility", "local", "permit", "icc"],
                source_url="https://codes.iccsafe.org/",
            ),
            _record(
                id="icc-a1171-2023",
                issuer="ICC",
                family="ICC A117.1",
                code="ICC A117.1",
                version="2023",
                title="Accessible and Usable Buildings and Facilities",
                publication_date=date(2023, 1, 1),
                effective_date=date(2023, 1, 1),
                status="active",
                citation="ICC A117.1-2023",
                tags=["accessibility", "local", "permit", "icc"],
                source_url="https://codes.iccsafe.org/",
            ),
        ]
    )
    return rows


def _nfpa_seed() -> list[dict]:
    family_editions = {
        "NFPA 1": [
            ("2015", date(2015, 1, 1)),
            ("2018", date(2018, 1, 1)),
            ("2021", date(2021, 1, 1)),
            ("2024", date(2024, 1, 1)),
        ],
        "NFPA 13": [
            ("2016", date(2016, 1, 1)),
            ("2019", date(2019, 1, 1)),
            ("2022", date(2022, 1, 1)),
            ("2025", date(2025, 1, 1)),
        ],
        "NFPA 14": [
            ("2016", date(2016, 1, 1)),
            ("2019", date(2019, 1, 1)),
            ("2024", date(2024, 1, 1)),
        ],
        "NFPA 20": [
            ("2016", date(2016, 1, 1)),
            ("2019", date(2019, 1, 1)),
            ("2022", date(2022, 1, 1)),
            ("2025", date(2025, 1, 1)),
        ],
        "NFPA 25": [
            ("2017", date(2017, 1, 1)),
            ("2020", date(2020, 1, 1)),
            ("2023", date(2023, 1, 1)),
        ],
        "NFPA 70": [
            ("2017", date(2017, 1, 1)),
            ("2020", date(2020, 1, 1)),
            ("2023", date(2023, 1, 1)),
        ],
        "NFPA 72": [
            ("2016", date(2016, 1, 1)),
            ("2019", date(2019, 1, 1)),
            ("2022", date(2022, 1, 1)),
            ("2025", date(2025, 1, 1)),
        ],
        "NFPA 101": [
            ("2015", date(2015, 1, 1)),
            ("2018", date(2018, 1, 1)),
            ("2021", date(2021, 1, 1)),
            ("2024", date(2024, 1, 1)),
        ],
        "NFPA 110": [
            ("2016", date(2016, 1, 1)),
            ("2019", date(2019, 1, 1)),
            ("2022", date(2022, 1, 1)),
            ("2025", date(2025, 1, 1)),
        ],
        "NFPA 780": [
            ("2017", date(2017, 1, 1)),
            ("2020", date(2020, 1, 1)),
            ("2023", date(2023, 1, 1)),
        ],
    }
    titles = {
        "NFPA 1": ("Fire Code", ["fire", "local", "permit", "nfpa", "life-safety"]),
        "NFPA 13": (
            "Standard for the Installation of Sprinkler Systems",
            ["fire", "sprinkler", "local", "permit", "nfpa"],
        ),
        "NFPA 14": (
            "Standard for the Installation of Standpipe and Hose Systems",
            ["fire", "standpipe", "local", "permit", "nfpa"],
        ),
        "NFPA 20": (
            "Standard for the Installation of Stationary Pumps for Fire Protection",
            ["fire", "pump", "local", "permit", "nfpa"],
        ),
        "NFPA 25": (
            (
                "Standard for the Inspection, Testing, and Maintenance of "
                "Water-Based Fire Protection Systems"
            ),
            ["fire", "maintenance", "local", "permit", "nfpa"],
        ),
        "NFPA 70": (
            "National Electrical Code",
            ["electrical", "local", "permit", "nfpa", "model-code"],
        ),
        "NFPA 72": (
            "National Fire Alarm and Signaling Code",
            ["fire", "alarm", "local", "permit", "nfpa"],
        ),
        "NFPA 101": (
            "Life Safety Code",
            ["life-safety", "building", "local", "permit", "nfpa"],
        ),
        "NFPA 110": (
            "Standard for Emergency and Standby Power Systems",
            ["electrical", "backup-power", "local", "permit", "nfpa"],
        ),
        "NFPA 780": (
            "Standard for the Installation of Lightning Protection Systems",
            ["electrical", "lightning", "local", "permit", "nfpa"],
        ),
    }
    rows: list[dict] = []
    latest = {
        "NFPA 1": "2024",
        "NFPA 13": "2025",
        "NFPA 14": "2024",
        "NFPA 20": "2025",
        "NFPA 25": "2023",
        "NFPA 70": "2023",
        "NFPA 72": "2025",
        "NFPA 101": "2024",
        "NFPA 110": "2025",
        "NFPA 780": "2023",
    }
    for code, editions in family_editions.items():
        title, tags = titles[code]
        family = "NEC" if code == "NFPA 70" else code
        for version, effective_date in editions:
            rows.append(
                _record(
                    id=f"{code.lower().replace(' ', '').replace('.', '')}-{version}",
                    issuer="NFPA",
                    family=family,
                    code=code,
                    version=version,
                    title=title,
                    publication_date=effective_date,
                    effective_date=effective_date,
                    status=_status_for(version, latest[code]),
                    citation=f"{code} {version}" + (" (NEC)" if code == "NFPA 70" else ""),
                    tags=tags,
                    source_url="https://www.nfpa.org/codes-and-standards",
                )
            )
    return rows


def _ada_seed() -> list[dict]:
    return [
        _record(
            id="ada-2010",
            issuer="DOJ",
            family="ADA",
            code="2010 ADA Standards",
            version="2010",
            title="2010 ADA Standards for Accessible Design",
            publication_date=date(2010, 9, 15),
            effective_date=date(2012, 3, 15),
            status="active",
            citation="2010 ADA Standards",
            tags=["accessibility", "local", "federal", "ada"],
            source_url="https://www.ada.gov/law-and-regs/design-standards/2010-stds/",
        ),
        _record(
            id="ada-titleii-2010",
            issuer="DOJ",
            family="ADA Title II",
            code="28 CFR Part 35",
            version="2010 rule",
            title="Revised ADA Regulations Implementing Title II",
            publication_date=date(2010, 9, 15),
            effective_date=date(2010, 9, 15),
            status="active",
            citation="28 CFR Part 35 / ADA Title II",
            tags=["accessibility", "federal", "ada"],
            source_url="https://www.ada.gov/law-and-regs/design-standards/2010-stds/",
        ),
        _record(
            id="ada-titleiii-2010",
            issuer="DOJ",
            family="ADA Title III",
            code="28 CFR Part 36",
            version="2010 rule",
            title="Revised ADA Regulations Implementing Title III",
            publication_date=date(2010, 9, 15),
            effective_date=date(2010, 9, 15),
            status="active",
            citation="28 CFR Part 36 / ADA Title III",
            tags=["accessibility", "federal", "ada"],
            source_url="https://www.ada.gov/law-and-regs/design-standards/2010-stds/",
        ),
    ]


def _federal_seed() -> list[dict]:
    return [
        _record(
            id="ufc-1-200-01-2022",
            issuer="DoD",
            family="UFC",
            code="UFC 1-200-01",
            version="2022",
            title="General Building Requirements",
            publication_date=date(2022, 6, 1),
            effective_date=date(2022, 6, 1),
            status="active",
            citation="UFC 1-200-01 (2022)",
            tags=["federal", "military", "ufc", "dod", "building"],
            source_url="https://www.wbdg.org/dod/ufc",
        ),
        _record(
            id="ufgs-26-05-19-2024",
            issuer="DoD",
            family="UFGS",
            code="UFGS 26 05 19",
            version="2024",
            title="Low-Voltage Electrical Power Conductors and Cables",
            publication_date=date(2024, 5, 1),
            effective_date=date(2024, 5, 1),
            status="active",
            citation="UFGS 26 05 19 (2024)",
            tags=["federal", "military", "electrical", "ufgs", "dod"],
            source_url="https://www.wbdg.org/ffc/dod/unified-facilities-guide-specifications-ufgs",
        ),
        _record(
            id="faa-std-019f-chg2",
            issuer="FAA",
            family="FAA STD 019",
            code="FAA-STD-019f",
            version="Chg 2",
            title=(
                "Lightning and Surge Protection, Grounding, Bonding, and Shielding "
                "Requirements for Facilities and Electronic Equipment"
            ),
            publication_date=date(2018, 7, 1),
            effective_date=date(2018, 7, 1),
            status="archived",
            citation="FAA-STD-019f, Chg 2",
            tags=["faa", "federal", "aviation", "electrical"],
            source_url="https://www.faa.gov/",
        ),
        _record(
            id="faa-std-019f-chg3",
            issuer="FAA",
            family="FAA STD 019",
            code="FAA-STD-019f",
            version="Chg 3",
            title=(
                "Lightning and Surge Protection, Grounding, Bonding, and Shielding "
                "Requirements for Facilities and Electronic Equipment"
            ),
            publication_date=date(2021, 11, 15),
            effective_date=date(2021, 11, 15),
            status="active",
            citation="FAA-STD-019f, Chg 3",
            tags=["faa", "federal", "aviation", "electrical"],
            source_url="https://www.faa.gov/",
        ),
        _record(
            id="faa-ac-150-5370-10h",
            issuer="FAA",
            family="FAA AC 150/5370-10",
            code="AC 150/5370-10",
            version="H",
            title="Standards for Specifying Construction of Airports",
            publication_date=date(2024, 2, 16),
            effective_date=date(2024, 2, 16),
            status="active",
            citation="FAA AC 150/5370-10H",
            tags=["faa", "federal", "aviation", "airport"],
            source_url="https://www.faa.gov/airports/engineering/design_standards/",
        ),
        _record(
            id="osha-1910",
            issuer="OSHA",
            family="29 CFR 1910",
            code="29 CFR 1910",
            version="2024",
            title="Occupational Safety and Health Standards",
            publication_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 1),
            status="active",
            citation="29 CFR 1910",
            tags=["safety", "federal", "osha"],
            source_url="https://www.osha.gov/laws-regs/regulations/standardnumber/1910",
        ),
        _record(
            id="epa-swm-2024",
            issuer="EPA",
            family="EPA",
            code="SWMM",
            version="2024",
            title="Storm Water Management Model Guidance",
            publication_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 1),
            status="active",
            citation="EPA SWMM guidance",
            tags=["stormwater", "drainage", "federal"],
            source_url="https://www.epa.gov/water-research/storm-water-management-model-swmm",
        ),
        _record(
            id="asce7-16",
            issuer="ASCE",
            family="ASCE 7",
            code="ASCE 7",
            version="7-16",
            title="Minimum Design Loads and Associated Criteria for Buildings and Other Structures",
            publication_date=date(2016, 6, 30),
            effective_date=date(2017, 1, 1),
            status="archived",
            citation="ASCE 7-16",
            tags=["structural", "loads", "building"],
            source_url="https://ascelibrary.org/",
        ),
        _record(
            id="asce7-22",
            issuer="ASCE",
            family="ASCE 7",
            code="ASCE 7",
            version="7-22",
            title="Minimum Design Loads and Associated Criteria for Buildings and Other Structures",
            publication_date=date(2021, 12, 1),
            effective_date=date(2022, 1, 1),
            status="active",
            citation="ASCE 7-22",
            tags=["structural", "loads", "building"],
            source_url="https://ascelibrary.org/",
        ),
    ]


def build_seed_catalog() -> list[dict]:
    rows = []
    rows.extend(_title24_seed())
    rows.extend(_icc_seed())
    rows.extend(_nfpa_seed())
    rows.extend(_ada_seed())
    rows.extend(_federal_seed())
    rows.sort(key=lambda item: (item["issuer"], item["family"], item["effective_date"] or date.min))
    return rows
