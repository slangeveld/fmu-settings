from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Self

import pandas
from pydantic import ValidationError

from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager
from fmu.settings.models.log import Filter, Log, LogEntryType

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
        self._cached_dataframe: pandas.DataFrame | None = None
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
            self._cached_dataframe = None
        except ValidationError as e:
            raise ValueError(
                f"Invalid log entry added to '{self.model_class.__name__}' with "
                f"value '{log_entry}': '{e}"
            ) from e

    def filter_log(self: Self, filter: Filter) -> Log[LogEntryType]:
        """Filters the log resource with the provided filter."""
        if self._cached_dataframe is None:
            if not self.exists:
                raise FileNotFoundError(
                    f"Resource file for '{self.__class__.__name__}' not found "
                    f"at: '{self.path}'"
                )
            log_model: Log[LogEntryType] = self.load()
            df_log = pandas.DataFrame([entry.__dict__ for entry in log_model])
            self._cached_dataframe = df_log
        df_log = self._cached_dataframe

        match filter.operator:
            case "==":
                filtered_df = df_log[df_log[filter.field_name] == filter.filter_value]
            case "!=":
                filtered_df = df_log[df_log[filter.field_name] != filter.filter_value]
            case "<=":
                if filter.filter_type == "str":
                    raise ValueError(
                        f"Invalid filter operator <= applied to 'str' field "
                        f"{filter.field_name} when filterting log resource "
                        f"{self.model_class.__name__} with value {filter.filter_value}."
                    )
                filtered_df = df_log[df_log[filter.field_name] <= filter.filter_value]
            case ">=":
                if filter.filter_type == "str":
                    raise ValueError(
                        f"Invalid filter operator >= applied to 'str' field "
                        f"{filter.field_name} when filterting log resource "
                        f"{self.model_class.__name__} with value {filter.filter_value}."
                    )
                filtered_df = df_log[df_log[filter.field_name] >= filter.filter_value]
            case _:
                raise ValueError(
                    f"Invalid filter operator applied when "
                    f"filterting log resource {self.model_class.__name__} "
                )

        filtered_dict = filtered_df.to_dict("records")
        return self.model_class.model_validate(filtered_dict)
