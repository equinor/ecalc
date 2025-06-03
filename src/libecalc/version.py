from libecalc.common.version import Version

# DO NOT EDIT - replaced in CI with release please
__version__ = "9.17.4"  # x-release-please-version
# END DO NOT EDIT


def current_version() -> Version:
    """Get the current version of eCalc. This is set and
    built in the CICD pipeline.
    :return:
    """
    return Version.from_string(__version__)
