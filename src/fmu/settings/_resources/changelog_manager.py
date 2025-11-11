from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import ChangeType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Log, LogFileName

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class ChangelogManager(LogManager[ChangeInfo]):
    """Manages the .fmu changelog file."""

    cache_enabled: bool = False

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the Change log resource manager."""
        super().__init__(fmu_dir, Log[ChangeInfo])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.changelog

    def log_updates_to_changelog(
        self: Self,
        updates: dict[str, Any],
        old_resource_dict: dict[str, Any],
        file: str,
    ) -> None:
        """Logs the updates to a resource to the changelog."""
        for key, new_value in updates.items():
            change_type = ChangeType.update
            if "." in key:
                old_value = self._get_dot_notation_key(
                    resource_dict=old_resource_dict, key=key
                )
            else:
                old_value = old_resource_dict.get(key)
            if old_value is not None:
                if isinstance(old_value, BaseModel) and isinstance(
                    new_value, BaseModel
                ):
                    old_value_string = str(old_value.model_dump())
                    new_value_string = str(new_value.model_dump())
                else:
                    old_value_string = str(old_value)
                    new_value_string = str(new_value)
                change_string = (
                    f"Updated field '{key}'. Old value: {old_value_string}"
                    f" -> New value: {new_value_string}"
                )
            else:
                change_type = ChangeType.add
                if isinstance(new_value, BaseModel):
                    new_value_string = str(new_value.model_dump())
                else:
                    new_value_string = str(new_value)
                change_string = f"Added field '{key}'. New value: {new_value_string}"

            change_entry = ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=change_type,
                user=os.getenv("USER", "unknown"),
                path=self.fmu_dir.path,
                change=change_string,
                hostname=socket.gethostname(),
                file=file,
                key=key,
            )
            self.add_log_entry(change_entry)
