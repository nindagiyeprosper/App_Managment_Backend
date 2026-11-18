from database import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)

def add_column_if_missing(table, column, col_type):
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
    except Exception as e:
        print(f"⚠ Table {table} introuvable : {e}")
        return
    if column not in cols:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        print(f"✓ {table}.{column} ajoutée")
    else:
        print(f"  {table}.{column} existe déjà")

# Colonnes manquantes à ajouter
add_column_if_missing('clients', 'photo_url', 'VARCHAR(500)')
add_column_if_missing('ventes', 'date_traitement', 'TIMESTAMP')
add_column_if_missing('ventes', 'delai_attente_minutes', 'INTEGER')

print("\nMigration SQLite terminée.")