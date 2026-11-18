from database import engine
from sqlalchemy import text

with engine.begin() as conn:
    print("Ajout de la colonne photo_url...")
    conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)"))
    print("OK - Colonne ajoutee")