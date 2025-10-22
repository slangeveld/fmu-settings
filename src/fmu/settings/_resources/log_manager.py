from __future__ import annotations

from typing import TYPE_CHECKING, Self, TypeVar

from pydantic import BaseModel, ValidationError

from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )

T = TypeVar("T", bound=BaseModel)
S = TypeVar("S", bound=BaseModel)


class LogManager(PydanticResourceManager[T]):
    """Manages the .fmu log files."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase, model_class: type[T]) -> None:
        """Initializes the log resource manager."""
        super().__init__(fmu_dir, model_class)

    def add_log_entry(self: Self, log_entry: S) -> None:
        """Adds a log entry to the log resource."""
        try:
            log_entry.model_validate(log_entry.model_dump())
            log_model = self.load() if self.exists else self.model_class(log=[])
            log_model.log.append(log_entry)  # type: ignore
            self.save(log_model)
        except ValidationError as e:
            raise ValueError(
                f"Invalid log entry added to '{self.__class__.__name__}' with "
                f"value '{log_entry}': '{e}"
            ) from e
