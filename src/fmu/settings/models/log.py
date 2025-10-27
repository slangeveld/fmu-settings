"""Root model for the log file."""

from typing import Any, Self, TypeVar

from pydantic import BaseModel, Field, RootModel

LogEntryType = TypeVar("LogEntryType", bound=BaseModel)


class Log(RootModel[list[LogEntryType]]):
    """Represents a log file in a .fmu directory."""

    root: list[LogEntryType] = Field(default_factory=list)

    def add_entry(self: Self, entry: LogEntryType) -> None:
        """Adds a log entry to the log."""
        self.root.append(entry)

    def __getitem__(self: Self, index: int) -> LogEntryType:
        """Retrieves a log entry from the log using the specified index."""
        return self.root[index]

    def __iter__(self: Self) -> Any:
        """Returns an iterator for the log."""
        return iter(self.root)

    def __len__(self: Self) -> int:
        """Returns the number of log entries in the log."""
        return len(self.root)
