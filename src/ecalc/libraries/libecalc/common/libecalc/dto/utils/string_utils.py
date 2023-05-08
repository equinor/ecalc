import hashlib
from typing import Iterable, Set


def get_duplicates(names: Iterable[str]) -> Set[str]:
    seen = set()
    duplicates = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    return duplicates


def generate_id(*args: str) -> str:
    """Generate an id from one or more strings. The string is encoded to avoid it being used to get other info than
    the id, i.e. it should not be used to get the name of a consumer, even if the name might be used to create the id.

    If there are many strings they are joined together.
    """
    full_string = "-".join(args)
    return hashlib.md5(full_string.encode()).hexdigest()  # noqa: S324 - insecure hash for ids
