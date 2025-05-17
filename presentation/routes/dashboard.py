from fastapi import APIRouter
from domain.usecases.get_stats import GetStatsUseCase
from domain.usecases.get_ebooks import GetEbooksUseCase
from infrastructure.adapters.in_memory_ebook_repository import InMemoryEbookRepository
from domain.entities.ebook import Ebook, EbookStatus
from datetime import datetime

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

# Repo et usecases (singleton pour garder les données en mémoire)
repo = InMemoryEbookRepository()
get_stats_usecase = GetStatsUseCase(repo)
get_ebooks_usecase = GetEbooksUseCase(repo)

# Données de test au démarrage
if not repo.ebooks:
    repo.ebooks.extend([
        Ebook(1, "Python pour les débutants", "John Doe", datetime.now(), EbookStatus.PENDING, drive_id="1FoBXPTsVO1GQ-WDLCAgGAuJm8jfMXjsS"),
        Ebook(2, "FastAPI Masterclass", "Jane Smith", datetime.now(), EbookStatus.VALIDATED, drive_id="1FoBXPTsVO1GQ-WDLCAgGAuJm8jfMXjsS"),
        Ebook(3, "Django REST", "Alice Johnson", datetime.now(), EbookStatus.PENDING, drive_id="1FoBXPTsVO1GQ-WDLCAgGAuJm8jfMXjsS")
    ])

@router.get("/stats")
async def get_stats():
    stats = await get_stats_usecase.execute()
    return stats.__dict__

@router.get("/ebooks")
async def get_ebooks(status: str = None):
    from typing import Optional
    ebook_status = None
    if status == "pending":
        ebook_status = EbookStatus.PENDING
    elif status == "validated":
        ebook_status = EbookStatus.VALIDATED
    ebooks = await get_ebooks_usecase.execute(ebook_status)
    # Sérialisation simple
    return [
        {
            "id": e.id,
            "title": e.title,
            "author": e.author,
            "created_at": e.created_at.isoformat(),
            "status": e.status.value,
            "drive_id": e.drive_id
        } for e in ebooks
    ] 