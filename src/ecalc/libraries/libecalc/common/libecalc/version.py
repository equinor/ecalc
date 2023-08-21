from libecalc.common.version import Version

# DO NOT EDIT - replaced in CI
__version__ = "8.3.0"  # x-release-please-version
# END DO NOT EDIT


def current_version() -> Version:
    """Get the current version of eCalc. This is set and
    built in in CICD pipeline. Locally it will always be 0.0.0
    :return:
    """
    return Version.from_string(__version__)
