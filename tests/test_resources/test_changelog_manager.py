"""Tests for ChangelogManager."""

import copy
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas
import pytest

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.changelog_manager import ChangelogManager
from fmu.settings.models._enums import ChangeType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Filter, Log, LogFileName

DATE_TIME_NOW = datetime.now(UTC)


@pytest.fixture
def change_entry() -> ChangeInfo:
    """Returns a valid ChangeInfo object."""
    return ChangeInfo(
        timestamp=DATE_TIME_NOW,
        change_type=ChangeType.add,
        user="test",
        path=Path("/test_folder"),
        file="config.json",
        change="Added new field to smda masterdata.",
        hostname="hostname",
        key="masterdata",
    )


@pytest.fixture
def change_entry_list() -> list[ChangeInfo]:
    """Returns a list of valid ChangeInfo entries."""
    return [
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(days=2),
            change_type=ChangeType.add,
            user="user_first_entry",
            path=Path("/path_first_entry"),
            file="config.json",
            change="Added new field.",
            hostname="hostname_first_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(days=1),
            change_type=ChangeType.update,
            user="user_second_entry",
            path=Path("/path_second_entry"),
            file="config.json",
            change="Updated field.",
            hostname="hostname_second_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW,
            change_type=ChangeType.remove,
            user="user_third_entry",
            path=Path("/path_third_entry"),
            file="config.json",
            change="Removed field.",
            hostname="hostname_third_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW,
            change_type=ChangeType.reset,
            user="user_fourth_entry",
            path=Path("/path_fourth_entry"),
            file="config.json",
            change="Reset field.",
            hostname="hostname_fourth_entry",
            key="masterdata",
        ),
    ]


def test_changelog_manager_instantiation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the ChangelogManager."""
    changelog: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog.fmu_dir == fmu_dir
    assert changelog.relative_path == Path("logs") / LogFileName.changelog
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
    assert changelog[0] == change_entry

    changelog_resource.add_log_entry(change_entry)
    changelog_resource.add_log_entry(change_entry)
    expected_log_entries = 3

    updated_changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(updated_changelog) == expected_log_entries


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
        ValueError, match=r"Invalid log entry added to 'Log\[ChangeInfo\]' "
    ):
        changelog_resource.add_log_entry(change_entry_with_issues)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(changelog) == 1
    assert changelog[0] == change_entry


def test_changelog_manager_add_invalid_entry_no_file_created(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding an invalid entry to a non-existing changelog.

    This should raise a Value error and not create the changelog file.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource.exists is False

    change_entry_with_issues = copy.deepcopy(change_entry)
    change_entry_with_issues.change_type = "invalid change_type"  # type: ignore

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with pytest.raises(
            ValueError, match=r"Invalid log entry added to 'Log\[ChangeInfo\]' "
        ):
            changelog_resource.add_log_entry(change_entry_with_issues)

    assert changelog_resource.exists is False


def test_changelog_filter_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with == operator.

    The filter should return all changelog entries where the value of the field
    `field_name` equals the filter value.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type="str",
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 1
    assert filtered_log[0] == changelog[0]

    filter = Filter(
        field_name="user",
        filter_value="user_second_entry",
        filter_type="str",
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 1
    assert filtered_log[0] == changelog[1]

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW),
        filter_type="datetime",
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp == DATE_TIME_NOW for entry in filtered_log)

    filter = Filter(
        field_name="change",
        filter_value="Changed field.",
        filter_type="str",
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_not_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with != operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is not equal to the filter value.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type="str",
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.change_type is not ChangeType.add for entry in filtered_log)

    filter = Filter(
        field_name="user",
        filter_value="user_second_entry",
        filter_type="str",
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.user != "user_second_entry" for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW),
        filter_type="datetime",
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp != DATE_TIME_NOW for entry in filtered_log)

    filter = Filter(
        field_name="key", filter_value="masterdata", filter_type="str", operator="!="
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_less_or_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with <= operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is less or equal to the filter value. Attempts to filter
    strings with the <= operator should raise an exception.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type="str",
        operator="<=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator <= applied to 'str' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type="str",
        operator="<=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator <= applied to 'str' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type="datetime",
        operator="<=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp <= yesterday for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW - timedelta(days=3)),
        filter_type="datetime",
        operator="<=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_greater_or_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with >= operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is greater or equal to the filter value. Attempts to filter
    strings with the >= operator should raise an exception.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type="str",
        operator=">=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator >= applied to 'str' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type="str",
        operator=">=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator >= applied to 'str' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type="datetime",
        operator=">=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp >= yesterday for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW + timedelta(days=1)),
        filter_type="datetime",
        operator=">=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_dataframe_cached_after_filtering(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests that _cached_dataframe is set after filtering has been applied."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource._cached_dataframe is None
    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource._cached_dataframe is None

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type="str",
        operator="==",
    )
    changelog_resource.filter_log(filter)
    assert changelog_resource._cached_dataframe is not None


def test_changelog_dataframe_cache_cleared(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests that _cached_dataframe is cleared when the changelog is updated."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource._cached_dataframe is None

    changelog_resource._cached_dataframe = pandas.DataFrame(["some_data"])
    assert changelog_resource._cached_dataframe is not None

    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource._cached_dataframe is None
