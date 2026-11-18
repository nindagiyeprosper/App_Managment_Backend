from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np
from scipy import stats as scipy_stats
import statsmodels.api as sm

from database import get_db
from models import Client, Vente, LigneVente, Commission
from auth import require_admin

router = APIRouter(prefix="/api/stats-advanced", tags=["stats-advanced"])


def _bornes(debut, fin):
    now = datetime.utcnow()
    if not debut:
        debut = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not fin:
        fin = now.isoformat()
    return datetime.fromisoformat(debut), datetime.fromisoformat(fin)


def _get_montants(db, d_debut, d_fin):
    rows = db.query(Vente).filter(
        Vente.date.between(d_debut, d_fin), Vente.statut == "payee"
    ).all()
    return np.array([float(v.montant_total) for v in rows])


# ============================================================
# NIVEAU 2
# ============================================================

@router.get("/boxplot")
def boxplot(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    """Boxplot complet : min, Q1, médiane, Q3, max, moustaches, outliers."""
    d_debut, d_fin = _bornes(debut, fin)
    arr = _get_montants(db, d_debut, d_fin)
    if len(arr) == 0:
        return {"vide": True, "n": 0}

    q1, med, q3 = np.percentile(arr, [25, 50, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = arr[(arr < lower) | (arr > upper)]

    return {
        "vide": False,
        "n": int(len(arr)),
        "min": float(np.min(arr)),
        "q1": float(q1),
        "mediane": float(med),
        "q3": float(q3),
        "max": float(np.max(arr)),
        "iqr": float(iqr),
        "moustache_basse": float(max(np.min(arr), lower)),
        "moustache_haute": float(min(np.max(arr), upper)),
        "outliers": sorted([float(o) for o in outliers]),
        "nb_outliers": int(len(outliers)),
    }


@router.get("/qqplot")
def qqplot(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    arr = _get_montants(db, d_debut, d_fin)
    if len(arr) < 3:
        return {"n": len(arr), "points": []}

    z = (arr - np.mean(arr)) / np.std(arr, ddof=1)
    z_sorted = np.sort(z)
    n = len(z_sorted)
    probs = (np.arange(1, n + 1) - 0.5) / n
    theoretical = scipy_stats.norm.ppf(probs)

    points = [
        {"theorique": round(float(t), 4), "empirique": round(float(e), 4)}
        for t, e in zip(theoretical, z_sorted)
    ]
    tmin, tmax = float(theoretical.min()), float(theoretical.max())

    return {
        "n": n,
        "points": points,
        "ligne_ref": [
            {"theorique": tmin, "empirique": tmin},
            {"theorique": tmax, "empirique": tmax},
        ],
    }


@router.get("/normalite")
def test_normalite(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    arr = _get_montants(db, d_debut, d_fin)
    n = len(arr)
    if n < 3:
        return {"n": n, "message": "Pas assez de données (n < 3)"}

    tests = []

    if n <= 5000:
        stat, p = scipy_stats.shapiro(arr)
        tests.append({"test": "Shapiro-Wilk", "statistique": round(float(stat), 4), "p_value": round(float(p), 6), "normal": p > 0.05})

    stat, p = scipy_stats.kstest(arr, "norm", args=(np.mean(arr), np.std(arr, ddof=1)))
    tests.append({"test": "Kolmogorov-Smirnov", "statistique": round(float(stat), 4), "p_value": round(float(p), 6), "normal": p > 0.05})

    stat, p = scipy_stats.jarque_bera(arr)
    tests.append({"test": "Jarque-Bera", "statistique": round(float(stat), 4), "p_value": round(float(p), 6), "normal": p > 0.05})

    return {"n": n, "tests": tests}


@router.get("/intervalle-confiance")
def intervalle_confiance(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    niveau: float = Query(0.95, ge=0.5, le=0.999),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    arr = _get_montants(db, d_debut, d_fin)
    n = len(arr)
    if n < 2:
        return {"n": n, "message": "Pas assez de données (n < 2)"}

    moy = float(np.mean(arr))
    ecart = float(np.std(arr, ddof=1))
    sem = ecart / np.sqrt(n)
    alpha = 1 - niveau

    if n < 30:
        t = scipy_stats.t.ppf(1 - alpha / 2, df=n - 1)
        methode = f"t de Student (ddl={n-1})"
    else:
        t = scipy_stats.norm.ppf(1 - alpha / 2)
        methode = "Normale (Z)"

    marge = t * sem

    return {
        "n": n, "niveau": niveau,
        "moyenne": round(moy, 2), "ecart_type": round(ecart, 2),
        "erreur_standard": round(float(sem), 2),
        "marge_erreur": round(float(marge), 2),
        "ic_bas": round(moy - marge, 2), "ic_haut": round(moy + marge, 2),
        "methode": methode,
    }


@router.get("/test-t")
def test_t(
    debut1: str = Query(...),
    fin1: str = Query(...),
    debut2: str = Query(...),
    fin2: str = Query(...),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d1a, d1b = _bornes(debut1, fin1)
    d2a, d2b = _bornes(debut2, fin2)

    a = _get_montants(db, d1a, d1b)
    b = _get_montants(db, d2a, d2b)

    if len(a) < 2 or len(b) < 2:
        raise HTTPException(400, "Chaque période doit avoir au moins 2 ventes")

    stat, p = scipy_stats.ttest_ind(a, b, equal_var=False)

    return {
        "periode1": {"n": len(a), "moyenne": round(float(np.mean(a)), 2), "ecart_type": round(float(np.std(a, ddof=1)), 2)},
        "periode2": {"n": len(b), "moyenne": round(float(np.mean(b)), 2), "ecart_type": round(float(np.std(b, ddof=1)), 2)},
        "statistique_t": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "significatif": p < 0.05,
        "interpretation": "Différence significative (p < 0.05)" if p < 0.05 else "Pas de différence significative (p ≥ 0.05)",
    }


# ============================================================
# NIVEAU 3
# ============================================================

@router.get("/regression-multiple")
def regression_multiple(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    ventes = db.query(Vente).filter(
        Vente.date.between(d_debut, d_fin), Vente.statut == "payee"
    ).all()

    if len(ventes) < 5:
        return {"message": "Pas assez de données (n < 5)"}

    lignes = []
    for v in ventes:
        nb_lignes = db.query(func.count(LigneVente.id)).filter(LigneVente.vente_id == v.id).scalar()
        nb_comm = db.query(func.count(Commission.id)).filter(Commission.vente_id == v.id).scalar()
        lignes.append({"montant": float(v.montant_total), "nb_lignes": int(nb_lignes), "nb_commissions": int(nb_comm), "benefice": float(v.benefice_total)})

    y = np.array([l["benefice"] for l in lignes])
    X = np.array([[l["montant"], l["nb_lignes"], l["nb_commissions"]] for l in lignes])
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()

    return {
        "n": len(lignes),
        "r2": round(float(model.rsquared), 4),
        "r2_ajuste": round(float(model.rsquared_adj), 4),
        "f_stat": round(float(model.fvalue), 4),
        "p_value_f": round(float(model.f_pvalue), 6),
        "coefficients": [
            {"nom": "constante", "valeur": round(float(model.params[0]), 4), "p_value": round(float(model.pvalues[0]), 6)},
            {"nom": "montant", "valeur": round(float(model.params[1]), 4), "p_value": round(float(model.pvalues[1]), 6)},
            {"nom": "nb_lignes", "valeur": round(float(model.params[2]), 4), "p_value": round(float(model.pvalues[2]), 6)},
            {"nom": "nb_commissions", "valeur": round(float(model.params[3]), 4), "p_value": round(float(model.pvalues[3]), 6)},
        ],
        "equation": f"Bénéfice = {model.params[0]:.2f} + {model.params[1]:.2f}·Montant + {model.params[2]:.2f}·NbLignes + {model.params[3]:.2f}·NbCommissions",
    }


@router.get("/arima")
def arima_forecast(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    periods: int = Query(7, ge=1, le=60),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    rows = db.query(
        func.to_char(Vente.date, "YYYY-MM-DD").label("jour"),
        func.coalesce(func.sum(Vente.montant_total), 0).label("ventes"),
    ).filter(
        Vente.date.between(d_debut, d_fin), Vente.statut == "payee"
    ).group_by("jour").order_by("jour").all()

    if len(rows) < 15:
        return {"message": "Pas assez de jours (n < 15)"}

    y = np.array([float(r.ventes) for r in rows])
    try:
        from statsmodels.tsa.arima.model import ARIMA
        model = ARIMA(y, order=(1, 1, 1)).fit()
        forecast = model.forecast(steps=periods)
    except Exception as e:
        return {"message": f"Erreur ARIMA : {e}"}

    historique = [{"jour": r.jour, "ventes": float(r.ventes)} for r in rows]
    last_date = datetime.fromisoformat(rows[-1].jour)
    previsions = []
    for i, val in enumerate(forecast, 1):
        previsions.append({"jour": (last_date + timedelta(days=i)).strftime("%Y-%m-%d"), "ventes": round(float(val), 2)})

    return {"historique": historique, "previsions": previsions, "avertissement": "ARIMA(1,1,1) sur peu de points → prudence."}


@router.get("/khi2")
def test_khi2(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    counts = []
    for niv in (1, 2, 3):
        c = db.query(func.count(Commission.id)).filter(
            Commission.date_calcul.between(d_debut, d_fin),
            Commission.statut.in_(["validee", "payee"]),
            Commission.niveau == niv,
        ).scalar()
        counts.append(int(c))

    total = sum(counts)
    if total == 0:
        return {"message": "Aucune commission sur la période"}

    stat, p = scipy_stats.chisquare(counts)
    return {
        "observes": {"N1": counts[0], "N2": counts[1], "N3": counts[2]},
        "attendus": {"N1": total / 3, "N2": total / 3, "N3": total / 3},
        "statistique_khi2": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "uniforme": p > 0.05,
        "interpretation": "Répartition uniforme (p > 0.05)" if p > 0.05 else "Répartition NON uniforme (p ≤ 0.05)",
    }


@router.get("/heatmap-semaine")
def heatmap_semaine(
    debut: str | None = Query(None),
    fin: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    d_debut, d_fin = _bornes(debut, fin)
    rows = db.query(
        func.extract("isodow", Vente.date).label("jour_semaine"),
        func.coalesce(func.sum(Vente.montant_total), 0).label("total"),
        func.count(Vente.id).label("nb"),
    ).filter(
        Vente.date.between(d_debut, d_fin), Vente.statut == "payee"
    ).group_by("jour_semaine").order_by("jour_semaine").all()

    jours_fr = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"}
    return [{"jour": jours_fr.get(int(r.jour_semaine), str(r.jour_semaine)), "total": float(r.total), "nb": r.nb} for r in rows]