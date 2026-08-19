"""Extract parts of a version string.

Convenience script for CICD etc to parse a compatible version string,
and reuse functionality we already have in libecalc.

Ideally, I think that we might want to extract this into a shared/
dir that we have access in different circumstances for libecalc etc,
that we copy into the library when we build it, instead of having it
as an external dependency. Ie build dependency only, not runtime
dependency. In that case, it is also easier to keep it independent,
and to avoid incorrect dependencies that breaks when we use it,
because it depends on some internal libecalc core/common etc. And to have
separate and independent tests that prove its correctness.

Usage:
    python get_libecalc_version.py version_string=1.2.3rc1 --get-major
    python get_libecalc_version.py version_string=1.2.3rc1 --get-minor
    python get_libecalc_version.py version_string=1.2.3rc1 --get-patch
    python get_libecalc_version.py version_string=1.2.3rc1 --get-release-candidate
    python get_libecalc_version.py version_string=1.2.3rc1 --is-prerelease
"""

import sys
from common.version import Version  # NOTE: Need either to add to syspath OR copy locally to access


def main():
    version_string = None
    command = None

    # Very simple ad-hoc arg parsing, might want to use argparse instead to make it
    # easier and more readabl.e
    for arg in sys.argv[1:]:
        if arg.startswith("version_string="):
            version_string = arg.split("=", 1)[1]
        elif arg.startswith("--get-") or arg.startswith("--is-"):
            command = arg
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)

    if version_string is None or command is None:
        print("Usage: python get_libecalc_version.py version_string=<version> --get-<part>", file=sys.stderr)
        sys.exit(1)

    version = Version.from_string(version_string)

    match command:
        case "--get-full-version":
            print(version)
        case "--get-major":
            print(version.major)
        case "--get-minor":
            print(version.minor)
        case "--get-patch":
            print(version.patch)
        case "--get-release-candidate":
            print(version.release_candidate if version.release_candidate is not None else "")
        case "--get-major-minor":
            print(f"{version.major}.{version.minor}")
        case "--is-prerelease":
            print("true" if version.release_candidate is not None else "false")
        case _:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
