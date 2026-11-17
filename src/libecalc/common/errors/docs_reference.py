from dataclasses import dataclass
from enum import StrEnum


class DocsPage(StrEnum):
    """
    A page in the eCalc docs, as its path below the docs root, e.g. https://equinor.github.io/ecalc/docs/<path>.

    Each page is checked against the built docs by src/check_docs_links.py.
    """

    MIGRATE_COMPRESSOR_SAMPLED = "about/nextgen/migrate-compressor-sampled"


@dataclass(frozen=True)
class DocsReference:
    """
    A reference from an error to the docs. The docs base URL depends on where eCalc runs, so it is given when rendering,
    e.g. https://equinor.github.io/ecalc for the latest release or https://equinor.github.io/ecalc/v15.7 for a version.
    """

    page: DocsPage
    message: str

    def get_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/docs/{self.page}"

    def render(self, base_url: str) -> str:
        return f"{self.message}: {self.get_url(base_url)}"
