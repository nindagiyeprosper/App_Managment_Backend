from database import engine
from sqlalchemy import text

with engine.begin() as conn:
    print("Ajout des colonnes...")
    conn.execute(text("ALTER TABLE ventes ADD COLUMN IF NOT EXISTS date_traitement TIMESTAMP"))
    conn.execute(text("ALTER TABLE ventes ADD COLUMN IF NOT EXISTS delai_attente_minutes INTEGER"))
    print("✓ Colonnes ajoutées")

    print("Extension de l'enum statut_vente...")
    try:
        conn.execute(text("ALTER TYPE statut_vente ADD VALUE IF NOT EXISTS 'en_attente'"))
        conn.execute(text("ALTER TYPE statut_vente ADD VALUE IF NOT EXISTS 'remise'"))
        print("✓ Enum étendu")
    except Exception as e:
        print(f"⚠ Enum déjà étendu ou erreur : {e}")

    print("Migration terminée avec succès !")