from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates
from domain.usecases.get_stats import GetStatsUseCase
from domain.usecases.get_ebooks import GetEbooksUseCase
from infrastructure.adapters.in_memory_ebook_repository import InMemoryEbookRepository
from domain.entities.ebook import Ebook, EbookStatus
from datetime import datetime

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

templates = Jinja2Templates(directory="presentation/templates")

# Ajout du filtre de date
def format_date(value):
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return value

templates.env.filters["date"] = format_date

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
async def get_stats(request: Request):
    stats = await get_stats_usecase.execute()
    return templates.TemplateResponse(
        "partials/stats.html",
        {"request": request, "stats": stats.__dict__}
    )

@router.get("/ebooks")
async def get_ebooks(request: Request, status: str = None):
    from typing import Optional
    ebook_status = None
    if status == "pending":
        ebook_status = EbookStatus.PENDING
    elif status == "validated":
        ebook_status = EbookStatus.VALIDATED
    ebooks = await get_ebooks_usecase.execute(ebook_status)
    
    # Sérialisation pour le template
    ebooks_data = [
        {
            "id": e.id,
            "title": e.title,
            "author": e.author,
            "created_at": e.created_at,
            "status": e.status.value,
            "drive_id": e.drive_id
        } for e in ebooks
    ]
    
    return templates.TemplateResponse(
        "partials/ebooks_table.html",
        {"request": request, "ebooks": ebooks_data}
    )

@router.get("/drive/ebooks/{drive_id}")
async def get_ebook_preview(drive_id: str):
    # Simuler une URL de prévisualisation Google Drive
    preview_url = f"https://drive.google.com/file/d/{drive_id}/preview"
    return Response(content=preview_url, media_type="text/plain") 