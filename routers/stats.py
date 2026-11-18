from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np
from scipy import stats as scipy_stats

from database import get_db
from models import Client, Produit, Vente, LigneVente, Commission
from auth import require_admin

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _bornes(debut: str | None, fin: str | None):
    now = datetime.utcnow()
    if not debut:
        debut = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not fin:
        fin = now.isoformat()
    return datetime.fromisoformat(debut), datetime.fromisoformat(fin)


def _descr(values: list[float]) -> dict:
    """Statistiques descriptives complètes d'une série."""
    arr = np.array([v for v in values if v is not None], dtype=float)
    n = len(arr)
    if n == 0:
        return {
            "n": 0, "moyenne": 0, "mediane": 0, "mode": None,
            "min": 0, "max": 0, "etendue": 0,
            "variance": 0, "ecart_type": 0, "cv_pct": 0,
            "q1": 0, "q3": 0, "iqr": 0,
            "skewness": 0, "kurtosis": 0,
        }

    moyenne = float(np.mean(arr))
    variance = float(np.var(arr, ddof=1)) if n > 1 else 0.0
    ecart_type = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    q1, q3 = (float(x) for x in np.percentile(arr, [25, 75]))

    # Mode : valeur la plus fréquente (arrondie à 2 décimales)
    try:
        mode_arr = scipy_stats.mode(np.round(arr, 2), keepdims=False)
        mode_val = float(mode_arr.mode) if mode_arr.count > 1 else None
    except Exception:
        mode_val = None

    return {
        "n": n,
        "moyenne": round(moyenne, 2),
        "mediane": round(float(np.median(arr)), 2),
        "mode": round(mode_val, 2) if mode_val is not None else None,
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "etendue": round(float(np.max(arr) - np.min(arr)), 2),
        "variance": round(variance, 2),
        "ecart_type": round(ecart_type, 2),
        "cv_pct": round(ecart_type / moyenne * 100, 2) if moyenne != 0 else 0,
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(q3 - q1, 2),
        "skewness": round(float(scipy_stats.skew(arr, bias=False)), 3) if n > 2 else 0,
        "kurtosis": round(float(scipy_stats.kurtosis(arr, bias=False)), 3) if n > 3 else 0,
    }


def _tendance(periodes: list[str], valeurs: list[float]) -> dict:
    """Régression linéaire : pente, R², direction."""
    if len(valeurs) < 2:
        return {"pente": 0, "r2": 0, "direction": "stable", "evolution_pct": 0}

    x = np.arange(len(valeurs), dtype=float)
    y = np.array(valeurs, dtype=float)
    slope, intercept, r_value, _, _ = scipy_stats.linregress(x, y)

    # % d'évolution : (dernier - premier) / premier
    if y[0] != 0:
        evo = (y[-1] - y[0]) / y[0] * 100
    else:
        evo = 0

    direction = "hausse" if slope > 0 else ("baisse" if slope < 0 else "stable")

    return {
        "pente": round(float(slope), 2),
        "r2": round(float(r_value ** 2), 4),
        "direction": direction,
        "evolution_pct": round(float(evo), 2),
    }


@router.get("")
def get_stats(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    group_by: str = Query("jour", pattern="^(jour|semaine|mois|annee)$"),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)

    # ---------- KPI ----------
    ventes_q = db.query(Vente).filter(
        Vente.date.between(d_debut, d_fin), Vente.statut == "payee"
    )
    nb_ventes = ventes_q.count()
    total_ventes = float(ventes_q.with_entities(func.coalesce(func.sum(Vente.montant_total), 0)).scalar())
    total_benefice = float(ventes_q.with_entities(func.coalesce(func.sum(Vente.benefice_total), 0)).scalar())

    comms_q = db.query(Commission).filter(
        Commission.date_calcul.between(d_debut, d_fin),
        Commission.statut.in_(["validee", "payee"])
    )
    total_commissions = float(comms_q.with_entities(func.coalesce(func.sum(Commission.montant), 0)).scalar())

    # ---------- Données brutes pour stats descriptives ----------
    montants = [float(v.montant_total) for v in ventes_q.all()]
    benefices = [float(v.benefice_total) for v in ventes_q.all()]
    comm_montants = [float(c.montant) for c in comms_q.all()]

    descr_ventes = _descr(montants)
    descr_benefices = _descr(benefices)
    descr_commissions = _descr(comm_montants)

    # ---------- Répartition par niveau ----------
    par_niveau = []
    for niv in (1, 2, 3):
        q = db.query(Commission).filter(
            Commission.date_calcul.between(d_debut, d_fin),
            Commission.statut.in_(["validee", "payee"]),
            Commission.niveau == niv
        )
        par_niveau.append({
            "niveau": f"N{niv}",
            "montant": float(q.with_entities(func.coalesce(func.sum(Commission.montant), 0)).scalar()),
            "count": q.count(),
        })

    # ---------- Évolution groupée ----------
    fmt = {"jour": "YYYY-MM-DD", "semaine": 'IYYY-"S"IW', "mois": "YYYY-MM", "annee": "YYYY"}[group_by]

    rows = db.query(
        func.to_char(Vente.date, fmt).label("periode"),
        func.coalesce(func.sum(Vente.montant_total), 0).label("ventes"),
        func.coalesce(func.sum(Vente.benefice_total), 0).label("benefice"),
        func.count(Vente.id).label("nb"),
    ).filter(
        Vente.date.between(d_debut, d_fin),
        Vente.statut == "payee",
    ).group_by("periode").order_by("periode").all()

    evolution = []
    cumul = 0.0
    for r in rows:
        cumul += float(r.ventes)
        evolution.append({
            "periode": r.periode,
            "ventes": float(r.ventes),
            "benefice": float(r.benefice),
            "nb": r.nb,
            "cumul": round(cumul, 2),
        })

    # Tendance sur les ventes
    tendance_ventes = _tendance([e["periode"] for e in evolution], [e["ventes"] for e in evolution])

    # ---------- Histogramme (bins automatiques) ----------
    histogramme = []
    if montants:
        arr = np.array(montants)
        counts, bins = np.histogram(arr, bins=min(10, max(3, len(arr) // 2)))
        for i in range(len(counts)):
            histogramme.append({
                "bin": f"{int(bins[i])}-{int(bins[i+1])}",
                "count": int(counts[i]),
            })

    # ---------- Top produits ----------
    top_produits_rows = db.query(
        Produit.nom,
        func.sum(LigneVente.quantite).label("quantite"),
        func.sum(LigneVente.benefice_ligne).label("benefice"),
    ).join(LigneVente, LigneVente.produit_id == Produit.id)\
     .join(Vente, Vente.id == LigneVente.vente_id)\
     .filter(Vente.date.between(d_debut, d_fin), Vente.statut == "payee")\
     .group_by(Produit.nom).order_by(func.sum(LigneVente.quantite).desc()).limit(5).all()

    top_produits = [
        {"nom": r.nom, "quantite": int(r.quantite), "benefice": float(r.benefice or 0)}
        for r in top_produits_rows
    ]

    # ---------- Top parrains ----------
    top_parrains_rows = db.query(
        Client.nom,
        func.count(Commission.id).label("nb"),
        func.coalesce(func.sum(Commission.montant), 0).label("total"),
    ).join(Commission, Commission.beneficiaire_id == Client.id)\
     .filter(
         Commission.date_calcul.between(d_debut, d_fin),
         Commission.statut.in_(["validee", "payee"]),
     )\
     .group_by(Client.nom).order_by(func.sum(Commission.montant).desc()).limit(5).all()

    top_parrains = [
        {"nom": r.nom, "nb": r.nb, "total": float(r.total)}
        for r in top_parrains_rows
    ]

    return {
        "periode": {"debut": d_debut.isoformat(), "fin": d_fin.isoformat(), "group_by": group_by},
        "kpi": {
            "nb_ventes": nb_ventes,
            "total_ventes": total_ventes,
            "total_benefice": total_benefice,
            "total_commissions": total_commissions,
        },
        "descriptives": {
            "ventes": descr_ventes,
            "benefices": descr_benefices,
            "commissions": descr_commissions,
        },
        "tendance": tendance_ventes,
        "histogramme": histogramme,
        "par_niveau": par_niveau,
        "evolution": evolution,
        "top_produits": top_produits,
        "top_parrains": top_parrains,
        
    }