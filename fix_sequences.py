from sqlalchemy import text
from database import engine

TABLES = [
    "clients", "produits", "mouvements_stock", "ventes",
    "lignes_vente", "commissions", "paiements", "notifications",
]

with engine.begin() as conn:
    for t in TABLES:
        sql = f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), coalesce(max(id),0) + 1, false) FROM {t}"
        conn.execute(text(sql))
        print(f"Séquence réalignée pour {t}")

print("Terminé.")