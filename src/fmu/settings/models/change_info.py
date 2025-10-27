"""Model for the log entries in the the changelog file."""

from pathlib import Path

from pydantic import AwareDatetime, BaseModel

from fmu.settings.models._enums import ChangeType, FileName


class ChangeInfo(BaseModel):
    """Represents a change in the changelog file."""

    change_type: ChangeType
    date: AwareDatetime
    user: str
    path: Path
    change: str
    hostname: str
    file: FileName
    key: str
