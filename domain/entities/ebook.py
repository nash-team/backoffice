from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class EbookStatus(Enum):
    PENDING = "pending"
    VALIDATED = "validated"

class Ebook(BaseModel):
    id: Optional[int] = None
    title: str
    author: str
    content: str
    status: EbookStatus = EbookStatus.PENDING
    created_at: datetime
    updated_at: datetime
    validated_by: Optional[int] = None
    feedback: Optional[str] = None
    preview_url: Optional[str] = None
    drive_id: Optional[str] = None  # ID du fichier dans Google Drive

@dataclass
class Ebook:
    id: int
    title: str
    author: str
    created_at: datetime
    status: EbookStatus = EbookStatus.PENDING
    preview_url: Optional[str] = None
    drive_id: Optional[str] = None  # ID du fichier dans Google Drive 