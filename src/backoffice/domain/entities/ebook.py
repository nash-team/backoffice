from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EbookStatus(Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"


@dataclass
class Ebook:
    id: int
    title: str
    author: str
    created_at: datetime | None
    status: EbookStatus = EbookStatus.PENDING
    preview_url: str | None = None
    drive_id: str | None = None  # ID du fichier dans Google Drive
