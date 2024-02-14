from typing import Any

from pydantic import BeforeValidator


def DiscriminatorWithFallback(discriminator_alias: str, discriminator_fallback: str) -> BeforeValidator:
    """
    Use if one of the objects in the Union does not contain the discriminator.

    Args:
        discriminator_alias: The discriminator alias, used when checking if discriminator exists.
        discriminator_fallback: the value that should be used for the fallback discriminator

    Returns:
    """

    def fallback_discriminator(data: Any):
        if not isinstance(data, dict):
            raise ValueError("data must be dict")
        if discriminator_alias not in data:
            data[discriminator_alias] = discriminator_fallback

        return data

    return BeforeValidator(fallback_discriminator)
