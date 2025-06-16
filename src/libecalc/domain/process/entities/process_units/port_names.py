"""Canonical port-name constants for process units."""

from __future__ import annotations


class SingleIO:
    """Default names for 1-in / 1-out units (valve, pump, compressor &)."""

    INLET = "inlet"
    OUTLET = "outlet"


# Leave placeholders for the future patterns
class MixerIO:
    """Port names for multiple in, one out units."""

    pass


class SplitterIO:
    """Port names for one in, multiple out units."""

    pass


class SeparatorIO:
    """Port names for one in, multiple phase outlets."""

    pass
