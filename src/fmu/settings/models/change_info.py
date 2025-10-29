"""Model for the log entries in the the changelog file."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from fmu.settings.models._enums import ChangeType


class ChangeInfo(BaseModel):
    """Represents a change in the changelog file."""

    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    change_type: ChangeType
    user: str
    path: Path
    change: str
    hostname: str
    file: Literal["config.json"]
    key: str
