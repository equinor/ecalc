from libecalc.common.version import Version

# DO NOT EDIT - replaced in CI with release please
__version__ = "15.5.0"  # x-release-please-version
# END DO NOT EDIT


def current_version() -> Version:
    """Get the current version of eCalc. This is set and
    built in the CICD pipeline.
    :return:
    """
    return Version.from_string(__version__)


"""
Every change among YAML elements, should be reflected in a new version of the YAML document.
We try to follow semantic versioning as closely as possible, but we allow for interpretation
whether a change is major, minor or patch.

We only track major schema versions of the document, and therefore only allows the users to
specify major version in the YAML itself. The version they specify is therefore a range and not a specific version.
For example, if the user specifies VERSION: 2, it means "any 2.x.y",
 and will match any root element that is available in any 2.x.y version of the document.

General considerations for versioning:
Major: breaking changes, e.g. removing a root element, changing the type of a field, changing the meaning of a field. This will lead to a new schema version of the document
Minor: new features, e.g. adding a new root element, adding a new field to an existing root element. This will NOT lead to a new schema version of the document, but will update the major one.
Patch: bug fixes, e.g. fixing a typo in a description, fixing a validation rule. This will NOT lead to a (visibly) new schema version of the document, but will update the major one.

Initially we start with v2 as the first version of the document, since that will allow v1 and v2 elements to be used in the same document. v1 elements will be deprecated in v2, and removed in v3.
"""
__yaml_version__ = "2.0.0"


def current_yaml_version() -> Version:
    """Get the current yaml version of eCalc.
    Must be updated by developer when changing yaml elements.
    :return:
    """
    return Version.from_string(__yaml_version__)
