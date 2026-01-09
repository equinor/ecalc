"""Tests for NeqSimFluidService cache configuration."""

from dataclasses import FrozenInstanceError

import pytest

from ecalc_neqsim_wrapper.cache_service import CacheConfig, CacheService
from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_values(self):
        config = CacheConfig()
        assert config.reference_fluid_max_size == 512
        assert config.flash_max_size == 100_000

    def test_custom_values(self):
        config = CacheConfig(reference_fluid_max_size=1000, flash_max_size=50_000)
        assert config.reference_fluid_max_size == 1000
        assert config.flash_max_size == 50_000

    def test_default_classmethod(self):
        config = CacheConfig.default()
        assert config == CacheConfig()

    def test_immutable(self):
        """CacheConfig is frozen (immutable)."""
        config = CacheConfig()
        with pytest.raises(FrozenInstanceError):
            config.flash_max_size = 999  # type: ignore[misc]


class TestFluidServiceConfigure:
    """Tests for NeqSimFluidService.configure()."""

    def setup_method(self):
        """Reset state before each test."""
        NeqSimFluidService.reset_instance()
        CacheService.clear_all()
        # Remove cache registrations for clean slate so new sizes take effect
        CacheService._caches.clear()

    def teardown_method(self):
        """Reset state after each test."""
        NeqSimFluidService.reset_instance()
        CacheService.clear_all()
        CacheService._caches.clear()

    def test_configure_before_instance(self, with_neqsim_service):
        """Configure called before instance() uses custom sizes."""
        config = CacheConfig(reference_fluid_max_size=100, flash_max_size=1000)
        NeqSimFluidService.configure(config)

        service = NeqSimFluidService.instance()

        assert service._reference_cache._max_size == 100
        assert service._flash_cache._max_size == 1000

    def test_default_sizes_without_configure(self, with_neqsim_service):
        """Without configure(), default sizes are used."""
        service = NeqSimFluidService.instance()

        assert service._reference_cache._max_size == 512
        assert service._flash_cache._max_size == 100_000

    def test_configure_after_instance_raises(self, with_neqsim_service):
        """Configure called after instance() raises RuntimeError."""
        _ = NeqSimFluidService.instance()

        with pytest.raises(RuntimeError, match="must be called before"):
            NeqSimFluidService.configure(CacheConfig())

    def test_reset_clears_config(self, with_neqsim_service):
        """reset_instance() clears the stored config."""
        NeqSimFluidService.configure(CacheConfig(flash_max_size=999))
        NeqSimFluidService.reset_instance()

        assert NeqSimFluidService._cache_config is None

    def test_configure_only_reference_cache(self, with_neqsim_service):
        """Can configure only one cache size, other uses default."""
        config = CacheConfig(reference_fluid_max_size=256)
        NeqSimFluidService.configure(config)

        service = NeqSimFluidService.instance()

        assert service._reference_cache._max_size == 256
        assert service._flash_cache._max_size == 100_000  # default

    def test_configure_only_flash_cache(self, with_neqsim_service):
        """Can configure only flash cache size, other uses default."""
        config = CacheConfig(flash_max_size=50_000)
        NeqSimFluidService.configure(config)

        service = NeqSimFluidService.instance()

        assert service._reference_cache._max_size == 512  # default
        assert service._flash_cache._max_size == 50_000
