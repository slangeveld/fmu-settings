"""Tests for MappingsManager."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fmu.datamodels.context.mappings import (
    DataSystem,
    RelationType,
    StratigraphyIdentifierMapping,
    StratigraphyMappings,
)

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.mappings_manager import MappingsManager
from fmu.settings.models._enums import ChangeType
from fmu.settings.models.mappings import Mappings

if TYPE_CHECKING:
    from fmu.settings.models.change_info import ChangeInfo
    from fmu.settings.models.log import Log


@pytest.fixture
def stratigraphy_mappings() -> StratigraphyMappings:
    """Returns a valid StratigraphyMappings object."""
    return StratigraphyMappings(
        root=[
            StratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=RelationType.primary,
                source_id="TopVolantis",
                target_id="VOLANTIS GP. Top",
            ),
            StratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=RelationType.alias,
                source_id="TopVOLANTIS",
                target_id="VOLANTIS GP. Top",
            ),
            StratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=RelationType.alias,
                source_id="TOP_VOLANTIS",
                target_id="VOLANTIS GP. Top",
            ),
        ]
    )


def test_mappings_manager_instantiation(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests basic facts about the Mappings resource Manager."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)

    assert mappings_manager.fmu_dir == fmu_dir
    assert mappings_manager.relative_path == Path("mappings.json")

    expected_path = mappings_manager.fmu_dir.path / mappings_manager.relative_path
    assert mappings_manager.path == expected_path
    assert mappings_manager.model_class == Mappings
    assert mappings_manager.exists is False

    with pytest.raises(
        FileNotFoundError, match="Resource file for 'MappingsManager' not found"
    ):
        mappings_manager.load()


def test_mappings_manager_update_stratigraphy_mappings_overwrites_mappings(
    fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: StratigraphyMappings,
) -> None:
    """Tests that updating stratigraphy mappings overwrites existing mappings."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    assert mappings_manager.exists is False

    mappings_manager.update_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.exists is True
    mappings = mappings_manager.load()
    expected_no_of_mappings = 3
    assert len(mappings.stratigraphy) == expected_no_of_mappings
    assert mappings.stratigraphy[0] == stratigraphy_mappings[0]

    new_mapping = StratigraphyIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=RelationType.primary,
        source_id="TopViking",
        target_id="VIKING GP. Top",
    )

    mappings_manager.update_stratigraphy_mappings(
        StratigraphyMappings(root=[new_mapping])
    )

    # Assert that existing mappings are overwritten
    mappings = mappings_manager.load()
    assert len(mappings.stratigraphy) == 1
    assert mappings.stratigraphy[0] == new_mapping


def test_mappings_manager_update_stratigraphy_mappings_writes_to_changelog(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that each update of the stratigraphy mappings, writes to the changelog."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    new_mappings = StratigraphyMappings(
        root=[
            StratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=RelationType.primary,
                source_id="TopViking",
                target_id="VIKING GP. Top",
            )
        ]
    )
    mappings_manager.update_stratigraphy_mappings(new_mappings)

    changelog: Log[ChangeInfo] = mappings_manager.fmu_dir._changelog.load()
    assert len(changelog) == 1
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].file == "mappings.json"
    assert changelog[0].key == "stratigraphy"
    assert f"New value: {new_mappings.model_dump()}" in changelog[0].change

    mappings_manager.update_stratigraphy_mappings(new_mappings)
    mappings_manager.update_stratigraphy_mappings(new_mappings)

    expected_no_of_mappings = 3
    assert len(mappings_manager.fmu_dir._changelog.load()) == expected_no_of_mappings


def test_mappings_manager_diff(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: StratigraphyMappings,
) -> None:
    """Tests that the mappings diff equals the mappings from the incomming resource."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_stratigraphy_mappings(stratigraphy_mappings)

    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)
    new_mapping = StratigraphyIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=RelationType.primary,
        source_id="TopViking",
        target_id="VIKING GP. Top",
    )
    new_mappings_manager.update_stratigraphy_mappings(
        StratigraphyMappings(root=[new_mapping])
    )

    diff = mappings_manager.get_mappings_diff(new_mappings_manager)

    assert diff.stratigraphy is not None
    assert len(diff.stratigraphy) == 1
    assert diff.stratigraphy == new_mappings_manager.load().stratigraphy


def test_mappings_manager_diff_mappings_raises(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: StratigraphyMappings,
) -> None:
    """Exception is raised when any of the mappings resources to diff does not exist.

    When trying to diff two mapping resources, the mappings file must
    exist in both directories in order to make a diff.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)

    expected_exp = (
        "Mappings resources to diff must exist in both directories: "
        "Current mappings resource exists: {}. "
        "Incoming mappings resource exists: {}."
    )

    with pytest.raises(FileNotFoundError, match=expected_exp.format("False", "False")):
        mappings_manager.get_mappings_diff(new_mappings_manager)

    mappings_manager.update_stratigraphy_mappings(stratigraphy_mappings)

    with pytest.raises(FileNotFoundError, match=expected_exp.format("True", "False")):
        mappings_manager.get_mappings_diff(new_mappings_manager)

    with pytest.raises(FileNotFoundError, match=expected_exp.format("False", "True")):
        new_mappings_manager.get_mappings_diff(mappings_manager)

    new_mappings_manager.update_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.get_mappings_diff(new_mappings_manager)


def test_mappings_manager_merge_mappings(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: StratigraphyMappings,
) -> None:
    """Tests that mappings from the incoming resource will overwrite current mappings.

    The current resource should be updated with all the mappings
    from the incoming resource.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_stratigraphy_mappings(stratigraphy_mappings)

    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)
    new_mapping = StratigraphyIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=RelationType.primary,
        source_id="TopViking",
        target_id="VIKING GP. Top",
    )
    new_mappings_manager.update_stratigraphy_mappings(
        StratigraphyMappings(root=[new_mapping])
    )

    assert new_mappings_manager.stratigraphy_mappings is not None
    assert len(new_mappings_manager.stratigraphy_mappings) == 1

    updated_mappings = new_mappings_manager.merge_mappings(mappings_manager)

    excepted_no_of_mappings = 3
    assert updated_mappings.stratigraphy is not None
    assert len(updated_mappings.stratigraphy) == excepted_no_of_mappings
    assert len(new_mappings_manager.stratigraphy_mappings) == excepted_no_of_mappings
    assert updated_mappings.stratigraphy == new_mappings_manager.stratigraphy_mappings
    assert (
        new_mappings_manager.stratigraphy_mappings
        == mappings_manager.stratigraphy_mappings
    )

    mappings = mappings_manager.load()
    mappings.wells = "test"
    mappings_manager.save(mappings)
    assert mappings.wells == "test"

    old_strat = mappings_manager.stratigraphy_mappings
    old_wells = mappings_manager.well_mappings

    new_mappings_manager.save(Mappings())
    updated_mappings = mappings_manager.merge_mappings(new_mappings_manager)

    assert updated_mappings.wells == old_wells
    assert updated_mappings.stratigraphy == old_strat


def test_mappings_manager_merge_changes(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that mappings from the change object will overwrite current mappings.

    The current resource should be updated with all the mappings
    from the change object.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.save(Mappings())

    change_object = Mappings()

    updated_mappings = mappings_manager.merge_changes(change_object)
    assert updated_mappings.stratigraphy is None
    assert updated_mappings.wells is None

    new_mappings = StratigraphyMappings(
        root=[
            StratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=RelationType.primary,
                source_id="TopViking",
                target_id="VIKING GP. Top",
            )
        ]
    )

    change_object.stratigraphy = new_mappings
    updated_mappings = mappings_manager.merge_changes(change_object)

    assert updated_mappings.wells is None
    assert updated_mappings.stratigraphy == new_mappings
    assert mappings_manager.stratigraphy_mappings == new_mappings

    change_object.wells = "test"
    with pytest.raises(NotImplementedError):
        updated_mappings = mappings_manager.merge_changes(change_object)

    old_wells = mappings_manager.well_mappings
    old_strat = mappings_manager.stratigraphy_mappings
    change_object.stratigraphy = None
    change_object.wells = None

    updated_mappings = mappings_manager.merge_changes(change_object)

    assert updated_mappings.wells == old_wells
    assert updated_mappings.stratigraphy == old_strat
