from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class EbookStatus(Enum):
    PENDING = "pending"
    VALIDATED = "validated"


@dataclass
class Ebook:
    id: int
    title: str
    author: str
    created_at: datetime
    status: EbookStatus = EbookStatus.PENDING
    preview_url: Optional[str] = None
    drive_id: Optional[str] = None  # ID du fichier dans Google Drive
