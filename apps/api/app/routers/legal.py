from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas_legal import LegalPlatformAcceptIn, LegalPlatformStatusOut
from ..services.legal_consent import legal_documents, platform_status, record_platform_acceptance


router = APIRouter(prefix="/legal", tags=["Legal"])


@router.get("/documents")
def get_documents():
    return legal_documents()


@router.get("/platform/status", response_model=LegalPlatformStatusOut)
def get_platform_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return platform_status(db, user)


@router.post("/platform/accept", response_model=LegalPlatformStatusOut)
def accept_platform(
    payload: LegalPlatformAcceptIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return record_platform_acceptance(
        db,
        user=user,
        accept_terms=payload.accept_terms,
        accept_privacy=payload.accept_privacy,
    )
