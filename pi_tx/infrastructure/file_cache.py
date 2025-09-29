from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
import weakref
from ..logging_config import get_logger

T = TypeVar("T")


@dataclass
class CachedFile(Generic[T]):
    """Represents a cached file with metadata."""

    path: str
    content: T
    mtime: float
    size: int
    last_accessed: datetime
    dirty: bool = False  # True if in-memory content differs from disk


class FileCache:
    """
    Centralized file cache manager for pi-tx application.

    Provides automatic caching, change detection, and lazy loading for all file operations.
    Thread-safe and supports automatic persistence on shutdown.
    """

    _instance: Optional["FileCache"] = None
    _lock = threading.RLock()

    def __init__(self):
        self._cache: Dict[str, CachedFile] = {}
        self._log = get_logger(__name__)
        self._parsers: Dict[str, Callable[[str], Any]] = {}
        self._serializers: Dict[str, Callable[[Any, str], None]] = {}
        self._lock = threading.RLock()
        self._auto_save = True
        # Register default parsers
        self.register_parser(".json", self._parse_json)
        self.register_serializer(".json", self._serialize_json)

        # Weak reference cleanup for automatic persistence
        weakref.finalize(self, self._cleanup)

    @classmethod
    def get_instance(cls) -> "FileCache":
        """Get singleton instance of FileCache."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = FileCache()
        return cls._instance

    def register_parser(self, extension: str, parser: Callable[[str], Any]):
        """Register a parser function for a file extension."""
        self._parsers[extension.lower()] = parser

    def register_serializer(
        self, extension: str, serializer: Callable[[Any, str], None]
    ):
        """Register a serializer function for a file extension."""
        self._serializers[extension.lower()] = serializer

    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Default JSON parser."""
        return json.loads(content)

    def _serialize_json(self, data: Any, filepath: str) -> None:
        """Default JSON serializer."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_file_info(self, filepath: str) -> tuple[float, int]:
        """Get file modification time and size."""
        try:
            stat = os.stat(filepath)
            return stat.st_mtime, stat.st_size
        except (OSError, FileNotFoundError):
            return 0.0, 0

    def _get_parser(self, filepath: str) -> Callable[[str], Any]:
        """Get appropriate parser for file extension."""
        ext = Path(filepath).suffix.lower()
        return self._parsers.get(ext, lambda x: x)  # Default to identity

    def _get_serializer(self, filepath: str) -> Callable[[Any, str], None]:
        """Get appropriate serializer for file extension."""
        ext = Path(filepath).suffix.lower()
        return self._serializers.get(ext, self._default_serializer)

    def _default_serializer(self, data: Any, filepath: str) -> None:
        """Default serializer for unknown file types."""
        with open(filepath, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                f.write(str(data))

    def load_file(
        self, filepath: str, default_value: Any = None, force_reload: bool = False
    ) -> Any:
        """
        Load file content with caching.

        Args:
            filepath: Path to file to load
            default_value: Value to return if file doesn't exist
            force_reload: Force reload from disk even if cached

        Returns:
            File content (parsed if parser available)
        """
        filepath = str(Path(filepath).resolve())

        with self._lock:
            current_mtime, current_size = self._get_file_info(filepath)

            # Check if file exists
            if current_mtime == 0.0:
                if default_value is not None:
                    # Store default value in cache
                    cached_file = CachedFile(
                        path=filepath,
                        content=default_value,
                        mtime=0.0,
                        size=0,
                        last_accessed=datetime.now(),
                        dirty=True,  # Mark as dirty since it needs to be saved
                    )
                    self._cache[filepath] = cached_file
                    return default_value
                else:
                    raise FileNotFoundError(f"File not found: {filepath}")

            # Check cache validity
            cached_file = self._cache.get(filepath)
            if (
                not force_reload
                and cached_file is not None
                and cached_file.mtime == current_mtime
                and cached_file.size == current_size
                and not cached_file.dirty
            ):

                # Update access time
                cached_file.last_accessed = datetime.now()
                return cached_file.content

            # Load from disk
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                parser = self._get_parser(filepath)
                parsed_content = parser(raw_content)

                # Cache the result
                cached_file = CachedFile(
                    path=filepath,
                    content=parsed_content,
                    mtime=current_mtime,
                    size=current_size,
                    last_accessed=datetime.now(),
                    dirty=False,
                )
                self._cache[filepath] = cached_file

                self._log.debug("Loaded %s (%d bytes)", filepath, current_size)
                return parsed_content

            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                if default_value is not None:
                    # Store default value in cache
                    cached_file = CachedFile(
                        path=filepath,
                        content=default_value,
                        mtime=current_mtime,
                        size=current_size,
                        last_accessed=datetime.now(),
                        dirty=True,
                    )
                    self._cache[filepath] = cached_file
                    self._log.warning(
                        "Error loading %s, using default: %s", filepath, e
                    )
                    return default_value
                else:
                    raise

    def save_file(self, filepath: str, content: Any, immediate: bool = True) -> None:
        """
        Save content to file and update cache.

        Args:
            filepath: Path to file to save
            content: Content to save
            immediate: Whether to save immediately or mark as dirty
        """
        filepath = str(Path(filepath).resolve())

        with self._lock:
            # Update cache
            cached_file = self._cache.get(filepath)
            if cached_file:
                cached_file.content = content
                cached_file.dirty = True
                cached_file.last_accessed = datetime.now()
            else:
                # Create new cache entry
                cached_file = CachedFile(
                    path=filepath,
                    content=content,
                    mtime=0.0,
                    size=0,
                    last_accessed=datetime.now(),
                    dirty=True,
                )
                self._cache[filepath] = cached_file

            if immediate:
                self._persist_file(filepath)

    def _persist_file(self, filepath: str) -> None:
        """Persist a single file to disk."""
        cached_file = self._cache.get(filepath)
        if not cached_file or not cached_file.dirty:
            return

        try:
            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Save to disk
            serializer = self._get_serializer(filepath)
            serializer(cached_file.content, filepath)

            # Update cache metadata
            new_mtime, new_size = self._get_file_info(filepath)
            cached_file.mtime = new_mtime
            cached_file.size = new_size
            cached_file.dirty = False

            self._log.debug("Saved %s (%d bytes)", filepath, new_size)

        except Exception as e:
            self._log.error("Error saving %s: %s", filepath, e)

    def update_content(self, filepath: str, content: Any) -> None:
        """Update in-memory content without immediately saving to disk."""
        filepath = str(Path(filepath).resolve())

        with self._lock:
            cached_file = self._cache.get(filepath)
            if cached_file:
                cached_file.content = content
                cached_file.dirty = True
                cached_file.last_accessed = datetime.now()
            else:
                # Create new cache entry
                cached_file = CachedFile(
                    path=filepath,
                    content=content,
                    mtime=0.0,
                    size=0,
                    last_accessed=datetime.now(),
                    dirty=True,
                )
                self._cache[filepath] = cached_file

    def is_loaded(self, filepath: str) -> bool:
        """Check if file is currently cached."""
        filepath = str(Path(filepath).resolve())
        return filepath in self._cache

    def is_dirty(self, filepath: str) -> bool:
        """Check if cached file has unsaved changes."""
        filepath = str(Path(filepath).resolve())
        cached_file = self._cache.get(filepath)
        return cached_file.dirty if cached_file else False

    def flush_all(self) -> None:
        """Save all dirty files to disk."""
        with self._lock:
            dirty_files = [fp for fp, cf in self._cache.items() if cf.dirty]

            for filepath in dirty_files:
                self._persist_file(filepath)

            if dirty_files:
                self._log.info("Flushed %d dirty files", len(dirty_files))

    def clear_cache(self, filepath: Optional[str] = None) -> None:
        """Clear cache for specific file or all files."""
        with self._lock:
            if filepath:
                filepath = str(Path(filepath).resolve())
                self._cache.pop(filepath, None)
                self._log.info("Cleared cache for %s", filepath)
            else:
                self._cache.clear()
                self._log.info("Cleared all cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_files = len(self._cache)
            dirty_files = sum(1 for cf in self._cache.values() if cf.dirty)
            total_size = sum(cf.size for cf in self._cache.values())

            return {
                "total_files": total_files,
                "dirty_files": dirty_files,
                "total_size_bytes": total_size,
                "files": {
                    filepath: {
                        "size": cf.size,
                        "dirty": cf.dirty,
                        "last_accessed": cf.last_accessed.isoformat(),
                    }
                    for filepath, cf in self._cache.items()
                },
            }

    def _cleanup(self):
        """Cleanup method called on shutdown."""
        if self._auto_save:
            self.flush_all()


# Global instance
file_cache = FileCache.get_instance()


# Convenience functions for common operations
def load_json(filepath: str, default_value: Dict[str, Any] = None) -> Dict[str, Any]:
    """Load JSON file with caching."""
    return file_cache.load_file(filepath, default_value or {})


def save_json(filepath: str, data: Dict[str, Any]) -> None:
    """Save JSON file and update cache."""
    file_cache.save_file(filepath, data)


def update_json(filepath: str, data: Dict[str, Any]) -> None:
    """Update JSON in memory without immediate save."""
    file_cache.update_content(filepath, data)
