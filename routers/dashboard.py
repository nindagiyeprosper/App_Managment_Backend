from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from models import Client, Produit, Vente, Commission
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/admin")
def admin_dashboard(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    today = datetime.utcnow().date()
    ventes_jour = db.query(func.coalesce(func.sum(Vente.montant_total), 0)).filter(
        func.date(Vente.date) == today, Vente.statut == "payee"
    ).scalar()

    benefice_total = db.query(func.coalesce(func.sum(Vente.benefice_total), 0)).filter(
        Vente.statut == "payee"
    ).scalar()

    commissions_distribuees = db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.statut.in_(["validee", "payee"])
    ).scalar()

    nb_clients = db.query(func.count(Client.id)).scalar()

    top_parrains = db.query(Client).order_by(Client.nb_descendants.desc()).limit(5).all()
    top_parrains_data = [
        {"id": c.id, "nom": c.nom, "nb_descendants": c.nb_descendants,
         "total_commissions": float(db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
             Commission.beneficiaire_id == c.id, Commission.statut.in_(["validee", "payee"])
         ).scalar())}
        for c in top_parrains
    ]

    return {
        "ventes_jour": float(ventes_jour),
        "benefice_total": float(benefice_total),
        "commissions_distribuees": float(commissions_distribuees),
        "nb_clients": nb_clients,
        "top_parrains": top_parrains_data,
        "top_produits": [],
    }


@router.get("/client")
def client_dashboard(db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    attente = db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.beneficiaire_id == user.id, Commission.statut == "calculee"
    ).scalar()

    payees = db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.beneficiaire_id == user.id, Commission.statut == "payee"
    ).scalar()

    nb_achats = db.query(func.count(Vente.id)).filter(Vente.client_id == user.id).scalar()

    return {
        "commissions_attente": float(attente),
        "commissions_payees": float(payees),
        "nb_achats": nb_achats,
    }