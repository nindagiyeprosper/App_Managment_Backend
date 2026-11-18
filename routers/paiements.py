from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Paiement
from auth import require_admin

router = APIRouter(prefix="/api/paiements", tags=["paiements"])


@router.get("")
def list_paiements(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    rows = db.query(Paiement).order_by(Paiement.id.desc()).all()
    return [
        {
            "id": p.id, "client_id": p.client_id,
            "montant": float(p.montant), "date": p.date,
            "reference": p.reference, "notes": p.notes,
        }
        for p in rows
    ]