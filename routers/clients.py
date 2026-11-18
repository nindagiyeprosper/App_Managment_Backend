from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Client, Commission, Vente
from schemas import UserOut, CommissionOut
from auth import get_current_user, require_admin, hash_password, verify_password
from models import Client, Commission, Vente, Produit

import os
import uuid
from fastapi import UploadFile, File
from PIL import Image
import io


router = APIRouter(prefix="/api/clients", tags=["clients"])


# ---------- LISTE ----------
@router.get("", response_model=list[UserOut])
def list_clients(db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    return db.query(Client).order_by(Client.id.desc()).all()


# ---------- MES DONNÉES ----------
@router.get("/me/commissions", response_model=list[CommissionOut])
def mes_commissions(db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    return db.query(Commission).filter(Commission.beneficiaire_id == user.id).order_by(Commission.id.desc()).all()


@router.get("/me/achats")
def mes_achats(db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    rows = db.query(Vente).filter(
        Vente.client_id == user.id
    ).order_by(Vente.id.desc()).all()

    result = []
    for v in rows:
        lignes = []
        for l in v.lignes:
            produit = db.query(Produit).get(l.produit_id)
            lignes.append({
                "produit_id": l.produit_id,
                "produit_nom": produit.nom if produit else "?",
                "categorie": produit.categorie if produit else "?",
                "taille": produit.taille if produit else "",
                "couleur": produit.couleur if produit else "",
                "quantite": l.quantite,
                "prix_unitaire": float(l.prix_unitaire),
                "sous_total": float(l.sous_total),
            })
        result.append({
            "id": v.id,
            "date": v.date,
            "montant_total": float(v.montant_total),
            "benefice_total": float(v.benefice_total),
            "statut": v.statut,
            "lignes": lignes,
        })
    return result

# ---------- DÉTAIL ----------
@router.get("/{client_id}", response_model=UserOut)
def get_client(client_id: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")
    c = db.query(Client).get(client_id)
    if not c:
        raise HTTPException(404, "Client introuvable")
    return c


# ---------- MODIFICATION PROFIL ----------
@router.put("/{client_id}", response_model=UserOut)
def update_client(client_id: int, payload: dict, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")
    c = db.query(Client).get(client_id)
    if not c:
        raise HTTPException(404, "Client introuvable")
    for field in ("nom", "email", "adresse"):
        if field in payload:
            setattr(c, field, payload[field])
    db.commit()
    db.refresh(c)
    return c


# ---------- CHANGEMENT DE MOT DE PASSE ----------
@router.put("/{client_id}/password")
def change_password(
    client_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    if user.id != client_id and user.role != "admin":
        raise HTTPException(403, "Accès refusé")
    c = db.query(Client).get(client_id)
    if not c:
        raise HTTPException(404, "Client introuvable")
    if not verify_password(payload.get("old_password", ""), c.password_hash):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    c.password_hash = hash_password(payload.get("new_password", ""))
    db.commit()
    return {"ok": True}


# ---------- RÉSEAU ----------
@router.get("/{client_id}/reseau")
def get_reseau(client_id: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")

    def node(c: Client, depth: int = 0):
        filleuls = db.query(Client).filter(Client.parrain_id == c.id).all()
        return {
            "id": c.id, "nom": c.nom, "telephone": c.telephone,
            "code_parrainage": c.code_parrainage,
            "nb_descendants": c.nb_descendants,
            "filleuls": [node(f, depth + 1) for f in filleuls] if depth < 2 else [],
        }

    c = db.query(Client).get(client_id)
    if not c:
        raise HTTPException(404, "Client introuvable")
    return node(c)


# ---------- COMMISSIONS D'UN CLIENT ----------
@router.get("/{client_id}/commissions", response_model=list[CommissionOut])
def commissions_client(client_id: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")
    return db.query(Commission).filter(Commission.beneficiaire_id == client_id).order_by(Commission.id.desc()).all()


# ---------- ACHATS D'UN CLIENT ----------
@router.get("/{client_id}/achats")
def achats_client(client_id: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")
    return db.query(Vente).filter(Vente.client_id == client_id).order_by(Vente.id.desc()).all()


# ---------- CODE DE PARRAINAGE ----------
@router.get("/{client_id}/code-parrainage")
def code_parrainage(client_id: int, db: Session = Depends(get_db), user: Client = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Accès refusé")
    c = db.query(Client).get(client_id)
    return {"code_parrainage": c.code_parrainage} 

@router.delete("/{client_id}")
def supprimer_client(client_id: int, db: Session = Depends(get_db), admin: Client = Depends(require_admin)):
    """Supprimer un client (si aucune vente, commission ni filleul)."""
    c = db.query(Client).get(client_id)
    if not c:
        raise HTTPException(404, "Client introuvable")

    if db.query(Vente).filter(Vente.client_id == client_id).first():
        raise HTTPException(400, "Impossible : ce client a des ventes enregistrées")
    if db.query(Commission).filter(Commission.beneficiaire_id == client_id).first():
        raise HTTPException(400, "Impossible : ce client a reçu des commissions")
    if db.query(Client).filter(Client.parrain_id == client_id).first():
        raise HTTPException(400, "Impossible : ce client a des filleuls")

    db.delete(c)
    db.commit()
    return {"ok": True} 
## Le loadage d'une photo

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 2 * 1024 * 1024  # 2 MB


@router.post("/me/photo")
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    """Uploader la photo de profil du client connecté."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Format accepté : JPG, PNG ou WEBP uniquement")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "Image trop lourde (max 2 Mo)")

    try:
        img = Image.open(io.BytesIO(contents))
        img = img.convert("RGB")
        img.thumbnail((400, 400))
    except Exception:
        raise HTTPException(400, "Image invalide")

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    img.save(filepath, "JPEG", quality=85)

    # Supprimer l'ancienne photo si elle existe
    if user.photo_url:
        old_filename = user.photo_url.split("/")[-1]
        old_path = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    user.photo_url = f"/uploads/photos/{filename}"
    db.commit()
    db.refresh(user)
    return {"ok": True, "photo_url": user.photo_url}


@router.delete("/me/photo")
def delete_photo(
    db: Session = Depends(get_db),
    user: Client = Depends(get_current_user),
):
    """Supprimer la photo de profil."""
    if user.photo_url:
        old_filename = user.photo_url.split("/")[-1]
        old_path = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        user.photo_url = None
        db.commit()
    return {"ok": True}
