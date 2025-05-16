from fastapi import APIRouter, Depends, HTTPException
from infrastructure.adapters.google_drive_repository import GoogleDriveRepository, GoogleDriveError
from domain.entities.ebook import Ebook
from infrastructure.api.dependencies import get_drive_repository

router = APIRouter()

@router.get("/drive/ebooks", response_model=list[Ebook])
async def list_ebooks(drive_repository: GoogleDriveRepository = Depends(get_drive_repository)):
    """Liste tous les ebooks disponibles dans le Drive"""
    try:
        return await drive_repository.list_ebooks()
    except GoogleDriveError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail={
                "message": e.message,
                "details": e.details
            }
        )

@router.get("/drive/ebooks/{file_id}", response_model=Ebook)
async def get_ebook(
    file_id: str,
    drive_repository: GoogleDriveRepository = Depends(get_drive_repository)
):
    """Récupère un ebook spécifique par son ID"""
    try:
        ebook = await drive_repository.get_ebook(file_id)
        if not ebook:
            raise HTTPException(
                status_code=404,
                detail="Ebook non trouvé"
            )
        return ebook
    except GoogleDriveError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail={
                "message": e.message,
                "details": e.details
            }
        )

@router.put("/drive/ebooks/{file_id}/status")
async def update_ebook_status(
    file_id: str,
    status: str,
    drive_repository: GoogleDriveRepository = Depends(get_drive_repository)
):
    """Met à jour le statut d'un ebook"""
    try:
        await drive_repository.update_ebook_status(file_id, status)
        return {"message": "Statut mis à jour avec succès"}
    except GoogleDriveError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail={
                "message": e.message,
                "details": e.details
            }
        ) 