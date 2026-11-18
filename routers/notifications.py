from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Notification
from auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    return db.query(Notification).filter(
        Notification.client_id == user.id
    ).order_by(Notification.id.desc()).all()


@router.put("/{nid}/lu")
def marquer_lu(nid: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    n = db.query(Notification).get(nid)
    if not n or n.client_id != user.id:
        raise HTTPException(404, "Notification introuvable")
    n.lu = True
    db.commit()
    return {"ok": True}