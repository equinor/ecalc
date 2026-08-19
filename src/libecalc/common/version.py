import re

from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import to_camel_case

VERSION_FORMAT = r"^(\d+)(\.\d+)?(\.\d+)?(rc\d+)?$"


class Version(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )
    major: int = 0
    minor: int = 0
    patch: int = 0
    release_candidate: int | None = None

    def __init__(self, major: int = 0, minor: int = 0, patch: int = 0, release_candidate: int | None = None):
        super().__init__()
        self.major = major
        self.minor = minor
        self.patch = patch
        self.release_candidate = release_candidate

    @classmethod
    def from_string(cls, version_string: str | None) -> "Version":
        """From any version that has either major, minor or patch in string, get the full
        version with major, minor and patch set.

        Release Candidate <rcN> is now supported as optional, after the vX.Y.Z
        The version string is still PEP440 compatible.
        Release Candidates should start with rc0. If not relevant, it
        is skipped entirely. It is only relevant for internal test/release
        candidates, that will eventually result in a vX.Y.Z release.

        If null, empty or invalid string, return Version 0.0.0

        :param version_string:
        :return:
        """
        if version_string is None:
            return cls()

        if version_string.lower().startswith("v"):
            version_string = version_string[1:]

        pattern = re.compile(VERSION_FORMAT)
        match = pattern.match(version_string)

        if match is None:
            return cls()

        if len(match.groups()):
            # NOTE! Group 0 is full (matched) expression
            major = int(match[1]) if match[1] is not None else 0
            minor = int(match[2][1:]) if match[2] is not None else 0
            patch = int(match[3][1:]) if match[3] is not None else 0
            release_candidate = int(match[4][2:]) if match[4] is not None else None
            return cls(major=major, minor=minor, patch=patch, release_candidate=release_candidate)
        else:
            # ignore wrong format for now, assume not set
            return cls()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.release_candidate is not None:
            return f"{base}rc{self.release_candidate}"
        return base

    def __repr__(self) -> str:
        base = f"Major: {self.major}\nMinor: {self.minor}\nPatch: {self.patch}"
        if self.release_candidate is not None:
            base += f"\nRelease Candidate: {self.release_candidate}"
        return base

    @property
    def _version_tuple(self) -> tuple[int, int, int, tuple[int, int]]:
        # No RC (released) is greater than any RC of the same base version.
        # Use (1, 0) for released (sorts higher) and (0, N) for rcN.
        if self.release_candidate is None:
            return self.major, self.minor, self.patch, (1, 0)
        return self.major, self.minor, self.patch, (0, self.release_candidate)

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple > other._version_tuple

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple >= other._version_tuple

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple < other._version_tuple

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple <= other._version_tuple

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple == other._version_tuple

    def __ne__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._version_tuple != other._version_tuple
