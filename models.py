from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric,
    Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    telephone = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=True)
    adresse = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    code_parrainage = Column(String, unique=True, nullable=False)
    parrain_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    nb_descendants = Column(Integer, default=0)
    role = Column(String, default="client")
    date_inscription = Column(DateTime, default=datetime.utcnow)
    photo_url = Column(String, nullable=True)   # ← AJOUT


class Produit(Base):
    __tablename__ = "produits"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    categorie = Column(String, nullable=False)
    taille = Column(String, nullable=True)
    couleur = Column(String, nullable=True)
    prix_achat = Column(Numeric(12, 2), nullable=False)
    prix_vente = Column(Numeric(12, 2), nullable=False)
    stock = Column(Integer, default=0)
    seuil_alerte = Column(Integer, default=5)
    actif = Column(Boolean, default=True)


class MouvementStock(Base):
    __tablename__ = "mouvements_stock"
    id = Column(Integer, primary_key=True)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    type = Column(SAEnum("entree", "sortie", name="type_mouvement"), nullable=False)
    quantite = Column(Integer, nullable=False)
    motif = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    admin_id = Column(Integer, ForeignKey("clients.id"), nullable=True)


class Vente(Base):
    __tablename__ = "ventes"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    montant_total = Column(Numeric(12, 2), nullable=False)
    benefice_total = Column(Numeric(12, 2), nullable=False)
    statut = Column(
        SAEnum("en_attente", "payee", "remise", "annulee", name="statut_vente"),
        default="en_attente",
    )
    date_traitement = Column(DateTime, nullable=True)          # ← AJOUT
    delai_attente_minutes = Column(Integer, nullable=True)     # ← AJOUT
    lignes = relationship("LigneVente", back_populates="vente", cascade="all, delete-orphan")

class LigneVente(Base):
    __tablename__ = "lignes_vente"
    id = Column(Integer, primary_key=True)
    vente_id = Column(Integer, ForeignKey("ventes.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite = Column(Integer, nullable=False)
    prix_unitaire = Column(Numeric(12, 2), nullable=False)
    sous_total = Column(Numeric(12, 2), nullable=False)
    benefice_ligne = Column(Numeric(12, 2), nullable=False)
    vente = relationship("Vente", back_populates="lignes")


class Commission(Base):
    __tablename__ = "commissions"
    id = Column(Integer, primary_key=True)
    vente_id = Column(Integer, ForeignKey("ventes.id"), nullable=False)
    beneficiaire_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    niveau = Column(Integer, nullable=False)
    taux = Column(Numeric(5, 2), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
    statut = Column(SAEnum("calculee", "validee", "payee", "annulee", name="statut_commission"), default="calculee")
    date_calcul = Column(DateTime, default=datetime.utcnow)
    date_validation = Column(DateTime, nullable=True)
    date_paiement = Column(DateTime, nullable=True)


class Paiement(Base):
    __tablename__ = "paiements"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    reference = Column(String, nullable=False)
    admin_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    notes = Column(String, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    lu = Column(Boolean, default=False)
    date = Column(DateTime, default=datetime.utcnow)    

class Commande(Base):
    __tablename__ = "commandes"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date_commande = Column(DateTime, default=datetime.utcnow)
    statut = Column(SAEnum("en_attente", "validee", "refusee", name="statut_commande"), default="en_attente")
    montant_total = Column(Numeric(12, 2), nullable=False, default=0)
    notes = Column(String, nullable=True)
    admin_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    date_traitement = Column(DateTime, nullable=True)
    motif_refus = Column(String, nullable=True)
    lignes = relationship("LigneCommande", back_populates="commande", cascade="all, delete-orphan")


class LigneCommande(Base):
    __tablename__ = "lignes_commande"
    id = Column(Integer, primary_key=True)
    commande_id = Column(Integer, ForeignKey("commandes.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite = Column(Integer, nullable=False)
    prix_unitaire = Column(Numeric(12, 2), nullable=False)
    commande = relationship("Commande", back_populates="lignes")