import re
from typing import Optional

from libecalc.dto.base import EcalcBaseModel

VERSION_FORMAT = r"^(\d+)(\.\d+)?(\.\d+)?$"


class Version(EcalcBaseModel):
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __init__(self, major: int = 0, minor: int = 0, patch: int = 0):
        super().__init__()
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def from_string(cls, version_string: Optional[str]) -> "Version":
        """From any version that has either major, minor or patch in string, get the full
        version with major, minor and patch set.

        If null, empty or invalid string, return Version 0.0.0

        :param version_string:
        :return:
        """
        if version_string is None:
            return Version()

        pattern = re.compile(VERSION_FORMAT)
        match = pattern.match(version_string)

        if match is None:
            return Version()

        if len(match.groups()):
            # NOTE! Group 0 is full (matched) expression
            major = int(match[1]) if match[1] is not None else 0
            minor = int(match[2][1:]) if match[2] is not None else 0
            patch = int(match[3][1:]) if match[3] is not None else 0
            return cls(major=major, minor=minor, patch=patch)
        else:
            # ignore wrong format for now, assume not set
            return Version()

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"Major: {self.major}\nMinor: {self.minor}\nPatch: {self.patch}"
