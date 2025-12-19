"""Model for the mappings.json file."""

from typing import Any

from pydantic import BaseModel, Field

from fmu.datamodels.context.mappings import StratigraphyMappings


class Mappings(BaseModel):
    """Represents the mappings file in a .fmu directory."""

    stratigraphy: StratigraphyMappings | None = Field(default=None)
    """Stratigraphy mappings in the mappings file."""

    wells: Any | None = Field(default=None)  # Todo: Add wells
    """Well mappings in the mappings file."""
