from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Produit
from schemas import ProduitIn, ProduitOut
from auth import require_admin

router = APIRouter(prefix="/api/produits", tags=["produits"])


def _out(p: Produit) -> dict:
    return {
        "id": p.id, "nom": p.nom, "categorie": p.categorie,
        "taille": p.taille, "couleur": p.couleur,
        "prix_achat": float(p.prix_achat), "prix_vente": float(p.prix_vente),
        "benefice_unitaire": float(p.prix_vente - p.prix_achat),
        "stock": p.stock, "seuil_alerte": p.seuil_alerte, "actif": p.actif,
    }


@router.get("", response_model=list[ProduitOut])
def list_produits(db: Session = Depends(get_db)):
    return [_out(p) for p in db.query(Produit).filter(Produit.actif == True).all()]


@router.get("/alertes-stock", response_model=list[ProduitOut])
def alertes_stock(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    return [_out(p) for p in db.query(Produit).filter(
        Produit.actif == True, Produit.stock <= Produit.seuil_alerte
    ).all()]


@router.post("", response_model=ProduitOut)
def create_produit(payload: ProduitIn, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    p = Produit(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.put("/{pid}", response_model=ProduitOut)
def update_produit(pid: int, payload: ProduitIn, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    p = db.query(Produit).get(pid)
    if not p:
        raise HTTPException(404, "Produit introuvable")
    for k, v in payload.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.delete("/{pid}")
def delete_produit(pid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    p = db.query(Produit).get(pid)
    if not p:
        raise HTTPException(404, "Produit introuvable")
    p.actif = False
    db.commit()
    return {"ok": True}