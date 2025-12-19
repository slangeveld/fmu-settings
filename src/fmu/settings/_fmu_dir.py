"""Main interface for working with .fmu directory."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, TypeAlias, cast

from fmu.settings._resources.changelog_manager import ChangelogManager
from fmu.settings._resources.mappings_manager import MappingsManager

from ._logging import null_logger
from ._readme_texts import PROJECT_README_CONTENT, USER_README_CONTENT
from ._resources.cache_manager import CacheManager
from ._resources.config_managers import (
    ProjectConfigManager,
    UserConfigManager,
)
from ._resources.lock_manager import DEFAULT_LOCK_TIMEOUT, LockManager
from .models.project_config import ProjectConfig
from .models.user_config import UserConfig

logger: Final = null_logger(__name__)

FMUConfigManager: TypeAlias = ProjectConfigManager | UserConfigManager


class FMUDirectoryBase:
    """Provides access to a .fmu directory and operations on its contents."""

    config: FMUConfigManager
    _lock: LockManager
    _cache_manager: CacheManager
    _README_CONTENT: str = ""
    _changelog: ChangelogManager
    _mappings: MappingsManager

    def __init__(
        self: Self,
        base_path: str | Path,
        cache_revisions: int = CacheManager.MIN_REVISIONS,
        *,
        lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """Initializes access to a .fmu directory.

        Args:
            base_path: The directory containing the .fmu directory or one of its parent
                dirs
            cache_revisions: Number of revisions to retain in the cache. Minimum is 5.
            lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

        Raises:
            FileExistsError: If .fmu exists but is not a directory
            FileNotFoundError: If .fmu directory doesn't exist
            PermissionError: If lacking permissions to read/write to the directory
        """
        self.base_path = Path(base_path).resolve()
        logger.debug(f"Initializing FMUDirectory from '{base_path}'")
        self._lock = LockManager(self, timeout_seconds=lock_timeout_seconds)
        self._cache_manager = CacheManager(self, max_revisions=cache_revisions)
        self._changelog = ChangelogManager(self)
        self._mappings = MappingsManager(self)

        fmu_dir = self.base_path / ".fmu"
        if fmu_dir.exists():
            if fmu_dir.is_dir():
                self._path = fmu_dir
            else:
                raise FileExistsError(
                    f".fmu exists at {self.base_path} but is not a directory"
                )
        else:
            raise FileNotFoundError(f"No .fmu directory found at {self.base_path}")

        logger.debug(f"Using .fmu directory at {self._path}")

    @property
    def path(self: Self) -> Path:
        """Returns the path to the .fmu directory."""
        return self._path

    @property
    def cache(self: Self) -> CacheManager:
        """Access the cache manager."""
        return self._cache_manager

    @property
    def cache_max_revisions(self: Self) -> int:
        """Current retention limit for revision snapshots."""
        return self._cache_manager.max_revisions

    @cache_max_revisions.setter
    def cache_max_revisions(self: Self, value: int) -> None:
        """Update the retention limit for revision snapshots.

        Args:
            value: The new maximum number of revisions to retain. Minimum value is 5.
                Values below 5 are set to 5.
        """
        clamped_value = max(CacheManager.MIN_REVISIONS, value)
        self._cache_manager.max_revisions = clamped_value
        self.set_config_value("cache_max_revisions", clamped_value)

    def get_config_value(self: Self, key: str, default: Any = None) -> Any:
        """Gets a configuration value by key.

        Supports dot notation for nested values (e.g., "foo.bar")

        Args:
            key: The configuration key
            default: Value to return if key is not found. Default None

        Returns:
            The configuration value or deafult
        """
        return self.config.get(key, default)

    def set_config_value(self: Self, key: str, value: Any) -> None:
        """Sets a configuration value by key.

        Args:
            key: The configuration key
            value: The value to set

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updated config is invalid
        """
        logger.info(f"Setting {key} in {self.path}")
        self.config.set(key, value)
        logger.debug(f"Set {key} to {value}")

    def update_config(
        self: Self, updates: dict[str, Any]
    ) -> ProjectConfig | UserConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated *Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return self.config.update(updates)

    def get_file_path(self: Self, relative_path: str | Path) -> Path:
        """Gets the absolute path to a file within the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            Absolute path to the file
        """
        return self.path / relative_path

    def read_file(self, relative_path: str | Path) -> bytes:
        """Reads a file from the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_path = self.get_file_path(relative_path)
        return file_path.read_bytes()

    def read_text_file(self, relative_path: str | Path, encoding: str = "utf-8") -> str:
        """Reads a text file from the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            encoding: Text encoding to use. Default utf-8

        Returns:
            File contents as string
        """
        file_path = self.get_file_path(relative_path)
        return file_path.read_text(encoding=encoding)

    def write_file(self, relative_path: str | Path, data: bytes) -> None:
        """Writes bytes to a file in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            data: Bytes to write
        """
        self._lock.ensure_can_write()
        file_path = self.get_file_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_bytes(data)
        logger.debug(f"Wrote {len(data)} bytes to {file_path}")

    def write_text_file(
        self, relative_path: str | Path, content: str, encoding: str = "utf-8"
    ) -> None:
        """Writes text to a file in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            content: Text content to write
            encoding: Text encoding to use. Default utf-8
        """
        self._lock.ensure_can_write()
        file_path = self.get_file_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding=encoding)
        logger.debug(f"Wrote text file to {file_path}")

    def list_files(self, subdirectory: str | Path | None = None) -> list[Path]:
        """Lists files in the .fmu directory or a subdirectory.

        Args:
            subdirectory: Optional subdirectory to list files from

        Returns:
            List of Path objects for files (not directories)
        """
        base = self.get_file_path(subdirectory) if subdirectory else self.path
        if not base.exists():
            return []

        return [p for p in base.iterdir() if p.is_file()]

    def ensure_directory(self, relative_path: str | Path) -> Path:
        """Ensures a subdirectory exists in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            Path to the directory
        """
        dir_path = self.get_file_path(relative_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def file_exists(self, relative_path: str | Path) -> bool:
        """Checks if a file exists in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            True if the file exists, False otherwise
        """
        return self.get_file_path(relative_path).exists()

    def restore(self: Self) -> None:
        """Attempt to reconstruct missing .fmu files from in-memory state."""
        if not self.path.exists():
            self.path.mkdir(parents=True, exist_ok=True)
            logger.info("Recreated missing .fmu directory at %s", self.path)

        readme_path = self.get_file_path("README")
        if self._README_CONTENT and not readme_path.exists():
            self.write_text_file("README", self._README_CONTENT)
            logger.info("Restored README at %s", readme_path)

        config_path = self.config.path
        if not config_path.exists():
            cached_model = getattr(self.config, "_cache", None)
            if cached_model is not None:
                self.config.save(cached_model)
                logger.info("Restored config.json from cached model at %s", config_path)
            else:
                self.config.reset()
                logger.info("Restored config.json from defaults at %s", config_path)


class ProjectFMUDirectory(FMUDirectoryBase):
    if TYPE_CHECKING:
        config: ProjectConfigManager

    _README_CONTENT: str = PROJECT_README_CONTENT

    def __init__(
        self: Self,
        base_path: str | Path,
        *,
        lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """Initializes a project-based .fmu directory.

        Args:
            base_path: Project directory containing the .fmu folder.
            lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.
        """
        self.config = ProjectConfigManager(self)
        super().__init__(
            base_path,
            CacheManager.MIN_REVISIONS,
            lock_timeout_seconds=lock_timeout_seconds,
        )
        try:
            max_revisions = self.config.get(
                "cache_max_revisions", CacheManager.MIN_REVISIONS
            )
            self._cache_manager.max_revisions = max_revisions
        except FileNotFoundError:
            pass

    def update_config(self: Self, updates: dict[str, Any]) -> ProjectConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated ProjectConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return cast("ProjectConfig", super().update_config(updates))

    @staticmethod
    def find_fmu_directory(start_path: Path) -> Path | None:
        """Searches for a .fmu directory in start_path and its parents.

        Args:
            start_path: The path to start searching from

        Returns:
            Path to the found .fmu directory or None if not found
        """
        current = start_path
        # Prevent symlink loops
        visited = set()

        while current not in visited:
            visited.add(current)
            fmu_dir = current / ".fmu"

            # Do not include $HOME/.fmu in the search
            if fmu_dir.is_dir() and current != Path.home():
                return fmu_dir

            # We hit root
            if current == current.parent:
                break

            current = current.parent

        return None

    @classmethod
    def find_nearest(
        cls: type[Self],
        start_path: str | Path = ".",
        *,
        lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
    ) -> Self:
        """Factory method to find and open the nearest .fmu directory.

        Args:
            start_path: Path to start searching from. Default current working director
            lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

        Returns:
            FMUDirectory instance

        Raises:
            FileNotFoundError: If no .fmu directory is found
        """
        start_path = Path(start_path).resolve()
        fmu_dir_path = cls.find_fmu_directory(start_path)
        if fmu_dir_path is None:
            raise FileNotFoundError(f"No .fmu directory found at or above {start_path}")
        return cls(fmu_dir_path.parent, lock_timeout_seconds=lock_timeout_seconds)

    def find_rms_projects(self: Self) -> list[Path]:
        """Searches for RMS project directories under the project root.

        RMS projects are identified by the presence of both .master and rms.ini
        files within a directory under rms/model/.

        Returns:
            List of Path objects to RMS project directories, sorted alphabetically.
            Returns empty list if none found.
        """
        project_root = self.base_path
        model_root = project_root / "rms/model"
        rms_projects: set[Path] = set()

        if model_root.is_dir():
            for candidate in model_root.iterdir():
                if not candidate.is_dir():
                    continue

                master_file = candidate / ".master"
                ini_file = candidate / "rms.ini"

                if master_file.is_file() and ini_file.is_file():
                    rms_projects.add(candidate)

        return sorted(rms_projects)

    def _sync_runtime_variables(self: Self) -> None:
        """Sync runtime variables with config file."""
        max_revisions_from_config = self.config.load().cache_max_revisions
        if self._cache_manager.max_revisions != max_revisions_from_config:
            self._cache_manager.max_revisions = max_revisions_from_config

    def get_dir_diff(
        self: Self, new_fmu_dir: Self
    ) -> dict[str, list[tuple[str, Any, Any]]]:
        """Get the resource differences between two .fmu directories.

        Compare all resources in the two .fmu directories and return a dict with the
        diff for each resource.

        Resources that are not present in both .fmu directories will not be diffed.
        """
        dir_diff: dict[str, list[tuple[str, Any, Any]]] = {}

        for resource in vars(self):
            try:
                match resource:
                    case "config":
                        current_resource: ProjectConfigManager = getattr(self, resource)
                        new_resource: ProjectConfigManager = getattr(
                            new_fmu_dir, resource
                        )
                        changes = current_resource.get_resource_diff(new_resource)
                    case "_mappings":
                        current_mappings: MappingsManager = getattr(self, resource)
                        new_mappings: MappingsManager = getattr(new_fmu_dir, resource)
                        changes = [
                            (
                                "mappings",
                                None,
                                current_mappings.get_mappings_diff(new_mappings),
                            )
                        ]
                    case "_changelog":
                        current_changelog: ChangelogManager = getattr(self, resource)
                        new_changelog: ChangelogManager = getattr(new_fmu_dir, resource)
                        changelog_diff = current_changelog.get_changelog_diff(
                            new_changelog
                        )
                        if len(changelog_diff.root) > 0:
                            changes = [("changelog", None, changelog_diff)]
                        else:
                            changes = []
                    case _:
                        continue
            except AttributeError:
                continue
            except FileNotFoundError:
                continue

            dir_diff[resource] = changes
        return dir_diff

    def sync_dir(self: Self, new_fmu_dir: Self) -> dict[str, Any]:
        """Sync the resources in two .fmu directories.

        Compare all resources in the two .fmu directories and merge all changes
        in the new .fmu directory into the current .fmu directory. Resources that are
        not present in both .fmu directories will not be synced.

        The changelog resource will be merged first to preserve the order of the log
        entries, as merging of the other resources may add new entries to the changelog.

        The sync is concluded by logging the sync details to the changelog.
        """
        changes_in_dir = self.get_dir_diff(new_fmu_dir)
        updates: dict[str, Any] = {}

        if "_changelog" in changes_in_dir and len(changes_in_dir["_changelog"]) > 0:
            current_changelog: ChangelogManager = self._changelog
            updated_changelog = current_changelog.merge_changes(
                changes_in_dir["_changelog"][0][2].root
            )
            updates["_changelog"] = updated_changelog
            changes_in_dir.pop("_changelog")

        for resource, changes in changes_in_dir.items():
            if len(changes) == 0:
                continue

            updated_resource: Any
            if resource == "config":
                current_config: ProjectConfigManager = self.config
                updated_resource = current_config.merge_changes(changes)
                self._sync_runtime_variables()
            elif resource == "_mappings":
                current_mapping: MappingsManager = self._mappings
                updated_resource = current_mapping.merge_changes(changes[0][2])

            updates[resource] = updated_resource

        self._changelog.log_merge_to_changelog(
            source_path=self.path,
            incoming_path=new_fmu_dir.path,
            merged_resources=list(updates.keys()),
        )

        return updates


class UserFMUDirectory(FMUDirectoryBase):
    if TYPE_CHECKING:
        config: UserConfigManager

    _README_CONTENT: str = USER_README_CONTENT

    def __init__(
        self: Self,
        *,
        lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """Initializes a user .fmu directory.

        Args:
            lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.
        """
        self.config = UserConfigManager(self)
        super().__init__(
            Path.home(),
            CacheManager.MIN_REVISIONS,
            lock_timeout_seconds=lock_timeout_seconds,
        )
        try:
            max_revisions = self.config.get(
                "cache_max_revisions", CacheManager.MIN_REVISIONS
            )
            self._cache_manager.max_revisions = max_revisions
        except FileNotFoundError:
            pass

    def update_config(self: Self, updates: dict[str, Any]) -> UserConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated UserConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return cast("UserConfig", super().update_config(updates))


def get_fmu_directory(
    base_path: str | Path,
    *,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
) -> ProjectFMUDirectory:
    """Initializes access to a .fmu directory.

    Args:
        base_path: The directory containing the .fmu directory or one of its parent
                   dirs
        lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

    Returns:
        FMUDirectory instance

    Raises:
        FileExistsError: If .fmu exists but is not a directory
        FileNotFoundError: If .fmu directory doesn't exist
        PermissionError: If lacking permissions to read/write to the directory

    """
    return ProjectFMUDirectory(base_path, lock_timeout_seconds=lock_timeout_seconds)


def find_nearest_fmu_directory(
    start_path: str | Path = ".",
    *,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
) -> ProjectFMUDirectory:
    """Factory method to find and open the nearest .fmu directory.

    Args:
        start_path: Path to start searching from. Default current working directory
        lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

    Returns:
        FMUDirectory instance

    Raises:
        FileNotFoundError: If no .fmu directory is found
    """
    return ProjectFMUDirectory.find_nearest(
        start_path, lock_timeout_seconds=lock_timeout_seconds
    )
