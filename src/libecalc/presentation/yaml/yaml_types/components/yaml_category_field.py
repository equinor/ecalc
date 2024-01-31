from typing import Any

from pydantic import Field


def CategoryField(default: Any, validate_default: bool = False) -> Field:
    return Field(
        default,
        title="CATEGORY",
        description="Output category/tag.\n\n$ECALC_DOCS_KEYWORDS_URL/CATEGORY",
    )
