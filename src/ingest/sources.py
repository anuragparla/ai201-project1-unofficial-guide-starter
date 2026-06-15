"""Registry of the 10 document sources for the Student Housing RAG.

Mirrors the Documents table in planning.md. Each entry carries the metadata
that travels with every chunk downstream (source / url / doc_type / source_date),
plus the `kind` that tells the ingester which parser to use.

kind:      html | pdf | reddit | mbta   -> selects the parser
doc_type:  official | law | forum | transit  -> authority signal used at retrieval
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: int
    slug: str           # short filename-safe id, e.g. "01_neu_offcampus"
    name: str           # human-readable name (matches planning.md)
    kind: str           # html | pdf | reddit | mbta
    doc_type: str       # official | law | forum | transit
    url: str
    source_date: str    # publication / access year, for the freshness challenge
    columns: int = 1    # PDF column count; >1 triggers column-aware extraction


SOURCES = [
    Source(
        id=1,
        slug="01_neu_offcampus_guidelines",
        name="Northeastern Off-Campus Housing Guidelines",
        kind="html",
        doc_type="official",
        url="https://offcampus.housing.northeastern.edu/explore-housing-options/bostonareahousing/",
        source_date="2025",
    ),
    Source(
        id=2,
        slug="02_neu_residence_hall_guide",
        name="Northeastern Guide to Residence Hall Living",
        kind="pdf",
        doc_type="official",
        url="https://housing.northeastern.edu/wp-content/uploads/2025/08/Guide-to-Residence-Hall-Living-AY25-26-Final.pdf",
        source_date="2025",
    ),
    Source(
        id=3,
        slug="03_ogs_housing_guide",
        name="Office of Global Services (OGS) Housing Guide",
        kind="html",
        doc_type="official",
        url="https://international.northeastern.edu/ogs/housing/",
        source_date="2025",
    ),
    Source(
        id=4,
        slug="04_network_relocation_intl",
        name="Network Housing Relocation - International Resources",
        kind="html",
        doc_type="official",
        url="https://network.housing.northeastern.edu/relocation-resources/resources-for-international-students/",
        source_date="2025",
    ),
    Source(
        id=5,
        slug="05_reddit_neu_housing",
        name="r/NEU Housing & Roommate Megathread",
        kind="reddit",
        doc_type="forum",
        # Subreddit search for housing posts; there is no single stable megathread URL.
        url="https://www.reddit.com/r/NEU/search.json?q=housing&restrict_sr=1&sort=top&t=all&limit=25",
        source_date="2025",
    ),
    Source(
        id=6,
        slug="06_reddit_boston_housing_wiki",
        name="r/boston Housing Wiki",
        kind="reddit",
        doc_type="forum",
        url="https://www.reddit.com/r/boston/wiki/housing.json",
        source_date="2025",
    ),
    Source(
        id=7,
        slug="07_ma_ag_tenant_rights",
        name="Massachusetts AG Guide to Landlord and Tenant Rights",
        kind="pdf",
        doc_type="law",
        url="https://www.mass.gov/doc/2025-guide-to-landlord-tenant-rights-11182025/download",
        source_date="2025",
    ),
    Source(
        id=8,
        slug="08_neu_leasing_zoning",
        name="Northeastern Leasing Information & Boston Zoning Rules",
        kind="html",
        doc_type="official",
        url="https://offcampus.housing.northeastern.edu/get-started/leasing-information/",
        source_date="2025",
    ),
    Source(
        id=9,
        slug="09_gbreb_standard_lease",
        name="Standard Greater Boston Real Estate Board (GBREB) Lease",
        kind="pdf",
        doc_type="official",
        url="https://freeforms.com/wp-content/uploads/2021/04/Greater-Boston-Real-Estate-Board-Standard-Form-Apartment-Lease.pdf",
        source_date="2021",
    ),
    Source(
        id=10,
        slug="10_mbta_subway",
        name="MBTA Subway Map and Schedules",
        kind="mbta",
        doc_type="transit",
        # We pull structured route/stop data from the MBTA v3 API instead of the
        # JS-rendered schedules page, then normalize it to natural-language facts.
        url="https://api-v3.mbta.com",
        source_date="2025",
    ),
    Source(
        id=11,
        slug="11_neu_intl_apartment_guide",
        name="Northeastern International Student Apartment Guide",
        kind="pdf",
        doc_type="official",
        # Manually-provided NEU OGS brochure; ingested from documents/raw/.
        url="https://international.northeastern.edu/ogs/housing/",
        source_date="2023",
        columns=3,  # landscape three-column brochure — extract each column separately
    ),
]


def get_sources(only_ids=None, only_kinds=None):
    """Return sources, optionally filtered by id list or kind list."""
    out = SOURCES
    if only_ids:
        out = [s for s in out if s.id in set(only_ids)]
    if only_kinds:
        out = [s for s in out if s.kind in set(only_kinds)]
    return out
