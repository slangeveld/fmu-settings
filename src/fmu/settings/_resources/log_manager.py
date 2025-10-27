from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Self

from pydantic import ValidationError

from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager
from fmu.settings.models.log import Log, LogEntryType

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class LogManager(PydanticResourceManager[Log[LogEntryType]], Generic[LogEntryType]):
    """Manages the .fmu log files."""

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, model_class: type[Log[LogEntryType]]
    ) -> None:
        """Initializes the log resource manager."""
        super().__init__(fmu_dir, model_class)

    def add_log_entry(self: Self, log_entry: LogEntryType) -> None:
        """Adds a log entry to the log resource."""
        try:
            validated_entry = log_entry.model_validate(log_entry.model_dump())
            log_model: Log[LogEntryType] = (
                self.load() if self.exists else self.model_class([])
            )
            log_model.add_entry(validated_entry)
            self.save(log_model)
        except ValidationError as e:
            raise ValueError(
                f"Invalid log entry added to '{self.__class__.__name__}' with "
                f"value '{log_entry}': '{e}"
            ) from e
