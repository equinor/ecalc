"""
Make sure that we use UUID7 for UUID generation,
and that it is backwards compatible with the stdlib UUID
"""

from uuid import UUID

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator


def test_ecalc_id_generator_returns_uuid7():
    """
    Even though the std lib UUID only supports until UUIDv5 in Python 3.12,
    the byte offset for the UUID version is the same for newer UUIDs, and
    they can thus be used as any other UUID
    Returns:

    """
    generated_id: UUID = ecalc_id_generator()
    assert generated_id.version == 7, f"Expected UUID version 7, got version {generated_id.version}"
