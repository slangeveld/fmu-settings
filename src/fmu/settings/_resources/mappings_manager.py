from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from fmu.datamodels.context.mappings import (
    StratigraphyMappings,
)
from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager
from fmu.settings.models.mappings import Mappings

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class MappingsManager(PydanticResourceManager[Mappings]):
    """Manages the .fmu mappings file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the mappings resource manager."""
        super().__init__(fmu_dir, Mappings)

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the mappings file."""
        return Path("mappings.json")

    @property
    def stratigraphy_mappings(self: Self) -> StratigraphyMappings | None:
        """Get all stratigraphy mappings."""
        return self.load().stratigraphy

    @property
    def well_mappings(self: Self) -> Any | None:
        """Get all well mappings."""
        return self.load().wells

    def update_stratigraphy_mappings(
        self: Self, strat_mappings: StratigraphyMappings
    ) -> StratigraphyMappings:
        """Updates the stratigraphy mappings in the mappings resource."""
        mappings: Mappings = (
            self.load()
            if self.exists
            else Mappings(stratigraphy=StratigraphyMappings(root=[]))
        )

        old_mappings_dict = copy.deepcopy(mappings.model_dump())
        mappings.stratigraphy = strat_mappings
        self.save(mappings)

        self.fmu_dir._changelog.log_update_to_changelog(
            updates={"stratigraphy": mappings.stratigraphy},
            old_resource_dict=old_mappings_dict,
            relative_path=self.relative_path,
        )

        assert self.stratigraphy_mappings is not None
        return self.stratigraphy_mappings

    def update_well_mappings(self: Self) -> None:
        # TODO: Add well mappings functionality
        raise NotImplementedError

    def get_mappings_diff(self: Self, incoming_mappings: MappingsManager) -> Mappings:
        """Get mappings diff with the incomming mappings resource.

        All mappings from the incomming mappings resource are returned.
        """
        if self.exists and incoming_mappings.exists:
            return incoming_mappings.load()
        raise FileNotFoundError(
            "Mappings resources to diff must exist in both directories: "
            f"Current mappings resource exists: {self.exists}. "
            f"Incoming mappings resource exists: {incoming_mappings.exists}."
        )

    def merge_mappings(self: Self, incoming_mappings: MappingsManager) -> Mappings:
        """Merge the mappings from the incomming mappings resource.

        The current mappings will be updated with the mappings
        from the incoming resource.
        """
        mappings_diff = self.get_mappings_diff(incoming_mappings)
        return self.merge_changes(mappings_diff)

    def merge_changes(self: Self, changes: Mappings) -> Mappings:
        """Merge the mappings changes into the current mappings.

        The current mappings will be updated with the mappings
        in the change object.
        """
        if changes.stratigraphy is not None:
            self.update_stratigraphy_mappings(changes.stratigraphy)
        if changes.wells is not None:
            self.update_well_mappings()
        return self.load()
