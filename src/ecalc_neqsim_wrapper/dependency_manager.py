import logging
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .jar_cache import JARCacheManager, NeqsimConfig

logger = logging.getLogger(__name__)


class NeqSimDependencyManager:
    """Manages NeqSim JAR dependencies from GitHub releases"""

    def __init__(
        self,
        config: NeqsimConfig,
        cache_dir: Path,
    ):
        """Initialize Neqsim Dependency Manager

        Args:
            config (NeqsimConfig): Configuration dictionary
            cache_dir (Path): Directory for caching JAR versions, defaults to ~/.ecalc/neqsim/cache
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.config = config
        self.logger = logger

        # Initialize cache manager
        self.cache_manager = JARCacheManager(self.cache_dir, self.config)

    def _get_jar_from_github(self) -> Path:
        """Download JAR from GitHub releases with fallback support and caching"""

        # Check cache first
        cached_jar = self.cache_manager.get_cached_jar()
        if cached_jar:
            return cached_jar

        url = self.config["url"]

        jar_filename = url.split("/")[-1]

        # Create temporary directory for download
        with tempfile.TemporaryDirectory(prefix="jneqsim_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            downloaded_jar = temp_dir / jar_filename

            try:
                self.logger.debug(f"Downloading '{jar_filename}' at '{url}'...")

                with urllib.request.urlopen(url) as response:  # noqa: S310
                    content = response.read()

                downloaded_jar.write_bytes(content)

                self.logger.info(f"Downloaded from GitHub: {downloaded_jar.name}")

                # Cache the downloaded JAR
                try:
                    cached_jar = self.cache_manager.cache_jar(downloaded_jar)
                except Exception as cache_exc:
                    self.logger.error(f"Failed to cache downloaded JAR: {cache_exc}")
                    raise cache_exc
                return cached_jar

            except Exception as e:
                # For non-HTTP errors, try fallback
                raise RuntimeError(f"Could not download NeqSim from GitHub: {e}") from e

    def resolve_dependency(self) -> Path:
        """
        Resolve NeqSim dependency

        Returns:
            Path to resolved JAR file
        """

        # Download dependency
        return self._get_jar_from_github()

    @property
    def jar_cache_dir(self) -> Path:
        """Access to JAR cache directory for backward compatibility"""
        return self.cache_manager.jar_cache_dir
