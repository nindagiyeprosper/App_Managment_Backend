import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from database import Base
import models  # noqa: F401

load_dotenv()

# Source : SQLite (ancien fichier)
SQLITE_URL = "sqlite:///./app.db"
sqlite_engine = create_engine(SQLITE_URL)
SqliteSession = sessionmaker(bind=sqlite_engine)

# Destination : PostgreSQL
PG_URL = os.getenv("DATABASE_URL")
pg_engine = create_engine(PG_URL)


def migrate():
    print("Début de la migration...")
    sqlite_db = SqliteSession()

    tables_in_order = [
        models.Client,
        models.Produit,
        models.MouvementStock,
        models.Vente,
        models.LigneVente,
        models.Commission,
        models.Paiement,
        models.Notification,
    ]

    for model in tables_in_order:
        table_name = model.__tablename__
        print(f"Migration de la table: {table_name}")

        rows = sqlite_db.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
        if not rows:
            print(f"  -> 0 ligne(s) à migrer.")
            continue

        with pg_engine.begin() as pg_conn:
            pg_conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
            pg_conn.execute(model.__table__.insert(), list(rows))

        print(f"  -> {len(rows)} ligne(s) migrée(s).")

    sqlite_db.close()
    print("Migration terminée avec succès !")


if __name__ == "__main__":
    migrate()