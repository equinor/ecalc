"""
A feature flag singleton service available when needed
"""

from libecalc.common.errors.exceptions import ProgrammingError


class FeatureFlagService:
    _instance = None
    _flags: dict[str, bool] = {}

    def __init__(self):
        raise ProgrammingError("Use get_instance() to get an instance of FeatureFlagService.")

    @classmethod
    def initialize(cls, flags: dict[str, bool]) -> None:
        """Initialize the feature flags.

        Args:
            flags (dict[str, bool]): A dictionary of feature flags.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._flags = flags

        raise ProgrammingError("FeatureFlagService is already initialized, and can only be initialiced once.")

    @classmethod
    def get_instance(cls) -> "FeatureFlagService":
        """Get the singleton instance of FeatureFlagService.

        Returns:
            FeatureFlagService: The singleton instance.
        """
        if cls._instance is None:
            raise ProgrammingError("FeatureFlagService is not initialized. Initialized before use.")

        return cls._instance

    def set_flag(self, feature_name: str, is_enabled: bool) -> None:
        """Set the status of a feature flag.

        Args:
            feature_name (str): The name of the feature.
            is_enabled (bool): True to enable the feature, False to disable it.
        """
        self._flags[feature_name] = is_enabled

    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            feature_name (str): The name of the feature.

        Returns:
            bool: True if the feature is enabled, False otherwise.
        """
        return self._flags.get(feature_name, False)
