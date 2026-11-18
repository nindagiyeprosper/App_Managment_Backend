import os
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from auth import require_admin
from models import Client

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Chemin complet vers pg_dump (Windows)
PG_DUMP = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"


@router.get("/backup")
def backup_db(admin: Client = Depends(require_admin)):
    """Télécharge une sauvegarde SQL de la base PostgreSQL."""
    path = os.path.join(os.getcwd(), "habit_app_backup.sql")

    if not os.path.exists(PG_DUMP):
        raise HTTPException(
            500,
            f"pg_dump introuvable à : {PG_DUMP}. Vérifiez que PostgreSQL 18 est installé."
        )

    try:
        subprocess.run(
            [
                PG_DUMP,
                "-U", "postgres",
                "-d", "habit_app",
                "-f", path,
            ],
            check=True,
            env={**os.environ, "PGPASSWORD": "nindagiyeprosper"},
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Erreur pg_dump : {e}")

    return FileResponse(
        path,
        filename="habit_app_backup.sql",
        media_type="application/sql",
    )