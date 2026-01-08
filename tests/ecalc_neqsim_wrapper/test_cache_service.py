import pytest

from ecalc_neqsim_wrapper.cache_service import CacheName, CacheService
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear caches before and after each test to ensure isolation."""
    CacheService.clear_all()
    yield
    CacheService.clear_all()


class TestCacheBehavior:
    """Tests for cache behavior in the fluid service.

    These tests verify the caching architecture works correctly:
    - Cache hits occur on repeated queries
    - Key rounding prevents false misses from floating-point noise
    - Two-tier caching (reference + flash) functions efficiently
    - Different compositions maintain separate cache entries
    """

    def test_flash_cache_hit_on_repeated_query(self, fluid_model_medium: FluidModel, fluid_service):
        """Verify cache hits occur when flashing the same composition to the same P/T conditions."""
        # Arrange: Capture initial cache stats
        flash_cache = CacheService.get_cache(CacheName.FLUID_SERVICE_FLASH)
        assert flash_cache is not None, "Flash cache should exist"
        stats_before = flash_cache.get_stats()

        # Act: Flash to specific P/T conditions twice
        pressure_bara = 100.0
        temperature_kelvin = 350.0

        fluid_1 = fluid_service.flash_pt(fluid_model_medium, pressure_bara, temperature_kelvin)
        fluid_2 = fluid_service.flash_pt(fluid_model_medium, pressure_bara, temperature_kelvin)

        # Assert: Second flash should hit cache
        stats_after = flash_cache.get_stats()

        # First flash is a miss, second is a hit
        assert stats_after["misses"] == stats_before["misses"] + 1, "Expected one cache miss on first flash"
        assert stats_after["hits"] == stats_before["hits"] + 1, "Expected one cache hit on second flash"

        # Both fluids should have identical properties
        assert fluid_1.pressure_bara == fluid_2.pressure_bara
        assert fluid_1.temperature_kelvin == fluid_2.temperature_kelvin
        assert fluid_1.density == fluid_2.density

    def test_cache_key_rounding_boundary(self, fluid_model_medium: FluidModel, fluid_service):
        """Verify the 6-decimal rounding strategy prevents false cache misses from floating-point noise."""
        # Arrange: Capture initial cache stats
        flash_cache = CacheService.get_cache(CacheName.FLUID_SERVICE_FLASH)
        assert flash_cache is not None, "Flash cache should exist"
        stats_before = flash_cache.get_stats()

        # Act: Flash with values that differ within 6 decimals (should hit same cache key)
        pressure_1 = 100.0000001
        temperature_1 = 350.0000001

        pressure_2 = 100.0000002  # Within 6 decimal threshold
        temperature_2 = 350.0000002  # Within 6 decimal threshold

        fluid_1 = fluid_service.flash_pt(fluid_model_medium, pressure_1, temperature_1)
        _ = fluid_service.flash_pt(fluid_model_medium, pressure_2, temperature_2)

        stats_after_hit = flash_cache.get_stats()

        # Assert: Second flash should hit cache (same rounded key)
        assert (
            stats_after_hit["misses"] == stats_before["misses"] + 1
        ), "Expected one miss on first flash with tiny difference"
        assert stats_after_hit["hits"] == stats_before["hits"] + 1, "Expected hit on second flash (same rounded key)"

        # Act: Flash with value outside 6 decimal threshold (should miss cache)
        pressure_3 = 100.0000100  # Outside 6 decimal threshold
        temperature_3 = 350.0000100

        fluid_3 = fluid_service.flash_pt(fluid_model_medium, pressure_3, temperature_3)

        stats_after_miss = flash_cache.get_stats()

        # Assert: Third flash should miss cache (different rounded key)
        assert (
            stats_after_miss["misses"] == stats_after_hit["misses"] + 1
        ), "Expected miss on third flash (outside rounding threshold)"
        assert stats_after_miss["hits"] == stats_after_hit["hits"], "Expected no additional hits"

        # Properties should be slightly different for fluid_3
        assert fluid_1.pressure_bara != fluid_3.pressure_bara

    def test_two_tier_cache_architecture(self, fluid_model_medium: FluidModel, fluid_service):
        """Verify the two-tier cache architecture (reference + flash) functions efficiently."""
        # Arrange: Get both caches
        reference_cache = CacheService.get_cache(CacheName.REFERENCE_FLUID)
        flash_cache = CacheService.get_cache(CacheName.FLUID_SERVICE_FLASH)
        assert reference_cache is not None, "Reference cache should exist"
        assert flash_cache is not None, "Flash cache should exist"

        initial_ref_size = len(reference_cache)
        initial_flash_size = len(flash_cache)

        # Act: Flash same composition to 3 different P/T states
        fluid_1 = fluid_service.flash_pt(fluid_model_medium, 100.0, 350.0)
        _ = fluid_service.flash_pt(fluid_model_medium, 150.0, 400.0)
        _ = fluid_service.flash_pt(fluid_model_medium, 200.0, 450.0)

        # Assert: Reference cache should have only 1 new entry (composition cached once)
        assert len(reference_cache) == initial_ref_size + 1, "Expected reference cache to grow by 1 (one composition)"

        # Assert: Flash cache should have 3 new entries (each P/T state cached)
        assert len(flash_cache) == initial_flash_size + 3, "Expected flash cache to grow by 3 (three P/T states)"

        # Act: Re-flash to one of the same P/T states
        stats_before_reuse = flash_cache.get_stats()
        fluid_1_repeat = fluid_service.flash_pt(fluid_model_medium, 100.0, 350.0)
        stats_after_reuse = flash_cache.get_stats()

        # Assert: Flash cache should hit (two-tier reuse)
        assert stats_after_reuse["hits"] == stats_before_reuse["hits"] + 1, "Expected flash cache hit on repeated P/T"
        assert len(reference_cache) == initial_ref_size + 1, "Reference cache size should remain unchanged"
        assert len(flash_cache) == initial_flash_size + 3, "Flash cache size should remain unchanged"

        # Properties should be identical
        assert fluid_1.pressure_bara == fluid_1_repeat.pressure_bara
        assert fluid_1.temperature_kelvin == fluid_1_repeat.temperature_kelvin

    def test_cache_independence_across_compositions(
        self, fluid_model_medium: FluidModel, fluid_model_rich: FluidModel, fluid_service
    ):
        """Verify that different compositions maintain separate cache entries."""
        # Arrange: Get both caches
        reference_cache = CacheService.get_cache(CacheName.REFERENCE_FLUID)
        flash_cache = CacheService.get_cache(CacheName.FLUID_SERVICE_FLASH)
        assert reference_cache is not None, "Reference cache should exist"
        assert flash_cache is not None, "Flash cache should exist"

        initial_ref_size = len(reference_cache)
        initial_flash_size = len(flash_cache)

        # Act: Flash two different compositions to the same P/T conditions
        pressure_bara = 100.0
        temperature_kelvin = 350.0

        fluid_medium = fluid_service.flash_pt(fluid_model_medium, pressure_bara, temperature_kelvin)
        fluid_rich = fluid_service.flash_pt(fluid_model_rich, pressure_bara, temperature_kelvin)

        # Assert: Both should be cache misses (different compositions = different keys)
        assert len(reference_cache) == initial_ref_size + 2, "Expected 2 new reference cache entries (two compositions)"
        assert len(flash_cache) == initial_flash_size + 2, "Expected 2 new flash cache entries (two compositions)"

        # Assert: Properties should differ (different compositions at same P/T)
        assert fluid_medium.density != fluid_rich.density, "Different compositions should have different densities"
        assert (
            fluid_medium.molar_mass != fluid_rich.molar_mass
        ), "Different compositions should have different molar masses"

        # Act: Re-flash medium composition to verify it hits its own cache entry
        stats_before = flash_cache.get_stats()
        fluid_medium_repeat = fluid_service.flash_pt(fluid_model_medium, pressure_bara, temperature_kelvin)
        stats_after = flash_cache.get_stats()

        # Assert: Should hit cache for medium composition
        assert stats_after["hits"] == stats_before["hits"] + 1, "Expected cache hit for repeated medium composition"
        assert len(reference_cache) == initial_ref_size + 2, "Cache sizes should remain unchanged"
        assert len(flash_cache) == initial_flash_size + 2, "Cache sizes should remain unchanged"

        # Properties should be identical to first medium flash
        assert fluid_medium.density == fluid_medium_repeat.density


class TestLRUCacheDisabling:
    """Test that max_size=0 disables caching efficiently."""

    def test_cache_disabled_with_max_size_zero(self):
        """Verify max_size=0 disables caching entirely without wasting CPU."""
        from ecalc_neqsim_wrapper.cache_service import LRUCache

        # Arrange: Create cache with size 0
        cache = LRUCache(max_size=0)

        # Act: Try to put values
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Assert: Nothing should be cached
        assert cache.get("key1") is None, "Cache should be disabled, get should return None"
        assert cache.get("key2") is None, "Cache should be disabled, get should return None"
        assert len(cache) == 0, "Cache should remain empty"

        # Assert: Stats should show all misses, no evictions
        stats = cache.get_stats()
        assert stats["hits"] == 0, "Should have no hits with disabled cache"
        assert stats["misses"] == 2, "Should have 2 misses"
        assert stats["evictions"] == 0, "Should have no evictions (early return prevents add-then-evict)"
        assert stats["size"] == 0, "Cache size should be 0"
