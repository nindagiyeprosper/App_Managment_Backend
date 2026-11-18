from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Produit, Vente, LigneVente, Commission
from schemas import VenteIn, VenteOut
from auth import require_admin
from commissions import calculer_commissions

router = APIRouter(prefix="/api/ventes", tags=["ventes"])

STATUTS_VALIDES = ("en_attente", "payee", "remise", "annulee")


# ============================================================
# CRÉATION
# ============================================================

@router.post("", response_model=VenteOut)
def create_vente(
    payload: VenteIn,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    client = db.query(Client).get(payload.client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    if not payload.lignes:
        raise HTTPException(400, "Aucune ligne")

    statut_choisi = payload.statut if payload.statut in STATUTS_VALIDES else "en_attente"

    montant_total = 0.0
    benefice_total = 0.0
    lignes_data = []

    for l in payload.lignes:
        p = db.query(Produit).get(l.produit_id)
        if not p or not p.actif:
            raise HTTPException(404, f"Produit {l.produit_id} introuvable")
        if p.stock < l.quantite:
            raise HTTPException(400, f"Stock insuffisant pour {p.nom}")

        prix_u = float(p.prix_vente)
        cout_u = float(p.prix_achat)
        sous_total = prix_u * l.quantite
        benef = (prix_u - cout_u) * l.quantite

        montant_total += sous_total
        benefice_total += benef

        # Décrémenter le stock sauf si la vente est créée directement annulée
        if statut_choisi != "annulee":
            p.stock -= l.quantite

        lignes_data.append({
            "produit_id": p.id,
            "quantite": l.quantite,
            "prix_unitaire": prix_u,
            "sous_total": sous_total,
            "benefice_ligne": benef,
        })

    vente = Vente(
        client_id=client.id,
        montant_total=montant_total,
        benefice_total=benefice_total,
        statut=statut_choisi,
    )

    # Si traité immédiatement (payée, remise, annulée) → marquer date_traitement
    if statut_choisi != "en_attente":
        vente.date_traitement = datetime.utcnow()
        vente.delai_attente_minutes = 0

    db.add(vente)
    db.flush()

    for ld in lignes_data:
        db.add(LigneVente(vente_id=vente.id, **ld))

    # Calculer les commissions seulement si payée ou remise
    if statut_choisi in ("payee", "remise"):
        calculer_commissions(db, vente, client)

    db.commit()
    db.refresh(vente)
    return vente


# ============================================================
# LISTE
# ============================================================

@router.get("", response_model=None)
def list_ventes(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    rows = db.query(Vente).order_by(Vente.id.desc()).all()
    result = []
    for v in rows:
        client = db.query(Client).get(v.client_id)
        lignes = []
        for l in v.lignes:
            p = db.query(Produit).get(l.produit_id)
            lignes.append({
                "produit_id": l.produit_id,
                "produit_nom": p.nom if p else "?",
                "categorie": p.categorie if p else "",
                "quantite": l.quantite,
                "prix_unitaire": float(l.prix_unitaire),
                "sous_total": float(l.sous_total),
                "benefice_ligne": float(l.benefice_ligne),
            })

        commissions = db.query(Commission).filter(Commission.vente_id == v.id).all()
        comms = [
            {
                "id": c.id,
                "beneficiaire_id": c.beneficiaire_id,
                "niveau": c.niveau,
                "taux": float(c.taux),
                "montant": float(c.montant),
                "statut": c.statut,
            }
            for c in commissions
        ]

        result.append({
            "id": v.id,
            "client_id": v.client_id,
            "client_nom": client.nom if client else "?",
            "client_telephone": client.telephone if client else "?",
            "date": v.date,
            "date_traitement": v.date_traitement,
            "delai_attente_minutes": v.delai_attente_minutes,
            "montant_total": float(v.montant_total),
            "benefice_total": float(v.benefice_total),
            "statut": v.statut,
            "nb_articles": sum(l.quantite for l in v.lignes),
            "lignes": lignes,
            "commissions": comms,
        })
    return result


# ============================================================
# DÉTAIL
# ============================================================

@router.get("/{vid}", response_model=VenteOut)
def get_vente(vid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    v = db.query(Vente).get(vid)
    if not v:
        raise HTTPException(404, "Vente introuvable")
    return v


# ============================================================
# WORKFLOW : TRAITER UNE VENTE EN ATTENTE
# ============================================================

@router.put("/{vid}/marquer-payee")
def marquer_payee(vid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    v = db.query(Vente).get(vid)
    if not v:
        raise HTTPException(404, "Vente introuvable")
    if v.statut != "en_attente":
        raise HTTPException(400, "Seules les ventes en attente peuvent être payées")

    now = datetime.utcnow()
    v.statut = "payee"
    v.date_traitement = now
    v.delai_attente_minutes = int((now - v.date).total_seconds() / 60)

    client = db.query(Client).get(v.client_id)
    if client:
        calculer_commissions(db, v, client)

    db.commit()
    return {"ok": True, "delai_minutes": v.delai_attente_minutes}


@router.put("/{vid}/marquer-remise")
def marquer_remise(vid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    v = db.query(Vente).get(vid)
    if not v:
        raise HTTPException(404, "Vente introuvable")
    if v.statut != "en_attente":
        raise HTTPException(400, "Seules les ventes en attente peuvent être remises")

    now = datetime.utcnow()
    v.statut = "remise"
    v.date_traitement = now
    v.delai_attente_minutes = int((now - v.date).total_seconds() / 60)

    client = db.query(Client).get(v.client_id)
    if client:
        calculer_commissions(db, v, client)

    db.commit()
    return {"ok": True, "delai_minutes": v.delai_attente_minutes}


@router.put("/{vid}/annuler")
def annuler_vente(vid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    v = db.query(Vente).get(vid)
    if not v:
        raise HTTPException(404, "Vente introuvable")
    if v.statut in ("payee", "remise", "annulee"):
        raise HTTPException(400, "Impossible d'annuler une vente déjà traitée")

    comms = db.query(Commission).filter(Commission.vente_id == vid).all()
    if any(c.statut in ("validee", "payee") for c in comms):
        raise HTTPException(400, "Commissions déjà validées, annulation impossible")

    for c in comms:
        c.statut = "annulee"

    now = datetime.utcnow()
    v.statut = "annulee"
    v.date_traitement = now
    v.delai_attente_minutes = int((now - v.date).total_seconds() / 60)

    # Restituer le stock
    for ligne in v.lignes:
        p = db.query(Produit).get(ligne.produit_id)
        if p:
            p.stock += ligne.quantite

    db.commit()
    return {"ok": True, "delai_minutes": v.delai_attente_minutes}

# SUPPRESSION
# ===========================================================
@router.delete("/{vid}")
def supprimer_vente(vid: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    """Supprimer une vente (si commissions non validées/payées)."""
    v = db.query(Vente).get(vid)
    if not v:
        raise HTTPException(404, "Vente introuvable")

    comms = db.query(Commission).filter(Commission.vente_id == vid).all()
    if any(c.statut in ("validee", "payee") for c in comms):
        raise HTTPException(400, "Impossible : commissions déjà validées/payées")

    if v.statut != "annulee":
        for ligne in v.lignes:
            p = db.query(Produit).get(ligne.produit_id)
            if p:
                p.stock += ligne.quantite

    db.query(Commission).filter(Commission.vente_id == vid).delete()
    db.query(LigneVente).filter(LigneVente.vente_id == vid).delete()
    db.delete(v)
    db.commit()
    return {"ok": True}  
