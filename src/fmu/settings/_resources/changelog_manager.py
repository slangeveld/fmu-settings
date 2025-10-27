from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Self

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import FileName
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Log

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class ChangelogManager(LogManager):
    """Manages the .fmu changelog file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the Change log resource manager."""
        super().__init__(fmu_dir, Log[ChangeInfo])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / FileName.changelog
