"""Root model for the log file."""

from typing import TypeVar

from pydantic import BaseModel, RootModel

GenericLogEntry = TypeVar("GenericLogEntry", bound=BaseModel)


class Log(RootModel[list[GenericLogEntry]]):
    """Represents a log file in a .fmu directory."""
