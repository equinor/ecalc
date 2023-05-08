import pytest
from libecalc.common.version import Version

data = [
    # negative integers
    (None, Version(0, 0, 0)),
    ("", Version(0, 0, 0)),
    ("weird", Version(0, 0, 0)),
    ("0.0.0", Version(0, 0, 0)),
    ("-1.-2.0", Version(0, 0, 0)),
    ("1.1.1", Version(1, 1, 1)),
    ("10.10.10", Version(10, 10, 10)),
    ("100.100.100", Version(100, 100, 100)),
    ("100.100", Version(100, 100, 0)),
    ("100", Version(100, 0, 0)),
    ("0", Version(0, 0, 0)),
    ("0.1.2", Version(0, 1, 2)),
]


@pytest.mark.parametrize(
    "version_string, expected_version",
    data,
)
def test_versions(version_string, expected_version):
    assert Version.from_string(version_string) == expected_version
