from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import ChangeType, FilterType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Filter, Log, LogFileName

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class ChangelogManager(LogManager[ChangeInfo]):
    """Manages the .fmu changelog file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the Change log resource manager."""
        super().__init__(fmu_dir, Log[ChangeInfo])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.changelog

    def log_update_to_changelog(
        self: Self,
        updates: dict[str, Any],
        old_resource_dict: dict[str, Any],
        relative_path: Path,
    ) -> None:
        """Logs the update of a resource to the changelog."""
        _MISSING_KEY = object()
        for key, new_value in updates.items():
            change_type = ChangeType.update
            if "." in key:
                old_value = self._get_dot_notation_key(
                    resource_dict=old_resource_dict, key=key, default=_MISSING_KEY
                )
            else:
                old_value = old_resource_dict.get(key, _MISSING_KEY)

            if old_value != _MISSING_KEY:
                old_value_string = (
                    str(old_value.model_dump())
                    if isinstance(old_value, BaseModel)
                    else str(old_value)
                )
                new_value_string = (
                    str(new_value.model_dump())
                    if isinstance(new_value, BaseModel)
                    else str(new_value)
                )
                change_string = (
                    f"Updated field '{key}'. Old value: {old_value_string}"
                    f" -> New value: {new_value_string}"
                )
            else:
                change_type = ChangeType.add
                new_value_string = (
                    str(new_value.model_dump())
                    if isinstance(new_value, BaseModel)
                    else str(new_value)
                )
                change_string = f"Added field '{key}'. New value: {new_value_string}"

            change_entry = ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=change_type,
                user=os.getenv("USER", "unknown"),
                path=self.fmu_dir.path,
                change=change_string,
                hostname=socket.gethostname(),
                file=str(relative_path),
                key=key,
            )
            self.add_log_entry(change_entry)

    def log_merge_to_changelog(
        self: Self, source_path: Path, incoming_path: Path, merged_resources: list[str]
    ) -> None:
        """Logs a change entry with merge details to the changelog."""
        resources_string = ", ".join([f"'{resource}'" for resource in merged_resources])
        change_string = (
            f"Merged resources {resources_string} from "
            f"'{incoming_path}' into '{source_path}'."
        )
        self.add_log_entry(
            ChangeInfo(
                timestamp=datetime.now(UTC),
                change_type=ChangeType.merge,
                user=os.getenv("USER", "unknown"),
                path=source_path,
                change=change_string,
                hostname=socket.gethostname(),
                file=resources_string,
                key=".fmu",
            )
        )

    def _get_latest_change_timestamp(self: Self) -> datetime:
        """Get the timestamp of the latest change entry in the changelog."""
        return self.load()[-1].timestamp

    def get_changelog_diff(
        self: Self, incoming_changelog: ChangelogManager
    ) -> Log[ChangeInfo]:
        """Get new entries from the incoming changelog.

        All log entries from the incoming changelog newer than the
        log entries in the current changelog are returned.
        """
        if self.exists and incoming_changelog.exists:
            starting_point = self._get_latest_change_timestamp()
            return incoming_changelog.filter_log(
                Filter(
                    field_name="timestamp",
                    filter_value=str(starting_point),
                    filter_type=FilterType.date,
                    operator=">",
                )
            )
        raise FileNotFoundError(
            "Changelog resources to diff must exist in both directories: "
            f"Current changelog resource exists: {self.exists}. "
            f"Incoming changelog resource exists: {incoming_changelog.exists}."
        )

    def merge_changelog(
        self: Self, incoming_changelog: ChangelogManager
    ) -> Log[ChangeInfo]:
        """Add new entries from the incoming changelog to the current changelog.

        All log entries from the incoming changelog newer than the
        log entries in the current changelog are added.
        """
        new_log_entries = self.get_changelog_diff(incoming_changelog)
        return self.merge_changes(new_log_entries.root)

    def merge_changes(self: Self, change: list[ChangeInfo]) -> Log[ChangeInfo]:
        """Merge a list of changes into the current changelog.

        All log entries in the change object are added to the changelog.
        """
        for entry in change:
            self.add_log_entry(entry)
        return self.load()
