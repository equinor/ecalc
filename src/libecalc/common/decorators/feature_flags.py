from collections.abc import Callable
from functools import wraps
from typing import Any

from libecalc.common.logger import logger


class Feature:
    """Class with utils for handling new (beta) and old (deprecated) features in a safe and communicative way."""

    @staticmethod
    def experimental(feature_description: str) -> Any | None:
        """Flag for experimental/beta features
        Args:
            feature_description: Description of new feature.

        Returns:

        """

        def decorate(experimental_feature: Callable):
            @wraps(experimental_feature)
            def with_experimental(*args, **kwargs):
                logger.warning(
                    f"!EXPERIMENTAL! {feature_description}."
                    f" It has not been thoroughly tested and Quality Assured yet. Use at own risk. !EXPERIMENTAL!"
                )
                try:
                    return experimental_feature(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"Error in {feature_description}: {e}."
                        f" However, this is an experimental feature and should be reported in #ecalc_support on Slack.",
                        e,
                    )
                return None

            return with_experimental

        return decorate

    @staticmethod
    def deprecated(message: str):
        """Flag for handling deprecated features
        Args:
            message: Info about deprecation of feature, and (if available) instructions on usage of replacement.

        Returns:

        """
        logger.warning(f"DEPRECATED! {message}. It will be removed in a future version.")


class FeatureToggle:
    """Decorator to handle 2 paths, depending on whether toggle is on or off."""

    @staticmethod
    def experimental(feature_toggle: bool, fallback: Callable) -> Any | None:
        """If feature_toggle is true, call current (experimental) method, if false fallback to old method.

        To easily and safely rollback to a working version in production for high(er) risk changes, but with
        e.g. more functionality. To safely roll out new features with safety net to old version instead of
        redeploy. E.g. essential for trunk based development and similar approaches.

        Both old and new must be compatible signature wise wrt in/out parameters, return values
        and possibly the in-place mutable changes done on in-parameters.

        :param feature_toggle:
        :param fallback: the old safe known method
        :return:
        """

        def decorate(experimental_feature: Callable):
            @wraps(experimental_feature)
            def with_feature_toggle(self, *args, **kwargs):
                if feature_toggle:
                    return experimental_feature(self, *args, **kwargs)
                else:
                    return fallback(self, *args, **kwargs)

            return with_feature_toggle

        return decorate
