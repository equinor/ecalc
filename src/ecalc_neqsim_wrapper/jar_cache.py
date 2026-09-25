import hashlib
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class NeqsimConfig(TypedDict):
    url: str
    sha: str


class JARCacheManager:
    """Simplified JAR cache manager that caches one JAR per version/java_version combination"""

    # Hash algorithms accepted in the config "sha" field; add e.g. "sha512" to support it.
    _ALLOWED_HASH_ALGORITHMS = frozenset({"sha256"})

    def __init__(self, cache_dir: Path, config: NeqsimConfig):
        """
        Initialize cache manager

        Args:
            cache_dir: Base cache directory
            config: Configuration dictionary
        """
        self.cache_dir = cache_dir
        self.jar_cache_dir = cache_dir / "jars"
        self.jar_cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.logger = logger

        # The config stores the hash as "<algorithm>:<hex>", e.g. "sha256:abc...".
        self._hash_algorithm, _, self._expected_hash = config["sha"].partition(":")

    def _get_cache_filename(self) -> str:
        """Generate simple cache filename for version and Java version combination"""
        # Use only the hex digest so the filename has no colon (which would collide
        # with the classpath separator when the JAR is added to the Java classpath).
        return f"neqsim-{self._expected_hash}.jar"

    def get_cached_jar(self) -> Path | None:
        """Check if JAR exists in cache"""
        cache_filename = self._get_cache_filename()
        cached_jar = self.jar_cache_dir / cache_filename

        if not cached_jar.exists():
            self.logger.debug("No cached JAR found")
            return None

        # Verify integrity if enabled
        if not self._verify_jar_integrity(cached_jar):
            self.logger.warning(f"Cached JAR failed integrity check, removing: {cached_jar.name}")
            cached_jar.unlink()  # Remove corrupted cache
            return None

        self.logger.info(f"Using cached JAR: {cached_jar.name}")
        return cached_jar

    def cache_jar(self, source_jar: Path) -> Path:
        """Cache downloaded JAR file, replacing any existing cached version"""
        cache_filename = self._get_cache_filename()
        cached_jar = self.jar_cache_dir / cache_filename

        tmp_path = None
        try:
            # Create a temp file in the same directory to ensure atomic rename
            file_descriptor, tmp_file_name = tempfile.mkstemp(prefix=cache_filename + ".", dir=str(self.jar_cache_dir))
            os.close(file_descriptor)
            tmp_path = Path(tmp_file_name)

            shutil.copy2(source_jar, tmp_path)

            # Verify the temporary JAR file before replacing
            if not self._verify_jar_integrity(tmp_path):
                self.logger.error(f"Downloaded JAR failed integrity check: {tmp_path}")
                try:
                    tmp_path.unlink()
                except Exception as e:
                    self.logger.error(f"Failed to unlink temporary file: {e}")
                raise RuntimeError("Downloaded JAR failed integrity check")

            # Replace the cached JAR atomically
            try:
                tmp_path.replace(cached_jar)
                self.logger.debug(f"Replaced cached JAR: {cache_filename}")
            except Exception as e:
                self.logger.error(f"Failed to replace cached JAR: {e}")
                try:
                    tmp_path.unlink()
                except Exception as e:
                    self.logger.error(f"Failed to unlink temporary file: {e}")
                raise

            self.logger.info(f"Cached JAR: {cached_jar.name}")
            return cached_jar
        finally:
            try:
                if tmp_path is not None and tmp_path.exists():
                    tmp_path.unlink()
            except Exception as e:
                self.logger.error(f"Failed to unlink temporary file during cleanup: {e}")

    def _verify_jar_integrity(self, jar_path: Path) -> bool:
        """Verify JAR file is not corrupted and matches the expected hash"""
        try:
            # Basic checks: file exists, has content, ends with proper extension
            if not jar_path.exists() or jar_path.stat().st_size == 0:
                return False

            # Check if it's a valid ZIP file (JARs are ZIP files)
            with zipfile.ZipFile(jar_path, "r") as zf:
                # Try to read the file list - this will fail if corrupted
                zf.namelist()

            # Verify the hash matches the expected value parsed from the config.
            if self._hash_algorithm not in self._ALLOWED_HASH_ALGORITHMS:
                allowed = ", ".join(sorted(self._ALLOWED_HASH_ALGORITHMS))
                self.logger.debug(f"Unsupported hash algorithm '{self._hash_algorithm}', allowed: {allowed}")
                return False

            actual_hash = self._compute_hash(jar_path, self._hash_algorithm)
            if actual_hash.lower() != self._expected_hash.lower():
                self.logger.debug(
                    f"JAR {self._hash_algorithm} mismatch for {jar_path}: "
                    f"expected {self._expected_hash}, got {actual_hash}"
                )
                return False

            return True

        except Exception as e:
            self.logger.debug(f"JAR integrity check failed for {jar_path}: {e}")
            return False

    @staticmethod
    def _compute_hash(jar_path: Path, algorithm: str) -> str:
        """Compute the hash of a file using the given algorithm"""
        digest = hashlib.new(algorithm)
        with open(jar_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
