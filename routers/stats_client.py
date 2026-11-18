from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Client, Commission, Vente, LigneVente, Produit
from auth import get_current_user

router = APIRouter(prefix="/api/stats-client", tags=["stats-client"]) 
# ============================================================
# STATS GÉNÉRALES DU CLIENT
# ============================================================
@router.get("")
def mes_stats(
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    # --- KPI ---
    total_gains = float(db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.beneficiaire_id == user.id,
        Commission.statut.in_(["validee", "payee"])
    ).scalar())

    # ✅ Compatible SQLite : strftime au lieu de date_trunc
    gains_mois = float(db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.beneficiaire_id == user.id,
        Commission.statut.in_(["validee", "payee"]),
        func.strftime("%Y-%m", Commission.date_calcul) == func.strftime("%Y-%m", func.date("now")),
    ).scalar())

    en_attente = float(db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
        Commission.beneficiaire_id == user.id,
        Commission.statut == "calculee",
    ).scalar())

    nb_filleuls = db.query(func.count(Client.id)).filter(Client.parrain_id == user.id).scalar()

    # --- Évolution mensuelle ---
    rows = db.query(
        func.strftime("%Y-%m", Commission.date_calcul).label("mois"),
        func.coalesce(func.sum(Commission.montant), 0).label("total"),
        func.count(Commission.id).label("nb"),
    ).filter(
        Commission.beneficiaire_id == user.id,
        Commission.statut.in_(["validee", "payee"]),
    ).group_by("mois").order_by("mois").all()

    evolution = []
    cumul = 0.0
    for r in rows:
        cumul += float(r.total)
        evolution.append({
            "mois": r.mois,
            "total": float(r.total),
            "nb": r.nb,
            "cumul": round(cumul, 2),
        })

    # --- Répartition par niveau ---
    par_niveau = []
    for niv in (1, 2, 3):
        montant = float(db.query(func.coalesce(func.sum(Commission.montant), 0)).filter(
            Commission.beneficiaire_id == user.id,
            Commission.statut.in_(["validee", "payee"]),
            Commission.niveau == niv,
        ).scalar())
        count = db.query(Commission).filter(
            Commission.beneficiaire_id == user.id,
            Commission.statut.in_(["validee", "payee"]),
            Commission.niveau == niv,
        ).count()
        par_niveau.append({"niveau": f"N{niv}", "montant": montant, "count": count})

    # --- Croissance du réseau ---
    reseau_rows = db.query(
        func.strftime("%Y-%m", Client.date_inscription).label("mois"),
        func.count(Client.id).label("nb"),
    ).filter(Client.parrain_id == user.id).group_by("mois").order_by("mois").all()

    reseau_evolution = [{"mois": r.mois, "nb": r.nb} for r in reseau_rows]

    # --- Moyenne globale ---
    moy_gains = float(db.query(func.coalesce(func.avg(Commission.montant), 0)).filter(
        Commission.statut.in_(["validee", "payee"])
    ).scalar())

    return {
        "kpi": {
            "total_gains": total_gains,
            "gains_mois": gains_mois,
            "en_attente": en_attente,
            "nb_filleuls": nb_filleuls,
            "moyenne_gains_tous_clients": moy_gains,
        },
        "evolution": evolution,
        "par_niveau": par_niveau,
        "reseau_evolution": reseau_evolution,
    }


# ============================================================
# ✅ NOUVELLE ROUTE : STATS ACHATS DU CLIENT
# ============================================================
@router.get("/achats")
def mes_achats_stats(
    debut: str | None = None,
    fin: str | None = None,
    group_by: str = "mois",
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    """Statistiques détaillées des achats du client connecté."""
    now = datetime.utcnow()
    d_debut = datetime.fromisoformat(debut) if debut else now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    d_fin = datetime.fromisoformat(fin) if fin else now

    # --- KPI achats ---
    ventes_q = db.query(Vente).filter(
        Vente.client_id == user.id,
        Vente.date.between(d_debut, d_fin),
        Vente.statut == "payee",
    )
    total_achats = float(ventes_q.with_entities(func.coalesce(func.sum(Vente.montant_total), 0)).scalar())
    nb_commandes = ventes_q.count()
    panier_moyen = round(total_achats / nb_commandes, 2) if nb_commandes > 0 else 0

    dernier = db.query(Vente).filter(
        Vente.client_id == user.id, Vente.statut == "payee"
    ).order_by(Vente.date.desc()).first()
    dernier_achat = {
        "date": dernier.date.isoformat() if dernier else None,
        "montant": float(dernier.montant_total) if dernier else 0,
    }

    # --- Évolution par période (SQLite compatible) ---
    if group_by == "jour":
        fmt = "%Y-%m-%d"
    elif group_by == "semaine":
        fmt = "%Y-W%W"
    elif group_by == "mois":
        fmt = "%Y-%m"
    else:
        fmt = "%Y"

    rows = db.query(
        func.strftime(fmt, Vente.date).label("periode"),
        func.coalesce(func.sum(Vente.montant_total), 0).label("total"),
        func.count(Vente.id).label("nb"),
    ).filter(
        Vente.client_id == user.id,
        Vente.date.between(d_debut, d_fin),
        Vente.statut == "payee",
    ).group_by("periode").order_by("periode").all()

    evolution = [
        {"periode": r.periode, "total": float(r.total), "nb": r.nb}
        for r in rows
    ]

    # --- Répartition par catégorie ---
    cat_rows = db.query(
        Produit.categorie,
        func.coalesce(func.sum(LigneVente.sous_total), 0).label("total"),
        func.coalesce(func.sum(LigneVente.quantite), 0).label("quantite"),
    ).join(Produit, Produit.id == LigneVente.produit_id)\
     .join(Vente, Vente.id == LigneVente.vente_id)\
     .filter(
         Vente.client_id == user.id,
         Vente.date.between(d_debut, d_fin),
         Vente.statut == "payee",
     )\
     .group_by(Produit.categorie).order_by(func.sum(LigneVente.sous_total).desc()).all()

    par_categorie = [
        {"categorie": r.categorie, "total": float(r.total), "quantite": int(r.quantite)}
        for r in cat_rows
    ]

    # --- Top produits ---
    top_rows = db.query(
        Produit.nom,
        func.coalesce(func.sum(LigneVente.quantite), 0).label("quantite"),
        func.coalesce(func.sum(LigneVente.sous_total), 0).label("total"),
    ).join(LigneVente, LigneVente.produit_id == Produit.id)\
     .join(Vente, Vente.id == LigneVente.vente_id)\
     .filter(
         Vente.client_id == user.id,
         Vente.date.between(d_debut, d_fin),
         Vente.statut == "payee",
     )\
     .group_by(Produit.nom).order_by(func.sum(LigneVente.quantite).desc()).limit(5).all()

    top_produits = [
        {"nom": r.nom, "quantite": int(r.quantite), "total": float(r.total)}
        for r in top_rows
    ]

    return {
        "periode": {"debut": d_debut.isoformat(), "fin": d_fin.isoformat(), "group_by": group_by},
        "kpi_achats": {
            "total_achats": total_achats,
            "nb_commandes": nb_commandes,
            "panier_moyen": panier_moyen,
            "dernier_achat": dernier_achat,
        },
        "evolution": evolution,
        "par_categorie": par_categorie,
        "top_produits": top_produits,
    }