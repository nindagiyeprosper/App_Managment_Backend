from sqlalchemy.orm import Session
from models import Client, Vente, Commission, Notification


def notifier(db: Session, client_id: int, type_: str, message: str):
    db.add(Notification(client_id=client_id, type=type_, message=message))


def calculer_commissions(db: Session, vente: Vente, client: Client):
    """Applique les règles du cahier des charges §3."""
    chaine = []
    current = client
    for _ in range(3):
        if not current.parrain_id:
            break
        current = db.query(Client).get(current.parrain_id)
        if not current:
            break
        chaine.append(current)

    def add_commission(benef: Client, niveau: int, taux: float):
        if benef.nb_descendants >= 3:
            return
        montant = round(float(vente.benefice_total) * taux / 100, 2)
        if montant <= 0:
            return
        c = Commission(
            vente_id=vente.id, beneficiaire_id=benef.id,
            niveau=niveau, taux=taux, montant=montant, statut="calculee",
        )
        db.add(c)
        notifier(db, benef.id, "commission",
                 f"Nouvelle commission de {montant} FBu (N{niveau}) sur vente #{vente.id}")

    if len(chaine) >= 1:
        add_commission(chaine[0], 1, 7)
    if len(chaine) >= 2:
        add_commission(chaine[1], 2, 5)
        add_commission(chaine[0], 2, 2)
    if len(chaine) >= 3:
        add_commission(chaine[2], 3, 4)
        add_commission(chaine[0], 3, 1.5)
        add_commission(chaine[1], 3, 1.5)

    db.flush()