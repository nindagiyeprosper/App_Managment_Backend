from datetime import datetime
from pydantic import BaseModel, EmailStr


# AUTH
class RegisterIn(BaseModel):
    nom: str
    telephone: str
    email: EmailStr | None = None
    adresse: str | None = None
    password: str
    code_parrainage: str | None = None


class LoginIn(BaseModel):
    telephone: str
    password: str


class UserOut(BaseModel):
    id: int
    nom: str
    telephone: str
    email: str | None = None
    adresse: str | None = None
    code_parrainage: str
    parrain_id: int | None = None
    nb_descendants: int
    role: str
    photo_url: str | None = None   # ← AJOUT
    class Config: from_attributes = True


class AuthOut(BaseModel):
    token: str
    user: UserOut


# PRODUITS
class ProduitIn(BaseModel):
    nom: str
    categorie: str
    taille: str | None = None
    couleur: str | None = None
    prix_achat: float
    prix_vente: float
    stock: int = 0
    seuil_alerte: int = 5


class ProduitOut(BaseModel):
    id: int
    nom: str
    categorie: str
    taille: str | None = None
    couleur: str | None = None
    prix_achat: float
    prix_vente: float
    benefice_unitaire: float
    stock: int
    seuil_alerte: int
    actif: bool


# VENTES
class LigneIn(BaseModel):
    produit_id: int
    quantite: int


class VenteIn(BaseModel):
    client_id: int
    lignes: list[LigneIn]
    statut: str = "en_attente"   # en_attente | payee | remise | annulee

class VenteOut(BaseModel):
    id: int
    client_id: int
    date: datetime
    montant_total: float
    benefice_total: float
    statut: str
    class Config: from_attributes = True


# COMMISSIONS
class CommissionOut(BaseModel):
    id: int
    vente_id: int
    beneficiaire_id: int
    niveau: int
    taux: float
    montant: float
    statut: str
    date_calcul: datetime
    class Config: from_attributes = True


class PayerIn(BaseModel):
    reference: str
    notes: str | None = None


# STOCK
class MouvementIn(BaseModel):
    produit_id: int
    type: str  # "entree" | "sortie"
    quantite: int
    motif: str | None = None

class PurgerCommandesIn(BaseModel):
    avant: str
    statuts: list[str] = ["validee", "refusee"]
    supprimer_ventes: bool = True
    
