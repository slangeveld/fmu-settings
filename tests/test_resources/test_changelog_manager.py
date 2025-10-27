"""Tests for ChangelogManager."""

import copy
import warnings
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.changelog_manager import ChangelogManager
from fmu.settings.models._enums import ChangeType, FileName
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Log


@pytest.fixture
def change_entry() -> ChangeInfo:
    """Returns a valid ChangeInfo object."""
    return ChangeInfo(
        change_type=ChangeType.add,
        date=datetime.now(UTC),
        user="test",
        path=Path("/test_folder"),
        file=FileName.config,
        change="Added new field to smda masterdata.",
        hostname="hostname",
        key="masterdata",
    )


def test_changelog_manager_instantiation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the ChangelogManager."""
    changelog: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog.fmu_dir == fmu_dir
    assert changelog.relative_path == Path("logs") / FileName.changelog
    assert changelog.exists is False
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'ChangelogManager' not found"
    ):
        changelog.load()

    assert changelog.model_class == Log[ChangeInfo]


def test_changelog_manager_add_entry(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding a new entry to a non-existing changelog.

    This should create the changelog file and add the new entry at the end.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource.exists is False
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'ChangelogManager' not found"
    ):
        changelog_resource.load()

    changelog_resource.add_log_entry(change_entry)

    assert changelog_resource.exists is True
    changelog = changelog_resource.load()
    assert changelog.root[0] == change_entry

    changelog_resource.add_log_entry(change_entry)
    changelog_resource.add_log_entry(change_entry)
    expected_log_entries = 3

    updated_changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(updated_changelog.root) == expected_log_entries


def test_changelog_manager_add_invalid_entry(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding an invalid entry to an existing changelog.

    This should raise a Value error and not add the invalid log entry.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource.exists

    change_entry_with_issues = copy.deepcopy(change_entry)
    del change_entry_with_issues.change_type

    with pytest.raises(
        ValueError, match="Invalid log entry added to 'ChangelogManager'"
    ):
        changelog_resource.add_log_entry(change_entry_with_issues)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(changelog.root) == 1
    assert changelog.root[0] == change_entry


def test_changelog_manager_add_invalid_entry_no_file_created(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding an invalid entry to a non-existing changelog.

    This should raise a Value error and not create the changelog file.
    """
    changelog: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog.exists is False

    change_entry_with_issues = copy.deepcopy(change_entry)
    change_entry_with_issues.change_type = "invalid change_type"  # type: ignore

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with pytest.raises(
            ValueError, match="Invalid log entry added to 'ChangelogManager'"
        ):
            changelog.add_log_entry(change_entry_with_issues)

    assert changelog.exists is False
