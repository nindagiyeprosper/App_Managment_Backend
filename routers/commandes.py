from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import (
    Client, Produit, Commande, LigneCommande,
    Vente, LigneVente, Commission,
)
from schemas import PurgerCommandesIn
from auth import get_current_user, require_admin
from commissions import calculer_commissions, notifier

router = APIRouter(prefix="/api/commandes", tags=["commandes"])


# ============================================================
# CÔTÉ CLIENT
# ============================================================

@router.post("")
def creer_commande(
    payload: dict,
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    lignes = payload.get("lignes", [])
    if not lignes:
        raise HTTPException(400, "Aucune ligne dans la commande")

    montant_total = 0.0
    lignes_data = []

    for l in lignes:
        p = db.query(Produit).get(l["produit_id"])
        if not p or not p.actif:
            raise HTTPException(404, f"Produit {l['produit_id']} introuvable")
        if p.stock < l["quantite"]:
            raise HTTPException(400, f"Stock insuffisant pour {p.nom}")

        prix_u = float(p.prix_vente)
        sous_total = prix_u * l["quantite"]
        montant_total += sous_total

        lignes_data.append({
            "produit_id": p.id,
            "quantite": l["quantite"],
            "prix_unitaire": prix_u,
        })

    commande = Commande(
        client_id=user.id,
        montant_total=montant_total,
        statut="en_attente",
        notes=payload.get("notes"),
    )
    db.add(commande)
    db.flush()

    for ld in lignes_data:
        db.add(LigneCommande(commande_id=commande.id, **ld))

    db.commit()
    db.refresh(commande)
    return {"ok": True, "commande_id": commande.id, "montant_total": montant_total}


@router.get("/mes-commandes")
def mes_commandes(
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    rows = db.query(Commande).filter(
        Commande.client_id == user.id
    ).order_by(Commande.id.desc()).all()

    return [
        {
            "id": c.id,
            "date_commande": c.date_commande,
            "statut": c.statut,
            "montant_total": float(c.montant_total),
            "notes": c.notes,
            "motif_refus": c.motif_refus,
            "nb_articles": len(c.lignes),
        }
        for c in rows
    ]


# ============================================================
# CÔTÉ ADMIN
# ============================================================

@router.get("")
def list_commandes(
    statut: str | None = None,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    q = db.query(Commande)
    if statut:
        q = q.filter(Commande.statut == statut)
    rows = q.order_by(Commande.id.desc()).all()

    return [
        {
            "id": c.id,
            "client_id": c.client_id,
            "date_commande": c.date_commande,
            "statut": c.statut,
            "montant_total": float(c.montant_total),
            "notes": c.notes,
            "nb_articles": len(c.lignes),
        }
        for c in rows
    ]


@router.get("/{commande_id}")
def get_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    c = db.query(Commande).get(commande_id)
    if not c:
        raise HTTPException(404, "Commande introuvable")

    client = db.query(Client).get(c.client_id)

    return {
        "id": c.id,
        "client_id": c.client_id,
        "client_nom": client.nom if client else "?",
        "client_telephone": client.telephone if client else "?",
        "date_commande": c.date_commande,
        "statut": c.statut,
        "montant_total": float(c.montant_total),
        "notes": c.notes,
        "motif_refus": c.motif_refus,
        "lignes": [
            {
                "produit_id": l.produit_id,
                "produit_nom": db.query(Produit).get(l.produit_id).nom,
                "quantite": l.quantite,
                "prix_unitaire": float(l.prix_unitaire),
                "sous_total": float(l.prix_unitaire) * l.quantite,
            }
            for l in c.lignes
        ],
    }


@router.put("/{commande_id}/valider")
def valider_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    c = db.query(Commande).get(commande_id)
    if not c:
        raise HTTPException(404, "Commande introuvable")
    if c.statut != "en_attente":
        raise HTTPException(400, "Commande déjà traitée")

    client = db.query(Client).get(c.client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")

    montant_total = 0.0
    benefice_total = 0.0
    lignes_vente = []

    for lc in c.lignes:
        p = db.query(Produit).get(lc.produit_id)
        if not p or not p.actif:
            raise HTTPException(404, f"Produit {lc.produit_id} introuvable")
        if p.stock < lc.quantite:
            raise HTTPException(400, f"Stock insuffisant pour {p.nom}")

        prix_u = float(p.prix_vente)
        cout_u = float(p.prix_achat)
        sous_total = prix_u * lc.quantite
        benef = (prix_u - cout_u) * lc.quantite

        montant_total += sous_total
        benefice_total += benef
        p.stock -= lc.quantite

        lignes_vente.append({
            "produit_id": p.id,
            "quantite": lc.quantite,
            "prix_unitaire": prix_u,
            "sous_total": sous_total,
            "benefice_ligne": benef,
        })

    vente = Vente(
        client_id=client.id,
        montant_total=montant_total,
        benefice_total=benefice_total,
        statut="payee",
    )
    db.add(vente)
    db.flush()

    for lv in lignes_vente:
        db.add(LigneVente(vente_id=vente.id, **lv))

    calculer_commissions(db, vente, client)

    c.statut = "validee"
    c.admin_id = admin.id
    c.date_traitement = datetime.utcnow()

    notifier(db, client.id, "commande", f"Votre commande #{c.id} a été validée")

    db.commit()
    db.refresh(vente)
    return {"ok": True, "vente_id": vente.id, "montant_total": montant_total}


@router.put("/{commande_id}/refuser")
def refuser_commande(
    commande_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    c = db.query(Commande).get(commande_id)
    if not c:
        raise HTTPException(404, "Commande introuvable")
    if c.statut != "en_attente":
        raise HTTPException(400, "Commande déjà traitée")

    c.statut = "refusee"
    c.admin_id = admin.id
    c.date_traitement = datetime.utcnow()
    c.motif_refus = payload.get("motif", "Refusée par l'administrateur")

    notifier(db, c.client_id, "commande", f"Votre commande #{c.id} a été refusée : {c.motif_refus}")

    db.commit()
    return {"ok": True}


# ============================================================
# SUPPRESSION UNITAIRE
# ============================================================

@router.delete("/{commande_id}")
def supprimer_commande(
    commande_id: int,
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    """Supprimer une commande.

    - Client : uniquement ses commandes en attente ou refusées
    - Admin : toutes les commandes (avec suppression de la vente associée si validée)
    """
    c = db.query(Commande).get(commande_id)
    if not c:
        raise HTTPException(404, "Commande introuvable")

    # Autorisation
    if user.role != "admin" and c.client_id != user.id:
        raise HTTPException(403, "Accès refusé")

    # Client : seulement si en attente ou refusée
    if user.role != "admin" and c.statut not in ("en_attente", "refusee"):
        raise HTTPException(400, "Impossible : commande validée (contactez l'admin)")

    # Si validée → supprimer aussi la vente liée
    if c.statut == "validee":
        vente_liee = None
        if c.date_traitement:
            vente_liee = db.query(Vente).filter(
                Vente.client_id == c.client_id,
                Vente.date >= c.date_traitement,
            ).order_by(Vente.date.asc()).first()

        if vente_liee:
            comms = db.query(Commission).filter(Commission.vente_id == vente_liee.id).all()
            if any(comm.statut in ("validee", "payee") for comm in comms):
                raise HTTPException(
                    400,
                    "Impossible : des commissions liées sont validées/payées. "
                    "Annulez-les d'abord dans /admin/commissions."
                )

            for ligne in vente_liee.lignes:
                p = db.query(Produit).get(ligne.produit_id)
                if p:
                    p.stock += ligne.quantite

            db.query(Commission).filter(Commission.vente_id == vente_liee.id).delete()
            db.query(LigneVente).filter(LigneVente.vente_id == vente_liee.id).delete()
            db.delete(vente_liee)

    # Supprimer lignes commande + commande
    db.query(LigneCommande).filter(LigneCommande.commande_id == commande_id).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}


# ============================================================
# PURGE EN MASSE (admin)
# ============================================================

@router.post("/purger")
def purger_commandes(
    payload: PurgerCommandesIn,
    db: Session = Depends(get_db),
    admin: Client = Depends(require_admin),
):
    """Purger les commandes d'un statut donné antérieures à une date."""
    try:
        date_limite = datetime.fromisoformat(payload.avant.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(400, "Format de date invalide (ISO 8601 attendu)")

    statuts = payload.statuts or ["validee", "refusee"]
    if not all(s in ("validee", "refusee") for s in statuts):
        raise HTTPException(400, "Statuts autorisés : 'validee' et/ou 'refusee'")

    commandes = db.query(Commande).filter(
        Commande.statut.in_(statuts),
        Commande.date_commande < date_limite,
    ).all()

    nb_commandes = 0
    nb_ventes = 0
    nb_commissions = 0
    bloquees = []

    for c in commandes:
        if c.statut == "validee" and payload.supprimer_ventes:
            vente_liee = None
            if c.date_traitement:
                vente_liee = db.query(Vente).filter(
                    Vente.client_id == c.client_id,
                    Vente.date >= c.date_traitement,
                ).order_by(Vente.date.asc()).first()

            if vente_liee:
                comms = db.query(Commission).filter(Commission.vente_id == vente_liee.id).all()
                if any(comm.statut in ("validee", "payee") for comm in comms):
                    bloquees.append({"id": c.id, "raison": "commissions validées/payées"})
                    continue

                for ligne in vente_liee.lignes:
                    p = db.query(Produit).get(ligne.produit_id)
                    if p:
                        p.stock += ligne.quantite

                nb_commissions += len(comms)
                db.query(Commission).filter(Commission.vente_id == vente_liee.id).delete()
                db.query(LigneVente).filter(LigneVente.vente_id == vente_liee.id).delete()
                db.delete(vente_liee)
                nb_ventes += 1

        db.query(LigneCommande).filter(LigneCommande.commande_id == c.id).delete()
        db.delete(c)
        nb_commandes += 1

    db.commit()

    return {
        "ok": True,
        "commandes_supprimees": nb_commandes,
        "ventes_supprimees": nb_ventes,
        "commissions_supprimees": nb_commissions,
        "bloquees": bloquees,
        "message": (
            f"{nb_commandes} commande(s) supprimée(s), "
            f"{nb_ventes} vente(s), {nb_commissions} commission(s)."
            + (f" {len(bloquees)} bloquée(s) (commissions validées)." if bloquees else "")
        ),
    }
@router.post("/purger-mes")
def purger_mes_commandes(
    payload: PurgerCommandesIn,
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    """Purger les propres commandes du client connecté.

    - Commandes en attente / refusées : supprimées librement
    - Commandes validées : supprimées UNIQUEMENT si toutes les commissions
      sont payées ou annulées (pour ne pas priver les parrains).
    """
    try:
        date_limite = datetime.fromisoformat(payload.avant.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(400, "Format de date invalide (ISO 8601 attendu)")

    statuts = payload.statuts or ["validee", "refusee"]
    if not all(s in ("en_attente", "validee", "refusee") for s in statuts):
        raise HTTPException(400, "Statuts autorisés : 'en_attente', 'validee' et/ou 'refusee'")

    commandes = db.query(Commande).filter(
        Commande.client_id == user.id,
        Commande.statut.in_(statuts),
        Commande.date_commande < date_limite,
    ).all()

    nb_commandes = 0
    nb_ventes = 0
    nb_commissions = 0
    bloquees = []

    for c in commandes:
        if c.statut == "validee":
            vente_liee = None
            if c.date_traitement:
                vente_liee = db.query(Vente).filter(
                    Vente.client_id == c.client_id,
                    Vente.date >= c.date_traitement,
                ).order_by(Vente.date.asc()).first()

            if vente_liee:
                comms = db.query(Commission).filter(Commission.vente_id == vente_liee.id).all()
                # Bloquer si une commission n'est PAS encore payée/annulée
                if any(comm.statut not in ("payee", "annulee") for comm in comms):
                    bloquees.append({
                        "id": c.id,
                        "raison": "commissions en attente de paiement",
                    })
                    continue

                nb_commissions += len(comms)
                db.query(Commission).filter(Commission.vente_id == vente_liee.id).delete()
                db.query(LigneVente).filter(LigneVente.vente_id == vente_liee.id).delete()
                db.delete(vente_liee)
                nb_ventes += 1

        db.query(LigneCommande).filter(LigneCommande.commande_id == c.id).delete()
        db.delete(c)
        nb_commandes += 1

    db.commit()

    return {
        "ok": True,
        "commandes_supprimees": nb_commandes,
        "ventes_supprimees": nb_ventes,
        "commissions_supprimees": nb_commissions,
        "bloquees": bloquees,
        "message": (
            f"{nb_commandes} commande(s) supprimée(s), "
            f"{nb_ventes} vente(s), {nb_commissions} commission(s)."
            + (f" {len(bloquees)} bloquée(s) : commissions non payées." if bloquees else "")
        ),
    }   