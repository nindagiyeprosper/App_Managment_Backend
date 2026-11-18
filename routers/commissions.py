from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Commission, Paiement
from schemas import CommissionOut, PayerIn
from auth import require_admin
from commissions import notifier

router = APIRouter(prefix="/api/commissions", tags=["commissions"])


@router.get("", response_model=list[CommissionOut])
def list_commissions(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    return db.query(Commission).order_by(Commission.id.desc()).all()


@router.put("/{cid}/valider", response_model=CommissionOut)
def valider(cid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    c = db.query(Commission).get(cid)
    if not c:
        raise HTTPException(404, "Commission introuvable")
    if c.statut != "calculee":
        raise HTTPException(400, "Commission non calculée")
    c.statut = "validee"
    c.date_validation = datetime.utcnow()
    notifier(db, c.beneficiaire_id, "commission_validee",
             f"Votre commission #{c.id} ({c.montant} FBu) a été validée")
    db.commit()
    db.refresh(c)
    return c


@router.put("/{cid}/payer", response_model=CommissionOut)
def payer(cid: int, payload: PayerIn, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    c = db.query(Commission).get(cid)
    if not c:
        raise HTTPException(404, "Commission introuvable")
    if c.statut != "validee":
        raise HTTPException(400, "Commission non validée")

    c.statut = "payee"
    c.date_paiement = datetime.utcnow()

    paiement = Paiement(
        client_id=c.beneficiaire_id, montant=c.montant,
        reference=payload.reference, admin_id=admin.id, notes=payload.notes,
    )
    db.add(paiement)
    notifier(db, c.beneficiaire_id, "commission_payee",
             f"Votre commission #{c.id} ({c.montant} FBu) a été payée (ref: {payload.reference})")
    db.commit()
    db.refresh(c)
    return c
@router.delete("/{cid}")
def supprimer_commission(cid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    """Supprimer une commission (si statut = calculee)."""
    c = db.query(Commission).get(cid)
    if not c:
        raise HTTPException(404, "Commission introuvable")
    if c.statut != "calculee":
        raise HTTPException(400, "Impossible : commission déjà validée/payée")

    db.delete(c)
    db.commit()
    return {"ok": True}