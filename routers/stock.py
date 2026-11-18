from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Produit, MouvementStock
from schemas import MouvementIn
from auth import require_admin, get_current_user

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.post("/mouvements")
def create_mouvement(payload: MouvementIn, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    p = db.query(Produit).get(payload.produit_id)
    if not p:
        raise HTTPException(404, "Produit introuvable")

    if payload.type == "entree":
        p.stock += payload.quantite
    elif payload.type == "sortie":
        if p.stock < payload.quantite:
            raise HTTPException(400, "Stock insuffisant")
        p.stock -= payload.quantite
    else:
        raise HTTPException(400, "Type invalide")

    m = MouvementStock(
        produit_id=p.id, type=payload.type,
        quantite=payload.quantite, motif=payload.motif,
        admin_id=admin.id,
    )
    db.add(m)
    db.commit()
    return {"ok": True, "stock": p.stock}


@router.get("/mouvements")
def list_mouvements(db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    return db.query(MouvementStock).order_by(MouvementStock.id.desc()).limit(200).all()